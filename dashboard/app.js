document.addEventListener('DOMContentLoaded', () => {
    fetchData(); // 최초 데이터 로드

    // 새로고침 버튼 이벤트
    const refreshBtn = document.getElementById('btn-refresh-news');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', (e) => {
            const btn = e.currentTarget;
            btn.classList.add('spinning'); // 애니메이션 클래스 적용
            fetchData().finally(() => {
                setTimeout(() => btn.classList.remove('spinning'), 500);
            });
        });
    }

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
        // 상대 경로 사용으로 DDNS 및 내부 IP 자동 대응
        const response = await fetch(`/api/stats`);
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();
        
        const countBadge = document.getElementById('stock-count-badge');
        if (countBadge) countBadge.textContent = data.today_targets;
        
        const statActive = document.getElementById('stat-active');
        if (statActive) statActive.textContent = data.today_targets;

        const statAvgStrength = document.getElementById('stat-avg-strength');
        if (statAvgStrength) statAvgStrength.textContent = data.top_strategy;
        
        const statusLabel = document.querySelector('#system-status .status-label');
        const statusDot = document.querySelector('#system-status .status-dot');
        
        if (statusLabel) statusLabel.textContent = data.status;
        
        if (data.status === 'Active') {
            if (statusLabel) statusLabel.style.color = '#34C759'; // Apple Green
            if (statusDot) {
                statusDot.classList.add('status-dot--live');
                statusDot.classList.remove('status-dot--closed');
            }
        } else {
            if (statusLabel) statusLabel.style.color = '#FF3B30'; // Apple Red
            if (statusDot) {
                statusDot.classList.remove('status-dot--live');
                statusDot.classList.add('status-dot--closed');
            }
        }
    } catch (error) {
        console.error("Stats 에러:", error);
        const statusLabel = document.querySelector('#system-status .status-label');
        if (statusLabel) {
            statusLabel.textContent = 'Disconnected';
            statusLabel.style.color = '#FF3B30';
        }
    }
}

async function fetchTargets() {
    try {
        // 상대 경로 사용
        const response = await fetch(`/api/targets`);
        if (!response.ok) throw new Error('Network response was not ok');
        const targets = await response.json();
        
        const container = document.getElementById('stock-list-container');
        if (!container) return; // Cannot read properties of null 방지
        
        container.innerHTML = '';
        
        if (targets.length === 0) {
            container.innerHTML = `
                <div class="empty-state" id="empty-state-stocks" aria-live="polite">
                    <div class="empty-state-icon" aria-hidden="true">📡</div>
                    <p class="empty-state-title">데이터 수신 대기 중</p>
                    <p class="empty-state-desc">현재 포착된 종목이 없습니다.</p>
                </div>
            `;
            return;
        }

        targets.forEach(target => {
            const card = document.createElement('div');
            card.className = 'stock-card';
            card.innerHTML = `
                <div class="card-header" style="display:flex; justify-content:space-between; margin-bottom: 8px;">
                    <div>
                        <div style="font-weight:600; font-size:1.1rem;">${target.symbol_name}</div>
                        <div style="font-size:0.8rem; color:#A1A1A6;">${target.symbol_code}</div>
                    </div>
                    <span class="strategy-badge" style="background:rgba(94,92,230,0.2); color:#c4b5fd; padding:4px 10px; border-radius:20px; font-size:0.75rem;">${target.strategy_code}</span>
                </div>
                <div class="card-body" style="display:flex; justify-content:space-between; align-items:center;">
                    <div class="price-text" style="font-weight:700; font-size:1.2rem; color:#32D74B;">₩${target.detect_price.toLocaleString()}</div>
                    <div style="font-size:0.8rem; color:#636366;">${target.detect_time}</div>
                </div>
                <div style="margin-top:12px; display:flex; justify-content:space-between; align-items:center;">
                    <div style="font-size:0.8rem; color:#A1A1A6;">${target.notes}</div>
                    <button class="action-btn" onclick="viewChart('${target.symbol_code}')" style="background:rgba(10,132,255,0.1); color:#0A84FF; border:none; padding:6px 12px; border-radius:6px; cursor:pointer;">Chart</button>
                </div>
            `;
            // 애플 스타일 글래스모피즘 직접 주입
            card.style.background = 'rgba(28, 28, 30, 0.72)';
            card.style.backdropFilter = 'blur(12px)';
            card.style.webkitBackdropFilter = 'blur(12px)';
            card.style.border = '1px solid rgba(255, 255, 255, 0.15)';
            card.style.borderRadius = '16px';
            card.style.padding = '20px';
            card.style.marginBottom = '16px';
            card.style.boxShadow = '0 4px 20px rgba(0,0,0,0.3)';
            container.appendChild(card);
        });
    } catch (error) {
        console.error("Targets 에러:", error);
        const container = document.getElementById('stock-list-container');
        if (container) {
            container.innerHTML = `<div style="text-align: center; color: #FF3B30; padding: 20px;">Failed to load targets. Check API connection.</div>`;
        }
    }
}

// 네이버 증권 차트 팝업
function viewChart(code) {
    const url = `https://finance.naver.com/item/main.naver?code=${code}`;
    window.open(url, '_blank');
}