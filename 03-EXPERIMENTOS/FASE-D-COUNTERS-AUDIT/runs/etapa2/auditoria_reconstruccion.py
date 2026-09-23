#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auditoría FASE D Etapa 2 — reconstrucción independiente desde artefactos crudos.
Solo lectura. No ejecuta corridas."""
import csv, re, json, statistics as st

BASE = "/home/lucas/Escritorio/RX550_Iterative_Research/experiments/FASE-D-COUNTERS-AUDIT/runs/etapa2"
RUNS = ["A1", "B1", "A2", "B2", "A3", "B3"]
BLOCKS = ["vgt", "ta", "sx", "sh", "spi", "sc", "pa", "db", "cb"]

def tele_fire(fn):
    rows = []
    with open(fn) as f:
        for row in csv.DictReader(f, delimiter=";"):
            try:
                rows.append(dict(ts=int(row["ts"]) / 1e9,
                                 pw=int(row["power_uW"]) / 1e6,
                                 temp=int(row["temp_mC"]) / 1e3,
                                 gpu=int(row["gpu_busy"]), mem=int(row["mem_busy"]),
                                 sclk=int(row["sclk_level"].split(":")[0]),
                                 mclk=int(row["mclk_level"].split(":")[0])))
            except Exception:
                continue
    return rows

def steady_idxs(rows, min_n=100):
    if len(rows) < 60: return []
    kept = rows[50:-1]
    seg = [i for i, r in enumerate(kept) if r["gpu"] >= 95 and r["sclk"] == 7 and r["mclk"] == 2]
    return ([i + 50 for i in seg] if len(seg) >= min_n else [])

def sstats(v):
    return (round(st.mean(v), 2), round(st.median(v), 2), round(min(v), 2), round(max(v), 2), len(v))

out = {}
for run in RUNS:
    d = {}
    rows = tele_fire(f"{BASE}/{run}/telemetria.csv")
    d["tele_n"] = len(rows)
    full = [r["pw"] for r in rows]
    sidx = steady_idxs(rows)
    seg = [rows[i] for i in sidx]
    d["steady_n"] = len(seg)
    if seg:
        spw = [r["pw"] for r in seg]
        d["power_avg_steady"] = round(st.mean(spw), 3)
        d["power_max_steady"] = round(max(spw), 3)
        d["power_min_steady"] = round(min(spw), 3)
        d["power_median_steady"] = round(st.median(spw), 3)
        d["gpu_avg_steady"] = round(st.mean([r["gpu"] for r in seg]), 2)
        d["mem_avg_steady"] = round(st.mean([r["mem"] for r in seg]), 2)
        d["mem_max_steady"] = round(max(r["mem"] for r in seg), 2)
        d["temp_avg_steady"] = round(st.mean([r["temp"] for r in seg]), 2)
        d["sclk_levels_steady"] = {str(k): sum(1 for r in seg if r["sclk"] == k) for k in sorted(set(r["sclk"] for r in seg))}
        d["mclk_levels_steady"] = {str(k): sum(1 for r in seg if r["mclk"] == k) for k in sorted(set(r["mclk"] for r in seg))}
        t0, t1 = seg[0]["ts"], seg[-1]["ts"]
        d["window_s"] = round(t1 - t0, 1)
        d["power_full_avg"] = round(st.mean(full), 2)
        d["power_full_max"] = round(max(full), 2)
    # radeontop
    rt = []
    for ln in open(f"{BASE}/{run}/radeontop.csv", errors="replace"):
        m = re.match(r"^([\d.]+):.*?gpu ([\d.]+)%, .*?vgt ([\d.]+)%, ta ([\d.]+)%, sx ([\d.]+)%, "
                     r"sh ([\d.]+)%, spi ([\d.]+)%, sc ([\d.]+)%, pa ([\d.]+)%, db ([\d.]+)%, cb ([\d.]+)%, "
                     r"vram [\d.]+% [\d.]+mb, gtt [\d.]+% [\d.]+mb, "
                     r"mclk ([\d.]+)% ([\d.]+)ghz, sclk ([\d.]+)% ([\d.]+)ghz", ln)
        if m:
            g = m.groups()
            rt.append(dict(ts=float(g[0]), gpu=float(g[1]),
                           **{b: float(g[2 + i]) for i, b in enumerate(BLOCKS)},
                           mclk_pct=float(g[11]), mclk_ghz=float(g[12]),
                           sclk_pct=float(g[13]), sclk_ghz=float(g[14])))
    if seg:
        tlo, thi = seg[0]["ts"], seg[-1]["ts"]
        rtwin = [x for x in rt if tlo <= x["ts"] <= thi and x["gpu"] >= 95]
        rtall = [x for x in rt if tlo <= x["ts"] <= thi]
        d["rt_n_win_gpu95"] = len(rtwin)
        d["rt_n_win_all"] = len(rtall)
        d["rt_blocks_gpu95"] = {b: (round(st.mean([x[b] for x in rtwin]), 2),
                                    round(min(x[b] for x in rtwin), 2),
                                    round(max(x[b] for x in rtwin), 2)) for b in BLOCKS} if rtwin else {}
        d["rt_blocks_all"] = {b: round(st.mean([x[b] for x in rtall]), 2) for b in BLOCKS} if rtall else {}
    out[run] = d

print(json.dumps(out, indent=1, ensure_ascii=False))