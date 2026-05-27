from PyQt6.QtWidgets import QMessageBox, QPushButton

from gui.theme import PRIMARY_BUTTON_STYLE


def _top_level(parent):
    # this is really stupid but I do not want to fix it for real right now
    return parent.window() if parent is not None else parent


def confirm_action(parent, title, message):
    # generic yes/no confirmation; defaults to No
    result = QMessageBox.question(
        _top_level(parent), title, message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return result == QMessageBox.StandardButton.Yes


def show_message(parent, icon, title, message):
    # single styled message box used for all info/warning/error popups
    msg_box = QMessageBox(_top_level(parent))
    msg_box.setIcon(icon)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    ok_btn = QPushButton("OK")
    ok_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
    msg_box.addButton(ok_btn, QMessageBox.ButtonRole.AcceptRole)
    msg_box.setDefaultButton(ok_btn)
    msg_box.exec()


def show_error(parent, message, title="Error"):
    show_message(parent, QMessageBox.Icon.Critical, title, message)


def show_success(parent, message, title="Success"):
    show_message(parent, QMessageBox.Icon.Information, title, message)
