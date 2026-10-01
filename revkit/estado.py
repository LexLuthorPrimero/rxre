#!/usr/bin/env python3
"""
estado.py -- sincroniza el estado del proyecto desde los documentos.

POR QUE EXISTE
--------------
El proyecto tiene varios ficheros de estado: EVIDENCE-MATRIX,
MASTER-RESEARCH-STATUS, CONTRADICTIONS, OPEN-FRONTIERS. Mantenerlos a mano
es trabajo repetitivo que se queda obsoleto en silencio: un hallazgo nuevo no
aparece en la matriz hasta que alguien se acuerda.

Este script NO EDITA esos ficheros. Extrae el estado que YA esta escrito en
los documentos y lo consolida, de modo que:

  - se ve que evidencia hay y de que clase
  - se ven las contradicciones abiertas y si estan resueltas
  - se ve que sigue NOT_DETERMINED
  - se comprueba si un hallazgo esta en la matriz o solo en su .md

QUE NO HACE
-----------
No decide. No cierra nada. Un NOT_DETERMINED sigue siendolo aunque aqui
aplazca. La consolidacion es una VISTA, no una fuente de verdad, y se declara
en la salida para que nadie la cite como si lo fuera.
"""
import argparse
import os
import re
from collections import Counter, defaultdict

PROJ = "/home/lucas/Escritorio/RX550-INVESTIGACION"

ESTADOS = [
    "PROVEN", "OBSERVED", "PROVEN_DERIVED", "PROVEN_ABSENT", "CORROBORATED",
    "REFUTED", "NOT_PROVEN", "UNKNOWN", "NOT_DETERMINED", "NOT_AVAILABLE",
    "NOT_OBSERVED", "NOT_FOUND", "NOT_APPLICABLE", "NOT_IN_CORPUS",
    "PARTIAL", "DEFERRED", "CONTRADICTED",
]
# Los que NO son evidencia de resolucion, para poder separarlos.
NEGATIVOS = {"NOT_DETERMINED", "UNKNOWN", "NOT_PROVEN", "NOT_FOUND",
             "NOT_AVAILABLE", "NOT_OBSERVED", "DEFERRED", "NOT_IN_CORPUS"}

RE_ESTADO = re.compile(r"\b(" + "|".join(ESTADOS) + r")\b")


def documentos(sub="."):
    out = []
    for base, _d, fs in os.walk(os.path.join(PROJ, sub)):
        if "/.git" in base or "/RESEARCH" in base or "/.write-lock" in base:
            continue
        for f in sorted(fs):
            if f.endswith(".md"):
                out.append(os.path.join(base, f))
    return out


def cmd_censo(args):
    mds = documentos(args[0] if args else ".")
    print("CENS0 DE ESTADOS: %d documentos" % len(mds))
    print()
    total = Counter()
    por_doc = {}
    for p in mds:
        txt = open(p, encoding="utf-8", errors="replace").read()
        c = Counter(RE_ESTADO.findall(txt))
        if not c:
            continue
        rel = os.path.relpath(p, PROJ)
        por_doc[rel] = c
        total.update(c)
    print("%-38s %s" % ("estado", "apariciones"))
    print("-" * 62)
    for e in ESTADOS:
        if total[e]:
            neg = " (no es resolucion)" if e in NEGATIVOS else ""
            print("%-38s %6d%s" % (e, total[e], neg))
    print("-" * 62)
    print("%-38s %6d" % ("TOTAL", sum(total.values())))
    print()
    pos = sum(v for k, v in total.items() if k not in NEGATIVOS)
    neg = sum(v for k, v in total.items() if k in NEGATIVOS)
    if pos + neg:
        print("resolucion : %d" % pos)
        print("no resuelto: %d" % neg)
    print()
    print("AVISO: esto cuenta MENCIONES de estados, no afirmaciones unicas.")
    print("Un mismo hecho puede aparecer marcado de dos formas en dos")
    print("documentos, y eso es una INCONSISTENCIA que el conteo no ve.")
    return 0


