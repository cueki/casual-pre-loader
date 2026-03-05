import json
import logging
import os
import subprocess
from sys import platform

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from valve_parsers import VPKFile

from core.constants import MOD_TYPE_COLORS
from gui.theme import COMBOBOX_POPUP_STYLE, FG_LIGHTEST, FG_MUTED
from core.folder_setup import folder_setup

log = logging.getLogger()


class ModJsonEditor(QDialog):
    addon_updated = pyqtSignal()

    def __init__(self, addon_name, addon_info, parent=None):
        super().__init__(parent)
        self.gamebanana_edit = None
        self.description_edit = None
        self.version_edit = None
        self.type_combo = None
        self.name_edit = None
        self.color_edit = None
        self.color_preview = None
        self.addon_name = addon_name
        self.addon_info = addon_info
        self.setWindowTitle(f"Edit {addon_name}")
        self.setObjectName("ModJsonEditor")
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

        # form layout
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)

        # addon name
        self.name_edit = QLineEdit()
        self.name_edit.setMinimumWidth(350)
        form_layout.addRow("Addon Name:", self.name_edit)

        # type dropdown
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Skin", "Model", "Texture", "Misc", "Animation", "Experimental", "HUD", "Sound"])
        self.type_combo.view().window().setStyleSheet(COMBOBOX_POPUP_STYLE)
        form_layout.addRow("Type:", self.type_combo)

        # custom color (optional)
        color_row = QHBoxLayout()
        color_row.setContentsMargins(0, 0, 0, 0)
        self.color_edit = QLineEdit()
        self.color_edit.setPlaceholderText("#RRGGBB")
        self.color_edit.textChanged.connect(self.update_color_preview)
        color_row.addWidget(self.color_edit, 1)

        self.color_preview = QPushButton()
        self.color_preview.setFixedSize(28, 28)
        self.color_preview.clicked.connect(self.pick_color)
        color_row.addWidget(self.color_preview)

        clear_color_btn = QPushButton("Clear")
        clear_color_btn.clicked.connect(lambda: self.color_edit.setText(""))
        color_row.addWidget(clear_color_btn)

        color_widget = QWidget()
        color_widget.setLayout(color_row)
        form_layout.addRow("Color (optional):", color_widget)

        # version
        self.version_edit = QLineEdit()
        form_layout.addRow("Version:", self.version_edit)

        # description
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        form_layout.addRow("Description:", self.description_edit)

        # gamebanana link
        self.gamebanana_edit = QLineEdit()
        self.gamebanana_edit.setPlaceholderText("https://gamebanana.com/mods/...")
        form_layout.addRow("GameBanana Link:", self.gamebanana_edit)

        layout.addLayout(form_layout)
        layout.addStretch()

        # buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setProperty("primary", True)
        save_btn.clicked.connect(self.save_changes)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def load_data(self):
        self.name_edit.setText(self.addon_info.get("addon_name", ""))

        addon_type = self.addon_info.get("type", "Unknown")
        index = self.type_combo.findText(addon_type, Qt.MatchFlag.MatchFixedString)
        if index >= 0:
            self.type_combo.setCurrentIndex(index)

        self.version_edit.setText(self.addon_info.get("version", ""))
        self.description_edit.setPlainText(self.addon_info.get("description", ""))
        self.gamebanana_edit.setText(self.addon_info.get("gamebanana_link", ""))

        # load custom color if set
        custom_color = self.addon_info.get("color", "")
        self.color_edit.setText(custom_color)
        self.update_color_preview()

    def update_color_preview(self):
        color = self.color_edit.text().strip()
        if color and color.startswith("#") and len(color) in (4, 7):
            self.color_preview.setStyleSheet(f"background-color: {color}; border: 1px solid {FG_LIGHTEST};")
        else:
            # Show unknown color when no custom color is set
            unknown_color = MOD_TYPE_COLORS.get("unknown", "#FF0000")
            self.color_preview.setStyleSheet(f"background-color: {unknown_color}; border: 1px solid {FG_LIGHTEST};")

    def pick_color(self):
        current = self.color_edit.text().strip()
        unknown_color = MOD_TYPE_COLORS.get("unknown", "#FF0000")
        initial = QColor(current) if current and current.startswith("#") else QColor(unknown_color)
        color = QColorDialog.getColor(initial, self, "Select Color")
        if color.isValid():
            self.color_edit.setText(color.name())

    def save_changes(self):
        folder_name = self.addon_info.get("file_path", self.addon_name)
        mod_json_path = folder_setup.addons_dir / folder_name / "mod.json"

        # build updated json
        updated_data = {
            "addon_name": self.name_edit.text(),
            "type": self.type_combo.currentText(),
            "version": self.version_edit.text(),
            "description": self.description_edit.toPlainText(),
            "gamebanana_link": self.gamebanana_edit.text()
        }

        # only include color if set
        custom_color = self.color_edit.text().strip()
        if custom_color and custom_color.startswith("#"):
            updated_data["color"] = custom_color

        # preserve existing contents field if it exists
        if "contents" in self.addon_info:
            updated_data["contents"] = self.addon_info["contents"]

        try:
            mod_json_path.parent.mkdir(parents=True, exist_ok=True)
            with open(mod_json_path, 'w') as f:
                json.dump(updated_data, f, indent=2)
            self.addon_updated.emit()
            self.accept()
        except Exception:
            log.exception("Failed to save mod.json")
            QMessageBox.critical(self, "Error", "Failed to save mod.json")


