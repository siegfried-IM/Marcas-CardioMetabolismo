// Extrae el grano por Obra Social del pivot "Detalle consumos y aportes por convenio"
// (app Convenios de rofina.us) para un anio + meses dados, y lo escribe a JSON.
// Uso: node shared/qlik/rofina-extract-convenios-os.mjs --year 2026 --months Jan,Feb,... --out <json>
//
// La seleccion va por listbox/qElemNumber (selectValues falla EN SILENCIO en este
// tenant) y se VERIFICA leyendo el selection object antes de extraer.
import { writeFileSync } from "fs";
import { loadSession, openEngine } from "./rofina-session.mjs";
import { CONSUMO_UNI, CONSUMO_UNI_BRUTO } from "./rofina-medidas.mjs";

const a = process.argv.slice(2);
const arg = (n, d) => { const i = a.indexOf("--" + n); return i >= 0 ? a[i + 1] : d; };
const YEAR = arg("year", "2026");
const MONTHS = arg("months", "").split(",").filter(Boolean);
const OUT = arg("out");

const s = loadSession();
const { session, app } = await openEngine(s.appId, s);

async function seleccionar(campo, valores) {
  const lb = await app.createSessionObject({
    qInfo: { qType: "lb" },
    qListObjectDef: {
      qDef: { qFieldDefs: [campo] },
      qInitialDataFetch: [{ qTop: 0, qLeft: 0, qHeight: 2000, qWidth: 1 }],
    },
  });
  const l = await lb.getLayout();
  const m = l.qListObject.qDataPages[0].qMatrix;
  const want = valores.map(String);
  const elems = m.filter((r) => want.includes(String(r[0].qText))).map((r) => r[0].qElemNumber);
  if (elems.length !== want.length) {
    throw new Error(`${campo}: pedi ${want.length} valores y encontre ${elems.length}`);
  }
  await lb.selectListObjectValues("/qListObjectDef", elems, false, false);
}

await app.clearAll();
await seleccionar("AñoSeleccion", [YEAR]);
if (MONTHS.length) await seleccionar("MesSeleccion", MONTHS);
await seleccionar("MesesRollBack", ["0"]);

// verificar que quedo lo pedido (el silent-fail se ve aca)
const so = await app.createSessionObject({ qInfo: { qType: "sel" }, qSelectionObjectDef: {} });
const sl = await so.getLayout();
const real = {};
for (const x of sl.qSelectionObject?.qSelections || []) {
  real[x.qField] = (x.qSelectedFieldSelectionInfo || []).map((v) => v.qName).join(",") || `${x.qTotal} sel`;
}
console.log("  selecciones reales:", JSON.stringify(real));
if (!real["AñoSeleccion"]?.includes(YEAR)) throw new Error("La seleccion de AñoSeleccion NO quedo aplicada");

// cubo: ObraSocial1 + Producto -> las DOS medidas.
// La que se publica es CONSUMO_UNI (neto de notas de debito): es la columna
// "Consumo uni" del pivot y el KPI "Consumo unidades" de la hoja, o sea el numero
// que el usuario ve en Qlik. El bruto viaja al lado solo para poder reproducir el
// "% convenio UNI" y para medir cuanto pesan las ND. Antes esto extraia el BRUTO y
// lo publicaba como unidades: +22,3% en ROACCUTAN Ene-Jun 2026.
const o = await app.createSessionObject({
  qInfo: { qType: "c" },
  qHyperCubeDef: {
    qDimensions: [
      { qDef: { qFieldDefs: ["ObraSocial1"] }, qNullSuppression: true },
      { qDef: { qFieldDefs: ["Producto"] }, qNullSuppression: true },
    ],
    qMeasures: [{ qDef: { qDef: CONSUMO_UNI } },
                { qDef: { qDef: CONSUMO_UNI_BRUTO } }],
    qInitialDataFetch: [],
    qSuppressZero: true,
  },
});
const lay = await o.getLayout();
const H = lay.qHyperCube.qSize.qcy, W = lay.qHyperCube.qSize.qcx;
const rows = [];
for (let top = 0; top < H; top += 2500) {
  const p = await o.getHyperCubeData("/qHyperCubeDef", [
    { qTop: top, qLeft: 0, qHeight: Math.min(2500, H - top), qWidth: W },
  ]);
  for (const r of p[0].qMatrix) rows.push([r[0].qText, r[1].qText, r[2].qNum, r[3].qNum]);
}
console.log(`  ${YEAR}: ${rows.length} filas (OS x Producto)`);
const aplicados = (real["MesSeleccion"] || "").split(",").map((x) => x.trim()).filter(Boolean);
console.log(`  meses aplicados: ${aplicados.join(",") || "(todos)"}`);
const neto = rows.reduce((t, r) => t + (r[2] || 0), 0);
const bruto = rows.reduce((t, r) => t + (r[3] || 0), 0);
console.log(`  consumo uni (neto de ND): ${Math.round(neto).toLocaleString("es-AR")}`);
console.log(`  bruto (solo para el %)  : ${Math.round(bruto).toLocaleString("es-AR")}` +
            `  -> las ND pesan ${(100 - neto / bruto * 100).toFixed(1)}%`);
// 'medida' es la compuerta: build-convenios-os.py ABORTA si el extracto no la declara,
// asi un JSON viejo (que traia el bruto en la col 2) no puede colarse como si fuera neto.
if (OUT) writeFileSync(OUT, JSON.stringify(
  { year: YEAR, mesesPedidos: MONTHS, mesesAplicados: aplicados,
    medida: "Consumo uni (neto de ND)", expr: CONSUMO_UNI,
    cols: ["ObraSocial1", "Producto", "consumo_uni_neto", "consumo_uni_bruto"],
    totalNeto: neto, totalBruto: bruto, rows }), "utf8");
await session.close();
process.exit(0);
