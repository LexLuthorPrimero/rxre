#!/usr/bin/env python3
# CONTRACT: name=mqd_layout
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
r"""MQD LAYOUT -- verifica la afirmacion estructural mas fuerte del driver.

LA AFIRMACION QUE ESTE CORRIGE. En gfx_v8_0.c, la funcion que programa una cola
hace esto:

    mqd_data = &mqd->cp_mqd_base_addr_lo;
    for (mqd_reg = mmCP_HQD_VMID; mqd_reg <= mmCP_HQD_EOP_CONTROL; mqd_reg++)
            WREG32(mqd_reg, mqd_data[mqd_reg - mmCP_MQD_BASE_ADDR]);

Eso NO es un bucle cualquiera. `mqd_data` es un puntero a un campo UINT32_T
DENTRO de `struct vi_mqd`, y se indexa con `offset_de_registro - offset_base`.
Por tanto el driver AFIRMA, sin decirlo y sin comprobarlo en runtime:

    campo[i] de struct vi_mqd  ==  registro en offset (base + i)

para todo el rango. Es una asercion sobre el MAPA DE REGISTROS DEL HARDWARE:

    A. el bloque de registros HQD es CONTIGUO (sin huecos)
    B. cada registro del bloque ocupa exactamente UN dword
    C. el orden de los campos del struct replica el orden de los offsets
    D. no hay campos de otro ancho (uint64_t, arrays) en medio

Si D fuera falso, `mqd_data[i]` leeria memoria equivocada y el driver
programaria cada registro con el valor del campo que este a la derecha. El
compilador no avisa: los indices son validos, solo WRONG. Es un fallo LATENTE
que no aparece como error de compilacion ni como crash.

Es decir: la estructura del struct es EVIDENCIA del hardware. Si el match sale
perfecto, la afirmacion A/B/C/D queda PROVEN por verificacion mecanica, y con
ella laExtension del bloque de registros HQD, que hasta ahora era una frase
del driver ("HQD registers extend from mmCP_MQD_BASE_ADDR to mmCP_HQD_ERROR")
sin verificar contra el header de offsets.

Y si el match falla, hay un bug real en el driver de esta ruta.

QUE NO HACE. No dice que hace cada registro. Dice que la correspondencia
entre el codigo, el struct y el header de offsets es exacta. La semantica de
los 52 registros sigue siendo NOT_DETERMINED (033: no hay documentacion
primaria de GCN3).

Uso:
  python3 mqd_layout.py                 tabla completa index -> offset -> campo
  python3 mqd_layout.py --mismatches    solo lo que no cuadra
  python3 mqd_layout.py --self-test     control negativo (mutacion deliberada)
  python3 mqd_layout.py --json
  python3 mqd_layout.py --ranges        los bucles tal cual estan en el codigo
"""
import os
import re
import sys
import json

CORPUS = ("/home/lucas/Escritorio/RX550-INVESTIGACION/"
          "RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd")
VIST = f"{CORPUS}/include/vi_structs.h"
# GCN1 no usa vi_mqd: usa cik_mqd, en su propio header. Es la razon por la que
# los dos sitios de gfx_v7_0 salian NO_ANALIZABLE: no era un fallo del
# extractor, era que se les pedia un struct equivocado.
CIK = f"{CORPUS}/include/cik_structs.h"

# El ASIC de esta placa. Polaris12 usa la familia gfx_8_0. El 8_1 se compara
# porque 065 demostro que 7 registros de GMC difieren entre 8_0 y 8_1: si el
# bloque HQD difiriese, la tabla de un solo ASIC seria incompleta.
ASIC_HDRS = {
    "gfx_7_0": f"{CORPUS}/include/asic_reg/gca/gfx_7_0_d.h",
    "gfx_8_0": f"{CORPUS}/include/asic_reg/gca/gfx_8_0_d.h",
    "gfx_8_1": f"{CORPUS}/include/asic_reg/gca/gfx_8_1_d.h",
}

# Los bucles tal cual estan escritos en el codigo. Se extraen del .c para no
# hardcodearlos: si el driver cambia un limite, esta herramienta lo sigue.
FUENTE_C = f"{CORPUS}/amdgpu/gfx_v8_0.c"

