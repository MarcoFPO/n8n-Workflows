# Troubleshooting - Mailserver

## Haeufige Probleme und Loesungen

### Problem: Webmail (SnappyMail) laedt nicht

**Ursachen**: Nginx nicht aktiv, PHP-FPM nicht aktiv, Netzwerkproblem

**Loesungsschritte**:

```bash
# 1. Nginx-Status pruefen
ssh root@10.1.1.100 "pct exec 121 -- systemctl status nginx"

# 2. PHP-FPM-Status pruefen
ssh root@10.1.1.100 "pct exec 121 -- systemctl status php8.4-fpm"

# 3. Services neu starten
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart nginx php8.4-fpm"

# 4. Nginx-Konfiguration validieren
ssh root@10.1.1.100 "pct exec 121 -- nginx -t"

# 5. Nginx-Fehler-Logs pruefen
ssh root@10.1.1.100 "pct exec 121 -- tail -n 30 /var/log/nginx/error.log"

# 6. HTTPS-Verbindung testen
curl -I https://webmail.doehlercomputing.de/
```

---

### Problem: Mails kommen nicht an

**Ursachen**: Stalwart nicht aktiv, SMTP-Port nicht erreichbar, Benutzer existiert nicht

**Loesungsschritte**:

```bash
# 1. Stalwart-Status pruefen
ssh root@10.1.1.100 "pct exec 121 -- systemctl status stalwart"

# 2. Falls inaktiv: neu starten
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart stalwart"

# 3. SMTP-Port pruefen
ssh root@10.1.1.100 "pct exec 121 -- ss -tlnp | grep :25"

# 4. Stalwart-Logs pruefen
ssh root@10.1.1.100 "pct exec 121 -- tail -n 100 /opt/stalwart/logs/stalwart.log | grep -i error"

# 5. Benutzer existiert? (via REST-API)
ssh root@10.1.1.100 "pct exec 121 -- curl -s -u admin:StalwartAdmin2026! http://localhost:8080/api/principal?limit=100"
```

---

### Problem: Login funktioniert nicht

**Ursachen**: Falsches Passwort, Benutzer nicht in Stalwart angelegt, Stalwart nicht aktiv

**Loesungsschritte**:

```bash
# 1. Stalwart laeuft?
ssh root@10.1.1.100 "pct exec 121 -- systemctl status stalwart"

# 2. IMAP-Port erreichbar?
ssh root@10.1.1.100 "pct exec 121 -- ss -tlnp | grep :993"

# 3. Stalwart-Logs auf Auth-Fehler pruefen
ssh root@10.1.1.100 "pct exec 121 -- grep -i 'auth' /opt/stalwart/logs/stalwart.log | tail -20"

# 4. Benutzer im Admin-Panel pruefen
# Browser: https://mail.doehlercomputing.de/
# Login: admin / StalwartAdmin2026!
# Accounts -> Benutzer suchen
```

---

### Problem: E-Mail kann nicht versendet werden

**Ursachen**: SMTP-Port blockiert, Stalwart nicht erreichbar, Authentifizierung fehlerhaft

**Loesungsschritte**:

```bash
# 1. Stalwart laeuft?
ssh root@10.1.1.100 "pct exec 121 -- systemctl status stalwart"

# 2. SMTP-Ports pruefen
ssh root@10.1.1.100 "pct exec 121 -- ss -tlnp | grep -E ':25|:465|:587'"

# 3. Stalwart-Logs pruefen
ssh root@10.1.1.100 "pct exec 121 -- grep -i 'smtp\|send\|queue' /opt/stalwart/logs/stalwart.log | tail -30"

# 4. SMTP-Test
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    echo -e \"EHLO test\nQUIT\" | nc -w5 localhost 25
'"
```

---

### Problem: OfflineIMAP synchronisiert nicht

**Ursachen**: Service gestoppt, Remote-Server nicht erreichbar, Credentials falsch

**Loesungsschritte**:

```bash
# 1. Status pruefen
ssh root@10.1.1.100 "pct exec 121 -- systemctl status offlineimap"

# 2. Logs pruefen
ssh root@10.1.1.100 "pct exec 121 -- journalctl -u offlineimap -n 50"

# 3. Manuellen Sync-Test
ssh root@10.1.1.100 "pct exec 121 -- offlineimap -c /opt/mailsync/.offlineimaprc -a Arcor -1"

# 4. Service neu starten
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart offlineimap"

# 5. Konfiguration pruefen
ssh root@10.1.1.100 "pct exec 121 -- cat /opt/mailsync/.offlineimaprc"
```

---

### Problem: PostgreSQL-Verbindung fehlgeschlagen

**Ursachen**: PostgreSQL nicht aktiv, Berechtigungen falsch

**Loesungsschritte**:

```bash
# 1. PostgreSQL-Status
ssh root@10.1.1.100 "pct exec 121 -- systemctl status postgresql"

# 2. Falls inaktiv: neu starten
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart postgresql"

# 3. Verbindung testen
ssh root@10.1.1.100 "pct exec 121 -- sudo -u postgres psql -c 'SELECT 1;'"

# 4. Stalwart-DB pruefen
ssh root@10.1.1.100 "pct exec 121 -- sudo -u postgres psql -c \"SELECT pg_size_pretty(pg_database_size('stalwart_mail'));\""

# 5. PostgreSQL-Logs
ssh root@10.1.1.100 "pct exec 121 -- tail -n 30 /var/log/postgresql/postgresql-17-main.log"
```

---

### Problem: SSL-Zertifikat abgelaufen

