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

  const STORAGE_KEY = 'sfgResizeCols_v2';
  const MIN_WIDTH = 32;
  const HANDLE_PX = 8;

  // Inject CSS para que el handle sea visible + hover claro
  const style = document.createElement('style');
  style.textContent = `
    .sf-rcol-h{ background: rgba(255,255,255,0); transition: background .15s; }
    .sf-rcol-h::after{
      content:''; position:absolute; right:2px; top:30%; bottom:30%;
      width:1px; background:rgba(255,255,255,.25); pointer-events:none;
    }
    .sf-rcol-h:hover{ background: rgba(176,30,30,.5); }
    .sf-rcol-h:hover::after{ background:#fff; width:2px; right:2px; }
    .sf-rcol-active{ background: rgba(176,30,30,.7) !important; }
    table.hm thead th{ box-sizing: border-box; }
  `;
  document.head.appendChild(style);

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
        const w = widths[k];
        th.style.width = w + 'px';
        th.style.minWidth = w + 'px';
        th.style.maxWidth = w + 'px';
        // Aplicar mismo width a las celdas tbody de esa columna
        applyColWidth(table, th, w);
      }
      if(th.querySelector('.sf-rcol-h')) return;
      const cs = window.getComputedStyle(th);
      if(cs.position === 'static') th.style.position = 'relative';
      th.style.userSelect = 'none';
      th.style.overflow = 'hidden';
      const handle = document.createElement('div');
      handle.className = 'sf-rcol-h';
      handle.style.cssText =
        'position:absolute;top:0;right:0;width:'+HANDLE_PX+'px;height:100%;'+
        'cursor:col-resize;z-index:10;';
      handle.title = 'Arrastrar para redimensionar · doble click para reset';
      handle.addEventListener('mousedown', e=>startResize(e, table, th));
      handle.addEventListener('dblclick', e=>resetCol(e, table, th));
      th.appendChild(handle);
    });
  }

  function applyColWidth(table, th, w){
    // Encontrar el índice de columna real considerando colspan/rowspan
    const ths = [...table.querySelectorAll('thead tr')[0].children];
    let colStart = 0;
    for(const t of ths){
      if(t === th){
        const colCount = parseInt(t.getAttribute('colspan')||'1', 10);
        // Para cada col en [colStart, colStart+colCount) setear width en tbody td
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row=>{
          const cells = row.children;
          for(let i = colStart; i < colStart + colCount && i < cells.length; i++){
            cells[i].style.minWidth = (w/colCount) + 'px';
            cells[i].style.maxWidth = (w/colCount) + 'px';
            cells[i].style.width = (w/colCount) + 'px';
          }
        });
        return;
      }
      colStart += parseInt(t.getAttribute('colspan')||'1', 10);
    }
  }

  let dragState = null;
  function startResize(e, table, th){
    e.preventDefault();
    e.stopPropagation();
    const startX = e.clientX;
    const startW = th.getBoundingClientRect().width;
    dragState = { table, th, startX, startW };
    document.body.style.cursor = 'col-resize';
    const handle = e.target;
    if(handle) handle.classList.add('sf-rcol-active');
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
    applyColWidth(dragState.table, dragState.th, w);
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
    document.querySelectorAll('.sf-rcol-active').forEach(h=>h.classList.remove('sf-rcol-active'));
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
