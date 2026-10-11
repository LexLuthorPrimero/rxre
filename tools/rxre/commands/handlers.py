#!/usr/bin/env python3
"""Normalizadores: salida de cada herramienta -> envelope de RXRE.

POR QUE ESTE MODULO EXISTE Y NO ESTA DENTRO DEL ADAPTADOR.

Porque cada herramienta tiene su propia forma de decir lo mismo y TRES cosas
distintas que no se pueden fundir:

    exito con resultados     la mayoria
    exito sin resultados     necesita decir POR QUE, y el por que es lo unico
                             que separa "no hay" de "no mire"
    no se pudo ejecutar      rc de precondicion incumplida, no un fallo

La tercera es la que se pierde si se normaliza sin mirar. `xref.py` sale con
codigo 3 cuando el AST esta incompleto y lo dice en texto; si eso se traduje a
"sin referencias", una IA concluiria que `amdgpu_vm` no tiene referencias, que
es FALSO y es de las afirmaciones mas caras de este proyecto.

Cada normalizador devuelve (env, rc_de_salida). El rc lo decide el envelope, no
la herramienta: una capacidad no hereda el criterio de salida de su backend.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple

from api.envelope import (
    ST_BLOCKED, ST_EMPTY, ST_ERROR, ST_OK, Blocked, envelope,
)
from core import dispatch

ROOT = dispatch.ROOT


def _load(stdout: str, stderr: str) -> Any:
    """Saca JSON de una salida. Devuelve None si no hay, sin inventarlo.

    No se hace `json.loads` a lo bruto porque varias herramientas imprimen
    cabeceras antes del JSON (`reg_resolve.py` va directo, pero `xref.py` y
    `pm4ops.py` no). Se busca el primer `{` y se intenta desde ahi.
    """
    s = stdout.strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except ValueError:
        pass
    for i, ch in enumerate(s):
        if ch == "{":
            try:
                return json.loads(s[i:])
            except ValueError:
                continue
    return None


def _tool_used(a: "dispatch.Adapter", r: Dict[str, Any]) -> Dict[str, Any]:
    return {"tool": a.cmd[0], "path": os.path.relpath(a.path, ROOT),
            "rc": r["rc"], "argv_tail": r["argv"][2:]}


# MEDIDO 2026-10-05: el normalizador de RXRE-002 necesita el JSON CRUDO de la
# herramienta, y el envelope de RXRE-001 solo lleva los resultados ya
# interpretados. Sin esto, `core/engine.py` no tiene de donde normalizar y
# devuelve `resultados: 0` con `raw_resultados: 6166562` al lado, que es un
# resultado que no existe con ninguno de los dos numeros.
#
# Se anade bajo una clave CON PREFIJO, y el envelope lo borra antes de salir, de
# modo que la forma publica de RXRE-001 no cambia: ni una clave mas, ni una
# menos. Es un canal interno, no un campo del contrato.
_CLAVE_CRUDO = "_raw_json"


def _con_crudo(env: Dict[str, Any], d: Any) -> Dict[str, Any]:
    env = dict(env)
    env[_CLAVE_CRUDO] = d
    return env


def _sin_crudo(env: Dict[str, Any]) -> Dict[str, Any]:
    env = dict(env)
    env.pop(_CLAVE_CRUDO, None)
    return env


def _ran(r: Dict[str, Any]) -> bool:
    return not r.get("timeout") and r["rc"] is not None


# --- capabilities ----------------------------------------------------------

def capabilities(args: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    # MEDIDO: el probe usa 60s, NO el timeout de la operacion (300 por
    # defecto). Con 300, `capabilities` tardaba 302s. Con 60 tarda 0,4s.
    # El timeout de la linea de ordenes es para la OPERACION; el probe es
    # una comprobacion de vida y no tiene por que_gole el mismo presupuesto.
    rows = dispatch.probe_all(timeout=args.get("probe_timeout", 60))
    caps = [r["capability"] for r in rows if r.get("available")]
    bloqueadas = [r for r in rows if not r.get("available")]
    lim = []
    if bloqueadas:
        lim.append("%d capacidad(es) declarada(s) no responden: %s"
                   % (len(bloqueadas),
                      ", ".join("%s (%s)" % (r["capability"],
                                             r.get("reason", "sin razon"))
                                for r in bloqueadas)))
    # El universo, porque una capacidad sin corpus no puede responder nada y
    # es mejor que la IA lo sepa antes de preguntar.
    corpus = os.path.join(ROOT, "RESEARCH", "working", "linux-7.1.3")
    prov = [("corpus", corpus, os.path.isdir(corpus)),
            ("corpus_manifest",
             os.path.join(ROOT, "RESEARCH", "corpus-manifest.json"),
             os.path.isfile(os.path.join(ROOT, "RESEARCH", "corpus-manifest.json")))]
    for nom, ruta, ok in prov:
        if not ok:
            lim.append("el %s no esta presente: %s" % (nom, ruta))
    a = dispatch.get("capabilities")
    r = a.run(a.build(args), timeout=args.get("probe_timeout", 60))
    inv = _load(r["stdout"], r["stderr"])
    n_reg = 0
    if isinstance(inv, dict):
        n_reg = len(inv.get("attribution", []) or [])
    env = _con_crudo(envelope(
        "capabilities",
        target="rx550",
        status=ST_OK if caps else ST_EMPTY,
        results=rows,
        evidence=[{"kind": "corpus", "path": corpus, "present": os.path.isdir(corpus)},
                  {"kind": "instrumentos_registrados", "count": n_reg,
                   "source": "tools/toolreg.py"}],
        provenance=[{"tool": "toolreg.py", "rc": r["rc"]}],
        limitations=lim,
        tools_used=[_tool_used(a, r)],
    ), inv)
    return _sin_crudo(env), 0


# --- search / symbol -------------------------------------------------------

def search(args: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    return _busqueda(args, "search")


def symbol(args: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    return _busqueda(args, "symbol")


def _busqueda(args: Dict[str, Any], op: str) -> Tuple[Dict[str, Any], int]:
    a = dispatch.get(op)
    argv = a.build(args)
    r = a.run(argv, timeout=args.get("timeout", 300))
    if r.get("timeout"):
        return envelope(op, target=args.get("target"), status=ST_ERROR,
                        limitations=["timeout a los %ds" % args.get("timeout", 300)],
                        tools_used=[_tool_used(a, r)]), 1
    if not _ran(r):
        return envelope(op, target=args.get("target"), status=ST_ERROR,
                        limitations=["la herramienta no arranco: %s"
                                     % (r["stderr"] or "sin stderr").strip()],
                        tools_used=[_tool_used(a, r)]), 1
    d = _load(r["stdout"], r["stderr"])
    if d is None:
        return envelope(op, target=args.get("target"), status=ST_ERROR,
                        limitations=["la salida de %s no es JSON legible; "
                                     "no se inventa un resultado"
                                     % a.cmd[0]],
                        tools_used=[_tool_used(a, r)]), 1
    hits = d.get("hits", []) or []
    fp = d.get("universe_fingerprint")
    # MEDIDO 2026-10-05: `--max-hits` en `evidence_search.py` solo recorta la
    # IMPRESION de la seccion RESULT (linea 609, `hits[: args.max_hits]`). El
    # campo `hits` del JSON lleva TODO. Por eso pedir 3 devolvia 35: el limite
    # estaba puesto y no hacia nada en la salida estructurada.
    #
    #     un limite que solo recorta la pantalla no limita el dato
    #
    # Aqui se aplica de verdad, y se DECLARA cuando recorta, porque un conjunto
    # recortado en silencio es peor que uno completo: la IA contaria 3 y creeria
    # que solo hay 3.
    topes = args.get("max_hits")
    recortado = 0
    if topes and len(hits) > int(topes):
        recortado = len(hits) - int(topes)
        hits = hits[: int(topes)]
    lim_extra = ([] if not recortado else
                 ["la herramienta encontro %d coincidencias y se muestran %d: "
                  "el tope es de PRESENTACION de esa herramienta, no del universo"
                  % (len(hits) + recortado, len(hits))])
    # MEDIDO 2026-10-05: el recorte se aplicaba a `hits` (lo que va en
    # `results`), pero `_raw_json` seguia con las 35. El normalizador lee
    # `_raw_json`, asi que mutar el recorte -- o la lista entera -- no cambia NADA
    # de lo que sale. Es el defecto de RXRE-002 en otra guise: el camino probado
    # y el usado son distintos.
    #
    #     mutar al productor debe cambiar lo que ve el consumidor
    #
    # Se aplica la decision del handler TAMBIEN al canal que lee el
    # normalizador. `raw` sigue siendo fiel: es la salida de la herramienta con
    # el recorte que RXRE declara, no recortada a espaldas de nadie.
    d = dict(d)
    d["hits"] = hits
    return _con_crudo(envelope(
        op, target=args.get("target"),
        status=ST_OK if hits else ST_EMPTY,
        results=hits,
        evidence=[{"kind": "universe", "fingerprint": fp,
                   "declared": d.get("universe", {})},
                  {"kind": "classification", "value": d.get("classification"),
                   "reasons": d.get("reasons", [])}],
        provenance=[{"tool": a.cmd[0], "argv_tail": r["argv"][2:],
                     "universe_fingerprint": fp}],
        limitations=lim_extra + (
            [] if hits else
            ["coincidencia literal en el universo declarado (fingerprint %s); "
             "esto NO es ausencia demostrada: es que la cadena no aparece en "
             "las raices que se declararon" % (fp or "?")]),
        tools_used=[_tool_used(a, r)],
    ), d), 0


# --- register --------------------------------------------------------------

def register(args: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    a = dispatch.get("register")
    r = a.run(a.build(args), timeout=args.get("timeout", 300))
    if not _ran(r) or r["rc"] == 1:
        return envelope("register", target=args.get("target"), status=ST_ERROR,
                        limitations=["reg_resolve fallo: %s"
                                     % (r["stderr"] or "rc=%s" % r["rc"]).strip()[:200]],
                        tools_used=[_tool_used(a, r)]), 1
    d = _load(r["stdout"], r["stderr"])
    if d is None:
        return envelope("register", target=args.get("target"), status=ST_ERROR,
                        limitations=["salida no JSON de reg_resolve"],
                        tools_used=[_tool_used(a, r)]), 1
    res = d.get("results", []) or []
    lim: List[str] = []
    # La unidad. reg_resolve la declara y sin ella un offset no es un offset.
    ud = d.get("unit_declaration")
    if ud:
        lim.append("unidad: %s (%s) -> %s" % (ud.get("quote"),
                                              ud.get("file"), ud.get("consequence")))
    for x in res:
        v = x.get("verdict", "")
        if v == "PROVEN_ABSENT_EN_ASIC_REG" and x.get("note"):
            # Aqui el ausente es real y esta acotado: es ausencia de DEFINICION
            # en asic_reg, no de hardware. Se conserva el texto de la herramienta.
            lim.append("%s: %s" % (x.get("symbol"), x["note"]))
    return _con_crudo(envelope(
        "register", target=args.get("target"),
        status=ST_OK if res else ST_EMPTY,
        results=res,
        evidence=[{"kind": "gfx", "value": d.get("gfx")},
                  {"kind": "amd_root", "path": d.get("amd_root")}],
        provenance=[{"tool": "reg_resolve.py", "version": d.get("version"),
                     "argv_tail": r["argv"][2:]}],
        limitations=lim, tools_used=[_tool_used(a, r)],
    ), d), 0


# --- xref / trace ----------------------------------------------------------

def xref(args: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    a = dispatch.get("xref")
    r = a.run(a.build(args), timeout=args.get("timeout", 300))
    # xref.py sale con 3 y explica por que: el AST esta a medias. Eso es
    # BLOCKED, no EMPTY. Es la distincion mas cara de todo este modulo.
    if r["rc"] == 3 or not _ran(r):
        txt = (r["stdout"] + r["stderr"]).strip()
        return envelope(
            "xref", target=args.get("target"), status=ST_BLOCKED,
            limitations=[
                "xref.py no puede construir el AST: el arbol esta a medias y "
                "completarlo es una ESCRITURA en el arbol de fuentes. "
                "NO se ejecuta, y por tanto NO hay resultado. Esto NO es "
                "'el simbolo no tiene referencias'.",
                "detalle de la herramienta: %s" % (txt.splitlines()[0] if txt else "sin texto"),
            ],
            tools_used=[_tool_used(a, r)],
        ), 2
    d = _load(r["stdout"], r["stderr"])
    res = []
    if isinstance(d, dict):
        res = d.get("results") or d.get("refs") or d.get("callers") or []
    return envelope(
        "xref", target=args.get("target"),
        status=ST_OK if res else ST_EMPTY,
        results=res, provenance=[{"tool": "xref.py"}],
        tools_used=[_tool_used(a, r)]), 0


def trace(args: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    a = dispatch.get("trace")
    r = a.run(a.build(args), timeout=args.get("timeout", 300))
    if r.get("timeout") or not _ran(r):
        return envelope("trace", target=args.get("target"), status=ST_ERROR,
                        limitations=["trace_path no se pudo ejecutar: rc=%s"
                                     % r["rc"]],
                        tools_used=[_tool_used(a, r)]), 1
    d = _load(r["stdout"], r["stderr"])
    res = []
    if isinstance(d, dict):
        res = d.get("chain") or d.get("results") or d.get("nodes") or []
    # MEDIDO 2026-10-05: `trace_path.py` devuelve UN resultado con
    # `"verdict": "NO_ENCONTRADO"`, no una lista vacia. Traducirlo a `status=ok`
    # con un resultado es technically cierto y praticamente una trampa: una IA
    # ve un resultado y se va. El veredicto por nodo se sube a `limitations`, que
    # es donde se lee lo que no se encontro.
    #
    #     un resultado que dice NO_ENCONTRADO no es un resultado
    lim: List[str] = []
    sin_encontrar = [x for x in res if isinstance(x, dict)
                     and x.get("verdict") == "NO_ENCONTRADO"]
    if sin_encontrar:
        lim.append("trace_path NO encontro el simbolo en el subarbol indexado "
                   "(%d nodo(s) con verdict=NO_ENCONTRADO, sin hijos). El "
                   "subarbol indexado es lo que la herramienta declara haber "
                   "recorrido, no el arbol entero." % len(sin_encontrar))
    return _con_crudo(envelope(
        "trace", target=args.get("target"),
        status=ST_OK if (res and not sin_encontrar) else ST_EMPTY,
        results=[] if sin_encontrar else res,
        provenance=[{"tool": "trace_path.py", "argv_tail": r["argv"][2:]}],
        limitations=lim, tools_used=[_tool_used(a, r)]), d), 0


# --- pm4 / evidence / provenance ------------------------------------------

def pm4(args: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    a = dispatch.get("pm4")
    r = a.run(a.build(args), timeout=args.get("timeout", 300))
    d = _load(r["stdout"], r["stderr"])
    if d is None:
        # pm4ops.py imprime una tabla, no JSON. Se devuelve el texto como un
        # unico resultado y se DICE que no es JSON, en vez de fingir.
        return envelope(
            "pm4", target=args.get("target"),
            status=ST_OK if r["stdout"].strip() else ST_ERROR,
            results=[{"kind": "texto", "contenido": r["stdout"]}] if r["stdout"].strip() else [],
            limitations=["pm4ops.py no emite JSON: se devuelve su salida como "
                         "texto, sin reinterpretar"],
            tools_used=[_tool_used(a, r)]), 0 if r["stdout"].strip() else 1
    return envelope("pm4", target=args.get("target"), status=ST_OK,
                    results=d if isinstance(d, list) else [d],
                    tools_used=[_tool_used(a, r)]), 0


def evidence(args: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    # `evidence` es `search` con la clasificacion a la vista: misma
    # herramienta, mismo universo, y el envelope pone la clasificacion en
    # `evidence` en vez de esconderla en `results`.
    env, rc = _busqueda(dict(args, target=args.get("target", "")), "evidence")
    return env, rc


def provenance(args: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    a = dispatch.get("provenance")
    r = a.run(a.build(args), timeout=args.get("timeout", 300))
    if not _ran(r):
        return envelope("provenance", status=ST_ERROR,
                        limitations=["prov.py no arranco: rc=%s" % r["rc"]],
                        tools_used=[_tool_used(a, r)]), 1
    # MEDIDO 2026-10-05: `prov.py --json` NO emite la tabla de texto; emite un
    # objeto con claves tipo "D1_pct". Con `--claves` emite la tabla. Se leen las
    # dos formas, y se dice cual se uso, porque el consumidor tiene que saber si
    # mira un recuento de apariciones o un porcentaje de cobertura.
    filas: List[Dict[str, Any]] = []
    forma = "texto"
    d = _load(r["stdout"], r["stderr"])
    if isinstance(d, dict):
        forma = "json"
        for k, vv in d.items():
            if k.endswith("_pct") and isinstance(vv, (int, float)):
                filas.append({"clave": k[:-4], "pct": vv,
                              "sin": d.get(k[:-4] + "_sin")})
        # RXRE-1644: `lim_pct` tiene que ser una LISTA. Estaba escrita como
        # str y el envelope hace `list(limitations or [])`, que sobre un str
        # da sus CARACTERES: la limitacion salia como 163 elementos de una
        # letra, no como una frase. `limitations` es `List[str]` en el
        # contrato del envelope; este camino lo violaba en silencio.
        lim_pct = ["`prov.py --json` devuelve PORCENTAJES de claves que cumplen "
                   "el contrato, no un recuento de apariciones. Para el "
                   "recuento, `rxre provenance` usa `prov.py --claves`."]
    else:
        for ln in r["stdout"].splitlines():
            pp = ln.split(None, 1)
            if len(pp) == 2 and pp[0].isdigit():
                filas.append({"clave": pp[1].strip(), "ocurrencias": int(pp[0])})
        lim_pct = []
    return _con_crudo(envelope(
        "provenance", status=ST_OK if filas else ST_EMPTY,
        results=filas,
        evidence=[{"kind": "directorio", "path": args.get("dir") or ROOT}],
        provenance=[{"tool": "prov.py", "forma_salida": forma}],
        limitations=lim_pct,
        tools_used=[_tool_used(a, r)]), d), 0




def register_fields(args: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    a = dispatch.get("register-fields")
    r = a.run(a.build(args), timeout=args.get("timeout", 300))
    if not _ran(r) or r["rc"] == 1:
        return envelope("register-fields", target=args.get("target"), status=ST_ERROR,
                        limitations=["rxre_register_fields fallo: %s"
                                     % (r["stderr"] or "rc=%s" % r["rc"]).strip()[:200]],
                        tools_used=[_tool_used(a, r)]), 1
    d = _load(r["stdout"], r["stderr"])
    if d is None:
        return envelope("register-fields", target=args.get("target"), status=ST_ERROR,
                        limitations=["salida no JSON de rxre_register_fields"],
                        tools_used=[_tool_used(a, r)]), 1
    res = d.get("fields", []) or []
    return _con_crudo(envelope(
        "register-fields", target=args.get("target"),
        status=ST_OK if res else ST_EMPTY,
        results=res,
        evidence=[{"kind": "gfx", "value": d.get("gfx")},
                  {"kind": "amd_root", "path": d.get("amd_root")}],
        provenance=[{"tool": "rxre_register_fields.py", "version": d.get("version"),
                     "argv_tail": r["argv"][2:]}],
        limitations=d.get("limitations", []),
        tools_used=[_tool_used(a, r)],
    ), d), 0


def trace_data(args: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    a = dispatch.get("trace_data")
    r = a.run(a.build(args), timeout=args.get("timeout", 300))
    if not _ran(r):
        return envelope("trace_data", target=args.get("target"),
                        status=ST_ERROR,
                        limitations=["rxre_trace_data no se pudo ejecutar: rc=%s" % r["rc"]],
                        tools_used=[_tool_used(a, r)]), 1
    d = _load(r["stdout"], r["stderr"])
    if d is None:
        return envelope("trace_data", target=args.get("target"),
                        status=ST_ERROR,
                        limitations=["salida no JSON de rxre_trace_data"],
                        tools_used=[_tool_used(a, r)]), 1
    res = d.get("results", []) or []
    lim: List[str] = list(d.get("limitations", []))
    if d.get("status") == "not_found":
        lim.append("no se encontraron accesos al registro/funcion en el corpus")
    return _con_crudo(envelope(
        "trace_data", target=args.get("target"),
        status=ST_OK if res else ST_EMPTY,
        results=res,
        evidence=[{"kind": "gfx", "value": d.get("gfx")},
                  {"kind": "tool_version", "value": d.get("version")}],
        provenance=[{"tool": "rxre_trace_data.py", "argv_tail": r["argv"][2:]}],
        limitations=lim,
        tools_used=[_tool_used(a, r)],
    ), d), 0


def _validar_contrato_defuse(d: Any) -> List[str]:
    """Valida el contrato de salida de lachesis_defuse.py ANTES
    de envolverlo en el envelope.

    El adaptador tiene su propio contrato (capas, resultados con
    estado epistemico, limitaciones). Un adaptador que no lo cumple
    no se envuelve: envolver una forma desconocida produce un
    envelope que miente sobre lo que se ejecuto.
    """
    if not isinstance(d, dict):
        return ["la salida no es un objeto"]
    errs: List[str] = []
    for k in ("tool", "version", "operation", "intent", "subject",
              "layers", "results", "limitations", "tools_used"):
        if k not in d:
            errs.append("falta %s" % k)
    if d.get("operation") != "defuse":
        errs.append("operation: se esperaba 'defuse', se recibio %r"
                    % d.get("operation"))
    if not isinstance(d.get("layers"), dict):
        errs.append("layers: no es objeto")
    if not isinstance(d.get("results"), list):
        errs.append("results: no es lista")
    else:
        for i, r in enumerate(d["results"]):
            if not isinstance(r, dict):
                errs.append("results[%d]: no es objeto" % i)
            elif "state" not in r:
                errs.append("results[%d]: falta state (estado "
                            "epistemico)" % i)
    return errs


def defuse(args: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """`defuse`: flujo de datos interprocedural via Lachesis.

    El adaptador ya clasifica (capa nativa / proveedor / dataflow,
    con estado epistemico por resultado). Este handler NO
    reinterpreta: valida el contrato del adaptador, envuelve, y
    deja que las capas viajen en `evidence`, que es donde el
    consumidor lee quien produjo que capa.

    Los codigos de salida del adaptador son los del VEREDICTO
    (0 ok/empty, 1 error, 2 blocked), y aqui se respetan: un
    `error` del proveedor NUNCA se convierte en `empty`, porque
    "el proveedor fallo" y "el proveedor no encontro" son
    respuestas distintas (la que cuesta caro es confundirlas).
    """
    a = dispatch.get("defuse")
    # El presupuesto de la OPERACION (subproceso completo) es
    # distinto del presupuesto por consulta del proveedor:
    # `def-use` de un registro ejecuta find-entity +
    # value-history por identidad, y una consulta mide ~65 s.
    # El default generico de 300 s mata la operacion antes de
    # que el adaptador termine, y eso NO es un resultado.
    timeout = args.get("adapter_timeout", 900)
    r = a.run(a.build(args), timeout=timeout)
    if r.get("timeout"):
        return envelope("defuse", target=args.get("target"),
                        status=ST_ERROR,
                        limitations=["timeout a los %ds" % timeout],
                        tools_used=[_tool_used(a, r)]), 1
    if not _ran(r):
        return envelope("defuse", target=args.get("target"),
                        status=ST_ERROR,
                        limitations=["lachesis_defuse no arranco: %s"
                                     % (r["stderr"] or "sin stderr").strip()],
                        tools_used=[_tool_used(a, r)]), 1
    d = _load(r["stdout"], r["stderr"])
    if d is None:
        return envelope("defuse", target=args.get("target"),
                        status=ST_ERROR,
                        limitations=["salida no JSON de "
                                     "lachesis_defuse.py"],
                        tools_used=[_tool_used(a, r)]), 1
    errs = _validar_contrato_defuse(d)
    if errs:
        return envelope("defuse", target=args.get("target"),
                        status=ST_ERROR,
                        limitations=["el contrato de lachesis_defuse.py "
                                     "no se cumple: %s"
                                     % "; ".join(errs[:5])],
                        tools_used=[_tool_used(a, r)]), 1
    if r["rc"] == 2:
        # blocked: precondicion no cumplida (falta grafo, corpus o
        # lachesis). El adaptador ya dijo el detalle en su JSON.
        detalle = ((d.get("error") or {}).get("detail")
                   or (d.get("limitations") or ["sin detalle"])[0])
        return envelope("defuse", target=args.get("target"),
                        status=ST_BLOCKED,
                        limitations=[detalle],
                        tools_used=[_tool_used(a, r)]), 2
    if r["rc"] == 1:
        # error: el proveedor o la capa nativa fallo. Con detalle,
        # nunca como empty.
        e = d.get("error") or {}
        return envelope("defuse", target=args.get("target"),
                        status=ST_ERROR,
                        limitations=["%s: %s" % (e.get("class", "?"),
                                                e.get("detail",
                                                      "sin detalle"))],
                        tools_used=[_tool_used(a, r)]), 1
    res = d.get("results", [])
    ev: List[Dict[str, Any]] = []
    for nombre, capa in (d.get("layers") or {}).items():
        fila: Dict[str, Any] = {"kind": "capa_%s" % nombre,
                                  "producer": capa.get("producer"),
                                  "status": capa.get("status")}
        if capa.get("verdict"):
            fila["verdict"] = capa.get("verdict")
        if capa.get("question"):
            fila["question"] = capa.get("question")
        ev.append(fila)
    lim = list(d.get("limitations") or [])
    if not res and not lim:
        lim = ["la operacion se ejecuto sin resultados; esto NO es "
               "ausencia demostrada: el proveedor no tiene nocion de "
               "universo exhaustivo"]
    return _con_crudo(envelope(
        "defuse", target=args.get("target"),
        status=ST_OK if res else ST_EMPTY,
        results=res,
        evidence=ev,
        provenance=[{"tool": "reg_resolve.py",
                     "kernel": args.get("kernel") or ""},
                    {"tool": "lachesis", "via": "CLI por subproceso",
                     "licencia": "AGPL-3.0 (proceso externo, no "
                                 "vendorizado)"}],
        limitations=lim,
        tools_used=[_tool_used(a, r)]), d), 0


HANDLERS = {
    "capabilities": capabilities,
    "search": search,
    "symbol": symbol,
    "register": register,
    "xref": xref,
    "trace": trace,
    "pm4": pm4,
    "evidence": evidence,
    "provenance": provenance,
    "register-fields": register_fields,
    "trace_data": trace_data,
    "defuse": defuse,
}