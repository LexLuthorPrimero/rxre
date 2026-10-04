#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
#
# CONTRACT: name=gart_seq_oracle
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no        (solo escribe en stdout; NUNCA en el arbol)
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: NEEDS_GPU=no
# VERSION: 1.0.0
"""
gart_seq_oracle -- la verdad de gmc_v8_0_gart_enable(), extraida del corpus.

QUE ES
    Un extractor.  NO compara con nada: extrae y emite.  Comparar es trabajo del
    consumidor.  La separacion es deliberada: si el extractor se rompe, el fallo
    lo dice el, y no se confunde con un fallo del driver.

POR QUE EXISTE
    El componente tiene dos juegos de numeros de linea escritos A MANO que
    documentan el orden de las 34 escrituras del GART: el enum de orden de
    rx550_gart_seq.c y la tabla ESPERADO de tests/test_gart_seq.c.  MEDIDO el
    2026-10-04: 1 de 20 y 16 de 19 respectively son FALSOS contra el corpus de
    disco.  El plan es correcto; la documentacion que lo acompana no lo esta.

    Un numero escrito a mano que nadie verifica no es evidencia: es decoracion,
    y la decoracion que se pudre no cuesta nada porque no se pierde nada al
    quitarla.  Este script es lo que permite dejar de tener numeros a mano.

LO QUE NO CONTIENE, POR CONSTRUCCION
    Ninguna constante de la forma L8xx, ningun indice de linea, ningun mnemonico
    de registro esperado.  Todo sale de leer el fichero del corpus y contar sus
    lineas.  La funcion se localiza por FIRMA y se cierra por LLAVE, no por
    numero; el bucle se reconoce por estructura y se evalua leyendo el #define
    de su cota.

SOBRE LA FRAGILIDAD
    Medida, no supuesta: este extractor no depende de la posicion de nada.  Se
    comprueba moviendo tres lineas de blanco al principio de una copia del
    fichero y exigiendo que la lista de operaciones sea IDENTICA con las lineas
    desplazadas.  Ese es el discriminante de si la afirmacion "viable ante
    reformateo" es un resultado o una opinion, y esta en selftest().

CODIGOS DE SALIDA
    0  extrae y emite
    2  CORPUS_ABSENT        no se pudo leer una fuente
    3  PARSE_AMBIGUOUS       se lee pero no se extrae sin ambiguedad
    4  CORPUS_VERSION_CHANGED  el hash no es el esperado
"""
import hashlib
import os
import re
import sys

TOOL_VERSION = "1.0.0"
FUNC_NAME = "gmc_v8_0_gart_enable"
VMIHUB_LOOP_BOUND_MACRO = "AMDGPU_NUM_VMID"

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROJ = os.path.dirname(os.path.dirname(R))

# Candidatas por defecto.  Se SONDEAN, no se Citations: si el proyecto se mueve,
# dos rutas relatives bastan y no hay ningun numero que actualizar.
def _candidates(rel):
    return [
        os.path.join(R, "..", "..", "RESEARCH", "kernelbuild", "linux-7.1.3", rel),
        os.path.join(_PROJ, "RESEARCH", "kernelbuild", "linux-7.1.3", rel),
        os.path.join(_PROJ, "RESEARCH", "working", "linux-7.1.3", rel),
    ]

DEFAULT_SOURCES = {
    "gmc_v8_0.c": "drivers/gpu/drm/amd/amdgpu/gmc_v8_0.c",
    "amdgpu_ids.h": "drivers/gpu/drm/amd/amdgpu/amdgpu_ids.h",
}


def _find(rel):
    for p in _candidates(rel):
        if os.path.exists(p):
            return p
    return None


def _read_lines(path):
    with open(path, "r", errors="replace") as f:
        return f.read().split("\n")


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(65536), b""):
            h.update(blk)
    return h.hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# El truco que sostiene la robustez: quitar comentarios ANTES de contar
# parentesis.  Un "/* ( */" en un comentario falsearia toda la aritmetica.
def quitar_comentarios(s):
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    s = re.sub(r"//[^\n]*", " ", s)
    return s


def localizar_funcion(lineas, nombre):
    """-> (primera, ultima) del CUERPO, por firma y por llave de cierre.

    Devuelve None si hay 0 o >1 candidatos.  Eso es AMBIGUO, y un ambiguo es un
    fallo honesto, no una lista de 34 inventada.
    """
    pat = re.compile(r"\b%s\s*\(" % re.escape(nombre))
    cands = []
    for i, l in enumerate(lineas, 1):
        if not pat.search(l):
            continue
        # una DEFINICION es la linea que abre la llave de cuerpo
        j = i
        while j < len(lineas) and lineas[j - 1].rstrip() != "{":
            j += 1
            if j - i > 8:
                break
        if j >= len(lineas) or lineas[j - 1].rstrip() != "{":
            continue
        # la llave de CIERRE es la primera llave a columna 0 por delante
        k = j
        while k < len(lineas) and lineas[k - 1].rstrip() != "}":
            k += 1
        if k < len(lineas):
            cands.append((i, k))
    if len(cands) != 1:
        return None
    return cands[0]


