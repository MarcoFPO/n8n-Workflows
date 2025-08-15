"""
Redis Event Persistence & Recovery System
Implements event sourcing, snapshots, and disaster recovery for the event bus
"""

import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

import asyncio
import json
import zlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from shared.redis_event_bus import RedisEventBus, Event, EventMetadata, EventPriority
from shared.redis_event_bus_factory import get_event_bus

try:
    import redis.asyncio as redis
    import structlog
    logger = structlog.get_logger()
    REDIS_AVAILABLE = True
except ImportError:
    # Mock Redis for development
    class MockRedis:
        def __init__(self, *args, **kwargs): pass
        async def set(self, key, value, ex=None): return True
        async def get(self, key): return None
        async def delete(self, *keys): return 1
        async def exists(self, key): return False
        async def zadd(self, name, mapping): return 1
        async def zrange(self, name, start, end, withscores=False): return []
        async def zremrangebyscore(self, name, min_score, max_score): return 0
        async def hset(self, name, mapping): return True
        async def hgetall(self, name): return {}
        async def hdel(self, name, *keys): return 1
        async def scan_iter(self, match=None): return []
        async def pipeline(self): return MockPipeline()
        async def close(self): pass
    
    class MockPipeline:
        def set(self, key, value, ex=None): return self
        def zadd(self, name, mapping): return self
        def hset(self, name, mapping): return self
        async def execute(self): return [True] * 10
    
    redis = type('redis', (), {'from_url': lambda url: MockRedis()})
    
    class MockLogger:
        def info(self, msg, **kwargs): print(f"ℹ️ {msg} {kwargs}")
        def debug(self, msg, **kwargs): print(f"🐛 {msg} {kwargs}")
        def error(self, msg, **kwargs): print(f"❌ {msg} {kwargs}")
        def warning(self, msg, **kwargs): print(f"⚠️ {msg} {kwargs}")
    
    structlog = type('structlog', (), {'get_logger': lambda: MockLogger()})
    logger = MockLogger()
    REDIS_AVAILABLE = False


class PersistenceStrategy(Enum):
    """Event persistence strategies"""
    NONE = "none"                       # No persistence
    CRITICAL_ONLY = "critical_only"     # Only critical events
    ALL_EVENTS = "all_events"           # All events
    SELECTIVE = "selective"             # Based on event type patterns


class CompressionType(Enum):
    """Compression types for event data"""
    NONE = "none"
    GZIP = "gzip"
    ZLIB = "zlib"


@dataclass
class PersistenceConfig:
    """Configuration for event persistence"""
    strategy: PersistenceStrategy = PersistenceStrategy.CRITICAL_ONLY
    compression: CompressionType = CompressionType.ZLIB
    retention_days: int = 30
    snapshot_interval_hours: int = 6
    max_events_per_stream: int = 10000
    enable_compression: bool = True
    compression_threshold_bytes: int = 1024
    enable_checksums: bool = True
    batch_size: int = 100
    
    # Recovery settings
    enable_auto_recovery: bool = True
    recovery_timeout_seconds: int = 300
    max_recovery_attempts: int = 3
    
    # Performance settings  
    background_cleanup_enabled: bool = True
    cleanup_interval_hours: int = 24
    max_memory_usage_mb: int = 512


@dataclass
class EventSnapshot:
    """Event stream snapshot for faster recovery"""
    stream_name: str
    snapshot_id: str
    timestamp: datetime
    event_count: int
    last_event_id: str
    checksum: str
    compressed_data: bytes
    metadata: Dict[str, Any]


@dataclass
class RecoveryCheckpoint:
    """Recovery progress checkpoint"""
    stream_name: str
    checkpoint_id: str
    last_processed_event_id: str
    processed_count: int
    timestamp: datetime
    status: str  # "active", "completed", "failed"


