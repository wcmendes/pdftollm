@echo off
REM ============================================================
REM PDF2LLM — Build Setup Installer
REM 
REM Pré-requisitos:
REM   1. Python com dependências instaladas (pip install -e .)
REM   2. PyInstaller instalado (pip install pyinstaller)
REM   3. Inno Setup 6 instalado (https://jrsoftware.org/isinfo.php)
REM
REM Resultado: dist\PDF2LLM-Setup-0.1.0-beta.exe
REM ============================================================

echo [1/2] Gerando pasta PDF2LLM com PyInstaller...
python -m PyInstaller pdfconverter_folder.spec --noconfirm --clean
if errorlevel 1 (
    echo ERRO: Falha no PyInstaller
    pause
    exit /b 1
)

echo.
echo [2/2] Gerando Setup com Inno Setup...
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
    "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" installer.iss
) else if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    "C:\Program Files\Inno Setup 6\ISCC.exe" installer.iss
) else (
    echo AVISO: Inno Setup nao encontrado.
    echo Instale em: https://jrsoftware.org/isinfo.php
    echo Ou execute manualmente: ISCC.exe installer.iss
    pause
    exit /b 1
)

echo.
echo ============================================================
echo PRONTO! Instalador gerado em: dist\PDF2LLM-Setup-0.1.0-beta.exe
echo ============================================================
pause