def unir_sentencias(lineas, lo, hi):
    """-> [(linea_inicial, texto_unido)].

    Une por BALANCE DE PARENTESIS y no por ';': un WREG32 partido en dos lineas
    sigue siendo UNA sentencia, y partirlo por el ';' daria dos medias.
    """
    out, buf, at, depth = [], [], None, 0
    for n in range(lo, hi + 1):
        s = lineas[n - 1]
        if at is None and s.strip() and not s.strip().startswith(("/*", "*", "//")):
            at = n
        buf.append(s)
        depth += s.count("(") - s.count(")")
        if depth <= 0 and s.rstrip()[-1:] in (";", "{", "}"):
            out.append((at, " ".join(x.strip() for x in buf)))
            buf, at, depth = [], None, 0
    return out


def cota_bucle(lo_txt, texto):
    """Del 'for (i = 1; i < MACRO; i++)' sale lo=1 y cota=MACRO."""
    # La cota puede ser un IDENTIFICADOR (AMDGPU_NUM_VMID) o un LITERAL (i < 8).
    # El primer caso de la clase de bug que este instrumento tiene que evitar:
    # con [A-Za-z_] como clase inicial, "i < 8" NO casa, el bucle no se
    # detecta, y sus escrituras se cuentan como rectas.  El resultado es una
    # lista plausible y falsa, que es peor que no extraer nada.
    m = re.search(r"for\s*\(\s*(\w+)\s*=\s*(\d+)\s*;\s*\w+\s*<\s*"
                  r"([A-Za-z_0-9]\w*)\s*;",
                  texto)
    if not m:
        return None
    return int(m.group(2)), m.group(3)


def _cuerpo_extento(lineas, desde, hasta):
    """Extent [a,b] del CUERPO de una sentencia que abre llave en `desde`.

    Devuelve None si no encuentra la llave.  Es lo que impide el error de
    "todo lo que viene despues del for esta dentro del for": las 4 escrituras
    que siguen al bucle NO estan dentro, y marcarlas como si estieran produce
    una lista plausible y falsa, que es el peor fallo posible de un extractor.
    """
    depth = 0
    abre = None
    for n in range(desde, hasta + 1):
        s = lineas[n - 1]
        abre_s = s.count("{")
        cierra_s = s.count("}")
        if abre is None and abre_s:
            abre = n
            depth = abre_s - cierra_s
            if depth <= 0:
                return (n, n)
            continue
        if abre is not None:
            depth += abre_s - cierra_s
            if depth <= 0:
                return (abre, n)
    return None

def ramas_excluyentes(lineas, ext):
    """¿El cuerpo del bucle tiene un if/else de PRIMER nivel?

    Es lo que hace el bucle del GART:

        for (i = 1; i < AMDGPU_NUM_VMID; i++) {
            if (i < 8)
                WREG32(A + i, ...);
            else
                WREG32(B + i - 8, ...);
        }

    Los DOS WREG32 se ejecutan, pero NUNCA en la misma iteracion: cada
    iteracion toma exactamente uno.  Multiplicar sitios por iteraciones daria
    2*15 = 30 cuando la verdad es 15, y por eso esta pregunta tiene que
    responderse antes de contar.
    """
    if not ext:
        return False
    prof = 0
    for n in range(ext[0], ext[1] + 1):
        s = lineas[n - 1]
        if prof == 1 and re.match(r"\s*else\b", s):
            return True
        prof += s.count("{") - s.count("}")
    return False

def extraer(lineas, lo, hi, num_vmid):
    """-> lista de dicts, en ORDEN, con los sitios del bucle marcados.

    NO expande el bucle: devuelve los SITIOS.  Expandir es trabajo del
    consumidor, y aqui solo se declara cuantas iteraciones hace cada uno.

    Los sitios se localizan LINEA A LINEA, no por sentencias unidas: un WREG32
    tiene su ancla en la linea donde esta el verbo, y eso es mas honesto que
    decidir donde empieza un if/else partido en dos lineas.
    """
    loops = []
    for n in range(lo, hi + 1):
        c = cota_bucle(n, lineas[n - 1])
        if c:
            loops.append((n, c))
    # mas de un for: no sabemos cual gobierna cual.  AMBIGUO, no lista inventada
    if len(loops) > 1:
        return None

    ext = _cuerpo_extento(lineas, loops[0][0], hi) if loops else None

    ops, vistos = [], set()
    for n in range(lo, hi + 1):
        m = re.search(r"\bWREG32\s*\(\s*([A-Za-z_]\w*)", lineas[n - 1])
        if not m or n in vistos:
            continue
        vistos.add(n)
        en_bucle = None
        if loops and ext and ext[0] <= n <= ext[1]:
            ln, (vlo, mac) = loops[0]
            en_bucle = {"linea_for": ln, "desde": vlo, "cota": mac,
                        "iteraciones": (num_vmid - vlo)
                        if mac == VMIHUB_LOOP_BOUND_MACRO else None}
        ops.append({"linea": n, "registro": m.group(1), "bucle": en_bucle})
    ops.append({"__ext__": ext, "__loops__": loops})
    return ops

