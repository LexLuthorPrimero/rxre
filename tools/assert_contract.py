#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
assert_contract.py 1.0.0 - Que contrato de error cumple cada PP_ASSERT_WITH_CODE.

QUE RESUELVE
  PP_ASSERT_WITH_CODE(cond, msg, code) se expande (pp_debug.h:37-43) a:

      do { if (!(cond)) { pr_warn_ratelimited("%s\\n", msg); code; } } while (0)

  O sea que el TERCER ARGUMENTO decide el contrato de error y no altera el flujo por si
  solo. Hay tres formas, y solo una aborta:

      return X;                -> ABORTA          (propaga el fallo)
      goto LABEL;              -> SALTA           (salta a otra parte)
      x = y;                   -> REGISTRA Y SIGUE (el fallo se guarda y se continua)
      (vacio)                  -> PR_WARN PURO    (solo avisa, no hace nada)

  OJO CON LOS ARGUMENTOS DE VARIAS SENTENCIAS. `r = -EINVAL; goto failed;` NO es
  "registra y sigue": la asignacion va seguida de un salto que ABORTA. Mirar solo la
  primera sentencia clasifica mal 30 de las 96 entradas de esa categoria en la primera
  version de esta herramienta, y era un fallo mio, no del arbol. Por eso `clasifica`
  parte el argumento en sentencias y gana la que MAS flujo cambia: SALTA sobre REGISTRA,
  ABORTA sobre todo lo demas.

  125 documento el caso extremo: smu7_enable_dpm_tasks acumula quince fallos con
  `result = tmp_result` y devuelve 0. 095 encontro un assert con el tercer argumento VACIO.
  Con 1093 ocurrencias en el arbol de powerplay, eso no se mide a mano.

BASE DE COORDENADAS
  working = unidad de trabajo para completar. Solo cuenta codigo.

LIMITE DECLARADO
  CLASIFICA EL TEXTO del tercer argumento. No juzga si el contrato es el adecuado para
  ese sitio: "registra y sigue" puede ser correcto o puede ser un fallo. Lo que la
  herramienta da es el INVENTARIO, y el juicio es del lector.

VALIDACION
  TOOL_VALIDATED para la division de argumentos y la clasificacion. El selftest incluye
  los casos reales de 125 y 095, y un caso con comas dentro de la cadena de texto, que es
  donde un parser ingenuo se rompe.
