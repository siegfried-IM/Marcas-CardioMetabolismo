// shared/qlik/rofina-extract-stock.mjs
// Extrae Stock/Ventas/Facturacion/Dias de Stock de la app "Stock y Ventas" del tenant
// rofina.us (la fuente de la seccion Stock + Cobertura del tablero).
//
// Uso: node shared/qlik/rofina-extract-stock.mjs --out <salida.json>
//
// ── POR QUE SIN SELECCIONES ────────────────────────────────────────────────────
// En este tenant `selectValues()` falla EN SILENCIO (ver POC-CONVENIOS.md): deja 0
// selecciones sin error y se extrae un universo desconocido que parece plausible.
// Aca NO hace falta filtrar nada:
//   - Laboratorio tiene UN solo valor ("Siegfried S.A."), la app ya esta acotada.
//   - Los meses se recortan despues, en Python, al armar el xlsx.
// Entonces: clearAll() y se pagina todo. Cero selecciones = cero riesgo de ese bug.
//
// ── DOS GRANOS (importante) ────────────────────────────────────────────────────
// "Dias de Stock" es un RATIO (stock / venta diaria), NO se puede sumar entre
// presentaciones. Por eso se extrae en dos granos y el de familia lo calcula Qlik:
//   grano producto : Familia + Producto + Mes-Ano   -> filas de presentacion
//   grano familia  : Familia + Mes-Ano              -> fila 'Totales' de cada familia
// (mismo patron que extract-recetas.mjs con su 2do grano de mercado).
//
// Dims y medidas se referencian por qLibraryId (son master items de la app), asi que
// se usan las MISMAS definiciones que ve el usuario en el tablero de rofina.
import { writeFileSync } from "fs";
import { loadSession, rest, openEngine } from "./rofina-session.mjs";

const APP = "8ae964dc-1af3-47b1-ab99-f0ef0598d957"; // "Stock y Ventas"

// master items (sacados de las propiedades del combochart 5ad3ce36 de la hoja
// "Sell Out y Dias de Stock", que es el objeto que muestra esta serie en rofina)
const DIM = {
  familia: "ce4bfbcb-74fd-4be0-b985-fdd639a56c08",
  producto: "mmJKpqV",
};
// ── EL MES VA POR %Periodo_key, *NO* POR [Mes-Año] ────────────────────────────
// [Mes-Año] (master dim EBnc, la que usa el combochart de la app) ABRE EN ABANICO:
// el modelo tiene un bridge de ventana movil (Meses adicionales / Flag_RollBack /
// AñoMesCliProd_key) y cada fila de hecho queda asociada a ~11,5 valores de Mes-Año.
// Medido en SINTROM: sumar los meses da 67.039.410 contra un total sin dimension de
// mes de 5.813.744 (11,5x). Con %Periodo_key la suma da 5.813.744 EXACTO.
// Probados tambien: AñoMesVisible y MesVisible (mismo 67M), [Mes-Año Actual] (1.866M).
// Validado ademas contra el export manual 'Laboratorio - Familia - Producto':
// Apr-2026 78/78 y May-2026 78/79 familias EXACTAS en stock y ventas (la que falla es
// SYNCROCOR, que en el tablero va splitteada por presentacion).
const F_PERIODO = "%Periodo_key"; // formato YYYYMM (202606)
// ORDEN = el que espera el xlsx de 'Laboratorio - Familia - Producto':
// Stock final, Ventas, Facturacion, Dias de Stock
const MEAS = [
  { id: "594f708e-f4d2-48a6-a4c6-b26874876cd5", name: "Stock final" },
  { id: "f5c90e2f-5357-4ab9-84f3-27a322043bc5", name: "Ventas" },
  { id: "fpmCGRV", name: "Facturacion" },
  { id: "aee4b72b-c348-4208-a8c7-284ffd3793d1", name: "Dias de Stock" },
];

const args = process.argv.slice(2);
const outPath = args[args.indexOf("--out") + 1];
if (!outPath || outPath.startsWith("--")) {
  console.error("Falta --out <salida.json>");
  process.exit(2);
}

const lib = (id) => ({ qLibraryId: id, qNullSuppression: true });
const fld = (f) => ({ qDef: { qFieldDefs: [f] }, qNullSuppression: true });

function cubeDef(dims) {
  return {
    qInfo: { qType: "stock-cube" },
    qHyperCubeDef: {
      qDimensions: dims,
      qMeasures: MEAS.map((m) => ({ qLibraryId: m.id })),
      qInitialDataFetch: [],
      qSuppressZero: false,
      qSuppressMissing: true,
    },
  };
}

// Pagina un hypercube entero. El ancho es dims+medidas; Qlik limita ~10k celdas por
// pedido, asi que el alto por pagina se calcula con eso.
async function pageAll(app, dims, label) {
  const obj = await app.createSessionObject(cubeDef(dims));
  const lay = await obj.getLayout();
  const hc = lay.qHyperCube;
  const W = hc.qSize.qcx;
  const H = hc.qSize.qcy;
  const perPage = Math.max(1, Math.floor(9000 / W));
  console.log(`  ${label}: ${H} filas x ${W} cols (paginas de ${perPage})`);
  const rows = [];
  for (let top = 0; top < H; top += perPage) {
    const pages = await obj.getHyperCubeData("/qHyperCubeDef", [
      { qTop: top, qLeft: 0, qHeight: Math.min(perPage, H - top), qWidth: W },
    ]);
    for (const r of pages[0].qMatrix) {
      const d = r.slice(0, dims.length).map((c) => c.qText);
      const meas = r.slice(dims.length).map((c) => (c.qNum === "NaN" ? null : c.qNum));
      rows.push([...d, ...meas]);
    }
  }
  if (rows.length !== H) throw new Error(`${label}: pagine ${rows.length} de ${H} filas`);
  console.log(`     ${rows.length} filas OK`);
  return rows;
}

