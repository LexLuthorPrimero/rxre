#!/usr/bin/env python3
"""REGEX-T5-001 — Discriminative measurement of T5_match for exact_word=True.

Compare multiple regex backends on the SAME corpus, SAME queries, SAME work.
Instrument only T5_match (pattern search on lines), no corpus/index timing.
"""
from __future__ import annotations

import os
import re
import sys
import time
import statistics
import tempfile
import json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)

import tools.evidence_search as es

# ----------------------------------------------------------- #
# Corpus identity (immutable for experiment)
# ----------------------------------------------------------- #
CORPUS_PATH = os.path.join(ROOT, "RESEARCH", "working", "linux-7.1.3")
CORPUS_SHA256 = "be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc"
HEAD = "7c2971e67b533a4e3b0471da8cbd9335af2f42c2"

# ----------------------------------------------------------- #
# Workload queries (same as prior experiments)
# ----------------------------------------------------------- #
QUERIES = ["VM_CONTEXT0_CNTL", "SMC", "VMID", "REG_SET_FIELD", "amdgpu_vm_init"]
REPS = 5
WARMUP = 1

# ----------------------------------------------------------- #
# Helper: get file lines from corpus for a given set of key roots
# ----------------------------------------------------------- #
def get_corpus_files():
    """Return list of (filepath, lines_list) for all .c/.h/.txt/.json/.md files."""
    files_and_lines = []
    for kr in es.DEFAULT_KEY_ROOTS:
        p = os.path.join(CORPUS_PATH, kr)
        if os.path.exists(p):
            for dirpath, dirnames, filenames in os.walk(p):
                dirnames[:] = [d for d in dirnames if d not in es.SKIP_DIRS]
                for fn in sorted(filenames):
                    if fn.endswith((".c", ".h", ".txt", ".json", ".md")):
                        fp = os.path.join(dirpath, fn)
                        try:
                            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                                lines = f.readlines()
                            files_and_lines.append((fp, lines))
                        except (OSError, IOError):
                            pass
    return files_and_lines

# ----------------------------------------------------------- #
# Backend definitions — each is a pattern builder + matcher
# ----------------------------------------------------------- #
def make_c0(query, exact_word):
    """C0: stdlib re with \\b word boundary (current backend)."""
    body = re.escape(query)
    if not exact_word:
        return re.compile(body)
    prefix = r"\b" if query[:1].isalnum() or query[:1] == "_" else ""
    suffix = r"\b" if query[-1:].isalnum() or query[-1:] == "_" else ""
    return re.compile(prefix + body + suffix)

def make_c1(query, exact_word):
    """C1: stdlib re — same as C0 but with explicit word boundary via lookarounds."""
    body = re.escape(query)
    if not exact_word:
        return re.compile(body)
    # Same semantic as \b but using lookbehind/lookahead for precise control
    has_prefix = query[:1].isalnum() or query[:1] == "_"
    has_suffix = query[-1:].isalnum() or query[-1:] == "_"
    pattern = body
    if has_prefix:
        pattern = r"(?<!\w)" + pattern
    if has_suffix:
        pattern = pattern + r"(?!\w)"
    return re.compile(pattern)

def make_c2(query, exact_word):
    """C2: two-stage — str.find (literal) + manual boundary check."""
    if not exact_word:
        return ("plain", re.escape(query))
    return ("two_stage", query)

# ----------------------------------------------------------- #
# Matcher for backends
# ----------------------------------------------------------- #
def match_c0_c1(pattern, line):
    """Stdlib re match."""
    return pattern.search(line) is not None

def match_c2(prepared, line):
    """Two-stage: str.find + manual boundary check."""
    mode, data = prepared
    if mode == "plain":
        return re.search(data, line) is not None
    else:
        query = data
        if not query:
            return True
        i = 0
        ql = len(query)
        while i < len(line):
            pos = line.find(query, i)
            if pos == -1:
                break
            prefix_ok = True
            if query[:1].isalnum() or query[:1] == "_":
                if pos > 0 and (line[pos - 1].isalnum() or line[pos - 1] == "_"):
                    prefix_ok = False
            suffix_ok = True
            if query[-1:].isalnum() or query[-1:] == "_":
                after_pos = pos + ql
                if after_pos < len(line) and (line[after_pos].isalnum() or line[after_pos] == "_"):
                    suffix_ok = False
            if prefix_ok and suffix_ok:
                return True
            i = pos + 1
        return False

