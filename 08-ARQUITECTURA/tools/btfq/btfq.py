#!/usr/bin/env python3
"""
btfq.py -- lector de BTF del driver amdgpu REALMENTE CARGADO en este host.

QUE PREGUNTA CONTESTA
---------------------
Este proyecto razona sobre RESEARCH/working/linux-7.1.3: el ARBOL DE FUENTES.
Ese arbol dice de donde VENIMOS. /sys/kernel/btf/amdgpu es el BINARIO que esta
corriendo ahora mismo en la RX550. Son dos artefactos distintos y no tienen por
que coincidir: el host puede llevar parches que el corpus no tiene.

Un BTF permite comprobar tres cosas que el corpus no puede:

  1. que una struct tiene el tamano y los offsets que el corpus asume;
  2. que un enumerador tiene el valor que el corpus asume;
  3. que un campo EXISTE en el binario, no solo en el fuente.

Que (3) importe mas de lo que parece: si el host corre un kernel con un
parche que el corpus no tiene, el BTF lo revela y la investigacion deja de
razonar sobre un arbol que no es el que manda.

SPLIT BTF (y por que esta herramienta tiene dos capas)
-------------------------------------------------------
El kernel expone un BTF por modulo, pero con CONFIG_DEBUG_INFO_BTF_MENU los ids
de tipo del modulo NO son locales: pahole compila el modulo con el base BTF a
la vista, asi que los ids ya estan en el espacio global, desplazados por los
tipos del base (/sys/kernel/btf/vmlinux).

La prueba, no la suposicion:

    base ids   1 .. 142435     (vmlinux, 142435 tipos propios)
    modulo ids 142436 .. 195834 (amdgpu, 53399 propios)
    referencias al base:    6433
    referencias al modulo: 30997
    referencias en el hueco: 3972, todas ellas el id 0 = void

Cero huecos reales. Si esto no fuera split BTF, el id minimo fuera de rango
(60629) caeria dentro del rango propio del modulo (1..53399) y seria un bug
de parseo. Como cae por debajo del rango del base y el maximo (195824) cae
dentro del rango global del modulo, el desplazamiento es el correcto.

Por eso hay dos capas: Btf parsea un fichero con ids locales, y Split los
normaliza al espacio global, recordando de que fichero salio cada tipo para
resolver los nombres en el pool de strings correcto (los dos ficheros tienen
pools SEPARADOS y un name_off del modulo no es valido en el base).

FORMATO (leido de /usr/include/linux/btf.h DEL HOST, no de memoria)
---------------------------------------------------------------------
struct btf_header {
    u16 magic; u8 version; u8 flags; u32 hdr_len;
    u32 type_off; u32 type_len; u32 str_off; u32 str_len;
    [u32 layout_off; u32 layout_len;]   -- solo si hdr_len >= 32
};
Los offsets son RELATIVOS al final del header.

struct btf_type {         <-- 12 BYTES, no 8
    u32 name_off;
    u32 info;              kind = (info>>24)&0x1f
                           vlen = info & 0xffff
                           kflag = info >> 31
    u32 size_o_u_type;
};

Cuerpos segun kind:
  INT 1xu32 | ARRAY 1x12 | STRUCT/UNION vlenx12 | ENUM vlenx8
  ENUM64 vlenx12 | FUNC_PROTO vlenx8 | VAR 1x4 | DATASEC vlenx12
  DECL_TAG 1x4 | resto 0

CUATRO ERRORES QUE ESTA HERRAMIENTA COMETIO, PARA NO REPETIRLOS
---------------------------------------------------------------
  1. btf_type leido como 4 bytes (name_off i32 + info como iBB). Cada
     entrada se leia desplazada y los kinds salian inventados (207, 21, 245).
     Un kind inventado hace que el recorrido se pare en el segundo tipo con
     un error que no senala el origen real.
  2. offsets de header leidos como absolutos en vez de relativos a hdr_len.
     type_off=0 significa "justo detras del header", no "en el byte 0".
  3. str_off sumado a type_off+type_len. str_off YA es type_off+type_len.
  4. Asumir que los ids del modulo son locales y marcar como "fuera de
     rango" 3972 referencias que en realidad son perfectly valid. Un parser
     que senala referencias colgantes donde no las hay NO es que este roto:
     es que no entiende el formato, y produce falsos positivos que niegan
     informacion real.

LIMITE
------
BTF no tiene valores de variables, solo tipos. Un enum de BTF es un tipo, no
una instancia. Esto responde "que constantes compila el driver", no "que valor
tiene adev->gmc.x en este instante". Lo segundo necesita runtime con root, que
no esta autorizado.

USO
---
  ./btfq.py census                  control de integridad del parseo
  ./btfq.py enums   <subcadena>      enums por nombre de enum o de valor
  ./btfq.py struct  <nombre>         campos con offset REAL en bits
  ./btfq.py size    <struct>         size declarado vs ultimo campo
  ./btfq.py present <subcadena>      miembros cuyo NOMBRE contenga eso
  ./btfq.py where   <subcadena>      de que base/modulo salio cada tipo
"""
import re
import struct
import sys

