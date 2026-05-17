'use strict';
import { h } from './utils.js';

let _allEvents = {};
let _gridYear = 0;
let _gridMonth = 0;
let _selDate = null;

export async function loadCalendar() {
  try {
    const todayData = await (await fetch('/api/calendar?days=1')).json();
    if (todayData.error) {
      throw new Error(todayData.error);
    }
    renderTodayCalendar(todayData);

    const now = new Date();
    _gridYear = now.getFullYear();
    _gridMonth = now.getMonth();

    await fetchGridEvents(_gridYear, _gridMonth);
  } catch (e) {
    const err = `<div class="loader">予定取得失敗: ${h(e.message)}<br><small>credentials.jsonがルートディレクトリに必要です</small></div>`;
    document.getElementById('calendar-today-list').innerHTML = err;
    document.getElementById('cal-grid').innerHTML = err;
  }
}

function renderTodayCalendar(events) {
  const list = document.getElementById('calendar-today-list');
  if (!events || events.length === 0) {
    list.innerHTML = '<div class="loader" style="animation:none">今日の予定はありません</div>';
    return;
  }
  list.innerHTML = events.map(ev => {
    const start = new Date(ev.start);
    const end = new Date(ev.end);
    const timeStr = ev.start.length > 10
      ? `${String(start.getHours()).padStart(2, '0')}:${String(start.getMinutes()).padStart(2, '0')} – ${String(end.getHours()).padStart(2, '0')}:${String(end.getMinutes()).padStart(2, '0')}`
      : '終日';
    return `
      <div class="cal-card">
        <div class="cal-header-row">
          <div class="cal-time">${timeStr}</div>
          ${ev.location ? `<div class="cal-loc">📍 ${h(ev.location)}</div>` : ''}
        </div>
        <div class="cal-summary">${h(ev.summary)}</div>
        ${ev.description ? `<div class="cal-desc">${h(ev.description)}</div>` : ''}
      </div>`;
  }).join('');
}

async function fetchGridEvents(year, month) {
  document.getElementById('cal-month-title').textContent = `${year}年 ${month + 1}月`;
  document.getElementById('cal-grid').innerHTML = '<div class="loader">予定を読み込み中...</div>';

  try {
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);

    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - firstDay.getDay());

    const totalCells = lastDay.getDay() === 6 && firstDay.getDay() === 0 ? 42 :
      (firstDay.getDay() + lastDay.getDate() > 35 ? 42 : 35);

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const startOfGrid = new Date(startDate);
    startOfGrid.setHours(0, 0, 0, 0);

    const diffMs = startOfGrid.getTime() - today.getTime();
    const startOffset = Math.round(diffMs / (1000 * 60 * 60 * 24));

    const url = `/api/calendar?days=${totalCells}&start_offset=${startOffset}`;
    const events = await (await fetch(url)).json();

    if (events.error) {
      throw new Error(events.error);
    }

    _allEvents = {};
    if (events && events.length) {
      events.forEach(ev => {
        const d = ev.start.slice(0, 10);
        if (!_allEvents[d]) _allEvents[d] = [];
        _allEvents[d].push(ev);
      });
    }

    renderGrid();
  } catch (e) {
    document.getElementById('cal-grid').innerHTML = `<div class="loader">予定取得失敗: ${h(e.message)}</div>`;
  }
}

function renderGrid() {
  const today = new Date();
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

  document.getElementById('cal-month-title').textContent = `${_gridYear}年 ${_gridMonth + 1}月`;

  const firstDay = new Date(_gridYear, _gridMonth, 1);
  const lastDay = new Date(_gridYear, _gridMonth + 1, 0);
  const startDate = new Date(firstDay);
  startDate.setDate(startDate.getDate() - firstDay.getDay());

  const cells = [];
  const cur = new Date(startDate);
  const totalCells = lastDay.getDay() === 6 && firstDay.getDay() === 0 ? 42 :
    (firstDay.getDay() + lastDay.getDate() > 35 ? 42 : 35);

  for (let i = 0; i < totalCells; i++) {
    const ds = `${cur.getFullYear()}-${String(cur.getMonth() + 1).padStart(2, '0')}-${String(cur.getDate()).padStart(2, '0')}`;
    const isThisMonth = cur.getMonth() === _gridMonth;
    const isToday = ds === todayStr;
    const evs = _allEvents[ds] || [];
    const hasEv = evs.length > 0;

    const labels = evs.slice(0, 3).map(ev => {
      const start = new Date(ev.start);
      const timePrefix = ev.start.length > 10 ? `${start.getHours()}:${String(start.getMinutes()).padStart(2, '0')}: ` : '';
      const isPast = ds < todayStr;
      return `<div class="cal-ev-label${ev.start.length <= 10 ? ' allday' : ''}${isPast ? ' past' : ''}">${timePrefix}${h(ev.summary)}</div>`;
    }).join('');

    cells.push(`
      <div class="cal-cell${isThisMonth ? '' : ' other-month'}${isToday ? ' today' : ''}${hasEv ? ' has-event' : ''}"
           data-date="${ds}">
        <div class="cal-cell-day">${cur.getDate()}</div>
        ${hasEv ? `<div class="cal-cell-titles">${labels}</div>` : ''}
      </div>`);
    cur.setDate(cur.getDate() + 1);
  }

  document.getElementById('cal-grid').innerHTML = cells.join('');
}

export function initCalendarListeners() {
  document.getElementById('cal-prev').addEventListener('click', () => {
    _gridMonth--;
    if (_gridMonth < 0) { _gridMonth = 11; _gridYear--; }
    _selDate = null;
    fetchGridEvents(_gridYear, _gridMonth);
  });
  document.getElementById('cal-next').addEventListener('click', () => {
    _gridMonth++;
    if (_gridMonth > 11) { _gridMonth = 0; _gridYear++; }
    _selDate = null;
    fetchGridEvents(_gridYear, _gridMonth);
  });
}
