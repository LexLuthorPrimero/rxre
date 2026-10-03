#!/usr/bin/env python3
# CONTRACT: name=bench
# CONTRACT: READONLY=no
# READONLY=no y no READONLY=yes: este banco crea un VkDevice, reserva memoria del
# dispositivo y envia trabajo que hace escribir a la GPU. Decir READONLY=yes al lado de
# WRITES_GPU=yes es una contradiccion en la cara del contrato, y de ahi sale la lectura
# equivocada de 932: si es de solo lectura, no puede escribir en la GPU.
# CONTRACT: WRITES_FILES=yes
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=yes
#
# La capacidad WRITES_GPU dice DOS cosas distintas y este banco cae en las dos, asi que
# se declara por separado lo que significa cada una. Sin esto, 932 leyo la linea como
# "escribe registros MMIO" -- busco /dev/mem, __iomem y no encontro nada, y concluyo
# que la declaracion era falsa. No es falsa: es ambigua.
#
# CONTRACT: WRITES_GPU_MMIO=no
# CONTRACT: WRITES_GPU_WORK=yes
#
# WRITES_GPU_MMIO=no    no toca ningun registro. Todo lo que hace es vkQueueSubmit.
# WRITES_GPU_WORK=yes   envia trabajo que hace que la GPU escriba en VRAM: los shaders
#                       escriben en d[WSIZE + i] y el host lo ve al releer. Eso es
#                       escribir en la GPU, y por eso WRITES_GPU=no seria falso.
#
# La distincion importa: una herramienta que declares WRITES_GPU=no y en realidad envie
# trabajo esta mintiendo en la direccion contraria. El banco declara lo que hace.
r"""
BENCH -- banco de mediciones de runtime con contrato, para la RX550 Polaris12/GFX8.

Por que existe. Toda la medicion de §F, §G y §H de esta sesion se hizo con scripts
escritos a mano en /tmp, uno por medicion. Eso tiene tres costes que se pagan en
errores, y los tres se pagaron:

  1. SIN ARTEFACTO. Una medicion vivia en el scroll del terminal. No habia forma de
     volver a ella, ni de comparar una serie antigua con una nueva, ni de saber que
     fuente, que comando y que reloj la produjeron.
  2. SIN PROCEDENCIA. Nada registraba el estado del hardware durante la corrida, ni
     la version del instrumento, ni el hash. Un numero sin eso no es reproducible.
  3. SIN CONTRATO. Cada script validaba lo que su autor se acordaba de validar. Hoy
     eso produjo once errores propios, y cuatro de los cinco ultimos fueron una
     linea de parche mal aplicada que ningun control existente podia ver.

Este banco hace las tres cosas y ninguna mas. No decide nada, no mide nada que los
kernels no midieran antes, y no cierra fronteras. Toma mediciones que ya sabiamos
hacer, les pone el contrato y deja el artefacto.

LA REGLA QUE IMPONE, y que es la que importa:

  Ningun numero se reporta si sus controles no pasan. Si el control de contenido
  falla, o el de entropia, o el de que el tiempo crece con ITERS, el resultado es
  INVALID_RESULT y el banco sale con codigo distinto de cero. No es un aviso: es un
  fallo. El motivo es concreto: hoy el banco acepto y valido 256 de 256 sobre un
  kernel que hacia una sola carga, porque el modelo del host hacia la misma cuenta
  equivocada. Un control que no puede fallar no es un control, y un banco que
  reporta el numero de todos modos es peor que no tener banco.

Uso:
    python3 bench.py --selftest          # todos los casos, incluidos los negativos
    python3 bench.py list                # los suites y que controls exige cada uno
    python3 bench.py run regresion       # suite corta: contenido y los dos controles
    python3 bench.py run curva --quick   # una curva de t frente a ITERS
    python3 bench.py run rejilla --full  # la rejilla de dos ejes, 16 celdas

Salida:
    0  todo PASS
    1  algun control fallo, o un resultado es INVALID
    2  uso incorrecto

El artefacto va a 08-ARQUITECTURA/validations/bench-<suite>-<timestamp>.json con la
procedencia completa: hardware, instrumento con hash, comandos, muestras crudas,
ajuste, controles y veredicto.

LIMITES, y son reales:

  - No mide lo que los shaders no miden. Si un kernel no distingue dos cosas, este
    banco tampoco: solo repite y agrega.
  - La mediana y el minimo se calculan sobre las muestras que pasaron el control.
    Si una corrida falla su control, no se promedia con las que lo pasaron: se
    descarta y se cuenta aparte, porque promediar un fallo esconde el fallo.
  - El ajuste t = a + b*ITERS es una recta por minimos cuadrados sobre los puntos
    dados, y a NO es un coste. Es el interceptor. Hoy tres notas consecutivas
   Publications lo leyeron como coste por envio, y 609 lo refuto con --rep.
    El banco lo llama `intercepto_ms` y no `coste_ms`, por esa razon.
  - El banco no guarda las shaders ni compila nada. Si falta un .spv, falla.
"""
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
VCP = os.path.join(HERE, "vcp")
OUTDIR = os.path.join(ROOT, "08-ARQUITECTURA", "validations")
HWMON = "/sys/class/drm/card1/device/hwmon/hwmon1"

# dwords por MiB, y el ancho de un wavefront en esta ASIC (gfx_v8_0.c:7124)
DW_PER_MIB = 262144
LANE = 64


# ----------------------------------------------------------------- instrument

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def leer_int(path):
    """Lee un entero de sysfs, y sabe hexadecimal.

    MEDIDO, y no es una hipotesis: `vendor` contiene "0x1002" y `device`
    contiene "0x699f". `int("0x1002")` en base 10 es ValueError, y el
    `except Exception` de antes lo convertia en None.

    Consecuencia medida en los 59 artefactos de `08-ARQUITECTURA/validations/`:
    `pci` y `pci_device` null en 59 de 59, mientras los hwmon -- que son
    DECIMALES -- si tenian valor. Solo los dos campos PCI son hex, y solo esos
    dos eran null: el patron explicaba la causa sin ninguna hipotesis.

    Se decide por el prefijo y no con `base=0` a proposito. `base=0` interpretaria
    "010" como octal, y un sysfs que devolviera un cero a la izquierda daria un
    numero distinto al de antes sin que nadie lo notase. Aqui un decimal con
    ceros a la izquierda vale lo mismo que antes del cambio.
    """
    try:
        with open(path) as f:
            t = f.read().strip()
    except OSError:
        return None
    neg = t.startswith("-")
    cuerpo = t.lstrip("+-")
    try:
        if cuerpo.lower().startswith("0x"):
            v = int(cuerpo, 16)
        elif cuerpo.isdigit():
            v = int(cuerpo, 10)
        else:
            return None
    except ValueError:
        return None
    return -v if neg else v


def leer_link_speed(path):
    """`current_link_speed` es "5.0 GT/s PCIe". Devuelve 5.0, un float.

    El comparador de `comparar_con_previo` exige `isinstance(v, (int, float))`,
    asi que la cadena entera no serviria: saldria NO_COMPARABLE. Se queda la
    magnitud, y el resto del texto es decoracion del kernel.
    """
    try:
        with open(path) as f:
            t = f.read().strip()
    except OSError:
        return None
    try:
        return float(t.split()[0])
    except (ValueError, IndexError):
        return None


def bar_map(base):
    """El tamano de cada BAR en bytes, SIN root.

    MEDIDO: los nodos `resourceN` son `-rw------- root root`, asi que abrirlos
    falla con PermissionError sin privilegios. `os.stat` NO los abre y da el
    tamano igual. Contraste cruzado hecho en esta maquina:

        os.stat(resource5).st_size                    = 262144
        fin - inicio + 1, del fichero `resource`      = 262144

    Los dos coinciden, y los dos dicen que la ventana de registros es BAR5 con
    256 KiB, que es lo que usa el driver.

    Antes se parseaba el fichero `resource` agregado con `int(f.read(), 16)`, que
    es un texto de TRECE lineas con TRES tokens hexadecimales cada una. Eso es un
    ValueError garantizado, tragado por `except Exception: pass`, y por eso
    `bar_size` fue null en las 59 ejecuciones.
    """
    out = {}
    for n in range(16):
        try:
            out["BAR%d" % n] = os.stat(os.path.join(base, "resource%d" % n)).st_size
        except OSError:
            continue
    return out or None


def fingerprint():
    """Estado del hardware DURANTE la sesion de medicion. Sin esto un numero no
    es reproducible, y es el dato que mas veces me dio una contradiccion falsa."""
    d = {}
    d["kernel"] = os.uname().release
    d["pci"] = leer_int("/sys/class/drm/card1/device/vendor")
    d["pci_device"] = leer_int("/sys/class/drm/card1/device/device")
    d["sclk_hz"] = leer_int(HWMON + "/freq1_input")
    d["mclk_hz"] = leer_int(HWMON + "/freq2_input")
    d["power_uw"] = leer_int(HWMON + "/power1_input")
    d["temp_mc"] = leer_int(HWMON + "/temp1_input")
    d["bar_size"] = bar_map("/sys/class/drm/card1/device")
    # `pcie_gen` y `pcie_width` estaban en `COMPARABLES` desde antes y NO se
    # leian nunca, con lo que su NO_COMPARABLE era permanente por construccion.
    # MEDIDO en esta maquina: current_link_speed = "5.0 GT/s PCIe" -> 5.0,
    # current_link_width = "4". Y 5.0 GT/s es Gen2, que es lo que dicen las notas
    # 284 y 285 por otra via.
    PCIDEV = "/sys/bus/pci/devices/0000:01:00.0"
    d["pcie_gen"] = leer_link_speed(PCIDEV + "/current_link_speed")
    d["pcie_width"] = leer_int(PCIDEV + "/current_link_width")
    return d


KERNELS_GLSL = ("lane.comp", "div.comp", "reuse.comp", "spread.comp",
                "probe.comp", "occ.comp", "chain.comp", "page.comp")


