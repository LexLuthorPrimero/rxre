#!/usr/bin/env python3
"""RXRE-004. Adapter de `binary.inspect`. UNA vertical completa.

POR QUE ESTA Y NO OTRA.

La matriz eligio `binary.inspect` por evidencia, no por conveniencia:

* rizin la da con `rz-bin -Ij`: un comando, salida JSON, SIN analysis, sin
  estado, determinista.
* Es la entrada natural de la cadena `registro -> binario -> funcion -> ...`
  que RXRE-004 describe.
* Su provenance es la mas simple de sostener y por tanto la que menos puede
  mentir: comando, argv, rc, stdout crudo, hash del input.

Y tiene una ventaja de riesgo: **no depende del analisis**. Si rizin
desaparece, `binary.inspect` sigue siendo reproducible con `readelf`.

## LO QUE ESTE ADAPTER HACE Y LO QUE NO

HACE:
    entrada -> hash -> invocacion -> limpieza -> parseo -> normalizacion
           -> provenance -> result_id -> persistencia

NO HACE, y por que:

* NO decompila. No hay producer.
* NO infiere arquitectura de la salida: la LEE del campo que el backend da, y
  si no lo da, queda `None`. Un backend que no dice la arquitectura no es
  motivo para suponerla.
* NO convierte inspect en un hecho sobre el hardware. `binary.inspect` es
  `RAW_BINARY`: lo que el binario DECLARA. Lo que el hardware hace es otra
  pregunta, y la respuesta esta en `validated_semantics`.

    una cabecera ELF declara; no demuestra

* NO llama a `rz-bin -j` a secas. MEDIDO: `-j` es modificador, no modo, y
  `rz-bin -j /bin/ls` imprime el usage y sale. Hay que combinarlo con el modo.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from backends import registry  # noqa: E402
from backends.contract import (  # noqa: E402
    BK_BLOCKED, BK_EMPTY, BK_ERROR, BK_INVALID, BK_OK, BK_UNSUPPORTED,
    RAW_BINARY, Backend, sha256_de,
    estado_firma,
)


class NoEsBinario(Exception):
    """La entrada no es un ELF. `invalid_input`, no `empty`."""


def _exe_de(backend_id: str, nombre: str) -> Optional[str]:
    """Ruta de un binario concreto del backend.

    MEDIDO 2026-10-06: el registro declara `exe="rizin"` (el analisis), pero
    `binary.inspect` lo produce `rz-bin` (un binario aparte). Usar el equivocado
    da `exit 0` con el banner de rizin en stdout: el fallo mas caro, porque
    parece un exito.
    """
    import shutil
    return shutil.which(nombre)



def _id_resultado(artefacto: str, backend: str, valor: Any,
                  donde: Optional[Dict[str, Any]] = None) -> str:
    """Un identificador que NO colisiona. Regla de F6.

    MEDIDO 2026-10-05 (F6): un id derivado solo de (tipo, valor, herramienta)
    colisionaba -- 36 usos del mismo texto daban 9 ids distintos, y con
    `INSERT OR REPLACE` 36 filas se convertible en 9 sin que nada lo notara.

    Aqui el valor de `binary.inspect` es un DICCIONARIO COMPLETO, asi que el
    hash de su serializacion canonica ya no colisiona entre entradas distintas.
    Aun asi se incluye la ubicacion, porque el coste es cero y la regla pide
    que el id no dependa solo del texto.
    """
    h = hashlib.sha256(
        ("%s|%s|%s|%s" % (RAW_BINARY, artefacto, backend,
                         json.dumps(valor, sort_keys=True, default=str)))
        .encode("utf-8")).hexdigest()[:12]
    return "res_binary_inspect_%s" % h


def _normalizar(insp: Dict[str, Any], artefacto: str, backend: str,
                sha: str) -> Dict[str, Any]:
    """Lo que el backend DECLARA, normalizado. Sin inferencias.

    MEDIDO: `rz-bin -Ij` devuelve `{"info": {...30 claves...}}`. Se toma el
    dict interior y se separates lo que es identidad del fichero de lo que es
    afirmacion sobre el formato.

    Cada campo lleva su procedencia implicita: si el backend no lo dio, el
    campo NO se inventa, se deja `None` y se anota en `limitations`.
    """
    info = insp.get("info") if isinstance(insp, dict) else None
    if info is None:
        info = insp if isinstance(insp, dict) else {}
    valor = {
        "file_format": info.get("bintype") or info.get("class"),
        "arch": info.get("arch"),
        "bits": info.get("bits"),
        "os": info.get("os"),
        "endian": info.get("endian"),
        "machine": info.get("machine"),
        "compiler": info.get("compiler"),
        "lang": info.get("lang"),
        "stripped": info.get("stripped"),
        "static": info.get("static"),
        "pic": info.get("pic"),
        "canary": info.get("canary"),
        "nx": info.get("nx"),
        "relro": info.get("relro"),
        "baddr": info.get("baddr"),
        "intrp": info.get("intrp"),
    }
    ausentes = sorted(k for k, v in valor.items() if v is None)
    lim = [
        "binary.inspect es una DECLARACION del binario (RAW_BINARY): lo que la "
        "cabecera dice, no lo que el hardware ejecuta. Nada de esto verifica "
        "semantica de hardware.",
    ]
    if ausentes:
        lim.append("el backend no declaro estos campos, y no se han supuesto: "
                   "%s" % ", ".join(ausentes))
    return {
        "result_id": _id_resultado(artefacto, backend, valor),
        "type": RAW_BINARY,
        "value": valor,
        "source": artefacto,
        "location": {"file": os.path.basename(artefacto)},
        "scope": "binary",
        "tool": backend,
        "tool_version": "",
        "input": {"path": artefacto, "sha256": sha},
        "timestamp": "",
        "artifact": artefacto,
        "artifact_hash": sha,
        "status": "declared",
        "limitations": lim,
        "raw": insp,
    }


def inspect(artefacto: str, backend_id: str = "rizin",
            timeout: int = 900) -> Dict[str, Any]:
    """La operacion. Devuelve SIEMPRE los seis canales del contrato."""
    ent = registry.get(backend_id)
    b: Backend = ent["backend"]

    # --- PRE-EXECUTION CONTRACT CHECK (§15). Antes de invocar. -----------
    pre = {"input_existe": os.path.isfile(artefacto),
           "input_legible": None,
           "input_es_elf": False, "input_hash": "",
           "backend_existe": b.existe(),
           "entrypoint_existe": bool(b.path()),
           "formato_esperado": "ELF",
           "arquitectura_esperada": "cualquiera que el backend sepa leer",
           "ok": False}
    if not pre["input_existe"]:
        return {"status": BK_INVALID, "precheck": pre,
                "limitations": ["la entrada no existe: %s" % artefacto]}
    firma = estado_firma(artefacto)
    if firma == "no_legible":
        # MEDIDO 2026-10-15 (chmod 000): aqui antes se respondia lo mismo que
        # para un no-ELF, pero la firma NUNCA se leyo. "Firma distinta de
        # \x7fELF" sin haber leido la firma es afirmar una medicion que no
        # ocurrio. No-saber se reporta como no-saber (input_es_elf=None).
        pre["input_legible"] = False
        pre["input_es_elf"] = None
        return {"status": BK_INVALID, "precheck": pre,
                "limitations": ["la entrada EXISTE pero no es legible "
                                "(permiso o E/S): %s" % artefacto,
                                "no se pudo leer la firma: NO se sabe si es "
                                "ELF (distinto de saber que no lo es)",
                                "no se invoco al backend"]}
    pre["input_legible"] = True
    if firma == "no_elf":
        # No se invoca al backend. `rz-bin` sobre un no-ELF devuelve `info: []`,
        # que es indistinguible de un ELF sin secciones.
        return {"status": BK_INVALID, "precheck": pre,
                "limitations": ["la entrada no es un ELF (firma distinta de "
                                "\\x7fELF): %s" % artefacto,
                                "no se invoco al backend: rz-bin sobre un "
                                "no-ELF responde `info: []`, indistinguible de "
                                "un binario sin secciones"]}
    pre["input_es_elf"] = True
    pre["input_hash"] = sha256_de(artefacto)
    if not pre["backend_existe"]:
        return {"status": BK_BLOCKED, "precheck": pre,
                "limitations": ["el backend %s no esta en PATH" % backend_id]}
    pre["ok"] = True

    # --- EJECUCION ------------------------------------------------------
    # MEDIDO: el comando correcto es `rz-bin -I` MAS `-j`. `-j` a solas imprime
    # el usage. Y `rizin -qc 'agf'` emite ASCII, no JSON.
    exe = b.path()
    # MEDIDO: hay que ejecutar el binario PROPIO del backend (`rz-bin`), no el
    # `exe` del registro, que es `rizin` con `-qc`. Este adapter 调用aba
    # `rizin -qc -I -j`, y rizin imprimio su banner y abrio un prompt:
    #
    #     -- You can use registers in math expressions...
    #     [0x00003910]>
    #
    # es decir, `exit 0` con una salida que NO es la pedida. Un rc=0 no es un
    # resultado (§26), y aqui se ve por que: el comando se construyo con el
    # ejecutable equivocado y el rc seguia diciendo "todo bien".
    argv = [_exe_de(backend_id, "rz-bin") or exe, "-I", "-j", artefacto]
    import subprocess
    import time as _t
    t0 = _t.time()
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        rc, so, se = p.returncode, p.stdout or "", p.stderr or ""
        timedout = False
    except subprocess.TimeoutExpired:
        rc, so, se, timedout = None, "", "timeout a los %ds" % timeout, True

    from backends.contract import limpiar, parsear_json
    limpio, n_quit = limpiar(so)
    dur = round(_t.time() - t0, 3)

    ejec = {
        "backend_id": backend_id,
        "operation": "binary.inspect",
        "command_or_api": "rz-bin -I -j <artefacto>",
        "argv": argv,
        "exit_status": rc,
        "raw_output_len": len(so),
        "stderr": se.strip()[:400],
        "limpieza": {"aplicada": n_quit > 0, "caracteres_quitados": n_quit},
        "timeout": timedout,
        "duration_s": dur,
    }
    ident = b.identidad()

    if timedout:
        ejec.update({"status": BK_BLOCKED,
                     "limitations": ["timeout a los %ds" % timeout]})
        return {"status": BK_BLOCKED, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "provenance": "PROVENANCE_INCOMPLETE: "
                                                "no hay salida que provenancear"}
    if rc != 0:
        ejec.update({"status": BK_ERROR,
                     "limitations": ["el backend salio con rc=%s: %s"
                                     % (rc, (se.strip() or so.strip())[:200])]})
        return {"status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "provenance": "PROVENANCE_INCOMPLETE: "
                                                "backend fallo, no hay salida"}

    d = parsear_json(limpio)
    if d is None:
        ejec.update({"status": BK_ERROR,
                     "limitations": ["la salida no es JSON legible. "
                                     "MEDIDO: sin `-e scr.color=0` rizin mete "
                                     "ANSI y el parseo falla; aqui `rz-bin` no "
                                     "emite color, asi que si falla es otra cosa",
                                     "stdout crudo (primeros 200): %s"
                                     % limpio[:200]]})
        return {"status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "provenance": "PROVENANCE_INCOMPLETE: "
                                                "salida no parseable"}
    info = d.get("info") if isinstance(d, dict) else None
    if not info:
        ejec.update({"status": BK_EMPTY,
                     "limitations": ["`info` vacio: el backend abrio el "
                                     "fichero y no declaro nada. Eso NO es "
                                     "que el binario no tenga formato"]})
        return {"status": BK_EMPTY, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "raw_output": d, "results": [],
                "provenance": "completa"}

    # --- ARQUITECTURA SOPORTADA O NO (B2-A) ----------------------------
    # MEDIDO 2026-10-06: sobre un ELF con `e_machine` desconocido (0xFFFF),
    # `rz-bin` responde rc=0 y devuelve `info` CON contenido, pero SIN la
    # clave `arch`; en su lugar `machine` vale `<unknown>: 0xffff`.
    #
    #     rizin  -> arch=None        machine='<unknown>: 0xffff'
    #     r2      -> arch='Unknown or unsupported arch'
    #     /bin/ls -> arch='x86'
    #
    # El precheck de firma pasa (es un ELF), el backend devuelve rc=0 y hay
    # salida. Reducido a la forma del contrato, esto seeria `ok` con una
    # declaracion incompleta, y una IA leeria "arquitectura: null" como si el
    # binario no tuviera arquitectura. No la tiene: es que NADIE la ha
    # identificado.
    #
    # Eso es `unsupported`, no `empty` ni `ok`:
    #
    #     no saber que arquitectura es  !=  no haber nada que mirar
    #
    # Y no se deduce la arquitectura del `machine` texto: se pide al producer.
    arch = info.get("arch")
    machine = info.get("machine") or ""
    sin_arch = (not arch) or ("unknown" in str(arch).lower()) \
        or ("unsupported" in str(arch).lower()) \
        or ("unknown" in machine.lower())
    if sin_arch:
        ejec.update({
            "status": BK_UNSUPPORTED,
            "limitations": [
                "el backend abrio el fichero (rc=0, info con contenido) pero "
                "NO identifico la arquitectura: arch=%r machine=%r. Es una "
                "ARQUITECTURA NO SOPORTADA por este backend, no un fichero "
                "vacio. MEDIDO con rizin 0.7.4 y corroborado con radare2 "
                "5.9.8, que responde arch='Unknown or unsupported arch'."
                % (arch, machine),
                "no se deduce la arquitectura de la cadena `machine`: "
                "convertir '<unknown>: 0xffff' en un nombre de arquitectura "
                "seria inventar un dato que ningun producer emitio",
            ],
        })
        return {"status": BK_UNSUPPORTED, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "raw_output": d, "results": [],
                "arquitectura": {"arch": arch, "machine": machine},
                "provenance": "completa: la salida EXISTE y es trazable; lo "
                              "que no se puede es interpretarla"}

    res = _normalizar(d, artefacto, backend_id, pre["input_hash"])
    res["tool_version"] = ident.get("tool_version", "")
    res["timestamp"] = _ts()

    prov = {
        "estado": "completa",
        "cadena": ["artefacto", "input_hash", "backend", "command", "argv",
                   "raw_output", "limpieza", "parseo", "normalizacion",
                   "result_id"],
        "artefacto": os.path.relpath(artefacto, PKG),
        "input_hash": pre["input_hash"],
        "backend_id": backend_id,
        "tool_version": ident.get("tool_version", ""),
        "version_verificada": ident.get("version_verificada"),
        "repository": ident.get("repository", ""),
        "repository_commit": ident.get("repository_commit", ""),
        "transformacion": "rz-bin -I -j -> limpieza de control chars -> "
                          "json.loads -> _normalizar()",
        "normalizador": "backends.adapters.rz_inspect._normalizar",
        "limitaciones": res["limitations"],
    }
    ejec.update({"status": BK_OK, "limitations": []})
    return {"status": BK_OK, "precheck": pre, "ejecucion": ejec,
            "backend": ident, "raw_output": d, "results": [res],
            "provenance": prov}


def _ts() -> str:
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def target_binario(artefacto: str, input_hash: str = "") -> str:
    """El `target` de una operacion binaria. B3: NO es un dispositivo PCI.

    MEDIDO: `persistir()` escribia `target: "0000:01:00.0"` en TODAS las
    operaciones, incluidas las que solo abren un fichero con `rz-bin`. Eso
    firmaba una evidencia que no habia ocurrido: una lectura de binario
    Findada a la RX550. Es la clase de defecto que F3 persiguio en el otro
    sentido: aqui no era una lista negra queodian, era un target inventado que
    todos aceptaban porque "era el target del proyecto".

        un target que no se ha tocado no se puede escribir como target

    El target real de esta operacion es el ARTEFACTO. Y el identificador del
    artefacto es su hash, no su nombre: dos ficheros con el mismo nombre en
    sitios distintos son artefactos distintos, y un `target` que solo diga
    `binary:/bin/ls` no los distinguiria.
    """
    base = os.path.basename(artefacto or "")
    if input_hash:
        return "binary:%s@%s" % (base, input_hash[:16])
    return "binary:%s" % base


def cadena_backend(env: Dict[str, Any]) -> Dict[str, Any]:
    """La cadena del backend, extraible del envelope YA PERSISTIDO.

    B3 / §9: `explain` tiene que poder reconstruir

        result_id -> operation_id -> backend -> version -> commit -> input
        -> input_hash -> argv -> raw -> transformacion -> normalizado

    El envelope que se guarda en `operations.response_json` ya contiene todo
    esto. Lo que faltaba era la vista que lo devuelve. Y no se re-calcula nada
    aqui: se LEE de lo persistido, porque una cadena que se recompone al leer
    probaria que la funcion de lectura funciona, no que la evidencia existe.
    """
    ej = env.get("ejecucion") or {}
    be = env.get("backend") or {}
    # MEDIDO 2026-10-12 (RXRE-1632): `env["provenance"]` es POLIMORFICO.
    # Este mismo modulo pone las dos formas - `{"artefacto": ...}` en las
    # rutas con dict, y `"completa"` / `"PROVENANCE_INCOMPLETE: ..."` en
    # las de cadena - y los adapters de Ghidra, Coccinelle y las nuevas
    # capacidades de contenedor usan SIEMPRE cadena.
    #
    # Antes se hacia `prov = env.get("provenance") or {}` y se llamaba
    # `.get()` encima. Con una cadena eso es `AttributeError: 'str' object
    # has no attribute 'get'`, y reventaba DENTRO de `persistir`: es decir,
    # la capacidad habia funcionado y fallaba al guardar el resultado. Las
    # pruebas de las cinco capacidades de contenedor lo encontraron al
    # ejecutar por el dispatch real.
    #
    # Se normaliza aqui, en el CONSUMIDOR, porque es el consumidor el que
    # admite las dos formas. Un adapter nuevo no tiene que saber que existe
    # la otra, y un envelope con forma nueva no rompe la persistencia.
    crudo_prov = env.get("provenance")
    prov = crudo_prov if isinstance(crudo_prov, dict) else {}
    # Cuando `provenance` es una cadena, su contenido es el ESTADO. No se
    # pierde: sale por `provenance_estado`, que es donde lo lee el resto.
    estado_prov = (prov.get("estado") if prov else None) or crudo_prov or ""
    return {
        "backend_id": be.get("backend_id") or prov.get("backend_id", ""),
        "tool_version": be.get("tool_version", ""),
        "backend_version_status": be.get("backend_version_status", ""),
        "version_verificada": be.get("version_verificada"),
        "repository": be.get("repository", ""),
        "repository_commit": be.get("repository_commit", ""),
        "command_or_api": ej.get("command_or_api", ""),
        "argv": ej.get("argv") or [],
        "exit_status": ej.get("exit_status"),
        "raw_output_len": ej.get("raw_output_len"),
        "stderr": ej.get("stderr", "")[:400],
        "limpieza": ej.get("limpieza") or {},
        "input_artifact": prov.get("artefacto", "") or res0_source(env),
        "input_hash": prov.get("input_hash", ""),
        "transformacion": prov.get("transformacion", ""),
        "normalizador": prov.get("normalizador", ""),
        "limitaciones": prov.get("limitaciones") or ej.get("limitations") or [],
        "provenance_estado": (estado_prov or "PROVENANCE_INCOMPLETE"),
        "chain": ["result_id", "operation_id", "backend", "tool_version",
                  "repository_commit", "input_artifact", "input_hash",
                  "command_or_api", "argv", "raw_output", "transformacion",
                  "normalizador", "normalized_result"],
    }


def res0_source(env: Dict[str, Any]) -> str:
    """El artefacto del envelope, deducido de donde LO DIJA el envelope."""
    for r in (env.get("results") or []):
        if isinstance(r, dict) and r.get("source"):
            return r["source"]
    pre = env.get("precheck") or {}
    return pre.get("input_path", "") or ""


def persistir(env: Dict[str, Any], db: Optional[Any] = None,
              question: str = "") -> Optional[str]:
    """Guarda la operacion para que `explain` pueda reconstruirla.

    MEDIDO 2026-10-05 (F6): si el `result_id` colisiona, `INSERT OR REPLACE`
    pisa la fila anterior y la evidencia desaparece sin avisar. Por eso antes de
    guardar se comprueba que el id es NUEVO.

    B3: el `target` es `binary:<nombre>@<hash del artefacto>`, no un PCI. Y el
    envelope que se persiste lleva la cadena del backend completa, para que
    `explain` pueda reconstruirla sin volver a ejecutar nada.
    """
    from core import store as S
    # MEDIDO (B3): la conexion se cierra SOLO si la abrimos nosotros. Antes se
    # cerraba tambien en la rama de colision, y si el llamante habia pasado su
    # propia conexion (`persistir(env, db=c)`) se quedaba con una base
    # cerrada: un `Cannot operate on a closed database` en un sitio que no
    # tiene nada que ver con una colision.
    #
    #     una funcion que devuelve el recurso no lo destruye
    _abierta_por_nosotros = db is None
    c = db or S.conectar()
    ids = [r["result_id"] for r in env.get("results") or []
           if isinstance(r, dict) and r.get("result_id")]
    existentes = []
    for i in ids:
        if c.execute("SELECT 1 FROM results WHERE result_id=?", (i,)).fetchone():
            existentes.append(i)
    if existentes:
        if _abierta_por_nosotros:
            c.close()
        return "COLISION:%s" % ",".join(existentes)
    pre = env.get("precheck") or {}
    res0 = (env.get("results") or [{}])[0] if env.get("results") else {}
    artefacto = res0.get("source") or ""
    op_id = S.registrar(
        c,
        {"request_id": "",
         "question": question or ("inspeccionar %s" % (artefacto or "artefacto")),
         "capability": "binary.inspect",
         "scope": "binary",
         "target": target_binario(artefacto, pre.get("input_hash", ""))},
        {"operation": "binary.inspect",
         "status": env.get("status"),
         "backend": env.get("backend"),
         "ejecucion": env.get("ejecucion"),
         "provenance": env.get("provenance"),
         "precheck": pre,
         "cadena_backend": cadena_backend(env),
         "results": env.get("results") or []},
        duracion=(env.get("ejecucion") or {}).get("duration_s", 0))
    if _abierta_por_nosotros:
        c.close()
    return op_id