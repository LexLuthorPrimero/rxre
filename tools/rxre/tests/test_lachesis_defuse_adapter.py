#!/usr/bin/env python3
"""RXRE-1630. Tests del adaptador lachesis_defuse: contrato, matriz de
errores y discriminante de identidad MMIO.

QUE PRUEBA Y QUE NO.

Este modulo convierte el contrato del adaptador
(`tools/rxre/adapters/lachesis_defuse.py`) en vectores
ejecutables. NO ejecuta Lachesis, NO ejecuta reg_resolve, NO
abre red y NO toca la GPU: los tests G1-G3 corren contra
SALIDAS REALES CAPTURADAS de lachesis 0.5.3 y reg_resolve
(fijadas como fixtures), con las dos capas externas sustituidas
por dobles. La unica excepcion es G4 (regresion de interfaces
consumidas), que ejecuta reg_resolve.py por subproceso LOCAL
contra el corpus kernelbuild: es la interfaz que el adaptador
consume, y su regresion es parte del contrato.

Cada grupo tiene un ORACLE INDEPENDIENTE donde aplica:

    G3 (discriminante MMIO): las identidades de mmATC_L2_CNTL
    se reconstruyen con regex PROPIA sobre los headers
    asic_reg, sin reg_resolve ni fixtures. El adaptador debe
    coincidir con ese oracle, no con su propia salida.

La prueba de NO-RED es estructural, no declarativa: durante
G1-G3, `subprocess.run` del modulo del adaptador se sustituye
por una funcion que LANZA. Si cualquier vector G1-G3 intenta
un proceso externo, el vector falla. Un test que pasa porque
el proceso no se intento es un test verde de verdad; uno que
pasa porque el proceso fallo silenciosamente no lo es.

CRITERIO DE FALLO CONTRA LOS DEFECTOS QUE ESTE TEST VIGILA:

    D1  un fallo del proveedor se convierte en "no hay flujo"
        -> G2 vigila que rc!=0, JSON ilegible, esquema roto y
           timeout son ERROR, nunca empty
    D2  mmATC_L2_CNTL se resuelve por nombre (fusion de las
        tres instancias) -> G3 vigila tres identidades con
        tres direcciones, sin colisiones, verificadas contra
        el oracle de headers
    D3  una ausencia del proveedor se convierte en
        PROVEN_ABSENT -> G1/G2 vigilan que la unica ausencia
        emitida es la NATIVA (reg_resolve, busqueda exhaustiva)
    D4  el adaptador elige un nodo o una identidad en silencio
        -> G1 vigila desambiguacion explicita y eleccion nativa
           REPORTADA con su evidencia, nunca reeligida
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import types
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
RXRE_PKG = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, RXRE_PKG)

from adapters import lachesis_defuse as lad  # noqa: E402
from api import envelope as E  # noqa: E402
from commands import handlers  # noqa: E402
from core import capabilities as caps  # noqa: E402
from core import dispatch  # noqa: E402
from core import engine  # noqa: E402
from core import normalize as N  # noqa: E402

FIXTURES = os.path.join(HERE, "fixtures", "lachesis")
KERNELBUILD = os.path.join(ROOT, "RESEARCH", "kernelbuild", "linux-7.1.3")
ASIC_REG = os.path.join(KERNELBUILD, "drivers", "gpu", "drm", "amd",
                        "include", "asic_reg")
REG_RESOLVE = os.path.join(ROOT, "tools", "reg_resolve.py")

fails: List[str] = []
checks = 0


def v(nombre: str, cond: bool, det: Any = "") -> None:
    global checks
    checks += 1
    if not cond:
        fails.append("%s %s" % (nombre, det))


def fx(nombre: str) -> Dict[str, Any]:
    with open(os.path.join(FIXTURES, nombre)) as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# DOBLES DE LAS CAPAS EXTERNAS (sin proceso, sin red)
# ---------------------------------------------------------------------------

def _doble_con(registros: Dict[str, Dict[str, Any]],
               fallos: Optional[Dict[str, Exception]] = None
               ) -> lad._ProveedorFijo:
    return lad._ProveedorFijo(registros, fallos)


def _nativo_con(docs: Dict[str, Dict[str, Any]]) -> lad._NativoFijo:
    return lad._NativoFijo(docs)


CASO1_PROV = _doble_con({"find-entity": fx(
    "find-entity_gmc_v8_0_gart_enable.json")})
CASO1_GART_NATIVE = _nativo_con({
    "gmc_v8_0_gart_enable": fx("reg-resolve_gmc_v8_0_gart_enable.json")})

CASO2_PROV = _doble_con({
    "find-entity": fx("find-entity_mmATC_L2_CNTL.json"),
    "value-history": fx("value-history_macro_mmATC_L2_CNTL.json")})
CASO2_NATIVE = _nativo_con({
    "mmATC_L2_CNTL": fx("reg-resolve_mmATC_L2_CNTL.json")})

CASO3_PROV = _doble_con({
    "find-entity": fx("find-entity_gmc_v8_0_gart_enable.json"),
    "function": fx("function_gmc_v8_0_gart_enable.json")})

CASO4_PROV = _doble_con({
    "value-history": fx("value-history_parameter_adev.json")})

CASO6_PROV = _doble_con({
    "find-entity": fx("find-entity_mmZZZ_NO_EXISTE.json")})
CASO6_NATIVE = _nativo_con({
    "mmZZZ_NO_EXISTE_ESTE_REG": fx(
        "reg-resolve_mmZZZ_NO_EXISTE_ESTE_REG.json")})


# ---------------------------------------------------------------------------
# ORACLE INDEPENDIENTE: identidad de registro leida de los headers
# con regex PROPIA, sin reg_resolve y sin fixtures
# ---------------------------------------------------------------------------

DEFINE_PAT = re.compile(
    r"^\s*#\s*define\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"\s+(?P<val>0[xX][0-9a-fA-F]+|\d+)\s*$"
)


def oracle_definiciones(reg: str) -> List[Tuple[str, int, int]]:
    """(relpath bajo asic_reg, linea, valor) de cada #define de `reg`,
    leido directamente de los headers."""
    out: List[Tuple[str, int, int]] = []
    for base, _, ficheros in os.walk(ASIC_REG):
        for f in sorted(ficheros):
            if not f.endswith(".h"):
                continue
            ruta = os.path.join(base, f)
            with open(ruta, errors="replace") as fh:
                for i, linea in enumerate(fh, 1):
                    m = DEFINE_PAT.match(linea)
                    if m and m.group("name") == reg:
                        out.append((os.path.relpath(ruta, ASIC_REG),
                                    i, int(m.group("val"), 0)))
    return out


def oracle_identidades(reg: str) -> Dict[Tuple[str, int],
                                         List[Tuple[str, int, int]]]:
    """Agrupacion oracle por (bloque, direccion). El bloque es el
    directorio bajo asic_reg/ (la misma regla de proyeccion que el
    adaptador, pero aplicada sobre el oracle, no sobre su salida)."""
    grupos: Dict[Tuple[str, int], List[Tuple[str, int, int]]] = {}
    for rel, linea, valor in oracle_definiciones(reg):
        partes = rel.split(os.sep)
        bloque = partes[0].upper() if partes else "DESCONOCIDO"
        grupos.setdefault((bloque, valor), []).append((rel, linea, valor))
    return grupos


# ---------------------------------------------------------------------------
# G1: LOS SEIS CASOS DEL EXPERIMENTO (contra fixtures reales)
# ---------------------------------------------------------------------------

def _sin_procesos():
    """Contexto que prohbe todo proceso externo: si un vector G1-G3
    intenta `subprocess.run`, LANZA en vez de ejecutar."""

    class _Prohibido:
        TimeoutExpired = subprocess.TimeoutExpired

        @staticmethod
        def run(*a: Any, **k: Any) -> Any:
            raise AssertionError(
                "subprocess.run() invocado en tests sin red: argv=%r"
                % (a[0] if a else None,))

    return _Prohibido()


def caso_1() -> Dict[str, Any]:
    a = lad.Defuse(native=CASO1_GART_NATIVE, provider=CASO1_PROV,
                   grafo="fixture://lachesis")
    return a.consultar("symbol", "gmc_v8_0_gart_enable")


def caso_2(ip_block: Optional[str] = None,
           address: Optional[str] = None) -> Dict[str, Any]:
    a = lad.Defuse(native=CASO2_NATIVE, provider=CASO2_PROV,
                   grafo="fixture://lachesis",
                   ip_block=ip_block, address=address)
    return a.consultar("def-use", "mmATC_L2_CNTL")


def caso_3() -> Dict[str, Any]:
    a = lad.Defuse(native=CASO1_GART_NATIVE, provider=CASO3_PROV,
                   grafo="fixture://lachesis")
    return a.consultar("def-use", "gmc_v8_0_gart_enable")


def caso_4() -> Dict[str, Any]:
    a = lad.Defuse(native=_nativo_con({}), provider=CASO4_PROV,
                   grafo="fixture://lachesis")
    return a.consultar("value-history",
                       "v2:frontend:clang-c:parameter:"
                       "4afbcc267c1671efd7dc")


def caso_5() -> Tuple[Dict[str, Any], _doble_con]:
    prov = _doble_con({})
    a = lad.Defuse(native=_nativo_con({}), provider=prov,
                   grafo="fixture://lachesis")
    return a.consultar("bit-semantics", "ATC_L2_CNTL"), prov


def caso_6() -> Dict[str, Any]:
    a = lad.Defuse(native=CASO6_NATIVE, provider=CASO6_PROV,
                   grafo="fixture://lachesis")
    return a.consultar("def-use", "mmZZZ_NO_EXISTE_ESTE_REG")


def g1_seis_casos() -> None:
    # Caso 1: localizacion de simbolo
    r = caso_1()
    v("T1601 caso1 identity layer ausente (no es registro)",
      r["layers"]["identity"]["status"] == "absent"
      and r["layers"]["identity"]["verdict"] == "PROVEN_ABSENT_EN_ASIC_REG",
      r["layers"]["identity"])
    v("T1601 caso1 tiene 3 resultados (1 definicion + 2 expresiones)",
      len(r["results"]) == 3, len(r["results"]))
    v("T1601 caso1 todos los resultados son PROVEN",
      all(x["state"] == "PROVEN" for x in r["results"]))
    v("T1601 caso1 la definicion es la funcion en :829",
      any(x["role"] == "definition" and x["kind"] == "function"
          and x["location"]["start_line"] == 829 for x in r["results"]),
      [(x.get("role"), x.get("location", {}).get("start_line"))
       for x in r["results"]])
    v("T1601 caso1 la procedencia es del compilador",
      all(x.get("origin") == "compiler" for x in r["results"]))
    v("T1601 caso1 declara el falso positivo de conteo de :1228",
      any("1228" in x and "MISMA sentencia" in x
          for x in r["limitations"]), r["limitations"])

    # Caso 2: identidad de registro por bloque de IP
    r2 = caso_2()
    ids = r2["results"]
    v("T1602 caso2 tres identidades, no una fusion por nombre",
      len(ids) == 3, len(ids))
    v("T1602 caso2 bloques {GC, GMC, MMHUB}",
      sorted(i["ip_block"] for i in ids) == ["GC", "GMC", "MMHUB"])
    v("T1602 caso2 direcciones {0x640, 0x800, 0xcd5}",
      sorted(i["address"] for i in ids) == ["0x640", "0x800", "0xcd5"])
    v("T1602 caso2 11 definiciones repartidas 3+5+3",
      [i["definition_count"] for i in ids] == [3, 5, 3],
      [i["definition_count"] for i in ids])
    v("T1602 caso2 9 nodos de proveedor repartidos 3+5+1",
      [len(i["provider_nodes"]) for i in ids] == [3, 5, 1],
      [len(i["provider_nodes"]) for i in ids])
    v("T1602 caso2 sin colisiones: cada identidad solo tiene nodos "
      "de SU bloque",
      all(all(n["location"]["file"].split("asic_reg/")[-1]
              .startswith(i["ip_block"].lower() + "/")
              for n in i["provider_nodes"]) for i in ids),
      [[n["location"]["file"] for n in i["provider_nodes"]] for i in ids])
    v("T1602 caso2 la union es por clave de definicion, no por nombre",
      all(all("clave de definicion" in n.get("union", "")
              for n in i["provider_nodes"]) for i in ids))
    v("T1602 caso2 2 definiciones sin nodo declaradas (mmhub_9_1, "
      "mmhub_9_3_0)",
      any("mmhub_9_1_offset.h" in x and "mmhub_9_3_0_offset.h" in x
          for x in r2["limitations"]), r2["limitations"])
    v("T1602 caso2 el dataflow de macro es NOT_DETERMINED con causa",
      all(i["dataflow"]["state"] == "NOT_DETERMINED"
          and "opaco" in i["dataflow"]["causa"] for i in ids),
      [i["dataflow"] for i in ids])
    v("T1602 caso2 la causa NO dice 'no hay flujo' (no es ausencia)",
      all("NO es ausencia" in i["dataflow"]["causa"] for i in ids))
    v("T1602 caso2 la eleccion nativa (GMC/0xcd5) se REPORTA con "
      "regla y evidencia",
      any(i.get("native_selection", {}).get("rule")
          == "GFX8 GMC consumer includes the selected register header"
          and i["native_selection"]["evidence"]["line"] == 35
          for i in ids),
      [i.get("native_selection") for i in ids])
    v("T1602 caso2 la eleccion nativa es de reg_resolve, no del "
      "adaptador",
      any(i.get("native_selection", {}).get("selected_by")
          == "reg_resolve.py" for i in ids))
    v("T1602 caso2 conflicto y candidatos declarados",
      r2["layers"]["identity"]["conflict"] is True
      and r2["layers"]["identity"]["candidates"] == ["0x640", "0x800",
                                                     "0xcd5"],
      r2["layers"]["identity"])
    v("T1602 caso2 unidad declarada (indice dword, byte = *4)",
      all(i["unidad"].startswith("indice dword")
          and i["byte_offset"] == "0x%x" % (int(i["address"], 16) * 4)
          for i in ids))

    # Caso 2 con filtros: desambiguacion explicita
    r2b = caso_2(ip_block="MMHUB")
    v("T1602b --ip-block MMHUB devuelve SOLO la identidad MMHUB",
      len(r2b["results"]) == 1
      and r2b["results"][0]["ip_block"] == "MMHUB"
      and r2b["results"][0]["address"] == "0x640",
      r2b["results"])
    r2c = caso_2(address="0x800")
    v("T1602c --address 0x800 devuelve SOLO la identidad GC",
      len(r2c["results"]) == 1
      and r2c["results"][0]["ip_block"] == "GC",
      r2c["results"])

    # Caso 3: definicion y consumidores de funcion
    r3 = caso_3()
    roles = [x.get("role") for x in r3["results"]]
    v("T1603 caso3 definicion de funcion primero",
      roles[0] == "definition"
      and r3["results"][0]["location"]["start_line"] == 829, roles)
    v("T1603 caso3 un parametro (adev)",
      sum(1 for x in r3["results"] if x.get("role") == "parameter") == 1)
    v("T1603 caso3 cuatro llamadas salientes",
      sum(1 for x in r3["results"] if x.get("role") == "outgoing_call") == 4,
      roles)
    v("T1603 caso3 dos aristas de destino (INVOKES + MAY_INVOKE)",
      sum(1 for x in r3["results"] if x.get("role") is None
          and x["kind"] == "call_target") == 2, roles)
    v("T1603 caso3 INVOKES es llamada directa (PROVEN)",
      any(x.get("edge_kind") == "INVOKES" and x["state"] == "PROVEN"
          and x.get("significado") == "direct_call"
          for x in r3["results"]))
    v("T1603 caso3 MAY_INVOKE es candidato a dispatch (PARTIAL, "
      "confianza low, name-fallback)",
      any(x.get("edge_kind") == "MAY_INVOKE" and x["state"] == "PARTIAL"
          and x.get("confidence") == "low" and x.get("reason") ==
          "name-fallback" for x in r3["results"]))
    v("T1603 caso3 declara el vocabulario unificado",
      any("INVOKES" in x and "MAY_INVOKE" in x and "VTABLE" in x
          for x in r3["limitations"]), r3["limitations"])
    v("T1603 caso3 declara las 2 llamadas sin arista como frontera "
      "de corpus",
      any("2 de 4 llamadas" in x and "EXTERNO al corpus" in x
          for x in r3["limitations"]), r3["limitations"])
    v("T1603 caso3 effect_count 0 declarado (tier de efectos)",
      any("effect_count=0" in x for x in r3["limitations"]))

    # Caso 4: historial de valores
    r4 = caso_4()
    v("T1604 caso4 resultados PARTIAL (limites autodeclarados)",
      r4["results"] and all(x["state"] == "PARTIAL" for x in r4["results"]))
    v("T1604 caso4 owner_chain viaja como cadena de procedencia",
      all(isinstance(x.get("owner_chain"), list) for x in r4["results"]))
    v("T1604 caso4 truncamiento de budget declarado con numeros",
      any("TRUNCA" in x and "61" in x and "101" in x for x in
          r4["limitations"]), r4["limitations"])
    v("T1604 caso4 limites del frontend declarados (context_sensitivity "
      "none)",
      any("context_sensitivity: none" in x for x in r4["limitations"]))

    # Caso 5: semantica de bits (rechazo por contrato)
    r5, prov5 = caso_5()
    v("T1605 caso5 NOT_DETERMINED con causa concreta",
      r5["results"][0]["state"] == "NOT_DETERMINED"
      and "no hay modelo de bits" in r5["results"][0]["causa"],
      r5["results"][0])
    v("T1605 caso5 señala quien responde: rxre_register_fields.py",
      r5["results"][0]["resolvable_by"]["tool"] ==
      "rxre_register_fields.py")
    v("T1605 caso5 NO se invoca al proveedor (no hay pregunta que "
      "hacerle)",
      prov5.llamadas == [], prov5.llamadas)
    v("T1605 caso5 las tres capas son not-applicable con razon",
      all(c["status"] == "not-applicable" and c.get("reason")
          for c in r5["layers"].values()))

    # Caso 6: sujeto inexistente
    r6 = caso_6()
    v("T1606 caso6 la ausencia es NATIVA (reg_resolve, busqueda "
      "exhaustiva), no del proveedor",
      r6["layers"]["identity"]["verdict"] == "PROVEN_ABSENT_EN_ASIC_REG"
      and "exhaustiva" in (r6["layers"]["identity"].get("note") or ""),
      r6["layers"]["identity"])
    v("T1606 caso6 el proveedor reporta not-found en SU indice",
      r6["layers"]["provider"]["status"] == "not-found")
    v("T1606 caso6 resultados vacios con causa (empty, no error)",
      r6["results"] == [] and r6["limitations"]
      and any("NO es ausencia demostrada" in x for x in r6["limitations"]),
      r6["limitations"])
    v("T1606 caso6 la capa identity declara la diferencia: ausencia de "
      "definicion, no de hardware",
      any("definicion de offset" in x or "no es ausencia" in x.lower()
          for x in r6["limitations"] + [
              r6["layers"]["identity"].get("note") or ""]))


# ---------------------------------------------------------------------------
# G2: MATRIZ DE ERRORES (un fallo nunca se convierte en ausencia)
# ---------------------------------------------------------------------------

def g2_matriz_de_errores() -> None:
    with _parche_subproceso():
        # D1: fallo del proveedor (rc != 0) -> ERROR, nunca empty
        prov = _doble_con(
            {"find-entity": fx("find-entity_mmATC_L2_CNTL.json")},
            {"find-entity": lad.ErrorDeProveedor("lachesis", 3,
                                                  "boom simulado")})
        a = lad.Defuse(native=CASO2_NATIVE, provider=prov,
                       grafo="fixture://lachesis")
        try:
            a.consultar("def-use", "mmATC_L2_CNTL")
            v("T1608 rc!=0 del proveedor lanza", False, "no lanzo")
        except lad.ErrorDeProveedor as e:
            v("T1608 rc!=0 del proveedor lanza ErrorDeProveedor "
              "(el handler lo traduce a ST_ERROR, no a empty)",
              e.rc == 3 and "boom" in str(e))

        # JSON ilegible por el transporte real (proceso falso)
        cli = lad.LachesisCLI(binario="ficticio")
        _parche_run(_ProcFalso(rc=0, out="no es json en absoluto"))
        try:
            cli._ejecutar(["query", "g", "find-entity", "x"], 5)
            v("T1609 salida no JSON lanza ErrorDeEsquema", False,
              "no lanzo")
        except lad.ErrorDeEsquema:
            v("T1609 salida no JSON del proveedor es ERROR de "
              "esquema, no empty", True)
        finally:
            _desparche_run()

        # rc != 0 del transporte real
        _parche_run(_ProcFalso(rc=127, err="lachesis: no such file"))
        try:
            cli._ejecutar(["--version"], 5)
            v("T1610 rc!=0 del transporte lanza ErrorDeProveedor",
              False, "no lanzo")
        except lad.ErrorDeProveedor as e:
            v("T1610 rc!=0 del transporte lleva el stderr como "
              "evidencia", "no such file" in e.detalle)
        finally:
            _desparche_run()

        # timeout del transporte real
        _parche_run_raise(subprocess.TimeoutExpired("cmd", 5))
        try:
            cli._ejecutar(["--version"], 5)
            v("T1611 timeout del proveedor lanza ErrorDeProveedorTimeout",
              False, "no lanzo")
        except lad.ErrorDeProveedorTimeout as e:
            v("T1611 timeout del proveedor es ERROR con el presupuesto",
              e.timeout == 5)
        finally:
            _desparche_run()

        # Transporte de texto: build/enrich NO devuelven
        # JSON (su stdout es progreso). Un build exitoso
        # NO es un ErrorDeEsquema: la integracion real
        # atrapo este defecto (el build de corpus-small
        # escribe 'Streamed 1 frontends into ...' en
        # stdout, y json.loads lo convertia en error).
        _parche_run(_ProcFalso(
            rc=0,
            out="Streamed 1 frontends into /tmp/x.kuzu\n"
                "Tier: core-only (nav rebuilds the dataflow"
                " tier)\n"))
        try:
            reg = cli._ejecutar_texto(
                "build",
                ["build", "--timeout", "1800", "corpus",
                 "salida"], 5)
            v("T1641 build con salida de progreso NO es "
              "ErrorDeEsquema: el rc es la senal de vida y "
              "la salida es evidencia del efecto",
              reg["rc"] == 0 and reg["operacion"] == "build"
              and "Streamed 1 frontends" in reg["salida"],
              reg)
        except lad.ErrorDeEsquema as e:
            v("T1641 build con salida de progreso NO es "
              "ErrorDeEsquema", False, e)
        finally:
            _desparche_run()

        # build con rc != 0: el fallo del build no se
        # interpreta como grafo construido
        _parche_run(_ProcFalso(rc=1, err="kuzu: disk full"))
        try:
            cli._ejecutar_texto(
                "build",
                ["build", "--timeout", "1800", "corpus",
                 "salida"], 5)
            v("T1642 build rc!=0 lanza ErrorDeProveedor",
              False, "no lanzo")
        except lad.ErrorDeProveedor as e:
            v("T1642 build rc!=0 es ErrorDeProveedor "
              "(un build fallido no se convierte en grafo "
              "valido)", "disk full" in e.detalle)
        finally:
            _desparche_run()

        # Esquema roto: campo obligatorio ausente
        roto1 = {"schema_version": 1, "query": "find-entity",
                 "status": "exact",
                 "matches": [{"kind": "macro", "label": "mmX",
                              "location":
                                  {"file": "f.h", "start_line": 1,
                                   "start_column": 1, "end_line": 1,
                                   "end_column": 5},
                              "origin": "compiler",
                              "confidence": "exact"}]}
        prov = _doble_con({"find-entity": roto1})
        a = lad.Defuse(native=CASO2_NATIVE, provider=prov,
                       grafo="fixture://lachesis")
        try:
            a.consultar("def-use", "mmATC_L2_CNTL")
            v("T1612 match sin 'id' es ERROR de esquema", False,
              "no lanzo")
        except lad.ErrorDeEsquema as e:
            v("T1612 match sin 'id' es ERROR de esquema (no se "
              "traduce lo que no se valido)", "id" in str(e))

        # Esquema roto: tipo incorrecto
        roto2 = json.loads(json.dumps(
            fx("find-entity_mmZZZ_NO_EXISTE.json")))
        roto2["matches"] = [{"id": 123, "kind": "macro", "label": "x",
                             "location": {"file": "f.h",
                                          "start_line": "uno",
                                          "start_column": 1,
                                          "end_line": 1,
                                          "end_column": 1},
                             "origin": "compiler",
                             "confidence": "exact"}]
        prov = _doble_con({"find-entity": roto2})
        a = lad.Defuse(native=CASO2_NATIVE, provider=prov,
                       grafo="fixture://lachesis")
        try:
            a.consultar("def-use", "mmATC_L2_CNTL")
            v("T1613 tipos incorrectos son ERROR de esquema", False,
              "no lanzo")
        except lad.ErrorDeEsquema as e:
            v("T1613 tipos incorrectos son ERROR de esquema "
              "(start_line str, id int)", "start_line" in str(e))

        # El proveedor corrio y no encontro: empty CON causa
        vacio = {"schema_version": 1, "query": "find-entity",
                 "criteria": {"name": "mmX", "kind": None,
                              "file": None},
                 "status": "exact", "matches": []}
        prov = _doble_con({"find-entity": vacio})
        a = lad.Defuse(native=CASO6_NATIVE, provider=prov,
                       grafo="fixture://lachesis")
        r = a.consultar("def-use", "mmZZZ_NO_EXISTE_ESTE_REG")
        v("T1614 matches vacios (status exact) es empty CON limitacion, "
          "no ausencia demostrada",
          r["results"] == [] and r["limitations"]
          and any("NO es ausencia demostrada" in x for x in
                  r["limitations"]), r["limitations"])

        # reg_resolve rc != 0: ERROR nativo, no "no es un registro"
        _parche_run(_ProcFalso(rc=1, err="reg_resolve: kernel malformado"))
        try:
            lad._nativo_reg_resolve(KERNELBUILD, "mmATC_L2_CNTL",
                                    "gfx_8_0", 30)
            v("T1615 rc!=0 de reg_resolve lanza ErrorNativo", False,
              "no lanzo")
        except lad.ErrorNativo as e:
            v("T1615 rc!=0 de reg_resolve es ErrorNativo (no se "
              "interpreta como ausencia de registro)",
              "kernel malformado" in e.detalle)
        finally:
            _desparche_run()

        # reg_resolve salida no JSON
        _parche_run(_ProcFalso(rc=0, out="<html>error</html>"))
        try:
            lad._nativo_reg_resolve(KERNELBUILD, "mmATC_L2_CNTL",
                                    "gfx_8_0", 30)
            v("T1616 salida no JSON de reg_resolve lanza ErrorNativo",
              False, "no lanzo")
        except lad.ErrorNativo:
            v("T1616 salida no JSON de reg_resolve es "
              "ErrorNativo", True)
        finally:
            _desparche_run()

        # Precondicion: sin grafo ni corpus, proveedor real
        cli2 = lad.LachesisCLI(binario="ficticio")
        nat_gart = _nativo_con({
            "gmc_v8_0_gart_enable": fx(
                "reg-resolve_gmc_v8_0_gart_enable.json")})
        a = lad.Defuse(native=nat_gart, provider=cli2)
        try:
            a.consultar("symbol", "gmc_v8_0_gart_enable")
            v("T1617 sin grafo ni corpus es ErrorDeContrato (blocked)",
              False, "no lanzo")
        except lad.ErrorDeContrato as e:
            v("T1617 sin grafo ni corpus es ErrorDeContrato (el "
              "handler lo traduce a ST_BLOCKED)",
              "falta grafo o corpus" in str(e))

        # Precondicion: grafo inexistente
        a = lad.Defuse(native=nat_gart, provider=cli2,
                       grafo="/no/existe/kuzu")
        try:
            a.consultar("symbol", "gmc_v8_0_gart_enable")
            v("T1618 grafo inexistente es ErrorDeContrato", False,
              "no lanzo")
        except lad.ErrorDeContrato as e:
            v("T1618 grafo inexistente es ErrorDeContrato, no se "
              "consulta sobre nada", "no existe" in str(e))


class _ProcFalso:
    """CompletedProcess falso: solo lo que _ejecutar lee."""

    def __init__(self, rc: int = 0, out: str = "",
                 err: str = "") -> None:
        self.returncode = rc
        self.stdout = out
        self.stderr = err


_RUN_ORIGINAL = subprocess.run
_ESTADO_RUN: List[Any] = []


def _parche_run(proc: Any) -> None:
    _ESTADO_RUN.append(subprocess.run)
    lad.subprocess = types.SimpleNamespace(
        run=lambda *a, **k: proc,
        TimeoutExpired=subprocess.TimeoutExpired)


def _parche_run_raise(exc: Exception) -> None:
    _ESTADO_RUN.append(subprocess.run)
    lad.subprocess = types.SimpleNamespace(
        run=lambda *a, **k: (_ for _ in ()).throw(exc),
        TimeoutExpired=subprocess.TimeoutExpired)


def _desparche_run() -> None:
    if _ESTADO_RUN:
        lad.subprocess = _ESTADO_RUN.pop()


class _ParcheSubproceso:
    """Context manager: prohbe subprocess.run en el modulo del
    adaptador (prueba estructural de no-red / no-proceso)."""

    def __enter__(self) -> None:
        self._anterior = lad.subprocess
        lad.subprocess = _sin_procesos_modulo()

    def __exit__(self, *a: Any) -> None:
        lad.subprocess = self._anterior


def _sin_procesos_modulo():
    class _Prohibido:
        TimeoutExpired = subprocess.TimeoutExpired

        @staticmethod
        def run(*args: Any, **kwargs: Any) -> Any:
            raise AssertionError(
                "subprocess.run() invocado donde esta prohibido: %r"
                % (args[0] if args else None,))
    return _Prohibido()


def _parche_subproceso() -> Any:
    return _ParcheSubproceso()


# ---------------------------------------------------------------------------
# G3: DISCRIMINANTE DE IDENTIDAD MMIO (oracle de headers)
# ---------------------------------------------------------------------------

def g3_discriminante_mmio() -> None:
    with _parche_subproceso():
        # Oracle: identidades reconstruidas de los headers, sin
        # reg_resolve y sin fixtures.
        grupos = oracle_identidades("mmATC_L2_CNTL")
        v("T1619 oracle independiente: mmATC_L2_CNTL tiene 3 "
          "identidades en los headers",
          len(grupos) == 3, sorted(grupos))
        v("T1620 oracle: las direcciones son {0x640, 0x800, 0xcd5}",
          sorted("0x%x" % v for (_, v) in grupos) ==
          ["0x640", "0x800", "0xcd5"],
          sorted("0x%x" % v for (_, v) in grupos))
        v("T1621 oracle: 11 definiciones en total (3 GC + 5 GMC + "
          "3 MMHUB)",
          sorted(len(d) for d in grupos.values()) == [3, 3, 5],
          sorted(len(d) for d in grupos.values()))

        # El adaptador (sobre el fixture de reg_resolve) debe
        # coincidir con el oracle.
        def _sufijo(ruta: str) -> str:
            # Ambos lados se normalizan al sufijo tras
            # asic_reg/: el fixture habla de rutas relativas
            # a la raiz del kernel, el oracle a asic_reg/.
            n = ruta.replace("\\", "/")
            return n.split("asic_reg/", 1)[1] \
                if "asic_reg/" in n else n

        r2 = caso_2()
        adapt = {(i["ip_block"], int(i["address"], 16)):
                 [(_sufijo(d["file"]), d["line"],
                   int(d["value"], 16))
                  for d in i["definitions"]]
                 for i in r2["results"]}
        v("T1622 el adaptador coincide con el oracle de headers: "
          "mismos (bloque, direccion)",
          set(adapt) == set(grupos),
          (sorted(adapt), sorted(grupos)))
        for clave in grupos:
            oracle_ds = sorted(grupos[clave])
            adapt_ds = sorted(adapt.get(clave, []))
            v("T1623 definiciones de %s/%s coinciden con el oracle "
              "(mismos file:line:value)" % clave,
              adapt_ds == oracle_ds,
              (adapt_ds, oracle_ds))

        # Las tres instancias nunca se fusionan: direcciones
        # distintas, definiciones disjuntas.
        dirs = [i["address"] for i in r2["results"]]
        v("T1624 homonimos no colisionan: 3 direcciones distintas",
          len(set(dirs)) == 3, dirs)
        todos = [d["file"] for i in r2["results"] for d in
                 i["definitions"]]
        v("T1625 las definiciones de las tres identidades son "
          "disjuntas (ningun file compartido)",
          len(todos) == len(set(todos)) == 11, len(set(todos)))

        # La direccion de cada identidad se verifica contra el
        # VALOR del header, no contra el nombre.
        for i in r2["results"]:
            valores = {int(d["value"], 16) for d in i["definitions"]}
            v("T1626 %s: todas sus definiciones valen %s (la "
              "identidad es el valor, no el nombre)"
              % (i["ip_block"], i["address"]),
              valores == {int(i["address"], 16)}, valores)


# ---------------------------------------------------------------------------
# G4: REGRESION DE INTERFACES CONSUMIDAS (subproceso LOCAL)
# ---------------------------------------------------------------------------

def g4_regresion_interfaces() -> None:
    # reg_resolve sigue respondiendo (es la capa nativa que el
    # adaptador consume). Subproceso local, sin red.
    if not os.path.isfile(REG_RESOLVE):
        v("T1627 reg_resolve.py existe", False, REG_RESOLVE)
        return
    p = subprocess.run(
        [sys.executable, REG_RESOLVE, "--kernel", KERNELBUILD,
         "--reg", "mmATC_L2_CNTL", "--gfx", "gfx_8_0", "--json"],
        cwd=ROOT, capture_output=True, text=True, timeout=120)
    v("T1627 reg_resolve responde (rc=0)", p.returncode == 0,
      p.stderr[:200])
    try:
        d = json.loads(p.stdout)
        res = d["results"][0]
        v("T1627 reg_resolve: 11 definiciones, conflict, 3 "
          "candidatos",
          len(res.get("definitions", [])) == 11
          and res.get("conflict") is True
          and res.get("candidates") == ["0x640", "0x800", "0xcd5"],
          (len(res.get("definitions", [])), res.get("conflict"),
           res.get("candidates")))
        v("T1627 reg_resolve: chosen = gmc_8_1_d.h:539 (0xcd5)",
          res.get("chosen", {}).get("rel", "").endswith(
              "gmc_8_1_d.h")
          and res.get("chosen", {}).get("line") == 539,
          res.get("chosen"))
    except (ValueError, KeyError, IndexError) as e:
        v("T1627 reg_resolve: JSON parseable con results", False, e)

    # Ausencia nativa intacta
    p2 = subprocess.run(
        [sys.executable, REG_RESOLVE, "--kernel", KERNELBUILD,
         "--reg", "mmZZZ_NO_EXISTE_ESTE_REG", "--gfx", "gfx_8_0",
         "--json"],
        cwd=ROOT, capture_output=True, text=True, timeout=120)
    try:
        d2 = json.loads(p2.stdout)
        v("T1628 reg_resolve: PROVEN_ABSENT_EN_ASIC_REG intacto "
          "para sujeto inexistente",
          d2["results"][0]["verdict"] == "PROVEN_ABSENT_EN_ASIC_REG",
          d2["results"][0].get("verdict"))
    except (ValueError, KeyError, IndexError) as e:
        v("T1628 reg_resolve: ausencia intacta", False, e)

    # dispatch: el adaptador esta registrado y su probe responde
    a = dispatch.ADAPTERS.get("defuse")
    v("T1629 dispatch: ADAPTERS['defuse'] registrado", a is not None)
    if a is None:
        return
    v("T1629 dispatch: cmd apunta al adaptador",
      a.cmd == ["rxre/adapters/lachesis_defuse.py"]
      and os.path.isfile(a.path), a.cmd)
    v("T1629 dispatch: probe es --selftest", a.probe == ["--selftest"])
    argv = a.build({"target": "mmATC_L2_CNTL", "intent": "def-use"})
    v("T1629 dispatch: build traduce target a --subject",
      "--subject" in argv and "mmATC_L2_CNTL" in argv
      and "--intent" in argv and "def-use" in argv
      and "--json" in argv and "--kernel" in argv, argv)
    pr = a.run(a.probe, timeout=60)
    v("T1629 dispatch: probe --selftest rc=0 (la capacidad "
      "responde)",
      pr["rc"] == 0 and not pr.get("timeout"), pr["stderr"][:200])

    # capabilities: la intencion se resuelve
    nombres = [c["capability"] for c in caps.CAPACIDADES]
    v("T1630 capabilities: value.defuse registrada",
      "value.defuse" in nombres)
    resueltas = caps.resolver(
        "que valores definen y consumen adev en gmc_v8_0_gart_enable")
    v("T1630 capabilities: la pista 'definen/consumen' resuelve a "
      "value.defuse",
      resueltas.get("resolved") == "value.defuse", resueltas)

    # engine: el pipeline existe y apunta a defuse
    v("T1631 engine: Pipelines['value.defuse'] = [dataflow/defuse]",
      engine.Pipelines.get("value.defuse") ==
      [{"step": "dataflow", "op": "defuse", "needs": ["target"]}],
      engine.Pipelines.get("value.defuse"))

    # normalize: de_defuse preserva el estado epistemico y puentea
    # la ausencia acotada
    contrato = caso_2()
    norm = N.de_defuse(contrato)
    v("T1632 normalize.de_defuse: una fila por resultado",
      len(norm) == 3, len(norm))
    v("T1632 normalize.de_defuse: status lleva el estado "
      "epistemico",
      all(r["status"] == "proven" for r in norm),
      [r["status"] for r in norm])
    v("T1632 normalize.de_defuse: raw conserva state y las "
      "definiciones",
      all(r["raw"].get("state") == "PROVEN" and "definitions" in
          r["raw"] for r in norm))
    aus = N.de_defuse(caso_6())
    v("T1633 normalize.de_defuse: caso6 no produce filas (empty "
      "con causa en el envelope)", aus == [])
    contrato6 = lad.Defuse(native=CASO6_NATIVE, provider=CASO6_PROV,
                           grafo="fixture://lachesis").consultar(
                               "def-use", "mmZZZ_NO_EXISTE_ESTE_REG")
    v("T1633 el veredicto de ausencia viaja en layers.identity "
      "(el envelope lo expone en evidence)",
      contrato6["layers"]["identity"]["verdict"] ==
      "PROVEN_ABSENT_EN_ASIC_REG")

    # Handler: el envelope es el acordado, y un error del adaptador
    # NUNCA se convierte en empty
    _handler_contrato_ok()


class _AdaptadorFalso:
    """Doble del Adapter de dispatch para el handler."""

    def __init__(self, resultado: Dict[str, Any]) -> None:
        self.name = "defuse"
        self.cmd = ["rxre/adapters/lachesis_defuse.py"]
        self.probe = ["--selftest"]
        self.summary = "doble"
        self.stage = 4
        self._resultado = resultado

    def build(self, a: Dict[str, Any]) -> List[str]:
        return ["--intent", a.get("intent", "def-use"),
                "--subject", a.get("target", "")]

    @property
    def path(self) -> str:
        # La misma ruta que el adaptador real: _tool_used
        # la lee para la provenance del envelope.
        return os.path.join(ROOT, "tools", "rxre", "adapters",
                            "lachesis_defuse.py")

    def run(self, args: List[str],
            timeout: int = 300) -> Dict[str, Any]:
        r = dict(self._resultado)
        r["argv"] = args
        return r


def _ejecutar_handler(contrato: Dict[str, Any], rc: int,
                      stdout_extra: str = "") -> Tuple[Dict[str, Any],
                                                       int]:
    salida = json.dumps(contrato, default=str) + stdout_extra
    falso = _AdaptadorFalso({"rc": rc, "stdout": salida,
                             "stderr": ""})
    original = dispatch.ADAPTERS.get("defuse")
    dispatch.ADAPTERS["defuse"] = falso  # type: ignore[assignment]
    try:
        return handlers.defuse({"target": "mmATC_L2_CNTL",
                                "intent": "def-use"})
    finally:
        if original is not None:
            dispatch.ADAPTERS["defuse"] = original  # type: ignore[assignment]


def _handler_contrato_ok() -> None:
    contrato = caso_2()
    env, rc = _ejecutar_handler(contrato, 0)
    v("T1634 handler: caso2 envuelve en ST_OK (rc=0)",
      env["status"] == E.ST_OK and rc == 0, (env["status"], rc))
    v("T1634 handler: los 3 resultados viajan al envelope",
      len(env["results"]) == 3, len(env["results"]))
    v("T1634 handler: las capas viajan en evidence",
      {e["kind"] for e in env["evidence"]} >=
      {"capa_identity", "capa_provider", "capa_dataflow"},
      env["evidence"])
    v("T1634 handler: la procedencia declara reg_resolve + lachesis "
      "por CLI",
      {p["tool"] for p in env["provenance"]} ==
      {"reg_resolve.py", "lachesis"}, env["provenance"])
    v("T1634 handler: limitations del adaptador viajan",
      any("NO modela bloques de IP" in x for x in env["limitations"]),
      env["limitations"])

    # Empty: el adaptador dice por que
    contrato6 = caso_6()
    env6, rc6 = _ejecutar_handler(contrato6, 0)
    v("T1635 handler: caso6 es ST_EMPTY (rc=0), NO ST_ERROR",
      env6["status"] == E.ST_EMPTY and rc6 == 0,
      (env6["status"], rc6))
    v("T1635 handler: empty lleva la causa en limitations "
      "(obligatorio)",
      bool(env6["limitations"]), env6["limitations"])

    # Error del adaptador: NUNCA empty
    err = {"tool": "lachesis_defuse.py", "version": "1.0.0",
           "operation": "defuse", "intent": "def-use",
           "subject": "mmATC_L2_CNTL",
           "error": {"kind": "error", "class": "ErrorDeProveedor",
                     "detail": "lachesis rc=3: boom"},
           "layers": {}, "results": [],
           "limitations": ["ErrorDeProveedor: lachesis rc=3: boom"],
           "tools_used": []}
    env_e, rc_e = _ejecutar_handler(err, 1)
    v("T1636 handler: error del proveedor es ST_ERROR (rc=1), "
      "NUNCA ST_EMPTY",
      env_e["status"] == E.ST_ERROR and rc_e == 1,
      (env_e["status"], rc_e))
    v("T1636 handler: el detalle del error viaja en limitations",
      any("boom" in x for x in env_e["limitations"]))

    # Blocked: precondicion
    blocked = {"tool": "lachesis_defuse.py", "version": "1.0.0",
               "operation": "defuse", "intent": "def-use",
               "subject": "mmATC_L2_CNTL",
               "error": {"kind": "blocked",
                         "detail": "falta grafo o corpus"},
               "layers": {}, "results": [],
               "limitations": ["falta grafo o corpus"],
               "tools_used": []}
    env_b, rc_b = _ejecutar_handler(blocked, 2)
    v("T1637 handler: precondicion es ST_BLOCKED (rc=2)",
      env_b["status"] == E.ST_BLOCKED and rc_b == 2,
      (env_b["status"], rc_b))

    # Contrato roto del adaptador: no se envuelve
    roto = {"tool": "lachesis_defuse.py", "intent": "def-use"}
    env_r, rc_r = _ejecutar_handler(roto, 0)
    v("T1638 handler: contrato del adaptador roto es ST_ERROR, no "
      "se envuelve lo que no se valido",
      env_r["status"] == E.ST_ERROR and rc_r == 1,
      (env_r["status"], rc_r))

    # Salida no JSON
    env_j, rc_j = _ejecutar_handler({"no": "json"}, 0,
                                     stdout_extra="basura")
    v("T1639 handler: salida no JSON es ST_ERROR",
      env_j["status"] == E.ST_ERROR, env_j["status"])

    # Timeout del transporte
    falso = _AdaptadorFalso({"rc": None, "stdout": "",
                             "stderr": "timeout a los 900s",
                             "timeout": True})
    original = dispatch.ADAPTERS.get("defuse")
    dispatch.ADAPTERS["defuse"] = falso  # type: ignore[assignment]
    try:
        env_t, rc_t = handlers.defuse({"target": "mmATC_L2_CNTL"})
    finally:
        if original is not None:
            dispatch.ADAPTERS["defuse"] = original  # type: ignore[assignment]
    v("T1640 handler: timeout es ST_ERROR (rc=1)",
      env_t["status"] == E.ST_ERROR and rc_t == 1,
      (env_t["status"], rc_t))


# ---------------------------------------------------------------------------

def main() -> int:
    with _parche_subproceso():
        g1_seis_casos()
        g2_matriz_de_errores()
        g3_discriminante_mmio()
    g4_regresion_interfaces()

    print("\n" + "=" * 64)
    print("REPORTE RXRE-1630: adaptador lachesis_defuse")
    print("=" * 64)
    print("verificados: %d" % checks)
    if fails:
        print("FALLOS (%d):" % len(fails))
        for f in fails:
            print("  [FALLA] %s" % f)
        return 1
    print("TODO VERDE (%d)" % checks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
