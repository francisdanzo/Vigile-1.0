import os
import subprocess
from config import BASE_DIR

def get_ssl_context():
    """
    Génère ou récupère un contexte SSL (cert.pem, key.pem).
    Utilise openssl nativement pour éviter les gels (ERR_TIMED_OUT) du serveur
    Flask (Werkzeug) en mode adhoc dans un thread Tkinter.
    """
    cert_file = os.path.join(BASE_DIR, "cert.pem")
    key_file = os.path.join(BASE_DIR, "key.pem")
    
    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        print("\n[VIGILE] Génération d'un certificat SSL de sécurité locale...")
        try:
            subprocess.run([
                "openssl", "req", "-x509", "-newkey", "rsa:4096", "-nodes",
                "-out", cert_file, "-keyout", key_file, "-days", "365",
                "-subj", "/CN=VigileLocal"
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("[VIGILE] Certificat SSL généré avec succès.")
        except Exception as e:
            print(f"[VIGILE] Erreur lors de la génération SSL : {e}")
            print("[VIGILE] Le serveur démarrera en HTTPS mais pourrait rencontrer des problèmes.")
    
    return (cert_file, key_file)
