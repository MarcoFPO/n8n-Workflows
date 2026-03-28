# Upgrade & Updates - Mailserver

## System Updates (Debian)

### Verfuegbare Updates pruefen

```bash
ssh root@10.1.1.100 "pct exec 121 -- apt update && apt list --upgradable"
```

### Sicherheits-Updates installieren

```bash
ssh root@10.1.1.100 "pct exec 121 -- apt update && apt upgrade -y"
```

### Distro-Upgrade

```bash
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    apt update
    apt dist-upgrade -y
    apt autoremove -y
    apt autoclean -y
'"
```

## Stalwart Mail Server Update

### Aktuelle Version pruefen

```bash
ssh root@10.1.1.100 "pct exec 121 -- /opt/stalwart/bin/stalwart --version"
# Aktuell: v0.15.5 (Stand 2026-03-05, aktuellste Version)
```

### Neue Version pruefen

Releases: https://github.com/stalwartlabs/stalwart/releases

### Stalwart aktualisieren

```bash
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    # 1. Backup ZUERST
    sudo -u postgres pg_dump stalwart_mail > /opt/stalwart/backup-pre-upgrade.sql
    cp /opt/stalwart/bin/stalwart /opt/stalwart/bin/stalwart.\$(date +%Y%m%d).bak

    # 2. Stalwart stoppen
    systemctl stop stalwart

    # 3. Neue Version herunterladen (Beispiel fuer x86_64)
    cd /tmp
    wget https://github.com/stalwartlabs/stalwart/releases/download/vX.Y.Z/stalwart-x86_64-unknown-linux-gnu.tar.gz
    tar -xzf stalwart-x86_64-unknown-linux-gnu.tar.gz

    # 4. Binary ersetzen
    cp stalwart /opt/stalwart/bin/stalwart
    chown stalwart:stalwart /opt/stalwart/bin/stalwart

    # 5. Stalwart starten
    systemctl start stalwart

    # 6. Status pruefen
    systemctl status stalwart
    /opt/stalwart/bin/stalwart --version
'"
```

### Nach dem Stalwart-Update

```bash
# Logs auf Fehler pruefen
ssh root@10.1.1.100 "pct exec 121 -- tail -n 50 /opt/stalwart/logs/stalwart.log"

# Admin-Panel erreichbar?
curl -I https://mail.doehlercomputing.de/

# IMAP-Test
ssh root@10.1.1.100 "pct exec 121 -- ss -tlnp | grep :993"
```

## Nginx Update

```bash
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    # Backup
    cp -r /etc/nginx /etc/nginx.backup

    # Update
    apt update && apt upgrade nginx -y

    # Konfiguration validieren
    nginx -t

    # Neu starten
    systemctl restart nginx
'"
```

## PostgreSQL Update

### Minor Update (z.B. 17.x -> 17.y)

```bash
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    # Backup ZUERST
    sudo -u postgres pg_dump stalwart_mail | gzip > /tmp/stalwart_db_backup.sql.gz

    # Update
    apt update && apt upgrade postgresql -y

    # Neu starten
    systemctl restart postgresql

    # Status
    sudo -u postgres psql -c \"SELECT version();\"
'"
```

### Major Upgrade (z.B. 17 -> 18)

Erfordert `pg_upgrade`. Detailliert planen und vorher testen!

```bash
# 1. Neue Version installieren
apt install postgresql-18

# 2. Upgrade mit pg_upgrade
pg_upgrade \
    --old-datadir=/var/lib/postgresql/17/main \
    --new-datadir=/var/lib/postgresql/18/main \
    --old-bindir=/usr/lib/postgresql/17/bin \
    --new-bindir=/usr/lib/postgresql/18/bin

# 3. Port konfigurieren und alte Version deinstallieren
```

## PHP Update

```bash
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    apt update && apt upgrade php8.4-fpm php8.4-* -y
    systemctl restart php8.4-fpm
    systemctl restart nginx
'"
```

## SnappyMail Update

