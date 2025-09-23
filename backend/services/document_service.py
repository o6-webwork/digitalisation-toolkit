import fitz
import torch
from pypdf import PdfReader, PdfWriter
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
from typing import Dict, Any, Callable, Optional
from config.settings import settings
from utils.logger import app_logger
from .translation_service import TranslationService

class DocumentService:
    """Service for handling document processing and conversion"""

    def __init__(self):
        self.translation_service = TranslationService()

        # Log GPU availability for informational purposes
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            app_logger.info(f"Detected {gpu_count} CUDA devices: {[f'cuda:{i}' for i in range(gpu_count)]}")
        else:
            app_logger.info("No CUDA devices detected, using CPU")


    async def translate_pdf(
        self,
        file_path: str,
        input_lang: str,
        output_lang: str,
        include_tbl: bool,
        url: str,
        authorization: str,
        model_name: str
    ) -> bytes:
        """Translate PDF document and return translated PDF bytes with concurrent processing"""
        try:
            app_logger.info("Starting PDF translation")

            # Validate PDF
            reader = PdfReader(file_path)
            total_pages = len(reader.pages)
            if total_pages == 0:
                raise ValueError("The PDF document is empty.")
        except Exception as e:
            raise Exception(f"Error: The PDF file is corrupted or invalid. {str(e)}")

        # Process document structure
        app_logger.info("Processing PDF document")
        redoc = self._convert_document_structure(file_path)
        doc_info = redoc["Pages"]

        # Collect all texts for batch translation
        all_texts = []
        text_mapping = {}

        for page_no, page_data in doc_info.items():
            for i, text_info in enumerate(page_data["Texts"]):
                text_content = text_info["text"]
                if text_content.strip():
                    all_texts.append(text_content)
                    text_mapping[text_content] = {
                        "page_no": page_no,
                        "element_type": "text",
                        "index": i,
                        "bbox": text_info["bbox"]
                    }

            if include_tbl:
                for table_i, table_info in enumerate(page_data["Tables"]):
                    for cell_i, cell in enumerate(table_info["table_cells"]):
                        table_text = cell["text"]
                        if table_text.strip():
                            all_texts.append(table_text)
                            text_mapping[table_text] = {
                                "page_no": page_no,
                                "element_type": "table",
                                "table_index": table_i,
                                "cell_index": cell_i,
                                "bbox": cell["bbox"]
                            }

        # Batch translate all texts
        app_logger.info(f"Batch translating {len(all_texts)} text elements")
        if all_texts:
            translated_texts = await self.translation_service.translate_batch(
                all_texts, input_lang, output_lang, url, authorization, model_name
            )
            translation_map = dict(zip(all_texts, translated_texts))
        else:
            translation_map = {}

        import tempfile
        import os

        # Create temporary output file
        output_fd, output_path = tempfile.mkstemp(suffix=".pdf", prefix="translated_")
        os.close(output_fd)  # Close file descriptor, we'll use the path

        try:
            with fitz.open(file_path) as doc:
                ocg_xref = doc.add_ocg(f"{output_lang} Translation", on=True)

            for page in doc:
                page_no = str(page.number + 1)
                app_logger.info(f"Processing page {page_no}")

                if page_no not in doc_info:
                    continue

                # Apply translated text elements
                for text_info in doc_info[page_no]["Texts"]:
                    try:
                        text_content = text_info["text"]
                        if text_content.strip() and text_content in translation_map:
                            text_bbox = text_info["bbox"]
                            translated_text = translation_map[text_content]
                            text_rect = fitz.Rect(self._reformat_bbox(text_bbox))
                            page.add_redact_annot(text_rect, text="")
                            page.apply_redactions()
                            page.insert_htmlbox(
                                text_rect,
                                f"<div style='font-family: sans-serif;'>{translated_text}</div>",
                                oc=ocg_xref
                            )
                    except KeyError as e:
                        app_logger.warning(f"KeyError processing text: {str(e)}")
                        continue

                # Apply translated table elements if requested
                if include_tbl:
                    for table_info in doc_info[page_no]["Tables"]:
                        for cell in table_info["table_cells"]:
                            table_text = cell["text"]
                            if table_text.strip() and table_text in translation_map:
                                table_bbox = cell["bbox"]
                                translated_text = translation_map[table_text]
                                table_rect = fitz.Rect(self._reformat_bbox(table_bbox))
                                page.add_redact_annot(table_rect, text="")
                                page.apply_redactions()
                                page.insert_htmlbox(
                                    table_rect,
                                    f"<div style='font-family: sans-serif;'>{translated_text}</div>",
                                    oc=ocg_xref
                                )

                page.clean_contents()

            doc.subset_fonts()
            doc.ez_save(output_path, clean=True, deflate=True, garbage=4)

        # Compress using PdfWriter
        writer = PdfWriter(clone_from=output_path)
        for page in writer.pages:
            for img in page.images:
                img.replace(img.image, quality=80)

        with open(output_path, "wb") as f:
            writer.write(f)

            # Read final optimized PDF into memory
            with open(output_path, "rb") as f:
                pdf_bytes = f.read()

            app_logger.info("PDF translation completed successfully")
            return pdf_bytes

        finally:
            # Clean up temporary output file
            if os.path.exists(output_path):
                os.unlink(output_path)
                app_logger.info(f"Cleaned up temporary output file: {output_path}")

    async def translate_pdf_with_progress(
        self,
        file_path: str,
        input_lang: str,
        output_lang: str,
        include_tbl: bool,
        url: str,
        authorization: str,
        model_name: str,
        progress_callback: Optional[Callable] = None
    ) -> bytes:
        """Translate PDF document with progress reporting"""
        try:
            if progress_callback:
                await progress_callback({
                    "type": "document_processing_start",
                    "message": "Starting document processing..."
                })

            app_logger.info("Starting PDF translation")

            # Validate PDF
            reader = PdfReader(file_path)
            total_pages = len(reader.pages)
            if total_pages == 0:
                raise ValueError("The PDF document is empty.")
        except Exception as e:
            raise Exception(f"Error: The PDF file is corrupted or invalid. {str(e)}")

        # Process document structure
        if progress_callback:
            await progress_callback({
                "type": "document_extraction",
                "message": f"Extracting text from PDF ({total_pages} pages)..."
            })

        app_logger.info("Processing PDF document")
        redoc = self._convert_document_structure(file_path)
        doc_info = redoc["Pages"]

        if progress_callback:
            await progress_callback({
                "type": "document_extraction_complete",
                "message": "Text extraction completed. Preparing for translation..."
            })

        # Collect all texts for batch translation
        all_texts = []
        text_mapping = {}

        for page_no, page_data in doc_info.items():
            for i, text_info in enumerate(page_data["Texts"]):
                text_content = text_info["text"]
                if text_content.strip():
                    all_texts.append(text_content)
                    text_mapping[text_content] = {
                        "page_no": page_no,
                        "element_type": "text",
                        "index": i,
                        "bbox": text_info["bbox"]
                    }

            if include_tbl:
                for table_i, table_info in enumerate(page_data["Tables"]):
                    for cell_i, cell in enumerate(table_info["table_cells"]):
                        table_text = cell["text"]
                        if table_text.strip():
                            all_texts.append(table_text)
                            text_mapping[table_text] = {
                                "page_no": page_no,
                                "element_type": "table",
                                "table_index": table_i,
                                "cell_index": cell_i,
                                "bbox": cell["bbox"]
                            }

        if progress_callback:
            await progress_callback({
                "type": "translation_start",
                "message": f"Starting translation of {len(all_texts)} text elements...",
                "total_elements": len(all_texts)
            })

        # Batch translate all texts with progress
        app_logger.info(f"Batch translating {len(all_texts)} text elements")
        if all_texts:
            translated_texts = await self.translation_service.translate_batch_with_progress(
                all_texts, input_lang, output_lang, url, authorization, model_name, progress_callback
            )
            translation_map = dict(zip(all_texts, translated_texts))
        else:
            translation_map = {}

        if progress_callback:
            await progress_callback({
                "type": "pdf_generation_start",
                "message": "Generating translated PDF..."
            })

        import tempfile
        import os

        # Create temporary output file
        output_fd, output_path = tempfile.mkstemp(suffix=".pdf", prefix="translated_")
        os.close(output_fd)  # Close file descriptor, we'll use the path

        try:
            with fitz.open(file_path) as doc:
                ocg_xref = doc.add_ocg(f"{output_lang} Translation", on=True)

                for page in doc:
                    page_no = str(page.number + 1)
                    if progress_callback:
                        await progress_callback({
                            "type": "pdf_generation_progress",
                            "message": f"Processing page {page_no} of {total_pages}...",
                            "page": page.number + 1,
                            "total_pages": total_pages
                        })

                    app_logger.info(f"Processing page {page_no}")

                    # Handle text elements
                    if page_no in doc_info and "Texts" in doc_info[page_no]:
                        for text_info in doc_info[page_no]["Texts"]:
                            original_text = text_info["text"]
                            if original_text.strip() and original_text in translation_map:
                                translated_text = translation_map[original_text]
                                bbox = text_info["bbox"]

                                rect = fitz.Rect(bbox["x0"], bbox["y0"], bbox["x1"], bbox["y1"])
                                text_dict = {
                                    "type": "text",
                                    "color": (1, 0, 0),
                                    "content": translated_text,
                                    "rect": rect,
                                    "fontsize": min(rect.height * 0.8, 12),
                                    "fontname": "helv",
                                    "fill": (1, 1, 1),
                                    "oc": ocg_xref
                                }
                                page.add_annot(text_dict)

                    # Handle table elements if requested
                    if include_tbl and page_no in doc_info and "Tables" in doc_info[page_no]:
                        for table_info in doc_info[page_no]["Tables"]:
                            for cell in table_info["table_cells"]:
                                original_text = cell["text"]
                                if original_text.strip() and original_text in translation_map:
                                    translated_text = translation_map[original_text]
                                    bbox = cell["bbox"]

                                    rect = fitz.Rect(bbox["x0"], bbox["y0"], bbox["x1"], bbox["y1"])
                                    text_dict = {
                                        "type": "text",
                                        "color": (0, 0, 1),
                                        "content": translated_text,
                                        "rect": rect,
                                        "fontsize": min(rect.height * 0.6, 10),
                                        "fontname": "helv",
                                        "fill": (1, 1, 1),
                                        "oc": ocg_xref
                                    }
                                    page.add_annot(text_dict)

            # Save and optimize the final PDF
            doc.save(output_path, garbage=4, deflate=True, clean=True)

            # Optimize images in the PDF
            writer = PdfWriter()
            reader = PdfReader(output_path)

            for page in reader.pages:
                writer.add_page(page)

            for page in writer.pages:
                if "/Resources" in page and "/XObject" in page["/Resources"]:
                    xobject = page["/Resources"]["/XObject"].get_object()
                    for obj in xobject:
                        if xobject[obj]["/Subtype"] == "/Image":
                            img = xobject[obj]
                            img.replace(img.image, quality=80)

            with open(output_path, "wb") as f:
                writer.write(f)

            # Read final optimized PDF into memory
            with open(output_path, "rb") as f:
                pdf_bytes = f.read()

            if progress_callback:
                await progress_callback({
                    "type": "complete",
                    "message": "PDF translation completed successfully!"
                })

            app_logger.info("PDF translation completed successfully")
            return pdf_bytes

        finally:
            # Clean up temporary output file
            if os.path.exists(output_path):
                os.unlink(output_path)
                app_logger.info(f"Cleaned up temporary output file: {output_path}")

    def _convert_document_structure(self, file_path: str) -> Dict[str, Any]:
        """Convert PDF to structured format using Docling"""
        app_logger.info("Setting up Docling pipeline")

        # Configure OCR options
        ocr_options = EasyOcrOptions(
            lang=["en"],
            model_storage_directory=settings.MODEL_STORAGE_DIRECTORY,
            download_enabled=False
        )

        pipeline_options = PdfPipelineOptions(
            artifacts_path=settings.ARTIFACTS_PATH,
            enable_remote_services=False,
            ocr_options=ocr_options
        )
        
        converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
        )
        
        try:
            app_logger.info("Converting document")
            result = converter.convert(file_path).document
        except Exception as e:
            app_logger.error(f"Document conversion error: {str(e)}")
            raise Exception(f"Document conversion error: {str(e)}")
        
        doc = result.export_to_dict()
        
        # Process document structure
        redoc = {"Pages": {}}
        for page_no, page_dim in doc["pages"].items():
            redoc["Pages"].update(
                {page_no: {"Texts": [], "Tables": [], "Page_Size": page_dim["size"]}}
            )

        # Process text elements
        for text_data in doc["texts"]:
            prov = text_data.get("prov", [{}])[0]
            text_label = text_data["label"]
            text_text = text_data["text"]
            text_page_no = prov["page_no"]
            text_bbox = prov["bbox"]
            text_bbox["t"] = redoc["Pages"][str(text_page_no)]["Page_Size"]["height"] - text_bbox["t"]
            text_bbox["b"] = redoc["Pages"][str(text_page_no)]["Page_Size"]["height"] - text_bbox["b"]
            redoc["Pages"][str(text_page_no)]["Texts"].append({
                "label": text_label,
                "text": text_text,
                "bbox": text_bbox,
            })

        # Process table elements
        if doc["tables"]:
            for table_data in doc["tables"]:
                prov = table_data.get("prov", [{}])[0]
                table_page_no = prov["page_no"]
                table_bbox = prov["bbox"]
                table_bbox["t"] = redoc["Pages"][str(table_page_no)]["Page_Size"]["height"] - table_bbox["t"]
                table_bbox["b"] = redoc["Pages"][str(table_page_no)]["Page_Size"]["height"] - table_bbox["b"]
                table_cell_list = []
                
                for table_cell in table_data["data"]["table_cells"]:
                    try:
                        if "bbox" not in table_cell:
                            app_logger.warning(f"Missing 'bbox' for table cell: {table_cell}")
                            continue
                        
                        table_cell["bbox"]["t"] = redoc["Pages"][str(table_page_no)]["Page_Size"]["height"] - table_cell["bbox"]["t"]
                        table_cell["bbox"]["b"] = redoc["Pages"][str(table_page_no)]["Page_Size"]["height"] - table_cell["bbox"]["b"]
                        table_cell_list.append({"text": table_cell["text"], "bbox": table_cell["bbox"]})
                    except Exception as e:
                        app_logger.error(f"Exception in table cell processing: {str(e)}")

                redoc["Pages"][str(table_page_no)]["Tables"].append({
                    "table_cells": table_cell_list,
                    "bbox": table_bbox
                })
        
        return redoc

    def _reformat_bbox(self, docling_bbox: Dict[str, float]) -> tuple:
        """Reformat bounding box coordinates from Docling format"""
        return (
            docling_bbox.get('l'),
            docling_bbox.get('t'),
            docling_bbox.get('r'),
            docling_bbox.get('b')
        )