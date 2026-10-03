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

    filas = medir()
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
    vis = [f for f in filas if not a.solo or f["clase"] == a.solo]
    for f in vis:
        print("  %-22s %-32s 0x%-8x %s" % (f["clase"], f["nombre"], f["valor"],
                                           f["fichero"].split("/")[-1] + ":%d" % f["linea"]))
        for o in f.get("fuentes", [])[:2]:
            print("      %-34s 0x%-8x %s:%s" % (
                (o.get("nombre") or "-")[:34], o["valor"],
                o["fichero"].split("/")[-1], o.get("linea", "?")))
    print()
    print("  %d #define con valor leidos en el driver: %s" % (len(filas), ", ".join(
        "%s %d" % (k, v) for k, v in sorted(dist.items()))))
    reg = len(filas) - dist.get("NO_ES_REGISTRO", 0)
    print("  de los cuales %d son direcciones de registro y %d no lo son."
          % (reg, dist.get("NO_ES_REGISTRO", 0)))
    print("  Los NO_ES_REGISTRO se listan aparte y no se mezclan: un opcode de")
    print("  paquete no es una direccion, y comprobarlo contra el corpus daria")
    print("  NO_EN_CORPUS para algo que no deberia estar ahi.")
    if not filas:
        print("""
  No se ha encontrado ninguna constante de registro. Eso NO es un 0 %: es una
  herramienta que no ha leido nada, que es la clase de resultado que esta tabla
  existe para evitar. El guardia de cargar() en drvchain.py intercepta el mismo fallo.
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
