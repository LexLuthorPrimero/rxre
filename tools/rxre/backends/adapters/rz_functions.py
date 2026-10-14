# SPDX-License-Identifier: GPL-2.0
"""Adaptador de `binary.functions`. RXRE-1631.

## QUE CAPACIDAD CIERRA

`binary.functions`: el conjunto de funciones que un productor de
analisis descubre en un binario. Es la PRIMERA de la brecha: de las 12
capacidades declaradas `AVAILABLE` sin adapter, esta es la que mas
capacidades desbloquea (`binary.basic_blocks`, `binary.disassemble`,
`binary.xrefs` y `binary.dataflow` se apoyan en el mismo discovery), y
la que menos-produce-verbo-secundario.

## MEDIDO, NO SUPUESTO

MEDIDO 2026-10-12, `/usr/bin/ls` (ELF ET_DYN, x86-64), ambos producers:

    rizin 0.7.4    `aa; aflj` -> 202 funciones
    radare2 5.9.8  `aa; aflj` -> 201 funciones

    comunes: 200, y TODOS con offset IDENTICO (0 discrepancias)
    solo rizin:    sym.imp.isatty
    solo radare2:  sym.oputs_   (rizin lo llama sym.oputs)

La diferencia es de COBERTURA DE SIMBOLOS, no de formato ni de
direcciones. Por eso este adaptador NO declara un backend como
autoridad: ejecuta el que se le pida, declara cual fue, y deja la
diferencia en `limitaciones`. Elegir rizin "porque ve mas" seria
convertir una medicion en una regla, y la regla no se sostiene: en otro
binario puede ir al reves. Es la misma disciplina que el hallazgo 1569
(exit cero con el ejecutable equivocado) aplicada a la eleccion de
fuente.

MEDIDO tambien sobre `amdgpu.ko` (ELF ET_REL, 37 MB), que es la clase de
entrada del driver del proyecto:

    rizin   `aa; aflj` -> 49306
    rizin  `aaa; aflj` -> 49306
    radare2 `aa; aflj` -> 48417

`aa` y `aaa` dan el MISMO numero para functions. El registro ya
documenta que para `binary.xrefs` la diferencia es real (`aa` da `[]` y
`aaa` da 3): son capacidades distintas con requisitos distintos. Este
adaptador usa `aa` por defecto, que es el mas barato, y expone el verbo
como parametro porque el coste de `aaa` en un binario grande no es
despreciable.

## LOS ESTADOS, Y POR QUE `empty` NO AFIRMA AUSENCIA

`binary.functions` con 0 funciones es el caso peligroso: el producer
puede no haber ejecutado el analisis, y "no encontro funciones" no es lo
mismo que "el binario no tiene funciones". El contrato de `contract.py`
ya obliga a separar `empty` de `unsupported`, y aqui se anade la tercera
distincion que hace falta: `empty` aqui significa

    el producer se ejecuto, devolvio una lista vacia, y eso NO
    establece que el binario no tenga funciones

Se declara con esa limitacion escrita. Un `empty` sin ella seria una
afirmacion sobre el binario que nadie ha medido.

## LO QUE NO HACE

No decide que una funcion es real. Un candidato a funcion de un
analizador lineal es `FUNCTION_CANDIDATE`, no `VALIDATED_SEMANTICS`: no
se ha probado que la frontera de la funcion sea correcta. Para un
ELF ET_REL de 37 MB con 49306 candidatas, la precision por Recall no
esta medida y no se afirma.
"""
from __future__ import annotations

import json
import os
import re
import struct
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, "..", ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from backends import registry  # noqa: E402
from backends.contract import (  # noqa: E402
    BK_BLOCKED, BK_EMPTY, BK_ERROR, BK_INVALID, BK_OK, BK_UNSUPPORTED,
    BASIC_BLOCK, FUNCTION_CANDIDATE, Backend, sha256_de, sha256_texto,
)

