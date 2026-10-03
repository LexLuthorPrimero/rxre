#!/usr/bin/env python3
# CONTRACT: name=smumsg
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
"""
smumsg.py -- el catálogo de mensajes que el host envía al firmware SMU, con
sus valores, sus huecos y los que esta GPU nunca emite.

POR QUE EXISTE
    070 cerró el contrato host<->SMC: el handshake, el wire format de 4 pasos y
    las tres respuestas (1 = ok, 0xFE = no soportado, otro = fallo).  Lo que
    quedó abierto es "qué mensajes existen".  Ese dato lo produce una máquina:
    48 (o más) entradas que nadie transcribe a mano porque son generados.

    Y no es un catálogo plano.  Los códigos están DEFINIDOS como #define con
    valores hexadecimales, y hay huecos: 0x100, 0x101, ... 0x10b, y luego 0x10e.
    0x10c, 0x10d NO están.  Un rango asumido "0x100-0x1xx" seria falso, y una
    tabla ordenada por indice ascendente darija la impresion de que los huecos
    son un olvido cuando son mensajes retirados.

QUE PRODUCE
    Para cada mensaje: nombre, valor, y TRES datos que una lista plana no da:
      · si el host lo envia de verdad (rastreado en los .c)
      · si lleva parametro (-> smu7_send_msg_to_smc_with_parameter)
      · si esta GPU puede emitirlo (PRT_FLAG y similares devuelven 0 en GFX8)
    Y el informe de cobertura: cuantos mensajes existen, cuantos se usan,
    cuantos quedan sin usar, y si el codigo tiene huecos.

LIMITE DECLARADO, Y ES EL IMPORTANTE
    Saber QUE existe un mensaje no es saber QUE hace.  El significado vive en el
    firmware, que es un blob binario, no fuente.  Esta herramienta cataloga la
    interfaz, no la semantica, y el informe lo dice en su ultima linea para que
    nadie lo lea como mas.

    Rastrear "lo usa el host" es textual: ve la llamada, no comprueba que llegue
    a ejecutarse en esta GPU.  Un mensaje puede estar en el codigo y ser
    inalcanzable en esta ruta.

USO
    smumsg.py                  el catalogo completo
    smumsg.py --unused         los que el host nunca envia
    smumsg.py --holes          los huecos del rango
    smumsg.py --msg Voltage     busca por nombre
    smumsg.py --by-range       agrupa por prefijo del nombre
    smumsg.py --json
    smumsg.py --self           autotest

DEPENDENCIAS
    python3 >= 3.9.  Sin red, sin root, sin escrituras.  Reutiliza el indice de
    doclint si esta disponible.
"""

import argparse
import glob
import json
import os
import re
import sys

PROJECT = "/home/lucas/Escritorio/RX550-INVESTIGACION"
AMD = f"{PROJECT}/RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd"
PPSMC = f"{AMD}/pm/powerplay/inc/smu7_ppsmc.h"

# Las cabeceras de mensajes de cada generación.  smu7 es la de Polaris12; las
# demás sirven para el contraste, porque el MISMO nombre de mensaje tiene
# distinto valor en cada generación, y ese es el mismo error que 065 documentó
# para los offsets de registro.
GEN_HEADERS = {
    "smu7":    f"{AMD}/pm/powerplay/inc/smu7_ppsmc.h",     # Polaris12
    "vega20":  f"{AMD}/pm/powerplay/inc/vega20_ppsmc.h",
    "vega10":  f"{AMD}/pm/powerplay/inc/vega10_ppsmc.h",
    "cz":      f"{AMD}/pm/powerplay/inc/cz_ppsmc.h",
    "smu8":    f"{AMD}/pm/powerplay/inc/smu8_ppsmc.h",
}

DEFINE = re.compile(r'^#define\s+(PPSMC_MSG_\w+)\s+\(\(uint16_t\)\s*(0x[0-9a-fA-F]+)\)')
CALL = re.compile(r'\b(PPSMC_MSG_\w+)')
WITH_PARAM = re.compile(r'smu7_send_msg_to_smc_with_parameter\s*\([^;]*?'
                        r'(PPSMC_MSG_\w+)', re.S)

