#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""avm1_cfg.py — Simulador de pila con flujo de control (CFG).

Deriva la semantica de los opcodes desconocidos de este
dialecto AVM1 no estandar por **consistencia de profundidad
de pila en puntos de merge** (RXRE-SWF-039).

Metodo (RXRE-SWF-042):
  1. Construir el CFG: bloques basicos partidos en los
     destinos de salto y despues de cada salto.
  2. Propagar la profundidad de pila hacia adelante como
     expresion LINEAL sobre los efectos desconocidos:
         profundidad = constante + sum(coef[c] * efecto[c])
     donde efecto[c] es una variable para cada opcode
     desconocido y un entero conocido para los probados.
  3. En cada punto de merge, las profundidades de todos
     los predecesores DEBEN ser iguales (programa
     bien formado). La diferencia da una ecuacion
     lineal sobre los efectos desconocidos.
  4. Resolver el sistema lineal (aritmetica exacta
     con Fraction) para obtener el efecto neto de cada
     opcode desconocido.

Codificacion de salto PROBADA (RXRE-SWF-042):
  0x99 = salto incondicional (un solo sucesor: destino)
  0x9D = branch condicional (dos sucesores: destino +
         caida)
  destino = pos_campo_offset + 2 + int16_con_signo
  (confirmado: 7053/7053 saltos caen en limites de
  instruccion).

Efectos de pila PROBADOS (RXRE-SWF-028/029):
  0x4E GetMember:  pop2 push1  => neto -1
  0x4F SetMember:  pop3 push0  => neto -3
