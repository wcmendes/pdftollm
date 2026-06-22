# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file para PDF2LLM Converter — modo ONE-FOLDER.

Gera uma pasta com o executável + dependências em arquivos separados.
Ideal para distribuição via ZIP.

Uso:
    python -m PyInstaller pdfconverter_folder.spec --noconfirm --clean
"""

import importlib
from pathlib import Path

block_cipher = None

PROJECT_ROOT = Path(SPECPATH)

_pymupdf_layout = importlib.import_module('pymupdf.layout')
PYMUPDF_LAYOUT_DIR = Path(_pymupdf_layout.__file__).parent
PYMUPDF_LAYOUT_RESOURCES = PYMUPDF_LAYOUT_DIR / 'resources'

a = Analysis(
    [str(PROJECT_ROOT / 'src' / 'main.py')],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        (str(PROJECT_ROOT / 'locales' / 'pt-br.json'), 'locales'),
        (str(PROJECT_ROOT / 'locales' / 'en.json'), 'locales'),
        (str(PYMUPDF_LAYOUT_RESOURCES / 'onnx'), 'pymupdf/layout/resources/onnx'),
    ],
    hiddenimports=[
        'src', 'src.gui', 'src.gui.main_window', 'src.gui.about_dialog',
        'src.converters', 'src.converters.pdf_converter',
        'src.converters.pdf_validator', 'src.converters.conversion_manager',
        'src.models', 'src.models.data_models', 'src.models.file_list_manager',
        'src.i18n', 'src.i18n.i18n_manager',
        'src.ocr', 'src.ocr.ocr_engine', 'src.ocr.ocr_manager',
        'src.ocr.tesseract_engine', 'src.ocr.easyocr_engine',
        'src.ocr.markdown_quality_detector',
        'pymupdf4llm', 'pymupdf.layout', 'pytesseract',
        'PIL', 'PIL.Image', 'numpy', 'onnxruntime', 'tkinterdnd2',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['pytest', 'hypothesis', 'pytest_cov', '_pytest',
              'tensorboard', 'torch.utils.tensorboard'],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # <-- ONE-FOLDER mode
    name='PDF2LLM',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='PDF2LLM',
)
