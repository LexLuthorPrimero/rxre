#!/usr/bin/env python3
"""
emisor.py -- contrasta un emisor de paquetes NUESTRO contra el del driver de referencia,
dword a dword y por ROL, no por texto.

POR QUE HACE FALTA, y es la pieza que la suite declara no tener
-------------------------------------------------------------
07-DRIVER/tests/test_pm4.c cierra sus 208 checks y declara, en su propia salida:

    the provenance of the PTEPDE expectations is weaker than the PACKET3 ones.
    Those five headers were counted inside amdgpu.ko; PTEPDE cannot be, because a
    PTEPDE packet contains no PACKET3 header to count. Its expected values are
    transcribed from sdma_v4_0.c. A matching misreading in the encoder and in this
    test would pass.

Eso es una circularidad declarada: el codificador se escribio leyendo amdgpu, y las
expectativas del test se transcribieron del MISMO amdgpu. Un error de lectura
replicado en los dos sitios pasa las comprobaciones.

Y no es hipotetico. El dword 9 estuvo mal dos veces y en la direccion peligrosa:

    findings/023   leyo sdma_v3_0.c  y registro `count`        -- correcto
    findings/036   leyo sdma_v4_0.c  y "corrigio" a `count-1`  -- incorrecto
    038            lo revirtio a `count`

El "cross-check" que justificaba el cambio decia que "los otros dos productores de
este ASIC coinciden", y estaba leyendo sdma_v4_0.c: una comprobacion hecha sobre una
sola fuente no es una comprobacion cruzada, y citar dos lineas del mismo fichero
como si fueran dos fuentes es justo la forma que me engano.

Esta herramienta hace la comprobacion cruzada DE VERDAD, y hace algo que el
comentario manual no hacia: puede CORRER contra el fichero equivocado y mostrar que
el veredicto cambia. Ver CN-3.

LO QUE COMPARA, y por que por rol y no por texto
-------------------------------------------------
Las dos fuentes escriben la misma secuencia con sintaxis distinta:

    referencia   ib->ptr[ib->length_dw++] = lower_32_bits(pe);
    nuestro      ib->buf[ib->length_dw++] = (__u32)(pe & 0xFFFFFFFFu);

Esas dos lineas SON la misma operacion. Y estas otras dos NO:

    count        -> el campo es un numero de entradas
    count - 1    -> el campo es un numero de entradas menos uno

Comparar texto daria un falso positivo en la primera pareja y pasaria en la segunda
si el "-1" estuviera en otra linea, que es donde se escondio. Por eso cada expresion
se reduce a un ROL canonico y se comparan las listas de roles:

    lo32(X)  hi32(X)  HEADER(op)  incr  0  count  count-1

Un rol no reconocido NO se da por bueno: se marca DESCONOCIDO y la herramienta sale
distinta. Un validador que solo sabe decir "iguales" no es un validador.

ADEMAS: el conteo de dwords
---------------------------
RX550_SDMA_PTEPDE_DW vale 10 y se compara con el numero REAL de sentencias de
emision del emisor de referencia, que se cuenta aqui. La constante vive en un header
distinto del .c que la usa, y las dos puntas de la suite leian el MISMO header: es
coherencia, no validacion. Ademas su cita apuntaba a sdma_v4_0.c, el ASIC que no
corre en esta placa. El valor 10 es el mismo en los dos emisores, asi que el valor no
falla por el numero: falla la fuente que lo justifica.

LO QUE NO HACE, y son las tres limitaciones que hay que decir
-------------------------------------------------------------
1. No sabe si el silicio de esta pieza lee el campo como lo escribe el driver de
   referencia. Lo que hace es comparar contra lo que hace el driver de referencia, y
   para esta pieza lo mejor disponible es eso. PROVEN_DERIVED, no PROVEN.
2. No compila nada ni ejecuta hardware. Es ESTATICA.
3. Solo conoce las formas de emitter que puede reducir a rol. Un emisor nuevo con una
   forma que no conhece sale DESCONOCIDO, que es el fallo correcto.
"""

import os
import re
import sys

