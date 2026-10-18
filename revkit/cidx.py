#!/usr/bin/env python3
# CONTRACT: name=cidx
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=indeterminado
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py, y el veredicto fue `NO_DETERMINED`.
# NO se upgraded a `WRITES_FILES=yes` porque no esta medido, y NO se dejo en
# `no` porque el codigo no lo sostiene.  La razon del NO_DETERMINED es que su unica escritura es el cache, en `/tmp/opencode/cidx.cache.pkl`, constante de modulo: resoluble pero no literal en la llamada.
#
# Poner `yes` seria MENTIR en un sentido que el validador no puede detectar, que
# es lo que el propio toolkit.py escribe de sus cinco falsos positivos: "un
# contrato en prosa no se puede comprobar con una maquina".  Poner `no` seria
# Peor: seria una afirmacion que nadie ha comprobado.
#
# TOUCHES_INTEGRATED=no: lee sysfs y ficheros.  No hace ioctl ni escribe en la
# GPU.  Ver 1487.
"""
cidx.py -- indice consultable del corpus, en vez de grep.

POR QUE EXISTE
--------------
Cada afirmacion de este proyecto exige responder "quien produce esto, quien lo
consume, quien lo llama". Hecho a mano eso es una secuencia de grep, y cada
grep tiene tres modos de fallo que ya han producido conclusiones falsas:

  1. SUBSTRING: "MTYPE_UC" casa dentro de "X86_MEMTYPE_UC". Finding: conclusion
     invertida sobre si GFX8 usa MTYPE.
  2. ALCANCE: un grep en el directorio equivocado. Finding: "gmc_v8_0.c no
     usa MTYPE" era cierto solo porque no se habia mirado gfxhub.
  3. FALSO VACIO: "grep encontro 0" con el patron mal construido se lee como
     un resultado, no como un fallo.

Este indice indexa el corpus UNA vez, con limites de palabra reales, y expone
las preguntas que el protocolo exige:

  producers/consumer/callers/callgraph   -- relacion, no solo nombre
  define                                 -- donde se define
  absent                                 -- ausencia CON ENUMERACION, que es lo
                                           unico que sostiene PROVEN_ABSENT

LIMITE QUE NO SE PUEDE SALVAR
-----------------------------
Un indice no lee semantica. Que un simbolo aparezca no significa que se use;
que no aparezca no prueba que no exista hasta haber enumerado variantes. Por
eso `absent` exige enumeraVariant y devuelve NOT_FOUND, nunca PROVEN_ABSENT,
salvo que se le pidan las variantes explicitamente.
"""
import argparse
import os
import re
import sys
from collections import defaultdict

CORPUS = "/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/working/linux-7.1.3"
AMDKG = os.path.join(CORPUS, "drivers/gpu/drm/amd/amdgpu")
REGINC = os.path.join(CORPUS, "drivers/gpu/drm/amd/include")

# Extensiones que aportan codigo real. Los .h de registro son macros, y tratarlos
# como codigo mezcla dos lenguajes: una macro y una funcion pueden llamarse
# igual y no significa nada.
CODE_EXT = (".c", ".h")


def ident_pat(nombre):
    """
    Patron de un identificador C con limites de palabra REALES.

    Un \\b en Python NO sirve con identificadores que acaban en digito o que
    contienen guiones bajos en medio: \\bAMDGPU_MTYPE\\b casa dentro de
    AMDGPU_MTYPE2. Se construye la alternancia explicita:

        (?<![A-Za-z0-9_])  NAME  (?![A-Za-z0-9_])

    que es la definicion real de "identificador completo".
    """
    return re.compile(r"(?<![A-Za-z0-9_])" + re.escape(nombre) +
                      r"(?![A-Za-z0-9_])")


CACHE = "/tmp/opencode/cidx.cache.pkl"
CACHE_VERSION = 3      # subirlo invalida el cache cuando cambia el formato


