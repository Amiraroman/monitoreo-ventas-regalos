"""Genera sitio/index.html y sitio/informe_evidently.html (Quantity y UnitPrice)."""
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from evidently import ColumnMapping
from evidently.metric_preset import DataDriftPreset
from evidently.report import Report

AUTOR = "TU NOMBRE AQUÍ"  # <-- cambia esto
FUENTE = ("Online Retail, UCI Machine Learning Repository "
          "(muestra de 12.000 filas por mes, Reino Unido, 2011)")
MESES = {"referencia": "septiembre", "control": "octubre", "nuevo": "noviembre"}
DATOS = Path("datos")
SALIDA = Path("sitio")


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
        f"<tr><td>{c}</td><td>{detalle[c]['stattest_name']}</td>"
        f"<td>{detalle[c]['drift_score']:.4f}</td>"
        f"<td>{'Sí' if detalle[c]['drift_detected'] else 'No'}</td></tr>"
        for c in cols
    )

    commit = os.environ.get("GITHUB_SHA", "local")[:7]
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    commit_html = (f'<a href="https://github.com/{repo}/commit/{os.environ["GITHUB_SHA"]}">{commit}</a>'
                   if repo and "GITHUB_SHA" in os.environ else commit)
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Monitoreo de ventas de regalos</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:760px;margin:2rem auto;padding:0 1rem;color:#222}}
table{{border-collapse:collapse;width:100%;margin:1rem 0}}
td,th{{border:1px solid #ccc;padding:.5rem;text-align:left}}
.k{{background:#f4f6f8}} footer{{margin-top:2rem;font-size:.9rem;color:#555}}
</style></head><body>
<h1>Monitoreo de ventas de una tienda de regalos en línea</h1>
<h2>Último lote publicado</h2>
<table>
<tr><th class="k">Mes actual</th><td>{mes.capitalize()} de 2011</td></tr>
<tr><th class="k">Filas analizadas</th><td>{len(act):,}</td></tr>
<tr><th class="k">Mediana de unidades por fila</th><td>{act['Quantity'].median():g}</td></tr>
<tr><th class="k">Mediana del precio unitario</th><td>£ {act['UnitPrice'].median():.2f}</td></tr>
</table>
<h2>Cambio de distribución frente a septiembre</h2>
<p>Drift global del conjunto: <strong>{'detectado' if drift_global else 'no detectado'}</strong></p>
<table><tr><th>Columna</th><th>Prueba</th><th>Puntaje</th><th>Drift</th></tr>{filas_drift}</table>
<p><a href="informe_evidently.html">Comparar {mes} con septiembre</a></p>
<footer>
<p>Autor: {AUTOR}<br>Fuente: {FUENTE}<br>
Generado: {fecha}<br>Commit: {commit_html}</p>
</footer></body></html>"""
    (SALIDA / "index.html").write_text(html, encoding="utf-8")
    print(f"Sitio generado para {mes}. Drift global: {drift_global}")


if __name__ == "__main__":
    main()
