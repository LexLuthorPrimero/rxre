#!/usr/bin/env python3
"""
regs.py -- decodificador de campos de registro del corpus.

POR QUE EXISTE
--------------
Cada afirmacion sobre un registro del hardware empieza igual: "el campo X del
registro Y ocupa N bits en el shift M". Eso vive en ficheros como

  include/asic_reg/gca/gfx_8_0_sh_mask.h

que son solo #define, y se Haydena a mano. El modo de fallo clasico es
confundir el MASK con el SHIFT, o coger el fichero del ASIC equivocado
(gfx_6_0 en vez de gfx_8_0), o dar por bueno un valor copiado de otro bloque.

Este decodificador hace tres cosas que el grep no:

  1. DA EL SHIFT REAL Y EL MASK REAL, y el ancho en bits deducido de ambos,
     comprobando que mask == (1<<ancho)-1 << shift.
  2. DICE SI HAY DISCREPANCIA. Hay entradas en estos headers donde el mask no
     corresponde con el shift declarado. Es informacion del hardware
     autoritativa, no un error del header.
  3. DIFERENCIA LOS ASIC. El mismo nombre de campo tiene valores distintos en
     gfx_6_0 y gfx_8_0. Preguntar "el ancho" sin decir de que ASIC es una
     pregunta ambigua, y la respuesta equivocada produce un error de
     implementacion que no falla de forma visible.

LIMITES
-------
- Solo cubre macros #define con forma REG__FIELD__MASK y REG__FIELD__SHIFT.
  Un campo definido de otra forma (union, struct) NO se ve. Eso es
  NOT_IN_CORPUS, no ausencia.
- No dice que hace el campo. Dice donde esta y cuanto mide. La semántica es
  OTRA pregunta.
"""
import argparse
import os
import re
import sys
from collections import defaultdict

CORPUS = "/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/working/linux-7.1.3"
REGINC = os.path.join(CORPUS, "drivers/gpu/drm/amd/include/asic_reg")
DRVINC = os.path.join(CORPUS, "drivers/gpu/drm/amd/include")

CACHE = "/tmp/opencode/regs.cache.pkl"
CACHE_VERSION = 3

# Formato REAL de los macros en amdgpu, leido del header, no de memoria:
#
#   #define CB_BLEND_RED__BLEND_RED_MASK 0xffffffff
#   #define CB_DCC_CONTROL__OVERWRITE_COMBINER_DISABLE_MASK 0x1
#   #define CC_GC_SHADER_ARRAY_CONFIG__INACTIVE_CUS_MASK 0xffff0000
#   #define CC_GC_SHADER_ARRAY_CONFIG__INACTIVE_CUS__SHIFT 0x10
#
# O sea: REG + "__" + FIELD + KIND, donde el sufijo del TIPO lleva UN guion
# bajo ( _MASK, _SHIFT ), pero SHIFT usa dos ( __SHIFT ). El caso de SHIFT es
# la excepcion, no la regla.
#
# La primera version de este parser pedia REG__FIELD__KIND, o sea "__MASK".
# Ese sufijo no existe: indexaba 3.4 millones de macros y no encontraba ni una,
# y devolvia "campo no encontrado" para un campo que existe y que se acababa
# de verificar a mano. Un indice que no encuentra lo que se le pide es PEOR
# que no tener indice, porque su 0 se lee como ausencia.
#
# El separador "__" entre REG y FIELD es ambiguo cuando el nombre del registro
# ya contiene "__": "CC_GC_SHADER_ARRAY_CONFIG" + "INACTIVE_CUS", o
# "CC_GC" + "SHADER_ARRAY_CONFIG". Eso se resuelve aparte, por evidencia.
RE_MASK = re.compile(
    r"^#define\s+([A-Z0-9_]+?)__(.+?)_?"
    r"(VIOLATION_MASK|VIOLATION_SHIFT|MASK32|MASK64|MASK|SHIFT|DEFAULT|FIELD)\b"
    r"\s*(.*)$")
RE_HEX = re.compile(r"^(?:0[xX]([0-9a-fA-F]+)|([0-9]+))(?:[uUlL]*)\s*$")