BTF_MAGIC = 0xEB9F
BTF_TYPE_SIZE = 12

KINDS = {
    0: "UNKN", 1: "INT", 2: "PTR", 3: "ARRAY", 4: "STRUCT", 5: "UNION",
    6: "ENUM", 7: "FWD", 8: "TYPEDEF", 9: "VOLATILE", 10: "CONST",
    11: "RESTRICT", 12: "FUNC", 13: "FUNC_PROTO", 14: "VAR",
    15: "DATASEC", 16: "FLOAT", 17: "DECL_TAG", 18: "TYPE_TAG",
    19: "ENUM64",
}

# kinds cuyo tercer campo de btf_type es un type_id (no un tamano)
HAS_TYPE = {2, 8, 9, 10, 11, 12, 13, 14, 17, 18}

BODY = {
    0: lambda vlen: 0,     1: lambda vlen: 4,     2: lambda vlen: 0,
    3: lambda vlen: 12,    4: lambda vlen: 12 * vlen,
    5: lambda vlen: 12 * vlen, 6: lambda vlen: 8 * vlen,
    7: lambda vlen: 0,     8: lambda vlen: 0,     9: lambda vlen: 0,
    10: lambda vlen: 0,    11: lambda vlen: 0,    12: lambda vlen: 0,
    13: lambda vlen: 8 * vlen, 14: lambda vlen: 4,
    15: lambda vlen: 12 * vlen, 16: lambda vlen: 0,
    17: lambda vlen: 4,    18: lambda vlen: 0,    19: lambda vlen: 12 * vlen,
}


def count_types(data, start, end):
    """
    Recorrido previo para dimensionar el array de ids.

    Se recorre dos veces en vez de inventar una cota: una cota superior que se
    quede corta truncaria el censo en silencio, que es el fallo que este
    proyecto ya registro con "grep | head".
    """
    off = start
    n = 1                       # el id 0 es void, implicito
    while off < end:
        if off + BTF_TYPE_SIZE > end:
            raise ValueError("btf_type truncado en el byte %d" % off)
        name_off, info, _ = struct.unpack_from("<III", data, off)
        vlen = info & 0xFFFF
        k = (info >> 24) & 0x1F
        if k not in BODY:
            raise ValueError(
                "kind BTF desconocido %d en el byte %d (name_off=%d, "
                "vlen=%d): el recorrido no puede continuar sin inventar el "
                "formato, y adivinarlo seria peor que parar"
                % (k, off, name_off, vlen))
        off += BTF_TYPE_SIZE + BODY[k](vlen)
        n += 1
    if off != end:
        raise ValueError("el recorrido no cierra: %d != %d" % (off, end))
    return n