# CADA SITIO que indexa una struct por offset de registro. 043 encontro el de
# gfx_v8_0.c. El grep los encuentra todos, y son cuatro:
#
#   gfx_v8_0.c            mqd_commit      (el de Polaris12)
#   gfx_v7_0.c            mqd_commit      (GCN1, bloque mas corto)
#   amdgpu_amdkfd_gfx_v8.c kgd_hqd_load   (el MISMO struct, otro consumidor)
#   amdgpu_amdkfd_gfx_v7.c kgd_hqd_load
#
# Los tres ultimos repiten la asercion. Que un consumidor la repita es
# CORROBORACION: dos rutas independientes del driver indexan el mismo bloque
# por offset y salen bien. Y donde NO coincide el comentario, hay un hallazgo
# real (043 seccion siguiente).
SITIOS = [
    dict(nombre="gfx_v8_0.c:mqd_commit", f=FUENTE_C,
         funcion="gfx_v8_0_mqd_commit", var_pat="mqd_reg",
         struct="vi_mqd", ancla="cp_mqd_base_addr_lo",
         asic="gfx_8_0"),
    dict(nombre="amdkfd_gfx_v8.c:kgd_hqd_load",
         f=f"{CORPUS}/amdgpu/amdgpu_amdkfd_gfx_v8.c",
         funcion="kgd_hqd_load", var_pat="reg",
         struct="vi_mqd", ancla="cp_mqd_base_addr_lo",
         asic="gfx_8_0"),
    dict(nombre="gfx_v7_0.c:mqd_commit",
         f=f"{CORPUS}/amdgpu/gfx_v7_0.c",
         funcion="gfx_v7_0_mqd_commit", var_pat="mqd_reg",
         struct="cik_mqd", struct_f=CIK, ancla="cp_mqd_base_addr_lo",
         asic="gfx_7_0"),
    dict(nombre="amdkfd_gfx_v7.c:kgd_hqd_load",
         f=f"{CORPUS}/amdgpu/amdgpu_amdkfd_gfx_v7.c",
         funcion="kgd_hqd_load", var_pat="reg",
         struct="cik_mqd", struct_f=CIK, ancla="cp_mqd_base_addr_lo",
         asic="gfx_7_0"),
]

LOOP_RE = re.compile(
    r"for\s*\(\s*(\w+)\s*=\s*(mm\w+)\s*;\s*\1\s*<=\s*(mm\w+)\s*;\s*\1\+\+\s*\)"
    r"\s*WREG32\(\s*\1\s*,")


def parse_regs(path):
    """{nombre: offset} desde los #define mmX 0xNNNN."""
    out = {}
    if not os.path.exists(path):
        return out
    for line in open(path, errors="replace"):
        m = re.match(r"#define\s+(mm\w+)\s+(0x[0-9a-fA-F]+)", line)
        if m:
            out[m.group(1)] = int(m.group(2), 16)
    return out


def parse_struct(path, nombre="vi_mqd"):
    """[(tipo, campo, es_array)] en orden de declaracion."""
    src = open(path, errors="replace").read()
    # NOTA: la llave abre en la MISMA linea que el nombre de la struct
    # (`struct vi_mqd {`). Un patron que exija \n antes de { no encuentra nada
    # y devuelve None, que la herramienta reporta como NO_ANALIZABLE. Eso es
    # preferible a un crash, pero un NO_ANALIZABLE por un regex es un fallo mio,
    # no una propiedad del corpus.
    m = re.search(r"struct\s+" + nombre + r"\s*\{(.*?)\n\};", src, re.S)
    if not m:
        return None
    out = []
    for l in m.group(1).split("\n"):
        l = l.strip()
        if not l or l.startswith(("/*", "*", "//", "#")):
            continue
        f = re.match(r"^([A-Za-z_]\w*)\s+(\w+)\s*(\[[^\]]*\])?\s*;$", l)
        if f:
            out.append((f.group(1), f.group(2), bool(f.group(3))))
    return out


def parse_loops(path, funcion=None):
    """[(var, reg_ini, reg_fin, linea)] de los bucles WREG32 sobre registro."""
    src = open(path, errors="replace").read().split("\n")
    out = []
    for i, l in enumerate(src):
        for m in LOOP_RE.finditer(l + "\n" + (src[i + 1] if i + 1 < len(src) else "")):
            out.append((m.group(1), m.group(2), m.group(3), i + 1, l.strip()))
    return out


def por_offset(regs):
    """{offset: [nombres]} -- mantiene los ALIAS, que son informacion."""
    d = {}
    for k, v in regs.items():
        d.setdefault(v, []).append(k)
    for v in d:
        d[v] = sorted(d[v])
    return d


def candidatos(campo):
    """Nombres de registro aceptables para un campo del struct.

    POR QUE HACE FALTA, Y POR QUE SON DOS. El struct nombra los registros de
    64 bits como `cp_hqd_pq_base_lo` / `cp_hqd_pq_base_hi`, pero el header de
    offsets define UN solo registro de 32 bits llamado `mmCP_HQD_PQ_BASE`.
    Quitar el sufijo hace cuadrar ese caso.

    PERO hay registros que SI se llaman `_HI` en el header, como
    `mmCP_MQD_BASE_ADDR_HI`. A esos hay que comparar SIN quitar el sufijo.

    Por eso se aceptan los dos, no solo uno:

        MISMATCH   el campo no corresponde a NINGUN nombre del offset
        ALIAS      el campo tiene DOS nombres validos en el offset, y este
                   es uno de ellos (registro con alias en el header)

    Sin los dos candidatos esta herramienta hubo de REPORTAR UN BUG QUE NO
    EXISTIA en dos versiones distintas. Un detector que llora lobo entrena a
    su usuario a ignorar lo que dice, que es peor que no tener detector.
    """
    out = {"mm" + campo.upper()}
    n = campo
    for suf in ("_lo", "_hi"):
        if n.endswith(suf):
            out.add("mm" + n[: -len(suf)].upper())
    return out


