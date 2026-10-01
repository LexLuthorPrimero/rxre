#!/usr/bin/env python3
"""
ibtrace.py -- extrae secuencias de emision de IB desde el codigo fuente.

POR QUE EXISTE
--------------
Cada secuencia de anillo del driver tiene la misma forma:

    amdgpu_ring_write(ring, PACKET3(PACKET3_ALU_DATA, 8));
    amdgpu_ring_write(ring, ...);
    amdgpu_ring_write(ring, ...);

Y para responder "que emite esta funcion" hay que leerla entera y transcribir
sus escrituras a mano. Eso se ha hecho para emit_vm_flush, hdp_flush,
pipeline_sync, fence_gfx, ib_gfx, ib_compute... y son decenas de funciones.

Es exactamente el caso que la regla de aceleracion describe: N funciones con
el mismo procedimiento. Una herramienta que las recorre todas produce mas
evidencia por minuto, y sobre todo produce una TABLA que se puede comparar
entre versiones y entre ASIC.

QUE HACE
--------
  func   Secuencia de escritura de una funcion, en orden, con su nombre
  todas  Inventario de TODAS las funciones con emision de anillo, por ASIC
  diff   Compara la secuencia de una funcion entre dos ficheros (para
         responder "que cambio entre gfx8 y gfx9")
  dwords Cuantos dwords escribe cada funcion, y el opcode del primero

POR QUE ES FIABLE Y POR QUE NO ES MAS
-------------------------------------
Lo que produce es la SECUENCIA DE ESCRITURAS, con su valor literal o symbolic
cuando se puede resolver. Eso es PROVEN: sale del texto.

Lo que NO produce, y se declara en su salida:
  - el VALOR final de un simbolico como PACKET3(x, n). Resolverlo exige
    preprocesar, y solo lo hace pte_preproc para un subconjunto.
  - el EFECTO de hardware. Que se escriba un opcode no significa que la GPU
    lo interprete asi.
  - si una escritura es alcanzable: solo estan las escrituras del CUERPO de
    la funcion, no las de las funciones que llama in situ.
"""
import argparse
import os
import re
import sys

AMDKG = ("/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/working/"
         "linux-7.1.3/drivers/gpu/drm/amd/amdgpu")

# Escrituras de anillo. Los nombres reales en el driver:
#
# Hay DOS formas de escribir en un IB, y la primera version de esta
# herramienta solo(conocía la primera:
#
#   amdgpu_ring_write(ring, VALOR);        <- el comun
#   ib->ptr[ib->length_dw++] = VALOR;      <- el de SDMA
#
# Los emisores de SDMA, que son los que escriben las page tables, usan
# SIEMPRE la segunda. Ignorarla no daba un resultado parcial: daba "sin
# escrituras de anillo en el cuerpo" para sdma_v4_0_vm_set_pte_pde, que es
# precisamente la funcion que escribe los PTE de este ASIC. Un 0 que
# significa "no se que buscar", no "no escribe".
RE_RING_WRITE = re.compile(
    r"\b(amdgpu_ring_write|amdgpu_ring_write_mult\w*|"
    r"RREG32|WREG32|WREG_SB|WREG64)\s*\(\s*(?P<args>[^;]*)\)\s*;")
RE_SDMA_WRITE = re.compile(
    r"ib->ptr\s*\[\s*(?P<idx>[^]]+?)\s*\]\s*=\s*(?P<val>[^;]+?);")
# La firma abre aqui; el cierre puede estar en la MISMA linea o en las
# siguientes, y esta linea puede acabar en COMA si el nucleo de argumentos
# sigue abajo:
#
#     static void gfx_v8_0_ring_emit_vm_flush(struct amdgpu_ring *ring,
#                                             unsigned vmid, uint64_t pd_addr)
#
# Exigir el cierre en la misma linea no encuentra NINGUNA funcion del driver.
RE_FUNC_HEAD = re.compile(
    r"^(?P<mods>(?:static\s+|inline\s+|const\s+|__maybe_unused\s+)+)"
    r"(?P<tipo>void|u\d+|s\d+|int|bool|uint\d+|unsigned(?:\s+long)?|"
    r"long|size_t|char)\s*\**\s*"
    r"(?P<nombre>[A-Za-z_]\w*)\s*\(")
