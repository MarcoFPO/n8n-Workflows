# 🧪 Test-Workflow Guide – NetBox-Abfrage

**Test-Workflow:** `test-workflow.json`
**Ziel-Workflow:** `Primitive: NetBox-Abfrage` (ID: `k8qsLh2kePMYWurk`)
**Status:** ✅ Test-Ready

---

## 🎯 Überblick

Der Test-Workflow ermöglicht es dir, den **Primitive: NetBox-Abfrage** Sub-Workflow manuell zu testen und die Ergebnisse zu überprüfen.

**Workflow-Ablauf:**
```
Manual Trigger → Define Test Parameters → Call Sub-Workflow → Process Response
```

---

## 🚀 Verwendung

### Schritt 1: Test-Workflow in n8n importieren

1. In n8n: **Workflows** → **Create new**
2. Code-Editor öffnen (oder JSON importieren)
3. `test-workflow.json` hochladen oder kopieren
4. Speichern & Aktivieren

### Schritt 2: Test starten

Auf den **Play-Button** klicken um den Workflow zu starten.

---

## 🔧 Test-Parameter anpassen

Die Test-Parameter befinden sich im Node **"🔧 Define Test Parameters"**.

### Standard-Parameter (alles laden)
```javascript
{
  "load_vms": true,
  "load_lxcs": true,
  "load_devices": true,
  "filter_by_type": null,
  "filter_by_ids": null,
  "device_primary_ip_filter": true
}
```

---

## 📝 Test-Szenarien

### Test 1: Nur VMs laden
```javascript
const testParams = {
  load_vms: true,
  load_lxcs: false,
  load_devices: false,
  filter_by_type: 'vm',
  filter_by_ids: null,
  device_primary_ip_filter: true
};
```

**Editiere:** Node "🔧 Define Test Parameters"
```javascript
// Ändere diese Zeile:
filter_by_type: null,    // ← Zu:
filter_by_type: 'vm',    // ← Nur VMs
```

---

### Test 2: Nach Typ filtern
```javascript
const testParams = {
  load_vms: true,
  load_lxcs: true,
  load_devices: true,
  filter_by_type: 'device',  // ← Nur Devices
  filter_by_ids: null,
  device_primary_ip_filter: true
};
```

---

### Test 3: Nach spezifischen IDs filtern
```javascript
const testParams = {
  load_vms: true,
  load_lxcs: true,
  load_devices: true,
  filter_by_type: null,
  filter_by_ids: '[42, 100, 150]',  // ← Diese IDs
  device_primary_ip_filter: true
};
```

---

### Test 4: Nur Objekte mit IP
```javascript
const testParams = {
  load_vms: true,
  load_lxcs: true,
  load_devices: true,
  filter_by_type: null,
  filter_by_ids: null,
  device_primary_ip_filter: true  // ← Nur mit IP
};
```

---

### Test 5: Kombination
```javascript
const testParams = {
  load_vms: true,
  load_lxcs: false,
  load_devices: true,
  filter_by_type: null,
  filter_by_ids: '[1, 2, 3, 4, 5]',
  device_primary_ip_filter: true
};
```

---

## 📊 Workflow-Nodes

### 1️⃣ 🚀 Manual Trigger
**Typ:** Manual Trigger
**Funktion:** Startet den Workflow manuell

```
Klick auf Play-Button im Editor
        ↓
Workflow startet
```

---

### 2️⃣ 🔧 Define Test Parameters
**Typ:** Code Node (JavaScript)
**Funktion:** Definiert Test-Parameter

```javascript
const testParams = {
  load_vms: true,
  load_lxcs: true,
  load_devices: true,
  filter_by_type: null,      // Änder diese Werte!
  filter_by_ids: null,
  device_primary_ip_filter: true
};

return { json: testParams };
```

**Modifizierbare Werte:**
- `load_vms`: `true` oder `false`
- `load_lxcs`: `true` oder `false`
- `load_devices`: `true` oder `false`
- `filter_by_type`: `null`, `'vm'`, `'lxc'`, `'device'`
- `filter_by_ids`: `null` oder `'[1, 2, 3]'`
- `device_primary_ip_filter`: `true` oder `false`

---

### 3️⃣ 📞 Call: Primitive NetBox-Abfrage
**Typ:** Execute Workflow
**Funktion:** Ruft den Sub-Workflow auf

```
Eingabe: Test-Parameter (aus Node 2)
   ↓
Sub-Workflow wird ausgeführt
   ↓
Ausgabe: Array von Hosts (4-Feld Format)
```

**Workflow ID:** `k8qsLh2kePMYWurk`

---

### 4️⃣ 📊 Process Response
**Typ:** Code Node (JavaScript)
**Funktion:** Verarbeitet und zeigt Ergebnisse

