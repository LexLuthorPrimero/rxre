#!/usr/bin/env python3
# CONTRACT: name=ip_surface
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no

"""ip_surface -- la superficie real de funciones de cada bloque IP, leida del .ko.

POR QUE EXISTE. El kernel registra 9 bloques IP en esta placa (hallazgo 190), y
cada bloque es un `struct amdgpu_ip_block_version` ESTATICO Y CONSTANTE dentro del
modulo cargado. Ese struct dice, sin ambiguedad y sin interpretar codigo, que
operaciones de ese ASIC existen de verdad: cuales de early_init/hw_init/soft_reset/
set_clockgating_state/... estan implementadas y cuales son NULL.

Eso responde de forma MECANICA una pregunta que 135 dejo abierta (cual es la
lista de capacidades por ASIC), y no depende de leer 40 ficheros de generacion.

POR QUE EL .KO Y NO EL CODIGO FUENTE. En el fuente, `gfx_v8_0_ip_block` y
`gfx_v10_0_ip_block` se ven IGUALES (mismo tipo de struct, misma tabla de
punteros). Lo que distingue a esta placa es QUE PUNTERO SE REGISTRO, y eso solo
esta en el binario. Ademas el binario es el que se esta ejecutando: si el fuente
y el .ko divergieran, el .ko tiene razon.

LIMITE DECLARADO. Se leen LAS TABLAS, no se desensambla codigo. Que un puntero sea
NULL significa "el driver no lo implemento para este ASIC", NO "el hardware no lo
puede hacer". Es el limite de la fuente, no del metodo, y no lo cruzo.

Uso:
  ip_surface.py --bloque gfx_v8_0_ip_block     una tabla, con sus funciones
  ip_surface.py --todos                        todos los bloques del .ko
  ip_surface.py --generacion                   que bloques existen por major
  ip_surface.py --self-test

Codigos de salida:
  0  ok
  2  fichero .ko ausente
  3  bloque no encontrado en el .ko
  4  .ko sin .symtab (no se puede resolver simbolos)
"""

import os
import struct
import sys

KO = "/tmp/amdgpu_loaded.ko"

# amd_shared.h:454. 24 campos: char *name y 23 punteros a funcion.
# El orden importa: se lee por indice, y un campo nuevo desplazaria todos los
# siguientes en silencio. Por eso el self-test comprueba el TAMANO total.
AMD_IP_FUNCS = [
    "name", "early_init", "late_init", "sw_init", "sw_fini", "early_fini",
    "hw_init", "hw_fini", "late_fini", "prepare_suspend", "suspend", "resume",
    "complete", "is_idle", "wait_for_idle", "check_soft_reset",
    "pre_soft_reset", "soft_reset", "post_soft_reset",
    "set_clockgating_state", "set_powergating_state", "get_clockgating_state",
    "dump_ip_state", "print_ip_state",
]
FUNCS_BYTES = len(AMD_IP_FUNCS) * 8

# amdgpu_ip.h:110. {u32 type; u32 major; u32 minor; u32 rev; ptr funcs;}
# El puntero queda alineado a 8, asi que funcs va en +16, no en +16..+20.
BLK_TYPE, BLK_MAJOR, BLK_MINOR, BLK_REV, BLK_FUNCS = 0, 4, 8, 12, 16

SHT_RELA = 4
SHT_NOBITS = 8


def die(codigo, msg):
    sys.stderr.write("ip_surface: %s\n" % msg)
    return codigo


