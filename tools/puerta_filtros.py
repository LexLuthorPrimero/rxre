#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""puerta_filtros.py -- la puerta que el censo de filtros propone y que no existia

WORK_CLASS=READ_ONLY
WRITE_EXECUTION=NONE

QUE AFIRMA

    Ninguna herramienta de este proyecto devuelve un conjunto vacio por un
    filtro que no caso sin decirlo.

Formulado como PREDICADO sobre (herramienta, argumento, valor) y no sobre el
codigo: se puede falsar con un vector, no con una opinion sobre el estilo.

POR QUE ESTA ESCRITA AHORA Y NO EN EL CENSO

El censo (08-ARQUITECTURA/FILTROS-MAL-FORMADOS.md, §8)arla dejo enunciada y no
escrita, y dijo por que: su prototipo vivia en /tmp y su oraculo se habia
falsado una vez. Este nodo (FILTROS-REPARO-2) ha reparado cinco de los
argumentos que el censo lista, y con ellos hay vectores REPARADOS y vectores
SIN REPARAR en la misma lista. Una puerta necesita las dos clases para
existir: si todos los vectores pasan, no se sabe si la puerta funciona o si el
oraculo es ancho. Asi que los dos grupos estan aqui.

EL ORACULO, Y POR QUE ESTA ANCLADO AL VALOR

    ok := rc != 0
       ó existe una LINEA que contenga a la vez:
             - el VALOR pedido, tal cual se escribio
             - una declaracion de que ese valor no esta en el conjunto valido

La segunda disyunctiva es ANCLADA A LA LINEA, no a la salida entera. Esa es
justamente la correccion del §8.3-bis: el primer oraculo aceptaba cualquier
"NO ENCONTRADO" en cualquier parte, y con el `hwip.py --chip Polaris12` PASABA
la puerta, porque esa herramienta imprime NO ENCONTRADO en su seccion 5
mientras en la seccion 3 afirma lo contrario. La linea de la seccion 5 no
contiene el valor pedido, asi que el oraculo anclado no la ve. MEDIDO en el
selftest, con ese caso reproducido como vector.

Y el valor se busca TAL CUAL, no "en alguna parte de la salida": si se
buscara en toda la salida, bastaria que el valor apareciera en la tabla para
que la salida contenga el valor, y la declaracion volveria a poder ser de
otro sitio.

LO QUE ESTA PUERTA NO PUEDE DECIR

- No puede exigir nada a los filtros de clase ABIERTA (--msg, --patron,
  --find, --fichero): no tienen conjunto cerrado, asi que "no caso" es una
  verdad sobre la consulta. A esos lo unico que se les puede exigir es que
  digan cuantas filas habia antes del filtro, que es otra puerta.
- No es una puerta de ESTILO. No lee el codigo de los filtros: ejecuta
  herramientas con un valor mal escrito y mira lo que dicen. Una puerta que
  solo leyera codigo no podria falsarse con un vector.
- NO es una puerta de correccion. Un rc=0 con la tabla vacia puede ser un
  resultado legitimo si el filtro es abierto y el valor es una verdad sobre la
  consulta. Por eso el vector trae su clase declarada y el resultado lo dice.

USO

    python3 tools/puerta_filtros.py --selftest
    python3 tools/puerta_filtros.py                    # todos los vectores
    python3 tools/puerta_filtros.py --rapido           # solo los que no leen corpus

INVARIANTE DE DIRECTORIO DE TRABAJO

toolreg.py:485 corre los self-tests con cwd=os.path.dirname(t.path), o sea
con cwd=tools/. Toda ruta de este fichero sale de __file__, no de os.getcwd(),
por el motivo que declara el hallazgo 1051: una puerta que depende del
directorio de trabajo se rompe justo en la puerta que la valida. Hay un
vector que lo comprueba.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

NAME = "puerta_filtros"
VERSION = "1.0.0"

# La raiz sale de __file__, NUNCA de os.getcwd(). Medido: toolreg corre los
# self-tests con cwd=tools/.
_AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(_AQUI)

