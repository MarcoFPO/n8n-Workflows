# LLD: Proof of Concept (PoC) Implementierungsplan (Punkt 6)

---

### 1. Zielsetzung

Das Ziel des Proof of Concept (PoC) ist es, die technische Machbarkeit der Kern-Pipeline mit einem reduzierten Umfang zu validieren. Der PoC soll zeigen, dass Daten akquiriert, verarbeitet, für ein Training genutzt und zur Prognoseerstellung verwendet werden können.

*   **Fokus:** 1 Aktie, 1 Prognosehorizont, 2 Experten-Modelle, 1 Meta-Modell.
*   **Erfolgskriterium:** Eine durchgängig lauffähige Pipeline, die eine Prognose generiert und deren Performance messbar ist (auch wenn sie noch nicht profitabel ist).

### 2. Umfang des PoC

*   **Wertpapier:** 1 liquider, gut dokumentierter US-Titel (z.B. **Apple Inc., AAPL**).
*   **Prognosehorizont:** Nur **1 Woche (7 Kalendertage)**.
*   **Experten-Modelle:**
    1.  **Technisches Modell:** LSTM auf Basis von Kurs- & Volumendaten.
    2.  **Fundamental-/Makro-Modell:** LightGBM auf Basis von `yfinance`-Fundamentaldaten und FRED-Makrodaten (VIX, Leitzins).
    *   *Das Sentiment-Modell wird im PoC bewusst ausgelassen, da die NLP-Pipeline den Aufwand initial stark erhöhen würde.*
*   **Meta-Modell:** LightGBM zur Konsolidierung der beiden Experten-Prognosen.
*   **Datenbank:** Vollständiges Schema wird aufgesetzt und genutzt.

### 3. Phasen & Arbeitspakete

**Phase 1: Setup & Datengewinnung (ca. 1-2 Tage)**

*   **AP 1.1:** Projekt-Setup gemäß `LLD_Projekt_Setup_Technologie.md` (Verzeichnisstruktur, venv, `requirements.txt`).
*   **AP 1.2:** Aufsetzen der PostgreSQL-Datenbank mit TimescaleDB-Erweiterung. Erstellen aller Tabellen gemäß `LLD_Datenbank.md`.
*   **AP 1.3:** Implementierung des Skripts `src/data_acquisition/get_price_data.py` (holt OHLCV für AAPL via `yfinance` und schreibt in `raw_price_data`).
*   **AP 1.4:** Implementierung des Skripts `src/data_acquisition/get_fundamental_macro_data.py` (holt Fundamentaldaten via `yfinance` und Makro-Daten via `pandas-datareader` und schreibt in die `raw_*`-Tabellen).
*   **Meilenstein 1:** Die `raw_*`-Tabellen in der Datenbank sind mit historischen Daten für AAPL gefüllt.

**Phase 2: Datenvorverarbeitung (ca. 1 Tag)**

*   **AP 2.1:** Implementierung des Skripts `src/preprocessing/process_technical_features.py`, das aus `raw_price_data` liest, technische Indikatoren berechnet und in `features_technical_daily` schreibt.
*   **AP 2.2:** Implementierung des Skripts `src/preprocessing/process_fundamental_macro_features.py`, das aus den `raw_*`-Tabellen liest, das Forward-Filling durchführt und in `features_fundamental_macro_daily` schreibt.
*   **Meilenstein 2:** Die `features_*_daily`-Tabellen sind gefüllt und bereit für das Training.

**Phase 3: Modell-Training (ca. 2 Tage)**

*   **AP 3.1:** Implementierung des Trainings-Skripts `src/training/train_experts.py` für das **Technische Modell (LSTM)**. Das Skript muss Daten laden, skalieren, sequenzieren, trainieren und das Modell-Artefakt (`.h5`) sowie den Scaler (`.pkl`) speichern.
*   **AP 3.2:** Erweiterung von `train_experts.py` für das **Fundamental-/Makro-Modell (LightGBM)**.
*   **AP 3.3:** Implementierung des Trainings-Skripts `src/training/train_meta_model.py`, das die trainierten Experten-Modelle lädt, "out-of-sample"-Prognosen auf dem Validierungs-Set erstellt und das Meta-Modell trainiert und speichert.
*   **Meilenstein 3:** Alle Modell-Artefakte für den 1W-Horizont für AAPL sind im `/models/1W/`-Verzeichnis gespeichert.

**Phase 4: Inferenz & Evaluation (ca. 1 Tag)**

*   **AP 4.1:** Implementierung des Inferenz-Skripts `src/inference/predict.py`, das eine Prognose für ein gegebenes Datum erstellen kann.
*   **AP 4.2:** Implementierung des Evaluations-Skripts `src/evaluation/evaluate_model.py`, das die Walk-Forward-Validierung auf dem Test-Set durchführt und die Metriken (MAE, DA, etc.) für das Ensemble-Modell und das Baseline-Modell berechnet und ausgibt.
*   **Meilenstein 4:** Ein finaler Report (Konsolenausgabe oder CSV) mit dem Performance-Vergleich zwischen dem PoC-Modell und der Baseline liegt vor.

### 4. Ressourcen

*   **Software:** Python, PostgreSQL, Git.
*   **Hardware:** Standard-Entwickler-Laptop. Für das LSTM-Training ist eine (optionale) NVIDIA-GPU mit CUDA-Setup vorteilhaft, aber nicht zwingend erforderlich.
