#!/usr/bin/env python3
"""
Tests for gen_batch_jsonl.py
"""

import io
import json
import os
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.append(str(Path(__file__).parent.parent))

from gen_batch_jsonl import (
    build_task_row,
    convert_csv_to_jsonl,
    validate_row,
    process_csv_rows,
    get_config_value,
    main,
    ConversionStats
)


class TestBuildTaskRow(unittest.TestCase):
    """Test the build_task_row function."""
    
    def test_basic_task_row(self):
        """Test building a basic task row."""
        result = build_task_row(
            artist_id="test_id",
            artist_name="Test Artist",
            artist_data="Test data",
            prompt_id="bio_gen",
            prompt_version="v1.0"
        )
        
        expected = {
            "custom_id": "test_id",
            "method": "POST",
            "url": "/v1/responses",
            "body": {
                "prompt": {
                    "id": "bio_gen",
                    "version": "v1.0",
                    "variables": {
                        "artist_name": "Test Artist",
                        "artist_data": "Test data"
                    }
                }
            }
        }
        
        self.assertEqual(result, expected)
    
    def test_empty_artist_data(self):
        """Test task row with empty artist data."""
        result = build_task_row(
            artist_id="id1",
            artist_name="Artist",
            artist_data="",
            prompt_id="prompt",
            prompt_version="v2"
        )
        
        self.assertEqual(result["body"]["prompt"]["variables"]["artist_data"], "")
    
    def test_special_characters(self):
        """Test task row with special characters."""
        result = build_task_row(
            artist_id="unicode_test",
            artist_name="Björk",
            artist_data="Icelandic artist with émotion",
            prompt_id="test",
            prompt_version="v1"
        )
        
        self.assertEqual(result["body"]["prompt"]["variables"]["artist_name"], "Björk")
        self.assertEqual(result["body"]["prompt"]["variables"]["artist_data"], "Icelandic artist with émotion")
    
    def test_optional_prompt_version(self):
        """Test task row without prompt version."""
        result = build_task_row(
            artist_id="test_id",
            artist_name="Test Artist",
            artist_data="Test data",
            prompt_id="bio_gen"
        )
        
        expected = {
            "custom_id": "test_id",
            "method": "POST",
            "url": "/v1/responses",
            "body": {
                "prompt": {
                    "id": "bio_gen",
                    "variables": {
                        "artist_name": "Test Artist",
                        "artist_data": "Test data"
                    }
                }
            }
        }
        
        self.assertEqual(result, expected)
        # Ensure version key is not present
        self.assertNotIn("version", result["body"]["prompt"])
    
    def test_none_prompt_version(self):
        """Test task row with explicit None prompt version."""
        result = build_task_row(
            artist_id="test_id",
            artist_name="Test Artist",
            artist_data="Test data",
            prompt_id="bio_gen",
            prompt_version=None
        )
        
        # Should behave same as omitted version
        self.assertNotIn("version", result["body"]["prompt"])
    
    def test_empty_string_prompt_version(self):
        """Test task row with empty string prompt version."""
        result = build_task_row(
            artist_id="test_id",
            artist_name="Test Artist",
            artist_data="Test data",
            prompt_id="bio_gen",
            prompt_version=""
        )
        
        # Empty string should be treated as falsy, version not included
        self.assertNotIn("version", result["body"]["prompt"])


class TestValidateRow(unittest.TestCase):
    """Test row validation."""
    
    def test_valid_row(self):
        """Test valid row validation."""
        self.assertTrue(validate_row("id1", "Artist Name", "Some data"))
        self.assertTrue(validate_row("id2", "Name", ""))  # Empty data is ok
    
    def test_invalid_rows(self):
        """Test invalid row validation."""
        self.assertFalse(validate_row("", "Artist Name", "data"))  # Empty ID
        self.assertFalse(validate_row("id1", "", "data"))  # Empty name
        self.assertFalse(validate_row("  ", "Artist", "data"))  # Whitespace ID
        self.assertFalse(validate_row("id1", "  ", "data"))  # Whitespace name


