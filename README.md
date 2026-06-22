# PDF2LLM

> **PDF to Markdown Converter** — Converte PDFs para Markdown otimizado para uso com modelos de linguagem (LLMs)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg)]()
[![Status](https://img.shields.io/badge/Status-Beta-orange.svg)]()

---

Aplicação desktop para conversão em lote de arquivos PDF para Markdown, ideal para alimentar LLMs como ChatGPT, Claude, Gemini e outros. Preserva a estrutura dos documentos (títulos, tabelas, listas) e oferece OCR automático para PDFs escaneados.

## Funcionalidades

- **Conversão em lote** — selecione até 50 PDFs e converta de uma vez
- **Estrutura preservada** — títulos, parágrafos, listas e tabelas mantidos no Markdown
- **Extração de imagens** — opcional, salva imagens em subpasta organizada
- **OCR automático** — detecta PDFs escaneados e reprocessa com Tesseract + EasyOCR
- **Interface gráfica** — simples, com barra de progresso e seletor de idioma
- **Bilíngue** — Português (Brasil) e Inglês, com troca ao vivo
- **Multiplataforma** — Windows e Linux

## Download

Baixe a versão mais recente na aba [Releases](https://github.com/wcmendes/pdftollm/releases):

| Plataforma | Arquivo |
|-----------|---------|
| Windows | `PDF2LLM.exe` |
| Linux (Debian/Ubuntu) | `pdf2llm_x.x.x_amd64.deb` |

## Requisitos

- **Para o .exe / .deb**: nenhum — tudo incluso
- **Para rodar do código-fonte**: Python 3.10+
- **Tesseract OCR** (opcional): melhora resultados de OCR, mas a aplicação funciona sem ele

### Instalar Tesseract (opcional)

<details>
<summary>Windows</summary>

1. Baixe em https://github.com/UB-Mannheim/tesseract/wiki
2. Instale e adicione ao PATH (ex: `C:\Program Files\Tesseract-OCR`)
</details>

<details>
<summary>Linux (Ubuntu/Debian)</summary>

```bash
sudo apt install tesseract-ocr tesseract-ocr-por
```
</details>

## Uso

### Via executável

Basta abrir o `PDF2LLM.exe` (Windows) ou `pdf2llm` (Linux). A interface guia todo o processo:

1. Selecione os PDFs
2. A pasta de destino é sugerida automaticamente (`/md` ao lado dos PDFs)
3. Clique em **Converter**
4. Ao final, escolha se quer abrir a pasta com os resultados

### Via código-fonte

```bash
git clone https://github.com/wcmendes/pdftollm.git
cd pdftollm
pip install -e .[dev]
python -m src.main
```

## OCR para PDFs escaneados

Após a conversão, se o sistema detectar PDFs que produziram Markdown vazio (documentos digitalizados), ele oferece reprocessamento automático com OCR:

1. **Tesseract** (primário) — rápido e preciso
2. **EasyOCR** (fallback) — baseado em deep learning, já incluso no executável

Se nenhum dos dois conseguir extrair texto, o arquivo original é preservado.

## Estrutura do Projeto

```
pdftollm/
├── src/
│   ├── main.py           # Entry point
│   ├── converters/       # Motor PDF → Markdown
│   ├── gui/              # Interface tkinter
│   ├── i18n/             # Internacionalização
│   ├── models/           # Dataclasses e gerenciadores
│   └── ocr/              # Tesseract + EasyOCR
├── locales/              # Traduções (JSON)
├── tests/                # 246 testes (unitários + propriedade)
├── pyproject.toml        # Dependências e config
└── pdfconverter.spec     # Build PyInstaller
```

## Testes

```bash
pytest                # executa todos
pytest --cov=src      # com cobertura
```

## Licença

[MIT](LICENSE) — William Mendes, 2026

## Autor

**William Mendes**
— [GitHub](http://github.com/wcmendes) · [Lattes](https://lattes.cnpq.br/7726054867638395)
