from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import os
import aiofiles
from app.models import KTPResponse, ErrorResponse
from app.services.smart_ocr_service import SmartOCRService
from app.services.ktp_extractor import KTPExtractor
from app.services.signature_extractor import SignatureExtractorService
from app.utils.helpers import (
    is_allowed_file, 
    validate_file_size, 
    generate_unique_filename,
    validate_image,
    cleanup_temp_file
)
from config.settings import TEMP_DIR
from pydantic import BaseModel
from typing import Optional

app = FastAPI(
    title="KTP OCR & Signature Extraction API",
    description="API untuk ekstraksi data KTP dan tanda tangan",
    version="2.0.0"
)

# Initialize services
ocr_service = SmartOCRService()
ktp_extractor = KTPExtractor()
signature_service = SignatureExtractorService()

class SignatureResponse(BaseModel):
    success: bool
    message: str
    signature_url: Optional[str] = None
    confidence: Optional[float] = None
    dimensions: Optional[dict] = None

@app.post("/extract-ktp", response_model=KTPResponse)
async def extract_ktp(file: UploadFile = File(...)):
    """
    Extract data from KTP (Indonesian ID Card) image
    
    - **file**: Image file (JPG, JPEG, PNG)
    - Returns: Extracted KTP data including NIK, name, address, etc.
    """
    temp_file_path = None
    
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file selected")
        
        if not is_allowed_file(file.filename):
            raise HTTPException(
                status_code=400, 
                detail="File type not allowed. Supported: jpg, jpeg, png"
            )
        
        # Read file
        contents = await file.read()
        file_size = len(contents)
        
        if not validate_file_size(file_size):
            raise HTTPException(
                status_code=400, 
                detail="File size too large. Maximum 10MB allowed"
            )
        
        # Save temporarily
        temp_filename = generate_unique_filename(file.filename)
        temp_file_path = os.path.join(TEMP_DIR, temp_filename)
        
        async with aiofiles.open(temp_file_path, 'wb') as f:
            await f.write(contents)
        
        # Validate image
        if not validate_image(temp_file_path):
            raise HTTPException(status_code=400, detail="Invalid image file")
        
        # Extract text using Google Vision
        ocr_result = ocr_service.extract_text(temp_file_path)
        
        # Extract KTP data
        ktp_data = ktp_extractor.extract_ktp_data(ocr_result)
        
        # Validate NIK
        if not ktp_data.nik:
            return KTPResponse(
                success=False,
                message="NIK not found. Please ensure the image is a valid KTP",
                data=None
            )
        
        return KTPResponse(
            success=True,
            message="KTP data extracted successfully",
            data=ktp_data
        )
    
    except HTTPException:
        raise
    except Exception as e:
        return KTPResponse(
            success=False,
            message=f"Processing failed: {str(e)}",
            data=None
        )
    
    finally:
        if temp_file_path:
            cleanup_temp_file(temp_file_path)

@app.post("/extract-signature", response_model=SignatureResponse)
async def extract_signature(file: UploadFile = File(...)):
    """
    Extract signature from image (signature on white paper)
    
    - **file**: Image file containing signature on white background
    - Returns: URL of extracted signature (transparent PNG) uploaded to CDN
    """
    temp_file_path = None
    
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file selected")
        
        if not is_allowed_file(file.filename):
            raise HTTPException(
                status_code=400, 
                detail="File type not allowed. Supported: jpg, jpeg, png"
            )
        
        # Read file
        contents = await file.read()
        file_size = len(contents)
        
        if not validate_file_size(file_size):
            raise HTTPException(
                status_code=400, 
                detail="File size too large. Maximum 10MB allowed"
            )
        
        # Process directly from bytes (no need to save file)
        result = signature_service.extract_and_upload(image_bytes=contents)
        
        return SignatureResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        return SignatureResponse(
            success=False,
            message=f"Processing failed: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "message": "API is running",
        "services": {
            "ktp_extraction": "active",
            "signature_extraction": "active"
        }
    }

@app.get("/")
async def root():
    """API information"""
    return {
        "name": "KTP OCR & Signature Extraction API",
        "version": "2.0.0",
        "endpoints": [
            {
                "path": "/extract-ktp",
                "method": "POST",
                "description": "Extract data from KTP image"
            },
            {
                "path": "/extract-signature",
                "method": "POST", 
                "description": "Extract signature from image"
            },
            {
                "path": "/health",
                "method": "GET",
                "description": "Health check"
            },
            {
                "path": "/docs",
                "method": "GET",
                "description": "API documentation"
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)