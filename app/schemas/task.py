from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Priority = Literal["low","medium","high"]

class TaskCreate(BaseModel):
    title: str = Field(min_length=1,max_length=200)
    description: str | None = None
    priority: Priority = "medium"

class TaskUpdate(BaseModel):
    title: str | None = Field(default=None,min_length=1,max_length=200)
    description: str | None = None
    priority: Priority | None = None
    is_completed: bool | None = None

class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    priority: Priority
    is_completed: bool
    owner_id: int
    created_at: datetime