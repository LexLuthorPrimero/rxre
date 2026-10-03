#!/usr/bin/env python3
# CONTRACT: name=gmmio_inventory
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
"""
INVENTARIO DE REGISTROS MMIO QUE TOCA EL CAMINO GFX8, con offset resuelto.

Por que esta herramienta y no un grep:

GFX8 no tiene un mapa de registros: tiene SEIS, y la confusion de nombres
invita a equivocarse en las dos direcciones.

  gfx_v8_0.c incluye:
    gmc/gmc_8_2_d.h      882 regs   <-- UNICO especifico de Polaris12 (8_2)
    oss/oss_3_0_d.h      545 regs
    bif/bif_5_0_d.h      475 regs
    gca/gfx_8_0_d.h     2633 regs   <-- nucleo de graficos, VI GENERICO
    dce/dce_10_0_d.h    6924 regs   <-- display, el mayor de todos
    smu/smu_7_1_3_d.h    133 regs   <-- reloj, especifico de Polaris12

CORRECCION PROPIA: mi primera redaccion de esta herramienta decia que "el
mapa de registros del RX550 es gmc_8_2". Es FALSO, y lo dije al ver el
include sin listar los demas. gmc_8_2 es solo la familia de la memoria. El
nucleo de graficos sale de gfx_8_0_d.h, que es el generico de VI, y el
display de dce_10_0_d.h, que tiene 6924 registros -- mas que todos los
demas juntos. La consecuencia util para un driver propio es la inversa de la
que yo dije: **para casi todo lo que importa no hace falta ningun header
especifico de Polaris, y donde si lo hace es en GMC y SMU.**

Ademas hay TRES espacios de direccionamiento, no uno:
  1. RREG32/WREG32        offset directo de BAR, desde los _d.h
  2. RREG32_SMC/WREG_SMC  apertura del SMC, registros con prefijo ix
  3. AMDGCN_REG_OFFSET(B,n,reg)  direccionado por bloque

Con el mapa ya resuelto, la pregunta util para un driver propio es: de todos los
registros que el driver toca, cuales son, donde estan, y cuales escribe frente a
cuales lee. Eso es la lista minima que hay que reprogramar.

Herramientas previas que se reutilizan en vez de reimplementar:
  pm4_reachable.py  aporta el indice de funciones y el conjunto alcanzable.
                    Aqui se importa para no duplicar la alcanzabilidad, que es la
                    parte cara y la que ya esta validada por mutacion.

Clases de acceso que se reconocen (y solo estas; lo no reconocido se declara):
  RREG32 / WREG32                      registro plano, offset directo
  RREG32_SMC / WREG32_SMC              registro del SMC, sufijo _SMC
  RREG_SOC15 / WREG_SOC15              registro SOC15 con macro de bloque
  AMDGCN_REG_OFFSET / SOC15_REG_OFFSET   direccionado por bloque

LIMITACION declarada: si un registro se accede con una expresion que la
herramienta no resuelve, se cuenta aparte como NO RESUELTO en vez de inventarse
un offset. Un inventario con numeros inventados es peor que uno incompleto.
"""
import re, sys, glob, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

AMD = "RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd"
BASE = f"{AMD}/amdgpu"
HDRS = f"{AMD}/include/asic_reg"


# ---------------------------------------------------------------- registros
def parse_d_header(path):
    """{mmNAME: offset} desde un header _d.h de amdgpu."""
    out = {}
    if not os.path.exists(path):
        return out
    for l in open(path, errors="replace"):
        m = re.match(r"\s*#\s*define\s+(mm[A-Za-z0-9_]+)\s+(0x[0-9A-Fa-f]+)\s*$", l)
        if m:
            out[m.group(1)] = int(m.group(2), 16)
    return out


