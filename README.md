# Artist Bio Generator - Batch Processing Tools

A collection of Python CLI tools for processing artist data with OpenAI's Batch API:

1. **`gen_batch_jsonl.py`** - Converts CSV files of artist data into OpenAI Batch API JSONL format
2. **`batch_tool.py`** - Manages OpenAI Batch API operations (create, status, retrieve, cancel)

## Requirements

- Python 3.11+
- For `gen_batch_jsonl.py`: No external dependencies (uses standard library only)
- For `batch_tool.py`: 
  - OpenAI Python SDK (`pip install openai`)
  - OpenAI API key (set via `OPENAI_API_KEY` environment variable)

## Installation

```bash
git clone <repository-url>
cd artist-bio-gen-batch-claude

# Install OpenAI SDK for batch_tool.py
pip install openai

# Set your OpenAI API key
export OPENAI_API_KEY=your_api_key_here
```

## Complete Workflow

Here's how to use both tools together for end-to-end batch processing:

```bash
# 1. Convert CSV to JSONL format
python gen_batch_jsonl.py --in artists.csv --out batch_requests.jsonl --prompt-id bio_gen --prompt-version v1.0

# 2. Create batch job
python batch_tool.py create --in batch_requests.jsonl
# Output: File ID: file-abc123, Batch ID: batch-def456

# 3. Check status (auto-saves results when completed)
python batch_tool.py status --batch-id batch-def456
# Output: Status: completed, Results saved: results_batch-def456.jsonl

# 4. Or manually retrieve results
python batch_tool.py retrieve --batch-id batch-def456 --out final_results.jsonl

# 5. Or cancel if needed (charges apply for completed work)
python batch_tool.py cancel --batch-id batch-def456
```

---

# Tool 1: CSV to JSONL Converter (`gen_batch_jsonl.py`)

Converts CSV files of artist data into OpenAI Batch API JSONL format.

## Basic Usage

```bash
# With prompt version
python gen_batch_jsonl.py --in input.csv --out output.jsonl --prompt-id bio_gen --prompt-version v1.0

# Without prompt version (version field omitted from JSON)
python gen_batch_jsonl.py --in input.csv --out output.jsonl --prompt-id bio_gen
```

## Configuration Options

### Environment Variables
```bash
export PROMPT_ID=bio_gen
export PROMPT_VERSION=v1.0
python gen_batch_jsonl.py --in input.csv --out output.jsonl
```

### Advanced Flags
```bash
# Limit processing to first 10 rows (for testing)
python gen_batch_jsonl.py --in input.csv --out output.jsonl --prompt-id bio_gen --prompt-version v1.0 --limit 10

# Process CSV without header (assumes artist_id,artist_name,artist_data order)
python gen_batch_jsonl.py --in input.csv --out output.jsonl --prompt-id bio_gen --prompt-version v1.0 --skip-header

# Strict mode: fail if any row is invalid (default: skip bad rows)
python gen_batch_jsonl.py --in input.csv --out output.jsonl --prompt-id bio_gen --prompt-version v1.0 --strict

# Verbose logging
python gen_batch_jsonl.py --in input.csv --out output.jsonl --prompt-id bio_gen --prompt-version v1.0 --verbose
```

## Input CSV Format

The input CSV must have these columns (header required unless using `--skip-header`):

- `artist_id`: Unique identifier (required, non-empty)
- `artist_name`: Artist name (required, non-empty) 
- `artist_data`: Additional data (can be empty, supports JSON strings)

### Example CSV:

```csv
artist_id,artist_name,artist_data
a1,NewJeans,"K-pop group; ADOR; 'Supernatural' era"
a2,Stereolab,"Franco-UK post-rock; ""Dots and Loops"""
a3,Perfume,"Japanese technopop trio
Known for 'love the world'"
```

## Output JSONL Format

Each line in the output file will be a JSON object formatted for the OpenAI Batch API:

**With prompt version:**
```json
{
  "custom_id": "a1",
  "method": "POST", 
  "url": "/v1/responses",
  "body": {
    "prompt": {
      "id": "bio_gen",
      "version": "v1.0",
      "variables": {
        "artist_name": "NewJeans",
        "artist_data": "K-pop group; ADOR; 'Supernatural' era"
      }
    }
  }
}
```

