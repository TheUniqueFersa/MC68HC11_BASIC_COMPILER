# mini_assembler.py
# Ensamblador básico MC68HC11 → código objeto en memoria
# Usa un diccionario SET_INST[mnem][modo] = {"opcode": str, "ciclo": int, "byte": int}

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import os
import sys
import html 
import pandas as pd


def validar_extension_source(source_path: str) -> bool:
    """
    Acepta únicamente archivos con extensión .asm o .asc.
    En caso contrario, muestra un mensaje y devuelve False.
    """
    _, ext = os.path.splitext(source_path)
    ext = ext.lower()

    if ext not in (".asm", ".asc"):
        print(f"[ERROR] Archivo fuente '{source_path}' con extensión no válida: '{ext}'")
        print("        Sólo se permiten archivos con extensión .asm o .asc.")
        return False

    return True


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

DEFAULT_EXCEL = os.path.join(
    os.path.dirname(__file__),
    "68HC11_SET_INSTRUCCIONES.xlsx"    # nombre de tu Excel
)
def resource_path(relative_path: str) -> str:
    """
    Devuelve la ruta absoluta a un recurso tanto en desarrollo
    como empaquetado con PyInstaller (onefile).
    """
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)

DEFAULT_EXCEL = resource_path("68HC11_SET_INSTRUCCIONES.xlsx")

from typing import Optional
# ------------------------------- ARCHIVOS

def _build_out_path(source_path: str, out_dir: Optional[str], ext: str) -> str:
    """
    Construye ruta de salida:
        out_dir / <nombre_sin_ext><ext>
    Si out_dir es None -> cwd (directorio desde donde se ejecuta compi).
    """
    if not out_dir:
        out_dir = os.getcwd()
    os.makedirs(out_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(source_path))[0]
    return os.path.join(out_dir, base_name + ext)

def parse_flag_string(flags: str):
    """
    Convierte la cadena de banderas (sin el '-') en seis booleanos:
        gen_lst, gen_ms19, gen_s19, gen_lst_html, gen_ms19_html, gen_s19_html
    """
    # DEFAULT: sin banderas → LST txt + S19 txt
    if not flags:
        return True, False, True, False, False, False

    flags = flags.strip()

    # -A → todo
    if "A" in flags:
        return True, True, True, True, True, True

    gen_lst = gen_ms19 = gen_s19 = False
    gen_lst_h = gen_ms19_h = gen_s19_h = False

    prev_c = False
    for ch in flags:
        if ch == "c":
            prev_c = True
            continue

        if ch in ("l", "s", "m"):
            if ch == "l":
                gen_lst = True
                if prev_c:
                    gen_lst_h = True
            elif ch == "s":
                gen_s19 = True
                if prev_c:
                    gen_s19_h = True
            elif ch == "m":
                gen_ms19 = True
                if prev_c:
                    gen_ms19_h = True
            prev_c = False
        else:
            print(f"[WARN] Bandera desconocida: '{ch}' (se ignora)")
            prev_c = False

    return gen_lst, gen_ms19, gen_s19, gen_lst_h, gen_ms19_h, gen_s19_h




# ----------------------------

# ---------------------------------------------------------------------
#  Estructuras de datos
# ---------------------------------------------------------------------

@dataclass
class AsmError:
    line_no: int
    code: int
    message: str

@dataclass
class ParsedLine:
    line_no: int
    label: Optional[str]
    mnemonic: Optional[str]    # puede ser directiva o instrucción
    operands: List[str]
    comment: str
    raw: str

@dataclass
class LineObject:
    parsed: ParsedLine
    address: Optional[int] = None          # dirección de la instrucción / dato
    size_bytes: int = 0                    # bytes totales que ocupa en memoria
    mode: Optional[str] = None             # modo de direccionamiento elegido
    object_bytes: List[int] = field(default_factory=list)  # bytes finales
    errors: List[AsmError] = field(default_factory=list)

# ---------------------------------------------------------------------
#  Errores del proyecto
# ---------------------------------------------------------------------

ERRORS = {
    1: "CONSTANTE INEXISTENTE",
    2: "VARIABLE INEXISTENTE",
    3: "ETIQUETA INEXISTENTE",
    4: "MNEMÓNICO INEXISTENTE",
    5: "INSTRUCCIÓN CARECE DE OPERANDO(S)",
    6: "INSTRUCCIÓN NO LLEVA OPERANDO(S)",
    7: "MAGNITUD DE OPERANDO ERRÓNEA",
    8: "SALTO RELATIVO MUY LEJANO",
    9: "INSTRUCCIÓN CARECE DE AL MENOS UN ESPACIO RELATIVO AL MARGEN",
    10: "NO SE ENCUENTRA END",
}

DIRECTIVES = {"ORG", "EQU", "FCB", "END"}

BRANCH_MNEMONICS = {
    "BRA", "BRN", "BHI", "BLS", "BCC", "BCS",
    "BNE", "BEQ", "BVC", "BVS", "BPL", "BMI",
    "BGE", "BLT", "BGT", "BLE", "BSR"
}

# ---------------------------------------------------------------------
#  Utilidades
# ---------------------------------------------------------------------

