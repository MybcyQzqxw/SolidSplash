"""Main application window wiring the UI together with the image pipeline."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .constants import (
    OFFSET_STEP,
    OFFSET_X_MAX,
    OFFSET_Y_MAX,
    SCALE_MIN,
    SCALE_STEP,
    THUMBNAIL_SIZE,
)
from .image_processing import ImageValidationError, compute_max_scale, load_image_info, process_image
from .widgets.console import ConsoleWidget
from .widgets.drop_area import DropArea
from .widgets.preview import PreviewWidget

_BUTTON_STYLE = """
QPushButton#PrimaryButton {
    background-color: #e3a8ba;
    color: #5c2436;
    border: none;
    border-radius: 4px;
    padding: 8px 20px;
    font-weight: bold;
}
QPushButton#PrimaryButton:disabled {
    background-color: #f2e2e7;
    color: #bda0a8;
}
QPushButton#PrimaryButton:hover:!disabled {
    background-color: #d88fa5;
}
"""


@dataclass
class _ImageRecord:
    path: str
    width: int
    height: int
    processed: Optional[Image.Image] = field(default=None, repr=False)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SolidSplash - SOLIDWORKS 启动画面个性化工具")
        self.resize(1180, 720)
        self.setStyleSheet(_BUTTON_STYLE)

        self._images: Dict[str, _ImageRecord] = {}
        self._order: List[str] = []
        self._has_converted_cache = False

        self._build_ui()
        self._connect_signals()
        self._update_buttons()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)

        splitter = QSplitter(Qt.Horizontal)
        root_layout.addWidget(splitter)

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 4)

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self.drop_area = DropArea()
        self.drop_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(QLabel("源图片（PNG）"))
        layout.addWidget(self.drop_area, 1)

        layout.addWidget(self._build_params_group())

        btn_row = QHBoxLayout()
        self.convert_btn = QPushButton("转换")
        self.convert_btn.setObjectName("PrimaryButton")
        self.export_btn = QPushButton("导出")
        self.export_btn.setObjectName("PrimaryButton")
        btn_row.addWidget(self.convert_btn)
        btn_row.addWidget(self.export_btn)
        layout.addLayout(btn_row)

        layout.addWidget(self._build_output_group())

        return panel

    def _build_params_group(self) -> QGroupBox:
        group = QGroupBox("参数")
        layout = QVBoxLayout(group)

        scale_row = QHBoxLayout()
        scale_row.addWidget(QLabel("缩小倍数"))
        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setDecimals(2)
        self.scale_spin.setSingleStep(SCALE_STEP)
        self.scale_spin.setRange(SCALE_MIN, 1.0)
        self.scale_spin.setValue(1.0)
        self.scale_spin.setEnabled(False)
        scale_row.addWidget(self.scale_spin, 1)
        layout.addLayout(scale_row)

        offset_row = QHBoxLayout()
        offset_row.addWidget(QLabel("横向偏移(px)"))
        self.offset_x_spin = QSpinBox()
        self.offset_x_spin.setRange(0, OFFSET_X_MAX)
        self.offset_x_spin.setSingleStep(OFFSET_STEP)
        self.offset_x_spin.setValue(0)
        offset_row.addWidget(self.offset_x_spin, 1)

        offset_row.addWidget(QLabel("纵向偏移(px)"))
        self.offset_y_spin = QSpinBox()
        self.offset_y_spin.setRange(0, OFFSET_Y_MAX)
        self.offset_y_spin.setSingleStep(OFFSET_STEP)
        self.offset_y_spin.setValue(0)
        offset_row.addWidget(self.offset_y_spin, 1)
        layout.addLayout(offset_row)

        return group

    def _build_output_group(self) -> QGroupBox:
        group = QGroupBox("输出目录")
        layout = QHBoxLayout(group)
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("选择或输入导出文件夹路径")
        browse_btn = QPushButton("浏览…")
        browse_btn.clicked.connect(self._on_browse_output)
        layout.addWidget(self.output_edit, 1)
        layout.addWidget(browse_btn)
        return group

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        layout.addWidget(QLabel("预览（透明区域以马赛克显示）"))
        self.preview = PreviewWidget()
        layout.addWidget(self.preview, 3)

        layout.addWidget(QLabel("运行日志"))
        self.console = ConsoleWidget()
        layout.addWidget(self.console, 2)

        return panel

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------
    def _connect_signals(self) -> None:
        self.drop_area.add_files_requested.connect(self._on_add_files_requested)
        self.drop_area.remove_item_requested.connect(self._on_remove_item_requested)
        self.drop_area.selection_changed.connect(lambda _id: self._update_preview())

        self.scale_spin.valueChanged.connect(self._update_preview)
        self.offset_x_spin.valueChanged.connect(self._update_preview)
        self.offset_y_spin.valueChanged.connect(self._update_preview)

        self.convert_btn.clicked.connect(self._on_convert)
        self.export_btn.clicked.connect(self._on_export)

        self.console.info("欢迎使用 SolidSplash，请拖入 PNG 图片开始。")

    # ------------------------------------------------------------------
    # Image list management
    # ------------------------------------------------------------------
    def _on_add_files_requested(self, paths: List[str]) -> None:
        existing_paths = {rec.path for rec in self._images.values()}
        added_any = False

        for raw_path in paths:
            path = raw_path.strip().strip('"')
            if not path:
                continue
            name = Path(path).name

            if not path.lower().endswith(".png"):
                self.console.warn(f"{name} 不是 PNG 文件，已忽略")
                continue
            if not os.path.isfile(path):
                self.console.warn(f"文件不存在：{path}")
                continue
            if path in existing_paths:
                self.console.warn(f"{name} 已在列表中，跳过重复添加")
                continue

            try:
                info = load_image_info(path)
            except ImageValidationError as exc:
                self.console.warn(f"{name}：{exc}")
                continue
            except Exception as exc:  # noqa: BLE001 - surface any decode error to the user
                self.console.warn(f"无法读取 {name}：{exc}")
                continue

            item_id = str(uuid4())
            self._images[item_id] = _ImageRecord(path=path, width=info.width, height=info.height)
            self._order.append(item_id)
            existing_paths.add(path)

            thumbnail = QPixmap(path).scaled(
                THUMBNAIL_SIZE, THUMBNAIL_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.drop_area.add_item(item_id, name, f"{info.width}x{info.height}", thumbnail)
            self.console.success(f"已添加：{name}（{info.width}x{info.height}）")
            added_any = True

        if added_any:
            self._recompute_scale_range()
            self._check_size_consistency()
            self._update_buttons()
            self._update_preview()

    def _on_remove_item_requested(self, item_id: str) -> None:
        rec = self._images.pop(item_id, None)
        if rec is None:
            return
        self._order.remove(item_id)
        self.drop_area.remove_item(item_id)
        self.console.info(f"已移除：{Path(rec.path).name}")

        self._recompute_scale_range()
        self._update_buttons()
        self._update_preview()

    def _recompute_scale_range(self) -> None:
        if not self._images:
            self.scale_spin.setEnabled(False)
            self.scale_spin.blockSignals(True)
            self.scale_spin.setRange(SCALE_MIN, 1.0)
            self.scale_spin.setValue(1.0)
            self.scale_spin.blockSignals(False)
            return

        self.scale_spin.setEnabled(True)
        max_height = max(rec.height for rec in self._images.values())
        max_scale = compute_max_scale(max_height)

        self.scale_spin.blockSignals(True)
        self.scale_spin.setRange(SCALE_MIN, max_scale)
        self.scale_spin.setValue(max_scale)
        self.scale_spin.blockSignals(False)

        if max_height > 604:
            self.console.info(
                f"检测到最高图片为 {max_height}px，已将缩小倍数上限与当前值设为 {max_scale:.2f}"
            )

    def _check_size_consistency(self) -> None:
        heights = [rec.height for rec in self._images.values()]
        if len(heights) < 2:
            return
        max_h, min_h = max(heights), min(heights)
        if max_h != min_h:
            ratio = max_h / min_h
            self.console.warn(
                f"检测到图片尺寸不一致：最高 {max_h}px，最低 {min_h}px（比例 {ratio:.2f}:1），"
                "建议使用尺寸一致的图片以获得最佳效果"
            )

    # ------------------------------------------------------------------
    # Button state management
    # ------------------------------------------------------------------
    def _update_buttons(self) -> None:
        has_images = bool(self._images)
        self.convert_btn.setEnabled(has_images)
        if not has_images:
            self._has_converted_cache = False
        self.export_btn.setEnabled(self._has_converted_cache)

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------
    def _update_preview(self) -> None:
        if not self._images:
            self.preview.clear()
            return

        item_id = self.drop_area.current_item_id() or self._order[0]
        rec = self._images.get(item_id) or self._images[self._order[0]]

        try:
            image = process_image(
                rec.path, self.scale_spin.value(), self.offset_x_spin.value(), self.offset_y_spin.value()
            )
        except Exception as exc:  # noqa: BLE001
            self.console.warn(f"预览生成失败：{exc}")
            return
        self.preview.set_image(image)

    # ------------------------------------------------------------------
    # Convert / export
    # ------------------------------------------------------------------
    def _on_convert(self) -> None:
        scale = self.scale_spin.value()
        offset_x = self.offset_x_spin.value()
        offset_y = self.offset_y_spin.value()

        self.console.info(
            f"开始转换（缩小倍数={scale:.2f}，横向偏移={offset_x}px，纵向偏移={offset_y}px）…"
        )
        ok_count = 0
        for item_id in self._order:
            rec = self._images[item_id]
            try:
                rec.processed = process_image(rec.path, scale, offset_x, offset_y)
                ok_count += 1
            except Exception as exc:  # noqa: BLE001
                self.console.warn(f"转换失败：{Path(rec.path).name}：{exc}")

        if ok_count:
            self._has_converted_cache = True
            self.console.success(f"转换完成，共处理 {ok_count} 张图片")
        self._update_buttons()
        self._update_preview()

    def _on_browse_output(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择输出文件夹", self.output_edit.text())
        if directory:
            self.output_edit.setText(directory)

    def _on_export(self) -> None:
        out_dir_text = self.output_edit.text().strip()
        if not out_dir_text:
            self.console.warn("请先选择或输入输出文件夹")
            return

        out_dir = Path(out_dir_text)
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:  # noqa: BLE001
            self.console.error(f"无法创建输出目录：{exc}")
            return

        exported = 0
        for item_id in self._order:
            rec = self._images[item_id]
            if rec.processed is None:
                continue
            out_name = f"{Path(rec.path).stem}_splash.png"
            out_path = out_dir / out_name
            try:
                rec.processed.save(out_path, format="PNG")
                exported += 1
            except Exception as exc:  # noqa: BLE001
                self.console.warn(f"导出失败：{out_name}：{exc}")

        if exported:
            self.console.success(f"导出完成，共导出 {exported} 张图片到 {out_dir}")
        else:
            self.console.warn("没有可导出的图片，请先点击“转换”")
