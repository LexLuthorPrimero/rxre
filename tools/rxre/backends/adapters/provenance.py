# SPDX-License-Identifier: GPL-2.0
"""RXRE-AUTO-002. El constructor UNICO de provenance estructurada.

POR QUE ESTE MODULO EXISTE.

MEDIDO 2026-10-15, gate sobre las 26 capacidades del dispatch:

    PASA                    4
    BLOQUEADA              11
    NO_CUBIERTA             8
    PRODUCTOR_*             3

Y las 11 bloqueadas dicen LO MISMO, con las mismas dos razones:

    TIERRA sin prueba: provenance como cadena sin estructura
    FUEGO   sin prueba: sin provenance estructurada

Una sola causa, once veces. Eso NO son once problemas: es un problema, once
veces. Un principio que se queja once por cada capacidad esta describiendo
un contrato que nadie cumple, no once fallos independientes.

## LA CAUSA, MEDIDA.

Dos formas de provenance conviven en el mismo repositorio:

    rz_xrefs, rz_callgraph, umr_read   -> dict  (PASA)
    cocci_search, cs_disasm,          -> str   (BLOQUEADA)
    gh_decompile, rz_cfg, ...

Y la forma string no es una forma distinta de la misma cosa. Es otra cosa:

    "provenance": "completa"

Una palabra. Declara que la trazabilidad esta completa mientras no lleva
ni el hash, ni el backend, ni la transformacion. No es una provenance
incompleta: es una AFIRMACION de completitud sin evidencia. TIERRA tiene
razon en rechazarla, y FUEGO tambien, y no porrigidez: por sustancia.

## Y AQUI ESTA LO QUE HACE FALTA DECIR.

El dato NO falta. MEDIDO en `cs_disasm.py`:

    linea 231:  pre["input_hash"] = sha256_de(ruta)
    linea 343:  "artifact_hash": pre["input_hash"]

El hash se calcula y se USA. Lo que no se hace es copiarlo a donde el
contrato lo pide. La evidencia esta archivada en `pre` y en el resultado;
el campo `provenance` recibe la palabra.

Asi que el fallo no es "los adapters no tienen provenance". Es "la
provenance esta en el sitio equivocado". Que es un fallo de FORMA, y el
formato se arregla con una funcion, no con ocho reescrituras.

## POR QUE NO SE RELAJA EL GATE.

Porque relajar seria el error caro y ya se pago una vez: convertir un
principio en lista de exenciones. Si `provenance: "completa"` se aceptara,
las once capacidades volverian a persistir y el nombre `completa`seguiria
mintiendo. El gate esta bien calibrado. Lo que estaba mal era el contrato
incumplido.

## POR QUE UN CONSTRUCTOR Y NO UN PARCHE POR ADAPTER.

Porque ocho copias del mismo dict es como se producen ocho formas
distintas, y las ocho se pudren. Una funcion que todos llaman se mantiene
sola, y cuando el contrato cambie hay un sitio.

Y porque el constructor DECLARA SU LIMITACION: `transformacion` es la
cadena que declara el adapter, no una descripcion que este modulo invente.
Un modulo comun no puede saber que hace cada adapter. Si se permitiera que
el modulo lo rellene por su cuenta, seria el modulo mintiendo en nombre de
quien no miente.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

#: Estado unico. No hay estados intermedios porque no hay evidencia
#: intermedia: o se sabe de donde salio el resultado, o no se sabe.
ESTADO_COMPLETA = "completa"
ESTADO_INCOMPLETA = "PROVENANCE_INCOMPLETE"


def construir(
    estado: str = ESTADO_COMPLETA,
    input_hash: Optional[str] = None,
    backend: str = "",
    command_or_api: str = "",
    transformacion: str = "",
    normalizador: str = "",
    tool_version: str = "",
    repository_commit: str = "",
    motivo_incompleta: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Construye la provenance en la forma que TIERRA y FUEGO exigen.

    `transformacion` y `normalizador` son OBLIGATORIOS y los pone quien
    llama. Este modulo no los rellena: un normalizador comun no puede
    saber que transformacion aplica cada adapter, y deducirlo seria
    inventar la evidencia que FUEGO existe para exigir.
    """
    if estado == ESTADO_INCOMPLETA or motivo_incompleta:
        return {
            "estado": ESTADO_INCOMPLETA,
            "motivo": motivo_incompleta or "declarada incompleta por el producer",
            "input_hash": input_hash or "",
            "transformacion": transformacion,
            "normalizador": normalizador,
        }
    return {
        "estado": ESTADO_COMPLETA,
        "input_hash": input_hash or "",
        "backend": backend,
        "command_or_api": command_or_api,
        "transformacion": transformacion,
        "normalizador": normalizador,
        "tool_version": tool_version,
        "repository_commit": repository_commit,
        "provenance_estado": ESTADO_COMPLETA,
        **({"extra": extra} if extra else {}),
    }


def desde_precheck(pre: Dict[str, Any], **kw: Any) -> Dict[str, Any]:
    """Atajo para el patron que ya usan 8 de 11 adapters.

    Esos adapters hacen `pre["input_hash"] = sha256_de(ruta)` y luego
    tiran ese `pre` fuera de `provenance`. Este atajo pone el dict donde
    el contrato lo pide, sin obligar a nadie a reescribir la funcion.

    `pre` es la evidencia. Este modulo la copia, no la mejora.
    """
    pre = pre or {}
    return construir(
        input_hash=pre.get("input_hash", "") or pre.get("sha256", ""),
        backend=pre.get("backend", "") or pre.get("backend_id", "")
        or pre.get("ident", "") or pre.get("caja", ""),
        command_or_api=pre.get("command_or_api", "") or pre.get("comando", ""),
        tool_version=pre.get("tool_version", "") or pre.get("version", ""),
        repository_commit=pre.get("repository_commit", ""),
        **kw,
    )