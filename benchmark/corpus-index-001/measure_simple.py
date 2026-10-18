#!/usr/bin/env python3
"""MEDICIÓN SIMPLE: comparar corpus de diferentes tamaños para ver si índice/cuero es una barrera.

Instrumentación mínima: solo medir time.time() de search() original.
Sin modificar ningún backend. Utiliza el corpus real, un fixture pequeño y el baseline.
Devuelve: T_total para cada workload, junto con fracciones de archivos y líneas.
"""
from __future__ import annotations

import os
import sys
import time
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)

import tools.evidence_search as es

REAL_QUERIES = ["VM_CONTEXT0_CNTL", "SMC", "VMID", "REG_SET_FIELD", "amdgpu_vm_init"]

def time_search(queries, roots, exact_word, reps=5, warmup=1):
    """Devolver lista de T_total (segundos) para cada repetición."""
    totals = []
    for _ in range(warmup):
        for q in queries:
            es.search(q, roots, exact_word, None)
    for _ in range(reps):
        for q in queries:
            t0 = time.perf_counter()
            es.search(q, roots, exact_word, None)
            t1 = time.perf_counter()
            totals.append(t1 - t0)
    return totals

def count_files_and_lines(roots):
    n_files = 0
    n_lines = 0
    for r in roots:
        for _, lines in r.iter_text_files((".c", ".h", ".txt", ".json", ".md")):
            n_files += 1
            n_lines += len(lines)
    return n_files, n_lines

def print_summary(label, total_times, n_files, n_lines, corpus_desc):
    print(f"\n=== {label} ===")
    print(f"  Corpus: {corpus_desc}")
    print(f"  Archivos efectivos: {n_files}, Líneas: {n_lines}")
    if total_times:
        median = statistics.median(total_times)
        p95 = statistics.quantiles(total_times, n=20)[18]
        mean = statistics.mean(total_times)
        print(f"  T_total por búsqueda:")
        print(f"    media   {mean*1000:.2f} ms")
        print(f"    median  {median*1000:.2f} ms")
        print(f"    P95     {p95*1000:.2f} ms")
        print(f"    min     {min(total_times)*1000:.2f} ms")
        print(f"    max     {max(total_times)*1000:.2f} ms")
        print(f"  Líneas/archivos por búsqueda: {n_lines/len(total_times):.0f} líneas, {n_files/len(total_times):.0f} archivos")


def main():
    print("=" * 70)
    print("CORPUS-INDEX-001 — Medición simple del tiempo de search end-to-end.")
    print("=" * 70)

    HEAD = "7c2971e67b533a4e3b0471da8cbd9335af2f42c2"
    print(f"ACTIVE_TREE = {ROOT}")
    print(f"HEAD = {HEAD}")

    # ----- REAL CORPUS (working) -----
    print("\n>>> CORPUS REAL: working/linux-7.1.3 <<<")
    real_roots = []
    corpus_path = os.path.join(ROOT, "RESEARCH", "working", "linux-7.1.3")
    for kr in es.DEFAULT_KEY_ROOTS:
        p = os.path.join(corpus_path, kr)
        if os.path.exists(p):
            real_roots.append(es.Root(kr, p))
    if real_roots:
        n_files, n_lines = count_files_and_lines(real_roots)
        print(f"  {len(real_roots)} key roots present")
        for exact in [True, False]:
            times = time_search(REAL_QUERIES, real_roots, exact_word=exact, reps=3, warmup=1)
            print_summary(f"REAL exact_word={exact}", times, n_files, n_lines,
                         f"{len(real_roots)} key roots, {n_files} archivos, {n_lines} líneas")

    # ----- FIXTURE PEQUEÑO -----
    print("\n>>> FIXTURE PEQUEÑO: 10×1000 <<<")
    fixture_dir = tempfile.mkdtemp(prefix="rxre_fixture_")
    try:
        for i in range(10):
            with open(os.path.join(fixture_dir, f"file_{i}.c"), "w") as f:
                for j in range(1000):
                    if j % 100 == 0:
                        f.write(f"#define FIXTURE_{j} {j}\n")
                    else:
                        f.write(f"void gmc_v8_1_init_{j}_{i}(void) {{}}\n")
        fixture_roots = [es.Root("fixture", fixture_dir)]
        for exact in [True, False]:
            n_files, n_lines = count_files_and_lines(fixture_roots)
            times = time_search(["FIXTURE_A", "FIXTURE_B"], fixture_roots, exact_word=exact, reps=3, warmup=1)
            print_summary(f"FIXTURE exact_word={exact}", times, n_files, n_lines,
                         f"10 archivos, {n_lines} líneas")
    finally:
        shutil.rmtree(fixture_dir, ignore_errors=True)

    print("=" * 70)
    print("FINALIZADO")
    print("=" * 70)

if __name__ == "__main__":
    import tempfile
    import shutil
    main()
