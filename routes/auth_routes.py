from fastapi import APIRouter, HTTPException
import logging
from models import UserRegister, UserLogin
from database import supabase
from auth import hash_password, verify_password, create_token

router = APIRouter()
logger = logging.getLogger("uvicorn.error")


@router.post("/api/register")
async def register(user: UserRegister):
    try:
        # Check if user exists
        existing = supabase.table("users").select("*").eq("email", user.email).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create user
        hashed_pw = hash_password(user.password)
        result = supabase.table("users").insert({
            "username": user.username,
            "email": user.email,
            "password": hashed_pw
        }).execute()
        
        user_data = result.data[0]
        user_id = user_data.get("user_id") or user_data.get("id")
        token = create_token(user_id, user_data["email"])
        
        return {
            "message": "User registered successfully",
            "token": token,
            "user": {
                "user_id": user_id,
                "username": user_data["username"],
                "email": user_data["email"],
            }
        }
    except HTTPException:
        # surface validation or bad-request style errors directly
        raise
    except Exception as e:
        # Log server-side, but keep response generic
        logger.exception("Registration failed")
        raise HTTPException(status_code=500, detail="Registration failed") from e


@router.post("/api/login")
async def login(user: UserLogin):
    try:
        # Find user
        result = supabase.table("users").select("*").eq("email", user.email).execute()
        if not result.data:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        user_data = result.data[0]
        user_id = user_data.get("user_id") or user_data.get("id")
        
        # Verify password
        if not verify_password(user.password, user_data["password"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        token = create_token(user_id, user_data["email"])
        
        return {
            "message": "Login successful",
            "token": token,
            "user": {
                "user_id": user_id,
                "username": user_data["username"],
                "email": user_data["email"],
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Login failed")
        raise HTTPException(status_code=500, detail="Login failed") from e
