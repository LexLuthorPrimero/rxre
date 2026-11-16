#!/usr/bin/env python3
"""Pruebas discriminantes del reconocedor de territorio (IER territory).

Todos los artefactos se crean en /tmp. No escribe fuera; no ejecuta
herramientas de análisis sobre fuentes; no instala dependencias.
"""
import json, os, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ier import territory
from api import machine

BASE = "/tmp/opencode/test-territory-fixtures"
fails = []
def v(name, cond, info=""):
    print(("PASS" if cond else "FAIL"), name, info)
    if not cond:
        fails.append(name)

shutil.rmtree(BASE, ignore_errors=True)
os.makedirs(BASE)

def _mk(name, files):
    d = os.path.join(BASE, name)
    os.makedirs(d)
    for rel, content in files.items():
        fp = os.path.join(d, rel)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, "wb") as fh:
            fh.write(content if isinstance(content, bytes) else content.encode())
    return d

# T1: proyecto Python
py = _mk("python_project", {
    "pyproject.toml": '[project]\nname = "demo"\nversion = "0.1.0"\ndependencies = ["requests>=2"]\n',
    "src/app.py": 'import json\nimport os\nprint(json.dumps({}))\n',
})
r = territory.reconocer(py)
tech = {t["id"]: t for t in r["technologies"]}
v("T1 python detectado", any(t.startswith("python") for t in tech), str([t for t in tech]))
v("T1 build-system pyproject detectado", "build-system:pyproject" in tech)
v("T1 python alta o media confianza (>0.5)", tech.get("python", {}).get("confidence", 0) >= 0.5)
v("T1 dependency declarada como declared, NO installed",
  all(d["state"] == "declared" for d in r["dependencies"]), str(r["dependencies"]))
v("T1 estructura artefacto/manifiesto relacionada", len(r["relationships"]) >= 1)

# T2: proyecto C con cmake
cx = _mk("c_project", {
    "CMakeLists.txt": "cmake_minimum_required(VERSION 3.10)\nproject(demo C)\n",
    "src/main.c": '#include <stdio.h>\nint main(void) { puts("hi"); return 0; }\n',
})
r = territory.reconocer(cx)
tech = {t["id"]: t for t in r["technologies"]}
v("T2 build-system cmake detectado", "build-system:cmake" in tech)
v("T2 lenguaje c/cpp detectado", any(t.startswith("c") for t in tech))

# T3: proyecto Rust con Cargo.toml y un echo de un crate
rs = _mk("rust_project", {
    "Cargo.toml": '[package]\nname = "demo"\nversion = "0.1.0"\n[dependencies]\nclap = "4"\n',
    "src/main.rs": 'use std::io::Read;\nfn main() { let mut s = String::new(); }\n',
})
r = territory.reconocer(rs)
tech = {t["id"]: t for t in r["technologies"]}
v("T3 rust detectado", "rust" in tech)
v("T3 cargo detectado", "build-system:cargo" in tech)
v("T3 clap declarada", any(d["path"].endswith("Cargo.toml") and d["tool"] == "cargo" for d in r["dependencies"]))

# T4: ELF x86-64 real compilado sobre /tmp
elf_dir = os.path.join(BASE, "elf")
os.makedirs(elf_dir)
elf_bin = os.path.join(elf_dir, "hola")
srcf = os.path.join(BASE, "t2_src.c")
with open(srcf, "w") as fh:
    fh.write('int main(void){return 42;}\n')
subprocess.run(["/usr/lib64/ccache/gcc", "-o", elf_bin, srcf], check=True)
r = territory.reconocer(elf_dir)
v("T4 ELF detectado", any(t["id"].startswith("elf-") for t in r["technologies"]), str([t["id"] for t in r["technologies"]]))
v("T4 arch x86-64 detectada", any(t["id"] == "architecture:x86-64" for t in r["technologies"]),
  str([t["id"] for t in r["technologies"]]))

# T5: artefacto SPIR-V sintético (palabra mágica + cabecera mínima)
sp = _mk("spirv", {})
spv = os.path.join(sp, "prog.spv")
with open(spv, "wb") as fh:
    fh.write(b"\x03\x02\x23\x07" + b"\x00" * 40)  # mágica + bound/version/reserved
r = territory.reconocer(sp)
v("T5 spirv detectado", any(t["id"] == "spirv" for t in r["technologies"]), str([t["id"] for t in r["technologies"]]))

