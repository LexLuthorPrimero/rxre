#!/usr/bin/env python3
# CONTRACT: name=run_all
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=yes
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
r"""
RUNNER -- una sola entrada para toda la caja de herramientas.

Por que existe. Con siete herramientas distintas, cada ronda terminaba asi:

    python3 pm4_reachable.py | head -40
    python3 gmmio_inventory.py | head -60
    python3 pm4_layout_audit.py
    git status --porcelain RESEARCH/
    grep -P '[\x{4e00}-\x{9fff}]' 06-.../0*.md
    ...

Cinco comandos con cinco sintaxis distintas, y es facil olvidar uno. El peor
caso real: olvidar el grep de intrusiones de otro idioma, que es el defecto que
mas he repetido.

Este script corre todo, comprueba el estado del corpus ANTES y DESPUES, y
termina con un codigo de salida utilizable desde un hook de commit.

Uso:
  python3 run_all.py              todo
  python3 run_all.py --quick      solo lo barato y lo que detecta errores
  python3 run_all.py --check      solo integridad (para un pre-commit hook)
Salida: 0 si todo bien, 1 si algo falla de verdad.
"""
import subprocess
import sys
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/lucas/Escritorio/RX550-INVESTIGACION"
GUARD = os.path.join(HERE, "corpus_guard.py")


def run(label, cmd, want_lines=0, quick_ok=False):
    print(f"\n{'=' * 70}")
    print(f">>> {label}")
    print(f"{'=' * 70}")
    t = time.time()
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True,
                           text=True, timeout=600)
    except subprocess.TimeoutExpired:
        print("TIMEOUT tras 600 s")
        return 1, False
    dt = time.time() - t
    out = (r.stdout or "").strip()
    err = (r.stderr or "").strip()
    if out:
        lines = out.split("\n")
        for l in lines[-want_lines:] if want_lines else lines:
            print(l)
        if want_lines and len(lines) > want_lines:
            print(f"... ({len(lines) - want_lines} lineas antes omitidas)")
    if err:
        print(f"--- stderr ---")
        for l in err.split("\n")[-8:]:
            print(l)
    print(f"[{dt:.1f}s  rc={r.returncode}]")
    return r.returncode, r.returncode == 0


def main():
    args = sys.argv[1:]
    quick = "--quick" in args
    check_only = "--check" in args
    results = []

    # 0. integridad del corpus, SIEMPRE primero
    rc, ok = run("INTEGRIDAD DEL CORPUS (antes)",
                 ["python3", GUARD, "--git"], want_lines=10)
    results.append(("integridad", ok))

    if check_only:
        print("\nsolo integridad; fin.")
        return 0 if all(o for _, o in results) else 1

    # 1. herramientas de analisis
    tools = [
        ("cierre de includes de gfx_v8_0.c",
         ["include_closure.py", "gfx_v8_0.c", "--opcodes"], 0),
        ("PM4 alcanzabilidad y vocabulario vivo", ["pm4_reachable.py"], 0),
        ("PM4 layouts documentados vs emitidos", ["pm4_layout_audit.py"], 0),
        ("inventario de registros MMIO", ["gmmio_inventory.py"], 0),
        # lectura del ASIC en vivo, SOLO LECTURA. Verifica que el modulo
        # cargado es el que cree el corpus. No escribe nada.
        ("runtime: estado del ASIC (solo lectura)",
         ["runtime_obs.py", "module"], 0),
        ("binario real vs corpus", ["binfacts.py"], 0),
        ("PM4 codec: contraste de layouts", ["pm4_codec.py", "--check"], 0),
        ("PM4 codec: NOP contra regla 034", ["pm4_codec.py", "--nops"], 0),
        ("contrato de las herramientas", ["toolkit.py"], 0),
        # El detector de contradicciones tiene que correr en CADA verificacion.
        # Si solo corre cuando me acuerdo, deja de ser un control y pasa a ser
        # una consulta: la contradiccion de block_size llego a tres documentos
        # porque nadie ejecuto nada en medio.
        ("contradicciones entre hallazgos",
         ["causal_map.py", "--contradictions"], 0),
        # El mapa causal. Se ejecuta entero porque su salida ES la
        # verificacion: si deja de encontrar las aristas que se conocen,
        # el corpus cambio o la herramienta se rompio.
        ("mapa causal (aristas del camino GFX8)", ["causal_chain.py"], 0),
        # El generador de trabajo. Se ejecuta para que el ranking este
        # disponible en cada verificacion y para que se note cuando cambia
        # el numero de registros sin documentar.
        ("siguiente trabajo (ranking)", ["next_work.py"], 12),
        # La asercion estructural del driver. Se ejecuta con codigo de salida
        # real: si el struct vi_mqd deja de cuadrar con los offsets, esto
        # devuelve 3 y el runner lo marca como fallo.
        ("asercion struct vi_mqd vs offsets", ["mqd_layout.py", "--mismatches"], 0),
        # Control negativo: una herramienta que no puede fallar no puede
        # decir que pasa. Debe detectar sus propias 4 mutaciones.
        ("mqd_layout: control negativo", ["mqd_layout.py", "--self-test"], 0),
    ]
    if quick:
        tools = tools[1:]
    for label, a, n in tools:
        # a es la lista COMPLETA de argumentos, no solo el nombre del script.
        # include_closure necesita sus tres (script, fichero, --opcodes) y con
        # a[0] se quedava sin el fichero -> rc=2 -> "FALLA" sin motivo real.
        rc, ok = run(label, ["python3", os.path.join(HERE, a[0])] + a[1:],
                     want_lines=n)
        results.append((label, ok))

    # 2. linter de documentos. Esto es lo que mas me ha ahorrado.
    print(f"\n{'=' * 70}")
    print(">>> LINTER DE HALLAZGOS")
    print(f"{'=' * 70}")
    t = time.time()
    r = subprocess.run(["python3", os.path.join(HERE, "doclint.py"), "--self"],
                       cwd=ROOT, capture_output=True, text=True, timeout=600)
    dt = time.time() - t
    lines = (r.stdout or "").split("\n")
    for l in lines[-14:]:
        print(l)
    print(f"[{dt:.1f}s  rc={r.returncode}]")
    results.append(("doclint", r.returncode == 0))

    # 3. integridad DESPUES. Si algo toco el corpus, esto lo dice.
    rc, ok = run("INTEGRIDAD DEL CORPUS (despues)",
                 ["python3", GUARD, "--git"], want_lines=10)
    results.append(("integridad final", ok))

    # resumen
    print(f"\n{'=' * 70}")
    print("RESUMEN")
    print(f"{'=' * 70}")
    for label, ok in results:
        print(f"  {'OK  ' if ok else 'FALLA'}  {label}")
    bad = [l for l, ok in results if not ok]
    if bad:
        print(f"\n{bad and len(bad)} comprobacion(es) fallan: {bad}")
        return 1
    print("\ntodas las comprobaciones pasan")
    return 0


if __name__ == "__main__":
    sys.exit(main())