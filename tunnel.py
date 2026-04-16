# -*- coding: utf-8 -*-
"""
VIGILE — Gestionnaire Cloudflare Tunnel
"Chaque équipement a sa sentinelle"

Expose le serveur Flask local via une URL HTTPS publique
en utilisant un binaire cloudflared embarqué dans la release.

Aucun compte Cloudflare requis — mode "quick tunnel" gratuit.
L'URL générée est du type : https://xxxx.trycloudflare.com
"""

import os
import platform
import re
import subprocess
import threading

try:
    from config import FLASK_PORT, get_resource_path
except ImportError:
    FLASK_PORT = 5000

    def get_resource_path(relative_path):
        return relative_path


def _get_cloudflared_path() -> str:
    """Retourne le chemin du binaire cloudflared embarqué."""
    system = platform.system().lower()
    if system == "windows":
        return get_resource_path("tunnel/cloudflared.exe")
    return get_resource_path("tunnel/cloudflared")


def is_cloudflared_available() -> bool:
    """Vérifie que le binaire cloudflared embarqué est présent."""
    return os.path.exists(_get_cloudflared_path())


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

        Returns:
            True si le lancement a démarré. L'URL arrive ensuite via callback.
        """
        if self._actif:
            return True

        chemin = _get_cloudflared_path()
        if not is_cloudflared_available():
            msg = (
                "cloudflared est absent de la release. "
                "Ajoutez le binaire dans le bundle PyInstaller."
            )
            print(f"[VIGILE Tunnel] {msg}")
            if callback_erreur:
                callback_erreur(msg)
            return False

        def _run():
            try:
                cmd = [
                    chemin,
                    "tunnel",
                    "--url", f"http://localhost:{self.port}",
                    "--no-autoupdate",
                ]
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
                    encoding="utf-8",
                    errors="replace",
                )
                self._actif = True

                url_trouvee = False
                for line in self._process.stdout:
                    if not self._actif:
                        break

                    line = line.strip()
                    if line:
                        print(f"[cloudflared] {line}")

                    if not url_trouvee:
                        match = re.search(
                            r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com",
                            line,
                        )
                        if match:
                            self._url = match.group(0)
                            url_trouvee = True
                            print(f"[VIGILE Tunnel] URL publique : {self._url}")
                            if callback_url:
                                callback_url(self._url)

                if self._process:
                    rc = self._process.poll()
                    if rc is not None and rc != 0 and not url_trouvee:
                        if callback_erreur:
                            callback_erreur(f"cloudflared s'est arrêté (code {rc})")

                self._actif = False
                self._url = None

            except Exception as exc:
                self._actif = False
                msg = f"Erreur tunnel : {exc}"
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
                self._process.terminate()
                self._process.wait(timeout=3)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None
        print("[VIGILE Tunnel] Tunnel arrêté.")
