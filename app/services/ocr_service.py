from google.cloud import vision
import os
from config.settings import GOOGLE_CLOUD_CREDENTIALS_PATH

class OCRService:
    def __init__(self):
        if not os.path.exists(GOOGLE_CLOUD_CREDENTIALS_PATH):
            raise FileNotFoundError(f"GCP credentials not found: {GOOGLE_CLOUD_CREDENTIALS_PATH}")
        
        self.client = vision.ImageAnnotatorClient.from_service_account_file(
            GOOGLE_CLOUD_CREDENTIALS_PATH
        )
    
    def extract_text(self, image_path: str) -> dict:
        try:
            with open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            image = vision.Image(content=content)
            response = self.client.text_detection(image=image)
            
            if response.error.message:
                raise Exception(f"OCR Error: {response.error.message}")
            
            return self._convert_response_to_dict(response)
        
        except Exception as e:
            raise Exception(f"OCR processing failed: {str(e)}")
    
    def extract_text_from_bytes(self, image_bytes: bytes) -> dict:
        try:
            image = vision.Image(content=image_bytes)
            response = self.client.text_detection(image=image)
            
            if response.error.message:
                raise Exception(f"OCR Error: {response.error.message}")
            
            return self._convert_response_to_dict(response)
        
        except Exception as e:
            raise Exception(f"OCR processing failed: {str(e)}")
    
    def _convert_response_to_dict(self, response) -> dict:
        """Convert Google Vision response to expected format"""
        text_annotations = []
        
        for text in response.text_annotations:
            annotation = {
                "description": text.description,
                "boundingPoly": {
                    "vertices": [
                        {"x": vertex.x, "y": vertex.y}
                        for vertex in text.bounding_poly.vertices
                    ]
                }
            }
            text_annotations.append(annotation)
        
        return {"textAnnotations": text_annotations}