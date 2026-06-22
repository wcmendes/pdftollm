# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file para PDF to Markdown Converter.

Gera um executável único (.exe) com todos os dados necessários embutidos.

Uso:
    python -m PyInstaller pdfconverter.spec --noconfirm --clean
"""

import sys
import os
from pathlib import Path

block_cipher = None

# Diretório raiz do projeto
PROJECT_ROOT = Path(SPECPATH)

# Diretório site-packages
SITE_PACKAGES = Path(r'C:\Users\willi\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages')

# Recursos do pymupdf_layout (modelos ONNX + YAML)
PYMUPDF_LAYOUT_RESOURCES = SITE_PACKAGES / 'pymupdf' / 'layout' / 'resources'

a = Analysis(
    [str(PROJECT_ROOT / 'src' / 'main.py')],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        # Catálogos de tradução (i18n)
        (str(PROJECT_ROOT / 'locales' / 'pt-br.json'), 'locales'),
        (str(PROJECT_ROOT / 'locales' / 'en.json'), 'locales'),
        # Recursos do pymupdf_layout (modelos ONNX e configurações YAML)
        (str(PYMUPDF_LAYOUT_RESOURCES / 'onnx'), 'pymupdf/layout/resources/onnx'),
    ],
    hiddenimports=[
        'src',
        'src.gui',
        'src.gui.main_window',
        'src.gui.about_dialog',
        'src.converters',
        'src.converters.pdf_converter',
        'src.converters.pdf_validator',
        'src.converters.conversion_manager',
        'src.models',
        'src.models.data_models',
        'src.models.file_list_manager',
        'src.i18n',
        'src.i18n.i18n_manager',
        'src.ocr',
        'src.ocr.ocr_engine',
        'src.ocr.ocr_manager',
        'src.ocr.tesseract_engine',
        'src.ocr.easyocr_engine',
        'src.ocr.markdown_quality_detector',
        'pymupdf4llm',
        'pymupdf.layout',
        'pymupdf.layout.DocumentLayoutAnalyzer',
        'pymupdf.layout.onnx',
        'pymupdf.layout.onnx.BoxRFDGNN',
        'pytesseract',
        'PIL',
        'PIL.Image',
        'numpy',
        'onnxruntime',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pytest',
        'hypothesis',
        'pytest_cov',
        '_pytest',
        'tensorboard',
        'torch.utils.tensorboard',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PDF2LLM',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Sem janela de console (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Adicione 'assets/icon.ico' se tiver um ícone .ico
)
