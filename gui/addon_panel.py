from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QListWidget, QPushButton, QHBoxLayout, QMenu, QStyle)
from PyQt6.QtCore import Qt, pyqtSignal
from gui.mod_descriptor import AddonDescription
from gui.load_order_panel import LoadOrderPanel


class AddonPanel(QWidget):
    addon_selection_changed = pyqtSignal()
    addon_checkbox_changed = pyqtSignal()
    load_order_changed = pyqtSignal()
    delete_button_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.restore_button = None
        self.install_button = None
        self.addons_list = None
        self.load_order_panel = None
        self.addon_description = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # horizontal layout for the three panels
        panels_layout = QHBoxLayout()

        # left: addons list
        addons_group = QGroupBox("Available Addons")
        addons_layout = QVBoxLayout()
        self.addons_list = QListWidget()
        self.addons_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.addons_list.itemClicked.connect(self.on_selection_changed)
        self.addons_list.itemChanged.connect(self.on_checkbox_changed)
        self.addons_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.addons_list.customContextMenuRequested.connect(self.show_context_menu)

        # make unchecked checkboxes more visible
        self.addons_list.setStyleSheet("""
            QListWidget::indicator:unchecked {
                background: #555;
            }
        """)

        addons_layout.addWidget(self.addons_list)
        addons_group.setLayout(addons_layout)
        panels_layout.addWidget(addons_group)

        # middle: description
        description_group = QGroupBox("Details")
        description_layout = QVBoxLayout()
        self.addon_description = AddonDescription()
        description_layout.addWidget(self.addon_description)
        description_group.setLayout(description_layout)
        panels_layout.addWidget(description_group)

        # right: load order panel
        self.load_order_panel = LoadOrderPanel()
        self.load_order_panel.load_order_changed.connect(self.on_load_order_changed)
        panels_layout.addWidget(self.load_order_panel)

        layout.addLayout(panels_layout)

        # install/uninstall buttons at the bottom
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 8, 0, 0)

        button_layout.addStretch()

        self.install_button = QPushButton("Install")
        self.install_button.setFixedWidth(100)
        self.install_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        button_layout.addWidget(self.install_button)

        self.restore_button = QPushButton("Uninstall")
        self.restore_button.setFixedWidth(100)
        self.restore_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        button_layout.addWidget(self.restore_button)

        layout.addWidget(button_container)

    def on_selection_changed(self):
        self.addon_selection_changed.emit()

    def on_checkbox_changed(self):
        self.update_load_order_list()
        self.addon_checkbox_changed.emit()

    def on_load_order_changed(self):
        self.load_order_changed.emit()

    def update_load_order_list(self):
        # sync checked addons to load order list
        # get currently checked items (preserve their original names)
        checked_items = []
        for i in range(self.addons_list.count()):
            item = self.addons_list.item(i)
            if item and item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                if item.checkState() == Qt.CheckState.Checked:
                    # get original name without [#N] suffix
                    original_name = item.data(Qt.ItemDataRole.UserRole) or item.text().split(' [#')[0]
                    checked_items.append(original_name)

        # delegate to load order panel
        self.load_order_panel.sync_from_checked_addons(checked_items)

    def get_checked_items(self):
        checked_items = []
        for i in range(self.addons_list.count()):
            item = self.addons_list.item(i)
            if item and item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                if item.checkState() == Qt.CheckState.Checked:
                    checked_items.append(item)
        return checked_items

    def get_load_order(self):
        # delegate to load order panel
        return self.load_order_panel.get_load_order()

    def show_context_menu(self, position):
        item = self.addons_list.itemAt(position)
        if item and item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
            menu = QMenu(self)
            delete_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon)
            delete_action = QAction(delete_icon, "Delete", self)
            delete_action.triggered.connect(lambda: self.delete_button_clicked.emit())
            menu.addAction(delete_action)
            menu.exec(self.addons_list.mapToGlobal(position))
