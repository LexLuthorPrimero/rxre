#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""regconst.py - cada constante de registro del driver propio, con su fuente.

POR QUE

AGENTS.md §IMPLEMENTATION_GATE no permite implementar una semantica porque
existe en otro sitio. Para una DIRECCION de registro eso se traduce en algo
muy concreto: cada `#define MM_... 0x2e12` del driver tiene que tener una
linea del corpus que diga lo mismo, en el fichero del ASIC correcto.

Sin esta comprobacion, un offset equivocado no falla: se compila, se escribe
en una IB, y el fallo aparece como "el shader no calcula", que no dice nada
sobre la causa. En esta sesion una tabla de nombres de opcode escrita de
memoria tenia SIETE entradas equivocadas y nadie lo vio hasta que un test
comprobo un valor. Un offset equivocado es el mismo error con menos sintomas.

QUE CLASES DISTINGUE

  PROVEN_POR_CITA    el #define declara su procedencia en el comentario de cola
                     y esa linea del corpus define ESE valor. Es la via fuerte:
                     el driver ya dice de donde sale y se comprueba
  PROVEN             el corpus define ese nombre con ESE valor, y el fichero
                     pertenece a la generacion de este ASIC
  CITA_CON_OTRO_VALOR la cita del propio #define resuelve a otra linea, y esa
                     linea tiene otro valor: la procedencia es incorrecta
  VALOR_DISCREPANTE  el corpus lo define con OTRO valor: el driver se equivoca
                     y se sabe exactamente en cuanto
  GENERACION_DIFIERE existe, pero en un _d.h de otra generacion: el valor
                     puede ser correcto y la autoridad no, que es el caso de
                     RX550_SDMA_OP_PTEPDE con vega10 (findings/147)
  NO_EN_CORPUS       no existe. NO es "el registro no existe": es "no lo he
                     encontrado", y por eso NO_SE_BUSCA en vez de AUSENTE
  FUERA_DE_BAR2       el valor no cabe en el BAR de 2 MiB medido en findings/176
                     -- el registro no estaria donde el driver lo pondria

LA NORMALIZACION Y POR QUE NO ES ADIVINAR

El driver escribe `MM_COMPUTE_PGM_RSRC1` y el corpus escribe
`mmCOMPUTE_PGM_RSRC1`. La regla es una sola y se declara: `MM_` -> `mm`. Con
esa regla, las seis constantes de registro del driver resuelven contra
gfx_8_0_d.h con el valor correcto -- 6 de 6, medido antes de escribir esto.

Si la normalizacion hiciera falta mas que un prefijo, la herramienta lo dira
en vez de intentar mas transformaciones: un resolvedor que "adivina el nombre"
convierte un fallo de evidencia en un verde.

USO

    regconst.py               tabla completa
    regconst.py --json        para componer
    regconst.py --solo MAL    solo lo que hay que arreglar
    regconst.py --selftest    vectores sinteticos
