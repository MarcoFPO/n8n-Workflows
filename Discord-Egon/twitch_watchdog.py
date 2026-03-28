#!/opt/twitch-stt/venv/bin/python3
"""
Twitch Stream Watchdog für twitch-stt.service

Überwacht einen Twitch-Kanal via Twitch Helix API und startet/stoppt
twitch-stt.service automatisch wenn der Kanal live geht bzw. offline ist.

Credentials: liest clientId + accessToken aus OpenClaw-Config
             (/home/mdoehler/.openclaw/openclaw.json)
Token-Refresh: automatisch bei 401-Fehler via refreshToken

Start:  twitch-stt sofort wenn Kanal live
Stop:   twitch-stt nach OFFLINE_THRESHOLD × POLL_INTERVAL Sekunden
        (verhindert Flapping bei kurzen Verbindungsunterbrechungen)
"""

import argparse
import json
import logging
import signal
import subprocess
import threading
import sys

import requests

# ─── Konfiguration ────────────────────────────────────────────────────────────

OPENCLAW_CONFIG   = "/home/mdoehler/.openclaw/openclaw.json"
TWITCH_STREAMS_URL = "https://api.twitch.tv/helix/streams"
TWITCH_TOKEN_URL   = "https://id.twitch.tv/oauth2/token"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("twitch-watchdog")

# ─── Twitch API ───────────────────────────────────────────────────────────────

def load_twitch_creds(account: str = "default") -> dict:
    """Liest Twitch-Credentials aus OpenClaw-Config (clientId, accessToken, ...)."""
    with open(OPENCLAW_CONFIG) as f:
        cfg = json.load(f)
    acc = cfg["channels"]["twitch"]["accounts"][account]
    return {
        "client_id":     acc["clientId"],
        "access_token":  acc["accessToken"],
        "refresh_token": acc["refreshToken"],
        "client_secret": acc["clientSecret"],
    }


def _refresh_token(creds: dict) -> str:
    """Erneuert den Access-Token via Refresh-Token und gibt neuen Token zurück."""
    resp = requests.post(TWITCH_TOKEN_URL, data={
        "grant_type":    "refresh_token",
        "refresh_token": creds["refresh_token"],
        "client_id":     creds["client_id"],
        "client_secret": creds["client_secret"],
    }, timeout=15)
    resp.raise_for_status()
    return resp.json()["access_token"]


def is_stream_live(channel: str, creds: dict) -> bool:
    """
    Prüft via Twitch Helix API ob der Kanal live ist.
    Führt automatischen Token-Refresh durch bei 401.
    """
    def _get(token: str) -> requests.Response:
        return requests.get(
            TWITCH_STREAMS_URL,
            params={"user_login": channel},
            headers={
                "Client-Id":     creds["client_id"],
                "Authorization": f"Bearer {token}",
            },
            timeout=15,
        )

    resp = _get(creds["access_token"])

    if resp.status_code == 401:
        log.info("Access-Token abgelaufen – erneuere via Refresh-Token …")
        creds["access_token"] = _refresh_token(creds)
        resp = _get(creds["access_token"])

    resp.raise_for_status()
    return len(resp.json().get("data", [])) > 0


# ─── Service-Steuerung ────────────────────────────────────────────────────────

def _service_active() -> bool:
    r = subprocess.run(
        ["systemctl", "is-active", "--quiet", "twitch-stt"],
        capture_output=True,
    )
    return r.returncode == 0


def _start_service(channel: str):
    log.info(f"#{channel} ist LIVE → starte twitch-stt.service")
    result = subprocess.run(["systemctl", "start", "twitch-stt"], capture_output=True, text=True)
    if result.returncode != 0:
        log.error(f"systemctl start fehlgeschlagen: {result.stderr.strip()}")


def _stop_service(channel: str):
    log.info(f"#{channel} ist OFFLINE → stoppe twitch-stt.service")
    result = subprocess.run(["systemctl", "stop", "twitch-stt"], capture_output=True, text=True)
    if result.returncode != 0:
        log.error(f"systemctl stop fehlgeschlagen: {result.stderr.strip()}")


# ─── Watchdog-Schleife ────────────────────────────────────────────────────────

def run(channel: str, poll_secs: int, offline_threshold: int):
    """
    Hauptschleife: prüft alle poll_secs Sekunden ob der Kanal live ist.

    Logik:
      live  → sofort starten (wenn noch nicht aktiv)
      offline × threshold → erst dann stoppen (Anti-Flapping-Puffer)
    """
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT,  lambda *_: stop.set())

    log.info(
        f"Watchdog gestartet: channel={channel}  "
        f"poll={poll_secs}s  offline-threshold={offline_threshold}×"
    )

    try:
        creds = load_twitch_creds()
    except Exception as e:
        log.error(f"OpenClaw-Config nicht lesbar: {e}")
        sys.exit(1)

    offline_count = 0

    while not stop.is_set():
        try:
            live = is_stream_live(channel, creds)
        except requests.RequestException as e:
            log.warning(f"Helix-API-Fehler (überspringe): {e}")
            stop.wait(poll_secs)
            continue
        except Exception as e:
            log.error(f"Unerwarteter Fehler: {e}")
            stop.wait(poll_secs)
            continue

        if live:
            if offline_count > 0:
                log.info(f"#{channel} wieder live (war {offline_count}× offline gezählt)")
            offline_count = 0
            if not _service_active():
                _start_service(channel)
            else:
                log.debug(f"#{channel} live – twitch-stt läuft bereits")
        else:
            offline_count += 1
            log.debug(f"#{channel} offline (Zähler {offline_count}/{offline_threshold})")
            if offline_count >= offline_threshold:
                if _service_active():
                    _stop_service(channel)
                else:
                    log.debug("twitch-stt bereits gestoppt")

        stop.wait(poll_secs)

    # Beim Beenden: Service auch stoppen (Watchdog = einzige Steuerinstanz)
    if _service_active():
        log.info("Watchdog wird beendet → stoppe twitch-stt.service")
        _stop_service(channel)

    log.info("Watchdog gestoppt.")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Twitch Watchdog: Startet/stoppt twitch-stt.service automatisch"
    )
    parser.add_argument(
        "channel", nargs="?", default="aibix0001",
        help="Twitch-Kanalname ohne # (default: aibix0001)",
    )
    parser.add_argument(
        "--poll", type=int, default=60,
        help="Prüfintervall in Sekunden (default: 60)",
    )
    parser.add_argument(
        "--offline-threshold", type=int, default=3,
        help="Anzahl konsekutiver Offline-Meldungen vor Service-Stop (default: 3 = 3 min)",
    )
    parser.add_argument(
        "--account", default="default",
        help="OpenClaw Twitch-Account-Name (default: default)",
    )
    args = parser.parse_args()

    run(
        channel=args.channel,
        poll_secs=args.poll,
        offline_threshold=args.offline_threshold,
    )


if __name__ == "__main__":
    main()
