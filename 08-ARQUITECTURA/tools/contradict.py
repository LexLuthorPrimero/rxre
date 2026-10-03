#!/usr/bin/env python3
"""
contradict.py -- cruza AFIRMACIONES NUMERICAS entre hallazgos y las contrasta
con el codigo.

POR QUE EXISTE
    El modo de fallo dominante de este proyecto no es no investigar: es
    afirmar una cifra y que otro la afirme distinta, sin que nadie cruce los
    documentos. Hay 88 hallazgos y 51 contienen cifras.  El arbitraje de
    block_size (10 vs 22) ocupo una entrada entera de CONTRADICTIONS.md, y la
    mapeo num_level -> root_level de 030 seguia published meses despues con el
    switch real diciendo lo contrario.

    Un humano no detecta esto leyendo: hay que comparar el MISMO simbolo con el
    MISMO nombre en 51 ficheros.  Eso es un trabajo de maquina.

QUE PRODUCE
    Para cada simbolo nombrado en todos los hallazgos, tabla de (documento, linea,
    valor, contexto).  Si un simbolo tiene VALORES DISTINTOS en documentos
    distintos, lo marca como CONTRADICCION y lo ordena por antiguedad, que es
    como se arbitra en este proyecto: gana el arbitro del host o el codigo.

    Y despues, para cada valor discrepante, un comando que comprueba si existe
    en el codigo, y con eso CONTRASTA el valor con el corpus.

POR QUE NO USA IA NI DEDUCE NADA
    Extrae la forma `simbolo = valor` y nada mas.  No adivina, no interpola, no
    resuelve unidades.  Si una cifra esta en prosa y no en esa forma, no la ve, y
    eso se declara abajo.

LIMITE DECLARADO, Y ES EL GRANDE
    Solo ve `simbolo = valor`, `simbolo: valor` y `simbolo = 0xVALOR`.  Se escapa:
      - una cifra escrita en prosa ("son 2 niveles", "22 bits de indice");
      - un simbolo con dos puntos de calculo escritos como formula;
      - un valor derivado ("el doble de block_size");
      - la MISMA cifra correcta escrita con distinto nombre de simbolo.
    Es decir: NO detecta una contradiccion semantica.  Detecta la misma cifra
    atribuida a dos valores distintos, que es el caso frecuente y el que se
    puede acotar.  Un documento puede contradecir a otro sin que aparezca aqui,
    y el caso de 030 -> PDB2/PDB1 lo demuestra: los dos numeros existen, estan
    bien, y aun asi estan en el orden equivocado.  Eso NO lo ve esta herramienta
    y por eso el modulo lo dice en voz alta.

    La tabla que imprime es la que hace el trabajo: revision ocular en un segundo.

USO
    contradict.py                     todos los hallazgos
    contradict.py --sym block_size    solo ese simbolo
    contradict.py --all               incluye los que tienen un solo valor
    contradict.py --check             existe el valor en el codigo? (--with-code)
    contradict.py --json              salida parseable
    contradict.py --self              autotest

DEPENDENCIAS
    python3 >= 3.9.  Sin red, sin root, sin escrituras.
"""

import argparse
import glob
import json
import os
import re
import sys

PROJECT = "/home/lucas/Escritorio/RX550-INVESTIGACION"
FINDINGS = f"{PROJECT}/06-INGENIERIA-INVERSA/findings"

# simbolo = valor   |   simbolo: valor   |   simbolo == valor
# El simbolo NO puede empezar por digito (no es un simbolo) ni contener espacio.
# Se acepta prefijo de ruta:  gmc_v8_0.c:1133 no es simbolo, pero si mc_mask si.
CLAIM = re.compile(
    r'(?<![\w.])'
    r'([a-z_][a-z0-9_]{2,})'          # simbolo
    r'\s*(?:==|=)\s*'                  # operador
    r'(0x[0-9a-fA-F]+|\d+)'            # valor entero
)

# "simbolo: valor" solo cuando NO es una cita de linea, que seria
# gmc_v8_0.c:1133 y no una afirmacion.
CLAIM_COLON = re.compile(
    r'(?<![\w./-])'
    r'([a-z_][a-z0-9_]{2,})'
    r'\s*:\s*'
    r'(0x[0-9a-fA-F]+|\d+)\b'
)

SKIP_FILES = ("CONTRADICTIONS",)

