# 📑 Dokumentations-Index – NetBox-Abfrage

**Workflow ID:** `k8qsLh2kePMYWurk`
**Workflow Name:** Primitive: NetBox-Abfrage
**Version:** 2.0
**Status:** ✅ Production Ready
**Last Updated:** 2026-01-24

---

## 📚 Dokumentation

### 🎯 README.md
**Überblick über den Workflow**

- Workflow-Architektur & Ablauf
- 7 Nodes (Input → Parse → Query → Merge → Filter)
- Funktionalität: Parallel-Abfragen, Filterung, Output-Standardisierung
- Besonderheiten: Optimiert, Robust, Wartbar

👉 **Für:** Schneller Überblick, Architektur-Verständnis

---

### 📥 INPUT-SPEC.md
**Detaillierte Parameter-Spezifikation**

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|-------------|
| `load_vms` | boolean | `true` | VMs laden |
| `load_lxcs` | boolean | `true` | LXCs laden |
| `load_devices` | boolean | `true` | Devices laden |
| `filter_by_type` | string | `null` | Filter nach Typ ('vm', 'lxc', 'device') |
| `filter_by_ids` | string | `null` | Filter nach IDs (JSON Array String) |
| `device_primary_ip_filter` | boolean | `true` | Nur Objekte mit IP |

**Inhalt:**
- Jeder Parameter detailliert erklärt
- Gültige Werte & Defaults
- Validierungsregeln
- 5 Beispiel-Aufrufe

👉 **Für:** Parameter konfigurieren, Aufruf strukturieren

---

### 📤 OUTPUT-SPEC.md
**Output-Format & Filterung**

**Standard Output: 4 Felder**
```json
{
  "hostname": "string",
  "ip": "string",
  "ssh_user": "string",
  "ssh_password": "string"
}
```

**Inhalt:**
- Jedes Feld detailliert erklärt
- Datenquellen & Mapping
- Filterungs-Reihenfolge
- Output-Beispiele
- Fehlerbehandlung & Garantien

👉 **Für:** Output verstehen, Verarbeitung planen

---

### 🚀 USAGE-GUIDE.md
**Integration & Best Practices**

**Inhalt:**
- Basis-Integration (3 Schritte)
- 5 Use Cases mit Code
- Fehlerbehandlung
- Integration mit anderen Workflows
- Daten-Verarbeitung (Transformation, Gruppierung)
- 8 Best Practices
- Integrations-Checkliste

**Use Cases:**
1. Alle Infrastruktur laden
2. Nur Objekt-Typen laden
3. Nach Typ filtern
4. Nach IDs filtern
5. Kombination: Filter + Typ

👉 **Für:** Master-Integration, Best Practices, Pattern

---

### 💡 EXAMPLES.md
**Praktische Code-Beispiele**

**10 praktische Szenarien mit vollständigem Code:**

| # | Szenario | Fokus |
|---|----------|--------|
| 1 | Basis-Aufruf mit Logging | Einfache Verwendung |
| 2 | Nur Production-VMs | Typ-Filter |
| 3 | Filter nach IDs | ID-Filter |
| 4 | CSV-Export | Transformation |
| 5 | Monitoring-Agent Installation | SSH-Ausführung |
| 6 | Nur Hosts mit SSH-Passwort | Filtern |
| 7 | Health-Check Script | Mehrfach-SSH |
| 8 | Gruppierung nach Subnet | Gruppierung |
| 9 | MongoDB-Storage | Persistierung |
| 10 | Notifications bei Änderungen | Vergleich & Alerts |

👉 **Für:** Copy-Paste Code, Inspiration, Troubleshooting

---

### 🔧 netbox-abfrage.json
**Workflow-Datei (n8n)**

- Vollständige Workflow-Definition
- 7 Nodes mit Konfiguration
- NetBox-Credentials
- Connections/Routing

👉 **Für:** In n8n importieren, bei Bedarf anpassen

---

## 🗺️ Workflow-Navigation

```
Master-Workflow
        ↓
📥 INPUT-SPEC.md  ← Parameter definieren
        ↓
🚀 USAGE-GUIDE.md  ← Integration planen
        ↓
💡 EXAMPLES.md  ← Code anpassen
        ↓
Primitive: NetBox-Abfrage aufrufen
        ↓
📤 OUTPUT-SPEC.md  ← Output verarbeiten
        ↓
Master-Workflow weiterleiten
```

---

## 🎯 Quick Start

### 1️⃣ Überblick lesen
```bash
📖 Lesen: README.md (2 min)
```

### 2️⃣ Parameter definieren
```bash
📖 Lesen: INPUT-SPEC.md (5 min)
💻 Beispiel wählen: USAGE-GUIDE.md → Use Case
```

