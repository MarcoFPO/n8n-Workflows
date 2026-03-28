# IMAP-Sync (OfflineIMAP) - Mailserver

## Uebersicht

OfflineIMAP synchronisiert externe Postfaecher (Arcor, Gmail) bidirektional mit dem lokalen Stalwart-Mailserver.
Nach jedem Sync sortiert `imap_sort.py` eingehende Mails anhand der Absender-Domain in Kategorien.

## Konfiguration

### OfflineIMAP-Konfigurationsdatei

Pfad: `/opt/mailsync/.offlineimaprc`

### Synchronisierte Accounts

| Account | Remote-Host | Remote-User | Lokal-Prefix | Intervall |
|---|---|---|---|---|
| Arcor | imap.arcor.de:993 | doehlerm@arcor.de | `Arcor/` | 15 min |
| Gmail | imap.gmail.com:993 | marcofpo@gmail.com | `Gmail/` | 15 min |

### Folder-Mapping

Die Folder-Uebersetzung erfolgt in `/opt/mailsync/helpers.py`:

**Arcor:**
- `INBOX` -> `Arcor/INBOX`
- `INBOX.Sent` -> `Arcor/Sent`
- `INBOX.Drafts` -> `Arcor/Drafts`
- etc.

**Gmail:**
- `INBOX` -> `Gmail/INBOX`
- `[Gmail]/Sent Mail` -> `Gmail/[Gmail]/Sent Mail`
- etc.

## Systemd-Service

```bash
# Status pruefen
ssh root@10.1.1.100 "pct exec 121 -- systemctl status offlineimap"

# Neu starten
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart offlineimap"

# Logs anschauen
ssh root@10.1.1.100 "pct exec 121 -- journalctl -u offlineimap -n 50"

# Live-Logs
ssh root@10.1.1.100 "pct exec 121 -- journalctl -u offlineimap -f"
```

Der Service ist enabled und startet nach `stalwart.service`.

## Post-Sync Sortierung

### imap_sort.py

Pfad: `/opt/mailsync/imap_sort.py`

Dieses Script wird nach jedem OfflineIMAP-Sync ausgefuehrt und sortiert Mails aus `Arcor/INBOX` und `Gmail/INBOX` anhand der Absender-Domain in kategorisierte Ordner.

### Funktionsweise

1. Verbindet sich direkt via IMAPS (Port 993) zu Stalwart
2. Liest Mails aus `Arcor/INBOX` und `Gmail/INBOX`
3. Extrahiert die Absender-Domain
4. Verschiebt Mails anhand des RULES-Dictionary in den passenden Ordner

### Kategorien (Beispiele)

Das RULES-Dictionary enthaelt ~100 Domain-zu-Ordner-Regeln:

| Absender-Domain | Ziel-Ordner |
|---|---|
| paypal.com | Finanzen/PayPal |
| amazon.de | Shopping/Amazon |
| github.com | IT/GitHub |
| booking.com | Reisen/Booking |
| steam.com | Gaming/Steam |
| ... | ... |

### Sortierregeln anpassen

```bash
# Datei bearbeiten
ssh root@10.1.1.100 "pct exec 121 -- nano /opt/mailsync/imap_sort.py"

# Im RULES-Dictionary neue Regel hinzufuegen:
# "neue-domain.de": "Kategorie/Ordner",
```

## Manueller Sync

### Einzelnen Account synchronisieren

```bash
# Nur Arcor
ssh root@10.1.1.100 "pct exec 121 -- offlineimap -c /opt/mailsync/.offlineimaprc -a Arcor -1"

# Nur Gmail
ssh root@10.1.1.100 "pct exec 121 -- offlineimap -c /opt/mailsync/.offlineimaprc -a Gmail -1"
```

### Alle Accounts synchronisieren

```bash
ssh root@10.1.1.100 "pct exec 121 -- offlineimap -c /opt/mailsync/.offlineimaprc -1"
```

### Debug-Modus

```bash
ssh root@10.1.1.100 "pct exec 121 -- offlineimap -c /opt/mailsync/.offlineimaprc -a Arcor -1 -d imap"
```

## Troubleshooting

### Sync laeuft nicht

```bash
# 1. Service-Status
ssh root@10.1.1.100 "pct exec 121 -- systemctl status offlineimap"

# 2. Logs pruefen
ssh root@10.1.1.100 "pct exec 121 -- journalctl -u offlineimap -n 50"

# 3. Lock-Datei entfernen (falls vorhanden)
ssh root@10.1.1.100 "pct exec 121 -- rm -f /tmp/offlineimap.lock"

# 4. Service neu starten
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart offlineimap"
```

### Verbindungsfehler zum Remote-Server

```bash
# Arcor IMAP testen
ssh root@10.1.1.100 "pct exec 121 -- openssl s_client -connect imap.arcor.de:993 </dev/null 2>/dev/null | head -5"

# Gmail IMAP testen
ssh root@10.1.1.100 "pct exec 121 -- openssl s_client -connect imap.gmail.com:993 </dev/null 2>/dev/null | head -5"
```

### Cache zuruecksetzen

```bash
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    systemctl stop offlineimap
    rm -rf /opt/mailsync/.offlineimap
    systemctl start offlineimap
'"
```

### Sortierung funktioniert nicht

```bash
# imap_sort.py manuell ausfuehren
ssh root@10.1.1.100 "pct exec 121 -- python3 /opt/mailsync/imap_sort.py"

# Python-Fehler pruefen
ssh root@10.1.1.100 "pct exec 121 -- python3 -c 'import imaplib; print(\"OK\")'"
```

## Dateien im Ueberblick

| Datei | Zweck |
|---|---|
| `/opt/mailsync/.offlineimaprc` | OfflineIMAP-Hauptkonfiguration |
| `/opt/mailsync/helpers.py` | Folder-Name-Uebersetzung |
| `/opt/mailsync/imap_sort.py` | Post-Sync Mail-Sortierung |
| `/opt/mailsync/.offlineimap/` | OfflineIMAP Cache/State |

## Legacy: imapsync-runner

Der fruehere `imapsync-runner` Python-Service (mit MariaDB-Backend) wurde durch OfflineIMAP ersetzt (Februar 2026).
Folgende Dateien sind obsolet:
- `imapsync-ctl`
- `imapsync-schema.sql`
- `imapsync-runner.service`
- `setup_database.sh`

## Naechste Schritte

- [Aliases & Weiterleitungen](./ALIASES.md)
- [Monitoring](./MONITORING.md)
- [Troubleshooting](./TROUBLESHOOTING.md)
