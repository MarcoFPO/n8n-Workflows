# 🚀 Usage Guide – NetBox-Abfrage

**Workflow ID:** `k8qsLh2kePMYWurk`
**Version:** 2.0
**Status:** ✅ Production Ready

---

## 🎯 Überblick

Dieser Guide zeigt, wie Sie den **Primitive: NetBox-Abfrage** Sub-Workflow aus Ihrem Master-Workflow aufrufen und die Ergebnisse verarbeiten.

---

## 🔌 Basis-Integration

### Schritt 1: Workflow im Master aufrufen

```javascript
const result = await $tools.workflow.call({
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
```

**Was passiert:**
1. Workflow wird aufgerufen mit den angegebenen Parametern
2. Alle aktiven VMs, LXCs und Devices aus NetBox werden geladen
3. Ergebnisse werden gefiltert und standardisiert
4. Array mit 4-Feld-Objekten wird zurückgegeben

---

### Schritt 2: Ergebnisse verarbeiten

```javascript
// Direkter Zugriff auf die Items
const items = result; // Array von Hosts

// Durch alle Hosts iterieren
items.forEach(host => {
  console.log(`Hostname: ${host.hostname}`);
  console.log(`IP: ${host.ip}`);
  console.log(`SSH User: ${host.ssh_user}`);
  console.log(`SSH Password: ${host.ssh_password}`);
});
```

---

## 📚 Use Cases

### Use Case 1: Alle Infrastruktur laden

**Szenario:** Master muss auf alle Infrastruktur-Objekte zugreifen

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

console.log(`Insgesamt ${infrastructure.length} Objekte geladen`);

infrastructure.forEach(host => {
  // z.B. Compliance-Check durchführen
  console.log(`Checking ${host.hostname}...`);
});
```

**Output:**
```
Insgesamt 15 Objekte geladen
Checking vm-prod-01...
Checking vm-prod-02...
Checking router-01...
...
```

---

### Use Case 2: Nur bestimmte Objekt-Typen

**Szenario:** Master braucht nur Devices (z.B. für Hardware-Audit)

```javascript
const devices = await $tools.workflow.call({
  name: 'Primitive: NetBox-Abfrage',
  parameters: {
    load_vms: false,
    load_lxcs: false,
    load_devices: true,
    filter_by_type: null,
    filter_by_ids: null,
    device_primary_ip_filter: true
  }
});

console.log(`${devices.length} Devices gefunden`);

devices.forEach(device => {
  console.log(`Device: ${device.hostname} (${device.ip})`);
});
```

---

### Use Case 3: Nach Typ filtern

**Szenario:** Master braucht nur VMs für Compliance-Scan

```javascript
const vms = await $tools.workflow.call({
  name: 'Primitive: NetBox-Abfrage',
  parameters: {
    load_vms: true,
    load_lxcs: true,
    load_devices: true,
    filter_by_type: 'vm',  // 👈 Nur VMs
    filter_by_ids: null,
    device_primary_ip_filter: true
  }
});

console.log(`${vms.length} VMs zum Scannen gefunden`);

vms.forEach(vm => {
  console.log(`VM: ${vm.hostname}`);
});
```

---

### Use Case 4: Nach spezifischen IDs abfragen

**Szenario:** Master muss spezifische Hosts verwalten

```javascript
const specificIds = [42, 100, 150];

const targetHosts = await $tools.workflow.call({
  name: 'Primitive: NetBox-Abfrage',
  parameters: {
    load_vms: true,
    load_lxcs: true,
    load_devices: true,
    filter_by_type: null,
    filter_by_ids: JSON.stringify(specificIds),  // 👈 Als JSON-String!
    device_primary_ip_filter: true
  }
});

console.log(`${targetHosts.length} Ziel-Hosts gefunden`);

targetHosts.forEach(host => {
  // SSH-Zugriff durchführen
  console.log(`Connecting to ${host.hostname} as ${host.ssh_user}@${host.ip}`);
});
```

---

### Use Case 5: Kombination: Nur Devices mit spezifischen IDs

**Szenario:** Master muss ein Subset von Devices verwalten

```javascript
const productionIds = [1, 2, 5];

const prodDevices = await $tools.workflow.call({
  name: 'Primitive: NetBox-Abfrage',
  parameters: {
    load_vms: false,
    load_lxcs: false,
    load_devices: true,
    filter_by_type: 'device',
    filter_by_ids: JSON.stringify(productionIds),
    device_primary_ip_filter: true
  }
});

console.log(`${prodDevices.length} Production-Devices gefunden`);
```

---

## 🔧 Fehlerbehandlung

### Szenario: Keine Treffer

```javascript
const result = await $tools.workflow.call({
  name: 'Primitive: NetBox-Abfrage',
  parameters: {
    load_vms: true,
    load_lxcs: true,
    load_devices: true,
    filter_by_type: 'vm',
    filter_by_ids: '[99999]',  // ID existiert nicht
    device_primary_ip_filter: true
  }
});

if (result.length === 0) {
  console.log('Keine Hosts gefunden!');
} else {
  console.log(`${result.length} Hosts gefunden`);
  result.forEach(host => {
    // Verarbeitung
  });
}
```

---

### Szenario: SSH-Passwort ist null

```javascript
const hosts = await $tools.workflow.call({
  name: 'Primitive: NetBox-Abfrage',
  parameters: {
    // ... Parameter
  }
});

