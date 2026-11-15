#!/usr/bin/env python3
"""RXRE-007 FASE 1. El catalogo de lo que RXRE puede PREGUNTAR.

GENERADO, NO ESCRITO A MANO
---------------------------
MEDIDO 2026-10-14: las 25 capacidades de aqui son las que el registry de
RXRE declara, y `resolved_by` son los producers que las resuelven SEGUN EL
REGISTRY, leidos en runtime. Nada de esta tabla se ha escrito por Taste: si
el registry y esta tabla se contradijeran, el registry manda y esta tabla
esta mal.

QUE ES ESTA TABLA Y QUE NO ES
-----------------------------
Es una tabla de PREGUNTAS, no de hechos. Una fila dice "esto es lo que se
puede preguntar y por quien se puede responder", y nada mas. Deliberadamente
NO dice que significa ningun valor: `question` esta libre de "value is",
"byte offset" y "dword" porque una pregunta que afirma semantica ya ha
respondido antes de medir. T0405 comprueba exactamente eso.

`requires` describe lo que hace falta para responder, derivado del namespace
(que en RXRE es una agrupacion real): `binary.*` necesita un artefacto,
`gpu.*` necesita un target, `rxre.*` necesita evidencia previa, `source.*`
necesita el corpus.

GENERADO: backends.registry (estado real de cada producer)
"""
from __future__ import annotations

#: Fecha y forma de la extraccion, para que se pueda re-derivar.
GENERADO_DESDE = "backends.registry + backends.dispatch._todas_las_fichas()"
GENERADO_EL = "2026-10-14T07:31:00-0300"