def classify_bytes(lo: LineObject, SET_INST: Dict) -> list[str]:
    """
    Clasifica cada byte de object_code de una línea como:
      - 'opcode'
      - 'op-imm', 'op-dir', 'op-ext', 'op-indx', 'op-indy', 'op-rel'
      - 'data' (para FCB u otros casos)
    """
    if not lo.object_bytes:
        return []

    pl = lo.parsed
    mnem = pl.mnemonic.upper() if pl.mnemonic else None

    # FCB: todos son datos
    if mnem == "FCB":
        return ["data"] * len(lo.object_bytes)

    if mnem not in SET_INST or lo.mode is None:
        return ["data"] * len(lo.object_bytes)

    info = SET_INST[mnem][lo.mode]
    opcode_len = len(str(info["opcode"]).split())

    tags: list[str] = []
    for i in range(len(lo.object_bytes)):
        if i < opcode_len:
            tags.append("opcode")
        else:
            mode = lo.mode
            if mode == "IMM":
                tags.append("op-imm")
            elif mode == "DIR":
                tags.append("op-dir")
            elif mode == "EXT":
                tags.append("op-ext")
            elif mode == "REL":
                tags.append("op-rel")
            elif mode == "IND,X":
                tags.append("op-indx")
            elif mode == "IND,Y":
                tags.append("op-indy")
            elif mode == "INH":
                tags.append("opcode")
            else:
                tags.append("data")
    return tags


def build_mem_info(result: CompileResult, SET_INST: Dict) -> tuple[dict[int, int], dict[int, str]]:
    """
    Construye:
      mem[addr]        = byte
      mem_tag[addr]    = 'opcode' | 'operand' | 'data'
    a partir de las líneas ya compiladas.
    """
    mem: dict[int, int] = {}
    mem_tag: dict[int, str] = {}

    for lo in result.lines:
        if lo.address is None or not lo.object_bytes:
            continue

        tags = classify_bytes(lo, SET_INST)
        for i, b in enumerate(lo.object_bytes):
            addr = (lo.address + i) & 0xFFFF
            tag = tags[i] if i < len(tags) else "data"

            # Simplificar etiquetas para formatos S19/MS19
            if tag == "opcode":
                simple = "opcode"
            elif tag.startswith("op-"):
                simple = "operand"
            else:
                simple = "data"

            mem[addr] = b & 0xFF
            mem_tag[addr] = simple

    return mem, mem_tag
# -----------------------------------------------------------------------------

CSS_COMMON = """
<style>
body  { font-family: monospace; background:#ffffff; color:#000000; }
pre   { font-family: monospace; }
.line { white-space: pre; }

.addr      { color:#0066cc; }
.bytes     { }
.byte      { }
.byte.opcode  { color:#d00000; font-weight:bold; }
.byte.operand { color:#007000; }
.byte.data    { color:#555555; }

.label    { color:#b35900; font-weight:bold; }
.mnemonic { color:#0000aa; font-weight:bold; }
.comment  { color:#888888; }

.op-imm  { color:#ff7f00; }
.op-dir  { color:#008b8b; }
.op-ext  { color:#800080; }
.op-indx { color:#2f4f4f; }
.op-indy { color:#2f4f4f; font-style:italic; }
.op-rel  { color:#b22222; }

</style>
"""


def hex_to_int(token: str) -> Optional[int]:
    """Convierte '$12', '0x12', '12' a entero. None si no es numérico."""
    t = token.strip().upper()
    try:
        if t.startswith("$"):
            return int(t[1:], 16)
        if t.startswith("0X"):
            return int(t[2:], 16)
        return int(t, 10)
    except ValueError:
        return None

def parse_immediate(token: str) -> Tuple[Optional[str], Optional[int]]:
    """
    Convierte un inmediato a:
      - ('NOMBRE', None) si es símbolo (#CONST)
      - (None, valor)    si es numérico (#$12, #10, #0x10, #'A)
    """
    t = token.strip()
    if not t.startswith("#"):
        return None, None

    inner = t[1:].strip()   # lo que está después de '#'

    # Caso 1: literal de carácter, estilo #'A
    if inner.startswith("'") and len(inner) >= 2:
        # Tomamos el primer carácter después de la comilla
        ch = inner[1]
        return None, ord(ch)

    # Caso 2: valor numérico
    val = hex_to_int(inner)
    if val is not None:
        return None, val

    # Caso 3: símbolo (CONST definida con EQU)
    return inner.upper(), None


# ---------------------------------------------------------------------
#  Tokenización de una línea
# ---------------------------------------------------------------------

