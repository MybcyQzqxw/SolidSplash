"""Core, UI-agnostic image processing for SolidSplash.

All functions here are read-only with respect to the user's source files:
images are always opened, processed in memory and returned as new Pillow
``Image`` objects. The original files on disk are never modified.
"""
from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

from .constants import CANVAS_HEIGHT, CANVAS_WIDTH, MIN_IMAGE_HEIGHT


class ImageValidationError(Exception):
    """Raised when a candidate image cannot be accepted into the project."""


@dataclass(frozen=True)
class ImageInfo:
    path: str
    width: int
    height: int


def load_image_info(path: str) -> ImageInfo:
    """Open ``path`` and validate it as a usable source image.

    Raises ``ImageValidationError`` if the file is not a PNG, or is too
    short to produce an acceptable result.
    """
    with Image.open(path) as img:
        img.load()
        if (img.format or "").upper() != "PNG":
            raise ImageValidationError(f"{path} 不是 PNG 格式的图片，已忽略")
        width, height = img.size

    if height < MIN_IMAGE_HEIGHT:
        raise ImageValidationError(
            f"图片高度仅 {height}px（小于 {MIN_IMAGE_HEIGHT}px），图片过小，处理效果不佳，已拒绝上传"
        )
    return ImageInfo(path=path, width=width, height=height)


def compute_max_scale(max_height: int) -> float:
    """Return the largest scale factor (<=1.0) that keeps ``max_height``
    within ``CANVAS_HEIGHT`` once scaled."""
    if max_height > CANVAS_HEIGHT:
        return round(CANVAS_HEIGHT / max_height, 4)
    return 1.0


def process_image(path: str, scale: float, offset_x: int, offset_y: int) -> Image.Image:
    """Scale the source image and place it on a transparent 900x604 canvas.

    The scaled image's bottom-right corner sits ``offset_x``/``offset_y``
    pixels away from the canvas's bottom-right corner. The source file on
    disk is never touched.
    """
    with Image.open(path) as src:
        src.load()
        rgba = src.convert("RGBA")

    new_w = max(1, round(rgba.width * scale))
    new_h = max(1, round(rgba.height * scale))
    scaled = rgba.resize((new_w, new_h), Image.LANCZOS)

    canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))
    right = CANVAS_WIDTH - offset_x
    bottom = CANVAS_HEIGHT - offset_y
    left = right - new_w
    top = bottom - new_h
    canvas.paste(scaled, (left, top), scaled)
    return canvas
