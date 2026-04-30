/* ================================================================
   QuantTerminal Pro — dashboard.js
   STEP 1: Clock · Magic Tab Indicator · Subheader sync · Toasts
================================================================ */
'use strict';

/* ─── Live Clock ─────────────────────────────────────────────── */
const clockEl = document.getElementById('clock-display');
function updateClock() {
  if (!clockEl) return;
  const n = new Date();
  const p = (v) => String(v).padStart(2, '0');
  clockEl.textContent = `${p(n.getHours())}:${p(n.getMinutes())}:${p(n.getSeconds())}`;
}
updateClock();
setInterval(updateClock, 1000);

/* ─── Connection Status (mock: live after 800ms) ─────────────── */
const statusPulse = document.getElementById('status-pulse');
const statusText  = document.getElementById('status-text');
setTimeout(() => {
  if (statusText) statusText.textContent = '실시간 연결';
  showToast('실시간 서버 연결 완료', 'success');
}, 800);

/* ─── Magic Tab Navigation ───────────────────────────────────── */
const tabNav    = document.getElementById('magic-tab-nav');
const indicator = document.getElementById('tab-indicator');
const tabBtns   = tabNav ? Array.from(tabNav.querySelectorAll('.tab-btn')) : [];
const tabViews  = document.querySelectorAll('.tab-view');
const subViews  = document.querySelectorAll('.subheader-view');

function positionIndicator(btn) {
  if (!indicator || !btn || !tabNav) return;
  // Measure btn position relative to the nav container
  const navRect = tabNav.getBoundingClientRect();
  const btnRect = btn.getBoundingClientRect();
  indicator.style.width     = `${btnRect.width}px`;
  indicator.style.transform = `translateX(${btnRect.left - navRect.left - 3}px)`;
}

function activateTab(btn) {
  const target = btn.dataset.tab;

  // 1. Update tab button states
  tabBtns.forEach(b => {
    b.classList.remove('active');
    b.setAttribute('aria-selected', 'false');
  });
  btn.classList.add('active');
  btn.setAttribute('aria-selected', 'true');

  // 2. Slide the magic indicator
  positionIndicator(btn);

  // 3. Switch main views
  tabViews.forEach(v => v.classList.remove('active'));
  const targetView = document.getElementById(`view-${target}`);
  if (targetView) targetView.classList.add('active');

  // 4. Switch subheader context
  subViews.forEach(v => v.classList.add('hidden'));
  const targetSub = document.getElementById(`sub-${target}`);
  if (targetSub) targetSub.classList.remove('hidden');
}

tabBtns.forEach(btn => {
  btn.addEventListener('click', () => activateTab(btn));
});

// Init indicator on first active tab (after fonts/layout settle)
window.addEventListener('load', () => {
  const activeBtn = tabNav?.querySelector('.tab-btn.active');
  if (activeBtn) positionIndicator(activeBtn);
});

// Re-position on resize
window.addEventListener('resize', () => {
  const activeBtn = tabNav?.querySelector('.tab-btn.active');
  if (activeBtn) positionIndicator(activeBtn);
});

/* ─── Subheader Filter Buttons ───────────────────────────────── */
document.querySelectorAll('.subheader-view').forEach(view => {
  view.querySelectorAll('.sub-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      // Deactivate siblings within same subheader-view
      view.querySelectorAll('.sub-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      // Emit custom event for STEP 2/3 to filter grids
      document.dispatchEvent(new CustomEvent('qt:filter', {
        detail: { tab: view.dataset.sub, filter: btn.dataset.filter }
      }));
    });
  });
});

/* ─── Modal ──────────────────────────────────────────────────── */
const overlay = document.getElementById('modal-overlay');

function openModal(data = {}) {
  if (!overlay) return;
  overlay.classList.add('open');
  overlay.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
  document.dispatchEvent(new CustomEvent('qt:modal-open', { detail: data }));
}

function closeModal() {
  if (!overlay) return;
  overlay.classList.remove('open');
  overlay.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
}

if (overlay) {
  overlay.addEventListener('click', e => {
    if (e.target === overlay) closeModal();
  });
}
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModal();
});

/* ─── Toast System ───────────────────────────────────────────── */
const toastArea = document.getElementById('toast-container');
const ICONS = { success:'✅', warning:'⚠️', error:'🔴', info:'ℹ️' };

function showToast(msg, type = 'info', ms = 3500) {
  if (!toastArea) return;
  const t = document.createElement('div');
  t.className = 'toast';
  t.setAttribute('role', 'alert');
  t.innerHTML = `<span>${ICONS[type] ?? 'ℹ️'}</span><span>${msg}</span>`;
  toastArea.appendChild(t);
  setTimeout(() => {
    t.classList.add('removing');
    t.addEventListener('animationend', () => t.remove(), { once: true });
  }, ms);
}

