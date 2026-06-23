# PDF2LLM

> **PDF to Markdown Converter** — Convert PDFs to Markdown optimized for language models (LLMs)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg)]()
[![Status](https://img.shields.io/badge/Status-Beta-orange.svg)]()

---

Desktop application for batch PDF to Markdown conversion, designed for feeding LLMs like ChatGPT, Claude, Gemini, and others. Preserves document structure (headings, tables, lists) and provides automatic OCR for scanned PDFs.

## Features

- **Batch conversion** — select up to 50 PDFs and convert at once
- **Structure preserved** — headings, paragraphs, lists, and tables kept in Markdown
- **Image extraction** — optional, saves images in an organized subfolder
- **Automatic OCR** — detects scanned PDFs and reprocesses with Tesseract + EasyOCR
- **GUI** — simple interface with progress bar and language selector
- **Bilingual** — Portuguese (Brazil) and English, with live switching
- **Cross-platform** — Windows and Linux

## Download

Get the latest version from [Releases](https://github.com/wcmendes/pdftollm/releases):

| Platform | File | Description |
|----------|------|-------------|
| Windows | `PDF2LLM-Setup-x.x.x.exe` | **Installer** with Start Menu and uninstaller |
| Windows | `PDF2LLM-portable.zip` | Portable version (extract and use) |
| Windows | `PDF2LLM.exe` | Standalone single-file executable |
| Linux (Debian/Ubuntu) | `pdf2llm_x.x.x_amd64.deb` | .deb package (`sudo dpkg -i ...`) |

### Lightweight alternative (Linux/macOS)

If you prefer not to download the full .deb, install via pip:

```bash
pip install git+https://github.com/wcmendes/pdftollm.git
python -m src.main
```

Requires Python 3.10+ and `python3-tk` (`sudo apt install python3-tk`).

## Requirements

- **For .exe / .deb**: none — everything is bundled
- **To run from source**: Python 3.10+
- **Tesseract OCR** (optional): improves OCR results, but the app works without it

### Install Tesseract (optional)

<details>
<summary>Windows</summary>

1. Download from https://github.com/UB-Mannheim/tesseract/wiki
2. Install and add to PATH (e.g., `C:\Program Files\Tesseract-OCR`)
</details>

<details>
<summary>Linux (Ubuntu/Debian)</summary>

```bash
sudo apt install tesseract-ocr tesseract-ocr-eng
```
</details>

## Usage

### Via executable

Open `PDF2LLM.exe` (Windows) or `pdf2llm` (Linux). The interface guides the whole process:

1. Select PDF files
2. Output folder is automatically suggested (`/md` next to the PDFs)
3. Click **Convert**
4. When done, choose whether to open the output folder

### From source

```bash
git clone https://github.com/wcmendes/pdftollm.git
cd pdftollm
pip install -e .[dev]
python -m src.main
```

## OCR for scanned PDFs

After conversion, if the system detects PDFs that produced empty Markdown (scanned documents), it offers automatic OCR reprocessing:

1. **Tesseract** (primary) — fast and accurate
2. **EasyOCR** (fallback) — deep learning based, bundled in the executable

If neither can extract text, the original file is preserved.

## Distribution / Build

The project offers multiple packaging options:

| Command | Result |
|---------|--------|
| `build_exe.bat` | `dist\PDF2LLM.exe` (standalone, ~280 MB) |
| `build_setup.bat` | `dist\PDF2LLM-Setup-x.x.x.exe` (installer) |
| PyInstaller folder | `dist\PDF2LLM\` → can be zipped as portable |

GitHub Actions (`release.yml`) builds everything automatically when you push a `v*` tag.

## Project Structure

```
pdftollm/
├── src/
│   ├── main.py              # Entry point
│   ├── converters/          # PDF → Markdown engine
│   ├── gui/                 # tkinter interface
│   ├── i18n/                # Internationalization
│   ├── models/              # Dataclasses and managers
│   └── ocr/                 # Tesseract + EasyOCR
├── locales/                 # Translations (JSON)
├── tests/                   # 246 tests (unit + property-based)
├── pyproject.toml           # Dependencies and config
├── pdfconverter.spec        # One-file build (.exe)
├── pdfconverter_folder.spec # One-folder build (for Setup/ZIP)
├── installer.iss            # Inno Setup script
└── .github/workflows/       # CI/CD (automatic releases)
```

## Tests

```bash
pytest                # run all
pytest --cov=src      # with coverage
```

## License

[MIT](LICENSE) — William Mendes, 2026

## Author

**William Mendes**
— [GitHub](http://github.com/wcmendes) · [Lattes](https://lattes.cnpq.br/7726054867638395)