hosts.forEach(host => {
  if (host.ssh_password === null) {
    console.log(`⚠️ ${host.hostname}: SSH-Passwort nicht gespeichert`);
    // Alternative Authentifizierung verwenden (SSH-Key, etc.)
  } else {
    console.log(`✅ ${host.hostname}: SSH-Passwort verfügbar`);
  }
});
```

---

## 🔀 Integration mit anderen Workflows

### Beispiel 1: Mit KI-Executer kombinieren

```javascript
// 1. Infrastructure laden
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

// 2. Befehle auf allen Hosts ausführen
for (const host of infrastructure) {
  const result = await $tools.workflow.call({
    name: 'Primitive: KI-Executer',
    parameters: {
      hostname: host.hostname,
      ip: host.ip,
      ssh_user: host.ssh_user,
      ssh_password: host.ssh_password,
      command: 'uname -a'
    }
  });

  console.log(`${host.hostname}: ${result}`);
}
```

---

### Beispiel 2: Mit Datenbank synchronisieren

```javascript
// 1. Infrastructure aus NetBox laden
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

// 2. In lokale DB speichern
const db = $db.getDb('hosts');
for (const host of infrastructure) {
  db.write({
    hostname: host.hostname,
    ip: host.ip,
    ssh_user: host.ssh_user,
    ssh_password: host.ssh_password,
    synced_at: new Date().toISOString()
  });
}

console.log(`${infrastructure.length} Hosts in DB synchronisiert`);
```

---

## 📊 Daten-Verarbeitung

### Transformation: IP-Listen erstellen

```javascript
const infrastructure = await $tools.workflow.call({
  name: 'Primitive: NetBox-Abfrage',
  parameters: {
    load_vms: true,
    load_lxcs: false,
    load_devices: false,
    filter_by_type: 'vm',
    filter_by_ids: null,
    device_primary_ip_filter: true
  }
});

// IP-Liste für Monitoring/Firewall-Konfiguration
const ips = infrastructure.map(host => host.ip);
console.log(ips); // ["10.1.1.100", "10.1.1.101", ...]

// CSV-Format für Export
const csv = infrastructure
  .map(h => `${h.hostname},${h.ip},${h.ssh_user}`)
  .join('\n');
console.log(csv);
```

---

### Transformation: Gruppieren nach Typ

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

// Gruppierung nach Typ (angenommen, wir haben ein "type" Feld intern)
const grouped = {
  vms: [],
  lxcs: [],
  devices: []
};

// In diesem Fall können wir nach separate Abfragen machen:
const vms = await $tools.workflow.call({
  name: 'Primitive: NetBox-Abfrage',
  parameters: {
    load_vms: true,
    load_lxcs: false,
    load_devices: false,
    filter_by_type: 'vm',
    filter_by_ids: null,
    device_primary_ip_filter: true
  }
});

const lxcs = await $tools.workflow.call({
  name: 'Primitive: NetBox-Abfrage',
  parameters: {
    load_vms: false,
    load_lxcs: true,
    load_devices: false,
    filter_by_type: 'lxc',
    filter_by_ids: null,
    device_primary_ip_filter: true
  }
});

const devices = await $tools.workflow.call({
  name: 'Primitive: NetBox-Abfrage',
  parameters: {
    load_vms: false,
    load_lxcs: false,
    load_devices: true,
    filter_by_type: 'device',
    filter_by_ids: null,
    device_primary_ip_filter: true
  }
});

console.log(`VMs: ${vms.length}, LXCs: ${lxcs.length}, Devices: ${devices.length}`);
```

---

## ⚙️ Best Practices

### 1. Filter verwenden für Performance
```javascript
// ❌ Ineffizient: Alle laden, dann filtern
const all = await $tools.workflow.call({
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

// ✅ Effizient: Mit Filter abfragen
const vms = await $tools.workflow.call({
  name: 'Primitive: NetBox-Abfrage',
  parameters: {
    load_vms: true,
    load_lxcs: false,
    load_devices: false,
    filter_by_type: 'vm',
    filter_by_ids: null,
    device_primary_ip_filter: true
  }
});
```

### 2. SSH-Passwörter sicher behandeln
```javascript
// ❌ Niemals Passwörter loggen
console.log(`Password: ${host.ssh_password}`);

// ✅ Sicher speichern
const secure = {
  hostname: host.hostname,
  ip: host.ip,
  ssh_user: host.ssh_user
  // ssh_password nicht speichern, nur bei Bedarf verwenden
};
```

### 3. Fehler beim Filter abfangen
```javascript
try {
  const result = await $tools.workflow.call({
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

  if (!Array.isArray(result)) {
    throw new Error('Unexpected response format');
  }

  console.log(`${result.length} Hosts gefunden`);
} catch (error) {
  console.error(`NetBox-Abfrage fehlgeschlagen: ${error.message}`);
}
```

---

## 📋 Checkliste für Integration

- [ ] Workflow ID `k8qsLh2kePMYWurk` im Master gespeichert
- [ ] Parameter-Objekt korrekt strukturiert
- [ ] `filter_by_ids` als JSON-String (nicht Array)
- [ ] Fehlerbehandlung für leere Results
- [ ] SSH-Passwörter sicher behandelt
- [ ] Logs zeigen erwartete Anzahl Hosts
- [ ] Workflow wurde in n8n erfolgreich deployt
- [ ] Permissions/Credentials sind konfiguriert

---

## 🔗 Referenzen

- **INPUT-SPEC.md** - Parameter-Details
- **OUTPUT-SPEC.md** - Output-Format
- **README.md** - Workflow-Überblick
- **EXAMPLES.md** - Code-Beispiele

---

**Version:** 2.0 | **Status:** ✅ Production Ready | **Last Updated:** 2026-01-24
