# 🔍 Primitive: NetBox-Abfrage

**Status:** Production Ready
**Version:** 3.0 (2x Query Architecture mit Hostname-Filter)
**Tier:** 1 (Primitive Sub-Workflow)
**Workflow ID:** `k8qsLh2kePMYWurk`

---

## 📋 Übersicht

Der **NetBox-Abfrage** ist ein spezialisierter Primitive Sub-Workflow für die effiziente Batch-Abfrage aller aktiven Infrastruktur-Objekte aus NetBox.

**Funktionalität:**
- 📥 Parallel laden von Virtuellen Maschinen (VMs+LXCs) und Geräten
- 🎯 Hostname-Filter mit höchster Priorität (oder leeres Array wenn nicht gefunden)
- 🔍 Flexible Fallback-Filterung nach Typ oder ID (wenn hostname nicht gegeben)
- 🔐 Automatische Extraktion von SSH-Zugangsdaten
- 📤 Standardisierte 4-Feld Output (hostname, ip, ssh_user, ssh_password)

---

## 🏗️ Workflow-Architektur

```
Input (Master Workflow)
        ↓
Parse Input Parameters (Validiert hostname, filter_by_type, filter_by_ids)
        ↓
    ┌─────────────────────────┐
    │ 2x NetBox API Queries   │
    ├─────────────────────────┤
    │ Query 1:                │
    │ virtualization          │  Alle aktiven VMs/LXCs
    │ Query 2:                │
    │ dcim/devices            │  Alle aktiven Devices mit IP
    └─────────────────────────┘
        ↓
   Merge All Objects
        ↓
Apply Filters & Finalize
    - Client-Side Hostname-Filter (Priorität 1)
    - Fallback: Type-Filter (Priorität 2)
    - Fallback: ID-Filter (Priorität 3)
    - Formatierung auf 4 Felder
        ↓
Output an Master
```

---

## 🔌 Aufruf aus Master-Workflow

```javascript
// Beispiel 1: Mit Hostname (direkte Abfrage)
await $tools.workflow.call({
  name: 'Primitive: NetBox-Abfrage',
  parameters: {
    hostname: 'WI-SW02'        // ← Sucht nach diesem Hostname
  }
});

// Beispiel 2: Ohne Hostname (mit Fallback-Filtern)
await $tools.workflow.call({
  name: 'Primitive: NetBox-Abfrage',
  parameters: {
    hostname: null,             // ← Kein Hostname
    filter_by_type: 'device'    // ← Fallback: Nur Devices
  }
});
```

---

## 📥 Input Parameter

| Parameter | Typ | Erforderlich | Beschreibung |
|-----------|-----|-------------|-------------|
| `hostname` | string | Nein | **Priorität 1 - Hostname-Filter**: Sucht nach diesem Hostname. Wenn gegeben, wird NUR dieses Objekt zurückgegeben (oder leeres Array wenn nicht gefunden). `filter_by_type` und `filter_by_ids` werden ignoriert! |
| `filter_by_type` | string | Nein | **Priorität 2 - Fallback-Filter** (nur wenn hostname=null): Filtert Ergebnisse nach Typ: `'vm'`, `'lxc'` oder `'device'` |
| `filter_by_ids` | string | Nein | **Priorität 3 - Fallback-Filter** (nur wenn hostname=null): Filtert Ergebnisse nach NetBox-Objekt-IDs. Format: JSON Array String z.B. `'[123, 456]'` |

---

## 📤 Output Format

**Array von Objekten mit 4 Feldern:**

```json
[
  {
    "hostname": "vm-prod-01",
    "ip": "10.1.1.100",
    "ssh_user": "root",
    "ssh_password": "secret123"
  },
  {
    "hostname": "router-01",
    "ip": "10.1.1.200",
    "ssh_user": "admin",
    "ssh_password": "router-pass"
  }
]
```

---

## 🎯 Workflow-Info

| Eigenschaft | Wert |
|-------------|------|
| **Workflow ID** | `k8qsLh2kePMYWurk` |
| **Name** | Primitive: NetBox-Abfrage |
| **Typ** | Primitive Sub-Workflow |
| **Status** | ✅ Aktiv |
| **Nodes** | 6 |
| **Tier** | Tier 1 (Low-Level Primitives) |

---

## 🔧 Nodes

| # | Name | Funktion |
|---|------|----------|
| 1 | 📥 Input from Master | Empfängt 3 Parameter: hostname, filter_by_type, filter_by_ids |
| 2 | 🔧 Parse Input Parameters | Validiert und parst die Input Parameter; logged Suchstrategie |
| 3 | 🔍 NetBox: Query VMs | Queries virtualization/virtual-machines mit status=active |
| 4 | 🔍 NetBox: Query Devices | Queries dcim/devices mit status=active + has_primary_ip=true |
| 5 | 🔗 Merge All Objects | Kombiniert Ergebnisse aus beiden Queries |
| 6 | 🎯 Apply Filters & Finalize | Wendet Hostname/Type/ID Filter an und formatiert auf 4 Felder |

---

## ✨ Besonderheiten

### ✅ Optimiert
- **2 parallele NetBox-API Queries** (virtualization + dcim) ohne redundante Filter
- **Client-seitige Filterung** in Apply Filters Node (JavaScr ipt)
- **Effiziente Fallback-Filterung** nach Typ oder ID wenn Hostname nicht gegeben
- **Minimale API-Überlastung** durch Limit von 250 Assets pro Query

### ✅ Robust
- Hostname-Filter hat höchste Priorität (garantiert 0 oder 1 Ergebnis)
- Type/ID-Filter als Fallback wenn hostname nicht gegeben
- Filtert Items ohne IP automatisch
- Defaults für SSH-User pro Typ
- Graceful Error Handling

### ✅ Wartbar
- Minimale Node-Struktur (6 Nodes)
- 2 dedizierte NetBox Query Nodes (wartbar und klar)
- Zentrale Apply Filters Node für komplexe Filterung
- Ausführlich dokumentierte Input/Output
- Einfach zu erweitern

---

## 📚 Dokumentation

- **INPUT-SPEC.md** - Detaillierte Parameter-Spezifikation
- **OUTPUT-SPEC.md** - Output-Format & Filterung
- **USAGE-GUIDE.md** - Integration & Beispiele

---

## 🚀 Integration

Dieser Sub-Workflow wird vom Master-Orchestrator aufgerufen für:
- Discovery aller Infrastruktur-Objekte
- Bereitstellung von SSH-Zugangsdaten
- Effiziente Filterung nach Typ/ID

---

**Version:** 4.0 (Client-Side Filtering)
**Status:** ✅ Production Ready
**Last Updated:** 2026-01-24 (18:30 UTC)

**Latest Changes in v4.0:**
- Vereinfachte Input-Parameter: Nur `hostname`, `filter_by_type`, `filter_by_ids`
- ❌ Entfernt: `load_vms`, `load_lxcs`, `load_devices`, `device_primary_ip_filter` (nicht nötig)
- ✅ Client-Side Filtering statt Server-Side (ermöglicht flexible Fallback-Filter)
- ✅ Klarere Filter-Priorität: hostname (Priorität 1) > type (Priorität 2) > ids (Priorität 3)
