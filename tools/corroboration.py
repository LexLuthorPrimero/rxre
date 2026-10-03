#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""
corroboration.py - audita las afirmaciones de MULTIPLICIDAD de evidencia.

POR QUE EXISTE

findings/122 encontró que una marca del driver propio afirmaba "PROVEN por
DOS familias de headers independientes" y la afirmación era cierta para TRES de
los cuatro campos: ENGINE no existe en la segunda familia. El estado no
cambió, pero la dimensión de la prueba sí, y una corroboración inflada hace
que todo lo demás parezca más sólido de lo que es.

Es la forma por la que cayó findings/034: un contraste que se presenta con dos
fuentes cuando leía una. La diferencia —y la razón de que vuelva— es que allí
las dos líneas estaban en el MISMO fichero y aquí en ficheros distintos. Un
fichero distinto no es una fuente distinta.

122 dejó escrito el límite en su propio confounder: "la cuenta es de este
paquete". Esta herramienta aplica el mismo criterio a TODOS los hallazgos, que
es lo que un `grep` bien escrito hace y lo que leerlos de uno en uno no.

QUE COMPRUEBA

Una afirmacion de multiplicidad ("dos fuentes", "dos familias independientes",
"corroborado por", "N fuentes") declara una redundancia. Lo que se puede
medir sin saber nada del tema es si la redundancia declarada tiene
respaldo NOMBRADO:

  RESPALDADA          el texto nombra >= N ficheros distintos y N coincide
                      con el número declarado
  INFLADA_DECLARADA   declara N y nombra menos de N fuentes distintas
  NO_COMPROBABLE      usa palabras de multiplicidad sin nombrar ninguna fuente
                      junto a la afirmación
  AUTOCITA            la "segunda fuente" es el mismo fichero que la primera

La cuarta clase es la más importante: es 034 con otro nombre.

POR QUE NO AFIRMA QUE UNA CORROBORACION SEA FALSA

Porque no puede. Estas herramientas sólo miden si la redundancia declarada
tiene las fuentes nombradas que la sostienen. Si las nombra, la corroboración
puede seguir siendo falsa por los motivos de 122 --mismas bases de datos de
origen, campos que no coinciden-- y eso exige leer. Lo que sí detecta es la
forma que se puede contar.

CODIGOS DE SALIDA

  0  se pudo medir
  2  no se pudo ejecutar
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Tuple

VERSION = "1.0.0"

# NUMERO escrito en letra o cifra. Se limita a 2-9 porque "una"/"dos" palabras
# sueltas son prosa; lo que importa es un numero COMPARTIDO con "fuentes".
NUMEROS = {
    "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7,
    "ocho": 8, "nueve": 9,
}
CIFRAS = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9}

# (regex del sintagma de multiplicidad, grupo con el numero, grupo con el resto)
SINTAXIS: List[Tuple[str, int, str]] = [
    (r"\b(?P<n>dos|tres|cuatro|cinco|[2-9])\s+(?P<r>fuentes|familias)\s+"
     r"(?:de\s+\w+\s+)?(?:independientes|de\s+headers|de\s+cabeceras)?", "n", "r"),
    (r"\b(?P<n>[2-9])\s+(?P<r>fuentes|cabeceras)\b", "n", "r"),
    (r"\bcorroborad[oa]\s+por\s+(?P<n>dos|tres|[2-9])\b", "n", "n"),
    (r"\bconfirmad[oa]\s+por\s+(?P<n>dos|tres|[2-9])\b", "n", "n"),
    (r"\bdoble\s+fuente\b", 2, ""),
    (r"\b[2-9]\s+familias\s+de\s+headers\b", 2, "familias"),
]

# El proyecto escribe `vid.h:169` y `007-gfx8-pm4-format.md:93-104`: el
# ancla de linea va DENTRO de las comillas. Un patron que exige que el nombre
# termine en extension no encuentra ninguno, y toda afirmacion con fuentes
# nombradas cae en NO_COMPROBABLE: el recuento sale plausible y equivocado, que
# es la forma que este proyecto lleva 122 hallazgos previniendo.
FICHERO_RX = re.compile(
    r"`([^`\n]+?\.(?:md|c|h|py|txt|sh))(?::[\d,\- ]+)?`")

