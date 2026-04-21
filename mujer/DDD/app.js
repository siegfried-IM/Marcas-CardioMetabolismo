// DDD Línea Mujer — app.js (adaptado del DDD Respiratorio Siegfried-BI)
// Fuente de datos: window.OTC_DATA.dddGineco (generado desde Producto-Molécula-ATC-provincia)
const ROOT = window.OTC_DATA || {};
const DD = ROOT.dddGineco || {};
const MKT_MAP = DD.families || {};
const MONTHS = DD.months || [];

function hasData(m){
  const v = MKT_MAP[m];
  if (!v) return false;
  const b = v?.molecule?.all;
  return b && (b.monthly || []).some(r => Number(r?.total || 0) > 0);
}
const ORDERED_MARKETS = (DD.order || Object.keys(MKT_MAP)).filter(m => MKT_MAP[m] && hasData(m));
const PARAMS = new URLSearchParams(location.search);
const MONTH_INDEX = {Ene:0,Feb:1,Mar:2,Abr:3,May:4,Jun:5,Jul:6,Ago:7,Sep:8,Oct:9,Nov:10,Dic:11};
const SIE = '#b01e1e';
const SEL = '#2563EB';
const RC  = ['#b01e1e','#2563EB','#7C3AED','#D97706','#16A34A','#DB2777','#0891B2','#EA580C','#6D28D9','#0D9488','#F59E0B','#4F46E5'];
const BC  = ['#2563EB','#7C3AED','#D97706','#16A34A','#DB2777','#0891B2','#EA580C','#6D28D9','#0D9488','#4F46E5','#CA8A04','#0369A1','#059669','#B91C1C','#F59E0B'];

function defaultMarket(){
  const q = PARAMS.get('market');
  if (q && MKT_MAP[q]) return q;
  return ORDERED_MARKETS[0];
}

let cur = defaultMarket();
let cmp = PARAMS.get('compare') || 'molecule';
if (!['molecule','atc'].includes(cmp)) cmp = 'molecule';
let selRegs = (PARAMS.get('regions') || '').split('|').filter(Boolean);
let selB = PARAMS.get('product') || null;
let chs = {};
let sC = 'total';
let sD = 'desc';
let ddOpen = false;
let ztSort = { col:'ms', dir:-1 };

function fmt(n){ return Number(n || 0).toLocaleString('es-AR'); }
function fms(n){ return Number(n || 0).toFixed(1) + '%'; }
function fk(n){ const v = Number(n || 0); return v >= 1e6 ? (v/1e6).toFixed(1)+'M' : v >= 1e3 ? (v/1e3).toFixed(1)+'k' : fmt(v); }
function mParts(key){ const [m,y] = String(key||'').split('-'); return {m, y:Number(y||0)}; }
function monthShort(key){ const p=mParts(key); return p.y?`${p.m}'${String(p.y).slice(-2)}`:key; }
function monthLabel(key){ const p=mParts(key); return p.y?`${p.m} ${p.y}`:key; }
function quarterKey(key){ const p=mParts(key); const q=Math.floor((MONTH_INDEX[p.m]||0)/3)+1; return `Q${q}-${p.y}`; }
function qParts(key){ const [q,y]=String(key||'').split('-'); return {q, y:Number(y||0)}; }
function validRegion(n){ return !!n && n !== '-'; }
function marketObj(){
  const fv = MKT_MAP[cur] || {};
  return fv?.[cmp]?.all || fv?.molecule?.all || null;
}
function marketMonths(mk){ return MONTHS.filter(m => mk?.regionsByMonth?.[m]); }
function latestMonth(mk){ return mk?.latestMonth || marketMonths(mk).slice(-1)[0] || MONTHS.slice(-1)[0] || ''; }
function regionRows(mk, m){ return ((mk?.regionsByMonth || {})[m] || []).filter(r => validRegion(r.name)); }
function productRows(mk, m){ return ((mk?.productsByMonth || {})[m] || []).filter(r => r && r.product); }
function regionRow(mk, reg, m){ return regionRows(mk, m).find(r => r.name === reg) || { name:reg, total:0, sie:0, share:0 }; }
function natRow(mk, m){
  const rows = regionRows(mk, m);
  const total = rows.reduce((s,r)=>s+Number(r.total||0),0);
  const sie   = rows.reduce((s,r)=>s+Number(r.sie||0),0);
  return { total, sie, ms: total>0 ? +(sie/total*100).toFixed(1) : 0 };
}
function activeReg(){ return selRegs.length === 1 ? selRegs[0] : '__NAC__'; }
function activeLabel(){ return selRegs.length === 1 ? selRegs[0].replace(/^_/, '') : 'Nacional'; }
function getSieMS(mk, reg){
  return marketMonths(mk).map(m => reg === '__NAC__' ? natRow(mk, m).ms : Number(regionRow(mk, reg, m).share || 0));
}
function getProdMonthly(mk, prod){
  return marketMonths(mk).map(m => {
    const row = productRows(mk, m).find(p => p.product === prod);
    return { month:m, units:Number(row?.units||0), ms:Number(row?.share||0) };
  });
}
function getQuarterlySieMS(mk, reg){
  const g = {};
  marketMonths(mk).forEach(m => {
    const q = quarterKey(m);
    const row = reg === '__NAC__' ? natRow(mk, m) : regionRow(mk, reg, m);
    if (!g[q]) g[q] = { total:0, sie:0 };
    g[q].total += Number(row.total||0);
    g[q].sie   += Number(row.sie||0);
  });
  return Object.keys(g).sort((a,b) => {
    const pa=qParts(a), pb=qParts(b);
    return pa.y*10 + Number(pa.q.slice(1)) - (pb.y*10 + Number(pb.q.slice(1)));
  }).map(q => ({ key:q, ms: g[q].total>0 ? +(g[q].sie/g[q].total*100).toFixed(1) : 0 }));
}
function getQuarterlyProdMS(mk, prod){
  const g = {};
  marketMonths(mk).forEach(m => {
    const q = quarterKey(m);
    const row = productRows(mk, m).find(p => p.product === prod);
    if (!g[q]) g[q] = { units:0, total:0 };
    g[q].units += Number(row?.units||0);
    g[q].total += natRow(mk, m).total;
  });
  return Object.keys(g).sort((a,b) => {
    const pa=qParts(a), pb=qParts(b);
    return pa.y*10 + Number(pa.q.slice(1)) - (pb.y*10 + Number(pb.q.slice(1)));
  }).map(q => ({ key:q, ms: g[q].total>0 ? +(g[q].units/g[q].total*100).toFixed(1) : 0 }));
}
function topRegionsByLatest(mk, n){
  return [...regionRows(mk, latestMonth(mk))].sort((a,b)=>Number(b.total||0)-Number(a.total||0)).slice(0,n).map(r=>r.name);
}
function competitorRows(mk){ return productRows(mk, latestMonth(mk)).filter(r => !r.isSie); }
function ensureSelection(){
  const mk = marketObj();
  const regs = regionRows(mk, latestMonth(mk)).map(r=>r.name);
  const prods = productRows(mk, latestMonth(mk)).map(r=>r.product);
  selRegs = selRegs.filter(r => regs.includes(r));
  if (selB && !prods.includes(selB)) selB = null;
}
function syncUrl(){
  const u = new URL(location.href);
  u.searchParams.set('market', cur);
  u.searchParams.set('compare', cmp);
  if (selB) u.searchParams.set('product', selB); else u.searchParams.delete('product');
  if (selRegs.length) u.searchParams.set('regions', selRegs.join('|')); else u.searchParams.delete('regions');
  history.replaceState({}, '', u);
}
function lineColor(i){ return BC[i % BC.length]; }
function destroyChart(k){ if (chs[k]) { chs[k].destroy(); chs[k] = null; } }

