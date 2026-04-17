from __future__ import annotations

import os
import re
import socket
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtCore import QDate, Qt, QVariantAnimation
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QComboBox, QDateEdit, QFormLayout, QHBoxLayout, QLabel, QMessageBox, QTextEdit, QVBoxLayout, QWidget

from config import EMPLACEMENTS_MATERIEL, ETATS_MATERIEL, TYPES_MATERIEL
from database import get_session
from desktop.main_window import COLORS, StatusBadge, StyledCard, VigileButton, VigileInput, run_in_thread
from models import Materiel
from qr.generator import generer_code_vigile, generer_qr_code


class StepBadge(QLabel):
    def __init__(self, index: int, title: str):
        super().__init__(f"{index}. {title}")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(36)
        self.set_active(False)

    def set_active(self, active: bool) -> None:
        self.setStyleSheet(
            f"QLabel {{ background-color: {'rgba(124,107,255,0.18)' if active else COLORS['input']}; "
            f"color: {COLORS['text'] if active else COLORS['text_secondary']}; "
            f"border: 1px solid {COLORS['primary'] if active else COLORS['border']}; border-radius: 18px; font-weight: bold; }}"
        )


class AddMaterialFrame(QWidget):
    def __init__(self, current_user: dict):
        super().__init__()
        self.current_user = current_user
        self.last_qr_path = ""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(18)
        title = QLabel("Nouveau matériel")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Parcours guidé en trois étapes avec prévisualisation du code VIGILE.")
        subtitle.setObjectName("MutedLabel")
        root.addWidget(title)
        root.addWidget(subtitle)
        steps = QHBoxLayout()
        self.step_widgets = [StepBadge(1, "Identification"), StepBadge(2, "État / Lieu"), StepBadge(3, "Confirmation")]
        for index, widget in enumerate(self.step_widgets):
            widget.set_active(index == 0)
            steps.addWidget(widget)
        root.addLayout(steps)
        body = QHBoxLayout()
        body.setSpacing(18)
        form_card = StyledCard()
        form_layout = form_card.layout()
        self.code_label = QLabel("VIG-—")
        self.code_label.setStyleSheet(f"font-size: 20px; font-weight: 600; color: {COLORS['primary']};")
        form_layout.addWidget(self.code_label)
        form = QFormLayout()
        form.setSpacing(14)
        self.type_combo = QComboBox()
        self.type_combo.addItems(TYPES_MATERIEL)
        self.marque = VigileInput("Marque", "Dell, Lenovo, HP…")
        self.modele = VigileInput("Modèle", "Latitude 5540")
        self.numero_serie = VigileInput("Numéro de série", "SN-ABC123")
        self.etat_combo = QComboBox()
        self.etat_combo.addItems(ETATS_MATERIEL)
        self.emplacement_combo = QComboBox()
        self.emplacement_combo.addItems(EMPLACEMENTS_MATERIEL)
        self.date_acq = QDateEdit()
        self.date_acq.setCalendarPopup(True)
        self.date_acq.setDate(QDate.currentDate())
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Commentaire utile pour le support ou la logistique.")
        form.addRow("Type", self.type_combo)
        form.addRow("Marque", self.marque)
        form.addRow("Modèle", self.modele)
        form.addRow("Numéro de série", self.numero_serie)
        form.addRow("État", self.etat_combo)
        form.addRow("Emplacement", self.emplacement_combo)
        form.addRow("Acquisition", self.date_acq)
        form.addRow("Notes", self.notes)
        form_layout.addLayout(form)
        actions = QHBoxLayout()
        self.save_button = VigileButton("Enregistrer", "primary")
        reset_button = VigileButton("Réinitialiser", "secondary")
        self.save_button.clicked.connect(self.save_material)
        reset_button.clicked.connect(self.reset_form)
        actions.addWidget(self.save_button)
        actions.addWidget(reset_button)
        form_layout.addLayout(actions)
        preview_card = StyledCard()
        preview_layout = preview_card.layout()
        preview_layout.addWidget(QLabel("Aperçu"))
        self.status_badge = StatusBadge("neuf")
        preview_layout.addWidget(self.status_badge)
        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        self.summary.setObjectName("MutedLabel")
        preview_layout.addWidget(self.summary)
        self.qr_label = QLabel("QR en attente")
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setMinimumSize(280, 280)
        self.qr_label.setStyleSheet(f"border: 1px dashed {COLORS['border']}; border-radius: 14px;")
        preview_layout.addWidget(self.qr_label)
        body.addWidget(form_card, 3)
        body.addWidget(preview_card, 2)
        root.addLayout(body)
        self.type_combo.currentTextChanged.connect(self.update_preview)
        self.etat_combo.currentTextChanged.connect(self.update_preview)
        self.emplacement_combo.currentTextChanged.connect(self.update_preview)
        self.numero_serie.input.textChanged.connect(self.update_preview)
        self.notes.textChanged.connect(self.update_preview)
        self.update_preview()

    def next_code(self) -> str:
        session = get_session()
        try:
            return generer_code_vigile(session)
        finally:
            session.close()

    def update_preview(self) -> None:
        # Le code VIGILE est prévisualisé en continu pour rassurer l'utilisateur avant la sauvegarde.
        self.code_label.setText(self.next_code())
        self.summary.setText(
            f"{self.type_combo.currentText().capitalize()} prêt à être enregistré à "
            f"{self.emplacement_combo.currentText().replace('_', ' ')} avec le code {self.code_label.text()}."
        )
        self.step_widgets[0].set_active(bool(self.type_combo.currentText()))
        self.step_widgets[1].set_active(bool(self.etat_combo.currentText() and self.emplacement_combo.currentText()))
        self.step_widgets[2].set_active(bool(self.numero_serie.text() or self.notes.toPlainText().strip()))
        state = self.etat_combo.currentText()
        layout = self.status_badge.parentWidget().layout()
        layout.removeWidget(self.status_badge)
        self.status_badge.deleteLater()
        self.status_badge = StatusBadge(state)
        layout.insertWidget(1, self.status_badge)

    def _save_impl(self) -> tuple[str, str]:
        session = get_session()
        try:
            code_vigile = generer_code_vigile(session)
            acquisition = datetime.combine(self.date_acq.date().toPyDate(), datetime.min.time()).replace(tzinfo=timezone.utc)
            materiel = Materiel(
                code_vigile=code_vigile,
                type=self.type_combo.currentText(),
                marque=self.marque.text() or None,
                modele=self.modele.text() or None,
                numero_serie=self.numero_serie.text() or None,
                etat=self.etat_combo.currentText(),
                emplacement=self.emplacement_combo.currentText(),
                date_acquisition=acquisition,
                notes=self.notes.toPlainText().strip() or None,
                created_by=self.current_user["id"],
            )
            session.add(materiel)
            session.flush()
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.connect(("8.8.8.8", 80))
                host = sock.getsockname()[0]
                sock.close()
            except Exception:
                host = "127.0.0.1"
            qr_path = generer_qr_code(code_vigile, host=host)
            materiel.qr_code_path = qr_path
            session.commit()
            return code_vigile, qr_path
        finally:
            session.close()

    def save_material(self) -> None:
        if self.numero_serie.text() and not re.match(r"^[A-Za-z0-9._/-]{4,}$", self.numero_serie.text()):
            QMessageBox.warning(self, "Validation", "Le numéro de série semble invalide.")
            return
        self.save_button.set_loading(True)
        run_in_thread(self, self._save_impl, self._on_saved, self._on_error)

    def _on_saved(self, result: tuple[str, str]) -> None:
        self.save_button.set_loading(False)
        code, qr_path = result
        self.last_qr_path = qr_path
        self.code_label.setText(code)
        pixmap = QPixmap(qr_path).scaled(280, 280, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.qr_label.setPixmap(pixmap)
        animation = QVariantAnimation(self, duration=500)
        animation.setStartValue(0.3)
        animation.setEndValue(1.0)
        animation.valueChanged.connect(lambda value: self.qr_label.setWindowOpacity(float(value)))
        animation.start()
        self._fade = animation
        QMessageBox.information(self, "Succès", f"Matériel {code} enregistré avec succès.")
        self.update_preview()

    def _on_error(self, message: str) -> None:
        self.save_button.set_loading(False)
        QMessageBox.critical(self, "Erreur", message)

    def reset_form(self) -> None:
        self.type_combo.setCurrentIndex(0)
        self.marque.setText("")
        self.modele.setText("")
        self.numero_serie.setText("")
        self.etat_combo.setCurrentIndex(0)
        self.emplacement_combo.setCurrentIndex(0)
        self.date_acq.setDate(QDate.currentDate())
        self.notes.clear()
        self.qr_label.clear()
        self.qr_label.setText("QR en attente")
        self.update_preview()