#: Los CLIs meten secuencias ANSI; sus `[` falsean la puerta de
#: busqueda de la lista JSON (MEDIDO 2026-10-12).
ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")

#: MEDIDO 2026-10-12, host Fedora 44. El recuento NO es unajerarquia: es
#: lo que se Midio en estas entradas concretas, y se declara como tal para
#: que quien lo lea sepa que depende del binario.
DIFERENCIA_MEDIDA = {
    "fecha": "2026-10-12",
    "binario": "/usr/bin/ls (ELF ET_DYN x86-64)",
    "rizin": 202,
    "radare2": 201,
    "comunes": 200,
    "comunes_con_offset_distinto": 0,
    "solo_rizin": ["sym.imp.isatty"],
    "solo_radare2": ["sym.oputs_"],
    "lectura": "la diferencia es de COBERTURA DE SIMBOLOS, no de "
               "direcciones: los 200 comunes coinciden en offset. "
               "NINGUN backend es autoridad; se declara el que se uso.",
}

#: `aflj` devuelve tipos `sym`, `fcn` y `loc`. `sym` son simbolos que el
#: loader做了 entrada pero que analizandolos septon como FUNCION.
#: MEDIDO 2026-10-12, `/usr/bin/ls` con `aa; afbj`. Dos bloques de
#: diferencia entre producers. Se DECLARA; no se promedia ni se elige.
DIFERENCIA_BLOQUES = {
    "fecha": "2026-10-12", "binario": "/usr/bin/ls (ELF ET_DYN)",
    "alcance": "funcion `main`, no el binario entero",
    "rizin": 388, "radare2": 386, "delta": 2,
    "punto_de_entrada": {"rizin": 1, "radare2": 1},
    "lectura": "diferencia de RECUBRIMIENTO entre producers; ninguno es "
               "autoridad. El recuento alto no dice nada sobre la "
               "precision: no hay verdad de suelo aqui. Y el alcance es "
               "UNA FUNCION: `afbj` no emite los bloques de todo el "
               "fichero, se.seekea y se pide una.",
}


def _backends_de(capacidad: str) -> List[str]:
    """Que producers declara esta capacidad (import perezoso: circular)."""
    try:
        from backends import dispatch as _d
        return sorted(_d.esta_permitida(capacidad).get("backends") or [])
    except Exception:
        return []


TIPOS_FUNCION = ("fcn",)
TIPOS_ENTRADA = ("sym", "loc")


def _elf_tipo(artefacto: str) -> str:
    """`ET_REL`, `ET_EXEC`, `ET_DYN`... leyendo solo la cabecera.

    No invoca `readelf`: aqui no hace falta saber que hay dentro, solo
    de que clase es el objeto, y la cabecera lo dice sin arrancar otro
    proceso."""
    try:
        with open(artefacto, "rb") as fh:
            h = fh.read(20)
    except OSError:
        return ""
    if len(h) < 18 or h[:4] != b"\x7fELF":
        return ""
    if h[4] == 2:
        e_type, = struct.unpack_from("<H" if h[5] == 1 else ">H", h, 16)
    else:
        e_type, = struct.unpack_from("<H" if h[5] == 1 else ">H", h, 16)
    return {1: "ET_REL", 2: "ET_EXEC", 3: "ET_DYN",
            4: "ET_CORE"}.get(e_type, "ET_%d" % e_type)


def _backends_de(capacidad: str) -> List[str]:
    """Que producers declara ESTA capacidad.

    Se pregunta al dispatch, que es quien tiene el mapa capacidad ->
    producers. Import perezoso a proposito: `dispatch` importa los
    adapters por el campo `modulo`, y un import en cabecera aqui seria
    circular.
    """
    try:
        from backends import dispatch as _d          # perezoso: circular
        return sorted(_d.esta_permitida(capacidad).get("backends") or [])
    except Exception:
        return []


