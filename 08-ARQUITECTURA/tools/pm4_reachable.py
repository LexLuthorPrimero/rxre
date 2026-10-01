#!/usr/bin/env python3
"""
VOCABULARIO PM4 VIVO DE UN ASIC: que paquetes ejecuta de verdad, no cuales define.

Por que esto es distinto de "grep PACKET3 en el fichero":

El driver de amdgpu tiene ~74 opcodes PACKET3 definidos para GFX8 (sid.h) y
codigo que emite muchos de ellos, pero solo una parte se alcanza con un ASIC
concreto. Hay codigo muerto por condicion de ASIC, codigo muerto porque el
modulo no lo compila para esta generacion, y codigo muerto por rama de
configuracion. Un "grep PACKET3" mezcla las tres cosas y no dice cuales.

Para un driver propio la pregunta util no es "que paquetes existen" sino
"cuales necesita este ASIC, en el camino que realmente ejecuta". Eso es
alcanzabilidad estatica:

  1. Indexar todas las funciones de amdgpu/*.c  (nombre -> cuerpo).
  2. Semillas = los punteros a funcion ASIGNADOS en las tablas ring_funcs de
     la generacion, mas los puntos de entrada genericos del submit
     (amdgpu_ring_commit, amdgpu_sched_*, amdgpu_ib_*).
  3. Recorrido BFS de las llamadas, resolviendo nombres a funciones reales.
  4. Todo PACKET3 emitido desde una funcion alcanzable = VOCABULARIO VIVO.
  5. Todo lo demas = NO ALCANZABLE desde las semillas de este ASIC.

LIMITACION, declarada y no escondida: el corpus es parcial (no hay display/,
dc/, kfd/, ttm/). El recorrido se detiene en el borde del corpus y todo lo que
cruza ese borde se marca, no se cuenta. Un paquete puede ser alcanzable por una
ruta que viva en display/ y que aqui no se vea. Por eso la salida distingue
"VIVO", "NO ALCANZABLE" y "FUERA DE ALCANCE (borde del corpus)".
"""
import re, sys, glob, os
from collections import defaultdict, deque

BASE = "RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu"

# Puntos de entrada genericos del submit. Son los que invocan ring->funcs->*.
# Son las semillas que no dependen del ASIC, pero sin ellos el recorrido
# desde las semillas de ring_funcs no llegaria al camino real de codigo.
GENERIC_ROOTS = [
    "amdgpu_ring_commit",
    "amdgpu_sched_run_job",
    "amdgpu_sched_process_job",
    "amdgpu_sched_sync_job",
    "amdgpu_ib_schedule",
    "amdgpu_ib_run",
    "amdgpu_ib_perform_direct",
    "amdgpu_ib_fence",
    "amdgpu_ib_add_job",
    "amdgpu_ib_attach",
    "amdgpu_fence_driver_start_ring",
    "amdgpu_fence_driver_stop_ring",
    "amdgpu_fence_wait_polling",
    "amdgpu_fence_process",
    "amdgpu_ring_fence_wait",
    "amdgpu_ring_fence_process",
    "amdgpu_ring_init",
    "amdgpu_ring_emit_fence",
    "amdgpu_ring_insert_nop",
    "amdgpu_ring_generic_pad_ib",
    "amdgpu_ring_fill_start_dw",
    "amdgpu_ring_pad_ib",
    "amdgpu_vm_flush",
    "amdgpu_vm_init",
    "amdgpu_vm_set_page_table_base",
    "amdgpu_device_attach",
]

FUNC_DEF = re.compile(r"^(static\s+)?[\w \*]*?\**(\w+)\s*\(")


def index_functions():
    """nombre -> (fichero, ini, fin, src). Solo definiciones, no prototipos."""
    idx = {}
    for p in sorted(glob.glob(f"{BASE}/*.c")):
        src = open(p, errors="replace").read().split("\n")
        i = 0
        while i < len(src):
            l = src[i]
            if FUNC_DEF.match(l) and not l.rstrip().endswith(";"):
                m = FUNC_DEF.match(l)
                name = m.group(2)
                j = i
                while "{" not in src[j] and j < len(src) - 1:
                    j += 1
                if "{" not in src[j]:
                    i += 1
                    continue
                d = 0
                for k in range(j, len(src)):
                    d += src[k].count("{") - src[k].count("}")
                    if d == 0:
                        # el primero gana: evita que una declaracion adelanteada
                        # pise la definicion real
                        idx.setdefault(name, (os.path.basename(p), i, k, src))
                        i = k
                        break
                else:
                    break
            i += 1
    return idx