/* ─── Public API ─────────────────────────────────────────────── */
window.QT = { showToast, openModal, closeModal };


/* ================================================================
   STEP 2 — STOCK CARD RENDERING
================================================================ */

/* ── Mock Data ───────────────────────────────────────────────── */
const MOCK_SCALP = [
  { code:'005930', name:'삼성전자',   price:78400,  change:+1200, rate:+1.56, strength:92, badge:'골든크로스', badgeCls:'badge-golden', strategy:'A-1 · 볼린저 밴드 하단 반등', fadeOut:false },
  { code:'000660', name:'SK하이닉스', price:195500, change:-2500, rate:-1.26, strength:81, badge:'눌림목',    badgeCls:'badge-dip',    strategy:'A-2 · 눌림목 재진입',         fadeOut:false },
  { code:'035420', name:'NAVER',      price:211000, change:+3000, rate:+1.44, strength:76, badge:'돌파',     badgeCls:'badge-break',  strategy:'A-3 · 박스권 상단 돌파',       fadeOut:false },
  { code:'035720', name:'카카오',     price:43650,  change:-350,  rate:-0.79, strength:65, badge:'거래량',   badgeCls:'badge-vol',    strategy:'A-2 · 거래량 이상 감지',       fadeOut:false },
  { code:'373220', name:'LG에너지솔루션', price:352000, change:+8500, rate:+2.47, strength:88, badge:'골든크로스', badgeCls:'badge-golden', strategy:'A-1 · 20/60 골든크로스',   fadeOut:false },
  { code:'207940', name:'삼성바이오로직스', price:968000, change:-12000, rate:-1.22, strength:58, badge:'이탈대기', badgeCls:'badge-vol', strategy:'A-3 · 조건식 이탈 중',       fadeOut:true  },
  { code:'006400', name:'삼성SDI',    price:274500, change:+4500, rate:+1.67, strength:79, badge:'눌림목',    badgeCls:'badge-dip',    strategy:'A-2 · 5일선 지지 눌림',        fadeOut:false },
  { code:'051910', name:'LG화학',     price:189500, change:-2000, rate:-1.04, strength:72, badge:'돌파',     badgeCls:'badge-break',  strategy:'A-3 · 저항선 돌파 시도',       fadeOut:false },
  { code:'028260', name:'삼성물산',   price:155000, change:+1500, rate:+0.98, strength:55, badge:'이탈대기', badgeCls:'badge-bband',  strategy:'B-1 · 조건 약화 이탈 대기',    fadeOut:true  },
  { code:'000270', name:'기아',       price:96400,  change:+800,  rate:+0.84, strength:83, badge:'MACD',    badgeCls:'badge-macd',   strategy:'B-3 · MACD 0선 돌파',          fadeOut:false },
  { code:'105560', name:'KB금융',     price:89300,  change:-600,  rate:-0.67, strength:70, badge:'엔벨로프', badgeCls:'badge-env',   strategy:'B-2 · 엔벨로프 하단 터치',      fadeOut:false },
  { code:'055550', name:'신한지주',   price:56700,  change:+400,  rate:+0.71, strength:91, badge:'골든크로스', badgeCls:'badge-golden', strategy:'A-1 · 정배열 골든크로스',     fadeOut:false },
];

const MOCK_SWING = [
  { code:'005380', name:'현대차',     price:228000, change:+5000, rate:+2.24, strength:85, badge:'볼린저밴드', badgeCls:'badge-bband',  strategy:'B-1 · 볼린저 하단 반등',       fadeOut:false },
  { code:'012330', name:'현대모비스', price:245000, change:-3000, rate:-1.21, strength:74, badge:'엔벨로프',   badgeCls:'badge-env',    strategy:'B-2 · 엔벨로프 하단 터치',     fadeOut:false },
  { code:'096770', name:'SK이노베이션', price:118500, change:+2000, rate:+1.72, strength:67, badge:'MACD',  badgeCls:'badge-macd',   strategy:'B-3 · MACD 0선 돌파',          fadeOut:false },
  { code:'003550', name:'LG',         price:89200,  change:+1100, rate:+1.25, strength:88, badge:'골든크로스', badgeCls:'badge-golden', strategy:'A-1 · 20/60 골든크로스',      fadeOut:false },
  { code:'010130', name:'고려아연',   price:612000, change:-8000, rate:-1.29, strength:61, badge:'이탈대기', badgeCls:'badge-vol',    strategy:'B-1 · 조건 약화',               fadeOut:true  },
  { code:'047810', name:'한국항공우주', price:67800, change:+1200, rate:+1.80, strength:93, badge:'돌파',   badgeCls:'badge-break',  strategy:'A-3 · 52주 신고가 돌파',        fadeOut:false },
  { code:'034020', name:'두산에너빌리티', price:22450, change:+350, rate:+1.59, strength:77, badge:'눌림목', badgeCls:'badge-dip',   strategy:'A-2 · 눌림목 5일선 지지',       fadeOut:false },
  { code:'009150', name:'삼성전기',   price:148000, change:-2500, rate:-1.66, strength:82, badge:'엔벨로프', badgeCls:'badge-env',   strategy:'B-2 · 엔벨로프 하단 반등',      fadeOut:false },
];

