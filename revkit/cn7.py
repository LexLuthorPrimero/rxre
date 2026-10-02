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
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pm4dec as P  # noqa: E402

FALLOS = []


def chk(nombre, cond, detalle=""):
    if cond:
        print("  OK    %s" % nombre)
    else:
        print("  FALLA %s %s" % (nombre, detalle))
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

    # Un anillo truncado DENTRO de una tirada de NOP no produce ningun
    # problema de paquete: el corte es invisible desde dentro del decode.
    # Por eso el codigo de salida no puede depender solo de `problemas`, y
    # por eso se comprueba que main() avise y devuelva 6 en ese caso.
    #
    # El bug que esto cubre: main() hacia rc_problemas = 0 en la rama "sin
    # problemas de paquete", con lo cual se comia el aviso de tamano. El
    # aviso se imprimia y el proceso salia con 0.
    import tempfile
    import subprocess as _sp
    aqui = os.path.dirname(os.path.abspath(__file__))
    with tempfile.TemporaryDirectory() as _td:
        _f = os.path.join(_td, "corto.txt")
        # 12 de cabecera + 997 dwords: 997 NO es potencia de dos, asi que es
        # un anillo truncado aunque el decode interno no se queje.
        with open(_f, "wb") as _h:
            _h.write(struct.pack("<3I", 0x200, 0x200, 0x200))
            _h.write(struct.pack("<997I", *([pk3(0x10, 0x3FFF)] * 997)))
        _r = _sp.run([sys.executable, os.path.join(aqui, "pm4dec.py"), _f],
                     capture_output=True, text=True)
        chk("anillo truncado: avisa y sale con rc=6",
            _r.returncode == 6 and "potencia de dos" in _r.stdout)

        # Y el caso contrario: un anillo de tamano POTENCIA DE DOS no debe dar
        # aviso. Sin esta comprobacion, un control que siempre dice "truncado"
        # pasaria lo mismo que uno que lo detecta bien.
        _f2 = os.path.join(_td, "entero.txt")
        with open(_f2, "wb") as _h:
            _h.write(struct.pack("<3I", 0x200, 0x200, 0x200))
            _h.write(struct.pack("<1024I", *([pk3(0x10, 0x3FFF)] * 1024)))
        _r2 = _sp.run([sys.executable, os.path.join(aqui, "pm4dec.py"), _f2],
                      capture_output=True, text=True)
        chk("anillo de tamano correcto: NO avisa, rc=0",
            _r2.returncode == 0 and "potencia de dos" not in _r2.stdout)

    # El contraste de direcciones tiene que DISCRIMINAR: con la base de VRAM
    # equivocada, las direcciones tienen que caer fuera y salir con rc=5. Si
    # la base fuera un valor que "siempre cuadra", este control no
    # comprobaria nada.
    anillo = os.path.join(aqui, "capturas", "amdgpu_ring_gfx.txt")
    if os.path.exists(anillo):
        r = subprocess.run([sys.executable,
                            os.path.join(aqui, "pm4dec.py"), anillo,
                            "--direcciones"], capture_output=True, text=True,
                           cwd=aqui)
        chk("direcciones del anillo caben en la VRAM, rc=0",
            r.returncode == 0 and "caben en la VRAM" in r.stdout,
            "(rc=%d)" % r.returncode)
        # El mutante se escribe EN revkit, no en un temporal.
        #
        # pm4dec resuelve capturas/ con os.path.dirname(__file__), asi que una
        # copia en /tmp no encuentra amdgpu_vram_mm.txt y sale con rc=4
        # (falta el fichero) en vez del rc=5 del contraste. Es un fallo
        # distinto que enmascara al que se quiere probar, y durante un rato
        # estuve ajustando el rc en vez de mirar por que salia 4.
        _p2 = os.path.join(aqui, "_pm4dec_mutante.py")
        _s2 = open(os.path.join(aqui, "pm4dec.py")).read()
        _m2 = _s2.replace("    base = 0x100000000", "    base = 0")
        chk("el mutante cambia de verdad la base", _m2 != _s2)
        try:
            open(_p2, "w").write(_m2)
            r2 = subprocess.run([sys.executable, _p2, anillo, "--direcciones"],
                               capture_output=True, text=True, cwd=aqui)
            chk("CASO NEGATIVO: base 0 -> NO caben, rc=5",
                r2.returncode == 5 and "NO caben" in r2.stdout,
                "(rc=%d) %s" % (r2.returncode, r2.stdout[-160:]))
        finally:
            if os.path.exists(_p2):
                os.remove(_p2)
    else:
        print("  OMIT  sin capturas/amdgpu_ring_gfx.txt no se prueban las"
              " direcciones")

    # --- el vm_flush de gmc_v8_0 + gfx_v8_0, paquete a paquete -------------
    #
    # No es un anillo inventado: son las llamadas exactas de
    # gmc_v8_0_emit_flush_gpu_tlb (gmc_v8_0.c:673-680) y
    # gfx_v8_0_ring_emit_vm_flush (gfx_v8_0.c:6199-6207), con el layout de
    # WRITE_DATA que da sid.h:377-388 (dst_sel<<8, WR_ONE_ADDR<<16,
    # WR_CONFIRM<<20, engine_sel<<30).
    #
    # La primera vez que se construyo esto a ojo salio mal por dos cosas, y
    # las dos las atrapa este control:
    #   1. opcode 0x3D, que es MEM_WRITE. WRITE_DATA es 0x37
    #   2. la direccion del registro en un dword a cero
    # Por eso se deriva del driver y no de una suposicion.

    def _wreg(reg, val, eng=1):
        return [pk3(0x37, 3), (1 << 20) | (eng << 30) | (1 << 16), reg, val]

    VMID, PD = 7, 0x1_0025_8000
    PTBA = 0x54f + VMID          # mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + vmid
    INVAL = 0x51e                # mmVM_INVALIDATE_REQUEST
    vm_flush = _wreg(PTBA, PD >> 12) + _wreg(INVAL, 1 << VMID) \
        + [pk3(0x3C, 5), 0, INVAL, 0, 0, 0x20]
    pk, _, pr, _ = P.decodifica(struct.pack("<%dI" % len(vm_flush), *vm_flush),
                                ops)
    chk("vm_flush: se decodifica en 3 paquetes, sin problemas",
        len(pk) == 3 and not pr, "(pk=%d pr=%s)" % (len(pk), pr))
    chk("vm_flush: los dos primeros son WRITE_DATA",
        [p["nombre"] for p in pk[:2]] == ["PACKET3_WRITE_DATA"] * 2)
    if len(pk) >= 3 and all(p["nombre"] == "PACKET3_WRITE_DATA"
                            for p in pk[:2]):
        chk("vm_flush: el 1o escribe la PTBA de vmid 7 (0x556) con pd_addr>>12",
            pk[0]["payload"][1] == PTBA and pk[0]["payload"][2] == (PD >> 12),
            "(reg=%s val=%s)" % (hex(pk[0]["payload"][1]),
                                 hex(pk[0]["payload"][2])))
        chk("vm_flush: el 2o escribe VM_INVALIDATE_REQUEST con 1<<vmid",
            pk[1]["payload"][1] == INVAL and pk[1]["payload"][2] == (1 << VMID),
            "(reg=%s val=%s)" % (hex(pk[1]["payload"][1]),
                                 hex(pk[1]["payload"][2])))
        chk("vm_flush: el WAIT_REG_MEM tiene control dword CERO",
            pk[2]["payload"][0] == 0, "(=%s)" % hex(pk[2]["payload"][0]))
        chk("vm_flush: vigila VM_INVALIDATE_REQUEST con ref=0 mask=0",
            pk[2]["payload"][1] == INVAL and pk[2]["payload"][2] == 0
            and pk[2]["payload"][3] == 0)

    # El caso que hace que esto no sea decorativo: en el driver hay DOS
    # emisores de WAIT_REG_MEM y NO coinciden. Este escribe 6 payload y
    # declara 5 (gfx_v8_0.c:6046-6055); el de arriba escribe 5 y declara 5
    # (gfx_v8_0.c:6199-6207). El anillo real capturado contiene el primero.
    hdp = _wreg(0xBCC, 0) + [pk3(0x3C, 5), 0x143, 0x1537, 0x1538, 1, 1, 0x20]
    pk2, _, pr2, _ = P.decodifica(struct.pack("<%dI" % len(hdp), *hdp), ops)
    wm2 = [p for p in pk2 if p["nombre"] == "PACKET3_WAIT_REG_MEM"]
    # La guarda tiene que FALLAR si no encuentra el paquete, no saltarselo.
    # Ya casi pasa: la primera version buscaba el WAIT_REG_MEM en la ultima
    # posicion, y por el propio off-by-one que este control mide, el 0x20
    # sobrante queda al final y el chequeo se saltaba en silencio.
    chk("hdp_flush: el anillo SI contiene el WAIT_REG_MEM buscado",
        len(wm2) == 1, "(encontrados=%d de %d paquetes)"
        % (len(wm2), len(pk2)))
    if wm2:
        # pm4dec NO mide el off-by-one: `dwords` es la extension DECLARADA
        # (cabecera + count), no la escrita. Lo que delata el dword de mas es
        # que se sale del paquete y aparece como un dword suelto. Asi que lo
        # que se mide es el sobrante, no `dwords`.
        chk("hdp_flush: count=5 pero el 0x20 se sale del paquete y queda "
            "como dword suelto (el off-by-one del emisor)",
            wm2[0]["cnt"] == 5 and len(wm2[0]["payload"]) == 5
            and any(p["nombre"].startswith("PKT0") for p in pk2),
            "(cnt=%s len=%d, sobrantes=%d)"
            % (wm2[0].get("cnt"), len(wm2[0].get("payload", [])),
               sum(1 for p in pk2 if p["nombre"].startswith("PKT0"))))
    if pk and pk[-1]["nombre"] == "PACKET3_WAIT_REG_MEM":
        chk("vm_flush: en cambio declara 5, escribe 5 y NO deja sobrante",
            pk[-1]["cnt"] == 5 and pk[-1]["dwords"] == 6
            and len(pk[-1]["payload"]) == 5 and len(pk) == 3,
            "(cnt=%s dwords=%s paquetes=%d)"
            % (pk[-1].get("cnt"), pk[-1].get("dwords"), len(pk)))

    # Y el discriminante que REFUTA "el hardware lee exactamente count":
    # sobre el anillo real, leer 5 produce menos paquetes validos y cabeceras
    # tipo 0 espurias; leer 6 produce mas paquetes y cero espurias.
    _ring = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "capturas", "amdgpu_ring_gfx.txt")
    if os.path.exists(_ring):
        _raw = open(_ring, "rb").read()
        _w = list(struct.unpack("<%dI" % (len(_raw) // 4), _raw))
        _n = len(_w)

        def _recorre(saltar_tipo0):
            i, ok, esp = 3, 0, 0
            while i < _n - 8:
                h = _w[i]
                if (h >> 30) & 3 in (2, 3):
                    c = (h >> 16) & 0x3FFF
                    i += (c + 1) if c else 1
                    ok += 1
                else:
                    if saltar_tipo0:
                        i += 1
                        continue
                    i += (h & 0xFFFF) + 1
                    esp += 1
            return ok, esp

        ok5, esp5 = _recorre(False)
        ok6, esp6 = _recorre(True)
        chk("anillo real: leer count=5 exactos da fewer paquetes y cabeceras "
            "espurias que leer los 6", ok5 < ok6 and esp5 > esp6,
            "(count=5 -> %d validos/%d espurias; count=6 -> %d/%d)"
            % (ok5, esp5, ok6, esp6))
        chk("anillo real: leer los 6 payload deja CERO dwords tipo 0",
            esp6 == 0, "(espurias=%d)" % esp6)
        if _n > 14:
            chk("anillo real: dwords 8..14 son un WAIT_REG_MEM de 7 con "
                "count=5 y poll 0x20 fuera del conteo",
                (_w[8] >> 30) & 3 == 3 and (_w[8] >> 8) & 0xFF == 0x3C
                and ((_w[8] >> 16) & 0x3FFF) == 5 and _w[14] == 0x20,
                "hdr=%s op=%s cnt=%s d14=%s" % (
                    hex(_w[8]), hex((_w[8] >> 8) & 0xFF),
                    (_w[8] >> 16) & 0x3FFF, hex(_w[14])))
            chk("y el dword 0x20 como cabecera seria tipo 0 con count=32, "
                "que se lleva el resto del anillo",
                (_w[14] >> 30) & 3 == 0 and (_w[14] & 0xFFFF) == 32,
                "tipo=%d cnt=%d" % ((_w[14] >> 30) & 3, _w[14] & 0xFFFF))
    else:
        print("  OMIT  sin capturas/amdgpu_ring_gfx.txt no se prueba el "
              "off-by-one sobre el anillo real")

    print("-" * 62)
    if FALLOS:
        print("%d control(es) FALLAN. pm4dec NO puede usarse como autoridad."
              % len(FALLOS))
        return 1
    print("todos los controles pasan")
    return 0


if __name__ == "__main__":
    sys.exit(main())
