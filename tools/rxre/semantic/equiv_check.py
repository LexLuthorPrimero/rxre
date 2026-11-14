#!/usr/bin/env python3
"""RXRE-EQUIV: verificación acotada de equivalencia semántica nativa (primer slice).

Comparación original (binario nativo) vs candidato (C o binario) para funciones
escalares de un argumento entero (uint64/int64) con retorno entero.

Modelo de resultados (alineado con morluto/rea#4972):
  PROVEN       — z3/UNSAT sobre todo el dominio en el modelo: semántica binaria
                 levantada por angr (VEX), registro de arg/retorno según SysV
                 AMD64, sin considerar efectos sobre memoria/entorno ni UB.
  MISMATCH     — contraejemplo reproducible (confirmado por ejecución concreta
                 cuando sea posible).
  TESTED_ONLY  — ejecución diferencial concreta superada en el corpus declarado;
                 equivalencia general NO demostrada.
  INCONCLUSIVE — símbolo ausente / shape no soportado / timeout: no se sabe.

Independencia: la vía simbólica usa angr+z3; el control concreto usa ctypes
(ejecución nativa del candidato, y de la original solo si es dlopen-able).

Uso:
  python3 tools/rxre/semantic/equiv_check.py \
      --orig orig.so --orig-func f --cand cand.c \
      [--sig u64|i64] [--cases N] [--seed S] [--out JSON]
"""
import argparse
import ctypes
import hashlib
import json
import os
import random
import signal
import subprocess
import sys
import tempfile
import time

DOMAINS = {"u64": ("uint64_t", 64), "i64": ("int64_t", 64)}
BOUNDARIES_U64 = [0, 1, 2, 255, 256, 2**32 - 1, 2**32, 2**63 - 1, 2**63, 2**64 - 1, 100, 101]
BOUNDARIES_I64 = [0, 1, -1, 2**31 - 1, 2**31, -2**31, -2**63, 2**63 - 1, 2**64 - 1, 7, -256]


class Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise Timeout()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def versions():
    v = {"python": sys.version.split()[0]}
    try:
        import angr
        v["angr"] = angr.__version__
    except Exception:
        v["angr"] = None
    try:
        import z3
        v["z3"] = z3.get_version_string()
    except Exception:
        v["z3"] = None
    try:
        out = subprocess.run(["gcc", "--version"], capture_output=True, text=True, timeout=30).stdout.splitlines()[0]
        v["gcc"] = out
    except Exception:
        v["gcc"] = None
    return v


def compile_candidate(src, outdir, sig):
    out = os.path.join(outdir, "cand.so")
    cmd = ["gcc", "-O2", "-fPIC", "-shared", "-o", out, src]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return None, "gcc timeout", None
    if proc.returncode != 0:
        return None, f"gcc rc={proc.returncode}: {proc.stderr.strip()[:400]}", None
    return out, None, sha256_file(out)


def symbolic_return_exprs(path, func, symbol_addr, sig, timeout_s):
    """Devuelve (lista de (path_constraints, ret_expr, input_var), error)."""
    import logging

    for name in ("angr", "cle", "pyvex", "archinfo", "rustylib", "claripy"):
        logging.getLogger(name).setLevel(logging.ERROR)

    import angr
    from angr import claripy

    signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(timeout_s)
    try:
        p = angr.Project(path, auto_load_libs=False)
        if symbol_addr is None:
            fs = p.loader.find_symbol(func)
            if fs is None:
                return None, f"symbol {func!r} not found in {path}"
            faddr = fs.rebased_addr
        else:
            faddr = symbol_addr
        x = claripy.BVS("arg0", 64)
        st = p.factory.call_state(faddr, x)
        sm = p.factory.simgr(st)
        sm.run(n=2000)
        exprs = []
        for e in sm.deadended:
            exprs.append((list(e.solver.constraints), e.regs.rax, x))
        if not exprs:
            return None, "no return states (errored/nonterminating/unsupported)"
        return exprs, None
    except Timeout:
        return None, f"symbolic exploration timed out after {timeout_s}s"
    except Exception as exc:  # angr can raise arbitrary lifter errors
        return None, f"symbolic error: {type(exc).__name__}: {exc}"
    finally:
        signal.alarm(0)