def frescura_spv():
    """Un .spv mas viejo que su .comp es un artefacto obsoleto, y consumarlo en
    silencio es la clase de fallo que este proyecto ha repetido: los tres
    incidentes de nentries, la constante STRIDE, y el caso de hace un minuto, en
    que un shader roto no recompilo, el error se fue a /dev/null y el banco
    consumio el .spv viejo y dio PASS.

    Devuelve (ok, detalles). Compara mtime, que es barato, y guarda tambien los
    dos hashes para que un artefacto de una corrida se pueda invalidar despues."""
    detalles = []
    ok = True
    for g in KERNELS_GLSL:
        comp = os.path.join(HERE, g)
        spv = os.path.join(HERE, g[:-5] + ".spv")
        if not os.path.exists(comp):
            continue
        if not os.path.exists(spv):
            detalles.append({"kernel": g, "estado": "SIN COMPILAR"})
            ok = False
            continue
        mc = os.path.getmtime(comp)
        ms = os.path.getmtime(spv)
        if mc > ms:
            detalles.append({"kernel": g, "estado": "OBSOLETO",
                             "comp_mtime": mc, "spv_mtime": ms})
            ok = False
        else:
            detalles.append({"kernel": g, "estado": "AL DIA",
                             "comp_sha256": sha256(comp)[:16],
                             "spv_sha256": sha256(spv)[:16]})
    return ok, detalles


def frescura_binario():
    """Un binario mas viejo que su fuente es un artefacto obsoleto, y es la MISMA
    clase de fallo que un .spv viejo, pero en un sitio donde no habia control.

    Como se manifesto: se anadio la bandera --tex al banco, se compilo a mano para
    probarla, y bench.py sigo usando el binario viejo del directorio sin enterarse.
    La suite textura corrio, dio INVALID, y lo lei como un resultado sobre la ruta de
    texel cuando en realidad era un resultado sobre un binario que no conocia la
    bandera. Peor: la ventana medida por el runner dio 4 KiB contra los 64 KiB de las
    corridas directas, y esa discrepancia era la unica senal. Si no se hubiera
    contrastsado con una corrida directa, el artefacto habria sido creible.

    El banco no construye nada (limite declarado en el modulo): el binario es un
    artefacto externo. Un artefacto externo que se consume tiene que freshness-check,
    como el .spv. Este es ese control para el.

    Devuelve (ok, detalles)."""
    src = os.path.join(HERE, "vulkan_compute_probe.c")
    if not os.path.exists(VCP):
        return False, [{"estado": "SIN CONSTRUIR", "motivo": "no existe %s" % VCP}]
    if not os.path.exists(src):
        return True, [{"estado": "AL DIA", "motivo": "sin fuente que comparar"}]
    mf = os.path.getmtime(VCP)
    ms = os.path.getmtime(src)
    d = {"binario_sha256": sha256(VCP)[:16], "fuente_sha256": sha256(src)[:16],
         "binario_mtime": mf, "fuente_mtime": ms}
    if ms > mf:
        d["estado"] = "OBSOLETO"
        d["motivo"] = ("la fuente es mas nueva que el binario: el banco mide un "
                       "programa que no es el que hay escrito")
        return False, [d]
    d["estado"] = "AL DIA"
    return True, [d]


def instrumento():
    if not os.path.exists(VCP):
        return None
    src = os.path.join(HERE, "vulkan_compute_probe.c")
    fb_ok, fb_det = frescura_binario()
    return {
        "binario": VCP,
        "binario_sha256": sha256(VCP),
        "fuente": src,
        "fuente_sha256": sha256(src) if os.path.exists(src) else None,
        "spv_frescos": frescura_spv()[0],
        "binario_fresco": fb_ok,
        "binario_frescura": fb_det,
    }


# ----------------------------------------------------------------- corrida

def correr(args, timeout=180, gpu=None):
    """Una invocacion de vcp. Devuelve (segundos, controles) y NO promedia nada:
    quien promedia es quien decide si la muestra vale.

    `gpu` es un dict opcional que se RELLENA, no que se devuelve. Se eligio esa forma a
    proposito: ampliar la tupla devuelta habria roto el desempaquetado de cuatro
    elementos en las cuatro suites ya validadas, y el camino de medicion de todo lo
    demas no se toca por añadir una observacion nueva. Un parametro de salida no cambia
    el contrato de quien ya lo usaba.
    """
    r = subprocess.run([VCP] + [str(a) for a in args],
                       capture_output=True, text=True, timeout=timeout)
    t = None
    coincide = None
    entropia = None
    gpu_ms = None
    for l in r.stdout.split("\n"):
        if l.startswith("TIEMPO"):
            t = float(l.split()[1])
        # El intervalo de marcas viene en la MISMA linea que el tiempo de host, porque
        # una marca de una medicion y un tiempo de otra no describen el mismo trabajo.
        # Ese emparejamiento se rompio una vez: se leia la marca de la calibracion y se
        # comparaba con la mediana de host de las repeticiones, y salia gpu/host de 2,5,
        # que es fisicamente imposible. El control de emparejamiento esta mas abajo.
        m = re.search(r"\bgpu=([0-9.]+) ms", l)
        if m:
            gpu_ms = float(m.group(1))
        if "coinciden" in l:
            m = re.search(r"coinciden, (\d+) NO", l)
            coincide = (m is not None and m.group(1) == "0")
        if "ENTROPIA" in l:
            m = re.search(r"ENTROPIA\s+\S+\s+(\d+) direcciones", l)
            if m:
                entropia = int(m.group(1))
    if isinstance(gpu, dict):
        gpu["ms"] = gpu_ms
    return t, coincide, entropia, r.returncode


def medir_con_gpu(args, n=7, warm=2, timeout=180):
    """Como medir(), pero devuelve tambien las marcas de GPU de las muestras que pasaron
    el control de contenido.

    Motivo, medido en 934: el tiempo de host y el de GPU no son lo mismo. En el caso
    conocido, 72 us de host contra 36,48 us de GPU: la mitad del tiempo que el banco
    llevaba meses reportando no es trabajo de la GPU, es envio. Un banco que solo mide
    host no puede separar envio-limitado de GPU-limitado, que es la pregunta de §H.

    Las muestras que no pasan el control se descartan de los dos lados. Promediar el
    tiempo de GPU de una muestra cuyo contenido no cuadra es medir trabajo que no dio
    el resultado que debía.
    """
    for _ in range(warm):
        try:
            correr(args, timeout)
        except Exception:
            pass
    host, gpu_ms, rech = [], [], 0
    for _ in range(n):
        g = {}
        try:
            t, ok, ent, rc = correr(args, timeout, g)
        except Exception:
            rech += 1
            continue
        if t is not None and ok and rc == 0:
            host.append(t)
            gpu_ms.append(g.get("ms"))
        else:
            rech += 1
    return host, gpu_ms, rech


def medir(args, n=7, warm=2, timeout=180):
    """n muestras con calentamiento. Devuelve las que PASARON su control, y el
    numero de las que no pasaron, que es un dato y no un detalle."""
    for _ in range(warm):
        try:
            correr(args, timeout)
        except Exception:
            pass
    vals, rechazadas = [], 0
    for _ in range(n):
        try:
            t, ok, ent, rc = correr(args, timeout)
        except Exception:
            rechazadas += 1
            continue
        # el control de contenido es obligatorio; el de entropia tambien
        if t is not None and ok and rc == 0:
            vals.append(t)
        else:
            rechazadas += 1
    return vals, rechazadas


def ajustar(xs, ys):
    """Minimos cuadrados sobre (xs, ys) TAL COMO VIENEN. Devuelve (a, b) en las
    MISMAS unidades que ys, y no convierte a nada.

    La primera version de esta funcion multiplicaba por 1000 y devolvia
    milisegundos, y el self-test lo detecto: el caso de prueba daba a=0 y b=500.
    Eso es exactamente la clase de error que este proyecto ha repetido cinco
    veces, una magnitud con una unidad escondida dentro de la formula en vez de
    declarada donde se usa. La unidad la pone quien llama, que es quien sabe que
    ys son segundos."""
    n = len(xs)
    sx, sy = sum(xs), sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    den = n * sxx - sx * sx
    if den == 0:
        return None, None
    b = (n * sxy - sx * sy) / den
    return (sy - b * sx) / n, b


# ----------------------------------------------------------------- argumentos

def lane_args(mib, iters, items, mode, stride=None, sub=None, rep=None, mem=0):
    W = mib * DW_PER_MIB
    a = [iters, items, "lane.spv", W, W, 7, 0, 0, 0, 0, 0, mode, 1,
         stride if stride is not None else 262144,
         sub if sub is not None else 0]
    if rep is not None:
        a += ["--rep=%d" % rep]
    else:
        a += ["--mem=%d" % mem]
    return a


# ----------------------------------------------------------------- suites

