# -*- coding: utf-8 -*-
"""
VIGILE — Authentification Flask
"Chaque équipement a sa sentinelle"

Configuration de Flask-Login pour l'authentification web :
- Wrapper FlaskUser compatible Flask-Login
- User loader
- Routes de login/logout
"""

import os
import sys

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_session
from models import User

# =============================================================================
# Blueprint pour l'authentification
# =============================================================================

auth_bp = Blueprint("auth", __name__)

# =============================================================================
# Classe wrapper Flask-Login
# =============================================================================

class FlaskUser(UserMixin):
    """
    Wrapper autour du modèle User SQLAlchemy pour compatibilité Flask-Login.
    
    Flask-Login nécessite que l'objet utilisateur implémente :
    - is_authenticated, is_active, is_anonymous, get_id()
    UserMixin fournit des implémentations par défaut.
    """

    def __init__(self, user_model):
        """
        Args:
            user_model: Instance du modèle SQLAlchemy User
        """
        self.id = user_model.id
        self.username = user_model.username
        self.email = user_model.email
        self.role = user_model.role
        self._is_active = user_model.is_active

    @property
    def is_active(self):
        """L'utilisateur est-il actif ?"""
        return self._is_active

    @property
    def is_admin(self):
        """L'utilisateur est-il administrateur ?"""
        return self.role == "admin"

    def get_id(self):
        """Retourne l'ID utilisateur sous forme de string (requis par Flask-Login)."""
        return str(self.id)


# =============================================================================
# Configuration de Flask-Login
# =============================================================================

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    """
    Callback Flask-Login : charge un utilisateur par son ID.
    Appelé automatiquement à chaque requête pour les utilisateurs connectés.
    """
    session = get_session()
    try:
        user = session.query(User).get(int(user_id))
        if user and user.is_active:
            return FlaskUser(user)
        return None
    except Exception:
        return None
    finally:
        session.close()


# =============================================================================
# Routes d'authentification
# =============================================================================

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Page de connexion web."""
    # Si déjà connecté, rediriger vers le scanner
    if current_user.is_authenticated:
        return redirect(url_for("main.scan"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Veuillez remplir tous les champs.", "error")
            return render_template("login.html")

        session = get_session()
        try:
            user = session.query(User).filter_by(
                username=username, is_active=True
            ).first()

            if user and user.check_password(password):
                flask_user = FlaskUser(user)
                login_user(flask_user, remember=True)
                # Rediriger vers la page demandée ou le scanner
                next_page = request.args.get("next")
                return redirect(next_page or url_for("main.scan"))
            else:
                flash("Nom d'utilisateur ou mot de passe incorrect.", "error")

        except Exception as e:
            flash(f"Erreur de connexion : {e}", "error")
        finally:
            session.close()

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """Déconnexion de l'utilisateur."""
    logout_user()
    flash("Vous avez été déconnecté.", "info")
    return redirect(url_for("auth.login"))