**Ursachen**: Certbot-Renewal fehlgeschlagen

**Loesungsschritte**:

```bash
# 1. Zertifikate pruefen
ssh root@10.1.1.100 "pct exec 121 -- certbot certificates"

# 2. Manuell erneuern
ssh root@10.1.1.100 "pct exec 121 -- certbot renew"

# 3. Nginx neu starten
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart nginx"

# 4. Stalwart-Zertifikate aktualisieren (falls noetig)
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart stalwart"
```

---

### Problem: Speicherplatz voll

**Ursachen**: Grosse Datenbank, Logs nicht rotiert, Mail-Volumen

**Loesungsschritte**:

```bash
# 1. Disk-Space pruefen
ssh root@10.1.1.100 "pct exec 121 -- df -h"

# 2. Groesste Verzeichnisse finden
ssh root@10.1.1.100 "pct exec 121 -- du -sh /* 2>/dev/null | sort -hr | head -10"

# 3. Stalwart-Logs pruefen
ssh root@10.1.1.100 "pct exec 121 -- du -sh /opt/stalwart/logs/"

# 4. Alte Logs loeschen
ssh root@10.1.1.100 "pct exec 121 -- find /opt/stalwart/logs -name '*.log' -mtime +30 -delete"

# 5. PostgreSQL VACUUM
ssh root@10.1.1.100 "pct exec 121 -- sudo -u postgres vacuumdb --all --analyze"

# 6. Journal-Logs bereinigen
ssh root@10.1.1.100 "pct exec 121 -- journalctl --vacuum-time=30d"

# 7. SnappyMail-Cache leeren
ssh root@10.1.1.100 "pct exec 121 -- rm -rf /var/www/snappymail/data/cache/*"
```

---

### Problem: Stalwart Admin-Panel nicht erreichbar

**Ursachen**: Nginx-Proxy-Fehler, Stalwart nicht auf Port 8080

**Loesungsschritte**:

```bash
# 1. Stalwart laeuft?
ssh root@10.1.1.100 "pct exec 121 -- systemctl status stalwart"

# 2. Port 8080 aktiv?
ssh root@10.1.1.100 "pct exec 121 -- ss -tlnp | grep :8080"

# 3. Nginx-Proxy testen
ssh root@10.1.1.100 "pct exec 121 -- curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/"

# 4. Nginx-Error-Log
ssh root@10.1.1.100 "pct exec 121 -- tail -n 20 /var/log/nginx/error.log"

# 5. Services neu starten
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart stalwart nginx"
```

---

## Logs analysieren

### Wichtige Log-Dateien

| Log | Pfad | Inhalt |
|---|---|---|
| Stalwart | `/opt/stalwart/logs/stalwart.log` | Mail-Server (SMTP, IMAP, Auth) |
| Nginx Access | `/var/log/nginx/access.log` | HTTP-Requests |
| Nginx Error | `/var/log/nginx/error.log` | Nginx-Fehler |
| PostgreSQL | `/var/log/postgresql/postgresql-17-main.log` | DB-Meldungen |
| OfflineIMAP | `journalctl -u offlineimap` | IMAP-Sync |
| PHP-FPM | `/var/log/php8.4-fpm.log` | PHP-Fehler |

### Log-Filterung

```bash
# Stalwart-Fehler
ssh root@10.1.1.100 "pct exec 121 -- grep -i error /opt/stalwart/logs/stalwart.log | tail -20"

# Nginx-Fehler
ssh root@10.1.1.100 "pct exec 121 -- tail -n 50 /var/log/nginx/error.log"

# PostgreSQL-Fehler
ssh root@10.1.1.100 "pct exec 121 -- grep -i 'error\|fatal' /var/log/postgresql/postgresql-17-main.log | tail -20"

# Live-Monitoring (Stalwart)
ssh root@10.1.1.100 "pct exec 121 -- tail -f /opt/stalwart/logs/stalwart.log"
```

---

## System-Diagnose

### Automatische Diagnose

```bash
#!/bin/bash
# /opt/Projekte/Mailserver/diagnose.sh

CONTAINER_ID="121"
PROXMOX_HOST="10.1.1.100"

echo "=== Mailserver Diagnose ==="
echo "Zeitstempel: $(date)"
echo ""

echo "=== Service Status ==="
for svc in stalwart nginx postgresql php8.4-fpm offlineimap; do
    status=$(ssh root@${PROXMOX_HOST} "pct exec ${CONTAINER_ID} -- systemctl is-active ${svc}")
    if [ "$status" = "active" ]; then
        echo "OK   $svc"
    else
        echo "FAIL $svc ($status)"
    fi
done

echo ""
echo "=== System-Ressourcen ==="
ssh root@${PROXMOX_HOST} "pct exec ${CONTAINER_ID} -- bash -c 'uptime; echo; free -h; echo; df -h /'"

echo ""
echo "=== Letzte Stalwart-Fehler ==="
ssh root@${PROXMOX_HOST} "pct exec ${CONTAINER_ID} -- grep -i error /opt/stalwart/logs/stalwart.log | tail -5"

echo ""
echo "=== Ports ==="
ssh root@${PROXMOX_HOST} "pct exec ${CONTAINER_ID} -- ss -tlnp | grep -E ':25|:443|:993|:8080'"

echo ""
echo "=== End Diagnose ==="
```

---

## Naechste Schritte

- [Monitoring](./MONITORING.md)
- [Administration](./ADMINISTRATION.md)
- [Backup & Restore](./BACKUP-RESTORE.md)
