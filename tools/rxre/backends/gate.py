#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-AUTO-001. El gate de los ocho principios, DENTRO del dispatch.

POR QUE ESTO EXISTE Y NO ES UN SEGUNDO `audit`.

`ocho_principios.py` (RXRE-ECO-001) audita UNA operacion a posteriori: se le
pasa un envelope ya capturado y devuelve `operacion_cerrada`. Eso es correcto y
sigue siendo correcto. Lo que no hacia era IMPEDIR que un envelope `ok` sin
trazabilidad llegara a la base de datos.

Y lo impedia de verdad. MEDIDO 2026-10-15: `test_eco_ast001` persedia a mano
poniendo `env["persistido"] = True`, porque sin el gate no habia quien lo
pusiera. Un test que fabrica su propia precondicion no prueba el
comportamiento de produccion: prueba el test.

Este modulo invierte eso. `evaluar()` se llama ANTES de `_persistir()`, y si
la operacion no pasa, no se persiste: se devuelve el envelope con el
diagnostico. La diferencia entre `audit` y esto:

    audit      responde "¿estuvo bien esto que ya guardé?"
    gate       responde "¿esto puede guardarse?"

## POR QUE ES UNA PUERTA Y NO UNA ADVERTENCIA

Porque una advertencia es un mensaje que nadie lee en el momento de ejecutar.
Una puerta es un `return` antes del `INSERT`. Y porque el fallo caro de RXRE
es un resultado `ok` que nadie puede repetir: se cont6a como trabajo hecho y
nunca se vuelve a mirar.

## LA ASIMETRIA, Y POR QUE IMPORTA

`gate` NO perdona por omision. Si un principio no tiene evidencia de cumplirse,
su veredicto es `not_proven`, y `not_proven` NO cierra la operacion.

Eso significa que una capacidad nueva que no declare sus limitaciones NO se
persiste, aunque su producer responda `ok`. Suena duro. Es lo correcto: o
declara lo que no puede hacer, o su resultado no es atribuible.

PERO hay una excepcion, y existe por una razon concreta: los envelopes que no
son `ok` (blocked, invalid_input, error, unsupported) NO se auditan. Un
`blocked` con su motivo es una RESPUESTA CORRECTA del sistema, y bloquearla
por no tener resultados seria absurdo: convertiria el fallo honesto en un
fallo silencioso.

## LO QUE ESTO NO ES

* NO es una puntuacion. No promedia, no da 7/8, no ordena capacidades.
* NO es un sustituto de `audit`. Este evita el almacenamiento; `audit` juzga
  lo ya almacenado. Son preguntas distintas.
* NO juzga correccion. `operacion_cerrada: true` significa "se cumplen las ocho
  condiciones que RXRE se exige", no "el resultado es cierto". Lo segundo
  necesita un discriminante contra el hardware.
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from adapters.ocho_principios import gate as _ocho_gate   # noqa: E402

#: Estados en los que NO se persiste. No son fallos del gate: son respuestas
#: honestas del producer, y auditar una respuesta honesta no tiene sentido.
ESTADOS_SIN_AUDITAR = frozenset((
    "blocked", "invalid_input", "error", "unsupported", "empty",
))

#: Interruptor del gate. NO lo consulta `evaluar()` (que es auditoria pura),
#: lo consulta `cerrar_o_abrir()` en su llamador: apagar el gate deja de
#: PERSISTIR, no cambia lo que la auditoria DICE.
#:
#: Existe para poder MEDIR cuantos envelopes pasarian sin el. No es un
#: interruptor de produccion, y `test_eco_gate004` comprueba que seguir
#: declarado como literal en el fuente: si desaparece, el diff lo delata.
ACTIVO = True