def tokenizar_linea(raw_line: str, line_no: int, mnemonics: set[str]) -> ParsedLine:
    """
    Regla de margen:
    - Si la línea comienza en columna 0 y el primer token es un mnemónico/directiva,
      es error de margen (se marcará después) pero se trata como instrucción sin etiqueta.
    - Si la línea comienza en columna 0 y el primer token NO es mnemónico/directiva,
      se considera etiqueta.
    - Si la línea comienza con uno o más espacios: no hay etiqueta.
    """

    line = raw_line.rstrip("\n")

    # Separar comentario (; o *)
    comment = ""
    code_part = line
    for sep in (";", "*"):
        idx = code_part.find(sep)
        if idx != -1:
            comment = code_part[idx+1:].strip()
            code_part = code_part[:idx]
            break

    if code_part.strip() == "":
        return ParsedLine(line_no, None, None, [], comment, raw_line)

    # Indentación
    indent = len(code_part) - len(code_part.lstrip(" "))
    rest = code_part.lstrip(" ")
    label = None
    mnemonic = None
    operands: List[str] = []

    # Separar primer token
    parts = rest.split(maxsplit=1)
    first = parts[0].upper()
    tail = parts[1] if len(parts) > 1 else ""

    if indent == 0:
        # Sin espacios al margen: o es etiqueta o es instrucción mal indentada
        if first in mnemonics or first in DIRECTIVES:
            # Instrucción/directiva pegada al margen → se marca error 9 después
            mnemonic = first
            operand_str = tail.strip()
        else:
            # Es etiqueta
            label = first
            tail = tail.strip()
            if tail:
                parts2 = tail.split(maxsplit=1)
                mnemonic = parts2[0].upper()
                operand_str = parts2[1] if len(parts2) > 1 else ""
            else:
                operand_str = ""
    else:
        # Hay indentación → no hay etiqueta
        mnemonic = first
        operand_str = tail.strip()

    if operand_str:
        operands = [op.strip() for op in operand_str.split(",") if op.strip()]

    return ParsedLine(line_no, label, mnemonic, operands, comment, raw_line)

# ---------------------------------------------------------------------
#  Detección de modo de direccionamiento
# ---------------------------------------------------------------------

def detectar_modo(mnem: str, operands: List[str], SET_INST: Dict) -> Optional[str]:
    """Determina el modo según los operandos y lo que soporta el mnemónico."""
    if mnem not in SET_INST:
        return None

    modos_disponibles = set(SET_INST[mnem].keys())

    # Sin operandos
    if not operands:
        if "INH" in modos_disponibles:
            return "INH"
        return None

    op = operands[0].upper()

    # Inmediato
    if op.startswith("#"):
        return "IMM" if "IMM" in modos_disponibles else None

    # Indexado
    if op.endswith(",X"):
        return "IND,X" if "IND,X" in modos_disponibles else None
    if op.endswith(",Y"):
        return "IND,Y" if "IND,Y" in modos_disponibles else None

    # Relativo
    if mnem in BRANCH_MNEMONICS and "REL" in modos_disponibles:
        return "REL"

    # Dir/Ext: si es valor numérico podemos decidir por rango
    base = op.split(",", 1)[0]  # por si algo raro
    val = hex_to_int(base)
    if val is not None:
        if val <= 0xFF and "DIR" in modos_disponibles:
            return "DIR"
        if "EXT" in modos_disponibles:
            return "EXT"

    # Simbólico: si solo hay EXT → EXT, si solo DIR → DIR
    if "DIR" in modos_disponibles and "EXT" not in modos_disponibles:
        return "DIR"
    if "EXT" in modos_disponibles and "DIR" not in modos_disponibles:
        return "EXT"

    # Ambiguo → por simplicidad elegimos EXT (más grande)
    if "EXT" in modos_disponibles:
        return "EXT"

    return None

# ---------------------------------------------------------------------
#  Primera pasada: tokenización + etiquetas + constantes + variables
# ---------------------------------------------------------------------

@dataclass
class SymbolTables:
    labels: Dict[str, int]          # etiquetas con dirección
    constants: Dict[str, int]       # nombre EQU valor
    variables: Dict[str, int]       # etiquetas de FCB (dirección de variable)

