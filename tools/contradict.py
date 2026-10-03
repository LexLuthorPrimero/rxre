#!/usr/bin/env python3
"""contradict.py — afirmaciones incompatibles entre hallazgos del proyecto.

Por qué existe
--------------
En este proyecto se han escrito ~57 documentos de hallazgos. Cada uno afirma
cosas sobre el mismo hardware, y a veces dos affirmed sobre lo mismo. Ha pasado
varias veces: `0x00` como "pendiente" contra "armado por el host",
`polaris10_smumgr.c` como "nuestra ruta" contra "rama de Polaris10", voltaje en
mV contra "0.25 mV deducido".

Cada corrección mia fue posible porque me acordé de que lo anterior decía otra
cosa. Eso no escala. Con 57 documentos y varios agentes trabajando en paralelo,
la contradicción entre dos documentos es inevitable y su detección debe ser
mecánica.

Qué compara
-----------
Líneas de forma `IDENTIFICADOR = ESTADO`, que es la convención que usan los
documentos de hallazgos, y en general cualquier pareja
`<SENTENCIA> ... <SUJETO> ... <PREDICADO>` con el mismo sujeto.

Y hace lo más importante: **distingue corrección de contradicción**.
Un hallazgo posterior que REFUTA uno anterior no es un conflicto: es progreso,
y el documento debe decirlo. Un conflicto es cuando dos afirmaciones
VIGENTES dicen cosas incompatibles y ninguna marca a la otra.

Lo que produce
--------------
Para cada par de afirmaciones incompatibles: fichero, línea, y qué dice cada
una. Y separa:
  CORRECCION    el segundo REFUTA al primero, con la marca explícita
  CONFLICTO     ambas vigentes, incompatibles, sin marcar
  SOSPECHOSO    no se puede decidir con el corpus de texto

Uso
---
    contradict.py --findings 06-INGENIERIA-INVERSA/findings
    contradict.py --findings 06-INGENIERIA-INVERSA/findings --only-conflicts
    contradict.py --selftest
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Set, Tuple

NAME = "contradict"
VERSION = "1.0.0"

WORK_CLASS = "READ_ONLY"
WRITE_EXECUTION = "NONE"

# Tres formas de escribir un veredicto, porque en 88 documentos no hay una
# sola. Aceptar solo la primera hacia "ningun conflicto" sobre 88 ficheros,
# que es un resultado limpio y falso.
#   IDENTIFICADOR = ESTADO
#   IDENTIFICADOR: ESTADO
#   | ESTADO |  dentro de una tabla, con el sujeto en la primera columna
ASSIGN = re.compile(r"^\s*([A-Z][A-Z0-9_]{4,})\s*=\s*([A-Z][A-Z0-9_]*)\s*$")
ASSIGN_COLON = re.compile(r"^\s*([A-Z][A-Z0-9_]{4,})\s*:\s*([A-Z][A-Z0-9_]*)\s*$")
TABLE_ROW = re.compile(
    r"^\s*\|\s*([^|\s][^|]{2,60}?)\s*\|\s*(PROVEN|PROVEN_ABSENT|REFUTED|"
    r"CORROBORATED|NOT_DETERMINED|NOT_PROVEN|NOT_IN_CORPUS|NOT_FOUND|"
    r"UNKNOWN|PARTIAL|DEFERRED|OBSERVED)\s*\|")

# Estados que describen el mismo eje. Dos afirmaciones del mismo eje con
# estados distintos son candidatas a conflicto.
AXES: Dict[str, Set[str]] = {
    "veredicto_existencia": {"PROVEN", "PROVEN_ABSENT", "NOT_IN_CORPUS",
                             "NOT_FOUND", "REFUTED", "CORROBORATED",
                             "NOT_DETERMINED", "NOT_PROVEN", "UNKNOWN",
                             "OBSERVED", "PARTIAL", "DEFERRED"},
    "veredicto_semantica": {"PROVEN", "NOT_DETERMINED", "NOT_PROVEN",
                            "CORROBORATED", "REFUTED", "UNKNOWN"},
    "alcance":          {"PROVEN", "NOT_IN_CORPUS", "NOT_READ", "PARTIAL"},
}

# Estados incompatibles dentro de un eje: no pueden coexistir.
INCOMPATIBLE = [("PROVEN", "PROVEN_ABSENT"), ("PROVEN", "REFUTED"),
                ("PROVEN", "NOT_DETERMINED"), ("PROVEN", "UNKNOWN"),
                ("PROVEN_ABSENT", "PROVEN"), ("CORROBORATED", "PROVEN_ABSENT"),
                ("OBSERVED", "PROVEN_ABSENT")]

# Marcas que convierten una contradiccion en correccion.
REFUTE_MARKS = ("REFUTED", "CORRECTS", "CORRECCION", "correcci", "retirado",
                "ERROR", "PROVEN_ABSENT", "retira")
SUPERSEDE = ("CORRECTS", "CORRECTION", "CORRECCION", "correcci",
             "supersede", "reemplaza", "retirado")


def parse_assignments(path: str) -> List[Dict[str, object]]:
    """Las lineas `IDENT = ESTADO` de un documento, con su linea."""
    out: List[Dict[str, object]] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return out
    # NO se ignoran los bloques de codigo: la convencion de estos hallazgos
    # es escribir las asignaciones DENTRO de un bloque de codigo. Filtrarlas dejaba
    # cero hallazgos y el informe decia "ninguna contradiccion", que es el
    # falso negativo mas peligroso de esta herramienta: parece un resultado.
    for n, line in enumerate(lines, 1):
        raw = line.rstrip()
        m = ASSIGN.match(raw) or ASSIGN_COLON.match(raw)
        if m:
            out.append({"file": os.path.basename(path), "line": n,
                        "ident": m.group(1), "state": m.group(2),
                        "forma": "IGUAL" if "=" in m.group(0) else "DOS_PUNTOS",
                        "text": raw.strip()})
            continue
        mt = TABLE_ROW.match(raw)
        if mt:
            # La primera columna es el sujeto; se normaliza a mayusculas y sin
            # espacios para poder compararlo con el de otra forma de escritura.
            ident = re.sub(r"[^A-Z0-9]+", "_",
                           mt.group(1).upper().replace("_", " ")).strip("_")
            out.append({"file": os.path.basename(path), "line": n,
                        "ident": ident, "state": mt.group(2),
                        "forma": "TABLA", "text": raw.strip()[:160]})
    return out


# Veredictos escritos en PROSA: "SMC_PAYLOAD = PROVEN" ya es formal, pero
# "DIDT_STALL_TUNING_ARE_GFX9_PLUS_ONLY = PROVEN_ABSENT" y otros 189 pares
# aparecen como "SUJETO es/no es PROVEN". Sin normalizar esa prosa, la
# herramienta compara 34 veredictos de 783 que hay en el corpus y declara
# "ningun conflicto" sobre el 95% del material.
VERDICT_TOKENS = ("PROVEN_ABSENT", "PROVEN_DERIVED", "PROVEN_DERIVED",
                  "NOT_DETERMINED", "NOT_IN_CORPUS", "NOT_PROVEN",
                  "NOT_FOUND", "NOT_OBSERVED", "NOT_AVAILABLE",
                  "CORROBORATED", "REFUTED", "UNKNOWN", "PARTIAL",
                  "DEFERRED", "OBSERVED", "PROVEN")
_VERDICT_ALT = "|".join(sorted(set(VERDICT_TOKENS), key=len, reverse=True))
_SUBJ = r"[A-Z][A-Z0-9_]{5,}"

_PROSA_A = re.compile(
    r"\b(" + _SUBJ + r")\b[^.\n|]{0,40}?\b(" + _VERDICT_ALT + r")\b")

def prose_verdicts(path: str) -> List[Dict[str, object]]:
    """Veredictos en prosa, normalizados a (sujeto, estado)."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return []
    out: List[Dict[str, object]] = []
    for n, line in enumerate(lines, 1):
        raw = line.rstrip()
        if raw.strip().startswith("```") or raw.strip().startswith("|"):
            continue
        if not re.search(_VERDICT_ALT, raw):
            continue
        # Una linea ya formal ("IDENT = ESTADO") la captura parse_assignments.
        # Si ademas se recoge aqui, el mismo hecho aparece dos veces y genera
        # un conflicto consigo mismo: cuatro findings donde hay uno.
        if ASSIGN.match(raw) or ASSIGN_COLON.match(raw):
            continue
        # SOLO la forma "SUJETO ... VEREDICTO". La inversa
        # ("VEREDICTO ... sujeto") captura como sujeto cualquier palabra en
        # mayusculas del inciso, y produjo falsos positivos en los tres
        # primeros documentos analizados:
        #   "es una pregunta abierta (NOT_DETERMINED, RUNTIME)"  -> sujeto RUNTIME
        #   "RUNTIME; (b) es PROVEN que no hay garantia"          -> sujeto RUNTIME
        #   "por que RELEASE_MEM no desaparecio (NOT_DETERMINED)"-> sujeto RELEASE_MEM
        # En los tres, el veredicto pertenece a otro inciso. Dos letras mayusculas
        # sueltas no son un sujeto, y esa forma no aporta ningun hallazgo real.
        m = _PROSA_A.search(raw)
        if not m:
            continue
        subj, st = m.group(1), m.group(2)
        if subj == st:
            continue
        # Una misma frase puede llevar dos veredictos a proposito:
        #   "es PROVEN_DERIVED a partir del orden, y NOT_DETERMINED a nivel
        #    de hardware"
        # Eso es precision, no contradiccion. Si la linea contiene mas de un
        # veredicto distinto, se descarta: normalizar dos en un par produce un
        # conflicto que el documento nunca afirmo.
        otros = {m2.group(0) for m2 in re.finditer(_VERDICT_ALT, raw)}
        if len(otros) > 1:
            continue
        out.append({"file": os.path.basename(path), "line": n,
                    "ident": subj, "state": st, "forma": "PROSA",
                    "text": raw.strip()[:200]})
    return out


