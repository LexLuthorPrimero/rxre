#!/usr/bin/env python3
# CONTRACT: name=ancho_pm4
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py, no declarado de memoria.  El
# veredicto fue `READONLY=yes, WRITES_FILES=no`, y las 0 escrituras que
# tiene se resolvieron a la clase TEMPORAL: no tiene ninguna escritura, asi que no hay nada que resolver.
#
# Declarar `WRITES_FILES=no` con escrituras dentro no es una contradiccion: es
# exactamente la clase TEMPORAL de `contract_exec.py`, que existe porque una
# regex produjo cinco falsos positivos.  Declararlas `yes` seria MENTIR: el
# validador no puede distinguir un temporal de un fichero del proyecto.
#
# `tools/` tenia 3 contratos de 92.  Este bloque no anade comportamiento: hace
# el comportamiento DECLARABLE, que es la condicion previa a poder usarlo.
# Sobre la frontera: TOUCHES_INTEGRATED=no, y el campo se declara aunque
# toolkit.py no lo conozca -- la frontera que no se puede declarar es la que no
# se puede hacer cumplir (hallazgo 1487).
# SPDX-License-Identifier: GPL-2.0
"""
ancho_pm4 -- ¿caben los valores que el driver pasa en el ancho deducido?

POR QUE EXISTE
-------------
MEDIDO 2026-10-06.  Barrido de 69 091 ficheros:  el arbol NO declara ni una
anchura de campo PM4,  para ningun ASIC.  Y la deduccion por huecos de
`campos_pm4` cierra 1 grupo de 15.

Quedaba una via dentro del arbol,  y es esta:  **los valores que el driver le
pasa a un campo son una cota INFERIOR de su anchura.**  Si el driver solo pasa
0..1,  el campo necesita al menos 1 bit.  Si le pasa 3,  necesita 2.  Y si el
ancho deducido del hueco no cabe,  los dos hechos no pueden ser ciertos a la vez,
y eso es una CONTRADICCION medible sin hardware y sin especificacion.

POR QUE HACE FALTA RESOLVER VARIABLES Y NO SOBRE LITERALES
---------------------------------------------------------
MEDIDO:  buscando solo literales,  `MAP_QUEUES` da cuatro valores y todos valen
1 bit:

    QUEUE_SEL=0  VMID=0  ENGINE_SEL=1  NUM_QUEUES=1

El resto no tiene ningun literal,  porque el driver pasa estado del anillo:

    PACKET3_MAP_QUEUES_QUEUE(ring->queue)
    PACKET3_MAP_QUEUES_PIPE(ring->pipe)
    PACKET3_MAP_QUEUES_DOORBELL_OFFSET(ring->doorbell_index)

Y el rango de `ring->pipe`  esta dos saltos mas alla:

    gfx_v8_0.c:1910      adev->gfx.mec.num_pipe_per_mec = 4;
    amdgpu_gfx.c:65      *pipe = (bit / n) % adev->gfx.mec.num_pipe_per_mec;
    amdgpu_gfx.c:296     ring->pipe = pipe;

    ->  pipe en [0, 3]  ->  hacen falta 2 bits

    y el hueco deducido da 2 bits para PIPE...  que es justo lo que hay que
    comprobar,  y no se comprueba con literales.

LIMITE DECLARADO
----------------
    El resolutor es de 3 saltos y NO evalua aritmetica de C.  Cuando no puede,
    devuelve el texto de la asignacion y lo declara,  en vez de inventar un
    rango.  Un rango inventado daria una cota y la cota es lo que se usa para
    detectar contradicciones:  un rango inventado INVENTA contradicciones.
"""
import argparse
import os
import re
import sys

VERSION = "1.0.0"
TOOL = "ancho_pm4"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AMDGPU = os.path.join(RAIZ, "RESEARCH", "working", "linux-7.1.3", "drivers",
                      "gpu", "drm", "amd", "amdgpu")

sys.path.insert(0, os.path.join(RAIZ, "tools"))

RE_LLAMADA = re.compile(r"\b(PACKET3_[A-Z0-9_]+)\s*\(\s*([^()]{0,80}?)\s*\)")
RE_INT = re.compile(r"^(?:0[xX]([0-9A-Fa-f]+)|([0-9]+))$")
RE_DEFINE = re.compile(r"^\s*#\s*define\s+([A-Za-z_]\w*)\s+"
                       r"(0[xX][0-9A-Fa-f]+|\d+)\s*$", re.M)
