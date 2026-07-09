import logging
import webbrowser

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from core.constants import PARTICLE_GROUP_MAPPING
from core.services.particles import (
    calculate_particle_availability,
    expand_group_selections,
)
from core.util.data import mod_urls
from gui.theme import BG_DEFAULT, BUTTON_STYLE_ALT, CODE_BG, FONT_SIZE_NORMAL

log = logging.getLogger()


class ConflictMatrix(QTableWidget):
    def __init__(self, settings=None):
        super().__init__()
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.settings = settings
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
        mod_name = self.verticalHeaderItem(index).text().split(" (")[0]
        self.open_mod_url(mod_name)

    def open_mod_url(self, mod_name):
        # open the URL for the mod in the default web browser
        if mod_name in mod_urls and mod_urls[mod_name]:
            try:
                webbrowser.open(mod_urls[mod_name])
            except Exception:
                log.exception(f"Error opening URL for {mod_name}")

    def load_selections(self):
        if self.settings:
            if self.simple_mode:
                return self.settings.matrix_selections_simple
            else:
                return self.settings.matrix_selections
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
                                mod_name = v_header_item.text().split(" (")[0]
                                selections[column_name] = mod_name
                                break

        # expand group selections to individual particles if in simple mode
        selections = expand_group_selections(
            selections, self.mod_particles_cache, self.simple_mode
        )

        return selections

    def save_selections(self):
        if not self.settings:
            return

        selections = self._get_current_selections_dict()
        if self.simple_mode:
            self.settings.matrix_selections_simple = selections
        else:
            self.settings.matrix_selections = selections

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
        from core.util.pcf_path_walk import get_mod_particles
        mod_particles, _ = get_mod_particles()
        self.mod_particles_cache = mod_particles

        if self.simple_mode:
            self.update_matrix_simple(mods)
        else:
            self.update_matrix_advanced(mods, pcf_files)

    def update_matrix_simple(self, mods):
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
        saved_checkboxes_to_check = []
        saved_selections = self.load_selections()

        # first pass: create Select All buttons and set up alternating column colors
        for row, mod in enumerate(mods):
            select_all_button = QPushButton("Select All")
            select_all_button.setStyleSheet(BUTTON_STYLE_ALT + f"QPushButton {{ padding: 4px 8px; font-size: {FONT_SIZE_NORMAL}; }}")
            select_all_button.clicked.connect(lambda checked=False, r=row: self.select_all_row(r))
            self.setCellWidget(row, 0, select_all_button)

        # set up alternating column colors for all cells
        for col in range(self.columnCount()):
            bg_color = CODE_BG if col % 2 == 0 else BG_DEFAULT

            header_item = self.horizontalHeaderItem(col)
            if header_item:
                header_item.setBackground(QColor(bg_color))

            for row in range(self.rowCount()):
                item = QTableWidgetItem()
                item.setBackground(QColor(bg_color))
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.setItem(row, col, item)

        # second pass: add checkboxes only where the mod has that particle/group
        for row, mod in enumerate(mods):
            mod_particles_set = set(self.mod_particles_cache.get(mod, []))

            for col_idx, column_name in enumerate(columns):
                col = col_idx + 1  # actual table column index (col 0 is Select All)

                # determine if checkbox should exist based on whether mod has this particle/group
                should_enable, should_check = calculate_particle_availability(
                    mod, column_name, self.simple_mode, mod_particles_set, saved_selections
                )

                # only add checkbox if this mod has the particle/group
                if not should_enable:
                    continue

                bg_color = CODE_BG if col % 2 == 0 else BG_DEFAULT

                cell_widget = QWidget()
                cell_widget.setStyleSheet(f"background: {bg_color};")
                layout = QHBoxLayout(cell_widget)
                layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.setContentsMargins(0, 0, 0, 0)

                checkbox = self.create_checkbox(row, col)

                if should_check:
                    saved_checkboxes_to_check.append(checkbox)

                layout.addWidget(checkbox)
                self.setCellWidget(row, col, cell_widget)

        # apply saved selections *after* all cells and widgets are created and signals are connected
        for checkbox in saved_checkboxes_to_check:
            checkbox.blockSignals(True)
            checkbox.setChecked(True)
            checkbox.blockSignals(False)

        # defer resize to ensure proper layout
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
        # force the resize to make sure buttons don't eat each other
        self.resizeColumnToContents(0)
        for row in range(self.rowCount()):
            self.resizeRowToContents(row)
        self._update_row_counts()

    def _update_row_counts(self):
        for row in range(self.rowCount()):
            v_header = self.verticalHeaderItem(row)
            if not v_header:
                continue

            # strip any existing count suffix to get the base mod name
            base_name = v_header.text().split(" (")[0]

            total = 0
            checked = 0
            for col in range(1, self.columnCount()):
                cell_widget = self.cellWidget(row, col)
                if cell_widget:
                    layout = cell_widget.layout()
                    if layout and layout.count() > 0:
                        checkbox = layout.itemAt(0).widget()
                        if isinstance(checkbox, QCheckBox):
                            total += 1
                            if checkbox.isChecked():
                                checked += 1

            if total > 0:
                v_header.setText(f"{base_name} ({checked}/{total})")
            else:
                v_header.setText(base_name)

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