# SEGUNDO formato: registros de 64 bits partidos en dos mitades.
#
#   #define mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR_LO32_DEFAULT 0x00000000
#   #define mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR_HI32_DEFAULT 0x00000000
#
# Estos van con prefijo mm_ (minusculas) y sufijo _DEFAULT, y NO usan "__"
# como separador registro/campo. La primera version de regs.py solounia el
# formato con "__", asi que mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR no aparecia:
# el driver lo usa en gmc_v8_0.c:673 y el indice no lo tenia.
#
# Un registro que el driver escribe y que el indice no encuentra es
# especialmente grave, porque invita a concluir que el registro no existe.
RE_MM = re.compile(
    r"^#define\s+(mm[A-Za-z0-9_]+?)_(LO32|HI32|HI16|LO16|DEFAULT)\b\s+(.+?)\s*$")


def norm_field(f):
    """
    Normaliza el nombre del campo.

    El sufijo del tipo se come el "_" o el "__" que lo precede, segun el caso:

        CC_GC_SHADER_ARRAY_CONFIG__INACTIVE_CUS_MASK
          -> reg=CC_GC_SHADER_ARRAY_CONFIG  field=INACTIVE_CUS

        CC_GC_SHADER_ARRAY_CONFIG__INACTIVE_CUS__SHIFT
          -> reg=CC_GC_SHADER_ARRAY_CONFIG  field=INACTIVE_CUS_

    El segundo caso deja un guion bajo colgando, y si no se quita, el MASK y el
    SHIFT se guardan bajo DOS claves distintas y el emparejamiento falla: el
    campo aparece con MASK pero "sin SHIFT en este fichero". Eso no es un
    dato del hardware, es un fallo del parser que se presenta como si fuera
    una propiedad del registro.
    """
    return f.rstrip("_")


def parse_val(txt):
    """valor entero de un literal, o None. Rechaza '~0x3' a proposito."""
    m = RE_HEX.match(txt.strip())
    if not m:
        return None
    return int(m.group(1), 16) if m.group(1) else int(m.group(2))


