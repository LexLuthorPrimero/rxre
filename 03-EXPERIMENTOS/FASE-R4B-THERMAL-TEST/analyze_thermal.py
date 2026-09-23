#!/usr/bin/env python3
"""analyze_thermal.py — análisis read-only del TEST TÉRMICO (EXP-F4-A / R-4B).
Entrada: runs/repREP/telemetry.csv (10 Hz) + timings.txt. Salida: curvas resumidas + métricas A–J.
No toca sysfs; solo lee los CSV ya adquiridos. Uso: analyze_thermal.py [--all]"""
import os, sys, json, math, statistics

BASE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(BASE, "runs")

def parse_telemetry(path):
    rows = []
    with open(path) as f:
        for l in f:
            if l.startswith("ts_ns") or not l.strip():
                continue
            c = l.rstrip("\n").split(";")
            if len(c) < 11:
                continue
            try:
                ts = int(c[0]); pwr = int(c[1]); tmp = int(c[2])
                busy = int(c[3]); mb = int(c[4]); vram = int(c[5]); gtt = int(c[6])
                sclk_lvl = c[7]; sclk = c[8]; mclk_lvl = c[9]; mclk = c[10]
            except ValueError:
                continue
            def num(x, dflt):
                try: return int(x)
                except ValueError: return dflt
            rows.append(dict(ts=ts, pwr=pwr, tmp=tmp, busy=busy, mb=mb, vram=vram, gtt=gtt,
                             sclk_lvl=num(sclk_lvl, -1), sclk=num(sclk, 0),
                             mclk_lvl=num(mclk_lvl, -1), mclk=num(mclk, 0)))
    return rows

def main():
    allrep = []
    for rep in ("rep1", "rep2"):
        d = os.path.join(RUNS, rep)
        if not os.path.isdir(d):
            print(f"[{rep}] NO EXISTE — omitida"); continue
        tel = os.path.join(d, "telemetry.csv")
        tim = os.path.join(d, "timings.txt")
        if not os.path.exists(tel):
            print(f"[{rep}] sin telemetry.csv"); continue
        rows = parse_telemetry(tel)
        if not rows:
            print(f"[{rep}] telemetry vacía"); continue
        t_t0 = rows[0]["ts"] / 1e9
        # referencia: inicio/fin de carga (epoch s) desde timings.txt
        load_start = load_end = cond = None
        if os.path.exists(tim):
            for l in open(tim):
                k, _, v = l.partition("=")
                if k == "t_load_start": load_start = float(v.strip())
                elif k == "t_load_end": load_end = float(v.strip())
                elif k == "t_cond": cond = float(v.strip())
        # métricas
        tmp0 = statistics.mean(r["tmp"] / 1000 for r in rows[:5])
        sclk0 = rows[0]["sclk"]; lvl0 = rows[0]["sclk_lvl"]
        t92 = None; t97 = None; t_degrade_sclk = None; t_degrade_temp = None; tmax = None
        deg_start = deg_start_i = None
        for i, r in enumerate(rows):
            t = (r["ts"] / 1e9) - t_t0
            if tmax is None or r["tmp"] > tmax[0]:
                tmax = (r["tmp"], r["tmp"] / 1000, t)
            if t92 is None and r["tmp"] >= 92000: t92 = t
            if t97 is None and r["tmp"] >= 97000: t97 = t
            # degradación sostenida: sclk < 1071 durante >=10 muestras consecutivas con busy>=95
            if deg_start is None:
                if r["sclk"] < 1071 and r["busy"] >= 95:
                    n = 0
                    for j in range(i, min(i + 10, len(rows))):
                        if rows[j]["sclk"] < 1071 and rows[j]["busy"] >= 95:
                            n += 1
                        else:
                            break
                    if n >= 10:
                        deg_start = (i, rows[i]["tmp"], t)
        if deg_start:
            t_degrade_sclk = deg_start[2]; t_degrade_temp = deg_start[1] / 1000
        # recuperación: cooldown = fin carga → condición
        recovery = None
        if load_end and cond:
            recovery = cond - load_end
        # temp/sclk/power al final (últimas 10 muestras)
        tail = rows[-10:]
        tmp_end = statistics.mean(r["tmp"] / 1000 for r in tail)
        sclk_end = tail[-1]["sclk"]; lvl_end = tail[-1]["sclk_lvl"]
        pwr_end = statistics.mean(r["pwr"] / 1e6 for r in tail)
        pwr_load = statistics.mean(r["pwr"] / 1e6 for r in rows if r["busy"] >= 95)
        # tiempo hasta 92 C y hasta 90 C
        t90 = None
        for r in rows:
            if t90 is None and r["tmp"] >= 90000:
                t90 = (r["ts"] / 1e9) - t_t0
        res = dict(rep=rep, temp0=round(tmp0, 1), sclk0=sclk0, lvl0=lvl0,
                   t90=round(t90, 1) if t90 else None, t92=round(t92, 1) if t92 else None,
                   t97=round(t97, 1) if t97 else None,
                   t_degrade=(round(t_degrade_sclk, 1), round(t_degrade_temp, 1)) if deg_start else None,
                   tmax=round(tmax[1], 1) if tmax else None,
                   recovery=round(recovery, 1) if recovery else None,
                   tmp_end=round(tmp_end, 1), sclk_end=sclk_end, lvl_end=lvl_end,
                   pwr_load=round(pwr_load, 2), pwr_end=round(pwr_end, 2),
                   n=len(rows), load_start=load_start, load_end=load_end, cond=cond)
        allrep.append(res)
        print(json.dumps(res, ensure_ascii=False))
    # reproducibilidad (J)
    if len(allrep) == 2:
        a, b = allrep
        def dv(x):
            if a.get(x) is None or b.get(x) is None: return None
            return abs(a[x] - b[x])
        print("--- J reproducibilidad REP1 vs REP2 ---")
        for k in ("t90", "t92", "recovery", "temp0", "tmp_end"):
            d = dv(k)
            print(f"  Δ{k}: {d if d is not None else 'N/A'}")
        if a.get("t_degrade") and b.get("t_degrade"):
            print(f"  Δt_degrade: {abs(a['t_degrade'][0]-b['t_degrade'][0])} s | ΔT_degrade: {abs(a['t_degrade'][1]-b['t_degrade'][1]):.1f} C")

if __name__ == "__main__":
    main()