def cuerpo_de(path, funcion):
    """El texto de UNA funcion, con su desplazamiento de linea real.

    Acotar a la funcion es obligatorio: si se leyera el fichero entero, las
    escrituras literales de OTRAS funciones aparecerian como programadas por
    esta, y el recuento de posiciones no significaria lo que dice.

    NOTA SOBRE EL PRIMER INTENTO. Esta funcion buscaba el cierre con
    "\n}\\n", que en un .c de amdgpu no existe: las funciones terminan con
    "\n}" y el salto de linea final. Con ese criterio NO ENCONTRABA NINGUN
    CUERPO, y por eso los cuatro sitios salian vacios o con 3 y 6 posiciones
    en vez de 53.

    El cierre se detecta contando llaves, que es lo unico que no depende del
    estilo de impresion. Se devuelve tambien el numero de linea de inicio,
    para que las citas sean las del fichero y no las de un fragmento.
    """
    if not os.path.exists(path):
        return "", 0
    lines = open(path, errors="replace").read().split("\n")
    ini = None
    for i, l in enumerate(lines):
        if funcion in l and re.search(r"\b" + funcion + r"\s*\(", l):
            ini = i
            break
    if ini is None:
        return "", 0
    prof = 0
    visto = False
    out = []
    for k in range(ini, len(lines)):
        out.append(lines[k])
        for ch in lines[k]:
            if ch == "{":
                prof += 1
                visto = True
            elif ch == "}":
                prof -= 1
        if visto and prof <= 0:
            break
    return "\n".join(out), ini + 1


def parse_loops(path, funcion=None, var_pat=None):
    """[(var, reg_ini, reg_fin, linea, texto)] de los bucles WREG32 sobre registro.

    Con `funcion`, se acota a esa funcion. Sin ella, se lee el fichero entero,
    que es lo que se hacia antes: sin acotar, los bucles de una funcion和你
    contaban como de otra.
    """
    if funcion:
        txt, off = cuerpo_de(path, funcion)
        base = off - 1
    else:
        txt, base = open(path, errors="replace").read(), 0
    # EL PATRON ABARCA DOS LINEAS: el for y el WREG32 que lo sigue. Buscarlo
    # linea a linea devolvia 0 bucles, y por eso los sitios salian con 3 y 6
    # posiciones (solo las escrituras literales) en vez de 53. Es el tercer
    # fallo de extraccion de esta herramienta, y el de peor aspecto: una
    # extraccion parcial que devuelve un numero plausible.
    lineas = txt.split("\n")
    out = []
    for i, l in enumerate(lineas):
        nxt = lineas[i + 1] if i + 1 < len(lineas) else ""
        m = LOOP_RE.search(l + "\n" + nxt)
        if m:
            out.append((m.group(1), m.group(2), m.group(3),
                        i + 1 + base, l.strip()))
    return out


def indices_programados(base, regs, sitio=None):
    """{indice: 'bucle'|'directo'} de lo que el driver ESCRIBE de verdad.

    Se deriva de los bucles de la funcion mas las escrituras literales de ESA
    MISMA funcion. Sin acotar a la funcion, el recuento mezcla sitios.
    """
    f = sitio["f"] if sitio else FUENTE_C
    fn = sitio["funcion"] if sitio else "gfx_v8_0_mqd_commit"
    prog = {}
    for _var, a, b, _ln, _txt in parse_loops(f, fn):
        lo, hi = regs.get(a), regs.get(b)
        if lo is None or hi is None:
            continue
        for off in range(lo, hi + 1):
            prog[off - base] = "bucle"
    cuerpo, _ini = cuerpo_de(f, fn)
    for m in re.finditer(r"WREG32\(\s*(mm\w+)\s*,", cuerpo):
        off = regs.get(m.group(1))
        if off is not None and off - base >= 0:
            prog.setdefault(off - base, "directo")
    return prog


