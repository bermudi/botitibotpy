import unittest
from unittest.mock import patch, MagicMock
from src.social.twitter import TwitterClient
from pathlib import Path
import json

class TestTwitterClient(unittest.TestCase):
    def setUp(self):
        self.twitter_client = TwitterClient()

    @patch('src.social.twitter.TwitterOpenapiPython')
    def test_post_content_success(self, mock_twitter_api):
        # Arrange
        mock_client = MagicMock()
        mock_post_api = MagicMock()
        mock_client.get_post_api.return_value = mock_post_api
        self.twitter_client.client = mock_client

        content = "Test content"

        # Act
        result = self.twitter_client.post_content(content)

        # Assert
        mock_client.get_post_api.assert_called_once()
        mock_post_api.post_create_tweet.assert_called_once_with(tweet_text=content)
        self.assertTrue(result)

    @patch('src.social.twitter.TwitterOpenapiPython')
    def test_post_content_error_handling(self, mock_twitter_api):
        # Arrange
        mock_client = MagicMock()
        mock_post_api = MagicMock()
        mock_post_api.post_create_tweet.side_effect = Exception("Network error")
        mock_client.get_post_api.return_value = mock_post_api
        self.twitter_client.client = mock_client

        # Act
        result = self.twitter_client.post_content("Test content")

        # Assert
        self.assertFalse(result)
        mock_client.get_post_api.assert_called_once()
        mock_post_api.post_create_tweet.assert_called_once()

    @patch('src.social.twitter.TwitterOpenapiPython')
    def test_get_timeline_default_limit(self, mock_twitter_api):
        # Arrange
        mock_client = MagicMock()
        mock_user_api = MagicMock()
        mock_timeline = MagicMock()
        mock_user_api.get_home_timeline.return_value = mock_timeline
        mock_client.get_user_api.return_value = mock_user_api
        self.twitter_client.client = mock_client

        # Act
        result = self.twitter_client.get_timeline()

        # Assert
        self.assertEqual(result, mock_timeline)
        mock_client.get_user_api.assert_called_once()
        mock_user_api.get_home_timeline.assert_called_once_with(count=20)

    @patch('src.social.twitter.TwitterOpenapiPython')
    def test_get_timeline_custom_limit(self, mock_twitter_api):
        # Arrange
        mock_client = MagicMock()
        mock_user_api = MagicMock()
        mock_timeline = MagicMock()
        mock_user_api.get_home_timeline.return_value = mock_timeline
        mock_client.get_user_api.return_value = mock_user_api
        self.twitter_client.client = mock_client
        custom_limit = 10

        # Act
        result = self.twitter_client.get_timeline(limit=custom_limit)

        # Assert
        self.assertEqual(result, mock_timeline)
        mock_user_api.get_home_timeline.assert_called_once_with(count=custom_limit)

    @patch('src.social.twitter.TwitterOpenapiPython')
    def test_get_tweet_thread(self, mock_twitter_api):
        # Arrange
        mock_client = MagicMock()
        mock_tweet_api = MagicMock()
        mock_thread = MagicMock()
        mock_tweet_api.get_tweet_detail.return_value = mock_thread
        mock_client.get_tweet_api.return_value = mock_tweet_api
        self.twitter_client.client = mock_client
        tweet_id = "123456789"

        # Act
        result = self.twitter_client.get_tweet_thread(tweet_id)

        # Assert
        self.assertEqual(result, mock_thread)
        mock_client.get_tweet_api.assert_called_once()
        mock_tweet_api.get_tweet_detail.assert_called_once_with(tweet_id)

    @patch('src.social.twitter.TwitterOpenapiPython')
    def test_like_tweet_success(self, mock_twitter_api):
        # Arrange
        mock_client = MagicMock()
        mock_tweet_api = MagicMock()
        mock_client.get_tweet_api.return_value = mock_tweet_api
        self.twitter_client.client = mock_client
        tweet_id = "123456789"

        # Act
        result = self.twitter_client.like_tweet(tweet_id)

        # Assert
        self.assertTrue(result)
        mock_client.get_tweet_api.assert_called_once()
        mock_tweet_api.favorite_tweet.assert_called_once_with(tweet_id)

    @patch('src.social.twitter.TwitterOpenapiPython')
    def test_reply_to_tweet_success(self, mock_twitter_api):
        # Arrange
        mock_client = MagicMock()
        mock_post_api = MagicMock()
        mock_client.get_post_api.return_value = mock_post_api
        self.twitter_client.client = mock_client
        tweet_id = "123456789"
        reply_text = "Test reply"

        # Act
        result = self.twitter_client.reply_to_tweet(tweet_id, reply_text)

        # Assert
        self.assertTrue(result)
        mock_client.get_post_api.assert_called_once()
        mock_post_api.post_create_tweet.assert_called_once_with(
            tweet_text=reply_text,
            reply_tweet_id=tweet_id
        )

    @patch('src.social.twitter.TwitterOpenapiPython')
    def test_get_author_feed_specific_user(self, mock_twitter_api):
        # Arrange
        mock_client = MagicMock()
        mock_user_api = MagicMock()
        mock_tweet_api = MagicMock()
        mock_user_info = MagicMock()
        mock_user_info.data.user.rest_id = "user123"
        mock_tweets = MagicMock()
        
        mock_user_api.get_user_by_screen_name.return_value = mock_user_info
        mock_tweet_api.get_user_tweets.return_value = mock_tweets
        
        mock_client.get_user_api.return_value = mock_user_api
        mock_client.get_tweet_api.return_value = mock_tweet_api
        
        self.twitter_client.client = mock_client
        screen_name = "testuser"

        # Act
        result = self.twitter_client.get_author_feed(screen_name)

        # Assert
        self.assertEqual(result, mock_tweets)
        mock_user_api.get_user_by_screen_name.assert_called_once_with(screen_name)
        mock_tweet_api.get_user_tweets.assert_called_once_with("user123")

    @patch('pathlib.Path.exists')
    @patch('builtins.open')
    @patch('json.load')
    def test_setup_auth_existing_cookies(self, mock_json_load, mock_open, mock_exists):
        # Arrange
        mock_exists.return_value = True
        mock_cookies = {"cookie1": "value1", "cookie2": "value2"}
        mock_json_load.return_value = mock_cookies
        mock_client = MagicMock()
        self.twitter_client.client = mock_client

        # Act
        result = self.twitter_client.setup_auth()

        # Assert
        self.assertTrue(result)
        mock_exists.assert_called_once()
        mock_open.assert_called_once()
        mock_json_load.assert_called_once()
        mock_client.get_client_from_cookies.assert_called_once_with(cookies=mock_cookies)

if __name__ == '__main__':
    unittest.main()
