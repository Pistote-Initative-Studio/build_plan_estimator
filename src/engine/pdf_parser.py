"""Stubbed PDF parsing utilities for the desktop application scaffold."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

ParsedPDFMetadata = Dict[str, Any]


def parse_pdf(file_path: str | Path) -> ParsedPDFMetadata:  # noqa: ARG001
    """Return placeholder data for the provided PDF file path."""

    return {
        "page_number": 1,
        "page_size": [1000, 2000],
        "scale": "1/4\" = 1'-0\"",
        "dimensions": ["12'-6\"", "15.5"],
    }
