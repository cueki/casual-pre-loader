from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QListWidget, QPushButton, QSplitter, QListWidgetItem)
from PyQt6.QtCore import Qt, pyqtSignal
from gui.mod_descriptor import AddonDescription


class AddonPanel(QWidget):
    addon_selection_changed = pyqtSignal()
    delete_button_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.addons_list = None
        self.addon_description = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # addons list
        addons_group = QGroupBox("Addons")
        addons_layout = QVBoxLayout()
        self.addons_list = QListWidget()
        self.addons_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.addons_list.itemSelectionChanged.connect(self.on_selection_changed)
        addons_layout.addWidget(self.addons_list)

        # delete button
        delete_button = QPushButton("Delete Selected Addons")
        delete_button.clicked.connect(self.delete_button_clicked)
        addons_layout.addWidget(delete_button)
        addons_group.setLayout(addons_layout)
        splitter.addWidget(addons_group)

        # description
        description_group = QGroupBox("Details")
        description_layout = QVBoxLayout()
        self.addon_description = AddonDescription()
        description_layout.addWidget(self.addon_description)
        description_group.setLayout(description_layout)
        splitter.addWidget(description_group)

        # set initial split sizes
        splitter.setSizes([400, 300])

        layout.addWidget(splitter)

    def add_group_header(self, title):
        header = QListWidgetItem(f"──── {title} ────")
        header.setFlags(Qt.ItemFlag.NoItemFlags)
        header.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.addons_list.addItem(header)
        return header

    def add_addon_item(self, name, data=None):
        item = QListWidgetItem(name)
        if data:
            item.setData(Qt.ItemDataRole.UserRole, data)
        self.addons_list.addItem(item)
        return item

    def get_selected_items(self):
        return self.addons_list.selectedItems()

    def update_description(self, name, info):
        self.addon_description.update_content(name, info)

    def clear_description(self):
        self.addon_description.clear()

    def select_items_by_name(self, names):
        self.addons_list.blockSignals(True)
        self.addons_list.clearSelection()

        for i in range(self.addons_list.count()):
            item = self.addons_list.item(i)
            if item and item.flags() & Qt.ItemFlag.ItemIsSelectable:
                if item.text() in names:
                    item.setSelected(True)

        self.addons_list.blockSignals(False)
        self.on_selection_changed()

    def on_selection_changed(self):
        self.addon_selection_changed.emit()