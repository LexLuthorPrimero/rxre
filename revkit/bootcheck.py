#!/usr/bin/env python3
# CONTRACT: name=bootcheck
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=indeterminado
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py, y el veredicto fue `NO_DETERMINED`.
# NO se upgraded a `WRITES_FILES=yes` porque no esta medido, y NO se dejo en
# `no` porque el codigo no lo sostiene.  La razon del NO_DETERMINED es que lanza comandos para leer el estado de arranque, y el destino de su salida no es un literal.
#
# Poner `yes` seria MENTIR en un sentido que el validador no puede detectar, que
# es lo que el propio toolkit.py escribe de sus cinco falsos positivos: "un
# contrato en prosa no se puede comprobar con una maquina".  Poner `no` seria
# Peor: seria una afirmacion que nadie ha comprobado.
#
# TOUCHES_INTEGRATED=no: lee sysfs y ficheros.  No hace ioctl ni escribe en la
# GPU.  Ver 1487.
# -*- coding: utf-8 -*-
"""bootcheck.py -- valida el arranque de la placa contra el log del kernel.

POR QUE EXISTE. Los cuatro `dev_err` de fase de inicializacion (early_init,
sw_init, hw_init, late_init) son un OBSERVABLE GENERICO de "esta placa no arranco
bien". Un driver propio necesita exactamente esa comprobacion para validar su
propio arranque, y hoy no hay ninguna herramienta que la haga.

DISEÑO, y sale directamente de dos errores mios de la ronda anterior:

  * **CADA CERO LLEVA SU CONTROL POSITIVO EN EL MISMO PIPELINE.** La leccion fue
    que un `grep -c` que devuelve 0 y otro que devuelve 0 son indistinguibles
    mientras no sepas que el canal lee. Aqui el control es el chequeo C0, y si el
    log no contiene NADA reconocible la herramienta NO dice "0 fallos": dice
    `INVALID_RESULT` y sale con rc=4. **Un cero sin prueba no se reporta.**

  * **LA ENTRADA ES UN FICHERO, no una tuberia.** Por lo mismo: si la herramienta
    ejecutara `journalctl` ella misma, un fallo de su propio pipeline seria
    indistinguible de un arranque limpio. Con fichero de entrada, se puede probar
    contra logs SINTETICOS, y ahi si se ve si el control funciona.

QUE RESUELVE, en cuatro preguntas que el proyecto ya necesita responder:

  C0  el log es legible y reconocible          (control, no resultado)
  C1  estan los 9 bloques de la placa          (superficie, EV-40/EV-42)
  C2  ninguna fase de init fallo               (cierre de EV-43)
  C3  el ASIC que el kernel nombro es Polaris12

LIMITES DECLARADOS, y son la parte importante:
  * No mira hardware. Dice lo que el driver **imprimio**, no lo que el hardware
    **hizo**. Que ninguna fase fallo NO es que el hardware quedara bien: eso sigue
    `NOT_DETERMINED` sin lectura de registros.
  * El log de UN arranque es una muestra de UN arranque. Un verde no es una
    garantia de que los otros arranquen igual.
  * La lista de bloques esperados viene de `gfx8blocks.py` mas lo OBSERVADO en
    EV-42. No es una lista inventada aqui; si el kernel cambia la lista, esta
    herramienta falla, y eso es lo correcto.

CONTRACT: name=bootcheck
CONTRACT: READONLY=yes
CONTRACT: WRITES_FILES=no
CONTRACT: WRITES_SYSFS=no
CONTRACT: MUTATES_CORPUS=no
CONTRACT: WRITES_GPU=no
"""

import io
import os
import re
import sys

FASE_FALLO = re.compile(
    r"(early_init|sw_init|hw_init|late_init|early_fini|sw_fini|hw_fini)"
    r" of IP block <[^>]*> failed")
IPB = re.compile(
    r"detected ip block number (\d+) <([a-z0-9_]+)> \(([a-z0-9_]+)\)")
ASIC = re.compile(r"initializing kernel modesetting \(([A-Z0-9_]+)")

# Los nueve bloques de Polaris12. Texto EXACTO observado en EV-42, no derivado:
#   numero, <version del IP>, (nombre de la TABLA de funciones)
ESPERADOS = [
    (0, "common_v1_0_0", "vi_common"),
    (1, "gmc_v8_1_0", "gmc_v8_0"),
    (2, "ih_v3_0_0", "tonga_ih"),
    (3, "gfx_v8_0_0", "gfx_v8_0"),
    (4, "sdma_v3_1_0", "sdma_v3_0"),
    (5, "smu_v1_0_0", "powerplay"),
    (6, "dce_v1_0_0", "dm"),
    (7, "uvd_v6_3_0", "uvd_v6_0"),
    (8, "vce_v3_4_0", "vce_v3_0"),
]
ASIC_ESPERADO = "POLARIS12"


