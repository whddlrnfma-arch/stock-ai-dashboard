import asyncio
import math
import logging
import time
from typing import List, Tuple, Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime

# 기존 TTLCache 로직 연동을 위해 임포트 (kiwoom_logic 모듈 존재 가정)
try:
    from kiwoom_logic import KiwoomLogic
except ImportError:
    KiwoomLogic = None

logger = logging.getLogger("StrategyEngine")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(ch)

# =====================================================================
# 1. Pydantic Models
# =====================================================================
class DetectionResult(BaseModel):
    stock_code: str
    stock_name: str
    strategy_name: str
    entry_strength: float = Field(..., ge=0.0, le=100.0)
    detected_price: int
    detected_at: datetime


# =====================================================================
# 2. Indicator Module (No Pandas/Numpy)
# =====================================================================
class Indicators:
    """
    pandas 없이 순수 파이썬 리스트 연산으로 기술적 지표를 계산하는 헬퍼 클래스.
    가장 과거가 인덱스 0, 가장 최근이 마지막 인덱스로 가정합니다.
    """
    @staticmethod
    def sma(data: List[float], period: int) -> List[Optional[float]]:
        result = [None] * len(data)
        for i in range(period - 1, len(data)):
            window = data[i - period + 1 : i + 1]
            result[i] = sum(window) / period
        return result

    @staticmethod
    def ema(data: List[float], period: int) -> List[Optional[float]]:
        result = [None] * len(data)
        if len(data) < period:
            return result
        
        sma_val = sum(data[:period]) / period
        result[period - 1] = sma_val
        
        k = 2 / (period + 1)
        for i in range(period, len(data)):
            result[i] = (data[i] - result[i - 1]) * k + result[i - 1]
        return result

    @staticmethod
    def stdev(data: List[float], period: int) -> List[Optional[float]]:
        result = [None] * len(data)
        for i in range(period - 1, len(data)):
            window = data[i - period + 1 : i + 1]
            mean = sum(window) / period
            variance = sum((x - mean) ** 2 for x in window) / period
            result[i] = math.sqrt(variance)
        return result

    @staticmethod
    def bollinger_bands(data: List[float], period: int = 20, multiplier: int = 2):
        smas = Indicators.sma(data, period)
        stdevs = Indicators.stdev(data, period)
        upper = [None] * len(data)
        lower = [None] * len(data)
        
        for i in range(len(data)):
            if smas[i] is not None and stdevs[i] is not None:
                upper[i] = smas[i] + multiplier * stdevs[i]
                lower[i] = smas[i] - multiplier * stdevs[i]
        return smas, upper, lower

    @staticmethod
    def rsi(data: List[float], period: int = 9) -> List[Optional[float]]:
        result = [None] * len(data)
        if len(data) < period + 1:
            return result
            
        gains, losses = [], []
        for i in range(1, period + 1):
            change = data[i] - data[i-1]
            gains.append(change if change > 0 else 0)
            losses.append(abs(change) if change < 0 else 0)
            
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            result[period] = 100
        else:
            rs = avg_gain / avg_loss
            result[period] = 100 - (100 / (1 + rs))
            
        for i in range(period + 1, len(data)):
            change = data[i] - data[i-1]
            gain = change if change > 0 else 0
            loss = abs(change) if change < 0 else 0
            
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
            
            if avg_loss == 0:
                result[i] = 100
            else:
                rs = avg_gain / avg_loss
                result[i] = 100 - (100 / (1 + rs))
        return result

    @staticmethod
    def stochastic_slow(highs: List[float], lows: List[float], closes: List[float], n: int = 5, m: int = 3, t: int = 3):
        fast_k = [None] * len(closes)
        for i in range(n - 1, len(closes)):
            window_high = max(highs[i - n + 1 : i + 1])
            window_low = min(lows[i - n + 1 : i + 1])
            if window_high == window_low:
                fast_k[i] = 50
            else:
                fast_k[i] = (closes[i] - window_low) / (window_high - window_low) * 100
                
        valid_indices = [i for i, v in enumerate(fast_k) if v is not None]
        slow_k = [None] * len(closes)
        if len(valid_indices) >= m:
            valid_fast_k = [fast_k[i] for i in valid_indices]
            sma_fast_k = Indicators.sma(valid_fast_k, m)
            for j, val in enumerate(sma_fast_k):
                slow_k[valid_indices[j]] = val

        valid_indices_d = [i for i, v in enumerate(slow_k) if v is not None]
        slow_d = [None] * len(closes)
        if len(valid_indices_d) >= t:
            valid_slow_k = [slow_k[i] for i in valid_indices_d]
            sma_slow_k = Indicators.sma(valid_slow_k, t)
            for j, val in enumerate(sma_slow_k):
                slow_d[valid_indices_d[j]] = val

        return slow_k, slow_d

    @staticmethod
    def envelope(data: List[float], period: int = 20, percent: float = 20.0):
        smas = Indicators.sma(data, period)
        upper = [None] * len(data)
        lower = [None] * len(data)
        for i in range(len(data)):
            if smas[i] is not None:
                upper[i] = smas[i] * (1 + percent / 100)
                lower[i] = smas[i] * (1 - percent / 100)
        return upper, lower

    @staticmethod
    def macd(data: List[float], short_period: int = 12, long_period: int = 26, signal_period: int = 9):
        short_ema = Indicators.ema(data, short_period)
        long_ema = Indicators.ema(data, long_period)
        
        macd_line = [None] * len(data)
        for i in range(len(data)):
            if short_ema[i] is not None and long_ema[i] is not None:
                macd_line[i] = short_ema[i] - long_ema[i]
                
        valid_indices = [i for i, v in enumerate(macd_line) if v is not None]
        signal_line = [None] * len(data)
        if len(valid_indices) >= signal_period:
            valid_macd = [macd_line[i] for i in valid_indices]
            ema_macd = Indicators.ema(valid_macd, signal_period)
            for j, val in enumerate(ema_macd):
                signal_line[valid_indices[j]] = val

        return macd_line, signal_line