function toggleDD(){
  ddOpen = !ddOpen;
  document.getElementById('regDD').classList.toggle('open', ddOpen);
  if (ddOpen) {
    document.getElementById('regQ').value = '';
    buildRegList();
    document.getElementById('regQ').focus();
  }
}
function closeDD(){
  ddOpen = false;
  document.getElementById('regDD').classList.remove('open');
}
document.addEventListener('click', e => {
  const w = document.getElementById('regWrap');
  if (ddOpen && w && !w.contains(e.target)) closeDD();
});
function buildRegList(){
  const mk = marketObj();
  const latest = latestMonth(mk);
  const q = (document.getElementById('regQ')?.value || '').toLowerCase();
  const rows = [...regionRows(mk, latest)]
    .filter(r => r.name.replace(/^_/, '').toLowerCase().includes(q))
    .sort((a,b) => Number(b.total||0) - Number(a.total||0));
  const list = document.getElementById('regList');
  list.innerHTML = '';
  rows.forEach(r => {
    const d = document.createElement('div');
    const sel = selRegs.includes(r.name);
    d.className = 'reg-opt' + (sel ? ' sel' : '');
    d.innerHTML = `<div class="reg-chk">${sel ? '✓' : ''}</div><span>${r.name.replace(/^_/, '')}</span>`;
    d.onclick = e => { e.stopPropagation(); toggleReg(r.name); };
    list.appendChild(d);
  });
}
function filterRegs(){ buildRegList(); }
function toggleReg(r){
  const i = selRegs.indexOf(r);
  if (i >= 0) selRegs.splice(i, 1); else selRegs.push(r);
  onRegsChanged();
}
function clrRegs(){ selRegs = []; onRegsChanged(); closeDD(); }
function selTop7(){ selRegs = topRegionsByLatest(marketObj(), 7); onRegsChanged(); }
function onRegsChanged(){ buildRegList(); updBtnText(); updTags(); render(); }
function updBtnText(){
  const b = document.getElementById('regBtnText');
  if (!b) return;
  if (selRegs.length === 0) b.textContent = 'Nacional (todas)';
  else if (selRegs.length === 1) b.textContent = selRegs[0].replace(/^_/, '');
  else b.textContent = selRegs.length + ' regiones seleccionadas';
}
function updTags(){
  const el = document.getElementById('rtags');
  if (!el) return;
  if (selRegs.length === 0) { el.innerHTML = ''; return; }
  el.innerHTML = selRegs.map(r => `<div class="rtag">${r.replace(/^_/, '')}<span class="x" onclick="rmReg('${r}')">✕</span></div>`).join('');
}
function rmReg(r){ selRegs = selRegs.filter(x => x !== r); onRegsChanged(); }

function renderHero(mk){
  const latest = latestMonth(mk);
  const rl = activeLabel();
  const cL = cmp === 'atc' ? 'mismo ATC' : 'misma molécula';
  document.querySelector('.hero-sub').textContent = `Market Share por Región · ${cur} · ${cL} · corte ${monthLabel(latest)} · vista ${rl}`;
}

function lineOptions(legendFont){
  return {
    responsive:true,
    maintainAspectRatio:false,
    interaction:{mode:'index', intersect:false},
    plugins:{
      legend:{position:'bottom', labels:{usePointStyle:true, pointStyle:'circle', padding:10, font:{size:legendFont, weight:'500'}}},
      tooltip:{backgroundColor:'#1A1A1A', padding:10, cornerRadius:6, mode:'index', intersect:false, callbacks:{label:c=>c.dataset.label+': '+c.parsed.y.toFixed(1)+'%'}}
    },
    scales:{
      y:{ticks:{callback:v=>v.toFixed(1)+'%', font:{size:10.5}, color:'#737373'}, grid:{color:'#E5E5E522'}, border:{display:false}},
      x:{ticks:{font:{size:10.5, weight:'500'}, color:'#737373'}, grid:{display:false}, border:{display:false}}
    }
  };
}

