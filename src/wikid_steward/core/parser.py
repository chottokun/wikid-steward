from pathlib import Path
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    AcceleratorDevice,
    AcceleratorOptions,
    PdfPipelineOptions,
    TableStructureOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption


class KnowledgeParser:
    """docling-markdown-generator (Docling v2.x) を利用してドキュメントから高精度に

    構造化 Markdown および画像アセットを抽出するパーサー。
    """

    def __init__(self, device: str = "cpu"):
        # PDF パイプライン設定
        pdf_options = PdfPipelineOptions()

        # デバイス（CPU / CUDA）明示設定
        acc_device = (
            AcceleratorDevice.CUDA
            if device.lower() == "cuda"
            else AcceleratorDevice.CPU
        )
        pdf_options.accelerator_options = AcceleratorOptions(device=acc_device)

        # デジタルPDFにおけるハルシネーション防止のため OCR はオフ
        pdf_options.do_ocr = False

        # セル結合を維持した高精度テーブル構造解析 (HTML <table> 出力)
        pdf_options.do_table_structure = True
        pdf_options.table_structure_options = TableStructureOptions(
            mode="accurate"
        )

        # 図表クロップの自動抽出設定
        pdf_options.images_scale = 2.0
        pdf_options.generate_picture_images = True

        # コンバーターのシングルトン化・初期化
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)
            }
        )

    def parse(self, file_path: Path | str, profile=None):
        """指定された原本ドキュメントをプロファイル設定に基づきパースし、DoclingConversionResult を返す。

        Args:
            file_path: 対象ファイルパス (PDF/DOCX/PPTX/XLSX)
            profile: パースプロファイル (ParseProfile)。未指定の場合は標準設定。

        Returns:
            パース結果
        """
        path = Path(file_path)

        if profile is not None:
            pdf_options = PdfPipelineOptions()
            pdf_options.do_ocr = profile.do_ocr
            pdf_options.images_scale = profile.images_scale
            pdf_options.do_table_structure = True
            pdf_options.table_structure_options = TableStructureOptions(
                mode=profile.table_mode
            )
            pdf_options.generate_picture_images = True

            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pdf_options
                    )
                }
            )
            return converter.convert(path)

        return self.converter.convert(path)
