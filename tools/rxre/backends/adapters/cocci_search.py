# SPDX-License-Identifier: GPL-2.0
"""Adaptador de Coccinelle (`spatch`). RXRE-BULK-2026-10-12.

## QUE CAPACIDAD ABRE

`source.semantic_search`: buscar en codigo C un PATRON SEMANTICO, no una
cadena. Es la capacidad que hace falta para la clase de pregunta del
proyecto RX 550 mas molesta:

    "todos los sitios donde el driver escribe un registro sin pasarlo por
     el helper de escritura"

Un grep no responde a eso: el texto es distinto en cada sitio. Un patron
semantico si. Y no es una capacidad de binario: no hay ELF, no hay
descompilacion, no hay direcciones. Por eso su namespace es `source.` y no
`binary.`, y por eso no se cuela en el catalogo de backends de binario.

## LO QUE ESTA MEDIDO Y NO SE SUPOÑO

MEDIDO 2026-10-12, spatch 1.3.1 (OCaml 5.4.0), Fedora 44:

  * `--version` responde con flags de compilacion.
  * `spatch --sp-file p.cocci f.c` APLICA el patron y reescribe.
    MEDIDO sobre un patron de escritura por puntero:
        - `*p = E;`  ->  `XX_write_through_p(E);`
  * CONTROL NEGATIVO: el mismo patron sobre un fichero SIN esa linea no
    produce diff. Es decir, el `empty` del productor es discriminante y no
    un fallo silencioso.
  * `spatch --spool` NO EXISTE en 1.3.1 (`unknown option`). La forma
    correcta es `--sp-file`. Un patron mal invocado da rc=255 con
    "No rules apply", que NO es lo mismo que "no coincide": es un error
    de invocacion disfrazado de resultado.

Ese ultimo punto es el que obliga a la comprobacion de salida: este
adaptador mira si el parche produce diff antes de decir que no coincidio.

## LO QUE NO HACE

No es un descompilador, no encuentra funciones, no da grafo de llamadas.
Para un `.ko` YA COMPILADO no sirve: Coccinelle necesita FUENTES. La
corpus del kernel esta en el arbol de 06-INGENIERIA-INVERSA (finding
1556: un corpus es una sola rama y 134 cabeceras fuera).
"""
from __future__ import annotations

import os
import re
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
    SEMANTIC_HYPOTHESIS, Backend, sha256_de, sha256_texto,
)


def disponible() -> Dict[str, Any]:
    d = {"backend_id": "coccinelle", "exe": "spatch", "existe": False,
         "version": "", "version_verificada": False}
    path = shutil_which("spatch")
    if not path:
        return d
    d["path"] = path
    d["existe"] = True
    try:
        p = subprocess.run([path, "--version"], capture_output=True,
                           text=True, timeout=30)
        t = (p.stdout or "") + (p.stderr or "")
        for ln in t.splitlines():
            if ln.startswith("spatch version"):
                d["version"] = ln.strip()[:120]
                d["version_verificada"] = True
                break
    except (OSError, subprocess.TimeoutExpired):
        d["version_error"] = "la sonda de version no respondio"
    return d


def shutil_which(nombre: str) -> Optional[str]:
    for dd in os.environ.get("PATH", "").split(os.pathsep):
        c = os.path.join(dd, nombre)
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


#: rc que Coccinelle devuelve segun el modo de fallo. MEDIDO 2026-10-12:
#:
#:   `--spool` (flag que NO existe en 1.3.1)  -> rc 2   + "unknown option"
#:   parche sin lineas +/-/*                  -> rc 255 + "No rules apply"
#:   parche que no aplica, bien invocado      -> rc 0   + sin diff
#:   parche que aplica                        -> rc 0   + diff
#:
#: La primera version de este adaptador asumia 255 para los dos fallos
#: "mal invocado". MEDIDO: no es el mismo rc. Lo que SI comparten es que
#: ninguno es un resultado sobre el codigo, asi que ninguno puede
#: consumirse como `empty`. El texto, no el rc, es lo que discrimina.
RC_INVOCACION_INVALIDA = 2
RC_SIN_REGLAS = 255
RC_SIN_MATCH = 0
RE_NO_RULES = re.compile(r"No rules apply", re.I)
RE_OPCION_DESCONOCIDA = re.compile(r"unknown option|unrecognized option",
                                   re.I)