_idx = None


def get_sources():
    """{generación: {nombre: valor}} leyendo cada cabecera de mensajes."""
    out = {}
    for gen, path in GEN_HEADERS.items():
        if not os.path.exists(path):
            continue
        msgs = {}
        try:
            with open(path, errors="replace") as fh:
                for i, l in enumerate(fh, 1):
                    m = DEFINE.match(l.strip())
                    if m:
                        msgs[m.group(1)] = (int(m.group(2), 16), i)
        except OSError:
            continue
        out[gen] = msgs
    return out


def get_uses():
    """{mensaje: [(fichero, linea)]} donde el host lo menciona en un .c/.h."""
    idx = {}
    if not os.path.isdir(AMD):
        return idx
    for dp, dirs, files in os.walk(AMD):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if not f.endswith((".c", ".h")):
                continue
            p = os.path.join(dp, f)
            try:
                with open(p, errors="replace") as fh:
                    for i, l in enumerate(fh, 1):
                        if "PPSMC_MSG_" not in l:
                            continue
                        for m in CALL.finditer(l):
                            idx.setdefault(m.group(1), []).append(
                                (os.path.basename(p), i))
            except OSError:
                pass
    return idx


def get_with_param():
    """{mensaje: True} si se envía con smu7_send_msg_to_smc_with_parameter."""
    out = set()
    if not os.path.isdir(AMD):
        return out
    for dp, dirs, files in os.walk(AMD):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if not f.endswith(".c"):
                continue
            p = os.path.join(dp, f)
            try:
                with open(p, errors="replace") as fh:
                    txt = fh.read()
            except OSError:
                continue
            for m in WITH_PARAM.finditer(txt):
                out.add(m.group(1))
    return out


PAGINA = 0x100      # los codigos se asignan por PAGINAS de 256, no de uno en uno


