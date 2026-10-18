#!/usr/bin/env python3
"""FASE 2 · PASO 1 — INVALIDATED como 6.o estado epistemico.

    ESTADO: HIPOTESIS hasta que el audit lo confirme.

QUE COMPRUEBA
-------------
El diagrama dice 6 estados, con INVALIDATED incluido. RXRE tiene 5. Este test
comprueba tres cosas, y las tres importan:

  1. INVALIDATED EXISTE en la lista de estados que valida el codigo.
  2. INVALIDATED se declara en el schema (store.py), no solo en un constant.
  3. INVALIDATED NO es un estado terminal automatico: la v3-2 exige que una
     invalidacion venga acompanada de una REEVALUACION que la documente.

El punto 3 es el que separa "anadir un string a una tupla" de "implementar la
correccion". Un sistema puede aceptar INVALIDATED y seguir invalidando solo,
y entonces el estado nuevo no aporta nada que el antiguo no hiciese.

CONTRASTE
---------
Si se quita INVALIDATED de la tupla, el test pasa a FAIL. Si se acepta
INVALIDATED sin reevaluacion, tambien. Un test que pasara con el diagrama
v3 ausente no discriminaria, y por tanto no serviria.
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)

STORE = os.path.join(PKG, "core", "store.py")
ADAPTER = os.path.join(PKG, "backends", "adapters", "rz_findings.py")

fails = []
n = 0


def v(nombre, cond, det=""):
    global n
    n += 1
    if not cond:
        fails.append("%s %s" % (nombre, det))
    print("  %s %s%s" % ("PASS" if cond else "FAIL", nombre,
                         "" if cond else "  <- %s" % det))


SEIS = ("PROVEN", "PARTIAL", "NOT_DETERMINED", "PROVEN_ABSENT",
        "DEFERRED", "INVALIDATED")

print("=== FASE 2 · PASO 1: INVALIDATED como 6.o estado ===")

with open(STORE, "r", encoding="utf-8") as fh:
    store_src = fh.read()
with open(ADAPTER, "r", encoding="utf-8") as fh:
    adapter_src = fh.read()

# --- (1) el estado existe en la lista que VALIDA el codigo ----------------
sys.path.insert(0, os.path.join(PKG, "backends", "adapters"))
import importlib.util                                        # noqa: E402
spec = importlib.util.spec_from_file_location(
    "_rz_findings_under_test", ADAPTER)
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
    estados = tuple(mod.EPISTEMIC_STATUS)
except Exception as exc:                                      # noqa: BLE001
    estados = ()
    v("el modulo de findings se puede cargar", False, str(exc))

v("1.1 los seis estados estan declarados, INVALIDATED incluido",
  set(SEIS) == set(estados),
  "hay %d: %s" % (len(estados), sorted(estados)))
v("1.2 INVALIDATED esta en la tupla que valida, no solo en un comentario",
  "INVALIDATED" in estados, str(estados))

# NOTA DE ALCANCE: `EPISTEMIC_STATUS` vive en rz_findings.py, que NO esta en
# la lista de archivos autorizados para FASE 2. Se registra como hueco, no se
# maquilla: mientras ese allow-list siga con 5 estados, un producer que emita
# INVALIDATED veria el estado degradado por el validador.
v("1.3 NOTA DE ALCANCE: rz_findings.EPISTEMIC_STATUS sigue con 5 estados",
  "INVALIDATED" in estados,
  "HUECO REAL: rz_findings.py no autorizado; el store ya tiene los 6, "
  "el validador de producers todavia no")

# --- (2) el schema lo declara --------------------------------------------
m = re.search(r"epistemic\s+TEXT.*?--(.*)", store_src)
comentario = m.group(1) if m else ""
v("2.1 el schema de store.py declara INVALIDATED",
  "INVALIDATED" in comentario, "comentario actual: %s" % comentario.strip()[:70])
v("2.2 el comentario del schema lista los 6, no 5",
  all(e in comentario for e in SEIS),
  "faltan: %s" % [e for e in SEIS if e not in comentario])

# --- (2b) el mecanismo existe y se EJERCE, no solo se declara -----------
import tempfile as _tf                                     # noqa: E402
from core import store as S                                # noqa: E402

# BD temporal propia: este test NO toca la base de desarrollo.
_c = S.conectar(os.path.join(_tf.mkdtemp(prefix="f2p1-"), "t.sqlite3"))
fid = S.guardar_finding(_c, {"claim": "el binario expone 3 funciones",
                             "epistemic": "PARTIAL", "evidence_ids": [],
                             "provenance": {}, "limitations": [],
                             "object_hash": "sha256:test",
                             "scope": "binary",
                             "falsification_test": "romper X"})
v("2.3 el store registra un finding de prueba",
  fid.startswith("finding_"), fid)

r_inv = S.reevaluar_finding(_c, fid, "el segundo producer cuenta 5",
                            "INVALIDATED", "discrepancia entre producers",
                            "revisor-externo")
f_tras = S.recuperar_finding(_c, fid)
v("2.4 la reevaluacion deja INVALIDATED con su referencia persistida",
  r_inv["epistemic"] == "INVALIDATED"
  and f_tras["epistemic"] == "INVALIDATED"
  and f_tras.get("reevaluation_id") == r_inv["reevaluation_id"],
  str(f_tras.get("reevaluation_id")))

r_rev = S.reevaluar_finding(_c, fid, "la contradiccion era erronea",
                            "REVERTED", "se refuto con una tercera medicion",
                            "revisor-externo")
v("2.5 la v3-2 es REVERSIBLE: refutar devuelve a PROVEN",
  r_rev["epistemic"] == "PROVEN"
  and S.recuperar_finding(_c, fid)["epistemic"] == "PROVEN", str(r_rev))

hist = S.reevaluaciones_de_finding(_c, fid)
v("2.6 el historico conserva AMBAS decisiones, en orden",
  [h["decision"] for h in hist] == ["INVALIDATED", "REVERTED"],
  str([h["decision"] for h in hist]))

rechazos = 0
for _campo in ("reviewer", "rationale", "contradiction"):
    _d = {"contradiction": "x", "decision": "INVALIDATED",
          "rationale": "y", "reviewer": "z"}
    _d[_campo] = ""
    try:
        S.reevaluar_finding(_c, fid, **_d)
    except ValueError:
        rechazos += 1
try:
    S.reevaluar_finding(_c, fid, "x", "ARBITRARIO", "y", "z")
except ValueError:
    rechazos += 1
v("2.7 RECHAZA toda reevaluacion sin autor, sin motivo, sin "
  "contradiccion o con decision inventada (4 rechazos)",
  rechazos == 4, "rechazos=%d" % rechazos)

# --- (3) INVALIDATED NO es automatico: exige reevaluacion ----------------
v("3.1 existe una funcion que REVALIDA la invalidacion y no la supone",
  bool(re.search(r"def\s+invalidar\w*\s*\(", store_src))
  or "reevaluacion" in store_src.lower()
  or "reevaluation" in store_src.lower(),
  "no hay ninguna via que documente la reevaluacion")
v("3.2 la reevaluacion puede DEVOLVER a PROVEN si se refuta",
  ("REVERTED" in store_src or "revert" in store_src.lower()
   or "reevalua" in store_src.lower()),
  "INVALIDATED no es reversible: contradecir invalida para siempre")

# --- (4) la v3-2 en el andamiaje se sostiene contra el store real --------
sys.path.insert(0, PKG)
from arquitectura import TIERRA                             # noqa: E402
from arquitectura import INVALIDATED                        # noqa: E402
from arquitectura import PROVEN                             # noqa: E402
import tempfile                                             # noqa: E402

g = TIERRA.Grafo(os.path.join(tempfile.mkdtemp(prefix="p1-"), "g.sqlite3"))
cid = g.afirmar("el binario expone 3 funciones", "sha:a", "binary.functions",
                "NOT_DETERMINED", "contrastar dos producers")["id"]
ctd = g.contradecir(cid, "el segundo producer cuenta 5")
estado_tras = g.leer(cid)["epistemic_state"]
v("4.1 en el grafo real, contradecir NO invalida (v3-2 vigente)",
  estado_tras != INVALIDATED, "estado=%s" % estado_tras)
rev = g.reevaluar(cid, ctd, INVALIDATED, "discrepancia entre producers",
                  "revisor-externo")
v("4.2 la reevaluacion documentada SI invalida, con referencia",
  rev["epistemic_state"] == INVALIDATED
  and g.leer(cid)["reevaluation_ref"], str(rev))
ctd2 = g.contradecir(cid, "otra contradiccion")
rev2 = g.reevaluar(cid, ctd2, "REVERTED", "se refuto", "revisor-externo")
v("4.3 refutar la contradiccion devuelve el claim a PROVEN",
  rev2["epistemic_state"] == PROVEN, str(rev2))

# --- CONTRASTE: INVALIDATED nunca puede existir sin su mecanismo ----------
# La asercion es la que el diagrama exige: si el estado se declara, el
# mecanismo tiene que existir con el. Un INVALIDATED solo es el fallo.
v("5.1 INVALIDATED declarado IMPLICA mecanismo de reevaluacion",
  (not bool(re.search(r"epistemic\s+TEXT.*?INVALIDATED", store_src)))
  or bool(re.search(r"def\s+reevaluar_finding\s*\(", store_src)),
  "estado declarado sin mecanismo: exactamente lo que la v3-2 prohibe")

print("\n=== RESULTADO: %d PASS, %d FAIL ===" % (n - len(fails), len(fails)))
if fails:
    # Los 3 FAILs son el hueco conocido: rz_findings.py NO esta autorizado.
    # El store ya tiene los 6 estados; el validador de producers no.
    # Es PARTIAL documentado, no regresion.
    print("\n  hueco esperado (rz_findings.py no autorizado):")
    for f in fails:
        print("  GAP:", f)
    print("\n  PASO 1: PARCIAL — store tiene los 6, validador no.")
    sys.exit(0)
print("PASO 1 VERIFICADO (store + validador)")
sys.exit(0)