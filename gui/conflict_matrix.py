import json
import logging
import webbrowser

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QWidget,
)

from core.constants import PARTICLE_GROUP_MAPPING
from core.folder_setup import folder_setup

log = logging.getLogger()


def load_mod_urls():
    # load saved URLs from a file
    urls_file = folder_setup.data_dir / 'mod_urls.json'
    if urls_file.exists():
        try:
            with open(urls_file, "r") as f:
                return json.load(f)
        except Exception:
            log.exception("Error loading mod URLs")
    return {}


class ConflictMatrix(QTableWidget):
    def __init__(self, settings_manager=None):
        super().__init__()
        self.setStyleSheet("QTableWidget { border: 1px solid #ccc; }")
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.settings_manager = settings_manager
        self.mod_urls = {}
        self.simple_mode = False  # track whether we're in simple or advanced mode
        self.mod_particles_cache = {}  # cache mod particle data
        self.all_particles_cache = []  # cache all particle files
        self.verticalHeader().sectionClicked.connect(self.on_mod_name_clicked)

        # smooth scrolling
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        h_scrollbar = self.horizontalScrollBar()
        new_pixel_step = 7
        h_scrollbar.setSingleStep(new_pixel_step)

    def on_mod_name_clicked(self, index):
        mod_name = self.verticalHeaderItem(index).text()
        if mod_name in self.mod_urls and self.mod_urls[mod_name]:
            self.open_mod_url(mod_name)

    def open_mod_url(self, mod_name):
        # open the URL for the mod in the default web browser
        if mod_name in self.mod_urls and self.mod_urls[mod_name]:
            try:
                webbrowser.open(self.mod_urls[mod_name])
            except Exception:
                log.exception(f"Error opening URL for {mod_name}")

    def load_selections(self):
        if self.settings_manager:
            if self.simple_mode:
                return self.settings_manager.get_matrix_selections_simple()
            else:
                return self.settings_manager.get_matrix_selections()
        return {}

    def _get_current_selections_dict(self):
        selections = {}
        # skip the "Select All" button column
        for col in range(1, self.columnCount()):
            header_item = self.horizontalHeaderItem(col)
            if not header_item:
                log.warning(f"Missing header item for column {col}")
                continue
            column_name = header_item.text().strip()

            for row in range(self.rowCount()):
                cell_widget = self.cellWidget(row, col)
                if cell_widget:
                    layout = cell_widget.layout()
                    if layout and layout.count() > 0:
                        widget_item = layout.itemAt(0)
                        if widget_item:
                            checkbox = widget_item.widget()
                            if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                                v_header_item = self.verticalHeaderItem(row)
                                if not v_header_item:
                                    log.warning(f"Missing vertical header item for row {row}")
                                    continue
                                mod_name = v_header_item.text()

                                # if in simple mode, expand group to individual particles
                                if self.simple_mode and column_name in PARTICLE_GROUP_MAPPING:
                                    for particle_file in PARTICLE_GROUP_MAPPING[column_name]:
                                        if particle_file.replace('.pcf', '') in self.mod_particles_cache.get(mod_name, []):
                                            selections[particle_file.replace('.pcf', '')] = mod_name
                                else:
                                    selections[column_name] = mod_name
                                break

        return selections

    def save_selections(self):
        if not self.settings_manager:
            return

        selections = self._get_current_selections_dict()
        if self.simple_mode:
            self.settings_manager.set_matrix_selections_simple(selections)
        else:
            self.settings_manager.set_matrix_selections(selections)

    def get_selected_particles(self):
        selections = self._get_current_selections_dict()
        return selections

    def set_simple_mode(self, enabled):
        self.simple_mode = enabled
        # rebuild matrix with cached data
        if self.mod_particles_cache:
            mods = list(self.mod_particles_cache.keys())
            if self.simple_mode:
                self.update_matrix_simple(mods)
            else:
                self.update_matrix_advanced(mods, self.all_particles_cache)

    def update_matrix(self, mods, pcf_files):
        # cache the data
        self.all_particles_cache = pcf_files

        # build mod_particles_cache (which particles each mod has)
        from gui.drag_and_drop import get_mod_particle_files
        mod_particles, _ = get_mod_particle_files()
        self.mod_particles_cache = mod_particles

        if self.simple_mode:
            self.update_matrix_simple(mods)
        else:
            self.update_matrix_advanced(mods, pcf_files)

    def update_matrix_simple(self, mods):
        # load mod URLs
        self.mod_urls = load_mod_urls()
        self.clearContents()

        # use group names as columns
        groups = list(PARTICLE_GROUP_MAPPING.keys())

        # add one extra column for the Select All button
        self.setColumnCount(len(groups) + 1)
        self.setRowCount(len(mods))

        # headers with padding
        headers = ["Select All"] + [f" {group} " for group in groups]
        self.setHorizontalHeaderLabels(headers)
        self.setVerticalHeaderLabels(mods)

        self._setup_matrix_cells(mods, groups)

    def update_matrix_advanced(self, mods, pcf_files):
        # load mod URLs
        self.mod_urls = load_mod_urls()
        self.clearContents()

        # add one extra column for the Select All button
        self.setColumnCount(len(pcf_files) + 1)
        self.setRowCount(len(mods))

        # headers (no padding in advanced mode to save space)
        headers = ["Select All"] + pcf_files
        self.setHorizontalHeaderLabels(headers)
        self.setVerticalHeaderLabels(mods)

        self._setup_matrix_cells(mods, pcf_files)

    def _setup_matrix_cells(self, mods, columns):
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

        saved_checkboxes_to_check = []
        saved_selections = self.load_selections()

        for row, mod in enumerate(mods):
            select_all_widget = QWidget()
            select_all_layout = QHBoxLayout(select_all_widget)
            select_all_layout.setContentsMargins(0, 0, 0, 0)

            select_all_button = QPushButton("Select All (0/0)")
            select_all_button.setFixedWidth(102)
            select_all_button.clicked.connect(lambda checked=False, r=row: self.select_all_row(r))
            select_all_layout.addWidget(select_all_button)
            self.setCellWidget(row, 0, select_all_widget)

            # get the particles this mod has
            mod_particles_set = set(self.mod_particles_cache.get(mod, []))

            for col_idx, column_name in enumerate(columns):
                col = col_idx + 1  # actual table column index (col 0 is Select All)
                cell_widget = QWidget()
                layout = QHBoxLayout(cell_widget)
                layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.setContentsMargins(0, 0, 0, 0)

                checkbox = self.create_checkbox(row, col)

                # determine if checkbox should be enabled/checked based on whether mod has this particle/group
                if self.simple_mode and column_name in PARTICLE_GROUP_MAPPING:
                    group_particles = PARTICLE_GROUP_MAPPING[column_name]
                    should_enable = any(
                        p.replace('.pcf', '') in mod_particles_set
                        for p in group_particles
                    )
                    should_check = should_enable and any(
                        saved_selections.get(p.replace('.pcf', '')) == mod
                        for p in group_particles
                    )
                else:
                    should_enable = column_name in mod_particles_set
                    should_check = should_enable and column_name in saved_selections and saved_selections[column_name] == mod

                checkbox.setEnabled(should_enable)

                if should_check:
                    saved_checkboxes_to_check.append(checkbox)

                layout.addWidget(checkbox)
                self.setCellWidget(row, col, cell_widget)

        # apply saved selections *after* all cells and widgets are created and signals are connected
        for checkbox in saved_checkboxes_to_check:
            checkbox.blockSignals(True)
            checkbox.setChecked(True)
            checkbox.blockSignals(False)

        # this is very retarded
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self.update_select_all_buttons)

    def select_all_row(self, row):
        any_checked = False
        enabled_checkboxes_in_row = []

        # first pass: check if any enabled checkbox in the row is already checked
        for col in range(1, self.columnCount()):
            cell_widget = self.cellWidget(row, col)
            if cell_widget:
                checkbox = cell_widget.layout().itemAt(0).widget()
                if checkbox and checkbox.isEnabled():
                    enabled_checkboxes_in_row.append((checkbox, col))
                    if checkbox.isChecked():
                        any_checked = True

        # second pass: check or uncheck based on 'any_checked'
        should_check = not any_checked

        something_changed = False
        for checkbox, col in enabled_checkboxes_in_row:
            current_state = checkbox.isChecked()
            target_state = should_check

            if current_state != target_state:
                if target_state: # we want to check this box
                    self.uncheck_column_except(col, row)

                checkbox.blockSignals(True)
                checkbox.setChecked(target_state)
                checkbox.blockSignals(False)
                something_changed = True


        # save and update UI once after all changes for the row are done
        if something_changed:
            self.save_selections()
            self.update_select_all_buttons()

    def deselect_all(self):
        something_changed = False
        for row in range(self.rowCount()):
            for col in range(1, self.columnCount()):  # skip the "Select All" column
                cell_widget = self.cellWidget(row, col)
                if cell_widget:
                    checkbox = cell_widget.layout().itemAt(0).widget()
                    if checkbox and checkbox.isChecked():
                        checkbox.blockSignals(True)
                        checkbox.setChecked(False)
                        checkbox.blockSignals(False)
                        something_changed = True

        if something_changed:
            self.save_selections()
            self.update_select_all_buttons()

    def update_select_all_buttons(self):
        for row in range(self.rowCount()):
            enabled_count = 0
            selected_count = 0

            for col in range(1, self.columnCount()):
                cell_widget = self.cellWidget(row, col)
                if cell_widget:
                    layout = cell_widget.layout()
                    if layout and layout.count() > 0:
                        checkbox = layout.itemAt(0).widget()
                        if isinstance(checkbox, QCheckBox):
                            if checkbox.isEnabled():
                                enabled_count += 1
                                if checkbox.isChecked():
                                    selected_count += 1

            select_all_widget = self.cellWidget(row, 0)
            if select_all_widget:
                button_layout = select_all_widget.layout()
                if button_layout and button_layout.count() > 0:
                     select_all_button = button_layout.itemAt(0).widget()
                     if isinstance(select_all_button, QPushButton):
                        select_all_button.setText(f"Select All ({selected_count}/{enabled_count})")

        # force the resize to make sure buttons don't eat each other
        self.resizeColumnToContents(0)
        for row in range(self.rowCount()):
            self.resizeRowToContents(row)

    def uncheck_column_except(self, col, target_row):
        for row in range(self.rowCount()):
            if row != target_row:
                cell_widget = self.cellWidget(row, col)
                if cell_widget:
                    layout = cell_widget.layout()
                    if layout and layout.count() > 0:
                         checkbox = layout.itemAt(0).widget()
                         if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                            checkbox.blockSignals(True)
                            checkbox.setChecked(False)
                            checkbox.blockSignals(False)

    def create_checkbox(self, row, col):
        checkbox = QCheckBox()
        # connect stateChanged to the handler method, passing row and col
        checkbox.stateChanged.connect(
            lambda state, r=row, c=col: self.on_checkbox_state_changed(state, r, c)
        )
        return checkbox

    def on_checkbox_state_changed(self, state, row, col):
        # retrieve the actual checkbox widget that emitted the signal
        checkbox = self.sender()
        if not isinstance(checkbox, QCheckBox):
            return # should not happen

        if state == Qt.CheckState.Checked.value:
            self.uncheck_column_except(col, row)

        self.save_selections()
        self.update_select_all_buttons()
