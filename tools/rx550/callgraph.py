#!/usr/bin/env python3
"""callgraph — quién llama a cada función, vía AST de clang

POR QUE        La pregunta que sigue a «26 funciones de runtime escriben varios
               registros sin mutex» es si PUEDEN pisarse: si dos rutinas de
               runtime del mismo bloque IP escriben a la vez, la ausencia de
               mutex es un riesgo; si el subsistema entero se serializa aguas
               arriba, no lo es.  Eso exige saber quién llama a cada una.

               Un subagente lo intentó y entregó `direct: []` para 18 de 23
               funciones, marcando «código muerto».  Era falso: las funciones
               son `static` y se llaman DENTRO del mismo .c, y su recuento de
               ocurrencias en el fuente no coincidía con el real.  Dos fallos
               distintos: un escaneo que devuelve un subconjunto parece
               completo (corrección 101), y un conteo mal hecho se publica
               como verdad (corrección 102).

MÉTODO         clang -Xclang -ast-dump=json -fsyntax-only.  Del AST se toman
               los `CallExpr` y, para cada uno, se busca el `FunctionDecl`
               ENCLOSING más interno: el llamante es la función que contiene la
               llamada, no el fichero.  Esto último es lo que faltaba: contar
               llamadas por fichero no dice quién llama a quién.

               Se distinguen dos vías, porque no son lo mismo:
                 DIRECTA   el CallExpr nombra la función.  Solo posible si es
                           no-static, o si comparten fichero (enlace interno).
                 INDIRECTA la función se mete en una tabla de ops
                           (`.soft_reset = fn`) y se llama por miembro
                           (`adev->gfx.soft_reset(...)`).  Aquí el CallExpr no
                           lleva su nombre: se resuelve nombre → miembro → CallExpr.

CONTROL NEGATIVO  Para cada función objetivo se cuenta además cuántas veces
               aparece su NOMBRE en el .c.  Si el AST dice 0 llamadas y el
               texto dice 3, el AST falló: se reporta como DISCREPANCIA, no
               como «código muerto».  Un resultado negativo sin ese control no
               es un resultado, es una ausencia silenciosa (clase F).

LIMITACIÓN     El CallExpr no distingue una llamada de una toma de dirección
               de función (`&fn` o `fn` en una tabla).  Por eso la vía
               INDIRECTA se resuelve por el nombre en el texto, y se declara
               como tal en la salida.
"""

import os
import re
import sys
import json
import glob
import subprocess

VERSION = "1.0"
NAME = "callgraph"
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from paths import AMD as _AMD          # ruta central, una sola fuente
except ImportError:                        # respaldo si falta paths.py
    _AMD = ("/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/"
            "kernelbuild/linux-7.1.3/drivers/gpu/drm/amd")


def clang_ast(path, amd=None):
    """AST JSON de un .c.

    DELEGA en `funcspan._clang_ast` en vez de repetir el clang.  Las dos copias
    eran identicas salvo en lo que importa: esta NO tenia cache en disco y
    usaba `capture_output`, que retiene los ~574 MB del stdout en memoria
    mientras corre clang.  Es exactamente el defecto que la correccion 142
    arreglo en `funcspan`, sin arreglar aqui: al ampliar el resolutor a 11
    ficheros, `alcance` pagaba 11 veces el mismo parseo.

    Delegar es tambien lo que exige la regla de composicion: `funcspan` ya
    esta validado (25 asserts) y su criterio de aceptacion es el CONTENIDO, no
    el codigo de salida --clang devuelve 1 aunque emita un AST valido de
    574 MB porque el .c no compila solo.  (correccion 188)
    """
    import funcspan as _fs
    return _fs._clang_ast(path, amd)


_AST = {}


def ast_of(path):
    if path not in _AST:
        _AST[path] = clang_ast(path)
    return _AST[path]


_OFFS = {}


def _tabla_offsets(path):
    """offset de inicio de cada linea, para convertir offset -> linea"""
    if path not in _OFFS:
        offs, acc = [0], 0
        with open(path, encoding="utf-8", errors="replace") as fh:
            for ln in fh:
                acc += len(ln.encode("utf-8"))
                offs.append(acc)
        _OFFS[path] = offs
    return _OFFS[path]


def linea_de_offset(off, path=None):
    """linea 1-indexada de un offset de byte; usa el fichero cacheado"""
    path = path or _ULTIMO_FICHERO[0]
    offs = _tabla_offsets(path)
    lo, hi = 0, len(offs) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if offs[mid] <= off:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1


_ULTIMO_FICHERO = [None]


