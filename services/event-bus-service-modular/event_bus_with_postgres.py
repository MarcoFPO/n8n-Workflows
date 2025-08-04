"""
Event-Bus Service mit PostgreSQL Event-Store Integration
Erweitert den bestehenden Event-Bus um persistente PostgreSQL-Speicherung
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

import redis.asyncio as aioredis
import aio_pika
import asyncpg
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("event-bus-postgres")

# Pydantic Models
class EventMessage(BaseModel):
    event_type: str
    stream_id: Optional[str] = None
    data: Dict[str, Any]
    source: str
    correlation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class EventQuery(BaseModel):
    event_types: Optional[List[str]] = None
    sources: Optional[List[str]] = None
    limit: int = 100

class PostgreSQLEventBus:
    """Event-Bus Service mit PostgreSQL Integration"""
    
    def __init__(self):
        self.app = FastAPI(
            title="Event-Bus Service with PostgreSQL",
            description="Event-Hub mit PostgreSQL Event-Store",
            version="2.0.0"
        )
        
        # CORS aktivieren
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Connections
        self.redis_client: Optional[aioredis.Redis] = None
        self.rabbitmq_connection: Optional[aio_pika.Connection] = None
        self.postgres_pool: Optional[asyncpg.Pool] = None
        
        # Statistics
        self.published_events = 0
        self.stored_events_redis = 0
        self.stored_events_postgres = 0
        
        self._setup_routes()
        
        # Startup/Shutdown Events
        self.app.add_event_handler("startup", self.startup_event)
        self.app.add_event_handler("shutdown", self.shutdown_event)
    
    async def startup_event(self):
        """Service initialization"""
        logger.info("Starting Event-Bus Service with PostgreSQL...")
        
        try:
            # Redis Connection
            await self._init_redis()
            
            # RabbitMQ Connection
            await self._init_rabbitmq()
            
            # PostgreSQL Connection
            await self._init_postgres()
            
            logger.info("Event-Bus Service with PostgreSQL started successfully")
        except Exception as e:
            logger.error(f"Failed to start Event-Bus Service: {e}")
            raise
    
    async def shutdown_event(self):
        """Service cleanup"""
        logger.info("Shutting down Event-Bus Service...")
        
        if self.postgres_pool:
            await self.postgres_pool.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        if self.rabbitmq_connection and not self.rabbitmq_connection.is_closed:
            await self.rabbitmq_connection.close()
        
        logger.info("Event-Bus Service shut down successfully")
    
    async def _init_redis(self):
        """Redis Connection initialisieren"""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis_client = await aioredis.from_url(redis_url)
            await self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def _init_rabbitmq(self):
        """RabbitMQ Connection initialisieren"""
        try:
            rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://localhost:5672")
            self.rabbitmq_connection = await aio_pika.connect_robust(rabbitmq_url)
            logger.info("RabbitMQ connection established")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            # RabbitMQ ist optional
            logger.warning("Continuing without RabbitMQ...")
    
    async def _init_postgres(self):
        """PostgreSQL Connection Pool initialisieren"""
        try:
            db_host = os.getenv("DB_HOST", "localhost")
            db_port = int(os.getenv("DB_PORT", "5432"))
            db_name = os.getenv("DB_NAME", "aktienanalyse_events")
            db_user = os.getenv("DB_USER", "aktienanalyse")
            db_password = os.getenv("DB_PASSWORD", "secure_password")
            
            # Connection Pool erstellen
            self.postgres_pool = await asyncpg.create_pool(
                host=db_host,
                port=db_port,
                database=db_name,
                user=db_user,
                password=db_password,
                min_size=5,
                max_size=20,
                command_timeout=30
            )
            
            # Test connection
            async with self.postgres_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            
            logger.info("PostgreSQL connection pool established")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    def _setup_routes(self):
        """API-Routen registrieren"""
        
        @self.app.get("/")
        async def root():
            return {
                "service": "event-bus-postgres",
                "version": "2.0.0",
                "status": "running",
                "port": 8014,
                "published_events": self.published_events,
                "stored_events_redis": self.stored_events_redis,
                "stored_events_postgres": self.stored_events_postgres
            }
        
        @self.app.get("/health")
        async def health():
            """Service Health Check"""
            redis_connected = False
            rabbitmq_connected = False
            postgres_connected = False
            
            try:
                if self.redis_client:
                    await self.redis_client.ping()
                    redis_connected = True
            except:
                pass
            
            try:
                if self.rabbitmq_connection:
                    rabbitmq_connected = not self.rabbitmq_connection.is_closed
            except:
                pass
            
            try:
                if self.postgres_pool:
                    async with self.postgres_pool.acquire() as conn:
                        await conn.fetchval("SELECT 1")
                    postgres_connected = True
            except:
                pass
            
            return {
                "status": "healthy" if postgres_connected else "degraded",
                "service": "event-bus-postgres",
                "redis_connected": redis_connected,
                "rabbitmq_connected": rabbitmq_connected,
                "postgres_connected": postgres_connected,
                "published_events": self.published_events,
                "stored_events_redis": self.stored_events_redis,
                "stored_events_postgres": self.stored_events_postgres
            }
        
        @self.app.post("/events/publish")
        async def publish_event(event: EventMessage):
            """Event publizieren und in Event-Store speichern"""
            try:
                # Event ID generieren
                event_id = str(uuid4())
                stream_id = event.stream_id or f"event-{event_id[:8]}"
                
                # Event-Daten zusammenstellen
                event_data = {
                    "id": event_id,
                    "stream_id": stream_id,
                    "event_type": event.event_type,
                    "data": event.data,
                    "source": event.source,
                    "correlation_id": event.correlation_id,
                    "metadata": event.metadata or {},
                    "timestamp": datetime.utcnow().isoformat(),
                    "published_by": "event-bus-postgres"
                }
                
                # Parallel speichern: Redis + PostgreSQL + RabbitMQ
                tasks = []
                
                # Redis Storage
                if self.redis_client:
                    tasks.append(self._store_event_redis(event_data))
                
                # PostgreSQL Storage
                if self.postgres_pool:
                    tasks.append(self._store_event_postgres(event_data))
                
                # RabbitMQ Publishing
                if self.rabbitmq_connection and not self.rabbitmq_connection.is_closed:
                    tasks.append(self._publish_to_rabbitmq(event_data))
                
                # Alle Tasks parallel ausführen
                await asyncio.gather(*tasks, return_exceptions=True)
                
                self.published_events += 1
                
                return {
                    "status": "published",
                    "event_id": event_id,
                    "stream_id": stream_id,
                    "event_type": event.event_type,
                    "timestamp": event_data["timestamp"],
                    "stored_in": ["redis", "postgres", "rabbitmq"] if len(tasks) == 3 else ["postgres"]
                }
                
            except Exception as e:
                logger.error(f"Failed to publish event: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/events/query")
        async def query_events(event_types: Optional[str] = None, sources: Optional[str] = None, limit: int = 100):
            """Events aus PostgreSQL Event-Store abfragen"""
            try:
                if not self.postgres_pool:
                    raise HTTPException(status_code=503, detail="PostgreSQL not connected")
                
                # SQL Query zusammenstellen
                where_conditions = []
                params = []
                param_count = 0
                
                if event_types:
                    event_type_list = [t.strip() for t in event_types.split(",")]
                    param_count += 1
                    where_conditions.append(f"event_type = ANY(${param_count})")
                    params.append(event_type_list)
                
                if sources:
                    source_list = [s.strip() for s in sources.split(",")]
                    param_count += 1
                    where_conditions.append(f"event_data->>'source' = ANY(${param_count})")
                    params.append(source_list)
                
                where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                param_count += 1
                
                query = f"""
                SELECT 
                    event_id,
                    stream_id,
                    event_type,
                    event_data,
                    metadata,
                    created_at
                FROM events 
                {where_clause}
                ORDER BY created_at DESC 
                LIMIT ${param_count}
                """
                
                params.append(limit)
                
                async with self.postgres_pool.acquire() as conn:
                    rows = await conn.fetch(query, *params)
                
                events = []
                for row in rows:
                    events.append({
                        "event_id": str(row["event_id"]),
                        "stream_id": row["stream_id"],
                        "event_type": row["event_type"],
                        "event_data": row["event_data"],
                        "metadata": row["metadata"],
                        "created_at": row["created_at"].isoformat()
                    })
                
                return {
                    "events": events,
                    "count": len(events),
                    "source": "postgres"
                }
                
            except Exception as e:
                logger.error(f"Failed to query events from PostgreSQL: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/events/stream/{stream_id}")
        async def get_stream_events(stream_id: str, from_version: int = 1):
            """Events für einen bestimmten Stream aus PostgreSQL abrufen"""
            try:
                if not self.postgres_pool:
                    raise HTTPException(status_code=503, detail="PostgreSQL not connected")
                
                query = """
                SELECT 
                    event_id,
                    event_type,
                    event_version,
                    event_data,
                    metadata,
                    created_at
                FROM events 
                WHERE stream_id = $1 
                AND event_version >= $2
                ORDER BY event_version
                """
                
                async with self.postgres_pool.acquire() as conn:
                    rows = await conn.fetch(query, stream_id, from_version)
                
                events = []
                for row in rows:
                    events.append({
                        "event_id": str(row["event_id"]),
                        "event_type": row["event_type"],
                        "event_version": row["event_version"],
                        "event_data": row["event_data"],
                        "metadata": row["metadata"],
                        "created_at": row["created_at"].isoformat()
                    })
                
                return {
                    "stream_id": stream_id,
                    "events": events,
                    "count": len(events),
                    "from_version": from_version
                }
                
            except Exception as e:
                logger.error(f"Failed to get stream events: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/statistics")
        async def statistics():
            """Service-Statistiken"""
            redis_stats = {"connected": False, "keys_count": 0}
            postgres_stats = {"connected": False, "total_events": 0}
            
            try:
                if self.redis_client:
                    await self.redis_client.ping()
                    redis_stats["connected"] = True
                    redis_stats["keys_count"] = await self.redis_client.dbsize()
            except:
                pass
            
            try:
                if self.postgres_pool:
                    async with self.postgres_pool.acquire() as conn:
                        count = await conn.fetchval("SELECT COUNT(*) FROM events")
                        postgres_stats["connected"] = True
                        postgres_stats["total_events"] = count
            except:
                pass
            
            return {
                "service": "event-bus-postgres",
                "status": "running",
                "published_events": self.published_events,
                "stored_events_redis": self.stored_events_redis,
                "stored_events_postgres": self.stored_events_postgres,
                "redis": redis_stats,
                "postgres": postgres_stats,
                "rabbitmq": {
                    "connected": self.rabbitmq_connection and not self.rabbitmq_connection.is_closed
                }
            }
    
    async def _store_event_redis(self, event_data: Dict[str, Any]):
        """Event in Redis speichern"""
        try:
            event_id = event_data["id"]
            event_key = f"event:{event_id}"
            
            # Event speichern
            await self.redis_client.hset(event_key, mapping={
                "data": json.dumps(event_data),
                "event_type": event_data["event_type"],
                "source": event_data["source"],
                "timestamp": event_data["timestamp"]
            })
            
            # Event-Type Index
            event_type = event_data["event_type"]
            await self.redis_client.sadd(f"events:type:{event_type}", event_id)
            
            # Global Event List
            await self.redis_client.lpush("events:all", event_id)
            await self.redis_client.ltrim("events:all", 0, 9999)  # Limit to 10k events
            
            self.stored_events_redis += 1
            logger.debug(f"Event stored in Redis: {event_id}")
            
        except Exception as e:
            logger.error(f"Failed to store event in Redis: {e}")
            raise
    
    async def _store_event_postgres(self, event_data: Dict[str, Any]):
        """Event in PostgreSQL Event-Store speichern"""
        try:
            # Stream Type aus Stream ID ableiten
            stream_id = event_data["stream_id"]
            
            if stream_id.startswith("stock-"):
                stream_type = "stock"
            elif stream_id.startswith("portfolio-"):
                stream_type = "portfolio"
            elif stream_id.startswith("trading-"):
                stream_type = "trading"
            else:
                stream_type = "system"
            
            # Event Version bestimmen (nächste Version für den Stream)
            async with self.postgres_pool.acquire() as conn:
                current_version = await conn.fetchval(
                    "SELECT COALESCE(MAX(event_version), 0) FROM events WHERE stream_id = $1",
                    stream_id
                )
                
                next_version = (current_version or 0) + 1
                
                # Event inserieren
                await conn.execute("""
                    INSERT INTO events (
                        stream_id, 
                        aggregate_type,
                        event_type, 
                        event_version,
                        aggregate_id,
                        event_data, 
                        metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, 
                    stream_id,
                    stream_type,
                    event_data["event_type"],
                    next_version,
                    stream_id,  # aggregate_id = stream_id
                    json.dumps(event_data["data"]),
                    json.dumps(event_data.get("metadata", {}))
                )
            
            self.stored_events_postgres += 1
            logger.debug(f"Event stored in PostgreSQL: {event_data['id']}")
            
        except Exception as e:
            logger.error(f"Failed to store event in PostgreSQL: {e}")
            raise
    
    async def _publish_to_rabbitmq(self, event_data: Dict[str, Any]):
        """Event zu RabbitMQ publishen"""
        try:
            if not self.rabbitmq_connection or self.rabbitmq_connection.is_closed:
                return
            
            channel = await self.rabbitmq_connection.channel()
            
            # Exchange erstellen/verwenden
            exchange = await channel.declare_exchange(
                "aktienanalyse.events",
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            
            # Routing Key aus Event Type ableiten
            routing_key = event_data["event_type"].replace(".", "_")
            
            # Message publishen
            message = aio_pika.Message(
                json.dumps(event_data).encode(),
                headers={"event_type": event_data["event_type"], "source": event_data["source"]}
            )
            
            await exchange.publish(message, routing_key=routing_key)
            await channel.close()
            
            logger.debug(f"Event published to RabbitMQ: {routing_key}")
            
        except Exception as e:
            logger.error(f"Failed to publish to RabbitMQ: {e}")


def main():
    """Main entry point"""
    event_bus = PostgreSQLEventBus()
    
    # Uvicorn-Server konfiguration
    config = uvicorn.Config(
        app=event_bus.app,
        host="0.0.0.0",
        port=8014,
        log_level="info",
        access_log=True
    )
    
    server = uvicorn.Server(config)
    
    logger.info("Event-Bus Service with PostgreSQL starting on port 8014...")
    
    try:
        server.run()
    except KeyboardInterrupt:
        logger.info("Event-Bus Service stopped by user")
    except Exception as e:
        logger.error(f"Event-Bus Service crashed: {e}")
        raise


if __name__ == "__main__":
    main()