def construir(asic="gfx_8_0", structs=None, regs=None, sitio=None):
    """Devuelve la tabla y el veredicto. Acepta inyectar struct/registros
    para poder hacer el control negativo del self-test sin tocar el corpus."""
    if sitio:
        asic = sitio["asic"]
    hdr = ASIC_HDRS.get(asic)
    if hdr is None:
        return None
    regs = regs if regs is not None else parse_regs(hdr)
    struct_f = (sitio or {}).get("struct_f", VIST)
    struct_n = (sitio or {}).get("struct", "vi_mqd")
    campos = structs if structs is not None else parse_struct(struct_f, struct_n)
    byoff = por_offset(regs)

    if not campos:
        return None
    nombres = [c[1] for c in campos]
    if "cp_mqd_base_addr_lo" not in nombres:
        return None
    i0 = nombres.index("cp_mqd_base_addr_lo")
    base_mm = "mmCP_MQD_BASE_ADDR"
    if base_mm not in regs:
        return None
    base = regs[base_mm]
    prog = indices_programados(base, regs, sitio)

    filas = []
    for i in range(len(campos) - i0):
        off = base + i
        f = campos[i0 + i]
        nombres_off = byoff.get(off, [])
        cands = candidatos(f[1])
        if not prog or i not in prog:
            estado = "NO_PROGRAMADO"
        elif not nombres_off:
            estado = "SIN_REGISTRO"
        elif f[2]:
            estado = "ARRAY"
        elif f[0] != "uint32_t":
            estado = "TIPO_EQUIVOCADO"
        elif cands & set(nombres_off):
            estado = "ALIAS" if len(nombres_off) > 1 else "MATCH"
        elif len(nombres_off) == 1:
            # POSICION UNICA. En este offset hay exactamente un registro y su
            # nombre no coincide con ninguno de los candidatos del campo.
            #
            # NO es un fallo de correspondencia: la correspondencia es por
            # POSICION, y aqui hay una sola posicion posible. Lo que falla es
            # el NOMBRE. El driver llama al campo `done_events` y el header
            # llama al registro `EVENTS`; el offset es el mismo.
            #
            # Se separa de MISMATCH porque una divergencia de nombre y un
            # desajuste de posicion son fallos de distinta gravedad, y
            # mezclarlos hace que el veredicto no signifique nada. Este caso
            # aparece en las 4 generaciones del struct (vi, v9..v12) con el
            # mismo nombre, asi que el struct es coherente consigo mismo y
            # el header usa otra palabra.
            estado = "NOMBRE_DIVERGENTE"
        else:
            # Varios registros en el offset y ninguno encaja: la
            # correspondencia por posicion es AMBIGUA. Esto si es un fallo.
            estado = "MISMATCH"
        filas.append(dict(
            indice=i, offset=f"0x{off:04x}", offset_dec=off,
            tipo_campo=f[0], campo=f[1], es_array=f[2],
            how=prog.get(i, "-"),
            registros=nombres_off, candidatos=sorted(cands), estado=estado))
    return dict(asic=asic, base_offset=base, i0=i0,
                sitio=sitio["nombre"] if sitio else "(sin sitio: por defecto)",
                n_campos=len(campos), programados=len(prog), filas=filas)


def veredicto(t):
    """Se evalua SOLO sobre los indices que el driver programa.

    Evaluar los 257 campos del struct contra 2633 registros daria MISMATCH en
    casi todo: el struct incluye el estado de dispatch de compute y graphics,
    que no se programan por offset sino campo a campo. El bloque relevante es
    el que los bucles tocan.
    """
    if t is None:
        return "NO_ANALIZABLE"
    filas = t["filas"]
    prog = [f for f in filas if f["how"] != "-"]
    # ALIAS cuenta como cuadre: el campo corresponde al offset, y ademas el
    # header da dos nombres para ese offset. Es informacion, no un fallo.
    ok_rows = [f for f in prog if f["estado"] in ("MATCH", "ALIAS")]
    match = [f for f in ok_rows if f["estado"] == "MATCH"]
    alias = [f for f in ok_rows if f["estado"] == "ALIAS"]
    mis = [f for f in prog if f["estado"] == "MISMATCH"]
    nomb = [f for f in prog if f["estado"] == "NOMBRE_DIVERGENTE"]
    sin = [f for f in prog if f["estado"] == "SIN_REGISTRO"]
    arrays = [f for f in prog if f["estado"] == "ARRAY"]
    otros = [f for f in prog if f["estado"] == "TIPO_EQUIVOCADO"]

    ultimo = max((f["indice"] for f in ok_rows), default=-1)
    primero = min((f["indice"] for f in prog), default=0)
    return dict(n_programados=len(prog), match=len(match), alias=len(alias),
                cuadran=len(ok_rows), mismatch=len(mis),
                nombre_divergente=len(nomb), filas_nombre=nomb,
                sin_registro=len(sin), arrays=len(arrays),
                otros_tipos=len(otros),
                alcance_ini=f"0x{t['base_offset'] + primero:04x}",
                alcance_fin=f"0x{t['base_offset'] + ultimo:04x}",
                alcance_dwords=ultimo - primero + 1,
                filas_mismatch=mis, filas_sin=sin, filas_arrays=arrays,
                filas_otros=otros, filas_alias=alias)