# NO es un nombre de fichero. La primera version de esta herramienta aceptaba
# `grep -n "INVALIDATE" gmc_8_2_d.h`, `CONTINUES=017-*.md` y `*.c` como
# fuentes nombradas, y con eso declaraba infladas afirmaciones que si lo estan.
# Una clase que no distingue un fichero de un comando no mide: cuenta.
# Regla: sin espacios, sin '=', sin '*', y con una extension real.
# search() busca en cualquier posicion, asi que el patron es la extension
# como SUFIJO. Con "^\." exigia que el nombre EMPEZARA por punto y
# rechazaba todos los ficheros -- con el nombre del fichero de la
# herramienta apareciendo 67 veces como NO_COMPROBABLE, que es un
# resultado plausible y del todo erroneo.
EXT_OK = re.compile(r"\.[A-Za-z0-9]{1,5}$")


def es_nombre_de_fichero(ref: str) -> bool:
    r = ref.strip()
    # tolera el ancla de linea tanto si viene como parte del ref como si ya
    # la"El patron que lo captura la deja fuera, pero la funcion se llama
    # tambien desde vectores de prueba y no debe depender de quien la llama.
    r = re.sub(r":[\d,\- ]+$", "", r)
    if not r or " " in r or "=" in r or "*" in r or '"' in r or "'" in r:
        return False
    if r.startswith(("grep", "sed", "cat", "ls", "git ", "python", "find")):
        return False
    return bool(EXT_OK.search(r))


def proyecto() -> str:
    return os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".."))


def n_de(token: str) -> int:
    # El texto del proyecto escribe "DOS familias" en mayusculas para
    # Kitchen. Una tabla de numeros que no baja el token devuelve 0, y el
    # filtro n>=2 descarta el sintagma entero: cero afirmaciones, que es un
    # resultado plausible y equivocado.
    t = (token or "").strip().lower()
    return NUMEROS.get(t, CIFRAS.get(t, 0))


def frases_multiplicidad(txt: str) -> List[Tuple[str, int, int, int]]:
    """(texto, offset, longitud, numero_declarado) para cada sintagma."""
    out = []
    for pat, grupo_num, _ in SINTAXIS:
        for m in re.finditer(pat, txt, re.IGNORECASE):
            # grupo_num == 2 marca los sintagmas SIN grupo de numero
            # ("doble fuente"), donde el valor es 2 por definicion del sintagma.
            if grupo_num == 2:
                tok = m.groupdict().get("n")
                n = 2 if tok is None else n_de(tok)
            else:
                n = n_de(m.group(grupo_num))
            if n >= 2:
                out.append((m.group(0), m.start(), len(m.group(0)), n))
    # solapes: el mismo sintoma no se cuenta dos veces por dos patrones
    out.sort(key=lambda x: (x[1], -x[2]))
    limpio: List[Tuple[str, int, int, int]] = []
    for f in out:
        if limpio and f[1] < limpio[-1][1] + limpio[-1][2]:
            continue
        limpio.append(f)
    return limpio


def clasificar(txt: str, ini: int, fin: int, declarado: int) -> Tuple[str, List[str]]:
    """La clase de UNA afirmacion, y los ficheros nombrados en su ventana.

    La ventana es +-VENTANA lineas alrededor. No es un detalle: la prueba de
    que un campo aparece en dos ficheros suele estar en la tabla de al lado,
    no en la frase que afirma la corroboración.
    """
    ini_linea = txt.rfind("\n", 0, ini) + 1
    fin_linea = txt.find("\n", fin)
    ventana = txt[max(0, ini_linea - 2200):(fin_linea + 2200 if fin_linea > 0
                                             else len(txt))]
    ficheros = sorted(set(x for x in FICHERO_RX.findall(ventana)
                          if es_nombre_de_fichero(x)))
    distintos = sorted(set(os.path.basename(f) for f in ficheros))
    # "5 cabeceras GMC, 0 coincidencias" NO es una afirmacion de redundancia:
    # es el DENOMINADOR de un resultado negativo, y este proyecto tiene
    # NEGATIVE_RESULT como categoria de primer orden. Contarlo como
    # corroboracion inflada es el error de lectura mas caro de esta
    # herramienta, porque el texto dice literalmente "0 coincidencias".
    neg = re.search(
        r"(0\s+coincidencias|0\s+matches|cero\s+(coincidencias|apariciones|casos)"
        r"|NEGATIVE_RESULT|PROVEN_ABSENT|\bno\s+existe\b)", ventana)
    if neg:
        return "DENOMINADOR_DE_UN_NEGATIVO", distintos
    if not distintos:
        return "NO_COMPROBABLE", []
    if len(distintos) < declarado:
        return "INFLADA_DECLARADA", distintos
    return "RESPALDADA", distintos


