#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""IER-106 · VERIFY — certificado de identidad independiente por hash sellado."""
import os
import sys
import json
import hashlib
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)

from ier import verify, mission  # noqa: E402

_fallos = []


def v(nombre, cond, info=""):
    if cond:
        print("  PASS %-50s" % nombre)
    else:
        print("  FAIL %-50s %s" % (nombre, info))
        _fallos.append(nombre)


# fixture estable sellado por hash
tmp = tempfile.mkdtemp(prefix="ier_cert_")
art = os.path.join(tmp, "fixture.elf")
with open(art, "wb") as f:
    f.write(b"\x7fELF" + b"sealed-content")
art_sha = hashlib.sha256(open(art, "rb").read()).hexdigest()

# 1) emitir certificado con oraculo independiente real
cert = verify.emitir(
    mission_id="mis_fixture",
    artefacto=art,
    verificaciones=[
        {"criterion": "RESOLVES", "name": "decodes_deterministically",
         "result": "PASS", "evidence": "sha256 estable en 2 runs"},
        {"criterion": "REPRODUCTION", "name": "fresh_clone_matches",
         "result": "PASS", "evidence": "verify-clone rc=0"},
        {"criterion": "NEGATIVE_CONTROL", "name": "corrupted_fixture_rejected",
         "result": "PASS", "evidence": "hash distinto -> REJECT"},
    ],
    oraculo_independiente={
        "producer_of_result": "rxre-test-harness",
        "oracle_tool": "sha256sum (coreutils)",
        "why_independent": "hash externo, no codigo del productor",
    },
    estado="PARTIAL",
    path=os.path.join(tmp, "cert_fixture.json"))
v("cert generado PARTIAL", cert["state"] == "PARTIAL")
v("cert id bien formado", cert["certificate_id"].startswith("cert_"))
v("cert estable hash artefacto", cert["artifact"]["sha256"] == art_sha)

# 2) revalidar el certificado
r = verify.verificar(cert)
v("verificar certificado OK", r["integridad_ok"])

# 3) verificacion de artefacto alterado
bad_art = os.path.join(tmp, "fixture_bad.elf")
open(bad_art, "wb").close()
cert["artifact"]["path"] = bad_art
r2 = verify.verificar(cert)
v("artifact distinto -> falla verificación", not r2["integridad_ok"])

# 4) oraculo del productor no aceptado como independiente
cert_prod_own = verify.emitir(
    mission_id="mis_fixture",
    artefacto=art,
    verificaciones=[{"criterion": "RESOLVES", "name": "decodes_deterministically",
                     "result": "PASS", "evidence": "sha256 estable en 2 runs"}],
    oraculo_independiente={
        "producer_of_result": "rxre",
        "oracle_tool": "rxre-test-harness",
        "why_independent": "n/a",
    },
    estado="PARTIAL")
r3 = verify.verificar(cert_prod_own)
v("productor como oráculo -> no verificador", not r3["integridad_ok"])

# 5) decision REJECT cuando hay FAIL interno
cert_fail = verify.emitir(
    mission_id="mis_fixture",
    artefacto=art,
    verificaciones=[{"criterion": "RESOLVES", "name": "x", "result": "FAIL", "evidence": ""}],
    oraculo_independiente={
        "producer_of_result": "rxre-test-harness",
        "oracle_tool": "sha256sum",
        "why_independent": "x",
    })
v("FAIL interno -> REJECT", verify.decidir(cert_fail) == "REJECT")

# 6) decisión sin verificaciones=no es PASS silencioso
cert_empty_checks = verify.emitir(
    mission_id="mis_fixture", artefacto=art,
    verificaciones=[{"criterion": "RESOLVES", "name": "x", "result": "PASS",
                     "evidence": "x"}],
    oraculo_independiente={
        "producer_of_result": "rxre-test-harness",
        "oracle_tool": "sha256sum",
        "why_independent": "x",
    },
    estado="PARTIAL")
v("certificado PARTIAL decide PARTIAL",
  verify.decidir(cert_empty_checks) == "PARTIAL")

print()
if _fallos:
    print("IER verify FALLA:", _fallos)
    sys.exit(1)
print("IER verify OK")
sys.exit(0)