class Indice:
    def __init__(self, raiz=AMDKG, verbose=False, use_cache=True):
        self.raiz = raiz
        self.files = {}
        self.ocurr = defaultdict(list)     # simbolo -> [(fichero, linea, col)]
        self.defs = {}                     # simbolo -> [(fich, linea)]
        self.calls = defaultdict(set)      # funcion -> {llamadores}
        self.funcs = {}                    # funcion -> [(fich, linea)]
        self.macros = defaultdict(list)   # macro -> [(fich, linea)]
        self._cache_ok = False
        if use_cache and self._carga_cache():
            if verbose:
                print("cache: %d ficheros, %d simbolos"
                      % (len(self.files), len(self.ocurr)), file=sys.stderr)
            return
        self._carga(verbose)
        self._guarda_cache()

    # ---------------------------------------------------------------- cache
    def _firma(self):
        """
        Firma del corpus: (version, raiz, mtime, tamano) de cada fichero.

        Sin esto el cache miente: si un fichero cambia, hay que reindexarlo.
        Una cache sin invalidacion es peor que no tenerla, porque devuelve
        datos viejos con toda la confianza de datos nuevos.
        """
        st = []
        for p in self._ficheros():
            try:
                s = os.stat(p)
                st.append((os.path.relpath(p, self.raiz),
                           int(s.st_mtime), s.st_size))
            except OSError:
                pass
        return (CACHE_VERSION, self.raiz, tuple(sorted(st)))

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
        self.files = d["files"]
        self.ocurr = defaultdict(list, d["ocurr"])
        self.defs = d["defs"]
        self.calls = defaultdict(set, d["calls"])
        self.funcs = d["funcs"]
        self.macros = defaultdict(list, d["macros"])
        self._cache_ok = True
        return True

    def _guarda_cache(self):
        import pickle
        try:
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            with open(CACHE, "wb") as f:
                pickle.dump({
                    "firma": self._firma(), "files": self.files,
                    "ocurr": dict(self.ocurr), "defs": self.defs,
                    "calls": dict(self.calls), "funcs": self.funcs,
                    "macros": dict(self.macros),
                }, f, protocol=4)
        except Exception as e:
            print("aviso: no se pudo guardar el cache: %s" % e,
                  file=sys.stderr)
        self._cache_ok = True

    # ---------------------------------------------------------------- carga
    def _ficheros(self):
        for base, _d, fs in os.walk(self.raiz):
            for f in sorted(fs):
                if f.endswith(CODE_EXT):
                    yield os.path.join(base, f)

    def _carga(self, verbose):
        n = 0
        for path in self._ficheros():
            rel = os.path.relpath(path, self.raiz)
            try:
                txt = open(path, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            self.files[rel] = txt
            n += 1
            self._indexa_txt(rel, txt)
        if verbose:
            print("indexados %d ficheros, %d simbolos distintos"
                  % (n, len(self.ocurr)), file=sys.stderr)

    def _indexa_txt(self, rel, txt):
        # 1. macros: lineas #define NOMBRE
        for i, ln in enumerate(txt.splitlines(), 1):
            m = re.match(r"\s*#\s*define\s+([A-Za-z_]\w*)", ln)
            if m:
                self.macros[m.group(1)].append((rel, i))

        # 2. definiciones de funcion al inicio de linea
        for m in re.finditer(
                r"^(?:static\s+|extern\s+|inline\s+)*"
                r"(?:void|int|u\w+|s\w+|uint\w+|int\w+|bool|char|long|"
                r"short|float|double|size_t|struct\s+\w+|union\s+\w+|"
                r"enum\s+\w+)\s+\*?\s*"
                r"([a-z_]\w*)\s*\(", txt, re.M):
            self.funcs.setdefault(m.group(1), []).append(
                (rel, txt[:m.start()].count("\n") + 1))
            self.defs.setdefault(m.group(1), []).append(
                (rel, txt[:m.start()].count("\n") + 1))

        # 3. llamadas: identificador seguido de (
        #    Se indexa TODO identificador seguido de parentesis, que es como
        #    se comporta el C: una macro tambien se "llama" asi.
        for m in re.finditer(r"(?<![A-Za-z0-9_])([A-Za-z_]\w*)\s*\(", txt):
            nombre = m.group(1)
            linea = txt[:m.start()].count("\n") + 1
            self.ocurr[nombre].append((rel, linea))
            self.calls[nombre].add(rel)

    # ------------------------------------------------------------- consultas
    def buscar(self, simbolo):
        """ficheros y lineas donde aparece, con limites de palabra"""
        rx = ident_pat(simbolo)
        out = []
        for rel, txt in self.files.items():
            for i, ln in enumerate(txt.splitlines(), 1):
                if rx.search(ln):
                    out.append((rel, i, ln.strip()[:120]))
        return out

    def consumidores(self, simbolo, excluir_def=True):
        """ficheros que USA el simbolo (aparecen como llamada o macro)"""
        rx = ident_pat(simbolo)
        out = {}
        for rel, txt in self.files.items():
            for i, ln in enumerate(txt.splitlines(), 1):
                if rx.search(ln):
                    if excluir_def and re.match(
                            r"\s*(?:static\s+)?\w[\w\s\*]*\s+%s\s*\(" % re.escape(simbolo),
                            ln):
                        continue
                    out.setdefault(rel, []).append((i, ln.strip()[:120]))
        return out

    def define(self, simbolo):
        return self.defs.get(simbolo, [])

    def callers(self, funcion):
        """ficheros que la llaman"""
        rx = ident_pat(funcion)
        out = set()
        for rel, txt in self.files.items():
            if re.match(r"\s*(?:static\s+)?\w[\w\s\*]*\s+%s\s*\("
                        % re.escape(funcion), txt.split("\n")[0] or ""):
                pass
            for i, ln in enumerate(txt.splitlines(), 1):
                if not rx.search(ln):
                    continue
                if re.match(r"\s*(?:static\s+)?\w[\w\s\*]*\s+%s\s*\("
                            % re.escape(funcion), ln):
                    continue          # es la definicion, no una llamada
                out.add(rel)
        return sorted(out)

    def ausente_en(self, simbolo, subset=None):
        """
        Enumeracion de Ausencia.

        Devuelve (ficheros_que_lo_usan, ficheros_ revisados). Devuelve
        NOT_FOUND cuando nadie lo usa: eso NO es PROVEN_ABSENT, porque no se
        han mirado variantes ni otros arboles. Para ascender a PROVEN_ABSENT
        hay que pasar las variantes, y el comando lo dice.
        """
        usados = list(self.consumidores(simbolo).keys())
        revisados = list(self.files.keys()) if subset is None else subset
        return usados, sorted(revisados)


def main():
    ap = argparse.ArgumentParser(
        description="indice del corpus con limites de palabra reales")
    ap.add_argument("cmd", choices=[
        "find", "use", "def", "callers", "absent", "stats", "funcs",
        "macro", "vtable", "cadena"])
    ap.add_argument("simbolo", nargs="?", default=None)
    ap.add_argument("--raiz", default=AMDKG)
    ap.add_argument("-n", type=int, default=40, help="maximo de lineas")
    a = ap.parse_args()

    idx = Indice(a.raiz, verbose=True)

    if a.cmd == "stats":
        print("ficheros indexados : %d" % len(idx.files))
        print("simbolos indexados : %d" % len(idx.ocurr))
        print("funciones definidas: %d" % len(idx.funcs))
        print("macros #define     : %d" % len(idx.macros))
        return 0

    if not a.simbolo:
        print("falta el simbolo")
        return 2

    # AVISO ANTES DE BUSCAR NADA.
    #
    # El indice busca con limites de palabra reales, asi que un FRAGMENTO
    # ("MTYPE") no casa nunca aunque el fichero lo contenga: solo casa con el
    # identificador completo ("AMDGPU_VM_MTYPE_MASK"). Sin este aviso, eso
    # devuelve "0 ocurrencias" con aspecto de resultado, y es el mismo fallo
    # que hizo que un grep de este proyecto produjera conclusiones
    # invertidas. Se comprueba ANTES de dar cualquier numero.
    frag_ok = ident_pat(a.simbolo)
    hay_prefijo = []
    for cand in list(idx.ocurr):
        if cand != a.simbolo and a.simbolo in cand:
            hay_prefijo.append(cand)
    if not idx.ocurr.get(a.simbolo) and hay_prefijo:
        print("AVISO: %r no es un identificador completo del indice."
              % a.simbolo)
        print("       Simbolos que CONTIENEN ese texto: %s"
              % ", ".join(sorted(hay_prefijo)[:8]))
        print("       Un 0 aqui NO significa ausencia: significa que el")
        print("       nombre buscado no es el del simbolo.")
        print("       Usa el nombre completo en cada uno:")
        for c in sorted(hay_prefijo)[:12]:
            us = sorted(idx.consumidores(c))
            print("         %-42s %d fichero(s)" % (c, len(us)))
        return 1
    del frag_ok

    if a.cmd == "find":
        for rel, i, ln in idx.buscar(a.simbolo)[:a.n]:
            print("%s:%d: %s" % (rel, i, ln))
        tot = len(idx.buscar(a.simbolo))
        print("--- %d ocurrencias en %d ficheros" %
              (tot, len({r for r, _, _ in idx.buscar(a.simbolo)})))
        return 0 if tot else 1

    if a.cmd == "use":
        c = idx.consumidores(a.simbolo)
        for rel in sorted(c)[:a.n]:
            for i, ln in c[rel][:3]:
                print("%s:%d: %s" % (rel, i, ln))
        print("--- %d ficheros lo usan" % len(c))
        return 0 if c else 1

    if a.cmd == "def":
        d = idx.define(a.simbolo)
        for rel, i in d[:a.n]:
            print("%s:%d" % (rel, i))
        print("--- %d definiciones" % len(d))
        return 0 if d else 1

    if a.cmd == "callers":
        for f in idx.callers(a.simbolo)[:a.n]:
            print(f)
        tot = len(idx.callers(a.simbolo))
        print("--- %d ficheros la llaman" % tot)
        return 0 if tot else 1

    if a.cmd == "absent":
        usados, revisados = idx.ausente_en(a.simbolo)
        print("revisados: %d ficheros" % len(revisados))
        if usados:
            print("AUSENTE = False, lo usan:")
            for u in usados[:a.n]:
                print("   %s" % u)
            return 0
        print("NOT_FOUND en este ambito (%s)" % os.path.basename(a.raiz))
        print("NO es PROVEN_ABSENT: faltan variantes, otros arboles y las")
        print("cabeceras de registro. Usa --raiz para ampliar el ambito.")
        return 1

    if a.cmd == "funcs":
        for f in sorted(idx.funcs)[:a.n]:
            d = idx.funcs[f][0]
            print("%-44s %s:%d" % (f, d[0], d[1]))
        print("--- %d funciones" % len(idx.funcs))
        return 0

    if a.cmd == "macro":
        """
        Resuelve una macro y de que clase es.

        Hace falta porque buena parte del despacho de amdgpu son MACROS que
       -expanden a un acceso por vtable:

            #define amdgpu_gmc_emit_flush_gpu_tlb(r, vmid, addr) \\
                (r)->adev->gmc.gmc_funcs->emit_flush_gpu_tlb(...)

        Buscar esa macro con 'def' devuelve 0 Definitions, y ese 0 parece
        una ausencia cuando lo que pasa es que no hay funcion: hay una macro
        que despacha a una vtable. Es el mismo fallo de "0 que parece
        resultado", aqui por otra via.
        """
        loc = idx.macros.get(a.simbolo, [])
        if not loc:
            cand = [m for m in idx.macros if a.simbolo in m]
            print("no hay macro %r" % a.simbolo)
            if cand:
                print("macros que contienen ese texto: %s"
                      % ", ".join(sorted(cand)[:10]))
            return 1
        for rel, i in loc[:a.n]:
            txt = idx.files[rel].splitlines()[i - 1]
            print("%s:%d" % (rel, i))
            print("   %s" % txt.strip()[:150])
            # la macro despacha a vtable?
            if "->" in txt and "(" in txt:
                print("   -> parece DESPACHO por puntero de funcion")
                for m in re.finditer(r"->(\w+)\s*\(", txt):
                    print("      campo: %s" % m.group(1))
        print("--- %d definiciones de la macro" % len(loc))
        return 0

    if a.cmd == "vtable":
        """
        Quien ASIGNA un campo de vtable, y con que funcion.

        Cierra el otro extremo de una macro de despacho: la macro llama a
        gmc_funcs->X, y aqui se ve que gmc_vX_0.c asigna X = una funcion.
        """
        rx = re.compile(r"\.%s\s*=\s*(\w+)" % re.escape(a.simbolo))
        for rel, txt in idx.files.items():
            for i, ln in enumerate(txt.splitlines(), 1):
                m = rx.search(ln)
                if not m:
                    continue
                destino = m.group(1)
                d = idx.define(destino)
                print("%s:%d" % (rel, i))
                print("   %s" % ln.strip()[:120])
                if d:
                    print("   -> %s definida en %s:%d"
                          % (destino, d[0][0], d[0][1]))
                    cs = idx.callers(destino)
                    if cs:
                        print("   -> la llaman: %s" % ", ".join(cs[:6]))
                else:
                    print("   -> %s NO aparece definida (macro? "
                          "externa?)" % destino)
        return 0

    if a.cmd == "cadena":
        """
        Cadena de despacho completa: macro -> vtable -> funcion -> callers.

        Es la pregunta que hace el protocolo: "cual es la relacion que
        deberia existir". Para una macro de despacho, la relacion pasa por la
        vtable del ASIC, y ninguna de las tres consultas sueltas la ve entera.
        """
        loc = idx.macros.get(a.simbolo, [])
        if not loc:
            print("%r no es una macro" % a.simbolo)
            return 1
        rel, i = loc[0]
        txt = idx.files[rel].splitlines()[i - 1]
        print("1. macro %s" % a.simbolo)
        print("   %s:%d" % (rel, i))
        print("   %s" % txt.strip()[:150])
        campos = re.findall(r"->(\w+)\s*\(", txt)
        if not campos:
            print("   no es un despacho por puntero de funcion")
            return 1
        for campo in campos:
            print()
            print("2. campo de vtable: %s" % campo)
            rx = re.compile(r"\.%s\s*=\s*(\w+)" % re.escape(campo))
            asignaciones = []
            for r2, t2 in idx.files.items():
                for i2, l2 in enumerate(t2.splitlines(), 1):
                    m = rx.search(l2)
                    if m:
                        asignaciones.append((r2, i2, m.group(1)))
            # la asignacion que corresponde a NUESTRO ASIC
            objetivo = None
            for r2, i2, destino in asignaciones:
                print("   %-40s -> %s" % (r2, destino))
                # la asignacion que corresponde a NUESTRO ASIC
                if objetivo is None and "v8" in r2:
                    objetivo = (r2, i2, destino)
            if not objetivo:
                objetivo = asignaciones[0] if asignaciones else None
            if objetivo:
                r2, i2, destino = objetivo
                print("   para GFX8: %s:%d -> %s" % (r2, i2, destino))
                d = idx.define(destino)
                if d:
                    print()
                    print("3. implementacion: %s:%d" % (d[0][0], d[0][1]))
                    cs = idx.callers(destino)
                    if cs:
                        print("   la llaman: %s" % ", ".join(cs[:8]))
                    else:
                        print("   NINGUN fichero la llama directamente "
                              "(puede ir por puntero a funcion)")
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())