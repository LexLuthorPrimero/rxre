#!/usr/bin/env python3
# CONTRACT: name=gfx8_opcode
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: EXIT_ON_SUCCESS=0
"""gfx8_opcode -- la tabla de opcode de GFX8, POR FAMILIA.

QUE CORRIGE, y de donde sale

    El diseno 013 dice: "44 de 77 valores SQ_S_* estan en mas de una tabla" y
    lo llama AMBIGUOUS. Medido: 77 valores distintos, 216 entradas, 44 con mas de
    un nombre. Es cierto. Lo que no es cierto es que eso sea una ambiguedad:

        0x00 -> S_MOV_B32, S_MOVK_I32, S_LOAD_DWORD, S_NOP, S_CMP_EQ_I32, S_ADD_U32
        0x01 -> S_MOV_B64, S_CMOVK_I32, S_LOAD_DWORDX2, S_ENDPGM, S_CMP_LG_I32, S_SUB_U32

    Eso no es un valor con dos nombres. Son SEIS TABLAS COMPLETAS, cada una
    empezando en cero e incrementando. S_ADD_U32=0, S_SUB_U32=1, S_ADD_I32=2 es
    una tabla; S_MOV_B32=0, S_MOV_B64=1, S_CMOV_B32=2 es otra.

    La pregunta "¿que es el opcode 0x00?" esta MAL FORMADA: le falta la
    dimension. Una vez que se dice de que FAMILIA, el valor es univoco.

POR QUE ESTO DESBLOQUEA LO QUE 013 DEJO ABIERTO

    013 dice que el programa GCN8 minimo necesita "decidir la tabla
    instruccion->opcode: RUNTIME_REQUIRED para verificarlo, pero escribible si se
    acepta tabla EXTERNAL".

    Y eso es exactamente lo que hay aqui: una tabla EXTERNAL no ambigua, derivada
    de gfx_8_0_enum.h, sin ejecutar nada y sin escribir en la GPU.

LO QUE ESTO NO ES

    No es un ensamblador. No sabe codificar una instruccion completa: solo sabe
    el valor de opcode DENTRO de una familia. Los demas campos --register,
    operandos, tipo-- son OTRA tabla y no estan aqui. Decir "0x00 = S_LOAD_DWORD"
    NO es un programa ensamblable: es la mitad izquierda del encoding.

HISTORIA DE ESTA HERRAMIENTA, porque su v1 afirmo algo falso
    (nunca se borra: el error es parte del resultado)

    v1 guardaba las familias como fam[clave][valor] = nombre, un dict indexado
    por valor, y detector de invertibilidad que recorria ese dict. Con esa forma
    DOS NOMBRES CON EL MISMO VALOR NO SON REPRESENTABLES: el segundo sobrescribe
    al primero. Asi que v1 imprimia "0 colisiones internas" SIEMPRE, con
    cualquier entrada. No era una medicion: era una tautologia, y el instrumento
    no podia fallar.

    v1 tambien imprimia "216 valores distintos" cuando hay 77, porque al pasar a
    pares contaba tuplas (nombre, valor) en vez de valores.

    v2 corrige las dos cosas: guarda PARES, que si admiten duplicados, y cuenta
    valores de verdad. Y al poder fallar por fin, resulto que SI hay una
    colision: la familia "S" en 0x10, con S_SENDMSG y S_SETVSKIP.

    Esa colision esta MEDIDA y CLASIFICADA, no hideada: depende de la regla de
    agrupacion, que es una convencion mia y no algo de la cabecera. Bajo la
    regla 'completo' -- un nombre de dos segmentos es su propia familia, porque
    no se puede partir -- la colision desaparece. Por eso la conclusion que se
    sostiene es "no se observa ambiguedad de opcode con estas dos reglas", y
    NO "PROVEN_ABSENT de ambiguedad".

VALIDACION DE LA HERRAMIENTA

    --self-test  extraction, conservacion en las dos direcciones, invertibilidad
                 bajo la regla que se afirma, y ejecucion real del camino de
                 impresion con comprobacion de su contrato de salida.
    --negativo   6 controles: el detector TIENE que senalar colisiones, perdidas
                 e invenciones con datos sinteticos, y NO tiene que senalarlas
                 donde no las hay. Incluye el caso real al final, para que un
                 filtro solo con negativos no llegue a rechazar todo.
    cross-check  Recuento por awk/sort/uniq. DIFIERE: 152/53 contra 216/77. La
                 diferencia son 64 entradas con hex en minuscula (0xa..0xf) que
                 el grep del cross-check no aceptaba. Diagnostico: el defecto
                 estaba en el cross-check, no en la herramienta. 216 y 77.
"""
import collections
import os
import re
import sys

