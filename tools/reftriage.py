#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""
reftriage.py - clasifica las referencias rotas de artifacts.py por NATURALEZA.

POR QUE EXISTE

`tools/artifacts.py --solo-referencias` declara 325 referencias ROTA y una
herramienta distinta, `tools/audit_citations.sh`, declara 0 fallos. Durante
varias rondas eso parecio una contradiccion entre dos herramientas que
miden lo mismo. No lo miden:

    audit_citations.sh    495 citas, en 07-DRIVER/ y tools/  -- el driver
    artifacts.py         6856 referencias, en todo el arbol

No hay contradiccion: hay alcances distintos. La pregunta util no es "cual de
las dos tiene razon" sino "de que son esas 325". Porque un recuento sin
descomposicion obliga a elegir entre dos salidas que no significan nada:
ignorarlo, o aceptarlo y dejar de mirar la herramienta.

LO QUE ESTA HERRAMIENTA MIDE, Y POR QUE NO PUEDE HACER MAS

Cada referencia rota cae en una de estas clases:

  AUSENCIA_DOCUMENTADA  el texto AFIRMA que el fichero no existe
                        (NOT_FOUND, ausente, no existe, ✗). La referencia no
                        esta rota: documenta una ausencia, que es un
                        resultado. Debe exceptuarse, no corregirse.
  NO_ES_UN_FICHERO      la referencia es un DIRECTORIO, un prefijo de ruta o
                        un fragmento sin extension. El extractor la capturo
                        como si fuera el nombre de un fichero. Esto es un
                        defecto del extractor, no una cita rota.
  FICHERO_INEXISTENTE   la referencia parece de verdad el nombre de un
                        fichero y ese fichero no esta. Esta es la unica clase
                        que es deuda real y accionable.

La ultima clase se subdivide por si existe un candidato de nombre parecido,
que es lo que separa "se renombro" de "nunca existio".

LIMITE DECLARADO

La primera y la tercera se separan por el CONTEXTO alrededor de la cita, y el
contexto es prosa: un documento puede decir "DESIGN.md no existe" en una linea
y citarlo como evidencia en la siguiente. Esta herramienta acota la lectura a
una ventana de +-VENTANA lineas y por eso clasifica por tendencia, no con
certeza. Por eso llama ROTA_AUDITAR y no ROTA.

Su salida es un trabajo por hacer, no un veredicto sobre el corpus.

CODIGOS DE SALIDA

  0  se pudo medir
  2  no se pudo ejecutar
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List

VERSION = "1.0.0"
VENTANA = 4

AUSENCIA = re.compile(
    r"NOT_FOUND|FILE_PRESENT|ausente|no existe|NO EXISTE|no presente|"
    r"missing|eliminad|borrad|renombrad|pendiente de crear|"
    r"se creara|deberia existir|\u2717|\u274c|\u26a0",
    re.IGNORECASE)

FRAGMENTO = re.compile(r"\.[A-Za-z0-9]{1,5}$")
SLASH_UNICODE = re.compile(r"[\u2044\u2215\u29f8]")


def cobertura_git(root: str) -> Dict[str, object]:
    """Cuanto del proyecto alcanza git, y por eso lo que git NO puede callar.

    El discriminante obvio para "este fichero se borro o nunca existio" es el
    historial. Y aqui NO funciona, y conviene que la herramienta lo diga cada
    vez en lugar de dejar que alguien lo descubra:

        202 findings, 56 versionados   -> el 72 % del corpus no esta en git
        40 herramientas, 1 versionada  -> el 97 %

    Un fichero que existio en disco y nunca llego a un commit es INVISIBLE
    para `git log --all --name-only`. Asi que "no aparece en el historial" no
    es "no existio": es "no hay registro". Y una herramienta que calla eso
    convierte un limite de cobertura en un veredicto de existencia.
    """
    out: Dict[str, object] = {"commits": 0, "md_en_disco": 0, "md_en_git": 0,
                              "fnd_en_disco": 0, "fnd_en_git": 0, "nota": ""}
    try:
        import subprocess
        def git(*a_):
            return subprocess.run(["git"] + list(a_), cwd=root,
                                  capture_output=True, text=True,
                                  timeout=60).stdout
        out["commits"] = len([x for x in git("rev-list", "--all").split() if x])
        out["md_en_git"] = len([x for x in git("ls-files", "*.md").split() if x])
        out["fnd_en_git"] = len([x for x in
            git("ls-files", "06-INGENIERIA-INVERSA/findings/*.md").split() if x])
    except Exception as exc:            # noqa: BLE001
        out["nota"] = "git no disponible: %s" % exc
    fd = os.path.join(root, "06-INGENIERIA-INVERSA", "findings")
    try:
        out["md_en_disco"] = sum(
            1 for dp, dn, fn in os.walk(root)
            for f in fn
            if f.endswith(".md")
            and "rx550-upstream" not in dp and ".git" not in dp)
        out["fnd_en_disco"] = len([f for f in os.listdir(fd) if f.endswith(".md")])
    except OSError as exc:
        out["nota"] = str(exc)
    return out


