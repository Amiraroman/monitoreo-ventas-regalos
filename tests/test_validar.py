import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from validar import validar_archivo  # noqa: E402

ENC = "InvoiceNo,StockCode,Description,InvoiceDate,Quantity,UnitPrice,lote\n"
FILA_OK = "536365,85123A,WHITE HANGING HEART,2011-10-03 08:26:00,6,2.55,control"


def escribir(tmp_path, filas, encabezado=ENC):
    ruta = tmp_path / "prueba.csv"
    ruta.write_text(encabezado + "".join(f + "\n" for f in filas), encoding="utf-8")
    return ruta


def test_archivo_valido(tmp_path):
    assert validar_archivo(escribir(tmp_path, [FILA_OK]), {"control"}) == []


def test_encabezado_faltante(tmp_path):
    enc = "InvoiceNo,StockCode,Description,InvoiceDate,Quantity,lote\n"
    errores = validar_archivo(escribir(tmp_path, [FILA_OK], enc), {"control"})
    assert errores and "UnitPrice" in errores[0]


def test_fecha_imposible(tmp_path):
    fila = FILA_OK.replace("2011-10-03 08:26:00", "2011-11-31 09:00:00")
    errores = validar_archivo(escribir(tmp_path, [fila]), {"control"})
    assert any("InvoiceDate" in e and "fila 2" in e for e in errores)


def test_cantidad_no_valida(tmp_path):
    errores = validar_archivo(escribir(tmp_path, [FILA_OK.replace(",6,", ",-3,")]), {"control"})
    assert any("Quantity" in e for e in errores)


def test_precio_negativo(tmp_path):
    errores = validar_archivo(escribir(tmp_path, [FILA_OK.replace(",2.55,", ",-2.55,")]), {"control"})
    assert any("UnitPrice" in e for e in errores)


def test_factura_repetida_se_acepta(tmp_path):
    otra = "536365,71053,METAL LANTERN,2011-10-03 08:26:00,3,3.39,control"
    assert validar_archivo(escribir(tmp_path, [FILA_OK, otra]), {"control"}) == []


def test_lote_mezclado(tmp_path):
    otra = "536370,71053,METAL LANTERN,2011-11-03 08:26:00,3,3.39,nuevo"
    errores = validar_archivo(escribir(tmp_path, [FILA_OK, otra]), {"control", "nuevo"}, un_solo_lote=True)
    assert any("más de un lote" in e for e in errores)
