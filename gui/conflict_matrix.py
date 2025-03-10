import json
import webbrowser
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTableWidget, QHeaderView, QCheckBox, QHBoxLayout, QWidget, QPushButton
from gui.settings_manager import SettingsManager


def load_mod_urls():
    # load saved URLs from a file
    urls_file = Path("mod_urls.json")
    if urls_file.exists():
        try:
            with open(urls_file, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading mod URLs: {e}")
    return {}


class ConflictMatrix(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("QTableWidget { border: 1px solid #ccc; }")
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.settings_manager = SettingsManager()
        self.mod_urls = {}
        self.verticalHeader().sectionClicked.connect(self.on_mod_name_clicked)

    def on_mod_name_clicked(self, index):
        mod_name = self.verticalHeaderItem(index).text()
        if mod_name in self.mod_urls and self.mod_urls[mod_name]:
            self.open_mod_url(mod_name)

    def open_mod_url(self, mod_name):
        # open the URL for the mod in the default web browser
        if mod_name in self.mod_urls and self.mod_urls[mod_name]:
            try:
                webbrowser.open(self.mod_urls[mod_name])
            except Exception as e:
                print(f"Error opening URL for {mod_name}: {e}")

    def load_selections(self):
        if self.settings_manager:
            return self.settings_manager.get_matrix_selections()
        return {}

    def save_selections(self):
        if not self.settings_manager:
            return

        selections = {}
        for col in range(1, self.columnCount()):
            particle_file = self.horizontalHeaderItem(col).text()
            for row in range(self.rowCount()):
                cell_widget = self.cellWidget(row, col)
                if cell_widget:
                    checkbox = cell_widget.layout().itemAt(0).widget()
                    if checkbox and checkbox.isChecked():
                        mod_name = self.verticalHeaderItem(row).text()
                        selections[particle_file] = mod_name

        self.settings_manager.set_matrix_selections(selections)

    def update_matrix(self, mods, pcf_files):
        # load mod URLs
        self.mod_urls = load_mod_urls()

        # add one extra column for the Select All button
        self.setColumnCount(len(pcf_files) + 1)
        self.setRowCount(len(mods))

        # headers
        headers = ["Select All"] + pcf_files
        self.setHorizontalHeaderLabels(headers)
        self.setVerticalHeaderLabels(mods)

        # make vertical header interactive
        self.verticalHeader().setStyleSheet("""
            QHeaderView::section { 
                background-color: lightgray; 
                border-style: outset; 
                border-width: 2px; 
                border-color: gray;
                color: black;
            }
            QHeaderView::section:hover { 
                color: blue; 
                text-decoration: underline;
                background-color: #e0e0e0;
            }
        """)

        saved_checkboxes = []

        for row, mod in enumerate(mods):
            # Select All button
            select_all_widget = QWidget()
            select_all_layout = QHBoxLayout(select_all_widget)
            select_all_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            select_all_layout.setContentsMargins(0, 0, 0, 0)

            select_all_button = QPushButton("Select All")
            select_all_button.setFixedWidth(70)
            select_all_layout.addWidget(select_all_button)
            self.setCellWidget(row, 0, select_all_widget)

            # checkboxes for each particle file
            for col, pcf_file in enumerate(pcf_files):
                cell_widget = QWidget()
                layout = QHBoxLayout(cell_widget)
                layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.setContentsMargins(0, 0, 0, 0)

                checkbox = self.create_checkbox(row, col + 1)

                # store saved selections
                saved_selections = self.load_selections()
                if pcf_file in saved_selections and saved_selections[pcf_file] == mod:
                    saved_checkboxes.append((checkbox, row, col + 1))

                layout.addWidget(checkbox)
                self.setCellWidget(row, col + 1, cell_widget)

            # connect Select All button
            select_all_button.clicked.connect(lambda checked, r=row: self.select_all_row(r))

        # apply saved selections after all cells are created and event handlers are connected
        for checkbox, row, col in saved_checkboxes:
            self.uncheck_column_except(col, row)
            checkbox.setChecked(True)

    def select_all_row(self, row):
        any_checked = False
        for col in range(1, self.columnCount()):
            cell_widget = self.cellWidget(row, col)
            if cell_widget:
                checkbox = cell_widget.layout().itemAt(0).widget()
                if checkbox and checkbox.isChecked():
                    any_checked = True
                    break

        for col in range(1, self.columnCount()):
            cell_widget = self.cellWidget(row, col)
            if cell_widget:
                checkbox = cell_widget.layout().itemAt(0).widget()
                if checkbox:
                    if not any_checked and checkbox.isEnabled():
                        # only check if no others in this column are checked
                        self.uncheck_column_except(col, row)
                        checkbox.setChecked(True)
                    else:
                        checkbox.setChecked(False)

        self.save_selections()

    def deselect_all(self):
        for row in range(self.rowCount()):
            for col in range(1, self.columnCount()):  # skip the "Select All" column
                cell_widget = self.cellWidget(row, col)
                if cell_widget:
                    checkbox = cell_widget.layout().itemAt(0).widget()
                    if checkbox and checkbox.isChecked():
                        checkbox.setChecked(False)
        self.save_selections()

    def uncheck_column_except(self, col, target_row):
        for row in range(self.rowCount()):
            if row != target_row:
                cell_widget = self.cellWidget(row, col)
                if cell_widget:
                    checkbox = cell_widget.layout().itemAt(0).widget()
                    if checkbox and checkbox.isChecked():
                        checkbox.setChecked(False)
        self.save_selections()

    def create_checkbox(self, row, col):
        checkbox = QCheckBox()

        def on_state_changed(state):
            if state == Qt.CheckState.Checked.value:
                # uncheck all other boxes in this column
                for other_row in range(self.rowCount()):
                    if other_row != row:
                        other_cell = self.cellWidget(other_row, col)
                        if other_cell:
                            other_checkbox = other_cell.layout().itemAt(0).widget()
                            if other_checkbox and other_checkbox.isEnabled():
                                other_checkbox.setChecked(False)
            self.save_selections()

        checkbox.stateChanged.connect(on_state_changed)
        return checkbox

    def get_selected_particles(self):
        selections = {}
        for col in range(1, self.columnCount()):
            particle_file = self.horizontalHeaderItem(col).text()
            for row in range(self.rowCount()):
                cell_widget = self.cellWidget(row, col)
                if cell_widget:
                    checkbox = cell_widget.layout().itemAt(0).widget()
                    if checkbox and checkbox.isChecked():
                        mod_name = self.verticalHeaderItem(row).text()
                        selections[particle_file] = mod_name
                        break
        return selections