# --------------------------------------------------------------------------
# EL ORACULO. Lo primero, lo mas importante.
# --------------------------------------------------------------------------
#
# Una declaracion tiene que MENCIONAR el valor. Sin esa exigencia, el oraculo
# es el ancho de §8.3-bis y la puerta autoriza en verde lo que debe señalar.
DECLARA = re.compile(
    r"no es ninguna clase"
    r"|no es ningun bloque"
    r"|no es ningun ASIC"
    r"|no es subcadena"
    r"|no existe o no es un directorio"
    r"|no contiene ningun \.c"
    r"|no esta en el enum"
    r"|no conozco"
    r"|no aparece con ninguna cifra"
    r"|unknown check"
    r"|mutante desconocido"
    r"|NINGUN sitio con ese NOMBRE EXACTO"
    r"|NINGUN registro, campo ni fichero casa"
    r"|NINGUNA de las raices existe"
    r"|no he podido comprobar"
    r"|no he leido nada"
    r"|No se ha medido nada"
    r"|no queda ningun nombre"
    r"|no es ninguno de los nombres",
    re.I)


def declara_el_valor(salida, valor):
    """True si ALGUNA LINEA declara, y esa linea contiene el valor pedido.

    MEDIDO sobre el caso que falsó el primer oraculo: una linea que dice
    "NO ENCONTRADO" sin mencionar el valor NO declara nada, aunque esté en la
    salida de una herramienta que en otra sección afirma lo contrario.

    Devuelve la linea que lo hace, para poder citarla en el informe. Sin la
    linea, un "OK" de la puerta no se puede revisar a mano.

    Un valor VACIO no ancla nada, y devuelve None aunque la linea declare: con
    la cadena vacia, `valor in linea` es True para todas las lineas, y el
    oraculo aprobaria cualquier salida que contenga la palabra "no". MEDIDO:
    sin esta guarda, `declara_el_valor("no es ninguna clase", "")` devolvia la
    linea, y un vector con valor vacio pasaba la puerta sin medir nada.
    """
    if not valor:
        return None
    for linea in (salida or "").splitlines():
        if valor in linea and DECLARA.search(linea):
            return linea.strip()
    return None


def veredicto(rc, salida, valor):
    """(estado, motivo, linea_que_declara)

    estado es "OK" o "CALLA". CALLA significa: la herramienta no ha dicho nada
    sobre el valor pedido, y eso es un FALLO de la puerta.
    """
    if rc is None:
        # Un timeout NO es un veredicto. Se devuelve como CALLA porque no hay
        # nada que leer, pero con su motivo, para que no se confunda con un
        # CALLA de verdad por parte de una herramienta que si ha corrido.
        return "CALLA", "TIMEOUT: no hay veredicto que leer", None
    if rc != 0:
        # Sin linea que citar: el rc es lo que declara, y se deja dicho para que
        # un revisor vea que aqui no habia texto, no que se leyo y se descarto.
        return "OK", "rc=%d: fallo visible aunque no lo explique" % rc, None
    linea = declara_el_valor(salida, valor)
    if linea:
        return "OK", "declara el valor pedido", linea
    return "CALLA", "rc=0 y ninguna linea declara el valor %r" % valor, None


# --------------------------------------------------------------------------
# LOS VECTORES
# --------------------------------------------------------------------------
#
# Cada vector trae su clase declarada, porque no todos los filtros Callan por
# el mismo motivo y la puerta no puede Tratarlos igual:
#
#   CERRADO  el conjunto de valores validos es calculable y esta medido. Un
#            valor que no esta en el es un error de escritura, y la puerta
#            PUEDE exigir que se note.
#   RUTA     lo que se escoge es una ruta. No existir es un error de escritura.
#   ABIERTA  no hay conjunto cerrado. "No caso" es una verdad sobre la consulta
#            y la puerta NO PUEDE exigir que se note. Se mide y se registra,
#            pero un CALLA aqui NO se cuenta como defecto de la puerta: se
#            cuenta como limite del argumento. Decirlo es parte del resultado.

