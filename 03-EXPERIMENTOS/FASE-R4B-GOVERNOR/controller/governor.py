#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""governor.py — Controlador frametime-feedback read-only (EXP-F4-A).

Señal   : p99 frametime por ventana rodante de 20 s (frames del log del harness).
Actuador: render-scale s ∈ {1.00, 0.87, 0.75, 0.62, 0.50}, escrito en control_scale.txt.
Regla (EXP-F4-A-PROTOCOL §10, pre-committed):
  - banda = [0.90·T, 1.10·T]
  - BAJADA: p99_window > 1.10·T durante >=2 ventanas consecutivas -> next_lower(s)
  - SUBIDA: p99_window < 0.90·T durante >=2 ventanas consecutivas (y s<1.00) -> next_higher(s)
  - dentro de banda -> no actuar
  - ventana mínima entre cambios = 40 s (>= 2 ventanas)
READ-ONLY: solo lee el log de frames y escribe control_scale.txt (en results/), nunca sysfs,
nunca contadores, nunca registros.

Ventanas: la ventana k es [t0 + k*20s, t0 + (k+1)*20s), con t0 = ts_us MONOTONIC de m0
(imprimido por el harness en stderr, o derivado de la primera fila del log). El harness
relee control_scale.txt al inicio de cada ventana (+250 ms), por lo que el governor debe
escribir la escala vigente para la ventana k ANTES de que el harness la lea: el governor
cierra la ventana k-1 en t0+k*20s y escribe de inmediato.

Uso:
  governor.py --frames LOG.tsv --control control_scale.txt --t0-us 1234567890123
              --T-ms 5.123 --duration 120 --trace trace.tsv
"""
import argparse
import math
import os
import time

SCALES = [1.00, 0.87, 0.75, 0.62, 0.50]
WINDOW_S = 20.0
WIN_US = int(WINDOW_S * 1e6)


def p99(xs):
    if not xs:
        return None
    s = sorted(xs)
    k = max(1, int(math.ceil(0.99 * len(s))))
    return float(s[k - 1])


def next_lower(s):
    i = SCALES.index(s)
    return SCALES[min(i + 1, len(SCALES) - 1)]


def next_higher(s):
    i = SCALES.index(s)
    return SCALES[max(i - 1, 0)]


def read_frames(path):
    """Devuelve lista de (ts_us_mono, ft_us)."""
    out = []
    try:
        with open(path) as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                p = line.split("\t")
                if len(p) < 4:
                    continue
                try:
                    ts = int(p[1])
                    ft = int(p[2])
                except ValueError:
                    continue
                out.append((ts, ft))
    except FileNotFoundError:
        return out
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--control", required=True)
    ap.add_argument("--t0-us", required=True, type=int,
                    help="ts_us MONOTONIC del instante m0 (inicio de ventana 0)")
    ap.add_argument("--T-ms", required=True, type=float)
    ap.add_argument("--duration", required=True, type=float)
    ap.add_argument("--trace", required=True)
    args = ap.parse_args()

    T = args.T_ms * 1000.0          # µs
    lo = 0.90 * T
    hi = 1.10 * T
    t0 = args.t0_us
    end_us = t0 + int(args.duration * 1e6)

    mono0 = time.monotonic_ns() // 1000   # referencia: mismo CLOCK_MONOTONIC que el harness

    scale = 1.00
    last_change_us = t0 - 10 ** 9   # nunca ha cambiado
    streak_hi = 0
    streak_lo = 0
    w_processed = -1                # última ventana cerrada

    with open(args.trace, "w") as trace:
        trace.write("#win\twb_us\twe_us\tp99_us\tscale\taction\n")

        deadline = time.monotonic() + args.duration + 20.0
        while time.monotonic() < deadline:
            now_us = mono0 + (time.monotonic_ns() // 1000 - mono0)
            k = w_processed + 1
            wb = t0 + k * WIN_US
            we = wb + WIN_US
            if we > end_us:
                break
            if now_us < we + 300000:        # esperar cierre real completo de la ventana
                time.sleep(0.2)
                continue

            frames = read_frames(args.frames)
            win_frames = [ft for (ts, ft) in frames if wb <= ts < we]
            p = p99(win_frames)
            if p is None:
                w_processed = k              # ventana sin frames: no actuar
                continue

            action = "none"
            if p > hi:
                streak_hi += 1
                streak_lo = 0
            elif p < lo:
                streak_lo += 1
                streak_hi = 0
            else:
                streak_hi = 0
                streak_lo = 0

            if (we - last_change_us) >= 40e6:
                if streak_hi >= 2 and scale > SCALES[-1]:
                    scale = next_lower(scale)
                    last_change_us = we
                    streak_hi = 0
                    streak_lo = 0
                    action = "LOWER"
                elif streak_lo >= 2 and scale < SCALES[0]:
                    scale = next_higher(scale)
                    last_change_us = we
                    streak_hi = 0
                    streak_lo = 0
                    action = "RAISE"

            tmp = args.control + ".tmp"
            with open(tmp, "w") as cf:
                cf.write("%.3f\n" % scale)
            os.replace(tmp, args.control)    # escritura atómica

            trace.write("%d\t%d\t%d\t%.1f\t%.3f\t%s\n" % (k, wb, we, p, scale, action))
            trace.flush()
            w_processed = k

    print("governor: done windows=%d final_scale=%.3f" % (w_processed, scale))


if __name__ == "__main__":
    main()