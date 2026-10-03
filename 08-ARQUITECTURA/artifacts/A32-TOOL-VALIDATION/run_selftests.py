#!/usr/bin/env python3
"""AGENT-32 / A32-1: re-ejecuta el selftest de cada herramienta del registro.

POR QUE NO REUTILIZO artifacts.py
---------------------------------
El registro TOOLS-STATUS.md lo genera artifacts.py. Si yo ejecuto el mismo
harness que produjo el veredicto, no tengo un contraste: tengo el mismo
tester. Este script invoca cada herramienta directamente como subproceso y
guarda lo OBSERVADO (rc, bytes de stdout/stderr, duracion, timeout), para que
la comparacion sea entre dos mecanismos distintos.

PRE-EXECUTION CONTRACT CHECK (AGENTS.md 26)
------------------------------------------
1. exit status del productor: registrado por herramienta
2. SIGPIPE: NO se encadena a head/tail; cada salida va a su propio fichero
3. truncamiento: se registra el numero de BYTES, no de lineas
4. timeout: clasificado aparte, nunca mezclado con "falla"
5. artefacto: TSV con una fila por herramienta + comprobacion de recuento
6. contaminacion: hash de `git status` antes y despues
"""
import hashlib
import os
import subprocess
import sys
import time

ROOT = "/home/lucas/Escritorio/RX550-INVESTIGACION"
TOOLS = os.path.join(ROOT, "tools")
OUT = "/tmp/opencode/rx550/a32"
LOGS = os.path.join(OUT, "logs")
TIMEOUT = 180

os.makedirs(LOGS, exist_ok=True)


def git_state_hash():
    """Huella del estado del arbol versionado: detector de contaminacion."""
    r = subprocess.run(
        ["git", "-C", ROOT, "status", "--porcelain"],
        capture_output=True, text=True, timeout=120,
    )
    return hashlib.sha256(r.stdout.encode()).hexdigest()[:16]


def classify(name, rc, timed_out, out_bytes, err_bytes):
    """Traduce lo OBSERVADO a un veredicto. Solo sobre lo medido."""
    if timed_out:
        return "TOOL_TIMEOUT", "supera %ds; no es un fallo del selftest" % TIMEOUT
    if rc == 0:
        return "TOOL_SELFTEST_PASS", "rc=0"
    if rc == 1:
        return "TOOL_SELFTEST_FAIL", "rc=1"
    if out_bytes == 0 and err_bytes == 0:
        return "TOOL_NO_OUTPUT", "rc=%d sin una sola palabra" % rc
    return "TOOL_RC_OTHER", "rc=%d" % rc


def run_one(path):
    name = os.path.basename(path)
    src = path
    if name.endswith(".c"):
        # Un .c no se ejecuta: requiere un binario. Se registra aparte.
        return {
            "tool": name, "kind": "FUENTE_C", "invocada": "-",
            "rc": "", "timeout": "no", "stdout_b": "", "stderr_b": "",
            "dur_s": "", "verdict": "TOOL_SOURCE_ONLY",
            "detail": "no es ejecutable sin compilar",
            "binario": "SI" if os.path.exists(os.path.join(TOOLS, name[:-2])) else "NO",
        }
    if name.endswith(".sh"):
        cmd = ["bash", src, "--selftest"]
    elif name.endswith(".py"):
        cmd = [sys.executable, src, "--selftest"]
    else:
        cmd = [src, "--selftest"]

    log = os.path.join(LOGS, name + ".out")
    t0 = time.time()
    timed_out = False
    try:
        r = subprocess.run(
            cmd, capture_output=True, timeout=TIMEOUT, cwd=ROOT, env=ENV,
        )
        rc, so, se = r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired as e:
        timed_out = True
        rc = -1
        so = e.stdout or b""
        se = e.stderr or b""
    dur = time.time() - t0

    with open(log, "wb") as f:
        f.write(b"=== STDOUT ===\n" + so + b"\n=== STDERR ===\n" + se)

    verdict, detail = classify(name, rc, timed_out, len(so), len(se))
    return {
        "tool": name, "kind": "EJECUTADA", "invocada": " ".join(cmd[1:]) or "-",
        "rc": rc, "timeout": "si" if timed_out else "no",
        "stdout_b": len(so), "stderr_b": len(se),
        "dur_s": "%.2f" % dur, "verdict": verdict, "detail": detail,
        "binario": "-",
    }


ENV = dict(os.environ)
ENV["PYTHONDONTWRITEBYTECODE"] = "0"  # no ocultar errores de importacion


def main():
    before = git_state_hash()
    names = sorted(
        f for f in os.listdir(TOOLS)
        if f.endswith((".py", ".sh", ".c")) and f != "ideas.txt"
    )
    rows = [run_one(os.path.join(TOOLS, n)) for n in names]
    after = git_state_hash()

    cols = ["tool", "kind", "rc", "timeout", "stdout_b", "stderr_b", "dur_s",
            "verdict", "detail", "binario", "invocada"]
    tsv = os.path.join(OUT, "selftest-observado.tsv")
    with open(tsv, "w") as f:
        f.write("# AGENT-32 A32-1 observacion directa de selftests\n")
        f.write("# git_status_antes=%s despues=%s\n" % (before, after))
        f.write("# filas=%d\n" % len(rows))
        f.write("\t".join(cols) + "\n")
        for r in rows:
            f.write("\t".join(str(r.get(c, "")) for c in cols) + "\n")

    # VALIDACION DEL ARTEFACTO: exit 0 no es resultado valido
    n_rows = sum(1 for l in open(tsv) if not l.startswith("#"))
    ok = (n_rows == len(rows) + 1)
    print("herramientas vistas : %d" % len(rows))
    print("filas en TSV (sin #): %d  -> artefacto %s"
          % (n_rows, "VALIDO" if ok else "INVALIDO"))
    print("git status antes   : %s" % before)
    print("git status despues : %s  -> %s"
          % (after, "sin contaminacion" if before == after else "CONTAMINADO"))
    from collections import Counter
    for v, c in sorted(Counter(r["verdict"] for r in rows).items()):
        print("  %-22s %d" % (v, c))
    print("artefacto: %s" % tsv)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
