from atproto import Client, client_utils
from typing import Optional, Any
from ..config import Config
from atproto_client.models.app.bsky.feed.get_author_feed import Params as AuthorFeedParams
import logging

logger = logging.getLogger("botitibot.social.bluesky")

class BlueskyClient:
    def __init__(self):
        logger.info("Initializing Bluesky client", extra={
            'context': {
                'component': 'bluesky.client'
            }
        })
        self.client = None
        self.profile = None
    
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
    
    def setup_auth(self) -> bool:
        """Authenticate with Bluesky using credentials from config"""
        try:
            logger.debug("Attempting Bluesky authentication", extra={
                'context': {
                    'identifier': Config.BLUESKY_IDENTIFIER,
                    'component': 'bluesky.auth'
                }
            })
            self.profile = self.client.login(
                Config.BLUESKY_IDENTIFIER,
                Config.BLUESKY_PASSWORD
            )
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
            return False
    
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
            
    def get_post_thread(self, uri: str, depth: int = 1) -> Optional[Any]:
        """Get thread for a post"""
        try:
            logger.debug("Fetching post thread", extra={
                'context': {
                    'uri': uri,
                    'depth': depth,
                    'component': 'bluesky.thread'
                }
            })
            thread = self.client.get_post_thread(uri=uri, depth=depth)
            logger.info(f"Successfully fetched thread for post {uri}", extra={
                'context': {
                    'uri': uri,
                    'component': 'bluesky.thread'
                }
            })
            return thread
        except Exception as e:
            logger.error("Error fetching post thread", exc_info=True, extra={
                'context': {
                    'error': str(e),
                    'component': 'bluesky.thread'
                }
            })
            return None
            
    def like_post(self, uri: str, cid: str) -> bool:
        """Like a post"""
        try:
            logger.debug("Attempting to like post", extra={
                'context': {
                    'uri': uri,
                    'cid': cid,
                    'component': 'bluesky.like'
                }
            })
            self.client.like(uri=uri, cid=cid)
            logger.info(f"Successfully liked post {uri}", extra={
                'context': {
                    'uri': uri,
                    'component': 'bluesky.like'
                }
            })
            return True
        except Exception as e:
            logger.error("Error liking post", exc_info=True, extra={
                'context': {
                    'error': str(e),
                    'component': 'bluesky.like'
                }
            })
            return False
            
    def reply_to_post(self, uri: str, cid: str, text: str) -> Optional[Any]:
        """Reply to a post"""
        try:
            logger.debug("Creating reply", extra={
                'context': {
                    'uri': uri,
                    'cid': cid,
                    'text_length': len(text),
                    'component': 'bluesky.reply'
                }
            })
            reply = self.client.send_post(text=text, reply_to={"uri": uri, "cid": cid})
            logger.info(f"Successfully replied to post {uri}", extra={
                'context': {
                    'uri': uri,
                    'reply_uri': getattr(reply, 'uri', None),
                    'component': 'bluesky.reply'
                }
            })
            return reply
        except Exception as e:
            logger.error("Error replying to post", exc_info=True, extra={
                'context': {
                    'error': str(e),
                    'component': 'bluesky.reply'
                }
            })
            return None
            
    def get_author_feed(self, actor: str, limit: int = 20) -> Optional[Any]:
        """Get posts from a specific author"""
        try:
            logger.debug("Fetching author feed", extra={
                'context': {
                    'actor': actor,
                    'limit': limit,
                    'component': 'bluesky.feed'
                }
            })
            params = AuthorFeedParams(actor=actor, limit=limit)
            feed = self.client.app.bsky.feed.get_author_feed(params)
            logger.info(f"Successfully fetched feed for author {actor}", extra={
                'context': {
                    'actor': actor,
                    'feed_length': len(feed.feed) if hasattr(feed, 'feed') else 0,
                    'component': 'bluesky.feed'
                }
            })
            return feed
        except Exception as e:
            logger.error("Error fetching author feed", exc_info=True, extra={
                'context': {
                    'error': str(e),
                    'component': 'bluesky.feed'
                }
            })
            return None