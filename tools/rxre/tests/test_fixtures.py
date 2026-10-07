#!/usr/bin/env python3
"""Fase H. Fixture de regresion RX550 sobre entradas reales del corpus.

POR QUE UN FIXTURE Y NO "LOS TESTS SIGUEN PASANDO".

Los vectores de `test_rxre002.py` comprueban el CONTRATO: que hay envelope, que
`empty` no es ausencia, que la Intel esta bloqueada. Eso no detecta una respuesta
que cambia de valor. Si manana `evidence_search.py` deja de encontrar los 35 usos
de `VM_CONTEXT0_CNTL` porque alguien toco el corpus, todos los vectores siguen en
verde porque solo comprueban la FORMA.

El fixture ata el contrato A un valor concreto del corpus RX550, y el corpus se
puede mover. Es lo que convierte "RXRE funciona" en "RXRE sigue funcionando
sobre ESTA maquina".

Y la regla del `not_expect` es la que lo hace util: no basta con que el estado sea
`ok`; hay que comprobar que no aparece el texto de una ausencia demostrada. Un
`ok` con una limitacion que dice "no existe" es el fallo mas caro de esta clase
y un fixture que solo mirara `status` no lo veria.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
MACHINE = os.path.join(PKG, "api", "machine.py")
FIXTURE = os.path.join(PKG, "fixtures", "rx550_regresion.json")
if PKG not in sys.path:
    sys.path.insert(0, PKG)

fails: List[str] = []
checked = 0


def v(nombre: str, cond: bool, det: Any = "") -> None:
    global checked
    checked += 1
    if not cond:
        fails.append("%s %s" % (nombre, det))


def machine(lineas, timeout=2400):
    entrada = "\n".join(json.dumps(x) for x in lineas) + "\n"
    p = subprocess.run([sys.executable, MACHINE], input=entrada,
                       capture_output=True, text=True, timeout=timeout)
    return [json.loads(ln) for ln in p.stdout.splitlines() if ln.strip()]


def _pct_de(r):
    """El `pct` de un resultado de provenance, este donde este.

    MEDIDO 2026-10-05: el `pct` no esta en la raiz del resultado sino dentro de
    `value`, porque el valor normalizado de una fila es `{clave, pct, sin}`. Y
    con la raiz vacia, `pct_maximo_por_clave` comparaba una lista VACIA: `all()`
    sobre `[]` es `True`, y un rango que se cumple con cero valores medidos no
    comprueba nada.

        un rango que se cumple con cero valores no comprueba nada
    """
    if isinstance(r, dict) and isinstance(r.get("pct"), (int, float)):
        return r["pct"]
    val = r.get("value") if isinstance(r, dict) else None
    if isinstance(val, dict) and isinstance(val.get("pct"), (int, float)):
        return val["pct"]
    return None


def check(nombre: str, sec: Dict[str, Any], rq: Dict[str, Any],
          env: Dict[str, Any]) -> None:
    """Comprueba un caso contra su EXPECT y su NOT_EXPECT."""
    exp = rq.get("expect", {})
    ne = rq.get("not_expect", {})

    for k, want in exp.items():
        if k == "min_results":
            v("%s: resultados >= %d" % (nombre, want),
              len(env.get("results", [])) >= want, len(env.get("results", [])))
        elif k == "next_actions_min":
            v("%s: next_actions >= %d" % (nombre, want),
              len(env.get("next_actions", [])) >= want,
              len(env.get("next_actions", [])))
        elif k == "opciones_min":
            v("%s: opciones >= %d" % (nombre, want),
              len(env.get("capability_resolution", {}).get("options", [])) >= want,
              len(env.get("capability_resolution", {}).get("options", [])))
        elif k == "herramientas":
            # MEDIDO 2026-10-05: el fixture pedia nombres de SCRIPT
            # ("evidence_search.py") y el envelope trae nombres de VERBO
            # ("search", "register"), porque `stages[].op` es la capacidad de
            # RXRE-001 y el script va en `tools_used[].tool`, que en un pipeline
            # va vacio: `tools_used` se rellena por CAPACIDAD, no por etapa.
            #
            # La asercion tiene que mirar las dos cosas y aceptar las dos
            # formas, o el fixture mide el nombre y no el hecho.
            usados = {t.get("tool") for t in env.get("tools_used", []) if t.get("tool")}
            etapas = {s.get("op") for s in env.get("stages", [])}
            prov = {p.get("tool") for p in env.get("provenance", [])
                    if isinstance(p, dict) and p.get("tool")}
            juntos = usados | etapas | prov
            faltan = [h for h in want if h not in juntos]
            faltan = [h for h in want if h not in juntos]
            v("%s: usaron %s" % (nombre, want), not faltan,
              "faltan %s de %s" % (faltan, sorted(juntos)))
        elif k == "results_empty":
            v("%s: results vacio" % nombre, env.get("results") == [],
              len(env.get("results", [])))
        elif k == "capability":
            v("%s: capability == %s" % (nombre, want),
              env.get("operation") == want, env.get("operation"))
        elif k == "result_types":
            tipos = {r.get("type") for r in env.get("results", [])}
            faltan = [t for t in want if t not in tipos]
            v("%s: tipos de resultado %s" % (nombre, want), not faltan,
              "faltan %s de %s" % (faltan, sorted(tipos)))
        elif k == "value_contiene":
            # MEDIDO 2026-10-05: este tipo de comprobacion es el UNICO que ata el
            # fixture al VALOR y no solo a la FORMA. Con solo `min_results`,
            # mutar el contenido real de un resultado daba fixture OK: la
            # respuesta seguia siendo "algo con 3 elementos".
            txt = " ".join(str(r.get("value", "")) for r in env.get("results", []))
            for frag in want:
                v("%s: algun valor contiene %r" % (nombre, frag),
                  frag in txt, "no aparece en %d chars" % len(txt))
        elif k == "claves_presentes":
            # MEDIDO 2026-10-05: el `clave` no esta en la raiz del resultado sino
            # dentro de `value`, porque el valor normalizado de una fila de
            # provenance es el objeto `{clave, pct, sin}`. Un fixture que busca
            # `r["clave"]` no encuentra nada y falla con una lista vacia que no
            # dice nada de donde viene el problema.
            #
            #     un fixture que no encuentra el campo ensena a mirar el campo
            def _clave_de(r):
                if isinstance(r, dict) and "clave" in r:
                    return r["clave"]
                val = r.get("value") if isinstance(r, dict) else None
                return val.get("clave") if isinstance(val, dict) else None

            claves = {k2 for k2 in (_clave_de(r) for r in env.get("results", []))
                      if k2}
            faltan = [c for c in want if c not in claves]
            v("%s: claves presentes %s" % (nombre, want), not faltan,
              "faltan %s de %s" % (faltan, sorted(k for k in claves if k)))
        elif k == "pct_maximo_por_clave":
            pcts = [_pct_de(r) for r in env.get("results", [])]
            pcts = [p for p in pcts if isinstance(p, (int, float))]
            # MEDIDO 2026-10-05: este rango NO cztaba la mutacion M7
            # (`pct: 0.0`) porque 0 esta dentro de [0, 100]. Un rango que
            # contiene el valor de la mutacion es un rango que no comprueba
            # nada.
            #
            #     un rango que contiene el valor mutado no detecta la mutacion
            #
            # Por eso el fixture ata el VALOR medido (85.7 / 28.6), y el rango
            # queda como red de seguridad para valores absurdos.
            todos_ok = all(0 < p <= want for p in pcts)
            v("%s: todos los pct en (0, %s]" % (nombre, want), todos_ok, pcts)
        elif k == "pct_minimo_por_clave":
            pcts = [_pct_de(r) for r in env.get("results", [])]
            pcts = [p for p in pcts if isinstance(p, (int, float))]
            todos_ok = all(want <= p for p in pcts)
            v("%s: todos los pct >= %s" % (nombre, want), todos_ok, pcts)
        elif k == "pct_valores":
            pcts = sorted(_pct_de(r) for r in env.get("results", []))
            pcts = [p for p in pcts if isinstance(p, (int, float))]
            v("%s: pct medidos == %s" % (nombre, want), pcts == sorted(want),
              pcts)
        elif k == "sin_capability":
            v("%s: sin capacidad" % nombre,
              env.get("capability_resolution", {}).get("resolved") is None,
              env.get("capability_resolution", {}).get("resolved"))
        elif k == "value_contiene":
            txt = " ".join(str(r.get("value", "")) for r in env.get("results", []))
            for frag in want:
                v("%s: ningun valor debe contener %r" % (nombre, frag),
                  frag not in txt, "aparece en %d chars" % len(txt))
        elif k == "capability_no_nula":
            v("%s: capability NO debe ser nula" % nombre,
              env.get("capability_resolution", {}).get("resolved") is None,
              env.get("capability_resolution", {}).get("resolved"))
        else:
            v("%s: %s == %r" % (nombre, k, want), env.get(k) == want,
              env.get(k))

    for k, want in ne.items():
        if k == "status":
            v("%s: status NO debe ser %s" % (nombre, want),
              env.get("status") != want, env.get("status"))
        elif k == "limitations_contienen":
            txt = " ".join(env.get("limitations", [])).lower()
            for frase in want:
                v("%s: limitations NO debe decir %r" % (nombre, frase),
                  frase.lower() not in txt, env.get("limitations")[:1])
        elif k == "value_contiene":
            txt = " ".join(str(r.get("value", "")) for r in env.get("results", []))
            for frag in want:
                v("%s: ningun valor debe contener %r" % (nombre, frag),
                  frag not in txt, "aparece en %d chars" % len(txt))
        elif k == "capability_no_nula":
            v("%s: capability NO debe ser nula" % nombre,
              env.get("capability_resolution", {}).get("resolved") is None,
              env.get("capability_resolution", {}).get("resolved"))


def main() -> int:
    with open(FIXTURE, encoding="utf-8") as fh:
        fx = json.load(fh)

    for sec, cuerpo in sorted(fx.items()):
        if sec.startswith("_"):
            continue
        for rq in cuerpo.get("requests", []):
            if rq.get("op") == "capability":
                lineas = [{"op": "query", "target": rq.get("target", "0000:01:00.0"),
                           "capability": rq["capability"]}]
            else:
                lineas = [dict(rq, op="query")]
                if "target" not in lineas[0]:
                    lineas[0]["target"] = "0000:01:00.0"
            env = machine(lineas)[0]
            nombre = "%s/%s" % (sec, (rq.get("question") or rq.get("capability"))
                                or "?")
            check(nombre, cuerpo, rq, env)

    if fails:
        print("fixture FALLA (%d de %d comprobaciones)" % (len(fails), checked))
        for f in fails:
            print("   " + f)
        return 1
    print("fixture OK (%d comprobaciones sobre %d secciones, entradas reales "
          "del corpus linux-7.1.3)" % (checked, len([k for k in fx
                                                    if not k.startswith("_")])))
    return 0


if __name__ == "__main__":
    sys.exit(main())