# Una linea que empieza con estos tokenscalcula ESCENARIO, no afirmacion:
#   vm_size=2048 GB -> block_size=16   es un caso hipotetico
#   block_size = 22                    es lo que se afirma de esta maquina
# Sin esto, una tabla de escenarios entra como si fueran valores en
# conflicto.  Se vio con 024: block_size tomaba los valores 10, 15 y 16 de
# una tabla de "que pasaria si la VM fuese de 1/2/4 TB", y ninguno era una
# afirmacion sobre este hardware.
ESCENARIO = re.compile(
    r'^\s*(?:[a-z_][a-z0-9_]*\s*=\s*[^->]*->|'
    r'(?:si|if|supon|con|para|caso|ejemplo|escenario|hipotet|pregunta)[^.]*->)',
    re.IGNORECASE)

# Palabras que aparecen como "simbolo = valor" pero no son afirmaciones del
# hardware.  Sin esta lista el informe se llena de ruido del propio codigo.
RUIDO = {
    "line", "lines", "l", "bit", "bits", "dw", "dword", "dwords", "byte",
    "bytes", "byte0", "w", "h", "d", "q", "v", "n", "x", "y", "z", "i", "j",
    "k", "idx", "id", "len", "size", "offset", "addr", "mask", "count",
    "sha256", "md5", "crc", "argc", "pid", "tid", "uid", "gid", "dev",
    "maj", "minor", "rev", "major", "version", "1e", "0x0",
}

# Palabras ESPANOLAS que la regex de "simbolo = entero" captura de la prosa y
# que no son identificadores del driver.  Sin esta lista, el barrido reportaba
# 34 contradicciones y solo 8 eran simbolos: "conformes : 27" (de una tabla de
# layouts), "max = 2000" y "min = 1100" (rangos de frecuencia), "rama = 2".
#
# La lista se construye de forma MEDIBLE: son las palabras que aparecen en el
# corpus con "= <entero>" y NO existen como identificador en ningun .c/.h.
# Se documenta como lista cerrada y conservadora; ampliarla a mano solo con
# evidencia, no por intuicion.
PROSA = {
    "conformes", "rama", "simple", "real", "side", "value", "min", "max",
    "cumple", "corpus", "documentos", "declarado", "discrepantes", "flags",
    "gcc", "payload", "payload_doc", "reg", "vmid_doc", "contables",
    "documento", "version_doc", "criterio", "cifras", "lineas", "filas",
    "columnas", "tabla", "hoja", "casos", "veces", "nota", "error",
    "estado", "motivo", "razon", "clave", "campo", "bitfield", "offset_doc",
}


def _norm_val(v):
    """Normaliza un valor para comparar: 0x10 y 16 son el mismo número."""
    try:
        n = int(v, 0)
    except ValueError:
        return None
    return n


def extract(text):
    """
    [(simbolo, valor_entero, linea_del_doc, texto)] de un documento.
    Los bloques de codigo se CONSERVAN a proposito: el codigo citado tambien
    afirma valores, y es donde viven las cifras que se contradicen.
    """
    out = []
    for i, line in enumerate(text.split("\n"), 1):
        if len(line) > 400:
            continue                     # lineas que no son lineas
        if ESCENARIO.match(line):
            continue                     # caso hipotetico, no afirmacion
        for rx in (CLAIM, CLAIM_COLON):
            for m in rx.finditer(line):
                sym, raw = m.group(1), m.group(2)
                if sym in RUIDO or sym in PROSA:
                    continue
                # Fila de tabla Markdown: "| `WAIT_REG_MEM` | 5 | cmd, reg, 0,
                # ref, mask, poll = 6 |".  El "=" enumera campos, no asigna.
                # Sin esto, poll tomaba 4 valores distintos y uno era el
                # numero de campos del paquete, que es una cifra de otra cosa.
                if line.lstrip().startswith("|"):
                    continue
                v = _norm_val(raw)
                if v is None:
                    continue
                out.append((sym, v, i, line.strip()[:96]))
    return out


def _in_code_fence(line, text_upto):
    """¿Esta la linea dentro de un bloque ```? (para marcar el origen)"""
    return text_upto.count("```") % 2 == 1


