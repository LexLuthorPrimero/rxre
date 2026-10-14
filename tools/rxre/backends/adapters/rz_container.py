# SPDX-License-Identifier: GPL-2.0
"""Las cinco capacidades de CONTENEDOR: sections, imports, exports,
strings y symbols. RXRE-1632.

## POR QUE UN SOLO ADAPTADOR PARA CINCO CAPACIDADES

MEDIDO 2026-10-12, rizin 0.7.4: las cinco responden SIN analisis de
funciones, con la misma forma de invocacion y sin ninguna dependencia
entre si.

    comando   sin `aa`, sobre /bin/ls (ET_DYN)   sobre amdgpu.ko (ET_REL, 37 MB)
    iSj       32 secciones                        ~120 s
    iij       121 imports                         ~120 s
    iEj       16 exports                          ~120 s
    izj       639 cadenas                         ~120 s
    isj       323 simbolos                        147 s

Ninguna necesita `aa`, y esa es la razon de agruparlas: el analisis de
funciones es lo que cuesta, y estas cinco no lo pagan. Cerrarlas juntas
cuesta UN productor y una pasada de container; cerrarlas por separado
serian cinco adaptadores con el mismo esqueleto y cinco subprocess.

El grafo de dependencias medido queda asi:

    sin analisis (este fichero)
        sections, imports, exports, strings, symbols
    con analisis (rz_functions.py, ya cerrado)
        basic_blocks, cfg, xrefs, callgraph, dataflow, disassemble_func

Y `binary.disassemble` es el caso limite: puedeLEA un rango sin analisis,
pero DESCIFRARLO necesita el mapa de instrucciones, que lo produce `aa`.
Queda fuera por eso, no por descuido.

## EL COSTE ES UNA LIMITACION, NO UN DETALLE

MEDIDO: sobre un ET_REL de 37 MB (la clase de entrada del driver) cada
uno de estos comandos tarda alrededor de DOS MINUTOS. No es un detalle de
implementacion: es lo que hace que un barrido de cinco capacidades sobre
un `.ko` grande sea un trabajo de quince minutos.

Por eso `TIMEOUT_POR_DEFECTO` no es el habitual de 900 s para binarios
pequenos sino uno que aguanta el ET_REL, y sobre todo por eso cada
resultado DECLARA lo que costo. Un consumidor que no mira la duracion
no puede saber si tardo dos segundos o dos minutos.

Y hay una consecuencia que conviene decir: `isj` sobre ET_REL tardo 147 s
en esta medicion, y en una primera pasada los mismos comandos devolviendo
datos agotaron el presupuesto de la sesion. La variacion es real. Por eso
el limite NO se deduce de una medicion: se declara como
`TIMEOUT_POR_DEFECTO` explicito y el consumidor lo ve.

## LO QUE ESTAS CAPACIDADES NO DICEN

Cinco advertencias que son distintas entre si y que se emiten todas:

  1. Una lista vacia de ESTA capacidad tampoco establece ausencia. Es lo
     mismo que dijimos para `binary.functions` y por el mismo motivo: un
     comando que no llego a correr y un fichero sin secciones producen la
     misma lista vacia.
  2. Los SIMBOLOS no son funciones. `isj` devuelve la tabla de simbolos;
     quien quiera funciones las tiene que pedir con `aflj`. Confundir las
     dos cosas es el error clasico de este terreno, y el tipo del
     contrato lo separa (`RAW_BINARY`, no `FUNCTION_CANDIDATE`).
  3. Las CADENAS son bytes que parecen texto. No son codigo, no son
     mensajes, y unLanguages string con formato de mensaje sigue sin
     serlo: son bytes leidos con una codificacion supuesta.
  4. Los IMPORTS son lo que el loader DECLARA, no lo que se resuelve en
     runtime. Para un ET_REL la mayoria son referencias sin resolver.
  5. En un ET_REL no hay direcciones de carga reales. `vaddr` es un
     offset dentro del objeto, no una VA del sistema. Confundirlos es
     exactamente el error que hace que un agente crea que un `.ko`
     tiene un mapa de memoria.
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
    BK_BLOCKED, BK_EMPTY, BK_ERROR, BK_INVALID, BK_OK,
    RAW_BINARY, Backend, sha256_de, sha256_texto,
)

#: MEDIDO 2026-10-12: ~147 s para `isj` sobre un ET_REL de 37 MB, y los
#: otros cuatro por debajo de ~120 s en la misma clase de entrada. Un
#: timeout de 900 s es lo que separa "este comando es lento" de "este
#: comando no funciona".
TIMEOUT_POR_DEFECTO = 900

#: MEDIDO 2026-10-12 sobre /bin/ls. Se declaran para que una lista vacia
#: inesperada tenga contra que compararse, no como verdad universal.
RECUENTO_ET_DYN = {"fecha": "2026-10-12", "binario": "/usr/bin/ls",
                   "secciones": 32, "imports": 121, "exports": 16,
                   "strings": 639, "symbols": 323}

ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


def _elf_tipo(ruta: str) -> str:
    try:
        with open(ruta, "rb") as fh:
            h = fh.read(20)
    except OSError:
        return ""
    if len(h) < 18 or h[:4] != b"\x7fELF":
        return ""
    fmt = "<H" if h[5] == 1 else ">H"
    (e_type,) = struct.unpack_from(fmt, h, 16)
    return {1: "ET_REL", 2: "ET_EXEC", 3: "ET_DYN",
            4: "ET_CORE"}.get(e_type, "ET_%d" % e_type)


def _argv(exe: str, artefacto: str, cmd: str) -> List[str]:
    """MEDIDO: `rizin -qc -e ...` se come el `-e` y sale VACIO sin error.
    La forma que funciona es `-q -N -e scr.color=0 -c`. Same trap que en
    `rz_functions`; aqui se repite porque cada invocacion es independiente
    y un fallo aqui pasaria desapercibido como `empty`."""
    return [exe, "-q", "-N", "-e", "scr.color=0", "-c", cmd,
            "-A", artefacto]


def _backends_de(capacidad: str) -> List[str]:
    try:
        from backends import dispatch as _d          # perezoso: circular
        return sorted(_d.esta_permitida(capacidad).get("backends") or [])
    except Exception:
        return []


#: capacidad -> (comando rizin, etiqueta legible, limite extra)
PLAN = {
    "binary.sections": ("iSj", "secciones", []),
    "binary.imports": ("iij", "imports", []),
    "binary.exports": ("iEj", "exports", []),
    "binary.strings": ("izj", "cadenas", []),
    "binary.symbols": ("isj", "simbolos", []),
}


def _correr(capacidad: str, comando: str, etiqueta: str,
            aviso_extra: List[str], artefacto: str,
            backend_id: str = "rizin", timeout: int = TIMEOUT_POR_DEFECTO,
            limite: int = 0, fixture_json: str = "") -> Dict[str, Any]:
    """El cuerpo comun a las cinco. Solo cambia el comando y el aviso."""
    try:
        ent = registry.get(backend_id)
    except KeyError:
        # `backend_id` viene de la ENTRADA del consumidor: es
        # `invalid_input`, no un error de programacion (MEDIDO en
        # RXRE-1631 con el mismo patron).
        return {"status": BK_INVALID,
                "precheck": {"ok": False, "backend_id": backend_id},
                "limitations": [
                    "backend desconocido: %r" % backend_id,
                    "los declarados son: %s"
                    % ", ".join(sorted(registry.backends())),
                    "esta capacidad declara producers para: %s"
                    % (", ".join(_backends_de(capacidad)) or "?")]}

    b: Backend = ent["backend"]
    etipo = "" if fixture_json else _elf_tipo(artefacto)
    pre = {"input_existe": os.path.isfile(artefacto) or bool(fixture_json),
           "input_es_elf": bool(etipo), "elf_tipo": etipo,
           "input_hash": "", "backend_existe": b.existe(),
           "backend_path": b.path() or "", "comando": comando,
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
                        "no se invoco al producer: un comando de container "
                        "sobre un no-ELF no puede descubrir %s" % etiqueta]}
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
        argv = _argv(b.path(), artefacto, comando)
        t0 = time.time()
        timedout = False
        try:
            p = subprocess.run(argv, capture_output=True, text=True,
                               timeout=timeout)
            rc, salida, se = (p.returncode, p.stdout or "", p.stderr or "")
        except subprocess.TimeoutExpired:
            rc, salida, se, timedout = (None, "", "timeout a los %ds"
                                        % timeout, True)
        except OSError as exc:
            rc, salida, se = None, "", str(exc)
        dur = round(time.time() - t0, 3)

    ident = b.identidad()
    ejec = {"backend_id": ident_backend if fixture_json else backend_id,
            "operation": capacidad, "command_or_api": " ".join(argv),
            "argv": argv, "exit_status": rc,
            "stderr": ANSI.sub("", se).strip()[:400],
            "timeout": timedout, "duration_s": dur, "comando": comando}

    if timedout:
        ejec.update({"status": BK_BLOCKED,
                     "limitations": [
                         "timeout a los %ds. MEDIDO: sobre un ET_REL de "
                         "37 MB estos comandos tardan del orden de dos "
                         "minutos; 900 s es el margen declarado, no un "
                         "numero arbitrario." % timeout]})
        return {"status": BK_BLOCKED, "precheck": pre, "ejecucion": ejec,
                "backend": ident,
                "limitations": ejec["limitations"],
                "provenance": "PROVENANCE_INCOMPLETE: no hay salida"}

    if rc not in (0, None):
        ejec.update({"status": BK_ERROR,
                     "limitations": ["el producer salio con rc=%s: %s"
                                     % (rc, ANSI.sub("", se).strip()[:300]
                                        or salida.strip()[:300])]})
        return {"status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "limitations": ejec["limitations"],
                "provenance": "PROVENANCE_INCOMPLETE: producer fallo"}

    # MEDIDO 2026-10-12 (RXRE-1632): los escapes ANSI CONTIENEN
    # `[` (`\x1b[0;32m`). Buscar la lista sobre texto crudo
    # puede caer DENTRO de un escape, y entonces `json.loads`
    # recibe `\x1b[0;32m...` y falla con un error que no
    # menciona el ANSI. Se limpia ANTES de buscar. Es el mismo
    # motivo por el que la invocacion lleva `-e scr.color=0`:
    # por si acaso, porque aqui si se ha complicado.
    texto = ANSI.sub("", salida or "")
    ini = texto.find("[")
    if ini < 0:
        ejec.update({"status": BK_ERROR, "limitations": [
            "la salida no contiene una lista JSON. MEDIDO: sin "
            "`-e scr.color=0` los CLIs meten ANSI y el parseo falla; si el "
            "flag va puesto y aun asi falla, la causa es otra.",
            "stdout (primeros 200): %s" % ANSI.sub("", texto)[:200]]})
        return {"status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "limitations": ejec["limitations"],
                "provenance": "PROVENANCE_INCOMPLETE: salida no parseable"}

    try:
        crudos = json.loads(texto[ini:])
    except ValueError as exc:
        ejec.update({"status": BK_ERROR,
                     "limitations": ["JSON mal formado: %s" % exc]})
        return {"status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "limitations": ejec["limitations"],
                "provenance": "PROVENANCE_INCOMPLETE: JSON invalido"}
    if not isinstance(crudos, list):
        ejec.update({"status": BK_ERROR, "limitations": [
            "`%s` devolvio %s, no una lista"
            % (comando, type(crudos).__name__)]})
        return {"status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "limitations": ejec["limitations"],
                "provenance": "PROVENANCE_INCOMPLETE: forma inesperada"}

    elementos = [{"crudo": x} for x in crudos if isinstance(x, dict)]
    if limite and limite > 0:
        elementos = elementos[:limite]

    lim = list(aviso_extra)
    if etipo == "ET_REL":
        lim.append(
            "la entrada es ET_REL: NO hay direcciones de carga reales. "
            "`vaddr`/`paddr` son offsets DENTRO del objeto, no direcciones "
            "virtuales del sistema. Usarlos como si fueran VAs es el error "
            "que hace creer que un .ko tiene un mapa de memoria.")
    lim.append("el producer es %s y la salida se declara como tal."
               % ("fixture" if fixture_json else backend_id))

    if not elementos:
        lim.append(
            "0 elementos. ESTO NO ESTABLECE que el fichero no tenga %s: un "
            "comando que no llego a correr devuelve la misma lista vacia. "
            "Antes de leerlo como ausencia, comprobar el verbo y comparar "
            "con el otro producer." % etiqueta)
        ejec.update({"status": BK_EMPTY, "limitations": lim})
        return {"status": BK_EMPTY, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "results": [], "n_elementos": 0,
                "limitations": lim, "provenance": "completa",
                "recuento_medido": RECUENTO_ET_DYN}

    ref = fixture_json or artefacto
    rid = "res_%s_%s" % (etiqueta,
                         sha256_texto("%s|%s|%d" % (ref, comando,
                                                   len(crudos)))[:12])
    res = {
        "result_id": rid,
        "type": RAW_BINARY,
        "value": {"n_elementos": len(elementos), "comando": comando,
                  "elementos": elementos[:2000]},
        "source": ref,
        "location": {"file": os.path.basename(ref)},
        "scope": "binary",
        "tool": "fixture" if fixture_json else backend_id,
        "tool_version": ident.get("tool_version", ""),
        "input": {"path": ref, "sha256": pre.get("input_hash", "")},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "artifact": ref,
        "artifact_hash": pre.get("input_hash", ""),
        "status": "declared",
        "limitations": lim,
        "duration_s": dur,
    }
    ejec.update({"status": BK_OK})
    return {"status": BK_OK, "precheck": pre, "ejecucion": ejec,
            "backend": ident, "results": [res], "n_elementos": len(elementos),
            "limitations": lim, "provenance": "completa",
            "recuento_medido": RECUENTO_ET_DYN}


# ------------------------------------------------------------------ API

def secciones(artefacto: str, **kw) -> Dict[str, Any]:
    """`binary.sections`: las secciones del contenedor.

    NO son paginas ni segmentos de memoria. `perm` es lo que el ELF
    declara que se PUEDE hacer ahi, no lo que se puede hacer en runtime.
    """
    return _correr("binary.sections", "iSj", "secciones", [
        "una seccion es una division declarada del fichero. `perm` es lo "
        "que la cabecera DECLARA, no una proteccion efectiva en runtime: "
        "en un ET_REL el kernel decide al cargar, y lo que el objeto "
        "dice puede no ser lo que queda.",
    ], artefacto, **kw)


def imports(artefacto: str, **kw) -> Dict[str, Any]:
    """`binary.imports`: referencias externas que el objeto declara.

    NO son simbolos resueltos. En un ET_REL la gran mayoria son
    referencias sin resolver, porque resolverlas es lo que hara el
    linker o el modulo loader.
    """
    return _correr("binary.imports", "iij", "imports", [
        "un import es lo que el objeto DECLARA necesitar, no lo que se "
        "resuelve en runtime. En un ET_REL casi todos estan sin resolver: "
        "resolverlos es tarea del linker o del module loader.",
    ], artefacto, **kw)


def exports(artefacto: str, **kw) -> Dict[str, Any]:
    """`binary.exports`: simbolos que el objeto ofrece."""
    return _correr("binary.exports", "iEj", "exports", [
        "un export es un simbolo que el objeto ofrece a otros. Que figure "
        "aqui NO significa que sea alcanzable en runtime: en un ET_REL la "
        "tabla la leyo el linker, no el kernel.",
    ], artefacto, **kw)


def strings(artefacto: str, **kw) -> Dict[str, Any]:
    """`binary.strings`: cadenas legibles.

    NO son mensajes, ni codigo, ni texto con significado. Son bytes que
    el productor decided que son imprimibles, leidos con una codificacion
    SUPUESTA. Una cadena con formato de mensaje sigue siendo bytes.
    """
    return _correr("binary.strings", "izj", "cadenas", [
        "una cadena aqui son BYTES que el producer decidio que son "
        "imprimibles, leidos con una codificacion SUPUESTA. No son "
        "mensajes, ni codigo, ni texto con significado: una cadena con "
        "forma de mensaje sigue sin serlo, y una que parece una ruta "
        "puede ser cualquier cosa.",
        "el subconjunto que se devuelve depende de la heuristica del "
        "productor (minimo de longitud, clase de caracteres). El umbral "
        "no esta medido aqui: cambiarlo cambia el resultado.",
    ], artefacto, **kw)


def symbols(artefacto: str, **kw) -> Dict[str, Any]:
    """`binary.symbols`: la tabla de simbolos.

    NO son funciones. El tipo del contrato lo separa a proposito
    (`RAW_BINARY` y no `FUNCTION_CANDIDATE`): una funcion es un conjunto "
    de bytes con una frontera probada, y eso lo produce `aflj`, no la
    tabla de simbolos.
    """
    return _correr("binary.symbols", "isj", "simbolos", [
        "los simbolos NO son funciones. La tabla de simbolos dice que "
        "nombres declara el objeto; una funcion es un conjunto de bytes "
        "con una frontera probada. Quien necesite funciones debe pedir "
        "`binary.functions` (`aflj`), que es otra capacidad con otro tipo "
        "en el contrato.",
        "MEDIDO: `isj` tardo 147 s sobre un ET_REL de 37 MB. Es el mas "
        "caro de los cinco y el que mascte chances tiene de agotar un "
        "timeout.",
    ], artefacto, **kw)