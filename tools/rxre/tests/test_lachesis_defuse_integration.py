#!/usr/bin/env python3
"""RXRE-1630. Prueba de integracion REAL: los seis casos del
experimento de RXRE-1629, contra Lachesis 0.5.3 ejecutado por
CLI y el corpus real del kernel.

QUE PRUEBA Y QUE NO.

Esta prueba SI ejecuta procesos: el adaptador por CLI (que a
su vez ejecuta reg_resolve.py y lachesis por subproceso), y la
maquina `query` end-to-end (intencion -> pipeline -> handler ->
adaptador -> proveedor -> envelope). Es la unica prueba que
demuestra el criterio binario de RXRE-1629 §8: los seis casos
responden con el envelope de RXRE, y mmATC_L2_CNTL se resuelve
POR BLOQUE DE IP, no por nombre.

NO toca la GPU, no escribe fuera del worktree, no instala nada
global. El grafo se construye UNA vez (build+enrich, ~6 min
medidos) y se reusa por manifiesto (huella del corpus + version
de lachesis + argv de build): la prueba es repetible sin repetir
el coste.

LO QUE SE REGISTRA POR CASO (artefactos en
tools/rxre/tests/fixtures/lachesis/integration-results/):

    argv, codigo de salida, tiempo de pared, el contrato JSON
    completo, y las aserciones de aceptacion del caso.

PRUEBAS NO EJECUTADAS (declaradas, no omitidas):

    El corpus COMPLETO del kernel (304 archivos, 128 k nodos):
    medido en RXRE-1629, no materializa en este host ni con
    2 GiB de pool ("Buffer manager exception: buffer pool is
    full"). El corpus acotado (corpus-small, 116 archivos,
    29 MB) es el universo declarado de esta prueba, y la
    frontera se declara en cada resultado como limitacion.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
RXRE_PKG = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, RXRE_PKG)

ADAPTADOR = os.path.join(RXRE_PKG, "adapters",
                            "lachesis_defuse.py")
LACHESIS_BIN = os.path.join(ROOT, "externals",
                                "lachesis-runtime", "bin",
                                "lachesis")
CORPUS = os.path.join(HERE, "fixtures", "lachesis",
                          "corpus-small")
GRAFO = os.path.join(HERE, "fixtures", "lachesis",
                         "lachesis-defuse.kuzu")
KERNELBUILD = os.path.join(ROOT, "RESEARCH", "kernelbuild",
                               "linux-7.1.3")
RESULTADOS = os.path.join(HERE, "fixtures", "lachesis",
                              "integration-results")

fails: List[str] = []
checks = 0


def v(nombre: str, cond: bool, det: Any = "") -> None:
    global checks
    checks += 1
    if not cond:
        fails.append("%s %s" % (nombre, det))


def _precondiciones() -> List[str]:
    """Todo lo que esta prueba necesita y que, si falta, la hace
    NO_EJECUTADA (con la causa), nunca falsa-verde."""
    faltan: List[str] = []
    if not os.path.isfile(ADAPTADOR):
        faltan.append("adaptador: %s" % ADAPTADOR)
    if not os.path.isfile(LACHESIS_BIN):
        faltan.append("lachesis 0.5.3: %s" % LACHESIS_BIN)
    if not os.path.isdir(CORPUS):
        faltan.append("corpus acotado: %s" % CORPUS)
    if not os.path.isfile(os.path.join(
            KERNELBUILD, "drivers", "gpu", "drm", "amd",
            "include", "asic_reg", "gmc", "gmc_8_1_d.h")):
        faltan.append("kernelbuild (symlink a RESEARCH): %s"
                      % KERNELBUILD)
    return faltan


def _ejecutar_adaptador(intent: str, subject: str,
                          extras: List[str],
                          timeout: int = 2400) -> Tuple[int,
                                                          Dict[str, Any],
                                                          float,
                                                          str]:
    argv = [sys.executable, ADAPTADOR,
            "--intent", intent, "--subject", subject,
            "--kernel", KERNELBUILD,
            "--lachesis-bin", LACHESIS_BIN,
            "--timeout", "300"] + list(extras)
    # El presupuesto de la OPERACION (subproceso
    # completo) lo acota el `timeout` de este ejecutor,
    # no una bandera del adaptador: el adaptador solo
    # conoce el presupuesto por consulta.
    t0 = time.time()
    p = subprocess.run(argv, capture_output=True, text=True,
                       timeout=timeout, cwd=ROOT)
    wall = time.time() - t0
    try:
        contrato = json.loads(p.stdout)
    except ValueError:
        contrato = {"_error": "salida no JSON",
                    "stdout": p.stdout[:400],
                    "stderr": p.stderr[:400]}
    return p.returncode, contrato, wall, p.stderr


def _grabar(nombre: str, obj: Any) -> None:
    os.makedirs(RESULTADOS, exist_ok=True)
    with open(os.path.join(RESULTADOS, nombre), "w") as fh:
        json.dump(obj, fh, indent=2, default=str)


_TRUNC_PAT = re.compile(
    r"TRUNCA el historial por presupuesto de respuesta: "
    r"(\d+) de (\d+) valores relacionados \((\d+) omitidos\)")


def _declara_truncamiento_consistente(limitacion: str) -> bool:
    """El truncamiento por presupuesto se DECLARA con
    numeros, y los numeros son internamente consistentes:
    mostrados + omitidos = total.

    Los conteos concretos dependen de la corrida (el
    estimador de tokens del proveedor ajusta cuantas
    entries entran en el presupuesto segun su tamano
    serializado), por lo que la asercion no hardcodea
    los numeros: verifica la PROPIEDAD del contrato,
    que es la declaracion numerica y su consistencia.
    Un historial truncado no es un historial completo,
    y el consumidor tiene que ver cuanto se omitio."""
    m = _TRUNC_PAT.search(limitacion)
    if not m:
        return False
    mostrados, total, omitidos = (int(g) for g in m.groups())
    return mostrados + omitidos == total


def main() -> int:
    faltan = _precondiciones()
    if faltan:
        print("INTEGRACION NO EJECUTADA. Faltan precondiciones:")
        for f in faltan:
            print("  - %s" % f)
        print("Causa declarada: sin ellas no hay prueba real, "
              "y una prueba sin proveedor no es una prueba de "
              "integracion (es un mock con apariencia de "
              "medicion).")
        return 3

    print("=" * 64)
    print("RXRE-1630 INTEGRACION REAL")
    print("lachesis: %s" % LACHESIS_BIN)
    print("corpus:   %s (%d archivos)"
          % (CORPUS, sum(len(fs) for _, _, fs in
                           os.walk(CORPUS))))
    print("kernel:   %s" % KERNELBUILD)
    print("=" * 64)

    registro: Dict[str, Any] = {"casos": {}, "maquina": {},
                                   "errores_reales": {}}

    # -- Caso 1: localizacion de simbolo (CON --corpus: ejercita
    #    build+enrich+manifiesto, cacheado para los demas) --
    print("\n[1/7] caso 1: symbol gmc_v8_0_gart_enable "
          "(--corpus: build+enrich la primera vez)...")
    rc, c1, wall, err = _ejecutar_adaptador(
        "symbol", "gmc_v8_0_gart_enable",
        ["--corpus", CORPUS])
    _grabar("caso-1-symbol.json",
            {"rc": rc, "wall_s": round(wall, 1),
             "contrato": c1, "stderr": err})
    print("      rc=%d wall=%.0fs resultados=%d"
          % (rc, wall, len(c1.get("results") or [])))
    v("caso1 rc=0", rc == 0, (rc, err[:200]))
    v("caso1 identity layer: ausencia NATIVA registrada",
      c1.get("layers", {}).get("identity", {}).get("status")
      == "absent")
    v("caso1 3 resultados PROVEN (1 definicion + 2 "
      "expresiones de llamada)",
      len(c1.get("results") or []) == 3
      and all(r.get("state") == "PROVEN"
              for r in c1.get("results") or []))
    v("caso1 la definicion es gmc_v8_0_gart_enable en "
      "gmc_v8_0.c:829",
      any(r.get("role") == "definition"
          and r.get("location", {}).get("start_line") == 829
          for r in c1.get("results") or []))
    v("caso1 declara el falso positivo de conteo de :1228",
      any("1228" in x and "MISMA sentencia" in x
          for x in c1.get("limitations") or []))
    registro["casos"]["caso1"] = {"rc": rc, "wall_s": wall,
                                      "estados":
                                      [r.get("state") for r in
                                       c1.get("results") or []]}

    # El grafo ya existe (build cacheado por manifiesto):
    # los demas casos lo consultan directamente.
    v("caso1 dejo un grafo construido y enriquecido",
      os.path.isdir(GRAFO)
      and os.path.isfile(GRAFO + ".manifest.json"),
      GRAFO)

    # -- Caso 2: identidad de registro por bloque de IP --
    print("\n[2/7] caso 2: def-use mmATC_L2_CNTL "
          "(la discriminante de identidad MMIO)...")
    rc, c2, wall, err = _ejecutar_adaptador(
        "def-use", "mmATC_L2_CNTL", ["--graph", GRAFO])
    _grabar("caso-2-defuse-mmatc_l2_cntl.json",
            {"rc": rc, "wall_s": round(wall, 1),
             "contrato": c2, "stderr": err})
    print("      rc=%d wall=%.0fs identidades=%d"
          % (rc, wall, len(c2.get("results") or [])))
    ids = c2.get("results") or []
    v("caso2 rc=0", rc == 0, (rc, err[:200]))
    v("caso2 TRES identidades (no una fusion por nombre)",
      len(ids) == 3, len(ids))
    v("caso2 bloques {GC, GMC, MMHUB}",
      sorted(i.get("ip_block") for i in ids)
      == ["GC", "GMC", "MMHUB"])
    v("caso2 direcciones {0x640, 0x800, 0xcd5}",
      sorted(i.get("address") for i in ids)
      == ["0x640", "0x800", "0xcd5"])
    v("caso2 11 definiciones nativas repartidas 3+5+3",
      [i.get("definition_count") for i in ids] == [3, 5, 3])
    v("caso2 9 nodos del proveedor repartidos 3+5+1",
      [len(i.get("provider_nodes") or []) for i in ids]
      == [3, 5, 1])
    v("caso2 SIN COLISIONES: los nodos de cada identidad "
      "vienen de SU bloque",
      all(all(n["location"]["file"].split("asic_reg/")[-1]
              .startswith(i["ip_block"].lower() + "/")
              for n in i.get("provider_nodes") or [])
          for i in ids))
    v("caso2 la union es por clave de definicion "
      "(sufijo asic_reg + linea)",
      all(all("clave de definicion" in n.get("union", "")
              for n in i.get("provider_nodes") or [])
          for i in ids))
    v("caso2 2 definiciones fuera del corpus del proveedor "
      "DECLARADAS (mmhub_9_1, mmhub_9_3_0)",
      any("mmhub_9_1_offset.h" in x and "mmhub_9_3_0_offset.h"
          in x for x in c2.get("limitations") or []))
    v("caso2 el dataflow de cada macro es NOT_DETERMINED con "
      "causa (opaco), NO 'no hay flujo'",
      all(i.get("dataflow", {}).get("state")
          == "NOT_DETERMINED"
          and "opaco" in i["dataflow"]["causa"]
          and "NO es ausencia" in i["dataflow"]["causa"]
          for i in ids))
    v("caso2 la eleccion nativa (GMC/0xcd5) se REPORTA con "
      "su regla y su evidencia de arista de include",
      any(i.get("native_selection", {}).get("rule")
          == "GFX8 GMC consumer includes the selected "
             "register header"
          and i["native_selection"]["evidence"]["line"] == 35
          for i in ids))
    v("caso2 conflicto y candidatos declarados",
      c2["layers"]["identity"]["conflict"] is True
      and c2["layers"]["identity"]["candidates"]
      == ["0x640", "0x800", "0xcd5"])
    registro["casos"]["caso2"] = {
        "rc": rc, "wall_s": wall,
        "identidades": [
            {"bloque": i["ip_block"],
             "direccion": i["address"],
             "defs": i["definition_count"],
             "nodos": len(i.get("provider_nodes") or []),
             "dataflow": i["dataflow"]["state"]}
            for i in ids]}

    # -- Caso 3: definicion y consumidores de funcion --
    print("\n[3/7] caso 3: def-use gmc_v8_0_gart_enable...")
    rc, c3, wall, err = _ejecutar_adaptador(
        "def-use", "gmc_v8_0_gart_enable", ["--graph", GRAFO])
    _grabar("caso-3-defuse-gmc_v8_0_gart_enable.json",
            {"rc": rc, "wall_s": round(wall, 1),
             "contrato": c3, "stderr": err})
    roles = [r.get("role") for r in c3.get("results") or []]
    print("      rc=%d wall=%.0fs roles=%s" % (rc, wall, roles))
    v("caso3 rc=0", rc == 0, (rc, err[:200]))
    v("caso3 definicion + 1 parametro + 4 llamadas + 2 "
      "aristas de destino",
      roles.count("definition") == 1
      and roles.count("parameter") == 1
      and roles.count("outgoing_call") == 4
      and sum(1 for r in c3.get("results") or []
              if r.get("kind") == "call_target") == 2, roles)
    v("caso3 MAY_INVOKE es PARTIAL (candidato a dispatch, "
      "confianza low, name-fallback)",
      any(r.get("edge_kind") == "MAY_INVOKE"
          and r.get("state") == "PARTIAL"
          and r.get("confidence") == "low"
          for r in c3.get("results") or []))
    v("caso3 INVOKES es PROVEN (llamada directa)",
      any(r.get("edge_kind") == "INVOKES"
          and r.get("state") == "PROVEN"
          for r in c3.get("results") or []))
    v("caso3 declara las 2 llamadas sin arista como frontera "
      "de corpus (no como llamadas no resueltas)",
      any("2 de 4 llamadas" in x and "EXTERNO al corpus" in x
          for x in c3.get("limitations") or []))
    registro["casos"]["caso3"] = {"rc": rc, "wall_s": wall,
                                      "roles": roles}

    # El nodo del parametro `adev` sale del caso 3: el sujeto
    # del historial de valores se DERIVA, no se hardcodea.
    nodo_adev = None
    for r in c3.get("results") or []:
        if r.get("role") == "parameter" \
                and r.get("label") == "adev":
            nodo_adev = r.get("node_id")
    if not nodo_adev:
        v("caso4 nodo del parametro adev derivable del caso 3",
          False, "no aparece en los resultados del caso 3")
        nodo_adev = "v2:frontend:clang-c:parameter:" \
                    "4afbcc267c1671efd7dc"

    # -- Caso 4: historial de valores (flujo de datos) --
    print("\n[4/7] caso 4: value-history del parametro adev...")
    rc, c4, wall, err = _ejecutar_adaptador(
        "value-history", nodo_adev, ["--graph", GRAFO])
    _grabar("caso-4-value-history.json",
            {"rc": rc, "wall_s": round(wall, 1),
             "sujeto": nodo_adev, "contrato": c4,
             "stderr": err})
    print("      rc=%d wall=%.0fs entries=%d"
          % (rc, wall, len(c4.get("results") or [])))
    v("caso4 rc=0", rc == 0, (rc, err[:200]))
    v("caso4 resultados PARTIAL con owner_chain como cadena "
      "de procedencia",
      bool(c4.get("results"))
      and all(r.get("state") == "PARTIAL"
              and isinstance(r.get("owner_chain"), list)
              for r in c4.get("results") or []))
    v("caso4 el truncamiento por presupuesto se DECLARA "
      "con numeros internamente consistentes (mostrados + "
      "omitidos = total)",
      any(_declara_truncamiento_consistente(x)
          for x in c4.get("limitations") or []),
      c4.get("limitations"))
    v("caso4 los limites del frontend se declaran "
      "(context_sensitivity: none)",
      any("context_sensitivity: none" in x
          for x in c4.get("limitations") or []))
    registro["casos"]["caso4"] = {
        "rc": rc, "wall_s": wall,
        "entries": len(c4.get("results") or [])}

    # -- Caso 5: semantica de bits (rechazo por contrato) --
    print("\n[5/7] caso 5: bit-semantics ATC_L2_CNTL "
          "(rechazo por contrato)...")
    rc, c5, wall, err = _ejecutar_adaptador(
        "bit-semantics", "ATC_L2_CNTL", [])
    _grabar("caso-5-bit-semantics.json",
            {"rc": rc, "wall_s": round(wall, 1),
             "contrato": c5, "stderr": err})
    print("      rc=%d wall=%.0fs" % (rc, wall))
    v("caso5 rc=0 (el rechazo ES una respuesta, no un fallo)",
      rc == 0, (rc, err[:200]))
    v("caso5 NOT_DETERMINED con causa de frontera de modelo",
      (c5.get("results") or [{}])[0].get("state")
      == "NOT_DETERMINED"
      and "no hay modelo de bits"
      in (c5.get("results") or [{}])[0].get("causa", ""))
    v("caso5 señala quien responde: rxre_register_fields.py",
      (c5.get("results") or [{}])[0].get("resolvable_by", {})
      .get("tool") == "rxre_register_fields.py")
    v("caso5 NO se invoca al proveedor (tools_used vacio)",
      c5.get("tools_used") == [], c5.get("tools_used"))
    registro["casos"]["caso5"] = {"rc": rc, "wall_s": wall}

    # -- Caso 6: sujeto inexistente --
    print("\n[6/7] caso 6: def-use mmZZZ_NO_EXISTE_ESTE_REG...")
    rc, c6, wall, err = _ejecutar_adaptador(
        "def-use", "mmZZZ_NO_EXISTE_ESTE_REG",
        ["--graph", GRAFO])
    _grabar("caso-6-defuse-inexistente.json",
            {"rc": rc, "wall_s": round(wall, 1),
             "contrato": c6, "stderr": err})
    print("      rc=%d wall=%.0fs" % (rc, wall))
    v("caso6 rc=0 (empty con causa, no error)", rc == 0,
      (rc, err[:200]))
    v("caso6 la ausencia es NATIVA (reg_resolve, busqueda "
      "exhaustiva sobre asic_reg)",
      c6.get("layers", {}).get("identity", {}).get("verdict")
      == "PROVEN_ABSENT_EN_ASIC_REG"
      and "exhaustiva"
      in (c6.get("layers", {}).get("identity", {})
          .get("note") or ""))
    v("caso6 el proveedor reporta not-found en SU "
      "indice (universo distinto, declarado)",
      c6.get("layers", {}).get("provider", {}).get("status")
      == "not-found")
    v("caso6 resultados vacios CON la causa (never empty "
      "silencioso)",
      (c6.get("results") or []) == []
      and any("NO es ausencia demostrada" in x
              for x in c6.get("limitations") or []))
    registro["casos"]["caso6"] = {"rc": rc, "wall_s": wall}

    # -- Error real: precondicion y fallo del proveedor NO se
    #    convierten en ausencia (discriminacion contra el
    #    proceso real, no contra un mock) --
    print("\n[7/7] discriminacion de errores reales...")
    rc_b, cb, _, _ = _ejecutar_adaptador(
        "symbol", "gmc_v8_0_gart_enable",
        ["--graph", "/no/existe/kuzu"])
    v("error real 1: grafo inexistente -> rc=2 (blocked) con "
      "la causa, NO resultados vacios que mientan",
      rc_b == 2 and cb.get("error", {}).get("kind") == "blocked"
      and "no existe" in (cb.get("error", {}).get("detail")
                          or ""),
      (rc_b, cb.get("error")))
    _grabar("error-real-blocked.json",
            {"rc": rc_b, "contrato": cb})

    # Un directorio que NO es un grafo: el proveedor falla de
    # verdad (rc != 0 de lachesis) y el adaptador debe decir
    # error (rc=1), nunca empty.
    falso_grafo = os.path.join(RESULTADOS, "falso-grafo")
    os.makedirs(falso_grafo, exist_ok=True)
    rc_e, ce, _, _ = _ejecutar_adaptador(
        "symbol", "gmc_v8_0_gart_enable",
        ["--graph", falso_grafo], timeout=600)
    v("error real 2: proveedor falla (rc!=0) -> rc=1 (error) "
      "con la clase y el detalle, NUNCA empty interpretado "
      "como ausencia",
      rc_e == 1 and ce.get("error", {}).get("kind") == "error"
      and ce.get("error", {}).get("class") ==
      "ErrorDeProveedor",
      (rc_e, ce.get("error")))
    _grabar("error-real-proveedor.json",
            {"rc": rc_e, "contrato": ce})
    registro["errores_reales"] = {
        "blocked": rc_b, "proveedor": rc_e}

    # -- Maquina end-to-end: `query` con la capacidad
    #    value.defuse (intencion -> pipeline -> handler ->
    #    adaptador -> proveedor -> envelope normalizado) --
    print("\n[maquina] query end-to-end por capability "
          "value.defuse (caso 2)...")
    from commands import query as maquina
    req = {
        "capability": "value.defuse",
        "target": "rx550",
        "question": "¿Qué valores definen y consumen "
                    "mmATC_L2_CNTL?",
        "inputs": {
            "target": "mmATC_L2_CNTL",
            "intent": "def-use",
            "graph": GRAFO,
            "kernel": KERNELBUILD,
            "lachesis_bin": LACHESIS_BIN,
            "adapter_timeout": 2400,
        },
    }
    t0 = time.time()
    env = maquina.responder(req, persistir=False)
    wall_m = time.time() - t0
    _grabar("maquina-caso-2.json",
            {"wall_s": round(wall_m, 1), "envelope": env})
    print("      status=%s wall=%.0fs resultados=%d"
          % (env.get("status"), wall_m,
             len(env.get("results") or [])))
    v("maquina: envelope status ok",
      env.get("status") == "ok", env.get("status"))
    v("maquina: 3 resultados normalizados",
      len(env.get("results") or []) == 3,
      len(env.get("results") or []))
    v("maquina: los resultados normalizados llevan el estado "
      "epistemico (proven) y el raw con state",
      all(r.get("status") == "proven"
          and (r.get("raw") or {}).get("state") == "PROVEN"
          for r in env.get("results") or []),
      [(r.get("status"), (r.get("raw") or {}).get("state"))
       for r in env.get("results") or []])
    v("maquina: las tres identidades conservan bloque y "
      "direccion distintos (sin colision por el pipeline)",
      sorted(r.get("raw", {}).get("ip_block")
             for r in env.get("results") or [])
      == ["GC", "GMC", "MMHUB"]
      and sorted(r.get("raw", {}).get("address")
                 for r in env.get("results") or [])
      == ["0x640", "0x800", "0xcd5"])
    ev = {e.get("kind") for e in env.get("evidence") or []}
    v("maquina: las capas viajan en evidence",
      ev >= {"capa_identity", "capa_provider",
             "capa_dataflow"}, ev)
    v("maquina: la provenance declara reg_resolve + lachesis "
      "por CLI",
      {p.get("tool") for p in env.get("provenance") or []}
      == {"reg_resolve.py", "lachesis"})
    v("maquina: limitaciones presentes (el conflicto y la "
      "agrupacion por identidad nativa)",
      any("CONFLICTO" in x or "conflicto" in x
          for x in env.get("limitations") or []))
    registro["maquina"] = {"status": env.get("status"),
                               "wall_s": wall_m,
                               "resultados":
                               len(env.get("results") or [])}

    # -- Resumen --
    _grabar("summary.json", registro)
    print("\n" + "=" * 64)
    print("RESUMEN DE INTEGRACION REAL")
    print("=" * 64)
    for nombre, datos in registro["casos"].items():
        print("  %-8s rc=%s wall=%.0fs %s"
              % (nombre, datos.get("rc"),
                 datos.get("wall_s", 0),
                 datos.get("identidades")
                 or datos.get("roles")
                 or datos.get("estados")
                 or ""))
    print("  maquina  status=%s wall=%.0fs resultados=%d"
          % (registro["maquina"].get("status"),
             registro["maquina"].get("wall_s", 0),
             registro["maquina"].get("resultados", 0)))
    print("  errores reales discriminados: blocked=%s "
          "proveedor=%s"
          % (registro["errores_reales"].get("blocked"),
             registro["errores_reales"].get("proveedor")))
    print("  verificados: %d" % checks)
    if fails:
        print("FALLOS (%d):" % len(fails))
        for f in fails:
            print("  [FALLA] %s" % f)
        return 1
    print("INTEGRACION REAL: TODO VERDE (%d)" % checks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
