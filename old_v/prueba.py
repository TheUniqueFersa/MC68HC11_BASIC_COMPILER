import os
import sys
import pandas as pd

def cargar_set_instrucciones(ruta_excel: str) -> dict:
    """
    Lee el Excel con el set de instrucciones del 68HC11 y construye:
        SET_INST[mnem][modo] = {"opcode": str, "ciclo": int, "byte": int}

    Maneja errores:
      - Archivo no encontrado
      - Problemas al leer el Excel (motor, formato, etc.)
    """

    if not os.path.exists(ruta_excel):
        print(f"[ERROR] No se encontró el archivo de set de instrucciones: '{ruta_excel}'")
        print("        Verifica la ruta o el nombre del archivo.")
        # Puedes elegir: salir del programa o lanzar excepción
        raise FileNotFoundError(ruta_excel)

    try:
        df = pd.read_excel(ruta_excel, header=0)
    except FileNotFoundError:
        # En teoría no llegas aquí porque ya validamos con os.path.exists,
        # pero lo dejamos por robustez.
        print(f"[ERROR] No se pudo abrir el archivo Excel: '{ruta_excel}'")
        raise
    except Exception as e:
        print(f"[ERROR] Fallo al leer el Excel '{ruta_excel}': {e}")
        # Aquí puedes decidir si abortas:
        raise

    # Estandarizar encabezados
    df.columns = [str(c).strip().upper() for c in df.columns]

    col_mnem = "MNEMONICO"
    if col_mnem not in df.columns:
        print("[ERROR] El Excel no contiene la columna 'MNEMONICO'.")
        raise ValueError("Formato de Excel inválido: falta columna MNEMONICO")

    # Lista de columnas excepto el mnemónico
    columnas = list(df.columns)
    columnas.remove(col_mnem)

    # Detectar modos (cada 3 columnas es un modo: OPCODE, CICLO, BYTE)
    modos: dict[str, tuple[str, str, str]] = {}
    i = 0
    while i + 2 < len(columnas):
        modo = columnas[i]          # Ej: "IMM", "DIR", "IND,X", ...
        col_opcode = columnas[i]
        col_ciclo  = columnas[i + 1]
        col_byte   = columnas[i + 2]
        modos[modo] = (col_opcode, col_ciclo, col_byte)
        i += 3

    SET_INST: dict[str, dict[str, dict[str, object]]] = {}

    for _, row in df.iterrows():
        mnem = str(row[col_mnem]).strip().upper()
        if not mnem or mnem == "NAN":
            continue

        SET_INST[mnem] = {}

        for modo, (col_op, col_ci, col_by) in modos.items():
            opcode = str(row[col_op]).strip()

            # Saltar modos no válidos en esta instrucción
            if opcode in ("--", "", "NAN", None):
                continue

            ciclo = row[col_ci]
            byte_ = row[col_by]

            try:
                ciclo = int(ciclo)
            except Exception:
                ciclo = None

            try:
                byte_ = int(byte_)
            except Exception:
                byte_ = None

            SET_INST[mnem][modo] = {
                "opcode": opcode,
                "ciclo": ciclo,
                "byte": byte_,
            }

    return SET_INST

"""
def tokenizar_archivo(ruta_fuente: str) -> list[ParsedLine]:
    lineas: list[ParsedLine] = []
    with open(ruta_fuente, 'r', encoding='utf-8') as f:
        for line_no, raw in enumerate(f, start=1):
            pl = tokenizar_linea(raw, line_no)
            lineas.append(pl)
    return lineas


parsed_lines = tokenizar_archivo("programa.asm")

for pl in parsed_lines:
    print(pl.line_no, pl.label, pl.mnemonic, pl.operands)
"""
SET_INST = cargar_set_instrucciones("68HC11_SET_INSTRUCCIONES.xlsx")

print(SET_INST["NOP"])
print(len((SET_INST["NOP"]["INH"]['opcode'])))
