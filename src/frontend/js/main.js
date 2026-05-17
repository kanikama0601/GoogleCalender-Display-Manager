'use strict';

import { enableDragScroll } from './utils.js';
import { loadWeather } from './weather.js';
import { loadNews } from './news.js';
import { loadCalendar, initCalendarListeners } from './calendar.js';
import { loadForex } from './forex.js';

const DAY = ['日', '月', '火', '水', '木', '金', '土'];
const ETOS = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥'];
const JIKKAN = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'];

const bgA = document.getElementById('bg-a');
const bgB = document.getElementById('bg-b');
let bgSide = 'a', bgList = [];

async function initBg() {
  try {
    const r = await fetch('/api/images');
    if (r.ok) bgList = await r.json();
  } catch { }
  if (bgList.length) showBg();
}

function showBg() {
  if (!bgList.length) return;
  const url = bgList[Math.floor(Math.random() * bgList.length)];
  const next = bgSide === 'a' ? bgB : bgA;
  const prev = bgSide === 'a' ? bgA : bgB;
  next.style.backgroundImage = `url('${url}')`;
  next.classList.add('on');
  setTimeout(() => prev.classList.remove('on'), 2100);
  bgSide = bgSide === 'a' ? 'b' : 'a';
}

function reiwaYear(y) { return y - 2018; }

function kanshi(y) {
  const jk = JIKKAN[(y - 4) % 10];
  const et = ETOS[(y - 4) % 12];
  return jk + et;
}

function tick() {
  const n = new Date();
  const y = n.getFullYear(), mo = n.getMonth() + 1, d = n.getDate();
  const hh = String(n.getHours()).padStart(2, '0');
  const mm = String(n.getMinutes()).padStart(2, '0');
  const ss = String(n.getSeconds()).padStart(2, '0');

  document.getElementById('th').textContent = hh;
  document.getElementById('tm').textContent = mm;
  document.getElementById('ts').textContent = ss;

  document.getElementById('time-sep').style.opacity = n.getSeconds() % 2 === 0 ? '1' : '0.15';

  document.getElementById('date-line').textContent =
    `${y}年 ${mo}月 ${d}日（${DAY[n.getDay()]}）`;
  document.getElementById('reiwa-line').textContent =
    `令和${reiwaYear(y)}年 / 干支 ${kanshi(y)}`;
}

// apply server-injected config
const CFG = window.MONITOR_CONFIG || {};
if (CFG.compactClock) document.body.classList.add('compact-clock');
if (CFG.compactNews) document.body.classList.add('compact-news');
if (CFG.mouseHide) document.body.classList.add('mouse-hide');

// wake lock
if (CFG.wakeLock && 'wakeLock' in navigator) {
  let wakeLock = null;
  async function acquireWakeLock() {
    try {
      wakeLock = await navigator.wakeLock.request('screen');
    } catch { }
  }
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') acquireWakeLock();
  });
  acquireWakeLock();
}

// Initialize everything
document.addEventListener('DOMContentLoaded', () => {
  tick();
  setInterval(tick, 1000);

  initBg();
  setInterval(showBg, 30000);

  loadWeather();
  loadNews();
  loadForex();
  loadCalendar();
  initCalendarListeners();

  setInterval(loadWeather, 10 * 60 * 1000);
  setInterval(loadNews, 5 * 60 * 1000);
  setInterval(loadForex, 60 * 60 * 1000);
  setInterval(loadCalendar, 5 * 60 * 1000);

  document.querySelectorAll('.drag-scroll').forEach(enableDragScroll);

  setTimeout(() => location.reload(), 6 * 60 * 60 * 1000);
});