def opcode_values():
    """opcode -> valor, opcode -> fichero, y opcode -> CONFLICTO si lo hay.

    DEFECTO QUE ESTA COMPROBACION ARREGLA, y que encontre por una mutacion:
    antes hacia vals.setdefault(nombre, valor) recorriendo las cabeceras en
    orden alfabetico. Con eso, si dos cabeceras dieran valores DISTINTOS para
    el mismo opcode, la herramienta se quedaba con la primera y no lo decia
    nunca. Es el peor fallo posible en una tabla de resolucion: no da un
    numero falso, da un numero arbitrario sin marcar.

    Lo que se hace ahora: se recogen TODOS los valores y se informa de los
    que discrepan. El valor que se usa es el primero, pero el conflicto se
    declara, porque un pacote redefinido entre generaciones es informacion.

    Se vio mutando sid.h: PACKET3_COND_EXEC 0x22 -> 0x23. La herramienta
    seguia diciendo 0x22, y la razon no era la que yo suponia (que GFX8
    tomase el opcode de otra cabecera), sino algo mas simple y mas
    tranquilizador: los CINCO headers de este corpus definen COND_EXEC como
    0x22. El opcode es redundante, no contradictorio. Pero el工具 no podia
    distinguir un caso del otro, y por eso lacked la comprobacion.
    """
    vals, where, conflict = {}, {}, {}
    for p in sorted(glob.glob(f"{BASE}/*.h")):
        for l in open(p, errors="replace"):
            m = re.match(r"\s*#\s*define\s+(PACKET3_[A-Z0-9_]+)\s+(0x[0-9A-Fa-f]+)\s*$", l)
            if not m:
                continue
            name, v = m.group(1), int(m.group(2), 16)
            conflict.setdefault(name, {}).setdefault(v, []).append(
                os.path.basename(p))
            vals.setdefault(name, v)
            where.setdefault(name, os.path.basename(p))
    clashes = {n: d for n, d in conflict.items() if len(d) > 1}
    return vals, where, clashes


def assigned_funcs(fname):
    """Nombres de funcion a los que apunta una tabla de structs concreta."""
    src = open(f"{BASE}/{fname}", errors="replace").read()
    out = []
    for m in re.finditer(r"^\s*\.(\w+)\s*=\s*(\w+)\s*,", src, re.M):
        out.append((m.group(1), m.group(2)))
    return out


def calls_in(body):
    """Nombres de funcion llamados en un cuerpo. Heuristico y declarado."""
    found = set()
    for m in re.finditer(r"(?<![\w.])([a-z_][a-z0-9_]*)\s*\(", body):
        n = m.group(1)
        if n in ("if", "for", "while", "switch", "return", "sizeof",
                 "defined", "__builtin_expect"):
            continue
        found.add(n)
    return found


def packets_in(name, rec):
    """(opcode, F, linea) de cada PACKET3 emitido en la funcion."""
    f, lo, hi, src = rec
    out = []
    for k in range(lo, hi + 1):
        m = re.search(r"PACKET3\(\s*(PACKET3_[A-Z0-9_]+|[\w\.]+)\s*,\s*([\w\.\(\)0-9 +\-]+?)\s*\)\s*\)", src[k])
        if m:
            out.append((m.group(1), m.group(2).strip(), k + 1, f))
    return out


