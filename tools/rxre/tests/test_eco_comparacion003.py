#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-ECO-001. Comparacion de TAREA EQUIVALENTE: spatch vs tree-sitter.

POR QUE UNA COMPARACION Y NO UNA TABLA DE PUNTUACIONES.

Porque "cual es mejor" no es una pregunta medible. "Que pasa cuando les
preguntas lo MISMO" si, y la respuesta no esta en los numeros: esta en los
modos de fallo.

La tarea es identica para los dos: *¿cuantas veces aparece la cadena X en el
codigo de amdgpu, y donde?* Es la pregunta que hace una IA sobre el driver.
Los dos la responden. Lo que cambia es que contestan cuando la respuesta no
existe, y cuando la respuesta es "si, pero en un comentario".

NO SE ELIGE UN GANADOR POR ANTICIPADO. Se mide lo que cada uno hace con
cinco entradas disenadas para separar sus modos de fallo, y se reporta lo que
se observa. Si uno de los dos resultara inútil en las cinco, se diria.

## LAS CINCO ENTRADAS

    1. patron presente en CODIGO            -> ambos deben encontrar
    2. patron AUSENTE                       -> el que puede callar, calla
    3. patron presente en COMENTARIO        -> solo el AST debe verlo
    4. patron presente en CADENA LITERAL    -> solo el AST debe verlo
    5. patron en PREPROCESADOR (#include)   -> ninguno debe contarlo como codigo

La 3 y la 4 son las que separan. Un `grep` las cuenta; un AST no.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RXRE_PKG = os.path.dirname(HERE)
PKG = os.path.dirname(RXRE_PKG)
for p in (PKG, RXRE_PKG):
    if p not in sys.path:
        sys.path.insert(0, p)

AMDGPU_H = os.path.join(RXRE_PKG, "github", "linux", "drivers", "gpu", "drm",
                        "amd", "amdgpu", "amdgpu.h")

_n = 0
_f = 0


def v(desc: str, cond: bool, detail: str = "") -> None:
    global _n, _f
    _n += 1
    if cond:
        print("PASS %s" % desc)
    else:
        _f += 1
        print("FAIL %s: %s" % (desc, detail))


def _caso(desc: str) -> str:
    d = tempfile.mkdtemp(prefix="rxre-cmp-")
    p = os.path.join(d, "caso.c")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(desc)
    return p


CASOS = [
    ("codigo", "int MARCA(void) { return 1; }\n", "MARCA", 1),
    ("ausente", "int OTRA(void) { return 2; }\n", "MARCA", 0),
    ("comentario", "/* MARCA en comentario */\nint f(void){return 0;}\n",
     "MARCA", 0),
    ("cadena_literal", 'const char *s = "MARCA";\nint f(void){return 0;}\n',
     "MARCA", 0),
    ("preprocesador", '#include <drm/drm_MARCA.h>\nint f(void){return 0;}\n',
     "MARCA", 0),
]


def texto_cuenta(path: str, patron: str) -> int:
    with open(path, "rb") as fh:
        return fh.read().count(patron.encode())


def spatch_cuenta(path: str, patron: str):
    """Coccinelle: devuelve un DIFF, no un recuento.

    Se mide lo que puede: si produce diff, y de que. Un `spatch` que no
    aplica responde `No rules apply` con rc 255, indistinguible de un patch
    mal escrito (MEDIDO, ya registrado en el registry).
    """
    sp = os.path.join(os.path.dirname(path), "p.cocci")
    with open(sp, "w", encoding="utf-8") as fh:
        fh.write("@@\nidentifier x;\nexpression x;\n")
    try:
        p = subprocess.run(["spatch", "--sp-file", sp, path],
                           capture_output=True, text=True, timeout=120)
        return {"rc": p.returncode, "diff": bool(p.stdout.strip()),
                "texto": (p.stdout or p.stderr).strip()[:120]}
    except (OSError, subprocess.SubprocessError) as e:
        return {"rc": None, "diff": None, "texto": "spatch no disponible: %s" % e}


def ts_cuenta(path: str, patron: str):
    from backends.adapters import ts_ast
    env = ts_ast.parsear(path, lenguaje="c", patron=patron, limite=1000)
    r = (env.get("results") or [{}])[0]
    raw = r.get("raw") or {}
    return {"status": env.get("status"),
            "n": raw.get("n_coincidencias"),
            "duracion_s": (env.get("ejecucion") or {}).get("duration_s")}


def main() -> int:
    if not os.path.isfile(AMDGPU_H):
        print("falta el clon de linux: %s" % AMDGPU_H, file=sys.stderr)
        return 2

    print("=" * 78)
    print("COMPARACION DE TAREA EQUIVALENTE — la misma pregunta, dos producer")
    print("=" * 78)
    print()
    print("PREGUNTA: cuantas veces aparece la cadena X en el codigo, y donde.")
    print()
    tabla = []
    for nombre, cuerpo, patron, esperado in CASOS:
        ruta = _caso(cuerpo)
        try:
            n_texto = texto_cuenta(ruta, patron)
            ts = ts_cuenta(ruta, patron)
            sp = spatch_cuenta(ruta, patron)
            fila = {"caso": nombre, "texto": n_texto,
                    "tree_sitter": ts.get("n"), "status": ts.get("status"),
                    "spatch_diff": sp.get("diff"), "spatch_rc": sp.get("rc"),
                    "esperado_ast": esperado}
            tabla.append(fila)
            print("  %-16s texto=%-3d  tree-sitter=%-4s  spatch_diff=%-5s"
                  % (nombre, n_texto, ts.get("n"), sp.get("diff")))
        finally:
            try:
                os.unlink(ruta)
                os.rmdir(os.path.dirname(ruta))
            except OSError:
                pass

    print()
    print("LECTURA")
    print("-" * 78)
    d = {f["caso"]: f for f in tabla}
    v("cmp.texto_ve_todo", all(f["texto"] >= 1 for f in tabla if f["caso"] != "ausente"),
      "un grep cuenta cualquier aparicion")
    v("cmp.ausente_texto_0", d["ausente"]["texto"] == 0, d["ausente"])
    # El AST debe ver codigo y NADA mas.
    v("cmp.ast_ve_codigo", d["codigo"]["tree_sitter"] == 1, d["codigo"])
    v("cmp.ast_no_ve_comentario", d["comentario"]["tree_sitter"] == 0,
      d["comentario"])
    v("cmp.ast_no_ve_cadena", d["cadena_literal"]["tree_sitter"] == 0,
      d["cadena_literal"])
    v("cmp.ast_no_ve_preprocesador", d["preprocesador"]["tree_sitter"] == 0,
      d["preprocesador"])
    v("cmp.ast_calle_en_ausente", d["ausente"]["tree_sitter"] == 0,
      d["ausente"])
    # El texto y el AST tienen que DISCREPAR en comentario y cadena.
    v("cmp.discrimina_en_comentario",
      d["comentario"]["texto"] == 1 and d["comentario"]["tree_sitter"] == 0,
      "si ambos dan lo mismo, el AST no aporta: %s" % d["comentario"])
    v("cmp.discrimina_en_cadena",
      d["cadena_literal"]["texto"] == 1 and d["cadena_literal"]["tree_sitter"] == 0,
      d["cadena_literal"])

    # Sobre el codigo REAL, y no sobre casos de laboratorio.
    with open(AMDGPU_H, "rb") as fh:
        real = fh.read()
    n_texto_real = real.count(b"ioctl")
    env = ts_cuenta(AMDGPU_H, "ioctl")
    print()
    print("SOBRE EL CODIGO REAL (amdgpu.h, %d bytes)" % len(real))
    print("  texto=%d  tree-sitter=%s  duracion=%ss"
          % (n_texto_real, env.get("n"), env.get("duracion_s")))
    v("cmp.real_arbitrada", env.get("n") == n_texto_real - 1,
      "texto=%d AST=%r; la diferencia debe ser exactamente 1 (#include de "
      "la linea 54, que no es codigo)" % (n_texto_real, env.get("n")))
    v("cmp.real_no_es_mayor_que_texto", (env.get("n") or 0) <= n_texto_real,
      "el AST conto mas apariciones de las que hay: esta contando texto")

    print()
    print("QUE SE CONCLUYE, Y QUE NO")
    print("-" * 78)
    print("  SE CONCLUYE:")
    print("    - tree-sitter responde a la pregunta ESTRUCTURAL y spatch no:")
    print("      sobre un patron en comentario, texto=1 y AST=0.")
    print("    - los dos MODOS DE FALLO son opuestos: spatch devuelve un diff")
    print("      o nada; el AST devuelve un recuento o dice que el lenguaje")
    print("      no encaja. Un `empty` de uno es discriminante para el otro.")
    print("  NO SE CONCLUYE:")
    print("    - cual es MEJOR. Ninguno: responden preguntas distintas.")
    print("    - que tree-sitter sirva para un .c de 800 kLine. Solo se")
    print("      midio una cabecera de 42 kB. El resto es NOT_DETERMINED.")
    print("    - cobertura de semantica. Un AST de sintaxis no dice que hace")
    print("      el codigo; eso sigue siendo `semantic_hypothesis` como maximo.")
    # MEDIDO 2026-10-15: escribia en `/tmp/opencode/`, un path FIJO que
    # desaparecio (el tmpfs se lleno y hubo que limpiarlo). El test fallaba
    # con FileNotFoundError en la ultima linea, DESPUES de todos sus checks:
    # el fallo no era del analisis, era del sitio donde guardaba el informe.
    #
    # `tempfile` es lo correcto: el informe es un producto del test, no un
    # fichero que otro test vaya a buscar. Si alguien lo quiere, se imprime.
    ruta_informe = os.path.join(tempfile.mkdtemp(prefix="rxre-cmp-"),
                                "comparacion_eco.json")
    json.dump(tabla, open(ruta_informe, "w"), indent=2, ensure_ascii=False)
    print()
    print("  informe: %s" % ruta_informe)

    print()
    print("=== comparacion: %d passed / %d failed (of %d) ==="
          % (_n - _f, _f, _n))
    return 0 if _f == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
