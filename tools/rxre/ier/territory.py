#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE · IER · TERRITORY — territorio tecnológico de una entrada desconocida.

Recibe una ruta (proyecto, archivo, directorio) y devuelve un contrato
estructurado (input/artifacts/technologies/dependencies/relationships/
available_tools/hypotheses/evidence/unknowns/epistemic_status).

Reglas de honestidad:
- Extensión jamás es prueba suficiente; cada detección conserva el método.
- Dependencias declaradas ≠ instaladas.
- Herramienta instalada ≠ integrada (se consulta el registry real de backends).
- Nada se inventa: lo que no se puede demostrar va a `unknowns`.

No ejecuta herramientas de análisis; jamás tocar datos sensibles ni hardware.
"""
from __future__ import annotations

import hashlib
import os
import re
import struct
from typing import Any, Dict, List, Optional, Tuple

MAX_FILES = 800
MAX_BYTES = 256 * 1024
SKIP_DIRS = {".git", "node_modules", "target", "build", "dist", "__pycache__",
             ".venv", "venv", ".tox", ".cargo", ".gradle", "out", ".next"}

# ---------------------------------------------------------------- firmas
def _read_head(path: str, n: int = 64) -> bytes:
    with open(path, "rb") as fh:
        return fh.read(n)

def _sig_format(path: str) -> Optional[Dict[str, Any]]:
    try:
        head = _read_head(path, 64)
    except OSError:
        return None
    if head.startswith(b"\x7fELF"):
        cls = {1: "32-bit", 2: "64-bit"}.get(head[4], "unknown")
        endian = "little" if head[5] == 1 else ("big" if head[5] == 2 else "unknown")
        endian_magic = "<H" if endian == "little" else ">H"
        try:
            machine = struct.unpack_from(endian_magic + "H", head, 18)[0]
            arch = {0x03: "i386", 0x3e: "x86-64", 0xb7: "aarch64",
                    0x28: "arm", 0xa3: "loongarch64", 0xf3: "riscv64", 0xf4: "riscv64",
                    0xa9: "aarch64"}.get(machine, "machine=0x%x" % machine)
        except struct.error:
            arch = "unknown"
        return {"kind": "elf", "arch": arch, "class": cls, "endian": endian,
                "confidence": "high", "method": "magic:ELF (bytes 0-4)"}
    if head.startswith(b"%PDF"):
        return {"kind": "pdf", "confidence": "high", "method": "magic:%PDF"}
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return {"kind": "png", "confidence": "high", "method": "magic:PNG"}
    if head.startswith(b"SQLite format 3\x00"):
        return {"kind": "sqlite3-database", "confidence": "high",
                "method": "magic:SQLite format 3"}
    if head.startswith(b"PK\x03\x04") or head.startswith(b"PK\x05\x06"):
        return {"kind": "zip-compatible", "confidence": "high", "method": "magic:PK"}
    if head.startswith(b"\x03\x02\x23\x07"):
        return {"kind": "spirv-binary", "confidence": "high", "method": "magic:SPIRV (word 0)"}
    if head.startswith(b"\xca\xfe\xba\xbe") or head.startswith(b"\xfe\xed\xfa\xce") or head.startswith(b"\xfe\xed\xfa\xcf") or head.startswith(b"\xce\xfa\xed\xfe") or head.startswith(b"\xcf\xfa\xed\xfe"):
        return {"kind": "mach-o-apple", "confidence": "high", "method": "magic:Mach-O"}
    if head[:2] == b"MZ":
        try:
            with open(path, "rb") as fh:
                fh.seek(0x3c)
                e_lfanew = int(fh.read(4)[0:4].hex(), 16) if False else 0
                fh.seek(0x3c)
                e_lfanew = int.from_bytes(fh.read(4), "little")
                fh.seek(e_lfanew)
                pe = fh.read(4)
            return {"kind": "pe-windows" if pe.startswith(b"PE\x00\x00") else "mz-dos",
                    "confidence": "high" if pe.startswith(b"PE\x00\x00") else "medium",
                    "method": "magic:MZ+PE"}
        except OSError:
            return {"kind": "mz-dos", "confidence": "medium", "method": "magic:MZ"}
    if b"#!" == head[:2]:
        first = head.split(b"\n", 1)[0].decode("utf-8", "ignore")
        interp = first[2:].strip().split("/")[-1].split()[0] if len(first) > 2 else "unknown"
        return {"kind": "text/script", "interpreter": interp, "confidence": "high",
                "method": "shebang:%s" % interp}
    if all(32 <= b < 127 or b in (9, 10, 13) for b in head[:48]):
        return {"kind": "text", "confidence": "low", "method": "printable-prefix(<=48B)"}
    return None

# ---------------------------------------------------------------- extensiones (nunca prueba final)
EXT_TECH = {
    ".py": ("python", 0.4), ".pyw": ("python", 0.4), ".pyx": ("cython", 0.5),
    ".c": ("c", 0.4), ".h": ("c", 0.3), ".cpp": ("cpp", 0.4), ".cc": ("cpp", 0.4),
    ".cxx": ("cpp", 0.4), ".hpp": ("cpp", 0.3), ".rs": ("rust", 0.4),
    ".go": ("go", 0.4), ".java": ("java", 0.4), ".kt": ("kotlin", 0.4),
    ".js": ("javascript", 0.4), ".ts": ("typescript", 0.4), ".mjs": ("javascript", 0.3),
    ".sh": ("shell", 0.4), ".bash": ("shell", 0.4), ".zsh": ("shell", 0.4),
    ".asm": ("assembly", 0.3), ".s": ("assembly", 0.3), ".S": ("assembly", 0.3),
    ".spv": ("spirv-assembly", 0.8), ".bc": ("llvm-ir", 0.5),
    ".glsl": ("glsl", 0.7), ".hlsl": ("hlsl", 0.7), ".wgsl": ("wgsl", 0.7),
    ".cu": ("cuda", 0.6), ".cmake": ("cmake", 0.5), ".gradle": ("gradle", 0.6),
}

MANIFESTS = {
    "cargo.toml": ("cargo", "rust", "rust-project"),
    "pyproject.toml": ("pyproject", "python", "python-packaging"),
    "setup.py": ("setuptools", "python", "python-packaging"),
    "setup.cfg": ("setuptools", "python", "python-packaging"),
    "requirements.txt": ("pip-requirements", "python", "python-dependencies"),
    "package.json": ("npm", "javascript", "javascript-packaging"),
    "go.mod": ("gomod", "go", "go-project"),
    "pom.xml": ("maven", "java", "java-project"),
    "build.gradle": ("gradle", "java/kotlin", "jvm-project"),
    "cmakelists.txt": ("cmake", "c/cpp", "cpp-build-system"),
    "makefile": ("make", "c/cpp", "make-build-system"),
    "meson.build": ("meson", "c/cpp", "meson-build-system"),
    "build.bazel": ("bazel", "polyglot", "bazel-build-system"),
    "flake.nix": ("nix", "polyglot", "nix-flake"),
    "dockerfile": ("docker", "polyglot", "container"),
    ".gitmodules": ("git", "vcs", "git-submodules"),
    "sconstruct": ("scons", "polyglot", "scons-build-system"),
    "tsconfig.json": ("typescript", "javascript", "typescript-config"),
}

IMPORT_RULES = [
    (re.compile(r"^\s*import\s+([a-zA-Z_][\w.]*)"), "python-import"),
    (re.compile(r"^\s*from\s+([a-zA-Z_][\w.]*)\s+import"), "python-import"),
    (re.compile(r"^\s*use\s+([a-zA-Z_][\w:]*)"), "rust-use"),
    (re.compile(r"^\s*#include\s*[<\"]([\w./-]+)"), "c-include"),
    (re.compile(r"^\s*package\s+([\w.]+)"), "go/java-package"),
    (re.compile(r"^\s*const\s+\w+\s*=\s*require\(['\"]([\w./-]+)"), "js-require"),
    (re.compile(r"^\s*import\s+.*?from\s+['\"]([\w./@-]+)"), "js/ts-import"),
]

def _analyze_text_sample(path: str) -> List[Dict[str, Any]]:
    out = []
    try:
        with open(path, "rb") as fh:
            data = fh.read(MAX_BYTES)
    except OSError:
        return out
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return out
    lines = text.splitlines()[:400]
    for i, line in enumerate(lines, 1):
        for rx, kind in IMPORT_RULES:
            m = rx.match(line)
            if m:
                out.append({"line": i, "kind": kind, "module": m.group(1),
                            "evidence": "%s:%d  %s" % (os.path.basename(path), i, line.strip()[:120])})
    return out

# ---------------------------------------------------------------- recorrido
def _iter_files(root: str, limit: int = MAX_FILES):
    try:
        st = os.lstat(root)
    except OSError:
        return
    if os.path.isfile(root):
        yield root
        return
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.isdigit()]
        for fn in sorted(filenames):
            if count >= limit:
                return
            yield os.path.join(dirpath, fn)
            count += 1

def _sha256_file(path: str) -> Optional[str]:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None

# ---------------------------------------------------------------- backends disponibles (consulta estado real)
def _available_tools() -> List[Dict[str, Any]]:
    tools = []
    candidates = [
        ("rizin", "/usr/bin/rizin", "binary.cfg"),
        ("radare2", "/usr/bin/radare2", "binary.cfg"),
        ("objdump", "/usr/bin/objdump", None),
        ("readelf", "/usr/bin/readelf", None),
        ("gdb", "/usr/bin/gdb", None),
        ("gcc", "/usr/lib64/ccache/gcc", None),
        ("z3", "/home/lucas/.local/bin/z3", None),
        ("bwrap", "/usr/bin/bwrap", None),
        ("spirv-val", "/usr/bin/spirv-val", None),
        ("spirv-dis", "/usr/bin/spirv-dis", None),
        ("spatch", "/usr/bin/spatch", None),
    ]
    import_modules = [("capstone", None), ("angr", None), ("z3", None)]
    for name, path, note in candidates:
        tools.append({"tool": name, "present": os.path.exists(path) if path else False,
                      "level": "AVAILABLE" if path and os.path.exists(path) else "MISSING",
                      "note": note})
    for name, _ in import_modules:
        try:
            mod = __import__(name)
            ver = getattr(mod, "__version__", getattr(mod, "get_version_string", lambda: "unknown")())
            tools.append({"tool": name, "present": True, "level": "IMPORTED", "note": str(ver)})
        except Exception as e:
            tools.append({"tool": name, "present": False, "level": "MISSING",
                          "note": "%s: %s" % (type(e).__name__, e)})
    # INTEGRADOS reales: consultar el registry de RXRE si se puede importar
    try:
        import sys
        if "backends.registry" not in sys.modules:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))
        import backends.registry as _reg
        for bid, data in _reg.backends().items():
            caps = data.get("capacities", {})
            integrated = sorted(caps)
            tools.append({"tool": "rxre-backend:%s" % bid, "present": True,
                          "level": "INTEGRATED", "note": (",".join(integrated[:6]) + (",..." if len(integrated) > 6 else "") if integrated else "sin capacidades medidas")})
    except Exception as e:
        tools.append({"tool": "rxre-backend:registry", "present": False,
                      "level": "NOT_DETERMINED",
                      "note": "%s: %s" % (type(e).__name__, e)})
    return tools

def reconocer(path: str) -> Dict[str, Any]:
    """Contrato de territorio para `path` (archivo o directorio)."""
    artifacts: List[Dict[str, Any]] = []
    technologies: List[Dict[str, Any]] = []
    dependencies: List[Dict[str, Any]] = []
    relationships: List[Dict[str, Any]] = []
    evidence: List[Dict[str, Any]] = []
    hypothesis: List[str] = []
    unknowns: List[str] = []

    def add_evidence(path_rel: str, method: str, finding: str, strength: str):
        evidence.append({"path": path_rel, "method": method,
                         "finding": finding, "strength": strength})

    if not os.path.exists(path):
        return {
            "input": path,
            "artifacts": [], "technologies": [], "dependencies": [],
            "relationships": [], "available_tools": _available_tools(),
            "hypotheses": [],
            "evidence": [],
            "unknowns": ["path not found: %s" % path],
            "epistemic_status": "BLOCKED",
        }

    is_dir = os.path.isdir(path)
    files = list(_iter_files(path))
    base = path if is_dir else os.path.dirname(path)

    tech_by_id: Dict[str, Dict[str, Any]] = {}

    def mark(tech_id: str, kind: str, methods: List[str], confidence: float,
             first_seen: Optional[str] = None, strength: str = "medium"):
        entry = tech_by_id.setdefault(tech_id, {
            "id": tech_id, "kind": kind, "confidence": 0.0,
            "methods": [], "seen_files": [],
        })
        entry["kind"] = kind or entry["kind"]
        entry["confidence"] = max(entry["confidence"], confidence)
        for m in methods:
            if m not in entry["methods"]:
                entry["methods"].append(m)
        if first_seen and first_seen not in entry["seen_files"] and len(entry["seen_files"]) < 12:
            entry["seen_files"].append(first_seen)
        entry["strength"] = "high" if entry["confidence"] >= 0.8 else (
            "medium" if entry["confidence"] >= 0.5 else "low")

    # --- primera pasada: firmas y extensión débil de cada archivo (capado)
    for fp in files:
        rel = os.path.relpath(fp, base)
        sig = _sig_format(fp)
        if sig:
            artifacts.append({"path": rel, "type": sig["kind"], "confidence": sig["confidence"]})
            add_evidence(rel, sig["method"], sig["kind"], sig["confidence"])
            if sig["kind"] == "elf":
                mark("elf-%s" % sig["arch"], "binary-format",
                     [sig["method"]], 0.95 if sig["confidence"] == "high" else 0.7, rel)
                mark("architecture:%s" % sig["arch"], "architecture",
                     [sig["method"]], 0.9 if sig["confidence"] == "high" else 0.6, rel)
            elif sig["kind"] == "spirv-binary":
                mark("spirv", "spirv-binary-format", [sig["method"]], 0.95, rel)
                mark("gpu-program", "gpu-compute-shader", [sig["method"]], 0.8, rel)
            elif sig["kind"] == "sqlite3-database":
                mark("sqlite3", "database", [sig["method"]], 0.95, rel)
            elif sig["kind"] in ("pdf", "png", "zip-compatible", "mach-o-apple",
                                 "pe-windows", "mz-dos", "text/script", "text"):
                mark(sig["kind"], "format", [sig["method"]], 0.8 if sig["confidence"] == "high" else 0.4, rel)
            ext = os.path.splitext(fp)[1].lower()
            entry = EXT_TECH.get(ext)
            if entry:
                tech_id, conf = entry
                # la extensión sola es señal débil: se registra con confianza baja,
                # nunca como prueba fuerte ni como única evidencia.
                mark(tech_id, "language-by-extension", ["extension:%s" % ext], 0.25, rel, "low")
        if not sig:
            ext = os.path.splitext(fp)[1].lower()
            entry = EXT_TECH.get(ext)
            if entry:
                tech_id, conf = entry
                mark(tech_id, "language-by-extension", ["extension:%s" % ext], conf, rel,
                     "low")
                if conf >= 0.5:
                    artifacts.append({"path": rel, "type": "source:%s" % tech_id,
                                      "confidence": "medium"})
            else:
                artifacts.append({"path": rel, "type": "unknown", "confidence": "n/a"})
        # manifiestos → tecnología a alta confianza de formato, pero solo como declara
        base_name = os.path.basename(fp).lower()
        man = MANIFESTS.get(base_name)
        if man:
            tool, env, kind = man
            sha = _sha256_file(fp) or ""
            mark("build-system:%s" % tool, kind,
                 ["manifest:%s" % base_name, "sha256:%s" % sha[:16]],
                 0.85, rel, "high")
            add_evidence(rel, "manifest:%s" % base_name,
                         "declarado: %s" % kind, "high")
            dependencies.append({"path": rel, "tool": tool, "kind": kind,
                                 "state": "declared"})

    # --- segunda pasada: pistas de contenido; NO prueba de lenguaje sin soporte
    for fp in files[:300]:
        rel = os.path.relpath(fp, base)
        try:
            with open(fp, "rb") as fh:
                head = fh.read(MAX_BYTES)
            if len(head) == 0 or b"\x00" in head[:512]:
                continue  # binario
        except OSError:
            continue
        findings = _analyze_text_sample(fp)
        for f in findings:
            add_evidence(rel, f["kind"], f["module"], "medium")
            if f["kind"] == "python-import":
                mark("python", "language", ["import:%s" % f["module"]], 0.7, rel)
            elif f["kind"] == "rust-use":
                mark("rust", "language", ["use:%s" % f["module"]], 0.7, rel)
            elif f["kind"] == "c-include":
                mark("c/cpp", "language", ["include:%s" % f["module"]], 0.6, rel)
            elif f["kind"] in ("js-require", "js/ts-import"):
                mark("javascript/typescript", "language", ["import:%s" % f["module"]], 0.5, rel)

    # --- relaciones archivo→manifiesto (el propio manifiesto y su árbol)
    seen_rel = set()
    for a in artifacts:
        ap = a["path"]
        root_dir = os.path.dirname(ap)
        for d in dependencies:
            ddir = os.path.dirname(d["path"])
            if ap == d["path"] or (ddir == "" and True) or (root_dir == ddir) or (root_dir.startswith(ddir + "/") if ddir else False):
                key = (ap, d["path"])
                if key in seen_rel:
                    continue
                seen_rel.add(key)
                relationships.append({"from": ap, "to": d["path"],
                                      "relation": "declared-by-build-system" if ap != d["path"]
                                      else "self-manifest"})
    # relación mutua entre manifiestos de ecosistemas (solo contabilidad)
    if len(dependencies) >= 2:
        for i in range(len(dependencies)):
            for j in range(i + 1, len(dependencies)):
                a, b = dependencies[i], dependencies[j]
                if os.path.dirname(a["path"]) == os.path.dirname(b["path"]):
                    key = (a["path"], b["path"], "coexists-with")
                    if key not in seen_rel:
                        seen_rel.add(key)
                        relationships.append({"from": a["path"], "to": b["path"],
                                              "relation": "coexists-with"})

    # capacidades conocidas por artefacto/plataforma (honestidad: solo disponibilidad/integración, no ejecución)
    available_tools = _available_tools()

    for tid, t in tech_by_id.items():
        technologies.append(t)
    technologies.sort(key=lambda t: t["confidence"], reverse=True)

    if not technologies:
        unknowns.append("no se detectó territorio reconocible; extensión desconocida o contenido inobservable")

    # contradicciones: múltiples manifiestos de ecosistemas distintos declarados
    ecosystems = {t["id"].split(":", 1)[-1] for t in technologies if t["id"].startswith("build-system:")}
    if len(ecosystems) > 1:
        hypothesis.append("Manifiestos de ecosistemas distintos conviven (%s) — puede ser monorepo legítimo o manifiestos residuales/contradictorios." % sorted(ecosystems))
        unknowns.append("¿monorepo, multi-package o manifiesto contradictor?: no resoluble con evidencia de lectura")

    # arquitectura prometida por manifests tipo Cargo/CMake sin triple real: no inventar
    arch_entries = [t for t in technologies if t["kind"] == "architecture"]
    if not arch_entries:
        if any(t["id"].startswith("build-system:") for t in technologies):
            hypothesis.append("proyecto compilable sin arquitectura de destino declarada localmente; no se fija CPU")

    return {
        "input": path,
        "artifacts": artifacts[:40],
        "technologies": technologies,
        "dependencies": dependencies,
        "relationships": relationships[:100],
        "available_tools": available_tools,
        "hypotheses": hypothesis,
        "evidence": evidence[:120],
        "unknowns": unknowns,
        "epistemic_status": "PARTIAL",
    }

# ====================================================================
# MENSAJE 3 — INTELIGENCIA OPERATIVA DE HERRAMIENTAS
# Niveles: DISCOVERED → AVAILABLE → INTEGRATED → INVOCABLE → EXECUTED → VERIFIED
# Nada se eleva sin evidencia propia. Cada herramienta corre readonly.
# ====================================================================

import subprocess

_LEVEL_ORDER = ["DISCOVERED", "AVAILABLE", "INTEGRATED", "INVOCABLE", "EXECUTED", "VERIFIED"]
_DECISIONS = ("UTILIZAR", "COMBINAR", "EXTENDER", "REPARAR", "SUSTITUIR", "BLOQUEAR")

def _run_readonly(cmd: List[str], timeout: int = 20) -> Dict[str, Any]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {"rc": p.returncode, "stdout": p.stdout, "stderr": p.stderr[-2000:],
                "command": cmd}
    except subprocess.TimeoutExpired:
        return {"rc": -99, "stdout": "", "stderr": "timeout %ds" % timeout,
                "command": cmd}
    except OSError as e:
        return {"rc": -98, "stdout": "", "stderr": "%s: %s" % (type(e).__name__, e),
                "command": cmd}

def _expect(name: str, matches: bool, evidence: str) -> Dict[str, Any]:
    return {"check": name, "matched": bool(matches), "evidence": evidence}


def _parse_elf_text_section(path: str) -> Optional[bytes]:
    """Extrae el segmento .text (x86-64 ELF) sin dependencias externas."""
    try:
        with open(path, "rb") as fh:
            data = fh.read()
        if data[:4] != b"\x7fELF" or data[4] != 2:  # solo ELF64 para este fixture
            return None
        is_le = data[5] == 1
        fmt = "<" if is_le else ">"
        e_shoff = struct.unpack_from(fmt + "Q", data, 0x28)[0]
        e_shentsize = struct.unpack_from(fmt + "H", data, 0x3a)[0]
        e_shnum = struct.unpack_from(fmt + "H", data, 0x3c)[0]
        e_shstrndx = struct.unpack_from(fmt + "H", data, 0x3e)[0]

        def sh(idx):
            base = e_shoff + idx * e_shentsize
            return {
                "name": struct.unpack_from(fmt + "I", data, base)[0],
                "type": struct.unpack_from(fmt + "I", data, base + 4)[0],
                "offset": struct.unpack_from(fmt + "Q", data, base + 0x18)[0],
                "size": struct.unpack_from(fmt + "Q", data, base + 0x20)[0],
            }
        shstr = sh(e_shstrndx)
        for i in range(e_shnum):
            s = sh(i)
            name_off = shstr["offset"] + s["name"]
            name = data[name_off:data.index(b"\x00", name_off)].decode("utf-8", "ignore")
            if name == ".text":
                return data[s["offset"]: s["offset"] + s["size"]]
        return None
    except (OSError, struct.error):
        return None


def verificar_herramientas(fixture_dir: Optional[str] = None,
                           gcc: str = "/usr/lib64/ccache/gcc") -> Dict[str, Any]:
    """Verifica herramientas reales sobre fixtures desechables.

    Contrasta cada herramienta con expectativas independientes. Ninguna
    herramienta se eleva a VERIFIED sin un check con expectativa ajena al
    propio tool (p.ej. 42=0x2a en el desarmado, símbolo `main` visible,
    SPIR-V universalmente aceptado y rechazado por mágic corrupta).
    """
    import tempfile, shutil
    base = fixture_dir or tempfile.mkdtemp(prefix="rxre-toolintel-")
    os.makedirs(base, exist_ok=True)
    fixture_c = os.path.join(base, "demo.c")
    fixture_elf = os.path.join(base, "demo.elf")
    fixture_shader = os.path.join(base, "mini.comp")
    fixture_spv = os.path.join(base, "mini.spv")
    fixture_bad_spv = os.path.join(base, "bad.spv")
    with open(fixture_c, "w", encoding="utf-8") as fh:
        fh.write("int main(void){ return 42; }\n")
    with open(fixture_shader, "w", encoding="utf-8") as fh:
        fh.write("#version 450\nlayout(local_size_x = 1) in;\nvoid main() {}\n")
    with open(fixture_bad_spv, "wb") as fh:
        fh.write(b"\xde\xad\xbe\xef" + b"\x00" * 60)
    tools: List[Dict[str, Any]] = []

    def finalize(tool, level, invocation, expected, checks, capabilities,
                 limitations=None, decision="BLOQUEAR", fingerprint=None):
        tools.append({
            "tool": tool,
            "level": level,
            "invocation": invocation,
            "fixture": fingerprint,
            "expected": expected,
            "checks": checks,
            "capabilities": capabilities,
            "limitations": limitations or [],
            "decision": decision,
        })

    # gcc: construye el fixture (entrada conocida) — evidencia de compilación real
    built = _run_readonly([gcc, "-O0", "-o", fixture_elf, fixture_c])
    exit_rc = built["rc"]
    sha = _sha256_file(fixture_elf) if exit_rc == 0 else None
    finalize("gcc",
             "EXECUTED" if exit_rc == 0 else "DISCOVERED",
             "gcc -O0 -o demo.elf demo.c",
             "compila sin warnings a ELF",
             [_expect("compile", exit_rc == 0, "rc=%d stderr=%s" % (exit_rc, built["stderr"][:200]))],
             ["compila C a ELF (fixture local)"] if exit_rc == 0 else [],
             limitations=["solo para fixtures locales; no forma parte del camino runtime de RXRE"],
             decision="UTILIZAR" if exit_rc == 0 else "BLOQUEAR",
             fingerprint=sha)

    # readelf: expectativa independiente (ELF64, x86-64) sobre el fixture
    rr = _run_readonly(["/usr/bin/readelf", "-h", fixture_elf])
    out = rr["stdout"]
    ok = rr["rc"] == 0 and "ELF64" in out and ("X86-64" in out or "Advanced Micro Devices X86-64" in out)
    finalize("readelf",
             "VERIFIED" if ok else ("EXECUTED" if rr["rc"] == 0 else "AVAILABLE"),
             "readelf -h demo.elf",
             "ELF64, x86-64 (fixture sabido)",
             [_expect("elf-header-class", ok, out.splitlines()[0] if out else "sin salida"),
              _expect("call", rr["rc"] == 0, "rc=%d" % rr["rc"])],
             ["inspección de cabecera ELF (clase/arquitectura)"] if ok else [],
             limitations=["clase ELF sólo del fixture compilado aquí"],
             decision="UTILIZAR" if ok else "BLOQUEAR",
             fingerprint=sha)

    # objdump: expectativa independiente (símbolo `main`)
    od = _run_readonly(["/usr/bin/objdump", "-t", fixture_elf])
    out = od["stdout"]
    has_main = od["rc"] == 0 and "main" in out
    finalize("objdump",
             "VERIFIED" if has_main else ("EXECUTED" if od["rc"] == 0 else "AVAILABLE"),
             "objdump -t demo.elf",
             "símbolo `main` visible (definido en el fixture)",
             [_expect("symbol main", has_main, out[:300].replace("\n", " | "))],
             ["listado de símbolos (tabla de)"] if has_main else [],
             limitations=["sin validación sobre objetos strippados: símbolo ausente no invalida el objeto"],
             decision="UTILIZAR" if has_main else "BLOQUEAR",
             fingerprint=sha)

    # rizin: ejecución real sobre el fixture (sin verificar semánticamente)
    rzn = _run_readonly(["/usr/bin/rizin", "-q", "-c", "aa; aflj", fixture_elf], timeout=30)
    out = rzn["stdout"]
    afl_ok = rzn["rc"] == 0 and '"offset"' in out
    finalize("rizin",
             "EXECUTED" if afl_ok else ("AVAILABLE" if os.path.exists("/usr/bin/rizin") else "DISCOVERED"),
             "rizin -q -c 'aa; aflj' demo.elf",
             "lista JSON de funciones (requiere análisis automático)",
             [_expect("aflj json", afl_ok, out[:400])],
             ["listado de funciones (json) tras aa"] if afl_ok else [],
             limitations=["capacidad semántica NO verificada; confianza derivada deSalida cruda no auditada"],
             decision="UTILIZAR" if afl_ok else "BLOQUEAR",
             fingerprint=sha)

    # glslangValidator: compila shader válido → evidencia positive
    gl = _run_readonly(["/usr/bin/glslangValidator", "-V", "-S", "comp", "-o", fixture_spv, fixture_shader])
    gl_ok = gl["rc"] == 0 and os.path.exists(fixture_spv)
    sha_spv = _sha256_file(fixture_spv) if gl_ok else None
    finalize("glslangValidator",
             "EXECUTED" if gl_ok else "AVAILABLE",
             "glslangValidator -V -S comp -o mini.spv mini.comp",
             "compila GLSL compute → SPIR-V (fixture conocido válido)",
             [_expect("spv emitido", gl_ok, "rc=%d stderr=%s" % (gl["rc"], gl["stderr"][:200]))],
             ["GLSL→SPIR-V compute (fixture)"] if gl_ok else [],
             limitations=["solo shaders triviales sintéticos; sin validación semántica GPU real"],
             decision="UTILIZAR" if gl_ok else "BLOQUEAR",
             fingerprint=sha_spv)

    # spirv-val: contraste positivo Y negativo
    spv_val = _run_readonly(["/usr/bin/spirv-val", fixture_spv]) if gl_ok else {"rc": -1, "stdout": "", "stderr": "sin fixture", "command": []}
    spv_bad = _run_readonly(["/usr/bin/spirv-val", fixture_bad_spv])
    pos = spv_val["rc"] == 0 if gl_ok else False
    neg = spv_bad["rc"] != 0
    finalize("spirv-val",
             "VERIFIED" if (pos and neg) else ("EXECUTED" if spv_val["rc"] == 0 else "AVAILABLE"),
             "spirv-val mini.spv; spirv-val bad.spv",
             "acepta SPIR-V válido; rechaza SPIR-V corrupto",
             [_expect("positive accepts", pos, "rc=%d" % spv_val["rc"]),
              _expect("negative rejects", neg, "rc=%d stderr=%s" % (spv_bad["rc"], spv_bad["stderr"][:120]))],
             ["validación de bien-formación SPIR-V"] if (pos and neg) else [],
             limitations=["valida bien-formación; no semántica ni licensing de shaders"],
             decision="UTILIZAR" if (pos and neg) else "BLOQUEAR",
             fingerprint=sha_spv)

    # capstone (python): expectativa independiente fuerte (42 = 0x2A está en el fixture)
    capstone_check = None
    try:
        import capstone
        text = _parse_elf_text_section(fixture_elf)
        insns = []
        if text:
            md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
            insns = list(md.disasm(text, 0x1000))
        capstone_check = _expect(
            "capstone disasm contains mov eax, 0x2a (return 42)",
            any("0x2a" in i.op_str.lower() for i in insns),
            "capstone %s; instrucciones: %d" % (capstone.__version__, len(insns)))
    except Exception as e:
        capstone_check = _expect("capstone import", False, "%s: %s" % (type(e).__name__, e))
    cap_level = "VERIFIED" if (capstone_check and capstone_check["matched"]) else "IMPORTED"
    finalize("capstone",
             cap_level,
             "capstone (python) sobre .text ELF64",
             "el desarmado contiene mov eax, 0x2a (retorno 42)",
             [capstone_check] if capstone_check else [],
             ["desarmado x86-64 sin ejecutar"] if cap_level == "VERIFIED" else [],
             limitations=["verificación sólo del fixture -O0 linux/x86-64"],
             decision="UTILIZAR" if cap_level == "VERIFIED" else "BLOQUEAR",
             fingerprint=sha)

    # z3: llamada no destructiva; sin juicio semántico
    z3 = _run_readonly(["/home/lucas/.local/bin/z3", "--version"])
    z3_ok = z3["rc"] == 0
    finalize("z3",
             "EXECUTED" if z3_ok else "MISSING",
             "z3 --version",
             "responde con su versión (no prueba capacidad SAT real)",
             [_expect("version", z3_ok, z3["stdout"].strip()[:120])],
             ["consultas SMT-LIB (no verificadas aquí)"] if z3_ok else [],
             decision="COMBINAR" if z3_ok else "BLOQUEAR",
             fingerprint=None)

    # bwrap: --version no destructivo
    bw = _run_readonly(["/usr/bin/bwrap", "--version"])
    bw_ok = bw["rc"] == 0
    finalize("bwrap",
             "EXECUTED" if bw_ok else "AVAILABLE",
             "bwrap --version",
             "versión responde (no prueba aislamiento real)",
             [_expect("version", bw_ok, bw["stdout"].strip()[:120])],
             ["sandboxing bubblewrap (no ejecutado en esta misión)"],
             decision="COMBINAR" if bw_ok else "BLOQUEAR")

    # spatch: --version si está
    sp = _run_readonly(["/usr/bin/spatch", "--version"])
    sp_ok = sp["rc"] == 0
    finalize("spatch",
             "EXECUTED" if sp_ok else "AVAILABLE",
             "spatch --version",
             "versión responde (no prueba aplicación de recetas)",
             [_expect("version", sp_ok, (sp["stdout"] + sp["stderr"]).strip()[:120])],
             ["búsqueda/transformación semántica (no verificada)"] if sp_ok else [],
             decision="COMBINAR" if sp_ok else "BLOQUEAR")

    # angr: import readonly; sin ejecutar análisis
    try:
        import angr as _angr
        angr_ver = getattr(_angr, "__version__", "unknown")
        angr_check = _expect("import angr", True, "angr %s" % angr_ver)
        angr_level = "IMPORTED"
        decision = "BLOQUEAR"
    except Exception as e:
        angr_check = _expect("import angr", False, "%s: %s" % (type(e).__name__, e))
        angr_level = "MISSING"
        decision = "BLOQUEAR"
    finalize("angr", angr_level, "import angr (solo importación)",
             "importable en este entorno (sin pruebas semánticas ejecutadas)",
             [angr_check],
             ["importación sin análisis"] ,
             limitations=["producer NOT_DETERMINED (registry RXRE-004); adormecimiento conocido por hw/env ausentes"],
             decision=decision)

    # comparación rizin vs objdump sobre símbolos (subproblema: listar funciones)
    # comparación sobre el mismo fixture: symbol listing de objdump vs aflj de rizin
    comparison = {
        "subproblem": "listar funciones/símbolos",
        "fixture": sha,
        "rizin_aflj_ok": afl_ok,
        "objdump_rc": rr["rc"],
        "overlap_evidence": [],
        "divergences": [],
    }
    od_out = _run_readonly(["/usr/bin/objdump", "-t", fixture_elf])["stdout"]
    rz_out = _run_readonly(["/usr/bin/rizin", "-q", "-c", "aa; aflj", fixture_elf], timeout=30)["stdout"]
    od_has = "main" in od_out
    rz_has = "main" in rz_out
    comparison["overlap_evidence"].append({"tool": "objdump", "finds_main": od_has})
    comparison["overlap_evidence"].append({"tool": "rizin", "finds_main": rz_has})
    if od_has and rz_has:
        comparison["divergences"].append("coinciden en detectar `main`; nada se audita en conteos ni offsets (M3: solo existencia y comportamiento)")
    if od_has and not rz_has:
        comparison["divergences"].append("objdump trae `main` en su tabla pero el aflj de rizin no lo trae; invocación o salida no auditadas")

    return {
        "fixture_dir": base,
        "fixture_sha256": sha,
        "tools": tools,
        "comparison": comparison,
        "note": "FIJEZAS desechables en /tmp; ejecuciones readonly; sin GPU/MMIO/red",
    }
