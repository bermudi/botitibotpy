from atproto import Client, client_utils
from atproto_client.exceptions import RequestException, LoginRequiredError
from typing import Optional, Any, Dict
from ..config import Config
from atproto_client.models.app.bsky.feed.get_author_feed import Params as AuthorFeedParams
import logging
import time
import json
from pathlib import Path
from functools import wraps

logger = logging.getLogger("botitibot.social.bluesky")

def handle_rate_limit(func):
    """Decorator to handle rate limit errors"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        max_retries = 3
        base_delay = 1  # Base delay in seconds
        
        for attempt in range(max_retries):
            try:
                try:
                    return func(self, *args, **kwargs)
                except LoginRequiredError:
                    logger.warning("Login required, attempting to re-authenticate", extra={
                        'context': {
                            'attempt': attempt + 1,
                            'component': 'bluesky.auth'
                        }
                    })
                    if self.setup_auth():
                        continue
                    raise
            except RequestException as e:
                if hasattr(e, 'response') and e.response.status_code == 429:
                    headers = e.response.headers
                    reset_time = int(headers.get('ratelimit-reset', 0))
                    remaining = int(headers.get('ratelimit-remaining', 0))
                    limit = int(headers.get('ratelimit-limit', 100))
                    current_time = int(time.time())
                    wait_time = max(1, reset_time - current_time)  # At least 1 second
                    
                    if attempt < max_retries - 1:
                        logger.warning(f"Rate limit hit ({remaining}/{limit}), waiting {wait_time} seconds", extra={
                            'context': {
                                'wait_time': wait_time,
                                'attempt': attempt + 1,
                                'remaining': remaining,
                                'limit': limit,
                                'reset_time': reset_time,
                                'current_time': current_time,
                                'component': 'bluesky.rate_limit'
                            }
                        })
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Rate limit error after {max_retries} attempts", extra={
                            'context': {
                                'error': str(e),
                                'wait_time': wait_time,
                                'remaining': remaining,
                                'limit': limit,
                                'reset_time': reset_time,
                                'current_time': current_time,
                                'component': 'bluesky.rate_limit'
                            }
                        })
                elif attempt < max_retries - 1:
                    # For non-rate-limit errors, use exponential backoff
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Request failed, retrying in {delay} seconds", extra={
                        'context': {
                            'error': str(e),
                            'attempt': attempt + 1,
                            'delay': delay,
                            'component': 'bluesky.retry'
                        }
                    })
                    time.sleep(delay)
                    continue
                raise
            except Exception as e:
                if attempt < max_retries - 1:
                    # For other exceptions, also use exponential backoff
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Operation failed, retrying in {delay} seconds", extra={
                        'context': {
                            'error': str(e),
                            'attempt': attempt + 1,
                            'delay': delay,
                            'component': 'bluesky.retry'
                        }
                    })
                    time.sleep(delay)
                    continue
                logger.error(f"Error in {func.__name__}: {str(e)}", extra={
                    'context': {
                        'error': str(e),
                        'component': 'bluesky.error'
                    }
                })
                raise
    return wrapper

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
        """Clean up resources when exiting context"""
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
        """Load saved session data"""
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
        """Save session data"""
        try:
            # Create parent directory if it doesn't exist
            self.session_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write session data with secure permissions
            with open(self.session_file, 'w') as f:
                json.dump(session, f)
            self.session_file.chmod(0o600)  # Read/write for owner only
            
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
                    'session_file': str(self.session_file),
                    'component': 'bluesky.auth'
                }
            })
    
    def _cleanup_session(self) -> None:
        """Clean up invalid session data"""
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
    
    @handle_rate_limit
    def setup_auth(self) -> bool:
        """Authenticate with Bluesky using credentials from config"""
        try:
            # Try to load existing session
            logger.debug("Attempting to load existing session", extra={
                'context': {
                    'session_file': str(self.session_file),
                    'component': 'bluesky.auth'
                }
            })
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
                    # Add delay before retrying
                    time.sleep(5)
            
            # Create new session
            logger.debug("Creating new session", extra={
                'context': {
                    'identifier': Config.BLUESKY_IDENTIFIER,
                    'component': 'bluesky.auth'
                }
            })
            self.client = Client()  # Create new client instance
            self.profile = self.client.login(
                Config.BLUESKY_IDENTIFIER,
                Config.BLUESKY_PASSWORD
            )
            
            # Save new session
            logger.debug("Saving new session", extra={
                'context': {
                    'session_file': str(self.session_file),
                    'component': 'bluesky.auth'
                }
            })
            self._save_session(self.client.session)
            
            logger.info(f"Successfully logged in as: {self.profile.display_name}", extra={
                'context': {
                    'display_name': self.profile.display_name,
                    'component': 'bluesky.auth'
                }
            })
            return True
        except Exception as e:
            logger.error("Error authenticating with Bluesky", exc_info=True, extra={
                'context': {
                    'error': str(e),
                    'component': 'bluesky.auth'
                }
            })
            self._cleanup_session()
            # Add delay before next attempt
            time.sleep(5)
            return False
    
    @handle_rate_limit
    def post_content(self, content: str, link: Optional[str] = None) -> Optional[Any]:
        """Post content to Bluesky with optional link"""
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
            
    def get_timeline(self, limit: int = 20) -> Optional[Any]:
        """Get timeline posts"""
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
            
    def get_author_feed(self, actor: Optional[str] = None, limit: int = 20) -> Any:
        """Get posts from an author's feed"""
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

    def get_post_thread(self, uri: str) -> Any:
        """Get a thread of posts"""
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

    def like_post(self, uri: str, cid: Optional[str] = None) -> bool:
        """Like a post"""
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
            return "success"
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

    def reply_to_post(self, uri: str, text: str) -> Any:
        """Reply to a post"""
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