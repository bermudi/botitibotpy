"""
Base test class for CLI tests.
"""

import unittest
from click.testing import CliRunner

from src.cli.cli import main

class BaseCliTest(unittest.TestCase):
    """Base test class for CLI tests."""
    
    def setUp(self):
        """Set up test environment."""
        self.runner = CliRunner()
        
    def invoke_cli(self, args, **kwargs):
        """Invoke CLI command with given arguments."""
        with self.runner.isolated_filesystem():
            return self.runner.invoke(main, args, catch_exceptions=True, **kwargs)
