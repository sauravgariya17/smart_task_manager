from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.tasks import router as tasks_router
from app.api.routes.auth import router as auth_router
from app.db.session import get_db

#create the FastAPI application

app = FastAPI(
    title="Smart Task Manager API",
    description="A learning project",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register authentication endpoints.
app.include_router(auth_router)
app.include_router(tasks_router)


#welcome endpoint
@app.get("/")
def home():
    return {"message": "Welcome to Smart task Manager"}

@app.get("/about")
def about():
    return{"message": "This is Smart Task Manager"}

#Health-check endpoint
@app.get("/health")
def health_check():
    return{"status": "heathy"}

@app.get("/db-health")
def database_health_check(
    db: Session = Depends(get_db),
):
    try:
        db.execute(text("SELECT 1"))

        return{
            "status": "healthy",
            "database": "connected",
        }

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=503,
            detail="Database is unavialable",
        ) from exc

