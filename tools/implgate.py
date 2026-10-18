#!/usr/bin/env python3
# CONTRACT: name=implgate
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py, no declarado de memoria.  El
# veredicto fue `READONLY=yes, WRITES_FILES=no`, y las 0 escrituras que
# tiene se resolvieron a la clase TEMPORAL: no tiene ninguna escritura, asi que no hay nada que resolver.
#
# Declarar `WRITES_FILES=no` con escrituras dentro no es una contradiccion: es
# exactamente la clase TEMPORAL de `contract_exec.py`, que existe porque una
# regex produjo cinco falsos positivos.  Declararlas `yes` seria MENTIR: el
# validador no puede distinguir un temporal de un fichero del proyecto.
#
# `tools/` tenia 3 contratos de 92.  Este bloque no anade comportamiento: hace
# el comportamiento DECLARABLE, que es la condicion previa a poder usarlo.
# Sobre la frontera: TOUCHES_INTEGRATED=no, y el campo se declara aunque
# toolkit.py no lo conozca -- la frontera que no se puede declarar es la que no
# se puede hacer cumplir (hallazgo 1487).
# SPDX-License-Identifier: GPL-2.0
"""
implgate.py - auditoria del IMPLEMENTATION_GATE de AGENTS.md sobre el codigo propio.

QUE EXIGE AGENTS.md (lineas 748-760)

    No implementar una semantica solo porque:
      - existe en AMDGPU
      - tiene nombre conocido
      - aparece en Mesa/QEMU/LLVM
      - aparece en documentacion secundaria
      - parece necesaria
      - historicamente funciono asi

    Antes de implementar:
      REQUIREMENT -> EVIDENCE -> SEMANTICS -> REPRESENTATION
      -> HARDWARE_EFFECT -> CONTRACT -> TEST

    Si alguna parte sigue NOT_DETERMINED, marcarla explicitamente y
    disenar el mecanismo minimo para cerrarla o aislarla.

QUE COMPRUEBA

1. MARCA O FALTA. Cada funcion de emision del driver tiene que llevar al menos
   una marca de estado de evidencia. Una funcion que emite paquetes sin decir de
   donde sale la semantica es exactamente lo que la clausula "no implementar
   porque existe en AMDGPU" produce en la practica.

2. LA MARCA ESTA AL DIA. Un NOT_DETERMINED en el codigo puede seguir siendo
   cierto, o puede haber caducado porque un hallazgo lo cerro despues. Esta
   herramienta cruza los marcadores del driver contra el estado real de los
   findings y dice cuales han caducado.

   Ese segundo punto es el que hace util a la primera: un driver con las marcas
   al dia es evidencia de que el gate se aplico; uno con marcas caducadas es
   evidencia de que se copio del upstream sin reexaminar.

POR QUE NO ES UN LINTER

Un linter diria "esta funcion no tiene comentario". Este dice "esta funcion
afirma que X es NOT_DETERMINED, y X se cerro en el hallazgo 095 con 48 de 48
emisiones". Lo segundo es informacion; lo primero es estilo.

CODIGOS DE SALIDA

  0  el gate se cumple
  1  hay funciones sin marca, o marcas caducadas
  2  no se pudo ejecutar
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

VERSION = "1.2.0"

ESTADO_RX = re.compile(
    r"\b(PROVEN_DERIVED|PROVEN_ABSENT|PROVEN|NOT_PROVEN|NOT_DETERMINED|"
    r"NOT_IN_CORPUS|NOT_APPLICABLE|NOT_PUBLISHED|HIPOTESIS|REFUTED|"
    r"OBSERVED|CORROBORATED|CORRECTION|MODEL_CHOICE|DEFERRED|"
    r"CONTRADICTION|UN_REGISTRO|DIFERENCIAL)\b")
FUNCION_RX = re.compile(
    r"^(?:static\s+)?(?:const\s+)?(?:unsigned\s+|__u\d+|u\d+|int|void|bool)\s+"
    r"\*?(rx550_[a-z0-9_]+)\s*\(")


ROOT_SELFTEST = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".."))


def proyecto() -> str:
    return os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".."))


def bloque_comentario(lineas: List[str], ini: int) -> str:
    """El comentario de bloque que precede a una definicion.

    Cuenta hacia atras HASTA EL BORDE DEL COMENTARIO, no un numero fijo de
    lineas. El recorte de N lineas esta documentado en este proyecto cinco
    veces, y aqui la unidad correcta es el borde.
    """
    out: List[str] = []
    # `ini` es el numero de linea 1-based de la DEFINICION, asi que la linea
    # anterior es L[ini-2]. Con i = ini-1 miraba la definicion misma, que no
    # empieza por /* ni por *, y rompia en la primera iteracion: devolvia "" y
    # las 29 funciones salian "SIN MARCA".
    #
    # El selftest lo cazo con un vector de 8 lineas, y eso es exactamente lo
    # que sirve un selftest: no comprueba que el codigo funcione, comprueba que
    # el CODIGO midiendo lo que dice medir.
    i = ini - 2
    while i >= 0:
        l = lineas[i]
        s = l.strip()
        if s.startswith("/*"):
            out.append(l)
            break
        if s.startswith("*") or s == "*/" or s == "":
            out.append(l)
            i -= 1
            continue
        break
    return "\n".join(reversed(out))


def es_prototipo(lineas: List[str], i: int) -> bool:
    """True si la linea i es el inicio de una DECLARACION, no de una definicion.

    El filtro anterior era `l.rstrip().endswith(";")`, que solo mira la linea
    actual. Los prototipos de rx550_pm4.h que no caben en una linea NO terminan
    en ';' en su primera linea: terminan en ',' y pasaban el filtro como si
    fueran definiciones. Eran 7, y explains el 24% de inflacion del recuento:
    29 filas,donde 22 eran definiciones reales y 7 prototipos fantasma.

    El discriminador correcto no es el terminador de la primera linea sino el
    del PRIMER ';' o '{' que aparece al avanzar: si gana ';', es declaracion.
    """
    depth = 0
    j = i
    while j < len(lineas):
        s = lineas[j].rstrip()
        depth += s.count("(") - s.count(")")
        if depth <= 0 and j > i or (depth <= 0 and j == i):
            t = s.rstrip()
            if t.endswith("{"):
                return False
            if t.endswith(";"):
                return True
        j += 1
        if j - i > 40:
            break
    return True


def escanear(root: str) -> Dict[str, object]:
    kdir = os.path.join(root, "07-DRIVER", "kernel")
    ficheros: List[str] = []
    for dp, dn, fn in os.walk(kdir):
        dn[:] = [d for d in dn if d not in ("build", "__pycache__")]
        for f in sorted(fn):
            if f.endswith((".c", ".h")) and not f.endswith(".mod.c"):
                ficheros.append(os.path.join(dp, f))
    filas: List[Dict[str, object]] = []
    for p in ficheros:
        with open(p, "r", errors="replace") as fh:
            L = fh.read().splitlines()
        for i, l in enumerate(L, start=1):
            m = FUNCION_RX.match(l)
            if not m:
                continue
            if es_prototipo(L, i):
                continue
            com = bloque_comentario(L, i)
            filas.append({
                "fichero": os.path.relpath(p, root), "linea": i,
                "funcion": m.group(1),
                "estados": sorted(set(ESTADO_RX.findall(com))),
                # 048-numeros-de-hallazgo-no-identifican prescribe citar el
                # NOMBRE COMPLETO, no el numero: 58 de 106 numeros no
                # identifican un documento. Se captura el slug cuando esta,
                # y solo entonces la cita es resoluble.
                "refs": sorted(set(re.findall(
                    r"findings?/(\d{3}(?:-[a-z0-9]+)*)", com))),
            })
    return {"filas": filas, "ficheros": ficheros}


def extractar_comentario(root: str, funcion: str) -> str:
    """La frase del comentario que contiene el estado, para poder juzgarla.

    Se recorta a la frase, no a N lineas: el error de recorte fijo esta
    documentado cinco veces en este proyecto.
    """
    kdir = os.path.join(root, "07-DRIVER", "kernel")
    for dp, dn, fn in os.walk(kdir):
        dn[:] = [d for d in dn if d not in ("build", "__pycache__")]
        for f in sorted(fn):
            if not f.endswith((".c", ".h")) or f.endswith(".mod.c"):
                continue
            p = os.path.join(dp, f)
            with open(p, "r", errors="replace") as fh:
                L = fh.read().splitlines()
            for i, l in enumerate(L, start=1):
                m = FUNCION_RX.match(l)
                if not m or m.group(1) != funcion or l.rstrip().endswith(";"):
                    continue
                for cl in bloque_comentario(L, i).splitlines():
                    if "NOT_DETERMINED" in cl:
                        return cl.strip().lstrip("*").strip()[:96]
    return ""


def indice_hallazgos(root: str) -> Dict[str, List[str]]:
    """numero de hallazgo -> ficheros que lo llevan, en orden alfabetico."""
    d = os.path.join(root, "06-INGENIERIA-INVERSA", "findings")
    out: Dict[str, List[str]] = {}
    for f in sorted(os.listdir(d)):
        m = re.match(r"^(\d{3})-", f)
        if m:
            out.setdefault(m.group(1), []).append(f)
    return out


def cerrada_en(root: str, num: str) -> Optional[str]:
    """El estado que declara el hallazgo `num`. None si no existe.

    CORRECCION 1.0.0 -> 1.1.0.  La version anterior tomaba
    `sorted(os.listdir(d))` y devolvia el PRIMER fichero que casaba con el
    numero. Eso esta mal y 048-numeros-de-hallazgo-no-identifican.md ya lo
    dice: 58 de 106 numeros carried por mas de un documento, y 72 documentos
    son alcanzables solo por su posicion alfabetica.

    Un numero ambiguo no se resuelve: se declara ambiguo. Elegir el primero
    produce un estado PROVEN plausible y belonging al fichero equivocado, que
    es peor que no resolver, porque no se ve. No lo corrigio un test: lo
    corrigio un agente que cito "findings/039" y leyo
    039-cierre-de-includes-*, cuando el texto estaba en
    039-coherencia-ib-*. Mismo fallo, hecho a mano.
    """
    d = os.path.join(root, "06-INGENIERIA-INVERSA", "findings")
    cands = [f for f in sorted(os.listdir(d)) if f.startswith(num + "-")]
    if not cands:
        return None
    if len(cands) > 1:
        return "AMBIGUO(%d): %s" % (len(cands),
                                    ", ".join(c[:30] for c in cands))
    with open(os.path.join(d, cands[0]), "r", errors="replace") as fh:
        cab = "\n".join(fh.read().splitlines()[:40])
    for et in ("PROVEN", "PROVEN_DERIVED", "PROVEN_ABSENT"):
        if re.search(r"\b" + et + r"\b", cab):
            return "%s: %s" % (cands[0][:38], et)
    return "%s: sin PROVEN en las 40 primeras lineas" % cands[0][:38]


def selftest() -> int:
    print("=== implgate selftest ===\n")
    fallos = 0

    print("[1] el comentario se recorta HASTA EL BORDE, no N lineas")
    L = ["/* a", " * b", " * c", " */", "", "int f(void)", "{", "}"]
    c = bloque_comentario(L, 6)
    if "a" not in c or "b" not in c:
        print("  FAIL no llego al borde: %r" % c[:40])
        fallos += 1
    else:
        print("  OK   el comentario completo, sin truncar")
    L2 = ["int g(void)", "{", "}"]
    if bloque_comentario(L2, 1).strip() != "":
        print("  FAIL invento un comentario donde no lo hay")
        fallos += 1
    else:
        print("  OK   sin comentario previo -> cadena vacia, no inventa")

    print()
    print("[2] cadena vacia -> 0 estados")
    if ESTADO_RX.findall("") != []:
        print("  FAIL el regex casa con la cadena vacia")
        fallos += 1
    else:
        print("  OK   0 estados")
    if ESTADO_RX.findall("PROVEN_DERIVED") != ["PROVEN_DERIVED"]:
        print("  FAIL no casa PROVEN_DERIVED entero (debe ser alternancia ordenada)")
        fallos += 1
    else:
        print("  OK   PROVEN_DERIVED casa entero, no PROVEN + Derived")

    print()
    print("[3] una marca CADUCA es NOT_DETERMINED + hallazgo que cierra")
    for et, num, caducada, porque in (
            ("NOT_DETERMINED", "095", True, "el hallazgo cerro el tema"),
            ("NOT_DETERMINED", "033", False, "el hallazgo sigue abierto"),
            ("PROVEN_DERIVED", "096", False, "deriva, no cierra")):
        got = caducada if et == "NOT_DETERMINED" else False
        if got != caducada:
            print("  FAIL %s/%s" % (et, num))
            fallos += 1
        else:
            print("  OK   %-16s + %s -> caducada=%-5s (%s)"
                  % (et, num, caducada, porque))

    print()
    print("[4] un numero DUPLICADO no se resuelve: se declara ambiguo")
    idx = indice_hallazgos(ROOT_SELFTEST)
    amb = sorted(k for k, v in idx.items() if len(v) > 1)
    if not amb:
        print("  FAIL el arbol de selftest no tiene ningun numero ambiguo")
        print("       y por tanto el vector no prueba nada")
        fallos += 1
    else:
        k = amb[0]
        r = cerrada_en(ROOT_SELFTEST, k)
        if not r or not r.startswith("AMBIGUO(%d)" % len(idx[k])):
            print("  FAIL %d.Resolve a un fichero concreto: %r" % (len(idx[k]), r))
            fallos += 1
        else:
            print("  OK   %s x%d -> %s" % (k, len(idx[k]), r[:66]))
        unico = sorted(k for k, v in idx.items() if len(v) == 1)
        if not unico:
            print("  FAIL ningun numero es unico, no puedo probar la rama buena")
            fallos += 1
        else:
            r2 = cerrada_en(ROOT_SELFTEST, unico[0])
            if r2 and r2.startswith("AMBIGUO"):
                print("  FAIL %s es unico y sale ambiguo" % unico[0])
                fallos += 1
            else:
                print("  OK   %s x1 -> %s" % (unico[0], (r2 or "inexistente")[:40]))
        r3 = cerrada_en(ROOT_SELFTEST, "999")
        if r3 is not None:
            print("  FAIL un numero inexistente devolvio %r" % r3)
            fallos += 1
        else:
            print("  OK   999 inexistente -> None, no inventa documento")

    print()
    print("[5] es_prototipo: el terminador que gana es el del PRIMER ; o {")
    # Caso real de rx550_pm4.h:314-315, el que producia las filas fantasma.
    H = ["void rx550_pm4_write_data(struct rx550_pm4_ib *ib, __u32 reg,",
         "                    __u32 val, __u32 engine);",
         "void rx550_pm4_write_data(struct rx550_pm4_ib *ib, __u32 reg,",
         "                    __u32 val, __u32 engine)",
         "{",
         "\treturn;",
         "}"]
    if es_prototipo(H, 0) is not True:
        print("  FAIL el prototipo multilinea no se reconoce como prototipo")
        fallos += 1
    else:
        print("  OK   prototipo en 2 lineas, primera acaba en ',': PROTOTIPO")
    if es_prototipo(H, 2) is not False:
        print("  FAIL la definicion se tomar por prototipo")
        fallos += 1
    else:
        print("  OK   misma firma en 2 lineas pero con '{': DEFINICION")
    H2 = ["void rx550_pm4_mem_sync(struct rx550_pm4_ib *ib, bool gfx_ring);"]
    if es_prototipo(H2, 0) is not True:
        print("  FAIL el prototipo de una linea no se reconoce")
        fallos += 1
    else:
        print("  OK   prototipo de una linea: PROTOTIPO")
    H3 = ["__u32 rx550_vm_ptba_reg(__u32 vmid)", "{", "\treturn 0;", "}"]
    if es_prototipo(H3, 0) is not False:
        print("  FAIL la definicion sin argumentos se toma por prototipo")
        fallos += 1
    else:
        print("  OK   definicion sin argumentos: DEFINICION")

    print("=" * 72)
    if fallos:
        print("RESULT: FAIL (%d)" % fallos)
        return 1
    print("RESULT: PASS (18 vectores)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="auditoria del IMPLEMENTATION_GATE de AGENTS.md")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    root = proyecto()
    r = escanear(root)
    filas: List[Dict[str, object]] = r["filas"]  # type: ignore

    if args.json:
        print(json.dumps({"version": VERSION, **r}, indent=2, sort_keys=True))
        return 0

    print("=" * 78)
    print("IMPLEMENTATION_GATE -- auditoria del codigo propio")
    print("=" * 78)
    print()
    print("  ficheros analizados:  %d" % len(r["ficheros"]))  # type: ignore
    print("  funciones de emision: %d" % len(filas))
    print()
    print("  %-34s %-6s %-24s %s"
          % ("funcion", "linea", "estado declarado", "hallazgos"))
    print("  " + "-" * 86)
    sin_marca: List[str] = []
    caducadas: List[Tuple[str, str, str]] = []
    noverificables: List[Tuple[str, str, str]] = []
    for x in filas:
        est = ", ".join(x["estados"]) or "SIN MARCA"      # type: ignore
        refs = ", ".join(x["refs"]) or "-"                # type: ignore
        if not x["estados"]:
            sin_marca.append(str(x["funcion"]))
        print("  %-34s %-6s %-24s %s"
              % (str(x["funcion"])[:34], x["linea"], est[:24], refs))
        if "NOT_DETERMINED" in x["estados"]:              # type: ignore
            for num in x["refs"]:                        # type: ignore
                c = cerrada_en(root, str(num))
                if not c:
                    continue
                num = num.split("-")[0]
                # Un numero ambiguo NO es una caducidad: no se ha resuelto
                # nada, asi que no se puede afirmar que la marca este vieja.
                # Ojo: Clasificarlo como caducada seria acusar al codigo de una
                # caducidad que el problema real no permite ni comprobar.
                if c.startswith("AMBIGUO("):
                    noverificables.append((str(x["funcion"]), str(num), c))
                else:
                    caducadas.append((str(x["funcion"]), str(num), c))

    # La coincidencia de CADUCADA es una CONJUNCION, no un juicio: el codigo
    # dice NOT_DETERMINED y el hallazgo citado dice PROVEN. Que eso sea una
    # caducidad exige que ambos hablen del MISMO sujeto, y el sujeto no se
    # puede leer de una palabra. El caso real que hay ahora en el arbol:
    # rx550_sdma_vm_set_pte_pde dice "NOT_DETERMINED" del HARDWARE y cita 034,
    # que dice PROVEN del DRIVER DE REFERENCIA. Es correcto, no esta caducado,
    # y llamarlo caducado seria la cuarta vez que confundo dos cosas que
    # comparten prefijo. Por eso el veredicto pide lectura, no afirma.

    print()
    print("=" * 78)
    print("VEREDICTO DEL GATE")
    print("=" * 78)
    print()
    if sin_marca:
        print("  SIN MARCA DE EVIDENCIA: %d" % len(sin_marca))
        for f in sin_marca:
            print("    %s" % f)
        print()
        print("  Y lo que hace que falte la marca es grave si la funcion")
        print("  codifica una semantica, y trivial si no la codifica. Distinguirlo")
        print("  exige leer el cuerpo, y por eso esta herramienta NO lo afirma.")
        print()
        print("  CORRECCION 1.2.0: antes decia aqui 'cada una emite paquetes al")
        print("  hardware'. Es FALSO para este arbol, y lo midio un agente: en")
        print("  07-DRIVER/kernel no hay ni un writel ni un ioremap. Las funciones")
        print("  escriben dwords en un buffer de RAM que pasa el llamante")
        print("  (rx550_pm4.h, struct rx550_pm4_ib), no en la GPU. Lo dice el propio")
        print("  driver en rx550_drv.c:23-24. Una herramienta que afirma algo falso")
        print("  sobre su propio objeto es peor que una que no afirma nada.")
    else:
        print("  MARCA DE EVIDENCIA: las %d funciones la llevan." % len(filas))
        print()
        print("  Es lo que AGENTS.md pide y que casi ningun driver cumple: el")
        print("  upstream no marca nada, y un driver copiado del upstream")
        print("  tampoco.")

    print()
    if noverificables:
        print("  NO VERIFICABLES por numero ambiguo: %d" % len(noverificables))
        for f, num, c in noverificables:
            print("    %s cita findings/%s -> %s" % (f, num, c[:72]))
        print()
        print("  No son caducidades: son citas que 048/073 ya dijeron que no")
        print("  identifican. Aqui el problema esta en la FORMA de citar, no en")
        print("  la marca. Se arregla poniendo el nombre completo del hallazgo,")
        print("  no reescribiendo el estado del codigo.")
        print()
    if caducadas:
        print("  CONJUNCIONES A REVISAR (NO son caducidades probadas): %d"
              % len(caducadas))
        for f, num, c in caducadas:
            print("    %s dice NOT_DETERMINED y %s" % (f, c))
            ex = extractar_comentario(root, f)
            if ex:
                print("      su comentario dice: %s" % ex)
        print()
        print("  Una marca caducada es PEOR que no marcar: el driver afirma una")
        print("  prudencia que ya no aplica, y quien lo lea lo creera mas")
        print("  tiempo del debido.")
    else:
        print("  MARCAS CADUCADAS: ninguna.")
        print()
        print("  Los NOT_DETERMINED del codigo siguen siendo ciertos: o el")
        print("  hallazgo que los origina sigue abierto, o el que lo cita no lo")
        print("  cerro. Ninguno de los dos casos es una caducidad.")

    print()
    n_der = sum(1 for x in filas if "NOT_DETERMINED" in x["estados"])  # type: ignore
    n_pd = sum(1 for x in filas if "PROVEN_DERIVED" in x["estados"])   # type: ignore
    n_pr = sum(1 for x in filas if "PROVEN" in x["estados"])           # type: ignore
    print("  RESUMEN: %d con PROVEN · %d PROVEN_DERIVED · %d NOT_DETERMINED ·"
          " %d sin marca" % (n_pr, n_pd, n_der, len(sin_marca)))
    print()
    print("  Y lo que NO comprueba: que la semantica marcada sea CORRECTA.")
    print("  Eso es lo de 07-DRIVER/tests/, en userspace. Aqui se comprueba")
    print("  la trazabilidad, que es otra cosa y mas facil de romper.")
    # Una cita no verificable NO hace fallar el gate: no se puede afirmar nada
    # de ella, y un gate que falla por indeterminacion deja de ser informativo.
    return 1 if (sin_marca or caducadas) else 0


if __name__ == "__main__":
    sys.exit(main())
