#!/usr/bin/env python3
"""
OpenAI Batch API CLI tool for creating, monitoring, retrieving, cancelling, and listing batch jobs.

Usage:
    python batch_tool.py create --in input.jsonl
    python batch_tool.py status --batch-id batch_123
    python batch_tool.py retrieve --batch-id batch_123 --out results.jsonl
    python batch_tool.py cancel --batch-id batch_123
    python batch_tool.py list --limit 10
"""

import argparse
import io
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from openai import OpenAI
except ImportError:
    print("Error: OpenAI SDK not installed. Install with: pip install openai", file=sys.stderr)
    sys.exit(1)


def setup_logger(log_path: Path) -> logging.Logger:
    """Set up file logger with immediate flushing."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger('batch_tool')
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create file handler with immediate flushing
    handler = logging.FileHandler(log_path)
    handler.setLevel(logging.INFO)
    
    # Set format
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    
    # Force immediate flush
    handler.flush = lambda: handler.stream.flush() if handler.stream else None
    
    logger.addHandler(handler)
    return logger


def upload_file(client: OpenAI, file_path: Path, logger: logging.Logger, verbose: bool = False) -> str:
    """Upload file to OpenAI and return file ID."""
    logger.info(f"UPLOAD - Starting file upload: {file_path}")
    
    try:
        with open(file_path, "rb") as file:
            response = client.files.create(
                file=file,
                purpose="batch"
            )
        
        file_id = response.id
        logger.info(f"UPLOAD - Success: file_id={file_id}")
        logger.info(f"UPLOAD - Response: {response.model_dump()}")
        
        if verbose:
            print(f"\nRaw API Response (upload_file):")
            try:
                print(json.dumps(response.model_dump(), indent=2))
            except (TypeError, ValueError) as e:
                print(f"Unable to serialize response: {e}")
                print(f"Response: {response.model_dump()}")
            print()
        
        return file_id
        
    except Exception as e:
        logger.error(f"UPLOAD - Failed: {str(e)}")
        raise


def create_batch(client: OpenAI, file_id: str, endpoint: str, completion_window: str, logger: logging.Logger, verbose: bool = False) -> Dict[str, Any]:
    """Create a batch job and return batch info."""
    logger.info(f"CREATE_BATCH - Starting batch creation: file_id={file_id}, endpoint={endpoint}, window={completion_window}")
    
    try:
        response = client.batches.create(
            input_file_id=file_id,
            endpoint=endpoint,
            completion_window=completion_window
        )
        
        batch_dict = response.model_dump()
        batch_id = batch_dict['id']
        
        logger.info(f"CREATE_BATCH - Success: batch_id={batch_id}")
        logger.info(f"CREATE_BATCH - Response: {batch_dict}")
        
        if verbose:
            print(f"\nRaw API Response (create_batch):")
            try:
                print(json.dumps(batch_dict, indent=2))
            except (TypeError, ValueError) as e:
                print(f"Unable to serialize response: {e}")
                print(f"Response: {batch_dict}")
            print()
        
        return batch_dict
        
    except Exception as e:
        logger.error(f"CREATE_BATCH - Failed: {str(e)}")
        raise


def get_batch_status(client: OpenAI, batch_id: str, logger: logging.Logger, verbose: bool = False) -> Dict[str, Any]:
    """Get batch status and return batch info."""
    logger.info(f"GET_STATUS - Retrieving status for batch_id={batch_id}")
    
    try:
        response = client.batches.retrieve(batch_id)
        batch_dict = response.model_dump()
        
        status = batch_dict.get('status', 'unknown')
        logger.info(f"GET_STATUS - Success: status={status}")
        logger.info(f"GET_STATUS - Response: {batch_dict}")
        
        if verbose:
            print(f"\nRaw API Response (get_batch_status):")
            try:
                print(json.dumps(batch_dict, indent=2))
            except (TypeError, ValueError) as e:
                print(f"Unable to serialize response: {e}")
                print(f"Response: {batch_dict}")
            print()
        
        return batch_dict
        
    except Exception as e:
        logger.error(f"GET_STATUS - Failed: {str(e)}")
        raise


def cancel_batch(client: OpenAI, batch_id: str, logger: logging.Logger, verbose: bool = False) -> Dict[str, Any]:
    """Cancel a batch job and return batch info."""
    logger.info(f"CANCEL_BATCH - Starting batch cancellation: batch_id={batch_id}")
    
    try:
        response = client.batches.cancel(batch_id)
        batch_dict = response.model_dump()
        
        status = batch_dict.get('status', 'unknown')
        logger.info(f"CANCEL_BATCH - Success: status={status}")
        logger.info(f"CANCEL_BATCH - Response: {batch_dict}")
        
        if verbose:
            print(f"\nRaw API Response (cancel_batch):")
            try:
                print(json.dumps(batch_dict, indent=2))
            except (TypeError, ValueError) as e:
                print(f"Unable to serialize response: {e}")
                print(f"Response: {batch_dict}")
            print()
        
        return batch_dict
        
    except Exception as e:
        logger.error(f"CANCEL_BATCH - Failed: {str(e)}")
        raise


def list_batches(client: OpenAI, limit: Optional[int], logger: logging.Logger, verbose: bool = False) -> list:
    """List batch jobs and return list of batch info."""
    logger.info(f"LIST_BATCHES - Starting batch listing with limit={limit}")
    
    try:
        batches = []
        # Use the paginated list method
        batch_list = client.batches.list(limit=limit) if limit else client.batches.list()
        
        for batch in batch_list:
            batch_dict = batch.model_dump()
            batches.append(batch_dict)
        
        logger.info(f"LIST_BATCHES - Success: retrieved {len(batches)} batches")
        logger.info(f"LIST_BATCHES - Batch IDs: {[b.get('id', 'unknown') for b in batches]}")
        
        if verbose:
            print(f"\nRaw API Response (list_batches):")
            try:
                print(json.dumps(batches, indent=2))
            except (TypeError, ValueError) as e:
                print(f"Unable to serialize response: {e}")
                print(f"Response: {batches}")
            print()
        
        return batches
        
    except Exception as e:
        logger.error(f"LIST_BATCHES - Failed: {str(e)}")
        raise


def download_results(client: OpenAI, output_file_id: str, out_path: Path, logger: logging.Logger) -> int:
    """Download batch results and return byte count."""
    logger.info(f"DOWNLOAD_RESULTS - Starting download: output_file_id={output_file_id}, out_path={out_path}")
    
    try:
        # Ensure output directory exists
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if file exists and warn about overwrite
        if out_path.exists():
            logger.warning(f"DOWNLOAD_RESULTS - Overwriting existing file: {out_path}")
        
        # Download content
        content = client.files.content(output_file_id)
        
        # Write to file
        with open(out_path, 'wb') as f:
            f.write(content.content)
        
        byte_count = len(content.content)
        logger.info(f"DOWNLOAD_RESULTS - Success: saved {byte_count} bytes to {out_path}")
        
        return byte_count
        
    except Exception as e:
        logger.error(f"DOWNLOAD_RESULTS - Failed: {str(e)}")
        raise


def cmd_create(args: argparse.Namespace, client: OpenAI, logger: logging.Logger) -> int:
    """Handle create subcommand."""
    input_path = Path(args.input_file)
    
    # Validate input file
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        logger.error(f"Input file not found: {input_path}")
        return 1
    
    if not input_path.is_file():
        print(f"Error: Input path is not a file: {input_path}", file=sys.stderr)
        logger.error(f"Input path is not a file: {input_path}")
        return 1
    
    try:
        # Upload file
        file_id = upload_file(client, input_path, logger, args.verbose)
        
        # Create batch
        batch_info = create_batch(client, file_id, args.endpoint, args.completion_window, logger, args.verbose)
        batch_id = batch_info['id']
        
        # Output to stdout
        print(f"File ID: {file_id}")
        print(f"Batch ID: {batch_id}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        logger.error(f"Create command failed: {str(e)}")
        return 1


def cmd_status(args: argparse.Namespace, client: OpenAI, logger: logging.Logger) -> int:
    """Handle status subcommand."""
    try:
        # Get batch status
        batch_info = get_batch_status(client, args.batch_id, logger, args.verbose)
        
        # Print status info to stdout
        status = batch_info.get('status', 'unknown')
        print(f"Status: {status}")
        
        if 'created_at' in batch_info:
            created_dt = datetime.fromtimestamp(batch_info['created_at'])
            print(f"Created: {created_dt.isoformat()}")
        
        if 'completed_at' in batch_info and batch_info['completed_at']:
            completed_dt = datetime.fromtimestamp(batch_info['completed_at'])
            print(f"Completed: {completed_dt.isoformat()}")
        
        # Auto-save if completed and auto-save is enabled
        if status == 'completed' and args.auto_save:
            output_file_id = batch_info.get('output_file_id')
            if output_file_id:
                output_path = Path(f"results_{args.batch_id}.jsonl")
                try:
                    byte_count = download_results(client, output_file_id, output_path, logger)
                    print(f"Results saved: {output_path} ({byte_count} bytes)")
                except Exception as e:
                    print(f"Warning: Failed to auto-save results: {str(e)}", file=sys.stderr)
                    logger.error(f"Auto-save failed: {str(e)}")
            else:
                print("Warning: Batch completed but no output_file_id found", file=sys.stderr)
                logger.warning("Batch completed but no output_file_id found")
        
        return 0
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        logger.error(f"Status command failed: {str(e)}")
        return 1


def cmd_retrieve(args: argparse.Namespace, client: OpenAI, logger: logging.Logger) -> int:
    """Handle retrieve subcommand."""
    try:
        # Get batch status first
        batch_info = get_batch_status(client, args.batch_id, logger, args.verbose)
        status = batch_info.get('status', 'unknown')
        
        if status != 'completed':
            print(f"Error: Batch not completed (status: {status})", file=sys.stderr)
            logger.error(f"Attempted to retrieve incomplete batch: status={status}")
            return 1
        
        # Get output file ID
        output_file_id = batch_info.get('output_file_id')
        if not output_file_id:
            print("Error: Batch completed but no output_file_id found", file=sys.stderr)
            logger.error("Batch completed but no output_file_id found")
            return 1
        
        # Determine output path
        output_path = Path(args.out) if args.out else Path(f"results_{args.batch_id}.jsonl")
        
        # Download results
        byte_count = download_results(client, output_file_id, output_path, logger)
        
        # Output to stdout
        print(f"Results saved: {output_path}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        logger.error(f"Retrieve command failed: {str(e)}")
        return 1


def cmd_cancel(args: argparse.Namespace, client: OpenAI, logger: logging.Logger) -> int:
    """Handle cancel subcommand."""
    try:
        # Cancel the batch
        batch_info = cancel_batch(client, args.batch_id, logger, args.verbose)
        status = batch_info.get('status', 'unknown')
        
        # Output to stdout
        print(f"Batch cancellation initiated: {args.batch_id}")
        print(f"Status: {status}")
        
        # Show additional info if available
        if 'created_at' in batch_info:
            from datetime import datetime
            created_at = datetime.fromtimestamp(batch_info['created_at']).strftime('%Y-%m-%d %H:%M:%S')
            print(f"Created: {created_at}")
        
        if status == 'cancelled':
            print("Note: Batch was successfully cancelled. Any completed requests have been processed and you will be charged for them.")
        elif status == 'cancelling':
            print("Note: Batch cancellation in progress. This may take up to 10 minutes.")
        
        return 0
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        logger.error(f"Cancel command failed: {str(e)}")
        return 1


def cmd_list(args: argparse.Namespace, client: OpenAI, logger: logging.Logger) -> int:
    """Handle list subcommand."""
    try:
        # List all batches
        batches = list_batches(client, args.limit, logger, args.verbose)
        
        if not batches:
            print("No batch jobs found.")
            return 0
        
        # Display header
        print(f"Found {len(batches)} batch job(s):\n")
        
        # Display batches in a table format
        for i, batch in enumerate(batches, 1):
            batch_id = batch.get('id', 'unknown')
            status = batch.get('status', 'unknown')
            endpoint = batch.get('endpoint', 'unknown')
            
            print(f"{i}. Batch ID: {batch_id}")
            print(f"   Status: {status}")
            print(f"   Endpoint: {endpoint}")
            
            # Show creation time
            if 'created_at' in batch:
                from datetime import datetime
                created_at = datetime.fromtimestamp(batch['created_at']).strftime('%Y-%m-%d %H:%M:%S')
                print(f"   Created: {created_at}")
            
            # Show completion time if available
            if 'completed_at' in batch and batch['completed_at']:
                completed_at = datetime.fromtimestamp(batch['completed_at']).strftime('%Y-%m-%d %H:%M:%S')
                print(f"   Completed: {completed_at}")
            
            # Show request counts if available
            if 'request_counts' in batch:
                counts = batch['request_counts']
                total = counts.get('total', 0)
                completed = counts.get('completed', 0)
                failed = counts.get('failed', 0)
                print(f"   Requests: {completed}/{total} completed, {failed} failed")
            
            print()  # Empty line between batches
        
        return 0
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        logger.error(f"List command failed: {str(e)}")
        return 1


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    # Create parent parser with common arguments
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        '--log-file',
        type=Path,
        help='Log file path (default: logs/batch_YYYYMMDD_HHMMSS.log)'
    )
    parent_parser.add_argument(
        '--verbose',
        action='store_true',
        help='Display raw API responses'
    )
    
    # Main parser
    parser = argparse.ArgumentParser(
        description='OpenAI Batch API CLI tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s create --in requests.jsonl --endpoint "/v1/responses" --completion-window 24h
  %(prog)s status --batch-id batch_abc123 --verbose
  %(prog)s retrieve --batch-id batch_abc123 --out my_results.jsonl --verbose
  %(prog)s cancel --batch-id batch_abc123 --verbose
  %(prog)s list --limit 10 --verbose
        """
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    subparsers.required = True
    
    # Create subcommand
    create_parser = subparsers.add_parser('create', help='Upload file and create batch', parents=[parent_parser])
    create_parser.add_argument('--in', dest='input_file', required=True, help='Input JSONL file path')
    create_parser.add_argument('--endpoint', default='/v1/responses', help='API endpoint (default: /v1/responses)')
    create_parser.add_argument('--completion-window', default='24h', help='Completion window (default: 24h)')
    
    # Status subcommand
    status_parser = subparsers.add_parser('status', help='Check batch status', parents=[parent_parser])
    status_parser.add_argument('--batch-id', required=True, help='Batch ID to check')
    status_parser.add_argument('--auto-save', action='store_true', default=True, help='Auto-save results if completed (default: on)')
    status_parser.add_argument('--no-auto-save', dest='auto_save', action='store_false', help='Disable auto-save')
    
    # Retrieve subcommand
    retrieve_parser = subparsers.add_parser('retrieve', help='Retrieve batch results', parents=[parent_parser])
    retrieve_parser.add_argument('--batch-id', required=True, help='Batch ID to retrieve')
    retrieve_parser.add_argument('--out', help='Output file path (default: results_<batch_id>.jsonl)')
    
    # Cancel subcommand
    cancel_parser = subparsers.add_parser('cancel', help='Cancel batch job', parents=[parent_parser])
    cancel_parser.add_argument('--batch-id', required=True, help='Batch ID to cancel')
    
    # List subcommand
    list_parser = subparsers.add_parser('list', help='List all batch jobs', parents=[parent_parser])
    list_parser.add_argument('--limit', type=int, help='Maximum number of batches to retrieve')
    
    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set", file=sys.stderr)
        return 1
    
    # Set up logging
    if args.log_file:
        log_path = args.log_file
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_path = Path(f'logs/batch_{timestamp}.log')
    
    logger = setup_logger(log_path)
    logger.info(f"Starting batch_tool - Command: {args.command}")
    
    # Initialize OpenAI client
    try:
        client = OpenAI(api_key=api_key)
        logger.info("OpenAI client initialized successfully")
    except Exception as e:
        print(f"Error: Failed to initialize OpenAI client: {str(e)}", file=sys.stderr)
        logger.error(f"Failed to initialize OpenAI client: {str(e)}")
        return 1
    
    # Dispatch to appropriate command handler
    try:
        if args.command == 'create':
            return cmd_create(args, client, logger)
        elif args.command == 'status':
            return cmd_status(args, client, logger)
        elif args.command == 'retrieve':
            return cmd_retrieve(args, client, logger)
        elif args.command == 'cancel':
            return cmd_cancel(args, client, logger)
        elif args.command == 'list':
            return cmd_list(args, client, logger)
        else:
            print(f"Error: Unknown command: {args.command}", file=sys.stderr)
            return 1
    except KeyboardInterrupt:
        print("\nOperation interrupted by user", file=sys.stderr)
        logger.info("Operation interrupted by user")
        return 1
    except Exception as e:
        print(f"Error: Unexpected error: {str(e)}", file=sys.stderr)
        logger.error(f"Unexpected error: {str(e)}")
        return 1
    finally:
        logger.info(f"Batch tool finished - Command: {args.command}")


if __name__ == '__main__':
    sys.exit(main())