from pdfminer.high_level import extract_text
from io import BytesIO
import json
from typing import Dict, Any
import tempfile
import os

def extract_text_from_pdf(content: bytes) -> str:
    """PDF 파일에서 텍스트를 추출합니다."""
    try:
        print("\n========== PDF EXTRACTION START ==========")
        print(f"PDF content size: {len(content)} bytes")
        
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name
            print(f"Created temporary file: {temp_path}")
        
        # PDF 텍스트 추출
        text = extract_text(temp_path)
        print(f"Extracted text length: {len(text)} characters")
        print("First 200 characters of extracted text:")
        print(text[:200] + "..." if len(text) > 200 else text)
        
        # 임시 파일 삭제
        os.unlink(temp_path)
        print("Temporary file deleted")
        
        text = text.strip()
        if not text:
            print("WARNING: No text extracted from PDF")
        
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        raise Exception("Failed to extract text from PDF")
