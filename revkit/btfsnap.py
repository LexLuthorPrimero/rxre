#!/usr/bin/env python3
"""
btfsnap.py -- guarda los layouts de struct que salen de la BTF del modulo.

POR QUE EXISTE. `/sys/kernel/btf/<modulo>` es NIVEL 2 (leer un fichero de
`/sys`, sin instrumentacion) y es PERECEDERO: es por arranque, y en esta maquina
incluso se reescribio DENTRO del mismo arranque (04:54 con el boot a las 00:10).
Es decir: cuando el layout haga falta y no este guardado, ya no habra forma de
sacarlo. `pahole` sobre el `.ko` no sirve de alternativa -- la seccion `.BTF`
del `.ko` esta partida y pahole falla con "Malformed BTF string section".

Lo que se guarda NO es la BTF (3.88 MB, no versionable) sino los LAYOUTS ya
resueltos, en texto, con su procedencia. Eso es lo que se necesita para un
driver propio: offsets y tamanos, no el indice de tipos.

LIMITE IMPORTANTE, y es el que mas Easily se malinterpreta. Que un struct NO
este en la BTF del modulo NO significa que no exista en el kernel. BTF solo cubre
los tipos que el modulo exporta a kallsyms. Medido aqui: `amdgpu_bo` si esta
(712 bytes) y `drm_bo` NO, pero `drm_gem_object` (368) si: eso es un RENOMBRADO
en este kernel, no una ausencia. Por eso una struct ausente se reporta como
`NO_EN_BTF`, que no es `PROVEN_ABSENT`.

Uso:

    btfsnap.py                    # escribe el snapshot con la lista por defecto
    btfsnap.py --comparar         # compara con lo guardado y avisa si hay deriva
    btfsnap.py --listar           # solo enumera los structs pedidos y su estado
    btfsnap.py --structs a,b,c    # lista propia
    btfsnap.py --btf /ruta/x.btf --salida /ruta/salida.txt

Codigos de salida:

    0  snapshot escrito, o sin deriva
    1  deriva detectada con --comparar (el hash de la BTF o el texto cambio)
    2  la BTF no existe
    3  pahole no esta instalado
    4  ninguna de las structs pedidas se pudo resolver
    5  error de uso o de escritura
"""

import argparse
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import time

VERSION = "1.0"

_AQUI = os.path.dirname(os.path.abspath(__file__))
BTF_POR_DEFECTO = "/sys/kernel/btf/amdgpu"

# Los structs que necesitan las fronteras abiertas de esta placa. No es "los
# que existen": es una eleccion, y por eso es una lista y no un glob.
#
#   amdgpu_bo        EV-33: bo->flags en 0x248; F2b: la mascara la puso userspace
#   amdgpu_vm        F2b, F12: PDE/PTE, ptba, el invalidate
#   amdgpu_gfx       F14: la configuracion de GFX que se programa por MMIO
#   amdgpu_ring      rings y scheduling
#   amdgpu_sched     scheduling
#   amdgpu_ib        EV-29: los 8 IB quePm4dec cuenta
#   drm_gem_object   el tipo donde vive la BO en este kernel (NO drm_bo: renombrado)
#   ttm_buffer_object  la base de ttm dentro de amdgpu_bo
#   amdgpu_mqd       el objeto de cola
#   amdgpu_fence     fences
#   amdgpu_device    la raiz; es enorme (392696 bytes, 491 lineas) y por eso va
#                    el ultimo y con aviso
STRUCTS_POR_DEFECTO = [
    "amdgpu_bo", "amdgpu_vm", "amdgpu_gfx", "amdgpu_ring", "amdgpu_sched",
    "amdgpu_ib", "drm_gem_object", "ttm_buffer_object", "amdgpu_mqd",
    "amdgpu_fence", "drm_device", "amdgpu_device",
]

# Estructuras grandes: su volcado se guarda igual, pero se avisa, porque ocupa
# y porque a nadie lo va a leer entero. Es un aviso, no un fallo.
TAMANO_AVISO = 64 * 1024


