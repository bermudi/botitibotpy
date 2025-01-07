"""
Tests for system management CLI commands.
"""

import unittest
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from .test_base import BaseCliTest
from src.cli.cli import system

class TestSystemCommands(BaseCliTest):
    """Test cases for system management commands."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.mock_monitoring = patch('src.cli.cli.MonitoringSystem').start()
        self.monitoring_instance = self.mock_monitoring.return_value
        self.mock_scheduler = patch('src.cli.cli.TaskScheduler').start()
        self.scheduler_instance = self.mock_scheduler.return_value
        
    def test_status_command(self):
        """Test system status command."""
        self.monitoring_instance.get_current_status.return_value = {
            'cpu_usage': 25.5,
            'memory_usage': 45.2,
            'disk_usage': 60.0,
            'active_tasks': 3,
            'queue_size': 5
        }
        
        result = self.invoke_cli(['system', 'status'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("CPU Usage: 25.5%", result.output)
        self.assertIn("Memory Usage: 45.2%", result.output)
        self.assertIn("Disk Usage: 60.0%", result.output)
        self.assertIn("Active Tasks: 3", result.output)
        self.assertIn("Task Queue Size: 5", result.output)
        
    def test_status_command_error(self):
        """Test system status command error handling."""
        self.monitoring_instance.get_current_status.side_effect = Exception("Test error")
        
        result = self.invoke_cli(['system', 'status'])
        
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Error: Test error", result.output)
        
    def test_start_scheduler(self):
        """Test starting the task scheduler."""
        result = self.invoke_cli(['system', 'start'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Task scheduler started successfully", result.output)
        self.scheduler_instance.start.assert_called_once()
        
    def test_start_scheduler_error(self):
        """Test starting the task scheduler with error."""
        self.scheduler_instance.start.side_effect = Exception("Failed to start")
        
        result = self.invoke_cli(['system', 'start'])
        
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Error: Failed to start", result.output)
        
    def test_stop_scheduler(self):
        """Test stopping the task scheduler."""
        result = self.invoke_cli(['system', 'stop'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Task scheduler stopped successfully", result.output)
        self.scheduler_instance.stop.assert_called_once()
        
    def test_stop_scheduler_error(self):
        """Test stopping the task scheduler with error."""
        self.scheduler_instance.stop.side_effect = Exception("Failed to stop")
        
        result = self.invoke_cli(['system', 'stop'])
        
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Error: Failed to stop", result.output)
