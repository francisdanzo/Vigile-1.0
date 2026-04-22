from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Callable

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QThread,
    QTimer,
    QVariantAnimation,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QButtonGroup,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config import APP_NAME, APP_SLOGAN, ETATS_MATERIEL, FLASK_PORT
from database import get_session
from models import Attribution, Materiel, User
from qr.generator import generer_qr_code
from tunnel import _get_cloudflared_path, telecharger_cloudflared

COLORS = {
    "bg": "#0d0d14",
    "sidebar": "#111118",
    "card": "#16161f",
    "input": "#1e1e2a",
    "hover": "#22222e",
    "primary": "#7c6bff",
    "secondary": "#00d4aa",
    "danger": "#ff5c7a",
    "warning": "#ffb347",
    "info": "#4da6ff",
    "text": "#f0f0f8",
    "text_secondary": "#9090aa",
    "muted": "#4a4a60",
    "border": "#2a2a38",
    "gold": "#f0c040",
}

STATE_COLORS = {
    "neuf": COLORS["secondary"],
    "bon": COLORS["info"],
    "usagé": COLORS["warning"],
    "en_panne": COLORS["danger"],
}

QSS_PATH = Path(__file__).resolve().parent.parent / "vigile_theme.qss"


def alpha(color: str, value: int) -> str:
    qcolor = QColor(color)
    return f"rgba({qcolor.red()}, {qcolor.green()}, {qcolor.blue()}, {value})"


def clear_layout(layout: QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        child_layout = item.layout()
        if widget:
            widget.deleteLater()
        elif child_layout:
            clear_layout(child_layout)


def apply_shadow(widget: QWidget, blur: int = 30, y_offset: int = 12, alpha_value: int = 110) -> None:
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, y_offset)
    color = QColor("#000000")
    color.setAlpha(alpha_value)
    shadow.setColor(color)
    widget.setGraphicsEffect(shadow)


def load_theme(app: QApplication) -> None:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ):
        if os.path.exists(path):
            QFontDatabase.addApplicationFont(path)
    if QSS_PATH.exists():
        app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    app.setFont(QFont("Inter", 10))


class WorkerSignals(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)


class FunctionWorker(QObject):
    def __init__(self, fn: Callable, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.finished.emit(result)
        except Exception as exc:
            self.signals.failed.emit(str(exc))


def run_in_thread(parent: QObject, fn: Callable, on_success: Callable, on_error: Callable | None = None, *args, **kwargs) -> QThread:
    # Centralise les tâches BD/réseau pour garder l'UI PyQt6 fluide.
    thread = QThread(parent)
    worker = FunctionWorker(fn, *args, **kwargs)
    # Conserver des références explicites évite que Qt/Python libèrent le thread
    # avant que les signaux de fin n'aient le temps de revenir vers l'UI.
    if not hasattr(parent, "_worker_threads"):
        parent._worker_threads = set()
    parent._worker_threads.add(thread)
    thread._worker = worker
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.signals.finished.connect(on_success)
    if on_error:
        worker.signals.failed.connect(on_error)
    worker.signals.finished.connect(thread.quit)
    worker.signals.failed.connect(thread.quit)
    worker.signals.finished.connect(worker.deleteLater)
    worker.signals.failed.connect(worker.deleteLater)
    thread.finished.connect(lambda: parent._worker_threads.discard(thread))
    thread.finished.connect(thread.deleteLater)
    thread.start()
    return thread


class StyledCard(QFrame):
    def __init__(self, parent: QWidget | None = None, padding: int = 14):
        super().__init__(parent)
        self.setObjectName("Card")
        self._border = QColor(COLORS["border"])
        self._animation = QVariantAnimation(self, duration=200)
        self._animation.setStartValue(QColor(COLORS["border"]))
        self._animation.setEndValue(QColor(COLORS["primary"]))
        self._animation.valueChanged.connect(self._on_border_change)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(padding, padding, padding, padding)
        layout.setSpacing(12)
        apply_shadow(self, blur=34, y_offset=10, alpha_value=90)

    def _on_border_change(self, color: QColor) -> None:
        self._border = color
        self.update()

    def enterEvent(self, event) -> None:
        self._animation.setDirection(QPropertyAnimation.Direction.Forward)
        self._animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._animation.setDirection(QPropertyAnimation.Direction.Backward)
        self._animation.start()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        # La bordure est peinte manuellement pour animer la mise en avant au survol.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(COLORS["card"]))
        painter.setPen(QPen(self._border, 1))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 12, 12)


class StatusBadge(QLabel):
    def __init__(self, state: str, text: str | None = None):
        super().__init__(text or state.replace("_", " ").capitalize())
        color = STATE_COLORS.get(state, COLORS["info"])
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            f"QLabel {{ background-color: {alpha(color, 45)}; color: {color}; "
            "padding: 6px 10px; border-radius: 999px; font-size: 11px; font-weight: bold; }}"
        )


class VigileInput(QFrame):
    def __init__(self, label: str, placeholder: str = "", password: bool = False):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        title = QLabel(label)
        title.setObjectName("CaptionLabel")
        layout.addWidget(title)
        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)
        if password:
            self.input.setEchoMode(QLineEdit.EchoMode.Password)
        glow = QGraphicsDropShadowEffect(self.input)
        glow.setBlurRadius(18)
        glow.setOffset(0, 0)
        glow_color = QColor(COLORS["primary"])
        glow_color.setAlpha(80)
        glow.setColor(glow_color)
        glow.setEnabled(False)
        self._glow = glow
        self.input.setGraphicsEffect(glow)
        self.input.installEventFilter(self)
        layout.addWidget(self.input)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.input and event.type() in (QEvent.Type.FocusIn, QEvent.Type.FocusOut):
            self._glow.setEnabled(event.type() == QEvent.Type.FocusIn)
        return super().eventFilter(watched, event)

    def text(self) -> str:
        return self.input.text().strip()

    def setText(self, value: str) -> None:
        self.input.setText(value)


