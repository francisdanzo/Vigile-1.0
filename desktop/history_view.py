from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QLineEdit, QTableWidgetItem, QVBoxLayout, QWidget

from database import get_session
from desktop.main_window import StyledCard, VigileButton, VigileTable, run_in_thread
from models import Attribution, Materiel


class HistoryFrame(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(18)
        title = QLabel("Historique des attributions")
        title.setObjectName("PageTitle")
        root.addWidget(title)
        filter_card = StyledCard()
        filters = QHBoxLayout()
        self.person = QLineEdit()
        self.person.setPlaceholderText("Personne")
        self.code = QLineEdit()
        self.code.setPlaceholderText("Code VIGILE")
        self.status = QComboBox()
        self.status.addItems(["Toutes", "Actives", "Terminées"])
        refresh = VigileButton("Actualiser", "secondary")
        refresh.clicked.connect(self.refresh)
        for widget in (self.person, self.code, self.status, refresh):
            filters.addWidget(widget)
        filter_card.layout().addLayout(filters)
        root.addWidget(filter_card)
        table_card = StyledCard()
        self.table = VigileTable(["Statut", "Code", "Type", "Attribué à", "Attribution", "Retour", "Notes"])
        table_card.layout().addWidget(self.table)
        root.addWidget(table_card)
        self._refreshing = False
        self._auto_timer = QTimer(self)
        self._auto_timer.setInterval(500)
        self._auto_timer.timeout.connect(self.refresh)
        self.person.textChanged.connect(self.refresh)
        self.code.textChanged.connect(self.refresh)
        self.status.currentTextChanged.connect(self.refresh)
        self.refresh()

    @staticmethod
    def _fetch(person: str, code: str, status: str) -> list[dict]:
        session = get_session()
        try:
            query = session.query(Attribution).join(Materiel)
            if person:
                query = query.filter(Attribution.attribue_a.ilike(f"%{person}%"))
            if code:
                query = query.filter(Materiel.code_vigile.ilike(f"%{code}%"))
            if status == "Actives":
                query = query.filter(Attribution.is_active.is_(True))
            elif status == "Terminées":
                query = query.filter(Attribution.is_active.is_(False))
            payload = []
            for attribution in query.order_by(Attribution.date_attribution.desc()).all():
                payload.append(
                    {
                        "statut": "En cours" if attribution.is_active else "Terminé",
                        "code": attribution.materiel.code_vigile if attribution.materiel else "—",
                        "type": attribution.materiel.type if attribution.materiel else "—",
                        "attribue_a": attribution.attribue_a,
                        "attribution": attribution.date_attribution.strftime("%d/%m/%Y %H:%M"),
                        "retour": attribution.date_retour.strftime("%d/%m/%Y %H:%M") if attribution.date_retour else "—",
                        "notes": attribution.notes or "—",
                    }
                )
            return payload
        finally:
            session.close()

    def refresh(self) -> None:
        if self._refreshing:
            return
        self._refreshing = True
        run_in_thread(self, self._fetch, self._bind, None, self.person.text().strip(), self.code.text().strip(), self.status.currentText())

    def showEvent(self, event) -> None:
        self._auto_timer.start()
        super().showEvent(event)

    def hideEvent(self, event) -> None:
        self._auto_timer.stop()
        super().hideEvent(event)

    def _bind(self, rows: list[dict]) -> None:
        self.table.setSortingEnabled(False)
        self._refreshing = False
        self.table.setRowCount(0)
        if not rows:
            self.table.empty("Aucun historique trouvé")
            self.table.setSortingEnabled(True)
            return
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            self.table.setItem(row_index, 0, QTableWidgetItem(row["statut"]))
            self.table.setItem(row_index, 1, QTableWidgetItem(row["code"]))
            self.table.setItem(row_index, 2, QTableWidgetItem(row["type"]))
            self.table.setItem(row_index, 3, QTableWidgetItem(row["attribue_a"]))
            self.table.setItem(row_index, 4, QTableWidgetItem(row["attribution"]))
            self.table.setItem(row_index, 5, QTableWidgetItem(row["retour"]))
            self.table.setItem(row_index, 6, QTableWidgetItem(row["notes"]))
        self.table.setSortingEnabled(True)
