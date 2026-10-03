#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""mutate.py - comprueba que la suite de pruebas del driver tiene dientes.

QUE RESUELVE

Una suite en verde no dice nada sobre si Sirve para detectar fallos. Solo dice
que hoy no hay ninguno. La unica forma de saber si check_ib(), el decodificador
pm4decode y las comprobaciones de cabecera detectan un bug real del encoder es
introducir un bug real y ver si algo se queja.

Eso hace esto: copia el arbol del driver a un directorio de trabajo, cambia una
linea del encoder por otra que esta rota de una forma concreta, construye,
ejecuta test_pm4 y registra si la suite lo noto.

POR QUE NO ES LO MISMO QUE LEER EL CODIGO

Porque el numero importante no es cuantos tests hay, es cuantos fallos
distintos detectan. Una suite con 200 comprobaciones que solo mira cabeceras
detecta dos clases de fallo. Una que ademas decodifica detecta cinco. Este
arnes mide esa diferencia en vez de suponerla.

Y mide tambien lo que NO se detecta, que es la parte que no se puede suponer.
Un mutante que sobrevive no es un fallo del arnes: es un agujero con nombre, y
un agujero con nombre se puede cerrar. La columna ESPERADA de la tabla dice lo
que creo que pasa; si lo que pasa y lo que creo no coinciden, la herramienta lo
dice en vez de darme la razon a mi.

NADA SE TOCA FUERA DEL DIRECTORIO DE TRABAJO

El arbol de trabajo se reconstruye en cada mutante. El corpus de Linux y el
driver del repo no se modifican jamas: si este fichero puede corromper el
driver, no sirve para auditar el driver.

USO

    mutate.py --list              catalogo de mutantes
    mutate.py --run wait_bajo     un mutante
    mutate.py --all               todos, con tabla resumen
    mutate.py --all --json        lo mismo, para composar
    mutate.py --selftest          comprueba el arnes con un proyecto sintetico

SALIDAS

    0  todo lo que se esperaba fue detectado, y nada se detecto por sorpresa
    1  alguna discrepancia: un fallo escapado, o una deteccion inesperada
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = "/tmp/opencode/mutate-scratch"