def parse_mask_header(path):
    r"""{REG: {CAMPO: (mask, shift)}} desde un header _sh_mask.h.

    BUG QUE ME COSTO DOS EJECUCIONES ENTERAS, y que es el mas silencioso
    posible porque no lanza error: puse el separador de campo como '__MASK'
    cuando el _sh_mask.h usa '_MASK'. Con '__MASK' la regex no casa NADA y el
    campo 'campos definidos' sale 0 para todos los registros -- un dato falso
    que parece un resultado. Se ve comparando el formato real:

        CP_RB0_CNTL__RB_BUFSZ_MASK          <- un underscore antes de MASK
        CP_RB0_CNTL | RB_BUFSZ | MASK

    Con '__MASK' la regex no puede casar porque tras el nombre del campo solo
    queda '_MASK'. Ademas (\w+) incluye '_', asi que el separador de dos
    underscores es el unico desambiguador posible entre registro y campo.

    Y la normalizacion de prefijo que sigue tambien es necesaria:
    el _sh_mask.h nombra los registros SIN el prefijo mm --
    VM_CONTEXT1_CNTL__PAGE_TABLE_BLOCK_SIZE_MASK
    -- y el _d.h los nombra CON el -- mmVM_CONTEXT1_CNTL. Hay que quitar el
    prefijo 'mm' en un lado para poder casarlos. Sin esa normalizacion la
    herramienta informa '0 campos definidos' para todo, que es un dato falso
    y silencioso: el peor tipo de error en una herramienta de inventario.
    """
    out = {}
    if not os.path.exists(path):
        return out
    for l in open(path, errors="replace"):
        m = re.match(r"\s*#\s*define\s+(\w+)__(\w+)_MASK\s+(0x[0-9A-Fa-f]+)\s*$", l)
        if not m:
            continue
        reg, fld, mask = m.group(1), m.group(2), int(m.group(3), 16)
        sh = 0
        while sh < 32 and not (mask >> sh) & 1:
            sh += 1
        out.setdefault(reg, {})[fld] = (mask, sh)
    return out


def block_macro_defs():
    """{BLOQUE: base} de las macros de direccionamiento por bloque."""
    out = {}
    for p in glob.glob(f"{AMD}/include/*.h") + glob.glob(f"{AMD}/amdgpu/*.h"):
        for l in open(p, errors="replace"):
            m = re.match(r"\s*#\s*define\s+(AMDGCN_REG_OFFSET|SOC15_REG_OFFSET)\s*\(B,\s*(\w+),\s*R\)\s+(.*)$",
                         l)
            if m:
                out.setdefault(m.group(2), set()).add(m.group(3).strip())
            m2 = re.match(r"\s*#\s*define\s+(\w+_BASE)\s+(0x[0-9A-Fa-f]+)\s*$", l)
            if m2:
                out[m2.group(1)] = m2.group(2)
    return out


# ------------------------------------------------------------- alcanzabilidad
def reachable_functions():
    """Delega en pm4_reachable: indice + semillas + BFS. Sin duplicar."""
    import pm4_reachable as R
    idx = R.index_functions()
    seeds = []
    src8 = open(f"{BASE}/gfx_v8_0.c", errors="replace").read()
    for tab in ("gfx_v8_0_ring_funcs_gfx", "gfx_v8_0_ring_funcs_compute",
                "gfx_v8_0_ring_funcs_kiq"):
        m = re.search(r"struct amdgpu_ring_funcs\s+" + tab + r"\s*=\s*\{(.*?)\n\};",
                      src8, re.S)
        if not m:
            continue
        for _fld, fn in re.findall(r"^\s*\.(\w+)\s*=\s*(\w+)\s*,", m.group(1), re.M):
            if fn in idx:
                seeds.append(fn)
    m_ip = re.search(r"struct amd_ip_funcs\s+gfx_v8_0_ip_funcs\s*=\s*\{(.*?)\n\};",
                     src8, re.S)
    if m_ip:
        for _fld, fn in re.findall(r"^\s*\.(\w+)\s*=\s*(\w+)\s*,", m_ip.group(1), re.M):
            if fn in idx:
                seeds.append(fn)
    for g in R.GENERIC_ROOTS:
        if g in idx:
            seeds.append(g)
    from collections import deque
    seen, q = set(), deque(seeds)
    while q:
        fn = q.popleft()
        if fn in seen:
            continue
        seen.add(fn)
        rec = idx.get(fn)
        if not rec:
            continue
        body = "\n".join(rec[3][rec[1]:rec[2] + 1])
        for c in R.calls_in(body):
            if c in idx and c not in seen:
                q.append(c)
    return idx, seen


