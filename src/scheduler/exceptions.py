"""Exceptions for the scheduler module"""

class RateLimitError(Exception):
    """Raised when a rate limit is hit"""
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds")
