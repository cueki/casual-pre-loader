# Color Palette
# TODO: Abstract this away so users can set their own theme

# Primary colors (lavender)
PRIMARY = "#9b7bc9"              # oklch(70% 0.12 280)
PRIMARY_LIGHT = "#b99bdf"        # oklch(80% 0.12 280)
PRIMARY_DARK = "#7d5bb3"         # oklch(60% 0.12 280)

# Accent (same as primary)
ACCENT = "#9b7bc9"
ACCENT_TRANSPARENT = "rgba(155, 123, 201, 0.1)"

# Background and text
BG_DEFAULT = "#1a1a1f"           # oklch(10% 0.04 280)
FG_DEFAULT = "#e4e2e8"           # oklch(90% 0.04 280)
FG_MUTED = "#9e9ba3"             # oklch(65% 0.04 280)
FG_LIGHTER = "#76747c"           # oklch(50% 0.04 280)
FG_LIGHTEST = "#5a585f"          # oklch(40% 0.04 280)

# Code blocks / elevated surfaces
CODE_BG = "#2d2b32"              # oklch(20% 0.04 280)
CODE_FG = "#e4e2e8"              # oklch(90% 0.04 280)

# UI elements
KBD_BG = "#45434a"               # oklch(30% 0.04 280)
KBD_BORDER = "#5a585f"           # oklch(40% 0.04 280)
KBD_BG_HOVER = "#55535a"         # oklch(35% 0.04 280)
TABLE_BG = "#2d2b32"             # oklch(20% 0.04 280)

# Status colors
WARNING = "#d9a65c"
DANGER = "#c9534a"
DANGER_HOVER = "#d9635a"
SUCCESS = "#4CAF50"

# Font
FONT_FAMILY = '"Segoe UI", "Roboto", "Noto Sans", "Helvetica Neue", sans-serif'
FONT_SIZE_SMALL = "11px"
FONT_SIZE_NORMAL = "14px"
FONT_SIZE_HEADER = "18px"


