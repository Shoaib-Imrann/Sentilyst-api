import os
import random
import uuid
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from services.email import send_email_otp
from supabase import Client, create_client

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class EmailRequest(BaseModel):
    email: EmailStr

class OTPVerifyRequest(BaseModel):
    jwt_token: str
    otp: str

class RegisterRequest(BaseModel):
    email: EmailStr
    fullName: str
    password: str


def generate_otp() -> str:
    return f"{random.SystemRandom().randint(100000, 999999)}"

def create_otp_jwt(email: str, otp: str) -> str:
    payload = {"email": email, "otp": otp}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_otp_jwt(token: str):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
    
class CheckEmailRequest(BaseModel):
    email: EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class GoogleToken(BaseModel):
    token: str

async def send_otp(req: EmailRequest):
    email = req.email
    exists = supabase.table("users").select("email").eq("email", email).execute().data
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")

    otp = generate_otp()
    token = create_otp_jwt(email, otp)

    try:
        send_email_otp(email, otp)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email send error: {e}")

    return {"jwt": token}


async def verify_otp(req: OTPVerifyRequest):
    
    payload = verify_otp_jwt(req.jwt_token)
    if not payload or payload.get("otp") != req.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP or token")

    # If we reach here, OTP is verified
    return {"verified": True, "message": "OTP verified successfully"}


async def register(req: RegisterRequest, request: Request):
    if not req.password:
        raise HTTPException(status_code=400, detail="Password is required")
    
    hashed_pw = pwd_context.hash(req.password)

    ist_time = datetime.utcnow() + timedelta(hours=5, minutes=30)

    result = supabase.table("users").insert({
        "email": req.email,
        "full_name": req.fullName,
        "password": hashed_pw,
        "created_at": ist_time.isoformat(),
        "updated_at": ist_time.isoformat(),
    }).execute()

    if not result.data:
        raise HTTPException(
            status_code=500,
            detail="User registration failed. Supabase returned no data."
        )

    user = result.data[0]

    user_data = {
        "sub": str(user["id"]),
        "user_agent": request.headers.get("user-agent"),
        "ip_address": request.client.host,
    }

    access_token = jwt.encode(user_data, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return {"message": "User registered successfully", "token": access_token}



async def check_email(req: CheckEmailRequest):
    result = supabase.table("users").select("email").eq("email", req.email).execute()
    if result.data:
        return {"exists": True}
    else:
        return {"exists": False}
    



async def login(req: LoginRequest, request: Request):
    result = supabase.table("users").select("id, password, full_name").eq("email", req.email).single().execute()

    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = result.data
    stored_password = user["password"]
    full_name = user["full_name"]

    if not pwd_context.verify(req.password, stored_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create access token for login
    access_token_data = {
        "sub": str(user["id"]),
        "user_agent": request.headers.get("user-agent"),
        "ip_address": request.client.host,
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    access_token = jwt.encode(access_token_data, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return {"access_token": access_token, "token_type": "bearer"}




async def google_login(data: GoogleToken, request: Request):
    try:
        # 1. Verify token with Google
        google_token = data.token
        response = requests.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={google_token}")
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid Google token")
        
        user_info = response.json()
        email = user_info.get("email")
        name = user_info.get("name")
        picture = user_info.get("picture")

        if not email or not name:
            raise HTTPException(status_code=400, detail="Missing email or name in token")

        # 2. Check if user exists in Supabase
        existing_user = supabase.table("users").select("*").eq("email", email).execute()

        ist_time = datetime.utcnow() + timedelta(hours=5, minutes=30)

        if not existing_user.data:
            # 3. Create user if not exists
            user_id = str(uuid.uuid4())  # Generate UUID only when creating a new user
            new_user = {
                "id": user_id,
                "full_name": name,
                "email": email,
                "profile_url": picture,
                "password": None,  # No password as it's Google login
                "created_at": ist_time.isoformat(),
                "updated_at": ist_time.isoformat(),
            }
            insert_response = supabase.table("users").insert(new_user).execute()

            if not insert_response.data:
                raise HTTPException(status_code=500, detail="Google login user insert failed.")

            user_id = new_user["id"]
        else:
            user_id = existing_user.data[0]["id"]
            
            # Update the profile URL if it's a Google login for existing user
            if picture and (not existing_user.data[0].get("profile_url") or existing_user.data[0].get("profile_url") != picture):
                supabase.table("users").update({"profile_url": picture, "updated_at": ist_time.isoformat()}).eq("id", user_id).execute()

        # 4. Create your app's JWT
        payload = {
            "sub": user_id,
            "user_agent": request.headers.get("user-agent"),
            "ip_address": request.client.host,
            "exp": datetime.utcnow() + timedelta(days=7)
        }
        app_jwt = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

        return {"token": app_jwt}

    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail=str(e))



async def is_auth(request: Request):
    user =  request.state.user
    
    if user:
        return JSONResponse(content={"success": True, "message": "Authenticated"})
    else:
        return JSONResponse(content={"success": False, "message": "Not Authenticated"}, status_code=401)



async def get_user_data(request: Request):
    user_id =  request.state.user
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        result = (
            supabase
            .table("users")
            .select("full_name, email, profile_url")
            .eq("id", user_id)
            .single()
            .execute()
        )
        user = result.data

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return JSONResponse(content={
            "success": True,
            "userData": {
                "full_name": user["full_name"],
                "email": user["email"],
                "profile_url": user.get("profile_url")
            }
        })

    except Exception as e:
        # print("🔥 Error in get_user_data:", e)
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Error fetching user data"},
        )