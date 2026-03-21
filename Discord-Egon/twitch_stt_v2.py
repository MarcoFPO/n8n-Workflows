#!/opt/twitch-stt/venv/bin/python3
"""
Twitch Stream STT → OpenClaw Bridge v2

Backends:
  pywhispercpp  - whisper.cpp via pywhispercpp (~4x schneller als Python-Whisper, chunk-basiert)
  streaming     - faster-whisper + LocalAgreement (whisper_streaming) - ~1.5s Latenz statt 6s

Unterschiede zu v1:
  - pywhispercpp Backend: C++ Inferenz, 4x schneller, CHUNK_SECS=6, beam_size=1
  - streaming Backend: OnlineASRProcessor mit LocalAgreement-Algorithmus,
    CHUNK_SECS=1.5, text wird bestätigt sobald zwei aufeinanderfolgende
    Fenster übereinstimmen (~2-3s Latenz)

Abhängigkeiten:
  pip: pywhispercpp, faster-whisper, librosa (alle in /opt/twitch-stt/venv)
  repos: /opt/whisper_streaming/ (LocalAgreement-Implementierung)
"""

import sys
sys.path.insert(0, "/opt/whisper_streaming")

import subprocess
import threading
import queue
import time
import signal
import logging
import argparse

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("twitch-stt")

# ─── Konfiguration ────────────────────────────────────────────────────────────

OPENCLAW_BIN = "/home/mdoehler/.npm-global/bin/openclaw"
SAMPLE_RATE  = 16000
MIN_TEXT_LEN = 4

SUMMARY_INTERVAL_SECS = 5 * 60
SUMMARY_MIN_CHARS     = 400
SUMMARY_MAX_CHARS     = 1200

SUMMARY_PROMPT = (
    "[Stream-Audio der letzten Minuten – bitte fasse in 1-2 Sätzen zusammen "
    "was gerade im Stream besprochen wurde. Antworte direkt und knapp im Chat-Stil.]"
)

# ─── Audio Capture ────────────────────────────────────────────────────────────

