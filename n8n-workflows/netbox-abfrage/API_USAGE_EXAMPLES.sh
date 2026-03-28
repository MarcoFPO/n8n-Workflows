#!/bin/bash
# N8N Workflow API Usage Examples
# Workflow ID: qQXIZPWmuFR6ylWC
# Server: http://10.1.1.180

# Configuration
API_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5ZDk0ZDFhYy1jMmZmLTQ5YTItOTFlMC1hMTRmOGU0ZDc2MjYiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzYwMDM3MzAxfQ.tZ72KsjUc6EuuWm5ZeTz1loMPmcMtMjO2B7ABA5dsiA"
SERVER="http://10.1.1.180"
WORKFLOW_ID="qQXIZPWmuFR6ylWC"

echo "=================================================================================="
echo "N8N Workflow API - Usage Examples"
echo "=================================================================================="
echo ""
echo "Server:        $SERVER"
echo "Workflow ID:   $WORKFLOW_ID"
echo ""

# ============================================================================
# 1. GET WORKFLOW DETAILS
# ============================================================================
echo "[1] Get Workflow Details"
echo "------"
echo "Get complete information about the deployed workflow"
echo ""
echo "Command:"
echo "curl -X GET $SERVER/api/v1/workflows/$WORKFLOW_ID \\"
echo "  -H \"X-N8N-API-KEY: \$API_KEY\" \\"
echo "  -H \"Content-Type: application/json\""
echo ""
echo "Usage:"
curl -s -X GET $SERVER/api/v1/workflows/$WORKFLOW_ID \
  -H "X-N8N-API-KEY: $API_KEY" \
  -H "Content-Type: application/json" | python3 -m json.tool 2>/dev/null | head -30
echo ""
echo "..."
echo ""

# ============================================================================
# 2. LIST ALL WORKFLOWS
# ============================================================================
echo "[2] List All Workflows"
echo "------"
echo "Get a list of all workflows on the server"
echo ""
echo "Command:"
echo "curl -X GET $SERVER/api/v1/workflows \\"
echo "  -H \"X-N8N-API-KEY: \$API_KEY\""
echo ""
echo "Usage:"
curl -s -X GET $SERVER/api/v1/workflows \
  -H "X-N8N-API-KEY: $API_KEY" | python3 -m json.tool 2>/dev/null | head -50
echo ""
echo "..."
echo ""

# ============================================================================
# 3. DEPLOY WORKFLOW (POST)
# ============================================================================
echo "[3] Deploy New Workflow (POST)"
echo "------"
echo "Deploy a workflow from JSON file"
echo ""
echo "Command:"
echo "curl -X POST $SERVER/api/v1/workflows \\"
echo "  -H \"X-N8N-API-KEY: \$API_KEY\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d @test-workflow.json"
echo ""
echo "Example JSON Structure (minimal required):"
cat << 'EOF'
{
  "name": "Workflow Name",
  "settings": {
    "executionOrder": "v1"
  },
  "nodes": [
    {
      "parameters": {},
      "id": "node-1",
      "name": "Node Name",
      "type": "n8n-nodes-base.manualTrigger",
      "typeVersion": 1,
      "position": [240, 240]
    }
  ],
  "connections": {
    "Node Name": {
      "main": [[]]
    }
  }
}
EOF
echo ""

# ============================================================================
# 4. UPDATE WORKFLOW (PUT)
# ============================================================================
echo "[4] Update Workflow (PUT)"
echo "------"
echo "Update an existing workflow"
echo ""
echo "Command:"
echo "curl -X PUT $SERVER/api/v1/workflows/$WORKFLOW_ID \\"
echo "  -H \"X-N8N-API-KEY: \$API_KEY\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d @workflow-updated.json"
echo ""
echo "Note: PUT requires all workflow fields (name, nodes, connections, settings)"
echo ""

# ============================================================================
# 5. ACTIVATE WORKFLOW
# ============================================================================
echo "[5] Activate Workflow"
echo "------"
echo "Enable automatic execution of the workflow"
echo ""
echo "Command:"
echo "curl -X POST $SERVER/api/v1/workflows/$WORKFLOW_ID/activate \\"
echo "  -H \"X-N8N-API-KEY: \$API_KEY\""
echo ""

# ============================================================================
# 6. DEACTIVATE WORKFLOW
# ============================================================================
echo "[6] Deactivate Workflow"
echo "------"
echo "Disable automatic execution of the workflow"
echo ""
echo "Command:"
echo "curl -X POST $SERVER/api/v1/workflows/$WORKFLOW_ID/deactivate \\"
echo "  -H \"X-N8N-API-KEY: \$API_KEY\""
echo ""

# ============================================================================
# 7. DELETE WORKFLOW
# ============================================================================
echo "[7] Delete Workflow"
echo "------"
echo "Remove the workflow from the server (WARNING: cannot be undone)"
echo ""
echo "Command:"
echo "curl -X DELETE $SERVER/api/v1/workflows/$WORKFLOW_ID \\"
echo "  -H \"X-N8N-API-KEY: \$API_KEY\""
echo ""

