import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import cv2
from PIL import Image

from ..utils.image_preprocessing import preprocess_page_image, segment_handwritten_lines
from ..core.config import settings

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self):
        self.rapid_ocr = None
        self.trocr_processor = None
        self.trocr_model = None
        self._models_initialized = False

    def _ensure_models_initialized(self):
        """Lazy load PP-OCR and TrOCR models on demand."""
        if self._models_initialized:
            return
        self._models_initialized = True

        # 1. Initialize PP-OCR Engine (RapidOCR ONNX or PaddleOCR)
        try:
            from rapidocr_onnxruntime import RapidOCR
            logger.info("Initializing PaddleOCR PP-OCR Engine via ONNX Runtime...")
            self.rapid_ocr = RapidOCR()
            logger.info("PaddleOCR PP-OCR Engine initialized successfully.")
        except Exception as e:
            logger.info(f"RapidOCR not available ({e}). Trying paddleocr fallback...")
            try:
                from paddleocr import PaddleOCR
                self.rapid_ocr = PaddleOCR(use_angle_cls=True, lang='en')
                logger.info("PaddleOCR initialized successfully.")
            except Exception as e2:
                logger.warning(f"PaddleOCR engines unavailable: {e2}")
                self.rapid_ocr = None

        # 2. Initialize Microsoft TrOCR Base Handwritten
        try:
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel
            import torch
            logger.info("Initializing Microsoft TrOCR Base Handwritten...")
            try:
                self.trocr_processor = TrOCRProcessor.from_pretrained(
                    "microsoft/trocr-base-handwritten",
                    local_files_only=True
                )
                self.trocr_model = VisionEncoderDecoderModel.from_pretrained(
                    "microsoft/trocr-base-handwritten",
                    local_files_only=True
                )
            except Exception:
                self.trocr_processor = TrOCRProcessor.from_pretrained(
                    "microsoft/trocr-base-handwritten",
                    local_files_only=False
                )
                self.trocr_model = VisionEncoderDecoderModel.from_pretrained(
                    "microsoft/trocr-base-handwritten",
                    local_files_only=False
                )
            if torch.cuda.is_available():
                self.trocr_model.to("cuda")
            logger.info("TrOCR initialized successfully.")
        except Exception as e:
            logger.info(f"TrOCR not initialized: {e}")
            self.trocr_processor = None
            self.trocr_model = None

    def process_document(self, file_path: Path) -> Tuple[str, int]:
        """
        Processes multi-page PDF or image file.
        Returns: (consolidated_text_string, page_count)
        """
        ext = file_path.suffix.lower()
        if ext == ".pdf":
            return self._process_pdf(file_path)
        else:
            return self._process_image_file(file_path)

    def _process_pdf(self, pdf_path: Path) -> Tuple[str, int]:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        page_texts: List[str] = []

        logger.info(f"Processing PDF document {pdf_path.name} ({page_count} pages)")

        for page_num in range(page_count):
            page = doc[page_num]
            # 1. Check embedded digital text
            digital_text = page.get_text("text").strip()

            # 2. Render page to high-res image (200 DPI) for visual/handwritten OCR
            try:
                pix = page.get_pixmap(dpi=200)
                img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                if pix.n == 4:
                    img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
                elif pix.n == 3:
                    img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
                else:
                    img_cv = cv2.cvtColor(img_np, cv2.COLOR_GRAY2BGR)

                preprocessed_img = preprocess_page_image(img_cv)
                ocr_text = self._ocr_single_page(preprocessed_img)
            except Exception as e:
                logger.error(f"Image rendering error on page {page_num + 1}: {e}")
                ocr_text = ""

            # Combine or select best representation
            if digital_text and len(digital_text) > len(ocr_text):
                combined = self._merge_digital_and_ocr(digital_text, ocr_text)
                page_texts.append(f"--- PAGE {page_num + 1} OF {page_count} ---\n{combined}")
            elif ocr_text:
                page_texts.append(f"--- PAGE {page_num + 1} OF {page_count} ---\n{ocr_text}")
            elif digital_text:
                page_texts.append(f"--- PAGE {page_num + 1} OF {page_count} ---\n{digital_text}")
            else:
                page_texts.append(f"--- PAGE {page_num + 1} OF {page_count} ---\n[UNREADABLE PAGE]")

        doc.close()
        consolidated = "\n\n".join(page_texts)
        return consolidated, page_count

    def _process_image_file(self, img_path: Path) -> Tuple[str, int]:
        img = cv2.imread(str(img_path))
        if img is None:
            return "[UNREADABLE DOCUMENT]", 1

        preprocessed = preprocess_page_image(img)
        ocr_text = self._ocr_single_page(preprocessed)
        if not ocr_text.strip():
            # Try raw image without preprocessing if thresholding stripped anything
            ocr_text = self._ocr_single_page(img)

        if not ocr_text.strip():
            ocr_text = "[UNREADABLE DOCUMENT]"

        result = f"--- PAGE 1 OF 1 ---\n{ocr_text}"
        return result, 1

    def _ocr_single_page(self, image: np.ndarray) -> str:
        """Runs PP-OCR and TrOCR on the image and orchestrates results."""
        self._ensure_models_initialized()
        extracted_lines = []
        ocr_scores = []

        # 1. Run PP-OCR (PaddleOCR / RapidOCR)
        if self.rapid_ocr:
            try:
                # RapidOCR accepts numpy image directly
                results, _ = self.rapid_ocr(image)
                if results:
                    # Sort results top-to-bottom, left-to-right
                    # Each item: [box, text, score]
                    sorted_res = sorted(results, key=lambda x: (int(min(p[1] for p in x[0]) / 18), min(p[0] for p in x[0])))
                    for box, text, score in sorted_res:
                        score = float(score)
                        ocr_scores.append(score)
                        clean_text = text.strip()
                        # If low confidence and looks handwritten, optionally refine with TrOCR
                        if score < 0.65 and self.trocr_model and self.trocr_processor:
                            crop = self._crop_box(image, box)
                            if crop is not None and crop.size > 0:
                                h_text = self._run_trocr_on_crop(crop)
                                if h_text and len(h_text) > 3:
                                    clean_text = f"{h_text} [Handwritten]"
                        if clean_text:
                            extracted_lines.append(clean_text)
            except Exception as e:
                logger.error(f"Error in PP-OCR recognition: {e}")

        # 2. RapidOCR can miss entire handwritten lines while still returning
        # some text. Run a segmented page-level TrOCR pass for sparse or weak OCR.
        rapid_text = "\n".join(extracted_lines)
        rapid_char_count = len(re.sub(r"\s", "", rapid_text))
        mean_ocr_score = sum(ocr_scores) / len(ocr_scores) if ocr_scores else 0.0
        needs_trocr_pass = (
            not extracted_lines
            or len(extracted_lines) <= 4
            or rapid_char_count < 160
            or (bool(ocr_scores) and mean_ocr_score < 0.78)
        )
        if needs_trocr_pass and self.trocr_model and self.trocr_processor:
            try:
                line_crops = segment_handwritten_lines(image)
                trocr_lines = []
                for crop in line_crops:
                    txt = self._run_trocr_on_crop(crop)
                    if txt:
                        trocr_lines.append(txt)

                trocr_text = "\n".join(trocr_lines)
                trocr_char_count = len(re.sub(r"\s", "", trocr_text))
                if trocr_text and (
                    not rapid_text
                    or trocr_char_count >= max(rapid_char_count + 25, int(rapid_char_count * 1.15))
                    or (bool(ocr_scores) and mean_ocr_score < 0.55)
                ):
                    logger.info(
                        "Using page-level TrOCR recovery (%s chars vs %s RapidOCR chars).",
                        trocr_char_count,
                        rapid_char_count
                    )
                    extracted_lines = trocr_lines
            except Exception as e:
                logger.error(f"Error running TrOCR segmenter fallback: {e}")
        elif needs_trocr_pass:
            logger.warning(
                "Sparse or low-confidence OCR detected, but TrOCR is unavailable for handwritten recovery."
            )

        return "\n".join(extracted_lines)

    def _crop_box(self, image: np.ndarray, box: List[List[float]]) -> Optional[np.ndarray]:
        try:
            x_min = max(0, int(min(p[0] for p in box)))
            x_max = min(image.shape[1], int(max(p[0] for p in box)))
            y_min = max(0, int(min(p[1] for p in box)))
            y_max = min(image.shape[0], int(max(p[1] for p in box)))
            if x_max > x_min and y_max > y_min:
                return image[y_min:y_max, x_min:x_max]
            return None
        except Exception:
            return None

    def _run_trocr_on_crop(self, crop: np.ndarray) -> str:
        try:
            import torch
            pil_img = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
            pixel_values = self.trocr_processor(pil_img, return_tensors="pt").pixel_values
            if torch.cuda.is_available():
                pixel_values = pixel_values.to("cuda")
            with torch.no_grad():
                generated_ids = self.trocr_model.generate(pixel_values, max_length=64)
            text = self.trocr_processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            return text.strip()
        except Exception as e:
            logger.error(f"TrOCR recognition error on crop: {e}")
            return ""

    def _merge_digital_and_ocr(self, digital: str, ocr: str) -> str:
        """Merges digital text with any additional OCR remarks/stamps."""
        if not ocr or ocr == digital:
            return digital
        
        diff_lines = []
        dig_lower = digital.lower()
        for line in ocr.splitlines():
            clean = line.strip()
            if len(clean) > 3 and clean.lower() not in dig_lower:
                diff_lines.append(clean)
                
        if diff_lines:
            return digital + "\n\n[Extracted Annotations / Remarks]\n" + "\n".join(diff_lines)
        return digital

ocr_service = OCRService()
