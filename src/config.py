import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Twitter credentials
    TWITTER_USERNAME = os.getenv('TWITTER_USERNAME')
    TWITTER_PASSWORD = os.getenv('TWITTER_PASSWORD')
    
    # Bluesky credentials
    BLUESKY_IDENTIFIER = os.getenv('BLUESKY_IDENTIFIER')
    BLUESKY_PASSWORD = os.getenv('BLUESKY_PASSWORD') 