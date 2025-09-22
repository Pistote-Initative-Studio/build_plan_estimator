from pathlib import Path

import pytest

from src.engine.pdf_parser import parse_pdf


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_parse_pdf_extracts_page_metadata():
    pdf_path = FIXTURES_DIR / "sample_plan.pdf"

    results = parse_pdf(pdf_path)

    assert isinstance(results, list)
    assert results, "Expected at least one page result"

    first_page = results[0]
    assert first_page["page_number"] == 1

    width, height = first_page["page_size"]
    assert width > 0
    assert height > 0

    assert first_page["scale"] == "1/4\" = 1'-0\""

    dimensions = first_page["dimensions"]
    assert any(dim.endswith('"') for dim in dimensions)
    assert "12'-6\"" in dimensions
    assert "15.5" in dimensions


def test_parse_pdf_missing_file():
    with pytest.raises(FileNotFoundError):
        parse_pdf(Path("does-not-exist.pdf"))