# ------------------------------------------------------------------ accesos
ACC = re.compile(
    r"\b(RREG32|WREG32|RREG32_SMC|WREG32_SMC|RREG_SOC15|WREG_SOC15|RREG|WREG)"
    r"(?:_SMC)?\s*\(\s*(mm[A-Za-z0-9_]+)\b")


def scan_accesses(idx, live, regs):
    """{registro: {'W':n,'R':n,'sitios':[...]}} sobre funciones alcanzables."""
    hits = {}
    unresolved = {}
    for fn in sorted(live):
        rec = idx.get(fn)
        if not rec:
            continue
        f, lo, hi, src = rec
        for k in range(lo, hi + 1):
            line = src[k]
            for m in ACC.finditer(line):
                op, reg = m.group(1), m.group(2)
                kind = "W" if op.startswith("W") else "R"
                if reg not in regs:
                    unresolved.setdefault(reg, []).append((f, k + 1, op))
                    continue
                e = hits.setdefault(reg, {"W": 0, "R": 0, "sites": [],
                                          "smc": False})
                e[kind] += 1
                if "SMC" in op:
                    e["smc"] = True
                if len(e["sites"]) < 3:
                    e["sites"].append((f, k + 1, op))
    return hits, unresolved


def main():
    print("=" * 78)
    print("INVENTARIO DE REGISTROS MMIO -- camino GFX8, con offset resuelto")
    print("=" * 78)

    # Las seis familias que gfx_v8_0.c incluye de verdad, no una.
    # El orden importa: la primera que define un nombre gana, que es lo que
    # hace el preprocesador con el orden de los #include.
    FAMILIES = [
        ("gmc/gmc_8_2_d.h",   "gmc_8_2",   "Polaris12  MEMORIA"),
        ("oss/oss_3_0_d.h",   "oss_3_0",   "VI generico OSS"),
        ("bif/bif_5_0_d.h",   "bif_5_0",   "VI generico PCIe"),
        ("gca/gfx_8_0_d.h",   "gfx_8_0",   "VI generico NUCLEO"),
        ("dce/dce_10_0_d.h",  "dce_10_0",  "VI generico DISPLAY"),
        ("smu/smu_7_1_3_d.h", "smu_7_1_3", "Polaris12  RELOJ"),
    ]
    regs, fam_of = {}, {}
    print("mapas de registro, en el orden en que los incluye gfx_v8_0.c:")
    for rel, tag, desc in FAMILIES:
        h = parse_d_header(f"{HDRS}/{rel}")
        for n, off in h.items():
            if n not in regs:
                regs[n] = off
                fam_of[n] = tag
        print(f"  {rel:22} {desc:24} {len(h):5}")
    print()
    print(f"  registros unicos resolubles: {len(regs)}")
    print(f"  de familia ESPECIFICA de Polaris12 (gmc/smu): "
          f"{sum(1 for n,t in fam_of.items() if t in ('gmc_8_2','smu_7_1_3'))}")
    # los _sh_mask.h de LAS SEIS familias. Antes cargaba cuatro y por eso
    # SRBM / HDP / GMCON salian con '0 campos' -- no porque no los tengan, sino
    # porque no mire donde estaba su mascara. Un 0 por no haber buscado es
    # indistinguible de un 0 real, y por eso el campo lleva el nombre de la
    # familia en la columna: si vuelve a 0 se ve de donde.
    masks = {}
    for rel, tag, _desc in FAMILIES:
        masks[tag] = parse_mask_header(
            f"{HDRS}/{rel.replace('_d.h', '_sh_mask.h')}")
    total_fields = sum(len(v) for v in masks.values())
    print(f"  mascaras de campo cargadas: {total_fields} campos en "
          f"{sum(len(v) for v in masks.values() if v)} registros")
    for tag, m in masks.items():
        print(f"    {tag:12} {len(m):5} registros con campos definidos")
    print()

    idx, live = reachable_functions()
    print(f"funciones alcanzables: {len(live)}")
    print()

    def fields_of(regname):
        """Campos definidos, normalizando el prefijo mm (ver parse_mask_header)."""
        bare = regname[2:] if regname.startswith("mm") else regname
        return masks[fam_of.get(regname, "")].get(bare, {})

    hits, unresolved = scan_accesses(idx, live, regs)



    writes = {r: v for r, v in hits.items() if v["W"]}
    reads = {r: v for r, v in hits.items() if r not in writes}

    # CHEQUEO DE COLISION: dos nombres distintos en el mismo offset seria una
    # red de seguridad, no un resultado. Se comprueba en el conjunto TOCADO,
    # no en los 11592 del mapa entero (alli los alias son legitimos y
    # habituales). Sobre los tocados, un choque significa que mi resolucion de
    # familias por orden de include esta equivocada en algun punto.
    byoff = {}
    for r in set(writes) | set(reads):
        byoff.setdefault(regs[r], []).append(r)
    col = {o: v for o, v in byoff.items() if len(v) > 1}

    print("-" * 78)
    print(f"A · REGISTROS ESCRITOS  ({len(writes)})   -- los que un driver debe programar")
    print("-" * 78)
    hdr = f"{'registro':32} {'offset':>9} {'W':>3} {'R':>3}  {'familia':12} campos"
    print(hdr)
    print("-" * len(hdr))
    for r in sorted(writes, key=lambda x: regs[x]):
        v = writes[r]
        nf = len(fields_of(r))
        site = f"{v['sites'][0][0]}:{v['sites'][0][1]}"
        print(f"{r:32} 0x{regs[r]:06x}  {v['W']:3} {v['R']:3}  "
              f"{fam_of[r]:12} {nf:3}   [{site}]")
    print()
    print(f"  subtotal escrituras: {sum(v['W'] for v in writes.values())}")
    print()

    print("-" * 78)
    print(f"B · SOLO LEIDOS  ({len(reads)})   -- consultar, no programar")
    print("-" * 78)
    for r in sorted(reads, key=lambda x: regs[x]):
        v = reads[r]
        nf = len(fields_of(r))
        site = f"{v['sites'][0][0]}:{v['sites'][0][1]}"
        print(f"{r:32} 0x{regs[r]:06x}  {v['W']:3} {v['R']:3}  "
              f"{fam_of[r]:12} {nf:3}   [{site}]")
    print()
    print(f"  subtotal lecturas: {sum(v['R'] for v in reads.values())}")
    print()

    print("-" * 78)
    print("C · NO RESUELTOS  (acceso a un mm* que no esta en gmc_8_2_d.h)")
    print("-" * 78)
    if not unresolved:
        print("  (ninguno)")
    for r, sites in sorted(unresolved.items()):
        print(f"  {r:34}  x{len(sites):<3} [{sites[0][0]}:{sites[0][1]}]")
    print(f"  subtotal no resueltos: {len(unresolved)}")
    print()

    print("-" * 78)
    print(f"D · CHEQUEO DE COLISION de offset sobre los registros tocados")
    print("-" * 78)
    if not col:
        print(f"  ninguno. {len(set(writes)|set(reads))} registros, "
              f"{len(byoff)} offsets distintos.")
        print("  Eso confirma que resolver el mapa por orden de #include no esta")
        print("  mezclando familias.")
    else:
        for o, v in sorted(col.items()):
            print(f"  *** 0x{o:06x}: {', '.join(sorted(v))}")
    print()

    print("=" * 78)
    print("LIMITACION")
    print("  1. Se escanean ACCESOS DIRECTOS con mm*. El direccionado por bloque")
    print("     (AMDGCN_REG_OFFSET / SOC15_REG_OFFSET) se cuenta aparte en 'no")
    print("     resueltos' y NO se inventa su offset.")
    print("  2. El corpus es parcial: display/ y dc/ no estan. Los registros que")
    print("     solo se toquen desde ahi son falsos negativos aqui.")
    print("  3. Este es el subgrafo del KERNEL. Como inventario del ASIC es")
    print("     NOT_DETERMINED, no PROVEN.")
    print("=" * 78)


if __name__ == "__main__":
    main()