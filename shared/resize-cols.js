/* shared/resize-cols.js
 * Permite redimensionar columnas de las tablas hm-prov / hm-cup
 * arrastrando el borde derecho de cada <th> (como Excel).
 * Auto-aplica handlers cuando las tablas se re-renderan via MutationObserver.
 * Persiste anchos en localStorage por columna (key = headerText).
 */
(function(){
  "use strict";
  if(window.__sfResizeColsInjected) return;
  window.__sfResizeColsInjected = true;

  const STORAGE_KEY = 'sfgResizeCols_v1';
  const MIN_WIDTH = 40;
  const HANDLE_PX = 6;

  function loadWidths(){
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); }
    catch(e){ return {}; }
  }
  function saveWidths(map){
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(map)); } catch(e){}
  }

  function keyForTh(table, th){
    const tid = table.id || 'tbl';
    const txt = (th.textContent||'').trim().slice(0, 40);
    const idx = [...th.parentElement.children].indexOf(th);
    return `${tid}::${idx}::${txt}`;
  }

  function attachHandles(table){
    if(!table) return;
    const widths = loadWidths();
    const ths = table.querySelectorAll('thead th');
    ths.forEach(th=>{
      // restore saved width
      const k = keyForTh(table, th);
      if(widths[k]){
        th.style.width = widths[k] + 'px';
        th.style.minWidth = widths[k] + 'px';
        th.style.maxWidth = widths[k] + 'px';
      }
      if(th.querySelector('.sf-rcol-h')) return;  // ya tiene handle
      // posicionar relative
      const cs = window.getComputedStyle(th);
      if(cs.position === 'static') th.style.position = 'relative';
      th.style.userSelect = 'none';
      const handle = document.createElement('div');
      handle.className = 'sf-rcol-h';
      handle.style.cssText =
        'position:absolute;top:0;right:0;width:'+HANDLE_PX+'px;height:100%;'+
        'cursor:col-resize;z-index:5;background:transparent;';
      handle.title = 'Arrastrar para redimensionar';
      handle.addEventListener('mousedown', e=>startResize(e, table, th));
      handle.addEventListener('dblclick', e=>resetCol(e, table, th));
      th.appendChild(handle);
    });
  }

  let dragState = null;
  function startResize(e, table, th){
    e.preventDefault();
    e.stopPropagation();
    const startX = e.clientX;
    const startW = th.getBoundingClientRect().width;
    dragState = { table, th, startX, startW };
    document.body.style.cursor = 'col-resize';
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp, { once:true });
  }
  function onMove(e){
    if(!dragState) return;
    const dx = e.clientX - dragState.startX;
    const w = Math.max(MIN_WIDTH, Math.round(dragState.startW + dx));
    dragState.th.style.width = w + 'px';
    dragState.th.style.minWidth = w + 'px';
    dragState.th.style.maxWidth = w + 'px';
  }
  function onUp(){
    if(!dragState) return;
    const { table, th } = dragState;
    const k = keyForTh(table, th);
    const w = parseInt(th.style.width, 10);
    const widths = loadWidths();
    if(w && !isNaN(w)) widths[k] = w;
    saveWidths(widths);
    document.body.style.cursor = '';
    document.removeEventListener('mousemove', onMove);
    dragState = null;
  }
  function resetCol(e, table, th){
    e.preventDefault();
    e.stopPropagation();
    th.style.width = '';
    th.style.minWidth = '';
    th.style.maxWidth = '';
    const k = keyForTh(table, th);
    const widths = loadWidths();
    delete widths[k];
    saveWidths(widths);
  }

  function applyAll(){
    document.querySelectorAll('table.hm').forEach(attachHandles);
  }

  // MutationObserver para re-aplicar handlers despues de re-renders
  function observe(tableId){
    const t = document.getElementById(tableId);
    if(!t) return;
    const thead = t.querySelector('thead');
    if(!thead) return;
    const obs = new MutationObserver(()=>attachHandles(t));
    obs.observe(thead, { childList:true, subtree:true });
  }

  function init(){
    applyAll();
    ['hm-prov', 'hm-cup'].forEach(observe);
    // Re-apply on any window event que pueda gatillar re-render
    window.addEventListener('hashchange', applyAll);
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