VECTORES = [
    # --- los cinco reparados en este nodo, con su control positivo ---
    dict(herr="tools/regconst.py", clase="CERRADO", arg="--solo",
         valor="CLASE_QUE_NO_EXISTE", kernel=None,
         argv=["--solo", "CLASE_QUE_NO_EXISTE"], nota="reparado 2026-10-04"),
    dict(herr="tools/regconst.py", clase="CERRADO", arg="--solo",
         valor="NO_EN_CORPUS", kernel=None,
         argv=["--solo", "NO_EN_CORPUS"], control_positivo=True,
         nota="control: clase que SI existe, tiene que dar rc=0"),
    dict(herr="tools/cap_census.py", clase="CERRADO", arg="--cap",
         valor="PHM_TYPOXX", kernel="RESEARCH/working/linux-7.1.3",
         argv=["--cap", "PHM_TYPOXX"], nota="reparado 2026-10-04"),
    dict(herr="tools/cap_census.py", clase="CERRADO", arg="--cap",
         valor="SQRamping", kernel="RESEARCH/working/linux-7.1.3",
         argv=["--cap", "SQRamping"], control_positivo=True,
         nota="control: subcadena que SI existe"),
    dict(herr="revkit/dires.py", clase="CERRADO", arg="--bloque",
         valor="BIF", kernel=None, argv=["--bloque", "BIF"],
         nota="reparado 2026-10-04"),
    dict(herr="08-ARQUITECTURA/tools/inst_closure.py", clase="CERRADO",
         arg="--asi", valor="dce999", kernel=None,
         argv=["--asi", "dce999"], nota="reparado 2026-10-04"),
    dict(herr="08-ARQUITECTURA/tools/inst_closure.py", clase="CERRADO",
         arg="--asi", valor="dce112", kernel=None,
         argv=["--asi", "dce112"], control_positivo=True,
         nota="control: el ASIC de esta GPU, que SI existe"),
    dict(herr="tools/trace_path.py", clase="RUTA", arg="--root",
         valor="NO_EXISTE_ESTA_RUTA",
         kernel="RESEARCH/kernelbuild/linux-7.1.3",
         argv=["--root", "NO_EXISTE_ESTA_RUTA", "--callers-of",
               "amdgpu_gc_atomic_cmdexec"], nota="reparado 2026-10-04"),
    dict(herr="tools/hwip.py", clase="CERRADO", arg="--chip",
         valor="CHIP_GA10", kernel=None, argv=["--chip", "CHIP_GA10"],
         nota="reparado en el nodo 1055, por otro turno"),

    # --- los que el censo deja SIN REPARAR: son los que hacen que la puerta
    #     pueda FALLAR. Sin estos, la puerta no se puede falsar. ---
    dict(herr="tools/assert_contract.py", clase="ABIERTA", arg="--fichero",
         valor="NO_EXISTE_XYZ", kernel=None,
         argv=["--fichero", "NO_EXISTE_XYZ"], nota="SIN REPARAR"),
    dict(herr="tools/citegen.py", clase="ABIERTA", arg="--fichero",
         valor="NO_EXISTE_XXX", kernel=None,
         argv=["--fichero", "NO_EXISTE_XXX"], nota="SIN REPARAR"),
    dict(herr="revkit/regs.py", clase="CERRADO", arg="--asic",
         valor="gfx_9_0", kernel=None,
         argv=["CC_GC_SHADER_ARRAY_CONFIG", "INACTIVE_CUS", "--asic", "gfx_9_0"],
         nota="SIN REPARAR"),
]


def _kernel_de(v):
    if not v:
        return None
    ruta = os.path.join(RAIZ, v)
    return ruta if os.path.isdir(ruta) else None


