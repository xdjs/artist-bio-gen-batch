#!/usr/bin/env python3
"""
CLI tool to convert CSV of artist data to OpenAI Batch API JSONL format.

Usage:
    python gen_batch_jsonl.py --in input.csv --out output.jsonl --prompt-id <id> --prompt-version <ver>
"""

import argparse
import csv
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, Iterator


@dataclass
class ConversionStats:
    """Statistics from the CSV to JSONL conversion process."""
    read: int
    written: int
    skipped: int


def build_task_row(
    artist_id: str,
    artist_name: str,
    artist_data: str,
    prompt_id: str,
    prompt_version: Optional[str] = None
) -> Dict[str, Any]:
    """Build a single JSONL task row for the OpenAI Batch API."""
    prompt = {
        "id": prompt_id,
        "variables": {
            "artist_name": artist_name,
            "artist_data": artist_data
        }
    }
    
    if prompt_version:
        prompt["version"] = prompt_version
    
    return {
        "custom_id": artist_id,
        "method": "POST",
        "url": "/v1/responses",
        "body": {
            "prompt": prompt
        }
    }


def validate_row(artist_id: str, artist_name: str, artist_data: str) -> bool:
    """Validate that a CSV row has required fields."""
    if not artist_id or not artist_id.strip():
        return False
    if not artist_name or not artist_name.strip():
        return False
    return True


def process_csv_rows(
    csv_file,
    has_header: bool,
    limit: Optional[int] = None,
    strict: bool = False
) -> Iterator[Dict[str, str]]:
    """Process CSV rows and yield normalized artist data."""
    if has_header:
        reader = csv.DictReader(csv_file)
        expected_columns = {'artist_id', 'artist_name', 'artist_data'}
        
        if not expected_columns.issubset(set(reader.fieldnames or [])):
            raise ValueError(
                f"CSV header must contain: {', '.join(sorted(expected_columns))}. "
                f"Found: {', '.join(reader.fieldnames or [])}"
            )
    else:
        reader = csv.reader(csv_file)
    
    rows_processed = 0
    
    for row_num, row in enumerate(reader, start=1):
        if limit is not None and rows_processed >= limit:
            break
            
        try:
            if has_header:
                artist_id = row['artist_id'].strip()
                artist_name = row['artist_name'].strip()
                artist_data = row['artist_data'].strip()
            else:
                if len(row) < 3:
                    raise ValueError(f"Row {row_num}: Expected 3 columns, got {len(row)}")
                artist_id = row[0].strip()
                artist_name = row[1].strip()
                artist_data = row[2].strip()
            
            if not validate_row(artist_id, artist_name, artist_data):
                error_msg = f"Row {row_num}: artist_id and artist_name are required"
                if strict:
                    raise ValueError(error_msg)
                logging.warning(error_msg)
                continue
            
            yield {
                'artist_id': artist_id,
                'artist_name': artist_name,
                'artist_data': artist_data
            }
            rows_processed += 1
            
        except Exception as e:
            error_msg = f"Row {row_num}: {str(e)}"
            if strict:
                raise ValueError(error_msg)
            logging.warning(error_msg)


def convert_csv_to_jsonl(
    input_path: Path,
    output_path: Path,
    prompt_id: str,
    prompt_version: str,
    limit: Optional[int] = None,
    skip_header: bool = False,
    strict: bool = False
) -> ConversionStats:
    """Convert CSV file to JSONL format for OpenAI Batch API."""
    stats = ConversionStats(read=0, written=0, skipped=0)
    
    try:
        with open(input_path, 'r', encoding='utf-8') as infile, \
             open(output_path, 'w', encoding='utf-8') as outfile:
            
            has_header = not skip_header
            
            for row_data in process_csv_rows(infile, has_header, limit, strict):
                stats.read += 1
                
                try:
                    task_row = build_task_row(
                        row_data['artist_id'],
                        row_data['artist_name'],
                        row_data['artist_data'],
                        prompt_id,
                        prompt_version
                    )
                    
                    json_line = json.dumps(task_row, ensure_ascii=False)
                    outfile.write(json_line + '\n')
                    stats.written += 1
                    
                except Exception as e:
                    error_msg = f"Failed to write row for artist_id {row_data['artist_id']}: {e}"
                    if strict:
                        raise ValueError(error_msg)
                    logging.warning(error_msg)
                    stats.skipped += 1
                    
    except FileNotFoundError:
        raise ValueError(f"Input file not found: {input_path}")
    except PermissionError:
        raise ValueError(f"Permission denied accessing files")
    except UnicodeDecodeError:
        raise ValueError(f"Input file must be UTF-8 encoded: {input_path}")
    
    return stats


def get_config_value(arg_value: Optional[str], env_var: str, name: str, required: bool = True) -> Optional[str]:
    """Get configuration value from CLI arg or environment variable."""
    if arg_value:
        return arg_value
    
    env_value = os.getenv(env_var)
    if env_value:
        return env_value
    
    if required:
        raise ValueError(f"{name} must be provided via --{name.lower().replace('_', '-')} or {env_var} environment variable")
    
    return None


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(levelname)s: %(message)s'
    )


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description='Convert CSV of artist data to OpenAI Batch API JSONL format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --in artists.csv --out batch.jsonl --prompt-id bio_gen --prompt-version v1.0
  %(prog)s --in data.csv --out output.jsonl --prompt-id gen --prompt-version v2 --limit 10
  PROMPT_ID=bio_gen PROMPT_VERSION=v1.0 %(prog)s --in data.csv --out output.jsonl
        """
    )
    
    parser.add_argument(
        '--in',
        dest='input_file',
        required=True,
        type=Path,
        help='Input CSV file path'
    )
    
    parser.add_argument(
        '--out',
        dest='output_file',
        required=True,
        type=Path,
        help='Output JSONL file path'
    )
    
    parser.add_argument(
        '--prompt-id',
        help='Prompt ID (or use PROMPT_ID env var)'
    )
    
    parser.add_argument(
        '--prompt-version',
        help='Prompt version (or use PROMPT_VERSION env var)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        help='Process only first N data rows (for dry runs)'
    )
    
    parser.add_argument(
        '--skip-header',
        action='store_true',
        help='Skip CSV header row (assume artist_id,artist_name,artist_data order)'
    )
    
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Fail if any row is invalid (default: log and skip bad rows)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    try:
        prompt_id = get_config_value(args.prompt_id, 'PROMPT_ID', 'prompt_id')
        prompt_version = get_config_value(args.prompt_version, 'PROMPT_VERSION', 'prompt_version', required=False)
        
        logging.info(f"Converting {args.input_file} to {args.output_file}")
        if prompt_version:
            logging.info(f"Using prompt_id: {prompt_id}, prompt_version: {prompt_version}")
        else:
            logging.info(f"Using prompt_id: {prompt_id} (no version specified)")
        
        if args.limit:
            logging.info(f"Limiting to first {args.limit} rows")
        
        stats = convert_csv_to_jsonl(
            input_path=args.input_file,
            output_path=args.output_file,
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            limit=args.limit,
            skip_header=args.skip_header,
            strict=args.strict
        )
        
        logging.info(f"Conversion complete: {stats.read} rows read, {stats.written} written, {stats.skipped} skipped")
        return 0
        
    except ValueError as e:
        logging.error(str(e))
        return 1
    except KeyboardInterrupt:
        logging.info("Conversion interrupted by user")
        return 1
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())