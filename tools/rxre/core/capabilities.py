#!/usr/bin/env python3
<<<<<<< HEAD
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
  'gfx_generation': 'gfx_8_0'}]

#: Indice por nombre. Se construye del mismo objeto para que no puedan
#: divergir: anadir una capacidad a CAPACIDADES la anade aqui.
por_nombre = {c["capability"]: c for c in CAPACIDADES}
=======
"""FASE B. Resolucion de CAPACIDAD, independiente del nombre del script.

EL PROBLEMA QUE RESUELVE, y por que un registro de adapters NO lo resuelve.

RXRE-001 tiene `ADAPTERS`, que empareja `search` con `evidence_search.py`. Eso
es un verbo -> un script. Pero una IA no pregunta "dame search", pregunta
**"¿quien escribe este registro?"** — y eso no es un verbo, es una INTENCION.

Si el unico mapa es verbo -> script, la IA tiene que saber el verbo. Que es
justo lo que este modulo quita: se registra la INTENCION, con su esquema de
entrada y salida, y la intencion declara que herramientas la resuelven.

La resolucion es por PALABRAS del enunciado, y se declara como tal: es
determinista, explicable y una IA puede leer por que eligio eso. No hay modelo
linguistico dentro de RXRE (§26: la IA decide, RXRE es la infraestructura), y
tampoco hay adivinanza silenciosa: si la intencion no esta clara, se responden
las INTENCIONES DISPONIBLES en vez de elegir una.

Y el punto donde NO se inventa una capacidad: la intencion declara `resolved_by`
con herramientas que EXISTEN. Una intencion que no se puede resolver con lo que
hay se marca `unsupported`, y se dice, en vez de devolver un hueco.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

#: Las intenciones. Cada una es lo que la IA dice que quiere saber, no lo que
#: hay que ejecutar. `requires` es lo que RXRE necesita para responder.
CAPACIDADES: List[Dict[str, Any]] = [
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

#: Orden de resolucion: el mas especifico primero. Un `register.writers` tiene
#: que ganar a un `register.uses` cuando la pregunta menciona "escribe". Por eso
#: `order` es explicito y no el orden del diccionario: el orden de un dict es un
#: detalle de implementacion y no puede decidir que se responde.
_PRIORIDAD = [
    "register.writers", "register.readers", "register.uses",
    "register.definition",
    "symbol.callers", "symbol.callgraph", "symbol.locate",
    "value.defuse",
    "pm4.opcodes", "provenance.keys", "evidence.search",
    "project.capabilities",
]
_ORDEN = {c: i for i, c in enumerate(_PRIORIDAD)}

#: Pistas de intencion. Formato: (nombre de capacidad, regex, peso).
#: Se puntua por coincidencia y gana la de mayor peso; el peso existe para
#: desempatar "quien escribe este registro" (writers) de "donde aparece este
#: registro" (uses), que comparten la palabra "registro".
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

_POR_NOMBRE = {c["capability"]: c for c in CAPACIDADES}

#: Techo de resultados por capacidad. Va AQUI y no en el dispatcher porque es
#: parte del contrato de la capacidad, no un detalle de transporte: una IA que
#: lee el catalogo tiene que poder ver el techo.
#:
#: MEDIDO 2026-10-05: sin esto, `query` sobre `VM_CONTEXT0_CNTL` devolvio
#: 6166562 resultados en 817s. `evidence_search.py --max-hits` es el tope de
#: ALMACENAMIENTO, no un limite de la consulta: recorre el universo entero.
#:
#:     un "max_hits" que no limita la consulta no es un limite
MAX_HITS_DEFECTO = 200

#: COMO se llama a cada capacidad. MEDIDO 2026-10-05: el catalogo declaraba
#: `resolved_by` -- los VERBOS de RXRE-001 que usa por dentro -- pero no decia
#: como se pide por la interfaz. Una IA leia `resolved_by: ["register","search"]`
#: y no podia saber si tinha que escribir `{"op":"register"}` (que no existe) o
#: `{"op":"query","capability":"register.writers"}` (que si).
#:
#:     resolved_by dice por dentro; invocable dice por fuera
#:
#: Es un campo derivado, no duplicado: sale de `example`, que ya existe. Se
#: expone aparte porque es lo que una IA necesita para llamar, y esconderlo en un
#: ejemplo obliga a leer el ejemplo como si fuera documentacion.
def _invocable(c: Dict[str, Any]) -> Dict[str, Any]:
    ej = c.get("example") or {}
    args: Dict[str, Any] = dict(ej.get("inputs") or {})
    args["op"] = "query"
    args["target"] = "0000:01:00.0"
    if c["capability"] not in (ej.get("operation") or ""):
        args["capability"] = c["capability"]
    return args


for _c in CAPACIDADES:
    _c.setdefault("max_hits", MAX_HITS_DEFECTO)
    _c["invocable"] = _invocable(_c)

# `_POR_NOMBRE` guarda las MISMAS referencias que la lista, y el bucle de arriba
# muta esas referencias, asi que el dict queda al dia. Se reconstruye de todos
# modos para que el orden de las dos lineas no importe: si alguien mueve el
# `setdefault`, el techo se pierde en silencio y el defecto vuelve.
_POR_NOMBRE = {c["capability"]: c for c in CAPACIDADES}


def por_nombre(cap: str) -> Optional[Dict[str, Any]]:
    c = _POR_NOMBRE.get(cap)
    return dict(c) if c else None


def disponibles() -> List[Dict[str, Any]]:
    """El catalogo, en orden de especificidad. Es la respuesta a '¿qué sé hacer?'."""
    return [dict(c) for c in sorted(CAPACIDADES,
                                    key=lambda x: _ORDEN.get(x["capability"], 99))]



def resolver(texto: str) -> Dict[str, Any]:
    """Resuelve una intencion en texto a una capacidad. Explicable y determinista.

    Devuelve SIEMPRE el reparto, no solo el ganador: una IA necesita ver por que
    se eligio, y sobre todo necesita ver que hubo otra candidata. Un ganador sin
    runners-up es una caja negra, y una caja negra en la capa que decide es
    donde nace una conclusion falsa.
    """
    t = (texto or "").lower()
    punt: Dict[str, List[int]] = {}
    for cap, rx, peso in PISTAS:
        if re.search(rx, t):
            punt.setdefault(cap, []).append(peso)
    if not punt:
        return {"resolved": None, "candidates": [],
                "reason": "ninguna intencion del catalogo casa con el enunciado",
                "options": [c["capability"] for c in disponibles()]}
    # El peso se SUMA por coincidencia, y la especificidad rompe el empate.
    orden = sorted(
        punt.items(),
        key=lambda kv: (-sum(kv[1]), _ORDEN.get(kv[0], 99)),
    )
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
        "options": [c["capability"] for c in disponibles()],
    }


def entradas_faltan(cap: str, request: Dict[str, Any]) -> List[str]:
    """Que entradas del contrato no trae el request. Para responder 400, no para fallar."""
    c = _POR_NOMBRE.get(cap)
    if not c:
        return []
    dados = set((request.get("inputs") or {}).keys())
    tgt = (request.get("inputs") or {}).get("target") or request.get("question") or ""
    faltan = [r for r in c["requires"] if r not in dados and not tgt]
    return faltan
>>>>>>> c682c4a4cf4e2c5c518a90f41e54107a7ecde6db
