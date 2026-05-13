# -*- coding: utf-8 -*-
"""
VIGILE — Point d'entrée principal
"Chaque équipement a sa sentinelle"

Ce script assemble et lance l'application complète :
1. Initialise la base de données
2. Crée l'application Flask
3. Lance Flask dans un thread séparé (si mode desktop)
4. Lance l'interface PyQt6 dans le thread principal

Usage :
    python app.py              → Mode complet (PyQt6 + Flask)
    python app.py --web-only   → Mode serveur uniquement (Flask seul)
"""

import os
import sys
import argparse
import threading

# S'assurer que le répertoire du projet est dans le path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from config import APP_NAME, APP_SLOGAN, APP_VERSION, FLASK_PORT


def main():
    """Point d'entrée principal de VIGILE."""
    # Parser les arguments de la ligne de commande
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} v{APP_VERSION} — {APP_SLOGAN}"
    )
    parser.add_argument(
        "--web-only",
        action="store_true",
        help="Lance uniquement le serveur Flask (sans interface PyQt6)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=FLASK_PORT,
        help=f"Port du serveur Flask (défaut: {FLASK_PORT})"
    )
    args = parser.parse_args()

    # Afficher la bannière
    print("=" * 60)
    print(f"  🛡  {APP_NAME} v{APP_VERSION}")
    print(f"  \"{APP_SLOGAN}\"")
    print("=" * 60)
    print()

    # ==========================================================================
    # Étape 1 : Initialiser la base de données
    # ==========================================================================
    print("[VIGILE] Initialisation de la base de données...")
    from database import init_db
    init_db()
    print()

    # ==========================================================================
    # Étape 2 : Créer l'application Flask
    # ==========================================================================
    print("[VIGILE] Création de l'application Flask...")
    from web.routes import create_flask_app
    flask_app = create_flask_app()
    print("[VIGILE] Application Flask prête.")
    print()

    # ==========================================================================
    # Mode web uniquement
    # ==========================================================================
    if args.web_only:
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
        except Exception:
            ip = "127.0.0.1"
            
        print(f"[VIGILE] Mode serveur uniquement")
        print(f"[VIGILE] Serveur accessible sur le réseau local à :")
        print(f"[VIGILE] 👉  http://{ip}:{args.port}")
        print(f"[VIGILE] Ctrl+C pour arrêter\n")
        
        flask_app.run(
            host="0.0.0.0",
            port=args.port,
            debug=False,
            use_reloader=False
        )
        return

    # ==========================================================================
    # Mode complet : PyQt6 + Flask
    # ==========================================================================
    print("[VIGILE] Mode complet (Desktop + Web)")
    print()

    # Importer PyQt6
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        print("[VIGILE] ERREUR : PyQt6 n'est pas disponible !")
        print("[VIGILE] Installez PyQt6 ou lancez avec --web-only")
        sys.exit(1)

    # Importer la fenêtre principale et le thème
    from desktop.main_window import VigileWindow, load_theme

    # Créer l'application Qt
    qt_app = QApplication.instance() or QApplication(sys.argv)
    load_theme(qt_app)

    # Créer et afficher la fenêtre principale
    window = VigileWindow(flask_app=flask_app)
    window.show()

    print("[VIGILE] Interface PyQt6 prête.")
    print("[VIGILE] Connectez-vous pour commencer.")
    print()

    # Lancer la boucle principale Qt
    exit_code = qt_app.exec()

    print("[VIGILE] Application fermée. À bientôt !")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
