# Backup & Restore - Mailserver

## Backup-Strategie

### Zu sichernde Komponenten

1. **PostgreSQL Datenbank** (kritisch)
   - Stalwart: Accounts, Mails, Volltextsuche, Konfiguration
   - Datenbank: `stalwart_mail`

2. **Stalwart-Konfiguration** (kritisch)
   - `/opt/stalwart/etc/config.toml`
   - `/opt/stalwart/etc/dkim-doehlercomputing.key`
   - `/opt/stalwart/etc/dkim-doehlercomputing.pub`
   - `/opt/stalwart/etc/cert.pem` / `key.pem`

3. **Nginx-Konfiguration**
   - `/etc/nginx/sites-enabled/`

4. **SSL-Zertifikate**
   - `/etc/letsencrypt/`

5. **OfflineIMAP-Konfiguration**
   - `/opt/mailsync/.offlineimaprc`
   - `/opt/mailsync/helpers.py`
   - `/opt/mailsync/imap_sort.py`

6. **SnappyMail**
   - `/var/www/snappymail/data/` (Konfiguration und Benutzerdaten)

### Backup-Haeufigkeiten

| Komponente | Haeufigkeit | Aufbewahrung |
|------------|-----------|--------------|
| PostgreSQL Datenbank | Taeglich | 30 Tage |
| Stalwart-Konfiguration | Woechentlich | 12 Monate |
| SSL-Zertifikate | Monatlich | 12 Monate |
| OfflineIMAP-Konfiguration | Monatlich | 12 Monate |

## Automatisiertes Backup-Skript

```bash
# Datei: /opt/Projekte/Mailserver/backup.sh
#!/bin/bash

BACKUP_DIR="/backups/mailserver"
CONTAINER_ID="121"
PROXMOX_HOST="10.1.1.100"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

mkdir -p $BACKUP_DIR

echo "=== Mailserver Backup gestartet: $DATE ==="

# 1. PostgreSQL Datenbank sichern
echo "Sicherung PostgreSQL..."
ssh root@${PROXMOX_HOST} "pct exec ${CONTAINER_ID} -- sudo -u postgres pg_dump stalwart_mail" \
    | gzip > $BACKUP_DIR/stalwart_db_${DATE}.sql.gz

if [ $? -eq 0 ]; then
    echo "OK  PostgreSQL gesichert"
else
    echo "FAIL PostgreSQL-Backup fehlgeschlagen"
fi

# 2. Stalwart-Konfiguration sichern
echo "Sicherung Stalwart-Konfiguration..."
ssh root@${PROXMOX_HOST} "pct exec ${CONTAINER_ID} -- tar -czf - \
    /opt/stalwart/etc/ 2>/dev/null" \
    > $BACKUP_DIR/stalwart_config_${DATE}.tar.gz

if [ $? -eq 0 ]; then
    echo "OK  Stalwart-Konfiguration gesichert"
else
    echo "FAIL Stalwart-Config-Backup fehlgeschlagen"
fi

# 3. Nginx + SSL + OfflineIMAP + SnappyMail sichern
echo "Sicherung weitere Konfigurationen..."
ssh root@${PROXMOX_HOST} "pct exec ${CONTAINER_ID} -- tar -czf - \
    /etc/nginx/sites-enabled \
    /etc/letsencrypt \
    /opt/mailsync \
    /var/www/snappymail/data 2>/dev/null" \
    > $BACKUP_DIR/configs_${DATE}.tar.gz

if [ $? -eq 0 ]; then
    echo "OK  Konfigurationen gesichert"
else
    echo "FAIL Konfigurations-Backup fehlgeschlagen"
fi

# 4. Alte Backups loeschen
echo "Loesche alte Backups..."
find $BACKUP_DIR -type f -mtime +$RETENTION_DAYS -delete

echo "=== Backup abgeschlossen ==="
ls -lh $BACKUP_DIR | tail -10
```

### Backup in Cron schedulen

```bash
# Taegliches Backup um 02:00 Uhr
0 2 * * * /opt/Projekte/Mailserver/backup.sh >> /var/log/mailserver-backup.log 2>&1
```

## Manuelles Backup

### PostgreSQL allein

```bash
# Komplettes Datenbank-Backup
ssh root@10.1.1.100 "pct exec 121 -- sudo -u postgres pg_dump stalwart_mail" \
    | gzip > stalwart_db_$(date +%Y%m%d).sql.gz

# Nur Schema (ohne Daten)
ssh root@10.1.1.100 "pct exec 121 -- sudo -u postgres pg_dump --schema-only stalwart_mail" \
    > stalwart_schema_$(date +%Y%m%d).sql
```

