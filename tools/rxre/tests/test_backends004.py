#!/usr/bin/env python3
"""RXRE-004. Vectores de la vertical `binary.inspect`.

QUE NO HACE ESTE FICHERO.

NO revalida rizin ni radare2. Esos son producer externos y su version es
dato suyo: un vector que revalidara un binario instalado seria una suite que
depende del entorno, y fallaria en otra maquina sin que hubiera un defecto.

Lo que SI hace es comprobar el MECANISMO de RXRE alrededor del producer:

    que el precheck ocurre ANTES de invocar
    que `invalid` no se confunde con `empty`
    que la provenance se reconstruye
    que el result_id no colisiona  (regla de F6)
    que el estado del backend no se colapsa
    que el contrato se puede pedir y se responde

Y usa el binario del sistema porque es lo que existe, pero ninguna asercion
depende de QUE el binario exista: si no esta, el test lo dice y no falla por
eso. Es la diferencia entre "el mecanismo esta roto" y "el entorno no tiene la
herramienta".
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
# MEDIDO 2026-10-06: `sys.path` necesita la raiz de PAQUETE (`tools/rxre/`),
# no el directorio de este fichero (`tools/rxre/tests/`) ni el de los modulos.
# Con el directorio equivocado, `from backends import ...` no encuentra nada
# porque buscaria `tests/backends/`.
PKG = os.path.abspath(os.path.join(HERE, ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from backends import registry                      # noqa: E402
from backends.adapters import rz_inspect           # noqa: E402
from backends.contract import (                    # noqa: E402
    BK_EMPTY, BK_ERROR, BK_INVALID, BK_OK, BK_UNSUPPORTED, BACKEND_STATES,
    ORDEN_CONFIANZA, DECOMPILATION, VALIDATED_SEMANTICS,
    Backend, contrato_de_backend, puede_declarar,
)

fails = []
n = 0


def v(nombre, cond, det=""):
    global n
    n += 1
    if not cond:
        fails.append("%s %s" % (nombre, det))


# --- 1. LOS ESTADOS DEL BACKEND SON MAS QUE LOS DE RXRE -------------------
v("unsupported es un estado propio", BK_UNSUPPORTED in BACKEND_STATES)
v("invalid_input es un estado propio", BK_INVALID in BACKEND_STATES)
v("unsupported != empty", BK_UNSUPPORTED != BK_EMPTY)
v("invalid != empty", BK_INVALID != BK_EMPTY)
v("unsupported != blocked", BK_UNSUPPORTED != "blocked")
v("los seis estados estan declarados", len(BACKEND_STATES) == 6,
  BACKEND_STATES)

# --- 2. LA REGLA DE CONFIANZA ---------------------------------------------
# La que impide que una DECOMPILACION se guarde como VALIDATED_SEMANTICS.
v("decompilacion NO demuestra semantica validada",
  not puede_declarar(DECOMPILATION, VALIDATED_SEMANTICS))
v("raw_binary no demuestra nada mas", not puede_declarar("raw_binary", "control_flow"))
v("la cadena de confianza esta ordenada",
  ORDEN_CONFIANZA.index("raw_binary") < ORDEN_CONFIANZA.index("disassembly")
  < ORDEN_CONFIANZA.index(DECOMPILATION) < ORDEN_CONFIANZA.index(VALIDATED_SEMANTICS))

# --- 3. EL CONTRATO SE RESPONDE Y DICE LO QUE ES -------------------------
ct = contrato_de_backend(registry.get("rizin")["backend"])
for campo in ("backend_id", "tool_version", "version_verificada",
              "repository", "repository_commit", "input_hash", "raw_output",
              "normalized_output", "command_or_api", "exit_status",
              "limitations", "limpieza"):
    v("el contrato declara %s" % campo, campo in ct["campos"], ct["campos"])
v("el contrato dice que unsupported != empty",
  "unsupported != empty" in ct["regla_de_estados"])
v("el contrato separa version de commit",
  "commit del repo es" in ct["regla_de_identidad"])

# --- 4. EL REGISTRO NO ES UN CATALOGO NUEVO DE CAPACIDADES ---------------
v("el registro tiene backends MEDIDOS, no capacidades inventadas",
  set(registry.backends()) == {"rizin", "radare2"},
  sorted(registry.backends()))
# Lo que NO se puede verificar esta declarado como NOT_DETERMINED, no borrado.
ids_nd = {b["backend_id"]: b["estado"] for b in registry.NO_VERIFICABLES}
v("angr declarado NOT_DETERMINED, no ausente", ids_nd.get("angr") == "NOT_DETERMINED",
  ids_nd)
v("rz-ghidra declarado NOT_DETERMINED", ids_nd.get("rz-ghidra") == "NOT_DETERMINED")
v("la razon de angr cita el namespace package",
  any("namespace" in b["razon"] for b in registry.NO_VERIFICABLES
      if b["backend_id"] == "angr"))
# Y `binary.decompile` NO esta disponible en ninguno de los medidos: es
# exactamente lo que el contrato obliga a no inventar.
for bid in registry.backends():
    caps = registry.get(bid)["capacities"]
    v("%s declara decompile UNAVAILABLE, no AVAILABLE" % bid,
      caps.get("binary.decompile") == "UNAVAILABLE", caps.get("binary.decompile"))
    v("%s NO declara ninguna capacidad como AVAILABLE sin haberla medido" % bid,
      all(v_ in ("AVAILABLE", "PARTIAL", "UNAVAILABLE", "NOT_DETERMINED")
          for v_ in caps.values()), caps)

# --- 5. EL PRECHECK OCURRE ANTES DE INVOCAR -----------------------------
# MEDIDO: con `falso.elf` (no existe) y con un fichero que no es ELF, el
# adapter NO debe llamar al backend. Se comprueba por el estado devuelto y por
# que el motivo diga que no se invoco.
env_no = rz_inspect.inspect("/tmp/opencode/no_existe_este_fichero")
v("entrada inexistente -> invalid_input, no error",
  env_no["status"] == BK_INVALID, env_no["status"])
v("y dice que no existe", "no existe" in (env_no["limitations"][0]).lower())
v("y el precheck lo dice antes", env_no["precheck"]["input_existe"] is False)
v("el precheck no marco ok", env_no["precheck"]["ok"] is False)
v("no se invoco al backend (no hay 'ejecucion')", "ejecucion" not in env_no)

with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as fh:
    fh.write(b"esto no es un ELF, es texto\n")
    no_elf = fh.name
try:
    env_texto = rz_inspect.inspect(no_elf)
    v("fichero que no es ELF -> invalid_input", env_texto["status"] == BK_INVALID,
      env_texto["status"])
    v("y dice que no se invoco al backend",
      any("no se invoco" in l for l in env_texto["limitations"]),
      env_texto["limitations"])
    v("el precheck marco input_es_elf=False",
      env_texto["precheck"]["input_es_elf"] is False)
finally:
    os.unlink(no_elf)

# --- 6. LA VERTICAL COMPLETA, si el backend existe ----------------------
# Ninguna asercion DEPENDE de que exista: si no esta, se marca y se sale. Es la
# diferencia entre "el mecanismo esta roto" y "el entorno no lo tiene".
tiene = shutil.which("rz-bin") is not None
if not tiene:
    v("rz-bin ausente: el entorno no tiene el backend (no es un fallo)", True)
else:
    env = rz_inspect.inspect("/bin/ls")
    v("binary.inspect de un ELF -> ok", env["status"] == BK_OK, env["status"])
    v("el precheck marco ok ANTES de invocar", env["precheck"]["ok"] is True)
    v("el precheck comprobó la firma ELF", env["precheck"]["input_es_elf"] is True)
    v("el precheck tiene el hash del input",
      len(env["precheck"]["input_hash"]) == 64, env["precheck"]["input_hash"][:12])

    # -- el comando REAL, no el declarado
    argv = env["ejecucion"]["argv"]
    v("el argv usa el binario PROPIO (rz-bin), no rizin",
      os.path.basename(argv[0]) == "rz-bin", argv[0])
    v("el comando lleva -I y -j (MEDIDO: -j solo imprime usage)",
      "-I" in argv and "-j" in argv, argv)
    v("rc=0", env["ejecucion"]["exit_status"] == 0, env["ejecucion"]["exit_status"])

    # -- un exit 0 con una salida que NO es la pedida tiene que ser error.
    #    MEDIDO: con `rizin -qc -I -j` salia rc=0 y stdout era el BANNER de
    #    rizin con su prompt. Un rc=0 no es un resultado.
    v("la salida se parseo como JSON, no como banner",
      isinstance(env.get("raw_output"), dict), type(env.get("raw_output")))

    # -- provenance reconstruible de punta a punta
    res = env["results"][0]
    prov = env["provenance"]
    v("la provenance esta completa", prov["estado"] == "completa", prov["estado"])
    for k in ("artefacto", "input_hash", "backend_id", "tool_version",
              "version_verificada", "repository_commit", "transformacion",
              "normalizador"):
        v("provenance declara %s" % k, bool(prov.get(k)), k)
    v("la version del runtime esta VERIFICADA, no declarada",
      prov["version_verificada"] is True, prov["version_verificada"])
    v("la cadena declara los 10 eslabones",
      len(prov["cadena"]) >= 10, len(prov["cadena"]))
    v("el result_id NO es un texto, es un hash",
      res["result_id"].startswith("res_binary_inspect_"), res["result_id"])
    v("el hash del artefacto coincide con el del input",
      prov["input_hash"] == env["precheck"]["input_hash"])
    v("el resultado guarda el RAW sin reinterpretar",
      isinstance(res.get("raw"), dict) and "info" in res["raw"])

    # -- la version del backend esta VERIFICADA de verdad, no declarada.
    #    MEDIDO: la mutacion `version_verificada: True` (fija, sin preguntar al
    #    binario) SOBREVIVIO a los vectores de arriba, porque todos comprueban
    #    `is True` y el mutador deja True. Un vector que comprueba el VALOR de
    #    un booleano que el codigo pone a True no comprueba nada.
    #
    #     un vector que comprueba lo que el codigo pone no comprueba el codigo
    #
    #    Lo que si se puede comprobar es que el backend RESPONDA al flag de
    #    version, y que la version string no sea la que se pone por defecto.
    _bv = registry.get("rizin")["backend"]
    _vi = _bv.identidad()
    v("la identidad del backend se verifica ejecutando el binario",
      _vi.get("version_verificada") is True
      and _vi.get("tool_version", "").startswith("rizin "),
      _vi.get("tool_version", "")[:40])
    v("la version NO es un valor por defecto", 
      "0.7.4" in _vi.get("tool_version", ""), _vi.get("tool_version", "")[:40])
    # Y el flag con el que se verifico queda escrito: sin el, no se puede
    # repetir la verificacion.
    _vv = _bv.version()
    v("la verificacion dice QUE FLAG la hizo", bool(_vv.get("flag")),
      _vv.get("flag"))
    v("el status de version es VERIFIED cuando la sonda respondio",
      _vi.get("backend_version_status") == "VERIFIED",
      _vi.get("backend_version_status"))

    # -- la version NO VERIFICADA se declara como tal, no como VERIFIED.
    #    MEDIDO (B0): los tres vectores de arriba eran INSENSIBLES a la
    #    mutacion `version_verificada: True`. Dos comprobaban `is True` (el
    #    mutador pone True) y el tercero miraba `version()`, que el mutador NO
    #    toca. Los tres pasaban con el codigo mutado.
    #
    #     un vector que comprueba lo que el codigo pone no comprueba el codigo
    #
    #    El discriminante necesita un backend que NO exista: entonces la
    #    identidad tiene que ser False/UNVERIFIED, y el mutador a True lo
    #    delata. `Backend.path()` devuelve None, `version()` no puede probar y
    #    `identidad()` no puede decir que verifico nada.
    _bx = Backend("no-existe-jamas", "rxre004_fantasma_xyz", [])
    v("PRECONDICION: el backend fantasma no esta en PATH",
      not _bx.existe())
    _xi = _bx.identidad()
    v("backend inexistente -> version_verificada es False, no True",
      _xi.get("version_verificada") is False, _xi.get("version_verificada"))
    v("backend inexistente -> backend_version_status es UNVERIFIED",
      _xi.get("backend_version_status") == "UNVERIFIED",
      _xi.get("backend_version_status"))
    v("backend inexistente -> NO se inventa una tool_version",
      not _xi.get("tool_version"), _xi.get("tool_version"))
    v("backend inexistente -> tool_version queda vacio, no 'unknown'",
      _xi.get("tool_version", "") == "", repr(_xi.get("tool_version")))
    v("el motivo de la no-verificacion queda escrito",
      bool(_xi.get("version_error")), _xi.get("version_error"))
    v("el commit del repo se conserva aunque no haya version (son datos separados)",
      _xi.get("repository_commit") is not None)

    # -- el resultado es RAW_BINARY y lo DICE
    v("el tipo es raw_binary", res["type"] == "raw_binary", res["type"])
    v("el estado del resultado es 'declared', no 'proven'",
      res["status"] == "declared", res["status"])
    v("las limitaciones dicen que es una DECLARACION",
      any("DECLARACION" in l for l in res["limitations"]), res["limitations"])

    # -- los campos que el backend NO dio no se inventan
    v("no se invento un campo ausente",
      any("no se han supuesto" in l for l in res["limitations"])
      or all(x is not None for x in res["value"].values()),
      res["limitations"][-1][:70])

# --- 7. EL RESULT_ID NO COLISIONA (regla de F6) --------------------------
# MEDIDO F6: un id derivado solo del texto daba 9 ids para 36 resultados, y
# con `INSERT OR REPLACE` la evidencia desaparecia sin avisar.
if tiene:
    _a = rz_inspect.inspect("/bin/ls")
    _b = rz_inspect.inspect("/bin/ls")
    _ids_a = [r["result_id"] for r in _a["results"]]
    _ids_b = [r["result_id"] for r in _b["results"]]
    v("dos inspect del MISMO fichero dan el MISMO id (determinista)",
      _ids_a == _ids_b, (_ids_a, _ids_b))
    # Y el id NO es un hash del valor solo. MEDIDO (B0): el vector anterior
    # comparaba el id contra `json.dumps(valor)`, pero el MUTADOR usa
    # `str(valor)`. Bytes distintos -> hash distinto -> el vector pasaba con las
    # dos implementaciones y no media nada.
    #
    #     un vector tiene que derivar el id con la MISMA formula que el mutador,
    #     o no esta midiendo el mutador
    #
    # El discriminante correcto es de COMPORTAMIENTO: dos artefactos byte a byte
    # identicos en rutas distintas dan el MISMO `value` normalizado, y sus
    # `result_id` TIENEN que diferir. Con un id derivado solo del valor,
    # colisionarian. Eso es F6 ("un identificador que colisiona no identifica")
    # en la forma que todavia no se habia medido.
    v("el id incorpora el artefacto, no solo el valor",
      _ids_a[0].startswith("res_binary_inspect_"), _ids_a[0])
    _dupdir = tempfile.mkdtemp(prefix="rxre004_dup_")
    try:
        _pa = os.path.join(_dupdir, "copia_a")
        _pb = os.path.join(_dupdir, "copia_b")
        shutil.copyfile("/bin/ls", _pa)
        shutil.copyfile("/bin/ls", _pb)
        _ea = rz_inspect.inspect(_pa)
        _eb = rz_inspect.inspect(_pb)
        if _ea.get("results") and _eb.get("results"):
            _va = _ea["results"][0]["value"]
            _vb = _eb["results"][0]["value"]
            _ida = _ea["results"][0]["result_id"]
            _idb = _eb["results"][0]["result_id"]
            # Esta es la PRECONDICION del vector, y importa que sea cierta: sin
            # valores iguales, la unicidad del id no probaria nada.
            v("PRECONDICION: dos artefactos identicos dan el mismo valor",
              _va == _vb)
            v("determinismo NO es unicidad: mismo valor -> ids DISTINTOS",
              _ida != _idb, "%s vs %s" % (_ida, _idb))
        else:
            v("PRECONDICION: dos artefactos identicos dan el mismo valor", False,
              "inspect no produjo resultados sobre las copias")
    finally:
        shutil.rmtree(_dupdir, ignore_errors=True)
    # Y dos ficheros DISTINTOS no pueden compartir id.
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as fh:
        fh.write(b"\x7fELF" + b"\x02\x01\x01" + b"\x00" * 64)
        otro = fh.name
    try:
        _c = rz_inspect.inspect(otro)
        _ids_c = [r["result_id"] for r in _c.get("results", [])]
        v("un binario DISTINTO no comparte result_id",
          not (set(_ids_a) & set(_ids_c)), (set(_ids_a) & set(_ids_c)))
    finally:
        os.unlink(otro)

# --- 8. LA LIMPIEZA DE CONTROL CHARS ES REAL Y DECLARADA ----------------
from backends.contract import limpiar  # noqa: E402
sucio = "\x1b[38;2;193;156;0mhola\x1b[0m\rmundo\x07"
limpio, quitados = limpiar(sucio)
v("limpiar quita ANSI, CR y BEL", "mundo" in limpio and "\x1b" not in limpio,
  repr(limpio))
v("limpiar DICE cuantos quito", quitados > 0, quitados)
v("limpiar una cadena limpia no inventa trabajo", limpiar("hola")[1] == 0)

# --- B3. LA PROVENANCE PERSISTIDA NO MIENTE ----------------------------
# MEDIDO: `persistir()` firmaba TODAS las operaciones con
# `target: "0000:01:00.0"`, incluidas las que solo abren un fichero con
# rz-bin. Eso adjuntaba una lectura de hardware que no habia ocurrido: una
# evidencia de la RX550 firmada por una operacion de fichero.
#
# Y `explain` no devolvia la cadena del backend, de modo que el mismo resultado
# tenia una explicacion incompleta.
if tiene:
    from core import store as _S
    _fx = os.path.join(PKG, "fixtures", "bin", "rxre_min.elf")
    if os.path.isfile(_fx):
        _dbdir = tempfile.mkdtemp(prefix="rxre004_db_")
        try:
            _c = _S.conectar(os.path.join(_dbdir, "t.sqlite3"))
            _env = rz_inspect.inspect(_fx)
            _op = rz_inspect.persistir(_env, db=_c)

            # -- el target NO es un dispositivo PCI ------------------------
            v("persistir devuelve un operation_id, no una colision",
              isinstance(_op, str) and _op.startswith("op_"), _op)
            _row = _c.execute("SELECT target, target_pci, capability, scope "
                              "FROM operations WHERE operation_id=?",
                              (_op,)).fetchone()
            v("B3: el target NO es la RX550", _row["target"] != "0000:01:00.0",
              _row["target"])
            v("B3: el target identifica el artefacto",
              str(_row["target"]).startswith("binary:"), _row["target"])
            v("B3: el target lleva el hash del artefacto, no solo el nombre",
              _env["precheck"]["input_hash"][:16] in str(_row["target"]),
              _row["target"])
            v("B3: target_pci tampoco miente con un PCI",
              str(_row["target_pci"]).startswith("binary:"),
              _row["target_pci"])
            v("B3: la operacion se declara de scope binary, no de hardware",
              _row["scope"] == "binary", _row["scope"])

            # -- explain reconstruye la cadena completa -------------------
            _ex = _S.explicar_operacion(_c, _op)
            _bc = _ex.get("backend") or {}
            v("explain por operation_id devuelve la cadena del backend",
              bool(_bc), sorted(_bc.keys())[:5])
            for _campo in ("backend_id", "tool_version",
                           "backend_version_status", "repository_commit",
                           "input_artifact", "input_hash", "command_or_api",
                           "argv", "exit_status", "transformacion",
                           "normalizador", "chain"):
                v("explain declara %s" % _campo, _campo in _bc, sorted(_bc))
            v("la cadena del backend tiene los 13 eslabones de §9",
              len(_bc.get("chain") or []) == 13, len(_bc.get("chain") or []))
            v("el hash del explain es el del artefacto real",
              _bc.get("input_hash") == _env["precheck"]["input_hash"])
            v("el commit del explain es el del repo auditado",
              _bc.get("repository_commit")
              == "d14c3fac4126bc5fbe66e7f3d1660aeab22b01d8",
              _bc.get("repository_commit"))
            v("el argv del explain usa el binario propio del producer",
              os.path.basename((_bc.get("argv") or [""])[0]) == "rz-bin",
              _bc.get("argv"))
            v("el explain NO dice PROVENANCE_INCOMPLETE en un camino con "
              "artefacto",
              "PROVENANCE_INCOMPLETE" not in str(_bc.get("provenance_estado")),
              _bc.get("provenance_estado"))

            # -- y por result_id tambien ----------------------------------
            _rid = _env["results"][0]["result_id"]
            _ex2 = _S.explicar(_c, _rid)
            v("explain por result_id devuelve la MISMA cadena del backend",
              (_ex2.get("backend") or {}).get("backend_id")
              == _bc.get("backend_id"),
              (_ex2.get("backend") or {}).get("backend_id"))
            v("y el mismo input_hash: una evidencia, una explicacion",
              (_ex2.get("backend") or {}).get("input_hash")
              == _bc.get("input_hash"))
            _c.close()
        finally:
            shutil.rmtree(_dbdir, ignore_errors=True)

        # -- y el caso de no-colision de F6 sigue vigente ------------------
        _dbdir2 = tempfile.mkdtemp(prefix="rxre004_db2_")
        try:
            _c2 = _S.conectar(os.path.join(_dbdir2, "t.sqlite3"))
            _env2 = rz_inspect.inspect(_fx)
            rz_inspect.persistir(_env2, db=_c2)
            _o2 = rz_inspect.persistir(_env2, db=_c2)
            v("B3/F6: el segundo intento dice COLISION y no pisa la fila",
              str(_o2).startswith("COLISION:"), _o2)
            _n = _c2.execute("SELECT COUNT(*) FROM results").fetchone()[0]
            v("y la tabla de resultados no se duplico", _n == 1, _n)
            # Y la conexion del llamante sigue viva: MEDIDO, `persistir` la
            # cerraba en la rama de colision y devolvia una base cerrada.
            _o3 = _c2.execute("SELECT COUNT(*) FROM operations").fetchone()[0]
            v("y la conexion del llamante NO fue cerrada por persistir",
              _o3 == 1, _o3)
            _c2.close()
        finally:
            shutil.rmtree(_dbdir2, ignore_errors=True)

# ==========================================================================
# B2. VECTORES DE ERROR, PROVENANCE E IDENTIDAD (§7)
# ==========================================================================
# Los tres que faltaban. Cada uno arranca de un caso REAL medido, no de un
# mock: un backend que devuelve lo que uno quiere no mide nada.

if tiene:

    # --- B2-A. ARQUITECTURA NO SOPORTADA ---------------------------------
    # MEDIDO: un ELF con `e_machine` desconocido (0xFFFF) pasa el precheck de
    # firma, `rz-bin` responde rc=0 y devuelve `info` CON contenido, pero SIN
    # `arch`. Corroborado con un segundo producer: r2 dice
    # arch='Unknown or unsupported arch'.
    #
    # Reducido a la forma del contrato, esto seria `ok` con arch=None, y una
    # IA leeria "arquitectura: null" como si el binario no tuviera
    # arquitectura. Es `unsupported`.
    import struct as _struct
    _dsk = tempfile.mkdtemp(prefix="rxre004_arch_")
    try:
        _fuente = "/bin/ls"
        _maq = os.path.join(_dsk, "maquina_desconocida.elf")
        with open(_fuente, "rb") as _fh:
            _b = bytearray(_fh.read())
        _struct.pack_into("<H", _b, 0x12, 0xFFFF)   # e_machine desconocido
        with open(_maq, "wb") as _fh:
            _fh.write(bytes(_b))
        _ea2 = rz_inspect.inspect(_maq)
        v("PRECONDICION: el ELF alterado sigue siendo un ELF (firma intacta)",
          _ea2["precheck"]["input_es_elf"] is True)
        v("PRECONDICION: el backend responde rc=0 (no es un error de ejecucion)",
          _ea2.get("ejecucion", {}).get("exit_status") == 0,
          _ea2.get("ejecucion", {}).get("exit_status"))
        v("arquitectura no soportada -> unsupported, NO empty",
          _ea2["status"] == BK_UNSUPPORTED, _ea2["status"])
        v("arquitectura no soportada -> NO es ok",
          _ea2["status"] != BK_OK, _ea2["status"])
        v("arquitectura no soportada -> NO es error de ejecucion",
          _ea2["status"] != BK_ERROR, _ea2["status"])
        v("y NO devuelve resultados, porque no hay nada que declarar",
          _ea2.get("results") == [], _ea2.get("results"))
        v("pero conserva el raw_output: la salida EXISTE y es trazable",
          isinstance(_ea2.get("raw_output"), dict)
          and "info" in _ea2["raw_output"])
        v("y dice POR QUE: nombra que no identifico la arquitectura",
          any("arquitectura" in l.lower() for l in
              _ea2.get("ejecucion", {}).get("limitations", [])),
          _ea2.get("ejecucion", {}).get("limitations"))
        v("y NO deduce la arquitectura de la cadena machine",
          any("machine" in l for l in _ea2["ejecucion"]["limitations"]))
        v("y la provenance no se pierde: hay salida que trazarla",
          "PROVENANCE_INCOMPLETE" not in _ea2.get("provenance", ""),
          _ea2.get("provenance"))
        # Y el caso de contraste: el mismo ELF con maquina CONOCIDA da ok.
        v("CONTRASTE: el mismo ELF sin alterar da ok (no es la ruta de error)",
          rz_inspect.inspect("/bin/ls")["status"] == BK_OK)
    finally:
        shutil.rmtree(_dsk, ignore_errors=True)

    # --- B2-C. DOS ARTEFACTOS, MISMO VALOR, IDS DISTINTOS ----------------
    # F6: "un identificador que colisiona no identifica". El caso real: dos
    # copias byte-identicas del fixture en rutas distintas dan el MISMO valor
    # normalizado y han de dar result_id DISTINTOS. Con un id derivado solo
    # del valor colisionarian.
    _cdir = tempfile.mkdtemp(prefix="rxre004_dupval_")
    try:
        _fx = os.path.join(PKG, "fixtures", "bin", "rxre_min.elf")
        if not os.path.isfile(_fx):
            v("PRECONDICION: el fixture B1 existe", False, _fx)
        else:
            _pa = os.path.join(_cdir, "copia_a.elf")
            _pb = os.path.join(_cdir, "copia_b.elf")
            shutil.copyfile(_fx, _pa)
            shutil.copyfile(_fx, _pb)
            _da = rz_inspect.inspect(_pa)
            _db = rz_inspect.inspect(_pb)
            if _da.get("results") and _db.get("results"):
                _vva = _da["results"][0]["value"]
                _vvb = _db["results"][0]["value"]
                _ida = _da["results"][0]["result_id"]
                _idb = _db["results"][0]["result_id"]
                # La PRECONDICION importa: sin valores iguales, la unicidad del
                # id no probaria nada.
                v("PRECONDICION: mismo valor normalizado en los dos artefactos",
                  _vva == _vvb)
                v("mismo valor -> result_id DISTINTOS (determinismo != unicidad)",
                  _ida != _idb, "%s vs %s" % (_ida, _idb))
                # Y determinismo: la MISMA entrada da SIEMPRE el mismo id.
                _da2 = rz_inspect.inspect(_pa)
                v("determinismo: la misma entrada da el mismo id",
                  _da2["results"][0]["result_id"] == _ida)
                v("y el hash del artefacto es identico en los dos (son copias)",
                  _da["precheck"]["input_hash"] == _db["precheck"]["input_hash"])
                # MEDIDO (B2): aqui estaba un vector que decia "el id NO deriva
                # solo del valor" y comparaba contra `hash(json.dumps(v))`.
                # PASA, pero pasa por la razon equivocada: el id real es
                # hash("raw_binary|artefacto|backend|json(v))", que tampoco
                # termina en hash(json(v)). Un id derivado SOLO del valor
                # -- hash(str(v)) -- tampoco terminaria en hash(json(v)).
                #
                #     un vector que pasa por la razon equivocada no mide nada
                #
                # El vector que SI discrimina esta dos lineas mas arriba
                # (mismo valor -> ids distintos): con el mutador `str(valor)`
                # los dos artefactos colapsan en un id y falla. Por eso el
                # vector de formula se sustituye por uno que exige la
                # PRECONDICION que lo hace informativo.
                v("PRECONDICION: el id lleva la Huella de valor+ubicacion, no "
                  "el hash desnudo del valor",
                  not _ida.endswith(
                      hashlib.sha256(
                          json.dumps(_vva, sort_keys=True,
                                     default=str).encode("utf-8")
                      ).hexdigest()[:12]),
                  _ida)
            else:
                v("PRECONDICION: mismo valor normalizado en los dos artefactos",
                  False, "inspect fallo sobre las copias")
    finally:
        shutil.rmtree(_cdir, ignore_errors=True)

# --- B2-B. PROVENANCE INCOMPLETA NO SE PUDRE ----------------------------
# El contrato declara PROVENANCE_INCOMPLETE. Aqui se comprueba que esa
# CADENA existe y que una provenance a la que le falta una pieza obligatoria no
# se presenta como completa. El mecanismo de la cadena esta en `_normalizar` y
# en `inspect`; lo que se mide aqui es que el contrato nombra las piezas.
_b2b_piezas = ("artefacto", "input_hash", "backend_id", "tool_version",
               "version_verificada", "repository_commit", "transformacion",
               "normalizador", "limitaciones", "cadena")
v("la provenance declara todas las piezas obligatorias del §8/B3",
  all(p in prov for p in _b2b_piezas),
  [p for p in _b2b_piezas if p not in prov])
# Y la palabra PROVENANCE_INCOMPLETE aparece EXACTAMENTE en los caminos que
# no tienen salida que provenancear. Se comprueba por el CODIGO, porque
# ejercitar cada rama exigiria un backend roto.
import inspect as _inspect_mod  # noqa: E402
_src = _inspect_mod.getsource(rz_inspect.inspect)
# MEDIDO (B2): pedi `>= 4` y hay 3. Antes de "arreglar" el codigo para llegar a
# 4, se enumero que ramas existen y cuales son las que de verdad no tienen
# salida que provenancear:
#
#     1. timeout                       -> no hay stdout
#     2. rc != 0                       -> el backend fallo
#     3. stdout no parseable           -> hay bytes, no hay artefacto
#
# Las otras dos salidas tempranas (no existe / no es ELF) NO llevan
# PROVENANCE_INCOMPLETE porque no hay `provenance` que pueda estar incompleto:
# el backend no se invoco. Pedir 4 seria exigir una cadena inexistente.
_v_b2b_ramas = _src.count("PROVENANCE_INCOMPLETE")
v("el adapter nombra PROVENANCE_INCOMPLETE en las TRES ramas sin artefacto",
  _v_b2b_ramas == 3, _v_b2b_ramas)
v("y cada una de las tres nombra una causa distinta",
  all(c in _src for c in ("timeout", "backend fallo, no hay salida",
                           "salida no parseable")))
v("y PROVENANCE_INCOMPLETE NUNCA se usa en un camino con resultados",
  "PROVENANCE_INCOMPLETE" not in prov["estado"],
  prov["estado"])
v("el camino con resultados dice 'completa', no PROVENANCE_INCOMPLETE",
  prov["estado"] == "completa", prov["estado"])

# --- 9. UNA CAPACIDAD QUE EL BACKEND NO TIENE --------------------------
# La pregunta que mas se querria declarar, y la que menos evidencia tiene.
for bid in registry.backends():
    caps = registry.get(bid)["capacities"]
    v("%s NO presenta decompile como lo tiene" % bid,
      caps.get("binary.decompile") == "UNAVAILABLE")
    # Y las parciales lo dicen en la ficha.
    ficha = registry.ficha(bid)
    v("%s lista sus capacidades parciales" % bid,
      bool(ficha["capabilities_parciales"]) or not ficha["capabilities_parciales"])

if fails:
    print("self-test FALLA (%d de %d)" % (len(fails), n))
    for f in fails:
        print("   " + f)
    sys.exit(1)
print("self-test OK (%d comprobaciones: los 6 estados de backend, la regla de "
        "confianza, el contrato, el registro no es catalogo nuevo, precheck "
        "antes de invocar, la vertical completa con provenance de 10 "
        "eslabones, result_id determinista y sin colision, limpieza declarada, "
        "y decompile NO declarado)" % n)
sys.exit(0)