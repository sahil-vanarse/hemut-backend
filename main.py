from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
import types
import bcrypt
import logging
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, field_validator
from typing import List, Optional
import os
from datetime import datetime
import json
from supabase import create_client, Client
from passlib.context import CryptContext
import jwt
from jwt.exceptions import InvalidTokenError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
JWT_SECRET = os.getenv("JWT_SECRET")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

# Validate required environment variables
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")

# Initialize Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Some bcrypt builds ship without __about__.__version__, which passlib expects.
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = types.SimpleNamespace(
        __version__=getattr(bcrypt, "__version__", "unknown")
    )

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# bcrypt ignores everything after 72 bytes; enforce a hard cap to avoid surprises
MAX_PASSWORD_BYTES = 72

app = FastAPI(title="Hemut Q&A Dashboard API")
logger = logging.getLogger("uvicorn.error")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add WebSocket CORS handling
from starlette.middleware import Middleware
from starlette.websockets import WebSocket as StarletteWebSocket

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        disconnected = []
        print(f"Broadcasting to {len(self.active_connections)} connections: {message.get('type')}")
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
                print(f"Successfully sent {message.get('type')} to connection")
            except Exception as e:
                print(f"Error sending message: {e}")
                disconnected.append(connection)
        # Remove disconnected connections
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)

manager = ConnectionManager()

# Pydantic models
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator('username')
    def username_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Username cannot be empty')
        return v.strip()

    @field_validator('password')
    def password_strong(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class QuestionCreate(BaseModel):
    message: str
    user_id: Optional[str] = None  # Supabase uses uuid for question owner

    @field_validator('message')
    def message_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Question cannot be empty')
        return v.strip()

class QuestionUpdate(BaseModel):
    status: str

    @field_validator('status')
    def valid_status(cls, v):
        if v not in ['Pending', 'Escalated', 'Answered']:
            raise ValueError('Invalid status')
        return v

class AnswerCreate(BaseModel):
    question_id: str  # Supabase uses uuid for question_id
    answer: str
    user_id: Optional[str] = None  # Supabase uses uuid for answer owner

    @field_validator('answer')
    def answer_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Answer cannot be empty')
        return v.strip()

# Helper functions
def validate_password_length(password: str):
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Password cannot be longer than {MAX_PASSWORD_BYTES} bytes. "
            "Please choose a shorter password.",
        )


def hash_password(password: str) -> str:
    validate_password_length(password)
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    validate_password_length(plain_password)
    return pwd_context.verify(plain_password, hashed_password)

def create_token(user_id: int, email: str) -> str:
    payload = {"user_id": user_id, "email": email}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_username(user_id: Optional[str]) -> str:
    if not user_id:
        return "Anonymous"
    try:
        res = supabase.table("users").select("username").eq("user_id", user_id).execute()
        if res.data and res.data[0].get("username"):
            return res.data[0]["username"]
    except Exception:
        pass
    return "Anonymous"

# Webhook notification
async def notify_webhook(event: str, data: dict):
    if not WEBHOOK_URL:
        return
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(WEBHOOK_URL, json={"event": event, "data": data})
    except:
        pass

# Routes
@app.get("/")
def read_root():
    return {"message": "Hemut Q&A Dashboard API", "status": "running"}

@app.post("/api/register")
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

@app.post("/api/login")
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

@app.post("/api/questions")
async def create_question(question: QuestionCreate):
    try:
        result = supabase.table("questions").insert({
            "user_id": question.user_id,
            "message": question.message,
            "status": "Pending",
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        
        question_data = result.data[0]
        question_data["username"] = get_username(question.user_id)
        
        # Broadcast to WebSocket clients
        await manager.broadcast({
            "type": "new_question",
            "data": question_data
        })
        
        return {"message": "Question created", "question": question_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/questions")
async def get_questions():
    try:
        result = supabase.table("questions").select("*, users(username)").order("created_at", desc=True).execute()
        
        questions = []
        for q in result.data:
            questions.append({
                **q,
                "username": q.get("users", {}).get("username", "Anonymous") if q.get("users") else "Anonymous"
            })
        
        # Sort: Escalated first, then by timestamp
        questions.sort(key=lambda x: (x["status"] != "Escalated", x["created_at"]), reverse=True)
        
        return {"questions": questions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/questions/{question_id}")
async def update_question(question_id: str, update: QuestionUpdate):
    try:
        result = supabase.table("questions").update({
            "status": update.status
        }).eq("question_id", question_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Question not found")
        
        question_data = result.data[0]
        question_data["username"] = get_username(question_data.get("user_id"))
        
        # Broadcast update
        await manager.broadcast({
            "type": "question_updated",
            "data": question_data
        })
        
        # Webhook notification
        if update.status == "Answered":
            await notify_webhook("question_answered", question_data)
        
        return {"message": "Question updated", "question": question_data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/answers")
async def create_answer(answer: AnswerCreate):
    try:
        result = supabase.table("answers").insert({
            "question_id": answer.question_id,
            "user_id": answer.user_id,
            "answer": answer.answer,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        
        answer_data = result.data[0]
        answer_data["username"] = get_username(answer.user_id)
        
        # Broadcast new answer
        await manager.broadcast({
            "type": "new_answer",
            "data": answer_data
        })
        
        return {"message": "Answer created", "answer": answer_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/answers/{question_id}")
async def get_answers(question_id: str):
    try:
        result = supabase.table("answers").select("*, users(username)").eq("question_id", question_id).order("created_at", desc=False).execute()
        
        answers = []
        for a in result.data:
            answers.append({
                **a,
                "username": a.get("users", {}).get("username", "Anonymous") if a.get("users") else "Anonymous"
            })
        
        return {"answers": answers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# AI-powered answer suggestion (bonus)
@app.post("/api/questions/{question_id}/suggest")
async def suggest_answer(question_id: str):
    try:
        # Get question
        result = supabase.table("questions").select("*").eq("question_id", question_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Question not found")
        
        question = result.data[0]
        
        # Simple mock AI suggestion (you can integrate LangChain here)
        suggestions = [
            f"Based on the question '{question['message']}', here are some helpful resources...",
            f"This question is related to common issues. Try checking the documentation.",
            f"Have you tried restarting the service? This often resolves similar issues."
        ]
        
        import random
        suggestion = random.choice(suggestions)
        
        return {"suggestion": suggestion}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    print("New WebSocket connection attempt from:", websocket.client)
    try:
        await manager.connect(websocket)
        print(f"✅ WebSocket connected. Total connections: {len(manager.active_connections)}")
    except Exception as e:
        print(f"❌ Error connecting WebSocket: {e}")
        return
    try:
        while True:
            try:
                # Wait for message with timeout to keep connection alive
                data = await websocket.receive_text()
                print(f"Received WebSocket message: {data}")
                # Echo received messages (can be used for ping/pong)
                await websocket.send_text(json.dumps({"type": "pong", "data": data}))
            except Exception as e:
                print(f"Error in WebSocket receive loop: {e}")
                # If there's an error receiving, break the loop
                break
    except WebSocketDisconnect:
        print("WebSocket disconnected normally")
    finally:
        manager.disconnect(websocket)
        print(f"WebSocket cleaned up. Remaining connections: {len(manager.active_connections)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)