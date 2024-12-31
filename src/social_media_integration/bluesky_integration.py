from atproto import Client, models
from typing import List, Dict
import logging

class BlueskyClient:
    def __init__(self):
        """
        Initializes the Bluesky client.
        """
        self.client = Client()
        self.logger = logging.getLogger('bluesky_client')
        logging.basicConfig(level=logging.INFO)

    def authenticate(self, identifier: str, password: str) -> bool:
        """
        Authenticates with the Bluesky API.

        Args:
            identifier: The user's identifier (email or handle).
            password: The user's password.

        Returns:
            True if authentication was successful, False otherwise.
        """
        try:
            self.client.login(identifier, password)
            self.logger.info(f"Successfully authenticated as {identifier}")
            return True
        except Exception as e:
            self.logger.error(f"Authentication failed: {str(e)}")
            return False

    def create_post(self, text: str) -> Dict:
        """
        Creates a new post on Bluesky.

        Args:
            text: The text content of the post.

        Returns:
            Dictionary containing post details or error message.
        """
        try:
            post = self.client.send_post(text)
            self.logger.info(f"Successfully created post: {post.uri}")
            return {
                'uri': post.uri,
                'cid': post.cid,
                'text': text
            }
        except Exception as e:
            self.logger.error(f"Failed to create post: {str(e)}")
            return {'error': str(e)}

    def get_comments(self, post_uri: str) -> List[Dict]:
        """
        Retrieves comments for a given post on Bluesky.

        Args:
            post_uri: The URI of the post.

        Returns:
            List of dictionaries containing comment details.
        """
        try:
            thread = self.client.get_post_thread(post_uri)
            comments = []
            
            if thread.parent and thread.parent.replies:
                for reply in thread.parent.replies:
                    comments.append({
                        'uri': reply.post.uri,
                        'text': reply.post.record.text,
                        'author': reply.post.author.handle,
                        'timestamp': reply.post.indexed_at
                    })
            
            self.logger.info(f"Retrieved {len(comments)} comments for post {post_uri}")
            return comments
        except Exception as e:
            self.logger.error(f"Failed to retrieve comments: {str(e)}")
            return [{'error': str(e)}]

    def respond_to_comment(self, comment_uri: str, text: str) -> Dict:
        """
        Responds to a comment on Bluesky.

        Args:
            comment_uri: The URI of the comment.
            text: The text content of the response.

        Returns:
            Dictionary containing response details or error message.
        """
        try:
            parent = self.client.get_post(comment_uri)
            response = self.client.send_post(
                text,
                reply_to=models.AppBskyFeedPost.ReplyRef(
                    parent=parent,
                    root=parent
                )
            )
            self.logger.info(f"Successfully responded to comment {comment_uri}")
            return {
                'uri': response.uri,
                'cid': response.cid,
                'text': text
            }
        except Exception as e:
            self.logger.error(f"Failed to respond to comment: {str(e)}")
            return {'error': str(e)}

if __name__ == '__main__':
    # Initialize client
    bluesky_client = BlueskyClient()
    
    # Test authentication
    if bluesky_client.authenticate("your_handle", "your_password"):
        # Test post creation
        post = bluesky_client.create_post("This is a test post from the social media framework.")
        print(f"Created post: {post}")
        
        # Test comment retrieval (requires a valid post URI)
        if 'uri' in post:
            comments = bluesky_client.get_comments(post['uri'])
            print(f"Comments: {comments}")
            
            # Test comment response (requires a valid comment URI)
            if comments:
                response = bluesky_client.respond_to_comment(
                    comments[0]['uri'],
                    "This is a test response from the framework."
                )
                print(f"Response: {response}")
