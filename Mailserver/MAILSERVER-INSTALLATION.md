# Mailserver Installation & Konfiguration

## Server-Informationen

| Parameter | Wert |
|---|---|
| **LXC-ID** | 121 |
| **Proxmox-Host** | 10.1.1.100 |
| **IP-Adresse** | 10.1.1.183 |
| **Hostname** | Mail.doehlercomputing.de |
| **OS** | Debian 13 (trixie) |
| **Speicher** | 50 GB Disk, 4 GB RAM, 512 MB Swap |

## Architektur

```
Internet / LAN
      |
   Nginx (80/443) -- SSL-Terminierung (Let's Encrypt)
      |          \
      |           \-- webmail.doehlercomputing.de -> SnappyMail (PHP 8.4-FPM)
      |
      +-- mail.doehlercomputing.de -> Stalwart Admin/API (localhost:8080)

Stalwart Mail Server (All-in-One):
  SMTP  : Port 25, 465 (TLS), 587 (STARTTLS)
  IMAP  : Port 143, 993 (TLS)
  POP3  : Port 110, 995 (TLS)
  Sieve : Port 4190
  Admin : Port 8080 (localhost)
      |
  PostgreSQL 17 (stalwart_mail)

OfflineIMAP:
  Arcor (imap.arcor.de) --> Stalwart Arcor/*
  Gmail (imap.gmail.com) --> Stalwart Gmail/*
  Post-Sync: imap_sort.py (Domain-basiertes Sortieren)
```

## Komponenten im Detail

### Stalwart Mail Server (v0.15.5)

All-in-One Mailserver (ersetzt Postfix + Dovecot seit Februar 2026).

**Installation**: `/opt/stalwart/`

```
/opt/stalwart/
+-- bin/stalwart                       # Binary (v0.15.5)
+-- bin/stalwart.0.15.4.bak            # Backup der Vorgaengerversion
+-- etc/config.toml                    # Hauptkonfiguration
+-- etc/cert.pem                       # SSL-Zertifikat (Stalwart-intern)
+-- etc/key.pem                        # SSL-Key (Stalwart-intern)
+-- etc/dkim-doehlercomputing.key      # DKIM Private Key
+-- etc/dkim-doehlercomputing.pub      # DKIM Public Key
+-- data/                              # Blob-Storage (~2.8 MB)
+-- logs/                              # Log-Dateien (taegliche Rotation)
+-- certbot/                           # Certbot Hooks
+-- backup-pre-upgrade.sql             # DB-Backup vor Upgrade
```

**Listener-Konfiguration** (`/opt/stalwart/etc/config.toml`):

| Listener | Bind | Protokoll | TLS |
|---|---|---|---|
| smtp | [::]:25 | smtp | nein |
| submission | [::]:587 | smtp | STARTTLS |
| submissions | [::]:465 | smtp | implicit TLS |
| imap | [::]:143 | imap | nein |
| imaptls | [::]:993 | imap | implicit TLS |
| pop3 | [::]:110 | pop3 | nein |
| pop3s | [::]:995 | pop3 | implicit TLS |
| sieve | [::]:4190 | managesieve | nein |
| https | 127.0.0.1:8080 | http (Admin/API) | nein (hinter Nginx) |

**Storage**: PostgreSQL (`stalwart_mail` DB fuer data, fts, blob, lookup)

**Directory**: Internal (in PostgreSQL gespeichert)

**DKIM**:
- Algorithmus: rsa-sha256
- Domain: doehlercomputing.de
- Selector: mail
- Key: `/opt/stalwart/etc/dkim-doehlercomputing.key`

**Admin-Zugang**: `admin` / `StalwartAdmin2026!` (Fallback-Admin in config.toml)

**Systemd-Service**: `stalwart.service` (enabled, laeuft als User `stalwart`)

### Nginx (v1.26.3)

Reverse Proxy mit SSL-Terminierung.

**vHost 1 - Stalwart Admin** (`mail.doehlercomputing.de`):
- HTTPS (443) mit Let's Encrypt Zertifikat
- Proxy zu `http://127.0.0.1:8080` (Stalwart Admin/API)
- WebSocket-Support (Upgrade-Header)

**vHost 2 - SnappyMail** (`webmail.doehlercomputing.de`):
- HTTPS (443) mit Let's Encrypt Zertifikat
- PHP-FPM via Unix-Socket (`/run/php/php8.4-fpm.sock`)
- `/data`-Verzeichnis per `deny all` gesperrt

**HTTP Redirect**: Port 80 -> 301 auf HTTPS

### PostgreSQL 17

- **Cluster**: 17-main, Port 5432 (nur localhost)
- **Locale**: de_DE.UTF-8

| Datenbank | Eigentuemer | Zweck |
|---|---|---|
| `stalwart_mail` | stalwart | Stalwart: Mails, Accounts, Volltextsuche |
| `sogo` | sogo | SOGo Groupware (reserviert) |

