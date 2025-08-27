---
name: 🐛 Bug Report (Intelligence-Enhanced)
about: Report a bug with automatic severity analysis and expert team routing
title: '[BUG] '
labels: ['type:bug-report']
assignees: []
---

## 🚨 Bug Description
<!-- Provide a clear and concise description of the bug -->

## 📍 Production Impact Assessment
<!-- The system will auto-analyze severity based on these indicators -->
- [ ] **Production Outage** - Service completely unavailable
- [ ] **Service Degradation** - Reduced functionality or performance
- [ ] **User Experience Impact** - Users cannot complete key workflows
- [ ] **Data Integrity Issue** - Data corruption or loss risk
- [ ] **Security Vulnerability** - Potential security breach
- [ ] **SLA Violation** - Response time >0.12s or availability <99.9%
- [ ] **Revenue Impact** - Direct financial loss

## 🔄 Reproduction Steps
<!-- Detailed steps to reproduce the issue -->
1. Step one
2. Step two
3. Step three
4. Expected vs Actual result

## 📊 Performance Impact
<!-- Critical for SLA violation detection and performance team routing -->
- **Current Response Time:** <!-- Actual measured response time -->
- **Target Response Time:** <!-- <0.12s SLA requirement -->
- **Throughput Impact:** <!-- Requests per minute affected -->
- **Resource Usage:** <!-- CPU, Memory, Disk usage -->
- **Error Rate:** <!-- Percentage of failed requests -->

## 🏗️ Architecture Context
<!-- For Clean Architecture impact analysis and team routing -->
- **Affected Service(s):** <!-- Which microservices are impacted -->
- **Architecture Layer:** <!-- Domain/Application/Infrastructure/Presentation -->
- **Integration Points:** <!-- External APIs, databases, message queues -->
- **Event Bus Impact:** <!-- Redis Pub/Sub, event sourcing affected -->

## 📝 Error Logs and Stack Traces
```
<!-- Paste complete error logs, stack traces, and relevant system logs -->
```

## 🔧 Environment Information
<!-- System context for environment-specific debugging -->
- **Server:** <!-- 10.1.1.174 or specific server -->
- **Service Version:** <!-- e.g., v6.1.0 -->
- **Python Version:** <!-- e.g., 3.11 -->
- **Browser/Client:** <!-- if applicable -->
- **Database:** <!-- PostgreSQL version, connection info -->
- **Redis:** <!-- Cache/Event bus status -->

## 🔍 Investigation Details
<!-- Additional context for root cause analysis -->
- **First Occurred:** <!-- When did this bug first appear -->
- **Frequency:** <!-- How often does it occur -->
- **Pattern:** <!-- Does it happen under specific conditions -->
- **Recent Changes:** <!-- Any recent deployments or configuration changes -->
- **Related Issues:** <!-- Link to similar or related issues -->

## 💡 Potential Root Cause
<!-- If you have hypotheses about the cause -->
- **Suspected Component:** 
- **Possible Cause:** 
- **Related Code Changes:** 

## 🚑 Immediate Workaround
<!-- Temporary solution if available -->
- **Workaround Available:** [ ] Yes [ ] No
- **Workaround Description:** 
- **Workaround Limitations:** 

## 📋 Testing Requirements
<!-- How to validate the fix -->
- [ ] Unit tests for affected components
- [ ] Integration tests for service interactions
- [ ] Performance tests for SLA compliance
- [ ] Regression tests to prevent recurrence
- [ ] Load testing if performance-related

---
<!-- 🤖 AUTO-ANALYSIS WILL POPULATE:
- Severity Level (Critical/High/Medium/Low based on production impact)
- Urgency Score (0-10 based on business impact and SLA violations)  
- Team Assignment (Backend/DevOps/Performance/Security based on context)
- Clean Architecture Compliance Impact Assessment
- Performance SLA Violation Detection and Escalation
- Pattern Matching with Historical Bugs
- Root Cause Analysis Suggestions
- Estimated Resolution Time based on Complexity
-->