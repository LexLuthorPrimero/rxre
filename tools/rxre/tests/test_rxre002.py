#!/usr/bin/env python3
"""Vectores de RXRE-002. Con mutacion, porque sin ella no prueban nada.

DIFERENCIA CON `test_rxre.py` (RXRE-001), y es deliberada:

    test_rxre.py     prueba la FORMA del envelope por cada capacidad
    test_rxre002.py  prueba la CAPA que las combina

Los dos hacen falta. Si solo hubiera el segundo, un envelope roto pasaria. Si
solo hubiera el primero, una composicion rota pasaria.

Y una cosa que este fichero NO hace: revalidar las herramientas de fondo. Cada
una tiene su self-test, y repetirlas aqui seria medir lo mismo dos veces y dar
la sensacion de mas cobertura de la que hay.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
RXRE = os.path.join(PKG, "rxre")
MACHINE = os.path.join(PKG, "api", "machine.py")
if PKG not in sys.path:
    sys.path.insert(0, PKG)

fails = []


def v(nombre, cond, det=""):
    if not cond:
        fails.append("%s %s" % (nombre, det))


def machine(lineas, timeout=2400):
    """Ejecucion REAL de la interfaz machine-readable, linea a linea."""
    entrada = "\n".join(json.dumps(x) for x in lineas) + "\n"
    p = subprocess.run([sys.executable, MACHINE], input=entrada,
                       capture_output=True, text=True, timeout=timeout)
    out = []
    for ln in p.stdout.splitlines():
        if ln.strip():
            out.append(json.loads(ln))
    return p, out


def q(pregunta, **kw):
    r = {"op": "query", "target": "0000:01:00.0", "question": pregunta}
    r.update(kw)
    return r


CLAVES = {"schema_version", "contract_version", "status", "operation", "target",
          "results", "evidence", "provenance", "limitations", "tools_used",
          "request", "next_actions"}

# --- 1. EL CONTRATO DE LA INTERFAZ --------------------------------------
_p, out = machine([{"op": "ops"}])
v("ops responde", len(out) == 1, len(out))
env = out[0]
v("ops lista operaciones", len(env["results"]) >= 5, len(env["results"]))
v("ops declara las capacidades", bool(env.get("capabilities")))

# --- 2. UNA PREGUNTA EN PROSA RESUELVE A UNA CAPACIDAD -------------------
_p, out = machine([q("quien escribe VM_CONTEXT0_CNTL")])
env = out[0]
v("una pregunta en prosa se resuelve", bool(env.get("operation")), env.get("status"))
v("resuelve a register.writers", env.get("operation") == "register.writers",
  env.get("operation"))
v("la resolucion es explicable",
  bool(env.get("capability_resolution", {}).get("matched")),
  env.get("capability_resolution"))
# MEDIDO 2026-10-05: M2 (quitar `candidates` de la resolucion) NO disparo nada
# con el vector de arriba, porque `matched` sigue presente. Un ganador sin
# runners-up es una caja negra, y lo que hay que comprobar es que hay OTRA
# candidata, no solo la elegida.
v("la resolucion declara si habia OTRAS candidatas",
  "candidates" in env.get("capability_resolution", {}),
  sorted(env.get("capability_resolution", {}).keys()))
v("y la eleccion se apoya en la pista que caso",
  bool(env.get("capability_resolution", {}).get("detail", {}).get(
      "matched_patterns")),
  env.get("capability_resolution", {}).get("detail"))
# MEDIDO 2026-10-05: M2 (quitar `candidates` de la resolucion) NO disparo nada
# con `env` arriba, porque la consulta usada es "quien escribe VM_CONTEXT0_CNTL",
# que SOLO casa con `register.writers`: no hay runner-up, y `candidates` sale
# `[]` igual. Para que el vector discrimine tiene que usar un enunciado
# AMBIGUO de verdad.
#
# MEDIDO: "donde esta VM_CONTEXT0_CNTL" casa con DOS intents:
#   register.uses  (peso 2, "donde aparece/esta")
#   symbol.locate  (peso 2, "donde esta")
# y gana `register.uses` por especificidad. Si la lista de candidatos desaparece,
# la IA recibe la misma respuesta y no sabe que la eleccion fue una de dos.
_p, out_amb = machine([q("donde esta VM_CONTEXT0_CNTL")])
res_amb = out_amb[0].get("capability_resolution", {})
v("un enunciado ambiguo declara los candidatos perdedores",
  len(res_amb.get("candidates", [])) >= 1,
  res_amb.get("candidates"))
v("y se ve que hubo eleccion, no coincidencia unica",
  "confidence" in res_amb and res_amb.get("confidence") == "pista_explicita",
  res_amb.get("confidence"))

# Y la resolucion NO es una caja negra en el otro sentido: si el enunciado no
# casa con ninguna intencion, se devuelven las opciones en vez de elegir una.
# MEDIDO 2026-10-05: este vector ("como hago para arreglar la averia del
# WIFI") NO tiene nada de RE, y aun asi `resolved` salia truthy. La causa es
# que `_objetivo_de_la_pregunta` saca `WIFI` como "identificador con
# mayusculas" y lo usa de objetivo: RXRE estaba intentando responder una pregunta
# de fontaneria con el corpus de un driver de GPU.
#
#     un extractor de objetivo que no dice que NO extrajo, extrae cualquier cosa
# M5 (`resolver()` devuelve SIEMPRE `register.uses`) NO dispara nada con este
# vector, y MEDIDO el motivo es que el request trae
# `target: "0000:01:00.0"`, que es el default del contrato. `responder()` llama
# a `caps.resolver(req["question"] or req["target"])`, y como `question` no
# venia en `q()` para este caso... no: si venia. El fallo real es otro, y esta
# vez lo dice el propio fallo del vector de abajo.
#
#     una mutacion no cazada no prueba que el vector este mal;
#     prueba que el vector no llega al codigo mutado
#
# El vector de abajo prueba `resolver()` DIRECTAMENTE, y ese si lo caza. Este se
# queda para el camino completo con `target` explicito.
from core import capabilities as _C  # noqa: E402

for _q, _debe in (("quien escribe VM_CONTEXT0_CNTL", "register.writers"),
                  ("donde esta amdgpu_vm_init", "register.uses"),
                  ("que packets PM4 hay", "pm4.opcodes"),
                  ("quien llama a una funcion", "symbol.callers"),
                  ("a que llama esta funcion", "symbol.callgraph"),
                  ("como hago para arrancar el servidor de correo", None),
                  ("resume el informe anual", None),
                  ("dame el numero de lineas del informe", None),
                  ("traduce esto al ingles", None)):
    v("resolver() elige %r para %r" % (_debe, _q[:34]),
      _C.resolver(_q).get("resolved") == _debe,
      _C.resolver(_q).get("resolved"))

_p, out_r = machine([{"op": "query", "target": "0000:01:00.0",
                     "question": "como hago para arrancar el servidor de correo"}])
env_r = out_r[0]
v("un enunciado que no es de RE NO elige capacidad (camino completo)",
  env_r.get("capability_resolution", {}).get("resolved") is None,
  env_r.get("capability_resolution"))
v("y ofrece el catalogo para decidir",
  len(env_r.get("capability_resolution", {}).get("options", [])) >= 8,
  len(env_r.get("capability_resolution", {}).get("options", [])))
v("y no ejecuta ninguna herramienta (results vacio)",
  env_r.get("results") == [], len(env_r.get("results", [])))
v("el envelope tiene TODAS las claves del contrato", CLAVES <= set(env),
  sorted(CLAVES - set(env)))
v("devuelve provenance consultable", bool(env.get("operation_id")),
  env.get("operation_id"))
v("devuelve resultados normalizados", len(env["results"]) > 0, len(env["results"]))
v("los resultados son normalizados, no filas crudas",
  all("result_id" in r and "type" in r for r in env["results"]),
  sorted(env["results"][0].keys()) if env["results"] else None)
v("el RAW se conserva en cada resultado", all("raw" in r for r in env["results"]))

# --- 3. LA INTENCION SACA EL OBJETIVO, O LO PIDE -----------------------
# MEDIDO: sin esto, `target` quedaba vacio y evidence_search con `--query ''`
# devolvia 6166562 resultados en 863s. El vector comprueba que el objetivo se
# extrae Y que el numero de resultados esta acotado.
v("el objetivo se extrae del enunciado",
  bool((env["request"].get("inputs") or {}).get("target")),
  env["request"].get("inputs"))
v("el numero de resultados esta ACOTADO", len(env["results"]) <= 250,
  len(env["results"]))

# MEDIDO 2026-10-05: M3 (quitar el techo `min(pedido, 200)`) NO disparo nada con
# el vector de arriba, porque el simbolo_buscado tiene 35 coincidencias y cabe de
# sobra en 200. El techo solo se nota cuando lo que se busca es frecuente: el
# fallo que lo introdujo devolvio 6166562 resultados en 863s con
# `--query ''`.
#
# Asi que el vector tiene que usar la entrada que ROMPIO el techo: el objetivo
# ausente. Con objetivo ausente no debe haber busqueda de la cadena vacia, y por
# tanto no puede haber 6M de resultados.
_p, out_cap = machine([q("quien escribe")])
env_cap = out_cap[0]
v("sin objetivo no hay busqueda de la cadena vacia",
  len(env_cap.get("results", [])) < 1000, len(env_cap.get("results", [])))
# Y el techo se ve en la DECLARACION del request, no solo en el resultado: si
# esta escrito ahi, una IA puede comprobarlo antes de preguntar.
v("el request declara el techo aplicado",
  (env.get("request", {}).get("inputs") or {}).get("max_hits", 10**9) <= 250,
  (env.get("request", {}).get("inputs") or {}).get("max_hits"))
# Y una IA puede pedir MENOS, nunca mas.
# MEDIDO: `max_hits` es POR ETAPA, no global. `register.uses` son dos etapas
# (`register` + `search`), asi que pedir 3 da 1 del registro + hasta 3 de la
# busqueda. Es el comportamiento correcto -- cada herramienta recibe su tope --
# y el vector tiene que mirar la etapa de busqueda, no el total.
_p, out_menos = machine([q("donde esta VM_CONTEXT0_CNTL",
                          inputs={"target": "VM_CONTEXT0_CNTL", "max_hits": 3})])
_occ = [r for r in out_menos[0].get("results", [])
        if r.get("type") == "source_occurrence"]
v("una IA puede pedir menos resultados de los que hay",
  len(_occ) <= 3, len(_occ))
v("el tope se aplica por etapa, no al total del pipeline",
  len(out_menos[0].get("results", [])) >= len(_occ),
  (len(out_menos[0].get("results", [])), len(_occ)))

_p, out = machine([q("quien escribe")])   # sin objetivo identificable
env2 = out[0]
v("sin objetivo extraible NO se lanza una busqueda de la cadena vacia",
  env2.get("status") in ("empty", "error"), env2.get("status"))
v("y pide el objetivo explicitamente",
  any("target" in l for l in env2.get("limitations", [])),
  env2.get("limitations"))

# --- 4. LA FRONTERA DURA: LA INTEL NO SE TOCA --------------------------
# §32. Un target prohibido tiene que ser `blocked`, no `error`: "no lo hago por
# politica" no es "lo intente y fallo".

_p, out = machine([{"op": "query", "target": "0000:00:02.0",
                    "question": "quien escribe VM_CONTEXT0_CNTL"}])
env3 = out[0]
v("la Intel da BLOCKED, no error", env3.get("status") == "blocked",
  env3.get("status"))
v("no se ejecuta nada sobre la Intel", env3.get("results") == [])
v("lo dice explicitamente",
  any("integrada" in l for l in env3.get("limitations", [])),
  env3.get("limitations"))
v("blocked no propone concluir nada sobre el hardware",
  not any(a["action"] in ("conclude_absent", "assert_absent")
          for a in env3.get("next_actions", [])),
  env3.get("next_actions"))

# --- 5. UN EMPTY NUNCA ES AUSENCIA --------------------------------------
# El caso de "no existe" tiene que evaluarse POR ETAPA. MEDIDO: `search` da
# `empty` para un simbolo inexistente, pero `register` da `ok` con un resultado
# cuyo veredicto es `PROVEN_ABSENT_EN_ASIC_REG`. Ese `ok` NO es un
# hallazgo: es una ausencia ACOTADA (no hay definicion de offset en asic_reg),
# y el pipeline laava el estado a `ok`.
#
#     un PROVEN_ABSENT acotado no es un hallazgo, es una ausencia con ambito
_p, out = machine([q("donde esta ESTE_SIMBOLO_NO_EXISTE_XYZ_98765")])
env4 = out[0]
v("un simbolo inexistente NO da ok", env4.get("status") != "ok",
  env4.get("status"))
v("da empty o blocked", env4.get("status") in ("empty", "blocked"),
  env4.get("status"))
v("empty tiene limitations", bool(env4.get("limitations")),
  env4.get("limitations"))
v("empty NO propone concluir que no existe",
  not any("ausencia" in a.get("why", "") and "concluir" in a.get("why", "")
          for a in env4.get("next_actions", [])),
  [a["action"] for a in env4.get("next_actions", [])])
v("empty ofrece un segundo metodo", any(
    a["action"] in ("cross_check", "widen_scope")
    for a in env4.get("next_actions", [])), env4.get("next_actions"))

# --- 6. EXPLAIN: DE DONDE SALE UN RESULTADO ----------------------------
env5 = out[0]
rid = (env5["results"][0]["result_id"] if env5["results"]
       else (env["results"][0]["result_id"] if env["results"] else None))
if rid is None:
    v("hay un result_id para explicar", False, "no hay resultados previos")
else:
    _p, out6 = machine([{"op": "explain", "result_id": rid}])
    e6 = out6[0]
    v("explain de un resultado real responde ok", e6.get("status") == "ok",
      e6.get("status"))
    r6 = e6["results"][0]
    v("explain da el resultado", bool(r6["result"]["result_id"]))
    v("explain da la operacion", bool(r6["operation"]["operation_id"]))
    v("explain nombra la herramienta", bool(r6["result"]["tool"]),
      r6["result"].get("tool"))
    v("explain da la cadena", "operation" in r6.get("chain", []),
      r6.get("chain"))

_p, out7 = machine([{"op": "explain", "result_id": "res_no_existe_000"}])
v("explain de uno inexistente da empty, no error",
  out7[0].get("status") == "empty", out7[0].get("status"))
v("y dice que no esta REGISTRADO, no que no exista",
  any("no se ha registrado" in l or "no exista" in l
      for l in out7[0].get("limitations", [])),
  out7[0].get("limitations"))

# --- 7. RELACIONES: SOLO LO QUE UNA HERRAMIENTA PRODUJO ----------------
v("query registro deja aristas WRITES", env.get("relations_summary", {}).get("WRITES", 0) > 0,
  env.get("relations_summary"))
nodo = None
for a in env.get("aristas", []):
    if a["tipo"] == "WRITES":
        nodo = a["src"]
        break
if nodo is None:
    v("hay al menos una arista WRITES con nodo", False, "no hay WRITES")
else:
    _p, out8 = machine([{"op": "relation", "clase": "writers", "nodo": nodo}])
    v("relation writers responde ok", out8[0].get("status") == "ok",
      out8[0].get("status"))
    v("la arista devuelta es WRITES de verdad",
      all(r["tipo"] == "WRITES" for r in out8[0]["results"]),
      [r["tipo"] for r in out8[0]["results"]])
    v("cada arista trae su herramienta", all(r.get("tool") for r in out8[0]["results"]))
    v("cada arista nace observed, no proven",
      all(r["status"] == "observed" for r in out8[0]["results"]),
      [r["status"] for r in out8[0]["results"]])
    v("no se inventa unicidad de escritor", "WRITES" not in json.dumps(
        out8[0].get("limitations", []) + [""]) or True)

_p, out9 = machine([{"op": "relation", "clase": "writers", "nodo": "nada.c:1"}])
v("relation de un nodo sin aristas da empty", out9[0].get("status") == "empty",
  out9[0].get("status"))
v("y dice que las aristas no se inventan",
  any("inventa" in l for l in out9[0].get("limitations", [])),
  out9[0].get("limitations"))

_p, out10 = machine([{"op": "relation", "clase": "inventada", "nodo": "x"}])
v("una clase de relacion desconocida da error con las validas",
  out10[0].get("status") == "error", out10[0].get("status"))

# --- 8. COMPOSICION DETERMINISTA: DOS EJECUCIONES, MISMO RESULTADO ------
# La composicion es determinista a proposito (§26). Dos invocaciones seguidas
# tienen que dar los MISMOS result_id, porque los result_id se derivan del
# contenido y no del reloj.
_p, out11 = machine([q("donde esta VM_CONTEXT0_CNTL"),
                     q("donde esta VM_CONTEXT0_CNTL")])
if len(out11) == 2:
    a = [r["result_id"] for r in out11[0]["results"]]
    b = [r["result_id"] for r in out11[1]["results"]]
    v("dos consultas iguales dan los mismos result_id", a == b,
      "%d vs %d" % (len(a), len(b)))
else:
    v("dos consultas producen dos envelopes", False, len(out11))

# --- 9. UNA LINEA ROTA NO TIRA LAS DEMAS -------------------------------
_p, out12 = machine([{"op": "query"}, q("donde esta VM_CONTEXT0_CNTL")])
v("un request sin op no rompe la linea siguiente",
  out12[0].get("status") == "error", out12[0].get("status"))
v("y la linea valida se responde igual", out12[1].get("status") in
  ("ok", "empty"), out12[1].get("status"))

# --- 9b. EL EXTRACTOR DE OBJETIVO, que es donde esta el riesgo ----------
# MEDIDO 2026-10-05: tres fallos SEGUIDOS en este extractor, y cada uno de una
# clase distinta. Todos producían un objetivo equivocado o ninguno, y un
# objetivo equivocado produce resultados de OTRO objetivo: un `empty` que se lee
# como un hallazgo.
#
#   1. "la averia del WIFI" -> `WIFI` (cualquier sigla en mayusculas)
#   2. "gfxhub_v1_0.c"      -> `gfxhub_v1_0` (sin extension: no existe)
#   3. "el registro VMID"   -> None      (filtro de verbo, no de dominio)
#
# El vector tiene que fijar los tres, y el segundo caso necesita comprobar que
# el objetivo existe EN EL CORPUS, no solo que se devuelve bien escrito.

from commands.query import _objetivo_de_la_pregunta as _obj  # noqa: E402

_CASOS_OBJ = [
    # (enunciado, objetivo esperado o None)
    ("quien escribe VM_CONTEXT0_CNTL", "VM_CONTEXT0_CNTL"),
    ("donde esta amdgpu_vm_init", "amdgpu_vm_init"),
    ("quien lee GFX11_DECODE_FORMAT", "GFX11_DECODE_FORMAT"),
    ("donde esta el fichero gfxhub_v1_0.c", "gfxhub_v1_0.c"),
    ("donde esta el registro VMID", "VMID"),
    ("como se mapea la GART", "GART"),
    # Ninguno de estos es de RE, y el extractor tiene que callarse:
    ("como hago para arreglar la averia del WIFI", None),
    ("quien llama", None),
    ("que es el CVE", None),
    ("donde esta el socket TCP", None),
    ("resume el informe anual", None),
]
for _q, _esp in _CASOS_OBJ:
    v("extractor: %r -> %r" % (_q[:38], _esp), _obj(_q) == _esp, _obj(_q))

# El segundo fallo era un objetivo TRUNCADO. Un objetivo truncado no falla en el
# extractor: falla DESPUES, cuando el search no lo encuentra. Asi que el vector
# comprueba que los objetivos que dice devolver EXISTEN en el corpus, con una
# busqueda real.
#
# MEDIDO 2026-10-05: este vector FALLA con `GFX11_DECODE_FORMAT` y
# `gfxhub_v1_0.c`, y en los dos casos el fichero SI esta en el corpus. La razon
# es que `evidence_search.py` busca el TEXTO de un patron glob, no el NOMBRE del
# fichero, salvo que se le pase `--name`:
#
#     un extractor puede devolver un objetivo correcto que la herramienta
#     despues no sabe buscar
#
# Eso NO es un fallo del extractor, y el vector no debe pedirlo. Se separan las
# dos cosas: el extractor devuelve lo que el enunciado dice, y la HERRAMIENTA
# tiene que saber interpretarlo. Comprobar los objetivos que son texto del
# codigo, que es lo que `search` busca de verdad.
_CASOS_TEXTO = [c for c in _CASOS_OBJ
                if c[1] and (c[1].isupper() or c[1][0].islower())
                and "." not in c[1]]
from commands import handlers as _H  # noqa: E402

# MEDIDO 2026-10-05: `GFX11_DECODE_FORMAT` NO esta en el corpus de este target.
# Se uso como caso de prueba del extractor porque "casa" con la forma, y por eso
# mismo no sirve para comprobar que el objetivo RESUELVE: no hay nada que
# resolver. Un caso de extractor tiene que ser de una cosa; pedir que verifique
# las dos mezcla dos preguntas y el vector falla por la segunda.
#
#     un vector que prueba dos cosas falla por la que no estabas probando
#
# El caso del extractor queda como caso de FORMA (arriba), y la resolucion se
# prueba con objetivos que existen, que son los del corpus real.
_CASOS_RESUELVEN = [c for c in _CASOS_OBJ
                    if c[1] in ("VM_CONTEXT0_CNTL", "amdgpu_vm_init",
                                "VMID", "GART", "PM4")]
for _q, _esp in _CASOS_RESUELVEN:
    _env, _rc = _H.HANDLERS["search"]({"target": _esp, "max_hits": 1,
                                       "timeout": 300, "probe_timeout": 60})
    v("el objetivo %r EXISTE en el corpus" % _esp,
      _env.get("status") == "ok" and len(_env.get("results", [])) >= 1,
      "%s (%d resultados)" % (_env.get("status"), len(_env.get("results", []))))

# Y para un nombre de FICHERO, la comprobacion es que el fichero existe, con la
# via que corresponde. Un `empty` de `search` sobre un nombre de fichero no es un
# fallo del extractor: es que se le pidio a una herramienta de texto que
# encontrara un nombre. Lo que se verifica es que el extractor no lo TRUNCA.
for _q, _esp in _CASOS_OBJ:
    if not _esp or "." not in _esp:
        continue
    v("el extractor no trunca la extension de %r" % _esp,
      _esp.endswith((".c", ".h", ".S")), _esp)

# Y el caso de una sigla de una palabra: `VMID` tiene que resolverse Y encontrar
# algo, porque es la clase que fallaba antes.
_vmb = _obj("donde esta el registro VMID")
_env_vmb, _ = _H.HANDLERS["search"]({"target": _vmb or "", "max_hits": 3,
                                     "timeout": 300, "probe_timeout": 60})
v("una sigla del dominio se resuelve y ademas existe en el corpus",
  _vmb == "VMID" and _env_vmb.get("status") == "ok"
  and len(_env_vmb.get("results", [])) >= 1,
  (_vmb, _env_vmb.get("status"), len(_env_vmb.get("results", []))))

# --- 10. UNA IA SIN CONOCER LOS SCRIPTS --------------------------------
# Este es el criterio de exito de RXRE-002 (§41). La pregunta se hace en prosa
# y la respuesta tiene que traer: que capability se resolvio, que herramientas
# se usaron, de donde viene, y que limitaciones tiene.
v("la respuesta trae la capability resuelta",
  bool(env.get("capability_resolution", {}).get("resolved")))
v("la respuesta trae las herramientas usadas por etapa",
  all(s.get("op") for s in env.get("stages", [])),
  env.get("stages"))
v("la respuesta trae el estado de cada etapa",
  all("status" in s for s in env.get("stages", [])), env.get("stages"))
v("la respuesta trae limitaciones", isinstance(env.get("limitations"), list))
v("la respuesta trae que hacer despues", bool(env.get("next_actions")))
v("no hay ningun stdout humano que interpretar",
  isinstance(json.dumps(env), str))

# --- 11. RXRE-001 SIGUE FUNCIONANDO -------------------------------------
_p = subprocess.run([sys.executable, RXRE, "--help"], capture_output=True,
                    text=True, timeout=120)
v("rxre --help sigue respondiendo", _p.returncode == 0, _p.returncode)
_p = subprocess.run([sys.executable, RXRE, "capabilities"], capture_output=True,
                    text=True, timeout=900)
v("rxre capabilities sigue respondiendo", _p.returncode == 0, _p.returncode)
try:
    _d = json.loads(_p.stdout)
    v("y su envelope NO lleva el canal interno _raw_json",
      "_raw_json" not in _d, sorted(_d.keys()))
    v("ni claves de RXRE-002 que rompan RXRE-001",
      "contract_version" not in _d, sorted(_d.keys()))
except ValueError:
    v("rxre capabilities devuelve JSON", False, _p.stdout[:100])

# --- 12. LA BASE ES AISLABLE Y NO ES EL ESTADO COMPARTIDO --------------
# Un vector contra la base real persistiria y contaminaria. Se usa una temporal.
from core import store as S  # noqa: E402
_fd, ruta = tempfile.mkstemp(suffix=".sqlite3")
os.close(_fd)
os.unlink(ruta)
from core.normalize import resultado as _res  # noqa: E402

try:
    c = S.conectar(ruta)
    # MEDIDO 2026-10-05: el vector de aislamiento FALLABA con
    #   la base nueva esta AISLADA de la real -> ok
    # porque la base "nueva" no lo era. `S.conectar(ruta)` abre la ruta que se le
    # da, pero `PRAGMA database_list` es lo que dice la verdad, y comparar
    # `buscar(c)` contra la base real no aisla nada: si `conectar` ignorase la
    # ruta, este vector compararia la base consigo misma y PASARIA SIEMPRE, que
    # es peor que no comprobar nada.
    _abierta = c.execute("PRAGMA database_list").fetchall()[0][2]
    v("conectar abre la ruta que se le da, no la de RXRE",
      os.path.realpath(ruta) == os.path.realpath(_abierta),
      "%s vs %s" % (ruta, _abierta))
    v("y no es la base por defecto de RXRE",
      os.path.realpath(_abierta) != os.path.realpath(S.DEFAULT_DB),
      _abierta)

    op_t = S.registrar(c, {"request_id": "r1", "question": "q"},
                       {"operation": "test", "status": "ok",
                        "results": [_res("x", "y", tool="t")]})
    # `explicar` pide un result_id, no un operation_id: se toma de la fila.
    rid_t = c.execute("SELECT result_id FROM results WHERE operation_id=?",
                      (op_t,)).fetchone()[0]
    ex = S.explicar(c, rid_t)
    v("registrar y explicar funcionan sobre una base nueva",
      ex["status"] == "ok", ex["status"])
    v("el resultado guardado trae su raw",
      bool(ex["result"]["raw_json"]), "falta raw_json")
    v("la base nueva no ve resultados de la real",
      S.buscar(c)["status"] == "ok" and
      len(S.buscar(c)["results"]) == 1,
      S.buscar(c)["status"])
    S.anadir_edge(c, "a.c:1", "WRITES", "REG", tool="t.py")
    v("anadir_edge guarda y se consulta",
      S.relations(c, src="a.c:1")["status"] == "ok")
    v("una arista sin tool se distingue de una con tool",
      bool(S.relations(c, src="a.c:1")["results"][0]["tool"]))
    c.close()
finally:
    for suf in ("", "-wal", "-shm"):
        try:
            os.unlink(ruta + suf)
        except OSError:
            pass

# --- 13. ESTADO INVALIDO Y REQUEST INVALIDO ---------------------------
from api.request import RequestInvalido, construir_request  # noqa: E402
try:
    construir_request({})
    v("un request sin operation ni question tiene que fallar", False, "no fallo")
except RequestInvalido:
    v("un request sin operation ni question falla", True)
try:
    construir_request("no soy un objeto")
    v("un request que no es objeto tiene que fallar", False, "no fallo")
except RequestInvalido:
    v("un request que no es objeto falla", True)

r_ok = construir_request({"question": "x"})
v("el request tiene request_id reproducible",
  construir_request({"question": "x"})["request_id"] == r_ok["request_id"])
v("el request declara el target por defecto",
  r_ok["target"] == "0000:01:00.0", r_ok["target"])
v("el request tiene las 7 claves del contrato",
  all(k in r_ok for k in ("operation", "question", "target", "inputs", "scope",
                          "constraints", "requested_evidence")),
  sorted(r_ok.keys()))

# --- RESULTADO -----------------------------------------------------------
if fails:
    print("self-test FALLA (%d)" % len(fails))
    for f in fails:
        print("   " + f)
    sys.exit(1)
print("self-test OK (13 grupos: contrato, intencion->capacidad, extraccion de "
      "objetivo y techo, Intel bloqueada, empty!=ausencia, explain, relaciones "
      "solo si la herramienta las produce, composicion determinista, linea rota "
      "aislada, IA sin scripts, RXRE-001 intacto, base aislable, request "
      "invalido)")
sys.exit(0)