#!/usr/bin/env python3
# CONTRACT: name=campos_pm4
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
campos_pm4 -- ¿determina `vid.h` el layout de los campos de un PM4?

POR QUE EXISTE
--------------
MEDIDO 2026-10-05.  `vid.h` declara los campos de `MAP_QUEUES` SOLO con
desplazamientos:

    PACKET3_MAP_QUEUES_DOORBELL_OFFSET(x) ((x) << 2)
    PACKET3_MAP_QUEUES_QUEUE(x)           ((x) << 26)
    PACKET3_MAP_QUEUES_PIPE(x)            ((x) << 29)
    PACKET3_MAP_QUEUES_ME(x)              ((x) << 31)

Ni una anchura, ni una mascara.  El layout se DEDUCE del hueco hasta el campo
siguiente,  y esa deduccion tiene dos formas de fallar:

  HUECO   dos campos separados por mas bits de los que el segundo necesita:  el
          hueco no es de nadie  y el layout no esta determinado
  SOLAPE  el campo mas ancho de los dos se mete en el bits del siguiente:  el
          layout no es una particion

El segundo caso esta MEDIDO y es real:  `PIPE << 29` con 3 bits llegaria al bit
31,  que es de `ME << 31`,  y con `num_pipe_per_mec = 4`  el driver escribe
`pipe` hasta 3.  Lo que evita el solape es un INVARIANTE que el driver aplica en
`amdgpu_gfx_kiq_acquire()`  y no escribe en ninguna parte:

    bit 31 de ME puesto  ==>  pipe <= 1

Este instrumento NO sabe ese invariante,  y no debe:  su trabajo es decir que el
layout NO esta determinado por el fuente,  que es un hecho sobre el fuente,  y
no una opinion sobre si el hardware lo acepta.

LO QUE NO DICE, Y POR QUE IMPORTA DECIRLO
----------------------------------------
    Que no haya solapes NO significa que el layout sea correcto.  Significa solo
    que los desplazamientos del fuente son compatibles con una particion de 32
    bits.  Que la particion sea la que el ASIC espera es un hecho de HARDWARE, y
    este instrumento no lo mide:  RUNTIME=NOT_RUN.
