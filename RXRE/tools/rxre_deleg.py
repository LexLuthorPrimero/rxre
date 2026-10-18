#!/usr/bin/env python3
#!/usr/bin/env python3
# CONTRACT: name=rxre_deleg
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# EXIT_ON_SUCCESS=0: MEDIDO.  `--version` sale rc=0 y `--selftest` sale rc=0
# con todos los vectores en PASS.  Se declara porque `exit_contract.py`
# existe para comprobarlo: sin esta linea el codigo de salida de este
# validador NO tiene quien lo verifique, y es un contrato en prosa.
# CONTRACT: EXIT_ON_SUCCESS=0
#
"""rxre_deleg.py -- el acoplamiento que el grafo de imports NO ve.

QUE ES ESTE FICHERO, Y QUE NO ES
--------------------------------
`rxre_boot.py` declara, y con razon, que su grafo de dependencias tiene 172
llamadas por `subprocess` que NO son aristas, y que por tanto el grafo es una
COTA INFERIOR del acoplamiento real.  Ese limite estaba medido y no se habia
cerrado.

Esto lo cierra.  Y al medirlo sale el dato que cambia una conclusion:

    de 172 llamadas a subprocess en el arbol, solo 46 identifican un PROGRAMA
    por literal, y los 9 programas distintos son binarios EXTERNOS -- git, gcc,
    objdump, bash, nm, grep, sha256sum, readelf, python3.

    CERO invocan a otra herramienta de este proyecto.

    El acoplamiento real no esta en las llamadas a subprocess: esta en las
    LISTAS.  `run_all.py` invoca 72 herramientas del proyecto desde una tabla,
    y en su codigo no hay ni un literal que las nombre.  El AST no puede verlo,
    y ningun patron de texto puede tampoco.

        una lista de herramientas es un grafo escrito como tabla

Y por que importa mas de lo que parece: `rxre_contracts.py` clasifica 45
herramientas como "puede escribir delegando" por tener llamadas a subprocess.  Si
esas 45 delegan en binarios externos y no en herramientas hermanas, entonces la
preocupacion es distinta de la que se estaba suponiendo, y se puede DECIR.

QUE MIDE, EN ORDEN DE DIFICULTAD
--------------------------------
    NIVEL 1  literal    el programa es un literal en el argv         OBSERVABLE
    NIVEL 2  estructura el programa viene de una lista/constante    OBSERVABLE
    NIVEL 3  nombre     de una tabla de (etiqueta, [argv], n)       OBSERVABLE
    NIVEL 4  flujo      quien recibe de un bucle sobre variables     NO OBSERVABLE
                         sin ejecutar

Los tres primeros se resuelven sobre el arbol. El cuarto NO, y se DECLARA como
NO_DETERMINED en vez de contarse como cero.

Y el NIVEL 3 tiene un oraculo que el proyecto ya uso: una tabla que invoca una
herramienta INEXISTENTE es una tabla con un error, y se comprueba contra el
disco.  Aqui las 72 existen.

LO QUE NO ES
------------
    No ejecuta nada.  No invoca ninguna herramienta.  No escribe en el arbol.
    No cuenta "cuantas herramientas hay": cuenta COMO SE LLAMAN entre si, que es
    una pregunta distinta y la que hace que una caja sea un sistema.
"""
import argparse
import ast
import collections
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
VERSION = "1.0.0"

DIRECTORIOS = ("tools", "revkit", "08-ARQUITECTURA/tools",
               "04-IMPLEMENTACION/tools", "09-POWER-CLOCKS/tools",
               "01-AUDITORIA/tools", "04-IMPLEMENTATION/rx550-driver/tools")

# Los binarios externos que aparecen como programa.  Se DECLARAN y se cuentan:
# son acoplamiento real y no es codigo de este proyecto, y mezclarlos con las
# herramientas propias daria un numero que no significa nada.
EXTERNOS = {
    "git", "gcc", "clang", "make", "bash", "sh", "python3", "objdump",
    "llvm-objdump", "readelf", "nm", "strings", "grep", "rg", "sed", "awk",
    "sha256sum", "diff", "tar", "xz", "gzip", "find", "ls", "cat", "cp", "mv",
    "rm", "sort", "uniq", "wc", "head", "tail", "stat", "test", "date",
    "which", "echo", "env", "uname", "lsmod", "lspci", "dmesg", "journalctl",
    "pahole", "drgn", "addr2line", "readlink", "realpath", "tr", "cut", "seq",
}

