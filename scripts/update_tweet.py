from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base, models
from src.database.models import Platform

# Create database engine and session
engine = create_engine('sqlite:///data/social_bot.db')
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

# Update the tweet ID
post = db.query(models.Post).filter_by(platform_post_id='1744520012345678901').first()
if post:
    post.platform_post_id = '1876793833179979949'
    db.commit()
    print("Updated tweet ID successfully")
else:
    print("Tweet not found in database") 