def primera_pasada(path: str, SET_INST: Dict) -> Tuple[List[LineObject], SymbolTables, List[AsmError]]:
    """
    - Lee el archivo.
    - Tokeniza.
    - Resuelve ORG, EQU, FCB, etiquetas.
    - Calcula dirección y tamaño aproximado de cada línea.
    - Cada ORG que aparezca mueve el contador de dirección (location counter).
    - Las constantes EQU no ocupan memoria y pueden ir en cualquier parte.
    - current_addr siempre se mantiene en 16 bits (0x0000–0xFFFF) con envolvimiento.
    """
    line_objs: List[LineObject] = []
    errors: List[AsmError] = []
    labels: Dict[str, int] = {}
    constants: Dict[str, int] = {}
    variables: Dict[str, int] = {}

    mnemonics = set(SET_INST.keys()) | DIRECTIVES

    with open(path, "r", encoding="ansi", errors="ignore") as f:
        lines = f.readlines()

    current_addr: Optional[int] = None
    found_end = False

    # 1) Tokenización
    for i, raw in enumerate(lines, start=1):
        pl = tokenizar_linea(raw, i, mnemonics)
        lo = LineObject(parsed=pl)
        line_objs.append(lo)

    # 2) Recorrido
    for lo in line_objs:
        pl = lo.parsed
        mnem = pl.mnemonic.upper() if pl.mnemonic else None

        # Error 9: instrucción pegada al margen sin etiqueta
        if pl.mnemonic and pl.label is None:
            if pl.raw and not pl.raw.startswith((" ", "\t")):
                if mnem in SET_INST:   # solo para instrucciones reales
                    lo.errors.append(AsmError(pl.line_no, 9, ERRORS[9]))

        # ORG
        if mnem == "ORG":
            if not pl.operands:
                lo.errors.append(AsmError(pl.line_no, 5, ERRORS[5]))
                continue
            val = hex_to_int(pl.operands[0])
            if val is None:
                lo.errors.append(AsmError(pl.line_no, 7, ERRORS[7]))
                continue
            current_addr = val & 0xFFFF  # limitar a 16 bits
            lo.address = current_addr
            lo.size_bytes = 0
            continue

        # END
        if mnem == "END":
            found_end = True
            lo.address = current_addr
            lo.size_bytes = 0
            break

        # EQU (constante, no ocupa memoria)
        if mnem == "EQU" and pl.label:
            if not pl.operands:
                lo.errors.append(AsmError(pl.line_no, 5, ERRORS[5]))
            else:
                val = hex_to_int(pl.operands[0])
                if val is None:
                    lo.errors.append(AsmError(pl.line_no, 7, ERRORS[7]))
                else:
                    constants[pl.label] = val & 0xFFFF
            lo.address = None
            lo.size_bytes = 0
            continue

        # Línea sin mnemónico (etiqueta sola / comentario)
        if mnem is None:
            if pl.label:
                if current_addr is None:
                    current_addr = 0
                if pl.label in labels:
                    errors.append(AsmError(pl.line_no, 0, f"Etiqueta redefinida: {pl.label}"))
                labels[pl.label] = current_addr
            lo.address = current_addr
            lo.size_bytes = 0
            continue

        # FCB: reserva memoria de datos
        if mnem == "FCB":
            if current_addr is None:
                current_addr = 0
            lo.address = current_addr
            n_bytes = len(pl.operands) if pl.operands else 1
            lo.size_bytes = n_bytes
            if pl.label:
                variables[pl.label] = current_addr
            current_addr = (current_addr + n_bytes) & 0xFFFF  # envolvimiento
            continue

        # MNEMÓNICO INEXISTENTE
        if mnem not in SET_INST:
            lo.errors.append(AsmError(pl.line_no, 4, ERRORS[4]))
            lo.address = current_addr
            lo.size_bytes = 0
            continue

        # Instrucción normal
        if current_addr is None:
            current_addr = 0

        if pl.label:
            if pl.label in labels:
                errors.append(AsmError(pl.line_no, 0, f"Etiqueta redefinida: {pl.label}"))
            labels[pl.label] = current_addr

        mode = detectar_modo(mnem, pl.operands, SET_INST)
        lo.mode = mode

        if mode is None:
            if not pl.operands:
                lo.errors.append(AsmError(pl.line_no, 5, ERRORS[5]))
            else:
                lo.errors.append(AsmError(pl.line_no, 7, "Modo de direccionamiento no válido"))
            size = 0
        else:
            size = SET_INST[mnem][mode]["byte"] or 0

        lo.address = current_addr
        lo.size_bytes = size
        current_addr = (current_addr + size) & 0xFFFF  # envolvimiento

    if not found_end:
        errors.append(AsmError(0, 10, ERRORS[10]))

    symtabs = SymbolTables(labels=labels, constants=constants, variables=variables)
    return line_objs, symtabs, errors

# ---------------------------------------------------------------------
#  Segunda pasada: generar código objeto y revisar errores semánticos
# ---------------------------------------------------------------------

