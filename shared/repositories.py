#!/usr/bin/env python3
"""
Repository Pattern Implementation für DIP-Compliance
Issue #62 - SOLID-Prinzipien durchsetzen - Phase 2: DIP-Implementation

Implementiert das Repository Pattern zur Entkopplung von Datenzugriff und Business-Logik:
- Abstrakte Repository-Interfaces (DIP)
- Konkrete Implementierungen für verschiedene Datenspeicher
- Event-Store, Config-Store, Message-Queue Abstractions

Author: System Modernization Team
Version: 1.0.0
Date: 2025-08-29
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, TypeVar, Generic
from datetime import datetime
from enum import Enum
import json
import logging

# Exception Framework Integration
from .exceptions import DatabaseException, EventBusException, ConfigurationException
from .exception_handler import handle_exceptions

# Generic Types
T = TypeVar('T')
K = TypeVar('K')  # Key Type
V = TypeVar('V')  # Value Type

# Logger
logger = logging.getLogger(__name__)


# =============================================================================
# REPOSITORY INTERFACES (DIP - Abstractions)
# =============================================================================

class Repository(ABC, Generic[K, V]):
    """Base Repository Interface"""
    
    @abstractmethod
    async def get(self, key: K) -> Optional[V]:
        """Entity by Key abrufen"""
        pass
    
    @abstractmethod
    async def save(self, key: K, entity: V) -> bool:
        """Entity speichern"""
        pass
    
    @abstractmethod
    async def delete(self, key: K) -> bool:
        """Entity löschen"""
        pass
    
    @abstractmethod
    async def exists(self, key: K) -> bool:
        """Prüfen ob Entity existiert"""
        pass
    
    @abstractmethod
    async def list_keys(self) -> List[K]:
        """Alle Keys auflisten"""
        pass


class EventRepository(ABC):
    """Event Repository Interface für Event Sourcing"""
    
    @abstractmethod
    async def store_event(self, stream_id: str, event: Dict[str, Any]) -> str:
        """Event in Stream speichern"""
        pass
    
    @abstractmethod
    async def get_events(self, stream_id: str, from_version: int = 0) -> List[Dict[str, Any]]:
        """Events aus Stream abrufen"""
        pass
    
    @abstractmethod
    async def get_events_by_type(self, event_type: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Events nach Typ abrufen"""
        pass
    
    @abstractmethod
    async def get_latest_version(self, stream_id: str) -> int:
        """Neueste Version eines Streams"""
        pass


class ConfigRepository(ABC):
    """Configuration Repository Interface"""
    
    @abstractmethod
    async def get_config(self, key: str) -> Optional[Any]:
        """Konfigurationswert abrufen"""
        pass
    
    @abstractmethod
    async def set_config(self, key: str, value: Any) -> bool:
        """Konfigurationswert setzen"""
        pass
    
    @abstractmethod
    async def get_all_configs(self) -> Dict[str, Any]:
        """Alle Konfigurationen abrufen"""
        pass
    
    @abstractmethod
    async def delete_config(self, key: str) -> bool:
        """Konfiguration löschen"""
        pass


class MessageQueueRepository(ABC):
    """Message Queue Repository Interface"""
    
    @abstractmethod
    async def publish(self, topic: str, message: Dict[str, Any]) -> bool:
        """Nachricht publizieren"""
        pass
    
    @abstractmethod
    async def subscribe(self, topic: str, callback: callable) -> bool:
        """Topic abonnieren"""
        pass
    
    @abstractmethod
    async def unsubscribe(self, topic: str) -> bool:
        """Topic-Abonnement aufheben"""
        pass
    
    @abstractmethod
    async def get_topic_stats(self, topic: str) -> Dict[str, Any]:
        """Topic-Statistiken abrufen"""
        pass


