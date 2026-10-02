#!/usr/bin/env python3
# CONTRACT: name=doclint
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
"""
DOCLINT -- verificador de hallazgos, para no repetir los errores que ya cometi.

Por que existe. No es un linter generico de estilo. Cada comprobacion
corresponde a un fallo REAL de mi propia historia, con su coste:

  1. Fragmento de otro idioma. Ha aparecido en 031, 032, 033, 034, 036 y 037.
     Siempre un fragmento CJK pegado dentro de una frase en castellano, y
     SIEMPRE se me paso porque lo escribi rapido y no lo relei. Es el defecto
     mas frecuente que tengo y el mas facil de automatizar.

  2. Cita de linea sin verificar. En 032 cité "gfx_v8_0.c:6231-6248" sin
     haberla leido; la linea real era otra. En 036 cité "6162-6178" y tube
     que comprobarlo despues. Un numero de linea que no existe, o que existe
     pero no dice lo que afirmo, es la forma mas comun de convertir una
     lectura cuidadosa en una afirmacion falsa.

  3. Marcadores de trabajo. TODO / FIXME / XXX / "???" en un documento que se
     presenta como cerrado. El estado del proyecto exige que un hallazgo diga
     explicitamente lo que NO se sabe; un marcador suelto no es eso.

  4. Numero declarado dos veces con valores distintos. En 035 tres sesiones
     declararon block_size como 13, 10 y 22/23/24. El conflicto se resolvio
     leyendo el log del kernel. Un linter que detecte la discrepancia EN el
     documento, antes de commitear, habria Evita el trabajo.

  5. Cabecera incompleta. El proyecto exige un conjunto de campos de
     clasificacion. Si faltan, el hallazgo no declara su propio estado y no es
     auditable.

Uso:
  python3 doclint.py <fichero.md> [<fichero.md> ...]
  python3 doclint.py --self            # comprueba los documentos que YO escribi
  python3 doclint.py --strict          # trata los avisos como fallos
Salida: codigo de salida 1 si hay ERROR, 0 si solo hay avisos.
"""
import re
import os
import tempfile
import os
import sys
import glob

ROOT = "/home/lucas/Escritorio/RX550-INVESTIGACION"
CORPUS_ROOTS = [
    f"{ROOT}/RESEARCH/working/linux-7.1.3",
    f"{ROOT}/08-ARQUITECTURA",
    f"{ROOT}/04-IMPLEMENTACION",
    "/usr/src/kernels/7.1.3-200.nobara.fc44",
]

# --------------------------------------------------------------------- 1
# Fragmentos de otro idioma. Rangos CJK, Hangul, y las zonas que aparecieron.
#
# Notado alRdame: los fragmentos que se me colaron NO eran CJK generico. Eran
# cosas como "fjCpu", "zyj", "calculation", "元siccion", "annon", "携手". Los
# ultimos dos son CJK; los primeros son basura lexica que un linter de CJK no
# detecta. Por eso hay dos comprobaciones: rango de escritura, Y palabras
#（ACEPTADAS） que son intrusiones conocidas.
CJK = re.compile(
    "["
    "\u1100-\u11ff"   # Hangul jamo
    "\u2e80-\u9fff"   # CJK radical..unificado
    "\uac00-\ud7af"   # Hangul silabas
    "\uf900-\ufaff"   # compatibilidad CJK
    "\uff00-\uffef"   # formas ASCII/fullwidth
    "\u3040-\u30ff"   # hiragana + katakana
    "]")

# Intrusiones lexicales concretas que ya se me colaron. Lista corta y
# justificada uno por uno en el docstring del commit; no es un diccionario
# arbitrario: cada entrada se puede enseñar con su documento.
FULLWIDTH_PUNCT = set("\uff5c\uff5d\uff5b\uff08\uff09\uff0c\uff1a\uff1b")

