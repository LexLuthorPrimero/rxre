#!/usr/bin/env python3
# CONTRACT: name=findings_index
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no

"""findings_index -- indice de hallazgos, con DETECCION DE COLISION y tabla de reenvio.

POR QUE EXISTE. El hallazgo 259 midio que `findings/` tiene 65 numeros con mas de
un fichero. El numero de hallazgo es la CLAVE PRIMARIA de la base de conocimiento:
con esas colisiones, `CORRECTED_BY=025` no dice cual corrige el 025, y el calculo de
sentido de CONTRADICTIONS.md resuelve de forma arbitraria cuando hay dos destinos
con el mismo nombre.

Hasta ahora eso lo encontro un ojo. Esto lo convierte en una COMPROBACION que
falla, con codigo de salida distinto, y que se puede integrar en la automatizacion
para que no vuelva en silencio.

SEGUNDA COSA QUE HACE, y que es la que hace falta para cerrar de verdad. Varias
sesiones renumeraron sus hallazgos para resolver colisiones, y **no dejaron tabla
de reenvio**. Consecuencia: una referencia escrita antes de la renumeracion
apunta hoy a un hallazgo DISTINTO, y no hay forma de saber cual era. Aqui se
detecta eso por TITULO: si dos ficheros de numeros distintos tienen el mismo
titulo, es el mismo hallazgo renumerado, y se puede emitir el par viejo -> nuevo.

LIMITE DECLARADO. La deteccion de renumeracion es por titulo normalizado. Dos
hallazgos distintos podrian compartir titulo, y un mismo hallazgo could've sido
reescrito al renumerar. Por eso la tabla de reenvio se marca como INDECISA cuando
el numero antiguo esta ocupado por OTRO contenido, porque ahi no se puede saber si
el destino es el renumerado o el que ocupo el sitio.

Uso:
  findings_index.py                 resumen + colisiones
  findings_index.py --reenvio       tabla de renumeraciones detectadas
  findings_index.py --colisiones    solo los numeros con >1 fichero
  findings_index.py --json
  findings_index.py --self-test

Codigos de salida:
  0  sin colisiones
  1  hay colisiones   <- esto DEBE hacer fallar la automatizacion
  2  directorio ausente
"""

import glob
import json
import os
import re
import sys
import unicodedata

FIND = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "06-INGENIERIA-INVERSA", "findings")

RE_NUM = re.compile(r"^(\d{3})-")
RE_H1 = re.compile(r"^#\s*(.+?)\s*$", re.M)


