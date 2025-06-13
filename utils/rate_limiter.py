"""Rate limiter utility for controlling API request frequency."""

import time
from typing import Optional, Callable, Any
from functools import wraps


class RateLimiter:
    """Rate limiter for API calls with exponential backoff."""
    
    def __init__(self, calls_per_second: float = 2.0, max_retries: int = 3):
        """
        Initialize rate limiter.
        
        Args:
            calls_per_second: Maximum number of calls per second
            max_retries: Maximum number of retries for failed requests
        """
        self.calls_per_second = calls_per_second
        self.delay = 1.0 / calls_per_second if calls_per_second > 0 else 0.5
        self.max_retries = max_retries
        self.last_call_time = 0.0
    
    def wait_if_needed(self):
        """Wait if necessary to respect rate limits."""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        
        if time_since_last_call < self.delay:
            sleep_time = self.delay - time_since_last_call
            time.sleep(sleep_time)
        
        self.last_call_time = time.time()
    
    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with rate limiting and retry logic.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or None if all retries failed
        """
        for attempt in range(self.max_retries):
            try:
                self.wait_if_needed()
                result = func(*args, **kwargs)
                
                # Check if result indicates rate limiting (HTTP 429)
                if hasattr(result, 'status_code') and result.status_code == 429:
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    print(f"Rate limited (429), waiting {wait_time}s before retry {attempt + 1}/{self.max_retries}")
                    time.sleep(wait_time)
                    continue
                
                return result
                
            except Exception as e:
                print(f"Error in attempt {attempt + 1}/{self.max_retries}: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = (attempt + 1) * 1.5
                    time.sleep(wait_time)
                else:
                    print(f"Max retries reached, giving up")
                    return None
        
        return None


def rate_limited(calls_per_second: float = 2.0, max_retries: int = 3):
    """
    Decorator for rate limiting function calls.
    
    Args:
        calls_per_second: Maximum number of calls per second
        max_retries: Maximum number of retries for failed requests
    """
    def decorator(func: Callable) -> Callable:
        limiter = RateLimiter(calls_per_second, max_retries)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return limiter.execute_with_retry(func, *args, **kwargs)
        
        return wrapper
    
    return decorator


class RequestThrottler:
    """Simple request throttler with configurable delays."""
    
    def __init__(self, min_delay: float = 0.5, max_delay: float = 2.0):
        """
        Initialize throttler.
        
        Args:
            min_delay: Minimum delay between requests in seconds
            max_delay: Maximum delay for exponential backoff in seconds
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request_time = 0.0
        self.consecutive_errors = 0
    
    def throttle(self, error_occurred: bool = False):
        """
        Apply throttling delay.
        
        Args:
            error_occurred: Whether the last request resulted in an error
        """
        current_time = time.time()
        
        if error_occurred:
            self.consecutive_errors += 1
            # Exponential backoff for errors
            delay = min(self.min_delay * (2 ** self.consecutive_errors), self.max_delay)
        else:
            self.consecutive_errors = 0
            delay = self.min_delay
        
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < delay:
            sleep_time = delay - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def reset(self):
        """Reset error counter."""
        self.consecutive_errors = 0 