CAPACIDADES = [{'capability': 'binary.basic_blocks',
  'question': 'como se divide el control de flujo de una funcion',
  'requires': {'artefacto': True,
               'target': False,
               'evidencia_previa': False,
               'corpus': False},
  'resolved_by': ['radare2', 'rizin'],
  'gfx_generation': 'gfx_8_0'},
 {'capability': 'binary.callgraph',
  'question': 'que funciones se llaman entre si',
  'requires': {'artefacto': True,
               'target': False,
               'evidencia_previa': False,
               'corpus': False},
  'resolved_by': ['radare2', 'rizin'],
  'gfx_generation': 'gfx_8_0'},
 {'capability': 'binary.cfg',
  'question': 'como se conecta el control de flujo entre bloques',
  'requires': {'artefacto': True,
               'target': False,
               'evidencia_previa': False,
               'corpus': False},
  'resolved_by': ['radare2', 'rizin'],
  'gfx_generation': 'gfx_8_0'},
 {'capability': 'binary.dataflow',
  'question': 'que datos viajan entre bloques',
  'requires': {'artefacto': True,
               'target': False,
               'evidencia_previa': False,
               'corpus': False},
  'resolved_by': ['radare2', 'rizin'],
  'gfx_generation': 'gfx_8_0'},
 {'capability': 'binary.decompile',
  'question': 'que pseudocodigo recupera el descompilador',
  'requires': {'artefacto': True,
               'target': False,
               'evidencia_previa': False,
               'corpus': False},
  'resolved_by': ['ghidra'],
  'gfx_generation': 'gfx_8_0'},
 {'capability': 'binary.disassemble',
  'question': 'que instrucciones genera el desensamblado',
  'requires': {'artefacto': True,
               'target': False,
               'evidencia_previa': False,
               'corpus': False},
  'resolved_by': ['capstone', 'radare2', 'rizin'],
  'gfx_generation': 'gfx_8_0'},
 {'capability': 'binary.disassemble_func',
  'question': 'que instrucciones genera una funcion concreta',
  'requires': {'artefacto': True,
               'target': False,
               'evidencia_previa': False,
               'corpus': False},
  'resolved_by': ['capstone', 'rizin'],
  'gfx_generation': 'gfx_8_0'},
 {'capability': 'binary.exports',
  'question': 'que simbolos ofrece',
  'requires': {'artefacto': True,
               'target': False,
               'evidencia_previa': False,
               'corpus': False},
  'resolved_by': ['rizin'],
  'gfx_generation': 'gfx_8_0'},
 {'capability': 'binary.functions',
  'question': 'que funciones contiene',
  'requires': {'artefacto': True,
               'target': False,
               'evidencia_previa': False,
               'corpus': False},
  'resolved_by': ['radare2', 'rizin'],
  'gfx_generation': 'gfx_8_0'},
 {'capability': 'binary.imports',
  'question': 'que simbolos externos requiere',
  'requires': {'artefacto': True,
               'target': False,
               'evidencia_previa': False,
               'corpus': False},
  'resolved_by': ['rizin'],
  'gfx_generation': 'gfx_8_0'},
 {'capability': 'binary.inspect',
  'question': 'que contiene y de que clase es este binario',
  'requires': {'artefacto': True,
               'target': False,
               'evidencia_previa': False,
               'corpus': False},
  'resolved_by': ['radare2', 'rizin'],
  'gfx_generation': 'gfx_8_0'},
 {'capability': 'binary.sections',
  'question': 'que secciones declara',
  'requires': {'artefacto': True,
               'target': False,
               'evidencia_previa': False,
               'corpus': False},
  'resolved_by': ['rizin'],
  'gfx_generation': 'gfx_8_0'},
 {'capability': 'binary.strings',
  'question': 'que cadenas legibles contiene',
  'requires': {'artefacto': True,
               'target': False,
               'evidencia_previa': False,
               'corpus': False},
  'resolved_by': ['rizin'],
  'gfx_generation': 'gfx_8_0'},
 {'capability': 'binary.symbols',
  'question': 'que simbolos exporta e importa',
  'requires': {'artefacto': True,
               'target': False,
               'evidencia_previa': False,
               'corpus': False},
  'resolved_by': ['rizin'],
  'gfx_generation': 'gfx_8_0'},
 {'capability': 'binary.xrefs',
  'question': 'quien referencia a un simbolo o funcion',
  'requires': {'artefacto': True,
               'target': False,
               'evidencia_previa': False,
               'corpus': False},
  'resolved_by': ['radare2', 'rizin'],
  'gfx_generation': 'gfx_8_0'},
 {'capability': 'gpu.mmr_read',
  'question': 'que valor tiene un registro MMR de la GPU mediante mecanismo no privilegiado',
  'requires': {'artefacto': False, 'target': True, 'evidencia_previa': False, 'corpus': False},
  'scope': 'gpu',
  'status': 'AVAILABLE'},
{'capability': 'gpu.register_read',
  'question': 'que valor tiene un registro de la GPU',
  'requires': {'artefacto': False,
               'target': True,
               'evidencia_previa': False,
               'corpus': False},
  'resolved_by': ['umr'],
  'gfx_generation': 'gfx_8_0'},
 {'capability': 'rxre.create_finding',
  'question': 'que afirmacion queda sostenida por esta evidencia',
  'requires': {'artefacto': False,
               'target': False,
               'evidencia_previa': True,
               'corpus': False},
  'resolved_by': ['knowledge'],
  'gfx_generation': 'gfx_8_0'},
 {'capability': 'rxre.create_finding_relation',
  'question': 'que relacion causal sostiene esta cadena',
  'requires': {'artefacto': False,
               'target': False,
               'evidencia_previa': True,
               'corpus': False},
  'resolved_by': ['knowledge'],
  'gfx_generation': 'gfx_8_0'},
 {'capability': 'rxre.evaluate_applicability',
  'question': 'hasta donde aplica un hallazgo a este caso',
  'requires': {'artefacto': False,
               'target': False,
               'evidencia_previa': True,
               'corpus': False},
  'resolved_by': ['knowledge'],
  'gfx_generation': 'gfx_8_0'},
 {'capability': 'rxre.get_finding',
  'question': 'que dice un hallazgo ya registrado',
  'requires': {'artefacto': False,
               'target': False,
               'evidencia_previa': True,
               'corpus': False},
  'resolved_by': ['knowledge'],
  'gfx_generation': 'gfx_8_0'},
 {'capability': 'rxre.list_finding_relations',
  'question': 'que relaciones hay entre hallazgos',
  'requires': {'artefacto': False,
               'target': False,
               'evidencia_previa': True,
               'corpus': False},
  'resolved_by': ['knowledge'],
  'gfx_generation': 'gfx_8_0'},
 {'capability': 'rxre.list_findings',
  'question': 'que hallazgos hay registrados',
  'requires': {'artefacto': False,
               'target': False,
               'evidencia_previa': True,
               'corpus': False},
  'resolved_by': ['knowledge'],
  'gfx_generation': 'gfx_8_0'},
 {'capability': 'rxre.plan_investigation',
  'question': 'que paso sigue dado lo que ya se sabe',
  'requires': {'artefacto': False,
               'target': False,
               'evidencia_previa': True,
               'corpus': False},
  'resolved_by': ['knowledge'],
  'gfx_generation': 'gfx_8_0'},
 {'capability': 'rxre.search_findings',
  'question': 'que hallazgos mencionan esto',
  'requires': {'artefacto': False,
               'target': False,
               'evidencia_previa': True,
               'corpus': False},
  'resolved_by': ['knowledge'],
  'gfx_generation': 'gfx_8_0'},
 {'capability': 'source.semantic_search',
  'question': 'que dice el corpus sobre esto',
  'requires': {'artefacto': False,
               'target': False,
               'evidencia_previa': False,
               'corpus': True},
  'resolved_by': ['coccinelle'],
  'gfx_generation': 'gfx_8_0'},
    {
        "capability": "register.definition",
        "question": "¿De qué offset y de qué campos consta este registro?",
        "requires": ["register_name"],
        "resolved_by": ["register"],
        "example": {"operation": "register", "inputs": {"target": "VM_CONTEXT0_CNTL"}},
        "limitations": ["cubre la tabla asic_reg del kernel, no el hardware",
                        "PROVEN_ABSENT en asic_reg significa ausencia de "
                        "definicion, NO que el registro no exista"],
    },
    {
        "capability": "register.writers",
        "question": "¿Quién escribe este registro?",
        "requires": ["register_name"],
        "resolved_by": ["register", "search", "symbol"],
        "example": {"operation": "search",
                    "inputs": {"target": "VM_CONTEXT0_CNTL"}},
        "limitations": ["los escritores se derivan del PATRON de texto del uso: "
                        "REG_SET_FIELD/REG_RMW/WREG",
                        "un uso que casa con un constructor de escritura es un "
                        "CANDIDATO a escritor; demostrar que escribe exige "
                        "ejecutar la funcion",
                        "no se puede afirmar unicidad del escritor"],
    },
    {
        "capability": "register.readers",
        "question": "¿Quién lee este registro?",
        "requires": ["register_name"],
        "resolved_by": ["register", "search", "symbol"],
        "example": {"operation": "search",
                    "inputs": {"target": "VM_CONTEXT0_CNTL"}},
        "limitations": ["misma derivacion por patron que register.writers",
                        "RREG/READ_DWORD clasifican lectura; un uso sin "
                        "constructor conocido NO se clasifica como lectura"],
    },
    {
        "capability": "register.uses",
        "question": "¿Dónde aparece este registro en el código?",
        "requires": ["register_name"],
        "resolved_by": ["search", "symbol", "register"],
        "example": {"operation": "search",
                    "inputs": {"target": "VM_CONTEXT0_CNTL"}},
        "limitations": ["coincidencia literal de la cadena; una coincidencia no "
                        "establece que el codigo la use como registro"],
    },
    {
        "capability": "symbol.locate",
        "question": "¿Dónde está definido este símbolo?",
        "requires": ["symbol_name"],
        "resolved_by": ["symbol", "search", "register"],
        "example": {"operation": "symbol", "inputs": {"target": "amdgpu_vm"}},
        "limitations": ["busca texto, no indices de simbolo: encuentra la cadena, "
                        "no la definicion enlazada"],
    },
    {
        "capability": "symbol.callers",
        "question": "¿Quién llama a esta función?",
        "requires": ["symbol_name"],
        "resolved_by": ["xref", "trace"],
        "example": {"operation": "trace", "inputs": {"target": "amdgpu_vm"}},
        "limitations": ["xref.py sale con blocked: el AST del arbol esta a medias",
                        "trace_path depende de lo que el indice declare recorrido"],
    },
    {
        "capability": "symbol.callgraph",
        "question": "¿A qué llama esta función?",
        "requires": ["symbol_name"],
        "resolved_by": ["trace"],
        "example": {"operation": "trace", "inputs": {"target": "amdgpu_vm_init"}},
        "limitations": ["no cubre punteros de funcion ni tablas de dispatch"],
    },
    {
        "capability": "value.defuse",
        "question": "¿Qué valores definen y consumen esta variable en esta función?",
        "requires": ["symbol_name"],
        "resolved_by": ["defuse"],
        "example": {"operation": "defuse",
                    "inputs": {"target": "gmc_v8_0_gart_enable"}},
        "limitations": [
            "flujo de datos por Lachesis 0.5.3 (AGPL-3.0), invocado "
            "como proceso externo por CLI: no se vendoriza ni se "
            "enlaza; la interpretacion de AGPL-3.0 queda pendiente de "
            "revision legal antes de redistribuir el conjunto",
            "la identidad de registro es (bloque de IP, direccion): "
            "la agrupa reg_resolve (nativo); el proveedor reporta "
            "macros homonymas sin agrupar y el adaptador las agrupa "
            "por la identidad nativa, nunca por nombre",
            "limites autodeclarados por el frontend C: "
            "direct_data_flow: partial, context_sensitivity: none, "
            "branch_histories: none",
            "las #define son opacas para el proveedor: sin historial "
            "def-use; los usos RREG32/WREG32 son macros invisibles",
            "el presupuesto de respuesta trunca historiales largos: "
            "el truncamiento se declara con numeros",
            "semantica de bits de registro: NOT_DETERMINED por "
            "contrato; la responde register-fields (nativo)",
        ],
    },
    {
        "capability": "pm4.opcodes",
        "question": "¿Qué opcodes PM4 existen y qué campos tienen?",
        "requires": [],
        "resolved_by": ["pm4"],
        "example": {"operation": "pm4"},
        "limitations": ["censo estatico desde cabeceras; no incluye los packets "
                        "que el kernel construye en runtime",
                        "pm4ops.py imprime una tabla, no JSON"],
    },
    {
        "capability": "evidence.search",
        "question": "¿Hay evidencia de esto en el corpus?",
        "requires": ["query"],
        "resolved_by": ["evidence", "search"],
        "example": {"operation": "evidence", "inputs": {"target": "VMID"}},
        "limitations": ["la clasificacion es de la herramienta, sobre el universo "
                        "DECLARADO; un NOT_FOUND no es ausencia demostrada"],
    },
    {
        "capability": "provenance.keys",
        "question": "¿Qué claves de procedencia usa el árbol?",
        "requires": [],
        "resolved_by": ["provenance"],
        "example": {"operation": "provenance"},
        "limitations": ["porcentajes de claves que cumplen contrato, no un "
                        "recuento de apariciones"],
    },
    {
        "capability": "project.capabilities",
        "question": "¿Qué puede investigar y qué responde de verdad?",
        "requires": [],
        "resolved_by": ["capabilities"],
        "example": {"operation": "capabilities"},
        "limitations": ["verifica por ejecucion, no por presencia del fichero"],
    },
    ]

