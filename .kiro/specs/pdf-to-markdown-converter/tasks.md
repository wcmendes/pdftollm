# Implementation Plan: PDF to Markdown Converter

## Overview

Plano de implementação da aplicação desktop multiplataforma para conversão em lote de PDFs para Markdown, utilizando Python com tkinter para GUI, PyMuPDF + pymupdf4llm para conversão, Tesseract/EasyOCR para fallback OCR e catálogos JSON para internacionalização. As tarefas estão organizadas por dependência, começando pela estrutura do projeto e modelos de dados, seguindo pela lógica de negócio, GUI e finalmente documentação.

## Tasks

- [x] 1. Estrutura do projeto, dependências e modelos de dados
  - [x] 1.1 Criar estrutura de diretórios e configurar dependências
    - Criar diretório raiz do projeto com `src/`, `src/converters/`, `src/ocr/`, `src/i18n/`, `src/gui/`, `src/models/`, `tests/`, `tests/unit/`, `tests/integration/`, `tests/smoke/`, `tests/fixtures/`, `locales/`
    - Criar `pyproject.toml` ou `requirements.txt` com dependências: PyMuPDF, pymupdf4llm, pytesseract, easyocr, hypothesis, pytest
    - Criar `__init__.py` em todos os módulos
    - _Requirements: 6.1_

  - [x] 1.2 Implementar modelos de dados (dataclasses e enums)
    - Criar `src/models/data_models.py` com todas as dataclasses: `ValidationResult`, `ImageInfo`, `ConversionFileResult`, `AddFilesResult`, `ConversionResult`, `ProgressUpdate`, `OCRCandidate`, `OCRFileResult`, `OCRBatchResult`, `LanguagePreference`
    - Criar enums: `ConversionStatus`, `OCREngineUsed`, `OCRStatus`, `Locale`
    - _Requirements: 3.1, 3.7, 4.4, 8.8_

  - [x]* 1.3 Escrever testes de propriedade para transformação de nomes
    - **Property 2: Transformação de nome PDF para Markdown**
    - Gerar nomes de arquivo aleatórios com extensão `.pdf` e verificar que a saída substitui `.pdf` por `.md` mantendo o restante do nome
    - **Validates: Requirements 3.2**

  - [x]* 1.4 Escrever testes de propriedade para nomenclatura de subpasta de assets
    - **Property 5: Nome da Subpasta de Assets**
    - Gerar nomes base de arquivo e verificar que a subpasta é nomeada `{nome_base}_assets`
    - **Validates: Requirements 4.3**

- [x] 2. FileListManager e validação de PDFs
  - [x] 2.1 Implementar PDFValidator
    - Criar `src/converters/pdf_validator.py` com classe `PDFValidator`
    - Implementar método `validate(file_path)` que verifica se o arquivo é PDF válido usando PyMuPDF (tenta abrir e verificar `page_count > 0`)
    - Detectar PDFs protegidos por senha e corrompidos
    - _Requirements: 1.5, 3.5_

  - [x] 2.2 Implementar FileListManager
    - Criar `src/models/file_list_manager.py` com classe `FileListManager`
    - Implementar limite de 50 arquivos (`MAX_FILES`)
    - Implementar `add_files()` com rejeição de duplicatas, arquivos inválidos e excedentes
    - Implementar `remove_file()` e `clear()`
    - Retornar `AddFilesResult` com listas de aceitos, rejeitados por invalidade, duplicata e limite
    - _Requirements: 1.2, 1.3, 1.5, 1.6_

  - [x]* 2.3 Escrever testes de propriedade para FileListManager
    - **Property 1: Invariantes do FileListManager**
    - Gerar sequências aleatórias de operações (add/remove) e verificar que a lista nunca excede 50 itens, não contém duplicatas e não contém inválidos
    - **Validates: Requirements 1.2, 1.3, 1.5, 1.6**

