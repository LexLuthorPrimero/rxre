#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE (salvo con --congelar: linea_base.json)
"""RXRE · dry_drift · una puerta de deriva sobre el mundo MEDIDO de RXRE.

POR QUÉ EXISTE
--------------
Remake honesto de `verif.py` de 2026-09-20. La herramienta original medía un
corpus de findings que ya no existe (fue borrado del repo por la auditoría del
2026-10-12). Lo que sobrevivió no fue el código sino la IDÉA, que sigue siendo
sólida: las fotos envejecen, las listas de medidas nombradas no, si llevan
declarada qué se espera de ellas.

El defecto que cierra aquí es el mismo de siempre: medir RXRE contra una linea
base sin declarar si se espera que se mueva, y llamar «verde» al silencio.

QUÉ MIDE
--------
El mundo que RXRE mismo produce y declara: el registro medido de backends
(`registry.recuento_real()`), los adapters activos (`dispatch.ADAPTERS`), y dos
fijos de contrato (los estados con producer y el ``primary`` declarado en
`decision.json`). Ninguna medida es sobre binarios o GPU: es sobre RXRE.

CLASES DE ESPERADA
------------------
ESTABLE     el contrato no debería cambiar. Si lo hace, falla.
DRIFTABLE   se mueve cuando el mundo cambia. Se informa; no falla.
VACIA       debería estar vacía. Si no lo está, saltó un hallazgo nuevo.
CONOCIDA    conocida no-vacía; FALLA si CRECE (aire del lobo).

SALIDAS
-------
0  sin hallazgos. DRIFTABLE puede haber cambiado sin ser visto.
1  ESTABLE cambió respecto a la línea base.
2  VACIA se llenó (hay algo donde debería no haber nada).
3  CONOCIDA creció.
4  DRIFTABLE cambió: revise y, si el cambio fue INTENCIONAL, haga `--congelar`.
5  línea base ausente o corrupta: haga `--congelar` primero.

NUNCA toca el árbol fuera de `linea_base.json`, y solo con `--congelar`.
"""
import argparse
import json
import os
import sys

VERSION = "1.0.0"
AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQUI)  # paquete tools/rxre
LINEA_BASE = os.path.join(AQUI, "linea_base.json")

CLASES = ("ESTABLE", "DRIFTABLE", "VACIA", "CONOCIDA")


def _json_sorted_keys(d):
    return json.dumps(d, sort_keys=True, separators=(",", ":"))


def medidas(rxre_root: str):
    """Mide RXRE sobre sí mismo. Determinista y sin GPU."""
    base = rxre_root or ROOT
    if base not in sys.path:
        sys.path.insert(0, base)
    from backends import dispatch, registry

    dec_path = os.path.join(base, "backends", "decision.json")
    try:
        decision = json.load(open(dec_path, encoding="utf-8"))
    except Exception as exc:
        decision = {"_error": "no se pudo leer decision.json: %s" % exc}

    out = {
        # DRIFTABLE: cambia cuando se añade/retira un backend o capacidad
        "registro.backends": ("DRIFTABLE", sorted(registry.backends())),
        "registro.n_backends": ("DRIFTABLE", [len(registry.backends())]),
        "registro.recuento_real": ("DRIFTABLE",
                                   [_json_sorted_keys(registry.recuento_real())]),
        "dispatch.adapters_activos": ("DRIFTABLE",
                                      sorted(k for k, a in dispatch.ADAPTERS.items() if a)),
        # ESTABLE: contrato interno, no debería cambiar sin dictado del dueño
        "registro.estados_con_producer": ("ESTABLE",
                                          sorted(registry.ESTADOS_CON_PRODUCER)),
        "decision.primary": ("ESTABLE", [str(decision.get("primary", "?"))]),
        # VACIA: invariante de que angr sigue siendo NOT_DETERMINED, nunca ausente
        "registro.backends_not_determined": ("VACIA", sorted(
            b["backend_id"] for b in registry.NO_VERIFICABLES
            if b["estado"] != "NOT_DETERMINED")),
        # CONOCIDA: backlog conocido (angr, alive2...). Crece => fallo.
        "registro.not_verificables": ("CONOCIDA", sorted(
            b["backend_id"] for b in registry.NO_VERIFICABLES)),
    }
    return out


