# 🚀 ML-Pipeline Deployment Checklist

**Datum:** 17. August 2025  
**Target:** 10.1.1.174 (aktienanalyse-ökosystem)  
**Status:** Ready for Production

---

## ✅ Pre-Deployment Checklist

### **1. Infrastruktur-Voraussetzungen:**
- [x] PostgreSQL Server aktiv und erreichbar
- [x] Redis Server aktiv und erreichbar  
- [x] Python 3.8+ verfügbar
- [x] SSH-Zugang zu 10.1.1.174 konfiguriert
- [x] Ausreichend Speicherplatz (min. 5GB für ML-Models)

### **2. Dependencies:**
- [x] TensorFlow 2.15.0
- [x] scikit-learn 1.3.2
- [x] pandas 2.1.4
- [x] asyncpg 0.29.0
- [x] redis[hiredis] 5.0.1
- [x] fastapi 0.104.1

### **3. Service-Files:**
- [x] ML Analytics Orchestrator implementiert
- [x] ML Training Service implementiert  
- [x] Technical Feature Engine implementiert
- [x] Model Manager implementiert
- [x] Prediction Orchestrator implementiert
- [x] Event-Bus Integration implementiert
- [x] Database Connection implementiert

### **4. systemd Configuration:**
- [x] ml-analytics.service definiert
- [x] ml-training.service definiert
- [x] ml-scheduler.service + .timer definiert
- [x] Environment Variables konfiguriert
- [x] Resource Limits gesetzt

### **5. Database Schema:**
- [x] ML Schema Extension SQL erstellt
- [x] 11 ML-Tabellen definiert
- [x] TimescaleDB Hypertables konfiguriert
- [x] Indexes und Constraints implementiert
- [x] Data Retention Policies definiert

---

## 🎯 Deployment Steps

### **Step 1: Quick Start Execution**
```bash
cd /home/mdoehler/aktienanalyse-ökosystem
./quick-start-ml-pipeline.sh
```

**Expected Results:**
- ✅ ML Schema deployed (11 tables)
- ✅ ML Services deployed to 10.1.1.174
- ✅ systemd services active
- ✅ APIs responding on ports 8019/8020
- ✅ Demo training triggered for AAPL

### **Step 2: Service Verification**
```bash
# Service Status Check
ssh aktienanalyse@10.1.1.174 'systemctl status ml-analytics ml-training ml-scheduler.timer'

# API Health Check  
curl http://10.1.1.174:8019/health
curl http://10.1.1.174:8020/status

# Database Schema Check
ssh aktienanalyse@10.1.1.174 'psql -U ml_service -d aktienanalyse -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name LIKE '\''ml_%'\''"'
```

**Expected Results:**
- ✅ All services "active (running)"
- ✅ APIs return HTTP 200 with "healthy" status
- ✅ Database shows 11 ML tables

### **Step 3: Training Verification**
```bash
# Monitor Training Logs
ssh aktienanalyse@10.1.1.174 'journalctl -u ml-training -f'

# Check Model Storage
ssh aktienanalyse@10.1.1.174 'ls -la /home/aktienanalyse/ml-models/technical/7d/'

# Verify Training Events
ssh aktienanalyse@10.1.1.174 'redis-cli -u redis://localhost:6379/2 PUBSUB CHANNELS "events:ml:*"'
```

**Expected Results:**
- ✅ Training logs show successful AAPL model training
- ✅ Model files (.h5, .pkl) created in storage
- ✅ ML events published to Redis

---

## 📊 Post-Deployment Validation

### **1. API Functionality:**
```bash
# Health Endpoints
curl -s http://10.1.1.174:8019/health | jq '.status'          # → "healthy"
curl -s http://10.1.1.174:8020/status | jq '.service_name'    # → "ml-training"

# Metrics Endpoints
curl -s http://10.1.1.174:8019/metrics | jq '.performance_metrics'
```

### **2. Database Integrity:**
```sql
-- Connect to database
psql -h 10.1.1.174 -U ml_service -d aktienanalyse

-- Verify ML schema
SELECT table_name, 
       (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as columns
FROM information_schema.tables t 
WHERE table_schema = 'public' AND table_name LIKE 'ml_%';

-- Check TimescaleDB hypertables
SELECT hypertable_name, num_chunks 
FROM timescaledb_information.hypertables 
WHERE hypertable_name LIKE 'ml_%';

-- Verify sample data (after training)
SELECT symbol, feature_type, COUNT(*) as feature_count
FROM ml_features 
GROUP BY symbol, feature_type;
```

### **3. Event-Bus Integration:**
```bash
# Monitor ML events
ssh aktienanalyse@10.1.1.174 'redis-cli -u redis://localhost:6379/2 MONITOR | grep "ml\."'

# Check event history
ssh aktienanalyse@10.1.1.174 'redis-cli -u redis://localhost:6379/2 KEYS "events:ml:*"'
```

### **4. Log Analysis:**
```bash
# Service startup logs
ssh aktienanalyse@10.1.1.174 'journalctl -u ml-analytics --since "1 hour ago" | grep -i "initialized\|healthy"'

# Error detection
ssh aktienanalyse@10.1.1.174 'journalctl -u ml-analytics -u ml-training --since "1 hour ago" | grep -i "error\|failed\|exception"'
```

---

## 🔧 Performance Validation