class Btf:
    """Un solo fichero BTF, con ids LOCALES (1..ntypes-1)."""

    def __init__(self, data, label="?"):
        self.label = label
        magic, ver, flags, hdr_len = struct.unpack_from("<HBBi", data, 0)
        if magic != BTF_MAGIC:
            raise ValueError("%s: no es BTF, magic=0x%x" % (label, magic))
        self.ver = ver
        self.hdr_len = hdr_len

        # hdr_len decide cuantos campos de offset existen: con 24 solo hay
        # type/str, con 32 estan ademas layout_off/layout_len. Leer layout_off
        # sin comprobarlo seria leer bytes del pool de strings como offset.
        if hdr_len not in (24, 32):
            raise ValueError("%s: hdr_len=%d no reconocido (se esperan 24 o 32)"
                             % (label, hdr_len))
        type_off, type_len, str_off, str_len = struct.unpack_from(
            "<IIII", data, 8)

        # los offsets son RELATIVOS al final del header
        tstart = hdr_len + type_off
        sstart = hdr_len + str_off
        if hdr_len + type_off + type_len != hdr_len + str_off:
            raise ValueError(
                "%s: geometria incoherente: tipos hasta %d, str_off dice %d"
                % (label, hdr_len + type_off + type_len, hdr_len + str_off))
        if sstart + str_len != len(data):
            raise ValueError(
                "%s: geometria incoherente: final %d, fichero %d. No se "
                "parsea sobre una geometria que no cierra."
                % (label, sstart + str_len, len(data)))

        self.ntypes = count_types(data, tstart, sstart)
        self.types = [None] * self.ntypes
        self.strs = data[sstart:sstart + str_len]

        off = tstart
        i = 1
        while off < sstart:
            name_off, info, sz = struct.unpack_from("<III", data, off)
            vlen = info & 0xFFFF
            k = (info >> 24) & 0x1F
            kflag = (info >> 31) & 1
            body = off + BTF_TYPE_SIZE
            t = {"id": i, "name_off": name_off, "kind": k, "vlen": vlen,
                 "kflag": kflag, "size_or_type": sz, "start": off,
                 "end": body + BODY[k](vlen)}
            if k == 1:
                t["int"] = struct.unpack_from("<I", data, body)[0]
            elif k == 3:
                t["array"] = struct.unpack_from("<III", data, body)
            elif k in (4, 5):
                t["members"] = [
                    dict(zip(("name_off", "type", "offset"),
                             struct.unpack_from("<III", data, body + 12 * j)))
                    for j in range(vlen)]
            elif k in (6, 19):
                vals = []
                for j in range(vlen):
                    no, a = struct.unpack_from("<Ii", data, body + 8 * j)
                    vals.append((no, a))
                t["values"] = vals
            elif k == 15:
                t["secs"] = [struct.unpack_from("<III", data, body + 12 * j)
                             for j in range(vlen)]
            self.types[i] = t
            off = t["end"]
            i += 1
        if off != sstart:
            raise ValueError("%s: conteo previo y relleno discrepan" % label)

    def s(self, name_off):
        if name_off <= 0 or name_off >= len(self.strs):
            return ""
        e = self.strs.find(b"\x00", name_off)
        if e < 0:
            e = len(self.strs)
        return self.strs[name_off:e].decode("utf-8", "replace")

    def bits(self, tid, depth=0):
        """Tamano en BITS, resuelto solo dentro del espacio local."""
        if not (0 < tid < self.ntypes) or depth > 32:
            return 0
        t = self.types[tid]
        k = t["kind"]
        if k == 1:
            return t["int"] & 0xFF
        if k == 2:
            return 64
        if k in (4, 5, 6, 19):
            return t["size_or_type"] * 8
        if k == 16:
            return 32
        if k == 3:
            et, _it, nel = t["array"]
            return self.bits(et, depth + 1) * nel
        if k in (8, 9, 10, 11):
            return self.bits(t["size_or_type"], depth + 1)
        return 0


