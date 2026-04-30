import sys
import time
import oracledb
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QAxContainer import QAxWidget

class RateLimiter:
    """조회 제한 방지를 위한 Rate Limiter"""
    def __init__(self, delay=0.2):
        self.delay = delay
        self.last_req_time = 0.0

    def wait(self):
        elapsed = time.time() - self.last_req_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_req_time = time.time()

class KiwoomLogic(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 키움 API OCX 연결
        self.kiwoom = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        self.kiwoom.OnEventConnect.connect(self.on_event_connect)
        self.kiwoom.OnReceiveRealData.connect(self.on_receive_real_data)
        
        self.rate_limiter = RateLimiter(0.2)
        
        # 오라클 DB Connection Pool 설정
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        db_ip = os.getenv("DB_IP", "127.0.0.1")
        db_port = int(os.getenv("DB_PORT", "1521"))
        db_sid = os.getenv("DB_SID", "XE")
        db_user = os.getenv("DB_USER", "system")
        db_pass = os.getenv("DB_PASS")

        self.dsn = oracledb.makedsn(db_ip, db_port, sid=db_sid)
        self.pool = oracledb.create_pool(
            user=db_user,
            password=db_pass,
            dsn=self.dsn,
            min=2,
            max=10,
            increment=1
        )
        print("✅ Oracle DB Connection Pool 생성 완료")
        
        # 키움 로그인 창 띄우기
        print("키움 OpenAPI 로그인 시도 중...")
        self.kiwoom.dynamicCall("CommConnect()")

    def on_event_connect(self, err_code):
        if err_code == 0:
            print("✅ 키움 OpenAPI 로그인 성공!")
            self.start_realtime_monitoring()
        else:
            print(f"❌ 키움 API 연결 실패 (에러코드: {err_code})")
            
    def get_stock_list(self):
        # 0: 코스피, 10: 코스닥
        kospi = self.kiwoom.dynamicCall("GetCodeListByMarket(QString)", ["0"]).split(';')
        kosdaq = self.kiwoom.dynamicCall("GetCodeListByMarket(QString)", ["10"]).split(';')
        return [code for code in (kospi + kosdaq) if code.strip() != '']
        
    def start_realtime_monitoring(self):
        print("전 종목 정보 로딩 중...")
        self.rate_limiter.wait()
        stock_list = self.get_stock_list()
        print(f"총 실시간 감시 대상 종목 수: {len(stock_list)}개")
        
        # 100개씩 나눠서 SetRealReg(실시간 등록) 수행
        chunk_size = 100
        for i in range(0, len(stock_list), chunk_size):
            chunk = stock_list[i:i+chunk_size]
            code_list_str = ";".join(chunk)
            screen_no = str(1000 + (i // chunk_size))
            
            self.rate_limiter.wait()
            # 실시간 등록 (FID: 10=현재가, 12=등락율, 20=체결시간)
            # 최초 등록(i==0)은 '0', 이후 등록은 '1'(추가 등록)
            opt_type = "0" if i == 0 else "1"
            res = self.kiwoom.dynamicCall(
                "SetRealReg(QString, QString, QString, QString)", 
                screen_no, code_list_str, "10;12;20", opt_type
            )
            
        print("🚀 전 종목 실시간 시세 수신 등록 완료!")

    def on_receive_real_data(self, code, real_type, real_data):
        if real_type == "주식체결":
            # GetCommRealData로 데이터 추출
            price_str = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", code, 10).strip()
            change_rate_str = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", code, 12).strip()
            
            if not price_str:
                return
                
            price = abs(int(price_str))
            
            # DB 부하를 줄이기 위해 로컬 딕셔너리로 관리하는 방법도 있으나,
            # '수신된 데이터를 오라클 DB에 즉시 업데이트' 요구사항에 맞춰 바로 UPSERT
            name = self.kiwoom.dynamicCall("GetMasterCodeName(QString)", [code]).strip()
            notes = f"등락률: {change_rate_str}%"
            
            self.update_db(code, name, price, notes)
            
    def update_db(self, code, name, price, notes):
        try:
            with self.pool.acquire() as conn:
                with conn.cursor() as cursor:
                    # MERGE INTO를 사용해 종목코드가 있으면 UPDATE, 없으면 INSERT (UPSERT)
                    sql = """
                    MERGE INTO TRADING_TARGETS t
                    USING (SELECT :1 AS code FROM dual) s
                    ON (t.SYMBOL_CODE = s.code)
                    WHEN MATCHED THEN
                        UPDATE SET 
                            DETECT_TIME = SYSTIMESTAMP,
                            DETECT_PRICE = :2,
                            NOTES = :3,
                            SYMBOL_NAME = :4,
                            STRATEGY_CODE = 'REALTIME'
                    WHEN NOT MATCHED THEN
                        INSERT (SYMBOL_CODE, SYMBOL_NAME, STRATEGY_CODE, DETECT_PRICE, NOTES)
                        VALUES (:1, :4, 'REALTIME', :2, :3)
                    """
                    cursor.execute(sql, (code, price, notes, name))
                conn.commit()
        except Exception as e:
            print(f"❌ DB Update Error ({code} {name}): {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    logic = KiwoomLogic()
    sys.exit(app.exec_())
