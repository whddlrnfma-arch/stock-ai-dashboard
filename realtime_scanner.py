import sys
import time
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtWidgets import QApplication

# 파이썬 실행을 위한 기본 세팅
app = QApplication(sys.argv)

class KiwoomDirectScanner:
    def __init__(self):
        self.ocx = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        self.ocx.OnEventConnect.connect(self._handler_login)
        self.ocx.OnReceiveTrData.connect(self._handler_tr_data)
        
        self.login_event_loop = None
        self.tr_event_loop = None
        self.received_data = []

        print("🚀 [집B PC] 키움 엔진 직접 가동...")
        self.login()

    def login(self):
        self.ocx.dynamicCall("CommConnect()")
        self.login_event_loop = time.time() # 루프 생성 대신 간단한 대기 처리 가능하나, 
        # 실제로는 아래처럼 이벤트 루프를 쓰는 게 정확합니다.
        from PyQt5.QtCore import QEventLoop
        self.login_event_loop = QEventLoop()
        self.login_event_loop.exec_()

    def _handler_login(self, err_code):
        if err_code == 0: print("✅ 키움 서버 접속 성공!")
        self.login_event_loop.exit()

    def get_ohlcv(self, code, interval="15"):
        self.received_data = []
        # opt10080: 주식분봉차트조회
        self.ocx.dynamicCall("SetInputValue(K_ARG, V_ARG)", "종목코드", code)
        self.ocx.dynamicCall("SetInputValue(K_ARG, V_ARG)", "틱범위", interval)
        self.ocx.dynamicCall("SetInputValue(K_ARG, V_ARG)", "수정주가구분", "1")
        
        self.tr_event_loop = time.current_loop = None
        from PyQt5.QtCore import QEventLoop
        self.tr_event_loop = QEventLoop()
        self.ocx.dynamicCall("CommRqData(S_RQNAME, S_TRCODE, N_PREVNEXT, S_SCREENNO)", 
                             "분봉조회", "opt10080", 0, "0101")
        self.tr_event_loop.exec_()
        return self.received_data

    def _handler_tr_data(self, screen_no, rqname, trcode, record_name, prev_next):
        if rqname == "분봉조회":
            count = self.ocx.dynamicCall("GetRepeatCnt(S_TRCODE, S_RECORDNAME)", trcode, record_name)
            for i in range(min(count, 100)): # 최근 100개의 분봉만 가져옴
                close = abs(int(self.ocx.dynamicCall("GetCommData(S_TRCODE, S_RECORDNAME, N_INDEX, S_ITEMNAME)", trcode, record_name, i, "현재가").strip()))
                high = abs(int(self.ocx.dynamicCall("GetCommData(S_TRCODE, S_RECORDNAME, N_INDEX, S_ITEMNAME)", trcode, record_name, i, "고가").strip()))
                low = abs(int(self.ocx.dynamicCall("GetCommData(S_TRCODE, S_RECORDNAME, N_INDEX, S_ITEMNAME)", trcode, record_name, i, "저가").strip()))
                self.received_data.append({'close': close, 'high': high, 'low': low})
            self.tr_event_loop.exit()

    def calculate_indicators(self, data):
        # 과거 데이터 순으로 뒤집기
        closes = [x['close'] for x in data][::-1]
        highs = [x['high'] for x in data][::-1]
        lows = [x['low'] for x in data][::-1]

        if len(closes) < 20: return 50, 50, 50

        # 1. RSI 9 계산
        period = 9
        deltas = [closes[i+1] - closes[i] for i in range(len(closes)-1)]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        rsi = 100 - (100 / (1 + (avg_gain / avg_loss))) if avg_loss != 0 else 100

        # 2. Stochastic Slow (5, 3, 3) 계산
        n, m, t = 5, 3, 3
        k_values = []
        for i in range(len(closes)-(m+t), len(closes)):
            hh, ll = max(highs[i-n+1:i+1]), min(lows[i-n+1:i+1])
            k = ((closes[i] - ll) / (hh - ll)) * 100 if hh != ll else 50
            k_values.append(k)
        slow_k = sum(k_values[-m:]) / m
        slow_d = sum(k_values[-t:]) / t

        return rsi, slow_k, slow_d

    def start_monitoring(self):
        # 코스피 상위 종목 리스트 가져오기 (직접 호출)
        all_codes = self.ocx.dynamicCall("GetCodeListByMarket(S_MARKET)", "0").split(';')[:30]
        
        while True:
            print(f"\n🔍 [스캔 시작] 대상: {len(all_codes)}개 종목 | 시간: {time.strftime('%H:%M:%S')}")
            for code in all_codes:
                if not code: continue
                name = self.ocx.dynamicCall("GetMasterCodeName(S_CODE)", code)
                data = self.get_ohlcv(code)
                
                if data:
                    rsi, k, d = self.calculate_indicators(data)
                    
                    # 타점 출력 로직
                    status = "측정중"
                    if rsi <= 30 and k > d:
                        status = "🔥 [매수타점] !!"
                        print(f"{status} {name}({code}) - RSI: {rsi:.1f}, K: {k:.1f}, D: {d:.1f}")
                    else:
                        # 감시 중임을 알리기 위해 점만 찍거나 요약 출력
                        print(f"watching: {name} (RSI:{rsi:.1f})", end='\r')
                
                time.sleep(0.3) # 조회 제한 방지
            
            print(f"\n☕ 스캔 완료. 15분 대기 후 {time.strftime('%H:%M:%S')}에 다시 시작합니다.")
            time.sleep(900)

if __name__ == "__main__":
    scanner = KiwoomDirectScanner()
    scanner.start_monitoring()