def segunda_pasada(
    line_objs: List[LineObject],
    sym: SymbolTables,
    SET_INST: Dict
) -> List[AsmError]:

    errors: List[AsmError] = []

    for lo in line_objs:
        pl = lo.parsed
        mnem = pl.mnemonic.upper() if pl.mnemonic else None

        # acumular errores de la primera pasada
        errors.extend(lo.errors)

        if not mnem:
            continue

        # --------------------------------------------------------
        # FCB: genera bytes de datos
        # --------------------------------------------------------
        if mnem == "FCB":
            data_bytes: List[int] = []

            for op_token in pl.operands:
                t = op_token.strip()

                # literal de carácter: 'A
                if t.startswith("'") and len(t) >= 2:
                    val = ord(t[1])
                else:
                    val = hex_to_int(t)
                    if val is None:
                        name = t.upper()
                        # permitir usar constantes EQU en FCB
                        if name in sym.constants:
                            val = sym.constants[name]
                        else:
                            errors.append(AsmError(pl.line_no, 2, ERRORS[2]))
                            continue

                if not (0 <= val <= 0xFF):
                    errors.append(AsmError(pl.line_no, 7, ERRORS[7]))
                    continue

                data_bytes.append(val & 0xFF)

            lo.object_bytes = data_bytes
            continue

        # --------------------------------------------------------
        # Directivas sin código objeto: ORG, EQU, END
        # --------------------------------------------------------
        if mnem in {"ORG", "EQU", "END"}:
            continue

        # --------------------------------------------------------
        # Instrucciones normales
        # --------------------------------------------------------
        if mnem not in SET_INST or lo.mode is None or lo.address is None:
            continue

        info_mode = SET_INST[mnem][lo.mode]
        opcode_str = info_mode["opcode"]
        total_bytes = info_mode["byte"] or 0
        opcode_bytes = [int(b, 16) for b in opcode_str.split()]

        # INH
        if lo.mode == "INH":
            lo.object_bytes = opcode_bytes
            if pl.operands:
                errors.append(AsmError(pl.line_no, 6, ERRORS[6]))
            continue

        # Falta operando
        if not pl.operands:
            errors.append(AsmError(pl.line_no, 5, ERRORS[5]))
            continue

        op_token = pl.operands[0].strip()
        obj: List[int] = list(opcode_bytes)

        # IMM
        if lo.mode == "IMM":
            sym_name, imm_val = parse_immediate(op_token)

            if sym_name is not None:
                if sym_name not in sym.constants:
                    errors.append(AsmError(pl.line_no, 1, ERRORS[1]))
                    continue
                imm_val = sym.constants[sym_name]

            if imm_val is None:
                errors.append(AsmError(pl.line_no, 7, ERRORS[7]))
                continue

            op_bytes = total_bytes - len(opcode_bytes)
            max_val = (1 << (8 * op_bytes)) - 1
            if not (0 <= imm_val <= max_val):
                errors.append(AsmError(pl.line_no, 7, ERRORS[7]))
                continue

            for shift in reversed(range(op_bytes)):
                obj.append((imm_val >> (8 * shift)) & 0xFF)

        # REL
        elif lo.mode == "REL":
            name = op_token.upper()

            if name in sym.labels:
                target = sym.labels[name]
            elif name in sym.constants:
                target = sym.constants[name]
            else:
                errors.append(AsmError(pl.line_no, 3, ERRORS[3]))
                continue

            next_addr = (lo.address + total_bytes) & 0xFFFF
            offset = target - next_addr
            if not (-128 <= offset <= 127):
                errors.append(AsmError(pl.line_no, 8, ERRORS[8]))
                continue
            obj.append(offset & 0xFF)

        # IND,X / IND,Y  (offset de 8 bits)
        elif lo.mode in ("IND,X", "IND,Y"):
            off_str, _reg = op_token.split(",", 1)
            off_str = off_str.strip()
            val = hex_to_int(off_str)
            if val is None:
                name = off_str.upper()
                if name in sym.constants:
                    val = sym.constants[name]
                else:
                    errors.append(AsmError(pl.line_no, 2, ERRORS[2]))
                    continue
            if not (0 <= val <= 0xFF):
                errors.append(AsmError(pl.line_no, 7, ERRORS[7]))
                continue
            obj.append(val & 0xFF)

        # DIR / EXT
        elif lo.mode in ("DIR", "EXT"):
            op_up = op_token.upper()
            addr_val = hex_to_int(op_up)
            name = None

            if addr_val is None:
                name = op_up

                if mnem in {"JMP", "JSR"}:
                    if name in sym.labels:
                        addr_val = sym.labels[name]
                    elif name in sym.constants:
                        addr_val = sym.constants[name]
                    else:
                        errors.append(AsmError(pl.line_no, 3, ERRORS[3]))
                        continue
                else:
                    if name in sym.variables:
                        addr_val = sym.variables[name]
                    elif name in sym.labels:
                        addr_val = sym.labels[name]
                    elif name in sym.constants:
                        addr_val = sym.constants[name]
                    else:
                        errors.append(AsmError(pl.line_no, 2, ERRORS[2]))
                        continue

            if addr_val is None:
                errors.append(AsmError(pl.line_no, 7, ERRORS[7]))
                continue

            addr_val &= 0xFFFF

            if lo.mode == "DIR":
                if not (0 <= addr_val <= 0xFF):
                    errors.append(AsmError(pl.line_no, 7, ERRORS[7]))
                    continue
                obj.append(addr_val & 0xFF)
            else:  # EXT
                obj.append((addr_val >> 8) & 0xFF)
                obj.append(addr_val & 0xFF)

        lo.object_bytes = obj

    return errors

# ---------------------------------------------------------------------
#  Función principal de compilación (sin generación de archivos aún)
# ---------------------------------------------------------------------

@dataclass
class CompileResult:
    lines: List[LineObject]
    symbols: SymbolTables
    errors: List[AsmError]

@dataclass
class CompileResult:
    lines: List[LineObject]
    symbols: SymbolTables
    errors: List[AsmError]

def compilar_archivo(path: str, SET_INST: Dict) -> CompileResult:
    """
    Compila un archivo fuente .asm/.asc:
      - Primera pasada: etiquetas, EQU, FCB, ORG, tamaños
      - Segunda pasada: bytes objeto, validación de errores
    Maneja FileNotFoundError del archivo fuente.
    """
    try:
        line_objs, sym, errors1 = primera_pasada(path, SET_INST)
    except FileNotFoundError:
        print(f"[ERROR] No se pudo abrir el archivo fuente: '{path}'")
        print("        Verifica que la ruta y el nombre sean correctos.")
        # Propagamos la excepción para que el caller decida qué hacer
        raise

    errors2 = segunda_pasada(line_objs, sym, SET_INST)
    all_errors = errors1 + errors2
    return CompileResult(lines=line_objs, symbols=sym, errors=all_errors)


def generar_lst(source_path: str, result: CompileResult, out_dir: Optional[str] = None) -> str:
    lst_path = _build_out_path(source_path, out_dir, ".lst")

    with open(lst_path, "w", encoding="ansi", errors="ignore") as f:
        for lo in result.lines:
            pl = lo.parsed
            addr_str = "    "
            if lo.address is not None:
                addr_str = f"{lo.address & 0xFFFF:04X}"

            obj_hex = ""
            if lo.object_bytes:
                obj_hex = " ".join(f"{b:02X}" for b in lo.object_bytes)

            src = pl.raw.rstrip("\n")
            f.write(f"{pl.line_no:4d}: {addr_str} ({obj_hex}) : {src}\n")

    return lst_path


