# CLAUDE.md - Artist Bio Generator Batch Processing Suite

## Project Overview

This is a **complete batch processing solution** for artist biography generation using OpenAI's Batch API. The project consists of two integrated Python CLI tools that handle the entire workflow from CSV input to processed results.

**Key Purpose**: End-to-end batch processing of artist data - from CSV conversion to OpenAI Batch API management, enabling automated artist biography generation at scale.

## Architecture & Design

### Core Components

1. **CSV to JSONL Converter** (`gen_batch_jsonl.py` - 299 lines)
   - CLI argument parsing and configuration management
   - CSV processing with robust error handling
   - JSONL output generation for OpenAI Batch API
   - Logging and statistics reporting

2. **Batch API Manager** (`batch_tool.py` - 356 lines)
   - OpenAI Batch API integration (create, status, retrieve)
   - File upload and download management
   - Comprehensive logging with immediate flushing
   - Auto-save functionality for completed batches

3. **Comprehensive Test Suites**
   - `tests/test_gen_batch_jsonl.py` (288 lines, 15 test cases)
   - `tests/test_batch_tool.py` (472 lines, 16 test cases)
   - Total: 31 tests covering edge cases and integration scenarios

4. **Sample Data & Documentation**
   - `samples/input.csv`: Real-world test data with complex CSV scenarios
   - Consolidated `README.md`: Complete user documentation
   - `CLAUDE.md`: Technical architecture documentation

### Key Design Principles

- **Modular architecture**: Two focused tools that work together seamlessly
- **Production-ready**: Comprehensive error handling, logging, validation
- **Type-safe**: Full type annotations throughout both codebases
- **Dependency-conscious**: Minimal external dependencies (OpenAI SDK only)
- **Test-driven**: Extensive test coverage for real-world edge cases
- **User-friendly**: Clear documentation and helpful error messages

## Technical Implementation

### Complete Workflow Architecture
```
CSV Input → gen_batch_jsonl.py → JSONL → batch_tool.py → OpenAI Batch API → Results
    ↓              ↓                 ↓           ↓              ↓            ↓
 Artists.csv → Validation → batch_requests.jsonl → Upload → Processing → results.jsonl
```

### Tool 1: CSV to JSONL Converter (`gen_batch_jsonl.py`)

**Core Functions:**
- `build_task_row()`: Creates OpenAI Batch API compatible JSON objects
- `convert_csv_to_jsonl()`: Main conversion orchestrator with statistics tracking
- `process_csv_rows()`: Robust CSV parsing with validation and error recovery
- `validate_row()`: Data integrity checks for required fields

**Key Features:**
- Streaming CSV processing (memory-efficient for large files)
- Support for embedded commas, newlines, and complex JSON in CSV fields
- Configurable validation modes (strict vs. error-recovery)
- Environment variable and CLI flag configuration

### Tool 2: Batch API Manager (`batch_tool.py`)

**Core Functions:**
- `upload_file()`: File upload to OpenAI with progress logging
- `create_batch()`: Batch job creation with configurable parameters
- `get_batch_status()`: Status checking with detailed timestamps
- `download_results()`: Result retrieval with automatic directory creation

**Key Features:**
- Three-mode operation: create, status (with auto-save), retrieve
- Comprehensive logging with immediate file flushing
- Automatic file management (directory creation, overwrite warnings)
- OpenAI SDK integration with proper error handling

### Input Format (CSV)
```csv
artist_id,artist_name,artist_data
a1,NewJeans,"K-pop group; ADOR; 'Supernatural' era"
a2,Stereolab,"Franco-UK post-rock; ""Dots and Loops"""
```

### Output Format (JSONL)
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

## Complete Workflow Usage

### End-to-End Example
```bash
# Step 1: Convert CSV to JSONL
python gen_batch_jsonl.py --in artists.csv --out batch_requests.jsonl --prompt-id bio_gen --prompt-version v1.0

# Step 2: Create batch job
python batch_tool.py create --in batch_requests.jsonl
# Output: File ID: file-abc123, Batch ID: batch-def456

# Step 3: Monitor status (auto-saves when complete)
python batch_tool.py status --batch-id batch-def456
# Output: Status: completed, Results saved: results_batch-def456.jsonl

# Step 4: Manual retrieval (if needed)
python batch_tool.py retrieve --batch-id batch-def456 --out final_results.jsonl
```

### Tool-Specific Usage

