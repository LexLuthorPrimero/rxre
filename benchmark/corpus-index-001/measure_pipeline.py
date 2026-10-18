#!/usr/bin/env python3
"""CORPUS-INDEX-001 — Medición de componentes del pipeline.

Parchea tar_index() y pat.search() para atribuir tiempo exacto a cada capa.
Conserva la semántica de evidence_search.py sin cambiarla.
"""
from __future__ import annotations

import os
import re
import sys
import time
import statistics
import tempfile
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)

import tools.evidence_search as es

# --------------------------------------------------------------------------- #
# Contadores temporales
# --------------------------------------------------------------------------- #
TIMERS = {"T1_index": 0.0, "T5_match": 0.0, "T_total": 0.0}

def reset_timers():
    for k in TIMERS:
        TIMERS[k] = 0.0

# --------------------------------------------------------------------------- #
# 1) Instrumentar tar_index — mide corpus discovery / tarball index
# --------------------------------------------------------------------------- #
ORIG_TAR_INDEX = es.tar_index

def tar_index_instr(path):
    t0 = time.perf_counter()
    r = ORIG_TAR_INDEX(path)
    t1 = time.perf_counter()
    TIMERS["T1_index"] += t1 - t0
    return r

es.tar_index = tar_index_instr

# 2) Instrumentar Root.resolve — incluye llamada a tar_index + filesystem checks
ORIG_RESOLVE = es.Root.resolve

def resolve_instr(self):
    t0 = time.perf_counter()
    ORIG_RESOLVE(self)
    t1 = time.perf_counter()
    # resolve puede incluir tar_index (ya contado) + checks. Atribuimos la parte
    # que no es tar_index como adicional de index/discovery.
    # Para no doble contar, restamos T1_index de este intervalo (no doble contar).
    # Pero como resolve se llama antes de la búsqueda, el T1_index se acumula dentro.
    # Entonces no atribuimos el total aquí, solo dejamos que tar_index se cuente solo.
    # La parte "residual" de resolve (os.path.exists, isdir, isfile) la dejamos en T_other.
    pass  # el conteo de tar_index ya está dentro; el overhead de resolve es T_other

es.Root.resolve = resolve_instr

# 3) Instrumentar pat.search — mide T5 (matching)
# Para esto, envolvemos search() original pero interceptamos pat.search
# La forma más limpia: monkeypatch `re.Pattern.search` solo dentro del search.
# Pero re.Pattern es global. En su lugar, parcheamos search() con timing inline.

# Guardamos el search original y creamos una versión que mide pat.search
ORIG_SEARCH = es.search

def search_instr(query, roots, exact_word, include, match_name=False):
    """Copia instrumentada del search() original con timing de pat.search."""
    reset_timers()
    total_start = time.perf_counter()

    filt = re.compile(include) if include else None
    pat = es.build_pattern(query, exact_word)
    hits = []
    universe = {}

    for root in roots:
        root.resolve()
        universe[root.name] = {
            "present": root.present,
            "spec": root.spec,
            "tarball": root.tarball,
            "reason": root.reason,
        }
        if not root.present:
            continue
        for logical, lines in root.iter_text_files((".c", ".h", ".txt", ".json", ".md")):
            if filt and not filt.search(logical):
                continue
            if match_name:
                # T5_match: pat.search en nombre de archivo
                tm0 = time.perf_counter()
                matched = pat.search(logical)
                tm1 = time.perf_counter()
                TIMERS["T5_match"] += tm1 - tm0
                if matched:
                    hits.append({
                        "root": root.name,
                        "file": logical,
                        "line": 0,
                        "text": "fichero presente",
                    })
                continue
            for n, line in enumerate(lines, 1):
                # T5_match: pat.search en contenido de línea
                tm0 = time.perf_counter()
                matched = pat.search(line)
                tm1 = time.perf_counter()
                TIMERS["T5_match"] += tm1 - tm0
                if matched:
                    # T6_result: procesar resultado
                    hits.append({
                        "root": root.name,
                        "file": logical,
                        "line": n,
                        "text": line.strip()[:200],
                    })

    total_end = time.perf_counter()
    TIMERS["T_total"] = total_end - total_start
    return hits, universe

es.search = search_instr

# --------------------------------------------------------------------------- #
# Validación semántica del patching
# --------------------------------------------------------------------------- #
tmpdir = tempfile.mkdtemp()
try:
    with open(os.path.join(tmpdir, "test.c"), "w") as f:
        f.write("#define FOO_BAR 1\nvoid baz(void) {}\n")
    r = es.Root("test", tmpdir)
    r.resolve()
    hits, _ = es.search("FOO_BAR", [r], exact_word=True, include=None)
    hits2, _ = es.search("FOO_BAR", [r], exact_word=False, include=None)
    hits3, _ = es.search("baz", [r], exact_word=True, include=None)
    hits4, _ = es.search("baz", [r], exact_word=False, include=None)
    if len(hits) != 1 or len(hits2) != 1 or len(hits3) != 1 or len(hits4) != 1:
        print("VALIDACIÓN FALLÓ: patching altera semántica",
              len(hits), len(hits2), len(hits3), len(hits4), file=sys.stderr)
        sys.exit(1)
    print("PATCHING VERIFICADO: semántica preservada (exact_word True/False funcionan).")
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)

