"""PDF utilities for rendering plan pages and estimating materials."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import fitz
import numpy as np
from PyQt5.QtGui import QImage

try:
    import cv2
except ImportError as exc:  # pragma: no cover - dependency error path
    raise RuntimeError(
        "OpenCV (cv2) is required for room detection but is not installed"
    ) from exc

PIXEL_TO_FEET = 0.1
WALL_HEIGHT_FT = 8.0
STUD_SPACING_FT = 16.0 / 12.0


@dataclass(frozen=True)
class RoomEstimate:
    """Container describing a detected room and the material estimates."""

    rect: tuple[int, int, int, int]
    flooring_sqft: float
    drywall_sqft: float
    studs: int


def _ensure_path(file_path: str | Path) -> Path:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    return path


def render_pdf_to_image(file_path: str | Path) -> tuple[QImage, np.ndarray]:
    """Render the first page of *file_path* and return it as a Qt image."""

    path = _ensure_path(file_path)
    document = fitz.open(path)
    if document.page_count == 0:
        raise ValueError("The provided PDF does not contain any pages")

    page = document.load_page(0)
    zoom_matrix = fitz.Matrix(2.0, 2.0)
    pixmap = page.get_pixmap(matrix=zoom_matrix, alpha=False)

    if pixmap.n == 4:
        image_format = QImage.Format_RGBA8888
    elif pixmap.n == 3:
        image_format = QImage.Format_RGB888
    else:
        image_format = QImage.Format_Grayscale8

    image = QImage(
        pixmap.samples,
        pixmap.width,
        pixmap.height,
        pixmap.stride,
        image_format,
    ).copy()

    row_stride = pixmap.stride
    array = np.frombuffer(pixmap.samples, dtype=np.uint8).copy()
    array = array.reshape((pixmap.height, row_stride))
    array = array[:, : pixmap.width * pixmap.n]
    array = array.reshape((pixmap.height, pixmap.width, pixmap.n))

    if pixmap.n == 1:
        array = np.repeat(array, 3, axis=2)

    if array.shape[2] == 3:
        alpha_channel = np.full(
            (pixmap.height, pixmap.width, 1), 255, dtype=np.uint8
        )
        array = np.concatenate([array, alpha_channel], axis=2)

    return image, array


def _qimage_to_numpy(image: QImage) -> np.ndarray:
    converted = image.convertToFormat(QImage.Format_RGBA8888)
    ptr = converted.bits()
    bytes_per_line = converted.bytesPerLine()
    ptr.setsize(converted.height() * bytes_per_line)
    array = np.frombuffer(ptr, dtype=np.uint8).copy()
    array = array.reshape((converted.height(), bytes_per_line))
    array = array[:, : converted.width() * 4]
    array = array.reshape((converted.height(), converted.width(), 4))
    return array


def _filter_contours(
    contours: Iterable[np.ndarray],
    width: int,
    height: int,
) -> List[np.ndarray]:
    filtered: List[np.ndarray] = []
    min_area = max(width * height * 0.0005, 2000)
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < min_area:
            continue
        if w >= width * 0.95 and h >= height * 0.95:
            continue
        filtered.append(contour)
    return filtered


def detect_rooms(image: QImage | np.ndarray) -> list[RoomEstimate]:
    """Identify room-like regions within *image* and estimate materials."""

    if isinstance(image, QImage):
        rgba = _qimage_to_numpy(image)
    else:
        rgba = image

    if rgba.ndim != 3 or rgba.shape[2] not in {3, 4}:
        raise ValueError("Image must be an RGB or RGBA array")

    if rgba.shape[2] == 4:
        bgr = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)
    else:
        bgr = cv2.cvtColor(rgba, cv2.COLOR_RGB2BGR)

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV,
        25,
        5,
    )
    kernel = np.ones((5, 5), np.uint8)
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(
        closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    contours = _filter_contours(contours, rgba.shape[1], rgba.shape[0])

    estimates: list[RoomEstimate] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        width_ft = w * PIXEL_TO_FEET
        height_ft = h * PIXEL_TO_FEET
        area_sqft = width_ft * height_ft
        perimeter_ft = 2 * (width_ft + height_ft)
        drywall_sqft = perimeter_ft * WALL_HEIGHT_FT
        studs_count = max(1, int(np.ceil(perimeter_ft / STUD_SPACING_FT)))

        estimates.append(
            RoomEstimate(
                rect=(x, y, w, h),
                flooring_sqft=round(area_sqft, 2),
                drywall_sqft=round(drywall_sqft, 2),
                studs=studs_count,
            )
        )

    estimates.sort(key=lambda estimate: estimate.flooring_sqft, reverse=True)
    return estimates


def parse_pdf(file_path: str | Path) -> dict:
    """Parse *file_path* and return summary data used by tests."""

    image, array = render_pdf_to_image(file_path)
    rooms = detect_rooms(array)

    totals = {
        "flooring_sqft": round(sum(room.flooring_sqft for room in rooms), 2),
        "drywall_sqft": round(sum(room.drywall_sqft for room in rooms), 2),
        "studs": sum(room.studs for room in rooms),
    }

    return {
        "page_number": 1,
        "image_size": [image.width(), image.height()],
        "room_count": len(rooms),
        "totals": totals,
    }
