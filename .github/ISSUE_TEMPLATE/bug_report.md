---
name: 🐛 Bug Report
about: Create a report to help us improve the Clean Architecture system
title: 'bug: [Brief description of the issue]'
labels: ['bug', 'needs-triage']
assignees: ''
---

## 🐛 **Bug Summary**
<!-- A clear and concise description of what the bug is -->

**Severity:**
- [ ] 🔴 **Critical** - System down, data loss, security breach
- [ ] 🟠 **High** - Major functionality broken, workaround difficult
- [ ] 🟡 **Medium** - Functionality impacted, workaround available
- [ ] 🟢 **Low** - Minor issue, easy workaround

**Bug Type:**
- [ ] Frontend/UI Issue
- [ ] Backend/API Issue  
- [ ] Database/Data Issue
- [ ] Performance Issue
- [ ] Security Vulnerability
- [ ] Infrastructure/Deployment Issue
- [ ] Clean Architecture Violation

---

## 🔍 **Environment Information**

### **System Environment:**
- **Server:** [Local | 10.1.1.174 Production | 10.1.1.174 Staging]
- **OS:** [Linux/Windows/macOS + version]
- **Python Version:** [e.g., 3.11.4]
- **Browser:** [Chrome/Firefox/Safari + version] (if frontend issue)
- **Deployment:** [Development | Staging | Production]

### **Service Information:**
**Affected Services:** (Check all that apply)
- [ ] 🎯 Frontend Service (Port 8080/8081)
- [ ] 🚌 Event Bus Service (Port 8014)
- [ ] 📈 Data Processing Service (Port 8017)
- [ ] 🤖 ML Analytics Service (Port 8021)
- [ ] 🎯 Prediction Tracking Service (Port 8018)
- [ ] 💰 Unified Profit Engine (Port 8025)
- [ ] 📊 MarketCap Service (Port 8019)
- [ ] 🔍 Monitoring Service (Port 8015)

### **Architecture Layer:**
- [ ] 🎯 Presentation Layer (Controllers/API)
- [ ] 🔄 Application Layer (Use Cases)
- [ ] 🏢 Domain Layer (Business Logic)  
- [ ] 🔧 Infrastructure Layer (Repositories/External Services)

---

## 📋 **Steps to Reproduce**
<!-- Provide detailed steps to reproduce the bug -->

1. Go to '...'
2. Click on '...'
3. Enter data '...'
4. See error

**Minimal Reproduction:**
```bash
# Commands to reproduce the issue
python -m pytest tests/specific_test.py
# OR
curl -X GET "http://localhost:8080/api/v1/endpoint"
# OR
[Specific steps...]
```

---

## ❌ **Expected vs Actual Behavior**

### **Expected Behavior:**
<!-- A clear description of what you expected to happen -->

### **Actual Behavior:**
<!-- A clear description of what actually happened -->

### **Screenshots/Logs:**
<!-- If applicable, add screenshots, error logs, or stack traces -->

```
[Paste error logs, stack traces, or relevant output here]
```

---

## 🔧 **Technical Analysis**

### **Error Information:**
**Error Message:**
```
[Full error message if available]
```

**Stack Trace:**
```
[Full stack trace if available]
```

**HTTP Status Code:** [e.g., 500, 404, 400] (if API issue)

### **Clean Architecture Impact:**
**Which layers are affected?**
- [ ] Domain logic corruption
- [ ] Use case execution failure  
- [ ] Infrastructure service failure
- [ ] Presentation layer rendering issue

**Dependency Flow Issues:**
- [ ] Circular dependencies detected
- [ ] Inappropriate layer dependencies
- [ ] Missing dependency injection
- [ ] Interface contract violation

---

## 🔍 **Investigation Details**

### **Database State:**
<!-- If database-related issue -->
- [ ] Data corruption suspected
- [ ] Schema migration issues
- [ ] Connection pool problems
- [ ] Query performance issues

