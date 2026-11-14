"""
05_extraer_por_resolucion.py   (SECCION 2: COPIAR los DICOM ORIGINALES por resolucion)
Para cada estudio BI-RADS 2 / 4 / 5 crea UNA CARPETA POR CADA RESOLUCION que tenga las
4 vistas completas y copia ahi los DICOM originales (sin modificarlos):

    SALIDA/BIRADS_5/B5-0001_3062x2394/B5-0001_R_CC.dcm  (y L_CC, R_MLO, L_MLO)
    SALIDA/BIRADS_5/B5-0001_2294x1914/B5-0001_R_CC.dcm  (...)

Asi abres el visor, lees el nombre de la carpeta y sabes que tamano estas viendo.
Si dentro de una misma resolucion una vista se repitio, se queda la toma mas reciente.
Si una resolucion NO tiene las 4 vistas, no se copia (queda anotada en el CSV).
Si un mismo codigo esta en dos estudios, el segundo lleva el sufijo _dup2 en la carpeta.

Uso:
    python 05_extraer_por_resolucion.py "E:\\DATOS DICOM" "E:\\dicom4vistas_res" --solo-indice
    python 05_extraer_por_resolucion.py "E:\\DATOS DICOM" "E:\\dicom4vistas_res"
    python 05_extraer_por_resolucion.py "E:\\DATOS DICOM" "E:\\dicom4vistas_res" --solo-multiples

Opciones:
    --solo-indice     no copia nada; solo genera CSV y conteos
    --solo-multiples  copia unicamente los estudios con MAS DE UNA resolucion completa
                      (los unicos que tienen dilema; el resto ya esta bien en tu carpeta anterior)
    --tambien DIR     otra carpeta de origen (se puede repetir)

Salida:
    SALIDA/BIRADS_x/<codigo>_<FILAS>x<COLUMNAS>/...
    SALIDA/resumen_por_resolucion.csv   una fila por (estudio, resolucion) y su motivo
    SALIDA/indice_por_resolucion.csv    una fila por imagen copiada
"""
import argparse
import csv
import shutil
from collections import Counter, defaultdict
from pathlib import Path

from mamo_comun import (CLASE_ALTA, CLASE_BENIGNA, clasificar_birads,
                        codigo_paciente, encontrar_estudios)