KNOWN_INTRUSIONS = [
    (r"\bfj\w*",            "fj* -- residuo de escritura"),
    (r"\bzyj\w*",           "zyj* -- residuo de escritura"),
    (r"\bannon\b",          "annon -- residuo de escritura"),
    (r"\bannon\w*",         "annon* -- residuo de escritura"),
    (r"\btalos\b",          "talos -- residuo de escritura"),
    (r"\bguar\w*niz\w*",    "garantiz* truncado"),
    (r"\bconstrand\w*",     "resto de palabra en otro idioma"),
    (r"\bnedott\w*",        "resto de palabra en otro idioma"),
    (r"\bstorun\w*",        "resto de palabra en otro idioma"),
    (r"\btakisto\w*",       "resto de palabra en otro idioma"),
]

# --------------------------------------------------------------------- 2
#
# BUG PROPIO QUE ESTA MISMA COMPROBACION CAUSO, y que habria hecho el linter
# inservible: la primera version era case-INsensitive, asi que \bTODO\b casaba
# con la palabra castellana "todo". Con un corpus en castellano, "todo el ASIC",
# "para todo" y "todo lo que" dan miles de falsos positivos y el linter deja de
# usarse en dos rondas.
#
# La regla: TODO / FIXME / XXX / TBD son convenciones en MAYUSCULAS. Se exige
# mayusculas. "PENDIENTE" si es legitimo en castellano y no se busca, asi que
# solo se marca cuando va solo en una linea y con mayuscula inicial.
PLACEHOLDERS = re.compile(r"(?:\bTODO\b|\bFIXME\b|\bXXX\b|\bTBD\b|\?\?\?)")
PENDIENTE = re.compile(r"\bPENDIENTE\b")

# --------------------------------------------------------------------- 3
CITE = re.compile(r"`?([A-Za-z0-9_./\-]+\.[ch])[`:]*(\d+)(?:\s*[-–]\s*(\d+))?`?")

REQUIRED_FIELDS = [
    "CLASSIFICATION", "WORK_CLASS", "WRITE_EXECUTION",
    "MODIFICATIONS", "RUNTIME",
]

# Vocabulario de clasificacion que el proyecto usa. Un token fuera de esta
# lista no es necesariamente un error, pero se avisa: la gracia de un estado
# tipado esta en que se puede comprobar.
KNOWN_CLASSES = {
    "PROVEN", "PROVEN_DERIVED", "PROVEN_ABSENT", "PROVEN_ABSENCE",
    "DERIVATION", "HYPOTHESIS", "REFUTED", "NOT_DETERMINED",
    "NOT_OBSERVED", "NOT_DETERMINED", "OBSERVED", "OBSERVATION",
    "NEGATIVE_RESULT", "SECONDARY_CORROBORATION", "PRIMARY_DOCUMENTATION",
    "SEMI_PRIMARY", "CORPUS", "LIMITATION", "CONFOUNDER", "UNLOCKS",
    "DESIGN_FREEDOM", "NOT_IMPLEMENTABLE", "READ_ANALYSIS",
    "WRITE_EXECUTION", "RUNTIME", "GPU", "INTACTA", "NO", "YES",
    "INTACT", "NONE", "MODIFICATIONS", "0", "1", "2", "MIXED", "HYBRID",
    "AND", "OR", "ENMENDADO", "CORRECTED_BY", "CONTINUES", "COMPLEMENTS",
    "RESOLVES", "STRENGTHENS", "CLARIFIES", "TRACK", "STATIC",
    "CLASSIFICATION", "WORK_CLASS", "ADJUDICA", "RECTIFIES", "HERRAMIENTA",
    "CORPUS_EXTERNAL", "READ_ONLY", "EVIDENCE", "RUN", "NOT_RUN",
}


