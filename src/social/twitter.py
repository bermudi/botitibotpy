from twitter_openapi_python import TwitterOpenapiPython
import json
from pathlib import Path
from typing import Optional, Any
from ..config import Config

class TwitterClient:
    def __init__(self):
        self.client = TwitterOpenapiPython()
        # Set Windows headers as recommended in docs for compatibility
        self.client.additional_api_headers = {
            "sec-ch-ua-platform": '"Windows"',
        }
        self.client.additional_browser_headers = {
            "sec-ch-ua-platform": '"Windows"',
        }
        self.setup_auth()
    
    def setup_auth(self) -> bool:
        """Authenticate with Twitter using cookie-based authentication"""
        try:
            cookie_path = Path("twitter_cookie.json")
            
            if cookie_path.exists():
                with open(cookie_path, "r") as f:
                    cookies_dict = json.load(f)
                    if isinstance(cookies_dict, list):
                        cookies_dict = {k["name"]: k["value"] for k in cookies_dict}
            else:
                # For first time setup, credentials should be provided via config
                if not Config.TWITTER_USERNAME or not Config.TWITTER_PASSWORD:
                    raise ValueError("Twitter credentials not found in config")
                    
                from tweepy_authlib import CookieSessionUserHandler
                auth_handler = CookieSessionUserHandler(
                    screen_name=Config.TWITTER_USERNAME,
                    password=Config.TWITTER_PASSWORD
                )
                cookies_dict = auth_handler.get_cookies().get_dict()
                
                # Save cookies for future use
                with open(cookie_path, "w") as f:
                    json.dump(cookies_dict, f, ensure_ascii=False, indent=4)
            
            # Initialize client with cookies
            self.client = self.client.get_client_from_cookies(cookies=cookies_dict)
            return True
            
        except Exception as e:
            print(f"Error authenticating with Twitter: {e}")
            return False
    
    def post_content(self, content: str) -> bool:
        """Post content to Twitter"""
        try:
            self.client.get_post_api().post_create_tweet(tweet_text=content)
            return True
        except Exception as e:
            print(f"Error posting to Twitter: {e}")
            return False
            
    def get_timeline(self, limit: int = 20) -> Optional[Any]:
        """Fetch user's timeline"""
        try:
            user_api = self.client.get_user_api()
            timeline = user_api.get_home_timeline(count=limit)
            return timeline
        except Exception as e:
            print(f"Error fetching timeline: {e}")
            return None
            
    def get_tweet_thread(self, tweet_id: str) -> Optional[Any]:
        """Fetch a tweet and its replies"""
        try:
            tweet_api = self.client.get_tweet_api()
            return tweet_api.get_tweet_detail(tweet_id)
        except Exception as e:
            print(f"Error fetching tweet thread: {e}")
            return None
            
    def like_tweet(self, tweet_id: str) -> bool:
        """Like a tweet"""
        try:
            tweet_api = self.client.get_tweet_api()
            tweet_api.favorite_tweet(tweet_id)
            return True
        except Exception as e:
            print(f"Error liking tweet: {e}")
            return False
            
    def reply_to_tweet(self, tweet_id: str, text: str) -> bool:
        """Reply to a tweet"""
        try:
            post_api = self.client.get_post_api()
            post_api.post_create_tweet(tweet_text=text, reply_tweet_id=tweet_id)
            return True
        except Exception as e:
            print(f"Error replying to tweet: {e}")
            return False 