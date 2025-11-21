import pandas as pd

df = pd.read_excel("68HC11_SET_INSTRUCCIONES.xlsx", header=None)

for i in range(5):
    print(f"\nFILA {i}:")
    print(list(df.iloc[i]))