$ErrorActionPreference = "Stop"

if (-not (Test-Path "tunnel\cloudflared.exe")) {
    throw "Placez tunnel\cloudflared.exe avant de lancer le build."
}

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-build.txt
pyinstaller --clean vigile.spec
