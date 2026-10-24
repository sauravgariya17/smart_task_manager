from fastapi import APIRouter , Depends, HTTPException , Response,status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from  sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate,TaskResponse,TaskUpdate

router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"],
)

@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
    ):

    new_task = Task(
        title = task_data.title,
        description = task_data.description,
        priority = task_data.priority,
        owner_id = current_user.id,
    )

    try:
        db.add(new_task)
        db.commit()
        db.refresh(new_task)

    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="could not create the task"
        ) from exc

    return new_task


@router.get("", response_model=list[TaskResponse])
def list_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    statement = (
        select(Task)
        .where(Task.owner_id == current_user.id)
        .order_by(Task.created_at.desc(), Task.id.desc())
    )

    return list(db.scalars(statement).all())


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    statement = select(Task).where(
        Task.id == task_id,
        Task.owner_id == current_user.id
    )

    task = db.scalar(statement)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task Not Found."
        )

    changes  = task_data.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one field to update."
        )

    # Required fields cannot be set to null.
    for field in ("title", "priority", "is_completed"):
        if field in changes and changes[field] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{field} cannot be null."
            )


    for field , value in changes.items():
        setattr(task,field,value)

    try:
        db.commit()
        db.refresh(task)

    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="could not update the task."
        ) from exc

    return task


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    statement = select(Task).where(
        Task.id == task_id,
        Task.owner_id == current_user.id
    )

    task = db.scalar(statement)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task Not Found."
        )

    try:
        db.delete(task)
        db.commit()

    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete the task."
        ) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)




