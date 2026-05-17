'use strict';
import { h } from './utils.js';

export async function loadNews() {
  try {
    const feeds = await (await fetch('/api/news')).json();
    const all = feeds.flatMap(f => f.items || []);

    const tHtml = all.slice(0, 35).map(it =>
      `<span class="ti">▶ ${h(it.title)}</span>`
    ).join('<span class="ti-sep">●</span>');
    document.getElementById('ticker-inner').innerHTML = tHtml + '<span class="ti-sep">●</span>' + tHtml;
  } catch (e) { }
}
