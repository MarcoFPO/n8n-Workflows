#!/bin/bash
# Start script for Diagnostic Service

export PYTHONPATH=/opt/aktienanalyse-ökosystem:/opt/aktienanalyse-ökosystem/shared:/opt/aktienanalyse-ökosystem/services/diagnostic-service
export DIAGNOSTIC_SERVICE_PORT=8013

# Redis and RabbitMQ configuration
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_DB=0
export RABBITMQ_HOST=localhost
export RABBITMQ_PORT=5672
export RABBITMQ_USER=guest
export RABBITMQ_PASSWORD=guest

cd /opt/aktienanalyse-ökosystem/services/diagnostic-service
exec /opt/aktienanalyse-ökosystem/venv-modular/bin/python diagnostic_orchestrator.py