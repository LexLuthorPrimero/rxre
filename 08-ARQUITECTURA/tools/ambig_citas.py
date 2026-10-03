#!/usr/bin/env python3
# CONTRACT: name=ambig_citas
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=yes     (solo con --escribir)
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no

"""ambig_citas -- inventario de citas que no saben a que hallazgo se refieren.

QUE MIDE, Y QUE NO

Medido el 2026-10-03 sobre el corpus: 74 numeros de hallazgo estan ocupados por
dos o tres ficheros distintos. 72 de esos numeros los cita alguien. Las citas
suman 1736, y una cita `NNN` desde un fichero distinto de `NNN` no tiene destino
unico: puede ser cualquiera de los dos o tres.

Esto NO es lo mismo que una referencia colgando. Una colgante es un puntero que
apunta al sitio equivocado y se arregla con un mapa. Aqui el problema es que el
identificador no es un identificador: no hay mapa posible, hay que ELEGIR.

POR QUE EXISTE Y QUE NO HACE

No elige. No propone. No reescribe. Para cada cita ambigua produce:

    linea exacta, numero, ficheros candidatos, y si hay alguna PISTA

"pista" significa: una palabra del titulo de UNO de los candidatos aparece en la
linea que cita. Se declara que la pista NO es una respuesta: se medio sobre 10
casos leidos a mano y la heuristica acierta en 6, se equivoca en 2 y en 2 no hay
forma de decidir. Con 274 casos resolubles por esta regla y ~25% de error,
APLICARLA AUTOMATICAMENTE GENERARIA ~68 REFERENCIAS NUEVAS EQUIVOCADAS, que es
justo la clase de dano que refs_repair.py acaba de eliminar de 1038 citas.

Por eso esta herramienta produce un INFORME y no una reparacion. El informe es
el insumo de una decision de politica del proyecto, y esa decision no es de esta
herramienta.

SALIDAS

  --json      lista estructurada, una entrada por cita ambigua
  --tsv       una linea por cita, para abrir en hoja de calculo
  --resumen   agrupado por numero: cuantos ficheros, cuantas citas
  --pistas    solo las que tienen pista, con el candidato que la pista nombra
  default     resumen corto por pantalla

Uso:
  ambig_citas.py [--json|--tsv|--resumen|--pistas] [--escribir DIR]
  ambig_citas.py --self-test

Codigos de salida:
  0  se pudo medir
  1 Citations ambiguas > 0 y se pidio una vista de detalle
  2  no se pudo ejecutar
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FIND = os.path.join(ROOT, "06-INGENIERIA-INVERSA", "findings")

RE_CITA = re.compile(r"`(\d{3,4})`")

# Palabras que no sirven como pista: son estructura de frase en castellano y
# aparecen en casi cualquier linea. Medido: con esta lista, la cobertura baja,
# pero las pistas que quedan nombran algo del hallazgo y no un verbo.
STOP = {
    "para", "porque", "sobre", "entre", "cuando", "donde", "este", "esta",
    "este", "esto", "este", "cada", "todo", "todos", "toda", "todas", "otra",
    "otro", "mismo", "misma", "mismos", "mismas", "solo", "tampoco", "puede",
    "pueden", "tiene", "tienen", "hace", "hacen", "pero", "como", "mas",
    "menos", "aqui", "alla", "algo", "nada", "algo", "mismo", "caso", "casos",
    "forma", "formas", "parte", "partes", "vez", "veces", "punto", "puntos",
    "linea", "lineas", "valor", "valores", "numero", "numeros", "cosa", "cosas",
    "gente", "manera", "motivo", "razon", "razones", "salida", "salidas",
}


def _num(basename):
    m = re.match(r"^(\d{3,4})-", basename)
    return int(m.group(1)) if m else None


def indice():
    """numero -> [ficheros]. Vacio si el directorio no existe."""
    if not os.path.isdir(FIND):
        return {}
    out = {}
    for f in sorted(os.listdir(FIND)):
        if not f.endswith(".md"):
            continue
        n = _num(f)
        if n is None:
            continue
        out.setdefault(n, []).append(f)
    return out


def colisiones(ind):
    return {n: v for n, v in ind.items() if len(v) > 1}


def palabras_titulo(fichero):
    """Palabras del titulo, sin relleno y sin palabras de estructura."""
    cuerpo = re.split(r"-", fichero, maxsplit=1)[1] if "-" in fichero else fichero
    cuerpo = cuerpo[:-3] if cuerpo.endswith(".md") else cuerpo
    return {w.lower() for w in re.split(r"[-_]", cuerpo) if len(w) > 4} - STOP


def citas_ambiguas(ind=None, d=FIND):
    """Una entrada por cita sin destino unico.

    Cada entrada: fichero que cita, linea, numero citado, candidatos, y el
    candidato (o los que sean) a los que una palabra del titulo apunta.
    """
    ind = ind if ind is not None else indice()
    col = colisiones(ind)
    if not col:
        return []
    tit = {f: palabras_titulo(f) for v in ind.values() for f in v}
    salida = []
    for nombre in sorted(os.listdir(d)):
        if not nombre.endswith(".md"):
            continue
        propio = _num(nombre)
        if propio is None:
            continue
        ruta = os.path.join(d, nombre)
        try:
            with open(ruta, encoding="utf-8", errors="replace") as fh:
                lineas = fh.read().split("\n")
        except OSError:
            continue
        for ln, linea in enumerate(lineas, 1):
            for m in RE_CITA.finditer(linea):
                v = int(m.group(1))
                if v not in col or v == propio:
                    continue
                cands = col[v]
                palabras_linea = set(re.findall(r"[a-zA-Z]{4,}", linea.lower()))
                con_pista = [c for c in cands if tit[c] & palabras_linea]
                salida.append({
                    "fichero": nombre,
                    "linea": ln,
                    "cita": v,
                    "texto": linea.strip()[:160],
                    "candidatos": list(cands),
                    "con_pista": con_pista,
                    # 0 = ninguna pista; 1 = la pista nombra uno; 2 = la pista
                    # nombra mas de uno y no decide.  El 2 NO se puede usar:
                    # es el caso donde el contexto NO desambigua.
                    "estado": (0 if not con_pista else
                               1 if len(con_pista) == 1 else 2),
                })
    salida.sort(key=lambda x: (x["cita"], x["fichero"], x["linea"]))
    return salida


def resumen(cs):
    por = {}
    for c in cs:
        e = por.setdefault(c["cita"], {
            "candidatos": c["candidatos"], "citas": 0,
            "con_pista": 0, "pista_ambigua": 0})
        e["citas"] += 1
        if c["estado"] == 1:
            e["con_pista"] += 1
        elif c["estado"] == 2:
            e["pista_ambigua"] += 1
    return por


def self_test():
    """Los controles tienen que poder fallar. Se comprueba por mutacion
    externa: este self-test declara los vectores, y `mutate.py` los rompe."""
    fails = []

    def eq(etiqueta, got, want):
        if got != want:
            fails.append("%s: %r != %r" % (etiqueta, got, want))

    eq("numero de 3 digitos", _num("023-pte-productor.md"), 23)
    eq("numero de 4 digitos", _num("1000-de-pci.md"), 1000)
    eq("sin numero", _num("sin-numero.md"), None)

    # INDICE vs FICHEROS. `indice()` devuelve NUMEROS, no ficheros: con 74
    # colisiones, 522 ficheros dan 421 numeros. La primera version comparaba
    # esas dos cantidades y daba "421 != 522", que no es un fallo del indice
    # sino de la comparacion. Se mide lo que la herramienta produce.
    n_fich = len([f for f in os.listdir(FIND) if f.endswith(".md")])
    ind0 = indice()
    eq("ficheros = numeros + colisiones repetidas",
       n_fich, len(ind0) + sum(len(v) - 1 for v in ind0.values()))
    eq("todo fichero .md tiene numero parseable",
       n_fich, sum(len(v) for v in ind0.values()))
    col = colisiones(indice())
    # LA CLAVE ES INT. Escribir "023" aqui daba KeyError, y el motivo es que el
    # indice de `indice()` se construye con `int(m.group(1))`. Se comprueba el
    # TIPO antes de la comparacion porque comparar un string con un int no
    # falla: falla al HASH, y el error dice "no existe" en vez de "mal tipo".
    eq("colision de 2", len(col[23]), 2)
    eq("la clave es int, no str", isinstance(next(iter(col)), int), True)
    # Control negativo de colisiones. La primera versionPedia que 001 fuera
    # unico, y NO LO ES: 001-amdgpu-location.md y 001-amdgpu-overview.md. El
    # control fallaba porque la premisa era falsa, no porque la herramienta
    # este mal. El numero se busca en vez de escribirse a mano.
    unicos = [n for n, v in ind0.items() if len(v) == 1]
    if not unicos:
        fails.append("no hay ningun numero unico: el control negativo seria "
                     "vacuio")
    else:
        eq("numero unico no es colision", unicos[0] in col, False)
        eq("numero colisionado si lo es", max(col) in col, True)

    # TITULO: la palabra util entra, la de estructura no.
    p = palabras_titulo("133-g-el-mtype-no-existe-en-gfx8.md")
    if "mtype" not in p:
        fails.append("el titulo no aporta 'mtype'")
    if "mismo" in p:
        fails.append("una palabra de estructura sobrevive en el titulo")

    # CONTROL NEGATIVO: una cita NO es ambigua si el numero no colisiona, ni si
    # el fichero que cita es ese mismo numero. Sin esto, "detecta ambiguedad"
    # podria ser "cuenta todas las citas".
    cs = citas_ambiguas()
    if not cs:
        fails.append("no se ha medido NINGUNA cita ambigua: el control de que "
                     "existen seria vacuo")
    propia = [c for c in cs if c["fichero"].startswith("%03d-" % c["cita"])
              or c["fichero"].startswith("%04d-" % c["cita"])]
    if propia:
        fails.append("cuenta %d auto-citas como ambiguas" % len(propia))
    if any(len(c["candidatos"]) < 2 for c in cs):
        fails.append("una cita ambigua con un solo candidato")
    for c in cs:
        if c["estado"] not in (0, 1, 2):
            fails.append("estado fuera de rango: %r" % c["estado"])
            break

    # INVARIANTE DE LA CLASIFICACION. `estado` tiene que ser exactamente la
    # funcion de `con_pista`: 0 si no hay, 1 si hay una sola, 2 si hay varias.
    #
    # Sin este control, dos mutaciones pasaban: poner `con_pista = list(cands)`
    # (toda cita con pista) y poner `estado = 1` siempre (toda cita con la pista
    # decisoria). Las dos mienten sobre lo mismo -- cuanto es automatico -- y
    # ninguna hacia fallar el self-test, porque este solo miraba que hubiera
    # citas, no que estuvieran BIEN CLASIFICADAS. Y la clasificacion es el
    # producto: es lo que dice si esto se puede automatizar.
    for c in cs:
        esperado = (0 if not c["con_pista"] else
                    1 if len(c["con_pista"]) == 1 else 2)
        if c["estado"] != esperado:
            fails.append("estado %r no corresponde a con_pista de %d elementos: "
                         "esperado %d (%s L%d cita `%03d`)"
                         % (c["estado"], len(c["con_pista"]), esperado,
                            c["fichero"], c["linea"], c["cita"]))
            break

    # Y que las tres clases existan de verdad. Con cero en una de ellas, el
    # reparto no esta medido y el informe no dice nada util.
    for est, etiq in ((0, "sin pista"), (1, "pista que decide"),
                      (2, "pista que no decide")):
        n = sum(1 for c in cs if c["estado"] == est)
        if n == 0:
            fails.append("ninguna cita de la clase %d (%s): el reparto de tres "
                         "clases no esta medido" % (est, etiq))

    # UN TITULO DE SOLO PALABRAS DE ESTRUCTURA NO APORTA PISTA. Vacia la lista
    # STOP y las palabras de frase vuelven a contar como pistas, que es como
    # una heuristica se convierte en ruido.
    solo_stop = palabras_titulo("001-que-es-lo-mismo-para-lo-que.md")
    if solo_stop:
        fails.append("palabras_titulo devuelve %r para un titulo de solo "
                     "palabras de estructura: la lista STOP no se aplica"
                     % sorted(solo_stop))

    if fails:
        print("self-test FALLA (%d)" % len(fails))
        for f in fails:
            print("   " + f)
        return 1
    print("self-test OK (%d vectores, %d colisiones, %d citas ambiguas)"
          % (SELFTEST_VECTORES, len(colisiones(indice())), len(cs)))
    return 0


SELFTEST_VECTORES = 9


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--tsv", action="store_true")
    ap.add_argument("--resumen", action="store_true")
    ap.add_argument("--pistas", action="store_true")
    ap.add_argument("--escribir", metavar="DIR")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)

    if a.self_test:
        return self_test()

    cs = citas_ambiguas()
    if cs is None:
        print("ambig_citas: no existe %s" % FIND, file=sys.stderr)
        return 2
    por = resumen(cs)
    detalle = False

    if a.json:
        detalle = True
        print(json.dumps({
            "citas_ambiguas": len(cs),
            "numeros_colisionados": len(por),
            "con_pista": sum(1 for c in cs if c["estado"] == 1),
            "pista_ambigua": sum(1 for c in cs if c["estado"] == 2),
            "sin_pista": sum(1 for c in cs if c["estado"] == 0),
            "entradas": cs,
        }, indent=1, ensure_ascii=False))

    elif a.tsv:
        detalle = True
        print("fichero\tlinea\tcita\testado\tcandidatos\tpista")
        for c in cs:
            print("%s\t%d\t%d\t%d\t%s\t%s" % (
                c["fichero"], c["linea"], c["cita"], c["estado"],
                "|".join(c["candidatos"]), "|".join(c["con_pista"])))

    elif a.pistas:
        detalle = True
        for c in cs:
            if c["estado"] == 0:
                continue
            print("%s L%d  `%03d`  %s" % (c["fichero"], c["linea"], c["cita"],
                                        c["texto"][:80]))
            for cand in c["candidatos"]:
                marca = " <-- la PISTA apunta aqui" if cand in c["con_pista"] else ""
                print("     %s%s" % (cand[:70], marca))

    elif a.resumen:
        print("%-6s %-4s %-8s %-10s %s" % ("num", "cand", "citas", "con_pista",
                                          "ficheros candidatos"))
        for n, e in sorted(por.items()):
            print("%03d    %-4d %-8d %-10d %s" % (
                n, len(e["candidatos"]), e["citas"], e["con_pista"],
                ", ".join(x[:34] for x in e["candidatos"])))

    else:
        unicos = len(por)
        con1 = sum(1 for c in cs if c["estado"] == 1)
        con2 = sum(1 for c in cs if c["estado"] == 2)
        sin0 = sum(1 for c in cs if c["estado"] == 0)
        # La etiqueta dice lo que mide. 72 NO es el numero de colisiones: es el
        # numero de numeros colisionados QUE ALGUIEN CITA. Hay 74 colisiones y
        # dos de ellas --el 027 y el 1011-- no las cita nadie, asi que no
        # aportan ninguna linea a este informe. Confundir 72 con 74 seria
        # reportar una cifra que no se ha medido.
        print("numeros colisionados          : %d" % len(colisiones(indice())))
        print("  de los cuales, con cita      : %d" % unicos)
        print("  sin ninguna cita             : %d"
              % (len(colisiones(indice())) - unicos))
        print("citas ambiguas         : %d" % len(cs))
        print("  con pista que decide  : %d   (%.0f%%)" % (con1, 100*con1/max(1,len(cs))))
        print("  pista que no decide   : %d" % con2)
        print("  sin ninguna pista     : %d   (%.0f%%)" % (sin0, 100*sin0/max(1,len(cs))))
        print()
        print("esto NO se repara solo. la pista acierta en ~3 de cada 4 y el")
        print("numero no es unico, asi que elegir es una decision del proyecto.")

    if a.escribir:
        os.makedirs(a.escribir, exist_ok=True)
        with open(os.path.join(a.escribir, "ambig-citas.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"citas_ambiguas": len(cs),
                       "numeros_colisionados": len(por),
                       "entradas": cs}, fh, indent=1, ensure_ascii=False)
        with open(os.path.join(a.escribir, "ambig-citas.tsv"), "w",
                  encoding="utf-8") as fh:
            fh.write("fichero\tlinea\tcita\testado\tcandidatos\tpista\n")
            for c in cs:
                fh.write("%s\t%d\t%d\t%d\t%s\t%s\n" % (
                    c["fichero"], c["linea"], c["cita"], c["estado"],
                    "|".join(c["candidatos"]), "|".join(c["con_pista"])))
        print("escrito en %s" % a.escribir, file=sys.stderr)

    return 1 if (detalle and cs) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))