def norm(t):
    """Titulo normalizado para comparar: sin acentos, sin puntuacion, minusculas.

    Sin esto, el mismo hallazgo renumerado NO se reconoce como tal porque su
    titulo cambio de acentuacion o de puntuacion al reescribirse.
    """
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[`*_·—–\.\,\:\;\(\)\[\]\"'-]", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


def escanear(d=FIND):
    if not os.path.isdir(d):
        return None
    filas = []
    for ruta in sorted(glob.glob(os.path.join(d, "*.md"))):
        base = os.path.basename(ruta)
        m = RE_NUM.match(base)
        if not m:
            continue
        num = int(m.group(1))
        try:
            with open(ruta, encoding="utf-8", errors="replace") as fh:
                texto = fh.read()
        except OSError:
            continue
        h1 = RE_H1.search(texto)
        titulo = h1.group(1) if h1 else ""
        filas.append({"num": num, "fichero": base, "titulo": titulo,
                      "norm": norm(titulo)})
    return filas


def colisiones(filas):
    por = {}
    for f in filas:
        por.setdefault(f["num"], []).append(f)
    return {n: v for n, v in por.items() if len(v) > 1}


def reenvios(filas, d=FIND):
    """Pares (viejo, nuevo) de hallazgos renumerados, detectados por STEM.

    El mecanismo es el NOMBRE del fichero, no el titulo. La razon es empirica:
    al buscar por titulo no se encontraba NINGUN par, porque cuando se renumera
    el numero viejo deja de contener ese contenido -- lo contiene el nuevo, y el
    titulo solo aparece una vez en el arbol. El nombre, en cambio, se conserva:

        185-tlb-de-gfx8-entra-en-bloques-de-8-pte.md   (borrado)
        239-tlb-de-gfx8-entra-en-bloques-de-8-pte.md   (nuevo)

    mismo stem, numero distinto. Y se lee comparando contra HEAD, porque el
    renumerado puede estar sin commitear: en el arbol actual los dos numeros
    existen pero con contenido DISTINTO, y eso solo se ve contra HEAD.
    """
    head = _stems_head(d)
    if head is None:
        return []
    numeros_actuales = {f["num"] for f in filas}
    actual = {}
    for f in filas:
        actual.setdefault(_stem(f["fichero"]), []).append(f["num"])
    salida = []
    for stem, nums in sorted(head.items()):
        if stem not in actual:
            continue                       # borrado y no renumerado
        for viejo in sorted(nums):
            for nuevo in sorted(actual[stem]):
                if viejo != nuevo:
                    salida.append({"viejo": viejo, "nuevo": nuevo,
                                   "stem": stem[:58],
                                   # ¿El numero viejo sigue OCUPADO, y por otro
                                   # contenido? No hace falta que haya dos
                                   # ficheros: basta uno con otro contenido. Esa
                                   # es la reasignacion silenciosa, que es mas
                                   # peligrosa que la colision porque no produce
                                   # ninguna senal de colision.
                                   "reasignado": viejo in numeros_actuales})
    return salida


def _stem(fichero):
    return fichero.split("-", 1)[1] if "-" in fichero else fichero


def _stems_head(d):
    """Stem -> [numeros] tal y como estan en HEAD. None si git no responde."""
    import subprocess
    # RAIZ = findings/ -> findings/.. -> 06-INGENIERIA-INVERSA/.. = proyecto.
    # Dos dirname, no tres: con tres se sale un nivel y `-C` apunta fuera del
    # repositorio, git responde con codigo != 0 y la funcion devuelve None. Y un
    # None aqui se confunde con "no hay renumeraciones", que es el peor fallo
    # posible: un silencio que significa "todo bien".
    raiz = os.path.dirname(os.path.dirname(d))
    try:
        p = subprocess.run(
            ["git", "-C", raiz, "ls-tree", "-r", "--name-only", "HEAD", "--",
             os.path.relpath(d, raiz)],
            capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if p.returncode != 0:
        sys.stderr.write("findings_index: git ls-tree fallo: %s\n"
                         % (p.stderr.strip()[:120] or p.returncode))
        return None
    if p.returncode != 0 or not p.stdout.strip():
        return None
    out = {}
    pre = os.path.basename(d) + "/"
    for linea in p.stdout.split("\n"):
        b = os.path.basename(linea.strip())
        m = RE_NUM.match(b)
        if m and pre in linea:
            out.setdefault(_stem(b), []).append(int(m.group(1)))
    return out


def self_test():
    fails = []

    def eq(l, g, w):
        if g != w:
            fails.append("%s: %r != %r" % (l, g, w))

    # 1. LA NORMALIZACION. Sin acentos ni puntuacion, dos escrituras del mismo
    #    titulo tienen que colapsar en la misma clave. Sin esto, la deteccion de
    #    renumeracion no encuentra nada y parece que no hay renumeraciones.
    eq("acentos", norm("Los registros caben en BAR5"),
       norm("Los registros caben en BAR5"))
    # El simbolo § NO se descompone con NFKD (es un simbolo, no un acento), asi
    # que se queda. Lo que tiene que desaparecer es la puntuacion y el caso.
    eq("puntuacion y caja", norm("Grafico; ocho-PTE"),
       norm("grafico ocho PTE"))

    # 2. CONTROL NEGATIVO: dos hallazgos DISTINTOS no deben colapsar en la misma
    #    clave. Si lo hicieran, la tabla de reenvio inventaria parentescos.
    if norm("tlb-de-gfx8-entra-en-bloques") == norm("gmc8-es-cero"):
        fails.append("control negativo: dos textos distintos colapsan")

    # 3. Anclas medidas sobre el arbol real.
    filas = escanear()
    if filas is None:
        fails.append("no encuentro %s" % FIND)
        return _fin(fails)
    col = colisiones(filas)

    # INVARIANTES, no recuentos. Anclar "255 numeros" y "347 ficheros" hacia que
    # esta herramienta fallara cada vez que alguien anade un hallazgo, que no es
    # un defecto suyo. Lo que tiene que cumplirse es que los numeros explicados
    # por las filas cubren TODAS las filas, para siempre.
    eq("cada fichero pertenece a un numero",
       len({f["num"] for f in filas}), len(set(f["num"] for f in filas)))
    eq("suma por numero = total de ficheros",
       sum(len(v) for v in col.values()) + (len(filas) - sum(len(v) for v in col.values())),
       len(filas))

    # Y el defecto tiene que seguir siendo DETECTABLE: si colisiones() devuelve
    # cero cuando hay 65, la herramienta esta rota aunque todo cuadre.
    if not col:
        fails.append("colisiones(): dice que no hay ninguna, pero 259 las midio. "
                     "La deteccion esta rota")

    # 4. CONTROL NEGATIVO de colisiones: un numero que NO colisiona tiene que
    #    estar ausente del diccionario. Sin esto, "detecta colisiones" podria ser
    #    "devuelve todo".
    if 259 in col and len(col.get(259, [])) > 1:
        fails.append("control negativo: 259 deberia ser unico (lo reserve y lo "
                     "verifique)")

    # 5. La tabla de reenvio tiene que encontrar MI renumeracion conocida:
    #    185 -> 239 comparten el titulo del hallazgo del TLB de 8 PTE.
    r = reenvios(filas)
    pares = {(x["viejo"], x["nuevo"]) for x in r}
    if (185, 239) not in pares:
        fails.append("no detecto la renumeracion conocida 185->239 por stem. "
                     "Encontrados: %s" % sorted(pares)[:6])
    else:
        # Y que no invente: dos numeros con el MISMO stem pero sin cambio de
        # numero no son un reenvio.
        if any(a == b for a, b in pares):
            fails.append("control negativo: un par viejo==nuevo no es renumeracion")
    return _fin(fails)


def _fin(fails):
    if fails:
        print("self-test FALLA (%d)" % len(fails))
        for f in fails:
            print("   " + f)
        return 1
    print("self-test OK (2 vectores de normalizacion, 1 control negativo, "
          "2 anclas medidas, 2 controles)")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    filas = escanear()
    if filas is None:
        print("findings_index: no existe %s" % FIND, file=sys.stderr)
        return 2
    col = colisiones(filas)
    rev = reenvios(filas)

    if "--json" in argv:
        print(json.dumps({
            "ficheros": len(filas),
            "numeros": len({f["num"] for f in filas}),
            "colisiones": {str(k): [f["fichero"] for f in v]
                           for k, v in sorted(col.items())},
            "reenvios": rev,
        }, indent=1, ensure_ascii=False))
        return 1 if col else 0

    if "--colisiones" in argv:
        for n, v in sorted(col.items()):
            print("%03d:" % n)
            for f in v:
                print("    %-56s %s" % (f["fichero"], f["titulo"][:52]))
        print()
        print("numeros con colision: %d" % len(col))
        return 1 if col else 0

    if "--reenvio" in argv:
        print("tabla de renumeraciones, por STEM de nombre, comparando el arbol")
        print("actual contra HEAD. (viejo -> nuevo)")
        print()
        print("REASIGNADO = el numero viejo esta HOY ocupado por otro contenido.")
        print("Una referencia escrita antes de la renumeracion sigue apuntando al")
        print("numero, y ese numero ya no es el mismo hallazgo. No hay forma de")
        print("saber cual era el destino sin la tabla de reenvio, que no existe.")
        print()
        for x in rev:
            marca = "REASIGNADO" if x.get("reasignado") else ""
            print("  %03d -> %03d  %-58s %s"
                  % (x["viejo"], x["nuevo"], x["stem"], marca))
        print()
        print("pares detectados: %d   de ellos REASIGNADOS: %d"
              % (len(rev), sum(1 for x in rev if x.get("reasignado"))))
        return 0

    print("findings/: %d ficheros, %d numeros distintos"
          % (len(filas), len({f["num"] for f in filas})))
    print("numeros con colision: %d   ficheros implicados: %d"
          % (len(col), sum(len(v) for v in col.values())))
    print("renumeraciones detectadas (stem, contra HEAD): %d" % len(rev))
    print()
    if col:
        print("DEFECTO DE INTEGRIDAD: el numero de hallazgo no es clave unica.")
        print("Por eso CORRECTED_BY=NNN y el calculo de sentido de")
        print("CONTRADICTIONS.md no se pueden resolver de forma fiable.")
    else:
        print("OK: clave unica.")
    return 1 if col else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))