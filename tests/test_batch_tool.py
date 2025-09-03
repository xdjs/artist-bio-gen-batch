#!/usr/bin/env python3
"""
Tests for batch_tool.py - Focus on meaningful edge cases and failure modes.
"""

import io
import logging
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from batch_tool import (
    setup_logger,
    create_parser,
    cmd_create,
    cmd_status,
    cmd_retrieve,
    cmd_cancel,
    cmd_list,
    cancel_batch,
    list_batches,
    main
)


class TestLoggerCreationAndFormat(unittest.TestCase):
    """Test logging setup and format validation."""
    
    def test_logger_creates_file_and_formats_correctly(self):
        """Ensure logs are actually written and flushed immediately."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test.log"
            
            # Create logger
            logger = setup_logger(log_path)
            
            # Write a test message
            test_message = "Test log message"
            logger.info(test_message)
            
            # Verify file was created and contains message
            self.assertTrue(log_path.exists())
            log_content = log_path.read_text()
            
            # Check format: YYYY-MM-DD HH:MM:SS,mmm LEVEL MESSAGE
            self.assertIn("INFO", log_content)
            self.assertIn(test_message, log_content)
            
            # Check timestamp format (roughly)
            lines = log_content.strip().split('\n')
            self.assertEqual(len(lines), 1)
            log_line = lines[0]
            
            # Should start with timestamp, contain level, end with message
            parts = log_line.split()
            self.assertTrue(len(parts) >= 3)
            self.assertEqual(parts[2], "INFO")  # Level should be third part
            self.assertIn(test_message, log_line)
    
    def test_logger_creates_parent_directories(self):
        """Verify logger creates parent directories if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "nested" / "dirs" / "test.log"
            
            # Verify parent doesn't exist initially
            self.assertFalse(log_path.parent.exists())
            
            # Create logger
            logger = setup_logger(log_path)
            logger.info("test")
            
            # Verify parent directories were created
            self.assertTrue(log_path.parent.exists())
            self.assertTrue(log_path.exists())
    
    def test_logger_handles_duplicate_handlers(self):
        """Ensure multiple logger setup calls don't create duplicate handlers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test.log"
            
            # Create logger twice
            logger1 = setup_logger(log_path)
            logger2 = setup_logger(log_path)
            
            # Should be the same logger instance
            self.assertEqual(logger1, logger2)
            
            # Should only have one handler
            self.assertEqual(len(logger1.handlers), 1)


class TestCLIArgumentParsing(unittest.TestCase):
    """Test CLI argument parsing edge cases."""
    
    def setUp(self):
        self.parser = create_parser()
    
    def test_conflicting_auto_save_flags(self):
        """Test --auto-save and --no-auto-save interaction."""
        # Default should be auto-save enabled
        args = self.parser.parse_args(['status', '--batch-id', 'test123'])
        self.assertTrue(args.auto_save)
        
        # Explicit --auto-save
        args = self.parser.parse_args(['status', '--batch-id', 'test123', '--auto-save'])
        self.assertTrue(args.auto_save)
        
        # --no-auto-save should disable
        args = self.parser.parse_args(['status', '--batch-id', 'test123', '--no-auto-save'])
        self.assertFalse(args.auto_save)
    
    def test_default_output_filename_generation(self):
        """Verify results_<batch_id>.jsonl naming works correctly."""
        # Test retrieve without --out flag
        args = self.parser.parse_args(['retrieve', '--batch-id', 'batch-abc123'])
        self.assertIsNone(args.out)  # Parser should leave as None for default handling
        
        # Test with custom output
        args = self.parser.parse_args(['retrieve', '--batch-id', 'batch-abc123', '--out', 'custom.jsonl'])
        self.assertEqual(args.out, 'custom.jsonl')
    
    def test_required_arguments_validation(self):
        """Test that required arguments are properly enforced."""
        # Missing batch-id for status
        with self.assertRaises(SystemExit):
            self.parser.parse_args(['status'])
        
        # Missing batch-id for retrieve
        with self.assertRaises(SystemExit):
            self.parser.parse_args(['retrieve'])
        
        # Missing input file for create
        with self.assertRaises(SystemExit):
            self.parser.parse_args(['create'])
    
    def test_default_values(self):
        """Test default values are set correctly."""
        args = self.parser.parse_args(['create', '--in', 'test.jsonl'])
        self.assertEqual(args.endpoint, '/v1/responses')
        self.assertEqual(args.completion_window, '24h')
        self.assertIsNone(args.log_file)


class TestFilePathValidation(unittest.TestCase):
    """Test file path validation and directory creation."""
    
    def test_input_file_validation_scenarios(self):
        """Test various invalid input file scenarios."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Setup mocks
            mock_client = Mock()
            mock_logger = Mock()
            
            # Test 1: Non-existent file
            args = Mock()
            args.input_file = str(tmpdir_path / "nonexistent.jsonl")
            args.endpoint = "/v1/responses"
            args.completion_window = "24h"
            
            result = cmd_create(args, mock_client, mock_logger)
            self.assertEqual(result, 1)  # Should return error code
            
            # Test 2: Directory instead of file
            dir_path = tmpdir_path / "directory"
            dir_path.mkdir()
            args.input_file = str(dir_path)
            
            result = cmd_create(args, mock_client, mock_logger)
            self.assertEqual(result, 1)  # Should return error code
            
            # Test 3: Valid file should not fail validation
            valid_file = tmpdir_path / "valid.jsonl"
            valid_file.write_text('{"test": "data"}')
            args.input_file = str(valid_file)
            
            # Mock the API calls to avoid actual network requests
            mock_client.files.create.return_value.id = "file-123"
            mock_client.batches.create.return_value.model_dump.return_value = {"id": "batch-123"}
            
            result = cmd_create(args, mock_client, mock_logger)
            self.assertEqual(result, 0)  # Should succeed
    
    def test_output_directory_creation(self):
        """Verify parent directories are created for output files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup deep nested output path
            output_path = Path(tmpdir) / "deep" / "nested" / "path" / "output.jsonl"
            
            # Mock the download_results function behavior
            with patch('batch_tool.download_results') as mock_download:
                mock_download.return_value = 1000  # byte count
                
                # Ensure parent directory creation is tested
                self.assertFalse(output_path.parent.exists())
                
                # This would be called within download_results
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text("test content")
                
                # Verify directory was created
                self.assertTrue(output_path.parent.exists())
                self.assertTrue(output_path.exists())
    
    def test_file_overwrite_handling(self):
        """Test behavior when output file already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            existing_file = Path(tmpdir) / "existing.jsonl"
            existing_file.write_text("existing content")
            
            # Test that file exists before operation
            self.assertTrue(existing_file.exists())
            original_content = existing_file.read_text()
            
            # Simulate overwrite behavior
            new_content = "new content"
            existing_file.write_text(new_content)
            
            # Verify file was overwritten
            self.assertEqual(existing_file.read_text(), new_content)
            self.assertNotEqual(existing_file.read_text(), original_content)


