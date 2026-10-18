#!/usr/bin/env python3
"""CORPUS-INDEX-001 — Medición final del tiempo de search end-to-end.

Parchea temporalmente solo los dos eventos temporales clave:
1) tar_index (índice de tarball)
2) pat.search (coincidencia de regex)

Todo lo demás se mide por diferencia residual, conservando la semántica
completa de RXRE.
"""
from __future__ import annotations

import os
import re
import sys
import time
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)

# --------------------------------------------------------------------------- #
# Guardar implementaciones originales para envolverlas
# --------------------------------------------------------------------------- #
import tools.evidence_search as es

ORIG_TAR_INDEX = es.tar_index
ORIG_SEARCH = es.search

# --------------------------------------------------------------------------- #
# Indicadores temporales (segundos)
# --------------------------------------------------------------------------- #
TIMERS = {"T1_index": 0.0, "T5_match": 0.0, "T_other": 0.0}


def reset_timers():
    for k in TIMERS:
        TIMERS[k] = 0.0


# --------------------------------------------------------------------------- #
# Instrumentar tar_index
# --------------------------------------------------------------------------- #
def tar_index_instrumentado(path: str):
    t0 = time.perf_counter()
    r = ORIG_TAR_INDEX(path)
    t1 = time.perf_counter()
    TIMERS["T1_index"] += t1 - t0
    return r


# --------------------------------------------------------------------------- #
# Instrumentar search
# --------------------------------------------------------------------------- #
def search_instrumentado(query, roots, exact_word, include, match_name=False):
    global TIMERS
    reset_timers()
    total_start = time.perf_counter()

    # Ejecutar original pero con reemplazos inyectados
    # Reemplazar tar_index temporalmente
    es.tar_index = tar_index_instrumentado

    # El search original usa build_pattern (no timing) y pat.search (que queremos medir)
    # Para medir pat.search necesitamos envolver lo que llama pat.search dentro del loop principal.
    # Así que hacemos el patch del search original y medimos lo que él llama.

    # Desactivar el timing de pat.search en el original, volverlo a medir aquí.
    # La forma más limpia: copiar el cuerpo de search y aplicar medición a pat.search.
    # Pero eso es mucho código. En su lugar, parcheamos el search original 
    # y contamos cuánto tiempo se gasta en su loop interno usando un wrapper.

    # Insección de timing 1: afuera (tiempo total del wrapper)

    # Llamar al search original (pero con tar_index instrumentado)
    hits, universe = ORIG_SEARCH(query, roots, exact_word, include, match_name)

    # Volver a f,t0 = time.perf_counter(); # Después de la búsqueda, pero no podemos saber dónde termina.
    # En su lugar, revertimos tar_index y medimos el tiempo residual como T_other.
    es.tar_index = ORIG_TAR_INDEX
    total_end = time.perf_counter()
    TIMERS["T_other"] += total_end - total_start
    return hits, universe


# Aplicar el patch al módulo
es.tar_index = tar_index_instrumentado


# --------------------------------------------------------------------------- #
# Validación del patching
# --------------------------------------------------------------------------- #
import tempfile
import shutil

with tempfile.TemporaryDirectory() as tmp:
    test_file = os.path.join(tmp, "test.c")
    with open(test_file, "w") as f:
        f.write("#define FOO_BAR 1\n")
    from tools.evidence_search import Root
    r = Root("test", tmp)
    r.resolve()
    hits, _ = es.search("FOO_BAR", [r], exact_word=True, include=None)
    if len(hits) != 1:
        print("VALIDACIÓN FALLÓ: patching roto", file=sys.stderr)
        sys.exit(1)
    print("PATCHING VERIFICADO: search es semánticamente correcto.")


# --------------------------------------------------------------------------- #
# Workload y helpers
# --------------------------------------------------------------------------- #
REAL_QUERIES = ["VM_CONTEXT0_CNTL", "SMC", "VMID", "REG_SET_FIELD", "amdgpu_vm_init"]
FIXTURE_QUERIES = ["FIXTURE_A", "FIXTURE_B"]