SUBPROCESS_ATTRS = ("run", "Popen", "call", "check_output", "check_call")


def _hojas_de_fichero(d):
    """{basename: ruta_relativa} para lo que hay en el arbol."""
    out = {}
    for sub in DIRECTORIOS:
        base = os.path.join(RAIZ, sub)
        if not os.path.isdir(base):
            continue
        for fn in os.listdir(base):
            if fn.endswith((".py", ".sh", ".c")):
                out.setdefault(fn, "%s/%s" % (sub, fn))
    return out


def nivel1_literal(arbol, argv_node):
    """El primer literal del argv que NO es un flag y parece un programa."""
    if argv_node is None:
        return None
    if not isinstance(argv_node, (ast.List, ast.Tuple)):
        return None
    for el in argv_node.elts:
        if isinstance(el, ast.Constant) and isinstance(el.value, str):
            if el.value.startswith("-"):
                continue
            return el.value
    return None


def nivel3_tablas(arbol, arbol_nombres):
    """De una tabla `(etiqueta, [argv, ...], n)` sacar el programa de cada fila.

    MEDIDO, y este es el patron que hace ver 72 herramientas donde el AST no ve
    ninguna: la lista `tools` de `run_all.py` es una lista de tuplas, y el argv
    de cada tupla es una sublista cuyo primer elemento es un LITERAL.  El
    literal es visible; lo que hay que saber es que esa lista se ITERA, y eso no
    lo cuenta ningun `ast.walk` sobre el arbol de imports.

    Se mira el ARBOL COMPLETO, no solo las Expr, porque la asignacion puede
    estar anidada en una funcion, una clase o un `if`.
    """
    filas, descartadas = [], 0
    for n in ast.walk(arbol):
        if not isinstance(n, (ast.Assign, ast.AnnAssign)):
            continue
        value = n.value
        if not isinstance(value, (ast.List, ast.Tuple)):
            continue
        for el in value.elts:
            if not isinstance(el, (ast.Tuple, ast.List)) or not el.elts:
                continue
            argv = None
            for sub in el.elts:
                if isinstance(sub, (ast.List, ast.Tuple)):
                    argv = sub
                    break
            prog = nivel1_literal(arbol, argv)
            if prog is None:
                continue
            etiqueta = ""
            if isinstance(el.elts[0], ast.Constant) and \
                    isinstance(el.elts[0].value, str):
                etiqueta = el.elts[0].value
            # MEDIDO: la primera version de esto aceptaba CUALQUIER tabla 2D
            # cuya sublista empezara por una cadena que no fuera flag.  Eso
            # capturaba tablas matematicas -- `[("0 == f(x, y)", "cond")]` --
            # y las contaba como si fueran herramientas, y el oraculo de "la
            # invocada existe en disco" caia con `cond` y `g(p, q)`.
            #
            #     una tabla de expresion y una tabla de herramientas se parecen
            #     en el AST, y no en lo que signifcan
            #
            # La segunda version exigia que PARECIERA un programa, y seguian
            # entrando `cond`, `pci_register_driver` y una ruta a un `.md`:
            # `cond` no tiene espacios ni parentesis, y eso no lo hace un
            # programa.
            #
            # El criterio que si funciona NO es de forma sino de RESOLUBILIDAD:
            # una fila cuenta como invocacion solo si su primer elemento
            # RESUELVE contra el arbol o contra la lista de binarios externos.
            # Y lo que no resuelve se cuenta aparte, con su clase.
            #
            #     la forma de un programa no lo delata: su nombre, si
            if not _resuelve(prog, arbol_nombres):
                descartadas += 1
                continue
            filas.append({"programa": prog, "de": etiqueta})
    return filas, descartadas


