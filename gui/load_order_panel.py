import logging
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

log = logging.getLogger()


class LoadOrderPanel(QWidget):
    load_order_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.load_order_list = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        load_order_group = QGroupBox("Load Order (Drag to Modify)")
        load_order_layout = QVBoxLayout()

        self.load_order_list = QListWidget()
        self.load_order_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.load_order_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.load_order_list.model().rowsMoved.connect(self.on_load_order_changed)

        # hide selection highlight completely
        self.load_order_list.setStyleSheet("""
            QListWidget::item:selected {
                background: transparent;
            }
        """)

        load_order_layout.addWidget(self.load_order_list)
        load_order_group.setLayout(load_order_layout)

        layout.addWidget(load_order_group)

    def on_load_order_changed(self):
        self.load_order_changed.emit()

    def get_load_order(self):
        load_order = []
        for i in range(self.load_order_list.count()):
            text = self.load_order_list.item(i).text()
            # strip [#N] prefix and ⚠️suffix if present
            clean_name = text.split('] ', 1)[-1].replace(' ⚠️', '')
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
                load_order_items.append(item.text().split(' [#')[0].split('] ', 1)[-1].replace(' ⚠️', ''))

            # rebuild with numbering and conflicts
            self.load_order_list.clear()
            total_items = len(load_order_items)
            for pos, addon_name in enumerate(load_order_items):
                priority_number = total_items - pos
                display_text = f"[#{priority_number}] {addon_name}"

                # resolve display name to folder name for conflict detection
                folder_name = addon_name
                if addon_name_mapping and addon_name in addon_name_mapping:
                    folder_name = addon_name_mapping[addon_name].get('file_path', addon_name)

                # check for conflicts
                if addon_contents and folder_name in addon_contents:
                    overwrites = {}
                    addon_files = set(addon_contents[folder_name])

                    # check against lower priority addons
                    for other_pos, other_name in enumerate(load_order_items):
                        if other_pos > pos:
                            other_folder_name = other_name
                            if addon_name_mapping and other_name in addon_name_mapping:
                                other_folder_name = addon_name_mapping[other_name].get('file_path', other_name)

                            if other_folder_name in addon_contents:
                                other_files = set(addon_contents[other_folder_name])
                                common_files = addon_files.intersection(other_files)
                                if common_files:
                                    overwrites[other_name] = list(common_files)

                    if overwrites:
                        display_text += " ⚠️"
                        tooltip = "Will overwrite:\n"
                        for overwrite_addon, overwrite_files in overwrites.items():
                            tooltip += f"• {overwrite_addon}: "
                            if overwrite_files:
                                tooltip += f"{len(overwrite_files)} files including {overwrite_files[0]}\n"
                            else:
                                tooltip += "Unknown files\n"

                        item = QListWidgetItem(display_text)
                        item.setToolTip(tooltip)
                        self.load_order_list.addItem(item)
                    else:
                        self.load_order_list.addItem(display_text)
                else:
                    self.load_order_list.addItem(display_text)

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
            clean_name = text.split('] ', 1)[-1].replace(' ⚠️', '')
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

    def restore_order(self, addon_names):
        # restore load order from saved list
        self.load_order_list.blockSignals(True)
        self.load_order_list.clear()
        for name in reversed(addon_names):
            self.load_order_list.addItem(name)
        self.load_order_list.blockSignals(False)
