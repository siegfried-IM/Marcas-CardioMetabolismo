// shared/qlik/rofina-extract-canales.mjs
// Por FAMILIA: unidades facturadas + consumo por convenio BRUTO y NETO de bajas (ND),
// para un anio + meses. Es la fuente de la seccion "Mostrador vs Convenios".
//
// Por que trae las dos: el pivot ThZZvT de la app calcula
//     % convenio UNI = sum(Consumo_Unidades_Inf)/sum(unidades_total)
// o sea consumo SIN descontar las bajas sobre unidades facturadas. Numerador y
// denominador no son el mismo universo y el cociente pasa de 100% (DILATREND Q1-2026:
// 185.411 consumidas contra 166.567 facturadas = 111,3%, imposible como participacion).
// Rofina ya migro su propio KPI al neto y dejo la version vieja comentada; este
// extractor trae las dos para que el rotulo del tablero pueda decir cual usa.
//
// Uso: node shared/qlik/rofina-extract-canales.mjs --year 2026 --months Jan,Feb,Mar --out <json>
//
// OJO: pedir meses que todavia no existen NO devuelve vacio, devuelve otra cosa
// (2026 Q4 dio 17,1M de unidades facturadas, 3x un trimestre real). Verificar siempre
// Sigma trimestres == anio antes de publicar.
import { writeFileSync } from "fs";
import { loadSession, openEngine } from "./rofina-session.mjs";
import { CONSUMO_UNI, CONSUMO_UNI_BRUTO } from "./rofina-medidas.mjs";
const a = process.argv.slice(2), arg = (n,d)=>{const i=a.indexOf("--"+n);return i>=0?a[i+1]:d;};
const YEAR = arg("year","2026"), MONTHS = arg("months","").split(",").filter(Boolean), OUT = arg("out");
const s = loadSession(); const { session, app } = await openEngine(s.appId, s);
async function sel(campo, vals){
  const lb = await app.createSessionObject({qInfo:{qType:"lb"},qListObjectDef:{qDef:{qFieldDefs:[campo]},
    qInitialDataFetch:[{qTop:0,qLeft:0,qHeight:2000,qWidth:1}]}});
  const l = await lb.getLayout(); const m = l.qListObject.qDataPages[0].qMatrix;
  const want = vals.map(String);
  const el = m.filter(r=>want.includes(String(r[0].qText))).map(r=>r[0].qElemNumber);
  if (el.length !== want.length) throw new Error(`${campo}: pedi ${want.length}, encontre ${el.length}`);
  await lb.selectListObjectValues("/qListObjectDef", el, false, false);
}
await app.clearAll();
await sel("AñoSeleccion",[YEAR]); if(MONTHS.length) await sel("MesSeleccion",MONTHS); await sel("MesesRollBack",["0"]);
const so = await app.createSessionObject({qInfo:{qType:"sel"},qSelectionObjectDef:{}});
const sl = await so.getLayout(); const real={};
for(const x of sl.qSelectionObject?.qSelections||[]) real[x.qField]=(x.qSelectedFieldSelectionInfo||[]).map(v=>v.qName).join(",");
console.log("  selecciones:", JSON.stringify(real));
if(!real["AñoSeleccion"]?.includes(YEAR)) throw new Error("seleccion no aplicada");
const o = await app.createSessionObject({qInfo:{qType:"c"},qHyperCubeDef:{
  qDimensions:[{qDef:{qFieldDefs:["Familia"]},qNullSuppression:true}],
  qMeasures:[{qDef:{qDef:"Sum(unidades_total)"}},{qDef:{qDef:CONSUMO_UNI_BRUTO}},{qDef:{qDef:CONSUMO_UNI}}],
  qInitialDataFetch:[],qSuppressZero:false}});
const lay = await o.getLayout(); const H=lay.qHyperCube.qSize.qcy, W=lay.qHyperCube.qSize.qcx;
const rows=[];
for(let top=0; top<H; top+=2500){
  const p = await o.getHyperCubeData("/qHyperCubeDef",[{qTop:top,qLeft:0,qHeight:Math.min(2500,H-top),qWidth:W}]);
  for(const r of p[0].qMatrix) rows.push([r[0].qText, r[1].qNum, r[2].qNum, r[3].qNum]);
}
console.log(`  ${YEAR} ${MONTHS.join(",")}: ${rows.length} familias`);
if(OUT) writeFileSync(OUT, JSON.stringify({year:YEAR,months:MONTHS,
  cols:["familia","facturado","bruto","neto"],rows}),"utf8");
await session.close(); process.exit(0);
