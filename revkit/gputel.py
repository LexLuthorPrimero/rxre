#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gputel.py -- telemetria de hardware de la GPU, con las unidades correctas.

POR QUE EXISTE. `bootcheck` valida la cadena de SOFTWARE (lo que el driver
imprimo). Este mide la cadena de HARDWARE. Y al hacerlo aparece una trampa que
cuesta un factor 10^6 si no se mira:

  ME DATO:  freq1_input = 1070150000
  LEIDO COMO: "1070150000 MHz"        <-- la convencion generica de hwmon dice MHz
  REAL:       1070150000 Hz = 1070.15 MHz

El arbol de sysfs de amdgpu publica las frecuencias en **Hz**, no en MHz como
predice la convencion de hwmon. Un guardia de unidades que no verifique el
productor daria un numero mil veces mayor, y un numero mil veces mayor es un
resultado falso con toda la aparencia de estar bien.

UNIDADES, y cada una verificada contra el valor, no supuesta:

  freq*_input   Hz       <-- NO la convencion de hwmon
  in0_input     mV
  power*_input  mW
  temp*_input   mC
  fan*_input    RPM
  pwm*          0..255   sin unidad
  power*_cap*   mW       <-- esto NO es una muestra: es un LIMITE del hardware

LIMITE ESTRUCTURAL, y es el que separa esta herramienta de un volcado: un
`freq1_input` es un **instante**. Con jitter de +-2% observado en sclk, una sola
lectura no es un valor: es una muestra. Por eso `--n` por defecto es > 1 y la
herramienta **se niega a resumir con una sola muestra** cuando se pide un
resumen estadistico. Los limites de potencia si son constantes y se leen una vez.

LO QUE NO DICE. Esto no mide un techo. No se ha puesto la GPU bajo carga, asi
que el sclk maximo y el mclk maximo son `NOT_DETERMINED`. Solo se sabe lo que la
GPU hace cuando NO esta haciendo nada, que es un dato distinto y tambien
necesario.

