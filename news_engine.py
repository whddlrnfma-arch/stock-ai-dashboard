import asyncio
import logging
from typing import List, Dict
from pydantic import BaseModel, Field

# 로깅 설정
logger = logging.getLogger("NewsEngine")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(ch)


# =====================================================================
# 1. Pydantic Models (API Response & Input)
# =====================================================================
class NewsArticle(BaseModel):
    article_id: str
    title: str
    content: str
    source: str
    
class GlobalNewsResponse(BaseModel):
    sentiment: str = Field(description="POSITIVE, NEUTRAL, or NEGATIVE")
    keywords: List[str] = Field(description="Matched global keywords")
    # 요구사항 2: 응답 데이터 표기 시 종목명 리턴
    related_domestic_stocks: List[str] = Field(description="Only KOSPI/KOSDAQ stock names")


# =====================================================================
# 2. THEME MAPPING & Rule Config
# =====================================================================
# 요구사항 1: 해외 종목(NVDA, TSLA 등) 완전 제외. 
# 오직 KOSPI/KOSDAQ 국내 주식 종목명만 매칭 풀에 포함.
THEME_MAPPING: Dict[str, List[str]] = {
    # 글로벌 키워드 -> 국내 수혜주/관련주
    "NVIDIA": ["SK하이닉스", "한미반도체", "이수페타시스"],
    "엔비디아": ["SK하이닉스", "한미반도체", "이수페타시스"],
    
    "TESLA": ["LG에너지솔루션", "삼성SDI", "에코프로", "엘앤에프"],
    "테슬라": ["LG에너지솔루션", "삼성SDI", "에코프로", "엘앤에프"],
    
    "APPLE": ["LG이노텍", "비에이치", "아이티엠반도체"],
    "애플": ["LG이노텍", "비에이치", "아이티엠반도체"],
    
    "MICROSOFT": ["삼성에스디에스", "더존비즈온"],
    "마이크로소프트": ["삼성에스디에스", "더존비즈온"],
    
    "AI": ["SK하이닉스", "네이버", "카카오", "솔트룩스"],
    "인공지능": ["SK하이닉스", "네이버", "카카오", "솔트룩스"],
    
    "SEMICONDUCTOR": ["삼성전자", "SK하이닉스", "리노공업"],
    "반도체": ["삼성전자", "SK하이닉스", "리노공업"],
    
    "BATTERY": ["LG에너지솔루션", "삼성SDI", "포스코퓨처엠"],
    "배터리": ["LG에너지솔루션", "삼성SDI", "포스코퓨처엠"]
}

# 긍정/부정 판단을 위한 감성 키워드 (Mock Logic용)
POSITIVE_WORDS = ["상승", "급등", "돌파", "호실적", "흑자", "성장", "수주", "기대", "최대", "UP", "SURGE", "BEAT", "GROWTH"]
NEGATIVE_WORDS = ["하락", "급락", "이탈", "적자", "우려", "쇼크", "둔화", "침체", "감소", "DOWN", "PLUNGE", "MISS", "RECESSION"]


# =====================================================================
# 3. News Engine Pipeline
# =====================================================================
class NewsEngine:
    """
    글로벌 뉴스 분석 및 테마주 매칭 엔진
    """
    def __init__(self):
        # 내부 백엔드 연산용 코드->이름 매핑 딕셔너리
        # 내부에서는 코드를 식별자로 쓰지만, 외부 API 리턴시에는 종목명으로 변환
        self.code_to_name = {
            "000660": "SK하이닉스",
            "042700": "한미반도체",
            "005930": "삼성전자",
            "373220": "LG에너지솔루션",
            "006400": "삼성SDI",
            "086520": "에코프로",
            "011070": "LG이노텍",
            "035420": "네이버"
        }
        
    async def analyze_article(self, article: NewsArticle) -> GlobalNewsResponse:
        """
        뉴스 기사 본문을 분석하여 감성 및 관련 국내 상장사 명단 반환
        """
        # 영문/국문 대소문자 무시를 위해 전부 대문자화
        text = f"{article.title} {article.content}".upper()
        
        # 1. 감성 분석 (Sentiment Analysis)
        sentiment_score = 0
        for word in POSITIVE_WORDS:
            if word in text:
                sentiment_score += 1
        for word in NEGATIVE_WORDS:
            if word in text:
                sentiment_score -= 1
                
        if sentiment_score > 0:
            sentiment = "POSITIVE"
        elif sentiment_score < 0:
            sentiment = "NEGATIVE"
        else:
            sentiment = "NEUTRAL"
            
        # 2. 키워드 검출 및 국내 종목 매핑
        found_keywords = set()
        related_stocks = set()
        
        for key, stocks in THEME_MAPPING.items():
            if key in text:
                found_keywords.add(key)
                for stock_name in stocks:
                    # 규칙 2: 최종 응답 객체에는 반드시 '종목명'이 포함되도록 할 것
                    related_stocks.add(stock_name)
                    
        response = GlobalNewsResponse(
            sentiment=sentiment,
            keywords=list(found_keywords),
            related_domestic_stocks=list(related_stocks)
        )
        
        logger.info(f"[뉴스 분석 완료] ID: {article.article_id} | 감성: {response.sentiment} | 추출 키워드: {response.keywords} | 관련주: {response.related_domestic_stocks}")
        return response

    async def run_news_stream_mock(self):
        """
        비동기 뉴스 스트림 처리기 목업
        """
        mock_news = [
            NewsArticle(
                article_id="NEWS_001",
                title="NVIDIA 역대급 호실적 발표, AI 반도체 수요 급증 기대",
                content="NVIDIA(엔비디아)가 시장 기대치를 뛰어넘는 실적을 발표하며 상승세...",
                source="Bloomberg"
            ),
            NewsArticle(
                article_id="NEWS_002",
                title="Tesla 전기차 수요 둔화 우려에 주가 하락",
                content="Tesla(테슬라)의 주요 시장 판매량 감소와 실적 쇼크 우려가 커지고 있다.",
                source="Reuters"
            )
        ]
        
        logger.info("글로벌 뉴스 분석 엔진 스트림 시작...")
        for article in mock_news:
            await self.analyze_article(article)
            await asyncio.sleep(1)


# =====================================================================
# 테스트 실행
# =====================================================================
if __name__ == "__main__":
    engine = NewsEngine()
    asyncio.run(engine.run_news_stream_mock())
