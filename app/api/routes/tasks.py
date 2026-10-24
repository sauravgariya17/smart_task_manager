from fastapi import APIRouter , Depends, HTTPException , Response,status, Query
from sqlalchemy import select, func, case
from sqlalchemy.exc import SQLAlchemyError
from  sqlalchemy.orm import Session
from typing import Literal

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate,TaskResponse,TaskUpdate, TaskPageResponse,TaskStatsResponse

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


@router.get("", response_model=TaskPageResponse)
def list_tasks(
    is_completed: bool | None = None,
    priority: Literal["low","medium","high"] | None = None,
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
    ),
    sort_by: Literal["created_at", "title","priority"] = "created_at",
    order: Literal["asc","desc"] = "desc",
    limit: int = Query(default=10,ge=1,le=100),
    offset: int = Query(default=0,ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # Apply ownership and optional filters.
    conditions = [Task.owner_id == current_user.id]

    if is_completed is not None:
        conditions.append(Task.is_completed == is_completed)

    if priority is not None:
        conditions.append(Task.priority == priority)

    if search is not None:
        conditions.append(Task.title.ilike(f"%{search}%"))

    # Count all matching tasks, not just the current page
    count_statement = (
        select(func.count(Task.id))
        .select_from(Task)
        .where(*conditions)
    )
    total = db.scalar(count_statement) or 0

    # Select a permitted sorting column.
    sort_column = {
        "created_at" : Task.created_at,
        "title" : Task.title,
        "priority": Task.priority
    }
    sort_column = sort_column[sort_by]

    # Apply ascending or descending order
    if order == "asc":
        ordering = (sort_column.asc(), Task.id.asc())
    else:
        ordering = (sort_column.desc(),Task.id.desc())

    # Fetch only the requested page.
    statement = (
        select(Task)
        .where(*conditions)
        .order_by(*ordering)
        .offset(offset)
        .limit(limit)
    )

    items = list(db.scalars(statement).all())

    return TaskPageResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset+len(items)) < total,
    )

@router.get("/stats",response_model=TaskStatsResponse)
def get_task_stats(
    db:Session = Depends(get_db),
    current_user : User = Depends(get_current_user)
):

    statement = select(
        func.count(Task.id),
        func.coalesce(
            func.sum(
                case(
                    (Task.is_completed.is_(True),1),
                    else_=0,
                )
            ),
            0,
        ),
        func.coalesce(
            func.sum(
                case(
                    (Task.is_completed.is_(False),1),
                    else_=0,
                )
            ),
            0,
        ),
        func.coalesce(
            func.sum(
                case(
                    (Task.priority == "high", 1),
                    else_=0,
                )
            ),
            0,
        ),
    ).where(Task.owner_id == current_user.id)

    row = db.execute(statement).one()

    return TaskStatsResponse(
        total_tasks=int(row[0]),
        completed_tasks=int(row[1]),
        pending_tasks=int(row[2]),
        high_priority_tasks=int(row[3]),
    )




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