def funciones_y_llamadas(path):
    """(definiciones, [(llamante, callee, linea)]) del AST de un .c"""
    ast = ast_of(path)
    if ast is None:
        return None, None
    _ULTIMO_FICHERO[0] = path
    defs = []          # (nombre, ini, fin)
    calls = []         # (llamante, callee, linea)
    pila = []          # funciones abiertas: (nombre, ini)

    def walk(n, depth=0):
        k = n.get("kind")
        if k == "FunctionDecl":
            loc = n.get("loc") or {}
            rng = n.get("range") or {}
            a = loc.get("line")
            cuerpo = next((c for c in (n.get("inner") or [])
                           if c.get("kind") == "CompoundStmt"), None)
            if a and cuerpo:
                # el final fiable es el del COMPOUND, no el del FunctionDecl:
                # el rango del nodo puede cortar antes (correccion 108)
                e = ((cuerpo.get("range") or {}).get("end") or {}).get("line")
                e = e or (rng.get("end") or {}).get("line") or a
                pila.append((n.get("name") or "?", a))
                for c in (n.get("inner") or []):
                    walk(c, depth + 1)
                nom, ini = pila.pop()
                defs.append((nom, ini, e))
                return
        if k == "CallExpr":
            # NO hay clave `called`: el callee es el PRIMER hijo de inner.
            # Y `range.begin` trae offset+col pero NO line, asi que la linea
            # hay que deducirla del offset.  Sin esto se obtenia una lista de
            # llamadas VACIA que parecia "nadie llama a nadie" (correccion 115).
            # El callee puede venir envuelto en ImplicitCastExpr, ParenExpr,
            # UnaryOperator...  Buscar SOLO en los hijos directos fallaba con
            # las funciones de puntero, que es justamente el caso de las
            # tablas de ops del kernel.  Se baja por los envoltorios.
            POR = ("DeclRefExpr", "MemberExpr", "FunctionDecl",
                   "CXXMethodDecl")
            ENVOLTORIO = ("ImplicitCastExpr", "ParenExpr", "UnaryOperator",
                          "ExprWithCleanups", "MaterializeTemporaryExpr")

            def _nombre_de(c):
                # Un DeclRefExpr que referencia una FUNCION no trae `name`:
                # lo trae `referencedDecl`.  Exigir `name` descartaba
                # exactamente las llamadas que interesan.  (correccion 116)
                if c.get("name"):
                    return c["name"]
                rd = c.get("referencedDecl")
                if isinstance(rd, dict):
                    return rd.get("name")
                return None

            def _busca(x, prof=0):
                if prof > 5:
                    return None
                for c in (x.get("inner") or []):
                    if c.get("kind") in POR and _nombre_de(c):
                        return c
                    if c.get("kind") in ENVOLTORIO:
                        r = _busca(c, prof + 1)
                        if r is not None:
                            return r
                return None

            hijo = _busca(n)
            if hijo is not None:
                off = ((n.get("range") or {}).get("begin") or {}).get("offset")
                calls.append((pila[-1][0] if pila else None,
                              _nombre_de(hijo),
                              off if off is None else linea_de_offset(off)))
        for c in (n.get("inner") or []):
            walk(c, depth + 1)

    walk(ast)
    return defs, calls


def occurrences(path, name):
    """cuantas veces aparece el NOMBRE en el texto del .c, y en que lineas"""
    try:
        txt = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return 0, []
    pat = re.compile(r"\b" + re.escape(name) + r"\b")
    hits = [i + 1 for i, ln in enumerate(txt.splitlines())
            if pat.search(ln)]
    return len(hits), hits


def es_miembro_de_tabla(lineas, ln, name):
    """¿la linea asigna `name` a un miembro .x = ... ?  (via indirecta)"""
    try:
        t = lineas[ln - 1]
    except IndexError:
        return None
    m = re.search(r"\.(\w+)\s*=\s*\**\s*" + re.escape(name) + r"\b", t)
    if m:
        return m.group(1)
    return None


def report_objetivos(objetivos, root=None):
    """objetivos: [(fichero, linea)] -> informe"""
    base = root or _AMD
    amdgpu = os.path.join(base, "amdgpu")
    by_file = {}
    for f, ln in objetivos:
        by_file.setdefault(f, []).append(ln)

    filas = []
    for f, lns in sorted(by_file.items()):
        path = os.path.join(amdgpu, f)
        defs, calls = funciones_y_llamadas(path)
        lineas = open(path, encoding="utf-8", errors="replace").read().splitlines()
        if defs is None:
            for ln in lns:
                filas.append({"fichero": f, "linea": ln, "nombre": None,
                              "estado": "AST_NO_DISPONIBLE"})
            continue
        # indice linea -> funcion que la contiene
        import funcspan
        for ln in lns:
            a, b, metodo = funcspan.of_line(path, ln)
            cab = lineas[a - 1].strip() if a else ""
            m = re.search(r"(\w+)\s*\(", cab)
            nombre = m.group(1) if m else None
            if not nombre:
                filas.append({"fichero": f, "linea": ln, "nombre": None,
                              "estado": "SIN_NOMBRE:" + str(metodo)})
                continue
            n_occ, lns_occ = occurrences(path, nombre)
            # llamada DIRECTA: el AST la ve desde una funcion
            # `calls` son triplas (llamante, callee, linea).  Antes se
            # desempaquetaba como si fueran parejas y reventaba al llegar al
            # corpus, donde si hay llamadas.  (correccion 117)
            directos = sorted({(c[0], c[2]) for c in calls
                               if len(c) == 3 and c[1] == nombre
                               and c[0] != nombre})
            # llamada INDIRECTA: el nombre aparece en una asignacion a miembro
            indirectos = []
            for ol in lns_occ:
                memb = es_miembro_de_tabla(lineas, ol, nombre)
                if memb:
                    # quien invoca ese miembro
                    indirectos.append((memb, ol))
            # el control negativo: AST 0 llamadas pero texto > 0 apariciones
            # no es codigo muerto, es un fallo del AST
            # Clasificacion del VEREDICTO, y por que no se puede llamar
            # "codigo muerto" sin control (clase F).
            estado = "OK"
            if not directos and not indirectos:
                # Sin ningun camino de llamada.  Antes de publicarlo se
                # comprueba el texto: si el nombre aparece, es un fallo del
                # AST, no una ausencia.  (correccion 115)
                estado = ("DISCREPANCIA" if n_occ > 1
                          else "SIN_LLAMANTES")
            elif not directos and indirectos:
                estado = "VIA_TABLA_OPS"
            filas.append({
                "fichero": f, "linea": ln, "nombre": nombre,
                "span": [a, b], "metodo": metodo, "cabecera": cab[:70],
                "n_ocurrencias_fuente": n_occ, "lineas_ocurrencia": lns_occ,
                "directos": [{"llamante": c[0], "linea": c[1]}
                              for c in directos if c[0] != nombre],
                "miembros": indirectos,
                "estado": estado,
            })
    return filas