def _unify(constraints, ret_expr, var, common):
    cs = [c.replace(var, common) for c in constraints]
    return cs, ret_expr.replace(var, common)


def prove_or_disprove(orig_exprs, cand_exprs, timeout_s):
    """Consulta z3 por pares de camino. Devuelve (verdict, detail).

    verdict: "PROVEN" | {"MISMATCH": cex_int} | "UNKNOWN"
    """
    from angr import claripy

    common = claripy.BVS("arg0", 64)
    o_paths = [_unify(g, r, v, common) for g, r, v in orig_exprs]
    c_paths = [_unify(g, r, v, common) for g, r, v in cand_exprs]

    for i, (go, ro) in enumerate(o_paths):
        for j, (gc, rc) in enumerate(c_paths):
            s = claripy.Solver()
            q = claripy.Neq(ro, rc)
            if s.satisfiable(extra_constraints=go + gc + [q]):
                cex = s.eval(common, 1, extra_constraints=go + gc + [q])[0]
                return {"MISMATCH": cex}, f"paths orig[{i}] vs cand[{j}]"

    def covers_all(paths):
        # Un camino sin constraints cubre todo el dominio.
        if any(not cs for cs, _ in paths):
            return True
        s = claripy.Solver()
        disj = claripy.Or(*[claripy.And(*cs) for cs, _ in paths])
        return not s.satisfiable(extra_constraints=[claripy.Not(disj)])

    co, cc = covers_all(o_paths), covers_all(c_paths)
    if co and cc:
        return "PROVEN", "z3 UNSAT diferencial; cobertura total en ambos lados"
    return "UNKNOWN", f"cobertura parcial: orig={co} cand={cc}"


def safe_calls(path, func, sig, vals, timeout_s=10):
    """Ejecuta N llamadas fork-por-llamada; un fallo/segfault en una llamada
    no tumba al verificador ni invalida las demás. Devuelve lista de
    uint64 o None (crash/timeout) por entrada."""
    import os
    import struct

    ctype = ctypes.c_uint64 if sig == "u64" else ctypes.c_int64
    try:
        lib = ctypes.CDLL(path)
        cfunc = getattr(lib, func)
        cfunc.restype = ctype
        cfunc.argtypes = [ctype]
    except Exception as exc:
        return None, f"dlopen/getattr fallo: {type(exc).__name__}: {exc}"

    out = []
    import select

    for v in vals:
        r_fd, w_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(r_fd)
            try:
                res = ctypes.c_uint64(cfunc(ctype(v % (1 << 64)))).value
                os.write(w_fd, struct.pack("<Q", res))
            except BaseException:
                pass
            finally:
                os._exit(0)
        os.close(w_fd)
        data = b""
        ready, _, _ = select.select([r_fd], [], [], timeout_s)
        if ready:
            while len(data) < 8:
                chunk = os.read(r_fd, 8 - len(data))
                if not chunk:
                    break
                data += chunk
        os.close(r_fd)
        _, status = os.waitpid(pid, 0)
        out.append(struct.unpack("<Q", data)[0] if len(data) == 8 else None)
    return out, None


def corpus(sig, n, seed):
    base = BOUNDARIES_U64 if sig == "u64" else BOUNDARIES_I64
    rng = random.Random(seed)
    vals = list(base)
    while len(vals) < n:
        vals.append(rng.getrandbits(64))
    return vals[:n]


