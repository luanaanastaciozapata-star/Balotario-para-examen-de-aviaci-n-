import pandas as pd
df = pd.read_csv("preguntas.csv", dtype=str)
required = {"id","numero","tema","pregunta","A","B","C","respuesta"}
missing = required - set(df.columns)
assert not missing, f"Faltan columnas: {missing}"
assert len(df) == 538, f"Se esperaban 538 filas; hay {len(df)}"
assert df["id"].nunique() == 538, "Hay IDs duplicados"
assert set(df["respuesta"].dropna().unique()).issubset({"A","B","C"})
print("OK: 538 preguntas válidas.")
