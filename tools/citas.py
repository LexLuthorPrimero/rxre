#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
citas.py -- verificador automatico de las citas de codigo fuente que hay en los
hallazgos.

POR QUE EXISTE
--------------
`cut -c1-104` me corto la linea 1675 de polaris10_smumgr.c justo donde estaba la
division, y de ahi salieron TRES hallazgos cuantitativos invalidos (931, 947, 956).
Todosgive un numero plausible. Ninguno fallo el control de dominio.

Un numero plausible que sale de una linea cortada no es un dato dudoso: es una
aritmetica distinta. Asi que hace falta un mecanismo que convierta «he citado codigo»
en algo comprobable, y no en algo que hay que mirar a ojo.

QUE HACE
--------
Extrae de cada hallazgo las lineas que parecen codigo C citado y comprueba, para
cada una, si es subcadena de alguna linea real del corpus. Lo que no encaja se
reporta como DISCREPANTE, con el fichero y la linea mas cercana que si encaja.

No juzga si el codigo dice lo que creo que dice. Comprueba que lo que escribi
existe, que es exactamente lo que evita el modo de fallo del corte.

ESTADO: VALIDATED con --self-test
WORK_CLASS: READ_ONLY. Solo lee ficheros.
"""

import io
import os
import re
import sys
import glob

VERSION = "1.2.0"

# El corpus propio. Unica fuente de verdad para el layout y para el codigo.
CORPUS_REL = "RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd"

# Una linea citada se normaliza:
#   - tabs y espacios multiples -> un espacio
#   - el backslash de continuacion de linea FINAL se quita
#     porque no es contenido: una cita que lo omite sigue siendo fiel,
#     y sin esta quitacion toda cita de una linea partida por \
#     pareceria truncada. Solo se quita al final, para no romper la
#     deteccion de un corte a media linea.
def norm(s):
    s = re.sub(r"[ \t]+", " ", s).strip()
    if s.endswith("\\"):
        s = s[:-1].rstrip()
    return s

# Lineas que en un bloque de codigo son claramente C, no prosa ni tablas.
def parece_c(s):
    if not s or s.startswith(("#", ">", "|")):
        return False
    if "$" in s or "==>" in s:
        return False
    return (";" in s) or ("{" in s) or ("}" in s) or \
           bool(re.match(r"^\s*[a-z_][a-zA-Z0-9_]*\s*=\s*[^=]", s)) or \
           ("(" in s and ")" in s and "=" in s)


class Corpus(object):
    def __init__(self, raiz):
        self.lineas = []           # (ruta_relativa, n_linea, texto_normalizado)
        for pat in ("**/*.c", "**/*.h"):
            for f in glob.glob(os.path.join(raiz, pat), recursive=True):
                try:
                    with io.open(f, encoding="utf-8", errors="replace") as fh:
                        for i, l in enumerate(fh, 1):
                            n = norm(l)
                            if n:
                                rel = os.path.relpath(f, raiz)
                                self.lineas.append((rel, i, n))
                except (IOError, OSError):
                    pass
        self.lineas.sort(key=lambda t: (t[0], t[1]))

    def verificar(self, cita):
        """Clasifica una cita frente al corpus.

        ESTE ES EL CORAZON DE LA HERRAMIENTA, Y HAY UNA TRAMPA:

        una linea truncada ES subcadena de la linea real. Un 'cita in linea'
        devuelve True tanto para una cita fiel como para un corte a media linea,
        y por tanto NO PUEDE distinguir el caso que motivo esta herramienta.
        La comprobacion tiene que mirar donde TERMINA la cita: si termina donde
        termina la linea real, la cita es fiel; si termina antes, esta cortada.

        devuelve (estado, ruta, linea, fraccion_cubierta)
        estados: COMPLETA  la cita es la linea entera
                 SUFIJO    la cita llega hasta el final de la linea
                 PARCIAL   coincide pero no llega al final: cita un trozo
                 AUSENTE   no aparece en ninguna linea
        """
        mejor = ("AUSENTE", None, None, 0.0)
        for (r, n, t) in self.lineas:
            pos = t.find(cita)
            if pos < 0:
                continue
            cub = (pos + len(cita)) / float(len(t))
            if pos == 0 and len(cita) == len(t):
                cand = ("COMPLETA", r, n, 1.0)
            elif pos + len(cita) == len(t):
                cand = ("SUFIJO", r, n, cub)
            else:
                cand = ("PARCIAL", r, n, cub)
            if cand[3] > mejor[3]:
                mejor = cand
        return mejor

    def coincide(self, cita):
        """Compatible: True si la cita aparece en el corpus de cualquier modo."""
        return self.verificar(cita)[0] != "AUSENTE"

    def mas_cercana(self, cita, prefijo=6):
        """La linea real que mas se le parece, por prefijo comun mas largo."""
        mejor = (0, None, None)
        for (r, n, t) in self.lineas:
            if not prefijo:
                break
            k = 0
            while k < min(len(cita), len(t), 60) and cita[k] == t[k]:
                k += 1
            if k > mejor[0]:
                mejor = (k, r, n)
        return mejor


def lineas_de_bloque(lineas):
    """Rendere las lineas que estan dentro de ``` ... ```"""
    dentro = False
    for i, l in enumerate(lineas, 1):
        if l.strip().startswith("```"):
            dentro = not dentro
            continue
        if dentro:
            yield i, l


def auditar(fichero_hallazgo, corpus):
    """Devuelve las citas que NO son fieles de un hallazgo.

    Solo se reportan TRUNCADAS (PARCIAL que no llega al final) y AUSENTES.
    Una cita PARCIAL que llega al final es SUFIJO y es legitima: citar el final
    interesante de una linea larga no es un error.
    """
    txt = io.open(fichero_hallazgo, encoding="utf-8").read().split("\n")
    malas = []
    for (n_linea_h, l) in lineas_de_bloque(txt):
        cita = norm(re.sub(r"^\s*\d+\s*\|\s*", "", l))
        cita = re.sub(r"^\d+\s+", "", cita)
        if not parece_c(cita):
            continue
        estado, r, n, cub = corpus.verificar(cita)
        if estado in ("COMPLETA", "SUFIJO"):
            continue
        if estado == "PARCIAL":
            # llega al final de OTRA linea pero no de la que empieza: esta cortada.
            # Es el caso CARO (mas_cercana recorre el corpus entero) y tambien el
            # RARO, asi que se calcula solo aqui.
            k, r2, n2 = corpus.mas_cercana(cita)
            malas.append((n_linea_h, cita, "TRUNCADA", r2, n2, cub))
        else:
            # AUSENTE es el caso FRECUENTE (mi propia salida, mis calculos, mis
            # reescrituras deliberadas). Buscarle la linea mas cercana aqui cuesta
            # O(n) por cita y no aporta nada: se reporta sin localizar, que es
            # informacion suficiente. Mantenerlo barato es lo que hace la auditoria
            # utilizable: en v1.1.0 esto agotaba el tiempo.
            malas.append((n_linea_h, cita, "AUSENTE", None, None, 0.0))
    return malas


# --------------------------------------------------------------------------
# SELF-TEST
# --------------------------------------------------------------------------
CASOS_SELFTEST_MINIMO = 18


def self_test(raiz_corpus, raiz_hallazgos):
    res = []

    def ok(nombre, cond, detalle=""):
        res.append((nombre, bool(cond), detalle))

    c = Corpus(raiz_corpus)
    ok("el corpus se cargo", len(c.lineas) > 10000, "%d lineas" % len(c.lineas))
    ok("no hay lineas vacias", all(t for (_r, _n, t) in c.lineas), "")

    # una cita real, textual, debe coincidir
    real = "volt_without_cks = (uint32_t)((2416794800U + (sclk_table->entries[i].clk/100) * 1476925/10 - (ro - 50) * 1000000) /"
    ok("cita textual real coincide", c.verificar(real)[0] in ("COMPLETA", "SUFIJO"), c.verificar(real)[0])
    TRUNC = "volt_without_cks = (uint32_t)((2753594000U + (sclk_table->entries[i].clk/100) * 136"
    ok("la TRAMPA: la truncada es subcadena de la real",
       c.coincide(TRUNC), "por eso el matching por subcadena no puede bastar")
    ok("pero verificar() la marca TRUNCADA/PARCIAL",
       c.verificar(TRUNC)[0] == "PARCIAL", c.verificar(TRUNC)[0])
    ok("y no llega al final de la linea", c.verificar(TRUNC)[3] < 1.0,
       "cubierta %.2f" % c.verificar(TRUNC)[3])
    ok("una inventada es AUSENTE", c.verificar("esto_no_existe_jamas_xyz")[0] == "AUSENTE", "")
    ok("una cita SUFIJO es legitima",
       c.verificar("* 136418 - (ro - 70) * 1000000) /")[0] in ("SUFIJO", "COMPLETA"),
       c.verificar("* 136418 - (ro - 70) * 1000000) /")[0])

    # la cita truncada debe encontrar la linea real que la contiene
    k, r, n = c.mas_cercana("volt_without_cks = (uint32_t)((2753594000U + (sclk_table->entries[i].clk/100) * 136")
    ok("la truncada localiza la linea real", r is not None and "polaris10_smumgr.c" in r,
       "%s:%s" % (r, n))
    ok("el prefijo comun es largo", k >= 60, "k=%d" % k)

    # normalizacion: tabs y espacios cuentan igual
    ok("norm() unifica tabs y espacios",
       norm("\t\tif  (a)  {") == norm("if (a) {"), norm("\t\tif  (a)  {"))

    # el clasificador de prosa
    ok("descarta prosa", not parece_c("el valor de la tension es 812 mV"), "")
    ok("descarta tablas", not parece_c("| nivel | MHz |"), "")
    ok("descarta lineas con $", not parece_c("cadena $PATH"), "")
    ok("acepta una asignacion", parece_c("volt_offset = 0;"), "")
    ok("acepta una llamada", parece_c("smu7_copy_bytes_to_smc(hwmgr, x);"), "")

    # auditar un hallazgo real y ver que encuentra la cita truncada
    h = None
    for cand in ("957-las-formulas-eran-divisiones.md",):
        p = os.path.join(raiz_hallazgos, cand)
        if os.path.isfile(p):
            h = p
    if h:
        malas = auditar(h, c)
        ok("el hallazgo 957 se audita", True, "%d discrepancias" % len(malas))
        truncada = [m for m in malas if "2753594000U" in m[1] and m[2] == "TRUNCADA"]
        ok("detecta la cita truncada que cito en 929", len(truncada) >= 1,
           "%d encontradas" % len(truncada))
    else:
        ok("el hallazgo 957 existe", False, h or "no encontrado")

    if len(res) < CASOS_SELFTEST_MINIMO:
        res.append(("SELF_TEST_MUST_EXCEED_FIXTURE", False,
                    "solo %d casos, minimo %d" % (len(res), CASOS_SELFTEST_MINIMO)))
    else:
        res.append(("SELF_TEST_MUST_EXCEED_FIXTURE", True,
                    "%d casos > minimo %d" % (len(res), CASOS_SELFTEST_MINIMO)))
    return res


def main(argv):
    a = argv[1:]
    if "--version" in a:
        print("citas %s" % VERSION)
        return 0
    raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    corpus = os.path.join(raiz, CORPUS_REL)
    hall = os.path.join(raiz, "06-INGENIERIA-INVERSA", "findings")
    if not os.path.isdir(corpus):
        print("citas: no encuentro el corpus en %s" % corpus, file=sys.stderr)
        return 2

    if "--self-test" in a:
        res = self_test(corpus, hall)
        fallos = sum(1 for (_n, b, _d) in res if not b)
        for (n, b, d) in res:
            print("    %-4s %-44s %s" % ("ok" if b else "FALLO", n, d))
        print("    ---> %d casos, %d fallos" % (len(res), fallos))
        return 0 if fallos == 0 else 1

    c = Corpus(corpus)
    patron = re.compile(r"^9\d\d-")
    objetivos = sorted(f for f in os.listdir(hall) if patron.match(f))
    if a and not a[0].startswith("-"):
        objetivos = [a[0]]
    total = 0
    for f in objetivos:
        malas = auditar(os.path.join(hall, f), c)
        if not malas:
            continue
        total += len(malas)
        print("    %s  (%d discrepancias)" % (f, len(malas)))
        for (n, cita, est, r, nn, cub) in malas[:6]:
            print("      hall:%-5d %-9s -> %s:%s" % (n, est, r, nn))
            print("        citado: %s" % cita[:96])
    print("    ---> %d hallazgos auditados, %d citas discrepantes" % (len(objetivos), total))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
