"""PDF ingestion and text extraction."""

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class ParserError(Exception):
    """Raised when a treaty PDF cannot be read or contains no extractable text."""


@dataclass
class PageSection:
    """One page's extracted text, tagged with its source page number."""

    page_number: int  # 1-indexed, for citation purposes
    text: str


def extract_treaty_sections(path: str | Path) -> list[PageSection]:
    """Extract text from a treaty PDF, one section per page, with page citations.

    Raises ParserError if the file cannot be opened as a PDF, or if no
    text at all can be extracted from any page (e.g. a scanned/image-only PDF).
    """
    try:
        reader = PdfReader(path)
        sections = [
            PageSection(page_number=i + 1, text=page.extract_text() or "")
            for i, page in enumerate(reader.pages)
        ]
    except (PdfReadError, OSError, ValueError) as exc:
        raise ParserError(f"Could not read PDF at {path!s}: {exc}") from exc

    if not any(section.text.strip() for section in sections):
        raise ParserError(f"No extractable text found in PDF at {path!s}")

    return sections
