"""
Rate Limiting Middleware for FastAPI
Prevents abuse of expensive endpoints by limiting requests per IP.
"""

import os
import sys
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
from collections import defaultdict

# Add parent directory to path for config import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import RateLimitConfig, get_logger

logger = get_logger("rate_limiter")


class RateLimitStore:
    """Simple in-memory rate limit store."""
    
    def __init__(self):
        # Structure: {client_ip: {endpoint: [timestamps]}}
        self.requests = defaultdict(lambda: defaultdict(list))
        self.lock = __import__('threading').Lock()
    
    def is_allowed(self, client_ip: str, endpoint: str, limit: str) -> bool:
        """
        Check if request is allowed based on rate limit.
        
        Args:
            client_ip: Client IP address
            endpoint: API endpoint path
            limit: Rate limit in format "5/second" or "100/minute"
            
        Returns:
            True if allowed, False if rate limited
        """
        # Parse limit format
        try:
            requests_allowed, time_window = limit.split("/")
            requests_allowed = int(requests_allowed)
        except ValueError:
            logger.error(f"Invalid limit format: {limit}")
            return True
        
        # Convert time window to seconds
        if time_window == "second":
            window_seconds = 1
        elif time_window == "minute":
            window_seconds = 60
        else:
            window_seconds = int(time_window)
        
        with self.lock:
            now = time.time()
            cutoff = now - window_seconds
            
            # Get requests for this client+endpoint
            request_times = self.requests[client_ip][endpoint]
            
            # Remove old requests outside window
            valid_requests = [t for t in request_times if t > cutoff]
            self.requests[client_ip][endpoint] = valid_requests
            
            # Check if allowed
            if len(valid_requests) < requests_allowed:
                valid_requests.append(now)
                return True
            
            return False
    
    def cleanup(self):
        """Clean up old entries (periodic maintenance)."""
        with self.lock:
            now = time.time()
            cutoff = now - 3600  # Keep 1 hour of history
            
            for client_ip in list(self.requests.keys()):
                for endpoint in list(self.requests[client_ip].keys()):
                    valid = [t for t in self.requests[client_ip][endpoint] if t > cutoff]
                    if valid:
                        self.requests[client_ip][endpoint] = valid
                    else:
                        del self.requests[client_ip][endpoint]
                
                if not self.requests[client_ip]:
                    del self.requests[client_ip]


# Global rate limit store
_store = RateLimitStore()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI.
    Enforces limits on expensive operations.
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request with rate limiting.
        """
        try:
            # Get client IP (safely)
            client_ip = "unknown"
            if request.client:
                client_ip = request.client.host
            
            endpoint = request.url.path
            
            # Check if endpoint has a rate limit
            if endpoint in RateLimitConfig.LIMITS:
                limit = RateLimitConfig.LIMITS[endpoint]
                
                if not _store.is_allowed(client_ip, endpoint, limit):
                    logger.warning(f"Rate limit exceeded for {client_ip} on {endpoint}")
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": "Too Many Requests",
                            "message": f"Rate limit exceeded: {limit}",
                            "retry_after": 60
                        }
                    )
            
            # Allow request to pass through
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Rate limiter error: {e}", exc_info=True)
            # On error, allow the request to pass through
            response = await call_next(request)
            return response


def get_rate_limit_stats() -> dict:
    """Get current rate limiting statistics."""
    with _store.lock:
        total_ips = len(_store.requests)
        total_endpoints = sum(len(endpoints) for endpoints in _store.requests.values())
        
        return {
            "tracked_ips": total_ips,
            "tracked_endpoints": total_endpoints,
            "limits": RateLimitConfig.LIMITS
        }
