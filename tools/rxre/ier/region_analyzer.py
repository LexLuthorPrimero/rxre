#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY · WRITE_EXECUTION=SCRATCH_ONLY (.rxre/state/region_analyzer/)
"""RXRE · IER · REGION_ANALYZER — análisis genérico de regiones de memoria y evidencia.

## QUÉ ES

Capacidad IER que razona sobre **regiones de memoria candidatas** para
decidir si una transformación (p. ej. la "string-lifting" de un simplificador)
conserva las observaciones y efectos relevantes, distinguiendo siempre entre:

    dirección (Reference)  ≠  contenido (Load/Store)  ≠  escape (call args)

No es un descompilador, no es un alias analysis general y no sustituye a
ningún oráculo externo.  Es un clasificador de evidencia con decisión acotada.

## QUÉ NO ES

    - NO depende de angr (núcleo independiente; angr entra, si acaso, vía un
      adaptador externo desacoplado como ``region_analyzer_ail.py``).
    - NO infiere lectura de contenido a partir de una ``Reference``.
    - NO promueve nada: la promoción de capacidades es dictado del propietario.
    - NO es un sustituto de ``equiv_check`` ni de ``binexpr``.
    - NO aplica reglas especiales para ningún binario concreto.

## MODELO (M10.4, sellado en /home/lucas/rxre-angr-7294-m10/)

    §3  Región:    R = [base, base + size), con procedencia y tamaño opcional
                   desconocido.  size=0 es tolerado pero vacío; tamaño/offset
                   desconocidos producen ``unknown_size`` (nunca se inventa).
    §4  Solapamiento:  overlap(A,B) = max(A.start,B.start) < min(A.end,B.end)
                   — solapar NO es identidad; ver ``relation()``.
    §5  Evidencia: 10 categorías (SCALAR_READ … UNKNOWN).  La ausencia de una
                   evidencia NO se convierte en evidencia de ausencia.
    §6  Llamadas:  resúmenes SOLO con cuerpo inspeccionado o contrato conocido
                   verificable; nombre de función ≠ comportamiento.
    §7  Decisión:  PRESERVE_SCALAR | ABSTAIN | SAFE_TO_TRANSFORM

## REGLAS DE DECISIÓN (§7 del contrato M10.4)

    1. Evidencia escalar positiva (SCALAR_READ) y ninguna contradicción
       textual de confianza alta/media  →  PRESERVE_SCALAR.
    2. SCALAR_READ y TEXTUAL_READ ambos presentes (confianza ≥ MEDIUM)
       →  contradicción  →  ABSTAIN.
    3. Evidencia textual (TEXTUAL_READ / READ_MODIFY_WRITE / WRITE_ONLY) sin
       evidencia escalar ni escapes sin resolver  →  SAFE_TO_TRANSFORM.
    4. Escape a callee desconocido/opaco (ADDRESS_ESCAPE), alias no resuelto,
       branch no analizado, unknown callee, o tamaño desconocido que impide
       demostrar disjuntividad  →  ABSTAIN.
    5. Sin ninguna observación  →  ABSTAIN (NOT_DETERMINED): nunca se convierte
       ausencia en acierto.
    6. PRESERVE_SCALAR gana a SAFE_TO_TRANSFORM; ABSTAIN gana a todo cuando
       hay incertidumbre relevante.

## ESTADOS (IER)

    Operacional: PASS | PARTIAL | BLOCKED | ERROR
    Epistémico:  PROVEN | PARTIAL | NOT_DETERMINED | BLOCKED
    (PROVEN exige un oráculo independiente explícito en la entrada; este
     módulo nunca lo inventa.)

## INTEGRACIÓN IER (sin duplicar infraestructura)

    MENTE   → hipótesis discriminantes (H0-disjoint / H1-textual / H2-scalar /
              H3-partial-overlap / H4-opaque) como campo de la salida.
    CUERPO  → identidad de región: base/size/intervalo/provenance/hash.
    TIERRA  → cada evidencia contiene subject/object/op/location/source/
              scope/confidence/justification/provenance: consumible como
              claim por TIERRA sin adaptación.
    AIRE    → la salida asocia decisión ↔ herramienta ↔ resultado
              (campo ``execution``).
    ROUTER  → ``select_capability()`` expone el punto de selección.

## PERSISTENCIA

    ``persist_state()`` escribe en ``.rxre/state/region_analyzer/<id>.json``.
    Append-only por id determinista; nunca sobreescribe un estado distinto.

## M10.6 — LINAJE SSA Y EVIDENCIA POR INTERVALOS

    Almacenamiento físico ≠ etiqueta SSA ≠ referencia:

    - Región física:  intervalo exacto [base, base+size).  El almacenamiento
      (``storage``) se declara explícitamente o deriva del intervalo exacto
      (``storage:<base>:<size>``).  Mismo intervalo + mismo storage → MISMO
      almacenamiento (propagación de evidencias de contenido entre versiones).
    - Mismo valor, distinto almacenamiento → NUNCA se fusionan (contraejemplos
      N2/N10/N16).  Copia parcial (evento ``copy``) mapea bytes concretos;
      escalar en la zona copiada se propaga SOLO a ese subintervalo.
    - Solapamiento parcial entre almacenamientos DISTINTOS sin resolución de
      alias → ABSTAIN siempre (opción X conservadora).  El veto informa los
      bytes exactos contestados (``relation=partially_overlap with N (K bytes
      [lo, hi))``).  Mismo almacenamiento NO solapa: es identidad.
    - Alias confirmado entre almacenamientos distintos propaga SCALAR_READ SOLO
      dentro del intervalo compartido.

    Evidencia por intervalos:

    - Toda evidencia lleva ``interval=[lo, hi)`` absoluto (None = región
      completa, comportamiento M10.5).  Una lectura escalar sobre un subintervalo
      NO contamina el resto del candidato, pero SÍ conserva su intervalo exacto.
    - El motor decide sobre evidencia derivada con su intervalo original;
      contradicción local-vs-derivada es una contradicción visible (N6).

    XOR reversible (operandos demostrados):

    - ``rmw`` con ``xor.index_base`` y bytes const en eventos ``store``
      permite reconstruir el buffer.  Si los bytes decodificados son ASCII
      imprimibles, emite TEXTUAL_READ HIGH con el contenido decodificado.
    - Clave no demostrada → ``xor-key-unproven``; el contenido NO se
      reconstruye (nunca se inventa).

    Interprocedimental §6 (M10.6):

    - Callee inspeccionado de forma parcial / contrato no cerrado →
      ``incomplete-callee`` (UNKNOWN MEDIUM) → veto ABSTAIN.
    - Resumen ``complete: true`` declarado por el autor del resumen se exige
      para cerrar esa vía; el nombre de función nunca autoriza nada.

## EXCLUSIONES DECLARADAS

    - Análisis de precisión: no resuelve alias a través de memoria indirecta
      no modelada; los alias se declaran vía eventos ``alias``.
    - No ejecuta código del artefacto.
    - No lee más bytes de los que la entrada declara.
    - No se propagan decisiones entre almacenamientos distintos (salvo alias
      confirmado, restringido al intervalo compartido, y copias parciales).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

REGION_ANALYZER_VERSION = "RYI-REGION-ANALYZER-1"
CAPABILITY_ID = "region_analyzer"

# ---------------------------------------------------------------- categorías §5

SCALAR_READ = "SCALAR_READ"
TEXTUAL_READ = "TEXTUAL_READ"
WRITE_ONLY = "WRITE_ONLY"
READ_MODIFY_WRITE = "READ_MODIFY_WRITE"
ADDRESS_ESCAPE = "ADDRESS_ESCAPE"
OPAQUE_CALL = "OPAQUE_CALL"
ALIAS_CONFIRMED = "ALIAS_CONFIRMED"
ALIAS_UNRESOLVED = "ALIAS_UNRESOLVED"
NO_OBSERVATION = "NO_OBSERVATION"
UNKNOWN = "UNKNOWN"

EVIDENCE_CATEGORIES = (
    SCALAR_READ, TEXTUAL_READ, WRITE_ONLY, READ_MODIFY_WRITE, ADDRESS_ESCAPE,
    OPAQUE_CALL, ALIAS_CONFIRMED, ALIAS_UNRESOLVED, NO_OBSERVATION, UNKNOWN,
)

# ------------------------------------------------------------- decisiones §7
PRESERVE_SCALAR = "PRESERVE_SCALAR"
ABSTAIN = "ABSTAIN"
SAFE_TO_TRANSFORM = "SAFE_TO_TRANSFORM"
DECISIONS = (PRESERVE_SCALAR, ABSTAIN, SAFE_TO_TRANSFORM)

# ----------------------------------------------------------- estados (IER)
OP_PASS, OP_PARTIAL, OP_BLOCKED, OP_ERROR = "PASS", "PARTIAL", "BLOCKED", "ERROR"
EP_PROVEN, EP_PARTIAL, EP_NOT_DETERMINED, EP_BLOCKED = (
    "PROVEN", "PARTIAL", "NOT_DETERMINED", "BLOCKED")

CONFIDENCE_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "UNKNOWN": 0}

EVENT_KINDS = ("reference", "load", "store", "rmw", "call_arg",
               "branch", "alias", "successor_scan", "copy")

# M10.6 §3 — linaje de valores y referencias
LINEAGE_SAME_STORAGE = "same_storage"      # mismo almacenamiento, distintas etiquetas SSA
LINEAGE_SAME_VALUE = "same_value"          # distinto almacenamiento, mismo valor (nunca fusiona)
LINEAGE_SUBREGION = "subregion"            # subregión contenida en otra
LINEAGE_PARTIAL_COPY = "partial_copy"      # copia parcial con mapping de bytes
LINEAGE_DERIVED_REF = "derived_reference"  # referencia derivada (p. ej. &r[i])
LINEAGE_ALIAS_CONFIRMED = "alias_confirmed"
LINEAGE_ALIAS_POSSIBLE = "alias_possible"
LINEAGE_TEMPORALLY_ALIASED = "temporally_aliased"   # M10.7 §2: mismo frame, vidas disjuntas
LINEAGE_UNKNOWN = "unknown"
LINEAGE_RELATIONS = (LINEAGE_SAME_STORAGE, LINEAGE_SAME_VALUE, LINEAGE_SUBREGION,
                     LINEAGE_PARTIAL_COPY, LINEAGE_DERIVED_REF,
                     LINEAGE_ALIAS_CONFIRMED, LINEAGE_ALIAS_POSSIBLE,
                     LINEAGE_TEMPORALLY_ALIASED, LINEAGE_UNKNOWN)


# =============================================================== CUERPO
# identidad y relaciones entre regiones. Ningún dato externo entra aquí.

def make_region(rid: str,
                base: Optional[int],
                size: Optional[int],
                kind: str = "vvar",
                encoding: str = "unknown",
                provenance: str = "external_analysis",
                label: Optional[str] = None,
                storage: Optional[str] = None,
                live_range: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Construye una región validada.

    Lanza ValueError con mensaje exacto si la entrada es malformada.
    ``size=0`` es válido pero vacío; ``size=None`` o ``base=None`` es
    tamaño/desplazamiento desconocido (jamás se inventa).
    """
    if not isinstance(rid, str) or not rid.strip():
        raise ValueError("región sin identificador estable")
    if base is not None:
        if not isinstance(base, int) or isinstance(base, bool):
            raise ValueError("base debe ser entero o None")
        if base < -2**63 or base > 2**63 - 1:
            raise ValueError("base fuera del dominio i64 del modelo: %d" % base)
    if size is not None:
        if not isinstance(size, int) or isinstance(size, bool):
            raise ValueError("size debe ser entero o None")
        if size < 0:
            raise ValueError("size negativo no es una región: %d" % size)
        if size > 2**31:
            raise ValueError("size fuera del dominio del modelo: %d" % size)
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("kind obligatorio")
    if not isinstance(encoding, str):
        raise ValueError("encoding debe ser cadena")
    if not isinstance(provenance, str) or not provenance.strip():
        raise ValueError("provenance obligatoria (procedencia de la información)")
    # linaje: el almacenamiento físico NO se infiere del valor ni de la
    # etiqueta SSA; se declara (o se deriva del intervalo exacto).
    if storage is not None:
        if not isinstance(storage, str) or not storage.strip():
            raise ValueError("storage debe ser cadena no vacía")
        st = storage.strip()
    else:
        st = None if (base is None or size is None) else "storage:%d:%d" % (base, size)
    region = {
        "id": rid.strip(),
        "base": base,
        "size": size,
        "kind": kind.strip(),
        "encoding": encoding,
        "provenance": provenance.strip(),
        "label": (label or rid).strip(),
        "storage": st,
        "live_range": _normalize_live_range(live_range),
        "empty": (size == 0),
        "unknown_size": (size is None),
        "unknown_base": (base is None),
    }
    region["interval"] = _interval(region)
    region["sha256"] = hashlib.sha256(_canonical(region).encode("utf-8")).hexdigest()
    return region


