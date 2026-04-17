from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config import ROLES_UTILISATEUR
from database import get_session
from desktop.main_window import StyledCard, VigileButton, VigileTable, run_in_thread
from models import User


class UserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nouvel utilisateur")
        layout = QFormLayout(self)
        self.username = QLineEdit()
        self.email = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.role = QComboBox()
        self.role.addItems(ROLES_UTILISATEUR)
        layout.addRow("Identifiant", self.username)
        layout.addRow("Email", self.email)
        layout.addRow("Mot de passe", self.password)
        layout.addRow("Rôle", self.role)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


class UserManagerFrame(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(18)
        header = QHBoxLayout()
        title = QLabel("Gestion des utilisateurs")
        title.setObjectName("PageTitle")
        header.addWidget(title)
        header.addStretch(1)
        create = VigileButton("Nouvel utilisateur", "primary")
        create.clicked.connect(self.create_user)
        header.addWidget(create)
        root.addLayout(header)
        card = StyledCard()
        self.table = VigileTable(["ID", "Username", "Email", "Rôle", "Statut", "Créé le"])
        card.layout().addWidget(self.table)
        root.addWidget(card)
        actions = QHBoxLayout()
        for label, callback in (
            ("Activer", lambda: self.toggle_user(True)),
            ("Désactiver", lambda: self.toggle_user(False)),
            ("Réinitialiser MDP", self.reset_password),
        ):
            button = VigileButton(label, "secondary")
            button.clicked.connect(callback)
            actions.addWidget(button)
        actions.addStretch(1)
        root.addLayout(actions)
        self.refresh()

    @staticmethod
    def _fetch() -> list[dict]:
        session = get_session()
        try:
            return [
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "status": "Actif" if user.is_active else "Inactif",
                    "created_at": user.created_at.strftime("%d/%m/%Y %H:%M"),
                }
                for user in session.query(User).order_by(User.id).all()
            ]
        finally:
            session.close()

    def refresh(self) -> None:
        run_in_thread(self, self._fetch, self._bind)

    def _bind(self, rows: list[dict]) -> None:
        self.table.setRowCount(0)
        if not rows:
            self.table.empty("Aucun utilisateur")
            return
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for col, key in enumerate(("id", "username", "email", "role", "status", "created_at")):
                self.table.setItem(row_index, col, QTableWidgetItem(str(row[key])))

    def selected_user_id(self) -> int | None:
        selection = self.table.selectionModel().selectedRows()
        if not selection:
            QMessageBox.information(self, "Sélection", "Sélectionnez un utilisateur.")
            return None
        return int(self.table.item(selection[0].row(), 0).text())

    def create_user(self) -> None:
        dialog = UserDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        username = dialog.username.text().strip()
        email = dialog.email.text().strip()
        password = dialog.password.text()
        role = dialog.role.currentText()
        if not username or not email or not password:
            QMessageBox.warning(self, "Validation", "Tous les champs sont obligatoires.")
            return
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            QMessageBox.warning(self, "Validation", "Email invalide.")
            return
        session = get_session()
        try:
            if session.query(User).filter((User.username == username) | (User.email == email)).first():
                QMessageBox.warning(self, "Doublon", "Un utilisateur avec ce nom ou cet email existe déjà.")
                return
            user = User(username=username, email=email, role=role, is_active=True)
            user.set_password(password)
            session.add(user)
            session.commit()
        finally:
            session.close()
        self.refresh()

    def toggle_user(self, active: bool) -> None:
        user_id = self.selected_user_id()
        if user_id is None:
            return
        session = get_session()
        try:
            user = session.get(User, user_id)
            if user:
                user.is_active = active
                session.commit()
        finally:
            session.close()
        self.refresh()

    def reset_password(self) -> None:
        user_id = self.selected_user_id()
        if user_id is None:
            return
        password, ok = QInputDialog.getText(self, "Réinitialiser le mot de passe", "Nouveau mot de passe")
        if not ok or len(password) < 4:
            return
        session = get_session()
        try:
            user = session.get(User, user_id)
            if user:
                user.set_password(password)
                session.commit()
        finally:
            session.close()
