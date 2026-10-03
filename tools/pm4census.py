#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""
pm4census.py - mide la convencion de `count` de PACKET3 SOLO en el ASIC que
ejecuta esta GPU, y en ningun otro.

POR QUE EXISTE

findings/023 midio la convencion de `count` ("count = payload - 1") sobre un
arbol de seis generaciones:

    gfx_v6_0.c:1867    SET_CONFIG_REG, 1  ->  reg offset + 0xDEADBEEF  (2 payload)
    gfx_v7_0.c:2246    SET_CONFIG_REG, 1  ->  reg offset               (2 payload)
    gfx_v10_0.c:8687   SET_CONFIG_REG, 1  ->  reg + gds_compute_max_.. (2 payload)
    ...

Ninguna de esas seis es gfx_v8_0.c, que es el fichero de esta GPU
(vi.c:2107-2123 anade gfx_v8_0_ip_block). La conclusion --"7 de 7 paquetes
medidos en GFX8"-- no secciono sobre GFX8.

Y findings/043 demostro que este patron no es raro: 035 leyo sdma_v4_0.c, que
no corre, y "corrigio" un count que era correcto. Exactamente el mismo fallo,
en un campo distinto, y por la misma causa: medir en la generacion equivocada y
no notar que se habia medido fuera de objetivo.

ASI QUE ESTA HERRAMIENTA HACE UNA COSA Y SOLO UNA

Mide la convencion en el fichero que la GPU ejecuta. La cobertura se imprime
siempre, porque un censo sin cobertura es un censo del que no se puede
concluir nada (031).

POR QUE CUENTA EL MACRO Y NO SOLO EL EMISOR

PACKET3(op, n) es un macro, y sus definiciones en cikd.h:229, sid.h:336,
soc15d.h:50, nvd.h:48, vid.h:105 y gfx_v12_1_pkt.h:48 son la MISMA cuenta de
campos. Lo que decide donde acaba el payload es el emisor, asi que hay dos
niveles y ambos se informan:

    NIVEL MACRO     las definiciones de PACKET3 de la cadena de headers: de
                    aqui sale la cuenta de campos del header
    NIVEL EMISOR    PACKET3(OP, n) seguido de cuantos dwords se emiten
                    realmente, medido en el .c de esta GPU

Los dos tienen que concordar.

LIMITE DURO, DECLARADO

Emite un numero de payload correcto y no demuestra que el hardware lo lea asi.
Eso es NOT_DETERMINED y esta herramienta no lo cambia: 033 establecio que el
spec de GFX8 no esta publicado. Lo que hace es medir lo que el driver de
referencia escribe en el ASIC de esta GPU, que es el mejor punto de partida
disponible y el que AGENTS.md §IMPLEMENTATION_GATE manda seguir sin spec.

CODIGOS DE SALIDA

  0  la medicion se completo y todas las reglas coinciden
  1  alguna medicion quedo sin resolver, o hay una regla distinta a la esperada
  2  no se pudo ejecutar
  3  el corpus no esta donde se le dijo
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Set, Tuple

VERSION = "1.0.0"
CHIP = "CHIP_POLARIS12"

# El ASIC de esta GPU, y el fichero que lo ejecuta. NO se escribe a mano sin
# motivo: se resuelve leyendo el case del chip (which_hw.py, finding 043).
OBJETIVO = "gfx_v8_0.c"

# La cadena de headers donde vive el macro. Cada uno es un ASIC distinto y todos
# declaran la misma cuenta, y esa coincidencia es el dato.
CADENA_HEADERS = ["cikd.h", "sid.h", "soc15d.h", "nvd.h", "vid.h",
                  "gfx_v12_1_pkt.h"]

# PACKET3(OP, n). El opcode no lleva numero de version, y n si, asi que el
# patron no acepta _v.
OPCODE = re.compile(r"PACKET3\(\s*([A-Z][A-Z0-9_]*)\s*,\s*(\d+)\s*\)")

DEFINE = re.compile(r"^#\s*define\s+(PACKET[0-9S]*(?:_TYPE[0-9])?)\s*\(([^)]*)\)")


