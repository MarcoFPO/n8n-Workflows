#!/bin/bash
export PYTHONPATH=/opt/aktienanalyse-ökosystem:/opt/aktienanalyse-ökosystem/shared:/opt/aktienanalyse-ökosystem/services/event-bus-service-modular
export EVENT_BUS_SERVICE_PORT=8014

# PostgreSQL Configuration
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=aktienanalyse_events
export DB_USER=aktienanalyse
export DB_PASSWORD=secure_password

# Redis Configuration
export REDIS_URL=redis://localhost:6379/1

# RabbitMQ Configuration
export RABBITMQ_URL=amqp://guest:guest@localhost:5672/

cd /opt/aktienanalyse-ökosystem/services/event-bus-service-modular
/opt/aktienanalyse-ökosystem/venv-modular/bin/python event_bus_with_postgres.py