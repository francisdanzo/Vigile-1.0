from __future__ import annotations

import csv
import math
import os
import sys
from functools import partial

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QLineEdit,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QInputDialog,
)

from config import EMPLACEMENTS_MATERIEL, ETATS_MATERIEL, TYPES_MATERIEL
from database import get_session
from desktop.main_window import StatusBadge, StyledCard, VigileButton, VigileTable, run_in_thread, COLORS
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
        self.current_page = 1
        self.per_page = 50
        self.total_items = 0
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(300)
        self.search_timer.timeout.connect(self.refresh)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(18)

        # ── En-tête ──────────────────────────────────────────────────────────
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

        # ── Filtres ───────────────────────────────────────────────────────────
        filters = StyledCard()
        filters_layout = filters.layout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Recherche par code, marque, modèle, numéro de série")
        self.search.textChanged.connect(self._reset_and_refresh)
        filters_layout.addWidget(self.search)
        row = QHBoxLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Tous"] + TYPES_MATERIEL)
        self.etat_combo = QComboBox()
        self.etat_combo.addItems(["Tous"] + ETATS_MATERIEL)
        self.emplacement_combo = QComboBox()
        self.emplacement_combo.addItems(["Tous"] + EMPLACEMENTS_MATERIEL)
        for combo in (self.type_combo, self.etat_combo, self.emplacement_combo):
            combo.currentTextChanged.connect(self._reset_and_refresh)
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

        # ── Table ─────────────────────────────────────────────────────────────
        table_card = StyledCard()
        self.table = VigileTable(["Code", "Type", "Marque / Modèle", "État", "Emplacement", "Attribué à", "Actions"])
        self.table.setColumnWidth(0, 140)
        self.table.setColumnWidth(1, 90)
        self.table.setColumnWidth(2, 180)
        self.table.setColumnWidth(3, 80)
        self.table.setColumnWidth(4, 90)
        self.table.setColumnWidth(5, 110)
        self.table.setColumnWidth(6, 370)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        table_card.layout().addWidget(self.table)

        # ── Pagination ────────────────────────────────────────────────────────
        pag = QHBoxLayout()
        self.btn_prev = VigileButton("‹  Précédent", "secondary")
        self.btn_prev.setFixedHeight(32)
        self.btn_prev.clicked.connect(self._prev_page)
        self.page_label = QLabel("Page 1 / 1")
        self.page_label.setObjectName("MutedLabel")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_next = VigileButton("Suivant  ›", "secondary")
        self.btn_next.setFixedHeight(32)
        self.btn_next.clicked.connect(self._next_page)
        pag.addStretch(1)
        pag.addWidget(self.btn_prev)
        pag.addWidget(self.page_label)
        pag.addWidget(self.btn_next)
        pag.addStretch(1)
        table_card.layout().addLayout(pag)
        root.addWidget(table_card, 1)
        self.refresh()

    # ── Chargement ────────────────────────────────────────────────────────────

    @staticmethod
    def _fetch(search: str, type_filter: str, etat_filter: str, emplacement_filter: str,
               page: int, per_page: int) -> dict:
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
            query = query.order_by(Materiel.created_at.desc())
            total = query.count()
            payload = []
            for materiel in query.offset((page - 1) * per_page).limit(per_page).all():
                attribution = session.query(Attribution).filter_by(
                    materiel_id=materiel.id, is_active=True
                ).first()
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
            return {"rows": payload, "total": total}
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
            self.current_page,
            self.per_page,
        )

    def _reset_and_refresh(self) -> None:
        self.current_page = 1
        self.search_timer.start()

    def _bind(self, payload: dict) -> None:
        self.rows = payload["rows"]
        self.total_items = payload["total"]
        total_pages = max(1, math.ceil(self.total_items / self.per_page))

        self.subtitle.setText(f"{self.total_items} équipement(s)")
        self.type_chip.set_count(len({row['type'] for row in self.rows}))
        self.etat_chip.set_count(len({row['etat'] for row in self.rows}))
        self.empl_chip.set_count(len({row['emplacement'] for row in self.rows}))

        self.page_label.setText(f"Page {self.current_page} / {total_pages}")
        self.btn_prev.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < total_pages)

        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        if not self.rows:
            self.table.empty("Aucun matériel trouvé")
            return
        self.table.setRowCount(len(self.rows))
        for row_index, row in enumerate(self.rows):
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
            for label, variant, callback in (
                ("Voir QR",    "secondary", partial(self.show_qr,  row["id"])),
                ("Attribuer",  "secondary", partial(self.assign,   row["id"])),
                ("Récupérer",  "secondary", partial(self.recover,  row["id"])),
                ("Supprimer",  "danger",    partial(self.delete,   row["id"])),
            ):
                button = VigileButton(label, variant)
                button.setFixedHeight(28)
                button.setStyleSheet(
                    button.styleSheet().replace("padding: 10px 18px", "padding: 4px 10px")
                )
                button.clicked.connect(callback)
                actions_layout.addWidget(button)
            self.table.setCellWidget(row_index, 6, actions)
        self.table.setSortingEnabled(True)

    # ── Pagination ────────────────────────────────────────────────────────────

    def _prev_page(self) -> None:
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh()

    def _next_page(self) -> None:
        total_pages = max(1, math.ceil(self.total_items / self.per_page))
        if self.current_page < total_pages:
            self.current_page += 1
            self.refresh()

    # ── Actions ───────────────────────────────────────────────────────────────

    def show_qr(self, materiel_id: int) -> None:
        session = get_session()
        try:
            materiel = session.get(Materiel, materiel_id)
            if not materiel or not materiel.qr_code_path:
                QMessageBox.information(self, "QR", "QR code indisponible pour ce matériel.")
                return
            code = materiel.code_vigile
            path = materiel.qr_code_path
        finally:
            session.close()

        if not os.path.exists(path):
            QMessageBox.information(self, "QR", f"Fichier QR introuvable :\n{path}")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"QR Code — {code}")
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        pixmap = QPixmap(path).scaled(
            320, 320,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        img_label = QLabel()
        img_label.setPixmap(pixmap)
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        code_label = QLabel(code)
        code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        code_label.setStyleSheet("font-size: 14px; font-weight: 600;")

        path_label = QLabel(path)
        path_label.setObjectName("MutedLabel")
        path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        path_label.setWordWrap(True)

        close_btn = VigileButton("Fermer", "secondary")
        close_btn.clicked.connect(dialog.accept)

        layout.addWidget(img_label)
        layout.addWidget(code_label)
        layout.addWidget(path_label)
        layout.addWidget(close_btn)
        dialog.exec()

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
            attribution = Attribution(
                materiel_id=materiel_id,
                attribue_a=name.strip(),
                attribue_par=self.current_user["id"],
                is_active=True,
            )
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
            person = active.attribue_a
        finally:
            session.close()

        reply = QMessageBox.question(
            self, "Confirmer la récupération",
            f"Récupérer le matériel attribué à <b>{person}</b> ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        session = get_session()
        try:
            active = session.query(Attribution).filter_by(materiel_id=materiel_id, is_active=True).first()
            if not active:
                return
            active.retourner()
            materiel = session.get(Materiel, materiel_id)
            if materiel:
                materiel.emplacement = "réserve"
            session.commit()
        finally:
            session.close()
        self.refresh()

    def delete(self, materiel_id: int) -> None:
        session = get_session()
        try:
            materiel = session.get(Materiel, materiel_id)
            if not materiel:
                return
            code = materiel.code_vigile
            qr_path = materiel.qr_code_path
            has_active = (
                session.query(Attribution)
                .filter_by(materiel_id=materiel_id, is_active=True)
                .count() > 0
            )
        finally:
            session.close()

        if has_active:
            QMessageBox.warning(
                self, "Suppression impossible",
                f"Le matériel <b>{code}</b> est actuellement attribué.\nRécupérez-le d'abord.",
            )
            return

        reply = QMessageBox.question(
            self, "Confirmer la suppression",
            f"Supprimer définitivement <b>{code}</b> ?\nCette action est irréversible.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        session = get_session()
        try:
            materiel = session.get(Materiel, materiel_id)
            if not materiel:
                return
            if qr_path and os.path.exists(qr_path):
                try:
                    os.remove(qr_path)
                except Exception:
                    pass
            session.delete(materiel)
            session.commit()
        finally:
            session.close()
        self.refresh()

    # ── Export ────────────────────────────────────────────────────────────────

    def export_csv(self) -> None:
        if not self.rows:
            QMessageBox.information(self, "Export", "Aucune ligne à exporter.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter l'inventaire", "vigile-inventaire.csv", "CSV (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=["code", "type", "details", "etat", "emplacement", "attribue"]
            )
            writer.writeheader()
            writer.writerows(self.rows)
        QMessageBox.information(self, "Export", f"Inventaire exporté vers {path}")
