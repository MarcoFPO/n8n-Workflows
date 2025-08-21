# LLD: Technologie-Stack & Projekt-Setup (Punkt 4)

---

### 1. Zielsetzung

Dieses Dokument beschreibt das technische Fundament des Projekts, einschließlich der Software-Versionen, des Abhängigkeitsmanagements und der Umgebungs-Konfiguration, um eine reproduzierbare und stabile Entwicklungsumgebung zu gewährleisten.

### 2. Kerntechnologien

*   **Programmiersprache:** Python 3.10 oder höher.
*   **Virtuelle Umgebung:** `venv` (Standardbibliothek von Python).
    *   **Begründung:** Isoliert die Projekt-Abhängigkeiten vom globalen System-Python und verhindert Konflikte.
*   **Paket-Management:** `pip` mit `requirements.txt`-Dateien.
    *   **Begründung:** Einfacher und universeller Standard für Python-Projekte.

### 3. Projektstruktur (Initial)

```
/Forschungsprojekt/
|-- data/                # (Optional) Für lokale CSV-Exporte oder temporäre Daten
|-- docs/                # Alle LLD- und HLD-Dokumente
|-- models/              # Speicherort für trainierte Modelle und Scaler
|-- src/                 # Der gesamte Python-Quellcode
|   |-- data_acquisition/  # Skripte zum Abrufen von Daten (z.B. get_price_data.py)
|   |-- preprocessing/     # Skripte für die Datenvorverarbeitung
|   |-- training/          # Skripte für das Modell-Training (train_experts.py, etc.)
|   |-- inference/         # Skripte für die Prognose-Erstellung (predict.py)
|   |-- utils/             # Hilfsfunktionen (z.B. datenbank-connect, config-loader)
|-- .gitignore           # Git-Ignore-Datei
|-- requirements.txt     # Haupt-Abhängigkeiten
|-- requirements-dev.txt # Entwicklungs-Abhängigkeiten
|-- README.md            # Projekt-Beschreibung und Setup-Anleitung
```

### 4. Abhängigkeitsmanagement (`requirements.txt`)

Die Abhängigkeiten werden in zwei Dateien aufgeteilt:

**`requirements.txt` (Kern-Abhängigkeiten):**
```
# --- Datenbank ---
psycopg2-binary==2.9.9
sqlalchemy==2.0.25

# --- Datenverarbeitung ---
pandas==2.2.2
numpy==1.26.4
pandas-ta==0.3.14b0
pandas-datareader==0.10.0

# --- Machine Learning ---
tensorflow==2.16.1
scikit-learn==1.4.2
lightgbm==4.3.0
xgboost==2.0.3

# --- NLP (Sentiment) ---
transformers==4.40.1
torch==2.3.0
nltk==3.8.1

# --- API-Zugriff ---
yfinance==0.2.38
NewsAPI-python==0.2.7
praw==7.7.1
requests==2.31.0
```

**`requirements-dev.txt` (Entwicklungs-Tools):**
```
# --- Code-Formatierung & Linting ---
black==24.4.2
ruff==0.4.2

# --- Notebooks für Analyse ---
jupyterlab==4.2.0
matplotlib==3.8.4
seaborn==0.13.2
```

### 5. Setup-Prozess

1.  **Repository klonen:** `git clone ...`
2.  **Virtuelle Umgebung erstellen:** `python3 -m venv venv`
3.  **Umgebung aktivieren:** `source venv/bin/activate`
4.  **Abhängigkeiten installieren:**
    *   Für die Ausführung: `pip install -r requirements.txt`
    *   Für die Entwicklung: `pip install -r requirements-dev.txt`
5.  **Datenbank-Setup:** PostgreSQL und die TimescaleDB-Erweiterung müssen separat installiert und konfiguriert werden. Die Zugangsdaten werden über Umgebungsvariablen oder eine `.env`-Datei verwaltet.