def evaluar(actual: dict, base: dict):
    """Compara medición vs línea base. Devuelve (hallazgos, infos, diffs)."""
    errores, avisos, diffs = [], [], []
    for nombre, (clase, valores) in sorted(actual.items()):
        b = base.get(nombre)
        if b is None:
            avisos.append(("sin línea base", nombre))
            continue
        antes = set(b.get("valores", []))
        ahora = set(valores)
        if valores != b.get("valores"):
            delta_mas = sorted(ahora - antes)
            delta_menos = sorted(antes - ahora)
            diffs.append((nombre, clase, delta_mas, delta_menos))
            if clase == "ESTABLE":
                errores.append("ESTABLE cambió: %s (+%s -%s)" %
                               (nombre, delta_mas, delta_menos))
            elif clase == "VACIA" and ahora:
                errores.append("VACIA se llenó: %s -> %s" % (nombre, delta_mas))
            elif clase == "CONOCIDA" and delta_mas:
                errores.append("CONOCIDA creció: %s -> %s" % (nombre, delta_mas))
            # DRIFTABLE: se informa, no falla
    faltan = sorted(set(base) - set(actual))
    if faltan:
        avisos.append(("medida declarada en base, no medida", faltan))
    return errores, avisos, diffs


def cmd_congelar(rxre_root: str) -> int:
    med = medidas(rxre_root)
    base = {}
    for nombre, (clase, valores) in med.items():
        base[nombre] = {"clase": clase, "valores": valores}
    with open(LINEA_BASE, "w", encoding="utf-8") as f:
        json.dump({"_version": VERSION, "medidas": base}, f, indent=2,
                  ensure_ascii=False)
        f.write("\n")
    print("línea base congelada en %s (%d medidas)" % (LINEA_BASE, len(base)))
    return 0


def cmd_verificar(rxre_root: str, como_json: bool) -> int:
    if not os.path.isfile(LINEA_BASE):
        print("línea base ausente: %s (use --congelar primero)" % LINEA_BASE)
        return 5
    try:
        base_raw = json.load(open(LINEA_BASE, encoding="utf-8"))
        base = base_raw["medidas"]
    except Exception as exc:
        print("línea base corrupta: %s" % exc)
        return 5
    actual = medidas(rxre_root)
    errores, avisos, diffs = evaluar(actual, base)
    if como_json:
        print(json.dumps({"errores": errores,
                          "diffs": [(n, c, m, me) for n, c, m, me in diffs],
                          "avisos": avisos},
                         ensure_ascii=False, indent=2))
    else:
        for n, c, dmas, dmenos in diffs:
            print("%-42s %-10s +%s -%s" % (n, c, dmas or "", dmenos or ""))
        for a in avisos:
            print("AVISO: %s %s" % a)
    if errores:
        for e in errores:
            print("FALLO: %s" % e)
        return next(3 if "CONOCIDA creció" in e else
                    2 if "VACIA se llenó" in e else 1 for e in errores)
    if diffs:
        print("DRIFTABLE cambió; si el cambio es intencional: --congelar")
        return 4
    print("sin deriva frente a la línea base")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--congelar", action="store_true",
                    help="escribir/actualizar linea_base.json con la medición actual")
    ap.add_argument("--json", action="store_true",
                    help="informe en JSON (--verificar)")
    ap.add_argument("--rxre", default=None,
                    help="raíz del paquete de RXRE (por defecto: la propia)")
    args = ap.parse_args()
    if args.congelar:
        return cmd_congelar(args.rxre)
    return cmd_verificar(args.rxre, args.json)


if __name__ == "__main__":
    sys.exit(main())
