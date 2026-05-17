'use strict';
import { h } from './utils.js';

export async function loadWeather() {
  try {
    const w = await (await fetch('/api/weather')).json();
    if (w.error) throw new Error(w.error);

    document.getElementById('city-line').textContent = '📍 ' + w.city;

    document.getElementById('weather-now').innerHTML = `
      <div class="wn-row">
        <div class="wn-icon">${w.icon}</div>
        <div>
          <div class="wn-temp">${w.temp}<span class="wn-unit">°C</span></div>
          <div class="wn-desc">${h(w.desc)}</div>
          <div class="wn-feels">体感 ${w.feels}°C</div>
        </div>
      </div>
      <div class="wn-stats">
        <div class="wn-stat"><div class="wn-stat-l">湿度</div><div class="wn-stat-v">${w.humidity}<span class="wn-stat-u">%</span></div></div>
        <div class="wn-stat"><div class="wn-stat-l">風速</div><div class="wn-stat-v">${w.wind}<span class="wn-stat-u">km/h</span></div></div>
        <div class="wn-stat"><div class="wn-stat-l">降水</div><div class="wn-stat-v">${w.precip}<span class="wn-stat-u">mm</span></div></div>
      </div>`;

    document.getElementById('hourly-strip').innerHTML =
      (w.hourly || []).map(x => `
        <div class="hc">
          <div class="hc-t">${x.time}</div>
          <div class="hc-i">${x.icon}</div>
          <div class="hc-tp">${x.temp}°</div>
        </div>`).join('');

  } catch (e) {
    document.getElementById('weather-now').innerHTML =
      `<div class="loader">天気取得失敗<br><small>${h(e.message)}</small></div>`;
  }
}
