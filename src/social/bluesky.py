from atproto import Client, client_utils
from typing import Optional, Any
from ..config import Config

class BlueskyClient:
    def __init__(self):
        self.client = Client()
        self.profile = None
        self.setup_auth()
    
    def setup_auth(self) -> bool:
        """Authenticate with Bluesky using credentials from config"""
        try:
            self.profile = self.client.login(
                Config.BLUESKY_IDENTIFIER,
                Config.BLUESKY_PASSWORD
            )
            print(f"Logged in as: {self.profile.display_name}")
            return True
        except Exception as e:
            print(f"Error authenticating with Bluesky: {e}")
            return False
    
    def post_content(self, content: str, link: Optional[str] = None) -> Optional[Any]:
        """Post content to Bluesky with optional link"""
        try:
            text = client_utils.TextBuilder()
            text.text(content)
            
            if link:
                text.link("🔗", link)
                
            post = self.client.send_post(text)
            return post
        except Exception as e:
            print(f"Error posting to Bluesky: {e}")
            return None
    
    def get_timeline(self, limit: int = 20) -> Optional[Any]:
        """Fetch user's timeline"""
        try:
            return self.client.get_timeline(limit=limit)
        except Exception as e:
            print(f"Error fetching timeline: {e}")
            return None
    
    def get_post_thread(self, uri: str) -> Optional[Any]:
        """Fetch a post and its replies"""
        try:
            return self.client.get_post_thread(uri)
        except Exception as e:
            print(f"Error fetching post thread: {e}")
            return None
            
    def like_post(self, uri: str, cid: Optional[str] = None) -> Optional[Any]:
        """Like a post
        
        Args:
            uri: The URI of the post to like
            cid: Content ID of the post. If not provided, will be extracted from the post
        """
        try:
            if not cid:
                # If CID not provided, try to get it from the post
                post = self.get_post_thread(uri)
                if post and hasattr(post, 'thread') and hasattr(post.thread, 'post'):
                    cid = post.thread.post.cid
                else:
                    raise ValueError("Could not determine post CID")
            
            return self.client.like(uri, cid)
        except Exception as e:
            print(f"Error liking post: {e}")
            return None
            
    def reply_to_post(self, uri: str, text: str, cid: Optional[str] = None) -> Optional[Any]:
        """Reply to a post"""
        try:
            return self.client.send_post(text=text, reply_to=uri)
        except Exception as e:
            print(f"Error replying to post: {e}")
            return None 