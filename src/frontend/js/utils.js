'use strict';

export function h(s) {
  return String(s || '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

export function isoDate(offsetDays = 0) {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}

export function enableDragScroll(el) {
  let startY = 0, startX = 0, scrollY = 0, scrollX = 0, dragging = false;

  function onDown(e) {
    dragging = true;
    startY = e.type === 'mousedown' ? e.clientY : e.touches[0].clientY;
    startX = e.type === 'mousedown' ? e.clientX : e.touches[0].clientX;
    scrollY = el.scrollTop;
    scrollX = el.scrollLeft;
    el.classList.add('dragging');
    if (e.type === 'mousedown') e.preventDefault();
  }
  function onMove(e) {
    if (!dragging) return;
    const cy = e.type === 'mousemove' ? e.clientY : e.touches[0].clientY;
    const cx = e.type === 'mousemove' ? e.clientX : e.touches[0].clientX;
    el.scrollTop = scrollY - (cy - startY);
    el.scrollLeft = scrollX - (cx - startX);
  }
  function onUp() { dragging = false; el.classList.remove('dragging'); }

  el.addEventListener('mousedown', onDown, { passive: false });
  el.addEventListener('mousemove', onMove);
  el.addEventListener('mouseup', onUp);
  el.addEventListener('mouseleave', onUp);
  el.addEventListener('touchstart', onDown, { passive: true });
  el.addEventListener('touchmove', onMove, { passive: true });
  el.addEventListener('touchend', onUp);
}