# ============================================================================
# 8. EXECUTE WORKFLOW (LIMITED)
# ============================================================================
echo "[8] Execute Workflow"
echo "------"
echo "Trigger manual workflow execution (may be restricted by API)"
echo ""
echo "Command:"
echo "curl -X POST $SERVER/api/v1/workflows/$WORKFLOW_ID/execute \\"
echo "  -H \"X-N8N-API-KEY: \$API_KEY\""
echo ""
echo "Note: This may return 405 Method Not Allowed. Use Web UI instead."
echo ""

# ============================================================================
# PYTHON EXAMPLE
# ============================================================================
echo "[PYTHON] Complete Python Script Example"
echo "------"
cat << 'PYEOF'
#!/usr/bin/env python3
import requests
import json

# Configuration
API_KEY = "your-api-key"
SERVER = "http://10.1.1.180"
WORKFLOW_ID = "qQXIZPWmuFR6ylWC"

headers = {
    "X-N8N-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

# Get workflow details
def get_workflow(workflow_id):
    response = requests.get(
        f"{SERVER}/api/v1/workflows/{workflow_id}",
        headers=headers
    )
    return response.json()

# List all workflows
def list_workflows():
    response = requests.get(
        f"{SERVER}/api/v1/workflows",
        headers=headers
    )
    return response.json()

# Create new workflow
def create_workflow(workflow_data):
    response = requests.post(
        f"{SERVER}/api/v1/workflows",
        json=workflow_data,
        headers=headers
    )
    return response.json()

# Update workflow
def update_workflow(workflow_id, workflow_data):
    response = requests.put(
        f"{SERVER}/api/v1/workflows/{workflow_id}",
        json=workflow_data,
        headers=headers
    )
    return response.json()

# Activate workflow
def activate_workflow(workflow_id):
    response = requests.post(
        f"{SERVER}/api/v1/workflows/{workflow_id}/activate",
        headers=headers
    )
    return response.json()

# Deactivate workflow
def deactivate_workflow(workflow_id):
    response = requests.post(
        f"{SERVER}/api/v1/workflows/{workflow_id}/deactivate",
        headers=headers
    )
    return response.json()

# Delete workflow
def delete_workflow(workflow_id):
    response = requests.delete(
        f"{SERVER}/api/v1/workflows/{workflow_id}",
        headers=headers
    )
    return response.status_code

# Example usage
if __name__ == "__main__":
    # Get workflow info
    workflow = get_workflow(WORKFLOW_ID)
    print(f"Workflow: {workflow['name']}")
    print(f"Active: {workflow['active']}")
    print(f"Nodes: {len(workflow['nodes'])}")
PYEOF
echo ""

# ============================================================================
# cURL HELPER FUNCTIONS
# ============================================================================
echo "[BASH] cURL Helper Functions"
echo "------"
cat << 'BASHEOF'
#!/bin/bash
# Add to your ~/.bashrc or use in scripts

API_KEY="your-api-key"
SERVER="http://10.1.1.180"

n8n_get_workflow() {
    local wf_id=$1
    curl -s -X GET "$SERVER/api/v1/workflows/$wf_id" \
        -H "X-N8N-API-KEY: $API_KEY" | python3 -m json.tool
}

n8n_list_workflows() {
    curl -s -X GET "$SERVER/api/v1/workflows" \
        -H "X-N8N-API-KEY: $API_KEY" | python3 -m json.tool
}

n8n_activate_workflow() {
    local wf_id=$1
    curl -s -X POST "$SERVER/api/v1/workflows/$wf_id/activate" \
        -H "X-N8N-API-KEY: $API_KEY" | python3 -m json.tool
}

n8n_deactivate_workflow() {
    local wf_id=$1
    curl -s -X POST "$SERVER/api/v1/workflows/$wf_id/deactivate" \
        -H "X-N8N-API-KEY: $API_KEY" | python3 -m json.tool
}

# Usage:
# n8n_get_workflow qQXIZPWmuFR6ylWC
# n8n_list_workflows
# n8n_activate_workflow qQXIZPWmuFR6ylWC
BASHEOF
echo ""

# ============================================================================
# USEFUL FILTERS
# ============================================================================
echo "[JQ] Useful jq Filters for JSON Processing"
echo "------"
cat << 'EOF'
# Get workflow ID from list
curl -s "$SERVER/api/v1/workflows" -H "X-N8N-API-KEY: $API_KEY" | \
  jq '.data[] | select(.name == "Workflow Name") | .id'

# Get all workflow names and IDs
curl -s "$SERVER/api/v1/workflows" -H "X-N8N-API-KEY: $API_KEY" | \
  jq '.data[] | {id: .id, name: .name, active: .active}'

# Get node names from workflow
curl -s "$SERVER/api/v1/workflows/$WORKFLOW_ID" -H "X-N8N-API-KEY: $API_KEY" | \
  jq '.nodes[] | {name: .name, type: .type}'

# Check if workflow is active
curl -s "$SERVER/api/v1/workflows/$WORKFLOW_ID" -H "X-N8N-API-KEY: $API_KEY" | \
  jq '.active'
EOF
echo ""

echo "=================================================================================="
echo "For more information, see:"
echo "  - DEPLOYMENT_SUMMARY.txt"
echo "  - DEPLOYMENT_REPORT.md"
echo "  - ERROR_RESOLUTION.md"
echo "=================================================================================="
