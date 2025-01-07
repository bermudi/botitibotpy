from twitter_openapi_python import TwitterOpenapiPython
from tweepy_authlib import CookieSessionUserHandler
import json
import logging
from pathlib import Path
from typing import Optional, Any, Dict
import time
from functools import wraps
from ..config import Config

# Configure logger
logger = logging.getLogger("botitibot.social.twitter")

def retry_on_failure(max_retries: int = 3, delay: int = 1):
    """Decorator to retry failed API calls"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed after {max_retries} attempts", exc_info=True, extra={
                            'context': {
                                'function': func.__name__,
                                'max_retries': max_retries,
                                'error': str(e),
                                'component': 'twitter.retry'
                            }
                        })
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed. Retrying...", extra={
                        'context': {
                            'function': func.__name__,
                            'attempt': attempt + 1,
                            'error': str(e),
                            'component': 'twitter.retry'
                        }
                    })
                    time.sleep(delay * (attempt + 1))  # Exponential backoff
            return None
        return wrapper
    return decorator

class TwitterClient:
    def __init__(self, log_level: int = logging.INFO):
        """Initialize Twitter client with custom logging level"""
        logger.setLevel(log_level)
        logger.info("Initializing Twitter client", extra={
            'context': {
                'log_level': log_level,
                'component': 'twitter.client'
            }
        })
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
        cookie_path = Path("twitter_cookie.json")
        try:
            if cookie_path.exists():
                cookies_dict = self._load_existing_cookies(cookie_path)
                if cookies_dict:
                    logger.info("Successfully loaded existing cookies", extra={
                        'context': {
                            'cookie_path': str(cookie_path),
                            'component': 'twitter.auth'
                        }
                    })
                    return True
            
            logger.info("Creating new authentication cookies", extra={
                'context': {
                    'cookie_path': str(cookie_path),
                    'component': 'twitter.auth'
                }
            })
            return self._create_new_cookies(cookie_path)
            
        except Exception as e:
            logger.error("Failed to set up authentication", exc_info=True, extra={
                'context': {
                    'error': str(e),
                    'component': 'twitter.auth'
                }
            })
            return False
            
    def _load_existing_cookies(self, cookie_path: Path) -> Dict:
        """Load existing cookies from file"""
        logger.debug("Loading existing cookies", extra={
            'context': {
                'cookie_path': str(cookie_path),
                'component': 'twitter.auth'
            }
        })
        with open(cookie_path, "r") as f:
            cookies_dict = json.load(f)
            return {k["name"]: k["value"] for k in cookies_dict} if isinstance(cookies_dict, list) else cookies_dict
            
    @retry_on_failure(max_retries=3, delay=2)
    def _create_new_cookies(self, cookie_path: Path) -> Dict:
        """Create and save new cookies with retry mechanism"""
        logger.debug("Creating new cookies", extra={
            'context': {
                'cookie_path': str(cookie_path),
                'component': 'twitter.auth'
            }
        })
        if not Config.TWITTER_USERNAME or not Config.TWITTER_PASSWORD:
            raise ValueError("Twitter credentials not found in config")
            
        try:
            auth_handler = CookieSessionUserHandler(
                screen_name=Config.TWITTER_USERNAME,
                password=Config.TWITTER_PASSWORD
            )
            logger.debug("Created auth handler, attempting to get cookies", extra={
                'context': {
                    'username': Config.TWITTER_USERNAME,
                    'component': 'twitter.auth'
                }
            })
            cookies_dict = auth_handler.get_cookies().get_dict()
            logger.debug("Successfully obtained cookies", extra={
                'context': {
                    'cookie_path': str(cookie_path),
                    'component': 'twitter.auth'
                }
            })
            
            with open(cookie_path, "w") as f:
                json.dump(cookies_dict, f, ensure_ascii=False, indent=4)
            logger.info("Successfully saved new cookies to file", extra={
                'context': {
                    'cookie_path': str(cookie_path),
                    'component': 'twitter.auth'
                }
            })
            return cookies_dict
            
        except Exception as e:
            logger.error(f"Failed to create new cookies: {e}", exc_info=True, extra={
                'context': {
                    'error': str(e),
                    'component': 'twitter.auth'
                }
            })
            raise
        
    def _validate_cookies(self, cookies_dict: Dict) -> None:
        """Validate cookie structure and contents"""
        required_keys = ['auth_token', 'ct0']  # Add required Twitter cookie keys
        missing = [key for key in required_keys if key not in cookies_dict]
        if missing:
            raise ValueError(f"Invalid cookie structure. Missing keys: {', '.join(missing)}")
    
    @retry_on_failure()
    def post_content(self, content: str) -> bool:
        """Post content to Twitter"""
        try:
            self.client.get_post_api().post_create_tweet(tweet_text=content)
            logger.info("Successfully posted content to Twitter", extra={
                'context': {
                    'content': content,
                    'component': 'twitter.post'
                }
            })
            return True
        except Exception as e:
            logger.error(f"Error posting to Twitter: {e}", exc_info=True, extra={
                'context': {
                    'error': str(e),
                    'component': 'twitter.post'
                }
            })
            raise
            
    @retry_on_failure()
    def get_timeline(self, limit: int = 20) -> Optional[Any]:
        """Fetch user's timeline"""
        try:
            user_api = self.client.get_user_api()
            timeline = user_api.get_home_timeline(count=limit)
            logger.info(f"Successfully fetched {limit} timeline items", extra={
                'context': {
                    'limit': limit,
                    'component': 'twitter.timeline'
                }
            })
            return timeline
        except Exception as e:
            logger.error(f"Error fetching timeline: {e}", exc_info=True, extra={
                'context': {
                    'error': str(e),
                    'component': 'twitter.timeline'
                }
            })
            raise
            
    @retry_on_failure()
    def get_tweet_thread(self, tweet_id: str) -> Optional[Any]:
        """Fetch a tweet and its replies"""
        try:
            tweet_api = self.client.get_tweet_api()
            thread = tweet_api.get_tweet_detail(tweet_id)
            logger.info(f"Successfully fetched thread for tweet {tweet_id}", extra={
                'context': {
                    'tweet_id': tweet_id,
                    'component': 'twitter.thread'
                }
            })
            return thread
        except Exception as e:
            logger.error(f"Error fetching tweet thread: {e}", exc_info=True, extra={
                'context': {
                    'error': str(e),
                    'component': 'twitter.thread'
                }
            })
            raise
            
    @retry_on_failure()
    def like_tweet(self, tweet_id: str) -> bool:
        """Like a tweet"""
        try:
            tweet_api = self.client.get_tweet_api()
            tweet_api.favorite_tweet(tweet_id)
            logger.info(f"Successfully liked tweet {tweet_id}", extra={
                'context': {
                    'tweet_id': tweet_id,
                    'component': 'twitter.like'
                }
            })
            return True
        except Exception as e:
            logger.error(f"Error liking tweet: {e}", exc_info=True, extra={
                'context': {
                    'error': str(e),
                    'component': 'twitter.like'
                }
            })
            raise
            
    @retry_on_failure()
    def reply_to_tweet(self, tweet_id: str, text: str) -> bool:
        """Reply to a tweet"""
        try:
            post_api = self.client.get_post_api()
            post_api.post_create_tweet(tweet_text=text, reply_tweet_id=tweet_id)
            logger.info(f"Successfully replied to tweet {tweet_id}", extra={
                'context': {
                    'tweet_id': tweet_id,
                    'text': text,
                    'component': 'twitter.reply'
                }
            })
            return True
        except Exception as e:
            logger.error(f"Error replying to tweet: {e}", exc_info=True, extra={
                'context': {
                    'error': str(e),
                    'component': 'twitter.reply'
                }
            })
            raise

    @retry_on_failure()
    def get_author_feed(self, screen_name: Optional[str] = None) -> Optional[Any]:
        """Fetch tweets from a specific author. If no screen_name is provided, fetches tweets from the authenticated user."""
        try:
            user_api = self.client.get_user_api()
            
            # If no screen_name provided, get the authenticated user's screen name
            if screen_name is None:
                user_info = user_api.get_user_by_screen_name(Config.TWITTER_USERNAME)
                screen_name = user_info.data.user.legacy.screen_name
            
            # Get user info to get the user ID
            user_info = user_api.get_user_by_screen_name(screen_name)
            user_id = user_info.data.user.rest_id
            
            # Get user tweets using the tweet API
            tweet_api = self.client.get_tweet_api()
            tweets = tweet_api.get_user_tweets(user_id)
            logger.info(f"Successfully fetched tweets for user {screen_name}", extra={
                'context': {
                    'screen_name': screen_name,
                    'component': 'twitter.feed'
                }
            })
            return tweets
        except Exception as e:
            logger.error(f"Error fetching author feed: {e}", exc_info=True, extra={
                'context': {
                    'error': str(e),
                    'component': 'twitter.feed'
                }
            })
            raise