class VigileButton(QPushButton):
    def __init__(self, text: str, variant: str = "primary", parent: QWidget | None = None):
        super().__init__(text, parent)
        self.variant = variant
        self._cached_text = text
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._anim = QPropertyAnimation(self, b"iconSize", self)
        self._anim.setDuration(120)
        self._anim.setStartValue(QSize(18, 18))
        self._anim.setEndValue(QSize(16, 16))
        self.setIconSize(QSize(18, 18))
        self._apply_variant()

    def _apply_variant(self) -> None:
        variants = {
            "primary": (COLORS["primary"], "#ffffff", "transparent"),
            "secondary": ("transparent", COLORS["text"], COLORS["border"]),
            "danger": (COLORS["danger"], "#ffffff", "transparent"),
            "ghost": (COLORS["hover"], COLORS["text"], "transparent"),
        }
        bg, fg, border = variants.get(self.variant, variants["primary"])
        hover_bg = COLORS["hover"] if bg == "transparent" else bg
        self.setStyleSheet(
            f"QPushButton {{ background-color: {bg}; color: {fg}; border: 1px solid {border}; "
            f"border-radius: 8px; padding: 10px 18px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: {hover_bg}; border: 1px solid {COLORS['primary']}; }}"
            f"QPushButton:disabled {{ color: {COLORS['muted']}; border: 1px solid {border}; }}"
        )

    def set_loading(self, loading: bool) -> None:
        self.setDisabled(loading)
        self.setText("Chargement..." if loading else self._cached_text)

    def mousePressEvent(self, event) -> None:
        self._anim.setDirection(QPropertyAnimation.Direction.Forward)
        self._anim.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._anim.setDirection(QPropertyAnimation.Direction.Backward)
        self._anim.start()
        super().mouseReleaseEvent(event)


class SidebarButton(QPushButton):
    clicked_with_key = pyqtSignal(str)

    def __init__(self, key: str, label: str, icon: str):
        super().__init__(f"{icon}  {label}")
        self.key = key
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            f"QPushButton {{ text-align: left; padding: 12px 16px; border-radius: 10px; "
            f"background: transparent; color: {COLORS['text_secondary']}; font-weight: 500; }}"
            f"QPushButton:hover {{ background: {COLORS['hover']}; color: {COLORS['text']}; }}"
            f"QPushButton:checked {{ background: {alpha(COLORS['primary'], 42)}; color: {COLORS['text']}; "
            f"border-left: 3px solid {COLORS['primary']}; padding-left: 13px; }}"
        )
        self.clicked.connect(lambda: self.clicked_with_key.emit(self.key))


class VigileTable(QTableWidget):
    def __init__(self, columns: list[str], parent: QWidget | None = None):
        super().__init__(0, len(columns), parent)
        self.setHorizontalHeaderLabels([column.upper() for column in columns])
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setShowGrid(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.horizontalHeader().setStretchLastSection(False)
        self.setSortingEnabled(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def empty(self, message: str) -> None:
        self.setRowCount(1)
        self.setSpan(0, 0, 1, self.columnCount())
        item = QTableWidgetItem(message)
        item.setForeground(QColor(COLORS["muted"]))
        self.setItem(0, 0, item)


class KPIValueLabel(QLabel):
    def animate_to(self, value: int) -> None:
        animation = QVariantAnimation(self, duration=1000)
        animation.setStartValue(0)
        animation.setEndValue(value)
        animation.valueChanged.connect(lambda current: self.setText(str(int(current))))
        animation.start()
        self._animation = animation


class DonutChart(QWidget):
    def __init__(self):
        super().__init__()
        self.items: list[tuple[str, int, str]] = []
        self.total = 0
        self.setMinimumHeight(260)

    def set_data(self, items: list[tuple[str, int, str]]) -> None:
        self.items = items
        self.total = sum(value for _, value, _ in items)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.total <= 0:
            painter.setPen(QColor(COLORS["muted"]))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Aucune donnée")
            return
        circle = QRectF(26, 24, 220, 220)
        angle_start = 90 * 16
        for label, value, color in self.items:
            span = -int(360 * 16 * (value / self.total))
            painter.setPen(QPen(QColor(color), 18))
            painter.drawArc(circle, angle_start, span)
            angle_start += span
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(COLORS["card"]))
        painter.drawEllipse(circle.adjusted(42, 42, -42, -42))
        painter.setPen(QColor(COLORS["text"]))
        painter.drawText(circle.adjusted(42, 42, -42, -42), Qt.AlignmentFlag.AlignCenter, f"{self.total}\nunités")
        y = 56
        for label, value, color in self.items:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(color))
            painter.drawEllipse(QRectF(272, y, 10, 10))
            painter.setPen(QColor(COLORS["text"]))
            painter.drawText(QRectF(290, y - 8, 160, 24), 0, f"{label} ({value})")
            y += 28