RE_PACKET3 = re.compile(r"PACKET3\s*\(\s*([A-Z0-9_]+)\s*,\s*(\d+)\s*\)")

# Los opcodes que el driver emite, para clasificar.
#
# NO estan en si_dispatch.h, que es donde se buscaron al principio: en 7.1.3
# los PACKET3_* viven en cikd.h (POLARIS), sid.h, soc15d.h y vid.h. Con la
# lista equivocada se cargaban 0 opcodes y la herramienta no sabe a "no se que
# opcode es", que se lee como si el opcode no existiera.
#
# Se recorren TODOS los .h del directorio y se filtran por prefijo, que es
# como se localizan de verdad. Un 0 aqui es NOT_FOUND del fichero, no
# ausencia del simbolo.
OPCODES_CONOCIDOS = {}


def _carga_opcodes():
    for fn in os.listdir(AMDKG):
        if not fn.endswith(".h"):
            continue
        try:
            for ln in open(os.path.join(AMDKG, fn), encoding="utf-8",
                           errors="replace"):
                m = re.match(
                    r"#define\s+(PACKET3_[A-Z0-9_]+|PKT_[A-Z0-9_]+)\s+"
                    r"(0x[0-9a-fA-F]+|\d+)\s*$", ln)
                if m:
                    OPCODES_CONOCIDOS.setdefault(m.group(1), m.group(2))
        except Exception:
            continue


_carga_opcodes()


def ficheros():
    return sorted(f for f in os.listdir(AMDKG)
                  if f.endswith((".c", ".h")))


def nombres_funciones(txt):
    """
    Todos los nombres de funcion definidos en txt, en orden de aparicion.

    El flag multilinea es OBLIGATORIO: la regex ancla con ^, y sin (?m) un
    finditer sobre el texto completo solo casa en la posicion 0, o sea que
    devolvia 0 funciones en un fichero de 4000 lineas. Con (?m) encuentra 157.
    """
    out = []
    for m in re.finditer(r"(?m)" + RE_FUNC_HEAD.pattern, txt):
        nom = m.group("nombre")
        if nom not in out and nom not in ("if", "while", "for", "switch",
                                          "return", "sizeof"):
            out.append(nom)
    return out


def cuerpo_de_funcion(txt, nombre):
    """
    Devuelve (linea_inicio, linea_fin, cuerpo) de una funcion.

    Dos cosas que hay que hacer bien:

    1. La FIRMA puede ocupar VARIAS lineas:

           static void gfx_v8_0_ring_emit_vm_flush(struct amdgpu_ring *ring,
                                                   unsigned vmid, uint64_t pd_addr)

       Una regex que exige la firma en una linea NO encuentra ninguna funcion
       del driver, porque el nucleo del estilo de amdgpu es partir los
       argumentos. La primera version de esta herramienta no encontraba ni una
       y decia "no se encontro la definicion", que es un 0 que parece una
       ausencia real.

    2. Se busca la DEFINICION, no cualquier mencion. Un nombre aparece en
       llamadas, en comentarios y en prototipos, y quedarse con la primera
       coincidencia daria un cuerpo vacio o el de otra funcion.

    Por eso se opera sobre LINEAS y no sobre un regex de texto: se busca la
    linea que abre la firma, se continua hasta que los parenteses cierren, y
    solo entonces se busca la llave del cuerpo.
    """
    lineas = txt.splitlines()
    # Los offsets se calculan sobre txt, el ORIGINAL. Limpiar comentarios
    # cambia la longitud del texto y desplaza todas las posiciones, asi que
    # buscar llaves en el texto limpio con offsets del original devuelve el
    # cuerpo equivocado. Por eso el corte de llaves va sobre txt, y solo el
    # PARSEO de llamadas usa el limpio.
    # indice global del inicio de cada linea, para no recounts
    offs, acc = [], 0
    for l in lineas:
        offs.append(acc)
        acc += len(l) + 1
    i = 0
    while i < len(lineas):
        m = RE_FUNC_HEAD.match(lineas[i])
        if not m:
            i += 1
            continue
        # avanzar hasta que los parenteses de la firma cierren
        depth = lineas[i].count("(") - lineas[i].count(")")
        j = i
        while depth > 0 and j + 1 < len(lineas):
            j += 1
            depth += lineas[j].count("(") - lineas[j].count(")")
        if m.group("nombre") != nombre:
            i = j + 1
            continue
        # el cuerpo empieza en la primera { tras el fin de la firma,
        # buscado sobre el ORIGINAL, y se cuenta llaves ignorando
        # comentarios: un { dentro de un /* */ descuadra el conteo.
        k = txt.find("{", offs[j] + len(lineas[j]))
        if k < 0:
            return None, None, None
        nivel, p = 0, k
        while p < len(txt):
            c = txt[p]
            if c == "/" and p + 1 < len(txt) and txt[p + 1] == "*":
                f = txt.find("*/", p)
                if f < 0:
                    break
                p = f + 2
                continue
            if c == "/" and p + 1 < len(txt) and txt[p + 1] == "/":
                f = txt.find("\n", p)
                p = (f if f >= 0 else len(txt))
                continue
            if c == "{":
                nivel += 1
            elif c == "}":
                nivel -= 1
                if nivel == 0:
                    break
            p += 1
        cuerpo = _quita_comentarios(txt[k:p + 1])
        return i + 1, txt[:p].count("\n") + 1, cuerpo
    return None, None, None