GLOBAL_STYLESHEET = f"""
    /* Base widget styles */
    QWidget {{
        font-family: {FONT_FAMILY};
        font-size: {FONT_SIZE_NORMAL};
        color: {FG_DEFAULT};
    }}

    QDialog, QDialog#ModJsonEditor {{
        background-color: {BG_DEFAULT};
    }}

    QLabel {{
        color: {FG_DEFAULT};
    }}

    QLabel[muted="true"] {{
        color: {FG_MUTED};
    }}

    /* Bold text */
    QLabel[bold="true"], QGroupBox::title {{
        font-weight: 700;
    }}

    /* Links / clickable text */
    QLabel[link="true"] {{
        color: {PRIMARY};
    }}
    QLabel[link="true"]:hover {{
        color: {PRIMARY_LIGHT};
    }}

    /* Buttons */
    QPushButton {{
        background-color: {CODE_BG};
        color: {FG_DEFAULT};
        padding: 8px 16px;
        border: none;
        border-radius: 4px;
    }}
    QPushButton:hover {{
        background-color: {KBD_BG};
    }}
    QPushButton:pressed {{
        background-color: {PRIMARY_DARK};
    }}
    QPushButton:checked {{
        background-color: {PRIMARY};
        color: {FG_DEFAULT};
    }}
    QPushButton:disabled {{
        background-color: {FG_LIGHTEST};
        color: {FG_LIGHTER};
    }}

    /* Primary buttons */
    QPushButton[primary="true"] {{
        background-color: {PRIMARY};
        color: {FG_DEFAULT};
        font-weight: 700;
    }}
    QPushButton[primary="true"]:hover {{
        background-color: {PRIMARY_LIGHT};
    }}
    QPushButton[primary="true"]:pressed {{
        background-color: {PRIMARY_DARK};
    }}

    /* Danger buttons */
    QPushButton[danger="true"] {{
        background-color: {DANGER};
        color: {FG_DEFAULT};
        font-weight: 700;
    }}
    QPushButton[danger="true"]:hover {{
        background-color: {DANGER_HOVER};
    }}

    /* List widgets */
    QListWidget {{
        background-color: {CODE_BG};
        border: none;
        border-radius: 4px;
        color: {FG_DEFAULT};
        outline: none;
    }}
    QListWidget::item {{
        padding: 8px;
    }}
    QListWidget::item:selected {{
        background-color: {KBD_BG};
        color: {FG_DEFAULT};
    }}
    QListWidget::item:hover:!selected {{
        background-color: {ACCENT_TRANSPARENT};
    }}
    QListWidget::item:focus {{
        outline: none;
        border: none;
    }}
    QListWidget::indicator:unchecked {{
        background-color: {KBD_BG};
        border: 1px solid {FG_LIGHTEST};
        border-radius: 3px;
    }}
    QListWidget::indicator:checked {{
        background-color: {PRIMARY};
        border: 1px solid {PRIMARY};
        border-radius: 3px;
    }}

    /* Group boxes */
    QGroupBox {{
        font-weight: 700;
        color: {FG_DEFAULT};
        border: 1px solid {FG_LIGHTEST};
        border-radius: 8px;
        margin-top: 12px;
        padding: 15px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
    }}

    /* Line edits */
    QLineEdit {{
        background-color: {CODE_BG};
        border: 1px solid {FG_LIGHTEST};
        border-radius: 4px;
        color: {FG_DEFAULT};
        padding: 6px 10px;
    }}
    QLineEdit:focus {{
        border: 1px solid {PRIMARY};
    }}

    /* Text edits */
    QTextEdit {{
        background-color: {CODE_BG};
        border: 1px solid {FG_LIGHTEST};
        border-radius: 4px;
        color: {FG_DEFAULT};
        padding: 6px;
    }}
    QTextEdit:focus {{
        border: 1px solid {PRIMARY};
    }}

    /* Combo boxes */
    QComboBox {{
        background-color: {CODE_BG};
        border: 1px solid {FG_LIGHTEST};
        padding: 6px 10px;
        color: {FG_DEFAULT};
    }}
    QComboBox:focus {{
        border: 1px solid {PRIMARY};
    }}
    QComboBox::drop-down {{
        width: 0px;
        border: none;
    }}

    /* Tables */
    QTableWidget {{
        background-color: {TABLE_BG};
        border: none;
        gridline-color: {FG_LIGHTEST};
    }}
    QTableWidget::item {{
        padding: 4px;
        color: {FG_DEFAULT};
    }}
    QHeaderView::section {{
        background-color: {KBD_BG};
        color: {FG_DEFAULT};
        padding: 6px;
        border: 1px solid {FG_LIGHTEST};
        font-weight: normal;
    }}

    /* Checkboxes */
    QCheckBox {{
        padding-left: 7px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
    }}
    QCheckBox::indicator:unchecked {{
        background-color: {KBD_BG};
        border: 1px solid {FG_LIGHTEST};
        border-radius: 3px;
    }}
    QCheckBox::indicator:checked {{
        background-color: {PRIMARY};
        border: 1px solid {PRIMARY};
        border-radius: 3px;
    }}
    QCheckBox::indicator:disabled {{
        background-color: {BG_DEFAULT};
        border: 1px solid {FG_LIGHTEST};
    }}

    /* Menus */
    QMenu {{
        background-color: {CODE_BG};
        color: {FG_DEFAULT};
        border: 1px solid {FG_LIGHTEST};
    }}
    QMenu::item:selected {{
        background-color: {KBD_BG};
    }}

    /* Scrollbars */
    QScrollBar:vertical {{
        background-color: {BG_DEFAULT};
        width: 10px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {FG_LIGHTEST};
        border-radius: 5px;
        min-height: 20px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {FG_LIGHTER};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        background-color: {BG_DEFAULT};
        height: 10px;
        border-radius: 5px;
    }}
    QScrollBar::handle:horizontal {{
        background-color: {FG_LIGHTEST};
        border-radius: 5px;
        min-width: 20px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background-color: {FG_LIGHTER};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* Tab widgets */
    QTabWidget::pane {{
        background-color: {BG_DEFAULT};
        border: none;
    }}
    QTabBar::tab {{
        background-color: {KBD_BG};
        color: {FG_DEFAULT};
        padding: 8px 16px;
        border: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background-color: {BG_DEFAULT};
    }}
    QTabBar::tab:hover:!selected {{
        background-color: {FG_LIGHTEST};
    }}
"""