class PulseIndicator(QWidget):
    def __init__(self, color: str):
        super().__init__()
        self._radius = 8.0
        self.color = QColor(color)
        self.animation = QVariantAnimation(self, duration=1200)
        self.animation.setStartValue(8.0)
        self.animation.setEndValue(14.0)
        self.animation.setLoopCount(-1)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self._set_radius)
        self.setFixedSize(24, 24)

    def _set_radius(self, radius: float) -> None:
        self._radius = radius
        self.update()

    def start(self) -> None:
        self.animation.start()

    def stop(self) -> None:
        self.animation.stop()
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        glow = QColor(self.color)
        glow.setAlpha(70)
        painter.setBrush(glow)
        painter.drawEllipse(QPointF(12, 12), self._radius, self._radius)
        painter.setBrush(self.color)
        painter.drawEllipse(QPointF(12, 12), 5, 5)


class TitleBar(QFrame):
    def __init__(self, window: "VigileWindow"):
        super().__init__(window)
        self.window = window
        self.setObjectName("TitleBar")
        self._drag_position: QPoint | None = None
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)
        brand = QLabel(f"🛡  {APP_NAME}")
        brand.setStyleSheet("font-size: 14px; font-weight: 600;")
        layout.addWidget(brand)
        layout.addStretch(1)
        for label, handler in (("—", self.window.showMinimized), ("▢", self.window.toggle_maximize), ("✕", self.window.close)):
            button = QPushButton(label)
            button.setObjectName("TitleButton")
            button.clicked.connect(handler)
            layout.addWidget(button)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.window.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_position and event.buttons() & Qt.MouseButton.LeftButton:
            self.window.move(event.globalPosition().toPoint() - self._drag_position)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_position = None
        super().mouseReleaseEvent(event)


class SplashScreen(QWidget):
    """Splash d'ouverture : fade-in séquentiel logo → nom → auteur, puis fade-out global."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(f"background-color: {COLORS['bg']};")
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())
        else:
            self.resize(1280, 800)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(18)
        self.logo_label = QLabel("\U0001f6e1")
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setStyleSheet(
            f"font-size: 90px; color: rgba(13,13,20,0); background: transparent;"
        )
        self.name_label = QLabel("V  I  G  I  L  E")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet(
            f"font-size: 44px; font-weight: 600; letter-spacing: 6px; "
            f"color: rgba(13,13,20,0); background: transparent;"
        )
        self.author_label = QLabel("\u00a9 2026 \u2014 Cr\u00e9\u00e9 par Francis NDAYUBAHA")
        self.author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.author_label.setStyleSheet(
            f"font-size: 11px; color: rgba(13,13,20,0); background: transparent;"
        )
        layout.addStretch(1)
        layout.addWidget(self.logo_label)
        layout.addWidget(self.name_label)
        layout.addStretch(1)
        layout.addWidget(self.author_label)
        layout.setContentsMargins(0, 40, 0, 40)
        self._animations: list = []

    def _fade_label(self, label: QLabel, target_color: str, duration: int) -> None:
        """Anime la couleur CSS d'un label de transparent vers target_color."""
        start = QColor(13, 13, 20, 0)
        end = QColor(target_color)
        anim = QVariantAnimation(self, duration=duration)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        current_style = label.styleSheet()

        def _update(color: QColor) -> None:
            css = current_style
            # remplace la valeur color: ... existante
            import re
            css = re.sub(
                r"color:[^;]+;",
                f"color: rgba({color.red()},{color.green()},{color.blue()},{color.alpha()});",
                css,
            )
            label.setStyleSheet(css)

        anim.valueChanged.connect(_update)
        anim.start()
        self._animations.append(anim)

    def run(self, on_finished: Callable) -> None:
        QTimer.singleShot(400,  lambda: self._fade_label(self.logo_label,   COLORS["info"],   800))
        QTimer.singleShot(1400, lambda: self._fade_label(self.name_label,   COLORS["text"],   800))
        QTimer.singleShot(2600, lambda: self._fade_label(self.author_label, COLORS["muted"], 1000))
        fade_out = QPropertyAnimation(self, b"windowOpacity", self)
        fade_out.setDuration(600)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_out_anim = fade_out

        def _start_fadeout():
            fade_out.start()

        def _finish():
            on_finished()
            self.close()

        QTimer.singleShot(4800, _start_fadeout)
        QTimer.singleShot(5400, _finish)


class SplashClosing(QWidget):
    """Splash de fermeture : éléments visibles dès le départ, fade-out séquentiel."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(f"background-color: {COLORS['bg']};")
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())
        else:
            self.resize(1280, 800)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(18)
        self.logo_label = QLabel("\U0001f6e1")
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setStyleSheet(
            f"font-size: 90px; color: {COLORS['info']}; background: transparent;"
        )
        self.name_label = QLabel("V  I  G  I  L  E")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet(
            f"font-size: 44px; font-weight: 600; letter-spacing: 6px; "
            f"color: {COLORS['text']}; background: transparent;"
        )
        self.author_label = QLabel("\u00a9 2026 \u2014 Cr\u00e9\u00e9 par Francis NDAYUBAHA")
        self.author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.author_label.setStyleSheet(
            f"font-size: 11px; color: {COLORS['muted']}; background: transparent;"
        )
        layout.addStretch(1)
        layout.addWidget(self.logo_label)
        layout.addWidget(self.name_label)
        layout.addStretch(1)
        layout.addWidget(self.author_label)
        layout.setContentsMargins(0, 40, 0, 40)
        self._animations: list = []

    def _fade_label(self, label: QLabel, duration: int) -> None:
        """Anime la couleur CSS d'un label vers la couleur de fond (invisible)."""
        import re
        current_style = label.styleSheet()
        match = re.search(r"color:\s*([^;]+);", current_style)
        start_color = QColor(match.group(1).strip()) if match else QColor(COLORS["text"])
        end_color = QColor(13, 13, 20, 0)
        anim = QVariantAnimation(self, duration=duration)
        anim.setStartValue(start_color)
        anim.setEndValue(end_color)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)

        def _update(color: QColor) -> None:
            css = re.sub(
                r"color:[^;]+;",
                f"color: rgba({color.red()},{color.green()},{color.blue()},{color.alpha()});",
                current_style,
            )
            label.setStyleSheet(css)

        anim.valueChanged.connect(_update)
        anim.start()
        self._animations.append(anim)

    def run(self) -> None:
        QTimer.singleShot(400,  lambda: self._fade_label(self.author_label,  800))
        QTimer.singleShot(1400, lambda: self._fade_label(self.name_label,    800))
        QTimer.singleShot(2600, lambda: self._fade_label(self.logo_label,   1000))
        QTimer.singleShot(3600, QApplication.quit)