# ---------------------------------------------------------------------------
# Catalogo de mutantes.
#
# buscar/reemplazar son literales exactos, no expresiones regulares: una
# mutacion que depende de un numero de linea se rompe con el primer cambio
# inocuo y deja de medir lo que dice medir.
#
# esperado = CAER   -> la suite TIENE que notarlo. Si no cae, es un agujero.
#          = VIVIR  -> se que la suite no lo nota, y lo mido para que quede
#                      escrito. Si cae, es una sorpresa, Declarada vale mas que
#                      una sorpresa.
# ---------------------------------------------------------------------------
CATALOGO = [
    dict(nombre="wait_count_alto",
         fichero="07-DRIVER/kernel/rx550_pm4.c",
         buscar="rx550_pm4_header(RX550_PKT3_WAIT_REG_MEM, 5, false);",
         cambio="rx550_pm4_header(RX550_PKT3_WAIT_REG_MEM, 6, false);",
         esperado="CAER",
         nota="declara 8 dwords y escribe 7: la IB se queda corta",
         quien="decodifica"),
    dict(nombre="wait_count_bajo",
         fichero="07-DRIVER/kernel/rx550_pm4.c",
         buscar="rx550_pm4_header(RX550_PKT3_WAIT_REG_MEM, 5, false);",
         cambio="rx550_pm4_header(RX550_PKT3_WAIT_REG_MEM, 4, false);",
         esperado="CAER",
         nota="declara 6 y escribe 7: sobra un dword",
         quien="decodifica"),
    dict(nombre="dispatch_count_alto",
         fichero="07-DRIVER/kernel/rx550_pm4.c",
         buscar="rx550_pm4_header(RX550_PKT3_DISPATCH_DIRECT, 3, compute);",
         cambio="rx550_pm4_header(RX550_PKT3_DISPATCH_DIRECT, 4, compute);",
         esperado="CAER",
         nota="DISPATCH_DIRECT declara 4 y escribe 5",
         quien="decodifica"),
    dict(nombre="sync_count_bajo",
         fichero="07-DRIVER/kernel/rx550_pm4.c",
         buscar="rx550_pm4_header(RX550_PKT3_SURFACE_SYNC, 3, false);",
         cambio="rx550_pm4_header(RX550_PKT3_SURFACE_SYNC, 2, false);",
         esperado="CAER",
         nota="SURFACE_SYNC declara 2 y escribe 3 payload",
         quien="PACKET3(SURFACE_SYNC"),
    dict(nombre="event_count_uno",
         fichero="07-DRIVER/kernel/rx550_pm4.c",
         buscar="rx550_pm4_header(RX550_PKT3_EVENT_WRITE, 0, false);",
         cambio="rx550_pm4_header(RX550_PKT3_EVENT_WRITE, 1, false);",
         esperado="CAER",
         nota="EVENT_WRITE declara 1 payload y escribe 0",
         quien="decodifica"),
    dict(nombre="dispatch_token_fuera",
         fichero="07-DRIVER/kernel/rx550_pm4.c",
         buscar="\t/* COMPUTE_DISPATCH_INITIATOR with COMPUTE_SHADER_EN "
               "(bit 0) set. */\n\tib->buf[ib->length_dw++] = 1u;\n",
         cambio="",
         esperado="CAER",
         nota="se pierde el dword de token, que va tras el count",
         quien="decodifica"),
    dict(nombre="dispatch_operandos_intercambiados",
         fichero="07-DRIVER/kernel/rx550_pm4.c",
         buscar="\tib->buf[ib->length_dw++] = x;\n"
               "\tib->buf[ib->length_dw++] = y;\n"
               "\tib->buf[ib->length_dw++] = z;\n",
         cambio="\tib->buf[ib->length_dw++] = y;\n"
               "\tib->buf[ib->length_dw++] = x;\n"
               "\tib->buf[ib->length_dw++] = z;\n",
         esperado="CAER",
         nota="x e y cambiados de sitio: la cabecera sigue siendo valida",
         quien="dword 1 is x"),
    dict(nombre="ptepde_count_menos_uno",
         fichero="07-DRIVER/kernel/rx550_pm4.c",
         buscar="\tib->buf[ib->length_dw++] = count;\n",
         cambio="\tib->buf[ib->length_dw++] = count - 1u;\n",
         esperado="CAER",
         nota="el bug documentado de sdma_v4_0 frente a sdma_v3_0. Lo puse "
              "VIVIR en la primera version del catalogo porque el decodificador "
              "no mira el payload SDMA, y el arnes lo desmintio: lo detecta "
              "check_eq sobre dw9, con la cita (043). El bug NO puede volver sin "
              "romper un test. Lo que sigue sin cubrirse es el payload SDMA en "
              "general, y eso es un agujero con nombre, no una hipotesis",
         quien="dw9  plain count"),
]


def _sh(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str),
                       capture_output=True, text=True, timeout=300)
    return p.returncode, p.stdout, p.stderr


def preparar():
    """Reconstruye el arbol de trabajo desde cero. Idempotente."""
    if os.path.isdir(SCRATCH):
        shutil.rmtree(SCRATCH)
    # La COPIA conserva la forma del arbol: 07-DRIVER/{kernel,tests} y tools/.
    # No basta con poner kernel/ y tests/ al mismo nivel, porque los Makefile y
    # los #include usan rutas relativas como ../../tools/pm4decode.h. Reconstruir
    # la forma en vez de reescribir las rutas es lo que evita que un cambio de
    # layout convierta una copia en un fallo de compilacion silencioso, que es
    # como el primer intento de este arnes reporto ocho mutantes "que no compilan"
    # sin decir que el problema era suyo y no del encoder.
    os.makedirs(os.path.join(SCRATCH, "tools"))
    os.makedirs(os.path.join(SCRATCH, "07-DRIVER"))
    for sub in ("kernel", "tests"):
        shutil.copytree(os.path.join(RAIZ, "07-DRIVER", sub),
                        os.path.join(SCRATCH, "07-DRIVER", sub))
    for f in ("pm4decode.c", "pm4decode.h"):
        shutil.copy2(os.path.join(RAIZ, "tools", f),
                     os.path.join(SCRATCH, "tools", f))