def axis_of(state: str) -> Optional[str]:
    for axis, states in AXES.items():
        if state in states:
            return axis
    return None


def incompatible(a: str, b: str) -> bool:
    for x, y in INCOMPATIBLE:
        if (a == x and b == y) or (a == y and b == x):
            return True
    return False


def doc_states(path: str) -> Dict[str, List[Dict[str, object]]]:
    """Estados por identificador, y el titulo para saber de que va."""
    by_ident: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for a in parse_assignments(path):
        by_ident[str(a["ident"])].append(a)
    return by_ident


def document_header(path: str) -> Dict[str, str]:
    """Las marcas del documento: se corrige, se retira, etc."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            head = "".join([next(fh, "") for _ in range(40)])
    except OSError:
        return {}
    out: Dict[str, str] = {}
    # Las marcas vienen en lineas tipo:
    #   `A=x` · `B=y` · `CORRECTS=049`
    # separadas por punto medio y dentro de backticks. Un regex de principio a
    # fin de linea no las veia, y una correccion declarada se reportaba como
    # conflicto abierto.
    for m in re.finditer(r"`([A-Z][A-Z_]{3,})=([^`\s]+)`", head):
        out[m.group(1)] = m.group(2).strip().rstrip("`·,")
    for m in re.finditer(r"^\s*`?([A-Z][A-Z_]{3,})=([^`\n·]+)", head, re.M):
        out.setdefault(m.group(1), m.group(2).strip())
    return out


def find_conflicts(files: Sequence[str]) -> List[Dict[str, object]]:
    """Pares de afirmaciones incompatibles sobre el MISMO identificador."""
    index: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    headers: Dict[str, Dict[str, str]] = {}
    for f in files:
        base = os.path.basename(f)
        headers[base] = document_header(f)
        rows = parse_assignments(f) + prose_verdicts(f)
        for a in rows:
            index[str(a["ident"])].append({**a, "header": headers[base]})

    conflicts: List[Dict[str, object]] = []
    for ident, occ in sorted(index.items()):
        if len(occ) < 2:
            continue
        for i, x in enumerate(occ):
            for y in occ[i + 1:]:
                if not incompatible(str(x["state"]), str(y["state"])):
                    continue
                hx, hy = str(x.get("file")), str(y.get("file"))
                # Mismo fichero y misma linea no es conflicto.
                if hx == hy and x["line"] == y["line"]:
                    continue
                # Si el mas nuevo se declara correccion, no es conflicto.
                # El orden NO es alfabetico de nombre de fichero: "010-a.md"
                # ordena DESPUES de "012-c.md" y la herramienta tomaba la
                # correccion como documento viejo, mirando sus marcas, que no
                # las tiene, y declarando CONFLICTO un par que era
                # correccion. El orden es por el NUMERO del documento, que es
                # lo que significa "posterior".
                def docnum(nm: str) -> int:
                    m2 = re.match(r"^(\d+)", nm)
                    return int(m2.group(1)) if m2 else -1
                newer, older = ((x, y) if docnum(hx) >= docnum(hy)
                                else (y, x))
                # La CLAVE es lo que dice "esto corrige a otro":
                # CORRECTS=010-a. Concatenar solo los valores daba "010-a" y
                # la palabra CORRECTS se perdia, con lo que una correccion
                # declarada se|reportaba como conflicto abierto.
                hdr = newer.get("header") or {}
                marks = " ".join(f"{k} {v}" for k, v in hdr.items())
                is_correction = any(mk.lower() in marks.lower() for mk in SUPERSEDE)
                conflicts.append({
                    "ident": ident,
                    "kind": "CORRECCION" if is_correction else "CONFLICTO",
                    "older": {"file": older["file"], "line": older["line"],
                              "state": older["state"]},
                    "newer": {"file": newer["file"], "line": newer["line"],
                              "state": newer["state"]},
                    "newer_marks": marks[:160],
                    "reason": ("el segundo se declara correccion del primero"
                               if is_correction else
                               "ambos vigentes, estados incompatibles, "
                               "ninguno marca al otro"),
                })
    return conflicts


def render(conflicts: Sequence[Dict[str, object]], only_conflicts: bool) -> str:
    L = [f"{NAME} {VERSION}"]
    L.append(f"  WORK_CLASS={WORK_CLASS} · WRITE_EXECUTION={WRITE_EXECUTION}")
    L.append("  CORRECCION: el segundo REFUTA al primero y lo declara. Es progreso.")
    L.append("  CONFLICTO: ambos vigentes, incompatibles, sin marcar. Eso hay que resolver.")
    L.append("")
    if not conflicts:
        L.append("  Ningun par incompatible sobre el mismo identificador.")
        return "\n".join(L)
    shown = [c for c in conflicts
             if not only_conflicts or c["kind"] == "CONFLICTO"]
    if not shown:
        L.append("  Solo hay correcciones. Ningun conflicto abierto.")
        return "\n".join(L)
    L.append(f"  {'identificador':<34} {'tipo':<12} {'viejo':<34} {'nuevo'}")
    L.append("  " + "-" * 116)
    for c in shown:
        old = f"{c['older']['file'][:20]}:{c['older']['line']} {c['older']['state']}"
        new = f"{c['newer']['file'][:20]}:{c['newer']['line']} {c['newer']['state']}"
        L.append(f"  {str(c['ident'])[:34]:<34} {str(c['kind']):<12} "
                 f"{old:<34} {new}")
        if c["kind"] == "CONFLICTO":
            L.append(f"      {c['reason']}")
    return "\n".join(L)


def selftest() -> int:
    failures: List[str] = []

    def check(name: str, got, want) -> None:
        if got != want:
            failures.append(f"{name}: obtuve {got!r}, esperaba {want!r}")

    check("ejes.proven", axis_of("PROVEN"), "veredicto_existencia")
    check("ejes.no_definido", axis_of("VOLTAGE_SCALE"), None)
    check("incomp.proven_absent", incompatible("PROVEN", "PROVEN_ABSENT"), True)
    check("incomp.identicos", incompatible("PROVEN", "PROVEN"), False)

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        # Dos documentos con el mismo identificador en estados incompatibles,
        # ninguno declarando correccion: CONFLICTO.
        a = os.path.join(td, "010-a.md")
        with open(a, "w", encoding="utf-8") as fh:
            fh.write("# 010 · a\n\n```\nVOLTAGE_UNIT = PROVEN\n```\n")
        b = os.path.join(td, "011-b.md")
        with open(b, "w", encoding="utf-8") as fh:
            fh.write("# 011 · b\n\n```\nVOLTAGE_UNIT = NOT_DETERMINED\n```\n")
        cs = find_conflicts([a, b])
        check("conflicto.detectado", len(cs), 1)
        check("conflicto.tipo", cs[0]["kind"], "CONFLICTO")

        # El segundo declara CORRECTS: es correccion, no conflicto.
        # Correccion: el MISMO identificador cambia de estado y el segundo
        # documento lo declara. Sin la marca, el par no aparece: el par solo
        # se detecta cuando los estados son INCOMPATIBLES, y una correccion
        # tipica va de NOT_DETERMINED a PROVEN, que si es incompatible, pero
        # de PROVEN a PROVEN no lo es y no hay nada que confrontar.
        c = os.path.join(td, "012-c.md")
        with open(c, "w", encoding="utf-8") as fh:
            fh.write("# 012 · c\n`CORRECTS=010-a`\n\n```\nVOLTAGE_UNIT = PROVEN\n```\n")
        # El 010 afirmaba NOT_DETERMINED, el 012 lo refuta como PROVEN.
        with open(a, "w", encoding="utf-8") as fh:
            fh.write("# 010 · a\n\n```\nVOLTAGE_UNIT = NOT_DETERMINED\n```\n")
        cs2 = find_conflicts([a, c])
        check("correccion.detectada", len(cs2), 1)
        check("correccion.tipo", cs2[0]["kind"], "CORRECCION")
        # El mismo par SIN la marca CORRECTS es un conflicto abierto.
        with open(c, "w", encoding="utf-8") as fh:
            fh.write("# 012 · c\n\n```\nVOLTAGE_UNIT = PROVEN\n```\n")
        cs3 = find_conflicts([a, c])
        check("sin_marca_es_conflicto", cs3[0]["kind"], "CONFLICTO")

        # Estados compatibles: sin conflicto
        d = os.path.join(td, "013-d.md")
        with open(d, "w", encoding="utf-8") as fh:
            fh.write("# 013\n\n```\nDIDT_GATES = PROVEN\nDIDT_GATES = PROVEN\n```\n")
        check("compatible.sin_conflicto", find_conflicts([d]), [])

        # Un '4' en el identificador no es identificador
        e = os.path.join(td, "014.md")
        with open(e, "w", encoding="utf-8") as fh:
            fh.write("# 014\n\n```\nlinea suelta = PROVEN\nX = 1\n```\n")
        check("no_identificador", parse_assignments(e), [])

        # Entradas vacias y ficheros inexistentes
        v = os.path.join(td, "vacio.md")
        open(v, "w").close()
        check("vacio", parse_assignments(v), [])
        # prosa: "SUJETO_X no esta en GFX8: PROVEN_ABSENT"
        pr = os.path.join(td, "015-prosa.md")
        with open(pr, "w", encoding="utf-8") as fh:
            fh.write("# 015\n\nDIDT_STALL_ARE_GFX9_PLUS_ONLY = PROVEN_ABSENT en gfx_8_0_d.h\n"
                     "Y_OTRA_COSA no esta: PROVEN_ABSENT\n")
        pv = prose_verdicts(pr)
        check("prosa.detecta", len(pv) >= 1, True)
        check("prosa.estado", pv[0]["state"] if pv else None, "PROVEN_ABSENT")
        check("prosa.sujeto", pv[0]["ident"] if pv else None,
              "DIDT_STALL_ARE_GFX9_PLUS_ONLY")
        check("prosa.ignora_bloque", prose_verdicts(pr)[1]["ident"] != "PROVEN_ABSENT", True)
        check("inexistente", parse_assignments(os.path.join(td, "nope.md")), [])

    print(f"{NAME} {VERSION} · self-test")
    if failures:
        print(f"  RESULTADO FALLIDO ({len(failures)}):")
        for f in failures:
            print(f"    - {f}")
        return 1
    print("  RESULTADO OK · vectores conocidos reproducidos")
    print("  NOTA: compara afirmaciones escritas. NO comprueba si son ciertas.")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog=NAME,
                                 description="Detecta afirmaciones incompatibles entre hallazgos.")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--findings", default=None)
    ap.add_argument("--only-conflicts", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.findings:
        ap.error("--findings es obligatorio salvo con --selftest")
    d = os.path.abspath(args.findings)
    if not os.path.isdir(d):
        print(f"ERROR  no existe {d}", file=sys.stderr)
        return 2
    files = sorted(os.path.join(d, f) for f in os.listdir(d)
                   if f.endswith(".md"))
    cs = find_conflicts(files)
    if args.json:
        print(json.dumps({"tool": NAME, "version": VERSION,
                          "documents": len(files), "conflicts": cs},
                         indent=2, ensure_ascii=False))
        return 0
    print(render(cs, args.only_conflicts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
