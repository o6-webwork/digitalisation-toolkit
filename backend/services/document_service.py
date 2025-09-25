import fitz
import torch
import os
import gc
import time
import psutil
from pypdf import PdfReader, PdfWriter
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
from typing import Dict, Any
from config.settings import settings
from utils.logger import app_logger
from .translation_service import TranslationService
import tempfile

class DocumentService:
    """Service for handling document processing and conversion"""

    def __init__(self):
        self.translation_service = TranslationService()

        # Log GPU availability without restrictive memory management
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            app_logger.info(f"Detected {gpu_count} CUDA devices: {[f'cuda:{i}' for i in range(gpu_count)]}")
            torch.cuda.empty_cache()
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

            # Initial single GPU memory management
            if torch.cuda.is_available():
                torch.cuda.set_device(0)  # Ensure we're using GPU 0
                torch.cuda.empty_cache()
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
                allocated_memory = torch.cuda.memory_allocated(0) / 1024**3
                app_logger.info(f"GPU 0 memory - Total: {gpu_memory:.1f}GB, Allocated: {allocated_memory:.1f}GB")

            # Validate PDF
            reader = PdfReader(file_path)
            total_pages = len(reader.pages)
            if total_pages == 0:
                raise ValueError("The PDF document is empty.")
        except Exception as e:
            raise Exception(f"Error: The PDF file is corrupted or invalid. {str(e)}")

        # Process document structure
        app_logger.info("Processing PDF document")
        redoc = self._convert_document_structure(file_path, input_lang)
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

        # Batch translate all texts with timeout monitoring
        app_logger.info(f"Batch translating {len(all_texts)} text elements")
        translation_start_time = time.time()

        if all_texts:
            try:
                translated_texts = await self.translation_service.translate_batch(
                    all_texts, input_lang, output_lang, url, authorization, model_name
                )
                translation_map = dict(zip(all_texts, translated_texts))
                translation_time = time.time() - translation_start_time
                app_logger.info(f"Translation completed in {translation_time:.2f} seconds")
            except Exception as e:
                app_logger.error(f"Translation failed after {time.time() - translation_start_time:.2f}s: {str(e)}")
                raise
        else:
            translation_map = {}

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
                            elif text_content.strip():
                                app_logger.warning(f"Translation missing for text: '{text_content[:50]}...'")
                        except (KeyError, ValueError, Exception) as e:
                            app_logger.error(f"Error processing text element on page {page_no}: {str(e)}")
                            continue

                    # Apply translated table elements if requested
                    if include_tbl:
                        for table_info in doc_info[page_no]["Tables"]:
                            try:
                                for cell in table_info["table_cells"]:
                                    try:
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
                                        elif table_text.strip():
                                            app_logger.warning(f"Translation missing for table text: '{table_text[:50]}...'")
                                    except (KeyError, ValueError, Exception) as e:
                                        app_logger.error(f"Error processing table cell on page {page_no}: {str(e)}")
                                        continue
                            except Exception as e:
                                app_logger.error(f"Error processing table on page {page_no}: {str(e)}")
                                continue

                    page.clean_contents()

                # Clear GPU cache and system memory before memory-intensive PDF operations
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    app_logger.debug("GPU cache cleared before PDF finalization")

                # Force garbage collection before intensive operations
                gc.collect()

                app_logger.info("Starting PDF finalization and compression")
                try:
                    # Monitor memory before finalization
                    if torch.cuda.is_available():
                        gpu_mem_before = torch.cuda.memory_allocated(0) / 1024**3
                        app_logger.info(f"GPU memory before finalization: {gpu_mem_before:.2f}GB")

                    # Subset fonts to reduce memory usage
                    doc.subset_fonts()
                    app_logger.debug("Font subsetting completed")

                    # Save with aggressive compression and cleanup
                    doc.ez_save(output_path, clean=True, deflate=True, garbage=4, linear=True)
                    app_logger.info("PDF saved successfully")

                except Exception as save_error:
                    app_logger.error(f"Error during PDF finalization: {str(save_error)}")
                    # Attempt fallback save without some optimizations
                    try:
                        app_logger.info("Attempting fallback save without linear optimization")
                        doc.save(output_path, clean=True, deflate=True)
                        app_logger.info("PDF saved with fallback method")
                    except Exception as fallback_error:
                        app_logger.error(f"Fallback save also failed: {str(fallback_error)}")
                        raise Exception(f"PDF finalization failed: {str(save_error)}")

            # Compress using PdfWriter with memory management
            app_logger.info("Starting PDF compression")
            compression_successful = False
            try:
                writer = PdfWriter(clone_from=output_path)

                # Process images in batches to manage memory
                page_count = len(writer.pages)
                app_logger.info(f"Compressing images in {page_count} pages")

                # Make batch size configurable, default to 50
                batch_size = getattr(settings, 'PDF_COMPRESSION_BATCH_SIZE', 50)
                for i in range(0, page_count, batch_size):
                    end_idx = min(i + batch_size, page_count)
                    app_logger.debug(f"Processing image batch {i+1}-{end_idx}")

                    try:
                        for page_idx in range(i, end_idx):
                            page = writer.pages[page_idx]
                            for img in page.images:
                                img.replace(img.image, quality=80)
                    except Exception as batch_error:
                        app_logger.warning(f"Error in compression batch {i+1}-{end_idx}: {str(batch_error)}")
                        # Continue with next batch
                        continue

                    # Force garbage collection between batches
                    gc.collect()

                # Write compressed PDF
                with open(output_path, "wb") as f:
                    writer.write(f)

                compression_successful = True
                app_logger.info("PDF compression completed successfully")

            except Exception as e:
                app_logger.warning(f"PDF compression failed, using uncompressed version: {str(e)}")
                compression_successful = False

            if not compression_successful:
                app_logger.info("Proceeding with uncompressed PDF")

            # Read final optimized PDF into memory
            app_logger.info("Reading final PDF into memory")
            with open(output_path, "rb") as f:
                pdf_bytes = f.read()

            # Final memory cleanup before return
            gc.collect()

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                app_logger.debug("Final GPU cache clear completed")

            app_logger.info(f"PDF translation completed successfully, final size: {len(pdf_bytes)} bytes")
            return pdf_bytes

        finally:
            # Clean up temporary output file
            if os.path.exists(output_path):
                os.unlink(output_path)
                app_logger.info(f"Cleaned up temporary output file: {output_path}")

            # Clear GPU cache to prevent memory buildup
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                app_logger.debug("GPU cache cleared")


    def _convert_document_structure(self, file_path: str, input_lang: str = None) -> Dict[str, Any]:
        """Convert PDF to structured format using Docling"""
        app_logger.info("Setting up Docling pipeline")

        # Configure OCR options with user-specified or default language detection
        ocr_languages = [input_lang] if input_lang and input_lang != 'auto' else ["en"]
        ocr_options = EasyOcrOptions(
            lang=ocr_languages,  # Default to English if no language specified
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
            start_time = time.time()

            # Monitor memory before conversion
            if torch.cuda.is_available():
                gpu_memory_before = torch.cuda.memory_allocated(0) / 1024**3
                app_logger.info(f"GPU memory before conversion: {gpu_memory_before:.2f}GB")

            system_memory_before = psutil.virtual_memory().percent
            app_logger.info(f"System memory usage before conversion: {system_memory_before:.1f}%")

            result = converter.convert(file_path).document

            conversion_time = time.time() - start_time
            app_logger.info(f"Document conversion completed in {conversion_time:.2f} seconds")

            # Monitor memory after conversion
            if torch.cuda.is_available():
                gpu_memory_after = torch.cuda.memory_allocated(0) / 1024**3
                app_logger.info(f"GPU memory after conversion: {gpu_memory_after:.2f}GB")

            system_memory_after = psutil.virtual_memory().percent
            app_logger.info(f"System memory usage after conversion: {system_memory_after:.1f}%")

        except Exception as e:
            app_logger.error(f"Document conversion error after {time.time() - start_time:.2f}s: {str(e)}")
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
        try:
            # Safely convert coordinates, handling large integers
            left = float(docling_bbox.get('l', 0))
            top = float(docling_bbox.get('t', 0))
            right = float(docling_bbox.get('r', 0))
            bottom = float(docling_bbox.get('b', 0))

            # Clamp to reasonable PDF coordinate bounds
            max_coord = 99999.0
            left = max(-max_coord, min(max_coord, left))
            top = max(-max_coord, min(max_coord, top))
            right = max(-max_coord, min(max_coord, right))
            bottom = max(-max_coord, min(max_coord, bottom))

            return (left, top, right, bottom)
        except (ValueError, OverflowError) as e:
            app_logger.warning(f"Invalid bbox coordinates, using default: {e}")
            return (0.0, 0.0, 100.0, 100.0)