"""Valida referencia.csv y actual.csv. Termina con error (exit 1) si algo falla."""
import math
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

COLUMNAS = ["InvoiceNo", "StockCode", "Description", "InvoiceDate",
            "Quantity", "UnitPrice", "lote"]
FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"
RE_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
# lote -> (año, mes) esperado
MES_LOTE = {"referencia": (2011, 9), "control": (2011, 10), "nuevo": (2011, 11)}


def validar_archivo(ruta, lotes_permitidos, un_solo_lote=False):
    """Devuelve una lista de mensajes de error (vacía si todo está bien)."""
    ruta = Path(ruta)
    nombre = ruta.name
    errores = []
    try:
        df = pd.read_csv(ruta, dtype=str, keep_default_na=False, sep=",")
    except Exception as e:
        return [f"{nombre}: no se pudo leer el archivo ({e})"]

    faltantes = [c for c in COLUMNAS if c not in df.columns]
    if faltantes or len(df.columns) != len(COLUMNAS):
        return [f"{nombre}: encabezado incorrecto. Faltan {faltantes}; "
                f"se esperaban exactamente {COLUMNAS}, se encontró {list(df.columns)}"]
    if len(df) < 1:
        return [f"{nombre}: el archivo no contiene filas de datos"]

    for i, fila in df.iterrows():
        linea = i + 2  # línea 1 = encabezado

        def err(campo, motivo):
            errores.append(f"{nombre}, fila {linea}, campo {campo}: {motivo}")

        for campo in ("InvoiceNo", "StockCode", "Description"):
            if fila[campo].strip() == "":
                err(campo, "está vacío")

        fecha_txt = fila["InvoiceDate"].strip()
        fecha = None
        if not RE_FECHA.match(fecha_txt):
            err("InvoiceDate", f"'{fila['InvoiceDate']}' no tiene formato AAAA-MM-DD HH:MM:SS")
        else:
            try:
                fecha = datetime.strptime(fecha_txt, FORMATO_FECHA)
            except ValueError:
                err("InvoiceDate", f"'{fecha_txt}' no es una fecha y hora real")

        q = fila["Quantity"].strip()
        if not re.fullmatch(r"\d+", q) or int(q) <= 0:
            err("Quantity", f"'{fila['Quantity']}' no es un entero positivo")

        p = fila["UnitPrice"].strip()
        try:
            valor = float(p)
            if not math.isfinite(valor) or valor <= 0:
                raise ValueError
        except ValueError:
            err("UnitPrice", f"'{fila['UnitPrice']}' no es un número finito mayor que cero")

        lote = fila["lote"].strip()
        if lote not in lotes_permitidos:
            err("lote", f"'{lote}' no permitido; se esperaba uno de {sorted(lotes_permitidos)}")
        elif fecha is not None and (fecha.year, fecha.month) != MES_LOTE[lote]:
            a, m = MES_LOTE[lote]
            err("InvoiceDate", f"{fecha_txt} no corresponde al lote '{lote}' ({a}-{m:02d})")

    if un_solo_lote:
        lotes = set(df["lote"].str.strip())
        if len(lotes) > 1:
            errores.append(f"{nombre}: contiene más de un lote {sorted(lotes)}; debe tener uno solo")
    return errores


def main(carpeta="datos"):
    carpeta = Path(carpeta)
    errores = []
    errores += validar_archivo(carpeta / "referencia.csv", {"referencia"}, un_solo_lote=True)
    errores += validar_archivo(carpeta / "actual.csv", {"control", "nuevo"}, un_solo_lote=True)
    if errores:
        print("VALIDACIÓN FALLIDA:")
        for e in errores[:50]:
            print(" -", e)
        if len(errores) > 50:
            print(f" ... y {len(errores) - 50} errores más")
        return 1
    print("Validación correcta: referencia.csv y actual.csv son válidos.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "datos"))