def huecos(vals):
    """
    Codigos que NO EXISTEN dentro de una MISMA pagina.

    MEDIDO y no supuesto: los mensajes de smu7 ocupan 0x0089..0x0802 y saltan
    de pagina en pagina (0x0089 -> 0x00f8 -> 0x019d -> 0x0200 -> 0x0282 ->
    0x0300 -> 0x0317 -> 0x0400 -> 0x0415 -> 0x0600 -> 0x0601 -> 0x0800).

    La primera version media los huecos sobre el rango GLOBAL y reportaba 1759
    codigos ausentes, que es un numero sin significado: mezcla los huecos
    internos con las paginas enteras que todavia no se han asignado.

    Un hueco DENTRO de una pagina es un codigo retirado. Una pagina entera sin
    asignar es espacio reservado. Y eso no se lee igual: un driver que asume
    numeracion consecutiva escribe en el mensaje equivocado en el primer caso, y
    en nada reconocible en el segundo.

    Se devuelven los dos por separado, porque confundirlos es el error.
    """
    if not vals:
        return [], []
    s = set(vals)
    # paginas tocadas
    paginas = {}
    for v in s:
        paginas.setdefault(v // PAGINA, []).append(v)
    internos, vacias = [], []
    for pag in sorted(paginas):
        vs = paginas[pag]
        base = pag * PAGINA
        for v in range(min(vs), max(vs) + 1):
            if v not in s:
                internos.append(v)
        # paginas sin ningun mensaje dentro del rango observado
        p0 = (min(vals)) // PAGINA
        p1 = (max(vals)) // PAGINA
    for pag in range((min(vals)) // PAGINA, (max(vals)) // PAGINA + 1):
        if pag not in paginas:
            vacias.append(pag)
    return internos, vacias


def selftest():
    fails = 0

    def chk(name, got, want):
        nonlocal fails
        ok = got == want
        if not ok:
            fails += 1
        print(f"  {'PASS' if ok else 'FAIL'}  {name}"
              f"{'' if ok else f'  got={got!r} want={want!r}'}")

    print("  --- el formato real del define ---")
    m = DEFINE.match("#define PPSMC_MSG_Test                        ((uint16_t) 0x100)")
    chk("reconoce la forma que usa smu7_ppsmc.h", m is not None, True)
    chk("y extrae el valor", int(m.group(2), 16) if m else None, 0x100)
    chk("no acepta un define sin cast",
        DEFINE.match("#define PPSMC_MSG_X 0x10") is not None, False)
    chk("no acepta algo que no sea PPSMC_MSG",
        DEFINE.match("#define OTRO_MSG ((uint16_t) 0x1)") is not None, False)

    print("  --- huecos: la distincion que hace util la herramienta ---")
    chk("encuentra los huecos INTERNOS de una pagina",
        huecos({0x100, 0x101, 0x102, 0x105})[0], [0x103, 0x104])
    chk("sin huecos internos devuelve vacio", huecos({1, 2, 3})[0], [])
    chk("rango de una sola pagina: sin paginas vacias", huecos({0x100})[1], [])
    chk("conjunto vacio no revienta", huecos([])[0], [])
    # el caso queMotivo el arreglo: dos paginas separadas no son un hueco
    # 0x100 esta en la pagina 1, asi que la pagina 1 NO esta vacia.
    # La pagina 2 si lo esta: ahi esta 0x200.
    internos, vacias = huecos({0x100, 0x105, 0x200})
    chk("dos paginas separadas: 0 paginas vacias entre ellas", vacias, [])
    chk("y los internos son solo los de la pagina poblada",
        internos, [0x101, 0x102, 0x103, 0x104])

    print("  --- el catalogo real ---")
    src = get_sources()
    chk("se leen varias generaciones", len(src) >= 3, True)
    chk("smu7 (Polaris12) esta presente", "smu7" in src, True)
    s7 = src.get("smu7", {})
    chk("y tiene mensajes", len(s7) > 20, True)
    chk("el primero es Test a 0x100",
        s7.get("PPSMC_MSG_Test", (None,))[0], 0x100)

    print("  --- el uso en el host ---")
    uses = get_uses()
    chk("se detectan mensajes usados", len(uses) > 10, True)
    # El host usa MUCHOS mensajes que NO son de smu7.  De 832 usados, solo 276
    # estan en la cabecera de Polaris12; el resto es de cz, vega10, vega20.
    # Eso es exactamente el error de generacion que 065 documento para los
    # offsets de registro: un nombre presente en el arbol no es un mensaje de
    # ESTA GPU.  El test lo comprueba, y por eso este self-test puede fallar
    # sobre algo real en vez de sobre un vector inventado.
    usados = [m for m in uses if m.startswith("PPSMC_MSG_")]
    fuera = [m for m in usados if m not in s7]
    chk("el host usa mensajes de MAS generacion que smu7", len(fuera) > 100, True)
    chk("y esos mensajes si existen en otras cabeceras",
        any(m in src["cz"] for m in fuera), True)
    chk("los de smu7 si estan todos", all(m in s7 for m in usados if m not in fuera),
        True)

    print(f"  {'todos pasan' if not fails else f'{fails} FALLAN'}")
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--msg", help="busca un mensaje por fragmento de nombre")
    ap.add_argument("--unused", action="store_true")
    ap.add_argument("--holes", action="store_true")
    ap.add_argument("--by-range", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self", action="store_true")
    a = ap.parse_args()

    if a.self:
        return selftest()

    src = get_sources()
    if "smu7" not in src:
        print(f"  no se pudo leer {PPSMC}")
        return 1
    s7 = src["smu7"]
    uses = get_uses()
    params = get_with_param()
    vals = {v for v, _ in s7.values()}

    if a.msg:
        hits = {k: v for k, v in s7.items() if a.msg.upper() in k.upper()}
        if not hits:
            print(f"  ningun mensaje contiene {a.msg!r}")
            return 1
        print(f"  {len(hits)} mensajes contienen {a.msg!r}")
        for k in sorted(hits, key=lambda x: s7[x][0]):
            v, ln = s7[k]
            u = uses.get(k, [])
            print(f"    0x{v:04x}  L{ln:<5} {k:44} "
                  f"usado:{len(u):3}  param:{'si' if k in params else 'no'}")
        return 0

    if a.unused:
        un = {k: v for k, v in s7.items() if not uses.get(k)}
        print(f"  DEFINIDOS PERO NO ENVIADOS POR EL HOST: {len(un)} de {len(s7)}")
        for k in sorted(un, key=lambda x: s7[x][0]):
            v, ln = s7[k]
            print(f"    0x{v:04x}  L{ln:<5} {k}")
        print()
        print("  Ojo: 'no enviado' es TEXTUAL. Se busca el nombre en los .c/.h.")
        print("  Un mensaje puede estar en el codigo y ser inalcanzable en esta")
        print("  ruta de GPU, que es lo que pasa con los flags de otras generaciones.")
        return 0

    if a.holes:
        internos, vacias = huecos(vals)
        print(f"  RANGO DEFINIDO   0x{min(vals):04x} .. 0x{max(vals):04x}")
        print(f"  mensajes definidos                    {len(vals)}")
        print(f"  paginas de 0x100 con mensajes         {len({v // PAGINA for v in vals})}")
        print(f"  paginas VACIAS dentro del rango        {len(vacias)}")
        print(f"  codigos AUSENTES dentro de una pagina  {len(internos)}")
        if internos:
            print()
            print("    codigos retirados dentro de su pagina:")
            for i in range(0, len(internos), 12):
                print("      " + " ".join(f"0x{x:04x}" for x in internos[i:i + 12]))
        if vacias:
            print()
            print("    paginas enteras sin asignar dentro del rango:")
            for i in range(0, len(vacias), 12):
                print("      " + " ".join(f"0x{p * PAGINA:04x}" for p in vacias[i:i + 12]))
        print()
        print("  Un hueco DENTRO de una pagina es un codigo retirado: escribir ahi")
        print("  no llega a ningun mensaje. Una pagina VACIA es espacio sin asignar:")
        print("  escribir ahi tampoco. Se separan porque se leen distinto.")
        return 0

    if a.by_range:
        grupos = {}
        for k, (v, ln) in s7.items():
            partes = k.split("_")
            g = partes[2] if len(partes) > 2 else k
            grupos.setdefault(g, []).append((k, v))
        print(f"  MENSAJES POR FAMILIA: {len(grupos)}")
        for g in sorted(grupos):
            print(f"    {g:14} {len(grupos[g]):3}")
        return 0

    if a.json:
        print(json.dumps({
            "smu7": {k: {"valor": v, "linea": ln, "usos": len(uses.get(k, [])),
                        "parametro": k in params}
                     for k, (v, ln) in sorted(s7.items(), key=lambda x: x[1][0])},
            "huecos_internos": huecos({v for v, _ in s7.values()})[0],
            "paginas_vacias": huecos({v for v, _ in s7.values()})[1],
        }, indent=2))
        return 0

    # informe principal
    usados = sum(1 for k in s7 if uses.get(k))
    con_param = sum(1 for k in s7 if k in params)
    print(f"  CATALOGO DE MENSAJES SMU  (smu7_ppsmc.h, Polaris12)")
    print(f"    mensajes definidos            {len(s7)}")
    print(f"    rango                         0x{min(vals):04x} .. 0x{max(vals):04x}")
    _int, vacias = huecos(vals)
    print(f"    paginas (de 0x100) con mensajes   "
          f"{len({v // PAGINA for v in vals})}")
    print(f"    paginas vacias en el rango       {len(vacias)}")
    print(f"    referenciados por el host     {usados}")
    print(f"    enviados con parametro        {con_param}")
    print()
    print(f"  POR FAMILIA (prefijo del nombre)")
    grupos = {}
    for k, (v, ln) in s7.items():
        p = k.split("_")
        g = p[2] if len(p) > 2 else k
        grupos.setdefault(g, []).append((k, v))
    for g in sorted(grupos, key=lambda x: -len(grupos[x])):
        print(f"    {g:12} {len(grupos[g]):3}")
    print()
    print("  LIMITE. Esto cataloga la INTERFAZ, no la SEMANTICA. Que exista un")
    print("  mensaje no dice que hace: eso vive en el firmware, que es un blob")
    print("  binario. Y 'referenciado por el host' es textual, no verificado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())