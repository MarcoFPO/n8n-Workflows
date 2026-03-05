# E-Mail Aliases & Weiterleitungen - Mailserver

## Uebersicht

Aliases und Weiterleitungen werden ueber das **Stalwart Admin-Panel** verwaltet.
Postfix-Aliases (`/etc/postfix/virtual`) sind nicht mehr relevant, da Stalwart als All-in-One Mailserver fungiert.

## Stalwart Admin-Panel

### Zugang

```
URL:   https://mail.doehlercomputing.de/
Login: admin / StalwartAdmin2026!
```

### Alias anlegen

1. Im Admin-Panel einloggen
2. **Accounts** -> **Principals** -> **Add**
3. Typ: **Individual** oder **List**
4. E-Mail-Adressen und Aliases konfigurieren

### Alias per REST-API

```bash
# Alle Accounts auflisten
ssh root@10.1.1.100 "pct exec 121 -- curl -s -u admin:StalwartAdmin2026! http://localhost:8080/api/principal?limit=100"

# Account-Details abrufen
ssh root@10.1.1.100 "pct exec 121 -- curl -s -u admin:StalwartAdmin2026! http://localhost:8080/api/principal/mdoehler"
```

## Alias-Typen in Stalwart

### 1. E-Mail-Alias (auf einem Account)

Ein Benutzer kann mehrere E-Mail-Adressen haben:

- Hauptadresse: `mdoehler@doehlercomputing.de`
- Alias: `marco@doehlercomputing.de`
- Alias: `admin@doehlercomputing.de`

Konfiguration im Admin-Panel unter dem jeweiligen Account -> **Email Addresses**.

### 2. Mailing List

Stalwart unterstuetzt native Mailing Lists:

1. Admin-Panel -> **Accounts** -> **Add**
2. Typ: **List**
3. Name: z.B. `team`
4. Mitglieder: `mdoehler`, `egon`, etc.

### 3. Catch-All

Alle Mails an nicht-existierende Adressen an einen bestimmten Account weiterleiten:

Konfiguration in `/opt/stalwart/etc/config.toml` oder im Admin-Panel unter Domain-Einstellungen.

## Sieve-Filter

### Server-seitige Filter

Stalwart unterstuetzt Sieve-Filter nativ (Port 4190 ManageSieve).

Benutzer koennen Sieve-Filter ueber:
- Das Stalwart Admin-Panel konfigurieren
- ManageSieve-kompatible Clients (z.B. Thunderbird mit Sieve-Plugin)
- SnappyMail (unter Einstellungen -> Filter)

### Beispiel Sieve-Script

```sieve
require ["fileinto", "reject"];

# Mails von bestimmter Domain in Ordner sortieren
if address :domain "from" "newsletter.example.com" {
    fileinto "Newsletter";
}

# Spam ablehnen
if header :contains "X-Spam-Flag" "YES" {
    fileinto "Junk";
}
```

## OfflineIMAP Mail-Sortierung

Die automatische Sortierung von Mails aus Arcor/Gmail-INBOX erfolgt durch `/opt/mailsync/imap_sort.py`.

Dieses Script sortiert eingehende Mails anhand der Absender-Domain in ~100 Kategorien:
- Finanzen, IT, Shopping, Reisen, Gaming, etc.

### Sortierregeln anpassen

```bash
# Regeln bearbeiten
ssh root@10.1.1.100 "pct exec 121 -- nano /opt/mailsync/imap_sort.py"
# -> RULES-Dictionary anpassen

# OfflineIMAP neu starten (Sortierung laeuft nach jedem Sync)
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart offlineimap"
```

Details zur OfflineIMAP-Konfiguration: [IMAP-SYNC.md](./IMAP-SYNC.md)

## Troubleshooting

### Alias funktioniert nicht

```bash
# 1. Account im Admin-Panel pruefen
# Browser: https://mail.doehlercomputing.de/

# 2. Stalwart-Logs pruefen
ssh root@10.1.1.100 "pct exec 121 -- grep -i 'alias\|redirect\|rcpt' /opt/stalwart/logs/stalwart.log | tail -20"

# 3. Stalwart neu starten
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart stalwart"
```

### Mail-Schleife erkannt

```bash
# Stalwart-Logs auf Loop-Fehler pruefen
ssh root@10.1.1.100 "pct exec 121 -- grep -i 'loop' /opt/stalwart/logs/stalwart.log | tail -10"
```

## Naechste Schritte

- [Administration](./ADMINISTRATION.md)
- [IMAP-Sync](./IMAP-SYNC.md)
- [Troubleshooting](./TROUBLESHOOTING.md)
