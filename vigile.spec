# -*- mode: python ; coding: utf-8 -*-
#
# vigile.spec — Configuration PyInstaller pour VIGILE
#
# Utilise Path(__file__).resolve().parent pour un chemin stable
# que ce soit en CI ou en build local.

from pathlib import Path

project_dir = Path(SPECPATH).resolve()
block_cipher = None

# ── Données à embarquer ────────────────────────────────────────────────────────

datas = [
    # Templates Jinja2 — Flask les cherche à <_MEIPASS>/web/templates/
    (str(project_dir / "web" / "templates"), "web/templates"),
    # Thèmes PyQt6 (dark + light)
    (str(project_dir / "vigile_theme.qss"), "."),
    (str(project_dir / "vigile_theme_light.qss"), "."),
    # Logo (splash, login, sidebar, favicon web)
    (str(project_dir / "assets" / "logo"), "assets/logo"),
]

static_dir = project_dir / "web" / "static"
if static_dir.exists():
    datas.append((str(static_dir), "web/static"))

# Binaire Cloudflare Tunnel — embarqué si présent (téléchargé par le CI avant le build)
cloudflared_exe = project_dir / "tunnel" / "cloudflared.exe"
if cloudflared_exe.exists():
    datas.append((str(cloudflared_exe), "tunnel"))

# ── Analyse ────────────────────────────────────────────────────────────────────

a = Analysis(
    ["app.py"],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # ── PyQt6 ──
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.sip",
        # ── Pillow ──
        "PIL.Image",
        "PIL.ImageDraw",
        "PIL.ImageFont",
        "PIL.ImageOps",
        # ── SQLAlchemy ──
        "sqlalchemy.dialects.sqlite",
        "sqlalchemy.orm",
        "sqlalchemy.ext.declarative",
        "sqlalchemy.pool",
        # ── Flask / Werkzeug ──
        "flask_login",
        "werkzeug.serving",
        "werkzeug.middleware.proxy_fix",
        "jinja2.ext",
        "itsdangerous.url_safe",
        # ── Modules app — importés dynamiquement dans VigileWindow.page_factories ──
        "desktop.main_window",
        "desktop.inventory_view",
        "desktop.add_material",
        "desktop.history_view",
        "desktop.user_manager",
        "web.routes",
        "web.auth",
        "qr.generator",
        "tunnel",
        # ── Crypto / sécurité ──
        "bcrypt",
        "cryptography",
        "cffi",
        # ── QR code ──
        "qrcode",
        "qrcode.image.base",
        "qrcode.image.pure",
        "qrcode.image.pil",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Vigile",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(project_dir / "assets" / "logo" / "vigile.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Vigile",
)
