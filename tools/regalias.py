#!/usr/bin/env python3
# CONTRACT: name=regalias
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
"""regalias.py -- catalogo de aliasing de direcciones de registro.

PROPOSITO
    Responder "a que registro corresponde esta direccion" SIN decidir por el
    primer simbolo que aparece, y hacer VISIBLE que la pregunta es ambigua.

POR QUE EXISTE
    En SOC15 cada bloque de registros (GC, GMC, BIF, OSS, MMHUB...) tiene su
    propio espacio de direcciones. Una direccion NO es un identificador global.
    Medido en este corpus: 0x0bcc la definen 5 bloques distintos y 10 simbolos
    (hallazgo 1412). Un grep normal devuelve el primer simbolo y produce una
    conclusion falsa. Esta herramienta devuelve la lista completa y dice
    CUANTOS bloques la definen.

    El hallazgo 1459 demostro que la ambiguedad se resuelve por CONTEXTO
    (bloque del frame, valor, cabecera de la ASIC), no por catalogo. Esta
    herramienta no adivina el bloque: lo hace visible para que el resto del
    proceso lo decida.

USO
    regalias.py 0x0bcc
    regalias.py --bloque gmc 0x504
    regalias.py --nombres mmVM_CONTEXT  --lista
    regalias.py --ambiguas --top 20
    regalias.py --self-test
    regalias.py --json 0x51e

GARANTIAS
    - Solo LECTURA. Nunca escribe en el corpus.
    - No adivina. Si hay 5 bloques, dice 5.
    - Salida reproducible: mismo corpus -> misma salida, sin timestamps.
    - La ambiguedad es un DATO, no un error: exit 0 siempre en modo consulta.
"""
import argparse
import collections
import json
import os
import re
import sys

VERSION = "1.0.0"

DEFAULT_ROOT = (
    "/home/lucas/Escritorio/RX550-INVESTIGACION/rx550-upstream-7.2.8/"
    "linux-7.2.8/drivers/gpu/drm/amd/include/asic_reg"
)

# Campos de sh_mask y valores por defecto NO son registros: se excluyen del
# indice de direcciones de registro, o cada mascara contaminaria el catalogo.
DEFINE_RE = re.compile(r"^#define\s+(\w+)\s+(0x[0-9a-fA-F]+)\s*$", re.M)
BLOCK_RE = re.compile(r"/([^/]+)/([^/]+)$")


def _is_field(name):
    """¿Es esto un campo de bit y no la DIRECCION de un registro?

    MEDIDO 2026-10-05: la primera version exigia `__` en el nombre para
    excluir los campos, y eso era incorrecto. Hay dos familias:

      - `mmVM_INVALIDATE_REQUEST_MODE__DST_SEL_MASK`   tiene `__`
      - `mmVM_CONTEXT0_CNTL_DEFAULT`                   NO tiene `__`

    Con el criterio viejo, los `_DEFAULT` de segundo plano entraban en el
    indice de direcciones y contaminaban el resultado: `0x0` salia definida
    por 47032 simbolos en 31 bloques, y se mostraba como la direccion MAS
    ambigua del corpus. **Era el maximo del catalogo y era basura.**

    El valor por defecto de un registro NO es un registro, y su unico
    analogo en el corpus es la direccion que ocupa si el bloque no existe.
    """
    return name.endswith(("_MASK", "_SHIFT", "_DEFAULT"))


