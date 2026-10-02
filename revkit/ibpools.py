#!/usr/bin/env python3
"""
ibpools.py -- analizador de amdgpu_sa_info: los buffers de IB del driver.

QUE ES ESTE DATO
----------------
amdgpu_sa_info no es memoria de shader, pese al nombre. Es
amdgpu_ib.c:486 -> amdgpu_sa_bo_dump_debug_info(), que vuelca los tres pools
de IB del driver:

    AMDGPU_IB_POOL_DELAYED    buffers con vida corta, reutilizables
    AMDGPU_IB_POOL_IMMEDIATE  buffers para un solo uso inmediato
    AMDGPU_IB_POOL_DIRECT     buffer propio de una submission

Cada linea es:

    [dir_fisica_ini dir_fisica_fin] size N protected by 0x... on context C

Las direcciones son FISICAS del sistema (0xff00...), no VAs de GPU. Eso las
hace especialmente utiles: acotan la RAM que el driver esta usando, sin
necesitar el GART ni las page tables.

UN BLOQUE HONESTO, Y POR QUE
---------------------------
La cadena "protected by 0x" NO existe en ningun sitio del corpus. Se
comprobo con grep en las tres raices (working, baseline y 7.2.8):
amdgpu_sa_bo_dump_debug_info se LLAMA desde amdgpu_ib.c:491 pero no esta
DEFINIDO en ninguna.

Es decir: el nodo existe en el driver cargado y su implementacion no esta en
el codigo que se tiene. Por eso este script:

  - NO interpreta el valor de "protected by". Lo cuenta y lo muestra, y dice
    que no se sabe que significa.
  - NO llama a los pools "cola" y "pool" con significado inventado.

La primera version de este analisis creyo ver una rotacion de 1, 3, 2 y lo
tomo por una mascara de bits de proteccion. Era falso: hay 138 valores
distintos, del 1 al 0x8A. Era un contador incremental y la "rotacion" era
la forma de los tres primeros.

Un patron repetido en los tres primeros datos no es un patron. Es como
empieza una secuencia.
"""
import argparse
import os
import re
import sys
from collections import Counter

# Formato real de una linea, medido sobre el volcado.
# El '>' va PEGADO al corchete en el volcado real (">[0xff..."), no separado
# por un espacio. Con un espacio de mas en el patron, esas dos lineas
# salen como "no reconocidas" y se pierde justo el IB en uso.
LINEA = re.compile(
    r"\s*(>?) ?\[(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)\]\s+size\s+(\d+)\s+"
    r"protected by (0x[0-9a-fA-F]+) on context (\d+)")

# amdgpu_ib.c:486-498. Los tres pools, en el orden en que se vuelcan.
POOLS = ["DELAYED", "IMMEDIATE", "DIRECT"]


def parsea(texto):
    """
    Devuelve (pools, lineas_no_reconhecidas).

    Se separan las lineas que no casan con el formato. Descartarlas en
    silencio haria que un cambio de formato del driver pareciese un pool
    vacio, que es un resultado con aspecto de verdad.
    """
    pools = {}
    desconocidas = []
    actual = None
    for ln in texto.splitlines():
        m = re.match(r"-+\s+([A-Z]+)\s+-+", ln.strip())
        if m:
            actual = m.group(1)
            pools.setdefault(actual, [])
            continue
        if not ln.strip():
            continue
        mm = LINEA.match(ln)
        if mm and actual:
            marca, lo, hi, sz, prot, ctx = mm.groups()
            pools[actual].append({
                "lo": int(lo, 16), "hi": int(hi, 16), "size": int(sz),
                "prot": int(prot, 16), "ctx": int(ctx),
                # El '>' inicial marca el IB que esta EN USO en este
                # momento. No es un fallo de formato: es un estado, y
                # descartar la linea habria perdido justo ese dato.
                "en_uso": marca == ">",
            })
        else:
            desconocidas.append(ln)
    return pools, desconocidas


