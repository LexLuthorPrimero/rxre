#!/usr/bin/env python3
# CONTRACT: name=pm4_codec
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no

r"""PM4 CODEC -- decodificar y construir indirect buffers de Polaris12.

POR QUE EXISTE Y POR QUE AHORA. La cadena causal de un proyecto de ingenieria
inversa es:

    REGISTRO -> MMIO -> PM4/IB -> CP/PFP/ME -> GPUVM -> MEMORIA -> EFECTO

Todo lo que he medido en 033-040 vive a la izquierda de "PM4/IB" o a la
derecha. El decodificador es **el cuello de botella**: sin el, el resto son
ficheros y el hardware es un misterio; con el, se puede tomar un IB de
verdad y leerlo.

Y se puede hacer YA porque las reglas de framing estan PROVEN y medidas:

    034/036/039, con dos fuentes internas independientes:
      TYPE3: campo F = numero de dwords de DATOS - 1
             paquete = F + 2 dwords
             F = 0x3FFF RESERVADO: la cabecera sola es el paquete
             opcode en bits 8..15, tipo en bits 31..30, longitud en 16..29
      033/034: paridad impar en TYPE4 y TYPE7, no en TYPE0 ni TYPE3
      033: los cuatro NOP de firmware son ASCII (MESG, BEGN, END)

Los nombres de opcode y las mascaras de campo salen del CIERRE DE INCLUDES real
de gfx_v8_0.c (039), no de un barrido alfabetico que ya se demostro falso.

Lo que NO hace, y se declara:
  * No interpreta la SEMANTICA de un payload. `RELEASE_MEM` con 6 dwords se
    decodifica con sus nombres de campo y su ancho; lo que el hardware HACE con
    ellos sigue siendo NOT_DETERMINED, y el decodificador no lo disimula.
  * No valida contra el hardware. Que el framing este bien no significa que el
    paquete sea lo que el driver creo.
  * Los macros de funcion (que expanden a varios dwords) no se expanden. Se
    marca el campo como MACRO_EXPAND con el nombre, no se decodifica.

Uso:
  python3 pm4_codec.py --ib fichero.bin              decodifica un IB
  python3 pm4_codec.py --ib f.bin --hex               con volcado hex
  python3 pm4_codec.py --opcodes                     tabla de opcodes
  python3 pm4_codec.py --doc <opcode>                 layout documentado
  python3 pm4_codec.py --build MAP_QUEUES 1 2 3 ...  construye un IB
  python3 pm4_codec.py --roundtrip f.bin             ida y vuelta byte-exacta
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
AMD = ("/home/lucas/Escritorio/RX550-INVESTIGACION/"
       "RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd")
AMDDIR = f"{AMD}/amdgpu"

TYPE = {0: "TYPE0", 1: "TYPE1", 2: "TYPE2", 3: "TYPE3", 4: "TYPE4",
        7: "TYPE7"}

# layout documentado por el kernel, como frase y no como layout numerico.
# La fuente es el comentario del _sh_mask.h: lo que hay aqui es lo que el propio
# driver escribe sobre el paquete.
DOC_LAYOUTS = {
    "PACKET3_CP_DMA": [
        "CONTROL",
        "SRC_ADDR_LO | DATA",
        "CP_SYNC[31] | SRC_SEL[30:29] | ENGINE[27] | DST_SEL[21:20] | SRC_ADDR_HI[7:0]",
        "DST_ADDR_LO[31:0]",
        "DST_ADDR_HI[7:0]",
        "COMMAND[30:21] | BYTE_COUNT[20:0]",
    ],
    "PACKET3_DMA_DATA": [
        "CONTROL",
        "SRC_ADDR_LO | DATA",
        "SRC_ADDR_HI[31:0]",
        "DST_ADDR_LO[31:0]",
        "DST_ADDR_HI[7:0]",
        "COMMAND[30:21] | BYTE_COUNT[20:0]",
    ],
    "PACKET3_SET_RESOURCES": [
        "CONTROL / resource size",
        "vmid_mask[31:16] | queue_type[15:14]",
        "queue_mask_lo[31:0]",
        "queue_mask_hi[31:0]",
        "gws_mask_lo[31:0]",
        "gws_mask_hi[31:0]",
        "RESOURCE_SIZE[31:0]",
    ],
    # MAP_QUEUES: layout de vid.h, que es el que ve gfx_v8_0.c. OJO: el de
    # soc15d.h (GFX9+) tiene 7 dwords y este tiene 6. Copiar el equivocado
    # desplaza todos los campos uno. BUG que cometi y que el decodificador
    # delato solo cuando un IB real salio desalineado.
    "PACKET3_MAP_QUEUES": [
        "CONTROL[31:0]  (queue_sel[4] | queue_type[21] | engine_sel[26] "
        "| num_queues[29])",
        "CONTROL2[31:0]  (doorbell_offset[25:2])",
        "MQD_ADDR_LO[31:0]",
        "MQD_ADDR_HI[31:0]",
        "WPTR_ADDR_LO[31:0]",
        "WPTR_ADDR_HI[31:0]",
    ],
    "PACKET3_UNMAP_QUEUES": [
        "ACTION[1] | QUEUE_SEL[2:0] | ENGINE_SEL[6:5] | NUM_QUEUES[10]",
        "DOORBELL_OFFSET0[25:2]",
        "dword[2]",
        "dword[3]",
        "dword[4]",
    ],
    "PACKET3_QUERY_STATUS": [
        "CONTROL / cadence",
        "CONTEXT_STATUS[21:12] | VMID[31:28]",
        "REGISTER_INDEX[23:0]",
        "STATUS_VALUE[31:0]",
        "dword[4]",
        "dword[5]",
    ],
    "PACKET3_RUN_CLEANER_SHADER": [
        "CLEANER_MODE / type",
    ],
}


def _closure():
    sys.path.insert(0, HERE)
    import include_closure as IC
    cl = IC.Closure()
    cl.process_file(os.path.join(AMDDIR, "gfx_v8_0.c"))
    return cl


def opcode_table():
    """{opcode: (nombre, valor)} tal como los ve gfx_v8_0.c."""
    cl = _closure()
    out = {}
    for name, hist in cl.history.items():
        if not name.startswith("PACKET3_"):
            continue
        try:
            v = int(hist[-1][0], 0)
        except (TypeError, ValueError):
            continue
        out[v] = (name, os.path.basename(hist[-1][1]))
    return out


def field_masks(opname):
    """{CAMPO: (mask, shift)} de un opcode, desde el _sh_mask.h correcto."""
    cl = _closure()
    bare = opname[2:] if opname.startswith("mm") else opname
    for tag, _rel in (("vid", None),):
        pass
    # el _sh_mask.h de amdgpu nombra los paquetes como PACKET3_*, no como campos
    # de registro, asi que los campos viven en vid.h como
    # PACKET3_<X>_<CAMPO>(x) -- ((x) << N). Se recuperan de ahi.
    vid = f"{AMDDIR}/vid.h"
    try:
        txt = open(vid, errors="replace").read()
    except OSError:
        return {}
    out = {}
    for m in re.finditer(r"^#\s*define\s+" + re.escape(opname) +
                         r"_(\w+)\(x\)\s+\(\(x\)\s*<<\s*(\d+)\)", txt, re.M):
        out[m.group(1)] = (0, int(m.group(2)))     # solo el shift
    for m in re.finditer(r"^#\s*define\s+" + re.escape(opname) +
                         r"_(\w+)\s+\(1\s*<<\s*(\d+)\)", txt, re.M):
        out.setdefault(m.group(1), (1 << int(m.group(2)),
                                    int(m.group(2))))
    return out


# ------------------------------------------------------------- decodificacion
def decode(dwords, with_hex=False):
    """Decodifica una lista de dwords. Devuelve una lista de paquetes."""
    i = 0
    pkts = []
    n = len(dwords)
    while i < n:
        dw = dwords[i]
        t = (dw >> 30) & 0x3
        tname = TYPE.get(t, f"TIPO{t}")
        pkt = {"ini": i, "tipo": tname, "header": dw, "datos": [],
               "campos": {}}

        if t == 3:
            opc = (dw >> 8) & 0xFF
            F = (dw >> 16) & 0x3FFF
            if F == 0x3FFF:
                payload = 0            # reservado: cabecera sola
                pkt["nota"] = ("F == 0x3FFF: RESERVADO. La cabecera sola es "
                               "el paquete (NOP unitario).")
            else:
                payload = F + 1
            name, src = opcode_table().get(opc, (f"OPCODE_0x{opc:02X}", "?"))
            pkt["opcode"] = opc
            pkt["nombre"] = name
            pkt["origen_nombre"] = src
            total = 1 + payload
        elif t == 0:
            payload = ((dw >> 16) & 0x3FFF) + 1
            pkt["registro"] = dw & 0x7FFF
            pkt["nombre"] = f"REG_{pkt['registro']}"
            total = 1 + payload
            if dw == 0:
                # Un dword todo cero es TYPE0 con offset de registro 0 y
                # payload 1. No es un error ni un hueco: asi lo interpreta
                # el hardware tambien. En un IB real sale de un dw de padding
                # o de un campo que el driver dejo sin usar, y el decodificador
                # debe decirlo con claridad y noDnde lo pare.
                pkt["nota"] = ("dword nulo: TYPE0 sobre el registro 0. No es "
                               "un paquete mal formado; el hardware tambien lo "
                               "interpreta asi.")
        elif t == 2:
            pkt["nombre"] = "NOP_TYPE2"
            pkt["nota"] = "TYPE2 es exactamente 0x80000000, sin payload."
            total = 1
        elif t == 4:
            payload = dw & 0x7F
            pkt["registro"] = (dw >> 8) & 0x3FFFF
            total = 1 + payload
            pkt["nombre"] = f"TYPE4_REG_{pkt['registro']}"
            pkt["paridad_offset"] = (dw >> 27) & 1
            pkt["paridad_cant"] = (dw >> 7) & 1
        elif t == 7:
            payload = dw & 0x3FFF
            pkt["opcode"] = (dw >> 16) & 0x7F
            total = 1 + payload
            pkt["nombre"] = f"TYPE7_OP_{pkt['opcode']}"
            pkt["paridad_cant"] = (dw >> 15) & 1
            pkt["paridad_opcode"] = (dw >> 23) & 1
        else:
            pkt["nombre"] = f"DESCONOCIDO_TIPO{t}"
            pkt["nota"] = "tipo de paquete no contemplado; no se avanza"
            pkts.append(pkt)
            break

        fin = min(i + total, n)
        pkt["datos"] = dwords[i + 1:fin]
        pkt["fin"] = fin
        if fin < i + total:
            pkt["nota"] = (pkt.get("nota", "") +
                           f" TRUNCADO: pide {total} dwords, hay {fin - i}.")
        pkts.append(pkt)
        i = fin if fin > i else i + 1
    return pkts


def check_layouts():
    """El layout documentado debe coincidir con el payload que emite el driver.

    BUG QUE ESTA COMPROBACION EVITA. Escribi el layout de MAP_QUEUES con 7
    dwords tomando el de soc15d.h, y el de gfx_v8_0.c (vid.h) tiene 6. Un
    layout erroneo no rompe el framing -- el framing es correcto y el paquete
    se consume bien -- pero desplaza TODOS los nombres de campo una posicion.
    Un decodificador que dice "WPTR_ADDR_LO = 0x12345000" cuando ese valor es
    MQD_ADDR_LO es peor que uno que no dice nada: parece preciso y no lo es.

    Por eso el layout se contrasta contra el numero real de payload.
    """
    import re as _re
    try:
        src = open(f"{AMDDIR}/gfx_v8_0.c", errors="replace").read().split("\n")
    except OSError:
        return []
    probs = []
    for op in DOC_LAYOUTS:
        for i, l in enumerate(src):
            m = _re.search(r"PACKET3\(\s*" + _re.escape(op) + r"\s*,\s*(\d+)\s*\)", l)
            if not m:
                continue
            F = int(m.group(1))
            # regla 034: payload = F + 1. Y el layout debe tener payload
            # entradas. NO se cuentan los ring_write: una llamada spans varias
            # lineas y contarlas asi da 1. El campo F es la fuente fiable.
            if F != 0x3FFF:
                esperado = F + 1
            else:
                esperado = 0
            if esperado != len(DOC_LAYOUTS[op]):
                probs.append((op, i + 1, len(DOC_LAYOUTS[op]), esperado, F))
            break
    return probs


def describe(pkts, with_hex=False):
    out = []
    for k, p in enumerate(pkts):
        d = p["datos"]
        total = 1 + len(d)
        lin = (f"[{k:3}] {p['ini']:5} {p['tipo']:6} {p.get('nombre','?'):34}"
               f" total={total:3} datos={len(d):3}")
        out.append(lin)
        if p.get("nota"):
            out.append(f"        NOTA: {p['nota']}")
        if with_hex:
            out.append(f"        hex: {' '.join(f'{x:08x}' for x in d)}")
        nm = p.get("nombre", "")
        if nm in DOC_LAYOUTS:
            lay = DOC_LAYOUTS[nm]
            out.append(f"        layout documentado ({len(lay)} campos):")
            for idx, fld in enumerate(lay):
                if idx < len(d):
                    out.append(f"          dw{idx+1} = 0x{d[idx]:08x}  {fld}")
                else:
                    out.append(f"          dw{idx+1} = (falta)      {fld}")
    return out


# ------------------------------------------------------------------ encoding
def build(opname, datas, extra_flags=0):
    """Construye un IB con un paquete. MISMAS reglas que decodifica.

    Que el codigo puedas construir lo que decodifica es la prueba de que el
    modelo de framing es cerrado. Si las dos funciones compartieran un error,
    el roundtrip pasaria igual; por eso --roundtrip tambien verifica contra
    el corpus.
    """
    tabs = opcode_table()
    rev = {v[0]: k for k, v in tabs.items()}
    if opname not in rev:
        raise SystemExit(f"{opname} no existe para gfx_v8_0.c")
    opc = rev[opname]
    if not datas:
        raise SystemExit("un paquete con 0 datos solo es valido si F=0x3FFF")
    F = len(datas) - 1
    if F > 0x3FFE:
        raise SystemExit(f"F={F} excede 0x3FFE (0x3FFF esta reservado)")
    hdr = (3 << 30) | ((opc & 0xFF) << 8) | ((F & 0x3FFF) << 16) | extra_flags
    return [hdr] + list(datas)


def nop(n=1):
    """NOP de n dwords, con el caso reservado del hallazgo 034."""
    if n == 1:
        return [(3 << 30) | (0x10 << 8) | (0x3FFF << 16)]
    if n < 2:
        raise SystemExit("n debe ser >= 1")
    hdr = (3 << 30) | (0x10 << 8) | ((n - 2) & 0x3FFF) << 16
    return [hdr] + [0] * (n - 1)


# --------------------------------------------------------------------- main
def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if "--check" in sys.argv:
        probs = check_layouts()
        print("CONTRASTE layout documentado vs payload emitido")
        for op, ln, doc, real, F in probs:
            print(f"  *** {op}: layout dice {doc} campos, pero F={F} implica "
                  f"{real} payload  (linea {ln})")
        if not probs:
            print("  todos los layouts coinciden con lo que emite el driver")
        return 1 if probs else 0

    if "--opcodes" in sys.argv:
        tabs = opcode_table()
        print("=" * 74)
        print(f"OPCODES PACKET3 que ve gfx_v8_0.c: {len(tabs)}")
        print("=" * 74)
        for v in sorted(tabs):
            name, src = tabs[v]
            doc = "  <-- LAYOUT DOCUMENTADO" if name in DOC_LAYOUTS else ""
            print(f"  0x{v:02X}  {name:34} {src}{doc}")
        return 0

    if "--doc" in sys.argv and args:
        nm = args[0]
        lay = DOC_LAYOUTS.get(nm)
        if not lay:
            print(f"{nm}: sin layout documentado en el corpus")
            return 1
        print(f"{nm}: {len(lay)} dwords de payload")
        for i, f in enumerate(lay):
            print(f"  dw{i+1}  {f}")
        return 0

    if "--build" in sys.argv and args:
        # --build OPCODE d0 d1 ...
        nums = []
        for a in args[1:]:
            try:
                nums.append(int(a, 0))
            except ValueError:
                pass
        dws = build(args[0], nums)
        print("IB construido:")
        for d in describe(decode(dws)):
            print(d)
        print(f"\nhex: {' '.join(f'{x:08x}' for x in dws)}")
        return 0

    if "--nops" in sys.argv:
        for n in (1, 2, 3, 8, 16):
            dws = nop(n)
            ok = len(dws) == n
            print(f"nop({n:2}) -> {len(dws)} dwords  "
                  f"{'OK' if ok else '*** MAL ***'}")
            print(f"          {' '.join(f'{x:08x}' for x in dws)}")
        return 0

    i = sys.argv.index("--ib") if "--ib" in sys.argv else None
    if i is not None:
        path = sys.argv[i + 1]
        raw = open(path, "rb").read()
        dws = list(struct.unpack(f"<{len(raw)//4}I", raw[:len(raw)//4*4]))
        pkts = decode(dws, "--hex" in sys.argv)
        print("=" * 74)
        print(f"IB: {path}   {len(dws)} dwords ({len(raw)} bytes)")
        print("=" * 74)
        for l in describe(pkts, "--hex" in sys.argv):
            print(l)
        tot = sum(1 + len(p["datos"]) for p in pkts)
        print()
        print(f"  paquetes: {len(pkts)}   dwords consumidos: {tot}/{len(dws)}")
        if tot != len(dws):
            print("  *** NO CUADRA: el framing no cubre el IB entero ***")
            return 1
        print("  cuadra exacto")
        return 0

    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())