#### CSV to JSONL Converter
```bash
# Basic usage
python gen_batch_jsonl.py --in artists.csv --out batch.jsonl --prompt-id bio_gen --prompt-version v1.0

# Environment variables
export PROMPT_ID=bio_gen
export PROMPT_VERSION=v1.0
python gen_batch_jsonl.py --in artists.csv --out batch.jsonl

# Advanced options
python gen_batch_jsonl.py --in artists.csv --out batch.jsonl --prompt-id bio_gen --prompt-version v1.0 --limit 100 --strict --verbose
```

#### Batch API Manager
```bash
# Create batch
python batch_tool.py create --in batch_requests.jsonl --endpoint "/v1/responses" --completion-window 24h

# Check status with auto-save
python batch_tool.py status --batch-id batch-abc123

# Manual retrieve
python batch_tool.py retrieve --batch-id batch-abc123 --out custom_output.jsonl
```

## Testing

### Test Coverage Overview
- **31 total test cases** across comprehensive test suites
- **Real-world edge cases**: CSV parsing complexities, API integration scenarios
- **Production failure modes**: File permissions, network errors, validation edge cases
- **Integration testing**: End-to-end workflows with mocked external dependencies

### Test Breakdown

#### CSV Converter Tests (`test_gen_batch_jsonl.py` - 15 tests)
1. **TestBuildTaskRow**: JSON structure validation and special character handling
2. **TestValidateRow**: Data validation logic for required fields
3. **TestProcessCsvRows**: CSV parsing edge cases (embedded commas, newlines, limits)
4. **TestConvertCsvToJsonl**: End-to-end conversion with statistics tracking

#### Batch Tool Tests (`test_batch_tool.py` - 16 tests)
1. **TestLoggerCreationAndFormat**: File logging with immediate flushing
2. **TestCLIArgumentParsing**: Command-line argument validation and defaults
3. **TestFilePathValidation**: File system operations and directory creation
4. **TestErrorMessageQuality**: User-friendly error messages for common issues
5. **TestEndToEndWorkflow**: Complete create→status→retrieve workflow simulation
6. **TestMainFunctionIntegration**: Command-line interface error handling