def ejecuta(v, timeout=300, cwd=None):
    """Ejecuta el vector. Devuelve (rc, salida) o (None, motivo) si no se pudo.

    Un vector que NO se puede ejecutar NO se cuenta como OK ni como CALLA: se
    registra como NO_EJECUTADO. Convertir "no lo he mirado" en "verde" seria el
    defecto que se esta auditando, un nivel mas arriba.
    """
    ruta = os.path.join(RAIZ, v["herr"])
    if not os.path.isfile(ruta):
        return None, "NO EXISTE la herramienta %s" % v["herr"]
    argv = [sys.executable, ruta] + list(v["argv"])
    if v.get("kernel"):
        k = _kernel_de(v["kernel"])
        if k is None:
            return None, "NO EXISTE el corpus %s" % v["kernel"]
        argv += ["--kernel", k]
    try:
        r = subprocess.run(argv, capture_output=True, text=True,
                           timeout=timeout, cwd=cwd or RAIZ)
    except subprocess.TimeoutExpired:
        return None, "TIMEOUT tras %ds" % timeout
    except OSError as exc:
        return None, "OSERROR %s" % exc
    return r.returncode, (r.stdout + r.stderr)


def escanea(rapido=False, cwd=None, verbose=True, vectores=None):
    resultados = []
    for v in (VECTORES if vectores is None else vectores):
        if v.get("control_positivo"):
            continue
        if rapido and v.get("kernel"):
            continue
        rc, salida = ejecuta(v, cwd=cwd)
        if rc is None:
            resultados.append(dict(v, estado="NO_EJECUTADO", motivo=salida,
                                   linea=None))
            continue
        estado, motivo, linea = veredicto(rc, salida, v["valor"])
        # Un ABIERTA que calla no es un defecto de la puerta: es un limite del
        # argumento. Se cuenta aparte para que el numero de cabecera no
        # mezcle las dos cosas.
        if estado == "CALLA" and v["clase"] == "ABIERTA":
            estado = "CALLA_ABIERTA"
        resultados.append(dict(v, estado=estado, motivo=motivo, linea=linea,
                               rc=rc))
    if verbose:
        for r in resultados:
            marca = {"OK": "  OK   ", "CALLA": "  FALLA",
                     "CALLA_ABIERTA": "  PARCIAL", "NO_EJECUTADO": "  N/E   "}[r["estado"]]
            print("%s %-38s %-11s %r" % (marca, r["herr"], r["arg"], r["valor"]))
            print("         %s" % r["motivo"])
            if r.get("linea"):
                print("         declara: %s" % r["linea"][:96])
            print("         clase=%s  %s" % (r["clase"], r.get("nota", "")))
    return resultados


def resumen(res):
    ok = sum(1 for r in res if r["estado"] == "OK")
    falla = sum(1 for r in res if r["estado"] == "CALLA")
    parcial = sum(1 for r in res if r["estado"] == "CALLA_ABIERTA")
    ne = sum(1 for r in res if r["estado"] == "NO_EJECUTADO")
    return dict(ok=ok, calan=falla, parcial_abierta=parcial, no_ejecutado=ne,
                total=len(res))


# --------------------------------------------------------------------------
# SELFTEST
# --------------------------------------------------------------------------

