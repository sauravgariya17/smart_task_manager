from fastapi import Depends,HTTPException,status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import JWT_ALGORITHM,JWT_SECRET_KEY
from app.db.session import get_db
from app.models.user import User
import jwt

bearer_scheme = HTTPBearer(auto_error=False)

def get_current_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(
            bearer_scheme
        ),
        db: Session = Depends(get_db)
) -> User:

    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"}
    )

    if credentials is None:
        raise unauthorized

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require":["sub","exp"]}
        )

        subject = payload.get("sub")

        if not isinstance(subject,str) or not subject.isdigit():
            raise unauthorized
        user_id = int(subject)

    except (jwt.InvalidTokenError, ValueError):
        raise unauthorized

    user = db.scalar(
        select(User).where(User.id == user_id)
    )

    if user is None:
        raise unauthorized

    return user