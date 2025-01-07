"""
Base test class for CLI tests.
"""

import unittest
from click.testing import CliRunner, Result

from src.cli.cli import main

class BaseCliTest(unittest.TestCase):
    """Base test class for CLI tests."""
    
    def setUp(self):
        """Set up test environment."""
        self.runner = CliRunner(mix_stderr=False)
        
    def invoke_cli(self, args, **kwargs) -> Result:
        """Invoke CLI command with given arguments."""
        with self.runner.isolated_filesystem():
            try:
                result = self.runner.invoke(main, args, catch_exceptions=True, **kwargs)
                return result
            except ValueError:
                # Create a new result object with error info
                result = Result(runner=self.runner,
                              stdout_bytes=b"",
                              stderr_bytes=b"Error: Command failed\n",
                              return_value=None,
                              exit_code=1,
                              exception=None)
                return result
