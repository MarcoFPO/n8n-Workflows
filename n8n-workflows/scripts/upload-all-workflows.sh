#!/bin/bash
# Upload alle Zabbix Sub-Workflows zu n8n
# Erstellt von Claude Code

set -e

# Lade API Config
source /home/mdoehler/.config/n8n/api_config.sh

WORKFLOW_DIR="/opt/Projekte/n8n-workflows/workflows"
LOG_FILE="/opt/Projekte/n8n-workflows/logs/upload-$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$(dirname "$LOG_FILE")"

echo "========================================" | tee -a "$LOG_FILE"
echo "n8n Workflow Upload" | tee -a "$LOG_FILE"
echo "$(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Workflows in der richtigen Reihenfolge hochladen
WORKFLOWS=(
  "sub1-problem-erfassung.json"
  "sub2-root-cause-analyse.json"
  "sub3-entscheidung-loesbarkeit.json"
  "sub4-remote-loesung.json"
  "sub5-user-benachrichtigung.json"
  "master-zabbix-orchestrator.json"
)

for workflow_file in "${WORKFLOWS[@]}"; do
  workflow_path="$WORKFLOW_DIR/$workflow_file"

  if [ ! -f "$workflow_path" ]; then
    echo "❌ Workflow nicht gefunden: $workflow_file" | tee -a "$LOG_FILE"
    continue
  fi

  echo "📤 Uploading: $workflow_file" | tee -a "$LOG_FILE"

  # Upload Workflow
  response=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "X-N8N-API-KEY: $N8N_API_KEY" \
    -H "Content-Type: application/json" \
    --data "@$workflow_path" \
    "$N8N_API_URL/workflows")

  # Parse Response
  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | sed '$d')

  if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
    workflow_id=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "unknown")
    workflow_name=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin)['name'])" 2>/dev/null || echo "unknown")
    echo "✅ Erfolgreich: $workflow_name (ID: $workflow_id)" | tee -a "$LOG_FILE"
    echo "   File: $workflow_file → ID: $workflow_id" >> "$WORKFLOW_DIR/../docs/workflow-ids.txt"
  else
    echo "❌ Fehler bei Upload: HTTP $http_code" | tee -a "$LOG_FILE"
    echo "   Response: $body" | tee -a "$LOG_FILE"
  fi

  echo "" | tee -a "$LOG_FILE"
  sleep 1
done

echo "========================================" | tee -a "$LOG_FILE"
echo "Upload abgeschlossen!" | tee -a "$LOG_FILE"
echo "Log gespeichert: $LOG_FILE" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
