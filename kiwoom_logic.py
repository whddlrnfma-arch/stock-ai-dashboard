import logging
import time
from cachetools import TTLCache

# 로깅 설정 (방어적 프로그래밍의 핵심)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class KiwoomLogic:
    """
    키움증권 실시간 단타 데이터 처리 및 진입/이탈 강도 로직을 담당하는 핵심 클래스
    """
    def __init__(self, db_connection=None):
        self.db = db_connection
        # 활성 종목을 관리하는 딕셔너리 (진입강도 70% 이상)
        self.active_stocks = {}
        
        # 10분 지연(Caching) 로직을 위한 TTLCache 설정
        # 최대 1000개 종목 수용, TTL은 600초(10분)
        self.fade_out_cache = TTLCache(maxsize=1000, ttl=600)
        
        # DB 동기화를 위해 수동으로 만료 시간을 트래킹하는 보조 딕셔너리 (필요시 사용)
        self.fade_out_timestamps = {}

    def calculate_entry_strength(self, real_time_data: dict) -> float:
        """
        [목업] 실시간 데이터를 바탕으로 진입강도를 계산 (0~100%)
        """
        try:
            # KeyError, ValueError 등을 방지하기 위한 안전한 데이터 파싱
            volume = float(real_time_data.get('volume', 0))
            price_change_rate = float(real_time_data.get('change_rate', 0.0))
            power = float(real_time_data.get('power', 0.0)) # 체결강도 등
            
            # 단순화된 가상의 진입강도 산출 로직
            base_score = (price_change_rate * 3) + (power * 0.5) + (volume / 100000)
            strength = min(max(base_score, 0.0), 100.0)
            
            return round(strength, 2)

        except (ValueError, TypeError) as e:
            logger.error(f"진입강도 계산 중 데이터 타입 에러 발생: {e} | 데이터: {real_time_data}")
            return 0.0
        except Exception as e:
            logger.error(f"진입강도 계산 중 알 수 없는 에러 발생: {e}")
            return 0.0

    def process_realtime_tick(self, stock_code: str, tick_data: dict):
        """
        실시간 틱 데이터가 들어올 때마다 호출되는 메인 파이프라인
        """
        if not stock_code or not isinstance(tick_data, dict):
            logger.warning(f"잘못된 형식의 틱 데이터 수신. stock_code: {stock_code}")
            return

        try:
            # 1. 진입강도 계산
            strength = self.calculate_entry_strength(tick_data)
            tick_data['strength'] = strength

            # 2. 조건 만족 판별 및 상태 전이
            if strength >= 70.0:
                self._handle_active_state(stock_code, tick_data, strength)
            else:
                self._handle_fade_out_state(stock_code, strength)

        except KeyError as e:
            logger.error(f"[{stock_code}] 틱 데이터 파싱 중 필수 키 누락: {e}")
        except Exception as e:
            logger.error(f"[{stock_code}] 실시간 틱 처리 중 치명적 에러 발생: {e}")

    def _handle_active_state(self, stock_code: str, data: dict, strength: float):
        """
        진입강도가 70% 이상인 '활성' 상태 종목의 처리 로직
        """
        try:
            # 기존에 10분 이탈 대기 중(CACHED)이었다면 캐시에서 즉시 복귀 (재진입)
            if stock_code in self.fade_out_cache:
                del self.fade_out_cache[stock_code]
                if stock_code in self.fade_out_timestamps:
                    del self.fade_out_timestamps[stock_code]
                logger.info(f"[{stock_code}] 진입강도 회복 ({strength}%). CACHED 해제 및 활성 상태 복귀.")
                
                # DB Status 'ACTIVE'로 업데이트 (Mock)
                if self.db:
                    pass # self.db.update_status(stock_code, 'ACTIVE')

            # 활성 상태 유지 및 데이터 업데이트
            self.active_stocks[stock_code] = data
            
            # DB 실시간 Insert / Update (Mock)
            if self.db:
                pass # self.db.upsert_stock_data(stock_code, data)
                
        except Exception as e:
            logger.error(f"[{stock_code}] 활성 상태 처리 중 에러: {e}")

    def _handle_fade_out_state(self, stock_code: str, strength: float):
        """
        진입강도가 70% 미만으로 떨어진 '조건식 이탈 대기' 상태 종목의 처리 로직
        """
        try:
            # 활성 목록에 있었다면 제거
            if stock_code in self.active_stocks:
                del self.active_stocks[stock_code]
                logger.info(f"[{stock_code}] 진입강도 하락 ({strength}%). 조건식 이탈, 10분 카운트다운 시작.")

            # 이미 캐시에 들어있지 않다면 신규 캐싱 처리
            if stock_code not in self.fade_out_cache:
                current_time = time.time()
                # TTLCache에 등록 (10분 후 자동 접근 불가)
                self.fade_out_cache[stock_code] = current_time
                # 백그라운드 DB 삭제 루프를 위한 타임스탬프 기록
                self.fade_out_timestamps[stock_code] = current_time
                
                # DB Status를 즉시 삭제하지 않고 'CACHED'로 업데이트 (Mock)
                if self.db:
                    pass # self.db.update_status(stock_code, 'CACHED')
                    
        except Exception as e:
            logger.error(f"[{stock_code}] 이탈 대기 상태 처리 중 에러: {e}")

    def run_db_cleanup_loop(self):
        """
        주기적으로(예: 1분마다) 호출되어 10분이 지나 완전히 만료된 종목을 DB에서 최종 삭제하는 루프
        """
        try:
            current_time = time.time()
            expired_codes = []

            for code, cached_time in list(self.fade_out_timestamps.items()):
                # 600초(10분) 경과 체크
                if current_time - cached_time >= 600:
                    expired_codes.append(code)

            for code in expired_codes:
                logger.info(f"[{code}] 10분 지연 이탈 시간 초과. DB에서 영구 삭제 진행.")
                # DB Delete (Mock)
                if self.db:
                    pass # self.db.delete_stock(code)
                
                # 타임스탬프 정리 (TTLCache에서는 이미 알아서 만료되어 삭제됨)
                del self.fade_out_timestamps[code]

        except Exception as e:
            logger.error(f"DB 정리 루프 실행 중 에러 발생: {e}")