ROOT = "/home/lucas/Escritorio/RX550-INVESTIGACION"
ENUM = os.path.join(ROOT, "RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd"
                    "/include/asic_reg/gca/gfx_8_0_enum.h")

# Solo esta cabecera existe en el corpus. Las otras 4 tablas de opcode del GCN8
# NO ESTAN, que es lo que 013 llama NOT_AVAILABLE. No se inventan: si no estan,
# no se escriben.
RE_DEF = re.compile(r"^#define\s+SQ_(S_[A-Z0-9_]+)\s+0x([0-9A-Fa-f]+)\s*$")


def tabla():
    """{familia: [(nombre, valor), ...]} y {nombre: (familia, valor)}.

    OJO CON LA FORMA DEL DATO, que fue un fallo real de la v1:

    La v1 guardaba fam[clave][valor] = nombre, un dict indexado por valor.
    Con esa forma, dos nombres de la misma familia con el mismo valor NO SON
    REPRESENTABLES: el segundo sobrescribe al primero. Y como el detector
    recorria d.items() -- donde cada valor aparece una vez por construccion --
    reportaba "0 colisiones internas" SIEMPRE, con cualquier entrada. Era una
    tautologia, no una medicion: el instrumento no podia fallar.

    Aqui se guardan PARES (nombre, valor), que si admiten duplicados. Asi
    "0 colisiones" es un resultado medido y no un resultado imposible.
    """
    fam = collections.defaultdict(list)
    nom = {}
    with open(ENUM, encoding="utf-8", errors="replace") as fh:
        for linea in fh:
            m = RE_DEF.match(linea)
            if not m:
                continue
            n, v = m.group(1), int(m.group(2), 16)
            p = n.split("_")
            clave = "_".join(p[:2]) if len(p) > 2 else "_".join(p[:1])
            fam[clave].append((n, v))
            nom[n] = (clave, v)
    return fam, nom


def por_valor(pares):
    """{valor: nombre} desde [(nombre, valor), ...]. Para mostrar, no para medir.

    NO usar para la comprobacion de invertibilidad: al indexar por valor
    descarta justo lo que se quiere detectar.
    """
    return {v: n for n, v in pares}


def colisiones_internas(fam):
    """Familias con dos nombres distintos para el MISMO valor.

    Ahora es una MEDICION real: la entrada son pares y un par duplicado
    sobrevive hasta aqui.
    """
    malas = []
    for k, pares in fam.items():
        visto = collections.defaultdict(set)
        for n, v in pares:
            visto[v].add(n)
        for v, noms in visto.items():
            if len(noms) > 1:
                malas.append((k, v, sorted(noms)))
    return malas


