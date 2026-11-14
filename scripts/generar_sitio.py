"""Genera sitio/index.html y sitio/informe_evidently.html (Quantity y UnitPrice)."""
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from evidently import ColumnMapping
from evidently.metric_preset import DataDriftPreset
from evidently.report import Report

AUTOR = "Amira Roman"
FUENTE = ("Online Retail, UCI Machine Learning Repository "
          "(muestra de 12.000 filas por mes, Reino Unido, 2011)")
MESES = {"referencia": "septiembre", "control": "octubre", "nuevo": "noviembre"}
NOMBRES = {"Quantity": "Cantidad (unidades por fila)", "UnitPrice": "Precio unitario (£)"}
DATOS = Path("datos")
SALIDA = Path("sitio")

CSS = """
:root{--bg:#f5f7fb;--card:#fff;--txt:#1f2937;--mut:#6b7280;--brd:#e5e7eb;
--pri:#4f46e5;--ok:#15803d;--okbg:#dcfce7;--warn:#b45309;--warnbg:#fef3c7}
@media (prefers-color-scheme:dark){:root{--bg:#0f172a;--card:#1e293b;--txt:#e5e7eb;
--mut:#94a3b8;--brd:#334155;--pri:#818cf8;--ok:#86efac;--okbg:#14532d;--warn:#fcd34d;--warnbg:#78350f}}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
background:var(--bg);color:var(--txt);line-height:1.5}
header{background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff;padding:2.2rem 1rem}
.wrap{max-width:860px;margin:0 auto;padding:0 1rem}
header .wrap{padding:0}
header h1{margin:0 0 .3rem;font-size:1.6rem}
header p{margin:0;opacity:.9}
main{padding:1.5rem 0 1rem}
h2{font-size:1.15rem;margin:1.6rem 0 .8rem}
.tag{display:inline-block;background:var(--pri);color:#fff;border-radius:999px;
padding:.15rem .8rem;font-size:.85rem;font-weight:600}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:1rem}
.card{background:var(--card);border:1px solid var(--brd);border-radius:12px;padding:1.1rem}
.card .l{color:var(--mut);font-size:.85rem}
.card .v{font-size:1.7rem;font-weight:700;margin-top:.2rem}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--brd);
border-radius:12px;overflow:hidden}
th,td{padding:.7rem .9rem;text-align:left;border-bottom:1px solid var(--brd)}
th{font-size:.8rem;text-transform:uppercase;letter-spacing:.04em;color:var(--mut)}
tr:last-child td{border-bottom:0}
.b{display:inline-block;border-radius:999px;padding:.1rem .7rem;font-size:.82rem;font-weight:600}
.si{background:var(--warnbg);color:var(--warn)} .no{background:var(--okbg);color:var(--ok)}
.btn{display:inline-block;background:var(--pri);color:#fff;text-decoration:none;
padding:.7rem 1.2rem;border-radius:10px;font-weight:600;margin-top:1rem}
.btn:hover{opacity:.9}
.nota{color:var(--mut);font-size:.9rem;margin-top:.6rem}
footer{border-top:1px solid var(--brd);margin-top:2rem;padding:1.2rem 0 2rem;
color:var(--mut);font-size:.88rem}
footer b{color:var(--txt)} a{color:var(--pri)}
"""


def main():
    ref = pd.read_csv(DATOS / "referencia.csv")
    act = pd.read_csv(DATOS / "actual.csv")
    mes = MESES[act["lote"].iloc[0]]
    cols = ["Quantity", "UnitPrice"]

    mapping = ColumnMapping(numerical_features=cols)
    report = Report(metrics=[DataDriftPreset(columns=cols)])
    report.run(reference_data=ref[cols], current_data=act[cols], column_mapping=mapping)

    if SALIDA.exists():
        shutil.rmtree(SALIDA)
    SALIDA.mkdir()
    report.save_html(str(SALIDA / "informe_evidently.html"))

    metricas = {m["metric"]: m["result"] for m in report.as_dict()["metrics"]}
    tabla = metricas["DataDriftTable"]
    drift_global = tabla["dataset_drift"]
    detalle = tabla["drift_by_columns"]
    filas_drift = "".join(
        f"<tr><td>{NOMBRES[c]}</td><td>{detalle[c]['stattest_name']}</td>"
        f"<td>{detalle[c]['drift_score']:.4f}</td>"
        f"<td><span class=\"b {'si' if detalle[c]['drift_detected'] else 'no'}\">"
        f"{'Drift detectado' if detalle[c]['drift_detected'] else 'Sin drift'}</span></td></tr>"
        for c in cols
    )
    n_drift = sum(detalle[c]["drift_detected"] for c in cols)
    resumen = (f"Evidently detectó cambio de distribución en {n_drift} de 2 columnas "
               f"al comparar {mes} con septiembre.")

    sha = os.environ.get("GITHUB_SHA", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    commit = sha[:7] if sha else "local"
    commit_html = (f'<a href="https://github.com/{repo}/commit/{sha}">{commit}</a>'
                   if repo and sha else commit)
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Monitoreo de ventas de regalos</title>
<style>{CSS}</style></head><body>
<header><div class="wrap">
<h1>Monitoreo de ventas · tienda de regalos en línea</h1>
<p>Cada lote válido se compara con septiembre de 2011 antes de publicarse.</p>
</div></header>
<main><div class="wrap">
<h2>Último lote publicado <span class="tag">{mes.capitalize()} 2011</span></h2>
<div class="grid">
<div class="card"><div class="l">Mes actual</div><div class="v">{mes.capitalize()}</div></div>
<div class="card"><div class="l">Filas analizadas</div><div class="v">{len(act):,}</div></div>
<div class="card"><div class="l">Mediana de unidades por fila</div><div class="v">{act['Quantity'].median():g}</div></div>
<div class="card"><div class="l">Mediana del precio unitario</div><div class="v">£ {act['UnitPrice'].median():.2f}</div></div>
</div>
<h2>Cambio de distribución frente a septiembre</h2>
<table><tr><th>Columna</th><th>Prueba</th><th>Puntaje</th><th>Resultado</th></tr>{filas_drift}</table>
<p class="nota">{resumen} Un lote válido se publica aunque haya drift.</p>
<a class="btn" href="informe_evidently.html">Comparar {mes} con septiembre</a>
</div></main>
<footer><div class="wrap">
<b>Autor:</b> {AUTOR}<br>
<b>Fuente:</b> {FUENTE}<br>
<b>Generado:</b> {fecha}<br>
<b>Commit:</b> {commit_html}
</div></footer></body></html>"""
    (SALIDA / "index.html").write_text(html, encoding="utf-8")
    print(f"Sitio generado para {mes}. Drift global: {drift_global}")


if __name__ == "__main__":
    main()