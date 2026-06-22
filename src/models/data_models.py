"""Modelos de dados da aplicação PDF to Markdown Converter.

Contém todas as dataclasses e enums utilizados pela aplicação.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


# ─── Enums ───────────────────────────────────────────────────────────────────


class ConversionStatus(Enum):
    """Status possíveis para a conversão de um arquivo."""

    SUCCESS = "success"
    FAILED_CORRUPTED = "failed_corrupted"
    FAILED_PASSWORD = "failed_password"
    FAILED_NO_TEXT = "failed_no_text"
    FAILED_IO_ERROR = "failed_io_error"


class OCREngineUsed(Enum):
    """Motor OCR utilizado na extração."""

    TESSERACT = "tesseract"
    EASYOCR = "easyocr"
    NONE = "none"


class OCRStatus(Enum):
    """Status do processamento OCR de um arquivo."""

    SUCCESS = "success"
    FAILED_ALL_ENGINES = "failed_all_engines"
    SKIPPED_BY_USER = "skipped_by_user"


class Locale(Enum):
    """Idiomas suportados pela aplicação."""

    PT_BR = "pt-br"
    EN = "en"


# ─── Dataclasses ─────────────────────────────────────────────────────────────


@dataclass
class ValidationResult:
    """Resultado da validação de um arquivo PDF."""

    is_valid: bool
    reason: str = ""


@dataclass
class ImageInfo:
    """Informações sobre uma imagem extraída."""

    filename: str  # ex: "img_001.png"
    format: str  # ex: "png", "jpeg"
    page_number: int  # página onde a imagem aparece
    position_index: int  # ordem na página


@dataclass
class ConversionFileResult:
    """Resultado da conversão de um único arquivo."""

    source: Path
    output: Path | None
    status: ConversionStatus
    error_message: str = ""
    images_extracted: int = 0


@dataclass
class AddFilesResult:
    """Resultado da adição de arquivos à lista."""

    accepted: list[Path] = field(default_factory=list)
    rejected_invalid: list[tuple[Path, str]] = field(default_factory=list)
    rejected_duplicate: list[Path] = field(default_factory=list)
    rejected_limit: list[Path] = field(default_factory=list)


@dataclass
class ConversionResult:
    """Resultado geral de uma operação de conversão em batch."""

    total: int
    succeeded: int
    failed: int
    results: list[ConversionFileResult] = field(default_factory=list)


@dataclass
class ProgressUpdate:
    """Mensagem de progresso enviada da thread de trabalho para a GUI."""

    current_index: int
    total: int
    current_filename: str
    is_complete: bool = False
    result: ConversionResult | None = None


@dataclass
class OCRCandidate:
    """Arquivo identificado como PDF_Imagem candidato a OCR."""

    source_pdf: Path
    output_md: Path
    page_count: int
    alphanumeric_count: int  # total de chars alfanuméricos no .md gerado


@dataclass
class OCRFileResult:
    """Resultado do processamento OCR de um único arquivo."""

    source_pdf: Path
    output_md: Path
    status: OCRStatus
    engine_used: OCREngineUsed
    error_message: str = ""


@dataclass
class OCRBatchResult:
    """Resultado geral do processamento OCR em batch."""

    total: int
    recovered: int
    failed: int
    results: list[OCRFileResult] = field(default_factory=list)


@dataclass
class LanguagePreference:
    """Preferência de idioma persistida localmente."""

    locale: str  # "pt-br" ou "en"
    saved_at: str = ""  # ISO timestamp da última alteração
