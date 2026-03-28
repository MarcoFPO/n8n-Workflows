# 🧪 Manueller Test-Guide - NetBox-Abfrage v4.0

## Status: ✅ BEREIT ZUM TESTEN

**Deployment-Datum:** 2026-01-24 18:16 UTC
**Version:** 4.0 (Production Ready)
**Workflow ID:** `k8qsLh2kePMYWurk`
**Test-Workflow ID:** `qQXIZPWmuFR6ylWC`

---

## 🎯 Test-Szenarios

### Test 1: Hostname-Filter (Priorität 1) ✅

**Parameter:**
```json
{
  "hostname": "WI-SW02"
}
```

**Erwartetes Ergebnis:**
- Suche nach Asset mit Hostname "WI-SW02"
- Output: `[{ hostname: "WI-SW02", ip: "10.x.x.x", ssh_user: "...", ssh_password: "..." }]`
- Oder: `[]` (wenn nicht gefunden)

**Konsolen-Output erwartet:**
```
🎯 Suche nach Hostname: "WI-SW02"
🎯 Hostname-Filter aktiv: "WI-SW02"
✅ Hostname-Filter Ergebnis: 1 Objekt(e) gefunden
```

---

### Test 2: Type-Filter (Priorität 2) ✅

**Parameter:**
```json
{
  "hostname": null,
  "filter_by_type": "device"
}
```

**Erwartetes Ergebnis:**
- Alle Devices (physische Geräte) zurückgeben
- Output: `[{ hostname: "device1", ... }, { hostname: "device2", ... }, ...]`

**Konsolen-Output erwartet:**
```
🎯 Suche nach Type: "device"
📊 NetBox-Abfrage: Total zurückgegeben = N
```

---

### Test 3: ID-Filter (Priorität 3) ✅

**Parameter:**
```json
{
  "hostname": null,
  "filter_by_ids": "[123, 456]"
}
```

**Erwartetes Ergebnis:**
- Nur Assets mit IDs 123 oder 456 zurückgeben
- Output: Array mit 0-2 Assets (je nachdem ob IDs existieren)

**Konsolen-Output erwartet:**
```
🎯 Suche nach IDs: [123,456]
📊 NetBox-Abfrage: Total zurückgegeben = 1 or 2
```

---

### Test 4: Keine Filter ✅

**Parameter:**
```json
{
  "hostname": null,
  "filter_by_type": null,
  "filter_by_ids": null
}
```

**Erwartetes Ergebnis:**
- Alle Assets (VMs, LXCs, Devices) mit IP zurückgeben
- Output: `[{ ... }, { ... }, ...]` (alle verfügbaren Assets)

**Konsolen-Output erwartet:**
```
📋 Keine Filter - alle Objekte werden zurückgegeben
📊 NetBox-Abfrage: Total zurückgegeben = N
```

---

## 🚀 Workflow ausführen

### Via n8n UI:

1. Öffne: `http://10.1.1.180/workflows/k8qsLh2kePMYWurk` (Sub-Workflow)
2. Klick: **Trigger Workflow** Button oder **Test-Workflow ausführen**
3. Im **Manual Trigger** Node Parameter eingeben
4. Konsolen-Output beobachten

### Oder: Test-Workflow verwenden

1. Öffne: `http://10.1.1.180/workflows/qQXIZPWmuFR6ylWC` (Test-Workflow)
2. Klick: **Test** oder **Manually execute workflow**
3. Der Test-Workflow nutzt `hostname: "WI-SW02"` als Default
4. Konsolen-Output + Response anschauen

---

## ✅ Erwartete Output-Struktur

```json
[
  {
    "hostname": "WI-SW02",
    "ip": "10.1.1.200",
    "ssh_user": "admin",
    "ssh_password": "password123"
  }
]
```

**Felder:**
- `hostname` (string): Asset Name aus NetBox
- `ip` (string): Primäre IP (CIDR-Format entfernt)
- `ssh_user` (string): SSH Benutzer (aus Custom Fields oder Default)
- `ssh_password` (string): SSH Passwort (aus Custom Fields oder null)

---

## 🔍 Debugging

### Wenn keine Ergebnisse zurückgegeben:

1. **Check: NetBox Verbindung**
   - Gehe zu Node: "🔍 NetBox: Query Virtuelle Maschinen"
   - Check Credentials: NetBox API Key gültig?

2. **Check: Hostname existiert in NetBox**
   - Öffne NetBox UI: `http://netbox-server/`
   - Suche nach dem Hostname

3. **Check: Konsolen-Output**
   - Workflow-Ausführung öffnen
   - Konsolen-Logs prüfen auf Fehler

4. **Check: Filter-Logik**
   - Apply Filters Node Logik prüfen
   - console.log Output verstehen

### Wenn Fehler "no IP":

- Asset hat keine primäre IP-Adresse in NetBox
- Nur Assets mit IP werden zurückgegeben (by design)

---

## 📊 Performance-Erwartungen

- **Query 1 (VMs):** ~200-500ms (abhängig von NetBox Größe)
- **Query 2 (Devices):** ~200-500ms
- **Merge + Filter:** ~50-100ms
- **Total:** ~500-1200ms

---

## 🎯 Validation-Checkliste

- [ ] Hostname-Filter funktioniert (Test 1)
- [ ] Type-Filter funktioniert (Test 2)
- [ ] ID-Filter funktioniert (Test 3)
- [ ] Keine Filter funktioniert (Test 4)
- [ ] Output hat exakt 4 Felder
- [ ] Konsolen-Logs sind informativ
- [ ] Fehlerbehandlung funktioniert (Non-Existent Hostname)

---

## 📝 Notes

- Hostname-Filter hat höchste Priorität (Test 1 ignoriert filter_by_type/filter_by_ids)
- Nur Assets mit primärer IP werden zurückgegeben (by design)
- Fallback-Filter werden nur angewendet wenn hostname=null
- SSH-User Default: "admin" für Devices, "root" für VMs/LXCs

---

**Version:** 4.0 | **Status:** ✅ Production Ready | **Last Updated:** 2026-01-24 18:30 UTC
