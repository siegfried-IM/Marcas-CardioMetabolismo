"""Construye data.js para el dashboard DDD Linea Mujer desde el Excel
Producto-Mol\u00e9cula-ATC-provincia.

Produce una constante window.OTC_DATA = {...} con la misma shape que el
DDD Respiratorio: {dddGineco: {order, months, families: {<mercado>: {molecule|atc: {all: MarketObj}}}}}"""
import pandas as pd, json, re
from pathlib import Path
from collections import defaultdict

ROOT  = Path(r"C:\Users\ajofre\OneDrive - Portalcorp\Documentos\D. SIEGFRIED\B-CLAUDE\A.DASHBOARD_LINEA_MUJER")
XLSX  = ROOT / "DATOS" / "Producto-Mol\u00e9cula-ATC-provincia - 20 de abril de 2026 (1).xlsx"
OUT_JSON = ROOT / "DASHBOARD" / "DDD" / "data.js"

# -------------------------------------------------------------------------
# Mapeo Mercado IQVIA (del Excel) -> mercado_dashboard (el eje del tablero).
# Los mercados "agregados" (Siderblut Familia, Calcio Base Dupomar,
# Anticonceptivos Orales totales) se ignoran porque duplican granularidad.
# Cefalexina queda fuera (no es L\u00ednea Mujer).
# -------------------------------------------------------------------------
MKT_MAP = {
    "Isis Free (Progest\u00e1genos Solos)":  "SIN ESTROGENO",
    "Isis":                                "ALTA DOSIS",
    "Isis Mini":                           "BAJA DOSIS 21+7",
    "Isis Mini 24":                        "BAJA DOSIS 24",
    "Siderblut Compuestos":                "COMPLEX",
    "Siderblut Solos S\u00f3lidos":        "SOLO (s\u00f3lidos)",
    "Siderblut Solos L\u00edquidos":       "SOLO (l\u00edquidos)",
    "Siderblut IM":                        "SOLO (IM)",
    "Hierro Polimaltosato (Sider gotas)":  "SOLO (gotas)",
    "Trip D3":                             "D3",
    "Calcio Base":                         "BASE",
    "Deltrox":                             "DELTROX",
}
# Orden para el selector de mercado
MERCADO_ORDER = [
    "SIN ESTROGENO", "ALTA DOSIS", "BAJA DOSIS 21+7", "BAJA DOSIS 24",
    "COMPLEX", "SOLO (s\u00f3lidos)", "SOLO (l\u00edquidos)",
    "SOLO (IM)", "SOLO (gotas)", "D3", "BASE", "DELTROX",
]

# Detecci\u00f3n SIE por patr\u00f3n de nombre.
SIE_REGEX = re.compile(
    r"^(ISIS|SIDERBLUT|SIDER\s+GOTAS|TRIP\s+D3|CALCIO\s+BASE|DELTROX)",
    re.IGNORECASE,
)
def is_sie(name: str) -> bool:
    return bool(SIE_REGEX.match(str(name).strip()))

MONTH_ORDER = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
def month_sort_key(m):
    mo, yr = str(m).split("-")
    return int(yr) * 12 + MONTH_ORDER.index(mo)

