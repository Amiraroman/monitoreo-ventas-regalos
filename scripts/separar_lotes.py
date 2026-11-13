import pandas as pd

df = pd.read_csv("ventas_regalos_2011.csv", dtype=str,
                 keep_default_na=False, encoding="utf-8-sig")
for lote in ["referencia", "control", "nuevo"]:
    sub = df[df["lote"] == lote]
    print(lote, len(sub))   # cada uno debe dar 12000
    sub.to_csv(f"datos/{lote}.csv", index=False)