# NetBox to vyOS IPv6 Route Sync - n8n Workflow

Automatischer Workflow zur Synchronisation von IPv6-Präfixen aus NetBox zu vyOS-Routern.

## 🎯 Workflow-Übersicht

```
┌─────────────────┐
│ Schedule Trigger│  ← Alle 5 Minuten
│  (5 Minuten)    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ NetBox API Call         │  ← GET /api/ipam/prefixes/?family=6
│ IPv6 Prefixes abrufen   │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Code Node               │  ← Transformation zu vyOS Commands
│ vyOS Commands generieren│     set protocols static route6 ...
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ SSH Node                │  ← Deployment via SSH
│ Deploy to vyOS          │     configure → commit → save
└─────────────────────────┘
```

## 📦 Installation

### 1. Workflow in n8n importieren

1. Öffnen Sie n8n in Ihrem Browser
2. Klicken Sie auf **"+"** → **"Import from File"**
3. Wählen Sie die Datei `netbox-vyos-workflow.json`
4. Workflow wird importiert

### 2. Credentials konfigurieren

#### NetBox API Token Credential

1. In n8n: **Settings** → **Credentials** → **"+ Add Credential"**
2. Credential Type: **"Header Auth"**
3. Name: `NetBox API Token`
4. Konfiguration:
   ```
   Name:  Authorization
   Value: Token IHR_NETBOX_API_TOKEN_HIER
   ```
5. Speichern

**NetBox API Token erstellen:**
- Loggen Sie sich in NetBox ein (http://10.1.1.104)
- Gehen Sie zu: **Admin** → **API Tokens** → **Add**
- User auswählen, Token generieren und kopieren

#### vyOS SSH Credential

1. In n8n: **Settings** → **Credentials** → **"+ Add Credential"**
2. Credential Type: **"SSH Password"**
3. Name: `vyOS SSH Credentials`
4. Konfiguration:
   ```
   Host: 10.2.1.1        # Ihre vyOS-Router-IP
   Port: 22
   Username: vyos
   Password: IHR_VYOS_PASSWORT
   ```
5. Speichern

### 3. Workflow anpassen

Öffnen Sie den Workflow und passen Sie folgende Werte an:

#### Node: "Generate vyOS Commands"

```javascript
// Zeile 6 anpassen:
const NEXT_HOP = '2001:db8::1';  // ← Ihre Gateway-IPv6-Adresse
```

#### Optional: NetBox API Filter anpassen

Im Node **"NetBox API - Get IPv6 Prefixes"** können Sie weitere Filter hinzufügen:

```
Query Parameters:
- family: 6
- status: active
- site: datacenter1        # Optional: Nur bestimmte Site
- tag: vyos-route          # Optional: Nur Prefixes mit Tag
```

### 4. Workflow aktivieren

1. Klicken Sie oben rechts auf den **Toggle** zum Aktivieren
2. Der Workflow läuft nun alle 5 Minuten automatisch

## 🧪 Testen

### Manueller Test

1. Öffnen Sie den Workflow
2. Klicken Sie auf **"Execute Workflow"** (oben rechts)
3. Prüfen Sie die Execution:
   - **NetBox API Node**: Zeigt abgerufene Prefixes
   - **Generate Commands Node**: Zeigt generierte vyOS-Befehle
   - **Deploy Node**: Zeigt SSH-Output

### Logs prüfen

- **Workflow Executions**: In n8n unter **"Executions"**
- Fehlerhafte Ausführungen werden rot markiert

## 📝 Beispiel-Output

### NetBox API Response
```json
{
  "results": [
    {
      "prefix": "2001:db8:1000::/48",
      "description": "Customer Network A",
      "status": { "value": "active" }
    },
    {
      "prefix": "2001:db8:2000::/48",
      "description": "Customer Network B",
      "status": { "value": "active" }
    }
  ]
}
```

### Generierte vyOS Commands
```
configure
set protocols static route6 2001:db8:1000::/48 next-hop 2001:db8::1
set protocols static route6 2001:db8:1000::/48 description 'Customer Network A'
set protocols static route6 2001:db8:2000::/48 next-hop 2001:db8::1
set protocols static route6 2001:db8:2000::/48 description 'Customer Network B'
commit
save
exit
```

## ⚙️ Konfiguration

### Schedule-Intervall ändern

Im Node **"Every 5 Minutes"**:
- Aktuell: Alle 5 Minuten
- Ändern: Klicken Sie auf den Node → **Rule** → **Minutes Interval**

### Mehrere vyOS-Router

Um mehrere Router zu unterstützen:

1. Duplizieren Sie den **"Deploy to vyOS"** Node
2. Erstellen Sie neue SSH-Credentials für jeden Router
3. Verbinden Sie alle Nodes mit dem **"Generate Commands"** Node

## 🔍 Troubleshooting

### "Invalid credentials" bei NetBox API

- Prüfen Sie den API Token in den Credentials
- Format muss sein: `Token XXXXX` (mit "Token " Präfix)

### SSH-Verbindung zu vyOS schlägt fehl

- Prüfen Sie IP-Adresse und Port
- Testen Sie SSH manuell: `ssh vyos@10.2.1.1`
- Prüfen Sie Firewall-Regeln

### Keine Prefixes gefunden

- Prüfen Sie NetBox-Filter (family=6, status=active)
- Testen Sie API manuell:
  ```bash
  curl -H "Authorization: Token XXX" \
       "http://10.1.1.104/api/ipam/prefixes/?family=6"
  ```

### vyOS Commit schlägt fehl

- Prüfen Sie ob NEXT_HOP valide ist
- Checken Sie vyOS-Logs: `show log`
- Testen Sie Commands manuell auf vyOS

## 🛠️ Erweiterte Features (Optional)

### Error Notifications

Fügen Sie einen **Error Trigger** hinzu:
1. Neuer Node: **"Error Trigger"**
2. Verbinden mit: **"Send Email"** oder **"Webhook"**

### Change Detection

Nur deployen wenn sich Prefixes geändert haben:
1. Fügen Sie einen **"Compare Datasets"** Node hinzu
2. Speichern Sie letzten State in n8n Static Data

### Backup vor Deployment

Vor dem Deploy ein Config-Backup erstellen:
1. SSH Node: `show configuration commands | cat`
2. Speichern in File oder Database

## 📚 Weitere Informationen

- **NetBox API Docs**: http://10.1.1.104/api/docs/
- **vyOS Docs**: https://docs.vyos.io/
- **n8n Docs**: https://docs.n8n.io/

## ✅ Checklist

- [ ] Workflow importiert
- [ ] NetBox API Token Credential erstellt
- [ ] vyOS SSH Credential erstellt
- [ ] NEXT_HOP in Code Node angepasst
- [ ] Manueller Test erfolgreich
- [ ] Workflow aktiviert
- [ ] Erste automatische Execution geprüft