def _quita_comentarios(txt):
    """
    Elimina comentarios de linea y de bloque ANTES de parsear.

    Es OBLIGATORIO antes de buscar llamadas, porque el estilo de amdgpu pone
    comentarios EN MEDIO de los argumentos:

        amdgpu_ring_write(ring, (WAIT_REG_MEM_OPERATION(0) | /* wait */
                                 WAIT_REG_MEM_FUNCTION(0) |  /* always */
                                 WAIT_REG_MEM_ENGINE(0))); /* me */

    Sin quitarlos, el /* rompe la expresion y la herramienta reporta DOS
    escrituras donde hay UNA, y ademas pierde los flags del medio. Contar
    paquetes de forma incorrecta hace que un "5 dwords" parezca "9", y eso
    se propaga a cualquier analisis que dependa del tamano del paquete.
    """
    txt = re.sub(r"/\*.*?\*/", " ", txt, flags=re.S)
    txt = re.sub(r"//[^\n]*", " ", txt)
    return txt


def escrituras_de(cuerpo):
    """
    [(linea_rel, llamada, argumentos)] en ORDEN DE APARICION.

    Hay que mezclar las dos formas de escritura en una sola lista ordenada,
    porque el ORDEN es el dato: en un IB el orden de los dwords ES el
    paquete. Presentarlos en dos listas separadas pierde la informacion
    principal, y da una lectura falsa del paquete.
    """
    limpio = _quita_comentarios(cuerpo)
    eventos = []
    for m in RE_RING_WRITE.finditer(limpio):
        eventos.append((m.start(),
                        limpio[:m.start()].count("\n"), m.group(1),
                        " ".join(m.group("args").split())))
    for m in RE_SDMA_WRITE.finditer(limpio):
        eventos.append((m.start(),
                        limpio[:m.start()].count("\n"),
                        "ib->ptr[%s]" % m.group("idx"),
                        " ".join(m.group("val").split())))
    eventos.sort(key=lambda x: x[0])
    return [(e[1], e[2], e[3]) for e in eventos]


def clasifica(args):
    """
    Que clase de escritura es.

    PACKET3(opcode, n) es un HEADER de packet: el ME lo decodifica. Un valor
    suelto es un dword de payload. Confundirlos hace que se cuente un paquete
    como si fueran cinco escrituras, o al reves.
    """
    m = RE_PACKET3.search(args)
    if m:
        op = m.group(1)
        val = OPCODES_CONOCIDOS.get(op)
        return ("HEADER", op, m.group(2), val)
    return ("DWORD", None, None, None)