/* ── Circular Gauge SVG Builder ──────────────────────────────── */
function buildGaugeSVG(pct) {
  const r   = 18;
  const cx  = 24;
  const cy  = 24;
  const circ = 2 * Math.PI * r;         // ≈ 113.1
  const offset = circ * (1 - pct / 100);
  const isHigh = pct >= 70;
  const fillCls = isHigh ? 'gauge-fill high' : 'gauge-fill low';
  const pctCls  = isHigh ? 'gauge-pct' : 'gauge-pct low-text';

  return `
    <div class="circular-gauge">
      <svg class="gauge-svg" viewBox="0 0 48 48" aria-hidden="true">
        <circle class="gauge-track" cx="${cx}" cy="${cy}" r="${r}"/>
        <circle
          class="${fillCls}"
          cx="${cx}" cy="${cy}" r="${r}"
          stroke-dasharray="${circ}"
          stroke-dashoffset="${offset}"
        />
      </svg>
      <div class="gauge-label">
        <span class="${pctCls}">${pct}%</span>
        <span class="gauge-caption">강도</span>
      </div>
    </div>`;
}

/* ── Card HTML Builder ───────────────────────────────────────── */
function buildCard(stock, index) {
  const isRise  = stock.change >= 0;
  const clrCls  = isRise ? 'rise' : 'fall';
  const arrow   = isRise ? '▲' : '▼';
  const absAmt  = Math.abs(stock.change).toLocaleString();
  const absRate = Math.abs(stock.rate).toFixed(2);
  const price   = stock.price.toLocaleString();

  const fadeClass  = stock.fadeOut ? ' fade-out' : '';
  const timerHTML  = stock.fadeOut
    ? `<span class="fadeout-timer" title="10분 카운트다운">⏱ 이탈대기</span>`
    : '';

  return `
    <article
      class="stock-card${fadeClass}"
      style="--card-delay:${index * 40}ms"
      data-code="${stock.code}"
      data-name="${stock.name}"
      tabindex="${stock.fadeOut ? -1 : 0}"
      aria-label="${stock.name} ${price}원 ${arrow}${absRate}%"
      role="button"
    >
      ${timerHTML}
      <div class="card-top">
        <div class="card-name-block">
          <span class="card-name">${stock.name}</span>
          <span class="card-code">${stock.code}</span>
        </div>
        <span class="card-badge ${stock.badgeCls}">${stock.badge}</span>
      </div>

      <div class="card-strategy">${stock.strategy}</div>

      <div class="card-bottom">
        <div class="card-price-block ${clrCls}">
          <span class="card-price">${price}<small style="font-size:13px;font-weight:500;margin-left:2px">원</small></span>
          <div class="card-change">
            <span class="card-change-amt">${arrow} ${absAmt}원</span>
            <span class="card-change-pct">${arrow}${absRate}%</span>
          </div>
        </div>
        <div class="card-gauge-wrap">
          ${buildGaugeSVG(stock.strength)}
        </div>
      </div>
    </article>`;
}

/* ── Render Grid ─────────────────────────────────────────────── */
function renderGrid(containerId, data) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = data.map((s, i) => buildCard(s, i)).join('');

  // Animate gauge arcs after DOM paint (dashoffset transition kicks in)
  requestAnimationFrame(() => {
    container.querySelectorAll('.gauge-fill').forEach(arc => {
      // Force reflow so transition plays from initial state
      arc.getBoundingClientRect();
    });
  });

  // Attach click → modal (pass FULL stock object for order book)
  container.querySelectorAll('.stock-card:not(.fade-out)').forEach(card => {
    card.addEventListener('click', () => {
      const code = card.dataset.code;
      // Look up full stock from ALL_STOCKS map, fall back to dataset
      const stock = ALL_STOCKS[code] || { code, name: card.dataset.name, price: 50000, change: 0, rate: 0, strength: 75, badge: '—', badgeCls: '' };
      window.QT.openModal(stock);
    });
    // Keyboard accessibility
    card.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') card.click();
    });
  });
}

