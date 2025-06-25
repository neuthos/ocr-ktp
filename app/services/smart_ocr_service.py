import os
from typing import Dict, Optional
from app.services.paddle_ocr_service import PaddleOCRService

class SmartOCRService:
    def __init__(self):
        """
        Initialize with dual OCR services: Google Cloud Vision (primary) + PaddleOCR (fallback)
        """
        # Initialize PaddleOCR (always available)
        self.paddle_ocr = PaddleOCRService()
        
        # Try to initialize Google Cloud Vision
        self.google_ocr = None
        self.use_google = False
        
        try:
            from app.services.ocr_service import OCRService
            from config.settings import GOOGLE_CLOUD_CREDENTIALS_PATH
            
            if os.path.exists(GOOGLE_CLOUD_CREDENTIALS_PATH):
                self.google_ocr = OCRService()
                self.use_google = True
                print("✅ Google Cloud Vision initialized (primary)")
            else:
                print("⚠️ Google Cloud credentials not found")
                
        except Exception as e:
            print(f"⚠️ Google Cloud Vision failed to initialize: {e}")
        
        print(f"🚀 Smart OCR ready - Primary: {'Google Vision' if self.use_google else 'PaddleOCR'}, Fallback: {'PaddleOCR' if self.use_google else 'None'}")
    
    def extract_text(self, image_path: str) -> Dict:
        """
        Extract text with automatic fallback
        """
        # Try Google Cloud Vision first (if available)
        if self.use_google and self.google_ocr:
            try:
                print("🔄 Trying Google Cloud Vision...")
                result = self.google_ocr.extract_text(image_path)
                
                # Validate result has meaningful content
                if self._validate_ocr_result(result):
                    print("✅ Google Cloud Vision successful")
                    return result
                else:
                    print("⚠️ Google Cloud Vision returned empty result, trying fallback...")
                    
            except Exception as e:
                print(f"❌ Google Cloud Vision failed: {str(e)}")
                print("🔄 Falling back to PaddleOCR...")
        
        # Use PaddleOCR (fallback or primary)
        try:
            print("🔄 Using PaddleOCR...")
            result = self.paddle_ocr.extract_text(image_path)
            
            if self._validate_ocr_result(result):
                print("✅ PaddleOCR successful")
                return result
            else:
                print("⚠️ PaddleOCR returned empty result")
                return {'textAnnotations': []}
                
        except Exception as e:
            print(f"❌ PaddleOCR failed: {str(e)}")
            raise Exception(f"All OCR services failed. Last error: {str(e)}")
    
    def extract_text_from_bytes(self, image_bytes: bytes) -> Dict:
        """
        Extract text from bytes with automatic fallback
        """
        # Try Google Cloud Vision first (if available)
        if self.use_google and self.google_ocr:
            try:
                print("🔄 Trying Google Cloud Vision...")
                result = self.google_ocr.extract_text_from_bytes(image_bytes)
                
                if self._validate_ocr_result(result):
                    print("✅ Google Cloud Vision successful")
                    return result
                else:
                    print("⚠️ Google Cloud Vision returned empty result, trying fallback...")
                    
            except Exception as e:
                print(f"❌ Google Cloud Vision failed: {str(e)}")
                print("🔄 Falling back to PaddleOCR...")
        
        # Use PaddleOCR (fallback or primary)
        try:
            print("🔄 Using PaddleOCR...")
            result = self.paddle_ocr.extract_text_from_bytes(image_bytes)
            
            if self._validate_ocr_result(result):
                print("✅ PaddleOCR successful")
                return result
            else:
                print("⚠️ PaddleOCR returned empty result")
                return {'textAnnotations': []}
                
        except Exception as e:
            print(f"❌ PaddleOCR failed: {str(e)}")
            raise Exception(f"All OCR services failed. Last error: {str(e)}")
    
    def _validate_ocr_result(self, result: Dict) -> bool:
        """
        Validate if OCR result contains meaningful content
        """
        if not result or 'textAnnotations' not in result:
            return False
        
        annotations = result['textAnnotations']
        if not annotations:
            return False
        
        # Check if we have substantial text content
        total_text = ""
        for annotation in annotations:
            if 'description' in annotation:
                total_text += annotation['description']
        
        # Require at least 10 characters for meaningful content
        return len(total_text.strip()) >= 10
    
    def get_service_status(self) -> Dict:
        """
        Get status of both OCR services
        """
        return {
            "google_vision": {
                "available": self.use_google,
                "status": "ready" if self.use_google else "not configured"
            },
            "paddle_ocr": {
                "available": True,
                "status": "ready"
            },
            "primary_service": "google_vision" if self.use_google else "paddle_ocr"
        }