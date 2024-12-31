from twitter_openapi_python import TwitterOpenapiPython
from twitter_openapi_python.models import PostCreateTweetRequest
from typing import List, Dict
import logging

class TwitterClient:
    def __init__(self):
        """
        Initializes the Twitter client.
        """
        self.api = TwitterOpenapiPython()
        self.client = None
        self.logger = logging.getLogger('twitter_client')
        logging.basicConfig(level=logging.INFO)

    def authenticate(self, api_key: str, api_secret: str, access_token: str, access_secret: str) -> bool:
        """
        Authenticates with the Twitter API.

        Args:
            api_key: The Twitter API key.
            api_secret: The Twitter API secret key.
            access_token: The Twitter access token.
            access_secret: The Twitter access secret token.

        Returns:
            True if authentication was successful, False otherwise.
        """
        try:
            self.client = self.api.get_client_from_keys(
                api_key=api_key,
                api_secret=api_secret,
                access_token=access_token,
                access_secret=access_secret
            )
            self.logger.info("Successfully authenticated with Twitter API")
            return True
        except Exception as e:
            self.logger.error(f"Twitter authentication failed: {str(e)}")
            return False

    def create_tweet(self, text: str) -> Dict:
        """
        Creates a new tweet on Twitter.

        Args:
            text: The text content of the tweet.

        Returns:
            Dictionary containing tweet details or error message.
        """
        try:
            request = PostCreateTweetRequest(text=text)
            response = self.client.get_tweet_api().post_create_tweet(request)
            tweet = response.data
            self.logger.info(f"Successfully created tweet: {tweet.id}")
            return {
                'id': tweet.id,
                'text': tweet.text,
                'url': f"https://twitter.com/user/status/{tweet.id}"
            }
        except Exception as e:
            self.logger.error(f"Failed to create tweet: {str(e)}")
            return {'error': str(e)}

    def get_tweet_comments(self, tweet_id: str) -> List[Dict]:
        """
        Retrieves comments for a given tweet on Twitter.

        Args:
            tweet_id: The ID of the tweet.

        Returns:
            List of dictionaries containing comment details.
        """
        try:
            response = self.client.get_tweet_api().get_tweet_detail(tweet_id)
            comments = []
            
            for entry in response.data.threaded_conversation_with_injections.instructions[0].entries:
                if entry.entry_id.startswith('conversationthread-'):
                    for item in entry.content.items:
                        comments.append({
                            'id': item.tweet.id,
                            'text': item.tweet.full_text,
                            'author': item.tweet.user.screen_name,
                            'timestamp': item.tweet.created_at
                        })
            
            self.logger.info(f"Retrieved {len(comments)} comments for tweet {tweet_id}")
            return comments
        except Exception as e:
            self.logger.error(f"Failed to retrieve comments: {str(e)}")
            return [{'error': str(e)}]

    def respond_to_tweet_comment(self, comment_id: str, text: str) -> Dict:
        """
        Responds to a comment on Twitter.

        Args:
            comment_id: The ID of the comment.
            text: The text content of the response.

        Returns:
            Dictionary containing response details or error message.
        """
        try:
            request = PostCreateTweetRequest(
                text=text,
                reply=PostCreateTweetRequest.Reply(in_reply_to_tweet_id=comment_id)
            )
            response = self.client.get_tweet_api().post_create_tweet(request)
            tweet = response.data
            self.logger.info(f"Successfully responded to comment {comment_id}")
            return {
                'id': tweet.id,
                'text': tweet.text,
                'url': f"https://twitter.com/user/status/{tweet.id}"
            }
        except Exception as e:
            self.logger.error(f"Failed to respond to comment: {str(e)}")
            return {'error': str(e)}

if __name__ == '__main__':
    # Initialize client
    twitter_client = TwitterClient()
    
    # Test authentication
    if twitter_client.authenticate("your_api_key", "your_api_secret", "your_access_token", "your_access_secret"):
        # Test tweet creation
        tweet = twitter_client.create_tweet("This is a test tweet from the social media framework.")
        print(f"Created tweet: {tweet}")
        
        # Test comment retrieval (requires a valid tweet ID)
        if 'id' in tweet:
            comments = twitter_client.get_tweet_comments(tweet['id'])
            print(f"Comments: {comments}")
            
            # Test comment response (requires a valid comment ID)
            if comments:
                response = twitter_client.respond_to_tweet_comment(
                    comments[0]['id'],
                    "This is a test response from the framework."
                )
                print(f"Response: {response}")