def _argv(backend_id: str, exe: str, artefacto: str, verb: str,
          salida_cmd: str = "aflj") -> List[str]:
    """El comando correcto para cada producer.

    MEDIDO: `rizin -qc -e scr.color=0 'cmd'` NO funciona; `-qc` se come
    el `-e` y sale VACIO sin error. La forma que funciona es
    `rizin -q -N -e scr.color=0 -c 'cmd'`. Es la misma clase de error que
    `aa` frente a `aaa`: un `empty` por invocacion incorrecta. El
    registro ya lo declara para rizin; aqui se aplica en codigo.
    """
    # `salida_cmd` es lo que se pide al producer DESPUES del analisis. Se
    # separo del verbo porque las capacidades de este modulo piden
    # comandos distintos: `functions` quiere `aflj` y `basic_blocks` quiere
    # `afbj`. Con el sufijo pegado al verbo, `basic_blocks` terminaba
    # ejecutando `aa; afbj; aflj`, que devuelve la lista de FUNCIONES y no
    # la de bloques: una respuesta ok con el contenido equivocado, que es
    # justo lo que no debe pasar. MEDIDO 2026-10-12 al escribir sus
    # pruebas.
    cmd = "%s; %s" % (verb, salida_cmd)
    if backend_id == "rizin":
        return [exe, "-q", "-N", "-e", "scr.color=0", "-c", cmd,
                "-A", artefacto]
    return [exe, "-q", "-e", "scr.color=0", "-c", cmd,
            "-A", artefacto]