class CacheRepository(ABC):
    """Cache Repository Interface"""
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Wert im Cache speichern"""
        pass
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Wert aus Cache abrufen"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Wert aus Cache löschen"""
        pass
    
    @abstractmethod
    async def flush_all(self) -> bool:
        """Cache komplett leeren"""
        pass
    
    @abstractmethod
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Cache-Statistiken"""
        pass


# =============================================================================
# REDIS IMPLEMENTATIONS (DIP - Concrete Implementations)
# =============================================================================

class RedisEventRepository(EventRepository):
    """Redis-basierte Event Repository Implementation"""
    
    def __init__(self, redis_connection=None, key_prefix: str = "events"):
        self.redis = redis_connection
        self.key_prefix = key_prefix
        self.logger = logging.getLogger(f"repository.redis-events.{key_prefix}")
    
    @handle_exceptions
    async def store_event(self, stream_id: str, event: Dict[str, Any]) -> str:
        """Event in Redis Stream speichern"""
        try:
            if not self.redis:
                raise DatabaseException("Redis connection not available")
            
            # Stream Key
            stream_key = f"{self.key_prefix}:{stream_id}"
            
            # Event mit Timestamp
            event_data = {
                **event,
                'timestamp': datetime.utcnow().isoformat(),
                'stream_id': stream_id
            }
            
            # Redis XADD für Stream
            event_id = await self.redis.xadd(stream_key, event_data)
            
            # Zusätzlich nach Event-Typ indexieren
            if 'event_type' in event:
                type_key = f"{self.key_prefix}:by_type:{event['event_type']}"
                await self.redis.zadd(type_key, {event_id: datetime.utcnow().timestamp()})
            
            self.logger.debug(f"Event stored: {event_id} in stream {stream_id}")
            return event_id
            
        except Exception as e:
            raise DatabaseException(
                f"Failed to store event in stream {stream_id}",
                original_exception=e,
                context={'stream_id': stream_id, 'event_type': event.get('event_type')}
            )
    
    @handle_exceptions
    async def get_events(self, stream_id: str, from_version: int = 0) -> List[Dict[str, Any]]:
        """Events aus Redis Stream abrufen"""
        try:
            if not self.redis:
                raise DatabaseException("Redis connection not available")
            
            stream_key = f"{self.key_prefix}:{stream_id}"
            
            # Start-ID bestimmen
            start_id = "0" if from_version == 0 else str(from_version)
            
            # XRANGE für Stream-Bereich
            events = await self.redis.xrange(stream_key, start_id, "+")
            
            result = []
            for event_id, fields in events:
                event_data = {
                    'event_id': event_id,
                    **fields
                }
                result.append(event_data)
            
            self.logger.debug(f"Retrieved {len(result)} events from stream {stream_id}")
            return result
            
        except Exception as e:
            raise DatabaseException(
                f"Failed to get events from stream {stream_id}",
                original_exception=e,
                context={'stream_id': stream_id, 'from_version': from_version}
            )
    
    @handle_exceptions
    async def get_events_by_type(self, event_type: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Events nach Typ aus Redis abrufen"""
        try:
            if not self.redis:
                raise DatabaseException("Redis connection not available")
            
            type_key = f"{self.key_prefix}:by_type:{event_type}"
            
            # Neueste Events nach Timestamp (ZREVRANGE)
            event_ids = await self.redis.zrevrange(type_key, 0, limit - 1)
            
            result = []
            for event_id in event_ids:
                # Event-Details aus entsprechendem Stream abrufen
                # Format: stream_id ist im event_id kodiert oder separat gespeichert
                event_details = await self._get_event_details(event_id)
                if event_details:
                    result.append(event_details)
            
            self.logger.debug(f"Retrieved {len(result)} events of type {event_type}")
            return result
            
        except Exception as e:
            raise DatabaseException(
                f"Failed to get events by type {event_type}",
                original_exception=e,
                context={'event_type': event_type, 'limit': limit}
            )
    
    async def _get_event_details(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Event-Details abrufen (Helper-Methode)"""
        # Implementierung abhängig von Event-ID-Format
        # Vereinfachte Version - würde in Praxis erweitert
        return {'event_id': event_id, 'details': 'mock'}
    
    @handle_exceptions
    async def get_latest_version(self, stream_id: str) -> int:
        """Neueste Version eines Streams"""
        try:
            if not self.redis:
                raise DatabaseException("Redis connection not available")
            
            stream_key = f"{self.key_prefix}:{stream_id}"
            
            # XLEN für Stream-Länge
            length = await self.redis.xlen(stream_key)
            return length
            
        except Exception as e:
            raise DatabaseException(
                f"Failed to get latest version for stream {stream_id}",
                original_exception=e,
                context={'stream_id': stream_id}
            )


class RedisConfigRepository(ConfigRepository):
    """Redis-basierte Config Repository Implementation"""
    
    def __init__(self, redis_connection=None, key_prefix: str = "config"):
        self.redis = redis_connection
        self.key_prefix = key_prefix
        self.logger = logging.getLogger(f"repository.redis-config.{key_prefix}")
    
    @handle_exceptions
    async def get_config(self, key: str) -> Optional[Any]:
        """Konfigurationswert aus Redis abrufen"""
        try:
            if not self.redis:
                raise DatabaseException("Redis connection not available")
            
            full_key = f"{self.key_prefix}:{key}"
            value = await self.redis.get(full_key)
            
            if value is None:
                return None
            
            # JSON deserialisieren falls möglich
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            raise ConfigurationException(
                f"Failed to get config {key}",
                original_exception=e,
                context={'config_key': key}
            )
    
    @handle_exceptions
    async def set_config(self, key: str, value: Any) -> bool:
        """Konfigurationswert in Redis setzen"""
        try:
            if not self.redis:
                raise DatabaseException("Redis connection not available")
            
            full_key = f"{self.key_prefix}:{key}"
            
            # JSON serialisieren für komplexe Werte
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value)
            else:
                serialized_value = str(value)
            
            success = await self.redis.set(full_key, serialized_value)
            
            self.logger.debug(f"Config set: {key} = {type(value).__name__}")
            return bool(success)
            
        except Exception as e:
            raise ConfigurationException(
                f"Failed to set config {key}",
                original_exception=e,
                context={'config_key': key, 'value_type': type(value).__name__}
            )
    
    @handle_exceptions
    async def get_all_configs(self) -> Dict[str, Any]:
        """Alle Konfigurationen aus Redis abrufen"""
        try:
            if not self.redis:
                raise DatabaseException("Redis connection not available")
            
            pattern = f"{self.key_prefix}:*"
            keys = await self.redis.keys(pattern)
            
            configs = {}
            for full_key in keys:
                # Prefix entfernen um clean key zu bekommen
                clean_key = full_key.replace(f"{self.key_prefix}:", "", 1)
                configs[clean_key] = await self.get_config(clean_key)
            
            self.logger.debug(f"Retrieved {len(configs)} configurations")
            return configs
            
        except Exception as e:
            raise ConfigurationException(
                "Failed to get all configurations",
                original_exception=e
            )
    
    @handle_exceptions
    async def delete_config(self, key: str) -> bool:
        """Konfiguration aus Redis löschen"""
        try:
            if not self.redis:
                raise DatabaseException("Redis connection not available")
            
            full_key = f"{self.key_prefix}:{key}"
            deleted = await self.redis.delete(full_key)
            
            self.logger.debug(f"Config deleted: {key}")
            return deleted > 0
            
        except Exception as e:
            raise ConfigurationException(
                f"Failed to delete config {key}",
                original_exception=e,
                context={'config_key': key}
            )


class RedisCacheRepository(CacheRepository):
    """Redis-basierte Cache Repository Implementation"""
    
    def __init__(self, redis_connection=None, key_prefix: str = "cache"):
        self.redis = redis_connection
        self.key_prefix = key_prefix
        self.logger = logging.getLogger(f"repository.redis-cache.{key_prefix}")
    
    @handle_exceptions
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Wert in Redis Cache setzen"""
        try:
            if not self.redis:
                raise DatabaseException("Redis connection not available")
            
            full_key = f"{self.key_prefix}:{key}"
            
            # Serialisierung
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value)
            else:
                serialized_value = str(value)
            
            # Mit oder ohne TTL setzen
            if ttl_seconds:
                success = await self.redis.setex(full_key, ttl_seconds, serialized_value)
            else:
                success = await self.redis.set(full_key, serialized_value)
            
            self.logger.debug(f"Cache set: {key} (TTL: {ttl_seconds}s)")
            return bool(success)
            
        except Exception as e:
            raise DatabaseException(
                f"Failed to set cache {key}",
                original_exception=e,
                context={'cache_key': key, 'ttl': ttl_seconds}
            )
    
    @handle_exceptions
    async def get(self, key: str) -> Optional[Any]:
        """Wert aus Redis Cache abrufen"""
        try:
            if not self.redis:
                raise DatabaseException("Redis connection not available")
            
            full_key = f"{self.key_prefix}:{key}"
            value = await self.redis.get(full_key)
            
            if value is None:
                return None
            
            # Deserialisierung versuchen
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            raise DatabaseException(
                f"Failed to get cache {key}",
                original_exception=e,
                context={'cache_key': key}
            )
    
    @handle_exceptions
    async def delete(self, key: str) -> bool:
        """Wert aus Redis Cache löschen"""
        try:
            if not self.redis:
                raise DatabaseException("Redis connection not available")
            
            full_key = f"{self.key_prefix}:{key}"
            deleted = await self.redis.delete(full_key)
            
            self.logger.debug(f"Cache deleted: {key}")
            return deleted > 0
            
        except Exception as e:
            raise DatabaseException(
                f"Failed to delete cache {key}",
                original_exception=e,
                context={'cache_key': key}
            )
    
    @handle_exceptions
    async def flush_all(self) -> bool:
        """Redis Cache komplett leeren"""
        try:
            if not self.redis:
                raise DatabaseException("Redis connection not available")
            
            pattern = f"{self.key_prefix}:*"
            keys = await self.redis.keys(pattern)
            
            if keys:
                deleted = await self.redis.delete(*keys)
                self.logger.info(f"Cache flushed: {deleted} keys deleted")
                return True
            
            return True
            
        except Exception as e:
            raise DatabaseException(
                "Failed to flush cache",
                original_exception=e
            )
    
    @handle_exceptions
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Cache-Statistiken abrufen"""
        try:
            if not self.redis:
                raise DatabaseException("Redis connection not available")
            
            pattern = f"{self.key_prefix}:*"
            keys = await self.redis.keys(pattern)
            
            stats = {
                'total_keys': len(keys),
                'prefix': self.key_prefix,
                'memory_usage': 'unknown',  # Würde Redis INFO verwenden
                'hit_rate': 'unknown'       # Würde Monitoring-Integration benötigen
            }
            
            return stats
            
        except Exception as e:
            raise DatabaseException(
                "Failed to get cache stats",
                original_exception=e
            )


# =============================================================================
# IN-MEMORY IMPLEMENTATIONS (für Testing/Development)
# =============================================================================

class InMemoryRepository(Repository[K, V]):
    """In-Memory Repository Implementation für Testing"""
    
    def __init__(self):
        self._data: Dict[K, V] = {}
        self.logger = logging.getLogger("repository.in-memory")
    
    async def get(self, key: K) -> Optional[V]:
        """Entity by Key abrufen"""
        return self._data.get(key)
    
    async def save(self, key: K, entity: V) -> bool:
        """Entity speichern"""
        self._data[key] = entity
        self.logger.debug(f"Entity saved: {key}")
        return True
    
    async def delete(self, key: K) -> bool:
        """Entity löschen"""
        if key in self._data:
            del self._data[key]
            self.logger.debug(f"Entity deleted: {key}")
            return True
        return False
    
    async def exists(self, key: K) -> bool:
        """Prüfen ob Entity existiert"""
        return key in self._data
    
    async def list_keys(self) -> List[K]:
        """Alle Keys auflisten"""
        return list(self._data.keys())


# =============================================================================
# REPOSITORY FACTORY (für Container-Registration)
# =============================================================================

class RepositoryFactory:
    """Factory für Repository-Instanzen"""
    
    @staticmethod
    def create_event_repository(connection_type: str = "redis", **kwargs) -> EventRepository:
        """Event Repository erstellen"""
        if connection_type == "redis":
            return RedisEventRepository(**kwargs)
        else:
            raise ConfigurationException(f"Unsupported event repository type: {connection_type}")
    
    @staticmethod
    def create_config_repository(connection_type: str = "redis", **kwargs) -> ConfigRepository:
        """Config Repository erstellen"""
        if connection_type == "redis":
            return RedisConfigRepository(**kwargs)
        else:
            raise ConfigurationException(f"Unsupported config repository type: {connection_type}")
    
    @staticmethod
    def create_cache_repository(connection_type: str = "redis", **kwargs) -> CacheRepository:
        """Cache Repository erstellen"""
        if connection_type == "redis":
            return RedisCacheRepository(**kwargs)
        else:
            raise ConfigurationException(f"Unsupported cache repository type: {connection_type}")
    
    @staticmethod
    def create_generic_repository(repository_type: type = InMemoryRepository, **kwargs) -> Repository:
        """Generic Repository erstellen"""
        return repository_type(**kwargs)


# =============================================================================
# REPOSITORY REGISTRY (für Service Registration)
# =============================================================================

class RepositoryRegistry:
    """Registry für Repository-Konfiguration und -Erstellung"""
    
    def __init__(self):
        self._config: Dict[str, Dict[str, Any]] = {}
        self._instances: Dict[str, Any] = {}
        self.logger = logging.getLogger("repository.registry")
    
    def register_repository_config(self, name: str, repository_type: str, **config):
        """Repository-Konfiguration registrieren"""
        self._config[name] = {
            'type': repository_type,
            'config': config
        }
        self.logger.debug(f"Repository config registered: {name} ({repository_type})")
    
    def get_repository(self, name: str) -> Optional[Any]:
        """Repository-Instanz abrufen (mit Lazy-Loading)"""
        if name in self._instances:
            return self._instances[name]
        
        if name not in self._config:
            self.logger.warning(f"Repository config not found: {name}")
            return None
        
        # Repository erstellen
        config = self._config[name]
        repository_type = config['type']
        repository_config = config['config']
        
        try:
            if repository_type == 'event':
                repository = RepositoryFactory.create_event_repository(**repository_config)
            elif repository_type == 'config':
                repository = RepositoryFactory.create_config_repository(**repository_config)
            elif repository_type == 'cache':
                repository = RepositoryFactory.create_cache_repository(**repository_config)
            else:
                repository = RepositoryFactory.create_generic_repository(**repository_config)
            
            self._instances[name] = repository
            self.logger.info(f"Repository created: {name} ({repository_type})")
            return repository
            
        except Exception as e:
            self.logger.error(f"Failed to create repository {name}: {e}")
            return None
    
    def list_repositories(self) -> List[str]:
        """Alle registrierten Repository-Namen auflisten"""
        return list(self._config.keys())
    
    def get_repository_stats(self) -> Dict[str, Any]:
        """Registry-Statistiken"""
        return {
            'total_configs': len(self._config),
            'total_instances': len(self._instances),
            'repositories': list(self._config.keys())
        }