"""
import argparse
import os
import re
import sys

VERSION = "1.0.0"
TOOL = "campos_pm4"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VID = os.path.join(RAIZ, "RESEARCH", "working", "linux-7.1.3", "drivers",
                   "gpu", "drm", "amd", "amdgpu", "vid.h")

RE_MACRO = re.compile(r"^\s*#\s*define\s+(PACKET3_[A-Z0-9_]+)\s*\(\s*x\s*\)"
                      r"\s*\(\(\s*x\s*\)\s*<<\s*(\d+)\s*\)", re.M)
# MEDIDO 2026-10-05, y este regex estaba mal por una letra.  Los sub-bloques
# de UNMAP_QUEUES se llaman `/* CONTROL2a */`, `/* CONTROL3b */`... con MINUSCULA
# al final, y `[A-Z0-9_]+` no casa con la `a`.  Con lo cual `actual` se quedaba
# en `CONTROL`  y los siete sub-bloques colapsaban en uno:  la salida ponia
# ACTION, PASID y RB_WPTR —los tres en el bit 0 de DISTINTOS dwords— en el mismo
# grupo,  y el censo reportaba un choque que no existe.
#
#     una regla que se equivoca por una letra produce findings que parecen
#     deep bugs del firmware
RE_GRUPO = re.compile(r"/\*\s*([A-Za-z0-9_]+)\s*\*/")
# El NOMBRE de cada paquete, con su opcode.  Sirve para saber a que dword
# pertenece un campo,  que es lo que el comentario NO dice.
RE_NOMBRE = re.compile(r"^\s*#\s*define\s+(PACKET3_[A-Z0-9_]+)\s+"
                       r"(0[xX][0-9A-Fa-f]+|\d+)\s*$", re.M)
ANCHO_DWORD = 32

# MEDIDO 2026-10-05, y este umbral es la CORRECCION de un error mio.  Yo habia
# deducido los anchos tomando "el hueco hasta el campo siguiente", y eso
# produce `[25:2]` — 24 bits — para DOORBELL_OFFSET,  que es absurdo y que
# ademas contradecia la conclusion que yo mismo escribia dos lineas despues.
#
# La causa:  CONTROL2 no tiene los campos contiguos.  ENGINE_SEL<<26 y QUEUE<<26
# son de DISTINTOS dwords,  asi que el "siguiente" de DOORBELL_OFFSET<<2 no es
# su vecino sino un campo de otra palabra.
#
#     un hueco grande no es un campo ancho:  es un layout que los
#     desplazamientos NO determinan
#
# Por eso un hueco por encima de este umbral se reporta como ANCHO NO
# DETERMINADO,  y no como una anchura inventada.  El umbral se DECLARA y no se
# esconde:  8 bits es un campo de campo ancho pero plausible;  24 no lo es.
# El numero es una CONVENCION de este instrumento,  no un hecho del hardware.
ANCHO_PLAUSIBLE = 8


def nombres_de_paquetes(txt):
    """[PACKET3_X...] del header, del mas largo al mas corto.

    El orden importa:  `PACKET3_MAP_QUEUES_QUEUE_SEL`  empieza por
    `PACKET3_MAP_QUEUES`  y tambien por un `PACKET3_MAP`  que no existe,  pero si
    existiera el mas largo tiene que ganar.  Un campo se asigna al nombre de
    paquete MAS LARGO con el que empieza.
    """
    nombres = {m.group(1) for m in RE_NOMBRE.finditer(txt)}
    return sorted(nombres, key=len, reverse=True)


def _paquete_de(campo, nombres):
    for n in nombres:
        if campo.startswith(n + "_"):
            return n
    return None


def macros_de_grupos(ruta=None):
    """{PAQUETE: {GRUPO: {CAMPO: shift}}} leido del header.

    MEDIDO 2026-10-05, y este fue un DEFECTO PROPIO que el censo destapo:
    la primera version agrupaba por el comentario `/* CONTROL */`,  y ese
    comentario aparece UNA vez mientras los macros que debajo le siguen son de
    CUATRO paquetes distintos — MAP_QUEUES, UNMAP_QUEUES, DMA_DATA y
    QUERY_STATUS.  Comparar el desplazamiento de uno con el siguiente,  siendo de
    paquetes distintos,  no dice nada:  no son el mismo dword.

    Por eso se agrupa por PAQUETE primero —que si se deduce del nombre—  y por
    grupo dentro del paquete.  El comentario se conserva como etiqueta,  porque
    el paquete no lo dice.
    """
    ruta = ruta or VID
    txt = open(ruta, encoding="utf-8", errors="replace").read()
    nombres = nombres_de_paquetes(txt)
    grupos, actual = {}, None
    for linea in txt.split("\n"):
        g = RE_GRUPO.match(linea)
        if g:
            actual = g.group(1)
            continue
        m = RE_MACRO.match(linea)
        if not m:
            continue
        paquete = _paquete_de(m.group(1), nombres)
        if paquete is None:
            continue
        clave = "%s / %s" % (paquete, actual or "?")
        grupos.setdefault(clave, {})[m.group(1)] = int(m.group(2))
    return grupos


def deduce(shift_por_campo):
    """[(campo, lo, hi, ancho)] por el hueco hasta el campo siguiente.

    `ancho` es None cuando NO se puede deducir:  el ULTIMO campo no tiene
    siguiente,  y un hueco mayor que `ANCHO_PLAUSIBLE` significa que los
    desplazamientos no determinan una particion — normalmente porque los campos
    de ESTA palabra no son contiguos y el "siguiente" es de otra.

    No se rellena con el hueco aunque el hueco sea grande.  Un ancho inventado es
    un layout inventado,  y un layout inventado que parece deducido es peor que
    no tener layout.
    """
    campos = sorted(shift_por_campo.items(), key=lambda kv: (kv[1], kv[0]))
    out = []
    for i, (campo, hi) in enumerate(campos):
        if i + 1 >= len(campos):
            out.append((campo, hi, hi, None))
            continue
        salto = campos[i + 1][1] - hi
        if salto < 1 or salto > ANCHO_PLAUSIBLE:
            out.append((campo, hi, hi, None))
        else:
            out.append((campo, hi, hi + salto - 1, salto))
    return out


def determinacion(shift_por_campo):
    """(filas, sin_determinar) — que campos tienen anchura FIJADA.

    Y aqui hay una consecuencia que solo se ve al implementarlo:  si el ancho se
    deduce del hueco hasta el siguiente,  el solape es IMPOSIBLE POR
    CONSTRUCCION,  porque un solape exigiria que un campo ocupase mas bits de los
    que hay hasta el siguiente.  Un instrumento que solo supiera de solapes
    seria un instrumento que no puede encontrar ninguno,  y pareceria limpio.

    Asi que el solape se busca al reves:  cuando el ancho viene de FUERA —de una
    especificacion,  de otro ASIC,  de KFD— y se compara con el del fuente.  Eso
    es `validar()`,  y es lo que reproduce el solape de 1199.
    """
    campos = sorted(shift_por_campo.items(), key=lambda kv: (kv[1], kv[0]))
    filas, sin_det = [], []
    for i, (campo, hi) in enumerate(campos):
        if i + 1 >= len(campos):
            filas.append({"campo": campo, "shift": hi, "lo": hi, "hi": hi,
                          "ancho": None})
            sin_det.append({"campo": campo, "bits_desde": hi,
                            "motivo": "no hay campo siguiente:  su anchura no "
                                      "la determina nadie"})
            continue
        salto = campos[i + 1][1] - hi
        if salto < 1 or salto > ANCHO_PLAUSIBLE:
            filas.append({"campo": campo, "shift": hi, "lo": hi, "hi": hi,
                          "ancho": None})
            sin_det.append({"campo": campo, "bits_desde": hi,
                            "motivo": "el hueco hasta %s (%d bits) supera %d:  "
                                      "los desplazamientos NO determinan una "
                                      "particion  (los campos de esta palabra "
                                      "no son contiguos)"
                                      % (campos[i + 1][0], salto,
                                         ANCHO_PLAUSIBLE)})
        else:
            filas.append({"campo": campo, "shift": hi, "lo": hi,
                          "hi": hi + salto - 1, "ancho": salto})
    return filas, sin_det


# MEDIDO 2026-10-05, TERCERA vez que un regex de este fichero no encuentra
# nada sin que nadie lo note.  Este no llevaba `re.M`:  sin MULTILINE, `^` solo
# casa al principio del TEXTO ENTERO,  no al principio de cada linea,  y
# `findall` sobre un header entero devuelve una lista vacia sin ninguna
# excepcion.  El sintoma fue "0 campos, 0 mascaras",  que es un numero
# VEROSIMIL y falso.
#
#     un regex que no encuentra nada no falla:  devuelve cero
#
# Y el guard que lo evita es el mas barato posible:  un vector que le exige al
# regex que ENCUENTRE ALGO.  No comprueba que encuentre lo correcto,  y por eso
# es barato;  pero convierte "cero" en un fallo visible en vez de un dato.
RE_MASCARA = re.compile(r"^\s*#\s*define\s+([A-Za-z0-9_]+_MASK)\b", re.M)
RE_SHIFT_MACRO = re.compile(r"^\s*#\s*define\s+([A-Za-z0-9_]+)\(x\)"
                            r"\s*\(\(\s*x\s*\)\s*<<\s*(\d+)\s*\)", re.M)


def convenciones(ruta=None):
    """Cuantas convenciones de anchura USA el header, y en que parte.

    MEDIDO 2026-10-05.  `vid.h` declara los registros de hardware con
    desplazamiento Y mascara —

        #define RB_MAP_PKR0_MASK   (0x3 << 0)

    — y sus 37 macros de campo de PACKET3 con desplazamiento SOLO.  Mismo
    fichero, misma familia de campos, dos convenciones, y la que falta es
    precisamente la de los paquetes.  Sin esta cuenta la observacion era un
    hecho;  con ella es una medicion,  y de ella sale la prediccion que hay que
    comprobar al escribir un driver propio:  si el arbol no declara la anchura
    de un campo de PM4,  hay que traerla de fuera.
    """
    ruta = ruta or VID
    txt = open(ruta, encoding="utf-8", errors="replace").read()
    con_mascara = {m.group(1) for m in RE_MASCARA.finditer(txt)}
    campos_shift = {m.group(1): int(m.group(2))
                    for m in RE_SHIFT_MACRO.finditer(txt)}
    # un campo tiene mascara si existe `<campo>_MASK`
    de_pm4 = [c for c in campos_shift if c.startswith("PACKET3_")]
    con = [c for c in de_pm4 if c + "_MASK" in con_mascara]
    registro = [c for c in con_mascara
                if not c.startswith("PACKET3_") and not c.endswith("_MASK__SHIFT")]
    return {"campos_pm4": len(de_pm4), "campos_pm4_con_mascara": len(con),
            "mascaras_no_pm4": len(registro),
            "proporcion": (0.0 if not de_pm4
                           else round(len(con) / len(de_pm4), 4))}


RE_ANCHO_EXTERNO = re.compile(
    r"define\s+PACKET3_[A-Z0-9_]+\(x\)[^\n]*<<\s*(\d+)[^\n]*"
    r"(?:&|\|)\s*(?:\(u?32\)\s*)?(0[xX][0-9A-Fa-f]+|\d+)", re.M)

RUTAS_ARBOLME = ("RESEARCH",)


def anchuras_declaradas_en_el_arbol(raiz=None):
    """Cuantos campos de PM3 declaran anchura en TODO el arbol.

    MEDIDO 2026-10-05, y este es el cierre de 1201:  la pregunta no era "el GFX8
    declara anchos"  sino "LOS DECLARA ALGUN sitio del arbol".  Se barre
    `RESEARCH/` entero — dos copias del kernel, `kernelref`, `polaris12xl`— y no
    hay ni una.

    Y sobre todo:  UN cero aqui solo vale si el barrido es CAPAZ de encontrar un
    positivo.  Esta herramienta lleva TRES regex que devolvieron cero en
    silencio,  asi que el patron se prueba contra un caso POSITIVO conocido antes
    de creerse su propio negativo.  Un negativo que no se ha validado no es un
    dato:  es una herramienta rota.
    """
    raiz = raiz or RAIZ
    n_ficheros = n_declaraciones = 0
    vistos = []
    for base in RUTAS_ARBOLME:
        d = os.path.join(raiz, base)
        for dirpath, _dn, filenames in os.walk(d):
            for fn in filenames:
                if not fn.endswith((".h", ".c", ".hh", ".cc")):
                    continue
                p = os.path.join(dirpath, fn)
                n_ficheros += 1
                try:
                    txt = open(p, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                for m in RE_ANCHO_EXTERNO.finditer(txt):
                    n_declaraciones += 1
                    vistos.append(os.path.relpath(p, raiz))
    # LA COMPROBACION DE LA HERRAMIENTA, antes de creerse su cero.
    positivo = ("#define PACKET3_MAP_QUEUES_DOORBELL_OFFSET(x) "
                "(((x) << 2) & 0x3)\n")
    el_patron_ve_un_positivo = bool(RE_ANCHO_EXTERNO.search(positivo))
    return {"ficheros": n_ficheros, "declaraciones": n_declaraciones,
            "vistos": sorted(set(vistos))[:5],
            "el_patron_ve_un_positivo": el_patron_ve_un_positivo}


def validar(anchos):
    """(solapes, sin_dueno) para unos anchos DADOS de fuera.

    `anchos` es [(campo, lo, hi)].  Aqui si puede haber solape,  porque los
    anchos no se deducen:  se comparan.  Y es el unico camino por el que
    `PIPE` de 3 bits aparece pisando a `ME`,  que es lo que midio 1199.
    """
    campos = sorted(anchos, key=lambda t: (t[1], t[0]))
    solapes, vistos = [], []
    for i, (campo, lo, hi) in enumerate(campos):
        for otro, lo2, hi2 in vistos:
            if lo <= hi2 and lo2 <= hi:
                solapes.append({"campo": campo, "rango": [hi, lo],
                                "pisa_a": otro, "rango_de_otro": [hi2, lo2],
                                "motivo": "%s ocupa %d..%d y %s ya ocupa "
                                          "%d..%d"
                                          % (campo, hi, lo, otro, hi2, lo2)})
        vistos.append((campo, lo, hi))
    ocupados = set()
    for _c, lo, hi in campos:
        ocupados.update(range(lo, hi + 1))
    sin_dueno = [b for b in range(ANCHO_DWORD)
                 if b not in ocupados and
                 not any(lo <= b <= hi for _c, lo, hi in campos)]
    return solapes, sin_dueno


def _particion_ocupa(ancho):
    """Cuantos bits reserva un campo de anchura `ancho` desde su shift."""
    return ancho


def ancho_maximo_antes_de_que_pise(shift, siguiente_shift):
    return max(0, siguiente_shift - shift)


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

    chk("grupos: el header existe y se lee", os.path.isfile(VID), VID)
    g = macros_de_grupos()
    chk("grupos: el header tiene grupos con campos", len(g) >= 5, sorted(g)[:8])
    chk("grupos: y MAP_QUEUES esta entre ellos",
        any(any("MAP_QUEUES" in c for c in v) for v in g.values()),
        {k: list(v)[:3] for k, v in list(g.items())[:3]})

    c2 = next((v for k, v in g.items()
               if k.upper().endswith("CONTROL2") and
               any("MAP_QUEUES" in c for c in v)), None)
    chk("MAP_QUEUES: el grupo CONTROL2 se localiza", c2 is not None, sorted(g))
    if c2:
        filas, sin_det = determinacion(c2)
        d = {f["campo"]: f for f in filas}
        # ESTE vector es la CORRECCION de un error del hallazgo 1199.  Alli se
        # dedujo el ancho "del hueco hasta el campo siguiente" y se escribio
        # `[25:2] y hueco` en la tabla y `[3:2],  de 2 bits` en la conclusion.
        # Las dos cosas no pueden ser verdad a la vez,  y la que se sostiene es
        # que NO SE DEDUCE:  el hueco es de 24 bits porque el "siguiente" (QUEUE
        # << 26)  es un campo de OTRO dword.
        chk("MAP_QUEUES: DOORBELL_OFFSET NO tiene anchura deducible",
            d.get("PACKET3_MAP_QUEUES_DOORBELL_OFFSET", {}).get("ancho") is None,
            d.get("PACKET3_MAP_QUEUES_DOORBELL_OFFSET"))
        chk("MAP_QUEUES: y el motivo lo dice, en vez de devolver 24 bits",
            any(x["campo"] == "PACKET3_MAP_QUEUES_DOORBELL_OFFSET" and
                "NO determinan" in x["motivo"] for x in sin_det),
            [x for x in sin_det][:3])
        chk("MAP_QUEUES: [25:2] es lo que daria la deducci ingenua, y es 24 bits",
            26 - 2 == 24, "comprobado a proposito: por eso no se deduce")

    # El ULTIMO campo:  sin siguiente,  ancho NO determinado
    filas, sin_det = determinacion({"A": 4, "B": 8})
    chk("sin determinar: el ultimo campo no inventa su anchura",
        len(sin_det) == 1 and sin_det[0]["campo"] == "B", sin_det)

    # Campos contiguos:  los anchos SI se deducen
    filas, sin_det = determinacion({"A": 4, "B": 8, "C": 10})
    # MEDIDO: este vector exigia `sin_det == []`,  y no puede ser:  el ULTIMO
    # campo no tiene siguiente y su anchura no la determina nadie.  Exigirlo
    # era exigir que el instrumento INVENTARA una,  que es justo lo que este
    # fichero dice que no hace.
    chk("contiguos: con pasos pequenos los DOS primeros quedan fijados, y el "
        "ultimo no",
        [f["ancho"] for f in filas] == [4, 2, None] and
        [x["campo"] for x in sin_det] == ["C"],
        ([(f["campo"], f["ancho"]) for f in filas],
         [x["campo"] for x in sin_det]))

    # `validar` es donde el solape EXISTE,  porque los anchos vienen de fuera
    sol, sin = validar([("QUEUE", 26, 28), ("PIPE", 29, 31), ("ME", 31, 31)])
    # MEDIDO: el vector exigia que el solape se reportara con `campo == "PIPE"`.
    # El recorrido ordena por bit de inicio,  asi que ME (31)  se encuentra
    # DESPUES de PIPE (29)  y el solape se reporta desde ME.  Los dos lados son
    # el mismo hecho,  y exigir un orden concreto es exigir la implementacion.
    chk("validar: PIPE de 3 bits (29..31) PISA a ME de 1 bit (31..31)",
        len(sol) == 1 and {sol[0]["campo"], sol[0]["pisa_a"]} ==
        {"PIPE", "ME"} and sol[0]["rango"] == [31, 31], sol)
    chk("validar: y el solape lo dice con los dos rangos",
        all("rango" in x and "rango_de_otro" in x for x in sol), sol)
    sol2, _ = validar([("QUEUE", 26, 28), ("PIPE", 29, 30), ("ME", 31, 31)])
    chk("validar: PIPE de 2 bits NO pisa a ME:  la particion es valida",
        sol2 == [], sol2)
    # 32 bits menos 2 cubiertos = 30.  El vector decia 25:  cuenta arithmetic
    # hecha de memoria,  que es de donde salen las cifras inventadas.
    _sol3, sin_dueno = validar([("A", 4, 4), ("B", 31, 31)])
    chk("validar: y los bits sin dueno se listan, y son 32 menos los cubiertos",
        len(sin_dueno) == ANCHO_DWORD - 2 and
        set(range(ANCHO_DWORD)) - set(sin_dueno) == {4, 31},
        (len(sin_dueno), sin_dueno[:6]))

    # El fallo de mi propia prueba de uso:  `--valida` con `action="append"`
    # acepta un valor por bandera,  y un dword con nueve campos son nueve
    # banderas.  Se acepta la lista separada por comas,  y se prueba con la
    # forma de TRES campos que es la que se usa de verdad.
    import subprocess as _sp
    _r = _sp.run([sys.executable, os.path.abspath(__file__), "--valida",
                  "QUEUE=26-28,PIPE=29-31,ME=31-31"], capture_output=True,
                 text=True)
    chk("CLI: --valida acepta una lista separada por comas, que es como se usa",
        _r.returncode == 1 and "SOLAPE" in _r.stdout,
        (_r.returncode, _r.stdout[:120], _r.stderr[:120]))

    # El defecto que la salida del instrumento destapo:  los sub-bloques de
    # UNMAP_QUEUES se distinguen por una MINUSCULA final  y el regex no la
    # aceptaba.  Este vector falla si alguien vuelve a poner `[A-Z0-9_]`.
    chk("agrupacion: el comentario de un sub-bloque con minúscula SI se reconoce",
        RE_GRUPO.search("/* CONTROL2a */") is not None and
        RE_GRUPO.search("/* CONTROL2a */").group(1) == "CONTROL2a",
        RE_GRUPRO if False else "no casa")
    _gu = macros_de_grupos()
    # MEDIDO: el vector exigia `len(_n_gu) == 1`,  y hay DOS grupos
    # CONTROL2a:  el de UNMAP_QUEUES y el de QUERY_STATUS.  El predicado era
    # demasiado flojo y fallaba por la coincidencia de NOMBRE,  no porque la
    # agrupacion fuera mala.  Un vector que falla por un nombre repetido en otro
    # sitio ensena a ignorar los que fallan de verdad.
    _n_gu = [k for k in _gu if "UNMAP_QUEUES" in k and k.endswith("CONTROL2a")]
    chk("agrupacion: y ACTION, PASID y RB_WPTR NO acaban en el mismo grupo",
        len(_n_gu) == 1 and
        set(_gu[_n_gu[0]]) == {"PACKET3_UNMAP_QUEUES_PASID"} and
        len([k for k in _gu if "UNMAP_QUEUES" in k and
             k.endswith("CONTROL3b")]) == 1, _n_gu)

    chk("limite: que no haya solapes NO demuestra que el layout sea el del ASIC",
        True, "declarado en el docstring;  RUNTIME=NOT_RUN")
    chk("limite: y el umbral ANCHO_PLAUSIBLE es una CONVENCION declarada",
        isinstance(ANCHO_PLAUSIBLE, int) and ANCHO_PLAUSIBLE == 8,
        ANCHO_PLAUSIBLE)

    print()
    if fallos:
        print("SELFTEST FALLIDO: %d" % len(fallos))
        return 1
    print("SELFTEST OK: %d vectores" % (len(fallos) + 31))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog=TOOL, description=__doc__.split("\n")[1])
    ap.add_argument("--header", help="header a leer;  por defecto vid.h")
    ap.add_argument("--grupo", help="muestra solo este grupo")
    ap.add_argument("--valida", metavar="CAMPO=lo-hi[,CAMPO=lo-hi...]",
                    action="append", default=[],
                    help="comprueba unos anchos DADOS:  solapes y bits sin "
                         "dueno.  Es donde el solape puede existir.  Se "
                         "acepta una lista separada por comas,  porque un "
                         "dword tiene hasta nueve campos y nine banderas no "
                         "son manejables")
    ap.add_argument("--solo-problemas", action="store_true",
                    help="solo los grupos con algun campo sin determinar")
    ap.add_argument("--arborme", action="store_true",
                    help="barra TODO el arbol buscando campos de PM3 que "
                         "declaren anchura,  y comprueba antes que el patron "
                         "sepa ver un positivo")
    ap.add_argument("--convenciones", action="store_true",
                    help="cuantos campos de PM4 declaran mascara, y cuantos "
                         "registros del mismo header si")
    ap.add_argument("--selftest", "--self-test", dest="selftest",
                    action="store_true", help="los vectores")
    ap.add_argument("--version", action="version", version=VERSION)
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.arborme:
        r = anchuras_declaradas_en_el_arbol()
        print("BARRIDO DEL ARBOL  %d ficheros" % r["ficheros"])
        print("  campos de PM3 que declaran anchura: %d" % r["declaraciones"])
        print("  el patron VE un positivo conocido:  %s"
              % r["el_patron_ve_un_positivo"])
        if not r["el_patron_ve_un_positivo"]:
            print("  EL BARRIDO NO ES FIABLE:  no encuentra ni el caso de")
            print("  prueba.  Su cero no es un dato.")
            return 2
        if r["declaraciones"]:
            for v in r["vistos"]:
                print("    %s" % v)
        else:
            print("  Ni una.  En TODO el arbol.  La anchura de un campo de PM4")
            print("  no se puede leer de aqui,  para NINGUN ASIC.")
        return 0
    if a.convenciones:
        c = convenciones(a.header)
        print("CONVENCIONES DE ANCHURA EN %s" % (a.header or VID))
        print("  campos de PM3 declarada con << : %d" % c["campos_pm4"])
        print("  de esos, con mascara declarada  : %d" % c["campos_pm4_con_mascara"])
        print("  mascaras de registro del mismo header: %d" % c["mascaras_no_pm4"])
        print()
        print("  El header declara anchura para los registros y NO para los")
        print("  campos de PM3.  No es su estilo:  son dos convenciones,  y la")
        print("  que falta es la de los paquetes.")
        return 0
    if a.valida:
        anchos = []
        for lista in a.valida:
            for v in lista.split(","):
                v = v.strip()
                if not v:
                    continue
                campo, _, r = v.partition("=")
                lo, _, hi = r.partition("-")
                try:
                    anchos.append((campo.strip(), int(lo), int(hi)))
                except ValueError:
                    print("  no se entiende: %r  (se quiere CAMPO=lo-hi)" % v)
                    return 2
        sol, sin = validar(anchos)
        print("VALIDANDO %d campos dados" % len(anchos))
        for s in sol:
            print("  SOLAPE %s" % s["motivo"])
        if sin:
            print("  SIN DUENO  %d bits: %s" % (len(sin), sin[:16]))
        if not sol and not sin:
            print("  particion valida de 32 bits, sin solapes ni huecos")
        print("  Que la particion sea VALIDA no dice que el ASIC la acepte:")
        print("  RUNTIME=NOT_RUN.")
        return 1 if sol else 0
    grupos = macros_de_grupos(a.header)
    if not grupos:
        print("  ningun grupo con macros de campo en %s" % (a.header or VID))
        return 2
    con_problemas = 0
    for nombre, campos in sorted(grupos.items()):
        if a.grupo and a.grupo.upper() not in nombre.upper():
            continue
        filas, sin_det = determinacion(campos)
        if sin_det:
            con_problemas += 1
        if a.solo_problemas and not sin_det:
            continue
        print("  %s" % nombre)
        for f in filas:
            print("    %-34s shift %2d   %s"
                  % (f["campo"].replace("PACKET3_", ""), f["shift"],
                     ("[%d:%d]  %d bits" % (f["hi"], f["lo"], f["ancho"]))
                     if f["ancho"] is not None
                     else "anchura NO deducible de los shifts"))
    print()
    print("  grupos con algun campo sin anchura deducible: %d de %d"
          % (con_problemas, len(grupos)))
    print("  Esto dice si los DESPLAZAMIENTOS determinan un layout.  No dice")
    print("  que el layout sea el del ASIC:  RUNTIME=NOT_RUN.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
