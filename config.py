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
# Chemins de base et Persistance
# =============================================================================

# Répertoire racine de l'exécutable ou du script
if getattr(sys, 'frozen', False):
    # Si l'application est "gelée" par PyInstaller
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Répertoire de données utilisateur (Peut être différent sur Windows/Linux)
# On utilise un dossier caché dans le répertoire personnel de l'utilisateur
DATA_DIR = os.path.join(os.path.expanduser("~"), ".vigile")

# Répertoire de stockage des QR codes générés
QR_CODES_DIR = os.path.join(DATA_DIR, "assets", "qr_codes")

# Chemin de la base de données SQLite
DATABASE_PATH = os.path.join(DATA_DIR, "vigile.db")

# URI SQLAlchemy pour la connexion à la base
SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"

# =============================================================================
# Configuration Flask
# =============================================================================

# Port par défaut du serveur web Flask
FLASK_PORT = 5000

# Clé secrète pour les sessions Flask
# Chargée depuis le disque (ou créée au premier lancement) pour que les sessions
# restent valides entre les redémarrages de l'application.
def _load_secret_key() -> str:
    key_file = os.path.join(DATA_DIR, ".secret_key")
    if os.path.exists(key_file):
        with open(key_file, "r") as _f:
            key = _f.read().strip()
            if key:
                return key
    key = secrets.token_hex(32)
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(key_file, "w") as _f:
        _f.write(key)
    return key

SECRET_KEY = _load_secret_key()

# Désactiver le mode debug en production
FLASK_DEBUG = False

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
# Politique de mot de passe
# =============================================================================

PASSWORD_MIN_LENGTH = 8

# =============================================================================
# Alertes d'attributions
# =============================================================================

# Nombre de jours au-delà duquel une attribution active est considérée "longue"
ATTRIBUTION_ALERTE_JOURS = 30

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

APP_NAME = "VIGILE"
APP_SLOGAN = "Chaque équipement a sa sentinelle"
APP_VERSION = "1.1.0"
