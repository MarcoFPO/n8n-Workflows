# Mailserver-Projekt (LXC 121)

Mailserver basierend auf Debian 13 mit **Stalwart Mail Server**, **Nginx** und **SnappyMail** Webmail.

## Quick Start

**Webmail**: https://webmail.doehlercomputing.de/
**Admin-Panel**: https://mail.doehlercomputing.de/
**SSH-Zugang**: `ssh root@10.1.1.100 "pct exec 121 -- bash"`

## Systemuebersicht

| Komponente | Version | Funktion | Status |
|------------|---------|----------|--------|
| Debian | 13.3 (trixie) | Betriebssystem | aktiv |
| Stalwart Mail | 0.15.5 | SMTP/IMAP/POP3/Sieve (All-in-One) | aktiv |
| Nginx | 1.26.3 | Reverse Proxy + SSL-Terminierung | aktiv |
| PostgreSQL | 17.8 | Datenbank | aktiv |
| PHP | 8.4.16 (FPM) | SnappyMail Backend | aktiv |
| SnappyMail | 2.38.2 | Webmail-Oberflaeche | aktiv |
| OfflineIMAP | 8.0.0 | IMAP-Sync (Arcor, Gmail) | aktiv |
| Certbot | 4.0.0 | SSL-Zertifikate (Let's Encrypt) | aktiv |
| Zabbix Agent | - | Monitoring (an 10.1.1.103) | aktiv |
| OpenDKIM | - | DKIM-Signierung (installiert, inaktiv) | inaktiv |

## Domains

| Domain | Zweck |
|--------|-------|
| `mail.doehlercomputing.de` | Stalwart Admin/API + MX-Record |
| `webmail.doehlercomputing.de` | SnappyMail Webmail |

## Dokumentation

### Erste Schritte
- [Installation & Setup](./MAILSERVER-INSTALLATION.md) - Komplettes Setup und Konfiguration
- [Quick-Start-Guide](./QUICK-START.md) - Schneller Einstieg fuer neue Benutzer

### Betrieb & Verwaltung
- [Verwaltungshandbuch](./ADMINISTRATION.md) - Benutzer, Mailboxen, Einstellungen verwalten
- [Monitoring & Health Checks](./MONITORING.md) - Server-Gesundheit ueberwachen
- [Backup & Restore](./BACKUP-RESTORE.md) - Daten sichern und wiederherstellen

### E-Mail Management
- [Mail-Alias & Weiterleitungen](./ALIASES.md) - E-Mail-Weiterleitungen und Aliases einrichten
- [IMAP-Sync (OfflineIMAP)](./IMAP-SYNC.md) - Externe Konten synchronisieren

### Wartung & Optimierung
- [Upgrade & Updates](./UPGRADES.md) - Komponenten aktualisieren
- [Performance-Optimierungen](./PERFORMANCE.md) - Tuning und Best Practices
- [Disaster Recovery](./DISASTER-RECOVERY.md) - Notfallwiederherstellung
- [Security](./SECURITY.md) - Sicherheitsrichtlinien

### Troubleshooting
- [Troubleshooting-Guide](./TROUBLESHOOTING.md) - Haeufige Probleme und Loesungen

## Haeufige Aufgaben

### Service-Status pruefen
```bash
ssh root@10.1.1.100 "pct exec 121 -- systemctl status stalwart nginx postgresql php8.4-fpm offlineimap"
```

### Stalwart neu starten
```bash
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart stalwart"
```

### Logs anschauen
```bash
# Stalwart Logs
ssh root@10.1.1.100 "pct exec 121 -- tail -f /opt/stalwart/logs/stalwart.log"

# OfflineIMAP Logs
ssh root@10.1.1.100 "pct exec 121 -- journalctl -u offlineimap -f"
```

### SSL-Zertifikate pruefen
```bash
ssh root@10.1.1.100 "pct exec 121 -- certbot certificates"
```

## Architektur

```
Internet / LAN
      |
   Nginx (80/443) ── SSL-Terminierung
      |          \
      |           \── webmail.doehlercomputing.de -> SnappyMail (PHP-FPM)
      |
      └── mail.doehlercomputing.de -> Stalwart (localhost:8080)
                                        |
                              SMTP(25,465,587)
                              IMAP(143,993)
                              POP3(110,995)
                              Sieve(4190)
                                        |
                                  PostgreSQL 17
                                  (stalwart_mail)

OfflineIMAP ── Arcor (imap.arcor.de) ──> Stalwart (Arcor/*)
            └─ Gmail (imap.gmail.com) ──> Stalwart (Gmail/*)
            └─ Post-Sync: imap_sort.py (Regel-basiertes Sortieren)
```

## Wichtige Pfade

| Pfad | Beschreibung |
|------|-------------|
| `/opt/stalwart/` | Stalwart Mail Server Installation |
| `/opt/stalwart/etc/config.toml` | Stalwart Konfiguration |
| `/opt/stalwart/logs/` | Stalwart Logs |
| `/opt/mailsync/` | OfflineIMAP Konfiguration + Sort-Skripte |
| `/var/www/snappymail/` | SnappyMail Webmail |
| `/etc/nginx/sites-enabled/` | Nginx vHosts |
| `/etc/letsencrypt/live/` | SSL-Zertifikate |

## Kontakt & Support

**Server-Admin**: mdoehler
**Installation**: 2025-10-23 (Postfix/Dovecot), Migration zu Stalwart: 2026-02
**Letzte Aktualisierung**: 2026-03-05 (System + Sicherheitsupdates, PostgreSQL 17.7→17.8)
