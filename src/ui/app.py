"""PyQt5 application scaffolding for the build plan estimator."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.engine.pdf_parser import parse_pdf


class MainWindow(QWidget):
    """Main window containing controls for selecting and displaying PDF data."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Build Plan Estimator")
        self.resize(640, 480)

        self._select_button = QPushButton("Select PDF", self)
        self._select_button.clicked.connect(self._handle_select_pdf)

        self._results_view = QTextEdit(self)
        self._results_view.setReadOnly(True)
        self._results_view.setPlaceholderText(
            "Select a PDF to view placeholder parsing results."
        )

        layout = QVBoxLayout()
        layout.addWidget(self._select_button)
        layout.addWidget(self._results_view)
        self.setLayout(layout)

    def _handle_select_pdf(self) -> None:
        """Prompt the user for a PDF file and display placeholder parse data."""

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF",
            str(Path.home()),
            "PDF Files (*.pdf);;All Files (*)",
        )
        if not file_path:
            return

        try:
            parsed_data = parse_pdf(file_path)
        except Exception as exc:  # pragma: no cover - UI feedback path
            QMessageBox.critical(
                self,
                "Parsing Error",
                f"An error occurred while parsing the PDF:\n{exc}",
            )
            return

        formatted = json.dumps(parsed_data, indent=2)
        self._results_view.setPlainText(formatted)


def run_app() -> None:
    """Create and execute the Qt application."""

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    app.exec_()