class TestProcessCsvRows(unittest.TestCase):
    """Test CSV processing."""
    
    def test_with_header(self):
        """Test processing CSV with header."""
        csv_content = """artist_id,artist_name,artist_data
a1,Artist One,Data one
a2,Artist Two,Data two"""
        
        csv_file = io.StringIO(csv_content)
        rows = list(process_csv_rows(csv_file, has_header=True))
        
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['artist_id'], 'a1')
        self.assertEqual(rows[0]['artist_name'], 'Artist One')
        self.assertEqual(rows[0]['artist_data'], 'Data one')
    
    def test_without_header(self):
        """Test processing CSV without header."""
        csv_content = """a1,Artist One,Data one
a2,Artist Two,Data two"""
        
        csv_file = io.StringIO(csv_content)
        rows = list(process_csv_rows(csv_file, has_header=False))
        
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['artist_id'], 'a1')
        self.assertEqual(rows[0]['artist_name'], 'Artist One')
        self.assertEqual(rows[0]['artist_data'], 'Data one')
    
    def test_embedded_commas_newlines(self):
        """Test CSV with embedded commas and newlines in artist_data."""
        csv_content = '''artist_id,artist_name,artist_data
a1,Test Artist,"Complex data with, commas and
newlines"
a2,Simple Artist,Simple data'''
        
        csv_file = io.StringIO(csv_content)
        rows = list(process_csv_rows(csv_file, has_header=True))
        
        self.assertEqual(len(rows), 2)
        self.assertIn('commas and\nnewlines', rows[0]['artist_data'])
    
    def test_limit_processing(self):
        """Test limit parameter."""
        csv_content = """artist_id,artist_name,artist_data
a1,Artist One,Data one
a2,Artist Two,Data two
a3,Artist Three,Data three"""
        
        csv_file = io.StringIO(csv_content)
        rows = list(process_csv_rows(csv_file, has_header=True, limit=2))
        
        self.assertEqual(len(rows), 2)
    
    def test_missing_artist_name_non_strict(self):
        """Test missing artist name in non-strict mode."""
        csv_content = """artist_id,artist_name,artist_data
a1,,Data one
a2,Artist Two,Data two"""
        
        csv_file = io.StringIO(csv_content)
        with patch('logging.warning') as mock_warn:
            rows = list(process_csv_rows(csv_file, has_header=True, strict=False))
        
        self.assertEqual(len(rows), 1)  # Only valid row
        self.assertEqual(rows[0]['artist_id'], 'a2')
        mock_warn.assert_called()
    
    def test_missing_artist_name_strict(self):
        """Test missing artist name in strict mode."""
        csv_content = """artist_id,artist_name,artist_data
a1,,Data one"""
        
        csv_file = io.StringIO(csv_content)
        
        with self.assertRaises(ValueError):
            list(process_csv_rows(csv_file, has_header=True, strict=True))
    
    def test_wrong_header_columns(self):
        """Test CSV with wrong header columns."""
        csv_content = """id,name,data
a1,Artist One,Data one"""
        
        csv_file = io.StringIO(csv_content)
        
        with self.assertRaises(ValueError) as cm:
            list(process_csv_rows(csv_file, has_header=True))
        
        self.assertIn("CSV header must contain", str(cm.exception))


class TestConvertCsvToJsonl(unittest.TestCase):
    """Test full CSV to JSONL conversion."""
    
    def test_basic_conversion(self):
        """Test basic conversion process."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.csv"
            output_path = Path(tmpdir) / "output.jsonl"
            
            # Create test CSV
            input_path.write_text("""artist_id,artist_name,artist_data
a1,NewJeans,K-pop group
a2,Stereolab,Post-rock band""")
            
            # Convert
            stats = convert_csv_to_jsonl(
                input_path=input_path,
                output_path=output_path,
                prompt_id="test_prompt",
                prompt_version="v1.0"
            )
            
            # Check stats
            self.assertEqual(stats.read, 2)
            self.assertEqual(stats.written, 2)
            self.assertEqual(stats.skipped, 0)
            
            # Check output
            output_lines = output_path.read_text().strip().split('\n')
            self.assertEqual(len(output_lines), 2)
            
            # Parse first line
            first_task = json.loads(output_lines[0])
            self.assertEqual(first_task['custom_id'], 'a1')
            self.assertEqual(first_task['method'], 'POST')
            self.assertEqual(first_task['url'], '/v1/responses')
            self.assertEqual(first_task['body']['prompt']['id'], 'test_prompt')
            self.assertEqual(first_task['body']['prompt']['version'], 'v1.0')
            self.assertEqual(first_task['body']['prompt']['variables']['artist_name'], 'NewJeans')
    
    def test_conversion_with_limit(self):
        """Test conversion with limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.csv"
            output_path = Path(tmpdir) / "output.jsonl"
            
            # Create test CSV with 3 rows
            input_path.write_text("""artist_id,artist_name,artist_data
a1,Artist One,Data one
a2,Artist Two,Data two
a3,Artist Three,Data three""")
            
            # Convert with limit of 2
            stats = convert_csv_to_jsonl(
                input_path=input_path,
                output_path=output_path,
                prompt_id="test",
                prompt_version="v1",
                limit=2
            )
            
            # Check only 2 rows processed
            self.assertEqual(stats.written, 2)
            
            output_lines = output_path.read_text().strip().split('\n')
            self.assertEqual(len(output_lines), 2)
    
    def test_conversion_with_invalid_rows(self):
        """Test conversion with some invalid rows."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.csv"
            output_path = Path(tmpdir) / "output.jsonl"
            
            # Create test CSV with invalid row (empty name)
            input_path.write_text("""artist_id,artist_name,artist_data
