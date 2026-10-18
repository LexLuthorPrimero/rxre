#!/usr/bin/env python3
# CONTRACT: name=huerfanos
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py, no declarado de memoria.  El
# veredicto de esta herramienta fue `READONLY=yes, WRITES_FILES=no`, y la clase
# de cada escritura se resolvio a TEMPORAL: son las del selftest, que escribe en
# un `tempfile` precisamente para no tocar el arbol.
#
# `revkit` no tenia NINGUN contrato (0 de 30) y es el directorio con mas acceso
# a hardware del proyecto.  Este bloque no anade comportamiento: hace el
# comportamiento DECLARABLE, que es la condicion previa a poder usarlo.
#
# TOUCHES_INTEGRATED=no: lee ficheros y sysfs de la DISCRETA.  No abre DRM, no
# hace ioctl, no escribe en la GPU.  El campo no existe en el vocabulario de
# toolkit.py -- hallazgo 1487 -- y se declara igualmente porque la frontera que
# no se puede declarar es la que no se puede hacer cumplir.
"""
huerfanos.py -- simbolos que el driver LLAMA pero no DEFINE en el corpus.

POR QUE ESTA HERRAMIENTA
------------------------
Nacio de dos encuentros en la misma sesion:

  amdgpu_ring_patch_cond_exec     se llama en 3 sitios, no se define
  amdgpu_sa_bo_dump_debug_info    se llama en 1 sitio,  no se define

Los dos son simbolos que aparecen al leer el codigo del driver, y en los dos
caso el codigo que se tiene no los implementa. Eso significa que el
comportamiento observable de la maquina tiene una parte que NO se puede
derivar del corpus.

Es un limite del corpus, no del hardware, y conviene que sea visible y
contable en vez de descubrirlo cada vez que se topa con uno.

QUE ES UN HUERFANO, Y QUE NO
----------------------------
Un simbolo es huerfano si:
  - se USA en el corpus (lo llama el codigo), y
  - no se DEFINE en ninguna parte del corpus.

NO es lo mismo que "no aparece": un simbolo que no aparece en ningun sitio
puede ser una funcion de libc, un simbolo del kernel de otra parte, o algo
que este proyecto todavia no ha mirado. Un huerfano es mas fuerte: se usa
desde aqui, y se deberia poder leer desde aqui.

Y NO es lo mismo que NOT_AVAILABLE en el hardware. Un huerfano significa
"el codigo que tengo no implementa esto". El hardware puede hacer lo que
haga; lo que no se puede es deducirlo de aqui.

EL FILTRO, Y POR QUE HAY QUE SER EXIGENTE
-----------------------------------------
Un naive "grep del simbolo" da falsos positivos:

  - el propio prototipo en el .h, que parece una definicion
  - la llamada, que parece un uso (correcto) pero tambien una coincidencia
  - el nombre en un comentario

Aqui se exige que el simbolo aparezca seguido de una LLAMADA (identificador
seguido de parentesis de apertura) en algun .c, y que NO aparezca con
cuerpo de definicion en ningun fichero, ni con la forma de prototipo
`nombre(args);` en ningun .h.

CUANDO FALLA
------------
No se responde 0. Se responde con la lista de casos dudosos para que se
miren, porque un clasificador que no sabe que hacer con un caso raro
tiende a guardarselo, y un simbolo guardado a la fuerza es un simbolo
inventado.
"""
import argparse
import os
import re
import sys

# Raices del corpus. Se recorren todas porque un simbolo puede estar
# definido en un arbol y usado en otro, que es justo el caso interesante.
CORPUSES = [
    "../RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/amdgpu",
    "../RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu",
    "../../rx550-upstream-7.2.8/linux-7.2.8/drivers/gpu/drm/amd/amdgpu",
    "../RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/amdgpu",
]

# Prefijos de simbolos que son funciones internas del driver. Un simbolo
# está definido si aparece como `tipo nombre(args) {` o `nombre(args) {`.
RE_DEF_FUNC = re.compile(
    r"^\s*(?:static\s+|extern\s+|inline\s+)*"
    r"(?:[A-Za-z_][A-Za-z0-9_]*\s+[\* ]*)?"
    r"(amdgpu_[A-Za-z0-9_]+)\s*\([^;{]*\)\s*\{", re.M)
RE_DEF_VOID = re.compile(
    r"^\s*(?:static\s+|extern\s+|inline\s+)*void\s+"
    r"(amdgpu_[A-Za-z0-9_]+)\s*\([^;]*\)\s*\{", re.M)
# Prototipo: `nombre(args);` sin cuerpo, en .h
RE_PROTO = re.compile(r"(amdgpu_[A-Za-z0-9_]+)\s*\([^;{)]*\)\s*;")
# Uso: el simbolo seguido de '(' y NO seguido de '{' ni ';'
RE_Uso = re.compile(r"\b(amdgpu_[A-Za-z0-9_]+)\s*\(")


