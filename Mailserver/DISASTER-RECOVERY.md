# Disaster Recovery - Mailserver

## Notfall-Szenarien

## Szenario 1: Stalwart Mail Server nicht funktionsfaehig

**Symptom**: Keine Mails, IMAP/SMTP nicht erreichbar

### 1. Status pruefen

```bash
ssh root@10.1.1.100 "pct exec 121 -- systemctl status stalwart"
ssh root@10.1.1.100 "pct exec 121 -- ss -tlnp | grep -E ':25|:993|:8080'"
```

### 2. Stalwart neu starten

```bash
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart stalwart"
```

### 3. Logs analysieren

```bash
ssh root@10.1.1.100 "pct exec 121 -- tail -n 100 /opt/stalwart/logs/stalwart.log"
```

### 4. Konfiguration aus Backup wiederherstellen

```bash
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    cp -r /opt/stalwart/etc /opt/stalwart/etc.broken
    cd / && tar -xzf /backups/mailserver/stalwart_config_DATUM.tar.gz
    systemctl restart stalwart
'"
```

### 5. Neu installieren (letzter Ausweg)

```bash
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    # Binary erneut herunterladen
    cd /tmp
    wget https://github.com/stalwartlabs/stalwart/releases/download/v0.15.5/stalwart-x86_64-unknown-linux-gnu.tar.gz
    tar -xzf stalwart-x86_64-unknown-linux-gnu.tar.gz
    cp stalwart /opt/stalwart/bin/stalwart
    chown stalwart:stalwart /opt/stalwart/bin/stalwart
    systemctl restart stalwart
'"
```

---

## Szenario 2: PostgreSQL-Datenbank beschaedigt

**Symptom**: Stalwart kann nicht starten, DB-Fehler in Logs

### 1. PostgreSQL-Status pruefen

```bash
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    systemctl status postgresql
    sudo -u postgres psql -c \"SELECT 1;\"
'"
```

### 2. PostgreSQL reparieren

```bash
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    systemctl restart postgresql
    sudo -u postgres psql -c \"SELECT pg_size_pretty(pg_database_size(\\\"stalwart_mail\\\"));\"
'"
```

### 3. Aus Backup wiederherstellen

```bash
# Stalwart stoppen
ssh root@10.1.1.100 "pct exec 121 -- systemctl stop stalwart"

# Datenbank neu erstellen
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    sudo -u postgres psql -c \"DROP DATABASE IF EXISTS stalwart_mail;\"
    sudo -u postgres psql -c \"CREATE DATABASE stalwart_mail OWNER stalwart;\"
'"

# Aus Backup wiederherstellen
gunzip -c /backups/mailserver/stalwart_db_DATUM.sql.gz | \
    ssh root@10.1.1.100 "pct exec 121 -- sudo -u postgres psql stalwart_mail"

# Stalwart starten
ssh root@10.1.1.100 "pct exec 121 -- systemctl start stalwart"
```

---

## Szenario 3: Nginx/Webmail nicht erreichbar

**Symptom**: https://webmail.doehlercomputing.de nicht erreichbar

### 1. Status pruefen

```bash
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    systemctl status nginx
    systemctl status php8.4-fpm
    nginx -t
'"
```

### 2. Nginx neu starten

```bash
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart nginx php8.4-fpm"
```

### 3. Konfiguration aus Backup

```bash
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    cp -r /etc/nginx /etc/nginx.broken
    cd / && tar -xzf /backups/mailserver/configs_DATUM.tar.gz etc/nginx
    nginx -t && systemctl restart nginx
'"
```

---

## Szenario 4: SSL-Zertifikate abgelaufen/beschaedigt

**Symptom**: Browser zeigt Zertifikatsfehler

### Sofortmassnahme

```bash
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    certbot renew --force-renewal
    systemctl restart nginx
    # Falls Stalwart eigene Zertifikate nutzt:
    systemctl restart stalwart
'"
```

### Zertifikate komplett neu erstellen

```bash
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    certbot certonly --nginx -d mail.doehlercomputing.de
    certbot certonly --nginx -d webmail.doehlercomputing.de
    systemctl restart nginx
'"
```

---

## Szenario 5: LXC-Container ausgefallen

**Symptom**: LXC 121 nicht erreichbar

### 1. Container-Status pruefen

```bash
ssh root@10.1.1.100 "pct status 121"
```

### 2. Container neu starten

```bash
ssh root@10.1.1.100 "pct start 121"

# Warten und pruefen
sleep 15
ssh root@10.1.1.100 "pct exec 121 -- systemctl status stalwart nginx postgresql php8.4-fpm offlineimap"
```