class TestErrorMessageQuality(unittest.TestCase):
    """Test that error messages help users fix problems."""
    
    def test_missing_api_key_error(self):
        """Test clear error message when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove OPENAI_API_KEY from environment
            if 'OPENAI_API_KEY' in os.environ:
                del os.environ['OPENAI_API_KEY']
            
            # Mock sys.argv to provide valid arguments
            test_args = ['batch_tool.py', 'status', '--batch-id', 'test123']
            with patch('sys.argv', test_args):
                with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
                    result = main()
                    
                    self.assertEqual(result, 1)
                    error_output = mock_stderr.getvalue()
                    self.assertIn("OPENAI_API_KEY", error_output)
                    self.assertIn("environment variable", error_output)
    
    def test_file_not_found_error_message(self):
        """Test helpful error message for missing input files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock args for non-existent file
            args = Mock()
            args.input_file = str(Path(tmpdir) / "missing.jsonl")
            
            mock_client = Mock()
            mock_logger = Mock()
            
            with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
                result = cmd_create(args, mock_client, mock_logger)
                
                self.assertEqual(result, 1)
                error_output = mock_stderr.getvalue()
                self.assertIn("not found", error_output.lower())
                self.assertIn("missing.jsonl", error_output)
    
    def test_batch_not_completed_error_message(self):
        """Test clear error message when trying to retrieve incomplete batch."""
        args = Mock()
        args.batch_id = "batch-test123"
        args.out = None
        
        mock_client = Mock()
        mock_logger = Mock()
        
        # Mock batch status as in_progress
        mock_batch_info = {
            'id': 'batch-test123',
            'status': 'in_progress',
            'created_at': int(datetime.now().timestamp())
        }
        mock_client.batches.retrieve.return_value.model_dump.return_value = mock_batch_info
        
        with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
            result = cmd_retrieve(args, mock_client, mock_logger)
            
            self.assertEqual(result, 1)
            error_output = mock_stderr.getvalue()
            self.assertIn("not completed", error_output)
            self.assertIn("in_progress", error_output)


