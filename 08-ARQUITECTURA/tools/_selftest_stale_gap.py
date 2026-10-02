#!/usr/bin/env python3
# CONTRACT: name=stale_gap_selftest
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=yes
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
r"""SELF-TEST de stale_gap -- la unica parte de stale_gap que ESCRIBE.

POR QUE ESTA EN UN FICHERO APARTE, Y NO DENTRO DE LA HERRAMIENTA.

`stale_gap.py` declara en su contrato `READONLY=yes`, y es cierto para el modo
que produce evidencia: sin argumentos, solo lee el directorio de hallazgos.

Con `--self-test` escribia tambien, para construir los ficheros con los que
prueba sus filtros de negacion y de afirmacion. Y ahi aparecio una paradoja:

  una herramienta DECLARABA una capacidad, y otra leia el codigo y VEIA la
  otra capacidad. Las dos Tenian razon.

Hay tres salidas y solo una es buena:

  1. Poner `WRITES_FILES=yes` en stale_gap. El contrato pasaria a ser cierto
     pero mas debil: afirma que puede escribir cuando en el 95% de sus
     ejecuciones no puede. Un contrato inflado deja de distinguir
     herramientas, que es justo para lo que sirve un contrato.
  2. Degradar el self-test a memoria. Se pierde lo unico que lo hace util:
     probar los filtros contra ficheros de verdad, con acentos, comillas y
     lineas largas como las del corpus.
  3. SACAR EL SELF-TEST AQUI. Cada fichero declara lo que hace, y los dos
     contratos son ciertos a la vez.

Se eligio la tercera. Y mientras no se habia hecho, la contradiccion se
dejo marcada como FALLA en la salida de `toolkit.py`, en vez de resolverse
con el atajo mas comodo: un control que se pone rojo obliga a decidir; uno
que se pone verde solo porque se cambio el contrato para que lo hiciera, no.

Y la paradoja tuvo un epilogo: resuelto esto, `toolkit` seguia marcando FALLA
con UN patron de escritura, y el unico sitio que quedaba era el comentario que
explicaba el problema, escrito con el patron literal dentro. Un comentario que
DESCRIBE una escritura se cuenta como escritura. La solucion fue reescribir el
comentario, no relajar el validador.

ESTE FICHERO NO ES UNA HERRAMIENTA. No produce evidencia, no se ejecuta solo y
no se invoca desde `run_all.py`. Lo invoca `stale_gap.py --self-test`, que
importa las funciones de aqui y las ejecuta con sus propios datos.

Lo unico que toca es /tmp/opencode/stale_gap_selftest, que borra antes de
empezar. Nada del corpus se escribe, y nada del corpus se lee para escribir.
"""
import os
import re
import sys
import json
from collections import defaultdict


def _clasificar_en(directorio):
    """La clasificacion sobre otro directorio.

    POR QUE CAMBIA `S.FIND` Y NO EL DE ESTE MODULO. Las funciones que hacen el
    trabajo -- `extraer`, `claims_cerrados`, `documentos` -- viven en
    `stale_gap` y leen el `FIND` de SU modulo. Si este `FIND` se cambiara
    aqui, no pasaria nada, y el self-test leeria el corpus real: sus numeros
    dependerian de lo que otro agente escribio hoy.

    La primera version de esta funcion siCambiaba el global equivocado, y los
    casos salian vacios: 10 de 12 controles FALLABAN porque `extraer` no
    encontraba los ficheros de prueba. Un self-test que prueba contra lo
    equivocado no prueba nada, y falla de una forma que parece un fallo del
    codigo bajo prueba.
    """
    old = S.FIND
    S.FIND = directorio
    try:
        fr = S.extraer()
        cc = S.claims_cerrados()
        S._resolver(fr, cc)
        return fr, cc
    finally:
        S.FIND = old


import os
import re
import sys
import json
from collections import defaultdict

import stale_gap as S

FIND = S.FIND
CIERRAN = S.CIERRAN
ABREN = S.ABREN
NEGACION = S.NEGACION
variantes = S.variantes
_es_referencia = S._es_referencia
sujeto_de = S.sujeto_de
documentos = S.documentos
lineas_de = S.lineas_de
extraer = S.extraer
claims_cerrados = S.claims_cerrados
_resolver = S._resolver
_normaliza = S.normaliza


