#!/usr/bin/env python3
"""
Script de compilation PyInstaller pour Vigile 1.0
Crée un exécutable .exe autonome sans dépendances Python
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def main():
    print("=" * 70)
    print("🔨 VIGILE 1.0 - Compilation Windows (PyInstaller)")
    print("=" * 70)
    
    # Vérifier que PyInstaller est installé
    try:
        import PyInstaller
    except ImportError:
        print("\n❌ PyInstaller non détecté.")
        print("Installation de PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Chemins
    root_dir = Path(__file__).parent.parent
    app_path = root_dir / "app.py"
    icon_path = root_dir / "setup" / "vigile.ico"
    
    # Nettoyer les anciennes builds
    print("\n🧹 Nettoyage des builds précédentes...")
    for folder in ["build", "dist", "vigile"]:
        folder_path = root_dir / folder
        if folder_path.exists():
            shutil.rmtree(folder_path)
            print(f"   ✓ Suppression de {folder}/")
    
    # Créer l'icône si elle n'existe pas
    if not icon_path.exists():
        print("⚠️  Icône vigile.ico non trouvée (optionnel)")
        icon_arg = ""
    else:
        icon_arg = f"--icon={icon_path}"
        print(f"✓ Icône trouvée: {icon_path}")
    
    # Commande PyInstaller
    print("\n📦 Compilation de l'application...")
    print("   (Cette opération peut prendre 2-5 minutes...)\n")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=Vigile",
        "--onefile",
        "--windowed",
        "--distpath=dist",
        "--buildpath=build",
        "--specpath=.",
        f"--workpath=build",
        "--collect-all=flask",
        "--collect-all=sqlalchemy",
        "--collect-all=bcrypt",
        "--collect-all=cryptography",
        "--collect-all=qrcode",
        "--hidden-import=flask",
        "--hidden-import=flask_login",
        "--hidden-import=sqlalchemy",
        "--hidden-import=bcrypt",
        "--hidden-import=PIL",
        "--hidden-import=qrcode",
        "--noupx",
    ]
    
    if icon_arg:
        cmd.append(icon_arg)
    
    cmd.append(str(app_path))
    
    try:
        subprocess.run(cmd, check=True, cwd=root_dir)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Erreur lors de la compilation: {e}")
        sys.exit(1)
    
    # Vérifier le résultat
    exe_path = root_dir / "dist" / "Vigile.exe"
    if exe_path.exists():
        print("\n" + "=" * 70)
        print("✅ COMPILATION RÉUSSIE!")
        print("=" * 70)
        print(f"\n📍 Exécutable créé: {exe_path}")
        print(f"📊 Taille: {exe_path.stat().st_size / (1024*1024):.1f} MB")
        print("\n🚀 Utilisateurs peuvent maintenant:")
        print("   1. Exécuter directement Vigile.exe")
        print("   2. Aucune installation Python requise")
        print("   3. Fonctionne sur tous les PC Windows")
    else:
        print("\n❌ Erreur: Vigile.exe n'a pas été créé")
        sys.exit(1)

if __name__ == "__main__":
    main()
