# VIGILE

`Vigile` est une application hybride `desktop + web` de gestion et de traçabilité de matériel informatique avec QR codes.

## Fonctionnalités

- Interface desktop Tkinter pour l'administration et l'inventaire
- Interface web/mobile Flask pour la consultation et le scan terrain
- Base SQLite locale créée automatiquement au premier lancement
- Compte par défaut créé sur installation vierge : `admin / admin123`
- Mot de passe stocké sous forme de hash `bcrypt`
- Tunnel `Cloudflare` optionnel pour exposer l'interface web en HTTPS

## Runtime de la release

La release Windows ne doit embarquer aucune donnée locale.

Au premier lancement :

- le dossier de données est créé automatiquement dans `%AppData%\Vigile\`
- la base `vigile.db` est créée automatiquement
- les QR générés sont stockés dans `%AppData%\Vigile\assets\qr_codes\`
- aucun certificat SSL local n'est requis

## Développement local

```bash
python -m venv .venv
source .venv/bin/activate  # Windows : .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Mode serveur seul :

```bash
python app.py --web-only --port 5000
```

## Build Windows avec PyInstaller

Pré-requis :

- machine de build Windows
- `cloudflared.exe` placé dans `tunnel/`
- dépendances runtime installées
- dépendances build installées via `requirements-build.txt`

Build rapide :

```powershell
pip install -r requirements.txt
pip install -r requirements-build.txt
pyinstaller --clean vigile.spec
```

Documentation associée :

- `packaging/windows/README.md`
- `packaging/windows/build_release.ps1`

## Structure utile

```text
Vigile-1.0/
├── app.py
├── config.py
├── database.py
├── models.py
├── tunnel.py
├── vigile.spec
├── requirements.txt
├── requirements-build.txt
├── desktop/
├── qr/
├── tunnel/
├── web/
│   ├── static/
│   └── templates/
└── packaging/windows/
```

## Points de release

- Ne pas distribuer de `vigile.db`
- Ne pas distribuer de `*.pem`
- Vérifier que `cloudflared.exe` est bien inclus dans la build
- Vérifier qu'un premier lancement crée uniquement le compte `admin`
