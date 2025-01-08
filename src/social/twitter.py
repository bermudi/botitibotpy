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
        # Set required headers for API compatibility
        self.client.additional_api_headers = {
            "sec-ch-ua-platform": '"Linux"',
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br"
        }
        self.client.additional_browser_headers = {
            "sec-ch-ua-platform": '"Linux"',
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br"
        }
        self.cookies_path = Path("twitter_cookie.json")
        self._auth_status = False
        self._api = None
        self.setup_auth()
    
    @property
    def is_authenticated(self) -> bool:
        """Check if client is authenticated"""
        return self._auth_status
        
    @property
    def api(self):
        """Get the Twitter API client"""
        if not self._api:
            # First get the guest token
            guest_client = self.client.get_guest_client()
            # Then get the authenticated client
            if self.client.additional_cookies:
                self._api = self.client.get_client_from_cookies(self.client.additional_cookies)
            else:
                self._api = guest_client
        return self._api
    
    def setup_auth(self) -> bool:
        """Set up authentication using saved cookies or create new ones."""
        logger.debug("Setting up Twitter authentication")
        
        if self.cookies_path.exists():
            try:
                cookies = self._load_existing_cookies(self.cookies_path)
                if self._validate_cookies(cookies):
                    logger.info("Successfully loaded existing cookies")
                    self.client.additional_cookies = cookies
                    self._auth_status = True
                    # Initialize API client with cookies
                    self._api = self.client.get_client_from_cookies(cookies)
                    return True
                else:
                    logger.warning("Invalid cookies found, creating new ones")
            except Exception as e:
                logger.error(f"Error loading cookies: {str(e)}")
        
        try:
            cookies = self._create_new_cookies(self.cookies_path)
            if cookies and self._validate_cookies(cookies):
                logger.info("Successfully created new cookies")
                self.client.additional_cookies = cookies
                self._auth_status = True
                # Initialize API client with cookies
                self._api = self.client.get_client_from_cookies(cookies)
                return True
            else:
                logger.error("Failed to create valid cookies")
                self._auth_status = False
                return False
        except Exception as e:
            logger.error(f"Error creating new cookies: {str(e)}")
            self._auth_status = False
            return False
            
    @retry_on_failure()
    async def get_timeline(self, limit: int = 20) -> Optional[Any]:
        """Fetch user's timeline"""
        try:
            timeline = self.api.get_tweet_api().get_home_timeline(count=limit)
            logger.debug(f"Timeline response type: {type(timeline)}")
            logger.debug(f"Timeline raw type: {type(timeline.raw)}")
            logger.debug(f"Timeline raw dir: {dir(timeline.raw)}")
            
            # Extract relevant data from timeline response
            tweets = []
            for tweet_data in timeline.data:
                if hasattr(tweet_data, 'tweet') and hasattr(tweet_data, 'user'):
                    tweet = tweet_data.tweet
                    user = tweet_data.user
                    tweets.append({
                        'content': tweet.legacy.full_text if hasattr(tweet.legacy, 'full_text') else tweet.legacy.text,
                        'created_at': tweet.legacy.created_at,
                        'author': user.legacy.screen_name,
                        'engagement_metrics': {
                            'likes': tweet.legacy.favorite_count,
                            'retweets': tweet.legacy.retweet_count,
                            'replies': tweet.legacy.reply_count,
                            'views': tweet.views.count if hasattr(tweet, 'views') else 0
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
            # Get tweet details with replies
            response = self.api.get_tweet_api().get_tweet_detail(
                focal_tweet_id=tweet_id,
                extra_param={
                    "includeReplies": True,
                    "withCommunity": True
                }
            )
            
            logger.debug(f"Raw thread response: {response.raw}")
            
            # Extract relevant data from thread response
            comments = []
            if hasattr(response, 'data'):
                # Convert instructions to entries
                entries = response.data.threaded_conversation_with_injections_v2.instructions
                logger.debug(f"Found {len(entries)} instruction sets")
                
                for instruction in entries:
                    if hasattr(instruction, 'entries'):
                        for entry in instruction.entries:
                            if hasattr(entry, 'content'):
                                # Handle timeline entries
                                if hasattr(entry.content, 'items'):
                                    # Multiple items in content
                                    for item in entry.content.items:
                                        if (hasattr(item, 'item') and 
                                            hasattr(item.item, 'itemContent') and 
                                            hasattr(item.item.itemContent, 'tweet_results')):
                                            tweet = item.item.itemContent.tweet_results.result
                                            if (hasattr(tweet, 'legacy') and 
                                                hasattr(tweet.legacy, 'in_reply_to_status_id_str') and
                                                tweet.legacy.in_reply_to_status_id_str == tweet_id):
                                                user = tweet.core.user_results.result
                                                logger.debug(f"Found reply from user: {user.legacy.screen_name}")
                                                comments.append({
                                                    'id': tweet.rest_id,
                                                    'author': user.legacy.screen_name,
                                                    'content': tweet.legacy.full_text if hasattr(tweet.legacy, 'full_text') else tweet.legacy.text,
                                                    'created_at': tweet.legacy.created_at
                                                })
                                # Handle conversation entries
                                elif (hasattr(entry.content, 'itemContent') and 
                                      hasattr(entry.content.itemContent, 'tweet_results')):
                                    tweet = entry.content.itemContent.tweet_results.result
                                    if (hasattr(tweet, 'legacy') and 
                                        hasattr(tweet.legacy, 'in_reply_to_status_id_str') and
                                        tweet.legacy.in_reply_to_status_id_str == tweet_id):
                                        user = tweet.core.user_results.result
                                        logger.debug(f"Found reply from user: {user.legacy.screen_name}")
                                        comments.append({
                                            'id': tweet.rest_id,
                                            'author': user.legacy.screen_name,
                                            'content': tweet.legacy.full_text if hasattr(tweet.legacy, 'full_text') else tweet.legacy.text,
                                            'created_at': tweet.legacy.created_at
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
            self.api.get_post_api().post_favorite_tweet(tweet_id=tweet_id)
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
            self.api.get_post_api().post_create_tweet(
                tweet_text=text,
                in_reply_to_tweet_id=tweet_id
            )
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
            
            # Get user info to get the user ID
            user_info = self.api.get_user_api().get_user_by_screen_name(screen_name=screen_name)
            user_id = user_info.data.user.rest_id
            
            # Get user tweets with correct parameters
            tweets_response = self.api.get_tweet_api().get_user_tweets(
                user_id=user_id,
                extra_param={"includeReplies": False, "includeRetweets": True}
            )
            
            logger.debug(f"Tweets response type: {type(tweets_response)}")
            logger.debug(f"Tweets response raw type: {type(tweets_response.raw)}")
            logger.debug(f"Tweets response raw dir: {dir(tweets_response.raw)}")
            logger.debug(f"Tweets response raw: {tweets_response.raw}")
            
            # Extract relevant data from tweets response
            tweets = []
            for tweet_data in tweets_response.data:
                if hasattr(tweet_data, 'result'):
                    tweet_result = tweet_data.result
                    user_result = tweet_result.core.user_results.result
                    
                    tweets.append({
                        'content': tweet_result.legacy.full_text if hasattr(tweet_result.legacy, 'full_text') else tweet_result.legacy.text,
                        'created_at': tweet_result.legacy.created_at,
                        'author': user_result.legacy.screen_name,
                        'engagement_metrics': {
                            'likes': tweet_result.legacy.favorite_count,
                            'retweets': tweet_result.legacy.retweet_count,
                            'replies': tweet_result.legacy.reply_count,
                            'views': tweet_result.views.count if hasattr(tweet_result, 'views') else 0
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
            
            if not cookies_dict:
                raise ValueError("Failed to obtain cookies from auth handler")
                
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

            # Create tweet with correct method and parameters
            self.api.get_post_api().post_create_tweet(tweet_text=content)
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
            tweet = self.api.get_post_api().post_create_tweet(tweet_text=content)
            if tweet and hasattr(tweet, 'data') and hasattr(tweet.data, 'tweet_results'):
                tweet_data = tweet.data.tweet_results.result
                return {
                    'id': tweet_data.rest_id,
                    'text': tweet_data.legacy.full_text
                }
            return None
        except Exception as e:
            logger.error(f"Error posting tweet: {e}", exc_info=True)
            raise

    @retry_on_failure()
    async def get_tweet_metrics(self, tweet_id: str) -> Optional[Dict[str, int]]:
        """Get engagement metrics for a tweet"""
        try:
            tweet = self.api.get_tweet_api().get_tweet_detail(focal_tweet_id=tweet_id)
            if tweet and hasattr(tweet, 'data'):
                # Extract metrics from the tweet data
                tweet_data = tweet.data
                if hasattr(tweet_data, 'tweet_results'):
                    result = tweet_data.tweet_results.result
                    return {
                        'likes': result.legacy.favorite_count,
                        'replies': result.legacy.reply_count,
                        'reposts': result.legacy.retweet_count,
                        'views': result.views.count if hasattr(result, 'views') else 0
                    }
            return None
        except Exception as e:
            logger.error(f"Error getting tweet metrics: {e}", exc_info=True)
            return None
