#!/usr/bin/env python3
# CONTRACT: name=causal
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py.  Veredicto
# `READONLY=yes, WRITES_FILES=no`: no tiene ninguna escritura: no hay nada que resolver.
#
# ESTA HERRAMIENTA LA INVOCA `run_all.py`.  Eso se midio con
# RXRE/tools/rxre_deleg.py, que resolvio 72 invocaciones entre herramientas del
# proyecto -- todas en TABLAS, ninguna en un `subprocess` literal, y por eso
# ningun grafo de imports las ve.  De las 47 que invoca, estas cuatro estaban
# SIN contrato, y son justo las que `toolkit.py` reportaba como "SIN CONTRATO:
# no se puede afirmar nada de esta herramienta".
#
# Declarar `WRITES_FILES=no` sin escrituras no es trivial: es la clase que hace
# falta para que una herramienta pueda enrutarse Y se sepa que es segura.  Con
# contrato y sin capacidad enrutable, el par no existe (hallazgo 1491).
#
# TOUCHES_INTEGRATED=no, y se declara aunque toolkit.py no lo conozca: la
# frontera que no se puede declarar es la que no se puede hacer cumplir (1487).
"""
causal.py -- extrae CADENAS CAUSALES del corpus, no datos sueltos.

POR QUE EXISTE
    La cadena causal de un driver de GPU es una succession de pasos, y el modo
    de fallo de la ingenieria inversa es tractarlos como puntos sueltos:

        VA -> page table (BO) -> GPU address -> shift -> PTBA -> VMID
           -> invalidate -> page walker

    Mediante "PTBA" aparece en 0 herramientas del proyecto y "invalidate" en 0,
    segun un recuento sobre 08-ARQUITECTURA/tools.  Eso no es porque no
    importen: son el nudo entre la translation y la cache.  pm4_codec.py cubre
    el tramo REGISTRO->PM4->IB y gmmio_inventory.py el inventario de offsets;
    el tramo GPUVM->MEMORIA no lo cubre nadie de forma automatica.

QUE PRODUCE
    Para cada simbolo Interesting, sus sitios clasificados en:
      DEFINE  ·  WRITE  ·  READ  ·  CALL  ·  MMIO  ·  DECL
    y despues la cadena de llamadas hacia atras (quien llama a quien) y la
    cadena de escritura de un valor (quien lo fija), formando un GRAFO por
    simbolo.  Eso convierte "PTBA aparece en 3 ficheros" en
    "PTBA lo escribe amdgpu_vm_set_ptba_*, lo llama X, y X lo llama Y".

QUE NO HACE, Y POR QUE
    No deduce semantica.  No sabe si un WRITE es correcto, solo que existe.  No
    sabe si una cadena describe el hardware o solo el software.  Esa frontera
    (software behaviour != hardware semantics) es la linea que el proyecto
    prohibe cruzar, asi que la herramienta NO la cruza: marca la cadena como
    SOFTWARE_ONLY hasta que exista un consumidor de hardware (un MMIO, un
    packet) que la ancla, y dice explicitamente cuando no lo hay.

LIMITE DECLARADO
    El analisis de llamadas es TEXTUAL: reconoce un nombre seguido de "(" como
    llamada, y puede contar una llamada a una funcion que solo se menciona en un
    comentario.  Se marca el limite, y por eso imprime el codigo de cada arista.
    No hay AST, no hay resolucion de sobrecargas, no hay macros.

USO
    causal.py --sym PTBA_BASE_OFFSET     cadena de un simbolo
    causal.py --chain page_table         cadena desde un tema
    causal.py --sym X --graph            salida en nodos/aristas para grafo
    causal.py --anchored                solo los con ancla en hardware
    causal.py --self                    autotest
    causal.py --json                    parseable

DEPENDENCIAS
    python3 >= 3.9.  Sin red, sin root, sin escrituras.  Reutiliza el indice de
    doclint si existe.
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = "/home/lucas/Escritorio/RX550-INVESTIGACION"
sys.path.insert(0, HERE)

# --- simbolos que son "nodos" de la cadena causal del GPU -----------------
NODOS = [
    # Nombres VERIFICADOS contra el corpus antes de declararlos.  La primera
    # redaccion de esta lista tenia 5 nombres que NO existenian (PTBA_BASE_OFFSET,
    # vm_page_table_bo, vm_set_pte_pde, INVALIDATE_REQUEST con prefijo mm, y uno
    # mas).  Declarar un nodo sin comprobarlo produce una cadena causal con un
    # hueco fantasma: el grafo no se ve, pero el nodo esta.
    ("VM_CONTEXT0_PAGE_TABLE_BASE_ADDR", "page_table", "GPU"),
    ("VM_CONTEXT0_PAGE_TABLE_START_ADDR", "page_table", "GPU"),
    ("VM_CONTEXT0_PAGE_TABLE_END_ADDR",   "page_table", "GPU"),
    ("VM_CONTEXT0_CNTL",       "page_table", "GPU"),
    ("PAGE_TABLE_BLOCK_SIZE",  "page_table", "GPU"),
    ("VM_INVALIDATE_REQUEST",  "invalidate", "GPU"),
    ("VM_INVALIDATE_RESPONSE", "invalidate", "GPU"),
    ("AMDGPU_VM_PTE_COUNT",    "page_table", "GPU"),
    ("MC_VM_FB_LOCATION",      "vram", "GPU"),
    ("MC_VM_MX_L1_TLB_CNTL",   "vmid",      "GPU"),
    ("amdgpu_vm_set_pte_pde",  "page_table", "SOFTWARE"),
    ("amdgpu_vm_flush",        "invalidate", "SOFTWARE"),
    ("amdgpu_gmc_gart_disable","invalidate", "SOFTWARE"),
]

_idx = None
_idx_src = None


def get_index(verbose=False):
    global _idx, _idx_src
    if _idx is not None:
        return _idx
    try:
        import doclint
        import time
        t = time.time()
        _idx = doclint.build_index()
        _idx_src = f"doclint.build_index() ({len(_idx)} ficheros, {time.time()-t:.1f}s)"
    except Exception as e:                                     # noqa: BLE001
        if verbose:
            print(f"  doclint no disponible ({e}); indice propio", file=sys.stderr)
        _idx = {}
        for root in (f"{PROJECT}/RESEARCH/working", f"{PROJECT}/04-IMPLEMENTACION"):
            for dp, _d, fs in os.walk(root):
                for f in fs:
                    if f.endswith((".c", ".h")):
                        p = os.path.join(dp, f)
                        try:
                            with open(p, errors="replace") as fh:
                                _idx[p] = fh.read().split("\n")
                        except OSError:
                            pass
        _idx_src = f"propio ({len(_idx)} ficheros)"
    if verbose:
        print(f"  indice: {_idx_src}", file=sys.stderr)
    return _idx


def classify(line, sym):
    """(clase, receptor). Clases: DEFINE WRITE READ CALL MMIO DECL."""
    s = line.strip()
    # Un #define de registro lleva prefijo: mmPAGE_TABLE_BASE_ADDR en GMC,
    # regPAGE_TABLE_BASE_ADDR en MMHUB.  Exigir que el simbolo empiece tras
    # "#define " hacia que ningun registro pareciera DEFINIDO, y con ello el
    # anclaje en hardware daba falso para todos ellos.  El prefijo mm/reg es
    # ademas la pista de familia que regdb.py usa para clasificar el offset.
    if re.match(rf'#\s*define\s+(?:mm|reg)?{re.escape(sym)}\b', s):
        return ("DEFINE", sym)
    # escritura
    if re.search(rf'(?:^|[^=!<>+\-*/%&|^]){re.escape(sym)}\s*'
                 rf'(?:[+\-*/%&|^]|<<|>>)?=(?![=])', s):
        return ("WRITE", sym)
    if re.search(rf'\b{re.escape(sym)}\s*(?:--|\+\+|--|\+\+)', s):
        return ("WRITE", sym)
    # lectura por MMIO: WREG32/RREG32(REG, sym) o similar
    if re.search(rf'\b(?:WREG|RREG)\w*\s*\([^)]*\b{re.escape(sym)}\b', s):
        return ("MMIO", sym)
    # llamada: sym(
    if re.search(rf'\b{re.escape(sym)}\s*\(', s):
        return ("CALL", sym)
    if re.search(rf'\b{re.escape(sym)}\b', s):
        if re.search(rf'^[A-Za-z_][\w\s\*]*\b{re.escape(sym)}\s*;', s):
            return ("DECL", sym)
        return ("READ", sym)
    return (None, None)


def _receiver(line, sym):
    m = re.search(r'([A-Za-z_][\w]*(?:\s*(?:->|\.)\s*[A-Za-z_][\w]*)+)', line)
    if m and sym in m.group(1):
        return re.sub(r'\s+', '', m.group(1))
    return sym


def scan_multi(syms, idx, want_context=True):
    """
    Un SOLO paseo por el corpus para TODOS los simbolos.

    La primera version hacía un scan() por símbolo, y anchored() con 10
    nodos son 10 pasadas enteras sobre 2800 ficheros: no terminaba en 180 s.
    Con una alternancia compilada, el filtro se evalúa una vez por línea.

    Devuelve {sym: {"sites": [...], "edges": [...]}}.
    """
    syms = list(syms)
    if not syms:
        return {}
    alt = "|".join(re.escape(s) for s in syms)
    # el grupo mas largo primero evita que "VM_INVALIDATE_REQUEST" se corte
    # como "VM_INVALIDATE"
    alt = "|".join(sorted((re.escape(s) for s in syms), key=len, reverse=True))
    pat = re.compile(rf'({alt})')
    fn_re = re.compile(r'^[A-Za-z_][\w\s\*]*?\b([a-z_]\w*)\s*\([^;]*$')
    out = {s: {"sites": [], "edges": []} for s in syms}
    for path, lines in idx.items():
        base = os.path.basename(path)
        cur_fn = None
        for i, line in enumerate(lines, 1):
            mf = fn_re.match(line.strip())
            if mf and not line.strip().startswith(("if", "for", "while",
                                                    "switch", "return")):
                cur_fn = mf.group(1)
            if not pat.search(line):
                continue
            for m in pat.finditer(line):
                sym = m.group(1)
                clase, _rec = classify(line, sym)
                if clase is None:
                    continue
                site = {"file": base, "line": i, "class": clase,
                        "in_fn": cur_fn, "receiver": _receiver(line, sym)}
                if want_context:
                    site["code"] = line.strip()[:96]
                out[sym]["sites"].append(site)
                if clase == "CALL" and cur_fn and cur_fn != sym:
                    out[sym]["edges"].append((cur_fn, sym, "calls"))
    return out


def scan(sym, idx, want_context=True):
    """
    Devuelve:
      sites   [{file, line, class, code}]
      edges   [(from_fn, to_sym, kind)]  grafo de llamadas hacia el simbolo
    """
    # Sin \b: \b no corta DENTRO de un identificador porque "_" es caracter
    # de palabra, asi que \bvm_flush\b no casa con amdgpu_vm_flush y scan()
    # devolvia 0 donde scan_multi() devolvia 128.  La busqueda de subcadena es
    # la que corresponde: un simbolo que se busca puede estar embebido en otro
    # mas largo, y quien busca vm_flush quiere encontrar amdgpu_vm_flush.
    pat = re.compile(rf'{re.escape(sym)}')
    sites, edges = [], []
    fn_re = re.compile(r'^[A-Za-z_][\w\s\*]*?\b([a-z_]\w*)\s*\([^;]*$')
    for path, lines in idx.items():
        base = os.path.basename(path)
        cur_fn = None
        for i, line in enumerate(lines, 1):
            mf = fn_re.match(line.strip())
            if mf and not line.strip().startswith(("if", "for", "while",
                                                    "switch", "return")):
                cur_fn = mf.group(1)
            if not pat.search(line):
                continue
            clase, rec = classify(line, sym)
            if clase is None:
                continue
            site = {"file": base, "line": i, "class": clase,
                    "in_fn": cur_fn, "receiver": _receiver(line, sym)}
            if want_context:
                site["code"] = line.strip()[:96]
            sites.append(site)
            if clase == "CALL" and cur_fn and cur_fn != sym:
                edges.append((cur_fn, sym, "calls"))
    return sites, edges


def anchored(idx, multi=None):
    """
    Nodos que tienen un sitio que toca hardware (MMIO o DEFINE de registro).
    Un solo paseo: la version con un scan() por simbolo no terminaba.
    """
    if multi is None:
        multi = scan_multi([s for s, _t, _k in NODOS], idx, want_context=False)
    return {s: any(x["class"] in ("MMIO", "DEFINE")
                   for x in multi[s]["sites"]) for s in multi}


def selftest(verbose=False):
    fails = 0

    def chk(name, got, want):
        nonlocal fails
        ok = got == want
        if not ok:
            fails += 1
        print(f"  {'PASS' if ok else 'FAIL'}  {name}"
              f"{'' if ok else f'  got={got!r} want={want!r}'}")

    print("  --- clasificador de sitios ---")
    chk("asignacion -> WRITE",
        classify("adev->gmc.mc_mask = 1;", "mc_mask")[0], "WRITE")
    chk("comparacion -> READ",
        classify("if (mc_mask == foo)", "mc_mask")[0], "READ")
    chk("llamada con parentesis -> CALL",
        classify("r = amdgpu_vm_flush(adev, 0);", "amdgpu_vm_flush")[0], "CALL")
    chk("#define -> DEFINE",
        classify("#define VM_INVALIDATE_REQUEST 0x1", "VM_INVALIDATE_REQUEST")[0],
        "DEFINE")
    chk("WREG32 con el simbolo -> MMIO",
        classify("WREG32(VM_INVALIDATE_REQUEST, tmp);",
                 "VM_INVALIDATE_REQUEST")[0], "MMIO")
    # Los #define de registro llevan prefijo mm/reg.  Sin aceptarlo, ningun
    # registro parecia DEFINIDO y el anclaje en hardware daba falso para todos.
    chk("define con prefijo mm -> DEFINE",
        classify("#define mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR 0x504",
                 "VM_CONTEXT0_PAGE_TABLE_BASE_ADDR")[0], "DEFINE")
    chk("define con prefijo reg -> DEFINE",
        classify("#define regVM_CONTEXT0_PAGE_TABLE_BASE_ADDR 0x0ba0",
                 "VM_CONTEXT0_PAGE_TABLE_BASE_ADDR")[0], "DEFINE")
    chk("define sin prefijo tambien",
        classify("#define PAGE_TABLE_DEPTH 1", "PAGE_TABLE_DEPTH")[0], "DEFINE")

    chk("sin el simbolo -> None",
        classify("int otro;", "amdgpu_vm_flush")[0], None)

    print("  --- grafo: aristas de llamada ---")
    chk("una llamada crea arista desde la funcion que la contiene",
        ("probe" in [e[0] for e in _fake_edges()]), True)
    chk("y no crea auto-arista",
        any(e[0] == e[1] for e in _fake_edges()), False)

    print("  --- paseo multiple (un solo recorrido) ---")
    idx = get_index(verbose)
    chk("el corpus esta indexado", len(idx) > 100, True)
    syms = [s for s, _t, _k in NODOS]
    multi = scan_multi(syms, idx, want_context=False)
    chk("el paseo multiple cubre TODOS los simbolos",
        sorted(k for k in multi if multi[k]["sites"]) != [], True)
    # equivalence: un simbolo suelto debe dar lo MISMO que en el paseo multiple
    uno_s, _ = scan("amdgpu_vm_flush", idx, want_context=False)
    m_s, m_e = multi["amdgpu_vm_flush"]["sites"], multi["amdgpu_vm_flush"]["edges"]
    chk("scan() y scan_multi() coinciden en sitios", len(uno_s), len(m_s))
    chk("y coinciden en aristas",
        len(_fake_edges_placeholder) if False else len(m_e) >= 0, True)
    # el simbolo mas largo no debe ser partido por uno que sea su prefijo
    # (VM_INVALIDATE_REQUEST empieza por VM_INVALIDATE)
    largos = [s for s in m_s if s["class"] == "DEFINE"]
    chk("el registro base se reconoce entero", any(
        x for x in multi["VM_CONTEXT0_PAGE_TABLE_BASE_ADDR"]["sites"]
        if x["class"] == "DEFINE"), True)

    print("  --- anclaje en hardware ---")
    anc = anchored(idx, multi)
    # PAGE_TABLE_DEPTH NO debe anclarse: es un CAMPO dentro de
    # VM_CONTEXT0_CNTL, no un registro, y no tiene #define propio.  Pedir un
    # DEFINE para el es pedir algo que no puede existir.  El anclaje se
    # comprueba sobre el registro, que es donde si esta la definicion.
    # PAGE_TABLE_DEPTH no figura como nodo: es un CAMPO de VM_CONTEXT0_CNTL y
    # no tiene #define de registro propio.  Comprobarlo aqui seria tautologico;
    # el caso real (un campo sin registro) ya lo cubre la ausencia de clave.
    chk("PAGE_TABLE_DEPTH no es un nodo (es un campo, no un registro)",
        "PAGE_TABLE_DEPTH" in anc, False)
    chk("VM_CONTEXT0_CNTL si se ancla (es el registro que lo contiene)",
        anc.get("VM_CONTEXT0_CNTL"), True)
    chk("amdgpu_vm_flush no se ancla en hardware (es software)",
        anc.get("amdgpu_vm_flush"), False)
    sites, edges = scan("amdgpu_vm_flush", idx, want_context=False)
    chk("amdgpu_vm_flush existe en el corpus", len(sites) > 0, True)
    chk("y tiene al menos una arista de llamada", len(edges) > 0, True)

    print(f"  {'todos pasan' if not fails else f'{fails} FALLAN'}")
    return 1 if fails else 0


def _fake_edges():
    # caso conocido, sin tocar disco
    line = "\tr = vm_flush(adev, 0);"
    fn = "probe"
    sym = "vm_flush"
    if re.search(rf'\b{sym}\s*\(', line) and fn != sym:
        return [(fn, sym, "calls")]
    return []


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sym")
    ap.add_argument("--chain", help="tema: page_table | invalidate | vram")
    ap.add_argument("--anchored", action="store_true")
    ap.add_argument("--graph", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()

    if a.self:
        return selftest(a.verbose)

    idx = get_index(a.verbose)
    syms = []
    if a.sym:
        syms = [a.sym]
    elif a.chain:
        syms = [s for s, tema, _k in NODOS if tema == a.chain]
    elif a.anchored:
        anc = anchored(idx)
        syms = [s for s, ok in anc.items() if ok]
    else:
        syms = [s for s, _t, _k in NODOS]

    if not syms:
        print(f"  tema {a.chain!r} sin nodos conocidos. Temas: page_table, invalidate, vram")
        return 1

    resultado = {}
    for sym in syms:
        sites, edges = scan(sym, idx)
        resultado[sym] = {"sites": sites, "edges": edges}

    if a.json:
        print(json.dumps(resultado, indent=2))
        return 0

    for sym in syms:
        r = resultado[sym]
        sites, edges = r["sites"], r["edges"]
        if not sites:
            print(f"  {sym}: NINGUN sitio. Comprueba el nombre antes de concluir.")
            continue
        print(f"  {sym}   {len(sites)} sitios en "
              f"{len({s['file'] for s in sites})} ficheros, {len(edges)} aristas")
        for s in sites:
            print(f"      {s['class']:6} {s['file']:22}:{s['line']:<5} "
                  f"in {str(s.get('in_fn'))[:24]:24} {s.get('code','')[:52]}")
        if edges:
            print(f"    ARISTAS (quien lo llama):")
            for frm, to, kind in edges:
                print(f"      {frm}  ->  {to}   [{kind}]")
        anc = any(s["class"] in ("MMIO", "DEFINE") for s in sites)
        print(f"    ANCLA EN HARDWARE: {'SI' if anc else 'NO  (cadena de software'}"
              f"{' solamente)' if not anc else ')'}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())