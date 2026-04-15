# -*- coding: utf-8 -*-
"""
VIGILE — Routes Flask
"Chaque équipement a sa sentinelle"

Routes principales de l'application web :
- Scanner QR avec caméra
- Fiche matériel
- Attribution / récupération rapide
- Factory function pour créer l'app Flask
"""

import os
import sys
from datetime import datetime, timezone

from flask import (
    Flask, Blueprint, render_template, request,
    redirect, url_for, flash, jsonify
)
from flask_login import login_required, current_user

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SECRET_KEY, APP_NAME, APP_SLOGAN, APP_VERSION
from database import get_session
from models import Materiel, Attribution, User

# =============================================================================
# Blueprint principal
# =============================================================================

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def index():
    """Page d'accueil — redirige vers le scanner."""
    return redirect(url_for("main.scan"))


@main_bp.route("/scan")
@login_required
def scan():
    """Page de scan QR avec caméra du téléphone."""
    return render_template("scan.html")


@main_bp.route("/materiel/<code_vigile>")
@login_required
def fiche_materiel(code_vigile):
    """
    Fiche détaillée d'un matériel identifié par son code VIGILE.
    Accessible après scan du QR code ou saisie manuelle.
    """
    session = get_session()
    try:
        materiel = session.query(Materiel).filter_by(
            code_vigile=code_vigile
        ).first()

        if not materiel:
            flash(f"Matériel '{code_vigile}' introuvable.", "error")
            return redirect(url_for("main.scan"))

        # Attribution active
        attribution = (
            session.query(Attribution)
            .filter_by(materiel_id=materiel.id, is_active=True)
            .first()
        )

        # Historique des attributions
        historique = (
            session.query(Attribution)
            .filter_by(materiel_id=materiel.id)
            .order_by(Attribution.date_attribution.desc())
            .limit(10)
            .all()
        )

        # Enrichir l'historique avec les noms des attributeurs
        historique_data = []
        for attr in historique:
            user = session.query(User).get(attr.attribue_par)
            historique_data.append({
                "attribue_a": attr.attribue_a,
                "date_attribution": attr.date_attribution.strftime("%d/%m/%Y %H:%M"),
                "date_retour": attr.date_retour.strftime("%d/%m/%Y %H:%M") if attr.date_retour else None,
                "attribue_par": user.username if user else "?",
                "notes": attr.notes,
                "is_active": attr.is_active,
            })

        # Préparer les données du matériel pour le template
        mat_data = {
            "id": materiel.id,
            "code_vigile": materiel.code_vigile,
            "type": materiel.type,
            "marque": materiel.marque or "—",
            "modele": materiel.modele or "—",
            "numero_serie": materiel.numero_serie or "—",
            "etat": materiel.etat,
            "emplacement": materiel.emplacement,
            "date_acquisition": materiel.date_acquisition.strftime("%d/%m/%Y") if materiel.date_acquisition else "—",
            "notes": materiel.notes or "—",
            "est_attribue": attribution is not None,
            "attribue_a": attribution.attribue_a if attribution else None,
            "date_attribution": attribution.date_attribution.strftime("%d/%m/%Y %H:%M") if attribution else None,
        }

        return render_template(
            "materiel.html",
            materiel=mat_data,
            historique=historique_data
        )

    except Exception as e:
        flash(f"Erreur lors du chargement : {e}", "error")
        return redirect(url_for("main.scan"))
    finally:
        session.close()


