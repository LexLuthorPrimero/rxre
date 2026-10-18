#!/usr/bin/env python3
# CONTRACT: name=captura
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=indeterminado
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py, y el veredicto fue `NO_DETERMINED`.
# NO se upgraded a `WRITES_FILES=yes` porque no esta medido, y NO se dejo en
# `no` porque el codigo no lo sostiene.  La razon del NO_DETERMINED es que lanza herramientas de captura por subprocess, que pueden escribir donde esta no lo ve.
#
# Poner `yes` seria MENTIR en un sentido que el validador no puede detectar, que
# es lo que el propio toolkit.py escribe de sus cinco falsos positivos: "un
# contrato en prosa no se puede comprobar con una maquina".  Poner `no` seria
# Peor: seria una afirmacion que nadie ha comprobado.
#
# TOUCHES_INTEGRATED=no: lee sysfs y ficheros.  No hace ioctl ni escribe en la
# GPU.  Ver 1487.
"""
captura.py -- toma un snapshot de TODOS los nodos de solo lectura, de una vez.

POR QUE UNA SESION
-----------------
Un `sudo` por nodo cuesta ~0,4 s y repite la autenticacion. Con 20 nodos son
8 segundos y 20 eventos de autenticacion. Ademas, si la maquina se reinicia a
mitad, se pierde el snapshot entero.

Aqui hay UNA sola sesion de sudo que recorre la lista blanca y deja cada
volcado en su fichero. Es atomico en la practica: o se capturo todo, o se
vio en el log que nodo.

LIMITE DE TAMANO, Y POR QUE
---------------------------
Cada volcado se corta a un maximo configurable. amdgpu_sa_info y amdgpu_regs
pueden ser muy grandes, y volcarlos enteros al terminal no aporta nada: el
analisis se hace DESPUES, sobre el fichero.

POR QUE NO SE CAPTURA amdgpu_regs
---------------------------------
Porque ha reiniciado el servidor dos veces de tres. No se ha probado que la
lectura lo cause, pero la correlacion es suficiente para no seguir con el.

Un volcado de 128 KiB de registros no aporta mas que un volcado de las
primeras 200 lineas para el trabajo que hay, y a cambio tiene un coste
operativo que se ha observado dos veces. La decision es economica y
prudente, no una afirmacion sobre la causa.

Que no este amdgpu_regs NO significa que no haya lectura de registros: hay
otros nodos que dan memoria real de la GPU (amdgpu_sa_info) y los parametros
del modulo dan la configuracion efectiva.
"""
import argparse
import hashlib
import os
import subprocess
import sys
import time

DEBUGFS = "/sys/kernel/debug/dri/0000:01:00.0"
AQUI = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(AQUI, "capturas")

# Nodos EXCLUIDOS del plan, con el motivo.
#
# Un nodo que esta aqui NO puede estar en PLAN ni en PLAN_BIN. La Exclusion
# es absoluta, no una nota.
#
# La version anterior de esta lista tenia amdgpu_vbios y psp_spirom_dump con el
# motivo "se captura aparte, en binario". Eso era contradictorio: estaban en
# EXCLUIDOS y en PLAN_BIN a la vez. El snapshot completo funcionaba, porque
# EXCLUIDOS solo se consulta cuando se pasa --solo, pero `--solo amdgpu_vbios`
# se rechazaba con "excluido a proposito" para un nodo que el propio plan
# queria capturar. El control que lo detecta esta en check_captura().
EXCLUIDOS = {
    "amdgpu_regs": "ha reiniciado el servidor 2 de 3 veces; no se arriesga",
    "amdgpu_regs2": "mismo fichero, mismo riesgo",
    "amdgpu_regs_pcie": "mismo riesgo que amdgpu_regs",
    "amdgpu_regs_pcie64": "mismo riesgo",
    "amdgpu_regs_smc": "mismo riesgo",
    "amdgpu_regs_didt": "mismo riesgo",
    "amdgpu_iomem": "EPERM: el kernel restringe la lectura incluso a root",
}

# Nodos binarios: se capturan igual, pero su contenido no es texto y su
# analisis es distinto. No estan excluidos: estan en otro plan.
PLAN_BIN = {
    "amdgpu_vbios": 131072,
    "psp_spirom_dump": 262144,
}

# lo que se captura: nombre -> (binario?, tope en bytes)
PLAN = {
    "amdgpu_vm_info": (False, 262144),
    "amdgpu_ring_gfx": (False, 262144),
    "amdgpu_ring_sdma0": (False, 262144),
    "amdgpu_ring_sdma1": (False, 262144),
    "amdgpu_ring_comp_1.3.1": (False, 262144),
    "amdgpu_gem_info": (False, 262144),
    "amdgpu_fence_info": (False, 131072),
    "amdgpu_sa_info": (False, 524288),
    "amdgpu_sensors": (False, 65536),
    "amdgpu_pm_info": (False, 65536),
    "amdgpu_firmware_info": (False, 65536),
    "amdgpu_dm_capabilities": (False, 65536),
    "amdgpu_gtt_mm": (False, 131072),
    "amdgpu_vram_mm": (False, 131072),
    "amdgpu_gds_mm": (False, 65536),
    "amdgpu_oa_mm": (False, 65536),
    "amdgpu_mst_topology": (False, 65536),
    "state": (False, 65536),
    "name": (False, 4096),
    "clients": (False, 65536),
    "gem_names": (False, 65536),
}


