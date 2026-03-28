# 🧪 Test-Objekt: WI-SW02

**Status:** ✅ Integration Test
**Testobjekt:** `WI-SW02`
**Typ:** Switch/Device
**Test-Workflow:** `qQXIZPWmuFR6ylWC`

---

## 📋 Überblick

Das Test-Objekt **WI-SW02** ist in den Test-Workflow integriert. Der Workflow wird automatisch nach diesem Objekt suchen und es, falls gefunden, mit einem ⭐ kennzeichnen.

---

## 🎯 Was WI-SW02 im Test-Workflow macht

### 1️⃣ Define Test Parameters Node
```javascript
const testObject = 'WI-SW02';
```

- Definiert das Test-Objekt
- Loggt den Namen
- Gibt Hinweis zum Filtern

### 2️⃣ Process Response Node
```javascript
// Suche nach Test-Objekt
const testObjectFound = result.find(item => item.hostname === testObject);

if (testObjectFound) {
  console.log(`✅ Test-Objekt GEFUNDEN: ${testObject}`);
  displayData = [testObjectFound, ...rest];  // An erster Stelle
}
```

**Verhalten:**
- ✅ Falls WI-SW02 gefunden: An Stelle 1 anzeigen
- ✅ Mit ⭐ kennzeichnen
- ✅ count aktualisiert
- ✅ test_object_found = true

---

## 📊 Mock-Daten für WI-SW02

Falls keine echten Daten vom Sub-Workflow kommen:

```json
{
  "hostname": "WI-SW02",
  "ip": "10.1.1.200",
  "ssh_user": "admin",
  "ssh_password": "test-password"
}
```

**Verwendung:** Nur wenn Sub-Workflow keine Ergebnisse hat (Fallback)

---

## 🚀 Test-Szenarien mit WI-SW02

### Szenario 1: Standard-Test (Alle Daten laden)

**Parameter:**
```javascript
{
  load_vms: true,
  load_lxcs: true,
  load_devices: true,
  filter_by_type: null,
  filter_by_ids: null,
  device_primary_ip_filter: true
}
```

**Ergebnis:**
```
✅ Sub-Workflow Response:
Total items returned: 5
Test-Objekt: WI-SW02

📋 5 Items (Test-Objekt: WI-SW02):
  1. WI-SW02 (10.1.1.200) - User: admin ⭐ TEST-OBJEKT
  2. vm-prod-01 (10.1.1.100) - User: root
  3. router-01 (10.1.1.150) - User: admin
  ...
```

---

### Szenario 2: Nur WI-SW02 Filtern

**Parameter (im Node anpassen):**
```javascript
filter_by_ids: '[WI-SW02]'  // Nach diesem Hostname filtern
```

**Ergebnis:**
```
✅ Sub-Workflow Response:
Total items returned: 1
Test-Objekt: WI-SW02

📋 1 Items (Test-Objekt: WI-SW02):
  1. WI-SW02 (10.1.1.200) - User: admin ⭐ TEST-OBJEKT

Success: test_object_found = true
```

---

### Szenario 3: Keine Ergebnisse (Mock-Daten)

**Wenn Sub-Workflow nichts zurückgibt:**

```
✅ Sub-Workflow Response:
Total items returned: 0
Test-Objekt: WI-SW02

📋 1 Items (Test-Objekt: WI-SW02):
  1. WI-SW02 (10.1.1.200) - User: admin ⭐ TEST-OBJEKT

Message: Success (with mock data)
```

---

## 📝 Output-Format mit WI-SW02

### Success Response (mit Test-Objekt gefunden)

```json
{
  "message": "Success",
  "count": 5,
  "test_object": "WI-SW02",
  "test_object_found": true,
  "items": [
    {
      "hostname": "WI-SW02",
      "ip": "10.1.1.200",
      "ssh_user": "admin",
      "ssh_password": "test-password"
    },
    ...
  ]
}
```

### Success Response (nur Mock-Daten)