# =====================================================================
# 3. Strategy Evaluator
# =====================================================================
class StrategyEvaluator:
    """
    각 전략별 매수 조건을 평가하고, 조건식 일치율에 따라 0~100점의 진입강도(entry_strength)를 반환.
    """
    def evaluate_a1(self, current_price_15m, sma_5d, volume_1d, prev_volume_1d, is_top_30_value, has_15pct_bull_candle) -> Optional[Tuple[str, float]]:
        name = "주도주 첫 눌림목"
        if not (is_top_30_value and has_15pct_bull_candle):
            return None
        if sma_5d is None:
            return None
            
        diff_pct = abs(current_price_15m - sma_5d) / sma_5d * 100
        # 5일선 정확히 터치(0% 오차) = 100점, 2% 오차 = 70점. 15배수 차감.
        strength = 100.0 - (diff_pct * 15.0)
        
        # 거래량 전일 대비 50% 이하 검증 (불만족시 강도 대폭 감소)
        if volume_1d > prev_volume_1d * 0.5:
            strength -= 40
            
        return name, max(0.0, min(100.0, strength))

    def evaluate_a2(self, bb_upper_1d_list, bb_lower_1d_list, current_price_15m, vol_15m, prev_5_vols_15m, bb_upper_15m) -> Optional[Tuple[str, float]]:
        name = "볼린저 밴드 돌파"
        if not bb_upper_1d_list or not bb_lower_1d_list or len(bb_upper_1d_list) < 20:
            return None
            
        widths = [u - l for u, l in zip(bb_upper_1d_list[-20:], bb_lower_1d_list[-20:]) if u is not None and l is not None]
        if not widths or widths[-1] > min(widths) * 1.05: # Squeeze 허용 오차 5% 이내
            return None
            
        if bb_upper_15m is None or current_price_15m <= bb_upper_15m:
            return None
            
        if not prev_5_vols_15m:
            return None
            
        avg_vol = sum(prev_5_vols_15m) / len(prev_5_vols_15m)
        if avg_vol == 0:
            return None
            
        vol_ratio = (vol_15m / avg_vol) * 100
        # 500% 이상 = 100점, 300% = 70점
        strength = 70 + (vol_ratio - 300) * (30.0 / 200.0)
        
        return name, max(0.0, min(100.0, strength))

    def evaluate_a3(self, rsi_9, slow_k_prev, slow_d_prev, slow_k_curr, slow_d_curr, open_price_1d, prev_close_1d) -> Optional[Tuple[str, float]]:
        name = "과매도 반등 콤보"
        if any(v is None for v in [rsi_9, slow_k_prev, slow_d_prev, slow_k_curr, slow_d_curr]):
            return None
            
        if open_price_1d <= prev_close_1d * 0.97:
            return None
            
        if not (slow_k_prev <= slow_d_prev and slow_k_curr > slow_d_curr):
            return None
            
        # RSI 20 이하 = 100점, 30 = 70점
        strength = 100.0 - (rsi_9 - 20.0) * 3.0
        
        return name, max(0.0, min(100.0, strength))

    def evaluate_b1(self, current_price, env_lower) -> Optional[Tuple[str, float]]:
        name = "엔벨로프 낙폭 과대"
        if env_lower is None:
            return None
            
        diff_pct = (env_lower - current_price) / env_lower * 100
        
        if diff_pct < 0:
            # 하단선 위쪽 (이탈 안함)
            strength = 70 - abs(diff_pct) * 10
        else:
            # 하단선 이탈 완료 (5% 이탈 시 100점)
            strength = 70 + (diff_pct / 5.0) * 30
            
        return name, max(0.0, min(100.0, strength))

    def evaluate_b2(self, current_price, prev_price, sma_20d_curr, sma_20d_prev, slow_k_curr=None) -> Optional[Tuple[str, float]]:
        name = "20일선 N자형 눌림목"
        if sma_20d_curr is None or sma_20d_prev is None:
            return None
            
        if sma_20d_curr <= sma_20d_prev:
            return None # 우상향이 아님
            
        diff_pct = abs(current_price - sma_20d_curr) / sma_20d_curr * 100
        # 0% 일치 시 100점, 1% 오차 시 70점
        strength = 100.0 - (diff_pct * 30.0)
        
        # 재진입(이탈 후 돌파) 보너스
        if prev_price < sma_20d_prev and current_price >= sma_20d_curr:
            strength += 10
            
        if slow_k_curr is not None and slow_k_curr <= 20:
            strength += 10
            
        return name, max(0.0, min(100.0, strength))

    def evaluate_b3(self, macd_prev, macd_curr, vol_1d_curr, vol_1d_prev, current_close, open_price) -> Optional[Tuple[str, float]]:
        name = "MACD 영선 돌파"
        if macd_prev is None or macd_curr is None:
            return None
            
        if not (macd_prev <= 0 and macd_curr > 0):
            return None
            
        if current_close <= open_price:
            return None
            
        if vol_1d_prev == 0:
            return None
            
        vol_ratio = (vol_1d_curr / vol_1d_prev) * 100
        # 100% 동일하면 70미만(40점), 200% 증가시 100점
        strength = 40.0 + (vol_ratio - 100.0) * 0.6
        
        return name, max(0.0, min(100.0, strength))