### Stalwart-Konfiguration allein

```bash
ssh root@10.1.1.100 "pct exec 121 -- tar -czf - /opt/stalwart/etc/" \
    > stalwart_config_$(date +%Y%m%d).tar.gz
```

### Alles zusammen

```bash
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    sudo -u postgres pg_dump stalwart_mail | gzip > /tmp/db.sql.gz &&
    tar -czf /tmp/stalwart-config.tar.gz /opt/stalwart/etc/ &&
    tar -czf /tmp/all-configs.tar.gz /etc/nginx/sites-enabled /etc/letsencrypt /opt/mailsync /var/www/snappymail/data
'" && \
    scp root@10.1.1.100:/tmp/db.sql.gz . && \
    scp root@10.1.1.100:/tmp/stalwart-config.tar.gz . && \
    scp root@10.1.1.100:/tmp/all-configs.tar.gz .
```

## Restore (Wiederherstellung)

### PostgreSQL wiederherstellen

```bash
# Backup-Datei in LXC kopieren
scp stalwart_db_20260305.sql.gz root@10.1.1.100:/tmp/

# Stalwart stoppen (damit DB nicht gesperrt ist)
ssh root@10.1.1.100 "pct exec 121 -- systemctl stop stalwart"

# Datenbank droppen und neu erstellen
ssh root@10.1.1.100 "pct exec 121 -- sudo -u postgres psql -c 'DROP DATABASE stalwart_mail;'"
ssh root@10.1.1.100 "pct exec 121 -- sudo -u postgres psql -c 'CREATE DATABASE stalwart_mail OWNER stalwart;'"

# Aus Backup wiederherstellen
ssh root@10.1.1.100 "pct exec 121 -- bash -c 'gunzip -c /tmp/stalwart_db_20260305.sql.gz | sudo -u postgres psql stalwart_mail'"

# Stalwart wieder starten
ssh root@10.1.1.100 "pct exec 121 -- systemctl start stalwart"

echo "PostgreSQL wiederhergestellt"
```

### Stalwart-Konfiguration wiederherstellen

```bash
# Aktuelle Konfiguration sichern
ssh root@10.1.1.100 "pct exec 121 -- cp -r /opt/stalwart/etc /opt/stalwart/etc.backup"

# Aus Backup wiederherstellen
scp stalwart_config_20260305.tar.gz root@10.1.1.100:/tmp/
ssh root@10.1.1.100 "pct exec 121 -- bash -c 'cd / && tar -xzf /tmp/stalwart_config_20260305.tar.gz'"

# Stalwart neu starten
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart stalwart"
```

### Nginx/SSL/OfflineIMAP wiederherstellen

```bash
scp configs_20260305.tar.gz root@10.1.1.100:/tmp/
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    cd / && tar -xzf /tmp/configs_20260305.tar.gz
    systemctl restart nginx
    systemctl restart offlineimap
'"
```

## Backup-Ueberpruefung

### Backup-Integritaet testen

```bash
# SQL-Dump pruefen
gzip -t stalwart_db_20260305.sql.gz && echo "OK  Dump intakt" || echo "FAIL Dump beschaedigt"

# TAR-Archive pruefen
tar -tzf stalwart_config_20260305.tar.gz > /dev/null && echo "OK  Archiv intakt" || echo "FAIL Archiv beschaedigt"
```

### Backup-Groessen ueberpruefen

```bash
ls -lh *.sql.gz *.tar.gz
du -sh /backups/mailserver/*
```

## Backup-Verzeichnis-Struktur

```
/backups/mailserver/
+-- stalwart_db_20260305_020000.sql.gz       (taeglich, PostgreSQL)
+-- stalwart_config_20260305_020000.tar.gz   (woechentlich)
+-- configs_20260305_020000.tar.gz           (woechentlich)
+-- ...
```

## Haeufig gestellte Fragen

### Q: Wie lange sollen Backups aufbewahrt werden?
**A:** Mindestens 30 Tage. Fuer kritische Systeme: 90+ Tage.

### Q: Kann ich einzelne E-Mails wiederherstellen?
**A:** Ja, ueber einen PostgreSQL-Restore der gesamten DB. Stalwart speichert Mails in der Datenbank.

### Q: Wie schnell ist ein Restore?
**A:** PostgreSQL-Restore: ~2-5 Minuten | Konfiguration: ~1 Minute | Gesamt: ~10 Minuten

## Naechste Schritte

- [Monitoring einrichten](./MONITORING.md)
- [Disaster Recovery](./DISASTER-RECOVERY.md)
- [Administration](./ADMINISTRATION.md)
