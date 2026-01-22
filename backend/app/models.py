from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    name: str
    avatar_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    provider: str = "google" 

class Email(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    gmail_id: str = Field(index=True, unique=True) # New Field for Deduplication
    user_id: int = Field(foreign_key="user.id")
    subject: str
    sender: str
    snippet: str
    body: Optional[str] = Field(default=None)
    received_time: datetime
    # Analysis Fields
    summary: Optional[str] = Field(default=None)
    intent: str
    urgency_score: int
    risk_level: str
    priority: str
    requires_action: bool
    is_read: bool = False
    # Smart Features
    suggested_reply: Optional[str] = Field(default=None)
    sentiment: Optional[str] = Field(default=None)
    tone: Optional[str] = Field(default=None)

class UserRead(SQLModel):
    id: int
    email: str
    name: str
    avatar_url: Optional[str]

class ChatHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sender: str # 'user' or 'agent'
    text: str # stored as plain text
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_email: str = Field(index=True, default=None, nullable=True) # Data isolation