def build_index():
    """{ruta_absoluta: lineas} para resolver citas sin releer el disco cada vez."""
    idx = {}
    for root in CORPUS_ROOTS:
        if not os.path.isdir(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            for f in files:
                if f.endswith((".c", ".h")):
                    p = os.path.join(dirpath, f)
                    try:
                        idx[p] = open(p, errors="replace").read().split("\n")
                    except OSError:
                        pass
    return idx


def resolve(name, idx):
    """Busca un fichero por nombre de referencia, en cualquier subarbol."""
    if os.path.isabs(name) and os.path.exists(name):
        return name
    base = os.path.basename(name)
    hits = [p for p in idx if os.path.basename(p) == base]
    if len(hits) == 1:
        return hits[0]
    return None


def quoted_spans(lines):
    """Devuelve, por linea, si el texto es CITADO y no redigido por mi.

    Es la distincion que hace falta para que el linter no me castigue por
    transcribir codigo ajeno. En 027 y 031 transcribi comentarios del driver
    que contienen literalmente "TODO" y "XXX": eso es EVIDENCIA, no un
    marcador mio sin resolver, y marcarlos como error habria督促ado a
    "arreglarlos" -- es decir, a manipular la cita.

    Tres formas de citar que cuentan:
      * bloque cercado con ```
      * fragmento entre acentos graves en la misma linea
    """
    out = []
    fence = False
    for l in lines:
        fenced = fence
        if l.lstrip().startswith("```"):
            fence = not fence
        out.append((fenced, l.count("`") >= 2))
    return out


def inline_spans(linea):
    """Rangos [ini, fin) de los tramos de acentos graves EN LINEA.

    Sirve para separar dos cosas que antes de esto iban juntas:

      * CJK DENTRO de un tramo -> es material citado. En este proyecto lo citado
        es codigo C y texto del kernel, y la excepcion real son los documentos
        que CITAN la corrupcion como evidencia (117, 189).
      * CJK FUERA de un tramo, en una linea que ademas lleva tramos -> es
        corrupcion mia. Esto es lo que antes se escapaba, porque bastaba con que
        la linea tuviera 2 acentos graves para degradarlo todo a "info".

    La regla es simetrica: cita y corrupcion se distinguen por la POSICION del
    ideograma, no por la mera presencia de acentos graves en la linea.
    """
    out = []
    i = linea.find("`")
    while i != -1:
        j = linea.find("`", i + 1)
        if j == -1:
            break
        out.append((i, j))
        i = linea.find("`", j + 1)
    return out


def lint(path, idx, strict=False):
    errs, warns, infos = [], [], []
    try:
        text = open(path, errors="replace").read()
    except OSError as e:
        return [f"no se pudo abrir: {e}"], [], []
    lines = text.split("\n")
    quoted = quoted_spans(lines)
    n_quoted = sum(1 for f, b in quoted if f or b)
    if n_quoted:
        infos.append(f"{n_quoted} lineas son material citado, no se auditan")

    # ---- 1. intrusiones de otro idioma --------------------------------
    for i, l in enumerate(lines, 1):
        fenced = quoted[i - 1][0]
        is_quoted = fenced or quoted[i - 1][1]
        spans = inline_spans(l)
        for m in CJK.finditer(l):
            ch = m.group(0)
            dentro = any(a <= m.start() < b for a, b in spans)
            msg = (f"L{i}: fragmento de otro idioma {ch!r} "
                   f"(U+{ord(ch):04X})")
            # BUG QUE ESTE LINTER TENIA, Y QUE DEJABA SU CONTROL SIN EFECTO:
            # `is_quoted` vale True para CUALQUIER linea con 2 o mas acentes
            # graves, y los hallazgos usan acentes graves en casi todas las
            # frases que mencionan un simbolo. Al degradar el CJK a "info"
            # cuando is_quoted, el chequeo quedaba DESACTIVADO en practicamente
            # toda la prosa util. Comprobado: dos ideogramas CJK en una linea con
            # 8 acentos graves daban "errores: 0".
            #
            # Regla que se aplica ahora: un bloque cercado SI puede citar material
            # ajeno, y ahi el CJK se degrada. Un fragmento EN LINEA NUNCA
            # excuse un ideograma: lo que se cita aqui es codigo C y texto del
            # kernel, y ninguno de los dos contiene CJK.
            if fenced or dentro:
                infos.append(msg + "  [citado: no es redaccion propia]")
            elif str(ch) in FULLWIDTH_PUNCT:
                warns.append(msg + "  [punctuacion de ancho completo]")
            else:
                errs.append(msg)
        if is_quoted:
            continue
        for pat, why in KNOWN_INTRUSIONS:
            if re.search(pat, l):
                errs.append(f"L{i}: intrusion lexical -- {why}  «{l.strip()[:60]}»")

    # ---- 2. marcadores de trabajo -------------------------------------
    for i, l in enumerate(lines, 1):
        if quoted[i - 1][0] or quoted[i - 1][1]:
            continue
        if PLACEHOLDERS.search(l):
            errs.append(f"L{i}: marcador de trabajo sin resolver -- {l.strip()[:70]}")
        elif PENDIENTE.search(l) and l.strip().startswith("#"):
            errs.append(f"L{i}: 'PENDIENTE' como titulo -- {l.strip()[:70]}")

    # ---- 3. cabecera ---------------------------------------------------
    head = "\n".join(lines[:40])
    missing = [f for f in REQUIRED_FIELDS if f not in head]
    if missing:
        (errs if strict else warns).append(
            f"cabecera: faltan {len(missing)} campos de clasificacion: "
            f"{', '.join(missing)}"
            + ("" if strict else "  [aviso: otras sesiones usan otro esquema]"))

    # ---- 4. citas verificables ----------------------------------------
    cited = 0
    for i, l in enumerate(lines, 1):
        if l.startswith("```"):
            continue
        for m in CITE.finditer(l):
            fname, a, b = m.group(1), int(m.group(2)), m.group(3)
            cited += 1
            real = resolve(fname, idx)
            if real is None:
                warns.append(
                    f"L{i}: cita a {fname}:{a}"
                    f"{'-' + b if b else ''}, no se resuelve: el nombre esta "
                    f"abreviado o el fichero no esta en el corpus. "
                    f"Una cita que no se resuelve no es verificable.")
                continue
            n = len(idx[real])
            hi = int(b) if b else a
            if hi > n or a < 1:
                errs.append(f"L{i}: cita {fname}:{a}"
                            f"{'-' + b if b else ''} fuera de rango "
                            f"(el fichero tiene {n} lineas)")
    # ---- 5. contradiccion numerica interna ----------------------------
    # Busca la misma clave con dos valores distintos en el mismo documento.
    # Formato: "| clave | 10 |" y tambien "clave = 10" / "clave = 22".
    pairs = {}
    for m in re.finditer(r"\|\s*`?([A-Za-z_][A-Za-z0-9_\.]*)`?\s*\|\s*"
                         r"`?(-?\d+(?:\.\d+)?)`?\s*\|", text):
        pairs.setdefault(m.group(1), set()).add(m.group(2))
    for m in re.finditer(r"`([A-Za-z_][A-Za-z0-9_\.]*)`\s*=\s*(-?\d+(?:\.\d+)?)",
                         text):
        pairs.setdefault(m.group(1), set()).add(m.group(2))
    for k, vs in pairs.items():
        if len(vs) > 1:
            warns.append(f"posible contradiccion numerica interna: "
                         f"`{k}` aparece con valores {sorted(vs)}")

    infos.append(f"{cited} citas verificadas contra el corpus")
    return errs, warns, infos


# El caso de "??" se construye por concatenacion a proposito: el literal
# "\u00bf\u00bf\u00bf" se pasa por shell y llega como signos de interrogacion
# invertidos, que es justo el caso que no debe disparar. Un caso de prueba
# corrupto es peor que no tener caso de prueba.
SELFTEST = [
    # (linea, debe_disparar_placeholder)
    ("todo el ASIC emite PACKET3_NOP", False),
    ("para todo lo que importa", False),
    ("Todo nivel esta medido", False),
    ("TODO: falta medir esto", True),
    (chr(63) * 3 + " cual es", True),
    ("FIXME acortar", True),
]


def selftest():
    """El linter se prueba a si mismo ANTES de usarse.

    Sin esto, la regla de marcadores -- que fallaba con "todo" -- habria
    llegado a todos los documentos sin que nadie se enterara. Un linter que no
    se autoinprueba es una afirmacion sin comprobar.
    """
    fails = []
    for line, should in SELFTEST:
        got = bool(PLACEHOLDERS.search(line))
        if got != should:
            fails.append(f"placeholder: {line!r} -> {got}, esperado {should}")
    # intrusion CJK
    if not CJK.search("el campo \u4e2d"):
        fails.append("CJK: no detecta un ideograma")
    if CJK.search("el campo de bytes"):
        fails.append("CJK: falso positivo en castellano")
    # CJK EN UNA LINEA CON ESPANES EN LINEA. Este es el agujero que hacia el
    # chequeo INEFECTIVO: quoted_spans marca como "citado" cualquier linea con
    # 2+ acentos graves, y los hallazgos los usan en casi todas las frases que
    # mencionan un simbolo, asi que el CJK se degradaba a info.
    #
    # El caso de arriba ("el campo \u4e2d") NO lo cubria, porque no lleva
    # acentes graves: probaba el REGEX, no el ENSAMBLAJE. Es la misma debilidad
    # que en ipver_zero e ip_surface: el componente correcto no valida el
    # montaje, y por eso el defecto pasa.
    _fd, _ruta = tempfile.mkstemp(suffix=".md")
    with os.fdopen(_fd, "w", encoding="utf-8") as _fh:
        _fh.write("# t" + chr(10)
                  + "`190` destapo que `uvd_v6_3` y `191` "
                  + chr(0x6CC4) + chr(0x6F0F) + " aqui" + chr(10))
    try:
        _errs, _w, _i = lint(_ruta, {}, strict=False)
        if not any("otro idioma" in e for e in _errs):
            fails.append("CJK en linea con >=2 acentos graves: se degrado a info "
                         "en vez de error -- el control esta sin efecto")
    finally:
        os.unlink(_ruta)
    # intrusiones lexicales conocidas
    for frag in ("fjCpu", "zyj", "annon"):
        if not any(re.search(p, frag) for p, _ in KNOWN_INTRUSIONS):
            fails.append(f"intrusion: no detecta {frag!r}")
    if fails:
        print("AUTOTEST FALLA:")
        for f in fails:
            print(f"   {f}")
        return 1
    print(f"autotest OK ({len(SELFTEST)} casos de marcador, "
          f"2 de CJK, intrusiones)")
    return 0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    strict = "--strict" in sys.argv
    if "--self" in sys.argv or not args:
        args = sorted(glob.glob(f"{ROOT}/06-INGENIERIA-INVERSA/findings/0[23]*.md"))
    if selftest() != 0:
        print("\nNo se ejecuta el lint: el linter no supera su autotest.")
        return 2
    print()

    idx = build_index()
    if not idx:
        sys.exit("no se pudo indexar el corpus: revisa CORPUS_ROOTS")

    tot_e = tot_w = 0
    for p in args:
        errs, warns, infos = lint(p, idx, strict)
        tot_e += len(errs)
        tot_w += len(warns)
        if not errs and not warns:
            print(f"OK    {os.path.basename(p)}")
            continue
        print(f"{'FALLA' if errs else 'avisa'} {os.path.basename(p)}")
        for e in errs:
            print(f"   ERROR  {e}")
        for w in warns:
            print(f"   aviso  {w}")
        for _ in infos:
            pass

    print()
    print(f"documentos: {len(args)}   errores: {tot_e}   avisos: {tot_w}")
    if strict and tot_w:
        print("modo estricto: los avisos cuentan como fallo")
        return 1
    return 1 if tot_e else 0


if __name__ == "__main__":
    sys.exit(main())