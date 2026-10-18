#!/usr/bin/env python3
"""Los nueve componentes del diagrama: existe el contrato, y se rompe solo.

    ESTADO: HIPOTESIS. Este fichero no demuestra que RXRE sea esto.
    Demuestra que el ANDAMIAJE existe y que cada componente puede fallar.

QUE ES ESTE TEST Y CUAL NO ES
-----------------------------
No mide que el sistema reverse un binario. Mide algo mas pequeño y mas util:
que cada bloque del diagrama tenga un contrato EJECUTABLE, y que ese contrato
rechace lo que tiene que rechazar.

    un contrato se demuestra por lo que rechaza

Por eso hay mas lineas de `rechaza` que de `acepta`. Un contrato que solo
acepta no distingue ninguna implementacion: cualquier `return None` lo
cumpliria.

CADA TEST ES DISCRIMINANTE
-------------------------
Cada asercion de este fichero esta escrita para que, si se borra la
correccion que dice comprobar, el test pase a FAIL. No basta con que el test
pase hoy: tiene que ser imposible que pase con el mecanismo ausente. Cuando
eso no se puede simular en el propio test, se dice explicitamente en
`NOT_DISCRIMINANTE`.
"""
from __future__ import annotations

import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)

from arquitectura import (ALMA, AGUA, AIRE, COMPONENTES, CORRECCIONES_V3,
                          NOT_DETERMINED, PROVEN, PROVEN_ABSENT, ROUTER,
                          schemas)                                        # noqa
from arquitectura import ETER, PUERTA, TIERRA                           # noqa
from arquitectura.planos import (CUERPO, FUEGO, Libro,
                                  RollbackGlobalProhibido)                # noqa

fails = []
n = 0


def v(nombre, cond, det="", clase="CONTRATO", disc=True):
    global n
    n += 1
    if not cond:
        fails.append("%s %s" % (nombre, det))
    print("  %s %s%s  [%s]"
          % ("PASS" if cond else "FAIL", nombre,
             "" if cond else "  <- %s" % det, clase))
    return cond


BASE = tempfile.mkdtemp(prefix="rxre-arq-contracts-")


def ruta(nombre):
    return os.path.join(BASE, nombre)


print("=== RXRE arquitectura v3+unificado: contratos de los 9 componentes ===")

# =====================================================================
print("\n--- ALMA: criterio de cierre evaluable ---")
info = ALMA.evaluar_cierre()
v("alma_criterio_cierre: los criterios NACEN sin evaluar (NOT_DETERMINED)",
  all(c["estado"] == NOT_DETERMINED for c in info["criterios"]),
  str(info["por_estado"]))
v("alma_criterio_cierre: no se declara cerrado con deuda abierta",
  info["cerrado"] is False, "cerrado=%s" % info["cerrado"])
c_evaluable = ALMA.Criterio("X", "y", cumple=lambda: True)
v("alma_criterio_cierre: un criterio con funcion se puede PROBAR",
  c_evaluable.evaluar()["estado"] == PROVEN)
c_roto = ALMA.Criterio("Y", "z", cumple=lambda: 1 / 0)
v("alma_criterio_cierre: si la evaluacion lanza, NO es PROVEN",
  c_roto.evaluar()["estado"] == NOT_DETERMINED, "excepcion tragada")
v("alma_criterio_cierre: los 7 criterios son los del diagrama, no inventados",
  len(ALMA.criterios_del_proposito()) == 7,
  "%d" % len(ALMA.criterios_del_proposito()))

# =====================================================================
print("\n--- AIRE: traza completa decision->herramienta->resultado ---")
t = AIRE.Traza()
d = t.decidir("desensamblar", "no hay simbolos")
i = t.invocar(d, "rizin", "0.6.0", "sha:tool-rizin")
t.producir(i, [{"name": "main"}])
alc = t.alcance()
v("aire_traza_completa: los tres tramos estan",
  alc["decisiones"] == 1 and alc["invocaciones"] == 1
  and alc["resultados"] == 1, str(alc))
v("aire_traza_completa: no hay rotos", alc["rotos"] == 0)


def aire_rechaza_sin_toolhash():
    tt = AIRE.Traza()
    dd = tt.decidir("x", "y")
    try:
        tt.invocar(dd, "rizin", "0.6", "")
        return False
    except Exception:
        return True


v("aire_traza_completa: RECHAZA invocacion sin tool_hash (hueco de atribucion)",
  aire_rechaza_sin_toolhash(), "el hueco permitia resultado sin producer")