"""

import argparse
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRIVER = os.path.join(RAIZ, "07-DRIVER")

CORPUS_POR_DEFECTO = (
    os.path.join(RAIZ, "RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd"),
    os.path.join(RAIZ, "rx550-upstream-7.2.8/linux-7.2.8/drivers/gpu/drm/amd"),
)

# findings/176, medido por stat() sin root: resource2 mide 2097152 bytes.
TAMANO_BAR2 = 2 * 1024 * 1024

# Un #define del driver con valor literal numerico
# El comentario de cola se ADMITE y hasta se lee: en el driver, el comentario
# de un #define es justo su procedencia -- `0x54f  /* gmc_8_1_d.h:636 */` -- y
# una version anterior exigia fin de linea, con lo cual las tres constantes que
# citan su fuente no se leian. Perder justo las que llevan citacion es perder
# las mas fiables.
RE_DEFINE = re.compile(r"^[ \t]*#[ \t]*define[ \t]+(?P<nom>MM_[A-Za-z0-9_]+)[ \t]+"
                       r"(?P<val>0[xX][0-9a-fA-F]+|[0-9]+)[ \t]*"
                       r"(?P<cola>(?://[^\n]*|/\*.*?\*/)?)[ \t]*$", re.M)
RE_DEFINE_RX = re.compile(r"^[ \t]*#[ \t]*define[ \t]+(?P<nom>RX550_[A-Za-z0-9_]+)"
                        r"(?P<cola>[^\n=]*?)\s+(?P<val>0[xX][0-9a-fA-F]+)"
                        r"[ \t]*(?P<citacion>(?://[^\n]*|/\*.*?\*/)?)[ \t]*$", re.M)

# Que nombres cuentan como "registro". El criterio tiene que cubrir lo que el
# driver USA, no lo que uno adivina: el driver llama a sus tres registros de
# GMC `RX550_MM_VM_...`, con el prefijo de delante, y una primera version que
# solo aceptaba `^MM_` se los comio. Reporto 5 de 8 constantes, todas
# PROVEN, y no dijo nada de las tres que faltan -- un total sin denominador es
# un total que no significa nada.
#
# Acepta: MM_ al principio, MM_ o _MM_ en cualquier punto, o _REG/_ADDR al
# final. Lo que NO se acepta es un opcode de paquete, que no es una direccion.
RE_NOMBRE_REGISTRO = re.compile(r"(^MM_|_MM_|^mm|_REG$|_ADDR$|^RX550_MM_)")
# PERO con una excluyente: `RX550_PKT3_SET_SH_REG` termina en _REG y es un
# opcode de paquete, no una direccion. Sin esta excluyente salia
# NO_EN_CORPUS para algo que no deberia estar en la tabla, y un NO_EN_CORPUS
# de mas es peor que uno de menos: dice "no lo he encontrado" cuando lo que
# pasa es "esto no es de esta clase".
RE_NO_ES_REGISTRO = re.compile(r"(^RX550_PKT3_|^RX550_SDMA_OP_|PACKET3_|_DW$)")


def a_numero(txt):
    return int(txt, 16) if txt.lower().startswith("0x") else int(txt)


def normaliza(nombre):
    """`MM_COMPUTE_X` -> `mmCOMPUTE_X`, `RX550_MM_VM_X` -> `mmVM_X`.

    Dos reglas, y las dos están medidas contra el corpus: las seis constantes
    MM_ y las tres RX550_MM_ resuelven con el valor correcto. Si hiciera falta
    una tercera transformacion, esta herramienta lo diría con un
    NO_EN_CORPUS en vez de intentar mas: un resolvedor que adivina el nombre
    convierte un fallo de evidencia en un verde.
    """
    if nombre.startswith("RX550_"):
        nombre = nombre[len("RX550_"):]
    if nombre.startswith("MM_"):
        return "mm" + nombre[3:]
    return nombre


RE_CORPUS_DEFINE = re.compile(
    r"#[ \t]*define[ \t]+(?P<nom>[A-Za-z_][A-Za-z0-9_]*)[ \t]+"
    r"(?P<val>0[xX][0-9a-fA-F]+)")


RE_CITACION = re.compile(r"(?P<fic>[A-Za-z0-9_.+-]+\.[ch]):(?P<lin>\d+)")


def extraer_citacion(declaracion):
    """De `/* gmc_8_1_d.h:636 */` saca ('gmc_8_1_d.h', 636).

    Es la via fuerte. El driver declara de donde sale cada constante, y esa
    declaracion es mas fiable que cualquier coincidencia de nombres: el corpus
    llama `mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR` a lo que el driver llama
    `MM_VM_CONTEXT0_PTBA`, asi que el emparejamiento por nombre da
    NO_EN_CORPUS sobre un registro que existe y que el propio driver ya cita.
    Verificar la cita es lo que convierte "creo que se" en "esta ahi".
    """
    if not declaracion:
        return None
    m = RE_CITACION.search(declaracion)
    return (m.group("fic"), int(m.group("lin"))) if m else None


def indexar_corpus(raices):
    """{nombre: [(valor, fichero, linea)]} para todos los #define con valor."""
    idx = {}
    posiciones = {}
    for raiz in raices:
        if not os.path.isdir(raiz):
            continue
        for dirpath, dirnames, filenames in os.walk(raiz):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for fn in sorted(filenames):
                if not fn.endswith(".h"):
                    continue
                ruta = os.path.join(dirpath, fn)
                try:
                    texto = open(ruta, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                # El patron va SIN ANCLAS a proposito. Con ^[ \t]* y [ \t]*$
                # en modo multilinea, sobre 476 cabeceras y 470 MB, la cosa no
                # acaba nunca. Sin anclas va a velocidad de escaneo, pero eso
                # permitiria dar por bueno un #define escrito DENTRO de un
                # comentario, que es justo la clase de error que esta
                # herramienta existe para no repetir. Asi que el '#' se
                # comprueba a mano: indice 0 o detras de un salto de linea.
                #
                # Y el numero de linea se cuenta de forma INCREMENTAL, no con
                # texto[:ini].count("\n"). La primera version hacia eso, y es
                # cuadratico: con ~194000 coincidencias sobre ficheros de
                # 20 MB, contar el prefijo cada vez son miles de millones de
                # operaciones por fichero. finditer devuelve las coincidencias
                # en orden, asi que basta con avanzar un cursor.
                rel = os.path.relpath(ruta, RAIZ)
                cursor = 0
                linea = 1
                for m in RE_CORPUS_DEFINE.finditer(texto):
                    ini = m.start()
                    if ini != 0 and texto[ini - 1] != "\n":
                        continue
                    linea += texto.count("\n", cursor, ini)
                    cursor = ini
                    n, v = m.group("nom"), a_numero(m.group("val"))
                    idx.setdefault(n, []).append((v, rel, linea, n))
                    # Indice INVERSO por posicion. Una cita dice fichero y
                    # linea, no nombre, asi que verificarla necesita poder
                    # preguntar "que hay definido en ESTA linea". Buscando
                    # dentro de los candidatos de nombre la verificacion de la
                    # cita no podia funcionar justo en los casos que mas la
                    # necesitan: PTBA frente a PAGE_TABLE_BASE_ADDR.
                    posiciones.setdefault((os.path.basename(rel), linea),
                                           []).append((n, v))
    return idx, posiciones


# Ficheros _d.h que son de una generacion que NO corre en esta GPU. Sirven para
# distinguir VALOR_DISCREPANTE de GENERACION_DIERE: el valor puede ser el
# correcto y aun asi la autoridad equivocada, que es findings/147.
NO_ESTA_GENERACION = re.compile(r"_(6_0|7_[02]|10|11|12|14|20|21|24)_(d|enum)\.h$")


def medir(corpus=None, driver=None):
    corpus = corpus or list(CORPUS_POR_DEFECTO)
    driver = driver or DRIVER
    idx, posiciones = indexar_corpus(corpus)
    filas = []
    for sub in ("kernel", "tests", "driver"):
        base = os.path.join(driver, sub)
        if not os.path.isdir(base):
            continue
        for fn in sorted(os.listdir(base)):
            if not fn.endswith((".c", ".h")):
                continue
            ruta = os.path.join(base, fn)
            texto = open(ruta, encoding="utf-8", errors="replace").read()
            for m in RE_DEFINE.finditer(texto):
                nombre = m.group("nom")
                val = a_numero(m.group("val"))
                filas.append(dict(fichero=os.path.relpath(ruta, driver),
                                  linea=texto[:m.start()].count("\n") + 1,
                                  nombre=nombre, valor=val, forma="MM_",
                                  declaracion=(m.group("cola") or "").strip()))
            for m in RE_DEFINE_RX.finditer(texto):
                nombre = m.group("nom")
                # se recogen TODOS los RX550_ con valor y decide el clasificador,
                # para que un criterio que se queda corto se vea como una caida
                # de cobertura y no como un corpus mas pequeno
                filas.append(dict(fichero=os.path.relpath(ruta, driver),
                                  linea=texto[:m.start()].count("\n") + 1,
                                  nombre=nombre, valor=a_numero(m.group("val")),
                                  forma="RX550_",
                                  declaracion=(m.group("citacion") or "").strip()))
    # clasificar
    for f in filas:
        if RE_NO_ES_REGISTRO.search(f["nombre"]) or \
                not RE_NOMBRE_REGISTRO.search(f["nombre"]):
            # No es una direccion de registro: es un opcode de paquete, una
            # mascara o un enumerado. Se cuenta aparte y no se deja fuera en
            # silencio, porque un total que solo dice "de estos N" no deja ver
            # cuantos se quedaron fuera por el criterio.
            f["clase"] = "NO_ES_REGISTRO"
            f["fuentes"] = []
            continue
        objetivo = normaliza(f["nombre"])
        occ = idx.get(objetivo) or idx.get(f["nombre"])
        f["buscado"] = objetivo
        # Se comprueba PRIMERO la cita propia del #define, si la lleva. Es la
        # via fuerte: el corpus llama `mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR` a lo
        # que el driver llama `MM_VM_CONTEXT0_PTBA`, asi que el emparejamiento
        # por nombre da NO_EN_CORPUS sobre un registro que existe y que el
        # propio driver ya cita. Verificar la cita convierte "creo que se" en
        # "esta ahi, y en esa linea".
        cit = extraer_citacion(f.get("declaracion"))
        f["cita"] = cit
        if cit:
            alla = posiciones.get(cit, [])
            if alla:
                coincide = [x for x in alla if x[1] == f["valor"]]
                f["fuentes"] = [dict(fichero=cit[0], linea=cit[1],
                                     nombre=x[0], valor=x[1]) for x in alla[:3]]
                f["clase"] = ("PROVEN_POR_CITA" if coincide
                              else "CITA_CON_OTRO_VALOR")
                continue
        if not occ:
            f["clase"] = "NO_EN_CORPUS"
        else:
            propios = [o for o in occ if not NO_ESTA_GENERACION.search(o[1])]
            candidatos = propios or occ
            if any(o[0] == f["valor"] for o in propios):
                f["clase"] = "PROVEN"
            elif any(o[0] == f["valor"] for o in occ):
                f["clase"] = "GENERACION_DIERE"
            else:
                f["clase"] = "VALOR_DISCREPANTE"
            f["fuentes"] = [dict(fichero=o[1], linea=o[2], nombre=o[3],
                                 valor=o[0]) for o in candidatos[:3]]
        if f["valor"] >= TAMANO_BAR2:
            f["clase"] = "FUERA_DE_BAR2"
    return filas


def selftest():
    d = "/tmp/opencode/regconst-selftest"
    os.system("rm -rf %s" % d)
    os.makedirs(os.path.join(d, "include/asic_reg/gca"))
    os.makedirs(os.path.join(d, "amdgpu"))
    with open(os.path.join(d, "include/asic_reg/gca/gfx_8_0_d.h"), "w") as f:
        f.write("#define mmCOMPUTE_PGM_RSRC1 0x2e12\n"
                "#define mmCOMPUTE_PGM_LO 0x2e0c\n"
                "#define mmOTRO_GENERACION 0x1234\n")
    with open(os.path.join(d, "include/asic_reg/gca/navi10_d.h"), "w") as f:
        f.write("#define mmOTRO_GENERACION 0xbeef\n")
    with open(os.path.join(d, "amdgpu/amdgpu.h"), "w") as f:
        f.write("#define mmEN_EL_DRIVER 0x50e\n")

    idx, pos = indexar_corpus([d])
    vectores = []
    vectores.append(("la normalizacion MM_ -> mm resuelve el nombre real",
                     "mmCOMPUTE_PGM_RSRC1" in idx, sorted(idx)[:4]))
    vectores.append(("el valor se indexa como numero, no como cadena",
                     idx["mmCOMPUTE_PGM_RSRC1"][0][0] == 0x2e12,
                     idx["mmCOMPUTE_PGM_RSRC1"][0]))
    # Por CONTENIDO y no por POSICION. La primera version de este vector
    # miraba idx[...][0] y asumia un orden de recorrido; al reordenar el
    # sistema de ficheros fallo sin que cambiara nada del codigo. Es el mismo
    # error que en citeambig.py: un vector que exige un orden esta probando el
    # recorrido del directorio y no el clasificador.
    vals = sorted(o[0] for o in idx["mmOTRO_GENERACION"])
    vectores.append(("una generacion ajena se indexa con su propio valor, no se mezcla",
                     vals == [0x1234, 0xbeef], vals))
    vectores.append(("un valor repetido en el corpus se conserva cada vez",
                     len(idx["mmOTRO_GENERACION"]) == 2, len(idx["mmOTRO_GENERACION"])))
    vectores.append(("un nombre ausente NO aparece en el indice",
                     "mmNO_EXISTE" not in idx, "ok"))
    vectores.append(("el indice inverso responde por fichero y linea",
                     ("gfx_8_0_d.h", 1) in pos
                     and pos[("gfx_8_0_d.h", 1)] == [("mmCOMPUTE_PGM_RSRC1", 0x2e12)],
                     pos.get(("gfx_8_0_d.h", 1))))
    vectores.append(("una linea que no define nada no esta en el indice inverso",
                     ("gfx_8_0_d.h", 99) not in pos, "ok"))
    # --- el clasificador, que es donde se decide y donde no habia vectores ---
    # El selftest anterior solo cubria el indice. La parte que clasifica -- la
    # que produce PROVEN, NO_EN_CORPUS, CITA_CON_OTRO_VALOR -- no tenia una
    # sola comprobacion, que es como se deja que la logica mas importante sea
    # la unica que nadie rompe a proposito.
    d2 = "/tmp/opencode/regconst-clasif"
    os.system("rm -rf %s" % d2)
    os.makedirs(os.path.join(d2, "corpus/include/asic_reg/gca"))
    os.makedirs(os.path.join(d2, "drv/kernel"))
    with open(os.path.join(d2, "corpus/include/asic_reg/gca/gfx_8_0_d.h"), "w") as f:
        f.write("#define mmBUENO 0x100\n"
                "#define mmOTRO 0x200\n"
                "#define mmLADO 0x300\n")
    with open(os.path.join(d2, "corpus/include/asic_reg/gca/navi10_d.h"), "w") as f:
        f.write("#define mmDE_OTRA_GEN 0x999\n")
    with open(os.path.join(d2, "drv/kernel/k.h"), "w") as f:
        f.write("#define MM_BUENO 0x100\n"
                "#define MM_OTRO 0x999\n"
                "#define MM_LADO 0x555  /* gfx_8_0_d.h:3 */\n"
                "#define MM_SIN_CITA 0x777\n"
                "#define RX550_PKT3_SET_SH_REG 0x76\n"
                "#define RX550_ALGO 0x42\n")

    filas = medir(corpus=[os.path.join(d2, "corpus")],
                  driver=os.path.join(d2, "drv"))
    por_nombre = {f["nombre"]: f for f in filas}

    def clase_de(nombre):
        return por_nombre.get(nombre, {}).get("clase", "AUSENTE_DE_LA_LISTA")

    vectores.append(("nombre y valor correctos: PROVEN",
                     clase_de("MM_BUENO") == "PROVEN", clase_de("MM_BUENO")))
    vectores.append(("el mismo nombre con OTRO valor: VALOR_DISCREPANTE",
                     clase_de("MM_OTRO") == "VALOR_DISCREPANTE",
                     clase_de("MM_OTRO")))
    vectores.append(("cita a una linea con otro valor: CITA_CON_OTRO_VALOR",
                     clase_de("MM_LADO") == "CITA_CON_OTRO_VALOR",
                     clase_de("MM_LADO")))
    vectores.append(("sin cita y sin nombre en el corpus: NO_EN_CORPUS",
                     clase_de("MM_SIN_CITA") == "NO_EN_CORPUS",
                     clase_de("MM_SIN_CITA")))
    vectores.append(("un opcode de paquete NO entra en la tabla de registros",
                     clase_de("RX550_PKT3_SET_SH_REG") == "NO_ES_REGISTRO",
                     clase_de("RX550_PKT3_SET_SH_REG")))
    vectores.append(("el total incluye los NO_ES_REGISTRO, no solo los registros",
                     len(filas) == 6, "%d filas" % len(filas)))
    # el corpus con otra generacion: mmDE_OTRA_GEN solo existe en navi10_d.h, y
    # MM_OTRO usa su valor 0x999, que es el de la OTRA generacion
    vectores.append(("un valor que solo existe en otra generacion NO es PROVEN "
                     "de esta", clase_de("MM_OTRO") != "PROVEN",
                     clase_de("MM_OTRO")))
    os.system("rm -rf %s" % d2)

    vectores.append(("a_numero entiende hexadecimal y decimal",
                     a_numero("0x2e12") == 0x2e12 and a_numero("16") == 16, "ok"))
    os.system("rm -rf %s" % d)

    # --- el filtro --solo, MEDIDO 2026-10-04 (nodo FILTROS-REPARO-2) ---
    #
    # El selftest anterior NO podia ver este defecto: no tenia ni un vector que
    # pasara un nombre de clase que no existe. Es el mismo motivo que el arreglo
    # de lint.py:953-954 -- un vector que solo prueba el caso bueno deja el
    # caso malo sin red.
    #
    # Se prueba sobre `filas` sinteticas, NO sobre el driver real: una
    # comprobacion que depende de 30 s de escaneo del corpus no es un vector de
    # selftest, es una medida disfrazada.
    demo = [dict(clase="NO_EN_CORPUS", nombre="MM_A", valor=1,
                 fichero="k.h", linea=1, fuentes=[]),
            dict(clase="NO_EN_CORPUS", nombre="MM_B", valor=2,
                 fichero="k.h", linea=2, fuentes=[]),
            dict(clase="PROVEN", nombre="MM_C", valor=3,
                 fichero="k.h", linea=3, fuentes=[])]
    clases_demo = sorted({r["clase"] for r in demo})
    vectores.append(("--solo: la poblacion de clases se calcula de la medicion",
                     clases_demo == ["NO_EN_CORPUS", "PROVEN"], clases_demo))
    vectores.append(("--solo: un nombre de clase que existe pasa la validacion",
                     "NO_EN_CORPUS" in clases_demo
                     and [r for r in demo if r["clase"] == "NO_EN_CORPUS"]
                     == demo[:2], "ok"))
    # Y el camino REAL de main(), no una reconstruccion del arbol de decision.
    # Se sustituye `medir` por las filas sinteticas y se invoca main() con argv
    # de verdad. Es lo unico que prueba el rc, que es la mitad del arreglo: un
    # vector que comprueba una funcion auxiliar no sabe si main() la llama.
    #
    # Sustituir `medir` es lo que hace esto instantaneo. Sin eso, el selftest
    # tardaria los 30 s del escaneo del corpus en cada vector, y un selftest que
    # tarda 30 s por vector no se ejecuta nunca.
    import io
    import contextlib

    medir_real = medir

    def invoca(argv):
        global medir
        argv_real = sys.argv
        buf = io.StringIO()
        try:
            medir = lambda corpus=None, driver=None: list(demo)
            sys.argv = ["regconst.py"] + argv
            with contextlib.redirect_stdout(buf):
                rc = main()
        finally:
            medir = medir_real
            sys.argv = argv_real
        return rc, buf.getvalue()

    rc, txt = invoca(["--solo", "NO_EN_CORPUS"])
    # La fila se imprime como "  <clase> <nombre> 0x<valor>", o sea que el
    # nombre NO va al principio de la linea. Y el texto de las clases, arriba, y
    # el parrafo de cierre, abajo, empiezan igual. Anclar al valor y no a la
    # posicion: es el mismo criterio que exige el orculo de la puerta, y un
    # detector que mira por una palabra suelta cuenta cuatro filas donde hay dos.
    filas_txt = [l for l in txt.splitlines()
                 if l.startswith("  NO_EN_CORPUS ") and "0x" in l]
    vectores.append(("--solo de una clase real: rc=0 y las filas SON las de esa clase",
                     rc == 0 and len(filas_txt) == 2
                     and "MM_A" in txt and "MM_B" in txt and "MM_C" not in txt,
                     "%d filas, rc=%r" % (len(filas_txt), rc)))
    vectores.append(("--solo: el resumen cuenta lo mostrado, no las 3 filas totales",
                     "2 #define con valor leidos" in txt
                     and "NO_EN_CORPUS 2" in txt and "PROVEN 1" not in txt,
                     [l for l in txt.splitlines() if "#define con valor" in l]))
    for malo in ("CLASE_QUE_NO_EXISTE", "GRAF_8_0", "no_en_corpus"):
        rc, txt = invoca(["--solo", malo])
        # El mensaje tiene que ANCLARSE AL VALOR pedido. Un orculo que aceptara
        # cualquier "no existe" de la salida daria un OK falso aqui, que es
        # exactamente el fallo que hizo pasar por buena a hwip.py en el orculo
        # ancho de la puerta (§8.3-bis del censo).
        vectores.append(("--solo %s: rc=2 nombrando el valor y las clases que SI hay"
                         % malo,
                         rc == 2 and ("--solo %s" % malo) in txt
                         and "NO_EN_CORPUS" in txt and "PROVEN" in txt
                         and "No se ha medido nada" in txt,
                         "rc=%r" % rc))
        rc, txt = invoca(["--json", "--solo", malo])
        vectores.append(("--json --solo %s: rc=2 y NINGUN json emitido" % malo,
                         rc == 2 and not txt.strip().startswith("{"),
                         "rc=%r, %d bytes" % (rc, len(txt.strip()))))
    # Equivalencia de modos: el vector que §8.6 dice que hace falta. Mismo
    # --solo, mismo conjunto, en texto y en --json. Antes el texto daba 2 y el
    # --json daba las 3, porque la rama --json estaba antes del filtro.
    rc, txt = invoca(["--json", "--solo", "NO_EN_CORPUS"])
    j = json.loads(txt)
    vectores.append(("--json respeta --solo: el mismo conjunto que el texto",
                     rc == 0 and j["total"] == 2
                     and j["distribucion"] == {"NO_EN_CORPUS": 2}
                     and {c["nombre"] for c in j["constantes"]} == {"MM_A", "MM_B"},
                     "total=%r dist=%r" % (j["total"], j["distribucion"])))
    rc, txt = invoca(["--json"])
    j = json.loads(txt)
    vectores.append(("--json sin --solo conserva la medicion entera",
                     rc == 0 and j["total"] == 3, "total=%r" % j["total"]))
    fallos = sum(1 for _, ok, _ in vectores if not ok)
    print("regconst.py selftest")
    for nombre, ok, det in vectores:
        print("  %s %s%s" % ("OK  " if ok else "FAIL", nombre,
                             "" if ok else "   -- %r" % (det,)))
    print("RESULT: %s (%d vectores)" % ("PASS" if not fallos else "FAIL",
                                        len(vectores)))
    return 0 if not fallos else 1


def main():
    ap = argparse.ArgumentParser(description="verifica constantes de registro")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--solo", metavar="CLASE", help="solo esa clase")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    # MEDIDO 2026-10-04 (nodo FILTROS-REPARO-2, sobre el censo
    # 08-ARQUITECTURA/FILTROS-MAL-FORMADOS.md:282-315).
    #
    # Este filtro comparaba con IGUALDAD EXACTA y no decia nada cuando no
    # encontraba nada. Consecuencia medida ANTES del arreglo:
    #
    #   --solo NO_EN_CORPUS          ->  3 filas, rc=0   (control)
    #   --solo CLASE_QUE_NO_EXISTE  ->  0 filas, rc=0
    #   --solo GRAF_8_0              ->  0 filas, rc=0   (no tiene forma de clase)
    #   y las tres salidas son IDENTICAS salvo las tres filas: mismo titulo, mismo
    #   cuerpo, misma linea de resumen.
    #
    # Peor que el vacio: la linea de resumen se contradecia sola. Anunciaba
    # "NO_EN_CORPUS 3" --contando `filas`, la lista SIN filtrar-- y debajo no
    # listaba ninguno. Quien lee el resumen creia que habia tres.
    #
    # Y un tercer defecto, MEDIDO aqui y NO listado por el censo: el filtro
    # tampoco se aplicaba en --json, porque la rama `if a.json: return 0` estaba
    # ANTES de que se calculara `vis`. Las dos invocaciones daban un fichero
    # byte a byte identico:
    #
    #   --json                          total=35  md5=3ff3b464888c4804b6d1304814a4e868
    #   --json --solo CLASE_QUE_NO_EXISTE  total=35  md5=3ff3b464888c4804b6d1304814a4e868
    #
    # El arreglo NO es "que no filtre": es "que diga lo que hizo". La poblacion
    # de clases se CALCULA de la medicion real --nunca de un fichero de texto-- y
    # el filtro se aplica ANTES de las dos salidas, para que texto y --json
    # seleccionar el mismo conjunto.
    #
    # El texto de error es el del hermano lint.py:959-968, que es el mismo
    # archivo de ideas con el mismo metavar="CLASE" y el mismo ==.
    filas = medir()

    # Esto es "no he leido nada", que es distinto de "el filtro no caso". Se
    # comprueba contra la lista SIN filtrar y por eso no puede dispararse con
    # --solo: un nombre de clase equivocado no es un corpus vacio.
    if not filas:
        print("""
  No se ha encontrado ninguna constante de registro. Eso NO es un 0 %: es una
  herramienta que no ha leido nada, que es la clase de resultado que esta tabla
  existe para evitar. El guardia de cargar() en drvchain.py intercepta el mismo fallo.
""")

    clases_presentes = sorted({f["clase"] for f in filas})
    if a.solo and a.solo not in clases_presentes:
        print("ERROR: --solo %s no es ninguna clase de este informe." % a.solo)
        print("  clases que SI existen (%d): %s"
              % (len(clases_presentes), ", ".join(clases_presentes)))
        print("  No se ha medido nada.  Un filtro que no casa y dice 'ninguno' es")
        print("  una puerta verde construida sobre una llamada mal escrita.")
        return 2

    # El filtro se aplica aqui, y no despues del `--json`, para que los dos modos
    # selecting el mismo conjunto. Es el vector de equivalencia de modos de §8.6.
    if a.solo:
        filas = [f for f in filas if f["clase"] == a.solo]

    # El recuento se hace sobre la lista YA filtrada. Antes contaba `filas` sin
    # filtrar, y por eso las dos lineas de resumen de abajo no describian lo que
    # la tabla de encima enseñaba.
    dist = {}
    for f in filas:
        dist[f["clase"]] = dist.get(f["clase"], 0) + 1

    if a.json:
        print(json.dumps({"total": len(filas), "distribucion": dist,
                          "constantes": filas}, indent=2, ensure_ascii=False))
        return 0

    print("=" * 78)
    print("CONSTANTES DE REGISTRO DEL DRIVER PROPIO -- contra el corpus")
    print("=" * 78)
    print("""
  Cada offset que el driver va a escribir tiene que existir en el ASIC, con el
  mismo valor, en el _d.h de ESTA generacion. Sin esto, un offset erroneo no
  falla al compilar: se escribe en una IB y el sintoma aparece lejos.

  PROVEN             el corpus lo define con ESE valor, en esta generacion
  VALOR_DISCREPANTE  existe en esta generacion con OTRO valor
  GENERACION_DIERE   el valor aparece, pero en el _d.h de otra generacion:
                     el numero puede servir y la autoridad no (findings/147)
  NO_EN_CORPUS       no se ha encontrado. NO es que el registro no exista
  FUERA_DE_BAR2       >= 2 MiB, el tamano medido de resource2 (findings/176)
""")
    vis = filas
    for f in vis:
        print("  %-22s %-32s 0x%-8x %s" % (f["clase"], f["nombre"], f["valor"],
                                           f["fichero"].split("/")[-1] + ":%d" % f["linea"]))
        for o in f.get("fuentes", [])[:2]:
            print("      %-34s 0x%-8x %s:%s" % (
                (o.get("nombre") or "-")[:34], o["valor"],
                o["fichero"].split("/")[-1], o.get("linea", "?")))
    print()
    # Estas dos lineas cuentan lo que la tabla de encima ha mostrado. Con --solo
    # lo que se han mostrado son las filas de UNA clase, y el denominador
    # completo se dice aparte y con su etiqueta, porque el total medido es real y
    # no se debe ocultar: lo que no puede es aparecer pegado a un reparto que no
    # es el suyo.
    print("  %d #define con valor leidos en el driver: %s" % (len(filas), ", ".join(
        "%s %d" % (k, v) for k, v in sorted(dist.items())) if dist else "ninguno"))
    reg = len(filas) - dist.get("NO_ES_REGISTRO", 0)
    print("  de los cuales %d son direcciones de registro y %d no lo son."
          % (reg, dist.get("NO_ES_REGISTRO", 0)))
    if a.solo:
        print("  Filtro --solo %s aplicado: la tabla de arriba y este recuento son"
              % a.solo)
        print("  las mismas filas. Las otras clases de la medicion existen y no se")
        print("  han pedido; la medicion completa se conserva en --json sin --solo.")
    print("  Los NO_ES_REGISTRO se listan aparte y no se mezclan: un opcode de")
    print("  paquete no es una direccion, y comprobarlo contra el corpus daria")
    print("  NO_EN_CORPUS para algo que no deberia estar ahi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
