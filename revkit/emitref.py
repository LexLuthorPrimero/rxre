#!/usr/bin/env python3
# CONTRACT: name=emitref
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=indeterminado
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py, y el veredicto fue `NO_DETERMINED`.
# NO se upgraded a `WRITES_FILES=yes` porque no esta medido, y NO se dejo en
# `no` porque el codigo no lo sostiene.  La razon del NO_DETERMINED es que invoca herramientas por subprocess; su AST no tiene ningun `open` en modo escritura.
#
# Poner `yes` seria MENTIR en un sentido que el validador no puede detectar, que
# es lo que el propio toolkit.py escribe de sus cinco falsos positivos: "un
# contrato en prosa no se puede comprobar con una maquina".  Poner `no` seria
# Peor: seria una afirmacion que nadie ha comprobado.
#
# TOUCHES_INTEGRATED=no: lee sysfs y ficheros.  No hace ioctl ni escribe en la
# GPU.  Ver 1487.
# -*- coding: utf-8 -*-
"""
emitref.py -- el emisor NUESTRO contra el emisor del CORPUS que corre en esta GPU.

POR QUE EXISTE
==============

`docs/IMPLEMENTATION-STATUS.md` 2.1 dice, con palabras:

    LO QUE FALTA PARA VALIDARLO, y es concreto
      un control negativo contra el emisor del driver de REFERENCIA, no contra la
      propia constante.

Y mas abajo, el motivo por el que importa:

    Las dos puntas del test leen RX550_SDMA_PTEPDE_DW del mismo header. Es
    coherencia, no validacion: no hay una segunda fuente con la que la constante
    pueda discrepar.

El campo `count` de la cabecera PTEPDE se ha dado la vuelta DOS veces en este
proyecto (C-011 y su ownPasado). Un control que comparase nuestro codigo con
nuestro header no lo habria detectado ninguna de las dos veces: las dos puntas
movidas a la vez.

QUE NO ES ESTA HERRAMIENTA
=========================

No es un generador de PM4, no calcula direcciones, no toca el hardware y no
escribe nada. Compara DOS TEXTO y dice si describen la misma secuencia, campo a
campo, y con que ORIGEN es cada campo.

El resultado que importa no es "coinciden": es "coinciden CON ESTA referencia,
que es la que corre en ESTE ASIC". Por eso el primer paso no es opcional: si se
eligiera la referencia equivocada, la comparacion dariia verde sobre la
referencia equivocada.

LA REGLA QUE ESTA HERRAMIENTA USA
================================

Ninguna expectativa se escribe a mano. El opcode esperado se SACA del header
del corpus; el ancho de registro se SACA contando los emits de la referencia; el
resultado esperado en los vectores se SACA del fixture.

PROTOCOLO DE SALIDA
===================

    0  OK
    1  FALLO
    2  uso incorrecto
    4  INVALID: no se puede comprobar
"""

import argparse
import io
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
AMDKG = os.path.join(RAIZ, "RESEARCH", "baseline", "linux-7.1.3", "drivers",
                     "gpu", "drm", "amd", "amdgpu")
KERNEL_NOSOTRO = os.path.join(RAIZ, "07-DRIVER", "kernel")

# Las tres rutas que hay que cerrar para que la comparacion signifique algo.
# El ASIC, el bloque IP que le anade vi.c, y la vtable que ese bloque usa.
ASIC = "POLARIS12"
EMISOR_NOSOTRO = "rx550_sdma_vm_set_pte_pde"
FICHERO_NOSOTRO = "rx550_pm4.c"


# --- extraccion de la secuencia de escrituras ---------------------------------
#
# Se reutiliza ibtrace._quita_comentarios porque ya esta validado y porque su
# unico contrato importante es NO DESTRUIR LA ESTRUCTURA DE LINEAS: si el
# numero de linea deja de coincidir, esta herramienta heredaria el defecto.
#
# MEDIDO 2026-10-03: se cpio el extractor en vez de importarlo y secciones el
# resultado con una version que aplastaba los comentarios de bloque. Mal.