### **Service Communication:**
<!-- If inter-service communication issue -->
- [ ] Event Bus message failure
- [ ] API endpoint unreachable
- [ ] Timeout issues
- [ ] Authentication/authorization failure

### **Performance Metrics:**
<!-- If performance-related -->
- **Response Time:** _____ seconds (Expected: < 0.12s)
- **Memory Usage:** _____ MB
- **CPU Usage:** _____ %
- **Database Query Time:** _____ ms

---

## 🧪 **Testing Information**

### **Test Coverage:**
- [ ] Existing tests are passing
- [ ] Existing tests are failing
- [ ] No tests exist for this functionality
- [ ] Tests need to be updated

### **Regression Testing:**
- [ ] Bug exists in current main branch
- [ ] Bug introduced in recent PR: #_____
- [ ] Bug exists since: [commit hash or version]
- [ ] Cannot determine introduction point

---

## 🚨 **Impact Assessment**

### **User Impact:**
- **Users Affected:** [All | Specific user group | Single user]
- **Functionality Impact:** [Complete failure | Partial failure | Minor inconvenience]
- **Workaround Available:** [Yes | No | Difficult]

### **Business Impact:**
- [ ] Revenue/business operations affected
- [ ] Data integrity compromised
- [ ] Security implications
- [ ] Performance degradation
- [ ] User experience impacted

### **System Impact:**
- [ ] Service downtime
- [ ] Cascading failures to other services
- [ ] Data consistency issues
- [ ] Performance bottlenecks

---

## 💡 **Suggested Solution**
<!-- If you have ideas for how to fix the bug -->

### **Root Cause Hypothesis:**
<!-- What do you think is causing this issue? -->

### **Potential Fixes:**
1. [Suggestion 1]
2. [Suggestion 2]
3. [Suggestion 3]

### **Architecture Improvements:**
<!-- Any Clean Architecture violations that should be addressed -->

---

## 🔒 **Security Considerations**

### **Security Impact:**
- [ ] No security implications
- [ ] Information disclosure
- [ ] Authentication bypass
- [ ] Authorization bypass
- [ ] Input validation issue
- [ ] SQL injection vulnerability
- [ ] XSS vulnerability

### **Immediate Security Actions:**
<!-- If security-related, what immediate actions should be taken? -->

---

## 📊 **Additional Context**

### **Related Issues:**
- Similar to: #_____
- Caused by: #_____
- Blocks: #_____
- Related PR: #_____

### **Configuration:**
<!-- Any relevant configuration that might be causing the issue -->
```yaml
# Relevant configuration files or environment variables
DATABASE_URL: [redacted]
REDIS_URL: [redacted] 
SERVICE_PORT: 8080
```

### **Recent Changes:**
<!-- Any recent deployments, configuration changes, or code changes? -->

---

## 🏷️ **Priority & Labels**

### **Priority Assessment:**
**Urgency:** [Low | Medium | High | Critical]  
**Impact:** [Low | Medium | High | Critical]  

**Suggested Labels:**
- [ ] `priority/critical`
- [ ] `priority/high`  
- [ ] `priority/medium`
- [ ] `priority/low`
- [ ] `component/[specific-service]`
- [ ] `architecture/[specific-layer]`
- [ ] `regression` (if caused by recent change)
- [ ] `security` (if security implications)

---

## ✅ **Definition of Done**
<!-- What needs to be done to consider this bug fixed? -->

**Fix Verification:**
- [ ] Bug no longer reproducible
- [ ] Automated test added to prevent regression
- [ ] Code review completed
- [ ] Clean Architecture compliance verified
- [ ] Performance impact assessed
- [ ] Security implications reviewed (if applicable)
- [ ] Documentation updated (if needed)

**Testing Requirements:**
- [ ] Unit tests added/updated
- [ ] Integration tests cover the fix
- [ ] Manual testing completed
- [ ] Regression testing passed

---

**Reported by:** @[username]  
**Date:** [Today's date]  
**Environment:** [Development | Staging | Production]  
**Urgency:** [When does this need to be fixed?]