def compilar():
    rc, out, err = _sh(["make", "-B", "-C", "07-DRIVER/tests", "test_pm4"], cwd=SCRATCH)
    if rc != 0:
        return False, (out + err)
    return True, ""


def ejecutar():
    binario = os.path.join(SCRATCH, "07-DRIVER/tests", "test_pm4")
    rc, out, err = _sh([binario])
    m = re.search(r"(\d+) checks, (\d+) failure", out)
    fallos_txt = re.findall(r"\[FAIL\] (.+)", out)
    if not m:
        return dict(checks=-1, fallos=-1, caido=None, porque=out[-300:] + err[-300:])
    checks, fallos = int(m.group(1)), int(m.group(2))
    return dict(checks=checks, fallos=fallos, caido=(fallos > 0),
                porque="; ".join(fallos_txt[:3])[:240],
                todos_fallos=fallos_txt)


def correr_mutante(m, verboso=False):
    preparar()
    ruta = os.path.join(SCRATCH, m["fichero"])
    if not os.path.isfile(ruta):
        return dict(nombre=m["nombre"], esperado=m["esperado"],
                    error="el fichero a mutar no existe: %s" % m["fichero"])
    with open(ruta, encoding="utf-8") as f:
        src = f.read()
    n = src.count(m["buscar"])
    if n != 1:
        return dict(nombre=m["nombre"], error="anclaje aparece %d veces, esperaba 1" % n,
                    esperado=m["esperado"])
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(src.replace(m["buscar"], m["cambio"]))
    ok, log = compilar()
    if not ok:
        return dict(nombre=m["nombre"], error="el mutante no compila",
                    esperado=m["esperado"], log=log[-400:])
    r = ejecutar()
    r["nombre"] = m["nombre"]
    r["esperado"] = m["esperado"]
    r["nota"] = m["nota"]
    fallos = r.pop("todos_fallos", [])
    r["n_fallos"] = len(fallos)
    r["por_quien"] = ([x for x in fallos if m.get("quien", "___") in x] if m.get("quien") else [])
    # La atribucion la calcula la herramienta, no quien lee la salida a mano.
    #
    # El criterio es el PREFIJO "[IB] " que exige la convencion declarada en
    # test_pm4.c, no una palabra suelta. La palabra "decodifica" servia y era
    # mas fragil: el check de PTEPDE no la llevaba porque su nombre hablaba de
    # la cabecera SDMA, y con el criterio por palabra ese mutante se atribuia
    # al header validator cuando en realidad lo cazan las dos comprobaciones.
    # Un criterio de atribucion tiene que ser una convencion verificada, no una
    # coincidencia de prosa.
    r["cae_el_decodificador"] = any(x.startswith("[IB]") for x in fallos)
    if r["caido"] is None:
        r["veredicto"] = "ERROR"
    elif m["esperado"] == "CAER" and r["caido"] and r["por_quien"]:
        r["veredicto"] = "CONFIRMADO"
    elif m["esperado"] == "VIVIR" and not r["caido"]:
        r["veredicto"] = "CONFIRMADO"
    else:
        r["veredicto"] = "DISCREPANCIA"
    if verboso:
        r["log_build"] = log[-200:]
    return r


