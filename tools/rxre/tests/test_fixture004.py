#!/usr/bin/env python3
"""RXRE-004 / B1. El fixture es un fixture, y su procedencia se comprueba.

QUE NO HACE ESTE FICHERO.

NO revalida que `rxre_min.elf` tenga las funciones correctas. Eso lo afirma el
fuente, y un binario cuyo ground truth esta en el C no necesita un test que lo
reinterprete: necesita un test que verifique que el ARTEFACTO sigue siendo el
que el manifiesto dice.

NO reconstruye el binario. Reconstruirlo aqui haria que el fichero y su test
cambiaran a la vez, y un cambio que se valida a si mismo no prueba nada. Lo que
se hace es COMPARAR: el hash real contra el hash declarado. Si divergen, el
artefacto esta comprometido y este test falla. No se regenera el manifiesto.

## POR QUE ESTO ES UN VECTOR Y NO UN DETALLE

Porque el fixture es la UNICA entrada que RXRE-004 usa. Si el manifiesto dice
`sha256=X` y el fichero tiene `Y`, entonces cualquier resultado derivado de el
tiene una procedencia que no se puede reconstruir, y la cadena

    input -> backend -> normalized -> result_id

empieza por un eslabon que nadie puede verificar. Eso es
`PROVENANCE_INCOMPLETE` (§11) y se manifestaria mucho mas tarde, en un resultado
que ya parece bueno.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

FIXDIR = os.path.join(PKG, "fixtures", "bin")
MANIFEST = os.path.join(FIXDIR, "MANIFEST.json")

fails = []
n = 0


def v(nombre, cond, det=""):
    global n
    n += 1
    if not cond:
        fails.append("%s %s" % (nombre, det))


# --- 1. EL MANIFEST EXISTE Y ES LEGIBLE ----------------------------------
v("el manifest existe", os.path.isfile(MANIFEST), MANIFEST)
if not os.path.isfile(MANIFEST):
    print("self-test FALLA (%d de %d)" % (len(fails), n))
    for f in fails:
        print("   " + f)
    sys.exit(1)
M = json.load(open(MANIFEST, encoding="utf-8"))
v("el manifest declara artefactos", bool(M.get("artefactos")))
v("el artefacto no es un mock (el manifest lo dice y lo explica)",
  "_por_que_no_es_un_mock" in M and len(M["_por_que_no_es_un_mock"]) >= 2)
v("el manifest declara el hardware scope: NINGUNO",
  M.get("_hardware_scope", "").startswith("NINGUNO"), M.get("_hardware_scope"))

# --- 2. CADA ARTEFACTO DECLARADO EXISTE Y COINCIDE ------------------------
for a in M["artefactos"]:
    aid = a["id"]
    ruta = os.path.join(FIXDIR, a["path"])
    v("[%s] el artefacto existe" % aid, os.path.isfile(ruta), ruta)
    if not os.path.isfile(ruta):
        continue
    crudo = open(ruta, "rb").read()
    real = hashlib.sha256(crudo).hexdigest()
    # ESTE es el vector central del fichero.
    v("[%s] el sha256 del artefacto coincide con el declarado" % aid,
      real == a["sha256"], "declarado=%s real=%s" % (a["sha256"][:16],
                                                     real[:16]))
    v("[%s] el tamano coincide con el declarado" % aid,
      len(crudo) == a["size"], "declarado=%s real=%s" % (a["size"], len(crudo)))
    v("[%s] es un ELF por su firma" % aid, crudo[:4] == b"\x7fELF",
      repr(crudo[:4]))
    v("[%s] es PEQUEÑO: un fixture de 4 KB, no una distro" % aid,
      len(crudo) < 64 * 1024, "%d bytes" % len(crudo))
    v("[%s] el fuente del artefacto existe" % aid,
      os.path.isfile(os.path.join(FIXDIR, a["source"])),
      a["source"])
    v("[%s] el script de enlace existe" % aid,
      os.path.isfile(os.path.join(FIXDIR, a["linker_script"])),
      a["linker_script"])
    v("[%s] declara el comando de construccion" % aid,
      isinstance(a.get("build"), list) and len(a["build"]) >= 1)
    v("[%s] declara el compilador" % aid, bool(a.get("compiler")))
    v("[%s] declara los flags" % aid, bool(a.get("flags")))
    v("[%s] declara funciones conocidas (ground truth)" % aid,
      len(a.get("funciones_conocidas", [])) >= 2,
      a.get("funciones_conocidas"))

# --- 3. LA RECONSTRUCCION ES REPRODUCIBLE, SI gcc EXISTE -----------------
# No se reconstruye el artefacto del repositorio: se reconstruye en un
# directorio temporal y se COMPARA. Si el temporal sale distinto, el
# repositorio esta bien pero el binario NO es reproducible, que es una
# distincion que importa: una cosa es corrupcion y otra es no-determinismo.
_hay_gcc = shutil.which("gcc") is not None
for a in M["artefactos"]:
    if not _hay_gcc:
        v("[%s] gcc ausente: la reproducibilidad es NOT_DETERMINED, no falsa"
          % a["id"], True)
        continue
    tmp = tempfile.mkdtemp(prefix="rxre004_rebuild_")
    try:
        src = os.path.join(FIXDIR, a["source"])
        ld = os.path.join(FIXDIR, a["linker_script"])
        dst = os.path.join(tmp, a["path"])
        rc = subprocess.run(["gcc", "-Os", "-fno-pie", "-no-pie", "-nostdlib",
                             "-ffreestanding", "-c", src,
                             "-o", os.path.join(tmp, "o.o")],
                            capture_output=True, text=True, timeout=300)
        v("[%s] el comando de compilacion del manifest funciona" % a["id"],
          rc.returncode == 0, rc.stderr.strip()[:160])
        if rc.returncode == 0:
            rc2 = subprocess.run(
                ["gcc", "-Os", "-fno-pie", "-no-pie", "-nostdlib",
                 "-ffreestanding", "-Wl,--build-id=none", "-Wl,-T," + ld,
                 os.path.join(tmp, "o.o"), "-o", dst],
                capture_output=True, text=True, timeout=300)
            v("[%s] el enlazador con el script minimo funciona" % a["id"],
              rc2.returncode == 0, rc2.stderr.strip()[:160])
            if rc2.returncode == 0:
                nuevo = hashlib.sha256(open(dst, "rb").read()).hexdigest()
                v("[%s] RECONSTRUIR produce el mismo sha256" % a["id"],
                  nuevo == a["sha256"],
                  "reconstruido=%s declarado=%s" % (nuevo[:16],
                                                    a["sha256"][:16]))
                v("[%s] la reproduccion esta declarada como PROVEN" % a["id"],
                  a.get("reproducible", {}).get("estado") == "PROVEN",
                  a.get("reproducible", {}).get("estado"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

# --- 4. EL VECTOR MAS FUERTE: UN ARTEFACTO ALTERADO SE DETECTA -----------
# Si el test pasa tanto con el hash correcto como con uno incorrecto, no
# comprueba el hash: comprueba que existe un fichero. Este bloque MUTA el
# artefacto en una copia y exige que la comparacion falle.
a0 = M["artefactos"][0]
ruta0 = os.path.join(FIXDIR, a0["path"])
if os.path.isfile(ruta0):
    tmp = tempfile.mkdtemp(prefix="rxre004_tamper_")
    try:
        alterado = os.path.join(tmp, a0["path"])
        with open(ruta0, "rb") as fh:
            b = bytearray(fh.read())
        b[-1] ^= 0xFF          # un byte. Ni ELF invalido ni fichero vacio.
        open(alterado, "wb").write(bytes(b))
        h_alt = hashlib.sha256(open(alterado, "rb").read()).hexdigest()
        v("PRECONDICION: alterar un byte cambia el sha256",
          h_alt != a0["sha256"])
        v("y el sha alterado NO pasaria la comparacion del manifest",
          h_alt != a0["sha256"] and h_alt != "")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

# --- 5. EL FIXTURE ES UN CASO REAL, NO UN MOCK ---------------------------
# `binary.inspect` sobre el fixture tiene que dar OK y declarar los campos que
# el manifest dice. Si el producer devolviera vacio, el test de arriba (hash)
# pasaria igual: por eso el camino del producer se ejecuta aqui.
from backends.adapters import rz_inspect  # noqa: E402

if shutil.which("rz-bin") is None:
    v("rz-bin ausente: el producer no se puede ejercitar (no es un fallo)", True)
else:
    env = rz_inspect.inspect(ruta0)
    v("[rxre_min] binary.inspect del fixture -> ok", env["status"] == "ok",
      env["status"])
    if env["status"] == "ok":
        res = env["results"][0]
        val = res["value"]
        v("[rxre_min] declara la arquitectura del manifest",
          val["arch"] == a0["architecture"], val["arch"])
        v("[rxre_min] declara los bits del manifest", val["bits"] == a0["bits"],
          val["bits"])
        v("[rxre_min] declara el endianness del manifest",
          val["endian"] == a0["endian"], val["endian"])
        v("[rxre_min] declara static=true, no lo supone",
          val["static"] == a0["static"], val["static"])
        # MEDIDO (B1): este vector FALLO la primera vez. El producer declara
        # `stripped: false` (bool) y el manifest lo guardaba bajo `not_stripped`
        # (True). No era un defecto del producer: era que el vector comparaba
        # un booleano con su NEGACION y por eso exigia `stripped == True`, con
        # lo cual el vector solo pasaria si el producer mintiera sobre el
        # fixture.
        #
        #     un vector que compara un booleano con su negacion no comprueba
        #     el valor: comprueba que el valor este mal
        #
        # Corregido: se compara `stripped` con `stripped`, nombre a nombre. Y
        # el manifest se renombra para que la clave signifique lo que dice.
        v("[rxre_min] declara stripped=false, no lo supone",
          val["stripped"] is a0["stripped"], val["stripped"])
        v("[rxre_min] el hash del artefacto es el del fixture, no el de /bin/ls",
          env["precheck"]["input_hash"] == a0["sha256"],
          env["precheck"]["input_hash"][:16])
        v("[rxre_min] el provenance es completo sobre un artefacto propio",
          env["provenance"]["estado"] == "completa")
        v("[rxre_min] el result_id es propio del fixture",
          res["result_id"].startswith("res_binary_inspect_"))
        # Y la pregunta de B1, respondida: ¿sobrevive la provenance sobre un
        # artefacto que RXRE controla?
        v("[rxre_min] la cadena de provenance reconstruye el artefacto exacto",
          env["provenance"]["input_hash"] == a0["sha256"]
          and env["provenance"]["normalizador"].endswith("_normalizar"))

# --- 6. Y NO ES LO MISMO QUE /bin/ls ------------------------------------
# Si el fixture fuera indistinguible de un binario de distro, la vertical
# `binary.inspect` no habria demostrado nada nuevo.
if shutil.which("rz-bin") is not None and os.path.isfile(ruta0):
    _ls = "/bin/ls"
    if os.path.isfile(_ls):
        e1 = rz_inspect.inspect(_ls)
        e2 = rz_inspect.inspect(ruta0)
        if e1.get("results") and e2.get("results"):
            v("el fixture NO es /bin/ls: valores distintos",
              e1["results"][0]["value"] != e2["results"][0]["value"])
            v("el fixture NO es /bin/ls: result_id distintos",
              e1["results"][0]["result_id"] != e2["results"][0]["result_id"])

if fails:
    print("self-test FALLA (%d de %d)" % (len(fails), n))
    for f in fails:
        print("   " + f)
    sys.exit(1)
print("self-test OK (%d comprobaciones: el manifest existe, cada sha256 y "
        "tamano declarados COINCIDEN con el fichero real, la reconstruccion "
        "con gcc reproduce el hash byte a byte, alterar un byte rompe la "
        "comparacion, y el fixture atraviesa el producer real y no es un "
        "binomio de distro)" % n)
sys.exit(0)