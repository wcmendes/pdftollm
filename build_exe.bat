@echo off
REM ============================================================
REM Script para gerar o executável PDFConverterMD.exe
REM ============================================================
REM
REM Pré-requisitos:
REM   1. Python 3.10+ instalado
REM   2. pip install pyinstaller
REM   3. pip install -e .  (dependências do projeto)
REM
REM O executável será gerado em: dist\PDFConverterMD.exe
REM ============================================================

echo === PDF to Markdown Converter - Build ===
echo.

REM Verificar se PyInstaller está instalado
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] PyInstaller nao encontrado. Instalando...
    pip install pyinstaller
    echo.
)

echo Gerando executavel...
echo.

pyinstaller pdfconverter.spec --noconfirm --clean

echo.
if exist "dist\PDFConverterMD.exe" (
    echo === BUILD CONCLUIDO COM SUCESSO ===
    echo.
    echo Executavel gerado em: dist\PDFConverterMD.exe
    echo Tamanho:
    for %%A in ("dist\PDFConverterMD.exe") do echo   %%~zA bytes
) else (
    echo === ERRO: Build falhou ===
    echo Verifique os logs acima para detalhes.
)

echo.
pause