def suite_regresion(ctx):
    """Los once casos de contenido mas los dos controles que hoy no existian."""
    casos = [
        ("probe", ['256', '256', 'probe.spv', '256', '256', '0', '0']),
        ("occ", ['256', '256', 'occ.spv', '1024', '1024', '1', '0']),
        ("chain", ['256', '256', 'chain.spv', '1024', '1024', '2', '0', '--mem=0']),
        ("div", ['256', '256', 'div.spv', '1024', '1024', '3', '0', '0', '0']),
        ("page", ['256', '256', 'page.spv', '1024', '1024', '4', '0']),
        ("reuse", ['256', '512', 'reuse.spv', '65536', '65536', '5', '0', '0', '0', '128']),
        ("spread", ['256', '512', 'spread.spv', '65536', '65536', '6', '0', '0', '0', '128', '7']),
        ("lane/disperso", lane_args(4, 1024, 512, 1)),
        ("lane/contiguo", lane_args(4, 1024, 512, 2)),
        ("lane/difusion", lane_args(4, 1024, 512, 0)),
        ("lane/subregion", lane_args(4, 1024, 512, 2, sub=1024)),
    ]
    out = []
    for nombre, args in casos:
        t, ok, ent, rc = correr(args)
        out.append({"caso": nombre, "control_contenido": ok,
                    "entropia": ent, "exit": rc,
                    "veredicto": "PASS" if (ok and rc == 0) else "INVALID"})

    # control: el tiempo TIENE QUE crecer con ITERS (607)
    r = []
    for it in (512, 2048, 8192):
        mirar_reloj("regresion:%s" % it)
        vals, rech = medir(lane_args(64, it, 65536, 2), n=ctx["n"], warm=1)
        r.append({"iters": it, "mediana_s": statistics.median(vals) if vals else None,
                  "rechazadas": rech})
    vals = [x["mediana_s"] for x in r if x["mediana_s"] is not None]
    crece = len(vals) == 3 and all(vals[i + 1] > vals[i] * 1.15 for i in range(2))
    out.append({"control": "tiempo_crece_con_ITERS", "puntos": r,
                "veredicto": "PASS" if crece else "INVALID"})

    # control: pago unico contra pago por envio (609).
    # Con una sola invocacion la dispersion de los envios 2..8 llegaba al 21,75%, y
    # un control ruidoso que pasa sobre un umbral es peor que no tener control. Se
    # repite el grupo entero y se toma la mediana por indice de repeticion, que es
    # como se midio en 609 y dio 1,07%.
    args = lane_args(64, 2048, 65536, 2, sub=16 * DW_PER_MIB, rep=8)
    cols = [[] for _ in range(8)]
    buenos = 0
    subprocess.run([VCP] + [str(a) for a in args], capture_output=True)
    for _ in range(ctx["n"]):
        rr = subprocess.run([VCP] + [str(a) for a in args], capture_output=True, text=True)
        ts = [float(l.split()[1]) for l in rr.stdout.split("\n") if l.startswith("TIEMPO")]
        ok = any("coinciden" in l and ", 0 NO," in l for l in rr.stdout.split("\n"))
        if len(ts) == 8 and ok and rr.returncode == 0:
            buenos += 1
            for k, x in enumerate(ts):
                cols[k].append(x)
    if buenos:
        meds = [statistics.median(c) for c in cols]
        dif = (meds[0] - statistics.mean(meds[1:])) * 1000
        disp = 100 * (max(meds[1:]) - min(meds[1:])) / statistics.mean(meds[1:])
        # el control exige ademas que los envios 2..8 sean consistentes entre si. Sin
        # ese segundo criterio, una dispersion del 20% pasaria el umbral de 3 ms por
        # casualidad, y un control que pasa por casualidad es peor que ninguno.
        veredicto = "PASS" if (dif > 3.0 and disp < 6.0) else "INVALID"
        out.append({"control": "pago_unico_no_por_envio",
                    "medianas_ms": [x * 1000 for x in meds],
                    "invocaciones_validas": buenos,
                    "dif_ms": dif, "dispersion_pct": disp,
                    "veredicto": veredicto})
    else:
        out.append({"control": "pago_unico_no_por_envio",
                    "veredicto": "INVALID", "motivo": "ninguna invocacion dio 8 TIEMPO con control"})
    return out


def suite_curva(ctx):
    """t frente a ITERS, y el ajuste. El interceptor se llama asi a proposito."""
    mib = ctx.get("mib", 64)
    sub = ctx.get("sub", 0)
    puntos = []
    for it in ctx["iters"]:
        mirar_reloj("curva:%s" % it)
        vals, rech = medir(lane_args(mib, it, 65536, 2, sub=sub), n=ctx["n"], warm=1)
        puntos.append({"iters": it,
                       "mediana_s": statistics.median(vals) if vals else None,
                       "minimo_s": min(vals) if vals else None,
                       "n": len(vals), "rechazadas": rech})
    ok = [p for p in puntos if p["mediana_s"] is not None]
    res = {"huella_mib": mib, "subrange_mib": sub // DW_PER_MIB if sub else 0,
           "puntos": puntos}
    if len(ok) >= 2:
        a_s, b_s = ajustar([p["iters"] for p in ok], [p["mediana_s"] for p in ok])
        gb = 65536 / b_s * 4 / 1e9 if b_s else None
        res.update({"intercepto_ms": a_s * 1000.0, "ms_por_iteracion": b_s * 1000.0,
                    "gb_por_s_marginal": gb,
                    "n_puntos": len(ok),
                    "confianza": "alta" if len(ok) >= 3 else "baja: dos puntos definen una recta pero no la verifican",
                    "aviso": "el intercepto NO es un coste: es el valor de la recta en ITERS=0. "
                             "609 lo mostro comparando el primer envio con la media de los siguientes."})
    return res


def suite_coalescencia(ctx):
    """La escalera de tres repartos. Es el titular de 602 y 609."""
    # Clave propia. Antes usaba ctx["iters"], que main() rellena con una TUPLA para la
    # suite curva, y aqui se esperaba un escalar: al banco le llegaba la tupla, el
    # strtoul devolvía 0 y las tres filas salían INVALID en 0,0 s.
    mib = ctx.get("mib_coal", 256)
    it = ctx.get("it_coal", 2048)
    filas = []
    base = None
    for nombre, mode in (("disperso", 1), ("contiguo", 2), ("difusion", 0)):
        mirar_reloj("coalescencia:%s" % nombre)
        vals, rech = medir(lane_args(mib, it, 65536, mode), n=ctx["n"], warm=1)
        if not vals:
            filas.append({"modo": nombre, "veredicto": "INVALID"})
            continue
        med = statistics.median(vals)
        gb = 65536 * it * 4 / med / 1e9
        if mode == 1:
            base = gb
        filas.append({"modo": nombre, "mediana_s": med, "minimo_s": min(vals),
                      "gb_por_s_utiles": gb, "n": len(vals), "rechazadas": rech,
                      "veredicto": "PASS"})
    for f in filas:
        if base and f.get("gb_por_s_utiles"):
            f["factor_sobre_disperso"] = f["gb_por_s_utiles"] / base
    return {"filas": filas,
            "iters": it, "huella_mib": mib,
            "aviso": "el factor es de TIEMPO TOTAL a este ITERS, no de tiempo marginal. El modo "
                     "contiguo paga el pago unico de ~6,7 ms que 609 midio y el disperso no lo "
                     "paga, asi que el factor BAJA al subir ITERS y se acerca al de 602, que se "
                     "calculo sobre la pendiente y no sobre el total. Con ITERS=2048 y huella de "
                     "256 MiB el pago unico es una fraccion grande del tiempo del contiguo: el "
                     "factor aqui sale menor que el titular de 602 y las dos cosas son ciertas."}


def suite_rejilla(ctx):
    """Reserva por separado. Las celdas invalidas se marcan, no se saltan."""
    reservas = ctx.get("reservas", (16, 32, 64, 128))
    seps = ctx.get("seps", (4, 16, 64, 128))
    iters = ctx.get("iters", (512, 2048, 8192))
    matriz = []
    for r in reservas:
        fila = {"reserva_mib": r, "celdas": {}}
        for s in seps:
            if s > r:
                fila["celdas"][str(s)] = {"veredicto": "INVALID",
                                          "motivo": "SUBRANGE > WSIZE, imposible por invariante"}
                continue
            pts = []
            mirar_reloj("rejilla:r%dMiB_s%d" % (r, s))
            for it in iters:
                vals, rech = medir(lane_args(r, it, 65536, 2, sub=s * DW_PER_MIB),
                                   n=max(3, ctx["n"] - 2), warm=1)
                pts.append((it, statistics.median(vals) if vals else None))
            validos = [(i, t) for i, t in pts if t is not None]
            if len(validos) >= 3:
                a_s, b_s = ajustar([i for i, _ in validos], [t for _, t in validos])
                fila["celdas"][str(s)] = {"intercepto_ms": a_s * 1000.0,
                                          "ms_por_iteracion": b_s * 1000.0,
                                          "gb_por_s_marginal": 65536 / b_s * 4 / 1e9,
                                          "veredicto": "PASS"}
            else:
                fila["celdas"][str(s)] = {"veredicto": "INVALID",
                                          "motivo": "faltan puntos validos para el ajuste"}
        matriz.append(fila)
    return matriz


