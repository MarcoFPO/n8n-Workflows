# 📤 Output-Spezifikation – NetBox-Abfrage

**Workflow ID:** `k8qsLh2kePMYWurk`
**Version:** 2.0
**Status:** ✅ Production Ready

---

## 🎯 Überblick

Der **Primitive: NetBox-Abfrage** Workflow gibt ein standardisiertes **Array von Objekten** mit genau **4 Feldern** zurück:

```json
[
  {
    "hostname": "string",
    "ip": "string",
    "ssh_user": "string",
    "ssh_password": "string"
  }
]
```

---

## 📋 Output-Felder

### 1. **hostname** (string)
| Eigenschaft | Wert |
|---|---|
| **Typ** | `string` |
| **Quelle** | NetBox Feld: `name` |
| **Leer möglich** | Nein |
| **Beschreibung** | Der Hostname des Objekts |

**Beispiele:**
```
"vm-prod-01"
"router-01"
"server-web-02"
"container-app"
```

---

### 2. **ip** (string)
| Eigenschaft | Wert |
|---|---|
| **Typ** | `string` (IPv4-Adresse) |
| **Quelle** | NetBox Feld: `primary_ip4.address` |
| **Format** | IPv4 ohne CIDR-Notation |
| **Leer möglich** | Nein (Items ohne IP werden gefiltert) |
| **Beschreibung** | Die primäre IPv4-Adresse |

**Verarbeitung:**
- CIDR-Format wird zu reiner IP-Adresse konvertiert
- `10.1.1.100/24` → `10.1.1.100`
- `192.168.1.50/32` → `192.168.1.50`

**Beispiele:**
```
"10.1.1.100"
"192.168.1.50"
"10.2.3.45"
```

---

### 3. **ssh_user** (string)
| Eigenschaft | Wert |
|---|---|
| **Typ** | `string` |
| **Quelle** | NetBox Custom Field: `ssh_username` |
| **Fallback** | `admin` (Devices), `root` (VMs/LXCs) |
| **Leer möglich** | Nein (es wird immer ein Default verwendet) |
| **Beschreibung** | SSH-Benutzer für Remote-Verbindungen |

**Logik:**
1. Prüfe `custom_fields.ssh_username`
2. Falls leer → verwende Default basierend auf Objekttyp:
   - **Devices:** `admin`
   - **VMs/LXCs:** `root`

**Beispiele:**
```
"root"
"admin"
"deploy"
"ubuntu"
"centos"
```

---

### 4. **ssh_password** (string | null)
| Eigenschaft | Wert |
|---|---|
| **Typ** | `string` oder `null` |
| **Quelle** | NetBox Custom Field: `ssh_password` |
| **Leer möglich** | Ja (kann null sein) |
| **Sicherheit** | ⚠️ Sensitive Data |
| **Beschreibung** | SSH-Passwort für Remote-Verbindungen |

**Verhalten:**
- Wenn `custom_fields.ssh_password` gesetzt: verwende diesen Wert
- Wenn `custom_fields.ssh_password` leer/nicht gesetzt: `null`
- **WICHTIG:** Behandle dieses Feld als sensitive Data!

**Beispiele:**
```json
"ssh_password": "super_secret_pass123"
"ssh_password": null
```

---

## 🔄 Output-Format

