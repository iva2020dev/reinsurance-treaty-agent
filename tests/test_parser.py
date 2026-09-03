"""Tests for src.parser."""

import pytest

from src.parser import ParserError, extract_treaty_sections

SAMPLE_TREATY_PATH = "data/sample_treaty.pdf"


def test_extract_treaty_sections_returns_one_section_per_page():
    sections = extract_treaty_sections(SAMPLE_TREATY_PATH)

    assert len(sections) == 2
    assert [s.page_number for s in sections] == [1, 2]
    assert "Attachment Point" in sections[0].text
    assert "EXCLUSIONS" in sections[1].text


def test_extract_treaty_sections_raises_on_malformed_pdf(tmp_path):
    bad_path = tmp_path / "not_a_pdf.pdf"
    bad_path.write_bytes(b"not a pdf at all")

    with pytest.raises(ParserError):
        extract_treaty_sections(bad_path)


def test_extract_treaty_sections_raises_on_missing_file(tmp_path):
    missing_path = tmp_path / "does_not_exist.pdf"

    with pytest.raises(ParserError):
        extract_treaty_sections(missing_path)