function rKPI(mk){
  const ar = activeReg();
  const latest = latestMonth(mk);
  const first = marketMonths(mk)[0];
  const latestRow = ar === '__NAC__' ? natRow(mk, latest) : regionRow(mk, ar, latest);
  const firstRow  = ar === '__NAC__' ? natRow(mk, first)  : regionRow(mk, ar, first);
  const latestMs = Number(ar === '__NAC__' ? latestRow.ms : latestRow.share || 0);
  const firstMs  = Number(ar === '__NAC__' ? firstRow.ms  : firstRow.share  || 0);
  const diff = +(latestMs - firstMs).toFixed(1);
  const lbl = activeLabel();
  let k4 = '';
  if (ar === '__NAC__') {
    const rows = regionRows(mk, latest);
    const above = rows.filter(r => Number(r.share||0) > latestMs).length;
    k4 = `<div class="kc c4"><div class="kh">REGIONES SOBRE PROMEDIO</div><div class="kv purple">${above}<span style="font-size:15px;color:var(--t4)">/${rows.length}</span></div><div class="kd">MS% > ${fms(latestMs)} nacional</div></div>`;
  } else {
    const nat = natRow(mk, latest).ms;
    const gap = +(latestMs - nat).toFixed(1);
    k4 = `<div class="kc c4"><div class="kh">VS NACIONAL</div><div class="kv purple">${gap>=0?'+':''}${gap}pp</div><div class="kd">Nacional: ${fms(nat)} · Región: ${fms(latestMs)}</div></div>`;
  }
  document.getElementById('kr').innerHTML = `
    <div class="kc c1"><div class="kh">MS% · ${lbl.toUpperCase()}</div><div class="kv red">${fms(latestMs)}</div><div class="kd">${cur}<br>${fmt(latestRow.total)} u. mercado</div></div>
    <div class="kc c2"><div class="kh">UNIDADES SIE · ${monthLabel(latest).toUpperCase()}</div><div class="kv blue">${fk(latestRow.sie)}</div><div class="kd">${mk.family}<br>de ${fk(latestRow.total)} u.</div></div>
    <div class="kc c3"><div class="kh">MS% ÚLTIMO CORTE · ${lbl.toUpperCase()}</div><div class="kv green">${fms(latestMs)}</div><div class="kd">${monthLabel(latest)} · <span style="color:${diff>=0?'var(--green)':'var(--red)'}">${diff>=0?'+':''}${diff}pp</span> vs ${monthLabel(first)}</div></div>${k4}`;
}

function rBF(mk){
  const ch = document.getElementById('fcs');
  ch.innerHTML = '';
  competitorRows(mk).sort((a,b)=>Number(b.units||0)-Number(a.units||0)).forEach((r, i) => {
    const d = document.createElement('div');
    d.className = 'bc' + (selB === r.product ? ' a' : '');
    d.innerHTML = `<span class="d" style="background:${lineColor(i)}"></span>${r.product}`;
    d.onclick = () => { selB = selB === r.product ? null : r.product; render(); };
    ch.appendChild(d);
  });
  document.getElementById('fcl').style.display = selB ? 'block' : 'none';
}
function clrB(){ selB = null; render(); }

function rC1(mk){
  destroyChart('c1');
  const ar = activeReg(), rl = activeLabel();
  const labels = marketMonths(mk).map(monthShort);
  const ds = [{
    label:'Siegfried', data:getSieMS(mk, ar),
    borderColor:SIE, backgroundColor:SIE+'15', fill:true, tension:.35,
    pointRadius:4, pointBackgroundColor:'#fff', pointBorderColor:SIE, pointBorderWidth:2,
    pointHoverRadius:6, borderWidth:2.5, order:0
  }];
  if (selB) {
    const p = getProdMonthly(mk, selB);
    ds.push({
      label: ar === '__NAC__' ? selB : `${selB} (nac.)`,
      data: p.map(x=>x.ms),
      borderColor:SEL, backgroundColor:SEL+'10', fill:false, tension:.35,
      pointRadius:4, pointBackgroundColor:'#fff', pointBorderColor:SEL, pointBorderWidth:2,
      pointHoverRadius:6, borderDash: ar === '__NAC__' ? [] : [7,4], borderWidth:2.5, order:1
    });
  }
  document.getElementById('s1').textContent = selB ? `Siegfried vs ${selB} · ${rl}` : `Siegfried · ${rl}`;
  chs.c1 = new Chart(document.getElementById('c1').getContext('2d'), { type:'line', data:{labels, datasets:ds}, options:lineOptions(10.5) });
}

function rC2(mk){
  destroyChart('c2');
  const labels = marketMonths(mk).map(monthShort);
  document.getElementById('s2').textContent = 'Top competidores · Nacional';
  const top = competitorRows(mk).sort((a,b)=>Number(b.units||0)-Number(a.units||0)).slice(0,8).map(r=>r.product);
  if (selB && !top.includes(selB)) top[top.length-1] = selB;
  const ds = [{
    label:'Siegfried', data:getSieMS(mk, '__NAC__'),
    borderColor:SIE, backgroundColor:'transparent', tension:.3,
    pointRadius:5, pointBackgroundColor:'#fff', pointBorderColor:SIE, pointBorderWidth:2.5,
    borderWidth:3, pointHoverRadius:5, order:0
  }];
  top.forEach((p, i) => {
    ds.push({
      label:p, data:getProdMonthly(mk, p).map(x=>x.ms),
      borderColor: p === selB ? SEL : lineColor(i),
      backgroundColor:'transparent', tension:.3,
      pointRadius: p === selB ? 5 : 2.5,
      pointBackgroundColor: p === selB ? '#fff' : lineColor(i),
      pointBorderColor: p === selB ? SEL : lineColor(i),
      pointBorderWidth: p === selB ? 2.5 : 1,
      borderWidth: p === selB ? 3 : 1.2, pointHoverRadius:5, order:1
    });
  });
  chs.c2 = new Chart(document.getElementById('c2').getContext('2d'), { type:'line', data:{labels, datasets:ds}, options:lineOptions(9.5) });
}