#: Indice por nombre. Se construye del mismo objeto para que no puedan
#: divergir: anadir una capacidad a CAPACIDADES la anade aqui.
# MEDIDO 2026-10-20 (RXRE-109): contrato restaurado; antes era dict (rotado)
# `commands/query.py:300` lo invoca como funcion; TypeError en producción.
# El indice _POR_NOMBRE se reconstruye con capa de resolucion.

# ------------------------------------------------------------------
# Recuperacion de contrato ejecutable (RXRE-109 / 108)
# ------------------------------------------------------------------

# ------------------------------------------------------------------
# Capa de resolucion de capacidades (RXRE-109 / 108).
#
# Reconstruye el contrato que `commands/query.py` consume:
#   resolver(texto)      -> intencion en texto a capacidad
#   disponibles()         -> el catalogo, ordenado
#   entradas_faltan()     -> que entradas del contrato faltan
#   por_nombre(cap)       -> la ficha de una capacidad
#
# El catalogo NO se duplica: CAPACIDADES es la lista vigente (generada
# desde backends.registry) mas las capacidades de INTENCION del contrato
# historico (lado B del conflicto de c682c4a4), que el registry no
# declara porque no son capacidades de producer sino de PREGUNTA.
# PISTAS es la tabla de patrones de intencion; no es un catalogo.
# ------------------------------------------------------------------
from typing import Any, Dict, List, Optional
import re

