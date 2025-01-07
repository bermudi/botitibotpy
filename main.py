from src.config import Config
from src.content.generator import ContentGenerator
from src.social.twitter import TwitterClient
from src.social.bluesky import BlueskyClient
from src.logging import setup_logging
import logging

def main():
    # Initialize logging
    loggers = setup_logging(Config.APP_NAME)
    logger = logging.getLogger(Config.APP_NAME)
    logger.info("Starting Botitibot application")
    
    try:
        # Initialize content generator
        logger.info("Initializing content generator")
        content_generator = ContentGenerator()
        
        # Initialize social media clients
        logger.info("Initializing social media clients")
        twitter_client = TwitterClient()
        bluesky_client = BlueskyClient()
        
        # Basic test to generate and post content
        logger.info("Generating content")
        content = content_generator.generate_content("Test prompt")
        
        logger.info("Posting content to social media platforms")
        twitter_client.post_content(content)
        bluesky_client.post_content(content)
        
        logger.info("Content posted successfully")
    except Exception as e:
        logger.error("Application error", exc_info=True)
        raise
    
if __name__ == "__main__":
    main()