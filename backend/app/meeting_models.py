from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime

class Meeting(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(description="Purpose or title of the meeting")
    start_time: datetime = Field(description="Start time of the meeting")
    end_time: datetime = Field(description="End time of the meeting")
    participants: str = Field(description="Comma  separated list of participants")
    status: str = Field(default="scheduled", description="Status: scheduled, cancelled")
    created_at: datetime = Field(default_factory=datetime.utcnow)