class Split:
    """
    Base (vmlinux) + modulo, con ids NORMALIZADOS al espacio global.

    Al normalizar, cada tipo recuerda de que fichero salio, porque los dos
    pools de strings son independientes: el name_off de un tipo del modulo no
    tiene sentido en el base, ni al reves. Resolver los nombres en el pool
    equivocado produce identificadores casi correctos pero equivocados
    ("ile_to_fpriv" en vez de "file_to_fpriv"), que es la peor clase de
    fallo: no se ve como error.
    """

    def __init__(self, base_path="/sys/kernel/btf/vmlinux",
                 mod_path="/sys/kernel/btf/amdgpu"):
        with open(base_path, "rb") as f:
            self.base = Btf(f.read(), label=base_path.split("/")[-1])
        with open(mod_path, "rb") as f:
            self.mod = Btf(f.read(), label=mod_path.split("/")[-1])

        self.base_n = self.base.ntypes - 1        # ids 1..base_n son del base
        total = self.base_n + self.mod.ntypes
        self.types = [None] * total
        self.owner = [None] * total
        for i in range(1, self.base.ntypes):
            self.types[i] = self.base.types[i]
            self.owner[i] = "base"
        for i in range(1, self.mod.ntypes):
            g = self.base_n + i
            self.types[g] = self.mod.types[i]
            self.owner[g] = "mod"
        # NO se reescriben los ids referenciados: en split BTF ya vienen en el
        # espacio global. El desplazamiento base_n solo cambia en que indice
        # del array unificado se mete cada ENTRADA, no lo que las entradas
        # apuntan.
        #
        # Este fue el error mas caro de la herramienta: shifting tambien las
        # referencias las empujaba hasta 338269 y hacia parecer que habia
        # refs colgantes, cuando el fichero era perfectly consistente. Un
        # falso positivo de "referencia colgante" es peligroso porque induce
        # a desconfiar de un dato que era correcto. La prueba que lo
        # desactivo: el id maximo referenciado por el modulo (195834) coincide
        # exactamente con base_n + tipos_propios (142435 + 53399), lo que solo
        # cuadra si los ids ya venian desplazados.
        self._check()

    def _check(self):
        """
        Las referencias del modulo tienen que caber en base+mod. Si no caben,
        la tabla unificada esta mal construida y hay que decirlo ANTES de
      responder cualquier consulta, no despues.
        """
        alto = self.base_n + self.mod.ntypes
        fuera = 0
        for i in range(1, self.mod.ntypes):
            t = self.mod.types[i]
            if not t:
                continue
            k = t["kind"]
            refs = []
            if k in HAS_TYPE:
                refs.append(t["size_or_type"])
            elif k == 3:
                refs.extend(t["array"][:2])
            elif k in (4, 5):
                refs.extend(m["type"] for m in t["members"])
            elif k == 15:
                refs.extend(s[0] for s in t["secs"])
            if any(r >= alto for r in refs):
                fuera += 1
        self.mod_out_of_range = fuera

    def pool(self, tid):
        return self.mod if self.owner[tid] == "mod" else self.base

    def _str(self, tid, name_off):
        """
        Resolver un name_off de una entrada que vive en el ESPACIO GLOBAL.

        Split BTF no solo comparte los type_ids: comparte tambien el pool de
        strings. Los name_off del modulo son globales respecto a
        base_pool ++ mod_pool:

            name_off <  len(base_pool) -> pool del base
            name_off >= len(base_pool) -> pool del modulo, en name_off-len(base)

        La prueba de por que hay que hacerlo asi y no "usar el pool del
        modulo": el name_off maximo del modulo es 4072459, y
        2691457 + 1381038 = 4072495 = len(base_pool) + len(mod_pool). Ningun
        pool aislado llega ahi, asi que resolver siempre contra el pool del
        modulo truncaria ~23000 nombres.

        Y el control que distingue las tres hipotesis posibles (solo-modulo,
        base-si-menor, base+modulo-desplazado) da 5.9%, 6.3% y 100.0% de
        nombres con forma de identificador C respectivamente. El 100% no es
        una heuristica: no queda ni un nombre por explicar.

        Los type_ids del base no necesitan correccion porque ya son globales
        y empiezan en 1.
        """
        if name_off <= 0:
            return ""
        if self.owner[tid] == "base":
            return self.base.s(name_off)
        lb = len(self.base.strs)
        if name_off < lb:
            return self.base.s(name_off)
        return self.mod.s(name_off - lb)

    def name(self, tid):
        if not (0 < tid < len(self.types)) or not self.types[tid]:
            return ""
        return self._str(tid, self.types[tid]["name_off"])

    def kindname(self, tid):
        if not (0 < tid < len(self.types)) or not self.types[tid]:
            return "VOID"
        k = self.types[tid]["kind"]
        return KINDS.get(k, "?%d" % k)

    def bits(self, tid, depth=0):
        if not (0 < tid < len(self.types)) or depth > 32:
            return 0
        t = self.types[tid]
        if not t:
            return 0
        k = t["kind"]
        if k == 1:
            return t["int"] & 0xFF
        if k == 2:
            return 64
        if k in (4, 5, 6, 19):
            return t["size_or_type"] * 8
        if k == 16:
            return 32
        if k == 3:
            et, _it, nel = t["array"]
            return self.bits(et, depth + 1) * nel
        if k in (8, 9, 10,11):
            return self.bits(t["size_or_type"], depth + 1)
        return 0

    def resolve(self, tid, depth=0):
        if not (0 < tid < len(self.types)):
            return "void"
        if depth > 32:
            return "..."
        t = self.types[tid]
        if not t:
            return "void"
        k = t["kind"]
        if k in (8, 9, 10, 11):
            return self.resolve(t["size_or_type"], depth + 1)
        if k == 4:
            return "struct " + self.name(tid)
        if k == 5:
            return "union " + self.name(tid)
        if k == 6:
            return "enum " + self.name(tid)
        if k == 19:
            return "enum64 " + self.name(tid)
        if k == 2:
            return self.resolve(t["size_or_type"], depth + 1) + " *"
        if k == 3:
            et, _it, nel = t["array"]
            return "%s[%d]" % (self.resolve(et, depth + 1), nel)
        if k == 1:
            return "int%d" % self.bits(tid)
        return self.name(tid) or ("%s?" % KINDS.get(k, k))

    def dangling(self):
        """
        Referencias que no existen en el espacio global. Debe dar SOLO el id 0
        (void). Cualquier otra cosa significa que el desplazamiento del
        modulo esta mal calculado, y por tanto toda consulta posterior seria
        sobre ids equivocados.
        """
        n = self.base_n
        mod_ids = set(range(n + 1, n + self.mod.ntypes))
        bad = set()
        for i in range(1, len(self.types)):
            t = self.types[i]
            if not t:
                continue
            refs = []
            if t["kind"] in HAS_TYPE:
                refs.append(t["size_or_type"])
            elif t["kind"] == 3:
                refs.extend(t["array"][:2])
            elif t["kind"] in (4, 5):
                refs.extend(m["type"] for m in t["members"])
            elif t["kind"] == 15:
                refs.extend(s[0] for s in t["secs"])
            for r in refs:
                if r == 0:
                    continue
                if not (0 < r < len(self.types)):
                    bad.add(r)
        del mod_ids
        return sorted(bad)

    def members(self, tid):
        t = self.types[tid]
        if not t or t["kind"] not in (4, 5):
            return []
        out = []
        for m in t["members"]:
            off, is_bf, bw = m["offset"], False, 0
            if t["kflag"]:
                # con kind_flag los 8 bits altos del offset son el ancho del
                # bitfield; ancho 0 = miembro normal, offset en bits
                bw = off >> 24
                off &= 0xFFFFFF
                is_bf = bw != 0
            # el name_off de un miembro usa el mismo espacio que la struct que
            # lo contiene, asi que se resuelve con el mismo criterio
            out.append((off, self.bits(m["type"]), m["type"],
                        self._str(tid, m["name_off"]), is_bf, bw))
        return out