def generar_lst_html(source_path: str,
                     result: CompileResult,
                     SET_INST: Dict,
                     out_dir: Optional[str] = None) -> str:

    html_path = _build_out_path(source_path, out_dir, ".lst.html")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write("<html><head><meta charset='utf-8'>\n")
        f.write(CSS_COMMON)
        f.write("</head><body><pre>\n")

        for lo in result.lines:
            pl = lo.parsed
            addr_str = ""
            if lo.address is not None:
                addr_str = f"{lo.address & 0xFFFF:04X}"

            bytes_html = ""
            if lo.object_bytes:
                tags = classify_bytes(lo, SET_INST)
                parts = []
                for b, t in zip(lo.object_bytes, tags):
                    cls = "byte "
                    if t == "opcode":
                        cls += "opcode"
                    elif t.startswith("op-"):
                        cls += "operand"
                    else:
                        cls += "data"
                    parts.append(f"<span class='{cls}'>{b:02X}</span>")
                bytes_html = " ".join(parts)

            code_parts = []
            if pl.label:
                code_parts.append(f"<span class='label'>{html.escape(pl.label)}</span>")
            if pl.mnemonic:
                code_parts.append(f"<span class='mnemonic'>{html.escape(pl.mnemonic)}</span>")

            if pl.operands:
                mode = lo.mode or ""
                op_cls = "op-imm"
                if mode == "DIR":
                    op_cls = "op-dir"
                elif mode == "EXT":
                    op_cls = "op-ext"
                elif mode == "IND,X":
                    op_cls = "op-indx"
                elif mode == "IND,Y":
                    op_cls = "op-indy"
                elif mode == "REL":
                    op_cls = "op-rel"
                elif mode == "IMM":
                    op_cls = "op-imm"

                ops = [f"<span class='{op_cls}'>{html.escape(op)}</span>" for op in pl.operands]
                code_parts.append(", ".join(ops))

            if pl.comment:
                code_parts.append(f"<span class='comment'>; {html.escape(pl.comment)}</span>")

            code_html = " ".join(code_parts)

            f.write(
                f"<span class='line'>"
                f"{pl.line_no:4d}: "
                f"<span class='addr'>{addr_str:4s}</span> "
                f"({bytes_html}) : {code_html}"
                f"</span>\n"
            )

        f.write("</pre></body></html>\n")

    return html_path


def _make_s1_record(addr: int, data_bytes: list[int]) -> str:
    addr &= 0xFFFF
    count = len(data_bytes) + 3  # addr(2) + data + checksum
    ah = (addr >> 8) & 0xFF
    al = addr & 0xFF
    s = count + ah + al + sum(data_bytes)
    cks = (~s) & 0xFF
    return "S1" + f"{count:02X}{addr:04X}" + "".join(f"{b:02X}" for b in data_bytes) + f"{cks:02X}"


def _make_s9_record(entry_addr: int) -> str:
    entry_addr &= 0xFFFF
    count = 3
    ah = (entry_addr >> 8) & 0xFF
    al = entry_addr & 0xFF
    s = count + ah + al
    cks = (~s) & 0xFF
    return "S9" + f"{count:02X}{entry_addr:04X}{cks:02X}"

def generar_ms19(source_path: str,
                 result: CompileResult,
                 SET_INST: Dict,
                 out_dir: Optional[str] = None) -> str:

    ms19_path = _build_out_path(source_path, out_dir, ".ms19")

    mem, _ = build_mem_info(result, SET_INST)

    with open(ms19_path, "w", encoding="ascii", errors="ignore") as f:
        if mem:
            sorted_addrs = sorted(mem.keys())
            max_data = 16

            start = sorted_addrs[0]
            prev = start
            chunk = [mem[start]]

            for addr in sorted_addrs[1:]:
                if addr == prev + 1 and len(chunk) < max_data:
                    chunk.append(mem[addr])
                    prev = addr
                else:
                    f.write(_make_s1_record(start, chunk) + "\n")
                    start = addr
                    prev = addr
                    chunk = [mem[addr]]

            if chunk:
                f.write(_make_s1_record(start, chunk) + "\n")

        entry = None
        for lo in result.lines:
            pl = lo.parsed
            mnem = pl.mnemonic.upper() if pl.mnemonic else None
            if mnem == "END" and pl.operands:
                op = pl.operands[0].strip()
                v = hex_to_int(op)
                if v is not None:
                    entry = v & 0xFFFF
                else:
                    name = op.upper()
                    if name in result.symbols.labels:
                        entry = result.symbols.labels[name]
                    elif name in result.symbols.constants:
                        entry = result.symbols.constants[name]

        if entry is None:
            if mem:
                entry = min(mem.keys())
            else:
                entry = 0

        f.write(_make_s9_record(entry) + "\n")

    return ms19_path

