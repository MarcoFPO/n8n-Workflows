# Monitoring & Health Checks - Mailserver

## Service-Status pruefen

### Alle Services auf einen Blick

```bash
ssh root@10.1.1.100 "pct exec 121 -- systemctl status stalwart nginx postgresql php8.4-fpm offlineimap --no-pager"
```

### Einzelne Services

```bash
# Stalwart Mail Server
ssh root@10.1.1.100 "pct exec 121 -- systemctl status stalwart"

# Nginx
ssh root@10.1.1.100 "pct exec 121 -- systemctl status nginx"

# PostgreSQL
ssh root@10.1.1.100 "pct exec 121 -- systemctl status postgresql"

# PHP-FPM
ssh root@10.1.1.100 "pct exec 121 -- systemctl status php8.4-fpm"

# OfflineIMAP
ssh root@10.1.1.100 "pct exec 121 -- systemctl status offlineimap"
```

## Port-Tests

```bash
# SMTP (25)
ssh root@10.1.1.100 "pct exec 121 -- ss -tlnp | grep :25"

# IMAP (143/993)
ssh root@10.1.1.100 "pct exec 121 -- ss -tlnp | grep -E ':143|:993'"

# HTTPS (443)
ssh root@10.1.1.100 "pct exec 121 -- ss -tlnp | grep :443"

# Stalwart Admin (8080)
ssh root@10.1.1.100 "pct exec 121 -- ss -tlnp | grep :8080"
```

## Zabbix-Integration

Zabbix Agent ist aktiv und meldet an Zabbix Server `10.1.1.103`.

```bash
# Zabbix Agent Status
ssh root@10.1.1.100 "pct exec 121 -- systemctl status zabbix-agent"

# Konfiguration
ssh root@10.1.1.100 "pct exec 121 -- grep -E '^Server|^Hostname' /etc/zabbix/zabbix_agentd.conf"
```

### Empfohlene Zabbix-Items

```
proc.num[stalwart]        - Stalwart-Prozess laeuft
proc.num[nginx]           - Nginx-Prozess laeuft
proc.num[postgres]        - PostgreSQL-Prozess laeuft
proc.num[offlineimap]     - OfflineIMAP-Prozess laeuft
net.tcp.listen[25]        - SMTP erreichbar
net.tcp.listen[993]       - IMAPS erreichbar
net.tcp.listen[443]       - HTTPS erreichbar
vfs.fs.size[/,used]       - Disk-Usage
```

## Logs

### Log-Dateien Uebersicht

| Log | Pfad | Inhalt |
|---|---|---|
| Stalwart | `/opt/stalwart/logs/stalwart.log` | Mail-Server (SMTP, IMAP, Auth) |
| Nginx Access | `/var/log/nginx/access.log` | HTTP-Requests |
| Nginx Error | `/var/log/nginx/error.log` | Nginx-Fehler |
| PostgreSQL | `/var/log/postgresql/postgresql-17-main.log` | DB-Meldungen |
| OfflineIMAP | `journalctl -u offlineimap` | IMAP-Sync |
| PHP-FPM | `/var/log/php8.4-fpm.log` | PHP-Fehler |

### Logs anschauen

```bash
# Stalwart (letzte 50 Zeilen)
ssh root@10.1.1.100 "pct exec 121 -- tail -n 50 /opt/stalwart/logs/stalwart.log"

# Stalwart Fehler
ssh root@10.1.1.100 "pct exec 121 -- grep -i error /opt/stalwart/logs/stalwart.log | tail -20"

# OfflineIMAP
ssh root@10.1.1.100 "pct exec 121 -- journalctl -u offlineimap -n 50"

# Nginx
ssh root@10.1.1.100 "pct exec 121 -- tail -n 20 /var/log/nginx/error.log"

# Live-Monitoring
ssh root@10.1.1.100 "pct exec 121 -- tail -f /opt/stalwart/logs/stalwart.log"
```

## Speicher & Ressourcen

### Festplattenplatz

```bash
ssh root@10.1.1.100 "pct exec 121 -- df -h"
# Aktuell: 50 GB Disk, ~5.6 GB belegt (~12%)
```

### RAM & CPU

```bash
# RAM
ssh root@10.1.1.100 "pct exec 121 -- free -h"
# Aktuell: 4 GB RAM, ~470 MB belegt

# CPU-Last
ssh root@10.1.1.100 "pct exec 121 -- uptime"

# Top-Prozesse
ssh root@10.1.1.100 "pct exec 121 -- ps aux --sort=-%mem | head -10"
```

### Datenbank-Groesse

```bash
ssh root@10.1.1.100 "pct exec 121 -- sudo -u postgres psql -c \"SELECT pg_size_pretty(pg_database_size('stalwart_mail'));\""
```

## SSL-Zertifikate ueberwachen

```bash
# Ablaufdaten pruefen
ssh root@10.1.1.100 "pct exec 121 -- certbot certificates"

# Aktuell:
# mail.doehlercomputing.de    -> Ablauf 2026-05-16
# webmail.doehlercomputing.de -> Ablauf 2026-05-19
```

## Health-Check-Skript

```bash
#!/bin/bash
# /opt/Projekte/Mailserver/check-health.sh

CONTAINER_ID="121"
PROXMOX_HOST="10.1.1.100"

check_service() {
    local service=$1
    local status=$(ssh root@${PROXMOX_HOST} "pct exec ${CONTAINER_ID} -- systemctl is-active ${service}")
    if [ "$status" = "active" ]; then
        echo "OK  $service"
        return 0
    else
        echo "FAIL $service"
        return 1
    fi
}

echo "=== Mailserver Health Check ==="
echo "Zeitstempel: $(date)"
echo ""

FAILED=0
check_service "stalwart"      || FAILED=$((FAILED+1))
check_service "nginx"         || FAILED=$((FAILED+1))
check_service "postgresql"    || FAILED=$((FAILED+1))
check_service "php8.4-fpm"    || FAILED=$((FAILED+1))
check_service "offlineimap"   || FAILED=$((FAILED+1))
check_service "zabbix-agent"  || FAILED=$((FAILED+1))

echo ""
if [ $FAILED -eq 0 ]; then
    echo "Alle Services aktiv"
    exit 0
else
    echo "$FAILED Service(s) inaktiv"
    exit 1
fi
```

## Monitoring-Checkliste

**Taeglich:**
- [ ] Services aktiv (stalwart, nginx, postgresql, php8.4-fpm, offlineimap)
- [ ] Stalwart-Logs auf Fehler pruefen
- [ ] Speicherplatz > 20% frei

**Woechentlich:**
- [ ] SSL-Zertifikat-Ablauf pruefen
- [ ] OfflineIMAP-Sync laeuft korrekt
- [ ] Datenbank-Groesse pruefen

**Monatlich:**
- [ ] PostgreSQL VACUUM
- [ ] Alte Logs loeschen
- [ ] Updates verfuegbar?

## Naechste Schritte

- [Backup einrichten](./BACKUP-RESTORE.md)
- [Troubleshooting](./TROUBLESHOOTING.md)
- [Upgrades durchfuehren](./UPGRADES.md)
