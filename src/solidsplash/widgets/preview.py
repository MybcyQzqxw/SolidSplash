"""Live preview widget that shows the processed splash image."""
from __future__ import annotations

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from ..constants import CANVAS_HEIGHT, CANVAS_WIDTH
from .qt_image_utils import composite_on_checkerboard, pil_to_qpixmap


class PreviewWidget(QWidget):
    """Displays a 900x604-ratio preview, scaled down to fit the panel.

    Transparent regions are rendered as a checkerboard, matching how they
    will look once exported and reused elsewhere.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._source_pixmap: QPixmap | None = None

        self._label = QLabel("拖入或选择 PNG 图片以查看预览")
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setMinimumSize(180, int(180 * CANVAS_HEIGHT / CANVAS_WIDTH))
        self._label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._label.setStyleSheet(
            "QLabel { background-color: #2a2a2a; color: #888; border: 1px solid #3c3c3c; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)

    def set_image(self, image: Image.Image) -> None:
        flattened = composite_on_checkerboard(image)
        self._source_pixmap = pil_to_qpixmap(flattened)
        self._refresh()

    def clear(self) -> None:
        self._source_pixmap = None
        self._label.setText("拖入或选择 PNG 图片以查看预览")
        self._label.setPixmap(QPixmap())

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self) -> None:
        if self._source_pixmap is None:
            return
        target = self._label.size()
        scaled = self._source_pixmap.scaled(
            target, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self._label.setPixmap(scaled)
