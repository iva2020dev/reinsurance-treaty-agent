"""Registry of prepared/golden treaty sample PDFs bundled with the repo.

Backs the Streamlit "Choose a reinsurance treaty" selector (`src/app.py`)
so a user can start an analysis without uploading a file from their own
disk. Every sample here ships in `data/` as part of the repo itself --
never a path picked from the user's local machine.
"""

from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR = _REPO_ROOT / "data"


@dataclass(frozen=True)
class SampleTreaty:
    id: str
    label: str
    filename: str  # PDF filename under data/

    @property
    def path(self) -> Path:
        return _DATA_DIR / self.filename


# Same 5 documents as tests/eval/golden_dataset.py's GOLDEN_DATASET
# (kept as an independent list, since src/ shouldn't import from tests/).
SAMPLE_TREATIES: list[SampleTreaty] = [
    SampleTreaty(
        id="acme_minimal",
        label="Acme Insurance Co. — minimal treaty (regex extraction)",
        filename="sample_treaty.pdf",
    ),
    SampleTreaty(
        id="meridian_rich",
        label="Meridian Insurance Group — rich treaty (regex extraction)",
        filename="sample_rich_treaty.pdf",
    ),
    SampleTreaty(
        id="sentinel_fuzzy",
        label="Sentinel Mutual Assurance — fuzzy prose (LLM fallback)",
        filename="sample_rich_fuzzy_treaty.pdf",
    ),
    SampleTreaty(
        id="harborlight_prose",
        label="Harborlight Mutual Insurance — prose treaty (LLM fallback)",
        filename="golden_harborlight_treaty.pdf",
    ),
    SampleTreaty(
        id="continental_prose",
        label="Continental Assurance Partners — prose treaty (LLM fallback)",
        filename="golden_continental_treaty.pdf",
    ),
]


def get_sample_bytes(sample: SampleTreaty) -> bytes:
    """Read a sample treaty's PDF bytes from its bundled path under data/."""
    return sample.path.read_bytes()
