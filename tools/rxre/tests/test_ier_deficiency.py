#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""IER-104 · deficiencia — 5 alternativas, evidencia exigida, J publicado.

El evaluador no optimiza hasta la promoción: dada evidencia de la tecnología,
propone la alternativa; la decisión final exige tu dictado.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)

from ier import deficiency  # noqa: E402

_fallos = []


def v(nombre, cond, info=""):
    if cond:
        print("  PASS %-46s" % nombre)
    else:
        print("  FAIL %-46s %s" % (nombre, info))
        _fallos.append(nombre)


# Q(T,G)=1 → reparar (la tecnología sirve)
r = deficiency.evaluar({"t_alcanza_el_objetivo": 1, "total_defecto": True})
v("Q=1 con defecto -> reparar", r["decision"] == "reparar")

# Falta subconjunto → extender
r = deficiency.evaluar({"t_alcanza_el_objetivo": 0, "falta_subconjunto": True})
v("falta subconjunto -> extender", r["decision"] == "extender")

# Sustituible → sustituir
r = deficiency.evaluar({"t_alcanza_el_objetivo": 0, "sustituible": True})
v("sustituible -> sustituir", r["decision"] == "sustituir")

# Combinable y nada_sirve=false → combinar
r = deficiency.evaluar({"t_alcanza_el_objetivo": 0, "combinable": True,
                        "nada_sirve": False})
v("combinable -> combinar", r["decision"] == "combinar")

# Nada sirve → crear
r = deficiency.evaluar({"t_alcanza_el_objetivo": 0, "nada_sirve": True})
v("nada sirve -> crear", r["decision"] == "crear")

# Sin flags → NOT_DETERMINED
r = deficiency.evaluar({"t_alcanza_el_objetivo": 0})
v("sin evidencia -> NOT_DETERMINED", r["decision"] == "NOT_DETERMINED")

# pesos publicados por defecto
pesos = deficiency.DEFAULT_PESOS
v("pesos por defecto sumados = 1.0",
  round(sum(pesos.values()), 6) == 1.0)

# publish sin dictado no engaña sobre el origen
tmpdir = tempfile.mkdtemp(prefix="ier_pub_")
doc = deficiency.publicar_pesos(os.path.join(tmpdir, "pesos.json"))
v("publicar pesos como default", doc["origen"] == "DEFAULT_NO_OPTIMIZADOS")

# publish con dictado declarado
doc2 = deficiency.publicar_pesos(os.path.join(tmpdir, "dict.json"),
                                 pesos={"C": 0.1, "R": 0.6, "T": 0.1, "M": 0.2})
v("publicar pesos dictados etiqueta=dictado", doc2["origen"] == "dictado del propietario")

print()
if _fallos:
    print("IER deficiency FALLA:", _fallos)
    sys.exit(1)
print("IER deficiency OK")
sys.exit(0)