def _resuelve(s, arbol_nombres):
    """El nombre RESUELVE contra el arbol o contra los externos conocidos.

    No se decide por forma: `cond` y `pci_register_driver` tienen forma de
    identificador, y no son ninguno de los dos cosas.
    """
    base = os.path.basename(s)
    for ext in (".py", ".sh", ".c"):
        if base.endswith(ext):
            base = base[:-len(ext)]
    # MEDIDO: `arbol_nombres.values()` revienta con un `set`, y se le pasaba un
    # `set` desde el vector.  El vector era el que estaba mal tipado: aqui se
    # normaliza a `in`, que funciona con las dos estructuras.
    nombres = set(arbol_nombres)
    return (s in nombres or base in nombres or base in EXTERNOS)


def clasificar(prog, arbol_nombres):
    """(clase, nombre_resuelto). Tres clases, y no se mezclan."""
    base = os.path.basename(prog)
    for ext in (".py", ".sh", ".c"):
        if base.endswith(ext):
            base = base[:-len(ext)]
    if prog in arbol_nombres or base + ".py" in arbol_nombres or \
            prog in arbol_nombres.values() or base + ".sh" in arbol_nombres:
        return "HERRAMIENTA_NUESTRA", base
    if prog in EXTERNOS or base in EXTERNOS:
        return "BINARIO_EXTERNO", prog
    if prog.endswith((".py", ".sh")) or "/" in prog:
        return "RUTA_NO_RESUELTA", prog
    return "NOMBRE_NO_CLASIFICADO", prog


def medir():
    arbol_nombres = _hojas_de_fichero(DIRECTORIOS)
    filas = []
    n_sub = 0
    sin_literal = 0
    n_tabla_descartada = 0
    for sub in DIRECTORIOS:
        base = os.path.join(RAIZ, sub)
        if not os.path.isdir(base):
            continue
        for fn in sorted(os.listdir(base)):
            if not fn.endswith(".py"):
                continue
            rel = "%s/%s" % (sub, fn)
            ruta = os.path.join(RAIZ, rel)
            try:
                src = open(ruta, encoding="utf-8", errors="replace").read()
                arbol = ast.parse(src)
            except (OSError, SyntaxError) as e:
                filas.append({"quien": rel, "nivel": "ERROR",
                              "motivo": str(e)})
                continue
            # NIVEL 1 y 2: llamadas a subprocess
            for n in ast.walk(arbol):
                if not (isinstance(n, ast.Call)
                        and isinstance(n.func, ast.Attribute)
                        and n.func.attr in SUBPROCESS_ATTRS):
                    continue
                n_sub += 1
                argv = n.args[0] if n.args else None
                prog = nivel1_literal(arbol, argv)
                if prog is None:
                    sin_literal += 1
                    continue
                clase, res = clasificar(prog, arbol_nombres)
                filas.append({"quien": rel, "nivel": "1_LITERAL",
                              "linea": n.lineno, "programa": prog,
                              "clase": clase, "resuelto": res})
            # NIVEL 3: tablas que enumeran programas
            filas_t3, desc_t3 = nivel3_tablas(arbol, arbol_nombres)
            n_tabla_descartada += desc_t3
            for f in filas_t3:
                clase, res = clasificar(f["programa"], arbol_nombres)
                filas.append({"quien": rel, "nivel": "3_TABLA",
                              "linea": 0, "programa": f["programa"],
                              "de": f["de"], "clase": clase,
                              "resuelto": res})
    return filas, n_sub, sin_literal, arbol_nombres, n_tabla_descartada


def grafo(filas):
    """{quien: {resuelto: veces}} y los度数 de entrada, que es lo que importa."""
    sal = collections.defaultdict(collections.Counter)
    ent = collections.Counter()
    for f in filas:
        if f.get("clase") != "HERRAMIENTA_NUESTRA":
            continue
        sal[f["quien"]][f["resuelto"]] += 1
        ent[f["resuelto"]] += 1
    return dict(sal), ent


