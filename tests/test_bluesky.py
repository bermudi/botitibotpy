import unittest
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from src.social.bluesky import BlueskyClient, SimpleRateLimiter, RateLimitError, handle_rate_limit
from atproto_client.exceptions import RequestException

@pytest.mark.asyncio
class TestBlueskyClient(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        """Set up test fixtures before each test method."""
        self.client = BlueskyClient()
        self.client.client = MagicMock()
        self.client.profile = MagicMock()

    async def test_rate_limiter_initialization(self):
        """Test rate limiter initialization with default values"""
        rate_limiter = SimpleRateLimiter()
        
        # Check auth bucket
        self.assertEqual(rate_limiter.limits["auth"]["limit"], 100)
        self.assertEqual(rate_limiter.limits["auth"]["window"], 86400)
        self.assertEqual(rate_limiter.limits["auth"]["min_remaining"], 5)
        
        # Check write bucket
        self.assertEqual(rate_limiter.limits["write"]["limit"], 5000)
        self.assertEqual(rate_limiter.limits["write"]["window"], 86400)
        self.assertEqual(rate_limiter.limits["write"]["min_remaining"], 50)
        
        # Check read bucket
        self.assertEqual(rate_limiter.limits["read"]["limit"], 50000)
        self.assertEqual(rate_limiter.limits["read"]["window"], 86400)
        self.assertEqual(rate_limiter.limits["read"]["min_remaining"], 100)

    async def test_rate_limiter_update_from_headers(self):
        """Test updating rate limits from response headers"""
        rate_limiter = SimpleRateLimiter()
        headers = {
            'ratelimit-limit': '1000',
            'ratelimit-remaining': '900',
            'ratelimit-reset': str(int(datetime.now().timestamp()) + 3600),
            'ratelimit-policy': '1000;w=3600'
        }
        
        rate_limiter.update_from_headers(headers, "write")
        
        self.assertEqual(rate_limiter.limits["write"]["limit"], 1000)
        self.assertEqual(rate_limiter.limits["write"]["remaining"], 900)
        self.assertEqual(rate_limiter.limits["write"]["window"], 3600)

    async def test_rate_limiter_can_make_request(self):
        """Test rate limit checking logic"""
        rate_limiter = SimpleRateLimiter()
        
        # Should allow request when above min_remaining
        self.assertTrue(rate_limiter.can_make_request("write"))
        
        # Set remaining just above min_remaining
        rate_limiter.limits["write"]["remaining"] = rate_limiter.limits["write"]["min_remaining"] + 1
        self.assertTrue(rate_limiter.can_make_request("write"))
        
        # Set remaining at min_remaining
        rate_limiter.limits["write"]["remaining"] = rate_limiter.limits["write"]["min_remaining"]
        self.assertFalse(rate_limiter.can_make_request("write"))

    async def test_rate_limiter_decrement(self):
        """Test decrementing rate limit counters"""
        rate_limiter = SimpleRateLimiter()
        initial_remaining = rate_limiter.limits["write"]["remaining"]
        
        rate_limiter.decrement("write")
        self.assertEqual(rate_limiter.limits["write"]["remaining"], initial_remaining - 1)

    async def test_rate_limiter_backoff_time(self):
        """Test backoff time calculation"""
        rate_limiter = SimpleRateLimiter()
        
        # Test standard backoff
        backoff = rate_limiter.get_backoff_time("write")
        self.assertEqual(backoff, rate_limiter.backoff_times["write"])
        
        # Test backoff near reset time
        now = int(datetime.now().timestamp())
        rate_limiter.limits["write"]["reset_time"] = now + 300  # 5 minutes from now
        backoff = rate_limiter.get_backoff_time("write")
        self.assertLessEqual(backoff, 300)

    @patch('src.social.bluesky.SimpleRateLimiter')
    async def test_handle_rate_limit_decorator(self, mock_rate_limiter):
        """Test rate limit decorator behavior"""
        mock_rate_limiter.return_value.can_make_request.return_value = True
        
        @handle_rate_limit("write")
        def test_function():
            return "success"
            
        # Test successful execution
        result = test_function()
        self.assertEqual(result, "success")
        mock_rate_limiter.return_value.decrement.assert_called_once_with("write")
        
        # Test rate limit prevention
        mock_rate_limiter.return_value.can_make_request.return_value = False
        mock_rate_limiter.return_value.get_backoff_time.return_value = 60
        
        with self.assertRaises(RateLimitError) as context:
            test_function()
        
        self.assertEqual(context.exception.operation_type, "write")
        self.assertEqual(context.exception.backoff, 60)

    @patch('src.social.bluesky.SimpleRateLimiter')
    async def test_handle_rate_limit_remote_error(self, mock_rate_limiter):
        """Test handling of remote rate limit errors"""
        mock_rate_limiter.return_value.can_make_request.return_value = True
        
        @handle_rate_limit("write")
        def test_function():
            response = MagicMock()
            response.status_code = 429
            response.headers = {
                'ratelimit-reset': str(int(datetime.now().timestamp()) + 60)
            }
            raise RequestException("Rate limit exceeded", response=response)
            
        with self.assertRaises(RateLimitError) as context:
            test_function()
            
        self.assertEqual(context.exception.operation_type, "write")
        mock_rate_limiter.return_value.update_from_headers.assert_called_once()

    async def test_post_content_rate_limit(self):
        """Test post_content method with rate limiting"""
        self.client.client.send_post = AsyncMock(side_effect=[
            RequestException("Rate limit exceeded", response=MagicMock(
                status_code=429,
                headers={'ratelimit-reset': str(int(datetime.now().timestamp()) + 60)}
            )),
            MagicMock(uri="test_uri")  # Success on second try
        ])
        
        # First attempt should raise RateLimitError
        with self.assertRaises(RateLimitError) as context:
            await self.client.post_content("Test content")
            
        self.assertEqual(context.exception.operation_type, "write")
        
        # Reset rate limiter state
        rate_limiter = SimpleRateLimiter()
        rate_limiter.limits["write"]["remaining"] = rate_limiter.limits["write"]["limit"]
        
        # Second attempt should succeed
        result = await self.client.post_content("Test content")
        self.assertIsNotNone(result)
        self.assertEqual(result.uri, "test_uri")

    async def test_get_timeline_rate_limit(self):
        """Test get_timeline method with rate limiting"""
        self.client.client.get_timeline = AsyncMock(side_effect=RequestException(
            "Rate limit exceeded",
            response=MagicMock(
                status_code=429,
                headers={'ratelimit-reset': str(int(datetime.now().timestamp()) + 60)}
            )
        ))
        
        with self.assertRaises(RateLimitError) as context:
            await self.client.get_timeline()
            
        self.assertEqual(context.exception.operation_type, "read")

    async def test_auth_rate_limit(self):
        """Test authentication with rate limiting"""
        self.client.client.login = AsyncMock(side_effect=RequestException(
            "Rate limit exceeded",
            response=MagicMock(
                status_code=429,
                headers={'ratelimit-reset': str(int(datetime.now().timestamp()) + 60)}
            )
        ))
        
        with self.assertRaises(RateLimitError) as context:
            await self.client.setup_auth()
            
        self.assertEqual(context.exception.operation_type, "auth")

if __name__ == '__main__':
    pytest.main([__file__])
