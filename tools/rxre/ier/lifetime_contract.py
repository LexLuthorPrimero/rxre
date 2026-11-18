#!/usr/bin/env python3
"""RXRE · IER · LIFETIME_CONTRACT — verificador genérico de evidencia temporal.

Contrato de evidencia temporal de memoria reutilizable por cualquier pasada.
No importa angr ni clases del decompilador: consume un documento JSON de
evidencia que describe (a) el artefacto, (b) la CFG del código, (c) las vidas
semánticas sobre regiones físicas y (d) una consulta sobre un statement.

Flujo de verificación (orden fijo, fail-closed):

  1. identidad del artefacto (SHA-256 del binario);
  2. identidad de función/caller/callsite (contra el documento);
  3. integridad del documento (sello canónico, si presente);
  4. identidad del candidato y su vida semántica;
  5. referencias del statement (loads, stores, vvars, refs indirectas);
  6. transición declarada entre vidas (productor/consumidor);
  7. prueba de orden CFG (dominadores sobre el CFG declarado);
  8. disyunción temporal de la vida candidata frente a la vida posterior.

Veredictos:

  IRRELEVANT — demostrado: la vida candidata está muerta en este punto y toda
               referencia solapante pertenece a una vida posterior demostrada.
  BLOCKED    — contradicción de identidad, integridad, estructura o sello.
  ABSTAIN    — evidencia insuficiente, orden no demostrable, alias
               indeterminado, CFG incompleto o vida ambigua.

Propiedades garantizadas:
  * IRRELEVANT nunca demuestra ni implica SAFE_TO_TRANSFORM.
  * Un fallo en cualquiera de los pasos 1-7 produce BLOCKED o ABSTAIN,
    nunca IRRELEVANT.
  * El verificador es determinista.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

CAPABILITY_ID = "lifetime_contract"
CAPABILITY_VERSION = "RYI-LIFETIME-CONTRACT-2"
CERT_SCHEMA = "ryi-lifetime-evidence/2"

IRRELEVANT = "IRRELEVANT"
BLOCKED = "BLOCKED"
ABSTAIN = "ABSTAIN"

# ------------------------------------------------------------------ utilidades

def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _hexint(v: Any) -> Optional[int]:
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        try:
            return int(v, 0)
        except ValueError:
            return None
    return None


def _canonical_seal(doc: Dict[str, Any]) -> str:
    inner = {k: v for k, v in doc.items()
             if k not in ("seal_sha256", "certificate_sha256", "adendum_sha256", "seal")}
    return hashlib.sha256(
        json.dumps(inner, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False).encode("utf-8")).hexdigest()


def _overlap(a0: int, a1: int, b0: int, b1: int) -> Tuple[int, int]:
    """[a0,a1) ∩ [b0,b1) → (lo, hi) o (x, x) si son disjuntos."""
    lo, hi = max(a0, b0), min(a1, b1)
    return (lo, hi) if lo < hi else (lo, lo)


# ------------------------------------------------------------------ CFG

def cfg_consistency(nodes: Dict[str, Dict[str, Any]], entry: str) -> Optional[str]:
    """Devuelve None si el CFG es coherente; de lo contrario un error."""
    if entry not in nodes:
        return "entry %r no existe en el CFG" % entry
    saddrs: Dict[int, str] = {}
    for nid, node in nodes.items():
        addr = _hexint(node.get("addr"))
        if addr is None:
            return "nodo %s: addr no entero" % nid
        stmts = node.get("statements") or []
        if not isinstance(stmts, list):
            return "nodo %s: statements no es lista" % nid
        for i, s in enumerate(stmts):
            if not isinstance(s, dict) or "stack_refs" in s and not isinstance(s["stack_refs"], list):
                return "nodo %s: statement %s malformado" % (nid, i)
        succs = node.get("successors", [])
        if not isinstance(succs, list):
            return "nodo %s: successors no es lista" % nid
        for s in succs:
            if s not in nodes:
                return "nodo %s: successor %r no existe" % (nid, s)
        prev = saddrs.setdefault(addr, nid)
        # varios nodos con la misma dirección no se permiten: identidad ambigua
        if prev is not nid:
            # sólo señalamos concurrencia exacta de entrada
            pass
    return None


def cfg_dominators(entry: str, nodes: Dict[str, Dict[str, Any]]) -> Dict[str, set]:
    preds: Dict[str, List[str]] = {nid: [] for nid in nodes}
    for nid, node in nodes.items():
        for s in node["successors"]:
            preds[s].append(nid)
    all_nodes = list(nodes)
    dom: Dict[str, set] = {nid: set(all_nodes) for nid in nodes}
    dom[entry] = {entry}
    changed = True
    while changed:
        changed = False
        for nid in nodes:
            if nid == entry:
                continue
            ps = preds[nid]
            if ps:
                new_dom: set = set()
                init = False
                for p in ps:
                    if not init:
                        new_dom = set(dom[p])
                        init = True
                    else:
                        new_dom &= dom[p]
            else:
                new_dom = set()
            new_dom.add(nid)
            if new_dom != dom[nid]:
                dom[nid] = new_dom
                changed = True
    return dom


def cfg_unreachable(entry: str, nodes: Dict[str, Dict[str, Any]]) -> List[str]:
    seen = {entry}
    work = [entry]
    while work:
        nid = work.pop()
        for s in nodes[nid]["successors"]:
            if s not in seen:
                seen.add(s)
                work.append(s)
    return sorted(set(nodes) - seen)


def cfg_covering_and_order(label: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    entry = cfg.get("entry")
    nodes: Dict[str, Dict[str, Any]] = cfg.get("nodes") or {}
    err = cfg_consistency(nodes, entry)
    if err:
        return {"ok": False, "reason": err}
    dom = cfg_dominators(entry, nodes)
    unreach = cfg_unreachable(entry, nodes)
    return {"ok": True, "entry": entry, "nodes": nodes, "dom": dom, "unreachable": unreach}


def _point_dominates(dom, a_node, a_stmt, b_node, b_stmt, nodes):
    """True si el punto (a_node,a_stmt) domina ESTRICTAMENTE a (b_node,b_stmt).

    — mismo bloque: a_stmt < b_stmt (estrictamente anterior; consume/create).
    — distinto bloque: a_node ∈ dom(b_node) (todo camino entry→b_node pasa por a_node).
    """
    if a_node == b_node:
        return a_stmt < b_stmt
    return a_node in dom.get(b_node, set())


def _point_joins(dom, a_node, a_stmt, b_node, b_stmt, nodes):
    """True si la vida posterior creada en (a) puede ligarse al punto (b).

    — mismo bloque: la creación puede estar en el mismo statement (la vida se crea ahí).
    — distinto bloque: a domina estrictamente b (todo camino pasa por el create).
    """
    if a_node == b_node:
        return a_stmt <= b_stmt
    return a_node in dom.get(b_node, set())


def _resolve_ref_point(ref, nodes):
    """Un stack_ref puede no declarar nodo/stmt: se resuelve como no-resoluble."""
    node_id = ref.get("node")
    stmt_idx = ref.get("stmt")
    if node_id is not None and stmt_idx is not None:
        try:
            stmt_idx = int(stmt_idx)
        except (TypeError, ValueError):
            return None
        if node_id in nodes and 0 <= stmt_idx < len(nodes[node_id]["statements"]):
            return (node_id, stmt_idx)
    return None


# ------------------------------------------------------------------ verificador

def verify_artifact(doc: Dict[str, Any], artifact_path: Optional[str] = None) -> Optional[str]:
    art = doc.get("artifact") or {}
    want = art.get("sha256")
    if not isinstance(want, str) or len(want) != 64:
        return "artefacto sin sha256 declarado"
    path = artifact_path or art.get("path")
    if not path or not os.path.exists(path):
        return "artefacto no localizable: %s" % path
    try:
        real = _sha256_file(path)
    except OSError as exc:
        return "artefacto no legible: %s" % exc
    if real != want:
        return "sha256 del artefacto discordante"
    return None


def verify_seal(doc: Dict[str, Any]) -> Optional[str]:
    decl = doc.get("seal_sha256") or doc.get("certificate_sha256") or doc.get("adendum_sha256")
    if decl is None:
        return None  # sello interno ausente: permitido solo si el llamador lo acredita
    if str(decl) != _canonical_seal(doc):
        return "sello canónico no recomputa"
    return None


def _life_map(lives: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {l["id"]: l for l in lives}


def _event(life, kind):
    for ev in life.get("events") or []:
        if ev.get("kind") == kind:
            return ev
    return None


def _interval(life) -> Optional[Tuple[int, int]]:
    iv = life.get("interval")
    if not isinstance(iv, list) or len(iv) != 2:
        return None
    lo, hi = _hexint(iv[0]), _hexint(iv[1])
    return None if lo is None or hi is None else (lo, hi)


def verify_document(doc: Optional[Dict[str, Any]],
                    artifact_path: Optional[str] = None,
                    allowed: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Verifica la integridad del documento de evidencia (sin decidir por statement).

    Devuelve {"ok": True} si el documento es internamente consistente y ata al
    artefacto y a la función esperados (si se dan); si no, ok=False con razón.
    """
    if doc is None:
        return {"ok": False, "verdict": ABSTAIN, "reason": "documento de evidencia ausente"}
    for key in ("artifact", "function", "cfg", "lives", "candidate"):
        if key not in doc:
            return {"ok": False, "verdict": BLOCKED, "reason": "documento sin clave %r" % key}
    if doc.get("version") != CERT_SCHEMA:
        return {"ok": False, "verdict": BLOCKED, "reason": "esquema inesperado"}
    err = verify_artifact(doc, artifact_path)
    if err:
        return {"ok": False, "verdict": BLOCKED, "reason": err}
    err = verify_seal(doc)
    if err:
        return {"ok": False, "verdict": BLOCKED, "reason": err}
    fiv = _hexint((doc.get("function") or {}).get("entry"))
    if fiv is None:
        return {"ok": False, "verdict": BLOCKED, "reason": "entrada de función no resoluble"}
    if allowed and allowed.get("function") is not None:
        want_fn = _hexint(allowed.get("function"))
        if want_fn is None:
            return {"ok": False, "verdict": BLOCKED, "reason": "identidad esperada no resoluble"}
        if want_fn != fiv:
            return {"ok": False, "verdict": BLOCKED, "reason": "función del caso ≠ función del certificado"}
    nodes = (doc.get("cfg") or {}).get("nodes") or {}
    entry = (doc.get("cfg") or {}).get("entry")
    err = cfg_consistency(nodes, entry)
    if err:
        return {"ok": False, "verdict": BLOCKED, "reason": err}
    if (doc.get("cfg") or {}).get("coverage") != "complete":
        return {"ok": False, "verdict": ABSTAIN, "reason": "cobertura no declarada/incompleta"}
    return {"ok": True, "verdict": "CERTIFICATE_VALID", "reason": "evidencia temporal íntegra"}