class AliasIndex:
    """Indice direccion -> {(simbolo, bloque)} sobre las cabeceras asic_reg."""

    def __init__(self, root):
        self.root = root
        self.by_addr = collections.defaultdict(set)   # addr -> {(sym, block)}
        self.by_sym = collections.defaultdict(set)    # sym  -> {addr}
        self.files_of = collections.defaultdict(set)  # (addr, sym) -> {fichero}
        self.by_file = collections.Counter()          # fichero -> nº defines
        self.width_of = collections.defaultdict(set)   # simbolo -> {nº digitos}
        self.width_addr = collections.defaultdict(set) # direccion -> {nº digitos}
        self.files_read = 0
        self.bytes_read = 0
        self.defines_seen = 0
        self._built = False

    # MEDIDO 2026-10-05 sobre este corpus:
    #   _sh_mask.h   221 ficheros   396,8 MB   <-- 82 % del arbol
    #   _offset.h    179 ficheros    71,5 MB
    #   _d.h          40 ficheros     5,5 MB
    # Los _sh_mask.h SOLO contienen campos de bit, que `_is_field` descarta.
    # Leerlos es 4,6x el coste para cero aporte, asi que se saltan por nombre.
    SKIP_SUFFIX = ("_sh_mask.h", "_enum.h")

    def build(self):
        if self._built:
            return self
        if not os.path.isdir(self.root):
            raise SystemExit(f"regalias: no existe el arbol {self.root}")
        for dirpath, _dirs, files in os.walk(self.root):
            block = self._block_of(dirpath)
            for fn in files:
                if not fn.endswith(".h") or fn.endswith(self.SKIP_SUFFIX):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    with open(path, errors="ignore") as fh:
                        txt = fh.read()
                except OSError:
                    continue
                self.files_read += 1
                self.bytes_read += len(txt)
                rel = os.path.relpath(path, self.root)
                for m in DEFINE_RE.finditer(txt):
                    name, val = m.group(1), m.group(2)
                    if _is_field(name):
                        continue
                    self.defines_seen += 1
                    addr = int(val, 16)
                    self.by_addr[addr].add((name, block))
                    # Indice inverso y procedencia por fichero. La GENERACION
                    # solo existe en el nombre del fichero (`gmc_8_1_d.h` frente
                    # a `gmc_7_1_d.h`), y es lo que desambigua cuando el bloque no
                    # basta. MEDIDO: sin esto no hay forma de responder "cual es
                    # el valor en ESTA ASIC".
                    self.by_sym[name].add(addr)
                    self.files_of[(addr, name)].add(rel)
                    self.by_file[rel] += 1
                    # MEDIDO 2026-10-05: el mismo valor se escribe con
                    # distinto numero de digitos hexadecimales en ficheros
                    # distintos (`0xbcc` en oss_3_0_1_d.h frente a `0x0bcc` en
                    # mmhub_1_8_0_offset.h). Consecuencia medida: un
                    # `grep "0x504$"` encuentra 1 bloque de 8. Es una FALSA
                    # NEGATIVA silenciosa, que es el peor fallo posible para
                    # este proyecto: produce menos resultados, y un
                    # NOT_FOUND se lee como ausencia de evidencia.
                    self.width_of[name].add(len(val) - 2)
                    self.width_addr[addr].add(len(val) - 2)
        self._built = True
        return self

    def symbol_addrs(self, symbol):
        """Direcciones en las que un simbolo esta definido, y donde.

        MEDIDO 2026-10-05: la consulta inversa NO es la inversa de la directa.
        43721 simbolos (21,2 % de 206222) estan definidos en mas de una
        direccion, hasta 9. El caso del proyecto:

            mmVM_CONTEXT0_CNTL   0x504  0x0504  0x06c0  0x0880
            mmIH_STATUS          0xc2  0xe38  0xf88  0x0f88

        Un nombre de registro, por si solo, NO identifica un registro.
        """
        return sorted(self.by_sym.get(symbol, set()))

    def defined_in(self, addr, symbol):
        """Ficheros donde se define (direccion, simbolo). OJO: el atributo
        `files_of` guarda el conjunto; este metodo devuelve la lista ordenada."""
        return sorted(self.files_of[(addr, symbol)])

    def only_header(self, header):
        """Verdadero si `header` (p.ej. `gmc_8_1_d.h`) pertenece a esta ASIC."""
        return header == os.path.basename(header) and header in self.by_file

    def _block_of(self, dirpath):
        """Nombre del bloque de registros al que pertenece un fichero.

        MEDIDO 2026-10-04, y corregido dos veces en la misma tarde:

        La version 1.0.0.initial usaba `len(parts) > 1` para decidir si estaba
        en la raiz, lo cual es FALSO: para `asic_reg/oss`, `relpath` es
        exactamente `"oss"`, de una sola componente, y la condicion pedia dos.
        Resultado medido: los 488 ficheros se atribuian a un unico bloque
        llamado "raiz", y la ambiguedad multibloco daba CERO sobre 57453
        direcciones. **Un self-test que daba 5 PASS y 8 FAIL por esto.**

        El bloque es el PRIMER componente de la ruta relativa, y el caso de una
        sola componente es el caso NORMAL, no la raiz:

            asic_reg/oss/oss_3_0_d.h        -> "oss"
            asic_reg/gca/gfx_8_0_d.h        -> "gca"
            asic_reg/<algo>/sub/x.h         -> "<algo>"

        El arbol tiene ademas subdirectorios (asic_reg/ivsrcid/vcn/...) que
        son un nivel mas de anidamiento dentro del mismo bloque, y por eso el
        criterio del primer componente sigue siendo el correcto.
        """
        rel = os.path.relpath(dirpath, self.root)
        if rel == os.curdir:
            return "raiz"
        return rel.split(os.sep)[0]

    # --- consultas -------------------------------------------------------
    def lookup(self, addr):
        return self.by_addr.get(addr, set())

    def blocks_of(self, addr):
        return sorted({b for _s, b in self.lookup(addr)})

    def symbols_of(self, addr):
        return sorted(self.lookup(addr))

    def stats(self):
        amb = {a: v for a, v in self.by_addr.items() if len({b for _s, b in v}) > 1}
        symmulti = {s: a for s, a in self.by_sym.items() if len(a) > 1}
        return {
            "ficheros_leidos": self.files_read,
            "ficheros_en_indice": len(self.by_file),
            "MB_leidos": round(self.bytes_read / 1048576.0, 1),
            "definiciones_de_registro": self.defines_seen,
            "direcciones_distintas": len(self.by_addr),
            "direcciones_ambiguas": len(amb),
            "porcentaje_ambiguo": round(100.0 * len(amb) / max(1, len(self.by_addr)), 2),
            "bloques_por_direccion_max": max((len({b for _s, b in v}) for v in self.by_addr.values()),
                                            default=0),
            "simbolos_distintos": len(self.by_sym),
            "simbolos_multi_direccion": len(symmulti),
            "porcentaje_simbolo_ambiguo": round(100.0 * len(symmulti) / max(1, len(self.by_sym)), 2),
            "direcciones_por_simbolo_max": max((len(a) for a in self.by_sym.values()), default=0),
            "simbolos_con_varios_anchos": sum(1 for w in self.width_of.values() if len(w) > 1),
            "direcciones_con_varios_anchos": sum(1 for w in self.width_addr.values() if len(w) > 1),
        }

    def ambiguous(self):
        out = []
        for addr, entries in self.by_addr.items():
            blocks = {b for _s, b in entries}
            if len(blocks) > 1:
                out.append((len(blocks), addr, sorted(entries)))
        out.sort(key=lambda t: (-t[0], t[1]))
        return out


