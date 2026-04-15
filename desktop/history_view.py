# -*- coding: utf-8 -*-
"""
VIGILE — Vue historique des attributions
"Chaque équipement a sa sentinelle"

Affiche l'historique complet des attributions :
- Qui a eu quel matériel et quand
- Filtrage par nom de personne et par matériel
- Indicateur visuel : attribution active (vert) vs terminée (gris)
"""

import os
import sys
import tkinter as tk
from tkinter import ttk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from desktop.main_window import COLORS, VigileButton
except ImportError:
    COLORS = {
        "bg_dark": "#0f0f1a", "bg_sidebar": "#161625", "bg_card": "#1c1c2e",
        "bg_input": "#252540", "bg_hover": "#2a2a45", "accent": "#6c63ff",
        "accent_green": "#00c896", "accent_orange": "#ff9f43",
        "accent_red": "#ff6b6b", "accent_blue": "#54a0ff",
        "text_primary": "#e8e8e8", "text_secondary": "#8888a0",
        "text_muted": "#555570", "border": "#2a2a45", "gold": "#ffd700",
    }

from database import get_session
from models import Materiel, Attribution, User


class HistoryFrame(tk.Frame):
    """
    Vue historique : tableau de toutes les attributions passées et actives.
    """

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self._construire_interface()

    def _construire_interface(self):
        """Construit l'interface de l'historique."""
        # =====================================================================
        # En-tête
        # =====================================================================
        header = tk.Frame(self, bg=COLORS["bg_dark"])
        header.pack(fill="x", padx=30, pady=(25, 15))

        tk.Label(
            header, text="📜 Historique des attributions",
            bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
            font=("Segoe UI", 22, "bold"), anchor="w"
        ).pack(side="left")

        self.count_label = tk.Label(
            header, text="0 attribution(s)",
            bg=COLORS["bg_dark"], fg=COLORS["text_muted"],
            font=("Segoe UI", 12), anchor="e"
        )
        self.count_label.pack(side="right")

        # =====================================================================
        # Barre de filtres
        # =====================================================================
        filter_card = tk.Frame(
            self, bg=COLORS["bg_card"],
            highlightbackground=COLORS["border"], highlightthickness=1
        )
        filter_card.pack(fill="x", padx=30, pady=(0, 10))

        filter_inner = tk.Frame(filter_card, bg=COLORS["bg_card"])
        filter_inner.pack(fill="x", padx=15, pady=12)

        # Recherche par nom de personne
        tk.Label(
            filter_inner, text="🔍 Personne :", bg=COLORS["bg_card"],
            fg=COLORS["text_muted"], font=("Segoe UI", 10)
        ).pack(side="left", padx=(0, 5))

        self.search_personne = tk.StringVar()
        self.search_personne.trace_add("write", lambda *a: self.rafraichir())
        tk.Entry(
            filter_inner, textvariable=self.search_personne,
            bg=COLORS["bg_input"], fg=COLORS["text_primary"],
            insertbackground=COLORS["accent"], font=("Segoe UI", 11),
            relief="flat", bd=6, width=18
        ).pack(side="left", padx=(0, 15))

        # Recherche par code matériel
        tk.Label(
            filter_inner, text="📦 Matériel :", bg=COLORS["bg_card"],
            fg=COLORS["text_muted"], font=("Segoe UI", 10)
        ).pack(side="left", padx=(0, 5))

        self.search_materiel = tk.StringVar()
        self.search_materiel.trace_add("write", lambda *a: self.rafraichir())
        tk.Entry(
            filter_inner, textvariable=self.search_materiel,
            bg=COLORS["bg_input"], fg=COLORS["text_primary"],
            insertbackground=COLORS["accent"], font=("Segoe UI", 11),
            relief="flat", bd=6, width=18
        ).pack(side="left", padx=(0, 15))

        # Filtre actif/terminé
        self.filtre_statut = ttk.Combobox(
            filter_inner, values=["Toutes", "Actives", "Terminées"],
            state="readonly", font=("Segoe UI", 10), width=10
        )
        self.filtre_statut.set("Toutes")
        self.filtre_statut.pack(side="left", padx=(0, 10))
        self.filtre_statut.bind("<<ComboboxSelected>>", lambda e: self.rafraichir())

        # Bouton rafraîchir
        VigileButton(
            filter_inner, text="↻", command=self.rafraichir,
            width=40, height=32, font_size=14, color=COLORS["bg_hover"]
        ).pack(side="right")

        # =====================================================================
        # Tableau
        # =====================================================================
        tree_container = tk.Frame(self, bg=COLORS["bg_card"])
        tree_container.pack(fill="both", expand=True, padx=30, pady=(0, 15))

        colonnes = (
            "statut", "code_materiel", "type", "attribue_a",
            "date_attribution", "date_retour", "attribue_par", "notes"
        )
        self.tree = ttk.Treeview(
            tree_container, columns=colonnes, show="headings",
            style="Vigile.Treeview", selectmode="browse"
        )

        col_config = {
            "statut": ("●", 40),
            "code_materiel": ("Matériel", 140),
            "type": ("Type", 90),
            "attribue_a": ("Attribué à", 150),
            "date_attribution": ("Date attribution", 140),
            "date_retour": ("Date retour", 140),
            "attribue_par": ("Par", 100),
            "notes": ("Notes", 180),
        }

        for col_id, (titre, largeur) in col_config.items():
            self.tree.heading(col_id, text=titre,
                            command=lambda c=col_id: self._trier_colonne(c))
            self.tree.column(col_id, width=largeur, minwidth=40)

        scrollbar = ttk.Scrollbar(
            tree_container, orient="vertical", command=self.tree.yview,
            style="Vigile.Vertical.TScrollbar"
        )
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Tags pour les couleurs
        self.tree.tag_configure("active", foreground=COLORS["accent_green"])
        self.tree.tag_configure("terminee", foreground=COLORS["text_muted"])

        # Tri
        self.sort_col = "date_attribution"
        self.sort_reverse = True

        # Charger les données
        self.rafraichir()

    def rafraichir(self):
        """Recharge l'historique depuis la BD."""
        self.tree.delete(*self.tree.get_children())

        session = get_session()
        try:
            query = session.query(Attribution)

            # Filtre statut
            statut = self.filtre_statut.get()
            if statut == "Actives":
                query = query.filter(Attribution.is_active == True)
            elif statut == "Terminées":
                query = query.filter(Attribution.is_active == False)

            # Filtre par personne
            pers = self.search_personne.get().strip().lower()
            if pers:
                query = query.filter(Attribution.attribue_a.ilike(f"%{pers}%"))

            # Filtre par matériel (nécessite un join)
            mat_search = self.search_materiel.get().strip().lower()
            if mat_search:
                query = query.join(Materiel).filter(
                    Materiel.code_vigile.ilike(f"%{mat_search}%")
                )

            attributions = query.order_by(
                Attribution.date_attribution.desc()
            ).all()

            for attr in attributions:
                # Chercher les infos liées
                materiel = session.query(Materiel).get(attr.materiel_id)
                user = session.query(User).get(attr.attribue_par)

                code = materiel.code_vigile if materiel else "?"
                type_mat = materiel.type if materiel else "?"
                par = user.username if user else "?"

                date_attr = attr.date_attribution.strftime("%d/%m/%Y %H:%M")
                date_ret = (
                    attr.date_retour.strftime("%d/%m/%Y %H:%M")
                    if attr.date_retour else "—"
                )

                statut_icon = "🟢" if attr.is_active else "⚪"
                tag = "active" if attr.is_active else "terminee"

                self.tree.insert("", "end", values=(
                    statut_icon, code, type_mat, attr.attribue_a,
                    date_attr, date_ret, par,
                    attr.notes or "—"
                ), tags=(tag,))

            self.count_label.config(text=f"{len(attributions)} attribution(s)")

        except Exception as e:
            print(f"[VIGILE] Erreur rafraîchissement historique : {e}")
        finally:
            session.close()

    def _trier_colonne(self, col):
        """Trie le tableau par colonne."""
        if self.sort_col == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_col = col
            self.sort_reverse = False

        items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        items.sort(reverse=self.sort_reverse)

        for index, (_, k) in enumerate(items):
            self.tree.move(k, "", index)
