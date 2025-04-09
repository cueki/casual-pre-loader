from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame)

class AddonDescription(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.content_layout = None
        self.name_label = None
        self.type_label = None
        self.version_label = None
        self.description_label = None
        self.features_label = None
        self.features_list = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

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

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.content_layout.addWidget(line)

        self.version_label = QLabel()
        self.version_label.setWordWrap(True)
        self.content_layout.addWidget(self.version_label)

        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.content_layout.addWidget(self.description_label)

        self.features_label = QLabel("Contains:")
        self.features_label.setStyleSheet("font-weight: bold;")
        self.content_layout.addWidget(self.features_label)

        self.features_list = QLabel()
        self.features_list.setWordWrap(True)
        self.content_layout.addWidget(self.features_list)

        self.content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        self.clear()

    def set_type_style(self, addon_type: str):
        colors = {
            "custom": "#4CAF50", # green
            "model": "#2196F3", # blue
            "texture": "#9C27B0", # magenta
            "misc": "#FF9800", # orange
            "animation": "#392C52", # purple
            "experimental": "#EED202", # yellow
            "unknown": "#FF0000" # red
        }

        color = colors.get(addon_type.lower(), "#757575")
        self.type_label.setStyleSheet(f"""
            background-color: {color};
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: bold;
        """)

    def update_content(self, addon_name: str, addon_info: dict):
        self.name_label.setText(addon_name)

        addon_type = addon_info.get("type", "Unknown")
        self.type_label.setText(addon_type.upper())
        self.set_type_style(addon_type)

        version = addon_info.get("version", [])
        if version:
            self.version_label.setText("Version: " + version)
            self.version_label.setStyleSheet(f"""
                color: #aaaaaa;
                """)
            self.version_label.show()
        else:
            self.version_label.hide()

        self.description_label.setText(addon_info.get("description", ""))

        contents = addon_info.get("contents", [])
        if contents:
            self.features_list.setText("• " + "\n• ".join(contents))
            self.features_label.show()
            self.features_list.show()
        else:
            self.features_label.hide()
            self.features_list.hide()

    def clear(self):
        self.name_label.clear()
        self.type_label.clear()
        self.description_label.setText("Select an addon to view details")
        self.features_label.hide()
        self.features_list.hide()