from twitter_openapi_python import TwitterOpenapiPython
from ..config import Config

class TwitterClient:
    def __init__(self):
        self.client = TwitterOpenapiPython()
        self.setup_auth()
    
    def setup_auth(self):
        # Implementation will depend on whether you're using API keys or cookie auth
        # This is a simplified version
        pass
    
    def post_content(self, content: str):
        try:
            self.client.get_post_api().post_create_tweet(tweet_text=content)
        except Exception as e:
            print(f"Error posting to Twitter: {e}") 