// G0 ANTI-ABANICO: suma por familia SIN dimension de mes. Si al cortar por el campo
// de periodo la suma no da lo mismo, ese campo duplica (le paso a [Mes-Año]: 11,5x) y
// NO se puede publicar. Es el unico chequeo que ve este bug: los totales "cierran"
// igual y los dias de stock quedan plausibles.
async function totalSinMes(app) {
  const obj = await app.createSessionObject(cubeDef([lib(DIM.familia)]));
  const lay = await obj.getLayout();
  const H = lay.qHyperCube.qSize.qcy;
  const W = lay.qHyperCube.qSize.qcx;
  const out = new Map();
  for (let top = 0; top < H; top += 500) {
    const p = await obj.getHyperCubeData("/qHyperCubeDef", [
      { qTop: top, qLeft: 0, qHeight: Math.min(500, H - top), qWidth: W },
    ]);
    for (const r of p[0].qMatrix) out.set(r[0].qText, [r[1].qNum || 0, r[2].qNum || 0]);
  }
  return out;
}

const s = loadSession();
const me = await rest("/api/v1/users/me", s);
console.log(`sesion : OK (${me.name || "usuario"})`);
const { session, app } = await openEngine(APP, s);
const lay = await app.getAppLayout();
console.log(`app    : ${lay.qTitle}  (lastReload ${lay.qLastReloadTime})`);

// clearAll: la app abre con seleccion por defecto (mismo caso que DDD y Recetas)
await app.clearAll();
const selObj = await app.createSessionObject({
  qInfo: { qType: "sel" },
  qSelectionObjectDef: {},
});
const selLay = await selObj.getLayout();
const activas = (selLay.qSelectionObject?.qSelections || []).map((x) => x.qField);
console.log(`sel    : ${activas.length === 0 ? "ninguna (clearAll OK)" : "ACTIVAS -> " + activas.join(", ")}`);
if (activas.length) throw new Error("Quedaron selecciones activas tras clearAll; abortando");

console.log("extrayendo:");
const prod = await pageAll(app, [lib(DIM.familia), lib(DIM.producto), fld(F_PERIODO)], "grano producto");
const fam = await pageAll(app, [lib(DIM.familia), fld(F_PERIODO)], "grano familia");

const rel = (a, b) => (b ? Math.abs(a - b) / Math.abs(b) : a === b ? 0 : 1);

// G1a: los dos granos tienen que cerrar entre si (misma medida, distinto corte).
const sum = (rows, idx) => rows.reduce((a, r) => a + (Number(r[idx]) || 0), 0);
const stockProd = sum(prod, 3), stockFam = sum(fam, 2);
const ventasProd = sum(prod, 4), ventasFam = sum(fam, 3);
console.log(`G1a stock : producto ${Math.round(stockProd).toLocaleString()} vs familia ${Math.round(stockFam).toLocaleString()}  (${(rel(stockProd, stockFam) * 100).toFixed(4)}%)`);
console.log(`G1a ventas: producto ${Math.round(ventasProd).toLocaleString()} vs familia ${Math.round(ventasFam).toLocaleString()}  (${(rel(ventasProd, ventasFam) * 100).toFixed(4)}%)`);
if (rel(stockProd, stockFam) > 0.005 || rel(ventasProd, ventasFam) > 0.005) {
  throw new Error("G1a FALLO: los dos granos no cierran; no se escribe nada");
}

// G1b ANTI-ABANICO (el chequeo que caza el bug de [Mes-Año]): por familia, la suma
// de todos los meses tiene que dar el total SIN dimension de mes.
console.log("  G1b anti-abanico (suma de meses == total sin mes, por familia)...");
const totales = await totalSinMes(app);
const porFam = new Map();
for (const r of fam) {
  const k = r[0];
  const a = porFam.get(k) || [0, 0];
  porFam.set(k, [a[0] + (Number(r[2]) || 0), a[1] + (Number(r[3]) || 0)]);
}
let peor = 0, peorFam = "";
for (const [f, [s, v]] of porFam) {
  const t = totales.get(f);
  if (!t) continue;
  const d = Math.max(rel(s, t[0]), rel(v, t[1]));
  if (d > peor) { peor = d; peorFam = f; }
}
console.log(`G1b: ${porFam.size} familias, peor desvio ${(peor * 100).toFixed(4)}% (${peorFam})`);
if (peor > 0.005) {
  throw new Error(
    `G1b FALLO: el campo de periodo DUPLICA (peor ${(peor * 100).toFixed(1)}% en ${peorFam}). ` +
    "Sintoma del abanico de [Mes-Año]; no se escribe nada."
  );
}

const meses = [...new Set(prod.map((r) => r[2]))].sort();
writeFileSync(
  outPath,
  JSON.stringify(
    {
      app: lay.qTitle,
      appId: APP,
      lastReload: lay.qLastReloadTime,
      extraido: new Date().toISOString(),
      medidas: MEAS.map((m) => m.name),
      meses,
      producto: { cols: ["Familia", "Producto", "Mes-Ano", ...MEAS.map((m) => m.name)], rows: prod },
      familia: { cols: ["Familia", "Mes-Ano", ...MEAS.map((m) => m.name)], rows: fam },
    },
    null,
    0
  ),
  "utf8"
);
console.log(`OK: producto=${prod.length} filas, familia=${fam.length} filas, ${meses.length} meses -> ${outPath}`);

await session.close();
process.exit(0);
