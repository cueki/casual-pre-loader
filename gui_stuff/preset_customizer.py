import json
from pathlib import Path
import zipfile
from typing import Dict, Set

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                            QLineEdit, QLabel, QScrollArea, QWidget, QCheckBox,
                            QMessageBox, QFrame)
from PyQt6.QtCore import Qt, pyqtSlot


class FileCheckFrame(QFrame):
    def __init__(self, filename: str, on_toggle, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 1, 5, 1)

        self.checkbox = QCheckBox()
        self.checkbox.clicked.connect(lambda: on_toggle(filename, self.checkbox.isChecked()))
        layout.addWidget(self.checkbox)

        self.label = QLabel(filename)
        self.label.mouseReleaseEvent = lambda e: self.toggle()
        layout.addWidget(self.label)
        layout.addStretch()

    def toggle(self):
        self.checkbox.setChecked(not self.checkbox.isChecked())
        self.checkbox.clicked.emit()

    def set_checked(self, checked: bool):
        self.checkbox.setChecked(checked)


class PresetSelectionManager:
    def __init__(self):
        self.selections_file = Path("preset_selections.json")
        self.selections = self.load_selections()

    def load_selections(self) -> Dict[str, list]:
        try:
            if self.selections_file.exists():
                with open(self.selections_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading selections: {e}")
            return {}

    def save_selections(self) -> None:
        try:
            with open(self.selections_file, 'w') as f:
                json.dump(self.selections, f, indent=2)
        except Exception as e:
            print(f"Error saving selections: {e}")

    def get_selection(self, preset_name: str) -> Set[str]:
        return set(self.selections.get(preset_name, []))

    def save_selection(self, preset_name: str, selected_files: Set[str]) -> None:
        self.selections[preset_name] = list(selected_files)
        self.save_selections()


class PresetCustomizer(QDialog):
    def __init__(self, parent, preset_name: str, selection_manager):
        super().__init__(parent)
        # she init on my super till i oop
        self.selection_label = None
        self.files_layout = None
        self.files_widget = None
        self.select_all_btn = None
        self.search_edit = None

        self.setWindowTitle(f"Customize Preset: {preset_name}")
        self.setFixedSize(600, 500)
        self.setModal(True)

        self.parent = parent
        self.preset_name = preset_name
        self.selection_manager = selection_manager
        self.selected_files = self.selection_manager.get_selection(preset_name)
        self.available_files = []
        self.file_frames = {}

        self.setup_ui()
        self.load_preset_files()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Search bar
        search_frame = QWidget()
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(0, 0, 0, 0)

        search_icon = QLabel("🔍")
        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self.filter_files)

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.toggle_all)

        search_layout.addWidget(search_icon)
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(self.select_all_btn)
        layout.addWidget(search_frame)

        # Scrollable files area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.files_widget = QWidget()
        self.files_layout = QVBoxLayout(self.files_widget)
        self.files_layout.setSpacing(1)
        self.files_layout.addStretch()

        scroll.setWidget(self.files_widget)
        layout.addWidget(scroll)

        # Selection counter
        self.selection_label = QLabel("Selected: 0 files")
        layout.addWidget(self.selection_label)

        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save Selection")
        save_button.clicked.connect(self.save_selection)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

    def load_preset_files(self):
        preset_path = Path("presets") / f"{self.preset_name}.zip"
        try:
            with zipfile.ZipFile(preset_path, 'r') as zip_ref:
                self.available_files = sorted([
                    name.split('/')[-1] for name in zip_ref.namelist()
                    if name.endswith('.pcf') and 'particles/' in name
                ])

            for file in self.available_files:
                frame = FileCheckFrame(file, self.on_file_toggle, self)
                frame.set_checked(file in self.selected_files)
                self.files_layout.insertWidget(self.files_layout.count() - 1, frame)
                self.file_frames[file] = frame

            self.update_selection_count()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read preset: {str(e)}")
            self.reject()

    @pyqtSlot(str)
    def filter_files(self, search_term: str):
        search_term = search_term.lower()
        for filename, frame in self.file_frames.items():
            frame.setVisible(search_term in filename.lower())

    def toggle_all(self):
        visible_files = [
            f for f in self.available_files
            if self.search_edit.text().lower() in f.lower()
        ]
        all_checked = all(f in self.selected_files for f in visible_files)

        for file in visible_files:
            frame = self.file_frames[file]
            if all_checked:
                self.selected_files.discard(file)
                frame.set_checked(False)
            else:
                self.selected_files.add(file)
                frame.set_checked(True)

        self.update_selection_count()
        self.select_all_btn.setText("Select All" if all_checked else "Deselect All")

    def on_file_toggle(self, filename: str, checked: bool):
        if checked:
            self.selected_files.add(filename)
        else:
            self.selected_files.discard(filename)
        self.update_selection_count()

    def update_selection_count(self):
        self.selection_label.setText(f"Selected: {len(self.selected_files)} files")

    def save_selection(self):
        if not self.selected_files and not QMessageBox.question(
                self, "Warning", "No files selected. Are you sure you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            return

        self.selection_manager.save_selection(self.preset_name, self.selected_files)
        self.parent.selected_preset_files = self.selected_files
        self.accept()

    def reject(self):
        self.parent.selected_preset_files = self.selection_manager.get_selection(self.preset_name)
        super().reject()