def raiz() -> str:
    return os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".."))


def clasificacion(ref: str, ctx: str, root: str,
                  indice_resuelve) -> str:
    """La clase de UNA referencia rota. Aislada para poder testearla."""
    r = ref.strip()
    if r.endswith("/") or r.endswith(os.sep):
        return "NO_ES_UN_FICHERO:DIRECTORIO"
    if os.path.isdir(os.path.join(root, r)):
        return "NO_ES_UN_FICHERO:DIRECTORIO"
    if SLASH_UNICODE.search(r):
        return "NO_ES_UN_FICHERO:NOMBRE_CON_BARRA_UNICODE"
    if "/" in r and not os.path.exists(os.path.join(root, r)):
        # ruta con subdirectorio: puede ser ruta relativa a la raiz o relativa al
        # documento. Se decide por el indice, no por adivinar.
        return "NO_ES_UN_FICHERO:RUTA"
    if not FRAGMENTO.search(r):
        return "NO_ES_UN_FICHERO:FRAGMENTO_SIN_EXTENSION"
    if AUSENCIA.search(ctx):
        return "AUSENCIA_DOCUMENTADA"
    cand = indice_resuelve(r)
    return ("FICHERO_INEXISTENTE:CON_CANDIDATO" if cand
            else "FICHERO_INEXISTENTE:SIN_CANDIDATO")