from mamo_resolucion import (agrupar_por_resolucion, conjuntos_completos,
                             faltan_vistas, indice_dcm, resolucion_dominante)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("entrada")
    ap.add_argument("salida")
    ap.add_argument("--tambien", action="append", default=[])
    ap.add_argument("--solo-indice", action="store_true")
    ap.add_argument("--solo-multiples", action="store_true")
    args = ap.parse_args()

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    estudios, ilegibles = encontrar_estudios([Path(args.entrada)] + [Path(p) for p in args.tambien])
    if not estudios:
        print("No se encontro ningun estudio.")
        return

    regs = []
    for carpeta, uid, inst in estudios:
        cod = codigo_paciente(inst)
        birads, clase, carpeta_birads = clasificar_birads(cod)
        if clase not in (CLASE_BENIGNA, CLASE_ALTA):
            continue
        g = agrupar_por_resolucion(inst)
        regs.append({"cod": cod, "birads": birads, "carpeta_birads": carpeta_birads,
                     "uid": uid, "carpeta": carpeta, "g": g, "comp": conjuntos_completos(g)})

    dominante, cuenta_res = resolucion_dominante([r["comp"] for r in regs])
    print(f"Estudios BI-RADS 2/4/5: {len(regs)} | resolucion dominante: {dominante or '(ninguna)'}")

    # codigos repetidos en varios estudios -> sufijo _dupN (orden estable por UID)
    por_cod = defaultdict(list)
    for r in regs:
        por_cod[r["cod"]].append(r)
    for cod, lista in por_cod.items():
        lista.sort(key=lambda r: r["uid"])
        for i, r in enumerate(lista):
            r["sufijo"] = "" if i == 0 else f"_dup{i + 1}"
        if len(lista) > 1:
            print(f"AVISO: {cod} esta en {len(lista)} estudios; carpetas con sufijo _dupN.")

    resumen, indice = [], []
    copiadas = Counter()   # (carpeta_birads, resolucion) -> carpetas
    for r in regs:
        if args.solo_multiples and len(r["comp"]) < 2:
            continue
        idx = indice_dcm(str(r["carpeta"]))
        for res in sorted(r["g"]):
            vistas = r["g"][res]
            nombre_carpeta = f"{r['cod']}_{res}{r['sufijo']}"
            fila = {"paciente": r["cod"], "birads": r["birads"], "resolucion": res,
                    "es_dominante": int(res == dominante), "carpeta_destino": nombre_carpeta,
                    "copiado": 0, "motivo": "", "repeticiones_descartadas": 0,
                    "uid_estudio": r["uid"]}
            falt = faltan_vistas(vistas)
            if falt:
                fila["motivo"] = "vistas_incompletas (faltan " + ",".join(falt) + ")"
                resumen.append(fila)
                continue
            elegidas = {lv: grupo[-1] for lv, grupo in vistas.items()}
            fila["repeticiones_descartadas"] = sum(len(gr) - 1 for gr in vistas.values())
            origenes = {lv: idx.get(d["_uid"]) for lv, d in elegidas.items()}
            if any(o is None for o in origenes.values()):
                fila["motivo"] = "archivo_no_encontrado (se esperan <SOPInstanceUID>.dcm)"
                resumen.append(fila)
                continue
            destino = salida / r["carpeta_birads"] / nombre_carpeta
            if not args.solo_indice:
                destino.mkdir(parents=True, exist_ok=True)
            for (lado, vista), d in sorted(elegidas.items()):
                nombre = f"{r['cod']}_{lado}_{vista}.dcm"
                if not args.solo_indice:
                    shutil.copy2(origenes[(lado, vista)], destino / nombre)
                indice.append({
                    "paciente": r["cod"], "birads": r["birads"], "resolucion": res,
                    "es_dominante": int(res == dominante), "lado": lado, "vista": vista,
                    "ruta": f"{r['carpeta_birads']}/{nombre_carpeta}/{nombre}",
                    "series_number": d.get("00200011", ""), "instance_number": d.get("00200013", ""),
                    "window_center": d.get("00281050", ""), "window_width": d.get("00281051", ""),
                    "archivo_origen": d["_uid"] + ".dcm"})
            fila["copiado"] = 1
            resumen.append(fila)
            copiadas[(r["carpeta_birads"], res)] += 1

    for nombre, datos in (("resumen_por_resolucion.csv", resumen), ("indice_por_resolucion.csv", indice)):
        if datos:
            with open(salida / nombre, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(datos[0].keys()))
                w.writeheader()
                w.writerows(datos)

    # ---------------- tablas
    print("\nTABLA 1. Carpetas (estudio x resolucion) creadas por BI-RADS y resolucion")
    resoluciones = sorted({res for (_, res) in copiadas})
    carpetas = sorted({c for (c, _) in copiadas})
    print(f"{'Carpeta':<12}" + "".join(f"{res:>13}" for res in resoluciones) + f"{'TOTAL':>9}")
    for c in carpetas:
        fila = [copiadas[(c, res)] for res in resoluciones]
        print(f"{c:<12}" + "".join(f"{n:>13}" for n in fila) + f"{sum(fila):>9}")
    total = sum(copiadas.values())
    print(f"{'TOTAL':<12}" + "".join(
        f"{sum(copiadas[(c, res)] for c in carpetas):>13}" for res in resoluciones) + f"{total:>9}")
    print(f"Imagenes {'que se copiarian' if args.solo_indice else 'copiadas'}: {total * 4}")

    print("\nTABLA 2. Resoluciones NO copiadas y por que")
    motivos = Counter(x["motivo"].split(" (")[0] for x in resumen if not x["copiado"])
    for m, n in motivos.most_common():
        print(f"  {m:<32}{n:>8}")
    if not motivos:
        print("  (ninguna)")

    multi = sum(1 for r in regs if len(r["comp"]) > 1)
    print(f"\nEstudios con MAS DE UNA resolucion completa: {multi}  (aqui hay que elegir cual usar)")

    if not args.solo_indice:
        malas = [p for p in salida.glob("BIRADS_*/*") if p.is_dir() and len(list(p.glob("*.dcm"))) != 4]
        print(f"Carpetas que NO tienen exactamente 4 .dcm: {len(malas)}"
              + (f" (ej. {malas[0]})" if malas else ""))
    else:
        print("(modo --solo-indice: no se copio ningun archivo)")
    if ilegibles:
        print(f"AVISO: {len(ilegibles)} XML ilegibles (ej. {ilegibles[0]})")


if __name__ == "__main__":
    main()
