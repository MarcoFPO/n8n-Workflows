# Mailserver-Dokumentation - Index

Dokumentation fuer das Mailserver-Projekt (LXC 121 auf Proxmox).

## Dokumentations-Ueberblick

| Dokument | Zweck |
|----------|-------|
| [README.md](README.md) | **Startpunkt** - Uebersicht und Quick Links |
| [QUICK-START.md](QUICK-START.md) | **Einstieg** - Webmail und Client-Einrichtung |
| [MAILSERVER-INSTALLATION.md](MAILSERVER-INSTALLATION.md) | **Setup** - Detaillierte Installation & Konfiguration |
| [ADMINISTRATION.md](ADMINISTRATION.md) | **Verwaltung** - Benutzer, Services, Datenbank |
| [MONITORING.md](MONITORING.md) | **Ueberwachung** - Health Checks & Zabbix |
| [BACKUP-RESTORE.md](BACKUP-RESTORE.md) | **Datensicherung** - Backup & Wiederherstellung |
| [ALIASES.md](ALIASES.md) | **E-Mail** - Aliases & Weiterleitungen |
| [IMAP-SYNC.md](IMAP-SYNC.md) | **Sync** - OfflineIMAP (Arcor, Gmail) |
| [UPGRADES.md](UPGRADES.md) | **Wartung** - Updates & Upgrades |
| [PERFORMANCE.md](PERFORMANCE.md) | **Optimierung** - Tuning & Best Practices |
| [SECURITY.md](SECURITY.md) | **Sicherheit** - SSL, DKIM, Firewall |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | **Fehlersuche** - Haeufige Probleme & Loesungen |
| [DISASTER-RECOVERY.md](DISASTER-RECOVERY.md) | **Notfall** - Recovery-Verfahren |

---

## Nach Rolle

### Endbenutzer / E-Mail-Nutzer
1. [QUICK-START.md](QUICK-START.md) - Webmail nutzen, Client einrichten
2. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Login-Probleme

### Systemadministrator
1. [README.md](README.md) - Uebersicht
2. [ADMINISTRATION.md](ADMINISTRATION.md) - Benutzer verwalten (Stalwart Admin-Panel)
3. [MONITORING.md](MONITORING.md) - Ueberwachen (Zabbix + manuell)
4. [BACKUP-RESTORE.md](BACKUP-RESTORE.md) - Sichern
5. [UPGRADES.md](UPGRADES.md) - Updaten

### Notfall-Situationen
1. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Probleme diagnostizieren
2. [DISASTER-RECOVERY.md](DISASTER-RECOVERY.md) - Wiederherstellung
3. [BACKUP-RESTORE.md](BACKUP-RESTORE.md) - Restore durchfuehren

---

## Dokumentations-Struktur

```
Mailserver-Projekt (LXC 121)
|
+-- README.md                      (Start hier!)
+-- QUICK-START.md                 (Webmail / Client-Setup)
|
+-- INSTALLATION & KONFIGURATION
|   +-- MAILSERVER-INSTALLATION.md (Stalwart, Nginx, PostgreSQL, SnappyMail)
|   +-- ALIASES.md                 (E-Mail-Weiterleitungen via Stalwart)
|   +-- IMAP-SYNC.md              (OfflineIMAP: Arcor + Gmail)
|
+-- BETRIEB & VERWALTUNG
|   +-- ADMINISTRATION.md          (Stalwart Admin-Panel, Services)
|   +-- MONITORING.md              (Zabbix, Health Checks)
|   +-- SECURITY.md                (SSL, DKIM, nftables)
|
+-- DATEN & BACKUP
|   +-- BACKUP-RESTORE.md          (PostgreSQL, Stalwart, Konfiguration)
|
+-- WARTUNG & OPTIMIERUNG
|   +-- UPGRADES.md                (Stalwart, Nginx, PostgreSQL, Debian)
|   +-- PERFORMANCE.md             (Tuning)
|
+-- PROBLEMLOESUNG
|   +-- TROUBLESHOOTING.md
|   +-- DISASTER-RECOVERY.md
|
+-- INDEX.md                       (Diese Datei)
```

---

## Server-Informationen

| Parameter | Wert |
|-----------|------|
| **Server-IP** | 10.1.1.183 |
| **Webmail** | https://webmail.doehlercomputing.de/ |
| **Admin-Panel** | https://mail.doehlercomputing.de/ |
| **Hostname** | Mail.doehlercomputing.de |
| **LXC-ID** | 121 (auf Proxmox 10.1.1.100) |
| **Betriebssystem** | Debian 13 (trixie) |
| **Mailserver** | Stalwart Mail Server 0.15.5 |
| **Administrator** | mdoehler |

---

## Wichtigste Befehle

### Service-Verwaltung
```bash
ssh root@10.1.1.100 "pct exec 121 -- systemctl status stalwart nginx postgresql php8.4-fpm offlineimap"
```

### Logs pruefen
```bash
# Stalwart
ssh root@10.1.1.100 "pct exec 121 -- tail -f /opt/stalwart/logs/stalwart.log"

# OfflineIMAP
ssh root@10.1.1.100 "pct exec 121 -- journalctl -u offlineimap -f"
```

### SSL-Zertifikate
```bash
ssh root@10.1.1.100 "pct exec 121 -- certbot certificates"
```

---

## Nach Service

- **Stalwart (SMTP/IMAP/POP3)**: [INSTALLATION.md](MAILSERVER-INSTALLATION.md#stalwart-mail-server-v0155), [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Nginx (Reverse Proxy)**: [INSTALLATION.md](MAILSERVER-INSTALLATION.md#nginx-v1263), [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **PostgreSQL (Datenbank)**: [INSTALLATION.md](MAILSERVER-INSTALLATION.md#postgresql-17)
- **SnappyMail (Webmail)**: [INSTALLATION.md](MAILSERVER-INSTALLATION.md#snappymail-v2382), [QUICK-START.md](QUICK-START.md)
- **OfflineIMAP (Sync)**: [IMAP-SYNC.md](IMAP-SYNC.md)

---

## Dokumentations-Versionshistorie

| Datum | Aenderung | Autor |
|-------|----------|-------|
| 2025-10-23 | Mailserver Installation (Postfix/Dovecot) | mdoehler |
| 2025-12-13 | Komplette Dokumentation erstellt | mdoehler |
| 2026-02-18 | Migration zu Stalwart Mail Server | mdoehler |
| 2026-03-05 | Dokumentation an aktuellen Stand angepasst | mdoehler/Claude |

---

## Weiterfuehrende Ressourcen

### Offizielle Dokumentation
- [Stalwart Mail Server](https://stalw.art/docs/)
- [Nginx](https://nginx.org/en/docs/)
- [PostgreSQL](https://www.postgresql.org/docs/)
- [SnappyMail](https://github.com/the-djmaze/snappymail/wiki)
- [OfflineIMAP](https://www.offlineimap.org/doc/)
- [Debian](https://www.debian.org/doc/)

---

**Erstellt**: 2025-12-13
**Letzte Aktualisierung**: 2026-03-05