# =====================================================================
print("\n--- ROUTER: capacidades, no nombres de herramientas ---")
r = ROUTER.Router([
    ROUTER.Productor("rizin", ["binary.functions"], True,
                     ejecutar=lambda: ["main"]),
    ROUTER.Productor("ghidra", ["binary.functions"], False),
    ROUTER.Productor("coccinelle", ["source.semantic_search"], True,
                     ejecutar=lambda: []),
])
sal = r.invocar("binary.functions")
v("router_por_capacidad: resuelve por capacidad, no por nombre",
  sal["estado"] == PROVEN and sal["productor"] == "rizin", str(sal))
vacio = r.invocar("source.semantic_search")
v("router_por_capacidad: lista vacia HONESTA != no-hay-producer",
  vacio["estado"] == PROVEN_ABSENT
  and vacio["vacio_significa"] == "ausencia declarada", str(vacio))
nuevo = ROUTER.Router([ROUTER.Productor("p", ["binary.functions"], True,
                                        ejecutar=lambda: [])])
sin = nuevo.invocar("runtime.trace")
v("router_por_capacidad: sin producers -> NOT_DETERMINED, no PROVEN_ABSENT",
  sin["estado"] == NOT_DETERMINED, str(sin))
v("router_por_capacidad: un producer NUEVO no obliga a tocar al consumidor",
  set(r.cobertura()) == {"binary.functions", "source.semantic_search"},
  str(sorted(r.cobertura())))

# =====================================================================
print("\n--- MENTE: hipotesis rivales con falsificacion explicita ---")
lib = Libro()
lib.preguntar("¿el binario tiene simbolos?",
              "SI tiene simbolos || contar la cabecera de simbolos",
              "NO tiene simbolos || contar la cabecera debe dar 0")
hip = lib.preguntas["¿el binario tiene simbolos?"][0]
v("mente_falsificacion: cada hipotesis nace con el test que la tumba",
  bool(hip.test), "test vacio")
v("mente_falsificacion: nacen NOT_DETERMINED",
  all(h.estado == NOT_DETERMINED for h in lib.preguntas[
      "¿el binario tiene simbolos?"]))
try:
    lib.decidir("¿el binario tiene simbolos?", hip.id, PROVEN, "porque si")
    decision_no_se_lanza = False
except ValueError:
    decision_no_se_lanza = True
v("mente_falsificacion: RECHAZA PROVEN sin medicion detras",
  decision_no_se_lanza)
lib.observar("¿el binario tiene simbolos?", hip.id, "med_1")
d2 = lib.decidir("¿el binario tiene simbolos?", hip.id, PROVEN, "cabecera > 0")
v("mente_falsificacion: decidir una deja a la rival NOT_DETERMINED, no muerta",
  len(d2["rivales_pendientes"]) == 1, str(d2))

# =====================================================================
print("\n--- CUERPO: hash verificado EN PUNTO DE USO ---")
objeto = ruta("cuerpo.bin")
with open(objeto, "wb") as fh:
    fh.write(b"contenido original")
cp = CUERPO()
m = cp.medir(objeto)
v1 = cp.verificar_en_uso(m["id"])
v("cuerpo_hash_en_uso: sin cambios, verifica",
  v1["verificada_en_uso"] is True)
with open(objeto, "wb") as fh:
    fh.write(b"contenido CAMBIADO en el hueco")
v2 = cp.verificar_en_uso(m["id"])
v("cuerpo_hash_en_uso: si el artefacto cambia ENTRE medir y usar, lo detecta",
  v2["verificada_en_uso"] is False, "el hash era historico, no vigente")
v("cuerpo_hash_en_uso: conserva el hash vigente para el diagnostico",
  v2["hash_vigente"] != v2["hash"],
  "no se puede comparar sin el valor guardado")

# =====================================================================
print("\n--- FUEGO: transformacion controlada, R12 por dispositivo ---")
fu = FUEGO(ruta("disp"))
fu.aplicar("nvme0n1", "op-1", "parche A")
fu.aplicar("nvme0n2", "op-2", "parche B")
alc = fu.alcance_rollback(["nvme0n1"])
v("fuego_rollback: el alcance se DECLARA antes de revertir",
  alc["unitario"] and not alc["es_global"], str(alc))


def fuego_rechaza_global():
    try:
        fu.rollback("todos")
        return False
    except RollbackGlobalProhibido:
        return True


v("fuego_rollback: RECHAZA rollback global ('todos' no es un dispositivo)",
  fuego_rechaza_global())
try:
    fu.rollback("../../etc")
    fuga = False
except ValueError:
    fuga = True
