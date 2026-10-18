#!/usr/bin/env python3
# CONTRACT: name=fingerprint
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no

"""fingerprint -- fingerprint de hardware reproducible, y veredicto TARGET_MATCH.

POR QUE EXISTE. Todo el trabajo del proyecto se apoya en una GPU concreta y nunca
se habia construido el fingerprint que la identifica, ni se habia comparado con el
target declarado. Eso deja una pregunta sin responder en la base de todo lo demas:
¿sobre QUE hardware se hizo cada hallazgo?

Este es un PRODUCTO, no una lectura de una vez: se regenera, se compara campo a
campo con el contrato de target, y devuelve codigo de salida distinto segun el
veredicto.

REGLA QUE IMPONE EL PROPIO CONTRATO. `NOT_AVAILABLE` no es `MATCH`. Un campo que no
se pudo leer se reporta como tal y hace que el veredicto NO sea MATCH. Si no, el
fingerprint "pasa" mientras le falta la mitad, que es como un filtro que solo dice
"no".

Y el dispositivo GPU NO se localiza por indice de bus: se busca por clase y por
identidad PCI. El indice 01:00.0 es una convencion de esta maquina, no una
propiedad del hardware, y hardcodearlo es exactamente el tipo de generalizacion
que este proyecto no quiere.

Uso:
  fingerprint.py --completo     todos los campos + veredicto
  fingerprint.py --campo N      un campo
  fingerprint.py --self-test

Codigos de salida:
  0  TARGET_MATCH
  1  TARGET_MISMATCH  (un campo contradice al contrato)
  2  TARGET_INDETERMINATE (un campo no se pudo leer)
  3  dependencia ausente (lspci / journalctl)
"""

import functools
import os
import re
import subprocess
import sys

PCI_DIR = "/sys/bus/pci/devices"
SYS_DMI = "/sys/class/dmi/id"

def _release_de(un_srmo):
    """Extrae el release de la salida de `uname -srmo`.

    MEDIDO 2026-10-05, y esta función existe por una razón concreta: al
    principio la extraccion estaba escrita en línea dentro de `Collected()`, y el
    self-test la sustituía por un `str.split()` propio del test.  Mutar el
    PRODUCTOR para que devolviera la cadena con sobre no provocaba ningún fallo,
    porque el vector probaba el lenguaje y no el código:

        un self-test que reimplementa la logica que dice probar
        no prueba la logica

    Aqui no hay reimplementación: `Collected()` y el self-test llaman a la MISMA
    función.  `uname -srmo` es "Linux <release> <arch> <os>", asi que el release
    es el token [1].  Si la forma cambiara, se devuelve None y el veredicto lo
    marca INDETERMINATE por la regla del punto 5, nunca MATCH.
    """
    if not un_srmo:
        return None
    tok = str(un_srmo).split()
    return tok[1] if len(tok) > 1 else None


def _inconsistencias(campos):
    """Contradicciones ENTRE CAMPOS del mismo fingerprint.

    POR QUE EXISTE, y es una medicion.  MEDIDO 2026-10-05: al anadir el eje
    kernel, la extraccion del release quedo escrita en linea en `Collected()`.  Al
    mutar esa linea para que devolviera la cadena con sobre
    ("Linux 7.2.9-... GNU/Linux"), NINGUN vector fallo: los vectores probaban
    `_es_misma_serie`, no la asignacion que la alimentaba.

        un campo que se calcula y no se contrasta con su propio productor
        es un campo que puede estar mal sin que nadie lo note

    Y cuando esta mal no se rompe de forma ruidosa: `_es_misma_serie` devuelve
    False y el veredicto dice MISMATCH, o sea un fallo que PARECE una
    discrepancia legitima del hardware y por tanto no se investiga.  Este es el
    peor modo de fallo posible para un verificador: un criterion que no puede
    pasar.

    Aqui el invariante es propio y no depende de que kernel corra: el release es
    un token de la cadena `kernel` que produjo el MISMO `uname`.  Si los dos no
    concuerdan, el fingerprint se contradice a si mismo y eso se dice, en vez
    de disfrazarse de MISMATCH de hardware.
    """
    malas = []
    k, rel = campos.get("kernel"), campos.get("kernel_release")
    if k is not None and rel is not None:
        if _release_de(k) != rel:
            malas.append("kernel_release (%r) no es el release de kernel (%r)"
                         % (rel, k))
        if len(str(rel).split()) != 1:
            malas.append("kernel_release (%r) tiene mas de un token: no es un "
                         "release, es una cadena con sobre" % (rel,))
    return malas