/* ── Filter Listener ─────────────────────────────────────────── */
document.addEventListener('qt:filter', (e) => {
  const { tab, filter } = e.detail;
  const source = tab === 'scalp' ? MOCK_SCALP : MOCK_SWING;
  const gridId = tab === 'scalp' ? 'grid-scalp' : 'grid-swing';

  if (filter === 'all') {
    renderGrid(gridId, source);
    return;
  }
  // Filter by badge keyword match
  const filtered = source.filter(s =>
    s.badge.includes(filter) ||
    s.strategy.toLowerCase().includes(filter) ||
    s.badgeCls.includes(filter)
  );
  renderGrid(gridId, filtered.length ? filtered : source);
});

/* ── Initial Render on DOMContentLoaded ──────────────────────── */
window.addEventListener('load', () => {
  renderGrid('grid-scalp', MOCK_SCALP);
  renderGrid('grid-swing', MOCK_SWING);
});


/* ================================================================
   STEP 3 — GLOBAL NEWS RENDERING
================================================================ */

/* ── Sentiment helpers ───────────────────────────────────────── */
const SENT_CLS  = { pos:'s-pos', neu:'s-neu', neg:'s-neg' };
const SENT_LABEL= { pos:'긍정', neu:'중립', neg:'부정' };

function sentDot(s, size = 'sm') {
  const big = size === 'lg';
  return `<span class="sentiment-dot ${SENT_CLS[s]}" title="${SENT_LABEL[s]}"></span>`;
}

/* ── Stock tag builder ───────────────────────────────────────── */
function buildTags(tags) {
  if (!tags?.length) return '';
  return `<div class="news-tags">
    ${tags.map(t => `<span class="news-tag tag-${t.market}">${t.label}</span>`).join('')}
  </div>`;
}

/* ── Mock News Data ──────────────────────────────────────────── */
const MOCK_NEWS_HERO = {
  id: 'hero-1',
  sentiment:  'neg',
  source:     'Bloomberg',
  category:   '거시경제',
  title:      '美 연준, 금리 동결 유지… "인플레이션 목표 달성 확신 필요" — 파월 의장 발언 전문',
  summary:    '제롬 파월 연준 의장은 FOMC 정례회의 직후 기자회견에서 "현재 통화정책 기조는 충분히 제한적"이라면서도 "2% 인플레이션 목표 달성에 대한 확신이 생기기 전까지 금리 인하는 없다"고 못 박았다. 시장은 연내 1~2회 인하 기대를 낮추며 반응했다.',
  time:       '14:32',
  elapsed:    '28분 전',
  thumbEmoji: '🏛️',
  thumbGrad:  'linear-gradient(135deg, #1D1D1F 0%, #3A3A3C 50%, #0071E3 100%)',
  tags: [
    { label:'TSLA', market:'us' }, { label:'NVDA', market:'us' },
    { label:'삼성전자', market:'kr' }, { label:'SK하이닉스', market:'kr' }
  ]
};

