"""Tests for the PDF rendering and room detection helpers."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PyQt5.QtGui import QImage

from src.engine.pdf_parser import (
    RoomEstimate,
    detect_rooms,
    parse_pdf,
    render_pdf_to_image,
)


FIXTURE = Path("tests/fixtures/sample_plan.pdf")


def test_render_pdf_to_image_produces_qimage_and_array() -> None:
    image, array = render_pdf_to_image(FIXTURE)

    assert isinstance(image, QImage)
    assert isinstance(array, np.ndarray)
    assert array.ndim == 3 and array.shape[2] == 4
    assert image.width() == array.shape[1]
    assert image.height() == array.shape[0]


def test_detect_rooms_returns_estimates() -> None:
    _, array = render_pdf_to_image(FIXTURE)
    rooms = detect_rooms(array)

    assert rooms, "Expected to detect at least one room"
    assert all(isinstance(room, RoomEstimate) for room in rooms)
    for estimate in rooms:
        x, y, w, h = estimate.rect
        assert w > 0 and h > 0
        assert estimate.flooring_sqft > 0
        assert estimate.drywall_sqft > 0
        assert estimate.studs > 0


def test_parse_pdf_returns_summary_totals() -> None:
    summary = parse_pdf(FIXTURE)

    assert summary["page_number"] == 1
    assert summary["room_count"] >= 0
    totals = summary["totals"]
    assert {"flooring_sqft", "drywall_sqft", "studs"} <= totals.keys()
