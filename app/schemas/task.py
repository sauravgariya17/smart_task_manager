from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Priority = Literal["low","medium","high"]

class TaskCreate(BaseModel):
    title: str = Field(min_length=1,max_length=200)
    description: str | None = Field(default=None,max_length=2000)
    priority: Priority = "medium"

    @field_validator("title")
    @classmethod
    def validate_title(cls,value : str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Task title cannot be blank.")

        return value
    @field_validator("description")
    @classmethod
    def validate_description(cls,value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            return value or None

        return value

class TaskUpdate(BaseModel):
    title: str | None = Field(default=None,min_length=1,max_length=200)
    description: str | None = Field(default=None,max_length=2000)
    priority: Priority | None = None
    is_completed: bool | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls,value : str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()

        if not value:
            raise ValueError("Task title cannot be blank.")

        @field_validator("description")
        @classmethod
        def validate_description(cls,value: str | None) -> str|None:
            if value is not None:
                value = value.strip()
                return value or None
            return value


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    priority: Priority
    is_completed: bool
    owner_id: int
    created_at: datetime

class TaskPageResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    limit: int
    offset: int
    has_more: bool

class TaskStatsResponse(BaseModel):
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    high_priority_tasks: int