#!/usr/bin/env python3
"""FASE D. Normalizacion de resultados, con el RAW conservado.

POR QUE UN RESULTADO NORMALIZADO Y NO EL TEXTO DE LA HERRAMIENTA.

Cada herramienta devuelve una forma distinta. `evidence_search.py` devuelve
`{root, file, line, text}`. `reg_resolve.py` devuelve
`{kind, symbol, verdict, definitions}`. `trace_path.py` devuelve un arbol con
`children`. Una IA que consulta tres capacidades tiene que aprender tres
formas, y el cuarto formato la rompe.

El resultado normalizado tiene las claves SIEMPRE, con `None` donde no aplica,
porque un consumidor que hace `r["location"]` y se encuentra una KeyError no es
un consumidor, es una fuente de conclusiones falsa.

Y LA REGLA QUE NO SE NEGOCIA: el `raw` se conserva SIEMPRE. Normalizar sin
guardar el original es perder informacion sin poder recuperarla, y la
normalizacion es una INTERPRETACION: si el normalizador se equivoca, el raw es
lo unico que permite saberlo.

    la normalizacion es una opinion sobre el dato; el raw es el dato
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List, Optional

SCHEMA_RESULT = "1.0"

#: Claves del resultado normalizado. Todas presentes siempre.
CAMPOS = ("result_id", "type", "value", "source", "location", "scope", "tool",
          "tool_version", "input", "timestamp", "artifact", "artifact_hash",
          "status", "limitations", "raw")


def _id(tipo: str, valor: Any, tool: str,
        donde: Optional[Dict[str, Any]] = None) -> str:
    """Identificador de un resultado. UNICO y DETERMINISTA.

    MEDIDO 2026-10-05: se derivaba solo de (tipo, valor, herramienta). Con una
    busqueda de un registro, 36 usos daban NINE ids distintos: muchos usos
    comparten el MISMO texto -- `tmp = REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL,` sale
    en 223, en 224 y en 226 -- y el id colisionaba.

        un identificador que colisiona no identifica

    Dos consecuencias, y las dos son malas:
      - `explain <result_id>` no puede decir cual de los 36 es
      - la tabla `results` usa `INSERT OR REPLACE`, asi que 36 filas se
        convierte en 9 y la evidencia se pierde SIN QUE NADIE LO NOTE

    La UBICACION entra en el hash: es lo que distingue dos usos del mismo texto.
    Sigue siendo determinista, que es lo que hace que la misma consulta dos
    veces de los mismos ids.
    """
    h = hashlib.sha256(
        ("%s|%s|%s|%s" % (tipo, json.dumps(valor, sort_keys=True, default=str),
                         tool, json.dumps(donde or {}, sort_keys=True,
                                          default=str)))
        .encode("utf-8")).hexdigest()[:12]
    return "res_%s_%s" % (tipo, h)


def resultado(tipo: str, valor: Any, *, tool: str, source: str = "",
              location: Optional[Dict[str, Any]] = None,
              scope: str = "linux-7.1.3", tool_version: str = "",
              entrada: Optional[Dict[str, Any]] = None,
              status: str = "observed", artifact: str = "",
              artifact_hash: str = "", raw: Any = None,
              limitations: Optional[List[str]] = None) -> Dict[str, Any]:
    """Un resultado normalizado. `raw` se conserva siempre.

    `status` por resultado es `observed` y no `proven`: un resultado es una
    OBSERVACION de una herramienta, y el veredicto epistemico lo pone quien
    interpreta, no el que recoge. Se separan a proposito (§9): un `observed` que
    alguien mas convierta en `proven` queda registrado como conversion, no como
    hecho.
    """
    return {
        "result_id": _id(tipo, valor, tool, location),
        "type": tipo,
        "value": valor,
        "source": source,
        "location": location or {},
        "scope": scope,
        "tool": tool,
        "tool_version": tool_version,
        "input": entrada or {},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "artifact": artifact,
        "artifact_hash": artifact_hash,
        "status": status,
        "limitations": list(limitations or []),
        "raw": raw if raw is not None else valor,
    }


# --- conversores por tipo de herramienta ----------------------------------
# Cada uno recibe la salida CRUDA de una herramienta y devuelve resultados
# normalizados. Se separan del transporte (`dispatch.py`) porque aqui es donde
# hay SEMANTICA, y la semantica de cada herramienta es distinta.

def de_busqueda(d: Dict[str, Any]) -> List[Dict[str, Any]]:
    """`evidence_search.py --json` -> una fila por coincidencia."""
    out = []
    for h in (d.get("hits") or []):
        loc = {"file": h.get("file"), "line": h.get("line"),
               "root": h.get("root")}
        txt = (h.get("text") or "").strip()
        out.append(resultado(
            "source_occurrence", txt or h.get("file", "?"),
            tool="evidence_search.py", source=h.get("root", ""),
            location=loc, entrada={"query": d.get("query")},
            artifact=loc.get("file", ""), raw=h,
            limitations=["una coincidencia de texto en un fichero; no establece "
                         "que el simbolo se USE, solo que la cadena aparece"],
        ))
    return out


def de_registro(d: Dict[str, Any]) -> List[Dict[str, Any]]:
    """`reg_resolve.py --json` -> resultados de registro/campo.

    MEDIDO: para `VM_CONTEXT0_CNTL` sobre `linux-7.1.3`, `reg_resolve.py`
    devuelve `verdict: PROVEN_ABSENT_EN_ASIC_REG` con `definitions: []`. Su
    propio `note` acota el alcance: es ausencia de DEFINICION DE OFFSET, no de
    hardware. esa acotacion se copia a `limitations` del resultado, porque sin
    ella el `PROVEN_ABSENT` se leeria como "el registro no existe", que es otra
    cosa y es falsa.
    """
    out = []
    ud = d.get("unit_declaration") or {}
    for r in (d.get("results") or []):
        lim = []
        if r.get("note"):
            lim.append(r["note"])
        if ud.get("consequence"):
            lim.append("unidad: %s" % ud["consequence"])
        out.append(resultado(
            "register", r.get("symbol"),
            tool="reg_resolve.py", source="asic_reg",
            location={"file": ud.get("file"), "symbol": ud.get("symbol")},
            tool_version=d.get("version", ""), status="resolved",
            entrada={"gfx": d.get("gfx"), "amd_root": d.get("amd_root")},
            raw=r, limitations=lim,
        ))
    return out


def de_defuse(d: Dict[str, Any]) -> List[Dict[str, Any]]:
    """`lachesis_defuse.py --json` -> una fila por resultado.

    El estado epistemico del adaptador (`state`) viaja como
    `status` del resultado normalizado y en `raw.state`. Cuando el
    estado es una ausencia acotada (PROVEN_ABSENT_*), `raw` lleva
    ademas `verdict`, para que la regla de ausencia acotada del
    pipeline (`engine._es_ausencia_acotada`) la reconozca: esa
    ausencia es de DEFINICION en asic_reg (con busqueda exhaustiva
    como evidencia), no de hardware, y el envelope la trata como
    tal en vez de como un hallazgo.
    """
    out = []
    for r in (d.get("results") or []):
        estado = str(r.get("state") or "NOT_DETERMINED")
        raw = dict(r)
        if estado.startswith("PROVEN_ABSENT"):
            raw.setdefault("verdict", estado)
        loc = r.get("location") or {}
        prov = r.get("provenance") or {}
        productor = prov.get("identity", {}).get("producer") \
            or prov.get("producer") or "lachesis"
        lim = ["estado epistemico: %s (productor: %s)"
               % (estado, productor)]
        lim.extend(r.get("limitations") or [])
        out.append(resultado(
            "defuse_%s" % (r.get("kind") or "resultado"),
            r.get("label") or r.get("symbol")
            or r.get("subject") or "?",
            tool="lachesis_defuse.py", source="lachesis",
            location={"file": loc.get("file"),
                      "line": loc.get("start_line")},
            tool_version=d.get("version", ""),
            entrada={"intent": d.get("intent"),
                     "subject": d.get("subject")},
            status=estado.lower(),
            raw=raw,
            limitations=lim,
        ))
    return out


def de_uso_registro(hit: Dict[str, Any], consulta: str) -> Dict[str, Any]:
    """Una fila de busqueda clasificada como uso de registro por su patron.

    MEDIDO 2026-10-05: no existe en `tools/` ninguna herramienta que clasifique
    lectura/escritura de un registro. SI existe el patron en el codigo del
    driver:

        REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL, ENABLE_CONTEXT, 1)

    `REG_SET_FIELD` construye un valor que se escribe; `RREG`/`WREG` de
    `amdgpu_device` son las primitivas. Un uso que casa con un constructor de
    ESCRITURA es un candidato a escritor.

    Y aqui esta la palabra que evita la trampa: **candidato**. Que el texto
    case con el patron es una OBSERVACION sobre el texto. Que la funcion sea la
    unica que escribe ese registro es una conclusion que exige mas: hay que
    llamar a la funcion, y eso no se ha hecho. Por eso `status` es `observed` y
    la limitacion lo dice.
    """
    txt = (hit.get("text") or "").strip()
    escritura = ("REG_SET_FIELD" in txt or "REG_RMW" in txt
                 or "WREG" in txt or "WRITE_DWORD" in txt)
    lectura = ("RREG" in txt or "READ_DWORD" in txt)
    tipo_pat = "escritura" if escritura else ("lectura" if lectura else "uso")
    lim = ["clasificacion por PATRON DE TEXTO (`%s` casa con un constructor de "
           "%s). No demuestra que la funcion escriba el registro en runtime: "
           "para eso hay que llamar a la funcion."
           % (tipo_pat, tipo_pat)]
    if tipo_pat == "uso":
        lim.append("el texto NO casa con ningun constructor conocido de lectura "
                   "ni de escritura: se clasifica como uso indeterminado, no "
                   "como lectura")
    return resultado(
        "register_use", txt, tool="evidence_search.py",
        source=hit.get("root", ""),
        location={"file": hit.get("file"), "line": hit.get("line")},
        entrada={"query": consulta}, artifact=hit.get("file", ""),
        raw={"hit": hit, "patron": tipo_pat}, status="observed",
        limitations=lim,
    )


def de_arbol_trace(nodo: Dict[str, Any]) -> List[Dict[str, Any]]:
    """`trace_path.py --json` -> aplanar el arbol a una lista.

    El arbol se aplana a una lista POR NIVEL, y cada nodo guarda su `padre`.
    Aplanar es una transformacion, asi que se dice: el arbol original esta en
    `raw` del primer nodo.
    """
    out: List[Dict[str, Any]] = []
    primero = True

    def anda(n: Dict[str, Any], padre: Optional[str], prof: int) -> None:
        nonlocal primero
        ver = n.get("verdict", "")
        lim = []
        if ver == "NO_ENCONTRADO":
            lim.append("trace_path no lo encontro en el subarbol que declara "
                       "haber recorrido; eso no es que no exista")
        r = resultado(
            "trace_node", n.get("sym"),
            tool="trace_path.py",
            location={"loc": n.get("loc"), "parent": padre, "depth": prof},
            status="observed", raw=(n if primero else None),
            entrada={"verdict": ver, "conds": n.get("conds")},
            limitations=lim,
        )
        if primero:
            r["raw"] = {"nodo": n}      # el arbol entero, una sola vez
            primero = False
        out.append(r)
        for c in (n.get("children") or []):
            anda(c, n.get("sym"), prof + 1)

    anda(nodo, None, 0)
    return out
