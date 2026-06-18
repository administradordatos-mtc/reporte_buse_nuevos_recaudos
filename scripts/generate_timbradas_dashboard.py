#!/usr/bin/env python3
from __future__ import annotations

import base64
import csv
import html
import json
import os
import ssl
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_PRIVATE = ROOT / "private"
OUT_PRIVATE.mkdir(exist_ok=True)
ENV_CANDIDATES = [ROOT / ".env", Path("/root/proyectos/supabase-reportes/.env")]
LOGO_PATH = Path("/root/sharepoint/La Carolina De Transporte/Projects/Revision_De_Concurrencia_Repuestos/Logo_lacarolina.jpeg")

SELECT = ",".join([
    "fecha_viaje", "codigo_vehiculo", "placa", "conductor_nombre", "codigo_conductor",
    "viaje", "descuento", "timbradas", "timbradas_real", "estado", "novedad",
    "ruta_programada", "ruta_reprogramada", "is_viaje_contable", "is_extemporaneo",
])


def load_env() -> dict[str, str]:
    env = dict(os.environ)
    for path in ENV_CANDIDATES:
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            s = raw.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return env


def supabase_get(table: str, params: list[tuple[str, str]], page_size: int = 1000):
    env = load_env()
    base = env["SUPABASE_URL"].rstrip("/")
    key = env["SUPABASE_KEY"]
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
        "Prefer": "count=exact",
    }
    rows = []
    total = None
    offset = 0
    while True:
        qs = params + [("limit", str(page_size)), ("offset", str(offset))]
        url = f"{base}/rest/v1/{urllib.parse.quote(table, safe='')}?{urllib.parse.urlencode(qs)}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=90, context=ssl.create_default_context()) as r:
            cr = r.headers.get("Content-Range") or r.headers.get("content-range")
            if cr and "/" in cr:
                t = cr.rsplit("/", 1)[-1]
                if t.isdigit():
                    total = int(t)
            batch = json.loads(r.read().decode("utf-8"))
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += len(batch)
    return rows, total


def dnum(x) -> Decimal:
    if x is None or x == "":
        return Decimal("0")
    return Decimal(str(x))


def fnum(x) -> float:
    return float(dnum(x))


def fmt_int(x) -> str:
    return f"{int(round(float(x))):,}".replace(",", ".")


def fmt_dec(x, n=1) -> str:
    return f"{float(x):,.{n}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x) -> str:
    return fmt_dec(x, 1) + "%"


def month_name(ym: str) -> str:
    names = {"01":"Ene", "02":"Feb", "03":"Mar", "04":"Abr", "05":"May", "06":"Jun", "07":"Jul", "08":"Ago", "09":"Sep", "10":"Oct", "11":"Nov", "12":"Dic"}
    y, m = ym.split("-")
    return f"{names.get(m, m)} {y}"


def weekday_name(iso: str) -> str:
    names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    try:
        return names[datetime.fromisoformat(iso).weekday()]
    except Exception:
        return "Sin fecha"


def route_of(r: dict) -> str:
    return (r.get("ruta_reprogramada") or r.get("ruta_programada") or "Sin ruta").strip() or "Sin ruta"


def logo_data_uri() -> str:
    if not LOGO_PATH.exists():
        return ""
    b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def add(bucket: dict, r: dict):
    bucket["viajes"] += 1
    bucket["tim"] += fnum(r.get("timbradas"))
    bucket["timr"] += fnum(r.get("timbradas_real"))
    bucket["descuento"] += fnum(r.get("descuento"))
    bucket["vehiculos"].add(r.get("codigo_vehiculo") or "Sin código")
    bucket["rutas"].add(route_of(r))
    if r.get("is_extemporaneo"):
        bucket["extemporaneos"] += 1
    if r.get("is_viaje_contable") is False:
        bucket["no_contables"] += 1


def bucket():
    return {"viajes": 0, "tim": 0.0, "timr": 0.0, "descuento": 0.0, "vehiculos": set(), "rutas": set(), "extemporaneos": 0, "no_contables": 0}