### SnappyMail (v2.38.2)

Webmail-Oberflaeche.

- **URL**: https://webmail.doehlercomputing.de/
- **Installationspfad**: `/var/www/snappymail/`
- **PHP**: 8.4.16-FPM
- **Owner**: www-data

### Let's Encrypt SSL-Zertifikate

| Domain | Ablauf | Pfad |
|---|---|---|
| mail.doehlercomputing.de | 2026-05-16 | `/etc/letsencrypt/live/mail.doehlercomputing.de/` |
| webmail.doehlercomputing.de | 2026-05-19 | `/etc/letsencrypt/live/webmail.doehlercomputing.de/` |

- Automatische Erneuerung via Certbot (Cron-Job in `/etc/cron.d/certbot`)
- DNS-basierte Validierung: `/opt/stalwart/certbot/dns-auth.sh` / `dns-cleanup.sh`
- Deploy-Hook: `/opt/stalwart/certbot/deploy-hook.sh`

### OfflineIMAP

Bidirektionaler IMAP-Sync fuer externe Postfaecher.

**Konfiguration**: `/opt/mailsync/.offlineimaprc`

| Account | Remote-Host | Remote-User | Lokal-Prefix | Intervall |
|---|---|---|---|---|
| Arcor | imap.arcor.de:993 | doehlerm@arcor.de | `Arcor/` | 15 min |
| Gmail | imap.gmail.com:993 | marcofpo@gmail.com | `Gmail/` | 15 min |

**Folder-Mapping** (in `/opt/mailsync/helpers.py`):
- Arcor: `INBOX` -> `Arcor/INBOX`, `INBOX.Sent` -> `Arcor/Sent`, etc.
- Gmail: `INBOX` -> `Gmail/INBOX`, `[Gmail]/Sent Mail` -> `Gmail/[Gmail]/Sent Mail`, etc.

**Post-Sync Sortierung** (`/opt/mailsync/imap_sort.py`):
- Sortiert Mails aus `Arcor/INBOX` und `Gmail/INBOX` anhand der Absender-Domain
- ~100 Regeln fuer Kategorien: Finanzen, IT, Shopping, Reisen, Gaming, etc.
- Verbindet sich direkt via IMAPS (993) zu Stalwart

**Systemd-Service**: `offlineimap.service` (enabled, after stalwart.service)

### Zabbix Agent

- **Server**: 10.1.1.103
- **Port**: 10050

### Weitere Pakete

| Paket | Status | Hinweis |
|---|---|---|
| OpenDKIM | installiert, **inaktiv** | DKIM wird von Stalwart nativ uebernommen |
| MariaDB | installiert, **gestoppt** | Legacy von der alten Installation |
| nftables | aktiv | Standard-Regeln (keine speziellen Mailserver-Regeln) |
| offlineimap3 | aktiv | IMAP-Sync |

## Benutzer auf dem System

| User | Zweck | Home |
|---|---|---|
| testuser (UID 1000) | Testaccount | /home/testuser |
| mdoehler | Hauptbenutzer | /home/mdoehler |
| admin | Admin-Account | /home/admin |
| egon | Benutzer | /home/egon |
| claude | Automatisierung | /home/claude |
| n8n | n8n Workflows | /home/n8n |

Maildir-Verzeichnisse existieren fuer: admin, egon, mdoehler

## Cron-Jobs

| Intervall | Befehl | Zweck |
|---|---|---|
| */15 min | `/usr/local/bin/swap-cleanup.sh` | Swap bereinigen |
| automatisch | Certbot Renewal | SSL-Zertifikate erneuern |

## Wichtige Befehle

### Services verwalten
```bash
# Stalwart
systemctl status stalwart
systemctl restart stalwart

# Nginx
systemctl status nginx
systemctl restart nginx

# PostgreSQL
systemctl status postgresql
systemctl restart postgresql

# PHP-FPM
systemctl status php8.4-fpm
systemctl restart php8.4-fpm

# OfflineIMAP
systemctl status offlineimap
systemctl restart offlineimap
```

### Logs pruefen
```bash
# Stalwart
tail -f /opt/stalwart/logs/stalwart.log

# Nginx
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# PostgreSQL
tail -f /var/log/postgresql/postgresql-17-main.log

# OfflineIMAP
journalctl -u offlineimap -f
```

## Migrations-Historie

| Datum | Aenderung |
|---|---|
| 2025-10-23 | Erstinstallation: Postfix + Dovecot + Apache + Roundcube + MariaDB |
| 2025-12-13 | IMAP-Sync-Service (imapsync-runner) und Dokumentation |
| 2026-02-18 | Migration zu Stalwart Mail Server + Nginx + SnappyMail + PostgreSQL |
| 2026-02-18 | OfflineIMAP ersetzt imapsync-runner |
| 2026-02-19 | Stalwart laeuft stabil (v0.15.5) |

---

**Erstellt**: 2025-10-23
**Letzte Aktualisierung**: 2026-03-05