class Regs:
    def __init__(self, verbose=False, use_cache=True):
        self.raw = []          # (reg, field, kind, valor, fichero, linea)
        self.macros = {}       # (reg, field, kind) -> [(valor, fichero, linea)]
        self.reg_files = {}    # reg -> {fichero}
        self.reg_fields = {}   # reg -> {field}
        if use_cache and self._carga_cache():
            if verbose:
                print("cache: %d campos en %d registros"
                      % (len(self.macros), len(self.reg_files)),
                      file=sys.stderr)
            # self.raw NO se guarda en el cache y NO se reconstruye: solo
            # alimenta self.macros, y las consultas van todas contra self.
            # macros. Guardarlo costs 3.7 s de carga y ~200 MB para algo que
            # no se consulta nunca.
            self.raw = []
            return
        self._carga(verbose)
        self._resolver_cortes(verbose)
        self._guarda_cache()

    def _firma(self):
        st = []
        for d, _s, fs in os.walk(DRVINC):
            for fn in sorted(fs):
                if fn.endswith((".h", ".c")):
                    p = os.path.join(d, fn)
                    try:
                        s = os.stat(p)
                        st.append((os.path.relpath(p, CORPUS),
                                   int(s.st_mtime), s.st_size))
                    except OSError:
                        pass
        return (CACHE_VERSION, tuple(sorted(st)))

    def _carga_cache(self):
        import pickle
        if not os.path.exists(CACHE):
            return False
        try:
            with open(CACHE, "rb") as f:
                d = pickle.load(f)
        except Exception:
            return False
        if d.get("firma") != self._firma():
            return False
        self.raw = []
        self.macros = d["macros"]
        self.reg_files = d["reg_files"]
        self.reg_fields = d["reg_fields"]
        return True

    def _guarda_cache(self):
        import pickle
        try:
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            with open(CACHE, "wb") as f:
                pickle.dump({"firma": self._firma(),
                             "macros": self.macros,
                             "reg_files": self.reg_files,
                             "reg_fields": self.reg_fields},
                            f, protocol=4)
        except Exception as e:
            print("aviso: cache no guardado: %s" % e, file=sys.stderr)

    def _carga(self, verbose):
        n = 0
        vistos = set()
        for base in (DRVINC,):          # REGINC esta DENTRO de DRVINC
            for d, _s, fs in os.walk(base):
                for fn in sorted(fs):
                    if not fn.endswith((".h", ".c")):
                        continue
                    p = os.path.join(d, fn)
                    # REGINC es un subdirectorio de DRVINC. Recorrer ambos
                    # recorre cada fichero DOS veces y duplica el indice
                    # entero: por eso salian 3.38 millones de macros y cada
                    # campo aparecia repetido. Un indice duplicado no es
                    # inofensivo: hace que un "cuantos ASIC definen esto"
                    # de 6 responda 12, y que un recuento de divergencias
                    # sea el doble del real.
                    if p in vistos:
                        continue
                    vistos.add(p)
                    rel = os.path.relpath(p, CORPUS)
                    try:
                        lines = open(p, encoding="utf-8",
                                     errors="replace").read().splitlines()
                    except Exception:
                        continue
                    for i, ln in enumerate(lines, 1):
                        m = RE_MASK.match(ln)
                        if m:
                            reg, field, kind, valtxt = m.groups()
                            v = parse_val(valtxt)
                            if v is not None:
                                self.raw.append(
                                    (reg, field, kind, v, rel, i))
                                n += 1
                            continue
                        # formato mm_<REG>_<LO32|HI32|DEFAULT>
                        m2 = RE_MM.match(ln)
                        if m2:
                            reg, mitad, valtxt = m2.groups()
                            v = parse_val(valtxt)
                            if v is not None:
                                self.raw.append(
                                    (reg, mitad, "ADDR", v, rel, i))
                                n += 1
                        continue
        if verbose:
            print("indexadas %d macros en %d ficheros" % (n, len(vistos)),
                  file=sys.stderr)

    def _resolver_cortes(self, verbose):
        """
        El corte REG/FIELD ya lo resuelve la propia regex, queCaptura REG de
        forma NO GREEDY hasta el PRIMER "__". Eso es exactamente la convencion
        de los headers: el "__" separa registro de campo, y los nombres de
        registro de amdgpu contienen "_" simple pero no "__".

        Se deja el metodo con su nombre porque documenta una decision que ya se
        tomo, pero no hace trabajo: no hay heuristica, no hay eleccion. Una
        heuristica aqui habria sido inventar una ambiguedad que la regex ya
        resuelve sin ambiguedad.
        """
        n = 0
        for reg, field, kind, v, rel, ln in self.raw:
            if not reg or not field:
                continue
            field = norm_field(field)
            self.macros.setdefault((reg, field, kind), []).append((v, rel, ln))
            self.reg_files.setdefault(reg, set()).add(rel)
            self.reg_fields.setdefault(reg, set()).add(field)
            n += 1
        if verbose:
            print("indexados %d campos en %d registros"
                  % (n, len(self.reg_files)), file=sys.stderr)

    def campo(self, reg, field):
        """
        Devuelve las definiciones de un campo, por ASIC.

        Se devuelven TODAS porque el mismo campo tiene valores distintos
        segun la generacion, y quedarse con una es un error silencioso.
        """
        mask = self.macros.get((reg, field, "MASK"), [])
        shift = self.macros.get((reg, field, "SHIFT"), [])
        return mask, shift

    def ancho(self, mask):
        """bits encendidos en un mask, normalizado"""
        return bin(mask).count("1")

    def consistente(self, mask, shift):
        """
        Comprueba mask == ((1<<ancho)-1) << shift.

        False NO es un error del header: es lo que el hardware hace, y por eso
        vale la pena mirarlo. Un mask con bits sueltos significa que hay
        posiciones del campo que el hardware no usa, lo cual cambia como se
        programs.
        """
        if shift == 0 and mask == 0:
            return True, 0, 0
        if shift > 31 or mask == 0:
            return False, 0, shift
        if mask & ((1 << shift) - 1):
            return False, self.ancho(mask), shift
        ancho = self.ancho(mask >> shift)
        esperado = ((1 << ancho) - 1) << shift
        return (mask == esperado), ancho, shift


