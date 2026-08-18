import urllib.request
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    AcceleratorDevice,
    AcceleratorOptions,
    PdfPipelineOptions,
    TableStructureOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_lib import DocumentConversionOptions, EnhancedDoclingConverter, PDFConverter


def check_ollama_available(endpoint: str = "http://localhost:11434") -> bool:
    """ローカル Ollama サービスが稼働中か判定するヘルパー"""
    try:
        req = urllib.request.Request(f"{endpoint}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=1) as response:
            return response.status == 200
    except Exception:
        return False


class KnowledgeParser:
    """docling-markdown-generator (Docling v2.x & EnhancedDoclingConverter) を利用して

    ドキュメントから高精度に構造化 Markdown および画像アセット、VLM 要約を抽出するパーサー。
    """

    def __init__(self, device: str = "cpu"):
        self.device = device
        pdf_options = PdfPipelineOptions()

        acc_device = AcceleratorDevice.CUDA if device.lower() == "cuda" else AcceleratorDevice.CPU
        pdf_options.accelerator_options = AcceleratorOptions(device=acc_device)
        pdf_options.do_ocr = False
        pdf_options.do_table_structure = True
        pdf_options.table_structure_options = TableStructureOptions(mode="accurate")
        pdf_options.images_scale = 2.0
        pdf_options.generate_picture_images = True

        self.converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)}
        )

    def parse(self, file_path: Path | str, profile=None):
        """指定された原本ドキュメントをプロファイル設定に基づきパースし、DoclingConversionResult を返す。"""
        path = Path(file_path)

        if profile is not None:
            pdf_options = PdfPipelineOptions()
            acc_device = (
                AcceleratorDevice.CUDA if self.device.lower() == "cuda" else AcceleratorDevice.CPU
            )
            pdf_options.accelerator_options = AcceleratorOptions(device=acc_device)

            pdf_options.do_ocr = profile.do_ocr
            pdf_options.images_scale = profile.images_scale
            pdf_options.do_table_structure = True
            pdf_options.table_structure_options = TableStructureOptions(mode=profile.table_mode)
            pdf_options.generate_picture_images = True

            converter = DocumentConverter(
                format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)}
            )
            return converter.convert(path)

        return self.converter.convert(path)

    def parse_to_markdown_with_vlm(
        self,
        file_path: Path | str,
        slug: str,
        assets_dir: Path | None = None,
        profile=None,
    ) -> str:
        """EnhancedDoclingConverter を呼び出し、各種 VLM (Ollama, OpenAI, Custom 等) 自動解説付きの

        整形 Markdown を生成・返却する。
        """
        path = Path(file_path)

        from wikid_steward.core.config import get_config

        app_cfg = get_config()

        vlm_enabled = app_cfg.vlm.enabled
        vlm_provider = app_cfg.vlm.provider
        vlm_model = app_cfg.vlm.model
        vlm_endpoint = app_cfg.vlm.endpoint
        vlm_api_key = app_cfg.vlm.api_key
        vlm_prompt = app_cfg.vlm.prompt

        if profile is not None:
            vlm_enabled = getattr(profile, "vlm_enabled", vlm_enabled)
            vlm_provider = getattr(profile, "vlm_provider", vlm_provider)
            vlm_model = getattr(profile, "vlm_model", vlm_model)
            vlm_endpoint = getattr(profile, "vlm_endpoint", vlm_endpoint)
            vlm_api_key = getattr(profile, "vlm_api_key", vlm_api_key)
            vlm_prompt = getattr(profile, "vlm_prompt", vlm_prompt)

        options = DocumentConversionOptions(
            do_ocr=profile.do_ocr if profile else False,
            image_scale=profile.images_scale if profile else 2.0,
            vlm_enabled=vlm_enabled,
            vlm_provider=vlm_provider,
            vlm_model=vlm_model,
            vlm_endpoint=vlm_endpoint,
            vlm_api_key=vlm_api_key,
            vlm_prompt=vlm_prompt,
        )

        pdf_converter = PDFConverter(options=options)
        enhanced_converter = EnhancedDoclingConverter(docling_converter=pdf_converter)

        return enhanced_converter.convert_to_markdown(
            input_path=path, slug=slug, assets_dir=assets_dir
        )

        return self.converter.convert(path)
