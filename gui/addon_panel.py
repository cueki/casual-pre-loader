from PyQt6.QtCore import QEvent, Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMenu,
    QPushButton,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from gui.load_order_panel import LoadOrderPanel
from gui.addon_details import AddonDescription
from gui.theme import BUTTON_STYLE_ALT, FRAME_STYLE, SECTION_LABEL_STYLE


class AddonPanel(QWidget):
    addon_selection_changed = pyqtSignal()
    addon_checkbox_changed = pyqtSignal()
    load_order_changed = pyqtSignal()
    delete_button_clicked = pyqtSignal()
    open_folder_clicked = pyqtSignal()
    refresh_clicked = pyqtSignal()
    details_collapse_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.addons_list = None
        self.addon_search = None
        self.load_order_panel = None
        self.addon_description = None
        self.details_frame = None
        self.details_header = None
        self.details_collapsed = False
        self.details_has_content = False
        self.collapse_btn = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # two-column layout: left (stacked) and right (load order)
        columns = QHBoxLayout()
        columns.setContentsMargins(0, 0, 0, 0)

        # left column: Available Addons + Addon Details stacked
        left_column = QVBoxLayout()
        left_column.setContentsMargins(0, 0, 0, 0)

        # available Addons frame
        available_frame = QFrame()
        available_frame.setStyleSheet(FRAME_STYLE)
        available_layout = QVBoxLayout(available_frame)

        # header row with label and search bar
        header_row = QHBoxLayout()
        available_lbl = QLabel("Available Addons")
        available_lbl.setStyleSheet(SECTION_LABEL_STYLE)
        header_row.addWidget(available_lbl)
        header_row.addStretch()

        self.addon_search = QLineEdit()
        self.addon_search.setPlaceholderText("Search...")
        self.addon_search.setFixedWidth(150)
        self.addon_search.textChanged.connect(self._filter_addons)
        header_row.addWidget(self.addon_search)

        open_folder_btn = QPushButton("Open Folder")
        open_folder_btn.setStyleSheet(BUTTON_STYLE_ALT)
        open_folder_btn.clicked.connect(self.open_folder_clicked.emit)
        header_row.addWidget(open_folder_btn)

        refresh_btn = QToolButton()
        refresh_btn.setAutoRaise(True)
        refresh_btn.setToolTip("Refresh all addons")
        refresh_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        refresh_btn.clicked.connect(self.refresh_clicked.emit)
        header_row.addWidget(refresh_btn)

        available_layout.addLayout(header_row)

        self.addons_list = QListWidget()
        self.addons_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.addons_list.itemClicked.connect(self.on_selection_changed)
        self.addons_list.itemChanged.connect(self.on_checkbox_changed)
        self.addons_list.itemDoubleClicked.connect(self.on_double_click)
        self.addons_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.addons_list.customContextMenuRequested.connect(self.show_context_menu)

        # smooth scrolling
        self.addons_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        v_scrollbar = self.addons_list.verticalScrollBar()
        v_scrollbar.setSingleStep(7)

        available_layout.addWidget(self.addons_list)
        left_column.addWidget(available_frame, 2)

        # Addon Details frame
        self.details_frame = QFrame()
        self.details_frame.setStyleSheet(FRAME_STYLE)
        details_layout = QVBoxLayout(self.details_frame)

        # Header row with label and collapse button
        self.details_header = QWidget()
        self.details_header.installEventFilter(self)
        details_header_layout = QHBoxLayout(self.details_header)
        details_header_layout.setContentsMargins(0, 0, 0, 0)
        details_lbl = QLabel("Addon Details")
        details_lbl.setStyleSheet(SECTION_LABEL_STYLE)
        details_header_layout.addWidget(details_lbl)
        details_header_layout.addStretch()

        self.collapse_btn = QToolButton()
        self.collapse_btn.setAutoRaise(True)
        self.collapse_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMinButton))
        self.collapse_btn.clicked.connect(self.toggle_details_collapse)
        details_header_layout.addWidget(self.collapse_btn)
        details_layout.addWidget(self.details_header)

        self.addon_description = AddonDescription()
        self.addon_description.content_changed.connect(self.on_details_content_changed)
        details_layout.addWidget(self.addon_description, 1)
        left_column.addWidget(self.details_frame, 1)

        columns.addLayout(left_column, 2)

        # right column: Load Order
        self.load_order_panel = LoadOrderPanel()
        self.load_order_panel.load_order_changed.connect(self.on_load_order_changed)
        self.load_order_panel.unadd_requested.connect(self.on_unadd_requested)
        columns.addWidget(self.load_order_panel, 1)

        layout.addLayout(columns)

        # Set initial size for empty state
        self._update_details_frame_size()

    def on_selection_changed(self):
        self.addon_selection_changed.emit()

    def toggle_details_collapse(self):
        self.details_collapsed = not self.details_collapsed
        self.details_collapse_changed.emit(self.details_collapsed)
        self.addon_description.setVisible(not self.details_collapsed)
        if self.details_collapsed:
            self.collapse_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarNormalButton))
        else:
            self.collapse_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMinButton))
        self._update_details_frame_size()

    def on_details_content_changed(self, has_content: bool):
        self.details_has_content = has_content
        self._update_details_frame_size()

    def _update_details_frame_size(self):
        layout = self.details_frame.layout()
        margins = layout.contentsMargins()
        header_height = self.collapse_btn.sizeHint().height()

        if self.details_collapsed:
            # Collapsed: just header
            collapsed_height = margins.top() + header_height + margins.bottom()
            self.details_frame.setFixedHeight(collapsed_height)
        elif not self.details_has_content:
            # Empty state: header + small content area for placeholder text
            empty_height = margins.top() + header_height + layout.spacing() + 40 + margins.bottom()
            self.details_frame.setFixedHeight(empty_height)
        else:
            # Full content: allow expansion
            self.details_frame.setMaximumHeight(16777215)
            self.details_frame.setMinimumHeight(0)

    def on_double_click(self, item):
        if item and item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
            if item.checkState() == Qt.CheckState.Checked:
                item.setCheckState(Qt.CheckState.Unchecked)
            else:
                item.setCheckState(Qt.CheckState.Checked)

    def on_checkbox_changed(self):
        self.update_load_order_list()
        self.addon_checkbox_changed.emit()

    def on_load_order_changed(self):
        self.load_order_changed.emit()

    def on_unadd_requested(self, addon_name):
        # uncheck the addon matching this load order entry; itemChanged then resyncs the list
        for i in range(self.addons_list.count()):
            item = self.addons_list.item(i)
            if item and item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                original_name = item.data(Qt.ItemDataRole.UserRole) or item.text().split(' [#')[0]
                if original_name == addon_name:
                    item.setCheckState(Qt.CheckState.Unchecked)
                    break

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
            # retrigger selection if stale
            self.addons_list.setCurrentItem(item)
            self.addon_selection_changed.emit()

            menu = QMenu(self)

            edit_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
            edit_action = QAction(edit_icon, "Edit mod.json", self)
            edit_action.triggered.connect(self.addon_description.open_editor)
            menu.addAction(edit_action)

            export_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
            export_action = QAction(export_icon, "Export as VPK", self)
            export_action.triggered.connect(self.addon_description.export_addon)
            menu.addAction(export_action)

            menu.addSeparator()

            delete_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon)
            delete_action = QAction(delete_icon, "Delete", self)
            delete_action.triggered.connect(lambda: self.delete_button_clicked.emit())
            menu.addAction(delete_action)

            menu.exec(self.addons_list.mapToGlobal(position))

    def _filter_addons(self, text):
        for i in range(self.addons_list.count()):
            item = self.addons_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def eventFilter(self, obj, event):
        if obj == self.details_header and event.type() == QEvent.Type.MouseButtonDblClick:
            self.toggle_details_collapse()
            return True
        return super().eventFilter(obj, event)