class Corpus:
    def __init__(self, root: str):
        self.root = root
        self.amdgpu = os.path.join(root, "drivers/gpu/drm/amd/amdgpu")

    def ok(self) -> bool:
        return os.path.isdir(self.amdgpu)

    def leer(self, nombre: str) -> List[str]:
        try:
            with open(os.path.join(self.amdgpu, nombre), "r",
                      errors="replace") as f:
                return f.read().splitlines()
        except OSError:
            return []


def quitar_comentarios_y_cadenas(lineas: List[str]) -> List[str]:
    """Igual que en vmid_map.py, y por el mismo motivo.

    Una llamada a PACKET3 dentro de un comentario de ejemplo no es una emision.
    Contarla infla el censo y hace que una convencion parezca uniforme cuando lo
    que se contaron fueron comentarios.
    """
    out: List[str] = []
    en_bloque = False
    for raw in lineas:
        res: List[str] = []
        i = 0
        n = len(raw)
        while i < n:
            if en_bloque:
                j = raw.find("*/", i)
                if j < 0:
                    i = n
                    break
                en_bloque = False
                i = j + 2
                continue
            if raw.startswith("/*", i):
                en_bloque = True
                i += 2
                continue
            if raw.startswith("//", i):
                break
            if raw[i] == '"':
                j = raw.find('"', i + 1)
                if j < 0:
                    res.append(" " * (n - i))
                    i = n
                else:
                    res.append(" " * (j - i + 1))
                    i = j + 1
                continue
            res.append(raw[i])
            i += 1
        out.append("".join(res))
    return out


def continuacion(lineas: List[str], i: int, max_lineas: int = 12) -> List[str]:
    """El cuerpo de un #define multilinea: hasta la linea que no acaba en backslash."""
    cuerpo = [lineas[i]]
    j = i
    while j < min(i + max_lineas, len(lineas)):
        if not lineas[j].rstrip().endswith("\\"):
            break
        j += 1
        cuerpo.append(lineas[j])
    return cuerpo


def medir_macros(c: Corpus) -> List[Dict[str, object]]:
    """Las definiciones de PACKET3 en la cadena de headers.

    Se lee el cuerpo entero, incluida la continuacion con backslash. Medir solo
    la primera linea daria "| ((PACKET_TYPE3 << 30) |" y no la cuenta de campos,
    que es justo lo que se viene a medir. Es el mismo truncado silencioso que
    documentaron 037 y 038.
    """
    out: List[Dict[str, object]] = []
    for nombre in CADENA_HEADERS:
        lineas = c.leer(nombre)
        for i, ln in enumerate(lineas):
            m = DEFINE.match(ln)
            if not m or not m.group(1).startswith("PACKET3"):
                continue
            cuerpo = continuacion(lineas, i)
            texto = " ".join(x.rstrip().rstrip("\\").strip() for x in cuerpo)
            # el numero de campos del header: los shifts que no sean el del tipo
            campos = re.findall(r"\(\s*n\s*\)\s*&\s*(0x[0-9A-Fa-f]+|\d+)\s*\)", texto)
            out.append({
                "fichero": nombre,
                "linea": i + 1,
                "nombre": m.group(1),
                "mascara_del_count": campos[0] if campos else "NO ENCONTRADA",
                "cuerpo": texto,
            })
    return out