VERSION = "1"

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
CORPUS = os.path.join(RAIZ, "RESEARCH", "working", "linux-7.1.3")
AMDGPU = os.path.join(CORPUS, "drivers", "gpu", "drm", "amd", "amdgpu")
NUESBRO = os.path.join(RAIZ, "07-DRIVER", "kernel")

# El emisor de referencia que CORRE en esta pieza, y por que. Esta es la eleccion que
# esta herramienta hace falsable, y el motivo de que exista.
#
#   sdma_v3_0.c:987   SDMA_OP_GEN_PTEPDE   count      V2   <-- corre en CHIP_POLARIS12
#   sdma_v4_0.c:1649  SDMA_OP_PTEPDE       count - 1  V3   <-- no corre
#
# La cadena que lo sostiene esta en el corpus y se cita al pie. No es una preferencia.
REFERENCIA = {
    "fichero": os.path.join(AMDGPU, "sdma_v3_0.c"),
    "funcion": "sdma_v3_0_vm_set_pte_pde",
    "op": "SDMA_OP_GEN_PTEPDE",
    "linea_op": 987,
}
REFERENCIA_ALT = {
    "fichero": os.path.join(AMDGPU, "sdma_v4_0.c"),
    "funcion": "sdma_v4_0_vm_set_pte_pde",
    "op": "SDMA_OP_PTEPDE",
    "linea_op": 1649,
}

# ---------------------------------------------------------------- extraccion


def cuerpo_de_funcion(ruta, nombre):
    """Devuelve (lineas_del_cuerpo, linea_de_la_declaracion).

    Se para en la llave de cierre de SU nivel, contando llaves, y no en el primer
    '}' que aparece: los emitters de amdgpu llevan comentarios de bloque que contienen
    llaves de ejemplo, y parar en la primera daria un cuerpo truncado que compara bien
    contra otro cuerpo truncado y no dice nada.
    """
    with open(ruta, encoding="utf-8", errors="replace") as f:
        L = f.read().split("\n")
    ini = None
    for i, l in enumerate(L):
        if re.search(r"\b%s\s*\(" % re.escape(nombre), l):
            ini = i
            break
    if ini is None:
        raise SystemExit("no encuentro la funcion %s en %s" % (nombre, ruta))
    nivel = 0
    visto = False
    for j in range(ini, len(L)):
        nivel += L[j].count("{") - L[j].count("}")
        if "{" in L[j]:
            visto = True
        if visto and nivel == 0:
            return L[ini:j + 1], ini + 1
    raise SystemExit("no cierro la funcion %s en %s" % (nombre, ruta))


def sin_comentarios(L):
    """Quita comentarios de linea y de bloque.

    Sin esto, un comentario que COPIA el codigo de la otra generacion -- y el
    rx550_pm4.c tiene varios, que existen precisamente para documentar el count - 1 --
    se contaria como una emision mas, y el conteo de dwords saldria 11 en vez de 10.
    """
    out = []
    en_bloque = False
    for l in L:
        s = l
        if en_bloque:
            fin = s.find("*/")
            if fin < 0:
                continue
            s = s[fin + 2:]
            en_bloque = False
        # bloques que empiezan y acaban en la misma linea
        while "/*" in s:
            a = s.find("/*")
            b = s.find("*/", a + 2)
            if b < 0:
                s = s[:a]
                en_bloque = True
                break
            s = s[:a] + s[b + 2:]
        s = re.sub(r"//.*$", "", s)
        out.append(s)
    return out


def emisiones(cuerpo, patron_puntero):
    """Las sentencias '<ptr>[<idx>++] = <expr>;' en orden, como texto de expr.

    `patron_puntero` es una EXPRESION REGULAR, no un literal: los dos emisores llaman
    distinto al mismo campo -- `ib->ptr` el de amdgpu, `ib->buf` el nuestro -- y la
    version anterior de esta funcion lo pasaba por re.escape(), que escapa tambien la
    barra de la alternacion. `ib->ptr|ib->buf` deja de ser "uno de los dos" y pasa a
    ser el literal con una barra en medio, que no casa con nada: cero emisiones, y un
    contraste que no emite no dice nada. Un fallo silencioso que nace de hacer bien
    la cosa equivocada.
    """
    L = sin_comentarios(cuerpo)
    pat = re.compile(r"(?:%s)\s*\[[^\]]*\+\+\]\s*=\s*(.+?);" % patron_puntero)
    return [m.group(1).strip() for l in L for m in [pat.search(l)] if m]


