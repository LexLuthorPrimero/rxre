#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv, re, json, os
from collections import OrderedDict

BASE = "/home/lucas/Escritorio/RX550_Iterative_Research/experiments/FASE-D-COUNTERS-AUDIT/runs/etapa2"
RUNS = ["A1", "B1", "A2", "B2", "A3", "B3"]
WLKIND = {"A1": "A", "B1": "B", "A2": "A", "B2": "B", "A3": "A", "B3": "B"}

BLOCKS = ["vgt", "ta", "sx", "sh", "spi", "sc", "pa", "db", "cb"]


def load_telemetry(path):
    rows = []
    with open(path, newline="") as f:
        r = csv.DictReader(f, delimiter=";")
        for row in r:
            try:
                rows.append({
                    "ts": int(row["ts"]) / 1e9,
                    "power_uW": int(row["power_uW"]),
                    "temp_mC": int(row["temp_mC"]),
                    "gpu": int(row["gpu_busy"]),
                    "mem": int(row["mem_busy"]),
                    "vram": int(row["vram_used"]),
                    "sclk_str": row["sclk_level"],
                    "mclk_str": row["mclk_level"],
                })
            except Exception:
                continue
    return rows


def steady_mask(rows):
    # filtro METRICS-DEFINITIONS: gpu_busy>=95 y sclk nivel 7 (1071) y mclk nivel 2 (1500)
    return [i for i, x in enumerate(rows)
            if x["gpu"] >= 95 and x["sclk_str"].startswith("7:") and x["mclk_str"].startswith("2:")]


def load_radeontop(path):
    lines = []
    pat = re.compile(
        r"^([\d.]+): bus \d+, gpu ([\d.]+)%, ee ([\d.]+)%, "
        r"(?:vgt ([\d.]+)%, ta ([\d.]+)%, sx ([\d.]+)%, sh ([\d.]+)%, spi ([\d.]+)%, "
        r"sc ([\d.]+)%, pa ([\d.]+)%, db ([\d.]+)%, cb ([\d.]+)%, )?"
        r"vram ([\d.]+)% [\d.]+mb, gtt ([\d.]+)% [\d.]+mb, "
        r"mclk ([\d.]+)% ([\d.]+)ghz, sclk ([\d.]+)% ([\d.]+)ghz")
    for ln in open(path, errors="replace"):
        ln = ln.strip()
        if not ln:
            continue
        m = pat.match(ln)
        if not m:
            continue
        g = m.groups()
        d = {"ts": float(g[0]), "gpu": float(g[1]), "ee": float(g[2])}
        if g[3] is not None:
            for i, b in enumerate(BLOCKS):
                d[b] = float(g[3 + i])
            d["vram"] = float(g[12])
            d["gtt"] = float(g[13])
            d["mclk_pct"] = float(g[14]); d["mclk_ghz"] = float(g[15])
            d["sclk_pct"] = float(g[16]); d["sclk_ghz"] = float(g[17])
        lines.append(d)
    return lines


def load_umr(path):
    samples = []
    for ln in open(path, errors="replace"):
        ln = ln.strip()
        if not ln:
            continue
        m = re.search(r"ts_ns=(\d+)", ln)
        if not m:
            continue
        ts = int(m.group(1)) / 1e9
        spi = [int(x, 16) for x in re.findall(r"mmSPI_CSQ_WF_ACTIVE_COUNT_\d => 0x([0-9a-fA-F]+)", ln)]
        rlc = re.search(r"mmRLC_GPU_CLOCK_COUNT_LSB => 0x([0-9a-fA-F]+) gfx800\.mmRLC_GPU_CLOCK_COUNT_MSB => 0x([0-9a-fA-F]+)", ln)
        grbm = re.search(r"mmGRBM_PERFCOUNTER0_LO => 0x([0-9a-fA-F]+)", ln)
        samples.append({
            "ts": ts,
            "spi": spi,
            "rlc_lsb": int(rlc.group(1), 16) if rlc else None,
            "rlc_msb": int(rlc.group(2), 16) if rlc else None,
            "grbm": int(grbm.group(1), 16) if grbm else None,
        })
    return samples


def steady_window(rows):
    N = len(rows)
    if N < 60:
        return [], None, None
    kept = rows[50:-1]  # descartar primeras ~50 (5s a 10Hz) y última muestra
    mask = steady_mask(kept)
    seg = [kept[i] for i in mask]
    if len(seg) < 100:
        return [], None, None
    t_lo = min(x["ts"] for x in seg)
    t_hi = max(x["ts"] for x in seg)
    return seg, t_lo, t_hi


def stats(vals):
    if not vals:
        return None
    return {"n": len(vals), "avg": round(sum(vals) / len(vals), 2), "max": round(max(vals), 2), "min": round(min(vals), 2)}


