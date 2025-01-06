import asyncio
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base
from src.scheduler.task_scheduler import TaskScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    try:
        # Create database engine and session
        engine = create_engine("sqlite:///data/social_bot.db")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Initialize task scheduler
        scheduler = TaskScheduler(db, log_level=logging.INFO)
        
        # Start scheduler tasks
        await scheduler.start()
        
        try:
            # Keep the script running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            # Stop scheduler tasks
            await scheduler.stop()
            
    except Exception as e:
        logger.error(f"Error in main: {str(e)}", exc_info=True)
    finally:
        # Close database connection
        db.close()

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main()) 