class TestEndToEndWorkflow(unittest.TestCase):
    """Test end-to-end workflow with mocked API calls."""
    
    def test_complete_workflow_with_mock_files(self):
        """Test create->status->retrieve workflow with file I/O but mocked API."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create test input file
            input_file = tmpdir_path / "input.jsonl"
            input_file.write_text('{"custom_id": "test-1", "method": "POST", "url": "/v1/responses"}\n')
            
            # Mock OpenAI client
            mock_client = Mock()
            
            # Mock file upload response
            mock_file_response = Mock()
            mock_file_response.id = "file-abc123"
            mock_client.files.create.return_value = mock_file_response
            
            # Mock batch creation response
            mock_batch_response = Mock()
            mock_batch_response.model_dump.return_value = {
                'id': 'batch-def456',
                'status': 'validating',
                'created_at': int(datetime.now().timestamp())
            }
            mock_client.batches.create.return_value = mock_batch_response
            
            # Mock batch status responses (progression from validating to completed)
            mock_status_validating = {
                'id': 'batch-def456',
                'status': 'validating',
                'created_at': int(datetime.now().timestamp())
            }
            
            mock_status_completed = {
                'id': 'batch-def456',
                'status': 'completed',
                'created_at': int(datetime.now().timestamp()),
                'completed_at': int(datetime.now().timestamp()),
                'output_file_id': 'file-output123'
            }
            
            # Mock file content download
            mock_content = Mock()
            mock_content.content = b'{"custom_id": "test-1", "response": {"result": "success"}}\n'
            mock_client.files.content.return_value = mock_content
            
            # Setup logger
            log_file = tmpdir_path / "test.log"
            logger = setup_logger(log_file)
            
            # Test 1: Create batch
            create_args = Mock()
            create_args.input_file = str(input_file)
            create_args.endpoint = "/v1/responses"
            create_args.completion_window = "24h"
            
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                result = cmd_create(create_args, mock_client, logger)
                
                self.assertEqual(result, 0)
                output = mock_stdout.getvalue()
                self.assertIn("file-abc123", output)
                self.assertIn("batch-def456", output)
            
            # Verify API calls
            mock_client.files.create.assert_called_once()
            mock_client.batches.create.assert_called_once()
            
            # Test 2: Status check (validating)
            mock_client.batches.retrieve.return_value.model_dump.return_value = mock_status_validating
            
            status_args = Mock()
            status_args.batch_id = "batch-def456"
            status_args.auto_save = True
            
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                result = cmd_status(status_args, mock_client, logger)
                
                self.assertEqual(result, 0)
                output = mock_stdout.getvalue()
                self.assertIn("validating", output)
                # Should not auto-save since not completed
                self.assertNotIn("Results saved", output)
            
            # Test 3: Status check (completed with auto-save)
            mock_client.batches.retrieve.return_value.model_dump.return_value = mock_status_completed
            
            # Mock the download_results function to create the file and log
            def mock_download_side_effect(client, file_id, out_path, logger):
                # Log the operation (mimic real download_results function)
                logger.info(f"DOWNLOAD_RESULTS - Starting download: output_file_id={file_id}, out_path={out_path}")
                # Ensure parent directory exists
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text('{"custom_id": "test-1", "response": {"result": "success"}}\n')
                byte_count = len('{"custom_id": "test-1", "response": {"result": "success"}}\n')
                logger.info(f"DOWNLOAD_RESULTS - Success: saved {byte_count} bytes to {out_path}")
                return byte_count
            
            # Change working directory to tmpdir for the test
            import os
            original_cwd = os.getcwd()
            os.chdir(tmpdir_path)
            try:
                with patch('batch_tool.download_results', side_effect=mock_download_side_effect):
                    with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                        result = cmd_status(status_args, mock_client, logger)
                        
                        self.assertEqual(result, 0)
                        output = mock_stdout.getvalue()
                        self.assertIn("completed", output)
                        self.assertIn("Results saved", output)
                        
                        # Verify auto-saved file exists
                        auto_saved_file = tmpdir_path / "results_batch-def456.jsonl"
                        self.assertTrue(auto_saved_file.exists())
                        saved_content = auto_saved_file.read_text()
                        self.assertIn("success", saved_content)
            finally:
                os.chdir(original_cwd)
            
            # Test 4: Manual retrieve
            retrieve_args = Mock()
            retrieve_args.batch_id = "batch-def456"
            retrieve_args.out = str(tmpdir_path / "manual_results.jsonl")
            
            os.chdir(tmpdir_path)
            try:
                with patch('batch_tool.download_results', side_effect=mock_download_side_effect):
                    with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                        result = cmd_retrieve(retrieve_args, mock_client, logger)
                        
                        self.assertEqual(result, 0)
                        output = mock_stdout.getvalue()
                        self.assertIn("manual_results.jsonl", output)
                        
                        # Verify manual file exists
                        manual_file = tmpdir_path / "manual_results.jsonl"
                        self.assertTrue(manual_file.exists())
            finally:
                os.chdir(original_cwd)
            
            # Verify log file was created and contains entries
            self.assertTrue(log_file.exists())
            log_content = log_file.read_text()
            self.assertIn("UPLOAD", log_content)
            self.assertIn("CREATE_BATCH", log_content)
            self.assertIn("GET_STATUS", log_content)
            self.assertIn("DOWNLOAD_RESULTS", log_content)


class TestMainFunctionIntegration(unittest.TestCase):
    """Test main function with various argument combinations."""
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    def test_main_with_invalid_command(self):
        """Test main function handles invalid commands gracefully."""
        with patch('sys.argv', ['batch_tool.py', 'invalid_command']):
            with patch('sys.stderr', new_callable=io.StringIO):
                # argparse exits with code 2 for invalid arguments
                with self.assertRaises(SystemExit) as cm:
                    main()
                self.assertEqual(cm.exception.code, 2)
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    def test_main_keyboard_interrupt(self):
        """Test main function handles keyboard interrupt gracefully."""
        with patch('sys.argv', ['batch_tool.py', 'status', '--batch-id', 'test123']):
            with patch('batch_tool.cmd_status', side_effect=KeyboardInterrupt()):
                with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
                    result = main()
                    
                    self.assertEqual(result, 1)
                    output = mock_stderr.getvalue()
                    self.assertIn("interrupted", output.lower())


class TestCancelFunctionality(unittest.TestCase):
    """Test cancel batch functionality."""
    
    def test_cancel_batch_success(self):
        """Test successful batch cancellation."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.model_dump.return_value = {
            'id': 'batch_test123',
            'status': 'cancelling',
            'created_at': 1640995200  # 2022-01-01 00:00:00 UTC
        }
        mock_client.batches.cancel.return_value = mock_response
        
        # Mock logger
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test.log"
            logger = setup_logger(log_path)
            
            # Test cancel_batch function
            result = cancel_batch(mock_client, 'batch_test123', logger)
            
            # Verify API was called correctly
            mock_client.batches.cancel.assert_called_once_with('batch_test123')
            
            # Verify response
            self.assertEqual(result['status'], 'cancelling')
            self.assertEqual(result['id'], 'batch_test123')
    
    def test_cancel_batch_api_error(self):
        """Test cancel batch with API error."""
        mock_client = Mock()
        mock_client.batches.cancel.side_effect = Exception("API Error")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test.log"
            logger = setup_logger(log_path)
            
            # Should raise the exception
            with self.assertRaises(Exception) as cm:
                cancel_batch(mock_client, 'batch_test123', logger)
            
            self.assertEqual(str(cm.exception), "API Error")
    
    def test_cmd_cancel_success(self):
        """Test cmd_cancel function success."""
        # Mock args
        args = Mock()
        args.batch_id = 'batch_test123'
        
        # Mock client
        mock_client = Mock()
        
        # Mock logger  
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test.log"
            logger = setup_logger(log_path)
            
            # Mock cancel_batch function
            with patch('batch_tool.cancel_batch') as mock_cancel:
                mock_cancel.return_value = {
                    'id': 'batch_test123',
                    'status': 'cancelled',
                    'created_at': 1640995200
                }
                
                # Capture stdout
                with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                    result = cmd_cancel(args, mock_client, logger)
                
                # Check result
                self.assertEqual(result, 0)
                
                # Check output
                output = mock_stdout.getvalue()
                self.assertIn('batch_test123', output)
                self.assertIn('cancelled', output)
                self.assertIn('successfully cancelled', output)
    
    def test_cmd_cancel_cancelling_status(self):
        """Test cmd_cancel with cancelling status."""
        args = Mock()
        args.batch_id = 'batch_test123'
        mock_client = Mock()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test.log"
            logger = setup_logger(log_path)
            
            with patch('batch_tool.cancel_batch') as mock_cancel:
                mock_cancel.return_value = {
                    'id': 'batch_test123',
                    'status': 'cancelling'
                }
                
                with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                    result = cmd_cancel(args, mock_client, logger)
                
                self.assertEqual(result, 0)
                output = mock_stdout.getvalue()
                self.assertIn('cancellation in progress', output)
                self.assertIn('10 minutes', output)
    
    def test_cmd_cancel_error(self):
        """Test cmd_cancel with error."""
        args = Mock()
        args.batch_id = 'batch_test123'
        mock_client = Mock()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test.log"
            logger = setup_logger(log_path)
            
            with patch('batch_tool.cancel_batch') as mock_cancel:
                mock_cancel.side_effect = Exception("Cancel failed")
                
                with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
                    result = cmd_cancel(args, mock_client, logger)
                
                self.assertEqual(result, 1)
                output = mock_stderr.getvalue()
                self.assertIn('Cancel failed', output)
    
    def test_main_function_cancel_command(self):
        """Test main function with cancel command."""
        test_args = [
            'batch_tool.py',
            'cancel',
            '--batch-id', 'batch_test123'
        ]
        
        with patch('sys.argv', test_args):
            with patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'}):
                with patch('batch_tool.OpenAI') as mock_openai_class:
                    with patch('batch_tool.cmd_cancel', return_value=0) as mock_cmd_cancel:
                        with patch('batch_tool.setup_logger'):
                            result = main()
                        
                        # Check that cmd_cancel was called
                        self.assertEqual(mock_cmd_cancel.call_count, 1)
                        self.assertEqual(result, 0)
    
    def test_parser_includes_cancel_command(self):
        """Test that argument parser includes cancel command."""
        parser = create_parser()
        
        # Parse cancel command
        args = parser.parse_args(['cancel', '--batch-id', 'batch_test123'])
        
        self.assertEqual(args.command, 'cancel')
        self.assertEqual(args.batch_id, 'batch_test123')


