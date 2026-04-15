# -*- coding: utf-8 -*-
"""
VIGILE — Configuration globale
"Chaque équipement a sa sentinelle"

Ce fichier centralise toutes les constantes et paramètres
de configuration utilisés par l'application.
"""

import os
import secrets

# =============================================================================
# Chemins de base
# =============================================================================

# Répertoire racine du projet (là où se trouve ce fichier)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Répertoire de stockage des QR codes générés
QR_CODES_DIR = os.path.join(BASE_DIR, "assets", "qr_codes")

# Chemin de la base de données SQLite
DATABASE_PATH = os.path.join(BASE_DIR, "vigile.db")

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

APP_NAME = "VIGILE"
APP_SLOGAN = "Chaque équipement a sa sentinelle"
APP_VERSION = "1.0.0"