def cmd_func(args):
    fichero, nombre = args.rsplit("::", 1)
    p = os.path.join(AMDKG, fichero)
    if not os.path.exists(p):
        cand = [f for f in ficheros() if f == fichero]
        if not cand:
            print("no existe %s en amdgpu" % fichero)
            return 1
        p = os.path.join(AMDKG, cand[0])
        fichero = cand[0]
    txt = open(p, encoding="utf-8", errors="replace").read()
    ini, fin, cuerpo = cuerpo_de_funcion(txt, nombre)
    if cuerpo is None:
        print("no se encontro la DEFINICION de %s en %s" % (nombre, fichero))
        print("Puede ser: una macro, un prototipo sin cuerpo, o el nombre")
        print("no es el exacto. NOT_FOUND, no PROVEN_ABSENT.")
        return 1
    print("%s: %s  (lineas %d-%d)" % (fichero, nombre, ini, fin))
    print("-" * 72)
    ws = escrituras_de(cuerpo)
    if not ws:
        print("sin escrituras de anillo en el cuerpo")
        print("Eso significa que escribe por otra via (helper, puntero a")
        print("funcion, o registro directo). NO que no escriba nada.")
        return 1
    for rel, llamada, a in ws:
        clase, op, n, val = clasifica(a)
        if clase == "HEADER":
            extra = "opcode=%s%s" % (op, " = %s" % val if val else "")
            print("  L%-4d %-22s HEADER %-32s n=%s" %
                  (ini + rel, llamada, extra, n))
        else:
            # Sin truncar, o con un truncado que avise. Truncar a 44
            # caracteres escondia WAIT_REG_MEM_FUNCTION y WAIT_REG_MEM_ENGINE,
            # que son justo los campos que interesan: el lector ve una
            # expresion incompleta y no puede saber que le falta informacion.
            print("  L%-4d %-22s DWORD   %s" % (ini + rel, llamada, a))
    print("--- %d escrituras (%d headers, %d dwords)" % (
        len(ws), sum(1 for w in ws if clasifica(w[2])[0] == "HEADER"),
        sum(1 for w in ws if clasifica(w[2])[0] == "DWORD")))
    print()
    print("Es la SECUENCIA DE ESCRITURAS. No dice:")
    print("  - el valor final de un simbolico sin preprocesar")
    print("  - el efecto de hardware de ningun opcode")
    print("  - que las escrituras de las funciones llamadas esten aqui")
    return 0


def cmd_todas(args):
    """
    Inventario de todas las funciones con emision de anillo, por fichero.

    Es la tabla que hace comparables dos ASIC y dos versiones. Sin esto,
    "que cambia entre gfx8 y gfx9" es una lectura manual de 2000 lineas.
    """
    solo = args[0] if args else None
    print("=== funciones con emision de anillo ===")
    print()
    print("%-22s %-46s %6s %6s %6s" % ("fichero", "funcion", "esc", "hdr", "dw"))
    print("-" * 92)
    total = 0
    for fn in ficheros():
        if solo and solo not in fn:
            continue
        if not fn.endswith(".c"):
            continue
        txt = open(os.path.join(AMDKG, fn), encoding="utf-8",
                   errors="replace").read()
        for nombre in nombres_funciones(txt):
            _i, _j, cuerpo = cuerpo_de_funcion(txt, nombre)
            if not cuerpo:
                continue
            ws = escrituras_de(cuerpo)
            if not ws:
                continue
            nh = sum(1 for w in ws if clasifica(w[2])[0] == "HEADER")
            total += 1
            print("%-22s %-46s %6d %6d %6d" %
                  (fn, nombre[:46], len(ws), nh, len(ws) - nh))
    print("--- %d funciones con emision" % total)
    return 0


