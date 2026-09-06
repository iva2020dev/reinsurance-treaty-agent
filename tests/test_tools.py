"""Tests for src.tools."""

from datetime import date

from src.models import ClaimsData, TreatyTerms
from src.parser import PageSection
from src.tools import calculate_loss_ratio, check_treaty_grounding, query_historical_claims


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


_GROUNDED_SECTIONS = [
    PageSection(
        page_number=1,
        text="This Treaty is between Sentinel Mutual\nAssurance and the Reinsurer.",
    ),
    PageSection(
        page_number=2,
        text=(
            "Coverage attaches after losses exceed $200,000. The Reinsurer's "
            "liability is limited to a further $1,000,000. Annual premium: "
            "$400,000."
        ),
    ),
    PageSection(
        page_number=3,
        text="EXCLUSIONS: war or warlike operations, nuclear reaction.",
    ),
]


def _grounded_treaty(**overrides) -> TreatyTerms:
    defaults = dict(
        cedent_name="Sentinel Mutual Assurance",
        attachment_point=200_000,
        limit=1_000_000,
        reinsurance_premium=400_000,
        exclusions=["War", "Nuclear"],
        page_citations={
            "cedent_name": 1,
            "attachment_point": 2,
            "limit": 2,
            "reinsurance_premium": 2,
            "exclusions": 3,
        },
    )
    defaults.update(overrides)
    return TreatyTerms(**defaults)


def test_check_treaty_grounding_all_fields_supported_by_cited_pages():
    """Line-wrapped cedent name and $-formatted numbers should still match (whitespace/format tolerant)."""
    ungrounded = check_treaty_grounding(_grounded_treaty(), _GROUNDED_SECTIONS)

    assert ungrounded == []


def test_check_treaty_grounding_flags_unsupported_cedent_name():
    treaty = _grounded_treaty(cedent_name="Totally Different Company")

    ungrounded = check_treaty_grounding(treaty, _GROUNDED_SECTIONS)

    assert ungrounded == ["cedent_name"]


def test_check_treaty_grounding_flags_unsupported_numeric_value():
    treaty = _grounded_treaty(attachment_point=999_999)

    ungrounded = check_treaty_grounding(treaty, _GROUNDED_SECTIONS)

    assert ungrounded == ["attachment_point"]


def test_check_treaty_grounding_flags_unsupported_exclusion():
    treaty = _grounded_treaty(exclusions=["War", "Flood"])

    ungrounded = check_treaty_grounding(treaty, _GROUNDED_SECTIONS)

    assert ungrounded == ["exclusions"]


def test_check_treaty_grounding_flags_citation_pointing_at_missing_page():
    treaty = _grounded_treaty(page_citations={"cedent_name": 99})

    ungrounded = check_treaty_grounding(treaty, _GROUNDED_SECTIONS)

    assert ungrounded == ["cedent_name"]


def test_check_treaty_grounding_tolerates_hyphenated_word_broken_across_line_wrap():
    """A real PDF can hyphenate-and-wrap a word (e.g. "asbestos-\\nrelated"); the
    extracted phrase ("asbestos-related...") should still be recognized as grounded."""
    sections = [
        PageSection(
            page_number=1,
            text="EXCLUSIONS: acts of terrorism, asbestos-\nrelated bodily injury.",
        )
    ]
    treaty = _grounded_treaty(
        exclusions=["asbestos-related bodily injury"],
        page_citations={"exclusions": 1},
    )

    ungrounded = check_treaty_grounding(treaty, sections)

    assert ungrounded == []


def test_check_treaty_grounding_skips_fields_with_no_citation():
    treaty = _grounded_treaty(cedent_name="Unrelated Corp", page_citations={})

    ungrounded = check_treaty_grounding(treaty, _GROUNDED_SECTIONS)

    assert ungrounded == []


def test_calculate_loss_ratio_claim_exceeding_layer_top_is_capped():
    claims = [
        ClaimsData(cedent_name="X", claim_amount=50_000_000, claim_date=date(2025, 1, 1)),
    ]

    # Layer top = 1,000,000 + 5,000,000 = 6,000,000; claim far exceeds it,
    # so ceded amount is capped at the full limit -> ratio of 1.0.
    ratio = calculate_loss_ratio(attachment_point=1_000_000, limit=5_000_000, claims=claims)

    assert ratio == 1.0