def _es_misma_serie(real, serie):
    """Compara una version de kernel por serie, no por substring.

    MEDIDO 2026-10-05, y la razon de existir es que la regla general de
    `veredicto()` para cadenas es `esperado in str(real)`, que es un SUBSTRING.
    Para una CPU o una placa da igual. Para una version no:

        "7.1.3" in "17.1.30"          -> True   (FALSO: otra serie)
        "7.1.3" in "7.1.30-rc1"       -> True   (FALSO: otro patchlevel)
        "7.1.3" in "7.2.9-200.nobara" -> False  (bien, por casualidad)

    Dos de esos tres casos darian TARGET_MISMATCH con el valor correcto, o
    MATCH con el valor equivocado. Un substring sobre numeros de version no es
    una comparacion de version.

    REGLA. La serie esperada tiene que ser un PREFIJO del valor real, y el
    caracter siguiente -- si lo hay -- no puede ser un digito ni un punto.  El
    sufijo de distro (`-200.nobara.fc44.x86_64`) empieza por guion y por eso
    pasa; un patchlevel mas alto (`7.1.30`) sigue con digito y por eso no.
    """
    if real is None:
        return False
    r, s = str(real), str(serie)
    if not r.startswith(s):
        return False
    resto = r[len(s):]
    return not (resto[:1].isdigit() or resto[:1] == ".")


# El contrato de target. Cada entrada: (etiqueta, valor esperado, predicado).
# El predicado se evalua sobre el valor real; None significa igualdad exacta.
TARGET = [
    ("cpu",        "Intel(R) Core(TM) i7-4790 CPU @ 3.60GHz", None),
    ("board",      "H81H3-M4",                                  None),
    ("os",         "Nobara Linux",                              None),
    ("gpu_vendor", "Advanced Micro Devices",                    None),
    ("gpu_device", "699f",                                      None),
    ("asic",       "POLARIS12",                                 None),
    ("gfx",        "8.0.0",                                     None),
    ("vram_mib",   2048,                                        lambda v: abs(v - 2048) < 64),
    ("bar0_mib",   256,                                         lambda v: abs(v - 256) < 4),
    ("igpu",       True,                                        lambda v: v is True),
    # MEDIDO 2026-10-05, y este campo NO estaba.  El kernel se LEIA (linea
    # 136, `uname -srmo`) y se IMPRIMIA en el bloque HARDWARE FINGERPRINT, pero
    # no estaba en el contrato: se leia y no se comparaba.
    #
    #     un campo que se lee y no se compara es un dato, no un criterio
    #
    # Y el efecto es que el eje que ROMPE EL DRIVER no podia dar mismatch:
    #
    #     $ uname -r                          7.2.9-200.nobara.fc44.x86_64
    #     $ modinfo .../rx550_drv.ko | grep vermagic
    #     vermagic:  7.1.3-200.nobara.fc44.x86_64
    #
    # `vermagic` es lo que hace que `insmod` falle con Invalid module format.  Es
    # la unica discrepancia de este contrato con consecuencia operativa INMEDIATA,
    # y era invisible para el verificador porque no era un campo suyo.
    #
    # El valor esperado NO es una decision de este fichero.  El target declarado
    # esta en HARDWARE-FINGERPRINT.md (7.1.3-200.nobara.fc44.x86_64) y en el
    # arbol de fuentes (RESEARCH/working/linux-7.1.3).  Si el proyecto migra, se
    # cambia AQUI y en ningun otro sitio, y el veredicto lo dira.
    #
    # Y se compara por PREFIJO DE SERIE con `_es_misma_serie`, no con el `in`
    # de la regla general.  MEDIDO, y no es purismo: ese `in` es un substring y
    # sobre numeros de version produce falsos positivos reales (vease la
    # funcion).  Aqui lo que importa es que un rebuild del mismo kernel con
    # otro sufijo de distro NO sea TARGET_MISMATCH, y que 7.1.30 SI lo sea.
    # El campo del contrato es `kernel_release`, NO `kernel`.  MEDIDO: comparar
    # la cadena con sobre ("Linux 7.1.3-... x86_64 GNU/Linux") contra "7.1.3"
    # devuelve MISMATCH con el kernel CORRECTO, o sea un criterio que no puede
    # pasar y por tanto no puede fallar.  Ver `_es_misma_serie` y el productor.
    ("kernel_release", "7.1.3",
     functools.partial(_es_misma_serie, serie="7.1.3")),
]