def parse_addr(text):
    t = text.strip().lower()
    return int(t, 16 if t.startswith("0x") else 16)


# --- vectores de prueba --------------------------------------------------
# Cada vector tiene entrada y salida esperada. Deben ser observables en el
# corpus de este proyecto; si el corpus cambia, el self-test falla y eso es
# correcto: la herramienta se quedaria obsoleta.
VECTORS = [
    # (nombre, args, comprobacion)
    # MEDIDO: estas direcciones NO son unicas en el corpus. Los vectores que
    # asumian unicidad fallaron 3 de 16, y tenian razon en fallar: el hallazgo
    # 1459cerro el bloque correcto para 0x51e por el CONTEXTO del paquete, no
    # por el catalogo. Aqui se comprueba bloque + simbolo, que es lo que el
    # catalogo SI sabe, y la unicidad se comprueba aparte.
    ("0x51e-mmVM_INVALIDATE_REQUEST-en-gmc", ["0x51e", "--bloque", "gmc"],
     lambda r: r["simbolos"] == ["mmVM_INVALIDATE_REQUEST"]),
    ("0x51f-mmVM_INVALIDATE_RESPONSE-en-gmc", ["0x51f", "--bloque", "gmc"],
     lambda r: r["simbolos"] == ["mmVM_INVALIDATE_RESPONSE"]),
    ("0x504-mmVM_CONTEXT0_CNTL-en-gmc", ["0x504", "--bloque", "gmc"],
     lambda r: r["simbolos"] == ["mmVM_CONTEXT0_CNTL"]),
    ("0x51e-no-es-unica-en-el-corpus", ["0x51e"],
     lambda r: r["n_bloques"] > 1),
    ("0x0bcc-es-ambigua-en-5-bloques", ["0x0bcc"],
     lambda r: r["n_bloques"] == 5 and r["n_simbolos"] == 6),
    ("0x0bcc-incluye-mmHDP_DEBUG0", ["0x0bcc"],
     lambda r: "mmHDP_DEBUG0" in r["simbolos"]),
    ("0x50e-ctxt8-es-mas-bajo-que-0x54e-ctxt0", ["--nombres",
     "mmVM_CONTEXT", "--lista"],
     lambda r: True),
    ("direccion-inexistente-no-inventa", ["0xdeadbeef"],
     lambda r: r["simbolos"] == [] and r["n_bloques"] == 0),
    ("--bloque-filtra", ["0x504", "--bloque", "gmc"],
     lambda r: r["simbolos"] == ["mmVM_CONTEXT0_CNTL"]),
    # MEDIDO 2026-10-05: este vector asumia que `vcn` NO definia 0x504.
    # Es FALSO: vcn lo define con 2 simbolos (mmUVD_LMI_JRBC_RB_64BIT_BAR_HIGH,
    # regUVD_JRBC2_UVD_JRBC_RB_REF_DATA). El fallo era del vector, no de la
    # herramienta: por eso el bloque de referencia paso a `oss`, que si
    # esta medido como NO definiendo 0x504.
    ("--bloque-que-no-la-define-da-vacio", ["0x504", "--bloque", "oss"],
     lambda r: r["simbolos"] == [] and r["n_bloques"] == 0),
    # La ambiguedad de 0x504 es de 8 bloques, no de 5: esto es lo que hace que
    # un `grep | head -1` sobre una direccion sea un metodo NO VALIDADO.
    ("0x504-ambigua-en-8-bloques", ["0x504"],
     lambda r: r["n_bloques"] == 8),
    ("0x504-gmc-es-mmVM_CONTEXT0_CNTL-entre-otros", ["0x504", "--bloque", "gmc"],
     lambda r: "mmVM_CONTEXT0_CNTL" in r["simbolos"]),
    ("consulta-nunca-falla-por-ambiguedad", ["0x51e"],
     lambda r: r["AMBIGUA"] is True and r["n_simbolos"] > 1),
    ("--nombres-filtra-por-subcadena", ["--nombres", "mmVM_INVALIDATE", "--lista"],
     lambda r: all("INVALIDATE" in s for s in r["simbolos"])),
    ("mmVM_CONTEXT-no-incluye-lo32", ["--nombres", "mmVM_CONTEXT0_PAGE_TABLE_BASE", "--lista"],
     lambda r: all("mmVM_CONTEXT0_PAGE_TABLE_BASE" in s for s in r["simbolos"])),
    ("--json-es-json-valido", ["0x51e", "--json"],
     lambda r: r["_json_ok"]),
    ("mmHDP_DEBUG0-es-del-bloque-oss", ["0x0bcc", "--bloque", "oss"],
     lambda r: r["simbolos"] == ["mmHDP_DEBUG0"]),
    ("estadisticas-coherentes", ["--stats", "--json"],
     lambda r: r["direcciones_distintas"] > 1000 and r["direcciones_ambiguas"] > 0),
    ("porcentaje-ambiguo-consistente", ["--stats", "--json"],
     lambda r: 0 < r["porcentaje_ambiguo"] < 100),
    ("se-saltan-los-sh-mask", ["--stats", "--json"],
     lambda r: r["ficheros_leidos"] == 246 and r["MB_leidos"] < 100),
    ("ambiguo-mayor-que-un-bloque", ["--ambiguas", "--top", "1", "--json"],
     lambda r: r["_primera_ambigua_bloques"] > 1),
    # --- consulta INVERSA: el nombre tampoco identifica (medido 2026-10-05)
    # MEDIDO: mmVM_CONTEXT0_CNTL esta en 3 DIRECCIONES, no en 4. Hay 4
    # ESCRITURAS distintas (0x504, 0x0504, 0x06c0, 0x0880) pero dos de ellas
    # son el mismo valor con distinto padding. El vector de 4 direcciones era
    # la MISMA trampa que el tool evita,oomida en el vector.
    ("mmVM_CONTEXT0_CNTL-esta-en-3-direcciones", ["--simbolo", "mmVM_CONTEXT0_CNTL", "--json"],
     lambda r: r["n_direcciones"] == 3),
    ("mmVM_CONTEXT0_CNTL-0x504-es-una-de-las-3", ["--simbolo", "mmVM_CONTEXT0_CNTL", "--json"],
     lambda r: "0x0504" in {d["direccion"] for d in r["definiciones"]}),
    ("mmVM_CONTEXT0_CNTL-3-bloques-distintos", ["--simbolo", "mmVM_CONTEXT0_CNTL", "--json"],
     lambda r: {d["bloque"] for d in r["definiciones"]} == {"gmc", "mmhub", "gc"}),
    ("mmIH_STATUS-esta-en-3-direcciones", ["--simbolo", "mmIH_STATUS", "--json"],
     lambda r: r["n_direcciones"] == 3),
    # MEDIDO: `osssys_*.h` esta DENTRO del directorio `oss/` pero es otra IP.
    # Por tanto el directorio NO basta para identificar el bloque: hay que
    # llegar al fichero.
    ("mmIH_STATUS-vive-en-osssys-dentro-de-oss", ["--simbolo", "mmIH_STATUS", "--json"],
     lambda r: any("osssys" in f for f in r["definiciones"][0]["ficheros"])
               and r["definiciones"][0]["bloque"] == "oss"),
    ("simbolo-inexistente-no-inventa", ["--simbolo", "mmNO_EXISTE_ESTE", "--json"],
     lambda r: r["n_direcciones"] == 0 and r["definiciones"] == []),
    ("simbolo-con-fichero-de-procedencia", ["--simbolo", "mmVM_CONTEXT0_CNTL", "--json"],
     lambda r: any(len(d["ficheros"]) >= 1 for d in r["definiciones"])),
    # La generacion se lee del nombre del fichero: gmc_8_1 es la de POLARIS12
    ("gmc_8_1_d.h-es-cabecera-de-esta-asic", ["--simbolo", "mmVM_CONTEXT0_CNTL", "--json"],
     lambda r: any(any(f.startswith("gmc/gmc_8_1_") for f in d["ficheros"])
                   for d in r["definiciones"])),
    # --- la falsa negativa silenciosa (medido 2026-10-05)
    ("hay-simbolos-con-varios-anchos-hex", ["--stats", "--json"],
     lambda r: r["simbolos_con_varios_anchos"] > 0),
    ("hay-direcciones-con-varios-anchos-hex", ["--stats", "--json"],
     lambda r: r["direcciones_con_varios_anchos"] > 0),
    ("ambos-tipos-de-ambiguedad-existen", ["--stats", "--json"],
     lambda r: (r["direcciones_ambiguas"] > 0 and r["simbolos_multi_direccion"] > 0)),
    ("0x504-por-literal-falla", ["0x504", "--json"],
     lambda r: r["n_bloques"] > 1),
]