- [x] 3. Motor de conversão PDF para Markdown
  - [x] 3.1 Implementar PDFConverter
    - Criar `src/converters/pdf_converter.py` com classe `PDFConverter`
    - Implementar `convert(source, output_dir, extract_images)` usando pymupdf4llm para extração de Markdown
    - Implementar `_extract_markdown(doc)` para extrair texto preservando estrutura (títulos, listas, tabelas)
    - Implementar `_extract_images(doc, assets_dir)` para extrair imagens com nomes sequenciais `img_XXX.{formato}`
    - Implementar `_insert_image_references(markdown, images, assets_dir_name)` para inserir `![imageN](caminho_relativo)`
    - Gerar Arquivo_Saída em UTF-8 com terminadores LF
    - _Requirements: 3.2, 3.3, 3.4, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 6.4_

  - [x]* 3.2 Escrever testes de propriedade para nomenclatura sequencial de imagens
    - **Property 6: Nomenclatura sequencial de imagens**
    - Gerar quantidades de 1 a 999 e verificar padrão `img_XXX.{formato}` com zero-padding de 3 dígitos
    - **Validates: Requirements 4.4**

  - [x]* 3.3 Escrever testes de propriedade para referências de imagem no Markdown
    - **Property 7: Referências de imagem no Markdown**
    - Gerar conjuntos de ImageInfo e verificar que o Markdown contém exatamente N referências `![imageN](...)`
    - **Validates: Requirements 4.5**

  - [x]* 3.4 Escrever testes de propriedade para ausência de artefatos quando extração desabilitada
    - **Property 8: Sem artefatos de imagem quando extração desabilitada**
    - Gerar PDFs mock com extração desabilitada e verificar que o Markdown não contém `![...](..._assets/...)` e nenhuma subpasta é criada
    - **Validates: Requirements 4.6**

  - [x]* 3.5 Escrever testes de propriedade para subpasta não criada sem imagens
    - **Property 9: Subpasta não criada para PDFs sem imagens**
    - Gerar PDFs mock sem imagens com extração habilitada e verificar que nenhuma Subpasta_Assets é criada
    - **Validates: Requirements 4.8**

  - [x]* 3.6 Escrever testes de propriedade para codificação e terminadores
    - **Property 11: Codificação e terminadores de saída**
    - Gerar conteúdo com caracteres Unicode variados e verificar que a saída é UTF-8 válido com terminadores LF exclusivos
    - **Validates: Requirements 6.4**

- [x] 4. ConversionManager e progresso
  - [x] 4.1 Implementar ConversionManager
    - Criar `src/converters/conversion_manager.py` com classe `ConversionManager`
    - Implementar `start(files, output_dir, extract_images)` que cria e inicia `threading.Thread`
    - Implementar `_worker()` que processa arquivos sequencialmente, trata erros por arquivo sem interromper o batch
    - Enviar `ProgressUpdate` via `queue.Queue` a cada arquivo processado
    - Enviar resultado final (`ConversionResult`) com `is_complete=True`
    - _Requirements: 3.1, 3.5, 3.7, 5.1, 5.3, 5.4, 7.4_

  - [x]* 4.2 Escrever testes de propriedade para invariante de batch
    - **Property 3: Invariante de conversão em batch**
    - Gerar listas de N arquivos com mocks que podem suceder ou falhar, verificar que `succeeded + failed == total == N`
    - **Validates: Requirements 3.5, 3.7, 5.3, 5.4**

  - [x]* 4.3 Escrever testes de propriedade para consistência de progresso
    - **Property 4: Consistência de progresso**
    - Gerar batches de tamanhos variados e verificar que são emitidas exatamente N mensagens com `current_index` crescente de 1 a N, última com `is_complete == True`
    - **Validates: Requirements 3.1, 5.1**

- [x] 5. Checkpoint - Verificação do motor de conversão
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Sistema de internacionalização (i18n)
  - [x] 6.1 Criar catálogos de tradução JSON
    - Criar `locales/pt-br.json` com todas as strings da interface em Português (Brasil)
    - Criar `locales/en.json` com todas as strings da interface em Inglês
    - Incluir rótulos de botões, mensagens de erro, mensagens de progresso, resumos, diálogos, e textos da Seção_Sobre
    - _Requirements: 10.1, 10.6_

  - [x] 6.2 Implementar I18nManager
    - Criar `src/i18n/i18n_manager.py` com classes `Locale` e `I18nManager`
    - Implementar `_load_catalogs()` para carregar JSONs de tradução
    - Implementar `t(key)` para traduzir chave ao idioma ativo (retorna a chave se não encontrada)
    - Implementar `set_locale(locale)` com notificação de listeners registrados
    - Implementar `register_listener(callback)` para atualização ao vivo da GUI
    - Implementar persistência de preferência em `~/.config/pdfconverter/` (Linux) / `%APPDATA%/pdfconverter/` (Windows)
    - Usar PT_BR como padrão quando sem preferência salva
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

  - [x]* 6.3 Escrever testes de propriedade para completude do catálogo
    - **Property 17: Completude do catálogo de traduções**
    - Iterar todas as chaves registradas × todos os locales e verificar que cada tradução existe e é string não-vazia
    - **Validates: Requirements 10.1, 10.6**

  - [x]* 6.4 Escrever testes de propriedade para consistência da troca de idioma
    - **Property 18: Consistência da troca de idioma ao vivo**
    - Gerar sequências de trocas de locale e verificar que `t(key)` sempre retorna texto do locale ativo
    - **Validates: Requirements 10.3**

  - [x]* 6.5 Escrever testes de propriedade para persistência de preferência (round-trip)
    - **Property 19: Persistência de preferência de idioma (round-trip)**
    - Salvar locale aleatório e carregar imediatamente, verificar que retorna o mesmo locale
    - **Validates: Requirements 10.4**

