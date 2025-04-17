import redis.asyncio as redis
import json
from typing import Any, Dict, Optional, Union
from ..config import settings
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.pool = redis.ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        self.redis = redis.Redis.from_pool(self.pool)
    
    async def connect(self):
        """Initialize connection and ping Redis to ensure it's available"""
        try:
            await self.redis.ping()
            logger.info("Successfully connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise
    
    async def close(self):
        """Close Redis connections"""
        await self.redis.close()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from Redis, deserializing JSON if needed"""
        try:
            value = await self.redis.get(key)
            if value is None:
                return None
            
            try:
                # Try to parse as JSON
                return json.loads(value)
            except json.JSONDecodeError:
                # Return as is if not JSON
                return value
        except Exception as e:
            logger.error(f"Error getting key {key} from Redis: {str(e)}")
            # Return None on error to avoid cache availability issues affecting the application
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a key in Redis with optional TTL, serializing to JSON if needed"""
        try:
            # Serialize complex objects to JSON
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
                
            if ttl:
                return await self.redis.set(key, value, ex=ttl)
            else:
                return await self.redis.set(key, value)
        except Exception as e:
            logger.error(f"Error setting key {key} in Redis: {str(e)}")
            return False
    
    async def delete(self, key: str) -> int:
        """Delete a key from Redis"""
        try:
            return await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Error deleting key {key} from Redis: {str(e)}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis"""
        try:
            return await self.redis.exists(key)
        except Exception as e:
            logger.error(f"Error checking existence of key {key} in Redis: {str(e)}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set an expiration time on a key"""
        try:
            return await self.redis.expire(key, ttl)
        except Exception as e:
            logger.error(f"Error setting expiration for key {key} in Redis: {str(e)}")
            return False
    
    async def clear_cache_by_prefix(self, prefix: str) -> int:
        """Clear all cache keys with a given prefix"""
        try:
            keys = []
            # Use scan for better performance with large number of keys
            async for key in self.redis.scan_iter(match=f"{prefix}*"):
                keys.append(key)
            
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Error clearing cache with prefix {prefix}: {str(e)}")
            return 0
            
    # Specific cache methods for our AB testing service
    
    async def get_experiment(self, experiment_id: str) -> Optional[Dict]:
        """Get cached experiment data"""
        return await self.get(f"experiment:{experiment_id}")
    
    async def set_experiment(self, experiment_id: str, experiment_data: Dict) -> bool:
        """Cache experiment data"""
        return await self.set(
            f"experiment:{experiment_id}", 
            experiment_data, 
            ttl=settings.EXPERIMENT_CACHE_TTL
        )
    
    async def delete_experiment_cache(self, experiment_id: str) -> int:
        """Delete experiment cache"""
        return await self.delete(f"experiment:{experiment_id}")
    
    async def get_assignment(self, subid: str, experiment_id: str) -> Optional[Dict]:
        """Get cached assignment"""
        return await self.get(f"assignment:{subid}:{experiment_id}")
    
    async def set_assignment(self, subid: str, experiment_id: str, assignment_data: Dict) -> bool:
        """Cache assignment"""
        return await self.set(
            f"assignment:{subid}:{experiment_id}", 
            assignment_data, 
            ttl=settings.ASSIGNMENT_CACHE_TTL
        )
        
    async def delete_assignment_cache(self, subid: str, experiment_id: str) -> int:
        """Delete assignment cache"""
        return await self.delete(f"assignment:{subid}:{experiment_id}")
    
    async def clear_experiment_caches(self, experiment_id: str) -> int:
        """Clear all caches related to an experiment (useful when updating experiment)"""
        # This only clears the experiment config cache
        # Assignment caches will persist until they expire to maintain user experience
        return await self.delete_experiment_cache(experiment_id)
    
    async def clear_all_experiment_caches(self) -> int:
        """Clear all experiment caches"""
        return await self.clear_cache_by_prefix("experiment:")
        
    async def clear_all_assignment_caches(self) -> int:
        """Clear all assignment caches"""
        return await self.clear_cache_by_prefix("assignment:")

# Initialize a global Redis client
redis_client = RedisClient()