def _quita_comentarios(txt):
    """Igual que ibtrace, y por el MISMO motivo: conserva los saltos de linea."""
    def _a_espacios(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    txt = re.sub(r"/\*.*?\*/", _a_espacios, txt, flags=re.S)
    txt = re.sub(r"//[^\n]*", lambda m: " " * len(m.group(0)), txt)
    return txt


# El corpus escribe en ib->ptr y el codigo nuestro en ib->buf. Es el mismo
# anillo con nombre distinto, y buscar solo uno de los dos seria mirar la mitad
# del problema.
RE_WRITE = re.compile(
    r"ib\s*->\s*(?P<buf>ptr|buf)\s*\[[^\]]*\]\s*=\s*(?P<val>[^;]+);")


def cuerpo_de(txt, nombre):
    """
    (linea_de_inicio, cuerpo) de la DEFINICION de `nombre`.

    Devuelve el cuerpo anclado en la MISMA linea que devuelve, porque el numero
    de linea y el offset tienen que compartir origen. MEDIDO: anclar el cuerpo
    en la llave y el inicio en la firma dejo todos los numeros 4 por debajo.
    """
    lineas = txt.splitlines()
    offs, acc = [], 0
    for l in lineas:
        offs.append(acc)
        acc += len(l) + 1
    i = 0
    while i < len(lineas):
        if not re.match(r"\s*(?:static\s+)?[A-Za-z_][\w \t\*]*?\b%s\s*\(" % nombre,
                        lineas[i]):
            i += 1
            continue
        depth = lineas[i].count("(") - lineas[i].count(")")
        j = i
        while depth > 0 and j + 1 < len(lineas):
            j += 1
            depth += lineas[j].count("(") - lineas[j].count(")")
        k = txt.find("{", offs[j] + len(lineas[j]))
        if k < 0:
            return None, None
        nivel, p = 0, k
        while p < len(txt):
            c = txt[p]
            if c == "/" and p + 1 < len(txt) and txt[p + 1] == "*":
                f = txt.find("*/", p)
                if f < 0:
                    break
                p = f + 2
                continue
            if c == "{":
                nivel += 1
            elif c == "}":
                nivel -= 1
                if nivel == 0:
                    break
            p += 1
        return i + 1, _quita_comentarios(txt[offs[i]:p + 1])
    return None, None


def emisiones(cuerpo):
    """[expresion] en orden de aparicion. El orden ES el paquete."""
    limpio = _quita_comentarios(cuerpo)
    ev = [(m.start(), " ".join(m.group("val").split()))
          for m in RE_WRITE.finditer(limpio)]
    ev.sort(key=lambda x: x[0])
    return [e[1] for e in ev]


# --- clasificacion por PAPEL, no por texto -----------------------------------
#
# El corpus y el codigo nuestro describen el mismo campo con sintaxis distinta:
#     lower_32_bits(pe)        frente a   (__u32)(pe & 0xFFFFFFFFu)
# Comparar texto daria "difieren" en los diez campos y no diria nada. Lo que se
# compara es el PAPEL: bajo 32 de pe, alto 32 de pe, el contador, el opcode.

RE_PAPEL = [
    ("HEADER", re.compile(r"^(?:[A-Za-z_]\w*\.)?(?:SDMA_)?PKT_HEADER_OP\(|^"
                          r"[A-Za-z_]\w*sdma_header\(|\bsdma_header\(")),
    ("LOW32", re.compile(r"^lower_32_bits\((?P<x>[A-Za-z_]\w*)\)")),
    ("HIGH32", re.compile(r"^upper_32_bits\((?P<x>[A-Za-z_]\w*)\)")),
    # MEDIDO 2026-10-03: mi primera regex exigia que el literal acabase en el
    # cierre, y en C los literales llevan sufijo de tipo. Con 0xFFFFFFFFu no
    # casaba, el clasificador decia DESCONOCIDO, y la comparacion daba tres
    # DIFERENCIAS FALSAS en los dwords 2, 4 y 6. Un clasificador que no
    # reconoce la sintaxis del codigo propio no puede compararlo con el ajeno.
    ("LOW32", re.compile(r"^\(__u32\)\((?P<x>[A-Za-z_]\w*)\s*&\s*"
                         r"0[xX][0-9A-Fa-f]+[uUlL]*\)")),
    ("HIGH32", re.compile(r"^\(__u32\)\((?P<x>[A-Za-z_]\w*)\s*>>\s*"
                          r"\d+[uUlL]*\)")),
    ("IDENT", re.compile(r"^(?P<x>[A-Za-z_]\w*)$")),
    ("CONST0", re.compile(r"^0+$")),
]


def papel(expr):
    """(ROL, argumento) de una expresion. (DESCONOCIDO, expr) si no se sabe."""
    e = expr.strip()
    for rol, rx in RE_PAPEL:
        m = rx.search(e)
        if m:
            if rol in ("HEADER", "CONST0"):
                return rol, ""
            return rol, m.group("x") if "x" in m.groupdict() else ""
    return "DESCONOCIDO", e


def tabla_papeles(emisiones_txt):
    return [papel(e) for e in emisiones_txt]


# --- opcode: el numero se SACA del corpus, no se escribe ---------------------

def valor_define(txt, macro):
    m = re.search(r"^\s*#\s*define\s+%s\s+(\d+)\b" % re.escape(macro),
                  txt, flags=re.M)
    return int(m.group(1)) if m else None


def opcode_de(expr_ref, expr_nos, txt_corpus, txt_nosotros):
    """
    El numero del opcode del primer dword, resuelto en las DOS fuentes.

    MEDIDO 2026-10-03: esta funcion recibia UNA sola expresion de cabecera, la de
    la referencia, y buscaba dentro de ella la macro NUESTRA. No la encontraba
    nunca, y el opcode salia NO RESUELTO. Cada fuente tiene su propia macro, y
    el numero se saca de cada una por separado; luego se comparan los numeros.

    Si las dos resuelven al mismo, el dword 1 es el mismo. Si no, no lo es aunque
    las dos lineas se parezcan.
    """
    m = re.search(r"\b(SDMA_OP\w*PTEPDE)\b", expr_ref)
    n_corpus = valor_define(txt_corpus, m.group(1)) if m else None
    m2 = re.search(r"\b([A-Z0-9_]*OP_[A-Z0-9_]*PTEPDE)\b", expr_nos)
    n_nosotros = valor_define(txt_nosotros, m2.group(1)) if m2 else None
    return n_corpus, n_nosotros


# --- la cadena que decide QUE referencia es la buena -------------------------

def cadena_del_asic():
    """
    QUE EMISOR DEL CORPUS CORRE EN ESTA GPU, eslabon por eslabon.

        1  vi.c         case CHIP_POLARIS12: -> &sdma_v3_1_ip_block
        2  sdma_v3_0.c  ese bloque          -> .funcs   = &sdma_v3_0_ip_funcs
        3  sdma_v3_0.c  esa vtable          -> .early_init = sdma_v3_0_early_init
        4  sdma_v3_0.c  ese cuerpo          -> &sdma_v3_0_vm_pte_funcs
        5  sdma_v3_0.c  esa tabla           -> .set_pte_pde = <EMISOR>

    Sin esto, comparar contra sdma_v4_0 y contra sdma_v3_0 seria igual de valido
    y la herramienta no podria elegir.

    MEDIDO 2026-10-03: el salto 4 NO es un campo de la vtable. Yo habia
    supuesto que .set_pte_pde estaba en sdma_v3_0_ip_funcs, y no: esta en
    sdma_v3_0_vm_pte_funcs, de tipo amdgpu_vm_pte_funcs, y se pasa por una LLAMADA
    dentro de early_init. Un salto imaginado aqui habria comparado el codigo
    nuestro contra la tabla equivocada y habria dado verde.
    """
    e = []
    vi = io.open(os.path.join(AMDKG, "vi.c"), encoding="utf-8",
                 errors="replace").read()
    bloque = _bloque_del_brazo(vi)
    if not bloque:
        return None, e
    e.append(("vi.c", "brazo CHIP_%s anade &%s" % (ASIC, bloque)))
    fn, txt = _declara_bloque(bloque)
    if not fn:
        return None, e + [("-", "no se declara %s en ningun .c del corpus" % bloque)]
    e.append((fn, "declarado en %s" % fn))

    vtable = _campo_de_tabla(txt, bloque, "funcs")
    if not vtable:
        return None, e + [(fn, "%s no tiene .funcs" % bloque)]
    e.append((fn, "%s.funcs = &%s" % (bloque, vtable)))

    init = _campo_de_tabla(txt, vtable, "early_init")
    if not init:
        return None, e + [(fn, "%s no tiene .early_init" % vtable)]
    e.append((fn, "%s.early_init = %s" % (vtable, init)))

    ini, cuerpo = cuerpo_de(txt, init)
    if not cuerpo:
        return None, e + [(fn, "no se lee el cuerpo de %s" % init)]
    m = re.search(r"&(\w*vm_pte_funcs)", cuerpo)
    if not m:
        return None, e + [(fn, "%s NO pasa ninguna tabla *_vm_pte_funcs" % init)]
    pte = m.group(1)
    e.append((fn, "%s pasa &%s" % (init, pte)))

    emisor = _campo_de_tabla(txt, pte, "set_pte_pde")
    if not emisor:
        return None, e + [(fn, "%s no asigna .set_pte_pde" % pte)]
    e.append((fn, "%s.set_pte_pde = %s" % (pte, emisor)))
    return emisor, e


def _bloque_del_brazo(vi):
    """
    El unico brazo de CHIP_<ASIC> que anade bloques IP.

    MEDIDO 2026-10-03: la etiqueta aparece OCHO veces en vi.c, en ocho tablas
    distintas. Siete son tablas de capacidades y no anaden ningun bloque; una,
    la de la linea 2107, anade los diez. Concatenarlas mezclaba ASICs y daba un
    bloque sDMA equivocado sin avisar.

    Si MAS DE UN brazo anadiera bloques, no se elige: se declara.
    """
    lineas = vi.splitlines()
    etiq = re.compile(r"\s*case\s+CHIP_%s:" % ASIC)
    brazos, k = [], 0
    while True:
        k = next((x for x in range(k, len(lineas)) if etiq.match(lineas[x])),
                 None)
        if k is None:
            break
        brazo, k = [], k + 1
        while k < len(lineas):
            l = lineas[k]
            if re.match(r"\s*case\s", l) or not l.strip():
                k += 1
                continue
            if re.match(r"\s*(break\b|default:|\})", l):
                break
            brazo.append(l)
            k += 1
        if any("amdgpu_device_ip_block_add" in l for l in brazo):
            brazos.append(brazo)
    if len(brazos) != 1:
        return None
    m = re.search(r"&(\w*sdma\w*ip_block)", "\n".join(brazos[0]))
    return m.group(1) if m else None


def _campo_de_tabla(txt, tabla, campo):
    """El simbolo al que `campo` apunta dentro de la tabla `tabla`, o None."""
    m = re.search(r"\b%s\s*=\s*\{(.*?)\n\};" % re.escape(tabla), txt,
                  flags=re.S)
    if not m:
        return None
    mc = re.search(r"\.%s\s*=\s*(&?)(\w+)" % re.escape(campo), m.group(1))
    return mc.group(2) if mc else None


def _declara_bloque(bloque):
    """(fichero, texto) donde se DECLARA el bloque. 0 filas NO es ausencia."""
    for fn in sorted(os.listdir(AMDKG)):
        if not fn.endswith(".c"):
            continue
        txt = io.open(os.path.join(AMDKG, fn), encoding="utf-8",
                      errors="replace").read()
        if re.search(r"\b%s\s*=\s*\{" % re.escape(bloque), txt):
            return fn, txt
    return None, None


def texto_de_emisor(fichero, emisor):
    for fn in (fichero,):
        p = os.path.join(AMDKG, fn)
        if os.path.exists(p):
            txt = io.open(p, encoding="utf-8", errors="replace").read()
            ini, cuerpo = cuerpo_de(txt, emisor)
            if cuerpo:
                return fn, ini, cuerpo
    return None, None, None


# --- comandos ----------------------------------------------------------------

def cmd_chain(args):
    print("QUE EMISOR DEL CORPUS CORRE EN %s" % ASIC)
    print("-" * 74)
    emisor, eslabones = cadena_del_asic()
    for donde, que in eslabones:
        print("  %-18s %s" % (donde, que))
    if not emisor:
        print()
        print("  INVALID: la cadena no cierra. Comparar sin saber cual es la")
        print("  referencia daria verde sobre la referencia equivocada.")
        return 4
    print("  %-18s EMISOR = %s" % ("", emisor))
    return 0


def cmd_comparar(args):
    emisor, eslabones = cadena_del_asic()
    if not emisor:
        print("INVALID: no se puede saber que emisor corre. Ver `chain`.")
        return 4
    fn_ref, _ini, cuerpo_ref = texto_de_emisor(
        "sdma_v3_0.c" if "v3_0" in emisor else "sdma_v4_0.c", emisor)
    if not cuerpo_ref:
        print("INVALID: no se localiza %s en el corpus" % emisor)
        return 4
    fn_nos = os.path.join(KERNEL_NOSOTRO, FICHERO_NOSOTRO)
    if not os.path.exists(fn_nos):
        print("INVALID: no existe %s" % fn_nos)
        print("Es codigo de otra sesion. Se LEE, no se escribe.")
        return 4
    txt_nos = io.open(fn_nos, encoding="utf-8", errors="replace").read()
    _i, cuerpo_nos = cuerpo_de(txt_nos, EMISOR_NOSOTRO)
    if not cuerpo_nos:
        print("INVALID: no se localiza %s en %s" % (EMISOR_NOSOTRO, FICHERO_NOSOTRO))
        return 4
    txt_corpus_hdr = _headers_de(fn_ref)
    hdr_nos = io.open(os.path.join(KERNEL_NOSOTRO, "rx550_pm4.h"),
                      encoding="utf-8", errors="replace").read()

    e_ref = emisiones(cuerpo_ref)
    e_nos = emisiones(cuerpo_nos)
    p_ref = tabla_papeles(e_ref)
    p_nos = tabla_papeles(e_nos)

    print("COMPARACION CONTRA EL EMISOR QUE CORRE EN %s" % ASIC)
    print("  referencia : %s::%s" % (fn_ref, emisor))
    print("  nuestro   : %s::%s" % (FICHERO_NOSOTRO, EMISOR_NOSOTRO))
    print("  el nuestro se lee, no se toca. Es de otra sesion.")
    print("-" * 74)
    print("  %-4s %-26s %-26s" % ("dword", "REFERENCIA (papel)", "NUESTRO (papel)"))
    fallos = []
    for k in range(max(len(p_ref), len(p_nos))):
        marca = "" if _pareja(p_ref, k) == _pareja(p_nos, k) else "   <-- DIFIERE"
        print("  %-4d %-26s %-26s%s" % (k + 1, _pareja(p_ref, k),
                                        _pareja(p_nos, k), marca))
    for k, a, b in _diferencias(p_ref, p_nos):
        fallos.append("dword %d: referencia %s, nuestro %s" % (k, a, b))

    n_op_ref, n_op_nos = opcode_de(e_ref[0] if e_ref else "",
                                    e_nos[0] if e_nos else "",
                                    txt_corpus_hdr, hdr_nos)
    print()
    print("  OPCODE del dword 1")
    print("    corpus  %s" % ("%s = %s" % (e_ref[0][:34], n_op_ref) if n_op_ref
                              is not None else "NO RESUELTO"))
    print("    nuestro %s" % ("%s = %s" % (e_nos[0][:34], n_op_nos)
                              if n_op_nos is not None else "NO RESUELTO"))
    if n_op_ref is None or n_op_nos is None:
        fallos.append("el opcode no se resuelve en una de las dos fuentes")
    elif n_op_ref != n_op_nos:
        fallos.append("opcode: corpus %d, nuestro %d" % (n_op_ref, n_op_nos))

    print()
    print("  EL CAMPO QUE SE HA DADO LA VUELTA DOS VECES, POR SU NOMBRE:")
    pos = [k for k, (r, x) in enumerate(p_ref) if r == "IDENT" and x == "count"]
    if not pos:
        print("    la referencia NO tiene un campo `count`: la pregunta no aplica")
        fallos.append("la referencia no tiene campo count")
    else:
        k = pos[0]
        got = p_nos[k][1] if k < len(p_nos) else "(ausente)"
        print("    dword %d, referencia = IDENT(count), nuestro = %s" % (k + 1, got))
        if got != "count":
            fallos.append("dword %d: el campo count vale %s, no count" % (k + 1, got))

    print()
    if fallos:
        for f in fallos:
            print("  FALLA %s" % f)
        print()
        print("  rc=1. Un campo distinto NO es un detalle: es la instruccion que")
        print("  se ejecuta.")
        return 1
    print("  OK    los %d dwords coinciden en PAPEL, el opcode coincide en"
          % len(p_ref))
    print("        NUMERO y el campo count es IDENT(count) en las dos fuentes.")
    print()
    print("  QUE NO ESTA COMPROBADO, y se dice:")
    print("    - que el hardware espere lo que escribe el emisor. Eso solo se")
    print("      comprueba en runtime, y el runtime no se ejecuta.")
    print("    - el resto de la cabecera, la de regimenes, la sin IRQ.")
    print("    - que la constante de ANCHO del header nuestro sea la correcta:")
    print("      las dos puntas de su test la leen del mismo header, y eso es")
    print("      coherencia, no validacion. Aqui el ancho se SACA CONTANDO los")
    print("      emits de la referencia, que es una segunda fuente.")
    ancho_ref, ancho_nos = len(e_ref), len(e_nos)
    print("        ancho de la referencia = %d, el nuestro = %d" % (ancho_ref, ancho_nos))
    if not _ancho_correcto(ancho_ref, ancho_nos):
        print("        y NO COINCIDEN")
        return 1
    return 0


def _ancho_correcto(n_ref, n_nos):
    """
    El numero de dwords de una cabecera de PTEPDE es el numero de EMITS de la
    funcion que la escribe. Contarlos es una SEGUNDA FUENTE: la constante del
    header nuestro no se contrasta con nada, porque las dos puntas de su test
    la leen del mismo header, y eso es coherencia, no validacion.

    MEDIDO 2026-10-03: al principio esto era un `if` suelto al final de
    comparar(), y la mutacion que lo desactiva NO LA CAZABA NINGUN VECTOR,
    porque ningun vector pasaba por ahi. Cuarta vez en este proyecto que un
    control existe y no se ejerce.
    """
    return n_ref == n_nos and n_ref > 0


def _diferencias(p_ref, p_nos):
    """
    Los dword en los que las dos secuencias de PAPELES no coinciden.

    MEDIDO 2026-10-03: el selftest probaba el CLASIFICADOR, que es la mitad de
    la historia, y no la COMPARACION, que es la otra mitad. Un `if a != b`
    puesto a false no lo detectaba nada, porque ningun vector pasaba por el. Un
    control que no ejerce la funcion que audita no es un control. Esta es la
    misma trampa que la del resumen y la salida detallada, y la cuarta vez que
    aparece en este proyecto.
    """
    out = []
    for k in range(max(len(p_ref), len(p_nos))):
        a, b = _pareja(p_ref, k), _pareja(p_nos, k)
        if a != b:
            out.append((k + 1, a, b))
    return out


def _pareja(papeles, k):
    if k < len(papeles):
        r, x = papeles[k]
        return "%s(%s)" % (r, x) if x else r
    return "(ausente)"


def _headers_de(fn):
    """El texto de los headers que el corpus usa para ese fichero."""
    out = []
    base = os.path.basename(fn)
    fam = base.split("_")[0]
    for h in sorted(os.listdir(AMDKG)):
        if h.endswith(".h") and (fam in h or "sdma" in h):
            out.append(io.open(os.path.join(AMDKG, h), encoding="utf-8",
                               errors="replace").read())
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="emisor propio contra el del corpus")
    ap.add_argument("cmd", choices=["chain", "comparar", "selftest"])
    a = ap.parse_args()
    if a.cmd == "chain":
        return cmd_chain(a)
    if a.cmd == "comparar":
        return cmd_comparar(a)
    return cmd_selftest()


