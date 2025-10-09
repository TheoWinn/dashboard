import pandas as pd

df = pd.read_csv("data/vorgang.csv", dtype=str)

print(df.info())
print(True in df.duplicated())
