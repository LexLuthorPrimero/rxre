#!/usr/bin/env python3
"""RXRE-FUEGO-001: la limpieza de temporales NO puede borrar el artefacto original.

DEFECTO QUE CUBRE
-----------------
`rz_callgraph._limpiar_tmp` y `rz_xrefs._limpiar_tmp` reciben `borra` y hacen
`os.unlink(tmp_path)` cuando `borra` es cierto. Su docstring dice:

    "Borra el temp file solo si corresponde (no si era el path original)"

Pero las doce llamadas pasan `es_path`, y `es_path` significa exactamente
"este tmp_path ES el archivo original". La bandera esta invertida:

    es_path == True   -> tmp_path es el ORIGINAL   -> se BORRA  (destruccion)
    es_path == False  -> tmp_path es un TEMPORAL   -> NO se borra (fuga)

CONDICION EXACTA DEL BORRADO
----------------------------
`artefacto` es un `str` que `os.path.isfile()` reconoce, y el flujo llega a
cualquiera de las seis llamadas de limpieza (backend ausente, timeout, rc != 0,
salida no-JSON, JSON invalido, exito).

REGLAS DE ESTE TEST
-------------------
1. Solo se usan archivos SENUELO creados por el propio test en un directorio
   temporal aislado. Nunca un artefacto real de la investigacion.
2. TMPDIR se aisla para poder observar exactamente que temporales crea RXRE.
3. Cada test es independiente y reporta FAIL/PASS explicitamente.
"""
import importlib
import json
import os
import shutil
import sys
import tempfile