```javascript
const result = $input.first().json;

console.log('✅ Sub-Workflow Response:');
console.log(`Total items returned: ${result.length}`);

if (result.length === 0) {
  console.log('⚠️ Keine Ergebnisse gefunden!');
  return { json: { message: 'Keine Ergebnisse', count: 0, items: [] } };
}

console.log('\n📋 Erste 5 Items:');
const first5 = result.slice(0, 5);
first5.forEach((item, index) => {
  console.log(`  ${index + 1}. ${item.hostname} (${item.ip}) - User: ${item.ssh_user}`);
});

return { json: { message: 'Success', count: result.length, items: result } };
```

**Output:**
```
✅ Sub-Workflow Response:
Total items returned: 15

📋 Erste 5 Items:
  1. vm-prod-01 (10.1.1.100) - User: root
  2. vm-prod-02 (10.1.1.101) - User: root
  3. router-01 (10.1.1.200) - User: admin
  4. app-server (192.168.1.50) - User: deploy
  5. lxc-app-01 (10.1.1.50) - User: root
```

---

## 📈 Ergebnis-Struktur

### Erfolgreiche Antwort
```json
{
  "message": "Success",
  "count": 15,
  "items": [
    {
      "hostname": "vm-prod-01",
      "ip": "10.1.1.100",
      "ssh_user": "root",
      "ssh_password": "secret123"
    },
    {
      "hostname": "vm-prod-02",
      "ip": "10.1.1.101",
      "ssh_user": "root",
      "ssh_password": null
    },
    ...
  ]
}
```

### Leere Antwort
```json
{
  "message": "Keine Ergebnisse",
  "count": 0,
  "items": []
}
```

---

## 🔍 Debugging

### Execution Logs anschauen

1. Workflow-Lauf starten (Play-Button)
2. Nach Ausführung: **Execution** Tab öffnen
3. Jeden Node durchgehen:
   - ✅ Node "🔧 Define Test Parameters" → Logs checken
   - ✅ Node "📞 Call: Primitive NetBox-Abfrage" → Fehler?
   - ✅ Node "📊 Process Response" → Output anschauen

---

### Häufige Probleme

#### Problem: Sub-Workflow wird nicht gefunden
```
Error: Workflow with ID k8qsLh2kePMYWurk not found
```

**Lösung:**
- Workflow ID überprüfen: `k8qsLh2kePMYWurk`
- Workflow existiert in n8n?
- Workflow ist aktiviert?

---

#### Problem: Keine Ergebnisse zurückgegeben
```
Message: "Keine Ergebnisse"
Count: 0
```

**Mögliche Gründe:**
- NetBox ist leer
- Filter zu restriktiv (z.B. `filter_by_type: 'unknown'`)
- IDs existieren nicht in NetBox (`filter_by_ids: '[99999]'`)

**Lösung:**
- Mit Standard-Parametern testen (alle `null` bzw. Defaults)
- NetBox-Daten überprüfen

---

#### Problem: SSH-Passwörter sind alle `null`
```json
"ssh_password": null
```

**Grund:** Custom Fields nicht in NetBox gespeichert

**Lösung:**
- Custom Fields in NetBox füllen
- SSH-Defaults nutzen (ssh_user ist gesetzt)

---

## ✅ Test-Checkliste

- [ ] Workflow in n8n importiert
- [ ] Workflow ID `k8qsLh2kePMYWurk` ist korrekt
- [ ] Manual Trigger clickbar
- [ ] Parameter konfiguriert
- [ ] Workflow startet erfolgreich (Play)
- [ ] Response hat Daten oder ist leer (beide OK)
- [ ] Logs zeigen Details
- [ ] Output-Format korrekt (4 Felder)

---

## 🎯 Nächste Schritte

Nach erfolgreichem Test des Sub-Workflows:

1. **Sub-Workflow in Master integrieren**
   - Code aus USAGE-GUIDE.md kopieren
   - Mit echten Anforderungen anpassen

2. **Production-Test**
   - Mit echten Parametern testen
   - Mit verschiedenen Filterkombinationen testen
   - Fehlerbehandlung testen

3. **Monitoring**
   - Logs überwachen
   - Performance testen
   - bei Problemen: Debugging mit diesem Test-Workflow

---

## 🔗 Referenzen

- **Workflow-Datei:** `test-workflow.json`
- **Ziel-Sub-Workflow:** `Primitive: NetBox-Abfrage` (ID: `k8qsLh2kePMYWurk`)
- **Parameter-Spec:** INPUT-SPEC.md
- **Output-Spec:** OUTPUT-SPEC.md
- **Integration Guide:** USAGE-GUIDE.md

---

**Version:** 1.0 | **Status:** ✅ Test-Ready | **Last Updated:** 2026-01-24
