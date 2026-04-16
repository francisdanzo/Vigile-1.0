# -*- coding: utf-8 -*-
"""
VIGILE — Gestion des utilisateurs
"Chaque équipement a sa sentinelle"

Module réservé aux administrateurs pour :
- Lister les utilisateurs existants
- Ajouter de nouveaux gestionnaires
- Activer / désactiver des comptes
"""

import os
import sys
import re
import tkinter as tk
from tkinter import ttk, messagebox

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

from config import ROLES_UTILISATEUR
from database import get_session
from models import User


class UserManagerFrame(tk.Frame):
    """
    Gestion des utilisateurs (admin uniquement).
    Permet d'ajouter, activer/désactiver des comptes.
    """

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self._construire_interface()

    def _construire_interface(self):
        """Construit l'interface de gestion des utilisateurs."""
        # =====================================================================
        # En-tête
        # =====================================================================
        header = tk.Frame(self, bg=COLORS["bg_dark"])
        header.pack(fill="x", padx=30, pady=(25, 15))

        tk.Label(
            header, text="👥 Gestion des utilisateurs",
            bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
            font=("Segoe UI", 22, "bold"), anchor="w"
        ).pack(side="left")

        VigileButton(
            header, text="➕ Nouvel utilisateur",
            command=self._dialog_ajouter, width=190, height=36,
            font_size=10, color=COLORS["accent"]
        ).pack(side="right")

        # =====================================================================
        # Tableau des utilisateurs
        # =====================================================================
        tree_container = tk.Frame(self, bg=COLORS["bg_card"])
        tree_container.pack(fill="both", expand=True, padx=30, pady=(0, 10))

        colonnes = ("id", "username", "email", "role", "statut", "cree_le")
        self.tree = ttk.Treeview(
            tree_container, columns=colonnes, show="headings",
            style="Vigile.Treeview", selectmode="browse"
        )

        col_config = {
            "id": ("ID", 50),
            "username": ("Nom d'utilisateur", 160),
            "email": ("Email", 220),
            "role": ("Rôle", 120),
            "statut": ("Statut", 100),
            "cree_le": ("Créé le", 150),
        }

        for col_id, (titre, largeur) in col_config.items():
            self.tree.heading(col_id, text=titre)
            self.tree.column(col_id, width=largeur, minwidth=40)

        scrollbar = ttk.Scrollbar(
            tree_container, orient="vertical", command=self.tree.yview,
            style="Vigile.Vertical.TScrollbar"
        )
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Tags pour les couleurs
        self.tree.tag_configure("actif", foreground=COLORS["accent_green"])
        self.tree.tag_configure("inactif", foreground=COLORS["accent_red"])
        self.tree.tag_configure("admin", foreground=COLORS["gold"])

        # =====================================================================
        # Barre d'actions
        # =====================================================================
        action_bar = tk.Frame(self, bg=COLORS["bg_dark"])
        action_bar.pack(fill="x", padx=30, pady=(0, 15))

        VigileButton(
            action_bar, text="✅ Activer",
            command=lambda: self._toggle_statut(True),
            width=130, height=36, font_size=10, color=COLORS["accent_green"]
        ).pack(side="left", padx=(0, 8))

        VigileButton(
            action_bar, text="⛔ Désactiver",
            command=lambda: self._toggle_statut(False),
            width=140, height=36, font_size=10, color=COLORS["accent_red"]
        ).pack(side="left", padx=(0, 8))

        VigileButton(
            action_bar, text="🔑 Réinitialiser MDP",
            command=self._reset_password, width=180, height=36,
            font_size=10, color=COLORS["accent_orange"]
        ).pack(side="left", padx=(0, 8))

        VigileButton(
            action_bar, text="↻ Actualiser",
            command=self.rafraichir, width=130, height=36,
            font_size=10, color=COLORS["bg_card"]
        ).pack(side="right")

        # Charger les données
        self.rafraichir()

    def rafraichir(self):
        """Recharge la liste des utilisateurs."""
        self.tree.delete(*self.tree.get_children())

        session = get_session()
        try:
            users = session.query(User).order_by(User.id).all()

            for user in users:
                statut = "✅ Actif" if user.is_active else "⛔ Inactif"
                tag = "actif" if user.is_active else "inactif"
                if user.is_admin:
                    tag = "admin"

                self.tree.insert("", "end", iid=str(user.id), values=(
                    user.id,
                    user.username,
                    user.email,
                    user.role.capitalize(),
                    statut,
                    user.created_at.strftime("%d/%m/%Y %H:%M")
                ), tags=(tag,))

        except Exception as e:
            print(f"[VIGILE] Erreur chargement utilisateurs : {e}")
        finally:
            session.close()

    def _get_selected_user_id(self):
        """Retourne l'ID de l'utilisateur sélectionné ou None."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Sélection", "Veuillez sélectionner un utilisateur.")
            return None
        return int(selection[0])

    def _dialog_ajouter(self):
        """Ouvre le dialogue d'ajout d'utilisateur."""
        dialog = tk.Toplevel(self)
        dialog.title("Nouvel utilisateur")
        dialog.geometry("420x420")
        dialog.configure(bg=COLORS["bg_dark"])
        dialog.transient(self)
        dialog.wait_visibility()
        dialog.grab_set()

        tk.Label(
            dialog, text="➕ Nouvel utilisateur",
            bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
            font=("Segoe UI", 18, "bold")
        ).pack(pady=(20, 20))

        fields_frame = tk.Frame(dialog, bg=COLORS["bg_dark"])
        fields_frame.pack(fill="x", padx=30)

        # Nom d'utilisateur
        tk.Label(
            fields_frame, text="Nom d'utilisateur *",
            bg=COLORS["bg_dark"], fg=COLORS["text_secondary"],
            font=("Segoe UI", 10), anchor="w"
        ).pack(fill="x")
        username_entry = tk.Entry(
            fields_frame, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
            insertbackground=COLORS["accent"], font=("Segoe UI", 11),
            relief="flat", bd=8
        )
        username_entry.pack(fill="x", pady=(2, 10))
        username_entry.focus_set()

        # Email
        tk.Label(
            fields_frame, text="Email *",
            bg=COLORS["bg_dark"], fg=COLORS["text_secondary"],
            font=("Segoe UI", 10), anchor="w"
        ).pack(fill="x")
        email_entry = tk.Entry(
            fields_frame, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
            insertbackground=COLORS["accent"], font=("Segoe UI", 11),
            relief="flat", bd=8
        )
        email_entry.pack(fill="x", pady=(2, 10))

        # Mot de passe
        tk.Label(
            fields_frame, text="Mot de passe *",
            bg=COLORS["bg_dark"], fg=COLORS["text_secondary"],
            font=("Segoe UI", 10), anchor="w"
        ).pack(fill="x")
        password_entry = tk.Entry(
            fields_frame, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
            insertbackground=COLORS["accent"], font=("Segoe UI", 11),
            relief="flat", bd=8, show="•"
        )
        password_entry.pack(fill="x", pady=(2, 10))

        # Rôle
        tk.Label(
            fields_frame, text="Rôle *",
            bg=COLORS["bg_dark"], fg=COLORS["text_secondary"],
            font=("Segoe UI", 10), anchor="w"
        ).pack(fill="x")
        role_combo = ttk.Combobox(
            fields_frame, values=ROLES_UTILISATEUR,
            state="readonly", font=("Segoe UI", 11)
        )
        role_combo.set("gestionnaire")
        role_combo.pack(fill="x", pady=(2, 15))

        def sauvegarder():
            username = username_entry.get().strip()
            email = email_entry.get().strip()
            password = password_entry.get()
            role = role_combo.get()

            # Validation
            if not username:
                messagebox.showwarning("Validation", "Le nom d'utilisateur est obligatoire.")
                return
            if not email:
                messagebox.showwarning("Validation", "L'email est obligatoire.")
                return
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                messagebox.showwarning("Validation", "Format d'email invalide.")
                return
            if not password or len(password) < 4:
                messagebox.showwarning(
                    "Validation", "Le mot de passe doit contenir au moins 4 caractères."
                )
                return

            session = get_session()
            try:
                # Vérifier l'unicité
                existant = session.query(User).filter(
                    (User.username == username) | (User.email == email)
                ).first()
                if existant:
                    messagebox.showwarning(
                        "Doublon",
                        "Un utilisateur avec ce nom ou cet email existe déjà."
                    )
                    return

                user = User(
                    username=username, email=email, role=role, is_active=True
                )
                user.set_password(password)
                session.add(user)
                session.commit()

                messagebox.showinfo(
                    "Succès",
                    f"Utilisateur '{username}' créé avec le rôle '{role}'."
                )
                dialog.destroy()
                self.rafraichir()

            except Exception as e:
                session.rollback()
                messagebox.showerror("Erreur", f"Impossible de créer l'utilisateur :\n{e}")
            finally:
                session.close()

        VigileButton(
            dialog, text="💾 Créer l'utilisateur", command=sauvegarder,
            width=200, height=40, color=COLORS["accent_green"]
        ).pack(pady=(10, 20))

    def _toggle_statut(self, activer):
        """Active ou désactive l'utilisateur sélectionné."""
        user_id = self._get_selected_user_id()
        if not user_id:
            return

        session = get_session()
        try:
            user = session.query(User).get(user_id)
            if not user:
                return

            # Empêcher de se désactiver soi-même / de désactiver le dernier admin
            if not activer:
                if user.is_admin:
                    admins_actifs = session.query(User).filter_by(
                        role="admin", is_active=True
                    ).count()
                    if admins_actifs <= 1:
                        messagebox.showwarning(
                            "Protection",
                            "Impossible de désactiver le dernier administrateur actif."
                        )
                        return

            action = "activer" if activer else "désactiver"
            if messagebox.askyesno(
                "Confirmer",
                f"Voulez-vous {action} l'utilisateur '{user.username}' ?"
            ):
                user.is_active = activer
                session.commit()
                self.rafraichir()
                messagebox.showinfo(
                    "Succès",
                    f"Utilisateur '{user.username}' {'activé' if activer else 'désactivé'}."
                )

        except Exception as e:
            session.rollback()
            messagebox.showerror("Erreur", str(e))
        finally:
            session.close()

    def _reset_password(self):
        """Réinitialise le mot de passe de l'utilisateur sélectionné."""
        user_id = self._get_selected_user_id()
        if not user_id:
            return

        dialog = tk.Toplevel(self)
        dialog.title("Réinitialiser le mot de passe")
        dialog.geometry("380x220")
        dialog.configure(bg=COLORS["bg_dark"])
        dialog.transient(self)
        dialog.wait_visibility()
        dialog.grab_set()

        tk.Label(
            dialog, text="🔑 Nouveau mot de passe",
            bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(20, 15))

        pw_entry = tk.Entry(
            dialog, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
            insertbackground=COLORS["accent"], font=("Segoe UI", 12),
            relief="flat", bd=8, show="•"
        )
        pw_entry.pack(fill="x", padx=30, pady=(0, 15))
        pw_entry.focus_set()

        def confirmer():
            new_pw = pw_entry.get()
            if not new_pw or len(new_pw) < 4:
                messagebox.showwarning(
                    "Validation", "Le mot de passe doit contenir au moins 4 caractères."
                )
                return

            session = get_session()
            try:
                user = session.query(User).get(user_id)
                if user:
                    user.set_password(new_pw)
                    session.commit()
                    messagebox.showinfo(
                        "Succès",
                        f"Mot de passe réinitialisé pour '{user.username}'."
                    )
                    dialog.destroy()
            except Exception as e:
                session.rollback()
                messagebox.showerror("Erreur", str(e))
            finally:
                session.close()

        VigileButton(
            dialog, text="✅ Confirmer", command=confirmer,
            width=160, height=38, color=COLORS["accent"]
        ).pack(pady=(5, 15))

        pw_entry.bind("<Return>", lambda e: confirmer())
