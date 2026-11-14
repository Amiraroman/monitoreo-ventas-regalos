"""
mamo_resolucion.py
Funciones compartidas por 04_detectar_resoluciones.py y 05_extraer_por_resolucion.py.
Deja este archivo en la MISMA carpeta que mamo_comun.py.

Idea: dentro de un estudio puede haber varias adquisiciones completas (4 vistas)
con tamanos distintos (ej. 3062x2394 y 2294x1914). Aqui se agrupan las imagenes 2D
«For Presentation» por RESOLUCION (filas x columnas), no por «la mas reciente».
"""
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

from mamo_comun import (COMBINACIONES, a_entero, es_2d_presentacion,
                        lado_y_vista, orden_cronologico)


@lru_cache(maxsize=None)
def indice_dcm(carpeta):
    """{nombre_sin_extension: ruta} de todos los .dcm bajo la carpeta del estudio."""
    return {p.stem: p for p in Path(carpeta).rglob("*.dcm")}


def resolucion(d):
    """'FILASxCOLUMNAS' tal como lo muestra pydicom (Rows x Columns), ej. '3062x2394'."""
    return f"{a_entero(d.get('00280010'))}x{a_entero(d.get('00280011'))}"


def agrupar_por_resolucion(inst):
    """{resolucion: {(lado, vista): [instancias de la mas antigua a la mas reciente]}}"""
    g = defaultdict(lambda: defaultdict(list))
    for d in inst:
        if not es_2d_presentacion(d):
            continue
        lv = lado_y_vista(d)
        if lv:
            g[resolucion(d)][lv].append(d)
    for res in g:
        for lv in g[res]:
            g[res][lv].sort(key=orden_cronologico)
    return g


def conjuntos_completos(g):
    """Solo las resoluciones que tienen las 4 vistas (R-CC, L-CC, R-MLO, L-MLO)."""
    return {res: v for res, v in g.items() if all(c in v for c in COMBINACIONES)}


def faltan_vistas(vistas):
    return [f"{l}-{v}" for l, v in COMBINACIONES if (l, v) not in vistas]


def resolucion_dominante(lista_de_completos):
    """Resolucion mas frecuente entre todos los conjuntos completos (uno por estudio y resolucion)."""
    c = Counter()
    for comp in lista_de_completos:
        for res in comp:
            c[res] += 1
    return (c.most_common(1)[0][0] if c else ""), c


def eleccion_del_02(inst):
    """Replica lo que hacia el script 02: por cada vista, la toma de mayor SeriesNumber
    sin mirar la resolucion. Devuelve {(lado, vista): resolucion}."""
    por_vista = defaultdict(list)
    for d in inst:
        if es_2d_presentacion(d):
            lv = lado_y_vista(d)
            if lv:
                por_vista[lv].append(d)
    return {lv: resolucion(sorted(l, key=orden_cronologico)[-1]) for lv, l in por_vista.items()}
