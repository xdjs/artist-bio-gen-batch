# Prompt

Build a Python 3.11 CLI program that converts a CSV of artist rows into an OpenAI Batch API JSONL file targeting the **Responses API**. Keep the code clean, typed, and dependency-light.

### Requirements

**Input CSV**
- Columns (header required, case-sensitive): `artist_id,artist_name,artist_data`
- UTF-8 encoding. Support quoted fields and commas/newlines inside `artist_data`.
= Example data: `4efb14b2-ef49-429f-95f4-2f1e593e1b67,KIRINJI,"{""x"": ""kirinjiofficial"", ""spotify"": ""0O1UtbTe4ca7HabaiMhYZ7"", ""instagram"": ""kirinji_official"", ""wikipedia"": ""Kirinji_(band)"", ""soundcloud"": ""kirinji-official""}"`

**Output JSONL**
- One JSON object per line (no trailing commas, no enclosing array).
- Exact shape per line:
```json
{
  "custom_id": "<ARTIST_ID>",
  "method": "POST",
  "url": "/v1/responses",
  "body": {
    "prompt": {
      "id": "<PROMPT_ID>",
      "version": "<PROMPT_VERSION>",
      "variables": {
        "artist_name": "<ARTIST_NAME>",
        "artist_data": "<ARTIST_DATA>"
      }
    }
  }
}
```

**Config**
- `PROMPT_ID` and `PROMPT_VERSION` must be configurable by BOTH:
  1) CLI flags `--prompt-id` and `--prompt-version`
  2) Environment variables `PROMPT_ID` and `PROMPT_VERSION`
- CLI flags override env vars. If missing, exit with a helpful error.

**CLI**
- Command: `python gen_batch_jsonl.py --in <path/to/input.csv> --out <path/to/output.jsonl> --prompt-id <id> --prompt-version <ver>`
- Optional flags:
  - `--limit N` → process only first N data rows (for dry runs)
  - `--skip-header` → allow CSVs without a header (then assume the column order above)
  - `--strict` → if any row is invalid, fail the whole run; otherwise, log and skip bad rows

**Validation**
- `artist_id`, `artist_name` required (non-empty strings after trimming).
- `artist_data` may be empty but must still be present.
- Ensure JSON is valid UTF-8 and properly escaped. No smart quotes. No control characters.

**Implementation details**
- Use stdlib only (`argparse`, `csv`, `json`, `os`, `pathlib`, `typing`, `logging`, `sys`).
- Use `csv.DictReader` when header present; otherwise `csv.reader` with positional mapping.
- Normalize whitespace: strip leading/trailing spaces on all three fields.
- Write with newline-separated JSON objects (`.write(json.dumps(obj, ensure_ascii=False) + "\n")`).
- Log a summary: total rows read, written, skipped.
- Exit code:
  - `0` on success (even if some rows skipped in non-strict mode),
  - `1` on fatal errors (bad config, unreadable file, strict row failure, etc.).

**Structure**
- `main()` parses args, loads env, configures logging, calls `convert_csv_to_jsonl(...)`.
- `convert_csv_to_jsonl` returns a `ConversionStats` dataclass: `read:int, written:int, skipped:int`.
- Small helper `build_task_row(artist_id, artist_name, artist_data, prompt_id, prompt_version) -> dict`.

**Tests (lightweight, inline or separate)**
- Unit tests for `build_task_row` (shape + values) and a tiny in-memory CSV conversion using `io.StringIO`.
- Include a test for:
  - embedded commas/newlines in `artist_data`,
  - missing `artist_name` (should skip unless `--strict`),
  - `--limit` behavior.

**Sample usage**
- Provide a `samples/input.csv` example:
  ```csv
  artist_id,artist_name,artist_data
  a1,NewJeans,"K-pop group; ADOR; 'Supernatural' era"
  a2,Stereolab,"Franco-UK post-rock; ""Dots and Loops"""
  a3,Perfume,"Japanese technopop trio\nKnown for 'love the world'"
  ```
- Show the first JSONL line output in a comment for verification.

**Non-goals**
- Do NOT call the network or create the batch job here. This tool only generates the JSONL.

**Dev UX**
- Clear error messages if headers are wrong or required fields are blank.
- Helpful `--help` text with examples.

Deliverables:
- `gen_batch_jsonl.py`
- `README.md` with install/run examples
- Minimal tests (can be `tests/test_gen_batch_jsonl.py` or docstring tests)

Make it production-ready, readable, and easy to extend later to upload with `client.files.create(purpose="batch")`.