def agrupar(pares, regla):
    """Agrupa pares (nombre, valor) en familias segun una regla.

    La familia NO esta en la cabecera: es una convencion mia. Por eso la
    colision depende de la regla y hay que medir su sensibilidad en vez de
    declarar que el opcode es ambiguo.

      prefijo2 : los dos primeros segmentos. Un nombre de solo 2 segmentos
                 (S_NOP, S_SENDMSG) cae en la familia "S", que mezcla tablas
                 distintas porque a un nombre asi no le queda nada que partir.
      completo : si el nombre tiene 2 segmentos es su propia familia, porque un
                 solo nombre no se puede partir en dos.
    """
    fam = collections.defaultdict(list)
    for n, v in pares:
        p = n.split("_")
        if regla == "completo" and len(p) <= 2:
            clave = n
        elif len(p) > 2:
            clave = "_".join(p[:2])
        else:
            clave = "_".join(p[:1])
        fam[clave].append((n, v))
    return fam


def conservacion(crudos, nom):
    """Fallos de conservacion entre la cabecera y la tabla.

    Dos direcciones, y las dos importan:
      - crudos <= nom  : nada de la cabecera se perdio al extraer
      - nom  <= crudos : la tabla no invento nombres
    Una sola direccion no alcanza: un extractor que copia sin leer pasaria
    la primera y un extractor que inventa pasaria la segunda.
    """
    fallos = []
    if not crudos <= set(nom):
        perdidos = sorted(crudos - set(nom))
        fallos.append("hay nombres de la cabecera que no llegaron a la tabla "
                      "(%d, p.ej. %s)" % (len(perdidos), perdidos[:3]))
    if not set(nom) <= crudos:
        inventados = sorted(set(nom) - crudos)
        fallos.append("la tabla trae nombres que no estan en la cabecera "
                      "(%d, p.ej. %s)" % (len(inventados), inventados[:3]))
    return fallos


def _negativo():
    """Controles negativos: el detector TIENE que detectar.

    Sin esto, "0 colisiones internas" es una frase sin fuerza: un detector
    que nunca dice que nada tambien diria 0. Aqui se le pasan datos
    deliberadamente rotos y se exige que los senale.

    Y el caso real se ejecuta igual, al final: un filtro solo con negativos
    tambien puede rechazar todo.tiene que seguir aceptando lo bueno.
    """
    fallos = []
    # (1) colision interna: dos nombres de una MISMA familia con el mismo valor.
    #     En PARES, que es la unica forma donde esto es representable.
    roto = {"S_FALSA": [("X_A", 0x00), ("X_B", 0x00)],
            "S_BUENA": [("S_LOAD_DWORD", 0x00)]}
    if not colisiones_internas(roto):
        fallos.append("colisiones_internas NO vio una familia con dos nombres "
                      "en 0x00: el detector de invertibilidad no funciona")
    # (2) caso limpio: no debe senalar colisiones donde no las hay
    if colisiones_internas({"S_OK": [("A", 0), ("B", 1)]}):
        fallos.append("colisiones_internas senalo una colision que no existe: "
                      "el detector da falsos positivos")
    # (2b) el MISMO nombre dos veces en la misma familia con el mismo valor no
    #      es colision: es una duplicacion textual de la cabecera
    if colisiones_internas({"S_DUP": [("A", 0), ("A", 0)]}):
        fallos.append("colisiones_internas senalo una duplicacion del mismo "
                      "nombre: no es una colision de opcode")
    # (3) extractor que pierde nombres
    if not conservacion({"A", "B"}, {"A"}):
        fallos.append("conservacion NO vio que falta B: no detecta perdidas")
    # (4) extractor que inventa nombres
    if not conservacion({"A"}, {"A", "FANTASMA"}):
        fallos.append("conservacion NO vio el nombre FANTASMA: no detecta "
                      "invenciones")
    # (5) caso limpio en las dos direcciones
    if conservacion({"A", "B"}, {"A", "B"}):
        fallos.append("conservacion senalo un problema donde no lo hay")
    # (6) Y el caso real. Aqui ya NO se exige "0 colisiones" como deseo: se
    #     exige lo que de verdad sostiene la conclusion, que la colision se
    #     explica por la regla y no por el opcode.
    fam, nom = tabla()
    if not fam:
        fallos.append("el caso real no se lee: el extractor no funciona")
    todos = [par for pares in fam.values() for par in pares]
    c2 = colisiones_internas(agrupar(todos, "prefijo2"))
    c3 = colisiones_internas(agrupar(todos, "completo"))
    if c3:
        fallos.append("bajo la regla 'completo' siguen quedando %d colisiones: "
                      "haria falta explicar cual es la ambiguedad real de "
                      "opcode, y la conclusion 'no es ambiguedad' seria falsa"
                      % len(c3))
    if not c2:
        fallos.append("bajo 'prefijo2' no sale ninguna colision, pero la regla "
                      "'completo' no es mas restrictiva: agrupar() no esta "
                      "midiendo lo que dice medir")
    # el caso de colision debe caer SIEMPRE en nombres de 2 segmentos, que es
    # justo el artefacto que se afirma
    for k, v, ns in c2:
        if not all(len(n.split("_")) <= 2 for n in ns):
            fallos.append("colision %s 0x%02X con nombres de 3+ segmentos: eso "
                          "no lo explica la regla 'S', y la lectura seria falsa"
                          % (k, v))
    crudos = _crudos()
    if conservacion(crudos, nom):
        fallos.append("el caso real no conserva: %s"
                      % conservacion(crudos, nom)[0])
    if len(fam) < 20 or len(nom) < 100:
        fallos.append("el caso real trae poco (%d familias, %d nombres): "
                      "se esperan >20 familias y >100 nombres"
                      % (len(fam), len(nom)))
    if fallos:
        print("CONTROLES NEGATIVOS FALLAN:")
        for f in fallos:
            print("   %s" % f)
        return 1
    print("controles negativos OK (6/6 detectan; caso real: %d familias, %d "
          "nombres, %d colisiones bajo prefijo2 y %d bajo completo)"
          % (len(fam), len(nom), len(c2), len(c3)))
    return 0


