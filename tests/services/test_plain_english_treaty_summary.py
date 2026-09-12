"""Tests for src.services.plain_english_treaty_summary."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.models import TreatyTerms
from src.parser import PageSection
from src.services.plain_english_treaty_summary import generate_plain_english_treaty_summary

TREATY = TreatyTerms(
    cedent_name="Test Cedent Co.",
    attachment_point=100_000,
    limit=200_000,
    reinsurance_premium=10_000,
    exclusions=["War", "Nuclear"],
)
SECTIONS = [PageSection(page_number=1, text="Cedent: Test Cedent Co.")]


def test_generate_plain_english_treaty_summary_returns_text_from_response(monkeypatch):
    text_block = SimpleNamespace(type="text", text="A short plain-English summary.")
    mock_client = MagicMock()
    mock_usage = SimpleNamespace(input_tokens=128, output_tokens=32)
    mock_client.messages.create.return_value = SimpleNamespace(content=[text_block], usage=mock_usage)
    monkeypatch.setattr("src.llm_client.anthropic.Anthropic", lambda **kwargs: mock_client)

    summary = generate_plain_english_treaty_summary(TREATY, SECTIONS)

    assert summary == "A short plain-English summary."
    mock_client.messages.create.assert_called_once()
    prompt = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "Test Cedent Co." in prompt
    assert "100,000" in prompt
    assert "War" in prompt


def test_generate_plain_english_treaty_summary_concatenates_multiple_text_blocks(monkeypatch):
    blocks = [
        SimpleNamespace(type="text", text="First part."),
        SimpleNamespace(type="text", text=" Second part."),
    ]
    mock_client = MagicMock()
    mock_usage = SimpleNamespace(input_tokens=1, output_tokens=1)
    mock_client.messages.create.return_value = SimpleNamespace(content=blocks, usage=mock_usage)
    monkeypatch.setattr("src.llm_client.anthropic.Anthropic", lambda **kwargs: mock_client)

    summary = generate_plain_english_treaty_summary(TREATY, SECTIONS)

    assert summary == "First part. Second part."


def test_generate_plain_english_treaty_summary_propagates_failure_after_retries_exhausted(monkeypatch):
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = RuntimeError("boom")
    monkeypatch.setattr("src.llm_client.anthropic.Anthropic", lambda **kwargs: mock_client)

    with pytest.raises(RuntimeError, match="boom"):
        generate_plain_english_treaty_summary(TREATY, SECTIONS)
