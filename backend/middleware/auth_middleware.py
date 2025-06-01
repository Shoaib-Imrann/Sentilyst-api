from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import HTTPException
from jose import jwt, JWTError
import os

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        authorization: str = request.headers.get("Authorization")
        if authorization:
            try:
                scheme, token = authorization.split()
                if scheme.lower() != "bearer":
                    raise HTTPException(status_code=401, detail="Invalid authentication scheme.")
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                # print("✅ Decoded Token Payload:", payload)
                user_id = payload.get("sub")
                # print("✅ User ID:", user_id)
                if not user_id:
                    # Instead of raising, set user to None and continue
                    request.state.user = None
                else:
                    request.state.user = user_id
            except (JWTError, ValueError):
                # Instead of raising, set user to None and continue
                request.state.user = None
        else:
            # No token provided, user_id will be None
            request.state.user = None

        response: Response = await call_next(request)
        return response
