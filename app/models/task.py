from datetime import datetime

from sqlalchemy import ( Boolean, CheckConstraint,DateTime,ForeignKey,String,Text,func)
from sqlalchemy.orm import Mapped,mapped_column,relationship

from app.db.base import Base

class Task(Base):
    __tablename__ = "tasks"

    __table_args__ = (
        CheckConstraint("priority IN ('low', 'medium','high')",
        name= "ck_tasks_prirority",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True,index=True,)

    title: Mapped[str] = mapped_column(String(200), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    priority: Mapped[str] = mapped_column(String(10), default="medium", server_default="medium",nullable=False)

    is_completed:Mapped[bool] = mapped_column(Boolean,default=False,server_default="0",nullable=False)

    owner_id:Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"),nullable=False,index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)

    owner: Mapped["User"] = relationship(back_populates="tasks")