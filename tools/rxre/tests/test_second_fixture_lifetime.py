#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""IER-116 · Second fixture lifetime — validación cruzada de la capa genérica.

Fixture 2 (independiente del cancel.sys en caso, CFG, intervalos y nombres):

    N0 entry ──┬──► N1 ASCII create ─► N2 ASCII use ─► N3 ASCII consume ─► N4
               │                                                    │
               └──► N6 (vida ASCII nunca en esta rama) ──────────────┤
                                                         N5 use─────┴──► N7 exit

  * Vida candidata: LIFE_HELLO  (storage frame:-64:20, interval [-64, -44))
  * Vida posterior:  LIFE_WORLD  (storage frame:-64:20, interval [-64, -44))
  * Misma región física, dos vidas sucesivas.
  * El brazo N6 es una rama donde la vida ASCII nunca se creó (camino ASCII-free).

El verificador genérico debe dar las decisiones esperadas en cada punto.

Ningún nombre vvar_*, ningún offset de pila del fixture original aparece ahí.
Artefacto anclado en el cancel.sys local (único PE disponible en el árbol).
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
os.environ.setdefault("IER_STORE", tempfile.mkdtemp(prefix="ier_fx2_"))

from ier import lifetime_contract as lc  # noqa: E402

_fallos = []


def t(name, cond, info=""):
    ok = bool(cond)
    print("  %s %s%s" % ("PASS" if ok else "FAIL", name, (" | " + str(info) if not ok and info else "")))
    if not ok:
        _fallos.append(name)


def mark(node, addr, stmts, succs):
    out = []
    for i, s in enumerate(stmts):
        s = dict(s)
        s["id"] = "%s#%d" % (node, i)
        out.append(s)
    return {"addr": addr, "statements": out, "successors": succs}


def build_fixture_module():
    nodes = {}
    mk = mark
    nodes["N@0x100000"] = mk("N@0x100000", 0x100000, [{"stack_refs": [], "references_complete": True}],
                             ["N@0x100010", "N@0x100060"])
    nodes["N@0x100010"] = mk("N@0x100010", 0x100010,
                             [{"stack_refs": [], "references_complete": True}],
                             ["N@0x100020"])
    nodes["N@0x100020"] = mk("N@0x100020", 0x100020,
                             [{"stack_refs": [{"kind": "vvar", "base": -64, "size": 1, "end": -63}]}],
                             ["N@0x100030"])
    nodes["N@0x100030"] = mk("N@0x100030", 0x100030,
                             [{"stack_refs": [{"kind": "call_arg", "base": -64, "size": 20, "end": -44}]}],
                             ["N@0x100040"])
    nodes["N@0x100040"] = mk("N@0x100040", 0x100040,
                             [{"stack_refs": [], "references_complete": True}],
                             ["N@0x100050"])
    nodes["N@0x100050"] = mk("N@0x100050", 0x100050,
                             [{"stack_refs": [{"kind": "vvar", "base": -64, "size": 20, "end": -44}]}],
                             ["N@0x100060"])
    nodes["N@0x100060"] = mk("N@0x100060", 0x100060,
                             [{"stack_refs": [], "references_complete": True}],
                             ["N@0x100070"])
    nodes["N@0x100070"] = mk("N@0x100070", 0x100070, [{"stack_refs": [], "references_complete": True}],
                             [])

    lives = [
        {"id": "LIFE_HELLO", "storage_id": "frame:-64:20", "interval": [-64, -44],
         "events": [
             {"kind": "create", "node": "N@0x100010", "stmt": 0, "evidence": "fixture2 create"},
             {"kind": "consume", "node": "N@0x100030", "stmt": 0, "evidence": "fixture2 consume"}],
         "transitions_to": [{"to": "LIFE_WORLD", "at_event": "consume"}],
         "semantic_identity": "fixture2 hello"},
        {"id": "LIFE_WORLD", "storage_id": "frame:-64:20", "interval": [-64, -44],
         "events": [
             {"kind": "create", "node": "N@0x100040", "stmt": 0, "evidence": "fixture2 posterior create"},
             {"kind": "consume", "node": "N@0x100060", "stmt": 0, "evidence": "fixture2 posterior consume"}],
         "transitions_to": [],
         "semantic_identity": "fixture2 world"},
    ]
    doc = {
        "version": lc.CERT_SCHEMA,
        "artifact": {"path": DEFAULT_BIN, "sha256": BIN_SHA, "architecture": "PE-x86_64"},
        "function": {"entry": "0x100000"},
        "cfg": {"entry": "N@0x100000", "coverage": "complete", "nodes": nodes},
        "lives": lives,
        "candidate": {"life": "LIFE_HELLO", "id": "cand_hello", "base": -64, "size": 20},
        "producer": {"tool": "test_second_fixture_lifetime", "schema": lc.CERT_SCHEMA},
    }
    return lc.seal_document(doc)