### Running Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test suite
python -m pytest tests/test_batch_tool.py -v
python -m pytest tests/test_gen_batch_jsonl.py -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html
```

### Test Philosophy
Tests focus on **meaningful failure scenarios** rather than trivial functionality:
- File system edge cases (permissions, missing directories, overwrites)
- CSV parsing complexities (embedded quotes, newlines, Unicode)
- API integration failures (network errors, invalid responses)
- CLI argument conflicts and validation
- Error message clarity and user experience

## Configuration

### Tool Configuration

#### CSV to JSONL Converter
| Parameter | CLI Flag | Environment Variable | Required | Default |
|-----------|----------|---------------------|----------|---------|
| Prompt ID | `--prompt-id` | `PROMPT_ID` | Yes | - |
| Prompt Version | `--prompt-version` | `PROMPT_VERSION` | Yes | - |
| Input File | `--in` | - | Yes | - |
| Output File | `--out` | - | Yes | - |
| Processing Limit | `--limit` | - | No | All rows |
| Strict Mode | `--strict` | - | No | `False` |
| Skip Header | `--skip-header` | - | No | `False` |
| Verbose Logging | `--verbose` | - | No | `False` |

#### Batch API Manager
| Parameter | CLI Flag | Environment Variable | Required | Default |
|-----------|----------|---------------------|----------|---------|
| OpenAI API Key | - | `OPENAI_API_KEY` | Yes | - |
| Log File | `--log-file` | - | No | `logs/batch_YYYYMMDD_HHMMSS.log` |
| Endpoint | `--endpoint` | - | No | `/v1/responses` |
| Completion Window | `--completion-window` | - | No | `24h` |
| Auto-save Results | `--auto-save` / `--no-auto-save` | - | No | `True` |

### Configuration Priority
1. CLI flags (highest priority)
2. Environment variables  
3. Default values
4. Error if required parameter missing

## Error Handling

### Validation Rules
- `artist_id`: Required, non-empty after trimming
- `artist_name`: Required, non-empty after trimming  
- `artist_data`: Optional, can be empty

### Operating Modes
- **Non-strict (default)**: Log and skip invalid rows
- **Strict**: Fail entire process on first invalid row

### Exit Codes
- `0`: Success (even with skipped rows in non-strict)
- `1`: Fatal errors (config, file access, strict validation)

## File Structure
```
artist-bio-gen-batch-claude/
├── gen_batch_jsonl.py          # CSV to JSONL converter (299 lines)
├── batch_tool.py               # OpenAI Batch API manager (356 lines)
├── tests/
│   ├── test_gen_batch_jsonl.py # CSV converter tests (288 lines, 15 tests)
│   └── test_batch_tool.py      # Batch tool tests (472 lines, 16 tests)
├── samples/input.csv           # Sample CSV data with edge cases
├── plans/                      # Original requirements and specifications
│   ├── artist_bio_gen_batch_prompt.md
│   └── batch_tool_prompt.md
├── logs/                       # Auto-generated log files (created by batch_tool.py)
├── .gitignore                  # Python + macOS gitignore
├── README.md                   # Complete user documentation
└── CLAUDE.md                   # Technical architecture documentation
```

### Code Metrics
- **Total Python code**: 1,415 lines across 4 files
- **Test coverage**: 31 tests covering real-world edge cases
- **Documentation**: Comprehensive user and technical docs
- **Dependencies**: Standard library + OpenAI SDK only

## Development Notes

### Code Quality
- **Full type annotations** using `typing` module throughout both codebases
- **Dataclass usage** for structured data (`ConversionStats`)
- **Comprehensive docstrings** for all public functions
- **Clean separation of concerns** between parsing, validation, and I/O operations
- **Consistent error handling** patterns across both tools

### Performance Considerations
- **Streaming CSV processing** (memory-efficient for large datasets)
- **Efficient JSON serialization** with `ensure_ascii=False` for international characters
- **Lazy file I/O** with proper resource management
- **Immediate log flushing** for real-time monitoring of batch operations
- **Minimal dependency footprint** for fast startup times

### Security & Robustness
- **UTF-8 encoding enforcement** throughout the pipeline
- **Proper file handle management** with context managers
- **Input sanitization and validation** at multiple layers
- **API key protection** (never logged or printed)
- **Secure temporary file handling** in tests
- **Comprehensive error boundaries** to prevent data loss

## Future Extensions

The modular architecture enables easy extension:

### CSV Converter Extensions
- Support for additional output formats (XML, Parquet, etc.)
- Multi-column artist data with configurable field mapping
- Advanced validation rules (regex patterns, data type checking)
- Parallel processing for very large CSV files
- Integration with databases as input sources

### Batch Tool Extensions
- Support for different OpenAI endpoints beyond `/v1/responses`
- Batch job scheduling and queuing system
- Cost tracking and billing integration
- Webhook notifications for batch completion
- Bulk batch management (multiple batches from single command)
- Integration with cloud storage (S3, GCS) for large files

### System Extensions
- Web interface for non-technical users
- Docker containerization for deployment
- Monitoring dashboard for batch job status
- Integration with workflow orchestration tools (Airflow, Prefect)
- Multi-tenant support for different organizations

## Production Deployment

### Recommended Setup
```bash
# Environment setup
python -m venv venv
source venv/bin/activate
pip install openai

# Configuration
export OPENAI_API_KEY=your_production_key
export PROMPT_ID=production_bio_gen
export PROMPT_VERSION=v2.0

# Directory structure
mkdir -p {input,output,logs,archive}

# Production run
python gen_batch_jsonl.py --in input/artists.csv --out output/batch_$(date +%Y%m%d).jsonl --strict
python batch_tool.py create --in output/batch_$(date +%Y%m%d).jsonl --log-file logs/batch_$(date +%Y%m%d_%H%M).log
```

### Monitoring & Maintenance
- Regular log rotation for batch operations
- Automated cleanup of old batch files
- Health checks for OpenAI API connectivity  
- Cost monitoring and usage alerts
- Backup procedures for critical input data

## Dependencies & Requirements

### Runtime Dependencies
- **Python 3.11+** (required for modern type annotations)
- **OpenAI Python SDK** (`pip install openai`) - for batch_tool.py only
- **Standard library modules**: `argparse`, `csv`, `json`, `logging`, `os`, `pathlib`, `typing`, `sys`, `datetime`, `io`

### Development Dependencies
- **pytest** - for running test suite
- **pytest-cov** - for coverage reporting (optional)

### System Requirements
- **Disk space**: Minimal for code, variable for input/output files
- **Memory**: Streaming processing keeps memory usage low
- **Network**: Required for OpenAI API access (batch_tool.py)
- **Permissions**: Write access for logs/, output files

This suite provides a production-ready solution for large-scale artist biography generation using OpenAI's Batch API, with comprehensive testing, documentation, and extension points for future enhancements.