# --------------------------------------------------------------------------- #
# Workload
# --------------------------------------------------------------------------- #
REAL_QUERIES = ["VM_CONTEXT0_CNTL", "SMC", "VMID", "REG_SET_FIELD", "amdgpu_vm_init"]

def count_files_and_lines(roots):
    n_files = 0
    n_lines = 0
    for r in roots:
        for _, lines in r.iter_text_files((".c", ".h", ".txt", ".json", ".md")):
            n_files += 1
            n_lines += len(lines)
    return n_files, n_lines

def get_real_roots():
    roots = []
    base = os.path.join(ROOT, "RESEARCH", "working", "linux-7.1.3")
    for kr in es.DEFAULT_KEY_ROOTS:
        p = os.path.join(base, kr)
        if os.path.exists(p):
            roots.append(es.Root(kr, p))
    return roots

def run_suite(queries, roots, exact_word, reps=3, warmup=1):
    rows = []
    # Warmup
    for _ in range(warmup):
        for q in queries:
            reset_timers()
            es.search(q, roots, exact_word, None)
    # Measured reps
    for rep in range(reps):
        for q in queries:
            reset_timers()
            hits, _ = es.search(q, roots, exact_word, None)
            rows.append({
                "T1_index": TIMERS["T1_index"],
                "T5_match": TIMERS["T5_match"],
                "T_total": TIMERS["T_total"],
                "query": q,
                "hits": len(hits),
                "rep": rep,
            })
    return rows

def summarize(rows, label, n_files, n_lines):
    print(f"\n=== {label} ===")
    print(f"  Archivos efectivos: {n_files}, Líneas: {n_lines}")
    n_queries = len(set(r["query"] for r in rows))
    for k in ["T1_index", "T5_match", "T_total"]:
        vals = [r[k] for r in rows]
        med = statistics.median(vals)
        print(f"  {k}: median={med*1000:.2f}ms  mean={statistics.mean(vals)*1000:.2f}ms")
    t_total_median = statistics.median([r["T_total"] for r in rows])
    if t_total_median > 0:
        t1_med = statistics.median([r["T1_index"] for r in rows])
        t5_med = statistics.median([r["T5_match"] for r in rows])
        print(f"  Fracción de T_total:")
        print(f"    T1_index (corpus discovery): {t1_med/t_total_median*100:.2f}%")
        print(f"    T5_match (regex matching):   {t5_med/t_total_median*100:.2f}%")
        print(f"    T_other (resto):              {(t_total_median-t1_med-t5_med)/t_total_median*100:.2f}%")
    # Hits por query
    hits_per_q = [r["hits"] for r in rows]
    print(f"  Hits: median={statistics.median(hits_per_q):.0f}")

def main():
    print("=" * 70)
    print("CORPUS-INDEX-001 — Medición de componentes del pipeline (T1, T5, T_other)")
    print("=" * 70)

    HEAD = "7c2971e67b533a4e3b0471da8cbd9335af2f42c2"
    print(f"ACTIVE_TREE = {ROOT}")
    print(f"HEAD = {HEAD}")

    # ----- CORPUS REAL -----
    print("\n>>> CORPUS REAL: working/linux-7.1.3 (521 MB) <<<")
    real_roots = get_real_roots()
    print(f"  {len(real_roots)} key roots present")
    n_files, n_lines = count_files_and_lines(real_roots)
    print(f"  Archivos efectivos: {n_files}, Líneas: {n_lines}")

    for exact in [True, False]:
        rows = run_suite(REAL_QUERIES, real_roots, exact_word=exact, reps=3, warmup=1)
        summarize(rows, f"REAL exact_word={exact}", n_files, n_lines)

    # ----- FIXTURE -----
    print("\n>>> FIXTURE: 10×1000 <<<")
    fixture_dir = tempfile.mkdtemp(prefix="rxre_fx_")
    try:
        for i in range(10):
            with open(os.path.join(fixture_dir, f"file_{i}.c"), "w") as f:
                for j in range(1000):
                    if j % 100 == 0:
                        f.write(f"#define FIXTURE_{j} {j}\n")
                    else:
                        f.write(f"void gmc_v8_1_init_{j}_{i}(void) {{}}\n")
        fixture_roots = [es.Root("fixture", fixture_dir)]
        n_files, n_lines = count_files_and_lines(fixture_roots)
        for exact in [True, False]:
            rows = run_suite(["FIXTURE_0", "FIXTURE_1"], fixture_roots, exact_word=exact, reps=3, warmup=1)
            summarize(rows, f"FIXTURE exact_word={exact}", n_files, n_lines)
    finally:
        shutil.rmtree(fixture_dir, ignore_errors=True)

    print("=" * 70)
    print("MEDICIÓN DE COMPONENTES COMPLETA")
    print("=" * 70)


if __name__ == "__main__":
    main()
