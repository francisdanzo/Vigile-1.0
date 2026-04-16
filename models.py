# -*- coding: utf-8 -*-
"""
VIGILE — Modèles de données SQLAlchemy
"Chaque équipement a sa sentinelle"

Définit les trois tables principales :
- User : utilisateurs du système (admin, gestionnaire)
- Materiel : équipements informatiques suivis
- Attribution : historique d'attribution du matériel aux personnes
"""

import os
from datetime import datetime, timezone

import bcrypt
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


# =============================================================================
# Classe de base SQLAlchemy (style moderne 2.0)
# =============================================================================

class Base(DeclarativeBase):
    """Classe de base pour tous les modèles SQLAlchemy."""
    pass


# =============================================================================
# Modèle : User (utilisateurs du système)
# =============================================================================

class User(Base):
    """
    Représente un utilisateur de VIGILE.
    
    Rôles possibles :
    - admin : accès complet (gestion users, matériel, attributions)
    - gestionnaire : gestion matériel et attributions uniquement
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="gestionnaire")
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    is_active = Column(Boolean, nullable=False, default=True)

    # Relations
    materiels_crees = relationship(
        "Materiel", back_populates="createur", lazy="dynamic"
    )
    attributions_faites = relationship(
        "Attribution", back_populates="attribueur", lazy="dynamic"
    )

    def set_password(self, password: str) -> None:
        """Hash le mot de passe avec bcrypt et le stocke."""
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password_bytes, salt).decode("utf-8")

    def check_password(self, password: str) -> bool:
        """Vérifie un mot de passe contre le hash stocké."""
        password_bytes = password.encode("utf-8")
        hash_bytes = self.password_hash.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hash_bytes)

    @property
    def is_admin(self) -> bool:
        """Retourne True si l'utilisateur est administrateur."""
        return self.role == "admin"

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


# =============================================================================
# Modèle : Materiel (équipements informatiques)
# =============================================================================

class Materiel(Base):
    """
    Représente un équipement informatique suivi par VIGILE.
    
    Chaque matériel a un code unique (VIG-YYYY-NNNN) et un QR code associé.
    """
    __tablename__ = "materiels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Code unique VIGILE (ex: VIG-2026-0001)
    code_vigile = Column(String(20), unique=True, nullable=False, index=True)
    
    # Chemin vers le fichier QR code PNG
    qr_code_path = Column(String(255), nullable=True)
    
    # Caractéristiques du matériel
    type = Column(String(50), nullable=False)  # ordinateur, clavier, souris, etc.
    marque = Column(String(100), nullable=True)
    modele = Column(String(100), nullable=True)
    numero_serie = Column(String(100), nullable=True)
    
    # État et localisation
    etat = Column(String(20), nullable=False, default="neuf")
    emplacement = Column(String(50), nullable=False, default="réserve")
    
    # Dates et métadonnées
    date_acquisition = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relations
    createur = relationship("User", back_populates="materiels_crees")
    attributions = relationship(
        "Attribution",
        back_populates="materiel",
        lazy="dynamic",
        order_by="Attribution.date_attribution.desc()"
    )

    @property
    def attribution_active(self):
        """Retourne l'attribution en cours, ou None si le matériel est libre."""
        return self.attributions.filter_by(is_active=True).first()

    @property
    def est_attribue(self) -> bool:
        """Retourne True si le matériel est actuellement attribué à quelqu'un."""
        return self.attribution_active is not None

    @property
    def qr_code_filename(self) -> str | None:
        """Retourne le nom de fichier du QR, compatible Unix/Windows."""
        if not self.qr_code_path:
            return None
        return os.path.basename(self.qr_code_path.replace("\\", "/"))

    def __repr__(self) -> str:
        return (
            f"<Materiel(id={self.id}, code='{self.code_vigile}', "
            f"type='{self.type}', etat='{self.etat}')>"
        )


# =============================================================================
# Modèle : Attribution (historique d'attribution du matériel)
# =============================================================================

class Attribution(Base):
    """
    Représente une attribution de matériel à une personne.
    
    Une attribution active (is_active=True) signifie que la personne
    possède actuellement le matériel. Quand le matériel est récupéré,
    date_retour est renseigné et is_active passe à False.
    """
    __tablename__ = "attributions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Matériel attribué
    materiel_id = Column(
        Integer, ForeignKey("materiels.id"), nullable=False, index=True
    )
    
    # Personne à qui le matériel est attribué (texte libre)
    attribue_a = Column(String(150), nullable=False)
    
    # Dates
    date_attribution = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    date_retour = Column(DateTime, nullable=True)  # None = pas encore retourné
    
    # Qui a fait l'attribution (utilisateur VIGILE)
    attribue_par = Column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    
    # Notes optionnelles
    notes = Column(Text, nullable=True)
    
    # True = attribution en cours, False = matériel rendu
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    # Relations
    materiel = relationship("Materiel", back_populates="attributions")
    attribueur = relationship("User", back_populates="attributions_faites")

    def retourner(self) -> None:
        """Marque le matériel comme retourné (fin d'attribution)."""
        self.date_retour = datetime.now(timezone.utc)
        self.is_active = False

    def __repr__(self) -> str:
        statut = "active" if self.is_active else "terminée"
        return (
            f"<Attribution(id={self.id}, materiel_id={self.materiel_id}, "
            f"à='{self.attribue_a}', {statut})>"
        )