def check_captura():
    """
    Coherencia interna del plan de captura. Devuelve una lista de fallos.

    ESTE CONTROL EXISTE PORQUE FALLO UNA VEZ. La primera version de
    EXCLUIDOS contenia amdgpu_vbios y psp_spirom_dump con el motivo "se
    captura aparte, en binario", y ademas estaban en PLAN_BIN. Nada lo
    detectaba: el snapshot completo funcionaba, porque EXCLUIDOS solo se mira
    cuando se pasa --solo, de modo que el conflicto estaba latente. Se
    manifesto cuando se probo `--solo amdgpu_vbios` y se rechazo un nodo que
    el plan queria capturar.

    El patron es el conocido de este proyecto: un mismo hecho en dos sitios y
    divergen en silencio. Por eso el control mira la RELACION entre los dos
    conjuntos, no cada uno por separado.
    """
    fallos = []
    en_plan = set(PLAN) | set(PLAN_BIN)
    solape = sorted(set(EXCLUIDOS) & en_plan)
    if solape:
        fallos.append("nodos a la vez EXCLUIDOS y en el plan: %s "
                      "(--solo los rechazaria)" % ", ".join(solape))
    sin_motivo = [k for k, v in EXCLUIDOS.items() if not v.strip()]
    if sin_motivo:
        fallos.append("excluidos sin motivo escrito: %s" % ", ".join(sin_motivo))
    sin_tope = [k for k in PLAN_BIN if not isinstance(PLAN_BIN[k], int)
                or PLAN_BIN[k] <= 0]
    if sin_tope:
        fallos.append("binarios sin tope de bytes valido: %s"
                      % ", ".join(sin_tope))
    sin_tope_t = [k for k, v in PLAN.items()
                  if not isinstance(v[1], int) or v[1] <= 0]
    if sin_tope_t:
        fallos.append("texto sin tope de bytes valido: %s"
                      % ", ".join(sin_tope_t))
    return fallos


