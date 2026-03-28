# 💡 Code-Beispiele – NetBox-Abfrage

**Workflow ID:** `k8qsLh2kePMYWurk`
**Version:** 2.0
**Status:** ✅ Production Ready

---

## 🎯 Überblick

Dieses Dokument enthält praktische Code-Beispiele für verschiedene Anwendungsfälle des **Primitive: NetBox-Abfrage** Workflows.

---

## 📝 Beispiel 1: Basis-Aufruf mit Logging

**Szenario:** Master ruft NetBox auf und loggt Ergebnis

```javascript
// Workflow aufrufen
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

// Logging
console.log(`NetBox-Abfrage abgeschlossen`);
console.log(`Insgesamt ${result.length} Hosts geladen`);
console.log(JSON.stringify(result, null, 2));

// Beispiel-Output:
// NetBox-Abfrage abgeschlossen
// Insgesamt 3 Hosts geladen
// [
//   {
//     "hostname": "vm-prod-01",
//     "ip": "10.1.1.100",
//     "ssh_user": "root",
//     "ssh_password": "secret123"
//   },
//   ...
// ]
```

---

## 📝 Beispiel 2: Nur Production-VMs

**Szenario:** Master braucht nur Production-VMs für Backup-Job

```javascript
const productionVms = await $tools.workflow.call({
  name: 'Primitive: NetBox-Abfrage',
  parameters: {
    load_vms: true,      // Nur VMs laden
    load_lxcs: false,    // LXCs ignorieren
    load_devices: false, // Devices ignorieren
    filter_by_type: 'vm',
    filter_by_ids: null,
    device_primary_ip_filter: true
  }
});

// Verarbeitung
console.log(`${productionVms.length} Production-VMs gefunden`);

productionVms.forEach(vm => {
  console.log(`- ${vm.hostname} (${vm.ip})`);
  // Backup-Script für jede VM ausführen
});

// Beispiel-Output:
// 5 Production-VMs gefunden
// - vm-prod-01 (10.1.1.100)
// - vm-prod-02 (10.1.1.101)
// - vm-prod-03 (10.1.1.102)
// - vm-prod-04 (10.1.1.103)
// - vm-prod-05 (10.1.1.104)
```

---

## 📝 Beispiel 3: Filter nach spezifischen IDs

**Szenario:** Master führt Patching für bestimmte Hosts durch

```javascript
// IDs der Hosts, die gepatcht werden sollen
const patchTargetIds = [42, 100, 150];

const patchTargets = await $tools.workflow.call({
  name: 'Primitive: NetBox-Abfrage',
  parameters: {
    load_vms: true,
    load_lxcs: true,
    load_devices: true,
    filter_by_type: null,
    filter_by_ids: JSON.stringify(patchTargetIds), // ⚠️ JSON.stringify!
    device_primary_ip_filter: true
  }
});

// Patching durchführen
console.log(`Starte Patching für ${patchTargets.length} Hosts`);

for (const host of patchTargets) {
  console.log(`Patching: ${host.hostname} (${host.ip})`);

  // SSH-Verbindung
  try {
    // Pseudo-Code für SSH-Ausführung
    const output = await executeSSH({
      host: host.ip,
      user: host.ssh_user,
      password: host.ssh_password,
      command: 'sudo apt update && sudo apt upgrade -y'
    });
    console.log(`✅ ${host.hostname} gepatcht`);
  } catch (error) {
    console.error(`❌ ${host.hostname} fehlgeschlagen: ${error.message}`);
  }
}

// Beispiel-Output:
// Starte Patching für 3 Hosts
// Patching: server-42 (192.168.1.42)
// ✅ server-42 gepatcht
// Patching: app-100 (192.168.1.100)
// ✅ app-100 gepatcht
// Patching: router-150 (10.1.1.150)
// ✅ router-150 gepatcht
```

---

## 📝 Beispiel 4: CSV-Export

**Szenario:** Master exportiert Infrastruktur in CSV-Format

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

// CSV-Header
const csvLines = ['hostname,ip,ssh_user,ssh_password_set'];

// CSV-Zeilen hinzufügen
infrastructure.forEach(host => {
  const passwordSet = host.ssh_password !== null ? 'true' : 'false';
  const line = `${host.hostname},${host.ip},${host.ssh_user},${passwordSet}`;
  csvLines.push(line);
});

const csvContent = csvLines.join('\n');
console.log(csvContent);

// CSV-Datei speichern (n8n API)
// await saveFile('infrastructure-export.csv', csvContent);

