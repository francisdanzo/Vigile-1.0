@echo off
REM Vigile 1.0 - Script de construction du Setup Windows
REM Utilise PyInstaller + NSIS

echo.
echo ===============================================================
echo  VIGILE 1.0 - Construction Setup Windows
echo ===============================================================
echo.

REM Vérifier Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installé ou non dans le PATH
    echo.
    echo Installez Python 3.9+ depuis: https://www.python.org/downloads/
    echo Assurez-vous de cocher "Add Python to PATH"
    pause
    exit /b 1
)

echo [OK] Python détecté

REM Aller au répertoire du projet
cd /d "%~dp0.."

REM Étape 1: Installer les dépendances de build
echo.
echo [1/3] Installation des dépendances de build...
pip install -q pyinstaller
if errorlevel 1 (
    echo [ERREUR] Impossible d'installer PyInstaller
    pause
    exit /b 1
)
echo [OK] Dépendances installées

REM Étape 2: Installer les dépendances de l'application
echo.
echo [2/3] Installation des dépendances de l'application...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo [ERREUR] Impossible d'installer les dépendances
    pause
    exit /b 1
)
echo [OK] Dépendances de l'app installées

REM Étape 3: Compiler avec PyInstaller
echo.
echo [3/3] Compilation de l'application...
python setup/build_exe.py
if errorlevel 1 (
    echo [ERREUR] Compilation échouée
    pause
    exit /b 1
)
echo [OK] Compilation terminée

REM Vérifier si NSIS est installé
echo.
echo ===============================================================
echo  CRÉATION DU SETUP.EXE (avec NSIS)
echo ===============================================================
echo.

where makensis >nul 2>&1
if errorlevel 1 (
    echo [INFO] NSIS n'est pas installé
    echo.
    echo Options:
    echo   1. Installer NSIS: https://nsis.sourceforge.io/Download
    echo   2. Ou utiliser Vigile.exe directement dans dist\
    echo.
    echo Le fichier Vigile.exe est déjà prêt à être distribué!
    echo.
) else (
    echo [OK] NSIS trouvé, création du Setup...
    makensis /V2 setup\installer.nsi
    if errorlevel 1 (
        echo [ERREUR] NSIS a échoué
    ) else (
        echo [OK] Setup créé: dist\Vigile-1.0-Setup.exe
    )
)

echo.
echo ===============================================================
echo  COMPILATION TERMINÉE
echo ===============================================================
echo.
echo Fichiers prêts pour distribution:
echo   - dist\Vigile.exe              (exécutable autonome)
echo   - dist\Vigile-1.0-Setup.exe    (installateur NSIS, si créé)
echo.
pause
