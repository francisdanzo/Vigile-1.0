# -*- coding: utf-8 -*-
"""
VIGILE — Configuration globale
"Chaque équipement a sa sentinelle"

Ce fichier centralise toutes les constantes et paramètres
de configuration utilisés par l'application.
"""

import os
import secrets
import sys

# =============================================================================
# Chemins de base et gestion PyInstaller
# =============================================================================

APP_NAME = "VIGILE"
APP_VERSION = "1.0.0"
APP_SLOGAN = "Chaque équipement a sa sentinelle"
APP_SLUG = "Vigile"


def get_resource_path(relative_path):
    """
    Récupère le chemin absolu d'une ressource, fonctionne en mode dev
    et pour PyInstaller (qui extrait les fichiers dans un dossier temporaire).
    """
    try:
        # PyInstaller crée un dossier temporaire et stocke le chemin dans _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)

# Répertoire des ressources (templates, binaires embarqués)
# Ces fichiers sont inclus dans le package (.exe)
RES_DIR = get_resource_path("")
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


def _get_default_data_dir() -> str:
    """
    Retourne le répertoire de données utilisateur selon la plateforme.

    Un override explicite reste possible via la variable d'environnement
    VIGILE_DATA_DIR, utile pour le debug ou les tests.
    """
    env_override = os.environ.get("VIGILE_DATA_DIR")
    if env_override:
        return os.path.abspath(env_override)

    home_dir = os.path.expanduser("~")

    if sys.platform.startswith("win"):
        appdata_dir = os.environ.get("APPDATA")
        if not appdata_dir:
            appdata_dir = os.path.join(home_dir, "AppData", "Roaming")
        return os.path.join(appdata_dir, APP_SLUG)

    if sys.platform == "darwin":
        return os.path.join(home_dir, "Library", "Application Support", APP_SLUG)

    xdg_data_home = os.environ.get(
        "XDG_DATA_HOME", os.path.join(home_dir, ".local", "share")
    )
    return os.path.join(xdg_data_home, APP_SLUG.lower())


DATA_DIR = _get_default_data_dir()
ASSETS_DIR = os.path.join(DATA_DIR, "assets")
QR_CODES_DIR = os.path.join(ASSETS_DIR, "qr_codes")
LOGS_DIR = os.path.join(DATA_DIR, "logs")
DATABASE_PATH = os.path.join(DATA_DIR, "vigile.db")


def ensure_runtime_dirs() -> None:
    """Crée l'arborescence runtime nécessaire à l'application."""
    for path in (DATA_DIR, ASSETS_DIR, QR_CODES_DIR, LOGS_DIR):
        os.makedirs(path, exist_ok=True)

# URI SQLAlchemy pour la connexion à la base
SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"

# =============================================================================
# Configuration Flask
# =============================================================================

# Port par défaut du serveur web Flask
FLASK_PORT = 5000

# Clé secrète pour les sessions Flask
# Générée aléatoirement au premier import, persiste tant que l'app tourne
SECRET_KEY = secrets.token_hex(32)

# Désactiver le mode debug en production
FLASK_DEBUG = False

# =============================================================================
# Compte administrateur par défaut
# Créé automatiquement au premier lancement si la BD est vide
# =============================================================================

ADMIN_DEFAULT = {
    "username": "admin",
    "email": "admin@vigile.local",
    "password": "admin123",
    "role": "admin"
}

# =============================================================================
# Format du code VIGILE
# Exemple : VIG-2026-0001
# =============================================================================

CODE_VIGILE_PREFIX = "VIG"

# =============================================================================
# Types, états et emplacements autorisés pour le matériel
# Utilisés pour la validation et les menus déroulants
# =============================================================================

TYPES_MATERIEL = [
    "ordinateur",
    "clavier",
    "souris",
    "écran",
    "imprimante",
    "câble",
    "accessoire",
    "autre"
]

ETATS_MATERIEL = [
    "neuf",
    "bon",
    "usagé",
    "en_panne"
]

EMPLACEMENTS_MATERIEL = [
    "bureau",
    "salle_serveur",
    "réserve",
    "attribué",
    "autre"
]

# =============================================================================
# Rôles utilisateurs
# =============================================================================

ROLES_UTILISATEUR = [
    "admin",
    "gestionnaire"
]

# =============================================================================
# Paramètres QR Code
# =============================================================================

# Taille du QR code (box_size en pixels par module)
QR_BOX_SIZE = 10

# Bordure autour du QR code (en modules)
QR_BORDER = 4

# =============================================================================
# Nom et slogan de l'application
# =============================================================================
