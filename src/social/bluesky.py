from atproto import Client
from ..config import Config

class BlueskyClient:
    def __init__(self):
        self.client = Client()
        self.setup_auth()
    
    def setup_auth(self):
        """Authenticate with Bluesky using credentials from config"""
        try:
            profile = self.client.login(
                Config.BLUESKY_IDENTIFIER,
                Config.BLUESKY_PASSWORD
            )
            print(f"Logged in as: {profile.display_name}")
        except Exception as e:
            print(f"Error authenticating with Bluesky: {e}")
    
    def post_content(self, content: str):
        """Post content to Bluesky"""
        try:
            post = self.client.send_post(text=content)
            return post
        except Exception as e:
            print(f"Error posting to Bluesky: {e}")
            return None
    
    def get_timeline(self, limit: int = 20):
        """Fetch user's timeline"""
        try:
            return self.client.get_timeline(limit=limit)
        except Exception as e:
            print(f"Error fetching timeline: {e}")
            return None
    
    def get_post_thread(self, uri: str):
        """Fetch a post and its replies"""
        try:
            return self.client.get_post_thread(uri)
        except Exception as e:
            print(f"Error fetching post thread: {e}")
            return None 