def _pahole():
    p = shutil.which("pahole")
    if not p:
        return None
    try:
        v = subprocess.run([p, "--version"], capture_output=True,
                           text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return (p, v.splitlines()[0] if v else "version desconocida")


def _sha256(ruta, bloques=1 << 20):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        while True:
            b = f.read(bloques)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _tamano_de(pahole, btf, nombre):
    """(bytes, None) si existe, (None, motivo) si no."""
    try:
        r = subprocess.run([pahole, "-s", "-C", nombre, btf],
                           capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        return None, "no se pudo ejecutar pahole: %s" % e
    for linea in r.stdout.splitlines():
        partes = linea.split()
        if partes and partes[0] == nombre and len(partes) >= 2:
            try:
                return int(partes[1]), None
            except ValueError:
                pass
    # pahole avisa por stderr y sale distinto cuando no existe. Se distingue
    # "no existe" de "existe pero no tiene layout", porque son cosas distintas
    # y una de ellas es un fallo de la herramienta.
    if "Unable to open" in r.stderr or not r.stdout.strip():
        return None, "no esta en la BTF"
    return None, "esta en la BTF pero pahole no devuelve layout: %s" % (
        r.stderr.strip().splitlines()[0] if r.stderr.strip() else "sin motivo")


def _campos_de(pahole, btf, nombre):
    try:
        r = subprocess.run([pahole, "-C", nombre, btf],
                           capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.SubprocessError) as e:
        return None, "no se pudo ejecutar pahole: %s" % e
    if not r.stdout.strip():
        return None, "pahole no devuelve cuerpo para %s" % nombre
    return r.stdout, None


def _selftest():
    """
    Comprueba los caminos de fallo con entradas que se pueden fabricar, y los
    compara con lo que este propio modulo afirma.

    Que un control pueda fallar no basta: hay que PROBAR que falla. Cada caso
    de aqui espera un codigo concreto, y si el codigo no es el esperado se
    cuenta como fallo aunque la ejecucion "parezca" correcta.
    """
    fallos = []
    print("btfsnap %s -- selftest" % VERSION)

    # Los sub-casos speaks por su cuenta, y en un selftest eso tapa el
    # veredicto. SeCaptura su salida: lo que interesa es el rc, no el ruido.
    def _silencioso(argv):
        buf_out, buf_err = io.StringIO(), io.StringIO()
        so, se = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = buf_out, buf_err
        try:
            return main(argv), buf_out.getvalue() + buf_err.getvalue()
        finally:
            sys.stdout, sys.stderr = so, se

    def _caso(desc, argv, esperado):
        rc, _ruido = _silencioso(argv)
        print("  %-46s rc=%d (esperado %d)%s"
              % (desc, rc, esperado, "" if rc == esperado else "   <-- NO"))
        if rc != esperado:
            fallos.append("%s deberia dar %d y dio %d" % (desc, esperado, rc))
        return rc

    # rc=2: una BTF que no existe. Se usa una ruta absurda a proposito.
    _caso("BTF inexistente", ["--btf", "/no/existe/de/verdad.btf", "--listar"], 2)

    # rc=4: struct que no puede existir. Con una BTF real, para no depender de
    # que falte pahole.
    hay_btf = os.path.exists(BTF_POR_DEFECTO)
    if hay_btf:
        _caso("nada resoluble",
              ["--structs", "no_existe_aaa,no_existe_bbb", "--listar"], 4)
        # Un nombre con espacios alrededor SI se resuelve.
        _caso("espacios alrededor", ["--structs", " amdgpu_bo ", "--listar"], 0)
    else:
        print("  OMIT  la BTF no esta: 3 casos que la necesitan no se comprueban")

    # rc=5: --structs dado pero vacio. NO debe caer a la lista por defecto: eso
    # seria una sustitucion silenciosa, y es el fallo que este caso vigila.
    _caso("--structs vacio (no cae a la lista)", ["--structs", ""], 5)
    _caso("--structs de solo comas", ["--structs", " , , "], 5)

    if hay_btf:
        # El contenido que se guarda tiene que ser utilizable: si el snapshot
        # no dice de que BTF viene, no es comprobable por un tercero.
        salida = os.path.join(_AQUI, ".selftest-layouts.txt")
        rc, _ruido = _silencioso(["--salida", salida, "--structs", "amdgpu_bo"])
        try:
            txt = open(salida, errors="replace").read()
            tiene_prov = "sha256 de la BTF" in txt and "pahole" in txt
            print("  %-46s rc=%d  procedencia=%s (esperado 0 y True)"
                  % ("snapshot con procedencia", rc, tiene_prov))
            if rc != 0 or not tiene_prov:
                fallos.append("el snapshot debe llevar la procedencia")
        except OSError as e:
            fallos.append("no se pudo leer el snapshot: %s" % e)
        finally:
            if os.path.exists(salida):
                os.remove(salida)

    print()
    if fallos:
        for f in fallos:
            print("  FALLA %s" % f)
        return 1
    print("  selftest correcto")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="snapshot de layouts de struct desde la BTF de un modulo")
    ap.add_argument("--btf", default=BTF_POR_DEFECTO)
    ap.add_argument("--salida", default=None)
    ap.add_argument("--structs", default=None,
                    help="lista separada por comas; por defecto la curada")
    ap.add_argument("--comparar", action="store_true",
                    help="compara contra lo guardado y sale 1 si hay deriva")
    ap.add_argument("--listar", action="store_true",
                    help="solo enumera estado y tamanos; no escribe nada")
    ap.add_argument("--selftest", action="store_true",
                    help="comprueba los caminos de fallo de esta herramienta")
    ap.add_argument("--version", action="version",
                    version="btfsnap %s" % VERSION)
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()

    ph = _pahole()
    if not ph:
        print("NO ESTA pahole. Sin el no hay forma de resolver el layout desde "
              "la BTF, y no se inventa.", file=sys.stderr)
        return 3
    pahole, ver_pahole = ph

    if not os.path.exists(a.btf):
        print("NO EXISTE la BTF: %s" % a.btf, file=sys.stderr)
        print("La BTF es por arranque. Si falta, este layout ya no se puede "
              "sacar de la BTF y no hay de donde reconstruirlo.", file=sys.stderr)
        return 2

    mod = os.path.basename(a.btf)
    salida = a.salida or os.path.join(_AQUI, "btf-%s-layouts.txt" % mod)
    if a.structs is None:
        nombres = list(STRUCTS_POR_DEFECTO)
    else:
        nombres = [x.strip() for x in a.structs.split(",") if x.strip()]
        if not nombres:
            # `--structs ""` (o solo comas) NO significa "la lista por defecto".
            # Caer a la lista por defecto seria una sustitucion silenciosa: el
            # usuario pide una cosa y recibe otra, sin que nada lo diga. Se
            # rechaza en vez de adivinar.
            print("--structs se dio pero no queda ningun nombre. Si querias la "
                  "lista por defecto, omite --structs.", file=sys.stderr)
            return 5

    resueltos, ausentes, errores = {}, [], []
    for n in nombres:
        tam, mot = _tamano_de(pahole, a.btf, n)
        if tam is None:
            ausentes.append((n, mot))
            continue
        cuerpo, mot2 = _campos_de(pahole, a.btf, n)
        if cuerpo is None:
            errores.append((n, mot2))
            continue
        resueltos[n] = (tam, cuerpo)

    if not resueltos:
        print("NINGUNA de las %d structs pedidas se pudo resolver. No se "
              "escribe un snapshot vacio, porque un fichero vacio pareceria "
              "una medida." % len(nombres), file=sys.stderr)
        for n, m in ausentes:
            print("  NO_EN_BTF %-22s %s" % (n, m), file=sys.stderr)
        return 4

    if a.listar:
        print("BTF %s   pahole %s" % (a.btf, ver_pahole))
        print()
        for n in nombres:
            if n in resueltos:
                tam = resueltos[n][0]
                print("  OK        %-22s %8d bytes%s"
                      % (n, tam, "   <-- grande" if tam >= TAMANO_AVISO else ""))
            elif any(n == x for x, _ in errores):
                print("  ERROR     %-22s" % n)
            else:
                print("  NO_EN_BTF %-22s" % n)
        print()
        if ausentes:
            print("NO_EN_BTF no es PROVEN_ABSENT: la BTF del modulo solo cubre")
            print("los tipos que el modulo exporta, y que falte aqui no dice")
            print("nada sobre el kernel. Ejemplo medido: drm_bo NO esta, y")
            print("drm_gem_object SI: es un renombrado, no una ausencia.")
        else:
            print("Todas las structs pedidas se resolvieron, asi que en esta")
            print("ejecucion no hay ninguna NO_EN_BTF y no se mezcla con esa")
            print("categoria, que significa otra cosa.")
        return 0

    try:
        h = _sha256(a.btf)
        st = os.stat(a.btf)
        uname = subprocess.run(["uname", "-r"], capture_output=True,
                               text=True, timeout=30).stdout.strip()
    except OSError as e:
        print("No se pudo leer la BTF: %s" % e, file=sys.stderr)
        return 5

    grande = [n for n in resueltos
              if resueltos[n][0] >= TAMANO_AVISO]

    partes = []
    partes.append("=" * 78)
    partes.append("LAYOUTS DE STRUCT DESDE LA BTF DEL MODULO -- snapshot de "
                  "btfsnap %s" % VERSION)
    partes.append("=" * 78)
    partes.append("")
    partes.append("PROCEDENCIA (esto es lo que hace que el fichero sea "
                  "comprobable)")
    partes.append("  fichero BTF      %s" % a.btf)
    partes.append("  modulo           %s" % mod)
    partes.append("  sha256 de la BTF %s" % h)
    partes.append("  bytes de la BTF  %d" % st.st_size)
    partes.append("  mtime de la BTF  %s" % time.strftime(
        "%Y-%m-%dT%H:%M:%S%z", time.localtime(st.st_mtime)))
    partes.append("  kernel           %s" % uname)
    partes.append("  pahole           %s" % ver_pahole)
    partes.append("  invocacion       %s -C <struct> %s" % (
        os.path.basename(pahole), mod))
    partes.append("  generado         %s" % time.strftime(
        "%Y-%m-%dT%H:%M:%S%z"))
    partes.append("")
    partes.append("LA BTF ES PERECEDERA. Es por arranque, y en esta maquina se")
    partes.append("reescribio dentro del mismo arranque. Este fichero es la copia")
    partes.append("que sobrevive; la BTF no.")
    partes.append("")
    if grande:
        partes.append("AVISO de tamano: %s ocupan mas de %d bytes. Su volcado "
                      "esta integro, pero"
                      % (", ".join(sorted(grande)), TAMANO_AVISO))
        partes.append("es raro que haga falta leerlo entero.")
        partes.append("")
    if ausentes:
        partes.append("NO_RESUELTAS (NO_EN_BTF, que NO es PROVEN_ABSENT):")
        for n, m in sorted(ausentes):
            partes.append("  %-24s %s" % (n, m))
        if errores:
            partes.append("")
            partes.append("ERRORES (estos SI son fallos, no ausencias):")
            for n, m in sorted(errores):
                partes.append("  %-24s %s" % (n, m))
        partes.append("")
    partes.append("=" * 78)
    partes.append("")
    for n in nombres:
        if n not in resueltos:
            continue
        tam, cuerpo = resueltos[n]
        partes.append(cuerpo.rstrip())
        partes.append("")
    partes.append("=" * 78)
    partes.append("fin del snapshot: %d structs resueltas, %d no resueltas, "
                  "%d errores" % (len(resueltos), len(ausentes), len(errores)))
    partes.append("=" * 78)
    texto = "\n".join(partes) + "\n"

    previo = None
    if os.path.exists(salida):
        try:
            with open(salida, errors="replace") as f:
                previo = f.read()
        except OSError as e:
            print("No se pudo leer lo guardado: %s" % e, file=sys.stderr)
            return 5

    try:
        with open(salida, "w") as f:
            f.write(texto)
    except OSError as e:
        print("No se pudo escribir %s: %s" % (salida, e), file=sys.stderr)
        return 5

    print("BTF      %s" % a.btf)
    print("  sha256 %s" % h)
    print("  pahole %s" % ver_pahole)
    print("  structs %d resueltas de %d pedidas" % (len(resueltos), len(nombres)))
    if ausentes:
        print("  NO_EN_BTF %d: %s" % (len(ausentes),
                                      ", ".join(n for n, _ in sorted(ausentes))))
    if errores:
        print("  ERRORES %d: %s" % (len(errores),
                                   ", ".join(n for n, _ in sorted(errores))))
    print("salida   %s (%d bytes)" % (salida, len(texto)))

    if a.comparar:
        if previo is None:
            print("deriva   no habia snapshot anterior: este es el primero")
            return 0
        # DERIVA se mide sobre el texto NORMALIZADO. Sin normalizar salia un
        # falso positivo en CADA ejecucion, porque la linea `generado` lleva la
        # hora y cambia siempre: dos ejecuciones seguidas sobre una BTF igual
        # daban "deriva" y era mentira. Un detector que siempre dice que algo
        # cambio no detecta nada.
        def _norm(t):
            return [l for l in t.splitlines()
                    if not l.strip().startswith("generado")]
        pa, pb = _norm(previo), _norm(texto)
        if pa == pb:
            print("deriva   NINGUNA: el texto es identico al guardado, una vez")
            print("          quitada la linea de hora, que cambia siempre")
            return 0
        # Ahora si hay diferencia real, y se dice DONDE, no que la linea 1 cambio.
        dif = []
        for i in range(max(len(pa), len(pb))):
            x = pa[i] if i < len(pa) else "<fin>"
            y = pb[i] if i < len(pb) else "<fin>"
            if x != y:
                dif.append((i + 1, x, y))
        def _firma(t):
            return [l for l in t.splitlines()
                    if "sha256 de la BTF" in l or "bytes de la BTF" in l]
        camb = ("la BTF cambio (sha256 o tamano)"
                if _firma(previo) != _firma(texto)
                else "la BTF es la misma pero el layout se imprime distinto")
        print("DERVA    %s" % camb)
        print("          %d linea(s) difieren; las 6 primeras:" % len(dif))
        for num, x, y in dif[:6]:
            print("            L%-5d - %s" % (num, x.strip()[:64]))
            print("                   + %s" % y.strip()[:64])
        if len(dif) > 6:
            print("            ... y %d mas" % (len(dif) - 6))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