class RedisEventPersistence:
    """Redis-based event persistence and recovery system"""
    
    def __init__(self, config: PersistenceConfig = None, service_name: str = "persistence"):
        self.config = config or PersistenceConfig()
        self.service_name = service_name
        self.logger = logger.bind(service=service_name)
        
        # Redis connections
        self.redis_client: Optional[redis.Redis] = None
        self.event_bus: Optional[RedisEventBus] = None
        
        # State management
        self.running = False
        self.recovery_in_progress = False
        
        # Metrics
        self.metrics = {
            'events_persisted': 0,
            'events_compressed': 0,
            'snapshots_created': 0,
            'recoveries_performed': 0,
            'cleanup_operations': 0,
            'bytes_saved': 0,
            'last_snapshot': None,
            'last_cleanup': None
        }
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        
        # Stream tracking
        self.active_streams: Set[str] = set()
        self.stream_stats: Dict[str, Dict[str, Any]] = {}
    
    async def initialize(self, redis_url: str = "redis://localhost:6379/0") -> bool:
        """Initialize persistence system"""
        try:
            # Create Redis connection
            self.redis_client = redis.from_url(redis_url)
            await self.redis_client.ping()
            
            # Get event bus reference
            self.event_bus = await get_event_bus(self.service_name)
            
            # Start background tasks
            await self._start_background_tasks()
            
            self.running = True
            self.logger.info("Event persistence system initialized",
                           strategy=self.config.strategy.value,
                           retention_days=self.config.retention_days)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to initialize persistence system", error=str(e))
            return False
    
    async def shutdown(self):
        """Shutdown persistence system"""
        try:
            self.running = False
            
            # Cancel background tasks
            for task in self.background_tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Close Redis connection
            if self.redis_client:
                await self.redis_client.close()
            
            self.logger.info("Event persistence system shut down")
            
        except Exception as e:
            self.logger.error("Error during persistence system shutdown", error=str(e))
    
    async def persist_event(self, event: Event) -> bool:
        """Persist event to Redis based on strategy"""
        try:
            # Check if event should be persisted
            if not await self._should_persist_event(event):
                return True
            
            # Prepare event data
            event_data = await self._prepare_event_data(event)
            if not event_data:
                return False
            
            # Generate storage keys
            stream_key = self._get_stream_key(event.event_type)
            event_key = self._get_event_key(event.metadata.event_id)
            
            # Store event in pipeline for atomicity
            pipeline = self.redis_client.pipeline()
            
            # Store event data
            ttl_seconds = self.config.retention_days * 24 * 3600
            pipeline.set(event_key, event_data['serialized'], ex=ttl_seconds)
            
            # Add to stream index with timestamp score
            timestamp_score = event_data['timestamp_score']
            pipeline.zadd(stream_key, {event.metadata.event_id: timestamp_score})
            
            # Update stream metadata
            stream_meta_key = f"{stream_key}:meta"
            pipeline.hset(stream_meta_key, mapping={
                'last_event_id': event.metadata.event_id,
                'last_timestamp': event.metadata.timestamp,
                'event_count': 1
            })
            
            # Execute pipeline
            await pipeline.execute()
            
            # Update metrics and tracking
            self.metrics['events_persisted'] += 1
            if event_data.get('compressed', False):
                self.metrics['events_compressed'] += 1
                self.metrics['bytes_saved'] += event_data.get('bytes_saved', 0)
            
            # Track stream
            self.active_streams.add(event.event_type)
            await self._update_stream_stats(event.event_type)
            
            self.logger.debug("Event persisted successfully",
                            event_id=event.metadata.event_id,
                            event_type=event.event_type,
                            compressed=event_data.get('compressed', False))
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to persist event",
                            event_id=event.metadata.event_id,
                            error=str(e))
            return False
    
    async def recover_events(self, stream_name: str, 
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           max_events: Optional[int] = None) -> List[Event]:
        """Recover events from persistence storage"""
        try:
            if self.recovery_in_progress:
                self.logger.warning("Recovery already in progress")
                return []
            
            self.recovery_in_progress = True
            self.logger.info("Starting event recovery",
                           stream_name=stream_name,
                           start_time=start_time,
                           end_time=end_time)
            
            # Create recovery checkpoint
            checkpoint = await self._create_recovery_checkpoint(stream_name)
            
            # Get event IDs from stream index
            event_ids = await self._get_event_ids_from_stream(
                stream_name, start_time, end_time, max_events
            )
            
            if not event_ids:
                self.logger.info("No events found for recovery", stream_name=stream_name)
                return []
            
            # Recover events in batches
            recovered_events = []
            batch_size = self.config.batch_size
            
            for i in range(0, len(event_ids), batch_size):
                batch_ids = event_ids[i:i + batch_size]
                batch_events = await self._recover_event_batch(batch_ids)
                recovered_events.extend(batch_events)
                
                # Update checkpoint
                await self._update_recovery_checkpoint(
                    checkpoint, batch_ids[-1], len(recovered_events)
                )
                
                # Yield control to allow other operations
                await asyncio.sleep(0.01)
            
            # Mark recovery complete
            await self._complete_recovery_checkpoint(checkpoint)
            
            self.metrics['recoveries_performed'] += 1
            self.logger.info("Event recovery completed",
                           stream_name=stream_name,
                           events_recovered=len(recovered_events))
            
            return recovered_events
            
        except Exception as e:
            self.logger.error("Event recovery failed",
                            stream_name=stream_name,
                            error=str(e))
            return []
        finally:
            self.recovery_in_progress = False
    
    async def create_snapshot(self, stream_name: str) -> Optional[EventSnapshot]:
        """Create snapshot of event stream"""
        try:
            stream_key = self._get_stream_key(stream_name)
            
            # Get recent events
            recent_events = await self.recover_events(
                stream_name, 
                start_time=datetime.now() - timedelta(hours=self.config.snapshot_interval_hours),
                max_events=self.config.max_events_per_stream
            )
            
            if not recent_events:
                return None
            
            # Create snapshot data
            snapshot_data = {
                'events': [event.to_dict() for event in recent_events],
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'event_count': len(recent_events),
                    'stream_name': stream_name,
                    'service': self.service_name
                }
            }
            
            # Serialize and compress
            serialized_data = json.dumps(snapshot_data, default=str).encode('utf-8')
            compressed_data = await self._compress_data(serialized_data)
            
            # Calculate checksum
            import hashlib
            checksum = hashlib.sha256(compressed_data).hexdigest()
            
            # Create snapshot object
            snapshot = EventSnapshot(
                stream_name=stream_name,
                snapshot_id=f"snap_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                timestamp=datetime.now(),
                event_count=len(recent_events),
                last_event_id=recent_events[-1].metadata.event_id,
                checksum=checksum,
                compressed_data=compressed_data,
                metadata=snapshot_data['metadata']
            )
            
            # Store snapshot
            await self._store_snapshot(snapshot)
            
            self.metrics['snapshots_created'] += 1
            self.metrics['last_snapshot'] = datetime.now()
            
            self.logger.info("Snapshot created",
                           stream_name=stream_name,
                           snapshot_id=snapshot.snapshot_id,
                           events=len(recent_events))
            
            return snapshot
            
        except Exception as e:
            self.logger.error("Failed to create snapshot",
                            stream_name=stream_name,
                            error=str(e))
            return None
    
    async def restore_from_snapshot(self, snapshot_id: str) -> bool:
        """Restore events from snapshot"""
        try:
            # Retrieve snapshot
            snapshot = await self._retrieve_snapshot(snapshot_id)
            if not snapshot:
                return False
            
            # Verify checksum
            import hashlib
            calculated_checksum = hashlib.sha256(snapshot.compressed_data).hexdigest()
            if calculated_checksum != snapshot.checksum:
                self.logger.error("Snapshot checksum verification failed",
                                snapshot_id=snapshot_id)
                return False
            
            # Decompress and deserialize
            decompressed_data = await self._decompress_data(snapshot.compressed_data)
            snapshot_data = json.loads(decompressed_data.decode('utf-8'))
            
            # Restore events
            restored_count = 0
            for event_dict in snapshot_data['events']:
                try:
                    event = Event.from_dict(event_dict)
                    success = await self.persist_event(event)
                    if success:
                        restored_count += 1
                except Exception as e:
                    self.logger.warning("Failed to restore event from snapshot",
                                      error=str(e))
            
            self.logger.info("Snapshot restoration completed",
                           snapshot_id=snapshot_id,
                           events_restored=restored_count)
            
            return restored_count > 0
            
        except Exception as e:
            self.logger.error("Failed to restore from snapshot",
                            snapshot_id=snapshot_id,
                            error=str(e))
            return False
    
    async def cleanup_expired_events(self) -> int:
        """Clean up expired events and snapshots"""
        try:
            cutoff_time = datetime.now() - timedelta(days=self.config.retention_days)
            cutoff_score = cutoff_time.timestamp()
            
            cleanup_count = 0
            
            # Cleanup each active stream
            for stream_name in self.active_streams:
                stream_key = self._get_stream_key(stream_name)
                
                # Get expired event IDs
                expired_event_ids = await self.redis_client.zrangebyscore(
                    stream_key, 0, cutoff_score
                )
                
                if expired_event_ids:
                    # Remove expired events
                    pipeline = self.redis_client.pipeline()
                    
                    # Remove from stream index
                    pipeline.zremrangebyscore(stream_key, 0, cutoff_score)
                    
                    # Remove event data
                    for event_id in expired_event_ids:
                        event_key = self._get_event_key(event_id.decode('utf-8'))
                        pipeline.delete(event_key)
                    
                    await pipeline.execute()
                    cleanup_count += len(expired_event_ids)
            
            # Cleanup expired snapshots
            await self._cleanup_expired_snapshots(cutoff_time)
            
            self.metrics['cleanup_operations'] += 1
            self.metrics['last_cleanup'] = datetime.now()
            
            self.logger.info("Cleanup completed", events_removed=cleanup_count)
            
            return cleanup_count
            
        except Exception as e:
            self.logger.error("Cleanup failed", error=str(e))
            return 0
    
    async def get_stream_info(self, stream_name: str) -> Dict[str, Any]:
        """Get information about an event stream"""
        try:
            stream_key = self._get_stream_key(stream_name)
            stream_meta_key = f"{stream_key}:meta"
            
            # Get stream metadata
            meta_data = await self.redis_client.hgetall(stream_meta_key)
            
            # Get event count
            event_count = await self.redis_client.zcard(stream_key)
            
            # Get oldest and newest timestamps
            oldest = await self.redis_client.zrange(stream_key, 0, 0, withscores=True)
            newest = await self.redis_client.zrange(stream_key, -1, -1, withscores=True)
            
            stream_info = {
                'stream_name': stream_name,
                'event_count': event_count,
                'oldest_event_time': datetime.fromtimestamp(oldest[0][1]).isoformat() if oldest else None,
                'newest_event_time': datetime.fromtimestamp(newest[0][1]).isoformat() if newest else None,
                'last_event_id': meta_data.get(b'last_event_id', b'').decode('utf-8') if meta_data else None,
                'last_timestamp': meta_data.get(b'last_timestamp', b'').decode('utf-8') if meta_data else None
            }
            
            return stream_info
            
        except Exception as e:
            self.logger.error("Failed to get stream info",
                            stream_name=stream_name,
                            error=str(e))
            return {}
    
    # Private helper methods
    
    async def _should_persist_event(self, event: Event) -> bool:
        """Determine if event should be persisted based on strategy"""
        if self.config.strategy == PersistenceStrategy.NONE:
            return False
        elif self.config.strategy == PersistenceStrategy.ALL_EVENTS:
            return True
        elif self.config.strategy == PersistenceStrategy.CRITICAL_ONLY:
            return event.metadata.priority in [EventPriority.HIGH, EventPriority.CRITICAL]
        elif self.config.strategy == PersistenceStrategy.SELECTIVE:
            # Define selective patterns (can be configured)
            selective_patterns = [
                'order.',
                'account.transaction',
                'intelligence.recommendation',
                'system.error'
            ]
            return any(event.event_type.startswith(pattern) for pattern in selective_patterns)
        
        return False
    
    async def _prepare_event_data(self, event: Event) -> Optional[Dict[str, Any]]:
        """Prepare event data for storage"""
        try:
            # Serialize event
            event_dict = event.to_dict()
            serialized = json.dumps(event_dict, default=str).encode('utf-8')
            
            # Compress if beneficial
            compressed = False
            bytes_saved = 0
            
            if (self.config.enable_compression and 
                len(serialized) > self.config.compression_threshold_bytes):
                compressed_data = await self._compress_data(serialized)
                if len(compressed_data) < len(serialized):
                    serialized = compressed_data
                    compressed = True
                    bytes_saved = len(serialized) - len(compressed_data)
            
            # Generate timestamp score for ordering
            try:
                event_timestamp = datetime.fromisoformat(event.metadata.timestamp.replace('Z', '+00:00'))
            except:
                event_timestamp = datetime.now()
            
            timestamp_score = event_timestamp.timestamp()
            
            return {
                'serialized': serialized,
                'compressed': compressed,
                'bytes_saved': bytes_saved,
                'timestamp_score': timestamp_score
            }
            
        except Exception as e:
            self.logger.error("Failed to prepare event data",
                            event_id=event.metadata.event_id,
                            error=str(e))
            return None
    
    async def _compress_data(self, data: bytes) -> bytes:
        """Compress data using configured compression type"""
        if self.config.compression == CompressionType.ZLIB:
            return zlib.compress(data)
        elif self.config.compression == CompressionType.GZIP:
            import gzip
            return gzip.compress(data)
        else:
            return data
    
    async def _decompress_data(self, data: bytes) -> bytes:
        """Decompress data using configured compression type"""
        if self.config.compression == CompressionType.ZLIB:
            return zlib.decompress(data)
        elif self.config.compression == CompressionType.GZIP:
            import gzip
            return gzip.decompress(data)
        else:
            return data
    
    def _get_stream_key(self, stream_name: str) -> str:
        """Get Redis key for event stream"""
        return f"event_stream:{stream_name}"
    
    def _get_event_key(self, event_id: str) -> str:
        """Get Redis key for individual event"""
        return f"event_data:{event_id}"
    
    def _get_snapshot_key(self, snapshot_id: str) -> str:
        """Get Redis key for snapshot"""
        return f"event_snapshot:{snapshot_id}"
    
    async def _get_event_ids_from_stream(self, stream_name: str,
                                       start_time: Optional[datetime] = None,
                                       end_time: Optional[datetime] = None,
                                       max_events: Optional[int] = None) -> List[str]:
        """Get event IDs from stream within time range"""
        try:
            stream_key = self._get_stream_key(stream_name)
            
            # Calculate score range
            min_score = start_time.timestamp() if start_time else 0
            max_score = end_time.timestamp() if end_time else '+inf'
            
            # Get event IDs
            if max_events:
                # Use ZRANGEBYSCORE with LIMIT
                event_ids = await self.redis_client.zrangebyscore(
                    stream_key, min_score, max_score, start=0, num=max_events
                )
            else:
                event_ids = await self.redis_client.zrangebyscore(
                    stream_key, min_score, max_score
                )
            
            return [event_id.decode('utf-8') for event_id in event_ids]
            
        except Exception as e:
            self.logger.error("Failed to get event IDs from stream",
                            stream_name=stream_name,
                            error=str(e))
            return []
    
    async def _recover_event_batch(self, event_ids: List[str]) -> List[Event]:
        """Recover a batch of events"""
        recovered_events = []
        
        try:
            # Get all events in parallel
            pipeline = self.redis_client.pipeline()
            for event_id in event_ids:
                event_key = self._get_event_key(event_id)
                pipeline.get(event_key)
            
            results = await pipeline.execute()
            
            # Process results
            for event_id, event_data in zip(event_ids, results):
                if event_data:
                    try:
                        # Decompress if needed
                        if self.config.enable_compression:
                            try:
                                decompressed_data = await self._decompress_data(event_data)
                                event_data = decompressed_data
                            except:
                                # Data might not be compressed
                                pass
                        
                        # Deserialize event
                        event_dict = json.loads(event_data.decode('utf-8'))
                        event = Event.from_dict(event_dict)
                        recovered_events.append(event)
                        
                    except Exception as e:
                        self.logger.warning("Failed to recover event",
                                          event_id=event_id,
                                          error=str(e))
            
        except Exception as e:
            self.logger.error("Failed to recover event batch", error=str(e))
        
        return recovered_events
    
    async def _create_recovery_checkpoint(self, stream_name: str) -> RecoveryCheckpoint:
        """Create recovery checkpoint"""
        checkpoint = RecoveryCheckpoint(
            stream_name=stream_name,
            checkpoint_id=f"recovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            last_processed_event_id="",
            processed_count=0,
            timestamp=datetime.now(),
            status="active"
        )
        
        # Store checkpoint
        checkpoint_key = f"recovery_checkpoint:{checkpoint.checkpoint_id}"
        await self.redis_client.hset(checkpoint_key, mapping=asdict(checkpoint))
        await self.redis_client.expire(checkpoint_key, 3600)  # Expire in 1 hour
        
        return checkpoint
    
    async def _update_recovery_checkpoint(self, checkpoint: RecoveryCheckpoint,
                                        last_event_id: str, processed_count: int):
        """Update recovery checkpoint"""
        checkpoint.last_processed_event_id = last_event_id
        checkpoint.processed_count = processed_count
        checkpoint.timestamp = datetime.now()
        
        checkpoint_key = f"recovery_checkpoint:{checkpoint.checkpoint_id}"
        await self.redis_client.hset(checkpoint_key, mapping=asdict(checkpoint))
    
    async def _complete_recovery_checkpoint(self, checkpoint: RecoveryCheckpoint):
        """Mark recovery checkpoint as completed"""
        checkpoint.status = "completed"
        checkpoint.timestamp = datetime.now()
        
        checkpoint_key = f"recovery_checkpoint:{checkpoint.checkpoint_id}"
        await self.redis_client.hset(checkpoint_key, mapping=asdict(checkpoint))
    
    async def _store_snapshot(self, snapshot: EventSnapshot):
        """Store snapshot in Redis"""
        snapshot_key = self._get_snapshot_key(snapshot.snapshot_id)
        
        snapshot_data = {
            'stream_name': snapshot.stream_name,
            'snapshot_id': snapshot.snapshot_id,
            'timestamp': snapshot.timestamp.isoformat(),
            'event_count': snapshot.event_count,
            'last_event_id': snapshot.last_event_id,
            'checksum': snapshot.checksum,
            'metadata': json.dumps(snapshot.metadata)
        }
        
        await self.redis_client.hset(snapshot_key, mapping=snapshot_data)
        await self.redis_client.set(f"{snapshot_key}:data", snapshot.compressed_data)
        
        # Set expiration
        ttl_seconds = self.config.retention_days * 24 * 3600
        await self.redis_client.expire(snapshot_key, ttl_seconds)
        await self.redis_client.expire(f"{snapshot_key}:data", ttl_seconds)
    
    async def _retrieve_snapshot(self, snapshot_id: str) -> Optional[EventSnapshot]:
        """Retrieve snapshot from Redis"""
        try:
            snapshot_key = self._get_snapshot_key(snapshot_id)
            
            # Get snapshot metadata
            snapshot_data = await self.redis_client.hgetall(snapshot_key)
            if not snapshot_data:
                return None
            
            # Get compressed data
            compressed_data = await self.redis_client.get(f"{snapshot_key}:data")
            if not compressed_data:
                return None
            
            # Create snapshot object
            snapshot = EventSnapshot(
                stream_name=snapshot_data[b'stream_name'].decode('utf-8'),
                snapshot_id=snapshot_data[b'snapshot_id'].decode('utf-8'),
                timestamp=datetime.fromisoformat(snapshot_data[b'timestamp'].decode('utf-8')),
                event_count=int(snapshot_data[b'event_count']),
                last_event_id=snapshot_data[b'last_event_id'].decode('utf-8'),
                checksum=snapshot_data[b'checksum'].decode('utf-8'),
                compressed_data=compressed_data,
                metadata=json.loads(snapshot_data[b'metadata'].decode('utf-8'))
            )
            
            return snapshot
            
        except Exception as e:
            self.logger.error("Failed to retrieve snapshot",
                            snapshot_id=snapshot_id,
                            error=str(e))
            return None
    
    async def _cleanup_expired_snapshots(self, cutoff_time: datetime):
        """Clean up expired snapshots"""
        try:
            # Scan for snapshot keys
            async for key in self.redis_client.scan_iter(match="event_snapshot:*"):
                if not key.endswith(b':data'):
                    # Get snapshot timestamp
                    snapshot_data = await self.redis_client.hget(key, 'timestamp')
                    if snapshot_data:
                        try:
                            timestamp = datetime.fromisoformat(snapshot_data.decode('utf-8'))
                            if timestamp < cutoff_time:
                                # Delete snapshot and data
                                await self.redis_client.delete(key)
                                await self.redis_client.delete(f"{key.decode('utf-8')}:data")
                        except:
                            continue
                            
        except Exception as e:
            self.logger.error("Failed to cleanup expired snapshots", error=str(e))
    
    async def _update_stream_stats(self, stream_name: str):
        """Update stream statistics"""
        if stream_name not in self.stream_stats:
            self.stream_stats[stream_name] = {
                'events_persisted': 0,
                'last_update': None,
                'first_event': None
            }
        
        stats = self.stream_stats[stream_name]
        stats['events_persisted'] += 1
        stats['last_update'] = datetime.now()
        
        if stats['first_event'] is None:
            stats['first_event'] = datetime.now()
    
    async def _start_background_tasks(self):
        """Start background maintenance tasks"""
        if self.config.background_cleanup_enabled:
            cleanup_task = asyncio.create_task(self._background_cleanup_task())
            self.background_tasks.append(cleanup_task)
        
        snapshot_task = asyncio.create_task(self._background_snapshot_task())
        self.background_tasks.append(snapshot_task)
    
    async def _background_cleanup_task(self):
        """Background task for cleanup operations"""
        while self.running:
            try:
                await asyncio.sleep(self.config.cleanup_interval_hours * 3600)
                if self.running:
                    await self.cleanup_expired_events()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Background cleanup task error", error=str(e))
    
    async def _background_snapshot_task(self):
        """Background task for creating snapshots"""
        while self.running:
            try:
                await asyncio.sleep(self.config.snapshot_interval_hours * 3600)
                if self.running:
                    # Create snapshots for all active streams
                    for stream_name in self.active_streams:
                        await self.create_snapshot(stream_name)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Background snapshot task error", error=str(e))
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get persistence metrics"""
        return {
            **self.metrics.copy(),
            'active_streams': len(self.active_streams),
            'stream_stats': self.stream_stats.copy(),
            'config': {
                'strategy': self.config.strategy.value,
                'compression': self.config.compression.value,
                'retention_days': self.config.retention_days
            }
        }