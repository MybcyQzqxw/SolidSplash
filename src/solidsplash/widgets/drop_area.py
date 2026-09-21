"""Drag-and-drop capable image list with per-item delete controls."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..constants import THUMBNAIL_SIZE

_ITEM_ID_ROLE = Qt.UserRole + 1


class _ImageRow(QWidget):
    """One row in the drop list: thumbnail + name + delete button."""

    delete_requested = Signal(str)

    def __init__(self, item_id: str, display_name: str, subtitle: str, thumbnail: QPixmap, parent=None):
        super().__init__(parent)
        self._item_id = item_id

        thumb_label = QLabel()
        thumb_label.setFixedSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE)
        thumb_label.setAlignment(Qt.AlignCenter)
        thumb_label.setStyleSheet("background-color: #f3dee5; border-radius: 3px;")
        if not thumbnail.isNull():
            thumb_label.setPixmap(
                thumbnail.scaled(
                    THUMBNAIL_SIZE, THUMBNAIL_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        name_label = QLabel(display_name)
        name_label.setStyleSheet("font-weight: bold;")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet("color: #888; font-size: 11px;")
        text_layout.addWidget(name_label)
        text_layout.addWidget(subtitle_label)

        delete_btn = QToolButton()
        delete_btn.setText("\u2715")
        delete_btn.setToolTip("移除该图片")
        delete_btn.setFixedSize(24, 24)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setStyleSheet(
            "QToolButton { color: #d16969; border: none; font-weight: bold; }"
            "QToolButton:hover { color: #ff5555; }"
        )
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(self._item_id))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.addWidget(thumb_label)
        layout.addLayout(text_layout, 1)
        layout.addWidget(delete_btn)


class DropArea(QWidget):
    """Accepts PNG files via drag-and-drop, a file browser, or manual paths."""

    add_files_requested = Signal(list)
    remove_item_requested = Signal(str)
    selection_changed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SingleSelection)
        self.list_widget.setSpacing(2)
        self.list_widget.setStyleSheet(
            "QListWidget { background-color: #fdf3f6; border: 1px dashed #d88fa5; border-radius: 4px; }"
            "QListWidget::item:selected { background-color: #f4d9e2; }"
        )
        self.list_widget.currentItemChanged.connect(self._on_current_item_changed)

        self._placeholder = QLabel("将 PNG 图片拖拽到此处，或使用下方按钮添加")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setStyleSheet("color: #b98a97;")
        self._placeholder.setWordWrap(True)

        browse_btn = QPushButton("浏览文件…")
        browse_btn.clicked.connect(self._on_browse)

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("或输入图片文件路径，多个路径用分号分隔，回车添加")
        self.path_edit.returnPressed.connect(self._on_manual_add)

        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self._on_manual_add)

        manual_row = QHBoxLayout()
        manual_row.addWidget(self.path_edit, 1)
        manual_row.addWidget(add_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.list_widget, 1)
        layout.addWidget(self._placeholder)
        layout.addWidget(browse_btn)
        layout.addLayout(manual_row)

        self.list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._sync_placeholder()

    # -- public API ---------------------------------------------------
    def add_item(self, item_id: str, display_name: str, subtitle: str, thumbnail: QPixmap) -> None:
        row = _ImageRow(item_id, display_name, subtitle, thumbnail)
        row.delete_requested.connect(self.remove_item_requested)

        item = QListWidgetItem(self.list_widget)
        item.setData(_ITEM_ID_ROLE, item_id)
        item.setSizeHint(row.sizeHint())
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, row)
        if self.list_widget.currentItem() is None:
            self.list_widget.setCurrentItem(item)
        self._sync_placeholder()

    def remove_item(self, item_id: str) -> None:
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(_ITEM_ID_ROLE) == item_id:
                self.list_widget.takeItem(i)
                break
        self._sync_placeholder()

    def clear(self) -> None:
        self.list_widget.clear()
        self._sync_placeholder()

    def current_item_id(self) -> str | None:
        item = self.list_widget.currentItem()
        return item.data(_ITEM_ID_ROLE) if item else None

    # -- internals ------------------------------------------------------
    def _sync_placeholder(self) -> None:
        self._placeholder.setVisible(self.list_widget.count() == 0)

    def _on_current_item_changed(self, current: QListWidgetItem, _previous) -> None:
        self.selection_changed.emit(current.data(_ITEM_ID_ROLE) if current else None)

    def _on_browse(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择 PNG 图片", "", "PNG 图片 (*.png)"
        )
        if paths:
            self.add_files_requested.emit(paths)

    def _on_manual_add(self) -> None:
        text = self.path_edit.text().strip()
        if not text:
            return
        paths = [p.strip().strip('"') for p in text.split(";") if p.strip()]
        if paths:
            self.add_files_requested.emit(paths)
        self.path_edit.clear()

    # -- drag & drop ------------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        paths = [p for p in paths if p]
        if paths:
            self.add_files_requested.emit(paths)
            event.acceptProposedAction()