def generar_ms19_html(source_path: str,
                      result: CompileResult,
                      SET_INST: Dict,
                      out_dir: Optional[str] = None) -> str:

    html_path = _build_out_path(source_path, out_dir, ".ms19.html")

    mem, mem_tag = build_mem_info(result, SET_INST)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write("<html><head><meta charset='utf-8'>\n")
        f.write(CSS_COMMON)
        f.write("</head><body><pre>\n")

        if mem:
            sorted_addrs = sorted(mem.keys())
            max_data = 16

            start = sorted_addrs[0]
            prev = start
            chunk_addrs = [start]

            for addr in sorted_addrs[1:]:
                if addr == prev + 1 and len(chunk_addrs) < max_data:
                    chunk_addrs.append(addr)
                    prev = addr
                else:
                    data_bytes = [mem[a] for a in chunk_addrs]
                    f.write(_make_s1_record_html(start, data_bytes, mem_tag) + "\n")
                    start = addr
                    prev = addr
                    chunk_addrs = [addr]

            if chunk_addrs:
                data_bytes = [mem[a] for a in chunk_addrs]
                f.write(_make_s1_record_html(start, data_bytes, mem_tag) + "\n")

        entry = None
        for lo in result.lines:
            pl = lo.parsed
            mnem = pl.mnemonic.upper() if pl.mnemonic else None
            if mnem == "END" and pl.operands:
                op = pl.operands[0].strip()
                v = hex_to_int(op)
                if v is not None:
                    entry = v & 0xFFFF
                else:
                    name = op.upper()
                    if name in result.symbols.labels:
                        entry = result.symbols.labels[name]
                    elif name in result.symbols.constants:
                        entry = result.symbols.constants[name]
        if entry is None:
            if mem:
                entry = min(mem.keys())
            else:
                entry = 0

        f.write(_make_s9_record(entry) + "\n")

        f.write("</pre></body></html>\n")

    return html_path


def _make_s1_record_html(addr: int, data_bytes: list[int], mem_tag: dict[int, str]) -> str:
    """
    Versión HTML del registro S1, donde sólo los bytes de datos
    se colorean según mem_tag[addr].
    """
    addr &= 0xFFFF
    count = len(data_bytes) + 3
    ah = (addr >> 8) & 0xFF
    al = addr & 0xFF
    s = count + ah + al + sum(data_bytes)
    cks = (~s) & 0xFF

    header = "S1" + f"{count:02X}{addr:04X}"
    parts = [header]

    for i, b in enumerate(data_bytes):
        a = (addr + i) & 0xFFFF
        tag = mem_tag.get(a, "data")
        cls = "byte "
        if tag == "opcode":
            cls += "opcode"
        elif tag == "operand":
            cls += "operand"
        else:
            cls += "data"
        parts.append(f"<span class='{cls}'>{b:02X}</span>")

    parts.append(f"{cks:02X}")
    return "".join(parts)

def generar_s19(source_path: str,
                result: CompileResult,
                SET_INST: Dict,
                out_dir: Optional[str] = None) -> str:

    s19_path = _build_out_path(source_path, out_dir, ".s19")

    mem, _ = build_mem_info(result, SET_INST)

    with open(s19_path, "w", encoding="ascii", errors="ignore") as f:
        if mem:
            sorted_addrs = sorted(mem.keys())
            start = sorted_addrs[0]
            prev = start
            chunk = [mem[start]]

            for addr in sorted_addrs[1:]:
                if addr == prev + 1 and len(chunk) < 16:
                    chunk.append(mem[addr])
                    prev = addr
                else:
                    f.write(_line_s19_simple(start, chunk) + "\n")
                    start = addr
                    prev = addr
                    chunk = [mem[addr]]

            if chunk:
                f.write(_line_s19_simple(start, chunk) + "\n")

    return s19_path



def _line_s19_simple(start_addr: int, data_bytes: list[int]) -> str:
    return "<" + f"{start_addr & 0xFFFF:04X}" + "> " + " ".join(f"{b:02X}" for b in data_bytes)


def generar_s19_html(source_path: str,
                     result: CompileResult,
                     SET_INST: Dict,
                     out_dir: Optional[str] = None) -> str:

    html_path = _build_out_path(source_path, out_dir, ".s19.html")

    mem, mem_tag = build_mem_info(result, SET_INST)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write("<html><head><meta charset='utf-8'>\n")
        f.write(CSS_COMMON)
        f.write("</head><body><pre>\n")

        if mem:
            sorted_addrs = sorted(mem.keys())
            start = sorted_addrs[0]
            prev = start
            chunk_addrs = [start]

            for addr in sorted_addrs[1:]:
                if addr == prev + 1 and len(chunk_addrs) < 16:
                    chunk_addrs.append(addr)
                    prev = addr
                else:
                    f.write(_line_s19_simple_html(start, chunk_addrs, mem, mem_tag) + "\n")
                    start = addr
                    prev = addr
                    chunk_addrs = [addr]

            if chunk_addrs:
                f.write(_line_s19_simple_html(start, chunk_addrs, mem, mem_tag) + "\n")

        f.write("</pre></body></html>\n")

    return html_path



def _line_s19_simple_html(start_addr: int,
                          addrs: list[int],
                          mem: dict[int, int],
                          mem_tag: dict[int, str]) -> str:
    parts = []
    parts.append("&lt;" + f"{start_addr & 0xFFFF:04X}" + "&gt; ")
    for a in addrs:
        b = mem[a]
        tag = mem_tag.get(a, "data")
        cls = "byte "
        if tag == "opcode":
            cls += "opcode"
        elif tag == "operand":
            cls += "operand"
        else:
            cls += "data"
        parts.append(f"<span class='{cls}'>{b:02X}</span> ")
    return "".join(parts).rstrip()



def _make_s1_record(addr: int, data_bytes: list[int]) -> str:
    """
    Construye un registro S1:
      S1 <count> <addr_hi><addr_lo> <data...> <checksum>
    count = 2 (addr) + len(data) + 1 (checksum)
    """
    addr = addr & 0xFFFF
    count = len(data_bytes) + 3  # addr(2) + data + checksum
    ah = (addr >> 8) & 0xFF
    al = addr & 0xFF
    s = count + ah + al + sum(data_bytes)
    cks = (~s) & 0xFF
    return "S1" + f"{count:02X}{addr:04X}" + "".join(f"{b:02X}" for b in data_bytes) + f"{cks:02X}"


