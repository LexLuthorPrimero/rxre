#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""analyze.py — análisis EXP-F4-A (FASE R-4B). READ-ONLY sobre results/.

Phase 1 (por sesión): p99 por bloque open-loop -> P99(s)=mediana de 3 bloques;
  GATEs (§6.1): monotonía (P99 no creciente en s descendente), ≥2 pasos ≥3 %,
  rango 5–200 ms, histéresis asc<->desc ≤15 % (§14-D) -> T=0.80·P99(1.00),
  s* = max{s : P99_openloop(s) ≤ T}, reachability -> manifest.json (FREEZE sha256).
Phase 2 (por sesión): ventanas de 20 s alineadas a t0 (m0); settle = últimas 2
  ventanas; métricas R1–R7 y pregunta E; métricas de potencia según
  METRICS-DEFINITIONS.md (power_avg_full/steady/max_full/max_steady).
Final (ambas sesiones): veredictos R1–R7, E (Wilcoxon pareado, bootstrap 90 %),
  falsación F1–F6, clasificación VERIFIED/DERIVED/ESTIMATED/UNKNOWN.

Uso:
  analyze.py phase1 --session-dir results/sessionN
  analyze.py phase2 --session-dir results/sessionN
  analyze.py final --results-dir results
"""
import argparse
import hashlib
import json
import os
import statistics as st
import numpy as np
from scipy import stats as sps

SCALES = [1.00, 0.87, 0.75, 0.62, 0.50]
STEP = {s: i for i, s in enumerate(SCALES)}
WINDOW_S = 20.0
TAG = {1.00: "s100", 0.87: "s087", 0.75: "s075", 0.62: "s062", 0.50: "s050"}
RNG = np.random.default_rng(0x5EED)


def p99(xs):
    if not xs:
        return None
    s = sorted(xs)
    k = max(1, int(np.ceil(0.99 * len(s))))
    return float(s[k - 1])


def load_frames(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            p = line.split("\t")
            if len(p) < 5:
                continue
            try:
                rows.append((float(p[0]), int(p[1]), int(p[2]), float(p[3]), int(p[4])))
            except ValueError:
                continue
    return rows  # (epoch_s, mono_us, frame_us, scale, layers)


def block_p99(frames_path):
    rows = load_frames(frames_path)
    return p99([r[2] for r in rows]), len(rows)


def load_telemetry(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path) as f:
        for line in f:
            p = line.strip().split(";")
            if len(p) < 11:
                continue
            if p[0] == "ts_ns":
                continue
            try:
                rows.append({
                    "t": int(p[0]) / 1e9,
                    "power_w": int(p[1]) / 1e6,
                    "temp_mc": int(p[2]),
                    "gpu_busy": int(p[3]),
                    "mem_busy": int(p[4]),
                    "sclk_mhz": int(p[8]) if p[8] != "N/A" else 0,
                    "mclk_mhz": int(p[10]) if p[10] != "N/A" else 0,
                })
            except ValueError:
                continue
    return rows


def power_metrics(rows, t0, t1):
    """METRICS-DEFINITIONS.md sobre ventana [t0,t1] (epoch s, pared)."""
    win = [r for r in rows if t0 <= r["t"] <= t1]
    out = {"power_avg_full": None, "power_max_full": None,
           "power_avg_steady": None, "power_max_steady": None,
           "steady_window_samples": 0, "steady_window_duration_s": 0.0}
    if not win:
        return out
    pw = [r["power_w"] for r in win]
    out["power_avg_full"] = float(np.mean(pw))
    out["power_max_full"] = float(np.max(pw))
    steady = [r for r in win if r["gpu_busy"] >= 95
              and r["sclk_mhz"] >= 1071 and r["mclk_mhz"] >= 1500]
    # exclusiones obligatorias (METRICS-DEFINITIONS §1.4): primeras ~50 muestras
    # (~5 s) y última muestra de la ventana
    if len(steady) >= 51:
        steady = steady[50:-1]
    if len(steady) >= 100:
        pw2 = [r["power_w"] for r in steady]
        out["power_avg_steady"] = float(np.mean(pw2))
        out["power_max_steady"] = float(np.max(pw2))
        out["steady_window_samples"] = len(steady)
        out["steady_window_duration_s"] = len(steady) * 0.1
    return out


def sha256_canonical(obj):
    s = json.dumps(obj, sort_keys=True, indent=2, default=str)
    return hashlib.sha256(s.encode()).hexdigest()


def bootstrap_ci(values, stat=np.median, n=20000, alpha=0.90):
    vals = np.asarray(values, dtype=float)
    draws = RNG.choice(vals, size=(n, len(vals)))
    b = [stat(d) for d in draws]
    lo = np.percentile(b, 100 * (1 - alpha) / 2)
    hi = np.percentile(b, 100 * (1 + alpha) / 2)
    return float(lo), float(hi)


# ---------------- PHASE 1 ----------------

def phase1(session_dir):
    blocks = os.path.join(session_dir, "fase1", "blocks")
    manifest = {"session": os.path.basename(session_dir), "version": "2.1",
                "T_ms": None, "s_star": None, "P99_curve_ms": {},
                "p99_blocks_us": {}, "gates": {}, "sha256": None}
    curve = {}
    blocks_us = {}
    for s in SCALES:
        t = TAG[s]
        vals = []
        bp = {}
        for pass_n in ("p1", "p2", "p3"):
            d = os.path.join(blocks, f"{pass_n}_{t}")
            fp = os.path.join(d, "frames.tsv")
            if not os.path.exists(fp):
                raise SystemExit(f"[phase1] falta bloque {d}")
            v, n = block_p99(fp)
            bp[pass_n] = v
            vals.append(v)
            if n < 60:
                print(f"[phase1] AVISO: {d} solo {n} frames")
        blocks_us[s] = bp
        curve[s] = st.median(vals) / 1000.0  # ms
    manifest["p99_blocks_us"] = {str(k): v for k, v in blocks_us.items()}
    manifest["P99_curve_ms"] = {str(k): v for k, v in curve.items()}

    # GATE 1: monotonía no creciente al recorrer s de 1.00 a 0.50
    seq = [curve[s] for s in SCALES]
    monotonic = all(seq[i] >= seq[i + 1] - 1e-9 for i in range(len(seq) - 1))
    # GATE 2: ≥2 pasos consecutivos con reducción ≥3 %
    reds = [(seq[i] - seq[i + 1]) / seq[i] for i in range(len(seq) - 1)]
    best_run = run = 0
    for r in reds:
        run = run + 1 if r >= 0.03 else 0
        best_run = max(best_run, run)
    steps_ok = best_run >= 2
    # GATE 3: rango sanity 5–200 ms en P99(1.00)
    range_ok = 5.0 <= curve[1.00] <= 200.0
    # GATE 4: histéresis asc<->desc ≤15 % (por escala)
    hyst = 0.0
    for s in SCALES:
        b = blocks_us[s]
        asc = st.median([b["p1"], b["p3"]])
        h = abs(b["p2"] - asc) / asc if asc else 0.0
        hyst = max(hyst, h)
    hyst_ok = hyst <= 0.15
    gates = {"monotonic": monotonic, "steps_ge3pct": steps_ok,
             "best_consecutive_steps": best_run, "range_5_200ms": range_ok,
             "hysteresis_max": round(hyst, 4), "hysteresis_le15pct": hyst_ok}
    manifest["gates"] = gates

    if not (monotonic and steps_ok and range_ok):
        raise SystemExit("[phase1] PARADA D: GATE calibración fallido (§6.1.4/5) -> "
                         + json.dumps(gates))
    if not hyst_ok:
        raise SystemExit("[phase1] PARADA D: histéresis asc<->desc >15 % (§14-D) -> "
                         + json.dumps(gates))

    T_ms = round(0.80 * curve[1.00], 3)
    s_star = next((s for s in SCALES if curve[s] <= T_ms + 1e-9), None)
    if s_star is None:
        raise SystemExit("[phase1] PARADA D: reachability fallida (§6.3) -> " + str(curve))
    manifest["T_ms"] = T_ms
    manifest["s_star"] = s_star
    manifest["gates"]["reachability"] = True
    manifest["sha256"] = sha256_canonical(
        {k: v for k, v in manifest.items() if k != "sha256"})

    out = os.path.join(session_dir, "fase1", "manifest.json")
    with open(out, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"[phase1] T={T_ms} ms  s*={s_star}  gates={json.dumps(gates)}")
    print(f"[phase1] manifest: {out} sha256={manifest['sha256'][:16]}…")
    return manifest


# ---------------- PHASE 2 ----------------

def window_stats(frames, wb, we, T_us):
    sel = [r for r in frames if wb <= r[1] < we]
    if not sel:
        return None
    ft = [r[2] for r in sel]
    scales = [r[3] for r in sel]
    s_mode = max(set(scales), key=scales.count)
    over = 100.0 * sum(1 for x in ft if x > T_us) / len(ft)
    return {"n": len(sel), "p99_us": p99(ft), "mean_us": float(np.mean(ft)),
            "median_us": float(np.median(ft)), "scale": s_mode,
            "lays": st.mode([r[4] for r in sel]),
            "overshoot_pct": round(over, 2)}


def load_governor_trace(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path) as f:
        for line in f:
            if line.startswith("#"):
                continue
            p = line.split("\t")
            if len(p) < 6:
                continue
            try:
                out.append({"win": int(p[0]), "wb": int(p[1]), "we": int(p[2]),
                            "p99": float(p[3]), "scale": float(p[4]),
                            "action": p[5].strip()})
            except ValueError:
                continue
    return out


def load_trial(session_dir, cond, idx):
    d = os.path.join(session_dir, "fase2", f"{cond}{idx}")
    frames = load_frames(os.path.join(d, "run_frames.tsv"))
    tel = load_telemetry(os.path.join(d, "telemetry.csv"))
    m0_file = os.path.join(d, "run_m0.txt")
    if not os.path.exists(m0_file):
        raise SystemExit(f"[phase2] falta m0 para {cond}{idx}: {m0_file}")
    with open(m0_file) as f:
        lines = f.read().split()
        t0_us = int(lines[0])
        t0_epoch = float(lines[1]) if len(lines) > 1 else (frames[0][0] if frames else 0.0)
    trace = load_governor_trace(os.path.join(d, "governor_trace.tsv"))
    return frames, tel, t0_us, t0_epoch, trace


def windows_of(frames, t0_us, t0_epoch, T_us, nwin):
    wins = []
    for k in range(nwin):
        wb = t0_us + int(k * WINDOW_S * 1e6)
        we = t0_us + int((k + 1) * WINDOW_S * 1e6)
        ws = window_stats(frames, wb, we, T_us)
        if ws is None:
            continue
        ws["win"] = k + 1
        ws["epoch_lo"] = t0_epoch + k * WINDOW_S
        ws["epoch_hi"] = t0_epoch + (k + 1) * WINDOW_S
        wins.append(ws)
    return wins


def analyze_gov_or_dist(frames, tel, t0_us, t0_epoch, T_us, nwin):
    wins = windows_of(frames, t0_us, t0_epoch, T_us, nwin)
    power = power_metrics(tel, t0_epoch, t0_epoch + nwin * WINDOW_S)
    return wins, power


def phase2(session_dir, order):
    """order: lista de "cond" por sesión (§7). Ej: ['fixed','gov','fixed',...]"""
    mf = os.path.join(session_dir, "fase1", "manifest.json")
    with open(mf) as f:
        man = json.load(f)
    T_ms, s_star = man["T_ms"], man["s_star"]
    T_us = T_ms * 1000.0

    gov, fixed, dist = [], [], []
    cnt = {"fixed": 0, "gov": 0, "dist": 0}
    for cond in order:
        cnt[cond] += 1
        idx = cnt[cond]
        dur = {"fixed": 60.0, "gov": 120.0, "dist": 200.0}[cond]
        frames, tel, t0_us, t0_epoch, trace = load_trial(session_dir, cond, idx)
        if cond in ("gov", "dist"):
            wins, power = analyze_gov_or_dist(frames, tel, t0_us, t0_epoch, T_us,
                                              int(dur / WINDOW_S))
        else:
            wins = windows_of(frames, t0_us, t0_epoch, T_us, int(dur / WINDOW_S))
            power = power_metrics(tel, t0_epoch, t0_epoch + dur)
        tr = {"cond": cond, "idx": idx, "wins": wins, "trace": trace,
              "t0_epoch": t0_epoch, "t0_us": t0_us, "power_trial_full": power,
              "power_wins": [power_metrics(tel, w["epoch_lo"], w["epoch_hi"]) for w in wins]}
        (gov if cond == "gov" else fixed if cond == "fixed" else dist).append(tr)

    result = {"session": os.path.basename(session_dir), "T_ms": T_ms,
              "s_star": s_star, "gov": gov, "fixed": fixed, "dist": dist}
    with open(os.path.join(session_dir, "fase2", "metrics.json"), "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"[phase2] {result['session']}: gov={len(gov)} fixed={len(fixed)} dist={len(dist)}")
    return result


# ---------------- FINAL (ambas sesiones) ----------------

def _settle_metrics(tr):
    """GOV: últimas 2 ventanas de 6 (v5,v6). FIXED: últimas 2 de 3."""
    n = len(tr["wins"])
    settle = tr["wins"][n - 2:]
    return settle


def final(results_dir):
    man1 = json.load(open(os.path.join(results_dir, "session1", "fase1", "manifest.json")))
    man2 = json.load(open(os.path.join(results_dir, "session2", "fase1", "manifest.json")))
    m1 = json.load(open(os.path.join(results_dir, "session1", "fase2", "metrics.json")))
    m2 = json.load(open(os.path.join(results_dir, "session2", "fase2", "metrics.json")))

    gov_all = m1["gov"] + m2["gov"]           # n=6
    fixed_all = m1["fixed"] + m2["fixed"]     # n=6, pares por posición
    dist_all = m1["dist"] + m2["dist"]        # n=4

    # --- R1 ---
    r_vals = []
    for tr in gov_all:
        settle = _settle_metrics(tr)
        r = st.median([w["p99_us"] for w in settle]) / (m1["T_ms"] * 1000.0)
        tr["r"] = r
        r_vals.append(r)
    r1_ok = sum(1 for r in r_vals if 0.90 <= r <= 1.10) >= 5
    ci_r = bootstrap_ci(r_vals)
    r1_ok = r1_ok and ci_r[0] >= 0.90 and ci_r[1] <= 1.10

    # --- R2 overshoot en settle ---
    over_all = []
    for tr in gov_all:
        settle = _settle_metrics(tr)
        o = st.mean([w["overshoot_pct"] for w in settle])
        tr["overshoot_settle"] = o
        over_all.append(o)
    r2_ok = sum(1 for o in over_all if o <= 1.0) >= 5 and all(o <= 2.0 for o in over_all)

    # --- R3 reversiones sostenidas ---
    rev_all = []
    for tr in gov_all:
        acts = [t for t in tr["trace"] if t["action"] in ("LOWER", "RAISE")]
        rev = 0
        for i in range(1, len(acts)):
            if acts[i]["action"] != acts[i - 1]["action"]:
                # reversión: p99 vuelve a cruzar el mismo umbral ≤2 ventanas después
                j = acts[i]["win"]
                later = [w for w in tr["wins"] if w["win"] in (j + 1, j + 2)]
                if acts[i]["action"] == "RAISE":
                    cond = any(w["p99_us"] < 0.90 * m1["T_ms"] * 1000.0 for w in later)
                else:
                    cond = any(w["p99_us"] > 1.10 * m1["T_ms"] * 1000.0 for w in later)
                if cond:
                    rev += 1
        tr["reversals"] = rev
        rev_all.append(rev)
    r3_ok = sum(1 for r in rev_all if r == 0) >= 5

    # --- R4 convergencia (GOV) ---
    conv = []
    for tr in gov_all:
        c = None
        for i in range(len(tr["wins"]) - 1):
            a, b = tr["wins"][i], tr["wins"][i + 1]
            if (0.90 * m1["T_ms"] * 1000.0 <= a["p99_us"] <= 1.10 * m1["T_ms"] * 1000.0
                    and 0.90 * m1["T_ms"] * 1000.0 <= b["p99_us"] <= 1.10 * m1["T_ms"] * 1000.0):
                c = b["win"]
                break
        tr["convergence_window"] = c
        conv.append(c)
    r4_ok = sum(1 for c in conv if c is not None and c <= 4) >= 5

    # --- R5 reproducibilidad ---
    cv_r = float(np.std(r_vals) / np.mean(r_vals)) if len(r_vals) > 1 else 0.0
    r5_cv_ok = cv_r <= 0.10
    med_s1 = st.median([tr["r"] for tr in m1["gov"]])
    med_s2 = st.median([tr["r"] for tr in m2["gov"]])
    med_diff = abs(med_s1 - med_s2) / max(med_s1, med_s2) if med_s1 and med_s2 else 0.0
    r5_med_ok = med_diff <= 0.15
    # predicción de dirección: cada LOWER debe tener p99>hi previo; cada RAISE p99<lo
    hits = tot = 0
    for tr in gov_all:
        for t in tr["trace"]:
            if t["action"] == "LOWER" and t["p99"] > 1.10 * m1["T_ms"] * 1000.0:
                hits += 1
            elif t["action"] == "RAISE" and t["p99"] < 0.90 * m1["T_ms"] * 1000.0:
                hits += 1
            if t["action"] in ("LOWER", "RAISE"):
                tot += 1
    dir_pred = hits / tot if tot else 1.0
    r5_dir_ok = dir_pred >= 0.90
    r5_ok = r5_cv_ok and r5_med_ok and r5_dir_ok

    # --- R6 Δ pasos vs s* ---
    s_star = m1["s_star"]
    deltas = []
    for tr in gov_all:
        settle = _settle_metrics(tr)
        s_settled = st.mode([w["scale"] for w in settle])
        d = abs(STEP[s_star] - STEP[s_settled]) if s_star is not None else None
        tr["s_settled"] = s_settled
        tr["delta_steps"] = d
        deltas.append(d)
    r6_ok = sum(1 for d in deltas if d == 0) >= 5

    # --- R7 DIST latencias ---
    r7_rows = []
    ok_low = ok_raise = ok_reinc = 0
    for tr in dist_all:
        acts = [t for t in tr["trace"] if t["action"] == "LOWER"
                and (t["we"] - tr["t0_us"]) / 1e6 >= 55.0]
        lat_low = None
        if acts:
            lat_low = round(((acts[0]["we"] - tr["t0_us"]) / 1e6 - 60.0) / WINDOW_S, 1)
        raises = [t for t in tr["trace"] if t["action"] == "RAISE"
                  and (t["we"] - tr["t0_us"]) / 1e6 >= 115.0]
        lat_raise = None
        if raises:
            lat_raise = round(((raises[0]["we"] - tr["t0_us"]) / 1e6 - 120.0) / WINDOW_S, 1)
        # re-incorporación a banda tras cada evento (≤2 ventanas = ventana de inicio ≤ evento+2*20)
        reinc_step = reinc_ret = None
        for w in tr["wins"]:
            if w["epoch_lo"] - tr["t0_epoch"] >= 60.0 and \
               0.90 * m1["T_ms"] * 1000.0 <= w["p99_us"] <= 1.10 * m1["T_ms"] * 1000.0:
                reinc_step = round((w["epoch_lo"] - tr["t0_epoch"] - 60.0) / WINDOW_S, 1)
                break
        for w in tr["wins"]:
            if w["epoch_lo"] - tr["t0_epoch"] >= 120.0 - 1e-6 and \
               0.90 * m1["T_ms"] * 1000.0 <= w["p99_us"] <= 1.10 * m1["T_ms"] * 1000.0:
                reinc_ret = round((w["epoch_lo"] - tr["t0_epoch"] - 120.0) / WINDOW_S, 1)
                break
        ok_low += lat_low is not None and lat_low <= 2.0
        ok_raise += lat_raise is not None and lat_raise <= 2.0
        ok_reinc += (reinc_step is not None and reinc_step <= 2.0
                     and reinc_ret is not None and reinc_ret <= 2.0)
        r7_rows.append({"lat_low_wins": lat_low, "lat_raise_wins": lat_raise,
                        "reinc_step_wins": reinc_step, "reinc_ret_wins": reinc_ret})
    r7_ok = (ok_low == 4 and ok_raise == 4 and ok_reinc == 4)

    # --- E (pareada, n=6) ---
    pairs = []
    for i in range(6):
        g = gov_all[i]
        f = fixed_all[i]
        pg = st.median([w["p99_us"] for w in _settle_metrics(g)])
        pf = st.median([w["p99_us"] for w in _settle_metrics(f)])
        pairs.append({"pair": i + 1, "p99_gov_us": pg, "p99_fixed_us": pf,
                      "s_gov": g.get("s_settled"), "s_fixed": 1.00,
                      "rel_diff_pct": round(100.0 * (pg - pf) / pf, 2), "r": g["r"]})
    rel = [p["rel_diff_pct"] for p in pairs]
    wil = sps.wilcoxon([p["p99_gov_us"] for p in pairs],
                       [p["p99_fixed_us"] for p in pairs])
    ci_rel = bootstrap_ci(rel)

    # --- falsaciones F1–F6 ---
    f1 = sum(1 for c in conv if c is None or c > 6) >= 2
    f2 = not (ci_r[0] >= 0.90 and ci_r[1] <= 1.10) or sum(1 for r in r_vals if not 0.90 <= r <= 1.10) >= 2
    f3 = sum(1 for r in rev_all if r >= 1) >= 2
    f4 = (4 - ok_low) >= 2 or (4 - ok_raise) >= 2 or (4 - ok_reinc) >= 2
    f5 = False  # GATEs pasaron en ambas sesiones (si no, parada D antes)
    f6 = cv_r > 0.10 or med_diff > 0.15
    falsified = f5 or sum([f1, f2, f3, f4, f6]) >= 2
    n_ok = sum([r1_ok, r2_ok, r3_ok, r4_ok, r5_ok, r6_ok, r7_ok])
    verdict = "INCONCLUSO" if (not falsified and n_ok < 7) else \
              ("FALSADO" if falsified else "HIPÓTESIS APOYADA")

    out = {
        "session1_manifest": man1, "session2_manifest": man2,
        "metrics": {"session1": m1, "session2": m2},
        "R1": {"r_vals": r_vals, "ci_r_median_90": ci_r, "ok": r1_ok},
        "R2": {"overshoot_pct": over_all, "ok": r2_ok},
        "R3": {"reversals": rev_all, "ok": r3_ok},
        "R4": {"convergence_window": conv, "ok": r4_ok},
        "R5": {"cv_r": cv_r, "med_s1": med_s1, "med_s2": med_s2,
               "med_diff_pct": round(100 * med_diff, 2), "dir_pred": dir_pred,
               "ok": r5_ok},
        "R6": {"deltas": deltas, "s_star": s_star, "s_settled": [tr.get("s_settled") for tr in gov_all],
               "ok": r6_ok},
        "R7": {"rows": r7_rows, "ok_low": ok_low, "ok_raise": ok_raise,
               "ok_reinc": ok_reinc, "ok": r7_ok},
        "E": {"pairs": pairs, "wilcoxon": {"stat": float(wil.statistic),
                                           "pvalue": float(wil.pvalue)},
              "rel_diff_mean_pct": round(float(np.mean(rel)), 2),
              "ci_rel_diff_90": ci_rel},
        "F": {"f1": f1, "f2": f2, "f3": f3, "f4": f4, "f5": f5, "f6": f6,
              "falsified": falsified},
        "verdict": verdict,
        "n_metrics_ok": n_ok,
    }
    with open(os.path.join(results_dir, "verdict.json"), "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"[final] veredicto: {verdict} ({n_ok}/7 métricas OK)  falsado={falsified}")
    print(f"[final] R1 r={[round(r,3) for r in r_vals]} ci={tuple(round(x,3) for x in ci_r)}")
    print(f"[final] R2 overshoot={[round(o,2) for o in over_all]}  R3 rev={rev_all}")
    print(f"[final] R4 conv={conv}  R5 cv={cv_r:.4f} dir={dir_pred:.2f} medΔ={100*med_diff:.1f}%")
    print(f"[final] R6 Δ={deltas} s*={s_star}  R7 {r7_rows}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["phase1", "phase2", "final"])
    ap.add_argument("--session-dir")
    ap.add_argument("--results-dir")
    ap.add_argument("--order", default="fixed,gov,fixed,gov,fixed,gov,dist,dist")
    args = ap.parse_args()
    if args.phase == "phase1":
        assert args.session_dir
        phase1(args.session_dir)
    elif args.phase == "phase2":
        assert args.session_dir and args.order
        phase2(args.session_dir, [c.strip() for c in args.order.split(",")])
    else:
        assert args.results_dir
        final(args.results_dir)