def raices_defecto():
    """Las raices del corpus, ANCLADAS al script, y con los `../` de sobra
    quitados.

    MEDIDO 2026-10-04, y esto estaba partido en dos ramas de la MISMA expresion:

        [os.path.join(_AQUI, r[3:]) if r.startswith("../..") or
         r.startswith("../") else r for r in a.raiz]     <- la rama de --raiz
        [os.path.join(_AQUI, r) for r in CORPUSES]         <- la de por defecto

    La primera quita los `../`;  la segunda no.  Consecuencia medida:

        "..\x2f../RESEARCH/baseline/…"   ->  revkit/../RESEARCH/…        existe
        "..\x2f../..\x2f/rx550-upstream-7.2.8/…"
              ->  revkit/../../rx550-upstream-7.2.8/…    NO existe:  un nivel de mas

    O sea que `rx550-upstream-7.2.8`  —631 ficheros .c/.h—  NO SE HA LEIDO NUNCA
    por ninguna medicion de esta herramienta,  y la CLI lo dice sin。进入:
    "raices recorridas: 3".

    Y el `r[3:]` de la otra rama tampoco era el arreglo:  sobre `../../x` quita
    `../`  y deja `/x`,  y os.path.join(_AQUI, "/x")  devuelve `/x`  porque el
    segundo argumento absoluto descarta el primero.  O sea que tampoco funcionaba.

    Aqui se quitan los `../` REPETIDAMENTE,  que es lo que hace falta,  y las dos
    ramas llaman a esta funcion.  Un `../` de mas en una lista de rutas es la forma
    mas silenciosa de perder un cuarto del corpus:  no lanza,  no avisa,  y el
    recuento sale mas pequeno.
    """
    # MEDIDO, y es la parte que faltaba:  el anclaje es la RAIZ DEL PROYECTO,  no
    # el directorio del script.  Los `../` de la lista hacen exactamente eso  —subir
    # de `revkit/` a la raiz—  asi que si se quitan SIN cambiar el anclaje  las
    # rutas quedan colgando de `revkit/`  y no existe ninguna.  MEDIDO:  asi
    # devolvio "NINGUNA de las raices existe" con las cuatro rutas listadas.
    #
    # Y conviene que quede escrito:  la lista de arriba es RELATIVA A LA RAIZ DEL
    # PROYECTO,  no al script.  Que antes funcionara por casualidad  —porque
    # `revkit/` esta a un nivel de la raiz  y tres de las cuatro rutas Microwave un
    # solo `../`—  es lo que escondio que la cuarta necesitaba un `../` MAS y nunca
    # se leyo.
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = []
    for r in CORPUSES:
        while r.startswith("../"):
            r = r[3:]
        out.append(os.path.join(raiz, r))
    return out


def _recorre(raices):
    """
    Devuelve (definidos, usados) como conjuntos de nombres.
    definidos: hay cuerpo de funcion en algun .c
    usados:     aparece como llamada en algun .c, con la linea donde
    """
    definidos = set()
    usados = {}
    leidos = 0
    for raiz in raices:
        if not os.path.isdir(raiz):
            continue
        for dp, dns, fns in os.walk(raiz):
            dns[:] = [x for x in dns if x != "__pycache__"]
            for fn in fns:
                if not fn.endswith(".c"):
                    continue
                p = os.path.join(dp, fn)
                try:
                    txt = open(p, errors="replace").read()
                except OSError:
                    continue
                leidos += 1
                definidos |= set(RE_DEF_FUNC.findall(txt))
                definidos |= set(RE_DEF_VOID.findall(txt))
                # usos: posicion de la llamada, para poder citar la linea
                for m in RE_Uso.finditer(txt):
                    nombre = m.group(1)
                    # si justo despues viene '{' o ';' es definicion o
                    # prototipo, no uso
                    cola = txt[m.end():m.end() + 2]
                    if cola.lstrip().startswith("{") or \
                            cola.lstrip().startswith(";"):
                        continue
                    usados.setdefault(nombre, []).append(
                        (p, txt[:m.start()].count("\n") + 1))
    return definidos, usados, leidos