# ------------------------------------------------------------------ rol canonico

def sin_casts(e):
    """Quita los casts: (__u32), (uint32_t), (unsigned int)...

    El driver de referencia escribe `lower_32_bits(pe)` y el nuestro `(__u32)(pe &
    0xFFFFFFFFu)`. Son la MISMA operacion con dos sintaxis, y hacer que el comparador
    las distinga seria un falso positivo. Quitar el cast primero deja el nucleo
    comparable, que es donde esta la diferencia que si importa: `count` contra
    `count - 1`.
    """
    for _ in range(3):
        nuevo = re.sub(r"\(\s*(?:(?:__)?u(?:int)?(?:8|16|32|64)(?:_t)?"
                       r"|unsigned\s+(?:int|long)|__u\d+)\s*\)", "", e)
        if nuevo == e:
            break
        e = nuevo
    # Y quitar los parentesis ENVOLVENTES que quedan al quitar el cast:
    # (__u32)(pe & 0xFFFFFFFFu) deja (pe & 0xFFFFFFFFu). Solo se quitan si el
    # parentesis que cierra es el ULTIMO caracter; `(a) + (b)` no se toca porque su
    # primer parentesis no cierra al final y no es un envoltorio.
    for _ in range(3):
        if not (e.startswith("(") and e.endswith(")")):
            break
        nivel = 0
        cierra_al_final = False
        for i, c in enumerate(e):
            if c == "(":
                nivel += 1
            elif c == ")":
                nivel -= 1
                if nivel == 0:
                    cierra_al_final = (i == len(e) - 1)
                    break
        if not cierra_al_final:
            break
        e = e[1:-1].strip()
    return e.strip()


def rol(expr):
    """Reduce una expresion a su rol canonico, o DESCONOCIDO con el texto."""
    e = sin_casts(expr.strip())
    # HEADER, y el NOMBRE del op entra en el rol a proposito. Una version anterior
    # devolvia "HEADER" sin mirar el op, y entonces el nuestro salia
    # HEADER:GEN_PTEPDE contra un HEADER a secas y las dos fuentes divergian en el
    # dword 0: un falso positivo que tapaba los nueve siguientes. El op es justo lo
    # que esta herramienta tiene que mirar.
    m = re.match(r"SDMA_PKT_HEADER_OP\s*\(\s*SDMA_OP_(\w+)\s*\)$", e)
    if m:
        return "HEADER:%s" % m.group(1)
    m = re.match(r"\w+\s*\(\s*RX550_SDMA_OP_(\w+)\s*\)$", e)
    if m:
        return "HEADER:%s" % m.group(1)
    m = re.match(r"lower_32_bits\s*\(\s*(\w+)\s*\)$", e)
    if m:
        return "LO32(%s)" % m.group(1)
    m = re.match(r"upper_32_bits\s*\(\s*(\w+)\s*\)$", e)
    if m:
        return "HI32(%s)" % m.group(1)
    m = re.match(r"(\w+)\s*&\s*0x[fF]{8}\w*$", e)
    if m:
        return "LO32(%s)" % m.group(1)
    m = re.match(r"(\w+)\s*>>\s*32$", e)
    if m:
        return "HI32(%s)" % m.group(1)
    # count y count - 1 tienen DOS defensas independientes, y esto se midio en vez de
    # suponerlo. Este comentarioOriginally decia "el orden importa": si `count` se
    # probase antes, el "- 1" casaria con COUNT y la herramienta pasaria el error que
    # existe para cazar. Es FALSO, y por dos motivos:
    #
    #   1. el patron de COUNT lleva ancla `$`, y "count - 1" no casa con `count$`
    #      con ningun orden de pruebas;
    #   2. aun sin ancla, COUNT_MENOS_UNO se prueba primero.
    #
    # Medido: quitar el ancla solo -> 16 de 16. Invertir el orden solo -> 16 de 16.
    # Quitar las dos cosas -> 12 de 16, y CN-7 reporta rc=0, o sea que la
    # herramienta habria dado verde al bug historico.
    #
    # Se conservan las dos defensas porque son baratas e independientes, y el comentario
    # va asi porque afirmar que el orden importa cuando no importa es un control que no
    # existe escrito como si existiera.
    if re.match(r"count\s*-\s*1$", e):
        return "COUNT_MENOS_UNO"
    if re.match(r"count$", e):
        return "COUNT"
    if re.match(r"incr$", e):
        return "INCR"
    if re.match(r"0$", e):
        return "CERO"
    return "DESCONOCIDO<%s>" % e


