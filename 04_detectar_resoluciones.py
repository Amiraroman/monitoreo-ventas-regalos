"""
04_detectar_resoluciones.py   (SECCION 1: DETECTAR, no copia nada)
Para cada estudio BI-RADS 2 / 4 / 5 dice:
  - que resoluciones tiene con las 4 vistas completas,
  - cual es la resolucion DOMINANTE de toda la muestra (ej. 3062x2394),
  - si el script 02 pudo haber elegido una resolucion NO dominante (afectado_por_02),
  - que estudios requieren revision manual.
Opcionalmente cruza tu lista de codigos fallidos (--fallidos) para ver si la causa
es la resolucion o es otra cosa.

Solo lee los XML (segundos). No abre ni copia DICOM.

Uso:
    python 04_detectar_resoluciones.py "E:\\DATOS DICOM"
    python 04_detectar_resoluciones.py "E:\\DATOS DICOM" --fallidos fallidos.txt
    python 04_detectar_resoluciones.py "C:\\MedSoft\\filestore" --tambien "E:\\OTRA"

Salida (carpeta resoluciones_detectadas/ por defecto):
    resumen_resoluciones.csv   una fila por estudio
    lista_afectados.txt        codigos afectados por el 02 (con alternativa dominante)
    lista_revision_manual.txt  codigos sin alternativa dominante o con formatos mezclados
"""
import argparse
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

from mamo_comun import (CLASE_ALTA, CLASE_BENIGNA, clasificar_birads,
                        codigo_paciente, encontrar_estudios)
from mamo_resolucion import (agrupar_por_resolucion, conjuntos_completos,
                             eleccion_del_02, faltan_vistas, resolucion_dominante)

CAT_OK = "OK_resolucion_unica"
CAT_MULTI = "MULTIPLE_con_dominante"
CAT_SIN_DOM = "REVISAR_sin_alternativa_dominante"
CAT_MEZCLA = "REVISAR_formatos_mezclados"
CAT_INCOMPLETO = "EXCLUIDO_vistas_incompletas"
CAT_SIN_2D = "EXCLUIDO_sin_2d"


