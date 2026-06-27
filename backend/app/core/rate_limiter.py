import asyncio
import time
from typing import Callable, Any

class AsyncRateLimiter:
    """Token bucket rate limiter for LLM API calls."""
    def __init__(self, max_rpm: int = 25, provider: str = "groq"):
        self.semaphore = asyncio.Semaphore(max_rpm)
        self.interval = 60.0 / max_rpm  # seconds between requests
    
    async def acquire(self):
        await self.semaphore.acquire()
        # Release the semaphore token after the interval expires
        asyncio.get_running_loop().call_later(self.interval, self.semaphore.release)
    
    async def call(self, fn: Callable, *args, **kwargs) -> Any:
        await self.acquire()
        return await fn(*args, **kwargs)
