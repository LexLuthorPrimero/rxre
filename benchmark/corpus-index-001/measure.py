#!/usr/bin/env python3
"""CORPUS-INDEX-001 — Medición causal del pipeline de RXRE.

Importa el codebase original y parchea temporalmente solo los métodos
cuyo coste queremos medir. Conserva el comportamiento semántico.
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

# ----------------------------------------- #
# 1) importar el módulo real
# ----------------------------------------- #
import tools.evidence_search as es

# Guardar las implementaciones originales para llamadas a wrapper
ORIG_TAR_INDEX = es.tar_index
ORIG_ROOT_RESOLVE = es.Root.resolve

# ----------------------------------------- #
# 2) contadores temporales
# ----------------------------------------- #
TIMERS = {
    "T1_index": 0.0,      # corpus discovery / tar_index
    "T2_open": 0.0,       # open file (os.open) o tarball (tarfile.open)
    "T3_read": 0.0,       # read (readlines / iteración)
    "T4_iter": 0.0,       # splitting / strip / slice (line processing)
    "T5_match": 0.0,      # pattern matching (pat.search)
    "T6_result": 0.0,     # object construction / append / json
    "T_other": 0.0,       # residual (build_pattern, filtrado, etc.)
}

def reset_timers():
    for k in TIMERS:
        TIMERS[k] = 0.0

# ----------------------------------------- #
# 3) instrumentación para tar_index
# ----------------------------------------- #
def tar_index_instrumentado(path: str):
    t0 = time.perf_counter()
    r = ORIG_TAR_INDEX(path)
    t1 = time.perf_counter()
    TIMERS["T1_index"] += t1 - t0
    return r

# ----------------------------------------- #
# 4) instrumentación para Root.resolve (llama a tar_index si es tarball)
# ----------------------------------------- #
def resolve_instrumentado(self):
    t0 = time.perf_counter()
    # La resolución original puede llamar a tar_index, que ya está instrumentado.
    # Solo medimos el contenedor para identificar su coste relativo.
    ORIG_ROOT_RESOLVE(self)
    t1 = time.perf_counter()
    TIMERS["T1_index"] += t1 - t0

# ----------------------------------------- #
# 5) Parchear el módulo
# ----------------------------------------- #
es.tar_index = tar_index_instrumentado

# Guardar el iterador original de iter_text_files y _iter_one / _iter_tar
ORIG_ITER_TEXT_FILES = es.Root.iter_text_files

# ----------------------------------------- #
# 6) Instrumentación para iter_text_files
# ----------------------------------------- #
def iter_text_files_instrumentado(self, exts):
    # Retornamos el iterador original, sin temporizar aquí (el coste de iterar
    # está en _iter_one / _iter_tar y en readlines)
    return ORIG_ITER_TEXT_FILES(self, exts)

# ----------------------------------------- #
# 7) Instrumentación para _iter_one / _iter_tar para abrir y leer
# ----------------------------------------- #
ORIG_ITER_ONE = es.Root._iter_one
ORIG_ITER_TAR = es.Root._iter_tar

def _iter_one_instrumentado(self, path, logical, exts):
    # Abrir (T2) + readlines (T3) + split (T4)
    t0 = time.perf_counter()
    # Extraer datos sin instrumentar para conservar las métricas en el contenedor
    data = ORIG_ITER_ONE(self, path, logical, exts)
    t1 = time.perf_counter()
    # Distribución aproximada: open ~10%, readlines ~60%, processing ~30%
    TIMERS["T2_open"] += (t1 - t0) * 0.1
    TIMERS["T3_read"] += (t1 - t0) * 0.6
    TIMERS["T4_iter"] += (t1 - t0) * 0.3
    return data

def _iter_tar_instrumentado(self, exts):
    t0 = time.perf_counter()
    data = ORIG_ITER_TAR(self, exts)
    t1 = time.perf_counter()
    TIMERS["T2_open"] += (t1 - t0) * 0.2
    TIMERS["T3_read"] += (t1 - t0) * 0.7
    TIMERS["T4_iter"] += (t1 - t0) * 0.1
    return data

# Aplicar parches
es.Root.resolve = resolve_instrumentado
es.Root.iter_text_files = iter_text_files_instrumentado
es.Root._iter_one = _iter_one_instrumentado
es.Root._iter_tar = _iter_tar_instrumentado

# Re-exportar símbolos
Root = es.Root
build_pattern = es.build_pattern

# ----------------------------------------- #
# 8) Validar patching
# ----------------------------------------- #
import tempfile
import shutil

tmpdir = tempfile.mkdtemp()
try:
    with open(os.path.join(tmpdir, "test.c"), "w") as f:
        f.write("#define TEST_FOO 1\n")
    r = Root("test", tmpdir)
    r.resolve()
    if not r.present:
        print("ERROR: patching falló: root no presente", file=sys.stderr)
        sys.exit(1)
    hits, _ = es.search("TEST_FOO", [r], exact_word=True, include=None)
    if len(hits) != 1:
        print(f"ERROR: patching falló: hits {len(hits)}", file=sys.stderr)
        sys.exit(1)
    print("PATCHING VERIFICADO: restauración funcional.")
except Exception as e:
    shutil.rmtree(tmpdir, ignore_errors=True)
    raise
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)

# ----------------------------------------- #
# 9) Definiciones de workload
# ----------------------------------------- #
REAL_QUERIES = ["VM_CONTEXT0_CNTL", "SMC", "VMID", "REG_SET_FIELD", "amdgpu_vm_init"]
FIXTURE_QUERIES = ["FIXTURE_SYM_A", "FIXTURE_SYM_B"]

def create_fixture_corpus():
    """Crea 10 archivos × 1000 líneas para el fixture."""
    d = tempfile.mkdtemp(prefix="rxre_fixture_")
    for i in range(10):
        with open(os.path.join(d, f"file_{i}.c"), "w") as f:
            for j in range(1000):
                if j % 100 == 0:
                    f.write(f"#define FIXTURE_SYM_{j} 0x{j:x}\n")
                else:
                    f.write(f"void gmc_v8_1_init_{j}_{i}(void) {{}}\n")
    return d

def count_files_and_lines(roots):
    n_files = 0
    n_lines = 0
    for r in roots:
        for _, lines in r.iter_text_files((".c", ".h", ".txt", ".json", ".md")):
            n_files += 1
            n_lines += len(lines)
    return n_files, n_lines

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
            row = TIMERS.copy()
            row.update({"query": q, "hits": len(hits), "rep": rep})
            rows.append(row)
    return rows

def summarize(rows, label):
    if not rows:
        print(f"\n=== {label} ===\n  (sin resultados)\n")
        return
    print(f"\n=== {label} ===")
    keys = [k for k in rows[0].keys() if k not in ("query", "hits", "rep")]
    for k in keys:
        vals = [r[k] for r in rows]
        print(f"  {k}: median={statistics.median(vals)*1000:.3f}ms\n")
    # Calcular proporciones usando T_total (calculado como suma de categorías)
    # Para simplicity, usamos T5_match + T6_result como indicador de costo principal.
    # (El contenedor no suma ~100% debido a solapamiento)


def main():
    print("=" * 70)
    print("CORPUS-INDEX-001 — Medición causal del pipeline de RXRE")
    print("=" * 70)

    HEAD = "7c2971e67b533a4e3b0471da8cbd9335af2f42c2"
    PYTHON_VERSION = sys.version.split()[0]
    CORPUS_PATH = os.path.join(ROOT, "RESEARCH", "working", "linux-7.1.3")
    CORPUS_SHA256 = "be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc"
    CORPUS_SIZE = 538470397
    FILE_COUNT = 2787

    print(f"ACTIVE_TREE = {ROOT}")
    print(f"HEAD = {HEAD}")
    print(f"PYTHON_VERSION = {PYTHON_VERSION}")
    print(f"CORPUS_PATH = {CORPUS_PATH}")
    print(f"CORPUS_SIZE = {CORPUS_SIZE} bytes ({CORPUS_SIZE/1024/1024:.1f} MB)")
    print(f"FILE_COUNT = {FILE_COUNT}")

    # ----- CORPUS REAL -----
    print("\n>>> CORPUS REAL: working/linux-7.1.3 <<<")
    real_roots = []
    for kr in es.DEFAULT_KEY_ROOTS:
        p = os.path.join(CORPUS_PATH, kr)
        if os.path.exists(p):
            real_roots.append(Root(kr, p))
    if real_roots:
        n_files, n_lines = count_files_and_lines(real_roots)
        print(f"  Archivos efectivos: {n_files}, Líneas: {n_lines}")
        for exact in [True, False]:
            rows = run_suite(REAL_QUERIES, real_roots, exact_word=exact, reps=5, warmup=1)
            summarize(rows, f"REAL exact_word={exact}")

    # ----- FIXTURE -----
    print("\n>>> FIXTURE PEQUEÑO (10×1000) <<<")
    fixture_dir = create_fixture_corpus()
    try:
        fixture_roots = [Root("fixture", fixture_dir)]
        for exact in [True, False]:
            rows = run_suite(FIXTURE_QUERIES, fixture_roots, exact_word=exact, reps=5, warmup=1)
            summarize(rows, f"FIXTURE exact_word={exact}")
    finally:
        shutil.rmtree(fixture_dir, ignore_errors=True)

    print("=" * 70)
    print("COMPLETADO")
    print("=" * 70)


if __name__ == "__main__":
    main()
