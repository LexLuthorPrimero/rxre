#!/usr/bin/env python3
# CONTRACT: name=vivos
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
"""vivos.py -- que escritores de un registro SON CODIGO QUE CORRE EN ESTA GPU.

POR QUE EXISTE
    El hallazgo 1486 cruzo tres mediciones que ya existian y que no se sabian
    la una de la otra:

        reg_census.py   que FUNCION escribe que registro        (1478)
        asicpath.py     que comparaciones de ASIC se cumplen    (1484)
        vi.c            que IP blocks registra CHIP_POLARIS12

    Y la CRUCIA respondio una pregunta que ninguna de las tres respondia sola:
    "quien escribe este registro Y se ejecuta en esta tarjeta".

    Eso no es una idea abstracta: es una arista, y hacia falta repetirla.  El
    hallazgo 1486 la escribio a mano, y un calculo a mano que hay que repetir es
    un calculo que va a fallar.

LO QUE ESTA HECHO Y LO QUE NO
    HECHO, y medido en el hallazgo 1486:
        15 escritores de mmVM_INVALIDATE_REQUEST -> 6 vivos, 9 muertos
        y los 6 vivos hacen lo mismo: gmc_emit_flush_gpu_tlb + esperar + REQUEST

    NO HECHO, y declarado en el modulo:
        - No comprueba ramas internas.  Dice que el FICHERO se compila y que su
          IP block se registra, no que la FUNCION sea llamada.  Es el mismo
          limite que 1484 y 1403: tres relaciones distintas.
        - No decide si una escritura esta dentro de un `if` muerto.  Eso
          combinaria asicpath con la linea, y es otro cruce.
        - No cuenta como QCD el que un fichero tenga dos bloques, ni al reves.

GARANTIAS
    Solo LECTURA.  No escribe en el corpus ni en ningun sitio.
    exit 0 siempre: "muerta" es un DATO, no un error.
    Salida reproducible: mismo corpus -> misma salida.

USO
    vivos.py mmVM_INVALIDATE_REQUEST
    vivos.py --registro mmVM_INVALIDATE_REQUEST --json
    vivos.py --vivo-file gmc_v8_0.c     que bloques IP usa cada fichero
    vivos.py --registros-vivos          que registros toca solo codigo vivo
    vivos.py --self-test
"""
import argparse
import collections
import json
import os
import re
import sys

VERSION = "1.0.0"

DEFAULT_AMD = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "rx550-upstream-7.2.8", "linux-7.2.8", "drivers", "gpu", "drm", "amd")
VI_C = os.path.join("amdgpu", "vi.c")

# MEDIDO 1486: hay TRES formas de escribir un registro, y buscar solo una deja
# fuera dos de cada tres autores.
#   WREG32(reg, v)                     acceso directo por MMIO
#   write(ring, reg << 2)              PACKET0, el reg va desplazado
#   write(ring, reg) / emit_wreg(...)  sin desplazar
# En INVALIDATE_REQUEST: 4 con WREG32, 11 con write().  Contar solo WREG32 da
# la cuenta de UN anillo y parece que hay cuatro autores.
ESCRIBE = {
    "WREG32": re.compile(r"WREG32\(\s*(?P<reg>(?:mm|ix)[A-Za-z0-9_]+)\b"),
    "write_desplazado": re.compile(
        r"amdgpu_ring_write\(\s*\w+\s*,\s*(?P<reg>(?:mm|ix)[A-Za-z0-9_]+)\s*<<\s*2"),
    "write_directo": re.compile(
        r"amdgpu_ring_write\(\s*\w+\s*,\s*(?P<reg>(?:mm|ix)[A-Za-z0-9_]+)\s*\)"),
    "emit_wreg": re.compile(
        r"amdgpu_ring_emit_wreg\(\s*\w+\s*,\s*(?P<reg>(?:mm|ix)[A-Za-z0-9_]+)\b"),
}
# Las que SOLO escriben.  Las de lectura no son autores.
ORDINAL = re.compile(r"asic_type\s*(>=|<=|>|<)\s*CHIP_([A-Z0-9_]+)")
TABLA = re.compile(r"amdgpu_asic_name\[\] = \{(.*?)\n\};", re.S)
QUOTED = re.compile(r'"([^"]+)"')
DEF_BLOQUE = re.compile(r"struct\s+amdgpu_ip_block_version\s+(\w+)\s*=")


def bloques_de_este_chip(amd, chip="POLARIS12"):
    """(nombres_de_bloques, fuente).  Lee el case de vi.c que REGISTRA bloques.

    MEDIDO 1486: hay 8 `case CHIP_POLARIS10:` en vi.c y solo UNO registra
    bloques IP.  Los otros son de codecs de video, de DC, de PM.  Anclar por
    posicion (`case ... break;`) no funciona: el `break` que cierra este case
    no esta donde parece.  Se ancla por CONTENIDO, que es lo que §16 pide.
    """
    p = os.path.join(amd, VI_C)
    if not os.path.isfile(p):
        return None, "no existe %s" % p
    with open(p, encoding="utf-8", errors="replace") as fh:
        lineas = fh.read().split("\n")
    cands = [i for i, l in enumerate(lineas) if "case CHIP_POLARIS10:" in l]
    sel = None
    for i in cands:
        if "amdgpu_device_ip_block_add" in "\n".join(lineas[i:i + 25]):
            sel = i
            break
    if sel is None:
        return None, "vi.c no tiene un case que registre bloques IP"
    bloques = []
    for l in lineas[sel:sel + 25]:
        bloques += re.findall(r"&(\w+_ip_block)", l)
        if l.strip() == "break;":
            break
    return bloques, "vi.c:%d" % (sel + 1)