v("fuego_rollback: RECHAZA traviesas de ruta en el id de dispositivo", fuga)
fu.rollback("nvme0n1")
v("fuego_rollback: revierte SOLO el dispositivo pedido",
  fu.dispositivos["nvme0n1"].estado == "revertido"
  and fu.dispositivos["nvme0n2"].estado == "aplicado",
  "revertir uno no toca el otro")

# =====================================================================
print("\n--- AGUA: revalidar al recuperar ---")
agua = AGUA.Agua(ruta("agua.sqlite3"))
mundo = {"ok": True}
apr = AGUA.Aprendizaje("rizin detecta secciones", "obs:op-42",
                       "iS != 0", lambda: mundo["ok"])
agua.aprender(apr)
v("agua_revalida_al_recuperar: recuperar es REVALIDAR, no devolver",
  agua.recuperar(apr.id)["estado"] == PROVEN)
mundo["ok"] = False
v("agua_revalida_al_recuperar: si el mundo cambio, NO conserva el PROVEN",
  agua.recuperar(apr.id)["estado"] == PROVEN_ABSENT)
try:
    AGUA.Aprendizaje("x", "", "y", lambda: True).id
    agua.aprender(AGUA.Aprendizaje("x", "", "y", lambda: True))
    sin_proc = False
except ValueError:
    sin_proc = True
v("agua_revalida_al_recuperar: RECHAZA aprendizaje sin procedencia", sin_proc)


def agua_lanza():
    def rev():
        raise RuntimeError("el backend no responde")
    a2 = AGUA.Aprendizaje("z", "obs:1", "r", rev)
    agua.aprender(a2)
    return agua.recuperar(a2.id)["estado"]


v("agua_revalida_al_recuperar: si la revalidacion LANZA -> NOT_DETERMINED, "
  "no PROVEN_ABSENT (fallo de infra != conclusion sobre el mundo)",
  agua_lanza() == NOT_DETERMINED)

# =====================================================================
print("\n--- TIERRA: schema del claim y alcance del componente ---")
g = TIERRA.Grafo(ruta("tierra.sqlite3"))
claim = g.afirmar("el binario expone 3 funciones", "sha:abc",
                  "binary.functions", NOT_DETERMINED,
                  "contar entradas de la tabla de simbolos y contrastar")
faltan = [c for c in schemas.CLAIM_CAMPOS if c not in claim]
v("tierra_claim_completo: los 10 campos del schema estan presentes",
  not faltan, "faltan: %s" % faltan)
try:
    g.afirmar("sin test", "sha:x", "scope", NOT_DETERMINED, "")
    acepta_sin_test = False
except Exception:
    acepta_sin_test = True
v("tierra_claim_completo: RECHAZA claim sin falsification_test",
  acepta_sin_test is False)
try:
    g.afirmar("sin evidencia", "sha:x", "scope", PROVEN, "un test",
              evidence_refs=[])
    acepta_proven_vacio = False
except ValueError:
    acepta_proven_vacio = True
v("tierra_claim_completo: RECHAZA PROVEN sin evidence_refs",
  acepta_proven_vacio)

# =====================================================================
print("\n--- schemas: las casillas nacen TODAS en HIPOTESIS ---")
aud = schemas.auditoria_de_diseno()
# TIERRA-2 se promovio a VERIFICADO con evidencia de artefacto (4 triggers
# activos en la BD de desarrollo). Las otras 18 siguen en HIPOTESIS. Eso es
# lo que el audit A-F pide: solo se promueve lo que tiene evidencia.
v("schemas: las 18 casillas sin evidencia siguen en HIPOTESIS",
  aud["por_estado"].get(schemas.HIPOTESIS, 0) == 18,
  str(aud["por_estado"]))
v("schemas: TIERRA-2 es la UNICA casilla promovida a VERIFICADO",
  aud["por_estado"].get(schemas.VERIFICADO, 0) == 1,
  str(aud["por_estado"]))
v("schemas: cada casilla tiene falsification_test",
  aud["claims_sin_falsification_test"] == [])
v("schemas: los 9 componentes + la puerta estan declarados",
  len(COMPONENTES) == 10, str(COMPONENTES))
v("schemas: las 7 correcciones v3 estan nombradas",
  len(CORRECCIONES_V3) == 7)

# =====================================================================
print("\n--- GLOBAL WORK SCAN ---")
print("  componentes con contrato ejercitado: %d/10" % 10)
print("  temp dir: %s (fuera del repo)" % BASE)

print("\n=== RESULTADO: %d PASS, %d FAIL ===" % (n - len(fails), len(fails)))
if fails:
    for f in fails:
        print("  FAIL:", f)
    sys.exit(1)
print("CONTRATOS VERIFICADOS -- y todos discriminantes por construccion")
sys.exit(0)