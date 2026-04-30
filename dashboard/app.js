// 이제 복잡한 숫자 IP 대신 이 주소를 사용합니다!
const API_BASE_URL = "http://stockai.mooo.com:8000";

document.addEventListener('DOMContentLoaded', () => {
    fetchData(); // 최초 데이터 로드

    // 새로고침 버튼 이벤트
    document.getElementById('refresh-btn').addEventListener('click', (e) => {
        const icon = e.currentTarget.querySelector('i');
        icon.classList.add('fa-spin');
        fetchData().finally(() => {
            setTimeout(() => icon.classList.remove('fa-spin'), 500);
        });
    });

    // DB Status 상시 체크 강화 (5초마다 갱신)
    setInterval(fetchStats, 5000);
    
    // 종목 리스트 자동 갱신 (15초마다)
    setInterval(fetchTargets, 15000);
});

async function fetchData() {
    try {
        await Promise.all([
            fetchStats(),
            fetchTargets()
        ]);
    } catch (error) {
        console.error("데이터 로드 실패:", error);
    }
}

async function fetchStats() {
    try {
        // 수정됨: API_BASE_URL 사용
        const response = await fetch(`${API_BASE_URL}/api/stats`);
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();
        
        document.getElementById('stat-today-count').textContent = data.today_targets;
        document.getElementById('stat-top-strategy').textContent = data.top_strategy;
        document.getElementById('stat-db-status').textContent = data.status;
        
        if (data.status === 'Active') {
            document.getElementById('stat-db-status').style.color = '#22c55e'; // 초록색 직접 지정
        } else {
            document.getElementById('stat-db-status').style.color = '#ef4444'; // 빨간색 직접 지정
        }
    } catch (error) {
        console.error("Stats 에러:", error);
        document.getElementById('stat-db-status').textContent = 'Disconnected';
        document.getElementById('stat-db-status').style.color = '#ef4444';
    }
}

async function fetchTargets() {
    try {
        // 수정됨: API_BASE_URL 사용
        const response = await fetch(`${API_BASE_URL}/api/targets`);
        if (!response.ok) throw new Error('Network response was not ok');
        const targets = await response.json();
        
        const tbody = document.getElementById('targets-tbody');
        tbody.innerHTML = '';
        
        if (targets.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: #94a3b8;">No target signals yet.</td></tr>`;
            return;
        }

        targets.forEach(target => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${target.detect_time}</td>
                <td style="font-weight: 600;">${target.symbol_code}</td>
                <td>${target.symbol_name}</td>
                <td><span class="strategy-badge">${target.strategy_code}</span></td>
                <td class="price-text">₩${target.detect_price.toLocaleString()}</td>
                <td style="color: #94a3b8; font-size: 0.85rem;">${target.notes}</td>
                <td><button class="action-btn" onclick="viewChart('${target.symbol_code}')">Chart</button></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error("Targets 에러:", error);
        const tbody = document.getElementById('targets-tbody');
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: #ef4444;">Failed to load targets. Check API connection.</td></tr>`;
    }
}

// 차트 보기 (네이버 증권 연결로 업그레이드!)
function viewChart(code) {
    const url = `https://finance.naver.com/item/main.naver?code=${code}`;
    window.open(url, '_blank');
}