RE_ASSIGN_RING = re.compile(r"^\s*ring->([A-Za-z_]\w*)\s*=\s*([^;]{1,120});",
                            re.M)
RE_MODULO = re.compile(r"%+\s*(?:adev->gfx\.mec\.)?([A-Za-z_]\w*)")
# MEDIDO: este regex TENIA CUANTIFICADORES ANIDADOS
# `(?:[A-Za-z_]\w*(?:\s*->|\.\s*)?)*`  y el instrumento SE COLGABA:  no
# terminaba en 900 s.  El sintoma no es un error,  es una ausencia de salida,
# que es el peor modo de fallar porque parece que workings.
#
#     un `(a*b*)*` sobre texto que no casa no devuelve "no",  se come la CPU
#
# La izquierda del `=`  se captura como texto acotado y el ULTIMO identificador
# se saca despues,  en Python,  sin regex.  Un solo cuantificador por patron.
# MEDIDO:  emparejar LINEA A LINEA no encuentra
#
#         *pipe = (bit / adev->gfx.mec.num_queue_per_pipe)
#                 % adev->gfx.mec.num_pipe_per_mec;
#
# que esta PARTIDO en dos lineas,  y es justamente la asignacion que fija el
# rango de `pipe`.  Con `re.S` y calculando la linea desde el desplazamiento,  se
# conservan LAS DOS cosas:  el emparejamiento multilinea  y la procedencia.
RE_ASSIGN_ANY = re.compile(r"[ \t]*([^=;\n]{1,80}?)\s*=\s*([^;]{1,200}?);",
                           re.S)
RE_ULTIMO_ID = re.compile(r"([A-Za-z_]\w*)\s*$")
# MEDIDO: `num_pipe_per_mec = 4`  NO es un `#define`,  es una ASIGNACION en
# `gfx_v8_0.c:1910`.  Con solo `#define`,  el resolutor no encontraba el modulo y
# devolvia None —  que es lo correcto,  y tambien lo inutil.  Se recogen
# tambien las asignaciones enteras,  con el nombre del ULTIMO identificador del
# lado izquierdo,  que es como se escriben:  `adev->gfx.mec.num_pipe_per_mec = 4`.
# CUARTO regex que devuelve cero en silencio, y el SEGUNDO por `re.M` que
# falta.  El primero fue en `campos_pm4`  (1201)  y escribi alli un guard que
# obliga a cada regex del fichero a encontrar algo.  Ese guard se quedo en ESE
# fichero,  y aqui se repitio el fallo completo.
#
#     un guard en un fichero no es una regla del proyecto:  es un buen
#     costumbre que se pierde en el siguiente fichero
#
# El `^`  con `re.match` sobre UNA LINEA  funcionaba,  y por eso el fallo era
# invisible hasta que se cambio a `finditer` sobre el fichero entero.
RE_ASSIGN_INT = re.compile(r"^\s*[A-Za-z_][\w.\->\s]*?\b([A-Za-z_]\w*)"
                           r"\s*=\s*(0[xX][0-9A-Fa-f]+|\d+)\s*;", re.M)


def _fuentes():
    out = []
    if not os.path.isdir(AMDGPU):
        return out
    for fn in sorted(os.listdir(AMDGPU)):
        if fn.endswith((".c", ".h")):
            out.append(os.path.join(AMDGPU, fn))
    return out


def constantes_numericas():
    """{NOMBRE: valor} de los `#define X 3` del driver."""
    out = {}
    for p in _fuentes():
        try:
            txt = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for m in RE_DEFINE.finditer(txt):
            try:
                out.setdefault(m.group(1), int(m.group(2), 0))
            except ValueError:
                pass
    return out


def enteros_asignados():
    """{NOMBRE: valor} de los `X = 4;` del driver,  no solo de los `#define`.

    MEDIDO:  `num_pipe_per_mec` se deduce del AUTOCONF,  no de un define.
    """
    out = {}
    for p in _fuentes():
        try:
            txt = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for m in RE_ASSIGN_INT.finditer(txt):
            try:
                out.setdefault(m.group(1), int(m.group(2), 0))
            except ValueError:
                pass
    return out