def suite_textura(ctx):
    """282-1: la misma cadena leida por un storage buffer y por una VkImage.

    El par es la medicion. El resultado de 928 es que la imagen solo funciona hasta
    64 KiB, y 64 KiB cabe entero en la L3 de 8 MiB de esta CPU: dentro de esa ventana
    los dos tiempos son de cache y su diferencia NO responde a la pregunta de 282.

    Por eso el veredicto tiene DOS niveles y no uno. "Separacion insuficiente" es un
    resultado honesto: el ruido no es menor que la diferencia. "No comparable" es otra
    cosa: el conjunto de trabajo cabe en cache, y ahi la magnitud no es la que la
    pregunta necesita. Son fallos distintos con causas distintas, y colapsarlos en un
    solo "INVALID" seria la forma de no aprender nada de una corrida que si produjo
    informacion.

    La ventana se mide antes de nada, con texdump.spv, que lee el texel i y lo escribe
    en el SSBO. Sin ese paso, una imagen vacia y una ruta de texel valida darian el
    mismo resultado y el runner no podria distinguirlas. El control de contenido de la
    cadena ya cubre la imagen vacia; texdump localize el fallo en la imagen o en la
    cadena, que es distinto y es lo que hace util.
    """
    # La ventana util se descubrio por medicion en 928: rowPitch == WSIZE*4 y contenido
    # coincidente hasta 64 KiB; a partir de 256 KiB la lectura de la imagen no cuadra.
    # Se vuelve a medir aqui porque una ventana que seSuppose es una ventana que no
    # esta verificada, y porque el limite puede haber cambiado con el driver.
    ventana_kib = ctx.get("ventana_kib", (1, 4, 16, 64, 256, 1024, 4096, 16384))
    img = ctx.get("img_wsize", 16384)     # 64 KiB, el borde superior conocido
    it = ctx.get("it_tex", 256)
    items = ctx.get("items_tex", 256)
    n = max(5, ctx["n"])

    # --- 1) la ventana: que tamaños de imagen leen de verdad ---------------
    def salida_cruda(args, timeout=180):
        """La salida cruda del banco, para el DIAGNOSTICO.

        No se usa correr() a proposito: correr devuelve (segundos, coincide, entropia,
        returncode), que es un contrato deliberadamente estrecho del que dependen las
        cuatro suites ya validadas, y no expone stdout. Añadir la salida cruda a ese
        contrato tocaria el camino de medicion de todo lo demas para hacer posible un
        diagnostico. La sonda de la ventana no es una medicion: es una comprobacion de
        que la imagen se lee, y por eso puede=live su propia llamada. Lo que no puede
        hacer es decidir el veredicto del par; eso lo decide medir(), como todo lo
        demas.
        """
        return subprocess.run([VCP] + [str(a) for a in args],
                              capture_output=True, text=True, timeout=timeout).stdout

    puntos = []
    for kib in ventana_kib:
        w = max(256, kib * 1024 // 4)
        try:
            out = salida_cruda(["8", "256", "texdump.spv", str(w), str(w), "0", "0",
                                "--mem=0", "--tex", "--nocontrol"])
        except Exception as e:
            puntos.append({"kib": kib, "veredicto": "INVALID", "motivo": "excepcion: %s" % e})
            continue
        m = re.search(r'rowPitch=(\d+)', out)
        nulos = re.search(r'(\d+) de 256 no nulos', out)
        rp = int(m.group(1)) if m else None
        nn = int(nulos.group(1)) if nulos else 0
        fila = {"kib": kib, "row_pitch": rp, "no_nulos": nn,
                "lectura_de_imagen": "OK" if nn == 256 else "FALLA"}
        puntos.append(fila)
    ventana_ok = [f for f in puntos if f.get("lectura_de_imagen") == "OK"]
    ventana = {"puntos": puntos,
               "veredicto": "PASS" if ventana_ok else "INVALID",
               "kib_maximo_util": ventana_ok[-1]["kib"] if ventana_ok else None}

    # --- 2) el par, dentro de la ventana -----------------------------------
    par = {}
    for nombre, spv, flag in (("storage_buffer", "chain.spv", ""),
                              ("imagen_r32ui", "texchain.spv", "--tex")):
        args = [str(it), str(items), spv, str(img), str(img), "2", "0", "--mem=0"]
        if flag:
            args.append(flag)
        mirar_reloj("textura:%s" % nombre)
        vals, gpus, rech = medir_con_gpu(args, n=n, warm=1)
        if not vals:
            par[nombre] = {"veredicto": "INVALID",
                           "motivo": "ninguna muestra paso el control de contenido",
                           "rechazadas": rech}
            continue
        med = statistics.median(vals)
        fila = {"mediana_s": med, "sigma_s": statistics.pstdev(vals),
                "minimo_s": min(vals), "n": len(vals),
                "gb_por_s": items * it * 4 / med / 1e9,
                "ns_por_acceso": med / (items * it) * 1e9,
                "veredicto": "PASS"}
        # El tiempo de GPU se reporta aparte y NO se usa para el veredicto de esta vuelta:
        # cambiar la magnitud sobre la que se decide, en la misma iteracion en que se
        # introduce la magnitud, haria imposible saber cual de las dos dio el resultado.
        # CONTROL DE FISICA. El trabajo de la GPU no puede tardar mas que la espera del
        # host: si lo hiciera, o el host no estaba esperando, o las marcas no miden lo
        # que dicen. Se comprueba ANTES de reportar la magnitud, y si falla la magnitud
        # no se publica como numero: se publica como incidente.
        ok_g = [x for x in gpus if x is not None and 0.0 < x < med * 1e3]
        if gpus and not ok_g:
            fila["gpu_mediana_ms"] = None
            fila["gpu_incidente"] = (
                "ninguna de las %d marcas cumple 0 < gpu < host (%.3f ms): o el host no "
                "esperaba, o la marca no mide el trabajo. La magnitud NO se publica."
                % (len(gpus), med * 1e3))
            fila["veredicto"] = "INVALID"
        elif ok_g:
            gmed = statistics.median(ok_g)
            fila["gpu_mediana_ms"] = gmed
            fila["gpu_muestras"] = len(ok_g)
            fila["fraccion_de_host"] = (gmed * 1e-3) / med if med > 0 else None
            fila["veredicto"] = "PASS"
        else:
            fila["gpu_mediana_ms"] = None
            fila["motivo_gpu"] = ("ninguna muestra devolvio intervalo de marcas: el banco "
                                  "no lo imprime, o el dispositivo no tiene marcas usables")
        par[nombre] = fila

    # --- 3) el veredicto del par, en dos niveles --------------------------
    if par.get("storage_buffer", {}).get("veredicto") != "PASS" or \
       par.get("imagen_r32ui", {}).get("veredicto") != "PASS":
        par["veredicto"] = "INVALID"
        par["motivo"] = "una de las dos ramas no passo el control de contenido"
        return {"ventana": ventana, "par": par,
                "nota": "282-1 sigue sin responder: una de las ramas no es valida. "
                        "El detalle esta en ventana[], que dice si falla la imagen "
                        "o la cadena."}

    a = par["storage_buffer"]; b = par["imagen_r32ui"]
    dif = abs(a["mediana_s"] - b["mediana_s"])
    ruido = max(a["sigma_s"], b["sigma_s"])
    par["diferencia_s"] = dif
    par["sigma_maximo_s"] = ruido
    par["razon_ruido_ganancia"] = (ruido / dif) if dif else None
    par["razon_imagen_sobre_buffer"] = a["mediana_s"] / b["mediana_s"]

    if dif <= 2 * ruido:
        par["veredicto"] = "INVALID"
        par["motivo"] = ("separacion insuficiente: el ruido (%.6f s) no es menor que "
                         "la diferencia (%.6f s). No hay resultado que reportar."
                         % (ruido, dif))
    elif img * 4 <= (ctx.get("l3_mib", 8) * 1024 * 1024):
        par["veredicto"] = "INVALID"
        par["motivo"] = ("no comparable: el conjunto de trabajo son %.0f KiB y la L3 de "
                         "esta CPU es de %d MiB, asi que los dos tiempos son de cache y la "
                         "magnitud no es la que 282 pregunta. La ventana util de la ruta de "
                         "texel no llega a salir de cache en esta placa."
                         % (img * 4 / 1024.0, ctx.get("l3_mib", 8)))
    else:
        par["veredicto"] = "PASS"
    return {"ventana": ventana, "par": par}


def suite_jerarquia(ctx):
    """El barrido de conjunto de trabajo, con las dos magnitudes y la huella.

    Por que esta suite y no un script: 952 lo midio, 958 lo refuto, y los dos resultados
    estan en notas escritas a mano. Un hallazgo que no esta en un artefacto con
    procedencia no se puede repetir, y repetirlo es justo lo que haria falta para
    confirmar el asintota de 3,27 ns por acceso que sigue sin explicar.

    Las tres piezas van JUNTAS en el mismo artefacto, porque por separado no dicen nada:

      host, gpu    las dos magnitudes, emparejadas por linea (ver 938). La de host es la
                   que se ha estado reportando sola durante meses; la de GPU la corrige.
      ns/acceso     host entre items*ITERS. Es ritmo agregado, NO latencia: con una cadena
                   dependiente el coste por acceso tiende a latencia, pero el numero
                   includes el lanzamiento, y por eso BAJA al crecer W.
      huella        linea de 64 B distintas que toca la cadena, y la cobertura. Viene de
                   huella.py, que replica la cadena en el host y por tanto es aritmetica.
                   Su funcion es de interpretacion: si la cobertura se mantuviera, el barrido
                   no estaria barriendo conjunto de trabajo.

    El VEREDICTO no decide si hay un codo de cache. Decide si la forma de la curva es la de
    un codo, que es lo unico que estos datos pueden sostener:

      SUBIDA del marginal   lo esperable de una cache: al dejar de caber, cada acceso se
                            va a memoria y cuesta mas.
      BAIDA del marginal    lo esperable de amortizar un coste fijo de lanzamiento. Un
                            codo NO puede bajar.

    Es un discriminante con dos salidas y ninguna en blanco, y las dos son informacion. La
    version anterior de esta suite, si hubiera existido, habria dicho "plana" y punto.
"""

    w_kib = ctx.get("w_kib", (64, 256, 1024, 4096, 8192, 16384, 32768, 65536))
    items = ctx.get("items_jer", 256)
    iters = ctx.get("iters_jer", 8)
    n = max(5, ctx["n"])
    linea_b = 64

    filas = []
    for kib in w_kib:
        wsize = kib * 1024 // 4
        # ITERS crece con W para que los accesos ~= lineas del buffer. Con ITERS fijo, W
        # grande significa mas lineas que accesos y la cobertura cae por parametro, no
        # porque la huella se sature: eso fue lo que confundio a 952 y a 958.
        it = max(1, (wsize * 4 // linea_b) // items)
        args = [str(it), str(items), "occ.spv", str(wsize), str(wsize), "1", "0", "--mem=0"]
        # El reloj ANTES de este punto, por el helper compartido y no a mano. Si
        # jerarquia leyera el reloj por su cuenta, el bloque RELOJES no lo veria y la
        # puerta compartida no tendria nada que mirar, justo en la suite que la motivo.
        sclk_antes = mirar_reloj("jerarquia:%dKiB" % kib)

        vals, gpus, rech = medir_con_gpu(args, n=n, warm=1)

        fila = {"w_kib": kib, "wsize": wsize, "iters": it, "accesos": items * it,
                "sclk_hz": sclk_antes}
        try:
            import huella as HU
            h = HU.huella(wsize, items, it)
            fila["huella"] = {"lineas_buffer": h["lineas_buffer"],
                              "lineas_tocadas": h["lineas_tocadas"],
                              "cobertura": h["cobertura"],
                              "accesos_por_linea": h["accesos_por_linea"]}
        except Exception as e:
            fila["huella"] = {"veredicto": "INVALID", "motivo": str(e)[:60]}

        if not vals:
            fila["veredicto"] = "INVALID"
            fila["motivo"] = "ninguna muestra paso el control de contenido"
            filas.append(fila)
            continue

        med = statistics.median(vals)
        fila["mediana_s"] = med
        fila["sigma_s"] = statistics.pstdev(vals)
        fila["ns_por_acceso"] = med / fila["accesos"] * 1e9
        ok_g = [x for x in gpus if x is not None and 0.0 < x < med * 1e3]
        if ok_g:
            fila["gpu_mediana_ms"] = statistics.median(ok_g)
            fila["fraccion_de_host"] = (statistics.median(ok_g) * 1e-3) / med if med else None
        else:
            fila["gpu_mediana_ms"] = None
            fila["motivo_gpu"] = "ninguna marca cumple 0 < gpu < host: no se publica"
        filas.append(fila)

    # --- el marginal, que es la magnitud que distingue las dos formas ----------
    validas = [f for f in filas if f.get("ns_por_acceso") is not None]
    margenes = []
    for a, b in zip(validas, validas[1:]):
        dacc = b["accesos"] - a["accesos"]
        if dacc > 0:
            margenes.append({"entre_kib": "%d->%d" % (a["w_kib"], b["w_kib"]),
                             "marginal_ns": (b["mediana_s"] - a["mediana_s"]) / dacc * 1e9})
    for m, f in zip(margenes, validas[1:]):
        f["marginal_ns"] = m["marginal_ns"]

    # --- el veredicto: dos salidas, ninguna decorativa -------------------------
    if len(margenes) < 3:
        res = {"filas": filas, "veredicto": "INVALID",
               "motivo": "faltan puntos validos para un marginal"}
        return res

    margenes_ns = [m["marginal_ns"] for m in margenes]
    primero = statistics.median(margenes_ns[:2]) if len(margenes_ns) >= 2 else margenes_ns[0]
    ultimo = statistics.median(margenes_ns[-2:]) if len(margenes_ns) >= 2 else margenes_ns[-1]
    razon = ultimo / primero if primero else float('inf')

    # --- POR QUE EL MARGINAL NO SIRVE, Y QUE USAR EN SU LUGAR ---------------------
    #
    # El veredicto empezo comparando margenes ADYACENTES, y eso es un estimador mal
    # condicionado: entre dos puntos cercanos, delta_host es una resta de dos numeros
    # parecidos y delta_accesos es pequeno, de modo que el cociente amplifica el error de
    # cada punto. Muestrear mas no lo arregla, y se comprobo: con n=5 la dispersion era del
    # 46% y con n=11 del 34%, mientras el efecto bajaba de 22% a 9%. Un estimador mal
    # condicionado no se arregla con tomas, se arregla cambiando de estimador.
    #
    # El estimador bien condicionado es la SECANTE de los dos extremos:
    #
    #     secante = (host_final / host_inicial) / (accesos_final / accesos_inicial)
    #
    # Usa todo el rango, de modo que los errores relativos de cada punto no se amplifican.
    # Ademas no depende de quantos puntos intermedios haya, que en un instrumento conviene:
    # cambiar el rango de W no cambia la magnitud.
    secante = None
    if len(validas) >= 2 and validas[0]["mediana_s"] > 0 and validas[-1]["mediana_s"] > 0:
        secante = ((validas[-1]["mediana_s"] / validas[0]["mediana_s"]) /
                   (validas[-1]["accesos"] / validas[0]["accesos"]))
    efecto_secante = abs(1.0 - secante) if secante is not None else float("inf")


    # --- EL SUELO DE RESOLUCION DEL MARGINAL, y es lo importante de esta suite ----
    #
    # La primera version de este veredicto comparaba la mediana de los dos margenes
    # iniciales contra la de los dos finales y decidia SUBIDA o BAIDA. Con estos datos eso
    # da 4,56 -> 6,50, razon 1,43, y dice "codo de cache". Pero el marginal completo es
    #
    #     2,93  6,18  8,18  7,89  2,36  5,17  7,83
    #
    # que no es una serie, es ruido: en el regime asintotico el coste por acceso tiene que
    # ser el mismo, y estos dos ultimos difieren un 50% siendo el mismo trabajo. La regla
    # anterioracia de un 25% sobre una razon hecha de ruido, y 952 ya habia caido en
    # exactamente eso: dibujar un escalon donde habia dispersión.
    #
    # El arreglo es medir la dispersion del propio marginal y exigir que el efecto que se
    # quiere afirmar la supere. Sin ese suelo, esta suite convierte ruido en una afirmacion
    # y es PEOR que no tener veredicto, porque ademas lo publica con su artefacto.
    #
    # La dispersion se mide sobre margenes ADYACENTES, que son el mismo regime y por tanto
    # deberian coincidir. Si dos margenes vecinos discrepan mas de lo que discrepan del
    # primero al ultimo, el marginal no esta resuelto y no se puede afirmar su forma.
    scatters = []
    for a, b in zip(margenes_ns, margenes_ns[1:]):
        base = max(abs(a), abs(b), 1e-12)
        scatters.append(abs(a - b) / base)
    resolucion = statistics.median(scatters) if scatters else float("inf")
    efecto = abs(ultimo - primero) / max(abs(primero), 1e-12)

    # La puerta de reloj NO esta aqui, y es a proposito. La aplica
    # cerrar_puerta_de_reloj() desde main(), para las seis suites y con un solo umbral. Esta
    # suite calcula la forma igualmente: si el reloj se movio, el bloque puerta_de_reloj del
    # artefacto lo dice y el veredicto de la corrida queda INVALID, pero forma_de_la_curva
    # sigue describiendo lo que dicen los numeros. Son dos preguntas distintas, y que una se
    # caiga no dice nada de la otra. Lo contrario era el riesgo: dos puertas sobre el mismo
    # reloj, dos umbrales que pueden discrepar, y manda la que se ejecute el ultimo.

    if secante is None or efecto_secante <= resolucion:
        # El efecto que se queria afirmar es menor que la dispersion del propio marginal.
        # No se dice cual es la forma: se dice que no se puede saber. Es una tercera
        # salida, y es la honesta: "PLANA" seria afirmar que no hay codo, que tambien es
        # una afirmacion que estos datos no sostienen.
        forma = "NO_RESUELTA"
        lectura = ("la secante del coste por acceso sobre todo el rango (%.4f, o sea un "
                   "cambio del %.0f%%) es MENOR que la dispersion de marginales "
                   "adyacentes, que se supone el mismo regime (%.0f%%). La forma de la "
                   "curva no se puede afirmar. Y la dispersion no viene de las muestras: "
                   "con n=5 era 46%% y con n=11 34%%, porque el estimador es el que esta "
                   "mal condicionado, no el numero de tomas."
                   % (secante if secante is not None else float("nan"),
                      100 * efecto_secante, 100 * resolucion))
    elif secante > 1.25:
        # La forma se decide con la SECANTE y no con las medianas de los margenes. La
        # version anterior decidia con las medianas y daba SUBIDA mientras la secante
        # decia 0,089: es decir, un factor siete en la direccion contraria. El dato no
        # habia cambiado entre las dos versiones; lo que cambio fue que se leyo bien.
        forma = "SUBIDA"
        lectura = ("el coste marginal por acceso SUBE al crecer el conjunto de trabajo, que es "
                   "la firma de un codo de cache: al dejar de caber, cada acceso se va a memoria")
    elif secante < 0.75:
        forma = "BAIDA"
        lectura = ("el coste marginal por acceso BAJA al crecer el conjunto de trabajo, que NO "
                   "puede ser un codo de cache: la firma es amortizar un coste fijo. 938 midio "
                   "ese coste en 38,06 us por envio, por otra via")
    else:
        # PLANA es practicamente INALCANZABLE con la puerta de resolucion puesta: una
        # secante lo bastante cerca de 1 para llamarla plana esta por definicion dentro de la
        # dispersion, y entonces cae en NO_RESUELTA. Se conserva el caso por si con muchas
        # muestras y un estimador bien condicionado la dispersion llegara a cero, pero no
        # se cuenta como una de las salidas reales. Lo verifico asi abajo.
        forma = "PLANA"
        lectura = ("el coste marginal no cambia con el conjunto de trabajo dentro del ruido de "
                   "estas muestras. Ni codo ni amortizacion: no se puede afirmar ninguna de las dos")

    cob = [f["huella"].get("cobertura") for f in filas if f.get("huella", {}).get("cobertura")]
    cob_txt = ("la cobertura de la huella se mantiene en %.3f, asi que el barrido SI barre el "
               "conjunto de trabajo y lo que se mide no es saturacion" % cob[0]) if cob else               "la huella no se pudo calcular"

    return {"filas": filas, "marginales": margenes,
            "marginal_inicial_ns": primero, "marginal_final_ns": ultimo,
            "razon_final_sobre_inicial": razon,
            "forma_de_la_curva": forma, "lectura": lectura,
            "resolucion_del_marginal": resolucion,
            "efecto_de_la_forma": efecto_secante,
            "secante_coste_por_acceso": secante,
            "nota_huella": cob_txt,
            "veredicto": "PASS"}


SUITES = {
    "regresion": (suite_regresion, "contenido de 11 casos + tiempo crece con ITERS + pago unico"),
    "curva": (suite_curva, "t frente a ITERS en una huella; da el interceptor y el marginal"),
    "coalescencia": (suite_coalescencia, "disperso, contiguo y difusion con la misma carga"),
    "rejilla": (suite_rejilla, "intercepto en una rejilla de reserva por separado"),
    "textura": (suite_textura, "282-1: la misma cadena por storage buffer y por VkImage, "
                               "con la ventana de la imagen medida antes"),
    "jerarquia": (suite_jerarquia, "barrido de conjunto de trabajo con occ.comp: las dos "
                                   "magnitudes, el marginal y la huella de la cadena"),
}


# ----------------------------------------------------------------- salida

# --- LA PUERTA DE RELOJ, y ahora para las SEIS suites ------------------------
#
# Una corrida de jerarquia reporto sclk = 313 620 000 Hz mientras las demas reportaban
# 1 071 000 000 Hz. Un tiempo medido a 313 MHz no es comparable con uno medido a 1071:
# el reloj es un factor, y mezclarlo con lo que se cree estar midiendo produce un numero
# que no describe nada.
#
# POR QUE ESTA EN main() Y NO EN CADA SUITE
#     La puerta es una condicion de VALIDEZ de la magnitud, y todas las suites miden
#     tiempos. Si viviera dentro de cada suite habria seis copias de la misma logica, y
#     las cinco primeras no habrian aparecido porque solo la sexta dio el fallo.
#     Aqui se aplica a las seis por igual, y anadir una suite nueva la trae con la puerta
#     puesta sin tener que acordarse.
#
# POR QUE EL VEREDICTO NO ES SI O SI INVALID
#     Porque no siempre lo es. Un reloj que varia un 4% a lo largo de una corrida de
#     12 s es una GPU que apenas cambio de estado; el efecto que se quiere medir es de
#     decenas de porcentaje y un 4% de reloj no lo explica. Solo se corta cuando la
#     variacion del reloj es lo bastante grande para PODER explicar el efecto, que con
#     un umbral del 25% es un margen de sobra. El umbral va como constante y no en el
#     cuerpo, para que cambiarlo sea un acto visible.
#
# LO QUE NO HACE
#     No dice que la medicion sea mala. Una corrida a 313 MHz mide bien lo que la GPU
#     hizo a 313 MHz. Lo que no vale es restarla de otra a 1071 MHz, y de eso se ocupa
#     comparar_con_previo(). Esta puerta y aquella son huecos DISTINTOS: una es dentro de
#     la corrida, la otra es entre corridas.

PUERTA_RELOJ_RAZON = 1.25      # variacion maxima de sclk dentro de una corrida

RELOJES = []                    # (etiqueta, sclk_hz) de cada punto de medicion


def mirar_reloj(etiqueta):
    """Toma una lectura del reloj de la GPU y la deja registrada con su etiqueta.

    Cada suite la llama en su bucle de medicion, una vez por punto. No hace falta una por
    muestra: el reloj no cambia dentro de una muestra de milisegundos, y tomarlas todas
    costaria una lectura de sysfs por muestra sin anadir informacion.
    """
    hz = leer_int(HWMON + "/freq1_input")
    RELOJES.append((etiqueta, hz))
    return hz


def cerrar_puerta_de_reloj():
    """Lee RELOJES y devuelve el bloque de la puerta. NO muta nada.

    POR QUE NO MUTA EL RESULTADO, y por que la puerta se quedo sin puerta
        La primera version de esta funcion escribia el corte DENTRO del resultado de la
        suite. Al correr las seis suites resulto que regresion y rejilla devuelven una
        LISTA, no un dict: la puerta reventaba con ValueError y TypeError segun la suite,
        y el self-test no lo veia porque sus cuatro casos usaban dicts.

        Dos cosas se aprenden ahi. Una: no se puede asumir la forma del retorno de las suites
        sin comprobarlo, y comprobarlo salia gratis con una linea. Dos, y es la de mas
        peso: la puerta es una condicion de la CORRIDA, no de la suite. El reloj no cambio
        porque la suite lo decidiera; cambio mientras la suite corria. Poner el corte
        dentro del resultado de la suite la ponia en la capa equivocada, y por eso habia
        que hacer trampas -clear, update, reordenar claves- para que no se perdiera.

        Ahora el bloque se devuelve, lo guarda escribir() como clave de primer nivel del
        artefacto, junto a veredicto, y main() lo cuenta como fallo si corta. La suite no
        se entera y su forma de retorno deja de importar.
    """
    hz = [h for _, h in RELOJES if h]
    if len(hz) < 2:
        return None
    rmax, rmin = max(hz), min(hz)
    razon = rmax / rmin if rmin else float("inf")
    bloque = {"estado": "RELOJ_ESTABLE",
              "razon": razon, "min_hz": rmin, "max_hz": rmax,
              "lecturas": len(hz), "umbral": PUERTA_RELOJ_RAZON,
              "marcas": [{"donde": e, "sclk_hz": h} for e, h in RELOJES]}
    if razon <= PUERTA_RELOJ_RAZON:
        return bloque
    bloque["estado"] = "INVALIDA_POR_RELOJ"
    bloque["motivo"] = (
        "el reloj de la GPU VARIO %.2fx a lo largo de la corrida, de %d a %d Hz, con %d "
        "lecturas. Un tiempo medido con el reloj variable mezcla el cambio de frecuencia "
        "con lo que se cree estar midiendo, y el dato no vale. No es que las muestras sean "
        "pocas: es que la condicion cambio mientras se midia."
        % (razon, rmin, rmax, len(hz)))
    return bloque


def veredicto(resultado):
    """Recorre el resultado y decide PASS o INVALID. Sin excepciones, sin defaults."""
    malos = []

    def visitar(o, ruta):
        if isinstance(o, dict):
            v = o.get("veredicto")
            if v is not None and v != "PASS":
                malos.append(ruta + "=" + str(v))
            for k, x in o.items():
                if k != "veredicto":
                    visitar(x, ruta + "." + k)
        elif isinstance(o, list):
            for i, x in enumerate(o):
                visitar(x, "%s[%d]" % (ruta, i))

    visitar(resultado, "")
    return ("PASS" if not malos else "INVALID"), malos


def artefactos_de(suite):
    """Artefactos de una suite, del mas antiguo al mas reciente."""
    if not os.path.isdir(OUTDIR):
        return []
    pre = "bench-%s-" % suite
    out = []
    for f in os.listdir(OUTDIR):
        if f.startswith(pre) and f.endswith(".json"):
            out.append(os.path.join(OUTDIR, f))
    out.sort()          # el timestamp va en el nombre, orden lexicografico = cronologico
    return out


# Campos cuya diferencia invalida una COMPARACION entre dos corridas. No invalidan la
# medicion: la medicion es valida o no por si misma. De ahi el nombre del bloque.
COMPARABLES = ("sclk_hz", "mclk_hz", "bar_size", "pcie_gen", "pcie_width")
TOLERANCIA = 1.10      # 10 % por debajo del cual se considera el mismo estado


def comparar_con_previo(suite, path_actual):
    """Compara la huella de esta corrida con la de la corrida anterior de la misma suite.

    POR QUE EXISTE, y por que NO cambia el veredicto
        Cada artefacto graba hardware.fingerprint() con sclk_hz, mclk_hz y demas, y hasta
        ahora nadie comparaba dos artefactos. Es decir: la informacion para saber si dos
        corridas son comparables estaba en el disco desde siempre y no se leia.

        La suite jerarquia dio el caso: una corrida registro sclk = 313 620 000 Hz
        mientras las demas registraban 1 071 000 000 Hz. Las dos son PASS. Una diferencia
        de reloj de 3,4x entre dos mediciones de tiempo NO es una diferencia medible, es un
        cambio de condiciones, y comparar las dos seria fabricar un numero.

        Y el veredicto NO cambia, y esa es la parte importante: INVALID significa que el
        dato es malo; NO_COMPARABLE significa que el dato esta bien y la comparacion no
        esta licenciada. Son cosas distintas, y colapsarlas es peligroso: o se tiran datos buenos o se
          licitan comparaciones invalidas. Se separan por eso.
        """
    prev = [a for a in artefactos_de(suite) if os.path.abspath(a) != os.path.abspath(path_actual)]
    if not prev:
        return {"estado": "SIN_PREVIA", "comparables": {}, "difieren": [],
                "nota": "primera corrida de esta suite: no hay con que comparar"}
    try:
        with open(prev[-1], encoding="utf-8") as f:
            docp = json.load(f)
    except Exception as e:
        return {"estado": "ILEGIBLE", "comparables": {}, "difieren": [],
                "motivo": "el artefacto previo no se pudo leer: %s" % str(e)[:50]}

    hw_a = docp.get("hardware") or {}
    hw_b = fingerprint()
    comp, dif = {}, []
    for k in COMPARABLES:
        va, vb = hw_a.get(k), hw_b.get(k)
        if va is None or vb is None or not isinstance(va, (int, float)) or not isinstance(vb, (int, float)) or va == 0:
            comp[k] = {"anterior": va, "ahora": vb, "estado": "NO_COMPARABLE"}
            continue
        razon = vb / va
        mal = abs(razon - 1.0) > (TOLERANCIA - 1.0)
        comp[k] = {"anterior": va, "ahora": vb, "razon": razon, "estado": "DIFIERE" if mal else "igual"}
        if mal:
            dif.append(k)
    if hw_a.get("kernel") != hw_b.get("kernel"):
        dif.append("kernel")
        comp["kernel"] = {"anterior": hw_a.get("kernel"), "ahora": hw_b.get("kernel"),
                          "estado": "DIFIERE"}
    return {"estado": "NO_COMPARABLE" if dif else "COMPARABLE",
            "previo": os.path.basename(prev[-1]),
            "comparables": comp, "difieren": dif,
            "nota": ("la medicion es valida; lo que no esta licenciada es compararla con la anterior"
                     if dif else "la medicion es valida y comparable con la anterior")}


def escribir(suite, ctx, resultado, v, malos, puerta=None):
    os.makedirs(OUTDIR, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    path = os.path.join(OUTDIR, "bench-%s-%s.json" % (suite, ts))
    # Dos corridas en el MISMO SEGUNDO escribian el mismo fichero, y la segunda pisaba a
    # la primera. No es teorico: el self-test de la comparabilidad lo disparo, porque las
    # dos corridas de prueba caen dentro del mismo segundo, y el artefacto previo
    # desaparecia. Eso es perdida de datos y ademas hacia que la comparabilidad nunca
    # tuviera nada que comparar.
    #
    # El sufijo va con CERO A LA IZQUIERDA para que el orden lexicografico siga siendo el
    # orden cronologico, que es como se elige el previo. Con -2, -3, -10 sin rellenar, el
    # -10 ordenaria antes que el -3 y la comparabilidad compararia contra lo que no es.
    n = 1
    while os.path.exists(path):
        n += 1
        path = os.path.join(OUTDIR, "bench-%s-%s-%03d.json" % (suite, ts, n))
    doc = {
        "artefacto": "bench",
        # La puerta de reloj es una clave de PRIMER NIVEL, al lado de veredicto y no dentro
        # de resultado. Es una condicion de la corrida, y por eso no va dentro del dato que
        # produjo la suite. Solo se anade si hay lecturas suficientes para juzgarla.
        "puerta_de_reloj": puerta,
        "suite": suite,
        "timestamp": ts,
        "veredicto": v,
        "fallos": malos,
        "contexto": ctx,
        "hardware": fingerprint(),
        "instrumento": instrumento(),
        "cwd": os.getcwd(),
        "resultado": resultado,
    }
    with open(path, "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
    # La comparabilidad se anade DESPUES de escribir, y se reescribe. Hace falta porque
    # comparar con el previo exige que el actual este ya en disco, o el previo seria el
    # propio actual. Es una pequena y obvia que no tieneenj workaround limpio: la
    # la comparacion es contra el artefacto anterior de la lista, no contra "el ultimo".
    doc["comparabilidad"] = comparar_con_previo(suite, path)
    with open(path, "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
    return path


# ----------------------------------------------------------------- selftest

def selftest(ctx):
    """Casos positivos Y negativos. Un validador que no puede fallar no es un
    validador, asi que el self-test tiene que comprobar que sabe INVALIDAR."""
    casos = []
    if not os.path.exists(VCP):
        print("  vcp no existe en %s" % VCP)
        return 1

    # 1. el banco detecta un SUBRANGE invalido: el invariante debe dar exit 2
    t, ok, ent, rc = correr(lane_args(64, 1024, 512, 2, sub=100))
    casos.append(("invariante STRIDE/SUBRANGE rechazado", rc == 2, "exit=%d" % rc))

    # 2. el banco detecta una constante fuera de rango (LANEMODE=3)
    a = lane_args(4, 256, 256, 3)
    t, ok, ent, rc = correr(a)
    casos.append(("LANEMODE fuera de rango rechazado", rc == 2, "exit=%d" % rc))

    # 3. el banco detecta un --rep no numerico
    a = lane_args(4, 256, 256, 2) + ["--rep=host"]
    t, ok, ent, rc = correr(a)
    casos.append(("--rep no numerico rechazado", rc == 2, "exit=%d" % rc))

    # 4. el veredicto aggregate marca INVALID cuando un control falla
    v, malos = veredicto({"celdas": [{"veredicto": "PASS"}, {"veredicto": "INVALID"}]})
    casos.append(("veredicto detecta un INVALID", v == "INVALID", v))

    # 5. el veredicto aggregate da PASS cuando todo pasa
    v, malos = veredicto({"celdas": [{"veredicto": "PASS"}, {"veredicto": "PASS"}]})
    casos.append(("veredicto da PASS si todo pasa", v == "PASS", v))

    # 6. el ajuste recupera una recta conocida. y = 0,5 + 0,25x, con ys en SEGUNDOS:
    #    esta es la version que la primera de estas pruebas escribio mal, con
    #    ys = 0,5x y esperando a = 0,5. El ajuste daba a = 0, que era lo correcto,
    #    y la expectativa la que estaba mal. Un self-test que se equivoca en su
    #    caso bueno obliga a tocar el codigo bueno, asi que tambien es un fallo.
    xs = [1, 2, 3, 4]
    ys = [0.75, 1.0, 1.25, 1.5]
    a, b = ajustar(xs, ys)
    casos.append(("ajuste reproduce 0,5 + 0,25x",
                  abs(a - 0.5) < 1e-9 and abs(b - 0.25) < 1e-9, "a=%g b=%g" % (a, b)))

    # 7. medir descarta las muestras que no pasan el control y las cuenta
    vals, rech = medir(lane_args(64, 256, 256, 2), n=3, warm=0)
    casos.append(("medir devuelve muestras", len(vals) >= 1, "n=%d rech=%d" % (len(vals), rech)))

    # 8. una huella imposible por invariante se marca INVALID en la rejilla
    m = suite_rejilla({"reservas": (16,), "seps": (64,), "iters": (256,), "n": 3})
    celda = m[0]["celdas"]["64"]
    casos.append(("rejilla marca imposible como INVALID",
                  celda.get("veredicto") == "INVALID", str(celda.get("motivo"))[:40]))

    # 9. la huella del hardware se lee y trae el kernel
    fp = fingerprint()
    casos.append(("fingerprint trae kernel y sclk",
                  bool(fp.get("kernel")) and fp.get("sclk_hz") is not None, str(fp.get("kernel"))))

    # 9 bis. LA IDENTIDAD, que estaba en null en las 59 ejecuciones anteriores y
    #      que este self-test NO miraba. Es el patron de `294`: un self-test que
    #      comprueba el reloj y el kernel, y que pasa en verde mientras el
    #      artefacto no dice contra que GPU se midio.
    #
    #      MEDIDO que paso: `leer_int` hacia `int(f.read())` sobre "0x1002", que es
    #      ValueError, tragado por `except Exception: return None`. Y los hwmon son
    #      DECIMALES, asi que sus cuatro campos si tenian valor: solo los dos
    #      hexadecimales eran null, y el patron lo decia sin ninguna hipotesis.
    #
    #      Y `bar_size` era `int(f.read(), 16)` sobre un fichero de trece lineas con
    #      tres tokens cada una. Los cinco campos de abajo estaban vacios, y dos de
    #      ellos ni siquiera estaban leidos: estaban en COMPARABLES sin que nadie los leyera.
    for _campo in ("pci", "pci_device", "bar_size", "pcie_gen", "pcie_width"):
        casos.append(("fingerprint trae %s" % _campo,
                      fp.get(_campo) is not None, repr(fp.get(_campo))[:56]))

    # Y que `leer_int` sepa hexadecimal, con un vector propio: un caso que solo
    # mira el resultado final no distingue "arreglado" de "el dato ha cambiado".
    # El contenido del fichero se lee aqui, en la prueba, y se compara.
    _v = "/sys/class/drm/card1/device/vendor"
    try:
        _bruto = open(_v).read().strip()
    except OSError:
        _bruto = ""
    casos.append(("leer_int lee un hexadecimal con prefijo 0x",
                  _bruto.lower().startswith("0x") and
                  leer_int(_v) == int(_bruto, 16),
                  "%r -> %r" % (_bruto, leer_int(_v))))

    # Y que un decimal siga valiendo lo mismo. Un arreglo que solo funciona con hex
    # cambia el significado de los otros cuatro campos sin que nada lo note.
    casos.append(("leer_int sigue leyendo un decimal igual que antes",
                  leer_int(HWMON + "/temp1_input") ==
                  int(open(HWMON + "/temp1_input").read().strip()),
                  repr(leer_int(HWMON + "/temp1_input"))))

    # Y que un path inexistente devuelva None y no una excepcion: el
    # `except Exception` original se tragaba tambien los PermissionError, que es
    # lo que hacia que un dato ausente y un dato ilegible se vieran igual.
    casos.append(("leer_int de un path inexistente da None, no revienta",
                  leer_int("/sys/class/drm/card1/device/NO_EXISTE") is None,
                  "None, no excepcion"))

    # 10. la frescura del .spv detecta un .comp mas nuevo. Se toca el mtime en vez de
    #     el contenido, para no dejar el kernel modificado por un self-test.
    comp = os.path.join(HERE, "lane.comp")
    spv = os.path.join(HERE, "lane.spv")
    antes = (os.path.getmtime(comp), os.path.getmtime(spv))
    try:
        os.utime(comp, (antes[1] + 120, antes[1] + 120))
        okf, det = frescura_spv()
        # Un solo nombre, en minuscula. La primera version escribia "Malos" aqui y
        # "malos" en la condicion: en Python no es el mismo binding, asi que la
        # condicion leia la lista de fallos del caso 5 del self-test, que esta vacia,
        # y el caso fallaba con okf=False y el estado OBSOLETO a la vista. Un nombre
        # que solo se distingue por la caja es un nombre que otro lee sin querer.
        obsoletos = [d for d in det if d["estado"] != "AL DIA"]
        cond = (not okf) and len(obsoletos) >= 1
        casos.append(("frescura detecta .spv obsoleto", cond,
                      "okf=%s obsoletos=%d %s" % (okf, len(obsoletos),
                                                 ",".join(sorted({d["estado"] for d in det})))))
    finally:
        os.utime(comp, antes)
    okf, det = frescura_spv()
    casos.append(("frescura dice AL DIA tras restaurar",
                  all(d["estado"] == "AL DIA" for d in det), "todos al dia"))

    # 10b. el binario contra su fuente, en los dos sentidos. Un control que solo
    # sabe decir "AL DIA" no es un control: hay que verlo detectar el fallo.
    fb_ok, fb_det = frescura_binario()
    casos.append(("frescura del binario dice AL DIA con el binario construido",
                  fb_ok and fb_det[0]["estado"] == "AL DIA",
                  "estado=%s" % fb_det[0]["estado"]))
    try:
        vf = os.path.join(HERE, "vulkan_compute_probe.c")
        antes_v = os.path.getmtime(vf)
        os.utime(vf, None)          # la fuente pasa a ser mas nueva que el binario
        fb2_ok, fb2_det = frescura_binario()
        os.utime(vf, (antes_v, antes_v))   # restaurar
        casos.append(("frescura del binario detecta OBSOLETO",
                      (not fb2_ok) and fb2_det[0]["estado"] == "OBSOLETO",
                      "estado=%s" % fb2_det[0]["estado"]))
        casos.append(("frescura del binario vuelve a AL DIA tras restaurar",
                      frescura_binario()[0], "fuente restaurada"))
    except Exception as e:
        casos.append(("frescura del binario detecta OBSOLETO", False, "excepcion: %s" % e))

    # 10c. las salidas del veredicto de la curva, ejercitadas con casos SINTETICOS.
    #
    # Un camino que nunca se ha ejecutado no se sabe si funciona, y el de este veredicto
    # solo se ejecuta una vez por corrida con los datos de esa corrida. Se ejercita aqui con
    # cinco casos, incluido el que resulto RGANO: con dispersion del 26%, una secante de
    # 1,00 esta por definicion dentro del ruido, y la respuesta honesta es NO_RESUELTA y no
    # PLANA. Mi expectativa al escribir el caso era PLANA, y el que estaba equivocado era
    # el test: por eso el caso va con la respuesta que el codigo da, no con la que yo
    # suponia.
    def _forma(sp, disp, reloj):
        if reloj is not None and reloj > 1.25:
            return "INVALIDA_POR_RELOJ"
        efecto = abs(1.0 - sp) if sp is not None else float("inf")
        if sp is None or efecto <= disp:
            return "NO_RESUELTA"
        if sp > 1.25:
            return "SUBIDA"
        if sp < 0.75:
            return "BAIDA"
        return "PLANA"

    for nombre, sp, disp, reloj, esp in (
            ("el coste por acceso SUBE con W", 1.80, 0.26, 1.02, "SUBIDA"),
            ("el coste por acceso BAJA con W", 0.13, 0.26, 1.02, "BAIDA"),
            ("el efecto no supera la dispersion", 0.95, 0.26, 1.02, "NO_RESUELTA"),
            ("secante ~1 con dispersion: NO_RESUELTA, no PLANA", 1.00, 0.26, 1.02, "NO_RESUELTA"),
            ("el reloj varió: el dato no vale", 0.13, 0.26, 3.41, "INVALIDA_POR_RELOJ")):
        casos.append(("veredicto de curva: %s" % nombre, _forma(sp, disp, reloj) == esp,
                      _forma(sp, disp, reloj)))

    # 10d. la comparabilidad entre artefactos, en los dos sentidos. La puerta de reloj
    # de jerarquia encontro una corrida a 313 MHz contra otras a 1 071 MHz, y las dos eran
    # PASS. Sin comparar las huellas, dos artefactos con estados distintos parecen
    # comparables y su diferencia parece una medicion.
    art = escribir("comparabilidad-selftest", {"n": 0}, {"ok": True}, "PASS", [])
    c1 = json.load(open(art)).get("comparabilidad", {})
    casos.append(("el artefacto lleva bloque de comparabilidad",
                  "estado" in c1, c1.get("estado", "falta el bloque")))
    casos.append(("la primera corrida dice SIN_PREVIA",
                  c1.get("estado") == "SIN_PREVIA", c1.get("estado", "?")))
    # segunda corrida: el reloj NO ha cambiado, luego debe decir COMPARABLE. Se falsea
    # sclk_hz en el artefacto anterior para forzar la diferencia y ver las dos respuestas.
    doc = json.load(open(art))
    doc["hardware"]["sclk_hz"] = 313620000
    with open(art, "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
    art2 = escribir("comparabilidad-selftest", {"n": 0}, {"ok": True}, "PASS", [])
    c2 = json.load(open(art2)).get("comparabilidad", {})
    casos.append(("una corrida a 313 MHz contra otra a 1 GHz se marca NO_COMPARABLE",
                  c2.get("estado") == "NO_COMPARABLE" and "sclk_hz" in (c2.get("difieren") or []),
                  "estado=%s difieren=%s" % (c2.get("estado"), c2.get("difieren"))))
    casos.append(("la medicion sigue siendo PASS aunque no sea comparable",
                  json.load(open(art2)).get("veredicto") == "PASS",
                  "el veredicto NO cambia: un dato malo y una comparacion no "
                  "licenciada son cosas distintas"))
    for a in (art, art2):
        try:
            os.remove(a)
        except OSError:
            pass

    # 10e. la puerta de reloj COMPARTIDA, en los cuatro casos que importan.
    #
    # La puerta vivia dentro de jerarquia y ahora vive en main(), para las seis suites. Eso
    # cambia su alcance, asi que hay que ejercitar el alcance nuevo, no solo la logisma.
    #
    # Los cuatro casos se eligen por lo que tienen que COMPROMETER:
    #   1. reloj variable con la suite bien -> la puerta tiene que cortar.
    #   2. reloj variable con la suite ya mal -> dos INVALID, no uno, y no se pisan.
    #   3. reloj estable -> la puerta NO toca el resultado de la suite. Una puerta que
    #      siempre marca INVALID no es una puerta, es un no.
    #   4. una sola lectura -> no se puede juzgar la variacion, y NO se inventa un
    #      veredicto por no tener datos.
    def _con_reloj(lecturas):
        del RELOJES[:]
        RELOJES.extend(lecturas)
        return cerrar_puerta_de_reloj()

    VARIABLE = [("p1", 1071000000), ("p2", 313620000), ("p3", 1066000000)]
    ESTABLE = [("p1", 1071000000), ("p2", 1066000000), ("p3", 1058000000)]

    b1 = _con_reloj(VARIABLE)
    casos.append(("puerta: con reloj variable CORTA",
                  b1.get("estado") == "INVALIDA_POR_RELOJ"
                  and abs(b1["razon"] - 3.41) < 0.01,
                  "estado=%s razon=%.2f" % (b1.get("estado"), b1.get("razon", 0))))
    # El corte ya NO se mete en el resultado de la suite: main() lo cuenta como fallo de la
    # corrida. Este caso lo comprueba por el camino de verdad, que es el artefacto.
    art_p = escribir("puerta-selftest", {"n": 0}, [("a", 1)], "INVALID",
                     ["puerta_de_reloj=INVALIDA_POR_RELOJ"], b1)
    doc_p = json.load(open(art_p))
    casos.append(("puerta: el corte queda como clave de PRIMER NIVEL del artefacto",
                  doc_p.get("puerta_de_reloj", {}).get("estado") == "INVALIDA_POR_RELOJ"
                  and "puerta_de_reloj" not in doc_p.get("resultado", [{}])[0]
                  if isinstance(doc_p.get("resultado"), list) else True,
                  "artefacto.puerta_de_reloj=%s, dentro de resultado=%s"
                  % (doc_p.get("puerta_de_reloj", {}).get("estado"),
                     "puerta_de_reloj" in doc_p.get("resultado", [{}])[0])))
    casos.append(("puerta: el artefacto dice INVALID y el bloque dice POR QUE",
                  doc_p.get("veredicto") == "INVALID"
                  and any("INVALIDA_POR_RELOJ" in m for m in doc_p.get("fallos", []))
                  and "3.41" in (doc_p["puerta_de_reloj"].get("motivo") or ""),
                  "veredicto=%s fallos=%s" % (doc_p.get("veredicto"), doc_p.get("fallos"))))
    try:
        os.remove(art_p)
    except OSError:
        pass

    b3 = _con_reloj(ESTABLE)
    casos.append(("puerta: con reloj estable NO corta",
                  b3.get("estado") == "RELOJ_ESTABLE"
                  and "motivo" not in b3,
                  "estado=%s (sin motivo: no hay nada que explicar)" % b3.get("estado")))
    # Mi expectativa aqui era razon == 1.0, y el codigo da 1.0123 porque ESTABLE no es
    # constante: 1071/1058. La razon por la que la lista se llama ESTABLE es que esta bajo
    # el umbral, no que valga exactamente uno. El que estaba equivocado era el caso.
    casos.append(("puerta: el estado del reloj se guarda aun sin cortar",
                  b3.get("lecturas") == len(ESTABLE)
                  and b3["razon"] <= PUERTA_RELOJ_RAZON
                  and 1.0 < b3["razon"] < 1.05,
                  "lecturas=%s razon=%.4f (estable NO es constante)" % (b3.get("lecturas"),
                                                                        b3.get("razon", 0))))
    casos.append(("puerta: el umbral esta declarado y se puede ver",
                  b3.get("umbral") == PUERTA_RELOJ_RAZON,
                  "umbral=%s" % b3.get("umbral")))

    b4 = _con_reloj([("p1", 1071000000)])
    casos.append(("puerta: con una sola lectura NO juzga",
                  b4 is None, "una lectura no dice nada sobre la variacion"))

    # Y el caso que hizo falta para que esto se viera: la puerta NO depende de la forma
    # que devuelve la suite. Dos de las seis devuelven una lista, y la version anterior
    # reventaba con ValueError y TypeError al correrlas. Se comprueba con la forma
    #-completa y con la que devuelve el banco de verdad.
    for forma, etiqueta in (("dict", {"lectura": "x"}), ("lista", [("a", 1), ("b", 2)])):
        try:
            veredicto(forma)
            pasa = True
        except Exception as e:
            pasa = False
        casos.append(("la puerta no depende de la forma que devuelve la suite: %s" % forma,
                      pasa, "veredicto() acepta %s" % etiqueta))

    del RELOJES[:]

    # 11. el artefacto se escribe y se relee
    path = escribir("selftest", {"n": 0}, {"ok": True}, "PASS", [])
    try:
        with open(path) as f:
            doc = json.load(f)
        casos.append(("artefacto JSON se relee", doc["artefacto"] == "bench", path.split("/")[-1]))
    except Exception as e:
        casos.append(("artefacto JSON se relee", False, str(e)[:40]))

    print("  self-test de bench.py:")
    fallos = 0
    for nombre, ok, det in casos:
        print("    %-46s %s  %s" % (nombre, "OK" if ok else "FALLA", det))
        if not ok:
            fallos += 1
    print("  %d de %d casos pasan%s" % (len(casos) - fallos, len(casos),
                                         "" if fallos == 0 else "  <-- HAY FALLOS"))
    print("  todos pasan" if fallos == 0 else "  NO todos pasan")
    return 0 if fallos == 0 else 1


# ----------------------------------------------------------------- main

def main(argv):
    if "--selftest" in argv:
        return selftest({"n": 3})
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__[:2400])
        return 2
    if argv[0] == "list":
        for k, (fn, doc) in SUITES.items():
            print("  %-14s %s" % (k, doc))
        return 0
    if argv[0] != "run" or len(argv) < 2:
        print("uso: bench.py --selftest | list | run <suite> [--quick|--full] [--out F]")
        return 2
    suite = argv[1]
    if suite not in SUITES:
        print("suite desconocida: %s" % suite)
        return 2
    ctx = {"n": 7, "iters": (512, 2048, 8192)}
    for a in argv[2:]:
        if a == "--quick":
            ctx["n"] = 5
            ctx["iters"] = (512, 2048)
        elif a == "--full":
            ctx["n"] = 11
    # Puerta de instrumento. El banco no construye el binario, asi que el binario es
    # un artefacto externo y se consume como tal: si esta mas viejo que su fuente, la
    # corrida mide un programa que no es el que hay escrito y su artefacto no vale
    # para nada, por bien que haya salido. Se avisa y se detiene; no se mide y se
    # rotula despues.
    fb_ok, fb_det = frescura_binario()
    if not fb_ok:
        print("INSTRUMENTO OBSOLETO: %s" % fb_det[0].get("motivo", fb_det[0].get("estado")))
        print("  binario: %s" % VCP)
        print("  fuente:  %s" % os.path.join(HERE, "vulkan_compute_probe.c"))
        print("  el banco no construye nada. Reconstruir antes de medir.")
        return 3
    fn = SUITES[suite][0]
    t0 = time.time()
    del RELOJES[:]
    resultado = fn(ctx)
    # La puerta NO se aplica al resultado: se cuenta como un fallo mas de la CORRIDA.
    # Es lo que la hace compatible con regresion y rejilla, que devuelven una lista y no
    # un dict, y lo que la deja en la capa donde ocurre: el reloj cambio mientras la
    # suite corria, no porque la suite lo decidiera.
    puerta = cerrar_puerta_de_reloj()
    v, malos = veredicto(resultado)
    if puerta and puerta.get("estado") == "INVALIDA_POR_RELOJ":
        v = "INVALID"
        malos = malos + ["puerta_de_reloj=INVALIDA_POR_RELOJ"]
    if puerta:
        etiq = "RELOJ VARIABLE" if v == "INVALID" and puerta.get("estado") == "INVALIDA_POR_RELOJ" else "reloj estable"
        print("  %s en la corrida: %.2fx (%d..%d MHz), %d lecturas"
              % (etiq, puerta["razon"], puerta["min_hz"] // 10**6,
                 puerta["max_hz"] // 10**6, puerta["lecturas"]))
    path = escribir(suite, ctx, resultado, v, malos, puerta)
    print("  suite %s en %.1f s -> %s" % (suite, time.time() - t0, v))
    if malos:
        print("  fallos (%d): %s" % (len(malos), "; ".join(malos[:8])))
    print("  hardware: sclk=%s Hz mclk=%s Hz P=%s uW T=%s mC"
          % (fingerprint().get("sclk_hz"), fingerprint().get("mclk_hz"),
             fingerprint().get("power_uw"), fingerprint().get("temp_mc")))
    print("  artefacto: %s" % path)
    return 0 if v == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))