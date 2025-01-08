from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base, models, operations
from src.database.models import Platform

# Create database engine and session
engine = create_engine('sqlite:///data/social_bot.db')
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

# Create Twitter credentials if they don't exist
creds = db.query(models.Credentials).filter_by(platform=Platform.TWITTER, username='botitibot').first()
if not creds:
    creds = models.Credentials(platform=Platform.TWITTER, username='botitibot', auth_data={})
    db.add(creds)
    db.commit()
    db.refresh(creds)

# Add the tweet to the database
db_ops = operations.DatabaseOperations(db)
db_ops.create_post(
    credentials_id=creds.id,
    platform_post_id='1744520012345678901',  # Replace with actual tweet ID
    content='Hey Twitter fam! 🚀 Just testing out the Twitter API with my botitibot! 🤖 Can\'t wait to see what cool stuff we can create together! Stay tuned for some fun updates! 🎉 #BotLife #TwitterAPI #TechFun'
) 