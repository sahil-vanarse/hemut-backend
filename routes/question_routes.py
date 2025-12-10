from fastapi import APIRouter, HTTPException
import logging
from typing import Optional
from datetime import datetime
import os
import google.generativeai as genai
from models import QuestionCreate, QuestionUpdate
from database import supabase
from websocket import manager
from config import WEBHOOK_URL, GOOGLE_API_KEY

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

# Configure Gemini AI
genai.configure(api_key=GOOGLE_API_KEY)


def get_username(user_id: Optional[str]) -> str:
    """Get username from user_id, returns 'Anonymous' if not found."""
    if not user_id:
        return "Anonymous"
    try:
        res = supabase.table("users").select("username").eq("user_id", user_id).execute()
        if res.data and res.data[0].get("username"):
            return res.data[0]["username"]
    except Exception:
        pass
    return "Anonymous"


async def notify_webhook(event: str, data: dict):
    """Send webhook notification for events."""
    if not WEBHOOK_URL:
        return
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(WEBHOOK_URL, json={"event": event, "data": data})
    except:
        pass


@router.post("/api/questions")
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


@router.get("/api/questions")
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


@router.put("/api/questions/{question_id}")
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


@router.post("/api/questions/{question_id}/suggest")
async def suggest_answer(question_id: str):
    try:
        # Get the question from the database
        question_data = supabase.table('questions').select('*').eq('question_id', question_id).execute()
        if not question_data.data:
            raise HTTPException(status_code=404, detail="Question not found")
        
        question = question_data.data[0]
        
        # Initialize the Gemini model
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Create the prompt
        prompt = f"""
        You are a helpful assistant that provides suggestions for answering questions in a forum.
        The user has asked: "{question['message']}"
        
        Provide a helpful and concise suggestion for answering this question.
        Focus on the key points and be specific.
        
        Suggestion:
        """
        
        # Generate the response
        response = model.generate_content(prompt)
        
        return {"suggestion": response.text.strip()}
        
    except Exception as e:
        logger.error(f"Error generating suggestion: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate suggestion")
