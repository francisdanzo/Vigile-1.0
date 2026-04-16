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

from config import (
    SECRET_KEY, APP_NAME, APP_SLOGAN, APP_VERSION,
    TYPES_MATERIEL, ETATS_MATERIEL, EMPLACEMENTS_MATERIEL, FLASK_PORT
)
from database import get_session
from models import Materiel, Attribution, User
from qr.generator import generer_qr_code, generer_code_vigile

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
# Gestion de l'inventaire
# =============================================================================

@main_bp.route("/inventaire")
@login_required
def inventaire():
    """Liste complète du matériel avec recherche et filtres."""
    session = get_session()
    try:
        query = session.query(Materiel)

        # Filtres
        type_f = request.args.get("type")
        if type_f and type_f in TYPES_MATERIEL:
            query = query.filter(Materiel.type == type_f)

        etat_f = request.args.get("etat")
        if etat_f and etat_f in ETATS_MATERIEL:
            query = query.filter(Materiel.etat == etat_f)

        empl_f = request.args.get("emplacement")
        if empl_f and empl_f in EMPLACEMENTS_MATERIEL:
            query = query.filter(Materiel.emplacement == empl_f)

        # Recherche
        q = request.args.get("q", "").strip()
        if q:
            query = query.filter(
                (Materiel.code_vigile.ilike(f"%{q}%")) |
                (Materiel.marque.ilike(f"%{q}%")) |
                (Materiel.modele.ilike(f"%{q}%")) |
                (Materiel.numero_serie.ilike(f"%{q}%"))
            )

        materiels = query.order_by(Materiel.created_at.desc()).all()

        return render_template(
            "inventory.html",
            materiels=materiels,
            types=TYPES_MATERIEL,
            etats=ETATS_MATERIEL,
            emplacements=EMPLACEMENTS_MATERIEL,
            filters={
                "type": type_f,
                "etat": etat_f,
                "emplacement": empl_f,
                "q": q
            }
        )
    finally:
        session.close()


@main_bp.route("/inventaire/ajouter", methods=["GET", "POST"])
@login_required
def ajouter_materiel():
    """Ajout d'un nouveau matériel."""
    session = get_session()
    try:
        if request.method == "POST":
            # Extraire les données du formulaire
            type_mat = request.form.get("type")
            marque = request.form.get("marque", "").strip()
            modele = request.form.get("modele", "").strip()
            serie = request.form.get("numero_serie", "").strip()
            etat = request.form.get("etat")
            emplacement = request.form.get("emplacement")
            notes = request.form.get("notes", "").strip()
            date_acq_str = request.form.get("date_acquisition", "").strip()

            # Validation
            if not type_mat or not etat or not emplacement:
                flash("Veuillez remplir tous les champs obligatoires.", "error")
                return render_template(
                    "form_materiel.html",
                    action="ajouter",
                    types=TYPES_MATERIEL,
                    etats=ETATS_MATERIEL,
                    emplacements=EMPLACEMENTS_MATERIEL
                )

            date_acq = None
            if date_acq_str:
                try:
                    date_acq = datetime.strptime(date_acq_str, "%Y-%m-%d")
                    date_acq = date_acq.replace(tzinfo=timezone.utc)
                except ValueError:
                    pass

            # Créer le matériel
            code_vigile = generer_code_vigile(session)
            materiel = Materiel(
                code_vigile=code_vigile,
                type=type_mat,
                marque=marque if marque else None,
                modele=modele if modele else None,
                numero_serie=serie if serie else None,
                etat=etat,
                emplacement=emplacement,
                date_acquisition=date_acq,
                notes=notes if notes else None,
                created_by=current_user.id
            )

            session.add(materiel)
            session.flush()

            # Générer le QR code
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
            except Exception:
                ip = "127.0.0.1"

            qr_path = generer_qr_code(code_vigile, host=ip, port=FLASK_PORT)
            materiel.qr_code_path = qr_path

            session.commit()
            flash(f"✅ Matériel {code_vigile} ajouté avec succès !", "success")
            return redirect(url_for("main.fiche_materiel", code_vigile=code_vigile))

        return render_template(
            "form_materiel.html",
            action="ajouter",
            types=TYPES_MATERIEL,
            etats=ETATS_MATERIEL,
            emplacements=EMPLACEMENTS_MATERIEL
        )
    except Exception as e:
        session.rollback()
        flash(f"Erreur lors de l'ajout : {e}", "error")
        return redirect(url_for("main.inventaire"))
    finally:
        session.close()


@main_bp.route("/inventaire/modifier/<int:mat_id>", methods=["GET", "POST"])
@login_required
def modifier_materiel(mat_id):
    """Modification d'un matériel existant."""
    session = get_session()
    try:
        materiel = session.query(Materiel).get(mat_id)
        if not materiel:
            flash("Matériel introuvable.", "error")
            return redirect(url_for("main.inventaire"))

        if request.method == "POST":
            materiel.type = request.form.get("type")
            materiel.marque = request.form.get("marque", "").strip() or None
            materiel.modele = request.form.get("modele", "").strip() or None
            materiel.numero_serie = request.form.get("numero_serie", "").strip() or None
            materiel.etat = request.form.get("etat")
            materiel.emplacement = request.form.get("emplacement")
            materiel.notes = request.form.get("notes", "").strip() or None

            date_acq_str = request.form.get("date_acquisition", "").strip()
            if date_acq_str:
                try:
                    date_acq = datetime.strptime(date_acq_str, "%Y-%m-%d")
                    materiel.date_acquisition = date_acq.replace(tzinfo=timezone.utc)
                except ValueError:
                    pass

            session.commit()
            flash(f"✅ Matériel {materiel.code_vigile} mis à jour.", "success")
            return redirect(url_for("main.fiche_materiel", code_vigile=materiel.code_vigile))

        return render_template(
            "form_materiel.html",
            action="modifier",
            materiel=materiel,
            types=TYPES_MATERIEL,
            etats=ETATS_MATERIEL,
            emplacements=EMPLACEMENTS_MATERIEL
        )
    except Exception as e:
        session.rollback()
        flash(f"Erreur lors de la modification : {e}", "error")
        return redirect(url_for("main.inventaire"))
    finally:
        session.close()


@main_bp.route("/inventaire/supprimer/<int:mat_id>", methods=["POST"])
@login_required
def supprimer_materiel(mat_id):
    """Suppression d'un matériel."""
    session = get_session()
    try:
        materiel = session.query(Materiel).get(mat_id)
        if not materiel:
            flash("Matériel introuvable.", "error")
            return redirect(url_for("main.inventaire"))

        code = materiel.code_vigile
        
        # Supprimer le fichier QR code s'il existe
        if materiel.qr_code_path and os.path.exists(materiel.qr_code_path):
            try:
                os.remove(materiel.qr_code_path)
            except Exception:
                pass

        session.delete(materiel)
        session.commit()
        flash(f"🗑 Matériel {code} supprimé avec succès.", "success")
    except Exception as e:
        session.rollback()
        flash(f"Erreur lors de la suppression : {e}", "error")
    finally:
        session.close()
    return redirect(url_for("main.inventaire"))




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