# ----------------------------------------------------------- #
# Semantic equivalence check
# ----------------------------------------------------------- #
def check_semantic_equivalence():
    """Verify that all backends produce identical match results on test cases."""
    test_lines = [
        "#define VM_CONTEXT0_CNTL 1",
        "void SMC_init(void) {}",
        "VMID is used in VM_CONTEXT0_CNTL",
        "this_is_VM_CONTEXT0_CNTL_",  # boundary test: should NOT match (suffix _word)
        "#define XVM_CONTEXT0_CNTLY",  # boundary: should NOT match
        "VM_CONTEXT0_CNTL",            # match
        "_VM_CONTEXT0_CNTL",           # _ prefix: \b should match (alnum)
        "123VM_CONTEXT0_CNTL",         # numeric prefix: should NOT match
    ]
    queries = [
        ("VM_CONTEXT0_CNTL", True),
        ("VM_CONTEXT0_CNTL", False),
        ("SMC", True),
        ("_", True),
        ("", True),
    ]
    
    for q, ew in queries:
        results = {}
        for name, maker, matcher in [
            ("c0", make_c0, match_c0_c1),
            ("c1", make_c1, match_c0_c1),
            ("c2", make_c2, match_c2),
        ]:
            pattern = maker(q, ew)
            matches = [bool(matcher(pattern, line)) for line in test_lines]
            results[name] = matches
        
        # Compare all
        ref = results["c0"]
        for name in ["c1", "c2"]:
            if results[name] != ref:
                print(f"SEMANTIC_DIFF: query={q!r} exact_word={ew}", file=sys.stderr)
                for i, line in enumerate(test_lines):
                    if results[name][i] != ref[i]:
                        print(f"  line={line!r}: c0={ref[i]} c2={results[name][i]}", file=sys.stderr)
                return False
    
    print("SEMÁNTICA OK: c0, c1, c2 producen resultados idénticos en casos de borde.")
    return True

# ----------------------------------------------------------- #
# Main measurement
# ----------------------------------------------------------- #
def run_matcher_on_corpus(maker, matcher, queries, exact_word=True, reps=REPS, warmup=WARMUP):
    """Medir T_match: solo el tiempo de pattern.search sobre las líneas del corpus.
    No incluye corpus discovery, file open, line read (ya leídos)."""
    # Pre-load all files and lines (to isolate T5 only)
    files_and_lines = get_corpus_files()
    
    # Warmup
    for q in queries:
        pattern = maker(q, exact_word)
        for _, lines in files_and_lines:
            for line in lines:
                matcher(pattern, line)
    
    # Measure
    times = []
    hits_total = 0
    total_lines = sum(len(lines) for _, lines in files_and_lines)
    
    for rep in range(reps):
        for q in queries:
            pattern = maker(q, exact_word)
            t0 = time.perf_counter()
            query_hits = 0
            for _, lines in files_and_lines:
                for line in lines:
                    if matcher(pattern, line):
                        query_hits += 1
            t1 = time.perf_counter()
            times.append(t1 - t0)
            hits_total += query_hits
    
    return {
        "T_match_median": statistics.median(times) * 1000,  # ms
        "T_match_mean": statistics.mean(times) * 1000,
        "T_match_p95": (statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times)) * 1000,
        "total_times": times,
        "hits": hits_total / (reps * len(queries)),  # hits per query average
        "total_lines": total_lines,
        "total_files": len(files_and_lines),
        "reps": reps,
    }