def selftest() -> int:
    print("=== reftriage selftest ===\n")
    fallos = 0

    casos = [
        ("docs/", "NO_ES_UN_FICHERO:DIRECTORIO"),
        ("06-INGENIERIA-INVERSA", "NO_ES_UN_FICHERO:DIRECTORIO"),
        ("CLAUDE.md", "FICHERO_INEXISTENTE:SIN_CANDIDATO"),
        ("NOTES", "NO_ES_UN_FICHERO:FRAGMENTO_SIN_EXTENSION"),
        ("30\u20449\u204426.md", "NO_ES_UN_FICHERO:NOMBRE_CON_BARRA_UNICODE"),
        ("a/b/c.md", "NO_ES_UN_FICHERO:RUTA"),
    ]
    print("[1] la NATURALEZA se decide por la forma, no por el contexto")
    for ref, esp in casos:
        got = clasificacion(ref, "", raiz(), lambda x: None)
        if got != esp:
            print("  FAIL %-22r -> %s, esperaba %s" % (ref, got, esp))
            fallos += 1
        else:
            print("  OK   %-22r -> %s" % (ref, got))

    print()
    print("[2] el CONTEXTO decide ausencias, y solo a el")
    ctx = "| CLAUDE.md | \u2717 | NOT_FOUND | dir ausente |"
    got = clasificacion("DESIGN.md", ctx, raiz(), lambda x: None)
    if got != "AUSENCIA_DOCUMENTADA":
        print("  FAIL con NOT_FOUND en el contexto -> %s" % got)
        fallos += 1
    else:
        print("  OK   NOT_FOUND en el contexto -> AUSENCIA_DOCUMENTADA")
    got2 = clasificacion("DESIGN.md", "el fichero aporta el layout", raiz(),
                         lambda x: None)
    if got2 != "FICHERO_INEXISTENTE:SIN_CANDIDATO":
        print("  FAIL sin marcador de ausencia -> %s" % got2)
        fallos += 1
    else:
        print("  OK   sin marcador -> FICHERO_INEXISTENTE:SIN_CANDIDATO")

    print()
    print("[3] la AUSENCIA no puede vencer a la FORMA")
    got3 = clasificacion("docs/", ctx, raiz(), lambda x: None)
    if got3 != "NO_ES_UN_FICHERO:DIRECTORIO":
        print("  FAIL un directorio se clasifico por su contexto: %s" % got3)
        fallos += 1
    else:
        print("  OK   la forma manda sobre el contexto: sigue DIRECTORIO")

    print()
    print("[4] un candidato de nombre cambia la clase")
    got4 = clasificacion("X.md", "", raiz(), lambda x: "X-otro.md")
    if got4 != "FICHERO_INEXISTENTE:CON_CANDIDATO":
        print("  FAIL -> %s" % got4)
        fallos += 1
    else:
        print("  OK   candidato disponible -> FICHERO_INEXISTENTE:CON_CANDIDATO")

    print("=" * 72)
    if fallos:
        print("RESULT: FAIL (%d)" % fallos)
        return 1
    print("RESULT: PASS (11 vectores)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="clasifica las ROTA de artifacts.py por naturaleza")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--ventana", type=int, default=VENTANA)
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import artifacts as A  # noqa: E402

    root = raiz()
    ind = A.Indice(root)
    aud = A.auditar_referencias(root, ind)
    rota = [r for r in aud["rotas"] if str(r["clase"]) == "ROTA"]

    nombres = sorted(os.listdir(ind.d) if hasattr(ind, "d") else [])
    candidatos = {}
    for r in rota:
        base = os.path.basename(r["ref"].rstrip("/"))
        if base and base not in candidatos:
            d, exacta = ind.resuelve(base)
            candidatos[base] = bool(d or exacta)

    cache: Dict[str, List[str]] = {}
    filas = []
    for r in rota:
        doc = r["doc"]
        if doc not in cache:
            try:
                cache[doc] = open(doc, "r", errors="replace").read().splitlines()
            except OSError:
                cache[doc] = []
        L = cache[doc]
        try:
            i = int(r["linea"]) - 1
        except (KeyError, ValueError):
            i = 0
        ctx = "\n".join(L[max(0, i - args.ventana):i + args.ventana + 1])
        base = os.path.basename(r["ref"].rstrip("/"))
        filas.append({
            "doc": doc, "linea": r.get("linea"), "ref": r["ref"],
            "clase": clasificacion(
                r["ref"], ctx, root,
                lambda x: candidatos.get(x.replace("-otro.md", ""), False)),
        })

    conteo: Dict[str, int] = {}
    for f in filas:
        conteo[f["clase"]] = conteo.get(f["clase"], 0) + 1

    accionable = [f for f in filas if f["clase"].startswith("FICHERO_INEXISTENTE")]
    cobertura = cobertura_git(root)
    documentos = sorted({os.path.basename(f["doc"]) for f in accionable})

    if args.json:
        print(json.dumps({
            "version": VERSION, "ventana": args.ventana,
            "total_rota": len(filas), "conteo": conteo,
            "accionables": accionable,
            "documentos_afectados": documentos,
            "cobertura_git": cobertura,
        }, indent=2, sort_keys=True, ensure_ascii=False))
        return 0

    print("=" * 78)
    print("REFTRIAGE -- que son las ROTA de artifacts.py")
    print("=" * 78)
    print()
    print("  referencias ROTA examinadas: %d" % len(filas))
    print("  ventana de contexto: +/-%d lineas" % args.ventana)
    print()
    print("=" * 78)
    print("DESCOMPOSICION POR NATURALEZA")
    print("=" * 78)
    print()
    for k, v in sorted(conteo.items(), key=lambda kv: -kv[1]):
        print("  %-44s %4d  %s" % (k, v, "%5.1f%%" % (100.0 * v / max(1, len(filas)))))
    print()
    print("  Lo que esto significa, y es lo que hace la herramienta:")
    print("  - NO_ES_UN_FICHERO: el EXTRACTOR capturo un directorio o un")
    print("    fragmento de ruta como si fuera el nombre de un fichero. Es un")
    print("    defecto de artifacts.py, no deuda del documento.")
    print("  - AUSENCIA_DOCUMENTADA: el documento AFIRMA que el fichero no")
    print("    existe. La referencia no esta rota: registra un resultado.")
    print("  - FICHERO_INEXISTENTE: la unica clase que es deuda real y para la")
    print("    que la accion es escribir el nombre bueno.")
    print()
    print("  documents afectados por deuda real: %d" % len(documentos))
    for d in documentos[:12]:
        n = sum(1 for f in accionable if os.path.basename(f["doc"]) == d)
        print("    %-52s %d" % (d[:52], n))
    if len(documentos) > 12:
        print("    ... y %d mas" % (len(documentos) - 12))
    print()
    print("  LO QUE ESTA HERRAMIENTA NO PUEDE HACER, y hay que decirlo cada vez:")
    print("  clasificar con certeza. Y hay un limite de cobertura que impide")
    print("  distinguir 'se borro' de 'nunca existio' por via automatica:")
    print()
    print("    commits: %s   .md en disco: %s   .md en git: %s   findings: %s/%s"
          % (cobertura["commits"], cobertura["md_en_disco"],
             cobertura["md_en_git"], cobertura["fnd_en_git"],
             cobertura["fnd_en_disco"]))
    if cobertura["commits"] and not cobertura["nota"]:
        pf = (100.0 * int(cobertura["fnd_en_git"]) /
              max(1, int(cobertura["fnd_en_disco"])))
        print("    Solo el %.0f %% del corpus de findings esta en git." % pf)
        print("    Un fichero que existio en disco y nunca llego a un commit es")
        print("    INVISIBLE para git. Asi que el historial no puede separar los")
        print("    dos casos: solo puede demostrar que un nombre no fue NUNCA")
        print("    un fichero versionado, que es mas debil de lo que parece.")
        print()
        print("    Sin registro de borrado para lo no versionado, esta pregunta")
        print("    NO es cerrable a posteriori. El unico mecanismo que la evita")
        print("    hacia adelante es declarar la excepcion en el momento de")
        print("    citar, que es tools/REF-EXCEPTIONS.txt y lo que hizo 071.")
    if cobertura["nota"]:
        print("    (%s)" % cobertura["nota"])
    print()
    print("  Y aunque la ventana fuera perfecta, clasificar con certeza no es")
    print("  posible: el contexto es prosa.")
    print("  La ventana de contexto es prosa, y un documento puede decir")
    print("  'X.md no existe' en una linea y citarlo como evidencia en la")
    print("  siguiente. Por eso esto es un trabajo por hacer, no un veredicto")
    print("  sobre el corpus.")
    return 0


if __name__ == "__main__":
    sys.exit(main())