const MOCK_NEWS_GRID = [
  {
    id:'n1', wide:true, hasThumb:true, sentiment:'pos',
    source:'Reuters', category:'반도체',
    title:   'TSMC, 2나노 수율 80% 돌파 — 애플·엔비디아 물량 조기 확보 경쟁',
    summary: '파운드리 업계 1위 TSMC가 2nm 공정 수율을 80% 이상으로 끌어올리며 양산 본궤도에 올랐다고 내부 소식통이 전했다.',
    time:'13:55', elapsed:'1시간 5분 전',
    thumbEmoji:'⚡', thumbGrad:'linear-gradient(135deg,#34C759,#0071E3)',
    tags:[ {label:'TSMC',market:'us'},{label:'AAPL',market:'us'},{label:'삼성전자',market:'kr'} ]
  },
  {
    id:'n2', wide:false, hasThumb:false, sentiment:'neg',
    source:'연합뉴스', category:'정치',
    title:   '트럼프, 中 반도체 장비 수출 통제 추가 강화 행정명령 서명',
    summary: '중국 내 반도체 제조 장비 수출을 전면 봉쇄하는 수위의 조치로, 국내 소부장 업체에 간접 영향 우려.',
    time:'13:10', elapsed:'1시간 50분 전',
    thumbEmoji:null, thumbGrad:null,
    tags:[ {label:'한미반도체',market:'kr'},{label:'원익IPS',market:'kr'} ]
  },
  {
    id:'n3', wide:false, hasThumb:false, sentiment:'neu',
    source:'한국경제', category:'환율',
    title:   '원/달러 환율 1,385원대 등락 — 외환당국 구두개입 경고',
    summary: '기획재정부가 "쏠림 현상 시 적극 대응"을 시사. 수출주 단기 수혜 기대.',
    time:'12:40', elapsed:'2시간 20분 전',
    thumbEmoji:null, thumbGrad:null,
    tags:[ {label:'현대차',market:'kr'},{label:'삼성전자',market:'kr'} ]
  },
  {
    id:'n4', wide:false, hasThumb:true, sentiment:'pos',
    source:'CNBC', category:'AI',
    title:   '엔비디아 블랙웰 GB200, 데이터센터 수요 예상 3배 초과 — 서버 대기 12개월',
    summary: 'AI 인프라 투자 사이클이 2027년까지 지속될 것이라는 월가 분석이 잇따름.',
    time:'11:58', elapsed:'3시간 2분 전',
    thumbEmoji:'🤖', thumbGrad:'linear-gradient(135deg,#5E5CE6,#0071E3)',
    tags:[ {label:'NVDA',market:'us'},{label:'SMCI',market:'us'},{label:'SK하이닉스',market:'kr'} ]
  },
  {
    id:'n5', wide:false, hasThumb:false, sentiment:'neg',
    source:'Caixin', category:'중국경제',
    title:   '中 차이신 제조업 PMI 49.2 — 3개월 연속 수축 국면 진입',
    summary: '글로벌 수요 위축 신호로 해석. 소재·화학 업종 하방 리스크 부각.',
    time:'10:30', elapsed:'4시간 30분 전',
    thumbEmoji:null, thumbGrad:null,
    tags:[ {label:'POSCO홀딩스',market:'kr'},{label:'LG화학',market:'kr'} ]
  },
  {
    id:'n6', wide:false, hasThumb:true, sentiment:'pos',
    source:'WSJ', category:'바이오',
    title:   '일라이릴리, GLP-1 차세대 비만 치료제 임상3상 성공 — 체중 감소 24% 달성',
    summary: '경쟁사 대비 압도적 효능으로 연간 500억 달러 시장 주도권 확보 전망.',
    time:'09:15', elapsed:'5시간 45분 전',
    thumbEmoji:'💊', thumbGrad:'linear-gradient(135deg,#FF9F0A,#FF3B30)',
    tags:[ {label:'LLY',market:'us'},{label:'한미약품',market:'kr'} ]
  },
  {
    id:'n7', wide:false, hasThumb:false, sentiment:'neu',
    source:'코인데스크', category:'암호화폐',
    title:   '비트코인 68,200달러 횡보 — 현물 ETF 순유입 3거래일째 지속',
    summary: '기관 매수세가 개인 차익실현을 흡수하는 구도. 단기 방향성은 FOMC 이후 결정될 전망.',
    time:'08:50', elapsed:'6시간 10분 전',
    thumbEmoji:null, thumbGrad:null,
    tags:[ {label:'BTC',market:'crypto'},{label:'ETH',market:'crypto'} ]
  },
  {
    id:'n8', wide:false, hasThumb:false, sentiment:'pos',
    source:'파이낸셜뉴스', category:'조선·방산',
    title:   'HD현대중공업, 美 해군 MRO 계약 수주 확정 — 수주잔고 역대 최대',
    summary: '총 계약 규모 2.3조원, 2026~2030년 분할 인식. 방산 밸류업 테마 재부각.',
    time:'08:00', elapsed:'7시간 전',
    thumbEmoji:null, thumbGrad:null,
    tags:[ {label:'HD현대중공업',market:'kr'},{label:'한화오션',market:'kr'} ]
  },
];

/* ── Hero Card Builder ───────────────────────────────────────── */
function buildHeroCard(item) {
  const thumbHTML = item.thumbGrad
    ? `<div class="hero-thumb-gradient" style="--thumb-grad:${item.thumbGrad}">${item.thumbEmoji ?? ''}</div>`
    : `<div class="hero-thumb-gradient">${item.thumbEmoji ?? '📰'}</div>`;

  return `
  <article class="news-hero" data-news-id="${item.id}" role="button" tabindex="0"
    aria-label="${item.source} — ${item.title}">
    <div class="hero-body">
      <div class="hero-meta-row">
        <span class="hero-source-badge">${item.source}</span>
        <span class="hero-category">${item.category}</span>
        ${sentDot(item.sentiment, 'lg')}
      </div>
      <h2 class="hero-title">${item.title}</h2>
      <p class="hero-summary">${item.summary}</p>
      <div class="hero-footer">
        <span class="hero-time">🕐 ${item.elapsed} &nbsp;·&nbsp; ${item.time} KST</span>
        ${buildTags(item.tags)}
      </div>
    </div>
    <div class="hero-thumb">
      ${thumbHTML}
    </div>
  </article>`;
}