### 3. Container nicht startbar

```bash
# Logs pruefen
ssh root@10.1.1.100 "pct exec 121 -- journalctl -n 100"

# Dateisystem pruefen
ssh root@10.1.1.100 "pct exec 121 -- fsck -y /dev/pve/vm-121-disk-0"
```

### 4. Container komplett neu aufsetzen

Falls der Container nicht reparierbar ist:

1. Neuen LXC-Container erstellen (Debian 13)
2. Alle Komponenten installieren (siehe [MAILSERVER-INSTALLATION.md](./MAILSERVER-INSTALLATION.md))
3. Konfiguration aus Backup wiederherstellen
4. PostgreSQL-Datenbank aus Backup wiederherstellen
5. SSL-Zertifikate neu erstellen
6. Services starten und testen

---

## Szenario 6: Speicherplatz voll

**Symptom**: Services stuerzen ab, keine neuen Mails

### Sofortmassnahmen

```bash
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    # 1. Speicher pruefen
    df -h

    # 2. Groesste Verzeichnisse
    du -sh /* 2>/dev/null | sort -hr | head -10

    # 3. Logs bereinigen
    find /opt/stalwart/logs -name \"*.log\" -mtime +7 -delete
    journalctl --vacuum-time=7d
    rm -rf /var/www/snappymail/data/cache/*

    # 4. Speicher pruefen
    df -h
'"
```

### Container vergroessern (Proxmox)

```bash
ssh root@10.1.1.100 "pct resize 121 rootfs +10G"
ssh root@10.1.1.100 "pct exec 121 -- resize2fs /dev/pve/vm-121-disk-0"
```

---

## Szenario 7: OfflineIMAP-Sync kaputt

**Symptom**: Arcor/Gmail-Mails werden nicht mehr synchronisiert

### Diagnose und Fix

```bash
# 1. Status pruefen
ssh root@10.1.1.100 "pct exec 121 -- systemctl status offlineimap"
ssh root@10.1.1.100 "pct exec 121 -- journalctl -u offlineimap -n 50"

# 2. Lock-Dateien entfernen (falls vorhanden)
ssh root@10.1.1.100 "pct exec 121 -- rm -f /tmp/offlineimap.lock"

# 3. Cache zuruecksetzen
ssh root@10.1.1.100 "pct exec 121 -- rm -rf /opt/mailsync/.offlineimap"

# 4. Manueller Test-Sync
ssh root@10.1.1.100 "pct exec 121 -- offlineimap -c /opt/mailsync/.offlineimaprc -a Arcor -1"

# 5. Service neu starten
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart offlineimap"
```

---

## RTO und RPO

| Szenario | Recovery Time (RTO) | Recovery Point (RPO) |
|----------|------|------|
| Stalwart-Neustart | < 2 Minuten | N/A |
| PostgreSQL-Restore | < 15 Minuten | 24 Stunden (letztes Backup) |
| SSL-Zertifikat erneuern | < 5 Minuten | N/A |
| Container-Neustart | < 5 Minuten | N/A |
| Container neu aufsetzen | < 2 Stunden | 24 Stunden |
| Disk voll (bereinigen) | < 10 Minuten | N/A |

---

## Notfall-Kontakte

```
Administrator:    mdoehler
Proxmox Host:     10.1.1.100
Mail Server IP:   10.1.1.183
LXC Container:    121
Backup-Speicher:  /backups/mailserver/
Admin-Panel:      https://mail.doehlercomputing.de/
```

---

## Checkliste fuer Notfall-Recovery

**Bei Service-Ausfall:**
- [ ] Betroffenen Service identifizieren
- [ ] Logs analysieren
- [ ] Service neu starten
- [ ] Falls erfolglos: Konfiguration aus Backup
- [ ] Falls erfolglos: Komponente neu installieren
- [ ] Tests durchfuehren

**Bei Datenverlust:**
- [ ] Letztes gutes Backup identifizieren
- [ ] Backup-Integritaet pruefen
- [ ] Stalwart stoppen
- [ ] PostgreSQL-Restore durchfuehren
- [ ] Stalwart starten
- [ ] Verifizieren (Login, Mails vorhanden)

**Bei Container-Ausfall:**
- [ ] Container-Status pruefen (Proxmox)
- [ ] Container neu starten
- [ ] Alle Services pruefen
- [ ] Falls Container beschaedigt: neu aufsetzen + Restore

## Naechste Schritte

- [Backup & Restore](./BACKUP-RESTORE.md)
- [Monitoring](./MONITORING.md)
- [Administration](./ADMINISTRATION.md)