def check(orig, orig_func, cand, sig="u64", cases=64, seed=20261114, out_path=None,
          orig_addr=None, timeout_s=60, skip_symbolic=False):
    t0 = time.time()
    result = {
        "tool": "rxre-equiv_check",
        "schema": "rxre.equiv_check/v1",
        "issue": "morluto/rea#4972",
        "hashes": {},
        "versions": versions(),
        "inputs": {"orig": orig, "orig_func": orig_func, "orig_addr": orig_addr,
                   "cand_input": cand, "sig": sig, "cases": cases, "seed": seed},
        "layers": {},
        "result": None,
        "counterexample": None,
        "scope": [
            "single argument integer scalar function",
            "SysV AMD64: arg in rdi, ret in rax",
            "binary lift semantics (angr/VEX), not source-level semantics",
            "memory/global side effects and environment NOT modeled",
            "domain: " + ("uint64" if sig == "u64" else "int64") + " full range",
        ],
        "limitations": [],
    }

    def finish(res):
        res["elapsed_s"] = round(time.time() - t0, 3)
        if out_path:
            with open(out_path, "w") as fh:
                json.dump(res, fh, indent=2, ensure_ascii=False)
        return res

    if not os.path.exists(orig):
        result["result"] = "INCONCLUSIVE"
        result["limitations"].append("original binary not found")
        return finish(result)
    orig = os.path.abspath(orig)
    result["hashes"]["orig"] = sha256_file(orig)

    compile_td = None
    if cand.endswith((".c", ".cc", ".cpp")):
        compile_td = tempfile.TemporaryDirectory(prefix="rxre-equiv-")
        cand_bin, err, cand_hash = compile_candidate(cand, compile_td.name, sig)
        if not cand_bin:
            compile_td.cleanup()
            result["result"] = "INCONCLUSIVE"
            result["limitations"].append(f"candidate build failed: {err}")
            return finish(result)
        result["hashes"]["cand_source"] = sha256_file(cand)
        result["hashes"]["cand_build"] = cand_hash
    else:
        cand_bin = os.path.abspath(cand)
        if not os.path.exists(cand_bin):
            result["result"] = "INCONCLUSIVE"
            result["limitations"].append("candidate binary not found")
            return finish(result)
        result["hashes"]["cand"] = sha256_file(cand_bin)

    res = _run_all_layers(result, orig, orig_func, cand_bin, sig,
                          cases, seed, orig_addr, timeout_s, skip_symbolic)
    if compile_td is not None:
        compile_td.cleanup()
    return finish(res)


