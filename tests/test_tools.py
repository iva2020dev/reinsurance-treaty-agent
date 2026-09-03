"""Tests for src.tools."""

from datetime import date

from src.models import ClaimsData
from src.tools import calculate_loss_ratio, query_historical_claims


def test_query_historical_claims_returns_claims_for_known_cedent():
    claims = query_historical_claims("Acme Insurance Co.")

    assert len(claims) == 3
    assert all(c.cedent_name == "Acme Insurance Co." for c in claims)
    assert sum(c.claim_amount for c in claims) == 750_000 + 2_500_000 + 120_000


def test_query_historical_claims_returns_empty_list_for_unknown_cedent():
    claims = query_historical_claims("Nonexistent Cedent LLC")

    assert claims == []


def test_calculate_loss_ratio_known_inputs():
    claims = [
        ClaimsData(cedent_name="X", claim_amount=750_000, claim_date=date(2025, 1, 1)),
        ClaimsData(cedent_name="X", claim_amount=2_500_000, claim_date=date(2025, 2, 1)),
    ]

    # Layer: attachment 1,000,000 / limit 5,000,000 (so layer top = 6,000,000)
    # Claim 1 (750,000) is below the attachment point -> ceded 0
    # Claim 2 (2,500,000) -> ceded 2,500,000 - 1,000,000 = 1,500,000
    ratio = calculate_loss_ratio(attachment_point=1_000_000, limit=5_000_000, claims=claims)

    assert ratio == 1_500_000 / 5_000_000


def test_calculate_loss_ratio_empty_claims_is_zero():
    ratio = calculate_loss_ratio(attachment_point=1_000_000, limit=5_000_000, claims=[])

    assert ratio == 0.0


def test_calculate_loss_ratio_claim_exceeding_layer_top_is_capped():
    claims = [
        ClaimsData(cedent_name="X", claim_amount=50_000_000, claim_date=date(2025, 1, 1)),
    ]

    # Layer top = 1,000,000 + 5,000,000 = 6,000,000; claim far exceeds it,
    # so ceded amount is capped at the full limit -> ratio of 1.0.
    ratio = calculate_loss_ratio(attachment_point=1_000_000, limit=5_000_000, claims=claims)

    assert ratio == 1.0
