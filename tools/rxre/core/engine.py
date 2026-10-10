#!/usr/bin/env python3
"""FASE C. Despacho de operaciones, y FASE F. Composicion.

POR QUE UN DESPACHADOR NUEVO Y NO UNA TABLA MAS.

RXRE-001 tiene `commands/handlers.py` con una funcion por capacidad, y funciona.
Lo que no tiene es el camino desde una INTENCION hasta varios pasos. Una IA que
pregunta "¿quién escribe este registro?" necesita tres llamadas encadenadas y
saber en que orden, y eso es composicion, no una capacidad mas.

La composicion es DELIBERADAMENTE DETERMINISTA. No hay planificador, no hay
heuristica, no hay eleccion. El pipeline esta escrito, se ejecuta en orden y
cada etapa declara que esquema espera y que devuelve. La razon esta en §19 y
§26: la IA es la que decide; RXRE es la que ejecuta. Si el pipeline eligiera
pasos por su cuenta, dos preguntas parecidas darian rutas distintas y nadie
podria reproducir por que se respondio lo que se respondio.

Y hay una regla sobre el fallo intermedio, que es la que hace que esto sirva de
algo y no sea decorativo:

    una etapa vacia NO para la composicion; una etapa bloqueada SI se propaga

    un `empty` en la etapa 1 no dice que la 2 no pueda correr: la 2 es una
    pregunta distinta. un `blocked` en la etapa 1 si dice que la 2 no tiene
    sentido, porque 2 depende de lo que 1 iba a dar.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional, Tuple

from core import dispatch

from api import envelope as E
from api.request import envolver
from core import capabilities as caps
from core import normalize as N

# --- ejecucion de una capacidad existente ---------------------------------

def _args_de_operacion(op: str, request: Dict[str, Any]) -> Dict[str, Any]:
    """Traduce `inputs` del contrato a los argumentos que RXRE-001 ya entiende.

    No se inventa un vocabulario nuevo: se mapea al que ya usa el CLI, para que
    la misma capacidad se pueda pedir por las dos vias y ambos caminos den el
    mismo resultado.
    """
    i = request.get("inputs") or {}
    return {
        # MEDIDO 2026-10-05: con un `target` vacio, `_b_search` monta
        # `--query ''`, y evidence_search con la cadena vacia casa con TODO el
        # universo: eso produjo 6166562 resultados y 863s. Un `target` ausente
        # tiene que ser un error ANTES de ejecutar, no una busqueda de la cadena
        # vacia.
        "target": i.get("target") or i.get("register_name")
                  or i.get("symbol_name") or i.get("query") or "",
        "max_hits": i.get("max_hits", 20),
        "depth": i.get("depth", 3),
        "gfx": i.get("gfx", "gfx_8_0"),
        "field": i.get("field"),
        "dir": i.get("dir"),
        "timeout": i.get("timeout", 300),
        "probe_timeout": i.get("probe_timeout", 60),
        # RXRE-1630: `defuse` habla el contrato de
        # lachesis_defuse.py. Estas entradas viajan al
        # adaptador sin reinterpretarlas: el adaptador es
        # quien sabe que significan. `intent` es la
        # pregunta (symbol/def-use/value-history/
        # bit-semantics); `graph`/`corpus` son la
        # precondicion del proveedor; `kernel` la raiz de
        # la capa nativa; `ip_block`/`address` la
        # desambiguacion por identidad de registro;
        # `lachesis_bin` y `budget_tokens` el transporte.
        # `adapter_timeout` es el presupuesto de la
        # OPERACION (el subproceso completo), y es distinto
        # de `timeout`: una operacion `def-use` de un registro
        # ejecuta find-entity + value-history por identidad,
        # y una consulta mide ~65 s, con lo que 4 consultas
        # superan el default generico de 300 s.
        "intent": i.get("intent"),
        "ip_block": i.get("ip_block"),
        "address": i.get("address"),
        "graph": i.get("graph"),
        "corpus": i.get("corpus"),
        "kernel": i.get("kernel"),
        "lachesis_bin": i.get("lachesis_bin"),
        "budget_tokens": i.get("budget_tokens"),
        "build_timeout": i.get("build_timeout"),
        "adapter_timeout": i.get("adapter_timeout"),
    }


def ejecutar_operacion(op: str, request: Dict[str, Any]) -> Dict[str, Any]:
    """Ejecuta UNA capacidad de RXRE-001 bajo el contrato de RXRE-002."""
    from commands import handlers  # import tardio: evita ciclo con cli
    fn = handlers.HANDLERS.get(op)
    if not fn:
        return E.envelope(op, target=request.get("target"), status=E.ST_ERROR,
                          limitations=["operacion desconocida: %s" % op])
    env, _rc = fn(_args_de_operacion(op, request))
    env["operation"] = op
    return env


# --- FASE F: pipelines deterministas ---------------------------------------
# Cada pipeline es una lista de etapas. Cada etapa dice que operacion es y que
# de la anterior necesita. Se ejecutan SIEMPRE en orden y su salida se acumula.

Pipelines: Dict[str, List[Dict[str, Any]]] = {
    # "¿Dónde está y quién lo escribe?" search -> register -> (patron)
    "register.writers": [
        {"step": "definition", "op": "register", "needs": ["target"]},
        {"step": "occurrences", "op": "search", "needs": ["target"]},
    ],
    "register.readers": [
        {"step": "definition", "op": "register", "needs": ["target"]},
        {"step": "occurrences", "op": "search", "needs": ["target"]},
    ],
    "register.uses": [
        {"step": "definition", "op": "register", "needs": ["target"]},
        {"step": "occurrences", "op": "search", "needs": ["target"]},
    ],
    "register.definition": [
        {"step": "definition", "op": "register", "needs": ["target"]},
    ],
    # search -> trace, para anadir la cadena de llamadas a lo que hay.
    "symbol.callers": [
        {"step": "occurrences", "op": "search", "needs": ["target"]},
        {"step": "callchain", "op": "trace", "needs": ["target"]},
    ],
    "symbol.callgraph": [
        {"step": "callchain", "op": "trace", "needs": ["target"]},
    ],
    "symbol.locate": [
        {"step": "occurrences", "op": "search", "needs": ["target"]},
    ],
    "value.defuse": [
        {"step": "dataflow", "op": "defuse", "needs": ["target"]},
    ],
    "pm4.opcodes": [{"step": "census", "op": "pm4", "needs": []}],
    "provenance.keys": [{"step": "keys", "op": "provenance", "needs": []}],
    "project.capabilities": [{"step": "inventory", "op": "capabilities", "needs": []}],
    "evidence.search": [
        {"step": "occurrences", "op": "search", "needs": ["target"]},
    ],
}


def _es_ausencia_acotada(resultados: List[Dict[str, Any]]) -> bool:
    """Todos los resultados son ausencias acotadas, y hay alguno.

    "Acotada" significa que el veredicto de la herramienta dice explicitly QUE
    no se encontro y DONDE. `PROVEN_ABSENT_EN_ASIC_REG` es de ese tipo: la
    ausencia esta en la tabla de offsets, no en el hardware.

    Y hace falta que HAYA alguno: una lista vacia no es una ausencia acotada, es
    un vacio, que es un estado distinto y ya lo trata el envelope.
    """
    if not resultados:
        return False
    for r in resultados:
        if not isinstance(r, dict):
            return False
        raw = r.get("raw") or {}
        ver = raw.get("verdict") if isinstance(raw, dict) else None
        if not (isinstance(ver, str) and ver.startswith("PROVEN_ABSENT")):
            return False
    return True


def _capa_de_busqueda(d: Dict[str, Any], tope: int) -> Dict[str, Any]:
    """El JSON crudo de `search`, recortado al tope que se pidió.

    MEDIDO 2026-10-05: `evidence_search.py --max-hits` recorta SOLO la
    impresion (su linea 609, `hits[: args.max_hits]`); el campo `hits` del JSON
    lleva los 35 completos. El handler ya recorta `env["results"]`, pero el
    NORMALIZADOR leia `_raw_json`, que seguia entero. Resultado: pedia 3 y el
    envelope final llevaba 35 normalizados.

        un limite que solo recorta la pantalla no limita el dato

    Se recorta aqui, sobre una COPIA, y no en el `_raw_json` que se guarda: el
    raw tiene que conservar lo que la herramienta dijo, no lo que nosotros
    decidimos mostrar.
    """
    d = dict(d or {})
    hits = d.get("hits") or []
    if tope and len(hits) > int(tope):
        d["hits"] = list(hits[: int(tope)])
        d["_recortado"] = len(hits) - int(tope)
    return d


def _normaliza_paso(step: str, env: Dict[str, Any], request: Dict[str, Any]
                    ) -> List[Dict[str, Any]]:
    """Convierte la salida de un paso en resultados normalizados."""
    op = env.get("operation", "")
    res: List[Dict[str, Any]] = []
    a = dispatch.ADAPTERS.get(op)
    if a is None:
        return res
    # MEDIDO 2026-10-05: el JSON crudo viaja en `_raw_json`, que el handler
    # anade y `api.envelope` NO borra. Antes se leia `_json`, que no existia, y
    # por eso `resultados: 0` salia con `raw_resultados: 6166562` al lado.
    d = env.get("_raw_json")
    if not isinstance(d, dict):
        # MEDIDO 2026-10-05: `pm4` y `capabilities` no emiten JSON parseable
        # (`pm4ops.py` imprime una tabla), asi que `_raw_json` es `None` y el
        # paso se quedaba con cero resultados normalizados mientras la etapa
        # decia `ok` con uno crudo. El pipeline era correcto y la composicion
        # invisible: una etapa que dice ok y no aporta nada.
        if op in ("pm4", "capabilities"):
            for x in (env.get("results") or []):
                if isinstance(x, dict) and x.get("kind") == "texto":
                    res.append(N.resultado(
                        "%s_census" % op, x.get("contenido", ""),
                        tool=a.cmd[0], status="observed", raw=x,
                        limitations=["la fuente emite una TABLA, no JSON: el "
                                     "valor es el texto de la herramienta, sin "
                                     "reinterpretar"]))
                elif isinstance(x, dict):
                    res.append(N.resultado("%s_item" % op, x, tool=a.cmd[0],
                                           status="observed", raw=x))
        # `provenance` SI emite JSON, pero con una forma propia: filas
        # `{clave, pct, sin}`. `_raw_json` es el dict, y cae en el
        # `return` de abajo: por eso devolvia cero resultados normalizados
        # teniendo tres filas. MEDIDO, con el fixture como detector.
        elif op == "provenance":
            for k, val in sorted((d or {}).items()):
                if isinstance(val, dict) or isinstance(val, (int, float)):
                    res.append(N.resultado(
                        "provenance_key",
                        {"clave": k, "pct": val,
                         "sin": d.get(str(k) + "_sin")},
                        tool=a.cmd[0], status="observed",
                        entrada={"dir": (request.get("inputs") or {}).get("dir")},
                        raw={k: val},
                        limitations=["porcentaje de claves que cumplen el "
                                     "contrato; NO es un recuento de "
                                     "apariciones"]))
        return res
    if op in ("search", "symbol", "evidence"):
        tope = (request.get("inputs") or {}).get("max_hits")
        d = _capa_de_busqueda(d, tope)
        res = N.de_busqueda(d)
    elif op == "register":
        res = N.de_registro(d)
    elif op == "trace":
        for n in (d.get("results") or d.get("chain") or []):
            if isinstance(n, dict):
                res.extend(N.de_arbol_trace(n))
    elif op == "defuse":
        res = N.de_defuse(d)
    elif op == "provenance":
        # MEDIDO 2026-10-05: `provenance` SI emite JSON, con forma propia:
        # `{"D1_pct": 85.7, "D1_sin": 6, ..., "tokens": {...}, "claves": {...}}`.
        # El fixture lo delato: pedia tres claves y recibia cero resultados, con
        # la etapa en `ok`.
        #
        # NORMALIZA DESDE `env["results"]`, NO DESDE `_raw_json`. Se probo al
        # reves y las MUTACIONES DEL HANDLER DEJABAN DE NOTARSE: el handler
        # devuelve `pct: 0.0` y la respuesta seguia dando 85.7.
        #
        #     un normalizador que relee el dato crudo ignora al que lo produce
        #
        # La razon de fondo es que hay DOS representaciones y una sola es la
        # que el consumidor ve: si el normalizador usa la que no ve nadie, el
        # camino que se prueba y el camino que se usa son distintos, y mutar el
        # handler no cambia lo que sale. Eso es una suite que mide otra cosa.
        #
        # El significado de `pct` lo pone `prov.py`; se copia con su limitacion
        # para que el consumidor no lea un porcentaje como si fuera un recuento.
        for x in (env.get("results") or []):
            if not isinstance(x, dict) or "clave" not in x:
                continue
            res.append(N.resultado(
                "provenance_key", dict(x), tool=a.cmd[0], status="observed",
                entrada={"dir": (request.get("inputs") or {}).get("dir")},
                raw=dict(x),
                limitations=["`pct` es el porcentaje de claves que cumplen el "
                             "contrato, NO un recuento de apariciones"]))
        return res
    return res


def _dedup_por_clave(seq: List[Any]) -> List[Any]:
    """Deduplica entries de evidence/provenance por su forma
    canonica. Dos etapas que citan la misma herramienta con
    el mismo artifacto son UN hecho de procedencia, no dos:
    duplicar provenance infla artificialmente la confianza
    que un consumidor podria derivar del conteo."""
    vista: set = set()
    out: List[Any] = []
    for x in seq:
        clave = (json.dumps(x, sort_keys=True, default=str)
                 if isinstance(x, dict) else x)
        if clave not in vista:
            vista.add(clave)
            out.append(x)
    return out


def _dedup_str(seq: List[str]) -> List[str]:
    vista: set = set()
    out: List[str] = []
    for x in seq:
        if x not in vista:
            vista.add(x)
            out.append(x)
    return out


def ejecutar_pipeline(cap: str, request: Dict[str, Any]) -> Dict[str, Any]:
    """Ejecuta el pipeline de una capacidad, con estado por etapa.

    La salida es un envelope con `results` = resultados normalizados de todas las
    etapas, y `stages` = el detalle de cada una con su estado. Las etapas van
    en `stages` y no solo en provenance porque una IA necesita ver DONDE se
    corto, no solo que se corto.
    """
    pasos = Pipelines.get(cap)
    if pasos is None:
        return E.envelope(cap, target=request.get("target"), status=E.ST_ERROR,
                          limitations=["no hay pipeline para la capacidad %s" % cap,
                                       "capacidades con pipeline: %s"
                                       % ", ".join(sorted(Pipelines))])

    tgt = request.get("target", "")
    etapas: List[Dict[str, Any]] = []
    resultados: List[Dict[str, Any]] = []
    estado_global = E.ST_OK
    bloqueos: List[str] = []
    # RXRE-1630: la evidence, la provenance y las limitaciones
    # que produce UNA ETAPA son parte de la respuesta, no
    # detalle interno. Hasta aqui el envelope final las
    # descartaba (evidence solo de la capacidad, provenance
    # vacia, limitations solo de bloqueos), y el consumidor
    # de la maquina recibia una caja negra: veia el resultado
    # pero no que capa lo produjo, con que herramienta, ni
    # que se habia declarado sobre el. Eso rompe la cadena
    # de procedencia (§14) en la frontera pipeline. Se
    # acumulan por etapa y se propagan al envelope final,
    # deduplicadas: mas informacion de procedencia nunca
    # fue un error, y ocultarla si lo es.
    evidencia: List[Dict[str, Any]] = []
    provenencia: List[Dict[str, Any]] = []
    limitaciones: List[str] = []

    for p in pasos:
        sub = dict(request)
        # MEDIDO 2026-10-05: `max_hits` se perdia en la frontera pipeline ->
        # etapa. `responder()` lo escribe en `req["inputs"]`, pero aqui se
        # re-copia `request.get("inputs")` y `request` es el dict ORIGINAL, que
        # todavia no tiene el techo aplicado. Resultado: pedia 3 y recibia 35,
        # y el limite del contrato no existia.
        #
        #     un limite escrito en el request y no propagado no es un limite
        sub["inputs"] = dict(request.get("inputs") or {})
        env = ejecutar_operacion(p["op"], sub)
        norm = _normaliza_paso(p["step"], env, request)
        resultados.extend(norm)
        evidencia.extend(env.get("evidence") or [])
        provenencia.extend(env.get("provenance") or [])
        limitaciones.extend(env.get("limitations") or [])
        etapas.append({
            "step": p["step"], "op": p["op"], "status": env.get("status"),
            "resultados": len(norm),
            "raw_resultados": len(env.get("results") or []),
            "limitations": env.get("limitations") or [],
        })
        if env.get("status") == E.ST_BLOCKED:
            # Un bloqueo se propaga: la etapa siguiente depende de esta.
            estado_global = E.ST_BLOCKED
            bloqueos.extend(env.get("limitations") or [])
            break
        if env.get("status") == E.ST_ERROR:
            estado_global = E.ST_ERROR
            bloqueos.extend(env.get("limitations") or [])
            break
        if env.get("status") == E.ST_EMPTY and not resultados:
            estado_global = E.ST_EMPTY

    # MEDIDO 2026-10-05: una etapa puede responder `ok` con un resultado cuyo
    # veredicto es `PROVEN_ABSENT_EN_ASIC_REG`. `register` lo hace para un
    # simbolo que no existe, porque "no hay definicion de offset en asic_reg" SI
    # es una respuesta correcta. Sin esta regla, el pipeline devolvia
    # `status: ok` con ese resultado, y una IA leia "hay un hallazgo" donde lo
    # que hay es una AUSENCIA ACOTADA.
    #
    #     un PROVEN_ABSENT acotado no es un hallazgo
    #
    # Se decide AL FINAL y sobre el estado GLOBAL: una etapa vacia no hunde a
    # otra con hallazgo real, y un PROVEN_ABSENT al principio no anula un
    # `search` que si encontro usos.
    ausencias = []
    if resultados and _es_ausencia_acotada(resultados):
        estado_global = E.ST_EMPTY
        ausencias.append(
            "ningun resultado es un hallazgo: todos llevan un veredicto de "
            "ausencia ACOTADA (PROVEN_ABSENT_*), que acota lo que no se encontro "
            "a la tabla de definiciones consultada. Eso NO es que el objeto no "
            "exista en el hardware")

    env_out = E.envelope(
        cap, target=tgt, status=estado_global, results=resultados,
        evidence=_dedup_por_clave(
            [{"kind": "capability", "value": cap,
              "resolved_by": [p["op"] for p in pasos],
              "resolved_from":
                  request.get("question") or ""}]
            + evidencia),
        provenance=_dedup_por_clave(provenencia),
        limitations=_dedup_str(limitaciones + bloqueos
                               + ausencias),
    )
    env_out["stages"] = etapas
    return env_out
