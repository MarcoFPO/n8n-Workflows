# 🚀 Projekt-Deployment-Regeln - KRITISCH

## ⚠️ **IMMER ANZUWENDENDE REGEL**

### 🎯 **Arbeitsumgebung: AUSSCHLIESSLICH 10.1.1.174**

**KRITISCHE ANWEISUNG**: Alle Entwicklung, Testing und Deployment erfolgt **AUSSCHLIESSLICH** auf dem Production-Server `10.1.1.174`.

```
🖥️ ARBEITSSERVER: 10.1.1.174 (aktienanalyse-lxc-120)
📍 NIEMALS lokal arbeiten - IMMER Remote auf 10.1.1.174
🔒 Diese Regel ist PERSISTENT und IMMER anzuwenden
```

## 📋 **Deployment-Spezifikationen**

### **Target-Server Details:**
- **IP-Adresse**: `10.1.1.174`
- **Container**: `aktienanalyse-lxc-120` (LXC)
- **Hardware**: 4 vCPU, 8GB RAM, 50GB Disk
- **Status**: Active, Production-Ready
- **Netzwerk**: 10.1.1.174/24

### **Service-Konfiguration:**
- **Frontend-Service**: Port 8000-8005
- **HTTPS-Access**: Port 443 (External)
- **systemd Services**: Alle 5 Services aktiv
- **Event-Store**: PostgreSQL + Redis

## 🔄 **Workflow-Regeln**

### **1. IMMER Remote-Zugriff verwenden**
```bash
# Alle Befehle auf 10.1.1.174 ausführen
ssh root@10.1.1.174
cd /opt/aktienanalyse-ökosystem/
```

### **2. NIEMALS lokale Entwicklung**
```
❌ VERBOTEN: /home/mdoehler/aktienanalyse-ökosystem/ (lokal)
✅ ERFORDERLICH: 10.1.1.174:/opt/aktienanalyse-ökosystem/ (remote)
```

### **3. Direkte Production-Deployment**
- Alle Änderungen direkt auf Production-Server
- Sofortige Live-Tests und Validation
- Kein lokaler Development-Server

## 🎯 **Implementation-Richtlinien**

### **Code-Änderungen:**
1. **SSH-Verbindung** zu 10.1.1.174 herstellen
2. **Direkte Bearbeitung** auf Production-Server
3. **Sofortige Tests** im Live-Environment
4. **Git-Commits** vom Production-Server

### **Service-Management:**
```bash
# Alle Service-Operationen auf 10.1.1.174
systemctl restart aktienanalyse-frontend.service
systemctl status aktienanalyse.target
```

### **Browser-Testing:**
```bash
# Frontend-Zugriff über Production-IP
https://10.1.1.174:443
http://10.1.1.174:8000
```

## 🔒 **Persistente Projekt-Konfiguration**

### **Automatische Anwendung:**
Diese Regel wird automatisch bei jedem Projekt-Zugriff angewendet:

```yaml
project: aktienanalyse-ökosystem
deployment_target: 10.1.1.174
local_development: DISABLED
remote_only: ENABLED
persistence: PERMANENT
```

### **Memory-Integration:**
```json
{
    "entity": "aktienanalyse-ökosystem-deployment",
    "rule": "ALWAYS_USE_10_1_1_174",
    "enforcement": "MANDATORY",
    "override": "NOT_ALLOWED"
}
```

## ⚡ **Sofortige Anwendung**

**AB SOFORT**: Jede Arbeit am aktienanalyse-ökosystem erfolgt **AUSSCHLIESSLICH** auf `10.1.1.174`.

### **Nächste Aktionen:**
1. SSH-Verbindung zu 10.1.1.174 herstellen
2. Projekt-Verzeichnis auf Remote-Server lokalisieren
3. Alle weiteren Operationen remote ausführen
4. Browser-Tests über 10.1.1.174 IP-Adresse

---

**🚨 KRITISCHE REGEL - IMMER EINHALTEN**  
**Server**: 10.1.1.174 (aktienanalyse-lxc-120)  
**Gültig**: PERMANENT für alle zukünftigen Arbeiten  
**Override**: NICHT ERLAUBT