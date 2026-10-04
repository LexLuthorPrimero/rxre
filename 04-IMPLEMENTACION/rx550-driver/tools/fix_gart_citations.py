#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
#
# CONTRACT: name=fix_gart_citations
# CONTRACT: READONLY=no        (reescribe las citas de linea de los dos ficheros)
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no   (solo LEE el corpus)
# CONTRACT: WRITES_GPU=no
# VERSION: 1.0.0
"""
fix_gart_citations -- corrige las citas de linea del plan del GART, y las
VERIFICA en el mismo paso.

POR QUE ESTE SCRIPT Y NO UNA EDICION A MANO
    MEDIDO el 2026-10-04: de los 20 numeros del enum de orden de
    rx550_gart_seq.c, 1 era falso; de los 19 de la tabla ESPERADO de
    tests/test_gart_seq.c, 16 eran falsos.  El plan era correcto; la
    documentacion que lo acompanaba ya no lo era, y nadie lo noto porque NADIE
    verificaba esos numeros.

    Editarlos a mano los arregla una vez y los vuelve a pudrir en la siguiente.
    Este script los genera desde el corpus y ademas falla si lo que encuentra no
    es lo que dice, de modo que el numero deja de ser una observacion con fecha
    y pasa a ser una propiedad regenerable.

QUE TOCA, Y QUE NO
    rx550_gart_seq.c      solo los comentarios /* L... */ del enum de orden
    tests/test_gart_seq.c solo los comentarios /* L... */ de ESPERADO[]
    No toca ni el orden de las operaciones, ni los mnemonicos, ni el codigo.

COMO SE USA
    python3 fix_gart_citations.py --check    solo verifica, no escribe, rc!=0 si hay discrepancia
    python3 fix_gart_citations.py --fix      corrige
"""
import importlib.util
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
COMP = os.path.dirname(AQUI)
DRV = COMP   # el .c vive en el componente, no un nivel mas arriba

spec = importlib.util.spec_from_file_location("oracle", os.path.join(AQUI, "gart_seq_oracle.py"))
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)


def verdad_del_corpus():
    """-> (sitios, ejecuciones, rango).  Los sitios traen su linea REAL."""
    ruta = oracle._find("drivers/gpu/drm/amd/amdgpu/gmc_v8_0.c")
    if not ruta:
        sys.stderr.write("CORPUS_ABSENT: no se encuentra gmc_v8_0.c\n")
        sys.exit(2)
    ids = oracle._find("drivers/gpu/drm/amd/amdgpu/amdgpu_ids.h")
    lineas = open(ruta, errors="replace").read().split("\n")
    nv = oracle.ler_cota_vmid if False else None
    m = re.search(r"#define\s+%s\s+(\d+)" % oracle.VMIHUB_LOOP_BOUND_MACRO,
                  open(ids, errors="replace").read())
    nv = int(m.group(1)) if m else None
    if nv is None:
        sys.stderr.write("PARSE_AMBIGUOUS: no se encuentra %s\n"
                         % oracle.VMIHUB_LOOP_BOUND_MACRO)
        sys.exit(3)
    rng = oracle.localizar_funcion(lineas, oracle.FUNC_NAME)
    if rng is None:
        sys.stderr.write("PARSE_AMBIGUOUS: no se localiza %s\n" % oracle.FUNC_NAME)
        sys.exit(3)
    ops = oracle.extraer(lineas, rng[0], rng[1], nv)
    if ops is None:
        sys.stderr.write("PARSE_AMBIGUOUS: extraccion ambigua\n")
        sys.exit(3)
    ops = ops[:-1]
    ext = oracle._cuerpo_extento(lineas, rng[0], rng[1])
    n_fuera = sum(1 for o in ops if o["bucle"] is None)
    its = next((o["bucle"]["iteraciones"] for o in ops
                if o["bucle"] and o["bucle"]["iteraciones"]), 0)
    n_bucle = sum(1 for o in ops if o["bucle"] is not None)
    excl = oracle.ramas_excluyentes(lineas, ext)
    total = n_fuera + (its if excl else n_bucle * its)
    return ops, total, rng, n_fuera, its, excl


