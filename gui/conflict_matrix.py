from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTableWidget, QHeaderView, QCheckBox, QHBoxLayout, QWidget, QPushButton


class ConflictMatrix(QTableWidget):
   def __init__(self):
      super().__init__()
      self.setStyleSheet("QTableWidget { border: 1px solid #ccc; }")
      self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
      self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
      self.setSelectionMode(QTableWidget.SelectionMode.NoSelection)

   def update_matrix(self, mods, pcf_files):
      # add one extra column for the Select All button
      self.setColumnCount(len(pcf_files) + 1)
      self.setRowCount(len(mods))

      # set headers
      headers = ["Select All"] + pcf_files
      self.setHorizontalHeaderLabels(headers)
      self.setVerticalHeaderLabels(mods)

      for row, mod in enumerate(mods):
         # add Select All button
         select_all_widget = QWidget()
         select_all_layout = QHBoxLayout(select_all_widget)
         select_all_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
         select_all_layout.setContentsMargins(0, 0, 0, 0)

         select_all_button = QPushButton("Select All")
         select_all_button.setFixedWidth(70)
         select_all_layout.addWidget(select_all_button)
         self.setCellWidget(row, 0, select_all_widget)

         # add checkboxes for each particle file
         for col, _ in enumerate(pcf_files):
            cell_widget = QWidget()
            layout = QHBoxLayout(cell_widget)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)

            checkbox = self.create_checkbox(row, col + 1)  # shift column index by 1
            layout.addWidget(checkbox)
            self.setCellWidget(row, col + 1, cell_widget)  # shift column index by 1

         # connect Select All button
         select_all_button.clicked.connect(lambda checked, r=row: self.select_all_row(r))

   def select_all_row(self, row):
      # start from column 1 (after Select All button)
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

   def uncheck_column_except(self, col, target_row):
      for row in range(self.rowCount()):
         if row != target_row:
            cell_widget = self.cellWidget(row, col)
            if cell_widget:
               checkbox = cell_widget.layout().itemAt(0).widget()
               if checkbox and checkbox.isChecked():
                  checkbox.setChecked(False)

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

      checkbox.stateChanged.connect(on_state_changed)
      return checkbox

   def get_selected_particles(self):
      selections = {}
      # start from column 1 (after Select All button)
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