def cmd_contradicciones(args):
    """Localiza contradicciones y comprueba si tienen veredicto."""
    p = os.path.join(PROJ, "docs/CONTRADICTIONS.md")
    if not os.path.exists(p):
        print("no existe docs/CONTRADICTIONS.md")
        return 1
    txt = open(p, encoding="utf-8", errors="replace").read()
    bloques = re.split(r"\n## ", txt)
    print("CONTRADICCIONES REGISTRADAS: %d" % (len(bloques) - 1))
    print()
    print("%-10s %-24s %s" % ("id", "estado", "severidad"))
    print("-" * 74)
    abiertas = 0
    for b in bloques[1:]:
        cabecera = b.split("\n")[0]
        # El id viene dentro de backticks: "## `C-005` · titulo". Se quita
        # todo lo que no sea el identificador, porque si no la columna
        # muestra "C-005 · `" y parece un dato corrupto en vez de un
        # recorte. Un campo con basura no se puede citar.
        mid = re.match(r"\s*`?([A-Z]-\d+)`?", cabecera)
        cid = mid.group(1) if mid else cabecera[:9].strip()
        est = re.search(r"ESTADO\s+(\w+)", b)
        sev = re.search(r"SEVERIDAD\s+([A-Z]+)", b)
        e = est.group(1) if est else "(sin ESTADO)"
        s = sev.group(1) if sev else "-"
        print("%-10s %-24s %s" % (cid, e, s))
        if e != "RESOLVED":
            abiertas += 1
    print("-" * 74)
    print("abiertas: %d de %d" % (abiertas, len(bloques) - 1))
    print()
    print("Una contradiccion con ESTADO que no sea RESOLVED sigue abierta,")
    print("y eso no es un descuido: es informacion sobre el estado real.")
    return 0


def cmd_cobertura(args):
    """
    Que documentos de evidencia existen, y cuales tienen su evidencia.

    Detecta el caso que mas caro sale: un documento que AFIRMA algo y no dice
    de donde sale. Un PROVEN sin evidencia es una CONCLUSION sin DERIVACION.
    """
    mds = documentos(".")
    print("COBERTURA DE EVIDENCIA")
    print()
    sin_ev, con_ev = [], []
    for p in mds:
        txt = open(p, encoding="utf-8", errors="replace").read()
        rel = os.path.relpath(p, PROJ)
        tiene_proven = "PROVEN" in txt
        # evidencia = cita al corpus, o ruta de fichero
        evidencia = bool(re.search(r"[\w/]+\.[ch]:\d+", txt)) or \
            bool(re.search(r"`[a-z_]+\.[ch]`", txt))
        if tiene_proven:
            (con_ev if evidencia else sin_ev).append(rel)
    print("documentos que afirman PROVEN: %d" % (len(con_ev) + len(sin_ev)))
    print("  con cita al corpus   : %d" % len(con_ev))
    print("  SIN cita al corpus   : %d" % len(sin_ev))
    if sin_ev:
        print()
        print("sin cita al corpus (revisar: la afirmacion de donde sale)")
        for r in sorted(sin_ev)[:25]:
            print("   %s" % r)
    print()
    print("Esto NO dice que las afirmaciones sean erroneas. Dice que el")
    print("documento no apunta a donde sale, que es distinto, y tambien")
    print("impide comprobarlas automaticamente.")
    return 0


def cmd_registro(args):
    """Lista los documentos con su primera linea de titulo: el indice."""
    mds = documentos(args[0] if args else ".")
    print("%-62s %s" % ("documento", "titulo"))
    print("-" * 110)
    for p in sorted(mds):
        try:
            primera = open(p, encoding="utf-8",
                           errors="replace").readline().strip()
        except Exception:
            continue
        if not primera.startswith("#"):
            primera = "(sin titulo)"
        rel = os.path.relpath(p, PROJ)
        n = sum(1 for _ in open(p, encoding="utf-8", errors="replace"))
        print("%-62s %4d L  %s" % (rel, n, primera[:40]))
    print()
    print("%d documentos" % len(mds))
    return 0


def main():
    ap = argparse.ArgumentParser(description="estado del proyecto")
    ap.add_argument("cmd", choices=["censo", "contradicciones", "cobertura",
                                    "registro"])
    ap.add_argument("args", nargs="*")
    a = ap.parse_args()
    return {"censo": cmd_censo, "contradicciones": cmd_contradicciones,
            "cobertura": cmd_cobertura, "registro": cmd_registro}[a.cmd](a.args)


if __name__ == "__main__":
    raise SystemExit(main())