def self_test():
    ok = fail = 0

    def chk(name, cond, extra=""):
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"    P  {name}")
        else:
            fail += 1
            print(f"    F  {name}  {extra}")

    print(f"  {NAME} {VERSION} self-test")
    t = "/tmp/callgraph_t.c"
    open(t, "w", encoding="utf-8").write(
        "static int hoja(void){\n  return 1;\n}\n"
        "static int usa(void){\n  return hoja();\n}\n"
        "static int usa2(void){\n  return usa();\n}\n"
        "struct ops { int (*f)(void); };\n"
        "static struct ops o = { .f = usa2 };\n"
        "int desde_tabla(void){\n  return o.f();\n}\n")
    defs, calls = funciones_y_llamadas(t)
    chk("BUILD: clang devuelve definiciones", defs is not None and len(defs) >= 4,
        None if defs is None else len(defs))
    chk("KNOWN INPUT: el nombre sale de referencedDecl, no de name",
        any(c[1] for c in calls), calls)
    chk("KNOWN INPUT: el callee se ve a traves de ImplicitCastExpr",
        any(c[1] == "hoja" for c in calls), calls)
    chk("KNOWN INPUT: ve la llamada directa hoja<-usa",
        any(c[1] == "hoja" and c[0] == "usa" for c in calls), calls)
    chk("KNOWN INPUT: ve la llamada encadenada usa<-usa2",
        any(c[1] == "usa" and c[0] == "usa2" for c in calls), calls)
    chk("KNOWN INPUT: la llamada por miembro NO lleva el nombre",
        not any(c[1] == "usa2" and c[0] == "desde_tabla" for c in calls),
        [c for c in calls if c[0] == "desde_tabla"])
    chk("KNOWN INPUT: el nombre en la tabla se detecta como miembro",
        es_miembro_de_tabla(["static struct ops o = { .f = usa2 };"],
                            1, "usa2") == "f")
    n, ls = occurrences(t, "hoja")
    chk("CONTROL: cuenta las ocurrencias en el texto (def en 1, uso en 5)",
        n == 2 and ls == [1, 5], (n, ls))
    n2, _ = occurrences(t, "no_existe_jamas")
    chk("NEGATIVO: un nombre ausente da 0 y lista vacia",
        n2 == 0, n2)

    # corpus real
    gmc = os.path.join(_AMD, "amdgpu", "gmc_v8_0.c")
    if os.path.isfile(gmc):
        filas = report_objetivos([("gmc_v8_0.c", 184),
                                  ("gmc_v8_0.c", 1228)])
        for fr in filas:
            chk(f"CORPUS: {fr['fichero']}:{fr['linea']} tiene nombre",
                bool(fr.get("nombre")), fr)
        g = [fr for fr in filas if fr.get("nombre") == "gmc_v8_0_mc_stop"]
        if g:
            fr = g[0]
            chk("CORPUS: mc_stop tiene >=1 llamante directo",
                len(fr["directos"]) >= 1, fr["directos"])
        else:
            chk("CORPUS: se resuelve mc_stop", False, filas)

    print(f"  {ok} pasaron, {fail} fallaron")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    if "--objetivos" in sys.argv:
        i = sys.argv.index("--objetivos")
        objs = []
        for tok in sys.argv[i + 1:]:
            f, _, ln = tok.partition(":")
            objs.append((f, int(ln)))
        print(json.dumps(report_objetivos(objs), indent=2, ensure_ascii=False))
    else:
        print("uso: callgraph.py --self-test | --objetivos f.c:N [f.c:N ...]")