def main():
    ap = argparse.ArgumentParser(
        description="analiza los pools de IB que vuelca amdgpu_sa_info")
    ap.add_argument("fichero", nargs="?",
                    default="capturas/amdgpu_sa_info.txt")
    a = ap.parse_args()
    if not os.path.exists(a.fichero):
        print("no existe %s" % a.fichero)
        print("Se obtiene con: RX550_SUDO_PASS=... captura.py")
        return 2

    texto = open(a.fichero, errors="replace").read()
    pools, desconocidas = parsea(texto)

    print("=" * 78)
    print("POOLS DE IB DEL DRIVER (amdgpu_sa_info)")
    print("=" * 78)
    print("fuente de las llamadas: amdgpu_ib.c:486-498")
    print("LAS DIRECCIONES SON FISICAS del sistema, no VAs de GPU.")
    print()
    print("%-10s %-6s %-10s %-10s %s"
          % ("pool", "n", "bytes", "rango fisico", "formato"))
    print("-" * 78)
    total = 0
    rangos = []
    for p in POOLS:
        items = pools.get(p, [])
        if not items:
            print("%-10s %-6d %-10s %-10s %s"
                  % (p, 0, "-", "-", "pool vacio o ausente"))
            continue
        lo = min(x["lo"] for x in items)
        hi = max(x["hi"] for x in items)
        by = sum(x["size"] for x in items)
        total += by
        rangos.append((lo, hi, by, p))
        print("%-10s %-6d %-10d 0x%x-0x%x %d lineas"
              % (p, len(items), by, lo, hi, len(items)))
    print("-" * 78)
    print("total de bytes en IBs vivos: %d" % total)
    print()

    if desconocidas:
        print("LINEAS NO RECONOCIDAS: %d" % len(desconocidas))
        for ln in desconocidas[:5]:
            print("  %r" % ln[:90])
        print("  Si el driver cambio el formato, esto es lo que se ve.")
        print("  No se ignoran: ignorarlas haria que un pool vacio pareciera")
        print("  un pool que no tiene buffers.")
        print()

    # Los tamanos de IB. Si hay un unico tamano dominante, es el tamano de
    # un IB de trabajo normal, y eso si es util.
    tam = Counter()
    for p in POOLS:
        for x in pools.get(p, []):
            tam[x["size"]] += 1
    if tam:
        print("TAMANOS DE IB:")
        for s, n in tam.most_common(8):
            print("  %8d bytes  x%-5d %s" % (s, n, "(dominante)" if n > 50 else ""))
        dom = tam.most_common(1)[0]
        print("  El dominante es %d bytes, %d veces. Es el tamano del IB"
              % (dom[0], dom[1]))
        print("  de trabajo normal que el driver reutiliza.")
        print()

    # La distancia entre buffers consecutivos, que es la unidad de asignacion.
    if rangos:
        lo, hi, by, p = rangos[0]
        items = sorted(pools[p], key=lambda x: x["lo"])
        gaps = Counter()
        for i in range(1, len(items)):
            gaps[items[i]["lo"] - items[i - 1]["hi"]] += 1
        if gaps:
            print("HUECOS entre buffers consecutivos (pool %s):" % p)
            for g, n in gaps.most_common(4):
                print("  %6d bytes  x%-5d" % (g, n))
            print("  Un hueco de 0 significa que los buffers son contiguos.")
            print()

    # EL IB EN USO. El '>' lo marca y es el ultimo de su pool.
    en_uso = []
    for p in POOLS:
        for x in pools.get(p, []):
            if x["en_uso"]:
                en_uso.append((p, x))
    print("IB EN USO (marcado con '>'):")
    if not en_uso:
        print("  ninguno. Ningun IB estaba marcado como en uso en el")
        print("  momento del volcado, lo cual es coherente con que la GPU")
        print("  estuviera ociosa.")
    else:
        for p, x in en_uso:
            print("  pool %-10s fisico 0x%x-0x%x  %d bytes  context %d"
                  % (p, x["lo"], x["hi"], x["size"], x["ctx"]))
        print("  Un '>' por pool como maximo. Si hubiera mas de uno por")
        print("  pool, el marcador no significaria 'el actual' y habria")
        print("  que revisar que significa.")
    print()

    # Contextos: cuantos hay, y si un mismo contexto usa varios pools.
    print("CONTEXTOS:")
    todos = {}
    for p in POOLS:
        for x in pools.get(p, []):
            todos.setdefault(x["ctx"], set()).add(p)
    print("  contextos distintos: %d" % len(todos))
    multip = sum(1 for v in todos.values() if len(v) > 1)
    print("  contextos que usan MAS DE UN pool: %d" % multip)
    if multip:
        print("  Un contexto en varios pools significa que la misma")
        print("  submission tiene buffers en mas de una etapa.")
    print()

    # EL BLOQUE HONESTO
    print("LO QUE NO SE INTERPRETA")
    prot = Counter()
    for p in POOLS:
        for x in pools.get(p, []):
            prot[x["prot"]] += 1
    print("  'protected by' tiene %d valores distintos (de 0x%x a 0x%x)."
          % (len(prot), min(prot), max(prot)))
    print("  Se cuenta pero NO se interpreta: la cadena 'protected by 0x' no")
    print("  existe en el corpus. amdgpu_sa_bo_dump_debug_info se llama desde")
    print("  amdgpu_ib.c:491 y no esta definido en ninguna de las tres")
    print("  raices. Es una ruta no descifrada.")
    print()
    print("  Los valores mas frecuentes:")
    for v, n in prot.most_common(4):
        print("    0x%-6x x%d" % (v, n))
    print()
    print("  Un patron de 3 valores NO es una mascara de bits. Cuando se vio")
    print("  1, 3, 2 en los primeros, parece una rotacion de proteccion.")
    print("  Hay %d valores distintos: era un contador, y el patron era"
          % len(prot))
    print("  como empieza la secuencia. Reconocer eso ANTES de escribirlo")
    print("  como mascara habria evitado un hallazgo falso.")
    print()

    # AUTOCOMPROBACION. Se ejecuta siempre, no solo en un test aparte.
    #
    # La version anterior de este regex exigia un espacio entre el '>' y el
    # corchete, y el volcado real lo pone pegado. Las dos lineas marcadas
    # salian como "no reconocidas" y el IB en uso desaparecia del informe
    # sin que nada fallara: el pool seguia teniendo 654 entradas, asi que
    # los numeros grandes seguian siendo ciertos y solo faltaba el dato
    # interesante.
    #
    # Un parser que pierde el 1% de las lineas y no lo dice es peor que uno
    # que las rechaza todas, porque el rechazo se ve y la perdida no.
    fallos = []
    if desconocidas:
        fallos.append("%d lineas no se interpretan; el formato puede haber"
                      " cambiado" % len(desconocidas))
    n_en_uso = len(en_uso)
    n_pools_con = len(set(p for p, _ in en_uso))
    if n_en_uso > n_pools_con:
        fallos.append("mas de un IB marcado en uso en el mismo pool: el "
                      "marcador no significa 'el actual'")
    for p in POOLS:
        for x in pools.get(p, []):
            if x["hi"] - x["lo"] != x["size"]:
                fallos.append("pool %s: [0x%x,0x%x) mide %d pero size dice %d"
                              % (p, x["lo"], x["hi"], x["hi"] - x["lo"],
                                 x["size"]))
                break
    if fallos:
        print("AUTOCOMPROBACION FALLIDA:")
        for f in fallos:
            print("  - %s" % f)
        print()
        print("  Los datos de arriba se imprimen, pero NO son de fiar hasta")
        print("  que esto se arreglo. Un informe que avisa de su propia")
        print("  escritura es mas util que uno que presenta medio dato")
        print("  como si fuera entero.")
        return 1
    print("AUTOCOMPROBACION: todas las lineas se interpretan, los rangos")
    print("  cuadran con size, y hay como maximo un IB en uso por pool.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
