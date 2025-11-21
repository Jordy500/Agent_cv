"""
Rate limiter utility for API calls (OpenAI, etc.)

Implements token bucket algorithm to prevent exceeding API rate limits.
"""
import time
import threading
from collections import deque


class RateLimiter:
    """Token bucket rate limiter.
    
    Example:
        limiter = RateLimiter(max_requests=60, time_window=60)  # 60 requests per minute
        
        with limiter:
            # Make API call
            response = api_call()
    """
    
    def __init__(self, max_requests, time_window):
        """Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.timestamps = deque()
        self.lock = threading.Lock()
    
    def __enter__(self):
        """Acquire rate limit token (blocks if limit reached)."""
        with self.lock:
            now = time.time()
            
            # Remove timestamps outside the time window
            while self.timestamps and self.timestamps[0] < now - self.time_window:
                self.timestamps.popleft()
            
            # Check if we've exceeded the rate limit
            if len(self.timestamps) >= self.max_requests:
                # Calculate how long to wait
                oldest_timestamp = self.timestamps[0]
                wait_time = (oldest_timestamp + self.time_window) - now
                
                if wait_time > 0:
                    print(f"Rate limit reached. Waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    # Re-clean the queue after waiting
                    now = time.time()
                    while self.timestamps and self.timestamps[0] < now - self.time_window:
                        self.timestamps.popleft()
            
            # Add current timestamp
            self.timestamps.append(now)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release (no-op for token bucket)."""
        pass


# Global rate limiters for different services
# OpenAI: 60 requests per minute for free tier (adjust based on your plan)
openai_limiter = RateLimiter(max_requests=20, time_window=60)  # Conservative: 20/min

# Adzuna: 1000 requests per month ≈ 33/day ≈ 1.4/hour (be very conservative)
adzuna_limiter = RateLimiter(max_requests=50, time_window=3600)  # 50 per hour