// Beispiel-Output:
// hostname,ip,ssh_user,ssh_password_set
// vm-prod-01,10.1.1.100,root,true
// vm-prod-02,10.1.1.101,root,false
// router-01,10.1.1.200,admin,true
// app-server,192.168.1.50,deploy,true
```

---

## 📝 Beispiel 5: Monitoring-Agentur Installation

**Szenario:** Master installiert Monitoring-Agent auf allen Hosts

```javascript
const infrastructure = await $tools.workflow.call({
  name: 'Primitive: NetBox-Abfrage',
  parameters: {
    load_vms: true,
    load_lxcs: true,
    load_devices: false, // Devices brauchen keinen Agent
    filter_by_type: null,
    filter_by_ids: null,
    device_primary_ip_filter: true
  }
});

// Agent-Installation Script
const agentInstallScript = `
#!/bin/bash
set -e

echo "Installing monitoring agent..."
curl -fsSL https://monitoring.example.com/install.sh | bash

# Konfiguration
mkdir -p /etc/monitoring-agent
cat > /etc/monitoring-agent/config.yaml << 'EOF'
server: monitoring.example.com:9090
hostname: $(hostname)
tags:
  environment: production
EOF

systemctl restart monitoring-agent
echo "Agent installed successfully"
`;

// Installation durchführen
let successCount = 0;
let failureCount = 0;

for (const host of infrastructure) {
  try {
    console.log(`Installing agent on ${host.hostname}...`);

    // Pseudo-Code für SSH
    const result = await executeSSH({
      host: host.ip,
      user: host.ssh_user,
      password: host.ssh_password,
      command: agentInstallScript
    });

    console.log(`✅ ${host.hostname}: Agent installed`);
    successCount++;
  } catch (error) {
    console.error(`❌ ${host.hostname}: ${error.message}`);
    failureCount++;
  }
}

console.log(`\nAgent Installation Summary:`);
console.log(`✅ Erfolgreich: ${successCount}`);
console.log(`❌ Fehler: ${failureCount}`);
```

---

## 📝 Beispiel 6: Nur Hosts mit SSH-Passwort

**Szenario:** Master muss nur auf Hosts mit Passwort-Auth zugreifen

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

// Filtern: nur Hosts mit SSH-Passwort
const hostsWithPassword = infrastructure.filter(host => host.ssh_password !== null);

console.log(`${hostsWithPassword.length} Hosts mit SSH-Passwort gefunden`);

hostsWithPassword.forEach(host => {
  console.log(`- ${host.hostname}: ${host.ssh_user}@${host.ip}`);
});

// Beispiel-Output:
// 8 Hosts mit SSH-Passwort gefunden
// - vm-prod-01: root@10.1.1.100
// - vm-prod-02: root@10.1.1.101
// - server-42: admin@192.168.1.42
// - app-100: deploy@192.168.1.100
// - router-150: admin@10.1.1.150
// - lxc-app-01: root@10.1.1.50
// - container-db: root@10.1.1.51
// - gateway: admin@10.1.1.1
```

---

## 📝 Beispiel 7: Health-Check Script

**Szenario:** Master führt Health-Checks auf allen Hosts durch

```javascript
// Infrastructure laden
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

// Health-Check durchführen
const healthChecks = [];

for (const host of infrastructure) {
  try {
    // Ping
    const pingResult = await executeSSH({
      host: host.ip,
      user: host.ssh_user,
      password: host.ssh_password,
      command: 'ping -c 1 8.8.8.8 && echo "ping_ok"'
    });

    // Disk-Usage
    const diskResult = await executeSSH({
      host: host.ip,
      user: host.ssh_user,
      password: host.ssh_password,
      command: 'df -h / | tail -1 | awk "{print $5}"'
    });

    // CPU-Load
    const cpuResult = await executeSSH({
      host: host.ip,
      user: host.ssh_user,
      password: host.ssh_password,
      command: 'uptime | awk -F"load average:" "{print $2}"'
    });

    healthChecks.push({
      hostname: host.hostname,
      ip: host.ip,
      status: 'healthy',
      ping: 'ok',
      disk_usage: diskResult.trim(),
      cpu_load: cpuResult.trim()
    });

    console.log(`✅ ${host.hostname}: Healthy`);
  } catch (error) {
    healthChecks.push({
      hostname: host.hostname,
      ip: host.ip,
      status: 'unhealthy',
      error: error.message
    });

    console.log(`❌ ${host.hostname}: ${error.message}`);
  }
}

console.log('\nHealth Check Results:');
console.log(JSON.stringify(healthChecks, null, 2));
```

