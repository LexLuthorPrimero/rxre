#!/usr/bin/env python3
"""RXRE -- angr #7294 / M9: regresion sincronizada con el contrato A3 definitivo.

Contrato de decision:
   PRESERVE_SCALAR   decision conservative when scalar use of the candidate region is proven.
   SAFE_TO_TRANSFORM autorizacion para la transformacion concreta cuando no hay evidencia escalar.
   ABSTAIN            cuando el control o la procedencia no pueden resolverse con seguridad.

      A3 definitivo (M7):
        - Un Store opaco intermedio no fuerza ABSTAIN automaticamente: NO es una lectura, NO
          demuestra solape con el objeto seguido, y el analisis puede continuar; la posicion
          del Store opaco debe conservarse y el fold solo se autoriza si preserva
          ByteEquivalent y OrderPreserved y AliasSafe.
        - Assignment con destino stack-vvar de offset o ancho desconocido -> ABSTAIN.
        - R2 cross-block: successors scan without shrink; graph unusable -> ABSTAIN.

      Invariante de independencia:
        Esta prueba NO llama a _scalar_use_decision ni a ningun helper privado de decision de
        angr para calcular el resultado esperado. Los oraculos son:
          (a) texto recuperado por el decompilador (subprocess aislado),
          (b) ejecucion nativa de fixtures compilados con gcc (ctypes) como oraculo semantico,
          (c) crosscheck con presets distintos.

      Si RXRE_ANGR_7294_SOURCE no esta definido o no apunta a un clon valido del angr reparado,
      la prueba imprime SKIP y sale 0 (comportamiento historico conservado).

Fixtures generados durante la prueba (directorio temp):
   - amd64_fixture.c      -> compilado con gcc; usado para oraculo nativo
   - two_block.c           -> gcc; rama con lectura del objeto escalar en sucesor
   - barrier_fixture.s     -> gcc -c; barrera con store opaco de registro
Nada se instalangaj; nada se muta fuera del directorio temporal.
"""
from __future__ import annotations

import ctypes
import hashlib
import os
import subprocess
import sys
import tempfile
import shutil

here = os.path.dirname(os.path.abspath(__file__))
MASTER = os.environ.get("RXRE_ANGR_7294_SOURCE", "")

FAILS = []
n = 0
DET = []


def v(name, cond, det=""):
    global n
    n += 1
    if not cond:
        FAILS.append("%s %s" % (name, det))


def box(title):
    print("=" * 78)
    print(title)
    print("=" * 78)


def patch_clone_ok(src):
    f = os.path.join(src, "angr", "analyses", "decompiler", "optimization_passes", "inlined_strcpy_simplifier.py")
    if not os.path.isfile(f):
        return False, "simplifier file missing"
    try:
        data = open(f, "rb").read()
        magic = b"_successor_evidence"
        if magic not in data:
            return False, "expected marker _successor_evidence not present (not the M6/M7 repaired clone)"
        if b"_ScalarUseFinder" not in data:
            return False, "missing _ScalarUseFinder (layer expected from M4+)"
        return True, "markers found"
    except Exception as e:
        return False, "open error: %r" % (e,)


def subproc(args, timeout=120):
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def decompile_shellcode(shell_hex, arch, preset, entry=0x400000):
    snippet = (
        "import sys\n"
        "src = %r\n"
        "sys.path.insert(0, src)\n"
        "import angr\n"
        "p = angr.load_shellcode(bytes.fromhex(%r), arch=%r, load_address=%d)\n"
        "p.analyses.CFGFast(normalize=True)\n"
        "p.analyses.CompleteCallingConventions(workers=0)\n"
        "fxn = p.kb.functions[0x400000]\n"
        "r = p.analyses.Decompiler(fxn, preset=%r)\n"
        "print(r.codegen.text if r.codegen else '')\n" % (MASTER, shell_hex, arch, entry, preset)
    )
    return subproc([sys.executable, "-c", snippet])


def decompile_project(project_path, func_name, preset="malware"):
    snippet = (
        "import sys\n"
        "src = %r\n"
        "sys.path.insert(0, src)\n"
        "import angr\n"
        "proj = angr.Project(%r, auto_load_libs=False)\n"
        "proj.analyses.CFGFast(normalize=True)\n"
        "proj.analyses.CompleteCallingConventions(workers=0)\n"
        "fxn = next(f for f in proj.kb.functions.values() if f.name == %r)\n"
        "r = proj.analyses.Decompiler(fxn, preset=%r)\n"
        "print(r.codegen.text if r.codegen else '')\n" % (MASTER, project_path, func_name, preset)
    )
    return subproc([sys.executable, "-c", snippet])