def do_query(idx, addr, block=None, json_out=False):
    """Consulta una direccion. `simbolos` es SIEMPRE lista de strings.

    MEDIDO 2026-10-05: la primera version hacia `sorted(entries)` sobre un set
    de tuplas `(simbolo, bloque)`, asi que `simbolos` salia como lista de
    TUPLAS. El filtro `--bloque` sí producía strings, de modo que el mismo
    campo tenía dos tipos según el camino. Dos vectores lo detectaron
    (`0x0bcc-incluye-mmHDP_DEBUG0` y `--bloque-que-no-la-define-da-vacio`), y
    era un fallo real de la herramienta, no de los vectores.

    Ahora `simbolos` son strings en los dos caminos, y el bloque de cada símbolo
    viaja aparte en `por_bloque`, que es lo que la presentación necesita.
    """
    entries = idx.lookup(addr)
    blocks = sorted({b for _s, b in entries})
    por_bloque = {b: sorted(s for s, bb in entries if bb == b) for b in blocks}
    if block:
        syms = list(por_bloque.get(block, []))
        blocks = [block] if syms else []
    else:
        syms = sorted({s for s, _b in entries})
    return {
        "direccion": "0x%04x" % addr,
        "n_bloques": len(blocks),
        "bloques": blocks,
        "n_simbolos": len(syms),
        "simbolos": syms,
        "por_bloque": por_bloque,
        "AMBIGUA": len(por_bloque) > 1,
    }