y los cortos estandar (RXRE-SWF-024):
  0x0A/0x0B/0x0C/0x0D: pop2 push1 => -1
  0x12 Not:  pop1 push1 => 0
  0x17 Pop:  pop1 => -1
  0x1C GetVariable: pop1 push1 => 0
  0x1D SetVariable: pop2 => -2
  0x07 Stop: => 0
  0x96 Push: => +N (N = # constantes, concreto)

Los demas opcodes (0x52, 0x87, 0x67, 0x88, 0x9B, 0x8E,
0x3D, 0x3E, 0x40, 0x42, 0x47, 0x48, 0x49, 0x4C, 0x50,
0x51, ...) se RESUELVEN por el solver.
"""
import struct
import sys
from fractions import Fraction

import avm1_disasm as A

# ---- Efectos de pila PROBADOS (neto: push - pop) ----
KNOWN_EFFECT = {
    0x07: 0,    # Stop
    0x0A: -1,   # Add
    0x0B: -1,   # Subtract
    0x0C: -1,   # Multiply
    0x0D: -1,   # Divide
    0x12: 0,    # Not
    0x17: -1,   # Pop
    0x1C: 0,    # GetVariable
    0x1D: -2,   # SetVariable
    0x4E: -1,   # GetMember  (RXRE-SWF-028)
    0x4F: -3,   # SetMember  (RXRE-SWF-029)
}

# Directivas (sin efecto de pila): se resuelven como 0 pero
# se incluyen en el sistema para CONFIRMARLO.
DIRECTIVES = {0x88, 0x9B, 0x8E}

# Saltos (efecto de pila por resolver: 0x9D consume la
# condicion? se resuelve)
JUMPS = {0x99, 0x9D}


def push_count(data):
    """# de constantes que apila un Push(0x96)."""
    n = 0
    i = 0
    L = len(data)
    while i < L:
        t = data[i]
        i += 1
        if t == 0:      # String
            j = data.find(b"\x00", i)
            if j < 0:
                j = L
            i = j + 1
        elif t == 1:    # Float32
            i += 4
        elif t in (2, 3):   # Null / Undefined
            pass
        elif t == 4:    # Register
            i += 1
        elif t == 5:    # Boolean
            i += 1
        elif t == 6:    # float32 + uint32
            i += 8
        elif t == 7:    # Integer
            i += 4
        elif t == 8:    # Lookup
            i += 1
        elif t == 9:    # Const16
            i += 2
        else:
            # tipo desconocido: no se puede contar con
            # precision; tratar como fin
            return n
        n += 1
    return n


def jump_target(script_off, doff, body):
    """Destino de salto PROBADO: drel + 2 + int16 signo."""
    raw = struct.unpack("<H", body[doff:doff + 2])[0]
    val = raw if raw < 32768 else raw - 65536
    return (doff - script_off) + 2 + val


# ---- Expresion lineal: const + sum(coeff[code]*efecto[code]) ----
class Linear:
    __slots__ = ("const", "coeffs")

    def __init__(self):
        self.const = Fraction(0)
        self.coeffs = {}

    def copy(self):
        l = Linear()
        l.const = self.const
        l.coeffs = dict(self.coeffs)
        return l

    def __eq__(self, other):
        return (self.const == other.const
                and self.coeffs == other.coeffs)

    def __repr__(self):
        parts = [str(self.const)]
        for c in sorted(self.coeffs):
            k = self.coeffs[c]
            if k == 0:
                continue
            parts.append("%+d*e[0x%02x]" % (k, c))
        return " ".join(parts)

    def sub(self, other):
        """self - other (para ecuaciones de merge)."""
        r = Linear()
        r.const = self.const - other.const
        keys = set(self.coeffs) | set(other.coeffs)
        for c in keys:
            d = self.coeffs.get(c, 0) - other.coeffs.get(c, 0)
            if d != 0:
                r.coeffs[c] = d
        return r


def apply_effect(lin, code, data, body):
    """Aplica el efecto de un opcode a la expresion.
    Solo 0x99 (salto incondicional) tiene efecto 0
    seguro.  Todo lo demas que no sea PROBADO o Push
    es una VARIABLE a resolver (incluye 0x9D, que
    probablemente consume la condicion, y las
    directivas 0x88/0x9B/0x8E, que se confirman)."""
    if code in KNOWN_EFFECT:
        lin.const += KNOWN_EFFECT[code]
    elif code == 0x96:
        lin.const += push_count(data)
    elif code == 0x99:
        pass                       # salto incondicional: 0
    else:
        # variable a resolver
        lin.coeffs[code] = lin.coeffs.get(code, 0) + 1


# ---- Construccion del CFG ----
def build_cfg(actions, script_off, body):
    """Devuelve (bloques, edges).
    bloques: lista de (inicio, [acciones]).
    edges: dict inicio -> [sucesores]."""
    # 1. Lideres: inicio, destinos de salto, caida de saltos
    leaders = {0}
    for code, doff, dlen in actions:
        drel = doff - script_off
        if code in JUMPS and dlen == 2:
            tgt = jump_target(script_off, doff, body)
            if tgt >= 0:
                leaders.add(tgt)
            leaders.add(drel + 2)     # caida
    leaders = sorted(l for l in leaders if l >= 0)

    # 2. Bloques: [leaders[i], leaders[i+1])
    pos_to_idx = {}
    for i, (code, doff, dlen) in enumerate(actions):
        drel = doff - script_off
        istart = drel - (3 if code >= 0x80 else 1)
        pos_to_idx[istart] = i

    blocks = []
    for bi in range(len(leaders)):
        start = leaders[bi]
        end = leaders[bi + 1] if bi + 1 < len(leaders) else None
        idx = pos_to_idx.get(start)
        if idx is None:
            continue
        block_actions = []
        for j in range(idx, len(actions)):
            code, doff, dlen = actions[j]
            drel = doff - script_off
            istart = drel - (3 if code >= 0x80 else 1)
            if end is not None and istart >= end:
                break
            block_actions.append((code, doff, dlen, istart))
        if block_actions:
            blocks.append((start, block_actions))

    # 3. Edges: el destino se calcula DESDE la ultima
    #    accion del bloque (no por el inicio del bloque)
    edges = {}
    block_starts = [b[0] for b in blocks]
    for bi, (start, acts) in enumerate(blocks):
        last_code, last_doff, last_dlen, _ = acts[-1]
        next_start = (block_starts[bi + 1]
                      if bi + 1 < len(block_starts) else None)
        succ = []
        if last_code == 0x99:
            # incondicional: solo destino
            tgt = jump_target(script_off, last_doff, body)
            if tgt in block_starts:
                succ.append(tgt)
        elif last_code == 0x9D:
            # condicional: destino + caida
            tgt = jump_target(script_off, last_doff, body)
            if tgt in block_starts:
                succ.append(tgt)
            if next_start is not None:
                succ.append(next_start)
        else:
            if next_start is not None:
                succ.append(next_start)
        edges[start] = succ
    return blocks, edges


# ---- Propagacion hacia adelante con ecuaciones de merge ----
def forward_solve(actions, script_off, body):
    """Devuelve (ecuaciones, bloques, edges)."""
    blocks, edges = build_cfg(actions, script_off, body)
    block_starts = [b[0] for b in blocks]
    bmap = {s: (s, acts) for s, acts in blocks}

    in_depth = {s: None for s in block_starts}
    entry = block_starts[0]
    in_depth[entry] = Linear()

    equations = []     # (Linear, )  == 0
    worklist = [entry]
    seen = set()

    while worklist:
        start = worklist.pop(0)
        if start in seen:
            continue
        seen.add(start)
        din = in_depth[start]
        if din is None:
            continue
        _, acts = bmap[start]
        dout = din.copy()
        for code, doff, dlen, istart in acts:
            data = body[doff:doff + dlen] if dlen > 0 else b""
            if code in JUMPS:
                # el salto es la ultera instruccion; su
                # efecto se aplica (0 por defecto, resolver)
                apply_effect(dout, code, data, body)
                break
            apply_effect(dout, code, data, body)
        for succ in edges.get(start, []):
            if in_depth[succ] is None:
                in_depth[succ] = dout.copy()
                if succ not in seen:
                    worklist.append(succ)
            else:
                # merge: las profundidades deben ser iguales
                diff = in_depth[succ].sub(dout)
                if diff.const != 0 or diff.coeffs:
                    equations.append(diff)

    # Resolver el sistema lineal
    return equations, blocks, edges


def solve_linear(equations):
    """Resuelve A*x = -b con aritmetica exacta.

    Devuelve (unicos, libres, inconsistentes, sospechosos):
      unicos: {code: efecto} determinados univocamente
      libres: set de codes NO determinados
      inconsistentes: # filas [0...0|c] con c!=0
      sospechosos: {code: #} opcodes implicados en
                   combinaciones inconsistentes
                   (candidatos a efecto dependiente
                   del valor, p.ej. CallMethod)
    """
    vars_ = set()
    for eq in equations:
        vars_ |= set(eq.coeffs.keys())
    vars_ = sorted(vars_)
    vidx = {c: i for i, c in enumerate(vars_)}
    n = len(vars_)
    m = len(equations)
    if n == 0:
        return {}, set(), 0, {}
    # cada fila: coeficientes + termino + fuente
    # (indices de ecuaciones originales que combina)
    M = [[Fraction(0)] * (n + 1) for _ in range(m)]
    src = [set() for _ in range(m)]
    for r, eq in enumerate(equations):
        for c, k in eq.coeffs.items():
            M[r][vidx[c]] = Fraction(k)
        M[r][n] = Fraction(-eq.const)
        src[r] = {r}
    # eliminacion Gauss-Jordan
    piv_row = 0
    pivots = {}
    for col in range(n):
        sel = None
        for r in range(piv_row, m):
            if M[r][col] != 0:
                sel = r
                break
        if sel is None:
            continue
        M[piv_row], M[sel] = M[sel], M[piv_row]
        src[piv_row], src[sel] = src[sel], src[piv_row]
        pv = M[piv_row][col]
        for j in range(col, n + 1):
            M[piv_row][j] /= pv
        for r in range(m):
            if r != piv_row and M[r][col] != 0:
                f = M[r][col]
                for j in range(col, n + 1):
                    M[r][j] -= f * M[piv_row][j]
                src[r] = src[r] | src[piv_row]
        pivots[col] = piv_row
        piv_row += 1
    # inconsistencias: fila [0...0 | c!=0]
    inconsistentes = 0
    inc_src = set()
    for r in range(m):
        if all(M[r][c] == 0 for c in range(n)) and M[r][n] != 0:
            inconsistentes += 1
            inc_src |= src[r]
    # opcodes implicados en ecuaciones inconsistentes
    sospechosos = {}
    for ir in inc_src:
        for c in equations[ir].coeffs:
            sospechosos[c] = sospechosos.get(c, 0) + 1
    # columnas libres = no pivoteadas
    pivot_cols = set(pivots.keys())
    free_cols = [c for c in range(n) if c not in pivot_cols]
    unicos = {}
    libres = set()
    for col, r in pivots.items():
        depende = any(M[r][fc] != 0 for fc in free_cols)
        if depende:
            libres.add(vars_[col])
        else:
            val = M[r][n]
            unicos[vars_[col]] = int(val) if val.denominator == 1 else val
    for fc in free_cols:
        libres.add(vars_[fc])
    return unicos, libres, inconsistentes, sospechosos


def analyze_swf(swf_path):
    import zlib
    data = open(swf_path, "rb").read()
    body = zlib.decompress(data[8:])
    nbits = body[0] >> 3
    off = (5 + 4 * nbits + 7) // 8 + 4
    scripts = A.collect_scripts(body, off, len(body))
    return body, scripts


def per_script_consensus(body, scripts):
    """Resuelve cada script por separado y agrega
    el consenso.  Devuelve (determinado, debil,
    no_determinado, n_consistentes, n_inconsistentes).

    Un efecto es DETERMINADO si es UNANIME (entero)
    en >=2 scripts.  DEBIL si es UNANIME en 1 script.
    NO_DETERMINADO si hay discordancia o es fraccion
    (un efecto de pila es siempre entero)."""
    determined = {}   # code -> effect (unanimous, >=2)
    debil = {}        # code -> effect (unanimous, 1)
    no_det = set()    # codes con discordancia/fraccion
    dist = {}         # code -> {effect: count}
    n_cons = 0
    n_inc = 0
    for s in scripts:
        if s["length"] <= 0:
            continue
        actions, _, _ = A.walk_actions(
            body, s["offset"], s["offset"] + s["length"])
        equations, blocks, edges = forward_solve(
            actions, s["offset"], body)
        if not equations:
            continue
        unicos, libres, inconsistentes, sos = \
            solve_linear(equations)
        if inconsistentes:
            n_inc += 1
            continue
        n_cons += 1
        for code, e in unicos.items():
            # un efecto de pila es siempre entero;
            # una determinacion fraccionaria es
            # espuria (script consistente pero
            # subdeterminado: el solver eligio un
            # valor no entero imposible).  Ignorarla.
            if not isinstance(e, int):
                continue
            dist.setdefault(code, {})
            dist[code][e] = dist[code].get(e, 0) + 1
    for code, counter in dist.items():
        total = sum(counter.values())
        effect, count = max(counter.items(),
                            key=lambda kv: kv[1])
        # efecto de pila siempre entero: rechazar
        # fracciones (determinacion espuria)
        if not isinstance(effect, int):
            no_det.add(code)
            continue
        if count == total and total >= 2:
            determined[code] = effect
        elif count == total and total == 1:
            debil[code] = effect
        else:
            no_det.add(code)
    return (determined, debil, no_det,
            n_cons, n_inc, dist)


def _validation_0x4e(body, scripts):
    """Auto-test: 0x4E (GetMember) debe dar -1."""
    saved = KNOWN_EFFECT.pop(0x4E)
    hits = 0
    tries = 0
    dist = {}
    for s in scripts:
        if s["length"] <= 0:
            continue
        actions, _, _ = A.walk_actions(
            body, s["offset"], s["offset"] + s["length"])
        equations, _, _ = forward_solve(
            actions, s["offset"], body)
        if not equations:
            continue
        unicos, _, inconsistentes, _ = solve_linear(
            equations)
        if inconsistentes:
            continue
        if 0x4E in unicos:
            tries += 1
            e = unicos[0x4E]
            dist[e] = dist.get(e, 0) + 1
            if e == -1:
                hits += 1
    KNOWN_EFFECT[0x4E] = saved
    return hits, tries, dist


def main(swf_path):
    body, scripts = analyze_swf(swf_path)
    (determined, debil, no_det,
     n_cons, n_inc, dist) = per_script_consensus(
        body, scripts)

    print("=== Simulador de pila con CFG (RXRE-SWF-042) ===")
    print("metodo: resolver cada script por separado")
    print("        (consenso entre scripts consistentes)")
    print()
    print("=== Auto-test: 0x4E=GetMember (esperado -1) ===")
    hits, tries, vdist = _validation_0x4e(body, scripts)
    print("  recuperado -1 en %d/%d scripts" % (hits, tries))
    print("  distribucion:", dict(vdist))
    print("  => metodo %s" % (
        "VALIDADO" if hits >= tries * 0.9 else "FALLO"))
    print()
    print("scripts consistentes: %d, inconsistentes: %d"
          % (n_cons, n_inc))
    print()
    print("=== Efectos DETERMINADOS (unanimos, >=2) ===")
    for code in sorted(determined):
        e = determined[code]
        interp = _interp(e)
        print("  0x%02x  neto = %-4s %s  (%d scripts)"
              % (code, e, interp,
                 dist[code][e]))
    print()
    print("=== DEBIL (unanimo, 1 script; requiere")
    print("           corroboracion) ===")
    for code in sorted(debil):
        e = debil[code]
        interp = _interp(e)
        print("  0x%02x  neto = %-4s %s  (1 script)"
              % (code, e, interp))
    print()
    print("=== NO DETERMINADO (discordancia/valor-")
    print("      dependiente/fraccion) ===")
    for code in sorted(no_det):
        print("  0x%02x  NOT_DETERMINED  %s"
              % (code, dict(dist[code])))
    return determined, debil, no_det


def _interp(e):
    if e == 0:
        return "(sin efecto de pila)"
    if e == -1:
        return "(pop1 neto)"
    if e == -2:
        return "(pop2 neto)"
    if e == 1:
        return "(push1 neto)"
    if e > 1:
        return "(push%d neto)" % e
    return "(pop%d neto)" % (-e)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else \
        "raw/original.swf"
    main(path)