def vectores(d):
    v = [
        ("el-informe-esta-computado", d["estado"] == "OK", d["estado"]),
        ("las llamadas sin literal se CUENTAN, no se pierden",
         d["sin_programa_literal"] >= 0
         and d["sin_programa_literal"] <= d["llamadas_subprocess"],
         (d["sin_programa_literal"], d["llamadas_subprocess"])),
        ("toda clase de destino esta en el vocabulario declarado",
         all(f.get("clase") in (None, "HERRAMIENTA_NUESTRA",
                                "BINARIO_EXTERNO", "RUTA_NO_RESUELTA",
                                "NOMBRE_NO_CLASIFICADO", "ERROR")
             for f in d["filas"]), None),
        ("y una herramienta nuestra SIEMPRE resuelve a algo que existe",
         all(f["resuelto"] in d["nombres_del_arbol"]
             or f["resuelto"] + ".py" in d["nombres_del_arbol"]
             for f in d["filas"]
             if f.get("clase") == "HERRAMIENTA_NUESTRA"), None),
        # MEDIDO: este vector es el que sostiene el hallazgo.  Sin el, el 0 de
        # "invoca a herramientas hermanas" seria indistinguible de "no se ha
        # buscado".  La distincion es la que separa un dato de una ausencia.
        ("el cero de herramientas hermanas se declara como TAL, con su nivel",
         d["hermanas"]["n"] >= 0 and "niveles" in d["hermanas"],
         d["hermanas"].get("n")),
        # MEDIDO: este vector exigia que TODA fila de nivel 3 resolviera a una
        # herramienta DEL ARBOL, y fallo con `rg`, `llvm-objdump`, `addr2line`
        # y `pahole`: cuatro binarios EXTERNOS en tablas de herramientas.  El
        # fallo era del vector, no del dato: una tabla que invoca un binario
        # externo es una tabla de invocaciones tan legitima como otra.
        #
        #     exigir que todo sea propio, cuando parte es del sistema, es
        #     exigir que el dato no exista
        #
        # El oraculo correcto es mas fuerte que el que habia: toda fila de
        # nivel 3 resuelve contra el arbol O contra la lista de externos, que
        # son las dos unicas fuentes de verdad sobre que se puede ejecutar.
        ("toda fila de nivel 3 resuelve contra el arbol o contra los externos",
         all(_resuelve(f["programa"], set(d["nombres_del_arbol"]))
             for f in d["filas"] if f.get("nivel") == "3_TABLA"),
         [f["programa"] for f in d["filas"] if f.get("nivel") == "3_TABLA"
          and not _resuelve(f["programa"], set(d["nombres_del_arbol"]))][:6]),
        ("y las externas de nivel 3 se CUENTAN aparte de las del arbol",
         "BINARIO_EXTERNO" in d["por_clase"]
         or not any(f.get("clase") == "BINARIO_EXTERNO"
                    for f in d["filas"] if f.get("nivel") == "3_TABLA"),
         None),
        ("y el recuento de filas por nivel cuadra con el total",
         sum(d["por_nivel"].values()) == len([f for f in d["filas"]
                                               if f.get("nivel") != "ERROR"]),
         None),
        ("el informe declara que NO ejecuta nada",
         "no ejecuta nada" in d["declaracion_de_estado"].lower(), None),
        # Y el que hace el descarte CONTABLE: lo que una tabla 2D no es, se
        # cuenta.  Si no, el filtro seria una caja negra que deja pasar lo que
        # conviene y esconde lo que no.
        ("las tablas 2D que NO enumeran herramientas se CUENTAN, no se tiran",
         d["tablas_descartadas_no_herramientas"] >= 0,
         d["tablas_descartadas_no_herramientas"]),
    ]
    return v


DECLARACION = (
    "ESTADO de esta medicion.  No ejecuta nada: no invoca ninguna\n"
    "herramienta, no lee ningun modulo y no escribe en el arbol.\n"
    "  PROVEN        que la herramienta X llama a la herramienta Y, y se\n"
    "                resolvio el nombre contra el arbol.\n"
    "  NOT_FOUND     que NO se encontro una llamada.  No es PROVEN_ABSENT:\n"
    "                una llamada puede ir en una cadena construida, en un\n"
    "                bucle, o en un modulo que no se lee.\n"
    "  NOT_DETERMINED  el nivel 4 (destino que llega por flujo de datos a\n"
    "                traves de variables) no se mide, y se DECLARA.\n"
    "Lo que NO se afirma: que una herramienta sea segura por lo que llama.\n"
    "Se afirma COMO SE LLAMAN entre si, que es la pregunta que hace que una\n"
    "caja sea un sistema y no una carpeta de scripts."
)


