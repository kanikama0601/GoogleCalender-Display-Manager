'use strict';
import { h, isoDate } from './utils.js';

const FX_PAIRS = [
  { base: 'usd', label: 'USD/JPY 米ドル/日本円' },
  { base: 'eur', label: 'EUR/JPY ユーロ/日本円' },
  { base: 'cny', label: 'CNY/JPY 人民元/日本円' },
];
let fxData = {};

async function fetchRate(dateStr, base) {
  const urls = [
    `https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@${dateStr}/v1/currencies/${base}.min.json`,
    `https://${dateStr}.currency-api.pages.dev/v1/currencies/${base}.min.json`,
  ];
  for (const url of urls) {
    try {
      const r = await fetch(url);
      if (!r.ok) continue;
      const j = await r.json();
      return j[base]['jpy'];
    } catch { }
  }
  return null;
}

export async function loadForex() {
  const yday = isoDate(-1);
  const lastWeek = isoDate(-7);
  try {
    const bases = FX_PAIRS.map(p => p.base);
    const [lt, yd, wk] = await Promise.all([
      Promise.all(bases.map(b => fetchRate('latest', b))),
      Promise.all(bases.map(b => fetchRate(yday, b))),
      Promise.all(bases.map(b => fetchRate(lastWeek, b))),
    ]);
    fxData = { latest: {}, prev1d: {}, prev1w: {} };
    bases.forEach((b, i) => {
      fxData.latest[b] = lt[i];
      fxData.prev1d[b] = yd[i];
      fxData.prev1w[b] = wk[i];
    });
    const now = new Date();
    document.getElementById('forex-updated').textContent =
      `最終更新 ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    renderForex();
  } catch (e) {
    document.getElementById('forex-cards').innerHTML =
      `<div class="loader" style="padding:8px;width:100%">取得失敗: ${h(e.message)}</div>`;
  }
}

function renderForex() {
  if (!fxData.latest) return;
  const prev = fxData.prev1w;
  const label = '前週比';
  const html = FX_PAIRS.map(p => {
    const cur = fxData.latest[p.base];
    const old = prev[p.base];
    if (cur == null) return `
      <div class="fx-card">
        <div class="fx-pair">${p.label}</div>
        <div class="fx-rate">—</div>
      </div>`;
    const diff = (old != null) ? cur - old : null;
    const pct = (old != null && old !== 0) ? (diff / old * 100) : null;
    const sign = diff > 0 ? '+' : '';
    const cls = diff == null ? 'flat' : diff > 0 ? 'up' : diff < 0 ? 'down' : 'flat';
    const arrow = diff == null ? '─' : diff > 0 ? '▲' : diff < 0 ? '▼' : '─';
    const changeHtml = diff != null
      ? `<div class="fx-change ${cls}">${arrow} ${sign}${diff.toFixed(2)} (${sign}${pct.toFixed(2)}%)</div>`
      : `<div class="fx-change flat">─</div>`;
    return `
      <div class="fx-card">
        <div class="fx-pair">${p.label}</div>
        <div class="fx-rate">${cur.toFixed(2)}<span>円</span></div>
        ${changeHtml}
        <div class="fx-label">${label}</div>
      </div>`;
  }).join('');
  document.getElementById('forex-cards').innerHTML = html;
}
