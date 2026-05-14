# 📥 Input-Spezifikation – NetBox-Abfrage

**Workflow ID:** `k8qsLh2kePMYWurk`
**Version:** 3.0 (2x Query Architecture)
**Status:** ✅ Production Ready
**Last Updated:** 2026-01-24 (Hostname-Filter in v3.0)

---

## 🎯 Überblick

Der **Primitive: NetBox-Abfrage** Workflow akzeptiert folgende Input-Parameter vom Master-Workflow:

```javascript
// Beispiel 1: Mit Hostname-Filter (Priorität 1)
await $tools.workflow.call({
  name: 'Primitive: NetBox-Abfrage',
  parameters: {
    hostname: 'WI-SW02'        // ← Filter-Priorität 1: Hostname
  }
});

// Beispiel 2: Ohne Hostname (mit Fallback-Filtern)
await $tools.workflow.call({
  name: 'Primitive: NetBox-Abfrage',
  parameters: {
    hostname: null,             // ← Keine Hostname-Filter
    filter_by_type: 'device',   // ← Fallback-Filter (nur wenn hostname=null)
    filter_by_ids: null
  }
});
```

---

## 📋 Parameter-Definitionen

### 0. **hostname** (string) - PRIORITÄT 1 🎯
| Eigenschaft | Wert |
|---|---|
| **Typ** | `string` (null möglich) |
| **Default** | `null` |
| **Erforderlich** | Nein |
| **Beschreibung** | Hostname-Filter für spezifische Geräte-Abfrage |

**Verhalten:**
- Wenn `hostname` gegeben: **ONLY dieses Gerät wird zurückgegeben** (oder leeres Array wenn nicht gefunden)
- Hostname wird **direkt in beiden NetBox-Queries als Filter** verwendet
- Andere Filter (filter_by_type, filter_by_ids) werden **IGNORIERT** wenn hostname gesetzt ist
- Wenn `hostname = null`: Andere Filter werden angewendet (Fallback)

**Beispiele:**
```javascript
hostname: 'WI-SW02'      // → Query sucht nur nach diesem Hostname
hostname: 'vm-prod-01'   // → Query sucht nur nach diesem Hostname
hostname: null           // → Keine Hostname-Filter, verwende andere Filter
```

**Output:**
```javascript
hostname: 'WI-SW02'      // → [{ hostname: 'WI-SW02', ip: '...', ... }]  (1 oder 0 Objekte)
hostname: 'NOT-EXISTS'   // → []  (Leer wenn nicht gefunden!)
hostname: null           // → [{ ... }, { ... }, ...]  (Alle mit anderen Filtern)
```

---

### 1. **filter_by_type** (string | null)
| Eigenschaft | Wert |
|---|---|
| **Typ** | `string` |
| **Default** | `null` (kein Filter) |
| **Erforderlich** | Nein |
| **Gültige Werte** | `'vm'`, `'lxc'`, `'device'` |
| **Beschreibung** | Ergebnisse nach Objekt-Typ filtern |

**Verhalten:**
- `null` oder nicht gesetzt: Alle Typen werden zurückgegeben
- `'vm'`: Nur VMs
- `'lxc'`: Nur LXC-Container
- `'device'`: Nur physische Devices
- Ungültige Werte: Werden ignoriert (kein Filter angewendet)

**Beispiele:**
```javascript
filter_by_type: null      // Alle Typen
filter_by_type: 'vm'      // Nur VMs
filter_by_type: 'device'  // Nur Devices
```

---

### 2. **filter_by_ids** (string | null)
| Eigenschaft | Wert |
|---|---|
| **Typ** | `string` (JSON Array) |
| **Default** | `null` (kein Filter) |
| **Erforderlich** | Nein |
| **Format** | JSON Array von Integer-IDs |
| **Beschreibung** | Ergebnisse nach NetBox-Objekt-IDs filtern |

**Verhalten:**
- `null` oder nicht gesetzt: Alle Objekte werden zurückgegeben
- JSON Array (als String): Nur Objekte mit diesen IDs
- Ungültiges JSON: Wird ignoriert (kein Filter angewendet)

**Beispiele:**
```javascript
filter_by_ids: null           // Kein Filter
filter_by_ids: '[123, 456]'   // Nur Objekte mit ID 123 oder 456
filter_by_ids: '[1]'          // Nur Objekt mit ID 1
```

**Wichtig:** IDs müssen als **JSON-String** übergeben werden, nicht als Array!

---

## 🔄 Input-Verarbeitung

Der Workflow verarbeitet die Input-Parameter wie folgt:

```
Input → Parse Input Parameters → Validierung & Defaults → Query-Entscheidung
                                        ↓
                              Defaultwerte setzen
                              (load_vms=true, ...)
```

**Parse Input Parameters Node:**
- Konvertiert `filter_by_ids` von JSON-String zu Array (falls vorhanden)
- Setzt Defaults für boolean-Parameter
- Loggt Konfiguration in n8n Console

---

## ✅ Validierungsregeln

| Regel | Verhalten |
|---|---|
| Ungültige Parameter ignorieren | Keine Fehler, Standards werden verwendet |
| Leer-String statt null | Wird als `null` behandelt |
| Boolean-Parameter nicht gesetzt | `true` wird verwendet |
| `filter_by_ids` ungültiges JSON | Filter wird ignoriert |
| Alle Load-Parameter = false | Workflow lädt nichts, gibt leeres Array zurück |

---

## 📝 Beispiel-Aufrufe

### Beispiel 1: Mit Hostname-Filter
```javascript
await $tools.workflow.call({
  name: 'Primitive: NetBox-Abfrage',
  parameters: {
    hostname: 'WI-SW02'         // ← Sucht nach diesem Hostname
  }
});
```
**Ergebnis:**
- `[{ hostname: 'WI-SW02', ip: '...', ssh_user: '...', ssh_password: '...' }]` (wenn gefunden)
- `[]` (wenn nicht gefunden)

---

### Beispiel 2: Nach Typ filtern
```javascript
await $tools.workflow.call({
  name: 'Primitive: NetBox-Abfrage',
  parameters: {
    hostname: null,              // ← Keine Hostname-Filter
    filter_by_type: 'device'     // ← Fallback: Nur Devices
  }
});
```
**Ergebnis:** Alle Devices mit IP

---

### Beispiel 3: Nach IDs filtern
```javascript
await $tools.workflow.call({
  name: 'Primitive: NetBox-Abfrage',
  parameters: {
    hostname: null,
    filter_by_ids: '[42, 123, 789]'  // ← Fallback: Nur diese IDs
  }
});
```
**Ergebnis:** Nur Objekte mit den IDs 42, 123 oder 789

---

### Beispiel 4: Alle Objekte laden
```javascript
await $tools.workflow.call({
  name: 'Primitive: NetBox-Abfrage',
  parameters: {
    hostname: null,
    filter_by_type: null,        // ← Kein Filter
    filter_by_ids: null
  }
});
```
**Ergebnis:** Alle Objekte (VMs, LXCs, Devices) mit IP

---

## 🔗 Referenzen

- **NetBox Custom Fields:** SSH-Credentials aus `custom_fields.ssh_username` und `custom_fields.ssh_password`
- **SSH Default-Benutzer:** `admin` für Devices, `root` für VMs/LXCs
- **Primary IP:** Wird automatisch aus dem CIDR-Format extrahiert (z.B. `10.1.1.100/24` → `10.1.1.100`)

---

**Version:** 2.0 | **Status:** ✅ Production Ready | **Last Updated:** 2026-01-24
