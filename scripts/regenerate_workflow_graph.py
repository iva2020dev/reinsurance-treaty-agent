"""Regenerate the workflow graph diagram in README.md (and optionally its PNG copy).

Run manually:
    python3 scripts/regenerate_workflow_graph.py         # updates README.md's mermaid block
    python3 scripts/regenerate_workflow_graph.py --png    # also regenerates data/workflow_graph.png

The README update is invoked automatically by the pre-commit hook in
.githooks/pre-commit whenever src/workflow.py is staged for commit. The
PNG is not regenerated automatically, since draw_mermaid_png() calls the
public mermaid.ink rendering service over the network - unsuitable for
a hook that must work offline and not add a network dependency to every
commit.
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
    png_bytes = build_workflow_graph().get_graph().draw_mermaid_png()
    PNG_PATH.write_bytes(png_bytes)


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
        print(f"Regenerated {PNG_PATH}")


if __name__ == "__main__":
    main()