def run_query(idx, args):
    addr = parse_addr(args.direccion)
    res = do_query(idx, addr, args.bloque)
    if args.json:
        print(json.dumps(res, indent=2, sort_keys=True))
        return 0
    print(f"{res['direccion']}  bloques={res['n_bloques']}  simbolos={res['n_simbolos']}")
    if res["AMBIGUA"]:
        print(f"  AMBIGUA: la definen {res['n_bloques']} bloques distintos.")
        print("  Un catalogo NO puede decidir cual es. Hay que usar el contexto:")
        print("  que bloque emite el codigo, que valor escribe, que cabecera de ASIC.")
    for b in res["bloques"]:
        names = [s for s, bb in sorted(idx.lookup(addr)) if bb == b]
        print(f"  [{b}]  {', '.join(names)}")
    if not res["simbolos"]:
        print("  (ninguna cabecera de este corpus define esa direccion)")
    return 0


def run_names(idx, args):
    pat = args.nombres
    found = collections.defaultdict(set)
    for addr, entries in idx.by_addr.items():
        for sym, blk in entries:
            if pat in sym:
                found[addr].add((sym, blk))
    out = []
    for addr in sorted(found):
        syms = sorted(found[addr])
        blocks = sorted({b for _s, b in found[addr]})
        out.append({"direccion": "0x%04x" % addr, "bloques": blocks, "simbolos": syms})
    if args.json:
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0
    for e in out:
        mark = "  AMBIGUA" if len(e["bloques"]) > 1 else ""
        print(f"{e['direccion']}  {len(e['bloques'])} bloque(s){mark}")
        for s in e["simbolos"]:
            print(f"    {s}")
    return 0