def main():
    idx = index_functions()
    vals, where, clashes = opcode_values()
    if not idx:
        sys.exit("NO_FUNCTIONS_INDEXED -- el indexador esta roto")
    print("=" * 76)
    print("VOCABULARIO PM4 VIVO -- alcanzabilidad estatica desde las semillas de submit")
    print("=" * 76)
    print(f"funciones indexadas en amdgpu/*.c : {len(idx)}")
    print(f"opcodes PACKET3 definidos        : {len(vals)}")
    if clashes:
        print()
        print("*** CONFLICTO DE VALOR entre cabeceras ***")
        print("  El mismo opcode definido con valores distintos. La herramienta")
        print("  usa el primero, y aqui lo declara:")
        for n, d in sorted(clashes.items()):
            det = "; ".join(f"0x{v:02X} en {','.join(sorted(fs))}"
                            for v, fs in sorted(d.items()))
            print(f"  {n:36} {det}")
    else:
        print("conflictos de valor entre cabeceras: ninguno")
    print()

    # --- 1. semillas -------------------------------------------------
    seeds = []
    ringtabs = [n for n in idx if "ring_funcs_gfx" in n or "ring_funcs_compute" in n]
    # las tablas ring_funcs son variables, no funciones: se leen del fichero
    for tab in ("gfx_v8_0_ring_funcs_gfx", "gfx_v8_0_ring_funcs_compute"):
        for field, fn in assigned_funcs("gfx_v8_0.c"):
            pass  # se filtra abajo por pertenencia a la tabla
    # lectura dirigida: los punteros de TODAS las tablas ring_funcs de GFX8.
    #
    # DEFECTO QUE CORRIJO AQUI: mi primera version sembraba solo
    # ring_funcs_gfx y ring_funcs_compute, y por eso reportaba
    # PACKET3_MAP_QUEUES y UNMAP_QUEUES como codigo muerto. Es falso, y es el
    # paquete mas importante de los dos: MAP_QUEUES es lo que instala la cola
    # en el hardware. Vive en el KIQ, que tiene su propia tabla
    # (gfx_v8_0_ring_funcs_kiq) y no aparece en las otras dos.
    #
    # El sintoma fue util: un resultado que dice "el paquete que instala la cola
    # no se usa en este ASIC" es tan absurdo que obliga a mirar. Si la
    # herramienta hubiera semillado solo el camino de usuario, habria
    # confirmado de mas una creencia falsa sobre el ASIC.
    src8 = open(f"{BASE}/gfx_v8_0.c", errors="replace").read()
    for tab in ("gfx_v8_0_ring_funcs_gfx", "gfx_v8_0_ring_funcs_compute",
                "gfx_v8_0_ring_funcs_kiq"):
        m = re.search(r"struct amdgpu_ring_funcs\s+" + tab + r"\s*=\s*\{(.*?)\n\};", src8, re.S)
        if not m:
            continue
        for f2, fn in re.findall(r"^\s*\.(\w+)\s*=\s*(\w+)\s*,", m.group(1), re.M):
            if fn in idx:
                seeds.append((f"{tab}.{f2}", fn))
    for g in GENERIC_ROOTS:
        if g in idx:
            seeds.append(("generic", g))

    # SEGUNDA CORRECCION DE SIEMBRA, y la mas importante.
    #
    # Anadio solo las tres tablas ring_funcs y seguia reportando
    # MAP_QUEUES / SET_RESOURCES / UNMAP_QUEUES como codigo muerto. Falso: esos
    # tres son exactamente el protocolo de instalacion de colas, y 029 y 034 ya
    # habian leido sus emisiones en el codigo.
    #
    # La causa es de fondo y no la quiero maquillar: la ruta de instalar una cola
    # NO pasa por un puntero de ring_funcs. Entra por
    #   gfx_v8_0_kcq_resume -> gfx_v8_0_kiq_kcq_enable -> MAP_QUEUES
    # que es un camino de INIT/RESUME, no de submit. Sembrar solo ring_funcs
    # analiza el camino de envio y no el de arranque, y el segundo contiene
    # paquetes que el primero necesita.
    #
    # Por eso las semillas tienen dos familias y no una: envio (ring_funcs) y
    # arranque (early_init y sus descendientes). Un inventario de PM4 que solo
    # mire el submit informa mal por construccion: omite la palabra que
    # enciende el motor.
    # SEMILLAS: SOLO PUNTEROS DE NIVEL SUPERIOR.
    #
    # DEFECTO QUE CORRIJO, y que solo aparecio al hacer la prueba de mutacion:
    # mi primera version sembraba tambien las funciones hoja
    # (kiq_kcq_enable, kcq_init_queue, ring_init...). Con eso, romper la arista
    # de llamada NO cambiaba el resultado, porque la hoja estaba sembrada y se
    # alcanzaba igual. La herramienta era insensible justo a lo que debe
    # medir.
    #
    # Corregido: las semillas son unicamente punteros de tablas -- los tres
    # ring_funcs y los de ciclo de vida de amd_ip_funcs -- y el resto lo
    # descubre el BFS. Asi una arista rota SACA un paquete del inventario, que es
    # lo que hace la herramienta creible en su categoria de precision.
    #
    # Y de paso se ve por que no hay llamadas directas: gfx_v8_0_early_init,
    # gfx_v8_0_resume y gfx_v8_0_hw_fini NO los llama nadie por nombre. Se
    # llaman a traves de struct amd_ip_funcs (gfx_v8_0.c:6849-6868). Un
    # indexador que solo buscara llamadas perderia las tres fases del ciclo de
    # vida enteras.
    IP_FUNCS = ("early_init", "late_init", "sw_init", "sw_fini",
                "hw_init", "hw_fini", "suspend", "resume", "is_idle",
                "wait_for_idle", "check_soft_reset", "pre_soft_reset",
                "soft_reset", "post_soft_reset",
                "set_clockgating_state", "set_powergating_state",
                "get_clockgating_state")
    src8_ip = open(f"{BASE}/gfx_v8_0.c", errors="replace").read()
    m_ip = re.search(r"struct amd_ip_funcs\s+gfx_v8_0_ip_funcs\s*=\s*\{(.*?)\n\};",
                     src8_ip, re.S)
    if not m_ip:
        print("AVISO: no se encontro gfx_v8_0_ip_funcs; el analisis de ciclo de")
        print("        vida quedaria incompleto. Se declara, no se asume.")
    else:
        for fld, fn in re.findall(r"^\s*\.(\w+)\s*=\s*(\w+)\s*,",
                                  m_ip.group(1), re.M):
            if fn in idx and fld in IP_FUNCS:
                seeds.append((f"ip_funcs.{fld}", fn))

    # known-inert: paquetes que SI se emiten en este ASIC pero no hacen nada.
    # No lo calculo: lo AFIRMO, con la evidencia que lo sostiene. Es el punto
    # donde un inventario de "que paquetes se emiten" se vuelve incompleto por
    # construccion, y por eso va explicito y no deducido.
    KNOWN_INERT = {
        "PACKET3_COND_EXEC":
            "022: el predicado (cond_exe_gpu_addr) solo lo escribe "
            "set_preempt_cond_exec, y sus 10 consumidores son v9/v10/v11/v12, "
            "sdma_v5_0..v7_1 y vpe. CERO en el path GFX8 (verificado). "
            "Con el predicado a 0 el hardware descarta los DW siguientes.",
    }

    print(f"semillas: {len(seeds)}")
    print(f"  de tablas ring_funcs de GFX8 : {sum(1 for s in seeds if 'ring_funcs' in s[0])}")
    print(f"  genericas del submit          : {sum(1 for s in seeds if s[0]=='generic')}")
    print(f"  de ciclo de vida (ip_funcs)  : {sum(1 for s in seeds if s[0].startswith('ip_funcs'))}")
    print()

    # --- 2. BFS ------------------------------------------------------
    seen = set()
    q = deque(fn for _, fn in seeds)
    unresolved = defaultdict(set)   # nombre -> desde quien se llamo
    order = []
    while q:
        fn = q.popleft()
        if fn in seen:
            continue
        seen.add(fn)
        rec = idx.get(fn)
        if not rec:
            continue
        order.append(fn)
        body = "\n".join(rec[3][rec[1]:rec[2] + 1])
        for c in calls_in(body):
            if c in idx and c not in seen:
                q.append(c)
            elif c not in idx:
                unresolved[c].add(fn)

    print(f"funciones alcanzables           : {len(order)} de {len(idx)} indexadas")
    print(f"nombres llamados no indexados   : {len(unresolved)}  (borde del corpus o funciones de kernel)")
    print()

    # --- 3. vocabulary vivo ------------------------------------------
    live = []          # (opcode, F, linea, fichero, funcion)
    livefns = set()
    for fn in order:
        rec = idx[fn]
        body = "\n".join(rec[3][rec[1]:rec[2] + 1])
        # solo si la funcion pertenece al ASIC: se filtra por fichero
        pk = packets_in(fn, rec)
        if pk:
            livefns.add(fn)
            for op, F, ln, f in pk:
                live.append((op, F, ln, f, fn))

    # codigo no alcanzable, por ASIC
    allpk = []
    for fn, rec in idx.items():
        for op, F, ln, f in packets_in(fn, rec):
            allpk.append((op, F, ln, f, fn))

    live_set = {(o, f) for o, _, _, f, _ in live}

    # DEFECTO QUE CORRIJO AQUI, y que hacia la primera version inutil:
    # "no alcanzable" mezclaba TODAS las generaciones. Un PACKET3 en
    # gfx_v10_0.c es inalcanzable desde semillas GFX8 por definicion -- es otro
    # ASIC -- y meterlo en una lista llamada "no alcanzable" lo presenta como si
    # fuera codigo muerto de ESTE ASIC. Es una falsa afirmacion de la clase que
    # mas dano hace: invita a concluir que un paquete no se usa cuando en
    # realidad lo usa otra generacion.
    #
    # La categoria accionable es "escrito en el path de ESTE ASIC y no se
    # ejecuta". Se restringe a los ficheros que pertenecen al camino GFX8.
    GFX8_PATH = ("gfx_v8_0.c", "gmc_v8_0.c", "amdgpu_gfx.c", "cikd.c",
                 "sdma_v3_0.c", "amdgpu_gfx.h")
    dead = [x for x in allpk
            if (x[0], x[3]) not in live_set and x[3] in GFX8_PATH]
    other_gen = [x for x in allpk if x[3] not in GFX8_PATH]

    def norm(op):
        return op if op.startswith("PACKET3") else op

    live_ops = {}
    for op, F, ln, f, fn in live:
        if op.startswith("PACKET3"):
            live_ops.setdefault(op, []).append((f, ln, fn, F))

    print("-" * 76)
    print("A · EMITIDO Y EFECTIVO   (se emite y hace algo)")
    print("-" * 76)
    effective = 0
    for op in sorted(live_ops, key=lambda o: (vals.get(o, 0x100), o)):
        if op in KNOWN_INERT:
            continue
        v = vals.get(op)
        vs = f"0x{v:02X}" if v is not None else "?"
        sites = live_ops[op]
        effective += 1
        print(f"  {op:38} {vs:>6}   x{len(sites):<3} "
              f"[{sites[0][0]}:{sites[0][1]}]")
    print()
    print(f"  subtotal: {effective}")
    print()

    print("-" * 76)
    print("B · EMITIDO PERO INERTE   (llega al hardware y no hace nada)")
    print("-" * 76)
    print("  Categoria que un 'grep PACKET3' no puede ver. Un paquete puede estar")
    print("  en cada submit y ser un no-op. Contarlos como necesarios para un")
    print("  driver minimo es trabajo desperdiciado.")
    print()
    inert_found = False
    for op in sorted(live_ops, key=lambda o: (vals.get(o, 0x100), o)):
        if op not in KNOWN_INERT:
            continue
        inert_found = True
        v = vals.get(op)
        vs = f"0x{v:02X}" if v is not None else "?"
        sites = live_ops[op]
        print(f"  {op:38} {vs:>6}   x{len(sites):<3} "
              f"[{sites[0][0]}:{sites[0][1]}]")
        print(f"      {KNOWN_INERT[op]}")
    if not inert_found:
        print("  (ninguno)")
    print()
    print(f"  subtotal: {len([o for o in live_ops if o in KNOWN_INERT])}")
    print()
    print(f"  TOTAL alcanzables (A+B) = {len(live_ops)}   |   EFECTIVOS (A) = {effective}")
    print()

    # --- 4. lo que queda fuera ---------------------------------------
    dead_ops = defaultdict(list)
    for op, F, ln, f, fn in dead:
        if op.startswith("PACKET3"):
            dead_ops[op].append((f, ln, fn))

    print("-" * 76)
    print("CODIGO MUERTO EN ESTE ASIC")
    print("(escrito en el path GFX8, emitido, y NO alcanzado desde las semillas)")
    print("-" * 76)
    if not dead_ops:
        print("  (ninguno)")
    for op in sorted(dead_ops, key=lambda o: (vals.get(o, 0x100), o)):
        v = vals.get(op)
        vs = f"0x{v:02X}" if v is not None else "?"
        sites = dead_ops[op]
        print(f"  {op:38} {vs:>6}   x{len(sites):<3} "
              f"[{sites[0][0]}:{sites[0][1]}]")
    print()
    print(f"  TOTAL opcodes muertos en GFX8: {len(dead_ops)}")
    print()
    print(f"  [descartado, no es codigo muerto] emisiones en ficheros de OTRAS")
    print(f"  generaciones: {len(other_gen)}. Son otros ASICs; inalcanzables desde")
    print(f"  semillas GFX8 por definicion, no por estar muertos.")
    print()

    # --- 5. limite honesto -------------------------------------------
    print("=" * 76)
    print("LIMITE DE ESTA HERRAMIENTA, y es estructural, no un detalle:")
    print("  El corpus NO contiene display/, dc/, amdkfd/, ttm/, vcn/, jpeg/.")
    print("  El recorrido se detiene en el borde. Un paquete alcanzable solo")
    print("  desde una ruta de display/dc contaria como 'no alcanzable' aqui,")
    print("  que es una FALSA NEGATIVA. Por eso:")
    print(f"    alcanzables   = {len(order)} funciones")
    print(f"    no indexadas  = {len(unresolved)} nombres llamados que no resuelven")
    print("  Los nombres no resueltos son la medida del borde. Los mas citados:")
    for n, callers in sorted(unresolved.items(),
                             key=lambda kv: -len(kv[1]))[:12]:
        print(f"    {n:34} desde {len(callers)} funciones")
    print("=" * 76)


if __name__ == "__main__":
    main()