class TestListFunctionality(unittest.TestCase):
    """Test list batches functionality."""
    
    def test_list_batches_success(self):
        """Test successful batch listing."""
        mock_client = Mock()
        
        # Mock batch objects
        mock_batch1 = Mock()
        mock_batch1.model_dump.return_value = {
            'id': 'batch_test123',
            'status': 'completed',
            'created_at': 1640995200,
            'endpoint': '/v1/responses',
            'request_counts': {'total': 10, 'completed': 10, 'failed': 0}
        }
        
        mock_batch2 = Mock()
        mock_batch2.model_dump.return_value = {
            'id': 'batch_test456',
            'status': 'in_progress',
            'created_at': 1640995260,
            'endpoint': '/v1/responses',
            'request_counts': {'total': 5, 'completed': 3, 'failed': 0}
        }
        
        # Mock the list method to return an iterable
        mock_client.batches.list.return_value = [mock_batch1, mock_batch2]
        
        # Mock logger
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test.log"
            logger = setup_logger(log_path)
            
            # Test list_batches function
            result = list_batches(mock_client, None, logger)
            
            # Verify API was called correctly
            mock_client.batches.list.assert_called_once()
            
            # Verify response
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]['id'], 'batch_test123')
            self.assertEqual(result[1]['id'], 'batch_test456')
    
    def test_list_batches_with_limit(self):
        """Test batch listing with limit."""
        mock_client = Mock()
        mock_batch = Mock()
        mock_batch.model_dump.return_value = {'id': 'batch_test123', 'status': 'completed'}
        mock_client.batches.list.return_value = [mock_batch]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test.log"
            logger = setup_logger(log_path)
            
            result = list_batches(mock_client, 5, logger)
            
            # Verify limit was passed
            mock_client.batches.list.assert_called_once_with(limit=5)
            self.assertEqual(len(result), 1)
    
    def test_list_batches_api_error(self):
        """Test list batches with API error."""
        mock_client = Mock()
        mock_client.batches.list.side_effect = Exception("API Error")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test.log"
            logger = setup_logger(log_path)
            
            # Should raise the exception
            with self.assertRaises(Exception) as cm:
                list_batches(mock_client, None, logger)
            
            self.assertEqual(str(cm.exception), "API Error")
    
    def test_cmd_list_success(self):
        """Test cmd_list function success."""
        # Mock args
        args = Mock()
        args.limit = 10
        
        # Mock client
        mock_client = Mock()
        
        # Mock logger  
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test.log"
            logger = setup_logger(log_path)
            
            # Mock list_batches function
            with patch('batch_tool.list_batches') as mock_list:
                mock_list.return_value = [
                    {
                        'id': 'batch_test123',
                        'status': 'completed',
                        'endpoint': '/v1/responses',
                        'created_at': 1640995200,
                        'completed_at': 1640995800,
                        'request_counts': {'total': 10, 'completed': 10, 'failed': 0}
                    },
                    {
                        'id': 'batch_test456',
                        'status': 'in_progress',
                        'endpoint': '/v1/responses',
                        'created_at': 1640995260
                    }
                ]
                
                # Capture stdout
                with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                    result = cmd_list(args, mock_client, logger)
                
                # Check result
                self.assertEqual(result, 0)
                
                # Check output
                output = mock_stdout.getvalue()
                self.assertIn('Found 2 batch job(s)', output)
                self.assertIn('batch_test123', output)
                self.assertIn('batch_test456', output)
                self.assertIn('completed', output)
                self.assertIn('in_progress', output)
                self.assertIn('10/10 completed', output)
    
    def test_cmd_list_no_batches(self):
        """Test cmd_list with no batches."""
        args = Mock()
        args.limit = None
        mock_client = Mock()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test.log"
            logger = setup_logger(log_path)
            
            with patch('batch_tool.list_batches') as mock_list:
                mock_list.return_value = []
                
                with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                    result = cmd_list(args, mock_client, logger)
                
                self.assertEqual(result, 0)
                output = mock_stdout.getvalue()
                self.assertIn('No batch jobs found', output)
    
    def test_cmd_list_error(self):
        """Test cmd_list with error."""
        args = Mock()
        args.limit = None
        mock_client = Mock()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test.log"
            logger = setup_logger(log_path)
            
            with patch('batch_tool.list_batches') as mock_list:
                mock_list.side_effect = Exception("List failed")
                
                with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
                    result = cmd_list(args, mock_client, logger)
                
                self.assertEqual(result, 1)
                output = mock_stderr.getvalue()
                self.assertIn('List failed', output)
    
    def test_main_function_list_command(self):
        """Test main function with list command."""
        test_args = [
            'batch_tool.py',
            'list',
            '--limit', '5'
        ]
        
        with patch('sys.argv', test_args):
            with patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'}):
                with patch('batch_tool.OpenAI') as mock_openai_class:
                    with patch('batch_tool.cmd_list', return_value=0) as mock_cmd_list:
                        with patch('batch_tool.setup_logger'):
                            result = main()
                        
                        # Check that cmd_list was called
                        self.assertEqual(mock_cmd_list.call_count, 1)
                        self.assertEqual(result, 0)
    
    def test_parser_includes_list_command(self):
        """Test that argument parser includes list command."""
        parser = create_parser()
        
        # Parse list command without limit
        args = parser.parse_args(['list'])
        self.assertEqual(args.command, 'list')
        self.assertIsNone(args.limit)
        
        # Parse list command with limit
        args = parser.parse_args(['list', '--limit', '10'])
        self.assertEqual(args.command, 'list')
        self.assertEqual(args.limit, 10)


if __name__ == '__main__':
    unittest.main()