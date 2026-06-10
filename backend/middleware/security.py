from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add OWASP recommended security headers"""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # OWASP recommended security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response

class RequestSizeLimiterMiddleware(BaseHTTPMiddleware):
    """Limit request body size to prevent DoS attacks"""
    def __init__(self, app, max_size: int = 1024 * 1024):  # 1MB default
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"Request body too large. Maximum size: {self.max_size} bytes"
                )
        
        return await call_next(request)