def main(argv):
    fix = "--fix" in argv
    ops, total, rng, n_fuera, its, excl = verdad_del_corpus()

    # El enum tiene 20 entradas.  Los 16 primeros sitios y el bucle y los tres
    # ultimos: es la misma particion que hace el .c, y se comprueba abajo con
    # el recuento, no se supone.
    lineas_por_sitio = [o["linea"] for o in ops]
    if len(lineas_por_sitio) != 21:
        sys.stderr.write("PARSE_AMBIGUOUS: %d sitios, se esperaban 21\n"
                         % len(lineas_por_sitio))
        sys.exit(3)
    # Los sitios 16 y 17 SON el bucle (sus dos WREG32, en ramas excluyentes).
    # El enum tiene UNA entrada para el bucle y luego las tres siguientes, asi
    # que hay que SALTAR los dos sitios del bucle: con lineas_por_sitio[16:]
    # el enum se corria una posicion y O_CTX1_PROT_FAULT recibia la linea del
    # bucle.  Dos sitios de bucle, una entrada de enum.
    enum_bucle = [o["linea"] for o in ops if o["bucle"] is not None]
    esperado_enum = lineas_por_sitio[:16] + [None] + lineas_por_sitio[18:]

    # ── rx550_gart_seq.c: el enum ────────────────────────────────────────
    p1 = os.path.join(DRV, "rx550_gart_seq.c")
    s = open(p1, errors="replace").read()
    orden = ["O_L1_TLB_CNTL", "O_L2_CNTL", "O_L2_CNTL2", "O_L2_CNTL3", "O_L2_CNTL4",
             "O_CTX0_PT_START", "O_CTX0_PT_END", "O_CTX0_PT_BASE", "O_CTX0_PROT_FAULT",
             "O_CTX0_CNTL2", "O_CTX0_CNTL", "O_IDA_LOW", "O_IDA_HIGH", "O_IDA_OFFSET",
             "O_CTX1_PT_START", "O_CTX1_PT_END", "O_CTX1_LOOP", "O_CTX1_PROT_FAULT",
             "O_CTX1_CNTL2", "O_CTX1_CNTL"]
    cambios1, discrepancias1 = [], []
    for i, nombre in enumerate(orden):
        pat = re.compile(
            r"(\b%s\s*=\s*0,|\b%s,)([^;]*?)/\*\s*L((?:[\d yL]*\d)?[^\n]*?)\*/"
            % (nombre, nombre))
        m = pat.search(s)
        if not m:
            discrepancias1.append("no se localiza la entrada %s" % nombre)
            continue
        if i == 16:
            nuevo = "L%d y L%d,  el bucle i = 1..%d" % (enum_bucle[0], enum_bucle[1], its)
            real = nuevo
        else:
            nuevo = "L%d" % esperado_enum[i]
            real = nuevo
        # Se normaliza el prefijo L a ambos lados: comparar "849" con "L849"
        # no es comparar nada, y daria 20 discrepancias falsas.
        escrito = re.sub(r"\s+", " ", m.group(3)).strip()
        escrito = re.sub(r"\bL(?=\d)", "", escrito)
        # Se comparan SOLO los tokens de linea, no la frase entera: el grupo
        # del regex corta en "912 y" porque despues viene una "L", y comparar
        # eso contra "L912 y L915,  el bucle i = 1..15" daria una discrepancia
        # FALSA.  Un verificador que se queja de lo que esta bien es tan
        # inutil como uno que no se queja de lo que esta mal.
        # `real` para el bucle trae un sufijo explicativo ("el bucle i = 1..15")
        # cuyos numeros NO son citas.  Se corta por la primera coma para que la
        # comparacion sea solo de las referencias de linea, que es lo que el
        # comentario afirma.
        toks = lambda t: re.findall(r"\d+", t)
        real_cita = real.split(",")[0]
        escrito_cita = escrito.split(",")[0]
        if toks(escrito_cita) != toks(real_cita):
            discrepancias1.append("%s: escrito '%s' real '%s'"
                                  % (nombre, escrito_cita, real_cita))
        if fix:
            # Se reemplaza el COMENTARIO ENTERO (desde los tabuladores que lo
            # preceden hasta el */), no solo el grupo de digitos.  Reemplazar
            # solo el grupo deja el "L" del comentario pegado al "L" nuevo y
            # produce "/* LL849*/", que es ruido puro.
            s = s[:m.start(2)] + "\t/* " + nuevo + " */" + s[m.end():]
            cambios1.append(nombre)

    # ── tests/test_gart_seq.c: ESPERADO[] ────────────────────────────────
    p2 = os.path.join(COMP, "tests", "test_gart_seq.c")
    t = open(p2, errors="replace").read()
    # op -> linea real.  Los ops 16..30 son el bucle.
    mapa = {}
    for k in range(16):
        mapa[k] = lineas_por_sitio[k]
    for k in range(16, 31):
        mapa[k] = None
    mapa[31] = lineas_por_sitio[18]
    mapa[32] = lineas_por_sitio[19]
    mapa[33] = lineas_por_sitio[20]

    discrepancias2, cambios2 = [], []
    def sub_esp(m):
        cuerpo, op, cita = m.group(1), int(m.group(2)), m.group(3)
        real = mapa.get(op)
        if real is None:
            nuevo = "L%d y L%d,  el bucle i = 1..%d" % (enum_bucle[0], enum_bucle[1], its)
            cmp_ = "L%d y L%d" % (enum_bucle[0], enum_bucle[1])
        else:
            nuevo = "L%d" % real
            cmp_ = nuevo
        toks = lambda t: re.findall(r"\d+", t)
        if toks(cita) != toks(cmp_):
            discrepancias2.append("ESPERADO op%d: escrito '%s' real '%s'"
                                  % (op, cita.strip(), cmp_))
            if fix:
                cambios2.append("op%d" % op)
        # cuerpo + ", op" + "  }, " + el comentario.  losing el ", op },"
        # haria que el test comprobara el mnemonico contra un indice corrupto.
        sep = cuerpo if cuerpo.endswith(" ") else cuerpo + " "
        return "%s%d  }, /* %s */" % (sep, op, nuevo)

        # mmMC_VM_MX_... empieza por mmMC y mmVM_L2_CNTL por mmVM: el tercer
    # caracter es M en ambos, y en mmVM_CONTEXT es V.  Por eso el patron
    # admite cualquier mayuscula ahi y no solo dos literales.
    pat2 = re.compile(r"(\{\s*\"mm[A-Z][^\"]*\"[^/]*?,\s*)(\d+)\s*\},\s*/\* L([\d y]+)[^\n]*\*/")
    t2 = pat2.sub(sub_esp, t)

    print("corpus: %s" % oracle._find("drivers/gpu/drm/amd/amdgpu/gmc_v8_0.c"))
    print("funcion: %s  %d..%d" % (oracle.FUNC_NAME, rng[0], rng[1]))
    print("ejecuciones: %d  (%d fuera + %d del bucle%s)"
          % (total, n_fuera, total - n_fuera,
             ", ramas excluyentes" if excl else ""))
    print("discrepancias enum:    %d" % len(discrepancias1))
    for d in discrepancias1:
        print("   - %s" % d)
    print("discrepancias ESPERADO: %d" % len(discrepancias2))
    for d in discrepancias2:
        print("   - %s" % d)

    if fix:
        open(p1, "w").write(s)
        open(p2, "w").write(t2)
        print("escritos %d entradas del enum y %d de ESPERADO" % (len(cambios1), len(cambios2)))

    return 1 if (discrepancias1 or discrepancias2) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))