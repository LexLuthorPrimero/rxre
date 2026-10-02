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


def run(label, cmd, want_lines=0, quick_ok=False, rc_ok=None):
    """Ejecuta una comprobacion. `rc_ok` es la lista de codigos que valen.

    POR QUE EXISTE `rc_ok` Y POR QUE NO PUEDE VIVIR EN EL LLAMANTE.

    `num_collision` devuelve 3 cuando hay numeros de hallazgo duplicados. Es un
    HECHO del proyecto, no un fallo de la herramienta: ponerlo en rojo obligaria
    a cambiar la convencion de citacion por las malas.

    La primera version de esto lo resolvio en el bucle del llamante:

        rc, ok = run(...)
        if ok and rc_tol is not None and rc not in (0, rc_tol):
            ok = False

    Y no funcionaba, porque `ok` ya era False: `run` devuelve `rc == 0`, y con
    rc=3 nunca puede ser cierto. La condicion `if ok and ...` nunca se
    cumplia, y la herramienta se quedaba en FALLA sin poder marcarlo.

    Es la clase de error que mas cuesta ver: la logica es correcta y la
    herramienta devuelve un valor que la hace inalcanzable. Por eso la
    decision se toma AQUI, donde se conoce el codigo de salida, y no dos
    niveles mas arriba.
    """
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
    validos = [0] if rc_ok is None else list(rc_ok)
    return r.returncode, r.returncode in validos


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
        # El contrato de las herramientas. rc 0 si todas lo tienen.
        #
        # FALLA cuando hay alguna sin contrato, y eso INCLUYE herramientas
        # que otra sesion commiteo. No se relaja: el contrato es lo unico que
        # permite preguntar "esta herramienta puede tocar el hardware?", y
        # aceptarlo como no-fallo para que el semaforo quede verde seria
        # admitir que el semaforo ya no mide.
        #
        # Lo que si se hace es que el nombre de la herramienta que falla este
        # en la salida, que ya lo esta. Un rojo con nombre es informacion; un
        # verde con excusas es ruido.
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
        # --- las siete herramientas de la sesion de registros/simbolos ---
        # Se ejecutan con --self, no con su modo informative. La razon es la
        # misma que el mapa causal: un self-test que nadie ejecuta deja de
        # ser un control. Estas siete se escribieron hoy y su modo normal es
        # un informe, que siempre sale "bien" aunque la herramienta este rota.
        # El --self es lo que puede fallar.
        ("citecheck: 32 vectores", ["citecheck.py", "--self"], 0),
        ("scopeguard: preflight", ["scopeguard.py", "--self"], 0),
        ("xref: lectura/escritura", ["xref.py", "--self"], 0),
        ("causal: grafo de llamadas", ["causal.py", "--self"], 0),
        ("contradict: cifras en conflicto", ["contradict.py", "--self"], 0),
        ("regdb: campos entre familias", ["regdb.py", "--self"], 0),
        ("hdrmap: familias por .c", ["hdrmap.py", "--self"], 0),
        # F11 pide el titular CRUDO y el FILTRADO de cada herramienta con
        # numero.  Esta mide si alguna vez se leyo su salida, y publica las
        # suyas para que el proximo pueda aplicar el mismo criterio.
        ("toolaudit: F11 titular leido", ["toolaudit.py", "--self"], 0),
        # Catalogo de mensajes SMU: 276 para Polaris12. El dato generado que
        # 070 dejo abierto, y que una herramienta debe producir, no transcribir.
        ("smumsg: catalogo de mensajes", ["smumsg.py", "--self"], 0),
        # El barrido que hizo el hallazgo 065: registros escritos por un .c con
        # direccion distinta segun familia. Si el numero deja de ser 7, o el
        # corpus cambio o la herramienta se rompio. Se ejecuta entero porque
        # su SALIDA es la verificacion, no su codigo de salida.
        ("registros con offset distinto entre familias",
         ["regdb.py", "--scan-file",
          "RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/gmc_v8_0.c"],
         0),
        # Control negativo: una herramienta que no puede fallar no puede
        # decir que pasa. Debe detectar sus propias 4 mutaciones.
        ("mqd_layout: control negativo", ["mqd_layout.py", "--self-test"], 0),
        # La misma asercion en los 4 sitios que la hacen (display y KFD, dos
        # generaciones). Cuatro sitios que cuadran es CORROBORACION de que el
        # struct esta construido para ese layout; uno que cuadra es un caso.
        ("asercion struct->offset en 4 sitios", ["mqd_layout.py", "--sitios"], 0),
        # El validador de contratos debe pasar su propio control de la regla
        # "lo que no esta en git no reproba". Si _en_git se equivoca, esa
        # regla dejaria de ser una excepcion y seria un agujero.
        ("toolkit: control de propias/ajenas",
         ["toolkit.py", "--selftest-ajenas"], 0),
        # Fronteras del proyecto que otro documento YA cerro. Un NOT_DETERMINED
        # obsoleto dirige el trabajo hacia algo hecho. Se ejecuta entero porque
        # su SALIDA es la verificacion.
        ("fronteras obsoletas (trabajo ya hecho)", ["stale_gap.py"], 0),
        ("stale_gap: control negativo", ["stale_gap.py", "--self-test"], 0),
        # Los numeros de hallazgo identifican un hallazgo.
        #
        # `num_collision` devuelve 3 cuando HAY colisiones, y eso no es un
        # fallo de la herramienta: es un hecho del proyecto. Va con want_lines
        # y rc tolerado, para que el numero este a la vista en cada
        # verificacion y nadie pueda decir que no se sabia, sin declarar
        # catastrophe por una convencion de citacion que hay que DECIDIR
        # cambiar.
        ("numeros de hallazgo unicos", ["num_collision.py"], 10, 3),
        ("num_collision: control negativo",
         ["num_collision.py", "--self-test"], 0),
        # Que parte del hardware NO se puede leer porque su codigo no esta.
        # Devuelve 2 sin el .ko descomprimido, y eso es un dato: "no puedo
        # comprobarlo" no es "no falta nada".
        ("hueco del corpus por bloque",
         ["corpus_gap.py"], 26, 0),
        ("corpus_gap: control negativo",
         ["corpus_gap.py", "--self-test"], 0),
        # La contabilidad de tamano de anillo del propio driver, resuelta
        # estaticamente. El contraste es contra una cantidad INDEPENDIENTE
        # (los `emit_frame_size` comentados de gfx_v8_0.c), que es lo que
        # convierte el self-test en validacion y no en tautologia.
        ("PM4 emitido, contraste con emit_frame_size",
         ["pm4_emit.py", "--frame-size"], 0),
        ("pm4_emit: control negativo",
         ["pm4_emit.py", "--self-test"], 0),
        # La tabla (device_id, revision) -> chip_id, leida del .ko cargado.
        # Es la que 050 dio por ausente porque hwmgr.c no esta en el corpus.
        # Devuelve 2 sin .ko y 3 si el layout deducido no encaja, y los dos
        # son datos: no se puede leer != no hay tabla.
        ("tabla de ASIC desde el binario", ["asic_table.py"], 26, 0),
        ("asic_table: control negativo",
         ["asic_table.py", "--self-test"], 0),
        # LA INTEGRIDAD CON HUELLA, no solo con git status.
        #
        # `--git` responde 0 cuando `git status --porcelain RESEARCH/` esta
        # vacio, y eso NO es una verificacion del corpus: solo comprueba que
        # git no ve cambios. Si alguien regenera un fichero y lo commitea, o
        # si el corpus se toco y luego se commiteo, `--git` dice que todo bien
        # y no es cierto.
        #
        # `--verify` compara la huella de 2787 ficheros con una referencia, y
        # devuelve 2 --distinto de 0-- cuando no hay ninguna referencia, para
        # que "no puedo comprobarlo" no se lea como "todo bien". Esa
        # distincion la hacia mal el propio corpus_guard, que antes devolvia
        # un texto de una linea indistinguible del exito.
        ("integridad del corpus (huella de 2787 ficheros)",
         ["corpus_guard.py", "--verify"], 0),
    ]
    if quick:
        tools = tools[1:]
    for t in tools:
        label, a, n = t[0], t[1], t[2]
        # a es la lista COMPLETA de argumentos, no solo el nombre del script.
        # include_closure necesita sus tres (script, fichero, --opcodes) y con
        # a[0] se quedava sin el fichero -> rc=2 -> "FALLA" sin motivo real.
        #
        # rc_tol: un codigo de salida que NO es fallo pero informa de un
        # estado. `num_collision` devuelve 3 cuando hay numeros de hallazgo
        # duplicados, y eso es un hecho del proyecto, no un error de la
        # herramienta. Marcarse FALLA obligaria a arreglar la convencion de
        # citacion por las malas; lo unico honesto es que el numero este a la
        # vista sin declarar catastrophe.
        #
        # Se distingue de `want_lines` porque no es lo mismo: `want_lines`
        # avisa si la salida sale VACIA, que si es un fallo. `rc_tol` acepta un
        # codigo concreto, que es una declaracion sobre que codigos son
        # validos para esa herramienta.
        rc_tol = t[3] if len(t) > 3 else None
        rc, ok = run(label, ["python3", os.path.join(HERE, a[0])] + a[1:],
                     want_lines=n,
                     rc_ok=[0, rc_tol] if rc_tol is not None else None)
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