# -*- coding: utf-8 -*-
"""
VIGILE — Vue inventaire du matériel
"Chaque équipement a sa sentinelle"

Tableau complet de l'inventaire avec :
- Filtres par type, état, emplacement
- Recherche textuelle
- Double-clic pour fiche détaillée
- Boutons : Imprimer QR, Attribuer, Modifier état
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timezone

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

from config import TYPES_MATERIEL, ETATS_MATERIEL, EMPLACEMENTS_MATERIEL
from database import get_session
from models import Materiel, Attribution, User


class InventoryFrame(tk.Frame):
    """
    Vue inventaire : tableau complet du matériel avec filtres et actions.
    """

    def __init__(self, parent, current_user):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.current_user = current_user
        self._construire_interface()

    def _construire_interface(self):
        """Construit l'interface de l'inventaire."""
        # =====================================================================
        # En-tête
        # =====================================================================
        header = tk.Frame(self, bg=COLORS["bg_dark"])
        header.pack(fill="x", padx=30, pady=(25, 15))

        tk.Label(
            header, text="📋 Inventaire du matériel",
            bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
            font=("Segoe UI", 22, "bold"), anchor="w"
        ).pack(side="left")

        self.count_label = tk.Label(
            header, text="0 équipement(s)",
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

        # Recherche
        search_frame = tk.Frame(filter_inner, bg=COLORS["bg_card"])
        search_frame.pack(side="left", padx=(0, 15))

        tk.Label(
            search_frame, text="🔍", bg=COLORS["bg_card"],
            font=("Segoe UI", 12)
        ).pack(side="left", padx=(0, 5))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.rafraichir())
        search_entry = tk.Entry(
            search_frame, textvariable=self.search_var,
            bg=COLORS["bg_input"], fg=COLORS["text_primary"],
            insertbackground=COLORS["accent"], font=("Segoe UI", 11),
            relief="flat", bd=6, width=20
        )
        search_entry.pack(side="left")

        # Filtre type
        self._creer_filtre_combo(
            filter_inner, "Type", ["Tous"] + TYPES_MATERIEL, "type_filter"
        )

        # Filtre état
        self._creer_filtre_combo(
            filter_inner, "État", ["Tous"] + ETATS_MATERIEL, "etat_filter"
        )

        # Filtre emplacement
        self._creer_filtre_combo(
            filter_inner, "Lieu", ["Tous"] + EMPLACEMENTS_MATERIEL, "empl_filter"
        )

        # Bouton rafraîchir
        VigileButton(
            filter_inner, text="↻", command=self.rafraichir,
            width=40, height=32, font_size=14, color=COLORS["bg_hover"]
        ).pack(side="right")

        # =====================================================================
        # Tableau (Treeview)
        # =====================================================================
        tree_container = tk.Frame(self, bg=COLORS["bg_card"])
        tree_container.pack(fill="both", expand=True, padx=30, pady=(0, 10))

        colonnes = ("code", "type", "marque", "modele", "serie", "etat", "emplacement", "attribue")
        self.tree = ttk.Treeview(
            tree_container, columns=colonnes, show="headings",
            style="Vigile.Treeview", selectmode="browse"
        )

        # Configuration des colonnes
        col_config = {
            "code": ("Code VIGILE", 140),
            "type": ("Type", 100),
            "marque": ("Marque", 100),
            "modele": ("Modèle", 120),
            "serie": ("N° Série", 120),
            "etat": ("État", 80),
            "emplacement": ("Emplacement", 100),
            "attribue": ("Attribué à", 140),
        }
        for col_id, (titre, largeur) in col_config.items():
            self.tree.heading(col_id, text=titre,
                            command=lambda c=col_id: self._trier_colonne(c))
            self.tree.column(col_id, width=largeur, minwidth=60)

        scrollbar_y = ttk.Scrollbar(
            tree_container, orient="vertical", command=self.tree.yview,
            style="Vigile.Vertical.TScrollbar"
        )
        self.tree.configure(yscrollcommand=scrollbar_y.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar_y.pack(side="right", fill="y")

        # Double-clic pour détails
        self.tree.bind("<Double-1>", self._ouvrir_details)

        # =====================================================================
        # Barre d'actions en bas
        # =====================================================================
        action_bar = tk.Frame(self, bg=COLORS["bg_dark"])
        action_bar.pack(fill="x", padx=30, pady=(0, 15))

        VigileButton(
            action_bar, text="📱 Voir QR Code",
            command=self._voir_qr, width=150, height=36,
            font_size=10, color=COLORS["accent_blue"]
        ).pack(side="left", padx=(0, 8))

        VigileButton(
            action_bar, text="👤 Attribuer",
            command=self._attribuer, width=140, height=36,
            font_size=10, color=COLORS["accent_green"]
        ).pack(side="left", padx=(0, 8))

        VigileButton(
            action_bar, text="📦 Récupérer",
            command=self._recuperer, width=140, height=36,
            font_size=10, color=COLORS["accent_orange"]
        ).pack(side="left", padx=(0, 8))

        VigileButton(
            action_bar, text="🔧 Changer état",
            command=self._changer_etat, width=150, height=36,
            font_size=10, color=COLORS["bg_card"]
        ).pack(side="left")

        # Tri actuel
        self.sort_col = "code"
        self.sort_reverse = False

        # Charger les données
        self.rafraichir()

    def _creer_filtre_combo(self, parent, label, values, attr_name):
        """Crée un filtre combobox."""
        frame = tk.Frame(parent, bg=COLORS["bg_card"])
        frame.pack(side="left", padx=(0, 12))

        tk.Label(
            frame, text=label, bg=COLORS["bg_card"],
            fg=COLORS["text_muted"], font=("Segoe UI", 9)
        ).pack(anchor="w")

        combo = ttk.Combobox(
            frame, values=values, state="readonly",
            font=("Segoe UI", 10), width=12
        )
        combo.set("Tous")
        combo.pack()
        combo.bind("<<ComboboxSelected>>", lambda e: self.rafraichir())

        setattr(self, attr_name, combo)

    def rafraichir(self):
        """Recharge les données depuis la BD avec les filtres appliqués."""
        self.tree.delete(*self.tree.get_children())

        session = get_session()
        try:
            query = session.query(Materiel)

            # Appliquer les filtres
            type_f = self.type_filter.get()
            if type_f and type_f != "Tous":
                query = query.filter(Materiel.type == type_f)

            etat_f = self.etat_filter.get()
            if etat_f and etat_f != "Tous":
                query = query.filter(Materiel.etat == etat_f)

            empl_f = self.empl_filter.get()
            if empl_f and empl_f != "Tous":
                query = query.filter(Materiel.emplacement == empl_f)

            # Recherche textuelle
            search = self.search_var.get().strip().lower()
            if search:
                query = query.filter(
                    (Materiel.code_vigile.ilike(f"%{search}%")) |
                    (Materiel.marque.ilike(f"%{search}%")) |
                    (Materiel.modele.ilike(f"%{search}%")) |
                    (Materiel.numero_serie.ilike(f"%{search}%"))
                )

            materiels = query.order_by(Materiel.created_at.desc()).all()

            for mat in materiels:
                # Trouver l'attribution active
                attr_active = (
                    session.query(Attribution)
                    .filter_by(materiel_id=mat.id, is_active=True)
                    .first()
                )
                attribue_a = attr_active.attribue_a if attr_active else "—"

                # Tags pour colorer les lignes
                tag = ""
                if mat.etat == "en_panne":
                    tag = "panne"
                elif attr_active:
                    tag = "attribue"

                self.tree.insert("", "end", iid=str(mat.id), values=(
                    mat.code_vigile,
                    mat.type,
                    mat.marque or "—",
                    mat.modele or "—",
                    mat.numero_serie or "—",
                    mat.etat,
                    mat.emplacement,
                    attribue_a
                ), tags=(tag,))

            # Couleurs des tags
            self.tree.tag_configure("panne", foreground=COLORS["accent_red"])
            self.tree.tag_configure("attribue", foreground=COLORS["accent_orange"])

            # Mise à jour du compteur
            self.count_label.config(text=f"{len(materiels)} équipement(s)")

        except Exception as e:
            print(f"[VIGILE] Erreur rafraîchissement inventaire : {e}")
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

    def _get_selected_materiel_id(self):
        """Retourne l'ID du matériel sélectionné ou None."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Sélection", "Veuillez sélectionner un matériel.")
            return None
        return int(selection[0])

    def _ouvrir_details(self, event):
        """Ouvre une fenêtre de détails pour le matériel sélectionné."""
        mat_id = self._get_selected_materiel_id()
        if not mat_id:
            return

        session = get_session()
        try:
            mat = session.query(Materiel).get(mat_id)
            if not mat:
                return

            # Fenêtre de détails
            detail_win = tk.Toplevel(self)
            detail_win.title(f"VIGILE — {mat.code_vigile}")
            detail_win.geometry("500x550")
            detail_win.configure(bg=COLORS["bg_dark"])
            detail_win.transient(self)
            detail_win.grab_set()

            # Contenu
            content = tk.Frame(detail_win, bg=COLORS["bg_dark"])
            content.pack(fill="both", expand=True, padx=25, pady=20)

            tk.Label(
                content, text=f"🏷 {mat.code_vigile}",
                bg=COLORS["bg_dark"], fg=COLORS["accent"],
                font=("Segoe UI", 20, "bold")
            ).pack(anchor="w", pady=(0, 15))

            # Infos dans une carte
            card = tk.Frame(content, bg=COLORS["bg_card"])
            card.pack(fill="x", pady=(0, 10))
            inner = tk.Frame(card, bg=COLORS["bg_card"])
            inner.pack(fill="x", padx=20, pady=15)

            infos = [
                ("Type", mat.type),
                ("Marque", mat.marque or "—"),
                ("Modèle", mat.modele or "—"),
                ("N° Série", mat.numero_serie or "—"),
                ("État", mat.etat),
                ("Emplacement", mat.emplacement),
                ("Date acquisition", mat.date_acquisition.strftime("%d/%m/%Y") if mat.date_acquisition else "—"),
                ("Notes", mat.notes or "—"),
            ]

            for label, valeur in infos:
                row = tk.Frame(inner, bg=COLORS["bg_card"])
                row.pack(fill="x", pady=3)
                tk.Label(
                    row, text=f"{label} :", bg=COLORS["bg_card"],
                    fg=COLORS["text_muted"], font=("Segoe UI", 10),
                    width=16, anchor="w"
                ).pack(side="left")
                tk.Label(
                    row, text=valeur, bg=COLORS["bg_card"],
                    fg=COLORS["text_primary"], font=("Segoe UI", 10),
                    anchor="w"
                ).pack(side="left", fill="x", expand=True)

            # Attribution active
            attr = (
                session.query(Attribution)
                .filter_by(materiel_id=mat.id, is_active=True)
                .first()
            )
            if attr:
                tk.Label(
                    content, text=f"👤 Attribué à : {attr.attribue_a}",
                    bg=COLORS["bg_dark"], fg=COLORS["accent_orange"],
                    font=("Segoe UI", 13, "bold"), anchor="w"
                ).pack(fill="x", pady=(10, 0))
                tk.Label(
                    content,
                    text=f"   Depuis le {attr.date_attribution.strftime('%d/%m/%Y')}",
                    bg=COLORS["bg_dark"], fg=COLORS["text_muted"],
                    font=("Segoe UI", 10), anchor="w"
                ).pack(fill="x")
            else:
                tk.Label(
                    content, text="✅ Disponible",
                    bg=COLORS["bg_dark"], fg=COLORS["accent_green"],
                    font=("Segoe UI", 13, "bold"), anchor="w"
                ).pack(fill="x", pady=(10, 0))

            # QR Code aperçu
            if mat.qr_code_path and os.path.exists(mat.qr_code_path):
                try:
                    from PIL import Image, ImageTk
                    img = Image.open(mat.qr_code_path)
                    img = img.resize((150, 150), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    qr_lbl = tk.Label(
                        content, image=photo, bg=COLORS["bg_dark"]
                    )
                    qr_lbl.image = photo  # Garder la référence
                    qr_lbl.pack(pady=(15, 0))
                except Exception:
                    pass

        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger les détails :\n{e}")
        finally:
            session.close()

    def _voir_qr(self):
        """Ouvre le fichier QR code du matériel sélectionné."""
        mat_id = self._get_selected_materiel_id()
        if not mat_id:
            return

        session = get_session()
        try:
            mat = session.query(Materiel).get(mat_id)
            if mat and mat.qr_code_path and os.path.exists(mat.qr_code_path):
                # Ouvrir avec le visualiseur par défaut du système
                import subprocess
                if sys.platform == "win32":
                    os.startfile(mat.qr_code_path)
                elif sys.platform == "darwin":
                    subprocess.run(["open", mat.qr_code_path])
                else:
                    subprocess.run(["xdg-open", mat.qr_code_path])
            else:
                messagebox.showinfo("QR Code", "Aucun QR code trouvé pour ce matériel.")
        finally:
            session.close()

    def _attribuer(self):
        """Ouvre le dialogue d'attribution pour le matériel sélectionné."""
        mat_id = self._get_selected_materiel_id()
        if not mat_id:
            return

        session = get_session()
        try:
            mat = session.query(Materiel).get(mat_id)
            if not mat:
                return

            # Vérifier qu'il n'est pas déjà attribué
            attr_active = (
                session.query(Attribution)
                .filter_by(materiel_id=mat.id, is_active=True)
                .first()
            )
            if attr_active:
                messagebox.showwarning(
                    "Attribution",
                    f"Ce matériel est déjà attribué à {attr_active.attribue_a}.\n"
                    f"Récupérez-le d'abord."
                )
                return

            mat_code = mat.code_vigile
        finally:
            session.close()

        # Dialogue d'attribution
        dialog = tk.Toplevel(self)
        dialog.title("Attribuer le matériel")
        dialog.geometry("400x280")
        dialog.configure(bg=COLORS["bg_dark"])
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(
            dialog, text=f"👤 Attribuer {mat_code}",
            bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(20, 15))

        # Champ nom
        tk.Label(
            dialog, text="Nom de la personne :",
            bg=COLORS["bg_dark"], fg=COLORS["text_secondary"],
            font=("Segoe UI", 11)
        ).pack(anchor="w", padx=30)

        nom_entry = tk.Entry(
            dialog, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
            insertbackground=COLORS["accent"], font=("Segoe UI", 12),
            relief="flat", bd=8
        )
        nom_entry.pack(fill="x", padx=30, pady=(5, 10))
        nom_entry.focus_set()

        # Champ notes
        tk.Label(
            dialog, text="Notes (optionnel) :",
            bg=COLORS["bg_dark"], fg=COLORS["text_secondary"],
            font=("Segoe UI", 11)
        ).pack(anchor="w", padx=30)

        notes_entry = tk.Entry(
            dialog, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
            insertbackground=COLORS["accent"], font=("Segoe UI", 12),
            relief="flat", bd=8
        )
        notes_entry.pack(fill="x", padx=30, pady=(5, 15))

        def confirmer():
            nom = nom_entry.get().strip()
            if not nom:
                messagebox.showwarning("Validation", "Le nom est obligatoire.")
                return

            session2 = get_session()
            try:
                attr = Attribution(
                    materiel_id=mat_id,
                    attribue_a=nom,
                    attribue_par=self.current_user["id"],
                    notes=notes_entry.get().strip() or None,
                    is_active=True
                )
                # Mettre à jour l'emplacement
                materiel = session2.query(Materiel).get(mat_id)
                if materiel:
                    materiel.emplacement = "attribué"
                session2.add(attr)
                session2.commit()
                messagebox.showinfo("Succès", f"Matériel attribué à {nom}.")
                dialog.destroy()
                self.rafraichir()
            except Exception as e:
                session2.rollback()
                messagebox.showerror("Erreur", f"Erreur d'attribution :\n{e}")
            finally:
                session2.close()

        VigileButton(
            dialog, text="✅ Confirmer", command=confirmer,
            width=160, height=38, color=COLORS["accent_green"]
        ).pack(pady=(5, 15))

        nom_entry.bind("<Return>", lambda e: confirmer())

    def _recuperer(self):
        """Récupère le matériel sélectionné (fin d'attribution)."""
        mat_id = self._get_selected_materiel_id()
        if not mat_id:
            return

        session = get_session()
        try:
            attr = (
                session.query(Attribution)
                .filter_by(materiel_id=mat_id, is_active=True)
                .first()
            )
            if not attr:
                messagebox.showinfo(
                    "Récupération", "Ce matériel n'est attribué à personne."
                )
                return

            if messagebox.askyesno(
                "Confirmer",
                f"Récupérer le matériel de {attr.attribue_a} ?"
            ):
                attr.retourner()
                # Remettre l'emplacement à réserve
                materiel = session.query(Materiel).get(mat_id)
                if materiel:
                    materiel.emplacement = "réserve"
                session.commit()
                messagebox.showinfo("Succès", "Matériel récupéré.")
                self.rafraichir()

        except Exception as e:
            session.rollback()
            messagebox.showerror("Erreur", f"Erreur de récupération :\n{e}")
        finally:
            session.close()

    def _changer_etat(self):
        """Change l'état du matériel sélectionné."""
        mat_id = self._get_selected_materiel_id()
        if not mat_id:
            return

        dialog = tk.Toplevel(self)
        dialog.title("Changer l'état")
        dialog.geometry("350x200")
        dialog.configure(bg=COLORS["bg_dark"])
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(
            dialog, text="🔧 Nouvel état",
            bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(20, 15))

        combo = ttk.Combobox(
            dialog, values=ETATS_MATERIEL, state="readonly",
            font=("Segoe UI", 12)
        )
        combo.pack(padx=30, fill="x")
        combo.set(ETATS_MATERIEL[0])

        def confirmer():
            nouvel_etat = combo.get()
            session2 = get_session()
            try:
                mat = session2.query(Materiel).get(mat_id)
                if mat:
                    mat.etat = nouvel_etat
                    session2.commit()
                    messagebox.showinfo("Succès", f"État changé en '{nouvel_etat}'.")
                    dialog.destroy()
                    self.rafraichir()
            except Exception as e:
                session2.rollback()
                messagebox.showerror("Erreur", str(e))
            finally:
                session2.close()

        VigileButton(
            dialog, text="✅ Confirmer", command=confirmer,
            width=160, height=38, color=COLORS["accent"]
        ).pack(pady=20)