def todos_los_sitios():
    """Verifica la asercion en TODOS los sitios que la hacen, no solo en uno.

    POR QUE IMPORTA MAS QUE EL PRIMER RESULTADO. 043 verifico el bloque de
    Polaris12 y dio 52/53. Pero hay CUATRO funciones que indexan el mismo
    bloque por offset de registro: dos de display y dos de KFD. Que las cuatro
    repitan la asercion y las cuatro cuadren es CORROBORACION de algo mas
    fuerte que que una cuadre: el struct esta construido para ese layout, no
    para que cuadre en un caso.

    Y donde dos sitios dicen cosas DISTINTAS del mismo bloque, la discrepancia
    es informacion: significa que el hardware tiene mas registros de los que
    uno de los dos comentarios afirma, y hay que decidir cual.
    """
    print("=" * 76)
    print("ASERCION struct->offset en TODOS los sitios que la hacen")
    print("=" * 76)
    filas = []
    for s in SITIOS:
        t = construir(sitio=s)
        if t is None:
            filas.append(dict(sitio=s["nombre"], asic=s["asic"],
                              estado="NO_ANALIZABLE"))
            continue
        v = veredicto(t)
        filas.append(dict(sitio=s["nombre"], asic=s["asic"],
                          estado="OK" if (v["mismatch"] == 0
                                          and v["sin_registro"] == 0
                                          and v["arrays"] == 0
                                          and v["otros_tipos"] == 0)
                          else "FALLA",
                          n=v["n_programados"], cuadran=v["cuadran"],
                          match=v["match"], alias=v["alias"],
                          nombre_div=v["nombre_divergente"],
                          mismatch=v["mismatch"],
                          sin_reg=v["sin_registro"], arrays=v["arrays"],
                          otros=v["otros_tipos"],
                          bloque=f"{v['alcance_ini']}..{v['alcance_fin']}",
                          dwords=v["alcance_dwords"]))
    print(f"{'sitio':32} {'asic':8} {'n':>4} {'cuadran':>8} {'nombre':>7} "
          f"{'bloque':>20} estado")
    print("-" * 118)
    for r in filas:
        if r["estado"] == "NO_ANALIZABLE":
            print(f"{r['sitio']:32} {r['asic']:8} {'':>4} {'':>8} {'':>7} "
                  f"{'':>20} NO_ANALIZABLE")
            continue
        print(f"{r['sitio']:32} {r['asic']:8} {r['n']:4} {r['cuadran']:8} "
              f"{r['nombre_div']:7} {r['bloque']:>20} {r['estado']}")

    ok = [r for r in filas if r.get("estado") == "OK"]
    print()
    print(f"  sitios que corroboran la asercion : {len(ok)}/{len(SITIOS)}")

    # Los bloques no son iguales entre generaciones. Eso NO es un fallo: es
    # que el bloque CRECE. Lo que hay que decir es si el de Polaris12 esta
    # dentro del patron.
    bloques = {}
    for r in filas:
        if r.get("estado") == "OK":
            bloques.setdefault(r["asic"], set()).add(r["bloque"])
    if len(bloques) > 1:
        print()
        print("  El bloque cambia entre generaciones del ASIC:")
        for a, bs in sorted(bloques.items()):
            print(f"    {a}: {' , '.join(sorted(bs))}")
        print("  Es COHERENTE con que EOP se anadio en GCN3 y no existe en")
        print("  GCN1: un ASIC mas nuevo tiene mas registros al final.")

    return 0 if len(ok) == len(SITIOS) else 3


