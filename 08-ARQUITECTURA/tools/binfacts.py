#!/usr/bin/env python3
# CONTRACT: name=binfacts
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=yes
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
r"""BINFACTS -- el binario real del modulo cargado, medido.

POR QUE EXISTE. Todo el proyecto mide un CORPUS: una copia del arbol de fuentes
en RESEARCH/working/linux-7.1.3/. Y todo el proyecto asume que ese corpus
describe el driver que esta corriendo.

Esa asuncion **nunca se ha verificado contra el binario cargado**. Se puede, y
no requiere escribir nada:

  /lib/modules/$(uname -r)/.../amdgpu.ko.zst   presente
  modinfo -F srcversion amdgpu                 D68004925455E20A24C2B87
  .BTF  presente    .symtab presente

Medido el 2026-10-01: el srcversion del .ko del arbol de la distro coincide con
el del modulo cargado. Eso es un eslabon, no la cadena entera: srcversion es un
hash del codigo, no de la configuracion de compilacion ni de las macros
externas.

Lo que esta herramienta hace es MEJORAR ESO: extraer del binario los hechos
estructurales y cruzarlos contra el corpus:

  1. ¿El binario tiene un simbolo que el corpus define?
  2. ¿La lista de cadenas coincide?  (modprobe_table, nombres de cola, banners)
  3. ¿Las struct de BTF coinciden en tamaño y campos con las del corpus?

Y contesta la pregunta al reves, que es la que importa: **¿hay algo
en el binario que NO este en el corpus?** Eso es lo que delata un corpus
desactualizado, y es la direction en la que no se ha mirado nunca.

Uso:
  python3 binfacts.py                resumen
  python3 binfacts.py --symbols      simbolos del binario vs el corpus
  python3 binfacts.py --strings      cadenas
  python3 binfacts.py --btf          structs desde BTF
  python3 binfacts.py --in-corpus    lo que el binario tiene y el corpus no
  python3 binfacts.py --json
"""
import gzip
import lzma
import os
import re
import subprocess
import sys
import shutil
import tempfile
from collections import Counter

KVER = os.uname().release
AMD = ("/home/lucas/Escritorio/RX550-INVESTIGACION/"
       "RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd")
CORPUS_SRC = f"{AMD}/amdgpu"
CORPUS_INC = f"{AMD}/include"


def find_ko():
    for dp, _d, files in os.walk(f"/lib/modules/{KVER}"):
        for f in files:
            if f.startswith("amdgpu.ko"):
                return os.path.join(dp, f)
    return None


def decompress(path):
    out = os.path.join(tempfile.gettempdir(), "amdgpu_loaded.ko")
    if os.path.exists(out) and os.path.getmtime(out) > os.path.getmtime(path):
        return out
    if path.endswith(".zst"):
        # lzma de python NO tiene FORMAT_ZSTD (comprobado: AttributeError).
        # El binario zstd si esta, y es la via fiable.
        zstd = shutil.which("zstd")
        if not zstd:
            raise RuntimeError("falta el binario zstd para descomprimir")
        r = subprocess.run([zstd, "-d", "-c", path], capture_output=True,
                           timeout=300)
        data = r.stdout
    elif path.endswith(".xz"):
        data = lzma.open(path, "rb").read()
    elif path.endswith(".gz"):
        data = gzip.open(path, "rb").read()
    else:
        shutil.copy2(path, out)
        return out
    open(out, "wb").write(data)
    return out


