#!/usr/bin/env python3
"""MUTACION: ¿los tests de las 7 v3 realmente discriminan?

FASE 1, criterio 2: "7 correcciones v3 verificadas por contraste (no solo por
test que pasa)".

Un test que pasa no prueba nada sobre la correccion que dice comprobar: pasa
igual con ella, sin ella, y con la mecanica al reves. Lo que lo prueba es
BORRAR la correccion y comprobar que el test pasa a FAIL.

Este fichero hace eso de verdad: copia el paquete a un temporal, ROMPE una
correccion, ejecuta el test contra la copia rota, y exige FAIL. Si un test
sigue pasando con la correccion destruida, el test no discrimina: DECLARA.

    un contraste que no se rompe no es un contraste

Uso:  python3 test_arquitectura_v3_03_mutacion.py
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
ORIGEN = os.path.join(PKG, "arquitectura")
TESTS = (
    "test_arquitectura_v3_01_contracts.py",
    "test_arquitectura_v3_02_v3.py",
)

# Cada mutacion: (correccion, fichero, [(viejo, nuevo), ...], que se rompe)
MUTACIONES = [
    ("V3-1_ETER_TRES_MODOS_Y_WRITE_AHEAD", "ETER.py", [
        # (a) el descarte deja de CONTARSE: el sistema miente sobre si mismo
        ("self.estadisticas.descartados_saturacion.incr()",
         "pass  # MUTADO: el descarte ya no se cuenta"),
        # (b) el fsync se declara HECHO cuando fallo: el write-ahead miente
        #     justo en la ventana de CAIDA_PROCESO que la v3-1 nombra
        ('pasos.update({"fsync": False, "error": str(exc),',
         'pasos.update({"fsync": True, "error": str(exc),'),
    ]),
    ("V3-2_INVALIDATED_CON_REEVALUACION", "TIERRA.py", [
        # la contradiccion invalida SOLA: la v3-2 desaparece entera
        ('"UPDATE claims SET contradiction_refs = json_insert"',
         '"UPDATE claims SET epistemic_state = \'INVALIDATED\', '
         'contradiction_refs = json_insert"'),
    ]),
    ("V3-3_CONCURRENCIA_POR_OPERACION", "TIERRA.py", [
        # el lock pasa a GLOBAL: serializa claims que no se tocan
        ("PRIMARY KEY (claim_id)\n);",
         "PRIMARY KEY ('LOCK_GLOBAL')\n);"),
    ]),
    ("V3-4_ROLLBACK_POR_DISPOSITIVO", "planos.py", [
        # el rollback global deja de estar prohibido
        ('if dispositivo_id in (None, "", "*", "todos", "global"):',
         'if False:'),
    ]),
    ("V3-5_INMUTABILIDAD_COMO_MECANISMO", "TIERRA.py", [
        # los triggers desaparecen -> la inmutabilidad pasa a ser un deseo
        ("CREATE TRIGGER IF NOT EXISTS trg_evidence_no_delete\n"
         "BEFORE DELETE ON evidence\nBEGIN\n"
         "    SELECT RAISE(ABORT, 'EVIDENCE_APPEND_ONLY: DELETE prohibido');\n"
         "END;",
         "-- MUTADO: trigger eliminado"),
        ("CREATE TRIGGER IF NOT EXISTS trg_evidence_no_update\n"
         "BEFORE UPDATE ON evidence\nBEGIN\n"
         "    SELECT RAISE(ABORT, 'EVIDENCE_APPEND_ONLY: UPDATE prohibido');\n"
         "END;",
         "-- MUTADO: trigger eliminado"),
    ]),
    ("V3-6_HASH_TRES_CAPAS_SEPARADAS", "TIERRA.py", [
        # el hash vuelve a ser un veredicto unico: autenticidad := integridad
        ("        elif referencia_confiable == declared_hash:\n"
         "            autenticidad = AUTENTICIDAD_PASS\n"
         "        else:\n"
         "            autenticidad = AUTENTICIDAD_FAIL",
         "        else:  # MUTADO: auth deducida de la integridad\n"
         "            autenticidad = (INTEGRIDAD_PASS\n"
         "                            if actual == declared_hash\n"
         "                            else INTEGRIDAD_FAIL)"),
        # y la validez semantica se DEDUCE del hash: la v3-6 prohibe eso
        ("            validez = (TEST_PASS if prueba_semantica else TEST_FAIL)",
         "            validez = INTEGRIDAD_PASS  # MUTADO: validez deducida"),
    ]),
    ("V3-7_ACCEPTED_CON_AUTORIDAD_DECLARADA", "PUERTA.py", [
        # ACCEPTED pasa a ser un string manual: la v3-7 desaparece
        ("faltan = [k for k in CONDICIONES if not condiciones[k][\"cumple\"]]",
         "faltan = []  # MUTADO: acepta sin evaluar condiciones"),
    ]),
]


def aplicar(copia: str, fichero: str, cambios) -> tuple:
    ruta = os.path.join(copia, fichero)
    with open(ruta, "r", encoding="utf-8") as fh:
        src = fh.read()
    aplicados = 0
    for viejo, nuevo in cambios:
        if viejo not in src:
            return False, "patron no encontrado en %s" % fichero
        src = src.replace(viejo, nuevo, 1)
        aplicados += 1
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(src)
    return True, "%d/%d aplicados" % (aplicados, len(cambios))


def correr_tests(pkg_origen: str) -> tuple:
    """Ejecuta los tests contra un paquete YA COPIADO (y mutado).

    `pkg_origen` es el directorio que CONTIENE los .py, no su padre: si se
    pasa el padre, el arbol queda con `arquitectura/arq/*.py` y los tests
    importan un paquete vacio. El control de este mismo fichero falla si
    eso ocurre, que es lo que hace que un fallo aqui sea visible en vez de
    disfrazarse de "la mutacion no se detecto".
    """
    raiz = tempfile.mkdtemp(prefix="rxre-mut-")
    destino = os.path.join(raiz, "tools", "rxre")
    os.makedirs(destino)
    shutil.copytree(pkg_origen, os.path.join(destino, "arquitectura"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    tests_dir = os.path.join(destino, "tests")
    os.makedirs(tests_dir)
    for t in TESTS:
        shutil.copyfile(os.path.join(HERE, t), os.path.join(tests_dir, t))

    passes = 0
    fails = 0
    detalle = []
    for t in TESTS:
        proc = subprocess.run(
            [sys.executable, os.path.join(tests_dir, t)],
            capture_output=True, text=True, timeout=300)
        salida = proc.stdout + proc.stderr
        m = re.search(r"=== RESULTADO: (\d+) PASS, (\d+) FAIL ===", salida)
        if not m:
            detalle.append("%s: SIN RESUMEN" % t)
            fails += 1
            continue
        passes += int(m.group(1))
        fails += int(m.group(2))
    shutil.rmtree(raiz, ignore_errors=True)
    return passes, fails, detalle


print("=== MUTACION: los tests de las 7 v3 discriminan de verdad? ===")
print()

# --- control: sin mutar, todo pasa -------------------------------------
copia_ok = tempfile.mkdtemp(prefix="rxre-arq-ok-")
shutil.copytree(ORIGEN, os.path.join(copia_ok, "arq"),
                ignore=shutil.ignore_patterns("__pycache__"))
p, f, det = correr_tests(os.path.join(copia_ok, "arq"))
print("CONTROL (sin mutar):            %d PASS, %d FAIL" % (p, f))
if f != 0:
    print("  el control ya falla: la mutacion no seria concluyente")
    for d in det:
        print("  %s" % d)
    sys.exit(2)
shutil.rmtree(copia_ok, ignore_errors=True)

# --- mutar una por una -------------------------------------------------
filas = []
for correccion, fichero, cambios in MUTACIONES:
    copia = tempfile.mkdtemp(prefix="rxre-arq-mut-")
    destino = os.path.join(copia, "arq")
    shutil.copytree(ORIGEN, destino)
    ok, det = aplicar(destino, fichero, cambios)
    if not ok:
        filas.append((correccion, "NO_APLICADA", det))
        print("  %-42s  %s" % (correccion, det))
        shutil.rmtree(copia, ignore_errors=True)
        continue
    p, f, _ = correr_tests(destino)
    shutil.rmtree(copia, ignore_errors=True)
    discriminante = (f > 0)
    filas.append((correccion, "DISCRIMINA" if discriminante else "NO_DISCRIMINA",
                  "%d PASS, %d FAIL" % (p, f)))
    print("  %-42s  %s  (%d FAIL detectados)"
          % (correccion,
             "DISCRIMINA" if discriminante else "NO DISCRIMINA", f))

# --- veredicto ---------------------------------------------------------
print()
malas = [r for r in filas if r[1] != "DISCRIMINA"]
print("=== RESUMEN: %d/%d correcciones discriminan ==="
      % (len(filas) - len(malas), len(filas)))
for correccion, estado, det in malas:
    print("  NO DISCRIMINA: %s (%s)" % (correccion, det))
if malas:
    print()
    print("Un test que sigue pasando con la correccion destruida DECLARA que")
    print("la correccion esta, sin verificarla. Eso no cumple el criterio 2.")
    sys.exit(1)
print("Las 7 correcciones v3 estan VERIFICADAS por mutacion: se rompio cada")
print("una y el suite correspondiente la detecto.")
sys.exit(0)