### 3️⃣ Workflow aufrufen
```bash
💡 Code kopieren: EXAMPLES.md → Szenario
🔧 Anpassen & integrieren
```

### 4️⃣ Output verarbeiten
```bash
📖 Lesen: OUTPUT-SPEC.md (5 min)
💻 Beispiel: EXAMPLES.md → Use Case
```

---

## 📊 Dokument-Übersicht

| Datei | Größe | Fokus | Leser |
|-------|-------|-------|-------|
| **README.md** | ~4 KB | Architektur | Alle |
| **INPUT-SPEC.md** | ~8 KB | Parameter | Integrierer |
| **OUTPUT-SPEC.md** | ~7 KB | Output | Integrierer |
| **USAGE-GUIDE.md** | ~10 KB | Patterns | Integrierer |
| **EXAMPLES.md** | ~12 KB | Code | Entwickler |
| **INDEX.md** | ~3 KB | Navigation | Alle |
| **netbox-abfrage.json** | ~5 KB | Workflow | DevOps |

**Gesamt:** ~49 KB, ~1500 Zeilen Dokumentation + Code

---

## 🔍 Thematische Suche

### Ich möchte ...

**... den Workflow verstehen**
→ README.md

**... ihn aufrufen**
→ INPUT-SPEC.md + USAGE-GUIDE.md (Step 1-2)

**... ein bestimmtes Szenario umsetzen**
→ EXAMPLES.md (durchsuchen)

**... die Output-Struktur verstehen**
→ OUTPUT-SPEC.md

**... häufige Probleme vermeiden**
→ USAGE-GUIDE.md (Best Practices)

**... Code schnell zu adaptieren**
→ EXAMPLES.md + USAGE-GUIDE.md

**... die Architektur zu modifizieren**
→ README.md + netbox-abfrage.json

---

## 🔗 Externe Referenzen

- **NetBox API:** `https://docs.netbox.dev/en/stable/api/`
- **n8n Workflows:** `https://docs.n8n.io/workflows/`
- **n8n Sub-Workflows:** `https://docs.n8n.io/workflows/sub-workflows/`

---

## ✅ Checkliste für neue Entwickler

- [ ] README.md lesen (Überblick)
- [ ] INPUT-SPEC.md verstehen (Parameter)
- [ ] USAGE-GUIDE.md durchgehen (Patterns)
- [ ] EXAMPLES.md durchsuchen (Dein Use Case)
- [ ] Beispiel-Code kopieren & anpassen
- [ ] OUTPUT-SPEC.md durchgehen (Output-Handling)
- [ ] Lokales Testen durchführen
- [ ] Bei Fragen: USAGE-GUIDE.md (Best Practices)

---

## 📞 Support & Fragen

| Frage | Dokument |
|-------|----------|
| Wie rufe ich den Workflow auf? | USAGE-GUIDE.md (Schritt 1) |
| Welche Parameter gibt es? | INPUT-SPEC.md |
| Welche Werte kann ich als Parameter übergeben? | INPUT-SPEC.md + EXAMPLES.md |
| Welche Daten bekomme ich zurück? | OUTPUT-SPEC.md |
| Wie verarbeite ich das Output? | OUTPUT-SPEC.md + EXAMPLES.md |
| Mein Use Case ist nicht abgedeckt | EXAMPLES.md + USAGE-GUIDE.md (kombinieren) |
| Warum bekomme ich leere Ergebnisse? | OUTPUT-SPEC.md (Filterungs-Reihenfolge) |
| Wie handle ich SSH-Passwörter sicher? | USAGE-GUIDE.md (Best Practice #2) |

---

## 🏆 Highlights

### 🎯 Hauptfeatures
- ✅ Parallele NetBox-Queries (3 gleichzeitig)
- ✅ Flexible Filterung (Typ, ID, IP)
- ✅ Automatische SSH-Defaults
- ✅ Standardisiertes 4-Feld Output
- ✅ Production-Ready

### 📚 Dokumentation
- ✅ Umfassend (49 KB, 1500 Zeilen)
- ✅ Praktisch (10 Code-Beispiele)
- ✅ Strukturiert (nach Zielgruppe)
- ✅ Leicht zu navigieren (INDEX.md)

### 🔧 Integration
- ✅ Einfache API
- ✅ Klare Parameter & Output
- ✅ Fehlerbehandlung
- ✅ Best Practices dokumentiert

---

## 📝 Versionsverlauf

| Version | Datum | Änderungen |
|---------|-------|-----------|
| 2.0 | 2026-01-24 | Komplette Dokumentation erstellt, Workflow neu deployed |
| 1.0 | 2026-01-XX | Ursprünglicher Workflow |

---

**Letzte Aktualisierung:** 2026-01-24
**Workflow ID:** `k8qsLh2kePMYWurk`
**Status:** ✅ Production Ready
