from src.config import Config
from src.content.generator import ContentGenerator
from src.social.twitter import TwitterClient
from src.social.bluesky import BlueskyClient

def main():
    # Initialize content generator
    content_generator = ContentGenerator()
    
    # Initialize social media clients
    twitter_client = TwitterClient()
    bluesky_client = BlueskyClient()
    
    # Basic test to generate and post content
    content = content_generator.generate_content("Test prompt")
    twitter_client.post_content(content)
    bluesky_client.post_content(content)

if __name__ == "__main__":
    main() 