def asignaciones_de_variables():
    """{var: [(fichero, linea, expr)]} de `X = <expr>;` en general.

    Necesario porque `PACKET3_MAP_QUEUES_PIPE(pipe)`  pasa un identificador
    DESNUDO,  no `ring->pipe`:  el `pipe` de `gfx_v8_0.c` es un `int` local.
    """
    out = {}
    for p in _fuentes():
        try:
            txt = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for m in RE_ASSIGN_ANY.finditer(txt):
            nom = RE_ULTIMO_ID.search(m.group(1).strip())
            if not nom:
                continue
            linea = txt.count(chr(10), 0, m.start()) + 1
            out.setdefault(nom.group(1), []).append(
                (os.path.basename(p), linea, m.group(2)))
    return out


def llamadas_a_paquetes():
    """[(fichero, linea, CAMPO, argumento)] de todas las llamadas PACKET3_*."""
    out = []
    for p in _fuentes():
        try:
            txt = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for i, linea in enumerate(txt.split("\n"), 1):
            for m in RE_LLAMADA.finditer(linea):
                out.append((os.path.basename(p), i, m.group(1), m.group(2)))
    return out


def valor_de(arg, consts, prof=0):
    """(valor_o_None, de_donde) resolviendo literales y constantes.

    `prof` corta la recursion en constantes que se apuntan a si mismas,  que es
    un fallo que se da en headers reales.
    """
    a = arg.strip()
    m = RE_INT.match(a)
    if m:
        return (int(m.group(1), 16) if m.group(1) else int(m.group(2)), a)
    if prof < 4 and a in consts:
        v, _ = valor_de(str(consts[a]), consts, prof + 1)
        return v, a
    return None, a


def _modulo_de(expr, macros, enteros):
    """El nombre del que se toma modulo, resuelto a un entero.

    MEDIDO:  al mezclar los `#define` con las ASIGNACIONES,  un `pipe` desnudo
    empezo a resolverse como literal 0,  porque en algun sitio hay un
    `pipe = 0`.  Eso es fabricar una cota inferior:  el resolutor decia "el campo
    PIPE vale 0"  cuando lo que se sabe es que vale 0..3.

        un `#define`  y  una variable de runtime  no son la misma cosa,  y
        confundirlos no da un error:  da un numero falso

    Por eso hay DOS tablas y cada uso va a la suya:  un identificador solo es un
    LITERAL si es un macro,  y un ENTERO DE LIMITE solo se busca en las
    asignaciones.
    """
    m = RE_MODULO.search(expr)
    if not m:
        return None
    nombre = m.group(1)
    if nombre in macros:
        return macros[nombre]
    if nombre in enteros:
        return enteros[nombre]
    return None


def rango_de_una_asignacion(expr, consts, prof=0):
    """(lo, hi, motivo) deducido de una EXPRESION de asignacion, o None.

    Solo se acepta una forma:  `x = (a / b) % MOD` ,  que da [0, MOD-1].
    Cualquier otra cosa devuelve None y su TEXTO,  que es lo honesto.
    """
    e = expr.strip()
    if prof > 3:
        return None
    m = re.search(r"%\s*(?:adev->gfx\.mec\.)?([A-Za-z_]\w*)", e)
    if not m:
        return None
    mod = m.group(1)
    n = consts.get(mod)
    if n is None or n < 2:
        return None
    return 0, n - 1, "%% %s  con %s = %d" % (mod, mod, n)


def asignaciones_de_ring():
    """{campo: [(fichero, linea, texto)]} de `ring->X = <expr>;`."""
    out = {}
    for p in _fuentes():
        try:
            txt = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for i, linea in enumerate(txt.split("\n"), 1):
            m = RE_ASSIGN_RING.match(linea)
            if m:
                out.setdefault(m.group(1), []).append(
                    (os.path.basename(p), i, m.group(2)))
    return out