def functions(artefacto: str, backend_id: str = "rizin",
              timeout: int = 900, verb: str = "aa", limite: int = 0,
              fixture_json: str = "") -> Dict[str, Any]:
    """La operacion. SIEMPRE los seis canales del contrato."""
    # `backend_id` viene de la ENTRADA del consumidor, no del codigo. Por
    # eso un id desconocido NO es un error de programacion sino
    # `invalid_input`, y el envelope debe decirlo en vez de dejar que el
    # `KeyError` de `registry.get` suba como traceback. MEDIDO: asi lo
    # encontraron las pruebas de RXRE-1631 al pedir
    # `backend_id="herramienta_que_no_existe"`.
    #
    # La lista de los que SI existen va en la respuesta: el que llama
    # necesita saber que nombre escribir, no solo que el suyo falla.
    try:
        ent = registry.get(backend_id)
    except KeyError:
        return {
            "status": BK_INVALID,
            "precheck": {"ok": False, "backend_id": backend_id},
            "limitations": [
                "backend desconocido: %r" % backend_id,
                "los declarados son: %s"
                % ", ".join(sorted(registry.backends())),
                "esta capacidad declara producers para: %s"
                % (", ".join(_backends_de("binary.functions")) or "?"),
            ],
        }
    b: Backend = ent["backend"]

    pre = {"input_existe": os.path.isfile(artefacto),
           "input_es_elf": False, "elf_tipo": "",
           "input_hash": "",
           "backend_existe": b.existe(),
           "backend_path": b.path() or "",
           "verb": verb,
           "usa_fixture": bool(fixture_json),
           "ok": False}

    if fixture_json:
        if not os.path.isfile(fixture_json):
            return {"status": BK_INVALID, "precheck": pre,
                    "limitations": ["no existe el fixture: %s"
                                    % fixture_json]}
    else:
        if not pre["input_existe"]:
            return {"status": BK_INVALID, "precheck": pre,
                    "limitations": ["la entrada no existe: %s" % artefacto]}
        pre["elf_tipo"] = _elf_tipo(artefacto)
        if not pre["elf_tipo"]:
            return {"status": BK_INVALID, "precheck": pre,
                    "limitations": [
                        "la entrada no es un ELF: %s" % artefacto,
                        "no se invoco al producer: `aflj` sobre un "
                        "no-ELF no puede discoverir funciones"]}
        pre["input_es_elf"] = True
        pre["input_hash"] = sha256_de(artefacto)
        if not pre["backend_existe"]:
            return {"status": BK_BLOCKED, "precheck": pre,
                    "limitations": ["el backend %s no esta en PATH"
                                    % backend_id]}
    pre["ok"] = True

    # --- EJECUCION ------------------------------------------------------
    if fixture_json:
        with open(fixture_json, encoding="utf-8") as fh:
            bruto = fh.read()
        rc, so, se, argv, dur = 0, "", "modo fixture: producer simulado", \
            ["<fixture>", fixture_json], 0.0
        timedout = False
        ident_backend = "fixture"
    else:
        argv = _argv(backend_id, b.path(), artefacto, verb)
        t0 = time.time()
        timedout = False
        try:
            p = subprocess.run(argv, capture_output=True, text=True,
                               timeout=timeout)
            rc, so, se = p.returncode, p.stdout or "", p.stderr or ""
        except subprocess.TimeoutExpired:
            rc, so, se, timedout = (None, "",
                                   "timeout a los %ds" % timeout, True)
        except OSError as exc:
            rc, so, se = None, "", str(exc)
        dur = round(time.time() - t0, 3)

    ejec = {
        "backend_id": ident_backend if fixture_json else backend_id,
        "operation": "binary.functions",
        "command_or_api": " ".join(argv),
        "argv": argv,
        "exit_status": rc,
        "stderr": se.strip()[:400],
        "timeout": timedout,
        "duration_s": dur,
        "verb": verb,
    }
    ident = b.identidad()

    if timedout:
        ejec.update({"status": BK_BLOCKED,
                     "limitations": ["timeout a los %ds: el analisis de un "
                                     "ET_REL grande no es barato. MEDIDO: "
                                     "amdgpu.ko con `aa` tarda minutos"
                                     % timeout]})
        return {"status": BK_BLOCKED, "precheck": pre, "ejecucion": ejec,
                "backend": ident,
                "limitations": ejec.get("limitations", []),
                "provenance": "PROVENANCE_INCOMPLETE: no hay salida"}

    if rc not in (0, None):
        ejec.update({"status": BK_ERROR,
                     "limitations": ["el producer salio con rc=%s: %s"
                                     % (rc, (se.strip() or so.strip())[:300])]})
        return {"status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
                "backend": ident,
                "limitations": ejec.get("limitations", []),
                "provenance": "PROVENANCE_INCOMPLETE: producer fallo"}

    # --- PARSEO ---------------------------------------------------------
    # MEDIDO 2026-10-12 (RXRE-1632): los escapes ANSI CONTIENEN `[`
    # (`\x1b[0;32m`). Buscar la lista sobre texto crudo puede caer
    # DENTRO de un escape, y `json.loads` recibe entonces
    # `\x1b[0;32m...`: un error que no menciona el ANSI. Se limpia
    # ANTES de buscar.
    texto = ANSI.sub("", (bruto if fixture_json else so) or "")
    inicio = texto.find("[")
    if inicio < 0:
        # Sin `[` no hay lista. Puede ser banner, ANSI o error silencioso.
        ejec.update({"status": BK_ERROR,
                     "limitations": [
                         "la salida no contiene una lista JSON. MEDIDO: sin "
                         "`-e scr.color=0` los CLIs meten ANSI y el parseo "
                         "falla; si el comando lleva ese flag y aun asi "
                         "falla, la causa es otra.",
                         "stdout (primeros 200): %s"
                         % re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "",
                                   texto)[:200]]})
        return {"status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
                "backend": ident,
                "provenance": "PROVENANCE_INCOMPLETO: salida no parseable"}

    try:
        crudas = json.loads(texto[inicio:])
    except ValueError as exc:
        ejec.update({"status": BK_ERROR,
                     "limitations": ["JSON mal formado: %s" % exc]})
        return {"status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
                "backend": ident,
                "provenance": "PROVENANCE_INCOMPLETO: JSON invalido"}
    if not isinstance(crudas, list):
        ejec.update({"status": BK_ERROR,
                     "limitations": ["`aflj` devolvio %s, no una lista"
                                     % type(crudas).__name__]})
        return {"status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
                "backend": ident,
                "provenance": "PROVENANCE_INCOMPLETO: forma inesperada"}

    # --- NORMALIZACION --------------------------------------------------
    # Se conservan TODOS los campos del producer. `valor` anade un mapa
    # comun entre backends, pero `crudo` deja el elemento intacto: dos
    # producers con distinto esquema no se vuelven iguales de verdad.
    funciones: List[Dict[str, Any]] = []
    n_sym = n_loc = 0
    for f in crudas:
        if not isinstance(f, dict):
            continue
        tipo = f.get("type") or ""
        if tipo == "sym":
            n_sym += 1
        elif tipo == "loc":
            n_loc += 1
        funciones.append({
            "name": f.get("name") or "",
            "offset": f.get("offset"),
            "size": f.get("size"),
            "realsz": f.get("realsz"),
            "nbbs": f.get("nbbs"),
            "nargs": f.get("nargs"),
            "cc": f.get("cc"),
            "type": tipo,
            "crudo": f,
        })
    if limite and limite > 0:
        funciones = funciones[:limite]

    cobertura = {
        "n_total": len(crudas),
        "n_sym": n_sym,
        "n_fcn": sum(1 for f in funciones if f.get("type") == "fcn"),
        "n_loc": n_loc,
        "n_normalizadas": len(funciones),
        "analizadas_como_funcion": sum(
            1 for f in funciones if f.get("type") == "fcn"),
    }

    lim = [
        "un candidato a funcion de un analizador lineal es "
        "FUNCTION_CANDIDATE, no semantica validada: no se ha probado que "
        "la frontera de la funcion sea correcta (contract.puede_declarar).",
        "la cobertura NO esta medida. Un recuento alto no dice nada sobre "
        "la precision: para Recall habria que contrastar contra verdad de "
        "suelo, y no existe aqui.",
        "el producer es %s y su salida se declara como tal: NINGUN backend "
        "es autoridad. MEDIDO: rizin %d vs radare2 %d sobre %s, con la "
        "diferencia de cobertura registrada en `diferencia_medida`."
        % (backend_id, DIFERENCIA_MEDIDA["rizin"],
           DIFERENCIA_MEDIDA["radare2"], DIFERENCIA_MEDIDA["binario"]),
    ]

    if not funciones:
        # EL CASO PELIGROSO. `empty` aqui NO afirma que el binario no
        # tenga funciones.
        lim += [
            "0 candidatas. ESTO NO ESTABLECE que el binario no tenga "
            "funciones: el producer se ejecuto y devolvio una lista "
            "vacia, que tambien es lo que devuelve un analisis que no "
            "llego a correr. Antes de leer esto como ausencia, comprobar "
            "el verbo de analisis y comparar con el otro backend.",
        ]
        ejec.update({"status": BK_EMPTY, "limitations": lim})
        return {"status": BK_EMPTY, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "results": [], "n_functions": 0,
                "cobertura": cobertura, "limitations": lim,
                "diferencia_medida": DIFERENCIA_MEDIDA,
                "provenance": "completa"}

    version = b.identidad().get("tool_version", "")
    artefacto_ref = artefacto if not fixture_json else fixture_json
    valor = {"n_funciones": len(funciones), "cobertura": cobertura,
             "funciones": funciones[:2000]}
    rid = "res_functions_" + sha256_texto(
        "%s|%s|%s|%d" % (artefacto_ref, backend_id, verb,
                         len(crudas)))[:12]
    res = {
        "result_id": rid,
        "type": FUNCTION_CANDIDATE,
        "value": valor,
        "source": artefacto_ref,
        "location": {"file": os.path.basename(artefacto_ref)},
        "scope": "binary",
        "tool": backend_id,
        "tool_version": version,
        "input": {"path": artefacto_ref,
                  "sha256": pre.get("input_hash", "")},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "artifact": artefacto_ref,
        "artifact_hash": pre.get("input_hash", ""),
        "status": "declared",
        "limitations": lim,
    }
    ejec.update({"status": BK_OK})
    return {"status": BK_OK, "precheck": pre, "ejecucion": ejec,
            "backend": ident, "results": [res], "n_functions": len(funciones),
            "cobertura": cobertura, "limitations": lim,
            "diferencia_medida": DIFERENCIA_MEDIDA,
            "provenance": "completa"}