function rC3(mk){
  destroyChart('c3');
  const regs = selRegs.length ? [...selRegs] : topRegionsByLatest(mk, 7);
  const qBase = getQuarterlySieMS(mk, '__NAC__');
  const ds = regs.map((r, i) => ({
    label:r.replace(/^_/, ''),
    data:getQuarterlySieMS(mk, r).map(x=>x.ms),
    borderColor:RC[i%RC.length], backgroundColor:'transparent', tension:.3,
    pointRadius:5, pointBackgroundColor:'#fff', pointBorderColor:RC[i%RC.length],
    pointBorderWidth:2.5, borderWidth:2.5, pointHoverRadius:7
  }));
  ds.push({
    label:'Nacional', data:qBase.map(x=>x.ms),
    borderColor:'#1A1A1A', borderDash:[5,3], backgroundColor:'transparent', tension:.3,
    pointRadius:3, pointBackgroundColor:'#1A1A1A', pointBorderColor:'#1A1A1A',
    borderWidth:1.5, pointHoverRadius:5
  });
  if (selB) {
    ds.push({
      label:`${selB} (producto)`, data:getQuarterlyProdMS(mk, selB).map(x=>x.ms),
      borderColor:SEL, borderDash:[8,4], backgroundColor:'transparent', tension:.3,
      pointRadius:5, pointBackgroundColor:'#fff', pointBorderColor:SEL, pointBorderWidth:2.5,
      borderWidth:2.5, pointHoverRadius:7
    });
  }
  document.getElementById('s3').textContent = selRegs.length ? (selRegs.length === 1 ? selRegs[0].replace(/^_/, '') : selRegs.length + ' regiones seleccionadas') : 'Top 7 regiones por volumen';
  chs.c3 = new Chart(document.getElementById('c3').getContext('2d'), {
    type:'line', data:{ labels:qBase.map(x=>x.key), datasets:ds },
    options:{
      ...lineOptions(10.5),
      scales:{
        y:{ticks:{callback:v=>v.toFixed(1)+'%', font:{size:10.5}, color:'#737373'}, grid:{color:'#E5E5E522'}, border:{display:false}},
        x:{ticks:{font:{size:11, weight:'600'}, color:'#525252'}, grid:{display:false}, border:{display:false}}
      }
    }
  });
}

function rComp(mk){
  const months = marketMonths(mk);
  const latest = months[months.length-1];
  const prev = months[months.length-2] || latest;
  const nLat = natRow(mk, latest);
  const nPrev = natRow(mk, prev);
  const rows = [{ name:'Siegfried', ms:nLat.ms, units:nLat.sie, var:+(nLat.ms - nPrev.ms).toFixed(2), sie:true }];
  competitorRows(mk).forEach(r => {
    const pr = productRows(mk, prev).find(p => p.product === r.product);
    rows.push({ name:r.product, ms:Number(r.share||0), units:Number(r.units||0), var:+(Number(r.share||0) - Number(pr?.share||0)).toFixed(2), sie:false });
  });
  rows.sort((a,b) => (b.sie - a.sie) || (Number(b.units||0) - Number(a.units||0)));
  const maxMs = Math.max(...rows.map(r=>r.ms), 1);
  document.getElementById('cpe').textContent = `PRODUCTOS NACIONALES · ${monthLabel(latest).toUpperCase()}`;
  document.getElementById('cbo').innerHTML = rows.map((r, i) => {
    const hl = selB === r.name;
    const vc = r.var > 0 ? 'p' : r.var < 0 ? 'n' : 'z';
    const vs = r.var > 0 ? '+' : '';
    const bw = Math.max(r.ms/maxMs*100, 1);
    return `<tr style="${hl?'background:#EFF6FF;font-weight:600':r.sie?'background:#FEF2F2':''}"><td class="rk">${i+1}</td>
      <td><div class="cbb"><div class="cl ${r.sie?'s':'o'}"></div>${r.name}${r.sie?' <span class="st">SIE</span>':''}</div></td>
      <td class="r mn">${r.ms.toFixed(1)}%</td><td class="shs"><div class="sb"><div class="sf ${r.sie?'s':'o'}" style="width:${bw}%"></div></div></td>
      <td class="r un">${fmt(r.units)}</td><td class="r"><span class="vb ${vc}">${vs}${r.var.toFixed(2)}pp</span></td></tr>`;
  }).join('');
}

function rTbl(mk){
  const latest = latestMonth(mk);
  let rows = regionRows(mk, latest).map(r => ({ region:r.name.replace(/^_/, ''), rr:r.name, total:Number(r.total||0), sie:Number(r.sie||0), ms:Number(r.share||0) }));
  rows.sort((a,b) => {
    if (sC === 'region') return sD === 'asc' ? a.region.localeCompare(b.region, 'es') : b.region.localeCompare(a.region, 'es');
    return sD === 'asc' ? a[sC] - b[sC] : b[sC] - a[sC];
  });
  const maxMs = Math.max(...rows.map(r=>r.ms), 1);
  const nMs = natRow(mk, latest).ms;
  let html = `<table class="rt2"><thead><tr><th onclick="doS('region')">#</th><th onclick="doS('region')">Región ↕</th><th onclick="doS('ms')">MS% ↕</th><th onclick="doS('sie')">U. Siegfried ↕</th><th onclick="doS('total')">U. Mercado ↕</th><th>vs Nac.</th></tr></thead><tbody>`;
  rows.forEach((r, i) => {
    const diff = +(r.ms - nMs).toFixed(1);
    const bw = Math.max(r.ms/maxMs*100, 2);
    const act = selRegs.includes(r.rr);
    html += `<tr style="${act?'background:#FEF2F2;font-weight:700;':''}" onclick="tglRegFromTbl('${r.rr}')"><td class="rk">${i+1}</td><td style="font-weight:600">${r.region}</td><td><div class="mbc"><div class="mmb ${r.ms>=nMs?'hi':'lo'}" style="width:${bw}%"></div><span class="mv">${r.ms.toFixed(1)}%</span></div></td><td class="uv">${fmt(r.sie)}</td><td class="uv">${fmt(r.total)}</td><td><span class="badge ${diff>=0?'up':'down'}">${diff>=0?'+':''}${diff}pp</span></td></tr>`;
  });
  html += '</tbody></table>';
  document.getElementById('tw').innerHTML = html;
}
function tglRegFromTbl(r){ toggleReg(r); }
function doS(c){ if (sC === c) sD = sD === 'asc' ? 'desc' : 'asc'; else { sC = c; sD = c === 'region' ? 'asc' : 'desc'; } rTbl(marketObj()); }