PISTAS: List[tuple] = [
    ("register.writers", r"\b(escribe|escritor|writers?|write[sd]?)\b", 3),
    ("register.readers", r"\b(lee|lector|readers?|reads?)\b", 3),
    ("register.uses", r"\b(usos?|donde\s+(aparece|esta|esta\s+definido))\b", 2),
    ("register.definition",
     r"\b(que\s+(offset|campos?|campos)|definicion|fields?|offsets?)\b", 2),
    ("symbol.callers", r"\b(quien\s+llama|callers?|quien\s+invoca)\b", 3),
    ("symbol.callgraph", r"\b(a\s+que\s+llama|callees?|callgraph)\b", 3),
    ("symbol.locate", r"\b(donde\s+esta|definicion\s+de|locate|localizar)\b", 2),
    ("value.defuse", r"\b(definen?|consumen?|flujo\s+de\s+datos|def\s*-?use|value[\s-]?history|dataflow)\b", 3),
    ("pm4.opcodes", r"\b(pm4|packet|opcode|opcodes)\b", 3),
    ("provenance.keys", r"\b(provenance|procedencia|claves)\b", 2),
    ("evidence.search", r"\b(evidencia|evidence)\b", 2),
    ("project.capabilities", r"\b(que\s+puedo|que\s+sabes|capabilities)\b", 3),
]