def evaluar(env: Dict[str, Any]) -> Dict[str, Any]:
    """Audita `env` y devuelve el veredicto. NUNCA lanza.

    Envuelve `_ocho_gate` porque el gate no puede ser el motivo por el que una
    operacion valida se caiga. Si los ocho principes no se pueden evaluar, el
    veredicto es `violation` con la causa: no `ok`, y no excepcion.
    """
    estado = (env or {}).get("status")

    if estado in ESTADOS_SIN_AUDITAR:
        return {
            "evaluable": False,
            "motivo": "estado %r: no es una afirmacion que haya que auditar"
                       % estado,
            "operacion_cerrada": True,     # no se audita, no se bloquea
            "nota": None,
        }

    # MEDIDO 2026-10-15. Este es el segundo intento de conectar el gate, y el
    # que funciona.
    #
    # El problema NO era el orden de las lineas en `dispatch.py`, sino que el
    # gate audita un estado en el que la persistencia es el PROXIMO PASO, no
    # un hecho. Poner `persiste_pretendido` despues de que el gate apruebe
    # (intento anterior) es un deadlock: si no aprueba, la linea no se ejecuta
    # nunca, y `persiste_pretendido` se queda en None para siempre.
    #
    # Aqui se declara ANTES, y solo como intencion. AGUA la acepta como tal
    # y lo dice en su porque. El HECHO lo verifica `ejecutar()` con el
    # `operation_id` que devuelve la base de datos.
    #
    # Solo si la operacion tiene resultados que hacer persistir. Un envelope
    # `ok` sin resultados no se "va a persistir": no hay nada que guardar, y
    # declararlo seria una intencion de guardar el vacio.
    if env.get("persiste_pretendido") is None and (env.get("results") or []):
        env["persiste_pretendido"] = True

    try:
        v = _ocho_gate(env)
    except Exception as e:                  # noqa: BLE001
        return {
            "evaluable": False,
            "motivo": "los ocho principios no se pudieron evaluar: %s: %s"
                      % (type(e).__name__, e),
            # Fallo de auditoria NO es aprobacion. Es lo contrario.
            "operacion_cerrada": False,
            "nota": None,
        }

    return {
        "evaluable": True,
        "motivo": "",
        "operacion_cerrada": bool(v.get("operacion_cerrada")),
        "razon": v.get("razon", ""),
        "nota": v.get("nota"),
    }


def cerrar_o_abrir(env: Dict[str, Any]) -> bool:
    """La decision, sin adornos. `True` = se persiste.

    Se separa de `evaluar` para que el dispatch tenga UNA llamada que leer y
    para que un test pueda afirmar sobre la decision sin parsear un dict.
    """
    # MEDIDO 2026-10-15: el mutante `return True` en esta funcion paso
    # 23/23 porque el dispatch no la llamaba. Ahora si la llama, asi que el
    # mutante aqui es detectable: por eso la decision va en UNA linea que no
    # se puede esquivar, y por eso `evaluar` NO mira `ACTIVO`.
    #
    # `evaluar` es la auditoria pura: no sabe si el gate esta encendido. Si
    # lo comprobara, apagar el gate cambiaria la AUDITIA, y eso es otra cosa
    # que un flag de potencia no deberia poder hacer.
    return bool(evaluar(env).get("operacion_cerrada"))


def razones_de_bloqueo(env: Dict[str, Any]) -> List[str]:
    """Por que NO se persiste, en texto. Para el envelope que se devuelve.

    Sin esto, un `blocked` por el gate sería indistinguible de un `blocked` del
    producer, y quien lo lee tendría que adivinar. §35: clasificar el fallo es
    parte del fallo.
    """
    v = evaluar(env)
    if v.get("operacion_cerrada"):
        return []
    if not v.get("evaluable"):
        return [v.get("motivo", "no se pudo evaluar")]
    nota = v.get("nota") or {}
    out = []
    for nombre in nota.get("en_violacion", []):
        d = (nota.get("detalle") or {}).get(nombre) or {}
        out.append("%s en violacion: %s" % (nombre, d.get("porque", "")))
    for nombre in nota.get("sin_probar", []):
        d = (nota.get("detalle") or {}).get(nombre) or {}
        out.append("%s sin prueba: %s" % (nombre, d.get("porque", "")))
    return out


def evaluar_envoltura(env: Dict[str, Any]) -> Dict[str, Any]:
    """Alias legible. `envoltura` es la palabra que usa el codigo para
    `env`: el sobre que devuelve una operacion de RXRE.

    Se mantiene separada de `evaluar` con el mismo criterio que
    `cerrar_o_abrir`: un nombre por responsabilidad, para que un test pueda
    usar el que corresponde en vez de recordar cual era.
    """
    return evaluar(env)