def _validar_patron(fichero_patron: str) -> Dict[str, Any]:
    if not os.path.isfile(fichero_patron):
        return {"ok": False,
                "motivo": "no existe el fichero de patron: %s"
                          % fichero_patron}
    try:
        with open(fichero_patron, encoding="utf-8",
                  errors="replace") as fh:
            txt = fh.read()
    except OSError as e:
        return {"ok": False, "motivo": str(e)}
    if not txt.strip():
        return {"ok": False, "motivo": "el fichero de patron esta vacio"}
    # MEDIDO: un patron sin ninguna linea +/- /* no es un patron de
    # emparejamiento: `spatch` responde "No rules apply". Se avisa ANTES de
    # gastar el proceso entero.
    tiene_regla = any(l.strip().startswith(p)
                      for l in txt.splitlines()
                      for p in ("+", "-", "*"))
    if not tiene_regla:
        return {"ok": False,
                "motivo": "el patron no tiene ninguna linea +/-/*: es un "
                          "patron de coincidencia literal, no semantico. "
                          "MEDIDO: `spatch` responde 'No rules apply' (rc 255) "
                          "con esos patrones"}
    return {"ok": True, "n_lineas": len(txt.splitlines()),
            "hash": sha256_de(fichero_patron)}


def buscar(artefacto: str, patron: str, backend_id: str = "coccinelle",
           timeout: int = 600, include_dirs: Optional[List[str]] = None,
           fixture_diff: str = "") -> Dict[str, Any]:
    """La operacion. SIEMPRE los seis canales."""
    ent = registry.get(backend_id)
    b: Backend = ent["backend"]
    disp = disponible()

    pre = {"input_existe": os.path.isfile(artefacto),
           "input_es_c": None,
           "patron_existe": os.path.isfile(patron),
           "patron_valido": False,
           "backend_existe": disp["existe"],
           "usa_fixture": bool(fixture_diff),
           "ok": False}
    if fixture_diff:
        pre["ok"] = True
        pre["input_existe"] = os.path.isfile(artefacto)
    else:
        if not pre["input_existe"]:
            return {"status": BK_INVALID, "precheck": pre,
                    "limitations": ["la entrada no existe: %s" % artefacto]}
        if not pre["patron_existe"]:
            return {"status": BK_INVALID, "precheck": pre,
                    "limitations": ["no existe el patron: %s" % patron]}
        v = _validar_patron(patron)
        pre["patron_valido"] = v.get("ok", False)
        if not v["ok"]:
            return {"status": BK_INVALID, "precheck": pre,
                    "limitations": [v["motivo"]]}
        if not pre["backend_existe"]:
            return {"status": BK_BLOCKED, "precheck": pre,
                    "limitations": ["spatch no esta en PATH"]}
        pre["input_es_c"] = True
        pre["input_hash"] = sha256_de(artefacto)
        pre["ok"] = True

    argv: List[str] = []
    rc: Optional[int] = None
    so = se = ""
    timedout = False
    dur = 0.0

    if fixture_diff:
        argv = ["<fixture>", fixture_diff]
        rc, so, se = 0, "", "modo fixture: producer simulado"
        salida = fixture_diff
    else:
        exe = disp["path"]
        argv = [exe, "--sp-file", patron, artefacto]
        for inc in (include_dirs or []):
            argv += ["-D", inc]
        t0 = time.time()
        try:
            p = subprocess.run(argv, capture_output=True, text=True,
                               timeout=timeout)
            rc, so, se = p.returncode, p.stdout or "", p.stderr or ""
        except subprocess.TimeoutExpired:
            rc, so, se, timedout = (None, "",
                                   "timeout a los %ds" % timeout, True)
        except OSError as exc:
            rc, so, se = None, "", str(exc)
        dur = round(time.time() - t0, 2)
        salida = so

    ejec = {
        "backend_id": "fixture" if fixture_diff else backend_id,
        "operation": "source.semantic_search",
        "command_or_api": "spatch --sp-file <patron.cocci> <fuente.c>",
        "argv": argv,
        "exit_status": rc,
        "stderr": se.strip()[:400],
        "timeout": timedout,
        "duration_s": dur,
    }
    ident = b.identidad()
    ident["coccinelle"] = disp

    if timedout:
        ejec.update({"status": BK_BLOCKED,
                     "limitations": ["timeout a los %ds" % timeout]})
        return {"status": BK_BLOCKED, "precheck": pre, "ejecucion": ejec,
                "backend": ident,
                "provenance": "PROVENANCE_INCOMPLETE: no hay salida"}

    # --- LA DISTINCION IMPORTANTE ----------------------------------------
    # MEDIDO 2026-10-12: hay DOS fallos que NO son un resultado sobre el
    # codigo, y se distinguen por TEXTO, no por rc:
    #
    #   "unknown option"  -> flag inexistente en esta version (rc 2)
    #   "No rules apply"  -> patron sin regla utilizable (rc 255)
    #
    # El segundo es el que casi se cuela como resultado: `spatch` responde
    # "No rules apply" cuando el parche no aplica Y cuando esta mal
    # construido. Sin mirar el texto, un parche roto se lee como "este
    # patron no coincide en este fichero", que es una afirmacion sobre el
    # driver y es FALSA: no se llego a examinar el codigo.
    if RE_OPCION_DESCONOCIDA.search(se or "") \
            or RE_OPCION_DESCONOCIDA.search(so or ""):
        ejec.update({"status": BK_INVALID,
                     "limitations": [
                         "`unknown option`: el flag no existe en esta "
                         "version. MEDIDO: spatch 1.3.1 no tiene `--spool`; "
                         "la forma correcta es `--sp-file <patron> <fuente>`.",
                         "rc=%s, stderr: %s"
                         % (rc, (se.strip() or so.strip())[:200])]})
        return {"status": BK_INVALID, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "results": [],
                "provenance": "PROVENANCE_INCOMPLETO: invocacion invalida"}

    if RE_NO_RULES.search(se or "") or RE_NO_RULES.search(so or ""):
        ejec.update({"status": BK_INVALID,
                     "limitations": [
                         "`No rules apply`: MEDIDO, spatch 1.3.1 emite esto "
                         "tanto si el parche no aplica como si esta mal "
                         "construido. Se clasifica invalid_input, NO empty: no "
                         "es que no coincida, es que el parche no es usable "
                         "sobre esta entrada.",
                         "stderr: %s" % (se.strip() or so.strip())[:300]]})
        return {"status": BK_INVALID, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "results": [],
                "provenance": "PROVENANCE_INCOMPLETO: parche no usable"}

    if rc not in (0, None) and rc != RC_SIN_MATCH:
        ejec.update({"status": BK_ERROR,
                     "limitations": ["spatch salio con rc=%s: %s"
                                     % (rc, (se.strip() or so.strip())[:300])]})
        return {"status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
                "backend": ident,
                "provenance": "PROVENANCE_INCOMPLETO: backend fallo"}

    # --- ¿HAY COINCIDENCIA? ---------------------------------------------
    # El productor de Coccinelle para un `+` es un DIFF. Sin diff, no
    # hubo coincidencia. Un rc 0 con salida vacia es `empty` DE VERDAD:
    # el control negativo MEDIDO lo confirma.
    lineas_diff: List[str] = []
    actual = None
    for ln in (salida or "").splitlines():
        if ln.startswith("+++") or ln.startswith("---"):
            actual = {"fichero": ln.split("\t")[-1].strip(),
                      "hunks": []}
            lineas_diff.append(ln)
            continue
        if ln.startswith("@@"):
            if actual is not None:
                actual["hunks"].append(ln)
            lineas_diff.append(ln)
            continue
        if ln[:1] in ("+", "-") and not ln.startswith(("+++", "---")):
            lineas_diff.append(ln)
            if actual is not None and ln.startswith("+"):
                actual["hunks"].append(ln)
    n_hits = len([x for x in lineas_diff if x.startswith("+")
                  and not x.startswith("+++")])
    n_lineas_original = len(lineas_diff)

    lim = [
        "una coincidencia de Coccinelle es una SEMANTIC_HYPOTHESIS sobre el "
        "TEXTO fuente: no es una verdad sobre el binario compilado ni sobre "
        "el hardware. El parche puede ser incorrecto.",
        "Coccinelle necesita FUENTES. No sirve sobre un `.ko` ya compilado.",
        "el texto es el de este corpus; si el corpus es una sola rama de las "
        "que hay (hallazgo 1556), los hallazgos no cubren el arbol entero.",
    ]

    if n_hits == 0:
        ejec.update({"status": BK_EMPTY,
                     "limitations": lim + [
                         "0 coincidencias. Con el patron validado y la "
                         "invocacion correcta, esto es `empty` de verdad "
                         "(MEDIDO: el control negativo da el mismo rc sin "
                         "diff)."]})
        return {"status": BK_EMPTY, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "results": [], "n_hits": 0,
                "raw_output": salida[:4000], "provenance": "completa"}

    artefacto_ref = artefacto
    rid = "res_semsrc_" + sha256_texto(
        "%s|%s|%s" % (artefacto_ref, patron, salida))[:12]
    valor = {"n_coincidencias": n_hits,
             "diff": lineas_diff[:200],
             "patron": patron,
             "ficheros": sorted(set(_ficheros_de(lineas_diff)))}
    completitud = {
        "completo": n_lineas_original <= 200,
        "omitidos": max(0, n_lineas_original - 200),
        "limite": 200,
        "elemento": "lineas_diff",
    }
    res = {
        "result_id": rid,
        "type": SEMANTIC_HYPOTHESIS,
        "value": valor,
        "source": artefacto_ref,
        "location": {"file": os.path.basename(artefacto_ref)},
        "scope": "fuente",
        "tool": "coccinelle",
        "tool_version": disp.get("version", ""),
        "input": {"path": artefacto_ref,
                  "sha256": pre.get("input_hash", "")},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "artifact": artefacto_ref,
        "artifact_hash": pre.get("input_hash", ""),
        "status": "declared",
        "limitations": lim,
        "completitud": completitud,
    }
    ejec.update({"status": BK_OK})
    return {"status": BK_OK, "precheck": pre, "ejecucion": ejec,
            "backend": ident, "results": [res], "n_hits": n_hits,
            "raw_output": salida[:4000], "limitations": lim,
            "provenance": "completa"}


def _ficheros_de(lineas: List[str]) -> List[str]:
    """Nombres de fichero de un diff unificado.

    MEDIDO (2026-10-12): la primera version devolvia la lista de lineas
    `+++` y el llamante hacia `a["fichero"]` sobre cada una, lo que
    reventaba con `TypeError: string indices must be integers`. El fallo
    salio al ejecutar el productor real, no al leer el codigo: un
    separador de linea de diff NO es un dict.

    Se separa la linea de su cabecera, que es donde vive el nombre.
    """
    out: List[str] = []
    for ln in lineas:
        if ln.startswith("+++"):
            out.append(ln[4:].split("\t")[-1].strip())
    return out