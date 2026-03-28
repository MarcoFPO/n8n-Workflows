# Ernährungs-App

Eine umfassende Webanwendung für Ernährungsmanagement mit folgenden Features:

## Funktionen

### 1. Ernährungstagebuch
- Tägliche Erfassung von Mahlzeiten
- Kalorienzählung und Makronährstoff-Tracking
- Zeiterfassung der Mahlzeiten

### 2. Rezepteverwaltung
- Speichern und Kategorisieren von Rezepten
- Nährstoffberechnung pro Rezept
- Portionsanpassung

### 3. Mahlzeitenplaner
- Wochenplanung von Mahlzeiten
- Automatische Einkaufslisten-Generierung
- Integration mit Rezeptdatenbank

### 4. Nährstoffanalyse
- Detaillierte Auswertung der Nährstoffzufuhr
- Grafische Darstellung von Trends
- Empfehlungen basierend auf Zielen

## Technologie-Stack

- **Backend**: FastAPI (Python)
- **Frontend**: HTML/CSS/JavaScript + Bootstrap
- **Datenbank**: PostgreSQL
- **ORM**: SQLAlchemy
- **Deployment**: LXC Container (direkt)

## Projektstruktur

```
/
├── backend/           # FastAPI Backend
│   ├── app/          # Hauptanwendung
│   ├── models/       # SQLAlchemy Modelle
│   ├── api/          # API Endpoints
│   ├── core/         # Konfiguration & Utils
│   └── services/     # Business Logic
├── frontend/         # Web Frontend
│   ├── static/       # CSS, JS, Bilder
│   └── templates/    # Jinja2 Templates
├── database/         # Datenbank Scripts
│   ├── migrations/   # Alembic Migrationen
│   └── seeds/        # Testdaten
├── deployment/       # LXC Deployment Skripte
└── docs/             # Dokumentation
```

## Entwicklung

### Setup
```bash
# Backend einrichten
cd backend
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Server starten
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Datenbank
```bash
# Migrationen ausführen
alembic upgrade head
```

## Deployment

Die Anwendung wird direkt in einem LXC Container auf der Proxmox-Infrastruktur gehostet.