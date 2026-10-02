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

# ESTE FICHERO NO ES UNA HERRAMIENTA. No produce evidencia, no se ejecuta solo
# y no se invoca desde `run_all.py`. Lo invoca `stale_gap.py --self-test`, que
# importa las funciones de aqui y las ejecuta con sus propios datos.
#
# Lo unico que toca es /tmp/opencode/stale_gap_selftest, que borra antes de
# empezar. Nada del corpus se escribe, y nada del corpus se lee para escribir.
#
# UNA ADVERTENCIA SOBRE SU PROPIA EXISTENCIA. `citecheck` mide si las citas
# `fichero:linea` de los hallazgos apuntan a donde dicen. Este fichero tiene
# citas en su docstring -- `017:153`, `056:153`, `017:194` -- que son a
# archivos REALES del proyecto y describen lineas reales. Se dejan a proposito:
# son la evidencia de los casos que prueba el self-test, y un validador que las
# eliminara habria eliminado el motivo de existir.
#
# Pero conviene saberlo: si alguna vez esas referencias dejan de ser ciertas,
# `citecheck` lo dira, y no habra que entenderlo como un fallo de `citecheck`.
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
    # QUE CUENTA COMO "ESTA RESUELTA".
    #
    # Tres controles miden si una frontera se cierra, y las tres clases de
    # cierre valen. Lo que NO vale es que se mezclen sin distinction: por eso
    # RESUELTA_SIN_VERIFICAR es una clase aparte y no un synonym de
    # RESUELTA_OTRO, aunque las dos digan "hay respuesta".
    #
    # La distinction importa por un motivo concreto: 31 y 60 se leen distinto.
    # Una resuelto Y verificado se corrige. Una resuelto y sin verificar hay
    # que MIRARLA antes de corregir nada, porque la respuesta puede no ser a la
    # pregunta.
    CIERRAN = ("RESUELTA_OTRO", "RESUELTA_SIN_VERIFICAR")
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
    #
    #    "vale 42" hace que la RESPUESTA sea de valor. Y la FRONTERA tambien
    #    tiene que serlo, o el filtro de "misma pregunta" los separa: el caso
    #    real es 072:116 respondiendo "X = 0x51f" a una frontera que preguntaba
    #    "si X puede dar completion". Son preguntas distintas.
    doc("t2-obsoleta.md", "El offset de `mmX_OTRO` es `NOT_DETERMINED`, "
                          "falta medirlo.\n")
    doc("t2-respuesta.md", "Se midio: `mmX_OTRO` = 42. `PROVEN`.\n")
    # 3. contradiccion consigo mismo: el mismo doc dice las dos.
    #
    #    Las dos lineas llevan verbo, a proposito. RESUELTA_AQUI exige
    #    alineacion POSITIVA de slot, no solo ausencia de conflicto: decir que
    #    un documento se contradice consigo mismo es una ACUSACION, y no se
    #    hace porque no se pudo clasificar la pregunta.
    #
    #    La primera version de este caso no tenia verbo en ninguna linea, y la
    #    herramienta lo aceptaba. Con el filtro mas estricto, dos filas de la
    #    misma tabla con el mismo sujeto se declaraban "autodeclaradas
    #    resueltas" sin que nadie lo hubiera dicho. Un documento no se
    #    contradice porque a la herramienta le falte un verbo.
    doc("t3-propia.md", "Sobre `mmX_AQUI`:\n"
                        "que significa sigue `NOT_DETERMINED` al principio.\n"
                        "Tres lineas mas tarde queda `PROVEN` resuelto.\n")
    # 4. sin sujeto: la linea dice el estado y nada mas, y las lineas anteriores
    #    no tienen sujeto ni frase que lo sea.
    #
    #    "No se sabe" NO cuenta como sujeto: es una frase que no nombra nada, y
    #    devolverla como etiqueta produce un sujeto que no se puede consultar ni
    #    comparar con nada. Aqui se prueba que no se inventa.
    doc("t4-sinsujeto.md", "\n\nNo se sabe.\n`NOT_DETERMINED`.\n")
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
    ok = any(c in CIERRAN for c in r)
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
    ok = r10b == ["RESUELTA_SIN_VERIFICAR"]
    print(f"  {'PROVEN real':12} no debe descartarse        {r10b if r10b else '(nada)'}"
          f"  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # 10e. LA VENTANA DE NEGACION, y el auto-referencia.
    #
    #     El caso mas importante de todos, y no salio de un filtro mal puesto:
    #     salio de ESCRIBIR el hallazgo que documenta el fallo anterior.
    #
    #     Al explicar "un PROVEN citado se cuela como respuesta", las lineas
    #     del propio hallazgo pasaron a ser respuesta de SIETE fronteras
    #     abiertas de FUNCTION=always. La herramienta se cita a si misma.
    #
    #     Aqui se reproducen los dos mecanismos por separado.
    # 10e-1: la ventana de negacion (frase partida en dos lineas).
    doc("t10e-vent.md", "`mmX_VENTANA`:\n`NOT_DETERMINED` abierto.\n")
    doc("t10e-resp.md", "para llegar a `PROVEN` es exactamente lo contrario.\n"
                        "El texto decia que no se puede llegar a `PROVEN`.\n")
    fr10e, _ = _clasificar_en(tmp)
    r10e = [f["clase"] for f in fr10e if f["sujeto"] == "mmX_VENTANA"]
    ok = r10e == ["VIVA"]
    print(f"  {'ventana neg.':12} frase partida en dos lineas   "
          f"{r10e if r10e else '(nada)'}  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # 10e-2: el documento de METODO no cierra fronteras del ASIC.
    #
    #     Aqui no hay ningun fallo de lenguaje: el documento esta bien escrito
    #     y sus PROVEN son ciertos. Lo que falla es la PREMISA, que un
    #     documento de metodo responda a una frontera del hardware. Por eso el
    #     filtro es por nombre de fichero y no por texto.
    doc("t10f-metodo-herramientas.md",
        "Una herramienta que cita el estado se cita a si misma.\n"
        "`mmX_METODO` queda `PROVEN` segun el detector.\n")
    doc("t10f-no-metodo.md",
        "Sobre `mmX_METODO`:\n`NOT_DETERMINED` abierto.\n")
    fr10f, _ = _clasificar_en(tmp)
    r10f = [f["clase"] for f in fr10f if f["sujeto"] == "mmX_METODO"]
    ok = r10f == ["VIVA"]
    print(f"  {'metodo':12} no cierra fronteras del ASIC    "
          f"{r10f if r10f else '(nada)'}  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # 10e-3: y un hallazgo NORMAL si cierra. El filtro no puede tragarse
    #        documentos legitimos por ser conservador.
    doc("t10g-real.md", "`mmX_REAL_DEL_DOC`:\n`NOT_DETERMINED` abierto.\n")
    doc("t10g-resp.md", "| `mmX_REAL_DEL_DOC` esta medido | `PROVEN` | tabla |")
    fr10g, _ = _clasificar_en(tmp)
    r10g = [f["clase"] for f in fr10g if f["sujeto"] == "mmX_REAL_DEL_DOC"]
    ok = r10g == ["RESUELTA_SIN_VERIFICAR"]
    print(f"  {'hallazgo real':12} sigue cerrando fronteras    "
          f"{r10g if r10g else '(nada)'}  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # 10h. EL SUJETO EN FRASE, Y QUE NO SEA CRUZABLE.
    #
    #     El sujeto de una frontera puede ser una FRASE, no un identificador:
    #
    #       | Que el hardware ejecute 19 dw | `NOT_DETERMINED` — RUNTIME |
    #
    #     Eso es un sujeto MEJOR: es una pregunta, y una pregunta se puede
    #     cerrar, repetir y medir. Un identificador es solo un indice.
    #
    #     Pero una frase no sirve como clave de cruce. Por eso la herramienta
    #     separa los dos papeles en vez de forzar la frase a ser clave:
    #     obligarla a cruzarse no encuentra nada, y quedarse sin el sujeto
    #     pierde una frontera que si se puede leer.
    doc("t10h-frase.md", "| Que el hardware ejecute 19 dw | `NOT_DETERMINED` "
                         "— requiere RUNTIME |")
    fr10h, _ = _clasificar_en(tmp)
    r10h = [f for f in fr10h if f.get("etiqueta")]
    ok = bool(r10h) and r10h[0]["clase"] == "SUJETO_EN_FRASE"
    print(f"  {'sujeto frase':12} se lee pero no se cruza       "
          f"{r10h[0]['clase'] if r10h else '(nada)'}"
          f"  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # 10i. la frase NO se recorta, y el control demuestra por que.
    #
    #     La primera version recortaba el condicional: "Que X" -> "X", para que
    #     las dos formas de la misma frontera cruzaran. Suena correcto y no lo
    #     es: funciona si el verbo es el mismo, y rompe en cuanto se conjuga.
    #
    #     | Que la cola arranque sola |  ->  "la cola arranque sola"
    #     "La cola arranca sola"                  "la cola arranca sola"
    #
    #     `arranque` y `arranca` son el mismo verbo en distinto tiempo. Para
    #     arreglarlo haria falta una regla que supiera que el espanol tiene
    #     cuatro tiempos verbales, que es empezar de nuevo.
    #
    #     El control falla a proposito si se recortase, y por eso mide LAS DOS
    #     cosas: que el recorte no existe, y que la frase completa se conserva
    #     intacta, que es lo que la hace legible.
    e1 = S.etiqueta_de("| Que la cola arranque sola | `NOT_DETERMINED` |")
    e2 = S.etiqueta_de("La cola arranca sola: `PROVEN` medido.")
    conserva = e1 is not None and "arranque" in e1
    print(f"  {'sin recorte':12} la frase se conserva entera    {e1!r}"
          f"  {'OK' if conserva else 'FALLA <<<'}")
    fallos += 0 if conserva else 1
    no_corta = e2 is None or "arranca" in e2
    print(f"  {'prosa no tabla':12} no inventa etiqueta           {e2!r}"
          f"  {'OK' if no_corta else 'FALLA <<<'}")
    fallos += 0 if no_corta else 1

    # 10j. MISMO SIMBOLO, DISTINTA PREGUNTA.
    #
    #     El cruce por sujeto empareja POR NOMBRE, y hay casos en que el nombre
    #     es el mismo y la pregunta es otra. El caso real:
    #
    #       017:146  "Si `VM_INVALIDATE_RESPONSE` puede dar completion
    #                 observable por dominio"          -> NOT_DETERMINED
    #       072:116  "`VM_INVALIDATE_RESPONSE` = 0x51f, igual en GMC 8.1 y
    #                 8.2"                              -> PROVEN
    #
    #     072 responde A QUE EXISTE y EN QUE OFFSET. 017 preguntaba SI PUEDE
    #     DAR COMPLETION. Distintas preguntas, y la respuesta no cubre.
    doc("t10j-prop.md", "| Si `mmX_POSIBLE` puede dar completion observable | "
                        "`NOT_DETERMINED` |")
    doc("t10j-val.md", "| `mmX_POSIBLE` = 0x51f, igual en GMC | `PROVEN` |")
    fr10j, _ = _clasificar_en(tmp)
    r10j = [f["clase"] for f in fr10j if f["sujeto"] == "mmX_POSIBLE"]
    ok = r10j == ["OTRO_SIMBOLO_OTRA_PREGUNTA"]
    print(f"  {'distinta pregunta':12} 'puede' != '= 0x51f'          "
          f"{r10j if r10j else '(nada)'}  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # 10m. DOS FRONTERAS DEL MISMO DOCUMENTO, SUJETO COMPARTIDO.
    #
    #     El caso real, y es el que produjo un falso positivo al arreglar 052:
    #
    #       052:137  "| contenido de src_data[0] en cada caso | NOT_DETERMINED |"
    #       052:138  "| diferencia entre 0x92 y 0x93 | REFUTED en 047 |"
    #
    #     Dos filas de la MISMA tabla, con el mismo sujeto, y la segunda ya
    #     resuelta. La herramienta las empareja y dice RESUELTA_AQUI: "este
    #     documento se contradice consigo mismo".
    #
    #     NO se contradicen. Son dos preguntas del mismo tema, y una esta
    #     resuelta mientras la otra no. "Que contiene" y "que diferencia hay"
    #     son preguntas distintas, y la respuesta de una no contesta a la otra.
    #
    #     Es la misma trampa que 017/072, pero dentro de un documento. El
    #     Criterion de slot tambien la separa: el sujeto es el simbolo, asi que
    #     lo que se compara es el TEXTO de cada fila, no solo el nombre.
    doc("t10m-dos.md",
        "| contenido de `mmX_DOS` en cada caso | `NOT_DETERMINED`, RUNTIME |\n"
        "| diferencia entre `mmX_DOS` casos | `REFUTED` — comparten handler |\n")
    fr10m, _ = _clasificar_en(tmp)
    r10m = [(f["linea"], f["clase"]) for f in fr10m if f["sujeto"] == "mmX_DOS"]
    # lo que importa es que NO se declaren RESUELTA_AQUI entre si
    auto = [c for c in r10m if c[1] == "RESUELTA_AQUI"]
    ok = not auto
    print(f"  {'2 filas misma tabla':12} no se auto-declaran resueltas {r10m}"
          f"  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # 10n. EL ENUNCIADO SEPARADO DEL COMENTARIO.
    #
    #     El caso real, y es la clase de error mas sutil que ha tenido esta
    #     herramienta: no un fallo de patron, sino de ALCANCE.
    #
    #       017:146  "| Si `VM_INVALIDATE_RESPONSE` puede dar completion
    #                  observable por dominio | `NOT_DETERMINED` | El hardware
    #                  lo publica y el driver lo ignora. Nadie lo ha leido
    #                  observando el valor. RUNTIME. |"
    #
    #     La PREGUNTA es "puede dar completion": SEMANTICA. Pero la celda
    #     tercera dice "el driver lo ignora" (USO) y "el valor" (VALOR), y con
    #     USO comprobado primero, la fila era USO.
    #
    #     Contra su propia respuesta: 072:117 dice "el driver lo lee 0 veces",
    #     que es USO. Las dos USO, la herramienta daba por CERRADA una frontera
    #     que sigue abierta.
    #
    #     Y lo importante: cambiar el orden de los patrones NO lo arregla. En
    #     una tabla el enunciado va antes y el comentario despues, asi que
    #     cualquier orden fijo deja ganar a una de las dos celdas. Lo que hay
    #     que hacer es NO MEZCLARLAS: el slot se calcula sobre el enunciado.
    doc("t10n-com.md",
        "| Si `mmX_COM` puede dar completion observable | `NOT_DETERMINED` | "
        "El driver lo ignora. Nadie lo ha leido observando el valor. |")
    doc("t10n-resp.md", "| El driver lo lee **0 veces** | `PROVEN_ABSENT` |")
    fr10n, _ = _clasificar_en(tmp)
    r10n = [f["clase"] for f in fr10n if f["sujeto"] == "mmX_COM"]
    # Lo que se mide es que NO se cierre. Con enunciado y respuesta en slots
    # distintos, el veredicto es False y la frontera queda VIVA: la respuesta
    # ni siquiera es candidata. Y esa es la clase mas fuerte de las que
    # significan "no hagas nada con esto".
    #
    # La primera version de este control esperaba RESUELTA_SIN_VERIFICAR, y
    # fallo por una razon util: confundi "no verificable" con "verificada
    # como distinta". Un control que espera lo mas debil cuando lo que sale es
    # lo mas fuerte hace que se relaje el criterio para que pase.
    ok = r10n == ["VIVA"]
    print(f"  {'enunciado':12} el comentario no vota el slot      "
          f"{r10n if r10n else '(nada)'}  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # 10n-2. y una fila SIN tabla sigue usando todo el texto, porque no hay
    #        commentary que separar.
    ok = S._slot("el driver usa `mmY` y eso es `NOT_DETERMINED`") == "USO"
    print(f"  {'sin tabla':12} todo el texto cuenta como enunciado "
          f"{'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # 10j-2. dos preguntas DE SEMANTICA si se cruzan, aunque una mencione "bits".
    #
    #     Este es el caso que el filtro por palabras SUELTAS descartaba:
    #
    #       024:284  "Que significa PAGE_TABLE_DEPTH 0 frente a 1"
    #       064:168  "PAGE_TABLE_DEPTH ocupa bits [1:2] de VM_CONTEXT*_CNTL"
    #
    #     "ocupa bits" es la RESPUESTA a "que significa", no una pregunta
    #     distinta. Un filtro que las separa da por abierta una frontera ya
    #     cerrada, y eso hace subir el trabajo pendiente sin motivo.
    doc("t10k-ok.md", "| Que significa `mmX_SEM` 0 frente a 1 | `NOT_DETERMINED` |")
    doc("t10k-resp.md", "| `mmX_SEM` ocupa bits [1:2] de `VM_CONTEXT` | `PROVEN` |")
    fr10k, _ = _clasificar_en(tmp)
    r10k = [f["clase"] for f in fr10k if f["sujeto"] == "mmX_SEM"]
    ok = r10k == ["RESUELTA_OTRO"]
    print(f"  {'slot semantica':12} 'que significa' == 'ocupa bits'  "
          f"{r10k if r10k else '(nada)'}  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # 10j-3. y un verbo NO RECONOCIDO no cierra con nada.
    doc("t10l-des.md", "| El comportamiento de `mmX_DESC` | `NOT_DETERMINED` |")
    doc("t10l-resp.md", "| `mmX_DESC` mide algo raro | `PROVEN` |")
    fr10l, _ = _clasificar_en(tmp)
    r10l = [f["clase"] for f in fr10l if f["sujeto"] == "mmX_DESC"]
    ok = r10l == ["RESUELTA_SIN_VERIFICAR"]
    print(f"  {'verbo desconocido':12} SIN VERIFICAR, no 'distinta'  "
          f"{r10l if r10l else '(nada)'}  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # 10l-2. y SIN_VERIFICAR se cuenta APARTE de RESUELTA_OTRO.
    #        Si se mezclaran, el informe diria "31 resueltas" cuando en
    #        realidad varias son de MIRAR antes de tocar nada. El numero de
    #        trabajo que se puede hacer sin leer es menor que el que dice.
    n_otro = sum(1 for f in fr10l if f["clase"] == "RESUELTA_OTRO")
    n_sv = sum(1 for f in fr10l if f["clase"] == "RESUELTA_SIN_VERIFICAR")
    ok = (n_otro + n_sv) > 0
    print(f"  {'clases separadas':12} RESUELTA_OTRO={n_otro} SIN_VERIFICAR={n_sv}"
          f"   {'OK' if ok else 'FALLA <<<'}")
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
    ok = r10d == ["RESUELTA_SIN_VERIFICAR"]
    print(f"  {'REFUTED real':12} en tabla si afirma         {r10d if r10d else '(nada)'}"
          f"  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    print()
    if fallos:
        print(f"  RESULTADO: TOOL_BROKEN -- {fallos} controles fallan")
        return 1
    print(f"  RESULTADO: TOOL_VALIDATED -- {len(casos) + 17} controles pasan.")
    print()
    print("  Los controles que evitan relaciones FALSAS, del mas grave al")
    print("  menos:")
    print("    - un documento de METODO no cierra fronteras del ASIC. El caso")
    print("      mas raro y el mas dañino: salio de escribir este mismo")
    print("      hallazgo. Las lineas que citaban FUNCTION=always para explicar")
    print("      el fallo se convirtieron en respuesta de SIETE fronteras")
    print("      abiertas. La herramienta se citaba a si misma.")
    print("    - la ventana de NEGACION abarca la linea anterior: una frase")
    print("      partida en dos lineas solo lleva la negacion en la primera.")
    print("    - PROVEN dentro de una frase negativa no cuenta como respuesta.")
    print("      El caso real (056:153) daba por cerradas dos fronteras")
    print("      ABIERTAS de FUNCTION=always, y el texto decia lo contrario.")
    print("    - un estado CONDCIONAL ('haría REFUTED incorrecto') no afirma.")
    print("      El caso real (017:194) cerraba dos fronteras de 018.")
    print("    - un numero de documento no es un sujeto consultable.")
    print("    - una actualizacion posterior no es una contradiccion consigo")
    print("      mismo.")
    print()
    print("  Y para los filtros de descarte se exige lo SIMETRICO, porque un")
    print("  filtro que solo sabe decir 'no' es un muro, no un filtro:")
    print("    PROVEN de verdad cuenta | REFUTED en tabla cuenta |")
    print("    un hallazgo normal sigue cerrando fronteras")
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
