"""Verifies README.md's workflow graph diagram matches the live graph.

This is a safety net for scripts/regenerate_workflow_graph.py and the
.githooks/pre-commit hook: if someone edits src/workflow.py without the
hook enabled (or bypasses it with --no-verify), this test fails instead
of letting the documented diagram silently go stale.
"""

from pathlib import Path

from scripts.regenerate_workflow_graph import END_MARKER, START_MARKER, get_mermaid_text

README_PATH = Path(__file__).resolve().parent.parent / "README.md"


def test_readme_workflow_graph_matches_live_graph():
    readme_text = README_PATH.read_text()
    start = readme_text.index(START_MARKER) + len(START_MARKER)
    end = readme_text.index(END_MARKER)
    documented_block = readme_text[start:end]

    current_mermaid = get_mermaid_text().rstrip()

    assert current_mermaid in documented_block, (
        "README.md's workflow graph diagram is out of date. Run: "
        "python3 scripts/regenerate_workflow_graph.py"
    )
