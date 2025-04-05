from PyQt6.QtCore import QObject, pyqtSignal


class ProgressManager(QObject):
    progress_updated = pyqtSignal(int, str)

    def __init__(self):
        super().__init__()
        self.current_progress = 0
        self.current_message = ""

    def update_progress(self, progress: int, message: str):
        self.current_progress = progress
        self.current_message = message
        self.progress_updated.emit(progress, message)

    def reset(self):
        self.update_progress(0, "")

    def get_current_progress(self):
        return self.current_progress

    def get_current_message(self):
        return self.current_message