def _run_all_layers(result, orig, orig_func, cand_bin, sig, cases, seed, orig_addr, timeout_s, skip_symbolic):
    cex_mismatch = None

    if not skip_symbolic:
        o_exprs, o_err = symbolic_return_exprs(orig, orig_func, orig_addr, sig, timeout_s)
        c_exprs, c_err = symbolic_return_exprs(cand_bin, orig_func, None, sig, timeout_s)
        if o_exprs and c_exprs:
            verdict, detail = prove_or_disprove(o_exprs, c_exprs, timeout_s)
            result["layers"]["symbolic"] = {"ok": True, "detail": detail}
            if isinstance(verdict, dict):
                cex_mismatch = verdict["MISMATCH"]
                result["layers"]["symbolic"]["counterexample"] = hex(cex_mismatch)
        else:
            result["layers"]["symbolic"] = {"ok": False, "orig_error": o_err, "cand_error": c_err}
    else:
        result["layers"]["symbolic"] = {"ok": False, "skipped": True}

    vals = corpus(sig, cases, seed)
    o_out, o_note = safe_calls(orig, orig_func, sig, vals)
    c_out, c_note = safe_calls(cand_bin, orig_func, sig, vals)
    ctype_note = "; ".join(n for n in (o_note, c_note) if n) or None

    diff = None
    crashes = 0
    if o_out is not None and c_out is not None:
        for v, a, b in zip(vals, o_out, c_out):
            if a is None or b is None:
                crashes += 1
                continue
            if a != b:
                diff = (v, a, b)
                break
        state = "ran" if crashes == 0 and ctype_note is None else "ran_with_errors"
        result["layers"]["concrete"] = {
            "state": state,
            "cases": len(vals),
            "crashes": crashes,
            "equivalent_on_corpus": diff is None and crashes == 0,
            "diff": None if diff is None else {"input": hex(diff[0]), "orig": hex(diff[1]), "cand": hex(diff[2])},
            "note": ctype_note or (f"{crashes} call(s) crashed/timed out" if crashes else None),
        }
    else:
        result["layers"]["concrete"] = {"state": "unavailable", "cases": 0, "crashes": None,
                                        "equivalent_on_corpus": None, "diff": None, "note": ctype_note}

    sym = result["layers"]["symbolic"]
    conc = result["layers"]["concrete"]

    if cex_mismatch is not None:
        result["result"] = "MISMATCH"
        result["counterexample"] = f"{cex_mismatch:#x}"
        if o_out is not None and c_out is not None:
            # confirmación concreta puntual del contraejemplo
            o_one, _ = safe_calls(orig, orig_func, sig, [cex_mismatch])
            c_one, _ = safe_calls(cand_bin, orig_func, sig, [cex_mismatch])
            if o_one and c_one and o_one[0] is not None and c_one[0] is not None:
                result["counterexample_confirmed_native"] = (o_one[0] != c_one[0])
        return result
    if sym.get("ok") and isinstance(sym.get("detail"), str) and sym["detail"].startswith("z3 UNSAT"):
        result["result"] = "PROVEN"
        # control: spot-check boundaries nativas (control, no prueba)
        if o_out is not None and c_out is not None:
            spot = BOUNDARIES_U64[:6] if sig == "u64" else BOUNDARIES_I64[:6]
            so, _ = safe_calls(orig, orig_func, sig, spot)
            sc, _ = safe_calls(cand_bin, orig_func, sig, spot)
            mism = [hex(v) for v, a, b in zip(spot, so or [], sc or []) if a is not None and b is not None and a != b]
            result["native_spot_check_mismatches"] = mism
            if mism:
                result["result"] = "MISMATCH"
                result["limitations"].append("native spot-check contradicts symbolic verdict; mistrust both")
        return result
    if conc.get("diff"):
        d = conc["diff"]
        result["result"] = "MISMATCH"
        result["counterexample"] = d["input"]
        result["counterexample_confirmed_native"] = True
        return result
    if conc.get("equivalent_on_corpus") and conc["cases"] > 0:
        result["result"] = "TESTED_ONLY"
        result["coverage"] = {"cases": conc["cases"], "corpus": [hex(v) for v in vals]}
        result["limitations"].append("equivalence NOT proven; finite corpus only")
        return result
    result["result"] = "INCONCLUSIVE"
    result["limitations"].append("no usable layer produced a verdict")
    return result


def main():
    ap = argparse.ArgumentParser(description="RXRE bounded equivalence check")
    ap.add_argument("--orig", required=True)
    ap.add_argument("--orig-func", required=True)
    ap.add_argument("--orig-addr", type=lambda s: int(s, 0), default=None)
    ap.add_argument("--cand", required=True, help="C source or compiled .so")
    ap.add_argument("--sig", choices=sorted(DOMAINS), default="u64")
    ap.add_argument("--cases", type=int, default=64)
    ap.add_argument("--seed", type=int, default=20261114)
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--no-symbolic", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = check(a.orig, a.orig_func, a.cand, sig=a.sig, cases=a.cases, seed=a.seed,
                out_path=a.out, orig_addr=a.orig_addr, timeout_s=a.timeout,
                skip_symbolic=a.no_symbolic)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0 if res["result"] in ("PROVEN", "MISMATCH", "TESTED_ONLY") else 2


if __name__ == "__main__":
    sys.exit(main())
