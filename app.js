/* ============================================================
   QUANT TERMINAL — app.js
   STEP 1: Foundation — Clock, Tab skeleton, Toast utility
   ============================================================ */
'use strict';

/* ── Live Clock ─────────────────────────────────────────────── */
function updateClock() {
  const el = document.getElementById('current-time');
  if (!el) return;
  const now = new Date();
  const hh  = String(now.getHours()).padStart(2, '0');
  const mm  = String(now.getMinutes()).padStart(2, '0');
  const ss  = String(now.getSeconds()).padStart(2, '0');
  el.textContent = `${hh}:${mm}:${ss}`;
}
updateClock();
setInterval(updateClock, 1000);


/* ── Segmented Tab Control ───────────────────────────────────── */
const segControl  = document.getElementById('segmented-control');
const tabBtns     = segControl ? segControl.querySelectorAll('.segment-btn') : [];
const panels      = document.querySelectorAll('.tab-panel');

tabBtns.forEach((btn) => {
  btn.addEventListener('click', () => {
    const target = btn.dataset.tab;

    // Update button states
    tabBtns.forEach(b => {
      b.classList.remove('active');
      b.setAttribute('aria-selected', 'false');
    });
    btn.classList.add('active');
    btn.setAttribute('aria-selected', 'true');

    // Slide the indicator
    if (target === 'swing') {
      segControl.classList.add('swing-active');
    } else {
      segControl.classList.remove('swing-active');
    }

    // Switch panels
    panels.forEach(p => p.classList.remove('active'));
    const targetPanel = document.getElementById(`panel-${target}`);
    if (targetPanel) targetPanel.classList.add('active');
  });
});


/* ── Toast Notification Utility ─────────────────────────────── */
const toastArea = document.getElementById('toast-area');

const TOAST_ICONS = {
  success:  '✅',
  warning:  '⚠️',
  error:    '🔴',
  info:     'ℹ️',
};

function showToast(message, type = 'info', duration = 3500) {
  if (!toastArea) return;
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.setAttribute('role', 'alert');
  toast.innerHTML = `
    <span class="toast-icon">${TOAST_ICONS[type] || 'ℹ️'}</span>
    <span class="toast-msg">${message}</span>
  `;
  toastArea.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('removing');
    toast.addEventListener('animationend', () => toast.remove(), { once: true });
  }, duration);
}


/* ── Header: Refresh news button ────────────────────────────── */
const btnRefreshNews = document.getElementById('btn-refresh-news');
if (btnRefreshNews) {
  btnRefreshNews.addEventListener('click', () => {
    btnRefreshNews.classList.add('spinning');
    btnRefreshNews.addEventListener('animationend', () => {
      btnRefreshNews.classList.remove('spinning');
    }, { once: true });
    showToast('뉴스 데이터를 갱신했습니다.', 'success');
  });
}


/* ── Modal Backdrop: close on outside click ─────────────────── */
const modalBackdrop = document.getElementById('modal-backdrop');
if (modalBackdrop) {
  modalBackdrop.addEventListener('click', (e) => {
    if (e.target === modalBackdrop) closeModal();
  });
}

/* Keyboard: Escape to close modal */
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeModal();
});

function openModal() {
  if (!modalBackdrop) return;
  modalBackdrop.classList.add('open');
  modalBackdrop.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  if (!modalBackdrop) return;
  modalBackdrop.classList.remove('open');
  modalBackdrop.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
}

/* Expose to global scope for later steps */
window.QuantTerminal = { showToast, openModal, closeModal };

/* ── Startup Toast ──────────────────────────────────────────── */
window.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => showToast('QuantTerminal 실시간 연결 완료', 'success'), 600);
});
