#!/usr/bin/env python3
"""toolcheck.py — contrato e integridad de las herramientas del proyecto.

Por qué existe
--------------
Hay diez herramientas propias y cuatro ajenas en `tools/`. Cada una promete
un contrato (nombre, versión, propósito, self-test, limitaciones) y ninguna lo
cumplía de forma verificable. Ya ha pasado: `msg_census` devolvió durante una
tanda **503 números de mensaje, la mayoría de la generación equivocada**, sin
avisar. El número era plausible; solo se detectó porque alguien comprobó a mano
qué cabecera se estaba usando.

Un parser correcto NO demuestra que la herramienta sea correcta. Este fichero
comprueba lo que sí se puede comprobar de forma automática:

  1. ¿existe y arranca?
  2. ¿el self-test pasa y con qué código de salida?
  3. ¿el texto declara sus límites? Una herramienta que no dice qué NO hace
     es una herramienta que hay que leer entera para usar bien.
  4. ¿hay Python que no parsea?
  5. ¿declara WORK_CLASS y WRITE_EXECUTION?

Lo que NO hace
--------------
No comprueba que la herramienta diga la verdad. Comprueba que tenga forma de
decirla y que sus pruebas automatizadas pasen. El juicio sobre la salida sigue
siendo de quien lee, y eso no se automatiza.

Uso
---
    toolcheck.py --dir tools
    toolcheck.py --dir tools --json
    toolcheck.py --selftest
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import time
from typing import Dict, List, Optional, Sequence, Tuple

NAME = "toolcheck"
VERSION = "1.0.0"

# Un timeout generoso: clang y el preprocesado tardan. Cortar aqui produciria
# un fallo falso, y un fallo falso en la herramienta que vigila las demas es
# peor que no tenerla.
SELFTEST_TIMEOUT = 150

# Lo que una herramienta debe declarar para ser auditable.
REQUIRED_MARKS = {
    "WORK_CLASS": r"WORK_CLASS",
    "WRITE_EXECUTION": r"WRITE_EXECUTION",
    "VERSION": r"__version__|VERSION\s*=",
    "LIMITACIONES": r"Lo que NO hace|Lo que no hace|NOT:|no prueba|no valida|no demuestra",
}

# Herramientas que no son mias o que son validadores: se listan pero no se
# exigen las mismas marcas.
ALIASES = {"docscan.py", "validate_rx550_final.py", "ipsolve.py",
           "vmid_map.py", "which_hw.py", "evidence_search.py"}


def py_syntax(path: str) -> Tuple[bool, str]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            ast.parse(fh.read(), filename=path)
        return True, ""
    except SyntaxError as e:
        return False, f"{type(e).__name__} linea {e.lineno}: {e.msg}"
    except (OSError, RecursionError) as e:
        return False, str(e)


def has_selftest(path: str) -> bool:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except OSError:
        return False
    return "--selftest" in src and "def selftest" in src


def run_selftest(path: str, timeout: int = SELFTEST_TIMEOUT) -> Dict[str, object]:
    """Ejecuta --selftest y distingue OK, PARCIAL y FALLO.

    Un codigo 0 con texto que diga PARCIAL no es un OK: hay herramientas que
    declaran que su self-test es parcial porque falta una dependencia. Sin
    esa distincion, un resumen contaria como verde algo que no lo esta.
    """
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, path, "--selftest"],
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "seconds": timeout, "detail": "supera el timeout"}
    except OSError as e:
        return {"status": "ERROR", "detail": str(e)}
    dt = time.time() - t0
    out = (r.stdout or "") + (r.stderr or "")
    low = out.lower()
    if r.returncode == 0:
        if "resultado parcial" in low or "parcial" in low:
            status = "PARCIAL"
        else:
            status = "OK"
    elif "resultado parcial" in low:
        status = "PARCIAL_RC"
    else:
        status = "FALLO"
    detail = ""
    for line in out.splitlines():
        if line.strip().startswith("RESULTADO") or "error" in line.lower():
            detail = line.strip()[:200]
            break
    return {"status": status, "rc": r.returncode, "seconds": round(dt, 1),
            "detail": detail}


def declared_marks(path: str) -> Dict[str, bool]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except OSError:
        return {k: False for k in REQUIRED_MARKS}
    return {k: bool(re.search(pat, src, re.I)) for k, pat in REQUIRED_MARKS.items()}


def audit(path: str, run: bool = True) -> Dict[str, object]:
    name = os.path.basename(path)
    ok, syn = py_syntax(path)
    st = has_selftest(path)
    marks = declared_marks(path)
    res: Dict[str, object] = {
        "tool": name,
        "bytes": os.path.getsize(path),
        "syntax_ok": ok,
        "syntax_detail": syn,
        "has_selftest": st,
        "marks": marks,
        "is_alias": name in ALIASES,
    }
    if not ok:
        res["verdict"] = "NO_PARSEA"
        res["missing_marks"] = []
        res["severity"] = "BLOQUEANTE"
        return res
    if not st:
        res["verdict"] = "SIN_SELFTEST"
        res["missing_marks"] = []
        res["severity"] = "ALTO" if name not in ALIASES else "INFO"
        return res
    if run:
        r = run_selftest(path)
        res["selftest"] = r
        if r["status"] in ("FALLO", "TIMEOUT", "ERROR", "PARCIAL_RC"):
            res["verdict"] = "SELFTEST_" + str(r["status"])
            res["missing_marks"] = [k for k, v in marks.items() if not v]
            res["severity"] = "BLOQUEANTE"
            return res
        if r["status"] == "PARCIAL":
            res["verdict"] = "SELFTEST_PARCIAL"
            res["missing_marks"] = [k for k, v in marks.items() if not v]
            res["severity"] = "AVISO"
            return res
    faltan = [k for k, v in marks.items() if not v]
    res["missing_marks"] = faltan
    res.setdefault("severity", "OK")
    if faltan:
        res["verdict"] = "CONTRATO_INCOMPLETO"
        res["severity"] = "MEDIO"
    else:
        res["verdict"] = "CONFORME"
        res["severity"] = "OK"
    return res


def render(rows: Sequence[Dict[str, object]]) -> str:
    L = [f"{NAME} {VERSION} · auditoria de herramientas"]
    L.append("  comprueba que la herramienta arranque, que su self-test pase y")
    L.append("  que declare sus limites. NO comprueba que diga la verdad.")
    L.append("")
    L.append(f"  {'herramienta':<26} {'veredicto':<22} {'sintaxis':<9} {'selftest':<10} {'s':>5}")
    L.append("  " + "-" * 82)
    for r in rows:
        st = str(r.get("selftest", {}).get("status", "-"))  # type: ignore[union-attr]
        L.append(f"  {str(r['tool'])[:26]:<26} {str(r['verdict'])[:22]:<22} "
                 f"{('ok' if r['syntax_ok'] else 'FALLA'):<9} {st:<10} "
                 f"{r.get('selftest', {}).get('seconds', '-'):>5}")  # type: ignore[union-attr]
        if not r["syntax_ok"]:
            L.append(f"      {r['syntax_detail']}")
        if r.get("missing_marks"):
            L.append(f"      sin declarar: {', '.join(r['missing_marks'])}")  # type: ignore[arg-type]
    L.append("")
    from collections import Counter
    sev = Counter(str(r["severity"]) for r in rows)
    L.append("  " + "  ".join(f"{k}={v}" for k, v in sorted(sev.items())))
    return "\n".join(L)


def selftest() -> int:
    failures: List[str] = []

    def check(name: str, got, want) -> None:
        if got != want:
            failures.append(f"{name}: obtuve {got!r}, esperaba {want!r}")

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        # 1. Python valido
        good = os.path.join(td, "buena.py")
        with open(good, "w", encoding="utf-8") as fh:
            fh.write("#!/usr/bin/env python3\n"
                     '"""doc"""\n'
                     'VERSION = "1.0.0"\n'
                     'WORK_CLASS = "READ_ONLY"\n'
                     'WRITE_EXECUTION = "NONE"\n'
                     '# Lo que NO hace: nada, esto es un fixture.\n'
                     'import sys\n'
                     'def selftest():\n'
                     '    print("RESULTADO OK")\n'
                     '    return 0\n'
                     'if __name__ == "__main__":\n'
                     '    sys.exit(selftest() if "--selftest" in sys.argv else 0)\n')
        a = audit(good)
        check("buena.sintaxis", a["syntax_ok"], True)
        check("buena.tiene_selftest", a["has_selftest"], True)
        check("buena.marcas", all(a["marks"].values()), True)
        r = run_selftest(good)
        check("buena.run", r["status"], "OK")

        # 2. Python que NO parsea: el caso que debe ser BLOQUEANTE
        bad = os.path.join(td, "mala.py")
        with open(bad, "w", encoding="utf-8") as fh:
            fh.write("def f(:\n    pass\n")
        b = audit(bad)
        check("mala.sintaxis", b["syntax_ok"], False)
        check("mala.veredicto", b["verdict"], "NO_PARSEA")
        check("mala.severidad", b["severity"], "BLOQUEANTE")

        # 3. self-test que FALLA
        fails = os.path.join(td, "falla.py")
        with open(fails, "w", encoding="utf-8") as fh:
            fh.write('"""WORK_CLASS WRITE_EXECUTION VERSION NO hace"""\n'
                     "import sys\n"
                     "def selftest():\n"
                     '    print("RESULTADO FALLIDO")\n'
                     "    return 1\n"
                     'if __name__ == "__main__":\n'
                     '    sys.exit(selftest() if "--selftest" in sys.argv else 1)\n')
        c = audit(fails)
        check("falla.veredicto", c["verdict"], "SELFTEST_FALLO")
        check("falla.severidad", c["severity"], "BLOQUEANTE")

        # 4. self-test PARCIAL: rc 0 pero dice PARCIAL. NO es verde.
        par = os.path.join(td, "parcial.py")
        with open(par, "w", encoding="utf-8") as fh:
            fh.write('"""WORK_CLASS WRITE_EXECUTION VERSION NO hace"""\n'
                     "import sys\n"
                     "def selftest():\n"
                     '    print("RESULTADO PARCIAL: falta clang")\n'
                     "    return 0\n"
                     'if __name__ == "__main__":\n'
                     '    sys.exit(selftest() if "--selftest" in sys.argv else 0)\n')
        d = audit(par)
        check("parcial.veredicto", d["verdict"], "SELFTEST_PARCIAL")
        check("parcial.severidad", d["severity"], "AVISO")

        # 5. sin self-test
        nos = os.path.join(td, "sin.py")
        with open(nos, "w", encoding="utf-8") as fh:
            fh.write("# sin self-test\nx = 1\n")
        e = audit(nos)
        check("sin_selftest.veredicto", e["verdict"], "SIN_SELFTEST")

        # 6. marcas incompletas
        inc = os.path.join(td, "incompleta.py")
        with open(inc, "w", encoding="utf-8") as fh:
            fh.write("import sys\n"
                     "def selftest():\n"
                     '    print("RESULTADO OK")\n'
                     "    return 0\n"
                     'if __name__ == "__main__":\n'
                     '    sys.exit(selftest() if "--selftest" in sys.argv else 0)\n')
        f = audit(inc)
        check("incompleta.veredicto", f["verdict"], "CONTRATO_INCOMPLETO")
        check("incompleta.marcas_faltan", len(f["missing_marks"]) > 0, True)

        # 7. timeout no debe confundirse con OK
        lento = os.path.join(td, "lento.py")
        with open(lento, "w", encoding="utf-8") as fh:
            fh.write("import sys, time\n"
                     "def selftest():\n"
                     "    time.sleep(5)\n"
                     '    print("RESULTADO OK")\n'
                     "    return 0\n"
                     'if __name__ == "__main__":\n'
                     '    sys.exit(selftest() if "--selftest" in sys.argv else 0)\n')
        g = run_selftest(lento, timeout=1)
        check("timeout.detectado", g["status"], "TIMEOUT")

    print(f"{NAME} {VERSION} · self-test")
    if failures:
        print(f"  RESULTADO FALLIDO ({len(failures)}):")
        for x in failures:
            print(f"    - {x}")
        return 1
    print("  RESULTADO OK · vectores conocidos reproducidos")
    print("  NOTA: comprueba forma y self-test. NO comprueba la verdad del dato.")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog=NAME,
                                 description="Audita el contrato de las herramientas.")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dir", default="tools")
    ap.add_argument("--no-run", action="store_true",
                    help="no ejecutar los self-test (solo sintaxis y marcas)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    d = os.path.abspath(args.dir)
    if not os.path.isdir(d):
        print(f"ERROR  no existe {d}", file=sys.stderr)
        return 2
    files = sorted(os.path.join(d, f) for f in os.listdir(d)
                   if f.endswith(".py") and not f.startswith("_"))
    # Este fichero se excluye a si mismo del recuento de conformes.
    rows = [audit(f, run=not args.no_run) for f in files]
    rows = [r for r in rows if r["tool"] != os.path.basename(__file__)]
    if args.json:
        print(json.dumps({"tool": NAME, "version": VERSION, "results": rows},
                         indent=2, ensure_ascii=False))
        return 0
    print(render(rows))
    bloqueantes = [r for r in rows if r["severity"] == "BLOQUEANTE"]
    return 1 if bloqueantes else 0


if __name__ == "__main__":
    sys.exit(main())
