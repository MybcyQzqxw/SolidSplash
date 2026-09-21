"""Helpers to bridge Pillow images and Qt pixmaps."""
from __future__ import annotations

from functools import lru_cache

from PIL import Image
from PySide6.QtGui import QImage, QPixmap


def pil_to_qpixmap(image: Image.Image) -> QPixmap:
    rgba = image.convert("RGBA")
    data = rgba.tobytes("raw", "RGBA")
    qimage = QImage(data, rgba.width, rgba.height, QImage.Format_RGBA8888)
    # .copy() forces Qt to own its own buffer, decoupling it from `data`.
    return QPixmap.fromImage(qimage.copy())


@lru_cache(maxsize=4)
def _checkerboard(width: int, height: int, cell: int = 12) -> Image.Image:
    light = (222, 222, 222, 255)
    dark = (188, 188, 188, 255)
    base = Image.new("RGBA", (width, height))
    pixels = base.load()
    for y in range(height):
        row_parity = (y // cell) % 2
        for x in range(width):
            col_parity = (x // cell) % 2
            pixels[x, y] = light if row_parity == col_parity else dark
    return base


def composite_on_checkerboard(image: Image.Image) -> Image.Image:
    """Flatten a transparent RGBA image onto a checkerboard for preview."""
    board = _checkerboard(image.width, image.height).copy()
    return Image.alpha_composite(board, image.convert("RGBA"))