---

## 📝 Beispiel 8: Gruppierung nach Subnet

**Szenario:** Master organisiert Hosts nach IP-Subnet

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

// Gruppierung nach Subnet (10.1.x.x, 10.2.x.x, etc.)
const grouped = {};

infrastructure.forEach(host => {
  const subnet = host.ip.split('.').slice(0, 3).join('.');
  if (!grouped[subnet]) {
    grouped[subnet] = [];
  }
  grouped[subnet].push(host);
});

// Ausgabe
Object.entries(grouped).forEach(([subnet, hosts]) => {
  console.log(`\nSubnet ${subnet}:`);
  hosts.forEach(host => {
    console.log(`  - ${host.hostname} (${host.ip})`);
  });
  console.log(`  Total: ${hosts.length} hosts`);
});

// Beispiel-Output:
// Subnet 10.1.1:
//   - vm-prod-01 (10.1.1.100)
//   - vm-prod-02 (10.1.1.101)
//   - router-01 (10.1.1.200)
//   Total: 3 hosts
//
// Subnet 10.2.1:
//   - server-db (10.2.1.50)
//   - app-app-01 (10.2.1.100)
//   Total: 2 hosts
//
// Subnet 192.168.1:
//   - device-switch (192.168.1.1)
//   - device-ap (192.168.1.10)
//   Total: 2 hosts
```

---

## 📝 Beispiel 9: Bestandsaufnahme in MongoDB

**Szenario:** Master speichert Infrastructure-Snapshot in MongoDB

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

// MongoDB-Integration (Pseudo-Code)
const mongoDb = await connectMongo('mongodb://localhost:27017/infrastructure');
const hostCollection = mongoDb.collection('hosts');

// Snapshot erstellen
const snapshot = {
  timestamp: new Date().toISOString(),
  host_count: infrastructure.length,
  hosts: infrastructure
};

// In DB speichern
await hostCollection.insertOne(snapshot);

console.log(`Snapshot gespeichert: ${snapshot.timestamp}`);
console.log(`Hosts: ${snapshot.host_count}`);

// Duplikate vermeiden (optional)
const retention = 30; // Tage
const thirtyDaysAgo = new Date();
thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - retention);

await hostCollection.deleteMany({
  timestamp: { $lt: thirtyDaysAgo.toISOString() }
});

console.log(`Alte Snapshots (>30 Tage) gelöscht`);
```

---

## 📝 Beispiel 10: Notification bei Veränderungen

**Szenario:** Master benachrichtigt bei Änderungen der Infrastruktur

```javascript
const currentInfrastructure = await $tools.workflow.call({
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

// Vorherige Infrastruktur-Liste laden (z.B. aus Cache)
const previousInfrastructure = await loadPreviousSnapshot();

// Vergleich
const currentHostnames = new Set(currentInfrastructure.map(h => h.hostname));
const previousHostnames = new Set(previousInfrastructure.map(h => h.hostname));

const newHosts = [...currentHostnames].filter(h => !previousHostnames.has(h));
const removedHosts = [...previousHostnames].filter(h => !currentHostnames.has(h));

// Notifications
if (newHosts.length > 0) {
  console.log(`🆕 Neue Hosts hinzugefügt:`);
  newHosts.forEach(hostname => {
    console.log(`  + ${hostname}`);
    // Slack-Nachricht senden, E-Mail verschicken, etc.
  });
}

if (removedHosts.length > 0) {
  console.log(`🗑️ Hosts entfernt:`);
  removedHosts.forEach(hostname => {
    console.log(`  - ${hostname}`);
    // Slack-Nachricht senden, E-Mail verschicken, etc.
  });
}

if (newHosts.length === 0 && removedHosts.length === 0) {
  console.log(`ℹ️ Keine Änderungen an der Infrastruktur`);
}

// Aktuellen Snapshot speichern
await saveCurrentSnapshot(currentInfrastructure);

// Beispiel-Output:
// 🆕 Neue Hosts hinzugefügt:
//   + vm-dev-01
//   + container-test-01
// 🗑️ Hosts entfernt:
//   - vm-old-server
// Snapshot aktualisiert
```

---

## 🔗 Referenzen

- **INPUT-SPEC.md** - Parameter-Details
- **OUTPUT-SPEC.md** - Output-Format
- **USAGE-GUIDE.md** - Integration & Best Practices
- **README.md** - Workflow-Überblick

---

**Version:** 2.0 | **Status:** ✅ Production Ready | **Last Updated:** 2026-01-24
