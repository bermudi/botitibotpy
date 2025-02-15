import unittest
from unittest.mock import patch, MagicMock, call, mock_open
from src.social.twitter import TwitterClient
from pathlib import Path
import json

@patch('time.sleep')  # Class-level patch for sleep to speed up all tests
class TestTwitterClient(unittest.TestCase):
    @patch('src.social.twitter.CookieSessionUserHandler')
    def setUp(self, mock_cookie_handler):
        """Setup test environment"""
        # Create mock cookies with required fields
        mock_cookies_dict = {
            "auth_token": "test_token",
            "ct0": "test_ct0"
        }
        # Simplify mock setup
        mock_handler = MagicMock()
        mock_handler.get_cookies.return_value.get_dict.return_value = mock_cookies_dict
        mock_cookie_handler.return_value = mock_handler

        # Mock the retry decorator to just call the function once
        patcher = patch('src.social.twitter.retry_on_failure', lambda *args, **kwargs: lambda f: f)
        self.addCleanup(patcher.stop)
        patcher.start()

        # Mock the Config
        with patch('src.social.twitter.Config') as mock_config:
            mock_config.TWITTER_USERNAME = "test_user"
            mock_config.TWITTER_PASSWORD = "test_pass"
            with patch('src.social.twitter.TwitterOpenapiPython') as mock_twitter_api:
                mock_client = MagicMock()
                mock_twitter_api.return_value = mock_client
                mock_client.get_client_from_cookies.return_value = mock_client
                self.twitter_client = TwitterClient()
                self.twitter_client.client = mock_client

        # Store the mock handler for use in tests
        self.mock_cookie_handler = mock_cookie_handler
        self.mock_handler = mock_handler

    def _setup_mock_client(self):
        """Helper method to set up a mock client with required attributes"""
        mock_client = MagicMock()
        self.twitter_client.client = mock_client
        return mock_client

    def _setup_mock_post_api(self, return_value=None, side_effect=None):
        """Helper method to set up mock post API"""
        mock_client = MagicMock()
        mock_post_api = MagicMock()
        if return_value is not None:
            mock_post_api.post_create_tweet.return_value = return_value
        if side_effect is not None:
            mock_post_api.post_create_tweet.side_effect = side_effect
        mock_client.get_post_api.return_value = mock_post_api
        self.twitter_client.client = mock_client
        return mock_client, mock_post_api

    def _setup_mock_user_api(self, return_value=None):
        """Helper method to set up mock user API"""
        mock_client = MagicMock()
        mock_user_api = MagicMock()
        mock_user_api.get_home_timeline.return_value = return_value
        mock_client.get_user_api.return_value = mock_user_api
        self.twitter_client.client = mock_client
        return mock_client, mock_user_api

    def _setup_mock_tweet_api(self, return_value=None):
        """Helper method to set up mock tweet API"""
        mock_client = MagicMock()
        mock_tweet_api = MagicMock()
        if return_value is not None:
            mock_tweet_api.get_tweet_detail.return_value = return_value
            mock_tweet_api.get_user_tweets.return_value = return_value
        mock_client.get_tweet_api.return_value = mock_tweet_api
        self.twitter_client.client = mock_client
        return mock_client, mock_tweet_api

    @patch('src.social.twitter.TwitterOpenapiPython')
    def test_post_content_success(self, mock_twitter_api, mock_sleep):
        # Arrange
        content = "Test content"
        mock_client, mock_post_api = self._setup_mock_post_api()

        # Act
        result = self.twitter_client.post_content(content)

        # Assert
        mock_client.get_post_api.assert_called_once()
        mock_post_api.post_create_tweet.assert_called_once_with(tweet_text=content)
        self.assertTrue(result)

    @patch('src.social.twitter.TwitterOpenapiPython')
    def test_post_content_error_handling(self, mock_twitter_api, mock_sleep):
        # Arrange
        mock_client = MagicMock()
        mock_post_api = MagicMock()
        mock_post_api.post_create_tweet.side_effect = Exception("Network error")
        mock_client.get_post_api.return_value = mock_post_api
        self.twitter_client.client = mock_client

        # Act & Assert
        with self.assertRaises(Exception) as context:
            self.twitter_client.post_content("Test content")
        self.assertIn("Network error", str(context.exception))
        
        # Verify the retry behavior
        self.assertEqual(mock_client.get_post_api.call_count, 3)
        self.assertEqual(mock_post_api.post_create_tweet.call_count, 3)
        mock_post_api.post_create_tweet.assert_has_calls([
            call(tweet_text="Test content"),
            call(tweet_text="Test content"),
            call(tweet_text="Test content")
        ])

    @patch('src.social.twitter.CookieSessionUserHandler')
    def test_create_new_cookies(self, mock_cookie_handler, mock_sleep):
        """Test creating new cookies"""
        # Arrange
        mock_cookies = MagicMock()
        mock_cookies.get_dict.return_value = {
            "auth_token": "test_token",
            "ct0": "test_ct0"
        }
        mock_handler = MagicMock()
        mock_handler.get_cookies.return_value = mock_cookies
        mock_cookie_handler.return_value = mock_handler

        # Mock Config values
        with patch('src.social.twitter.Config') as mock_config:
            mock_config.TWITTER_USERNAME = "test_user"
            mock_config.TWITTER_PASSWORD = "test_pass"
            
            # Mock file operations
            mock_open_obj = mock_open()
            with patch('builtins.open', mock_open_obj):
                # Act
                result = self.twitter_client._create_new_cookies(Path("test_path"))

                # Assert
                self.assertEqual(result, {
                    "auth_token": "test_token",
                    "ct0": "test_ct0"
                })
                mock_cookie_handler.assert_called_once_with(
                    screen_name="test_user",
                    password="test_pass"
                )
                mock_handler.get_cookies.assert_called_once()
                mock_open_obj.assert_called_once_with(Path("test_path"), "w")
                self.assertTrue(mock_open_obj().write.called)

    def test_create_new_cookies_missing_credentials(self, mock_sleep):
        """Test creating new cookies with missing credentials"""
        with patch('src.social.twitter.Config') as mock_config:
            mock_config.TWITTER_USERNAME = None
            mock_config.TWITTER_PASSWORD = None
            
            with self.assertRaises(ValueError) as context:
                self.twitter_client._create_new_cookies(Path("test_path"))
            
            self.assertIn("Twitter credentials not found", str(context.exception))

    @patch('src.social.twitter.CookieSessionUserHandler')
    def test_create_new_cookies_auth_failure(self, mock_cookie_handler, mock_sleep):
        """Test creating new cookies with authentication failure"""
        # Arrange
        mock_handler = MagicMock()
        mock_handler.get_cookies.side_effect = Exception("LoginEnterPassword not found in response")
        mock_cookie_handler.return_value = mock_handler

        with patch('src.social.twitter.Config') as mock_config:
            mock_config.TWITTER_USERNAME = "test_user"
            mock_config.TWITTER_PASSWORD = "test_pass"
            
            # Mock file operations
            mock_open_obj = mock_open()
            with patch('builtins.open', mock_open_obj):
                # Act & Assert
                with self.assertRaises(Exception) as context:
                    self.twitter_client._create_new_cookies(Path("test_path"))
                
                self.assertIn("LoginEnterPassword not found in response", str(context.exception))
                # Verify retry behavior
                self.assertEqual(mock_handler.get_cookies.call_count, 3)
                # The CookieSessionUserHandler is called three times due to the retry decorator
                self.assertEqual(mock_cookie_handler.call_count, 3)
                # Verify all calls including constructor and method calls
                expected_calls = [
                    call(screen_name="test_user", password="test_pass"),
                    call().get_cookies(),
                    call(screen_name="test_user", password="test_pass"),
                    call().get_cookies(),
                    call(screen_name="test_user", password="test_pass"),
                    call().get_cookies()
                ]
                mock_cookie_handler.assert_has_calls(expected_calls, any_order=True)

    @patch('src.social.twitter.TwitterOpenapiPython')
    def test_get_timeline_default_limit(self, mock_twitter_api, mock_sleep):
        # Arrange
        mock_timeline = MagicMock()
        mock_client, mock_user_api = self._setup_mock_user_api(mock_timeline)

        # Act
        result = self.twitter_client.get_timeline()

        # Assert
        self.assertEqual(result, mock_timeline)
        mock_client.get_user_api.assert_called_once()
        mock_user_api.get_home_timeline.assert_called_once_with(count=20)

    @patch('src.social.twitter.TwitterOpenapiPython')
    def test_get_timeline_custom_limit(self, mock_twitter_api, mock_sleep):
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
    def test_get_tweet_thread(self, mock_twitter_api, mock_sleep):
        # Arrange
        mock_thread = MagicMock()
        mock_client, mock_tweet_api = self._setup_mock_tweet_api(mock_thread)
        tweet_id = "123456789"

        # Act
        result = self.twitter_client.get_tweet_thread(tweet_id)

        # Assert
        self.assertEqual(result, mock_thread)
        mock_client.get_tweet_api.assert_called_once()
        mock_tweet_api.get_tweet_detail.assert_called_once_with(tweet_id)

    @patch('src.social.twitter.TwitterOpenapiPython')
    def test_like_tweet_success(self, mock_twitter_api, mock_sleep):
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
    def test_reply_to_tweet_success(self, mock_twitter_api, mock_sleep):
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
    def test_get_author_feed_specific_user(self, mock_twitter_api, mock_sleep):
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
    def test_setup_auth_existing_cookies(self, mock_json_load, mock_open, mock_exists, mock_sleep):
        # Arrange
        mock_exists.return_value = True
        mock_cookies = {
            "auth_token": "test_auth_token",
            "ct0": "test_ct0"
        }
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

    @patch('src.social.twitter.TwitterOpenapiPython')
    def test_retry_mechanism_all_failures(self, mock_twitter_api, mock_sleep):
        """Test behavior when all retry attempts fail"""
        mock_client, mock_post_api = self._setup_mock_post_api(
            side_effect=Exception("Persistent failure")
        )

        with self.assertRaises(Exception) as context:
            self.twitter_client.post_content("Test content")
        self.assertIn("Persistent failure", str(context.exception))
        self.assertEqual(mock_post_api.post_create_tweet.call_count, 3)

    @patch('src.social.twitter.TwitterOpenapiPython')
    def test_retry_mechanism(self, mock_twitter_api, mock_sleep):
        """Test that retry mechanism works correctly"""
        mock_client, mock_post_api = self._setup_mock_post_api(
            side_effect=[
                Exception("First failure"),
                Exception("Second failure"),
                True  # Succeeds on third try
            ]
        )

        result = self.twitter_client.post_content("Test content")
        self.assertTrue(result)
        self.assertEqual(mock_post_api.post_create_tweet.call_count, 3)


if __name__ == '__main__':
    unittest.main()