class AddonDescription(QWidget):
    addon_modified = pyqtSignal()
    content_changed = pyqtSignal(bool)  # True if has content, False if empty

    def __init__(self, parent=None):
        super().__init__(parent)
        self.gamebanana_label = None
        self.content_layout = None
        self.name_label = None
        self.type_label = None
        self.separator_line = None
        self.version_label = None
        self.description_label = None
        self.features_label = None
        self.features_list = None
        self.current_addon_name = None
        self.current_addon_info = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        self.content_layout = QVBoxLayout(content)

        self.name_label = QLabel()
        self.name_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.content_layout.addWidget(self.name_label)

        self.type_label = QLabel()
        self.type_label.setStyleSheet("""
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: bold;
        """)
        self.content_layout.addWidget(self.type_label)

        self.separator_line = QFrame()
        self.separator_line.setFrameShape(QFrame.Shape.HLine)
        self.separator_line.setFrameShadow(QFrame.Shadow.Sunken)
        self.content_layout.addWidget(self.separator_line)

        self.version_label = QLabel()
        self.version_label.setWordWrap(True)
        self.content_layout.addWidget(self.version_label)

        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.content_layout.addWidget(self.description_label)

        self.gamebanana_label = QLabel()
        self.gamebanana_label.setOpenExternalLinks(True)
        self.gamebanana_label.setWordWrap(True)
        self.content_layout.addWidget(self.gamebanana_label)

        self.features_label = QLabel("Contains:")
        self.features_label.setStyleSheet("font-weight: bold;")
        self.content_layout.addWidget(self.features_label)

        self.features_list = QLabel()
        self.features_list.setWordWrap(True)
        self.content_layout.addWidget(self.features_list)

        self.content_layout.addStretch()

        self.scroll.setWidget(content)
        layout.addWidget(self.scroll)

        self.clear()

    def set_type_style(self, addon_type: str, custom_color: str = None):
        if custom_color and custom_color.startswith("#"):
            color = custom_color
        else:
            color = MOD_TYPE_COLORS.get(addon_type.lower(), "#757575")
        self.type_label.setStyleSheet(f"""
            background-color: {color};
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: bold;
        """)

    def update_content(self, addon_name: str, addon_info: dict):
        self.current_addon_name = addon_name
        self.current_addon_info = addon_info
        self.name_label.setText(addon_name)
        self.name_label.show()
        self.type_label.show()
        self.separator_line.show()

        addon_type = addon_info.get("type", "Unknown")
        self.type_label.setText(addon_type.upper())
        custom_color = addon_info.get("color")
        self.set_type_style(addon_type, custom_color)

        version = addon_info.get("version", "")
        if version:
            self.version_label.setText("Version: " + version)
            self.version_label.setStyleSheet(f"color: {FG_MUTED};")
            self.version_label.show()
        else:
            self.version_label.hide()

        self.description_label.setText(addon_info.get("description", ""))

        # gamebanana link
        gamebanana_link = addon_info.get("gamebanana_link", "")
        if gamebanana_link and gamebanana_link.startswith("https://gamebanana.com"):
            self.gamebanana_label.setText(f'<a href="{gamebanana_link}">View on GameBanana</a>')
            self.gamebanana_label.show()
        else:
            self.gamebanana_label.hide()

        contents = addon_info.get("contents", [])
        if contents:
            self.features_list.setText("• " + "\n• ".join(contents))
            self.features_label.show()
            self.features_list.show()
        else:
            self.features_label.hide()
            self.features_list.hide()

        self.content_changed.emit(True)

    def clear(self):
        self.current_addon_name = None
        self.current_addon_info = None
        self.name_label.hide()
        self.type_label.hide()
        self.separator_line.hide()
        self.version_label.hide()
        self.description_label.setText("Select an addon to view details")
        self.gamebanana_label.hide()
        self.features_label.hide()
        self.features_list.hide()
        self.content_changed.emit(False)

    def open_editor(self):
        if self.current_addon_name and self.current_addon_info:
            dialog = ModJsonEditor(self.current_addon_name, self.current_addon_info, self.window())
            dialog.addon_updated.connect(self.addon_modified.emit)
            dialog.addon_updated.connect(self.refresh_current_addon)
            dialog.exec()

    def export_addon(self):
        if not self.current_addon_name or not self.current_addon_info:
            return

        folder_name = self.current_addon_info.get("file_path", self.current_addon_name)
        addon_dir = folder_setup.addons_dir / folder_name
        default_name = folder_name.replace(" ", "_")

        # custom dialog with .vpk suffix
        dialog = QDialog(self.window())
        dialog.setWindowTitle(f"Export {self.current_addon_name}")
        layout = QVBoxLayout(dialog)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

        label = QLabel("VPK filename:")
        layout.addWidget(label)

        input_layout = QHBoxLayout()
        name_input = QLineEdit(default_name)
        name_input.setMinimumWidth(300)
        input_layout.addWidget(name_input)
        suffix_label = QLabel(".vpk")
        input_layout.addWidget(suffix_label)
        layout.addLayout(input_layout)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        ok_btn = QPushButton("Export")
        ok_btn.setProperty("primary", True)
        ok_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_btn)
        layout.addLayout(button_layout)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        vpk_name = name_input.text()
        if not vpk_name:
            return

        exports_dir = folder_setup.mods_dir / 'exports'
        exports_dir.mkdir(parents=True, exist_ok=True)
        vpk_path = exports_dir / vpk_name

        try:
            addon_dir.mkdir(parents=True, exist_ok=True) # INFO: technically not necessary, but VPKFile does not check if `source_dir` exists
            total_size = sum(f.stat().st_size for f in addon_dir.rglob('*') if f.is_file())
            split_size = 200 * 1024 * 1024 if total_size > 200 * 1024 * 1024 else None
            if not VPKFile.create(str(addon_dir), str(vpk_path), split_size=split_size):
                QMessageBox.critical(self, "Export Failed", "Failed to create VPK file.")
                return
            # open exports folder for user
            if platform == "win32":
                os.startfile(str(exports_dir))
            else:
                subprocess.run(["xdg-open", str(exports_dir)])

        except Exception:
            log.exception("Error exporting addon")
            QMessageBox.critical(self, "Export Failed", "Error exporting addon")

    def refresh_current_addon(self):
        if self.current_addon_name and self.current_addon_info:
            folder_name = self.current_addon_info.get("file_path", self.current_addon_name)
            mod_json_path = folder_setup.addons_dir / folder_name / "mod.json"
            try:
                mod_json_path.parent.mkdir(parents=True, exist_ok=True)
                with open(mod_json_path, 'r') as f:
                    updated_info = json.load(f)
                    updated_info['file_path'] = folder_name
                    self.update_content(updated_info.get("addon_name", self.current_addon_name), updated_info)
            except Exception:
                log.exception("Error refreshing addon details")
                self.clear()
