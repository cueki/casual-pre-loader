from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame)
from PyQt6.QtCore import Qt
from pathlib import Path


class PresetDescription(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.preview_image = None
        self.preview_label = None
        self.features_list = None
        self.features_label = None
        self.description_label = None
        self.type_label = None
        self.name_label = None
        self.content_layout = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        self.content_layout = QVBoxLayout(content)

        # Preset name and type
        self.name_label = QLabel()
        self.name_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.content_layout.addWidget(self.name_label)

        self.type_label = QLabel()
        self.type_label.setStyleSheet("""
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: bold;
            display: inline-block;
        """)
        self.content_layout.addWidget(self.type_label)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.content_layout.addWidget(line)

        # Description
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.content_layout.addWidget(self.description_label)

        # Features section
        self.features_label = QLabel("Features:")
        self.features_label.setStyleSheet("font-weight: bold;")
        self.content_layout.addWidget(self.features_label)

        self.features_list = QLabel()
        self.features_list.setWordWrap(True)
        self.content_layout.addWidget(self.features_list)

        # Preview images section
        self.preview_label = QLabel("Preview:")
        self.preview_label.setStyleSheet("font-weight: bold;")
        self.content_layout.addWidget(self.preview_label)

        self.preview_image = QLabel()
        self.content_layout.addWidget(self.preview_image)

        self.content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Default state
        self.clear()

    def set_type_style(self, preset_type: str):
        colors = {
            "vanilla": "#4CAF50",  # Green
            "fun": "#9C27B0",  # Purple
            "friend": "#2196F3"  # Blue
        }

        color = colors.get(preset_type.lower(), "#757575")
        self.type_label.setStyleSheet(f"""
            background-color: {color};
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: bold;
        """)

    def update_content(self, preset_name: str, preset_info: dict):
        self.name_label.setText(preset_name)

        preset_type = preset_info.get("type", "Unknown")
        self.type_label.setText(preset_type.upper())
        self.set_type_style(preset_type)

        self.description_label.setText(preset_info.get("description", ""))

        features = preset_info.get("features", [])
        if features:
            self.features_list.setText("• " + "\n• ".join(features))
            self.features_label.show()
            self.features_list.show()
        else:
            self.features_label.hide()
            self.features_list.hide()

        # Handle preview image if provided
        preview_path = preset_info.get("preview")
        if preview_path and Path(preview_path).exists():
            # Image loading logic here
            self.preview_label.show()
            self.preview_image.show()
        else:
            self.preview_label.hide()
            self.preview_image.hide()

    def clear(self):
        self.name_label.clear()
        self.type_label.clear()
        self.description_label.setText("Select a preset to view details")
        self.features_label.hide()
        self.features_list.hide()
        self.preview_label.hide()
        self.preview_image.hide()