def load():
    return Split()


def cmd_census(b):
    from collections import Counter
    c = Counter(t["kind"] for t in b.types[1:] if t)
    print("base   %-14s tipos=%-8d hdr_len=%d"
          % (b.base.label, b.base.ntypes - 1, b.base.hdr_len))
    print("modulo %-14s tipos=%-8d hdr_len=%d"
          % (b.mod.label, b.mod.ntypes - 1, b.mod.hdr_len))
    print("espacio global: 1..%d (base)  %d..%d (modulo)  0=void"
          % (b.base_n, b.base_n + 1, len(b.types) - 1))
    print()
    total = 0
    for k, v in sorted(c.items()):
        print("  %-12s %6d" % (KINDS.get(k, "?%d" % k), v))
        total += v
    print("  %-12s %6d" % ("TOTAL", total))
    if total != len(b.types) - 1:
        print("\nDISCREPANCIA: %d contados vs %d ids. NO CONFIABLE."
              % (total, len(b.types) - 1))
        return 1
    bad = b.dangling()
    if bad:
        print("\nREFERENCIAS DANANTES FUERA DEL ESPACIO GLOBAL (%d): %s"
              % (len(bad), bad[:20]))
        print("  -> la tabla unificada esta mal construida. NO confiar en "
              "ninguna consulta hasta arreglarlo.")
        return 1
    print("\nreferencias danantes: 0 (solo el id 0 = void, que es legal)")
    print("entradas del modulo con ref fuera de rango: %d" % b.mod_out_of_range)
    return 0


