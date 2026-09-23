#!/usr/bin/env python3
"""compare.py — yune ground-truth (GT) con lo recuperado por la layer y calcula metricas.

Uso: compare.py --gt GT.json --rec REC.lines --out OUT.json [--tol 0.01]

El archivo REC es el log de la layer: cada linea "<marker> <jx> <jy>".
El marker == frame index del harness (mismo indice global que la GT).
Los frames prelude (marker<jg_prelude) se excluyen de las metricas.
"""
import argparse
import json
import math

def pearson(x, y):
    n = len(x)
    if n < 2:
        return float("nan")
    mx, my = sum(x)/n, sum(y)/n
    num = sum((a-mx)*(b-my) for a, b in zip(x, y))
    dx = math.sqrt(sum((a-mx)**2 for a in x))
    dy = math.sqrt(sum((b-my)**2 for b in y))
    if dx == 0 or dy == 0:
        return float("nan")
    return num/(dx*dy)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt", required=True)
    ap.add_argument("--rec", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tol", type=float, default=0.01)
    args = ap.parse_args()

    gt = json.load(open(args.gt))
    gt_frames = gt["frames"]
    prelude = gt.get("prelude", 0)

    rec = {}
    for line in open(args.rec):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            m, jx, jy = line.split()
        except ValueError:
            continue
        rec[int(float(m))] = (float(jx), float(jy))

    pairs = []
    missing = []
    for f in gt_frames:
        if f["prelude"]:
            continue
        if f["frame"] in rec:
            pairs.append((f, rec[f["frame"]]))
        else:
            missing.append(f["frame"])

    errx, erry = [], []
    for f, (rjx, rjy) in pairs:
        errx.append(rjx - f["jx"])
        erry.append(rjy - f["jy"])

    n = len(pairs)
    res = {
        "n_frames_measured": n,
        "n_missing_in_rec": len(missing),
        "missing_frames": missing[:20],
        "tol_px": args.tol,
        "mae_x": (sum(abs(e) for e in errx)/n) if n else float("nan"),
        "mae_y": (sum(abs(e) for e in erry)/n) if n else float("nan"),
        "mae_total": (sum(math.hypot(ex, ey) for ex, ey in zip(errx, erry))/n) if n else float("nan"),
        "rms_x": math.sqrt(sum(e*e for e in errx)/n) if n else float("nan"),
        "rms_y": math.sqrt(sum(e*e for e in erry)/n) if n else float("nan"),
        "max_err": max((math.hypot(ex, ey) for ex, ey in zip(errx, erry)), default=float("nan")),
        "max_err_x": max((abs(e) for e in errx), default=float("nan")),
        "max_err_y": max((abs(e) for e in erry), default=float("nan")),
        "frames_correct": sum(1 for ex, ey in zip(errx, erry) if math.hypot(ex, ey) < args.tol),
        "frames_incorrect": sum(1 for ex, ey in zip(errx, erry) if math.hypot(ex, ey) >= args.tol),
        "frac_correct": (sum(1 for ex, ey in zip(errx, erry) if math.hypot(ex, ey) < args.tol)/n) if n else float("nan"),
        "pearson_jx": pearson([f["jx"] for f, _ in pairs], [rjx for _, (rjx, _) in pairs]),
        "pearson_jy": pearson([f["jy"] for f, _ in pairs], [rjy for _, (_, rjy) in pairs]),
    }
    # outliers (top 5 por error total)
    ranked = sorted(pairs, key=lambda p: math.hypot(p[1][0]-p[0]["jx"], p[1][1]-p[0]["jy"]), reverse=True)[:5]
    res["top5_outliers"] = [
        {"frame": f["frame"], "gt": [f["jx"], f["jy"]], "rec": [rjx, rjy],
         "err_px": round(math.hypot(rjx-f["jx"], rjy-f["jy"]), 9)}
        for f, (rjx, rjy) in ranked
    ]

    with open(args.out, "w") as f:
        json.dump(res, f, indent=2)

    print(f"frames={n} missing={len(missing)} tol={args.tol}")
    print(f"MAE_X={res['mae_x']:.6f} MAE_Y={res['mae_y']:.6f} MAE_total={res['mae_total']:.6f}")
    print(f"RMS_X={res['rms_x']:.6f} RMS_Y={res['rms_y']:.6f} MAX={res['max_err']:.6f}")
    print(f"correct={res['frames_correct']}/{n} ({(100*res['frac_correct'] if n else float('nan')):.2f}%)")
    print(f"pearson jx={res['pearson_jx']:.6f} jy={res['pearson_jy']:.6f}")

if __name__ == "__main__":
    main()