def selftest():
    """El arnes tiene que distinguir CAER de VIVIR, y decirlo cuando se equivoca.

    Se prueba sobre un proyecto sintetico de tres ficheros, no sobre el driver:
    el selftest tiene que ser rapido y hermetico, y un arnes que solo funciona
    con el driver real no se puede comprobar sin pagar el build entero.
    """
    vectores = []
    d = "/tmp/opencode/mutate-selftest"
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)

    # codigo del mutante y del codigo bueno, en el mismo fichero
    with open(os.path.join(d, "k.c"), "w") as f:
        f.write(
            "#include <stdint.h>\n"
            "struct ib { uint32_t *b; unsigned n; unsigned cap; };\n"
            "static uint32_t hdr(unsigned op, unsigned cnt)\n"
            "{ return (3u<<30) | (cnt<<16) | (op<<8); }\n"
            "int emit(struct ib *ib, unsigned op, unsigned cnt)\n"
            "{\n"
            "  if (!ib || ib->n + cnt + 2u > ib->cap) return 0;\n"
            "  ib->b[ib->n++] = hdr(op, cnt);\n"
            "  for (unsigned i = 0; i < cnt; i++) ib->b[ib->n++] = 0xAAu;\n"
            "  ib->b[ib->n++] = 0u; /* el dword que sigue al payload */\n"
            "  return 1;\n"
            "}\n"
            "unsigned decode(struct ib *ib, unsigned *n_pkt)\n"
            "{\n"
            "  unsigned i = 0; *n_pkt = 0;\n"
            "  while (i < ib->n) {\n"
            "    unsigned cnt = (ib->b[i] >> 16) & 0x3Fu;\n"
            "    if (i + cnt + 2u > ib->n) return 1;\n"
            "    i += cnt + 2u; (*n_pkt)++;\n"
            "  }\n"
            "  return 0;\n"
            "}\n")

    def construir(y_correr_paquetes):
        with open(os.path.join(d, "t.c"), "w") as f:
            f.write(
                "#include <stdint.h>\n"
                "#include <stdio.h>\n"
                "struct ib { uint32_t *b; unsigned n; unsigned cap; };\n"
                "int emit(struct ib *, unsigned, unsigned);\n"
                "unsigned decode(struct ib *, unsigned *);\n"
                "int main(void)\n"
                "{\n"
                "  static uint32_t buf[64];\n"
                "  struct ib ib = { buf, 0, 64 };\n"
                "  unsigned np = 0, fails = 0, checks = 0;\n"
                + y_correr_paquetes() +
                "  printf(\"%u checks, %u failures\\n\", checks, fails);\n"
                "  return fails ? 1 : 0;\n"
                "}\n")
        rc, o, e = _sh(["gcc", "-std=gnu11", "-Wall", "-Wextra", "-o", "t", "k.c", "t.c"], cwd=d)
        if rc != 0:
            return None, e
        rc, o, e = _sh([os.path.join(d, "t")], cwd=d)
        m = re.search(r"(\d+) checks, (\d+) failures", o)
        if not m:
            return None, o
        return (int(m.group(1)), int(m.group(2))), ""

    bueno = ("  emit(&ib, 0x15u, 3u);\n"
             "  checks++;\n"
             "  if (ib.n != 5u) { fails++; }\n"
             "  checks++;\n"
             "  if (decode(&ib, &np) != 0 || np != 1u) { fails++; }\n")
    r, err = construir(lambda: bueno)
    vectores.append(("el codigo sin mutar pasa", r == (2, 0), r or err))

    # mutante 1: el count no cuadra con lo escrito -> tiene que caer
    src = open(os.path.join(d, "k.c")).read()
    with open(os.path.join(d, "k.c"), "w") as f:
        f.write(src.replace("ib->b[ib->n++] = hdr(op, cnt);",
                            "ib->b[ib->n++] = hdr(op, cnt + 1u);"))
    r, err = construir(lambda: bueno)
    vectores.append(("un count que no cuadra lo cae el test", r is not None and r[1] > 0, r or err))
    with open(os.path.join(d, "k.c"), "w") as f:
        f.write(src)

    # mutante 2: un valor de payload equivocado -> NO tiene que caer, porque
    # el decodificador no sabe semantica de payload. Y el arnes tiene que
    # reportarlo como superviviente, no como fallo del arnes.
    with open(os.path.join(d, "k.c"), "w") as f:
        f.write(src.replace("ib->b[ib->n++] = 0xAAu;", "ib->b[ib->n++] = 0xBBu;"))
    r, err = construir(lambda: bueno)
    vectores.append(("un payload distinto no lo ve el decodificador",
                     r is not None and r[1] == 0, r or err))
    with open(os.path.join(d, "k.c"), "w") as f:
        f.write(src)

    # el anclaje tiene que ser unico: si el arnés muta el fichero equivocado
    # mide otra cosa y no lo dice
    from mutate import CATALOGO as _c  # noqa: E402
    dups = [m["nombre"] for m in _c
            if open(os.path.join(RAIZ, m["fichero"]),
                     encoding="utf-8").read().count(m["buscar"]) != 1]
    vectores.append(("todos los anclajes del catalogo son unicos en su fichero",
                     not dups, dups or "0 duplicados"))

    # La convencion de marcado es la que sostiene el reparto de atribucion, asi
    # que tiene que comprobarse contra el binario, no contra el fuente: si una
    # llamada a un helper se anade sin prefijo, el reparto empieza a mentir y
    # nada mas lo detecta.
    preparar()
    binario = os.path.join(SCRATCH, "07-DRIVER/tests", "test_pm4")
    _, out, err = _sh([binario])
    marcados = len([l for l in out.splitlines() if "[ OK ] [IB] " in l or "[FAIL] [IB] " in l])
    fuente = os.path.join(RAIZ, "07-DRIVER/tests/test_pm4.c")
    llamadas = len(re.findall(r"check_ib(?:_hasta_no_pm4)?\(\s*\"\[IB\]",
                             open(fuente, encoding="utf-8").read()))
    vectores.append(("todo check de decodificacion lleva el marcador [IB]",
                     marcados > 0 and marcados == llamadas,
                     "marcados=%d llamadas=%d" % (marcados, llamadas)))

    # un anclaje ausente tiene que ser ERROR, no un CAER ni un VIVIR. Esto es
    # lo que evita que un catalogo con un anclaje mal escrito mida otra cosa y
    # no lo diga: sin este vector, dispatch_token_fuera -- que no era unico --
    # habria Mutado el primer sitio que casara y emitido un veredicto.
    malo = dict(nombre="anclaje_inexistente", fichero="07-DRIVER/kernel/rx550_pm4.c",
                buscar="UNA_CADENA_QUE_NO_EXISTE_EN_NINGUN_FICHERO_12345",
                cambio="x", esperado="CAER", nota="vector del arnes")
    r = correr_mutante(malo)
    vectores.append(("un anclaje ausente se reporta como error, no como veredicto",
                     "error" in r and "anclaje" in r["error"], r))
    shutil.rmtree(d, ignore_errors=True)

    fallos = sum(1 for _, ok, _ in vectores if not ok)
    print("mutate.py selftest")
    for nombre, ok, det in vectores:
        print("  %s %s%s" % ("OK  " if ok else "FAIL", nombre,
                             "" if ok else "   -- %r" % (det,)))
    print("RESULT: %s (%d vectores)" % ("PASS" if not fallos else "FAIL",
                                        len(vectores)))
    return 0 if not fallos else 1