const PROVS = [
  {id:'jujuy', pts:'97,6 131,6 125,44 97,38', zones:['JUJUY']},
  {id:'salta', pts:'97,6 161,6 169,34 153,70 97,38', zones:['SALTA']},
  {id:'formosa', pts:'161,6 223,6 216,58 161,58', zones:['FORMOSA']},
  {id:'misiones', pts:'223,6 281,16 279,72 252,96 221,70', zones:['POSADAS']},
  {id:'chaco', pts:'161,58 216,58 207,102 188,114 161,108', zones:['RESISTENCIA']},
  {id:'tucuman', pts:'97,68 130,68 121,100 94,94', zones:['TUCUMAN']},
  {id:'corrientes', pts:'161,58 207,102 252,96 240,128 218,134 200,112 161,108', zones:['CORRIENTES']},
  {id:'catamarca', pts:'80,70 97,68 94,94 78,116 58,114 56,86', zones:['CATAMARCA']},
  {id:'santiago', pts:'130,68 161,68 157,130 139,134 121,100', zones:['SANTIAGO DEL ESTERO']},
  {id:'entre_r', pts:'200,112 218,134 240,128 242,160 236,196 206,196 194,150', zones:['PARANA','CONCORDIA']},
  {id:'larioja', pts:'56,86 78,116 74,160 50,158 46,120', zones:['LA RIOJA']},
  {id:'sanjuan', pts:'36,104 80,104 78,168 48,170 34,150', zones:['SAN JUAN']},
  {id:'cordoba', pts:'78,108 157,108 157,198 78,200', zones:['CORDOBA','RIO IV Y ALREDEDORES','SAN FCO-ESTE Y NORTE']},
  {id:'santafe', pts:'157,94 196,94 200,196 157,196', zones:['ROSARIO','SANTA FE','RAFAELA-NTE SANTA FE']},
  {id:'mendoza', pts:'32,150 78,150 76,196 56,220 30,210 30,184', zones:['MENDOZA','SAN RAFAEL']},
  {id:'sanluis', pts:'78,154 120,154 118,200 78,204', zones:['SAN LUIS']},
  {id:'bsas', pts:'138,196 236,196 256,254 240,304 203,312 144,312 124,284 120,228', zones:['AZUL-OLAVARRIA-TANDIL','BAHIA BLANCA','JUNIN-CHIVILCOY-PERGAMINO','M.DEL PLATA','BARADERO-SAN PEDRO-RAMALLO-SAN NICOLAS','LUJAN Y ALREDEDORES','LA PLATA','ZARATE - CAMPANA','PILAR - ESCOBAR']},
  {id:'gba', pts:'202,192 240,192 238,208 202,208', zones:['_CAPITAL FEDERAL','_SUBURBANO NORTE','_SUBURBANO OESTE','_SUBURBANO SUR']},
  {id:'lapampa', pts:'60,196 120,196 124,284 88,296 58,268 56,222', zones:['SANTA ROSA']},
  {id:'neuquen', pts:'28,238 78,238 76,310 28,312', zones:['NEUQUEN']},
  {id:'rionegro', pts:'28,312 158,312 148,358 28,360', zones:['RIO NEGRO']},
  {id:'chubut', pts:'26,360 130,360 126,452 26,454', zones:['TRELEW','COMODORO RIVADAVIA']},
  {id:'santacruz', pts:'24,430 106,430 104,500 24,502', zones:['SANTA CRUZ']},
  {id:'tdf', pts:'42,478 104,478 102,506 42,506', zones:['TIERRA DEL FUEGO']}
];
const ZPOS = {
  '_CAPITAL FEDERAL':{x:224,y:200}, '_SUBURBANO NORTE':{x:216,y:194},
  '_SUBURBANO OESTE':{x:210,y:200}, '_SUBURBANO SUR':{x:218,y:206},
  'LA PLATA':{x:230,y:208}, 'ZARATE - CAMPANA':{x:216,y:190}, 'PILAR - ESCOBAR':{x:212,y:194}, 'LUJAN Y ALREDEDORES':{x:206,y:198},
  'BARADERO-SAN PEDRO-RAMALLO-SAN NICOLAS':{x:198,y:182}, 'JUNIN-CHIVILCOY-PERGAMINO':{x:180,y:196}, 'M.DEL PLATA':{x:238,y:250},
  'AZUL-OLAVARRIA-TANDIL':{x:194,y:240}, 'BAHIA BLANCA':{x:158,y:264}, 'ROSARIO':{x:182,y:168}, 'SANTA FE':{x:184,y:146},
  'RAFAELA-NTE SANTA FE':{x:168,y:142}, 'SAN FCO-ESTE Y NORTE':{x:162,y:144}, 'CORDOBA':{x:134,y:146}, 'RIO IV Y ALREDEDORES':{x:124,y:168},
  'PARANA':{x:190,y:148}, 'CONCORDIA':{x:228,y:146}, 'POSADAS':{x:262,y:84}, 'CORRIENTES':{x:212,y:88}, 'RESISTENCIA':{x:204,y:86},
  'FORMOSA':{x:222,y:64}, 'SALTA':{x:110,y:44}, 'JUJUY':{x:113,y:30}, 'TUCUMAN':{x:110,y:72}, 'SANTIAGO DEL ESTERO':{x:134,y:90},
  'CATAMARCA':{x:108,y:98}, 'LA RIOJA':{x:92,y:114}, 'SAN JUAN':{x:66,y:140}, 'MENDOZA':{x:62,y:170}, 'SAN RAFAEL':{x:70,y:192},
  'SAN LUIS':{x:96,y:176}, 'SANTA ROSA':{x:128,y:228}, 'NEUQUEN':{x:50,y:270}, 'RIO NEGRO':{x:144,y:296}, 'TRELEW':{x:110,y:332},
  'COMODORO RIVADAVIA':{x:76,y:372}, 'SANTA CRUZ':{x:60,y:434}, 'TIERRA DEL FUEGO':{x:68,y:480}
};
// Rampa de color: gris claro -> bordó oscuro -> rojo Siegfried
function zoneColor(pct){
  const p = Math.min(Math.max(pct, 0), 1);
  if (p < 0.5) {
    const t = p * 2;
    return `rgb(${Math.round(203+(75-203)*t)},${Math.round(213+(22-213)*t)},${Math.round(225+(24-225)*t)})`;
  }
  const t = (p-0.5)*2;
  return `rgb(${Math.round(75+(176-75)*t)},${Math.round(22+(30-22)*t)},${Math.round(24+(30-24)*t)})`;
}
function highlightZone(r){
  document.querySelectorAll('[data-zone]').forEach(el => {
    const m = el.dataset.zone === r;
    el.setAttribute('fill-opacity', m ? '1' : '0.25');
    el.setAttribute('stroke-width', m ? '1.8' : '0.5');
    el.setAttribute('stroke-opacity', m ? '0.9' : '0.2');
  });
}
function clearHighlight(){
  document.querySelectorAll('[data-zone]').forEach(el => {
    el.setAttribute('fill-opacity', '0.82');
    el.setAttribute('stroke-width', '0.8');
    el.setAttribute('stroke-opacity', '0.4');
  });
}
function showTip(tipId, bgId, t1, t2, t3, t4, n, ms, total, sie, natMs, tx, ty, sW, sH){
  const tip = document.getElementById(tipId);
  if (!tip) return;
  const diff = (ms - natMs).toFixed(1);
  document.getElementById(t1).textContent = n.replace(/^_/, '');
  document.getElementById(t2).textContent = `MS%: ${ms.toFixed(1)}%`;
  document.getElementById(t3).textContent = total>0 ? `SIE: ${sie.toLocaleString('es-AR')} · Mkt: ${total.toLocaleString('es-AR')}` : '';
  document.getElementById(t4).textContent = `vs Nac: ${diff>=0?'+':''}${diff} pp`;
  const W = 158, H = 52;
  document.getElementById(bgId).setAttribute('width', W);
  document.getElementById(bgId).setAttribute('height', H);
  let x = tx+8, y = ty-28;
  if (x+W > sW-4) x = tx-W-8;
  if (y < 4) y = 4;
  if (y+H > sH-4) y = sH-H-4;
  tip.setAttribute('transform', `translate(${x},${y})`);
  tip.setAttribute('visibility', 'visible');
}
function rMapa(mk){
  if (!document.getElementById('prov-layer')) return;
  const NS = 'http://www.w3.org/2000/svg';
  const latest = latestMonth(mk);
  const zData = {};
  regionRows(mk, latest).forEach(r => { zData[r.name] = { ms:Number(r.share||0), sie:Number(r.sie||0), total:Number(r.total||0) }; });
  const allMs = Object.values(zData).map(x=>x.ms);
  const allTot = Object.values(zData).map(x=>x.total).filter(x=>x>0);
  const maxMs = Math.max(...allMs, 0.1);
  const maxTot = Math.max(...allTot, 1);
  const nMs = natRow(mk, latest).ms;
  document.getElementById('map-leg-max').textContent = maxMs.toFixed(1)+'%';
  document.getElementById('s6').textContent = `MS%: ${cur} · ${monthLabel(latest)}`;
  const pL = document.getElementById('prov-layer');
  pL.innerHTML = '';
  PROVS.forEach(p => {
    const poly = document.createElementNS(NS, 'polygon');
    poly.setAttribute('points', p.pts);
    poly.setAttribute('fill', '#f1f5f9');
    poly.setAttribute('stroke', '#cbd5e1');
    poly.setAttribute('stroke-width', '0.7');
    pL.appendChild(poly);
  });
  const bL = document.getElementById('bub-layer');
  const mTip = document.getElementById('map-tip');
  bL.innerHTML = '';
  const entries = Object.entries(ZPOS).filter(([r]) => zData[r]).sort((a,b) => zData[b[0]].total - zData[a[0]].total);
  const rMax = 22, rMin = 4;
  entries.forEach(([r, pos]) => {
    const d = zData[r];
    const pct = maxMs > 0 ? d.ms/maxMs : 0;
    const rad = rMin + (rMax-rMin) * Math.sqrt(d.total/maxTot);
    const fill = zoneColor(pct);
    const c = document.createElementNS(NS, 'circle');
    c.setAttribute('cx', pos.x);
    c.setAttribute('cy', pos.y);
    c.setAttribute('r', rad.toFixed(1));
    c.setAttribute('fill', fill);
    c.setAttribute('fill-opacity', '0.82');
    c.setAttribute('stroke', 'white');
    c.setAttribute('stroke-opacity', '0.4');
    c.setAttribute('stroke-width', '0.8');
    c.setAttribute('data-zone', r);
    if (d.ms > maxMs*0.4) c.setAttribute('filter', 'url(#fglow)');
    c.style.cursor = 'pointer';
    c.addEventListener('mouseenter', () => {
      highlightZone(r);
      showTip('map-tip','mt-bg','mt-t1','mt-t2','mt-t3','mt-t4', r, d.ms, d.total, d.sie, nMs, pos.x, pos.y, 300, 560);
      bL.parentNode.appendChild(mTip);
    });
    c.addEventListener('mouseleave', () => { clearHighlight(); mTip.setAttribute('visibility', 'hidden'); });
    c.addEventListener('click', () => toggleReg(r));
    bL.appendChild(c);
  });
  rScatter(zData, maxMs, nMs);
  renderZT(zData, maxMs, nMs);
}
function rScatter(zData, maxMs, nMs){
  const NS = 'http://www.w3.org/2000/svg';
  const g = document.getElementById('scatter-g');
  if (!g) return;
  const W=400, H=320, ML=50, MR=14, MT=28, MB=46;
  const PW = W-ML-MR, PH = H-MT-MB;
  const scTip = document.getElementById('sc-tip');
  g.innerHTML = '';
  const allTot = Object.values(zData).map(x=>x.total).filter(x=>x>0);
  const minT = Math.min(...allTot), maxT = Math.max(...allTot);
  const logMin = Math.log10(Math.max(minT,1)), logMax = Math.log10(Math.max(maxT,1));
  const xSc = t => ML + (Math.log10(Math.max(t,1)) - logMin) / Math.max(logMax-logMin, 1) * PW;
  const ySc = ms => MT + PH - (ms/(maxMs*1.18)) * PH;
  const rSc = t => 4 + 14 * Math.sqrt(t/maxT);
  const yStep = maxMs > 30 ? 10 : maxMs > 12 ? 5 : 2;
  for (let v=0; v<=maxMs*1.2; v+=yStep) {
    const y = ySc(v);
    if (y < MT || y > MT+PH) continue;
    const gl = document.createElementNS(NS, 'line');
    gl.setAttribute('x1', ML); gl.setAttribute('x2', ML+PW); gl.setAttribute('y1', y); gl.setAttribute('y2', y);
    gl.setAttribute('stroke', '#f0f0f0'); gl.setAttribute('stroke-width', '1');
    g.appendChild(gl);
    const gt = document.createElementNS(NS, 'text');
    gt.setAttribute('x', ML-5); gt.setAttribute('y', y+3.5); gt.setAttribute('text-anchor', 'end'); gt.setAttribute('fill', '#9ca3af'); gt.setAttribute('font-size', '9'); gt.textContent = v+'%';
    g.appendChild(gt);
  }
  [500,1000,2000,5000,10000,20000,50000,100000,200000,500000,1000000,2000000].filter(v=>v>=minT*0.3 && v<=maxT*3).forEach(v => {
    const x = xSc(v);
    if (x < ML || x > ML+PW) return;
    const gl = document.createElementNS(NS, 'line');
    gl.setAttribute('x1', x); gl.setAttribute('x2', x); gl.setAttribute('y1', MT); gl.setAttribute('y2', MT+PH); gl.setAttribute('stroke', '#f0f0f0'); gl.setAttribute('stroke-width', '1');
    g.appendChild(gl);
    const lbl = v >= 1e6 ? (v/1e6).toFixed(1)+'M' : v >= 1e3 ? (v/1e3).toFixed(0)+'k' : v;
    const gt = document.createElementNS(NS, 'text');
    gt.setAttribute('x', x); gt.setAttribute('y', MT+PH+16); gt.setAttribute('text-anchor', 'middle'); gt.setAttribute('fill', '#9ca3af'); gt.setAttribute('font-size', '8.5'); gt.textContent = lbl;
    g.appendChild(gt);
  });
  const nY = ySc(nMs);
  const refL = document.createElementNS(NS, 'line');
  refL.setAttribute('x1', ML); refL.setAttribute('x2', ML+PW); refL.setAttribute('y1', nY); refL.setAttribute('y2', nY); refL.setAttribute('stroke', SIE); refL.setAttribute('stroke-width', '1.2'); refL.setAttribute('stroke-dasharray', '5 3'); refL.setAttribute('opacity', '0.75');
  g.appendChild(refL);
  const refT = document.createElementNS(NS, 'text');
  refT.setAttribute('x', ML+PW-4); refT.setAttribute('y', nY-5); refT.setAttribute('text-anchor', 'end'); refT.setAttribute('fill', '#f87171'); refT.setAttribute('font-size', '8.5'); refT.setAttribute('font-weight', '600'); refT.textContent = `Nac. ${nMs.toFixed(1)}%`;
  g.appendChild(refT);
  const ax = document.createElementNS(NS, 'polyline');
  ax.setAttribute('points', `${ML},${MT} ${ML},${MT+PH} ${ML+PW},${MT+PH}`); ax.setAttribute('fill', 'none'); ax.setAttribute('stroke', '#d1d5db'); ax.setAttribute('stroke-width', '1.2');
  g.appendChild(ax);
  const yL = document.createElementNS(NS, 'text');
  yL.setAttribute('transform', `rotate(-90,14,${MT+PH/2})`); yL.setAttribute('x', 14); yL.setAttribute('y', MT+PH/2); yL.setAttribute('text-anchor', 'middle'); yL.setAttribute('fill', '#9ca3af'); yL.setAttribute('font-size', '9'); yL.textContent = 'Market Share %';
  g.appendChild(yL);
  const xL = document.createElementNS(NS, 'text');
  xL.setAttribute('x', ML+PW/2); xL.setAttribute('y', H-10); xL.setAttribute('text-anchor', 'middle'); xL.setAttribute('fill', '#9ca3af'); xL.setAttribute('font-size', '9'); xL.textContent = 'Unidades de mercado (log)';
  g.appendChild(xL);
  const tL = document.createElementNS(NS, 'text');
  tL.setAttribute('x', ML+PW/2); tL.setAttribute('y', MT-12); tL.setAttribute('text-anchor', 'middle'); tL.setAttribute('fill', '#6b7280'); tL.setAttribute('font-size', '10'); tL.setAttribute('font-weight', '600'); tL.textContent = 'Volumen vs MS% · por zona CUP';
  g.appendChild(tL);
  [{x:ML+4,y:MT+12,t:'Baja vol · Alta MS',a:'start'},{x:ML+PW-4,y:MT+12,t:'Alta vol · Alta MS',a:'end'},{x:ML+4,y:MT+PH-5,t:'Baja vol · Baja MS',a:'start'},{x:ML+PW-4,y:MT+PH-5,t:'Alta vol · Baja MS',a:'end'}].forEach(i => {
    const q = document.createElementNS(NS, 'text');
    q.setAttribute('x', i.x); q.setAttribute('y', i.y); q.setAttribute('text-anchor', i.a); q.setAttribute('fill', '#e5e7eb'); q.setAttribute('font-size', '7.5'); q.textContent = i.t;
    g.appendChild(q);
  });
  Object.entries(zData).filter(([,x])=>x.total>0).sort((a,b)=>b[1].total-a[1].total).forEach(([r, x]) => {
    const cx = xSc(x.total), cy = ySc(x.ms), rad = rSc(x.total), pct = maxMs>0 ? x.ms/maxMs : 0, fill = zoneColor(pct);
    const c = document.createElementNS(NS, 'circle');
    c.setAttribute('cx', cx.toFixed(1)); c.setAttribute('cy', cy.toFixed(1)); c.setAttribute('r', rad.toFixed(1)); c.setAttribute('fill', fill); c.setAttribute('fill-opacity', '0.82'); c.setAttribute('stroke', 'white'); c.setAttribute('stroke-opacity', '0.4'); c.setAttribute('stroke-width', '0.8'); c.setAttribute('data-zone', r); c.style.cursor = 'pointer';
    if (x.total > maxT*0.08 || x.ms > maxMs*0.6) {
      const l = document.createElementNS(NS, 'text');
      l.setAttribute('x', cx+rad+3); l.setAttribute('y', cy+3.5); l.setAttribute('fill', '#9ca3af'); l.setAttribute('font-size', '7.5'); l.setAttribute('pointer-events', 'none'); l.textContent = r.replace(/^_/, '').split('-')[0].trim();
      g.appendChild(l);
    }
    c.addEventListener('mouseenter', () => { highlightZone(r); showTip('sc-tip','st-bg','st-t1','st-t2','st-t3','st-t4', r, x.ms, x.total, x.sie, nMs, cx, cy, W, H); g.appendChild(scTip); });
    c.addEventListener('mouseleave', () => { clearHighlight(); scTip.setAttribute('visibility', 'hidden'); });
    c.addEventListener('click', () => toggleReg(r));
    g.appendChild(c);
  });
  g.appendChild(scTip);
}
function renderZT(zData, maxMs, nMs){
  const tbody = document.getElementById('zona-tbl-mapa');
  if (!tbody) return;
  let rows = Object.entries(zData).map(([r, d]) => ({ zone:r.replace(/^_/, ''), reg:r, ms:d.ms, sie:d.sie, total:d.total, diff:+(d.ms - nMs).toFixed(2) }));
  rows.sort((a,b) => {
    const va = ztSort.col === 'zone' ? a.zone.toLowerCase() : a[ztSort.col];
    const vb = ztSort.col === 'zone' ? b.zone.toLowerCase() : b[ztSort.col];
    if (va === vb) return 0;
    return ztSort.dir === -1 ? (va>vb?-1:1) : (va>vb?1:-1);
  });
  tbody.innerHTML = rows.map((r, i) => {
    const pct = maxMs > 0 ? r.ms/maxMs : 0;
    const col = zoneColor(pct);
    const dCol = r.diff >= 0 ? '#16a34a' : '#dc2626';
    const bw = Math.max(pct*100, 1).toFixed(1);
    const sel = selRegs.includes(r.reg);
    return `<tr class="${sel?'act':''}" onclick="toggleReg('${r.reg}')"><td class="zt-num">${i+1}</td><td class="zt-zone"><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:${col};margin-right:5px;vertical-align:middle"></span>${r.zone}</td><td class="zt-ms"><div class="ms-bar-wrap"><span style="min-width:36px;text-align:right">${r.ms.toFixed(1)}%</span><div class="ms-bar-bg"><div class="ms-bar-fill" style="width:${bw}%"></div></div></div></td><td class="zt-diff" style="color:${dCol}">${r.diff>=0?'+':''}${r.diff}pp</td><td class="zt-units">${r.sie.toLocaleString('es-AR')}</td><td class="zt-units" style="color:#a3a3a3">${r.total.toLocaleString('es-AR')}</td></tr>`;
  }).join('');
}
function sortZT(th){
  const c = th.dataset.col;
  if (ztSort.col === c) ztSort.dir *= -1; else { ztSort.col = c; ztSort.dir = c === 'zone' ? 1 : -1; }
  document.querySelectorAll('.zt thead th').forEach(h => { h.className = h.dataset.col === c ? (ztSort.dir === -1 ? 'sort-desc' : 'sort-asc') : 'sort-none'; });
  render();
}

