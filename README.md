<div align="center">
  
# 🛡 VIGILE
**"Chaque équipement a sa sentinelle"**

![Python](https://img.shields.io/badge/Python-3.x-blue.svg?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-Web_Framework-black.svg?style=for-the-badge&logo=flask)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57.svg?style=for-the-badge&logo=sqlite)
![Tkinter](https://img.shields.io/badge/Tkinter-Desktop_UI-lightgrey.svg?style=for-the-badge)

*Système hyrbide professionnel (Bureau + Web) de gestion et de traçabilité de matériel informatique avec technologie QR Code.*

</div>

<br>

<div align="center">
  <i>Une solution légère, moderne et puissante pour suivre vos équipements de bout en bout, gérer les attributions et scanner les matériels directement depuis le terrain avec votre smartphone.</i>
</div>

## ✨ Fonctionnalités Principales

### 💻 Application de Bureau (Gestion Centrale)
- **Interface Premium** : Design "Dark Mode" élégant, réactif et optimisé pour la lisibilité.
- **Gestionnaire d'Inventaire** : Ajoutez, modifiez et suivez chaque pièce d'équipement (Ordinateurs, Moniteurs, Imprimantes...).
- **Suivi des Attributions** : Prêtez et récupérez du matériel avec un historique complet et traçable.
- **Module Serveur Intégré** : Lancez et contrôlez le serveur Web Flask directement depuis l'application de bureau en un clic.

### 🌐 Interface Web & Mobile (Opérations Terrain)
- **Scanner QR Code Intégré** : Utilisez l'appareil photo de n'importe quel smartphone pour scanner un équipement et accéder immédiatement à sa fiche.
- **Tableau de Bord & Inventaire** : Parcourez tout votre parc informatique (statistiques en temps réel, alertes de maintenance) via une interface moderne "Glassmorphism" construite avec Bootstrap 5.
- **Cloudflare Tunnel (Inclus)** : Le web server local est publiquement exposé via un tunnel HTTPS sécurisé généré automatiquement afin de garantir que les caméras mobiles fonctionnent sans problème de certificats SSL locaux.

### 🏷️ Technologie VIGILE
- Génération automatique de codes uniques (`VIG-2026-0001`).
- Génération et stockage automatiques des QR Codes PNG pour impression/étiquetage.

---

## 🛠️ Stack Technique

- **Backend** : Python 3, Flask, Flask-Login.
- **Base de données** : SQLite via SQLAlchemy (ORM).
- **Sécurité** : Hachage Bcrypt pour les mots de passe.
- **Interface Desktop** : Tkinter natif perfectionné avec styles personnalisés.
- **Interface Web** : HTML5, Vanilla CSS personnalisé, Bootstrap 5, `html5-qrcode` pour le scan caméra.
- **Réseau** : `cloudflared` (géré programmatiquement) pour le Tunnel HTTPS.

---

## 🚀 Installation & Démarrage

### 1. Prérequis
Assurez-vous d'avoir Python 3 installé sur votre machine.

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

## 📂 Structure du Projet

```text
Vigile-1.0/
│
├── app.py                  # Point d'entrée principal de l'application
├── config.py               # Configuration globale (Couleurs, Ports, Répertoires)
├── database.py             # Initialisation SQLAlchemy
├── models.py               # Modèles de BDD (User, Materiel, Attribution)
├── tunnel.py               # Gestion automatique de Cloudflare Tunnel
│
├── desktop/                # 🖥️ Interface Applicative (Tkinter)
│   ├── main_window.py      # Fenêtre principale et navigation
│   ├── inventory_view.py   # Tableau des équipements
│   ├── add_material.py     # Logique d'ajout d'équipement
│   └── ...
│
├── web/                    # 🌐 Serveur Web (Flask)
│   ├── routes.py           # Routes de l'application (Dashboard, Scan, Auth)
│   ├── auth.py             # Module d'authentification Flask-Login
│   ├── static/             # CSS & JS
│   └── templates/          # Templates HTML Bootstrap (Dashboard, Historique...)
│
├── qr/
│   └── generator.py        # Moteur de génération des QR Codes
│
└── assets/                 # Dossier généré : Base de données (.db) et /qr_codes
```

---

<div align="center">
  Construit avec ❤️ pour simplifier la sécurité et la traçabilité des équipements.<br>
  <b>2026 — Francis NDAYUBAHA</b>
</div>
