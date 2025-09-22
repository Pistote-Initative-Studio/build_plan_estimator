"""Utilities for parsing plan PDFs for basic measurement metadata."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List, Sequence

import pdfplumber

# Normalization helpers for quote and dash characters that commonly appear in PDFs.
_CHARACTER_TRANSLATION = str.maketrans(
    {
        "’": "'",
        "‘": "'",
        "′": "'",
        "“": '"',
        "”": '"',
        "″": '"',
        "–": "-",
        "—": "-",
        "−": "-",
    }
)

# Regex designed to capture scale annotations such as `1/4" = 1'-0"`.
_SCALE_PATTERN = re.compile(
    r"""
    (?:
        \d+\s*/\s*\d+\s*[\"”″]?   # fraction with optional inch mark
    )
    \s*=\s*
    (?:
        \d+\s*[’'′]\s*-?\s*\d+[\"”″]?  # feet-inches with optional hyphen and inch mark
    )
    """,
    re.VERBOSE,
)

# Regex patterns that represent common dimension formats we want to extract.
_DIMENSION_PATTERNS: Sequence[re.Pattern[str]] = (
    # Feet and inches, e.g. 12'-6" or 8' 0"
    re.compile(r"\d+\s*[’'′]\s*-?\s*\d+[\"”″]?"),
    # Inch-only values such as 9" (avoid matching the inch component of a feet-inch value)
    re.compile(r"(?<![\d-])\d+\s*[\"”″]"),
    # Decimal values like 15.5
    re.compile(r"\d+\.\d+"),
    # Fractional values such as 1/4"
    re.compile(r"\d+\s*/\s*\d+[\"”″]?"),
)


def _normalize_characters(value: str) -> str:
    """Replace curly quotes and dashes with their ASCII counterparts."""
    return value.translate(_CHARACTER_TRANSLATION)


def _collapse_whitespace(value: str) -> str:
    """Collapse whitespace runs into single spaces and trim the result."""
    return " ".join(value.split())


def _normalize_measurement(value: str) -> str:
    """Standardize measurement text for consistent downstream comparisons."""
    value = _normalize_characters(value)
    value = value.strip()
    # Remove superfluous whitespace around separators that commonly appear in measurements.
    value = re.sub(r"\s*/\s*", "/", value)
    value = re.sub(r"\s*-\s*", "-", value)
    value = re.sub(r"\s*'\s*", "'", value)
    value = re.sub(r'\s*"\s*', '"', value)
    return value


def _normalize_scale(value: str) -> str:
    """Normalize scale annotations to a consistent textual representation."""
    value = _normalize_characters(value)
    value = re.sub(r"\s*/\s*", "/", value)
    value = re.sub(r"\s*-\s*", "-", value)
    value = re.sub(r"\s*'\s*", "'", value)
    value = re.sub(r'\s*"\s*', '"', value)
    value = re.sub(r"\s*=\s*", " = ", value)
    return _collapse_whitespace(value)


def _extract_scale(text: str) -> str | None:
    """Locate and normalize the first scale annotation found in the supplied text."""
    if not text:
        return None
    match = _SCALE_PATTERN.search(_normalize_characters(text))
    if not match:
        return None
    return _normalize_scale(match.group(0))


def _iter_dimension_strings(texts: Iterable[str]) -> Iterable[str]:
    for text in texts:
        if not text:
            continue
        normalized = _normalize_characters(text)
        for pattern in _DIMENSION_PATTERNS:
            for match in pattern.finditer(normalized):
                yield _normalize_measurement(match.group(0))


def _extract_dimensions(texts: Iterable[str], scale: str | None) -> List[str]:
    """Extract unique dimension strings from the provided text fragments."""
    seen: List[str] = []
    for measurement in _iter_dimension_strings(texts):
        if not measurement:
            continue
        if scale and measurement in scale:
            # Avoid echoing dimension fragments that originate from the scale annotation itself.
            continue
        if measurement not in seen:
            seen.append(measurement)
    return seen


def parse_pdf(file_path: str | Path) -> List[dict]:
    """Parse a PDF and return per-page metadata for use in takeoff estimation.

    The result is a list of dictionaries, each containing:
        - ``page_number``: 1-based index of the page in the PDF
        - ``page_size``: tuple of page width and height in points
        - ``scale``: detected scale annotation text, or ``None`` if not found
        - ``dimensions``: ordered list of distinct dimension-like strings discovered on the page
    """

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    results: List[dict] = []
    with pdfplumber.open(str(path)) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ""
            scale = _extract_scale(page_text)

            text_fragments: List[str] = [page_text]
            try:
                for word in page.extract_words():
                    value = word.get("text")
                    if value:
                        text_fragments.append(value)
            except Exception:
                # ``extract_words`` can fail on some PDFs; fall back to the raw text only.
                pass

            dimensions = _extract_dimensions(text_fragments, scale)
            results.append(
                {
                    "page_number": page_number,
                    "page_size": (page.width, page.height),
                    "scale": scale,
                    "dimensions": dimensions,
                }
            )
    return results
