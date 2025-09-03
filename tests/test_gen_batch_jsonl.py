#!/usr/bin/env python3
"""
Tests for gen_batch_jsonl.py
"""

import io
import json
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


if __name__ == '__main__':
    unittest.main()