def _make_s9_record(entry_addr: int) -> str:
    """
    Registro S9 (fin de fichero, 16 bits):
      S9 <count> <addr_hi><addr_lo> <checksum>
    count = 3 (addr(2) + checksum)
    """
    entry_addr &= 0xFFFF
    count = 3
    ah = (entry_addr >> 8) & 0xFF
    al = entry_addr & 0xFF
    s = count + ah + al
    cks = (~s) & 0xFF
    return "S9" + f"{count:02X}{entry_addr:04X}{cks:02X}"




from typing import Optional

def ensamblar_y_generar_archivos(
    source_path: str,
    excel_path: str,
    out_dir: Optional[str] = None,
    gen_lst: bool = True,
    gen_ms19: bool = True,
    gen_s19_simple: bool = True,
    gen_lst_html: bool = True,
    gen_ms19_html: bool = True,
    gen_s19_html: bool = True,
) -> Optional[CompileResult]:

    # 1) Cargar set de instrucciones
    try:
        SET_INST = cargar_set_instrucciones(excel_path)
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"[ERROR] No se pudo preparar el set de instrucciones: {e}")
        return None

    # 2) Compilar fuente
    try:
        result = compilar_archivo(source_path, SET_INST)
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"[ERROR] Fallo inesperado durante la compilación de '{source_path}': {e}")
        return None

    # 3) Si hay errores → se imprimen en consola y NO se generan archivos
    if result.errors:
        print("\nErrores de compilación (no se generarán archivos de salida):")
        # AQUÍ ESTABA EL BUG: usar el mismo nombre de parámetro dentro de la lambda
        for err in sorted(result.errors, key=lambda err: (err.line_no, err.code)):
            if err.line_no > 0:
                print(f"  Línea {err.line_no:4d}  Error {err.code:03d}: {err.message}")
            else:
                print(f"  Error {err.code:03d}: {err.message}")
        return result

    # 4) Sin errores → generar archivos según flags
    if gen_lst:
        path_lst = generar_lst(source_path, result, out_dir)
        print(f"[OK] Generado: {path_lst}")
    if gen_ms19:
        path_ms19 = generar_ms19(source_path, result, SET_INST, out_dir)
        print(f"[OK] Generado: {path_ms19}")
    if gen_s19_simple:
        path_s19 = generar_s19(source_path, result, SET_INST, out_dir)
        print(f"[OK] Generado: {path_s19}")
    if gen_lst_html:
        path_lst_html = generar_lst_html(source_path, result, SET_INST, out_dir)
        print(f"[OK] Generado: {path_lst_html}")
    if gen_ms19_html:
        path_ms19_html = generar_ms19_html(source_path, result, SET_INST, out_dir)
        print(f"[OK] Generado: {path_ms19_html}")
    if gen_s19_html:
        path_s19_html = generar_s19_html(source_path, result, SET_INST, out_dir)
        print(f"[OK] Generado: {path_s19_html}")

    return result




# ---------------------------------------------------------------------
#  Ejemplo de uso mínimo
# ---------------------------------------------------------------------
def main(argv=None):
    if argv is None:
        argv = sys.argv

    if len(argv) < 2:
        print("Uso:")
        print("  compi <fuente.asm> [banderas] [directorio_salida]")
        print()
        print("Banderas:")
        print("  -l   genera .lst (texto)")
        print("  -s   genera .s19 (formato simple por páginas)")
        print("  -m   genera .ms19 (S-records Motorola)")
        print("  -cX  X∈{l,s,m} genera también HTML coloreado de ese formato")
        print("  -A   genera todos los formatos (txt + html)")
        print()
        print("Ejemplos:")
        print("  compi burbuja.asm              -> .lst y .s19 texto en cwd")
        print("  compi burbuja.asm -lcs         -> .lst txt, .s19 txt + .s19.html")
        print("  compi burbuja.asm -A ./out     -> todos los 6 archivos en ./out")
        sys.exit(1)

    source_path = argv[1]

    # >>> VALIDACIÓN DE EXTENSIÓN <<<
    if not validar_extension_source(source_path):
        sys.exit(1)
    # <<< FIN VALIDACIÓN >>>

    flags_raw = ""
    out_dir = None

    if len(argv) >= 3:
        if argv[2].startswith("-"):
            flags_raw = argv[2][1:]   # quitar '-'
            if len(argv) >= 4:
                out_dir = argv[3]
        else:
            out_dir = argv[2]

    gen_lst, gen_ms19, gen_s19, gen_lst_h, gen_ms19_h, gen_s19_h = parse_flag_string(flags_raw)

    ensamblar_y_generar_archivos(
        source_path=source_path,
        excel_path=DEFAULT_EXCEL,
        out_dir=out_dir,
        gen_lst=gen_lst,
        gen_ms19=gen_ms19,
        gen_s19_simple=gen_s19,
        gen_lst_html=gen_lst_h,
        gen_ms19_html=gen_ms19_h,
        gen_s19_html=gen_s19_h,
    )


if __name__ == "__main__":
    main()
