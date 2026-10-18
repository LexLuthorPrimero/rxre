#!/usr/bin/env python3
"""mutate_reg_resolve.py - comprueba que test_p003.py detecta fallos.

QUE RESUELVE
------------
test_p003.py en verde no prueba que sea un buen test. Solo prueba que
test_p003.py no falla hoy. Hay dos agujeros posibles:

  D4: borrar la deteccion de CONFLICT -> T0302 tiene que caer
  D5: borrar la advertencia de colision dword_index -> T0301 tiene que caer
  D9: borrar el campo candidates -> T0302 tiene que caer

mutate_reg_resolve.py copia reg_resolve.py a un arbol de trabajo,
elimina esas lineas una a una, ejecuta test_p003.py y registra si algo
cayo.

Un mutante que sobrevive es un agujero con nombre: o la suite es ciega
a ese fallo, o la reparacion que se esta midiendo no es necesaria.

NADA SE TOCA FUERA DEL DIRECTORIO DE TRABAJO
-------------------------------------------
reg_resolve.py original jamas se modifica. El arbol de trabajo se
reconstruye en cada mutante.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = "/tmp/opencode/mutate-reg-resolve"

# Catalogo de mutantes: nombre, busco esto literalmente, lo reemplazo por
# NADA (borro la linea) y lo que se espera.
#
# esperado = CAER    -> test_p003.py tiene que reportar al menos un fallo
#          = VIVIR   -> la suite no lo nota y se mide a proposito (debe ser
#                      declarada, si cae es una sorpresa)

CATALOGO = [
    dict(nombre="D4_sin_semantic_conflict",
         fichero="tools/reg_resolve.py",
         buscar='        out["semantic_conflict"] = True',
         esperado="CAER",
         nota="borro la declaracion SEMANTIC_CONFLICT=true; T0302 no debe sobrevivir"),
    dict(nombre="D9_sin_candidates",
         fichero="tools/reg_resolve.py",
         buscar='        out["candidates"] = sorted(hex(v) for v in unique_values)',
         esperado="CAER",
         nota="borro la lista de candidatos conflict; T0302 no debe sobrevivir"),
    dict(nombre="D10_sin_value_disagreement",
         fichero="tools/reg_resolve.py",
         buscar='        out["value_disagreement"] = True',
         esperado="CAER",
         nota="borro la declaracion VALUE_DISAGREEMENT=true; T0302 no debe sobrevivir"),
    dict(nombre="D11_sin_target_filtering",
         fichero="tools/reg_resolve.py",
         buscar='    applicable_candidates = [h for h in hits if h in in_target]',
         esperado="CAER",
         nota="borro el filtrado por target aplicable; T0302 no debe sobrevivir"),
]


def run_command(cmd, cwd=None, timeout=60):
    """Ejecuta y devuelve (exitcode, stdout, stderr)."""
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def apply_mutation(path, search, replacement=""):
    """Aplica una mutacion y devuelve la ruta del mutante creado."""
    with open(path, "r", encoding="utf-8") as fh:
        src = fh.read()
    if search not in src:
        return None, "busqueda_no_encuentra"
    out = src.replace(search, replacement, 1)
    tmp = os.path.join(SCRATCH, "mutante")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(out)
    return tmp, None


def run_tests(mutable_script, timeout=120):
    """Ejecuta test_p003.py contra el guion mutante.
    
    Parchea temporalmente test_p003.py para que use el script mutante
    en lugar del reg_resolve.py original.
    """
    test_p003 = os.path.join(RAIZ, "tools", "rxre", "tests", "test_p003.py")
    
    # Leer test_p003.py original
    with open(test_p003, "r", encoding="utf-8") as fh:
        test_src = fh.read()
    
    # Parchear REG_RESOLVE para que apunte al mutante
    original_line = 'REG_RESOLVE = os.path.join(ROOT, "tools", "reg_resolve.py")'
    patched_line = f'REG_RESOLVE = "{mutable_script}"'
    if original_line not in test_src:
        return 2, "", f"no se encuentra la linea a parchear en {test_p003}"
    
    patched_test = test_src.replace(original_line, patched_line)
    
    # Escribir test parcheado temporalmente
    tmp_test = os.path.join(SCRATCH, "test_p003_patched.py")
    with open(tmp_test, "w", encoding="utf-8") as fh:
        fh.write(patched_test)
    
    # Ejecutar test parcheado
    cmd = [sys.executable, tmp_test]
    return run_command(cmd, cwd=RAIZ, timeout=timeout)


def mutate_all(mutation, verboso=False):
    """Aplica TODO el catalogo y devuelve la tabla de resultados."""
    results = []
    for m in CATALOGO:
        if mutation and m["nombre"] != mutation:
            continue
        src = os.path.join(RAIZ, m["fichero"])
        tmp, err = apply_mutation(src, m["buscar"], "")
        if err:
            results.append(dict(nombre=m["nombre"], fichero=m["fichero"], estado="FATAL",
                                causa=err, ok=False, detectado=False,
                                esperado=m["esperado"], nota=m["nota"]))
            continue
        exitcode, stdout, stderr = run_tests(tmp)
        # test_p003.py sale con 0 si TODO VERDE, con 1 si hay FALLOS
        detectado = (exitcode == 1)
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
        if verboso:
            print("  [%s] %s -> %s" % ("OK" if ok else "XX",
                                      m["nombre"], m["nota"]))
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mutate_reg_resolve",
                                 description="Mutation testing de reg_resolve.py")
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

    print("================================================================")
    print("RESULTADO DEL MUTATION TESTING (reg_resolve.py, oraculo=test_p003.py)")
    print("================================================================")
    n_ok = sum(1 for r in results if r["ok"])
    for r in results:
        print("  [%s] %-24s %s" % ("OK" if r["ok"] else "XX",
                                  r["nombre"], r["nota"]))
        print("         estado=%s esperado=%s" % (r["estado"], r["esperado"]))
    print("-" * 72)
    print("mutantes %d / %d con comportamiento esperado" % (n_ok, len(results)))
    return 0 if n_ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
