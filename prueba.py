import pandas as pd

def cargar_set_instrucciones(ruta_excel):

    # Leemos el Excel tomando la fila 0 como encabezado real
    df = pd.read_excel(ruta_excel, header=0)

    # Estandarizar encabezados
    df.columns = [c.strip().upper() for c in df.columns]

    col_mnem = "MNEMONICO"

    # Lista de columnas excepto el mnemónico
    columnas = list(df.columns)
    columnas.remove(col_mnem)

    # Detectar modos (cada 3 columnas es un modo)
    modos = {}
    i = 0
    while i < len(columnas):
        modo = columnas[i]                    # Ej: "IMM", "DIR", "IND,X"
        col_opcode = columnas[i]
        col_ciclo  = columnas[i + 1]
        col_byte   = columnas[i + 2]

        modos[modo] = (col_opcode, col_ciclo, col_byte)
        i += 3

    # Construir SET_INST
    SET_INST = {}

    for _, row in df.iterrows():

        mnem = str(row[col_mnem]).strip().upper()

        if not mnem or mnem == "NAN":
            continue

        SET_INST[mnem] = {}

        for modo, (col_op, col_ci, col_by) in modos.items():

            opcode = str(row[col_op]).strip()

            if opcode in ("--", "", "NAN", None):
                continue

            ciclo = row[col_ci]
            byte_ = row[col_by]

            try:
                ciclo = int(ciclo)
            except:
                ciclo = None

            try:
                byte_ = int(byte_)
            except:
                byte_ = None

            SET_INST[mnem][modo] = {
                "opcode": opcode,
                "ciclo": ciclo,
                "byte": byte_
            }

    return SET_INST



# --------------------------
# EJEMPLO DE USO
# --------------------------

SET_INST = cargar_set_instrucciones("68HC11_SET_INSTRUCCIONES.xlsx")

print(SET_INST["ADCA"]["IND,Y"]["byte"])



from dataclasses import dataclass
from typing import Optional, List

@dataclass
class ParsedLine:
    line_no: int              # número de línea en el archivo
    label: Optional[str]      # etiqueta, o None
    mnemonic: Optional[str]   # mnemónico, o None (línea vacía/comentario)
    operands: List[str]       # lista de operandos, ya separados por coma
    comment: str              # comentario sin el ';' o '*'
    raw: str                  # línea original


def tokenizar_linea(raw_line: str, line_no: int) -> ParsedLine:
    # Quitamos el salto de línea del final
    line = raw_line.rstrip('\n')

    # Separar comentario (asumimos ';' como comentario en línea)
    comment = ""
    if ';' in line:
        code_part, comment_part = line.split(';', 1)
        line = code_part
        comment = comment_part.strip()
    else:
        code_part = line

    # Si la línea está vacía o sólo tiene comentario → línea sin instrucción
    if code_part.strip() == "":
        return ParsedLine(
            line_no=line_no,
            label=None,
            mnemonic=None,
            operands=[],
            comment=comment,
            raw=raw_line
        )

    # Contar espacios iniciales
    indent = len(code_part) - len(code_part.lstrip(' '))
    rest = code_part.lstrip(' ')

    label = None
    mnemonic = None
    operands: list[str] = []

    # Regla que comentaste:
    #  - indent < 4  → hay etiqueta
    #  - indent >= 4 → no hay etiqueta, empieza mnemónico
    if indent < 4:
        # Tomamos primer token como etiqueta
        parts = rest.split(maxsplit=1)
        label = parts[0].rstrip(':').upper()   # por si algún día escribes "LOOP:"
        rest_after_label = parts[1] if len(parts) > 1 else ""
    else:
        rest_after_label = rest

    # Si después de la etiqueta (o indent) hay algo, esperamos mnemónico y operandos
    rest_after_label = rest_after_label.strip()
    if rest_after_label:
        parts = rest_after_label.split(maxsplit=1)
        mnemonic = parts[0].upper()
        operand_str = parts[1] if len(parts) > 1 else ""
        if operand_str:
            operands = [op.strip() for op in operand_str.split(',')]
        else:
            operands = []
    # Si no hay nada, es una línea solo con etiqueta

    return ParsedLine(
        line_no=line_no,
        label=label,
        mnemonic=mnemonic,
        operands=operands,
        comment=comment,
        raw=raw_line
    )


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
