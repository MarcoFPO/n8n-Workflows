# Quick-Start-Guide - Mailserver

## Webmail nutzen

### 1. SnappyMail oeffnen
```
Browser: https://webmail.doehlercomputing.de/
```

### 2. Anmelden
```
Username: <stalwart-benutzername> (z.B. mdoehler)
Passwort: <stalwart-passwort>
```

### 3. Erste E-Mail schreiben
- "Compose" klicken
- An: `mdoehler@doehlercomputing.de`
- Betreff: "Test"
- Senden

## E-Mail-Clients einrichten

### Thunderbird / Outlook / Mail.app

| Einstellung | Wert |
|---|---|
| **IMAP-Server** | mail.doehlercomputing.de |
| **IMAP-Port** | 993 (SSL/TLS) |
| **SMTP-Server** | mail.doehlercomputing.de |
| **SMTP-Port** | 465 (SSL/TLS) oder 587 (STARTTLS) |
| **Benutzername** | Stalwart-Benutzername |
| **Authentifizierung** | Normal Password |

### POP3 (falls gewuenscht)

| Einstellung | Wert |
|---|---|
| **POP3-Server** | mail.doehlercomputing.de |
| **POP3-Port** | 995 (SSL/TLS) |

## Administration

### Stalwart Admin-Panel
```
Browser: https://mail.doehlercomputing.de/
Login:   admin / StalwartAdmin2026!
```

Hier koennen verwaltet werden:
- Benutzerkonten
- Domains
- Sieve-Filter
- Queues und Logs

## Services pruefen

```bash
# Alle relevanten Services
ssh root@10.1.1.100 "pct exec 121 -- systemctl status stalwart nginx postgresql php8.4-fpm offlineimap"
```

**Alle sollten "active (running)" sein.**

## Logs anschauen

```bash
# Stalwart Mail Logs
ssh root@10.1.1.100 "pct exec 121 -- tail -n 50 /opt/stalwart/logs/stalwart.log"

# Nginx Access-Logs
ssh root@10.1.1.100 "pct exec 121 -- tail -n 20 /var/log/nginx/access.log"

# OfflineIMAP Sync-Logs
ssh root@10.1.1.100 "pct exec 121 -- journalctl -u offlineimap -n 50"
```

## Troubleshooting

### Webmail laedt nicht
```bash
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart nginx php8.4-fpm"
```

### Mails kommen nicht an
```bash
# Stalwart-Logs pruefen
ssh root@10.1.1.100 "pct exec 121 -- tail -n 100 /opt/stalwart/logs/stalwart.log | grep -i error"

# Stalwart neu starten
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart stalwart"
```

### IMAP-Sync funktioniert nicht
```bash
# OfflineIMAP Status
ssh root@10.1.1.100 "pct exec 121 -- systemctl status offlineimap"

# OfflineIMAP neu starten
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart offlineimap"
```

### SSL-Zertifikat abgelaufen
```bash
ssh root@10.1.1.100 "pct exec 121 -- certbot renew"
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart nginx"
```

## Weitere Informationen

- Detailliertes Setup: [MAILSERVER-INSTALLATION.md](./MAILSERVER-INSTALLATION.md)
- Verwaltung: [ADMINISTRATION.md](./ADMINISTRATION.md)
- Probleme loesen: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- Monitoring: [MONITORING.md](./MONITORING.md)
