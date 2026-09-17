// shared/qlik/rofina-medidas.mjs
// Expresiones CANONICAS de la app "Convenios" de rofina.us. Viven una sola vez acá
// porque duplicarlas ya costó caro: rofina-extract-convenios-os.mjs se escribió con
// sum(Consumo_Unidades_Inf) pelado y publicó el consumo BRUTO como si fuera el que
// muestra el tablero. En ROACCUTAN Ene-Jun 2026 eso dio 83.237 u. contra las 68.035
// que ve el usuario (+22,3%), y el desvío es por obra social (0% a +74%), no un factor
// que se pueda corregir después.
//
// La diferencia es Tipo_Cabecera='ND' (notas de débito): la columna "Consumo uni" las
// RESTA, el "% convenio UNI" NO. Ver shared/qlik/POC-CONVENIOS.md.

/** Neto de notas de débito. Es lo que muestra la columna "Consumo uni" del pivot
 *  y el KPI "Consumo unidades" de la hoja: el número que el usuario lee en Qlik. */
export const CONSUMO_UNI =
  "sum(if(Tipo_Cabecera='ND', -Consumo_Unidades_Inf,Consumo_Unidades_Inf))";

/** Bruto, SIN restar ND. Solo para reproducir el "% convenio UNI" tal como lo
 *  publica rofina. NO usarlo para mostrar unidades. */
export const CONSUMO_UNI_BRUTO = "sum(Consumo_Unidades_Inf)";

export const MEASURES = [
  ["Unidades facturadas", "Sum(unidades_total)"],
  ["Convenios", "Sum(convenios)"],
  ["$ neto facturado", "Sum(neto)"],
  ["Consumo uni", CONSUMO_UNI],
  ["Consumo PVP", "sum(if(Tipo_Cabecera='ND', -Consumo_Pesos_Inf,Consumo_Pesos_Inf))"],
  ["Aporte neto", "sum(if(Tipo_Cabecera='ND', -Aporte_Neto,Aporte_Neto))"],
  ["$ netos", "sum(if(Tipo_Cabecera='ND', -impneto,impneto))"],
  ["% convenio UNI", CONSUMO_UNI_BRUTO + "/sum(unidades_total)"],
  ["% mostrador UNI", "(sum(unidades_total)-" + CONSUMO_UNI_BRUTO + ")/sum(unidades_total)"],
  ["% dto com", "(sum(neto)-sum(convenios))/sum(bruto_hipotetico)-1"],
  ["% dto conv", "sum(convenios)/sum(bruto_hipotetico)"],
  ["% dto total", "-(sum(bruto_hipotetico)-sum(neto))/sum(bruto_hipotetico)"],
];
