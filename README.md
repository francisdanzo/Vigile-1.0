<div align="center">
  
# 🛡 VIGILE
**"Chaque équipement a sa sentinelle"**

![Version](https://img.shields.io/badge/Version-1.1.0-brightgreen.svg?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.13-blue.svg?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-Web_Framework-black.svg?style=for-the-badge&logo=flask)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57.svg?style=for-the-badge&logo=sqlite)
![PyQt6](https://img.shields.io/badge/PyQt6-Desktop_UI-41CD52.svg?style=for-the-badge&logo=qt)

*Système hybride professionnel (Bureau + Web) de gestion et de traçabilité de matériel informatique avec technologie QR Code.*

</div>

<br>

<div align="center">
  <i>Une solution légère, moderne et puissante pour suivre vos équipements de bout en bout, gérer les attributions et scanner les matériels directement depuis le terrain avec votre smartphone.</i>
</div>

---

## ✨ Fonctionnalités Principales

### 💻 Application de Bureau (Gestion Centrale)
- **Thème Clair / Sombre** : Basculez à tout moment via le bouton ☀/🌙 dans la barre de titre — la préférence est sauvegardée automatiquement.
- **Design Apple Liquid Glass** : Interface PyQt6 repensée avec la palette Apple (noir profond `#06060e`, accent `#0A84FF`), effets glass et variables de couleur alignées sur le système iOS/macOS.
- **Auto-actualisation** : L'inventaire se rafraîchit automatiquement toutes les 30 secondes quand la vue est active ; l'historique se met à jour en temps quasi-réel (intervalle 500 ms) lors des recherches. Un verrou `_refreshing` empêche les requêtes simultanées.
- **Gestionnaire d'Inventaire** : Ajoutez, modifiez et suivez chaque pièce d'équipement (Ordinateurs, Moniteurs, Imprimantes...) avec pagination 10 items/page, filtres par type, état et emplacement.
- **Suivi des Attributions** : Prêtez et récupérez du matériel avec un historique complet et traçable.
- **Module Serveur Intégré** : Lancez et contrôlez le serveur Web Flask directement depuis l'application de bureau en un clic.

### 🌐 Interface Web & Mobile (Opérations Terrain)
- **Thème Clair / Sombre** : Toggle ☀/🌙 accessible depuis la page de connexion et toutes les pages — choix persisté dans `localStorage`.
- **Apple Liquid Glass Design System** : CSS entièrement réécrit avec le set de tokens `--glass`, `--blur`, `--accent`, etc. — sidebar et topbar en verre dépoli (`backdrop-filter`), ambiances lumineuses CSS-only, police Inter depuis Google Fonts, icônes Lucide.
- **Limitation de débit (login)** : Flask-Limiter protège la route POST `/login` à 10 tentatives par minute par IP.
- **Scanner QR Code Intégré** : Utilisez l'appareil photo de n'importe quel smartphone pour scanner un équipement et accéder immédiatement à sa fiche.
- **Tableau de Bord & Inventaire** : Parcourez tout votre parc informatique (statistiques en temps réel avec icônes Lucide, alertes de maintenance) via une interface mobile-first moderne.
- **Cloudflare Tunnel (Inclus)** : Le web server local est publiquement exposé via un tunnel HTTPS sécurisé généré automatiquement afin de garantir que les caméras mobiles fonctionnent sans problème de certificats SSL locaux.

### 🏷️ Technologie VIGILE
- Génération automatique de codes uniques (`VIG-2026-0001`).
- Génération et stockage automatiques des QR Codes PNG pour impression/étiquetage.

---

## 🛠️ Stack Technique

| Couche | Technologie |
|---|---|
| Backend | Python 3.13, Flask 3.x, Flask-Login |
| Base de données | SQLite via SQLAlchemy 2.x (ORM) |
| Sécurité | Bcrypt (mots de passe), Flask-Limiter (rate limiting), Flask-WTF (CSRF) |
| Interface Desktop | PyQt6 ≥ 6.6, QSS Liquid Glass (dark + light), QTimer auto-refresh |
| Interface Web | HTML5, CSS custom (tokens Liquid Glass), JS vanilla, `jsQR` (scan caméra), Lucide Icons, Inter |
| Réseau | `cloudflared` (géré programmatiquement) pour le Tunnel HTTPS |
| Build | PyInstaller + Inno Setup, CI GitHub Actions (Windows) |

---

## 🚀 Installation & Démarrage

### 1. Prérequis
Python 3.13 installé sur votre machine.

### 2. Cloner le projet et installer les dépendances
```bash
# Clonez ou téléchargez le répertoire
cd Vigile-1.0

# Création d'un environnement virtuel (Recommandé)
python -m venv venv
source venv/bin/activate  # Sur Windows : venv\Scripts\activate

# Installation des paquets
pip install -r requirements.txt
```

### 3. Lancer l'application
```bash
python app.py
```
> Lors du premier lancement, la base de données `vigile.db` sera créée automatiquement, et un compte d'administration par défaut vous sera proposé de créer (ex: *admin* / *admin123*).

---

## 📱 Utilisation Typique du Scanner

1. Lancez **VIGILE** (`python app.py`).
2. Dans le panneau de gauche, allez dans **Serveur**.
3. **Démarrez le serveur local**.
4. **Activez l'Accès Internet (Tunnel)** pour contourner les restrictions SSL des navigateurs mobiles. Une fois activé, un QR code de connexion serveur apparaîtra.
5. Scannez ce QR Code avec votre téléphone (ou tapez l'URL `https://...trycloudflare.com` fournie).
6. Identifiez-vous avec l'utilisateur et le mot de passe web de VIGILE.
7. Allez dans l'onglet **Scanner**, balayez l'étiquette d'un matériel : sa fiche d'attribution et ses détails apparaissent instantanément !

---

## 🏗️ Build Windows (Exécutable)

Le CI GitHub Actions produit automatiquement un installateur Windows (`VigileSetup-1.0.0.exe`) via PyInstaller + Inno Setup à chaque push sur les branches `main` ou `before`, ou sur les tags `v*`.

```bash
# Build local (depuis Windows)
pip install -r requirements.txt -r requirements-build.txt
# Télécharger cloudflared.exe dans tunnel/
pyinstaller --clean vigile.spec
# Puis lancer Inno Setup sur packaging/windows/vigile.iss
```

L'artefact est publié comme artifact GitHub Actions pendant 30 jours.

---

## 📂 Structure du Projet

```text
Vigile-1.0/
│
├── app.py                      # Point d'entrée principal de l'application
├── config.py                   # Configuration globale (Couleurs, Ports, Répertoires)
├── database.py                 # Initialisation SQLAlchemy
├── models.py                   # Modèles de BDD (User, Materiel, Attribution)
├── tunnel.py                   # Gestion automatique de Cloudflare Tunnel
├── vigile.spec                 # Configuration PyInstaller
├── vigile_theme.qss            # Thème desktop — Dark (Apple Liquid Glass)
├── vigile_theme_light.qss      # Thème desktop — Light (Apple Liquid Glass)
│
├── desktop/                    # 🖥️ Interface Applicative (PyQt6)
│   ├── main_window.py          # Fenêtre principale, composants UI, palettes de couleurs
│   ├── inventory_view.py       # Tableau des équipements (auto-refresh 30s, pagination)
│   ├── history_view.py         # Historique des attributions (refresh live 500ms)
│   ├── user_manager.py         # Gestion des utilisateurs web
│   └── add_material.py         # Dialogue d'ajout d'équipement
│
├── web/                        # 🌐 Serveur Web (Flask)
│   ├── routes.py               # Routes de l'application (Dashboard, Scan, Auth)
│   ├── auth.py                 # Module d'authentification Flask-Login + rate limiting
│   ├── extensions.py           # Extensions Flask (CSRF, Limiter)
│   ├── static/                 # CSS & JS
│   └── templates/              # Templates HTML (Design System Liquid Glass)
│       ├── base.html           # Layout de base, tokens CSS, sidebar, topbar
│       ├── login.html          # Page de connexion (glass card, logo highlight)
│       ├── dashboard.html      # Tableau de bord (icônes Lucide, stat cards colorées)
│       ├── inventory.html      # Liste de l'inventaire
│       ├── materiel.html       # Fiche détail d'un équipement
│       ├── assign.html         # Attribution / récupération (mat-info-card)
│       ├── form_materiel.html  # Formulaire ajout/modification (sections labellisées)
│       ├── history.html        # Historique
│       ├── scan.html           # Scanner QR Code (caméra)
│       └── setup.html          # Configuration initiale
│
├── qr/
│   └── generator.py            # Moteur de génération des QR Codes
│
├── packaging/
│   └── windows/
│       └── vigile.iss          # Script Inno Setup pour l'installateur Windows
│
├── .github/
│   └── workflows/
│       └── build-windows.yml   # CI/CD : build PyInstaller + Inno Setup
│
└── assets/                     # Dossier généré : Base de données (.db), QR codes et logo
    └── logo/
        └── vigile.ico          # Icône application Windows
```

---

## 📋 Changelog

### v1.1.0 — Liquid Glass & Auto-refresh

**Interface Desktop**
- Refonte complète du design system PyQt6 : palette Apple Liquid Glass (dark `#06060e` / light `#F2F2F7`), couleurs système Apple (`#0A84FF`, `#30D158`, `#FF453A`, `#FFD60A`)
- `VigileButton` — nouveau paramètre `padding` pour un contrôle granulaire sans patch inline
- `VigileTable` — hauteur de ligne par défaut fixée à 40px
- Auto-refresh : inventaire toutes les 30s, historique en live (500ms), guards `_refreshing` pour éviter les requêtes concurrentes
- Correction `setSortingEnabled(False/True)` encapsulant tous les `_bind()` (évite un crash Qt lors du tri pendant le peuplement)
- Correction de la fonction `alpha()` : l'alpha est maintenant un float 0–1 (requis par Qt6 CSS `rgba()`)
- Colonne "Code VIGILE" renommée (anciennement "Code"), "Lieu" (anciennement "Emplacement")
- Largeurs de colonnes et dimensionnement des contrôles de filtre revus
- Pagination réduite de 50 à 10 items par page

**Interface Web**
- Design System Apple Liquid Glass (base.html) : tokens `--glass`, `--blur`, `--accent`, `--txt-1/2/3`, ambiances CSS radiales, Inter depuis Google Fonts, icônes Lucide
- Sidebar et topbar en verre dépoli (`backdrop-filter: blur(48px) saturate(200%)`)
- Page login : glass card avec effet caustic light et logo en relief
- Dashboard : icônes Lucide (boxes, circle-check, user-check, triangle-alert), couleurs de valeurs contextuelles
- `assign.html` : nouveau composant `mat-info-card` avec icône Lucide contextuelle
- `form_materiel.html` : formulaire en sections labellisées (`form-section-label`)
- Flask-Limiter : protection anti-brute-force sur POST `/login` (10 req/min par IP)

**Build / CI**
- Migration Python 3.12 → 3.13 dans le workflow GitHub Actions
- `vigile_theme_light.qss` embarqué dans le build PyInstaller
- Diagnostics CI enrichis (PyQt6, Flask, SQLAlchemy)

---

<div align="center">
  Construit avec ❤️ pour simplifier la sécurité et la traçabilité des équipements.<br>
  <b>2026 — Francis NDAYUBAHA — v1.1.0</b>
</div>
