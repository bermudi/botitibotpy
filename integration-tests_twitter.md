Here's how you can add integration tests for the Twitter client with real credentials:

1. First, create a separate test file for integration tests:

```python
# tests/integration/test_twitter_integration.py

import unittest
import os
import logging
from src.social.twitter import TwitterClient
from src.config import Config

class TestTwitterIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Setup test environment with real credentials"""
        # Ensure credentials exist
        if not Config.TWITTER_USERNAME or not Config.TWITTER_PASSWORD:
            raise unittest.SkipTest("Twitter credentials not configured")
        
        # Initialize client with debug logging
        cls.client = TwitterClient(log_level=logging.DEBUG)
        
        # Verify authentication
        if not cls.client.setup_auth():
            raise unittest.SkipTest("Failed to authenticate with Twitter")

    def test_timeline_fetch(self):
        """Test fetching actual timeline"""
        timeline = self.client.get_timeline(limit=5)
        self.assertIsNotNone(timeline)
        # Add specific assertions about timeline structure
        
    def test_post_and_delete_tweet(self):
        """Test posting and then deleting a tweet"""
        test_content = "Test tweet from integration tests " + os.urandom(4).hex()
        
        # Post tweet
        result = self.client.post_content(test_content)
        self.assertTrue(result)
        
        # Verify in own feed
        feed = self.client.get_author_feed()
        found = any(tweet.text == test_content for tweet in feed.tweets)
        self.assertTrue(found)
        
        # Clean up - delete test tweet
        # Add delete functionality if available in your client
        
    def test_interaction_flow(self):
        """Test a full interaction flow"""
        # 1. Post tweet
        tweet_text = f"Integration test tweet {os.urandom(4).hex()}"
        result = self.client.post_content(tweet_text)
        self.assertTrue(result)
        
        # 2. Get own feed to find tweet
        feed = self.client.get_author_feed()
        tweet = next(t for t in feed.tweets if t.text == tweet_text)
        
        # 3. Like own tweet
        like_result = self.client.like_tweet(tweet.id)
        self.assertTrue(like_result)
        
        # 4. Reply to tweet
        reply_text = f"Reply to integration test {os.urandom(4).hex()}"
        reply_result = self.client.reply_to_tweet(tweet.id, reply_text)
        self.assertTrue(reply_result)
        
        # 5. Get thread
        thread = self.client.get_tweet_thread(tweet.id)
        self.assertIsNotNone(thread)
        # Verify reply appears in thread

    def test_author_feed_fetch(self):
        """Test fetching specific author's feed"""
        # Test with known account like Twitter official
        feed = self.client.get_author_feed("Twitter")
        self.assertIsNotNone(feed)
        self.assertTrue(len(feed.tweets) > 0)

def main():
    # Setup logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Run tests
    unittest.main(verbosity=2)

if __name__ == '__main__':
    main()
```

2. Create a separate config file for testing:

```python
# tests/config/test_config.ini
[twitter]
username = your_test_account_username
password = your_test_account_password
```

3. Add helper script to run integration tests:

```bash
#!/bin/bash
# run_integration_tests.sh

export PYTHONPATH="."
export TWITTER_USERNAME="your_test_account"
export TWITTER_PASSWORD="your_test_password"

python -m unittest tests/integration/test_twitter_integration.py -v
```

Key points for integration testing:

1. Use a dedicated test account:
```python
# Create test account with:
- Limited followers/following
- No important data
- Clear description that it's a test account
```

2. Handle rate limits:
```python
def test_with_rate_limit(self):
    """Example of handling rate limits"""
    try:
        result = self.client.get_timeline(limit=100)
        self.assertIsNotNone(result)
    except Exception as e:
        if "rate limit" in str(e).lower():
            self.skipTest("Rate limit reached")
        raise
```

3. Clean up test data:
```python
def tearDown(self):
    """Clean up any test tweets/replies"""
    # Find and delete test tweets
    feed = self.client.get_author_feed()
    for tweet in feed.tweets:
        if "test tweet" in tweet.text.lower():
            self.client.delete_tweet(tweet.id)
```

4. Add environment variable support:
```python
# config.py
import os

class Config:
    TWITTER_USERNAME = os.getenv('TWITTER_USERNAME') 
    TWITTER_PASSWORD = os.getenv('TWITTER_PASSWORD')
```

5. Run selectively:
```bash
# Run specific test
python -m unittest tests.integration.test_twitter_integration.TestTwitterIntegration.test_timeline_fetch -v

# Run all integration tests
python -m unittest discover tests/integration -v
```

This setup allows you to:
- Test with real credentials safely
- Verify actual API behavior
- Clean up test data
- Handle rate limits
- Skip tests if credentials aren't available
- Run integration tests separately from unit tests

Remember to:
- Never commit real credentials
- Use a dedicated test account
- Clean up test data
- Handle rate limits gracefully
- Log extensively for debugging