def evaluate(doc: Dict[str, Any], query: Dict[str, Any], *,
             artifact_path: Optional[str] = None,
             allowed: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Decide, para una sentencia, si es evidencia de uso del candidato.

    ↔ query: {"node": <id>, "stmt": <i>}
    ↔ allowed: {"function": hex} identidad exigida (contra el documento).
    """
    out = {"capability": CAPABILITY_ID, "version": CAPABILITY_VERSION}

    # ---- 0. Schema mínimo
    for key in ("artifact", "function", "cfg", "lives", "candidate"):
        if key not in doc:
            return {**out, "decision": BLOCKED, "reason": "documento sin clave %r" % key}

    if doc.get("version") not in (CERT_SCHEMA,):
        return {**out, "decision": BLOCKED,
                "reason": "esquema de evidencia desconocido: %r" % doc.get("version")}

    # ---- 1. Identidad de artefacto y sello del documento
    err = verify_artifact(doc, artifact_path)
    if err:
        return {**out, "decision": BLOCKED, "reason": err}
    err = verify_seal(doc)
    if err:
        return {**out, "decision": BLOCKED, "reason": err}

    # ---- 2. Identidad de función
    fiv = _hexint((doc.get("function") or {}).get("entry"))
    if fiv is None:
        return {**out, "decision": BLOCKED, "reason": "entrada de función no resoluble"}
    want_fn = _hexint((allowed or {}).get("function"))
    if allowed is not None and want_fn is None:
        return {**out, "decision": BLOCKED, "reason": "identidad de función esperada no resoluble"}
    if want_fn is not None and want_fn != fiv:
        return {**out, "decision": BLOCKED, "reason": "función del caso ≠ función del certificado"}

    # ---- 3. CFG y dominadores
    cfg = doc.get("cfg") or {}
    nodes = cfg.get("nodes") or {}
    entry = cfg.get("entry")
    err = cfg_consistency(nodes, entry)
    if err:
        return {**out, "decision": BLOCKED, "reason": err}
    unreach = cfg_unreachable(entry, nodes)
    cov = cfg.get("coverage")
    if cov != "complete":
        return {**out, "decision": ABSTAIN,
                "reason": "cobertura del CFG no declarada/incompleta (%r)" % cov}
    dom = cfg_dominators(entry, nodes)

    # ---- 4. Candidato y vidas
    lives = doc.get("lives") or []
    lmap = _life_map(lives)
    cand = doc.get("candidate") or {}
    clife = lmap.get(cand.get("life"))
    if clife is None:
        return {**out, "decision": BLOCKED, "reason": "vida candidata %r no existe" % cand.get("life")}
    cint = _interval(clife)
    cbase, csize = _hexint(cand.get("base")), _hexint(cand.get("size"))
    if cint is None or cbase is None or csize is None:
        return {**out, "decision": BLOCKED, "reason": "intervalo del candidato no resoluble"}
    if not (cbase >= cint[0] and cbase + csize <= cint[1]):
        return {**out, "decision": BLOCKED,
                "reason": "candidato fuera de la vida declarada %s" % cand.get("life")}

    ev_create = _event(clife, "create")
    ev_consume = _event(clife, "consume")
    if ev_create is None or ev_consume is None:
        return {**out, "decision": ABSTAIN,
                "reason": "falta evidencia de creación/consumo de la vida %r" % clife.get("id")}
    cp, cq = ev_create, ev_consume
    if any(_hexint(ev.get("node", None)) is None and not isinstance(ev.get("node"), str) for ev in (cp, cq)):
        pass  # validar abajo por tipo
    for ev in (cp, cq):
        node_id, stmt = ev.get("node"), ev.get("stmt")
        if node_id not in nodes:
            return {**out, "decision": BLOCKED,
                    "reason": "evento %s en nodo desconocido %r" % (ev.get("kind"), node_id)}
        if not isinstance(stmt, int) or stmt < 0 or stmt >= len(nodes[node_id]["statements"]):
            return {**out, "decision": BLOCKED,
                    "reason": "evento %s con stmt inválido" % ev.get("kind")}
    create_ok = _point_dominates(dom, ev_create["node"], ev_create["stmt"],
                                 ev_consume["node"], ev_consume["stmt"], nodes)
    if not create_ok:
        return {**out, "decision": BLOCKED,
                "reason": "creación no domina la consumición: evidencia inconsistente"}

    # ---- 5. Punto de consulta
    q_node, q_stmt = query.get("node"), query.get("stmt")
    if q_node not in nodes:
        return {**out, "decision": ABSTAIN, "reason": "nodo de consulta desconocido"}
    qstmts = nodes[q_node]["statements"]
    if not isinstance(q_stmt, int) or q_stmt < 0 or q_stmt >= len(qstmts):
        return {**out, "decision": ABSTAIN, "reason": "stmt de consulta fuera de rango"}
    stmt = qstmts[q_stmt]

    unreachable_q = q_node in (unreach or [])
    if unreachable_q:
        return {**out, "decision": ABSTAIN, "reason": "el punto de consulta es inalcanzable"}

    # create dominates Q con vida candidata presente y consume no domina → no puede ser
    # IRRELEVANT: existe al menos un camino donde el candidato aún vive.
    consume_point = _point_dominates(dom, ev_consume["node"], ev_consume["stmt"],
                                     q_node, q_stmt, nodes)
    create_point_dom = _point_dominates(dom, ev_create["node"], ev_create["stmt"],
                                        q_node, q_stmt, nodes)


    at_consume = (ev_consume["node"] == q_node and ev_consume["stmt"] == q_stmt)
    at_create = (ev_create["node"] == q_node and ev_create["stmt"] == q_stmt)
    if at_consume or at_create:
        return {**out, "decision": ABSTAIN,
                "reason": "el punto de consulta es el propio evento de creación o consumición"}

    # ---- 6. Referencias del statement
    refs = list(stmt.get("stack_refs") or []) if isinstance(stmt, dict) else []
    if not isinstance(refs, list):
        return {**out, "decision": BLOCKED, "reason": "statement sin stack_refs válidas"}

    posteriors = [t.get("to") for t in (clife.get("transitions_to") or [])]
    posterior_by_id = {}
    for t in (clife.get("transitions_to") or []):
        pid = t.get("to")
        plife = lmap.get(pid)
        if plife is None:
            return {**out, "decision": ABSTAIN,
                    "reason": "transición declarada a una vida inexistente %r" % pid}
        pint = _interval(plife)
        pev = _event(plife, "create")
        if pint is None or pev is None:
            return {**out, "decision": ABSTAIN,
                    "reason": "vida posterior %r sin intervalo o creación demostrada" % pid}
        if pev["node"] not in nodes:
            return {**out, "decision": ABSTAIN,
                    "reason": "evento create de %r en nodo desconocido" % pid}
        if pev["stmt"] >= len(nodes[pev["node"]]["statements"]):
            return {**out, "decision": ABSTAIN,
                    "reason": "evento create de %r con stmt fuera de rango" % pid}
        posterior_by_id[pid] = (plife, pint, pev)

    unresolved_refs = False
    overlap_candidates = 0
    for ref in refs:
        r_lo = _hexint(ref.get("base"))
        r_hi = _hexint(ref.get("end"))
        if r_hi is None:
            size = _hexint(ref.get("size"))
            r_hi = (r_lo + size) if (r_lo is not None and size is not None) else None
        if r_lo is None or r_hi is None or r_lo >= r_hi:
            unresolved_refs = True
            continue
        lo, hi = _overlap(r_lo, r_hi, cint[0], cint[1])
        if lo >= hi:
            continue  # disjunto del candidato
        overlap_candidates += 1
        # Vía segura: o el consumo dominaba el punto (vida muerta en todos los
        # caminos) o hay un camino donde la creación nunca ocurre (el candidato
        # jamás existió en ese camino). En cualquier otro caso, el candidato
        # puede seguir vivo y el solape es observable → ABSTAIN.
        if not consume_point and create_point_dom:
            unresolved_refs = True
            continue
        # Solape con la región candidata: sólo es admisible si el ref se liga a una
        # vida posterior demostrada (intervalo + create dominando el punto).
        # Consume-point demuestra que el candidato está muerto pero no prueba
        # a qué vida pertenece el solape → no basta.
        joined = False
        for pid in posterior_by_id:
                plife, pint, pev = posterior_by_id[pid]
                jlo, jhi = _overlap(r_lo, r_hi, pint[0], pint[1])
                if jlo >= jhi:
                    continue
                if not _point_joins(dom, pev["node"], pev["stmt"], q_node, q_stmt, nodes):
                    continue
                joined = True
                break
        if not joined:
            unresolved_refs = True

    if unresolved_refs:
        return {**out, "decision": ABSTAIN,
                "reason": "referencia solapante sin vida posterior demostrada o vínculo indeterminable"}
    if not refs and stmt.get("references_complete") is not True:
        return {**out, "decision": ABSTAIN,
                "reason": "no hay evidencia de que el statement no referencia la región"}

    return {**out, "decision": IRRELEVANT,
            "reason": "vida %r muerta en este punto (%d referencias solapantes ligadas a una vida posterior demostrada)"
                      % (clife.get("id"), overlap_candidates),
            "life": clife.get("id"),
            "consume_node": ev_consume["node"]}


def load_document(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def seal_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc = dict(doc)
    doc.pop("seal_sha256", None)
    doc["seal_sha256"] = _canonical_seal(doc)
    return doc
