"""Exceptions for the scheduler module"""

class RateLimitError(Exception):
    """Exception raised when a rate limit is hit"""
    def __init__(self, message: str, operation_type: str, backoff: int):
        super().__init__(message)
        self.operation_type = operation_type
        self.backoff = backoff  # Time to wait in seconds