# --- selftest ----------------------------------------------------------------
#
# Los controles van con entrada buena Y con entrada mala. Un control que solo se
# ejerce con el caso bueno no se sabe si comprueba; ya ha pasado en este
# repositorio cuatro veces.
#
# El fixture se escribe con BYTES LITERALES, nunca con la misma expresion que se
# quiere comprobar, y lo esperado se DERIVA del fixture.

FIXTURE_REF = """static void ref_emit(struct andgpu_ib *ib, uint64_t pe,
                                     uint64_t addr, unsigned count,
                                     uint32_t incr, uint64_t flags)
{
	ib->ptr[ib->length_dw++] = SDMA_PKT_HEADER_OP(SDMA_OP_GEN_PTEPDE);
	ib->ptr[ib->length_dw++] = lower_32_bits(pe);
	ib->ptr[ib->length_dw++] = upper_32_bits(pe);
	ib->ptr[ib->length_dw++] = lower_32_bits(flags);
	ib->ptr[ib->length_dw++] = upper_32_bits(flags);
	ib->ptr[ib->length_dw++] = lower_32_bits(addr);
	ib->ptr[ib->length_dw++] = upper_32_bits(addr);
	ib->ptr[ib->length_dw++] = incr;
	ib->ptr[ib->length_dw++] = 0;
	ib->ptr[ib->length_dw++] = count;
}
"""

