import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_API_BASE = os.getenv('OPENAI_API_BASE')
    OPENAI_API_MODEL = os.getenv('OPENAI_API_MODEL')
    
    # Twitter credentials
    TWITTER_USERNAME = os.getenv('TWITTER_USERNAME')
    TWITTER_PASSWORD = os.getenv('TWITTER_PASSWORD')
    
    # Bluesky credentials
    BLUESKY_IDENTIFIER = os.getenv('BLUESKY_IDENTIFIER')
    BLUESKY_PASSWORD = os.getenv('BLUESKY_PASSWORD') 