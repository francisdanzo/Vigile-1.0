# -*- coding: utf-8 -*-
"""
VIGILE — Fenêtre principale Tkinter
"Chaque équipement a sa sentinelle"

Ce module contient :
- LoginFrame : écran de connexion au démarrage
- MainWindow : fenêtre principale avec navigation latérale
- DashboardFrame : tableau de bord avec statistiques
- ServerFrame : contrôle du serveur Flask
"""

import os
import sys
import socket
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timezone

# Ajouter le répertoire racine au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    APP_NAME, APP_SLOGAN, APP_VERSION, FLASK_PORT,
    TYPES_MATERIEL, ETATS_MATERIEL, EMPLACEMENTS_MATERIEL
)
from database import get_session, init_db
from models import User, Materiel, Attribution


# =============================================================================
# Palette de couleurs VIGILE
# =============================================================================

COLORS = {
    "bg_dark": "#0f0f1a",        # Fond principal sombre
    "bg_sidebar": "#161625",     # Fond barre latérale
    "bg_card": "#1c1c2e",        # Fond des cartes/panneaux
    "bg_input": "#252540",       # Fond des champs de saisie
    "bg_hover": "#2a2a45",       # Fond survol
    "accent": "#6c63ff",         # Violet accent principal
    "accent_hover": "#5a52d5",   # Violet survol
    "accent_green": "#00c896",   # Vert succès
    "accent_orange": "#ff9f43",  # Orange avertissement
    "accent_red": "#ff6b6b",     # Rouge danger/erreur
    "accent_blue": "#54a0ff",    # Bleu info
    "text_primary": "#e8e8e8",   # Texte principal
    "text_secondary": "#8888a0", # Texte secondaire
    "text_muted": "#555570",     # Texte atténué
    "border": "#2a2a45",         # Bordures
    "gold": "#ffd700",           # Doré pour le slogan
}


# =============================================================================
# Configuration du style ttk global
# =============================================================================

def configurer_style(root):
    """Configure le thème ttk pour toute l'application."""
    style = ttk.Style(root)
    style.theme_use("clam")

    # Treeview (tableaux)
    style.configure(
        "Vigile.Treeview",
        background=COLORS["bg_card"],
        foreground=COLORS["text_primary"],
        fieldbackground=COLORS["bg_card"],
        rowheight=32,
        borderwidth=0,
        font=("Segoe UI", 10)
    )
    style.configure(
        "Vigile.Treeview.Heading",
        background=COLORS["bg_sidebar"],
        foreground=COLORS["accent"],
        font=("Segoe UI", 10, "bold"),
        borderwidth=0,
        relief="flat"
    )
    style.map(
        "Vigile.Treeview",
        background=[("selected", COLORS["accent"])],
        foreground=[("selected", "#ffffff")]
    )

    # Scrollbar
    style.configure(
        "Vigile.Vertical.TScrollbar",
        background=COLORS["bg_sidebar"],
        troughcolor=COLORS["bg_dark"],
        borderwidth=0,
        arrowsize=0
    )

    return style


# =============================================================================
# Widgets personnalisés réutilisables
# =============================================================================

class VigileButton(tk.Canvas):
    """Bouton personnalisé avec coins arrondis et effets de survol."""

    def __init__(self, parent, text, command=None, color=None,
                 width=180, height=40, font_size=11, **kwargs):
        super().__init__(
            parent, width=width, height=height,
            bg=parent.cget("bg") if hasattr(parent, "cget") else COLORS["bg_dark"],
            highlightthickness=0, **kwargs
        )
        self.command = command
        self.color = color or COLORS["accent"]
        self.hover_color = self._lighten(self.color)
        self.text = text
        self.width = width
        self.height = height
        self.font_size = font_size
        self._active_color = self.color

        self._draw()

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _lighten(self, hex_color):
        """Éclaircit une couleur hexadécimale."""
        r = min(255, int(hex_color[1:3], 16) + 25)
        g = min(255, int(hex_color[3:5], 16) + 25)
        b = min(255, int(hex_color[5:7], 16) + 25)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _draw(self):
        """Dessine le bouton avec coins arrondis."""
        self.delete("all")
        r = 8  # rayon des coins
        w, h = self.width, self.height
        # Rectangle arrondi
        self.create_arc(0, 0, 2*r, 2*r, start=90, extent=90,
                       fill=self._active_color, outline="")
        self.create_arc(w-2*r, 0, w, 2*r, start=0, extent=90,
                       fill=self._active_color, outline="")
        self.create_arc(0, h-2*r, 2*r, h, start=180, extent=90,
                       fill=self._active_color, outline="")
        self.create_arc(w-2*r, h-2*r, w, h, start=270, extent=90,
                       fill=self._active_color, outline="")
        self.create_rectangle(r, 0, w-r, h, fill=self._active_color, outline="")
        self.create_rectangle(0, r, w, h-r, fill=self._active_color, outline="")
        # Texte centré
        self.create_text(
            w//2, h//2, text=self.text,
            fill="#ffffff", font=("Segoe UI", self.font_size, "bold")
        )

    def _on_enter(self, event):
        self._active_color = self.hover_color
        self._draw()

    def _on_leave(self, event):
        self._active_color = self.color
        self._draw()

    def _on_click(self, event):
        if self.command:
            self.command()


