# Verwaltungshandbuch - Mailserver

## Benutzer-Verwaltung

Benutzer werden ueber das **Stalwart Admin-Panel** verwaltet:

```
URL:   https://mail.doehlercomputing.de/
Login: admin / StalwartAdmin2026!
```

Im Admin-Panel koennen Benutzer angelegt, geaendert und geloescht werden.
Stalwart nutzt ein internes Directory (in PostgreSQL gespeichert), keine Unix-Accounts mehr.

### Benutzer auf System-Ebene

Einige Unix-Accounts existieren noch auf dem LXC fuer Legacy-Zwecke:

```bash
ssh root@10.1.1.100 "pct exec 121 -- ls /home/"
# admin, claude, egon, mdoehler, n8n, testuser
```

## Service-Verwaltung

### Aktive Services

| Service | Funktion | Systemd-Unit |
|---|---|---|
| Stalwart | SMTP/IMAP/POP3/Sieve | `stalwart.service` |
| Nginx | Reverse Proxy + SSL | `nginx.service` |
| PostgreSQL | Datenbank | `postgresql.service` |
| PHP-FPM | SnappyMail Backend | `php8.4-fpm.service` |
| OfflineIMAP | IMAP-Sync | `offlineimap.service` |
| Zabbix Agent | Monitoring | `zabbix-agent.service` |

### Services starten/stoppen/neu starten

```bash
# Stalwart (Mailserver)
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart stalwart"

# Nginx (Webserver)
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart nginx"

# PostgreSQL (Datenbank)
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart postgresql"

# PHP-FPM (fuer SnappyMail)
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart php8.4-fpm"

# OfflineIMAP (IMAP-Sync)
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart offlineimap"

# Alle Services auf einmal pruefen
ssh root@10.1.1.100 "pct exec 121 -- systemctl status stalwart nginx postgresql php8.4-fpm offlineimap"
```

## Stalwart Admin-Panel

### Zugriff

```
URL:   https://mail.doehlercomputing.de/
Login: admin / StalwartAdmin2026!
```

### Funktionen im Admin-Panel

- **Accounts**: Benutzer anlegen, aendern, loeschen
- **Domains**: Domains verwalten
- **Queues**: Mail-Queue einsehen und verwalten
- **Reports**: DMARC/TLS Reports
- **Sieve**: Server-weite Sieve-Filter
- **Logs**: Echtzeit-Logs

### Stalwart CLI (falls benoetigt)

Stalwart bietet auch eine REST-API auf `localhost:8080`:

```bash
# Beispiel: Alle Accounts auflisten
ssh root@10.1.1.100 "pct exec 121 -- curl -s -u admin:StalwartAdmin2026! http://localhost:8080/api/principal?limit=100"
```

## Datenbank-Verwaltung

### PostgreSQL

```bash
# Mit Datenbank verbinden
ssh root@10.1.1.100 "pct exec 121 -- sudo -u postgres psql stalwart_mail"

# Datenbanken auflisten
ssh root@10.1.1.100 "pct exec 121 -- sudo -u postgres psql -l"

# Datenbankgroesse
ssh root@10.1.1.100 "pct exec 121 -- sudo -u postgres psql -c \"SELECT pg_size_pretty(pg_database_size('stalwart_mail'));\""
```

### MariaDB (Legacy, gestoppt)

MariaDB ist noch installiert, aber gestoppt. Die alte `imapsync`-Datenbank ist nicht mehr in Verwendung.

```bash
# Falls MariaDB benoetigt wird:
ssh root@10.1.1.100 "pct exec 121 -- systemctl start mariadb"
```

## SnappyMail Verwaltung

### Admin-Zugang

SnappyMail hat ein eigenes Admin-Panel:

```
URL: https://webmail.doehlercomputing.de/?admin
```

**Hinweis:** Das Admin-Passwort ist als bcrypt-Hash in `/var/www/snappymail/data/_data_/_default_/configs/application.ini` gespeichert. Falls das Passwort unbekannt ist, kann es dort manuell zurueckgesetzt werden:

```bash
# Neuen bcrypt-Hash generieren
ssh root@10.1.1.100 "pct exec 121 -- python3 -c \"import bcrypt; print(bcrypt.hashpw(b'NEUES_PASSWORT', bcrypt.gensalt()).decode())\""

# In application.ini den Wert von admin_password ersetzen
ssh root@10.1.1.100 "pct exec 121 -- nano /var/www/snappymail/data/_data_/_default_/configs/application.ini"
```

### SnappyMail-Konfiguration

```
Installationspfad:  /var/www/snappymail/
Datenverzeichnis:   /var/www/snappymail/data/
Version:            2.38.2
PHP-Backend:        php8.4-fpm
```

### Cache leeren

```bash
ssh root@10.1.1.100 "pct exec 121 -- rm -rf /var/www/snappymail/data/cache/*"
```

## Nginx-Verwaltung

### Konfiguration pruefen

```bash
ssh root@10.1.1.100 "pct exec 121 -- nginx -t"
```

### Konfiguration neu laden (ohne Restart)

```bash
ssh root@10.1.1.100 "pct exec 121 -- nginx -s reload"
```

### vHosts

Konfiguration in `/etc/nginx/sites-enabled/`:
- `mail.doehlercomputing.de` -> Stalwart Admin (localhost:8080)
- `webmail.doehlercomputing.de` -> SnappyMail (PHP-FPM)

## SSL-Zertifikat-Verwaltung

### Zertifikate pruefen

```bash
ssh root@10.1.1.100 "pct exec 121 -- certbot certificates"
```

### Zertifikate erneuern

```bash
ssh root@10.1.1.100 "pct exec 121 -- certbot renew"
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart nginx"
```

## OfflineIMAP-Verwaltung

### Status pruefen

```bash
ssh root@10.1.1.100 "pct exec 121 -- systemctl status offlineimap"
ssh root@10.1.1.100 "pct exec 121 -- journalctl -u offlineimap -n 50"
```

### Konfiguration bearbeiten

```bash
ssh root@10.1.1.100 "pct exec 121 -- nano /opt/mailsync/.offlineimaprc"
```

### Sync-Regeln anpassen

Die Mail-Sortierregeln befinden sich in `/opt/mailsync/imap_sort.py` (RULES-Dictionary).

## Regelmaessige Wartungsaufgaben

### Taeglich
- Stalwart-Logs pruefen (`/opt/stalwart/logs/stalwart.log`)
- Speicherplatz pruefen (`df -h`)
- OfflineIMAP-Status pruefen

### Woechentlich
- SSL-Zertifikat-Ablauf pruefen
- PostgreSQL-Groesse pruefen
- Alte Logs rotieren

### Monatlich
- PostgreSQL VACUUM
  ```bash
  ssh root@10.1.1.100 "pct exec 121 -- sudo -u postgres vacuumdb --all --analyze"
  ```
- Debian Updates installieren
  ```bash
  ssh root@10.1.1.100 "pct exec 121 -- apt update && apt upgrade -y"
  ```
- Stalwart auf neue Version pruefen (https://github.com/stalwartlabs/stalwart/releases)

## Naechste Schritte

- [Backup & Restore](./BACKUP-RESTORE.md)
- [Monitoring](./MONITORING.md)
- [Troubleshooting](./TROUBLESHOOTING.md)