def main():
    ap = argparse.ArgumentParser(description="prueba de mutacion del encoder PM4")
    ap.add_argument("--list", action="store_true", help="lista el catalogo")
    ap.add_argument("--run", metavar="NOMBRE", help="corre un mutante")
    ap.add_argument("--all", action="store_true", help="corre todos")
    ap.add_argument("--json", action="store_true", help="salida JSON")
    ap.add_argument("--verboso", action="store_true", help="incluye el log de build")
    ap.add_argument("--selftest", action="store_true", help="comprueba el arnes")
    a = ap.parse_args()

    if a.selftest:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        return selftest()

    if a.list:
        for m in CATALOGO:
            print("  %-30s %-9s %s" % (m["nombre"], m["esperado"], m["nota"]))
        print("\n  %d mutantes" % len(CATALOGO))
        return 0

    if a.run:
        sel = [m for m in CATALOGO if m["nombre"] == a.run]
        if not sel:
            print("mutante desconocido: %s" % a.run, file=sys.stderr)
            return 2
        res = [correr_mutante(sel[0], a.verboso)]
    elif a.all:
        res = []
        for m in CATALOGO:
            r = correr_mutante(m, a.verboso)
            res.append(r)
            if not a.json:
                print("  %-32s %-12s %-4s %-8s %s"
                  % (r["nombre"], r.get("veredicto", r.get("error", "")),
                     r.get("n_fallos", "?"),
                     "DECODIF" if r.get("cae_el_decodificador") else "cabecera",
                     r.get("porque", "")[:52]), flush=True)
    else:
        ap.print_help()
        return 2

    if a.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif not a.all:
        for r in res:
            print(json.dumps(r, indent=2, ensure_ascii=False))

    malas = [r for r in res if r.get("veredicto") != "CONFIRMADO"]
    return 1 if malas else 0


if __name__ == "__main__":
    sys.exit(main())
