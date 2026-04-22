from __future__ import annotations

import csv
import os
import sys
from functools import partial

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QLineEdit, QTableWidgetItem, QVBoxLayout, QWidget, QInputDialog

from config import EMPLACEMENTS_MATERIEL, ETATS_MATERIEL, TYPES_MATERIEL
from database import get_session
from desktop.main_window import StatusBadge, StyledCard, VigileButton, VigileTable, run_in_thread
from models import Attribution, Materiel


class CounterChip(VigileButton):
    def __init__(self, label: str):
        super().__init__(label, "secondary")
        self.base_label = label

    def set_count(self, count: int) -> None:
        self.setText(f"{self.base_label} ({count})")


class InventoryFrame(QWidget):
    def __init__(self, current_user: dict):
        super().__init__()
        self.current_user = current_user
        self.rows: list[dict] = []
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(300)
        self.search_timer.timeout.connect(self.refresh)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(18)
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Inventaire")
        title.setObjectName("PageTitle")
        self.subtitle = QLabel("0 équipement")
        self.subtitle.setObjectName("MutedLabel")
        title_box.addWidget(title)
        title_box.addWidget(self.subtitle)
        header.addLayout(title_box)
        header.addStretch(1)
        export = VigileButton("Exporter CSV", "secondary")
        export.clicked.connect(self.export_csv)
        header.addWidget(export)
        root.addLayout(header)
        filters = StyledCard()
        filters_layout = filters.layout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Recherche par code, marque, modèle, numéro de série")
        self.search.textChanged.connect(lambda: self.search_timer.start())
        filters_layout.addWidget(self.search)
        row = QHBoxLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Tous"] + TYPES_MATERIEL)
        self.etat_combo = QComboBox()
        self.etat_combo.addItems(["Tous"] + ETATS_MATERIEL)
        self.emplacement_combo = QComboBox()
        self.emplacement_combo.addItems(["Tous"] + EMPLACEMENTS_MATERIEL)
        for combo in (self.type_combo, self.etat_combo, self.emplacement_combo):
            combo.currentTextChanged.connect(self.refresh)
            row.addWidget(combo)
        filters_layout.addLayout(row)
        chips = QHBoxLayout()
        self.type_chip = CounterChip("Types")
        self.etat_chip = CounterChip("États")
        self.empl_chip = CounterChip("Lieux")
        for chip in (self.type_chip, self.etat_chip, self.empl_chip):
            chips.addWidget(chip)
        chips.addStretch(1)
        filters_layout.addLayout(chips)
        root.addWidget(filters)
        table_card = StyledCard()
        self.table = VigileTable(["Code", "Type", "Marque / Modèle", "État", "Emplacement", "Attribué à", "Actions"])
        self.table.setColumnWidth(0, 140)
        self.table.setColumnWidth(1, 90)
        self.table.setColumnWidth(2, 180)
        self.table.setColumnWidth(3, 80)
        self.table.setColumnWidth(4, 90)
        self.table.setColumnWidth(5, 110)
        self.table.setColumnWidth(6, 290)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        table_card.layout().addWidget(self.table)
        root.addWidget(table_card, 1)
        self.refresh()

    @staticmethod
    def _fetch(search: str, type_filter: str, etat_filter: str, emplacement_filter: str) -> list[dict]:
        session = get_session()
        try:
            query = session.query(Materiel)
            if type_filter != "Tous":
                query = query.filter(Materiel.type == type_filter)
            if etat_filter != "Tous":
                query = query.filter(Materiel.etat == etat_filter)
            if emplacement_filter != "Tous":
                query = query.filter(Materiel.emplacement == emplacement_filter)
            if search:
                query = query.filter(
                    (Materiel.code_vigile.ilike(f"%{search}%"))
                    | (Materiel.marque.ilike(f"%{search}%"))
                    | (Materiel.modele.ilike(f"%{search}%"))
                    | (Materiel.numero_serie.ilike(f"%{search}%"))
                )
            payload = []
            for materiel in query.order_by(Materiel.created_at.desc()).all():
                attribution = session.query(Attribution).filter_by(materiel_id=materiel.id, is_active=True).first()
                payload.append(
                    {
                        "id": materiel.id,
                        "code": materiel.code_vigile,
                        "type": materiel.type,
                        "details": f"{materiel.marque or '—'} / {materiel.modele or '—'}",
                        "etat": materiel.etat,
                        "emplacement": materiel.emplacement,
                        "attribue": attribution.attribue_a if attribution else "—",
                    }
                )
            return payload
        finally:
            session.close()

    def refresh(self) -> None:
        run_in_thread(
            self,
            self._fetch,
            self._bind,
            None,
            self.search.text().strip(),
            self.type_combo.currentText(),
            self.etat_combo.currentText(),
            self.emplacement_combo.currentText(),
        )

    def _bind(self, rows: list[dict]) -> None:
        # Les actions restent dans chaque ligne pour limiter les allers-retours cognitifs.
        self.rows = rows
        self.subtitle.setText(f"{len(rows)} équipement(s)")
        self.type_chip.set_count(len({row['type'] for row in rows}))
        self.etat_chip.set_count(len({row['etat'] for row in rows}))
        self.empl_chip.set_count(len({row['emplacement'] for row in rows}))
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        if not rows:
            self.table.empty("Aucun matériel trouvé")
            return
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            self.table.setItem(row_index, 0, QTableWidgetItem(row["code"]))
            self.table.setItem(row_index, 1, QTableWidgetItem(row["type"]))
            self.table.setItem(row_index, 2, QTableWidgetItem(row["details"]))
            self.table.setCellWidget(row_index, 3, StatusBadge(row["etat"]))
            self.table.setItem(row_index, 4, QTableWidgetItem(row["emplacement"]))
            self.table.setItem(row_index, 5, QTableWidgetItem(row["attribue"]))
            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(4)
            for label, callback in (
                ("Voir QR", partial(self.show_qr, row["id"])),
                ("Attribuer", partial(self.assign, row["id"])),
                ("Récupérer", partial(self.recover, row["id"])),
            ):
                button = VigileButton(label, "secondary")
                button.setFixedHeight(28)
                button.setStyleSheet(
                    button.styleSheet().replace("padding: 10px 18px", "padding: 4px 10px")
                )
                button.clicked.connect(callback)
                actions_layout.addWidget(button)
            self.table.setCellWidget(row_index, 6, actions)
        self.table.setSortingEnabled(True)

    def show_qr(self, materiel_id: int) -> None:
        session = get_session()
        try:
            materiel = session.get(Materiel, materiel_id)
            if not materiel or not materiel.qr_code_path:
                QMessageBox.information(self, "QR", "QR code indisponible.")
                return
            QMessageBox.information(self, "QR", f"QR disponible ici : {materiel.qr_code_path}")
        finally:
            session.close()

    def assign(self, materiel_id: int) -> None:
        name, ok = QInputDialog.getText(self, "Attribuer le matériel", "Nom de la personne")
        if not ok or not name.strip():
            return
        session = get_session()
        try:
            active = session.query(Attribution).filter_by(materiel_id=materiel_id, is_active=True).first()
            if active:
                QMessageBox.warning(self, "Attribution", f"Déjà attribué à {active.attribue_a}.")
                return
            materiel = session.get(Materiel, materiel_id)
            attribution = Attribution(materiel_id=materiel_id, attribue_a=name.strip(), attribue_par=self.current_user["id"], is_active=True)
            session.add(attribution)
            if materiel:
                materiel.emplacement = "attribué"
            session.commit()
        finally:
            session.close()
        self.refresh()

    def recover(self, materiel_id: int) -> None:
        session = get_session()
        try:
            active = session.query(Attribution).filter_by(materiel_id=materiel_id, is_active=True).first()
            if not active:
                QMessageBox.information(self, "Récupération", "Aucune attribution active.")
                return
            active.retourner()
            materiel = session.get(Materiel, materiel_id)
            if materiel:
                materiel.emplacement = "réserve"
            session.commit()
        finally:
            session.close()
        self.refresh()

    def export_csv(self) -> None:
        if not self.rows:
            QMessageBox.information(self, "Export", "Aucune ligne à exporter.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exporter l'inventaire", "vigile-inventaire.csv", "CSV (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["code", "type", "details", "etat", "emplacement", "attribue"])
            writer.writeheader()
            writer.writerows(self.rows)
        QMessageBox.information(self, "Export", f"Inventaire exporté vers {path}")