def top_items(rows: list[dict], keyfn, label_fields, limit=12):
    groups = defaultdict(bucket)
    labels = {}
    for r in rows:
        key = keyfn(r)
        add(groups[key], r)
        labels[key] = label_fields(r)
    out = []
    for key, b in groups.items():
        avg = b["timr"] / b["viajes"] if b["viajes"] else 0
        out.append({
            "key": str(key), "label": labels.get(key, str(key)), "viajes": b["viajes"],
            "tim": round(b["tim"], 1), "timr": round(b["timr"], 1),
            "descuento": round(b["descuento"], 1), "avg": round(avg, 1),
            "vehiculos": len(b["vehiculos"]), "rutas": len(b["rutas"]),
        })
    return sorted(out, key=lambda x: x["timr"], reverse=True)[:limit]


def build_data(rows: list[dict], total_count):
    for r in rows:
        r["fecha_viaje"] = str(r.get("fecha_viaje") or "")[:10]
        r["codigo_vehiculo"] = str(r.get("codigo_vehiculo") or "Sin código")
        r["placa"] = str(r.get("placa") or "")
        r["conductor_nombre"] = str(r.get("conductor_nombre") or "Sin conductor")
        r["codigo_conductor"] = str(r.get("codigo_conductor") or "")
        r["ruta"] = route_of(r)
        r["tim"] = round(fnum(r.get("timbradas")), 1)
        r["timr"] = round(fnum(r.get("timbradas_real")), 1)
        r["descuento_num"] = round(fnum(r.get("descuento")), 1)
        r["mes"] = r["fecha_viaje"][:7] if len(r["fecha_viaje"]) >= 7 else "Sin fecha"
        r["dia_semana"] = weekday_name(r["fecha_viaje"])

    overall = bucket()
    by_day = defaultdict(bucket)
    by_month = defaultdict(bucket)
    by_weekday = defaultdict(bucket)
    for r in rows:
        add(overall, r)
        add(by_day[r["fecha_viaje"]], r)
        add(by_month[r["mes"]], r)
        add(by_weekday[r["dia_semana"]], r)

    daily = []
    for k in sorted(by_day):
        b = by_day[k]
        daily.append({"fecha": k, "dia": weekday_name(k), "viajes": b["viajes"], "tim": round(b["tim"], 1), "timr": round(b["timr"], 1), "descuento": round(b["descuento"], 1), "promedio": round(b["timr"] / b["viajes"], 1) if b["viajes"] else 0, "buses": len(b["vehiculos"]), "rutas": len(b["rutas"])})
    monthly = []
    for k in sorted(by_month):
        b = by_month[k]
        monthly.append({"mes": k, "label": month_name(k) if k != "Sin fecha" else k, "viajes": b["viajes"], "tim": round(b["tim"], 1), "timr": round(b["timr"], 1), "descuento": round(b["descuento"], 1), "promedio": round(b["timr"] / b["viajes"], 1) if b["viajes"] else 0, "buses": len(b["vehiculos"]), "rutas": len(b["rutas"])})
    weekdays_order = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    weekday = []
    for k in weekdays_order:
        b = by_weekday.get(k, bucket())
        if b["viajes"]:
            weekday.append({"dia": k, "viajes": b["viajes"], "timr": round(b["timr"], 1), "promedio": round(b["timr"] / b["viajes"], 1)})

    top_bus = top_items(rows, lambda r: r["codigo_vehiculo"], lambda r: f"{r['codigo_vehiculo']} · {r['placa']}", 15)
    top_route = top_items(rows, lambda r: r["ruta"], lambda r: r["ruta"], 12)
    top_driver = top_items(rows, lambda r: r["conductor_nombre"], lambda r: r["conductor_nombre"], 12)

    best_day = max(daily, key=lambda x: x["timr"], default={"fecha":"Sin datos", "timr":0})
    avg_trip = overall["timr"] / overall["viajes"] if overall["viajes"] else 0
    tim_gap = overall["timr"] - overall["tim"]
    discount_rate = (overall["descuento"] / overall["timr"] * 100) if overall["timr"] else 0
    best_month = max(monthly, key=lambda x: x["timr"], default={"label":"Sin datos", "timr":0})
    concentration = (sum(x["timr"] for x in top_bus[:3]) / overall["timr"] * 100) if overall["timr"] else 0

    insights = [
        f"El periodo concentra {fmt_int(overall['timr'])} timbradas reales (TIM R) en {fmt_int(overall['viajes'])} viajes, con {fmt_dec(avg_trip, 1)} TIM R por viaje.",
        f"El mejor día operativo fue {best_day.get('fecha')} con {fmt_int(best_day.get('timr', 0))} TIM R.",
        f"El mes con mayor validación fue {best_month.get('label')} con {fmt_int(best_month.get('timr', 0))} TIM R.",
        f"Las 3 busetas líderes aportan {pct(concentration)} de la TIM R total; útil para monitorear concentración operativa.",
        f"La diferencia TIM R vs timbradas registradas es {fmt_int(tim_gap)}; úsela como alerta para revisar descuentos, transbordos o ajustes de validación.",
        f"Los descuentos suman {fmt_int(overall['descuento'])}, equivalentes al {pct(discount_rate)} de la TIM R.",
    ]

    compact_rows = [{
        "fecha": r["fecha_viaje"], "mes": r["mes"], "vehiculo": r["codigo_vehiculo"], "placa": r["placa"],
        "ruta": r["ruta"], "conductor": r["conductor_nombre"], "viaje": r.get("viaje") or "", "tim": r["tim"],
        "timr": r["timr"], "descuento": r["descuento_num"], "estado": r.get("estado") or "", "novedad": r.get("novedad") or "",
        "extemporaneo": bool(r.get("is_extemporaneo")), "contable": r.get("is_viaje_contable") is not False,
    } for r in rows]

    return {
        "meta": {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "source": "Supabase / viajes_recaudados", "filter": "codigo_vehiculo like 10* · fecha_viaje 2026", "rows": len(rows), "total_count_header": total_count, "period": f"{daily[0]['fecha']} a {daily[-1]['fecha']}" if daily else "Sin registros"},
        "kpis": {"timr": round(overall["timr"], 1), "tim": round(overall["tim"], 1), "descuento": round(overall["descuento"], 1), "tim_gap": round(tim_gap, 1), "viajes": overall["viajes"], "buses": len(overall["vehiculos"]), "rutas": len(overall["rutas"]), "avg_trip": round(avg_trip, 1), "discount_rate": round(discount_rate, 2), "best_day": best_day, "best_month": best_month},
        "monthly": monthly, "daily": daily, "weekday": weekday, "top_bus": top_bus, "top_route": top_route, "top_driver": top_driver, "insights": insights, "rows": compact_rows,
        "filters": {"months": sorted(set(r["mes"] for r in rows)), "vehicles": sorted(set(r["codigo_vehiculo"] for r in rows)), "routes": sorted(set(r["ruta"] for r in rows))},
    }