/* ── Standard News Card Builder ──────────────────────────────── */
function buildNewsCard(item, index) {
  const wideClass  = item.wide     ? ' news-card-wide' : '';
  const thumbClass = item.hasThumb ? ' has-thumb'      : '';

  const thumbHTML = item.hasThumb && item.thumbGrad
    ? `<div class="news-thumb-sm">
         <div class="news-thumb-sm-gradient" style="--thumb-grad:${item.thumbGrad}">
           ${item.thumbEmoji ?? ''}
         </div>
       </div>`
    : '';

  const bodyHTML = `
    <div class="news-body">
      <div class="news-card-header">
        <span class="news-source">${item.source}</span>
        <span class="news-category-tag">${item.category}</span>
        ${sentDot(item.sentiment)}
      </div>
      <p class="news-title">${item.title}</p>
      ${item.summary ? `<p class="news-summary">${item.summary}</p>` : ''}
      <div class="news-footer">
        <span class="news-meta">${item.elapsed} · ${item.time}</span>
        ${buildTags(item.tags)}
      </div>
    </div>`;

  return `
  <article
    class="news-card${wideClass}${thumbClass}"
    style="--news-delay:${index * 50}ms"
    data-news-id="${item.id}"
    role="button" tabindex="0"
    aria-label="${item.source} — ${item.title}"
  >
    ${thumbHTML}
    ${bodyHTML}
  </article>`;
}

/* ── Full News View Renderer ─────────────────────────────────── */
function renderNews(filter = 'all') {
  const container = document.getElementById('grid-news');
  if (!container) return;

  // Apply filter
  let items = MOCK_NEWS_GRID;
  if (filter === 'positive') items = items.filter(n => n.sentiment === 'pos');
  else if (filter === 'negative') items = items.filter(n => n.sentiment === 'neg');
  else if (filter === 'us') items = items.filter(n => n.tags?.some(t => t.market === 'us'));
  else if (filter === 'china') items = items.filter(n => n.category.includes('중국') || n.tags?.some(t => t.label.includes('中') || n.source === 'Caixin'));

  container.innerHTML = `
    <div class="news-canvas">
      <!-- ZONE A: Hero -->
      <div class="news-section-label">🔥 주요 뉴스</div>
      ${buildHeroCard(MOCK_NEWS_HERO)}

      <!-- ZONE B: Grid -->
      <div class="news-section-label">📡 실시간 뉴스</div>
      <div class="news-grid-zone">
        ${items.map((item, i) => buildNewsCard(item, i)).join('')}
      </div>
    </div>`;

  // Attach click events
  container.querySelectorAll('[data-news-id]').forEach(el => {
    el.addEventListener('click', () => {
      showToast('뉴스 상세 뷰 (STEP 4에서 모달 연동 예정)', 'info', 2000);
    });
    el.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') el.click();
    });
  });
}

/* ── Filter event listener ───────────────────────────────────── */
document.addEventListener('qt:filter', (e) => {
  if (e.detail.tab !== 'news') return;
  renderNews(e.detail.filter);
});

/* ── Render on initial load ──────────────────────────────────── */
window.addEventListener('load', () => {
  renderNews('all');
});


/* ================================================================
   STEP 4 — DETAIL MODAL: CHART + ORDER BOOK + INTERACTIONS
================================================================ */

/* ── Mock Order Book Generator ───────────────────────────────── */
function generateOrderBook(basePrice) {
  const tick   = basePrice >= 50000 ? 50  : basePrice >= 10000 ? 10 : 5;
  const asks   = [];  // 매도 10호가 (위 → 아래: 높은가 → 낮은가)
  const bids   = [];  // 매수 10호가 (위 → 아래: 높은가 → 낮은가)

  for (let i = 10; i >= 1; i--) {
    asks.push({
      price: basePrice + tick * i,
      qty:   Math.floor(Math.random() * 30000 + 3000),
    });
  }
  for (let i = 1; i <= 10; i++) {
    bids.push({
      price: basePrice - tick * i,
      qty:   Math.floor(Math.random() * 40000 + 5000),
    });
  }
  return { asks, bids, currentPrice: basePrice };
}

/* ── Chart View HTML Builders ────────────────────────────────── */
const CHART_CONFIGS = {
  min:  { label:'분봉',     icon:'📊', indicators:['볼린저밴드', 'RSI(14)', '스토캐스틱'] },
  cond: { label:'조건식 봉', icon:'🎯', indicators:['신호 발생봉', '진입강도', '이격도'] },
  day:  { label:'일봉',     icon:'📈', indicators:['MACD', '엔벨로프', '이동평균'] },
};

