#!/usr/bin/env python3
"""reg_census.py — qué registros toca un .c, resueltos, con su unidad y su bus.
    WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE
    No abre /sys, no escribe ficheros, no toca la GPU ni el arbol.

Por qué existe
--------------
Para reconstruir una ruta hay que saber qué MMIO toca cada fichero. Hacerlo a
mano son veinte `grep mm` y luego, para cada nombre, ir a `reg_resolve` a
buscar su offset y su unidad. Y el error de unidad vuelve: `mmGRBM_STATUS2`
es `0x2002` en dword pero `0x8008` en byte, y ambos son "correctos" según
cómo se mire.

Esta herramienta hace el bucle entero de una vez y, sobre todo, hace las dos
distinciones que importan y que un grep no hace:

  1. **acceso directo vs indirecto.** `cgs_read_register(dev, mmX)` va al MMIO
     del ASIC. `cgs_write_ind_register(dev, CGS_IND_REG__DIDT, ixX, v)` va
     primero a `mm*_IND_INDEX` y luego a `mm*_IND_DATA`. El `ix*` NO es un
     offset: es un índice de bus. Confundirlos es el error más caro de la
     serie.

  2. **lectura vs escritura.** Saber que se toca un registro no dice si el
     driver lo configura, lo consulta, o solo lo lee para diagnosticar.

Lo que produce
--------------
Por fichero `.c`: los `mm*` directos, los `ix*` indirectos agrupados por bus,
y el recuento de lecturas y escrituras por registro. Con `--resolve`, añade el
valor y la unidad de cada uno.

Lo que NO hace
--------------
No dice si el registro existe en tu ASIC. Eso lo dice `reg_resolve`. Aquí solo
se lee lo que el fichero menciona.

Uso
---
    reg_census.py --kernel RAIZ --file .../smu7_powertune.c
    reg_census.py --kernel RAIZ --file .../smu7_powertune.c --resolve --gfx gfx_8_0
    reg_census.py --kernel RAIZ --dir pm/powerplay/hwmgr --top 20
    reg_census.py --selftest
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Tuple

NAME = "reg_census"
VERSION = "1.0.0"

DEFAULT_CHIP = "CHIP_POLARIS12"
ASIC_ENUM_REL = "include/drm/amd_asic_type.h"

# Acceso DIRECTO al MMIO. DOS formas, y confundirlas deja registros fuera:
#   con argumentos:   cgs_read_register(hwmgr->device, mmSMC_RESP_0)
#   macro de un solo argumento:  RREG32(mmGRBM_STATUS2)
# La segunda es un `mm*` sin coma delante. Buscar solo la primera deja fuera
# todos los RREG32/WREG32, que son la mitad del acceso directo del driver.
_DIRECT = re.compile(
    r"(?:\b(?P<fn1>cgs_(?:read|write)_register)\s*\(\s*[^,]+,\s*"
    r"(?P<reg1>mm[A-Za-z0-9_]+)\b)"
    r"|(?:\b(?P<fn2>[RWD]REG32)\s*\(\s*(?P<reg2>mm[A-Za-z0-9_]+)\b)"
)
# Acceso INDIRECTO por bus: el segundo argumento es el espacio, el tercero el ix*.
_INDIRECT = re.compile(
    r"\b(?P<fn>cgs_(?:read|write)_ind_register)\s*\(\s*[^,]+,\s*"
    r"(?P<space>CGS_IND_REG_?[A-Z_]*)\s*,\s*(?P<idx>ix[A-Za-z0-9_]+)\b"
)
# Las macros de campo: CGS_WREG32_FIELD_IND(..., CGS_IND_REG__DIDT, DIDT_SQ_CTRL0, ...)
_MACRO_FIELD_IND = re.compile(
    r"CGS_[WR]REG32_FIELD_IND\s*\([^,]+,\s*(?P<space>CGS_IND_REG_?[A-Z_]*)\s*,"
    r"\s*(?P<reg>[A-Za-z_][A-Za-z0-9_]*)\s*,"
)

_BUS_LABEL = {
    "CGS_IND_REG__SMC": "SMC",
    "CGS_IND_REG__DIDT": "DIDT",
    "CGS_IND_REG__PCIE": "PCIE",
    "CGS_IND_REG__UVD_CTX": "UVD_CTX",
    "CGS_IND_REG_GC_CAC": "GC_CAC",
    "CGS_IND_REG_SE_CAC": "SE_CAC",
    "CGS_IND_REG__AUDIO_ENDPT": "AUDIO_ENDPT",
}

# El bus se traduce a dos registros MMIO con este patron. Se declara aqui y se
# marca como PREDICCION, porque la pareja INDEX/DATA la fija cada ASIC.
_IND_PAIR = {
    "DIDT": ("mmDIDT_IND_INDEX", "mmDIDT_IND_DATA"),
    "SMC": ("mmSMC_IND_INDEX", "mmSMC_IND_DATA"),
}


def strip_comments_len(text: str) -> str:
    """Quita comentarios conservando longitud, para no invalidar el mapa de
    posiciones. Ver cap_census.strip_comments: el mismo bug dio 225 lineas
    equivocadas alli y lo arrangla aqui desde el principio."""
    out: List[str] = list(text)
    i, n = 0, len(text)
    while i < n:
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
        elif text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        else:
            i += 1
    return "".join(out)


def census_file(path: str) -> Dict[str, object]:
    if not os.path.isfile(path):
        return {"file": path, "error": "NO_LEGIBLE"}
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        raw = fh.read()
    clean = strip_comments_len(raw)

    direct: Dict[str, Dict[str, object]] = {}
    indirect: Dict[str, Dict[str, object]] = {}
    buses: Dict[str, set] = defaultdict(set)

    def note(store: Dict[str, Dict[str, object]], key: str, rw: str,
             lineno: int, fn: str) -> None:
        e = store.setdefault(key, {"reads": 0, "writes": 0, "lines": [], "fns": set()})
        e["reads" if rw == "r" else "writes"] += 1
        if len(e["lines"]) < 6:
            e["lines"].append(lineno)
        e["fns"].add(fn)

    for m in _DIRECT.finditer(clean):
        lineno = clean[:m.start()].count("\n") + 1
        if m.group("fn1"):
            fn, reg = m.group("fn1"), m.group("reg1")
            rw = "r" if "read" in fn else "w"
        else:
            fn, reg = m.group("fn2"), m.group("reg2")
            rw = "w" if fn[0] == "W" else "r"
        note(direct, reg, rw, lineno, fn)

    for m in _INDIRECT.finditer(clean):
        rw = "r" if "read" in m.group("fn") else "w"
        note(indirect, m.group("idx"), rw, clean[:m.start()].count("\n") + 1, m.group("fn"))
        buses[_BUS_LABEL.get(m.group("space"), m.group("space"))].add(m.group("idx"))

    # Las macros de campo revelan el bus aunque no haya llamada indirecta.
    macro_buses: Dict[str, int] = defaultdict(int)
    for m in _MACRO_FIELD_IND.finditer(clean):
        lbl = _BUS_LABEL.get(m.group("space"), m.group("space"))
        macro_buses[lbl] += 1
        buses[lbl].add(m.group("reg"))

    return {
        "file": path,
        "direct_count": len(direct),
        "indirect_count": len(indirect),
        "direct": {k: {**v, "fns": sorted(v["fns"])} for k, v in sorted(direct.items())},
        "indirect": {k: {**v, "fns": sorted(v["fns"])} for k, v in sorted(indirect.items())},
        "buses": {k: sorted(v) for k, v in sorted(buses.items())},
        "macro_field_calls": dict(sorted(macro_buses.items())),
    }


def render_file(res: Dict[str, object], resolve=None) -> str:
    if res.get("error"):
        return f"{NAME} {VERSION} · ERROR {res['error']}: {res['file']}"
    L = [f"{NAME} {VERSION} · {os.path.basename(str(res['file']))}"]
    d = int(res["direct_count"]); i = int(res["indirect_count"])
    L.append(f"  directos (mm*, MMIO del ASIC)   {d}")
    L.append(f"  indirectos (ix*, bus INDEX/DATA) {i}")
    L.append("")
    if d:
        L.append(f"  {'registro mm*':<34} {'r':>3} {'w':>3} {'lineas':<18} valor")
        L.append("  " + "-" * 78)
        for k, v in list(res["direct"].items())[:40]:  # type: ignore[union-attr]
            val = ""
            if resolve:
                r = resolve(k)
                val = str(r.get("value") or "?")
                if r.get("verdict", "").startswith("DEFINIDO_EN_OTRA"):
                    val += " (otra gen)"
                elif r.get("verdict") == "PROVEN_ABSENT_EN_ASIC_REG":
                    val = "AUSENTE"
            L.append(f"  {k:<34} {v['reads']:>3} {v['writes']:>3} "
                     f"{str(v['lines'])[:18]:<18} {val}")
        if d > 40:
            L.append(f"  ... y {d - 40} mas")
    if res["buses"]:
        L.append("")
        L.append("  BUS INDIRECTO (ix* NO es offset de byte):")
        for bus, regs in res["buses"].items():  # type: ignore[union-attr]
            pair = _IND_PAIR.get(bus)
            pairtxt = f"  -> {pair[0]} / {pair[1]}" if pair else ""
            L.append(f"    {bus:<16} {len(regs)} registros{pairtxt}")
    if res["macro_field_calls"]:
        L.append("")
        L.append(f"  llamadas macro de campo: {res['macro_field_calls']}")
    return "\n".join(L)


def census_dir(root: str, limit: int = 20) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [x for x in dirnames if x not in (".git", "__pycache__")]
        for fn in filenames:
            if not fn.endswith(".c"):
                continue
            p = os.path.join(dirpath, fn)
            r = census_file(p)
            if r.get("error"):
                continue
            r["total_touches"] = int(r["direct_count"]) + int(r["indirect_count"])
            rows.append(r)
    rows.sort(key=lambda r: -int(r["total_touches"]))
    return rows[:limit]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog=NAME,
                                 description="Censo de registros que toca un .c, con unidad y bus.")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--kernel")
    ap.add_argument("--file", action="append", default=[])
    ap.add_argument("--dir", default=None, help="barrer un directorio .c y ranking")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--resolve", action="store_true", help="añadir valor y veredicto")
    ap.add_argument("--gfx", default="gfx_8_0")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.kernel:
        ap.error("--kernel es obligatorio salvo con --selftest")
    kernel = os.path.abspath(args.kernel)

    resolve = None
    if args.resolve:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        try:
            import reg_resolve as RR
            amd_root = os.path.join(kernel, "drivers/gpu/drm/amd")
            resolve = lambda s: RR.resolve_reg(amd_root, args.gfx, s)
        except ImportError:
            print("AVISO  reg_resolve no disponible: --resolve sin efecto",
                  file=sys.stderr)

    if args.dir:
        root = args.dir if os.path.isabs(args.dir) else os.path.join(kernel, args.dir)
        rows = census_dir(root, args.top)
        if args.json:
            print(json.dumps({"tool": NAME, "version": VERSION, "rows": rows},
                             indent=2, ensure_ascii=False))
            return 0
        print(f"{NAME} {VERSION} · ranking de {root}")
        print("  toques = registros mm* directos + indices ix* indirectos")
        print()
        print(f"  {'fichero':<40} {'directos':>9} {'indirectos':>11}")
        print("  " + "-" * 64)
        for r in rows:
            print(f"  {os.path.basename(str(r['file'])):<40} "
                  f"{r['direct_count']:>9} {r['indirect_count']:>11}")
        return 0

    if not args.file:
        ap.error("indica --file o --dir")

    blocks = []
    for f in args.file:
        p = f if os.path.isabs(f) else os.path.join(kernel, f)
        blocks.append(census_file(p))
    if args.json:
        print(json.dumps({"tool": NAME, "version": VERSION, "results": blocks},
                         indent=2, ensure_ascii=False))
        return 0
    for b in blocks:
        print()
        print("=" * 78)
        print(render_file(b, resolve))
    return 0


def selftest() -> int:
    failures: List[str] = []

    def check(name: str, got, want) -> None:
        if got != want:
            failures.append(f"{name}: obtuve {got!r}, esperaba {want!r}")

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "a.c")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(
                "#include \"x.h\"\n"
                "int f(struct amdgpu_device *adev)\n"
                "{\n"
                "\tint r;\n"
                "\tr = cgs_read_register(adev, mmGRBM_STATUS2);\n"
                "\tcgs_write_register(adev, mmGRBM_STATUS2, 0);\n"
                "\tRREG32(mmSMC_RESP_0);\n"
                "\tWREG32(mmSMC_MESSAGE_0, 0x10);\n"
                "\t/* mmNO_TOCADO no debe aparecer */\n"
                "\tr = cgs_read_ind_register(adev, CGS_IND_REG__DIDT, ixDIDT_SQ_CTRL0);\n"
                "\tcgs_write_ind_register(adev, CGS_IND_REG__DIDT, ixDIDT_SQ_WEIGHT0_3, v);\n"
                "\tCGS_WREG32_FIELD_IND(adev, CGS_IND_REG__DIDT,\n"
                "\t\tDIDT_SQ_CTRL0, DIDT_CTRL_EN, 1);\n"
                "\tr = cgs_read_ind_register(adev, CGS_IND_REG_GC_CAC, ixGC_CAC_CNTL);\n"
                "\treturn r;\n"
                "}\n"
            )
        res = census_file(p)
        # 3 registros DISTINTOS: mmGRBM_STATUS2 sale dos veces (lectura y
        # escritura). Lo que se cuenta es el numero de nombres, no de sitios.
        check("census.directos", res["direct_count"], 3)
        # 3 indices indirectos: ixDIDT_SQ_CTRL0, ixDIDT_SQ_WEIGHT0_3, ixGC_CAC_CNTL
        check("census.indirectos", res["indirect_count"], 3)
        check("census.comentario_excluido", "mmNO_TOCADO" in res["direct"], False)
        st = res["direct"]["mmGRBM_STATUS2"]  # type: ignore[index]
        check("census.lectura", st["reads"], 1)
        check("census.escritura", st["writes"], 1)
        check("census.macro_leida_como_escritura",
              res["direct"]["mmSMC_RESP_0"]["reads"], 1)  # type: ignore[index]
        check("census.macro_escrita",
              res["direct"]["mmSMC_MESSAGE_0"]["writes"], 1)  # type: ignore[index]
        check("census.bus_didt", "DIDT" in res["buses"], True)
        check("census.bus_gc_cac", "GC_CAC" in res["buses"], True)
        # El bus DIDT lleva 3 nombres: ixDIDT_SQ_CTRL0, ixDIDT_SQ_WEIGHT0_3
        # (llamadas indirectas) y DIDT_SQ_CTRL0 (de la macro de campo, que
        # pega el prefijo ix por dentro via ix##reg).
        check("census.bus_didt_regs", len(res["buses"]["DIDT"]), 3)  # type: ignore[index]
        check("census.bus_gc_cac_1", len(res["buses"]["GC_CAC"]), 1)  # type: ignore[index]
        check("census.macro_field", res["macro_field_calls"].get("DIDT"), 1)
        # La pareja INDEX/DATA debe citarse: es la que da la unidad del ix*.
        out = render_file(res)
        if "mmDIDT_IND_INDEX" not in out:
            failures.append("render: no declara la pareja INDEX/DATA del bus")

        check("census.ilegible", census_file(os.path.join(td, "nope.c")).get("error"),
              "NO_LEGIBLE")
        open(os.path.join(td, "vacio.c"), "w").close()
        check("census.vacio", census_file(os.path.join(td, "vacio.c"))["direct_count"], 0)

    print(f"{NAME} {VERSION} · self-test")
    if failures:
        print(f"  RESULTADO FALLIDO ({len(failures)}):")
        for f in failures:
            print(f"    - {f}")
        return 1
    print("  RESULTADO OK · vectores conocidos reproducidos")
    print("  NOTA: dice que registros se tocan. NO dice si existen ni que hacen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