def main():
    print("=" * 70)
    print("REGEX-T5-001 — Medición discriminante de T5_match para exact_word=True")
    print("=" * 70)
    
    print(f"ACTIVE_TREE = {ROOT}")
    print(f"HEAD = {HEAD}")
    print(f"CORPUS_PATH = {CORPUS_PATH}")
    print(f"CORPUS_SHA256 = {CORPUS_SHA256}")
    
    # Check semantic equivalence first
    print("\n>>> VERIFICACIÓN SEMÁNTICA <<<")
    if not check_semantic_equivalence():
        print("FALLO SEMÁNTICO. Abortando.")
        sys.exit(1)
    
    # Load corpus
    print("\n>>> CARGANDO CORPUS <<<")
    t0 = time.perf_counter()
    files_and_lines = get_corpus_files()
    t1 = time.perf_counter()
    n_files = len(files_and_lines)
    n_lines = sum(len(lines) for _, lines in files_and_lines)
    n_bytes = sum(os.path.getsize(fp) for fp, _ in files_and_lines)
    print(f"  Archivos: {n_files}")
    print(f"  Líneas: {n_lines}")
    print(f"  Bytes: {n_bytes} ({n_bytes/1024/1024:.1f} MB)")
    print(f"  Tiempo de carga: {(t1-t0)*1000:.1f}ms (NO incluido en T_match)")
    
    # Run measurements for C0 and C2 (the interesting comparison)
    print("\n>>> MEDICIÓN DE C0 (stdlib re con \\b word boundary — actual) <<<")
    c0_result = run_matcher_on_corpus(make_c0, match_c0_c1, QUERIES, exact_word=True, reps=REPS, warmup=WARMUP)
    
    print("\n>>> MEDICIÓN DE C1 (stdlib re con lookbehind/lookahead) <<<")
    c1_result = run_matcher_on_corpus(make_c1, match_c0_c1, QUERIES, exact_word=True, reps=REPS, warmup=WARMUP)
    
    print("\n>>> MEDICIÓN DE C2 (two-stage: str.find + manual boundary) <<<")
    c2_result = run_matcher_on_corpus(make_c2, match_c2, QUERIES, exact_word=True, reps=REPS, warmup=WARMUP)
    
    # Results table
    print("\n" + "=" * 80)
    print("REGEX-T5-001 — RESULTADOS")
    print("=" * 80)
    print(f"{'Candidate':<35} {'T5_match median (ms)':>25} {'Speedup vs C0':>18} {'Hits/query':>15}")
    print("-" * 100)
    
    results = [
        (c0_result, "c0 (stdlib re + \\b) — BASELINE"),
        (c1_result, "c1 (stdlib re + lookaround)"),
        (c2_result, "c2 (two-stage str.find)"),
    ]
    
    for r, name in results:
        speedup = c0_result["T_match_median"] / r["T_match_median"] if r["T_match_median"] > 0 else 0
        print(f"{name:<35} {r['T_match_median']:>25.2f} {speedup:>18.2f}x {r['hits']:>15.1f}")
    
    # Save raw results
    os.makedirs(HERE, exist_ok=True)
    results_json = {
        "metadata": {
            "HEAD": HEAD,
            "corpus_path": CORPUS_PATH,
            "corpus_sha256": CORPUS_SHA256,
            "queries": QUERIES,
            "reps": REPS,
            "warmup": WARMUP,
        },
        "corpus_stats": {
            "n_files": n_files,
            "n_lines": n_lines,
            "n_bytes": n_bytes,
            "load_time_ms": (t1-t0)*1000,
        },
        "results": {
            "c0_baseline": c0_result,
            "c1_lookaround": c1_result,
            "c2_two_stage": c2_result,
        },
        "semantic_check": "PASSED",
    }
    
    json_path = os.path.join(HERE, "regex_t5_001_results.json")
    with open(json_path, "w") as f:
        json.dump(results_json, f, indent=2)
    print(f"\nRaw results saved to: {json_path}")
    
    # Decision
    c0_t = c0_result["T_match_median"]
    c1_t = c1_result["T_match_median"]
    c2_t = c2_result["T_match_median"]
    
    print(f"\n--- DECISION ---")
    print(f"C0 (baseline): {c0_t:.2f}ms")
    print(f"C1 (lookaround): {c1_t:.2f}ms (speedup: {c0_t/c1_t:.2f}x)")
    print(f"C2 (two-stage): {c2_t:.2f}ms (speedup: {c0_t/c2_t:.2f}x)")
    
    # Final assessment
    if c2_t < c0_t * 0.9:
        print(f"\nC2 ofrece una mejora >10% sobre C0.")
        print(f"  → Estado de C2: SAFE_BUT_NOT_FASTER (verifica semántica)")
    elif c1_t < c0_t * 0.9:
        print(f"\nC1 ofrece una mejora >10% sobre C0.")
    else:
        print(f"\nNingún candidato supera a C0.")
    
    print(f"\nT5_FRONTIER_CHARACTERIZED: DONE")

if __name__ == "__main__":
    main()