function buildChartView(type) {
  const cfg = CHART_CONFIGS[type];
  return `
  <div class="chart-view ${type === 'min' ? 'active' : ''}" data-chart="${type}">
    <div class="chart-area-main">
      <span class="chart-placeholder-icon">${cfg.icon}</span>
      <span class="chart-placeholder-text">${cfg.label} 차트 — 실시간 연동 대기 중</span>
    </div>
    <div class="chart-area-sub">
      ${cfg.indicators.map(ind =>
        `<span class="chart-indicator-label">${ind}</span>`
      ).join('')}
    </div>
  </div>`;
}

/* ── Order Book HTML Builder ─────────────────────────────────── */
function buildOrderBook(stock) {
  const { asks, bids, currentPrice } = generateOrderBook(stock.price);

  // Max qty across all rows for proportional bar widths
  const maxQty = Math.max(...asks.map(a => a.qty), ...bids.map(b => b.qty));
  const fillPct = (qty) => `${Math.round((qty / maxQty) * 100)}%`;

  // Total buy/sell for summary ratio
  const totalBid = bids.reduce((s, r) => s + r.qty, 0);
  const totalAsk = asks.reduce((s, r) => s + r.qty, 0);
  const bidRatio = Math.round((totalBid / (totalBid + totalAsk)) * 100);

  // Asks (매도): highest price first
  const askRows = asks.map(r => `
  <div class="ob-row">
    <div class="ob-qty-ask" style="--fill:${fillPct(r.qty)}">${r.qty.toLocaleString()}</div>
    <div class="ob-price rise">${r.price.toLocaleString()}</div>
    <div class="ob-qty-bid" style="--fill:0%">—</div>
  </div>`).join('');

  // Center row (현재가)
  const isRise = stock.change >= 0;
  const centerRow = `
  <div class="ob-row ob-center">
    <div class="ob-qty-ask" style="--fill:0%">현재가</div>
    <div class="ob-price ${isRise ? 'rise' : 'fall'}">${currentPrice.toLocaleString()}</div>
    <div class="ob-qty-bid" style="--fill:0%">${isRise ? '▲' : '▼'} ${Math.abs(stock.rate).toFixed(2)}%</div>
  </div>`;

  // Bids (매수): highest bid first
  const bidRows = bids.map(r => `
  <div class="ob-row">
    <div class="ob-qty-ask" style="--fill:0%">—</div>
    <div class="ob-price fall">${r.price.toLocaleString()}</div>
    <div class="ob-qty-bid" style="--fill:${fillPct(r.qty)}">${r.qty.toLocaleString()}</div>
  </div>`).join('');

  return `
  <div class="orderbook-header">
    <span class="orderbook-title">10호가 잔량</span>
    <span class="orderbook-spread">스프레드 ${(asks[asks.length-1].price - bids[0].price).toLocaleString()}원</span>
  </div>
  <div class="orderbook-cols">
    <span class="ob-col-label">잔량(매도)</span>
    <span class="ob-col-label">호가</span>
    <span class="ob-col-label">잔량(매수)</span>
  </div>
  <div class="orderbook-rows">
    ${askRows}
    ${centerRow}
    ${bidRows}
  </div>
  <div class="orderbook-footer">
    <div class="ob-ratio-labels">
      <span class="ob-ratio-buy">매수 ${bidRatio}%</span>
      <span class="ob-ratio-sell">매도 ${100 - bidRatio}%</span>
    </div>
    <div class="ob-ratio-bar">
      <div class="ob-ratio-fill" id="ob-ratio-fill" style="width:0%"></div>
    </div>
  </div>`;
}

/* ── Full Modal HTML Builder ─────────────────────────────────── */
function buildModalHTML(stock) {
  const isRise   = stock.change >= 0;
  const clrCls   = isRise ? 'rise' : 'fall';
  const arrow    = isRise ? '▲' : '▼';
  const absAmt   = Math.abs(stock.change).toLocaleString();
  const absRate  = Math.abs(stock.rate).toFixed(2);
  const price    = stock.price.toLocaleString();

  return `
  <!-- Modal Header -->
  <div class="modal-header">
    <div style="display:flex;align-items:center;gap:16px;flex:1;min-width:0;">
      <div class="modal-stock-info">
        <span class="modal-stock-name" id="modal-stock-name">${stock.name}</span>
        <span class="modal-stock-code">${stock.code}</span>
      </div>
      <div class="modal-price-block">
        <span class="modal-price ${clrCls}">${price}원</span>
        <span class="modal-change ${clrCls}">${arrow} ${absAmt}원 (${arrow}${absRate}%)</span>
      </div>
      <span class="modal-badge ${stock.badgeCls}">${stock.badge}</span>
    </div>
    <button class="modal-close-btn" id="modal-close-btn" aria-label="닫기">✕</button>
  </div>

  <!-- Modal Body -->
  <div class="modal-body">
    <!-- LEFT: Chart -->
    <div class="chart-panel">
      <div class="chart-tab-bar" id="chart-tab-bar">
        <button class="chart-tab-btn active" data-chart="min">분봉</button>
        <button class="chart-tab-btn" data-chart="cond">조건식 봉</button>
        <button class="chart-tab-btn" data-chart="day">일봉</button>
        <span class="chart-tab-indicator">실시간 연동 대기 중</span>
      </div>
      <div class="chart-views" id="chart-views">
        ${buildChartView('min')}
        ${buildChartView('cond')}
        ${buildChartView('day')}
      </div>
    </div>

    <!-- RIGHT: Order Book -->
    <div class="orderbook-panel" id="orderbook-panel">
      ${buildOrderBook(stock)}
    </div>
  </div>`;
}