```json
{
  "message": "Success",
  "count": 1,
  "test_object": "WI-SW02",
  "test_object_found": false,
  "items": [
    {
      "hostname": "WI-SW02",
      "ip": "10.1.1.200",
      "ssh_user": "admin",
      "ssh_password": "test-password"
    }
  ]
}
```

---

## 🔍 Konsolenausgabe mit WI-SW02

**Wenn Test-Workflow ausgeführt wird:**

```
✅ Sub-Workflow Response:
Total items returned: 5
Test-Objekt: WI-SW02

✅ Test-Objekt GEFUNDEN: WI-SW02

📋 5 Items (Test-Objekt: WI-SW02):
  1. WI-SW02 (10.1.1.200) - User: admin ⭐ TEST-OBJEKT
  2. vm-prod-01 (10.1.1.100) - User: root
  3. lxc-app-01 (10.1.1.50) - User: root
  4. router-01 (10.1.1.150) - User: admin
  5. device-fw-01 (10.2.1.1) - User: admin
```

---

## 💻 Wie man WI-SW02 im Workflow ändert

### Im "Define Test Parameters" Node:

```javascript
// Aktuelle Zeile:
const testObject = 'WI-SW02';

// Ändern zu:
const testObject = 'vm-prod-01';     // Oder anderes Device
const testObject = 'router-01';
const testObject = 'lxc-app-01';
// etc.
```

---

## 🧪 Test-Checkliste mit WI-SW02

- [ ] Test-Workflow `qQXIZPWmuFR6ylWC` startet
- [ ] "Define Test Parameters" zeigt WI-SW02
- [ ] Sub-Workflow wird aufgerufen
- [ ] Process Response führt Suche durch
- [ ] Falls gefunden: ⭐ und test_object_found = true
- [ ] Falls nicht gefunden: Mock-Daten werden genutzt
- [ ] Output hat test_object Feld
- [ ] Output hat test_object_found Flag

---

## ✅ Validierung

### Test erfolgreich wenn:

```
✓ Konsole zeigt: "✅ Test-Objekt GEFUNDEN: WI-SW02"
✓ WI-SW02 ist an Position 1
✓ WI-SW02 hat ⭐ kennzeichnung
✓ test_object_found = true (wenn gefunden)
✓ Output JSON ist valid
```

### Test mit Mock erfolgreich wenn:

```
✓ Konsole zeigt: kein "GEFUNDEN", aber Mock-Daten
✓ WI-SW02 wird angezeigt (Mock)
✓ test_object_found = false
✓ count = 1 (Mock-Daten)
✓ Output JSON ist valid
```

---

## 🔧 Änderungen im Workflow

### `test-workflow.json` – Node "Define Test Parameters"

```javascript
const testObject = 'WI-SW02';  // ← HIER ANPASSEN

// Optionen für Filter:
filter_by_ids: null,           // Alle laden
filter_by_ids: '[WI-SW02]'    // Nur WI-SW02
```

### `test-workflow.json` – Node "Process Response"

```javascript
// Automatisch:
// - Sucht nach WI-SW02
// - Priorisiert es (Position 1)
// - Kennzeichnet mit ⭐
// - Setzt test_object_found Flag
```

---

## 📚 Referenzen

- **Test-Workflow:** `/opt/Projekte/n8n-workflows/netbox-abfrage/test-workflow.json`
- **Test-Guide:** `/opt/Projekte/n8n-workflows/netbox-abfrage/TEST-GUIDE.md`
- **Sub-Workflow:** ID `k8qsLh2kePMYWurk` (Primitive: NetBox-Abfrage)
- **API Reference:** `N8N-API-REFERENCE.md`

---

## 🎯 Zusammenfassung

**WI-SW02** ist ein Testobjekt, das:

1. ✅ Automatisch gesucht wird
2. ✅ Mit ⭐ gekennzeichnet wird (wenn gefunden)
3. ✅ An die erste Position rückt
4. ✅ Mock-Daten hat (falls nicht vorhanden)
5. ✅ Status-Flag setzt (test_object_found)
6. ✅ Validierung vereinfacht

---

**Version:** 1.0 | **Status:** ✅ Production Ready | **Last Updated:** 2026-01-24