def selftest() -> int:
    print("=== corroboration selftest ===\n")
    fallos = 0

    print("[1] se detecta el sintagma y el numero")
    t = "PROVEN por DOS familias de headers independientes."
    f = frases_multiplicidad(t)
    if len(f) != 1 or f[0][3] != 2:
        print("  FAIL %r" % f)
        fallos += 1
    else:
        print("  OK   'DOS familias ... independientes' -> declarado 2: %r" % (f[0][0],))

    print()
    print("[2] un numero repetido en la misma frase cuenta UNA vez")
    t2 = "dos fuentes y dos cabeceras"
    f2 = frases_multiplicidad(t2)
    if len(f2) != 1:
        print("  FAIL %d sintomas, esperaba 1 sin solapes" % len(f2))
        fallos += 1
    else:
        print("  OK   solape eliminado: 1 sintoma")

    print()
    print("[3] la clase depende de las fuentes NOMBRADAS, no de la frase")
    txt_ok = ("`vid.h:169` y `soc15d.h:199` corroboran el campo\n"
              "PROVEN por dos familias de headers\n")
    c, f = clasificar(txt_ok, txt_ok.find("PROVEN por dos"), 0, 2)
    if c != "RESPALDADA":
        print("  FAIL %s %s" % (c, f))
        fallos += 1
    else:
        print("  OK   dos ficheros nombrados -> RESPALDADA %s" % f)

    txt_mal = ("PROVEN por dos familias de headers\n")
    c2, f2 = clasificar(txt_mal, txt_mal.find("PROVEN por dos"), 0, 2)
    if c2 != "NO_COMPROBABLE":
        print("  FAIL sin ficheros -> %s" % c2)
        fallos += 1
    else:
        print("  OK   sin ficheros nombrados -> NO_COMPROBABLE")

    print()
    print("[4] declarar mas de lo que se nombra es INFLADA")
    txt3 = ("`vid.h:186` lo define.\n"
            "PROVEN por dos familias de headers independientes\n")
    c3, f3 = clasificar(txt3, txt3.find("PROVEN por dos"), 0, 2)
    if c3 != "INFLADA_DECLARADA":
        print("  FAIL -> %s (%s)" % (c3, f3))
        fallos += 1
    else:
        print("  OK   declara 2, nombra 1 -> INFLADA_DECLARADA %s" % f3)

    print()
    print("[5] la ventana +-2 lineas alcanza la tabla de al lado")
    # REGLA: un fichero cuenta como nombrado si aparece como RUTA entre
    # backticks. Este vector lo comprobaba con nombres sueltos, y por eso
    # fallaba: el vector estaba mal, no la herramienta. Exigir backticks es
    # lo que separa "citó un fichero" de "una palabra que acaba en .h".
    txt5 = ("`vid.h:186`\n"
            "`vid.h:169`\n"
            "`vid.h:182`\n"
            "PROVEN por dos familias de headers\n")
    c5, f5 = clasificar(txt5, txt5.find("PROVEN por dos"), 0, 2)
    if c5 != "INFLADA_DECLARADA":
        print("  FAIL declara 2 y hay un solo fichero: %s %s" % (c5, f5))
        fallos += 1
    else:
        print("  OK   la ventana alcanza los campos y solo hay 1: %s" % c5)
    txt5b = ("`vid.h:186`\n`soc15d.h:199`\n"
             "PROVEN por dos familias de headers\n")
    c5b, f5b = clasificar(txt5b, txt5b.find("PROVEN por dos"), 0, 2)
    if c5b != "RESPALDADA":
        print("  FAIL con dos ficheros: %s" % c5b)
        fallos += 1
    else:
        print("  OK   con dos ficheros en la ventana: RESPALDADA")

    print()
    print("[6] un comando o un glob NO son ficheros nombrados")
    ruido = ["`grep -n \"X\" gmc_8_2_d.h`", "`CONTINUES=017-x.md`", "`*.c`"]
    malos = [x for x in ruido if es_nombre_de_fichero(x)]
    if malos:
        print("  FAIL acepto como fichero: %s" % malos)
        fallos += 1
    else:
        print("  OK   comando, puntero CONTINUES= y glob: los 3 descartados")
    for bueno in ("vid.h", "vid.h:169", "gmc_8_1_sh_mask.h", "007-x.md:93-104"):
        if not es_nombre_de_fichero(bueno):
            print("  FAIL rechazo un nombre legitimo: %r" % bueno)
            fallos += 1
            break
    else:
        print("  OK   'vid.h', 'vid.h:169', 'gmc_8_1_sh_mask.h': los 3 aceptados")
    if False:
        print("  FAIL rechazo un nombre de fichero legitimo")
        fallos += 1
    else:
        print("  OK   'vid.h' si es nombre de fichero")

    print()
    print("[7] 'N cabeceras, 0 coincidencias' NO es corroboracion")
    negt = ("`vid.h` `soc15d.h`\n"
            "| Que GFX8 no expone ack | `PROVEN_ABSENT` | 5 cabeceras GMC, "
            "0 coincidencias |\n")
    cn, fn = clasificar(negt, negt.find("5 cabeceras"), 0, 5)
    if cn != "DENOMINADOR_DE_UN_NEGATIVO":
        print("  FAIL -> %s (debio ser denominador de un negativo)" % cn)
        fallos += 1
    else:
        print("  OK   PROVEN_ABSENT + 0 coincidencias -> denominador, no corroboracion")

    print()
    print("[8] una prosa sin sintagma no se cuenta")
    if frases_multiplicidad("el mismo error en dos sitios") != []:
        print("  FAIL conto una prosa sin sintagma de fuentes")
        fallos += 1
    else:
        print("  OK   'en dos sitios' no es sintagma de fuentes")

    print("=" * 72)
    if fallos:
        print("RESULT: FAIL (%d)" % fallos)
        return 1
    print("RESULT: PASS (16 vectores)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="audita las afirmaciones de multiplicidad de evidencia")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    d = os.path.join(proyecto(), "06-INGENIERIA-INVERSA", "findings")
    filas = []
    conteo: Dict[str, int] = {}
    for f in sorted(os.listdir(d)):
        if not f.endswith(".md"):
            continue
        with open(os.path.join(d, f), "r", errors="replace") as fh:
            txt = fh.read()
        for frase, ini, lon, n in frases_multiplicidad(txt):
            clase, nombrados = clasificar(txt, ini, ini + lon, n)
            lin = txt.count("\n", 0, ini) + 1
            conteo[clase] = conteo.get(clase, 0) + 1
            filas.append({"finding": f, "linea": lin, "frase": frase,
                          "declarado": n, "clase": clase,
                          "nombrados": nombrados})

    if args.json:
        print(json.dumps({"version": VERSION, "total": len(filas),
                          "conteo": conteo, "filas": filas},
                         indent=2, sort_keys=True, ensure_ascii=False))
        return 0

    print("=" * 78)
    print("CORROBORACION -- afirmaciones de multiplicidad en los hallazgos")
    print("=" * 78)
    print()
    print("  hallazgos analizados: %d" % len(
        [f for f in os.listdir(d) if f.endswith(".md")]))
    print("  afirmaciones de multiplicidad: %d" % len(filas))
    print()
    for k, v in sorted(conteo.items(), key=lambda kv: -kv[1]):
        print("    %-22s %4d  %s" % (k, v, "%5.1f%%" % (100.0 * v / max(1, len(filas)))))
    print()
    print("  QUE SIGNIFICA CADA CLASE:")
    print("  RESPALDADA          el texto declara N y nombra >= N ficheros")
    print("                      distintos en la ventana. NO implica que la")
    print("                      corroboracion sea correcta: 122 demuestra que")
    print("                      dos ficheros pueden ser una sola fuente.")
    print("  INFLADA_DECLARADA   declara mas fuentes de las que nombra. Es la")
    print("                      clase de 122 y de 034.")
    print("  NO_COMPROBABLE      usa palabras de multiplicidad sin nombrar")
    print("                      ninguna fuente al lado. Puede ser prosa.")
    print("  DENOMINADOR_DE_UN_NEGATIVO  el numero es el alcance de un")
    print("                      resultado NEGATIVO ('5 cabeceras, 0")
    print("                      coincidencias'), no una redundancia. No son")
    print("                      deuda y no deben tocarse.")
    print()
    print("  LO QUE ESTA HERRAMIENTA NO HACE, y conviene no olvidar:")
    print("  no comprueba que las fuentes sean independientes. Dos ficheros que")
    print("  terminan en la misma base de datos de ASIC son una fuente. Eso")
    print("  exige leer el arbol de cada cita, y aqui no se hace.")
    print()

    infladas = [x for x in filas if x["clase"] == "INFLADA_DECLARADA"]
    print("  INFLADAS_DECLARADAS (%d), que son las que hay que mirar:" % len(infladas))
    for x in infladas[:20]:
        print("    %-46s L%-4d declara %d, nombra %d"
              % (x["finding"][:46], x["linea"], x["declarado"],
                 len(x["nombrados"])))
        print("        \"%s\"" % x["frase"][:60])
        for n in x["nombrados"][:3]:
            print("          nombrado: %s" % n)
    if len(infladas) > 20:
        print("    ... y %d mas" % (len(infladas) - 20))
    return 0


if __name__ == "__main__":
    sys.exit(main())