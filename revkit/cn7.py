#!/usr/bin/env python3
"""
cn7.py -- controles de pm4dec.py.

POR QUE ESTA EN UN FICHERO Y NO EN UN COMANDO
---------------------------------------------
Porque ya se perdio una vez. Los tests de pm4dec se ejecutaron como un
aqui-doc de python pegado en un comando de shell, y no quedo registro. Cuando
hace falta volver a pasarlos no hay nada que ejecutar, y rehacerlos a mano es
justo lo queiautomatiza este proyecto.

Ademas, uno de esos tests FALLO y el diagnostico apuntaba al sitio
equivocado: el test usaba el opcode 0x10, que ES PACKET3_NOP, y por eso la
regla nueva de NOP hacia que no hubiera problema. La herramienta estaba
bien; el test estaba mal. Un test mal escrito que falla senala al codigo
equivocado, y eso se paga caro. Aqui queda escrito cual es el caso valido.

QUE COMPRUEBA
-------------
1. NOP con cuenta 0 ocupa 1 dword.
2. NOP con cuenta 0x3FFF (el valor real de GFX8) ocupa 1 dword y no reporta
   problema. Este es el caso que Importa: sin esta regla el decodificador se
   comia el resto del anillo.
3. Varios NOP seguidos se cuentan bien y NO se desincronizan.
4. NOP seguido de un paquete real: los dos se ven, en orden.
5. Un paquete que declara mas payload del que hay SE REPORTA. Y se prueba
   con un opcode que NO sea NOP, precisamente porque si se usara 0x10 el
   control pasaria por el motivo equivocado.
6. Opcode desconocido sale como PKT3_UNKNOWN, no se inventa un nombre.
7. Entrada vacia y entrada a medias no rompen nada.
8. saltar_cabecera decide, y por defecto es False: la funcion de bajo nivel
   no adivina el formato. Este control existe porque el defectoOpposite
   (assumir cabecera) se manifesto como un fallo que PARECIA del NOP.
"""
import struct
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pm4dec as P  # noqa: E402

FALLOS = []


def chk(nombre, cond):
    if cond:
        print("  OK    %s" % nombre)
    else:
        print("  FALLA %s" % nombre)
        FALLOS.append(nombre)


def pk3(op, cnt):
    return (3 << 30) | ((op & 0xFF) << 8) | ((cnt & 0x3FFF) << 16)