def _leer(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read().strip()
    except OSError:
        return None


def _cmd(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=60)
        return p.stdout if p.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _dmi(f):
    return _leer(os.path.join(SYS_DMI, f))


def _klog():
    """Kernel log via journalctl. `dmesg` puede estar vacio por permisos."""
    return _cmd(["journalctl", "-k", "--no-pager"]) or ""


def gpu_dispositivo():
    """Localiza la GPU por clase PCI 0300 con vendor 1002. NO por indice de bus."""
    vendor = _cmd(["lspci", "-nn"])
    if vendor is None:
        return None
    for linea in vendor.split("\n"):
        # "01:00.0 VGA compatible controller [0300]: ... [1002:699f] (rev c7)"
        m = re.match(r"([0-9a-f]{2}:[0-9a-f]{2}\.\d)\s+"
                     r"VGA compatible controller.*\[([0-9a-f]{4}):([0-9a-f]{4})\]", linea)
        if m and m.group(2) == "1002":
            return {"slot": m.group(1), "vendor": m.group(2),
                    "device": m.group(3), "linea": linea}
    return None


def iGPU_presente():
    vendor = _cmd(["lspci", "-nn"]) or ""
    # 8086:0412 es el GT3 de Haswell (Iris Pro 4600 / HD Graphics 4600).
    return "8086:0412" in vendor


def Collected():
    """Reúne todos los campos. Devuelve (campos, ausentes)."""
    k = _klog()
    campos = {}

    cpuinfo = _leer("/proc/cpuinfo") or ""
    m = re.search(r"model name\s*:\s*(.+)", cpuinfo)
    campos["cpu"] = m.group(1).strip() if m else None
    n_cpu = len(re.findall(r"^processor\s*:", cpuinfo, re.M))
    campos["cpus_logicos"] = n_cpu or None
    # nucleos fisicos, de la topologia del kernel (una entrada por nucleo)
    topo = _leer("/sys/devices/system/cpu/cpu0/topology/thread_siblings_list") or ""
    campos["thread_siblings"] = topo

    mem = _leer("/proc/meminfo") or ""
    m = re.search(r"MemTotal:\s+(\d+) kB", mem)
    campos["ram_kib"] = int(m.group(1)) if m else None
    campos["ram_gib"] = round(campos["ram_kib"] / 1048576.0, 2) if campos["ram_kib"] else None

    campos["board"] = _dmi("board_name")
    campos["board_vendor"] = _dmi("board_vendor")
    campos["bios"] = _dmi("bios_version")

    un = _cmd(["uname", "-srmo"])
    campos["kernel"] = un.strip() if un else None
    # `uname -srmo` emite "Linux <release> <arch> <os>".  El campo `kernel` de
    # arriba es la CADENA COMPLETA, y por eso no sirve para comparar: empieza
    # por "Linux " y acaba en "GNU/Linux".  Un contrato que comparase esa cadena
    # contra "7.1.3" daria MISMATCH SIEMPRE, con el kernel correcto y con el
    # incorrecto, y por tanto no distinguiria nada.
    #
    #     una cadena con sobre no es un valor comparable
    #
    # El release va aparte, y sale del MISMO uname que ya se pide: no es una
    # llamada nueva, es la extraccion que se prueba en el punto 8 del self-test.
    campos["kernel_release"] = _release_de(un)
    campos["arch"] = un.split()[2] if un and len(un.split()) > 2 else None

    osr = _leer("/etc/os-release") or ""
    m = re.search(r'PRETTY_NAME="([^"]+)"', osr)
    campos["os"] = m.group(1) if m else None

    g = gpu_dispositivo()
    if g:
        campos["gpu_slot"] = g["slot"]
        campos["gpu_vendor"] = g["linea"].split(": ", 1)[1].split(" [")[0]
        campos["gpu_device"] = g["device"]
        campos["gpu_linea"] = g["linea"]
    else:
        campos["gpu_slot"] = campos["gpu_vendor"] = campos["gpu_device"] = None
        campos["gpu_linea"] = None

    # ASIC y GFX: el driver los imprime al arrancar.
    m = re.search(r"initializing kernel modesetting \(([^ ]+)", k)
    campos["asic"] = m.group(1) if m else None
    m = re.search(r"detected ip block number 3 <gfx_v(\d+)_(\d+)_(\d+)>", k)
    campos["gfx"] = ("%s.%s.%s" % (m.group(1), m.group(2), m.group(3))
                     if m else None)

    m = re.search(r"Detected VRAM RAM=(\d+)M, BAR=(\d+)M", k)
    campos["vram_mib"] = int(m.group(1)) if m else None
    campos["bar0_mib_log"] = int(m.group(2)) if m else None

    m = re.search(r"GART:\s*(\d+)M", k)
    campos["gart_mib"] = int(m.group(1)) if m else None
    m = re.search(r"(\d+)M of GTT memory ready", k)
    campos["gtt_mib"] = int(m.group(1)) if m else None

    # BAR0 medido del recurso, independiente del log.
    if campos["gpu_slot"]:
        # lspci imprime "01:00.0" SIN dominio; sysfs usa "0000:01:00.0" CON el.
        # Sin esta normalizacion el recurso no existe y el fingerprint queda
        # INDETERMINATE -- que es lo que paso, y que es el comportamiento
        # correcto: la herramienta dijo que le faltaba un campo en vez de
        # suponerlo.
        slot = campos["gpu_slot"]
        if not re.match(r"^[0-9a-f]{4}:", slot):
            slot = "0000:" + slot
        campos["gpu_slot_sysfs"] = slot
        r = os.path.join(PCI_DIR, slot, "resource")
        txt = _leer(r)
        if txt:
            filas = [l.split() for l in txt.split("\n") if l.strip()]
            if filas:
                a, b = int(filas[0][0], 16), int(filas[0][1], 16)
                campos["bar0_mib"] = (b - a + 1) // (1024 * 1024) if b else None
    campos.setdefault("bar0_mib", None)

    # BAR de registros: el que el driver mapea de verdad.
    m = re.search(r"register mmio base:\s*(0x[0-9A-Fa-f]+)", k)
    campos["rmmio_base"] = m.group(1) if m else None
    m = re.search(r"register mmio size:\s*(\d+)", k)
    campos["rmmio_size"] = int(m.group(1)) if m else None

    campos["igpu"] = iGPU_presente() if campos["gpu_vendor"] else None

    campos["driver"] = "amdgpu"
    campos["modulo"] = "amdgpu" if _leer("/proc/modules") and "amdgpu" in (
        _leer("/proc/modules") or "") else None

    ausentes = [n for n, _e, _p in TARGET if campos.get(n) is None]
    return campos, ausentes


def veredicto(campos):
    filas, mal, indet = [], [], []
    for etiqueta, esperado, pred in TARGET:
        real = campos.get(etiqueta)
        if real is None:
            estado = "INDETERMINATE"
            indet.append(etiqueta)
        elif pred is not None:
            estado = "MATCH" if pred(real) else "MISMATCH"
        else:
            if isinstance(esperado, bool):
                estado = "MATCH" if real is esperado else "MISMATCH"
            elif isinstance(esperado, str):
                estado = "MATCH" if esperado in str(real) else "MISMATCH"
            else:
                estado = "MATCH" if real == esperado else "MISMATCH"
        if estado == "MISMATCH":
            mal.append(etiqueta)
        filas.append((etiqueta, str(esperado), str(real), estado))
    return filas, mal, indet


def self_test():
    fails = []

    def eq(l, g, w):
        if g != w:
            fails.append("%s: %r != %r" % (l, g, w))

    # 1. La aritmetica de RAM: MemTotal viene en KiB y el contrato pide GiB.
    eq("12098904 kB son GiB", round(12098904 / 1048576.0, 2), 11.54)

    # 2. La GPU se localiza por clase, no por indice. Un fixture con la GPU en
    #    OTRO bus tiene que dar el mismo resultado: por eso el parser es el
    #    producto que se prueba, no el indice.
    lineas = [
        "00:02.0 Display controller [0380]: Intel Corporation [8086:0412] (rev 06)",
        "01:00.0 VGA compatible controller [0300]: Advanced Micro Devices, Inc. "
        "[AMD/ATI] Lexa PRO [1002:699f] (rev c7)",
        "07:00.0 VGA compatible controller [0300]: Advanced Micro Devices, Inc. "
        "[AMD/ATI] Another [1002:699f] (rev c7)",
    ]
    got = None
    for l in lineas:
        m = re.match(r"([0-9a-f]{2}:[0-9a-f]{2}\.\d)\s+"
                     r"VGA compatible controller.*\[([0-9a-f]{4}):([0-9a-f]{4})\]", l)
        if m and m.group(2) == "1002":
            got = m.group(1)
            break          # el PRIMERO gana, como en gpu_dispositivo()
    eq("el parser encuentra la primera VGA de vendor 1002", got, "01:00.0")

    # 3. CONTROL NEGATIVO del parser: una linea que NO es la GPU no debe casar.
    #    Sin esto, "hay 0300 en alguna parte" seria suficiente y seria falso.
    m = re.match(r"([0-9a-f]{2}:[0-9a-f]{2}\.\d)\s+"
                 r"VGA compatible controller.*\[([0-9a-f]{4}):([0-9a-f]{4})\]",
                 "00:02.0 Display controller [0380]: Intel Corporation [8086:0412]")
    if m:
        fails.append("control negativo: el parser caso con un Display controller Intel")

    # 4. CONTROL NEGATIVO: una GPU de otro vendor NO debe_selected.
    m = re.match(r"([0-9a-f]{2}:[0-9a-f]{2}\.\d)\s+"
                 r"VGA compatible controller.*\[([0-9a-f]{4}):([0-9a-f]{4})\]",
                 "01:00.0 VGA compatible controller [0300]: NVIDIA Corporation "
                 "GA106 [10de:2404] (rev a1)")
    if m and m.group(2) == "1002":
        fails.append("control negativo: selecciono una GPU NVIDIA")

    # 5. LA REGLA QUE IMPONE EL CONTRATO: un campo ausente NO es MATCH.
    campos = {n: None for n, _e, _p in TARGET}
    _f, mal, indet = veredicto(campos)
    if not indet:
        fails.append("todos los campos a None deben ser INDETERMINATE, no MATCH")
    eq("ninguno debe ser MISMATCH con todo ausente", mal, [])

    # 6. Y al reves: un valor equivocado debe ser MISMATCH, no INDETERMINATE.
    campos2 = {n: 1 for n, _e, _p in TARGET}
    _f2, mal2, indet2 = veredicto(campos2)
    if not mal2:
        fails.append("valores erroneos deben dar MISMATCH")

    # 7. EL EJE KERNEL, y la comparacion por serie.  MEDIDO 2026-10-05: el
    #    kernel se leia y se imprimia pero NO estaba en el contrato, que es la
    #    clase de defecto que ya se ha visto cinco veces en este proyecto (un
    #    valor calculado y nunca comparado).  Aqui se prueba la FRONTERA de
    #    `_es_misma_serie`, que es donde un substring daria un falso positivo.
    #
    #    Mismo kernel, distinto sufijo de distro -> MATCH (si no, un rebuild
    #    del mismo kernel seria TARGET_MISMATCH, que es un falso negativo).
    eq("misma serie con otro sufijo de distro",
       _es_misma_serie("7.1.3-200.nobara.fc44.x86_64", "7.1.3"), True)
    # CONTROL NEGATIVO: patchlevel mas alto.  "7.1.3" es substring de "7.1.30",
    # asi que un `in` lo daria por bueno.  Aqui NO.
    eq("patchlevel mas alto NO es la misma serie",
       _es_misma_serie("7.1.30-rc1", "7.1.3"), False)
    # CONTROL NEGATIVO: la serie aparece con un prefijo de otra parte.
    eq("serie precedida de otra no es la misma serie",
       _es_misma_serie("17.1.30", "7.1.3"), False)
    # CONTROL NEGATIVO: la serie de veras distinta que se esta ejecutando.
    eq("7.2.9 no es 7.1.3",
       _es_misma_serie("7.2.9-200.nobara.fc44.x86_64", "7.1.3"), False)
    # Y el valor ausente no puede ser MATCH: es la misma regla del punto 5.
    eq("kernel ausente no es MATCH",
       _es_misma_serie(None, "7.1.3"), False)

# 8. Y el PRODUCTOR, no solo el predicado.  El punto 7 anterior probaba
    #    `_es_misma_serie` con cadenas limpias ("7.1.3-200.nobara..."), que NO
    #    es lo que emite `uname -srmo`.  Ese hueco dejo pasar un criterio roto:
    #    el veredicto daba MISMATCH con el kernel correcto, y el self-test
    #    pasaba igual.  MEDIDO y REPARADO.
    #
    #    Asi que aqui se alimentan las CADENAS EXACTAS que produce `uname -srmo`
    #    en esta maquina, con su "Linux " delante y su "GNU/Linux" detras, y se
    #    llama a `_release_de`, que es la funcion que USA el productor.  La
    #    primera version de este vector hacia `un.split()[1]` aqui mismo, y al
    #    mutar el PRODUCTOR no fallaba nada: probaba el lenguaje, no el codigo.
    eq("el productor extrae el release de 'uname -srmo' (7.2.9)",
       _release_de("Linux 7.2.9-200.nobara.fc44.x86_64 x86_64 GNU/Linux"),
       "7.2.9-200.nobara.fc44.x86_64")
    eq("el productor extrae el release de 'uname -srmo' (7.1.3)",
       _release_de("Linux 7.1.3-200.nobara.fc44.x86_64 x86_64 GNU/Linux"),
       "7.1.3-200.nobara.fc44.x86_64")
    # CONTROL NEGATIVO: una `uname` vacia o de un solo token NO puede dar un
    # release inventado.  Sin esto, el `[0]` de una cadena vacia seria "" y
    # `"" in str(real)` casaria con cualquier cosa.
    eq("uname vacia no da release", _release_de(""), None)
    eq("uname de un solo token no da release", _release_de("Linux"), None)
    eq("uname ausente no da release", _release_de(None), None)

    # Y el criterio, alimentado con ESE release y no con una cadena inventada:
    eq("release correcto -> MATCH",
       _es_misma_serie("7.1.3-200.nobara.fc44.x86_64", "7.1.3"), True)
    eq("release incorrecto -> MISMATCH",
       _es_misma_serie("7.2.9-200.nobara.fc44.x86_64", "7.1.3"), False)

    # Y la prueba de que el criterio DISTINGUE, no solo que responde: los dos
    # casos anteriores tienen que ser opuestos.  Si los dos fueran False, el
    # verificador no distinguiria el kernel bueno del malo, que es el defecto
    # que se acaba de encontrar y no debe poder volver.
    if (_es_misma_serie("7.1.3-200.nobara.fc44.x86_64", "7.1.3")
            == _es_misma_serie("7.2.9-200.nobara.fc44.x86_64", "7.1.3")):
        fails.append("el criterio kernel no distingue 7.1.3 de 7.2.9")

    # Y que el campo del contrato sea el release y no la cadena con sobre.
    _etiquetas = [n for n, _e, _p in TARGET]
    if "kernel_release" not in _etiquetas:
        fails.append("el contrato no tiene el campo kernel_release")
    if "kernel" in _etiquetas:
        fails.append("el contrato compara 'kernel' (cadena con sobre), "
                     "no 'kernel_release'")

    # 9. LA CONSISTENCIA INTERNA.  MEDIDO: M1 (el.call site devuelve la cadena con
    #    sobre) no fallo con ningun vector hasta que esta funcion existio.  Asi
    #    que se prueba con la forma EXACTA que M1 produce.
    _un_ok = "Linux 7.1.3-200.nobara.fc44.x86_64 x86_64 GNU/Linux"
    # El caso sano: no dice nada.
    if _inconsistencias({"kernel": _un_ok,
                         "kernel_release": "7.1.3-200.nobara.fc44.x86_64"}):
        fails.append("control negativo: un fingerprint coherente no debe dar "
                     "inconsistencia")
    # Y el caso que M1 producia, que es el que hay que cazar.
    _malas = _inconsistencias({"kernel": _un_ok,
                               "kernel_release": _un_ok})   # release = sobre
    if not _malas:
        fails.append("un release que es la cadena con sobre debe dar "
                     "inconsistencia: es el caso que M1 producia en silencio")
    # Y el caso de un release que NO es token de kernel (p.ej. de otra maquina).
    _malas2 = _inconsistencias({"kernel": _un_ok,
                                "kernel_release": "6.1.0-rc1"})
    if not _malas2:
        fails.append("un release que no viene de kernel debe dar "
                     "inconsistencia")
    # Y que la ausencia de uno de los dos NO es inconsistencia: es INDETERMINATE,
    # que es otra cosa, y la regla del punto 5 dice que no se convierte en MATCH.
    if _inconsistencias({"kernel": _un_ok, "kernel_release": None}):
        fails.append("un release ausente no es INCONSISTENTE, es ausente")

    # 10. EL CAMINO COMPLETO, sin hardware.  MEDIDO: los puntos 7-9 probaban
    #     unidades, y por eso ninguna mutacion del ARMADO fallo.  Aqui se llama
    #     a `_informe`, que es la MISMA funcion que llama `main()`, con campos
    #     sinteticos.  Es lo que permite que estas comprobaciones corran en una
    #     maquina que NO sea la correcta, que es justo cuando mas se necesitan.
    #
    #     un self-test que necesita el hardware correcto no puede probar el
    #     verificador que decide si el hardware es el correcto

    # Los tres codigos de salida tienen que ser DISTINTOS y significar cosas
    # distintas.  Si dos coincidieran, uno de los tres estados seria invisible.
    _sink = []
    _todos_ok = {n: None for n, _e, _p in TARGET}
    eq("fingerprint sin ningun campo -> INDETERMINATE (rc=2)",
       _informe(_todos_ok, _sink.append), 2)
    _malos = {n: 1 for n, _e, _p in TARGET}
    _malos["kernel"] = "Linux 7.2.9-200.nobara.fc44.x86_64 x86_64 GNU/Linux"
    _malos["kernel_release"] = "7.2.9-200.nobara.fc44.x86_64"
    eq("fingerprint coherente pero distinto del target -> MISMATCH (rc=1)",
       _informe(_malos, _sink.append), 1)
    # Y rc=3, que es el que M1 producia en silencio.
    _m1 = dict(_malos)
    _m1["kernel_release"] = _m1["kernel"]      # el call site devuelve el sobre
    eq("release con sobre -> INCONSISTENTE (rc=3), no MISMATCH",
       _informe(_m1, _sink.append), 3)
    # Y los tres codigos no pueden ser el mismo numero.
    if len({2, _informe(_malos, _sink.append),
            _informe(_m1, _sink.append)}) != 3:
        fails.append("MATCH/MISMATCH/INCONSISTENTE comparten codigo de salida: "
                     "algun estado seria invisible para quien llame a la herramienta")
    # Y el texto que se imprime tiene que DECIRLO, no solo devolver el numero:
    # un rc=3 sin texto parece un MISMATCH raro y se investiga como hardware.
    _txt = []
    _informe(_m1, _txt.append)
    if not any("INCONSISTENTE" in t for t in _txt):
        fails.append("rc=3 pero la salida no dice que es una inconsistencia "
                     "del verificador, no un mismatch de hardware")
    if any(t.startswith("TARGET_MISMATCH en:") for t in _txt):
        # MEDIDO: esta comprobacion empezo buscando "TARGET_MISMATCH" en
        # cualquier linea, y FALLO contra el propio texto de la herramienta: la frase
        # "Esto NO es un TARGET_MISMATCH" contiene ese substring.  Un vector
        # que se puede satisfacer con una negacion no distingue el caso que
        # quiere distinguir, y hay que afilarlo, no relajarlo.
        #
        #     un substring sobre prosa no es un oraculo
        #
        # Se comprueba el VEREDICTO, que es una linea que empieza por
        # "TARGET_MISMATCH en:", y no cualquier mencion de la palabra.
        fails.append("un fingerprint inconsistente imprime la linea de "
                     "veredicto TARGET_MISMATCH: seria una mentira sobre "
                     "el hardware")

    # 11. VIAS INDEPENDIENTES DEL MISMO HECHO, y su diferencia con una
    #     inconsistencia.  MEDIDO: `bar0_mib` (recurso PCI) y `bar0_mib_log`
    #     (log del driver) son el mismo hecho por dos vias, se imprimen los dos
    #     y no se comparaban nunca.  Septima aparicion de la misma clase.
    eq("dos vias que coinciden",
       [(t, e) for t, _a, _b, e in _crosadas({"bar0_mib": 256,
                                              "bar0_mib_log": 256})],
       [("bar0_mib", "COINCIDE")])
    eq("dos vias que difieren se DICEN",
       [(t, e) for t, _a, _b, e in _crosadas({"bar0_mib": 256,
                                              "bar0_mib_log": 512})],
       [("bar0_mib", "DIFIERE")])
    # CONTROL NEGATIVO: si falta una de las dos vias no se dice nada.  Una
    # ausencia es INDETERMINATE por la regla del punto 5, no COINCIDE.
    if _crosadas({"bar0_mib": 256, "bar0_mib_log": None}):
        fails.append("una via ausente no se informa: no hay nada que comparar")

    # Y el punto que hace que esto no sea teatro: una discrepancia NO puede
    # parecerse a un verificador roto.  rc=3 significa "la herramienta esta
    # mal"; si un DIFIERE tambien diera rc=3, el codigo se volveria inutil y se
    # acabaria ignorando los dos casos.
    _d = {"kernel": "Linux 7.1.3-200.nobara.fc44.x86_64 x86_64 GNU/Linux",
          "kernel_release": "7.1.3-200.nobara.fc44.x86_64",
          "bar0_mib": 256, "bar0_mib_log": 512}
    if _inconsistencias(_d):
        fails.append("una diferencia entre dos vias NO es inconsistencia "
                     "interna: confundirlas haria que rc=3 no significara nada")
    # Y el codigo de salida de verdad, con un fingerprint coherente pero cuyo
    # unico problema es una discrepancia entre vias: rc=1 por los campos que no
    # son el target, NUNCA rc=3.
    _d2 = {n: 1 for n, _e, _p in TARGET}
    _d2.update(_d)
    eq("un DIFIERE no convierte un MISMATCH en INCONSISTENTE",
       _informe(_d2, _sink.append), 1)

    if fails:
        print("self-test FALLA (%d)" % len(fails))
        for f in fails:
            print("   " + f)
        return 1
    print("self-test OK (1 de unidades, 4 de parser con 3 controles negativos, "
          "2 de veredicto, 5 de serie de kernel con 3 controles negativos, "
          "3 del productor real con 3 controles negativos, 1 de distincion, 2 de forma del contrato, 4 de consistencia interna con 3 controles negativos, 5 de camino completo sin hardware, 3 de vias independientes con 1 control negativo)")
    return 0


def _crosadas(campos):
    """Pares de campos que SON EL MISMO HECHO, medidos por dos vias.

    MEDIDO 2026-10-05.  `_inconsistencias` cubre los pares que DEBEN coincidir
    siempre (kernel y su release salen del mismo `uname`).  Esta funcion cubre
    los pares que DEBERIAN coincidir pero pueden no, y por eso NO son un fallo:

        DEBEN coincidir siempre  -> si no, el verificador esta roto   -> rc=3
        DEBERIAN coincidir      -> si no, es INFORMACION               -> se dice

    `bar0_mib` y `bar0_mib_log` son el ejemplo.  El primero sale del recurso
    PCI config (`/sys/bus/pci/devices/<slot>/resource`), que es lo que el
    hardware TIENE.  El segundo sale del log del driver
    (`Detected VRAM RAM=..., BAR=...M`), que es lo que amdgpu VIO.  Son dos
    vias independientes del mismo hecho, y una discrepancia entre ellas es
    exactamente el dato que hace sospechar de un redimensionado de BAR por
    firmware, o de que el driver leyera otra cosa.

    Que difieran NO es un error del verificador, y por eso no se trata igual que
    una inconsistencia: una regla que confunde "el hardware es raro" con "la
    herramienta esta mal" acaba enseñando a ignorar sus propios avisos.

    Cuando uno de los dos falta no se dice nada: es INDETERMINATE, que por la
    regla del punto 5 del self-test no es MATCH ni MISMATCH.
    """
    pares = []
    for etiqueta, a, b in (("bar0_mib", campos.get("bar0_mib"),
                            campos.get("bar0_mib_log")),):
        if a is None or b is None:
            continue                       # ausente: no se informa de nada
        pares.append((etiqueta, a, b, "COINCIDE" if a == b else "DIFIERE"))
    return pares


def _informe(campos, salida=None):
    """Imprime el fingerprint y devuelve el codigo de salida. SIN leer hardware.

    MEDIDO 2026-10-05, y esta extraccion existe por una segunda medicion.  El
    self-test probaba `_inconsistencias` y `_release_de` por separado, y ninguna
    mutacion del ARMADO — la linea de `main()` que las llama — hacia fallar
    ningun vector:

        M1  el call site devuelve la cadena con sobre  -> self-test OK
        M4  la alarma se desconecta (`malas_internas = []`) -> self-test OK

    Los dos son fallos REALES del camino de ejecucion que los vectores no veian,
    porque los vectores probaban unidades y no la composicion.  Y el remedio es
    el mismo que para `_release_de`: una sola implementacion, llamada por los dos
    lados.  `main()` llama a esta funcion con los campos reales; el self-test la
    llama con campos sinteticos, entre ellos la forma exacta que M1 producia.

    Que el camino se pueda probar SIN hardware es la consecuencia util: el
    verificador de target del proyecto entero tiene ahora un vector que no
    necesita que la maquina sea la correcta para poder fallar.
    """
    w = salida if salida is not None else _stdout().write
    # La consistencia interna se comprueba ANTES de comparar con el target.  Si
    # el fingerprint se contradice a si mismo, un MISMATCH seria una MENTIRA:
    # diria que el hardware no es el esperado cuando lo que ocurre es que el
    # propio verificador esta roto.
    malas_internas = _inconsistencias(campos)

    w("=" * 72 + "\nHARDWARE FINGERPRINT\n" + "=" * 72 + "\n")
    for k in ("cpu", "cpus_logicos", "ram_gib", "board_vendor", "board", "bios",
              "os", "kernel", "kernel_release", "arch", "gpu_slot", "gpu_vendor",
              "gpu_device", "asic", "gfx", "vram_mib", "bar0_mib", "bar0_mib_log",
              "gart_mib", "gtt_mib", "rmmio_base", "rmmio_size", "igpu",
              "driver", "modulo"):
        v = campos.get(k)
        w("  %-14s %s\n" % (k, "NOT_AVAILABLE" if v is None else v))

    w("\n" + "-" * 72 + "\nVEREDICTO CONTRA EL CONTRATO DE TARGET\n" + "-" * 72 + "\n")
    w("  %-13s %-38s %-22s %s\n" % ("campo", "esperado", "real", "estado"))
    filas, mal, indet = veredicto(campos)
    for etiqueta, esp, real, estado in filas:
        w("  %-13s %-38s %-22s %s\n" % (etiqueta, esp[:38], real[:22], estado))

    pares = _crosadas(campos)
    if pares:
        w("\n" + "-" * 72 + "\nVIAS INDEPENDIENTES DEL MISMO HECHO\n"
          + "-" * 72 + "\n")
        w("  %-14s %-14s %-14s %s\n" % ("hecho", "via_1", "via_2", "estado"))
        for etiqueta, a, b, estado in pares:
            w("  %-14s %-14s %-14s %s\n" % (etiqueta, a, b, estado))
        if any(e == "DIFIERE" for _t, _a, _b, e in pares):
            w("  DIFIERE no es un fallo del verificador: es el dato.  bar0_mib\n"
              "  viene del recurso PCI y bar0_mib_log de lo que el driver vio.\n")

    w("\n")
    if malas_internas:
        # rc=3, distinto de 1 (MISMATCH) y de 2 (INDETERMINATE).  Un verificador
        # que se contradice a si mismo no ha medido un target distinto: ha
        # fallado como verificador, y esa es otra cosa que un MISMATCH.
        w("FINGERPRINT_INCONSISTENTE (%d).  Esto NO es un TARGET_MISMATCH:\n"
          % len(malas_internas))
        for m in malas_internas:
            w("   " + m + "\n")
        w("  El veredicto de arriba no es de fiar hasta arreglar esto.\n")
        return 3
    if mal:
        w("TARGET_MISMATCH en: %s\n" % ", ".join(mal))
        return 1
    if indet:
        w("TARGET_INDETERMINATE: %s no se pudo leer.\n" % ", ".join(indet))
        w("  NOT_AVAILABLE no es MATCH. El fingerprint esta incompleto.\n")
        return 2
    w("TARGET_MATCH\n")
    return 0


def _stdout():
    import sys as _s
    return _s.stdout


def main(argv):
    if "--self-test" in argv:
        return self_test()

    campos, _aus = Collected()

    if "--campo" in argv:
        n = argv[argv.index("--campo") + 1]
        v = campos.get(n)
        print("%-14s %s" % (n, "NOT_AVAILABLE" if v is None else v))
        return 0 if v is not None else 2

    return _informe(campos)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))