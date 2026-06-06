"""Shared dark theme for OwlLock dialogs."""

from PyQt6.QtWidgets import QApplication

OWLLOCK_STYLESHEET = """
QWidget {
    background: #0d1424;
    color: #e7efff;
    font-size: 13px;
}
QFrame#ShellCard, QFrame#AppCard, QFrame#HeroCard, QFrame#FaceCard, QFrame#PanelCard {
    background: #101a2f;
    border: 1px solid #203455;
    border-radius: 16px;
}
QLabel#Title {
    font-size: 30px;
    font-weight: 700;
    background: transparent;
}
QLabel#SectionTitle {
    font-size: 18px;
    font-weight: 700;
    background: transparent;
}
QLabel#Subtitle, QLabel#Muted {
    color: #90a7d3;
    background: transparent;
}
QLineEdit {
    background: #0e1728;
    border: 1px solid #263d63;
    border-radius: 10px;
    padding: 10px 12px;
    color: #e7efff;
}
QPushButton {
    background: #2f77ff;
    border: none;
    color: white;
    border-radius: 10px;
    padding: 10px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background: #4384ff;
}
QPushButton[secondary="true"] {
    background: #1a2a46;
    color: #e7efff;
}
QPushButton[secondary="true"]:hover {
    background: #233758;
}
QScrollArea {
    border: none;
    background: transparent;
}
QListWidget {
    background: #0e1728;
    border: 1px solid #263d63;
    border-radius: 12px;
    padding: 6px;
}
QListWidget::item {
    padding: 8px 10px;
    border-radius: 8px;
}
QListWidget::item:selected {
    background: #2f77ff;
    color: white;
}
QPushButton#LockButton {
    background: #2f77ff;
    color: white;
}
QPushButton#UnlockButton {
    background: #e54848;
    color: white;
}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(OWLLOCK_STYLESHEET)