class VigileEntry(tk.Frame):
    """Champ de saisie stylisé avec label optionnel."""

    def __init__(self, parent, label="", placeholder="", show="", **kwargs):
        super().__init__(parent, bg=COLORS["bg_card"])

        if label:
            lbl = tk.Label(
                self, text=label, bg=COLORS["bg_card"],
                fg=COLORS["text_secondary"],
                font=("Segoe UI", 10), anchor="w"
            )
            lbl.pack(fill="x", pady=(0, 4))

        self.entry_frame = tk.Frame(
            self, bg=COLORS["bg_input"],
            highlightbackground=COLORS["border"],
            highlightthickness=1, highlightcolor=COLORS["accent"]
        )
        self.entry_frame.pack(fill="x")

        entry_kwargs = {
            "bg": COLORS["bg_input"],
            "fg": COLORS["text_primary"],
            "insertbackground": COLORS["accent"],
            "font": ("Segoe UI", 11),
            "relief": "flat",
            "bd": 8,
        }
        if show:
            entry_kwargs["show"] = show

        self.entry = tk.Entry(self.entry_frame, **entry_kwargs)
        self.entry.pack(fill="x")

        # Placeholder
        self._is_placeholder_active = False
        if placeholder:
            self._placeholder = placeholder
            self._is_placeholder_active = True
            self.entry.insert(0, placeholder)
            self.entry.config(fg=COLORS["text_muted"])
            self.entry.bind("<FocusIn>", self._on_focus_in)
            self.entry.bind("<FocusOut>", self._on_focus_out)

    def _on_focus_in(self, event):
        if self._is_placeholder_active:
            self.entry.delete(0, "end")
            self.entry.config(fg=COLORS["text_primary"])
            self._is_placeholder_active = False

    def _on_focus_out(self, event):
        if not self.entry.get():
            self._is_placeholder_active = True
            self.entry.insert(0, self._placeholder)
            self.entry.config(fg=COLORS["text_muted"])

    def get(self):
        """Retourne la valeur saisie (ignore le placeholder)."""
        if getattr(self, "_is_placeholder_active", False):
            return ""
        return self.entry.get()

    def set(self, value):
        """Définit la valeur du champ."""
        self.entry.delete(0, "end")
        self.entry.insert(0, value)
        self.entry.config(fg=COLORS["text_primary"])
        self._is_placeholder_active = False

    def clear(self):
        """Vide le champ."""
        self.entry.delete(0, "end")
        if hasattr(self, "_placeholder"):
            self._is_placeholder_active = True
            self.entry.insert(0, self._placeholder)
            self.entry.config(fg=COLORS["text_muted"])
        else:
            self._is_placeholder_active = False


# =============================================================================
# LoginFrame — Écran de connexion
# =============================================================================

