import logging
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("sentilyst.security")

class SecurityEventLogger(BaseHTTPMiddleware):
    """Log security-relevant events like rate limits, large requests, etc."""
    
    def __init__(self, app):
        super().__init__(app)
        self.suspicious_ips = defaultdict(int)
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        
        # Log potentially suspicious patterns
        if request.method not in ["GET", "POST", "OPTIONS"]:
            logger.warning(f"Suspicious HTTP method {request.method} from {client_ip}")
        
        response = await call_next(request)
        
        # Log rate limit violations
        if response.status_code == 429:
            self.suspicious_ips[client_ip] += 1
            logger.warning(f"Rate limit exceeded for IP {client_ip} (violations: {self.suspicious_ips[client_ip]})")
        
        # Log oversized requests
        if response.status_code == 413:
            logger.warning(f"Oversized request rejected from IP {client_ip}")
        
        return response
