"""
PhotonPath Rate Limiting Module
================================

Redis-based rate limiting for API requests.
Supports multiple plans with different limits.

Usage:
    from rate_limiter import RateLimiter, check_rate_limit
    
    limiter = RateLimiter(redis_url="redis://localhost:6379")
    
    # In FastAPI endpoint
    @app.get("/endpoint")
    async def endpoint(user = Depends(check_rate_limit)):
        ...

Author: PhotonPath
Version: 1.0.0
"""

import time
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

# Try to import redis, fallback to in-memory if not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️ Redis not installed. Using in-memory rate limiting (not for production)")


class Plan(str, Enum):
    SPARK = "spark"        # Free
    PHOTON = "photon"      # 29€/mois
    BEAM = "beam"          # 99€/mois
    LASER = "laser"        # 299€/mois
    FUSION = "fusion"      # Sur devis


# Rate limits per plan (requests per day)
PLAN_LIMITS = {
    Plan.SPARK: {
        "requests_per_day": 100,
        "requests_per_minute": 10,
        "monte_carlo_per_day": 10,
        "batch_size": 5,
        "tissues_access": "basic"  # 10 tissus de base
    },
    Plan.PHOTON: {
        "requests_per_day": 2000,
        "requests_per_minute": 30,
        "monte_carlo_per_day": 100,
        "batch_size": 20,
        "tissues_access": "full"
    },
    Plan.BEAM: {
        "requests_per_day": 15000,
        "requests_per_minute": 100,
        "monte_carlo_per_day": 1000,
        "batch_size": 100,
        "tissues_access": "full"
    },
    Plan.LASER: {
        "requests_per_day": 100000,
        "requests_per_minute": 500,
        "monte_carlo_per_day": 10000,
        "batch_size": 500,
        "tissues_access": "full_custom"
    },
    Plan.FUSION: {
        "requests_per_day": 1000000,
        "requests_per_minute": 2000,
        "monte_carlo_per_day": 100000,
        "batch_size": 1000,
        "tissues_access": "unlimited"
    }
}


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    limit: int
    reset_at: datetime
    retry_after: Optional[int] = None


class InMemoryStore:
    """Fallback in-memory rate limiter (for development only)."""
    
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
    
    def get(self, key: str) -> Optional[str]:
        if key in self._store:
            data = self._store[key]
            if data.get('expires_at', 0) > time.time():
                return str(data.get('value', 0))
            else:
                del self._store[key]
        return None
    
    def set(self, key: str, value: Any, ex: int = None):
        self._store[key] = {
            'value': value,
            'expires_at': time.time() + (ex or 86400)
        }
    
    def incr(self, key: str) -> int:
        current = int(self.get(key) or 0)
        new_value = current + 1
        # Preserve existing TTL
        if key in self._store:
            expires_at = self._store[key].get('expires_at', time.time() + 86400)
            self._store[key] = {'value': new_value, 'expires_at': expires_at}
        else:
            self._store[key] = {'value': new_value, 'expires_at': time.time() + 86400}
        return new_value
    
    def ttl(self, key: str) -> int:
        if key in self._store:
            return max(0, int(self._store[key].get('expires_at', 0) - time.time()))
        return 0
    
    def expire(self, key: str, seconds: int):
        if key in self._store:
            self._store[key]['expires_at'] = time.time() + seconds


