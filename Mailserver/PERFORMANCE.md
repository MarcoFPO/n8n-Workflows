# Performance-Optimierungen - Mailserver

## System-Baseline

**Aktuelle Konfiguration (LXC 121)**:

```
CPU:     2 Cores
RAM:     4 GB (aktuell ~500 MB belegt, Stand 2026-03-05)
Disk:    50 GB (aktuell ~5.7 GB belegt, ~12%)
Network: 1 Gbps
```

```bash
# Aktuelle Werte pruefen
ssh root@10.1.1.100 "pct config 121" | grep -E "cores|memory|rootfs"
```

---

## Stalwart-Optimierungen

### Thread-Pool & Connection Limits

Konfiguration in `/opt/stalwart/etc/config.toml`:

```toml
# Worker Threads (Standard: Anzahl CPU-Cores)
[global]
thread-pool = 4

# Connection Limits pro Listener
[server.listener.smtp]
max-connections = 256

[server.listener.imap]
max-connections = 256
```

### Stalwart-Logs

```bash
# Log-Level anpassen (weniger Logging = mehr Performance)
# In config.toml:
# [tracing]
# level = "info"  # debug, info, warn, error
```

### Stalwart-Performance pruefen

```bash
# Aktive Verbindungen
ssh root@10.1.1.100 "pct exec 121 -- ss -tlnp | grep stalwart"

# Prozess-Ressourcen
ssh root@10.1.1.100 "pct exec 121 -- ps aux | grep stalwart"

# Stalwart-Logs auf Performance-Probleme
ssh root@10.1.1.100 "pct exec 121 -- grep -i 'timeout\|slow\|overload' /opt/stalwart/logs/stalwart.log | tail -10"
```

---

## PostgreSQL-Optimierungen

### Grundlegende Tuning-Parameter

```bash
# /etc/postgresql/17/main/postgresql.conf
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    cat >> /etc/postgresql/17/main/conf.d/tuning.conf << EOF
# Memory
shared_buffers = 1GB
effective_cache_size = 3GB
work_mem = 16MB
maintenance_work_mem = 256MB

# WAL
wal_buffers = 16MB
checkpoint_completion_target = 0.9

# Connections
max_connections = 100

# Logging
log_min_duration_statement = 1000
EOF

    systemctl restart postgresql
'"
```

### Regelmaessige Wartung

```bash
# VACUUM und ANALYZE (monatlich empfohlen)
ssh root@10.1.1.100 "pct exec 121 -- sudo -u postgres vacuumdb --all --analyze"

# Datenbank-Groesse pruefen
ssh root@10.1.1.100 "pct exec 121 -- sudo -u postgres psql -c \"
    SELECT pg_size_pretty(pg_database_size('stalwart_mail'));
\""

# Tabellen-Groessen
ssh root@10.1.1.100 "pct exec 121 -- sudo -u postgres psql stalwart_mail -c \"
    SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) as size
    FROM pg_tables
    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
    ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC
    LIMIT 10;
\""
```

### Langsame Queries identifizieren

```bash
# Slow Query Log aktivieren (in postgresql.conf)
# log_min_duration_statement = 1000  (1 Sekunde)

# Langsame Queries anzeigen
ssh root@10.1.1.100 "pct exec 121 -- grep 'duration' /var/log/postgresql/postgresql-17-main.log | tail -10"
```

---

## Nginx-Optimierungen

### Worker & Connections

```bash
# /etc/nginx/nginx.conf
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    # worker_processes auto (Standard: Anzahl Cores)
    # worker_connections 1024 (Standard: 768)
    grep -E \"worker_processes|worker_connections\" /etc/nginx/nginx.conf
'"
```

### Gzip-Kompression

```bash
# Falls nicht aktiv, in nginx.conf:
# gzip on;
# gzip_types text/plain text/css application/json application/javascript;
# gzip_min_length 256;
```

### Proxy-Cache fuer Stalwart Admin

```nginx
# In der vHost-Konfiguration:
proxy_cache_path /tmp/nginx_cache levels=1:2 keys_zone=stalwart_cache:10m;

location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_cache stalwart_cache;
    proxy_cache_valid 200 5m;
}
```

---

## PHP-FPM Optimierungen (SnappyMail)

```bash
# /etc/php/8.4/fpm/pool.d/www.conf
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    grep -E \"pm =|pm.max_children|pm.start_servers\" /etc/php/8.4/fpm/pool.d/www.conf
'"

# Empfohlene Werte fuer 4 GB RAM:
# pm = dynamic
# pm.max_children = 10
# pm.start_servers = 3
# pm.min_spare_servers = 2
# pm.max_spare_servers = 5
```

### PHP-Memory

```bash
# In /etc/php/8.4/fpm/php.ini:
# memory_limit = 256M
# opcache.enable = 1
# opcache.memory_consumption = 128
```

---

## Speicher-Optimierungen

### Stalwart-Logs bereinigen

```bash
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    du -sh /opt/stalwart/logs/
    find /opt/stalwart/logs -name \"*.log\" -mtime +30 -delete
'"
```

### Journal-Logs begrenzen

```bash
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    journalctl --vacuum-time=30d
    journalctl --disk-usage
'"
```

### SnappyMail-Cache leeren

```bash
ssh root@10.1.1.100 "pct exec 121 -- rm -rf /var/www/snappymail/data/cache/*"
```

---

## Netzwerk-Optimierungen

### TCP-Tuning

```bash
ssh root@10.1.1.100 "pct exec 121 -- bash -c '
    cat >> /etc/sysctl.conf << EOF

# TCP Performance
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 67108864
net.ipv4.tcp_wmem = 4096 65536 67108864
net.core.somaxconn = 65535
EOF

    sysctl -p
'"
```

---

## Monitoring & Benchmarking

### Aktuelle Performance messen

```bash
# CPU-Last
ssh root@10.1.1.100 "pct exec 121 -- uptime"

# RAM-Nutzung
ssh root@10.1.1.100 "pct exec 121 -- free -h"

# Disk I/O
ssh root@10.1.1.100 "pct exec 121 -- iostat -x 1 3"

# Top-Prozesse nach RAM
ssh root@10.1.1.100 "pct exec 121 -- ps aux --sort=-%mem | head -10"
```

---

## Performance-Checkliste

**Monatlich ueberpruefen:**
- [ ] CPU-Auslastung < 70%
- [ ] RAM-Auslastung < 80%
- [ ] Disk-Auslastung < 80%
- [ ] PostgreSQL VACUUM durchfuehren
- [ ] Stalwart-Logs rotieren

**Quartalweise:**
- [ ] PostgreSQL-Tabellen-Groessen pruefen
- [ ] Langsame Queries analysieren
- [ ] PHP-FPM Pool-Einstellungen pruefen

---

## Ressourcen

- [Stalwart Performance](https://stalw.art/docs/server/configuration/)
- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Tuning_Your_PostgreSQL_Server)
- [Nginx Performance](https://nginx.org/en/docs/http/ngx_http_core_module.html)
- [PHP-FPM Tuning](https://www.php.net/manual/en/install.fpm.configuration.php)

---

## Naechste Schritte

- [Monitoring](./MONITORING.md)
- [Administration](./ADMINISTRATION.md)
- [Upgrades](./UPGRADES.md)
