"""
Base test class for CLI tests.
"""

import unittest
from click.testing import CliRunner, Result
from contextlib import contextmanager

from src.cli.cli import main

class BaseCliTest(unittest.TestCase):
    """Base test class for CLI tests."""
    
    def setUp(self):
        """Set up test environment."""
        self.runner = CliRunner()
        
    def invoke_cli(self, args, **kwargs) -> Result:
        """Invoke CLI command with given arguments."""
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(main, args, catch_exceptions=True, **kwargs)
            return result