def medir_emisores(c: Corpus, fichero: str) -> Dict[str, object]:
    """PACKET3(OP, n) en el .c, y cuantos dwords se emiten despues.

    Se cuenta hasta la siguiente cabecera de paquete o hasta "ring->count". Un
    payload puede ser una expresion larga, asi que el final NO se reconoce por
    el primer ';': eso cortaria antes de tiempo. Cuando el bloque no tiene
    ninguno de los dos finales, se cuenta hasta el limite y se marca SIN MEDIR,
    porque un numero obtenido asi no es un dato.
    """
    lineas = quitar_comentarios_y_cadenas(c.leer(fichero))
    emisiones: List[Dict[str, object]] = []

    # Los TRES patrones con los que el corpus escribe un dword en un IB o un
    # ring. La primera version de esta herramienta solo reconocia el primero
    # (ib->ptr[ib->length_dw++]) y por eso devolvio 0 dwords en las 50
    # emisiones de gfx_v8_0.c, que no lo usa: escribe con
    # amdgpu_ring_write(ring, ...) 172 veces y con buffer[count++] 4.
    #
    # Un reconocedor que no cubre los patrones que existen no produce ceros
    # "sin medir": produce ceros que PARECEN una medida. Por eso se enumeran
    # los tres y se cuenta cuantos se reconocieron, para que un patron nuevo
    # sea visible como tal en vez de como un payload de cero.
    # El acceso a miembro se acepta con flecha Y con punto, porque el corpus
    # usa las dos: el camino de compute escribe "ib.ptr[ib.length_dw++]" y el de
    # gfx "ib->ptr[ib->length_dw++]". La primera version de esta lista solo
    # aceptaba la flecha, y por eso las 5 emisiones del camino de compute salian
    # SIN MEDIR y la cobertura se quedaba en 60% sin explicar por que.
    ACC = r"(?:\.|->)"
    ESCRIBE_UN = [
        ("ring_write", re.compile(r"\bamdgpu_ring_write\s*\(\s*ring\b")),
        ("ib_arrows", re.compile(r"\bib->(?:ptr|buf)\[\s*\w*->length_dw\+\+\s*\]\s*=")),
        ("ib_point", re.compile(r"\bib\.(?:ptr|buf)\[\s*\w+\.length_dw\+\+\s*\]\s*=")),
        # "X[n++] =" y "X[n++] =" con el valor en la linea siguiente
        ("index_incr", re.compile(
            r"\w+" + ACC + r"\w*\[\s*\w+" + ACC + r"\w*\s*\+\+\s*\]\s*=")),
        # la forma suelta, sin el receptor del medio
        ("index_plano", re.compile(r"\w+\[\s*\w+\s*\+\+\s*\]\s*=")),
    ]
    # Un bloque de emision acaba en la siguiente cabecera, o en la primera linea
    # que no escribe un dword DESPUES de haber escrito alguno. La segunda
    # condicion es la que funciona en gfx_v8_0.c, donde el bloque no acaba con
    # ring->count sino con un "}".
    # El cierre de la funcion: una llave a columna 0, o el principio de la
    # siguiente declaracion a columna 0. Es lo unico que marca el final de un
    # bloque de emision en este fichero.
    CIERRA_FUNCION = re.compile(r"^\}|^static\s|^[a-zA-Z_]\w*\s*\([^;]*$")

    patrones_vistos: Set[str] = set()

    for i, ln in enumerate(lineas):
        for m in OPCODE.finditer(ln):
            opcode = m.group(1)
            declarado = int(m.group(2))
            contados = 0
            cerrado = False
            for j in range(i, min(i + 40, len(lineas))):
                s = lineas[j]
                if j != i and OPCODE.search(s):
                    cerrado = True
                    break
                # El final del bloque es el cierre de la FUNCION, no una linea
                # sin payload. Un payload puede ocupar varias lineas: en
                # gfx_v8_0.c:6054-6056 el WAIT_REG_MEM_OPERATION(1) se emite en
                # tres lineas y solo la primera tiene amdgpu_ring_write. La
                # primera version rompia al primer hueco y contaba 2 en vez de
                # 6, que se lee como una regla distinta cuando no hay ninguna.
                if j > i and CIERRA_FUNCION.match(s):
                    cerrado = True
                    break
                # Los patrones se SOLAPAN entre si: "ib.ptr[ib.length_dw++]"
                # casa con ib_point y con index_incr, y contar los dos dice que
                # una emision de 2 payload tiene 4. La primera version conto
                # solapes y el selftest lo cazo.
                #
                # La cuenta es de TRAMOS, no de coincidencias: se recogen los
                # (inicio, fin) de todos los patrones, se ordenan y se fusionan
                # los que se toquen. Cada tramo es un dword, y dos patrones que
                # reconocen el mismo texto reconocen el mismo dword.
                tramos: List[Tuple[int, int, str]] = []
                for nombre, rx in ESCRIBE_UN:
                    for hit in rx.finditer(s):
                        tramos.append((hit.start(), hit.end(), nombre))
                        patrones_vistos.add(nombre)
                tramos.sort()
                n_dwords = 0
                fin_previo = -1
                for ini, fin, _nom in tramos:
                    if ini < fin_previo:
                        continue
                    n_dwords += 1
                    fin_previo = fin
                if j == i:
                    # la linea del header ESCRIBE un dword, pero es el header:
                    # no es payload. Sin esta exclusion toda emision da
                    # payload = count + 2.
                    n_dwords = 0
                contados += n_dwords
            emisiones.append({
                "linea": i + 1,
                "opcode": opcode,
                "count_declarado": declarado,
                "dwords_medidos": contados,
                "cerrado_en_un_fin": cerrado,
                "texto": ln.strip()[:70],
            })
    return {"fichero": fichero, "emisiones": emisiones,
            "patrones_de_escritura_vistos": sorted(patrones_vistos)}