@main_bp.route("/materiel/<code_vigile>/attribuer", methods=["GET", "POST"])
@login_required
def attribuer(code_vigile):
    """
    Attribution rapide d'un matériel à une personne.
    GET : affiche le formulaire
    POST : enregistre l'attribution
    """
    session = get_session()
    try:
        materiel = session.query(Materiel).filter_by(
            code_vigile=code_vigile
        ).first()

        if not materiel:
            flash("Matériel introuvable.", "error")
            return redirect(url_for("main.scan"))

        # Vérifier qu'il n'est pas déjà attribué
        attr_active = (
            session.query(Attribution)
            .filter_by(materiel_id=materiel.id, is_active=True)
            .first()
        )

        if request.method == "POST":
            if attr_active:
                flash(
                    f"Ce matériel est déjà attribué à {attr_active.attribue_a}.",
                    "error"
                )
                return redirect(url_for("main.fiche_materiel", code_vigile=code_vigile))

            nom = request.form.get("nom", "").strip()
            notes = request.form.get("notes", "").strip()

            if not nom:
                flash("Le nom de la personne est obligatoire.", "error")
                return render_template(
                    "assign.html",
                    materiel=materiel,
                    action="attribuer"
                )

            # Créer l'attribution
            attribution = Attribution(
                materiel_id=materiel.id,
                attribue_a=nom,
                attribue_par=current_user.id,
                notes=notes if notes else None,
                is_active=True
            )
            materiel.emplacement = "attribué"
            session.add(attribution)
            session.commit()

            flash(
                f"✅ Matériel {code_vigile} attribué à {nom} avec succès !",
                "success"
            )
            return redirect(url_for("main.fiche_materiel", code_vigile=code_vigile))

        # GET — afficher le formulaire
        if attr_active:
            flash(
                f"Ce matériel est déjà attribué à {attr_active.attribue_a}. "
                f"Récupérez-le d'abord.",
                "warning"
            )
            return redirect(url_for("main.fiche_materiel", code_vigile=code_vigile))

        return render_template(
            "assign.html",
            materiel=materiel,
            action="attribuer"
        )

    except Exception as e:
        session.rollback()
        flash(f"Erreur : {e}", "error")
        return redirect(url_for("main.fiche_materiel", code_vigile=code_vigile))
    finally:
        session.close()


@main_bp.route("/materiel/<code_vigile>/recuperer", methods=["POST"])
@login_required
def recuperer(code_vigile):
    """Récupération d'un matériel (fin d'attribution active)."""
    session = get_session()
    try:
        materiel = session.query(Materiel).filter_by(
            code_vigile=code_vigile
        ).first()

        if not materiel:
            flash("Matériel introuvable.", "error")
            return redirect(url_for("main.scan"))

        attr_active = (
            session.query(Attribution)
            .filter_by(materiel_id=materiel.id, is_active=True)
            .first()
        )

        if not attr_active:
            flash("Ce matériel n'est attribué à personne.", "info")
            return redirect(url_for("main.fiche_materiel", code_vigile=code_vigile))

        ancien_proprietaire = attr_active.attribue_a
        attr_active.retourner()
        materiel.emplacement = "réserve"
        session.commit()

        flash(
            f"✅ Matériel {code_vigile} récupéré de {ancien_proprietaire}.",
            "success"
        )
        return redirect(url_for("main.fiche_materiel", code_vigile=code_vigile))

    except Exception as e:
        session.rollback()
        flash(f"Erreur : {e}", "error")
        return redirect(url_for("main.fiche_materiel", code_vigile=code_vigile))
    finally:
        session.close()


# =============================================================================
# API endpoint pour la recherche par code (utilisé par le scanner JS)
# =============================================================================

@main_bp.route("/api/materiel/<code_vigile>")
@login_required
def api_materiel(code_vigile):
    """Retourne les infos d'un matériel en JSON (pour le scanner)."""
    session = get_session()
    try:
        materiel = session.query(Materiel).filter_by(
            code_vigile=code_vigile
        ).first()

        if not materiel:
            return jsonify({"error": "Matériel introuvable"}), 404

        return jsonify({
            "code_vigile": materiel.code_vigile,
            "type": materiel.type,
            "marque": materiel.marque,
            "etat": materiel.etat,
            "url": url_for("main.fiche_materiel", code_vigile=code_vigile)
        })

    finally:
        session.close()


# =============================================================================
# Factory Flask
# =============================================================================

def create_flask_app():
    """
    Factory function qui construit et configure l'application Flask complète.
    
    Returns:
        Instance Flask configurée avec tous les blueprints
    """
    app = Flask(
        __name__,
        template_folder=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "templates"
        )
    )

    # Configuration
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["SESSION_COOKIE_NAME"] = "vigile_session"

    # Injecter les variables globales dans les templates
    @app.context_processor
    def inject_globals():
        return {
            "app_name": APP_NAME,
            "app_slogan": APP_SLOGAN,
            "app_version": APP_VERSION,
        }

    # Enregistrer Flask-Login
    from web.auth import login_manager, auth_bp
    login_manager.init_app(app)

    # Enregistrer les blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    return app