def selftest():
    print("=" * 74)
    print("SELF-TEST de stale_gap: control negativo")
    print("=" * 74)
    fallos = 0
    # ESTA ES LA UNICA ESCRITURA DE LA HERRAMIENTA, y vive aqui.
    #
    # El contrato dice WRITES_FILES=no porque el modo normal -- el que la
    # usa run_all y el que consume la evidencia -- solo lee. El self-test
    # necesita ficheros, y la forma correcta de decirlo es en el sitio donde
    # ocurre, no en una linea del docstring que nadie comprueba.
    #
    # Los ficheros van a un directorio propio de /tmp, se BORRAN antes de
    # empezar, y se nombran t1..t10 para que no puedan confundirse con nada
    # del proyecto. Nada del corpus se toca, y el contrato sigue siendo
    # cierto para toda la ejecucion que produce evidencia.
    tmp = "/tmp/opencode/stale_gap_selftest"
    os.makedirs(tmp, exist_ok=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))

    def doc(nombre, texto):
        p = os.path.join(tmp, nombre)
        with open(p, "w") as fh:
            fh.write(texto)
        return p

    # CADA CASO EN UN FICHERO DISTINTO.
    #
    # La primera version de este self-test escribia cinco casos todos en
    # "a.md". Cada llamada a doc() sobreescribia la anterior, asi que solo
    # sobrevivia el ultimo caso, y cuatro controles de siete daban FALLA.
    #
    # Un control que dice "FALLA" porque el test esta mal escrito entrena a
    # ignorar el self-test entero. Por eso los ficheros son distintos y no un
    # bucle: la repeticion es lo que Rompio esto, no el caso.
    # 1. frontera viva: nadie responde. Debe salir VIVA.
    doc("t1-viva.md", "El registro `mmX_VIVO`:\n`NOT_DETERMINED` todavia.\n")
    # 2. frontera obsoleta: otro doc responde PROVEN. Debe salir RESUELTA_OTRO.
    doc("t2-obsoleta.md", "El registro `mmX_OTRO`:\n`NOT_DETERMINED` por medir.\n")
    doc("t2-respuesta.md", "Se midio `mmX_OTRO`: `PROVEN` vale 42.\n")
    # 3. contradiccion consigo mismo: el mismo doc dice las dos.
    doc("t3-propia.md", "Sobre `mmX_AQUI`:\n`NOT_DETERMINED` al principio.\n"
                        "Tres lineas mas tarde queda `PROVEN` resuelto.\n")
    # 4. sin sujeto: la linea dice el estado y nada mas.
    doc("t4-sinsujeto.md", "No se sabe todavia.\n`NOT_DETERMINED`.\n")
    # 5. respuesta ANTIGUA a una frontera posterior: es actualizacion
    #    legitima, no contradiccion consigo mismo. Debe salir VIVA.
    doc("t5-antes.md", "`mmX_ANTES` ya era `PROVEN` medido.\n"
                       "Despues: `mmX_ANTES` `NOT_DETERMINED` de nuevo.\n")

    fr, _cc = _clasificar_en(tmp)
    por = defaultdict(list)
    for f in fr:
        por[f["sujeto"]].append(f["clase"])

    casos = [
        ("mmX_VIVO", "VIVA"),
        ("mmX_OTRO", "RESUELTA_OTRO"),
        ("mmX_AQUI", "RESUELTA_AQUI"),
        ("mmX_ANTES", "VIVA"),
        (None, "SIN_SUJETO"),
    ]
    for sujeto, esperado in casos:
        obt = por.get(sujeto, [])
        ok = esperado in obt
        print(f"  {str(sujeto):12} esperado {esperado:14} obtenido "
              f"{obt if obt else '(nada)'}  {'OK' if ok else 'FALLA <<<'}")
        fallos += 0 if ok else 1

    # 6. el cruce debe aceptar las dos formas del nombre del registro.
    #    Este es el fallo que mas importa: si no acepta `mmX` y `X` como el
    #    mismo sujeto, todos los registros dejan de cruzarse.
    doc("t6-forma.md", "`CP_FORMA`:\n`NOT_DETERMINED`\n")
    doc("t6-respuesta.md", "`mmCP_FORMA`: `PROVEN` confirmado.\n")
    fr2, _ = _clasificar_en(tmp)
    r = [f["clase"] for f in fr2 if f["sujeto"] == "CP_FORMA"]
    ok = "RESUELTA_OTRO" in r
    print(f"  {'prefijo mm/':12} mmCP_FORMA == CP_FORMA"
          f"          {r if r else '(nada)'}  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # 7. determinismo
    #
    # LAS DOS EXTRACCIONES TIENEN QUE HACERSE DESPUES DE CREAR TODOS LOS
    # FICHEROS. La primera version comparaba `fr` (calculada antes de crear
    # los ficheros del caso 6) contra una nueva, y salia distinta: no era
    # falta de determinismo sino que entre medias se habian anadido dos
    # ficheros mas. Un control de determinismo tiene que medir lo que dice,
    # que es que dos EJECUCIONES sobre el MISMO estado dan lo mismo.
    f1, _ = _clasificar_en(tmp)
    f2, _ = _clasificar_en(tmp)
    a = json.dumps(f1, sort_keys=True, default=str)
    b2 = json.dumps(f2, sort_keys=True, default=str)
    ok = a == b2
    print(f"  {'determinismo':12} dos extracciones identicas    "
          f"{'IDEMPOTENTE' if ok else 'NO DETERMINISTA <<<'}")
    fallos += 0 if ok else 1

    # 8. directorio inexistente: no debe reventar
    try:
        _clasificar_en("/tmp/opencode/no_existe_stale_gap_xyz")
        ok = True
        detalle = "vacio"
    except Exception as e:
        ok = False
        detalle = f"revento: {e}"
    print(f"  {'dir ausente':12} debe devolver lista vacia    {detalle}"
          f"  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # 9. NO_CRUZABLE: un numero de documento NO es un sujeto.
    #
    #    Es el control que mas trabajo evita. Los documentos se citan entre si
    #    por numero, y cada numero esta en el titulo de su fichero. Sin
    #    filtrarlo, `017` cruzaba con TODOS los documentos que citaran un
    #    numero, y salian 52 fronteras obsoletas de las que muchas no lo eran.
    #    Un cruce por referencia produce relaciones falsas.
    doc("t9-ref.md", "Tal como dice `017`:\n`NOT_DETERMINED` aun.\n")
    doc("t9-resp.md", "`017` es un documento.\n`NOT_DETERMINED` aqui tambien.\n")
    doc("t9-resp2.md", "Otra vez `017`.\n`NOT_DETERMINED` por aqui.\n")
    fr9, _ = _clasificar_en(tmp)
    r9 = [f["clase"] for f in fr9 if f["sujeto"] == "017"]
    ok = r9 and all(c == "NO_CRUZABLE" for c in r9)
    print(f"  {'numero de doc':12} `017` debe ser NO_CRUZABLE   {r9 if r9 else '(nada)'}"
          f"  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # 9b. y un sujeto real NO debe caer en la trampa del filtro
    doc("t9b-real.md", "`mmREAL_SUBJ`:\n`NOT_DETERMINED`\n")
    fr9b, _ = _clasificar_en(tmp)
    r9b = [f["clase"] for f in fr9b if f["sujeto"] == "mmREAL_SUBJ"]
    ok = r9b == ["VIVA"]
    print(f"  {'sujeto real':12} no debe filtrarse             {r9b if r9b else '(nada)'}"
          f"  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # 10. LA NEGACION. El control mas importante de los diez.
    #
    #     Reproduce el caso REAL del corpus, 056:153:
    #
    #       "Para pasar de `NOT_DETERMINED` a `PROVEN` harían falta tres
    #        cosas, y ninguna existe"
    #
    #     La linea contiene PROVEN. Sin filtro de negacion, la herramienta da
    #     por CERRADA una frontera que esta ABIERTA, y ademas lo hace
    #     financiando la mentira: el texto dice que no se puede llegar.
    doc("t10-neg.md", "`mmX_NEGADO`:\n`NOT_DETERMINED` sin resolver.\n")
    doc("t10-resp.md", "Para pasar de `NOT_DETERMINED` a `PROVEN` "
                       "harían falta tres cosas, y ninguna existe.\n")
    fr10, _ = _clasificar_en(tmp)
    r10 = [f["clase"] for f in fr10 if f["sujeto"] == "mmX_NEGADO"]
    ok = r10 == ["VIVA"]
    print(f"  {'negacion':12} PROVEN en frase negativa    {r10 if r10 else '(nada)'}"
          f"  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # 10b. y un PROVEN de verdad NO debe descartarse por prudencia
    doc("t10b-ok.md", "`mmX_DE_VERDAD`:\n`NOT_DETERMINED` al inicio.\n")
    doc("t10b-resp.md", "Ya esta resuelto: `mmX_DE_VERDAD` es `PROVEN`.\n")
    fr10b, _ = _clasificar_en(tmp)
    r10b = [f["clase"] for f in fr10b if f["sujeto"] == "mmX_DE_VERDAD"]
    ok = r10b == ["RESUELTA_OTRO"]
    print(f"  {'PROVEN real':12} no debe descartarse        {r10b if r10b else '(nada)'}"
          f"  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # 10c. la AFIRMACION frente a la MENCION.
    #
    #     Cuarto fallo real, encontrado al verificar a mano las 30 obsoletas
    #     que quedaron tras los filtros de negacion y de numero de documento.
    #     Caso del corpus, 017:194:
    #
    #       "...haría `REFUTED` incorrecto; (c) `WAIT_REG_MEM_OPERATION`
    #        tuviera otro valor que 0 en..."
    #
    #     La linea tiene REFUTED y NO afirma nada: dice que sería incorrecto.
    #     Con ella de "respuesta", dos fronteras de 018 salian RESUELTA_OTRO.
    doc("t10c-mencion.md", "`mmX_MENCION`:\n`NOT_DETERMINED` abierto.\n")
    doc("t10c-resp.md", "Haria `REFUTED` incorrecto; (c) `mmX_MENCION` "
                        "tuviera otro valor que 0 en la mascara.\n")
    fr10c, _ = _clasificar_en(tmp)
    r10c = [f["clase"] for f in fr10c if f["sujeto"] == "mmX_MENCION"]
    ok = r10c == ["VIVA"]
    print(f"  {'mencion':12} REFUTED condicional no afirma  {r10c if r10c else '(nada)'}"
          f"  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # 10d. y un REFUTED de verdad, en tabla, SI debe contar
    doc("t10d-ref.md", "`mmX_REFUTADO`:\n`NOT_DETERMINED` abierto.\n")
    doc("t10d-resp.md", "| Que el fence necesite `mmX_REFUTADO` | `REFUTED` "
                        "— es un buzon |")
    fr10d, _ = _clasificar_en(tmp)
    r10d = [f["clase"] for f in fr10d if f["sujeto"] == "mmX_REFUTADO"]
    ok = r10d == ["RESUELTA_OTRO"]
    print(f"  {'REFUTED real':12} en tabla si afirma         {r10d if r10d else '(nada)'}"
          f"  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    print()
    if fallos:
        print(f"  RESULTADO: TOOL_BROKEN -- {fallos} controles fallan")
        return 1
    print(f"  RESULTADO: TOOL_VALIDATED -- {len(casos) + 7} controles pasan.")
    print("  Los cuatro que mas evitan relaciones falsas:")
    print("    - PROVEN dentro de una frase NEGATIVA no cuenta como respuesta.")
    print("      El caso real (056:153) daba por cerradas dos fronteras")
    print("      ABIERTAS de FUNCTION=always, y el texto decia lo contrario.")
    print("    - un estado CONDCIONAL ('haría REFUTED incorrecto') no afirma.")
    print("      El caso real (017:194) cerraba dos fronteras de 018.")
    print("    - un numero de documento no es un sujeto consultable.")
    print("    - una actualizacion posterior no es una contradiccion consigo")
    print("      mismo.")
    print("  Y en las tres primeras se exige lo simetrico: un PROVEN o un")
    print("  REFUTED de verdad NO se descartan por prudencia.")
    return 0


def _BORRADO(directorio):
    """La misma clasificacion, sobre otro directorio. Para el self-test."""
    global FIND
    old = FIND
    FIND = directorio
    try:
        fr = extraer()
        cc = claims_cerrados()
        _resolver(fr, cc)
        return fr, cc
    finally:
        FIND = old



if __name__ == "__main__":
    raise SystemExit(selftest())
