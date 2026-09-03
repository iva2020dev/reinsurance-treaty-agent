# reinsurance-treaty-agent
Reinsurance Treaty Analyzer Agent. Tech Stack: Python 3.11+, Pydantic v2, LangGraph (for deterministic agent orchestration), FastAPI (for API/services), Pytest (testing), Docker &amp; Streamlit (for easy deployment &amp; UI). AI Tooling: Claude Code (CLI) inside PyCharm, interacting with Claude 3.5 Sonnet via Anthropic API.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Running Tests

Tests live under `tests/` and are run with `pytest` from the project root
(so `src/` and `data/` resolve as relative paths).

Run the full suite:

```bash
python3 -m pytest tests/
```

Run with per-test output (`-v`):

```bash
python3 -m pytest tests/ -v
```

Example output:

```
============================= test session starts ==============================
collected 5 items

tests/test_parser.py::test_extract_treaty_sections_returns_one_section_per_page PASSED [ 20%]
tests/test_parser.py::test_extract_treaty_sections_handles_rich_multi_page_treaty PASSED [ 40%]
tests/test_parser.py::test_extract_treaty_sections_raises_on_malformed_pdf PASSED [ 60%]
tests/test_parser.py::test_extract_treaty_sections_raises_on_missing_file PASSED [ 80%]
tests/test_workflow.py::test_module_imports PASSED                       [100%]

============================== 5 passed in 0.06s ===============================
```

Run a single test file, e.g. just the parser tests:

```bash
python3 -m pytest tests/test_parser.py -v
```

Example output:

```
============================= test session starts ==============================
collected 4 items

tests/test_parser.py::test_extract_treaty_sections_returns_one_section_per_page PASSED [ 25%]
tests/test_parser.py::test_extract_treaty_sections_handles_rich_multi_page_treaty PASSED [ 50%]
tests/test_parser.py::test_extract_treaty_sections_raises_on_malformed_pdf PASSED [ 75%]
tests/test_parser.py::test_extract_treaty_sections_raises_on_missing_file PASSED [100%]

============================== 4 passed in 0.06s ===============================
```

Run a single test by name:

```bash
python3 -m pytest tests/test_parser.py::test_extract_treaty_sections_returns_one_section_per_page -v
```

Example output:

```
============================= test session starts ==============================
collected 1 item

tests/test_parser.py::test_extract_treaty_sections_returns_one_section_per_page PASSED [100%]

============================== 1 passed in 0.06s ===============================
```

## Sample Treaty Fixtures

`data/` holds two hand-built mock treaty PDFs used by the parser tests,
each with its parsed output saved alongside it as JSON for inspection
without running any code:

| PDF | Parsed output | Pages | Content |
|---|---|---|---|
| `sample_treaty.pdf` | `sample_treaty_parsed.json` | 2 | Minimal: attachment point, limit, premium, exclusions |
| `sample_rich_treaty.pdf` | `sample_rich_treaty_parsed.json` | 4 | Detailed: parties/period/territory, two layers with reinstatements and brokerage, a 10-item exclusions list, and claims/arbitration/governing-law provisions |
