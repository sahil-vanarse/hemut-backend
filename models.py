from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional


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