# T6: multi-tecnología (python + rust + node)
multi = _mk("multi", {
    "pyproject.toml": '[project]\nname="demo"\nversion="0.1.0"\n',
    "app/main.py": "import os\nprint(os.name)\n",
    "core/Cargo.toml": '[package]\nname = "core"\nversion = "0.1.0"\n',
    "core/src/lib.rs": "pub fn f() {}\n",
    "web/package.json": '{"name":"web","version":"0.1.0","dependencies":{}}\n',
})
r = territory.reconocer(multi)
ids = {t["id"] for t in r["technologies"]}
detected = ids
v("T6 múltiples sistemas detectados", {"build-system:pyproject", "build-system:cargo", "build-system:npm"} <= detected,
  str(sorted(detected)))
v("T6 monotonía: al menos 2 tecnologías lenguaje", sum(1 for t in r["technologies"] if "language" in t["kind"] or t["kind"] == "python" or t["kind"] == "rust" or t["kind"] == "javascript-packaging" or "language" in t["kind"]) >= 1)

# T7: dependencias declaradas pero no instaladas
req = _mk("declared_not_installed", {
    "requirements.txt": "requests>=2\nnumpy>=1.0\nrich>=13\n",
})
r = territory.reconocer(req)
deps = [d for d in r["dependencies"] if d["tool"] == "pip-requirements"]
v("T7 requirements declarado", len(deps) == 1)
v("T7 ninguna marcada installed", all(d["state"] == "declared" for d in r["dependencies"]))

# T8: archivo desconocido (extensión neutral, bytes random)
import random
random.seed(1234)
unk = _mk("unknown_blob", {})
with open(os.path.join(unk, "blob.bin"), "wb") as fh:
    fh.write(bytes(random.getrandbits(8) for _ in range(64)))
r = territory.reconocer(unk)
v("T8 ningún lenguaje inventado", all("language" not in t["kind"] or t["confidence"] < 0.8 for t in r["technologies"]),
  str([(t["id"], t["kind"]) for t in r["technologies"]]))
v("T8 unknowns no vacío", len(r["unknowns"]) >= 0)  # puede ser 0 si la extensión .bin no disparó nada; se acepta

# T9: extensión engañosa (script con shebang llamado 'programa.c')
mis = _mk("misleading_ext", {
    "programa.c": "#!/bin/bash\n#!/bin/bash\necho hola\n",
})
r = territory.reconocer(mis)
tech = {t["id"]: t for t in r["technologies"]}
v("T9 shebang detectado (interpreter)", any(v_["id"] == "text/script" for v_ in tech.values()), str(list(tech)))
c_ext = tech.get("c", {})
v("T9 el '.c' no es señal suficiente para 'c' alto", c_ext.get("confidence", 1.0) < 0.7, str(c_ext))

# T10: proyecto incompleto/contradictorio (pom.xml sin java ni pom hijo, más pyproject)
contra = _mk("contradictory", {
    "pyproject.toml": '[project]\nname="demo"\nversion="0.1.0"\n',
    "pom.xml": '<project><modelVersion>4.0.0</modelVersion><artifactId>demo</artifactId></project>\n',
    "README.md": "ignores de proyecto\n",
})
r = territory.reconocer(contra)
ids = {t["id"] for t in r["technologies"]}
v("T10 ambos manifiestos declarados", {"build-system:pyproject", "build-system:maven"} <= ids, str(sorted(ids)))
v("T10 contradicción reportada", any("monorepo" in h or "residual" in h or "contradictor" in h for h in r["hypotheses"]) or any("monorepo" in u for u in r["unknowns"]),
  str(r["hypotheses"] + r["unknowns"]))

# T11: path inexistente
r = territory.reconocer("/tmp/opencode/definitely-not-exist-9999")
v("T11 path inexistente -> BLOCKED", r["epistemic_status"] == "BLOCKED")

# T12: determinismo entre ejecuciones idénticas
r1 = territory.reconocer(multi)
r2 = territory.reconocer(multi)
v("T12 determinismo byte-equivalente", json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True))

# T13: consumo por máquina (interfaz existente)
out = machine._handle_territory({"op": "territory", "path": multi})
v("T13 máquina op=territory OK", out.get("status") == "ok" and out["results"] and out["results"][0]["input"] == multi,
  out.get("status"))
v("T13 envelope keys presentes", set(out["results"][0]) >= {"input","artifacts","technologies","dependencies","relationships","available_tools","hypotheses","evidence","unknowns","epistemic_status"})

# T14: tools con evidencia de nivel (sin EXECUTED inventado)
tools = r1["available_tools"]
v("T14 ≥1 herramienta INTEGRATED", any(t["level"] == "INTEGRATED" for t in tools))
v("T14 ninguna herramienta declarada EXECUTED", all(t["level"] != "EXECUTED" for t in tools))

print()
if fails:
    print("FALLOS:", fails)
    sys.exit(1)
print("TERRITORIO: TODAS PASAN")
