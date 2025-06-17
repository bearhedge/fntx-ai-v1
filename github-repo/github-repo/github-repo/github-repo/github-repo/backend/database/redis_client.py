"""
Redis client for hot memory storage in MCP system.
Provides fast access to active sessions and real-time data.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Set
from datetime import timedelta

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Async Redis client wrapper for MCP hot memory storage.
    """
    
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, 
                 password: Optional[str] = None, decode_responses: bool = True):
        """
        Initialize Redis client.
        
        Args:
            host: Redis server host
            port: Redis server port
            db: Database number
            password: Optional password for authentication
            decode_responses: Whether to decode responses to strings
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.decode_responses = decode_responses
        self._client: Optional[redis.Redis] = None
        self._pool: Optional[ConnectionPool] = None
        
    async def connect(self) -> None:
        """Establish connection to Redis."""
        try:
            self._pool = ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=self.decode_responses,
                max_connections=50
            )
            
            self._client = redis.Redis(connection_pool=self._pool)
            
            # Test connection
            await self._client.ping()
            logger.info(f"Connected to Redis at {self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
            
    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            await self._pool.disconnect()
            logger.info("Redis connection closed")
            
    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.get(key)
        
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """
        Set key-value pair with optional TTL.
        
        Args:
            key: Redis key
            value: String value
            ttl: Time to live in seconds
            
        Returns:
            True if successful
        """
        if not self._client:
            raise RuntimeError("Redis client not connected")
            
        if ttl:
            return await self._client.setex(key, ttl, value)
        else:
            return await self._client.set(key, value)
            
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Get JSON value by key."""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON for key {key}")
                return None
        return None
        
    async def set_json(self, key: str, value: Dict[str, Any], 
                       ttl: Optional[int] = None) -> bool:
        """Set JSON value with optional TTL."""
        try:
            json_str = json.dumps(value)
            return await self.set(key, json_str, ttl)
        except Exception as e:
            logger.error(f"Failed to encode JSON for key {key}: {e}")
            return False
            
    async def delete(self, key: str) -> int:
        """Delete key."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.delete(key)
        
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return bool(await self._client.exists(key))
        
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.expire(key, seconds)
        
    async def ttl(self, key: str) -> int:
        """Get TTL of key in seconds."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.ttl(key)
        
    async def scan_match(self, pattern: str, count: int = 100) -> List[str]:
        """Scan for keys matching pattern."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
            
        keys = []
        cursor = 0
        
        while True:
            cursor, batch = await self._client.scan(
                cursor=cursor,
                match=pattern,
                count=count
            )
            keys.extend(batch)
            
            if cursor == 0:
                break
                
        return keys
        
    async def hget(self, key: str, field: str) -> Optional[str]:
        """Get hash field value."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.hget(key, field)
        
    async def hset(self, key: str, field: str, value: str) -> int:
        """Set hash field value."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.hset(key, field, value)
        
    async def hgetall(self, key: str) -> Dict[str, str]:
        """Get all hash fields and values."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.hgetall(key)
        
    async def sadd(self, key: str, *values: str) -> int:
        """Add values to set."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.sadd(key, *values)
        
    async def smembers(self, key: str) -> Set[str]:
        """Get all members of set."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.smembers(key)
        
    async def srem(self, key: str, *values: str) -> int:
        """Remove values from set."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.srem(key, *values)
        
    async def rpush(self, key: str, *values: str) -> int:
        """Push values to list."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.rpush(key, *values)
        
    async def lpop(self, key: str) -> Optional[str]:
        """Pop from left of list."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.lpop(key)
        
    async def lrange(self, key: str, start: int, stop: int) -> List[str]:
        """Get range of list values."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.lrange(key, start, stop)
        
    async def publish(self, channel: str, message: str) -> int:
        """Publish message to channel."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.publish(channel, message)
        
    async def subscribe(self, *channels: str):
        """Subscribe to channels (returns PubSub object)."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        pubsub = self._client.pubsub()
        await pubsub.subscribe(*channels)
        return pubsub