def _interval(region: Dict[str, Any]) -> Optional[List[int]]:
    base, size = region["base"], region["size"]
    if base is None or size is None:
        return None  # tamaño u offset desconocidos: nunca se normaliza
    return [base, base + size]


# ------------------------------------------------------------ M10.6 helpers

def _hexint(v: Any) -> Optional[int]:
    if v is None:
        return None
    if isinstance(v, bool):
        raise ValueError("bloque debe ser entero o hex string")
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        try:
            return int(v, 0)
        except ValueError:
            raise ValueError("bloque no parseable: %r" % v)
    raise ValueError("bloque debe ser entero o hex string")


def _normalize_live_range(lr: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if lr is None:
        return None
    if not isinstance(lr, dict):
        raise ValueError("live_range debe ser objeto {start_block, end_block}")
    start = _hexint(lr.get("start_block"))
    end = _hexint(lr.get("end_block"))
    if start is None or end is None:
        raise ValueError("live_range exige start_block y end_block")
    return {"start_block": start, "end_block": end}

def _intersect(a: Sequence[int], b: Sequence[int]) -> Optional[List[int]]:
    lo, hi = max(a[0], b[0]), min(a[1], b[1])
    return [lo, hi] if lo < hi else None


def _signed_span(lo: int, hi: int) -> str:
    return "[%d, %d)" % (lo, hi)


def _coerce_interval(raw: Any) -> Optional[List[int]]:
    if raw is None:
        return None
    if (not isinstance(raw, (list, tuple))) or len(raw) != 2:
        raise ValueError("intervalo debe ser [lo, hi)")
    lo, hi = raw
    if not isinstance(lo, int) or not isinstance(hi, int):
        raise ValueError("extremos de intervalo deben ser enteros")
    if lo >= hi:
        raise ValueError("intervalo vacío o invertido: [%d, %d)" % (lo, hi))
    return [int(lo), int(hi)]


def _event_interval(ev: Dict[str, Any],
                    region: Dict[str, Any]) -> Optional[List[int]]:
    """Intervalo absoluto del acceso observado (default: región completa)."""
    region_iv = _interval(region)
    if region_iv is None:
        return None
    if ev.get("interval") is not None:
        return _coerce_interval(ev["interval"])
    offset = ev.get("offset")
    size = ev.get("size")
    if offset is None and size is None:
        return region_iv  # comportamiento previo al M10.6
    if offset is None:
        offset = 0
    if not isinstance(offset, int) or isinstance(offset, bool):
        return None
    if size is None:
        if region["size"] is None:
            return None
        size = region["size"] - offset
    if not isinstance(size, int) or isinstance(size, bool) or size < 1:
        return None
    lo = region["base"] + offset
    hi = lo + size
    if lo < region_iv[0] or hi > region_iv[1]:
        # intervalo fuera del candidato: la procedencia es incorrecta y se
        # descarta (nunca se inventa)
        return None
    return [lo, hi]


def overlap(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """overlap(A,B) = max(A.start,B.start) < min(A.end,B.end). Vacíos nunca solapan."""
    ia, ib = _interval(a), _interval(b)
    if ia is None or ib is None:
        return False
    return max(ia[0], ib[0]) < min(ia[1], ib[1])


def relation(a: Dict[str, Any], b: Dict[str, Any]) -> str:
    """Relación geométrica entre dos regiones.

    Devuelve una de: identical | contained | containing | partially_overlap |
    disjoint | unknown_size | empty.  NO decide alias: los alias son una
    observación con procedencia (eventos ``alias``), no geometría.
    """
    if a["empty"] or b["empty"]:
        return "empty"
    ia, ib = _interval(a), _interval(b)
    if ia is None or ib is None:
        return "unknown_size"
    if ia == ib:
        return "identical"
    if not overlap(a, b):
        return "disjoint"
    a0, a1, b0, b1 = ia[0], ia[1], ib[0], ib[1]
    if a0 >= b0 and a1 <= b1:
        return "contained"
    if b0 >= a0 and b1 <= a1:
        return "containing"
    return "partially_overlap"


def overlap_bytes(a: Dict[str, Any], b: Dict[str, Any]) -> Optional[int]:
    ia, ib = _interval(a), _interval(b)
    if ia is None or ib is None:
        return None
    lo, hi = max(ia[0], ib[0]), min(ia[1], ib[1])
    return max(0, hi - lo)


# =============================================================== evidencia §5

def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def make_evidence(category: str,
                  subject: str,
                  obj: Optional[str],
                  op: str,
                  location: Dict[str, Any],
                  source: str,
                  scope: str,
                  confidence: str,
                  justification: str,
                  related: Sequence[str] = (),
                  provenance: Optional[Dict[str, Any]] = None,
                  interval: Optional[Sequence[int]] = None,
                  derived_from: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """Registro de evidencia §5.2 (M10.6: con intervalo de bytes afectados).

    ``interval`` es [lo, hi) en bytes absolutos del candidato.  None significa
    "todo el candidato" (comportamiento M10.5).  ``derived_from`` marca
    evidencias derivadas por linaje (no primarias)."""
    if category not in EVIDENCE_CATEGORIES:
        raise ValueError("categoría desconocida: %s" % category)
    if confidence not in CONFIDENCE_ORDER:
        raise ValueError("confianza desconocida: %s" % confidence)
    if not isinstance(subject, str) or not subject.strip():
        raise ValueError("sujeto obligatorio")
    if not isinstance(op, str) or not op.strip():
        raise ValueError("operación obligatoria")
    if not isinstance(justification, str) or not justification.strip():
        raise ValueError("justificación obligatoria (la evidencia no se auto-explica)")
    iv = _coerce_interval(interval) if interval is not None else None
    payload = {
        "category": category,
        "subject": subject,
        "object": obj,
        "op": op,
        "location": dict(location or {}),
        "source": source,
        "scope": scope,
        "confidence": confidence,
        "related": sorted(set(related)),
        "interval": iv,
    }
    if derived_from:
        payload["derived"] = True
        payload["derived_from"] = sorted(set(derived_from))
    payload["id"] = "ev-" + hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()[:16]
    payload["justification"] = justification
    payload["provenance"] = dict(provenance or {})
    return payload


def dedupe_evidence(evidences: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Colapsa duplicados exactos (mismo id). Determinista."""
    seen: Dict[str, Dict[str, Any]] = {}
    for ev in evidences:
        seen.setdefault(ev["id"], ev)
    return [seen[k] for k in sorted(seen)]


# =============================================================== M10.7 §4 resúmenes sellados

CALL_SUMMARY_SCHEMA = "RXRE-IER-CALL-SUMMARY-1"
_SUMMARY_CLASSIFICATIONS = ("inspected", "external-contract", "known-text-consuming",
                            "known-object-manipulator", "known-text-producing",
                            "opaque", "indirect-unresolved")


def _summary_body(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Cuerpo canónico del resumen (excluye el sello)."""
    return {k: v for k, v in summary.items() if k not in ("seal_sha256", "sealed")}


def seal_call_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Sella un resumen: sha256 del cuerpo canónico. Determinista."""
    body = _summary_body(summary)
    body["schema"] = CALL_SUMMARY_SCHEMA
    sealed = dict(body)
    sealed["sealed"] = True
    sealed["seal_sha256"] = hashlib.sha256(
        _canonical(body).encode("utf-8")).hexdigest()
    return sealed


def call_summary_seal_valid(summary: Dict[str, Any]) -> bool:
    if not summary.get("sealed"):
        return False
    body = _summary_body(summary)
    body["schema"] = CALL_SUMMARY_SCHEMA
    expected = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
    return summary.get("seal_sha256") == expected


def validate_call_summary(summary: Any) -> List[str]:
    """Valida un resumen de llamada. Devuelve lista de defectos ([] = válido).

    Un resumen NO sellado o con defectos jamás cierra el análisis
    interprocedimental: el analizador lo rechaza como ``incomplete-callee``.
    Las reglas no examinan el nombre del callee.
    """
    problems: List[str] = []
    if not isinstance(summary, dict):
        return ["resumen no es objeto"]
    name = summary.get("name")
    if name is not None and not isinstance(name, str):
        problems.append("name debe ser cadena o null")
    cls = summary.get("classification")
    if cls is not None and cls not in _SUMMARY_CLASSIFICATIONS:
        problems.append("clasificación desconocida: %r" % (cls,))
    for key in ("reads_args", "writes_args", "writes_through_args",
                "preserves_pointer_args"):
        v = summary.get(key, [])
        if not isinstance(v, list) or any(not isinstance(i, int) or isinstance(i, bool)
                                          or i < 0 or i > 15 for i in v):
            problems.append("%s debe ser lista de índices enteros en [0,15]" % key)
    if not summary.get("complete"):
        # un resumen incompleto es válido para transportar información,
        # nunca para cerrar el análisis interprocedimental
        return problems
    # -- desde aquí: complete == True exige evidencia suficiente
    evidence = summary.get("evidence")
    if not isinstance(evidence, list) or not [e for e in evidence if e]:
        problems.append("complete=True sin evidencias (cuerpo inspeccionado o contrato sellado)")
    validity = summary.get("validity")
    if not isinstance(validity, list) or not [v for v in validity if v]:
        problems.append("complete=True sin condiciones de validez")
    if bool(summary.get("text_consuming")) and bool(summary.get("writes_candidate_scalar")):
        problems.append("contradicción: text_consuming y writes_candidate_scalar simultáneos")
    side_effects = summary.get("side_effects", [])
    if side_effects and any(str(s).lower().startswith("unknown")
                            for s in side_effects):
        problems.append("side_effects declara efectos desconocidos en un resumen completo")
    reads = set(summary.get("reads_args", []))
    writes = set(summary.get("writes_args", []))
    if reads & writes and bool(summary.get("preserves_pointer_args")):
        pass  # arg leído y escrito puede preservarse o no; no es contradicción per se
    if not bool(summary.get("sealed")):
        problems.append("complete=True exige resumen sellado (seal_sha256)")
    elif not call_summary_seal_valid(summary):
        problems.append("sellado inválido: seal_sha256 no coincide con el cuerpo")
    return problems


# =============================================================== llamadas §6

def make_call_summary(name: Optional[str],
                      classification: str,
                      reads_args: Sequence[int] = (),
                      writes_args: Sequence[int] = (),
                      writes_through_args: Sequence[int] = (),
                      preserves_pointer_args: Sequence[int] = (),
                      text_consuming: bool = False,
                      writes_candidate_scalar: bool = False,
                      unknown: bool = False,
                      side_effects: Sequence[str] = (),
                      validity: Sequence[str] = (),
                      evidence: Sequence[str] = (),
                      complete: bool = False) -> Dict[str, Any]:
    """Resumen de función §6.  Solo es 'text_consuming' por evidencia declarada,
    nunca por nombre.  El nombre se conserva como procedencia, no como hecho."""
    cls = classification or "opaque"
    if cls not in ("inspected", "known-text-consuming", "known-object-manipulator",
                   "known-text-producing", "opaque", "indirect-unresolved",
                   "external-contract"):
        raise ValueError("clasificación de callee desconocida: %s" % cls)
    return {
        "name": name,
        "classification": "opaque" if unknown else cls,
        "reads_args": sorted(set(reads_args)),
        "writes_args": sorted(set(writes_args)),
        "writes_through_args": sorted(set(writes_through_args)),
        "preserves_pointer_args": sorted(set(preserves_pointer_args)),
        "text_consuming": bool(text_consuming),
        "writes_candidate_scalar": bool(writes_candidate_scalar),
        "unknown": bool(unknown),
        "side_effects": list(side_effects),
        "validity": list(validity),
        "evidence": list(evidence),
        # M10.6 §6: el resumen solo cierra el análisis interprocedimental
        # cuando su autor lo declara completo y con evidencia; por defecto no.
        "complete": bool(complete),
    }


# =============================================================== eventos

def _event_error(errors: List[str], where: str, msg: str) -> None:
    errors.append("%s: %s" % (where, msg))


def _validate_event(raw: Any, regions: Dict[str, Dict[str, Any]],
                    errors: List[str]) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        _event_error(errors, "event", "evento debe ser objeto")
        return None
    kind = raw.get("kind")
    if kind not in EVENT_KINDS:
        _event_error(errors, "event", "kind desconocido: %r" % (kind,))
        return None
    block = raw.get("block")
    if block is not None and not isinstance(block, (str, int)):
        _event_error(errors, "event", "block debe ser hex str o entero")
        return None
    target = raw.get("region")
    if not isinstance(target, str) or not target.strip():
        _event_error(errors, "event", "evento sin región candidata")
        return None
    if target not in regions:
        _event_error(errors, "event", "región desconocida: %s" % target)
        return None
    return raw


# =============================================================== M10.6 linaje §3

def _cfg_reach(cfg: Dict[str, Any], src: int, dst: int, max_depth: int = 10000) -> bool:
    """True si dst es alcanzable desde src en el CFG proporcionado."""
    if src == dst:
        return True
    succs: Dict[int, List[int]] = {}
    for k, v in (cfg or {}).items():
        try:
            ks = _hexint(k) if isinstance(k, str) else (int(k) if isinstance(k, int) else None)
            if ks is None:
                continue
            sv: List[int] = []
            if isinstance(v, (list, tuple)):
                for x in v:
                    xs = _hexint(x) if isinstance(x, str) else x
                    if isinstance(xs, int):
                        sv.append(xs)
            succs[ks] = sv
        except (ValueError, TypeError):
            continue
    frontier = [src]
    seen = {src}
    depth = 0
    while frontier and depth < max_depth:
        depth += 1
        nxt: List[int] = []
        for node in frontier:
            for s in succs.get(node, []):
                if s == dst:
                    return True
                if s not in seen:
                    seen.add(s)
                    nxt.append(s)
        frontier = nxt
    return False


def _temporally_disjoint(ra: Dict[str, Any], rb: Dict[str, Any],
                         cfg: Dict[str, Any]) -> Optional[bool]:
    """Prueba de vidas disjuntas sobre un CFG dado.

    A y B tienen vidas disjuntas si:
      - el último uso de A (end) alcanza el inicio de B (startB), y
      - el final de B NO alcanza el inicio de A (imposibilidad de re-entrar a A).
    Ambas direcciones deben cumplirse (A precede a B o B precede a A).
    Devuelve None si cualquiera de las vidas no está declarada.
    """
    la, lb = ra.get("live_range"), rb.get("live_range")
    if not la or not lb:
        return None
    a_start, a_end = la["start_block"], la["end_block"]
    b_start, b_end = lb["start_block"], lb["end_block"]
    a_first = not _cfg_reach(cfg, b_end, a_start) and _cfg_reach(cfg, a_end, b_start)
    b_first = not _cfg_reach(cfg, a_end, b_start) and _cfg_reach(cfg, b_end, a_start)
    return a_first or b_first


def _classify_alias_pair(ra: Dict[str, Any], rb: Dict[str, Any], rel: str,
                         overlap_n: Optional[int],
                         cfg: Dict[str, Any], coverage_complete: bool,
                         regions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Clasifica la relación de alias entre dos regiones (M10.7 §2).

    CONFIRMED          misma vida útil + mismo almacenamiento (alias confirmado)
    TEMPORALLY_ALIASED mismo frame, vidas disjuntas demostradas por CFG + cobertura
                       completa declarada por el adaptador (nunca simultáneamente vivos)
    POSSIBLE           solapamiento parcial sin corroboración
    DISJOINT           intervalos disjuntos
    UNKNOWN            tamaño/base no normalizable
    """
    out: Dict[str, Any] = {"a": ra["id"], "b": rb["id"], "relation": rel,
                           "overlap_bytes": overlap_n}
    if rel in ("disjoint", "identical"):
        out["classification"] = "DISJOINT" if rel == "disjoint" else "CONFIRMED"
        out["evidence"] = ["geometric: %s" % rel]
        return out
    if rel in ("contained", "containing"):
        # contención ≠ alias: una subregión no es un almacenamiento simultáneo
        out["classification"] = "SUBREGION"
        out["evidence"] = ["geometric: %s (contención estricta)" % rel]
        return out
    if rel == "unknown_size" or rel == "empty":
        out["classification"] = "UNKNOWN"
        out["evidence"] = ["non-normalizable interval"]
        return out
    ta = _temporally_disjoint(ra, rb, cfg) if coverage_complete else None
    shared_iv = _intersect(_interval(ra), _interval(rb))
    out["shared_interval"] = shared_iv
    if ta is True:
        out["classification"] = "TEMPORALLY_ALIASED"
        out["evidence"] = [
            "CFG: 0x%x (last-use A) → 0x%x (first-constr B) alcanzable; sin reentrada" % (
                ra["live_range"]["end_block"], rb["live_range"]["start_block"]),
            "adaptador: coverage=complete (enumeración total de usos en la función)",
        ]
        return out
    if ta is False:
        # vidas solapadas o no verificables: posible, no confirmado
        out["classification"] = "POSSIBLE"
        out["evidence"] = ["intervalos solapan; vidas no disjuntas demostrables"]
        return out
    out["classification"] = "POSSIBLE"
    out["evidence"] = ["solapamiento sin prueba de disjunción temporal ni alias confirmado"]
    return out


def _derive_evidence(ev: Dict[str, Any],
                     dst_rid: str,
                     interval: Optional[List[int]],
                     path_note: str) -> Dict[str, Any]:
    """Evidencia derivada por linaje.  NUNCA comparte ``id`` con la original."""
    return make_evidence(
        ev["category"], dst_rid, ev.get("object"),
        ev["op"],
        dict(ev.get("location") or {}),
        str(ev.get("source", "derived")),
        str(ev.get("scope", "function")),
        str(ev.get("confidence", "MEDIUM")),
        "derivado por linaje (%s): %s" % (path_note, ev.get("justification", "")),
        related=ev.get("related") or (),
        provenance=dict(ev.get("provenance") or {}, derived_via=path_note),
        interval=interval,
        derived_from=[ev["id"]])


def _same_storage_groups(regions: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Grupos verificados: mismo storage declarado Y mismo intervalo exacto.

    Dos candidatos con el mismo storage declarado pero intervalos distintos NO son
    mismo almacenamiento: se registran como alias posible, nunca se fusionan.
    """
    groups: Dict[str, List[str]] = {}
    for rid, region in regions.items():
        st = region.get("storage")
        if st:
            groups.setdefault(st, []).append(rid)
    out: List[Dict[str, Any]] = []
    for st, members in sorted(groups.items()):
        if len(members) < 2:
            continue
        members = sorted(members)
        ivs = {tuple(_interval(regions[m]) or []) for m in members}
        if len(ivs) == 1:
            out.append({"storage": st, "members": members,
                        "relation": LINEAGE_SAME_STORAGE,
                        "shared_interval": _interval(regions[members[0]])})
    return out


def _propagate_same_storage(groups: List[Dict[str, Any]],
                            per_candidate: Dict[str, List[Dict[str, Any]]]) -> None:
    """Propaga evidencias de CONTENIDO dentro de un mismo almacenamiento."""
    for group in groups:
        members = group["members"]
        shared = group["shared_interval"]
        for dst in members:
            for src in members:
                if src == dst:
                    continue
                for ev in list(per_candidate[src]):
                    if ev["category"] == NO_OBSERVATION:
                        continue
                    if ev.get("derived"):
                        continue  # evitar ecos: solo se propagan evidencias primarias
                    per_candidate[dst].append(
                        _derive_evidence(ev, dst, ev.get("interval") or shared,
                                         "same-storage:%s" % src))


def _propagate_confirmed_alias(edges: List[Dict[str, Any]],
                               regions: Dict[str, Dict[str, Any]],
                               per_candidate: Dict[str, List[Dict[str, Any]]]) -> None:
    """Alias confirmado entre almacenamientos distintos: SCALAR_READ cruza solo
    en los bytes compartidos (el resto queda sin contaminar)."""
    for edge in edges:
        if edge.get("relation") != LINEAGE_ALIAS_CONFIRMED:
            continue
        if edge.get("same_storage"):
            continue  # ya cubierto por _propagate_same_storage
        shared = edge.get("shared_interval")
        a, b = edge.get("a"), edge.get("b")
        if not shared or a not in regions or b not in regions:
            continue
        for src, dst in ((a, b), (b, a)):
            for ev in list(per_candidate[src]):
                if ev["category"] != SCALAR_READ:
                    continue
                if ev.get("derived"):
                    continue
                iv = ev.get("interval") or _interval(regions[src])
                inter = _intersect(iv, shared) if iv else None
                if inter:
                    per_candidate[dst].append(
                        _derive_evidence(ev, dst, inter,
                                         "alias-confirmed:%s∩bytes" % src))


def _propagate_partial_copies(edges: List[Dict[str, Any]],
                              regions: Dict[str, Dict[str, Any]],
                              per_candidate: Dict[str, List[Dict[str, Any]]]) -> None:
    """Copia parcial: SCALAR_READ se mapea byte a byte en la zona copiada."""
    for edge in edges:
        if edge.get("relation") != LINEAGE_PARTIAL_COPY:
            continue
        a, b = edge.get("a"), edge.get("b")  # a=padre, b=hijo
        if a not in regions or b not in regions:
            continue
        p_lo, p_hi = edge["parent_interval"]
        c_lo, _ = edge["child_interval"]
        for src, dst, src_base, dst_base, span_lo, span_hi in (
                (a, b, p_lo, c_lo, p_lo, p_hi),
                (b, a, c_lo, p_lo, c_lo, c_lo + edge["size"])):
            src_iv = _interval(regions[src])
            if src_iv is None:
                continue
            for ev in list(per_candidate[src]):
                if ev["category"] != SCALAR_READ:
                    continue
                if ev.get("derived"):
                    continue
                iv = ev.get("interval") or src_iv
                lo, hi = max(iv[0], span_lo), min(iv[1], span_hi)
                if lo >= hi:
                    continue
                mapped = [dst_base + (lo - src_base), dst_base + (hi - src_base)]
                per_candidate[dst].append(
                    _derive_evidence(ev, dst, mapped,
                                     "partial-copy:%s[%s,%s)" % (src, lo, hi)))


def _apply_xor_decode(ev: Dict[str, Any],
                      eint: Optional[List[int]],
                      regions: Dict[str, Dict[str, Any]],
                      const_stores: Dict[str, List[Tuple[int, int, int]]],
                      per_candidate: Dict[str, List[Dict[str, Any]]],
                      artifact: Optional[Dict[str, Any]]) -> None:
    """Intenta reconstruir bytes cuando el RMW es XOR reversible con clave
    demostrada.  Nunca reconstruye con operandos no demostrados.

    ``xor.unit_size`` (default 1): bytes individuales; ``2`` = unidades
    de 16 bits little-endian (bucle `Mul 2` de AIL sobre wide chars).
    """
    rid = ev.get("region")
    region = regions.get(rid)
    if region is None:
        return
    loc = {"block_addr": _hex(ev.get("block")), "stmt_index": ev.get("stmt")}
    src = ev.get("source", "external-adapter")
    prov = prov_of(ev, artifact)
    rng = ev.get("xor") if isinstance(ev.get("xor"), dict) else None
    iv = eint or _interval(region)
    if iv is None:
        per_candidate[rid].append(make_evidence(
            UNKNOWN, rid, rid,
            "xor-decode-indeterminate",
            loc, src, scope_of(ev), "LOW",
            "RMW sobre intervalo no normalizable: el contenido no se reconstruye",
            provenance=prov))
        return
    if rng is None or not isinstance(rng.get("index_base"), int):
        per_candidate[rid].append(make_evidence(
            UNKNOWN, rid, rid,
            "xor-key-unproven",
            loc, src, scope_of(ev), "LOW",
            "Clave XOR no demostrada en el evento: el contenido no se reconstruye; "
            "la operación sigue siendo byte-wise",
            provenance=prov, interval=iv))
        return
    index_base = rng["index_base"]
    unit = rng.get("unit_size", 1)
    if unit not in (1, 2):
        per_candidate[rid].append(make_evidence(
            UNKNOWN, rid, rid,
            "xor-unit-unsupported",
            loc, src, scope_of(ev), "LOW",
            "unit_size %r no soportado; el contenido no se reconstruye" % (unit,),
            provenance=prov, interval=iv))
        return
    if unit == 2:
        # unidades de 16 bits little-endian
        unit_vals: Dict[int, int] = {}
        for lo, hi, value in const_stores.get(rid, []):
            if hi - lo == 2 and (lo - region["base"]) % 2 == 0:
                unit_vals[(lo - region["base"]) // 2] = value
        span_units = (iv[1] - iv[0]) // 2
        decoded_units: List[int] = []
        for u in range(span_units):
            v = unit_vals.get((iv[0] - region["base"]) // 2 + u)
            if v is None:
                per_candidate[rid].append(make_evidence(
                    UNKNOWN, rid, rid,
                    "xor-decode-incomplete-stores",
                    loc, src, scope_of(ev), "MEDIUM",
                    "Faltan unidades de 16 bits demostradas (unidad %d de %s); no se inventa el contenido" % (u, rid),
                    provenance=prov, interval=iv))
                return
            decoded_units.append(v ^ ((u + index_base) & 0xffff))
        printable = bool(decoded_units) and all(32 <= b < 127 for b in decoded_units)
        if printable:
            decoded_txt = "".join(chr(b) for b in decoded_units)
            per_candidate[rid].append(make_evidence(
                TEXTUAL_READ, rid, rid,
                "xor16-decode(index_base=%d, units=%r)" % (index_base, decoded_txt),
                loc, src, scope_of(ev), "HIGH",
                "Operandos XOR demostrados sobre wide chars: unit_i ^ ((i + %d) & 0xffff); "
                "las unidades decodificadas son ASCII imprimibles (%r)" % (
                    index_base, decoded_txt),
                provenance=dict(prov, decode="xor16-reversible",
                                operands="demonstrated"),
                interval=iv))
        else:
            per_candidate[rid].append(make_evidence(
                UNKNOWN, rid, rid,
                "xor-decode-not-printable",
                loc, src, scope_of(ev), "LOW",
                "Las unidades decodificadas no son ASCII imprimibles: no se afirma texto",
                provenance=prov, interval=iv))
        return
    byte_vals: Dict[int, int] = {}
    for lo, hi, value in const_stores.get(rid, []):
        if hi - lo == 1:
            byte_vals[lo - region["base"]] = value
    decoded: List[int] = []
    for i in range(iv[0] - region["base"], iv[1] - region["base"]):
        v = byte_vals.get(i)
        if v is None:
            per_candidate[rid].append(make_evidence(
                UNKNOWN, rid, rid,
                "xor-decode-incomplete-stores",
                loc, src, scope_of(ev), "MEDIUM",
                "Faltan bytes constantes demostrados para reconstruir el buffer "
                "(offset %d de %s); no se inventa el contenido" % (i, rid),
                provenance=prov, interval=iv))
            return
        decoded.append(v ^ ((i + index_base) & 0xff))
    printable = bool(decoded) and all(32 <= b < 127 for b in decoded)
    if printable:
        decoded_bytes = bytes(decoded)
        per_candidate[rid].append(make_evidence(
            TEXTUAL_READ, rid, rid,
            "xor-decode(index_base=%d, bytes=%r)" % (index_base, decoded_bytes),
            loc, src, scope_of(ev), "HIGH",
            "Operandos XOR demostrados: cada byte almacenado es byte_i ^ ((i + %d) "
            "& 0xff); los bytes decodificados son ASCII imprimibles (%r)" % (
                index_base, decoded_bytes),
            provenance=dict(prov, decode="xor-reversible",
                            operands="demonstrated"),
            interval=iv))
    else:
        per_candidate[rid].append(make_evidence(
            UNKNOWN, rid, rid,
            "xor-decode-not-printable",
            loc, src, scope_of(ev), "LOW",
            "Los bytes decodificados no son ASCII imprimibles: no se afirma texto",
            provenance=prov, interval=iv))


# =============================================================== motor §7

def _conf_ge(conf: str, minimum: str) -> bool:
    return CONFIDENCE_ORDER.get(conf, 0) >= CONFIDENCE_ORDER[minimum]


def analyze_region_events(candidates: Sequence[Dict[str, Any]],
                          events: Sequence[Dict[str, Any]],
                          artifact: Optional[Dict[str, Any]] = None,
                          oracle: Optional[Dict[str, Any]] = None,
                          cfg: Optional[Dict[str, Any]] = None,
                          assurance: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Analiza candidatos y devuelve el contrato de salida (§8.3 adaptado).

    Función pura: misma entrada → misma salida (determinista).
    """
    errors: List[str] = []
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        return _blocked("candidates debe ser una lista", artifact)
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes)):
        return _blocked("events debe ser una lista", artifact)
    if len(candidates) == 0:
        return _blocked("sin candidatos: nada que clasificar", artifact)

    regions: Dict[str, Dict[str, Any]] = {}
    for raw in candidates:
        try:
            region = make_region(
                str(raw.get("id")),
                raw.get("base"),
                raw.get("size"),
                kind=str(raw.get("kind", "vvar")),
                encoding=str(raw.get("encoding", "unknown")),
                provenance=str(raw.get("provenance", "external_analysis")),
                label=raw.get("label"),
                storage=raw.get("storage"),
                live_range=raw.get("live_range"))
        except (ValueError, TypeError, AttributeError) as exc:
            _event_error(errors, "candidate", str(exc))
            continue
        if region["id"] in regions:
            _event_error(errors, "candidate",
                         "identificador duplicado: %s" % region["id"])
            continue
        regions[region["id"]] = region
    if errors:
        return _blocked("; ".join(errors), artifact,
                        limitations=["entrada malformada; nada se clasificó"])

    events_valid: List[Dict[str, Any]] = []
    for raw in events:
        ev = _validate_event(raw, regions, errors)
        if ev is not None:
            events_valid.append(ev)
    if errors:
        return _blocked("; ".join(errors), artifact,
                        limitations=["eventos malformados; nada se clasificó"])

    # orden determinista de procesamiento: por bloque, luego por índice, luego kind
    def _key(ev: Dict[str, Any]):
        blk = ev.get("block")
        blk_i = blk if isinstance(blk, int) else int(str(blk), 0) if str(blk).startswith(("0x", "0X")) else 0
        return (blk_i if isinstance(blk_i, int) else 0,
                ev.get("stmt", 0) or 0,
                str(ev.get("kind") or ""),
                str(ev.get("region") or ""))
    events_sorted = sorted(events_valid, key=_key)

    # ------- recolección de evidencias por candidato
    per_candidate: Dict[str, List[Dict[str, Any]]] = {rid: [] for rid in regions}
    relation_cache: Dict[str, str] = {}
    region_ids = sorted(regions)

    def _rid(ev):
        return ev.get("region")

    const_stores: Dict[str, List[Tuple[int, int]]] = {rid: [] for rid in regions}
    rmw_events: List[Dict[str, Any]] = []
    lineage_edges: List[Dict[str, Any]] = []

    for ev in events_sorted:
        kind = ev["kind"]
        rid = _rid(ev)
        region = regions[rid]
        eint = _event_interval(ev, region)
        loc = {"block_addr": _hex(ev.get("block")), "stmt_index": ev.get("stmt"),
               "block_label": ev.get("block_label")}
        src = ev.get("source", "external-adapter")
        if kind == "reference":
            # una Reference NUNCA implica contenido (contrato §3.3)
            per_candidate[rid].append(make_evidence(
                UNKNOWN, rid, region["id"],
                "UnaryOp('Reference', %s)" % region["id"],
                loc, src, scope_of(ev), conf_of(ev, "MEDIUM"),
                "Reference observada: dirección transmitida, no contenido; "
                "no constituye evidencia escalar ni textual por sí misma",
                provenance=prov_of(ev, artifact), interval=eint))
        elif kind == "load":
            vclass = ev.get("value_class", "scalar")
            size = ev.get("size")
            if vclass == "text" or vclass == "byte_stream":
                cat = TEXTUAL_READ
                just = ("Load textual del candidato (%s bytes @ %s): bytes consumidos como "
                        "cadena, no como entero escalar" % (size, _span(eint)))
            else:
                cat = SCALAR_READ
                just = ("Load escalar del candidato (%s bytes @ %s): el contenido es "
                        "observado como entero" % (size, _span(eint)))
            per_candidate[rid].append(make_evidence(
                cat, rid, region["id"],
                "Load(addr=Reference %s, size=%s, offset=%s)" % (
                    region["id"], size, ev.get("offset", 0)),
                loc, src, scope_of(ev), conf_of(ev, "HIGH"),
                just, provenance=prov_of(ev, artifact), interval=eint))
        elif kind == "store":
            is_term = bool(ev.get("terminator"))
            per_candidate[rid].append(make_evidence(
                WRITE_ONLY, rid, region["id"],
                "Store(addr=Reference %s, data=%s, offset=%s)" % (
                    region["id"], "0<8>" if is_term else ev.get("data_class", "const"),
                    ev.get("offset")),
                loc, src, scope_of(ev), conf_of(ev, "HIGH"),
                ("Escritura del terminador NUL" if is_term else
                 "Escritura sin lectura observada del mismo contenido"),
                provenance=prov_of(ev, artifact), interval=eint))
            if isinstance(ev.get("value"), int) and isinstance(ev.get("offset"), int):
                base_iv = eint or _interval(region)
                if base_iv is not None:
                    const_stores[rid].append((base_iv[0], base_iv[1], ev["value"]))
        elif kind == "rmw":
            rmw_events.append((ev, eint))
            per_candidate[rid].append(make_evidence(
                READ_MODIFY_WRITE, rid, region["id"],
                "Load+Store(addr=Reference %s) in-loop (byte-wise)" % region["id"],
                loc, src, scope_of(ev), conf_of(ev, "HIGH"),
                "Observación y modificación del mismo contenido en una única "
                "operación lógica (p. ej. decode byte a byte)",
                provenance=prov_of(ev, artifact), interval=eint))
        elif kind == "call_arg":
            _process_call_arg(ev, regions, per_candidate, artifact, loc, src, eint)
        elif kind == "branch":
            # Cond branch observing candidate or unclassified successors
            per_candidate[rid].append(make_evidence(
                UNKNOWN, rid, region["id"],
                "ConditionalJump(%s)" % ev.get("branch_class", "unresolved"),
                loc, src, scope_of(ev), conf_of(ev, "MEDIUM"),
                "Bifurcación relevante: la linealidad del candidato depende del "
                "camino; sin prueba de exhaustividad no se decide",
                provenance=prov_of(ev, artifact), interval=eint))
        elif kind == "alias":
            confirmed = bool(ev.get("confirmed"))
            other = ev.get("other")
            other_id = other if isinstance(other, str) else None
            cat = ALIAS_CONFIRMED if confirmed else ALIAS_UNRESOLVED
            other_region = regions.get(other_id) if other_id else None
            shared = (_intersect(_interval(region), _interval(other_region))
                      if other_region else None)
            per_candidate[rid].append(make_evidence(
                cat, rid, other_id,
                (("alias confirmado vía procedencia de memoria (%s)" % _span(shared)) if confirmed else
                 "alias no resoluble con la evidencia disponible"),
                loc, src, scope_of(ev), conf_of(ev, "HIGH" if confirmed else "LOW"),
                (("Dos identificadores nombrados a la misma memoria, confirmado"
                  if confirmed else
                  "No se puede demostrar ni identidad ni separación")),
                provenance=prov_of(ev, artifact),
                interval=eint))
            if other_id and other_id in regions:
                per_candidate[other_id].append(make_evidence(
                    cat, other_id, rid,
                    (("alias confirmado vía procedencia de memoria (%s)" % _span(shared)) if confirmed else
                     "alias no resoluble con la evidencia disponible"),
                    loc, src, scope_of(ev), conf_of(ev, "HIGH" if confirmed else "LOW"),
                    ("Misma región con dos etiquetas SSA" if confirmed else
                     "Identidad no demostrada"),
                    provenance=prov_of(ev, artifact),
                    interval=shared))
            lineage_edges.append({
                "relation": (LINEAGE_ALIAS_CONFIRMED if confirmed else LINEAGE_ALIAS_POSSIBLE),
                "a": rid, "b": other_id,
                "shared_interval": shared,
                "same_storage": bool(
                    other_region and region.get("storage") == other_region.get("storage")
                    and _interval(region) == _interval(other_region)),
                "source": "alias event",
            })
        elif kind == "successor_scan":
            result = ev.get("result", "clean")
            if result == "clean":
                per_candidate[rid].append(make_evidence(
                    NO_OBSERVATION, rid, region["id"],
                    "successor_scan=clean",
                    loc, src, "function", conf_of(ev, "MEDIUM" if ev.get("complete") else "LOW"),
                    ("Escaneo declarado completo de los bloques alcanzables: ninguna "
                     "observación del candidato; cerrado-mundo dentro del dominio"
                     if ev.get("complete") else
                     "Escaneo limpio sin declaración de exhaustividad: señal débil, "
                     "no cierra el análisis"),
                    provenance=prov_of(ev, artifact), interval=eint))
            elif result == "conflict":
                per_candidate[rid].append(make_evidence(
                    UNKNOWN, rid, region["id"],
                    "successor_scan=conflict",
                    loc, src, "function", conf_of(ev, "MEDIUM"),
                    "Los bloques sucesores reportan observaciones conflictivas "
                    "del candidato; no se puede confirmar la transformación",
                    provenance=prov_of(ev, artifact), interval=eint))
            elif result == "unreachable":
                per_candidate[rid].append(make_evidence(
                    NO_OBSERVATION, rid, region["id"],
                    "successor_scan=unreachable",
                    loc, src, "function", conf_of(ev, "MEDIUM"),
                    "Descendientes sin camino relevante al candidato: se excluyen "
                    "del escaneo; no aportan ni vetan",
                    provenance=prov_of(ev, artifact), interval=eint))
        elif kind == "copy":
            other = ev.get("from_region")
            if not isinstance(other, str) or other not in regions:
                _event_error(errors, "copy", "from_region desconocido: %r" % (other,))
                continue
            parent_iv = _interval(regions[other])
            o_off = ev.get("parent_offset")
            t_off = ev.get("offset", 0)
            size = ev.get("size")
            if (parent_iv is None or not isinstance(o_off, int) or not isinstance(t_off, int)
                    or not isinstance(size, int) or size < 1
                    or o_off < 0 or t_off < 0 or o_off + size > (parent_iv[1] - parent_iv[0])
                    or (region["size"] is None) or t_off + size > region["size"]):
                _event_error(errors, "copy",
                             "mapeo de copia inválido (offsets/tamaño fuera de regiones)")
                continue
            lineage_edges.append({
                "relation": LINEAGE_PARTIAL_COPY,
                "a": other, "b": rid,              # de parent a child
                "parent_offset": o_off, "child_offset": t_off, "size": size,
                "parent_interval": [parent_iv[0] + o_off, parent_iv[0] + o_off + size],
                "child_interval": [region["base"] + t_off, region["base"] + t_off + size],
                "source": src,
            })
            per_candidate[rid].append(make_evidence(
                UNKNOWN, rid, other,
                "Copy(%s → %s, bytes %s del padre)" % (
                    other, rid, size),
                loc, src, scope_of(ev), conf_of(ev, "MEDIUM"),
                "Copia parcial: mapping explícito de bytes; no fusiona ni extiende "
                "identidades, solo mapea intervalos",
                provenance=prov_of(ev, artifact), interval=eint))

    # ------- M10.6: decodificación XOR cuando los operandos están demostrados
    for ev, eint in rmw_events:
        _apply_xor_decode(ev, eint, regions, const_stores, per_candidate, artifact)

    # ------- M10.6: linaje (mismo almacenamiento, alias confirmados, copias)
    same_storage = _same_storage_groups(regions)
    _propagate_same_storage(same_storage, per_candidate)
    _propagate_confirmed_alias(lineage_edges, regions, per_candidate)
    _propagate_partial_copies(lineage_edges, regions, per_candidate)

    # ------- relaciones por pares (geométricas, sin alias inventados)
    relations = []
    alias_classifications: List[Dict[str, Any]] = []
    cfg_successors = cfg if isinstance(cfg, dict) else {}
    coverage_complete = bool(assurance and str(assurance.get("coverage", "")).lower() == "complete")
    for i, a_id in enumerate(region_ids):
        for b_id in region_ids[i + 1:]:
            ra, rb = regions[a_id], regions[b_id]
            rel = relation(ra, rb)
            relation_cache["%s|%s" % (a_id, b_id)] = rel
            overlap_n = overlap_bytes(ra, rb)
            relations.append({
                "a": a_id, "b": b_id, "relation": rel,
                "overlap_bytes": overlap_n,
                "disjoint": rel == "disjoint",
            })
            alias_classifications.append(_classify_alias_pair(
                ra, rb, rel, overlap_n, cfg_successors, coverage_complete, regions))
            if rel == "partially_overlap":
                # §4: un solapamiento parcial sin resolución de alias es
                # incertidumbre relevante, nunca identidad ni independencia.
                # M10.7: aunque la procedencia demuestre encarnaciones temporalmente
                # disjuntas, el veto SE CONSERVA por autorización explícita.
                shared_iv = _intersect(_interval(ra), _interval(rb))
                shared_txt = _span(shared_iv)
                temporally = next((c for c in alias_classifications
                                   if c["a"] == a_id and c["b"] == b_id), None)
                temporal_note = (
                    "; procedencia demostrable: encarnaciones del mismo frame con vidas "
                    "disjuntas (ningún byte compartido simultáneamente vivo) — el veto "
                    "se conserva por política del dictamen M10.7"
                    if temporally and temporally.get("classification") == "TEMPORALLY_ALIASED"
                    else "")
                for x_id, y_id in ((a_id, b_id), (b_id, a_id)):
                    per_candidate[x_id].append(make_evidence(
                        UNKNOWN, x_id, regions[x_id]["id"],
                        "relation=partially_overlap with %s (%s bytes %s)" % (
                            y_id, overlap_n, shared_txt) + temporal_note,
                        {"block_addr": None, "stmt_index": None},
                        "region_analyzer:relations", "function", "MEDIUM",
                        "Solapamiento parcial con %s en %s sin resolución de alias: "
                        "los intervalos no son ni independientes ni equivalentes; "
                        "la incertidumbre afecta solo a los bytes compartidos%s" % (
                            y_id, shared_txt, temporal_note),
                        provenance={"method": "interval_geometry"},
                        interval=shared_iv))

    for c in alias_classifications:
        if c["classification"] == "TEMPORALLY_ALIASED":
            lineage_edges.append({
                "relation": LINEAGE_TEMPORALLY_ALIASED,
                "a": c["a"], "b": c["b"],
                "shared_interval": c.get("shared_interval"),
                "same_storage": False,
                "evidence": c.get("evidence", []),
                "source": "cfg+assurance liveness proof",
            })
        elif c["classification"] == "SUBREGION":
            lineage_edges.append({
                "relation": LINEAGE_SUBREGION,
                "a": c["a"], "b": c["b"],
                "shared_interval": c.get("shared_interval"),
                "same_storage": False,
                "source": "interval_geometry",
            })

    # ------- decisión por candidato
    analyses = []
    for rid in region_ids:
        evs = dedupe_evidence(per_candidate[rid])
        analyses.append(decide(rid, regions[rid], evs, regions, relation_cache))

    # ------- hipótesis rivales (MENTE)
    hypotheses = [
        {"id": "H0", "claim": "el candidato no es observado escalar ni textualmente por ningún camino",
         "discriminated_by": "T1/T5/T9"},
        {"id": "H1", "claim": "el candidato se consume textualmente",
         "discriminated_by": "T3/T10/T11/T12"},
        {"id": "H2", "claim": "el candidato se consume como escalar",
         "discriminated_by": "T2/T13"},
        {"id": "H3", "claim": "el candidato solapa/aliasa con otra región no analizada",
         "discriminated_by": "T6/T7/T8/T16"},
        {"id": "H4", "claim": "el candidato escapa a un consumidor opaco",
         "discriminated_by": "T4/T14"},
    ]

    # ------- agregación
    decision_counts = {}
    for a in analyses:
        decision_counts[a["decision"]] = decision_counts.get(a["decision"], 0) + 1

    # PROVEN global exige oráculo independiente explícito (§3): nunca se inventa
    oracle_ok = bool(oracle and oracle.get("independent") and
                     str(oracle.get("result", "")).upper() == "PASS")
    if oracle_ok:
        for a in analyses:
            if a["decision"] != ABSTAIN:
                a["epistemic_status"] = EP_PROVEN

    ep_statuses = [a["epistemic_status"] for a in analyses]
    if any(s == EP_BLOCKED for s in ep_statuses):
        epistemic = EP_BLOCKED
    elif all(s == EP_PROVEN for s in ep_statuses):
        epistemic = EP_PROVEN
    elif any(s in (EP_PROVEN, EP_PARTIAL) for s in ep_statuses):
        epistemic = EP_PARTIAL
    elif all(s == EP_NOT_DETERMINED for s in ep_statuses):
        epistemic = EP_NOT_DETERMINED
    else:
        epistemic = EP_NOT_DETERMINED

    op = OP_PASS if decision_counts.get(ABSTAIN, 0) == 0 else OP_PARTIAL

    result = {
        "capability": CAPABILITY_ID,
        "capability_version": REGION_ANALYZER_VERSION,
        "operational_status": op,
        "epistemic_status": epistemic,
        "artifact": dict(artifact or {}),
        "oracle": dict(oracle or {}),
        "candidates": analyses,
        "relations": relations,
        "alias_classifications": alias_classifications,
        "lineage": {
            "same_storage": _same_storage_groups(regions),
            "edges": lineage_edges,
        },
        "hypotheses": hypotheses,
        "observations": {
            "events_processed": len(events_sorted),
            "evidence_total": sum(len(a["evidence"]) for a in analyses),
        },
        "execution": {
            "tool": "rxre/ier/region_analyzer.py",
            "tool_version": REGION_ANALYZER_VERSION,
            "decision": (analyses[0]["decision"] if len(analyses) == 1 else
                         dict(sorted(decision_counts.items()))),
            "outcome": "completed",
        },
        "limitations": _global_limitations(analyses, oracle_ok),
        "errors": [],
    }
    result["limitations"] = list(dict.fromkeys(result["limitations"]))
    return result


def _process_call_arg(ev: Dict[str, Any],
                      regions: Dict[str, Dict[str, Any]],
                      per_candidate: Dict[str, List[Dict[str, Any]]],
                      artifact: Optional[Dict[str, Any]],
                      loc: Dict[str, Any],
                      src: str,
                      interval: Optional[List[int]] = None) -> None:
    rid = ev["region"]
    summary_raw = ev.get("callee") or {}
    if not isinstance(summary_raw, dict):
        summary_raw = {"classification": "opaque", "unknown": True}
    name = summary_raw.get("name")
    cls = summary_raw.get("classification", "opaque")
    unknown = bool(summary_raw.get("unknown")) or cls in ("opaque",
                                                          "indirect-unresolved")
    text_consuming = bool(summary_raw.get("text_consuming"))
    writes_scalar = bool(summary_raw.get("writes_candidate_scalar"))
    arg_pos = ev.get("arg_pos")
    writes_through = summary_raw.get("writes_through_args") or []
    if arg_pos in writes_through:
        writes_scalar = True
    prov = prov_of(ev, artifact)
    if summary_raw.get("seal_sha256"):
        prov = dict(prov, summary_seal=summary_raw["seal_sha256"])
    if unknown:
        per_candidate[rid].append(make_evidence(
            ADDRESS_ESCAPE, rid, regions[rid]["id"],
            "Call(%s, arg[%s]=&%s)" % (name or "<opaque>", arg_pos, regions[rid]["id"]),
            loc, src, scope_of(ev), conf_of(ev, "MEDIUM"),
            "El candidato escapa a un consumidor no identificado: no se puede "
            "demostrar qué observa",
            provenance=prov, interval=interval))
        per_candidate[rid].append(make_evidence(
            OPAQUE_CALL, rid, regions[rid]["id"],
            "Call(%s)" % (name or "<opaque>"),
            loc, src, scope_of(ev), conf_of(ev, "MEDIUM"),
            "Callee desconocido u opaco: ninguna caracterización por nombre es válida",
            provenance=prov, interval=interval))
        return
    complete = bool(summary_raw.get("complete"))
    if complete:
        # M10.7 §4: un resumen declarado completo solo se acepta si
        # valida (sello + estructura + coherencia). Inválido → veto.
        problems = validate_call_summary(summary_raw)
        if problems:
            per_candidate[rid].append(make_evidence(
                UNKNOWN, rid, regions[rid]["id"],
                "incomplete-callee: Call(%s, arg[%s]=&%s) — resumen sellado inválido (%s)" % (
                    name, arg_pos, regions[rid]["id"], "; ".join(problems[:3])),
                loc, src, scope_of(ev), conf_of(ev, "MEDIUM"),
                "Resumen completo pero EXPLÍCITAMENTE inválido: %s" % "; ".join(problems),
                provenance=prov, interval=interval))
            return
    if writes_scalar:
        per_candidate[rid].append(make_evidence(
            SCALAR_READ, rid, regions[rid]["id"],
            "Call(%s, arg[%s]=&%s) con escritura escalar observable" % (
                name, arg_pos, regions[rid]["id"]),
            loc, src, scope_of(ev), conf_of(ev, "MEDIUM"),
            "El callee escribe el contenido del candidato como escalar "
            "(evidencia declarada en el resumen, no inferida del nombre)",
            provenance=prov, interval=interval))
        return
    if text_consuming:
        per_candidate[rid].append(make_evidence(
            TEXTUAL_READ, rid, regions[rid]["id"],
            "Call(%s, arg[%s]=&%s) — consumo textual declarado" % (
                name, arg_pos, regions[rid]["id"]),
            loc, src, scope_of(ev), conf_of(ev, "MEDIUM"),
            "El callee consume el candidato como cadena según evidencia sellada del resumen "
            "(cuerpo inspeccionado y verificado o contrato válido)",
            provenance=prov, interval=interval))
        return
    if complete:
        # resumen declarado completo, validado y con efecto demostrado ausente:
        # no aporta ni veta (pero queda registrado)
        per_candidate[rid].append(make_evidence(
            UNKNOWN, rid, regions[rid]["id"],
            "Call(%s, arg[%s]=&%s) — callee resumen completo válido, sin efecto demostrado" % (
                name, arg_pos, regions[rid]["id"]),
            loc, src, scope_of(ev), conf_of(ev, "LOW"),
            "Resumen validado: no aporta evidencia de consumo del candidato; "
            "no constituye efecto",
            provenance=prov, interval=interval))
        return
    # M10.6 §6: efecto interprocedimental NO demostrado => veto ABSTAIN
    per_candidate[rid].append(make_evidence(
        UNKNOWN, rid, regions[rid]["id"],
        "incomplete-callee: Call(%s, arg[%s]=&%s) sin efecto interprocedimental demostrado" % (
            name, arg_pos, regions[rid]["id"]),
        loc, src, scope_of(ev), conf_of(ev, "MEDIUM"),
        "El callee no está resuelto interprocedualmente de forma completa: "
        "no se puede demostrar qué observa del candidato; la ausencia de efecto "
        "no es efecto demostrado (NEVER se asume semántica por nombre)",
        provenance=prov, interval=interval))


def decide(rid: str,
           region: Dict[str, Any],
           evidences: List[Dict[str, Any]],
           regions: Dict[str, Dict[str, Any]],
           relation_cache: Dict[str, str]) -> Dict[str, Any]:
    """Aplica la tabla de decisión §7 del contrato M10.4."""
    cats = [e["category"] for e in evidences]
    by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for e in evidences:
        by_cat.setdefault(e["category"], []).append(e)

    scalar = [e for e in evidences if e["category"] == SCALAR_READ]
    textual = [e for e in evidences if e["category"] == TEXTUAL_READ]
    rmw = [e for e in evidences if e["category"] == READ_MODIFY_WRITE]
    write_only = [e for e in evidences if e["category"] == WRITE_ONLY]
    escapes = [e for e in evidences if e["category"] == ADDRESS_ESCAPE]
    opaque = [e for e in evidences if e["category"] == OPAQUE_CALL]
    alias_unres = [e for e in evidences if e["category"] == ALIAS_UNRESOLVED]
    branches = [e for e in evidences
                if e["category"] == UNKNOWN and "ConditionalJump" in e["op"]]
    scans_conflict = [e for e in evidences
                      if e["category"] == UNKNOWN and "successor_scan=conflict" in e["op"]]
    overlap_unres = [e for e in evidences
                     if e["category"] == UNKNOWN and "partially_overlap" in e["op"]]
    interproc = [e for e in evidences
                 if e["category"] == UNKNOWN and "incomplete-callee" in e["op"]]

    limitation: List[str] = []
    if region["unknown_size"]:
        limitation.append("tamaño desconocido: no se demuestra disjuntividad ni solapamiento; los alias quedan abiertos")
    if region["unknown_base"]:
        limitation.append("base desconocida: el intervalo no es normalizable")
    if region["empty"]:
        limitation.append("región de tamaño cero: vacía por construcción; no puede sostener una decisión")
    if [e for e in evidences if "xor-key-unproven" in e["op"]]:
        limitation.append("clave XOR no demostrada: el contenido no se reconstruye")

    textual_or_stream = textual + rmw + write_only
    complete_scan = [e for e in evidences
                     if e["category"] == NO_OBSERVATION and "successor_scan=clean" in e["op"]
                     and _conf_ge(e["confidence"], "MEDIUM")]
    verdict_evidences: List[str] = []
    decision: str
    contradiction = False

    scalar_strong = [e for e in scalar if _conf_ge(e["confidence"], "MEDIUM")]
    textual_strong = [e for e in textual_or_stream if _conf_ge(e["confidence"], "MEDIUM")]

    if region["unknown_size"] or region["unknown_base"]:
        decision = ABSTAIN
        limitation.append("tamaño/base desconocidos impiden clasificar disjuntividad e identidad")
    elif region["empty"]:
        decision = ABSTAIN
        limitation.append("región vacía: nada que clasificar")
    elif scalar_strong and textual_strong:
        contradiction = True
        decision = ABSTAIN
        verdict_evidences = [e["id"] for e in scalar_strong + textual_strong]
        limitation.append(
            "contradicción: evidencia escalar y textual simultáneas sobre el mismo candidato")
    elif scalar_strong or scalar:
        decision = PRESERVE_SCALAR
        verdict_evidences = [e["id"] for e in scalar]
    elif alias_unres:
        decision = ABSTAIN
        verdict_evidences = [e["id"] for e in alias_unres]
        limitation.append("alias no resuelto: identidad de memoria no demostrable")
    elif escapes or opaque:
        decision = ABSTAIN
        verdict_evidences = [e["id"] for e in escapes + opaque]
        limitation.append("escape a consumidor opaco: el efecto externo no es demostrable")
    elif branches:
        decision = ABSTAIN
        verdict_evidences = [e["id"] for e in branches]
        limitation.append("bifurcación relevante observada sin prueba de exhaustividad de caminos")
    elif scans_conflict:
        decision = ABSTAIN
        verdict_evidences = [e["id"] for e in scans_conflict]
        limitation.append("conflicto reportado en sucesores")
    elif interproc:
        decision = ABSTAIN
        verdict_evidences = [e["id"] for e in interproc]
        limitation.append(
            "efecto interprocedimental no demostrado: callee inspeccionado de forma "
            "parcial o contrato no cerrado; se mantiene NOT_DETERMINED")
    elif overlap_unres:
        decision = ABSTAIN
        verdict_evidences = [e["id"] for e in overlap_unres]
        limitation.append(
            "solapamiento parcial con otra región candidata, sin resolución de alias")
    elif textual_or_stream:
        decision = SAFE_TO_TRANSFORM
        verdict_evidences = [e["id"] for e in textual_or_stream]
    elif complete_scan:
        decision = SAFE_TO_TRANSFORM
        verdict_evidences = [e["id"] for e in complete_scan]
        limitation.append(
            "cerrado-mundo declarado por el adaptador: SAFE_TO_TRANSFORM vale "
            "únicamente dentro del dominio escaneado y de los eventos de entrada")
    else:
        # sin observación alguna: la ausencia no prueba acierto
        decision = ABSTAIN
        limitation.append("ninguna observación registrada del candidato (NOT_DETERMINED)")
        evidences = evidences + [make_evidence(
            NO_OBSERVATION, rid, rid,
            "no-op",
            {"block_addr": None, "stmt_index": None},
            "region_analyzer:default", "function", "MEDIUM",
            "Sin evidencia registrada; la ausencia de evidencia no es evidencia de ausencia")]

    if not verdict_evidences:
        verdict_evidences = [e["id"] for e in evidences]

    # estado epistémico por candidato (sin oráculo externo nunca PROVEN aquí;
    # el oráculo global lo aplica analyze_region_events sobre esta base)
    if decision == ABSTAIN:
        epistemic = EP_NOT_DETERMINED
    else:
        epistemic = EP_PARTIAL

    domain = {
        "region": rid,
        "interval": _interval(region),
        "assumptions": [
            "solo caminos observados en los eventos de entrada",
            "los resúmenes de callee son contratos declarados, no hechos de angr",
            "la ausencia de evidencia no equivale a evidencia de ausencia",
        ],
        "validity": (
            "dominio limitado a los candidatos y eventos proporcionados; "
            "no implica corrección funcional del artefacto"
        ),
    }

    return {
        "candidate_id": rid,
        "region": {
            "id": region["id"], "base": region["base"], "size": region["size"],
            "interval": _interval(region), "kind": region["kind"],
            "encoding": region["encoding"], "provenance": region["provenance"],
            "sha256": region["sha256"],
        },
        "decision": decision,
        "epistemic_status": epistemic,
        "evidence": evidences,
        "evidence_refs": [e["id"] for e in evidences],
        "verdict_evidences": verdict_evidences,
        "contradiction": contradiction,
        "relations": {k: v for k, v in relation_cache.items() if k.startswith(rid + "|") or k.endswith("|" + rid)},
        "limitations": limitation,
        "domain": domain,
    }


# --------------------------------------------------------------- helpers

def scope_of(ev: Dict[str, Any]) -> str:
    return str(ev.get("scope", "function"))


def conf_of(ev: Dict[str, Any], default: str) -> str:
    c = ev.get("confidence")
    return c if c in CONFIDENCE_ORDER else default


def prov_of(ev: Dict[str, Any], artifact: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    prov = dict(ev.get("provenance") or {})
    if artifact:
        prov.setdefault("artifact_sha256", artifact.get("sha256"))
        prov.setdefault("artifact_path", artifact.get("path"))
    return prov


def _hex(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, int):
        return hex(v)
    return str(v)


def _span(iv: Optional[Sequence[int]]) -> str:
    if iv is None:
        return "desconocido"
    return "[%d, %d)" % (iv[0], iv[1])


def _global_limitations(analyses: Sequence[Dict[str, Any]], oracle_ok: bool) -> List[str]:
    lims: List[str] = [
        "análisis acotado a los candidatos y eventos de entrada",
        "no ejecuta el artefacto; ningún efecto externo se observa directamente",
        "sin oráculo independiente explícito no se emite PROVEN",
    ]
    if not oracle_ok:
        lims.append("oráculo independiente ausente: todos los veredictos quedan en PARTIAL o NOT_DETERMINED")
    for a in analyses:
        for item in a.get("limitations", []):
            if item not in lims:
                lims.append(item)
    return lims


def _blocked(reason: str,
             artifact: Optional[Dict[str, Any]],
             limitations: Optional[List[str]] = None) -> Dict[str, Any]:
    return {
        "capability": CAPABILITY_ID,
        "capability_version": REGION_ANALYZER_VERSION,
        "operational_status": OP_BLOCKED,
        "epistemic_status": EP_BLOCKED,
        "artifact": dict(artifact or {}),
        "oracle": {},
        "candidates": [],
        "relations": [],
        "hypotheses": [],
        "observations": {"events_processed": 0, "evidence_total": 0},
        "execution": {"tool": "rxre/ier/region_analyzer.py",
                      "tool_version": REGION_ANALYZER_VERSION,
                      "decision": None, "outcome": "blocked"},
        "limitations": list(limitations or [reason]),
        "errors": [reason],
    }


# =============================================================== IER glue

def as_capability_stub() -> Dict[str, Any]:
    """Semilla para ier.capability.declarar(); NO declara ni promociona nada."""
    return {
        "name": "region_analyzer",
        "purpose": "análisis genérico de regiones de memoria y evidencia para decidir transformaciones",
        "domain": "re/decompiler-simplifiers",
        "version": REGION_ANALYZER_VERSION,
        "limitations": [
            "núcleo independiente de angr; requiere adaptador para AIL",
            "no ejecuta el artefacto",
            "PROVEN exige oráculo independiente explícito",
        ],
    }


def select_capability() -> Dict[str, Any]:
    """Punto de selección para el ROUTER de backends (informativo)."""
    return {"id": CAPABILITY_ID,
            "version": REGION_ANALYZER_VERSION,
            "available": True,
            "categories": list(EVIDENCE_CATEGORIES),
            "decisions": list(DECISIONS)}


def state_dir() -> str:
    override = os.environ.get("RXRE_STATE")
    if override:
        return override
    return os.path.join(_repo_root(), ".rxre", "state", "region_analyzer")


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def persist_state(result: Dict[str, Any], path: Optional[str] = None) -> str:
    """Append-only: si el id ya existe con otro contenido, escribe un sufijo -N."""
    root = path or state_dir()
    os.makedirs(root, exist_ok=True)
    fingerprint = hashlib.sha256(_canonical({
        "candidates": [c["candidate_id"] for c in result.get("candidates", [])],
        "artifact": result.get("artifact"),
        "tool_version": REGION_ANALYZER_VERSION,
    }).encode("utf-8")).hexdigest()[:16]
    base = os.path.join(root, "ra_%s.json" % fingerprint)
    target, n = base, 0
    while os.path.exists(target):
        if _canonical(json.load(open(target))) == _canonical(result):
            return target
        n += 1
        target = os.path.join(root, "ra_%s.%d.json" % (fingerprint, n))
    result = dict(result)
    result["persisted_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.gmtime())
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, sort_keys=True, ensure_ascii=False)
    return target


def analyze(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Entrada pública: dict del contrato §8.2 → resultado §8.3 adaptado."""
    if not isinstance(payload, dict):
        return _blocked("payload debe ser un objeto", None)
    artifact = payload.get("artifact") or {}
    candidates = payload.get("candidates") or []
    events = payload.get("events") or []
    oracle = payload.get("oracle")
    candidates_in = []
    for raw in candidates:
        if not isinstance(raw, dict):
            return _blocked("cada candidato debe ser objeto", artifact)
        cand = dict(raw)
        # normalizar aliases de campo del contrato externo
        if "sp_offset" in cand and "base" not in cand:
            cand["base"] = cand.pop("sp_offset")
        if "size_bytes" in cand and "size" not in cand:
            cand["size"] = cand.pop("size_bytes")
        if "id" not in cand and "identifier" in cand:
            cand["id"] = cand.pop("identifier")
        candidates_in.append(cand)
    return analyze_region_events(
        candidates_in, events, artifact, oracle,
        cfg=payload.get("cfg_successors"),
        assurance=payload.get("assurance"))


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="RXRE region_analyzer — análisis de regiones y evidencia")
    parser.add_argument("payload", help="JSON de entrada (contrato de análisis)")
    parser.add_argument("--write", action="store_true", help="persistir en .rxre/state/region_analyzer/")
    parser.add_argument("--out", help="ruta de salida JSON (por defecto stdout)")
    args = parser.parse_args(argv)
    try:
        with open(args.payload, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print("ERROR: %s" % exc)
        return 2
    result = analyze(payload)
    if args.write:
        persist_state(result)
    text = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        print(text)
    return 0 if result["operational_status"] != OP_BLOCKED else 1


if __name__ == "__main__":
    raise SystemExit(main())