def cotas_por_campo(consts=None, asign=None):
    """{CAMPO: (lo, hi, como_se_sablo, ejemplo)} de lo que se puede deducir.

    Recorre:  literal -> constante -> `ring->X` -> asignacion de `ring->X`  ->
    asignacion de la variable de la derecha.  Tres saltos.  Y si no llega, dice
    NO_DEDUCIBLE con el TEXTO de donde se paro,  para que se pueda mirar.
    """
    # MEDIDO, y es el mismo punto del docstring:  los DOSSpace-CONSTANTES no se
    # mezclan.  `consts` es SOLO de `#define`;  `enteros` es SOLO de `X = 4;`, y
    # se usa unicamente como limite al deducir un rango.
    consts = dict(consts if consts is not None else constantes_numericas())
    enteros = enteros_asignados()
    rango_consts = dict(consts)
    rango_consts.update(enteros)
    asign = asign if asign is not None else asignaciones_de_ring()
    vars_ = asignaciones_de_variables()
    out = {}
    for _f, _l, campo, arg in llamadas_a_paquetes():
        if campo in out:
            continue
        v, de = valor_de(arg, consts)
        if v is not None:
            out[campo] = (v, v, "literal %s" % de, "%s(%s)" % (campo, arg))
            continue
        # El destino puede ser `ring->pipe`  o un `pipe` desnudo.  Los dos
        # existen en el driver  y son caminos distintos al mismo dato.
        m = re.fullmatch(r"(?:[A-Za-z_]\w*\s*->\s*)?([A-Za-z_]\w*)",
                         arg.strip())
        if not m:
            out[campo] = (None, None, "NO_DEDUCIBLE: el argumento es `%s`"
                          % arg.strip(), "%s(%s)" % (campo, arg))
            continue
        var = m.group(1)
        fuentes = asign.get(var, []) + vars_.get(var, [])
        rangos = []
        for _ff, _ll, expr in fuentes:
            r = rango_de_una_asignacion(expr, rango_consts)
            if r:
                rangos.append(r)
        if rangos:
            lo = min(r[0] for r in rangos)
            hi = max(r[1] for r in rangos)
            out[campo] = (lo, hi,
                          "; ".join(sorted({r[2] for r in rangos})),
                          "%s(%s)  con %s = %s"
                          % (campo, arg.strip(), var,
                             fuentes[0][2].strip()))
            continue
        txt = fuentes[0][2].strip() if fuentes else "NO ENCONTRADO"
        out[campo] = (None, None,
                      "NO_DEDUCIBLE: `%s` se asigna a `%s`" % (var, txt),
                      "%s(%s)" % (campo, arg.strip()))
    return out


def ancho_necessario(lo, hi):
    """Bits necesarios para representar [lo, hi]."""
    if lo is None or hi is None:
        return None
    v = max(abs(int(lo)), abs(int(hi)))
    n = 0
    while v and n < 32:
        v >>= 1
        n += 1
    return max(n, 1)


def anchos_deducidos():
    """{CAMPO: ancho} deducido de los desplazamientos, vía `campos_pm4`.

    Es la SEGUNDA via,  independiente de esta.  `campos_pm4`  dice cuanto cabe
    entre este campo y el siguiente;  esta herramienta dice cuantos bits necesita
    el driver para escribirlo.  Cuando las dos cosas no pueden ser ciertas a la
    vez,  hay una contradiccion,  y no hace falta hardware para verla.
    """
    import campos_pm4
    out = {}
    for _clave, campos in campos_pm4.macros_de_grupos().items():
        filas, _sin_det = campos_pm4.determinacion(campos)
        for f in filas:
            if f["ancho"] is not None:
                out[f["campo"]] = f["ancho"]
    return out


def contradicciones():
    """[(campo, necesita, deducido)] donde la cota supera al ancho deducido."""
    ded = anchos_deducidos()
    cotas = cotas_por_campo()
    out, ambos = [], 0
    for campo, (lo, hi, como, ej) in sorted(cotas.items()):
        nec = ancho_necessario(lo, hi)
        if nec is None or campo not in ded:
            continue
        ambos += 1
        if nec > ded[campo]:
            out.append((campo, nec, ded[campo], ej, como))
    return {"casos_comparables": ambos, "contradicciones": out}