SIDEBAR_NAV_STYLE = f"""
    QListWidget {{
        border: none;
        background-color: {CODE_BG};
        color: {FG_DEFAULT};
        font-size: {FONT_SIZE_NORMAL};
        outline: none;
    }}
    QListWidget::item {{
        padding: 10px 12px;
        border-radius: 4px;
        margin: 2px 6px;
        border-bottom: none;
        color: {FG_DEFAULT};
    }}
    QListWidget::item:selected {{
        background-color: {KBD_BG};
        color: {FG_DEFAULT};
    }}
    QListWidget::item:hover:!selected {{
        background-color: {ACCENT_TRANSPARENT};
        color: {FG_DEFAULT};
    }}
    QListWidget::item:focus {{
        outline: none;
        border: none;
    }}
"""


PROFILE_BUTTON_STYLE = f"""
    QPushButton {{
        padding: 4px 10px;
        border-top-left-radius: 4px;
        border-bottom-left-radius: 4px;
        border-top-right-radius: 0px;
        border-bottom-right-radius: 0px;
        background-color: {KBD_BG};
        color: {FG_DEFAULT};
        border: none;
        text-align: left;
    }}
    QPushButton:hover {{
        background-color: {FG_LIGHTEST};
    }}
    QPushButton::menu-indicator {{
        subcontrol-position: right center;
        subcontrol-origin: padding;
        right: 8px;
    }}
"""

PROFILE_ADD_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {KBD_BG};
        color: {FG_DEFAULT};
        border: none;
        border-top-left-radius: 0px;
        border-bottom-left-radius: 0px;
        border-top-right-radius: 4px;
        border-bottom-right-radius: 4px;
        border-left: 1px solid {FG_LIGHTEST};
    }}
    QPushButton:hover {{
        background-color: {FG_LIGHTEST};
    }}
    QPushButton::menu-indicator {{
        width: 0px;
    }}
"""

BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {CODE_BG};
        color: {FG_DEFAULT};
        padding: 8px 16px;
        border: none;
        border-radius: 4px;
    }}
    QPushButton:hover {{
        background-color: {KBD_BG};
    }}
    QPushButton:checked {{
        background-color: {PRIMARY};
        color: {FG_DEFAULT};
    }}
    QPushButton:disabled {{
        background-color: {FG_LIGHTEST};
        color: {FG_LIGHTER};
    }}
"""

DANGER_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {DANGER};
        color: {FG_DEFAULT};
        padding: 8px 16px;
        border: none;
        border-radius: 4px;
        font-weight: 700;
    }}
    QPushButton:hover {{
        background-color: {DANGER_HOVER};
    }}
    QPushButton:disabled {{
        background-color: {FG_LIGHTEST};
        color: {FG_LIGHTER};
    }}
"""

BUTTON_STYLE_ALT = f"""
    QPushButton {{
        background-color: {KBD_BG};
        color: {FG_DEFAULT};
        padding: 8px 16px;
        border: none;
        border-radius: 4px;
    }}
    QPushButton:hover {{
        background-color: {KBD_BG_HOVER};
    }}
    QPushButton:disabled {{
        background-color: {FG_LIGHTEST};
        color: {FG_LIGHTER};
    }}
"""

COMBOBOX_POPUP_STYLE = f"""
    * {{
        background-color: {CODE_BG};
        border: none;
    }}
    QFrame {{
        background-color: {CODE_BG};
        border: 1px solid {FG_LIGHTEST};
    }}
    QListView {{
        background-color: {CODE_BG};
        color: {FG_DEFAULT};
        border: none;
        outline: none;
    }}
    QListView::item {{
        padding: 6px 10px;
        background-color: {CODE_BG};
    }}
    QListView::item:hover {{
        background-color: {KBD_BG};
    }}
    QListView::item:selected {{
        background-color: {KBD_BG};
    }}
"""

# Common style patterns
FRAME_STYLE = f"background-color: {CODE_BG}; border-radius: 8px;"
SECTION_LABEL_STYLE = f"color: {FG_MUTED}; font-weight: bold;"
