"""Regenerate the workflow graph diagram in README.md and its PNG copy.

Run manually:
    python3 scripts/regenerate_workflow_graph.py         # updates README.md's mermaid block only
    python3 scripts/regenerate_workflow_graph.py --png    # also regenerates data/workflow_graph.png

Both steps are invoked automatically by the pre-commit hook in
.githooks/pre-commit whenever src/workflow.py is staged for commit. The
PNG step calls the public mermaid.ink rendering service over the
network via draw_mermaid_png(); if that call fails (offline, service
down), update_png() prints a warning and returns instead of raising, so
an unrelated commit touching src/workflow.py doesn't hard-fail just
because the network/service is unavailable -- only README.md's diagram
is guaranteed to stay in sync (enforced by
tests/test_workflow_graph_docs.py).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.workflow import build_workflow_graph  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
README_PATH = REPO_ROOT / "README.md"
PNG_PATH = REPO_ROOT / "data" / "workflow_graph.png"
START_MARKER = "<!-- workflow-graph:start -->"
END_MARKER = "<!-- workflow-graph:end -->"


def get_mermaid_text() -> str:
    return build_workflow_graph().get_graph().draw_mermaid()


def update_readme(mermaid_text: str) -> bool:
    """Replace the mermaid block between the markers. Returns True if content changed."""
    original = README_PATH.read_text()
    start = original.index(START_MARKER) + len(START_MARKER)
    end = original.index(END_MARKER)
    new_block = f"\n```mermaid\n{mermaid_text.rstrip()}\n```\n"
    updated = original[:start] + new_block + original[end:]
    if updated == original:
        return False
    README_PATH.write_text(updated)
    return True


def update_png() -> None:
    """Best-effort: prints a warning and returns instead of raising on failure
    (e.g. no network access to the mermaid.ink rendering service), so callers
    like the pre-commit hook don't hard-fail an unrelated commit over this."""
    try:
        png_bytes = build_workflow_graph().get_graph().draw_mermaid_png()
    except Exception as exc:  # noqa: BLE001 -- any failure here is non-fatal by design
        print(f"Warning: could not regenerate {PNG_PATH} ({type(exc).__name__}: {exc})")
        return
    PNG_PATH.write_bytes(png_bytes)
    print(f"Regenerated {PNG_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--png", action="store_true", help="Also regenerate data/workflow_graph.png (network call)"
    )
    args = parser.parse_args()

    mermaid_text = get_mermaid_text()
    changed = update_readme(mermaid_text)
    print(f"README.md workflow graph {'updated' if changed else 'already up to date'}")

    if args.png:
        update_png()


if __name__ == "__main__":
    main()
