"""Deterministic tools (database query, math calculators)."""

import csv
from datetime import date
from pathlib import Path

from src.models import ClaimsData

HISTORICAL_CLAIMS_CSV = Path(__file__).resolve().parent.parent / "data" / "historical_claims.csv"


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
