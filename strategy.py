import oracledb
import oracledb as cx_Oracle  # 구형 코드와의 호환성을 위해 이름을 별칭으로 지정
import math
from datetime import datetime

# Oracle DB 연결을 위한 라이브러리.
# 집B PC가 Python 3.10 (32-bit)이므로, 오라클 클라이언트 32-bit 설치 후 cx_Oracle이나 oracledb 패키지를 사용해야 합니다.

class Indicators:
    """
    pandas 없이 순수 파이썬 리스트 연산으로 기술적 지표를 계산하는 클래스
    모든 데이터는 가장 과거가 0, 가장 최근이 마지막 인덱스인 리스트로 가정합니다.
    """
    @staticmethod
    def sma(data, period):
        result = [None] * len(data)
        for i in range(period - 1, len(data)):
            window = data[i - period + 1 : i + 1]
            result[i] = sum(window) / period
        return result

    @staticmethod
    def ema(data, period):
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
    def stdev(data, period):
        result = [None] * len(data)
        for i in range(period - 1, len(data)):
            window = data[i - period + 1 : i + 1]
            mean = sum(window) / period
            variance = sum((x - mean) ** 2 for x in window) / period
            result[i] = math.sqrt(variance)
        return result

    @staticmethod
    def bollinger_bands(data, period=20, multiplier=2):
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
    def rsi(data, period=9):
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
    def stochastic_slow(highs, lows, closes, n=5, m=3, t=3):
        fast_k = [None] * len(closes)
        for i in range(n - 1, len(closes)):
            window_high = max(highs[i - n + 1 : i + 1])
            window_low = min(lows[i - n + 1 : i + 1])
            if window_high == window_low:
                fast_k[i] = 50
            else:
                fast_k[i] = (closes[i] - window_low) / (window_high - window_low) * 100
                
        # slow_k: fast_k의 m기간 SMA
        valid_indices = [i for i, v in enumerate(fast_k) if v is not None]
        slow_k = [None] * len(closes)
        if len(valid_indices) >= m:
            valid_fast_k = [fast_k[i] for i in valid_indices]
            sma_fast_k = Indicators.sma(valid_fast_k, m)
            for j, val in enumerate(sma_fast_k):
                slow_k[valid_indices[j]] = val

        # slow_d: slow_k의 t기간 SMA
        valid_indices_d = [i for i, v in enumerate(slow_k) if v is not None]
        slow_d = [None] * len(closes)
        if len(valid_indices_d) >= t:
            valid_slow_k = [slow_k[i] for i in valid_indices_d]
            sma_slow_k = Indicators.sma(valid_slow_k, t)
            for j, val in enumerate(sma_slow_k):
                slow_d[valid_indices_d[j]] = val

        return slow_k, slow_d

    @staticmethod
    def envelope(data, period=20, percent=20):
        smas = Indicators.sma(data, period)
        upper = [None] * len(data)
        lower = [None] * len(data)
        for i in range(len(data)):
            if smas[i] is not None:
                upper[i] = smas[i] * (1 + percent / 100)
                lower[i] = smas[i] * (1 - percent / 100)
        return upper, lower

    @staticmethod
    def macd(data, short_period=12, long_period=26, signal_period=9):
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