_PRIORIDAD = [
    "register.writers", "register.readers", "register.uses",
    "register.definition",
    "symbol.callers", "symbol.callgraph", "symbol.locate",
    "value.defuse",
    "pm4.opcodes", "provenance.keys", "evidence.search",
    "project.capabilities",
]
_ORDEN = {c: i for i, c in enumerate(_PRIORIDAD)}

MAX_HITS_DEFECTO = 200

for _c in CAPACIDADES:
    _c.setdefault("max_hits", MAX_HITS_DEFECTO)

_POR_NOMBRE = {c["capability"]: c for c in CAPACIDADES}


#: Namespace -> requisito. Derivado de la regla documentada en la cabeada
#: del modulo (RXRE-007 FASE 1), y medido en la tabla. Una capacida sin
#: namespace cubierto no tiene requisito: es honesto decir que no hay entradas.
_REQUIRES_POR_NAMESPACE: Dict[str, Dict[str, bool]] = {
    "binary": {"artefacto": True},
    "gpu": {"target": True},
    "rxre": {"evidencia_previa": True},
    "source": {"corpus": True},
}
# (`rea.*` no tiene regla documentada; se retorna vacio -> None/{} como
# trumento fisico honesto, no inventando requisito.)


def _capacidades_del_registry() -> Dict[str, Dict[str, Any]]:
    """Capacidades que el registry declara AHORA. Fuente EFECTIVA del catalogo.

    Si el registry y la tabla estatica divergen, el registry manda y la tabla
    solo proporciona metadatos (pregunta/requisitos/generacion) para las
    capacidades que la tabla conata.
    """
    from backends import registry  # import local; evita ciclos con core
    out: Dict[str, Dict[str, Any]] = {}
    for b in registry.catalogo():
        bid = b.get("backend_id")
        if bid is None:
            continue
        caps = b.get("capacities") or {}
        for cap, estado in caps.items():
            e = out.setdefault(cap, {
                "resolved_by": [], "estados": {}, "limitaciones": []})
            e["resolved_by"].append(bid)
            e["estados"][bid] = (estado or "UNAVAILABLE")
            if isinstance(estado, dict) and estado.get("error"):
                e["limitaciones"].append(
                    "%s la declara ERROR: %s" % (bid, estado.get("error")))
    return out


def _requires_por_namespace(cap: str) -> Dict[str, bool]:
    ns = cap.split(".", 1)[0]
    base = _REQUIRES_POR_NAMESPACE.get(ns)
    if base is None:
        return {}
    return dict(base)


