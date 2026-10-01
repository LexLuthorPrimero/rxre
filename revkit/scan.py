#!/usr/bin/env python3
"""
scan.py -- descubre TRABAJO, en vez de esperar a que le pidan trabajo.

POR QUE EXISTE
--------------
Las herramientas anteriores responden preguntas que uno se hace. Esta
encuentra las que NO te has hecho.

El protocolo pide un "next action" siempre. Buscarlo a mano es lo mas caro del
proyecto, y se hace mal de dos formas: eligiendo lo mas interesante en vez de
lo mas bloqueante, y repitiendo trabajo ya hecho porque nadie recuerda que
existia un hallazgo.

Este script barre el estado real del proyecto y produce una lista ORDENADA por
valor, no por novedad:

  bloqueantes   lo que impide cerrar mas cosas
  huecos        lo que se afirmo sin evidencia
  invariantes   hechos que parecem especificos y son de la familia entera
  solo-escritos registros MMIO sin observable
  abierta       contradicciones sin resolver

QUE NO HACE
-----------
No decide cual investigar. Ordena por un criterio declarado y explica el
criterio, para que se pueda discutir. Una lista de candidatos sin criterio es
tan inutil como no tenerla.
"""
import argparse
import os
import re
import subprocess
import sys
from collections import defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
PROJ = "/home/lucas/Escritorio/RX550-INVESTIGACION"