def main():
    ops, err = P.cargar_opcodes()
    if not ops:
        # DEGRADACION HONESTA, NO UN OK FALSO.
        #
        # pm4dec necesita sid.h del corpus para sacar los opcodes. En un clon
        # de revkit solo, sid.h no esta. La version anterior de este control
        # devolvia 2, que check.sh reportaba como FALLO: eso hace creer que
        # pm4dec esta roto, cuando lo que falta es el corpus, que es una
        # dependencia legitima y declarada.
        #
        # rc=0 con "OMITIDO" seria mentira: el control NO se ha ejecutado.
        # rc=2 con un mensaje claro dice lo que paso. En check.sh se distingue
        # con el propio codigo y con el texto, no se maquilla de verde.
        print("OMITIDO: no se encuentra sid.h (%s)." % err)
        print("Este control necesita el corpus del kernel, que no viaja con")
        print("revkit. No se ejecuta y NO se cuenta como pasado.")
        print("Con el corpus presente, este control da 11 comprobaciones.")
        return 2
    print("controles de pm4dec.py (%d opcodes desde sid.h)" % len(ops))
    print("-" * 62)

    d = struct.pack("<I", pk3(0x10, 0))
    pk, _, pr, no = P.decodifica(d, ops)
    chk("NOP cnt=0 ocupa 1 dword",
        len(pk) == 1 and pk[0]["dwords"] == 1 and len(no) == 1)

    d = struct.pack("<I", pk3(0x10, 0x3FFF))
    pk, _, pr, no = P.decodifica(d, ops)
    chk("NOP cnt=0x3FFF (valor GFX8) ocupa 1 dword y no es problema",
        len(pk) == 1 and pk[0]["dwords"] == 1 and not pr)

    d = struct.pack("<5I", *[pk3(0x10, 0x3FFF)] * 5)
    pk, _, _, no = P.decodifica(d, ops)
    chk("5 NOP seguidos = 5 paquetes, 5 dwords (sin desincronizar)",
        len(pk) == 5 and sum(p["dwords"] for p in pk) == 5)

    d = struct.pack("<I", pk3(0x10, 0x3FFF)) + \
        struct.pack("<4I", pk3(0x37, 3), 1, 2, 3)
    pk, _, pr, _ = P.decodifica(d, ops)
    chk("NOP + WRITE_DATA: ambos, en orden",
        [p["nombre"] for p in pk] == ["PACKET3_NOP", "PACKET3_WRITE_DATA"])

    d = struct.pack("<4I", pk3(0x37, 3), 1, 2, 3)
    pk, _, _, _ = P.decodifica(d, ops)
    chk("WRITE_DATA cnt=3 ocupa 4 dwords",
        len(pk) == 1 and pk[0]["dwords"] == 4)

    # OJO: opcode 0x37, NO 0x10. Con 0x10 (que es NOP) este control pasaria
    # por un motivo que no es el que quiere comprobar. Ya paso una vez.
    d = struct.pack("<I", pk3(0x37, 10))
    pk, _, pr, _ = P.decodifica(d, ops)
    chk("paquete no-NOP que declara payload de mas SE REPORTA",
        len(pr) == 1)

    d = struct.pack("<I", pk3(0xFE, 0))
    pk, _, _, _ = P.decodifica(d, ops)
    chk("opcode desconocido sale como PKT3_UNKNOWN, no inventado",
        pk[0]["nombre"] == "PKT3_UNKNOWN_0xFE")

    pk, _, pr, _ = P.decodifica(b"", ops)
    chk("entrada vacia no rompe nada", pk == [])

    d = struct.pack("<I", pk3(0x10, 0))[:3]
    pk, _, _, _ = P.decodifica(d, ops)
    chk("entrada a medias (3 bytes) no rompe nada", pk == [])

    d = struct.pack("<3I", pk3(0x10, 0), pk3(0x10, 0), pk3(0x10, 0))
    pk, _, _, _ = P.decodifica(d, ops, saltar_cabecera=False)
    chk("por defecto NO se salta cabecera (3 paquetes)",
        len(pk) == 3)
    pk, _, _, _ = P.decodifica(d, ops, saltar_cabecera=True)
    chk("con saltar_cabecera=True empieza en el dword 3", len(pk) == 0)

    # Fija el formato de PACKET3 con un caso construido a mano:
    # (3<<30)|(op<<8)|(cnt<<16). Si esto se rompe, el opcode y el conteo de
    # todo lo demas tambien, y sin este control el fallo se manifestaria
    # como un numero raro en vez de como un error de formato.
    d = struct.pack("<6I", pk3(0x3C, 5), 0x143, 0x1537, 0x1538, 1, 1)
    pk, _, pr, _ = P.decodifica(d, ops)
    chk("WAIT_REG_MEM cnt=5 -> 6 dwords, opcode nombrado",
        len(pk) == 1 and pk[0]["nombre"] == "PACKET3_WAIT_REG_MEM"
        and pk[0]["dwords"] == 6 and pk[0]["cnt"] == 5)

    # Y que el dword de tipo 0 (el poll interval 0x20 que el driver escribe
    # de mas, sin declararlo en count) no se tome por cabecera de PKT0 que
    # se come 85 dwords y desincroniza todo lo que viene despues.
    d = struct.pack("<7I", pk3(0x3C, 5), 0x143, 0x1537, 0x1538, 1, 1, 0x20)
    pk, _, _, _ = P.decodifica(d, ops)
    chk("el 6to dword (0x20) no rompe la sincronizacion",
        sum(p["dwords"] for p in pk) == 7 and len(pk) == 2)

    print("-" * 62)
    if FALLOS:
        print("%d control(es) FALLAN. pm4dec NO puede usarse como autoridad."
              % len(FALLOS))
        return 1
    print("todos los controles pasan")
    return 0


if __name__ == "__main__":
    sys.exit(main())
