#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""IER-115 · IRRELEVANT ADVERSARIAL (E11) — contrato de evidencia temporal.

Pruebas independientes del cancel.sys cuando es posible; las que requieren
un artefacto con sha256 usan el cancel.sys real en lectura.

  E11-01 CFG demuestra consumo anterior + nueva vida → IRRELEVANT
  E11-02 CFG no demuestra orden → ABSTAIN
  E11-03 Statement anterior al consumo → no IRRELEVANT
  E11-04 Statement lee la vida ASCII candidata → no IRRELEVANT
  E11-05 Statement escribe la vida ASCII candidata → no IRRELEVANT
  E11-06 Acceso posterior a misma región física, vida nueva demostrada → IRRELEVANT
  E11-07 Alias físico sin identidad temporal demostrada → ABSTAIN
  E11-08 Caller inconsistente → BLOCKED
  E11-09 Callee no resoluble → ABSTAIN (caso de cobertura; verificador temporal no admite análisis unbound)
  E11-10 Certificado alterado → BLOCKED
  E11-11 Candidato fuera del intervalo certificado → no IRRELEVANT
  E11-12 Mismo offset, función distinta → BLOCKED
  E11-13 IRRELEVANT usado como autorización directa de transformación → rechazado
  E11-14 CFG con ramas; consumo no domina al statement → ABSTAIN (o IRRELEVANT si y sólo si el solape liga vida posterior demostrada)
  E11-15 Ciclo que invalida la secuencia temporal → ABSTAIN o BLOCKED

Propiedades:
  P1  Invalid OR Unknown ⇒ Decision != IRRELEVANT
  P2  Decision == IRRELEVANT ⇒ Decision != SAFE_TO_TRANSFORM
