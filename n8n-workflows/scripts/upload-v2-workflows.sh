#!/bin/bash

# Zabbix Workflow V2 Upload Script
# Uploads event-based workflows to n8n

set -e

# Configuration
N8N_URL="http://10.1.1.180/api/v1"
API_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5ZDk0ZDFhYy1jMmZmLTQ5YTItOTFlMC1hMTRmOGU0ZDc2MjYiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzYwMDM3MzAxfQ.tZ72KsjUc6EuuWm5ZeTz1loMPmcMtMjO2B7ABA5dsiA"
WORKFLOWS_DIR="/opt/Projekte/n8n-workflows/workflows"

echo "================================================"
echo "Zabbix Workflow V2 Upload"
echo "================================================"
echo ""

# Function to upload a workflow
upload_workflow() {
    local file=$1
    local name=$(basename "$file" .json)

    echo "Uploading: $name"
    echo "  File: $file"

    # Upload workflow
    response=$(curl -s -w "\n%{http_code}" -X POST "$N8N_URL/workflows" \
        -H "X-N8N-API-KEY: $API_KEY" \
        -H "Content-Type: application/json" \
        -d @"$file")

    # Split response and status code
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 201 ]; then
        workflow_id=$(echo "$body" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
        echo "  ✓ Success! Workflow ID: $workflow_id"
        echo "  URL: http://10.1.1.180/workflow/$workflow_id"
        echo ""

        # Save to workflow-ids-v2.txt
        echo "$name → ID: $workflow_id" >> "$WORKFLOWS_DIR/../docs/workflow-ids-v2.txt"
    else
        echo "  ✗ Failed! HTTP $http_code"
        echo "  Response: $body"
        echo ""
        exit 1
    fi
}

# Initialize workflow IDs file
echo "# Zabbix Workflow V2 - Workflow IDs" > "$WORKFLOWS_DIR/../docs/workflow-ids-v2.txt"
echo "# Erstellt: $(date '+%Y-%m-%d %H:%M:%S')" >> "$WORKFLOWS_DIR/../docs/workflow-ids-v2.txt"
echo "" >> "$WORKFLOWS_DIR/../docs/workflow-ids-v2.txt"

# Check if workflows exist
if [ ! -f "$WORKFLOWS_DIR/sub1-problem-erfassung-v2.json" ]; then
    echo "Error: V2 workflow files not found in $WORKFLOWS_DIR"
    exit 1
fi

# Upload workflows in correct order
echo "Uploading V2 Workflows..."
echo ""

# Sub-1 V2 (Event Receiver)
upload_workflow "$WORKFLOWS_DIR/sub1-problem-erfassung-v2.json"

# Master V2 (Event Processor)
upload_workflow "$WORKFLOWS_DIR/master-zabbix-orchestrator-v2.json"

# Note: Sub-2, Sub-3, Sub-4, Sub-5 remain unchanged from V1
echo "================================================"
echo "Note: Sub-2, Sub-3, Sub-4, Sub-5 remain from V1"
echo "Only Sub-1 and Master have V2 versions"
echo "================================================"
echo ""

echo "✓ All V2 workflows uploaded successfully!"
echo ""
echo "Next Steps:"
echo "1. Configure Zabbix Action (see docs/zabbix-action-configuration.md)"
echo "2. Test with manual webhook:"
echo "   curl -X POST http://10.1.1.180/webhook/zabbix-event \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"eventid\":\"12345\",\"name\":\"Test Problem\",\"severity\":\"3\",\"host\":\"test-server\"}'"
echo ""
echo "3. Monitor Redis queue:"
echo "   redis-cli LLEN zabbix:event:queue"
echo "   redis-cli GET zabbix:event:counter"
echo ""
echo "4. Trigger Master manually:"
echo "   curl -X POST http://10.1.1.180/webhook/master-zabbix-processor \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"trigger\":\"manual\"}'"
echo ""
echo "Workflow IDs saved to: docs/workflow-ids-v2.txt"