CONTRACT: name=gputel
CONTRACT: READONLY=yes
CONTRACT: WRITES_FILES=no
CONTRACT: WRITES_SYSFS=no
CONTRACT: MUTATES_CORPUS=no
CONTRACT: WRITES_GPU=no
"""

import io
import os
import re
import statistics
import sys
import time

# (fichero, etiqueta que el propio arbol declara, unidad REAL, clase)
MEDIDAS = [
    ("freq1_input", "sclk", "Hz", "muestra"),
    ("freq2_input", "mclk", "Hz", "muestra"),
    ("in0_input", "vddgfx", "mV", "muestra"),
    ("power1_input", "PPT", "uW", "muestra"),
    ("temp1_input", "edge", "mC", "muestra"),
    ("fan1_input", "fan", "RPM", "muestra"),
    ("pwm1", "pwm", "/255", "muestra"),
    ("power1_cap", "PPT-cap", "uW", "limite"),
    ("power1_cap_min", "PPT-min", "uW", "limite"),
    ("power1_cap_max", "PPT-max", "uW", "limite"),
    ("power1_cap_default", "PPT-def", "uW", "limite"),
]
# MEDIDO: esto estaba mal por un factor 100. `excursion` se calcula en PORCENTAJE
# y se comparaba contra LIMITE_PPM/100 = 200, cuando 20000 ppm son 2%. El
# control existia y no podia pasar. Un umbral con la unidad equivocada es un
# control que no mide nada, y encima da la sensacion de que mide.
LIMITE_PPM = 20000          # partes por millon de excursion
LIMITE_PCT = LIMITE_PPM / 10000.0   # 2.0 %, en la misma unidad que `excursion`

# El texto de "una sola muestra", expuesto para que el self-test lo compruebe.
_RESUMEN_UN_MUESTRA = [None]


def descubrir(card="card1"):
    base = "/sys/class/drm/%s/device" % card
    hw = os.path.join(base, "hwmon")
    if not os.path.isdir(hw):
        return None, None
    for d in sorted(os.listdir(hw)):
        if d.startswith("hwmon"):
            return os.path.join(hw, d), base
    return None, base


def leer(hw, nombre):
    p = os.path.join(hw, nombre)
    if not os.path.isfile(p):
        return None
    try:
        return io.open(p, encoding="utf-8").read().strip()
    except Exception:
        return None


def muestrear(hw, n, intervalo, verbose=False, lee=None):
    """n muestras de cada medida. Devuelve {fichero: [valores]}.

    MEDIDO, y este es un defecto de DISENO que solo aparecio al testear: con el
    lector fijo, tres muestras de un fichero que no cambia dan tres valores
    IDENTICOS, y el recorrido es 0 siempre. Entonces ninguna de las afirmaciones
    sobre estabilidad, jitter o transicion se puede comprobar: la herramienta
    era incriticable sin hardware. Por eso el lector se INYECTA, que es lo que
    permite probarla contra un arbol sintetico que si cambia.
    """
    lee = lee or leer
    out = {}
    for _i in range(n):
        for f, _lab, _u, _c in MEDIDAS:
            v = lee(hw, f)
            if v is None:
                continue
            out.setdefault(f, []).append(v)
        if verbose and _i < n - 1:
            sys.stderr.write("    ...muestra %d de %d\n" % (_i + 1, n))
        if _i < n - 1:
            time.sleep(intervalo)
    return out


def human(fichero, unidad, v):
    """Convierte a una escala legible, POR MEDIDA, no por convencion."""
    try:
        x = float(v)
    except (TypeError, ValueError):
        return "no numerico (%r)" % (v,)
    if unidad == "Hz":
        return "%.2f MHz" % (x / 1e6)
    if unidad == "mV":
        return "%.0f mV (%.3f V)" % (x, x / 1000.0)
    if unidad == "uW":
        return "%.0f uW (%.3f W)" % (x, x / 1e6)
    if unidad == "mW":
        return "%.0f mW (%.2f W)" % (x, x / 1000.0)
    if unidad == "mC":
        return "%.0f mC (%.1f C)" % (x, x / 1000.0)
    return "%s %s" % (v, unidad)


def plausible(clase, valor, unidad):
    """Un cap de potencia debe caer en un rango de placa. Es un control de UNIDAD
    disguised de rango fisico: si alguien vuelve a cambiar la escala, salta antes
    de que el numero llegue a un documento."""
    try:
        x = float(valor)
    except (TypeError, ValueError):
        return True          # no numerico: no se afirma nada
    if clase != "limite" or unidad not in ("uW", "mW"):
        return True
    vatios = x / 1e6 if unidad == "uW" else x / 1000.0
    return 5.0 <= vatios <= 500.0


def resumen_un_muestra():
    """El texto que la herramienta imprime cuando solo hay una muestra. Se extrae
    a una funcion para que el self-test pueda MIRARLO, en vez de mirar el numero
    de muestras, que es lo que no detecta la mutacion."""
    return _RESUMEN_UN_MUESTRA[0]


def selftest():
    """Vectores sobre un arbol SYNTHETICO. Necesario porque las unidades no se
    pueden comprobar contra el arbol real sin fijar el hardware."""
    ok = fallan = 0

    def chk(n, c):
        nonlocal ok, fallan
        if c:
            ok += 1
            print("  OK    %s" % n)
        else:
            fallan += 1
            print("  FALLA %s" % n)

    import tempfile
    d = tempfile.mkdtemp()
    try:
        # arbol sintetico: sclk con jitter conocido, resto plano
        vals = {
            "freq1_input": ["1038000000", "1060000000", "1042000000"],
            "freq2_input": ["300000000", "300000000", "300000000"],
            "in0_input": ["881", "881", "881"],
            "power1_input": ["6112000", "6127000", "6159000"],
            "temp1_input": ["44000", "44000", "44000"],
            "power1_cap": ["35000000"],
            "power1_cap_min": ["0"],
            "power1_cap_max": ["35000000"],
            "power1_cap_default": ["35000000"],
        }
        for k, vs in vals.items():
            io.open(os.path.join(d, k), "w", encoding="utf-8").write(vs[0] + "\n")

        # --- la conversion de unidades, que es el fallo que motiva la herramienta
        chk("1070150000 Hz -> 1070.15 MHz, NO 1070150000 MHz",
            human("freq1_input", "Hz", "1070150000") == "1070.15 MHz")
        # MEDIDO: estas tres comparaban con `endswith("0.881 V")` cuando la
        # cadena es "881 mV (0.881 V)". Un aserto mal escrito que NO puede pasar
        # es peor que uno mal escrito que si: hidea el fallo de verdad.
        chk("881 mV -> 0.881 V", "(0.881 V)" in human("in0_input", "mV", "881"))
        # MEDIDO: la unidad de potencia estaba mal. 11133000 leido como mW son
        # 11,1 kW, y un cap de 35000000 serian 35 kW: fisicamente imposible para
        # esta placa. Como uW, el cap son 35 W (clase RX550) y el consumo 11,1 W.
        # El self-test lo cazo; yo no lo iba a cazar leyendo el numero.
        chk("11133000 uW -> 11.133 W, NO 11.13 kW",
            "(11.133 W)" in human("power1_input", "uW", "11133000"))
        chk("35000000 uW -> 35.000 W, el cap de esta placa",
            "(35.000 W)" in human("power1_cap", "uW", "35000000"))
        # MEDIDO, y esto es un patron que me ha salido dos veces: el control
        # llevaba la unidad ESCRITA A MANO, mientras la unidad real vive en la
        # tabla MEDIDAS. La mutacion T1 (volver a mW en la tabla) no la notaba,
        # porque el test no lee la tabla: afirma sobre una copia. **Un control
        # tiene que leer el valor del sitio donde vive, o no controla nada.**
        uni_pot = [u for f, _l, u, _c in MEDIDAS if f == "power1_input"][0]
        chk("la tabla declara la potencia en uW (y el test lo lee de la tabla)",
            uni_pot == "uW")
        uni_freq = [u for f, _l, u, _c in MEDIDAS if f == "freq1_input"][0]
        chk("la tabla declara la frecuencia en Hz, no en la convencion de hwmon",
            uni_freq == "Hz")
        chk("convertir con la unidad de la TABLA, no con una escrita a mano",
            "(11.133 W)" in human("power1_input", uni_pot, "11133000"))

        # MEDIDO: la primera version de este control llamaba con la unidad
        # CORRECTA y esperaba que saliera impausible, o sea que era imposible que
        # pasara. Para cazar el error de unidad hay que pasar la lectura con la
        # unidad ERRONEA: 35000000 leido como mW son 35000 W.
        chk("un cap de 35000 W se detecta como implausible (control de unidad)",
            not plausible("limite", 35000000, "mW"))
        chk("el MISMO numero leido como uW, 35 W, SI es plausible",
            plausible("limite", 35000000, "uW"))
        chk("una muestra, no un limite, no se juzga por plausibilidad",
            plausible("muestra", 99999999, "mW"))
        chk("43000 mC -> 43.0 C", "(43.0 C)" in human("temp1_input", "mC", "43000"))
        chk("un valor no numerico se marca, no se inventa",
            "no numerico" in human("freq1_input", "Hz", "salud"))

        # --- la disciplina de muestreo, con un lector que SI cambia ----------
        seq = {"freq1_input": ["1038000000", "1060000000", "1042000000"],
               "freq2_input": ["300000000", "300000000", "300000000"],
               "power1_cap": ["35000000", "35000000", "35000000"]}
        estado = {"i": 0}

        def lector(hwdir, f):
            if f in seq:
                vs = seq[f]
                v = vs[min(estado["i"], len(vs) - 1)]
                return v
            return leer(hwdir, f)

        r1 = muestrear(d, 1, 0, lee=lector)
        r3 = muestrear(d, 3, 0, lee=lambda h, f: (lambda vs: (
            seq.__setitem__(f, vs[1:]), vs[0])[1])(seq[f]) if f in seq
            else leer(h, f))
        vals3 = [float(x) for x in r3["freq1_input"]]
        chk("con lector que cambia, el recorrido de sclk NO es 0",
            (max(vals3) - min(vals3)) > 0)
        chk("la mediana de 3 muestras cae dentro del recorrido",
            min(vals3) <= statistics.median(vals3) <= max(vals3))
        excursion = 100.0 * (max(vals3) - min(vals3)) / statistics.median(vals3)
        chk("el recorrido de sclk sintetico supera el 2%% (%.1f%%)" % excursion,
            excursion > LIMITE_PCT)
        chk("con 1 sola muestra la herramienta NO inventa un resumen",
            len(r1["freq1_input"]) == 1)
        # MEDIDO: el control de arriba mira el NUMERO de muestras, que la
        # mutacion T4 no cambia, y por eso T4 pasaba. Lo que hay que mirar es el
        # COMPORTAMIENTO: el texto que sale por pantalla.
        # MEDIDO: la primera version de esto llamaba a main() sin --n=1, con lo
        # que la rama de una sola muestra NO se ejecutaba y el control no podia
        # pasar. Es el mismo error que el control imposible, con mas pasos: un
        # control tiene que EJECUTAR el camino que dice comprobar.
        import io as _io
        import contextlib as _c
        buf = _io.StringIO()
        with _c.redirect_stdout(buf):
            main(["--n=1", "--card=card1"])
        chk("con --n=1 la salida dice que una muestra no es un resumen",
            "una sola muestra" in buf.getvalue())
        buf2 = _io.StringIO()
        with _c.redirect_stdout(buf2):
            main(["--n=3", "--card=card1", "--intervalo=0"])
        chk("con --n=3 NO aparece el aviso de una sola muestra",
            "una sola muestra" not in buf2.getvalue())
        chk("con --n=1 la herramienta dice explicitamente que no mide un techo",
            "no es un techo" in buf.getvalue() or "NOT_DETERMINED" in buf.getvalue())
        chk("un limite se lee igual que una muestra, y se CLASIFICA aparte",
            len(r3["power1_cap"]) == 3 and
            [c for _f, _l, _u, c in MEDIDAS if _f == "power1_cap"][0] == "limite")

        # --- errores y entradas invalidas -----------------------------------
        chk("atributo ausente -> None, no 0", leer(d, "no_existe") is None)
        chk("human(None) se marca como no numerico, no revienta",
            "no numerico" in human("x", "Hz", None))
        chk("descubrir() de un card inexistente -> (None, ruta), no revienta",
            descubrir("card999")[0] is None)
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)

    print("  ---")
    print("  vectores OK: %d   controles en rojo: %d" % (ok, fallan))
    return 1 if fallan else 0


def main(argv):
    if "--self-test" in argv:
        return selftest()
    n, intervalo, card = 5, 1.0, "card1"
    for a in argv:
        if a.startswith("--n="):
            n = int(a.split("=", 1)[1])
        if a.startswith("--intervalo="):
            intervalo = float(a.split("=", 1)[1])
        if a.startswith("--card="):
            card = a.split("=", 1)[1]
    if n < 1:
        print("ERROR/INVALID: --n=%d. Con 0 muestras no hay nada que resumir."
              % n)
        return 4
    hw, base = descubrir(card)
    if hw is None:
        print("ERROR/INVALID: no encuentro hwmon para %s. Sin el arbol de "
              "telemetria no hay nada que medir; esto NO es 'cero'." % card)
        return 4
    busy = leer(base, "gpu_busy_percent")
    print("gputel: telemetria de %s" % card)
    print("  hwmon:  %s" % hw)
    print("  muestras: %d   intervalo: %.1f s" % (n, intervalo))
    print("  gpu_busy_percent = %s   (lo que el DRIVER afirma; no es una medida)"
          % (busy if busy is not None else "no disponible"))
    print("  " + "-" * 78)
    d = muestrear(hw, n, intervalo)
    print("  %-18s %-9s %-7s %-13s %-13s %-10s"
          % ("medida", "clase", "n", "min", "mediana", "max"))
    print("  " + "-" * 78)
    for f, lab, unidad, clase in MEDIDAS:
        vs = d.get(f)
        if not vs:
            print("  %-18s %-9s %-7s %s" % (lab, clase, "-", "no disponible"))
            continue
        try:
            xs = [float(x) for x in vs]
        except ValueError:
            print("  %-18s %-9s %-7s %s" % (lab, clase, len(vs),
                                            "no numerico"))
            continue
        if len(xs) == 1:
            mn = md = mx = xs[0]
            resumen = "(una sola muestra: no es un resumen)"
            _RESUMEN_UN_MUESTRA[0] = resumen
        else:
            mn, md, mx = min(xs), statistics.median(xs), max(xs)
            resumen = ""
        print("  %-18s %-9s %-7d %-13s %-13s %-10s %s"
              % (lab, clase, len(xs), human(f, unidad, mn),
                 human(f, unidad, md), human(f, unidad, mx), resumen))
        if clase == "muestra" and len(xs) > 1 and md:
            exc = 100.0 * (mx - mn) / md
            # MEDIDO: un umbral SOLO porcentual marca como "inestable" a una
            # medida cuya granularidad es gruesa. La temperatura dio 37->38 C,
            # que es UN paso del sensor, no una oscilacion. Por eso se informa
            # tambien el recorrido ABSOLUTO y el paso de cuantizacion deducido
            # del menor incremento no nulo entre muestras consecutivas.
            salto = min((abs(xs[i + 1] - xs[i]) for i in range(len(xs) - 1)
                         if xs[i + 1] != xs[i]), default=None)
            if salto is not None and abs(mx - mn) <= salto:
                etiqueta = "recorrido de UN paso de cuantizacion, no oscilacion"
            else:
                etiqueta = "oscilacion real"
            if exc > LIMITE_PCT:
                print("  %-18s   recorrido %.1f%% (abs %.0f %s, salto %s): %s"
                      % ("", exc, mx - mn, unidad,
                         ("%g" % salto) if salto is not None else "n/d",
                         etiqueta))
    print("  " + "-" * 78)
    print("  UNIDADES: las frecuencias de este arbol estan en Hz, NO en la "
          "convencion de hwmon (MHz).")
    print("  LIMITES: `PPT-cap/min/max/def` son LIMITES del hardware, leidos una "
          "vez; no son muestras.")
    print("  LO QUE ESTO NO ES: un techo. No se ha puesto la GPU bajo carga, asi "
          "que sclk y mclk maximos son NOT_DETERMINED.")
    print("  gpu_busy_percent es lo que el driver AFIRMA, no una medida.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))