class RateLimiter:
    """
    Redis-based rate limiter with sliding window.
    
    Parameters:
    -----------
    redis_url : str
        Redis connection URL (e.g., "redis://localhost:6379")
    prefix : str
        Key prefix for Redis keys
    """
    
    def __init__(self, redis_url: str = None, prefix: str = "photonpath"):
        self.prefix = prefix
        
        if redis_url and REDIS_AVAILABLE:
            try:
                self.redis = redis.from_url(redis_url, decode_responses=True)
                self.redis.ping()
                self._using_redis = True
                print(f"✅ Redis connected: {redis_url}")
            except Exception as e:
                print(f"⚠️ Redis connection failed: {e}. Using in-memory fallback.")
                self.redis = InMemoryStore()
                self._using_redis = False
        else:
            self.redis = InMemoryStore()
            self._using_redis = False
            if not REDIS_AVAILABLE:
                print("⚠️ Redis package not installed. Using in-memory rate limiting.")
    
    @property
    def is_redis(self) -> bool:
        return self._using_redis
    
    def _get_key(self, api_key: str, window: str) -> str:
        """Generate Redis key for rate limiting."""
        key_hash = hashlib.md5(api_key.encode()).hexdigest()[:12]
        return f"{self.prefix}:ratelimit:{key_hash}:{window}"
    
    def check_rate_limit(
        self,
        api_key: str,
        plan: Plan = Plan.SPARK,
        endpoint_type: str = "general"
    ) -> RateLimitResult:
        """
        Check if request is within rate limits.
        
        Parameters:
        -----------
        api_key : str
            User's API key
        plan : Plan
            User's subscription plan
        endpoint_type : str
            Type of endpoint ("general", "monte_carlo", "batch")
            
        Returns:
        --------
        RateLimitResult
        """
        limits = PLAN_LIMITS[plan]
        now = datetime.utcnow()
        
        # Check per-minute limit
        minute_key = self._get_key(api_key, now.strftime("%Y%m%d%H%M"))
        minute_count = int(self.redis.get(minute_key) or 0)
        minute_limit = limits["requests_per_minute"]
        
        if minute_count >= minute_limit:
            return RateLimitResult(
                allowed=False,
                remaining=0,
                limit=minute_limit,
                reset_at=now.replace(second=0, microsecond=0) + timedelta(minutes=1),
                retry_after=60 - now.second
            )
        
        # Check per-day limit
        day_key = self._get_key(api_key, now.strftime("%Y%m%d"))
        day_count = int(self.redis.get(day_key) or 0)
        day_limit = limits["requests_per_day"]
        
        # Special limits for Monte Carlo
        if endpoint_type == "monte_carlo":
            mc_key = self._get_key(api_key, f"mc_{now.strftime('%Y%m%d')}")
            mc_count = int(self.redis.get(mc_key) or 0)
            mc_limit = limits["monte_carlo_per_day"]
            
            if mc_count >= mc_limit:
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    limit=mc_limit,
                    reset_at=now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1),
                    retry_after=self.redis.ttl(mc_key)
                )
        
        if day_count >= day_limit:
            return RateLimitResult(
                allowed=False,
                remaining=0,
                limit=day_limit,
                reset_at=now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1),
                retry_after=self.redis.ttl(day_key)
            )
        
        # Increment counters
        new_minute = self.redis.incr(minute_key)
        if new_minute == 1:
            self.redis.expire(minute_key, 60)
        
        new_day = self.redis.incr(day_key)
        if new_day == 1:
            self.redis.expire(day_key, 86400)
        
        if endpoint_type == "monte_carlo":
            mc_key = self._get_key(api_key, f"mc_{now.strftime('%Y%m%d')}")
            new_mc = self.redis.incr(mc_key)
            if new_mc == 1:
                self.redis.expire(mc_key, 86400)
        
        return RateLimitResult(
            allowed=True,
            remaining=day_limit - new_day,
            limit=day_limit,
            reset_at=now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        )
    
    def get_usage(self, api_key: str, plan: Plan = Plan.SPARK) -> Dict[str, Any]:
        """Get current usage statistics for an API key."""
        now = datetime.utcnow()
        limits = PLAN_LIMITS[plan]
        
        day_key = self._get_key(api_key, now.strftime("%Y%m%d"))
        minute_key = self._get_key(api_key, now.strftime("%Y%m%d%H%M"))
        mc_key = self._get_key(api_key, f"mc_{now.strftime('%Y%m%d')}")
        
        day_count = int(self.redis.get(day_key) or 0)
        minute_count = int(self.redis.get(minute_key) or 0)
        mc_count = int(self.redis.get(mc_key) or 0)
        
        return {
            "daily": {
                "used": day_count,
                "limit": limits["requests_per_day"],
                "remaining": max(0, limits["requests_per_day"] - day_count),
                "reset_in_seconds": self.redis.ttl(day_key)
            },
            "per_minute": {
                "used": minute_count,
                "limit": limits["requests_per_minute"],
                "remaining": max(0, limits["requests_per_minute"] - minute_count)
            },
            "monte_carlo": {
                "used": mc_count,
                "limit": limits["monte_carlo_per_day"],
                "remaining": max(0, limits["monte_carlo_per_day"] - mc_count)
            },
            "plan": plan.value
        }


# Global instance (initialized in API)
_limiter: Optional[RateLimiter] = None


def init_rate_limiter(redis_url: str = None) -> RateLimiter:
    """Initialize global rate limiter."""
    global _limiter
    _limiter = RateLimiter(redis_url)
    return _limiter


def get_rate_limiter() -> Optional[RateLimiter]:
    """Get global rate limiter instance."""
    return _limiter


# FastAPI dependency
async def check_rate_limit_dependency(api_key: str, plan: str = "free") -> RateLimitResult:
    """FastAPI dependency for rate limiting."""
    if _limiter is None:
        # No rate limiting configured
        return RateLimitResult(
            allowed=True,
            remaining=999999,
            limit=999999,
            reset_at=datetime.utcnow() + timedelta(days=1)
        )
    
    try:
        plan_enum = Plan(plan)
    except ValueError:
        plan_enum = Plan.SPARK
    
    return _limiter.check_rate_limit(api_key, plan_enum)