a1,Valid Artist,Valid data
a2,,Invalid data
a3,Another Valid,More valid data""")
            
            # Convert in non-strict mode
            with patch('logging.warning'):
                stats = convert_csv_to_jsonl(
                    input_path=input_path,
                    output_path=output_path,
                    prompt_id="test",
                    prompt_version="v1",
                    strict=False
                )
            
            # Should skip invalid row
            self.assertEqual(stats.read, 2)  # Only valid rows counted in read
            self.assertEqual(stats.written, 2)
            self.assertEqual(stats.skipped, 0)
            
            output_lines = output_path.read_text().strip().split('\n')
            self.assertEqual(len(output_lines), 2)


class TestGetConfigValue(unittest.TestCase):
    """Test the get_config_value function."""
    
    def test_cli_arg_takes_precedence(self):
        """Test that CLI argument takes precedence over environment variable."""
        with patch.dict(os.environ, {'TEST_VAR': 'env_value'}):
            result = get_config_value('cli_value', 'TEST_VAR', 'test_param')
            self.assertEqual(result, 'cli_value')
    
    def test_env_var_when_no_cli_arg(self):
        """Test using environment variable when no CLI arg provided."""
        with patch.dict(os.environ, {'TEST_VAR': 'env_value'}):
            result = get_config_value(None, 'TEST_VAR', 'test_param')
            self.assertEqual(result, 'env_value')
    
    def test_required_parameter_missing(self):
        """Test error when required parameter is missing from both sources."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as cm:
                get_config_value(None, 'MISSING_VAR', 'test_param')
            
            self.assertIn('test_param must be provided', str(cm.exception))
            self.assertIn('--test-param', str(cm.exception))
            self.assertIn('MISSING_VAR', str(cm.exception))
    
    def test_optional_parameter_returns_none(self):
        """Test that optional parameter returns None when missing."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_config_value(None, 'MISSING_VAR', 'test_param', required=False)
            self.assertIsNone(result)
    
    def test_optional_parameter_with_cli_arg(self):
        """Test optional parameter with CLI argument provided."""
        result = get_config_value('cli_value', 'MISSING_VAR', 'test_param', required=False)
        self.assertEqual(result, 'cli_value')
    
    def test_optional_parameter_with_env_var(self):
        """Test optional parameter with environment variable provided."""
        with patch.dict(os.environ, {'TEST_VAR': 'env_value'}):
            result = get_config_value(None, 'TEST_VAR', 'test_param', required=False)
            self.assertEqual(result, 'env_value')
    
    def test_empty_string_cli_arg_required(self):
        """Test that empty string CLI arg raises error when required."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                get_config_value('', 'TEST_VAR', 'test_param')
    
    def test_empty_string_cli_arg_optional(self):
        """Test that empty string CLI arg returns None when optional."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_config_value('', 'TEST_VAR', 'test_param', required=False)
            self.assertIsNone(result)
    
    def test_empty_string_env_var_required(self):
        """Test that empty string env var raises error when required."""
        with patch.dict(os.environ, {'TEST_VAR': ''}):
            with self.assertRaises(ValueError):
                get_config_value(None, 'TEST_VAR', 'test_param')
    
    def test_empty_string_env_var_optional(self):
        """Test that empty string env var returns None when optional."""
        with patch.dict(os.environ, {'TEST_VAR': ''}):
            result = get_config_value(None, 'TEST_VAR', 'test_param', required=False)
            self.assertIsNone(result)


class TestConvertCsvToJsonlOptionalVersion(unittest.TestCase):
    """Test CSV to JSONL conversion with optional prompt version."""
    
    def test_conversion_without_prompt_version(self):
        """Test conversion without prompt version."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.csv"
            output_path = Path(tmpdir) / "output.jsonl"
            
            # Create test CSV
            input_path.write_text("""artist_id,artist_name,artist_data
a1,NewJeans,K-pop group
a2,Stereolab,Post-rock band""")
            
            # Convert without version
            stats = convert_csv_to_jsonl(
                input_path=input_path,
                output_path=output_path,
                prompt_id="test_prompt",
                prompt_version=None
            )
            
            # Check stats
            self.assertEqual(stats.read, 2)
            self.assertEqual(stats.written, 2)
            self.assertEqual(stats.skipped, 0)
            
            # Check output
            output_lines = output_path.read_text().strip().split('\n')
            self.assertEqual(len(output_lines), 2)
            
            # Parse first line and verify no version field
            first_task = json.loads(output_lines[0])
            self.assertEqual(first_task['custom_id'], 'a1')
            self.assertEqual(first_task['body']['prompt']['id'], 'test_prompt')
            self.assertNotIn('version', first_task['body']['prompt'])
            self.assertEqual(first_task['body']['prompt']['variables']['artist_name'], 'NewJeans')
    
    def test_conversion_with_prompt_version(self):
        """Test conversion with prompt version still works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.csv"
            output_path = Path(tmpdir) / "output.jsonl"
            
            # Create test CSV
            input_path.write_text("""artist_id,artist_name,artist_data
