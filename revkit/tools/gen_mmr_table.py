#!/usr/bin/env python3
"""Genera la tabla de registros que mmrlive.c lleva embebida, LEYENDO la
lista blanca del driver.  Existe para que las dos no puedan divergir.

Fuente de verdad: amdgpu/vi.c  ->  vi_allowed_read_registers[]
Offsets: include/asic_reg/{gca,oss,gc,gmc}/*.d.h, mas vid.h para SDMA*_REGISTER_OFFSET
Salida:    tabla C lista para sustituir en mmrlive.c
"""
import re, os, sys, glob

AMD  = 'rx550-upstream-7.2.8/linux-7.2.8/drivers/gpu/drm/amd'
AR   = os.path.join(AMD, 'include/asic_reg')
VI   = os.path.join(AMD, 'amdgpu/vi.c')

def macro_index():
    """mmX -> (offset, fichero) para todas las cabeceras ASIC."""
    idx = {}
    pat = re.compile(r'^#define\s+(mm[A-Za-z0-9_]+)\s+\(?\s*(0[xX][0-9a-fA-F]+)\s*\)?\s*(?:/\*.*)?$', re.M)
    for p in glob.glob(AR + '/**/*.h', recursive=True):
        t = open(p, errors='ignore').read()
        for m in pat.finditer(t):
            # la primera definicion gana: gca/ antes que otras por orden de ruta
            idx.setdefault(m.group(1), (int(m.group(2), 16), os.path.relpath(p, AR)))
    return idx

def sdma_offsets():
    """SDMA0_REGISTER_OFFSET / SDMA1_REGISTER_OFFSET salen de vid.h."""
    out = {}
    for name, src in (('SDMA0_REGISTER_OFFSET', 'vid.h'), ('SDMA1_REGISTER_OFFSET', 'vid.h')):
        t = open(os.path.join(AMD, 'amdgpu', src), errors='ignore').read()
        m = re.search(r'^#define\s+%s\s+(0[xX][0-9a-fA-F]+)' % name, t, re.M)
        if m: out[name] = int(m.group(1), 16)
    return out

def main():
    idx = macro_index()
    sd  = sdma_offsets()
    t   = open(VI, errors='ignore').read()
    i   = t.index('vi_allowed_read_registers[] = {')
    # recortar DESPUES de la llave de la declaracion: si no, esa llave se
    # empareja con la primera entrada y mmGRBM_STATUS sale como "{mmGRBM_STATUS"
    body_start = t.index('{', t.index('=', i)) + 1
    blk = t[body_start:t.index('};', body_start)]
    ent = re.findall(r'\{\s*([^}]+?)\s*\}', blk)

    rows, unresolved = [], []
    for e in ent:
        parts = [x.strip() for x in e.split(',')]
        expr = parts[0]
        indexed_true = len(parts) > 1 and parts[1] == 'true'
        m = re.match(r'^(mm[A-Za-z0-9_]+)(?:\s*\+\s*([A-Za-z0-9_]+))?$', expr)
        if not m:
            unresolved.append((expr, 'no es mmX ni mmX+Y')); continue
        sym, add = m.group(1), m.group(2)
        if sym not in idx:
            unresolved.append((expr, 'macro sin definir')); continue
        off = idx[sym][0]
        if add:
            if add not in sd:
                unresolved.append((expr, 'offset %s sin definir' % add)); continue
            off += sd[add]
        rows.append((off, sym + ('+' + add if add else ''), 1 if indexed_true else 0))

    rows.sort()
    dup = [o for o in set(r[0] for r in rows) if sum(1 for r in rows if r[0] == o) > 1]
    print("/* GENERADO por revkit/tools/gen_mmr_table.py -- NO EDITAR A MANO */")
    print("/* fuente: vi.c:vi_allowed_read_registers[]  (%d entradas, %d sin resolver) */"
          % (len(ent), len(unresolved)))
    if unresolved:
        print("/* SIN RESOLVER:")
        for e, why in unresolved: print(' *   %s  -> %s' % (e, why))
        print(' */')
    for off, name, ix in rows:
        print('        { 0x%04X, "%s", %d },' % (off, name, ix))
    print("/* offsets duplicados: %s */" % (dup if dup else 'ninguno'))
    return 0

if __name__ == '__main__':
    sys.exit(main())