def _catalogo_efectivo() -> List[Dict[str, Any]]:
    """Catalogo EFECTIVO = tabla estatica + capacidades heredadas del registry."""
    merged: Dict[str, Dict[str, Any]] = {}
    # Lado A + lado B (intenciones): de la tabla estatica.
    for c in CAPACIDADES:
        merged[c["capability"]] = dict(c)
    # Lado A (registry, fuente de verdad): nombres + metadata.
    for cap, e in _capacidades_del_registry().items():
        if cap not in merged:
            merged[cap] = {
                "capability": cap,
                "question": None,  # registry no describe preguntas; honestamente
                                   # no hay pregunta para estas capacidades.
                "requires": _requires_por_namespace(cap),
                "resolved_by": sorted(e["resolved_by"]),
                "estado_agregado": sorted(set(e["estados"].values())),
                "limitaciones": sorted(e["limitaciones"]),
                "src": "registry",
            }
        else:
            # El registry manda en resolved_by (siemPrec  diverge la tabla,
            # como en binary.decompile [ghidra] vs registry [ghidra, radare2, rizin].
            existing = merged[cap]
            if e["resolved_by"]:
                existing["resolved_by"] = sorted(e["resolved_by"])
            if e["limitaciones"]:
                ex = set(existing.get("limitaciones") or [])
                ex |= set(e["limitaciones"])
                existing["limitaciones"] = sorted(ex)
            if e.get("estado_agregado"):
                s1 = set((existing.get("estado_agregado") or "").split("|")) if existing.get("estado_agregado") else set()
                s2 = set(e["estado_agregado"].split("|")) if isinstance(e.get("estado_agregado"), str) else set()
                existing["estado_agregado"] = sorted(s1 | s2)
    return list(merged.values())


def por_nombre(cap: str) -> Optional[Dict[str, Any]]:
    """La ficha de una capacidad, o None si no existe. Busca el catalogo
    EFECTIVO (tabla + registry), como cualquier consumidor de produccion."""
    for c in _catalogo_efectivo():
        if c.get("capability") == cap:
            return dict(c)
    return None


def disponibles() -> List[Dict[str, Any]]:
    """El catalogo, en orden de especificidad. Usa el catalogo EFECTIVO."""
    return [dict(c) for c in sorted(_catalogo_efectivo(),
                                    key=lambda x: _ORDEN.get(x.get("capability"), 99))]


def resolver(texto: str) -> Dict[str, Any]:
    """Resuelve una intencion en texto a una capacidad.

    Devuelve SIEMPRE el reparto, no solo el ganador: una IA necesita
    ver por que se eligio, y sobre todo necesita ver que hubo otra
    candidata.
    """
    t = (texto or "").lower()
    punt: Dict[str, List[int]] = {}
    cap_names = {c.get("capability") for c in _catalogo_efectivo()}
    for cap, rx, peso in PISTAS:
        if cap not in cap_names:
            continue
        if re.search(rx, t):
            punt.setdefault(cap, []).append(peso)
    if not punt:
        return {"resolved": None, "candidates": [],
                "reason": "ninguna intencion del catalogo casa con el enunciado",
                "options": [c.get("capability") for c in disponibles()]}
    orden = sorted(punt.items(),
                   key=lambda kv: (-sum(kv[1]), _ORDEN.get(kv[0], 99)))
    cap, pesos = orden[0]
    runners = [c for c, _ in orden[1:3]]
    return {
        "resolved": cap,
        "confidence": "pista_explicita",
        "matched": {"capability": cap, "pistas": pesos,
                     "peso_total": sum(pesos)},
        "candidates": runners,
        "reason": "pista(s) de intencion que casaron en el enunciado",
        "detail": {"matched_patterns": [p for c, p, _w in PISTAS if c in punt]},
        "options": [c.get("capability") for c in disponibles()],
    }


def entradas_faltan(cap: str, request: Dict[str, Any]) -> List[str]:
    """Que entradas del contrato no trae el request."""
    c = None
    for item in _catalogo_efectivo():
        if item.get("capability") == cap:
            c = item
            break
    if not c:
        return []
    dados = set((request.get("inputs") or {}).keys())
    tgt = (request.get("inputs") or {}).get("target") or request.get("question") or ""
    requires = c.get("requires") or []
    if isinstance(requires, dict):
        # Catalogo derivado del registry: `requires` son CATEGORIAS
        # (artefacto, target, evidencia_previa, corpus), no nombres de
        # entrada. Se exponen como categorias faltantes.
        return [k for k, v in requires.items() if v and k not in dados and not tgt]
    return [r for r in requires if r not in dados and not tgt]