def write_csv(data: dict):
    path = OUT_PRIVATE / "timbradas_vehiculos_10_2026_detalle.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        fields = ["fecha", "mes", "vehiculo", "placa", "ruta", "conductor", "viaje", "tim", "timr", "descuento", "estado", "novedad", "extemporaneo", "contable"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(data["rows"])
    return path


def render_html(data: dict) -> str:
    data_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    logo = logo_data_uri()
    logo_html = f'<img src="{logo}" alt="Logo La Carolina">' if logo else 'LC'
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dashboard timbradas busetas 10* · La Carolina</title>
<style>
:root{{--red:#bf2026;--red2:#7c1116;--gold:#d7b85f;--dark:#151b1e;--ink:#18212a;--muted:#69727d;--bg:#f4f0e7;--card:#fffdf7;--line:#e8dfce;--ok:#16734f;--warn:#a15c00;--blue:#1769aa}}
*{{box-sizing:border-box}} html{{scroll-behavior:smooth}} body{{margin:0;background:linear-gradient(180deg,#1b1111 0,#f4f0e7 360px);font-family:Inter,Segoe UI,Roboto,Arial,sans-serif;color:var(--ink)}}
.hero{{color:white;padding:28px clamp(16px,4vw,48px) 86px;background:radial-gradient(circle at 15% 0,rgba(215,184,95,.30),transparent 30%),linear-gradient(135deg,#17191c 0%,#330a10 52%,#bf2026 100%);border-bottom:6px solid var(--gold)}}
.brand{{display:flex;align-items:center;gap:14px;margin-bottom:22px}} .logo{{width:74px;height:74px;border-radius:20px;background:#fff;display:grid;place-items:center;overflow:hidden;box-shadow:0 14px 28px rgba(0,0,0,.28);color:#111;font-weight:900;font-size:28px}} .logo img{{width:100%;height:100%;object-fit:contain;padding:6px}}
.eyebrow{{display:inline-flex;gap:8px;align-items:center;background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.20);border-radius:999px;padding:7px 12px;color:#ffeab0;font-weight:800;font-size:12px;letter-spacing:.06em;text-transform:uppercase}}
h1{{font-size:clamp(28px,5vw,56px);line-height:1.02;margin:14px 0 10px;max-width:1050px}} .subtitle{{color:#ffeab0;font-size:clamp(15px,2vw,20px);font-weight:650;max-width:980px}} .hero-grid{{display:grid;grid-template-columns:1.4fr .8fr;gap:26px;align-items:end}} .hero-panel{{background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.18);border-radius:24px;padding:18px;backdrop-filter:blur(10px)}} .hero-panel strong{{color:#fff5c7}}
main{{max-width:1480px;margin:-58px auto 70px;padding:0 clamp(12px,3vw,34px)}} .kpis{{display:grid;grid-template-columns:repeat(6,minmax(160px,1fr));gap:14px}} .kpi{{background:var(--card);border:1px solid var(--line);border-radius:22px;padding:18px;box-shadow:0 18px 40px rgba(21,27,30,.13);position:relative;overflow:hidden}} .kpi:before{{content:"";position:absolute;inset:0 0 auto 0;height:5px;background:linear-gradient(90deg,var(--gold),var(--red))}} .label{{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:850}} .value{{font-size:clamp(24px,3vw,36px);font-weight:950;margin-top:8px;color:var(--dark)}} .hint{{font-size:12px;color:var(--muted);margin-top:7px;line-height:1.35}}
.card{{background:rgba(255,253,247,.96);border:1px solid var(--line);border-radius:24px;margin-top:18px;padding:20px;box-shadow:0 10px 26px rgba(21,27,30,.08)}} .section-title{{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;margin-bottom:14px}} h2,h3{{margin:0;color:var(--dark)}} .small{{font-size:13px;color:var(--muted)}}
.filters{{display:grid;grid-template-columns:repeat(4,minmax(160px,1fr));gap:12px;position:sticky;top:0;z-index:8;background:rgba(244,240,231,.88);backdrop-filter:blur(12px);padding:12px;border:1px solid var(--line);border-radius:22px;margin-top:18px}} select,input{{width:100%;border:1px solid #d9cfbd;border-radius:15px;background:white;padding:12px 13px;font:inherit;color:var(--ink)}} .actions{{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}} button,.btn{{border:0;border-radius:14px;padding:11px 14px;font-weight:900;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:8px}} .primary{{background:linear-gradient(135deg,var(--gold),#fff0a8);color:#241a00}} .secondary{{background:#231f20;color:white}}
.grid-2{{display:grid;grid-template-columns:1.2fr .8fr;gap:18px}} .grid-3{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}} canvas{{width:100%;height:310px;border-radius:18px;background:linear-gradient(180deg,#fff,#fffaf0);border:1px solid #efe4cf}} .legend{{display:flex;gap:12px;flex-wrap:wrap;margin-top:10px;color:var(--muted);font-size:13px}} .dot{{width:12px;height:12px;border-radius:50%;display:inline-block;background:var(--red)}} .dot.gold{{background:var(--gold)}} .dot.blue{{background:var(--blue)}}
.insights{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}} .insight{{background:linear-gradient(180deg,#fff9e8,#fff);border:1px solid #ead9ac;border-radius:18px;padding:15px;line-height:1.42}} .insight b{{color:var(--red2)}}
.table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:18px;background:white}} table{{width:100%;border-collapse:collapse;min-width:980px}} th{{position:sticky;top:0;background:#20262d;color:#fff;text-align:left;padding:11px 12px;font-size:12px;letter-spacing:.04em;text-transform:uppercase;z-index:1}} td{{border-bottom:1px solid #eee4d2;padding:10px 12px;vertical-align:top}} tr:hover td{{background:#fff8dc}} .right{{text-align:right;white-space:nowrap}} .badge{{display:inline-flex;border-radius:999px;padding:4px 9px;background:#f2e7c7;color:#5f4500;font-weight:850;font-size:12px}} .badge.ok{{background:#dff5ec;color:#0d5f3d}} .badge.warn{{background:#fff0d2;color:#8a4a00}}
.rank{{display:grid;gap:10px}} .rank-row{{display:grid;grid-template-columns:minmax(130px,1fr) 90px;gap:10px;align-items:center}} .bar{{height:13px;background:#eee2ca;border-radius:999px;overflow:hidden;margin-top:5px}} .bar span{{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,var(--gold),var(--red))}} footer{{text-align:center;color:#6b6255;padding:30px;font-size:12px}}
@media(max-width:1150px){{.kpis{{grid-template-columns:repeat(3,1fr)}}.hero-grid,.grid-2,.grid-3,.insights{{grid-template-columns:1fr}}}}
@media(max-width:760px){{.hero{{padding-bottom:42px}}main{{margin-top:-24px}}.kpis{{grid-template-columns:1fr 1fr}}.filters{{grid-template-columns:1fr;position:relative}}.card{{padding:15px;border-radius:18px}}canvas{{height:260px}}.value{{font-size:25px}}}}
@media(max-width:460px){{.kpis{{grid-template-columns:1fr}}.brand{{align-items:flex-start}}.logo{{width:58px;height:58px}}}}
</style>
</head>
<body>
<header class="hero">
  <div class="hero-grid">
    <div>
      <div class="brand"><div class="logo">{logo_html}</div><div><strong>La Carolina</strong><div class="subtitle">Transporte con Corazón</div></div></div>
      <span class="eyebrow">Dashboard operativo · Timbradas</span>
      <h1>Busetas código 10*: validación de pasajeros y eficiencia operativa</h1>
      <div class="subtitle">Experiencia interactiva enfocada en TIM R, timbradas netas, descuentos, viajes, buses activos, rutas e insights accionables.</div>
    </div>
    <div class="hero-panel"><strong>Fuente:</strong> Supabase / viajes_recaudados<br><strong>Filtro:</strong> código vehículo 10* · fecha viaje 2026<br><strong>Periodo:</strong> <span id="periodHero"></span><br><strong>Generado:</strong> {html.escape(data['meta']['generated_at'])}</div>
  </div>
</header>
<main>
  <section class="kpis" id="kpis"></section>
  <section class="filters" aria-label="Filtros interactivos">
    <div><label class="label">Mes</label><select id="monthFilter"><option value="">Todos</option></select></div>
    <div><label class="label">Buseta</label><select id="vehicleFilter"><option value="">Todas</option></select></div>
    <div><label class="label">Ruta</label><select id="routeFilter"><option value="">Todas</option></select></div>
    <div><label class="label">Buscar</label><input id="searchBox" placeholder="placa, conductor, viaje, novedad..."></div>
  </section>
  <div class="actions"><button class="primary" onclick="resetFilters()">Limpiar filtros</button><button class="secondary" onclick="window.print()">Imprimir / PDF</button><a class="btn primary" href="/api/csv">Descargar CSV detalle</a><span class="small" id="visibleCount"></span></div>

  <section class="card">
    <div class="section-title"><div><h2>Insights operativos</h2><div class="small">Lecturas automáticas de la base consultada, recalculadas con los filtros.</div></div></div>
    <div class="insights" id="insights"></div>
  </section>

  <section class="grid-2">
    <div class="card"><div class="section-title"><div><h2>Evolución diaria</h2><div class="small">Timbradas reales (TIM R) por fecha de viaje.</div></div></div><canvas id="dailyChart"></canvas><div class="legend"><span><i class="dot"></i> TIM R</span><span><i class="dot gold"></i> Promedio móvil visual</span></div></div>
    <div class="card"><div class="section-title"><div><h2>Comportamiento por día</h2><div class="small">TIM R y promedio por viaje según día de semana.</div></div></div><canvas id="weekdayChart"></canvas><div class="legend"><span><i class="dot blue"></i> TIM R</span></div></div>
  </section>

  <section class="grid-3">
    <div class="card"><h2>Top busetas por TIM R</h2><div id="rankBus" class="rank"></div></div>
    <div class="card"><h2>Top rutas por TIM R</h2><div id="rankRoute" class="rank"></div></div>
    <div class="card"><h2>Top conductores por TIM R</h2><div id="rankDriver" class="rank"></div></div>
  </section>

  <section class="card">
    <div class="section-title"><div><h2>Resumen mensual</h2><div class="small">Sin valores monetarios: foco exclusivo en validación y operación.</div></div></div>
    <div class="table-wrap"><table><thead><tr><th>Mes</th><th class="right">Viajes</th><th class="right">TIM</th><th class="right">TIM R</th><th class="right">Descuentos</th><th class="right">TIM R / viaje</th><th class="right">Buses</th><th class="right">Rutas</th></tr></thead><tbody id="monthlyBody"></tbody></table></div>
  </section>

  <section class="card">
    <div class="section-title"><div><h2>Detalle de viajes</h2><div class="small">Tabla interactiva con los primeros 300 registros visibles según filtros.</div></div></div>
    <div class="table-wrap"><table><thead><tr><th>Fecha</th><th>Buseta</th><th>Placa</th><th>Ruta</th><th>Conductor</th><th>Viaje</th><th class="right">TIM</th><th class="right">TIM R</th><th class="right">Desc.</th><th>Estado</th></tr></thead><tbody id="detailBody"></tbody></table></div>
  </section>
</main>
<footer>La Carolina · Transporte con Corazón · Dashboard protegido en Vercel · Sin valores monetarios</footer>
<script id="dashboard-data" type="application/json">{data_json}</script>
<script>
const DATA = JSON.parse(document.getElementById('dashboard-data').textContent);
const $ = id => document.getElementById(id);
const nf = new Intl.NumberFormat('es-CO', {{maximumFractionDigits:0}});
const nfd = new Intl.NumberFormat('es-CO', {{maximumFractionDigits:1}});
function sum(rows, field){{return rows.reduce((a,r)=>a+(Number(r[field])||0),0)}}
function group(rows, keyFn){{const m=new Map(); for(const r of rows){{const k=keyFn(r); if(!m.has(k)) m.set(k,[]); m.get(k).push(r)}} return m}}
function agg(rows){{const viajes=rows.length,tim=sum(rows,'tim'),timr=sum(rows,'timr'),des=sum(rows,'descuento'); const buses=new Set(rows.map(r=>r.vehiculo)).size; const rutas=new Set(rows.map(r=>r.ruta)).size; return {{viajes,tim,timr,des,buses,rutas,avg:viajes?timr/viajes:0,gap:timr-tim,discRate:timr?des/timr*100:0}}}}
function opts(id, vals, labels={{}}){{const el=$(id); vals.forEach(v=>{{const o=document.createElement('option'); o.value=v; o.textContent=labels[v]||v; el.appendChild(o)}})}}
opts('monthFilter', DATA.filters.months, Object.fromEntries(DATA.monthly.map(m=>[m.mes,m.label]))); opts('vehicleFilter', DATA.filters.vehicles); opts('routeFilter', DATA.filters.routes);
function filteredRows(){{const m=$('monthFilter').value,v=$('vehicleFilter').value,rt=$('routeFilter').value,q=$('searchBox').value.trim().toLowerCase(); return DATA.rows.filter(r=>(!m||r.mes===m)&&(!v||r.vehiculo===v)&&(!rt||r.ruta===rt)&&(!q||[r.fecha,r.vehiculo,r.placa,r.ruta,r.conductor,r.viaje,r.estado,r.novedad].join(' ').toLowerCase().includes(q)))}}
function kpi(label,value,hint){{return `<div class="kpi"><div class="label">${{label}}</div><div class="value">${{value}}</div><div class="hint">${{hint||''}}</div></div>`}}
function renderKPIs(rows){{const a=agg(rows); $('kpis').innerHTML=[kpi('TIM R total',nf.format(a.timr),'Timbradas reales / validaciones control'),kpi('Timbradas netas',nf.format(a.tim),'Registro neto operativo'),kpi('Descuentos',nf.format(a.des),`${{nfd.format(a.discRate)}}% sobre TIM R`),kpi('Viajes',nf.format(a.viajes),`${{nfd.format(a.avg)}} TIM R por viaje`),kpi('Buses activos',nf.format(a.buses),'Vehículos código 10* con operación'),kpi('Rutas activas',nf.format(a.rutas),'Rutas observadas en el filtro')].join('')}}
function renderInsights(rows){{const a=agg(rows); const byDay=[...group(rows,r=>r.fecha)].map(([k,rs])=>({{fecha:k,timr:sum(rs,'timr'),viajes:rs.length}})).sort((x,y)=>y.timr-x.timr); const byBus=[...group(rows,r=>r.vehiculo+' · '+r.placa)].map(([k,rs])=>({{k,timr:sum(rs,'timr')}})).sort((x,y)=>y.timr-x.timr); const byRoute=[...group(rows,r=>r.ruta)].map(([k,rs])=>({{k,timr:sum(rs,'timr')}})).sort((x,y)=>y.timr-x.timr); const top3=byBus.slice(0,3).reduce((s,x)=>s+x.timr,0); const conc=a.timr?top3/a.timr*100:0; const list=[`<b>Mayor día:</b> ${{byDay[0]?.fecha||'Sin datos'}} con ${{nf.format(byDay[0]?.timr||0)}} TIM R.`, `<b>Buseta líder:</b> ${{byBus[0]?.k||'Sin datos'}} con ${{nf.format(byBus[0]?.timr||0)}} TIM R.`, `<b>Ruta principal:</b> ${{byRoute[0]?.k||'Sin datos'}} concentra ${{nf.format(byRoute[0]?.timr||0)}} TIM R.`, `<b>Concentración:</b> top 3 busetas aportan ${{nfd.format(conc)}}% de la TIM R visible.`, `<b>Brecha TIM R vs TIM:</b> ${{nf.format(a.gap)}} validaciones; revisar descuentos/transbordos/ajustes si crece.`, `<b>Productividad:</b> ${{nfd.format(a.avg)}} TIM R por viaje en el filtro actual.`]; $('insights').innerHTML=list.map(x=>`<div class="insight">${{x}}</div>`).join('')}}
function drawBars(canvasId, items, labelKey, valueKey, color='#bf2026'){{const c=$(canvasId),ctx=c.getContext('2d'),dpr=window.devicePixelRatio||1; const W=c.clientWidth*dpr,H=c.clientHeight*dpr; c.width=W;c.height=H;ctx.scale(dpr,dpr); const w=c.clientWidth,h=c.clientHeight; ctx.clearRect(0,0,w,h); ctx.font='12px Arial'; ctx.fillStyle='#69727d'; const pad=42; const max=Math.max(...items.map(x=>x[valueKey]),1); const bw=Math.max(8,(w-pad*2)/items.length*.72); items.forEach((it,i)=>{{const x=pad+i*((w-pad*2)/items.length)+((w-pad*2)/items.length-bw)/2; const bh=(h-pad*2)*(it[valueKey]/max); const y=h-pad-bh; const grad=ctx.createLinearGradient(0,y,0,h-pad); grad.addColorStop(0,color); grad.addColorStop(1,'#d7b85f'); ctx.fillStyle=grad; ctx.fillRect(x,y,bw,bh); if(items.length<18){{ctx.save();ctx.translate(x+bw/2,h-12);ctx.rotate(-0.75);ctx.fillStyle='#4b5563';ctx.textAlign='right';ctx.fillText(String(it[labelKey]).slice(5)||it[labelKey],0,0);ctx.restore()}} }}); ctx.fillStyle='#20262d'; ctx.font='bold 13px Arial'; ctx.fillText('Timbradas reales (TIM R)',pad,18); }}
function rankHtml(items){{const max=Math.max(...items.map(x=>x.timr),1); return items.slice(0,12).map(x=>`<div class="rank-row"><div><b>${{x.label||x.k||x.key}}</b><div class="bar"><span style="width:${{Math.max(3,x.timr/max*100)}}%"></span></div><div class="small">${{nf.format(x.viajes||0)}} viajes · ${{nfd.format(x.avg||0)}} TIM R/viaje</div></div><div class="right"><b>${{nf.format(x.timr)}}</b><div class="small">TIM R</div></div></div>`).join('')}}
function topFrom(rows,key,label){{return [...group(rows,key)].map(([k,rs])=>{{const a=agg(rs); return {{label:label(k,rs),timr:a.timr,viajes:a.viajes,avg:a.avg}}}}).sort((a,b)=>b.timr-a.timr)}}
function renderTables(rows){{const months=[...group(rows,r=>r.mes)].map(([m,rs])=>{{const a=agg(rs); return {{m,label:(DATA.monthly.find(x=>x.mes===m)||{{label:m}}).label,...a}}}}).sort((a,b)=>a.m.localeCompare(b.m)); $('monthlyBody').innerHTML=months.map(x=>`<tr><td><b>${{x.label}}</b></td><td class="right">${{nf.format(x.viajes)}}</td><td class="right">${{nf.format(x.tim)}}</td><td class="right"><b>${{nf.format(x.timr)}}</b></td><td class="right">${{nf.format(x.des)}}</td><td class="right">${{nfd.format(x.avg)}}</td><td class="right">${{nf.format(x.buses)}}</td><td class="right">${{nf.format(x.rutas)}}</td></tr>`).join(''); $('detailBody').innerHTML=rows.slice(0,300).map(r=>`<tr><td>${{r.fecha}}</td><td><b>${{r.vehiculo}}</b></td><td>${{r.placa}}</td><td>${{r.ruta}}</td><td>${{r.conductor}}</td><td>${{r.viaje}}</td><td class="right">${{nf.format(r.tim)}}</td><td class="right"><b>${{nf.format(r.timr)}}</b></td><td class="right">${{nf.format(r.descuento)}}</td><td><span class="badge ${{r.contable?'ok':'warn'}}">${{r.estado||'Sin estado'}}</span></td></tr>`).join('')}}
function renderRanks(rows){{$('rankBus').innerHTML=rankHtml(topFrom(rows,r=>r.vehiculo,r=>r)); $('rankRoute').innerHTML=rankHtml(topFrom(rows,r=>r.ruta,r=>r)); $('rankDriver').innerHTML=rankHtml(topFrom(rows,r=>r.conductor,r=>r));}}
function update(){{const rows=filteredRows(); $('periodHero').textContent=DATA.meta.period; $('visibleCount').textContent=`${{nf.format(rows.length)}} viajes visibles de ${{nf.format(DATA.rows.length)}} consultados`; renderKPIs(rows); renderInsights(rows); renderTables(rows); renderRanks(rows); const daily=[...group(rows,r=>r.fecha)].map(([fecha,rs])=>({{fecha,timr:sum(rs,'timr')}})).sort((a,b)=>a.fecha.localeCompare(b.fecha)); drawBars('dailyChart',daily,'fecha','timr','#bf2026'); const order=['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']; const wd=order.map(d=>{{const rs=rows.filter(r=>new Date(r.fecha+'T00:00:00').toLocaleDateString('es-CO',{{weekday:'long'}}).replace(/^./,c=>c.toUpperCase())===d); return {{dia:d,timr:sum(rs,'timr')}}}}).filter(x=>x.timr); drawBars('weekdayChart',wd,'dia','timr','#1769aa');}}
function resetFilters(){{$('monthFilter').value='';$('vehicleFilter').value='';$('routeFilter').value='';$('searchBox').value='';update()}}
['monthFilter','vehicleFilter','routeFilter'].forEach(id=>$(id).addEventListener('change',update)); $('searchBox').addEventListener('input',update); window.addEventListener('resize',()=>setTimeout(update,80)); update();
</script>
</body>
</html>"""


def main():
    rows, total = supabase_get("viajes_recaudados", [
        ("select", SELECT),
        ("codigo_vehiculo", "like.10*"),
        ("fecha_viaje", "gte.2026-01-01"),
        ("fecha_viaje", "lt.2027-01-01"),
        ("order", "fecha_viaje.asc,codigo_vehiculo.asc"),
    ])
    data = build_data(rows, total)
    csv_path = write_csv(data)
    html_path = OUT_PRIVATE / "report.html"
    html_path.write_text(render_html(data), encoding="utf-8")
    print(f"Filas consultadas: {len(rows)} de {total}")
    print(f"Periodo: {data['meta']['period']}")
    print(f"TIM R: {fmt_int(data['kpis']['timr'])}")
    print(f"Viajes: {fmt_int(data['kpis']['viajes'])}")
    print(f"Buses: {fmt_int(data['kpis']['buses'])}")
    print(f"HTML: {html_path}")
    print(f"CSV: {csv_path}")


if __name__ == "__main__":
    main()