def main():
    res = OrderedDict()
    agg = {"A": OrderedDict(), "B": OrderedDict()}

    for run in RUNS:
        d = OrderedDict()
        d["workload"] = WLKIND[run]
        rows = load_telemetry(os.path.join(BASE, run, "telemetria.csv"))
        full_pw = [r["power_uW"] / 1e6 for r in rows]
        d["tele_n"] = len(rows)
        d["power_full"] = stats(full_pw)

        seg, t_lo, t_hi = steady_window(rows)
        if seg:
            pw = [r["power_uW"] / 1e6 for r in seg]
            tmp = [r["temp_mC"] / 1000.0 for r in seg]
            d["power_steady"] = stats(pw)
            d["temp_steady"] = {"n": len(tmp),
                                "avg": round(sum(tmp) / len(tmp), 2),
                                "max": round(max(tmp), 2),
                                "min": round(min(tmp), 2)}
            d["window_s"] = round(t_hi - t_lo, 1)
            d["steady_n"] = len(seg)
            d["gpu_steady"] = stats([r["gpu"] for r in seg])
            d["mem_steady"] = stats([r["mem"] for r in seg])
        else:
            d["power_steady"] = None
            for k in ["temp_steady", "window_s", "steady_n", "gpu_steady", "mem_steady"]:
                d[k] = None

        rt = load_radeontop(os.path.join(BASE, run, "radeontop.csv"))
        if seg and t_lo is not None and t_hi is not None:
            rt_win = [x for x in rt if t_lo <= x["ts"] <= t_hi and x.get("spi") is not None and x["gpu"] >= 95]
            d["rt_n"] = len(rt_win)
            d["rt_blocks"] = {b: stats([x[b] for x in rt_win]) for b in BLOCKS if rt_win}
            d["rt_mclk_ghz"] = stats([x["mclk_ghz"] for x in rt_win]) if rt_win else None
            d["rt_sclk_ghz"] = stats([x["sclk_ghz"] for x in rt_win]) if rt_win else None
            d["rt_mclk_pct"] = stats([x["mclk_pct"] for x in rt_win]) if rt_win else None
            d["rt_sclk_pct"] = stats([x["sclk_pct"] for x in rt_win]) if rt_win else None
        else:
            d["rt_n"] = 0
            d["rt_blocks"] = {}

        umr = load_umr(os.path.join(BASE, run, "umr_samples.csv"))
        d["umr_n"] = len(umr)
        if t_lo is not None and t_hi is not None:
            umr_win = [x for x in umr if t_lo <= x["ts"] <= t_hi]
        else:
            umr_win = umr
        d["umr_win_n"] = len(umr_win)
        if len(umr_win) >= 2:
            spis = [n for x in umr_win for n in x["spi"]]
            d["spi_any_nonzero"] = {"n_total": len(spis), "n_nonzero": sum(1 for v in spis if v > 0),
                                    "pct_nonzero": round(100 * sum(1 for v in spis if v > 0) / len(spis), 2)}
            rlc_ok = [(x["rlc_lsb"], x["rlc_msb"]) for x in umr_win if x["rlc_lsb"] is not None]
            rates = []
            for i in range(1, len(rlc_ok)):
                dt = umr_win[i]["ts"] - umr_win[i - 1]["ts"]
                if dt <= 0:
                    continue
                v = rlc_ok[i][0] + (rlc_ok[i][1] << 32)
                p = rlc_ok[i - 1][0] + (rlc_ok[i - 1][1] << 32)
                dv = (v - p) % (1 << 64)
                rates.append(dv / dt / 1e6)  # MHz de contador RLC
            d["rlc_clock_mhz"] = stats(rates) if rates else None
            if rates:
                sr = sorted(rates)
                d["rlc_clock_mhz"]["median"] = round(sr[len(sr) // 2], 2)
            grbms = [x["grbm"] for x in umr_win if x["grbm"] is not None]
            d["grbm_nonzero_written"] = None if not grbms else (1 if any(g != 0 for g in grbms) else 0)
        else:
            d["spi_any_nonzero"] = None
            d["rlc_clock_mhz"] = None
            d["grbm_nonzero_written"] = None

        res[run] = d

        for key in agg[WLKIND[run]]:
            pass
        # acumulados
        for var in ["power_steady", "temp_steady"]:
            pass

    # agregados simples (media de métricas válidas por réplica)
    aggA = {v: [] for v in ["power_full", "power_steady"]}
    aggB = {v: [] for v in ["power_full", "power_steady"]}
    for run, d in res.items():
        for v in ["power_full", "power_steady"]:
            (aggA if d["workload"] == "A" else aggB)[v].append((d[v] or {}).get("avg"))

    print(json.dumps(res, indent=1))
    print("\nMEDIA power_full W:  A=%s B=%s" % (avg(aggA["power_full"]), avg(aggB["power_full"])))
    print("MEDIA power_steady W:A=%s B=%s" % (avg(aggA["power_steady"]), avg(aggB["power_steady"])))
    ratios = []
    for v in ["power_steady"]:
        for i in range(3):
            a = (res["A%d" % (i + 1)][v] or {}).get("avg")
            b = (res["B%d" % (i + 1)][v] or {}).get("avg")
            if a and b:
                ratios.append(a / b)
    if ratios:
        print("RATIO A/B power_steady por par: %s  media=%.3f" % ([round(x, 3) for x in ratios], ratios[0] if len(ratios) < 3 else sum(ratios) / len(ratios)))
    # ratios por bloque
    print("\nRATIO bloque (A/B) media de promedios steady:")
    for b in BLOCKS:
        av = [((res[r].get("rt_blocks") or {}).get(b) or {}).get("avg") for r in RUNS if res[r]["workload"] == "A"]
        bv = [((res[r].get("rt_blocks") or {}).get(b) or {}).get("avg") for r in RUNS if res[r]["workload"] == "B"]
        av = [x for x in av if x is not None]; bv = [x for x in bv if x is not None]
        if av and bv and sum(bv) / len(bv) > 0:
            print("  %-4s A_avg=%6.2f B_avg=%6.2f ratio=%6.3f" % (b, sum(av) / len(av), sum(bv) / len(bv), (sum(av) / len(av)) / (sum(bv) / len(bv))))
        elif av and bv:
            print("  %-4s A_avg=%6.2f B_avg=%6.2f ratio=inf(B=0)" % (b, sum(av) / len(av), sum(bv) / len(bv)))


def avg(vals):
    vals = [v for v in vals if v is not None]
    return None if not vals else round(sum(vals) / len(vals), 2)


if __name__ == "__main__":
    main()