# =====================================================================
# 4. Detection Logic & Data Pipeline
# =====================================================================
class StrategyEngine:
    def __init__(self, kiwoom_logic=None):
        # 만약 kiwoom_logic 인스턴스가 주입되지 않았다면 새로 생성 (의존성 주입)
        self.kiwoom_logic = kiwoom_logic if kiwoom_logic else (KiwoomLogic() if KiwoomLogic else None)
        self.evaluator = StrategyEvaluator()

    async def run_15min_scanner_loop(self):
        """
        15분 단위로 구동되는 비동기 스캐너 루프.
        """
        logger.info("실시간 퀀트 전략 엔진(15분 스캐너) 시작...")
        while True:
            logger.info("15분봉 완성 확인 - 전 종목 대상 검사 스캔 중...")
            
            # TODO: 실제 DB나 Open API를 통해 전 종목 데이터 Fetch
            # 여기서는 예시용 목업 리스트를 사용
            mock_stock_list = [
                {"code": "005930", "name": "삼성전자"},
                {"code": "000660", "name": "SK하이닉스"}
            ]
            
            for stock in mock_stock_list:
                result = await self._scan_stock(stock["code"], stock["name"])
                if result:
                    self._handle_detection(result)
            
            logger.info("전 종목 스캔 완료. 다음 15분봉까지 대기.")
            # 실제 운영 환경에서는 다음 15분 단위(예: 00분, 15분, 30분, 45분) 정각까지 대기하는 로직 권장
            await asyncio.sleep(15 * 60)

    async def _scan_stock(self, code: str, name: str) -> Optional[DetectionResult]:
        """
        특정 종목의 지표를 계산하고 전략 평가 함수들을 호출
        """
        # (예시) 실제 데이터가 들어왔다고 가정하고 가상의 A-1 전략 통과 케이스를 리턴
        # 실제 구현에서는 Indicators 클래스를 활용하여 지표를 먼저 계산한 후 evaluator에 전달합니다.
        
        # ... fetch data ...
        # ... compute indicators ...
        
        # 목업 로직 (테스트용)
        if code == "005930":
            # 삼성전자가 '볼린저 밴드 돌파' 전략에 포착되었고 진입강도가 85점이라고 가정
            strategy_name = "볼린저 밴드 돌파"
            strength = 85.0
            price = 78400
            
            return DetectionResult(
                stock_code=code,
                stock_name=name,
                strategy_name=strategy_name,
                entry_strength=strength,
                detected_price=price,
                detected_at=datetime.now()
            )
        elif code == "000660":
            # SK하이닉스가 '엔벨로프 낙폭 과대'에 포착되었으나 강도가 65점이라고 가정
            strategy_name = "엔벨로프 낙폭 과대"
            strength = 65.0
            price = 195500
            
            return DetectionResult(
                stock_code=code,
                stock_name=name,
                strategy_name=strategy_name,
                entry_strength=strength,
                detected_price=price,
                detected_at=datetime.now()
            )
        return None

    def _handle_detection(self, result: DetectionResult):
        """
        포착된 종목의 진입강도에 따라 파이프라인(활성 상태 유지 vs 10분 지연 캐싱) 분기
        """
        logger.info(f"[{result.stock_code}] {result.strategy_name} 조건 부합. 진입강도: {result.entry_strength:.1f}%")
        
        if self.kiwoom_logic:
            tick_data = {
                'price': result.detected_price,
                'strategy_name': result.strategy_name,
                'strength': result.entry_strength
            }
            
            # 진입강도가 70 미만이면 이탈한 것으로 간주해 TTLCache 로직으로 넘김
            if result.entry_strength >= 70.0:
                logger.info(f" -> 강도 70 이상: 활성 파이프라인 진입")
                self.kiwoom_logic._handle_active_state(result.stock_code, tick_data, result.entry_strength)
            else:
                logger.info(f" -> 강도 70 미만: 이탈 간주 및 10분 캐싱(TTLCache) 이관")
                self.kiwoom_logic._handle_fade_out_state(result.stock_code, result.entry_strength)
        else:
            logger.warning("KiwoomLogic 객체가 연결되지 않아 상태 전이를 수행할 수 없습니다.")

# =====================================================================
# 테스트 실행부
# =====================================================================
if __name__ == "__main__":
    engine = StrategyEngine()
    
    # 단일 실행 테스트
    async def run_test():
        # 스캐너 루프를 백그라운드 태스크로 실행하고 3초 후 종료 (테스트용)
        task = asyncio.create_task(engine.run_15min_scanner_loop())
        await asyncio.sleep(3)
        task.cancel()
        
    asyncio.run(run_test())