### Standard-Output (mit Daten)
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
    "ssh_password": null
  },
  {
    "hostname": "app-server",
    "ip": "192.168.1.50",
    "ssh_user": "deploy",
    "ssh_password": "deploy-pass"
  }
]
```

### Leerer Output (keine Treffer)
```json
[]
```

**Länge:** Array enthält 0 bis N Objekte, abhängig von:
- Filtern (`filter_by_type`, `filter_by_ids`)
- Verfügbaren Objekten in NetBox
- `device_primary_ip_filter` Einstellung

---

## 🎯 Filterung & Ausschlusslogik

### Objekte WERDEN AUSGESCHLOSSEN wenn:

| Grund | Details |
|---|---|
| **Keine IP** | `primary_ip4` ist null/leer (und `device_primary_ip_filter=true`) |
| **Falsche Typ** | Nicht mit `filter_by_type` überein |
| **ID nicht gelistet** | Nicht in `filter_by_ids` enthalten |
| **Status nicht active** | NetBox Status ist nicht "active" |

### Filterungs-Reihenfolge

```
1. Load-Entscheidung (load_vms, load_lxcs, load_devices)
2. Status-Filter (nur "active" Objekte)
3. IP-Filter (device_primary_ip_filter=true)
4. Typ-Filter (filter_by_type)
5. ID-Filter (filter_by_ids)
6. Output-Standardisierung (4 Felder)
```

---

## 📊 Datenquellen & Mapping

### Von NetBox zu Output

| Output-Feld | NetBox-Quelle | Typ | Fallback |
|---|---|---|---|
| `hostname` | `name` | string | - |
| `ip` | `primary_ip4.address` (ohne /XX) | string | Items ausgeschlossen |
| `ssh_user` | `custom_fields.ssh_username` | string | `admin` oder `root` |
| `ssh_password` | `custom_fields.ssh_password` | string | `null` |

### Objekt-Typ Bestimmung

| Quelle | Mapping | Standard ssh_user |
|---|---|---|
| VMs (Tag="vm") | type = 'vm' | `root` |
| LXCs (Tag="lxc") | type = 'lxc' | `root` |
| Devices | type = 'device' | `admin` |

---

## ✅ Validierung & Fehlerbehandlung

### Fehlerhafte Daten

**Problem:** Objekt hat kein `primary_ip4`
- **Verhalten:** Objekt wird ausgeschlossen (nicht im Output)
- **Grund:** IP ist erforderlich für SSH-Zugriff

**Problem:** Objekt hat keine Custom Fields
- **Verhalten:** SSH-Defaults werden verwendet
- **SSH-User:** `admin` (Device) oder `root` (VM/LXC)
- **SSH-Password:** `null`

**Problem:** CIDR-Notation in IP
- **Verhalten:** CIDR wird entfernt, nur IP bleibt
- **Beispiel:** `10.1.1.100/24` → `10.1.1.100`

### Garantien

| Garantie | Details |
|---|---|
| **4 Felder** | Jedes Output-Objekt hat genau diese 4 Felder: `hostname`, `ip`, `ssh_user`, `ssh_password` |
| **Eindeutige Hosts** | Nicht garantiert (aber wahrscheinlich) |
| **Sortierung** | Keine garantierte Sortierung |
| **Duplikate** | Können vorkommen, wenn dasselbe Objekt in mehreren Kategorien (VMs/LXCs/Devices) existiert |

---

## 📈 Output-Beispiele

### Beispiel 1: Alle Objekte
```json
[
  {
    "hostname": "vm-prod-01",
    "ip": "10.1.1.100",
    "ssh_user": "root",
    "ssh_password": "secret123"
  },
  {
    "hostname": "lxc-app-01",
    "ip": "10.1.1.101",
    "ssh_user": "root",
    "ssh_password": null
  },
  {
    "hostname": "router-01",
    "ip": "10.1.1.200",
    "ssh_user": "admin",
    "ssh_password": "router-pass"
  }
]
```

### Beispiel 2: Nur VMs (filter_by_type='vm')
```json
[
  {
    "hostname": "vm-prod-01",
    "ip": "10.1.1.100",
    "ssh_user": "root",
    "ssh_password": "secret123"
  },
  {
    "hostname": "vm-dev-01",
    "ip": "10.1.1.105",
    "ssh_user": "root",
    "ssh_password": null
  }
]
```

### Beispiel 3: Nach IDs gefiltert (filter_by_ids='[42, 100]')
```json
[
  {
    "hostname": "server-42",
    "ip": "192.168.1.42",
    "ssh_user": "admin",
    "ssh_password": null
  },
  {
    "hostname": "app-100",
    "ip": "192.168.1.100",
    "ssh_user": "deploy",
    "ssh_password": "deploy123"
  }
]
```

### Beispiel 4: Keine Treffer (leeres Array)
```json
[]
```

---

## 🔍 Output-Verarbeitung im Master

**Typischer Code im Master-Workflow:**

```javascript
const infrastructure = await $tools.workflow.call({
  name: 'Primitive: NetBox-Abfrage',
  parameters: {
    load_vms: true,
    load_lxcs: true,
    load_devices: true,
    filter_by_type: null,
    filter_by_ids: null,
    device_primary_ip_filter: true
  }
});

// infrastructure ist ein Array
infrastructure.forEach(host => {
  console.log(`${host.hostname} (${host.ip}) SSH: ${host.ssh_user}`);
});
```

---

## ⚠️ Wichtige Hinweise

### Sicherheit
- `ssh_password` kann **null** sein – Handle gracefully
- `ssh_password` sollte nie geloggt oder exposed werden
- SSH-Credentials sollten nur bei echtem Bedarf verwendet werden

### Datenkonsistenz
- Output ist abhängig von NetBox-Daten
- Falls NetBox leer: Output ist leeres Array
- Falls Filter zu restriktiv: Output ist leeres Array

### Performance
- Workflow lädt standardmäßig alle 3 Kategorien parallel
- Für große Infrastrukturen kann Filterung wichtig sein
- Verwende `filter_by_ids` oder `filter_by_type` für effiziente Abfragen

---

## 🔗 Referenzen

- **INPUT-SPEC.md** - Eingabe-Parameter
- **USAGE-GUIDE.md** - Integration & Beispiele
- **README.md** - Workflow-Überblick

---

**Version:** 2.0 | **Status:** ✅ Production Ready | **Last Updated:** 2026-01-24
