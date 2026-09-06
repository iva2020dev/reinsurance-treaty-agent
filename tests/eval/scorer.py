"""Field-level precision/recall scorer for the extraction accuracy eval suite.

Runs each golden case through the real end-to-end pipeline
(`run_workflow_from_pdf`) -- regex first, falling back to the LLM
Extraction Fallback exactly as production does -- and compares the
extracted `TreatyTerms` against the case's known-correct values.
"""

import math
from dataclasses import dataclass, field

from tests.eval.golden_dataset import GoldenCase
from src.workflow import run_workflow_from_pdf

SCALAR_FIELDS = ["cedent_name", "attachment_point", "limit", "reinsurance_premium"]


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _numeric_match(expected: float, actual: float) -> bool:
    return math.isclose(expected, actual, rel_tol=1e-9, abs_tol=0.01)


@dataclass
class CaseResult:
    name: str
    extraction_method: str
    field_correct: dict[str, bool]
    exclusions_precision: float
    exclusions_recall: float
    error: str | None = None


@dataclass
class EvalReport:
    case_results: list[CaseResult] = field(default_factory=list)

    def field_accuracy(self, field_name: str) -> float:
        results = [r.field_correct[field_name] for r in self.case_results if field_name in r.field_correct]
        return sum(results) / len(results) if results else 0.0

    def overall_accuracy(self) -> float:
        all_results = [correct for r in self.case_results for correct in r.field_correct.values()]
        return sum(all_results) / len(all_results) if all_results else 0.0

    def mean_exclusions_precision(self) -> float:
        vals = [r.exclusions_precision for r in self.case_results]
        return sum(vals) / len(vals) if vals else 0.0

    def mean_exclusions_recall(self) -> float:
        vals = [r.exclusions_recall for r in self.case_results]
        return sum(vals) / len(vals) if vals else 0.0


def _score_exclusions(expected_keywords: list[str], actual_exclusions: list[str]) -> tuple[float, float]:
    """Set-based precision/recall via normalized substring containment.

    Not exact-string matching: an LLM-extracted exclusion clause can be
    correctly extracted while phrased differently than the golden
    keyword (e.g. "acts of terrorism" vs. "terrorism, as defined
    under..."), so each expected keyword just needs to appear
    (normalized, substring) inside at least one extracted item.
    """
    if not expected_keywords:
        return (1.0, 1.0) if not actual_exclusions else (0.0, 1.0)

    normalized_actual = [_normalize(item) for item in actual_exclusions]
    normalized_expected = [_normalize(k) for k in expected_keywords]

    matched_keywords = sum(1 for k in normalized_expected if any(k in item for item in normalized_actual))
    recall = matched_keywords / len(normalized_expected)

    if not normalized_actual:
        return 0.0, recall
    matched_items = sum(1 for item in normalized_actual if any(k in item for k in normalized_expected))
    precision = matched_items / len(normalized_actual)
    return precision, recall


def score_case(case: GoldenCase) -> CaseResult:
    try:
        result = run_workflow_from_pdf(case.pdf_path)
    except Exception as exc:  # noqa: BLE001 -- a parse failure is itself a scored failure, not a crash
        return CaseResult(
            name=case.name,
            extraction_method="none",
            field_correct={f: False for f in SCALAR_FIELDS},
            exclusions_precision=0.0,
            exclusions_recall=0.0,
            error=f"{type(exc).__name__}: {exc}",
        )

    treaty = result.get("treaty")
    if treaty is None:
        missing = ", ".join(result.get("missing_fields", []))
        return CaseResult(
            name=case.name,
            extraction_method=result.get("extraction_method", "none"),
            field_correct={f: False for f in SCALAR_FIELDS},
            exclusions_precision=0.0,
            exclusions_recall=0.0,
            error=result.get("llm_error") or f"extraction incomplete: missing {missing}",
        )

    field_correct = {
        "cedent_name": _normalize(treaty.cedent_name) == _normalize(case.expected_cedent_name),
        "attachment_point": _numeric_match(case.expected_attachment_point, treaty.attachment_point),
        "limit": _numeric_match(case.expected_limit, treaty.limit),
        "reinsurance_premium": _numeric_match(case.expected_reinsurance_premium, treaty.reinsurance_premium),
    }
    precision, recall = _score_exclusions(case.expected_exclusion_keywords, treaty.exclusions)

    return CaseResult(
        name=case.name,
        extraction_method=result.get("extraction_method", "none"),
        field_correct=field_correct,
        exclusions_precision=precision,
        exclusions_recall=recall,
    )


def run_eval(dataset: list[GoldenCase]) -> EvalReport:
    return EvalReport(case_results=[score_case(case) for case in dataset])