RAIZ = "/home/lucas/Escritorio/rxre"
for _p in (os.path.join(RAIZ, "tools"), os.path.join(RAIZ, "tools", "rxre")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backends.adapters import rz_callgraph as CG  # noqa: E402
from backends.adapters import rz_xrefs as XR       # noqa: E402

# Fuente ELF canonica para los senuelos. Es un binario del sistema; aqui solo
# se COPIA a un temporal y la copia es lo que RXRE analizara.
FUENTE_ELF = "/bin/true"

_fallos = []
_pasados = []


def chk(descripcion, condicion, detalle=""):
    """Assert con reporte: acumula fallos en vez de abortar el test entero."""
    if condicion:
        _pasados.append(descripcion)
        print("    ok   %s" % descripcion)
    else:
        _fallos.append("%s %s" % (descripcion, detalle))
        print("    FAIL %s %s" % (descripcion, detalle))
    return bool(condicion)


# TMPDIR del sistema, memorizado ANTES de que ningun test lo toque, para poder
# crear un workspace nuevo aunque el anterior ya haya sido borrado.
_TMPDIR_SISTEMA = os.environ.get("TMPDIR") or tempfile.gettempdir()


def _nuevo_workspace(prefijo):
    """Crea un workspace aislado y lo convierte en el TMPDIR de tempfile.

    El orden importa: primero hay que devolver tempfile.gettempdir() a un sitio
    REAL (el del sistema), porque `tempfile.tempdir` queda cacheado y puede
    apuntar al workspace del test anterior, ya borrado. Luego se crea el nuevo
    y se aisla.
    """
    os.environ["TMPDIR"] = _TMPDIR_SISTEMA
    tempfile.tempdir = _TMPDIR_SISTEMA
    ws = tempfile.mkdtemp(prefix=prefijo)
    os.environ["TMPDIR"] = ws
    importlib.reload(tempfile)
    tempfile.tempdir = ws
    return ws


def _senuelo_elf(ws, nombre="canary.elf"):
    """Crea un senuelo ELF real (copia de un binario del sistema)."""
    destino = os.path.join(ws, nombre)
    shutil.copy2(FUENTE_ELF, destino)
    return destino


def _temporales_rxre(ws):
    """Ficheros que RXRE creo como temporal (NamedTemporaryFile suffix='.bin')."""
    return sorted(f for f in os.listdir(ws) if f.startswith("tmp") and f.endswith(".bin"))


# ---------------------------------------------------------------- T1
def t1_callgraph_original_sobrevive():
    """T1: binary.callgraph con archivo original -> el original sobrevive."""
    ws = _nuevo_workspace("rxre_t1_")
    try:
        original = _senuelo_elf(ws)
        CG.callgraph(original)
        chk("T1 callgraph: el artefacto original sobrevive",
            os.path.isfile(original),
            "(el fichero fue BORRADO)")
    finally:
        shutil.rmtree(ws, ignore_errors=True)
        os.environ["TMPDIR"] = _TMPDIR_SISTEMA
        tempfile.tempdir = _TMPDIR_SISTEMA


# ---------------------------------------------------------------- T2
def t2_xrefs_original_sobrevive():
    """T2: binary.xrefs con archivo original -> el original sobrevive."""
    ws = _nuevo_workspace("rxre_t2_")
    try:
        original = _senuelo_elf(ws)
        XR.xrefs(original)
        chk("T2 xrefs: el artefacto original sobrevive",
            os.path.isfile(original),
            "(el fichero fue BORRADO)")
    finally:
        shutil.rmtree(ws, ignore_errors=True)
        os.environ["TMPDIR"] = _TMPDIR_SISTEMA
        tempfile.tempdir = _TMPDIR_SISTEMA


# ---------------------------------------------------------------- T3
def t3_callgraph_temporal_de_bytes_se_limpia():
    """T3: entrada por bytes -> RXRE crea un temporal -> debe limpiarlo."""
    ws = _nuevo_workspace("rxre_t3_")
    try:
        with open(FUENTE_ELF, "rb") as fh:
            datos = fh.read()
        CG.callgraph(datos)
        chk("T3 callgraph bytes: no queda temporal huerfano",
            _temporales_rxre(ws) == [],
            "(temporales sin limpiar: %s)" % _temporales_rxre(ws))
    finally:
        shutil.rmtree(ws, ignore_errors=True)
        os.environ["TMPDIR"] = _TMPDIR_SISTEMA
        tempfile.tempdir = _TMPDIR_SISTEMA


# ---------------------------------------------------------------- T4
def t4_callgraph_fixture_se_limpia():
    """T4: fixture_json -> RXRE crea un temporal -> debe limpiarlo.

    Variante semanticamente distinta: en modo fixture `es_path` NUNCA se
    asigna. La expresion `es_path if not fixture_json else False` evita el
    NameError pero evalua a False, con lo que el temporal queda huerfano.
    """
    ws = _nuevo_workspace("rxre_t4_")
    try:
        with open(FUENTE_ELF, "rb") as fh:
            datos = fh.read()
        # MEDIDO: fixture_json debe ser un JSON VALIDO. El hex crudo NO lo es:
        # json.loads("7f454c46...") lanza y el adapter devuelve invalid_input
        # ANTES de crear el temporal, con lo que no probaria nada.
        CG.callgraph(b"", fixture_json=json.dumps(datos.hex()))
        chk("T4 callgraph fixture: no queda temporal huerfano",
            _temporales_rxre(ws) == [],
            "(temporales sin limpiar: %s)" % _temporales_rxre(ws))
    finally:
        shutil.rmtree(ws, ignore_errors=True)
        os.environ["TMPDIR"] = _TMPDIR_SISTEMA
        tempfile.tempdir = _TMPDIR_SISTEMA


# ---------------------------------------------------------------- T5
def t5_xrefs_bytes_se_limpia():
    """T5: xrefs con bytes -> RXRE crea un temporal -> debe limpiarlo."""
    ws = _nuevo_workspace("rxre_t5_")
    try:
        with open(FUENTE_ELF, "rb") as fh:
            datos = fh.read()
        XR.xrefs(datos)
        chk("T5 xrefs bytes: no queda temporal huerfano",
            _temporales_rxre(ws) == [],
            "(temporales sin limpiar: %s)" % _temporales_rxre(ws))
    finally:
        shutil.rmtree(ws, ignore_errors=True)
        os.environ["TMPDIR"] = _TMPDIR_SISTEMA
        tempfile.tempdir = _TMPDIR_SISTEMA


# ---------------------------------------------------------------- T6
def t6_entrada_invalida_no_borra_nada():
    """T5 del encargo: ruta ambigua o invalida -> no se borra nada.

    Un `str` que no es un fichero existente NO debe provocar borrado de nada,
    y un fichero preexistente que no es ELF debe sobrevivir.
    """
    ws = _nuevo_workspace("rxre_t6_")
    try:
        ruta_inexistente = os.path.join(ws, "no-existe-este-fichero")
        CG.callgraph(ruta_inexistente)
        chk("T6a ruta inexistente: el adapter no lanzo excepcion", True)
        chk("T6b ruta inexistente: no se creo ni se borro nada",
            not os.path.exists(ruta_inexistente))

        # Fichero preexistente que NO es ELF: debe rechazarse sin borrarlo.
        no_elf = os.path.join(ws, "no-es-elf.bin")
        with open(no_elf, "wb") as fh:
            fh.write(b"esto no es un ELF" * 64)
        CG.callgraph(no_elf)
        chk("T6c fichero no-ELF preexistente: sobrevive al rechazo",
            os.path.isfile(no_elf),
            "(el fichero fue BORRADO)")

        no_elf2 = os.path.join(ws, "no-es-elf-2.bin")
        with open(no_elf2, "wb") as fh:
            fh.write(b"esto tampoco es un ELF" * 64)
        XR.xrefs(no_elf2)
        chk("T6d xrefs fichero no-ELF preexistente: sobrevive al rechazo",
            os.path.isfile(no_elf2),
            "(el fichero fue BORRADO)")
    finally:
        shutil.rmtree(ws, ignore_errors=True)
        os.environ["TMPDIR"] = _TMPDIR_SISTEMA
        tempfile.tempdir = _TMPDIR_SISTEMA


# ---------------------------------------------------------------- T7
def t7_limpiar_tmp_caminos_exito_y_error():
    """T6 del encargo: caminos de exito y error de la propia _limpiar_tmp."""
    ws = _nuevo_workspace("rxre_t7_")
    try:
        # camino 1: borra=False -> no borra
        a = os.path.join(ws, "a.bin")
        open(a, "w").close()
        CG._limpiar_tmp(a, False)
        chk("T7a _limpiar_tmp(borra=False): conserva el fichero", os.path.isfile(a))

        # camino 2: borra=True -> borra
        b = os.path.join(ws, "b.bin")
        open(b, "w").close()
        CG._limpiar_tmp(b, True)
        chk("T7b _limpiar_tmp(borra=True): borra el fichero", not os.path.exists(b))

        # camino 3: error -> no propaga (OSError silenciado)
        try:
            CG._limpiar_tmp(os.path.join(ws, "no-existe.bin"), True)
            chk("T7c _limpiar_tmp sobre inexistente: no propaga OSError", True)
        except OSError as exc:
            chk("T7c _limpiar_tmp sobre inexistente: no propaga OSError", False,
                "(propago %r)" % exc)

        # misma matriz para rz_xrefs
        c = os.path.join(ws, "c.bin")
        open(c, "w").close()
        XR._limpiar_tmp(c, False)
        chk("T7d xrefs._limpiar_tmp(borra=False): conserva el fichero", os.path.isfile(c))

        d = os.path.join(ws, "d.bin")
        open(d, "w").close()
        XR._limpiar_tmp(d, True)
        chk("T7e xrefs._limpiar_tmp(borra=True): borra el fichero", not os.path.exists(d))
    finally:
        shutil.rmtree(ws, ignore_errors=True)
        os.environ["TMPDIR"] = _TMPDIR_SISTEMA
        tempfile.tempdir = _TMPDIR_SISTEMA


# ---------------------------------------------------------------- T8
def t8_original_sobrevive_a_rutas_de_error():
    """T3 del encargo: si la operacion falla, el original tambien sobrevive.

    Se fuerzan rutas de error del adapter sobre un ORIGINAL real:
      - backend ausente (se pasa un backend_id inexistente),
      - fichero original corrupto que hace que el producer falle.
    """
    ws = _nuevo_workspace("rxre_t8_")
    try:
        original_a = _senuelo_elf(ws, "err-backend.elf")
        CG.callgraph(original_a, backend_id="no-existe-este-backend")
        chk("T8a callgraph backend ausente: el original sobrevive",
            os.path.isfile(original_a), "(el fichero fue BORRADO)")

        original_b = _senuelo_elf(ws, "err-producer.elf")
        with open(original_b, "r+b") as fh:   # rompe el contenido del ELF
            fh.seek(0)
            fh.write(b"\x00" * 32)
        CG.callgraph(original_b)
        chk("T8b callgraph producer falla: el original sobrevive",
            os.path.isfile(original_b), "(el fichero fue BORRADO)")

        original_c = _senuelo_elf(ws, "err-xrefs.elf")
        with open(original_c, "r+b") as fh:
            fh.seek(0)
            fh.write(b"\x00" * 32)
        XR.xrefs(original_c)
        chk("T8c xrefs producer falla: el original sobrevive",
            os.path.isfile(original_c), "(el fichero fue BORRADO)")
    finally:
        shutil.rmtree(ws, ignore_errors=True)
        os.environ["TMPDIR"] = _TMPDIR_SISTEMA
        tempfile.tempdir = _TMPDIR_SISTEMA


TESTS = [t1_callgraph_original_sobrevive,
         t2_xrefs_original_sobrevive,
         t3_callgraph_temporal_de_bytes_se_limpia,
         t4_callgraph_fixture_se_limpia,
         t5_xrefs_bytes_se_limpia,
         t6_entrada_invalida_no_borra_nada,
         t7_limpiar_tmp_caminos_exito_y_error,
         t8_original_sobrevive_a_rutas_de_error]


if __name__ == "__main__":
    print("=" * 78)
    print("RXRE-FUEGO-001: el original NO puede ser borrado por la limpieza")
    print("=" * 78)
    for t in TESTS:
        print("\n== %s ==" % t.__name__)
        try:
            t()
        except Exception as exc:  # una excepcion tambien es un fallo
            _fallos.append("%s lanzo %r" % (t.__name__, exc))
            print("    FAIL %s lanzo %r" % (t.__name__, exc))
    print("\n" + "=" * 78)
    print("RESUMEN: %d comprobaciones ok, %d FAIL" % (len(_pasados), len(_fallos)))
    for f in _fallos:
        print("  FAIL %s" % f)
    print("=" * 78)
    sys.exit(1 if _fallos else 0)