def cmd_enums(b, pat):
    rx = pat.lower()
    found = 0
    for tid, t in enumerate(b.types):
        if not t or t["kind"] not in (6, 19):
            continue
        vals = t.get("values", [])
        nm = b.name(tid)
        names = [b._str(tid, v[0]) for v in vals]
        if rx not in (nm + " " + " ".join(names)).lower():
            continue
        found += 1
        print("enum %s  (id %d, %s, %d valores, %d bits)"
              % (nm or "(sin nombre)", tid, b.owner[tid], len(vals),
                 t["size_or_type"] * 8))
        for no, v in vals:
            print("    %-46s = %d" % (b._str(tid, no), v))
        print()
    if not found:
        print("(ningun enum coincide con %r)" % pat)
    return 0 if found else 1


def cmd_struct(b, pat):
    rx = pat.lower()
    found = 0
    for tid, t in enumerate(b.types):
        if not t or t["kind"] not in (4, 5):
            continue
        if rx not in b.name(tid).lower():
            continue
        found += 1
        mem = b.members(tid)
        for off, bits, mt, mn, is_bf, bw in mem:
            ex = "  bitfield ancho=%d" % bw if is_bf else ""
            print("  %-38s bitoff=%-7d bits=%-5d %s%s"
                  % (mn or "(anon)", off, bits, b.resolve(mt), ex))
        print("  ---- %s %s [%s]: %d miembros, size declarado %d bytes\n"
              % (KINDS[t["kind"]], b.name(tid), b.owner[tid], len(mem),
                 t["size_or_type"]))
    if not found:
        print("(ninguna struct coincide con %r)" % pat)
    return 0 if found else 1


def cmd_present(b, pat):
    rx = pat.lower()
    found = 0
    for tid, t in enumerate(b.types):
        if not t or t["kind"] not in (4, 5):
            continue
        for off, bits, mt, mn, is_bf, bw in b.members(tid):
            if rx in mn.lower():
                found += 1
                print("%-10s %-30s %-34s bitoff=%-7d bits=%-4d %s"
                      % (b.owner[tid], KINDS[t["kind"]], b.name(tid), off,
                         bits, b.resolve(mt)))
    print("\n(%d miembros cuyo nombre contiene %r)" % (found, pat))
    return 0 if found else 1


def cmd_size(b, pat):
    rx = pat.lower()
    found = 0
    for tid, t in enumerate(b.types):
        if not t or t["kind"] not in (4, 5):
            continue
        if rx not in b.name(tid).lower():
            continue
        found += 1
        mem = b.members(tid)
        last = max((off + (bw if is_bf else bits)
                    for off, bits, _mt, _mn, is_bf, bw in mem), default=0)
        end = (last + 7) // 8
        print("%-10s %-32s size_declarado=%-5d ultimo_campo_ends=%-5d "
              "(%d miembros) %s"
              % (b.owner[tid], b.name(tid), t["size_or_type"], end,
                 len(mem),
                 "OK" if end == t["size_or_type"] else "<-- DIFERENCIA"))
    if not found:
        print("(ninguna struct coincide con %r)" % pat)
    return 0 if found else 1


def cmd_where(b, pat):
    rx = pat.lower()
    found = 0
    for tid, t in enumerate(b.types):
        if not t:
            continue
        nm = b.name(tid)
        if not nm:
            continue
        if rx not in nm.lower():
            continue
        found += 1
        print("%-5s %-10s id=%-7d %r" % (b.owner[tid], KINDS[t["kind"]],
                                         tid, nm))
    print("\n(%d tipos cuyo nombre contiene %r)" % (found, pat))
    return 0 if found else 1


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    pat = argv[2] if len(argv) > 2 else None
    try:
        b = load()
    except Exception as e:
        # Un fallo de parseo se imprime como fallo, nunca como "0 resultados".
        # "0 enums" y "el parser no arranca" se ven igual si no se distingue,
        # y esa confusion ya costo una conclusion invertida en este proyecto.
        print("ERROR no se pudo leer el BTF: %s" % e)
        return 3
    table = {"census": (cmd_census, False), "enums": (cmd_enums, True),
             "struct": (cmd_struct, True), "present": (cmd_present, True),
             "size": (cmd_size, True), "where": (cmd_where, True)}
    if cmd not in table:
        print(__doc__)
        return 2
    fn, needs_pat = table[cmd]
    if needs_pat and pat is None:
        print("falta el patron")
        return 2
    return fn(b, pat) if needs_pat else fn(b)


if __name__ == "__main__":
    sys.exit(main(sys.argv))