print("\n== Second fixture (LIFE_HELLO/LIFE_WORLD, diamond CFG)")

doc = build_fixture_module()
probes = [
    ("ASCII-CREATE stmt (create event)",   "N@0x100010", 0, "ABSTAIN"),
    ("pre-consume ASCII use",              "N@0x100020", 0, "ABSTAIN"),
    ("ASCII consume (consume event)",      "N@0x100030", 0, "ABSTAIN"),
    ("merge arm B (vida nunca creada)",    "N@0x100060", 0, "IRRELEVANT"),
    ("posterior ASCII-ref after consume+create", "N@0x100050", 0, "IRRELEVANT"),
    ("posterior consume (create domina)",  "N@0x100060", 0, "IRRELEVANT"),
]
for label, node, stmt, expected in probes:
    r = lc.evaluate(doc, {"node": node, "stmt": stmt},
                    allowed={"function": 0x100000},
                    artifact_path=DEFAULT_BIN)
    t("%s → %s" % (label, expected), r["decision"] == expected, r)

# cand fuera del intervalo (base -100)
r = lc.evaluate({**doc,
                 "candidate": {"life": "LIFE_HELLO", "id": "out", "base": -100, "size": 4}},
                {"node": "N@0x100050", "stmt": 0},
                allowed={"function": 0x100000}, artifact_path=DEFAULT_BIN)
t("candidato fuera del intervalo → BLOCKED", r["decision"] == "BLOCKED", r)

# caller inconsistente
r = lc.evaluate(doc, {"node": "N@0x100050", "stmt": 0},
                allowed={"function": 0xdeadbeef}, artifact_path=DEFAULT_BIN)
t("caller inconsistente → BLOCKED", r["decision"] == "BLOCKED", r)

# vida posterior ausencia de demostrable create
doc2 = build_fixture_module()
doc2["lives"] = [l for l in doc2["lives"] if l["id"] != "LIFE_WORLD"]
doc2 = lc.seal_document(doc2)
r = lc.evaluate(doc2, {"node": "N@0x100050", "stmt": 0},
                allowed={"function": 0x100000}, artifact_path=DEFAULT_BIN)
t("posterior sin create demostrado → no IRRELEVANT", r["decision"] != "IRRELEVANT", r)

# determinismo: misma entrada → misma salida
r1 = lc.evaluate(doc, {"node": "N@0x100050", "stmt": 0},
                 allowed={"function": 0x100000}, artifact_path=DEFAULT_BIN)
r2 = lc.evaluate(doc, {"node": "N@0x100050", "stmt": 0},
                 allowed={"function": 0x100000}, artifact_path=DEFAULT_BIN)
t("determinismo: misma entrada → mismo veredicto", r1 == r2, (r1, r2))

# certificado alterado → no IRRELEVANT
doc3 = build_fixture_module()
doc3["lives"][0]["events"][0]["node"] = "N@0xdeadbeef"
doc3 = lc.seal_document(doc3)
r = lc.evaluate(doc3, {"node": "N@0x100050", "stmt": 0},
                allowed={"function": 0x100000}, artifact_path=DEFAULT_BIN)
t("certificado con nodo desconocido → BLOCKED/ABSTAIN",
  r["decision"] in ("BLOCKED", "ABSTAIN") and r["decision"] != "IRRELEVANT", r)

# cobertura incompleta
doc4 = build_fixture_module()
doc4["cfg"]["coverage"] = "partial"
doc4 = lc.seal_document(doc4)
r = lc.evaluate(doc4, {"node": "N@0x100050", "stmt": 0},
                allowed={"function": 0x100000}, artifact_path=DEFAULT_BIN)
t("cobertura partial → no IRRELEVANT", r["decision"] != "IRRELEVANT", r)

print()
if _fallos:
    print("FALLOS:", _fallos)
    sys.exit(1)
print("Second fixture lifetime: OK")
sys.exit(0)