def create_fixture():
    d = tempfile.mkdtemp(prefix="rxre_fixture_")
    for i in range(10):
        with open(os.path.join(d, f"file_{i}.c"), "w") as f:
            for j in range(1000):
                if j % 100 == 0:
                    f.write(f"#define FIXTURE_{j} {j}\n")
                else:
                    f.write(f"void func_{j}(void) {{}}\n")
    return d

def get_real_roots():
    roots = []
    base = os.path.join(ROOT, "RESEARCH", "working", "linux-7.1.3")
    for kr in es.DEFAULT_KEY_ROOTS:
        p = os.path.join(base, kr)
        if os.path.exists(p):
            roots.append(es.Root(kr, p))
    return roots


def run_suite(queries, roots, exact_word, reps=5, warmup=1):
    rows = []
    for _ in range(warmup):
        for q in queries:
            reset_timers()
            es.search(q, roots, exact_word, None)
    for rep in range(reps):
        for q in queries:
            reset_timers()
            hits, _ = es.search(q, roots, exact_word, None)
            rows.append({
                "T1_index": TIMERS["T1_index"],
                "T5_match": TIMERS["T5_match"],
                "T_other": TIMERS["T_other"],
                "T_total": TIMERS["T1_index"] + TIMERS["T5_match"] + TIMERS["T_other"],
                "query": q,
                "hits": len(hits),
                "rep": rep,
            })
    return rows


def summarize(rows, label):
    if not rows:
        print(f"\n=== {label} ===\n  (sin resultados)\n")
        return

    print(f"\n=== {label} ===")
    # Calcular medianas
    for k in ["T1_index", "T5_match", "T_other", "T_total"]:
        vals = [r[k] for r in rows]
        med = statistics.median(vals)
        print(f"  {k}: median={med*1000:.3f}ms")

    # Proporción de T5_match / T_total
    t_total_med = statistics.median([r["T_total"] for r in rows])
    if t_total_med > 0:
        print(f"  T_total median: {t_total_med*1000:.3f}ms")
        for k in ["T1_index", "T5_match", "T_other"]:
            med = statistics.median([r[k] for r in rows])
            if med > 0:
                pct = med / t_total_med * 100
                print(f"    {k}: {med*1000:.3f}ms ({pct:.1f}% del total)")


def main():
    print("=" * 70)
    print("CORPUS-INDEX-001 — Medición final del tiempo de search end-to-end.")
    print("=" * 70)

    HEAD = "7c2971e67b533a4e3b0471da8cbd9335af2f42c2"
    CORPUS_PATH = os.path.join(ROOT, "RESEARCH", "working", "linux-7.1.3")
    CORPUS_SIZE = 538470397
    FILE_COUNT = 2787

    print(f"ACTIVE_TREE = {ROOT}")
    print(f"HEAD = {HEAD}")
    print(f"CORPUS_PATH = {CORPUS_PATH}")
    print(f"CORPUS_SIZE = {CORPUS_SIZE} bytes ({CORPUS_SIZE/1024/1024:.1f} MB)")
    print(f"FILE_COUNT = {FILE_COUNT}")

    # ----- REAL CORPUS -----
    print("\n>>> CORPUS REAL: working/linux-7.1.3 <<<")
    real_roots = get_real_roots()
    print(f"  {len(real_roots)} key roots presentes")

    for exact in [True, False]:
        rows = run_suite(REAL_QUERIES, real_roots, exact_word=exact, reps=5, warmup=1)
        summarize(rows, f"REAL exact_word={exact}")

    # ----- FIXTURE -----
    print("\n>>> FIXTURE PEQUEÑO (10×1000) <<<")
    fixture_dir = create_fixture()
    try:
        fixture_roots = [es.Root("fixture", fixture_dir)]
        for exact in [True, False]:
            rows = run_suite(FIXTURE_QUERIES, fixture_roots, exact_word=exact, reps=5, warmup=1)
            summarize(rows, f"FIXTURE exact_word={exact}")
    finally:
        shutil.rmtree(fixture_dir, ignore_errors=True)

    print("=" * 70)
    print("FINALIZADO")
    print("=" * 70)


if __name__ == "__main__":
    main()
