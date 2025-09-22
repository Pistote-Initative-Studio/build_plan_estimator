"""Tests for the placeholder PDF parser implementation."""

from __future__ import annotations

from src.engine.pdf_parser import parse_pdf


EXPECTED_KEYS = {"page_number", "page_size", "scale", "dimensions"}


def test_parse_pdf_returns_placeholder_data() -> None:
    result = parse_pdf("fake.pdf")

    assert isinstance(result, dict)
    assert EXPECTED_KEYS.issubset(result.keys())
    assert result["page_number"] == 1
    assert isinstance(result["page_size"], list)
    assert len(result["page_size"]) == 2
    assert isinstance(result["dimensions"], list)
    assert "12'-6\"" in result["dimensions"]


def test_parse_pdf_accepts_pathlike() -> None:
    class DummyPath:
        def __fspath__(self) -> str:
            return "dummy.pdf"

    result = parse_pdf(DummyPath())
    assert result["page_number"] == 1
