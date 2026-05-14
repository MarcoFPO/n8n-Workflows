# n8n Modular Workflows - Module System

**Version:** 2.0
**Status:** In Development
**Dokumentation:** ../MODULE_SPECIFICATION.md

---

## 📚 ÜBERSICHT

Dieses Verzeichnis enthält alle **wiederverwendbaren, parametrizierten n8n-Workflow-Module** in einer 4-Tier-Hierarchie.

### Module sind...
- ✅ **Selbstständig:** Können unabhängig getestet und deployed werden
- ✅ **Parametrisiert:** Input/Output via standardisierte JSON-Schemas
- ✅ **Dokumentiert:** Jedes Modul hat vollständige API-Dokumentation
- ✅ **Getestet:** Unit + Integration Tests im `/tests` Verzeichnis
- ✅ **Versioniert:** Versions-Tagging für Breaking-Change Management

---

## 🏗️ 4-TIER ARCHITEKTUR

```
┌─────────────────────────────────────────┐
│ TIER 4: ORCHESTRATION                   │
│ Master-Workflows, Event-Handlers        │
└────────────────────┬────────────────────┘
                     │ nutzt
┌────────────────────▼────────────────────┐
│ TIER 3: FUNCTIONAL MODULES              │
│ Log-Analyse, Health-Checks, Updates     │
└────────────────────┬────────────────────┘
                     │ nutzt
┌────────────────────▼────────────────────┐
│ TIER 2: PLATFORM MODULES                │
│ VM, LXC, Device (Router) Operationen    │
└────────────────────┬────────────────────┘
                     │ nutzt
┌────────────────────▼────────────────────┐
│ TIER 1: PRIMITIVES                      │
│ SSH, HTTP, Validation, Formatting       │
└─────────────────────────────────────────┘
```

---

## 📁 DIRECTORY STRUCTURE

```
modules/
├─ primitives/                          [Tier 1: Low-Level Operations]
│  ├─ ssh-command-executor.json
│  ├─ http-request-wrapper.json
│  ├─ json-schema-validator.json
│  ├─ result-formatter.json
│  ├─ tests/
│  │  ├─ ssh-executor.test.json
│  │  ├─ http-wrapper.test.json
│  │  ├─ validator.test.json
│  │  └─ formatter.test.json
│  └─ README.md
│
├─ platforms/                           [Tier 2: System-Specific Ops]
│  ├─ vm-operations.json
│  ├─ lxc-operations.json
│  ├─ device-operations.json
│  ├─ tests/
│  │  ├─ vm-operations.test.json
│  │  ├─ lxc-operations.test.json
│  │  └─ device-operations.test.json
│  └─ README.md
│
├─ functional/                          [Tier 3: Business Logic]
│  ├─ unified-log-analyser.json
│  ├─ unified-health-checker.json
│  ├─ unified-system-updater.json
│  ├─ issue-aggregator.json
│  ├─ tests/
│  │  ├─ log-analyser.test.json
│  │  ├─ health-checker.test.json
│  │  ├─ system-updater.test.json
│  │  └─ issue-aggregator.test.json
│  └─ README.md
│
├─ orchestration/                       [Tier 4: Master Workflows]
│  ├─ master-orchestrator.json
│  ├─ master-incident-handler.json
│  ├─ tests/
│  │  ├─ orchestrator.test.json
│  │  └─ incident-handler.test.json
│  └─ README.md
│
├─ IMPLEMENTATION_NOTES.md              [Design decisions, patterns]
├─ TESTING_GUIDE.md                     [How to test modules]
├─ README.md                            [This file]
└─ VERSION_HISTORY.md                   [Version tracking]
```

---

## 🚀 QUICK START: USING A MODULE

### 1. Find the Module

```javascript
// Looking for: Execute SSH commands on a target host
Module: modules/primitives/ssh-command-executor.json
```

### 2. Check the API Contract

```bash
# Look up input/output schema
cat ../config/api-contracts.yaml | grep -A 50 "ssh_command_executor:"
```

### 3. Use in Your Workflow

```json
{
  "nodes": [
    {
      "name": "Execute SSH",
      "type": "executeWorkflow",
      "parameters": {
        "workflowId": "ssh-command-executor.json",
        "inputData": {
          "host": "10.1.1.5",
          "commands": ["/system/identity/print", "/system/resource/print"],
          "auth_method": "password",
          "username": "admin",
          "password": "BASE64ENCODED",
          "timeout_seconds": 30
        }
      }
    },
    {
      "name": "Process Results",
      "type": "code",
      "code": "return $('Execute SSH').json.results"
    }
  ]
}
```