class Elf(object):
    """Lector ELF64 minimo: secciones, simbolos y relocaciones.

    Solo lo justo para leer tablas constantes de un objeto reubicable (.ko).
    En un .ko los punteros NO son direcciones: son RELOCACIONES contra simbolos.
    Por eso `en`() devuelve un nombre de simbolo, no un numero.
    """

    def __init__(self, ruta):
        self.ruta = ruta
        if not os.path.exists(ruta):
            raise IOError(2)
        self.d = open(ruta, "rb").read()
        if self.d[:4] != b"\x7fELF":
            raise ValueError("no es ELF")
        if self.d[4] != 2:
            raise ValueError("no es ELF64")
        self._secciones()
        self._simbolos()
        self._relocs()

    def _secciones(self):
        d = self.d
        e_shoff, = struct.unpack_from("<Q", d, 0x28)
        e_shentsize, = struct.unpack_from("<H", d, 0x3A)
        e_shnum, = struct.unpack_from("<H", d, 0x3C)
        e_shstrndx, = struct.unpack_from("<H", d, 0x3E)
        self.secciones = []
        for i in range(e_shnum):
            o = e_shoff + i * e_shentsize
            (nm, tp, fl, ad, of, sz, lk, inf, al, es) = \
                struct.unpack_from("<IIQQQQIIQQ", d, o)
            self.secciones.append({"name": nm, "type": tp, "flags": fl,
                                   "addr": ad, "off": of, "size": sz,
                                   "link": lk, "info": inf, "entsize": es})
        strs = self.secciones[e_shstrndx]
        base = strs["off"]
        for s in self.secciones:
            s["nombre"] = self._cstr(base + s["name"])

    def _cstr(self, off):
        fin = self.d.index(b"\0", off)
        return self.d[off:fin].decode("utf-8", "replace")

    def _simbolos(self):
        idx = None
        for i, s in enumerate(self.secciones):
            if s["nombre"] == ".symtab":
                idx = i
                break
        if idx is None:
            raise KeyError(".symtab")
        self.simtab = idx
        st = self.secciones[idx]
        strs = self.secciones[st["link"]]
        base = strs["off"]
        self.sim = {}
        n = st["size"] // 24
        for i in range(n):
            o = st["off"] + i * 24
            nm, info, other, shndx, val, size = \
                struct.unpack_from("<IBBHQQ", self.d, o)
            if nm == 0:
                continue
            nombre = self._cstr(base + nm)
            if nombre:
                self.sim[nombre] = (shndx, val, size, info & 0xF)
        # Indice inverso: resuelve un (seccion, offset) a nombre de simbolo.
        # Es lo que permite seguir un puntero escrito contra un simbolo de
        # seccion, donde el offset real va en el addend.
        self.por_offset = {}
        for n, (sh, v, _sz, _t) in self.sim.items():
            self.por_offset.setdefault((sh, v), n)

    def _relocs(self):
        """(seccion, offset) -> nombre de simbolo destino de la reubicacion."""
        self.rel = {}
        for i, s in enumerate(self.secciones):
            if s["type"] != SHT_RELA:
                continue
            strs = self.secciones[s["link"]]
            base = strs["off"]
            # BUG QUE ESTA HERRAMIENTA TENIA: indexaba por el indice de la
            # seccion RELA (i), no por la seccion a la que la reubicacion se
            # APLICA (sh_info). Como se busca con el indice de la seccion de
            # datos, la busqueda nunca encontraba nada y TODOS los punteros
            # parecian NULL. Con sh_info, .rela.rodata indexa .rodata.
            obj = s["info"]
            n = s["size"] // 24
            for k in range(n):
                o = s["off"] + k * 24
                r_off, r_info, r_add = struct.unpack_from("<QQq", self.d, o)
                rsym = r_info >> 32
                if rsym == 0:
                    continue
                noff = strs["off"] + rsym * 24
                nm, _i, _o, sh_sym = struct.unpack_from("<IBBH", self.d, noff)
                self.rel[(obj, r_off)] = (self._cstr(base + nm), sh_sym, r_add)

    def leer(self, shndx, off, tam):
        s = self.secciones[shndx]
        if s["type"] == SHT_NOBITS:
            return b"\0" * tam
        return self.d[s["off"] + off: s["off"] + off + tam]

    def puntero(self, shndx, off):
        """Nombre del simbolo al que apunta (shndx, off), o None si es NULL.

        Hay DOS formas de puntero en un .ko y solo una es obvia:

        1. Reubicacion contra un simbolo CON NOMBRE. El objetivo es ese simbolo.
        2. Reubicacion contra un SIMBOLO DE SECCION (nombre vacio). Entonces el
           objetivo es el simbolo que este en (sh_shndx, addend). Es el caso de
           los punteros a datos locales, y es MAYORITARIO aqui: casi todas las
           tablas ip_funcs se referencian asi, con el offset en el addend.

        Un puntero a NULL es un 0 sin reubicacion (o una reubicacion cuyo
        resultado es 0). Trato ambos como NULL y NO invento un nombre.
        """
        r = self.rel.get((shndx, off))
        if r is None:
            return None
        nombre, sh_simbolo, addend = r
        if nombre:
            return nombre
        return self.por_offset.get((sh_simbolo, addend))


