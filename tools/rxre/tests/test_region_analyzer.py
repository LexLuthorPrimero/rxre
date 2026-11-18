#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""IER-107 · REGION_ANALYZER — modelo independiente de regiones, evidencia y decisión.

Cubre los 16 escenarios adversariales de la matriz M10.4 (T1-T16) más
propiedades de límites, determinismo, entradas malformadas e integración IER.

El núcleo NO importa angr. Los resúmenes de callee son contratos declarados
de la entrada, nunca inferencias por nombre.
"""
import os
import sys
import json
import hashlib
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)
os.environ["IER_STORE"] = tempfile.mkdtemp(prefix="ier_region_")

from ier import region_analyzer as ra  # noqa: E402

_fallos = []


def _raises(exc, fn):
    try:
        fn()
        return False
    except exc:
        return True


def v(nombre, cond, info=""):
    if cond:
        print("  PASS %-52s" % nombre)
    else:
        print("  FAIL %-52s %s" % (nombre, info))
        _fallos.append(nombre)


def C(cid, base, size, enc="unknown", prov="external_analysis"):
    return {"id": cid, "base": base, "size": size, "encoding": enc, "provenance": prov}


def one(cand, events, oracle=None, artifact=None):
    return ra.analyze({
        "artifact": artifact or {"path": "/fixture/cancel.sys",
                                 "sha256": "bca61f" + "0" * 58,
                                 "kind": "PE"},
        "candidates": [cand],
        "events": events,
        "oracle": oracle,
    })


def decision_of(result, rid="vvar_253"):
    for c in result["candidates"]:
        if c["candidate_id"] == rid:
            return c["decision"]
    return None


def cand_of(result, rid):
    for c in result["candidates"]:
        if c["candidate_id"] == rid:
            return c
    raise AssertionError("candidato no encontrado: %s" % rid)


def cats_of(result, rid="vvar_253"):
    for c in result["candidates"]:
        if c["candidate_id"] == rid:
            return [e["category"] for e in c["evidence"]]
    return []


FIX = C("vvar_253", -44, 20, "ascii", "AIL(AFTER_SSA_LEVEL1)")

print()

# ── núcleo: regiones ─────────────────────────────────────────────
r = ra.make_region("r0", -44, 20)
v("región: intervalo [base, base+size)", r["interval"] == [-44, -24])
v("región: tamaño cero marcado vacío", ra.make_region("r1", 0, 0)["empty"])
v("región: size<0 rechazado", _raises(ValueError, lambda: ra.make_region("r2", 0, -1)))
v("región: base i64 límite superior ok", ra.make_region("r3", 2**63 - 8, 8)["interval"] == [2**63 - 8, 2**63])
v("región: base fuera de i64 rechazada", _raises(ValueError, lambda: ra.make_region("r4", 2**63, 1)))
v("región: tamaño None → unknown_size", ra.make_region("r5", -44, None)["unknown_size"])
v("región: base None → unknown_base", ra.make_region("r6", None, 4)["unknown_base"])
v("región: id vacío rechazado", _raises(ValueError, lambda: ra.make_region("  ", 0, 4)))

# ── núcleo: solapamiento §4 ──────────────────────────────────────
a = ra.make_region("A", 0, 16)
b = ra.make_region("B", 8, 16)
c = ra.make_region("D", 100, 4)
e = ra.make_region("E", 0, 16)
v("overlap parcial → partially_overlap", ra.relation(a, b) == "partially_overlap")
v("idénticas → identical", ra.relation(a, e) == "identical")
v("disjuntas → disjoint", ra.relation(a, c) == "disjoint")
v("contenido → contained", ra.relation(ra.make_region("F", 2, 4), a) == "contained")
v("tamaño desconocido → unknown_size", ra.relation(ra.make_region("G", 0, None), a) == "unknown_size")
v("overlap vacías → False", not ra.overlap(ra.make_region("H", 0, 0), a))
v("solapamiento parcial NO es identidad", ra.relation(a, b) != ra.relation(a, e))

# ── T1: Reference sin Load → ABSTAIN ──────────────────────────────
res = one(FIX, [{"kind": "reference", "region": "vvar_253",
                 "block": "0x140005293", "stmt": 1, "confidence": "HIGH"}])
v("T1 Reference sin Load → ABSTAIN", decision_of(res) == ra.ABSTAIN, decision_of(res))
v("T1 sin leer contenido: no SCALAR_READ", ra.SCALAR_READ not in cats_of(res))

# ── T2: Reference + Load escalar → PRESERVE_SCALAR ─────────────────
res = one(FIX, [{"kind": "reference", "region": "vvar_253",
                 "block": "0x1400052ac", "stmt": 1},
                {"kind": "load", "region": "vvar_253", "block": "0x1400052ac",
                 "stmt": 2, "size": 4, "value_class": "scalar"}])
v("T2 Reference + Load escalar → PRESERVE_SCALAR",
  decision_of(res) == ra.PRESERVE_SCALAR, decision_of(res))

# ── T3: Reference + lectura textual → SAFE_TO_TRANSFORM ────────────
res = one(FIX, [{"kind": "reference", "region": "vvar_253",
                 "block": "0x140005293", "stmt": 1},
                {"kind": "load", "region": "vvar_253", "block": "0x140005293",
                 "stmt": 2, "size": 1, "value_class": "text"}])
v("T3 lectura textual → SAFE_TO_TRANSFORM",
  decision_of(res) == ra.SAFE_TO_TRANSFORM, decision_of(res))

# ── T4: Reference + llamada opaca → ABSTAIN ─────────────────────────
res = one(FIX, [{"kind": "reference", "region": "vvar_253",
                 "block": "0x1400052ac", "stmt": 1},
                {"kind": "call_arg", "region": "vvar_253", "block": "0x1400052ac",
                 "stmt": 2, "arg_pos": 1,
                 "callee": {"name": "sub_opaque", "classification": "opaque",
                            "unknown": True}}])
v("T4 llamada opaca → ABSTAIN", decision_of(res) == ra.ABSTAIN, decision_of(res))
v("T4 registra ADDRESS_ESCAPE", ra.ADDRESS_ESCAPE in cats_of(res))

# ── T5: Reference a región disjunta → SAFE_TO_TRANSFORM ─────────────
alt = C("vvar_260", -92, 4)
res = ra.analyze({
    "artifact": {"path": "/f", "sha256": "ab12" + "0" * 60, "kind": "PE"},
    "candidates": [FIX, alt],
    "events": [{"kind": "reference", "region": "vvar_260",
                "block": "0x1400053c2", "stmt": 2},
               {"kind": "successor_scan", "region": "vvar_253",
                "block": "0x1400053c2", "stmt": 99, "result": "clean",
                "complete": True}],
    "oracle": None})
v("T5 región disjunta, escaneo completo limpio → SAFE_TO_TRANSFORM",
  decision_of(res, "vvar_253") == ra.SAFE_TO_TRANSFORM, decision_of(res, "vvar_253"))
v("T5 relaciones reportan disjoint",
  any(r_["relation"] == "disjoint" for r_ in res["relations"]))

# ── T6: solapamiento parcial → ABSTAIN ─────────────────────────────
over = C("vvar_271", -48, 16)
res = ra.analyze({
    "artifact": {"path": "/f", "sha256": "ab12" + "0" * 60, "kind": "PE"},
    "candidates": [FIX, over],
    "events": [{"kind": "load", "region": "vvar_253", "size": 1,
                "value_class": "text", "block": "0x1", "stmt": 1}],
    "oracle": None})
v("T6 solapamiento parcial → ABSTAIN",
  decision_of(res, "vvar_253") == ra.ABSTAIN, decision_of(res, "vvar_253"))

# ── T7: alias confirmado → SAFE_TO_TRANSFORM ───────────────────────
alias_a = C("vvar_252", -44, 20, "binary")
res = ra.analyze({
    "artifact": {"path": "/f", "sha256": "ab12" + "0" * 60, "kind": "PE"},
    "candidates": [FIX, alias_a],
    "events": [{"kind": "alias", "region": "vvar_252", "other": "vvar_253",
                "confirmed": True, "block": "0x14000526e", "stmt": 4},
               {"kind": "load", "region": "vvar_253", "size": 1,
                "value_class": "text", "block": "0x1", "stmt": 2}],
    "oracle": None})
v("T7 alias confirmado → SAFE_TO_TRANSFORM",
  decision_of(res, "vvar_253") == ra.SAFE_TO_TRANSFORM, decision_of(res, "vvar_253"))
v("T7 registra ALIAS_CONFIRMED",
  ra.ALIAS_CONFIRMED in cats_of(res, "vvar_252"))

# ── T8: alias no resuelto → ABSTAIN ────────────────────────────────
res = ra.analyze({
    "artifact": {"path": "/f", "sha256": "ab12" + "0" * 60, "kind": "PE"},
    "candidates": [FIX, alias_a],
    "events": [{"kind": "alias", "region": "vvar_252", "other": "vvar_253",
                "confirmed": False, "block": "0x14000526e", "stmt": 4},
               {"kind": "load", "region": "vvar_253", "size": 1,
                "value_class": "text", "block": "0x1", "stmt": 2}],
    "oracle": None})
v("T8 alias no resuelto → ABSTAIN",
  decision_of(res, "vvar_253") == ra.ABSTAIN, decision_of(res, "vvar_253"))

# ── T9: escritura exclusiva → SAFE_TO_TRANSFORM ────────────────────
res = one(FIX, [{"kind": "store", "region": "vvar_253", "block": "0x14000526e",
                 "stmt": i, "data_class": "const"} for i in range(18)])
v("T9 escritura exclusiva → SAFE_TO_TRANSFORM",
  decision_of(res) == ra.SAFE_TO_TRANSFORM, decision_of(res))

# ── T10: read-modify-write → SAFE_TO_TRANSFORM ─────────────────────
res = one(FIX, [{"kind": "rmw", "region": "vvar_253", "block": "0x140005293",
                 "stmt": 2}])
v("T10 RMW loop → SAFE_TO_TRANSFORM",
  decision_of(res) == ra.SAFE_TO_TRANSFORM, decision_of(res))
v("T10 registra READ_MODIFY_WRITE",
  ra.READ_MODIFY_WRITE in cats_of(res))

# ── T11: Store de terminador → SAFE_TO_TRANSFORM ───────────────────
res = one(FIX, [{"kind": "store", "region": "vvar_253", "block": "0x1400052ac",
                 "stmt": 2, "terminator": True}])
v("T11 terminador → SAFE_TO_TRANSFORM",
  decision_of(res) == ra.SAFE_TO_TRANSFORM, decision_of(res))

# ── T12: callee que conserva el puntero (textual) ──────────────────
res = one(FIX, [{"kind": "call_arg", "region": "vvar_253", "block": "0x1",
                 "stmt": 1, "arg_pos": 1,
                 "callee": {"name": "RtlInitUnicodeString",
                            "classification": "external-contract",
                            "text_consuming": True,
                            "writes_args": [0],
                            "preserves_pointer_args": [1]}}])
v("T12 callee preserva puntero (textual) → SAFE_TO_TRANSFORM",
  decision_of(res) == ra.SAFE_TO_TRANSFORM, decision_of(res))

# ── T13: callee que escribe escalar mediante puntero ───────────────
res = one(FIX, [{"kind": "call_arg", "region": "vvar_253", "block": "0x1",
                 "stmt": 1, "arg_pos": 1,
                 "callee": {"name": "opaque_writer",
                            "classification": "inspected",
                            "writes_candidate_scalar": True}}])
v("T13 callee escribe escalar → PRESERVE_SCALAR",
  decision_of(res) == ra.PRESERVE_SCALAR, decision_of(res))

# ── T14: sucesores alternativos sin prueba → ABSTAIN ───────────────
res = one(FIX, [{"kind": "branch", "region": "vvar_253", "block": "0x1",
                 "stmt": 1, "branch_class": "jcc"},
                {"kind": "successor_scan", "region": "vvar_253", "block": "0x1",
                 "stmt": 2, "result": "conflict"}])
v("T14 sucesores alternativos/conflictivos → ABSTAIN",
  decision_of(res) == ra.ABSTAIN, decision_of(res))

# ── T15: descendientes no alcanzables excluidos ─────────────────────
res = one(FIX, [{"kind": "load", "region": "vvar_253", "size": 1,
                 "value_class": "text", "block": "0x1", "stmt": 1},
                {"kind": "successor_scan", "region": "vvar_253", "block": "0x1",
                 "stmt": 99, "result": "unreachable"}])
v("T15 descendientes no alcanzables no vetan → SAFE_TO_TRANSFORM",
  decision_of(res) == ra.SAFE_TO_TRANSFORM, decision_of(res))

# ── T16: evidencias contradictorias → ABSTAIN ──────────────────────
res = one(FIX, [{"kind": "load", "region": "vvar_253", "size": 8,
                 "value_class": "scalar", "block": "0x1", "stmt": 1,
                 "confidence": "HIGH"},
                {"kind": "load", "region": "vvar_253", "size": 1,
                 "value_class": "text", "block": "0x1", "stmt": 2,
                 "confidence": "HIGH"}])
v("T16 escalar+textual simultáneos → ABSTAIN",
  decision_of(res) == ra.ABSTAIN, decision_of(res))
res_c = res["candidates"][0]
v("T16 registra contradicción", res_c["contradiction"] is True)

# ── M10.6 · linaje SSA y evidencia por intervalos ───────────────────

def two(cands, events, oracle=None):
    return ra.analyze({
        "artifact": {"path": "/fixture/x", "sha256": "ab12" + "0" * 60, "kind": "PE"},
        "candidates": cands, "events": events, "oracle": oracle})

S_A = {"id": "ssa_a", "base": -44, "size": 20, "storage": "frame:-44:20",
       "encoding": "ascii"}
S_B = {"id": "ssa_b", "base": -44, "size": 20, "storage": "frame:-44:20",
       "encoding": "binary"}
D_A = dict(S_A, storage="frame:A")
D_B = dict(S_B, storage="frame:B")

# N1/N12/N13. Dos etiquetas SSA del mismo almacenamiento: propagación
res = two([S_A, S_B], [{"kind": "load", "region": "ssa_a", "size": 8,
                        "value_class": "scalar", "block": "0x1", "stmt": 1}])
v("N1 mismo almacenamiento, SSA distintos → escalar propaga a ambos",
  decision_of(res, "ssa_a") == ra.PRESERVE_SCALAR and
  decision_of(res, "ssa_b") == ra.PRESERVE_SCALAR)
db_evid = [e for e in res["candidates"][1]["evidence"]
           if e["category"] == ra.SCALAR_READ]
v("N1 evidencias derivadas conservan intervalo e indican origen",
  any(e.get("derived") and e["interval"] == [-44, -36] for e in db_evid))

# N2/N10. Mismo valor, distinto almacenamiento declarado → NO propagan
res = two([D_A, D_B], [{"kind": "load", "region": "ssa_a", "size": 8,
                        "value_class": "scalar", "block": "0x1", "stmt": 1},
                       {"kind": "store", "region": "ssa_b", "block": "0x1",
                        "stmt": 2}])
v("N2 mismo intervalo, storage distinto → escalar NO contamina B",
  decision_of(res, "ssa_a") == ra.PRESERVE_SCALAR and
  decision_of(res, "ssa_b") == ra.SAFE_TO_TRANSFORM)

# N12. storage por defecto (base/size) → propagación automática
res = two([dict(S_A, storage=None), dict(S_B, storage=None)],
          [{"kind": "load", "region": "ssa_a", "size": 4,
            "value_class": "scalar", "block": "0x1", "stmt": 1}])
v("N12 storage por defecto desde base/size → propagación activa",
  decision_of(res, "ssa_b") == ra.PRESERVE_SCALAR)

# N3. Copia parcial: mapping byte a byte en la zona copiada
P = {"id": "parent", "base": -40, "size": 8}
CH = {"id": "child", "base": -80, "size": 4}
res = two([P, CH], [
    {"kind": "copy", "region": "child", "from_region": "parent",
     "parent_offset": 2, "offset": 0, "size": 4, "block": "0x1", "stmt": 1},
    {"kind": "load", "region": "child", "size": 4, "value_class": "scalar",
     "block": "0x1", "stmt": 2}])
p_scalar = [e for e in cand_of(res, "parent")["evidence"]
            if e["category"] == ra.SCALAR_READ and e.get("derived")]
v("N3 copia parcial: escalar del hijo mapea a [padre+2, padre+6)",
  any(e["interval"] == [-38, -34] for e in p_scalar))
v("N3 copia parcial: decisión PRESERVE en ambos lados",
  decision_of(res, "parent") == ra.PRESERVE_SCALAR and
  decision_of(res, "child") == ra.PRESERVE_SCALAR)

# N4. Solapamiento con lectura escalar dentro de la intersección → PRESERVE
res = two([FIX, over], [{"kind": "load", "region": "vvar_253", "size": 4,
                         "value_class": "scalar", "block": "0x1", "stmt": 1}])
v("N4 solapamiento + escalar en la intersección → PRESERVE_SCALAR",
  decision_of(res, "vvar_253") == ra.PRESERVE_SCALAR)

# N5. Solapamiento: lectura fuera de la intersección, compartida sin observar
res = two([FIX, over], [{"kind": "load", "region": "vvar_253", "offset": 16,
                         "size": 4, "value_class": "text",
                         "block": "0x1", "stmt": 1}])
v("N5 lectura solo fuera de la intersección → ABSTAIN (fail-closed)",
  decision_of(res, "vvar_253") == ra.ABSTAIN)
n5_ivs = [e.get("interval") for e in cand_of(res, "vvar_253")["evidence"]]
v("N5 la evidencia identifica los bytes compartidos [-44, -32)",
  [-44, -32] in n5_ivs)

# N6. Contradicción entre evidencia local y evidencia derivada (mismo storage)
res = two([S_A, S_B], [
    {"kind": "load", "region": "ssa_a", "size": 1, "value_class": "text",
     "block": "0x1", "stmt": 1},
    {"kind": "load", "region": "ssa_b", "size": 8, "value_class": "scalar",
     "block": "0x1", "stmt": 2}])
v("N6 contradicción local-vs-derivada → ABSTAIN",
  decision_of(res, "ssa_a") == ra.ABSTAIN)
v("N6 contradicción visible",
  cand_of(res, "ssa_a")["contradiction"] is True)

# N7. Dos operaciones sobre intervalos disjuntos: sin contaminación
P7 = {"id": "p7", "base": -100, "size": 16}
Q7 = {"id": "q7", "base": -200, "size": 16}
res = two([P7, Q7], [{"kind": "load", "region": "p7", "size": 4,
                      "value_class": "scalar", "block": "0x1", "stmt": 1},
                     {"kind": "load", "region": "q7", "size": 1,
                      "value_class": "text", "block": "0x1", "stmt": 2}])
v("N7 intervalos disjuntos: escalares de p7 no contaminan q7",
  decision_of(res, "p7") == ra.PRESERVE_SCALAR and
  decision_of(res, "q7") == ra.SAFE_TO_TRANSFORM)

# N8/N14. XOR reversible con clave demostrada → TEXTUAL_READ con payload
bytes19 = [0xd8, 0xfd, 0xd7, 0xe6, 0xfc, 0xe0, 0xf2, 0xea, 0xd6, 0xf8,
           0xf1, 0xf9, 0xfe, 0xea, 0xcb, 0xd9, 0xd1, 0xc7, 0xa3]
evs = [{"kind": "store", "region": "vvar_253", "block": "0x1", "stmt": i,
        "offset": i, "size": 1, "value": b} for i, b in enumerate(bytes19)]
evs.append({"kind": "rmw", "region": "vvar_253", "block": "0x1", "stmt": 100,
            "offset": 0, "size": 18,
            "xor": {"index_base": 145,
                    "formula": "decoded[i] = stored[i] ^ ((i - 111) & 0xff)"}})
res = one(FIX, evs)
txt = [e for e in res["candidates"][0]["evidence"]
       if "xor-decode" in e["op"]]
v("N8/N14 XOR reversible clave demostrada → TEXTUAL_READ del buffer",
  txt and txt[0]["category"] == ra.TEXTUAL_READ
  and "IoDriverObjectType" in txt[0]["op"])

# N9. XOR sin clave demostrada → no se reconstruye el contenido
evs9 = [dict(e) for e in evs]
evs9[-1] = {"kind": "rmw", "region": "vvar_253", "block": "0x1", "stmt": 100,
            "offset": 0, "size": 18}
res = one(FIX, evs9)
txt9 = [e for e in res["candidates"][0]["evidence"] if "xor-" in e["op"]]
v("N9 XOR sin clave → contenido NO reconstruido",
  any(e["op"] == "xor-key-unproven" for e in txt9))
lim9 = res["candidates"][0]["limitations"]
v("N9 limitation declara clave no demostrada",
  any("clave XOR" in l for l in lim9))

# N11. alias_possible sin confirmación → sin propagación
res = two([D_A, D_B], [
    {"kind": "alias", "region": "ssa_a", "other": "ssa_b", "confirmed": False,
     "block": "0x1", "stmt": 1},
    {"kind": "load", "region": "ssa_a", "size": 8, "value_class": "scalar",
     "block": "0x1", "stmt": 2}])
v("N11 alias posible sin confirmar → escalar NO propaga a B",
  decision_of(res, "ssa_b") != ra.PRESERVE_SCALAR)

# N15. Determinismo con linaje: evidencias derivadas deduplicadas
res1 = two([S_A, S_B], [{"kind": "load", "region": "ssa_a", "size": 4,
                         "value_class": "scalar", "block": "0x1", "stmt": 1}])
res2 = two([S_A, S_B], [{"kind": "load", "region": "ssa_a", "size": 4,
                         "value_class": "scalar", "block": "0x1", "stmt": 1}])
v("N15 determinismo con linaje SSA",
  json.dumps(res1, sort_keys=True) == json.dumps(res2, sort_keys=True))

# N16. Propagación incorrecta entre almacenamientos distintos (anti-fusión)
res = two([D_A, D_B], [{"kind": "rmw", "region": "ssa_a", "block": "0x1",
                        "stmt": 1},
                       {"kind": "call_arg", "region": "ssa_b",
                        "block": "0x1", "stmt": 2, "arg_pos": 1,
                        "callee": {"name": "sink", "classification": "opaque",
                                   "unknown": True}}])
v("N16 almacenamiento distinto → evidencia de A no cambia callee de B",
  ra.ADDRESS_ESCAPE in cats_of(res, "ssa_b") and
  ra.ADDRESS_ESCAPE not in cats_of(res, "ssa_a"))

# ── M10.7 · resúmenes sellados y oráculos ──────────────────────────

def sealed_summary(**overrides):
    body = {
        "name": "sub_test", "classification": "inspected",
        "reads_args": [0, 1], "writes_args": [],
        "writes_through_args": [], "preserves_pointer_args": [0, 1],
        "text_consuming": True, "writes_candidate_scalar": False,
        "unknown": False, "complete": True,
        "side_effects": [],
        "validity": ["arg1 es cadena terminada en NUL legible"],
        "evidence": ["cuerpo inspeccionado", "sin Stores fuera de prólogo (objdump)"],
    }
    body.update(overrides)
    return ra.seal_call_summary(body)

TXT = {"kind": "load", "region": "vvar_253", "size": 1, "value_class": "text",
       "block": "0x1", "stmt": 1}

# N17. Resumen completo VALIDADO: consumo textual demostrado → SAFE
res = one(FIX, [TXT,
                {"kind": "call_arg", "region": "vvar_253", "block": "0x1",
                 "stmt": 2, "arg_pos": 1, "callee": sealed_summary()}])
v("N17 resumen completo válido → SAFE_TO_TRANSFORM",
  decision_of(res) == ra.SAFE_TO_TRANSFORM)
v("N17 resumen sellado registrado en procedencia",
  any((e.get("provenance") or {}).get("summary_seal") for e in
      res["candidates"][0]["evidence"]))

# N18. Sello manipulado → rechazado → veto ABSTAIN
bad = sealed_summary()
bad = dict(bad, side_effects=["writes through arg1 somewhere"])
res = one(FIX, [TXT,
                {"kind": "call_arg", "region": "vvar_253", "block": "0x1",
                 "stmt": 2, "arg_pos": 1, "callee": bad}])
v("N18 sello inválido → resumen rechazado → ABSTAIN",
  decision_of(res) == ra.ABSTAIN)

# N19. Resumen completo con efecto desconocido declarado → rechazado
res = one(FIX, [TXT,
                {"kind": "call_arg", "region": "vvar_253", "block": "0x1",
                 "stmt": 2, "arg_pos": 1,
                 "callee": sealed_summary(side_effects=["unknown: writes maybe"])}])
v("N19 efecto desconocido en resumen completo → ABSTAIN",
  decision_of(res) == ra.ABSTAIN)

# N20. Resumen contradictorio (text_consuming + writes_candidate_scalar) → rechazado
res = one(FIX, [TXT,
                {"kind": "call_arg", "region": "vvar_253", "block": "0x1",
                 "stmt": 2, "arg_pos": 1,
                 "callee": sealed_summary(text_consuming=True,
                                          writes_candidate_scalar=True)}])
v("N20 contradicción en resumen → ABSTAIN",
  decision_of(res) == ra.ABSTAIN)

# N21. Resumen completo sin evidencias/validity → rechazado
res = one(FIX, [TXT,
                {"kind": "call_arg", "region": "vvar_253", "block": "0x1",
                 "stmt": 2, "arg_pos": 1,
                 "callee": sealed_summary(evidence=[], validity=[])}])
v("N21 sin evidencias → ABSTAIN",
  decision_of(res) == ra.ABSTAIN)

# N22. Resumen completo válido sin efectos demostrados → registrado sin vetar
res = one(FIX, [TXT,
                {"kind": "call_arg", "region": "vvar_253", "block": "0x1",
                 "stmt": 2, "arg_pos": 1,
                 "callee": sealed_summary(text_consuming=False)}])
v("N22 completo válido sin efectos → SAFE (consumo textual previo)",
  decision_of(res) == ra.SAFE_TO_TRANSFORM)

# N23. Alias condicional (confirmed=false, alcance de rama) → sin propagación
res = two([D_A, D_B], [
    {"kind": "alias", "region": "ssa_a", "other": "ssa_b", "confirmed": False,
     "block": "0x1", "stmt": 1, "scope": "branch"},
    {"kind": "load", "region": "ssa_a", "size": 8, "value_class": "scalar",
     "block": "0x1", "stmt": 2}])
v("N23 alias condicional → escalar NO propaga a B",
  decision_of(res, "ssa_b") != ra.PRESERVE_SCALAR)

# N24. XOR sobre wide chars (unit_size=2): decoded units imprimibles → TEXTUAL_READ
evs24 = [{"kind": "store", "region": "vvar_253", "block": "0x1", "stmt": 0,
          "offset": 0, "size": 2, "value": 0x00DE},
         {"kind": "store", "region": "vvar_253", "block": "0x1", "stmt": 1,
          "offset": 2, "size": 2, "value": 0x00F0},
         {"kind": "rmw", "region": "vvar_253", "block": "0x1", "stmt": 2,
          "offset": 0, "size": 4,
          "xor": {"index_base": 145, "unit_size": 2}}]
res = one(FIX, evs24)
txt24 = [e for e in res["candidates"][0]["evidence"] if "xor16-decode" in e["op"]]
v("N24 XOR wide char demostrado → TEXTUAL_READ con 'Ob'",
  txt24 and "Ob" in txt24[0]["op"])

# N25. Escrituras indirectas vía writes_through_args → SCALAR_READ → PRESERVE
res = one(FIX, [{"kind": "call_arg", "region": "vvar_253", "block": "0x1",
                 "stmt": 1, "arg_pos": 0,
                 "callee": sealed_summary(text_consuming=False,
                                          writes_through_args=[0])}])
v("N25 escritura indirecta a través de puntero → PRESERVE_SCALAR",
  decision_of(res) == ra.PRESERVE_SCALAR)

# N26. Ruta incompleta (unaligned unit_size desconocido) → no reconstruye
evs26 = [dict(e) for e in evs24[:2]]
evs26.append({"kind": "rmw", "region": "vvar_253", "block": "0x1", "stmt": 2,
              "offset": 0, "size": 4,
              "xor": {"index_base": 145, "unit_size": 3}})
res = one(FIX, evs26)
har26 = [e for e in res["candidates"][0]["evidence"] if "xor-unit-unsupported" in e["op"]]
v("N26 unit_size no soportado → no reconstrucción",
  len(har26) == 1)

# N27. Vidas disjuntas demostradas por CFG → clasificación TEMPORALLY_ALIASED
RES27 = dict(FIX, storage="frame:-44:20",
             live_range={"start_block": "0x14000526e", "end_block": "0x1400052c9"})
RES271 = dict(over, storage="frame:-48:16",
              live_range={"start_block": "0x1400053c2", "end_block": "0x1400053de"})
res = ra.analyze({
    "artifact": {"path": "/f", "sha256": "ab12" + "0" * 60, "kind": "PE"},
    "candidates": [RES27, RES271],
    "events": [{"kind": "store", "region": "vvar_253", "block": "0x14000526e",
                "stmt": 0, "offset": 0, "size": 1, "value": 0x41}],
    "cfg_successors": {"0x14000526e": ["0x1400052ac"],
                       "0x1400052ac": ["0x1400052c9"],
                       "0x1400052c9": ["0x1400053c2"],
                       "0x1400053c2": ["0x1400053de"],
                       "0x1400053de": []},
    "assurance": {"coverage": "complete"},
    "oracle": None})
alias27 = [c for c in res["alias_classifications"]
           if c["a"] == "vvar_253" and c["b"] == "vvar_271"]
v("N27 vidas disjuntas (CFG) → TEMPORALLY_ALIASED",
  alias27 and alias27[0]["classification"] == "TEMPORALLY_ALIASED")

# ── duplicados deterministas ───────────────────────────────────────
ev_dup = {"kind": "load", "region": "vvar_253", "size": 4,
          "value_class": "scalar", "block": "0x1", "stmt": 1}
res = one(FIX, [ev_dup, dict(ev_dup)])
n = len([e for e in res["candidates"][0]["evidence"]
         if e["category"] == ra.SCALAR_READ])
v("evidencias duplicadas colapsadas", n == 1, "n=%d" % n)

# ── límites: size cero, offset negativo, i64 ──────────────────────
res = one(C("zerosize", -10, 0), [])
v("size=0: ABSTAIN honesta, sin inventar",
  decision_of(res, "zerosize") == ra.ABSTAIN)
neg = C("neg", -4096, 8)
res = one(neg, [{"kind": "load", "region": "neg", "size": 8,
                 "value_class": "scalar", "block": "0x1", "stmt": 1}])
v("offset negativo válido → PRESERVE_SCALAR",
  decision_of(res, "neg") == ra.PRESERVE_SCALAR)
big = C("big", 2**62, 16)
res = one(big, [{"kind": "store", "region": "big", "block": "0x1", "stmt": 1}])
v("offset grande i64 → SAFE_TO_TRANSFORM",
  decision_of(res, "big") == ra.SAFE_TO_TRANSFORM)

# ── tamaño desconocido → ABSTAIN ───────────────────────────────────
res = one(C("unk", -44, None), [{"kind": "load", "region": "unk", "size": 4,
                                 "value_class": "scalar", "block": "0x1",
                                 "stmt": 1}])
v("tamaño desconocido → ABSTAIN (nunca se inventa)",
  decision_of(res, "unk") == ra.ABSTAIN)

# ── entradas malformadas ───────────────────────────────────────────
for nombre, payload in [
        ("payload no dict", None),
        ("candidates lista vacía", {"candidates": [], "events": []}),
        ("candidato size negativo", {"candidates": [{"id": "x", "base": 0, "size": -3}],
                                     "events": []}),
        ("evento con región desconocida", {"candidates": [C("ok", 0, 4)],
                                           "events": [{"kind": "load", "region": "nope",
                                                       "block": "0x1", "stmt": 1}]}),
        ("evento con kind desconocido", {"candidates": [C("ok2", 0, 4)],
                                         "events": [{"kind": "teleport", "region": "ok2"}]}),
        ]:
    res = ra.analyze(payload)
    v("malformada: %s → BLOCKED" % nombre,
      res["operational_status"] == ra.OP_BLOCKED)

# ── determinismo ───────────────────────────────────────────────────
def run():
    return json.dumps(one(FIX, [
        {"kind": "store", "region": "vvar_253", "block": "0x14000526e", "stmt": i}
        for i in range(4)] + [
        {"kind": "rmw", "region": "vvar_253", "block": "0x140005293", "stmt": 9},
    ]), sort_keys=True, separators=(",", ":"))

v("determinismo: misma entrada → misma salida canónica", run() == run())

# ── PROVEN exige oráculo independiente ────────────────────────────
res_no = one(FIX, [{"kind": "load", "region": "vvar_253", "size": 1,
                    "value_class": "text", "block": "0x1", "stmt": 1}])
res_yes = one(FIX, [{"kind": "load", "region": "vvar_253", "size": 1,
                     "value_class": "text", "block": "0x1", "stmt": 1}],
              oracle={"independent": True, "tool": "equiv_check",
                      "result": "PASS"})
v("sin oráculo independiente → PARTIAL (nunca PROVEN)",
  res_no["epistemic_status"] == ra.EP_PARTIAL)
v("con oráculo independiente PASS → PROVEN",
  res_yes["epistemic_status"] == ra.EP_PROVEN and
  all(c["epistemic_status"] == ra.EP_PROVEN
      for c in res_yes["candidates"]))

# ── evidencia: campos TIERRA completos ─────────────────────────────
res = one(FIX, [{"kind": "rmw", "region": "vvar_253", "block": "0x140005293",
                 "stmt": 2,
                 "provenance": {"artifact_sha256": "deadbeef"}}])
ev0 = res["candidates"][0]["evidence"][0]
for campo in ("id", "category", "subject", "object", "op", "location", "source",
              "scope", "confidence", "justification", "related", "provenance"):
    v("evidencia contiene %s" % campo, campo in ev0)
v("evidencia id determinista", ev0["id"].startswith("ev-"))

# ── ausencia de evidencia ≠ evidencia de ausencia ──────────────────
res = one(FIX, [])
cats = cats_of(res)
v("sin observaciones → ABSTAIN, NO_OBSERVATION registrada",
  decision_of(res) == ra.ABSTAIN and ra.NO_OBSERVATION in cats)

# ── integración IER: registro como capacidad DECLARED, sin promoción ─
from ier import capability  # noqa: E402
tmp = tempfile.mkdtemp(prefix="ier_ra_cap_")
art = os.path.join(tmp, "ra.py")
with open(art, "w") as fh:
    fh.write(open(os.path.join(PKG, "ier", "region_analyzer.py")).read())
stub = ra.as_capability_stub()
cap = capability.declarar(name=stub["name"], purpose=stub["purpose"],
                          domain=stub["domain"], ruta=art,
                          version="1.0.0", limitations=stub["limitations"],
                          source_mission_id="mis_m105")
v("IER: capacidad declarable (DECLARED)", cap["status"] == "DECLARED")
try:
    capability.transitar(cap["capability_id"], "PROMOTED", "auto")
    v("IER: PROMOTED sigue requiriendo dictado", False)
except PermissionError:
    v("IER: PROMOTED sigue requiriendo dictado", True)

sel = ra.select_capability()
v("ROUTER: selección expone decisiones y categorías",
  sel["available"] and set(sel["decisions"]) == {ra.PRESERVE_SCALAR, ra.ABSTAIN,
                                                 ra.SAFE_TO_TRANSFORM})

print()
if _fallos:
    print("region_analyzer FALLA:", _fallos)
    sys.exit(1)
print("region_analyzer: OK")
sys.exit(0)