### 4. Handle the Response

```javascript
// Standard response structure (all modules)
{
  "exit_code": "success|partial|failed",
  "session_id": "unique-id",
  "data": { /* module-specific */ },
  "timestamp": "ISO8601"
}
```

---

## 📖 MODULE STRUCTURE

Every module follows this pattern:

```json
{
  "name": "Module Name",
  "description": "What this module does",
  "version": "2.0",
  "tier": 1,
  "inputs": [
    {
      "name": "parameter_name",
      "type": "string|integer|object|array",
      "required": true|false,
      "description": "...",
      "example": "..."
    }
  ],
  "outputs": [
    {
      "name": "result",
      "type": "object",
      "description": "Standard output with exit_code, session_id, data"
    }
  ],
  "nodes": [
    {
      "name": "Input Trigger",
      "type": "n8n-nodes-base.executeWorkflowTrigger"
    },
    {
      "name": "Validation",
      "type": "n8n-nodes-base.code",
      "code": "/* Validate inputs against schema */"
    },
    {
      "name": "Main Logic",
      "type": "n8n-nodes-base.code|ssh|httpRequest"
    },
    {
      "name": "Format Output",
      "type": "n8n-nodes-base.code",
      "code": "return { exit_code: 'success', session_id, data }"
    }
  ]
}
```

---

## 🔌 CREATING A NEW MODULE

### Step 1: Define API Contract

Add to `config/api-contracts.yaml`:
```yaml
my_new_module:
  module_name: "My New Module"
  file_path: "modules/tier/my-new-module.json"
  tier: 1|2|3|4
  version: "2.0"

  input_schema:
    type: object
    required: ["param1", "param2"]
    properties:
      param1: { type: "string" }
      param2: { type: integer }

  output_schema:
    type: object
    properties:
      exit_code: { type: "string", enum: ["success", "failed"] }
      data: { type: object }
```

### Step 2: Create Module JSON

```bash
# Create file
touch modules/tier/my-new-module.json

# Copy this template:
```

```json
{
  "name": "My New Module",
  "description": "Does something useful",
  "version": "2.0",
  "tier": 1,
  "nodes": [
    {
      "name": "Input",
      "type": "n8n-nodes-base.executeWorkflowTrigger"
    },
    {
      "name": "Validate Input",
      "type": "n8n-nodes-base.code",
      "code": "
if (!$('Input').json.required_param) {
  throw new Error('required_param is required');
}
return $('Input').json;
      "
    },
    {
      "name": "Main Logic",
      "type": "n8n-nodes-base.code",
      "code": "
const result = {
  exit_code: 'success',
  session_id: require('crypto').randomUUID(),
  data: { /* your data */ },
  timestamp: new Date().toISOString()
};
return result;
      "
    }
  ]
}
```

### Step 3: Write Tests

Create `modules/tier/tests/my-new-module.test.json`:
```json
{
  "name": "Test: My New Module",
  "nodes": [
    {
      "name": "Test Case: Happy Path",
      "type": "n8n-nodes-base.code",
      "code": "
const result = await executeWorkflow('my-new-module.json', {
  required_param: 'value'
});
if (result.exit_code !== 'success') {
  throw new Error('Test failed');
}
return { status: 'PASS', message: 'Happy path works' };
      "
    }
  ]
}
```

### Step 4: Document

Add section to `modules/tier/README.md`:
```markdown
## My New Module

**Purpose:** Brief description
**Tier:** 1
**Dependencies:** List dependencies

### Input
- param1 (string, required)
- param2 (integer, optional)

### Output
- exit_code (success|failed)
- data (object with results)

### Example
[Show usage example]

### Tests
Run: `test my-new-module`
```

### Step 5: Version & Release

1. Update VERSION_HISTORY.md
2. Create git tag: `module-v2.1`
3. Test in staging
4. Deploy to production

---

## 🧪 TESTING MODULES

### Unit Tests
```bash
# Test single module
curl -X POST http://localhost:5678/webhook/test-module \
  -d '{"param1": "value1"}'
```

### Integration Tests
```bash
# Test module combination
curl -X POST http://localhost:5678/webhook/integration-test \
  -d '{
    "modules": ["module-a", "module-b"],
    "params": { "shared": "data" }
  }'
```

### Full Test Suite
```bash
# Run all tests
bash modules/run-tests.sh
```