def build():
    df = pd.read_excel(XLSX, sheet_name="Sheet1", header=2)
    df = df[df["RegionCUP"] != "Totales"].copy()
    df = df.dropna(subset=["RegionCUP", "Mercado", "Producto", "A\u00f1oMes", "Unidades"])
    df = df[df["RegionCUP"] != "-"]
    df["Unidades"] = pd.to_numeric(df["Unidades"], errors="coerce").fillna(0).astype(int)
    print(f"Filas cargadas: {len(df):,}")

    # Filtrar solo mercados mapeados
    df = df[df["Mercado"].isin(MKT_MAP.keys())].copy()
    df["MercadoDash"] = df["Mercado"].map(MKT_MAP)
    df["es_sie"] = df["Producto"].apply(is_sie)
    df["ATC"] = df["Codigo Clase Terapeutica"].astype(str).str.strip()
    print(f"Filas L\u00ednea Mujer: {len(df):,}")
    print(f"  productos SIE: {df[df['es_sie']]['Producto'].nunique()}")
    print(f"  productos competencia: {df[~df['es_sie']]['Producto'].nunique()}")

    months_set = sorted(df["A\u00f1oMes"].unique(), key=month_sort_key)
    print(f"Meses: {months_set[0]} -> {months_set[-1]} ({len(months_set)} meses)")

    # ---------- Construcci\u00f3n por mercado (molecule) y por ATC (atc) ----------
    families = {}
    # Pre-agrupaciones para reutilizar
    for fam_key, group_col in [("molecule", "MercadoDash"), ("atc", "ATC")]:
        keys = (
            MERCADO_ORDER
            if fam_key == "molecule"
            else sorted(df["ATC"].unique())
        )
        for key in keys:
            sub = df[df[group_col] == key].copy()
            if sub.empty:
                continue
            # Grain mensual
            regs_by_month = defaultdict(list)
            prods_by_month = defaultdict(list)
            monthly = []
            for month in months_set:
                sm = sub[sub["A\u00f1oMes"] == month]
                if sm.empty:
                    continue
                # regiones
                reg_agg = (
                    sm.groupby("RegionCUP")
                    .apply(lambda g: pd.Series({
                        "total": int(g["Unidades"].sum()),
                        "sie":   int(g[g["es_sie"]]["Unidades"].sum()),
                    }), include_groups=False)
                    .reset_index()
                )
                reg_rows = []
                for _, r in reg_agg.iterrows():
                    total = int(r["total"]); sie = int(r["sie"])
                    if total <= 0: continue
                    share = round(sie / total * 100, 1)
                    reg_rows.append({"name": r["RegionCUP"], "total": total, "sie": sie, "share": share})
                # producto (topN por suma de unidades para el mes)
                prod_agg = (
                    sm.groupby("Producto")
                    .apply(lambda g: pd.Series({
                        "units":   int(g["Unidades"].sum()),
                        "isSie":   bool(g["es_sie"].any()),
                    }), include_groups=False)
                    .reset_index()
                )
                total_mes = int(sm["Unidades"].sum())
                prod_rows = []
                for _, r in prod_agg.iterrows():
                    units = int(r["units"])
                    if units <= 0: continue
                    share = round(units / total_mes * 100, 1) if total_mes > 0 else 0
                    prod_rows.append({
                        "product": r["Producto"],
                        "units":   units,
                        "share":   share,
                        "isSie":   bool(r["isSie"]),
                    })
                prod_rows.sort(key=lambda x: -x["units"])
                regs_by_month[month] = sorted(reg_rows, key=lambda x: -x["total"])
                prods_by_month[month] = prod_rows[:30]  # top 30 productos por mes
                total_m = int(sm["Unidades"].sum())
                sie_m   = int(sm[sm["es_sie"]]["Unidades"].sum())
                monthly.append({
                    "month":  month,
                    "total":  total_m,
                    "sie":    sie_m,
                    "share":  round(sie_m / total_m * 100, 1) if total_m > 0 else 0,
                })
            market_obj = {
                "family":         key,
                "latestMonth":    monthly[-1]["month"] if monthly else months_set[-1],
                "monthly":        monthly,
                "regionsByMonth": dict(regs_by_month),
                "productsByMonth":dict(prods_by_month),
            }
            families.setdefault(key, {"molecule": {"all": None}, "atc": {"all": None}})
            if fam_key == "molecule":
                families[key]["molecule"]["all"] = market_obj
            else:
                # Los ATC usan la misma key: guardamos con "ATC_<code>" para no pisar
                pass

    # Segundo pase: para mercado en MERCADO_ORDER, completar atc.all = scope ATC
    # (el ATC del principal producto SIE de ese mercado; si hay m\u00e1s de uno, tomar el top).
    for mkt in MERCADO_ORDER:
        subM = df[df["MercadoDash"] == mkt]
        if subM.empty: continue
        atc_top = (subM.groupby("ATC")["Unidades"].sum().sort_values(ascending=False))
        top_atc = atc_top.index[0] if len(atc_top) else None
        if top_atc is None: continue
        subA = df[df["ATC"] == top_atc].copy()
        monthly = []
        regs_by_month = {}
        prods_by_month = {}
        for month in months_set:
            sm = subA[subA["A\u00f1oMes"] == month]
            if sm.empty: continue
            reg_agg = sm.groupby("RegionCUP").apply(
                lambda g: pd.Series({"total": int(g["Unidades"].sum()), "sie": int(g[g["es_sie"]]["Unidades"].sum())}),
                include_groups=False,
            ).reset_index()
            reg_rows = []
            for _, r in reg_agg.iterrows():
                t, s = int(r["total"]), int(r["sie"])
                if t <= 0: continue
                reg_rows.append({"name": r["RegionCUP"], "total": t, "sie": s, "share": round(s/t*100,1)})
            prod_agg = sm.groupby("Producto").apply(
                lambda g: pd.Series({"units": int(g["Unidades"].sum()), "isSie": bool(g["es_sie"].any())}),
                include_groups=False,
            ).reset_index()
            tot = int(sm["Unidades"].sum())
            prod_rows = []
            for _, r in prod_agg.iterrows():
                u = int(r["units"])
                if u <= 0: continue
                prod_rows.append({"product": r["Producto"], "units": u,
                                  "share": round(u/tot*100,1) if tot else 0,
                                  "isSie": bool(r["isSie"])})
            prod_rows.sort(key=lambda x: -x["units"])
            regs_by_month[month] = sorted(reg_rows, key=lambda x: -x["total"])
            prods_by_month[month] = prod_rows[:30]
            tm = int(sm["Unidades"].sum())
            sm_sie = int(sm[sm["es_sie"]]["Unidades"].sum())
            monthly.append({"month": month, "total": tm, "sie": sm_sie,
                            "share": round(sm_sie/tm*100,1) if tm else 0})
        families[mkt]["atc"]["all"] = {
            "family": mkt, "atcCode": top_atc,
            "latestMonth": monthly[-1]["month"] if monthly else months_set[-1],
            "monthly": monthly,
            "regionsByMonth": regs_by_month,
            "productsByMonth": prods_by_month,
        }

    # Fallback: si atc.all sigue vac\u00edo, copiar molecule.all
    for mkt, fv in families.items():
        if fv["atc"]["all"] is None:
            fv["atc"]["all"] = fv["molecule"]["all"]
        # Replicar "etico" y "popular" como clones de "all" (no tenemos ese desglose)
        fv["molecule"]["etico"]   = fv["molecule"]["all"]
        fv["molecule"]["popular"] = fv["molecule"]["all"]
        fv["atc"]["etico"]        = fv["atc"]["all"]
        fv["atc"]["popular"]      = fv["atc"]["all"]

    out = {
        "meta": {
            "source": XLSX.name,
            "generatedFor": "Linea Mujer Siegfried - DDD por Provincia",
        },
        "dddGineco": {
            "order":    MERCADO_ORDER,
            "months":   months_set,
            "families": families,
        },
    }

    js = "window.OTC_DATA = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n"
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(js, encoding="utf-8")
    size_mb = OUT_JSON.stat().st_size / 1024 / 1024
    print(f"\nOK -> {OUT_JSON}  ({size_mb:.2f} MB)")
    # Resumen
    for mkt in MERCADO_ORDER:
        if mkt in families and families[mkt]["molecule"]["all"]:
            mo = families[mkt]["molecule"]["all"]
            print(f"  {mkt:<22} {len(mo['monthly']):>2} meses  {len(mo['regionsByMonth'])} meses regs  "
                  f"latest={mo['latestMonth']}  total \u00faltimo={mo['monthly'][-1]['total']:>8,}  SIE={mo['monthly'][-1]['sie']:>7,}  MS={mo['monthly'][-1]['share']}%")

if __name__ == "__main__":
    build()
