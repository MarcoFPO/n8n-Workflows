#!/bin/bash
export PYTHONPATH=/opt/aktienanalyse-ökosystem:/opt/aktienanalyse-ökosystem/shared:/opt/aktienanalyse-ökosystem/services/monitoring-service-modular
export MONITORING_SERVICE_PORT=8015

cd /opt/aktienanalyse-ökosystem/services/monitoring-service-modular
/opt/aktienanalyse-ökosystem/venv-modular/bin/python monitoring_orchestrator.py