STT_OBJECT = 1
BLK_BYTES = 24


def bloques_reales(elf):
    """Solo los simbolos que SON la tabla, no funciones que casen por el sufijo.

    `amdgpu_device_ip_get_ip_block` es una FUNCION y termina en `_ip_block`. Sin
    este filtro entraba como bloque con type/funcs leidos de .text, y producia
    filas con basura que parecia dato. Dos señales independientes: tipo STT_OBJECT
    y tamano exacto de la struct.
    """
    out = []
    for n, (shndx, val, size, tipo) in elf.sim.items():
        if not n.endswith("_ip_block") or tipo != STT_OBJECT:
            continue
        if size != BLK_BYTES:
            continue
        out.append(n)
    return sorted(out)


def funcs_de(elf, shndx, off):
    """Lista (campo, simbolo|NULL) de los 24 campos de un amd_ip_funcs."""
    out = []
    for i, campo in enumerate(AMD_IP_FUNCS):
        out.append((campo, elf.puntero(shndx, off + i * 8)))
    return out


def bloque(elf, nombre):
    if nombre not in elf.sim:
        return None
    shndx, val, size, _t = elf.sim[nombre]
    tp = struct.unpack("<I", elf.leer(shndx, val + BLK_TYPE, 4))[0]
    mj = struct.unpack("<I", elf.leer(shndx, val + BLK_MAJOR, 4))[0]
    mn = struct.unpack("<I", elf.leer(shndx, val + BLK_MINOR, 4))[0]
    rv = struct.unpack("<I", elf.leer(shndx, val + BLK_REV, 4))[0]
    return {"tipo": tp, "major": mj, "minor": mn, "rev": rv,
            "funcs_sym": elf.puntero(shndx, val + BLK_FUNCS),
            "seccion": shndx, "off": val}


