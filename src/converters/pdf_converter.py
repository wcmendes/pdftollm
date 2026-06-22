"""Conversor de PDF para Markdown.

Utiliza PyMuPDF (fitz) e pymupdf4llm para extrair texto estruturado e imagens
de arquivos PDF, gerando Markdown com referências de imagem opcionais.
"""

import logging
from pathlib import Path

import fitz  # PyMuPDF
import pymupdf4llm

from src.models.data_models import ConversionFileResult, ConversionStatus, ImageInfo

logger = logging.getLogger(__name__)


class PDFConverter:
    """Converte um arquivo PDF individual para Markdown."""

    def convert(
        self,
        source: Path,
        output_dir: Path,
        extract_images: bool,
    ) -> ConversionFileResult:
        """
        Converte um PDF para Markdown.

        Args:
            source: Caminho do arquivo PDF de entrada.
            output_dir: Diretório onde o arquivo .md será salvo.
            extract_images: Se True, extrai imagens para subpasta de assets.

        Returns:
            ConversionFileResult com status, caminho de saída e contagem de imagens.
        """
        output_path = output_dir / source.with_suffix(".md").name

        try:
            doc = fitz.open(str(source))
        except Exception as e:
            logger.error("Falha ao abrir PDF '%s': %s", source, e)
            return ConversionFileResult(
                source=source,
                output=None,
                status=ConversionStatus.FAILED_CORRUPTED,
                error_message=f"Arquivo corrompido ou formato inválido: {e}",
            )

        try:
            # Verifica proteção por senha
            if doc.is_encrypted:
                return ConversionFileResult(
                    source=source,
                    output=None,
                    status=ConversionStatus.FAILED_PASSWORD,
                    error_message="Arquivo protegido por senha",
                )

            # Extrai markdown do documento
            markdown = self._extract_markdown(doc)

            images_extracted = 0

            if extract_images:
                # Determina nome da subpasta de assets
                assets_dir_name = f"{source.stem}_assets"
                assets_dir = output_dir / assets_dir_name

                # Extrai imagens
                images = self._extract_images(doc, assets_dir)

                if images:
                    images_extracted = len(images)
                    # Insere referências de imagem no markdown
                    markdown = self._insert_image_references(
                        markdown, images, assets_dir_name
                    )

            # Escreve arquivo de saída em UTF-8 com terminadores LF
            # Normaliza terminadores de linha para LF
            markdown = markdown.replace("\r\n", "\n").replace("\r", "\n")
            output_path.write_text(markdown, encoding="utf-8", newline="\n")

            return ConversionFileResult(
                source=source,
                output=output_path,
                status=ConversionStatus.SUCCESS,
                images_extracted=images_extracted,
            )

        except OSError as e:
            logger.error("Erro de I/O ao processar '%s': %s", source, e)
            return ConversionFileResult(
                source=source,
                output=None,
                status=ConversionStatus.FAILED_IO_ERROR,
                error_message=str(e),
            )
        except Exception as e:
            logger.error("Erro inesperado ao processar '%s': %s", source, e)
            return ConversionFileResult(
                source=source,
                output=None,
                status=ConversionStatus.FAILED_IO_ERROR,
                error_message=str(e),
            )
        finally:
            doc.close()

    def _extract_markdown(self, doc: fitz.Document) -> str:
        """
        Extrai conteúdo do PDF como texto Markdown usando pymupdf4llm.

        Preserva estrutura hierárquica: títulos, subtítulos, parágrafos,
        listas e tabelas.

        Args:
            doc: Documento PyMuPDF aberto.

        Returns:
            String com conteúdo em formato Markdown.
        """
        return pymupdf4llm.to_markdown(doc)

    def _extract_images(
        self,
        doc: fitz.Document,
        assets_dir: Path,
    ) -> list[ImageInfo]:
        """
        Extrai imagens embutidas do PDF e salva na pasta de assets.

        Imagens são nomeadas sequencialmente: img_001.png, img_002.jpeg, etc.
        A pasta de assets só é criada se houver imagens a extrair.

        Args:
            doc: Documento PyMuPDF aberto.
            assets_dir: Caminho da subpasta onde salvar as imagens.

        Returns:
            Lista de ImageInfo com detalhes de cada imagem extraída.
        """
        images: list[ImageInfo] = []
        image_counter = 0
        seen_xrefs: set[int] = set()

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_images = page.get_images(full=True)

            position_in_page = 0
            for img_info in page_images:
                xref = img_info[0]

                # Evita extrair a mesma imagem (mesmo xref) mais de uma vez
                if xref in seen_xrefs:
                    continue
                seen_xrefs.add(xref)

                try:
                    extracted = doc.extract_image(xref)
                    if not extracted or not extracted.get("image"):
                        continue

                    image_counter += 1
                    position_in_page += 1

                    # Determina formato da imagem
                    img_format = extracted.get("ext", "png").lower()
                    if not img_format:
                        img_format = "png"

                    # Nome do arquivo com zero-padding de 3 dígitos
                    filename = f"img_{image_counter:03d}.{img_format}"

                    # Cria pasta de assets apenas quando a primeira imagem é extraída
                    if not assets_dir.exists():
                        assets_dir.mkdir(parents=True, exist_ok=True)

                    # Salva imagem
                    img_path = assets_dir / filename
                    img_path.write_bytes(extracted["image"])

                    images.append(
                        ImageInfo(
                            filename=filename,
                            format=img_format,
                            page_number=page_num + 1,  # 1-indexed
                            position_index=position_in_page,
                        )
                    )

                except Exception as e:
                    image_counter += 1
                    position_in_page += 1
                    logger.warning(
                        "Falha ao extrair imagem xref=%d da página %d: %s",
                        xref,
                        page_num + 1,
                        e,
                    )
                    # Insere marcador de falha como ImageInfo com filename especial
                    images.append(
                        ImageInfo(
                            filename="__FAILED__",
                            format="",
                            page_number=page_num + 1,
                            position_index=position_in_page,
                        )
                    )

        return images

    def _insert_image_references(
        self,
        markdown: str,
        images: list[ImageInfo],
        assets_dir_name: str,
    ) -> str:
        """
        Insere referências de imagem no Markdown gerado.

        Para cada imagem extraída com sucesso, insere uma referência no formato:
        `![imageN](assets_dir_name/img_XXX.formato)`

        Para imagens que falharam na extração, insere marcador:
        `[Falha na extração da imagem]`

        As referências são adicionadas ao final do Markdown.

        Args:
            markdown: Conteúdo Markdown original.
            images: Lista de ImageInfo com imagens extraídas.
            assets_dir_name: Nome da subpasta de assets (para caminho relativo).

        Returns:
            Markdown com referências de imagem inseridas.
        """
        if not images:
            return markdown

        references: list[str] = []
        image_number = 0

        for img in images:
            image_number += 1
            if img.filename == "__FAILED__":
                references.append("[Falha na extração da imagem]")
            else:
                ref_path = f"{assets_dir_name}/{img.filename}"
                references.append(f"![image{image_number}]({ref_path})")

        # Adiciona referências ao final do markdown, separadas por linhas em branco
        if references:
            # Garante que o markdown termina com newline antes das referências
            if markdown and not markdown.endswith("\n"):
                markdown += "\n"
            markdown += "\n" + "\n\n".join(references) + "\n"

        return markdown