def leer_fallidos(ruta):
    texto = Path(ruta).read_text(encoding="utf-8", errors="ignore")
    codigos = re.findall(r"B\d[a-cA-C]?-\d+", texto)
    vistos, unicos = set(), []
    for c in codigos:
        c = c.upper().replace("B4A", "B4a").replace("B4B", "B4b").replace("B4C", "B4c")
        if c not in vistos:
            vistos.add(c)
            unicos.append(c)
    return unicos


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("entrada")
    ap.add_argument("--tambien", action="append", default=[])
    ap.add_argument("--fallidos", help="txt con tus codigos que salieron mal (cualquier separador)")
    ap.add_argument("--salida", default="resoluciones_detectadas")
    args = ap.parse_args()

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    estudios, ilegibles = encontrar_estudios([Path(args.entrada)] + [Path(p) for p in args.tambien])
    if not estudios:
        print("No se encontro ningun estudio.")
        return

    regs, excluidos_birads = [], 0
    for carpeta, uid, inst in estudios:
        cod = codigo_paciente(inst)
        birads, clase, carpeta_birads = clasificar_birads(cod)
        if clase not in (CLASE_BENIGNA, CLASE_ALTA):
            excluidos_birads += 1
            continue
        g = agrupar_por_resolucion(inst)
        comp = conjuntos_completos(g)
        regs.append({"cod": cod, "birads": birads, "carpeta_birads": carpeta_birads,
                     "uid": uid, "carpeta": carpeta, "g": g, "comp": comp,
                     "ant": eleccion_del_02(inst)})

    dominante, cuenta_res = resolucion_dominante([r["comp"] for r in regs])
    print(f"\nEstudios leidos: {len(estudios)} | BI-RADS 2/4/5: {len(regs)} | "
          f"excluidos por BI-RADS (0,1,3,6): {excluidos_birads}")
    print(f"RESOLUCION DOMINANTE (conjuntos de 4 vistas completos): {dominante or '(ninguna)'}")
    print("  Conjuntos completos por resolucion (1 conjunto = 4 imagenes):")
    for res, n in cuenta_res.most_common():
        print(f"    {res:<12}{n:>6} conjuntos  ({n * 4} imagenes)")

    cod_repetidos = {c for c, n in Counter(r["cod"] for r in regs).items() if n > 1}

    for r in regs:
        g, comp = r["g"], r["comp"]
        if not g:
            cat = CAT_SIN_2D
        elif not comp:
            todas = set()
            for res in g:
                todas.update(g[res].keys())
            cat = CAT_MEZCLA if len(faltan_vistas(todas)) == 0 else CAT_INCOMPLETO
        elif dominante in comp:
            cat = CAT_MULTI if len(comp) > 1 else CAT_OK
        else:
            cat = CAT_SIN_DOM
        r["cat"] = cat
        elegidas = set(r["ant"].values())
        r["afectado"] = int(dominante in comp and any(x != dominante for x in elegidas))
        r["mezcla_02"] = int(len(elegidas) > 1)

    # ---------------- tablas
    cats = [CAT_OK, CAT_MULTI, CAT_SIN_DOM, CAT_MEZCLA, CAT_INCOMPLETO, CAT_SIN_2D]
    carpetas = sorted({r["carpeta_birads"] for r in regs})
    print("\nTABLA 1. Estudios por categoria y carpeta BI-RADS")
    print(f"{'Categoria':<38}" + "".join(f"{c:>11}" for c in carpetas) + f"{'TOTAL':>9}")
    for cat in cats:
        fila = [sum(1 for r in regs if r["cat"] == cat and r["carpeta_birads"] == c) for c in carpetas]
        print(f"{cat:<38}" + "".join(f"{n:>11}" for n in fila) + f"{sum(fila):>9}")

    print("\nTABLA 2. Estudios AFECTADOS por el 02 (eligio una resolucion no dominante "
          "habiendo alternativa dominante)")
    tot = 0
    for c in carpetas:
        n = sum(r["afectado"] for r in regs if r["carpeta_birads"] == c)
        tot += n
        print(f"  {c:<12}{n:>6}")
    print(f"  {'TOTAL':<12}{tot:>6}")
    print(f"  (de ellos, con vistas de resoluciones MEZCLADAS en la eleccion del 02: "
          f"{sum(r['afectado'] and r['mezcla_02'] for r in regs)})")

    revisar = [r for r in regs if r["cat"] in (CAT_SIN_DOM, CAT_MEZCLA)]
    print(f"\nRevision manual (sin alternativa dominante o formatos mezclados): {len(revisar)}")
    if cod_repetidos:
        print(f"AVISO: {len(cod_repetidos)} codigos aparecen en mas de un estudio "
              f"(ej. {sorted(cod_repetidos)[:5]}).")
    if ilegibles:
        print(f"AVISO: {len(ilegibles)} XML ilegibles (ej. {ilegibles[0]})")

    # ---------------- archivos
    campos = ["paciente", "birads", "categoria", "afectado_por_02", "resolucion_dominante",
              "resoluciones_completas", "resoluciones_parciales", "eleccion_02",
              "codigo_repetido", "uid_estudio", "carpeta_origen"]
    with open(salida / "resumen_resoluciones.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for r in sorted(regs, key=lambda x: x["cod"]):
            parciales = [res for res in r["g"] if res not in r["comp"]]
            w.writerow({
                "paciente": r["cod"], "birads": r["birads"], "categoria": r["cat"],
                "afectado_por_02": r["afectado"], "resolucion_dominante": dominante,
                "resoluciones_completas": ";".join(sorted(r["comp"])),
                "resoluciones_parciales": ";".join(sorted(parciales)),
                "eleccion_02": ";".join(f"{l}-{v}:{x}" for (l, v), x in sorted(r["ant"].items())),
                "codigo_repetido": int(r["cod"] in cod_repetidos),
                "uid_estudio": r["uid"], "carpeta_origen": r["carpeta"]})
    (salida / "lista_afectados.txt").write_text(
        "\n".join(sorted(r["cod"] for r in regs if r["afectado"])) + "\n", encoding="utf-8")
    (salida / "lista_revision_manual.txt").write_text(
        "\n".join(f"{r['cod']}\t{r['cat']}" for r in sorted(revisar, key=lambda x: x["cod"])) + "\n",
        encoding="utf-8")
    print(f"\nGuardado en {salida.resolve()}: resumen_resoluciones.csv, "
          f"lista_afectados.txt, lista_revision_manual.txt")

    # ---------------- cruce con tu lista de fallidos
    if args.fallidos:
        fallidos = leer_fallidos(args.fallidos)
        por_cod = defaultdict(list)
        for r in regs:
            por_cod[r["cod"]].append(r)
        no_enc = [c for c in fallidos if c not in por_cod]
        enc = [c for c in fallidos if c in por_cod]
        afect = [c for c in enc if any(r["afectado"] for r in por_cod[c])]
        multi = [c for c in enc if c not in afect and any(len(r["comp"]) > 1 for r in por_cod[c])]
        unica = [c for c in enc if c not in afect and c not in multi]
        rev = [c for c in enc if any(r["cat"] in (CAT_SIN_DOM, CAT_MEZCLA) for r in por_cod[c])]
        print(f"\nCRUCE CON TU LISTA DE FALLIDOS ({len(fallidos)} codigos distintos)")
        print(f"  Afectados por el 02 (la resolucion explica el fallo): {len(afect)}")
        print(f"  Con varias resoluciones pero el 02 ya eligio la dominante:   {len(multi)}")
        print(f"  Con UNA sola resolucion (la causa NO es la resolucion):     {len(unica)}")
        print(f"  En revision manual:                                      {len(rev)}")
        print(f"  No encontrados en los XML:                               {len(no_enc)} {no_enc[:10]}")
        if unica:
            print("  -> Estos NO se arreglan cambiando de resolucion; hay que mirar "
                  "ventana/VOI LUT u otra causa:")
            print("     " + ", ".join(unica))


if __name__ == "__main__":
    main()