def _crudos():
    """Los nombres tal cual estan en la cabecera, sin extraer ni agrupar."""
    with open(ENUM, encoding="utf-8", errors="replace") as fh:
        return {m.group(1) for m in (RE_DEF.match(l) for l in fh) if m}


def main(argv):
    if "--self-test" in argv or "--self" in argv:
        return selftest()
    if "--negativo" in argv:
        return _negativo()
    fam, nom = tabla()
    nombres = [n for pares in fam.values() for n, _ in pares]
    valores = {v for pares in fam.values() for _, v in pares}
    print("TABLA DE OPCODE GFX8 POR FAMILIA")
    print()
    print("  %d familias, %d nombres, %d valores distintos"
          % (len(fam), len(nombres), len(valores)))
    print("  fuente: gfx_8_0_enum.h  (las otras 4 tablas de opcode NO estan)")
    print()
    print("  OJO: 'valores' son valores GLOBALES, sin familia. Menos de %d"
          % len(nombres))
    print("  significa que un mismo numero es opcode en mas de una tabla")
    print("  distinta, que es lo normal en GCN8: 0x00 es ADD_U32 y tambien")
    print("  LOAD_DWORD y tambien MOV_B32.")
    print()
    print("  %-14s %-8s %s" % ("familia", "valores", "rango"))
    print("  " + "-" * 48)
    for k in sorted(fam, key=lambda x: (-len(fam[x]), x))[:14]:
        d = por_valor(fam[k])
        print("  %-14s %-8d 0x%02X-0x%02X" % (k, len(d), min(d), max(d)))
    print()
    malas = colisiones_internas(fam)
    todos = [par for pares in fam.values() for par in pares]
    print("  COLISIONES INTERNAS, y son SENSIBLES A LA REGLA:")
    for regla in ("prefijo2", "completo"):
        f2 = agrupar(todos, regla)
        m2 = colisiones_internas(f2)
        print("    %-9s %3d familias  %d colisiones"
              % (regla, len(f2), len(m2)))
        for k, v, ns in m2[:3]:
            print("        %s 0x%02X -> %s" % (k, v, ", ".join(ns)))
    print()
    if malas:
        print("  LECTURA: la colision vive en la familia 'S', que la regla")
        print("  prefijo2 llena porque a un nombre de 2 segmentos no le queda")
        print("  segundo token que usar. S_SENDMSG y S_SETVSKIP son tablas")
        print("  DISTINTAS, no dos nombres del mismo opcode. Bajo 'completo'")
        print("  cada uno es su propia familia y la colision desaparece.")
        print("  CONCLUSION: no es ambiguedad de opcode, es artefacto de la")
        print("  regla de agrupacion. No se declara PROVEN_ABSENT de ambiguedad:")
        print("  solo que con estas dos reglas no se observa ninguna.")
    else:
        print("  0 colisiones internas bajo AMBAS reglas.")
    print()
    print("  POR QUE 0x00 NO ES AMBIGUO")
    print("    0x00 aparece en varias tablas porque son tablas DISTINTAS, no")
    print("    porque un valor tenga dos nombres. A la pregunta le falta la")
    print("    dimension 'familia', no le falta el valor.")
    print()
    print("  LO QUE UN PROGRAMA MINIMO NECESITA, y esta aqui:")
    fam2 = agrupar(todos, "prefijo2")
    for want in ("S_LOAD", "S_STORE", "S_CMP", "S_ADD", "S_MOV"):
        pares = fam2.get(want)
        if not pares:
            continue
        d = por_valor(pares)
        print("    %-8s %s" % (want, ", ".join(
            "0x%02X=%s" % (v, d[v]) for v in sorted(d)[:5])))
    print()
    print("  NO es un ensamblador: solo el campo de opcode dentro de la")
    print("  familia. Los operandos y los registros son otra tabla.")
    return 0