def expected_scalar_preserved(text: str) -> bool:
    return (
        "unsigned" in text.lower()
        and "v0" in text
        and "741158447" in text
        and "strncpy" not in text
        and "char v0[" not in text
    )


def expect_fold_preserved(text: str) -> bool:
    # legitimate strings must continue to be optimized by the simplifier
    return ("strncpy" in text and "v0[" in text)


def main():
    box("RXRE ANGR-7294 M9 regression (A3 definitivo)")
    if not MASTER or not os.path.isfile(os.path.join(MASTER, "angr", "__init__.py")):
        print("SKIP: RXRE_ANGR_7294_SOURCE does not point to a valid angr source checkout")
        return 0

    ok, msg = patch_clone_ok(MASTER)
    v("repaired clone provides _ScalarUseFinder/_successor_evidence", ok, msg)

    # Test directories (append-only; removed at the end via finally)
    tmpdir = tempfile.mkdtemp(prefix="rxre-m9-")

    # ---------------------------------------------------------------
    # Test 1: original x86 fixture under all presets
    # ---------------------------------------------------------------
    FIXTURE_HEX = "83ec04c704242f2e2d2c8b042483c404c3"
    for preset in ["malware", "basic", "fast", "full"]:
        rc, out, err = decompile_shellcode(FIXTURE_HEX, "x86", preset)
        v("x86 #7294 preset=%s: rc==0" % preset, rc == 0, "stderr=%r" % err[:200])
        v("x86 #7294 preset=%s: scalar preserved" % preset, expected_scalar_preserved(out), out[:200])
        v("x86 #7294 preset=%s: no char v0[" % preset, "char v0[" not in out)
        v("x86 #7294 preset=%s: no strncpy" % preset, "strncpy" not in out)

    # ---------------------------------------------------------------
    # Test 2: AMD64 variant (amd64 assembly file compiled at test time)
    # ---------------------------------------------------------------
    amd64_c = os.path.join(tmpdir, "amd64_fixture.c")
    amd64_so = os.path.join(tmpdir, "amd64_fixture.so")
    with open(amd64_c, "w") as fh:
        fh.write("#include <stdint.h>\nuint64_t f(void){ volatile uint64_t v = 0x2c2d2e2f; return v; }\n")
    rc, _, err = subproc(["gcc", "-O0", "-fPIC", "-shared", "-o", amd64_so, amd64_c])
    v("test asm fixture fixture-compile rc==0", rc == 0, "stderr=%r" % err[:200])
    if rc == 0:
        rc, out, err = decompile_project(amd64_so, "f")
        v("AMD64 fixture decomp rc==0", rc == 0, "stderr=%r" % err[:200])
        v("AMD64 fixture scalar preserved", expected_scalar_preserved(out), out[:200])
        v("AMD64 fixture no char v0[", "char v0[" not in out)
        # Native oracle
        try:
            lib = ctypes.CDLL(amd64_so)
            fn = lib.f
            fn.restype = ctypes.c_ulonglong
            fn.argtypes = []
            v("native oracle: f()==0x2c2d2e2f", fn() == 0x2c2d2e2f)
        except Exception as e:
            v("native oracle: f() loadable", False, "ctypes_error=%r" % (e,))
    else:
        v("AMD64 fixture skipped (compiler failure)", False)

    # ---------------------------------------------------------------
    # Test 3: Branching two-block (cross-block evidence, R2)
    # ---------------------------------------------------------------
    t2 = os.path.join(tmpdir, "two_block.c")
    t2so = os.path.join(tmpdir, "two_block.so")
    with open(t2, "w") as fh:
        fh.write(
            "unsigned int two_block(unsigned int c){\n"
            "    volatile unsigned int v = 0x2c2d2e2f;\n"
            "    if (c) return v;\n"
            "    return 0;\n"
            "}\n"
        )
    rc, _, err = subproc(["gcc", "-O0", "-fPIC", "-shared", "-o", t2so, t2])
    v("two_block fixture-compile rc==0", rc == 0, "stderr=%r" % err[:200])
    if rc == 0:
        rc, out, err = decompile_project(t2so, "two_block")
        v("two_block decomp rc==0", rc == 0, "stderr=%r" % err[:200])
        v("two_block scalar preserved (cross-block)", expected_scalar_preserved(out), out[:200])
        try:
            lib = ctypes.CDLL(t2so)
            fn = lib.two_block
            fn.restype = ctypes.c_uint
            fn.argtypes = [ctypes.c_uint]
            v("native two_block(0)==0", fn(0) == 0)
            v("native two_block(1)==0x2c2d2e2f", fn(1) == 0x2c2d2e2f)
        except Exception as e:
            v("native two_block loadable", False, "ctypes_error=%r" % (e,))
    else:
        v("two_block fixture skipped (compiler failure)", False)

    # ---------------------------------------------------------------
    # Test 4: Store opaco intermedio entre escrituras constantes
    # ---------------------------------------------------------------
    bar = os.path.join(tmpdir, "barrier.s")
    barso = os.path.join(tmpdir, "barrier.so")
    with open(bar, "w") as fh:
        fh.write(
            ".intel_syntax noprefix\n"
            ".text\n"
            ".globl barrier_fix\n"
            ".type barrier_fix, @function\n"
            "barrier_fix:\n"
            "    push rbp\n"
            "    mov rbp, rsp\n"
            "    sub rsp, 24\n"
            "    mov dword ptr [rbp-8], 0x2c2d2e2f\n"
            "    mov dword ptr [rbp-12], 0x44434241\n"
            "    mov byte ptr [rdi], 0x41\n"
            "    mov dword ptr [rbp-16], 0x33323130\n"
            "    xor eax, eax\n"
            "    mov rsp, rbp\n"
            "    pop rbp\n"
            "    ret\n"
        )
    rc, _, err = subproc(["gcc", "-O0", "-fPIC", "-shared", "-o", barso, bar])
    v("barrier fixture-compile rc==0", rc == 0, "stderr=%r" % err[:200])
    if rc == 0:
        rc, out, err = decompile_project(barso, "barrier_fix")
        v("barrier decomp rc==0", rc == 0, "stderr=%r" % err[:200])
        v("opaque store preserved (rdi byte write, '*a0 = 65' or 'mov *[rdi], 65' style)",
          ("a0" in out and "65" in out), out[:400])
        v("fold preserved by simplifier (strncpy or v0[/v1[)",
          ("strncpy" in out and "v0[" in out or "v1[" in out), out[:400])
    else:
        v("barrier fixture skipped (compiler failure)", False)

    # ---------------------------------------------------------------
    # Test 5: cadena legitima "ABCD" (sin lecturas escalares; strncpy conservada)
    # ---------------------------------------------------------------
    ABCD_HEX = "83ec04c704244142434433c0c3"
    for preset in ["malware", "basic", "fast", "full"]:
        rc, out, err = decompile_shellcode(ABCD_HEX, "x86", preset)
        v("ABCD preset=%s: rc==0" % preset, rc == 0, "stderr=%r" % err[:200])
        v("ABCD preset=%s: fold preserved (strncpy present)" % preset,
          "strncpy" in out and "ABCD" in out, out[:200])

    # ---------------------------------------------------------------
    # Test 6: Early/Late parity
    # ---------------------------------------------------------------
    ALL_DISABLE = (
        "import sys\n"
        "src = %r\n"
        "sys.path.insert(0, src)\n"
        "import angr\n"
        "from angr.analyses.decompiler.optimization_passes.inlined_strcpy_simplifier import InlinedStrcpySimplifier\n"
        "p = angr.load_shellcode(bytes.fromhex(%r), arch='x86', load_address=0x400000)\n"
        "p.analyses.CFGFast(normalize=True)\n"
        "p.analyses.CompleteCallingConventions(workers=0)\n"
        "fxn = p.kb.functions[0x400000]\n"
        "r = p.analyses.Decompiler(fxn, preset='malware', disable_opts=[InlinedStrcpySimplifier])\n"
        "print(r.codegen.text if r.codegen else '')\n" % (MASTER, FIXTURE_HEX)
    )
    rc_default, out_default, err_default = decompile_shellcode(FIXTURE_HEX, "x86", "malware")
    rc_skip_early, out_skip_early, err_skip_early = subproc([sys.executable, "-c", ALL_DISABLE])
    v("Early-disabled rc==0", rc_skip_early == 0, "stderr=%r" % err_skip_early[:200])
    v("Early-disabled: scalar preserved", expected_scalar_preserved(out_skip_early), out_skip_early[:200])
    v("parity: default output equals Early-disabled output",
      out_default == out_skip_early, "DIFFERS")

    # ---------------------------------------------------------------
    # Test 7: prerequisites of the repaired clone hashes binding
    # ---------------------------------------------------------------
    src_file = os.path.join(MASTER, "angr", "analyses", "decompiler", "optimization_passes", "inlined_strcpy_simplifier.py")
    sha = hashlib.sha256(open(src_file, "rb").read()).hexdigest()
    v("patched source sha == deef285f...", sha == "deef285f88a7ee4cda57cce2ef379f48348f4c87dc42ee1bedcfbc0baf24b2a9", sha)

    shutil.rmtree(tmpdir, ignore_errors=True)

    # ---------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------
    print()
    print("RXRE ANGR-7294 M9 regression: %d passed, %d failed" % (n - len(FAILS), len(FAILS)))
    if FAILS:
        for line in FAILS:
            print("FAIL:", line)
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
