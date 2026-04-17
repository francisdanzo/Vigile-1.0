# -*- coding: utf-8 -*-
"""
VIGILE — Générateur de QR Codes
"Chaque équipement a sa sentinelle"

Ce module génère des QR codes uniques pour chaque équipement.
Le QR code encode l'URL web du matériel, permettant un scan
depuis un téléphone pour accéder directement à la fiche.
"""

import os

import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image, ImageDraw, ImageFont

from config import QR_CODES_DIR, QR_BOX_SIZE, QR_BORDER, FLASK_PORT


def generer_qr_code(
    code_vigile: str,
    host: str = "192.168.1.1",
    port: int = None,
    url: str | None = None
) -> str:
    """
    Génère un QR code PNG pour un matériel identifié par son code VIGILE.

    Par défaut, le QR code encode l'URL : http://{host}:{port}/materiel/{code_vigile}.
    Si une URL complète est fournie, elle est utilisée telle quelle.

    Args:
        code_vigile: Code unique du matériel (ex: VIG-2026-0001)
        host: Adresse IP ou hostname du serveur Flask
        port: Port du serveur Flask (défaut: config.FLASK_PORT)
        url: URL complète à encoder dans le QR code (optionnel)

    Returns:
        Chemin absolu du fichier QR code PNG généré

    Raises:
        OSError: Si le répertoire de destination n'est pas accessible
        ValueError: Si le code_vigile est vide
    """
    if not code_vigile:
        raise ValueError("Le code VIGILE ne peut pas être vide.")

    if url is None:
        if port is None:
            port = FLASK_PORT
        url = f"http://{host}:{port}/materiel/{code_vigile}"

    # S'assurer que le répertoire de destination existe
    os.makedirs(QR_CODES_DIR, exist_ok=True)

    # S'assurer que le répertoire de destination existe
    os.makedirs(QR_CODES_DIR, exist_ok=True)

    # Créer le QR code
    qr = qrcode.QRCode(
        version=None,  # Taille automatique selon le contenu
        error_correction=ERROR_CORRECT_H,  # Haute correction d'erreur (30%)
        box_size=QR_BOX_SIZE,
        border=QR_BORDER,
    )
    qr.add_data(url)
    qr.make(fit=True)

    # Générer l'image du QR code
    qr_image = qr.make_image(fill_color="#1a1a2e", back_color="#ffffff")

    # Convertir en RGB pour pouvoir travailler avec Pillow
    qr_image = qr_image.convert("RGB")

    # Ajouter un label sous le QR code avec le code VIGILE
    qr_image = _ajouter_label(qr_image, code_vigile)

    # Chemin de sauvegarde
    nom_fichier = f"{code_vigile}.png"
    chemin_complet = os.path.join(QR_CODES_DIR, nom_fichier)

    # Sauvegarder l'image
    qr_image.save(chemin_complet)
    print(f"[VIGILE QR] QR code généré : {chemin_complet}")
    print(f"[VIGILE QR] URL encodée    : {url}")

    return chemin_complet


def _ajouter_label(image: Image.Image, texte: str) -> Image.Image:
    """
    Ajoute un label texte sous l'image du QR code.
    
    Ceci permet d'identifier visuellement le matériel
    même sans scanner le QR code.
    
    Args:
        image: Image PIL du QR code
        texte: Texte à afficher sous le QR code
    
    Returns:
        Nouvelle image avec le label ajouté
    """
    largeur_qr, hauteur_qr = image.size

    # Hauteur de la zone de texte
    hauteur_label = 40

    # Créer une nouvelle image plus grande pour inclure le label
    nouvelle_image = Image.new(
        "RGB",
        (largeur_qr, hauteur_qr + hauteur_label),
        "#ffffff"
    )

    # Coller le QR code en haut
    nouvelle_image.paste(image, (0, 0))

    # Dessiner le texte centré en bas
    draw = ImageDraw.Draw(nouvelle_image)

    # Essayer d'utiliser une police système, sinon utiliser la police par défaut
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    except (OSError, IOError):
        try:
            # Fallback Windows
            font = ImageFont.truetype("arial.ttf", 16)
        except (OSError, IOError):
            # Fallback police par défaut Pillow
            font = ImageFont.load_default()

    # Calculer la position centrée du texte
    bbox = draw.textbbox((0, 0), texte, font=font)
    largeur_texte = bbox[2] - bbox[0]
    x = (largeur_qr - largeur_texte) // 2
    y = hauteur_qr + (hauteur_label - (bbox[3] - bbox[1])) // 2

    # Dessiner le texte
    draw.text((x, y), texte, fill="#1a1a2e", font=font)

    # Ajouter "VIGILE" en petit au-dessus du code
    try:
        font_petit = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    except (OSError, IOError):
        try:
            font_petit = ImageFont.truetype("arial.ttf", 10)
        except (OSError, IOError):
            font_petit = ImageFont.load_default()

    bbox_vigile = draw.textbbox((0, 0), "VIGILE", font=font_petit)
    largeur_vigile = bbox_vigile[2] - bbox_vigile[0]
    x_vigile = (largeur_qr - largeur_vigile) // 2
    y_vigile = hauteur_qr + 2

    draw.text((x_vigile, y_vigile), "VIGILE", fill="#888888", font=font_petit)

    return nouvelle_image


def generer_code_vigile(session) -> str:
    """
    Génère le prochain code VIGILE disponible.
    
    Format : VIG-YYYY-NNNN
    Exemple : VIG-2026-0001, VIG-2026-0002, etc.
    
    Le compteur est basé sur le nombre total de matériels
    existants dans la base de données.
    
    Args:
        session: Session SQLAlchemy active
    
    Returns:
        Prochain code VIGILE disponible (ex: VIG-2026-0042)
    """
    from datetime import datetime, timezone
    from models import Materiel
    from config import CODE_VIGILE_PREFIX

    annee = datetime.now(timezone.utc).strftime("%Y")

    # Trouver le dernier numéro utilisé pour cette année
    dernier = (
        session.query(Materiel)
        .filter(Materiel.code_vigile.like(f"{CODE_VIGILE_PREFIX}-{annee}-%"))
        .order_by(Materiel.code_vigile.desc())
        .first()
    )

    if dernier:
        # Extraire le numéro séquentiel du dernier code
        try:
            dernier_num = int(dernier.code_vigile.split("-")[-1])
        except (ValueError, IndexError):
            dernier_num = 0
        prochain_num = dernier_num + 1
    else:
        prochain_num = 1

    return f"{CODE_VIGILE_PREFIX}-{annee}-{prochain_num:04d}"


# =============================================================================
# Point d'entrée pour test direct
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("VIGILE — Test du générateur de QR codes")
    print("=" * 60)

    # Test de génération
    chemin = generer_qr_code("VIG-2026-TEST", host="192.168.1.100", port=5000)
    print(f"\nQR code de test généré : {chemin}")

    # Vérifier que le fichier existe
    assert os.path.exists(chemin), "Le fichier QR n'a pas été créé !"
    print("[OK] Le fichier existe")

    # Vérifier la taille de l'image
    img = Image.open(chemin)
    print(f"[OK] Dimensions : {img.size[0]}x{img.size[1]} pixels")

    # Test génération du code VIGILE
    from database import init_db, get_session
    init_db()
    session = get_session()
    try:
        code = generer_code_vigile(session)
        print(f"[OK] Prochain code VIGILE : {code}")
    finally:
        session.close()

    # Nettoyage du fichier de test
    os.remove(chemin)
    print("[OK] Fichier de test nettoyé")

    print("\n✅ PHASE 2 — TOUS LES TESTS PASSENT")
