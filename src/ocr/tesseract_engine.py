"""Motor OCR baseado em Tesseract (pytesseract + PyMuPDF).

Utiliza PyMuPDF (fitz) para renderizar páginas do PDF como imagens
e pytesseract para extrair texto via OCR.
"""

import logging
import shutil
from pathlib import Path

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

from src.ocr.ocr_engine import OCREngine

logger = logging.getLogger(__name__)


def is_tesseract_available() -> bool:
    """Verifica se o Tesseract OCR está instalado e acessível no sistema.

    Returns:
        True se o Tesseract estiver disponível no PATH ou configurado.
    """
    # Verificar se está no PATH
    if shutil.which("tesseract"):
        return True

    # Verificar caminhos comuns no Windows
    common_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for path in common_paths:
        if Path(path).exists():
            pytesseract.pytesseract.tesseract_cmd = path
            return True

    return False


class TesseractEngine(OCREngine):
    """Motor OCR baseado em Tesseract (pytesseract)."""

    # DPI para renderização das páginas — 300 é um bom equilíbrio
    # entre qualidade de OCR e uso de memória.
    RENDER_DPI = 300

    def __init__(self) -> None:
        """Inicializa o motor Tesseract verificando disponibilidade."""
        self._available = is_tesseract_available()

    @property
    def available(self) -> bool:
        """Indica se o Tesseract está disponível no sistema."""
        return self._available

    @property
    def name(self) -> str:
        return "Tesseract"

    def extract_text(self, pdf_path: Path) -> str:
        """
        Extrai texto de um PDF usando pytesseract.

        Se o Tesseract não estiver instalado, retorna string vazia
        imediatamente (fallback para EasyOCR será usado).

        Args:
            pdf_path: Caminho para o arquivo PDF.

        Returns:
            Texto extraído concatenado de todas as páginas.
            Retorna string vazia em caso de falha ou indisponibilidade.
        """
        if not self._available:
            logger.info("Tesseract não disponível, pulando para motor secundário.")
            return ""

        try:
            doc = fitz.open(str(pdf_path))
        except Exception as e:
            logger.error(f"Tesseract: falha ao abrir PDF '{pdf_path}': {e}")
            return ""

        pages_text: list[str] = []

        try:
            zoom = self.RENDER_DPI / 72  # 72 é o DPI padrão do PDF
            matrix = fitz.Matrix(zoom, zoom)

            for page_num in range(len(doc)):
                try:
                    page = doc[page_num]
                    pixmap = page.get_pixmap(matrix=matrix)

                    # Converte pixmap para PIL Image
                    img = Image.frombytes(
                        "RGB",
                        (pixmap.width, pixmap.height),
                        pixmap.samples,
                    )

                    # Detecta e corrige orientação da imagem
                    img = self._fix_orientation(img)

                    # Executa OCR com suporte a português e inglês
                    text = pytesseract.image_to_string(img, lang="por+eng")

                    # Filtra resultado lixo (texto incoerente)
                    if self._is_garbage_text(text):
                        logger.warning(
                            f"Página {page_num + 1} de '{pdf_path.name}': "
                            f"OCR produziu texto incoerente, descartando."
                        )
                        pages_text.append("")
                    else:
                        pages_text.append(text)

                except Exception as e:
                    logger.warning(
                        f"Tesseract: falha ao processar página {page_num + 1} "
                        f"de '{pdf_path}': {e}"
                    )
                    pages_text.append("")
        finally:
            doc.close()

        return "\n\n".join(pages_text)

    def _fix_orientation(self, img: Image.Image) -> Image.Image:
        """Detecta e corrige orientação da imagem usando Tesseract OSD.

        Usa o Tesseract em modo OSD (Orientation and Script Detection)
        para determinar se a imagem está rotacionada e corrigi-la.
        Usa Image.transpose para rotações exatas de 90/180/270°.

        Args:
            img: Imagem PIL a verificar.

        Returns:
            Imagem corrigida (rotacionada se necessário) ou original se
            a detecção falhar.
        """
        try:
            osd = pytesseract.image_to_osd(img, output_type=pytesseract.Output.DICT)
            rotation = osd.get("rotate", 0)
            if rotation == 90:
                logger.info("Detectada rotação de 90°, corrigindo com ROTATE_270...")
                img = img.transpose(Image.Transpose.ROTATE_270)
            elif rotation == 180:
                logger.info("Detectada rotação de 180°, corrigindo...")
                img = img.transpose(Image.Transpose.ROTATE_180)
            elif rotation == 270:
                logger.info("Detectada rotação de 270°, corrigindo com ROTATE_90...")
                img = img.transpose(Image.Transpose.ROTATE_90)
        except Exception as e:
            logger.debug(f"Detecção de orientação falhou (normal para textos curtos): {e}")
        return img

    @staticmethod
    def _is_garbage_text(text: str) -> bool:
        """Detecta se o texto extraído pelo OCR é lixo/incoerente.

        Heurística: se mais de 60% dos "tokens" (palavras) têm 1-2 caracteres
        e poucos têm 4+ caracteres, o texto provavelmente é resultado de OCR
        falhando em documento rotacionado ou muito degradado.

        Args:
            text: Texto extraído pelo OCR.

        Returns:
            True se o texto parece ser lixo incoerente.
        """
        if not text or len(text.strip()) < 20:
            return False  # Texto muito curto não é avaliável

        words = text.split()
        if len(words) < 10:
            return False  # Poucas palavras, não dá pra avaliar

        short_words = sum(1 for w in words if len(w) <= 2)
        ratio_short = short_words / len(words)

        # Se mais de 60% das palavras são de 1-2 caracteres, é lixo
        return ratio_short > 0.60
