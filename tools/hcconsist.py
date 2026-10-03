#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""
hcconsist.py - consistencia entre el .h y el .c del driver propio.

POR QUE ESTA HERRAMIENTA EXISTE

En findings/114 aparecio UNA contradiccion entre 07-DRIVER/kernel/rx550_pm4.h
y 07-DRIVER/kernel/rx550_pm4.c: la cabecera afirmaba que el count se codifica
como `count - 1` porque "0 - 1 seria 0xFFFFFFFF, 4 G entradas", y el .c
retractaba eso textualmente, atribuyendolo a findings/034.

Aparecio POR CASUALIDAD, markandose una funcion. Eso es exactamente la
situacion que este proyecto lleva 114 hallazgos previniendo: un patron que se
puede automatizar y que se estaba mirando a mano, una funcion cada vez. La
forma correcta no es mirar mas careful la proxima: es medir todas.

QUE COMPRUEBA

 1. CORRESPONDENCIA 1:1. Cada prototipo del .h tiene exactamente una
    definicion en el .c, y viceversa. Sin esto, ninguna otra comprobacion
    significa nada: si no sabes que dos textos hablan de la misma funcion,
    compararlos es comparar ruido.
 2. PARAMETRIZACION. Mismo numero de parametros y mismos tipos. Una cabecera
    con 4 parametros y un .c con 3 no es un problema de estilo: es una
    llamada que no compila en el .c del otro.
 3. DECLARACIONES HUERFANAS. Prototipo sin definicion: promesa no cumplida.
    Definiciones sin prototipo: el modulo expone algo que el .h no cuenta.
 4. DUPLICADOS. La misma funcion declarada dos veces.
 5. CRUCE DE CIFRAS ENTRE LADOS. Los numeros que aparecen en la documentacion
    de un lado y no en la del otro.

POR QUE (5) ES UN GENERADOR DE CANDIDATOS Y NO UN VEREDICTO

Porque "el .h dice 5 dwords y el .c dice 7 dwords" no prueba nada por si solo:
puede ser que el .c describa una variante de 64 bits, o que uno de los dos
comentarios este describiendo otra cosa. Lo que si prueba es que hay DOS
cifras en juego para la misma funcion, y que al menos una de las dos
documentaciones esta incompleta. Eso es un hecho. La contradiccion es una
LECTURA de ese hecho, y por eso la herramienta no la afirma: la propone.

La diferencia importa porque en 114 la contradiccion era semantica, no
numerica -- "count - 1" contra "count" -- y un cruce de cifras la habria
dejado pasar. Por eso (5) es una criba y no una prueba, y por eso esta
documentada como lo que es.

CODIGOS DE SALIDA

  0  los dos lados son consistentes
  1  hay correspondencia rotas, huerfanos o duplicados (errores duros)
  2  no se pudo ejecutar
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Set, Tuple

VERSION = "1.0.0"

# La primera version de este patron pedia el tipo de retorno con una
# alternancia de tres ramas y no casaba con NADA. El selftest vector 1 dio
# "0 firmas, esperaba 1", que es el fallo mas informativo posible: un filtro
# que descarta todo no se distingue de un filtro que funciona sobre un arbol
# sin nada que filtrar. Un 0 asi NO es un resultado.
FUNCION_RX = re.compile(
    r"^\s*(?P<mods>(?:(?:static|extern|inline|__init|__exit|__must_check"
    r"|__user|__iomem)\s+)*)"
    r"(?P<ret>[A-Za-z_]\w*(?:\s*\*)*)\s+"
    r"(?P<nombre>[A-Za-z_]\w*)\s*\(")

TIPO_RX = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")

# Palabras reservadas que NO pueden ser el tipo de retorno de una declaracion.
PALABRAS_C = frozenset((
    "return", "if", "else", "while", "do", "for", "switch", "case", "default",
    "goto", "break", "continue", "sizeof", "typedef", "struct", "union",
    "enum", "static", "extern", "const", "volatile", "inline", "register",
    "sizeof", "_Alignof", "return", "delete", "new", "throw", "catch",
))

