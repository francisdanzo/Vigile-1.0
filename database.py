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

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import (
    ADMIN_DEFAULT,
    DATA_DIR,
    DATABASE_PATH,
    SQLALCHEMY_DATABASE_URI,
    ensure_runtime_dirs,
)
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
    1. Crée toutes les tables définies dans models.py
    2. Crée le répertoire pour les QR codes s'il n'existe pas
    3. Crée le compte admin par défaut si aucun utilisateur n'existe
    """
    ensure_runtime_dirs()
    print(f"[VIGILE] Répertoire de données : {DATA_DIR}")

    # Créer toutes les tables
    Base.metadata.create_all(bind=engine)
    print("[VIGILE] Tables de la base de données créées avec succès.")
    print(f"[VIGILE] Base de données prête : {DATABASE_PATH}")

    # Créer l'admin par défaut si la BD est vide
    _creer_admin_par_defaut()


def _creer_admin_par_defaut() -> None:
    """
    Crée le compte administrateur par défaut si aucun utilisateur
    n'existe dans la base. Ceci permet un premier accès au système.
    """
    session = SessionLocal()
    try:
        # Vérifier s'il existe déjà des utilisateurs
        nombre_users = session.query(User).count()
        if nombre_users > 0:
            print("[VIGILE] Des utilisateurs existent déjà, pas de création admin.")
            return

        # Créer l'administrateur par défaut
        admin = User(
            username=ADMIN_DEFAULT["username"],
            email=ADMIN_DEFAULT["email"],
            role=ADMIN_DEFAULT["role"],
            is_active=True
        )
        admin.set_password(ADMIN_DEFAULT["password"])

        session.add(admin)
        session.commit()
        print(
            f"[VIGILE] Compte admin créé : "
            f"username='{ADMIN_DEFAULT['username']}'"
        )
        print("[VIGILE] ⚠ Changez ce mot de passe après la première connexion !")

    except Exception as e:
        session.rollback()
        print(f"[VIGILE] Erreur lors de la création de l'admin : {e}")
        raise
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