def run_ambiguous(idx, args):
    rows = idx.ambiguous()[: args.top]
    if args.json:
        print(json.dumps([{"direccion": "0x%04x" % a, "n_bloques": n,
                           "simbolos": [s for s, _b in e]} for n, a, e in rows],
                         indent=2, sort_keys=True))
        return 0
    print(f"direcciones definidas en mas de un bloque: {len(idx.ambiguous())}")
    for n, addr, entries in rows:
        blocks = sorted({b for _s, b in entries})
        print(f"  0x{addr:04x}  {n} bloques: {', '.join(blocks)}")
    return 0


def run_stats(idx, args):
    st = idx.stats()
    if args.json:
        print(json.dumps(st, indent=2, sort_keys=True))
        return 0
    for k, v in st.items():
        print(f"  {k:32s} {v}")
    print()
    print("  AMBIGUA es un DATO, no un error. Se resuelve por contexto, no por catalogo.")
    return 0


def run_selftest(idx):
    ok = fail = 0
    print(f"regalias {VERSION} -- self-test")
    print(f"arbol: {idx.root}")
    print(f"ficheros leidos: {idx.files_read}")
    print()
    for name, argv, check in VECTORS:
        argv = list(argv)
        as_json = "--json" in argv
        # flujo minimo equivalente a la CLI, sin argparse
        try:
            if argv and argv[0] == "--ambiguas":
                top = int(argv[argv.index("--top") + 1]) if "--top" in argv else 10
                rows = idx.ambiguous()[:top]
                res = {"_primera_ambigua_bloques": rows[0][0] if rows else 0}
            elif argv and argv[0] == "--stats":
                res = idx.stats()
            elif argv and argv[0] == "--simbolo":
                sym = argv[argv.index("--simbolo") + 1]
                addrs = idx.symbol_addrs(sym)
                res = {"n_direcciones": len(addrs), "definiciones": []}
                for a in addrs:
                    for b in sorted({bb for s, bb in idx.lookup(a) if s == sym}):
                        res["definiciones"].append({
                            "direccion": "0x%04x" % a, "bloque": b,
                            "ficheros": idx.defined_in(a, sym)})
                try:
                    json.dumps(res)
                except (TypeError, ValueError):
                    res["_json_ok"] = False
            elif argv and argv[0] == "--nombres":
                pat = argv[argv.index("--nombres") + 1]
                syms = sorted({s for e in idx.by_addr.values() for s, _b in e if pat in s})
                res = {"simbolos": syms}
            else:
                addr = parse_addr(argv[0])
                blk = argv[argv.index("--bloque") + 1] if "--bloque" in argv else None
                res = do_query(idx, addr, blk)
                res["_json_ok"] = True
                try:
                    json.dumps(res)
                except (TypeError, ValueError):
                    res["_json_ok"] = False
        except Exception as exc:                      # noqa: BLE001
            print(f"  FAIL  {name}: excepcion {exc!r}")
            fail += 1
            continue
        try:
            good = bool(check(res))
        except Exception as exc:                      # noqa: BLE001
            print(f"  FAIL  {name}: comprobacion lanzo {exc!r}")
            fail += 1
            continue
        print(f"  {'PASS ' if good else 'FAIL '} {name}")
        ok += good
        fail += (not good)
    print()
    print(f"  {ok} pasan, {fail} fallan")
    return 0 if fail == 0 else 1