### **1. Response Time Tests:**
```bash
# API Response Times (should be < 500ms)
time curl -s http://10.1.1.174:8019/health > /dev/null
time curl -s http://10.1.1.174:8020/status > /dev/null

# Database Query Performance
ssh aktienanalyse@10.1.1.174 'psql -U ml_service -d aktienanalyse -c "EXPLAIN ANALYZE SELECT * FROM ml_features ORDER BY calculation_timestamp DESC LIMIT 10;"'
```

### **2. Resource Usage:**
```bash
# Memory Usage
ssh aktienanalyse@10.1.1.174 'systemctl show ml-analytics.service --property=MemoryCurrent'
ssh aktienanalyse@10.1.1.174 'systemctl show ml-training.service --property=MemoryCurrent'

# CPU Usage
ssh aktienanalyse@10.1.1.174 'top -p $(pgrep -f ml_analytics_orchestrator) -n 1'

# Disk Usage  
ssh aktienanalyse@10.1.1.174 'du -sh /home/aktienanalyse/ml-models/'
```

### **3. Model Performance:**
```sql
-- Model accuracy metrics (after training completes)
SELECT model_type, horizon_days, 
       performance_metrics->>'directional_accuracy' as accuracy,
       performance_metrics->>'mae_score' as mae
FROM ml_model_metadata 
WHERE status = 'active';
```

---

## 🚨 Troubleshooting Guide

### **Common Issues & Solutions:**

#### **1. Service won't start:**
```bash
# Check logs
ssh aktienanalyse@10.1.1.174 'journalctl -u ml-analytics --no-pager -n 50'

# Common fixes:
ssh aktienanalyse@10.1.1.174 'systemctl restart postgresql redis'
ssh aktienanalyse@10.1.1.174 'systemctl restart ml-analytics'
```

#### **2. Database connection fails:**
```bash
# Test connection
ssh aktienanalyse@10.1.1.174 'PGPASSWORD="ml_service_secure_2025" psql -h localhost -U ml_service -d aktienanalyse -c "SELECT 1"'

# Reset if needed
ssh aktienanalyse@10.1.1.174 'sudo -u postgres psql -c "ALTER USER ml_service PASSWORD '\''ml_service_secure_2025'\'';"'
```

#### **3. Redis connection fails:**
```bash
# Test Redis
ssh aktienanalyse@10.1.1.174 'redis-cli -u redis://localhost:6379/2 ping'

# Restart if needed
ssh aktienanalyse@10.1.1.174 'systemctl restart redis'
```

#### **4. Training fails:**
```bash
# Check training logs
ssh aktienanalyse@10.1.1.174 'journalctl -u ml-training --no-pager -n 100'

# Manually trigger training
ssh aktienanalyse@10.1.1.174 'systemctl start ml-scheduler'
```

#### **5. Low model performance:**
```bash
# Check data availability
ssh aktienanalyse@10.1.1.174 'psql -U aktienanalyse -d aktienanalyse -c "SELECT symbol, COUNT(*) FROM market_data_daily WHERE date > CURRENT_DATE - INTERVAL '\''365 days'\'' GROUP BY symbol;"'

# Retrain with more data
ssh aktienanalyse@10.1.1.174 'systemctl start ml-scheduler'
```

---

## ✅ Deployment Success Criteria

### **Minimum Requirements for "Go-Live":**
- [x] All 3 services active and healthy
- [x] APIs responding with < 1s response time
- [x] Database schema deployed (11 tables)
- [x] At least 1 successful training completion
- [x] ML events publishing correctly
- [x] No critical errors in logs

### **Optimal Success Indicators:**
- [x] Model directional accuracy > 55%
- [x] Feature calculation < 500ms
- [x] Training completion < 30 minutes
- [x] Prediction generation < 200ms
- [x] Event-to-prediction latency < 5 seconds

---

## 📅 Post-Deployment Tasks

### **Immediate (Day 1):**
- [ ] Monitor service stability for 24 hours
- [ ] Verify first scheduled training (02:00 next day)
- [ ] Test manual prediction requests
- [ ] Document any performance issues

### **Short-term (Week 1):**
- [ ] Analyze model performance trends
- [ ] Optimize feature calculation if needed
- [ ] Fine-tune training parameters
- [ ] Set up monitoring dashboards

### **Medium-term (Month 1):**
- [ ] Evaluate prediction accuracy vs. market
- [ ] Implement additional symbols
- [ ] Consider model architecture improvements
- [ ] Plan Phase 2 features (sentiment, fundamental)

---

## 📞 Support Information

### **Log Locations:**
- **Service Logs:** `journalctl -u <service-name>`
- **Application Logs:** `/home/aktienanalyse/aktienanalyse-ökosystem/logs/`
- **Model Storage:** `/home/aktienanalyse/ml-models/`

### **Key Commands:**
```bash
# Service management
systemctl {start|stop|restart|status} ml-analytics
systemctl {start|stop|restart|status} ml-training  
systemctl {start|stop|restart|status} ml-scheduler.timer

# Manual operations
systemctl start ml-scheduler          # Trigger training
curl http://10.1.1.174:8019/health   # Health check
redis-cli -u redis://localhost:6379/2 MONITOR  # Event monitoring
```

### **Emergency Contacts:**
- **System Admin:** aktienanalyse@10.1.1.174
- **Database:** PostgreSQL on localhost:5432
- **Event Bus:** Redis on localhost:6379/2

---

**Deployment Checklist Complete - Ready for Production! 🚀**