import unittest
from unittest.mock import patch, MagicMock
from src.social.bluesky import BlueskyClient


class TestBlueskyClient(unittest.TestCase):
    @patch('src.social.bluesky.Client')
    def setUp(self, mock_client):
        self.mock_client = mock_client
        self.bluesky_client = BlueskyClient()
        self.bluesky_client.__enter__()
    
    def tearDown(self):
        self.bluesky_client.__exit__(None, None, None)

    @patch('src.social.bluesky.client_utils.TextBuilder')
    def test_post_content_with_link(self, mock_text_builder):
        # Arrange
        mock_text_builder_instance = mock_text_builder.return_value
        mock_client_instance = self.mock_client.return_value
        mock_client_instance.send_post.return_value = "mock_post_response"
        self.bluesky_client.client = mock_client_instance

        content = "Test content"
        link = "https://example.com"

        # Act
        result = self.bluesky_client.post_content(content, link)

        # Assert
        mock_text_builder.assert_called_once()
        mock_text_builder_instance.text.assert_called_once_with(content)
        mock_text_builder_instance.link.assert_called_once_with("🔗", link)
        mock_client_instance.send_post.assert_called_once_with(mock_text_builder_instance)
        self.assertEqual(result, "mock_post_response")

    @patch('src.social.bluesky.client_utils.TextBuilder')
    def test_post_content_error_handling(self, mock_text_builder):
        # Arrange
        mock_text_builder_instance = mock_text_builder.return_value
        mock_client_instance = self.mock_client.return_value
        mock_client_instance.send_post.side_effect = Exception("Network error")
        self.bluesky_client.client = mock_client_instance
        
        # Act
        result = self.bluesky_client.post_content("Test content", "https://example.com")
        
        # Assert
        self.assertIsNone(result)
        mock_text_builder_instance.text.assert_called_once_with("Test content")
        mock_text_builder_instance.link.assert_called_once_with("🔗", "https://example.com")
        mock_client_instance.send_post.assert_called_once_with(mock_text_builder_instance)

    def test_get_timeline_default_limit(self):
        # Arrange
        mock_timeline = MagicMock()
        self.mock_client.return_value.get_timeline.return_value = mock_timeline
        self.bluesky_client.client = self.mock_client.return_value

        # Act
        result = self.bluesky_client.get_timeline()

        # Assert
        self.assertEqual(result, mock_timeline)
        self.mock_client.return_value.get_timeline.assert_called_once_with(limit=20)


    def test_get_timeline_with_custom_limit(self):
        # Arrange
        custom_limit = 10
        mock_timeline = MagicMock()
        self.bluesky_client.client.get_timeline = MagicMock(return_value=mock_timeline)

        # Act
        result = self.bluesky_client.get_timeline(limit=custom_limit)

        # Assert
        self.assertEqual(result, mock_timeline)
        self.bluesky_client.client.get_timeline.assert_called_once_with(limit=custom_limit)

    def test_get_post_thread_valid_uri(self):
        # Arrange
        mock_client_instance = self.mock_client.return_value
        mock_client_instance.get_post_thread.return_value = MagicMock(name='mock_thread')
        self.bluesky_client.client = mock_client_instance
        test_uri = "at://did:plc:1234abcd/app.bsky.feed.post/1234"

        # Act
        result = self.bluesky_client.get_post_thread(test_uri)

        # Assert
        self.assertIsNotNone(result)
        mock_client_instance.get_post_thread.assert_called_once_with(test_uri)

    def test_like_post_with_uri_and_cid(self):
        # Arrange
        uri = "test_uri"
        cid = "test_cid"
        self.mock_client.return_value.like.return_value = "success"
        self.bluesky_client.client = self.mock_client.return_value

        # Act
        result = self.bluesky_client.like_post(uri, cid)

        # Assert
        self.assertEqual(result, "success")
        self.mock_client.return_value.like.assert_called_once_with(uri, cid)

    def test_like_post_uri_only(self):
        # Arrange
        mock_client_instance = self.mock_client.return_value
        mock_post = MagicMock()
        mock_post.thread.post.cid = 'test_cid'
        mock_client_instance.get_post_thread.return_value = mock_post
        mock_client_instance.like.return_value = 'success'
        self.bluesky_client.client = mock_client_instance
        
        # Act
        result = self.bluesky_client.like_post('test_uri')
        
        # Assert
        mock_client_instance.get_post_thread.assert_called_once_with('test_uri')
        mock_client_instance.like.assert_called_once_with('test_uri', 'test_cid')
        self.assertEqual(result, 'success')

    def test_reply_to_post(self):
        # Arrange
        self.bluesky_client.client = MagicMock()
        uri = "test_uri"
        reply_text = "This is a test reply"
        expected_response = MagicMock()
        self.bluesky_client.client.send_post.return_value = expected_response

        # Act
        result = self.bluesky_client.reply_to_post(uri, reply_text)

        # Assert
        self.assertEqual(result, expected_response)
        self.bluesky_client.client.send_post.assert_called_once_with(text=reply_text, reply_to=uri)
    

    @patch('src.social.bluesky.AuthorFeedParams')
    def test_get_author_feed_current_user(self, mock_params):
        # Arrange
        mock_profile = MagicMock()
        mock_profile.did = 'test_user_did'
        self.bluesky_client.profile = mock_profile
        self.bluesky_client.client = self.mock_client

        mock_params.return_value = 'mocked_params'
        self.mock_client.get_author_feed.return_value = 'mocked_feed'

        # Act
        result = self.bluesky_client.get_author_feed()

        # Assert
        mock_params.assert_called_once_with(actor='test_user_did', limit=20)
        self.mock_client.get_author_feed.assert_called_once_with(params='mocked_params')
        self.assertEqual(result, 'mocked_feed')

if __name__ == '__main__':
    unittest.main()