def capture_audio(
    channel: str,
    chunk_secs: float,
    audio_queue: queue.Queue,
    stop: threading.Event,
):
    streamlink_cmd = [
        "streamlink", f"https://www.twitch.tv/{channel}",
        "best", "--stdout", "--quiet",
    ]
    ffmpeg_cmd = [
        "ffmpeg", "-re", "-i", "pipe:0",
        "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE),
        "-f", "s16le", "-loglevel", "quiet", "pipe:1",
    ]
    chunk_bytes = int(SAMPLE_RATE * 2 * chunk_secs)

    sl = ff = None
    try:
        log.info(f"Connecting to twitch.tv/{channel} …")
        sl = subprocess.Popen(streamlink_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        ff = subprocess.Popen(
            ffmpeg_cmd, stdin=sl.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        log.info(f"Audio capture started (chunk={chunk_secs}s)")

        while not stop.is_set():
            data = ff.stdout.read(chunk_bytes)
            if not data:
                log.warning("Audio stream ended")
                break
            if audio_queue.full():
                try:
                    audio_queue.get_nowait()
                except queue.Empty:
                    pass
            audio_queue.put(data)

    except Exception as e:
        log.error(f"Capture error: {e}")
    finally:
        for proc in (ff, sl):
            if proc:
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                except Exception:
                    pass
        log.info("Audio capture stopped")


# ─── Backend A: pywhispercpp (whisper.cpp) ────────────────────────────────────

def transcribe_worker_pywhisper(
    audio_queue: queue.Queue,
    text_queue: queue.Queue,
    stop: threading.Event,
    model_size: str,
    language: str | None,
):
    """
    Chunk-basiertes Backend via whisper.cpp (pywhispercpp).
    ~4× schneller als faster-whisper auf CPU durch C++-Implementierung.
    Greedy-Decoding (temperature=0, best_of=1) für maximale Geschwindigkeit.
    """
    from pywhispercpp.model import Model

    log.info(f"Loading whisper.cpp model '{model_size}' (CPU, 6 threads) …")
    model = Model(
        model_size,
        n_threads=6,
        print_progress=False,
        print_realtime=False,
    )
    log.info("whisper.cpp model ready")

    while not stop.is_set():
        try:
            data = audio_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0

        try:
            segments = model.transcribe(
                audio,
                language=language or "",
                no_context=True,
                temperature=0.0,
                greedy={"best_of": 1},
            )
            for seg in segments:
                text = seg.text.strip()
                if len(text) >= MIN_TEXT_LEN:
                    log.info(f"  STT [cpp] → {text}")
                    text_queue.put(text)
        except Exception as e:
            log.error(f"Transcription error: {e}")

    log.info("pywhispercpp worker stopped")


# ─── Backend B: whisper_streaming mit LocalAgreement ─────────────────────────

class CpuFasterWhisperASR:
    """
    faster-whisper auf CPU mit der für whisper_streaming's OnlineASRProcessor
    kompatiblen API (ts_words, segments_end_ts).
    """
    sep = ""  # faster-whisper liefert Leerzeichen im Token-Text selbst

    def __init__(self, lan: str, modelsize: str = "base"):
        self.original_language = lan if lan not in ("auto", "") else None
        self.transcribe_kargs: dict = {}
        from faster_whisper import WhisperModel
        log.info(f"Loading faster-whisper '{modelsize}' (CPU int8, 6 threads) …")
        self.model = WhisperModel(
            modelsize, device="cpu", compute_type="int8", cpu_threads=6
        )
        log.info("faster-whisper model ready")

    def transcribe(self, audio: np.ndarray, init_prompt: str = ""):
        segs, _ = self.model.transcribe(
            audio,
            language=self.original_language,
            initial_prompt=init_prompt or None,
            beam_size=1,
            word_timestamps=True,          # für LocalAgreement zwingend nötig
            condition_on_previous_text=False,
            vad_filter=True,
            **self.transcribe_kargs,
        )
        return list(segs)

    def ts_words(self, segments):
        """Gibt [(start, end, word), ...] zurück – whisper_streaming-Protokoll."""
        out = []
        for seg in segments:
            for word in (seg.words or []):
                if seg.no_speech_prob > 0.9:
                    continue
                out.append((word.start, word.end, word.word))
        return out

    def segments_end_ts(self, segments):
        return [s.end for s in segments]

    def use_vad(self):
        self.transcribe_kargs["vad_filter"] = True

    def set_translate_task(self):
        self.transcribe_kargs["task"] = "translate"


def transcribe_worker_streaming(
    audio_queue: queue.Queue,
    text_queue: queue.Queue,
    stop: threading.Event,
    model_size: str,
    language: str | None,
):
    """
    Streaming-Backend: faster-whisper + LocalAgreement-Algorithmus.

    Funktionsweise (LocalAgreement):
    - Audio wird in kleinen Fenstern (1.5s) kontinuierlich eingespeist.
    - OnlineASRProcessor transkribiert immer den gesamten gepufferten Audio.
    - Ein Wort wird "bestätigt" (committed), sobald zwei aufeinanderfolgende
      Hypothesen übereinstimmen → typische Latenz ~2-3s statt 6-8s.
    - Puffer wird nach ~15s Segment-Ende beschnitten.
    """
    from whisper_online import OnlineASRProcessor

    asr = CpuFasterWhisperASR(lan=language or "auto", modelsize=model_size)
    online = OnlineASRProcessor(
        asr,
        buffer_trimming=("segment", 15),
        logfile=open("/dev/null", "w"),  # whisper_streaming-eigene Logs unterdrücken
    )
    log.info("whisper_streaming (LocalAgreement) ready")

    while not stop.is_set():
        try:
            data = audio_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
        online.insert_audio_chunk(audio)

        try:
            beg, end, text = online.process_iter()
        except Exception as e:
            log.error(f"Streaming transcription error: {e}")
            continue

        if text:
            text = text.strip()
            if len(text) >= MIN_TEXT_LEN:
                log.info(f"  STT [stream +{end:.1f}s] → {text}")
                text_queue.put(text)

    # Restlichen Buffer flushen
    try:
        _, _, text = online.finish()
        if text and len(text.strip()) >= MIN_TEXT_LEN:
            text_queue.put(text.strip())
    except Exception:
        pass

    log.info("streaming worker stopped")


# ─── OpenClaw Injection + Summary ────────────────────────────────────────────

_INJECT_ENV = {
    "HOME": "/home/mdoehler",
    "PATH": "/home/mdoehler/.npm-global/bin:/usr/local/bin:/usr/bin:/bin",
}


def _run_openclaw(channel: str, message: str, deliver: bool):
    cmd = [
        OPENCLAW_BIN, "agent",
        "--channel", "twitch",
        "--to", f"#{channel}",
        "--message", message,
    ]
    if deliver:
        cmd.append("--deliver")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=90, env=_INJECT_ENV
        )
        if result.returncode != 0:
            log.error(f"OpenClaw failed (rc={result.returncode}): {result.stderr.strip()}")
        else:
            action = "SUMMARY→chat" if deliver else "context"
            log.info(f"  [{action}] OK: {message[:70]}")
    except subprocess.TimeoutExpired:
        log.error("OpenClaw inject timed out")
    except Exception as e:
        log.error(f"OpenClaw inject error: {e}")


def inject_and_summary_worker(
    text_queue: queue.Queue,
    channel: str,
    stop: threading.Event,
):
    """
    - Jede STT-Zeile → stille Kontext-Injektion (kein --deliver)
    - Alle SUMMARY_INTERVAL_SECS oder bei genug Text → Zusammenfassung mit --deliver
    """
    buffer: list[str] = []
    last_summary = time.monotonic()

    while not stop.is_set():
        try:
            text = text_queue.get(timeout=1.0)
            buffer.append(text)
            _run_openclaw(channel, f"[Stream] {text}", deliver=False)
        except queue.Empty:
            pass

        if not buffer:
            continue

        now = time.monotonic()
        elapsed = now - last_summary
        total_chars = sum(len(t) for t in buffer)

        should_summarize = (
            elapsed >= SUMMARY_INTERVAL_SECS
            or total_chars >= SUMMARY_MAX_CHARS
            or (total_chars >= SUMMARY_MIN_CHARS and elapsed >= 90)
        )

        if should_summarize:
            excerpt = " ".join(buffer)
            summary_msg = (
                f"[Stream-Transkript der letzten ~{int(elapsed / 60) + 1} Minuten:\n"
                f"{excerpt}\n\n"
                f"{SUMMARY_PROMPT}]"
            )
            log.info(
                f"→ Triggering summary ({len(buffer)} segments, "
                f"{total_chars} chars, {int(elapsed)}s)"
            )
            _run_openclaw(channel, summary_msg, deliver=True)
            buffer.clear()
            last_summary = time.monotonic()

    log.info("Inject/summary worker stopped")


# ─── Main ─────────────────────────────────────────────────────────────────────

BACKENDS = {
    "pywhispercpp": (transcribe_worker_pywhisper, 6.0),   # chunk-basiert, schnell
    "streaming":    (transcribe_worker_streaming, 1.5),   # LocalAgreement, niedrige Latenz
}


def main():
    parser = argparse.ArgumentParser(description="Twitch STT → OpenClaw Bridge v2")
    parser.add_argument("channel", help="Twitch channel name (z.B. aibix0001)")
    parser.add_argument("--model", default="base", choices=["tiny", "base", "small"],
                        help="Whisper-Modellgröße (default: base)")
    parser.add_argument("--lang", default="de",
                        help="Sprachcode (default: de)")
    parser.add_argument("--interval", type=int, default=300,
                        help="Summary-Intervall in Sekunden (default: 300)")
    parser.add_argument(
        "--backend", default="pywhispercpp", choices=list(BACKENDS.keys()),
        help=(
            "STT-Backend: "
            "pywhispercpp = whisper.cpp, ~4× schneller (chunk-basiert, 6s); "
            "streaming = LocalAgreement, ~2-3s Latenz (default: pywhispercpp)"
        ),
    )
    args = parser.parse_args()

    global SUMMARY_INTERVAL_SECS
    SUMMARY_INTERVAL_SECS = args.interval

    transcribe_fn, chunk_secs = BACKENDS[args.backend]

    log.info(
        f"Twitch STT v2: channel={args.channel} model={args.model} "
        f"lang={args.lang} backend={args.backend} chunk={chunk_secs}s "
        f"summary_interval={args.interval}s"
    )

    stop    = threading.Event()
    audio_q = queue.Queue(maxsize=10)
    text_q  = queue.Queue()

    threads = [
        threading.Thread(
            target=capture_audio,
            args=(args.channel, chunk_secs, audio_q, stop),
            daemon=True, name="capture",
        ),
        threading.Thread(
            target=transcribe_fn,
            args=(audio_q, text_q, stop, args.model, args.lang),
            daemon=True, name="transcribe",
        ),
        threading.Thread(
            target=inject_and_summary_worker,
            args=(text_q, args.channel, stop),
            daemon=True, name="inject",
        ),
    ]

    def _shutdown(sig, frame):
        log.info("Shutting down …")
        stop.set()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    for t in threads:
        t.start()

    while not stop.is_set():
        time.sleep(5)
        if not threads[0].is_alive():
            log.info("Capture thread died – restarting in 15s …")
            time.sleep(15)
            if not stop.is_set():
                t = threading.Thread(
                    target=capture_audio,
                    args=(args.channel, chunk_secs, audio_q, stop),
                    daemon=True, name="capture",
                )
                t.start()
                threads[0] = t

    for t in threads:
        t.join(timeout=5)
    log.info("Stopped.")


if __name__ == "__main__":
    main()
