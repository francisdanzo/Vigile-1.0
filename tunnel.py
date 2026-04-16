# -*- coding: utf-8 -*-
"""
VIGILE — Gestionnaire Cloudflare Tunnel
"Chaque équipement a sa sentinelle"

Expose le serveur Flask local via une URL HTTPS publique
en utilisant cloudflared (Cloudflare Tunnel).

Aucun compte Cloudflare requis — mode "quick tunnel" gratuit.
L'URL générée est du type : https://xxxx.trycloudflare.com
"""

import os
import re
import sys
import platform
import subprocess
import threading
import urllib.request
import zipfile
import stat
from pathlib import Path

# Importer les constantes de config
try:
    from config import BASE_DIR, FLASK_PORT
except ImportError:
    # Fallback pour les tests unitaires
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    FLASK_PORT = 5000


# =============================================================================
# Chemins
# =============================================================================

TUNNEL_DIR = os.path.join(BASE_DIR, "tunnel")
os.makedirs(TUNNEL_DIR, exist_ok=True)

# Nom de l'exécutable selon l'OS
def _get_cloudflared_path() -> str:
    """Retourne le chemin de l'exécutable cloudflared."""
    system = platform.system().lower()
    if system == "windows":
        return os.path.join(TUNNEL_DIR, "cloudflared.exe")
    else:
        return os.path.join(TUNNEL_DIR, "cloudflared")


# =============================================================================
# Téléchargement automatique de cloudflared
# =============================================================================

def _get_download_url() -> str:
    """Retourne l'URL de téléchargement cloudflared selon l'OS/architecture."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    # Mapper l'architecture
    if "arm" in machine or "aarch64" in machine:
        arch = "arm64"
    elif "64" in machine:
        arch = "amd64"
    else:
        arch = "386"

    base = "https://github.com/cloudflare/cloudflared/releases/latest/download"

    if system == "windows":
        return f"{base}/cloudflared-windows-{arch}.exe"
    elif system == "darwin":
        return f"{base}/cloudflared-darwin-{arch}.tgz"
    else:
        return f"{base}/cloudflared-linux-{arch}"


def telecharger_cloudflared(callback_progression=None) -> bool:
    """
    Télécharge cloudflared si absent.
    
    Args:
        callback_progression: Fonction appelée avec un message de statut (str)
    
    Returns:
        True si prêt, False si erreur
    """
    chemin = _get_cloudflared_path()

    if os.path.exists(chemin):
        return True

    url = _get_download_url()
    tmp = chemin + ".tmp"

    def _log(msg):
        print(f"[VIGILE Tunnel] {msg}")
        if callback_progression:
            callback_progression(msg)

    _log(f"Téléchargement de cloudflared...")
    _log(f"Source : {url}")

    try:
        # User-Agent pour éviter le blocage de certains serveurs
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-agent', 'Mozilla/5.0')]
        urllib.request.install_opener(opener)

        # Téléchargement avec progression
        def reporthook(count, block_size, total_size):
            if total_size > 0:
                pct = min(100, int(count * block_size * 100 / total_size))
                if pct % 5 == 0: # Mise à jour toutes les 5% pour fluidité UI
                    _log(f"Téléchargement : {pct}%")

        urllib.request.urlretrieve(url, tmp, reporthook)

        # Si c'est un .tgz (macOS), extraire
        if url.endswith(".tgz"):
            import tarfile
            with tarfile.open(tmp, "r:gz") as tar:
                for member in tar.getmembers():
                    if "cloudflared" in member.name and not member.name.endswith("/"):
                        member.name = os.path.basename(chemin)
                        tar.extract(member, TUNNEL_DIR)
                        break
            os.remove(tmp)
        else:
            os.rename(tmp, chemin)

        # Rendre exécutable sur Linux/macOS
        if platform.system() != "Windows":
            os.chmod(chemin, os.stat(chemin).st_mode | stat.S_IEXEC)

        _log("cloudflared téléchargé avec succès.")
        return True

    except Exception as e:
        _log(f"Erreur de téléchargement : {e}")
        if os.path.exists(tmp):
            os.remove(tmp)
        return False


# =============================================================================
# Gestionnaire du tunnel
# =============================================================================

class CloudflareTunnel:
    """
    Gère le cycle de vie d'un Cloudflare Quick Tunnel.
    
    Usage :
        tunnel = CloudflareTunnel(port=5000)
        tunnel.demarrer(callback_url=lambda url: print(url))
        ...
        tunnel.arreter()
    """

    def __init__(self, port: int = None):
        self.port = port or FLASK_PORT
        self._process = None
        self._thread = None
        self._url = None
        self._actif = False

    @property
    def url(self) -> str | None:
        """URL publique du tunnel, ou None si non démarré."""
        return self._url

    @property
    def actif(self) -> bool:
        return self._actif

    def demarrer(self, callback_url=None, callback_erreur=None) -> bool:
        """
        Lance cloudflared en arrière-plan et extrait l'URL publique.
        
        Args:
            callback_url: Appelé avec l'URL HTTPS quand disponible (str)
            callback_erreur: Appelé avec un message d'erreur si problème (str)
        
        Returns:
            True si le lancement a démarré (l'URL arrive de façon asynchrone)
        """
        if self._actif:
            return True

        chemin = _get_cloudflared_path()
        if not os.path.exists(chemin):
            msg = "cloudflared introuvable. Téléchargez-le d'abord."
            print(f"[VIGILE Tunnel] {msg}")
            if callback_erreur:
                callback_erreur(msg)
            return False

        def _run():
            try:
                # Lance le quick tunnel (sans compte)
                cmd = [
                    chemin,
                    "tunnel",
                    "--url", f"http://localhost:{self.port}",
                    "--no-autoupdate",
                ]
                # Sur Windows, on utilise CREATE_NO_WINDOW pour le process enfant
                startupinfo = None
                if platform.system() == "Windows":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    startupinfo=startupinfo,
                    encoding='utf-8',
                    errors='replace'
                )
                self._actif = True

                # Lire la sortie ligne par ligne pour trouver l'URL
                url_trouvee = False
                for line in self._process.stdout:
                    if not self._actif:
                        break
                    
                    line = line.strip()
                    if line:
                        print(f"[cloudflared] {line}")

                    # Chercher l'URL dans la sortie
                    if not url_trouvee:
                        match = re.search(
                            r'https://[a-zA-Z0-9\-]+\.trycloudflare\.com',
                            line
                        )
                        if match:
                            self._url = match.group(0)
                            url_trouvee = True
                            print(f"[VIGILE Tunnel] URL publique : {self._url}")
                            if callback_url:
                                callback_url(self._url)

                # Si le processus s'arrête prématurément
                if self._process:
                    rc = self._process.poll()
                    if rc is not None and rc != 0 and not url_trouvee:
                        if callback_erreur:
                            callback_erreur(f"cloudflared s'est arrêté (code {rc})")

                self._actif = False
                self._url = None

            except Exception as e:
                self._actif = False
                msg = f"Erreur tunnel : {e}"
                print(f"[VIGILE Tunnel] {msg}")
                if callback_erreur:
                    callback_erreur(msg)

        self._thread = threading.Thread(target=_run, daemon=True, name="cloudflared")
        self._thread.start()
        return True

    def arreter(self):
        """Arrête le tunnel proprement."""
        self._actif = False
        self._url = None
        if self._process:
            try:
                # On tente une terminaison douce
                self._process.terminate()
                self._process.wait(timeout=3)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None
        print("[VIGILE Tunnel] Tunnel arrêté.")