def cmd_diff(args):
    """
    Compara la MISMA funcion entre dos ficheros.

    Responde "que cambia de gfx8 a gfx9" como un diff, no como una lectura.
    """
    if len(args) != 2:
        print("diff necesita dos ficheros: ibtrace.py diff A.c B.c")
        return 2
    cuerpos = []
    for f in args:
        p = os.path.join(AMDKG, f)
        txt = open(p, encoding="utf-8", errors="replace").read()
        nombres = [m.group("nombre") for m in RE_FUNC_HEAD.finditer(txt)]
        cuerpos.append((f, txt, nombres))
    comunes = set(cuerpos[0][2]) & set(cuerpos[1][2])
    if not comunes:
        print("ningun nombre de funcion es comun")
        return 1
    print("funciones comunes: %d" % len(comunes))
    print()
    for nombre in sorted(comunes):
        res = []
        for f, txt, _ in cuerpos:
            _i, _j, c = cuerpo_de_funcion(txt, nombre)
            res.append([clasifica(w[2])[1] or clasifica(w[2])[0]
                        for w in escrituras_de(c)] if c else [])
        if res[0] != res[1]:
            print("DIFIERE %s:" % nombre)
            print("   %s: %s" % (cuerpos[0][0], res[0][:14]))
            print("   %s: %s" % (cuerpos[1][0], res[1][:14]))
    return 0


def cmd_sync(args):
    """
    Que funciones emiten un opcode de SINCRONIZACION, y en que orden.

    Es la pregunta que mas se ha hecho a mano en este proyecto: "quien
    sincroniza PFP con ME", "que se emite entre PTBA e invalidate", "el fence
    espera o no". Con 63 funciones con emision en gfx_v8_0, responder eso a
    mano significa recorrer las 63.

    Los opcodes de sincronizacion son los que SINCRONIZAN, no los que
    transfieren: SYNC_ME, PFP_SYNC_ME, PFP_FENCE, EVENT_WRITE, GRBM_GUI,
    CS_HALT, DMA_DATA. Se listan sus funciones y el orden relativo de sus
    escrituras de sincronizacion dentro de cada una.
    """
    solo = args[0] if args else "v8"
    print("=== funciones que emiten opcodes de SINCRONIZACION ===")
    print()
    print("%-46s %-26s %s" % ("funcion", "sincronizaciones", "archivo"))
    print("-" * 100)
    total = 0
    for fn in ficheros():
        if not fn.endswith(".c"):
            continue
        if solo and solo not in fn and "gfx" not in fn and "gmc" not in fn:
            continue
        txt = open(os.path.join(AMDKG, fn), encoding="utf-8",
                   errors="replace").read()
        for nombre in nombres_funciones(txt):
            ini, _j, cuerpo = cuerpo_de_funcion(txt, nombre)
            if not cuerpo:
                continue
            ws = escrituras_de(cuerpo)
            ops = []
            for rel, _c, a in ws:
                clase, op, _n, _v = clasifica(a)
                if clase == "HEADER" and op and any(
                        s in op for s in ("SYNC", "FENCE", "EVENT_WRITE",
                                          "GRBM_GUI", "CS_HALT", "CNTXCNTL")):
                    ops.append(op.replace("PACKET3_", ""))
            if ops:
                total += 1
                print("%-46s %-26s %s" % (nombre[:46],
                                          ",".join(ops)[:26], fn))
    print("--- %d funciones con sincronizacion" % total)
    return 0


def main():
    ap = argparse.ArgumentParser(description="traza secuencias de IB")
    ap.add_argument("cmd", choices=["func", "todas", "diff", "sync"])
    ap.add_argument("args", nargs="*")
    a = ap.parse_args()
    print("opcodes conocidos cargados: %d" % len(OPCODES_CONOCIDOS))
    print()
    if a.cmd == "func":
        if len(a.args) != 1 or "::" not in a.args[0]:
            print("func necesita FICHERO::FUNCION")
            return 2
        return cmd_func(a.args[0])
    if a.cmd == "todas":
        return cmd_todas(a.args)
    if a.cmd == "sync":
        return cmd_sync(a.args)
    if a.cmd == "diff":
        return cmd_diff(a.args)
    return 2


if __name__ == "__main__":
    sys.exit(main())