def sh(*cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    return r.stdout


# ------------------------------------------------------------------ simbolos
def bin_symbols(ko):
    """{nombre: {tipo, tam}} de nm sobre el .ko descomprimido."""
    out = sh("nm", ko)
    syms = {}
    for line in out.split("\n"):
        parts = line.split()
        if len(parts) >= 3 and re.match(r"^[0-9a-fA-F]+$", parts[0]):
            addr, kind, name = parts[0], parts[1], parts[2]
            syms[name] = {"tipo": kind, "dir": addr}
    return syms


def corpus_symbols():
    """{nombre: fichero} de lo que el corpus DEFINE como funcion o variable."""
    out = {}
    for d in (CORPUS_SRC, CORPUS_INC):
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith((".c", ".h")):
                continue
            p = os.path.join(d, f)
            try:
                txt = open(p, errors="replace").read()
            except OSError:
                continue
            # Funciones... y ademas VARIABLES static const, que tambien
            # aparecen en el binario. Sin esto, los once simbolos
            # gfx_v8_0_*_funcs/_ring_funcs salian como "ausentes del corpus"
            # cuando SI estan, porque son tablas, no funciones. Falso positivo
            # mio, y del tipo que hace dudar de la conclusion correcta.
            for m in re.finditer(r"^(?:static\s+)?[\w \*]*?\**(\w+)\s*\(",
                                 txt, re.M):
                out.setdefault(m.group(1), f)
            for m in re.finditer(r"^static\s+const\s+struct\s+\w+\s+(\w+)\s*=",
                                 txt, re.M):
                out.setdefault(m.group(1), f)
    return out


def cross_symbols():
    bs = bin_symbols(KO)
    cs = corpus_symbols()
    in_both = sorted(set(bs) & set(cs))
    only_bin = sorted(set(bs) - set(cs))
    only_corpus = sorted(set(cs) - set(bs))
    return bs, cs, in_both, only_bin, only_corpus


# ------------------------------------------------------------------- cadenas
def bin_strings(ko, minlen=8):
    out = sh("strings", "-n", str(minlen), ko)
    return set(l for l in out.split("\n") if l.strip())


CORPUS_BANNERS = [
    "amdgpu", "GFX", "CP", "CPC", "CPT", "Ring", "ring", "IB",
    "VM_CONTEXT", "GRBM", "GART", "page table", "fence", "scheduler",
    "PM4", "COMPUTE", "SDMA", "VCE", "UVD", "VBIOS", "PSP",
    "GMC", "UMD", "KMD", "pas", "SRBM", "HDP", "ATC", "TLB",
]


def interesting_strings(bs):
    hits = Counter()
    examples = {}
    for s in bs:
        for k in CORPUS_BANNERS:
            if k in s:
                hits[k] += 1
                examples.setdefault(k, s[:90])
    return hits, examples


# ----------------------------------------------------------------------- BTF
def btf_structs(ko):
    """structs desde BTF via bpftool o pahole. Vacio si no hay herramienta."""
    if shutil.which("bpftool"):
        out = sh("bpftool", "btf", "dump", "file", ko, "format", "c")
        return parse_bpftool(out)
    if shutil.which("pahole"):
        out = sh("pahole", "-C", "struct", ko)
        return {"_raw_pahole": len(out.split("\n")), "_out": out[:400]}
    return {"_error": "ni bpftool ni pahole disponibles"}


def parse_bpftool(out):
    structs = {}
    cur = None
    for line in out.split("\n"):
        m = re.match(r"^struct (\w+) \{", line)
        if m:
            cur = m.group(1)
            structs[cur] = {"campos": [], "tam": None}
            continue
        if cur and re.match(r"^\};", line):
            cur = None
            continue
        if cur:
            m2 = re.match(r"\s+(\w[\w ]*\**\w+)\s+(\w+)\s*;", line)
            if m2:
                structs[cur]["campos"].append(m2.group(2))
    return structs


def corpus_struct_size(name):
    """El sizeof de un struct en el corpus, si se puede calcular leyendo."""
    found = []
    for d in (CORPUS_INC, CORPUS_SRC):
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith(".h"):
                continue
            p = os.path.join(d, f)
            try:
                txt = open(p, errors="replace").read()
            except OSError:
                continue
            m = re.search(r"struct\s+" + re.escape(name) + r"\s*\{(.*?)\n\};",
                          txt, re.S)
            if m:
                fields = re.findall(r"([\w \*]+?)\s+(\w+)\s*(\[|\s*;)",
                                    m.group(1))
                found.append((f, [x[1] for x in fields]))
    return found


# ------------------------------------------------------------------- informe
def main():
    global KO
    args = sys.argv[1:]
    ko_path = find_ko()
    if not ko_path:
        print("no se encuentra amdgpu.ko en /lib/modules")
        return 2
    KO = decompress(ko_path)

    print("=" * 74)
    print("BINFACTS -- el binario real del modulo cargado")
    print("=" * 74)
    print(f"kernel en ejecucion     : {KVER}")
    print(f".ko en el arbol         : {ko_path}")
    print(f".ko descomprimido       : {KO}  ({os.path.getsize(KO)} bytes)")
    sv_disk = sh("modinfo", "-F", "srcversion", ko_path).strip()
    sv_loaded = sh("modinfo", "-F", "srcversion", "amdgpu").strip()
    print(f"srcversion del .ko      : {sv_disk}")
    print(f"srcversion CARGADO      : {sv_loaded}")
    print(f"  -> {'COINCIDEN' if sv_disk == sv_loaded and sv_disk else 'difieren o ausente'}")
    print()

    bs, cs, both, only_bin, only_corpus = cross_symbols()

    if not args or "--symbols" in args:
        print("--- SIMBOLOS ---")
        print(f"  en el binario              : {len(bs)}")
        print(f"  definidos en el corpus     : {len(cs)}")
        print(f"  en ambos                   : {len(both)}")
        print(f"  solo en el BINARIO         : {len(only_bin)}")
        print(f"  solo en el CORPUS          : {len(only_corpus)}")
        print()
        if only_corpus:
            print("  primeros que solo estan en el corpus (pueden ser static,")
            print("  o de otro fichero que no es de amdgpu/):")
            for n in only_corpus[:10]:
                print(f"      {n:44} ({cs[n]})")
            print()

    if not args or "--in-corpus" in args:
        print("--- DIRECCION QUE NO SE HA MIRADO: que tiene el binario y el corpus no ---")
        print("  Si esto no esta vacio, el corpus NO describe el binario.")
        # FILTRAR EL RUIDO, que si no lo bury la senal. Medido: de 36405
        # simbolos "ausentes", la mayoria no son del driver:
        #   CSWTCH.N   lowering de switch/case del compilador. Miles.
        #   __*        infraestructura de la toolchain
        #   .L*, ANON, BTF_*   artefactos del compilador y del BTF
        # Lo que interesa es un simbolo NOMBRADO que no este en el corpus y que
        # parezca del driver: una funcion o variable con nombre legible.
        RUIDO = re.compile(
            r"^(CSWTCH\.\d+|__|\.|_exit|_start|cleanup_module|init_module"
            r"|ANON|anon|\.L|BTF_|__param|__UNIQUE|__func__|__string)")
        NOMBRES_BIEN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{3,}$")
        suspicious = [n for n in only_bin
                      if not RUIDO.match(n) and NOMBRES_BIEN.match(n)]
        driverish = [n for n in suspicious
                     if re.search(r"amdgpu|gfx|gmc|cp_|cpRB|kiq|sdma|ring|vm|"
                                  r"sched|pm4|ib_|gfx8|vi_|atombios|display",
                                  n, re.I)]
        print(f"  simbolos NAMED no-ruido ausentes del corpus: {len(suspicious)}")
        print(f"  de ellos con nombre de driver:                 {len(driverish)}")
        print()
        if driverish:
            print("  estos SI parecen del driver y no estan en el corpus:")
            for n in sorted(driverish)[:30]:
                print(f"      {n}")
            print()


    if "--strings" in args:
        print("--- CADENAS ---")
        hits, ex = interesting_strings(bin_strings(KO))
        for k, n in hits.most_common(20):
            print(f"  {k:12} x{n:<6} ej: {ex.get(k,'')[:60]}")
        print()

    if "--btf" in args:
        print("--- BTF ---")
        b = btf_structs(KO)
        if "_error" in b:
            print(f"  {b['_error']}")
        else:
            real_structs = {k: v for k, v in b.items()
                            if not k.startswith("_")}
            print(f"  structs en BTF: {len(real_structs)}")
            for name in ("amdgpu_ring", "amdgpu_device", "amdgpu_kobj",
                         "amdgpu_gfx", "amdgpu_vm_manager",
                         "amdgpu_dm_buf_params"):
                if name in real_structs:
                    n = len(real_structs[name]["campos"])
                    csr = corpus_struct_size(name)
                    csn = len(csr[0][1]) if csr else None
                    mark = "" if csn == n else "  <-- DISCREPA"
                    print(f"      {name:28} BTF {n:4} campos | "
                          f"corpus {csn if csn is not None else '-'} "
                          f"({csr[0][0] if csr else 'no encontrado'}){mark}")
        print()

    return 0


KO = None

if __name__ == "__main__":
    raise SystemExit(main())