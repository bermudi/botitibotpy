"""
Base test class for CLI tests.
"""

import unittest
from click.testing import CliRunner
from contextlib import contextmanager

from src.cli.cli import main

class BaseCliTest(unittest.TestCase):
    """Base test class for CLI tests."""
    
    def setUp(self):
        """Set up test environment."""
        self.runner = CliRunner()
        
    def invoke_cli(self, args, **kwargs):
        """Invoke CLI command with given arguments."""
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(main, args, catch_exceptions=True, **kwargs)
            if result.exit_code == 1:
                # For error cases, we expect exit code 1
                return result
            elif result.exit_code != 0:
                raise Exception(f"Command failed with exit code {result.exit_code}: {result.output}")
            return result