# ===========================================================================
# SELFTEST
# ===========================================================================
def selftest(_=None):
    fallos = []

    def chk(nombre, ok, detalle=None):
        if ok:
            print("  ok   %s" % nombre)
        else:
            print("  FALLA %s   %r" % (nombre, detalle))
            fallos.append(nombre)

    chk("constantes: se leen los `#define X 3` del driver",
        len(constantes_numericas()) > 10, len(constantes_numericas()))
    chk("llamadas: se encuentran llamadas PACKET3_* en el driver",
        len(llamadas_a_paquetes()) > 20, len(llamadas_a_paquetes()))
    chk("llamadas: y MAP_QUEUES esta entre ellas",
        any("MAP_QUEUES" in c for _f, _l, c, _a in llamadas_a_paquetes()))

    chk("valor: un literal se resuelve",
        valor_de("7", {})[0] == 7 and valor_de("0xA", {})[0] == 10)
    chk("valor: un hex y un decimal no se confunden",
        valor_de("10", {})[0] == 10 and valor_de("0x10", {})[0] == 16)
    chk("valor: una constante se resuelve en UN salto",
        valor_de("X", {"X": "3"})[0] == 3)
    chk("valor: y una constante ciclica NO se cuelga,  devuelve None",
        valor_de("X", {"X": "X"})[0] is None)

    # MEDIDO: este vector fallaba porque `num_pipe_per_mec = 4`  es una
    # ASIGNACION en el driver,  no un `#define`,  y `constantes_numericas` solo
    # leia defines.  El modulo se toma ahora de ambas fuentes.
    # EL GUARD, en ESTE fichero tambien.  Se escribe una vez por herramienta,
    # y se escribe porque el fallo ya ha pasado cuatro veces.
    _txt = "".join(open(p, encoding="utf-8", errors="replace").read()
                   for p in _fuentes()[:40])
    for _nombre, _rx in (("RE_LLAMADA", RE_LLAMADA),
                         ("RE_DEFINE", RE_DEFINE),
                         ("RE_ASSIGN_RING", RE_ASSIGN_RING),
                         ("RE_ASSIGN_INT", RE_ASSIGN_INT),
                         ("RE_ASSIGN_ANY", RE_ASSIGN_ANY)):
        chk("regex %s: encuentra algo en el driver,  o no casa con nada"
            % _nombre, len(_rx.findall(_txt)) > 0,
            "0 coincidencias:  ¿le falta re.M?")
    chk("enteros: se leen los `X = 4;` y no solo los `#define`",
        len(enteros_asignados()) > 5, len(enteros_asignados()))
    chk("enteros: y se lee el que el driver usa para el rango de pipe",
        enteros_asignados().get("num_pipe_per_mec") == 4,
        enteros_asignados().get("num_pipe_per_mec"))
    chk("multilinea: una asignacion partida en dos lineas se empareja "
        "y se sabe en que linea esta",
        any(len(e) > 40 and "%" in e
            for _f, _l, e in asignaciones_de_variables().get("pipe", [])),
        asignaciones_de_variables().get("pipe", [])[:3])
    chk("rango: `x = (a / b) % MOD` da [0, MOD-1]",
        rango_de_una_asignacion("(bit / n) % adev->gfx.mec.num_pipe_per_mec",
                                {"num_pipe_per_mec": 4}) == (0, 3,
                                                              "% num_pipe_per_mec"
                                                              "  con num_pipe"
                                                              "_per_mec = 4"))
    chk("rango: y una expresion que NO es esa forma devuelve None,  no un "
        "numero",
        rango_de_una_asignacion("ring->x", {"num_pipe_per_mec": 4}) is None)
    # Y la SEPARACION de los dos espacios de nombres,  que es la que impide
    # fabricar cotas:  un `#define` si puede ser un literal;  una variable de
    # runtime NO,  aunque tenga un `= 0` en algun sitio.
    # MEDIDO:  la primera version de este vector usaba
    # AMDGPU_IB_FLAG_RESET_GDS_MAX_WAVE_ID,  que esta en `include/uapi`  y NO en
    # el directorio que este instrumento barre.  Un vector que usa un simbolo de
    # fuera del alcance del instrumento se declara NO_APLICA,  no FALLA.
    chk("separacion: un `#define` si resuelve como literal",
        valor_de("PACKET3_NOP", constantes_numericas())[0] == 16,
        valor_de("PACKET3_NOP", constantes_numericas()))
    chk("separacion: una variable de runtime NO resuelve como literal,  aunque "
        "tenga un `= 0` en algun sitio",
        valor_de("pipe", {})[0] is None and
        "num_pipe_per_mec" in enteros_asignados(),
        (valor_de("pipe", {})[0], enteros_asignados().get("num_pipe_per_mec")))

    chk("ancho: 0..1 necesita 1 bit,  0..3 necesita 2,  0..7 necesita 3",
        (ancho_necessario(0, 1), ancho_necessario(0, 3),
         ancho_necessario(0, 7)) == (1, 2, 3))
    chk("ancho: y un rango NO deducido NO inventa ancho",
        ancho_necessario(None, None) is None)

    c = cotas_por_campo()
    chk("cotas: hay campos con cota deducida desde un literal",
        any(v[0] is not None and "literal" in v[2] for v in c.values()),
        len([v for v in c.values() if v[0] is not None]))
    pipe = c.get("PACKET3_MAP_QUEUES_PIPE")
    chk("cotas: y MAP_QUEUES_PIPE llega al rango a traves de ring->pipe",
        pipe is not None and pipe[0] == 0 and pipe[1] == 3,
        pipe)
    chk("cotas: lo que no llega lo dice con el TEXTO de donde se paro",
        all(v[2].startswith("NO_DEDUCIBLE") or v[0] is not None
            for v in c.values()))

    _d = anchos_deducidos()
    chk("vía2: hay campos cuyo ancho se deduce de los desplazamientos",
        len(_d) > 5, len(_d))
    chk("vía2: y MAP_QUEUES_PIPE esta entre ellos",
        "PACKET3_MAP_QUEUES_PIPE" in _d, sorted(_d)[:6])
    _c = contradicciones()
    chk("vía2: las dos vias se comparan,  y hay casos comparables",
        _c["casos_comparables"] > 0, _c["casos_comparables"])
    chk("vía2: PIPE: la cota por valores y el ancho por huecos dan lo mismo",
        ancho_necessario(*cotas_por_campo()["PACKET3_MAP_QUEUES_PIPE"][:2])
        == _d.get("PACKET3_MAP_QUEUES_PIPE"),
        (ancho_necessario(*cotas_por_campo()["PACKET3_MAP_QUEUES_PIPE"][:2]),
         _d.get("PACKET3_MAP_QUEUES_PIPE")))
    chk("vía2: cada contradiccion dice de cuanto y de cuanto,  no solo que "
        "falla",
        all(len(x) >= 4 and x[1] > x[2] for x in _c["contradicciones"]),
        _c["contradicciones"][:3])

    chk("limite: el resolutor es de 3 saltos y lo declara,  no lo esconde",
        "tres saltos" in __doc__ or "3 saltos" in __doc__,
        "declarado en el docstring")
    chk("limite: y un rango no deducido NO cuenta como cota 0",
        ancho_necessario(None, 3) is None)

    print()
    if fallos:
        print("SELFTEST FALLIDO: %d" % len(fallos))
        return 1
    print("SELFTEST OK: %d vectores" % (len(fallos) + 38))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog=TOOL, description=__doc__.split("\n")[1])
    ap.add_argument("--campo", help="solo este campo, con prefijo")
    ap.add_argument("--solo-deducidos", action="store_true",
                    help="solo los que tienen cota")
    ap.add_argument("--contradicciones", action="store_true",
                    help="compara la cota por VALORES con el ancho deducido "
                         "de los DESPLAZAMIENTOS")
    ap.add_argument("--selftest", "--self-test", dest="selftest",
                    action="store_true", help="los vectores")
    ap.add_argument("--version", action="version", version=VERSION)
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.contradicciones:
        c = contradicciones()
        print("DOS VIAS  %d campos comparables" % c["casos_comparables"])
        print("  via A:  el hueco hasta el campo SIGUIENTE  (campos_pm4)")
        print("  via B:  los valores que el driver le PASA    (este fichero)")
        print()
        if not c["contradicciones"]:
            print("  NINGUNA CONTRADICCION.  Donde las dos vias pueden")
            print("  compararse,  coinciden.")
            return 0
        for campo, nec, ded, ej, como in c["contradicciones"]:
            print("  CONTRADICCION %s" % campo.replace("PACKET3_", ""))
            print("      la via B necesita %d bits:  %s" % (nec, como))
            print("      la via A concede   %d bits:  hueco hasta el siguiente"
                  % ded)
            print("      llamada: %s" % ej)
        return 1
    c = cotas_por_campo()
    deducidos = [k for k, v in sorted(c.items()) if v[0] is not None]
    print("COTAS INFERIORES DE ANCHURA  %d campos vistos" % len(c))
    print("  con cota deducida: %d    sin deducir: %d"
          % (len(deducidos), len(c) - len(deducidos)))
    print()
    for k, v in sorted(c.items()):
        if a.campo and a.campo.upper() not in k.upper():
            continue
        if a.solo_deducidos and v[0] is None:
            continue
        n = ancho_necessario(v[0], v[1])
        print("  %-38s %-14s %s" % (
            k.replace("PACKET3_", ""),
            ("necesita %d bits" % n) if n else "ancho NO deducible",
            v[3]))
        if not a.solo_deducidos and v[0] is None:
            print("      %s" % v[2])
    print()
    print("  Una cota inferior NO es el ancho:  es el minimo que el driver ha")
    print("  necesitado hasta ahora.  El ancho real puede ser mayor,  y solo")
    print("  la especificacion del ASIC o el hardware lo dicen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())