**Without prompt version (when `--prompt-version` is omitted):**
```json
{
  "custom_id": "a1",
  "method": "POST", 
  "url": "/v1/responses",
  "body": {
    "prompt": {
      "id": "bio_gen",
      "variables": {
        "artist_name": "NewJeans",
        "artist_data": "K-pop group; ADOR; 'Supernatural' era"
      }
    }
  }
}
```

## Configuration

Configuration can be provided via CLI flags (higher priority) or environment variables:

| CLI Flag | Environment Variable | Description | Required |
|----------|---------------------|-------------|----------|
| `--prompt-id` | `PROMPT_ID` | Prompt identifier | Yes |
| `--prompt-version` | `PROMPT_VERSION` | Prompt version | No (optional) |

## Error Handling

- **Non-strict mode (default)**: Invalid rows are logged and skipped, processing continues
- **Strict mode (`--strict`)**: Any invalid row causes the entire process to fail
- **Exit codes**: 0 for success, 1 for fatal errors

## Examples

### Test with Sample Data

```bash
# Use the provided sample data
python gen_batch_jsonl.py --in samples/input.csv --out test_output.jsonl --prompt-id bio_gen --prompt-version v1.0

# Check the first line of output
head -1 test_output.jsonl
```

Expected first line output:
```json
{"custom_id": "a1", "method": "POST", "url": "/v1/responses", "body": {"prompt": {"id": "bio_gen", "version": "v1.0", "variables": {"artist_name": "NewJeans", "artist_data": "K-pop group; ADOR; 'Supernatural' era"}}}}
```

### Test with Sample Data

```bash
# Use the provided sample data
python gen_batch_jsonl.py --in samples/input.csv --out test_output.jsonl --prompt-id bio_gen --prompt-version v1.0

# Process only first 2 rows for testing
python gen_batch_jsonl.py --in samples/input.csv --out test.jsonl --prompt-id test --prompt-version v1 --limit 2 --verbose
```

---

# Tool 2: OpenAI Batch API Manager (`batch_tool.py`)

Manages OpenAI Batch API operations: creating batches, checking status, retrieving results, and cancelling jobs.

## Operations

### 1. Create Batch

Upload a JSONL file and create a batch job:

```bash
python batch_tool.py create --in input.jsonl
```

**Options:**
- `--in <path>` (required): Input JSONL file path
- `--endpoint <endpoint>` (default: `/v1/responses`): API endpoint
- `--completion-window <window>` (default: `24h`): Completion window

**Example:**
```bash
python batch_tool.py create --in requests.jsonl --endpoint "/v1/responses" --completion-window 24h
# Output: File ID: file-abc123, Batch ID: batch-def456
```

### 2. Check Status

Check the status of a batch job:

```bash
python batch_tool.py status --batch-id batch-def456
```

**Options:**
- `--batch-id <id>` (required): Batch ID to check
- `--auto-save` (default: on): Automatically download results if completed
- `--no-auto-save`: Disable automatic result download

**Output examples:**
```
# In progress
Status: in_progress
Created: 2024-01-15T10:30:00

# Completed with auto-save
Status: completed
Created: 2024-01-15T10:30:00
Completed: 2024-01-15T11:45:00
Results saved: results_batch-def456.jsonl (15420 bytes)
```

### 3. Retrieve Results

Manually download results from a completed batch:

```bash
python batch_tool.py retrieve --batch-id batch-def456 --out my_results.jsonl
```

**Options:**
- `--batch-id <id>` (required): Batch ID to retrieve
- `--out <path>` (optional): Output file path (default: `results_<batch_id>.jsonl`)

### 4. Cancel Batch

Cancel a batch job that is queued or in progress:

```bash
python batch_tool.py cancel --batch-id batch-def456
```

**Options:**
- `--batch-id <id>` (required): Batch ID to cancel

**Output examples:**
```
# Successfully cancelled
Batch cancellation initiated: batch-def456
Status: cancelled
Created: 2024-01-15 10:30:00
Note: Batch was successfully cancelled. Any completed requests have been processed and you will be charged for them.

# Cancellation in progress
Batch cancellation initiated: batch-def456
Status: cancelling
Created: 2024-01-15 10:30:00
Note: Batch cancellation in progress. This may take up to 10 minutes.
```