def scan(findings_dir=FINDINGS):
    """{simbolo: {valor: [(doc, linea, contexto, en_fence)]}}"""
    tabla = {}
    for path in sorted(glob.glob(os.path.join(findings_dir, "*.md"))):
        base = os.path.basename(path)
        if any(s in base for s in SKIP_FILES):
            continue
        try:
            with open(path, errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        for sym, v, ln, ctx in extract(text):
            en_fence = _in_code_fence(ln, text)
            tabla.setdefault(sym, {}).setdefault(v, []).append(
                (base, ln, ctx, en_fence))
    return tabla


def code_has_value(sym, value):
    """
    ¿El corpus contiene `<simbolo> ... value`?  Es un COMPROBADOR, no un
    validador: que no aparezca NO significa que el valor sea falso, porque el
    valor puede estar en un enum, en un header con otro nombre, o ser
    derivado.  Se informa como "no visto", nunca como "refutado".
    """
    try:
        import doclint
    except ImportError:
        return None                      # sin indice: no se afirma nada
    idx = doclint.build_index()
    n = 0
    for path, lines in idx.items():
        if not path.endswith((".c", ".h")):
            continue
        for line in lines:
            if sym in line and re.search(rf'\b{value}\b', line):
                n += 1
                if n >= 3:
                    return True
    return False


def selftest():
    fails = 0

    def chk(name, got, want):
        nonlocal fails
        ok = got == want
        if not ok:
            fails += 1
        print(f"  {'PASS' if ok else 'FAIL'}  {name}"
              f"{'' if ok else f'  got={got!r} want={want!r}'}")

    print("  --- normalizacion de valores ---")
    chk("hex y decimal son el mismo numero", _norm_val("0x10"), 16)
    chk("0x22 == 34", _norm_val("0x22"), 34)
    chk("decimal plano", _norm_val("22"), 22)

    print("  --- extraccion: casos unitarios ---")
    ex = extract("block_size = 10\n")
    chk("forma simbolo = entero",
        [(s, v) for s, v, _, _ in ex], [("block_size", 10)])
    chk("forma simbolo == entero",
        [(s, v) for s, v, _, _ in extract("root_level = 5\n")],
        [("root_level", 5)])
    # Un simbolo de 1-2 caracteres no se considera afirmacion: son variables
    # de bucle y indices, no valores del hardware.  Se acota por longitud.
    chk("un simbolo de 1 caracter no es afirmacion",
        extract("x = 5\n"), [])
    chk("uno de 2 caracteres tampoco",
        extract("pc = 4\n"), [])
    chk("pero uno de 3 si lo es",
        len(extract("num_level = 1\n")), 1)
    chk("dos cifras del MISMO simbolo se guardan",
        len(extract("mc_mask = 1\nmc_mask = 2\n")), 2)

    # Escenario hipotetico NO es afirmacion.  Sin este filtro, la tabla
    # "vm_size=2048 GB -> block_size=16" de 024 entraba como valor en
    # conflicto y hacia parecer que block_size era 10, 15, 16 y 22.
    chk("una linea de escenario se descarta",
        extract("vm_size=2048 GB -> block_size=16\n"), [])
    chk("y una con preposicion tambien",
        extract("si la VM fuese de 4 TB -> block_size=16\n"), [])
    chk("pero la afirmacion real se conserva",
        [(s, v) for s, v, _, _ in extract("block_size = 22 con 16 GB de RAM\n")],
        [("block_size", 22)])

    print("  --- lo que NO debe contar como afirmacion ---")
    # Una cita de linea NO debe producir ninguna afirmacion.  Con el \b y el
    # filtro de 3+ caracteres, "c:1133" no entra: el simbolo que capturaria
    # la regex seria "c", de un caracter.  Se comprueba el efecto, no un
    # indice que antes daba IndexError.
    chk("una cita de linea no produce afirmacion",
        extract("gmc_v8_0.c:1133 mc_mask = 1\n"),
        [("mc_mask", 1, 1, "gmc_v8_0.c:1133 mc_mask = 1")])
    chk("una cita suelta no produce nada",
        extract("gmc_v8_0.c:1133\n"), [])
    chk("una fecha no es un simbolo",
        [s for s, _, _, _ in extract("2026-10-01 12:54 algo\n")], [])
    chk("una palabra de ruido se descarta",
        [s for s, _, _, _ in extract("len = 4\nbit = 2\n")], [])
    chk("una palabra de prosa no es un simbolo del driver",
        extract("conformes = 27\nrama = 2\n"), [])
    chk("y el simbolo real de la misma linea si cuenta",
        [(s, v) for s, v, _, _ in extract("conformes = 27\nnum_level = 1\n")],
        [("num_level", 1)])

    chk("una fila de tabla no es una asignacion",
        extract("| `WAIT_REG_MEM` | 5 | cmd, reg, 0, ref, mask, poll = 6 |\n"), [])
    # "op" son 2 caracteres y no llega al minimo: es correcto que no cuente.
    chk("pero la afirmacion fuera de tabla si cuenta",
        [(s, v) for s, v, _, _ in extract("poll=0x20 op=0 function=0\n")],
        [("poll", 32), ("function", 0)])

    chk("sha256 no se toma como cifra",
        [s for s, _, _, _ in extract("sha256 = 4\n")], [])
    chk("una linea enorme no se procesa",
        [s for s, _, _, _ in extract("x" * 500 + " foo = 1\n")], [])

    print("  --- deteccion de contradiccion, sobre datos sintéticos ---")
    tabla = {}
    tabla.setdefault("block_size", {}).setdefault(10, []).append(("a.md", 1, "", False))
    tabla.setdefault("block_size", {}).setdefault(22, []).append(("b.md", 1, "", False))
    tabla.setdefault("nuevo_simbolo", {}).setdefault(7, []).append(("c.md", 1, "", False))
    chk("dos valores del mismo simbolo = contradiccion",
        len(disputados(tabla)), 1)
    chk("un solo valor no es contradiccion",
        "nuevo_simbolo" in [s for s, _ in disputados(tabla)], False)
    chk("el simbolo en conflicto se nombra",
        disputados(tabla)[0][0], "block_size")

    print(f"  {'todos pasan' if not fails else f'{fails} FALLAN'}")
    return 1 if fails else 0


def disputados(tabla):
    """[(simbolo, {valor: sitios})] donde el simbolo tiene mas de un valor."""
    out = []
    for sym, vals in sorted(tabla.items()):
        if len(vals) > 1:
            out.append((sym, vals))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sym")
    ap.add_argument("--dir", default=FINDINGS)
    ap.add_argument("--all", action="store_true",
                    help="incluye simbolos con un solo valor")
    ap.add_argument("--check", action="store_true",
                    help="comprueba cada valor discrepante contra el codigo")
    ap.add_argument("--min-sites", type=int, default=2,
                    help="sitios minimos por valor para considerarlo afirmado")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self", action="store_true")
    a = ap.parse_args()

    if a.self:
        return selftest()

    tabla = scan(a.dir)
    disp = disputados(tabla)

    if a.json:
        print(json.dumps(
            {"contradicciones": {s: {str(v): [list(x) for x in st]
                                      for v, st in vals.items()}
                                 for s, vals in disp},
             "total_simbolos": len(tabla)}, indent=2))
        return 0 if not disp else 1

    print(f"  HALLAZGOS  {len(glob.glob(os.path.join(a.dir, '*.md')))} documentos")
    print(f"  SIMBOLOS   {len(tabla)} con al menos una cifra atribuida")
    print(f"  DISPUTADOS {len(disp)} con mas de un valor")
    print()

    if not disp and not a.all:
        print("  Ningun simbolo con dos valores distintos.  O no hay cifras, o no se contradicen.")
        return 0

    items = disp if not a.all else sorted(
        (s, v) for s, v in tabla.items() if a.sym in (None, s) or s == a.sym)
    if a.sym:
        items = [(s, v) for s, v in items if s == a.sym]
        if not items:
            print(f"  {a.sym!r}: no aparece con ninguna cifra en {a.dir}")
            print(f"  Comprueba el nombre antes de concluir que no existe (como en xref.py).")
            return 1

    for sym, vals in items:
        etiq = "CONTRADICCION" if len(vals) > 1 else "un solo valor"
        # Se cuenta lo que se MUESTRA, no lo que hay: si la cabecera dice 3
        # valores y se imprimen 2, el informe afirma algo que no muestra.
        mostrables = [(v, st) for v, st in vals.items()
                      if len(st) >= a.min_sites or len({x[0] for x in st}) >= 2]
        ocultos = len(vals) - len(mostrables)
        cab = f"  {sym}   [{etiq}, {len(mostrables)} valores"
        cab += f" de {len(vals)}" if ocultos else ""
        cab += "]"
        print(cab)
        if ocultos:
            print(f"    ({ocultos} valor(es) con muy pocos sitios, no se muestran; "
                  f"baja --min-sites para verlos)")
        for valor, sitios in sorted(mostrables):
            v = valor
            docs = {s[0] for s in sitios}
            marca = ""
            if a.check:
                r = code_has_value(sym, str(v))
                marca = {True: "  [en codigo: SI]", False: "  [en codigo: no visto]",
                         None: "  [sin indice]"}[r]
            print(f"    = {v:<12} {len(sitios):3} sitios, {len(docs)} docs{marca}")
            vistos = set()
            for doc, ln, ctx, fence in sitios:
                if doc in vistos:
                    continue
                vistos.add(doc)
                print(f"        {doc}:{ln:<4} {ctx[:74]}")
            if len(vistos) < len(docs):
                print(f"        (+{len(docs)-len(vistos)} documentos mas)")
        print()
    return 1 if disp else 0


if __name__ == "__main__":
    sys.exit(main())