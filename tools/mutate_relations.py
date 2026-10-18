#!/usr/bin/env python3
"""mutate_relations.py - comprueba que test_p005.py detecta fallos.

Mutation testing para core/relations.py. Prueba que las mutaciones
críticas sobre el motor de relaciones causales son detectadas por
T0501-T0508.

Si un mutante sobrevive, significa que la suite es ciega a ese fallo.
"""

import argparse
import os
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = "/tmp/opencode/mutate-relations"

# Catalogo de mutantes: nombre, busco esto literalmente en relations.py,
# lo reemplazo por NADA o por algo distinto, y lo que se espera.
#
# esperado = CAER    -> test_p005.py tiene que reportar al menos un fallo
#          = VIVIR   -> la suite no lo nota (agujero)

CATALOGO = [
    dict(nombre="R1_sin_evidence_check",
         fichero="tools/rxre/core/relations.py",
         buscar='            evid = json.loads(row[1] or "[]")\n            if not evid:\n                return False  # No se permite PROVEN automático sin evidencia',
         reemplazo='            pass  # mutacion: check de evidencia removido',
         esperado="CAER",
         nota="borro la validacion de evidencia en actualizar_estado; PROVEN sin evidencia no debe permitirse"),
    dict(nombre="R2_corrupt_evidence_json",
         fichero="tools/rxre/core/relations.py",
         buscar='            evid = json.loads(row[1] or "[]")',
         reemplazo='            evid = json.loads(row[1] or "INVALID")',
         esperado="CAER",
         nota="corrompo evidence_json parseo; la validacion puede fallar distinto"),
    dict(nombre="R3_evidencia_vacia_aceptada",
         fichero="tools/rxre/core/relations.py",
         buscar='            if not evid:',
         reemplazo='            if False:  # mutacion: siempre pasa el check',
         esperado="CAER",
         nota="elimino check de evidencia vacia; PROVEN sin evidencia quedaria permitido"),
    dict(nombre="R4_estado_invalido",
         fichero="tools/rxre/core/relations.py",
         buscar='    if nuevo_estado not in RELACION_ESTADOS:',
         reemplazo='    if nuevo_estado not in ("PROVEN",):  # mutacion: solo acepta PROVEN',
         esperado="CAER",
         nota="rechazo todos los estados excepto PROVEN; tests fallan por estados invalidos"),
]


def apply_mutation(path, search, replacement=""):
    """Aplica una mutacion y devuelve la ruta del mutante creado."""
    with open(path, "r", encoding="utf-8") as fh:
        src = fh.read()
    if search not in src:
        return None, "busqueda_no_encuentra"
    out = src.replace(search, replacement, 1)
    tmp = os.path.join(SCRATCH, "mutante_relations.py")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(out)
    return tmp, None


def run_tests(mutable_script, timeout=120):
    """Ejecuta test_p005.py contra el guion mutante."""
    cmd = [sys.executable, mutable_script]
    return run_command(cmd, timeout=timeout)


def run_command(cmd, cwd=None, timeout=120):
    """Ejecuta y devuelve (exitcode, stdout, stderr)."""
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    return p.returncode, p.stdout, p.stderr


def run_tests_with_path(mutable_script, cwd=None, timeout=120):
    """Ejecuta test_p005.py con PYTHONPATH configurado."""
    cmd = [sys.executable, "-c",
           f"import sys; sys.path.insert(0, '/home/lucas/Escritorio/rxre/tools/rxre'); "
           f"import tests.test_p005; "
           f"tests.test_p005.main()"]
    return run_command(cmd, cwd=cwd, timeout=timeout)


def mutate_all(mutation=None, json_output=False):
    """Aplica TODO el catalogo y devuelve la tabla de resultados."""
    results = []
    for m in CATALOGO:
        if mutation and m["nombre"] != mutation:
            continue
        src = os.path.join(RAIZ, m["fichero"])
        tmp, err = apply_mutation(src, m["buscar"], m["reemplazo"])
        if err:
            results.append(dict(nombre=m["nombre"], estado="FATAL",
                                causa=err))
            continue
        exitcode, stdout, stderr = run_tests_with_path(tmp)
        # test_p005.py sale con 0 si TODO VERDE, con 1 si hay FALLOS
        # FALLOS = test detecto la mutacion (bueno)
        detectado = (exitcode == 1)  # FALLAS en la suite = mutante detectado
        vivo = not detectado
        esperado_cae = (m["esperado"] == "CAER")
        if esperado_cae and vivo:
            status = "MUTANTE SOBREVIVE (agujero)"
            ok = False
        elif esperado_cae and detectado:
            status = "detectado"
            ok = True
        elif not esperado_cae and detectado:
            status = "Sorpresa: la suite noto algo no esperado"
            ok = False
        else:
            status = "sobrevive (medido)"
            ok = True
        results.append(dict(nombre=m["nombre"],
                            fichero=m["fichero"],
                            esperado=m["esperado"],
                            estado=status,
                            detectado=detectado,
                            ok=ok,
                            nota=m["nota"]))
        print("  [%s] %-30s -> %s" % ("OK" if ok else "XX",
                                     m["nombre"], m["nota"]))
        print("         estado=%s esperado=%s detectado=%s" % (
              status, m["esperado"], detectado))
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mutate_relations",
                                 description="Mutation testing de relations.py")
    ap.add_argument("--list", action="store_true",
                    help="muestra el catalogo de mutantes")
    ap.add_argument("--run", metavar="NOMBRE",
                    help="corre un solo mutante")
    ap.add_argument("--all", action="store_true", default=True,
                    help="todos, con tabla resumen")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    shutil.rmtree(SCRATCH, ignore_errors=True)
    os.makedirs(SCRATCH, exist_ok=True)

    if args.list:
        print("Mutantes registrados:")
        for m in CATALOGO:
            print("  %s  %s\n      %s" % (m["nombre"], m["esperado"], m["nota"]))
        return 0

    results = mutate_all(args.run, args.json)

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    n_ok = sum(1 for r in results if r["ok"])
    print("-" * 72)
    print("mutantes %d / %d con comportamiento esperado" % (n_ok, len(results)))
    return 0 if n_ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())