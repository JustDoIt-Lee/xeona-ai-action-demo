from pydantic import BaseModel
from typing import List, Dict

class KeywordInfo(BaseModel):
    text: str
    count: int
    context: List[str]  # 이 키워드가 등장하는 모든 문맥들

class DocumentAnalysis(BaseModel):
    filename: str  # 분석한 파일의 이름
    title: str  # 문서의 주요 주제/목적
    summary: str  # 2-3문장의 핵심 요약
    keywords: List[KeywordInfo]  # 주요 키워드와 빈도수
    mainTopics: List[str]  # 주요 내용 요약 (bullet points)
    recommendations: List[str] = []  # 추천사항 (옵션)
