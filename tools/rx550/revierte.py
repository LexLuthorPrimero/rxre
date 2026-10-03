#!/usr/bin/env python3
"""revierte — ¿el ciclo devuelve el registro al estado que encontro?

POR QUE        `bits` separo las operaciones: `gart_enable` pone 4 campos de
               CONTEXT0_CNTL/1_CNTL (configuracion + ENABLE_CONTEXT), la IRQ
               pone 7 campos de NOTIFICACION, y `gart_disable` escribe el
               registro ENTERO a cero.

               Eso plantea la pregunta de reversibilidad, que es la que decide
               si un driver propio puede repetir el ciclo:

                 ¿`gart_disable` seguido de `gart_enable` deja CONTEXT0_CNTL y
                 CONTEXT1_CNTL como estaban?

               La respuesta NO es trivial y no se puede contestar leyendo los
               nombres.  Hay que hacer la cuenta de bits:

                 estado_final = (estado_inicial & ~(lo que pone disable))
                                | (lo que pone enable)

               donde "lo que pone disable" es TODO (pisa el registro) y "lo que
               pone enable" son 4 campos concretos.  Si hay algun campo que solo
               lo pone la IRQ, el ciclo enable->disable->enable lo pierde, y el
               segundo enable no lo recupera: la IRQ hay que volver a llamarla.

METODO         Se opera sobre la mascara de campos de `bits`:
                 - `disable` pone 0xFFFFFFFF (pisa todo el registro)
                 - `enable` pone su mascara calculada
                 - `irq` pone su mascara calculada
               y se compara el estado antes y despues del ciclo.  No se
               necesita el valor inicial: el ciclo lo destruye si el estado
               inicial tenia bits que solo la IRQ pone, y eso se detecta
               calculando el conjunto de bits que el ciclo NO puede recuperar.

CONTROL        El resultado peligroso es "el ciclo es reversible", porque
               llevaria a concluir que repetir enable/disable es inocuo.  Asi:
                 - se EXIGE un caso POSITIVO: tiene que existir al menos un bit
                   que el ciclo no recupera.  Si no hay ninguno, el ciclo seria
                   reversible y la herramienta estara probando otra cosa.
                 - CONTROL DE BORDE: un ciclo donde el setup pone TODO lo que el
                   teardown borra, y no hay IRQ, SI es reversible.  Se prueba
                   con un caso sintetico, para que el "no reversible" del
                   corpus no venga de que la funcion siempre diga que no.

DEPENDENCIAS   bits, funcspan, paths
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from paths import AMD as _AMD                     # noqa: E402
import funcspan                                    # noqa: E402
import bits as _bits                               # noqa: E402

VERSION = "1.0"
NAME = "revierte"

# (fichero, linea, etiqueta)
MIEMBROS = [("gmc_v8_0.c", 829, "setup"),
            ("gmc_v8_0.c", 972, "teardown"),
            ("gmc_v8_0.c", 1385, "irq")]

BRUTO = 0xFFFFFFFF


def mascara(miembro_fichero, linea, ctx, equivalente=None):
    p = os.path.join(_AMD, "amdgpu", miembro_fichero)
    a, b, _m = funcspan.of_line(p, linea)
    if a is None:
        return None, None
    ls = open(p, encoding="utf-8", errors="replace").read().splitlines()
    cuerpo = "\n".join(ls[a - 1:b])
    campos = _bits.bits_de_cuerpo(cuerpo)
    return _bits.mascara_de(campos, ctx, equivalent=equivalente), campos


def ciclo(ctx):
    """(recuperados, perdidos, reversible) del ciclo sobre un contexto"""
    m_setup, c_setup = mascara(*MIEMBROS[0][:2], ctx)
    m_tear, _ = mascara(*MIEMBROS[1][:2], ctx)
    m_irq, _ = mascara(*MIEMBROS[2][:2], ctx, equivalente=1)
    if m_setup is None or m_tear is None:
        return None, None, None
    # el teardown pisa a 0 -> todo lo que hubiera se pierde
    # el setup recupera su mascara
    recuperados = m_setup
    # lo que el ciclo borra y ni el setup ni la IRQ recuperan
    perdidos = (BRUTO & ~m_tear) & ~recuperados & ~m_irq
    reversible = perdidos == 0
    return recuperados, perdidos, reversible


def mascara_maquina():
    """(mascara de la IRQ, campos que la nombra)

    La IRQ escribe `mmVM_CONTEXT0_CNTL` y `mmVM_CONTEXT1_CNTL` con la misma
    mascara, y los nombres de campo son de CONTEXT1.  Por eso hay que pasar
    `equivalente=1`: sin eso da 0 y el assert "los 7 estan entre los perdidos"
    falla con 0x0 aunque los 7 bits esten ahi.  (correccion 173)
    """
    m, campos = mascara(*MIEMBROS[2][:2], 0, equivalente=1)
    return m or 0, campos or set()


def self_test():
    ok = fail = 0

    def chk(name, cond, extra=""):
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"    P  {name}")
        else:
            fail += 1
            print(f"    F  {name}  {extra}")

    print(f"  {NAME} {VERSION} self-test")

    # --- aritmetica del ciclo, en un caso CONOCIDO ---
    # El teardown real (`gart_disable`) escribe 0 en el registro: BORRA todo.
    # `m_tear` es la mascara que PONE, no la que borra.  Con `m_tear = BRUTO`
    # la formula `BRUTO & ~m_tear` da 0: no se borra nada.  Ese fue el primer
    # caso de esta lista, y por eso daba "nada perdido" con el
    # razonamiento equivocado.  (correccion 171)
    m_setup, m_tear, m_irq = 0x1, 0, 0
    perdidos = (BRUTO & ~m_tear) & ~m_setup & ~m_irq
    chk("KNOWN: teardown que pone 0 borra todo y sin IRQ se pierde casi todo",
        bin(perdidos).count("1") > 28, bin(perdidos).count("1"))
    m_setup, m_tear, m_irq = 0x1, 0, 0x1
    perdidos2 = (BRUTO & ~m_tear) & ~m_setup & ~m_irq
    chk("KNOWN: si la IRQ cubre el bit, ese bit no se pierde",
        (perdidos2 & 0x1) == 0, hex(perdidos2))
    chk("KNOWN: y solo se pierde lo que la IRQ no cubre",
        bin(perdidos2).count("1") == 31, bin(perdidos2).count("1"))
    perdidos3 = (BRUTO & ~0) & ~BRUTO & ~0
    chk("KNOWN: si el setup pone TODO, el ciclo es reversible",
        perdidos3 == 0, hex(perdidos3))

    if "--rapido" in sys.argv:
        print(f"  {ok} pasaron, {fail} fallaron"
              "  (sintetico; corpus NO evaluado)")
        return 0 if fail == 0 else 1

    for ctx in (0, 1):
        rec, perd, rev = ciclo(ctx)
        chk(f"CORPUS: el ciclo sobre CONTEXT{ctx}_CNTL se calcula",
            rec is not None, (rec, perd, rev))
        # CONTROL POSITIVO: tiene que haber bits que el ciclo no recupera
        chk(f"HALLAZGO CONT{ctx}: el ciclo NO es reversible",
            rev is False, (hex(rec), hex(perd) if perd else None, rev))
        # Los 7 de la IRQ son solo una parte: el setup configura muchos campos
        # solo en CONTEXT1, asi que en CONTEXT0 hay 21 bits que ni el setup ni
        # la IRQ recuperan.  Mi aserto de "pierde 7" era una suposicion sobre
        # lo que el ciclo tocaba, y no sobre lo que decia el calculo.
        # (correccion 172)
        chk(f"HALLAZGO CONT{ctx}: pierde MAS bits que los 7 de la IRQ",
            bin(perd).count("1") > 7,
            (hex(perd), bin(perd).count("1")))
        chk(f"HALLAZGO CONT{ctx}: la mascara de la IRQ (0x249248) esta en juego",
            mascara_maquina()[0] == 0x249248, hex(mascara_maquina()[0]))
        # En CONTEXT0 el setup pone 4 campos y la IRQ 7 distintos: los 7 se
        # pierden.  En CONTEXT1 el setup pone 14 campos que INCLUYEN los 7 de
        # la IRQ, y ahi se pierde el resto.  Por eso el assert no puede ser
        # "los 7 estan perdidos" en los dos: seria falso en CONTEXT1.  Lo que
        # se comprueba es que el ciclo pierde bits, y que son los que ni el
        # setup ni la IRQ cubren para ese contexto.
        cubiertos = rec | mascara_maquina()[0]
        chk(f"HALLAZGO CONT{ctx}: lo perdido NO lo cubre ni setup ni IRQ",
            (perd & cubiertos) == 0,
            hex(perd & cubiertos))
        d = _bits.campos_de_contexto(ctx)
        perdidos_nombres = sorted(
            k for k, v in d.items() if v and (v & perd) == v)
        chk(f"HALLAZGO CONT{ctx}: hay campos con nombre que se pierden",
            len(perdidos_nombres) >= 5, len(perdidos_nombres))

    # y el dato duro, separado por contexto
    rec0, perd0, rev0 = ciclo(0)
    rec1, perd1, rev1 = ciclo(1)
    chk("DATO: CONTEXT0 pierde 21 bits y CONTEXT1 pierde 11",
        bin(perd0).count("1") == 21 and bin(perd1).count("1") == 11,
        (bin(perd0).count("1"), bin(perd1).count("1")))
    chk("DATO: el setup pone 4 campos en CONTEXT0 y 14 en CONTEXT1",
        bin(rec0).count("1") == 4 and bin(rec1).count("1") == 14,
        (bin(rec0).count("1"), bin(rec1).count("1")))

    print(f"  {ok} pasaron, {fail} fallaron")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    if "--out" in sys.argv:
        for ctx in (0, 1):
            rec, perd, rev = ciclo(ctx)
            print(f"  CONTEXT{ctx}_CNTL")
            print(f"    el setup recupera : {hex(rec)} ({bin(rec).count('1')} bits)")
            print(f"    el ciclo pierde    : {hex(perd)} ({bin(perd).count('1')} bits)")
            print(f"    reversible         : {rev}")
    else:
        print("uso: revierte.py --self-test [--rapido] | --out")