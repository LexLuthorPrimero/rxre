# SPDX-License-Identifier: GPL-2.0
"""`binary.lift` sobre RXRE-Lifter (en proceso). RXRE-M1110-001 / M11.10.

## POR QUE UN PRODUCER DE MODULO Y NO UN SUBPROCESO

El lifter de RXRE es una libreria en el arbol, no una herramienta externa.
Llamarla por API es el objetivo: un productor que existe en el arbol y que no
se ejecuta desde la linea de comandos requiere que el mismo adapter que
consume el resultado consuma la libreria. Es el mismo criterio que
`cs_disasm`/capstone: se importa y se usa dentro del proceso del adapter.

## LO QUE ESTA CAPACIDAD ES Y LO QUE NO

MEDIDO, esta capacidad devuelve una **reconstrucción C con un certificado
de trazabilidad** que nunca declara equivalencia demostrada fuera del
dominio medido. No es semantica
validada ni equivalencia general:

  type        decompilation
  status      partial
  certificate equivalence_claim = "NOT_PROVEN (PARTIAL acotado)"
  consumption = 1.0 solo si cada nodo recibido es consumido por la reconstruccion;
                0 en otro caso (rechazo conservador explicito)
  traceability 1.0 cuando cada nodo queda clasificado contablemente
                (known/unknown/malformed); no aumenta C

Un lifter que NO sabe levantar una funcion respondera `unsupported`, nunca
`empty` ni `ok` con fragmentos plausivles. El dominio admitido esta limitado
a lo medido y auditado en M11.2..M11.8; fuera de el, el adapter RECHAZA
(cltd / jp / jnp / vmovntpd / fxsave...). `unsupported` lleva el mnemonico
responsable, que es lo que la capability tiene que ser capaz de decir.

## NO ES UN SUSTITUTO DE binary.decompile

Ghidra decompila cualquier ET_REL x86-64 con `RecreateFlow` y retorna C con
tipos. Esta capacidad NO reemplaza nada: ofrece un producer propio, de
capa estrecha, medido, limitado y trazable — con refusal explicito fuera
de dominio. Aqui el dominio se declara byte a byte.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from typing import Any, Dict, Optional

__version__ = "1.0.0"

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, "..", ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from backends.contract import (  # noqa: E402
    BK_BLOCKED, BK_EMPTY, BK_ERROR, BK_INVALID, BK_OK, BK_UNSUPPORTED,
    DECOMPILATION, sha256_de, estado_firma,
)
from . import provenance as _prov  # noqa: E402

#: Huella medida del lifter RXRE — sirve como identificador de la versión
#: del producer, análogo funcional a `__version__` del módulo capstone.
#: Si este hash cambia, el consumer sabe qué producer está en juego.
def _lifter_sha256() -> str:
    import hashlib as _hl
    p = os.path.join(PKG, "decompiler", "lifter.py")
    try:
        return _hl.sha256(open(p, "rb").read()).hexdigest()
    except OSError:
        return ""

LIFTER_SHA256 = _lifter_sha256()

#: Estado de disponibilidad y medición del producer en este host.
def disponible() -> Dict[str, Any]:
    try:
        from decompiler import lift_objdump, generate_c, certificate  # noqa: F401
        mod = True
    except Exception as exc:
        mod = False
        return {"existe": False, "lifter_sha256": LIFTER_SHA256,
                "motivo": "decompiler.lifter no importable: %s" % exc}
    return {"existe": True, "lifter_sha256": LIFTER_SHA256,
            "lifter_path": os.path.join(PKG, "decompiler", "lifter.py")}


def _fn_section(full: str, funcion: str) -> Optional[str]:
    """Corta la sección de una sola función en la salida de objdump -d.

    Devuelve None si no existe. El formato de salida de objdump es
    estable en este binario (binutils 2.46.1): la sección empieza en
    la cabecera `<funcion>:` y termina en la siguiente cabecera.
    """
    m = re.search(r"(?m)^[0-9a-fA-F]+ <%s>:$" % re.escape(funcion), full)
    if not m:
        return None
    start = m.start()
    nxt = re.search(r"(?m)^[0-9a-fA-F]+ <", full[m.end():])
    end = m.end() + nxt.start() if nxt else len(full)
    sec = full[start:end]
    i = sec.find("Desensamblado") if "Desensamblado" in sec else len(sec)
    return sec[:i]


def _list_functions(full: str) -> list:
    """Lista las secciones presentes en `objdump -d` (nombres de función)."""
    return [m.group(1) for m in re.finditer(
        r"(?m)^[0-9a-fA-F]+ <([^>]+)>:$", full)]


def lift(artefacto: str, funcion: str = "", backend_id: str = "rxre-lifter",
         timeout: int = 0, **_ignored) -> Dict[str, Any]:
    """Levanta (lifts) una función ELF a C con certificado de trazabilidad.

    `backend_id` lo inyecta el dispatch por defecto del catálogo. Se ACEPTA
    y se COMPRUEBA: si se pide `backend_id="ghidra"`, la respuesta dice que
    este adapter no puede servirla y no devuelve un resultado de RXRE
    etiquetado como si fuera de otro producer — el mismo criterio que
    `cs_disasm`.
    """
    if backend_id != "rxre-lifter":
        return {"status": BK_INVALID,
                "limitations": [
                    "backend %r no puede servir esta capacidad: su único "
                    "producer es `rxre-lifter` (módulo en proceso)." % backend_id,
                    "backend_por_defecto es 'rxre-lifter'; pedir otro devolveria "
                    "un resultado de RXRE etiquetado equivocado."],
                "precheck": {"ok": False}}
    if not disponible()["existe"]:
        return {"status": BK_BLOCKED,
                "limitations": ["decompiler.lifter no importable: ver disponible()"],
                "precheck": {"ok": False}}

    if not os.path.isfile(artefacto):
        return {"status": BK_INVALID,
                "precheck": {"ok": False, "input_existe": False},
                "limitations": ["la entrada no existe: %s" % artefacto]}
    firma = estado_firma(artefacto)
    if firma == "no_legible":
        return {"status": BK_INVALID,
                "precheck": {"ok": False, "input_es_elf": None},
                "limitations": [
                    "la entrada existe pero no es legible (permiso o E/S)",
                    "la firma ELF no se pudo leer; no se sabe si el fichero es ELF",
                    "no se levantó: no se ejecutó ningún análisis"]}
    if firma != "elf":
        return {"status": BK_INVALID,
                "precheck": {"ok": False, "input_es_elf": False},
                "limitations": [
                    "la entrada no es un ELF: %s" % artefacto,
                    "no se levantó: no hay instrucciones decodificables que analizar"]}
    pre = {"input_existe": True, "input_es_elf": True,
           "input_hash": sha256_de(artefacto),
           "backend_id": "rxre-lifter",
           "lifter_sha256": LIFTER_SHA256,
           "backend": "rxre-lifter",
           "command_or_api": "rxre lifter (en proceso, sin subproceso)",
           "ok": False}

    try:
        full = subprocess.check_output(
            ["objdump", "-d", artefacto], text=True,
            timeout=timeout if timeout and timeout > 0 else None)
    except FileNotFoundError:
        return {"status": BK_BLOCKED, "precheck": pre,
                "limitations": ["objdump no está disponible en el sistema"]}
    except subprocess.CalledProcessError as exc:
        return {"status": BK_BLOCKED, "precheck": pre,
                "limitations": ["objdump -d falló: %s" % exc]}
    except subprocess.TimeoutExpired:
        return {"status": BK_BLOCKED, "precheck": pre,
                "limitations": ["objdump -d agotó el timeout"]}

    funciones = _list_functions(full)
    if funcion:
        sec = _fn_section(full, funcion)
        if sec is None:
            return {"status": BK_UNSUPPORTED, "precheck": pre,
                    "funciones_detectadas": funciones[:50],
                    "limitations": [
                        "la función %r no aparece como sección en objdump -d de %s" % (funcion, artefacto),
                        "funciones detectadas: %s" % (", ".join(funciones[:20]) or "(ninguna)"),
                        "no se levantó nada: no existe evidencia de instrucciones para esta función"]}
        objetivo = funcion
    else:
        if not funciones:
            return {"status": BK_EMPTY, "precheck": pre,
                    "limitations": ["objdump -d no identificó ninguna función en %s" % artefacto]}
        objetivo = funciones[0]
        sec = _fn_section(full, objetivo)

    from decompiler import lift_objdump, generate_c, certificate
    t0 = time.time()
    try:
        nodes = lift_objdump(sec, objetivo)
        out = generate_c(objetivo, nodes)
        cert = certificate(objetivo, [], nodes)
    except Exception as exc:
        return {"status": BK_ERROR, "precheck": pre,
                "limitations": ["error interno del lifter: %s: %s" % (type(exc).__name__, exc)]}
    dur = round(time.time() - t0, 6)
    pre["ok"] = True

    if out.startswith("/*"):
        # Rechazo conservador: la instrucción responsable viaja en el cuerpo.
        return {"status": BK_UNSUPPORTED,
                "precheck": pre,
                "ejecucion": {"operation": "binary.lift", "backend_id": "rxre-lifter",
                              "command_or_api": "rxre lifter (en proceso)",
                              "argv": [], "exit_status": 4, "duration_s": dur,
                              "timeout": False, "stderr": "",
                              "nota": "producer EN PROCESO: argv va vacio por diseño"},
                "results": [],
                "problemas": [out],
                "funciones_detectadas": funciones[:50],
                "certificate": cert,
                "limitations": [
                    "el lifter NO reconstruyó esta función; la salida es un marcador PARTIAL explícito",
                    "instrucciones responsables listadas en `problemas`",
                    "esto NO es un fallo del lifter: es la respuesta correcta fuera de dominio",
                    "equivalence_claim sigue NOT_PROVEN (PARTIAL acotado)",
                ],
                "provenance": _prov.desde_precheck(
                    pre,
                    transformacion='objdump -d -> lift_objdump -> generate_c (rechazada)',
                    normalizador='backends.adapters.rxre_lifter.lift')}

    lim = [
        "esto es una reconstrucción instrucción-dependiente, NO equivalencia semántica demostrada. "
        "equivalence_claim = NOT_PROVEN (PARTIAL acotado).",
        "traceability_coverage=1.0 no implica consumo; consumption_coverage == 1.0 sólo con todos los nodos emitidos.",
        "scope: x86-64, función concreta, dominio admitido y auditado en RXRE M11.2-M11.8 (opcodes admitidos únicamente).",
        "el dominio de equivalencia NO se extrapola: fuera de esta plantilla medida, no se afirma nada.",
        "el lifter rechaza (unsupported) las instrucciones no admitidas; nunca produce fragmentos sospechosos.",
        "certificate() separa traceability_coverage y consumption_coverage; ninguna declara PROVEN.",
        "el hash del lifter que produjo este resultado está en provenance.lifter_sha256.",
    ]
    lim.extend(cert.get("traceability", {}).get("limitations", []))

    res = {
        "result_id": "res_rxre_lift_" + __import__("hashlib").sha256(
            ("%s|%s|%s" % (artefacto, objetivo, out)).encode("utf-8")).hexdigest()[:12],
        "type": DECOMPILATION,
        "status": "partial",
        "value": {"funcion": objetivo,
                  "reconstruccion_c": out,
                  "certificado_rxre": cert},
        "source": artefacto,
        "location": {"file": os.path.basename(artefacto)},
        "scope": "binary", "tool": "rxre-lifter",
        "tool_version": LIFTER_SHA256[:16],
        "input": {"path": artefacto, "sha256": pre["input_hash"]},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "artifact": artefacto, "artifact_hash": pre["input_hash"],
        "limitations": lim, "duration_s": dur,
    }
    return {"status": BK_OK,
            "precheck": pre,
            "ejecucion": {"operation": "binary.lift",
                          "backend_id": "rxre-lifter",
                          "command_or_api": "rxre lifter (en proceso, sin subproceso)",
                          "argv": [], "exit_status": 0, "duration_s": dur,
                          "timeout": False, "stderr": "",
                          "nota": "producer EN PROCESO: por eso argv va vacio"},
            "results": [res],
            "n_reconstrucciones": 1,
            "certificate": cert,
            "limitations": lim,
            "provenance": _prov.desde_precheck(
                pre,
                transformacion='objdump -d -> lift_objdump() -> generate_c() + certificate()',
                normalizador='backends.adapters.rxre_lifter.lift'),
            "rxre_lifter_medido": disponible()}
