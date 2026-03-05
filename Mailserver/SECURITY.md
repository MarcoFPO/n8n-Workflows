# Sicherheit - Mailserver

## Aktueller Sicherheitsstatus

### Implementiert

- [x] SSL/TLS fuer SMTP (Port 465 implicit TLS, Port 587 STARTTLS)
- [x] SSL/TLS fuer IMAP (Port 993 implicit TLS)
- [x] SSL/TLS fuer POP3 (Port 995 implicit TLS)
- [x] HTTPS fuer Webmail (https://webmail.doehlercomputing.de/)
- [x] HTTPS fuer Admin-Panel (https://mail.doehlercomputing.de/)
- [x] Let's Encrypt Zertifikate mit automatischer Erneuerung
- [x] DKIM-Signaturen (rsa-sha256, Selector: mail)
- [x] Stalwart-internes Directory (keine Unix-Accounts fuer Mail)
- [x] PostgreSQL nur auf localhost (Port 5432)
- [x] Nginx als Reverse Proxy (kein direkter Zugriff auf Stalwart Admin)
- [x] nftables Firewall (Grundkonfiguration)
- [x] Zabbix Agent Monitoring

### Empfohlen (noch nicht implementiert)

- [ ] SPF-Record in DNS
- [ ] DMARC-Policy in DNS
- [ ] Fail2Ban fuer Brute-Force-Schutz
- [ ] Rate-Limiting in Stalwart
- [ ] Spam-Filtering (Stalwart hat integrierte Spam-Filter)

---

## SSL/TLS-Verschluesselung

### Let's Encrypt Zertifikate

| Domain | Ablauf | Pfad |
|---|---|---|
| mail.doehlercomputing.de | 2026-05-16 | `/etc/letsencrypt/live/mail.doehlercomputing.de/` |
| webmail.doehlercomputing.de | 2026-05-19 | `/etc/letsencrypt/live/webmail.doehlercomputing.de/` |

### Zertifikate pruefen

```bash
ssh root@10.1.1.100 "pct exec 121 -- certbot certificates"
```

### Zertifikate erneuern

```bash
ssh root@10.1.1.100 "pct exec 121 -- certbot renew"
ssh root@10.1.1.100 "pct exec 121 -- systemctl restart nginx"
```

Automatische Erneuerung ist per Cron-Job in `/etc/cron.d/certbot` konfiguriert.
DNS-basierte Validierung: `/opt/stalwart/certbot/dns-auth.sh` / `dns-cleanup.sh`.
Deploy-Hook: `/opt/stalwart/certbot/deploy-hook.sh`.

### Stalwart TLS-Konfiguration

Stalwart verwendet eigene Zertifikate fuer direkte TLS-Verbindungen (IMAPS, SMTPS, POP3S):
- Zertifikat: `/opt/stalwart/etc/cert.pem`
- Key: `/opt/stalwart/etc/key.pem`

---

## DKIM-Authentifizierung

Stalwart signiert ausgehende Mails mit DKIM:

| Parameter | Wert |
|---|---|
| Algorithmus | rsa-sha256 |
| Domain | doehlercomputing.de |
| Selector | mail |
| Private Key | `/opt/stalwart/etc/dkim-doehlercomputing.key` |
| Public Key | `/opt/stalwart/etc/dkim-doehlercomputing.pub` |

### DKIM-Signatur pruefen

```bash
# Auf dem Empfaenger-Server die Mail-Header pruefen:
# Suche nach "DKIM-Signature:" und "Authentication-Results: dkim=pass"
```

### DNS-Records (empfohlen)

Folgende DNS-Records sollten fuer `doehlercomputing.de` gesetzt sein:

```
# DKIM
mail._domainkey.doehlercomputing.de  TXT  "v=DKIM1; k=rsa; p=<PUBLIC_KEY>"

# SPF (empfohlen)
doehlercomputing.de  TXT  "v=spf1 ip4:10.1.1.183 ~all"

# DMARC (empfohlen)
_dmarc.doehlercomputing.de  TXT  "v=DMARC1; p=quarantine; rua=mailto:dmarc@doehlercomputing.de"
```

---

## Firewall (nftables)

### Aktuelle Konfiguration

```bash
ssh root@10.1.1.100 "pct exec 121 -- nft list ruleset"
```

### Empfohlene Ports

```
Port 25    (SMTP)         - eingehend
Port 465   (SMTPS)        - eingehend
Port 587   (Submission)   - eingehend
Port 143   (IMAP)         - eingehend
Port 993   (IMAPS)        - eingehend
Port 110   (POP3)         - eingehend
Port 995   (POP3S)        - eingehend
Port 443   (HTTPS)        - eingehend (Nginx)
Port 80    (HTTP)         - eingehend (Redirect auf HTTPS)
Port 4190  (ManageSieve)  - eingehend
Port 8080  (Admin API)    - NUR localhost
Port 5432  (PostgreSQL)   - NUR localhost
```

---

## Passwort-Verwaltung

### Stalwart-Benutzer

Benutzer werden ueber das **Stalwart Admin-Panel** verwaltet (nicht ueber Unix-Accounts):

```
URL:   https://mail.doehlercomputing.de/
Login: admin / StalwartAdmin2026!
```

### Empfehlungen

- Mindestens 12 Zeichen
- Kombination aus Gross-, Kleinbuchstaben, Zahlen, Sonderzeichen
- Regelmaessig aendern (alle 90 Tage)
- Admin-Passwort besonders schuetzen

---

## Datei-Berechtigungen

### Kritische Dateien

```bash
# Stalwart-Konfiguration (nur stalwart-User)
chmod 600 /opt/stalwart/etc/config.toml
chmod 600 /opt/stalwart/etc/dkim-doehlercomputing.key
chown stalwart:stalwart /opt/stalwart/etc/*

# SnappyMail (nur www-data)
chmod 750 /var/www/snappymail/data
chown -R www-data:www-data /var/www/snappymail

# Nginx-Konfiguration
chmod 644 /etc/nginx/sites-enabled/*

# SSL-Zertifikate
chmod 700 /etc/letsencrypt/live/
chmod 600 /etc/letsencrypt/live/*/privkey.pem
```

---

## Log-Ueberwachung

### Verdaechtige Aktivitaeten erkennen

```bash
# Fehlgeschlagene Login-Versuche (Stalwart)
ssh root@10.1.1.100 "pct exec 121 -- grep -i 'authentication failed' /opt/stalwart/logs/stalwart.log | tail -20"

# Nginx-Fehler (z.B. unerwartete Zugriffe)
ssh root@10.1.1.100 "pct exec 121 -- grep -E '4[0-9]{2}|5[0-9]{2}' /var/log/nginx/access.log | tail -20"

# Brute-Force-Versuche erkennen
ssh root@10.1.1.100 "pct exec 121 -- grep -i 'auth' /opt/stalwart/logs/stalwart.log | grep -i 'fail' | awk '{print \$NF}' | sort | uniq -c | sort -rn | head -10"
```

---

## Fail2Ban (empfohlen)

```bash
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    apt install fail2ban -y

    cat > /etc/fail2ban/jail.local << EOF
[stalwart]
enabled = true
port = smtp,465,587,imap,993,pop3,995
filter = stalwart
logpath = /opt/stalwart/logs/stalwart.log
maxretry = 5
findtime = 600
bantime = 3600
EOF

    cat > /etc/fail2ban/filter.d/stalwart.conf << EOF
[Definition]
failregex = authentication failed.*<HOST>
ignoreregex =
EOF

    systemctl enable fail2ban
    systemctl restart fail2ban
'"
```

---

## Sicherheits-Checkliste

**Taeglich:**
- [ ] Stalwart-Logs auf fehlgeschlagene Logins pruefen
- [ ] Services aktiv (stalwart, nginx, postgresql)

**Woechentlich:**
- [ ] SSL-Zertifikat-Ablauf pruefen
- [ ] Firewall-Regeln aktiv
- [ ] Backup-Integritaet pruefen

**Monatlich:**
- [ ] Sicherheits-Updates installieren
- [ ] Stalwart auf neue Version pruefen
- [ ] Nginx-Access-Logs analysieren

**Jaehrlich:**
- [ ] DKIM-Keys rotieren
- [ ] Alle Passwoerter aendern
- [ ] Backup-Restore-Test

---

## Netzwerk-Architektur

```
Internet / LAN
      |
   Nginx (80/443) -- SSL-Terminierung (Let's Encrypt)
      |          \
      |           \-- webmail.doehlercomputing.de -> SnappyMail (PHP-FPM)
      |
      +-- mail.doehlercomputing.de -> Stalwart Admin (localhost:8080)

Stalwart Mail Server:
  SMTPS  : Port 465 (implicit TLS)
  SMTP   : Port 587 (STARTTLS)
  IMAPS  : Port 993 (implicit TLS)
  POP3S  : Port 995 (implicit TLS)
  DKIM   : rsa-sha256 Signierung
      |
  PostgreSQL 17 (nur localhost:5432)
```

---

## Weitere Ressourcen

- [Stalwart Security](https://stalw.art/docs/security/)
- [Nginx Security](https://nginx.org/en/docs/http/configuring_https_servers.html)
- [Let's Encrypt](https://letsencrypt.org/docs/)
- [DKIM/SPF/DMARC Best Practices](https://www.dmarcanalyzer.com/)

---

## Naechste Schritte

- [Monitoring](./MONITORING.md)
- [Backup & Restore](./BACKUP-RESTORE.md)
- [Disaster Recovery](./DISASTER-RECOVERY.md)
