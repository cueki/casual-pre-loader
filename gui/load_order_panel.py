import logging
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.services.conflicts import detect_addon_overwrites
from gui.theme import BUTTON_STYLE_ALT, FONT_SIZE_NORMAL, FRAME_STYLE, SECTION_LABEL_STYLE, WARNING

log = logging.getLogger()


class LoadOrderPanel(QWidget):
    load_order_changed = pyqtSignal()
    unadd_requested = pyqtSignal(str)
    deselect_all_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.load_order_list = None
        self.conflict_label = None
        self.deselect_all_btn = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        load_order_frame = QFrame()
        load_order_frame.setStyleSheet(FRAME_STYLE)
        load_order_layout = QVBoxLayout(load_order_frame)

        header_row = QHBoxLayout()
        load_order_lbl = QLabel("Load Order (Drag to Reorder)")
        load_order_lbl.setStyleSheet(SECTION_LABEL_STYLE)
        header_row.addWidget(load_order_lbl)
        header_row.addStretch()

        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.setStyleSheet(BUTTON_STYLE_ALT)
        self.deselect_all_btn.clicked.connect(self.deselect_all_requested)
        header_row.addWidget(self.deselect_all_btn)

        load_order_layout.addLayout(header_row)

        self.load_order_list = QListWidget()
        self.load_order_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.load_order_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.load_order_list.model().rowsMoved.connect(self.on_load_order_changed)
        self.load_order_list.itemClicked.connect(lambda: self.load_order_list.clearSelection())
        self.load_order_list.itemDoubleClicked.connect(self.on_item_double_clicked)

        load_order_layout.addWidget(self.load_order_list)

        self.conflict_label = QLabel("Conflicts detected, hover over ⚠ for details")
        self.conflict_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.conflict_label.setStyleSheet(f"color: {WARNING}; font-size: {FONT_SIZE_NORMAL}; padding: 8px;")
        self.conflict_label.hide()
        load_order_layout.addWidget(self.conflict_label)

        layout.addWidget(load_order_frame)

    def on_load_order_changed(self):
        self.load_order_changed.emit()

    def on_item_double_clicked(self, item):
        # double-click removes the mod from the load order by unchecking its addon
        text = item.text()
        clean_name = text.split('] ', 1)[-1].replace(' ⚠', '').strip()
        self.unadd_requested.emit(clean_name)

    def get_load_order(self):
        load_order = []
        for i in range(self.load_order_list.count()):
            text = self.load_order_list.item(i).text()
            # strip [#N] prefix and ⚠ suffix if present
            clean_name = text.split('] ', 1)[-1].replace(' ⚠', '').strip()
            load_order.append(clean_name)
        # reverse the order so that top item is installed last and wins conflicts
        return list(reversed(load_order))

    def update_display(self, addon_contents, addon_name_mapping=None):
        # add numbering and conflict detection to load order list
        try:
            self.load_order_list.blockSignals(True)
            load_order_items = []

            # collect all items
            for i in range(self.load_order_list.count()):
                item = self.load_order_list.item(i)
                load_order_items.append(item.text().split('] ', 1)[-1].replace(' ⚠', '').strip())

            # rebuild with numbering and conflicts
            self.load_order_list.clear()
            total_items = len(load_order_items)

            # detect all conflicts at once using the conflicts service
            all_overwrites = detect_addon_overwrites(
                load_order_items,
                addon_contents if addon_contents else {},
                addon_name_mapping
            )

            has_conflicts = False
            for pos, addon_name in enumerate(load_order_items):
                priority_number = total_items - pos
                display_text = f"[#{priority_number}] {addon_name}"

                # check if this addon has conflicts
                if addon_name in all_overwrites:
                    overwrites = all_overwrites[addon_name]
                    display_text += " ⚠"
                    has_conflicts = True
                    tooltip = "Will overwrite:\n"
                    for overwrite_addon, overwrite_files in overwrites.items():
                        tooltip += f"• {overwrite_addon}: "
                        if overwrite_files:
                            tooltip += f"{len(overwrite_files)} files including {overwrite_files[0]}\n"
                        else:
                            tooltip += "Unknown files\n"

                    item = QListWidgetItem(display_text)
                    item.setToolTip(tooltip)
                    item.setForeground(QColor(WARNING))
                    self.load_order_list.addItem(item)
                else:
                    self.load_order_list.addItem(display_text)

            # show/hide conflict warning
            self.conflict_label.setVisible(has_conflicts)

            self.load_order_list.blockSignals(False)

        except Exception:
            log.exception("Error in update_display")

    def sync_from_checked_addons(self, checked_addon_names):
        # update load order list from checked addons
        self.load_order_list.blockSignals(True)

        # get current load order
        existing_order = []
        for i in range(self.load_order_list.count()):
            text = self.load_order_list.item(i).text()
            clean_name = text.split('] ', 1)[-1].replace(' ⚠', '').strip()
            existing_order.append(clean_name)

        # add new items at top, then keep existing order
        new_order = []
        for name in checked_addon_names:
            if name not in existing_order:
                new_order.append(name)

        # then add existing items that are still checked
        for name in existing_order:
            if name in checked_addon_names:
                new_order.append(name)

        # update the list
        self.load_order_list.clear()
        for name in new_order:
            self.load_order_list.addItem(name)

        self.load_order_list.blockSignals(False)

    def clear(self):
        self.load_order_list.clear()
        self.conflict_label.hide()

    def restore_order(self, addon_names):
        # restore load order from saved list
        self.load_order_list.blockSignals(True)
        self.load_order_list.clear()
        for name in reversed(addon_names):
            self.load_order_list.addItem(name)
        self.load_order_list.blockSignals(False)
