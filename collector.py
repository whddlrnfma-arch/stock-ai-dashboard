import sys
import time
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QTimer
from strategy import Indicators, StrategyEvaluator, insert_target

class KiwoomCollector(QMainWindow):
    def __init__(self):
        super().__init__()
        self.kiwoom = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        self.kiwoom.OnEventConnect.connect(self.on_event_connect)
        self.kiwoom.OnReceiveTrData.connect(self.on_receive_tr_data)
        
        # 키움 로그인 창 띄우기
        self.kiwoom.dynamicCall("CommConnect()")
        
        self.evaluator = StrategyEvaluator()
        self.stock_list = []
        self.current_idx = 0
        self.is_running = False
        
        # 15분(900,000ms)마다 전 종목 스캔을 실행하는 타이머
        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self.start_scan)
        
    def on_event_connect(self, err_code):
        if err_code == 0:
            print("===================================")
            print("키움 OpenAPI 로그인 성공!")
            print("===================================")
            self.stock_list = self.get_stock_list()
            print(f"총 스캔 대상 종목 수: {len(self.stock_list)}개")
            
            # 로그인 직후 1회 스캔 시작, 이후 15분마다 반복
            self.start_scan()
            self.scan_timer.start(15 * 60 * 1000)
        else:
            print(f"키움 API 연결 실패 (에러코드: {err_code})")
            
    def get_stock_list(self):
        # 0: 코스피, 10: 코스닥
        kospi = self.kiwoom.dynamicCall("GetCodeListByMarket(QString)", ["0"]).split(';')
        kosdaq = self.kiwoom.dynamicCall("GetCodeListByMarket(QString)", ["10"]).split(';')
        # ETF 등 제외하고 순수 주식만 필터링하는 로직을 추가할 수 있습니다.
        return [code for code in (kospi + kosdaq) if code.strip() != '']
        
    def start_scan(self):
        if self.is_running:
            print("현재 스캔이 진행 중입니다. 건너뜁니다.")
            return
            
        print(f"전 종목 스캔 시작... (15분 주기)")
        self.is_running = True
        self.current_idx = 0
        self.request_next_stock()
        
    def request_next_stock(self):
        if self.current_idx >= len(self.stock_list):
            print("전 종목 스캔 완료.")
            self.is_running = False
            return
            
        code = self.stock_list[self.current_idx]
        
        # 키움 API 조회 제한 (초당 5회) 회피를 위해 0.25초 딜레이
        time.sleep(0.25)
        
        # opt10080: 주식 분봉 차트 조회 요청 (15분봉)
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "틱범위", "15")
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")
        self.kiwoom.dynamicCall("CommRqData(QString, QString, int, QString)", "opt10080_req", "opt10080", 0, "0101")
        
    def on_receive_tr_data(self, screen_no, rqname, trcode, record_name, prev_next, data_len, err_code, msg1, msg2):
        if rqname == "opt10080_req":
            code = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, record_name, 0, "종목코드").strip()
            name = self.kiwoom.dynamicCall("GetMasterCodeName(QString)", [code]).strip()
            
            rows = self.kiwoom.dynamicCall("GetRepeatCnt(QString, QString)", trcode, record_name)
            
            # 차트 데이터 추출
            closes = []
            vols = []
            for i in range(min(rows, 100)): # 최근 100개 봉만 사용
                close_price = abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, record_name, i, "현재가").strip()))
                volume = abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, record_name, i, "거래량").strip()))
                closes.append(close_price)
                vols.append(volume)
                
            # 최신이 0번 인덱스이므로, 과거->최신 순으로 리스트 뒤집기
            closes.reverse()
            vols.reverse()
            
            if len(closes) >= 20:
                # ==============================================================
                # [전략 판별 로직 적용 부분]
                # 완벽한 판별을 위해서는 일봉(opt10081) 요청도 병행해야 합니다.
                # 예시로 15분봉 데이터만으로 A-1 전략 조건을 단순화하여 테스트합니다.
                # ==============================================================
                sma5 = Indicators.sma(closes, 5)
                current_price = closes[-1]
                
                # A-1 주도주 5일선 눌림목 간소화 테스트 (실제 일봉 거래량 등은 임의 값(True) 처리)
                if self.evaluator.evaluate_a1(current_price, sma5[-1], vols[-1], vols[-2] if len(vols)>1 else 1, True, True):
                    print(f"🔥 타점 포착: [{code}] {name} (전략: A-1)")
                    insert_target(code, name, "A-1", current_price, "15분봉 기반 A-1 포착")
                    
                # B-1 엔벨로프 낙폭 과대 테스트
                env_upper, env_lower = Indicators.envelope(closes, 20, 20)
                if self.evaluator.evaluate_b1(current_price, env_lower[-1]):
                    print(f"🔥 타점 포착: [{code}] {name} (전략: B-1)")
                    insert_target(code, name, "B-1", current_price, "엔벨로프 하단 터치")

            # 다음 종목 요청
            self.current_idx += 1
            self.request_next_stock()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    collector = KiwoomCollector()
    sys.exit(app.exec_())