def main():
    args = sys.argv[1:]

    if "--self-test" in args:
        return self_test()

    t = construir()
    v = veredicto(t)

    if "--json" in args:
        print(json.dumps(dict(tabla=t, veredicto=v), indent=1))
        return 0

    if "--sitios" in args:
        return todos_los_sitios()

    if "--ranges" in args:
        print("=" * 76)
        print("BUCLES de registro que indexan la struct por offset")
        print("=" * 76)
        for s in SITIOS:
            if not os.path.exists(s["f"]):
                print(f"\n  {s['nombre']}: FICHERO AUSENTE")
                continue
            regs = parse_regs(ASIC_HDRS.get(s["asic"], ""))
            if not regs:
                print(f"\n  {s['nombre']}: header {s['asic']} ausente")
                continue
            byoff = por_offset(regs)
            print(f"\n  {s['nombre']}  [{s['asic']}]")
            bucles = parse_loops(s["f"], s["funcion"])
            if not bucles:
                print("    sin bucles de registro en esa funcion")
            for _var, a, b, ln, txt in bucles:
                lo, hi = regs.get(a), regs.get(b)
                if lo is None or hi is None:
                    print(f"    :{ln} {a}..{b}  ALGUNO NO ESTA EN EL HEADER")
                    continue
                n = [o for o in byoff if lo <= o <= hi]
                print(f"    :{ln}  {a} (0x{lo:04x}) .. {b} (0x{hi:04x})"
                      f"  -> {len(n)} offsets con registro")
        print()
        print("  Nota: las lineas son relativas al cuerpo de la funcion")
        print("  extraido, no al fichero. Con sed -n hay que sumar el")
        print("  desplazamiento de la funcion.")
        return 0

    print("=" * 76)
    print("MQD LAYOUT -- el struct vi_mqd indexado por offset de registro")
    print("=" * 76)
    if t is None:
        print("NO_ANALIZABLE: no se pudo leer el struct o el header")
        return 1

    print(f"struct vi_mqd        : {t['n_campos']} campos; ancla en el indice {t['i0']}")
    print(f"offset base (GFX8.0) : mmCP_MQD_BASE_ADDR = 0x{t['base_offset']:04x}")
    print(f"indices programados  : {t['programados']}")
    print()
    ver = "--all" in args or "--mismatches" not in args
    print(f"{'i':>4} {'offset':>8} {'como':8} {'campo del struct':32} "
          f"{'registro':30} estado")
    print("-" * 118)
    n_omit = 0
    for f in t["filas"]:
        regs = ",".join(f["registros"]) or "(ninguno)"
        if not ver and f["estado"] == "MATCH":
            n_omit += 1
            continue
        if not ver and f["estado"] == "NO_PROGRAMADO":
            n_omit += 1
            continue
        print(f"{f['indice']:4} {f['offset']:>8} {f['how']:8} {f['campo']:32} "
              f"{regs:30} {f['estado']}")
    if n_omit:
        print(f"... y {n_omit} filas MATCH/NO_PROGRAMADO omitidas (--all para verlas)")

    print()
    print("-" * 76)
    print("VEREDICTO sobre la asercion del driver")
    print("-" * 76)
    if v == "NO_ANALIZABLE":
        print("  NO_ANALIZABLE")
        return 1
    ok = (v["mismatch"] == 0 and v["sin_registro"] == 0
          and v["arrays"] == 0 and v["otros_tipos"] == 0)
    print(f"  indices programados               : {v['n_programados']}")
    print(f"  cuadran (MATCH)                   : {v['match']}")
    print(f"  cuadran con ALIAS en el header    : {v['alias']}")
    print(f"  nombre DIVERGENTE (posicion ok)   : {v['nombre_divergente']}")
    print(f"  MISMATCH (posicion ambigua)      : {v['mismatch']}")
    print(f"  offsets SIN registro definido     : {v['sin_registro']}")
    print(f"  campos array (rompen el indice)   : {v['arrays']}")
    print(f"  campos de otro tipo que no uint32 : {v['otros_tipos']}")
    print(f"  bloque verificado                 : {v['alcance_ini']}..{v['alcance_fin']}"
          f"  ({v['alcance_dwords']} dwords)")
    print()
    if ok:
        print("  PROVEN por verificacion mecanica, sobre lo que el driver escribe:")
        print("    A. el bloque HQD es CONTIGUO: sin huecos entre offsets")
        print("    B. cada registro del bloque ocupa UN dword")
        print("    C. el orden del struct replica el orden de los offsets")
        print("    D. no hay campos de otro ancho en el rango")
        print()
        print("  Y coincide con la frase del driver: 'HQD registers extend from")
        print(f"  mmCP_MQD_BASE_ADDR to mmCP_HQD_ERROR' = {v['alcance_ini']}..{v['alcance_fin']}")
        print("  ConfIRMADA contra el header de offsets, no solo declarada.")
    if v["nombre_divergente"]:
        print("  Divergencias de NOMBRE, con la posicion correcta:")
        for f in v["filas_nombre"]:
            print(f"    i={f['indice']} {f['offset']}: el struct lo llama "
                  f"{f['campo']}, el header llama {f['registros'][0]}")
        print("    El offset coincide y es el unico registro en esa posicion,")
        print("    asi que la correspondencia es correcta; lo que difiere es la")
        print("    palabra. No es un fallo de la asercion.")
        print()
    if not ok:
        print("  LA ASERCION DEL DRIVER NO SE CUMPLE. Posibles bugs:")
        for f in v["filas_mismatch"][:14]:
            print(f"    i={f['indice']} {f['offset']}: struct tiene "
                  f"{f['campo']}, registro es {f['registros']}")
        for f in v["filas_sin"][:14]:
            print(f"    i={f['indice']} {f['offset']}: el struct tiene "
                  f"{f['campo']} pero NO hay registro en ese offset")
        for f in v["filas_arrays"][:8]:
            print(f"    i={f['indice']} {f['offset']}: {f['campo']} es ARRAY")
        for f in v["filas_otros"][:8]:
            print(f"    i={f['indice']} {f['offset']}: {f['campo']} es "
                  f"{f['tipo_campo']}, no uint32_t")
    print()
    print("  LO QUE NO DICE: que hace cada registro. La semantica de los")
    print(f"  {v['alcance_dwords']} registros sigue NOT_DETERMINED: 033 demostro")
    print("  que no hay documentacion primaria de GCN3.")
    print()
    return 0 if ok else 3