**Expected Output:**
```
Test Results:
✅ primitives/ssh-executor ... PASS (1.2s)
✅ primitives/http-wrapper ... PASS (0.8s)
✅ platforms/vm-operations ... PASS (2.1s)
✅ functional/log-analyser ... PASS (3.5s)
✅ orchestration/master ... PASS (5.2s)

Total: 5 tests, 5 passed, 0 failed
Coverage: 86%
```

---

## 📋 MODULE CHECKLIST

When adding a new module, ensure:

- [ ] API contract defined in `config/api-contracts.yaml`
- [ ] Module JSON created with correct tier
- [ ] Input validation implemented
- [ ] Output follows standard format
- [ ] Unit tests written and passing
- [ ] Integration tests written and passing
- [ ] README documentation complete
- [ ] Examples provided
- [ ] Performance benchmarked
- [ ] Versioned in VERSION_HISTORY.md
- [ ] Approved by code review

---

## 🎯 BEST PRACTICES

### 1. Single Responsibility
Each module should do ONE thing well.

❌ Bad:
```json
{
  "name": "Log Analysis + Health Check + Update Module",
  "nodes": [/* 200+ nodes */]
}
```

✅ Good:
```json
{
  "name": "Log Analyser",
  "nodes": [/* 40 nodes, focused */]
}
```

### 2. Clear Input/Output Contracts
Always define exact expected inputs and outputs.

❌ Bad:
```javascript
// Code node without validation
const host = $('Input').json.host;  // Might be undefined
```

✅ Good:
```javascript
const { host, commands } = $('Input').json;
if (!host || !Array.isArray(commands)) {
  throw new Error('Invalid input schema');
}
```

### 3. Standardized Error Handling
All modules use same error response format.

```javascript
{
  "exit_code": "failed",
  "error": {
    "code": "SSH_TIMEOUT",
    "message": "SSH connection timed out after 30s",
    "details": { /* debug info */ }
  },
  "session_id": "...",
  "timestamp": "..."
}
```

### 4. Session Tracking
Include `session_id` for traceability.

```javascript
const sessionId = $('Input').json.session_id ||
                  require('crypto').randomUUID();
// Use throughout module for logging
```

### 5. Timeout Handling
Always respect timeout parameters.

```javascript
const timeout = $('Input').json.timeout_seconds || 60;
const startTime = Date.now();

// In loops:
if (Date.now() - startTime > timeout * 1000) {
  throw new Error(`Timeout after ${timeout}s`);
}
```

---

## 🔄 VERSION MANAGEMENT

Modules use semantic versioning:

- **2.0** - Current major version (breaking changes from v1.x)
- **2.1** - Minor update (backward compatible feature addition)
- **2.1.1** - Patch (bug fix, no functionality change)

### Breaking Changes
- Rename parameter
- Change output structure
- Remove operation

→ Increment major version (2.0 → 3.0)

### Backward Compatible
- Add optional parameter
- Add new output field
- Improve performance

→ Increment minor version (2.0 → 2.1)

### Bug Fixes
- Fix error message
- Fix timeout handling
- Fix log parsing

→ Increment patch version (2.0 → 2.0.1)

---

## 📞 TROUBLESHOOTING

### Module not found
```
Error: Module not found: "my-module.json"
```
**Solution:** Check file path in `executeWorkflow` node

### Input validation fails
```
Error: Invalid input schema: "host" is required
```
**Solution:** Provide all required fields from api-contracts.yaml

### Timeout error
```
Error: SSH execution timed out after 30s
```
**Solution:**
- Increase `timeout_seconds` parameter
- Check network latency
- Check target host load

### Performance degradation
```
Module took 15s instead of usual 2s
```
**Solution:**
- Check target host resources
- Review logs for slowness
- Consider batch size reduction

---

## 📚 REFERENCES

- **API Contracts:** `../config/api-contracts.yaml`
- **Module Spec:** `../MODULE_SPECIFICATION.md`
- **Testing Guide:** `./TESTING_GUIDE.md`
- **Implementation Notes:** `./IMPLEMENTATION_NOTES.md`
- **Migration Guide:** `../MIGRATION_GUIDE.md`

---

## 🚀 NEXT STEPS

1. Review `MODULE_SPECIFICATION.md` for detailed specs
2. Check `config/api-contracts.yaml` for your module's contract
3. Follow template above to create new modules
4. Write tests in `tests/` subdirectory
5. Update VERSION_HISTORY.md
6. Submit for review

---

**Last Updated:** 2026-01-24
**Module System Version:** 2.0
**Maintenance:** DevOps Team