class LoginFrame(QWidget):
    login_success = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.setSpacing(10)
        self.logo = QLabel("🛡")
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo.setStyleSheet(f"font-size: 52px; color: {COLORS['primary']};")
        center_layout.addWidget(self.logo)
        title = QLabel(APP_NAME)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: 600;")
        center_layout.addWidget(title)
        slogan = QLabel(APP_SLOGAN)
        slogan.setAlignment(Qt.AlignmentFlag.AlignCenter)
        slogan.setStyleSheet(f"color: {COLORS['gold']}; font-style: italic;")
        center_layout.addWidget(slogan)
        self.card = StyledCard()
        self.card.setMaximumWidth(460)
        self.card.setMinimumWidth(300)
        self.card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        card_layout = self.card.layout()
        heading = QLabel("Connexion sécurisée")
        heading.setObjectName("PageTitle")
        caption = QLabel("Administration du parc, traçabilité et tunnel terrain.")
        caption.setObjectName("MutedLabel")
        card_layout.addWidget(heading)
        card_layout.addWidget(caption)
        self.username = VigileInput("Identifiant", "Nom d'utilisateur")
        self.password = VigileInput("Mot de passe", "••••••••", password=True)
        card_layout.addWidget(self.username)
        card_layout.addWidget(self.password)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet(f"color: {COLORS['danger']};")
        card_layout.addWidget(self.error_label)
        self.submit = VigileButton("Se connecter", "primary")
        self.submit.clicked.connect(self.authenticate)
        self.submit.setMinimumHeight(42)
        card_layout.addWidget(self.submit)
        center_layout.addWidget(self.card)
        layout.addWidget(center)
        self.setMinimumWidth(0)
        self.username.input.returnPressed.connect(self.authenticate)
        self.password.input.returnPressed.connect(self.authenticate)
        self._intro()

    def _intro(self) -> None:
        # L'animation reste sobre pour donner un signal premium sans ralentir la saisie.
        animation = QVariantAnimation(self, duration=800)
        animation.setStartValue(0.8)
        animation.setEndValue(1.0)
        animation.valueChanged.connect(lambda value: self.logo.setStyleSheet(f"font-size: {int(52 * value)}px; color: {COLORS['primary']};"))
        animation.start()
        self._animation = animation

    def _shake(self) -> None:
        animation = QPropertyAnimation(self.card, b"pos", self)
        animation.setDuration(280)
        animation.setKeyValueAt(0.0, self.card.pos())
        animation.setKeyValueAt(0.25, self.card.pos() + QPoint(-10, 0))
        animation.setKeyValueAt(0.5, self.card.pos() + QPoint(10, 0))
        animation.setKeyValueAt(0.75, self.card.pos() + QPoint(-6, 0))
        animation.setKeyValueAt(1.0, self.card.pos())
        animation.start()
        self._shake_animation = animation

    @staticmethod
    def _authenticate(username: str, password: str) -> dict:
        session = get_session()
        try:
            user = session.query(User).filter_by(username=username, is_active=True).first()
            if not user or not user.check_password(password):
                raise ValueError("Nom d'utilisateur ou mot de passe incorrect.")
            return {"id": user.id, "username": user.username, "role": user.role, "email": user.email}
        finally:
            session.close()

    def authenticate(self) -> None:
        username = self.username.text()
        password = self.password.text()
        if not username or not password:
            self.error_label.setText("Renseignez vos identifiants.")
            self._shake()
            return
        self.submit.set_loading(True)
        self.error_label.clear()
        self._auth_thread = run_in_thread(self, self._authenticate, self._on_auth_success, self._on_auth_error, username, password)

    def _on_auth_success(self, user_data: dict) -> None:
        self.submit.set_loading(False)
        self.submit.setText("Ouverture...")
        self.login_success.emit(user_data)

    def _on_auth_error(self, message: str) -> None:
        self.submit.set_loading(False)
        self.error_label.setText(message)
        self._shake()