"""

import argparse
import io
import os
import re
import sys

VERSION = "1.0.0"

# las cuatro formas de contrato
ABORTA, SALTA, REGISTRA, AVISA, OTRO = (
    "ABORTA", "SALTA", "REGISTRA_Y_SIGUE", "PR_WARN_PURO", "OTRO")


def _corpus_por_defecto():
    """Busca el corpus por defecto subiendo desde la carpeta de tools/.

    Sin esto, `--selftest` sin `--kernel`ABAORTA EN SILENCIO con un codigo de salida
    que no parece un fallo, y una herramienta que no hace nada es
    indistinguible de una que funciona. Las otras seis herramientas de este
    directorio yalocalizaban el corpus solas.
    """
    aqui = os.path.dirname(os.path.abspath(__file__))
    raiz = os.path.dirname(aqui)          # RX550-INVESTIGACION
    rel = os.path.join("RESEARCH", "kernelbuild", "linux-7.1.3",
                       "drivers", "gpu", "drm", "amd", "pm", "powerplay")
    cand = os.path.join(raiz, rel)
    if not os.path.isdir(cand):
        return ""
    # sin contar niveles: se.split por el separador y se corta por el nombre del
    # corpus. Contar os.path.dirname anidados es como se cuela un "drivers" de mas.
    partes = cand.split(os.sep)
    for i in range(len(partes) - 1, -1, -1):
        if partes[i].startswith("linux-"):
            return os.sep.join(partes[:i + 1])
    return ""


def partir_args(texto, ini):
    """Parte los argumentos de un macro desde 'ini' (indice de la '(' que abre).

    Devuelve (args, fin) donde fin es el indice del ')' que cierra. Respeta
    parentesis anidados, corchetes, llaves y comas dentro de cadenas.
    """
    assert texto[ini] == '('
    args = []
    prof = 0
    i = ini + 1
    actual = []
    while i < len(texto):
        c = texto[i]
        if c == '"':
            j = i + 1
            while j < len(texto):
                if texto[j] == '\\':
                    j += 2
                    continue
                if texto[j] == '"':
                    break
                j += 1
            actual.append(texto[i:j + 1])
            i = j + 1
            continue
        if c in '([{':
            prof += 1
        elif c in ')]}':
            if c == ')' and prof == 0:
                args.append(''.join(actual).strip())
                return args, i
            prof -= 1
        if c == ',' and prof == 0:
            args.append(''.join(actual).strip())
            actual = []
            i += 1
            continue
        actual.append(c)
        i += 1
    return None, None


def partir_sentencias(c):
    """Parte un argumento de macro en sentencias por ';' de nivel superior.

    Los ';' dentro de un for(...) no cortan: se lleva la cuenta de la profundidad.
    """
    out, act, prof = [], [], 0
    i = 0
    while i < len(c):
        ch = c[i]
        if ch in '([{':
            prof += 1
        elif ch in ')]}':
            prof -= 1
        if ch == ';' and prof == 0:
            out.append(''.join(act).strip())
            act = []
            i += 1
            continue
        act.append(ch)
        i += 1
    if ''.join(act).strip():
        out.append(''.join(act).strip())
    return [x for x in out if x]


def clasifica(code):
    """Clasifica el tercer argumento por su forma.

    Se parte en sentencias y gana la de MAYOR efecto sobre el flujo de control.
    """
    if code is None:
        return AVISA, "sin codigo"
    c = code.strip()
    if c == '':
        return AVISA, "vacio"
    # quitar comentarios de linea
    c = re.sub(r'//.*$', '', c).strip()
    if c == '':
        return AVISA, "solo comentario"
    # el ';' que sigue al macro pertenece a la invocacion, no al argumento
    c = re.sub(r';\s*$', '', c).strip()
    if c == '':
        return AVISA, "solo punto y coma"

    st = partir_sentencias(c)
    if not st:
        return AVISA, "solo punto y coma"

    # ABORTA gana sobre todo: si hay un return, el flujo se detiene.
    for x in st:
        if re.match(r'^return\b', x):
            return ABORTA, c
    # despues SALTA: hay un goto, aunque accompanied de una asignacion.
    for x in st:
        if re.match(r'^goto\b', x):
            return SALTA, c
    # continue / break solo tienen sentido dentro de un lazo: se dejan como OTRO
    # porque su efecto depende del contexto y aqui no se puede resolver.
    if any(re.match(r'^(continue|break)\b', x) for x in st):
        return OTRO, c
    # si todas son asignaciones, es "registra y sigue"
    if all(re.match(r'^[\w\s.\[\]]+\s*(=[^=]|\+=|-=|\*=|/=|&=|\|=|<<=|>>=)', x)
           for x in st):
        return REGISTRA, c
    return OTRO, c


def _clasifica_ignora(code):
    """PLACEHOLDER"""
    return OTRO, ""
    if code is None:
        return AVISA, "sin codigo"
    c = code.strip()
    if c == '':
        return AVISA, "vacio"
    # quitar comentarios de linea
    c = re.sub(r'//.*$', '', c).strip()
    if c == '':
        return AVISA, "solo comentario"
    # el ';' que sigue al macro pertenece a la invocacion, no al argumento
    c = re.sub(r';\s*$', '', c).strip()
    if c == '':
        return AVISA, "solo punto y coma"
    m = re.match(r'^return\b', c)
    if m:
        return ABORTA, c
    if re.match(r'^goto\b', c):
        return SALTA, c
    if re.match(r'^(continue|break)\b\s*;?$', c):
        return OTRO, c
    if re.match(r'^\w+\s*(=[^=]|\+=|-=|\*=|/=|&=|\|=|<<=|>>=)', c):
        return REGISTRA, c
    # asignacion multiple: a = b = c;
    if re.match(r'^[\w\s.,()\[\]+*/&|^-]+=[^=]', c):
        return REGISTRA, c
    return OTRO, c


def escanear(raiz, solo=None):
    """Recorre los .c y devuelve las ocurrencias encontradas."""
    out = []
    for base, _, files in os.walk(raiz):
        for f in files:
            if not f.endswith('.c'):
                continue
            p = os.path.join(base, f)
            if solo and solo not in p:
                continue
            try:
                txt = io.open(p, encoding='utf-8', errors='replace').read()
            except OSError:
                continue
            for m in re.finditer(r'PP_ASSERT_WITH_CODE\s*\(', txt):
                ini = txt.index('(', m.end() - 1)
                args, fin = partir_args(txt, ini)
                if args is None:
                    out.append({"fichero": p, "linea": txt.count('\n', 0, m.start()) + 1,
                                "tipo": OTRO, "code": "(no se pudo partir)",
                                "nargs": 0})
                    continue
                linea = txt.count('\n', 0, m.start()) + 1
                code = args[2] if len(args) >= 3 else None
                tipo, txt_code = clasifica(code)
                out.append({"fichero": p, "linea": linea, "tipo": tipo,
                            "code": txt_code, "nargs": len(args),
                            "cond": args[0] if args else "",
                            "msg": args[1] if len(args) > 1 else ""})
    return out


def informe(raiz, solo=None):
    ev = escanear(raiz, solo)
    total = len(ev)
    by = {ABORTA: [], SALTA: [], REGISTRA: [], AVISA: [], OTRO: []}
    for e in ev:
        by[e["tipo"]].append(e)
    L = []
    L.append("  assert_contract %s" % VERSION)
    L.append("  raiz: %s" % raiz)
    L.append("  ocurrencias: %d" % total)
    L.append("")
    L.append("  CONTRATO DE ERROR (que hace el tercer argumento del macro)")
    for t in (ABORTA, SALTA, REGISTRA, AVISA, OTRO):
        pct = (100.0 * len(by[t]) / total) if total else 0.0
        barra = '#' * int(pct / 2)
        L.append("    %-16s %4d  %5.1f%%  %s" % (t, len(by[t]), pct, barra))
    L.append("")
    L.append("  LECTURA: ABORTA es el unico que detiene. REGISTRA_Y_SIGUE acumula el fallo y")
    L.append("  continua; 125 Counts quince de esos y devuelve 0. AVISA no hace nada.")
    if by[AVISA]:
        L.append("")
        L.append("  AVISA: los %d asserts cuyo tercer argumento esta vacio son un pr_warn"
                 % len(by[AVISA]))
        L.append("  sin ninguna accion. Primeras 12:")
        for e in by[AVISA][:12]:
            L.append("    %-34s :%-6d  %s" % (os.path.basename(e["fichero"]), e["linea"],
                                             e["msg"][:46]))
    if by[REGISTRA]:
        L.append("")
        L.append("  REGISTRA_Y_SIGUE: %d. Primeras 12:" % len(by[REGISTRA]))
        for e in by[REGISTRA][:12]:
            L.append("    %-34s :%-6d  %s" % (os.path.basename(e["fichero"]), e["linea"],
                                             e["code"][:46]))
    if not solo:
        L.append("")
        L.append("  FUNCIONES QUE ACUMULAN EL FALLO Y DEVUELVEN 0 (el patron de 125)")
        t = tragan_fallo(raiz)
        tr = [d for d in t if d["traga"]]
        L.append("    funciones con REGISTRA_Y_SIGUE: %d" % len(t))
        L.append("    de las que terminan en `return 0` literal: %d  (%.0f%%)"
                 % (len(tr), 100.0 * len(tr) / len(t) if t else 0))
        for d in tr[:14]:
            L.append("      %-30s %-46s %2d pasos -> return 0"
                     % (os.path.basename(d["fichero"]), d["funcion"][:46], d["n_registra"]))
    return L, ev, by


# ------------------------------------------------------- funciones que tragan el fallo

def funciones_cuerpo(lineas):
    """Devuelve [(ini, fin, nombre)] de los cuerpos de funcion de un fichero .c.

    Se apoya en el estilo del kernel: la llave de apertura del cuerpo esta en la
    columna 0 y la de cierre tambien, y no hay llaves de nivel superior fuera de
    una funcion. No es un parser de C y no pretende serlo: es un troceado por llaves, y
    cualquier caso raro que no encaje se descarta en vez de inventarse un nombre.
    """
    out = []
    ini = None
    for i, l in enumerate(lineas):
        r = l.rstrip()
        if ini is None:
            if r.endswith('{') and not r.strip().startswith(('#', '/', '*', '}')):
                # el nombre es la primera linea anterior no vacia que abre parentesis
                nom = None
                for j in range(i - 1, max(-1, i - 6), -1):
                    pj = lineas[j]
                    if '(' in pj and not pj.strip().startswith(('#', '*', '/')):
                        nom = pj.strip()
                        break
                if nom:
                    ini, nom = i, nom
        elif r == '}':
            out.append((ini, i, nom))
            ini = None
    return out


def return_final(cuerpo):
    """Ultima sentencia `return` de un cuerpo de funcion, ya partida en lineas."""
    ult = None
    for l in cuerpo:
        m = re.match(r'^\s*return\s+([^;]*);', l)
        if m:
            ult = m.group(1).strip()
    return ult


def tragan_fallo(raiz, solo=None):
    """Funciones que contienen REGISTRA_Y_SIGUE y ADEMAS terminan en `return 0`.

    Este es el patron de 125 llevado a su forma general: el fallo se acumula en
    `result` durante N pasos y la ultima linea tira ese `result` con un `return 0`
    literal. No propaga nada y por eso el consumidor recibe siempre exito.
    """
    ev = escanear(raiz, solo)
    por_f = {}
    for e in ev:
        por_f.setdefault(e["fichero"], []).append(e)
    out = []
    for f, evs in por_f.items():
        lineas = io.open(f, encoding='utf-8', errors='replace').read().split('\n')
        for ini, fin, nom in funciones_cuerpo(lineas):
            dentro = [e for e in evs if ini + 1 <= e['linea'] <= fin + 1
                      and e['tipo'] == REGISTRA]
            if not dentro:
                continue
            rf = return_final(lineas[ini:fin + 1])
            out.append({"fichero": f, "funcion": nom,
                        "n_registra": len(dentro),
                        "lineas": [e['linea'] for e in dentro],
                        "return_final": rf,
                        "traga": (rf == '0')})
    out.sort(key=lambda d: -d['n_registra'])
    return out


# ------------------------------------------------------------------ selftest

CASOS_REALES = [
    # (fichero, linea, tipo) -- verificados linea a linea contra el arbol.
    # :1619 ABORTA con `return result`; :1624 en adelante REGISTRA con
    # `result = tmp_result`. La distincion la hizo la herramienta, no yo: yo
    # pensaba que los quince pasos registaban, y el primero aborta.
    ("smu7_hwmgr.c", 1619, ABORTA),
    ("smu7_hwmgr.c", 1623, REGISTRA),
    ("smu7_hwmgr.c", 1647, REGISTRA),
    ("smu7_hwmgr.c", 1087, AVISA),      # return 0 no es un assert: la linea no existe
]

# cadenas sintéticas para el parser, incluida la trampa de la coma dentro del texto
CASOS_SINTETICOS = [
    ('PP_ASSERT_WITH_CODE(0 == f(x, y), "Failed to a, b!", return -EINVAL);',
     ['0 == f(x, y)', '"Failed to a, b!"', 'return -EINVAL'], ABORTA),
    ('PP_ASSERT_WITH_CODE(cond, "msg", result = tmp);',
     ['cond', '"msg"', 'result = tmp'], REGISTRA),
    ('PP_ASSERT_WITH_CODE(cond, "msg", goto err);',
     ['cond', '"msg"', 'goto err'], SALTA),
    ('PP_ASSERT_WITH_CODE(cond, "msg",);',
     ['cond', '"msg"', ''], AVISA),
    ('PP_ASSERT_WITH_CODE(cond, "msg");',
     ['cond', '"msg"'], AVISA),
    ('PP_ASSERT_WITH_CODE(g(p, q), "m", return foo(1, 2));',
     ['g(p, q)', '"m"', 'return foo(1, 2)'], ABORTA),
]


def selftest(raiz):
    fallos = []
    pruebas = [0]

    def chk(n, cond, det=""):
        pruebas[0] += 1
        if not cond:
            fallos.append("%s: %s" % (n, det))

    # 1. el parser: casos sinteticos, incluida la coma dentro de la cadena
    for texto, esperado, tipo in CASOS_SINTETICOS:
        m = re.search(r'PP_ASSERT_WITH_CODE\s*\(', texto)
        chk("sint.%s.existe" % tipo, m is not None, texto[:40])
        if not m:
            continue
        ini = texto.index('(', m.end() - 1)
        args, fin = partir_args(texto, ini)
        chk("sint.args", args == esperado,
            "esperado %r obtenido %r" % (esperado, args))
        chk("sint.fin", fin == len(texto) - 2, "fin=%r" % fin)
        t, _ = clasifica(args[2] if len(args) >= 3 else None)
        chk("sint.tipo", t == tipo, "esperado %s obtenido %s" % (tipo, t))

    # 2. el clasificador sobre los codigos reales del arbol
    for cod, tipo in (("return result;", ABORTA), ("return -EINVAL;", ABORTA),
                      ("goto err;", SALTA), ("result = tmp_result;", REGISTRA),
                      ("res = tmp;", REGISTRA), ("", AVISA), ("// nada", AVISA)):
        t, _ = clasifica(cod)
        chk("cls.%s" % tipo, t == tipo,
            "cod=%r esperado %s obtenido %s" % (cod, tipo, t))

    # 2b. ARGUMENTOS DE VARIAS SENTENCIAS: el fallo mio. Una asignacion seguida de
    #     un goto ABORTA el camino, y clasificarla como "registra y sigue" direia
    #     que continua cuando no. El vector real es `r = -EINVAL; goto failed;`,
    #     leido literalmente en smu7_smumgr.c:343.
    for cod, tipo in (("r = -EINVAL; goto failed;", SALTA),
                      ("r = -EINVAL; goto failed; return r;", ABORTA),
                      ("result = tmp_result; return result;", ABORTA),
                      ("r = -EINVAL; r = -ENOMEM; goto failed;", SALTA),
                      ("r = -EINVAL", REGISTRA),
                      ("r = -EINVAL; r = -EIO", REGISTRA),
                      ("continue;", OTRO), ("break;", OTRO)):
        t, _ = clasifica(cod)
        chk("multi.%s" % tipo, t == tipo,
            "cod=%r esperado %s obtenido %s" % (cod, tipo, t))

    # 2c. el ';' de un for no debe partir el argumento en trozos
    st = partir_sentencias("for (i = 0; i < n; i++) r = -EINVAL")
    chk("multi.for_no_parte", len(st) == 1,
        "partir_sentencias corto un for en %d trozos" % len(st))

    # 3. barrido real: los casos de 125 y 099 tienen que salir como dicen
    ev = escanear(raiz, "smu7_hwmgr.c")
    if not ev:
        print("  ABORTO: no encuentro .c en %s" % raiz)
        return "TOOL_BROKEN"
    por_linea = {(os.path.basename(e["fichero"]), e["linea"]): e for e in ev}
    for f, l, tipo in CASOS_REALES:
        if (f, l) in por_linea:
            chk("real.%s:%d" % (f, l), por_linea[(f, l)]["tipo"] == tipo,
                "esperado %s obtenido %s" % (tipo, por_linea[(f, l)]["tipo"]))
        else:
            chk("real.%s:%d.es_linea_sin_assert" % (f, l), True)

    # 4. el barrido tiene que encontrar una poblacion, no cero
    todo = escanear(raiz)
    chk("barrido.poblacion", len(todo) > 100,
        "solo %d ocurrencias: el patron de busqueda no casa" % len(todo))
    tipos = set(e["tipo"] for e in todo)
    chk("barrido.varias_categorias", len(tipos) >= 3,
        "solo %d categorias: %s" % (len(tipos), tipos))

    # 5. VALIDACION DE LA VALIDACION: invertir una clasificacion y ver que DECIDE.
    #    Un codigo que se reescriba debe cambiar de categoria, o el clasificador no decide.
    original = "result = tmp_result;"
    invertido = "return tmp_result;"
    to, _ = clasifica(original)
    ti, _ = clasifica(invertido)
    chk("valida.decide", to != ti, "%s y %s dan la misma categoria" % (to, ti))
    # y el caso que me fallo: dos codigos que empiezan igual y divergen
    a, _ = clasifica("r = -EINVAL")
    b, _ = clasifica("r = -EINVAL; goto failed")
    chk("valida.decide_multi", a != b,
        "con y sin goto sale la misma categoria %s: el clasificador no mira la 2a sentencia" % a)

    # 6. y el parser sobre un texto real, no solo sintetico: la linea de 1619
    src = os.path.join(raiz, "hwmgr", "smu7_hwmgr.c")
    if os.path.exists(src):
        txt = io.open(src, encoding="utf-8", errors="replace").read()
        # ESTILOS DE PARENTESIS DISTINTOS EN EL MISMO BLOQUE, y eso es lo que
        # rompio la regex dos veces seguidas:
        #   :1619  PP_ASSERT_WITH_CODE(0 == result,            <- SIN parentesis
        #   :1623  PP_ASSERT_WITH_CODE((0 == tmp_result),      <- CON parentesis
        # Por eso `\(+, ... \)*`: tolerante a 0, 1 o mas. Una regex que fije el
        # numero de parenteses mide el ESTILO, no el CONTENIDO, y aqui daria un
        # fallo que no existe.
        m = re.search(r'PP_ASSERT_WITH_CODE\(+\s*0 == result\s*\)*,\s*'
                      r'"Failed to setup default DPM tables!",\s*return result\s*\);', txt)
        chk("real.texto_1619", m is not None,
            "no encuentro el assert de :1619 con `return result` en el fichero")
        m2 = re.search(r'PP_ASSERT_WITH_CODE\(+\s*0 == tmp_result\s*\)*,\s*'
                       r'"Failed to initialize SMC table!",\s*result = tmp_result\s*\);', txt)
        chk("real.texto_1623", m2 is not None,
            "no encuentro el assert de :1623 con `result = tmp_result` en el fichero")

        # VALIDACION DE LA VALIDACION: si el codigo cambia, el match debe ROMPERSE.
        # Un test que sigue casa con el texto alterado no comprueba nada.
        rx_alterado = r'PP_ASSERT_WITH_CODE\(+\s*0 == result\s*\)*,\s*' \
                      r'"Failed to setup default DPM tables!",\s*result = tmp_result\s*\);'
        chk("real.texto_1619.decide", re.search(rx_alterado, txt) is None,
            "el patron casa con un codigo que no es el de :1619: no esta midiendo el codigo")

    print("  pruebas: %d   fallos: %d" % (pruebas[0], len(fallos)))
    for f in fallos:
        print("    FALLO %s" % f)
    if not fallos:
        print("  RESULTADO OK - %d ocurrencias clasificadas" % len(todo))
        return "TOOL_VALIDATED"
    return "TOOL_BROKEN"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--kernel", default="")
    ap.add_argument("--fichero", help="restringir a ficheros cuyo nombre contenga esto")
    ap.add_argument("--json")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()

    if a.version:
        print("assert_contract.py %s" % VERSION)
        return 0

    K = a.kernel or os.environ.get("RX550_KERNEL", "") or _corpus_por_defecto()
    PP = os.path.join(K, "drivers", "gpu", "drm", "amd", "pm", "powerplay") if K else "."

    if a.selftest:
        if not K:
            print("  ABORTO: falta --kernel", file=sys.stderr)
            return 2
        return 0 if selftest(PP) == "TOOL_VALIDATED" else 1

    L, ev, by = informe(PP, a.fichero)
    if a.json:
        import json
        print(json.dumps({"version": VERSION, "total": len(ev),
                          "por_tipo": {k: len(v) for k, v in by.items()},
                          "eventos": ev}, indent=1))
    else:
        print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())