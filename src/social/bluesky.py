import json
import time
import logging
from atproto import Client, client_utils
from atproto_client.exceptions import RequestException, LoginRequiredError
from typing import Optional, Any, Dict, Callable
from ..config import Config
from atproto_client.models.app.bsky.feed.get_author_feed import Params as AuthorFeedParams
from pathlib import Path
from functools import wraps

logger = logging.getLogger("botitibot.social.bluesky")

class SimpleRateLimiter:
    def __init__(self):
        # Simplified rate limits with just a few buckets
        self.limits = {
            "auth": {
                "limit": 100,      # auth operations per day
                "reset_time": 0,   
                "remaining": 100,
                "window": 86400,   # 24 hours
                "min_remaining": 5  # Keep some auth operations in reserve
            },
            "write": {
                "limit": 5000,     # write operations per day
                "reset_time": 0,
                "remaining": 5000,
                "window": 86400,   # 24 hours
                "min_remaining": 50 # Keep some write operations in reserve
            },
            "read": {
                "limit": 50000,    # read operations per day
                "reset_time": 0,
                "remaining": 50000,
                "window": 86400,   # 24 hours
                "min_remaining": 100 # Keep some read operations in reserve
            }
        }
        self.backoff_times = {
            "auth": 300,    # 5 minutes
            "write": 600,   # 10 minutes
            "read": 300     # 5 minutes
        }

    def update_from_headers(self, headers, op_type: str):
        """Update limits from server response headers"""
        if op_type not in self.limits:
            op_type = "read"
        
        info = self.limits[op_type]
        
        # Update from headers if available
        if 'ratelimit-limit' in headers:
            info['limit'] = int(headers['ratelimit-limit'])
        if 'ratelimit-remaining' in headers:
            info['remaining'] = int(headers['ratelimit-remaining'])
        if 'ratelimit-reset' in headers:
            info['reset_time'] = int(headers['ratelimit-reset'])
        if 'ratelimit-policy' in headers:
            try:
                policy = headers['ratelimit-policy']
                limit, window = policy.split(';w=')
                info['window'] = int(window)
            except (ValueError, KeyError):
                pass

    def can_make_request(self, op_type: str) -> bool:
        if op_type not in self.limits:
            op_type = "read"
        info = self.limits[op_type]
        now = int(time.time())
        
        # Reset counters if past reset time
        if now >= info['reset_time']:
            info['remaining'] = info['limit']
            info['reset_time'] = now + info['window']
            
        # Allow request if we have more than min_remaining
        return info['remaining'] > info['min_remaining']

    def decrement(self, op_type: str):
        if op_type not in self.limits:
            op_type = "read"
        info = self.limits[op_type]
        if info['remaining'] > 0:
            info['remaining'] -= 1

    def get_backoff_time(self, op_type: str) -> int:
        """Return a reasonable backoff time when rate limited"""
        if op_type not in self.limits:
            op_type = "read"
            
        info = self.limits[op_type]
        now = int(time.time())
        
        # If we're close to reset time, wait for reset
        if info['reset_time'] - now < self.backoff_times[op_type]:
            return max(1, info['reset_time'] - now)
            
        # Otherwise use the standard backoff time
        return self.backoff_times[op_type]

# Global rate limiter instance
rate_limiter = SimpleRateLimiter()

