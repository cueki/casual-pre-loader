from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.constants import Sourcemods
from core.util.sourcemod import (
    InvalidSourcemod,
    InvalidSourcemodInstallationPath,
    auto_detect_sourcemod,
    get_sourcemod,
    validate_game_directory,
)


class ProfileDialog(QDialog):
    def __init__(self, parent=None, name: str | None = None, game_path: Path | None = None, sourcemod: Sourcemods = Sourcemods.DEFAULT):
        super().__init__(parent)
        self.setWindowTitle("New Profile" if not name else "Edit Profile")
        self.setModal(True)

        self.name: str | None = name
        self.game_path: Path | None = game_path
        self.sourcemod: Sourcemods = sourcemod

        layout = QVBoxLayout(self)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

        # Name
        layout.addWidget(QLabel("Profile Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setText(name)
        self.name_edit.setPlaceholderText("e.g. Main, Testing, Competitive...")
        self.name_edit.setMinimumWidth(400)
        layout.addWidget(self.name_edit)

        # Game target (Steam folder name)
        layout.addWidget(QLabel("Sourcemod (For auto detection, optional):"))
        self.sourcemod_edit = QLineEdit()
        self.sourcemod_edit.setText(sourcemod.full_name)
        self.sourcemod_edit.setPlaceholderText("e.g. Team Fortress 2, Team Fortress 2 Classified...")
        layout.addWidget(self.sourcemod_edit)

        # Game path
        layout.addWidget(QLabel("Game Directory:"))
        path_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setText(game_path and str(game_path) or None)
        self.path_edit.setPlaceholderText("Select game directory containing gameinfo.txt...")
        path_row.addWidget(self.path_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)

        auto_detect_btn = QPushButton("Auto-Detect")
        auto_detect_btn.clicked.connect(self.auto_detect)
        layout.addWidget(auto_detect_btn)

        self.validation_label = QLabel("")
        self.validation_label.setWordWrap(True)
        layout.addWidget(self.validation_label)

        if game_path:
            validate_game_directory(game_path, self.validation_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("Save")
        ok_btn.setProperty("primary", True)
        ok_btn.clicked.connect(self.try_accept)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

    def browse(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Game Directory")
        if directory:
            self.game_path = Path(directory)
            self.path_edit.setText(directory)
            validate_game_directory(self.game_path, self.validation_label)

    def auto_detect(self):
        sourcemod = self.sourcemod_edit.text().strip()
        try:
            self.sourcemod = get_sourcemod(sourcemod) if sourcemod else Sourcemods.DEFAULT
        except InvalidSourcemod:
            QMessageBox.information(self, "Auto-Detection Failed",
                                    f"Unknown sourcemod: {sourcemod}.\n"
                                    "Please check the game target name.")
            return

        try:
            self.game_path = auto_detect_sourcemod(self.sourcemod)

            self.path_edit.setText(str(self.game_path))
            validate_game_directory(self.game_path, self.validation_label)
            QMessageBox.information(self, "Auto-Detection Successful", f"Found sourcemod `{self.sourcemod.full_name}` at:\n{self.game_path}")
        except InvalidSourcemodInstallationPath:
            QMessageBox.information(self, "Auto-Detection Failed",
                                    f"Could not find sourcemod '{self.sourcemod.full_name}' in common Steam locations.\n"
                                    "Please manually select your game directory.")

    def try_accept(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Please enter a profile name.")
            return
        if not self.game_path:
            QMessageBox.warning(self, "Validation Error", "Please select a game directory.")
            return
        self.name = name
        self.sourcemod = get_sourcemod(self.sourcemod_edit.text().strip() or None)
        self.accept()
