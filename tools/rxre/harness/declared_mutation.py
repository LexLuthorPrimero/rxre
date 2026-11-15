#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY_OVER_TREE · WRITE_EXECUTION=SCRATCH_ONLY (/tmp)
"""RXRE · declared_mutation · arnés genérico de mutaciones DECLARADAS.

POR QUÉ EXISTE
--------------
Remake unificado de `mutate.py` (2026-09-20) y `mutscore.py` (mismas fechas),
adapado a cualquier árbol de RXRE. La clase de fallo que cierra es la misma:

    una leyenda no puede distinguir "test en verde" de "test que no puede
    llegar a rojo" sin introducir el bug que el test dice cazar.

LO QUE *NO* ES
--------------
NO ES un mutation score. Un mutation score muta todo el fichero y publica un
porcentaje, cuyo significado depende de la elección de N. Aquí NO hay N: cada
mutación está DECLARADA de antemano, con su objetivo, con su cambio literal de
texto, y con lo que se espera que pase. Un total sobre un conjunto declarado
no es un índice; es una lista de comprobaciones con nombre.

ENTRADA
-------
Un manifiesto JSON: lista de entradas.

    [{"nombre": "b7_knowledge_9_a_8",
      "ruta": "backends/decision.json",
      "buscar": "\\"knowledge\\": 9",
      "cambio": "\\"knowledge\\": 8",
      "esperado": "CAER",
      "probe": ["python3", "herramientas/vector_b7.py"],
      "nota": "el B7 compara declarado vs real; tras la mutación deben divergir"}]

- `ruta` es SIEMPRE relativa a la raíz dada con `--raiz`.
- `buscar` es un literal exacto (no regex). No aparece contenido sin mutar.
- `probe` se ejecuta con cwd=workdir, donde `workdir` contiene la copia
  mutada en la misma disposición de rutas que la raíz original.
  El probe FALLA => ejerció la mutación. `{workdir}` se sustituye en los args.
- `esperado`: "CAER" (el probe DEBE fallar tras la mutación) o
  "VIVIR" (el probe NO debe notarlo: se mide a sabiendas que sobrevive).

SALIDA
------
Para cada entrada:
    DETECTADA   la mutación cayó y la esperábamos (esperado=CAER) → OK
    SOBREVIVE   la mutación sobrevivió y la esperábamos (esperado=VIVIR) → OK
    PUNTO CIEGO esperado=CAER y sobrevivió → un agujero con nombre (fallo)
    SORPRESA    esperado=VIVIR y cayó → informativo, se avisa
    ERROR       el probe no pudo ejecutarse (fallo, no se cuenta)

Código de salida: 0 sin puntuaciones ciegas ni errores; 1 si hay al menos
una; 2 uso erróneo; 3 la mutación no es aplicable (buscar no aparece).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

VERSION = "1.0.0"


def aplicar_mutacion(raiz: str, entrada: dict, workdir: str) -> str:
    """Copia la raíz y sustituye UN literal. Devuelve la ruta mutada."""
    ruta = entrada["ruta"]
    src = os.path.join(raiz, ruta)
    if not os.path.isfile(src):
        raise FileNotFoundError("ruta no encontrada en la raíz: %s" % ruta)
    buscar = entrada["buscar"]
    cambio = entrada["cambio"]
    texto = open(src, encoding="utf-8").read()
    if buscar not in texto:
        raise ValueError("buscar no aparece en %s" % ruta)
    shutil.copytree(raiz, workdir)
    dst = os.path.join(workdir, ruta)
    open(dst, "w", encoding="utf-8").write(texto.replace(buscar, cambio, 1))
    return dst


def ejecutar_entrada(raiz: str, entrada: dict, tmp_root: str) -> dict:
    """Aplica una mutación y corre un probe. NUNCA toca la raíz."""
    nombre = entrada.get("nombre", "?")
    # reservar nombre único y dejar la ruta libre para copytree
    holder = tempfile.mkdtemp(prefix="rxre_mut_%s_" % nombre, dir=tmp_root)
    os.rmdir(holder)
    workdir = holder
    try:
        try:
            aplicar_mutacion(raiz, entrada, workdir)
        except (ValueError, FileNotFoundError) as exc:
            return {"nombre": nombre, "resultado": "ERROR", "motivo": str(exc)}
        cmd = [a.replace("{workdir}", workdir) for a in entrada["probe"]]
        try:
            p = subprocess.run(cmd, cwd=workdir, capture_output=True,
                               timeout=entrada.get("timeout", 300))
        except Exception as exc:
            return {"nombre": nombre, "resultado": "ERROR",
                    "motivo": "probe no ejecutable: %s" % exc}
        probe_fallo = p.returncode != 0
        esperado = entrada.get("esperado", "CAER")
        if esperado == "CAER":
            if probe_fallo:
                res, ok = "DETECTADA", True
            else:
                res, ok = "SOBREVIVE", False
        elif esperado == "VIVIR":
            if probe_fallo:
                res, ok = "DETECTADA", None  # sorpresa declarada
            else:
                res, ok = "SOBREVIVE", True
        else:
            return {"nombre": nombre, "resultado": "ERROR",
                    "motivo": "esperado desconocido: %r" % esperado}
        return {"nombre": nombre, "resultado": res,
                "esperado": esperado, "probe_returncode": p.returncode,
                "esperado_cumplido": ok,
                "nota": entrada.get("nota", ""),
                "stderr_cola": (p.stderr or b"").decode("utf-8", "replace")[-300:]}
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def cargar_manifiesto(path: str):
    man = json.load(open(path, encoding="utf-8"))
    if isinstance(man, dict):
        man = man.get("mutaciones", [])
    if not isinstance(man, list):
        raise ValueError("el manifiesto debe ser una lista o {'mutaciones': [...]}")
    return man


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("manifiesto", help="JSON con la lista de mutaciones declaradas")
    ap.add_argument("--raiz", required=True, help="raíz del árbol a mutar (COPIA)")
    ap.add_argument("--tmp", default=tempfile.gettempdir(),
                    help="directorio scratch (por defecto /tmp)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if not os.path.isdir(args.raiz):
        print("raíz inexistente: %s" % args.raiz)
        return 2
    try:
        man = cargar_manifiesto(args.manifiesto)
    except Exception as exc:
        print("manifiesto inválido: %s" % exc)
        return 2
    filas = [ejecutar_entrada(args.raiz, e, args.tmp) for e in man]
    if args.json:
        print(json.dumps(filas, indent=2, ensure_ascii=False))
    else:
        for f in filas:
            print("%-28s %-11s esperado=%-5s rc=%s %s" % (
                f["nombre"], f["resultado"], f.get("esperado", "-"),
                f.get("probe_returncode", "-"),
                ("PUNTO CIEGO" if f.get("esperado_cumplido") is False
                 else f.get("nota", ""))))
    ciegos = [f for f in filas if f.get("esperado_cumplido") is False]
    errores = [f for f in filas if f["resultado"] == "ERROR"]
    print("%d mutaciones: %d ciegas, %d errores" %
          (len(filas), len(ciegos), len(errores)))
    return 1 if (ciegos or errores) else 0


if __name__ == "__main__":
    sys.exit(main())