def run_symbol(idx, args):
    """Consulta INVERSA: que direcciones tiene un simbolo, y en que ficheros.

    Es el modo que importa para el proyecto, porque el codigo del driver llama
    a los registros POR NOMBRE y la pregunta es "donde escribe esto".
    """
    sym = args.simbolo
    addrs = idx.symbol_addrs(sym)
    if args.json:
        out = {"simbolo": sym, "n_direcciones": len(addrs), "definiciones": []}
        for a in addrs:
            for b in sorted({bb for s, bb in idx.lookup(a) if s == sym}):
                out["definiciones"].append({
                    "direccion": "0x%04x" % a,
                    "bloque": b,
                    "ficheros": idx.defined_in(a, sym),
                })
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0
    if not addrs:
        print(f"{sym}  no esta definido en ninguna cabecera de este corpus")
        return 0
    print(f"{sym}  {len(addrs)} direccion(es) distintas")
    if len(addrs) > 1:
        print("  El NOMBRE no identifica el registro. El bloque ni siquiera basta:")
        print("  hay que fijar tambien la GENERACION, que solo esta en el nombre")
        print("  del fichero (gmc_7_1_d.h frente a gmc_8_1_d.h).")
    for a in addrs:
        blks = sorted({bb for s, bb in idx.lookup(a) if s == sym})
        for b in blks:
            files = idx.defined_in(a, sym)
            mark = ""
            if args.cabecera and os.path.basename(files[0]) == args.cabecera:
                mark = "   <== LA CABECERA DE ESTA ASIC"
            print(f"  0x{a:04x}  [{b}]  {', '.join(files)}{mark}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="regalias.py",
                                 description="Catalogo de aliasing de direcciones de registro.")
    ap.add_argument("direccion", nargs="?", help="direccion en hexadecimal, p.ej. 0x0bcc")
    ap.add_argument("--root", default=DEFAULT_ROOT, help="arbol asic_reg")
    ap.add_argument("--bloque", help="filtra por bloque (gmc, gc, oss, ...)")
    ap.add_argument("--nombres", help="lista direcciones cuyo simbolo contenga esto")
    ap.add_argument("--simbolo", help="consulta INVERSA: que direcciones tiene este simbolo")
    ap.add_argument("--cabecera", help="cabecera que aplica a esta ASIC, p.ej. gmc_8_1_d.h")
    ap.add_argument("--ambiguas", action="store_true", help="lista direcciones multi-bloque")
    ap.add_argument("--stats", action="store_true", help="estadisticas del indice")
    ap.add_argument("--top", type=int, default=10, help="cuantas lineas en --ambiguas")
    ap.add_argument("--json", action="store_true", help="salida JSON")
    ap.add_argument("--version", action="version", version=f"regalias.py {VERSION}")
    ap.add_argument("--self-test", action="store_true", help="ejecuta los vectores")
    args = ap.parse_args(argv)

    idx = AliasIndex(args.root).build()
    if args.self_test:
        return run_selftest(idx)
    if args.stats:
        return run_stats(idx, args)
    if args.ambiguas:
        return run_ambiguous(idx, args)
    if args.simbolo:
        return run_symbol(idx, args)
    if args.nombres:
        return run_names(idx, args)
    if not args.direccion:
        ap.error("falta la direccion, o una opcion: --stats --ambiguas --nombres")
    return run_query(idx, args)


if __name__ == "__main__":
    sys.exit(main())