- [x] 7. Sistema OCR com fallback
  - [x] 7.1 Implementar MarkdownQualityDetector
    - Criar `src/ocr/markdown_quality_detector.py` com classe `MarkdownQualityDetector`
    - Implementar `is_illegible(markdown_content, page_count)` com limiar de 50 chars alfanuméricos por página
    - Implementar `detect_ocr_candidates(results)` que analisa cada Arquivo_Saída e retorna lista de `OCRCandidate`
    - _Requirements: 8.1, 8.2_

  - [x] 7.2 Implementar OCREngine, TesseractEngine e EasyOCREngine
    - Criar `src/ocr/ocr_engine.py` com classe abstrata `OCREngine`
    - Criar `src/ocr/tesseract_engine.py` com `TesseractEngine` usando pytesseract + pdf2image
    - Criar `src/ocr/easyocr_engine.py` com `EasyOCREngine` usando easyocr
    - Ambos implementam `extract_text(pdf_path) -> str`
    - _Requirements: 8.4, 8.5_

  - [x] 7.3 Implementar OCRManager
    - Criar `src/ocr/ocr_manager.py` com classe `OCRManager`
    - Implementar `process_batch(ocr_candidates, output_dir)` com progresso via Queue
    - Implementar `_process_single(candidate, output_dir)` com cadeia de fallback: Tesseract → EasyOCR → preserva original
    - Backup do conteúdo original antes de tentar OCR; restaurar se ambos falharem
    - Emitir mensagens de progresso OCR para cada arquivo processado
    - _Requirements: 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_

  - [x]* 7.4 Escrever testes de propriedade para detecção de Markdown ilegível
    - **Property 12: Detecção de Markdown ilegível**
    - Gerar strings com densidades variadas de chars alfanuméricos e page_count, verificar classificação correta como legível/ilegível
    - **Validates: Requirements 8.1**

  - [x]* 7.5 Escrever testes de propriedade para cadeia de fallback OCR
    - **Property 13: Cadeia de fallback OCR**
    - Gerar cenários com mocks de motores que retornam textos de qualidade variável, verificar que Tesseract é sempre invocado primeiro e EasyOCR só quando Tesseract falha
    - **Validates: Requirements 8.4, 8.5**

  - [x]* 7.6 Escrever testes de propriedade para falha total preserva original
    - **Property 14: Falha total de OCR preserva original**
    - Gerar cenários com ambos motores falhando, verificar que o Arquivo_Saída original permanece inalterado (byte a byte)
    - **Validates: Requirements 8.6**

  - [x]* 7.7 Escrever testes de propriedade para consistência de progresso OCR
    - **Property 15: Consistência de progresso OCR**
    - Gerar batches OCR de tamanhos variados, verificar exatamente N mensagens com índice crescente de 1 a N
    - **Validates: Requirements 8.7**

  - [x]* 7.8 Escrever testes de propriedade para completude do resumo OCR
    - **Property 16: Completude do resumo OCR**
    - Gerar resultados OCR com combinações de sucesso/falha, verificar que `recovered + failed == total` e `engine_used` é válido
    - **Validates: Requirements 8.8**

- [x] 8. Checkpoint - Verificação da lógica de negócio
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Interface gráfica principal (MainWindow)
  - [x] 9.1 Implementar MainWindow com layout e widgets
    - Criar `src/gui/main_window.py` com classe `MainWindow`
    - Implementar layout: área de listagem de arquivos (Listbox com scrollbar), botão seleção de arquivos, campo de Pasta_Destino com botão, checkbox de extração de imagens, botão "Converter", Barra_Progresso (ttk.Progressbar), label de arquivo atual, Seletor_Idioma
    - Integrar `I18nManager` para todos os textos dos widgets
    - Registrar listener para atualização ao vivo dos textos na troca de idioma
    - _Requirements: 7.1, 7.2, 7.3, 10.2, 10.3_

  - [x] 9.2 Implementar lógica de interação da MainWindow
    - Implementar `select_files()` usando `tkinter.filedialog.askopenfilenames` com filtro PDF
    - Implementar `select_output_folder()` usando `tkinter.filedialog.askdirectory`
    - Implementar `remove_selected_file()` para remoção da lista
    - Implementar `start_conversion()` com validações (lista vazia, pasta não selecionada, permissão)
    - Implementar `update_progress(current, total, filename)` com truncamento a 60 chars + "..."
    - Implementar `show_summary(result)` para resumo de conversão
    - Desabilitar botão converter durante processamento, reabilitar ao final
    - Implementar polling da Queue via `root.after()` para atualizar GUI a partir da thread worker
    - _Requirements: 1.1, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.6, 5.1, 5.2, 5.3, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [x]* 9.3 Escrever testes de propriedade para truncamento de nomes
    - **Property 10: Truncamento de nomes longos no progresso**
    - Gerar strings de comprimento variável e verificar que nomes > 60 chars resultam em no máximo 63 chars (60 + "..."), e nomes ≤ 60 chars são mantidos sem alteração
    - **Validates: Requirements 5.2**

