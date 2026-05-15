# -*- coding: utf-8 -*-
"""
VIGILE — Initialisation de la base de données
"Chaque équipement a sa sentinelle"

Ce module gère :
- La création du moteur SQLAlchemy (SQLite)
- La factory de sessions
- L'initialisation des tables
- La création du compte admin par défaut au premier lancement
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import SQLALCHEMY_DATABASE_URI, QR_CODES_DIR, DATA_DIR
from models import Base, User


# =============================================================================
# Moteur SQLAlchemy
# =============================================================================

# Création du moteur SQLite
# check_same_thread=False est nécessaire car Flask et Tkinter
# utilisent des threads différents
engine = create_engine(
    SQLALCHEMY_DATABASE_URI,
    echo=False,  # Mettre à True pour voir les requêtes SQL en debug
    connect_args={"check_same_thread": False}
)

# =============================================================================
# Factory de sessions
# =============================================================================

# Chaque opération BD doit utiliser une session obtenue via SessionLocal()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# =============================================================================
# Fonctions d'initialisation
# =============================================================================

def init_db() -> None:
    """
    Initialise la base de données :
    1. Crée le dossier de données utilisateur
    2. Crée toutes les tables définies dans models.py
    3. Crée le répertoire pour les QR codes s'il n'existe pas
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    print("[VIGILE] Tables de la base de données créées avec succès.")
    os.makedirs(QR_CODES_DIR, exist_ok=True)
    print(f"[VIGILE] Répertoire QR codes vérifié : {QR_CODES_DIR}")


def is_first_launch() -> bool:
    """Retourne True si aucun utilisateur n'existe encore en base."""
    session = SessionLocal()
    try:
        return session.query(User).count() == 0
    finally:
        session.close()


def get_session():
    """
    Crée et retourne une nouvelle session de base de données.
    
    Utilisation recommandée avec un context manager :
        session = get_session()
        try:
            # ... opérations BD ...
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    """
    return SessionLocal()


# =============================================================================
# Point d'entrée pour test direct
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("VIGILE — Initialisation de la base de données")
    print("=" * 60)
    init_db()
    print("\n[VIGILE] Base de données initialisée avec succès !")
    print(f"[VIGILE] Fichier BD : {SQLALCHEMY_DATABASE_URI}")
