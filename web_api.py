from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import oracledb as cx_Oracle
from pydantic import BaseModel
from typing import List
import os

app = FastAPI(title="AntiGravity Stock Dashboard API")

# 1. CORS 설정: 외부 기기(스마트폰, 맥북) 접속 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. DB 접속 함수: 최신 oracledb 방식 및 Connection Pool 적용
import os
from dotenv import load_dotenv
load_dotenv()

pool = None

@app.on_event("startup")
def startup_event():
    global pool
    db_ip = os.getenv("DB_IP", "127.0.0.1")
    db_port = int(os.getenv("DB_PORT", "1521"))
    db_sid = os.getenv("DB_SID", "XE")
    db_user = os.getenv("DB_USER", "system")
    db_pass = os.getenv("DB_PASS")

    dsn = cx_Oracle.makedsn(db_ip, db_port, sid=db_sid)
    pool = cx_Oracle.create_pool(user=db_user, password=db_pass, dsn=dsn, min=2, max=10, increment=1)
    print("✅ Web API: Oracle DB Connection Pool 생성 완료")

@app.on_event("shutdown")
def shutdown_event():
    if pool:
        pool.close()
        print("✅ Web API: Oracle DB Connection Pool 종료")

def get_db_connection():
    return pool.acquire()

# 3. 데이터 모델 정의
class TargetModel(BaseModel):
    id: int
    detect_time: str
    symbol_code: str
    symbol_name: str
    strategy_code: str
    detect_price: float
    notes: str

# 4. API 경로 (화면 연결보다 위에 있어야 함)

@app.get("/api/targets", response_model=List[TargetModel])
def get_targets():
    """최근 포착 종목 리스트 100건 가져오기"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ID, TO_CHAR(DETECT_TIME, 'YYYY-MM-DD HH24:MI:SS'), 
                   SYMBOL_CODE, SYMBOL_NAME, STRATEGY_CODE, DETECT_PRICE, NOTES
            FROM TRADING_TARGETS
            ORDER BY DETECT_TIME DESC
            FETCH FIRST 100 ROWS ONLY
        """)
        rows = cursor.fetchall()
        results = [
            {
                "id": r[0], "detect_time": r[1], "symbol_code": r[2], 
                "symbol_name": r[3], "strategy_code": r[4], 
                "detect_price": float(r[5]), "notes": r[6] if r[6] else ""
            } for r in rows
        ]
        return results
    except Exception as e:
        print(f"❌ DB Fetch Error (Targets): {e}")
        return []
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.get("/api/stats")
def get_stats():
    """상단 통계 데이터 가져오기"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 오늘 포착 개수
        cursor.execute("SELECT COUNT(*) FROM TRADING_TARGETS WHERE TRUNC(DETECT_TIME) = TRUNC(SYSDATE)")
        today_count = cursor.fetchone()[0]
        
        # 최다 포착 전략
        cursor.execute("""
            SELECT STRATEGY_CODE FROM TRADING_TARGETS 
            GROUP BY STRATEGY_CODE ORDER BY COUNT(*) DESC FETCH FIRST 1 ROWS ONLY
        """)
        top_row = cursor.fetchone()
        top_strategy = top_row[0] if top_row else "N/A"
        
        return {"today_targets": today_count, "top_strategy": top_strategy, "status": "Active"}
    except Exception as e:
        print(f"❌ DB Fetch Error (Stats): {e}")
        return {"today_targets": 0, "top_strategy": "N/A", "status": "Error"}
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

# 5. 대시보드 화면(HTML) 연결 (가장 아래에 위치)

# 실행 중인 파일 위치를 기준으로 dashboard 폴더를 자동으로 찾습니다.
current_dir = os.path.dirname(os.path.abspath(__file__))
dashboard_path = os.path.join(current_dir, "dashboard")

print(f"\n--- 시스템 시작 정보 ---")
print(f"현재 파일 위치: {current_dir}")

if os.path.exists(dashboard_path):
    # 루트("/")로 접속 시 dashboard 폴더의 index.html을 보여줍니다.
    app.mount("/", StaticFiles(directory=dashboard_path, html=True), name="dashboard")
    print(f"✅ 대시보드 화면 연결 성공: {dashboard_path}")
else:
    # 자동 경로 실패 시 수동 경로 시도
    manual_path = r"C:\STOCK AI\dashboard"
    if os.path.exists(manual_path):
        app.mount("/", StaticFiles(directory=manual_path, html=True), name="dashboard")
        print(f"✅ 수동 경로로 대시보드 연결 성공: {manual_path}")
    else:
        print(f"❌ 오류: 대시보드 폴더를 찾을 수 없습니다.")
        print(f"   'dashboard' 폴더가 {current_dir} 안에 있는지 확인하세요.")
print(f"------------------------\n")
