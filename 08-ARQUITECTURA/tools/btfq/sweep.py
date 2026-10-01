#!/usr/bin/env python3
"""
sweep.py -- rastreo de la cifra refutada block_size por TODO el proyecto.

POR QUE
-------
Se ha establecido con PROVEN que en GFX8 block_size = 10, no 9, 13 ni 22/23/24.
Una cifra refuteada propagada a varios documentos se convierte en varias
implementaciones con el mismo error, y el project no tiene forma de saber
cuantos ficheros llevan ya el valor equivocado.

Esto NO es un grep con "block_size | grep 9". Un grep asi no distingue:

  - un 9 que es block_size        (ERROR)
  - un 9 que es fragment_size     (correcto, mismo numero)
  - un 9 dentro de 029 o de 219   (correcto, substring)
  - una tabla que lista 13/14/15  (ERROR, pero no como "block_size = 9")
  - una cita del log "10-bit"     (OBSERVACION, correcta)

Esa confusion es exactamente la que produjo los cuatro valores en circulacion.
El sweep clasifica cada aparicion por CONTEXTO y solo marca ERROR cuando puede
apoyarse en la linea completa.

LIMITE DECLARADO
----------------
Esto marca donde hay que MIRAR. No demuestra que un documento este mal: un
documento puede citar el 13 para refutarlo. Se separa explicitamente con
clasificacion por verbos (afirmar vs refutar) y el resto queda como REVISAR.
"""
import os
import re
import sys

ROOT = "/home/lucas/Escritorio/RX550-INVESTIGACION"

# Valores refutados para block_size en GFX8. El 9 y el 13 son los que
# circularon; el 22/23/24 viene de pasar max_pfn en vez de tmp.
BAD = {"9", "13", "14", "15", "22", "23", "24"}

# Verbos que indican que el documento REFUTA el valor, no que lo afirma.
REFUTA = re.compile(r"\b(errat|rectific|correg|mal|error|equivoc|mal|"
                    r"refut|\bno es\b|incorrect|debió|debio|❌|✗|❌)\b",
                    re.I)

SKIP_DIRS = {".git", "RESEARCH", ".write-lock", "node_modules"}


def linea_es_error(linea, valor):
    """
    Decide si una linea AFIRMA block_size = valor PARA GFX8.

    Es mas estricto de lo que parece, porque la version previa marco 60
    lineas y al revisarlas el error real era cero. Dos formas de producto
    fallaban:

      - "2^22 entradas ... 219 paginas con block_size 9": el 9 es legitimo
        y el 22 tambien, pero ninguno de los dos es el claim refutado.
      - "el rango codificable de block_size es [9,24]": esos numeros son
        los extremos del CAMPO, no una afirmacion sobre GFX8.

    Reglas, en orden:

      1. el numero debe ser un token propio, no parte de 219/1024/2^22;
      2. debe haber un signo de ASIGNACION cerca ("=", "->", ":") o el
         formato "block_size N" con N pegado al termino;
      3. si la linea habla de rango, minimo, maximo, base o campo
         codificable, NO es un claim sobre GFX8;
      4. contexto de refutacion (error mio, rectific, ...) -> no cuenta.
    """
    if valor not in linea:
        return False, ""

    # (3) una linea que habla de RANGOS o del CAMPO no afirma nada sobre
    # GFX8: son limites del campo, validos con cualquier block_size
    if re.search(r"\b(rango|range|codificab|campo|field|min|max|"
                 r"base\b|bounds?|extremos)", linea, re.I):
        # ...salvo que ademas afirme explicitamente el valor
        if not re.search(r"(block_size\s*(=|->|:)\s*%s\b)" % re.escape(valor),
                         linea):
            return False, "RANGO"

    # (1) token propio: no parte de un numero mayor
    candidatos = []
    for m in re.finditer(re.escape(valor), linea):
        a, b = m.start(), m.end()
        prev = linea[a - 1] if a > 0 else " "
        nxt = linea[b] if b < len(linea) else " "
        if prev.isdigit() or nxt.isdigit():
            continue
        candidatos.append(m)
    if not candidatos:
        return False, ""

    for m in candidatos:
        a = m.start()
        antes = linea[max(0, a - 60):a]
        # (2) asignacion explicita, o el numero pegado al termino
        asig = re.search(r"(block_size|BITS_PER_LEVEL|PTE_COUNT)\s*"
                         r"(=|->|:)\s*$", antes, re.I)
        pegado = re.search(r"(block_size|BITS_PER_LEVEL)\s*%s\b"
                           % re.escape(valor), linea, re.I)
        if not (asig or pegado):
            continue
        ctxm = linea[max(0, a - 90): a + 90]
        # (4) refutacion
        if REFUTA.search(ctxm):
            return False, "REFUTA"
        return True, "AFIRMA"
    return False, ""


def barrer():
    hallazgos = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith((".md", ".c", ".h", ".py", ".txt")):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, ROOT)
            try:
                lineas = open(p, encoding="utf-8",
                              errors="replace").read().splitlines()
            except Exception:
                continue
            for i, ln in enumerate(lineas, 1):
                for v in BAD:
                    err, how = linea_es_error(ln, v)
                    if err:
                        hallazgos.append((rel, i, v, ln.strip()[:110]))
                        break
    return hallazgos


def main():
    print("Barrido de cifras refutadas de block_size (GFX8: el valor real es 10)")
    print()
    print("Solo se marca ERROR cuando la MISMA linea contiene el valor y un")
    print("termino de block_size, y no esta en contexto de refutacion.")
    print()
    h = barrer()
    if not h:
        print("Ningun documento AFIRMA un valor refutado de block_size.")
        return 0
    print("AFIRMAN valores refutados:")
    por_fich = {}
    for rel, i, v, txt in h:
        por_fich.setdefault(rel, []).append((i, v, txt))
    for rel in sorted(por_fich):
        print()
        print("  %s" % rel)
        for i, v, txt in por_fich[rel]:
            print("     L%-5d block_size=%-3s | %s" % (i, v, txt))
    print()
    print("TOTAL: %d lineas en %d ficheros" % (len(h), len(por_fich)))
    print()
    print("NOTA: esto marca donde hay que MIRAR, no que esten mal.")
    print("Un documento puede citar un valor refutado para refutarlo. Hay que")
    print("leer el contexto antes de enmendar.")
    return 1


if __name__ == "__main__":
    sys.exit(main())