class StrategyEvaluator:
    """
    6가지 핵심 매매 전략을 판별하는 클래스
    """
    def __init__(self):
        pass

    def evaluate_a1(self, current_price_15m, sma_5d, volume_1d, prev_volume_1d, is_top_30_value, has_15pct_bull_candle):
        """
        전략 A-1: 주도주 5일선 첫 눌림목
        """
        if not (is_top_30_value and has_15pct_bull_candle):
            return False
            
        if sma_5d is None: return False
        
        # 5일 이동평균선에 터치 혹은 -2% 이내 근접
        if sma_5d * 0.98 <= current_price_15m <= sma_5d * 1.02:
            # 하락 시 거래량이 전일 대비 50% 이하로 급감
            if volume_1d <= prev_volume_1d * 0.5:
                return True
        return False

    def evaluate_a2(self, bb_upper_1d_list, bb_lower_1d_list, current_price_15m, vol_15m, prev_5_vols_15m, bb_upper_15m):
        """
        전략 A-2: 볼린저 밴드 변동성 돌파
        """
        if not bb_upper_1d_list or not bb_lower_1d_list or len(bb_upper_1d_list) < 20:
            return False
            
        # Squeeze: 일봉상 볼린저 밴드 폭이 최근 20일 중 최저 수준
        widths = [u - l for u, l in zip(bb_upper_1d_list[-20:], bb_lower_1d_list[-20:]) if u is not None and l is not None]
        if not widths or widths[-1] > min(widths):
            return False
            
        # 15분봉상 상단선 돌파
        if bb_upper_15m is None or current_price_15m <= bb_upper_15m:
            return False
            
        # 필터: 돌파 캔들 거래량이 직전 5개 캔들 평균의 300% 이상
        if prev_5_vols_15m:
            avg_vol = sum(prev_5_vols_15m) / len(prev_5_vols_15m)
            if vol_15m >= avg_vol * 3:
                return True
        return False

    def evaluate_a3(self, rsi_9, slow_k_prev, slow_d_prev, slow_k_curr, slow_d_curr, open_price_1d, prev_close_1d):
        """
        전략 A-3: 과매도 RSI + 스토캐스틱 콤보
        """
        if any(v is None for v in [rsi_9, slow_k_prev, slow_d_prev, slow_k_curr, slow_d_curr]):
            return False
            
        # RSI 30 이하
        if rsi_9 <= 30:
            # Stochastic 골든크로스 (%K선이 %D선 상향 돌파)
            if slow_k_prev <= slow_d_prev and slow_k_curr > slow_d_curr:
                # 당일 시가가 -3% 이하로 과도하게 밀린 종목 제외
                if open_price_1d >= prev_close_1d * 0.97:
                    return True
        return False

    def evaluate_b1(self, current_price, env_lower):
        """
        전략 B-1: 엔벨로프 낙폭 과대
        """
        if env_lower is None: return False
        if current_price <= env_lower:
            return True
        return False

    def evaluate_b2(self, current_price, prev_price, sma_20d_curr, sma_20d_prev, slow_k_curr=None):
        """
        전략 B-2: 20일선 N자형 눌림목
        """
        if sma_20d_curr is None or sma_20d_prev is None: return False
        
        # 20일선 우상향
        if sma_20d_curr > sma_20d_prev:
            # 20일선 근접 (1% 이내) 또는 이탈 후 재진입
            near_sma = sma_20d_curr * 0.99 <= current_price <= sma_20d_curr * 1.01
            break_and_reenter = (prev_price < sma_20d_prev) and (current_price >= sma_20d_curr)
            
            if near_sma or break_and_reenter:
                # 옵션: 스토캐스틱 20 이하에서 반등 시 신뢰도 가중 가능
                return True
        return False

    def evaluate_b3(self, macd_prev, macd_curr, vol_1d_curr, vol_1d_prev, current_close, open_price):
        """
        전략 B-3: MACD 영선(0-Line) 돌파
        """
        if macd_prev is None or macd_curr is None: return False
        
        # MACD가 0선을 아래에서 위로 돌파
        if macd_prev <= 0 and macd_curr > 0:
            # 거래량 증가 & 양봉 (종가가 시가보다 높음)
            if vol_1d_curr > vol_1d_prev and current_close > open_price:
                return True
        return False


def insert_target(symbol_code, symbol_name, strategy_code, detect_price, notes=""):
    """
    집A PC(서버)의 오라클 DB로 타점 포착 데이터를 전송
    """
    # 환경에 맞게 IP 및 인증 정보 수정 필요
    db_ip = "127.0.0.1"  # 로컬호스트 (집A PC)
    db_port = 1521
    db_sid = "XE"
    db_user = "system"       # DB 유저 이름
    db_pass = "dkanrjsk1!"       # DB 비밀번호
    
    try:
        dsn = cx_Oracle.makedsn(db_ip, db_port, sid=db_sid)
        connection = cx_Oracle.connect(user=db_user, password=db_pass, dsn=dsn)
        cursor = connection.cursor()
        
        sql = '''
            INSERT INTO TRADING_TARGETS 
            (SYMBOL_CODE, SYMBOL_NAME, STRATEGY_CODE, DETECT_PRICE, NOTES)
            VALUES (:1, :2, :3, :4, :5)
        '''
        cursor.execute(sql, (symbol_code, symbol_name, strategy_code, detect_price, notes))
        connection.commit()
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {symbol_name}({symbol_code}) - {strategy_code} DB 전송 완료.")
        
    except Exception as e:
        print(f"DB Insert Error: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()