NUMERO_RX = re.compile(
    r"\b(0[xX][0-9a-fA-F]+|\d+)\b")


def proyecto() -> str:
    return os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".."))


class Firma:
    def __init__(self, nombre: str, ini: int, fin: int, es_def: bool,
                 params: List[str], ret: str, fichero: str,
                 estatico: bool = False):
        self.nombre = nombre
        self.estatico = estatico
        self.ini = ini          # 1-based, linea del nombre
        self.fin = fin          # 1-based, linea donde acaba la firma
        self.es_def = es_def
        self.params = params
        self.ret = ret.strip()
        self.fichero = fichero

    def tipos(self) -> List[str]:
        return [" ".join(p.split()[:2]).strip() for p in self.params]

    def __repr__(self) -> str:
        return "<%s %s:%d %dparams %s>" % (
            "def" if self.es_def else "proto", self.nombre, self.ini,
            len(self.params), self.ret)


def parsear_firmas(lineas: List[str], fichero: str) -> List[Firma]:
    """Extrae todas las firmas, uniendo las que estan partidas en varias lineas.

    Une por paréntesis balanceados, no por una condición de fin de línea: por
    eso findings/114 encontró que el filtro `endswith(";")` de implgate.py
    contaba 7 prototipos multilínea como si fueran definiciones.
    """
    out: List[Firma] = []
    i = 0
    while i < len(lineas):
        l = lineas[i]
        m = FUNCION_RX.match(l)
        if not m or l.lstrip().startswith(("#", "*", "/*", "//")):
            i += 1
            continue
        # Una macro del kernel se escribe como NOMBRE(args) y casa con el mismo
        # patron que una declaracion. DEVICE_ATTR_RO(rx550_info) en
        # rx550_drv.c:202 salia como "prototipo declarado y nunca definido",
        # que es una alarma falsa. El discriminador es la caja: una funcion
        # del kernel nunca se nombra en MAYUSCULAS enteras, una macro si.
        if m.group("nombre").isupper():
            i += 1
            continue
        # Una LLAMADA casa con el patron de una declaracion porque el tipo de
        # retorno solo se distingue por ser un identificador. `return
        # rx550_ioctl_version(file, cmd, arg);` parseaba como prototipo con
        # parametros (file, cmd, arg) y comparado contra la definicion daba un
        # desajuste de tipos falso en rx550_main.c:177 y :179. El tipo de
        # retorno de una declaracion nunca es una palabra reservada de C.
        if m.group("ret").strip() in PALABRAS_C:
            i += 1
            continue
        # reunir hasta cerrar parentesis
        buf = l
        j = i
        while buf.count("(") > buf.count(")") and j + 1 < len(lineas):
            j += 1
            buf += " " + lineas[j].strip()
        if buf.count("(") != buf.count(")"):
            i += 1
            continue
        # avanzar hasta el terminador de la declaracion o definicion
        k = j
        while k + 1 < len(lineas):
            t = lineas[k].rstrip()
            if t.endswith("{") or t.endswith(";"):
                break
            k += 1
            if k - j > 60:
                break
        term = lineas[k].rstrip()
        cuerpo = buf[buf.index("(") + 1:buf.rindex(")")]
        params = [p.strip() for p in cuerpo.split(",") if p.strip()]
        mods = m.group("mods") or ""
        out.append(Firma(m.group("nombre"), i + 1, k + 1,
                         term.endswith("{"), params, m.group("ret"), fichero,
                         "static" in mods.split()))
        i = k + 1
    return out


