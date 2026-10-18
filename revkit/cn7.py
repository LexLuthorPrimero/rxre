#!/usr/bin/env python3
# CONTRACT: name=cn7
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=indeterminado
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py, y el veredicto fue `NO_DETERMINED`.
# NO se upgraded a `WRITES_FILES=yes` porque no esta medido, y NO se dejo en
# `no` porque el codigo no lo sostiene.  La razon del NO_DETERMINED es que sus 3 escrituras van a temporales, pero compone rutas de `subprocess` que este AST no puede seguir.
#
# Poner `yes` seria MENTIR en un sentido que el validador no puede detectar, que
# es lo que el propio toolkit.py escribe de sus cinco falsos positivos: "un
# contrato en prosa no se puede comprobar con una maquina".  Poner `no` seria
# Peor: seria una afirmacion que nadie ha comprobado.
#
# TOUCHES_INTEGRATED=no: lee sysfs y ficheros.  No hace ioctl ni escribe en la
# GPU.  Ver 1487.
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
import glob
import struct
import sys
import os
import re
import subprocess

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import pm4dec as P  # noqa: E402
import pte as _PTE  # noqa: E402

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

    # Layout de WRITE_DATA segun gfx_v8_0_ring_emit_wreg (gfx_v8_0.c:6349):
    #     PACKET3(WRITE_DATA, 3) | cmd | reg | 0 | val      -> 5 dwords
    # Son 5 dwords con 3 payload declarados: el `0` y el `val` quedan fuera.
    # Y `cmd` es WRITE_DATA_ENGINE_SEL(1) | WR_CONFIRM = 0x40100000: esta
    # variante NO pone WR_ONE_ADDR. Las dos cosas las salio el contraste con
    # el anillo real, no la lectura del header.
    def _wreg(reg, val, eng=1):
        return [pk3(0x37, 3), (1 << 20) | (eng << 30), reg, 0, val]

    VMID, PD = 7, 0x1_0025_8000
    PTBA = 0x54f + VMID          # mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + vmid
    INVAL = 0x51e                # mmVM_INVALIDATE_REQUEST
    vm_flush = _wreg(PTBA, PD >> 12) + _wreg(INVAL, 1 << VMID) \
        + [pk3(0x3C, 5), 0, INVAL, 0, 0, 0, 0x20]
    pk, _, pr, _ = P.decodifica(struct.pack("<%dI" % len(vm_flush), *vm_flush),
                                ops)
    # Con el emit_wreg real (5 dwords, count=3) el vm_flush NO decodifica en
    # 3 paquetes. Cada WRITE_DATA deja su `val` fuera del conteo declarado, y
    # eso tambien es off-by-one. El orden real es:
    #   WRITE_DATA(PTBA) | valor | WRITE_DATA(INVALIDATE) | valor | WAIT_REG_MEM
    chk("vm_flush: 6 paquetes, sin problemas (los 3 sobrantes quedan "
        "sueltos)", len(pk) == 6 and not pr, "(pk=%d pr=%s)" % (len(pk), pr))
    chk("vm_flush: WD, valor, WD, valor, WAIT_REG_MEM, poll",
        [p["nombre"].split("(")[0] for p in pk] ==
        ["PACKET3_WRITE_DATA", "PKT0", "PACKET3_WRITE_DATA", "PKT0",
         "PACKET3_WAIT_REG_MEM", "PKT0"],
        "(%s)" % [p["nombre"].split("(")[0] for p in pk])
    if len(pk) == 6:
        # payload del WRITE_DATA = [cmd, reg, 0]; el valor va FUERA
        chk("vm_flush: el 1o WRITE_DATA apunta a la PTBA de vmid 7 (0x556)",
            pk[0]["payload"][1] == PTBA,
            "(reg=%s)" % hex(pk[0]["payload"][1]))
        chk("vm_flush: su valor suelto es pd_addr>>12 = 0x%08x" % (PD >> 12),
            pk[1]["nombre"].startswith("PKT0") and pk[1]["hdr"] == (PD >> 12),
            "(suelto=%s)" % hex(pk[1].get("hdr", 0)))
        chk("vm_flush: el 2o WRITE_DATA apunta a VM_INVALIDATE_REQUEST (0x51e)",
            pk[2]["payload"][1] == INVAL,
            "(reg=%s)" % hex(pk[2]["payload"][1]))
        chk("vm_flush: su valor suelto es 1<<vmid = 0x%02x" % (1 << VMID),
            pk[3]["nombre"].startswith("PKT0") and pk[3]["hdr"] == (1 << VMID),
            "(suelto=%s)" % hex(pk[3].get("hdr", 0)))
        chk("vm_flush: el WAIT_REG_MEM tiene control dword CERO",
            pk[4]["payload"][0] == 0, "(=%s)" % hex(pk[4]["payload"][0]))
        chk("vm_flush: vigila VM_INVALIDATE_REQUEST con ref=0 mask=0",
            pk[4]["payload"][1] == INVAL and pk[4]["payload"][2] == 0
            and pk[4]["payload"][3] == 0)
        chk("vm_flush: el 0x20 se sale del paquete, IGUAL que hdp_flush: no "
            "hay excepcion a count = payload - 1",
            pk[5]["nombre"].startswith("PKT0") and pk[5]["hdr"] == 0x20,
            "(ultimo=%s)" % pk[5]["nombre"])

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
        # que se sale del paquete y aparece como un dword suelto.
        chk("hdp_flush: count=5 pero el 0x20 se sale del paquete y queda "
            "como dword suelto (el off-by-one del emisor)",
            wm2[0]["cnt"] == 5 and len(wm2[0]["payload"]) == 5
            and any(p["nombre"].startswith("PKT0") for p in pk2),
            "(cnt=%s len=%d, sobrantes=%d)"
            % (wm2[0].get("cnt"), len(wm2[0].get("payload", [])),
               sum(1 for p in pk2 if p["nombre"].startswith("PKT0"))))
        chk("hdp_flush: el WRITE_DATA tambien se pasa en uno (5 dwords, "
            "count=3)",
            any(p["nombre"] == "PACKET3_WRITE_DATA" and p["cnt"] == 3
                and p["dwords"] == 4 for p in pk2),
            "(los WRITE_DATA: %s)" % [(p.get("cnt"), p.get("dwords"))
                                      for p in pk2
                                      if p["nombre"] == "PACKET3_WRITE_DATA"])
    wmv = [p for p in pk if p["nombre"] == "PACKET3_WAIT_REG_MEM"]
    if wmv:
        # El bloque del WAIT_REG_MEM son los ULTIMOS 7 dwords: cabecera + 6
        # payload (control, addr, ref, mask, y un 0, y el poll). CORRECCION
        # 2026-10-02: se contaba 5 payload. Era falso; el 0 del mask y el
        # 0x20 del poll son DOS dwords y no uno.
        _bloque = vm_flush[-7:]
        _esperado = [pk3(0x3C, 5), 0, INVAL, 0, 0, 0, 0x20]
        chk("vm_flush: escribe 6 payload con count=5, como los otros dos "
            "emisores. CORRECCION: se contaba 5 y era falso",
            _bloque == _esperado and wmv[0]["cnt"] == 5,
            "(bloque=%s esperado=%s)"
            % ([hex(x) for x in _bloque], [hex(x) for x in _esperado]))

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
        # El WRITE_DATA del anillo, que es donde se corrigio mi sintético:
        # son 5 dwords (hdr, cmd, reg, 0, val) con count=3, y el cmd NO
        # lleva WR_ONE_ADDR. Las dos cosas se leisieron mal antes.
        if _n > 26:
            chk("anillo real: WRITE_DATA en 22..26 = 5 dwords con count=3",
                ((_w[22] >> 30) & 3) == 3 and ((_w[22] >> 8) & 0xFF) == 0x37
                and ((_w[22] >> 16) & 0x3FFF) == 3 and _w[25] == 0
                and _w[24] == 0xBCC,
                "hdr=%s op=%s cnt=%s d24=%s d25=%s d26=%s" % (
                    hex(_w[22]), hex((_w[22] >> 8) & 0xFF),
                    (_w[22] >> 16) & 0x3FFF, hex(_w[24]), hex(_w[25]),
                    hex(_w[26])))
            chk("anillo real: cmd = WR_CONFIRM|ENGINE(1) = 0x40100000, "
                "SIN WR_ONE_ADDR",
                _w[23] == 0x40100000, "(cmd=%s)" % hex(_w[23]))
            chk("emit_wreg construye el mismo bloque de 5 dwords",
                _wreg(0xBCC, _w[26]) == [_w[22], _w[23], _w[24], _w[25],
                                          _w[26]],
                "(sintetico=%s vs real=%s)"
                % ([hex(x) for x in _wreg(0xBCC, _w[26])],
                   [hex(_w[i]) for i in range(22, 27)]))
        # Los 8 INDIRECT_BUFFER, por layout del emisor y NO por el count.
        # EV-21 se escribio mirando el primero y generalize: length_dw NO es
        # constante (344/1104/1488) y la alineacion no es 0x600 sino 0x200.
        _ibs = []
        for _k in range(8):
            _d = 18 + 256 * _k
            if _d + 3 < _n:
                _ibs.append((_d,
                             ((_w[_d + 2] & 0xFFFF) << 32)
                             | (_w[_d + 1] & 0xFFFFFFFC),
                             _w[_d + 3] >> 24, _w[_d + 3] & 0xFFFF))
        chk("anillo real: 8 INDIRECT_BUFFER en el stride 256", len(_ibs) == 8,
            "(encontrados=%d)" % len(_ibs))
        if len(_ibs) == 8:
            chk("los 8 tienen vmid=7 (sostiene la lectura de EV-21)",
                all(v == 7 for _d, _a, v, _l in _ibs),
                "(vmids=%s)" % sorted(set(v for _d, _a, v, _l in _ibs)))
            chk("length_dw NO es constante: hay 344, 1104 y 1488",
                sorted(set(l for _d, _a, _v, l in _ibs)) == [344, 1104, 1488],
                "(valores=%s)" % sorted(set(l for _d, _a, _v, l in _ibs)))
            _ad = [a for _d, a, _v, _l in _ibs]
            chk("las direcciones estan alineadas a 0x200, NO a 0x600",
                all(a % 0x200 == 0 for a in _ad)
                and not all(a % 0x600 == 0 for a in _ad),
                "(mod 0x200=%s, mod 0x600=%s)"
                % (sorted(set(hex(a % 0x200) for a in _ad)),
                   sorted(set(hex(a % 0x600) for a in _ad))))
            chk("ninguna direccion pasa de 48 bits (el emisor enmascara el "
                "alto a 0xFFFF)", all(a < (1 << 48) for a in _ad),
                "(max=0x%x)" % max(_ad))
            chk("el rango es 0x1_0025_8000 .. 0x1_0027_8600, como dice EV-21",
                min(_ad) == 0x100258000 and max(_ad) == 0x100278600,
                "(min=0x%x max=0x%x)" % (min(_ad), max(_ad)))
        # Y la estructura se repite pero el contenido NO: lo que obliga a
        # decir "misma estructura" y no "8 repeticiones".
        if _n > 300:
            _dif = [i for i in range(256) if _w[3 + i] != _w[259 + i]]
            chk("los bloques 0 y 1 tienen la MISMA estructura pero distinto "
                "contenido", len(_dif) > 0 and len(_dif) < 20,
                "(difieren en %d dwords: %s)" % (len(_dif), _dif[:8]))

        # Y el punto que obliga a retirar el REFUTED de EV-27: los dos modelos
        # que seexcluidos a proposito dan lo MISMO sobre este anillo.
        def _recorre2(honrar_count, saltar_tipo0):
            i, paq, esp = 3, 0, 0
            while i < _n - 8:
                h = _w[i]
                if (h >> 30) & 3 == 3:
                    c = (h >> 16) & 0x3FFF
                    i += (c + 1) if (honrar_count or c == 0) else (c + 2)
                    paq += 1
                else:
                    if saltar_tipo0:
                        i += 1
                        continue
                    i += (h & 0xFFFF) + 1
                    esp += 1
            return paq, esp

        _m1 = _recorre2(True, True)
        _m2 = _recorre2(False, True)
        _m3 = _recorre2(True, False)
        chk("EV-27: 'honrar count' y 'leer count+1' dan lo MISMO sobre este "
            "anillo (por eso no discriminan)",
            _m1 == _m2, "(M1=%s M2=%s)" % (_m1, _m2))
        chk("EV-27: lo que SI cae es tratar el tipo 0 como cabecera",
            _m3[0] < _m1[0] and _m3[1] > _m1[1],
            "(M3=%s vs M1=%s)" % (_m3, _m1))

        # --- EL TEST DEL RING: el unico sitio donde el count se resuelve
        # desde el hardware y no desde el codigo.
        #
        # gfx_v8_0_ring_test_ring (gfx_v8_0.c:838-864) reserva 3 dwords y
        # escribe:
        #     PACKET3(PACKET3_SET_UCONFIG_REG, 1)      <- count declara 1
        #     mmSCRATCH_REG0 - PACKET3_SET_UCONFIG_REG_START
        #     0xDEADBEEF
        # despues sondea mmSCRATCH_REG0 hasta que lea 0xDEADBEEF, que antes
        # habia puesto a 0xCAFEDEAD. Si el hardware no ejecutara el tercer
        # dword, la lectura nunca seria 0xDEADBEEF, el test daria ETIMEDOUT, y
        # amdgpu_ring_test_helper (amdgpu_ring.c:765) pondria sched.ready = 0:
        # el anillo no se usaria nunca.
        # El anillo de compute ESTA USADO. Luego el hardware consumio los 3.
        _comp = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "capturas", "amdgpu_ring_comp_1.3.1.txt")
        if os.path.exists(_comp):
            _rc = open(_comp, "rb").read()
            _wc = list(struct.unpack("<%dI" % (len(_rc) // 4), _rc))
            chk("test_ring: el anillo de compute empieza con el "
                "SET_UCONFIG_REG del test",
                ((_wc[3] >> 30) & 3) == 3 and ((_wc[3] >> 8) & 0xFF) == 0x79
                and ((_wc[3] >> 16) & 0x3FFF) == 1 and _wc[4] == 0x40
                and _wc[5] == 0xDEADBEEF,
                "d3=%s op=%s cnt=%s d4=%s d5=%s"
                % (hex(_wc[3]), hex((_wc[3] >> 8) & 0xFF),
                   (_wc[3] >> 16) & 0x3FFF, hex(_wc[4]), hex(_wc[5])))
            # 0xc040 (mmSCRATCH_REG0, gfx_8_0_d.h:454) - 0xc000
            # (PACKET3_SET_UCONFIG_REG_START, vid.h:353) = 0x40
            chk("y el desplazamiento 0x40 es mmSCRATCH_REG0(0xc040) menos "
                "START(0xc000)",
                0xc040 - 0xc000 == _wc[4],
                "(0xc040-0xc000 = 0x%x, anillo = 0x%x)"
                % (0xc040 - 0xc000, _wc[4]))
            # Y por eso el count es payload-1: declaro 1, escribio 2.
            chk("el count declara 1 y se escribieron 2 payload: por eso el "
                "hardware lee count+1",
                ((_wc[3] >> 16) & 0x3FFF) + 2 == 3,
                "(count=%d, payload escritos=2, total=%d)"
                % ((_wc[3] >> 16) & 0x3FFF, 3))
            chk("tras el test viene relleno, no trabajo: el anillo estaba "
                "rellenado",
                _wc[6] == 0xffff1000, "(d6=%s)" % hex(_wc[6]))

            # Las 7 emisiones que pm4census dejaba SIN MEDIR o LIMITE, y que
            # la propia herramienta pide mirar. Las 7 cumplen payload =
            # count+1. Se comprueba contra el recuento de amdgpu_ring_write /
            # ib.ptr[] de cada region, con los numeros de linea de grep -n.
            # La razon de que la herramienta no las viera son dos puntos
            # ciegos suyos: su regex es `amdgpu_ring_write\(\s*ring\b`, que no
            # reconoce `kiq_ring`, y su patron de opcode casa con
            # PACKET3_UNMAP_QUEUES dentro de
            # PACKET3_UNMAP_QUEUES_DOORBELL_OFFSET0.
            _SRC = ("/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/"
                    "baseline/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/"
                    "gfx_v8_0.c")

            def _cuenta(ini, fin):
                if not os.path.exists(_SRC):
                    return None
                _ls = open(_SRC, errors="replace").read().split("\n")
                _t = re.compile(r"amdgpu_ring_write\s*\(\s*(\w+)")
                _p = re.compile(r"ib\.ptr\[\s*(\d+)\s*\]\s*=")
                n = 0
                for k in range(ini - 1, min(fin, len(_ls))):
                    if _t.search(_ls[k]) or _p.search(_ls[k]):
                        n += 1
                return n

            # (linea_cabecera, count_declarado, n_payload_esperado)
            for _nom, _ini, _fin, _cnt, _esp in (
                    ("SET_RESOURCES (kiq_ring)", 4331, 4339, 6, 7),
                    ("MAP_QUEUES (kiq_ring)", 4345, 4358, 5, 6),
                    ("UNMAP_QUEUES (kiq_ring)", 4773, 4783, 4, 5)):
                _n = _cuenta(_ini, _fin)
                chk("pm4census ciego: %s escribe %d payload con count=%d"
                    % (_nom, _esp, _cnt),
                    _n == _esp + 1, "(escritos en la region=%s, payload=%s)"
                    % (_n, None if _n is None else _n - 1))
            _n891 = _cuenta(891, 896)
            chk("pm4census ciego: test_ib escribe 4 payload con count=3",
                _n891 == 5, "(lineas 891-896, escrituras=%s)" % _n891)
    else:
        print("  OMIT  sin capturas/amdgpu_ring_gfx.txt no se prueba el "
              "off-by-one sobre el anillo real")

    # --- pte.py dump: el ancho de direccion de GFX8
    #
    # cmd_dump tenia las fronteras de campo HARDCODEADAS, sin filtro de ASIC:
    # decia "bit 47..12 ADDR_BA", o sea 36 bits. Para GFX8 no es asi:
    # gmc_v8_0.c:1134 pone pte_addr_mask = 0x000000FFFFFFF000, con lo que la
    # direccion va en bits 12..39 = 28 bits. Leer la tabla generica como si
    # fuera de esta GPU da 8 bits de mas, que es justo el modo de fallo que
    # este kit lleva corrigiendo toda la sesion
    _ancho = _PTE.ancho_direccion_este_asic(0x000000FFFFFFF000)
    chk("pte dump: el ancho sale de pte_addr_mask, no de la tabla generica",
        _ancho == {"bit_mas_alto": 39, "bits_de_direccion": 28,
                   "ventana_bytes": 268435456}, "(%s)" % (_ancho,))
    chk("pte dump: 28 bits son 2^28 = 256 MiB, no 2^27 = 128",
        _ancho["ventana_bytes"] == (1 << 28),
        "(ventana=%d)" % _ancho["ventana_bytes"])
    chk("pte dump: la tabla generica da 36 bits y la diferencia con GFX8 "
        "es de 8", (47 - 12 + 1) - 28 == 8,
        "(%d - 28 = %d)" % (47 - 12 + 1, 47 - 12 + 1 - 28))
    _r = subprocess.run([sys.executable, os.path.join(AQUI, "pte.py"),
                         "dump", "0x0001002581f3"], capture_output=True,
                        text=True)
    chk("pte dump: avisa de que los campos son la union de generaciones",
        "no el layout de GFX8" in _r.stdout, "(rc=%d)" % _r.returncode)
    chk("pte dump: dice 256 MiB en la salida",
        "256 MiB" in _r.stdout, "(rc=%d)" % _r.returncode)
    chk("pte dump: la constante del modulo ES la de gmc_v8_0.c:1134",
        _PTE.PTE_ADDR_MASK_GFX8 == 0x000000FFFFFFF000,
        "(constante=0x%016x)" % _PTE.PTE_ADDR_MASK_GFX8)

    # --- F13: "protected by" es amdgpu_bo::flags en el offset 0x248
    #
    # Depende de dos cosas externas: /tmp/amdgpu_loaded.ko y
    # /sys/kernel/btf/amdgpu. Por eso es OMIT y no FALLA cuando no estan: son
    # dependencias legitimas, como el corpus lo es para pm4dec.
    import subprocess as _sb
    import re as _re7
    _KO7 = "/tmp/amdgpu_loaded.ko"
    _BTF7 = "/sys/kernel/btf/amdgpu"
    if os.path.exists(_KO7):
        _d7 = _sb.run(["objdump", "-d", "--disassemble="
                       "amdgpu_sa_bo_dump_debug_info", _KO7],
                      capture_output=True, text=True)
        chk("F13: la funcion carga el campo en el offset 0x248",
            "248(%rdi)" in _d7.stdout,
            "(objdump rc=%d)" % _d7.returncode)
    else:
        print("  OMIT  sin /tmp/amdgpu_loaded.ko no se comprueba el offset "
              "de F13")
    if os.path.exists(_BTF7) and _sb.run(["command", "-v", "pahole"],
                                          capture_output=True).returncode == 0:
        _p7 = _sb.run(["pahole", "-C", "amdgpu_bo", _BTF7],
                      capture_output=True, text=True)
        _m7 = _re7.search(r"u64\s+flags;\s+/\*\s*(\d+)\s+(\d+)\s*\*/",
                          _p7.stdout)
        chk("F13: en la BTF, flags esta en el offset 584 = 0x248",
            _m7 is not None and int(_m7.group(1)) == 0x248,
            "(encontrado=%s)" % (_m7.group(1) if _m7 else None,))
    else:
        print("  OMIT  sin /sys/kernel/btf/amdgpu o pahole no se comprueba "
              "el layout del struct")

    # --- la convergencia de 5 vias sobre el vm_flush
    #
    # Es el dato con mas fuentes independientes de toda la sesion. Si una via
    # deriva, el resto la delata. Y una de las cinco es el BINARIO que el
    # kernel tiene cargado, que no se puede deducir del fuente.
    _KO = "/tmp/amdgpu_loaded.ko"
    _KOT = os.path.abspath(os.path.join(
        AQUI, "..", "08-ARQUITECTURA", "tools", "ko_immediate.py"))
    if os.path.exists(_KO) and os.path.exists(_KOT):
        _r = subprocess.run([sys.executable, _KOT, "--func",
                             "gfx_v8_0_ring_emit_vm_flush"],
                            capture_output=True, text=True, cwd=AQUI)
        _imm = re.findall(r"0x([0-9A-Fa-f]{8})", _r.stdout)
        _esperado = ["C0053C00", "00000000", "0000051E", "00000000",
                     "00000000", "00000000", "00000020", "C0004200",
                     "00000000"]
        chk("binario: el vm_flush tiene 9 stores, en el orden esperado",
            [x.upper() for x in _imm] == _esperado,
            "(binario=%s)" % ([x.upper() for x in _imm],))
        chk("binario: el WAIT_REG_MEM del vm_flush acaba en 0x20, que es la "
            "correcion de EV-28",
            len(_imm) >= 7 and _imm[6].upper() == "00000020",
            "( septimo=%s)" % (_imm[6] if len(_imm) > 6 else "?"))
        chk("binario: el control dword del WAIT_REG_MEM es CERO, como en la "
            "fuente", _imm[1].upper() == "00000000",
            "(segundo=%s)" % _imm[1])
        # el hdp_flush, que es el otro emisor y el que SI esta en el anillo
        _r2 = subprocess.run([sys.executable, _KOT, "--func",
                              "gfx_v8_0_ring_emit_hdp_flush"],
                             capture_output=True, text=True, cwd=AQUI)
        chk("binario: el hdp_flush tiene 0x1537 y 0x1538, los mismos que el "
            "anillo capturado",
            "00001537" in [x.upper() for x in
                           re.findall(r"0x([0-9A-Fa-f]{8})", _r2.stdout)]
            and "00001538" in [x.upper() for x in
                               re.findall(r"0x([0-9A-Fa-f]{8})", _r2.stdout)],
            "(stores=%s)" % re.findall(r"0x([0-9A-Fa-f]{8})", _r2.stdout))
        chk("binario: la herramienta cuenta INMEDIATOS, no dwords emitidos: "
            "emit_wreg son 5 dwords y solo 2 inmediatos",
            len(re.findall(r"0x[0-9A-Fa-f]{8}",
                           subprocess.run(
                               [sys.executable, _KOT, "--func",
                                "gfx_v8_0_ring_emit_wreg"],
                               capture_output=True, text=True,
                               cwd=AQUI).stdout)) == 2,
            "por eso el vm_flush si se verifica completo y las otras dos no")
    else:
        print("  OMIT  sin /tmp/amdgpu_loaded.ko no se contrasta con el "
              "binario cargado")

    # --- La tabla de opcodes: QUE HEADER, y por que ----------------------------
    #
    # No es cosmetico, en los dos sentidos opuestos. Con solo sid.h (lo que
    # hacia antes) no se podian nombrar 0x49, 0x58 y 0x79, que salen en el anillo
    # de COMPUTE. Y sid.h, que es de SI/GCN1, esta DESPLAZADO UNA POSICION en los
    # tres LOAD_*: nombraria 0x5F/0x60/0x61 como LOAD_CONFIG/LOAD_CONTEXT/
    # LOAD_SH cuando en GFX8 son LOAD_SH/LOAD_CONFIG/LOAD_CONTEXT. Un nombre
    # equivocado con toda la apariencia de un dato es peor que "desconocido".
    print()
    print("  -- la tabla de opcodes de pm4dec --")
    _ops, _cab = P.cargar_opcodes()
    _cabs, _cerr = P.cabeceras_de_opcodes_de(P.FUENTE_GFX8)
    chk("tabla de opcodes: dice que cabecera usa; no es una tabla anonima",
        _cab == "vid.h", "(usa %r)" % (_cab,))
    chk("tabla de opcodes: la cabecera sale del GRAFO DE INCLUDES de "
        "gfx_v8_0.c, no de un orden fijo de ficheros",
        _cabs == ["vid.h"] and _cerr is None,
        "(gfx_v8_0.c incluye %r)" % (_cabs,))
    chk("tabla de opcodes: nombra los 3 que sid.h NO podia (RELEASE_MEM, "
        "ACQUIRE_MEM, SET_UCONFIG_REG)",
        all(_ops.get(b) == n for b, n in (
            (0x49, "PACKET3_RELEASE_MEM"),
            (0x58, "PACKET3_ACQUIRE_MEM"),
            (0x79, "PACKET3_SET_UCONFIG_REG"))))
    chk("tabla de opcodes: YA NO usa los nombres desplazados de sid.h",
        all(_ops.get(b) == n for b, n in (
            (0x5F, "PACKET3_LOAD_SH_REG"),
            (0x60, "PACKET3_LOAD_CONFIG_REG"),
            (0x61, "PACKET3_LOAD_CONTEXT_REG"))),
        "(sid.h daria LOAD_CONFIG/LOAD_CONTEXT/LOAD_SH)")
    # Este control va contra nvd.h y NO contra la tabla por defecto, y es
    # deliberado. Medido: sid.h, vid.h y cikd.h no tienen NINGUN define
    # PACKET3_* con '__' que pase el resto de filtros (0 de 74, 0 de 70, 0 de
    # 66), asi que para la tabla por defecto el filtro '__' no hace nada, y un
    # control escrito ahi NUNCA PODRIA FALLAR. En nvd.h hay 109 de 229, 28 de
    # ellos sobre el opcode 0x00; en soc15d.h, 58 de 128. El filtro carga el
    # peso ahi, y es ahi donde se comprueba que siga puesto.
    _nvd_ruta = os.path.join(P._directorio_amdgpu(), "nvd.h")
    _con_guion = len([_l for _l in open(_nvd_ruta, errors="replace")
                      if re.match(r"^#define\s+PACKET3_[A-Z0-9_]*__[A-Z0-9_]*"
                                  r"\s+(0x[0-9A-Fa-f]+|\d+)\s*$", _l)])
    _nvd_ops = P._leer_opcodes_de(_nvd_ruta)
    chk("tabla de opcodes: el filtro '__' PESA y no es decorativo; nvd.h "
        "define %d PACKET3_* con '__' y la tabla no deja entrar ninguno"
        % _con_guion,
        _con_guion > 0 and not [n for n in _nvd_ops.values() if "__" in n],
        "(nvd.h: %d defines con '__' de 229, 28 sobre el opcode 0x00; en la "
        "tabla quedan %d)"
        % (_con_guion,
           sum(1 for n in _nvd_ops.values() if "__" in n)))
    _vid_ops = P._leer_opcodes_de(os.path.join(P._directorio_amdgpu(), "vid.h"))
    chk("tabla de opcodes: PROVEN_ABSENT de defines con '__' en vid.h, que es "
        "la cabecera que usa esta GPU; por eso el filtro no se nota aqui",
        not [n for n in _vid_ops.values() if "__" in n]
        and 0x00 not in _vid_ops)
    chk("tabla de opcodes: los 3 opcodes que difieren entre generaciones "
        "quedan listados como conflicto, para que la eleccion sea auditable",
        all(v in P.CONFLICTOS_OPCODE for v in P.RENUMERADOS_SID))
    _o2, _e2 = P.cargar_opcodes(fuente="fichero_que_no_existe.c")
    chk("tabla de opcodes: una fuente inexistente FALLA, en vez de devolver "
        "una tabla a medias",
        _o2 is None and bool(_e2))
    chk("tabla de opcodes: una fuente que no incluye ningun header de opcodes "
        "tambien falla, en vez de caer a otro header por defecto",
        P.cargar_opcodes(fuente="gfx_v8_0.h")[0] is None)
    # La seleccion por generacion tiene que funcionar para VARIAS, no solo para
    # GFX8. Si se rompe la regla del include graph y todos acaban en el mismo
    # header, este control es el que lo ve.
    _gen = {f: P.cargar_opcodes(fuente=f)[1] for f in
            ("si.c", "gfx_v7_0.c", "gfx_v8_0.c", "gfx_v9_0.c", "gfx_v12_1.c")}
    chk("tabla de opcodes: la seleccion por generacion DISTINGUE las cinco, "
        "SI / CIK / GFX8 / MI / NAVI12.1, cada una con su cabecera",
        _gen == {"si.c": "sid.h", "gfx_v7_0.c": "cikd.h",
                 "gfx_v8_0.c": "vid.h", "gfx_v9_0.c": "soc15d.h",
                 "gfx_v12_1.c": "gfx_v12_1_pkt.h"},
        "(obtenido: %s)" % (_gen,))
    chk("tabla de opcodes: se auditan las SEIS cabeceras, incluida "
        "gfx_v12_1_pkt.h, la de NAVI 12.1, que se habia olvidado",
        len(P.HEADERS_OPCODE) == 6
        and "gfx_v12_1_pkt.h" in P.HEADERS_OPCODE
        and all(v in P.CONFLICTOS_OPCODE for v in P.RENUMERADOS_SID),
        "(cabeceras: %s)" % (P.HEADERS_OPCODE,))

    # El anillo SDMA NO es PM4: el paseo de pm4dec no significa nada ahi. Este
    # control lo fija, y ademas avisa si algun dia apareciera un PACKET3.
    # El patron va con os.path.join, que mete la barra, y NO pegado al
    # componente: `capturas/*` y no `capturas*`. Pegado, glob no aplica el
    # comodin al final y devuelve 0 ficheros, y un 0 de ficheros se lee igual
    # que un 0 de cabeceras. Es NR-2026-10-02-o, y por eso aqui se cuenta lo
    # que se ha abierto y se dice si no se ha abierto nada.
    _sds = sorted(glob.glob(os.path.join(AQUI, "capturas",
                                         "amdgpu_ring_sdma*.txt")))
    if not _sds:
        print("  OMIT  no hay capturas de anillo SDMA: el paseo PM4 en SDMA no "
              "se comprueba, y NO cuenta como pasado")
    _sd = set()
    for _f in _sds:
        _raw = open(_f, "rb").read()
        _w = list(struct.unpack("<%dI" % (len(_raw) // 4), _raw))
        _sd |= set((_w[i] >> 8) & 0xFF for i in range(3, len(_w) - 1)
                   if (_w[i] >> 30) & 3 in (2, 3))
    # Ni 0x00 ni 0xFF son un PACKET3: 0x00 no esta en la tabla (un opcode de
    # paquete no vale 0) y 0xFF no lo define ningun header. Que en un anillo
    # SDMA salgan dwords con bits[31:30] = 11 es en si la prueba de que se esta
    # leyendo DATO y no una cabecera: el anillo de SDMA no es una secuencia
    # PACKET3 y el paseo de pm4dec no significa nada ahi.
    chk("anillo SDMA: no aporta NINGUN PACKET3 (solo 0x00 y 0xFF, que no son "
        "opcodes), asi que el paseo de pm4dec no aplica ahi",
        bool(_sds) and _sd <= {0x00, 0xFF},
        "(%d capturas abiertas; cabeceras aparentes: %s)"
        % (len(_sds), ["0x%02x" % b for b in sorted(_sd)]))

    # El aviso de "el paseo no aplica" tiene que aparecer donde NO aplica y no
    # aparecer donde SI. Un aviso que sale siempre no informa de nada, y uno que
    # no sale nunca no cumple su funcion. Se comprueba en los dos sentidos.
    #
    # Si la captura no esta, esto NO puede pasar en silencio: seria un control
    # que se approves sin haber comprobado nada, que es la forma de un 0 vacio
    # dentro de un fichero verde. Se declara OMIT con su motivo.
    def _aviso(nombre):
        _f = os.path.join(AQUI, "capturas", "amdgpu_ring_%s.txt" % nombre)
        if not os.path.exists(_f):
            print("  OMIT  no existe %s: el aviso de pm4dec no se comprueba, "
                  "y NO cuenta como pasado" % _f)
            return None
        return subprocess.run([sys.executable,
                               os.path.join(AQUI, "pm4dec.py"), _f],
                              capture_output=True, text=True, cwd=AQUI).stdout

    _a_sdma = _aviso("sdma0")
    _a_gfx = _aviso("gfx")
    chk("pm4dec AVISA en el anillo de SDMA de que el paseo no aplica y de que "
        "el numero de paquetes no es una medida",
        (_a_sdma is not None) and ("NO APLICA A ESTE ANILLO" in _a_sdma))
    chk("pm4dec NO AVISA en el anillo GFX, donde el paseo si aplica: un aviso "
        "que saliera siempre no informaria de nada",
        (_a_gfx is not None) and ("NO APLICA A ESTE ANILLO" not in _a_gfx))
    chk("pm4dec dice DE QUE cabecera saca la tabla, y no dice 'sid.h' cuando la "
        "tabla viene de vid.h (antes la etiqueta de la salida era falsa)",
        (_a_gfx is not None) and ("desde vid.h" in _a_gfx))

    # --- EV-38: los TRES codificadores de PTE y la unicidad de la mascara ----
    #
    # Todo se lee del FUENTE, no de constantes escritas aqui. Si el corpus
    # cambia, el control tiene que caer, no seguir contando lo que era cierto
    # la ultima vez que se miró.
    print()
    print("  -- EV-38: codificadores de PTE/PDE y la mascara --")
    _AMD = os.path.join(AQUI, "..", "RESEARCH", "baseline", "linux-7.1.3",
                        "drivers", "gpu", "drm", "amd", "amdgpu")
    if not os.path.isdir(_AMD):
        print("  OMIT  no hay arbol amdgpu: EV-38 no se comprueba, y NO cuenta")
    else:
        _lecturas, _asig, _decl = [], [], []
        for _f in sorted(os.listdir(_AMD)):
            if not _f.endswith((".c", ".h")):
                continue
            for _n, _l in enumerate(open(os.path.join(_AMD, _f),
                                          errors="replace"), 1):
                if "pte_addr_mask" not in _l:
                    continue
                _c = _l.strip()
                if _c.startswith("uint64_t") and _c.endswith(";"):
                    _decl.append("%s:%d" % (_f, _n))
                elif re.match(r"(adev->gmc\.)?pte_addr_mask\s*=\s*0x", _c):
                    _asig.append("%s:%d" % (_f, _n))
                elif re.match(r"adev->gmc\.pte_addr_mask\s*=\s*\w", _c):
                    # gmc_v12_0.c:921 copia de una variable local: tambien es
                    # asignacion. Sin esta rama caia en "lectura" y hacia
                    # parecer que la mascara se leia dos veces.
                    _asig.append("%s:%d" % (_f, _n))
                else:
                    _lecturas.append(("%s:%d" % (_f, _n), _c))
        chk("EV-38: pte_addr_mask se LEE exactamente una vez en todo el driver",
            len(_lecturas) == 1,
            "(lecturas: %d -> %s)" % (len(_lecturas), [x[0] for x in _lecturas]))
        chk("EV-38: esa unica lectura es la de la ruta CPU, con la mascara a "
            "la izquierda de un AND",
            len(_lecturas) == 1 and "&" in _lecturas[0][1]
            and _lecturas[0][0].startswith("amdgpu_gmc.c:"),
            "(%s)" % (_lecturas,))
        chk("EV-38: 12 apariciones clasificadas como 9 asignaciones, 2 "
            "declaraciones y 1 lectura, y ninguna se queda sin clasificar",
            (len(_asig), len(_decl), len(_lecturas)) == (9, 2, 1),
            "(asig=%d decl=%d lect=%d)" % (len(_asig), len(_decl),
                                           len(_lecturas)))

        # El ancho se CALCULA con la mascara leida del fuente. 28 bits es la
        # cifra correcta para GFX8; lo que se comprueba es que bits(12..39) es
        # lo que sale de 0x000000FFFFFFF000, para que nadie lo asuma.
        #
        # El fichero esta FIJADO a proposito. Un grep por el valor, sin fijar la
        # generacion, encuentra el primero que coincide, y gmc_v6_0.c y
        # gmc_v7_0.c tienen LA MISMA mascara que gmc_v8_0.c. Medido: al mutar la
        # de v8_0 para comprobar este control, el control leia la de v6 y pasaba
        # en verde. O sea que el control cometia exactamente el error que EV-38
        # describe: mezclar generaciones al leer un valor.
        _linea = None
        for _l in open(os.path.join(_AMD, "gmc_v8_0.c"), errors="replace"):
            if "adev->gmc.pte_addr_mask = 0x" in _l:
                _linea = _l.strip()
        _mm = re.search(r"0x([0-9A-Fa-f]+)ULL", _linea or "")
        _v = int(_mm.group(1), 16) if _mm else 0
        chk("EV-38: el ancho de la mascara sale del fuente y son 28 bits de "
            "direccion, ventana 2^28",
            _v.bit_length() - 12 == 28 and (1 << (_v.bit_length() - 12)) == 1 << 28,
            "(mascara=0x%X bit_alto=%d bits_dir=%d)" % (_v, _v.bit_length() - 1,
                                                        _v.bit_length() - 12))
        chk("EV-38: los bits 0..11 de la mascara estan a cero, o sea que el "
            "offset de pagina no se enmascara",
            _v != 0 and (_v & 0xFFF) == 0, "(mascara=0x%X)" % _v)
        chk("EV-38: la mascara leida sale de gmc_v8_0.c y no de otra "
            "generacion, aunque varias compartan ese mismo valor",
            _v == 0x000000FFFFFFF000,
            "(leido=0x%X desde gmc_v8_0.c)" % _v)

        # Los tres codificadores existen: si uno desaparece, el recuento de
        # "tres" pasa a ser falso y hay que decirlo.
        _gmc = open(os.path.join(_AMD, "amdgpu_gmc.c"),
                    errors="replace").read()
        _sdma = open(os.path.join(_AMD, "amdgpu_vm_sdma.c"),
                     errors="replace").read()

        # El fichero de SDMA NO se escribe aqui: se DERIVA del case del chip.
        # Escribi "sdma_v2_4.c" a mano en la primera version de EV-38 y era la
        # generacion equivocada -- Polaris12 instala sdma_v3_1_ip_block, que
        # comparte sdma_v3_0_ip_funcs. Un nombre de fichero escrito a mano en un
        # control es una generacion supuesta; este lo lee del case.
        # El fichero de SDMA NO se escribe aqui: se DERIVA del case del chip.
        # Escribi "sdma_v2_4.c" a mano en la primera version de EV-38 y era la
        # GENERACION EQUIVOCADA: Polaris12 instala sdma_v3_1_ip_block, que
        # comparte sdma_v3_0_ip_funcs. Un nombre de fichero puesto a mano en un
        # control es una generacion supuesta.
        #
        # Y la version intermedia de esta derivacion tenia el defecto que el
        # control pretendia cazar: hacia vi.find("case CHIP_POLARIS12:") sobre
        # el fichero entero, y vi.c tiene OCHO casos de POLARIS12 en switches
        # distintos. Agarraba el primero, que no es vi_set_ip_blocks. Medido.
        _vi = open(os.path.join(_AMD, "vi.c"), errors="replace").read()
        _fi = _vi.find("int vi_set_ip_blocks(")
        _ff = _vi.find("\nint ", _fi + 10)
        _cuerpo_vi = _vi[_fi:_ff if _ff > 0 else len(_vi)]
        _k = _cuerpo_vi.find("case CHIP_POLARIS12:")
        _m = re.search(r"sdma_v(\d)_(\d)_ip_block",
                       _cuerpo_vi[_k:_k + 900]) if _k >= 0 else None
        _bloque = ("sdma_v%s_%s_ip_block" % (_m.group(1), _m.group(2))
                   if _m else None)
        chk("EV-38: el case de CHIP_POLARIS12 DENTRO de vi_set_ip_blocks "
            "instala sdma_v3_1_ip_block, y se lee del fuente",
            _bloque == "sdma_v3_1_ip_block",
            "(encontrado: %s; casos de POLARIS12 en vi.c: %d, en esta funcion: "
            "%d)" % (_bloque, _vi.count("case CHIP_POLARIS12:"),
                     _cuerpo_vi.count("case CHIP_POLARIS12:")))

        # Del bloque, a su fichero y a su .funcs.
        _impl = _pnombre = _fnombre = None
        for _f in sorted(os.listdir(_AMD)):
            if not _f.endswith(".c"):
                continue
            _t = open(os.path.join(_AMD, _f), errors="replace").read()
            _i2 = _t.find("struct amdgpu_ip_block_version %s" % (_bloque or "@@"))
            if _i2 < 0:
                continue
            _m2 = re.search(r"\.funcs\s*=\s*&(\w+)", _t[_i2:_i2 + 320])
            if not _m2:
                break
            _fnombre = _m2.group(1)
            _impl = _f
            break
        chk("EV-38: ese bloque vive en sdma_v3_0.c y comparte "
            "sdma_v3_0_ip_funcs, o sea que el codificador vivo es el de v3.0",
            _impl == "sdma_v3_0.c" and _fnombre == "sdma_v3_0_ip_funcs",
            "(fichero=%s funcs=%s)" % (_impl, _fnombre))

        # De la tabla de PTE: los punteros vivos.
        _s = (open(os.path.join(_AMD, _impl), errors="replace").read()
              if _impl else "")
        _wp = _sp = _cd = None
        # El "= {" importa: entre el nombre de la tabla y la llave hay un "=",
        # no solo espacios. Con \s*\{ solo, la expresion no casa y todos los
        # controles siguientes darian falso por una razon que no es la suya.
        _m3 = re.search(r"struct amdgpu_vm_pte_funcs (\w+vm_pte_funcs)\s*=\s*\{"
                        r"(.*?)\n\};", _s, re.S)
        if _m3:
            _pnombre = _m3.group(1)
            _tabla = _m3.group(2)
            _wp = re.search(r"\.write_pte\s*=\s*(\w+)", _tabla)
            _sp = re.search(r"\.set_pte_pde\s*=\s*(\w+)", _tabla)
            _cd = re.search(r"\.copy_pte_num_dw\s*=\s*(\d+)", _tabla)
            _wp = _wp.group(1) if _wp else None
            _sp = _sp.group(1) if _sp else None
            _cd = int(_cd.group(1)) if _cd else None
        chk("EV-38: la tabla de PTE viva asigna write_pte y set_pte_pde, y "
            "declara copy_pte_num_dw = 7 (no los 10 de GEN_PTEPDE)",
            _pnombre == "sdma_v3_0_vm_pte_funcs" and _wp and _sp and _cd == 7,
            "(tabla=%s write_pte=%s set_pte_pde=%s copy_pte_num_dw=%s)"
            % (_pnombre, _wp, _sp, _cd))

        def _cuerpo_de(nombre):
            _m = re.search(r"static void %s\(.*?\)\s*\{(.*?)\n\}" % nombre,
                           _s, re.S)
            return _m.group(1) if _m else None

        _cb_write = _cuerpo_de(_wp) if _wp else None
        _cb_gen = _cuerpo_de(_sp) if _sp else None
        chk("EV-38: el codificador de 1-2 entradas parte el valor en dos stores "
            "de 32 bits, con la cabecera WRITE_LINEAR",
            _cb_write is not None
            and "lower_32_bits(value)" in _cb_write
            and "upper_32_bits(value)" in _cb_write
            and "SDMA_SUBOP_WRITE_LINEAR" in _cb_write,
            "(funcion=%s)" % (_wp,))

        _ndw = len(re.findall(r"ib->ptr\[ib->length_dw\+\+\]",
                              _cb_gen or ""))
        chk("EV-38: el codificador de 3+ es GEN_PTEPDE, con 'mask' y 'value' "
            "en campos separados, y son 10 dwords",
            _cb_gen is not None and "SDMA_OP_GEN_PTEPDE" in _cb_gen
            and _ndw == 10 and "/* mask */" in _cb_gen
            and "/* value */" in _cb_gen,
            "(funcion=%s ndw=%d)" % (_sp, _ndw))

        chk("EV-38: el criterio de eleccion de ruta es count < 3, leido de "
            "amdgpu_vm_sdma.c",
            re.search(r"if \(count < 3\)", _sdma) is not None,
            "(amdgpu_vm_sdma.c contiene 'if (count < 3)')")

        chk("EV-38: los CUATRO codificadores existen: writeq en CPU, split de "
            "32 en SDMA, GEN_PTEPDE con campo mask, y u64 armado en el IB",
            ("writeq(value" in _gmc) and (_cb_write is not None)
            and (_cb_gen is not None)
            and ("pte[i] = amdgpu_vm_map_gart" in _sdma),
            "(writeq=%s split=%s gen=%s en_ib=%s)"
            % ("writeq(value" in _gmc, _cb_write is not None,
               _cb_gen is not None, "pte[i] = amdgpu_vm_map_gart" in _sdma))

        chk("EV-38: las rutas SDMA NO enmascaran; solo la CPU lo hace",
            ("addr | flags" in _sdma or "addr|flags" in _sdma)
            and "pte_addr_mask" not in _sdma
            and "pte_addr_mask" not in _s,
            "(amdgpu_vm_sdma.c menciona la mascara: %s; %s: %s)"
            % ("pte_addr_mask" in _sdma, _impl, "pte_addr_mask" in _s))

    print("-" * 62)
    if FALLOS:
        print("%d control(es) FALLAN. pm4dec NO puede usarse como autoridad."
              % len(FALLOS))
        return 1
    print("todos los controles pasan")
    return 0


if __name__ == "__main__":
    sys.exit(main())
