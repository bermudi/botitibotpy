"""
Tests for content generation CLI commands.
"""

import unittest
from unittest.mock import MagicMock, patch

from .test_base import BaseCliTest

class TestContentCommands(BaseCliTest):
    """Test cases for content generation commands."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.mock_generator = patch('src.cli.cli.ContentGenerator').start()
        self.generator_instance = self.mock_generator.return_value
        
    def test_generate_content(self):
        """Test content generation."""
        self.generator_instance.generate_post.return_value = "Generated content"
        
        result = self.invoke_cli(['content', 'generate',
                                '--prompt', 'Test prompt'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Generated content", result.output)
        self.generator_instance.generate_post.assert_called_once_with("Test prompt", max_length=None, tone='neutral')
        
    def test_generate_content_error(self):
        """Test content generation error handling."""
        self.generator_instance.generate_post.side_effect = Exception("Test error")
        
        result = self.invoke_cli(['content', 'generate',
                                '--prompt', 'Test prompt'])
        
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Error: Test error", result.output)
        
    def test_list_sources(self):
        """Test listing content sources."""
        self.generator_instance.list_sources.return_value = [
            "source1.txt",
            "source2.txt"
        ]
        
        result = self.invoke_cli(['content', 'list-sources'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Content Sources:", result.output)
        self.assertIn("source1.txt", result.output)
        self.assertIn("source2.txt", result.output)
        
    def test_list_sources_empty(self):
        """Test listing content sources when none exist."""
        self.generator_instance.list_sources.return_value = []
        
        result = self.invoke_cli(['content', 'list-sources'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No content sources registered", result.output)
        
    def test_update_index(self):
        """Test updating content index."""
        self.generator_instance.update_index.return_value = [
            "Added: file1.txt",
            "Modified: file2.txt"
        ]
        
        result = self.invoke_cli(['content', 'update-index'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Index Changes:", result.output)
        self.assertIn("Added: file1.txt", result.output)
        self.assertIn("Modified: file2.txt", result.output)
        self.generator_instance.update_index.assert_called_once_with(dry_run=False)
        
    def test_update_index_dry_run(self):
        """Test updating content index in dry-run mode."""
        self.generator_instance.update_index.return_value = [
            "Would add: file1.txt",
            "Would modify: file2.txt"
        ]
        
        result = self.invoke_cli(['content', 'update-index', '--dry-run'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Index Changes:", result.output)
        self.assertIn("Would add: file1.txt", result.output)
        self.assertIn("Would modify: file2.txt", result.output)
        self.generator_instance.update_index.assert_called_once_with(dry_run=True)