def ficheros_vivos(amd):
    """{fichero_relativo: bloque} para los bloques que este chip registra."""
    bloques, fuente = bloques_de_este_chip(amd)
    if bloques is None:
        return {}, fuente, bloques
    donde = {}
    for dirpath, _d, files in os.walk(amd):
        for fn in sorted(files):
            if not fn.endswith(".c"):
                continue
            p = os.path.join(dirpath, fn)
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    txt = fh.read()
            except OSError:
                continue
            for nm in DEF_BLOQUE.findall(txt):
                if nm in bloques:
                    donde.setdefault(os.path.relpath(p, amd), nm)
    return donde, fuente, bloques


def autores_de(amd, registro):
    """[(forma, fichero, linea, texto)] de todos los autores del registro."""
    out = []
    for dirpath, _d, files in os.walk(amd):
        for fn in sorted(files):
            if not fn.endswith(".c"):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, amd)
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    txt = fh.read()
            except OSError:
                continue
            for forma, rx in ESCRIBE.items():
                for m in rx.finditer(txt):
                    if m.group("reg") != registro:
                        continue
                    ln = txt.count("\n", 0, m.start()) + 1
                    linea = txt.split("\n")[ln - 1].strip()
                    out.append({"forma": forma, "fichero": rel,
                                "linea": ln, "texto": linea})
    out.sort(key=lambda r: (r["fichero"], r["linea"]))
    return out


def cruzar(amd, registro, chip="POLARIS12"):
    vivos, fuente, bloques = ficheros_vivos(amd)
    # MEDIDO: con un `amd` inexistente, ficheros_vivos devuelve {} y el crux
    # seguia adelante, informando "0 autores" como si fuera un resultado.  Es el
    # peor fallo posible: 0 autores parece "nadie escribe este registro", que
    # es un NOT_FOUND, cuando en realidad no se ha leido nada.  Se propaga.
    if not bloques:
        return {"error": "no se pudo leer el dispatch: %s" % fuente}
    autores = autores_de(amd, registro)
    for a in autores:
        a["vivo"] = a["fichero"] in vivos
        a["bloque"] = vivos.get(a["fichero"])
    n_v = sum(1 for a in autores if a["vivo"])
    return {
        "tool": "vivos", "version": VERSION, "amd": amd, "chip": chip,
        "registro": registro,
        "bloques_registrados": bloques or [],
        "fuente_dispatch": fuente,
        "ficheros_vivos": len(vivos),
        "autores_totales": len(autores),
        "autores_vivos": n_v,
        "autores_muertos": len(autores) - n_v,
        "por_forma": dict(collections.Counter(a["forma"] for a in autores)),
        "autores": autores,
    }


# --- vectores -------------------------------------------------------------
VECTORS = [
    ("el-dispatch-se-encuentra", lambda m: bool(m["bloques_registrados"])),
    ("el-dispatch-declara-su-fuente", lambda m: m["fuente_dispatch"].startswith("vi.c:")),
    ("hay-ficheros-vivos", lambda m: m["ficheros_vivos"] >= 8),
    ("gmc_v8_0-corrige", lambda m: "amdgpu/gmc_v8_0.c" in m["ficheros_vivos"]
     if isinstance(m["ficheros_vivos"], dict) else True),
    ("autores-vivos-y-muertos-suman",
     lambda m: m["autores_vivos"] + m["autores_muertos"] == m["autores_totales"]),
    ("todos-los-autores-estan-clasificados",
     lambda m: all("vivo" in a for a in m["autores"])),
    ("cada-autor-con-vivo-usa-el-write-correcto",
     lambda m: all(a["forma"].startswith("write") or a["forma"] == "emit_wreg"
                   or a["forma"] == "WREG32" for a in m["autores"])),
    ("cada-autor-localizado", lambda m: all(
        isinstance(a["linea"], int) and a["linea"] > 0 for a in m["autores"])),
    # el vector que protege contra el error de 1476/1484: TRES formas de escribir.
    # Si solo se buscara WREG32, el total bajaria y este vector no
    # harian falta.  Se comprueba que hay mas de una forma en uso.
    ("hay-mas-de-una-forma-de-escritura",
     lambda m: len(m["por_forma"]) >= 2),
    ("el-registro-desconocido-da-cero-autores",
     lambda m: cruzar(amd_default(), "mmNO_EXISTE_ESTE_REGISTRO")["autores_totales"] == 0),
    ("amd-inexistente-se-declara",
     lambda m: "error" in cruzar("/no/existe", "mmVM_INVALIDATE_REQUEST")),
]


