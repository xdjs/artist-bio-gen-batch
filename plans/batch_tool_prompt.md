# Prompt

Build a Python 3.11 CLI that drives the **OpenAI Batch API** with three distinct modes. The program takes an **input filename** and performs:

**A. Create batch**
1) Upload the file  
2) Create a batch

**B. Check status of batch**  
3) Check the status of a batch **and if status is `completed`, automatically retrieve and save results**

**C. Retrieve batch**  
4) Retrieve results of a batch **given a batch id** (download and save output)

## Functional Requirements

### Inputs
- API key via `OPENAI_API_KEY` env var.
- Required CLI subcommands: `create`, `status`, `retrieve`.
- Common flags:
  - `--log-file <path>` (default: `logs/batch_<YYYYmmdd_HHMMSS>.log`)
- `create` flags:
  - `--in <path/to/input.jsonl>` (required)
  - `--endpoint "/v1/responses"` (default; string)
  - `--completion-window "24h"` (default; string)
- `status` flags:
  - `--batch-id <id>` (required)
  - `--auto-save` (boolean; default **on**; if completed, immediately fetch and save results)
- `retrieve` flags:
  - `--batch-id <id>` (required)
  - `--out <path/to/output.jsonl>` (optional; default: `results_<batch_id>.jsonl`)

### API Operations (use the official Python SDK)
- Initialize once: `from openai import OpenAI; client = OpenAI()`
- **Upload**: `client.files.create(file=open(input_path, "rb"), purpose="batch")`
- **Create batch**:  
  `client.batches.create(input_file_id=<file.id>, endpoint=<endpoint>, completion_window=<completion_window>)`
- **Check status**: `client.batches.retrieve(<batch_id>)`
- **Download output** (when batch is completed):  
  `content = client.files.content(<output_file_id>)`  
  Save bytes to the specified output path (no extra parsing).

### Behavior Details
- **Mode A (create)**:
  1) Upload the provided JSONL file (purpose `"batch"`).  
  2) Create a batch using the returned file id.  
  3) Print to stdout: the uploaded **file id** and **batch id**.  
  4) Log both responses (see Logging spec).

- **Mode B (status)**:
  1) Retrieve the batch by `--batch-id`.  
  2) Print to stdout the status and key timestamps.  
  3) **If status is `completed` and `--auto-save` is on**: download output using `output_file_id`, save to a local file, and print the saved filename.  
  4) Log the full status response. If results were saved, **do not log file content**—log only the local output path.

- **Mode C (retrieve)**:
  1) Retrieve the batch by `--batch-id`.  
  2) If status is not `completed`, exit non-zero with a clear message.  
  3) If `completed`, download the `output_file_id` and save to `--out` (default `results_<batch_id>.jsonl`).  
  4) Print to stdout the saved filename.  
  5) Log the action and the local output path (not the file contents).

### Logging (must stream to file as events occur)
- Use only `logging` from stdlib. Create a **FileHandler** that flushes on every emit (default handler flushes—ensure it does).  
- Log format: `%(asctime)s %(levelname)s %(message)s`
- Auto-create the log directory if needed.
- **Every API call** should be logged with:
  - Operation name (UPLOAD, CREATE_BATCH, GET_STATUS, DOWNLOAD_RESULTS)
  - **Request metadata** (no secrets)
  - **Response JSON** (except for the big results file; see next line)
- For **results download**, **do not log file content**; log only the **local output filename** and byte count.

### Errors & Exit Codes
- Non-zero exit on:
  - Missing/invalid arguments
  - Missing `OPENAI_API_KEY`
  - File not found / unreadable input
  - Network/API errors (show concise reason)
  - `retrieve` when batch not completed
- Print a concise error to stderr and log the stack/response.

### Implementation Constraints
- **Stdlib only**: `argparse`, `os`, `sys`, `pathlib`, `logging`, `json`, `typing`, `datetime`, `io`, `textwrap`
- Typed, readable, small functions. Suggested structure:
  - `main()` → argument parsing + dispatcher
  - `setup_logger(log_path) -> logging.Logger`
  - `upload_file(client, path) -> str` (returns file_id)
  - `create_batch(client, file_id, endpoint, window) -> dict`
  - `get_batch_status(client, batch_id) -> dict`
  - `download_results(client, file_id, out_path) -> int` (returns byte count)

### CLI Examples
- Create:  
  `python batch_tool.py create --in requests.jsonl --endpoint "/v1/responses" --completion-window 24h`
- Status (auto-save if completed):  
  `python batch_tool.py status --batch-id batch_abc123`
- Retrieve (explicit):  
  `python batch_tool.py retrieve --batch-id batch_abc123 --out my_results.jsonl`

### Validation / Safety
- Confirm input file exists and is readable for `create`.
- Do **not** attempt to parse/validate the JSONL payload lines; treat as opaque (the user’s responsibility).
- When saving results, ensure parent dir exists, handle overwrite with a warning.

### Output
- Print succinct user-facing lines (ids, status, local file path).  
- Everything else goes to the log file.

### Deliverables
- `batch_tool.py`
- `README.md` with:
  - Setup (env var, install)
  - Examples above
  - Notes on JSONL input shape (one JSON object per line)
- Minimal inline tests or a `tests/` note are optional but not required.

**Goal**: production-ready, minimal dependencies, clear logs, robust error handling, easy to extend.
