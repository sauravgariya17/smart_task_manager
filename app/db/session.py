import os

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import sessionmaker

# Load variables from the project's root .env file.
load_dotenv()

# Read database settings from environment variables.
db_host = os.getenv("DB_HOST","localhost")
db_port = int(os.getenv("DB_PORT","3306"))
db_name = os.getenv("DB_NAME","smart_task_manager")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")

if not db_user or not db_password:
    raise RuntimeError(
        "Set DB_USER and DB_PASSWORD in your .env file"
    )

# Build the connection URL safely.
database_url = URL.create(
    drivername="mysql+pymysql",
    username=db_user,
    password=db_password,
    host=db_host,
    port=db_port,
    database=db_name,
)

# Create the SQLAlchemy engine.
engine = create_engine(
    database_url,
    pool_pre_ping=True,
)

# Create a factory for database sessions.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

# Provide one session per request.
def get_db():
    db=SessionLocal()

    try:
        yield db
    finally:
        db.close()