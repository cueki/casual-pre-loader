from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QCheckBox, QProgressBar,
                             QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from core.auto_updater import AutoUpdater
from gui.settings_manager import SettingsManager


class UpdateWorker(QThread):
    progress_updated = pyqtSignal(str)
    update_completed = pyqtSignal(bool, str)
    
    def __init__(self, updater):
        super().__init__()
        self.updater = updater
    
    def run(self):
        try:
            self.progress_updated.emit("Starting update...")
            result = self.updater.perform_update()
            
            if result.get("error"):
                self.update_completed.emit(False, f"Update failed: {result['error']}")
            elif result.get("app_updated"):
                self.update_completed.emit(True, "Update completed successfully! Please restart the application.")
            else:
                self.update_completed.emit(False, "Update failed: No update file found")
        
        except Exception as e:
            self.update_completed.emit(False, f"Update failed: {str(e)}")


class UpdateDialog(QDialog):
    def __init__(self, update_info, parent=None):
        super().__init__(parent)
        self.update_button = None
        self.later_button = None
        self.skip_button = None
        self.suppress_checkbox = None
        self.progress_label = None
        self.progress_bar = None
        self.update_info = update_info
        self.updater = AutoUpdater()
        self.update_worker = None
        self.settings_manager = SettingsManager()
        
        self.setWindowTitle("Update Available")
        self.setMinimumSize(500, 400)
        self.setModal(True)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # title
        title_label = QLabel(f"Update Available: v{self.update_info['version']}")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # release notes
        notes_label = QLabel("Release Notes:")
        notes_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(notes_label)
        
        notes_text = QTextEdit()
        notes_text.setPlainText(self.update_info.get("body", "No release notes available"))
        notes_text.setMaximumHeight(150)
        notes_text.setReadOnly(True)
        layout.addWidget(notes_text)
        
        # progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # progress label (initially hidden)
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)
        
        # suppress checkbox
        self.suppress_checkbox = QCheckBox("Don't ask about updates again")
        layout.addWidget(self.suppress_checkbox)
        
        # buttons
        button_layout = QHBoxLayout()
        
        self.skip_button = QPushButton("Skip This Version")
        self.skip_button.clicked.connect(self.skip_version)
        button_layout.addWidget(self.skip_button)
        
        self.later_button = QPushButton("Remind Me Later")
        self.later_button.clicked.connect(self.remind_later)
        button_layout.addWidget(self.later_button)
        
        self.update_button = QPushButton("Update Now")
        self.update_button.clicked.connect(self.start_update)
        self.update_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        button_layout.addWidget(self.update_button)
        
        layout.addLayout(button_layout)
    
    def skip_version(self):
        if self.suppress_checkbox.isChecked():
            self.save_suppress_setting()
        else:
            self.save_skipped_version()
        self.reject()
    
    def remind_later(self):
        self.reject()
    
    def start_update(self):
        # disable buttons and show progress
        self.skip_button.setEnabled(False)
        self.later_button.setEnabled(False)
        self.update_button.setEnabled(False)
        self.suppress_checkbox.setEnabled(False)
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.progress_label.setVisible(True)
        
        # start update worker
        self.update_worker = UpdateWorker(self.updater)
        self.update_worker.progress_updated.connect(self.update_progress)
        self.update_worker.update_completed.connect(self.update_finished)
        self.update_worker.start()
    
    def update_progress(self, message):
        self.progress_label.setText(message)
    
    def update_finished(self, success, message):
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        
        if success:
            QMessageBox.information(self, "Update Complete", message)
            self.accept()
        else:
            QMessageBox.critical(self, "Update Failed", message)
            self.skip_button.setEnabled(True)
            self.later_button.setEnabled(True)
            self.update_button.setEnabled(True)
            self.suppress_checkbox.setEnabled(True)
    
    def save_suppress_setting(self):
        try:
            self.settings_manager.set_suppress_update_notifications(True)
            print("Suppressing future update notifications")
        except Exception as e:
            print(f"Error saving suppress setting: {e}")
    
    def save_skipped_version(self):
        try:
            self.settings_manager.set_skipped_update_version(self.update_info["version"])
            print(f"Skipped version {self.update_info['version']}")
        except Exception as e:
            print(f"Error saving skipped version: {e}")


def show_update_dialog(update_info, parent=None):
    dialog = UpdateDialog(update_info, parent)
    return dialog.exec()