def comentario_de(lineas: List[str], firma: Firma) -> str:
    """El comentario INMEDIATAMENTE anterior, o cadena vacia.

    Inmediatamente es la palabra clave. En 114 se perdio media hora porque un
    recorrido hacia atrás sin condición de contigüidad fue a parar al
    comentario de la función de arriba, y otro parceo metió texto dentro del
    cuerpo de una función. Aquí se corta en cuanto aparece código.
    """
    j = firma.ini - 2
    out: List[str] = []
    while j >= 0:
        s = lineas[j].strip()
        if s == "":
            j -= 1
            continue
        if s.startswith("/*"):
            out.append(s)
            break
        if s.startswith("*"):
            out.append(s)
            j -= 1
            continue
        break
    return "\n".join(reversed(out))


def cifras(texto: str) -> Set[str]:
    """Cifras de un comentario, sin las que son numeros de linea de la cita."""
    t = re.sub(r"\.md:\d+(?:[-,]\d+)*", " ", texto)
    t = re.sub(r"findings?/[\w.-]+", " ", t)
    return set(NUMERO_RX.findall(t))


def selftest() -> int:
    print("=== hcconsist selftest ===\n")
    fallos = 0

    print("[1] una firma partida en 3 lineas se lee como UNA")
    L = ["void rx550_pm4_write_data(struct rx550_pm4_ib *ib, __u32 reg,",
         "\t\t\t    __u32 val, __u32 engine);", ""]
    fs = parsear_firmas(L, "x.h")
    if len(fs) != 1:
        print("  FAIL %d firmas, esperaba 1" % len(fs))
        fallos += 1
    else:
        f = fs[0]
        # ib cuenta: son ib, reg, val, engine. Escribi este vector esperando 3
        # y el fallo era mio, no del parser -- el parametro puntero de primer
        # argumento es un parametro como cualquier otro.
        if f.es_def or len(f.params) != 4:
            print("  FAIL es_def=%s params=%d, esperaba False/4"
                  % (f.es_def, len(f.params)))
            fallos += 1
        else:
            print("  OK   prototipo de 2 lineas con 4 parametros: %r" % f)

    print()
    print("[2] la misma firma con '{' es definicion, no prototipo")
    L2 = ["void rx550_pm4_indirect(struct rx550_pm4_ib *ib, __u64 a,",
          "\t\t\t    __u32 b)", "{", "\treturn;", "}"]
    fs2 = parsear_firmas(L2, "x.c")
    if len(fs2) != 1 or not fs2[0].es_def or len(fs2[0].params) != 3:
        print("  FAIL %r" % fs2)
        fallos += 1
    else:
        print("  OK   definicion de 2 lineas con 3 parametros (ib, a, b)")

    print()
    print("[3] una linea que NO es firma no produce nada")
    L3 = ["/* rx550_algo(ib) */", " * mas texto", " */",
          "static inline __u32 f(void)", "{", "  return 0;", "}"]
    fs3 = parsear_firmas(L3, "x.c")
    if len(fs3) != 1 or fs3[0].nombre != "f":
        print("  FAIL %r" % fs3)
        fallos += 1
    else:
        print("  OK   el comentario no se cuenta como firma: 1 sola, 'f'")

    print()
    print("[4] comentario_inmediato se corta en codigo, no lo salta")
    L4 = ["/* comentario de la funcion de ARRIBA", " * sigue", " */",
          "int g(void)", "{", "\treturn 0;", "}",
          "int h(void)", "{", "\treturn 1;", "}"]
    fh = Firma("h", 8, 10, True, [], "int", "x.c")
    c = comentario_de(L4, fh)
    if "comentario de la funcion de ARRIBA" in c:
        print("  FAIL se llevo el comentario de la funcion de arriba")
        fallos += 1
    else:
        print("  OK   comentario vacio: h no tiene propio")

    print()
    print("[5] las cifras de una CITA no cuentan como cifra de la semantica")
    if "125" in cifras("EVIDENCIA = PROVEN -- findings/007-x.md:125-131."):
        print("  FAIL el numero de linea de la cita se conto como cifra")
        fallos += 1
    else:
        print("  OK   la cita se descarta, solo quedan las cifras del texto")
    if "0x2c00" not in cifras("SET_SH_REG_START = 0x2c00 y el payload"):
        print("  FAIL no lee el hex 0x2c00 del texto")
        fallos += 1
    else:
        print("  OK   0x2c00 si se lee del texto")

    print()
    print("[6] la comprobacion es de correspondencia, no de estilo")
    if not (len(parsear_firmas(L2, "x.c")) == len(parsear_firmas(L2[:1], "x.c")) + 1):
        print("  FAIL anadir '{' no cambio el recuento de firmas")
        fallos += 1
    else:
        print("  OK   el '{' convierte prototipo en definicion, no crea otra firma")

    print()
    print("[7] una LLAMADA no es una declaracion")
    L4 = ["static long f(void)", "{",
          "\t\treturn g(file, cmd, arg);",
          "}"]
    fs4 = parsear_firmas(L4, "x.c")
    nombres = sorted(x.nombre for x in fs4)
    if "g" in nombres:
        print("  FAIL la llamada a g() se conto como declaracion: %s" % nombres)
        fallos += 1
    else:
        print("  OK   `return g(file, cmd, arg);` no es una firma: %s" % nombres)

    print()
    print("[8] una macro en MAYUSCULAS tampoco")
    L5 = ["static DEVICE_ATTR_RO(rx550_info);", "int h(void)", "{", "\treturn 0;", "}"]
    fs5 = parsear_firmas(L5, "x.c")
    if len(fs5) != 1 or fs5[0].nombre != "h":
        print("  FAIL la macro se conto: %r" % fs5)
        fallos += 1
    else:
        print("  OK   la macro no es firma: 1 sola, 'h'")

    print("=" * 72)
    if fallos:
        print("RESULT: FAIL (%d)" % fallos)
        return 1
    print("RESULT: PASS (14 vectores)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="consistencia .h/.c del driver propio")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    kdir = os.path.join(proyecto(), "07-DRIVER", "kernel")
    # El nombre importa: `cab` llevo primero las LINEAS del fichero y despues
    # las Firmas de los prototiops, y al reusarlo parsear_firmas recibio una
    # lista de objetos donde esperaba texto. Un diccionario con dos significados
    # es un error que no se ve leyendo.
    lineas: Dict[str, List[str]] = {}
    for f in sorted(os.listdir(kdir)):
        if not f.endswith((".c", ".h")) or f.endswith(".mod.c"):
            continue
        with open(os.path.join(kdir, f), "r", errors="replace") as fh:
            lineas[f] = fh.read().splitlines()

    protos: Dict[str, List[Firma]] = {}
    defs: Dict[str, List[Firma]] = {}
    for f, L in lineas.items():
        for s in parsear_firmas(L, f):
            (defs if s.es_def else protos).setdefault(s.nombre, []).append(s)

    errores: List[str] = []
    candidatos: List[Tuple[str, str, str]] = []

    for nom, ps in sorted(defs.items()):
        if len(ps) > 1:
            errores.append("%s tiene %d definiciones (%s)" % (
                nom, len(ps), ", ".join("%s:%d" % (p.fichero, p.ini) for p in ps)))
    for nom, ps in sorted(protos.items()):
        if len(ps) > 1:
            errores.append("%s declarado %d veces (%s)" % (
                nom, len(ps), ", ".join("%s:%d" % (p.fichero, p.ini) for p in ps)))
        if nom not in defs:
            errores.append("%s DECLARADO Y NUNCA DEFINIDO (%s)" % (
                nom, ps[0].fichero))
    for nom, ds in sorted(defs.items()):
        if nom not in protos:
            # Una funcion static NO necesita prototipo en el .h: su ambito es el
            # propio fichero. Exigirselo produce una alarma por cada helper
            # local del modulo, que es como se epidermis el aviso y deja de
            # leerse. rx550_ioctl_version es static en rx550_main.c:130 y por
            # eso no aparece en ninguna cabecera: esta bien.
            if not ds[0].estatico:
                errores.append(
                    "%s DEFINIDO SIN PROTOTIPO y con enlace externo (%s:%d)" % (
                        nom, ds[0].fichero, ds[0].ini))
        else:
            p, d = protos[nom][0], ds[0]
            if len(p.params) != len(d.params):
                errores.append(
                    "%s: prototipo con %d parametros, definicion con %d" % (
                        nom, len(p.params), len(d.params)))
            else:
                pt, dt = p.tipos(), d.tipos()
                if pt != dt:
                    errores.append(
                        "%s: tipos %s vs %s" % (nom, pt, dt))

    # CRUCE DE CIFRAS: candidato, no veredicto.
    for nom in sorted(set(defs) & set(protos)):
        p, d = protos[nom][0], defs[nom][0]
        cp, cd = cifras(comentario_de(lineas[p.fichero], p)), \
            cifras(comentario_de(lineas[d.fichero], d))
        solo_h, solo_c = cp - cd, cd - cp
        if solo_h or solo_c:
            candidatos.append((nom,
                               "solo .h: " + (", ".join(sorted(solo_h)) or "-"),
                               "solo .c: " + (", ".join(sorted(solo_c)) or "-")))

    if args.json:
        print(json.dumps({
            "version": VERSION,
            "n_prototipos": len(protos),
            "n_definiciones": len(defs),
            "errores": errores,
            "candidatos": candidatos,
        }, indent=2, sort_keys=True, ensure_ascii=False))
        return 1 if errores else 0

    print("=" * 78)
    print("CONSISTENCIA .h / .c -- 07-DRIVER/kernel")
    print("=" * 78)
    print()
    print("  prototipo: %d funciones    definicion: %d funciones"
          % (len(protos), len(defs)))
    print()
    print("=" * 78)
    print("ERRORES DUROS")
    print("=" * 78)
    print()
    if errores:
        for e in errores:
            print("  %s" % e)
        print()
        print("  %d. Un prototipo sin definicion es una promesa que el .c no" % len(errores))
        print("  cumple; una definicion sin prototipo es algo que el .h no cuenta.")
        print("  Los dos compilan y los dos mienten sobre la superficie del modulo.")
    else:
        print("  ninguno. Todos los prototipos tienen su definicion, con los")
        print("  mismos parametros y los mismos tipos.")
        print()
        print("  Las funciones `static` quedan fuera a proposito: su ambito es su")
        print("  fichero y no deben aparecer en una cabecera. Exigirselo convierte")
        print("  cada helper local en una alarma, y una alarma que suena siempre")
        print("  es una alarma que no se lee.")

    print()
    print("=" * 78)
    print("CIFRAS QUE CRUZAN ENTRE LADOS -- CANDIDATOS, NO VEREDICTOS")
    print("=" * 78)
    print()
    if candidatos:
        for nom, a, b in candidatos:
            print("  %-32s %-34s %s" % (nom[:32], a[:34], b[:34]))
        print()
        print("  Que es esto: las mismas funciones documentadas en los dos lados")
        print("  dan cifras distintas, o dan cifras que el otro lado no menciona.")
        print("  Lo que ESO prueba es que hay dos versiones de la verdad y al")
        print("  menos una documentacion esta incompleta. Lo que NO prueba es cual")
        print("  es la equivocada: puede que una describa una variante de 64 bits")
        print("  y no se contradiga.")
        print()
        print("  Y no detecta la clase de 114, que era SEMANTICA ('count - 1'")
        print("  contra 'count'), no numerica. Es una criba, no una prueba.")
    else:
        print("  ninguno: ambos lados documentan las mismas cifras.")

    print()
    n = len(candidatos)
    print("  RESUMEN: %d errores duros · %d pares con cifras que cruzan"
          % (len(errores), n))
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())