import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

class Config:
    # Application Configuration
    APP_NAME = "botitibot"
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_DIR = Path("logs")
    
    # Component Log Levels (can be overridden by environment variables)
    CONTENT_LOG_LEVEL = os.getenv('CONTENT_LOG_LEVEL', LOG_LEVEL)
    SOCIAL_LOG_LEVEL = os.getenv('SOCIAL_LOG_LEVEL', LOG_LEVEL)
    SCHEDULER_LOG_LEVEL = os.getenv('SCHEDULER_LOG_LEVEL', LOG_LEVEL)
    DATABASE_LOG_LEVEL = os.getenv('DATABASE_LOG_LEVEL', LOG_LEVEL)
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_API_BASE = os.getenv('OPENAI_API_BASE')
    OPENAI_API_MODEL = os.getenv('OPENAI_API_MODEL')
    
    @classmethod
    def validate(cls) -> None:
        """Validate required environment variables are set"""
        required_vars = [
            'OPENAI_API_KEY',
            # 'TWITTER_USERNAME',
            # 'TWITTER_PASSWORD',
            # 'BLUESKY_IDENTIFIER',
            # 'BLUESKY_PASSWORD'
        ]
        
        missing = [var for var in required_vars if not getattr(cls, var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    # Google API Configuration
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    
    # Twitter credentials
    TWITTER_USERNAME = os.getenv('TWITTER_USERNAME')
    TWITTER_PASSWORD = os.getenv('TWITTER_PASSWORD')
    
    # Bluesky credentials
    BLUESKY_IDENTIFIER = os.getenv('BLUESKY_IDENTIFIER')
    BLUESKY_PASSWORD = os.getenv('BLUESKY_PASSWORD') 
