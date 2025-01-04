from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path

# Create the database directory if it doesn't exist
db_dir = Path("data")
db_dir.mkdir(exist_ok=True)

# Create SQLite database engine
SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_dir}/social_bot.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base for models
Base = declarative_base()

def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 