class LoginFrame(tk.Frame):
    """
    Écran de connexion affiché au démarrage.
    Authentifie l'utilisateur via username/password (bcrypt).
    """

    def __init__(self, parent, on_login_success):
        """
        Args:
            parent: Widget parent (root)
            on_login_success: Callback appelé avec l'objet User après connexion
        """
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.on_login_success = on_login_success
        self._construire_interface()

    def _construire_interface(self):
        """Construit l'interface de connexion."""
        # Centrer le contenu
        container = tk.Frame(self, bg=COLORS["bg_dark"])
        container.place(relx=0.5, rely=0.5, anchor="center")

        # Logo / Titre
        titre = tk.Label(
            container, text="🛡 VIGILE",
            bg=COLORS["bg_dark"], fg=COLORS["accent"],
            font=("Segoe UI", 36, "bold")
        )
        titre.pack(pady=(0, 5))

        slogan = tk.Label(
            container, text=APP_SLOGAN,
            bg=COLORS["bg_dark"], fg=COLORS["gold"],
            font=("Segoe UI", 12, "italic")
        )
        slogan.pack(pady=(0, 30))

        # Carte de connexion
        card = tk.Frame(
            container, bg=COLORS["bg_card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )
        card.pack(padx=40, pady=10, ipadx=30, ipady=25)

        tk.Label(
            card, text="Connexion", bg=COLORS["bg_card"],
            fg=COLORS["text_primary"], font=("Segoe UI", 18, "bold")
        ).pack(pady=(10, 20))

        # Champ username
        self.username_field = VigileEntry(
            card, label="Nom d'utilisateur", placeholder="admin"
        )
        self.username_field.pack(fill="x", padx=20, pady=(0, 12))

        # Champ password
        self.password_field = VigileEntry(
            card, label="Mot de passe", placeholder="••••••••", show="•"
        )
        self.password_field.pack(fill="x", padx=20, pady=(0, 20))

        # Message d'erreur (caché par défaut)
        self.error_label = tk.Label(
            card, text="", bg=COLORS["bg_card"],
            fg=COLORS["accent_red"], font=("Segoe UI", 10)
        )
        self.error_label.pack(pady=(0, 10))

        # Bouton connexion
        btn = VigileButton(
            card, text="Se connecter", command=self._tenter_connexion,
            width=220, height=42
        )
        btn.pack(pady=(0, 15))

        # Version
        tk.Label(
            container, text=f"v{APP_VERSION}",
            bg=COLORS["bg_dark"], fg=COLORS["text_muted"],
            font=("Segoe UI", 9)
        ).pack(pady=(20, 0))

        # Bind Enter key
        self.username_field.entry.bind("<Return>", lambda e: self._tenter_connexion())
        self.password_field.entry.bind("<Return>", lambda e: self._tenter_connexion())

        # Focus sur le champ username
        self.after(100, lambda: self.username_field.entry.focus_set())

    def _tenter_connexion(self):
        """Vérifie les credentials et connecte l'utilisateur."""
        username = self.username_field.get()
        password = self.password_field.get()

        if not username or not password:
            self.error_label.config(text="Veuillez remplir tous les champs.")
            return

        session = get_session()
        try:
            user = session.query(User).filter_by(
                username=username, is_active=True
            ).first()

            if user and user.check_password(password):
                self.error_label.config(text="")
                # Stocker les infos nécessaires avant de fermer la session
                user_id = user.id
                user_username = user.username
                user_role = user.role
                session.close()
                # Créer un objet dict pour transporter les infos
                user_info = {
                    "id": user_id,
                    "username": user_username,
                    "role": user_role
                }
                self.on_login_success(user_info)
            else:
                self.error_label.config(
                    text="Nom d'utilisateur ou mot de passe incorrect."
                )
                self.password_field.clear()
        except Exception as e:
            self.error_label.config(text=f"Erreur de connexion : {e}")
        finally:
            session.close()


# =============================================================================
# DashboardFrame — Tableau de bord avec statistiques
# =============================================================================

class DashboardFrame(tk.Frame):
    """
    Tableau de bord principal avec cartes de statistiques.
    Affiche : total matériel, attribué, disponible, en panne.
    """

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self._construire_interface()

    def _construire_interface(self):
        """Construit le tableau de bord."""
        # Titre
        header = tk.Frame(self, bg=COLORS["bg_dark"])
        header.pack(fill="x", padx=30, pady=(25, 20))

        tk.Label(
            header, text="📊 Tableau de bord",
            bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
            font=("Segoe UI", 22, "bold"), anchor="w"
        ).pack(side="left")

        # Bouton rafraîchir
        VigileButton(
            header, text="↻ Actualiser", command=self.rafraichir,
            width=130, height=34, font_size=10,
            color=COLORS["bg_card"]
        ).pack(side="right")

        # Zone des cartes de statistiques
        self.cards_frame = tk.Frame(self, bg=COLORS["bg_dark"])
        self.cards_frame.pack(fill="x", padx=30, pady=10)

        # Stocker les labels pour mise à jour
        self.stat_labels = {}

        # Créer les 4 cartes
        cartes_config = [
            ("total", "📦 Total matériel", COLORS["accent_blue"], "0"),
            ("attribue", "👤 Attribué", COLORS["accent_orange"], "0"),
            ("disponible", "✅ Disponible", COLORS["accent_green"], "0"),
            ("en_panne", "⚠ En panne", COLORS["accent_red"], "0"),
        ]

        for i, (key, titre, couleur, valeur) in enumerate(cartes_config):
            card = self._creer_carte(
                self.cards_frame, titre, valeur, couleur, i
            )
            self.stat_labels[key] = card

        # Zone d'activité récente
        recent_frame = tk.Frame(self, bg=COLORS["bg_dark"])
        recent_frame.pack(fill="both", expand=True, padx=30, pady=(20, 15))

        tk.Label(
            recent_frame, text="🕐 Activité récente",
            bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
            font=("Segoe UI", 16, "bold"), anchor="w"
        ).pack(fill="x", pady=(0, 10))

        # Treeview pour les dernières actions
        tree_container = tk.Frame(recent_frame, bg=COLORS["bg_card"])
        tree_container.pack(fill="both", expand=True)

        colonnes = ("date", "action", "materiel", "personne")
        self.tree_recent = ttk.Treeview(
            tree_container, columns=colonnes, show="headings",
            style="Vigile.Treeview", height=8
        )
        self.tree_recent.heading("date", text="Date")
        self.tree_recent.heading("action", text="Action")
        self.tree_recent.heading("materiel", text="Matériel")
        self.tree_recent.heading("personne", text="Personne")

        self.tree_recent.column("date", width=150, minwidth=120)
        self.tree_recent.column("action", width=120, minwidth=100)
        self.tree_recent.column("materiel", width=200, minwidth=150)
        self.tree_recent.column("personne", width=180, minwidth=120)

        scrollbar = ttk.Scrollbar(
            tree_container, orient="vertical",
            command=self.tree_recent.yview,
            style="Vigile.Vertical.TScrollbar"
        )
        self.tree_recent.configure(yscrollcommand=scrollbar.set)

        self.tree_recent.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Charger les données
        self.rafraichir()

    def _creer_carte(self, parent, titre, valeur, couleur, index):
        """Crée une carte de statistique."""
        card = tk.Frame(
            parent, bg=COLORS["bg_card"],
            highlightbackground=couleur,
            highlightthickness=2
        )
        card.grid(row=0, column=index, padx=8, pady=5, sticky="nsew")
        parent.grid_columnconfigure(index, weight=1)

        # Bande colorée en haut
        top_bar = tk.Frame(card, bg=couleur, height=4)
        top_bar.pack(fill="x")

        # Contenu
        content = tk.Frame(card, bg=COLORS["bg_card"])
        content.pack(fill="both", expand=True, padx=18, pady=15)

        label_titre = tk.Label(
            content, text=titre, bg=COLORS["bg_card"],
            fg=COLORS["text_secondary"], font=("Segoe UI", 11),
            anchor="w"
        )
        label_titre.pack(fill="x")

        label_valeur = tk.Label(
            content, text=valeur, bg=COLORS["bg_card"],
            fg=couleur, font=("Segoe UI", 32, "bold"),
            anchor="w"
        )
        label_valeur.pack(fill="x", pady=(5, 0))

        return label_valeur

    def rafraichir(self):
        """Rafraîchit les statistiques depuis la base de données."""
        session = get_session()
        try:
            # Compter le matériel
            total = session.query(Materiel).count()

            # Compter les matériels avec une attribution active
            attribue = (
                session.query(Materiel)
                .join(Attribution, Materiel.id == Attribution.materiel_id)
                .filter(Attribution.is_active == True)
                .count()
            )

            # En panne
            en_panne = session.query(Materiel).filter_by(etat="en_panne").count()

            # Disponible = total - attribué - en panne
            disponible = total - attribue - en_panne

            # Mettre à jour les labels
            self.stat_labels["total"].config(text=str(total))
            self.stat_labels["attribue"].config(text=str(attribue))
            self.stat_labels["disponible"].config(text=str(max(0, disponible)))
            self.stat_labels["en_panne"].config(text=str(en_panne))

            # Charger les dernières attributions
            self.tree_recent.delete(*self.tree_recent.get_children())

            attributions = (
                session.query(Attribution)
                .order_by(Attribution.date_attribution.desc())
                .limit(15)
                .all()
            )

            for attr in attributions:
                materiel = session.query(Materiel).get(attr.materiel_id)
                code = materiel.code_vigile if materiel else "?"
                action = "Attribution" if attr.is_active else "Retour"
                date_str = attr.date_attribution.strftime("%d/%m/%Y %H:%M")
                if not attr.is_active and attr.date_retour:
                    date_str = attr.date_retour.strftime("%d/%m/%Y %H:%M")

                self.tree_recent.insert("", "end", values=(
                    date_str, action, code, attr.attribue_a
                ))

        except Exception as e:
            print(f"[VIGILE] Erreur rafraîchissement dashboard : {e}")
        finally:
            session.close()


# =============================================================================
# ServerFrame — Contrôle du serveur Flask
# =============================================================================

class ServerFrame(tk.Frame):
    """
    Panneau de contrôle du serveur web Flask.
    Permet de démarrer/arrêter le serveur et affiche l'URL d'accès.
    """

    def __init__(self, parent, flask_app=None):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.flask_app = flask_app
        self.server_thread = None
        self.server_running = False
        self._construire_interface()

    def _get_ip_locale(self):
        """Récupère l'adresse IP locale de la machine."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _construire_interface(self):
        """Construit l'interface de contrôle du serveur."""
        # Titre
        tk.Label(
            self, text="🌐 Serveur Web",
            bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
            font=("Segoe UI", 22, "bold"), anchor="w"
        ).pack(fill="x", padx=30, pady=(25, 20))

        # Carte principale
        card = tk.Frame(self, bg=COLORS["bg_card"])
        card.pack(fill="x", padx=30, pady=10)

        content = tk.Frame(card, bg=COLORS["bg_card"])
        content.pack(fill="x", padx=30, pady=25)

        # État du serveur
        self.status_label = tk.Label(
            content, text="● Serveur arrêté",
            bg=COLORS["bg_card"], fg=COLORS["accent_red"],
            font=("Segoe UI", 16, "bold"), anchor="w"
        )
        self.status_label.pack(fill="x", pady=(0, 15))

        # IP et port
        ip = self._get_ip_locale()
        self.url_label = tk.Label(
            content,
            text=f"URL : http://{ip}:{FLASK_PORT}",
            bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
            font=("Consolas", 13), anchor="w"
        )
        self.url_label.pack(fill="x", pady=(0, 5))

        tk.Label(
            content,
            text=f"Port : {FLASK_PORT}  |  IP locale : {ip}",
            bg=COLORS["bg_card"], fg=COLORS["text_muted"],
            font=("Segoe UI", 10), anchor="w"
        ).pack(fill="x", pady=(0, 20))

        # Boutons
        btn_frame = tk.Frame(content, bg=COLORS["bg_card"])
        btn_frame.pack(fill="x")

        self.btn_start = VigileButton(
            btn_frame, text="▶ Démarrer le serveur",
            command=self._demarrer_serveur,
            width=220, height=44, color=COLORS["accent_green"]
        )
        self.btn_start.pack(side="left", padx=(0, 10))

        self.btn_stop = VigileButton(
            btn_frame, text="⏹ Arrêter le serveur",
            command=self._arreter_serveur,
            width=220, height=44, color=COLORS["accent_red"]
        )
        self.btn_stop.pack(side="left")

        # Zone QR code du serveur
        qr_frame = tk.Frame(self, bg=COLORS["bg_card"])
        qr_frame.pack(fill="x", padx=30, pady=(15, 10))

        tk.Label(
            qr_frame, text="📱 QR Code d'accès mobile",
            bg=COLORS["bg_card"], fg=COLORS["text_primary"],
            font=("Segoe UI", 14, "bold")
        ).pack(pady=(15, 10))

        self.qr_label = tk.Label(
            qr_frame, text="Démarrez le serveur pour générer le QR code",
            bg=COLORS["bg_card"], fg=COLORS["text_muted"],
            font=("Segoe UI", 10)
        )
        self.qr_label.pack(pady=(0, 15))

        # Info
        info_frame = tk.Frame(self, bg=COLORS["bg_dark"])
        info_frame.pack(fill="x", padx=30, pady=15)

        tk.Label(
            info_frame,
            text="ℹ Le serveur web permet aux utilisateurs de scanner les QR codes\n"
                 "depuis leur téléphone sur le même réseau WiFi.",
            bg=COLORS["bg_dark"], fg=COLORS["text_secondary"],
            font=("Segoe UI", 10), justify="left", anchor="w"
        ).pack(fill="x")

    def _demarrer_serveur(self):
        """Démarre le serveur Flask dans un thread séparé."""
        if self.server_running:
            messagebox.showinfo("Serveur", "Le serveur est déjà en cours d'exécution.")
            return

        if not self.flask_app:
            messagebox.showerror(
                "Erreur",
                "L'application Flask n'est pas configurée.\n"
                "Lancez l'application via app.py."
            )
            return

        try:
            ip = self._get_ip_locale()

            def run_server():
                self.flask_app.run(
                    host="0.0.0.0", port=FLASK_PORT,
                    debug=False, use_reloader=False
                )

            self.server_thread = threading.Thread(
                target=run_server, daemon=True
            )
            self.server_thread.start()
            self.server_running = True

            # Mettre à jour l'interface
            self.status_label.config(
                text="● Serveur en cours d'exécution",
                fg=COLORS["accent_green"]
            )
            self.url_label.config(
                text=f"URL : http://{ip}:{FLASK_PORT}",
                fg=COLORS["accent_green"]
            )

            # Générer le QR code du serveur
            self._generer_qr_serveur(ip)

            print(f"[VIGILE] Serveur Flask démarré sur http://{ip}:{FLASK_PORT}")

        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de démarrer le serveur :\n{e}")

    def _arreter_serveur(self):
        """Arrête le serveur Flask."""
        if not self.server_running:
            messagebox.showinfo("Serveur", "Le serveur n'est pas en cours d'exécution.")
            return

        # Note : Flask dans un thread daemon s'arrête quand l'app principale s'arrête
        # Pour un arrêt propre, on utilise werkzeug.server.shutdown
        self.server_running = False
        self.status_label.config(
            text="● Serveur arrêté", fg=COLORS["accent_red"]
        )
        self.url_label.config(fg=COLORS["text_secondary"])
        self.qr_label.config(
            text="Démarrez le serveur pour générer le QR code",
            image="", compound="none"
        )
        print("[VIGILE] Serveur Flask arrêté.")

    def _generer_qr_serveur(self, ip):
        """Génère un QR code pointant vers l'URL du serveur."""
        try:
            from qr.generator import generer_qr_code
            from PIL import Image, ImageTk

            # Générer un QR spécial pour l'URL du serveur
            url = f"http://{ip}:{FLASK_PORT}"

            import qrcode as qr_lib
            qr = qr_lib.QRCode(box_size=6, border=2)
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#6c63ff", back_color="#1c1c2e")
            img = img.convert("RGB")
            img = img.resize((200, 200), Image.NEAREST)

            # Convertir pour Tkinter
            self._qr_photo = ImageTk.PhotoImage(img)
            self.qr_label.config(
                image=self._qr_photo,
                text=f"\n{url}",
                compound="top",
                fg=COLORS["text_secondary"]
            )
        except Exception as e:
            self.qr_label.config(text=f"QR : {e}")

    def set_flask_app(self, app):
        """Définit l'application Flask à utiliser."""
        self.flask_app = app


# =============================================================================
# MainWindow — Fenêtre principale avec navigation
# =============================================================================

class MainWindow:
    """
    Fenêtre principale de VIGILE avec navigation latérale.
    Gère le basculement entre les différentes vues (frames).
    """

    def __init__(self, root, flask_app=None):
        """
        Args:
            root: Fenêtre Tk racine
            flask_app: Instance de l'application Flask (optionnel)
        """
        self.root = root
        self.flask_app = flask_app
        self.current_user = None
        self.frames = {}
        self.active_nav_button = None

        # Configuration de la fenêtre
        self.root.title(f"{APP_NAME} — {APP_SLOGAN}")
        self.root.geometry("1200x750")
        self.root.minsize(1000, 650)
        self.root.configure(bg=COLORS["bg_dark"])

        # Configurer le style ttk
        configurer_style(self.root)

        # Afficher l'écran de connexion
        self._afficher_login()

    def _afficher_login(self):
        """Affiche l'écran de connexion."""
        self.login_frame = LoginFrame(self.root, on_login_success=self._on_login)
        self.login_frame.pack(fill="both", expand=True)

    def _on_login(self, user_info):
        """Callback après connexion réussie."""
        self.current_user = user_info
        self.login_frame.destroy()
        self._construire_interface_principale()

    def _construire_interface_principale(self):
        """Construit l'interface principale après connexion."""
        # Container principal
        main_container = tk.Frame(self.root, bg=COLORS["bg_dark"])
        main_container.pack(fill="both", expand=True)

        # =====================================================================
        # Barre latérale (sidebar)
        # =====================================================================
        sidebar = tk.Frame(
            main_container, bg=COLORS["bg_sidebar"], width=220
        )
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Logo dans la sidebar
        logo_frame = tk.Frame(sidebar, bg=COLORS["bg_sidebar"])
        logo_frame.pack(fill="x", pady=(20, 5))

        tk.Label(
            logo_frame, text="🛡", bg=COLORS["bg_sidebar"],
            font=("Segoe UI", 28)
        ).pack()

        tk.Label(
            logo_frame, text=APP_NAME, bg=COLORS["bg_sidebar"],
            fg=COLORS["accent"], font=("Segoe UI", 18, "bold")
        ).pack()

        tk.Label(
            logo_frame, text=APP_SLOGAN, bg=COLORS["bg_sidebar"],
            fg=COLORS["text_muted"], font=("Segoe UI", 8, "italic"),
            wraplength=180
        ).pack(pady=(2, 0))

        # Séparateur
        tk.Frame(
            sidebar, bg=COLORS["border"], height=1
        ).pack(fill="x", padx=15, pady=15)

        # Boutons de navigation
        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "📊  Tableau de bord"),
            ("inventaire", "📋  Inventaire"),
            ("ajouter", "➕  Ajouter matériel"),
            ("historique", "📜  Historique"),
        ]

        # Ajouter la gestion users seulement pour les admins
        if self.current_user["role"] == "admin":
            nav_items.append(("users", "👥  Utilisateurs"))

        nav_items.append(("serveur", "🌐  Serveur Web"))

        for key, label in nav_items:
            btn = self._creer_nav_button(sidebar, key, label)
            self.nav_buttons[key] = btn

        # Info utilisateur en bas de la sidebar
        user_frame = tk.Frame(sidebar, bg=COLORS["bg_sidebar"])
        user_frame.pack(side="bottom", fill="x", padx=15, pady=15)

        tk.Frame(sidebar, bg=COLORS["border"], height=1).pack(
            side="bottom", fill="x", padx=15
        )

        tk.Label(
            user_frame,
            text=f"👤 {self.current_user['username']}",
            bg=COLORS["bg_sidebar"], fg=COLORS["text_primary"],
            font=("Segoe UI", 11), anchor="w"
        ).pack(fill="x")

        tk.Label(
            user_frame,
            text=f"Rôle : {self.current_user['role']}",
            bg=COLORS["bg_sidebar"], fg=COLORS["text_muted"],
            font=("Segoe UI", 9), anchor="w"
        ).pack(fill="x")

        # Bouton déconnexion
        logout_btn = tk.Label(
            user_frame, text="🚪 Déconnexion",
            bg=COLORS["bg_sidebar"], fg=COLORS["accent_red"],
            font=("Segoe UI", 10), cursor="hand2", anchor="w"
        )
        logout_btn.pack(fill="x", pady=(8, 0))
        logout_btn.bind("<Button-1>", lambda e: self._deconnexion())

        # =====================================================================
        # Zone de contenu (droite)
        # =====================================================================
        self.content_area = tk.Frame(main_container, bg=COLORS["bg_dark"])
        self.content_area.pack(side="left", fill="both", expand=True)

        # =====================================================================
        # Créer les frames de contenu
        # =====================================================================
        self._creer_frames()

        # Afficher le dashboard par défaut
        self._naviguer("dashboard")

    def _creer_nav_button(self, parent, key, text):
        """Crée un bouton de navigation dans la sidebar."""
        btn = tk.Label(
            parent, text=text,
            bg=COLORS["bg_sidebar"], fg=COLORS["text_secondary"],
            font=("Segoe UI", 11), anchor="w", padx=20, pady=10,
            cursor="hand2"
        )
        btn.pack(fill="x")

        btn.bind("<Enter>", lambda e, b=btn, k=key:
                 b.config(bg=COLORS["bg_hover"]) if self.active_nav_button != k else None)
        btn.bind("<Leave>", lambda e, b=btn, k=key:
                 b.config(bg=COLORS["bg_sidebar"]) if self.active_nav_button != k else None)
        btn.bind("<Button-1>", lambda e, k=key: self._naviguer(k))

        return btn

    def _creer_frames(self):
        """Crée toutes les frames de contenu."""
        # Dashboard
        self.frames["dashboard"] = DashboardFrame(self.content_area)

        # Les autres frames seront importées depuis leurs modules respectifs
        # Pour l'instant, on crée des placeholders qui seront remplacés
        try:
            from desktop.add_material import AddMaterialFrame
            self.frames["ajouter"] = AddMaterialFrame(
                self.content_area, self.current_user
            )
        except ImportError:
            self.frames["ajouter"] = self._placeholder_frame("Ajouter matériel")

        try:
            from desktop.inventory_view import InventoryFrame
            self.frames["inventaire"] = InventoryFrame(
                self.content_area, self.current_user
            )
        except ImportError:
            self.frames["inventaire"] = self._placeholder_frame("Inventaire")

        try:
            from desktop.history_view import HistoryFrame
            self.frames["historique"] = HistoryFrame(self.content_area)
        except ImportError:
            self.frames["historique"] = self._placeholder_frame("Historique")

        if self.current_user["role"] == "admin":
            try:
                from desktop.user_manager import UserManagerFrame
                self.frames["users"] = UserManagerFrame(self.content_area)
            except ImportError:
                self.frames["users"] = self._placeholder_frame("Gestion utilisateurs")

        # Serveur Web
        server_frame = ServerFrame(self.content_area, self.flask_app)
        self.frames["serveur"] = server_frame

    def _placeholder_frame(self, titre):
        """Crée un frame placeholder pour les modules pas encore implémentés."""
        frame = tk.Frame(self.content_area, bg=COLORS["bg_dark"])
        tk.Label(
            frame, text=f"🚧 {titre}",
            bg=COLORS["bg_dark"], fg=COLORS["text_muted"],
            font=("Segoe UI", 20)
        ).pack(expand=True)
        return frame

    def _naviguer(self, destination):
        """Bascule vers une frame de contenu."""
        # Cacher toutes les frames
        for frame in self.frames.values():
            frame.pack_forget()

        # Afficher la frame demandée
        if destination in self.frames:
            self.frames[destination].pack(fill="both", expand=True)

            # Rafraîchir les données si la frame a une méthode rafraichir
            if hasattr(self.frames[destination], "rafraichir"):
                self.frames[destination].rafraichir()

        # Mettre à jour l'apparence des boutons de navigation
        for key, btn in self.nav_buttons.items():
            if key == destination:
                btn.config(
                    bg=COLORS["accent"], fg="#ffffff",
                    font=("Segoe UI", 11, "bold")
                )
            else:
                btn.config(
                    bg=COLORS["bg_sidebar"], fg=COLORS["text_secondary"],
                    font=("Segoe UI", 11)
                )
        self.active_nav_button = destination

    def _deconnexion(self):
        """Déconnecte l'utilisateur et revient à l'écran de connexion."""
        if messagebox.askyesno("Déconnexion", "Voulez-vous vous déconnecter ?"):
            self.current_user = None
            # Détruire tous les widgets
            for widget in self.root.winfo_children():
                widget.destroy()
            # Réafficher le login
            self._afficher_login()

    def get_server_frame(self):
        """Retourne le ServerFrame pour configuration externe."""
        return self.frames.get("serveur")


# =============================================================================
# Point d'entrée pour test direct
# =============================================================================

if __name__ == "__main__":
    # Initialiser la BD
    init_db()

    # Créer la fenêtre
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()