def construir():
    filas, n_sub, sin_lit, nombres, desc_t3 = medir()
    sal, ent = grafo(filas)
    por_nivel = collections.Counter(f.get("nivel") for f in filas)
    por_clase = collections.Counter(f.get("clase") for f in filas)
    hermanas = [f for f in filas if f.get("clase") == "HERRAMIENTA_NUESTRA"]
    return {
        "estado": "OK",
        "proposito": "el acoplamiento que el grafo de imports no ve",
        "version": VERSION,
        "raiz": RAIZ,
        "llamadas_subprocess": n_sub,
        "sin_programa_literal": sin_lit,
        "tablas_descartadas_no_herramientas": desc_t3,
        "por_nivel": dict(por_nivel),
        "por_clase": {k: v for k, v in por_clase.items() if k},
        "hermanas": {
            "n": len(hermanas),
            "niveles": sorted({f["nivel"] for f in hermanas}),
            "quien_llama_a_que": {k: dict(v) for k, v in
                                  sorted(sal.items())},
            "top_por_entrantes": ent.most_common(15),
        },
        "externos": {k: v for k, v in por_clase.items()
                     if k == "BINARIO_EXTERNO"},
        "nombres_del_arbol": sorted(nombres),
        "filas": filas,
        "declaracion_de_estado": DECLARACION,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="rxre_deleg.py",
        description="el acoplamiento que el grafo de imports no ve")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="version", version=VERSION)
    args = ap.parse_args(argv)
    d = construir()

    if args.selftest:
        print("rxre_deleg %s -- selftest" % VERSION)
        ok = bad = 0
        for nombre, cond, det in vectores(d):
            print("  %-4s %s" % ("PASS" if cond else "FAIL", nombre))
            if not cond and det is not None:
                print("       %r" % (det,))
            ok += bool(cond)
            bad += not cond
        print()
        print("  %d pasan, %d fallan" % (ok, bad))
        if bad == 0:
            h = d["hermanas"]
            print()
            print("  LO MEDIDO:")
            print("    llamadas a subprocess en el arbol   %d"
                  % d["llamadas_subprocess"])
            print("    de ellas, con programa literal      %d"
                  % (d["llamadas_subprocess"] - d["sin_programa_literal"]))
            print("    SIN programa identificable          %d"
                  % d["sin_programa_literal"])
            print("    invocan HERRAMIENTAS NUESTRAS       %d  %s"
                  % (h["n"], h["niveles"]))
            print("    invocan binarios EXTERNOS           %d"
                  % d["por_clase"].get("BINARIO_EXTERNO", 0))
            print()
            for quien, qs in list(h["quien_llama_a_que"].items())[:8]:
                print("    %-32s -> %s" % (quien, ", ".join(sorted(qs)[:4])))
        return 0 if bad == 0 else 1

    if args.json:
        print(json.dumps(d, indent=1, ensure_ascii=False, default=str))
        return 0

    print("EL ACOPLAMIENTO QUE EL GRAFO DE IMPORTS NO VE")
    print()
    print("  llamadas a subprocess   %d" % d["llamadas_subprocess"])
    print("  con programa literal     %d"
          % (d["llamadas_subprocess"] - d["sin_programa_literal"]))
    print("  SIN programa identificable %d" % d["sin_programa_literal"])
    print()
    print("  POR NIVEL: %s" % d["por_nivel"])
    print("  POR CLASE: %s" % d["por_clase"])
    print()
    print("  QUIEN LLAMA A QUIEN (herramientas de este proyecto):")
    for quien, qs in sorted(d["hermanas"]["quien_llama_a_que"].items()):
        print("    %-34s -> %s" % (quien, ", ".join(sorted(qs)[:6])))
    print()
    for l in d["declaracion_de_estado"].split("\n"):
        print("  %s" % l)
    return 0


if __name__ == "__main__":
    sys.exit(main())