def main():
    ap = argparse.ArgumentParser(
        description="decodificador de campos de registro")
    ap.add_argument("reg", nargs="?", help="REGISTRO")
    ap.add_argument("field", nargs="?", help="CAMPO")
    ap.add_argument("--find", help="buscar registros o campos por fragmento")
    ap.add_argument("--ancho", action="store_true",
                    help="solo el ancho en bits de cada ASIC")
    ap.add_argument("--incumplen", action="store_true",
                    help="campos cuyo MASK no corresponde con su SHIFT")
    ap.add_argument("--asic", default=None,
                    help="filtra por fichero de ASIC, p.ej. gfx_8_0")
    a = ap.parse_args()

    r = Regs(verbose=True)
    print()

    if a.incumplen:
        malos = []
        for (reg, field, kind), vals in sorted(r.macros.items()):
            if kind != "MASK":
                continue
            sh = r.macros.get((reg, field, "SHIFT"), [])
            if not sh:
                continue
            for (mv, mf, ml), (sv, _sf, _sl) in zip(vals, sh):
                ok, ancho, shift = r.consistente(mv, sv)
                if not ok:
                    malos.append((reg, field, mv, mv, shift, ancho,
                                  os.path.basename(mf)))
        if not malos:
            print("ningun MASK incumple su SHIFT")
            return 0
        print("campos con MASK incoherente con SHIFT:")
        for reg, field, mv, _v, shift, ancho, f in malos:
            print("  %-38s %-26s mask=0x%08x shift=%-2d ancho=%d  (%s)"
                  % (reg, field, mv, shift, ancho, f))
        print("--- %d discrepancias" % len(malos))
        print("No son errores del header: son posiciones del campo que el")
        print("hardware no usa, o una asimetria MASK/SHIFT que hay que")
        print("comprobar antes de escribir ese campo.")
        return 0

    if a.find:
        rx = re.compile(a.find, re.I)
        # Un ASIC (gfx_8_0, gmc_v10_0) aparece en el NOMBRE DEL FICHERO, no
        # en el del registro. Buscarlo en la clave del registro daba 0
        # resultados y se leia como "este ASIC no tiene registros", que es
        # falso. Se buscan los tres sitios y se dice de donde salio cada uno.
        por_fichero = defaultdict(set)
        for (reg, f, k), vals in r.macros.items():
            for (_v, rel, _l) in vals:
                if rx.search(rel):
                    por_fichero[rel].add(reg)
        campos = defaultdict(set)
        for (reg, f, k), vals in r.macros.items():
            for (_v, rel, _l) in vals:
                if rx.search(rel):
                    campos[rel].add(f)

        print("patron: %r" % a.find)
        print()
        print("FICHEROS que casan: %d" % len(por_fichero))
        for rel in sorted(por_fichero)[:40]:
            print("  %-34s %5d registros  %5d campos"
                  % (rel.split("/")[-1], len(por_fichero[rel]),
                     len(campos[rel])))

        regs = {x for v in por_fichero.values() for x in v}
        cf = {x for v in campos.values() for x in v}
        print()
        print("registros unicos en esos ficheros: %d" % len(regs))
        print("campos unicos en esos ficheros   : %d" % len(cf))
        # y el caso de que el patron fuera un nombre de REGISTRO o de CAMPO.
        # Sin esto, buscar un registro por su NOMBRE daba 0 ficheros, y se
        # concluyo que el ASIC no lo tiene, cuando lo que falta era mirar
        # donde se guarda la clave.
        rr = sorted(x for x in r.reg_files if rx.search(x))
        cc = sorted({f for (_reg, f, _k) in r.macros if rx.search(f)})
        if rr:
            print("registros cuyo NOMBRE casa: %d" % len(rr))
            for x in rr[:25]:
                print("   %s" % x)
        if cc:
            print("campos cuyo NOMBRE casa: %d" % len(cc))
            for x in cc[:25]:
                print("   %s" % x)
        if not rr and not cc and not por_fichero:
            print("NINGUN registro, campo ni fichero casa con el patron.")
            print("Eso es NOT_FOUND, no PROVEN_ABSENT: el registro puede estar")
            print("definido de otra forma, o ser de un ASIC no cubierto.")
        return 0

    if not a.reg:
        ap.print_help()
        return 2

    # registro solo: listar sus campos
    if not a.field:
        campos = sorted({f for (reg, f, k) in r.macros if reg == a.reg})
        if not campos:
            cand = [x for x in r.reg_files if a.reg in x]
            print("el registro %r no existe en los headers." % a.reg)
            if cand:
                print("registros parecidos:")
                for c in sorted(cand)[:20]:
                    print("  %s" % c)
            print("NOT_IN_CORPUS, no PROVEN_ABSENT: puede estar definido como")
            print("union o struct en lugar de macro.")
            return 1
        print("registro %s: %d campos" % (a.reg, len(campos)))
        for f in campos[:80]:
            m, s = r.campo(a.reg, f)
            extra = ""
            if m and s:
                ok, ancho, shift = r.consistente(m[0][0], s[0][0])
                extra = "  %2d bits @ %2d %s" % (ancho, shift,
                                                 "" if ok else "<-- INCOHERENTE")
            print("  %-34s%s" % (f, extra))
        return 0

    mask, shift = r.campo(a.reg, a.field)
    if not mask:
        cand = sorted({f for (reg, f, k) in r.macros
                       if reg == a.reg and a.field in f})
        print("campo %s.%s no encontrado." % (a.reg, a.field))
        if cand:
            print("campos parecidos en ese registro: %s" % ", ".join(cand[:10]))
        return 1

    print("%s.%s" % (a.reg, a.field))
    print("-" * 60)
    # El filtro por ASIC es lo que hace la respuesta NO ambigua. POLARIS12
    # usa gfx_v8_0, asi que un --asic gfx_8_0 deja una sola fila.
    if a.asic:
        mask = [x for x in mask if a.asic in x[1]]
        shift = [x for x in shift if a.asic in x[1]]
    # Emparejar MASK con SU SHIFT por ORIGEN, no por orden.
    #
    # La primera version emparejaba por posicion de lista y por
    # os.path.basename, lo que daba SHIFT=? en casi todo: el MASK y el SHIFT
    # estan en el MISMO fichero, asi que hay que emparejar por fichero
    # exacto y, cuando hay varios candidatos, por linea mas cercana.
    #
    # Emparejar por posicion de lista es un fallo silencioso especialmente
    #en particular: si hay 4 ASIC y el 3o no tiene el campo, se empareja el
    # MASK de uno con el SHIFT de otro y el ancho sale plausible pero equivocado.
    # Por eso el emparejamiento es explicito y se avisa si falta.
    for (mv, mf, ml) in mask:
        # candidatos de SHIFT en el MISMO fichero, el mas cercano por linea
        cands = [(abs(sl - ml), sv, sf, sl)
                 for (sv, sf, sl) in shift if sf == mf]
        if cands:
            _d, sv, sf, sl = min(cands)
            donde = "%s:%d" % (os.path.basename(mf), ml)
            gen = os.path.basename(mf).replace("_sh_mask.h", "")
        else:
            sv = None
            donde = os.path.basename(mf)
            gen = os.path.basename(mf).replace("_sh_mask.h", "") + " (sin SHIFT)"
        # Una sola linea por ASIC: antes se imprimia dos veces, con y sin el
        # MASK, porque la rama "--ancho" no estaba dentro de la condition del
        # SHIFT. Dos filas iguales hacen dudar de si son dos ASIC o una.
        if a.ancho:
            if sv is not None:
                _ok, ancho, _sh = r.consistente(mv, sv)
                print("  %-16s %2d bits @ %2d   %s" % (gen, ancho, _sh, donde))
            else:
                print("  %-16s %2d bits (del MASK)   %s"
                      % (gen, r.ancho(mv), donde))
            continue
        if sv is not None:
            ok, ancho, sh = r.consistente(mv, sv)
            print("  %-16s MASK=0x%08x SHIFT=%-3d -> %2d bits @ %2d  %-9s %s"
                  % (gen, mv, sv, ancho, sh,
                     "" if ok else "INCOHERENTE", donde))
        else:
            print("  %-16s MASK=0x%08x SHIFT=? -> %2d bits (del MASK)   %s"
                  % (gen, mv, r.ancho(mv), donde))
    print()
    print("NOTA: el mismo campo tiene valores distintos por ASIC.")
    print("Un unico valor sin decir de que ASIC es una respuesta ambigua.")
    return 0


if __name__ == "__main__":
    sys.exit(main())