FIXTURE_NOS_OK = """static void nos_emit(struct rx550_pm4_ib *ib, __u64 pe, __u64 addr,
                                     unsigned count, __u32 incr, __u64 flags)
{
	ib->buf[ib->length_dw++] = rx550_sdma_header(RX550_SDMA_OP_GEN_PTEPDE);
	ib->buf[ib->length_dw++] = (__u32)(pe & 0xFFFFFFFFu);
	ib->buf[ib->length_dw++] = (__u32)(pe >> 32);
	ib->buf[ib->length_dw++] = (__u32)(flags & 0xFFFFFFFFu);
	ib->buf[ib->length_dw++] = (__u32)(flags >> 32);
	ib->buf[ib->length_dw++] = (__u32)(addr & 0xFFFFFFFFu);
	ib->buf[ib->length_dw++] = (__u32)(addr >> 32);
	ib->buf[ib->length_dw++] = incr;
	ib->buf[ib->length_dw++] = 0;
	ib->buf[ib->length_dw++] = count;
}
"""


def cmd_selftest():
    fallos = []
    print("SELFTEST: el clasificador de PAPEL y el comparador, con entrada mala")
    print("-" * 74)

    # el extractor, y su control de que el anchor de linea es el de la firma
    ini, cuerpo = cuerpo_de(FIXTURE_REF, "ref_emit")
    if cuerpo is None:
        print("  FALLA el extractor no encuentra la funcion del fixture")
        return 1
    if ini != 1:
        print("  FALLA el fixture deberia empezar en la linea 1 y dice %d" % ini)
        fallos.append("ancla de linea")
    else:
        print("  OK    el cuerpo se ancla en la linea que devuelve")

    e_ref = emisiones(cuerpo)
    n_esperado = FIXTURE_REF.count("ib->ptr[ib->length_dw++]")
    if len(e_ref) != n_esperado:
        print("  FALLA el fixture declara %d escrituras y se leen %d"
              % (n_esperado, len(e_ref)))
        fallos.append("numero de emisiones")
    else:
        print("  OK    se leen las %d escrituras que el fixture declara" % n_esperado)

    p_ref = tabla_papeles(e_ref)

    # lo mismo, con la SINTAXIS NUESTRA: los papeles tienen que COINCIDIR
    _i2, cuerpo2 = cuerpo_de(FIXTURE_NOS_OK, "nos_emit")
    p_nos = tabla_papeles(emisiones(cuerpo2))
    if p_ref != p_nos:
        print("  FALLA el fixture de sintaxis distinta NO da los mismos papeles:")
        print("         ref  %s" % (p_ref,))
        print("         nos  %s" % (p_nos,))
        fallos.append("sintaxis distinta cambia el papel")
    else:
        print("  OK    dos sintaxis distintas dan los MISMOS papeles, que es")
        print("        lo que hace util comparar por papel y no por texto")

    # el CONTRASTE que da potencia al comparador: count frente a count - 1
    Fixture_malo = FIXTURE_NOS_OK.replace(
        "ib->buf[ib->length_dw++] = count;",
        "ib->buf[ib->length_dw++] = count - 1;")
    _i3, cuerpo3 = cuerpo_de(Fixture_malo, "nos_emit")
    p_malo = tabla_papeles(emisiones(cuerpo3))
    d = [k for k in range(max(len(p_ref), len(p_malo)))
         if _pareja(p_ref, k) != _pareja(p_malo, k)]
    if d:
        print("  OK    count frente a count - 1 se separa en el dword %d, que"
              % (d[0] + 1))
        print("        es exactamente el campo que C-011 dio la vuelta dos veces")
    else:
        print("  FALLA count y count - 1 NO se separan: el comparador no tiene")
        print("        potencia sobre el campo que importa")
        fallos.append("count - 1 no se detecta")

    # un campo CRUZADO, que es el otro modo de fallo real
    cruzado = FIXTURE_NOS_OK.replace(
        "ib->buf[ib->length_dw++] = (__u32)(addr & 0xFFFFFFFFu);",
        "ib->buf[ib->length_dw++] = (__u32)(flags & 0xFFFFFFFFu);")
    _i4, cuerpo4 = cuerpo_de(cruzado, "nos_emit")
    p_cruz = tabla_papeles(emisiones(cuerpo4))
    if p_ref == p_cruz:
        print("  FALLA memoria y Flags cruzados NO se detectan")
        fallos.append("campos cruzados no se detectan")
    else:
        print("  OK    memoria y flags cruzados se detectan")

    # el clasificador tiene que saber decir NO SE
    if papel("esto_no_es_un_campo(x, y)")[0] == "DESCONOCIDO":
        print("  OK    el clasificador declara DESCONOCIDO lo que no reconoce,")
        print("        en vez de inventarle un papel")
    else:
        print("  FALLA el clasificador le puso papel a una expresion sin forma")
        fallos.append("clasificador inventivo")

    # el opcode se SACA, no se escribe
    hdr = "#define SDMA_OP_GEN_PTEPDE  12\n"
    a, b = opcode_de("SDMA_PKT_HEADER_OP(SDMA_OP_GEN_PTEPDE)",
                     "rx550_sdma_header(RX550_SDMA_OP_GEN_PTEPDE)", hdr,
                     "#define RX550_SDMA_OP_GEN_PTEPDE 12\n")
    if a == 12 and b == 12:
        print("  OK    el opcode se resuelve en las dos fuentes sin escribirlo")
    else:
        print("  FALLA el opcode no se resolvio: corpus=%s nuestro=%s" % (a, b))
        fallos.append("opcode")
    c, _ = opcode_de("SDMA_PKT_HEADER_OP(SDMA_OP_GEN_PTEPDE)",
                     "rx550_sdma_header(RX550_SDMA_OP_GEN_PTEPDE)", hdr,
                     "#define RX550_SDMA_OP_GEN_PTEPDE 13\n")
    if c == 12 and _ == 13:
        print("  OK    dos opcodes distintos se ven distintos, que es lo que")
        print("        hace util resolverlo en vez de comparar el texto")
    else:
        print("  FALLA dos opcodes distintos no se distinguieron")
        fallos.append("opcode distinto")

    # el ANCHO, con dos anchos distintos y con uno CERO, que tambien es
    # invalido: un emisor que no emite nada no es un emisor
    if not _ancho_correcto(10, 10):
        print("  FALLA el control de ancho rechaza dos anchos iguales")
        fallos.append("ancho: falso positivo")
    elif _ancho_correcto(10, 9) or _ancho_correcto(0, 0):
        print("  FALLA el control de ancho NO separa anchos distintos ni el cero")
        fallos.append("ancho: no detecta")
    else:
        print("  OK    el ancho se comprueba y separa 10 de 9 y el caso de cero")

    # la UNICIDAD del brazo, con un vi.c sintetico de DOS brazos. El caso real
    # tiene uno solo, con lo que la comprobacion no se ejercita alli: sin este
    # vector, la mutacion que la relaja pasa.
    _vi2 = ("static void f(int a)\n{\n\tswitch (a) {\n"
            "\tcase CHIP_POLARIS12:\n"
            "\t\tamdgpu_device_ip_block_add(d, &sdma_v3_1_ip_block);\n"
            "\t\tbreak;\n\tcase CHIP_VEGA:\n"
            "\t\tamdgpu_device_ip_block_add(d, &sdma_v4_0_ip_block);\n"
            "\t\tbreak;\n\tdefault:\n\t\tbreak;\n\t}\n}\n"
            "static void g(int a)\n{\n\tswitch (a) {\n"
            "\tcase CHIP_POLARIS12:\n"
            "\t\tamdgpu_device_ip_block_add(d, &sdma_v3_0_ip_block);\n"
            "\t\tbreak;\n\tdefault:\n\t\tbreak;\n\t}\n}\n")
    if _bloque_del_brazo(_vi2) is not None:
        print("  FALLA dos brazos que anaden bloques IP y se elige UNO en silencio")
        print("        Dos tablas que dan dos ASIC para la misma etiqueta es una")
        print("        contradiccion del corpus, y elegir una seria inventar")
        fallos.append("unicidad del brazo")
    else:
        print("  OK    dos brazos que anaden bloques IP se declaran, no se eligen")

    # LA COMPARACION, no solo el clasificador
    if _diferencias(p_ref, p_ref):
        print("  FALLA la comparador da diferencias consigo mismo")
        fallos.append("comparacion: falso positivo")
    elif not _diferencias(p_ref, p_malo):
        print("  FALLA la comparacion no ve la diferencia que el clasificador ve")
        fallos.append("comparacion: no detecta")
    else:
        print("  OK    la comparacion no se ve a si misma y ve la diferencia real")

    print()
    if fallos:
        for f in fallos:
            print("  FALLA %s" % f)
        return 1
    print("  OK    todos los controles pasan")
    return 0


if __name__ == "__main__":
    sys.exit(main())