def analizar(texto):
    """Devuelve un dict con todo lo medido. Sin efectos: funcion pura."""
    bloques = IPB.findall(texto)
    fases_fallidas = FASE_FALLO.findall(texto)
    asic = ASIC.findall(texto)
    return {
        "n_lineas": len(texto.splitlines()),
        "n_amdgpu": texto.count("amdgpu"),
        "bloques": bloques,
        "n_bloques": len(bloques),
        "fases_fallidas": fases_fallidas,
        "n_fallos": len(fases_fallidas),
        "asic": asic[0] if asic else None,
        "n_asic": len(asic),
        # senal de que el log es de ESTE arranque y de esta placa
        "reconocible": (len(bloques) > 0 and "amdgpu" in texto),
    }


def checks(r):
    """Lista de (nombre, ok, detalle). C0 va primero y es el control."""
    out = []
    # --- C0: CONTROL. Sin esto no se reporta ningun cero. -------------------
    ok0 = r["reconocible"] and r["n_bloques"] > 0
    out.append(("C0 control: el log es de esta placa y es legible",
                ok0,
                "lineas=%d amdgpu=%d bloques=%d" % (r["n_lineas"], r["n_amdgpu"],
                                                    r["n_bloques"])))
    # --- C1: los nueve bloques ---------------------------------------------
    vistos = set((int(n), v, t) for n, v, t in r["bloques"])
    faltan = [e for e in ESPERADOS if e not in vistos]
    out.append(("C1 los 9 bloques de Polaris12 estan, con su tabla", not faltan,
                "faltan: %s" % (faltan if faltan else "ninguno")))
    # --- C2: ninguna fase fallo --------------------------------------------
    out.append(("C2 ninguna fase de inicializacion fallo", r["n_fallos"] == 0,
                "fallos: %d %s" % (r["n_fallos"],
                                   sorted(set(r["fases_fallidas"]))
                                   if r["fases_fallidas"] else "")))
    # --- C3: el ASIC que nombro el kernel ---------------------------------
    out.append(("C3 el kernel nombro %s" % ASIC_ESPERADO,
                r["asic"] == ASIC_ESPERADO,
                "nombrado: %r" % (r["asic"],)))
    return out