a1,Artist One,Data one""")
            
            # Convert with version
            stats = convert_csv_to_jsonl(
                input_path=input_path,
                output_path=output_path,
                prompt_id="test_prompt",
                prompt_version="v1.0"
            )
            
            # Check output includes version
            output_lines = output_path.read_text().strip().split('\n')
            first_task = json.loads(output_lines[0])
            self.assertEqual(first_task['body']['prompt']['version'], 'v1.0')


class TestMainFunctionOptionalVersion(unittest.TestCase):
    """Test main function with optional PROMPT_VERSION."""
    
    def test_main_with_prompt_version_env_var(self):
        """Test main function with PROMPT_VERSION environment variable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.csv"
            output_path = Path(tmpdir) / "output.jsonl"
            
            # Create test CSV
            input_path.write_text("""artist_id,artist_name,artist_data
a1,Test Artist,Test data""")
            
            # Mock sys.argv and environment
            test_args = [
                'gen_batch_jsonl.py',
                '--in', str(input_path),
                '--out', str(output_path),
                '--prompt-id', 'test_prompt',
                '--prompt-version', 'v2.0'
            ]
            
            with patch('sys.argv', test_args):
                with patch('logging.info') as mock_log:
                    exit_code = main()
            
            # Check success
            self.assertEqual(exit_code, 0)
            
            # Check that version was logged
            log_calls = [call.args[0] for call in mock_log.call_args_list]
            version_logged = any('prompt_version: v2.0' in call for call in log_calls)
            self.assertTrue(version_logged)
            
            # Check output file
            self.assertTrue(output_path.exists())
            output_lines = output_path.read_text().strip().split('\n')
            first_task = json.loads(output_lines[0])
            self.assertEqual(first_task['body']['prompt']['version'], 'v2.0')
    
    def test_main_without_prompt_version(self):
        """Test main function without PROMPT_VERSION."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.csv"
            output_path = Path(tmpdir) / "output.jsonl"
            
            # Create test CSV
            input_path.write_text("""artist_id,artist_name,artist_data
a1,Test Artist,Test data""")
            
            # Mock sys.argv without version
            test_args = [
                'gen_batch_jsonl.py',
                '--in', str(input_path),
                '--out', str(output_path),
                '--prompt-id', 'test_prompt'
            ]
            
            # Ensure no PROMPT_VERSION in environment
            with patch.dict(os.environ, {}, clear=True):
                os.environ['PROMPT_ID'] = 'test_prompt'  # Required, so set it
                
                with patch('sys.argv', test_args):
                    with patch('logging.info') as mock_log:
                        exit_code = main()
            
            # Check success
            self.assertEqual(exit_code, 0)
            
            # Check that "no version specified" was logged
            log_calls = [call.args[0] for call in mock_log.call_args_list]
            no_version_logged = any('no version specified' in call for call in log_calls)
            self.assertTrue(no_version_logged)
            
            # Check output file has no version
            self.assertTrue(output_path.exists())
            output_lines = output_path.read_text().strip().split('\n')
            first_task = json.loads(output_lines[0])
            self.assertNotIn('version', first_task['body']['prompt'])
    
    def test_main_with_prompt_version_from_env(self):
        """Test main function with PROMPT_VERSION from environment variable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.csv"
            output_path = Path(tmpdir) / "output.jsonl"
            
            # Create test CSV
            input_path.write_text("""artist_id,artist_name,artist_data
a1,Test Artist,Test data""")
            
            # Mock sys.argv without version argument
            test_args = [
                'gen_batch_jsonl.py',
                '--in', str(input_path),
                '--out', str(output_path),
                '--prompt-id', 'test_prompt'
            ]
            
            # Set version via environment variable
            with patch.dict(os.environ, {'PROMPT_VERSION': 'v3.0'}):
                with patch('sys.argv', test_args):
                    with patch('logging.info') as mock_log:
                        exit_code = main()
            
            # Check success
            self.assertEqual(exit_code, 0)
            
            # Check that version from env was logged
            log_calls = [call.args[0] for call in mock_log.call_args_list]
            version_logged = any('prompt_version: v3.0' in call for call in log_calls)
            self.assertTrue(version_logged)
            
            # Check output file has version
            self.assertTrue(output_path.exists())
            output_lines = output_path.read_text().strip().split('\n')
            first_task = json.loads(output_lines[0])
            self.assertEqual(first_task['body']['prompt']['version'], 'v3.0')


if __name__ == '__main__':
    unittest.main()