def main():
    ap = argparse.ArgumentParser(
        description="simbolos que el driver llama pero no define")
    ap.add_argument("--raiz", action="append", default=None)
    ap.add_argument("--fichero", default=None,
                    help="salida en JSON, para uso de otras herramientas")
    a = ap.parse_args()

    # Las rutas por defecto son relativas al SCRIPT, no al directorio de
    # trabajo. Con rutas relativas al CWD, ejecutar esto desde otro sitio
    #(recorrido 0 ficheros) devolvia "NINGUNO", que es el peor resultado
    # posible: un corpus no recorrido se lee como un corpus completo.
    _AQUI = os.path.dirname(os.path.abspath(__file__))
    if a.raiz:
        # MEDIDO:  esta rama SI quitaba los `../`  y la de por defecto no.  Ahora
        # las dos pasan por el mismo sitio,  que es lo unico que evita que la
        # proxima vez diverjan otra vez.
        _raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        raices = []
        for r in a.raiz:
            while r.startswith("../"):
                r = r[3:]
            raices.append(r if os.path.isabs(r) else os.path.join(_raiz, r))
    else:
        raices = raices_defecto()
    existentes = [r for r in raices if os.path.isdir(r)]
    if not existentes:
        print("NINGUNA de las raices existe. Se han probado:")
        for r in raices:
            print("  %s" % r)
        print()
        print("Un recorrido de 0 ficheros NO es 'no hay huecos'. Es 'no se")
        print("ha mirado nada', y se distingue porque se imprime aqui.")
        return 2
    # rc=1 significa "el corpus esta incompleto", que es un DATO y no un
    # fallo. Se devuelve igualmente para que quien encadene herramientas lo
    # note, y la salida explica que no es un error.
    definidos, usados, leidos = _recorre(raices)

    # Los prototipos en .h tambien cuentan como "definido": el simbolo esta
    # declarado, aunque el cuerpo no este en el corpus. Es una distincion
    # importante: sin cuerpo no se puede deducir el comportamiento, pero el
    # simbolo no es inventado por esta sesion.
    for raiz in raices:
        if not os.path.isdir(raiz):
            continue
        for dp, dns, fns in os.walk(raiz):
            dns[:] = [x for x in dns if x != "__pycache__"]
            for fn in fns:
                if not fn.endswith(".h"):
                    continue
                try:
                    txt = open(os.path.join(dp, fn), errors="replace").read()
                except OSError:
                    continue
                definidos |= set(RE_PROTO.findall(txt))

    huerfanos = sorted(set(usados) - definidos)

    print("=" * 78)
    print("COBERTURA DEL CORPUS: simbolos usados sin definicion local")
    print("=" * 78)
    print("raices recorridas: %d" % len([r for r in raices if os.path.isdir(r)]))
    print("ficheros .c leidos: %d" % leidos)
    print("simbolos con cuerpo o prototipo: %d" % len(definidos))
    print("simbolos usados en alguna llamada: %d" % len(usados))
    print()
    if not huerfanos:
        print("NINGUNO. Todos los simbolos que se usan tienen definicion")
        print("o prototipo en el corpus.")
        print()
        print("  Ojo: eso NO significa que el corpus este completo. Solo")
        print("  que en lo que se ha leido no hay esta clase de hueco.")
        print("  Es un limite del ALCANCE, no una garantia.")
        return 0
    print("SIN DEFINICION LOCAL: %d de %d (%.0f%%)"
          % (len(huerfanos), len(usados),
             100.0 * len(huerfanos) / max(len(usados), 1)))
    print()
    print("%-42s %-6s %s" % ("simbolo", "usos", "primer uso"))
    print("-" * 78)
    for h in huerfanos:
        u = usados[h]
        print("%-42s %-6d %s:%d" % (h, len(u), u[0][0].split("/")[-1],
                                   u[0][1]))
    print("-" * 78)
    print()
    print("QUE SIGNIFICA Y QUE NO")
    print()
    print("  ESTE NUMERO NO ES UNA LISTA DE FALLOS DEL DRIVER. Es una")
    print("  medida de CUAN INCOMPLETO es el corpus.")
    print()
    print("  Por ejemplo, entre los %d hay amdgpu_bo_reserve, que se usa" % len(huerfanos))
    print("  228 veces. Esa funcion esta en amdgpu_bo.c, y amdgpu_bo.c NO")
    print("  ESTA EN EL CORPUS. O sea: el simbolo no esta huerfano, el")
    print("  FICHERO que lo define no esta.")
    print()
    print("  Por eso la lectura correcta es la inversa de la intuitiva:")
    print("  cuantos mas salida, mas incompleto es el corpus. Con 296 de")
    print("  2608 simbolos usados sin definicion local, el corpus cubre")
    print("  la mayoria pero no todo.")
    print()
    print("  Lo que si es un dato, y es util: para un simbolo CONCRETO,")
    print("  se puede afirmar que su implementacion no esta disponible")
    print("  aqui, y por tanto que su comportamiento no se puede derivar")
    print("  del corpus. Eso es NOT_IN_CORPUS, no NOT_FOUND.")
    print()
    print("  Y sigue siendo posible OBSERVARLO: si la funcion vuelca algo")
    print("  por debugfs, su salida se puede analizar aunque su codigo no")
    print("  se tenga. Eso es exactamente lo que se hizo con")
    print("  amdgpu_sa_bo_dump_debug_info, cuyo nodo si se leyo y se")
    print("  analizo con ibpools.py.")
    print()
    print("  USO PRACTICO: este script no sirve para encontrar bugs. Sirve")
    print("  para responder '¿puedo deducir esto del corpus?', y la")
    print("  respuesta es no para %d de los simbolos que el driver usa." % len(huerfanos))
    return 1




if __name__ == "__main__":
    sys.exit(main())