def selftest():
    """Vectores SINTETICOS. Aqui es donde se ve si el control funciona: el log
    bueno y el log de un arranque roto se differentiation en la entrada."""
    ok = fallan = 0

    def chk(nombre, cond):
        nonlocal ok, fallan
        if cond:
            ok += 1
            print("  OK    %s" % nombre)
        else:
            fallan += 1
            print("  FALLA %s" % nombre)

    def linea(n, v, t):
        return ("oct 02 14:55:03 kernel: amdgpu 0000:01:00.0: detected ip block "
                "number %d <%s> (%s)" % (n, v, t))

    BUENO = "\n".join([
        "oct 02 kernel: amdgpu 0000:01:00.0: initializing kernel modesetting "
        "(POLARIS12 0x1002:0x699F, 0xC7)",
        linea(*ESPERADOS[0]), linea(*ESPERADOS[1]), linea(*ESPERADOS[2]),
        linea(*ESPERADOS[3]), linea(*ESPERADOS[4]), linea(*ESPERADOS[5]),
        linea(*ESPERADOS[6]), linea(*ESPERADOS[7]), linea(*ESPERADOS[8]),
        "oct 02 kernel: amdgpu 0000:01:00.0: VRAM: 2048M",
    ]) + "\n"

    # --- el vector bueno: todo pasa ---------------------------------------
    r = analizar(BUENO)
    cs = checks(r)
    chk("log bueno -> los 4 controles pasan", all(c[1] for c in cs))

    # --- NEGATIVOS, uno por control. Un control que no puede fallar es peor
    #     que ninguno, y aqui se comprueba que cada uno puede.
    r2 = analizar(BUENO.replace(linea(*ESPERADOS[4]) + "\n", ""))
    cs2 = checks(r2)
    # MEDIDO: aqui habia un control escrito como "(not C0) and C0", que es
    # SIEMPRE falso: un control que no puede pasar. Y era redundante con el
    # siguiente, que si distingue. Se queda solo el que distingue, y se comprueba
    # explicitamente que C0 sigue en verde, porque si C0 cayera tambien el motivo
    # del fallo de C1 seria otro (log ilegible, no bloque que falta).
    _roto2 = [c[0] for c in cs2 if not c[1]]
    chk("sin sdma_v3_1 -> falla SOLO C1, y C0 sigue en verde",
        _roto2 == [cs[1][0]] and cs2[0][1] is True)

    roto = BUENO.replace(
        "VRAM: 2048M",
        "hw_init of IP block <sdma_v3_0> failed -19")
    cs3 = checks(analizar(roto))
    chk("un hw_init fallido -> C2 FALLA, y solo C2",
        [c[0] for c in cs3 if not c[1]] == [cs[2][0]])

    otro = BUENO.replace("POLARIS12", "NAVI10")
    cs4 = checks(analizar(otro))
    chk("ASIC distinto -> C3 FALLA, y solo C3",
        [c[0] for c in cs4 if not c[1]] == [cs[3][0]])

    # --- EL CONTROL, y su limite exacto -----------------------------------
    vacio = checks(analizar("esta es una linea que no es el log de nadie\n"))
    chk("log irreconocible -> C0 FALLA (no dice '0 fallos')",
        not vacio[0][1])
    chk("log irreconocible -> ademas fallan C1 y C3, y C2 sale 0 sin mentir",
        [c[0] for c in vacio if not c[1]] == [vacio[0][0], vacio[1][0], vacio[3][0]]
        and vacio[2][1] is True)
    chk("log irreconocible -> el 0 de C2 viene con C0 en rojo al lado",
        not vacio[0][1] and "0" in vacio[2][2])

    # --- casos limite ------------------------------------------------------
    chk("log vacio -> C0 FALLA y no revienta",
        not checks(analizar(""))[0][1])
    chk("sin salto de linea final -> se analiza igual",
        checks(analizar(BUENO.rstrip("\n")))[0][1] is True and
        checks(analizar(BUENO.rstrip("\n")))[1][1] is True)
    chk("doble espacio antes de '(' -> NO cuenta como bloque (fiel al bug de EV-42)",
        analizar(BUENO.replace("<gfx_v8_0_0> (gfx_v8_0)",
                               "<gfx_v8_0_0>  (gfx_v8_0)"))["n_bloques"] == 8)

    print("  ---")
    print("  vectores OK: %d   controles en rojo: %d" % (ok, fallan))
    return 1 if fallan else 0


def main(argv):
    if "--self-test" in argv:
        return selftest()
    ruta = None
    if "--log" in argv:
        ruta = argv[argv.index("--log") + 1]
    if "--esperado-blocks" in argv:
        # util para una placa distinta, sin tocar el codigo
        for e in argv[argv.index("--esperado-blocks") + 1].split(";"):
            n, v, t = e.split(",")
            ESPERADOS.append((int(n), v, t))
    # NOTA DE DISEÑO: aqui NO se ejecuta journalctl. La entrada es un
    # fichero. Motivo: si la herramienta ejecutara el pipeline, un fallo del
    # pipeline seria indistinguible de un arranque limpio, que es exactamente
    # el error que casi me costo un resultado falso.
    if ruta:
        if not os.path.isfile(ruta):
            print("ERROR/INVALID: no existe %s" % ruta)
            return 4
        texto = io.open(ruta, encoding="utf-8", errors="replace").read()
        origen = ruta
    else:
        texto = sys.stdin.read()
        origen = "stdin"
    r = analizar(texto)
    cs = checks(r)
    print("bootcheck: arranque validado sobre %s" % origen)
    print("  " + "-" * 70)
    for nombre, okc, det in cs:
        print("  %-4s %-52s %s" % ("OK" if okc else "FALLA", nombre[:52], det))
    print("  " + "-" * 70)
    if not cs[0][1]:
        print("  INVALID_RESULT: el log no es reconocible como el de esta placa.")
        print("  NO se puede afirmar 'cero fallos': no hay con que compararlo.")
        print("  Esto NO es un arranque limpio, es una lectura invalida. rc=4.")
        return 4
    n_falla = sum(1 for _n, o, _d in cs if not o)
    if n_falla:
        print("  %d control(es) en rojo. rc=3" % n_falla)
        return 3
    print("  arranque limpio segun el log. rc=0")
    print("  LIMITE: esto dice lo que el driver IMPRIMO, no lo que el hardware")
    print("  HIZO. Que el hardware quedara bien sigue NOT_DETERMINED sin lectura")
    print("  de registros. Y es la muestra de UN arranque.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))