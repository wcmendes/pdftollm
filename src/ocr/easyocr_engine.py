"""Motor OCR baseado em EasyOCR + PyMuPDF.

Utiliza PyMuPDF (fitz) para renderizar páginas do PDF como imagens PIL
e EasyOCR para extrair texto via deep learning.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import fitz  # PyMuPDF
import numpy as np
from PIL import Image

from src.ocr.ocr_engine import OCREngine

if TYPE_CHECKING:
    import easyocr
else:
    try:
        import easyocr
    except ImportError:  # pragma: no cover
        easyocr = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class EasyOCREngine(OCREngine):
    """Motor OCR baseado em EasyOCR."""

    # DPI para renderização das páginas
    RENDER_DPI = 300

    def __init__(self) -> None:
        """Inicializa o motor EasyOCR.

        O Reader é criado sob demanda (lazy) na primeira chamada a
        extract_text para evitar carga de modelos desnecessária.
        """
        self._reader: "easyocr.Reader | None" = None

    @property
    def name(self) -> str:
        return "EasyOCR"

    def _get_reader(self) -> "easyocr.Reader":
        """Retorna (ou cria) o Reader do EasyOCR com suporte a pt e en."""
        if self._reader is None:
            if easyocr is None:
                raise RuntimeError(
                    "EasyOCR não está instalado. Instale com: pip install easyocr"
                )
            self._reader = easyocr.Reader(["pt", "en"], gpu=False)
        return self._reader

    def extract_text(self, pdf_path: Path) -> str:
        """
        Extrai texto de um PDF usando EasyOCR.

        Renderiza cada página do PDF como imagem via PyMuPDF e aplica
        easyocr.Reader.readtext para extrair o texto.

        Args:
            pdf_path: Caminho para o arquivo PDF.

        Returns:
            Texto extraído concatenado de todas as páginas.
            Retorna string vazia em caso de falha.
        """
        try:
            doc = fitz.open(str(pdf_path))
        except Exception as e:
            logger.error(f"EasyOCR: falha ao abrir PDF '{pdf_path}': {e}")
            return ""

        pages_text: list[str] = []

        try:
            zoom = self.RENDER_DPI / 72
            matrix = fitz.Matrix(zoom, zoom)
            reader = self._get_reader()

            for page_num in range(len(doc)):
                try:
                    page = doc[page_num]
                    pixmap = page.get_pixmap(matrix=matrix)

                    # Converte pixmap para PIL Image e depois para numpy array
                    img = Image.frombytes(
                        "RGB",
                        (pixmap.width, pixmap.height),
                        pixmap.samples,
                    )
                    img_array = np.array(img)

                    # Executa OCR — readtext retorna lista de (bbox, text, conf)
                    results = reader.readtext(img_array)
                    page_text = "\n".join(
                        text for _, text, _ in results
                    )
                    pages_text.append(page_text)

                except Exception as e:
                    logger.warning(
                        f"EasyOCR: falha ao processar página {page_num + 1} "
                        f"de '{pdf_path}': {e}"
                    )
                    pages_text.append("")
        finally:
            doc.close()

        return "\n\n".join(pages_text)
