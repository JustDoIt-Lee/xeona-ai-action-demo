# PDF 문서 분석기 (PDF Document Analyzer)

PDF 문서를 분석하여 주요 내용을 요약하고 키워드를 추출하는 AI 기반 문서 분석 도구입니다.

## 주요 기능

- 📄 PDF 파일 분석
- 📝 문서 내용 요약
- 🔑 주요 키워드 추출 및 문맥 분석
- 📌 핵심 토픽 추출
- 💡 AI 기반 추천사항 제공

## 기술 스택

### Frontend
- Next.js 14
- TypeScript
- Tailwind CSS
- Axios

### Backend
- FastAPI
- Python
- Docker

## 시작하기

### 사전 요구사항
- Node.js 18.0.0 이상
- Python 3.9 이상
- Docker

### 프로젝트 설정

1. **저장소 클론**
```bash
git clone https://github.com/JustDoIt-Lee/xeona-ai-action-demo.git
cd xeona-ai-action-demo
```

2. **환경변수 설정**
```bash
# .env 파일 생성
cp .env.example .env
# .env 파일을 수정하여 필요한 환경변수 설정
```

3. **Frontend 설정**
```bash
cd frontend
npm install
npm run dev
```

4. **Backend 설정**

Docker를 사용하는 경우:
```bash
docker build -t xeona-ai-backend .
docker run -p 8000:8000 --env-file .env xeona-ai-backend
```

직접 실행하는 경우:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 접속 방법

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API 문서: http://localhost:8000/docs

## 주요 기능 설명

### PDF 파일 업로드
- 드래그 앤 드롭 또는 파일 선택 버튼을 통해 PDF 파일 업로드
- PDF 파일 형식 검증

### 문서 분석
- AI 모델을 통한 문서 내용 분석
- 핵심 내용 요약 및 주요 키워드 추출
- 문맥 기반 키워드 분석

### 결과 표시
- 문서 제목 및 요약
- 주요 키워드와 출현 빈도
- 키워드별 상세 문맥 확인 기능
- 주요 토픽 및 추천사항

## 라이센스

이 프로젝트는 MIT 라이센스로 제공됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.
