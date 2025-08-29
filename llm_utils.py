import os
import time
import traceback
import asyncio
from typing import List, Dict
from collections import Counter
import re
from models import DocumentAnalysis, KeywordInfo
from openai import AsyncOpenAI
import httpx
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# OpenAI API 초기화
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

# OpenAI 비동기 클라이언트 초기화
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# GPT 모델 설정
GPT_MODEL = "gpt-4-turbo-preview"  # 최신 GPT-4 모델 사용
GPT_MAX_TOKENS = 4000  # 토큰 제한 설정

async def generate_completion(prompt: str, max_retries: int = 3) -> str:
    """OpenAI API를 사용하여 텍스트를 생성합니다."""
    for attempt in range(max_retries):
        try:
            completion = await client.chat.completions.create(
                model=GPT_MODEL,
                messages=[{
                    "role": "system",
                    "content": "한국어로 명확하고 전문적으로 응답해주세요."
                }, {
                    "role": "user",
                    "content": prompt
                }],
                temperature=0.7,
                max_tokens=GPT_MAX_TOKENS
            )
            # Make sure we can access the response before returning
            if not completion or not completion.choices or not completion.choices[0].message:
                raise ValueError("Invalid response structure from OpenAI API")
            return completion.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API 호출 오류 (시도 {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # exponential backoff
                continue
            raise

def extract_keywords(text: str, min_length: int = 2, top_k: int = 10) -> List[KeywordInfo]:
    """고도화된 키워드 추출 알고리즘을 사용하여 텍스트에서 핵심 키워드를 추출합니다.
    
    특징:
    1. TextRank + TF-IDF 하이브리드 방식
    2. 문맥 기반 키워드 중요도 계산
    3. 정확한 키워드 출현 횟수 계산
    4. 전문용어 및 명사구 우선 추출
    5. 유사 키워드 통합
    6. 키워드가 포함된 문장 추출
    """
    import numpy as np
    import networkx as nx
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from konlpy.tag import Okt
    from collections import defaultdict
    
    class KeywordExtractor:
        def __init__(self):
            self.okt = Okt()
            self.vectorizer = TfidfVectorizer(
                min_df=1,
                max_df=0.9,
                smooth_idf=True
            )
        
        def preprocess_text(self, text):
            """텍스트 전처리 및 문장 분리"""
            # 괄호 안의 보조 설명 제거
            text = re.sub(r'\([^)]*\)', '', text)
            # 특수문자 제거 (마침표는 문장 구분을 위해 유지)
            text = re.sub(r'[^가-힣a-zA-Z0-9\s\.]', ' ', text)
            # 중복 공백 제거
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
        
        def count_keyword_occurrences(self, text: str, keyword: str) -> int:
            """주어진 텍스트에서 키워드의 실제 출현 횟수를 계산"""
            # 전처리
            text = re.sub(r'\([^)]*\)', '', text)  # 괄호 내용 제거
            text = re.sub(r'\s+', ' ', text)  # 공백 정리
            
            # 대소문자 구분 없이 검색
            return len(re.findall(re.escape(keyword.strip()), text, re.IGNORECASE))
            
        def get_keyword_contexts(self, text: str, keyword: str) -> List[str]:
            """주어진 키워드가 포함된 문장만을 추출"""
            # 전처리
            text = re.sub(r'\.{3,}', '.', text)  # 연속된 마침표를 하나로
            text = re.sub(r'([.!?])\s*([.!?])+', r'\1', text)  # 중복된 문장 부호 제거
            text = text.strip()

            # 문장 분리
            sentence_pattern = r'[^.!?]+[.!?]'
            sentences = [s.strip() for s in re.findall(sentence_pattern, text) if s.strip()]

            # 키워드가 포함된 문장만 추출
            keyword_lower = keyword.strip().lower()
            matching_sentences = []
            seen = set()

            for sentence in sentences:
                if keyword_lower in sentence.lower():
                    # 문장 정규화 (중복 체크용)
                    normalized = re.sub(r'\s+', ' ', sentence).strip()
                    
                    # 중복이 아닌 경우만 추가
                    if normalized not in seen:
                        matching_sentences.append(sentence)
                        seen.add(normalized)

            return matching_sentences

    def combine_related_terms(terms_dict):
        """관련된 용어들을 하나로 통합"""
        combined = {}
        used = set()
        
        # 유사어 그룹 정의
        similar_terms = {
            '개발': {'설계', '구현', '제작'},
            '분석': {'해석', '조사', '평가'},
            '관리': {'운영', '유지', '보수'},
            '서버': {'서버군', '서버팜', '서버풀'},
            '기술': {'테크', '기법', '방식'}
        }
        
        for term, count in sorted(terms_dict.items(), key=lambda x: x[1], reverse=True):
            if term in used:
                continue
                
            # 관련 용어 찾기
            related = set()
            for key, values in similar_terms.items():
                if term in values or term == key:
                    related = values | {key}
                    break
            
            # 카운트 통합
            total_count = count
            final_term = term
            for r in related:
                if r in terms_dict and r != term:
                    total_count += terms_dict[r]
                    used.add(r)
                    if terms_dict[r] > count:  # 더 자주 등장하는 용어를 대표어로 선택
                        final_term = r
                        
            used.add(term)
            combined[final_term] = total_count
            
        return combined
    
    def calculate_keyword_importance(word, sentences, tf_idf_score):
        """키워드 중요도 계산을 위한 복합 점수"""
        importance = tf_idf_score
        
        # 1. 문서 구조적 위치 가중치
        for i, sent in enumerate(sentences):
            if word in sent:
                # 문서 앞쪽에 등장할수록 높은 가중치
                position_weight = 1 + (len(sentences) - i) / len(sentences)
                importance *= position_weight
                break
        
        # 2. 전문성 가중치
        if any(tech in word for tech in ['AI', 'ML', 'API', 'SDK', 'DB']):
            importance *= 1.3
        
        # 3. 복합 명사구 가중치
        if ' ' in word and len(word.split()) >= 2:
            importance *= 1.2
            
        # 4. 영어 전문용어 가중치
        if any(c.isascii() for c in word):
            importance *= 1.1
            
        return importance

    def normalize_text(text):
        """텍스트 정규화 및 문장 분리"""
        # 문장 단위로 분리
        sentences = text.split('.')
        # 빈 문장 제거 및 정규화
        normalized = []
        for sent in sentences:
            sent = sent.strip()
            if sent:
                # 불필요한 공백 제거
                sent = re.sub(r'\s+', ' ', sent)
                # 영문 대소문자 통일
                sent = re.sub(r'[A-Za-z]+', lambda m: m.group(0).lower(), sent)
                normalized.append(sent)
        return normalized
    
    def get_candidate_words(sentences):
        okt = Okt()
        
        def is_meaningful_phrase(phrase):
            """구가 의미있는 전문 용어인지 확인"""
            # 일반적인 동작/상태 단어로만 구성된 경우 제외
            action_words = {
                '확장', '구성', '설정', '적용', '추가', '삭제', '변경', '수정',
                '제공', '운영', '관리', '유지', '보수', '지원', '처리', '진행',
                '수행', '실시', '담당', '추진'
            }
            status_words = {
                '완료', '진행중', '예정', '필요', '가능', '불가', '준비',
                '최신', '기존', '신규', '이전', '현재', '미래'
            }
            generic_words = {
                '전문', '기본', '고급', '특수', '일반', '공통', '기타',
                '다양', '특정', '주요', '기초', '핵심', '표준'
            }
            
            words = phrase.split()
            # 일반 동작/상태 단어로만 구성된 경우 제외
            if all(w in action_words or w in status_words or w in generic_words for w in words):
                return False
                
            # 실제 기술 용어나 구체적인 명사가 포함된 경우만 허용
            # 예: "클라우드 확장", "시스템 구성" 등
            technical_terms = {
                # 기술/직무 분야
                '클라우드', '시스템', '네트워크', '데이터', '서버', '보안',
                '소프트웨어', '하드웨어', '메모리', '프로세스', '인터페이스',
                '엔지니어링', '아키텍처', '프로그래밍', '개발자', '엔지니어',
                '디자이너', '기획자', '분석가', '매니저', 'PM', 'PO',
                # 기술 스택
                'API', 'GPU', 'CPU', 'ML', 'AI', '데이터베이스', '알고리즘',
                '프레임워크', '플랫폼', '프로토콜', '아키텍처', '인프라',
                'React', 'Vue', 'Angular', 'Node.js', 'Python', 'Java',
                'Spring', 'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP',
                # 전문 분야
                '머신러닝', '딥러닝', '블록체인', '빅데이터', 'IoT',
                '클라우드', '사이버보안', '데브옵스', 'CI/CD', '마이크로서비스',
                '프론트엔드', '백엔드', '풀스택', '임베디드', '모바일',
                # 비즈니스/프로세스
                '기획', '설계', '구현', '배포', '운영', '최적화',
                '프로젝트', '애자일', '스크럼', '칸반', '워터폴',
                # 산업 분야
                '금융', '의료', '교육', '제조', '물류', '유통',
                '게임', '미디어', '콘텐츠', '커머스', '핀테크',
                # 비즈니스/도메인 용어
                '고객', '사용자', '제품', '서비스', '솔루션', '프로젝트',
                '매출', '비용', '계약', '정책', '전략', '브랜드'
            }
            
            # 일반적인 수식어 패턴
            generic_patterns = {'전문', '특별', '기본', '주요', '핵심', '고급',
                              '일반', '특수', '공통', '표준', '필수', '선택'}
            
            # 구를 단어로 분리
            words = phrase.split()
            
            # 일반적인 수식어로만 구성된 경우 제외
            if all(w in generic_patterns for w in words):
                return False
            
            # 실제 기술 용어나 구체적인 명사가 포함된 경우 허용
            if any(term in phrase for term in technical_terms):
                return True
                
            return len(words) > 1  # 단일 단어가 아닌 경우 기본적으로 허용
        
        stop_words = {
            # 기본 조사/어미
            '이', '가', '은', '는', '을', '를', '의', '에', '로', '으로',
            # 일반 동사/형용사
            '하다', '되다', '있다', '없다', '같다', '이다', '아니다',
            # 자주 등장하는 일반적인 표현
            '것', '등', '수', '점', '년', '월', '일', '때', '중', '내',
            '받다', '주다', '시키다', '나오다', '들다', '보다', '가다',
            # 조사 결합형
            '위하여', '위해', '통하여', '통해', '의하여', '의해',
            '대하여', '대해', '관하여', '관해', '따라서', '따라',
            # 기타 연결어미와 조사
            '대한', '위한', '의한', '통한', '따른', '으로써',
            '까지', '부터', '에서', '에게', '으로', '처럼',
            # 일반적인 수식어/형용사
            '최신', '기존', '신규', '새로운', '이전', '현재', '최근',
            '많은', '적은', '큰', '작은', '높은', '낮은', '좋은', '나쁜',
            '일반', '특별', '보통', '기타', '다양', '여러', '모든', '각종',
            '전문', '기본', '주요', '핵심', '고급', '상세', '세부', '전체',
            '상위', '하위', '일부', '전부', '특수', '공통', '표준', '임의',
            '필수', '선택', '기초', '심화', '부가', '기본적', '특징적',
            # 시간/상태 관련 수식어
            '최초', '마지막', '처음', '현재', '미래', '과거', '기존', '신규',
            '임시', '영구', '임의', '즉시', '서서히', '이후', '이전',
            # 동작/상태를 나타내는 명사형
            '확장', '구성', '설정', '적용', '추가', '삭제', '변경', '수정',
            '생성', '제거', '등록', '해제', '실행', '중지', '시작', '종료',
            '관리', '운영', '유지', '보수', '점검', '확인', '검토', '검사',
            '구현', '처리', '동작', '작동', '진행', '수행', '실시', '활용',
            # 일반적인 동작/상태 관련 명사
            '방식', '방법', '과정', '절차', '단계', '상태', '정도', '형태',
            '구조', '체계', '방안', '방침', '기준', '원칙', '정책', '규칙'
        }
        
        candidates = []
        for sentence in sentences:
            # 명사구와 명사 추출
            words = okt.phrases(sentence)  # 의미있는 명사구 추출
            words.extend(okt.nouns(sentence))  # 개별 명사도 추가
            
            # 필터링
            words = [
                word for word in words
                if len(word) >= min_length
                and word not in stop_words
                and not word.isdigit()
                and not any(c.isdigit() for c in word)
                and not any(pattern in word for pattern in [
                    '할', '하고', '되어', '있는',  # 기본 동사 패턴
                    '위해', '통해', '의해', '까지', '부터',  # 조사 결합
                    '대해', '관해', '따라', '의한', '으로써',  # 부사격 조사
                    '하기', '되기', '시키기', '만들기',  # 동사의 명사형
                    '최신', '기존', '신규', '새로운',  # 일반적인 수식어
                    '최근', '현재', '이전', '이후',  # 시간 관련 수식어
                    '많은', '적은', '높은', '낮은',  # 정도 관련 수식어
                    # 동작/상태 관련 패턴
                    '확장', '구성', '설정', '적용',
                    '추가', '삭제', '변경', '수정',
                    '등록', '해제', '실행', '중지',
                    '방식', '방법', '상태', '단계'
                ])
            ]
            candidates.extend(words)
        
        return list(set(candidates))  # 중복 제거
    
    def build_graph(sentences, candidates):
        # TF-IDF 행렬 생성
        vectorizer = TfidfVectorizer(vocabulary=candidates)
        tfidf_matrix = vectorizer.fit_transform(sentences)
        
        # 단어 간 동시 출현 그래프 구축
        graph = np.zeros((len(candidates), len(candidates)))
        for i in range(len(sentences)):
            word_ids = tfidf_matrix[i].nonzero()[1]
            for id1 in word_ids:
                for id2 in word_ids:
                    if id1 != id2:
                        # TF-IDF 값을 가중치로 사용
                        weight = tfidf_matrix[i, id1] * tfidf_matrix[i, id2]
                        graph[id1][id2] += weight
        
        return graph

    # 문장 정규화 및 후보 단어 추출
    sentences = normalize_text(text)
    candidates = get_candidate_words(sentences)
    
    if not candidates:
        return []
    
    # 그래프 구축 및 TextRank 적용
    graph = build_graph(sentences, candidates)
    nx_graph = nx.from_numpy_array(graph)
    scores = nx.pagerank(nx_graph)

    # 형태소 분석기 초기화
    okt = Okt()
    
    # 불용어 목록
    stop_words = {
        # 일반적인 조사/어미
        '이', '가', '을', '를', '의', '에', '로', '으로', '과', '와', '한', '하는', '은', '는',
        # 대명사/부사/접속사
        '저', '나', '내', '우리', '저희', '너', '그', '이것', '그것', '매우', '가장', '잘', '더',
        '그리고', '또는', '그러나', '하지만', '또한', '그래서',
        # 일반적인 동사/형용사
        '하다', '되다', '있다', '없다', '같다', '보다', '않다',
        # 자주 등장하는 일반 명사
        '것', '등', '때', '데', '수', '중', '점', '말', '일', '면', '제', '건', '분', '개',
        # 비즈니스 관련 일반 용어
        '기업', '회사', '업체', '시장', '산업', '경우', '상황', '현재', '계획', '방안',
        # 일반적인 동사의 명사형
        '제공', '활용', '사용', '적용', '도입', '추진', '진행', '수행', '처리', '실시',
        '확인', '설정', '구성', '관리', '유지', '변경', '개선', '향상', '증가', '감소',
        # 일반적인 서술어의 명사형
        '가능', '필요', '중요', '가능성', '필요성', '중요성',
        # 비즈니스 문서에서 자주 등장하는 동사의 명사형
        '운영', '개발', '지원', '분석', '평가', '검토', '조사', '연구', '교육', '안내',
        '요청', '문의', '답변', '설명', '소개', '안내', '진단', '판단', '결정'
    }
    
    # 텍스트에서 명사구 추출
    nouns = []
    for sent in text.split('.'):
        nouns.extend(okt.phrases(sent))  # phrases() 메소드로 의미있는 명사구 추출
    
    # 단어별 중요도 점수와 문맥 수집
    keyword_infos = []
    ranked_words = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # 상위 키워드 선택 및 정보 수집
    for i, (word_idx, score) in enumerate(ranked_words):
        if i >= top_k:
            break
            
        word = candidates[word_idx]
        
        # 키워드가 포함된 가장 관련성 높은 문장 찾기
        matching_sentences = []
        for sent in sentences:
            if word in sent:
                matching_sentences.append(sent)
        
        if matching_sentences:
            # TextRank 점수를 기반으로 중요도 레벨 결정
            importance_level = "핵심" if score > np.mean(list(scores.values())) + np.std(list(scores.values())) else ""
            
            # 키워드 추출기 초기화
            extractor = KeywordExtractor()
            
            # 키워드의 실제 출현 횟수 계산
            count = extractor.count_keyword_occurrences(text, word)
            
            # 키워드가 포함된 문장들 추출
            contexts = extractor.get_keyword_contexts(text, word)
            
            if count >= 2:  # 최소 2번 이상 등장하는 키워드만 포함
                keyword_infos.append(KeywordInfo(
                    text=word,
                    count=count,  # 실제 출현 횟수 사용
                    context=contexts  # 키워드가 포함된 문장들
                ))
    
    return keyword_infos

async def generate_with_retry(prompt: str, max_retries: int = 2, initial_delay: int = 1) -> str:
    """재시도 로직이 포함된 최적화된 생성 함수"""
    for attempt in range(max_retries):
        try:
            response = await client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": "문서 분석 전문가로서 핵심 내용을 간단명료하게 요약하세요."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # 더 일관된 결과를 위해 낮춤
                max_tokens=GPT_MAX_TOKENS,
                presence_penalty=0,
                frequency_penalty=0,
                response_format={"type": "text"},  # 구조화된 응답 강제
                seed=42  # 일관성을 위한 시드 설정
            )
            
            if not response or not response.choices or not response.choices[0].message:
                raise ValueError("Invalid response structure from OpenAI API")
                
            return response.choices[0].message.content
            
        except Exception as e:
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)
                print(f"Error occurred: {str(e)}. Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
                continue
            raise e

async def analyze_with_llm(text: str, filename: str = "") -> DocumentAnalysis:
    """문서를 분석하여 주요 내용을 추출합니다."""
    if not text.strip():
        raise ValueError("Empty text provided for analysis")

    try:
        print(f"Starting analysis for file: {filename}")
        # 텍스트 전처리 최적화
        text = re.sub(r'\s+', ' ', text)  # 연속된 공백 제거
        text = text.strip()
        print(f"Text length after preprocessing: {len(text)} characters")
        
        # 먼저 간단한 테스트로 API 연결 확인
        test_prompt = "간단한 테스트입니다."
        try:
            test_response = await generate_completion(test_prompt)
            print("OpenAI API 테스트 성공")
            print(f"Test response: {test_response}")
        except Exception as e:
            print(f"OpenAI API 테스트 실패: {str(e)}")
            raise

        # 텍스트 길이가 너무 길 경우 청크로 나누어 처리
        MAX_CHARS = 4000
        if len(text) > MAX_CHARS:
            chunks = [text[i:i + MAX_CHARS] for i in range(0, len(text), MAX_CHARS)]
            summaries = []
            
            # 청크별로 병렬 처리
            async def process_chunk(chunk):
                summary_prompt = f"다음 텍스트의 핵심만 1-2문장으로 요약:\n\n{chunk}"
                return await generate_completion(summary_prompt)
            
            tasks = [process_chunk(chunk) for chunk in chunks]
            summaries = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 오류 체크
            valid_summaries = []
            for summary in summaries:
                if isinstance(summary, Exception):
                    print(f"Chunk processing error: {str(summary)}")
                    continue
                valid_summaries.append(summary)
            
            if not valid_summaries:
                raise ValueError("Failed to process any text chunks")
            
            text = ' '.join(valid_summaries)

        # 문서 분석 프롬프트
        prompt = f'''다음 문서를 분석하여 핵심 내용만 추출해주세요:

{text}

아래 형식을 정확히 지켜서 응답해주세요:
제목: [3-5단어로 문서의 핵심 주제만]

요약: [아래 규칙을 지켜서 작성]
- 문서의 핵심 내용을 2-3개의 간단한 문장으로
- 가장 중요한 내용을 먼저 언급
- 불필요한 수식어 제외

주요내용: [중요도 순서로 나열]
- 가장 중요한 포인트 (한 문장으로)
- 두 번째로 중요한 포인트 (한 문장으로)
- 세 번째로 중요한 포인트 (한 문장으로)'''

        # GPT 분석과 키워드 추출을 동시에 실행
        try:
            response, keywords = await asyncio.gather(
                generate_completion(prompt),
                asyncio.to_thread(extract_keywords, text)
            )
        except Exception as e:
            print(f"Error in analysis: {str(e)}")
            raise
        
        # 응답 파싱
        title = ""
        brief_summary = ""
        key_points = []
        
        current_section = None
        for line in response.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('제목:'):
                title = line.split(':', 1)[1].strip()
                current_section = 'title'
            elif line.startswith('요약:'):
                brief_summary = line.split(':', 1)[1].strip()
                current_section = 'summary'
            elif line.startswith('주요내용:'):
                current_section = 'points'
            elif line.startswith('-') and current_section == 'points':
                point = line[1:].strip()
                if point:  # 빈 bullet point 제외
                    key_points.append(point)
            elif current_section == 'summary' and not line.startswith('주요내용:'):
                brief_summary += ' ' + line  # 여러 줄의 요약 텍스트 처리
        
        # keywords는 이미 asyncio.gather에서 받아왔으므로 추가 처리 필요 없음
        
        # 결과 정제
        # 1. 제목 정제
        if title:
            # 불필요한 수식어구 및 조사 제거
            title = re.sub(r'^(관련|관한|대한|위한|about|regarding)\s+', '', title, flags=re.IGNORECASE)
            title = re.sub(r'\s*(의|에|를|을|에서|으로|이|가)\s+', ' ', title)
            # 괄호 내용 제거
            title = re.sub(r'\([^)]*\)', '', title)
            # 특수문자 제거 및 공백 정리
            title = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', title)
            title = re.sub(r'\s+', ' ', title).strip()
            
            # 길이 제한
            words = title.split()
            if len(words) > 5:
                title = ' '.join(words[:5])

        # 2. 요약 정제
        if brief_summary:
            # 중복 문장 제거
            sentences = [s.strip() for s in brief_summary.split('.') if s.strip()]
            unique_sentences = []
            seen = set()
            for sentence in sentences:
                clean_sent = re.sub(r'\s+', ' ', sentence).lower()
                if clean_sent not in seen:
                    seen.add(clean_sent)
                    unique_sentences.append(sentence)
            brief_summary = '. '.join(unique_sentences[:3]) + '.'
        
        # 3. 주요 내용 정제
        if key_points:
            # 각 포인트 정제 및 중복 제거
            refined_points = []
            seen = set()
            for point in key_points:
                # 불필요한 수식어 제거
                point = re.sub(r'^(그리고|또한|따라서|이에)\s+', '', point)
                # 특수문자 처리
                point = re.sub(r'[^\w\s가-힣.,]', '', point)
                # 공백 정리
                point = re.sub(r'\s+', ' ', point).strip()
                
                if point and point.lower() not in seen:
                    seen.add(point.lower())
                    refined_points.append(point)
            
            key_points = refined_points[:5]  # 최대 5개로 제한
        
        # 결과 반환
        return DocumentAnalysis(
            filename=filename,
            title=title or "문서 제목",
            summary=brief_summary.strip() or "요약을 생성할 수 없습니다.",
            keywords=keywords,
            mainTopics=key_points or ["주요 내용을 추출할 수 없습니다."],
            recommendations=[]  # 기본값
        )
        
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        traceback.print_exc()
        raise ValueError(f"Failed to analyze document: {str(e)}")