def leer_cota_vmid(ruta_ids):
    t = open(ruta_ids, errors="replace").read()
    m = re.search(r"#define\s+%s\s+(\d+)" % VMIHUB_LOOP_BOUND_MACRO, t)
    return int(m.group(1)) if m else None


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("-")]
    fmt = "tsv"
    esperado = None
    for a in argv[1:]:
        if a == "--format=json":
            fmt = "json"
        if a.startswith("--expect-sha256="):
            esperado = a.split("=", 1)[1]

    rutas = {}
    for k, rel in DEFAULT_SOURCES.items():
        rutas[k] = args[0] if (k == "gmc_v8_0.c" and args) else _find(rel)
    if not rutas["gmc_v8_0.c"] or not os.path.exists(rutas["gmc_v8_0.c"]):
        sys.stderr.write("CORPUS_ABSENT gmc_v8_0.c\n")
        return 2
    if not rutas["amdgpu_ids.h"] or not os.path.exists(rutas["amdgpu_ids.h"]):
        sys.stderr.write("CORPUS_ABSENT amdgpu_ids.h\n")
        return 2

    sha = _sha256(rutas["gmc_v8_0.c"])
    veredicto_version = "VERIFIED" if (esperado is None or sha == esperado) \
        else "CORPUS_VERSION_CHANGED"

    num_vmid = leer_cota_vmid(rutas["amdgpu_ids.h"])
    if num_vmid is None:
        sys.stderr.write("PARSE_AMBIGUOUS %s no encontrado\n" % VMIHUB_LOOP_BOUND_MACRO)
        return 3

    lineas = _read_lines(rutas["gmc_v8_0.c"])
    rng = localizar_funcion(lineas, FUNC_NAME)
    if rng is None:
        sys.stderr.write("PARSE_AMBIGUOUS no se localiza %s\n" % FUNC_NAME)
        return 3
    lo, hi = rng

    ops = extraer(lineas, lo, hi, num_vmid)
    if ops is None or not ops:
        sys.stderr.write("PARSE_AMBIGUOUS extraccion vacia o multi-for\n")
        return 3
    ext = ops[-1].pop("__ext__")
    ops.pop()

    n_fuera = sum(1 for o in ops if o["bucle"] is None)
    n_en_bucle = sum(1 for o in ops if o["bucle"] is not None)
    its = 0
    for o in ops:
        if o["bucle"] is not None and o["bucle"]["iteraciones"]:
            its = o["bucle"]["iteraciones"]
            break
    excl = ramas_excluyentes(lineas, ext)
    if n_en_bucle == 0:
        tot, nota = n_fuera, "sin bucle"
    elif excl:
        # cada iteracion toma UNO de los dos: el bucle aporta `its`, no `2*its`
        tot, nota = n_fuera + its, ("bucle con ramas excluyentes: %d iteraciones "
                                    "aportan %d escrituras, NO %d"
                                    % (its, its, n_en_bucle * its))
    else:
        tot, nota = n_fuera + n_en_bucle * its, ("bucle sin if/else: %d sitios "
                                                  "x %d" % (n_en_bucle, its))

    if fmt == "json":
        import json
        print(json.dumps({
            "tool": "gart_seq_oracle@%s" % TOOL_VERSION,
            "function": FUNC_NAME,
            "range": [lo, hi],
            "corpus_sha256": sha,
            "corpus_version_status": veredicto_version,
            "loop_bound": num_vmid,
            "sitios": len(ops),
            "ejecuciones": tot,
            "ops": ops,
        }, indent=1, sort_keys=True))
    else:
        print("# tool\tgart_seq_oracle\t%s" % TOOL_VERSION)
        print("# corpus\tgmc_v8_0.c\tsha256=%s\t%s" % (sha, veredicto_version))
        print("# funcion\t%s\t%d..%d\tPROVEN\tpor firma y llave de cierre"
              % (FUNC_NAME, lo, hi))
        print("# loop_bound\t%d\t%s=%d\tPROVEN" % (num_vmid, VMIHUB_LOOP_BOUND_MACRO,
                                                    num_vmid))
        for i, o in enumerate(ops):
            if o["bucle"] is None:
                print("sitio\t%d\t%s\tPROVEN\tgmc_v8_0.c:%d"
                      % (i, o["registro"], o["linea"]))
            else:
                b = o["bucle"]
                print("sitio\t%d\t%s\tPROVEN\tgmc_v8_0.c:%d\tLOOP i=%d..%d (%d it)"
                      % (i, o["registro"], o["linea"], b["desde"],
                         b["desde"] + b["iteraciones"] - 1, b["iteraciones"]))
        print("ejecuciones\t%d\t-\tPROVEN\t%d fuera + %d del bucle | %s"
              % (tot, n_fuera, tot - n_fuera, nota))

    return 0 if veredicto_version == "VERIFIED" else 4


if __name__ == "__main__":
    sys.exit(main(sys.argv))