def roles_de(fichero, funcion, patron_puntero):
    cuerpo, lin = cuerpo_de_funcion(fichero, funcion)
    exprs = emisiones(cuerpo, patron_puntero)
    return [rol(e) for e in exprs], exprs, lin


# --------------------------------------------------------------------- contrato


def contrato(a, b, ca, cb):
    """Compara dos listas de roles. Devuelve (ok, lineas_de_informe)."""
    L = []
    if len(a) != len(b):
        L.append("  DIVERGE el CONTEO: referencia %d dwords, nuestro %d" % (len(a), len(b)))
    for i in range(min(len(a), len(b))):
        ok = a[i] == b[i]
        L.append("  dw%-2d %-4s ref=%-22s nuestro=%-22s   %s"
                 % (i, "OK" if ok else "MAL", a[i], b[i],
                    "" if ok else "<<< DIVERGE"))
    return all(x == y for x, y in zip(a, b)) and len(a) == len(b), L


def constante_de_dwords():
    ruta = os.path.join(NUESBRO, "rx550_pm4.h")
    with open(ruta, encoding="utf-8", errors="replace") as f:
        t = f.read()
    m = re.search(r"#define\s+RX550_SDMA_PTEPDE_DW\s+(\d+)(.*)", t)
    if not m:
        return None, "", ""
    return int(m.group(1)), m.group(2).strip(), ruta


def main(argv):
    if "--version" in argv:
        print("emisor.py %s" % VERSION)
        return 0
    if "--self" in argv:
        return selftest()
    if not os.path.isdir(AMDGPU):
        print("ERROR: no encuentro el corpus en %s" % AMDGPU)
        print("  sin el driver de referencia esta herramienta no tiene nada que contrastar")
        return 2

    ref = REFERENCIA
    if "--alt" in argv:
        ref = REFERENCIA_ALT
    nuestro = os.path.join(NUESBRO, "rx550_pm4.c")
    if "--nuestro" in argv:
        nuestro = argv[argv.index("--nuestro") + 1]

    print("emisor.py -- contraste emisor propio contra driver de referencia")
    print()
    print("  REFERENCIA  %s:%d  %s()" % (os.path.relpath(ref["fichero"], RAIZ),
                                         ref["linea_op"], ref["funcion"]))
    print("  NUESTRO     %s  rx550_sdma_vm_set_pte_pde()" % os.path.relpath(nuestro, RAIZ))

    roles_ref, expr_ref, lin_ref = roles_de(ref["fichero"], ref["funcion"],
                                            r"ib->(?:ptr|buf)")
    roles_nue, expr_nue, lin_nue = roles_de(nuestro, "rx550_sdma_vm_set_pte_pde",
                                            r"ib->(?:ptr|buf)")
    ok, informe = contrato(roles_ref, roles_nue, "ref", "nuestro")
    print()
    for l in informe:
        print(l)

    print()
    desc = [r for r in roles_ref if r.startswith("DESCONOCIDO")] + \
           [r for r in roles_nue if r.startswith("DESCONOCIDO")]
    if desc:
        print("  HAY ROLES QUE NO CONOZCO, y por eso no puedo llamar identicos a nada:")
        for d in desc:
            print("    %s" % d)
        print()
        print("  RESULT: DESCONOCIDO")
        return 1

    # La constante del header contra el conteo REAL de la referencia.
    dw, cita, ruta_h = constante_de_dwords()
    print()
    if dw is None:
        print("  RX550_SDMA_PTEPDE_DW: no encontrada en %s" % ruta_h)
        print("  RESULT: DESCONOCIDO")
        return 1
    conteo = len(roles_ref)
    print("  RX550_SDMA_PTEPDE_DW = %d   el emisor de referencia emite %d   %s"
          % (dw, conteo, "OK" if dw == conteo else "<<< DIVERGE"))
    if cita:
        fuente_ok = "sdma_v3_0" in cita
        print("  su cita dice: %s" % cita)
        if not fuente_ok:
            print("  AVISO: la cita NO apunta al emisor que corre en esta pieza.")
            print("          El valor %d coincide con los dos emisores, asi que el numero" % dw)
            print("          no falla; lo que falla es la fuente que lo justifica, y eso")
            print("          es lo que hizo que el dword 9 fuera del ASIC equivocado.")

    print()
    print("  RESULT: %s" % ("IDENTICOS" if ok and dw == conteo else "DIVERGEN"))
    if not (ok and dw == conteo):
        return 1
    print()
    print("  LIMITACION, y no es pequena: esto dice que nuestro emisor hace lo que el")
    print("  driver de referencia hace. NO dice que el silicio de esta pieza lea el")
    print("  campo como el driver lo escribe. Para eso haria falta hardware, y la")
    print("  GFX8 no lo da sin autorizacion.")
    return 0