def ejecuta(args, timeout=600):
    try:
        r = subprocess.run([sys.executable] + args, cwd=AQUI,
                           capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:
        return 1, "", str(e)


# --------------------------------------------------------------- bloqueantes
def bloqueantes():
    """
    Dependencias: que NO_DETERMINED bloquea mas cosas.

    Se cuenta cuantas veces aparece cada simbolo o registro en el estado
    NOT_DETERMINED de los documentos. Un simbolo que aparece 8 veces como
    Determinado bloquea mas trabajo que uno que aparece una.
    """
    print("=" * 76)
    print("1. BLOQUEANTES: que aparece muchas veces como NOT_DETERMINED")
    print("=" * 76)
    print()
    d = os.path.join(PROJ, "08-ARQUITECTURA")
    if not os.path.isdir(d):
        return
    conteo = defaultdict(int)
    donde = defaultdict(set)
    for base, _dd, fs in os.walk(d):
        for f in sorted(fs):
            if not f.endswith(".md"):
                continue
            p = os.path.join(base, f)
            try:
                txt = open(p, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            # lineas con NOT_DETERMINED, y que simbolos menciona
            for ln in txt.splitlines():
                if "NOT_DETERMINED" not in ln:
                    continue
                for tok in re.findall(
                        r"\b(m?[A-Z][A-Z0-9_]{4,})\b", ln):
                    conteo[tok] += 1
                    donde[tok].add(f)

    # QUITAR el ruido antes de ordenar.
    #
    # La primera version contaba "NOT_DETERMINED" 189 veces, que es la
    # palabra que se estaba buscando, y "PROVEN" 9 veces, que es la
    # CONTRAPARTIDA de la busqueda. Un ranking dominado por su propio termino
    # de busqueda no ordena nada: da la sensacion de tener un plan y no lo
    # tiene.
    RUIDO = {
        "NOT_DETERMINED", "PROVEN", "DERIVATION", "MODEL_CHOICE",
        "REQUIREMENT", "POLICY", "IMPLEMENTATION", "TEST", "CONCLUSION",
        "HYPOTHESIS", "ASSUMPTION", "LIMITATION", "ERROR", "FACT",
        "OBSERVATION", "MEASUREMENT", "NEGATIVE_RESULT", "CONTRADICTION",
        "DEPENDENCY", "COMPLETION", "REQUIRED", "OPTIONAL", "GENERIC",
        "SPECIFIC", "BLOQUEADO", "STATUS", "REABIERTA", "REQUIREMENTS",
        "NOT_FOUND", "NOT_RUN", "PROVEN_DERIVED", "PROVEN_ABSENT",
        "CORROBORATED", "REFUTED", "UNKNOWN", "NOT_AVAILABLE",
        "NOT_OBSERVED", "NOT_APPLICABLE", "NOT_IN_CORPUS", "PARTIAL",
        "DEFERRED", "CONTRADICTED", "EVIDENCE", "SEMANTICS", "DISCRIMINANT",
        "VALIDATION", "IMPLEMENTACION", "DOCUMENTACION", "EVIDENCIA",
        "INVARIANTE", "COHERENCE", "COHERENCIA", "LIBGL_ALWAYS_SOFTWARE",
    }
    conteo = {k: v for k, v in conteo.items()
              if k not in RUIDO and len(k) >= 5}

    # SEPARAR lo que esta RESUELTO de lo que no, aunque la linea lo mezcle.
    #
    # GFX_HWIP salia como el bloqueante numero 1 con 5 apariciones en 5
    # documentos, pero 009bis lo descompone en tres objetos y DOS son
    # PROVEN. El termino esta bloqueado en un sentido y resuelto en dos
    # otros. Un conteo que no lo distingue infla el bloqueante mas visible
    # del proyecto.
    #
    # Se busca el termino en el resto del documento: si el mismo simbolo
    # aparece con PROVEN o REFUTED, se anota como PARCIAL, no como bloqueante
    # puro.
    resueltos = set()
    for base, _dd, fs in os.walk(d):
        for f in sorted(fs):
            if not f.endswith(".md"):
                continue
            try:
                txt = open(os.path.join(base, f),
                           encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            for sym in list(conteo):
                if re.search(r"\b%s\b\s+.*\b(PROVEN|REFUTED|CORROBORATED)\b"
                             % re.escape(sym), txt) or \
                   re.search(r"\b(PROVEN|REFUTED|CORROBORATED)\b.*\b%s\b"
                             % re.escape(sym), txt):
                    resueltos.add(sym)
    top = sorted(conteo.items(), key=lambda x: -x[1])[:18]
    if not top:
        print("ningun simbolo aparece en lineas NOT_DETERMINED")
        return
    print("%-40s %5s %5s %s" % ("simbolo", "veces", "docs", "estado real"))
    print("-" * 76)
    for tok, n in top:
        est = ("PARCIAL: ya resuelto en parte" if tok in resueltos
               else "bloqueante")
        print("%-40s %5d %5d %s" % (tok[:40], n, len(donde[tok]), est))
    print()
    print("Criterio: cuantas lineas NOT_DETERMINED lo mencionan, y si el")
    print("         mismo simbolo aparece tambien como PROVEN o REFUTED.")
    print("LIMITE: muchas menciones NO son muchas dependencias. Esto ordena")
    print("        por VISIBILIDAD, no por causalidad. Es un INDICADOR de")
    print("        que mirar antes, no un plan de trabajo.")
    return


# ------------------------------------------------------------------- huecos
def huecos():
    """
    Documentos que afirman PROVEN y no citan el corpus.
    """
    print()
    print("=" * 76)
    print("2. HUECOS: PROVEN sin cita al corpus")
    print("=" * 76)
    print()
    rc, out, _ = ejecuta(["estado.py", "cobertura"])
    m = re.search(r"SIN cita al corpus\s*:\s*(\d+)", out)
    if not m:
        print("no se pudo leer el recuento")
        return
    print("documentos con PROVEN y sin cita: %s" % m.group(1))
    print()
    print("Criterio: el documento marca PROVEN y no tiene ninguna cita")
    print("         fichero.c:LINEA. Eso NO lo hace erroneo: le quita la")
    print("         posibilidad de comprobarlo automaticamente.")
    return


# -------------------------------------------------------------- invariantes
def invariantes():
    """
    Hechos que parecen especificos de GFX8 y en realidad son de la familia.

    Se compara el numero de ficheros donde aparece un simbolo. Si aparece en
    seisASIC, el hallazgo sobre uno de ellos probablemente aplica a los otros
    cinco, y ese es un dato que rara vez se busca.

    Esto se ha encontrado de verdad: PFP_SYNC_ME en vm_flush esta en las ocho
    generaciones de v6 a v12. El proyecto lo tenia como decision de GFX8.
    """
    print()
    print("=" * 76)
    print("3. INVARIANTES: comportamientos compartidos por toda la familia")
    print("=" * 76)
    print()
    rc, out, _ = ejecuta(["ibtrace.py", "sync"])
    fam = defaultdict(list)
    for ln in out.splitlines():
        m = re.match(r"(\S+)\s+(\S.*?)\s{2,}(\S+)", ln)
        if not m:
            continue
        fn, ops, fichero = m.groups()
        if "v" not in fichero:
            continue
        g = re.match(r"(gfx_v|gmc_v)(\d+)", fichero)
        if not g:
            continue
        for o in ops.split(","):
            if o.strip():
                fam[o.strip()].append("%s:%s" % (fn[:38], g.group(2)))
    for op, donde in sorted(fam.items()):
        gens = sorted({d.split(":")[1] for d in donde},
                      key=lambda x: int(re.sub(r"\D", "", x) or 0))
        if len(gens) >= 4:
            print("%-24s en %d generacion(es): %s"
                  % (op, len(gens), ", ".join(gens)))
    print()
    print("Criterio: al menos 4 generaciones. Si un comportamiento aparece")
    print("en 8, no es una decision del ASIC sino de la familia, y eso")
    print("cambia la lectura de 'por que GFX8 hace esto'.")
    return


# ------------------------------------------------------------ solo-escritos
def solo_escritos():
    """
    Registros que el driver escribe y nunca lee.

    Para cada uno no hay observable en el driver de referencia. Ese es el
    frente de investigacion mas grande que genera el modo descubrimiento.
    """
    print()
    print("=" * 76)
    print("4. SOLO-ESCRITOS: registros MMIO sin observable")
    print("=" * 76)
    print()
    for asic in ("gfx_v8_0", "gmc_v8_0", "sdma_v4_0"):
        rc, out, _ = ejecuta(["causa.py", "descubrir", asic])
        m = re.search(r"total distintos\s*:\s*(\d+)", out)
        s = re.search(r"SOLO escritos\s*:\s*(\d+)", out)
        if not (m and s):
            continue
        print("%-12s %4s registros, %3s solo escritos (%s%%)"
              % (asic, m.group(1), s.group(1),
                 int(100 * int(s.group(1)) / max(int(m.group(1)), 1))))
    print()
    print("Un registro solo-escrito es un candidato natural a pregunta")
    print("abierta: el hardware lo consume y el driver no puede saber si lo")
    print("necesita ni de que depende. Para resolverlo hace falta runtime.")
    print()
    print("los candidatos concretos, por ASIC:")
    print("   ./causa.py descubrir gfx_v8_0")
    return


# ------------------------------------------------------------------ abiertas
def abiertas():
    print()
    print("=" * 76)
    print("5. ABIERTAS: contradicciones sin veredicto")
    print("=" * 76)
    print()
    rc, out, _ = ejecuta(["estado.py", "contradicciones"])
    for ln in out.splitlines():
        if re.match(r"C-\d+", ln):
            print(ln)
    print()
    print("Criterio: ESTADO distinto de RESOLVED.")
    return


def main():
    ap = argparse.ArgumentParser(description="descubre trabajo pendiente")
    ap.add_argument("--solo", default=None,
                    help="bloqueantes|huecos|invariantes|solo|abiertas")
    a = ap.parse_args()
    print("SCAN DE TRABAJO PENDIENTE")
    print("Ordenado por criterio declarado, no por novedad.")
    print()
    if a.solo:
        {"bloqueantes": bloqueantes, "huecos": huecos,
         "invariantes": invariantes, "solo": solo_escritos,
         "abiertas": abiertas}[a.solo]()
        return 0
    bloqueantes()
    huecos()
    invariantes()
    solo_escritos()
    abiertas()
    print()
    print("=" * 76)
    print("NINGUNO de estos criterios mide causalidad. Todos son")
    print("indicadores de VISIBILIDAD: lo que se ve mucho tiene prioridad")
    print("para MIRARSE, no para estar bloqueado de verdad.")
    print("La dependencia real hay que leerla. Esta lista solo evita que se")
    print("pase por alto lo que ya se sabe que esta abierto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())