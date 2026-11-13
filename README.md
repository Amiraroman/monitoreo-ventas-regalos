# Monitoreo de ventas de regalos con CI/CD

Valida lotes de ventas (Online Retail, UCI), compara `Quantity` y `UnitPrice` contra
septiembre con Evidently y publica el informe en GitHub Pages cuando todo es válido.

- Sitio: `https://github.com/Amiraroman/monitoreo-ventas-regalos`
- Autor: Amira Roman

## Estructura
```
datos/referencia.csv   septiembre 2011 (fijo)
datos/control.csv      octubre 2011 (lote control)
datos/nuevo.csv        noviembre 2011 (lote nuevo)
datos/actual.csv       copia de control.csv o de nuevo.csv (lo que se publica)
scripts/validar.py     validador de CSV
scripts/generar_sitio.py  informe Evidently + index.html
tests/                 pruebas con pytest
.github/workflows/ci-cd.yml
```

## Uso local
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest -v                        # pruebas
python scripts/validar.py        # valida referencia.csv y actual.csv
python scripts/generar_sitio.py  # genera la carpeta sitio/
```
Abre `sitio/index.html` en el navegador para ver el resultado.

## Flujo
Cada push a `main` ejecuta **CI** (instala, pruebas, valida, genera HTML, sube artefacto)
y, solo si CI pasa, **CD** despliega en GitHub Pages. Si la validación falla, CD se omite
y el sitio conserva el último commit publicado correctamente.

## Cambiar de lote
- Octubre: `actual.csv` = copia de `control.csv`.
- Noviembre: reemplazar todo el contenido de `actual.csv` por `nuevo.csv`.