- [x] 10. Integração do fluxo OCR na GUI
  - [x] 10.1 Implementar fluxo pós-conversão com detecção OCR
    - Na `MainWindow`, após conversão concluída, invocar `MarkdownQualityDetector.detect_ocr_candidates()`
    - Se candidatos OCR detectados, exibir lista ao usuário e perguntar se deseja reprocessar
    - Se confirmado, iniciar thread OCR com `OCRManager.process_batch()`
    - Implementar polling de progresso OCR e atualização da Barra_Progresso
    - Exibir resumo OCR ao final (recuperados, falhas, motor usado)
    - Se usuário recusar, manter arquivos originais e encerrar fluxo
    - _Requirements: 8.1, 8.2, 8.3, 8.7, 8.8, 8.9_

- [x] 11. AboutDialog
  - [x] 11.1 Implementar diálogo Sobre
    - Criar `src/gui/about_dialog.py` com classe `AboutDialog`
    - Exibir como janela modal (Toplevel + grab_set)
    - Mostrar: nome do autor (William Mendes), link GitHub (http://github.com/wcmendes), link Lattes (https://lattes.cnpq.br/7726054867638395), versão da aplicação, ano de publicação
    - Implementar `_open_link(url)` usando `webbrowser.open()`
    - Integrar com `I18nManager` para textos traduzíveis
    - Adicionar botão ou menu "Sobre" na MainWindow
    - _Requirements: 9.1, 9.5, 9.6_

- [x] 12. Checkpoint - Verificação da GUI e integração
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Ponto de entrada e documentação
  - [x] 13.1 Criar ponto de entrada da aplicação
    - Criar `src/main.py` como entry point
    - Inicializar `tk.Tk()`, instanciar `I18nManager`, `MainWindow`
    - Configurar título da janela, tamanho mínimo, ícone (se disponível)
    - Chamar `root.mainloop()`
    - _Requirements: 7.1_

  - [x] 13.2 Criar arquivo de licença MIT
    - Criar `LICENSE` na raiz do projeto com texto completo da licença MIT
    - Nome do autor: William Mendes, ano atual
    - _Requirements: 9.2_

  - [x] 13.3 Criar README bilíngue
    - Criar `README.md` em Português (Brasil) com: descrição do projeto, requisitos do sistema (Python 3.10+, Tesseract), tutorial de instalação passo a passo, instruções de uso, informações de licença
    - Criar `README_EN.md` em Inglês com o mesmo conteúdo traduzido
    - _Requirements: 9.3, 9.4_

- [x] 14. Checkpoint final
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tarefas marcadas com `*` são opcionais e podem ser ignoradas para um MVP mais rápido
- Cada tarefa referencia requisitos específicos para rastreabilidade
- Checkpoints garantem validação incremental a cada grupo lógico de funcionalidades
- Testes de propriedade validam propriedades universais de corretude definidas no documento de design
- Testes unitários validam exemplos específicos e casos de borda
- A biblioteca Hypothesis é usada para property-based testing em Python
- pytest é o framework de testes principal

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2"] },
    { "id": 2, "tasks": ["1.3", "1.4", "2.1", "6.1"] },
    { "id": 3, "tasks": ["2.2", "6.2"] },
    { "id": 4, "tasks": ["2.3", "3.1", "6.3", "6.4", "6.5"] },
    { "id": 5, "tasks": ["3.2", "3.3", "3.4", "3.5", "3.6", "4.1"] },
    { "id": 6, "tasks": ["4.2", "4.3", "7.1"] },
    { "id": 7, "tasks": ["7.2"] },
    { "id": 8, "tasks": ["7.3", "7.4"] },
    { "id": 9, "tasks": ["7.5", "7.6", "7.7", "7.8"] },
    { "id": 10, "tasks": ["9.1"] },
    { "id": 11, "tasks": ["9.2", "9.3", "11.1"] },
    { "id": 12, "tasks": ["10.1"] },
    { "id": 13, "tasks": ["13.1", "13.2", "13.3"] }
  ]
}
```
