"""The golden dataset: treaty documents paired with known-correct TreatyTerms values.

Two documents (Acme, Meridian) are extracted by the deterministic
regex Extractor; three (Sentinel, Harborlight, Continental) are
phrased as prose that defeats regex by design, exercising the LLM
Extraction Fallback. `expected_exclusion_keywords` are short phrases
expected to appear (case-insensitive, whitespace-normalized substring)
in at least one extracted exclusion item -- not exact strings, since
an LLM's phrasing of the same clause can vary in wording even when the
underlying fact is correctly extracted.
"""

from dataclasses import dataclass, field


@dataclass
class GoldenCase:
    name: str
    pdf_path: str
    extraction_path: str  # "regex" or "llm" -- which path this case is meant to exercise
    expected_cedent_name: str
    expected_attachment_point: float
    expected_limit: float
    expected_reinsurance_premium: float
    expected_exclusion_keywords: list[str] = field(default_factory=list)


GOLDEN_DATASET: list[GoldenCase] = [
    GoldenCase(
        name="acme_minimal",
        pdf_path="data/sample_treaty.pdf",
        extraction_path="regex",
        expected_cedent_name="Acme Insurance Co.",
        expected_attachment_point=1_000_000,
        expected_limit=5_000_000,
        expected_reinsurance_premium=250_000,
        expected_exclusion_keywords=["war and warlike operations", "nuclear reaction or contamination"],
    ),
    GoldenCase(
        name="meridian_rich",
        pdf_path="data/sample_rich_treaty.pdf",
        extraction_path="regex",
        expected_cedent_name="Meridian Insurance Group, Inc.",
        expected_attachment_point=10_000_000,
        expected_limit=20_000_000,
        expected_reinsurance_premium=1_800_000,
        expected_exclusion_keywords=[
            "war, invasion",
            "nuclear reaction",
            "terrorism",
            "pollution",
            "asbestos",
            "cyber",
            "communicable disease",
            "prior to the inception",
            "fraudulent or dishonest",
            "cryptocurrency",
        ],
    ),
    GoldenCase(
        name="sentinel_fuzzy",
        pdf_path="data/sample_rich_fuzzy_treaty.pdf",
        extraction_path="llm",
        expected_cedent_name="Sentinel Mutual Assurance",
        expected_attachment_point=200_000,
        expected_limit=1_000_000,
        expected_reinsurance_premium=400_000,
        expected_exclusion_keywords=[
            "war",
            "nuclear",
            "terrorism",
            "pollution",
            "asbestos",
            "cyber",
            "pandemic",
        ],
    ),
    GoldenCase(
        name="harborlight_prose",
        pdf_path="data/golden_harborlight_treaty.pdf",
        extraction_path="llm",
        expected_cedent_name="Harborlight Mutual Insurance Company",
        expected_attachment_point=500_000,
        expected_limit=2_500_000,
        expected_reinsurance_premium=175_000,
        expected_exclusion_keywords=["war", "nuclear", "terrorism", "pollution"],
    ),
    GoldenCase(
        name="continental_prose",
        pdf_path="data/golden_continental_treaty.pdf",
        extraction_path="llm",
        expected_cedent_name="Continental Assurance Partners",
        expected_attachment_point=750_000,
        expected_limit=3_000_000,
        expected_reinsurance_premium=225_000,
        expected_exclusion_keywords=["asbestos", "cyber", "pandemic"],
    ),
]