```bash
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    cd /tmp

    # Aktuelle Version herunterladen
    wget https://github.com/the-djmaze/snappymail/releases/download/vX.Y.Z/snappymail-X.Y.Z.tar.gz

    # Backup
    cp -r /var/www/snappymail /var/www/snappymail.backup

    # Update (data-Verzeichnis wird beibehalten)
    tar -xzf snappymail-X.Y.Z.tar.gz -C /var/www/snappymail --exclude=data

    # Berechtigungen setzen
    chown -R www-data:www-data /var/www/snappymail
'"
```

## Update-Strategie

### Pre-Update Checkliste

- [ ] Vollstaendiges Backup erstellen (PostgreSQL + Konfiguration)
- [ ] Aktuelle Service-Status dokumentieren
- [ ] Freien Speicherplatz ueberpruefen (min. 1 GB)
- [ ] Stalwart-Version notieren

### Update-Ablauf

1. **Backup erstellen**
   ```bash
   /opt/Projekte/Mailserver/backup.sh
   ```

2. **Services pruefen**
   ```bash
   ssh root@10.1.1.100 "pct exec 121 -- systemctl status stalwart nginx postgresql php8.4-fpm offlineimap"
   ```

3. **Update durchfuehren**
   ```bash
   ssh root@10.1.1.100 "pct exec 121 -- apt update && apt upgrade -y"
   ```

4. **Nach Update pruefen**
   ```bash
   ssh root@10.1.1.100 "pct exec 121 -- bash -c '
       echo \"=== Services ===\"
       systemctl status stalwart nginx postgresql php8.4-fpm offlineimap --no-pager
       echo \"=== Disk ===\"
       df -h /
       echo \"=== Stalwart Logs ===\"
       tail -n 20 /opt/stalwart/logs/stalwart.log
   '"
   ```

### Post-Update Checkliste

- [ ] Alle Services aktiv
- [ ] Webmail erreichbar (https://webmail.doehlercomputing.de/)
- [ ] Admin-Panel erreichbar (https://mail.doehlercomputing.de/)
- [ ] Login funktioniert
- [ ] IMAP/SMTP-Ports erreichbar
- [ ] Logs auf Fehler pruefen

## Rollback bei Problemen

### Stalwart zuruecksetzen

```bash
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    systemctl stop stalwart
    cp /opt/stalwart/bin/stalwart.0.15.4.bak /opt/stalwart/bin/stalwart
    systemctl start stalwart
'"
```

### PostgreSQL aus Backup zuruecksetzen

```bash
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    systemctl stop stalwart
    sudo -u postgres psql -c \"DROP DATABASE stalwart_mail;\"
    sudo -u postgres psql -c \"CREATE DATABASE stalwart_mail OWNER stalwart;\"
    sudo -u postgres psql stalwart_mail < /opt/stalwart/backup-pre-upgrade.sql
    systemctl start stalwart
'"
```

### Nginx zuruecksetzen

```bash
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    cp -r /etc/nginx.backup/* /etc/nginx/
    nginx -t && systemctl restart nginx
'"
```

## Automatisierte Sicherheits-Updates

### Unattended-Upgrades

```bash
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    apt install unattended-upgrades -y
    dpkg-reconfigure -plow unattended-upgrades
'"
```

## Hinweis: Stalwart APT-Repository

Stalwart ist als Binary installiert, **nicht via APT**. Das Stalwart-APT-Repository
(`/etc/apt/sources.list.d/stalwart.list`) wurde deaktiviert (`.disabled`), da:
- Der Repo-Host `repo.stalwart.email` nicht erreichbar war (Timeout)
- Updates ueber GitHub-Releases manuell eingespielt werden

Fuer Stalwart-Updates immer den manuellen Binary-Austausch verwenden (siehe Abschnitt oben).

## Update-Historie

| Datum | Pakete | Typ |
|-------|--------|-----|
| 2026-03-05 | PostgreSQL 17.7→17.8, GnuTLS, libpng, linux-libc-dev (13 Pakete) | Security |

## Naechste Schritte

- [Monitoring](./MONITORING.md)
- [Disaster Recovery](./DISASTER-RECOVERY.md)
- [Administration](./ADMINISTRATION.md)
