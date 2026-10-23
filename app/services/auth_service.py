from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate

def register_user(
        db: Session,
        user_data: UserCreate,
) -> User:
    
    # Check whether the email already exists.

    statement = select(User).where(
        User.email == str(user_data.email)
    )

    existing_user = db.scalar(statement)

    if existing_user:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    # Hash the password before saving it.
    new_user = User(name = user_data.name,email=str(user_data.email), hashed_password=hash_password(user_data.password))

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

    except IntegrityError as exc:
        db.rollback()

        # Handles a duplicate-email race condition.
        raise HTTPException(status_code=409,detail="An account with this email already exists.") from exc

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(status_code=500, detail="Could not create the account.") from exc

    return new_user