# --------------------------------------------------------------------- selftest
#
# Un control negativo que no se ejecuta no controla nada. Los tres casos de abajo son
# los que hacen que la linea "RESULT: IDENTICOS" signifique algo.
def selftest():
    casos = []

    # CN-1  la extraccion cuenta los dwords de los DOS emisores
    a, _, la = roles_de(REFERENCIA["fichero"], REFERENCIA["funcion"], r"ib->(?:ptr|buf)")
    b, _, lb = roles_de(os.path.join(NUESBRO, "rx550_pm4.c"),
                        "rx550_sdma_vm_set_pte_pde", r"ib->buf")
    casos.append(("CN-1 el emisor de referencia emite 10 dwords",
                  len(a) == 10, "cuenta %d (linea %d)" % (len(a), la)))
    casos.append(("CN-1 nuestro emisor emite 10 dwords",
                  len(b) == 10, "cuenta %d (linea %d)" % (len(b), lb)))

    # CN-2  el dword 9 tiene que ser COUNT y no COUNT_MENOS_UNO. Este es EL error, y
    #       el orden de PATRONES es lo que lo hace cazable.
    casos.append(("CN-2 el dword 9 de la referencia es COUNT",
                  a[9] == "COUNT", "es %s" % a[9]))
    casos.append(("CN-2 nuestro dword 9 es COUNT, no COUNT_MENOS_UNO",
                  b[9] == "COUNT", "es %s" % b[9]))

    # CN-2b la forma mutada TIENE que divergir. Si `count - 1` no divergiera, el
    #        control de CN-2 no estaria probando el error que dice probar.
    mut = list(a)
    mut[9] = "COUNT_MENOS_UNO"
    ok_mut, _ = contrato(a, mut, "a", "b")
    casos.append(("CN-2b una forma con count-1 DIVERGE (control negativo real)",
                  not ok_mut, "la comparacion dice %s" % ("identicos" if ok_mut else "divergen")))

    # CN-3  el contraste CONTRA EL OTRO ASIC tiene que dar otro veredicto. Esta es la
    #       prueba de que elegir la fuente no es decorativo: el mismo codigo nuestro
    #       es IDENTICO contra sdma_v3_0 y DIVERGE contra sdma_v4_0.
    alt, _, lalt = roles_de(REFERENCIA_ALT["fichero"], REFERENCIA_ALT["funcion"],
                            r"ib->(?:ptr|buf)")
    casos.append(("CN-3 el otro ASIC emite tambien 10 dwords",
                  len(alt) == 10, "cuenta %d (linea %d)" % (len(alt), lalt)))
    casos.append(("CN-3 el otro ASIC pone COUNT_MENOS_UNO en el dword 9",
                  alt[9] == "COUNT_MENOS_UNO", "es %s" % alt[9]))
    ok_alt, _ = contrato(alt, b, "alt", "nuestro")
    casos.append(("CN-3 nuestro codigo DIVERGE contra el ASIC que no corre",
                  not ok_alt, "veredicto %s" % ("identicos" if ok_alt else "divergen")))
    casos.append(("CN-3 y por tanto la fuente elegida cambia el veredicto",
                  contrato(a, b, "a", "b")[0] and not ok_alt,
                  "v3=%s  v4=%s" % (contrato(a, b, "a", "b")[0], ok_alt)))

    # CN-4  una expresion desconocida no se da por buena
    casos.append(("CN-4 una expresion no reconocida sale DESCONOCIDO",
                  rol("algo_raro(pe, 3)").startswith("DESCONOCIDO"),
                  rol("algo_raro(pe, 3)")))

    # CN-5  los comentarios NO cuentan como emisiones. El .c tiene comentarios que
    #       COPIAN el codigo de la otra generacion, y sin esto el conteo saldria 11.
    cuerpo = ["void f(void) {",
              "\t/* ib->ptr[ib->length_dw++] = count - 1; */",
              "\tib->buf[ib->length_dw++] = count;",
              "}"]
    casos.append(("CN-5 un comentario con codigo NO cuenta como emision",
                  emisiones(cuerpo, r"ib->buf") == ["count"],
                  "emite %s" % emisiones(cuerpo, r"ib->buf")))

    # CN-6  la constante del header contra el conteo real de la referencia
    dw, cita, _ = constante_de_dwords()
    casos.append(("CN-6 RX550_SDMA_PTEPDE_DW coincide con las 10 de la referencia",
                  dw == len(a), "constante %s, referencia %d" % (dw, len(a))))

    # CN-7  END TO END: main() tiene que LEER el fichero que dice leer.
    #
    # Este caso existe por un fallo real de esta herramienta, no por teoria. La primera
    # version de main() imprimia la ruta que le daba --nuestro en la cabecera pero leia
    # la ruta fija, porque el replace que la cambio no casaba y no se comprobo. La
    # cabecera decia "estoy leyendo la copia mutada" mientras leia el original, y las
    # dos mutaciones de prueba pasaban con exit=0: la herramienta que existe para cazar
    # count-1 no cazaba count-1.
    #
    # Y el fallo era invisible en el self-test, porque los casos usaban la libreria
    # directamente y no main(). Un self-test que ejercita la libreria no prueba el
    # programa: prueba las funciones que el programa llama, y el cableado entre ellas
    # es justo donde estaba el fallo.
    #
    # Asi que aqui se ejecuta main() de verdad, con un fichero mutado de verdad, y se
    # comprueban las DOS cosas: que DIVERGE, y que el codigo de salida es 1.
    import tempfile
    import shutil
    real = os.path.join(NUESBRO, "rx550_pm4.c")
    if os.path.exists(real):
        with open(real, encoding="utf-8") as f:
            texto = f.read()
        mutado = texto.replace("ib->buf[ib->length_dw++] = count;",
                               "ib->buf[ib->length_dw++] = count - 1;")
        casos.append(("CN-7 el fichero mutado difiere del original",
                      mutado != texto, "la mutacion se aplico"))
        if mutado != texto:
            tmpd = tempfile.mkdtemp(prefix="emisor-cn7-")
            try:
                ruta = os.path.join(tmpd, "rx550_pm4.c")
                with open(ruta, "w", encoding="utf-8") as f:
                    f.write(mutado)
                import io
                import contextlib
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rc = main(["--nuestro", ruta])
                salida = buf.getvalue()
                casos.append(("CN-7 main() DIVERGE contra el fuente mutado",
                              "DIVERGEN" in salida, "rc=%s" % rc))
                casos.append(("CN-7 main() sale con codigo 1, no con 0",
                              rc == 1, "rc=%s" % rc))
                casos.append(("CN-7 y senala EL dword, no solo que diverge",
                              "dw9" in salida and "COUNT_MENOS_UNO" in salida,
                              "el dword 9 es el divergente"))
            finally:
                shutil.rmtree(tmpd, ignore_errors=True)

    print("emisor.py --self: control negativo del contraste de emisores")
    print()
    fallos = 0
    for nombre, ok, det in casos:
        if not ok:
            fallos += 1
        print("  %-58s %-4s %s" % (nombre, "OK" if ok else "FALLA", det))
    print()
    print("  %d de %d casos pasan" % (len(casos) - fallos, len(casos)))
    if fallos:
        print("  NO todos pasan")
        return 1
    print("  todos pasan")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))