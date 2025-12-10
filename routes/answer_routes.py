from fastapi import APIRouter, HTTPException
from datetime import datetime
from models import AnswerCreate
from database import supabase
from websocket import manager
from routes.question_routes import get_username

router = APIRouter()


@router.post("/api/answers")
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


@router.get("/api/answers/{question_id}")
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
