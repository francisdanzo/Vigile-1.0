# -*- coding: utf-8 -*-
"""
VIGILE — Point d'entrée principal
"Chaque équipement a sa sentinelle"

Ce script assemble et lance l'application complète :
1. Initialise la base de données
2. Crée l'application Flask
3. Lance Flask dans un thread séparé (si mode desktop)
4. Lance l'interface Tkinter dans le thread principal

Usage :
    python app.py               → Mode complet (Tkinter + Flask)
    python app.py --web-only    → Mode serveur uniquement (Flask seul)
"""

import os
import sys
import argparse

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
        help="Lance uniquement le serveur Flask (sans interface Tkinter)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=FLASK_PORT,
        help=f"Port du serveur web (défaut : {FLASK_PORT})"
    )
    args = parser.parse_args()

    # Afficher la bannière
    print("\n" + "=" * 60)
    print(f"  🛡  {APP_NAME} v{APP_VERSION}")
    print(f"  \"{APP_SLOGAN}\"")
    print("=" * 60 + "\n")

    # ==========================================================================
    # Étape 1 : Initialiser la base de données
    # ==========================================================================
    print("[VIGILE] Initialisation du système...")
    from database import init_db
    init_db()

    # ==========================================================================
    # Étape 2 : Créer l'application Flask
    # ==========================================================================
    from web.routes import create_flask_app
    flask_app = create_flask_app()
    print("[VIGILE] Moteur prêt.")

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
        print(f"[VIGILE] Serveur accessible à : http://{ip}:{args.port}")
        print(f"[VIGILE] Ctrl+C pour arrêter\n")
        
        flask_app.run(
            host="0.0.0.0",
            port=args.port,
            debug=False,
            use_reloader=False
        )
        return

    # ==========================================================================
    # Mode complet : Tkinter + Flask
    # ==========================================================================
    print("[VIGILE] Mode complet (Desktop + Web)")
    print()

    # Importer Tkinter
    try:
        import tkinter as tk
    except ImportError:
        print("[VIGILE] ERREUR : Tkinter n'est pas disponible !")
        print("[VIGILE] Installez python3-tk ou lancez avec --web-only")
        sys.exit(1)

    # Importer la fenêtre principale
    from desktop.main_window import MainWindow

    # Créer la fenêtre Tkinter
    root = tk.Tk()

    # Configurer l'icône (si disponible)
    try:
        root.iconphoto(False, tk.PhotoImage(data=""))
    except Exception:
        pass

    # Créer l'interface principale avec l'app Flask
    app = MainWindow(root, flask_app=flask_app)

    # Gérer la fermeture propre
    def on_closing():
        """Callback de fermeture de l'application."""
        print("\n[VIGILE] Fermeture de l'application...")
        app._afficher_splash_fermeture()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    print("[VIGILE] Interface Tkinter prête.")
    print("[VIGILE] Connectez-vous pour commencer.")
    print()

    # Lancer la boucle principale Tkinter
    # (Flask est lancé depuis le ServerFrame quand l'utilisateur clique "Démarrer")
    root.mainloop()

    print("[VIGILE] Application fermée. À bientôt !")


if __name__ == "__main__":
    main()
