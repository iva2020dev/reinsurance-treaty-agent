"""Pydantic data schemas (TreatyTerms, ClaimsData, AnomalyReport)."""

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TreatyTerms(BaseModel):
    """Terms extracted from a reinsurance treaty PDF."""

    cedent_name: str = Field(min_length=1, description="The ceding insurer party to this treaty")
    attachment_point: float = Field(gt=0, description="Loss level at which reinsurance coverage begins")
    limit: float = Field(gt=0, description="Maximum reinsurance coverage above the attachment point")
    reinsurance_premium: float = Field(gt=0, description="Premium ceded to the reinsurer")
    exclusions: list[str] = Field(default_factory=list, description="Exclusion clauses")
    page_citations: dict[str, int] = Field(
        default_factory=dict,
        description="Maps a TreatyTerms field name to the source PDF page it was extracted from",
    )


class ClaimsData(BaseModel):
    """A single historical claim record for a cedent."""

    cedent_name: str = Field(min_length=1)
    claim_amount: float = Field(gt=0)
    claim_date: date


class AnomalyFinding(BaseModel):
    """A single flagged discrepancy between treaty terms and historical claims."""

    field: str
    description: str
    severity: Severity


class AnomalyReport(BaseModel):
    """Final audit report comparing treaty terms against historical claims."""

    treaty: TreatyTerms
    claims: list[ClaimsData] = Field(default_factory=list)
    loss_ratio: float = Field(ge=0)
    findings: list[AnomalyFinding] = Field(default_factory=list)
