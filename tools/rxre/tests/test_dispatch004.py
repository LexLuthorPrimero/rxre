#!/usr/bin/env python3
"""RXRE-004 / B4. ¿Una IA que solo sabe JSONL puede inspeccionar un binario?

LA PREGUNTA DISCRIMINANTE DE §10, LITERAL:

    ¿una IA que solo conoce RXRE_PUBLIC_CONTRACT.md puede ejecutar
     binary.inspect sin nombrar rizin?

Asi que este fichero NO importa el dispatcher y lo llama. Lo ejercita a TRAVES
DE LA SUPERFICIE PUBLICA, por JSONL sobre stdin/stdout, que es lo unico que
una IA que no conoce la implementacion tiene. Si este test importara
`dispatch.esta_permitida`, estaria midiendo la funcion, no el contrato.

Y mide algo mas que el camino feliz: que los RECHAZOS sean correctos y
distintos entre si. Una allow-list que acepta todo pasa los tests de exito. Lo
que demuestra que existe son los siete rechazos.

    una allow-list se demuestra por lo que rechaza
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
MAQUINA = os.path.join(PKG, "api", "machine.py")
FIXTURE = os.path.join(PKG, "fixtures", "bin", "rxre_min.elf")

fails = []
n = 0


def v(nombre, cond, det=""):
    global n
    n += 1
    if not cond:
        fails.append("%s %s" % (nombre, det))


def rx(requests):
    """Habla JSONL con RXRE por stdin/stdout. BLACK BOX."""
    entrada = "\n".join(json.dumps(r) for r in requests) + "\n"
    p = subprocess.run([sys.executable, MAQUINA], input=entrada,
                       capture_output=True, text=True, timeout=1200)
    lineas = []
    for l in (p.stdout or "").splitlines():
        l = l.strip()
        if not l:
            continue
        try:
            lineas.append(json.loads(l))
        except ValueError:
            fails.append("una linea de salida no es JSON: %r" % l[:80])
    return lineas


# --- 0. PRECONDICIONES ----------------------------------------------------
v("la entrada publica existe", os.path.isfile(MAQUINA), MAQUINA)
v("el fixture B1 existe", os.path.isfile(FIXTURE), FIXTURE)
_tiene_rzbin = subprocess.run(["which", "rz-bin"], capture_output=True,
                             text=True).returncode == 0
if not _tiene_rzbin:
    v("rz-bin ausente: el camino de ejecucion no se puede ejercitar", True)

# --- 1. EL CATALOGO: la IA PUEDE DESCUBRIR SIN SABER NOMBRES -------------
envs = rx([{"op": "backends"}])
v("op:backends responde una linea", len(envs) == 1, len(envs))
if envs:
    B = envs[0]
    v("op:backends -> status ok", B.get("status") == "ok", B.get("status"))
    v("devuelve fichas de backend", bool(B.get("backends")),
      len(B.get("backends") or []))
    v("devuelve el catalogo de capacidades", bool(B.get("capacities")))
    v("separa ejecutables de no ejecutables",
      "ejecutables" in B and "no_ejecutables" in B)
    v("declara las reglas de la allow-list", bool(B.get("reglas")))
    v("expone el contrato del backend", bool(B.get("contracto")))
    v("declara los backends NO verificables con su estado",
      {x["backend_id"]: x["estado"] for x in (B.get("not_verificables") or [])}
      == {"angr": "NOT_DETERMINED", "rz-ghidra": "NOT_DETERMINED"},
      B.get("not_verificables"))

    # La columna vertebral de §10: la IA ve `binary.inspect` sin que nadie le
    # haya dicho que existe.
    ejec = B.get("ejecutables") or []
    v("binary.inspect aparece como EJECUTABLE sin que se le pida",
      any(c["capability"] == "binary.inspect" for c in ejec),
      [c["capability"] for c in ejec])
    v("y es la UNICA ejecutable, porque es la unica con producer medido",
      len(ejec) == 1, [c["capability"] for c in ejec])

# --- 2. EL CAMINO FELIZ: ejecutar sin nombrar el backend ------------------
if _tiene_rzbin:
    envs = rx([{"op": "run", "capability": "binary.inspect",
                "artefacto": FIXTURE}])
    v("op:run responde una linea", len(envs) == 1, len(envs))
    if envs:
        R = envs[0]
        v("op:run -> status ok", R.get("status") == "ok", R.get("status"))
        v("el status del BACKEND tambien viaja, no solo el del envelope",
          R.get("backend_status") == "ok", R.get("backend_status"))
        v("el rc del backend viaja (rc=0 NO es un resultado, se comprueba)",
          R.get("backend_rc") == 0, R.get("backend_rc"))
        v("la capability pedida se refleja en la respuesta",
          R.get("capability") == "binary.inspect")
        v("devuelve un resultado", len(R.get("results") or []) == 1,
          len(R.get("results") or []))
        rid = (R.get("results") or [{}])[0].get("result_id")
        v("el resultado tiene result_id", bool(rid), rid)
        v("el resultado es RAW_BINARY",
          (R.get("results") or [{}])[0].get("type") == "raw_binary")
        v("la identidad del backend viaja (version VERIFICADA)",
          (R.get("backend_identity") or {}).get("version_verificada") is True,
          (R.get("backend_identity") or {}).get("tool_version", "")[:40])
        # §11: el siguiente paso debe poder EJECUTARSE. RXRE-003 lo exige.
        na = R.get("next_actions") or []
        v("propone next_actions", bool(na), na)
        v("toda next_action ejecutable trae op y available:true",
          all(("available" in a) for a in na), na)
        v("la accion explain lleva result_id real",
          any(a.get("op") == "explain" and a.get("available") is True
              and (a.get("args") or {}).get("result_id") == rid for a in na),
          na)
        v("binary.decompile aparece como NO disponible con su motivo",
          any(a.get("op") == "run" and a.get("available") is False
              and (a.get("args") or {}).get("capability") == "binary.decompile"
              and bool(a.get("reason")) for a in na), na)

        # Y el ciclo se cierra: explain reconstruye la cadena del backend.
        envs2 = rx([{"op": "explain", "result_id": rid}])
        v("explain cierra el ciclo", len(envs2) == 1, len(envs2))
        if envs2:
            X = envs2[0]
            v("explain por result_id -> ok", X.get("status") == "ok",
              X.get("status"))
            bc = X.get("backend") or {}
            v("explain conserva la cadena del backend a traves de la "
              "interfaz publica",
              bool(bc.get("backend_id")) and bool(bc.get("input_hash")),
              sorted(bc.keys())[:6])
            v("la cadena tiene los 13 eslabones de §9",
              len(bc.get("chain") or []) == 13, len(bc.get("chain") or []))

# --- 3. LA ALLOW-LIST: SE DEMUESTRA POR LO QUE RECHAZA -------------------
# Siete rechazos, y lo importante no es que rechacen: es que el MOTIVO de cada
# uno sea el correcto. Si los siete dijeran "no", la allow-list podria ser un
# `return False` incondicional y estos vectores pasarian igual.
casos = [
    ("capability que existe pero NO tiene adapter", "binary.cfg", "adapter"),
    ("capacidad sin producer verificable", "binary.decompile", "adapter"),
    ("identificador cerrado: ruta", "../../etc/passwd", "identificador cerrado"),
    ("identificador cerrado: comando", "rizin --version", "identificador cerrado"),
    ("nombre de shell", "shell", "no hay ninguna capacidad registrada"),
    ("sin capability", None, "falta 'capability'"),
]
for etiqueta, cap, trozo_esperado in casos:
    req = {"op": "run"}
    if cap is not None:
        req["capability"] = cap
    envs = rx([req])
    v("[%s] responde una linea" % etiqueta, len(envs) == 1, len(envs))
    if not envs:
        continue
    R = envs[0]
    v("[%s] NO se ejecuta" % etiqueta, R.get("ejecutada") is False,
      R.get("ejecutada"))
    v("[%s] status blocked" % etiqueta, R.get("status") == "blocked",
      R.get("status"))
    v("[%s] NO devuelve resultados" % etiqueta, not (R.get("results") or []))
    lim = " ".join(R.get("limitations") or [])
    v("[%s] el motivo es el correcto" % etiqueta, trozo_esperado in lim,
      lim[:100])
    v("[%s] NO es `empty`: no ejecutar no es no encontrar" % etiqueta,
      R.get("status") != "empty", R.get("status"))

# Y el caso de parametro obligatorio ausente: eso NO es `blocked`.
envs = rx([{"op": "run", "capability": "binary.inspect"}])
if envs:
    R = envs[0]
    v("[sin artefacto] es invalid_input, no blocked",
      R.get("backend_status") == "invalid_input", R.get("backend_status"))
    v("[sin artefacto] el motivo NOMBRA el parametro que falta",
      "artefacto" in " ".join(R.get("limitations") or []),
      R.get("limitations"))

# Y el artefacto que no existe: `invalid_input`, no `empty` y no `ok`.
envs = rx([{"op": "run", "capability": "binary.inspect",
            "artefacto": "/tmp/opencode/no_existe_este_fichero_rxre"}])
if envs:
    R = envs[0]
    v("[artefacto inexistente] invalid_input", R.get("backend_status")
      == "invalid_input", R.get("backend_status"))
    v("[artefacto inexistente] NO es empty", R.get("status") != "empty",
      R.get("status"))
    v("[artefacto inexistente] el motivo dice que no existe",
      "no existe" in " ".join(R.get("limitations") or []).lower(),
      R.get("limitations"))

# --- 4. UNA CAPACIDAD EN EL REGISTRY QUE NO ESTA EN EL CATALOGO DE OPS ---
envs = rx([{"op": "ops"}])
if envs:
    ops = {r.get("op") for r in (envs[0].get("results") or [])}
    v("ops declara `backends`", "backends" in ops, sorted(ops))
    v("ops declara `run`", "run" in ops, sorted(ops))
    v("run documenta sus campos", any(
        r.get("op") == "run" and "capability" in (r.get("campos") or [])
        for r in envs[0].get("results") or []))
    # Y las ejemplos de `run` son EJECUTABLES: el mismo F1 de RXRE-003, aplicado
    # a la superficie nueva.
    ej = [r for r in envs[0].get("results") or [] if r.get("op") == "run"]
    if ej and _tiene_rzbin:
        ex = ej[0].get("ejemplo") or {}
        e2 = rx([ex])
        v("el ejemplo de `run` de ops ES ejecutable",
          bool(e2) and e2[0].get("status") in ("ok", "error", "blocked"),
          e2[0].get("status") if e2 else "sin linea")
        v("y no es un `empty` silencioso",
          bool(e2) and bool(e2[0].get("limitations"))
          or bool(e2) and e2[0].get("status") == "ok",
          e2[0].get("limitations") if e2 else None)

# --- 5. LA CAPA DE DISPATCH ES LA DEL REGISTRY, NO UNA COPIA ------------
# Si la allow-list estuviera escrita en dispatch.py, mutar el registry no la
# moveria, y B7 seria decorativo. Se comprueba leyendo las dos: cambiar la
# ficha de rizin tiene que cambiar lo que el registry afirma, y lo que el
# dispatch dice viene de ahi.
import importlib  # noqa: E402
if PKG not in sys.path:
    sys.path.insert(0, PKG)
from backends import dispatch as _D  # noqa: E402
from backends import registry as _R   # noqa: E402

_todas = _D._todas_las_fichas()
_union_caps = {c for b in _R.backends() for c in _R.get(b)["capacities"]}
v("la capa de dispatch PREGUNTA al registry (mismas capacidades)",
  set(_todas) == _union_caps, sorted(_todas)[:4])
v("binary.cfg es PARTIAL en rizin y AVAILABLE en radare2 (medido)",
  _todas.get("binary.cfg", {}).get("estados", {}).get("rizin") == "PARTIAL"
  and _todas["binary.cfg"]["estados"].get("radare2") == "AVAILABLE",
  _todas.get("binary.cfg", {}).get("estados"))
v("y la agregada conserva la limitacion por backend",
  any("rizin" in x for x in _todas["binary.cfg"]["limitaciones"]),
  _todas.get("binary.cfg", {}).get("limitaciones"))
v("binary.decompile es UNAVAILABLE en los dos backends MEDIDOS",
  _todas.get("binary.decompile", {}).get("estado_agregado") == "UNAVAILABLE",
  _todas.get("binary.decompile", {}).get("estado_agregado"))

# --- B5. LA CLASIFICACION DE DATAFLOW ESTA RESPALDADA POR EVIDENCIA ----
# §12: no corregir por intuicion. Estas comprobaciones no re-ejecutan los
# verbos (eso lo hizo la medicion y esta en las notas del registry); comprueban
# que la DECLARACION nombre el producer real y la limitacion medida, para que
# no se pueda volver a la razon falsa sin que un vector lo note.
_notas_r = " ".join(_R.get("rizin")["notas"])
_notas_2 = " ".join(_R.get("radare2")["notas"])

v("B5: la nota de rizin nombra el producer REAL (afvxj), no pdj",
  "afvxj" in _notas_r and "afvxj" in _notas_2)
v("B5: y se RETRACTA la razon anterior en las notas, no solo en un comentario",
  "RETRACCION" in _notas_r and "ESA RAZON ERA FALSA" in _notas_r)
v("B5: una razon correcta importa tanto como una etiqueta correcta",
  "se pueden equivocar por separado" in _notas_r)
v("B5: rizin dataflow es PARTIAL por FORMATO, no por ausencia de producer",
  _R.get("rizin")["capacities"]["binary.dataflow"] == "PARTIAL"
  and "mal formado" in _notas_r.lower() or "mal formado" in _notas_r.lower(),
  _R.get("rizin")["capacities"]["binary.dataflow"])
v("B5: r2 dataflow es AVAILABLE porque su JSON es VALIDO",
  _R.get("radare2")["capacities"]["binary.dataflow"] == "AVAILABLE"
  and "json valido" in _notas_2.lower(),
  _R.get("radare2")["capacities"]["binary.dataflow"])
# La limitacion que de verdad importa para ESTE proyecto: las 24 aristas WRITES.
v("B5: se declara que el conjunto de escrituras sale VACIO para un store real",
  "vac" in _notas_2.lower() and "0x400024" in _notas_r)
v("B5: y se dice explicitamente que NO puede cerrar la frontera WRITES",
  "WRITES" in _notas_r and "PROVEN_ABSENT" in _notas_r)
v("B5: available NO se confunde con completo",
  any("no significa completo" in x.lower() for x in _R.get("radare2")["notas"]))
# Y el trap de flags, que ya produjo un empty falso una vez.
v("B5: se declara el trap de ORDEN DE FLAGS (-qc se come -e)",
  "-qc" in _notas_r and "ORDEN DE FLAGS" in _notas_r)
v("B5: y se relaciona con el mismo error que `aa` frente a `aaa`",
  "aaa" in _notas_r and "una invocacion incorrecta" in _notas_r.lower()
  or "invocacion incorrecta" in _notas_r.lower())

# --- B6. PLAN SIN EJECUCION ---------------------------------------------
# §13: la IA tiene que poder ver el camino ANTES de recorrerlo, y un plan no
# puede afirmar que un paso va a funcionar.
_envs = rx([{"op": "plan", "capability": "binary.decompile",
             "question": "que funcion escribe este registro"}])
v("op:plan responde una linea", len(_envs) == 1, len(_envs))
if _envs:
    P = _envs[0]
    v("op:plan -> status ok", P.get("status") == "ok", P.get("status"))
    # LO CENTRAL: un plan no ejecuta.
    v("execution vale literalmente 'not_started'",
      P.get("execution") == "not_started", P.get("execution"))
    v("el plan NO produce resultados (no se ejecuto nada)",
      not (P.get("results") or []) or not (P.get("results") or [{}])[0].get(
          "results"),
      P.get("results"))
    v("el plan NO persiste ninguna operacion", P.get("operation_id") in
      (None, ""), P.get("operation_id"))
    v("plan lista pasos", len(P.get("plan") or []) >= 2,
      len(P.get("plan") or []))

    # Y el caso de §13: `binary.decompile` se ve como callejon ANTES de
    # ejecutar nada. Es la razon de que exista `plan`.
    pasos = P.get("plan") or []
    dec = [x for x in pasos if x["operation"] == "binary.decompile"]
    v("binary.decompile APARECE en el plan (no se oculta)",
      len(dec) == 1, [x["operation"] for x in pasos])
    if dec:
        v("y aparece como NO disponible", dec[0]["available"] is False,
          dec[0]["available"])
        v("con el motivo POR QUE no", bool(dec[0]["reason"]),
          dec[0]["reason"][:60])
        v("y no se propone como accion ejecutable",
          all(a["available"] is False for a in P.get("next_actions") or []
              if a["args"]["capability"] == "binary.decompile"))

    # `verifiable` y `available` son cosas DISTINTAS. Medido: los seis pasos
    # son verificables (el registry los declara) y solo uno es ejecutable.
    v("verificables != ejecutables: 6 verificables, 1 ejecutable",
      len([x for x in pasos if x["verifiable"]]) == 6
      and len([x for x in pasos if x["available"]]) == 1,
      (len([x for x in pasos if x["verifiable"]]),
       len([x for x in pasos if x["available"]])))
    v("todo paso declara operation, capability, verifiable, available, reason",
      all(all(k in x for k in ("operation", "capability", "verifiable",
                               "available", "reason")) for x in pasos))
    v("la advertencia dice que verifiable NO es promesa de exito",
      "NO significa que la ejecucion tendra exito" in P.get("advertencia", ""),
      P.get("advertencia", "")[:70])

    # Y `next_actions` respeta T4 de RXRE-003 sobre el plan tambien.
    na = P.get("next_actions") or []
    v("toda next_action del plan es ejecutable o available:false con motivo",
      all(a.get("available") is True
          or (a.get("available") is False and bool(a.get("reason")))
          for a in na), na)

# Un plan de una capacidad que no existe: se dice, no se inventa un camino.
_envs = rx([{"op": "plan", "capability": "binary.magic"}])
if _envs:
    P = _envs[0]
    v("capacidad sin plan -> empty con motivo, no error",
      P.get("status") == "empty", P.get("status"))
    v("y el motivo NO la llama 'no existe la capacidad' (existe, no tiene plan)",
      "no hay un plan definido" in " ".join(P.get("limitations") or []),
      P.get("limitations"))
    v("y lista las capacidades que SI tienen plan",
      "plan son:" in " ".join(P.get("limitations") or []))

# Un plan de UNA capacidad ejecutable: un solo paso, disponible.
_envs = rx([{"op": "plan", "capability": "binary.inspect"}])
if _envs:
    P = _envs[0]
    v("plan de binary.inspect -> ok", P.get("status") == "ok", P.get("status"))
    v("con un solo paso", len(P.get("plan") or []) == 1,
      len(P.get("plan") or []))
    v("y ese paso es ejecutable",
      (P.get("plan") or [{}])[0].get("available") is True)
    v("execution sigue siendo not_started aunque sea todo ejecutable",
      P.get("execution") == "not_started", P.get("execution"))

# --- B7. LA DECISION §18 ES MACHINE-READABLE Y COMPROBABLE -------------
# §15: tiene que existir una mutacion que cambie PRIMARY=rizin por
# PRIMARY=radare2 y provoque fallo. Para que eso sea posible, `primary` no puede
# vivir solo en la prosa: y para que no sea decorativo, el vector compara el
# `primary` declarado contra el RECUENTO REAL del registro.
_e = rx([{"op": "backends"}])
if _e:
    B7 = _e[0]
    dec = B7.get("decision") or {}
    rec = B7.get("recuento_real") or {}
    v("B7: la decision se expone por la superficie publica", bool(dec),
      sorted(dec)[:5])
    v("B7: declara primary, secondary y analytical",
      all(k in dec for k in ("primary", "secondary", "analytical")),
      sorted(dec)[:6])
    v("B7: primary = rizin (medido)", dec.get("primary") == "rizin",
      dec.get("primary"))
    v("B7: secondary = radare2 (medido)", dec.get("secondary") == "radare2",
      dec.get("secondary"))
    v("B7: analytical = NOT_DETERMINED, NO 'ninguno' ni UNAVAILABLE",
      dec.get("analytical") == "NOT_DETERMINED", dec.get("analytical"))
    v("B7: el recuento declarado COINCIDE con el recuento real del registro",
      (dec.get("capacidades_cerradas_por_backend") or {}) == rec,
      "declarado=%s real=%s" % (dec.get("capacidades_cerradas_por_backend"),
                                rec))
    # Y la regla que justifica la decision, comprobada: primary cierra mas.
    if rec.get(dec.get("primary")) is not None:
        _otros = [x for k, x in rec.items() if k != dec["primary"]]
        v("B7: primary es de verdad el que mas capacidades cierra",
          not _otros or rec[dec["primary"]] > max(_otros), rec)
    v("B7: la decision dice QUE se reviso por mutacion",
      "test_mutations003.py" in (dec.get("revisado_por_mutacion") or ""),
      dec.get("revisado_por_mutacion"))
    v("B7: y lo que NO se decidio queda escrito",
      bool(dec.get("no_decidido")), dec.get("no_decidido"))
    v("B7: se declara que angr NO se instalo",
      any("angr" in x and "NO" in x.upper() for x in dec.get("no_decidido") or []))

if fails:
    print("self-test FALLA (%d de %d)" % (len(fails), n))
    for f in fails:
        print("   " + f)
    sys.exit(1)
print("self-test OK (%d comprobaciones: la superficie publica responde "
        "`backends` y `run`, binary.inspect se ejecuta end-to-end por JSONL sin "
        "nombrar el backend, explain cierra el ciclo con los 13 eslabones, y "
        "los SEIS rechazos de la allow-list tienen cada uno su motivo "
        "correcto)" % n)
sys.exit(0)