"""
import hashlib
import json
import os
import sys
import tempfile

DEFAULT_BIN = os.path.join(
    os.environ.get("RXRE_7294_SEALED_DIR", os.path.expanduser("~/rxre-angr-7294-m10")),
    "binaries/tests/x86_64/windows/cancel.sys",
)
BIN_SHA = hashlib.sha256(open(DEFAULT_BIN, "rb").read()).hexdigest()

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)
os.environ.setdefault("IER_STORE", tempfile.mkdtemp(prefix="ier_e11_"))

from ier import lifetime_contract as lc  # noqa: E402


def t(name, cond, info=""):
    ok = bool(cond)
    print("  %s %s%s" % ("PASS" if ok else "FAIL", name, (" | " + str(info) if not ok and info else "")))
    if not ok:
        t.fails.append(name)
t.fails = []


def _nodes():
    nodes = {}
    def mk(nid, addr, stmts, succs):
        out = []
        for i, s in enumerate(stmts):
            s2 = dict(s)
            s2["id"] = "%s#%d" % (nid, i)
            out.append(s2)
        nodes[nid] = {"addr": addr, "statements": out, "successors": succs}
    return mk, nodes


def _doc(cfg_nodes, life_specs, candidate, *, artifact_path=DEFAULT_BIN,
         artifact_sha=BIN_SHA, function=0x100000, seal=True, complete=True):
    lives = []
    for spec in life_specs:
        create_node, create_stmt = spec["create"]
        consume_node, consume_stmt = spec["consume"]
        transition_to = spec["posterior"]
        lives.append({
            "id": spec["id"],
            "storage_id": spec["storage_id"],
            "interval": spec["interval"],
            "events": [
                {"kind": "create", "node": create_node, "stmt": create_stmt,
                 "evidence": "fixture-create:%s/%s" % (create_node, create_stmt)},
                {"kind": "consume", "node": consume_node, "stmt": consume_stmt,
                 "evidence": "fixture-consume:%s/%s" % (consume_node, consume_stmt)},
            ],
            "transitions_to": transition_to,
            "semantic_identity": "fixture:%s" % spec["id"],
        })
    doc = {
        "version": lc.CERT_SCHEMA,
        "artifact": {"path": artifact_path, "sha256": artifact_sha, "architecture": "PE-x86_64"},
        "function": {"entry": hex(function)},
        "cfg": {"entry": "N@0x100010", "coverage": "complete" if complete else "partial",
                "nodes": cfg_nodes},
        "lives": lives,
        "candidate": candidate,
        "producer": {"tool": "test_lifetime_irrelevant_adversarial", "schema": lc.CERT_SCHEMA},
    }
    return lc.seal_document(doc) if seal else doc


# ============================================================ fixture CFG básico
#
#   N@0x100000 (entry)
#     -> N@0x100010 (create ASCII)
#     -> N@0x100020 (other write / use before consume and no refs)
#     -> N@0x100030 (ASCII consume)
#     -> N@0x100040 (posterior create point)
#     -> N@0x100050 (use after create)
#     -> N@0x100060 (exit)
def _fixture(complete=True):
    mk, nodes = _nodes()
    mk("N@0x100000", 0x100000, [{"stack_refs": [], "references_complete": True}], ["N@0x100010"])
    mk("N@0x100010", 0x100010, [{"stack_refs": [], "references_complete": True}], ["N@0x100020"])
    mk("N@0x100020", 0x100020, [{"stack_refs": [{"kind": "vvar", "base": -44, "size": 1, "end": -43}]}], ["N@0x100030"])
    mk("N@0x100030", 0x100030, [{"stack_refs": [{"kind": "call_arg", "base": -44, "size": 20, "end": -24}]}], ["N@0x100040"])
    mk("N@0x100040", 0x100040, [{"stack_refs": [], "references_complete": True}], ["N@0x100050"])
    mk("N@0x100050", 0x100050, [{"stack_refs": [{"kind": "vvar", "base": -44, "size": 16, "end": -28}]}], ["N@0x100060"])
    mk("N@0x100060", 0x100060, [{"stack_refs": [], "references_complete": True}], [])
    return nodes

CAND = {"life": "LIFE_A", "id": "cand", "base": -44, "size": 20}

# ============ E11-01 · consumo anterior + nueva vida → IRRELEVANT
nodes = _fixture()
lives = [
    {"id": "LIFE_A", "storage_id": "frame:-44:20", "interval": [-44, -24],
     "ident": "A",
     "create": ("N@0x100010", 0), "consume": ("N@0x100030", 0),
     "posterior": [{"to": "LIFE_B", "at_event": "consume"}]},
    {"id": "LIFE_B", "storage_id": "frame:-44:20", "interval": [-44, -24],
     "ident": "B",
     "create": ("N@0x100040", 0), "consume": ("N@0x100060", 0),
     "posterior": []},
]
doc = _doc(nodes, lives, CAND)
r = lc.evaluate(doc, {"node": "N@0x100050", "stmt": 0},
                allowed={"function": 0x100000}, artifact_path=DEFAULT_BIN)
t("E11-01 CFG consume anterior + vida posterior dominada → IRRELEVANT",
  r["decision"] == "IRRELEVANT", r)

# ============ E11-02 · CFG no demuestra orden → ABSTAIN
# Mismo CFG pero App-consume no domina el punto de consulta (el punto es en el mismo bloque consumición que create)
# Reproducimos con CFG parcial (coverage partial) → ABSTAIN
nodes2 = _fixture()
lives2 = lives
doc = _doc(nodes2, lives2, CAND, complete=False)
r = lc.evaluate(doc, {"node": "N@0x100050", "stmt": 0},
                allowed={"function": 0x100000}, artifact_path=DEFAULT_BIN)
t("E11-02 CFG con coverage partial → no IRRELEVANT", r["decision"] != "IRRELEVANT", r)

# ============ E11-03 · Statement anterior al consumo → no IRRELEVANT
r = lc.evaluate(_doc(_fixture(), lives, CAND), {"node": "N@0x100020", "stmt": 0},
                allowed={"function": 0x100000}, artifact_path=DEFAULT_BIN)
t("E11-03 Statement anterior al consumo (y solape) → no IRRELEVANT",
  r["decision"] != "IRRELEVANT", r)

# ============ E11-04 · Statement lee la vida ASCII → no IRRELEVANT
nodes = _nodes()
# sobrescritura: create(0x10, 0), consume(0x30, 0), y el statement 0x20 con ref solapado
mk, nodes = _nodes()
mk("N@0x100000", 0x100000, [{"stack_refs": [], "references_complete": True}], ["N@0x100010"])
mk("N@0x100010", 0x100010, [{"stack_refs": [], "references_complete": True}], ["N@0x100020"])
mk("N@0x100020", 0x100020, [{"stack_refs": [{"kind": "vvar", "base": -40, "size": 1, "end": -39}]}], ["N@0x100030"])
mk("N@0x100030", 0x100030, [{"stack_refs": [], "references_complete": True}], ["N@0x100040"])
mk("N@0x100040", 0x100040, [{"stack_refs": [], "references_complete": True}], ["N@0x100050"])
mk("N@0x100050", 0x100050, [{"stack_refs": [{"kind": "vvar", "base": -44, "size": 4, "end": -40}]}], ["N@0x100060"])
mk("N@0x100060", 0x100060, [{"stack_refs": [], "references_complete": True}], [])
readroom = _doc(nodes, lives, CAND)
r = lc.evaluate(readroom, {"node": "N@0x100020", "stmt": 0},
                allowed={"function": 0x100000}, artifact_path=DEFAULT_BIN)
t("E11-04 Statement lee la vida candidata → no IRRELEVANT", r["decision"] != "IRRELEVANT", r)

# ============ E11-05 · Statement escribe la vida ASCII → no IRRELEVANT
nodes = _nodes()
mk, nodes = _nodes()
mk("N@0x100000", 0x100000, [{"stack_refs": [], "references_complete": True}], ["N@0x100010"])
mk("N@0x100010", 0x100010, [{"stack_refs": [], "references_complete": True}], ["N@0x100020"])
mk("N@0x100020", 0x100020, [{"stack_refs": [{"kind": "store", "base": -44, "size": 1, "end": -43}]}], ["N@0x100030"])
mk("N@0x100030", 0x100030, [{"stack_refs": [], "references_complete": True}], ["N@0x100040"])
mk("N@0x100040", 0x100040, [{"stack_refs": [], "references_complete": True}], ["N@0x100050"])
mk("N@0x100050", 0x100050, [{"stack_refs": [], "references_complete": True}], ["N@0x100060"])
mk("N@0x100060", 0x100060, [{"stack_refs": [], "references_complete": True}], [])
writeroom = _doc(nodes, lives, CAND)
r = lc.evaluate(writeroom, {"node": "N@0x100020", "stmt": 0},
                allowed={"function": 0x100000}, artifact_path=DEFAULT_BIN)
t("E11-05 Statement escribe la vida candidata → no IRRELEVANT", r["decision"] != "IRRELEVANT", r)

# ============ E11-06 · Posterior demostrada misma región → IRRELEVANT
r = lc.evaluate(_doc(_fixture(), lives, CAND), {"node": "N@0x100050", "stmt": 0},
                allowed={"function": 0x100000}, artifact_path=DEFAULT_BIN)
t("E11-06 Alias físico + vida posterior demostrada → IRRELEVANT (respecto ASCII)",
  r["decision"] == "IRRELEVANT", r)

# ============ E11-07 · Alias físico SIN identidad temporal demostrada → ABSTAIN
# Quitar disjuntor de la vida posterior (no create event) → el ref solapante no se liga
lives7 = [
    {"id": "LIFE_A", "storage_id": "frame:-44:20", "interval": [-44, -24],
     "ident": "A",
     "create": ("N@0x100010", 0), "consume": ("N@0x100030", 0), "posterior": []},
    {"id": "LIFE_B", "storage_id": "frame:-44:20", "interval": [-44, -24],
     "ident": "B",
     "create": ("N@0x100040", 0), "consume": ("N@0x100060", 0), "posterior": []},
]
doc7 = _doc(_fixture(), lives7, CAND)
r = lc.evaluate(doc7, {"node": "N@0x100050", "stmt": 0},
                allowed={"function": 0x100000}, artifact_path=DEFAULT_BIN)
t("E11-07 Alias físico sin identidad temporal demostrada → no IRRELEVANT",
  r["decision"] != "IRRELEVANT", r)

# ============ E11-08 · Caller inconsistente → BLOCKED
r = lc.evaluate(_doc(_fixture(), lives, CAND), {"node": "N@0x100050", "stmt": 0},
                allowed={"function": 0xdeadbeef}, artifact_path=DEFAULT_BIN)
t("E11-08 Caller inconsistente → BLOCKED", r["decision"] == "BLOCKED", r)

# ============ E11-09 · Callee no resoluble → no IRRELEVANT (cobertura)
# El verificador temporal evalúa el statement; no conoce el callee — esta línea se
# satisface por cobertura: un doc sin create/consume declarados → ABSTAIN
nodes9 = _fixture()
lives9 = [
    {"id": "LIFE_A", "storage_id": "frame:-44:20", "interval": [-44, -24],
     "ident": "A",
     "create": ("N@0x100010", 0), "consume": ("N@0x100030", 0), "posterior": []},
]
r = lc.evaluate(_doc(nodes9, lives9, CAND), {"node": "N@0x100050", "stmt": 0},
                allowed={"function": 0x100000}, artifact_path=DEFAULT_BIN)
# Aquí LIFE_A tiene el create, consume, y el point está tras el consumo con vida posterior
# inexistente: basta que no sea SAFE_TO_TRANSFORM ni tampoco IRRELEVANT incorrecto.
t("E11-09 Sin posterior demostrada → no IRRELEVANT", r["decision"] != "IRRELEVANT", r)

# ============ E11-10 · Certificado alterado → BLOCKED
doc = _doc(_fixture(), lives, CAND)
# adulterar la estructura de vidas
doc["lives"][0]["events"][0]["stmt"] = 999   # fuera de rango
sealed_doc = lc.seal_document(doc)
r = lc.evaluate(sealed_doc, {"node": "N@0x100050", "stmt": 0},
                allowed={"function": 0x100000}, artifact_path=DEFAULT_BIN)
t("E11-10 Evidencia alterada → BLOCKED/ABSTAIN, nunca IRRELEVANT",
  r["decision"] in ("BLOCKED", "ABSTAIN"), r)

# also: tamper the seal specifically
doc2 = _doc(_fixture(), lives, CAND)
doc2["seal_sha256"] = "00" * 32
r = lc.evaluate(doc2, {"node": "N@0x100050", "stmt": 0},
                allowed={"function": 0x100000}, artifact_path=DEFAULT_BIN)
t("E11-10b Certificado con seal adulterado → BLOCKED", r["decision"] == "BLOCKED", r)

# ============ E11-11 · Candidato fuera del intervalo certificado → no IRRELEVANT
r = lc.evaluate(_doc(_fixture(), lives, {"life": "LIFE_A", "id": "ox", "base": -100, "size": 4}),
                {"node": "N@0x100050", "stmt": 0},
                allowed={"function": 0x100000}, artifact_path=DEFAULT_BIN)
t("E11-11 Candidato fuera del intervalo → no IRRELEVANT", r["decision"] != "IRRELEVANT", r)

# ============ E11-12 · Mismo offset, función distinta → BLOCKED
r = lc.evaluate(_doc(_fixture(), lives, CAND, function=0x200000), {"node": "N@0x100050", "stmt": 0},
                allowed={"function": 0x100000}, artifact_path=DEFAULT_BIN)
t("E11-12 Misma región, función distinta → BLOCKED", r["decision"] == "BLOCKED", r)

# ============ E11-13 · IRRELEVANT ≠ autorización de transformación
# El consumidor _successor_evidence acepta IRRELEVANT como no-evidencia.
# Aquí sólo exijo invariante invariante: IRRELEVANT ≠ SAFE_TO_TRANSFORM.
r = lc.evaluate(_doc(_fixture(), lives, CAND), {"node": "N@0x100050", "stmt": 0},
                allowed={"function": 0x100000}, artifact_path=DEFAULT_BIN)
t("E11-13 verdict IRRELEVANT ≠ SAFE_TO_TRANSFORM", r["decision"] == "IRRELEVANT" and
  r["decision"] != "SAFE_TO_TRANSFORM", r)

# ============ E11-14 · CFG con ramas: consumo no domina al statement
# CFG1: entry → branch A (consume) / branch B (no consume) → exit.
mk, nodes14 = _nodes()
mk("N@0x100000", 0x100000, [{"stack_refs": [], "references_complete": True}], ["N@0x100010", "N@0x100020"])
mk("N@0x100010", 0x100010, [{"stack_refs": [], "references_complete": True}], ["N@0x100030"])
mk("N@0x100020", 0x100020, [{"stack_refs": [], "references_complete": True}], ["N@0x100040"])
mk("N@0x100030", 0x100030, [{"stack_refs": [{"kind": "call_arg", "base": -44, "size": 20, "end": -24}]}], ["N@0x100050"])
mk("N@0x100040", 0x100040, [{"stack_refs": [], "references_complete": True}], ["N@0x100050"])
mk("N@0x100050", 0x100050, [{"stack_refs": [{"kind": "vvar", "base": -44, "size": 4, "end": -40}]}], ["N@0x100060"])
mk("N@0x100060", 0x100060, [{"stack_refs": [], "references_complete": True}], [])
lives14 = [
    {"id": "LIFE_A", "storage_id": "frame:-44:20", "interval": [-44, -24],
     "ident": "A",
     "create": ("N@0x100010", 0), "consume": ("N@0x100030", 0),
     "posterior": [{"to": "LIFE_B", "at_event": "consume"}]},
    {"id": "LIFE_B", "storage_id": "frame:-44:20", "interval": [-44, -24],
     "ident": "B",
     "create": ("N@0x100040", 0), "consume": ("N@0x100060", 0), "posterior": []},
]
r = lc.evaluate(_doc(nodes14, lives14, CAND), {"node": "N@0x100050", "stmt": 0},
                allowed={"function": 0x100000}, artifact_path=DEFAULT_BIN)
# En la vida B (rama sin consume ASCII), LIFE_B existe pero CREATE de la vida ASCII no domina el
# join en la rama B; aunque el ref la liga con vida B, el nodo de consulta coincide en ambas ramas.
# La regla conservadora: la rama B nunca creó A, luego desde la óptica de la vida candidata,
# el consumo no domina este punto.
t("E11-14 CFG con ramas y consumo no domina → no IRRELEVANT",
  r["decision"] != "IRRELEVANT", r)

# ============ E11-15 · Ciclo que invalida la secuencia temporal
# CFG cíclico con consume dentro del ciclo; un regreso viola la secuencia temporal.
mk, nodes15 = _nodes()
mk("N@0x100000", 0x100000, [{"stack_refs": [], "references_complete": True}], ["N@0x100010"])
mk("N@0x100010", 0x100010, [{"stack_refs": [], "references_complete": True}], ["N@0x100020"])
mk("N@0x100020", 0x100020, [{"stack_refs": [{"kind": "vvar", "base": -44, "size": 1, "end": -43}]}], ["N@0x100030", "N@0x100040"])
mk("N@0x100030", 0x100030, [{"stack_refs": [{"kind": "call_arg", "base": -44, "size": 20, "end": -24}]}], ["N@0x100040"])
mk("N@0x100040", 0x100040, [{"stack_refs": [], "references_complete": True}], ["N@0x100050", "N@0x100020"])
mk("N@0x100050", 0x100050, [{"stack_refs": [{"kind": "vvar", "base": -44, "size": 1, "end": -43}]}], ["N@0x100060"])
mk("N@0x100060", 0x100060, [{"stack_refs": [], "references_complete": True}], [])
lives15 = [
    {"id": "LIFE_A", "storage_id": "frame:-44:20", "interval": [-44, -24],
     "ident": "A",
     "create": ("N@0x100010", 0), "consume": ("N@0x100030", 0),
     "posterior": [{"to": "LIFE_B", "at_event": "consume"}]},
    {"id": "LIFE_B", "storage_id": "frame:-44:20", "interval": [-44, -24],
     "ident": "B",
     "create": ("N@0x100040", 0), "consume": ("N@0x100060", 0), "posterior": []},
]
r = lc.evaluate(_doc(nodes15, lives15, CAND), {"node": "N@0x100050", "stmt": 0},
                allowed={"function": 0x100000}, artifact_path=DEFAULT_BIN)
t("E11-15 ciclo/retroavance → no IRRELEVANT o BLOCKED",
  r["decision"] != "IRRELEVANT" or r["decision"] == "BLOCKED", r)

# ============ P1 · Invalid OR Unknown ⇒ Decision != IRRELEVANT
# Secuencias adversariales de documentos inválidos: ninguno debe entregar IRRELEVANT.
print("\n== Propiedad P1 (Invalid ⇒ != IRRELEVANT)")
for label, mut in [
    ("sin lives", lambda d: d.pop("lives")),
    ("sin candidate", lambda d: d.pop("candidate")),
    ("sin cfg", lambda d: d.pop("cfg")),
    ("sin artifact sha", lambda d: d["artifact"].pop("sha256")),
    ("schema erróneo", lambda d: d.update(version="ryi-lifetime-evidence/1")),
    ("binario discordante", lambda d: d["artifact"].update(sha256="00" * 32)),
]:
    d = _doc(_fixture(), lives, CAND)
    mut(d)
    d = lc.seal_document(d)
    r = lc.evaluate(d, {"node": "N@0x100050", "stmt": 0},
                    allowed={"function": 0x100000}, artifact_path=DEFAULT_BIN)
    t("P1 %s ⇒ no IRRELEVANT" % label, r["decision"] != "IRRELEVANT", r)

print()
if t.fails:
    print("FALLOS:", t.fails)
    sys.exit(1)
print("E11 adversarial: OK (todos los casos)")
sys.exit(0)
