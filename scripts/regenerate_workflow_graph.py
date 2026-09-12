"""Regenerate the workflow graph diagrams in README.md and the default
selection's PNG copy: the default (single-task) diagram and a second,
multi-task diagram showing every currently-implemented domain task
fanning out (get_multi_task_selected_ids() below).

Run manually:
    python3 scripts/regenerate_workflow_graph.py         # updates README.md's mermaid blocks only
    python3 scripts/regenerate_workflow_graph.py --png    # also regenerates data/workflow_graph.png (default selection only)

Both steps are invoked automatically by the pre-commit hook in
.githooks/pre-commit whenever src/workflow.py or src/domain_tasks.py is
staged for commit -- the latter because get_multi_task_selected_ids()
reads DOMAIN_TASKS directly, so a task's implementation_status flipping
there is exactly the kind of change that can change this diagram's
content. The PNG step calls the public mermaid.ink rendering service
over the network via draw_mermaid_png(); if that call fails (offline,
service down), update_png() prints a warning and returns instead of
raising, so an unrelated commit doesn't hard-fail just because the
network/service is unavailable -- only README.md's diagram is
guaranteed to stay in sync (enforced by tests/test_workflow_graph_docs.py).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.domain_tasks import DOMAIN_TASKS  # noqa: E402
from src.workflow import build_workflow_graph  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
README_PATH = REPO_ROOT / "README.md"
PNG_PATH = REPO_ROOT / "data" / "workflow_graph.png"
START_MARKER = "<!-- workflow-graph:start -->"
END_MARKER = "<!-- workflow-graph:end -->"

MULTI_TASK_START_MARKER = "<!-- workflow-graph-multi-task:start -->"
MULTI_TASK_END_MARKER = "<!-- workflow-graph-multi-task:end -->"


def get_multi_task_selected_ids() -> set[str]:
    """Every currently-implemented domain task's id.

    Computed from DOMAIN_TASKS rather than a fixed constant, so the
    multi-task diagram always reflects real fan-out as of whatever's
    actually shipped -- it grows on its own as more tasks are
    implemented, instead of needing a manual edit each time.
    """
    return {task.id for task in DOMAIN_TASKS if task.implementation_status == "implemented"}


def get_mermaid_text() -> str:
    return build_workflow_graph().get_graph().draw_mermaid()


def get_multi_task_mermaid_text() -> str:
    return build_workflow_graph(get_multi_task_selected_ids()).get_graph().draw_mermaid()


def _replace_between_markers(text: str, start_marker: str, end_marker: str, mermaid_text: str) -> str:
    """Replace the mermaid code block between start_marker/end_marker with mermaid_text."""
    start = text.index(start_marker) + len(start_marker)
    end = text.index(end_marker)
    new_block = f"\n```mermaid\n{mermaid_text.rstrip()}\n```\n"
    return text[:start] + new_block + text[end:]


def update_readme(mermaid_text: str) -> bool:
    """Replace the default single-task mermaid block. Returns True if content changed."""
    original = README_PATH.read_text()
    updated = _replace_between_markers(original, START_MARKER, END_MARKER, mermaid_text)
    if updated == original:
        return False
    README_PATH.write_text(updated)
    return True


def update_readme_multi_task(mermaid_text: str) -> bool:
    """Replace the multi-task example mermaid block. Returns True if content changed."""
    original = README_PATH.read_text()
    updated = _replace_between_markers(original, MULTI_TASK_START_MARKER, MULTI_TASK_END_MARKER, mermaid_text)
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

    multi_task_mermaid_text = get_multi_task_mermaid_text()
    multi_task_changed = update_readme_multi_task(multi_task_mermaid_text)
    print(f"README.md multi-task workflow graph {'updated' if multi_task_changed else 'already up to date'}")

    if args.png:
        update_png()


if __name__ == "__main__":
    main()