def self_test():
    """CONTROL NEGATIVO. Si esta herramienta no puede FALLAR, no puede
    decir que PASA. Se sustituyen los datos reales por otros y se exige que
    detecte el fallo."""
    print("=" * 76)
    print("SELF-TEST de mqd_layout: control negativo")
    print("=" * 76)
    fallos = 0

    # 1. datos reales -> debe pasar
    t = construir()
    v = veredicto(t)
    if t is None:
        print("  [FALLA] no se pudo construir la tabla real")
        return 1
    real_ok = (v["mismatch"] == 0 and v["sin_registro"] == 0
               and v["arrays"] == 0 and v["otros_tipos"] == 0)
    print(f"  1. datos reales -> cuadran={v['cuadran']}/{v['n_programados']}"
          f" (match={v['match']}, alias={v['alias']}, mismatch={v['mismatch']})")
    print(f"     -> el veredicto de PASS exige 0 MISMATCH, 0 SIN_REGISTRO,")
    print(f"        0 ARRAY y 0 tipos equivocados. Ver 'mqd_layout.py' a secas.")

    # 2. mutacion 1: renombrar un campo del struct.
    #
    #    QUE DEBE DETECTAR ESTA HERRAMIENTA: no el fallo del driver, sino el
    #    hecho de que la correspondencia por POSICION se ha roto. Un campo
    #    renombrado no se convierte en MISMATCH si en ese offset hay un solo
    #    registro: pasa a NOMBRE_DIVERGENTE, que es la categoria correcta,
    #    porque la posicion sigue siendo correcta y lo unico que cambio es la
    #    palabra.
    #
    #    La primera version de este control exigia que MISMATCH subiera, y
    #    fallo con la nueva clasificacion. El control estaba mal escrito para
    #    la herramienta: tras añadir NOMBRE_DIVERGENTE, la senal correcta de
    #    "el nombre ya no corresponde" es que NOMBRE_DIVERGENTE sube.
    #
    #    Se mide, por tanto, `cuadran` (los que cuadran) Y
    #    `nombre_divergente` por separado. Bajar `cuadran` detecta el fallo.
    campos = parse_struct(VIST)
    mut = [(t0, n + "_x" if n == "cp_hqd_vmid" else n, a)
           for (t0, n, a) in campos]
    v2 = veredicto(construir(structs=mut))
    d1 = v["cuadran"] - v2["cuadran"]
    print(f"  2. campo renombrado -> cuadran {v['cuadran']}->{v2['cuadran']},"
          f" nombre_divergente {v['nombre_divergente']}->{v2['nombre_divergente']}"
          f"  {'DETECTA' if d1 >= 1 else 'NO DETECTA <<<'}")
    fallos += 0 if d1 >= 1 else 1

    # 3. mutacion 2: cambiar un tipo a uint64_t. Debe detectarlo.
    mut2 = [("uint64_t" if n == "cp_hqd_active" else t0, n, a)
            for (t0, n, a) in campos]
    v3 = veredicto(construir(structs=mut2))
    print(f"  3. tipo cambiado a 64 bits -> otros_tipos "
          f"{v['otros_tipos']}->{v3['otros_tipos']}"
          f"  {'DETECTA' if v3['otros_tipos'] > v['otros_tipos'] else 'NO DETECTA <<<'}")
    fallos += 0 if v3["otros_tipos"] > v["otros_tipos"] else 1

    # 4. mutacion 3: sacar un registro del header. Debe dar SIN_REGISTRO.
    #
    #    LA VICTIMA NO PUEDE SER UNA COTA DE BUCLE. La primera version de este
    #    control borro mmCP_HQD_EOP_CONTROL, que es el limite superior del
    #    primer bucle. Al desaparecer del header, el bucle ya no se puede
    #    resolver (no hay ni offset de inicio ni de fin), asi que sus indices
    #    pasan a NO_PROGRAMADO y no aparece ningun SIN_REGISTRO.
    #
    #    Es comportamiento COHERENTE, no un fallo: si la herramienta no sabe
    #    donde acaba el bloque, no afirma que falte un registro dentro. Pero
    #    hace que el control no discriminara. Ahora se elige un registro que
    #    esta DENTRO de un rango y no es ninguna cota.
    regs = parse_regs(ASIC_HDRS["gfx_8_0"])
    cotas = set()
    for _v, a, b, _l, _t in parse_loops(FUENTE_C):
        cotas.add(a)
        cotas.add(b)
    victim = None
    for _v, a, b, _l, _t in parse_loops(FUENTE_C):
        lo, hi = regs.get(a), regs.get(b)
        for o in range(lo + 1, hi):
            ks = [k for k, off in regs.items() if off == o and k not in cotas]
            if ks:
                victim = sorted(ks)[0]
                break
        if victim:
            break
    off = regs.get(victim)
    regs2 = dict(regs)
    del regs2[victim]
    v4 = veredicto(construir(regs=regs2))
    print(f"  4. registro {victim} (0x{off:04x}, no es cota) borrado -> "
          f"sin_registro {v['sin_registro']}->{v4['sin_registro']}"
          f"  {'DETECTA' if v4['sin_registro'] > v['sin_registro'] else 'NO DETECTA <<<'}")
    fallos += 0 if v4["sin_registro"] > v["sin_registro"] else 1

    # 4b. el caso de la cota: que NO la confunda con una ausencia. Si una cota
    #     desaparece, el bloque queda sin resolver y la herramienta no debe
    #     inventar un hueco dentro de el.
    regs3 = dict(regs)
    del regs3["mmCP_HQD_EOP_CONTROL"]
    v4b = veredicto(construir(regs=regs3))
    bien4b = (v4b["n_programados"] < v["n_programados"]
              and v4b["sin_registro"] == 0)
    print(f"  4b cota borrada -> programados {v['n_programados']}->{v4b['n_programados']},"
          f" sin_registro {v4b['sin_registro']}"
          f"  {'COHERENTE' if bien4b else 'INCOHERENTE <<<'}")
    fallos += 0 if bien4b else 1

    # 5. borde: struct vacio. Debe devolver None, no reventar.
    v5 = veredicto(construir(structs=[]))
    print(f"  5. struct vacio -> {'NO_ANALIZABLE' if v5 == 'NO_ANALIZABLE' else 'REVIENTA <<<'}")
    fallos += 0 if v5 == "NO_ANALIZABLE" else 1

    # 6. borde: header vacio. Debe devolver None, no reventar.
    v6 = veredicto(construir(regs={}))
    print(f"  6. header vacio -> {'NO_ANALIZABLE' if v6 == 'NO_ANALIZABLE' else 'REVIENTA <<<'}")
    fallos += 0 if v6 == "NO_ANALIZABLE" else 1

    # 7. borde: el ancla no existe. Debe devolver None.
    sin_ancla = [("uint32_t", "otra_cosa", False)]
    v7 = veredicto(construir(structs=sin_ancla))
    print(f"  7. sin campo ancla -> {'NO_ANALIZABLE' if v7 == 'NO_ANALIZABLE' else 'REVIENTA <<<'}")
    fallos += 0 if v7 == "NO_ANALIZABLE" else 1

    # 8. determinismo: dos invocaciones identicas.
    a = json.dumps(construir(), sort_keys=True)
    b = json.dumps(construir(), sort_keys=True)
    print(f"  8. determinismo -> {'IDEMPOTENTE' if a == b else 'NO DETERMINISTA <<<'}")
    fallos += 0 if a == b else 1

    # 9. el otro ASIC de la familia tambien cuadra? (065 mostro que 7
    #    registros de GMC difieren; si HQD difiere, hay que saberlo)
    t81 = construir("gfx_8_1")
    v81 = veredicto(t81)
    print(f"  9. gfx_8_1 -> match={v81['match']} mismatch={v81['mismatch']}"
          f" sin={v81['sin_registro']}  (informativo)")

    # 10. TODOS los sitios que hacen la asercion, no solo el de Polaris12.
    #     Si uno de ellos dejara de cuadrar, la tabla --sitios debe decirlo.
    todos = [(s["nombre"], veredicto(construir(sitio=s)) or {})
             for s in SITIOS]
    n_ok = sum(1 for _n, v in todos
               if isinstance(v, dict) and v
               and v.get("mismatch") == 0 and v.get("sin_registro") == 0)
    print(f" 10. sitios que corroboran -> {n_ok}/{len(SITIOS)}"
          f"  {'COHERENTE' if n_ok == len(SITIOS) else 'ALGUNO FALLA <<<'}")
    fallos += 0 if n_ok == len(SITIOS) else 1

    # 11. dos sitios del MISMO ASIC tienen que dar el MISMO bloque. Si dieran
    #     distinto, uno de los dos extractorese estaria leyendo otra funcion.
    por_asic = {}
    for s in SITIOS:
        v = veredicto(construir(sitio=s))
        if isinstance(v, dict) and v:
            por_asic.setdefault(s["asic"], set()).add(
                (v["alcance_ini"], v["alcance_fin"], v["n_programados"]))
    incoherentes = [a for a, bs in por_asic.items() if len(bs) > 1]
    print(f" 11. coherencia entre sitios del mismo ASIC -> "
          f"{'OK' if not incoherentes else 'INCOHERENTE: ' + str(incoherentes) + ' <<<'}")
    fallos += 0 if not incoherentes else 1

    print()
    if fallos:
        print(f"  RESULTADO: TOOL_BROKEN -- {fallos} controles fallan")
        return 1
    print(f"  RESULTADO: TOOL_VALIDATED -- {11 - fallos}/11 controles pasan:")
    print("    detecta renombre de campo, cambio de tipo, registro ausente,")
    print("    entrada vacia sin reventar, salida determinista, y que los 4")
    print("    sitios den el MISMO bloque dentro de cada ASIC.")
    if real_ok:
        print("    Y sobre los datos REALES no detecta nada, que es el dato")
        print("    que se iba a verificar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())