from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
from pdf_utils import extract_text_from_pdf
from llm_utils import analyze_with_llm
from models import DocumentAnalysis

load_dotenv()

app = FastAPI(title="PDF 문서 분석기")

@app.get("/")
async def read_root():
    return {"status": "ok", "message": "API is running"}

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용
    allow_credentials=False,  # False로 설정하여 CORS 제한 완화
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/analyze", response_model=DocumentAnalysis)
async def analyze_document(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF 파일만 지원됩니다")

    try:
        # PDF 파일 읽기
        content = await file.read()
        
        # PDF에서 텍스트 추출 (비동기로 처리)
        import asyncio
        text = await asyncio.to_thread(extract_text_from_pdf, content)
        
        # 텍스트가 비어있는지 확인
        if not text.strip():
            raise HTTPException(status_code=400, detail="PDF에서 텍스트를 찾을 수 없습니다")
        
        # LLM으로 분석 (비동기 실행)
        analysis = await analyze_with_llm(text, file.filename)
        return analysis
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