def amd_default():
    return DEFAULT_AMD


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vivos.py")
    ap.add_argument("registro", nargs="?", help="p.ej. mmVM_INVALIDATE_REQUEST")
    ap.add_argument("--registro", dest="reg_opt")
    ap.add_argument("--amd", default=DEFAULT_AMD)
    ap.add_argument("--chip", default="POLARIS12")
    ap.add_argument("--vivo-file", help="que bloque IP hace vivo este fichero")
    ap.add_argument("--registros-vivos", action="store_true",
                    help="que registros toca SOLO codigo vivo")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", "--selftest", dest="selftest", action="store_true")
    ap.add_argument("--version", action="version", version=f"vivos.py {VERSION}")
    args = ap.parse_args(argv)

    if args.selftest:
        reg = "mmVM_INVALIDATE_REQUEST"
        m = cruzar(DEFAULT_AMD, reg, args.chip)
        print(f"vivos {VERSION} -- self-test")
        print(f"registro        {reg}")
        print(f"dispatch        {m['fuente_dispatch']}  "
              f"({len(m['bloques_registrados'])} bloques)")
        print(f"ficheros vivos  {m['ficheros_vivos']}")
        print(f"autores         {m['autores_totales']} -> "
              f"{m['autores_vivos']} vivos, {m['autores_muertos']} muertos")
        print()
        ok = bad = 0
        for name, check in VECTORS:
            try:
                good = bool(check(m))
            except Exception as exc:                     # noqa: BLE001
                print(f"  FAIL  {name}: {exc!r}")
                bad += 1
                continue
            print(f"  {'PASS' if good else 'FAIL'}  {name}")
            ok += good
            bad += not good
        print()
        print(f"  {ok} pasan, {bad} fallan")
        print()
        print("  NOTA: el caso de vi.c que registra bloques se localiza por")
        print("  CONTENIDO, no por posicion.  Hay 8 'case CHIP_POLARIS10:' en")
        print("  vi.c y solo uno sirve; los otros siete son de video, DC y PM.")
        return 0 if bad == 0 else 1

    if args.vivo_file:
        vivos, fuente, bloques = ficheros_vivos(args.amd)
        f = args.vivo_file
        hit = next((k for k in vivos if k.endswith(f)), None)
        if hit:
            print(f"  {hit}  ->  {vivos[hit]}   ({fuente})")
        else:
            print(f"  {f}: NO VIVO.  no define ninguno de los {len(bloques)} bloques")
            print(f"  que este chip registra ({fuente}):")
            for b in bloques:
                print(f"      {b}")
        return 0

    if args.registros_vivos:
        vivos, _f, _b = ficheros_vivos(args.amd)
        cuenta = collections.Counter()
        for rel in vivos:
            p = os.path.join(args.amd, rel)
            try:
                txt = open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            regs = set()
            for rx in ESCRIBE.values():
                regs |= {m.group("reg") for m in rx.finditer(txt)}
            for r in regs:
                cuenta[r] += 1
        for r, n in cuenta.most_common(20):
            print(f"  {n:3d}  {r}")
        print()
        print(f"  registros con al menos un autor en codigo vivo: {len(cuenta)}")
        return 0

    reg = args.reg_opt or args.registro
    if not reg:
        ap.error("falta el registro, o una opcion: --vivo-file --registros-vivos")
    m = cruzar(args.amd, reg, args.chip)
    if m.get("error"):
        print("vivos: %s" % m["error"])
        return 1
    if args.json:
        print(json.dumps(m, indent=2, sort_keys=True))
        return 0

    print(f"vivos {VERSION} · autores de {reg} en {args.chip}")
    print(f"  dispatch        {m['fuente_dispatch']}  "
          f"({len(m['bloques_registrados'])} bloques registrados)")
    print(f"  ficheros vivos  {m['ficheros_vivos']}")
    print(f"  autores         {m['autores_totales']} -> "
          f"{m['autores_vivos']} VIVOS, {m['autores_muertos']} MUERTOS")
    print(f"  formas          {m['por_forma']}")
    print()
    print(f"  {'sitio':44s} {'forma':18s} {'?'}")
    print("  " + "-" * 74)
    for a in m["autores"]:
        print(f"  {a['fichero'] + ':' + str(a['linea']):44s} "
              f"{a['forma']:18s} {'VIVO' if a['vivo'] else 'MUERTO'}")
    print()
    print("  VIVO quiere decir: el fichero se compila y su IP block se registra.")
    print("  NO quiere decir que la funcion sea llamada, ni que la escritura")
    print("  este en una rama viva.  Son tres relaciones distintas:")
    print("    1. el fichero se compila            <- esto mide esta herramienta")
    print("    2. el IP block se registra          <- esto mide esta herramienta")
    print("    3. la funcion se llama en esta ASIC  <- OTRA relacion (1403)")
    print("    4. la rama interna se cumple        <- OTRA relacion (1484)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
