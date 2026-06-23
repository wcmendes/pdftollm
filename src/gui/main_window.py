"""Janela principal da aplicação PDF to Markdown Converter.

Contém a classe MainWindow com todos os widgets de interface gráfica,
integrada com I18nManager para suporte a múltiplos idiomas com troca ao vivo.
"""

import logging
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from src.converters.conversion_manager import ConversionManager
from src.gui.about_dialog import AboutDialog
from src.i18n.i18n_manager import I18nManager
from src.models.data_models import ConversionResult, Locale, OCRBatchResult, ProgressUpdate
from src.models.file_list_manager import FileListManager
from src.ocr.easyocr_engine import EasyOCREngine
from src.ocr.markdown_quality_detector import MarkdownQualityDetector
from src.ocr.ocr_manager import OCRManager
from src.ocr.tesseract_engine import TesseractEngine, is_tesseract_available

logger = logging.getLogger(__name__)

# Máximo de caracteres para exibição de nomes de arquivo no progresso
MAX_FILENAME_DISPLAY = 60

# Intervalo de polling da fila de progresso (milissegundos)
POLL_INTERVAL_MS = 100


class MainWindow:
    """Janela principal da aplicação.

    Apresenta todos os widgets de interação: listagem de arquivos,
    seleção de pasta de destino, opções de conversão, barra de progresso
    e seletor de idioma. Todos os textos são gerenciados via I18nManager
    para suporte à internacionalização com atualização ao vivo.
    """

    def __init__(self, root: tk.Tk, i18n: I18nManager) -> None:
        """Inicializa a janela principal com todos os widgets.

        Args:
            root: Instância raiz do tkinter.
            i18n: Gerenciador de internacionalização para textos da GUI.
        """
        self.root = root
        self.i18n = i18n

        # Gerenciador de lista de arquivos
        self._file_list_manager = FileListManager()

        # Fila de comunicação com a thread de conversão
        self._progress_queue: queue.Queue[ProgressUpdate] = queue.Queue()

        # Gerenciador de conversão
        self._conversion_manager = ConversionManager(self._progress_queue)

        # Caminho da pasta de destino selecionada
        self._output_folder_path: Path | None = None

        # Flag indicando se conversão está em andamento
        self._is_converting = False

        # Variáveis de controle do tkinter
        self._extract_images_var = tk.BooleanVar(value=False)
        self._language_var = tk.StringVar()
        self._output_folder_var = tk.StringVar(value=self.i18n.t("labels.output_folder_none"))
        self._current_file_var = tk.StringVar(value="")

        # Configuração da janela
        self.root.title(self.i18n.t("window.title"))
        self.root.minsize(700, 550)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Construir layout
        self._build_layout()

        # Definir idioma atual no seletor
        self._set_language_selector_value()

        # Registrar listener para atualização ao vivo dos textos
        self.i18n.register_listener(self._update_texts)

        # Vincular comandos dos botões
        self._bind_commands()

        # Configurar drag-and-drop (se tkinterdnd2 estiver disponível)
        self._setup_drag_and_drop()

    def _bind_commands(self) -> None:
        """Vincula os comandos de interação aos widgets."""
        self._select_files_button.config(command=self.select_files)
        self._remove_file_button.config(command=self.remove_selected_file)
        self._clear_list_button.config(command=self._clear_file_list)
        self._select_folder_button.config(command=self.select_output_folder)
        self._convert_button.config(command=self.start_conversion)
        self._language_combo.bind("<<ComboboxSelected>>", self._on_language_changed)

    def _setup_drag_and_drop(self) -> None:
        """Configura drag-and-drop de arquivos PDF para a listbox.

        Usa tkinterdnd2 se disponível. Caso contrário, ignora silenciosamente.
        """
        try:
            from tkinterdnd2 import DND_FILES
            self._file_listbox.drop_target_register(DND_FILES)
            self._file_listbox.dnd_bind("<<Drop>>", self._on_files_dropped)
        except (ImportError, Exception) as e:
            logger.debug("Drag-and-drop não disponível: %s", e)

    def _on_files_dropped(self, event) -> None:
        """Handler para arquivos arrastados para a interface.

        Processa os caminhos recebidos via drag-and-drop, filtra apenas .pdf
        e adiciona ao FileListManager.
        """
        # tkinterdnd2 retorna paths separados por espaço, com {} em volta se tiver espaços
        raw_data = event.data
        # Parse: paths entre chaves ou separados por espaço
        paths: list[Path] = []
        if "{" in raw_data:
            # Formato: {path with spaces} {another path}
            import re
            matches = re.findall(r"\{([^}]+)\}", raw_data)
            paths = [Path(m) for m in matches if m.lower().endswith(".pdf")]
        else:
            # Formato simples: path1 path2
            for p in raw_data.split():
                if p.lower().endswith(".pdf"):
                    paths.append(Path(p))

        if not paths:
            return

        result = self._file_list_manager.add_files(paths)
        self._refresh_file_listbox()

        # Atualizar pasta de destino com pasta do último arquivo
        if result.accepted:
            source_folder = result.accepted[-1].parent
            self._output_folder_path = source_folder
            self._output_folder_var.set(str(source_folder))

        self._notify_rejections(result)

    def _build_layout(self) -> None:
        """Constrói o layout completo da janela principal."""
        # Frame principal com padding
        self._main_frame = ttk.Frame(self.root, padding=10)
        self._main_frame.grid(row=0, column=0, sticky="nsew")
        self._main_frame.columnconfigure(0, weight=1)

        row = 0

        # ─── Seção: Cabeçalho com Seletor de Idioma e botão Sobre ────────
        row = self._build_header(row)

        # ─── Seção: Lista de Arquivos ────────────────────────────────────
        row = self._build_file_list_section(row)

        # ─── Seção: Botões de arquivo (Selecionar / Remover) ─────────────
        row = self._build_file_buttons(row)

        # ─── Seção: Pasta de Destino ─────────────────────────────────────
        row = self._build_output_folder_section(row)

        # ─── Seção: Opções de Conversão ──────────────────────────────────
        row = self._build_options_section(row)

        # ─── Seção: Botão Converter ──────────────────────────────────────
        row = self._build_convert_button(row)

        # ─── Seção: Progresso ────────────────────────────────────────────
        row = self._build_progress_section(row)

        # ─── Seção: Status do Tesseract OCR ──────────────────────────────
        row = self._build_tesseract_status(row)

        # ─── Rodapé ─────────────────────────────────────────────────────
        row = self._build_footer(row)

    def _build_header(self, row: int) -> int:
        """Constrói o cabeçalho com seletor de idioma e botão Sobre.

        Args:
            row: Linha atual no grid.

        Returns:
            Próxima linha disponível no grid.
        """
        header_frame = ttk.Frame(self._main_frame)
        header_frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        header_frame.columnconfigure(1, weight=1)

        # Seletor de idioma
        self._language_label = ttk.Label(
            header_frame, text=self.i18n.t("labels.language")
        )
        self._language_label.grid(row=0, column=0, padx=(0, 5))

        self._language_combo = ttk.Combobox(
            header_frame,
            textvariable=self._language_var,
            values=[
                self.i18n.t("language.pt_br"),
                self.i18n.t("language.en"),
            ],
            state="readonly",
            width=20,
        )
        self._language_combo.grid(row=0, column=1, sticky="w")

        # Botão Sobre
        self._about_button = ttk.Button(
            header_frame, text=self.i18n.t("buttons.about"), command=self._show_about
        )
        self._about_button.grid(row=0, column=2, padx=(10, 0))

        return row + 1

    def _build_file_list_section(self, row: int) -> int:
        """Constrói a seção de listagem de arquivos com scrollbar.

        Args:
            row: Linha atual no grid.

        Returns:
            Próxima linha disponível no grid.
        """
        # Label da lista de arquivos
        self._file_list_label = ttk.Label(
            self._main_frame, text=self.i18n.t("labels.file_list")
        )
        self._file_list_label.grid(row=row, column=0, sticky="w", pady=(0, 2))
        row += 1

        # Frame para Listbox + Scrollbar
        list_frame = ttk.Frame(self._main_frame)
        list_frame.grid(row=row, column=0, sticky="nsew", pady=(0, 5))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        self._main_frame.rowconfigure(row, weight=1)

        # Scrollbar vertical
        self._file_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self._file_scrollbar.grid(row=0, column=1, sticky="ns")

        # Listbox de arquivos
        self._file_listbox = tk.Listbox(
            list_frame,
            selectmode=tk.EXTENDED,
            yscrollcommand=self._file_scrollbar.set,
            height=10,
        )
        self._file_listbox.grid(row=0, column=0, sticky="nsew")
        self._file_scrollbar.config(command=self._file_listbox.yview)

        return row + 1

    def _build_file_buttons(self, row: int) -> int:
        """Constrói os botões de seleção e remoção de arquivos.

        Args:
            row: Linha atual no grid.

        Returns:
            Próxima linha disponível no grid.
        """
        btn_frame = ttk.Frame(self._main_frame)
        btn_frame.grid(row=row, column=0, sticky="w", pady=(0, 10))

        self._select_files_button = ttk.Button(
            btn_frame, text=self.i18n.t("buttons.select_files")
        )
        self._select_files_button.grid(row=0, column=0, padx=(0, 5))

        self._remove_file_button = ttk.Button(
            btn_frame, text=self.i18n.t("buttons.remove_file")
        )
        self._remove_file_button.grid(row=0, column=1, padx=(0, 5))

        self._clear_list_button = ttk.Button(
            btn_frame, text=self.i18n.t("buttons.clear_list")
        )
        self._clear_list_button.grid(row=0, column=2)

        return row + 1

    def _build_output_folder_section(self, row: int) -> int:
        """Constrói a seção de seleção de pasta de destino.

        Args:
            row: Linha atual no grid.

        Returns:
            Próxima linha disponível no grid.
        """
        folder_frame = ttk.Frame(self._main_frame)
        folder_frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        folder_frame.columnconfigure(1, weight=1)

        self._output_folder_label = ttk.Label(
            folder_frame, text=self.i18n.t("labels.output_folder")
        )
        self._output_folder_label.grid(row=0, column=0, padx=(0, 5))

        self._output_folder_entry = ttk.Entry(
            folder_frame,
            textvariable=self._output_folder_var,
            state="readonly",
        )
        self._output_folder_entry.grid(row=0, column=1, sticky="ew", padx=(0, 5))

        self._select_folder_button = ttk.Button(
            folder_frame, text=self.i18n.t("buttons.select_folder")
        )
        self._select_folder_button.grid(row=0, column=2)

        return row + 1

    def _build_options_section(self, row: int) -> int:
        """Constrói a seção de opções de conversão (checkbox de imagens).

        Args:
            row: Linha atual no grid.

        Returns:
            Próxima linha disponível no grid.
        """
        self._extract_images_check = ttk.Checkbutton(
            self._main_frame,
            text=self.i18n.t("labels.extract_images"),
            variable=self._extract_images_var,
        )
        self._extract_images_check.grid(row=row, column=0, sticky="w", pady=(0, 10))

        return row + 1

    def _build_convert_button(self, row: int) -> int:
        """Constrói o botão de iniciar conversão.

        Args:
            row: Linha atual no grid.

        Returns:
            Próxima linha disponível no grid.
        """
        self._convert_button = ttk.Button(
            self._main_frame, text=self.i18n.t("buttons.convert")
        )
        self._convert_button.grid(row=row, column=0, sticky="ew", pady=(0, 10))

        return row + 1

    def _build_progress_section(self, row: int) -> int:
        """Constrói a seção de progresso (barra e label de arquivo atual).

        Args:
            row: Linha atual no grid.

        Returns:
            Próxima linha disponível no grid.
        """
        # Barra de progresso
        self._progress_bar = ttk.Progressbar(
            self._main_frame,
            mode="determinate",
            maximum=100,
        )
        self._progress_bar.grid(row=row, column=0, sticky="ew", pady=(0, 2))
        row += 1

        # Label do arquivo atual sendo processado
        self._current_file_label = ttk.Label(
            self._main_frame,
            textvariable=self._current_file_var,
            anchor="w",
        )
        self._current_file_label.grid(row=row, column=0, sticky="ew")

        return row + 1

    def _build_tesseract_status(self, row: int) -> int:
        """Constrói o indicador de status do Tesseract OCR.

        Mostra se o Tesseract está instalado ou não, com recomendação
        de instalação caso não esteja disponível.

        Args:
            row: Linha atual no grid.

        Returns:
            Próxima linha disponível no grid.
        """
        self._tesseract_available = is_tesseract_available()

        if self._tesseract_available:
            status_text = self.i18n.t("labels.tesseract_available")
            fg_color = "green"
        else:
            status_text = self.i18n.t("labels.tesseract_missing")
            fg_color = "#B8860B"  # dark goldenrod (amarelo escuro legível)

        tess_frame = ttk.Frame(self._main_frame)
        tess_frame.grid(row=row, column=0, sticky="w", pady=(8, 0))

        self._tesseract_status_label = ttk.Label(
            tess_frame,
            text=status_text,
            foreground=fg_color,
            font=("TkDefaultFont", 8),
        )
        self._tesseract_status_label.pack(side="left")

        if not self._tesseract_available:
            install_link = ttk.Label(
                tess_frame,
                text="  [Instalar]",
                foreground="#0066CC",
                font=("TkDefaultFont", 8, "underline"),
                cursor="hand2",
            )
            install_link.pack(side="left")
            install_link.bind("<Button-1>", lambda e: __import__('webbrowser').open(
                "https://github.com/UB-Mannheim/tesseract/wiki"
            ))

        return row + 1

    def _build_footer(self, row: int) -> int:
        """Constrói o rodapé discreto com link do autor.

        Args:
            row: Linha atual no grid.

        Returns:
            Próxima linha disponível no grid.
        """
        self._footer_label = ttk.Label(
            self._main_frame,
            text="William Mendes",
            foreground="gray",
            cursor="hand2",
            font=("TkDefaultFont", 7),
        )
        self._footer_label.grid(row=row, column=0, sticky="e", pady=(4, 0))
        self._footer_label.bind(
            "<Button-1>",
            lambda e: __import__("webbrowser").open("https://lattes.cnpq.br/7726054867638395"),
        )

        return row + 1

    # ─── Métodos de interação ────────────────────────────────────────────────

    def select_files(self) -> None:
        """Abre diálogo nativo para seleção de arquivos PDF.

        Utiliza tkinter.filedialog.askopenfilenames com filtro para .pdf.
        Os arquivos selecionados são validados e adicionados ao FileListManager.
        Caso haja rejeições, exibe mensagem informativa ao usuário.
        Sugere automaticamente uma subpasta 'md' na pasta de origem como destino.
        """
        file_paths = filedialog.askopenfilenames(
            title=self.i18n.t("buttons.select_files"),
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )

        if not file_paths:
            return

        paths = [Path(fp) for fp in file_paths]
        result = self._file_list_manager.add_files(paths)

        # Atualizar a Listbox com os novos arquivos aceitos
        self._refresh_file_listbox()

        # Sempre atualizar pasta de destino com a pasta do último arquivo aceito
        if result.accepted:
            source_folder = result.accepted[-1].parent
            self._output_folder_path = source_folder
            self._output_folder_var.set(str(source_folder))

        # Notificar rejeições ao usuário
        self._notify_rejections(result)

    def select_output_folder(self) -> None:
        """Abre diálogo nativo para seleção da pasta de destino.

        Utiliza tkinter.filedialog.askdirectory. Se o usuário cancelar,
        mantém a pasta anteriormente selecionada (ou vazia).
        """
        folder = filedialog.askdirectory(
            title=self.i18n.t("buttons.select_folder"),
        )

        if not folder:
            # Usuário cancelou - manter pasta anterior
            return

        folder_path = Path(folder)

        # Verificar permissão de escrita
        if not self._check_write_permission(folder_path):
            messagebox.showerror(
                self.i18n.t("window.title"),
                self.i18n.t("errors.no_write_permission").replace(
                    "{folder}", str(folder_path)
                ),
            )
            return

        self._output_folder_path = folder_path
        self._output_folder_var.set(str(folder_path))

    def remove_selected_file(self) -> None:
        """Remove os arquivos selecionados na Listbox da lista.

        Obtém os índices selecionados na Listbox, remove os arquivos
        correspondentes do FileListManager e atualiza a exibição.
        """
        selected_indices = self._file_listbox.curselection()
        if not selected_indices:
            return

        # Obter arquivos pelos índices (em ordem reversa para não invalidar índices)
        files = self._file_list_manager.files
        for index in reversed(selected_indices):
            if index < len(files):
                self._file_list_manager.remove_file(files[index])

        self._refresh_file_listbox()

    def start_conversion(self) -> None:
        """Valida pré-condições e inicia a conversão em thread separada.

        Validações:
        - Lista de arquivos não pode estar vazia
        - Pasta de destino deve estar selecionada
        - Pasta de destino deve ter permissão de escrita

        Desabilita o botão converter e inicia o polling da fila de progresso.
        """
        # Validar lista de arquivos
        if self._file_list_manager.count == 0:
            messagebox.showwarning(
                self.i18n.t("window.title"),
                self.i18n.t("errors.no_files_selected"),
            )
            return

        # Validar pasta de destino
        if self._output_folder_path is None:
            messagebox.showwarning(
                self.i18n.t("window.title"),
                self.i18n.t("errors.no_folder_selected"),
            )
            return

        # Verificar permissão de escrita novamente
        if not self._check_write_permission(self._output_folder_path):
            messagebox.showerror(
                self.i18n.t("window.title"),
                self.i18n.t("errors.no_write_permission").replace(
                    "{folder}", str(self._output_folder_path)
                ),
            )
            return

        # Desabilitar botão converter durante o processamento
        self._set_converting_state(True)

        # Garantir que pasta de destino existe
        self._output_folder_path.mkdir(parents=True, exist_ok=True)

        # Resetar barra de progresso
        self._progress_bar["value"] = 0
        self._current_file_var.set(self.i18n.t("progress.processing"))

        # Iniciar conversão na thread de trabalho
        self._conversion_manager.start(
            files=self._file_list_manager.files,
            output_dir=self._output_folder_path,
            extract_images=self._extract_images_var.get(),
        )

        # Iniciar polling da fila de progresso
        self._poll_progress_queue()

    def update_progress(self, current: int, total: int, filename: str) -> None:
        """Atualiza barra de progresso e nome do arquivo atual.

        Trunca nomes de arquivo com mais de 60 caracteres adicionando "...".

        Args:
            current: Índice do arquivo atual (1-based).
            total: Total de arquivos no batch.
            filename: Nome do arquivo sendo processado.
        """
        # Calcular porcentagem
        percentage = (current / total) * 100 if total > 0 else 0
        self._progress_bar["value"] = percentage

        # Truncar nome do arquivo se necessário
        display_name = truncate_filename(filename)

        # Atualizar label com informações de progresso
        progress_text = self.i18n.t("progress.converting").replace(
            "{current}", str(current)
        ).replace(
            "{total}", str(total)
        ).replace(
            "{filename}", display_name
        )
        self._current_file_var.set(progress_text)

    def show_summary(self, result: ConversionResult) -> None:
        """Exibe resumo final da conversão em um messagebox.

        Após exibir o resumo, pergunta se o usuário deseja abrir a pasta de destino.

        Args:
            result: Resultado da conversão com contadores de sucesso e falha.
        """
        summary_lines = [
            self.i18n.t("summary.total_processed").replace(
                "{total}", str(result.total)
            ),
            self.i18n.t("summary.files_converted").replace(
                "{count}", str(result.succeeded)
            ),
            self.i18n.t("summary.files_failed").replace(
                "{count}", str(result.failed)
            ),
        ]

        messagebox.showinfo(
            self.i18n.t("summary.title"),
            "\n".join(summary_lines),
        )

        # Perguntar se deseja abrir a pasta de destino
        if self._output_folder_path and self._output_folder_path.exists():
            open_folder = messagebox.askyesno(
                self.i18n.t("summary.title"),
                self.i18n.t("summary.open_folder"),
            )
            if open_folder:
                import os
                import subprocess
                import sys

                folder_str = str(self._output_folder_path)
                if sys.platform == "win32":
                    os.startfile(folder_str)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", folder_str])
                else:
                    subprocess.Popen(["xdg-open", folder_str])

    # ─── Métodos internos ────────────────────────────────────────────────────

    def _poll_progress_queue(self) -> None:
        """Faz polling da fila de progresso via root.after().

        Verifica se há mensagens de ProgressUpdate na fila e processa cada uma.
        Quando recebe is_complete=True, finaliza o polling e exibe o resumo.
        Caso contrário, agenda novo polling após POLL_INTERVAL_MS.
        """
        try:
            while True:
                update: ProgressUpdate = self._progress_queue.get_nowait()

                if update.is_complete:
                    # Conversão finalizada
                    self._progress_bar["value"] = 100
                    self._current_file_var.set(
                        self.i18n.t("progress.conversion_complete")
                    )
                    self._set_converting_state(False)

                    if update.result is not None:
                        self.show_summary(update.result)
                        # Verificar candidatos a OCR após conversão
                        self._check_ocr_candidates(update.result)
                    return

                # Atualizar progresso intermediário
                self.update_progress(
                    update.current_index,
                    update.total,
                    update.current_filename,
                )

        except queue.Empty:
            pass

        # Agendar próximo polling
        if self._is_converting:
            self.root.after(POLL_INTERVAL_MS, self._poll_progress_queue)

    def _set_converting_state(self, is_converting: bool) -> None:
        """Define o estado de conversão, habilitando/desabilitando widgets.

        Args:
            is_converting: True para desabilitar controles durante conversão.
        """
        self._is_converting = is_converting
        state = "disabled" if is_converting else "normal"
        self._convert_button.config(state=state)
        self._select_files_button.config(state=state)
        self._remove_file_button.config(state=state)
        self._clear_list_button.config(state=state)
        self._select_folder_button.config(state=state)

    def _refresh_file_listbox(self) -> None:
        """Atualiza a Listbox com a lista atual de arquivos do FileListManager."""
        self._file_listbox.delete(0, tk.END)
        for file_path in self._file_list_manager.files:
            # Exibir nome do arquivo truncado se necessário
            display_name = truncate_filename(file_path.name)
            self._file_listbox.insert(tk.END, f"{display_name}  ({file_path})")

    def _clear_file_list(self) -> None:
        """Limpa toda a lista de arquivos."""
        self._file_list_manager.clear()
        self._refresh_file_listbox()

    def _notify_rejections(self, result) -> None:
        """Notifica o usuário sobre arquivos rejeitados.

        Args:
            result: AddFilesResult com listas de arquivos rejeitados.
        """
        messages = []

        # Arquivos inválidos
        for file_path, reason in result.rejected_invalid:
            messages.append(
                self.i18n.t("errors.invalid_file")
                .replace("{filename}", file_path.name)
                .replace("{reason}", reason)
            )

        # Duplicatas
        for file_path in result.rejected_duplicate:
            messages.append(
                self.i18n.t("errors.duplicate_file").replace(
                    "{filename}", file_path.name
                )
            )

        # Limite atingido
        if result.rejected_limit:
            messages.append(
                self.i18n.t("errors.max_files_reached").replace(
                    "{count}", str(len(result.rejected_limit))
                )
            )

        if messages:
            messagebox.showwarning(
                self.i18n.t("dialogs.files_rejected_title"),
                "\n".join(messages),
            )

    def _check_write_permission(self, folder: Path) -> bool:
        """Verifica se a pasta possui permissão de escrita.

        Args:
            folder: Caminho da pasta a verificar.

        Returns:
            True se a pasta é gravável, False caso contrário.
        """
        import os

        return os.access(folder, os.W_OK)

    def _on_language_changed(self, event: tk.Event) -> None:
        """Evento de troca de idioma no seletor.

        Mapeia o valor selecionado no Combobox para o Locale correspondente
        e chama i18n.set_locale() para atualizar toda a interface.
        """
        selected = self._language_var.get()

        # Mapear texto selecionado para Locale
        # Comparar com textos atuais do catálogo (independente do idioma ativo)
        if selected == self.i18n.t("language.pt_br"):
            new_locale = Locale.PT_BR
        elif selected == self.i18n.t("language.en"):
            new_locale = Locale.EN
        else:
            # Fallback: tentar comparar com textos fixos
            if "Portugu" in selected:
                new_locale = Locale.PT_BR
            else:
                new_locale = Locale.EN

        if new_locale != self.i18n.current_locale:
            self.i18n.set_locale(new_locale)

    def _set_language_selector_value(self) -> None:
        """Define o valor atual do seletor de idioma baseado no locale ativo."""
        locale = self.i18n.current_locale
        if locale == Locale.PT_BR:
            self._language_var.set(self.i18n.t("language.pt_br"))
        else:
            self._language_var.set(self.i18n.t("language.en"))

    def _update_texts(self) -> None:
        """Atualiza todos os textos dos widgets ao vivo na troca de idioma.

        Este método é registrado como listener no I18nManager e é chamado
        automaticamente quando o idioma é alterado.
        """
        # Título da janela
        self.root.title(self.i18n.t("window.title"))

        # Header - Idioma e Sobre
        self._language_label.config(text=self.i18n.t("labels.language"))
        self._language_combo.config(
            values=[
                self.i18n.t("language.pt_br"),
                self.i18n.t("language.en"),
            ]
        )
        self._about_button.config(text=self.i18n.t("buttons.about"))

        # Lista de arquivos
        self._file_list_label.config(text=self.i18n.t("labels.file_list"))

        # Botões de arquivo
        self._select_files_button.config(text=self.i18n.t("buttons.select_files"))
        self._remove_file_button.config(text=self.i18n.t("buttons.remove_file"))
        self._clear_list_button.config(text=self.i18n.t("buttons.clear_list"))

        # Pasta de destino
        self._output_folder_label.config(text=self.i18n.t("labels.output_folder"))
        self._select_folder_button.config(text=self.i18n.t("buttons.select_folder"))

        # Opções
        self._extract_images_check.config(text=self.i18n.t("labels.extract_images"))

        # Botão converter
        self._convert_button.config(text=self.i18n.t("buttons.convert"))

        # Atualizar valor do seletor de idioma
        self._set_language_selector_value()

        # Atualizar placeholder da pasta de destino se nenhuma selecionada
        if self._output_folder_path is None:
            self._output_folder_var.set(self.i18n.t("labels.output_folder_none"))

        # Atualizar status do Tesseract
        if self._tesseract_available:
            self._tesseract_status_label.config(
                text=self.i18n.t("labels.tesseract_available")
            )
        else:
            self._tesseract_status_label.config(
                text=self.i18n.t("labels.tesseract_missing")
            )

    def _show_about(self) -> None:
        """Exibe o diálogo Sobre da aplicação."""
        about_dialog = AboutDialog(self.root, self.i18n)
        about_dialog.show()

    # ─── OCR Post-Conversion Flow ────────────────────────────────────────────

    def _check_ocr_candidates(self, result: ConversionResult) -> None:
        """Verifica se há candidatos a OCR após a conversão.

        Utiliza MarkdownQualityDetector para identificar Arquivos_Saída
        com Markdown ilegível (PDFs baseados em imagem). Se encontrar,
        exibe lista ao usuário e pergunta se deseja reprocessar com OCR.

        Args:
            result: Resultado da conversão em batch.
        """
        detector = MarkdownQualityDetector()
        candidates = detector.detect_ocr_candidates(result.results)

        if not candidates:
            return

        # Construir lista de nomes de arquivo para exibição
        file_names = [c.source_pdf.name for c in candidates]
        file_list_text = "\n".join(f"  • {name}" for name in file_names)

        # Montar mensagem com lista de arquivos e pergunta
        message = (
            f"{self.i18n.t('ocr.illegible_detected_message')}\n\n"
            f"{file_list_text}\n\n"
            f"{self.i18n.t('ocr.confirm_prompt')}"
        )

        # Perguntar ao usuário
        user_confirmed = messagebox.askyesno(
            self.i18n.t("ocr.illegible_detected_title"),
            message,
        )

        if user_confirmed:
            self._start_ocr_processing(candidates)
        # Se usuário recusar, manter arquivos originais e encerrar o fluxo

    def _start_ocr_processing(self, candidates: list) -> None:
        """Inicia o processamento OCR em uma thread separada.

        Configura motores OCR (Tesseract primário, EasyOCR secundário),
        desabilita controles da GUI e inicia polling de progresso OCR.

        Args:
            candidates: Lista de OCRCandidate para reprocessamento.
        """
        # Desabilitar controles durante OCR
        self._set_converting_state(True)

        # Resetar barra de progresso para OCR
        self._progress_bar["value"] = 0
        self._current_file_var.set(self.i18n.t("progress.processing"))

        # Criar fila separada para progresso OCR
        self._ocr_progress_queue: queue.Queue = queue.Queue()

        # Determinar diretório de saída a partir do primeiro candidato
        output_dir = candidates[0].output_md.parent

        # Iniciar thread OCR
        self._ocr_thread = threading.Thread(
            target=self._ocr_worker,
            args=(candidates, output_dir),
            daemon=True,
        )
        self._ocr_thread.start()

        # Iniciar polling de progresso OCR
        self._ocr_candidates_total = len(candidates)
        self._poll_ocr_progress_queue()

    def _ocr_worker(self, candidates: list, output_dir: Path) -> None:
        """Worker thread para processamento OCR.

        Instancia os motores OCR e o OCRManager, processa o batch
        e coloca o resultado final na fila de progresso OCR.

        Args:
            candidates: Lista de OCRCandidate.
            output_dir: Diretório de saída dos arquivos Markdown.
        """
        try:
            primary_engine = TesseractEngine()
            secondary_engine = EasyOCREngine()

            ocr_manager = OCRManager(
                primary_engine=primary_engine,
                secondary_engine=secondary_engine,
                progress_queue=self._ocr_progress_queue,
            )

            batch_result = ocr_manager.process_batch(candidates, output_dir)

            # Sinalizar conclusão via fila
            self._ocr_progress_queue.put(
                {
                    "type": "ocr_complete",
                    "result": batch_result,
                }
            )
        except Exception as e:
            logger.error("Erro no processamento OCR: %s", e)
            self._ocr_progress_queue.put(
                {
                    "type": "ocr_complete",
                    "result": OCRBatchResult(
                        total=len(candidates),
                        recovered=0,
                        failed=len(candidates),
                        results=[],
                    ),
                }
            )

    def _poll_ocr_progress_queue(self) -> None:
        """Faz polling da fila de progresso OCR via root.after().

        Processa mensagens de progresso OCR e atualiza barra de progresso.
        Quando recebe a mensagem de conclusão, exibe o resumo OCR.
        """
        try:
            while True:
                msg = self._ocr_progress_queue.get_nowait()

                if msg["type"] == "ocr_complete":
                    # OCR finalizado
                    self._progress_bar["value"] = 100
                    self._current_file_var.set(
                        self.i18n.t("progress.conversion_complete")
                    )
                    self._set_converting_state(False)
                    self._show_ocr_summary(msg["result"])
                    return

                if msg["type"] == "ocr_progress":
                    # Atualizar progresso OCR
                    current = msg["current_index"]
                    total = msg["total"]
                    filename = msg["filename"]

                    percentage = (current / total) * 100 if total > 0 else 0
                    self._progress_bar["value"] = percentage

                    display_name = truncate_filename(filename)
                    progress_text = (
                        self.i18n.t("ocr.progress")
                        .replace("{current}", str(current))
                        .replace("{total}", str(total))
                        .replace("{filename}", display_name)
                    )
                    self._current_file_var.set(progress_text)

        except queue.Empty:
            pass

        # Agendar próximo polling
        self.root.after(POLL_INTERVAL_MS, self._poll_ocr_progress_queue)

    def _show_ocr_summary(self, result: OCRBatchResult) -> None:
        """Exibe resumo do processamento OCR ao usuário.

        Mostra quantidade de arquivos recuperados, falhas e motor
        utilizado em cada arquivo.

        Args:
            result: OCRBatchResult com resultados do processamento OCR.
        """
        summary_lines = [
            self.i18n.t("ocr.files_recovered").replace(
                "{count}", str(result.recovered)
            ),
            self.i18n.t("ocr.files_failed").replace(
                "{count}", str(result.failed)
            ),
        ]

        # Adicionar detalhes de motor usado por arquivo
        if result.results:
            summary_lines.append("")
            for file_result in result.results:
                engine_text = self.i18n.t("ocr.engine_used").replace(
                    "{engine}", file_result.engine_used.value
                )
                summary_lines.append(
                    f"  {file_result.source_pdf.name}: {engine_text}"
                )

        messagebox.showinfo(
            self.i18n.t("ocr.summary_title"),
            "\n".join(summary_lines),
        )


def truncate_filename(filename: str) -> str:
    """Trunca nomes de arquivo com mais de 60 caracteres.

    Nomes com mais de MAX_FILENAME_DISPLAY (60) caracteres são cortados
    e recebem "..." no final, resultando em no máximo 63 caracteres.
    Nomes com 60 caracteres ou menos são retornados sem alteração.

    Args:
        filename: Nome do arquivo a ser truncado.

    Returns:
        Nome truncado com "..." se necessário, ou o nome original.
    """
    if len(filename) > MAX_FILENAME_DISPLAY:
        return filename[:MAX_FILENAME_DISPLAY] + "..."
    return filename
