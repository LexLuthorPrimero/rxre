#!/usr/bin/env python3
"""Vectores de RXRE. Con mutacion, porque un test que no puede fallar no prueba.

QUE PRUEBA ESTE FICHERO, y que NO:

* SI: que el envelope tiene la forma que una IA espera, siempre.
* SI: que `empty` no se convierte en ausencia, y que dice por que.
* SI: que `blocked` no se confunde con `empty`.
* SI: que el codigo de salida distingue los cuatro estados.
* NO: que las herramientas subyacentes sean correctas. Eso es de ellas, y cada
  una trae su propio self-test. RXRE no revalida a 220 herramientas: seria
  duplicar el registry y mentir sobre quien es responsable de que.

El criterio de correccion es `--self-test` en cero y el corpus real.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
RXRE = os.path.join(PKG, "rxre")
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from api import envelope as E  # noqa: E402

fails = []


def v(nombre: str, cond: bool, det: str = "") -> None:
    if not cond:
        fails.append("%s %s" % (nombre, det))


def run(args, timeout=600):
    p = subprocess.run([sys.executable, RXRE] + list(args),
                       capture_output=True, text=True, timeout=timeout)
    return p


def jrun(args, timeout=600):
    """Ejecuta y exige JSON parseable. Devuelve (rc, env)."""
    p = run(args, timeout)
    try:
        return p.returncode, json.loads(p.stdout)
    except ValueError:
        fails.append("rxre %s no devolvio JSON: %s" % (args, p.stdout[:120]))
        return p.returncode, {}


# --- 1. LA FORMA DEL ENVELOPE, que es el contrato con la IA ---------------

CLAVES = {"schema_version", "status", "operation", "target", "results",
          "evidence", "provenance", "limitations", "tools_used"}

rc, env = jrun(["capabilities"])
v("todas las claves existen", CLAVES <= set(env), sorted(CLAVES - set(env)))
v("status es uno de los cuatro", env.get("status") in E.VALID_STATUS, env.get("status"))
v("el esquema se declara", env.get("schema_version") == E.SCHEMA_VERSION)
v("capabilities responde ok", env.get("status") == E.ST_OK, env.get("status"))

# --- 2. UNA CAPACIDAD NO ES UNA ENTRADA DE DICCIONARIO --------------------
# La razon de que `capabilities` verifique por EJECUCION. Si solo listara lo
# declarado, estas dos vectores no distinction entre "existe" y "responde".

caps = env.get("results", [])
v("capabilities lista capacidades", len(caps) >= 5, len(caps))
todos_resp = all("available" in c for c in caps)
v("cada capacidad trae su disponibilidad", todos_resp)
n_disponibles = sum(1 for c in caps if c.get("available"))
v("hay capacidades disponibles de verdad", n_disponibles >= 5, n_disponibles)
v("cada capacidad nombra su script", all(c.get("tool") for c in caps))

# CONTROL NEGATIVO. Una capacidad declarada pero no disponible tiene que
# existir en la salida; si el filtro las borrara, `capabilities`diria que
# todo funciona sin que se note lo que no.
v("no se reportan capacidades como disponibles sin probarlas",
  all(("available" in c) or ("reason" in c) for c in caps))

# --- 3. `empty` NO ES AUSENCIA -------------------------------------------
# Es la distincion mas cara del proyecto. Se prueba con una cadena que no
# existe, y el requisito es que el envelope lo diga y lo justifique.

rc, env = jrun(["search", "ZZZ_NO_EXISTE_ESTE_SIMBOLO_XYZ_12345"])
v("una cadena inexistente da empty, no ok",
  env.get("status") == E.ST_EMPTY, env.get("status"))
v("empty tiene limitations obligatorias",
  bool(env.get("limitations")), env.get("limitations"))
v("empty dice explicitamente que no es ausencia",
  any("no es ausencia" in l.lower() or "NO es ausencia" in l
      for l in env.get("limitations", [])),
  env.get("limitations"))
v("empty NO trae resultados", env.get("results") == [])
v("un vacio no es error: rc=0", rc == 0, rc)

# Y la forma del envelope se mantiene tambien cuando esta vacio.
v("empty mantiene todas las claves", CLAVES <= set(env))

# --- 4. `blocked` NO ES `empty` ------------------------------------------
# xref.py sale con 3 porque el AST esta incompleto. Si eso se tradujera a
# empty, una IA concluiria que el simbolo no tiene referencias.

rc, env = jrun(["xref", "amdgpu_vm"])
v("un precondicion incumplida da blocked", env.get("status") == E.ST_BLOCKED,
  env.get("status"))
v("blocked tiene rc=2, distinto de error", rc == 2, rc)
v("blocked NO trae resultados", env.get("results") == [])
v("blocked dice que no se ejecuto",
  any("no se ejecut" in l.lower() or "NO hay resultado" in l
      for l in env.get("limitations", [])),
  env.get("limitations"))
v("blocked dice explicitamente que no es 'sin referencias'",
  any("referencias" in l for l in env.get("limitations", [])),
  env.get("limitations"))

# --- 5. LOS CUATRO CODIGOS DE SALIDA SON DISTINTOS ----------------------
# Si dos coincidieran, uno de los estados seria invisible para quien llama.

rc_ok, _ = jrun(["search", "VM_CONTEXT0_CNTL"])
rc_empty, _ = jrun(["search", "ZZZ_NO_EXISTE_XYZ_123"])
rc_blocked, _ = jrun(["xref", "amdgpu_vm"])
p_err = run(["capacidad_que_no_existe"])
try:
    json.loads(p_err.stdout)
    ok = True
except ValueError:
    ok = False
v("capacidad desconocida devuelve JSON de error, no un traceback", ok,
  p_err.stdout[:120])

v("ok y empty comparten rc a proposito", rc_ok == 0 and rc_empty == 0,
  (rc_ok, rc_empty))
v("blocked tiene rc propio", rc_blocked != 0 and rc_blocked != 1, rc_blocked)
v("capacidad inexistente tiene rc de error", p_err.returncode == 1,
  p_err.returncode)

# --- 6. LA UNIDAD DEL REGISTRO LLEGA A LA IA ----------------------------
# Un offset sin unidad no es un offset. reg_resolve lo declara; RXRE tiene que
# llevarlo al envelope, no tragarselo.

rc, env = jrun(["register", "VM_CONTEXT0_CNTL"])
v("register responde", env.get("status") in (E.ST_OK, E.ST_EMPTY),
  env.get("status"))
v("register declara la unidad en limitations",
  any("unidad" in l.lower() for l in env.get("limitations", [])),
  env.get("limitations"))
v("register dice el gfx que uso",
  any(e.get("kind") == "gfx" for e in env.get("evidence", [])))

# --- 7. HERRAMIENTAS REALES DETRAS DE CADA CAPACIDAD ---------------------
# El requisito es "usa el tooling existente, no lo reescribas". Se comprueba
# que cada capacidad nombra la herramienta que de verdad ejecuto.

for cap, debe in (("search", "evidence_search.py"),
                  ("register", "reg_resolve.py"),
                  ("xref", "xref.py"),
                  ("trace", "trace_path.py"),
                  ("capabilities", "toolreg.py")):
    argv = ["amdgpu_vm"] if cap in ("trace", "xref") else (
        ["VM_CONTEXT0_CNTL"] if cap in ("search", "register") else [])
    _r, e = jrun([cap] + argv)
    nombres = [t.get("tool") for t in e.get("tools_used", [])]
    v("%s nombra %s" % (cap, debe), debe in nombres, nombres)

# --- 8. UN OBJETIVO VACIO ES ERROR DE USO, NO UNA BUSQUEDA DE "" ----------
rc, env = jrun(["search"])
v("objetivo ausente da error, no busca la cadena vacia",
  env.get("status") == E.ST_ERROR, env.get("status"))
v("objetivo ausente explica que falta",
  any("falta el objetivo" in l for l in env.get("limitations", [])))

# --- 9. --help Y --version FUNCIONAN SIN TOCAR NADA ----------------------
p = run(["--help"])
v("--help responde 0", p.returncode == 0, p.returncode)
v("--help lista las capacidades obligatorias",
  all(w in p.stdout for w in ("capabilities", "search", "symbol", "xref",
                               "trace", "register", "pm4", "evidence",
                               "provenance")))
p = run(["--version"])
v("--version responde 0", p.returncode == 0, p.returncode)
v("--version nombra el target RX550", "rx550" in p.stdout.lower(), p.stdout)

# --- 10. --human NO PIERDE EL ENVELOPE ----------------------------------
p = run(["--human", "search", "VM_CONTEXT0_CNTL"])
v("--human responde 0", p.returncode == 0, p.returncode)
v("--human dice el estado", p.stdout.startswith("ok"), p.stdout[:40])

# --- RESULTADO ------------------------------------------------------------

# --- 11. MUTACION, y por que hace falta en DOS sitios mas ---------------
# MEDIDO 2026-10-05: M1 y M3 NO dispararon nada. No era que los vectores
# estuvieran mal, era que probaban el camino de la CAPACIDAD y no el del
# ENVELOPE que la envuelve.
#
# M1  -> se quito la obligacion de `limitations` en `empty`. Los vectores
#        comprobaban que `empty` trae limitations, pero las escribia el
#        HANDLER, no el envelope. El envelope no hacia nada y nadie se dio cuenta.
# M3  -> se declaro toda capacidad disponible sin probarla. Los vectores
#        contaban las disponibles, pero como ya lo eran TODAS, contar no
#        discriminaba: hacia falta una capacidad que NO respondiera, y no hay
#        ninguna en un arbol sano.
#
# Es el mismo motivo por el que `1524`/`1527` tu que extraer funciones: lo que
# hay que probar es el codigo que decide, no el que calcule.

from api import envelope as _E
from core import dispatch as _D  # noqa: E402

# M1: el envelope tiene que PRODUCIR el limitation, no solo admitirlo.
_geo = _E.envelope("prueba", status=_E.ST_EMPTY)
v("el envelope pone el limitation aunque nadie se lo pase",
  any("NO es ausencia" in l for l in _geo["limitations"]), _geo["limitations"])
# Y el caso sano no lo pone de mas.
_vac = _E.envelope("prueba", status=_E.ST_OK, results=[{"a": 1}])
v("con resultados no inventa limitations", _vac["limitations"] == [])
# Y `blocked` tampoco los inventa, porque tiene su propia obligacion.
_bl = _E.envelope("prueba", status=_E.ST_BLOCKED)
v("blocked sale sin limitations inventadas: las pone el handler",
  _bl["limitations"] == [])

# M3: hace falta una capacidad que NO responda, para que "contar" discrimine.
# Se construye una a proposito; no se espera que el arbol tenga una.
_rota = _D.Adapter(name="__vacia__", cmd=["no_existe_este_script.py"],
                   probe=["--help"], summary="ficticia", build=lambda a: [])
_filas = _D.probe_all(timeout=60)
# Se comprueba el CONTRATO de la filaUnavailable con la capacidad rota.
# `_rota` no esta en el registro, asi que se llama al camino de la fila tal
# cual, que es lo que `probe_all` hace por cada adaptador.
_presente = _rota.exists()
v("una capacidad cuyo script no existe se marca presente=False",
  _presente is False, _presente)
# Y la fila de esa capacidad en la salida real tiene que llevar `available`
# en False y un motivo, no desaparecer del inventario.
#
# MEDIDO: M4 (quitar el `reason` de la fila no disponible) NO disparo nada con
# los vectores de arriba, porque en un arbol sano TODAS las capacidades existen
# y ninguna fila no-disponible llega a existir. Repetir el defecto de M3: falta
# el caso NEGATIVO, no el vector.
#
# Aqui se produce el caso de verdad: se mete una capacidad rota en el registro,
# se ejecuta `probe_all` de nuevo, y se comprueba que sale en el inventario con
# `available=False` y un motivo. Se restaura el registro al final, porque si el
# test falla a mitad no debe dejar el registro contaminado para el siguiente.
_registro_backup = dict(_D.ADAPTERS)
try:
    _D.ADAPTERS["__rota__"] = _rota
    _con_rota = _D.probe_all(timeout=60)
    _fila = next((c for c in _con_rota if c["capability"] == "__rota__"), None)
    v("una capacidad rota APARECE en el inventario, no se omite",
      _fila is not None, "no esta en la salida")
    if _fila is not None:
        v("la capacidad rota se marca available=False", _fila.get("available") is False,
          _fila.get("available"))
        v("la capacidad rota explica por que no esta disponible",
          bool(_fila.get("reason")), _fila.get("reason"))
    v("la capacidad rota no se cuela entre las disponibles",
      not any(c.get("available") for c in _con_rota
              if c["capability"] == "__rota__"))
finally:
    _D.ADAPTERS.clear()
    _D.ADAPTERS.update(_registro_backup)

v("todas las filas traen `available`, no se filtran",
  all("available" in c for c in _filas))
v("ninguna capacidad se declara disponible sin probe",
  all(("probe_rc" in c) for c in _filas if c.get("available")))

# --- 12. UN ESTADO INVALIDO NO PASA DESAPARECIDO -----------------------
# El envelope tiene cuatro estados y se rechazan a proposito. Sin esto, un
# estado mal escrito pasaria y el consumidor leeria algo que no existe.
try:
    _E.envelope("prueba", status="tal_vez")
    v("un estado invalido tiene que ser rechazado", False, "no lanzo")
except ValueError:
    v("un estado invalido tiene que ser rechazado", True)

# --- 13. UN RESULTADO QUE DICE "NO ENCONTRADO" NO ES UN RESULTADO -------
# MEDIDO 2026-10-05: M6 (quitar la regla que sube `verdict=NO_ENCONTRADO` a
# `limitations` y vacia `results`) NO disparo nada. El vector que hacia falta
# es uno que ejecute `trace` sobre un simbolo INEXISTENTE y compruebe que no
# devuelve un `results` lleno de "no encontrado" con status `ok`.
#
# Es la clase de `1524` y `1527` por tercera vez: el codigo estaba bien, faltaba
# el vector que lo mirara. Y es la clase de `1529` en el otro sentido: la
# herramienta de fondo responde bien, y el que traducia mal era RXRE.

_r, e_trace = jrun(["trace", "SYM_QUE_NO_EXISTE_XYZ_98765"])
v("trace de un simbolo inexistente no da status=ok",
  e_trace.get("status") != E.ST_OK, e_trace.get("status"))
_v = [x for x in e_trace.get("results", []) if isinstance(x, dict)]
v("trace no devuelve nodos con verdict=NO_ENCONTRADO como si fueran hallados",
  not any(x.get("verdict") == "NO_ENCONTRADO" for x in _v), _v[:1])
v("trace explica que no lo encontro",
  any("NO encontro" in l or "no encontro" in l for l in e_trace.get("limitations", [])),
  e_trace.get("limitations"))

# Y el caso sano: un simbolo que SI existe tiene que dar status=ok CON
# resultados. Sin este control, "siempre empty" pasaria el vector anterior.
_r, e_ok_trace = jrun(["trace", "amdgpu_vm_init"])
v("trace de un simbolo real da ok con resultados",
  e_ok_trace.get("status") == E.ST_OK and bool(e_ok_trace.get("results")),
  (e_ok_trace.get("status"), len(e_ok_trace.get("results", []))))
v("el simbolo real trae su ubicacion",
  any(x.get("loc") and x["loc"] != "-" for x in e_ok_trace.get("results", [])
      if isinstance(x, dict)),
  [x.get("loc") for x in e_ok_trace.get("results", []) if isinstance(x, dict)][:2])

# --- 14. TODA CAPACIDAD DECLARA SU UNIVERSO, O LO DICE ------------------
# MEDIDO 2026-10-05: M7 (quitar el `--root` por defecto de `evidence`) NO
# disparo nada. La razon es que `evidence` y `search` comparten la capacidad y
# el self-test solo ejecutaba `search`. Y lo que rompe al quitarlo NO es un
# resultado: es una CLASIFICACION.
#
# Sin `--root`, `evidence_search.py` responde
# `"classification": "NOT_FOUND"` con `"universo exhaustivo, sin hits"`. Declara
# haber registrado TODO el sistema de ficheros y no haber visto nada. Eso es una
# afirmacion sobre el alcance, y es falsa. Por eso el vector mira la
# clasificacion, no los hits.
#
#     una clasificacion sin universo declarado es una afirmacion inventada

_r, e_ev = jrun(["evidence", "VM_CONTEXT0_CNTL"])
v("evidence responde con un universo declarado",
  e_ev.get("status") in (E.ST_OK, E.ST_EMPTY), e_ev.get("status"))
_univ = next((e for e in e_ev.get("evidence", []) if e.get("kind") == "universe"), None)
v("evidence declara el universo en `evidence`", _univ is not None)
v("el universo tiene raiz con nombre", bool((_univ or {}).get("declared")),
  (_univ or {}).get("declared"))
v("el universo tiene fingerprint, no es un nombre inventado",
  bool((_univ or {}).get("fingerprint")), (_univ or {}).get("fingerprint"))
# Y la clasificacion no puede ser NOT_FOUND con hits: seria incoherente.
_cls = next((e for e in e_ev.get("evidence", [])
             if e.get("kind") == "classification"), None)
v("evidence trae su clasificacion", _cls is not None)
if _cls and e_ev.get("results"):
    v("clasificacion NOT_FOUND con resultados seria incoherente",
      (_cls or {}).get("value") != "NOT_FOUND", _cls.get("value"))
# Y la razon de la clasificacion va con ella: un NOT_FOUND sin motivo es
# la mitad de la misma mentira.
v("la clasificacion trae razones", bool((_cls or {}).get("reasons")),
  (_cls or {}).get("reasons"))

# --- 15. `limitations` ES List[str], NO UN STRING TROCEADO --------------
# MEDIDO (RXRE-1644): la rama JSON del handler de `provenance` puso la
# limitacion en un `str` y el envelope hace `list(limitations or [])`. Sobre
# un str eso da sus CARACTERES: la frase salia como 163 elementos de una
# letra. El contrato del envelope dice `limitations: List[str]`, y ninguna
# suite ejecutaba el op `provenance`, asi que el defecto paso inadvertido.
#
#     un str troceado en letras no es una lista de limitaciones
#
# El vector lo ata por la superficie publica (CLI -> envelope), que es donde
# un consumidor lo veria.

_rcp, e_prov = jrun(["provenance"])
v("`provenance` responde con envelope",
  _rcp == 0 and e_prov.get("status") in (E.ST_OK, E.ST_EMPTY),
  (e_prov.get("status"), _rcp))
_lp = e_prov.get("limitations")
v("las limitations de `provenance` son frases, no caracteres sueltos",
  all(isinstance(x, str) and len(x) > 1 for x in (_lp or [])), _lp)
# Y el vector tiene que EJERCITAR la rama que fallaba: si `prov.py` cayera al
# camino de texto, `limitations` seria [] y el vector de arriba pasaria sin
# mirar nada. Aqui se exige que la limitacion exista (la rama JSON es la de
# por defecto), para que el vector discriminante no sea vacuo.
v("la rama JSON de `provenance` produce su limitacion (el vector no es vacuo)",
  bool(_lp), _lp)

if fails:
    print("self-test FALLA (%d)" % len(fails))
    for f in fails:
        print("   " + f)
    sys.exit(1)
print("self-test OK (15 grupos: forma del envelope, verificacion por ejecucion, "
      "empty != ausencia, blocked != empty, 4 codigos distintos, unidad del "
      "registro, herramientas reales detras, objetivo vacio, help/version, human, "
      "envelope y capacity-no-disponible, estados invalidos, NO_ENCONTRADO no es "
      "resultado, universo declarado, limitations es List[str] no un str troceado)")
sys.exit(0)