**Important Notes:**
- You can cancel batches that are `validating`, `queued`, `in_progress`, or `finalizing`
- Any completed requests will be processed and you'll be charged for them
- Cancellation may take up to 10 minutes to complete
- Once cancelled, partial results (if any) will be available in the output file

## Logging

All operations are logged to `logs/batch_YYYYMMDD_HHMMSS.log` (or use `--log-file <path>`):

- All API operations (UPLOAD, CREATE_BATCH, GET_STATUS, CANCEL_BATCH, DOWNLOAD_RESULTS)
- Request metadata (without secrets)
- Response data (except large result files)
- Error details and stack traces

---

# Input/Output Formats

## CSV Input Format (for `gen_batch_jsonl.py`)

```csv
artist_id,artist_name,artist_data
a1,NewJeans,"K-pop group; ADOR; 'Supernatural' era"
a2,Stereolab,"Franco-UK post-rock; ""Dots and Loops"""
a3,Perfume,"Japanese technopop trio
Known for 'love the world'"
```

**Requirements:**
- `artist_id`: Unique identifier (required, non-empty)
- `artist_name`: Artist name (required, non-empty) 
- `artist_data`: Additional data (can be empty, supports JSON strings)

## JSONL Output Format

Each line is a JSON object for the OpenAI Batch API:

```json
{
  "custom_id": "a1",
  "method": "POST", 
  "url": "/v1/responses",
  "body": {
    "prompt": {
      "id": "bio_gen",
      "version": "v1.0",
      "variables": {
        "artist_name": "NewJeans",
        "artist_data": "K-pop group; ADOR; 'Supernatural' era"
      }
    }
  }
}
```

---

# Configuration & Error Handling

## Configuration Priority
1. CLI flags (highest priority)
2. Environment variables
3. Error if missing

| Tool | CLI Flag | Environment Variable | Description | Required |
|------|----------|---------------------|-------------|----------|
| `gen_batch_jsonl.py` | `--prompt-id` | `PROMPT_ID` | Prompt identifier | Yes |
| `gen_batch_jsonl.py` | `--prompt-version` | `PROMPT_VERSION` | Prompt version | No (optional) |
| `batch_tool.py` | N/A | `OPENAI_API_KEY` | OpenAI API key | Yes |

## Error Handling
- **Exit codes**: 0 for success, 1 for fatal errors, 2 for invalid arguments
- **Non-strict mode** (gen_batch_jsonl.py): Invalid rows are logged and skipped
- **Strict mode** (gen_batch_jsonl.py): Any invalid row fails the entire process

## Features

### CSV to JSONL Converter
- **UTF-8 Support**: Handles international characters and emojis
- **CSV Robustness**: Supports quoted fields, embedded commas and newlines
- **Validation**: Checks required fields and data integrity
- **Flexible Input**: Works with or without CSV headers
- **Error Recovery**: Continues processing despite individual row failures (in non-strict mode)

### Batch API Manager
- **Auto-save**: Automatically downloads results when batch completes
- **Comprehensive logging**: All operations logged with timestamps
- **Error resilience**: Clear error messages and proper exit codes
- **File management**: Auto-creates directories, handles overwrites

---

# Development

## Running Tests

```bash
python -m pytest tests/ -v
```

**Test coverage:**
- 56 total tests (23 for batch_tool.py, 33 for gen_batch_jsonl.py)
- Edge cases: CSV parsing, file validation, API mocking
- Integration tests: End-to-end workflows

## File Structure

```
.
├── gen_batch_jsonl.py          # CSV to JSONL converter
├── batch_tool.py               # Batch API manager
├── samples/input.csv           # Sample data
├── tests/                      # Test suites
├── logs/                       # Auto-generated logs
├── CLAUDE.md                   # Technical documentation
└── README.md                   # This file
```

## Troubleshooting

**OpenAI SDK not installed:**
```bash
pip install openai
```

**Missing API key:**
```bash
export OPENAI_API_KEY=your_key_here
```

**Batch not completed:**
- Wait for processing to complete
- Check status: `python batch_tool.py status --batch-id <id>`
- Processing time depends on queue and completion window

**Permission errors:**
- Ensure write permissions for log directory and output files
- Check that file paths are valid and accessible