def handle_rate_limit(operation_type: str) -> Callable:
    """
    Decorator that handles both local rate limiting and remote rate limit responses.
    Uses a more graceful approach for a continuously running bot:
    - Keeps some operations in reserve for critical tasks
    - Uses shorter backoff times instead of waiting for full reset
    - Fails fast with RateLimitError instead of blocking
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            max_retries = 3
            base_delay = 1
            
            # Check if we can make the request
            if not rate_limiter.can_make_request(operation_type):
                backoff = rate_limiter.get_backoff_time(operation_type)
                logger.warning(f"Rate limit reached for {operation_type}, suggesting backoff of {backoff}s", extra={
                    'context': {
                        'operation_type': operation_type,
                        'backoff': backoff,
                        'component': 'bluesky.rate_limit'
                    }
                })
                # Raise custom exception so caller can handle it
                raise RateLimitError(f"Rate limit reached for {operation_type}", 
                                   operation_type=operation_type,
                                   backoff=backoff)
            
            # Decrement our local counter
            rate_limiter.decrement(operation_type)
            
            for attempt in range(max_retries):
                try:
                    result = func(*args, **kwargs)
                    return result
                    
                except RequestException as e:
                    # Get response if available
                    response = getattr(e, 'response', None)
                    if response and response.status_code == 429:
                        # Update our rate limiter from the response headers
                        rate_limiter.update_from_headers(response.headers, operation_type)
                        
                        # Get backoff time
                        backoff = rate_limiter.get_backoff_time(operation_type)
                        
                        logger.warning(f"Remote rate limit hit for {operation_type}, suggesting backoff of {backoff}s", extra={
                            'context': {
                                'operation_type': operation_type,
                                'backoff': backoff,
                                'attempt': attempt + 1,
                                'component': 'bluesky.rate_limit'
                            }
                        })
                        # Let caller handle the backoff
                        raise RateLimitError(f"Remote rate limit hit for {operation_type}",
                                           operation_type=operation_type,
                                           backoff=backoff)
                    
                    # For non-rate-limit errors, use exponential backoff
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Request failed, retrying in {delay}s", extra={
                            'context': {
                                'error': str(e),
                                'attempt': attempt + 1,
                                'delay': delay,
                                'component': 'bluesky.retry'
                            }
                        })
                        time.sleep(delay)
                        continue
                    
                    logger.error(f"Error in {func.__name__} after {max_retries} attempts", extra={
                        'context': {
                            'error': str(e),
                            'component': 'bluesky.error'
                        }
                    })
                    raise
                
                except Exception as e:
                    # For other exceptions, use exponential backoff
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Operation failed, retrying in {delay}s", extra={
                            'context': {
                                'error': str(e),
                                'attempt': attempt + 1,
                                'delay': delay,
                                'component': 'bluesky.retry'
                            }
                        })
                        time.sleep(delay)
                        continue
                    
                    logger.error(f"Error in {func.__name__} after {max_retries} attempts", extra={
                        'context': {
                            'error': str(e),
                            'component': 'bluesky.error'
                        }
                    })
                    raise
            
            raise RuntimeError(f"Gave up after {max_retries} retries in {func.__name__}")
        return wrapper
    return decorator

class RateLimitError(Exception):
    """Custom exception for rate limit errors that includes backoff information"""
    def __init__(self, message: str, operation_type: str, backoff: int):
        super().__init__(message)
        self.operation_type = operation_type
        self.backoff = backoff

class BlueskyClient:
    def __init__(self):
        logger.info("Initializing Bluesky client", extra={
            'context': {
                'component': 'bluesky.client'
            }
        })
        self.client = None
        self.profile = None
        
        # Create data directory if it doesn't exist
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        self.session_file = self.data_dir / "bluesky_session.json"
        
        # Ensure session file is readable/writable only by owner
        if self.session_file.exists():
            self.session_file.chmod(0o600)
            
    def __enter__(self):
        if not self.client:
            logger.debug("Creating new Bluesky client", extra={
                'context': {
                    'component': 'bluesky.client'
                }
            })
            self.client = Client()
            self.setup_auth()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.debug("Cleaning up Bluesky client resources", extra={
            'context': {
                'component': 'bluesky.client'
            }
        })
        if hasattr(self.client, 'close'):
            self.client.close()
        elif hasattr(self.client, '_session') and hasattr(self.client._session, 'close'):
            self.client._session.close()
    
    def _load_session(self) -> Optional[Dict]:
        try:
            if self.session_file.exists():
                with open(self.session_file, 'r') as f:
                    session = json.load(f)
                    logger.debug("Loaded existing session", extra={
                        'context': {
                            'component': 'bluesky.auth'
                        }
                    })
                    return session
        except Exception as e:
            logger.error(f"Error loading session: {str(e)}", extra={
                'context': {
                    'error': str(e),
                    'component': 'bluesky.auth'
                }
            })
        return None
    
    def _save_session(self, session: Dict) -> None:
        try:
            self.session_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.session_file, 'w') as f:
                json.dump(session, f)
            self.session_file.chmod(0o600)
            logger.debug("Saved session data", extra={
                'context': {
                    'session_file': str(self.session_file),
                    'component': 'bluesky.auth'
                }
            })
        except Exception as e:
            logger.error(f"Error saving session: {str(e)}", extra={
                'context': {
                    'error': str(e),
                    'component': 'bluesky.auth'
                }
            })
    
    def _cleanup_session(self) -> None:
        try:
            if self.session_file.exists():
                self.session_file.unlink()
                logger.debug("Removed invalid session file", extra={
                    'context': {
                        'component': 'bluesky.auth'
                    }
                })
        except Exception as e:
            logger.error(f"Error cleaning up session: {str(e)}", extra={
                'context': {
                    'error': str(e),
                    'component': 'bluesky.auth'
                }
            })
    
    @handle_rate_limit("auth")
    def setup_auth(self) -> bool:
        """Authenticate with Bluesky using credentials from config"""
        try:
            # Try to load existing session
            session = self._load_session()
            if session:
                try:
                    self.client = Client()
                    self.client.session = session
                    # Verify session is still valid
                    self.profile = self.client.get_profile()
                    logger.info(f"Successfully restored session for: {self.profile.display_name}", extra={
                        'context': {
                            'display_name': self.profile.display_name,
                            'component': 'bluesky.auth'
                        }
                    })
                    return True
                except Exception as e:
                    logger.warning(f"Saved session invalid: {str(e)}", extra={
                        'context': {
                            'error': str(e),
                            'component': 'bluesky.auth'
                        }
                    })
                    self._cleanup_session()
            
            # Create new session
            logger.debug("Creating new session", extra={
                'context': {
                    'identifier': Config.BLUESKY_IDENTIFIER,
                    'component': 'bluesky.auth'
                }
            })
            
            max_retries = 3
            base_delay = 1
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    self.client = Client()
                    self.profile = self.client.login(
                        Config.BLUESKY_IDENTIFIER,
                        Config.BLUESKY_PASSWORD
                    )
                    
                    # Save new session
                    self._save_session(self.client.session)
                    
                    logger.info(f"Successfully logged in as: {self.profile.display_name}", extra={
                        'context': {
                            'display_name': self.profile.display_name,
                            'component': 'bluesky.auth'
                        }
                    })
                    return True
                    
                except RequestException as e:
                    last_error = e
                    response = getattr(e, 'response', None)
                    if response and response.status_code == 429:
                        # Get rate limit info
                        reset_time = int(response.headers.get('ratelimit-reset', 0))
                        current_time = int(time.time())
                        wait_time = max(30, reset_time - current_time)
                        
                        if attempt < max_retries - 1:
                            logger.warning(f"Rate limit hit during auth, waiting {wait_time}s", extra={
                                'context': {
                                    'wait_time': wait_time,
                                    'attempt': attempt + 1,
                                    'reset_time': reset_time,
                                    'component': 'bluesky.auth'
                                }
                            })
                            time.sleep(wait_time)
                            continue
                    
                    # For non-rate-limit errors, use exponential backoff
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Auth request failed, retrying in {delay}s", extra={
                            'context': {
                                'error': str(e),
                                'attempt': attempt + 1,
                                'delay': delay,
                                'component': 'bluesky.auth'
                            }
                        })
                        time.sleep(delay)
                        continue
            
            if last_error:
                logger.error("Error authenticating with Bluesky", exc_info=True, extra={
                    'context': {
                        'error': str(last_error),
                        'component': 'bluesky.auth'
                    }
                })
            self._cleanup_session()
            return False
            
        except Exception as e:
            logger.error("Error authenticating with Bluesky", exc_info=True, extra={
                'context': {
                    'error': str(e),
                    'component': 'bluesky.auth'
                }
            })
            self._cleanup_session()
            return False
    
    @handle_rate_limit("write")
    def post_content(self, content: str, link: Optional[str] = None) -> Optional[Any]:
        try:
            logger.debug("Creating post content", extra={
                'context': {
                    'content_length': len(content),
                    'has_link': bool(link),
                    'component': 'bluesky.post'
                }
            })
            text = client_utils.TextBuilder()
            text.text(content)
            
            if link:
                text.link("🔗", link)
                
            post = self.client.send_post(text)
            logger.info("Successfully posted content to Bluesky", extra={
                'context': {
                    'post_uri': getattr(post, 'uri', None),
                    'component': 'bluesky.post'
                }
            })
            return post
        except Exception as e:
            logger.error("Error posting to Bluesky", exc_info=True, extra={
                'context': {
                    'error': str(e),
                    'component': 'bluesky.post'
                }
            })
            return None
            
    @handle_rate_limit("read")
    def get_timeline(self, limit: int = 20) -> Optional[Any]:
        try:
            logger.debug("Fetching timeline", extra={
                'context': {
                    'limit': limit,
                    'component': 'bluesky.timeline'
                }
            })
            timeline = self.client.get_timeline(limit=limit)
            logger.info(f"Successfully fetched {limit} timeline items", extra={
                'context': {
                    'limit': limit,
                    'component': 'bluesky.timeline'
                }
            })
            return timeline
        except Exception as e:
            logger.error("Error fetching timeline", exc_info=True, extra={
                'context': {
                    'error': str(e),
                    'component': 'bluesky.timeline'
                }
            })
            return None
            
    @handle_rate_limit("read")
    def get_author_feed(self, actor: Optional[str] = None, limit: int = 20) -> Any:
        try:
            if actor is None:
                actor = self.profile.did
                
            logger.debug("Fetching author feed", extra={
                'context': {
                    'actor': actor,
                    'limit': limit,
                    'component': 'bluesky.feed'
                }
            })
            
            params = AuthorFeedParams(actor=actor, limit=limit)
            feed = self.client.get_author_feed(params=params)
            
            logger.info(f"Successfully fetched feed for {actor}", extra={
                'context': {
                    'actor': actor,
                    'limit': limit,
                    'component': 'bluesky.feed'
                }
            })
            return feed
        except Exception as e:
            logger.error("Error fetching author feed", exc_info=True, extra={
                'context': {
                    'actor': actor,
                    'limit': limit,
                    'error': str(e),
                    'component': 'bluesky.feed'
                }
            })
            return None

    @handle_rate_limit("read")
    def get_post_thread(self, uri: str) -> Any:
        try:
            logger.debug("Fetching post thread", extra={
                'context': {
                    'uri': uri,
                    'component': 'bluesky.thread'
                }
            })
            
            thread = self.client.get_post_thread(uri)
            
            logger.info("Successfully fetched thread", extra={
                'context': {
                    'uri': uri,
                    'component': 'bluesky.thread'
                }
            })
            return thread
        except Exception as e:
            logger.error("Error fetching post thread", exc_info=True, extra={
                'context': {
                    'uri': uri,
                    'error': str(e),
                    'component': 'bluesky.thread'
                }
            })
            return None

    @handle_rate_limit("write")
    def like_post(self, uri: str, cid: Optional[str] = None) -> bool:
        try:
            logger.debug("Liking post", extra={
                'context': {
                    'uri': uri,
                    'cid': cid,
                    'component': 'bluesky.like'
                }
            })
            
            if cid is None:
                thread = self.get_post_thread(uri)
                if thread and hasattr(thread, 'thread') and hasattr(thread.thread, 'post'):
                    cid = thread.thread.post.cid
                else:
                    raise ValueError("Could not determine post CID")
            
            self.client.like(uri, cid)
            
            logger.info("Successfully liked post", extra={
                'context': {
                    'uri': uri,
                    'cid': cid,
                    'component': 'bluesky.like'
                }
            })
            return True
        except Exception as e:
            logger.error("Error liking post", exc_info=True, extra={
                'context': {
                    'uri': uri,
                    'cid': cid,
                    'error': str(e),
                    'component': 'bluesky.like'
                }
            })
            return False

    @handle_rate_limit("write")
    def reply_to_post(self, uri: str, text: str) -> Any:
        try:
            logger.debug("Replying to post", extra={
                'context': {
                    'uri': uri,
                    'text_length': len(text),
                    'component': 'bluesky.reply'
                }
            })
            
            response = self.client.send_post(text=text, reply_to=uri)
            
            logger.info("Successfully replied to post", extra={
                'context': {
                    'uri': uri,
                    'response_uri': response.uri if response else None,
                    'component': 'bluesky.reply'
                }
            })
            return response
        except Exception as e:
            logger.error("Error replying to post", exc_info=True, extra={
                'context': {
                    'uri': uri,
                    'error': str(e),
                    'component': 'bluesky.reply'
                }
            })
            return None