def self_test():
    fails = []

    def eq(label, got, want):
        if got != want:
            fails.append("%s: %r != %r" % (label, got, want))

    # 1. Layout de la struct. Si upstream añade un campo, el self-test falla.
    eq("amd_ip_funcs: numero de campos", len(AMD_IP_FUNCS), 24)
    eq("amd_ip_funcs: tamano", FUNCS_BYTES, 192)
    eq("primer campo", AMD_IP_FUNCS[0], "name")
    eq("ultimo campo", AMD_IP_FUNCS[-1], "print_ip_state")

    # 2. CONTROL NEGATIVO: un .ko inexistente tiene que dar codigo 2, no traceback
    #    ni una lista vacia que parece "no hay bloques".
    try:
        Elf("/tmp/opencode/no_existe.este.ko")
        fails.append("control negativo: un .ko inexistente no lanzo excepcion")
    except IOError as e:
        eq("codigo de .ko inexistente", e.args[0], 2)

    # 3. CONTROL NEGATIVO: un fichero que no es ELF tiene que fallar, no devolver
    #    una struct vacia.
    try:
        Elf("/etc/hostname")
        fails.append("control negativo: un fichero no-ELF no lanzo excepcion")
    except (ValueError, KeyError, IOError):
        pass

    # 4. CARGA DEL .KO REAL. Si no existe, esto no se puede validar.
    if not os.path.exists(KO):
        fails.append("no existe %s: no se puede validar el pipeline" % KO)
        return _fin(fails)

    try:
        elf = Elf(KO)
    except Exception as e:
        fails.append("no se pudo abrir el .ko: %r" % (e,))
        return _fin(fails)

    # 5. El .ko debe tener simbolos. Un .symtab vacio haria que todo se vea NULL.
    if len(elf.sim) < 100:
        fails.append("el .ko solo tiene %d simbolos: sospecho de symtab vacio"
                     % len(elf.sim))
    if not elf.rel:
        fails.append("el .ko no tiene reubicaciones: los punteros no se podrian "
                     "resolver, y todo pareceria NULL")

    # 6. TEST DE PIPELINE con ANCLA EXTERNA. gfx_v8_0 debe dar 8.0.0. Eso no lo
    #    afirmo yo: el log del kernel dice <gfx_v8_0_0> de forma independiente.
    #    Dos fuentes distintas tienen que coincidir.
    b = bloque(elf, "gfx_v8_0_ip_block")
    if b is None:
        fails.append("no encontre gfx_v8_0_ip_block en el .ko: el regex de "
                     "nombres o la tabla de simbolos no casa")
    else:
        eq("gfx_v8_0_ip_block.major (ancla: log del kernel <gfx_v8_0_0>)",
           b["major"], 8)
        eq("gfx_v8_0_ip_block.minor", b["minor"], 0)
        eq("gfx_v8_0_ip_block.rev", b["rev"], 0)
        if not b["funcs_sym"]:
            fails.append("gfx_v8_0_ip_block.funcs no se resolvio: el puntero "
                         "parece NULL, lo que haria ver todos los bloques "
                         "identicos")
        else:
            eq("gfx_v8_0_ip_block.funcs_sym", b["funcs_sym"],
               "gfx_v8_0_ip_funcs")

    # 7. Los 9 bloques que el kernel registra en esta placa deben existir en el
    #    .ko. Si uno falta, la extraccion no cubre esta placa.
    for n in ("vi_common_ip_block", "gmc_v8_1_ip_block", "tonga_ih_ip_block",
              "gfx_v8_0_ip_block", "sdma_v3_1_ip_block", "pp_smu_ip_block",
              "dm_ip_block", "uvd_v6_3_ip_block", "vce_v3_4_ip_block"):
        if n not in elf.sim:
            fails.append("falta el bloque %s de los 9 que registra el kernel" % n)

    # 8. CONTROL NEGATIVO: un bloque que NO existe tiene que decir que no existe,
    #    no devolver una struct de ceros que parece "un ASIC sin funciones".
    if bloque(elf, "no_existe_este_ip_block") is not None:
        fails.append("control negativo: un bloque inexistente devolvio datos")

    # 9. Que el recorrido no se cuenta a si mismo: el total de bloques con sufijo
    #    _ip_block tiene que ser > 9, porque el .ko contiene todos los ASIC.
    total = len(bloques_reales(elf))
    if total <= 9:
        fails.append("solo %d bloques _ip_block: no se esta leyendo el .ko "
                     "entero" % total)

    return _fin(fails)


def _fin(fails):
    if fails:
        print("self-test FALLA (%d)" % len(fails))
        for f in fails:
            print("   " + f)
        return 1
    print("self-test OK (4 vectores de layout, 2 anclas externas, "
          "5 controles)")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    try:
        elf = Elf(KO)
    except IOError:
        return die(2, "no existe %s" % KO)
    except Exception as e:
        return die(4, ".ko ilegible o sin .symtab: %r" % (e,))

    nombres = bloques_reales(elf)

    if "--bloque" in argv:
        nom = argv[argv.index("--bloque") + 1]
        b = bloque(elf, nom)
        if b is None:
            return die(3, "no existe %s en el .ko" % nom)
        print("%s  type=%d  version=%d.%d.%d"
              % (nom, b["tipo"], b["major"], b["minor"], b["rev"]))
        print("funcs -> %s" % b["funcs_sym"])
        fb = elf.sim[b["funcs_sym"]]
        n = 0
        for campo, sym in funcs_de(elf, fb[0], fb[1]):
            if sym:
                print("   %-24s %s" % (campo, sym))
                n += 1
        print("   (%d de %d campos implementados)" % (n, len(AMD_IP_FUNCS)))
        return 0

    if "--generacion" in argv:
        gens = {}
        for nom in nombres:
            b = bloque(elf, nom)
            if b:
                gens.setdefault(b["major"], []).append(
                    (nom, "%d.%d.%d" % (b["major"], b["minor"], b["rev"])))
        for maj in sorted(gens):
            print("IP v%-3d : %d bloques" % (maj, len(gens[maj])))
            for nom, v in gens[maj]:
                print("        %-34s %s" % (nom, v))
        return 0

    # --todos
    print("%d bloques *_ip_block en el .ko" % len(nombres))
    for nom in nombres:
        b = bloque(elf, nom)
        if not b:
            continue
        print("  %-34s %d.%d.%d" % (nom, b["major"], b["minor"], b["rev"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))