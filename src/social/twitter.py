from twikit import Client
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
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
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
        self.client = Client()
        self.cookies_path = Path("twitter_cookie.json")
        self._auth_status = False
        
    @property
    def is_authenticated(self) -> bool:
        """Check if client is authenticated"""
        return self._auth_status
    
    async def setup_auth(self) -> bool:
        """Set up authentication using saved cookies or create new ones."""
        logger.debug("Setting up Twitter authentication")
        
        if self.cookies_path.exists():
            try:
                cookies = self._load_existing_cookies(self.cookies_path)
                if self._validate_cookies(cookies):
                    logger.info("Successfully loaded existing cookies")
                    # Set cookies directly on the client
                    self.client.set_cookies(cookies)
                    # Verify the cookies work by getting the user ID
                    try:
                        user_id = self.client.user_id()
                        if user_id:
                            # Unlock the client for write operations
                            self.client.unlock()
                            self._auth_status = True
                            return True
                    except Exception as e:
                        logger.warning(f"Existing cookies are invalid: {str(e)}")
                else:
                    logger.warning("Invalid cookies found, creating new ones")
            except Exception as e:
                logger.error(f"Error loading cookies: {str(e)}")
        
        try:
            if not Config.TWITTER_USERNAME or not Config.TWITTER_PASSWORD:
                raise ValueError("Twitter credentials not found in config")
            
            # Create a new client and login
            self.client = Client()
            
            # First get a guest token
            self.client.get_guest_token()
            
            # Perform login with required arguments
            self.client.login(
                auth_info_1=Config.TWITTER_USERNAME,
                password=Config.TWITTER_PASSWORD
            )
            
            # Verify login was successful
            user_id = self.client.user_id()
            if not user_id:
                raise ValueError("Login failed - could not get user ID")
                
            # Unlock the client for write operations
            self.client.unlock()
            
            # Save the cookies for future use
            cookies = self.client.get_cookies()
            with open(self.cookies_path, "w") as f:
                json.dump(cookies, f, ensure_ascii=False, indent=4)
            
            logger.info("Successfully created and saved new cookies")
            self._auth_status = True
            return True
            
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            self._auth_status = False
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
            return json.load(f)
            
    def _validate_cookies(self, cookies_dict: Dict) -> bool:
        """Validate cookie structure and contents"""
        try:
            required_keys = ['auth_token', 'ct0']
            missing = [key for key in required_keys if key not in cookies_dict]
            
            if missing:
                logger.error(f"Invalid cookie structure. Missing keys: {', '.join(missing)}")
                return False
                
            # Check if cookies are not empty
            for key in required_keys:
                if not cookies_dict[key]:
                    logger.error(f"Empty value for required cookie: {key}")
                    return False
                    
            return True
        except Exception as e:
            logger.error(f"Error validating cookies: {str(e)}")
            return False
    
    @retry_on_failure()
    async def get_timeline(self, limit: int = 20) -> Optional[Any]:
        """Fetch user's timeline"""
        try:
            timeline = await self.client.get_timeline(count=limit)
            tweets = []
            for tweet in timeline:
                tweets.append({
                    'content': tweet.text,
                    'created_at': tweet.created_at,
                    'author': tweet.user.screen_name,
                    'engagement_metrics': {
                        'likes': tweet.favorite_count,
                        'retweets': tweet.retweet_count,
                        'replies': tweet.reply_count,
                        'views': getattr(tweet, 'view_count', 0)
                    }
                })
            
            logger.info(f"Successfully fetched {len(tweets)} timeline items", extra={
                'context': {
                    'limit': limit,
                    'component': 'twitter.timeline'
                }
            })
            return tweets
        except Exception as e:
            logger.error(f"Error fetching timeline: {e}", exc_info=True, extra={
                'context': {
                    'error': str(e),
                    'component': 'twitter.timeline'
                }
            })
            raise
            
    @retry_on_failure()
    async def get_tweet_thread(self, tweet_id: str) -> Optional[Any]:
        """Fetch a tweet and its replies"""
        try:
            tweet = await self.client.get_tweet_by_id(tweet_id)
            if not tweet:
                logger.error("Tweet not found")
                return []
                
            # Get replies to the tweet
            replies = await self.client.search_tweet(f"conversation_id:{tweet_id}")
            
            comments = []
            for reply in replies:
                comments.append({
                    'id': reply.id,
                    'author': reply.user.screen_name,
                    'content': reply.text,
                    'created_at': reply.created_at
                })
            
            logger.info(f"Successfully fetched thread for tweet {tweet_id} with {len(comments)} replies", extra={
                'context': {
                    'tweet_id': tweet_id,
                    'reply_count': len(comments),
                    'component': 'twitter.thread'
                }
            })
            return comments
            
        except Exception as e:
            logger.error(f"Error fetching tweet thread: {e}", exc_info=True)
            raise
            
    @retry_on_failure()
    async def like_tweet(self, tweet_id: str) -> None:
        """Like a tweet."""
        try:
            await self.client.favorite_tweet(tweet_id)
            logger.info(f"Successfully liked tweet {tweet_id}", extra={
                'context': {
                    'tweet_id': tweet_id,
                    'component': 'twitter.like'
                }
            })
        except Exception as e:
            logger.error(f"Error liking tweet: {e}", exc_info=True, extra={
                'context': {
                    'error': str(e),
                    'component': 'twitter.like'
                }
            })
            raise
            
    @retry_on_failure()
    async def reply_to_tweet(self, tweet_id: str, text: str) -> bool:
        """Reply to a tweet"""
        try:
            await self.client.create_tweet(text, in_reply_to_status_id=tweet_id)
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
    async def get_author_feed(self, screen_name: Optional[str] = None) -> Optional[Any]:
        """Fetch tweets from a specific author. If no screen_name is provided, fetches tweets from the authenticated user."""
        try:
            # If no screen_name provided, get the authenticated user's screen name
            if screen_name is None:
                screen_name = Config.TWITTER_USERNAME
            
            # Get user info
            user = await self.client.get_user_by_screen_name(screen_name)
            if not user:
                logger.error(f"User {screen_name} not found")
                return None
            
            # Get user tweets
            tweets_response = await self.client.get_user_tweets(user.id)
            
            tweets = []
            for tweet in tweets_response:
                tweets.append({
                    'content': tweet.text,
                    'created_at': tweet.created_at,
                    'author': tweet.user.screen_name,
                    'engagement_metrics': {
                        'likes': tweet.favorite_count,
                        'retweets': tweet.retweet_count,
                        'replies': tweet.reply_count,
                        'views': getattr(tweet, 'view_count', 0)
                    }
                })
            
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

    @retry_on_failure()
    async def post_content(self, content: str, use_rag: bool = False, **kwargs) -> bool:
        """Post content to Twitter with optional RAG support"""
        try:
            # Generate content if kwargs are provided
            if kwargs:
                from ..content.generator import ContentGenerator
                generator = ContentGenerator()
                
                if use_rag:
                    # Load content sources and index for RAG
                    if not generator.load_content_source("content_sources"):
                        logger.error("Failed to load content sources")
                        return False
                        
                    # Load the index
                    if not generator.load_index():
                        logger.error("Failed to load index")
                        return False
                    
                    # Generate content with RAG
                    content = generator.generate_post_withRAG(content, **kwargs)
                else:
                    # Generate content without RAG
                    content = generator.generate_post(content, **kwargs)
                
                if not content:
                    logger.error("Failed to generate content")
                    return False

            # Create tweet
            await self.client.create_tweet(content)
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
    async def post_tweet(self, content: str) -> Optional[Dict[str, Any]]:
        """Post a new tweet"""
        try:
            tweet = await self.client.create_tweet(content)
            if tweet:
                return {
                    'id': tweet.id,
                    'text': tweet.text
                }
            return None
        except Exception as e:
            logger.error(f"Error posting tweet: {e}", exc_info=True)
            raise

    @retry_on_failure()
    async def get_tweet_metrics(self, tweet_id: str) -> Optional[Dict[str, int]]:
        """Get engagement metrics for a tweet"""
        try:
            tweet = await self.client.get_tweet_by_id(tweet_id)
            if tweet:
                return {
                    'likes': tweet.favorite_count,
                    'replies': tweet.reply_count,
                    'reposts': tweet.retweet_count,
                    'views': getattr(tweet, 'view_count', 0)
                }
            return None
        except Exception as e:
            logger.error(f"Error getting tweet metrics: {e}", exc_info=True)
            return None