class DashboardFrame(QWidget):
    navigate = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        top = QHBoxLayout()
        titles = QVBoxLayout()
        title = QLabel("Tableau de bord")
        title.setObjectName("PageTitle")
        self.clock_label = QLabel("")
        self.clock_label.setObjectName("MutedLabel")
        titles.addWidget(title)
        titles.addWidget(self.clock_label)
        top.addLayout(titles)
        top.addStretch(1)
        layout.addLayout(top)
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)
        self._update_clock()
        self.kpi_layout = QGridLayout()
        self.kpi_layout.setSpacing(10)
        self.kpis: dict[str, KPIValueLabel] = {}
        specs = [
            ("total", "Total équipements", "◫", COLORS["info"]),
            ("disponible", "Disponibles", "✓", COLORS["secondary"]),
            ("attribue", "En prêt", "👤", COLORS["warning"]),
            ("maintenance", "En maintenance", "⚠", COLORS["danger"]),
        ]
        for index, (key, text, icon, color) in enumerate(specs):
            card = StyledCard(padding=14)
            card_layout = card.layout()
            badge = QLabel(icon)
            badge.setStyleSheet(
                f"background: {alpha(color, 36)}; color: {color}; padding: 8px; border-radius: 10px; font-size: 18px;"
            )
            card_layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignLeft)
            label = QLabel(text)
            label.setObjectName("MutedLabel")
            value = KPIValueLabel("0")
            value.setStyleSheet("font-size: 28px; font-weight: 600;")
            card_layout.addWidget(label)
            card_layout.addWidget(value)
            self.kpis[key] = value
            self.kpi_layout.addWidget(card, index // 2, index % 2)
        layout.addLayout(self.kpi_layout)
        lower = QHBoxLayout()
        lower.setSpacing(18)
        distribution = StyledCard()
        distribution.layout().addWidget(QLabel("Répartition par état"))
        self.chart = DonutChart()
        distribution.layout().addWidget(self.chart)
        lower.addWidget(distribution, 1)
        activity = StyledCard()
        activity.layout().addWidget(QLabel("Dernières attributions"))
        self.activity_table = VigileTable(["Matériel", "Attribué à", "Date"])
        self.activity_table.setMaximumHeight(280)
        activity.layout().addWidget(self.activity_table)
        lower.addWidget(activity, 1)
        layout.addLayout(lower)
        quick = StyledCard()
        quick.layout().addWidget(QLabel("Accès rapide"))
        quick_row = QHBoxLayout()
        for key, label in (("inventory", "Ouvrir inventaire"), ("add", "Ajouter un matériel"), ("server", "Piloter le serveur")):
            button = VigileButton(label, "secondary")
            button.clicked.connect(lambda checked=False, destination=key: self.navigate.emit(destination))
            quick_row.addWidget(button)
        quick.layout().addLayout(quick_row)
        layout.addWidget(quick)
        self.refresh()

    def _update_clock(self) -> None:
        self.clock_label.setText(datetime.now().strftime("%A %d %B %Y · %H:%M:%S"))

    @staticmethod
    def _load() -> dict:
        session = get_session()
        try:
            total = session.query(Materiel).count()
            attribue = session.query(Attribution).filter_by(is_active=True).count()
            maintenance = session.query(Materiel).filter_by(etat="en_panne").count()
            disponible = max(0, total - attribue - maintenance)
            states = [
                (state.replace("_", " ").capitalize(), session.query(Materiel).filter_by(etat=state).count(), STATE_COLORS[state])
                for state in ETATS_MATERIEL
            ]
            activities = []
            recent = session.query(Attribution).join(Materiel).order_by(Attribution.date_attribution.desc()).limit(10).all()
            for attr in recent:
                activities.append(
                    {
                        "materiel": attr.materiel.code_vigile if attr.materiel else "—",
                        "person": attr.attribue_a,
                        "date": attr.date_attribution.strftime("%d/%m/%Y %H:%M"),
                    }
                )
            return {
                "stats": {"total": total, "disponible": disponible, "attribue": attribue, "maintenance": maintenance},
                "states": states,
                "activities": activities,
            }
        finally:
            session.close()

    def refresh(self) -> None:
        run_in_thread(self, self._load, self._bind)

    def _bind(self, payload: dict) -> None:
        for key, label in self.kpis.items():
            label.animate_to(payload["stats"][key])
        self.chart.set_data(payload["states"])
        self.activity_table.setRowCount(0)
        if not payload["activities"]:
            self.activity_table.empty("Aucune attribution récente")
            return
        self.activity_table.setRowCount(len(payload["activities"]))
        for row, activity in enumerate(payload["activities"]):
            self.activity_table.setItem(row, 0, QTableWidgetItem(activity["materiel"]))
            self.activity_table.setItem(row, 1, QTableWidgetItem(activity["person"]))
            self.activity_table.setItem(row, 2, QTableWidgetItem(activity["date"]))


class TunnelRunner(QThread):
    log = pyqtSignal(str)
    url_ready = pyqtSignal(str)
    stopped = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, port: int):
        super().__init__()
        self.port = port
        self.process: subprocess.Popen | None = None
        self._running = True

    def run(self) -> None:
        if not telecharger_cloudflared(lambda message: self.log.emit(message)):
            self.failed.emit("Impossible de préparer cloudflared.")
            return
        command = [_get_cloudflared_path(), "tunnel", "--url", f"http://localhost:{self.port}", "--no-autoupdate"]
        try:
            self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
            for line in self.process.stdout or []:
                if not self._running:
                    break
                text = line.strip()
                if text:
                    self.log.emit(text)
                if "trycloudflare.com" in text:
                    for token in text.split():
                        if token.startswith("https://") and "trycloudflare.com" in token:
                            self.url_ready.emit(token)
                            break
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            if self.process and self.process.poll() is None:
                self.process.terminate()
            self.stopped.emit()

    def stop(self) -> None:
        self._running = False
        if self.process and self.process.poll() is None:
            self.process.terminate()


