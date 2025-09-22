"""PyQt5 application for viewing PDF plans and material estimates."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QMessageBox,
    QGraphicsScene,
    QGraphicsView,
    QGraphicsRectItem,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QVBoxLayout,
    QWidget,
)

from src.engine.pdf_parser import (
    detect_rooms,
    render_pdf_to_image,
)


class MainWindow(QWidget):
    """Main window containing controls for selecting and displaying PDF data."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Build Plan Estimator")
        self.resize(1024, 768)

        self._select_button = QPushButton("Select PDF", self)
        self._select_button.clicked.connect(self._handle_select_pdf)

        self._scene = QGraphicsScene(self)
        self._graphics_view = QGraphicsView(self._scene, self)
        self._graphics_view.setRenderHints(
            QPainter.Antialiasing | QPainter.SmoothPixmapTransform
        )
        self._graphics_view.setDragMode(QGraphicsView.ScrollHandDrag)

        self._table = QTableWidget(self)
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(
            ["Room #", "Flooring (sqft)", "Drywall (sqft)", "Studs"]
        )
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.NoSelection)

        self._splitter = QSplitter(Qt.Horizontal, self)
        self._splitter.addWidget(self._graphics_view)
        self._splitter.addWidget(self._table)
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 1)

        layout = QVBoxLayout()
        layout.addWidget(self._select_button)
        layout.addWidget(self._splitter)
        self.setLayout(layout)

    def _handle_select_pdf(self) -> None:
        """Prompt for a PDF, render it, and display detected room estimates."""

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF",
            str(Path.home()),
            "PDF Files (*.pdf);;All Files (*)",
        )
        if not file_path:
            return

        try:
            image, array = render_pdf_to_image(file_path)
        except Exception as exc:  # pragma: no cover - UI feedback path
            QMessageBox.critical(
                self,
                "Render Error",
                f"Unable to render the PDF page:\n{exc}",
            )
            return

        pixmap = QPixmap.fromImage(image)
        self._scene.clear()
        self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(pixmap.rect())

        try:
            room_estimates = detect_rooms(array)
        except Exception as exc:  # pragma: no cover - UI feedback path
            QMessageBox.warning(
                self,
                "Detection Error",
                f"Failed to detect rooms in the PDF:\n{exc}",
            )
            room_estimates = []

        self._draw_room_overlays(room_estimates)
        self._populate_table(room_estimates)

    def _draw_room_overlays(self, room_estimates) -> None:
        pen = QPen(QColor("red"))
        pen.setWidth(2)
        for index, estimate in enumerate(room_estimates, start=1):
            x, y, w, h = estimate.rect
            rect_item = QGraphicsRectItem(x, y, w, h)
            rect_item.setPen(pen)
            rect_item.setZValue(1)
            rect_item.setToolTip(
                f"Room {index}\n"
                f"Flooring: {estimate.flooring_sqft} sqft\n"
                f"Drywall: {estimate.drywall_sqft} sqft\n"
                f"Studs: {estimate.studs}"
            )
            self._scene.addItem(rect_item)

    def _populate_table(self, room_estimates) -> None:
        self._table.setRowCount(len(room_estimates))
        for row, estimate in enumerate(room_estimates, start=0):
            room_item = QTableWidgetItem(str(row + 1))
            room_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 0, room_item)

            flooring_item = QTableWidgetItem(f"{estimate.flooring_sqft:.2f}")
            flooring_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 1, flooring_item)

            drywall_item = QTableWidgetItem(f"{estimate.drywall_sqft:.2f}")
            drywall_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 2, drywall_item)

            studs_item = QTableWidgetItem(str(estimate.studs))
            studs_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 3, studs_item)


def run_app() -> None:
    """Create and execute the Qt application."""

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    app.exec_()
