"""RXRE-EQUIV (morluto/rea#4972 slice): verificación acotada de equivalencia
semántica nativa para funciones escalares entero → entero.

Controls:
  - candidato correcto distinto algoritmo        → PROVEN
  - candidato incorrecto (x*25 vs x*256)        → MISMATCH + confirmación nativa
  - candidato incorrecto con rama               → MISMATCH
  - --no-symbolic                               → TESTED_ONLY
  - original ausente / candidato inválido       → INCONCLUSIVE
"""
import ctypes
import hashlib
import json
import os
import subprocess
import sys
import tempfile

import pytest

REPO_ROOT = '/home/lucas/Escritorio/rxre'
sys.path.insert(0, REPO_ROOT)

from tools.rxre.semantic import equiv_check

ORIG_C = r"""
#include <stdint.h>
uint64_t f(uint64_t x){ return x * 256; }
"""
CAND_OK_C = r"""
#include <stdint.h>
uint64_t f(uint64_t x){ return x << 8; }
"""
CAND_OK2_C = r"""
#include <stdint.h>
uint64_t f(uint64_t x){ return x * 128 + x * 128; }
"""
CAND_BAD_C = r"""
#include <stdint.h>
uint64_t f(uint64_t x){ return x * 25; }
"""
BR_C = r"""
#include <stdint.h>
uint64_t f(uint64_t x){ if (x > 100) return x - 100; return 100 - x; }
"""
BR_BAD_C = r"""
#include <stdint.h>
uint64_t f(uint64_t x){ if (x > 100) return x - 100; return 99 - x; }
"""


def gcc_available():
    try:
        out = subprocess.run(["gcc", "--version"], capture_output=True, timeout=30)
        return out.returncode == 0
    except Exception:
        return False


def angr_available():
    try:
        import angr  # noqa: F401
        return True
    except Exception:
        return False


pytestmark = [pytest.mark.skipif(not gcc_available(), reason="gcc ausente"),
              pytest.mark.skipif(not angr_available(), reason="angr ausente")]


@pytest.fixture(scope="module")
def build(tmp_path_factory):
    d = tmp_path_factory.mktemp("equiv")
    paths = {}
    for name, src in [("orig", ORIG_C), ("cand_ok", CAND_OK_C), ("cand_ok2", CAND_OK2_C),
                      ("cand_bad", CAND_BAD_C), ("br", BR_C), ("br_bad", BR_BAD_C)]:
        p = os.path.join(d, name + ".c")
        with open(p, "w") as fh:
            fh.write(src)
        so = os.path.join(d, name + ".so")
        subprocess.run(["gcc", "-O2", "-fPIC", "-shared", "-o", so, p],
                       check=True, capture_output=True, timeout=120)
        paths[name] = (p, so)
    return paths


def test_proven_equivalent_alt_algorithm(build):
    orig_c, orig_so = build["orig"]
    _, _ = build["cand_ok"]
    cand_src, _ = build["cand_ok"]
    r = equiv_check.check(orig_so, "f", cand_src, sig="u64", cases=32, seed=1)
    assert r["result"] == "PROVEN", json.dumps(r, indent=2)
    assert r["counterexample"] is None
    assert r["hashes"]["orig"] == hashlib.sha256(open(orig_so, "rb").read()).hexdigest()


def test_proven_different_but_equal_algorithm(build):
    _, orig_so = build["orig"]
    cand_src, _ = build["cand_ok2"]
    r = equiv_check.check(orig_so, "f", cand_src, sig="u64", cases=32, seed=1)
    assert r["result"] == "PROVEN", json.dumps(r, indent=2)


def test_mismatch_wrong_candidate(build):
    _, orig_so = build["orig"]
    cand_src, _ = build["cand_bad"]
    r = equiv_check.check(orig_so, "f", cand_src, sig="u64", cases=32, seed=1)
    assert r["result"] == "MISMATCH"
    assert r["counterexample"]
    # confirmación independiente: ctypes directo, sin pasar por el módulo
    lib = ctypes.CDLL(orig_so)
    f1 = ctypes.cast(getattr(lib, "f"), ctypes.CFUNCTYPE(ctypes.c_uint64, ctypes.c_uint64))
    kc = ctypes.CDLL(os.path.join(os.path.dirname(cand_src), "cand_bad.so"))
    f2 = ctypes.cast(getattr(kc, "f"), ctypes.CFUNCTYPE(ctypes.c_uint64, ctypes.c_uint64))
    v = int(r["counterexample"], 16)
    assert f1(v) != f2(v)


def test_branchy_proven_and_branchy_mismatch(build):
    _, br_so = build["br"]
    br_src, _ = build["br"]
    r = equiv_check.check(br_so, "f", br_src, sig="u64", cases=32, seed=1)
    assert r["result"] == "PROVEN", json.dumps(r, indent=2)
    br_bad_src, _ = build["br_bad"]
    r2 = equiv_check.check(br_so, "f", br_bad_src, sig="u64", cases=32, seed=1)
    assert r2["result"] == "MISMATCH"


def test_tested_only_when_symbolic_disabled(build):
    _, orig_so = build["orig"]
    cand_src, _ = build["cand_ok"]
    r = equiv_check.check(orig_so, "f", cand_src, sig="u64", cases=32, seed=7,
                          skip_symbolic=True)
    assert r["result"] == "TESTED_ONLY"
    assert r["coverage"]["cases"] == 32


def test_inconclusive_missing_orig(tmp_path, build):
    cand_src, _ = build["cand_ok"]
    r = equiv_check.check(str(tmp_path / "nope.so"), "f", cand_src, sig="u64")
    assert r["result"] == "INCONCLUSIVE"


def test_inconclusive_unbuildable_candidate(build, tmp_path):
    _, orig_so = build["orig"]
    bad = tmp_path / "bad.c"
    bad.write_text("this is not C\n")
    r = equiv_check.check(orig_so, "f", str(bad), sig="u64")
    assert r["result"] == "INCONCLUSIVE"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
