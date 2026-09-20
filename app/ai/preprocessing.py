# app/ai/preprocessing.py
import os
import cv2
import numpy as np
import pymupdf as fitz
from pathlib import Path

# Unifying storage locations
PROCESSED_DOCS_DIR = Path("storage/processed_documents")
PROCESSED_DOCS_DIR.mkdir(parents=True, exist_ok=True)

# Also create data/processed_documents to prevent broken links in any legacy path
Path("data/processed_documents").mkdir(parents=True, exist_ok=True)

def deskew_image(image: np.ndarray) -> np.ndarray:
    """Safely deskews an image using OpenCV minAreaRect bounding."""
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thresh > 0))
        
        if len(coords) < 50:
            return image
            
        angle = cv2.minAreaRect(coords)[-1]
        
        if angle < -45:
            angle = -(90 + angle)
        elif angle > 45:
            angle = 90 - angle
        else:
            angle = -angle
            
        # Ignore negligible tilt or near-90-degree flips
        if abs(angle) < 0.5 or abs(angle) > 45:
            return image
            
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated
    except Exception:
        return image

def enhance_image(image: np.ndarray) -> np.ndarray:
    """Applies fast Gaussian denoising and adaptive binarization for clean OCR."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    # Fast Gaussian blur removes salt-and-pepper noise in <5ms
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    # Adaptive thresholding creates high-contrast black-and-white text
    enhanced = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8
    )
    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)

def preprocess_document(file_path: str, doc_id: str) -> list[str]:
    """Converts PDF/Image, enhances it, and saves PNGs to storage/processed_documents/."""
    processed_paths = []
    file_ext = file_path.lower().split('.')[-1]
    
    if file_ext == "pdf":
        doc = fitz.open(file_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=300)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            
            if pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                
            deskewed = deskew_image(img)
            enhanced = enhance_image(deskewed)
            
            out_path = str(PROCESSED_DOCS_DIR / f"{doc_id}_page_{page_num+1}.png")
            cv2.imwrite(out_path, enhanced)
            processed_paths.append(out_path)
    else:
        img = cv2.imread(file_path)
        if img is not None:
            deskewed = deskew_image(img)
            enhanced = enhance_image(deskewed)
            out_path = str(PROCESSED_DOCS_DIR / f"{doc_id}_processed.png")
            cv2.imwrite(out_path, enhanced)
            processed_paths.append(out_path)
        
    return processed_paths