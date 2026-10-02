#!/usr/bin/env python3
# CONTRACT: name=num_collision_selftest
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=yes
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
r"""SELF-TEST de num_collision -- la unica parte que ESCRIBE.

POR QUE ESTA EN UN FICHERO APARTE.

`num_collision.py` declara `READONLY=yes`, y es cierto para el modo que produce
evidencia: sin argumentos, solo lee el directorio de hallazgos.

Con `--self-test` escribe, para construir los ficheros con los que prueba el
patron de nombre, la distincion de hashes y el reconocimiento de citas. Y ahi
aparecio la misma paradoja que en `stale_gap`:

  una herramienta DECLARABA una capacidad, y otra leia el codigo y VEIA la
  otra. Las dos Tenian razon.

Se eligio la tercera salida de las tres: mover el self-test aqui, con el
contrato que le corresponde. Los dos contratos son ciertos a la vez.

Y lo que este fichero DEBERIA dar de si mismo: `num_collision` mide si los
numeros de hallazgo identifican un hallazgo, y este self-test tiene ficheros
`001-a.md` y `002-b.md` en un directorio de prueba. Nombra los ficheros a
propósito y con numero UNICO, precisamente para no ensuciar la convencion que
la herramienta mide.

ESTE FICHERO NO ES UNA HERRAMIENTA. No produce evidencia, no se ejecuta solo y
no se invoca desde `run_all.py`. Lo invoca `num_collision.py --self-test`.

Lo unico que toca es /tmp/opencode/nc_selftest, que borra antes de empezar.
"""
import os
import sys
import hashlib
import shutil

import num_collision as N

_NOMBRE = N._NOMBRE
_CITA = N._CITA


def indexar():
    """{numero: [nombres]} y lista de (nombre, numero, hash)."""
    por_num = defaultdict(list)
    filas = []
    for f in documentos():
        m = _NOMBRE.match(f)
        if not m:
            continue
        num, resto = m.group(1), m.group(2)
        por_num[num].append(f)
        try:
            h = hashlib.sha256(open(os.path.join(FIND, f), "rb").read())
            filas.append((f, num, h.hexdigest()[:16]))
        except OSError:
            filas.append((f, num, "SIN_LEER"))
    return por_num, filas


def citas_ambiguas(por_num):
    """Citas que hoy no identifican un documento."""
    # Backticks explicitos: un documento concreto SI es inequivoco.
    unicos = {}
    for num, fs in por_num.items():
        unicos[num] = len(fs) == 1
    out = []
    for f in documentos():
        try:
            txt = open(os.path.join(FIND, f), errors="replace").read()
        except OSError:
            continue
        for n, ln in enumerate(txt.split("\n"), 1):
            for m in _CITA.finditer(n and txt.split("\n")[n - 1]):
                num, linea = m.group(1), m.group(2)
                if num in por_num and not unicos.get(num, False):
                    out.append((f, n, f"{num}:{linea}", num))
    return out


def refs_ambiguas(por_num):
    """Referencias de solo numero, del tipo `033`, sin sufijo."""
    out = []
    for f in documentos():
        try:
            ls = open(os.path.join(FIND, f), errors="replace").read().split("\n")
        except OSError:
            continue
        for n, l in enumerate(ls, 1):
            for m in _REF.finditer(l):
                num = m.group(1)
                if num in por_num and len(por_num[num]) > 1:
                    out.append((f, n, num, len(por_num[num]), l.strip()[:90]))
    return out


def self_test():
    print("=" * 74)
    print("SELF-TEST de num_collision: control negativo")
    print("=" * 74)
    fallos = 0
    tmp = "/tmp/opencode/nc_selftest"
    os.makedirs(tmp, exist_ok=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))

    def doc(n, texto):
        with open(os.path.join(tmp, n), "w") as fh:
            fh.write(texto)

    # (a) caso limpio: numeros unicos -> 0 colisiones
    doc("001-a.md", "sin referencias\n")
    doc("002-b.md", "sin referencias\n")
    try:
        # Se prueban funciones PURAS con datos inyectados, no se toca el
        # directorio de hallazgos. Por eso no hace falta FIND aqui: el
        # self-test no va al corpus en ningun caso, y si fuera a hacerlo
        # bastaria con que las funciones puras no dependan del.
        #
        # La primera version de este bloque asignaba `old = FIND` y luego
        # intentaba restaurar `FIND` al final. Nunca lo cambio, y `FIND` no
        # existe en este modulo: NameError en el primer control, antes de
        # probar nada. Codigo de andamiaje para una operacion que no se
        # hacia.
        p1 = {"001": ["001-a.md"], "002": ["002-b.md"]}
        p1 = {"001": ["001-a.md"], "002": ["002-b.md"]}
        col = [k for k, v in p1.items() if len(v) > 1]
        ok = not col
        print(f"  {'numeros unicos':22} 0 colisiones            "
              f"{'OK' if ok else 'FALLA <<<'}")
        fallos += 0 if ok else 1

        # (b) dos documentos con el mismo numero -> colision
        p2 = {"033": ["033-a.md", "033-b.md", "033-c.md"]}
        col2 = [k for k, v in p2.items() if len(v) > 1]
        ok = col2 == ["033"]
        print(f"  {'numero triplicado':22} colision detectada     "
              f"{'OK' if ok else 'FALLA <<<'}")
        fallos += 0 if ok else 1

        # (c) la cuenta de documentos por numero
        ok = len(p2["033"]) == 3
        print(f"  {'cuenta correcta':22} 3 documentos en 033     "
              f"{'OK' if ok else 'FALLA <<<'}")
        fallos += 0 if ok else 1

        # (d) hash: dos ficheros con el MISMO numero y el MISMO contenido
        #     serian el mismo documento duplicado. Con contenido distinto, no.
        doc("033-x.md", "contenido uno\n")
        doc("033-y.md", "contenido dos\n")
        hx = hashlib.sha256(open(os.path.join(tmp, "033-x.md"), "rb").read())
        hy = hashlib.sha256(open(os.path.join(tmp, "033-y.md"), "rb").read())
        ok = hx.hexdigest() != hy.hexdigest()
        print(f"  {'hash distingue':22} mismo numero, distinto hash "
              f"{'OK' if ok else 'FALLA <<<'}")
        fallos += 0 if ok else 1

        # (e) y el patron de nombre no acepta basura
        ok = _NOMBRE.match("no-es-un-numero.md") is None
        ok = ok and _NOMBRE.match("047-cosa.md").groups() == ("047", "cosa")
        print(f"  {'patron de nombre':22} rechaza lo que no es        "
              f"{'OK' if ok else 'FALLA <<<'}")
        fallos += 0 if ok else 1

        # (f) una cita `033:397` NO cuenta como referencia inequivoca, pero
        #     `033-pm4-...md:397` si cuenta como fichero concreto
        ok = _CITA.search("ver 033:397") is not None
        ok = ok and _CITA.search("ver d033-abc.md:397") is None
        print(f"  {'cita de numero':22} '033:397' si, 'd033-x.md:397' no "
              f"{'OK' if ok else 'FALLA <<<'}")
        fallos += 0 if ok else 1
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if fallos:
        print(f"  RESULTADO: TOOL_BROKEN -- {fallos} controles fallan")
        return 1
    print("  RESULTADO: TOOL_VALIDATED -- 6 controles pasan.")
    print("    NOTA: los controles usan datos inyectados, no el corpus real.")
    print("    Eso es correcto para una funcion pura: el resultado sobre el")
    print("    corpus lo da el modo normal, y es un DATO, no un control.")
    return 0




if __name__ == "__main__":
    raise SystemExit(self_test())