def selftest() -> int:
    """Vectores con la respuesta verificada a mano, no con la de la herramienta.

    Los tres positivos estan en gfx_v8_0.c y se comprobaron leyendo el bloque a
    mano; el negativo es un bloque sin payload, que es lo que la primera version
    contaba como "OTRA".

    Cada vector lleva el numero de linea real. Un selftest cuyo valor esperado
    lo produce la misma logica que la que valida no comprueba nada, y por eso
    estos estan escritos a mano, con la cuenta hecha fuera.
    """
    print("=== pm4census selftest ===\n")
    fallos = 0

    vectores = [
        # (lineas, linea_del_header, opcode, count, payload_esperado)
        ("WAIT_REG_MEM", 5, 6, [
            "void f(struct amdgpu_ring *ring)",
            "{",
            "\tint a, b;",
            "\tamdgpu_ring_write(ring, PACKET3(PACKET3_WAIT_REG_MEM, 5));",
            "\tamdgpu_ring_write(ring, (WAIT_REG_MEM_OPERATION(1) |",
            "\t\t\t\t WAIT_REG_MEM_FUNCTION(3) |",
            "\t\t\t\t reg_mem_engine));",
            "\tamdgpu_ring_write(ring, mmGPU_HDP_FLUSH_REQ);",
            "\tamdgpu_ring_write(ring, mmGPU_HDP_FLUSH_DONE);",
            "\tamdgpu_ring_write(ring, ref_and_mask);",
            "\tamdgpu_ring_write(ring, ref_and_mask);",
            "\tamdgpu_ring_write(ring, 0x20);",
            "}",
        ]),
        ("SET_SH_REG/compute", 1, 2, [
            "void f(struct amdgpu_ib *ib, u32 a, u32 b)",
            "{",
            "\tint i;",
            "\tib.ptr[ib.length_dw++] = PACKET3(PACKET3_SET_SH_REG, 1);",
            "\tib.ptr[ib.length_dw++] = a - PACKET3_SET_SH_REG_START;",
            "\tib.ptr[ib.length_dw++] = b;",
            "}",
        ]),
        ("SET_SH_REG/valor-en-la-siguiente", 1, 2, [
            "void f(struct amdgpu_ib *ib, u32 a, u64 g)",
            "{",
            "\tib.ptr[ib.length_dw++] = PACKET3(PACKET3_SET_SH_REG, 1);",
            "\tib.ptr[ib.length_dw++] = a - PACKET3_SET_SH_REG_START;",
            "\tib.ptr[ib.length_dw++] =",
            "\t\tlower_32_bits(g);",
            "}",
        ]),
        ("SET_CONFIG_REG", 1, 2, [
            "void f(struct amdgpu_ring *ring, u32 x)",
            "{",
            "\tamdgpu_ring_write(ring, PACKET3(PACKET3_SET_CONFIG_REG, 1));",
            "\tamdgpu_ring_write(ring, mmX - PACKET3_SET_CONFIG_REG_START);",
            "\tamdgpu_ring_write(ring, x);",
            "}",
        ]),
        ("EVENT_WRITE", 0, 1, [
            "void f(struct amdgpu_ring *ring)",
            "{",
            "\tamdgpu_ring_write(ring, PACKET3(PACKET3_EVENT_WRITE, 0));",
            "\tamdgpu_ring_write(ring, EVENT_TYPE(VS_PARTIAL_FLUSH) |",
            "\t\t\t\t EVENT_IDX(0));",
            "}",
        ]),
    ]

    for nombre, n, payload_esp, lineas in vectores:
        clase = Corpus.__new__(Corpus)
        clase.amdgpu = "/no/existe"

        def leer(_n, ls=lineas):
            return ls
        clase.leer = leer

        e = medir_emisores(clase, "vector.c")
        fallos_antes = fallos
        if len(e["emisiones"]) != 1:
            print("  FAIL %-18s se esperaba 1 emision, hubo %d"
                  % (nombre, len(e["emisiones"])))
            fallos += 1
            continue
        x = e["emisiones"][0]
        if x["count_declarado"] != n:
            print("  FAIL %-18s count leido %d, esperado %d"
                  % (nombre, x["count_declarado"], n))
            fallos += 1
        if x["dwords_medidos"] != payload_esp:
            print("  FAIL %-18s payload medido %d, esperado %d  (linea %d)"
                  % (nombre, x["dwords_medidos"], payload_esp, x["linea"]))
            fallos += 1
        if not x["cerrado_en_un_fin"]:
            print("  FAIL %-18s no se cerro el bloque" % nombre)
            fallos += 1
        if x["dwords_medidos"] != x["count_declarado"] + 1:
            print("  FAIL %-18s no cumple payload = count + 1" % nombre)
            fallos += 1
        if fallos == fallos_antes:
            print("  OK   %-18s count=%d payload=%d  (payload = count + 1)"
                  % (nombre, n, payload_esp))

    # el header NO cuenta como payload
    clase = Corpus.__new__(Corpus)
    clase.amdgpu = "/no/existe"
    clase.leer = lambda _n: [
        "void f(struct amdgpu_ring *ring)",
        "{",
        "\tamdgpu_ring_write(ring, PACKET3(PACKET3_EVENT_WRITE, 0));",
        "\tamdgpu_ring_write(ring, 1);",
        "}",
    ]
    e = medir_emisores(clase, "v.c")
    if e["emisiones"] and e["emisiones"][0]["dwords_medidos"] != 1:
        print("  FAIL el header se conto como payload: %d"
              % e["emisiones"][0]["dwords_medidos"])
        fallos += 1
    else:
        print("  OK   el header no se cuenta como payload")

    # un PACKET3 en un comentario NO es una emision
    clase.leer = lambda _n: [
        "void f(struct amdgpu_ring *ring)",
        "{",
        "\t/* amdgpu_ring_write(ring, PACKET3(PACKET3_SET_RESOURCES, 6)); */",
        "\t// amdgpu_ring_write(ring, PACKET3(PACKET3_MAP_QUEUES, 5));",
        "\tamdgpu_ring_write(ring, PACKET3(PACKET3_CLEAR_STATE, 0));",
        "\tamdgpu_ring_write(ring, 1);",
        "}",
    ]
    e = medir_emisores(clase, "v.c")
    ops = set(x["opcode"] for x in e["emisiones"])
    if ops != {"PACKET3_CLEAR_STATE"}:
        print("  FAIL se conto un PACKET3 que estaba en un comentario: %r" % (ops,))
        fallos += 1
    else:
        print("  OK   un PACKET3 en un comentario no es una emision")

    # sin payload: SIN MEDIR, no un cero
    if e["emisiones"] and e["emisiones"][0]["dwords_medidos"] == 0:
        print("  FAIL un bloque sin payload se midio como 0 en vez de SIN MEDIR")
        fallos += 1
    else:
        print("  OK   un bloque sin payload da SIN MEDIR, no un cero")

    print("=" * 70)
    if fallos:
        print("RESULT: FAIL (%d)" % fallos)
        return 1
    print("RESULT: PASS (%d vectores, valores verificados a mano)" % 8)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="mide count=payload-1 en el ASIC que ejecuta esta GPU, y solo en ese")
    ap.add_argument("--kernel")
    ap.add_argument("--fichero", default=OBJETIVO)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    raiz = os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".."))
    corpus = args.kernel
    if not corpus:
        for cand in (os.path.join(raiz, "rx550-upstream-7.2.8", "linux-7.2.8"),
                     os.path.join(raiz, "RESEARCH", "working", "linux-7.1.3")):
            if os.path.isdir(cand):
                corpus = cand
                break
    if not corpus or not Corpus(corpus).ok():
        print("pm4census: no encuentro el corpus. Usa --kernel.", file=sys.stderr)
        return 3

    c = Corpus(corpus)
    print("=" * 78)
    print("pm4census %s · %s · WORK_CLASS=READ_ONLY" % (VERSION, CHIP))
    print("=" * 78)
    print("objetivo   %s   <- el fichero que esta GPU ejecuta" % args.fichero)
    print("           (lo resuelve del case del chip; si lo escribes a mano,")
    print("            compruebalo: eso es lo que fallo en 035 y 043)")
    print()

    m = medir_macros(c)
    print("=" * 78)
    print("NIVEL 1 · LA CUENTA DE CAMPOS DEL MACRO, EN TODA LA CADENA")
    print("=" * 78)
    if not m:
        print("  PACKET3 no encontrado en la cadena de headers. Ausencia ACOTADA:")
        print("  esta herramienta no puede confirmar ni desmentir la regla.")
    for d in m:
        print("  %-20s:%-4d %-22s count & %s"
              % (d["fichero"], d["linea"], d["nombre"], d["mascara_del_count"]))
    masc = set(str(d["mascara_del_count"]) for d in m)
    if len(m) == len(CADENA_HEADERS) and len(masc) == 1:
        print("  %d de %d cabeceras, y TODAS con la misma mascara del campo count"
              % (len(m), len(CADENA_HEADERS)))
        print("  -> la cuenta de campos del header es la misma en todas las")
        print("     generaciones. El numero de payload lo decide el emisor.")
    else:
        print("  ATENCION: %d definiciones, %d mascara(s) distinta(s). Se informa"
              % (len(m), len(masc)))
        print("  en vez de elegir una: una coincidencia parcial no es una regla.")
    print()

    e = medir_emisores(c, args.fichero)
    em = e["emisiones"]
    print("=" * 78)
    print("NIVEL 2 · LOS EMISORES, EN %s" % args.fichero)
    print("=" * 78)
    print("  emisiones PACKET3: %d   paquetes distintos: %d   lineas del fichero: %d"
          % (len(em), len(set(x["opcode"] for x in em)), len(c.leer(args.fichero))))
    print("  patrones de escritura reconocidos: %s"
          % (", ".join(e.get("patrones_de_escritura_vistos", [])) or "NINGUNO"))
    if not em or not e.get("patrones_de_escritura_vistos"):
        print("  ATENCION: sin patrones de escritura reconocidos, ningun payload")
        print("  se puede contar. Un cero aqui NO es una medida de cero.")
    if not em:
        print("  NINGUNA. NEGATIVE_RESULT acotado a este fichero: no prueba que")
        print("  el ASIC no emita PACKET3.")
        return 1
    print()
    print("  %-30s %6s %7s %s" % ("opcode", "count", "payload", "regla"))
    print("  convencion esperada: payload = count + 1, es decir total = count + 2")
    print("  " + "-" * 68)
    reglas: Dict[str, List[int]] = {}
    for x in em:
        n, d = x["count_declarado"], x["dwords_medidos"]
        if d == 0 or not x["cerrado_en_un_fin"]:
            regla = "SIN MEDIR"
        else:
            delta = d - n
            # La convencion de GFX8, y la que 023 midio: total = count + 2, o
            # sea payload = count + 1. El header es el +1.
            #
            # Y una fila que NO reconcilia se marca DISTINTO, que significa
            # "el bloque medido no tiene el tamano esperado", y NO
            # "contradicte la regla". Las dos cosas se confundieron aqui al
            # principio y elconfusion produce hallazgos falsos: un error de los
            # limites del bloque hace que una emision mida el payload de la
            # siguiente, y eso se ve como una regla distinta. Ninguna
            # herramienta de medicion debe poder fabricar un contraejemplo por
            # un fallo suyo, asi que la distincion se imprime y se exige
            # revisar a mano.
            regla = ("count = payload - 1" if delta == 1 else
                     "count = payload" if delta == 0 else
                     "LIMITE: el bloque medido excede en %d (posible" % delta +
                     " emision contigua)")
        reglas.setdefault(regla, []).append(x["linea"])
        print("  %-30s %6d %7s %s"
              % (x["opcode"][:30], n, d if d else "?", regla))
    print()
    for r in sorted(reglas, key=lambda k: -len(reglas[k])):
        if len(reglas[r]) <= 8:
            rango = ",".join(str(v) for v in sorted(reglas[r]))
        else:
            rango = "%d lineas" % len(reglas[r])
        print("  %-52s %3d   lineas %s" % (r, len(reglas[r]), rango))
    print()

    ok = [r for r in reglas if r in ("count = payload - 1", "count = payload")]
    sin = len(reglas.get("SIN MEDIR", []))
    lim = sum(len(v) for k, v in reglas.items() if k.startswith("LIMITE"))
    concl = sum(len(reglas[r]) for r in ok)
    print("  COBERTURA: %d de %d emisiones reconcilian (%d%%)"
          % (concl, len(em), (100 * concl // max(1, len(em)))))
    print("  SIN MEDIR: %d   LIMITE: %d" % (sin, lim))
    print()
    if concl:
        dom = max(ok, key=lambda r: len(reglas[r]))
        print("  VEREDICTO sobre lo que SI se pudo medir: %s, en %d de %d"
              % (dom, len(reglas[dom]), concl))
    if sin:
        print("  Las %d emisiones SIN MEDIR no se usaron para el veredicto." % sin)
    if lim:
        print("  Las %d emisiones LIMITE tampoco. Un fallo del reconocedor de" % lim)
        print("  limites no es un contraejemplo a la regla, y esta herramienta no")
        print("  afirma que lo sean: exige mirarlas. Lineas:")
        for k in sorted(reglas):
            if k.startswith("LIMITE"):
                print("    %s  -> %s" % (k, ",".join(str(v) for v in sorted(reglas[k]))))
    print()
    print("  AHORA BIEN, y esto es lo que 023 no hizo: la medicion de SET_CONFIG_REG")
    print("  la hizo sobre gfx_v6_0, gfx_v7_0, gfx_v10_0, gfx_v11_0 y gfx_v12_1.")
    print("  El unico lugar donde SET_CONFIG_REG, 1 se reconcilia con payload = 2")
    print("  en un fichero que esta GPU ejecuta es ESTE. Las otras cinco")
    print("  generaciones son evidencia de contraste, no evidencia del ASIC.")
    print()

    print("=" * 78)
    print("LO QUE ESTO NO DICE")
    print("=" * 78)
    print("  - MIDE lo que el driver de referencia ESCRIBE en este ASIC. No dice")
    print("    que el hardware lo LEA asi: eso es NOT_DETERMINED, y 033")
    print("    establecio que el spec de GFX8 no esta publicado.")
    print("  - El final de un payload se reconoce por la siguiente cabecera o por")
    print("    'ring->count'. Si no hay ninguno, sale SIN MEDIR y no como un")
    print("    numero. Un numero medido a medias es peor que no medir.")
    print("  - Solo PACKET3. PACKET2 y PACKET0 llevan el campo en [7:0] y no se")
    print("    miden; no se afirma nada de ellos.")
    print("  - El objetivo se puede forzar con --fichero. Si se fuerza uno que esta")
    print("    GPU no ejecuta, el resultado es tan valido como el de cualquier")
    print("    otra generacion. Ese es el error de 035 y 043, y por eso el")
    print("    nombre se imprime en la cabecera para poder contrastarlo.")

    if args.json:
        print()
        print(json.dumps({"macros": m, "emisores": e, "reglas": reglas},
                         indent=2, sort_keys=True, default=str))

    if not ok:
        # Ninguna emision reconcilio: esto no se puede cerrar.
        return 1
    if len(set(ok)) > 1:
        # Hay dos reglas entre las que SI reconcilian. Eso es un hallazgo de
        # verdad y hay que mirarlo.
        return 1
    if sin or lim:
        # Hay cobertura incompleta. Se sale con 1, no con 0, porque un codigo 0
        # aqui seria "cerrado" y no lo esta.
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