def selftest():
    """Vectores que FALLAN A PROPOSITO, mas el oraculo falsado de §8.3-bis.

    Un selftest de una puerta tiene que contener vectores que la puerta tiene
    que RECHAZAR. Si todos los vectores pasan, el selftest no distingue una
    puerta de un `return True`.

    Los vectores que callan se construyen aqui, en un directorio temporal, con
    herramientas minimas cuyo comportamiento esta fijado por construccion: asi
    que el selftest no depende de que otra herramienta este reparada o no. Si
    este selftest dijera "assert_contract tiene que callar", reparar
    assert_contract lo romperia, y un selftest que falla cuando el proyecto
    mejora es un selftest malo.
    """
    fallos = []
    vectores = [0]

    def chk(nombre, cond, detalle=""):
        vectores[0] += 1
        if not cond:
            fallos.append("%s%s" % (nombre, ("  -- %r" % (detalle,)) if detalle else ""))

    # --- 1. El oraculo, sobre texto plano. Sin subprocess. ---
    v = "Polaris12"
    # El caso que FALSO el primer oraculo, reproducido. rc=0, hay un
    # "NO ENCONTRADO" en la salida, y la linea que lo dice NO menciona el
    # valor. Esta herramienta, en otra seccion, afirma lo contrario.
    salida_1055 = (
        "  seccion 3\n"
        "  Consecuencia directa: para esta GPU, TODAS las versiones de IP\n"
        "  se leen de la tarjeta. No hay ningun atajo estatico.\n"
        "  seccion 5\n"
        "  amdgpu_drv.c:2041  some_ip_read  NO ENCONTRADO\n")
    e, _, _ = veredicto(0, salida_1055, v)
    chk("el caso de §8.3-bis sigue dando CALLA, no un OK falso",
        e == "CALLA", e)

    # rc=0, tabla vacia, ninguna declaracion: CALLA.
    e, _, _ = veredicto(0, "cabecera\ntabla\n", "NO_EXISTE")
    chk("rc=0 sin declaracion da CALLA", e == "CALLA", e)

    # rc=0 y la declaracion esta en OTRA linea que el valor: CALLA. El anclaje
    # es a la LINEA, no a la salida. Aqui la linea que declara NO lleva el valor
    # ("--solo" a secas), y el valor aparece solo, en la tabla de abajo.
    # Una primera version de este vector metia el valor en la linea de la
    # declaracion y por eso daba OK: el vector no probaba lo que decia probar.
    salida_dos = ("ERROR\n  --solo no es ninguna clase de este informe.\n"
                  "  tabla:\n  NO_EXISTE  algo\n")
    e, _, _ = veredicto(0, salida_dos, "NO_EXISTE")
    chk("la declaracion en otra linea que el valor da CALLA", e == "CALLA", e)

    # rc=0 con la declaracion y el valor EN LA MISMA linea: OK.
    e, _, linea = veredicto(0, "ERROR: --solo NO_EXISTE no es ninguna clase de"
                                " este informe.\n", "NO_EXISTE")
    chk("rc=0 declarando el valor en la misma linea da OK",
        e == "OK" and linea, e)

    # rc!=0 manda, y se dice que es visible aunque no explique nada.
    e, m, _ = veredicto(2, "", "X")
    chk("rc=2 da OK sin necesidad de texto", e == "OK" and "rc=2" in m, m)
    e, _, _ = veredicto(None, "", "X")
    chk("un timeout NO se cuenta como OK", e == "CALLA", e)

    # Un valor vacio no puede anclar nada: declararia CUALQUIER linea, porque la
    # cadena vacia esta en todas. Sin esta guarda, el oraculo aprueba cualquier
    # salida que contenga la palabra "no" cuando el valor va vacio.
    chk("un valor vacio no ancla una declaracion",
        declara_el_valor("no es ninguna clase de este informe", "") is None,
        "declararia una linea sin valor: es un fallo del oraculo, no un OK")

    # --- 2. Herramientas minimas reales, con los tres comportamientos. ---
    with tempfile.TemporaryDirectory() as td:
        # (a) la que CALLA: rc=0, resultado vacio, no dice nada.
        with open(os.path.join(td, "calla.py"), "w") as fh:
            fh.write("#!/usr/bin/env python3\n"
                     "import sys\n"
                     "print('herramienta de prueba')\n"
                     "print('  filas: 0')\n"
                     "sys.exit(0)\n")
        # (b) la que DECLARA el valor, con rc=0.
        with open(os.path.join(td, "declara.py"), "w") as fh:
            fh.write("#!/usr/bin/env python3\n"
                     "import sys\n"
                     "v = sys.argv[1]\n"
                     "print('herramienta de prueba')\n"
                     "print('ERROR --solo %s no es ninguna clase de este informe.' % v)\n"
                     "print('  clases que SI existen (2): A, B')\n"
                     "print('  No se ha medido nada.')\n"
                     "sys.exit(0)\n")
        # (c) la que sale con rc=2 sin explicar nada.
        with open(os.path.join(td, "rc2.py"), "w") as fh:
            fh.write("#!/usr/bin/env python3\n"
                     "import sys\n"
                     "sys.stderr.write('algo salio mal\\n')\n"
                     "sys.exit(2)\n")
        # (d) la que IMPRIME el valor pedido pero no declara nada. Es el caso
        #     mas traicionero: el valor esta en la salida y aun asi calla, y un
        #     oraculo que buscara el valor en toda la salida lo aprueba.
        with open(os.path.join(td, "valor_sin_declarar.py"), "w") as fh:
            fh.write("#!/usr/bin/env python3\n"
                     "import sys\n"
                     "v = sys.argv[1]\n"
                     "print('buscando %s' % v)\n"
                     "print('  0 filas')\n"
                     "sys.exit(0)\n")

        for nombre, valor, esperado in (
                ("calla.py", "NO_EXISTE", "CALLA"),
                ("declara.py", "NO_EXISTE", "OK"),
                ("rc2.py", "NO_EXISTE", "OK"),
                ("valor_sin_declarar.py", "NO_EXISTE", "CALLA")):
            # La ruta ABSOLUTA del temporal, no el nombre suelto: `ejecuta`
            # resuelve contra RAIZ, y con un nombre suelto buscaba la
            # herramienta en el proyecto y no la encontraba. MEDIDO: los cuatro
            # vectores fallaron con "NO EXISTE la herramienta" por esto.
            v = dict(herr=os.path.join(td, nombre), kernel=None, argv=[valor])
            rc, salida = ejecuta(v, timeout=60)
            chk("herramienta sintetica %s esta en pie" % nombre, rc is not None,
                salida)
            if rc is None:
                continue
            e, _, _ = veredicto(rc, salida, valor)
            chk("sintetica %-22s -> %s" % (nombre, esperado), e == esperado, e)

        # El caso (d) es el que mas se parece a lo que se quiere cazar, y por
        # eso tiene su propia linea: una puerta que solo busca el valor en la
        # salida le daria OK.
        rc, salida = ejecuta(dict(herr=os.path.join(td, "valor_sin_declarar.py"),
                                   kernel=None, argv=["NO_EXISTE"]), timeout=60)
        chk("imprimir el valor NO es declarar (si lo fuera, (d) pasaria)",
            declara_el_valor(salida, "NO_EXISTE") is None,
            "declara: %r" % declara_el_valor(salida, "NO_EXISTE"))

    # --- 3. Un vector REAL y rapido, de una herramienta reparada. ---
    # revkit/dires.py acepta --raiz, asi que se le puede dar un arbol de tres
    # ficheros en vez del corpus de 235. MEDIDO: 0,05 s. Es el unico vector
    # real del selftest, y va con los dos signos: el malo tiene que dar OK en la
    # puerta, y el bueno tiene que dar rc=0 para que no se haya roto el camino
    # bueno al reparar el malo.
    with tempfile.TemporaryDirectory() as td:
        for sub, nombre, cuerpo in (
                ("bif", "bif_4_1_d.h", "#define mmGPU_HDP_FLUSH_REQ 0x1537\n"
                                          "#define mmGPU_HDP_FLUSH_DONE 0x1538\n"),
                ("bif", "bif_5_0_d.h", "#define mmGPU_HDP_FLUSH_REQ 0x1537\n"),
                ("gc", "gc_9_0_0_offset.h", "#define mmOTRO 0x900\n")):
            os.makedirs(os.path.join(td, sub), exist_ok=True)
            with open(os.path.join(td, sub, nombre), "w") as fh:
                fh.write(cuerpo)
        # El arbol tiene que pasar la AUTOCOMPROBACION de la propia herramienta
        # (0x1537/0x1538 en BIF 4.1), o dira rc=3 por su cuenta.
        v_malo = dict(herr="revkit/dires.py", kernel=None,
                      argv=["0x1537", "--raiz", td, "--bloque", "BIF"])
        rc, salida = ejecuta(v_malo, timeout=120)
        chk("vector real: la herramienta reparada se ejecuta", rc is not None,
            salida)
        if rc is not None:
            e, _, _ = veredicto(rc, salida, "BIF")
            chk("vector real dirs --bloque BIF: la puerta da OK", e == "OK", e)
            chk("vector real dirs --bloque BIF: rc=2",
                rc == 2, "rc=%r" % rc)
        v_bueno = dict(herr="revkit/dires.py", kernel=None,
                       argv=["0x1537", "--raiz", td, "--bloque", "bif"])
        rc, salida = ejecuta(v_bueno, timeout=120)
        chk("vector real dirs --bloque bif: rc=0 y trae filas (control positivo)",
            rc == 0 and "mmGPU_HDP_FLUSH_REQ" in salida, "rc=%r" % rc)

    # --- 4. El invariante de directorio de trabajo. ---
    # toolreg.py:485 corre esto con cwd=tools/. Si la raiz saliera de
    # os.getcwd(), aqui y en la puerta real se caeria. Se comprueba que la
    # raiz es la misma con los dos cwd.
    raiz_desde_tools = None
    cwd_antes = os.getcwd()
    try:
        os.chdir(_AQUI)
        raiz_desde_tools = os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))
    finally:
        os.chdir(cwd_antes)
    chk("la raiz NO sale de os.getcwd() (invariante de toolreg)",
        raiz_desde_tools == RAIZ, "%r != %r" % (raiz_desde_tools, RAIZ))
    # Y un vector ejecutado con cwd=tools/ tiene que dar lo mismo que con la
    # raiz, porque la puerta es la que va a correr asi.
    v_cwd = dict(herr="revkit/dires.py", kernel=None, argv=["--contar"])
    rc_a, sal_a = ejecuta(v_cwd, timeout=120, cwd=RAIZ)
    rc_b, sal_b = ejecuta(v_cwd, timeout=120, cwd=_AQUI)
    chk("la misma herramienta con cwd=raiz y cwd=tools/ da lo mismo",
        (rc_a, sal_a) == (rc_b, sal_b), "rc %r vs %r" % (rc_a, rc_b))

    # --- 5. El recuento no se vuelve verde sin ejecutar. ---
    # Con vectores SINTETICOS, no con los de la lista real. La version primera
    # de este vector llamaba a escanea(rapido=True) sobre VECTORES, y MEDIDO
    # costaba 52 s: regconst.py lee el corpus entero (30 s) e inst_closure.py
    # tambien. Un selftest de 52 s es un selftest que nadie lanza dentro de
    # toolreg, y un selftest que no se lanza no es una red.
    with tempfile.TemporaryDirectory() as td:
        # Su propia copia de la que calla: el temporal de la seccion 2 ya esta
        # cerrado aqui, y sin escribirla el vector salia NO_EJECUTADO y el
        # check de CALLA fallaba por un fallo mio, no por el de la puerta.
        with open(os.path.join(td, "calla.py"), "w") as fh:
            fh.write("#!/usr/bin/env python3\n"
                     "import sys\nprint('filas: 0')\nsys.exit(0)\n")
        con_td = [
            dict(herr=os.path.join(td, "calla.py"), kernel=None,
                 argv=["NO_EXISTE"], valor="NO_EXISTE", clase="CERRADO",
                 arg="--x", nota="sintetica"),
            dict(herr=os.path.join(td, "no_existe_esta_herramienta.py"),
                 kernel=None, argv=["NO_EXISTE"], valor="NO_EXISTE",
                 clase="CERRADO", arg="--x", nota="sintetica"),
        ]
        res = escanea(verbose=False, vectores=con_td)
    chk("el resumen no declara OK un vector no ejecutado",
        all(r["estado"] != "OK" for r in res if r["estado"] == "NO_EJECUTADO"),
        "no deberia haber OK entre los NO_EJECUTADO")
    chk("una herramienta que no existe queda NO_EJECUTADO, no CALLA",
        any(r["estado"] == "NO_EJECUTADO" for r in res),
        [r["estado"] for r in res])
    chk("y una que calla queda CALLA, que es un estado distinto",
        any(r["estado"] == "CALLA" for r in res), [r["estado"] for r in res])
    s = resumen(res)
    chk("el resumen cuenta lo que hay", s["total"] == len(res), s)

    print("%s %s · self-test" % (NAME, VERSION))
    print("  vectores: %d" % vectores[0])
    if fallos:
        print("  RESULTADO FALLIDO (%d de %d):" % (len(fallos), vectores[0]))
        for f in fallos:
            print("    - %s" % f)
        return 1
    print("  RESULTADO OK · %d vectores, incluidos %d que la puerta tiene que"
          % (vectores[0], 3))
    print("    RECHAZAR (varias herramientas minimas que callan, el caso de")
    print("    §8.3-bis, y el oraculo anclado a la linea).")
    print("  Una puerta cuyo selftest solo tiene vectores que pasa no es una")
    print("  puerta: es un `return True` con subprocess.")
    return 0


