# -*- coding: utf-8 -*-
"""
VIGILE — Formulaire d'ajout de matériel
"Chaque équipement a sa sentinelle"

Ce module contient le formulaire complet pour ajouter un nouveau
matériel à l'inventaire. Il génère automatiquement le code VIGILE
et le QR code associé.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timezone

# Ajouter le répertoire racine au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importer les couleurs et widgets depuis main_window
try:
    from desktop.main_window import COLORS, VigileButton, VigileEntry
except ImportError:
    # Fallback si exécuté directement
    COLORS = {
        "bg_dark": "#0f0f1a", "bg_sidebar": "#161625", "bg_card": "#1c1c2e",
        "bg_input": "#252540", "bg_hover": "#2a2a45", "accent": "#6c63ff",
        "accent_hover": "#5a52d5", "accent_green": "#00c896",
        "accent_orange": "#ff9f43", "accent_red": "#ff6b6b",
        "accent_blue": "#54a0ff", "text_primary": "#e8e8e8",
        "text_secondary": "#8888a0", "text_muted": "#555570",
        "border": "#2a2a45", "gold": "#ffd700",
    }

from config import TYPES_MATERIEL, ETATS_MATERIEL, EMPLACEMENTS_MATERIEL
from database import get_session
from models import Materiel
from qr.generator import generer_qr_code, generer_code_vigile


# =============================================================================
# AddMaterialFrame — Formulaire d'ajout de matériel
# =============================================================================

class AddMaterialFrame(tk.Frame):
    """
    Formulaire complet pour ajouter un nouveau matériel.
    
    Fonctionnalités :
    - Génération automatique du code VIGILE (VIG-YYYY-NNNN)
    - Tous les champs du modèle Materiel
    - Validation des champs obligatoires
    - Génération QR à la sauvegarde
    - Aperçu du QR code dans le formulaire
    """

    def __init__(self, parent, current_user):
        """
        Args:
            parent: Widget parent
            current_user: Dict avec les infos de l'utilisateur connecté
        """
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.current_user = current_user
        self.qr_photo = None  # Référence pour empêcher le garbage collection
        self._construire_interface()

    def _construire_interface(self):
        """Construit le formulaire d'ajout."""
        # Conteneur scrollable
        canvas = tk.Canvas(self, bg=COLORS["bg_dark"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=canvas.yview,
            style="Vigile.Vertical.TScrollbar"
        )
        self.scroll_frame = tk.Frame(canvas, bg=COLORS["bg_dark"])

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Scroll avec la molette
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def on_mousewheel_linux(event):
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

        canvas.bind_all("<MouseWheel>", on_mousewheel)
        canvas.bind_all("<Button-4>", on_mousewheel_linux)
        canvas.bind_all("<Button-5>", on_mousewheel_linux)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # =====================================================================
        # En-tête
        # =====================================================================
        header = tk.Frame(self.scroll_frame, bg=COLORS["bg_dark"])
        header.pack(fill="x", padx=30, pady=(25, 15))

        tk.Label(
            header, text="➕ Ajouter un matériel",
            bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
            font=("Segoe UI", 22, "bold"), anchor="w"
        ).pack(side="left")

        # =====================================================================
        # Layout : formulaire à gauche, aperçu QR à droite
        # =====================================================================
        body = tk.Frame(self.scroll_frame, bg=COLORS["bg_dark"])
        body.pack(fill="both", expand=True, padx=30)

        # Colonne formulaire (gauche)
        form_col = tk.Frame(body, bg=COLORS["bg_dark"])
        form_col.pack(side="left", fill="both", expand=True, padx=(0, 15))

        # Colonne aperçu QR (droite)
        qr_col = tk.Frame(body, bg=COLORS["bg_dark"], width=280)
        qr_col.pack(side="right", fill="y", padx=(15, 0))
        qr_col.pack_propagate(False)

        # =====================================================================
        # Formulaire — Section Identification
        # =====================================================================
        self._section_titre(form_col, "🏷 Identification")
        id_card = self._creer_carte(form_col)

        # Code VIGILE (auto-généré)
        self.code_var = tk.StringVar(value="Sera généré automatiquement")
        code_frame = tk.Frame(id_card, bg=COLORS["bg_card"])
        code_frame.pack(fill="x", pady=(0, 12))

        tk.Label(
            code_frame, text="Code VIGILE", bg=COLORS["bg_card"],
            fg=COLORS["text_secondary"], font=("Segoe UI", 10), anchor="w"
        ).pack(fill="x")

        code_display = tk.Label(
            code_frame, textvariable=self.code_var,
            bg=COLORS["bg_input"], fg=COLORS["accent"],
            font=("Consolas", 13, "bold"), anchor="w",
            padx=10, pady=8, relief="flat"
        )
        code_display.pack(fill="x", pady=(4, 0))

        # Type de matériel
        type_frame = tk.Frame(id_card, bg=COLORS["bg_card"])
        type_frame.pack(fill="x", pady=(0, 12))

        tk.Label(
            type_frame, text="Type de matériel *", bg=COLORS["bg_card"],
            fg=COLORS["text_secondary"], font=("Segoe UI", 10), anchor="w"
        ).pack(fill="x")

        self.type_combo = ttk.Combobox(
            type_frame, values=TYPES_MATERIEL, state="readonly",
            font=("Segoe UI", 11)
        )
        self.type_combo.pack(fill="x", pady=(4, 0))
        self.type_combo.set("ordinateur")

        # Marque
        self.marque_field = self._creer_champ(id_card, "Marque", "Ex: Dell, HP, Lenovo...")

        # Modèle
        self.modele_field = self._creer_champ(id_card, "Modèle", "Ex: Latitude 5540")

        # Numéro de série
        self.serie_field = self._creer_champ(id_card, "Numéro de série", "Ex: SN-ABC123456")

        # =====================================================================
        # Formulaire — Section État et Localisation
        # =====================================================================
        self._section_titre(form_col, "📍 État et localisation")
        etat_card = self._creer_carte(form_col)

        # État
        etat_frame = tk.Frame(etat_card, bg=COLORS["bg_card"])
        etat_frame.pack(fill="x", pady=(0, 12))

        tk.Label(
            etat_frame, text="État *", bg=COLORS["bg_card"],
            fg=COLORS["text_secondary"], font=("Segoe UI", 10), anchor="w"
        ).pack(fill="x")

        self.etat_combo = ttk.Combobox(
            etat_frame, values=ETATS_MATERIEL, state="readonly",
            font=("Segoe UI", 11)
        )
        self.etat_combo.pack(fill="x", pady=(4, 0))
        self.etat_combo.set("neuf")

        # Emplacement
        empl_frame = tk.Frame(etat_card, bg=COLORS["bg_card"])
        empl_frame.pack(fill="x", pady=(0, 12))

        tk.Label(
            empl_frame, text="Emplacement *", bg=COLORS["bg_card"],
            fg=COLORS["text_secondary"], font=("Segoe UI", 10), anchor="w"
        ).pack(fill="x")

        self.empl_combo = ttk.Combobox(
            empl_frame, values=EMPLACEMENTS_MATERIEL, state="readonly",
            font=("Segoe UI", 11)
        )
        self.empl_combo.pack(fill="x", pady=(4, 0))
        self.empl_combo.set("réserve")

        # Date d'acquisition
        self.date_field = self._creer_champ(
            etat_card, "Date d'acquisition",
            datetime.now().strftime("%d/%m/%Y")
        )

        # =====================================================================
        # Formulaire — Section Notes
        # =====================================================================
        self._section_titre(form_col, "📝 Notes")
        notes_card = self._creer_carte(form_col)

        tk.Label(
            notes_card, text="Notes et commentaires", bg=COLORS["bg_card"],
            fg=COLORS["text_secondary"], font=("Segoe UI", 10), anchor="w"
        ).pack(fill="x")

        self.notes_text = tk.Text(
            notes_card, height=4, bg=COLORS["bg_input"],
            fg=COLORS["text_primary"], insertbackground=COLORS["accent"],
            font=("Segoe UI", 11), relief="flat", bd=8,
            highlightbackground=COLORS["border"],
            highlightthickness=1, highlightcolor=COLORS["accent"]
        )
        self.notes_text.pack(fill="x", pady=(4, 0))

        # =====================================================================
        # Boutons d'action
        # =====================================================================
        btn_frame = tk.Frame(form_col, bg=COLORS["bg_dark"])
        btn_frame.pack(fill="x", pady=(20, 30))

        VigileButton(
            btn_frame, text="💾 Sauvegarder", command=self._sauvegarder,
            width=200, height=44, color=COLORS["accent_green"]
        ).pack(side="left", padx=(0, 10))

        VigileButton(
            btn_frame, text="🔄 Réinitialiser", command=self._reinitialiser,
            width=180, height=44, color=COLORS["bg_card"]
        ).pack(side="left")

        # =====================================================================
        # Zone aperçu QR (colonne droite)
        # =====================================================================
        qr_card = tk.Frame(
            qr_col, bg=COLORS["bg_card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )
        qr_card.pack(fill="x", pady=(42, 0))

        tk.Label(
            qr_card, text="📱 Aperçu QR Code",
            bg=COLORS["bg_card"], fg=COLORS["text_primary"],
            font=("Segoe UI", 13, "bold")
        ).pack(pady=(15, 10))

        self.qr_preview_label = tk.Label(
            qr_card,
            text="Le QR code sera généré\naprès la sauvegarde",
            bg=COLORS["bg_card"], fg=COLORS["text_muted"],
            font=("Segoe UI", 10), justify="center"
        )
        self.qr_preview_label.pack(pady=(10, 15), padx=15)

        # Info sous l'aperçu
        info_card = tk.Frame(qr_col, bg=COLORS["bg_card"])
        info_card.pack(fill="x", pady=(15, 0))

        tk.Label(
            info_card,
            text="ℹ Le QR code encode l'URL\ndu serveur web VIGILE.\n\n"
                 "Scannez-le avec un\ntéléphone pour accéder\n"
                 "à la fiche du matériel.",
            bg=COLORS["bg_card"], fg=COLORS["text_muted"],
            font=("Segoe UI", 9), justify="center"
        ).pack(pady=15, padx=10)

        # Générer le prochain code VIGILE
        self._rafraichir_code()

    def _section_titre(self, parent, texte):
        """Ajoute un titre de section."""
        tk.Label(
            parent, text=texte, bg=COLORS["bg_dark"],
            fg=COLORS["text_primary"], font=("Segoe UI", 14, "bold"),
            anchor="w"
        ).pack(fill="x", pady=(18, 8))

    def _creer_carte(self, parent):
        """Crée une carte (cadre) pour regrouper des champs."""
        card = tk.Frame(
            parent, bg=COLORS["bg_card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )
        card.pack(fill="x", pady=(0, 5))

        inner = tk.Frame(card, bg=COLORS["bg_card"])
        inner.pack(fill="x", padx=20, pady=15)
        return inner

    def _creer_champ(self, parent, label, placeholder=""):
        """Crée un champ de saisie avec label."""
        frame = tk.Frame(parent, bg=COLORS["bg_card"])
        frame.pack(fill="x", pady=(0, 12))

        tk.Label(
            frame, text=label, bg=COLORS["bg_card"],
            fg=COLORS["text_secondary"], font=("Segoe UI", 10), anchor="w"
        ).pack(fill="x")

        entry_container = tk.Frame(
            frame, bg=COLORS["bg_input"],
            highlightbackground=COLORS["border"],
            highlightthickness=1, highlightcolor=COLORS["accent"]
        )
        entry_container.pack(fill="x", pady=(4, 0))

        entry = tk.Entry(
            entry_container, bg=COLORS["bg_input"],
            fg=COLORS["text_primary"], insertbackground=COLORS["accent"],
            font=("Segoe UI", 11), relief="flat", bd=8
        )
        entry.pack(fill="x")

        # Placeholder
        if placeholder:
            entry._placeholder = placeholder
            entry.insert(0, placeholder)
            entry.config(fg=COLORS["text_muted"])

            def on_focus_in(e):
                if entry.get() == entry._placeholder:
                    entry.delete(0, "end")
                    entry.config(fg=COLORS["text_primary"])

            def on_focus_out(e):
                if not entry.get():
                    entry.insert(0, entry._placeholder)
                    entry.config(fg=COLORS["text_muted"])

            entry.bind("<FocusIn>", on_focus_in)
            entry.bind("<FocusOut>", on_focus_out)

        return entry

    def _get_field_value(self, entry):
        """Retourne la valeur d'un champ (ignore le placeholder)."""
        val = entry.get()
        if hasattr(entry, "_placeholder") and val == entry._placeholder:
            return ""
        return val.strip()

    def _rafraichir_code(self):
        """Génère et affiche le prochain code VIGILE disponible."""
        session = get_session()
        try:
            code = generer_code_vigile(session)
            self.code_var.set(code)
        except Exception as e:
            self.code_var.set(f"Erreur : {e}")
        finally:
            session.close()

    def _sauvegarder(self):
        """Sauvegarde le matériel dans la base de données."""
        # Validation
        type_mat = self.type_combo.get()
        etat = self.etat_combo.get()
        emplacement = self.empl_combo.get()

        if not type_mat:
            messagebox.showwarning("Validation", "Veuillez sélectionner un type de matériel.")
            return
        if not etat:
            messagebox.showwarning("Validation", "Veuillez sélectionner un état.")
            return
        if not emplacement:
            messagebox.showwarning("Validation", "Veuillez sélectionner un emplacement.")
            return

        # Récupérer les valeurs
        marque = self._get_field_value(self.marque_field)
        modele = self._get_field_value(self.modele_field)
        numero_serie = self._get_field_value(self.serie_field)
        date_acq_str = self._get_field_value(self.date_field)
        notes = self.notes_text.get("1.0", "end").strip()

        # Parser la date d'acquisition
        date_acquisition = None
        if date_acq_str:
            try:
                date_acquisition = datetime.strptime(date_acq_str, "%d/%m/%Y")
                date_acquisition = date_acquisition.replace(tzinfo=timezone.utc)
            except ValueError:
                messagebox.showwarning(
                    "Validation",
                    "Format de date invalide. Utilisez JJ/MM/AAAA."
                )
                return

        session = get_session()
        try:
            # Générer le code VIGILE
            code_vigile = generer_code_vigile(session)

            # Créer le matériel
            materiel = Materiel(
                code_vigile=code_vigile,
                type=type_mat,
                marque=marque if marque else None,
                modele=modele if modele else None,
                numero_serie=numero_serie if numero_serie else None,
                etat=etat,
                emplacement=emplacement,
                date_acquisition=date_acquisition,
                notes=notes if notes else None,
                created_by=self.current_user["id"]
            )

            session.add(materiel)
            session.flush()  # Pour obtenir l'ID

            # Générer le QR code
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
            except Exception:
                ip = "127.0.0.1"

            qr_path = generer_qr_code(code_vigile, host=ip)
            materiel.qr_code_path = qr_path

            session.commit()

            # Afficher l'aperçu du QR code
            self._afficher_qr_preview(qr_path, code_vigile)

            messagebox.showinfo(
                "Succès",
                f"Matériel enregistré avec succès !\n\n"
                f"Code : {code_vigile}\n"
                f"Type : {type_mat}\n"
                f"QR code : {os.path.basename(qr_path)}"
            )

            # Préparer pour le prochain ajout
            self._reinitialiser()

        except Exception as e:
            session.rollback()
            messagebox.showerror(
                "Erreur",
                f"Impossible d'enregistrer le matériel :\n{e}"
            )
            import traceback
            traceback.print_exc()
        finally:
            session.close()

    def _afficher_qr_preview(self, qr_path, code_vigile):
        """Affiche l'aperçu du QR code dans le formulaire."""
        try:
            from PIL import Image, ImageTk

            # Charger et redimensionner l'image QR
            img = Image.open(qr_path)
            # Calculer la taille proportionnelle
            max_size = 220
            ratio = min(max_size / img.width, max_size / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

            # Convertir pour Tkinter
            self.qr_photo = ImageTk.PhotoImage(img)
            self.qr_preview_label.config(
                image=self.qr_photo,
                text=f"\n{code_vigile}",
                compound="top",
                fg=COLORS["accent"],
                font=("Consolas", 11, "bold")
            )
        except Exception as e:
            self.qr_preview_label.config(
                text=f"QR généré : {code_vigile}\n(Aperçu non disponible)",
                fg=COLORS["accent"]
            )

    def _reinitialiser(self):
        """Réinitialise tous les champs du formulaire."""
        self.type_combo.set("ordinateur")
        self.etat_combo.set("neuf")
        self.empl_combo.set("réserve")

        for field in [self.marque_field, self.modele_field,
                      self.serie_field, self.date_field]:
            field.delete(0, "end")
            if hasattr(field, "_placeholder"):
                field.insert(0, field._placeholder)
                field.config(fg=COLORS["text_muted"])

        self.notes_text.delete("1.0", "end")

        # Réinitialiser l'aperçu QR
        self.qr_photo = None
        self.qr_preview_label.config(
            image="",
            text="Le QR code sera généré\naprès la sauvegarde",
            compound="none",
            fg=COLORS["text_muted"],
            font=("Segoe UI", 10)
        )

        # Rafraîchir le code VIGILE
        self._rafraichir_code()

    def rafraichir(self):
        """Appelé quand on navigue vers cette vue."""
        self._rafraichir_code()


# =============================================================================
# Point d'entrée pour test direct
# =============================================================================

if __name__ == "__main__":
    from database import init_db
    init_db()

    root = tk.Tk()
    root.title("VIGILE — Test Ajout Matériel")
    root.geometry("900x700")
    root.configure(bg=COLORS["bg_dark"])

    # Simuler un utilisateur connecté
    user = {"id": 1, "username": "admin", "role": "admin"}

    from desktop.main_window import configurer_style
    configurer_style(root)

    frame = AddMaterialFrame(root, user)
    frame.pack(fill="both", expand=True)

    root.mainloop()
