import cv2
import numpy as np
from typing import Tuple, Optional, List

def deskew_image(image: np.ndarray, max_angle: float = 45.0) -> np.ndarray:
    """
    Detects skew angle using Hough line transform / minimum area bounding box
    and rotates the image to align horizontally.
    """
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
        # Invert colors so text is white on black background
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
        
        # Find all white pixels (text)
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) < 100:
            return image
            
        angle = cv2.minAreaRect(coords)[-1]
        
        # Fix OpenCV angle logic
        if angle < -45:
            angle = -(90 + angle)
        elif angle > 45:
            angle = 90 - angle
        else:
            angle = -angle
            
        # If angle is negligible or too extreme, don't rotate
        if abs(angle) < 0.5 or abs(angle) > max_angle:
            return image
            
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated
    except Exception:
        return image

def enhance_contrast_and_denoise(image: np.ndarray) -> np.ndarray:
    """
    Applies CLAHE (Contrast Limited Adaptive Histogram Equalization)
    and gentle bilateral filtering to preserve text edges while reducing noise.
    """
    try:
        if len(image.shape) == 3:
            # Convert to LAB to equalize only luminance
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            limg = cv2.merge((cl, a, b))
            enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
            # Gentle bilateral filter
            denoised = cv2.bilateralFilter(enhanced, d=5, sigmaColor=50, sigmaSpace=50)
            return denoised
        else:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(image)
            denoised = cv2.bilateralFilter(enhanced, d=5, sigmaColor=50, sigmaSpace=50)
            return denoised
    except Exception:
        return image

def preprocess_page_image(image: np.ndarray) -> np.ndarray:
    """
    Complete non-destructive page preprocessing pipeline:
    1. Deskew
    2. Contrast enhancement & gentle denoising
    """
    deskewed = deskew_image(image)
    enhanced = enhance_contrast_and_denoise(deskewed)
    return enhanced

def segment_handwritten_lines(image: np.ndarray) -> List[np.ndarray]:
    """
    Extracts text line crops from an image region for TrOCR line-level recognition.
    Uses morphological horizontal dilation and contour analysis.
    """
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
        # Binarize with Otsu
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Morphological horizontal dilation to bridge characters into text lines
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 3))
        dilated = cv2.dilate(binary, kernel, iterations=2)
        
        # Use RETR_LIST so internal text line contours are found even inside page boundaries
        contours, _ = cv2.findContours(dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        line_crops = []
        bounding_boxes = []
        
        h_img, w_img = image.shape[:2]
        
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            # Filter out outer document border (e.g. spans almost entire page)
            if w > (w_img * 0.95) and h > (h_img * 0.95):
                continue
            # Keep valid text line candidates
            if w > 35 and 12 < h < (h_img * 0.35):
                bounding_boxes.append((x, y, w, h))
                
        # Deduplicate heavily overlapping bounding boxes
        cleaned_boxes = []
        for box in bounding_boxes:
            x, y, w, h = box
            overlap = False
            for cb in cleaned_boxes:
                cx, cy, cw, ch = cb
                # Check if almost the same box
                if abs(x - cx) < 20 and abs(y - cy) < 15 and abs(w - cw) < 30 and abs(h - ch) < 20:
                    overlap = True
                    break
            if not overlap:
                cleaned_boxes.append(box)

        # Sort top-to-bottom
        cleaned_boxes.sort(key=lambda b: b[1])
        
        for (x, y, w, h) in cleaned_boxes:
            pad_y = int(h * 0.15)
            pad_x = int(w * 0.05)
            y1 = max(0, y - pad_y)
            y2 = min(h_img, y + h + pad_y)
            x1 = max(0, x - pad_x)
            x2 = min(w_img, x + w + pad_x)
            
            crop = image[y1:y2, x1:x2]
            if crop.size > 0:
                line_crops.append(crop)
                
        return line_crops
    except Exception:
        return []