class ServerFrame(QWidget):
    def __init__(self, flask_app):
        super().__init__()
        self.flask_app = flask_app
        self.flask_thread: threading.Thread | None = None
        self.tunnel_thread: TunnelRunner | None = None
        self.local_url = self._local_url()
        self.public_url = ""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        title = QLabel("Serveur & tunnel")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        cards = QHBoxLayout()
        cards.setSpacing(18)
        self.local_card = StyledCard()
        self.local_indicator = PulseIndicator(COLORS["secondary"])
        local_row = QHBoxLayout()
        local_row.addWidget(self.local_indicator)
        local_row.addWidget(QLabel("Réseau local"))
        local_row.addStretch(1)
        self.local_card.layout().addLayout(local_row)
        self.local_label = QLabel(self.local_url)
        self.local_label.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {COLORS['info']};")
        self.local_status = QLabel("Prêt à démarrer")
        self.local_status.setObjectName("MutedLabel")
        self.local_card.layout().addWidget(self.local_label)
        self.local_card.layout().addWidget(self.local_status)
        cards.addWidget(self.local_card, 1)
        self.tunnel_card = StyledCard()
        self.tunnel_indicator = PulseIndicator(COLORS["primary"])
        tunnel_row = QHBoxLayout()
        tunnel_row.addWidget(self.tunnel_indicator)
        tunnel_row.addWidget(QLabel("Tunnel Internet"))
        tunnel_row.addStretch(1)
        self.tunnel_card.layout().addLayout(tunnel_row)
        self.tunnel_label = QLabel("Tunnel inactif")
        self.tunnel_label.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {COLORS['primary']};")
        self.tunnel_status = QLabel("Tunnel arrêté")
        self.tunnel_status.setObjectName("MutedLabel")
        self.tunnel_card.layout().addWidget(self.tunnel_label)
        self.tunnel_card.layout().addWidget(self.tunnel_status)
        cards.addWidget(self.tunnel_card, 1)
        layout.addLayout(cards)
        actions = QHBoxLayout()
        self.start_server_button = VigileButton("Démarrer serveur", "primary")
        self.start_server_button.clicked.connect(self.start_server)
        self.stop_server_button = VigileButton("Arrêter serveur", "danger")
        self.stop_server_button.clicked.connect(self.stop_server)
        self.stop_server_button.setEnabled(False)
        self.start_tunnel_button = VigileButton("Démarrer tunnel", "secondary")
        self.start_tunnel_button.clicked.connect(self.start_tunnel)
        self.start_tunnel_button.setEnabled(False)
        self.stop_tunnel_button = VigileButton("Arrêter tunnel", "danger")
        self.stop_tunnel_button.clicked.connect(self.stop_tunnel)
        self.stop_tunnel_button.setEnabled(False)
        copy_local = VigileButton("Copier URL locale", "secondary")
        copy_local.clicked.connect(lambda: QApplication.clipboard().setText(self.local_url))
        self.copy_public_button = VigileButton("Copier URL publique", "secondary")
        self.copy_public_button.clicked.connect(lambda: QApplication.clipboard().setText(self.public_url))
        self.copy_public_button.setEnabled(False)
        for widget in (
            self.start_server_button,
            self.stop_server_button,
            self.start_tunnel_button,
            self.stop_tunnel_button,
            copy_local,
            self.copy_public_button,
        ):
            actions.addWidget(widget)
        layout.addLayout(actions)
        lower = QHBoxLayout()
        lower.setSpacing(18)
        qr_card = StyledCard()
        qr_card.layout().addWidget(QLabel("QR Cloudflare"))
        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_card.layout().addWidget(self.qr_label)
        self.qr_hint = QLabel("QR disponible après activation du tunnel")
        self.qr_hint.setObjectName("MutedLabel")
        self.qr_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_card.layout().addWidget(self.qr_hint)
        self._refresh_qr(None)
        lower.addWidget(qr_card, 1)
        layout.addLayout(lower)

    def _local_url(self) -> str:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            sock.close()
        except Exception:
            ip = "127.0.0.1"
        return f"http://{ip}:{FLASK_PORT}"

    def _refresh_qr(self, url: str | None) -> None:
        # Le QR du serveur ne s'affiche que pour l'URL Cloudflare publique.
        if not url:
            self.qr_label.clear()
            self.qr_hint.setText("QR disponible après activation du tunnel")
            self.qr_hint.show()
            return
        try:
            path = generer_qr_code("VIG-SERVER", url=url)
            pixmap = QPixmap(path).scaled(220, 220, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.qr_label.setPixmap(pixmap)
            self.qr_hint.hide()
        except Exception:
            self.qr_label.setText("QR indisponible")
            self.qr_hint.hide()

    def append_log(self, message: str) -> None:
        pass

    def start_server(self) -> None:
        if self.flask_thread and self.flask_thread.is_alive():
            self.append_log("Serveur Flask déjà actif.")
            return

        def run_server():
            self.flask_app.run(host="0.0.0.0", port=FLASK_PORT, debug=False, use_reloader=False)

        self.flask_thread = threading.Thread(target=run_server, daemon=True, name="vigile-flask")
        self.flask_thread.start()
        self.local_indicator.start()
        self.local_status.setText("Serveur actif")
        self.start_server_button.setEnabled(False)
        self.stop_server_button.setEnabled(True)
        self.start_tunnel_button.setEnabled(True)
        self.append_log(f"Serveur démarré sur {self.local_url}")

    def stop_server(self) -> None:
        if not self.flask_thread or not self.flask_thread.is_alive():
            self.local_status.setText("Serveur arrêté")
            self.start_server_button.setEnabled(True)
            self.stop_server_button.setEnabled(False)
            self.start_tunnel_button.setEnabled(False)
            return
        try:
            request = urllib.request.Request(
                f"http://127.0.0.1:{FLASK_PORT}/__shutdown__",
                method="POST",
            )
            urllib.request.urlopen(request, timeout=3)
        except Exception:
            pass
        self.local_indicator.stop()
        self.local_status.setText("Serveur arrêté")
        self.start_server_button.setEnabled(True)
        self.stop_server_button.setEnabled(False)
        self.start_tunnel_button.setEnabled(False)
        self.stop_tunnel_button.setEnabled(False)
        self.copy_public_button.setEnabled(False)
        self.public_url = ""
        self.tunnel_label.setText("Tunnel inactif")
        self._refresh_qr(None)

    def start_tunnel(self) -> None:
        if self.tunnel_thread and self.tunnel_thread.isRunning():
            self.append_log("Tunnel déjà actif.")
            return
        if not self.flask_thread or not self.flask_thread.is_alive():
            self.tunnel_status.setText("Démarrez d'abord le serveur local")
            return
        self.tunnel_thread = TunnelRunner(FLASK_PORT)
        self.tunnel_thread.log.connect(self.append_log)
        self.tunnel_thread.url_ready.connect(self._on_tunnel_url)
        self.tunnel_thread.failed.connect(lambda message: self.append_log(f"Erreur: {message}"))
        self.tunnel_thread.stopped.connect(self._on_tunnel_stopped)
        self.tunnel_thread.start()
        self.tunnel_indicator.start()
        self.tunnel_status.setText("Initialisation du tunnel…")
        self.start_tunnel_button.setEnabled(False)
        self.stop_tunnel_button.setEnabled(True)

    def stop_tunnel(self) -> None:
        if not self.tunnel_thread:
            return
        self.tunnel_thread.stop()
        self.tunnel_indicator.stop()
        self.tunnel_status.setText("Tunnel arrêté")
        self.start_tunnel_button.setEnabled(True)
        self.stop_tunnel_button.setEnabled(False)
        self.copy_public_button.setEnabled(False)
        self.public_url = ""
        self.tunnel_label.setText("Tunnel inactif")
        self._refresh_qr(None)

    def _on_tunnel_url(self, url: str) -> None:
        self.public_url = url
        self.tunnel_label.setText(url)
        self.tunnel_status.setText("Tunnel opérationnel")
        self._refresh_qr(url)
        self.stop_tunnel_button.setEnabled(True)
        self.start_tunnel_button.setEnabled(False)
        self.copy_public_button.setEnabled(True)

    def _on_tunnel_stopped(self) -> None:
        self.tunnel_indicator.stop()
        self.tunnel_status.setText("Tunnel arrêté")
        self.start_tunnel_button.setEnabled(True)
        self.stop_tunnel_button.setEnabled(False)
        self.copy_public_button.setEnabled(False)
        self.public_url = ""
        self.tunnel_label.setText("Tunnel inactif")
        self._refresh_qr(None)


class Sidebar(QFrame):
    page_requested = pyqtSignal(str)
    logout_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("Sidebar")
        self.setFixedWidth(220)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(8)
        self.logo = QLabel("🛡")
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo.setStyleSheet(f"font-size: 26px; color: {COLORS['primary']};")
        layout.addWidget(self.logo)
        brand = QLabel(APP_NAME)
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand.setStyleSheet("font-size: 15px; font-weight: 600;")
        layout.addWidget(brand)
        animation = QVariantAnimation(self, duration=900)
        animation.setStartValue(70)
        animation.setEndValue(255)
        animation.setLoopCount(-1)
        animation.valueChanged.connect(
            lambda value: self.logo.setStyleSheet(f"font-size: 26px; color: rgba(124,107,255,{int(value)});")
        )
        animation.start()
        self._logo_animation = animation
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(f"background: {COLORS['border']}; max-height: 1px;")
        layout.addWidget(divider)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: dict[str, SidebarButton] = {}
        for key, label, icon in (
            ("dashboard", "Dashboard", "◫"),
            ("inventory", "Inventaire", "▤"),
            ("add", "Nouveau matériel", "＋"),
            ("history", "Historique", "⟲"),
            ("users", "Utilisateurs", "◎"),
            ("server", "Serveur", "☁"),
        ):
            button = SidebarButton(key, label, icon)
            button.clicked_with_key.connect(self.page_requested.emit)
            self.group.addButton(button)
            layout.addWidget(button)
            self.buttons[key] = button
        layout.addStretch(1)
        self.user_card = StyledCard(padding=14)
        top = QHBoxLayout()
        self.avatar = QLabel("VG")
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar.setFixedSize(44, 44)
        self.avatar.setStyleSheet(
            f"background: {alpha(COLORS['primary'], 50)}; color: {COLORS['text']}; border-radius: 22px; font-weight: 600;"
        )
        top.addWidget(self.avatar)
        identity = QVBoxLayout()
        self.username = QLabel("Utilisateur")
        self.role = QLabel("—")
        self.role.setObjectName("MutedLabel")
        identity.addWidget(self.username)
        identity.addWidget(self.role)
        top.addLayout(identity)
        self.user_card.layout().addLayout(top)
        logout = VigileButton("Déconnexion", "secondary")
        logout.clicked.connect(self.logout_requested.emit)
        self.user_card.layout().addWidget(logout)
        layout.addWidget(self.user_card)

    def set_user(self, user: dict) -> None:
        initials = "".join(part[0].upper() for part in user["username"].split()[:2]) or user["username"][:2].upper()
        self.avatar.setText(initials)
        self.username.setText(user["username"])
        self.role.setText(user["role"].capitalize())

    def set_admin_visibility(self, visible: bool) -> None:
        self.buttons["users"].setVisible(visible)

    def set_active(self, key: str) -> None:
        if key in self.buttons:
            self.buttons[key].setChecked(True)


class VigileWindow(QMainWindow):
    def __init__(self, flask_app, tk_root=None):
        super().__init__()
        self.flask_app = flask_app
        self.tk_root = tk_root
        self.current_user: dict | None = None
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(1280, 800)
        self.setMinimumSize(960, 620)
        outer = QWidget()
        outer.setObjectName("WindowRoot")
        self.setCentralWidget(outer)
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(18, 18, 18, 18)
        self.shell = QFrame()
        self.shell.setObjectName("AppShell")
        apply_shadow(self.shell, blur=42, y_offset=18, alpha_value=120)
        shell_layout = QVBoxLayout(self.shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        self.title_bar = TitleBar(self)
        shell_layout.addWidget(self.title_bar)
        self.body = QHBoxLayout()
        self.body.setContentsMargins(12, 12, 12, 12)
        self.body.setSpacing(12)
        shell_layout.addLayout(self.body)
        outer_layout.addWidget(self.shell)
        self._closing = False
        self.splash = SplashScreen()
        self.splash.show()
        self.splash.run(on_finished=self._show_login)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect().adjusted(8, 8, -8, -8)), 18, 18)
        painter.fillPath(path, QColor(0, 0, 0, 1))

    def toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _show_login(self) -> None:
        clear_layout(self.body)
        self.login = LoginFrame()
        self.login.login_success.connect(self._on_login_success)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self.login)
        self.body.addWidget(scroll)

    def _on_login_success(self, user_data: dict) -> None:
        self.current_user = user_data
        self._build_shell()

    def _build_shell(self) -> None:
        clear_layout(self.body)
        self.sidebar = Sidebar()
        self.sidebar.set_user(self.current_user)
        self.sidebar.set_admin_visibility(self.current_user["role"] == "admin")
        self.sidebar.page_requested.connect(self.show_page)
        self.sidebar.logout_requested.connect(self.logout)
        self.body.addWidget(self.sidebar)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        right_layout.addWidget(self.stack)
        self.body.addWidget(right, 1)
        self.page_factories = {
            "dashboard": lambda: DashboardFrame(),
            "inventory": lambda: __import__("desktop.inventory_view", fromlist=["InventoryFrame"]).InventoryFrame(self.current_user),
            "add": lambda: __import__("desktop.add_material", fromlist=["AddMaterialFrame"]).AddMaterialFrame(self.current_user),
            "history": lambda: __import__("desktop.history_view", fromlist=["HistoryFrame"]).HistoryFrame(),
            "users": lambda: __import__("desktop.user_manager", fromlist=["UserManagerFrame"]).UserManagerFrame(),
            "server": lambda: ServerFrame(self.flask_app),
        }
        self.page_order = list(self.page_factories.keys())
        self.pages: dict[str, QWidget] = {}
        self.page_containers: dict[str, QScrollArea] = {}
        for _ in self.page_order:
            placeholder = QScrollArea()
            placeholder.setWidgetResizable(True)
            placeholder.setFrameShape(QFrame.Shape.NoFrame)
            placeholder.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            placeholder.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            placeholder.setWidget(QWidget())
            self.stack.addWidget(placeholder)
        self._ensure_page("dashboard")
        self.show_page("dashboard")

    def _ensure_page(self, key: str) -> None:
        if key in self.pages:
            return
        page = self.page_factories[key]()
        if key == "dashboard":
            page.navigate.connect(self.show_page)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        surface = QWidget()
        surface_layout = QVBoxLayout(surface)
        surface_layout.setContentsMargins(14, 14, 14, 14)
        surface_layout.addWidget(page)
        surface_layout.addStretch(1)
        scroll.setWidget(surface)
        index = self.page_order.index(key)
        old = self.stack.widget(index)
        self.stack.removeWidget(old)
        old.deleteLater()
        self.stack.insertWidget(index, scroll)
        self.pages[key] = page
        self.page_containers[key] = scroll

    def show_page(self, key: str) -> None:
        if key not in self.page_factories:
            return
        self._ensure_page(key)
        self.stack.setCurrentIndex(self.page_order.index(key))
        self.sidebar.set_active(key)
        page = self.pages[key]
        if hasattr(page, "refresh"):
            page.refresh()

    def logout(self) -> None:
        self.current_user = None
        self._show_login()

    def _stop_threads(self) -> None:
        for thread in list(getattr(self, "_worker_threads", set())):
            thread.quit()
            thread.wait(1500)
        if hasattr(self, "pages"):
            for page in self.pages.values():
                for thread in list(getattr(page, "_worker_threads", set())):
                    thread.quit()
                    thread.wait(1500)

    def _show_closing_splash(self) -> None:
        if self._closing:
            return
        self._closing = True
        self._stop_threads()
        self.shell.hide()
        self._splash_closing = SplashClosing()
        self._splash_closing.show()
        self._splash_closing.run()
        if self.tk_root is not None:
            self.tk_root.after(3700, self.tk_root.destroy)

    def closeEvent(self, event) -> None:
        if self._closing:
            # Fermeture déjà initiée via le splash — on laisse Qt terminer.
            event.accept()
            return
        event.ignore()
        self._show_closing_splash()


class MainWindow:
    """Pont Tkinter -> PyQt6 pour garder app.py inchangé."""

    def __init__(self, root, flask_app):
        self.root = root
        self.root.withdraw()
        self.qt_app = QApplication.instance() or QApplication(sys.argv)
        load_theme(self.qt_app)
        self.window = VigileWindow(flask_app=flask_app, tk_root=root)
        self.window.show()
        self._alive = True
        self._pump()

    def _pump(self) -> None:
        # app.py reste maître du cycle de vie, donc on pompe explicitement l'event loop Qt.
        if not self._alive:
            return
        self.qt_app.processEvents()
        self.root.after(16, self._pump)

    def _afficher_splash_fermeture(self) -> None:
        self._alive = False
        self.window._show_closing_splash()
