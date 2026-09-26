import os

# Set environment flags before PaddleOCR imports
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"

import logging
from paddleocr import PaddleOCR

logging.getLogger('ppocr').setLevel(logging.ERROR)

ocr_engine = PaddleOCR(use_angle_cls=True, lang='en', use_mkldnn=False, enable_mkldnn=False)

def extract_text_with_boxes(image_path: str) -> list[dict]:
    result = ocr_engine.ocr(image_path)
    extracted_data = []
    
    if not result or not result[0]:
        return extracted_data
        
    for line in result[0]:
        box = line[0]
        text = line[1][0]
        confidence = float(line[1][1])
        
        x_coords = [point[0] for point in box]
        y_coords = [point[1] for point in box]
        
        extracted_data.append({
            "text": text,
            "confidence": confidence,
            "bounding_box": {
                "x1": min(x_coords),
                "y1": min(y_coords),
                "x2": max(x_coords),
                "y2": max(y_coords)
            }
        })
        
    return extracted_data