# ---------------------------------------------------------------------------
# `binary.basic_blocks`. RXRE-1633.
#
# Va aqui y no en `rz_container` a proposito. MEDIDO 2026-10-12: las
# capacidades se parten en dos por si necesitan analisis de funciones.
# `iSj`, `iij`, `iEj`, `izj` e `isj` responden SIN `aa`; `afbj` no. La
# separacion es del GRAFO, no una cuestion de donde queda el fichero:
# basic_blocks necesita el mapa de funciones que produce `aflj`.

def basic_blocks(artefacto: str, funcion: str = "",
                 backend_id: str = "rizin",
                 timeout: int = 900, verb: str = "aa", limite: int = 0,
                 fixture_json: str = "") -> Dict[str, Any]:
    """`binary.basic_blocks`: los bloques basicos de UNA FUNCION.

    Un bloque basico es un tramo de codigo SIN bifurcacion interna: se
    entra por arriba y se sale por abajo. No es una funcion, y no es una
    instruccion. Confundir los tres niveles es el error clasico al
    construir un CFG encima.

    ## POR QUE ES DE UNA FUNCION Y NO DEL BINARIO ENTERO

    MEDIDO 2026-10-12, rizin 0.7.4 sobre /bin/ls. Se seekeo a distintas
    posiciones y se comparo:

        `aa; afbj`              -> 1     (la funcion en la posicion actual)
        `aa; s entry0; afbj`    -> 1
        `aa; s main; afbj`      -> 388   (esa funcion)
        `aa; afbj @@ fcn`       -> SIN JSON (el iterador no emite JSON)
        `aa; afbj @@=fcn`       -> SIN JSON
        `aa; afb*`              -> SIN JSON (texto)

    Es decir: `afbj` es FUNCTION-SCOPED y NO existe un comando JSON que
    de los bloques de todo el binario. La version anterior de esta
    capacidad corria `aa; afbj` sin destino y devolvia 1 bloque
    llamandolo "los bloques de todas las funciones". Eso es peor que no
    entregar nada: un CFG de un bloque parece un CFG valido y no lo es.

    Dos salidas posibles y aqui se toma la HONESTA:

      (a) bloques de una funcion, con la funcion como parametro. Es lo
          que el producer sabe dar, es barato (0.9 s) y es lo que se
          necesita para analizar una funcion.
      (b) iterar una invocacion por funcion: 202 funciones en /bin/ls,
          202 invocaciones. Cara, y el coste crece con el binario.

    Se toma (a) y se DECLARA (b) como no hecha, con su motivo. Volver
    cuando el coste de (b) se justifique: sobre un ET_REL de 37 MB con
    ~49000 candidatas, son ~49000 invocaciones.

    MEDIDO, el recuento depende de donde se mire: 388 bloques en `main`
    frente a 1 en el entrypoint. Un recuento alto NO dice nada sobre la
    precision: no hay verdad de suelo con la que contrastarlo.
    """
    try:
        ent = registry.get(backend_id)
    except KeyError:
        return {"status": BK_INVALID,
                "precheck": {"ok": False, "backend_id": backend_id},
                "limitations": [
                    "backend desconocido: %r" % backend_id,
                    "los declarados son: %s"
                    % ", ".join(sorted(registry.backends())),
                    "esta capacidad declara producers para: %s"
                    % (", ".join(sorted(_backends_de("binary.basic_blocks")))
                       or "?")]}
    b: Backend = ent["backend"]

    etipo = "" if fixture_json else _elf_tipo(artefacto)
    pre = {"input_existe": os.path.isfile(artefacto) or bool(fixture_json),
           "input_es_elf": bool(etipo), "elf_tipo": etipo, "input_hash": "",
           "backend_existe": b.existe(), "backend_path": b.path() or "",
           "usa_fixture": bool(fixture_json), "ok": False}

    if fixture_json:
        if not os.path.isfile(fixture_json):
            return {"status": BK_INVALID, "precheck": pre,
                    "limitations": ["no existe el fixture: %s"
                                    % fixture_json]}
    else:
        if not pre["input_existe"]:
            return {"status": BK_INVALID, "precheck": pre,
                    "limitations": ["la entrada no existe: %s" % artefacto]}
        if not etipo:
            return {"status": BK_INVALID, "precheck": pre,
                    "limitations": [
                        "la entrada no es un ELF: %s" % artefacto,
                        "no se invoco al producer: `afbj` sobre un no-ELF "
                        "no puede descubrir bloques basicos"]}
        pre["input_hash"] = sha256_de(artefacto)
        if not pre["backend_existe"]:
            return {"status": BK_BLOCKED, "precheck": pre,
                    "limitations": ["el backend %s no esta en PATH"
                                    % backend_id]}
    pre["ok"] = True

    if fixture_json:
        with open(fixture_json, encoding="utf-8") as fh:
            salida = fh.read()
        rc, se, argv, dur = 0, "modo fixture: producer simulado", \
            ["<fixture>", fixture_json], 0.0
        timedout, ident_backend = False, "fixture"
    else:
        # MEDIDO: `afbj` necesita el mapa de funciones, asi que el verbo de
        # analisis va delante. Sin el, rizin devuelve `[]` - y `[]` aqui
        # significa lo mismo que en `functions`: que no se sabe, no que no
        # haya bloques.
        # MEDIDO: `afbj` sin destino da los bloques de la funcion en la
        # posicion ACTUAL, que es el entrypoint tras abrir el fichero. Se
        # pide la funcion explicitamente para que el resultado sea el que
        # se pidio y no el que salio por defecto.
        cmd = "afbj" if not funcion else "afbj @ %s" % funcion
        argv = _argv(backend_id, b.path(), artefacto, verb,
                     salida_cmd=cmd)
        t0 = time.time()
        timedout = False
        try:
            p = subprocess.run(argv, capture_output=True, text=True,
                               timeout=timeout)
            rc, salida, se = p.returncode, p.stdout or "", p.stderr or ""
        except subprocess.TimeoutExpired:
            rc, salida, se, timedout = (None, "", "timeout", True)
        except OSError as exc:
            rc, salida, se = None, "", str(exc)
        dur = round(time.time() - t0, 3)

    ident = b.identidad()
    ejec = {"backend_id": ident_backend if fixture_json else backend_id,
            "operation": "binary.basic_blocks",
            "command_or_api": " ".join(argv), "argv": argv,
            "exit_status": rc, "stderr": ANSI.sub("", se).strip()[:400],
            "timeout": timedout, "duration_s": dur, "verb": verb}

    if timedout:
        ejec.update({"status": BK_BLOCKED, "limitations": [
            "timeout a los %ds. MEDIDO: `aa` + `afbj` sobre un ET_REL de "
            "37 MB es un trabajo de minutos, no de segundos." % timeout]})
        return {"status": BK_BLOCKED, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "limitations": ejec["limitations"],
                "provenance": "PROVENANCE_INCOMPLETE: no hay salida"}
    if rc not in (0, None):
        ejec.update({"status": BK_ERROR, "limitations": [
            "el producer salio con rc=%s: %s"
            % (rc, ANSI.sub("", se).strip()[:300] or salida.strip()[:300])]})
        return {"status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "limitations": ejec["limitations"],
                "provenance": "PROVENANCE_INCOMPLETE: producer fallo"}

    texto = ANSI.sub("", salida or "")
    inicio = texto.find("[")
    if inicio < 0:
        ejec.update({"status": BK_ERROR, "limitations": [
            "la salida no contiene una lista JSON. MEDIDO: sin "
            "`-e scr.color=0` los CLIs meten ANSI y el parseo falla.",
            "stdout (primeros 200): %s" % texto[:200]]})
        return {"status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "limitations": ejec["limitations"],
                "provenance": "PROVENANCE_INCOMPLETE: salida no parseable"}
    try:
        crudos = json.loads(texto[inicio:])
    except ValueError as exc:
        ejec.update({"status": BK_ERROR,
                     "limitations": ["JSON mal formado: %s" % exc]})
        return {"status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "limitations": ejec["limitations"],
                "provenance": "PROVENANCE_INCOMPLETE: JSON invalido"}
    if not isinstance(crudos, list):
        ejec.update({"status": BK_ERROR, "limitations": [
            "`afbj` devolvio %s, no una lista" % type(crudos).__name__]})
        return {"status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "limitations": ejec["limitations"],
                "provenance": "PROVENANCE_INCOMPLETE: forma inesperada"}

    bloques = [{"crudo": x} for x in crudos if isinstance(x, dict)]
    if limite and limite > 0:
        bloques = bloques[:limite]

    lim = [
        "un bloque basico es un tramo SIN bifurcacion interna: se entra "
        "por arriba y se sale por abajo. NO es una funcion y NO es una "
        "instruccion. Los tres niveles se confunden con facilidad.",
        "una arista es una RELACION CANDIDATA: que un bloque salte a otro "
        "no prueba que el camino sea alcanzable en runtime.",
        "el alcance es UNA FUNCION%s, no el binario entero. MEDIDO: no "
        "existe comando JSON que de los bloques de todo el fichero; "
        "`afbj` es function-scoped y los iteradores `@@ fcn` no emiten "
        "JSON. Para el conjunto completo haria falta una invocacion por "
        "funcion." % (" (%s)" % funcion if funcion else " (la del punto de "
                      "entrada)"),
        "el producer es %s y se declara como tal. NINGUN backend es "
        "autoridad: MEDIDO 2026-10-12, rizin `afbj` -> 388 bloques y "
        "radare2 -> 386 sobre /bin/ls. Se declara la diferencia en vez de "
        "elegir uno." % ("fixture" if fixture_json else backend_id),
    ]
    if etipo == "ET_REL":
        lim.append("la entrada es ET_REL: los offsets son internos al "
                   "objeto, no direcciones de carga del sistema.")

    if not bloques:
        lim.append("0 bloques. ESTO NO ESTABLECE que el binario no tenga "
                   "bloques: `afbj` sin el mapa de funciones devuelve la "
                   "misma lista vacia. MEDIDO: el verbo de analisis va "
                   "delante a proposito por esto.")
        ejec.update({"status": BK_EMPTY, "limitations": lim})
        return {"status": BK_EMPTY, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "results": [], "n_bloques": 0,
                "limitations": lim, "provenance": "completa"}

    ref = fixture_json or artefacto
    res = {
        "result_id": "res_basicblocks_" + sha256_texto(
            "%s|%s|%d" % (ref, backend_id, len(crudos)))[:12],
        "type": BASIC_BLOCK,
        "value": {"n_bloques": len(bloques), "bloques": bloques[:2000]},
        "source": ref, "location": {"file": os.path.basename(ref)},
        "scope": "binary",
        "tool": "fixture" if fixture_json else backend_id,
        "tool_version": ident.get("tool_version", ""),
        "input": {"path": ref, "sha256": pre.get("input_hash", "")},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "artifact": ref, "artifact_hash": pre.get("input_hash", ""),
        "status": "declared", "limitations": lim, "duration_s": dur,
    }
    ejec.update({"status": BK_OK})
    return {"status": BK_OK, "precheck": pre, "ejecucion": ejec,
            "backend": ident, "results": [res], "n_bloques": len(bloques),
            "limitations": lim, "provenance": "completa",
            "diferencia_medida": DIFERENCIA_BLOQUES}