def main():
    ap = argparse.ArgumentParser(description="snapshot de solo lectura")
    ap.add_argument("--dest", default=DEST)
    ap.add_argument("--timeout", type=int, default=240)
    ap.add_argument("--solo", default=None, help="un solo nodo")
    a = ap.parse_args()

    pw = os.environ.get("RX550_SUDO_PASS", "")
    # El control de coherencia corre ANTES de tocar sudo, y siempre.
    # Si el plan es incoherente, no se lee nada: un plan contradictorio
    # puede capturar un nodo que el propio script dice no tocar, y eso es
    # peor que no capturar nada.
    fallos = check_captura()
    if fallos:
        print("PLAN INCOHERENTE: no se captura nada.")
        print("El plan se contradice a si mismo, y un plan que se contradice")
        print("puede leer un nodo marcado como prohibido. Se corrige antes.")
        for f in fallos:
            print("  - %s" % f)
        return 3

    if not pw:
        print("Falta RX550_SUDO_PASS en el entorno.")
        print("Se lee de ahi y NO de un fichero ni de un argumento: un")
        print("argumento aparece en /proc/PID/cmdline y queda en el")
        print("historial del shell.")
        return 2
    os.makedirs(a.dest, exist_ok=True)

    plan = dict(PLAN)
    plan_bin = dict(PLAN_BIN)
    if a.solo:
        if a.solo in EXCLUIDOS:
            print("EXCLUIDO A PROPOSITO: %s -- %s"
                  % (a.solo, EXCLUIDOS[a.solo]))
            return 1
        if a.solo in plan:
            plan = {a.solo: plan[a.solo]}
            # --solo tiene que ser SOLO. La primera version dejaba plan_bin
            # intacta, asi que `--solo amdgpu_firmware_info` informaba
            # "1 (+2 binarios)" y ademas capturaba el VBIOS y el SPI ROM.
            # El nombre de la opcion decia una cosa y el codigo hacia otra.
            plan_bin = {}
        elif a.solo in plan_bin:
            plan = {}
            plan_bin = {a.solo: plan_bin[a.solo]}
        else:
            print("%r no esta en el plan de captura" % a.solo)
            return 2
    if not plan and not plan_bin:
        print("plan de captura vacio: no se lee nada")
        return 2

    print("SNAPSHOT DE SOLO LECTURA")
    print("destino: %s" % a.dest)
    print("nodos a capturar: %d (+%d binarios)" % (len(plan), len(plan_bin)))
    print("GPU INTACTA: solo se leen ficheros, no se escribe nada.")
    print()

    # UNA sola sesion de sudo. El script interno itera y escribe.
    script = r"""
set -u
D="%s"
outdir="%s"
shift
for spec in "$@"; do
  nodo="${spec%%=*}"
  tope="${spec##*=}"
  f="$outdir/$nodo.txt"
  # head -c es lo que limita: no se lee mas de lo necesario
  head -c "$tope" "$D/$nodo" > "$f" 2>"$f.err"
  rc=$?
  printf '%%s\t%%s\t%%s\n' "$nodo" "$rc" "$(wc -c < "$f")"
done
""" % (DEBUGFS, a.dest)

    specs = ["%s=%d" % (k, v[1]) for k, v in plan.items()]
    specs += ["%s=%d" % (k, v) for k, v in plan_bin.items()]

    t0 = time.time()
    try:
        r = subprocess.run(["sudo", "-S", "-k", "bash", "-c", script,
                            "captura"] + specs,
                           input=pw + "\n", capture_output=True, text=True,
                           timeout=a.timeout)
        salida = r.stdout
        rc_global = r.returncode
    except subprocess.TimeoutExpired:
        print("TIMEOUT a los %d s. Se conserva lo capturado hasta ese punto."
              % a.timeout)
        salida = ""
        rc_global = 1
    dt = time.time() - t0

    # AUTENTICACION FALLIDA, DICHA POR SU NOMBRE.
    #
    # El fallo dominante de este proyecto ha sido siempre el mismo: un cero
    # que parece un resultado. Aqui era facil de producir: si sudo no
    # authentica, el script interno no llega a correr, no sale ninguna linea
    # "nodo\trc\tbytes", y el resumen imprimia "con contenido: 0, vacios: 0,
    # con error: 0". Eso parece un snapshot limpio de un arbol vacio, cuando
    # en realidad no se ha leido NADA.
    #
    # La distincion es estructural, no heuristica: se pedian N lineas de
    # resultado y se recibieron 0 con un codigo de salida distinto de cero.
    # Eso no es un resultado, es un fallo de ejecucion.
    specs_esperadas = len(specs)
    lineas_parseadas = [ln for ln in salida.splitlines()
                        if not ln.startswith("[sudo]")
                        and ln.count("\t") == 2 and ln.split("\t")[0] in
                        (set(plan) | set(plan_bin))]
    if rc_global != 0 and not lineas_parseadas:
        print("FALLO DE EJECUCION: no se capturo NINGUN nodo.")
        print()
        print("  nodos pedidos    : %d" % specs_esperadas)
        print("  lineas recibidas : %d" % len(lineas_parseadas))
        print("  codigo de salida : %d" % rc_global)
        print()
        print("Esto NO es un snapshot vacio: es un fallo. La causa mas")
        print("probable es que sudo no haya autenticado. Se dice")
        print("explicitamente para que un 0 no se lea como 'no hay nada que")
        print("mirar'.")
        err_txt = (r.stderr if 'r' in dir() else "") or ""
        limpio = [l for l in err_txt.splitlines()
                  if l.strip() and "contrase" not in l]
        if limpio:
            print()
            print("stderr:")
            for l in limpio[:8]:
                print("  %s" % l[:160])
        return 4

    print("%-28s %-5s %10s  %s" % ("nodo", "rc", "bytes", "sha256[:16]"))
    print("-" * 68)
    ok = vacio = err = 0
    for ln in salida.splitlines():
        if ln.startswith("[sudo]") or not ln.strip():
            continue
        partes = ln.split("\t")
        if len(partes) != 3:
            continue
        nodo, rc, nb = partes[0], partes[1], partes[2]
        p = os.path.join(a.dest, nodo + ".txt")
        try:
            h = hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
        except Exception:
            h = "(no leido)"
        if rc != "0":
            err += 1
        elif int(nb) == 0:
            vacio += 1
        else:
            ok += 1
        print("%-28s %-5s %10s  %s" % (nodo, rc, nb, h))
    print("-" * 68)
    print("con contenido : %d" % ok)
    print("vacios        : %d" % vacio)
    print("con error     : %d" % err)
    print("tiempo         : %.1f s (una sola sesion de sudo)" % dt)
    print()
    if vacio:
        print("Nodos VACIOS: puede ser EPERM (el kernel lo restringe) o que")
        print("no haya datos. No es lo mismo, y se mira el .err de cada uno.")
    print()
    print("EXCLUIDOS A PROPOSITO:")
    for n, why in sorted(EXCLUIDOS.items()):
        print("   %-22s %s" % (n, why))
    print()
    print("El snapshot queda como ARTEFACTO: se puede volver a analizar")
    print("sin tocar la GPU otra vez. Eso es lo que evita repetir la")
    print("operacion, y por eso capturar una vez a fichero importa.")
    return 0


if __name__ == "__main__":
    sys.exit(main())