# PDF to Markdown Converter

Aplicação desktop multiplataforma para conversão em lote de arquivos PDF para Markdown, com extração opcional de imagens e fallback OCR para documentos digitalizados.

## Funcionalidades

- Conversão em lote de múltiplos arquivos PDF para Markdown
- Preservação da estrutura do documento (títulos, parágrafos, listas, tabelas)
- Extração opcional de imagens embutidas nos PDFs
- Fallback OCR automático para PDFs escaneados (Tesseract + EasyOCR)
- Interface gráfica simples e intuitiva (tkinter)
- Internacionalização: Português (Brasil) e Inglês
- Compatível com Linux e Windows

## Requisitos do Sistema

- **Python** 3.10 ou superior
- **Tesseract OCR** (opcional, necessário apenas para PDFs escaneados)
- **Sistema Operacional**: Linux ou Windows 10+

### Instalação do Tesseract (opcional)

O Tesseract é necessário apenas se você deseja usar o recurso de OCR para PDFs baseados em imagem.

**Windows:**

1. Baixe o instalador em: https://github.com/UB-Mannheim/tesseract/wiki
2. Execute o instalador e siga as instruções
3. Adicione o caminho de instalação ao PATH do sistema (ex: `C:\Program Files\Tesseract-OCR`)

**Linux (Ubuntu/Debian):**

```bash
sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-por
```

**Linux (Fedora):**

```bash
sudo dnf install tesseract tesseract-langpack-por
```

## Instalação

1. Clone o repositório:

```bash
git clone https://github.com/wcmendes/PDFConverter_MD_Desktop.git
cd PDFConverter_MD_Desktop
```

2. Crie e ative um ambiente virtual (recomendado):

```bash
python -m venv venv

# Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

3. Instale o projeto com dependências de desenvolvimento:

```bash
pip install -e .[dev]
```

## Uso

### Interface Gráfica

Execute a aplicação com o comando:

```bash
pdfconverter
```

Ou diretamente via módulo Python:

```bash
python -m src.main
```

### Passo a passo

1. Clique em **"Selecionar Arquivos"** para escolher os PDFs que deseja converter
2. Clique em **"Selecionar Pasta de Destino"** para definir onde os arquivos Markdown serão salvos
3. (Opcional) Marque a opção **"Extrair Imagens"** para salvar as imagens embutidas dos PDFs
4. Clique em **"Converter"** para iniciar o processo
5. Acompanhe o progresso pela barra de progresso
6. Ao final, um resumo exibirá quantos arquivos foram convertidos com sucesso

### Fallback OCR

Se a aplicação detectar PDFs escaneados (que geraram Markdown ilegível), ela perguntará se você deseja reprocessá-los com OCR. O sistema tenta primeiro o Tesseract e, se necessário, o EasyOCR como motor secundário.

## Estrutura do Projeto

```
PDFConverter_MD_Desktop/
├── src/
│   ├── main.py              # Ponto de entrada da aplicação
│   ├── converters/          # Motor de conversão PDF → Markdown
│   ├── gui/                 # Interface gráfica (tkinter)
│   ├── i18n/                # Internacionalização
│   ├── models/              # Modelos de dados
│   └── ocr/                 # Motores OCR (Tesseract, EasyOCR)
├── locales/                 # Catálogos de tradução (JSON)
├── tests/                   # Testes unitários e de propriedade
├── pyproject.toml           # Configuração do projeto e dependências
├── LICENSE                  # Licença MIT
└── README.md                # Este arquivo
```

## Executando os Testes

```bash
pytest
```

Com cobertura:

```bash
pytest --cov=src
```

## Licença

Este projeto é licenciado sob a [Licença MIT](LICENSE).

## Autor

**William Mendes**

- GitHub: [github.com/wcmendes](http://github.com/wcmendes)
- Lattes: [lattes.cnpq.br/7726054867638395](https://lattes.cnpq.br/7726054867638395)