function init(){
  const bar = document.getElementById('mbar');
  const cmpBar = document.getElementById('cmpBar');
  ORDERED_MARKETS.forEach(m => {
    const c = document.createElement('div');
    c.className = 'mc' + (m === cur ? ' a' : '');
    c.textContent = m;
    c.dataset.m = m;
    c.onclick = () => {
      cur = m;
      ensureSelection();
      document.querySelectorAll('.mc').forEach(n => n.classList.toggle('a', n.dataset.m === m));
      render();
    };
    bar.appendChild(c);
  });
  [{key:'molecule', label:'Molécula'}, {key:'atc', label:'ATC'}].forEach(i => {
    const c = document.createElement('div');
    c.className = 'mc' + (i.key === cmp ? ' a' : '');
    c.textContent = i.label;
    c.dataset.c = i.key;
    c.onclick = () => {
      cmp = i.key;
      ensureSelection();
      document.querySelectorAll('#cmpBar .mc').forEach(n => n.classList.toggle('a', n.dataset.c === i.key));
      render();
    };
    cmpBar.appendChild(c);
  });
  ensureSelection();
  buildRegList();
  updBtnText();
  updTags();
  render();
}

function render(){
  const mk = marketObj();
  if (!mk) return;
  ensureSelection();
  syncUrl();
  renderHero(mk);
  rKPI(mk);
  rBF(mk);
  rC1(mk);
  rC2(mk);
  rC3(mk);
  rComp(mk);
  rTbl(mk);
  rMapa(mk);
  buildRegList();
  updBtnText();
  updTags();
}

init();
