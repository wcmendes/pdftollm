# PDF to Markdown Converter

Cross-platform desktop application for batch conversion of PDF files to Markdown, with optional image extraction and OCR fallback for scanned documents.

## Features

- Batch conversion of multiple PDF files to Markdown
- Preservation of document structure (headings, paragraphs, lists, tables)
- Optional extraction of embedded images from PDFs
- Automatic OCR fallback for scanned PDFs (Tesseract + EasyOCR)
- Simple and intuitive graphical interface (tkinter)
- Internationalization: Brazilian Portuguese and English
- Compatible with Linux and Windows

## System Requirements

- **Python** 3.10 or higher
- **Tesseract OCR** (optional, required only for scanned PDFs)
- **Operating System**: Linux or Windows 10+

### Installing Tesseract (optional)

Tesseract is only required if you want to use the OCR feature for image-based PDFs.

**Windows:**

1. Download the installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer and follow the instructions
3. Add the installation path to the system PATH (e.g., `C:\Program Files\Tesseract-OCR`)

**Linux (Ubuntu/Debian):**

```bash
sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-por
```

**Linux (Fedora):**

```bash
sudo dnf install tesseract tesseract-langpack-por
```

## Installation

1. Clone the repository:

```bash
git clone https://github.com/wcmendes/PDFConverter_MD_Desktop.git
cd PDFConverter_MD_Desktop
```

2. Create and activate a virtual environment (recommended):

```bash
python -m venv venv

# Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

3. Install the project with development dependencies:

```bash
pip install -e .[dev]
```

## Usage

### Graphical Interface

Run the application with:

```bash
pdfconverter
```

Or directly via the Python module:

```bash
python -m src.main
```

### Step by step

1. Click **"Select Files"** to choose the PDFs you want to convert
2. Click **"Select Output Folder"** to define where the Markdown files will be saved
3. (Optional) Check the **"Extract Images"** option to save embedded images from PDFs
4. Click **"Convert"** to start the process
5. Follow the progress via the progress bar
6. At the end, a summary will show how many files were successfully converted

### OCR Fallback

If the application detects scanned PDFs (which produced illegible Markdown), it will ask if you want to reprocess them with OCR. The system first tries Tesseract and, if needed, EasyOCR as a secondary engine.

## Project Structure

```
PDFConverter_MD_Desktop/
├── src/
│   ├── main.py              # Application entry point
│   ├── converters/          # PDF → Markdown conversion engine
│   ├── gui/                 # Graphical interface (tkinter)
│   ├── i18n/                # Internationalization
│   ├── models/              # Data models
│   └── ocr/                 # OCR engines (Tesseract, EasyOCR)
├── locales/                 # Translation catalogs (JSON)
├── tests/                   # Unit and property-based tests
├── pyproject.toml           # Project configuration and dependencies
├── LICENSE                  # MIT License
└── README.md                # Documentation (Portuguese)
```

## Running Tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=src
```

## License

This project is licensed under the [MIT License](LICENSE).

## Author

**William Mendes**

- GitHub: [github.com/wcmendes](http://github.com/wcmendes)
- Lattes: [lattes.cnpq.br/7726054867638395](https://lattes.cnpq.br/7726054867638395)