/* ── Chart Tab Switching (Modal Inner) ───────────────────────── */
function initChartTabs() {
  const tabBar   = document.getElementById('chart-tab-bar');
  const views    = document.getElementById('chart-views');
  if (!tabBar || !views) return;

  tabBar.querySelectorAll('.chart-tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.chart;

      // Update buttons
      tabBar.querySelectorAll('.chart-tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      // Fade-in target view
      views.querySelectorAll('.chart-view').forEach(v => v.classList.remove('active'));
      const targetView = views.querySelector(`[data-chart="${target}"]`);
      if (targetView) targetView.classList.add('active');
    });
  });
}

/* ── Animate the ratio bar after modal opens ─────────────────── */
function animateRatioBar(stock) {
  const fill = document.getElementById('ob-ratio-fill');
  if (!fill) return;
  // Seed from stock.strength for consistent feel
  const ratio = Math.round(30 + stock.strength * 0.5);
  requestAnimationFrame(() => {
    setTimeout(() => { fill.style.width = `${ratio}%`; }, 80);
  });
}

/* ── Enhanced openModal ──────────────────────────────────────── */
const overlayEl  = document.getElementById('modal-overlay');
const modalPanel = document.getElementById('modal-panel');

/* Override the base openModal from STEP 1 */
window.QT.openModal = function(stock) {
  if (!overlayEl || !modalPanel || !stock?.code) return;

  // Build content
  modalPanel.innerHTML = buildModalHTML(stock);

  // Wire close button
  document.getElementById('modal-close-btn')?.addEventListener('click', window.QT.closeModal);

  // Animate in
  overlayEl.classList.add('open');
  overlayEl.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';

  // Init chart tabs
  initChartTabs();

  // Animate order book ratio bar
  animateRatioBar(stock);
};

/* Backdrop click */
overlayEl?.addEventListener('click', e => {
  if (e.target === overlayEl) window.QT.closeModal();
});

/* ESC key */
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && overlayEl?.classList.contains('open')) {
    window.QT.closeModal();
  }
});

/* ── Rebind card clicks with full stock object ────────────────── */
/*
  STEP 2's renderGrid passes { code, name } to openModal.
  We need the full stock object for the order book.
  We upgrade the card click handler here using combined mock data.
*/
const ALL_STOCKS = {};
window.addEventListener('load', () => {
  // Merge scalp + swing into a lookup map by code
  [...(window.MOCK_SCALP_DATA || []), ...(window.MOCK_SWING_DATA || [])].forEach(s => {
    ALL_STOCKS[s.code] = s;
  });
});

/* Expose lookup so renderGrid can use it */
window.QT.getStock = (code) => ALL_STOCKS[code];

/* Patch: renderGrid already calls openModal({code, name}).
   We patch openModal to auto-enrich with full data if available. */
const _baseOpen = window.QT.openModal;
window.QT.openModal = function(data) {
  const full = ALL_STOCKS[data?.code] || data;
  // Guarantee required fields with sensible defaults
  const stock = {
    code:     full.code     || '000000',
    name:     full.name     || '알 수 없음',
    price:    full.price    || 50000,
    change:   full.change   || 0,
    rate:     full.rate     || 0,
    strength: full.strength || 75,
    badge:    full.badge    || '—',
    badgeCls: full.badgeCls || '',
  };
  _baseOpen(stock);
};

/* Expose mock arrays for the lookup above */
window.addEventListener('DOMContentLoaded', () => {
  // Patch after STEP2 arrays are defined (they're in the same file, so available)
  if (typeof MOCK_SCALP !== 'undefined') {
    MOCK_SCALP.forEach(s => { ALL_STOCKS[s.code] = s; });
  }
  if (typeof MOCK_SWING !== 'undefined') {
    MOCK_SWING.forEach(s => { ALL_STOCKS[s.code] = s; });
  }
});
