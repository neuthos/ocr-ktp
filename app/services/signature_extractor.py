import cv2
import numpy as np
from typing import Optional, Tuple, Dict
import os
import requests
from PIL import Image
import io
import base64
import uuid

class SignatureExtractorService:
    def __init__(self):
        
        self.cdn_base_url = os.getenv('CDN_BASE_URL', '')
        self.cdn_api_key = os.getenv('CDN_API_KEY', '')
        
        
        self.blur_kernel = 3
        self.threshold_value = 127
        self.min_signature_area = 500
        self.padding = 20
    
    def extract_signature(self, image_path: str) -> Optional[Dict]:
        """Extract signature from image file"""
        try:
            
            img = cv2.imread(image_path)
            if img is None:
                return None
            
            return self._process_signature(img)
            
        except Exception as e:
            raise Exception(f"Signature extraction failed: {str(e)}")
    
    def extract_signature_from_bytes(self, image_bytes: bytes) -> Optional[Dict]:
        """Extract signature from image bytes"""
        try:
            
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return None
            
            return self._process_signature(img)
            
        except Exception as e:
            raise Exception(f"Signature extraction failed: {str(e)}")
    
    def _process_signature(self, img: np.ndarray) -> Optional[Dict]:
        """Process image to extract signature"""
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        
        blurred = cv2.GaussianBlur(gray, (self.blur_kernel, self.blur_kernel), 0)
        
        
        
        _, binary = cv2.threshold(blurred, self.threshold_value, 255, cv2.THRESH_BINARY_INV)
        
        
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
        
        
        largest_contour = max(contours, key=cv2.contourArea)
        
        
        if cv2.contourArea(largest_contour) < self.min_signature_area:
            
            significant_contours = [c for c in contours if cv2.contourArea(c) > 50]
            if not significant_contours:
                return None
            
            
            all_points = np.concatenate(significant_contours)
            x, y, w, h = cv2.boundingRect(all_points)
        else:
            
            x, y, w, h = cv2.boundingRect(largest_contour)
        
        
        x = max(0, x - self.padding)
        y = max(0, y - self.padding)
        w = min(img.shape[1] - x, w + 2 * self.padding)
        h = min(img.shape[0] - y, h + 2 * self.padding)
        
        
        signature_crop = binary[y:y+h, x:x+w]
        
        
        signature_rgba = self._create_transparent_signature(signature_crop)
        
        return {
            'image': signature_rgba,
            'bbox': {'x': x, 'y': y, 'width': w, 'height': h},
            'confidence': 0.9  
        }
    
    def _create_transparent_signature(self, binary_img: np.ndarray) -> np.ndarray:
        """Convert binary image to transparent PNG with black signature"""
        h, w = binary_img.shape
        
        
        signature_rgba = np.zeros((h, w, 4), dtype=np.uint8)
        
        
        
        mask = binary_img > 127
        
        
        signature_rgba[mask, 0] = 0    
        signature_rgba[mask, 1] = 0    
        signature_rgba[mask, 2] = 0    
        signature_rgba[mask, 3] = 255  
        
        
        
        return signature_rgba
    
    def upload_to_cdn(self, signature_image: np.ndarray, filename: str = None) -> Tuple[Optional[str], str]:
        """Upload signature to CDN"""
        try:
            if not self.cdn_base_url:
                return None, "CDN_BASE_URL not configured"
            
            
            if not filename:
                filename = f"signature_{uuid.uuid4()}.png"
            
            
            _, buffer = cv2.imencode('.png', signature_image)
            
            
            files = {
                'file': (filename, buffer.tobytes(), 'image/png')
            }
            
            headers = {}
            if self.cdn_api_key:
                headers['Authorization'] = f'Bearer {self.cdn_api_key}'
            
            
            response = requests.post(
                f"{self.cdn_base_url}/api/v1/files/upload",
                files=files,
                headers=headers,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                file_url = result.get('file_url') or result.get('url')
                return file_url, "Upload successful"
            else:
                return None, f"CDN upload failed: {response.status_code}"
                
        except Exception as e:
            return None, f"CDN upload error: {str(e)}"
    
    def extract_and_upload(self, image_path: str = None, image_bytes: bytes = None) -> Dict:
        """Extract signature and upload to CDN"""
        try:
            
            if image_path:
                signature_result = self.extract_signature(image_path)
            elif image_bytes:
                signature_result = self.extract_signature_from_bytes(image_bytes)
            else:
                return {
                    'success': False,
                    'message': 'No image provided'
                }
            
            if not signature_result:
                return {
                    'success': False,
                    'message': 'No signature found in image'
                }
            
            
            cdn_url, message = self.upload_to_cdn(signature_result['image'])
            
            if not cdn_url:
                return {
                    'success': False,
                    'message': f'Failed to upload signature: {message}'
                }
            
            return {
                'success': True,
                'message': 'Signature extracted and uploaded successfully',
                'signature_url': cdn_url,
                'confidence': signature_result['confidence'],
                'dimensions': {
                    'width': signature_result['image'].shape[1],
                    'height': signature_result['image'].shape[0]
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }