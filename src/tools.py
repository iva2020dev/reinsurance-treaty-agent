"""Deterministic tools (database query, math calculators)."""

import csv
import math
import re
from datetime import date
from pathlib import Path

from src.models import ClaimsData, TreatyTerms
from src.parser import PageSection

HISTORICAL_CLAIMS_CSV = Path(__file__).resolve().parent.parent / "data" / "historical_claims.csv"

_NUMERIC_FIELDS = ("attachment_point", "limit", "reinsurance_premium")
_NUMBER_PATTERN = re.compile(r"\$?\d[\d,]*(?:\.\d+)?")


def query_historical_claims(
    cedent_name: str, csv_path: str | Path = HISTORICAL_CLAIMS_CSV
) -> list[ClaimsData]:
    """Return historical claims for a cedent from the mock claims CSV.

    Matching is an exact, case-sensitive match on cedent_name. Returns an
    empty list if the cedent has no rows in the CSV.
    """
    claims = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["cedent_name"] == cedent_name:
                claims.append(
                    ClaimsData(
                        cedent_name=row["cedent_name"],
                        claim_amount=float(row["claim_amount"]),
                        claim_date=date.fromisoformat(row["claim_date"]),
                    )
                )
    return claims


def calculate_loss_ratio(
    attachment_point: float, limit: float, claims: list[ClaimsData]
) -> float:
    """Return the historical burn rate for a layer defined by [attachment_point, attachment_point + limit].

    For each claim, only the portion falling within the layer counts:
    max(0, min(claim_amount, attachment_point + limit) - attachment_point).
    The ratio is that ceded total divided by the layer's limit. 0 means
    the layer would have been untouched historically; 1.0 means it would
    have been fully exhausted; values above 1.0 mean historical losses
    would have exceeded the layer.
    """
    layer_top = attachment_point + limit
    ceded_total = sum(
        max(0.0, min(claim.claim_amount, layer_top) - attachment_point) for claim in claims
    )
    return ceded_total / limit


def _normalize_whitespace(text: str) -> str:
    # Rejoin a hyphenated word broken across a PDF line wrap (e.g.
    # "asbestos-\nrelated" -> "asbestos-related") before collapsing
    # whitespace -- a genuine hyphen is never followed by whitespace in
    # correctly-typeset text, so this only affects wrap artifacts.
    text = re.sub(r"-\s+", "-", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _numbers_in_text(text: str) -> list[float]:
    numbers = []
    for match in _NUMBER_PATTERN.finditer(text):
        try:
            numbers.append(float(match.group().replace("$", "").replace(",", "")))
        except ValueError:
            continue
    return numbers


def check_treaty_grounding(treaty: TreatyTerms, sections: list[PageSection]) -> list[str]:
    """Return the names of fields whose extracted value isn't supported by its cited page.

    For every field in treaty.page_citations, confirms the cited
    page's raw text actually contains the extracted value: an exact,
    whitespace-normalized, case-insensitive substring match for
    cedent_name/exclusions, or a numeric-equivalence match (tolerating
    "$"/comma formatting) for attachment_point/limit/
    reinsurance_premium. A field with no citation entry isn't checked
    -- there's nothing to verify it against. This is a deterministic
    safety net over LLM-extracted values, not used for regex
    extraction (whose values are anchored to page text by
    construction).
    """
    pages_by_number = {section.page_number: section.text for section in sections}
    ungrounded = []
    for field, page_number in treaty.page_citations.items():
        page_text = pages_by_number.get(page_number)
        if page_text is None:
            ungrounded.append(field)
            continue

        if field in _NUMERIC_FIELDS:
            value = getattr(treaty, field)
            grounded = any(
                math.isclose(value, n, rel_tol=1e-9, abs_tol=0.01)
                for n in _numbers_in_text(page_text)
            )
        elif field == "exclusions":
            normalized_page = _normalize_whitespace(page_text)
            grounded = all(
                _normalize_whitespace(item) in normalized_page for item in treaty.exclusions
            )
        else:  # cedent_name, or any other free-text field
            value = getattr(treaty, field, "")
            grounded = _normalize_whitespace(str(value)) in _normalize_whitespace(page_text)

        if not grounded:
            ungrounded.append(field)
    return ungrounded