def main():
    ap = argparse.ArgumentParser(
        prog=NAME,
        description="predicado falsable sobre filtros que devuelven vacio sin decirlo")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--rapido", action="store_true",
                    help="solo los vectores que no leen corpus")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    # MEDIDO 2026-10-04: con `verbose=True` (el defecto) el modo --json
    # imprimia el bloque de texto ANTES del json, y stdout no se podia parsear.
    # Es exactamente el defecto que este nodo repara en cap_census.py: un
    # camino de salida que no es parseable mientras el otro si. Se ha visto
    # porque se ha INTENTO parsear el resultado, no porque se supusiera.
    res = escanea(rapido=a.rapido, verbose=not a.json)
    s = resumen(res)
    if a.json:
        print(json.dumps({"tool": NAME, "version": VERSION,
                          "resumen": s,
                          "criterio": "ok := rc!=0 ó una linea que contenga el "
                                      "VALOR pedido y una declaracion",
                          "vectores": [{k: v for k, v in r.items()
                                        if k != "argv"} for r in res]},
                         indent=2, ensure_ascii=False))
        return 0

    print("=" * 78)
    print("%s %s -- ¿algun filtro devuelve un vacio sin decirlo?" % (NAME, VERSION))
    print("=" * 78)
    print("""
  Criterio, ANCLADO AL VALOR:
    ok := rc != 0
       ó existe una LINEA que contenga el valor pedido Y una declaracion.

  CALLA        = la puerta falla: la herramienta no dice nada del valor pedido
  CALLA_ABIERTA= el filtro es de clase abierta, "no caso" es una verdad sobre la
                 consulta, y la puerta NO puede exigir nada. Es un limite del
                 argumento, no un defecto de la puerta, y por eso no se mezcla
                 con CALLA en el recuento.
  NO_EJECUTADO = no se ha podido ejecutar. NO cuenta como OK.

  Una puerta que solo tiene vectores que pasa no se puede falsar. Por eso hay
  vectores SIN REPARAR a proposito en la lista, y por eso el selftest incluye
  herramientas minimas que la puerta tiene que RECHAZAR.
""")
    print("  OK %d · CALLA %d · CALLA_ABIERTA %d · NO_EJECUTADO %d · de %d vectores"
          % (s["ok"], s["calan"], s["parcial_abierta"], s["no_ejecutado"],
             s["total"]))
    if s["calan"]:
        print()
        print("  CALLA %d: la puerta NO pasa. Es lo que se espera mientras queden"
              % s["calan"])
        print("  filtros de clase cerrada sin reparar, y es la unica forma de que")
        print("  esta puerta signifique algo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())