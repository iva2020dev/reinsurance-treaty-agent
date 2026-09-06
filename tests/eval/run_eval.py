"""CLI: `python -m tests.eval.run_eval`.

Runs the golden dataset through the full extraction pipeline and
prints a field-level accuracy report. Cases exercising the LLM
Extraction Fallback need a real `ANTHROPIC_API_KEY` (same convention
as `tests/test_integration.py`'s real-API integration test); without
one, they're reported as skipped rather than failing.
"""

import os

from tests.eval.golden_dataset import GOLDEN_DATASET
from tests.eval.scorer import SCALAR_FIELDS, run_eval


def _ok(value: bool) -> str:
    return "OK" if value else "FAIL"


def main() -> None:
    has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    cases = [c for c in GOLDEN_DATASET if c.extraction_path == "regex" or has_api_key]
    skipped = [c.name for c in GOLDEN_DATASET if c.extraction_path == "llm" and not has_api_key]

    report = run_eval(cases)

    header = f"Extraction Accuracy Eval Suite -- {len(cases)} case(s) scored"
    if skipped:
        header += f", {len(skipped)} skipped (no ANTHROPIC_API_KEY): {', '.join(skipped)}"
    print(header)
    print()
    print(
        f"{'case':<20} {'method':<8} {'cedent':<6} {'attach':<6} {'limit':<6} "
        f"{'premium':<8} {'excl P':<7} {'excl R':<7} error"
    )
    for r in report.case_results:
        fc = r.field_correct
        print(
            f"{r.name:<20} {r.extraction_method:<8} "
            f"{_ok(fc.get('cedent_name')):<6} {_ok(fc.get('attachment_point')):<6} "
            f"{_ok(fc.get('limit')):<6} {_ok(fc.get('reinsurance_premium')):<8} "
            f"{r.exclusions_precision:<7.2f} {r.exclusions_recall:<7.2f} {r.error or ''}"
        )
    print()
    for field_name in SCALAR_FIELDS:
        print(f"{field_name} accuracy: {report.field_accuracy(field_name):.0%}")
    print(f"exclusions mean precision: {report.mean_exclusions_precision():.0%}")
    print(f"exclusions mean recall: {report.mean_exclusions_recall():.0%}")
    print(f"overall scalar-field accuracy: {report.overall_accuracy():.0%}")


if __name__ == "__main__":
    main()
