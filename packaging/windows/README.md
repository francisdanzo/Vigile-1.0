# Build Windows

Ce dossier contient le minimum nécessaire pour produire une release Windows propre de `Vigile`.

## Pré-requis

- Python installé sur la machine de build Windows
- Le binaire `cloudflared.exe` placé dans `tunnel/` à la racine du projet
- Un environnement virtuel Python propre

## Étapes rapides

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-build.txt
pyinstaller --clean vigile.spec
```

## Résultat attendu

- Exécutable desktop dans `dist/Vigile/`
- Templates Flask embarqués
- `cloudflared.exe` embarqué dans `dist/Vigile/tunnel/`
- Données runtime créées au premier lancement dans `%AppData%\Vigile\`

## Vérifications avant publication

- Aucun `vigile.db` n'est présent dans `dist/`
- Aucun certificat `*.pem` n'est présent dans `dist/`
- Le dossier `dist/Vigile/tunnel/` contient bien `cloudflared.exe`
- Le premier lancement crée une base vierge avec uniquement `admin`
- Le tunnel Cloudflare fonctionne sans téléchargement runtime