def selftest():
    fallos = []
    fam, nom = tabla()
    # (1) caso real: la tabla se lee y tiene contenido
    if not fam:
        fallos.append("no se lee ninguna familia: el extractor no funciona")
    if len(fam) < 20:
        fallos.append("solo %d familias: se espera mas de 20" % len(fam))
    # (2) INVERTIBILIDAD bajo la regla que se afirma. Se exige sobre la regla
    #     'completo', que es la que sostiene la conclusion; 'prefijo2' tiene
    #     una colision conocida y ARTIFACTUAL, y por eso no se exige ahi.
    todos = [par for pares in fam.values() for par in pares]
    if colisiones_internas(agrupar(todos, "completo")):
        fallos.append("hay colisiones dentro de una familia bajo 'completo': "
                      "la tabla NO es invertible y todo el argumento se cae")
    # (3) y el control de que el extractor NO invente ni pierda: cada nombre de
    #     la cabecera tiene que aparecer en la tabla, y la tabla no puede traer
    #     nombres que no esten.
    for f in conservacion(_crudos(), nom):
        fallos.append(f)
    # (4) el path de impresion. Un self-test que solo comprueba datos puede
    #     pasar mientras main() revienta al imprimir. Se ejecuta la rama de
    #     exito REALmente y se exige que devuelva 0.
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main([])
    if rc != 0:
        fallos.append("main([]) devolvio %d en el camino de exito: el "
                      "formateo de la salida esta roto" % rc)
    for exigido in ("TABLA DE OPCODE GFX8 POR FAMILIA", "SENSIBLES A LA REGLA"):
        if exigido not in buf.getvalue():
            fallos.append("la salida no contiene %r: el contrato de salida "
                          "no se cumple" % exigido)
    if fallos:
        print("AUTOTEST FALLA:")
        for f in fallos:
            print("   %s" % f)
        return 1
    print("autotest OK (%d familias, %d nombres, invertibilidad + "
          "path de impresion)" % (len(fam), len(nom)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))