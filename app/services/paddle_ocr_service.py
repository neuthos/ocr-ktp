from paddleocr import PaddleOCR
import cv2
import numpy as np
from typing import Dict, List

class PaddleOCRService:
    def __init__(self):
        self.ocr = PaddleOCR(
            use_angle_cls=True, 
            lang='en',  
            use_gpu=False,
            show_log=False
        )
    
    def extract_text(self, image_path: str) -> dict:
        try:
            result = self.ocr.ocr(image_path, cls=True)
            return self._convert_to_gcv_format(result[0])
        except Exception as e:
            raise Exception(f"PaddleOCR processing failed: {str(e)}")
    
    def extract_text_from_bytes(self, image_bytes: bytes) -> dict:
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            result = self.ocr.ocr(img, cls=True)
            return self._convert_to_gcv_format(result[0])
        except Exception as e:
            raise Exception(f"PaddleOCR processing failed: {str(e)}")
    
    def _convert_to_gcv_format(self, paddle_result: List) -> dict:
        """Convert PaddleOCR format to Google Cloud Vision format"""
        if not paddle_result:
            return {"textAnnotations": []}
        
        text_annotations = []
        full_text = ""
        
        for line in paddle_result:
            if line is None:
                continue
                
            bbox = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            text = line[1][0]  # text
            confidence = line[1][1]  # confidence
            
            full_text += text + " "
            
            # Convert bbox to GCV format
            vertices = [
                {"x": int(bbox[0][0]), "y": int(bbox[0][1])},
                {"x": int(bbox[1][0]), "y": int(bbox[1][1])},
                {"x": int(bbox[2][0]), "y": int(bbox[2][1])},
                {"x": int(bbox[3][0]), "y": int(bbox[3][1])}
            ]
            
            text_annotation = {
                "description": text,
                "boundingPoly": {
                    "vertices": vertices
                }
            }
            text_annotations.append(text_annotation)
        
        # Add full text as first annotation (GCV format)
        if text_annotations:
            full_text_annotation = {
                "description": full_text.strip(),
                "boundingPoly": {
                    "vertices": [
                        {"x": 0, "y": 0},
                        {"x": 1000, "y": 0},
                        {"x": 1000, "y": 1000},
                        {"x": 0, "y": 1000}
                    ]
                }
            }
            text_annotations.insert(0, full_text_annotation)
        
        return {"textAnnotations": text_annotations}