#!/usr/bin/env python3
"""RXRE-004. El dispatch: que se puede ejecutar, contra quien, y como se prueba.

POR QUE HAY UNA CAPA DE DISPATCH Y NO UNA LLAMADA DIRECTA AL ADAPTER.

Una IA no debe poder decir "ejecuta esto". Si `op: run`tomase un comando, un
nombre de fichero o una cadena arbitraria, habria que decidir si es una
peticion o un ataque, y esa decision se tomaria con una expresion regular.

Aqui la unicadecision NO es "este texto es valido". Es:

    ¿esta capacidad EXISTE en el registry?

Que es la misma forma que tuvo F3. `target_permitido` no era una lista negra de
targets peligrosos; era "permite explicitamente solo estos targets". La
allow-list de capacidades es el mismo patron aplicado a otro sitio: no
"sabemos que capacidades son peligrosas", sino "solo se puede pedir una
capacidad que el registry declara, y solo si tiene ficha, contrato, adapter y
producer".

## LA REGLA QUE MAS IMPORTA Y QUE MAS SE CONFUNDE

    ejecutable  !=  va a funcionar

`binary.cfg` en rizin 0.7.4 es `PARTIAL`: existe un producer, pero emite ASCII
visual y no JSON. Se PUEDE pedir -- asi que es ejecutable -- y su limitacion
viaja con el. Ocultar una capacidad `PARTIAL` seria mentir: la capacidad
existe. Declararla `AVAILABLE` seria mentir tambien: no cumple el contrato.

Y al reves: `NOT_DETERMINED` NO es ejecutable. No se comprobo que falte; se
comprobo que no se puede verificar. Un backend no verificable no puede entrar
en la allow-list, porque su resultado no tendria provenance creible.

## POR QUE EL REGISTRY ES LA AUTORIDAD

Si la allow-list viviera aqui, en `dispatch.py`, habria dos listas: la de aqui
y la del registry, y divergirian. La unica lista es la del registry, y este
modulo PREGUNTA. La mutacion que cambia el registro se propaga sola; la que
cambia una lista copiada no.
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
# MEDIDO: la raiz de PAQUETE, no el directorio de este fichero. Con
# `backends/` en el path, `from core import store` buscaria `backends/core/`.
PKG = os.path.abspath(os.path.join(HERE, "..", ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from backends import registry  # noqa: E402
from backends.adapters import rz_inspect  # noqa: E402
from backends.contract import BACKEND_RC  # noqa: E402

#: Los unicos adapters que existen. Una capacidad sin entrada aqui NO se
#: ejecuta, por mucho que el registry la declare AVAILABLE: eso seria una
#: capacidad declarada sin producer, que es exactamente lo que §5 prohibe.
#:
#: MEDIDO: hoy hay UNA capacidad con producer. Registrarla aqui no es
#: infraestructura por adelantado: es la lista de lo que existe, y growea
#: cuando growe.
ADAPTERS = {
    "binary.inspect": {
        "modulo": "backends.adapters.rz_inspect",
        "funcion": "inspect",
        "backend_por_defecto": "rizin",
        "parametros": ["artefacto", "backend_id", "timeout"],
        "obligatorio": ["artefacto"],
    },
}

#: Estados que permiten EJECUTAR. `PARTIAL` entra con su limitacion; los otros
#: dos no entran.
EJECUTABLES = ("AVAILABLE", "PARTIAL")

#: Los PLANES. Que capacidades componen el camino hacia un objetivo.
#:
#: ESTA lista es una DECISION DE DISENO, no una medicion, y por eso vive aqui y
#: no en el registry: el registry dice que capacidades EXISTEN, no en que orden
#: conviene recorrerlas para responder una pregunta.
#:
#: Y por eso `plan()` NO deduce los pasos de estos nombres: deduce el ESTADO de
#: cada paso del registry. Si una capacidad de un plan desaparece del registry,
#: el paso sigue en el plan y aparece como no ejecutable con su motivo, en vez
#: de desaparecer -- que seria un plan que se acorta solo para parecer viable.
PLANES: Dict[str, List[str]] = {
    "binary.inspect": ["binary.inspect"],
    "binary.functions": ["binary.inspect", "binary.functions"],
    "binary.disassemble": ["binary.inspect", "binary.disassemble"],
    "binary.xrefs": ["binary.inspect", "binary.functions", "binary.xrefs"],
    "binary.cfg": ["binary.inspect", "binary.functions", "binary.cfg"],
    "binary.dataflow": ["binary.inspect", "binary.functions", "binary.dataflow"],
    "binary.decompile": ["binary.inspect", "binary.functions",
                         "binary.disassemble", "binary.cfg", "binary.dataflow",
                         "binary.decompile"],
}


def planificar(capability: str, question: str = "") -> Dict[str, Any]:
    """El plan SIN ejecutar. §13 / B6.

    Cada paso declara tres cosas y son distintas:

        verifiable  el registry AFIRMA que existe producer para ese paso
        available   se puede pedir AHORA (verifiable + adapter + no-huerfano)
        reason      por que, cuando no

    Y `verifiable` NO significa que la ejecucion tendra exito. Significa
    unicamente que hay un producer declarado. Confundir las dos cosas es
    exactamente lo que haria que un plan pareciera una promesa.

    Un plan que solo contuviera pasos ejecutables seria mas vistoso y menos
    util: la IA tiene que ver `binary.decompile` como un callejon ANTES de
    recorrer los otros cinco pasos.
    """
    fichas = _todas_las_fichas()
    pasos_cap = PLANES.get(capability)
    if pasos_cap is None:
        # No hay plan para esto. Se dice, con lo que SI hay, en vez de
        # inventar un camino de una sola capacidad.
        return {
            "question": question, "capability": capability,
            "execution": "not_started",
            "plan": [],
            "status": "no_plan",
            "motivo": "no hay un plan definido para '%s'. Las capacidades con "
                      "plan son: %s. Que una capacidad no tenga plan NO es que "
                      "no se pueda hacer: es que nadie ha definido el camino."
                      % (capability, ", ".join(sorted(PLANES)) or "(ninguno)"),
            "capacidades_del_registry": sorted(fichas),
            "advertencia": ADVERTENCIA_PLAN,
        }
    pasos: List[Dict[str, Any]] = []
    for i, cap in enumerate(pasos_cap, 1):
        p = esta_permitida(cap)
        e = fichas.get(cap)
        pasos.append({
            "orden": i,
            "operation": cap,
            "capability": cap,
            "verifiable": bool(e),
            "available": bool(p["permitida"]),
            "estado_registro": (e or {}).get("estado_agregado", "AUSENTE"),
            "backends": (e or {}).get("backends", []),
            "limitaciones": (e or {}).get("limitaciones", []),
            "reason": p["motivo"] or "",
            "nota": ("este paso no se puede pedir todavia" if not p["permitida"]
                     else "ejecutable"),
        })
    ejecutables = sum(1 for x in pasos if x["available"])
    return {
        "question": question,
        "capability": capability,
        "execution": "not_started",
        "plan": pasos,
        "status": "ok",
        "resumen": {
            "pasos": len(pasos),
            "verificables": sum(1 for x in pasos if x["verifiable"]),
            "ejecutables": ejecutables,
            "bloqueos": [{"operation": x["operation"], "reason": x["reason"]}
                         for x in pasos if not x["available"]],
        },
        "nota": "este plan NO se ha ejecutado. `execution` vale literalmente "
                "'not_started' y ningun backend se ha invocado al construirlo.",
        "advertencia": ADVERTENCIA_PLAN,
    }


ADVERTENCIA_PLAN = (
    "`verifiable` significa que el REGISTRY afirma que hay producer para ese "
    "paso. NO significa que la ejecucion tendra exito: significa unicamente que "
    "el paso tiene nombre y ficha. Un plan no es una promesa; es un camino con "
    "sus puertas marcadas, algunas de ellas cerradas."
)


def _todas_las_fichas() -> Dict[str, Dict[str, Any]]:
    """capacidad -> {estado, backends, limitaciones} derivado del registry.

    Una capacidad sin producer no aparece. Una capacidad que aparece en un
    backend y no en otro declara los dos: la disagreement ENTRE backends es
    informacion, no un defecto que haya que promediar.
    """
    todas: Dict[str, Dict[str, Any]] = {}
    for bid in sorted(registry.backends()):
        caps = registry.get(bid)["capacities"]
        for cap, estado in caps.items():
            e = todas.setdefault(cap, {"estados": {}, "backends": [],
                                       "limitaciones": []})
            e["estados"][bid] = estado
            e["backends"].append(bid)
            if estado == "PARTIAL":
                e["limitaciones"].append(
                    "%s la declara PARTIAL: existe producer pero la salida no "
                    "cumple el contrato" % bid)
    for cap, e in todas.items():
        est = set(e["estados"].values())
        if est == {"UNAVAILABLE"}:
            e["estado_agregado"] = "UNAVAILABLE"
        elif est == {"NOT_DETERMINED"}:
            e["estado_agregado"] = "NOT_DETERMINED"
        elif "AVAILABLE" in est:
            e["estado_agregado"] = "AVAILABLE"
        elif "PARTIAL" in est:
            e["estado_agregado"] = "PARTIAL"
        else:
            e["estado_agregado"] = "NOT_DETERMINED"
        e.pop("limitaciones", None)
        # MEDIDO: `binary.cfg` es PARTIAL en rizin y AVAILABLE en radare2. La
        # agregada sale AVAILABLE, y su limitacion por backend se conserva
        # aparte: promediar los dos estados en uno solo habria hecho
        # desaparecer el hecho de que rizin 0.7.4 solo emite ASCII.
        e["limitaciones"] = ["%s: PARTIAL (existe producer, pero la salida no "
                             "cumple el contrato)" % b
                             for b in e["backends"]
                             if e["estados"][b] == "PARTIAL"]
    return todas


def esta_permitida(capability: str) -> Dict[str, Any]:
    """La allow-list. Devuelve POR QUE, no solo si/no.

    Un rechazo sin motivo es un `blocked` que parece un bug. Y el motivo es lo
    que permite a una IA cambiar de camino: "no hay adapter" y "no hay
    producer" son dos decisiones distintas con dos salidas distintas.
    """
    if not capability or not isinstance(capability, str):
        return {"permitida": False,
                "motivo": "falta 'capability' (o no es texto)",
                "regla": "capability es un identificador CERRADO"}
    # Una capacidad es `prefijo.nombre`. Nada mas. Esto no es una validacion
    # de seguridad: es que un identificador con `/` o espacios no puede ser
    # ninguna de las que existen, y sin esta comprobacion el error seria
    # "capacidad desconocida: ../../etc/passwd", que es un mensaje de error
    # disfrazado de intento de intrusion.
    if "/" in capability or ".." in capability or " " in capability:
        return {"permitida": False,
                "motivo": "una capability es un identificador cerrado "
                          "(prefijo.nombre). '%s' no lo es" % capability,
                "regla": "capability es un identificador CERRADO"}
    fichas = _todas_las_fichas()
    if capability not in fichas:
        return {"permitida": False,
                "motivo": "no hay ninguna capacidad registrada llamada '%s'"
                          % capability,
                "regla": "la allow-list es el REGISTRY, no una lista local",
                "capacidades_conocidas": sorted(fichas)}
    e = fichas[capability]
    if capability not in ADAPTERS:
        return {"permitida": False,
                "motivo": "'%s' esta en el registry como %s pero NO tiene "
                          "adapter: declararla ejecutable seria una capacidad "
                          "sin producer"
                          % (capability, e["estado_agregado"]),
                "regla": "sin adapter no hay producer: capability declarada y "
                         "no ejecutable",
                "estado_registro": e["estado_agregado"]}
    if e["estado_agregado"] not in EJECUTABLES:
        return {"permitida": False,
                "motivo": "'%s' esta en estado %s, y solo %s son ejecutables"
                          % (capability, e["estado_agregado"],
                             "/".join(EJECUTABLES)),
                "regla": "NOT_DETERMINED NO es ejecutable: no se comprobo que "
                         "falte, se comprobo que no se puede verificar",
                "estado_registro": e["estado_agregado"]}
    return {"permitida": True, "motivo": "", "regla": "",
            "estado_registro": e["estado_agregado"],
            "limitaciones": e["limitaciones"],
            "backends": e["backends"]}


def listar() -> Dict[str, Any]:
    """`op: backends`. Que hay, que sabe hacer cada uno, y que no."""
    fichas = _todas_las_fichas()
    ejec = []
    no_ejec = []
    for cap in sorted(fichas):
        p = esta_permitida(cap)
        fila = {"capability": cap,
                "estado": fichas[cap]["estado_agregado"],
                "backends": fichas[cap]["backends"],
                "tiene_adapter": cap in ADAPTERS}
        if p["permitida"]:
            fila["ejecutable"] = True
            fila["limitaciones"] = p.get("limitaciones") or []
            ejec.append(fila)
        else:
            fila["ejecutable"] = False
            fila["motivo"] = p["motivo"]
            no_ejec.append(fila)
    return {
        "contracto": registry.contrato(),
        "decision": registry.decision(),
        "recuento_real": registry.recuento_real(),
        "backends": registry.catalogo(),
        "capacidades": fichas,
        "ejecutables": ejec,
        "no_ejecutables": no_ejec,
        "reglas": {
            "allow_list": "solo capacidades del registry, con adapter, y en "
                          "estado AVAILABLE o PARTIAL",
            "identificador_cerrado": "una capability es prefijo.nombre",
            "parcial": "PARTIAL es ejecutable y conserva su limitacion",
            "no_determinado": "NOT_DETERMINED no es ejecutable",
            "autoria": "la lista vive en el REGISTRY; este modulo la consulta",
        },
        "not_verificables": registry.NO_VERIFICABLES,
    }


def ejecutar(capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """`op: run`. Devuelve SIEMPRE los seis canales, execution included.

    NEVER `empty` por una capability desconocida: eso seria "no hay nada que
    mirar", y hay algo: hay un nombre que no existe. Se responde `blocked` con
    el motivo, que es lo que permite a la IA seguir por otro camino.
    """
    p = esta_permitida(capability)
    if not p["permitida"]:
        return {"status": "blocked", "capability": capability,
                "ejecutada": False,
                "motivo": p["motivo"], "regla": p["regla"],
                "capabilities_conocidas": p.get("capacidades_conocidas")
                or sorted(_todas_las_fichas()),
                "results": [],
                "next_actions": []}
    a = ADAPTERS[capability]
    faltan = [k for k in a["obligatorio"] if not params.get(k)]
    if faltan:
        return {"status": "invalid_input", "capability": capability,
                "ejecutada": False,
                "motivo": "faltan parametros obligatorios: %s"
                          % ", ".join(faltan),
                "parametros": a["parametros"],
                "results": [], "next_actions": []}
    fn = getattr(rz_inspect, a["funcion"], None)
    if fn is None:
        # No deberia pasar: ADAPTERS y el modulo estan juntos. Pero si pasara,
        # se DICE en vez de devolver un traceback.
        return {"status": "error", "capability": capability,
                "ejecutada": False,
                "motivo": "el adapter declara la funcion '%s' y no existe"
                          % a["funcion"],
                "results": [], "next_actions": []}
    kwargs = {k: params[k] for k in a["parametros"] if params.get(k) is not None}
    if "backend_id" not in kwargs:
        kwargs["backend_id"] = a["backend_por_defecto"]
    env = fn(**kwargs)
    env["capability"] = capability
    env["ejecutada"] = True
    env["rc"] = BACKEND_RC.get(env.get("status"), 1)
    # MEDIDO (B4): sin esto, `explain <result_id>` devolvia `empty` después de
    # un `run` que habia funcionado. El resultado existia y no estaba
    # registrado: la cadena de §9 se rompia en el ultimo eslabon, justo el que
    # se pide para poder SEGUIR investigando.
    #
    #     un resultado que no se puede explicar no es un resultado
    #
    # Solo se persiste si hay resultados que explicar. Un `blocked` sin
    # resultados no tiene nada que reconstruir, y registrarlo llenaria la base
    # de filas que no explican nada.
    if env.get("results"):
        op_id = rz_inspect.persistir(env)
        env["operation_id"] = op_id
        # MEDIDO (B4): `result_id` es determinista, así que pedir DOS VECES la
        # misma inspeccion da siempre `COLISION`. Eso NO es un fallo: es que la
        # evidencia ya existe y `explain` la alcanza. Reportarlo como
        # `persistido: false` seria decir "no se guardo" cuando en realidad esta
        # guardada, y una IA leeria que su resultado se ha perdido.
        #
        #     una colision de un id determinista es la garantia funcionando
        if str(op_id).startswith("COLISION:"):
            env["persistido"] = True
            env["nota_persistencia"] = (
                "el resultado ya estaba registrado con el MISMO result_id "
                "(determinista). No se creo una fila nueva porque habria "
                "pisado la anterior con el mismo contenido. La evidencia "
                "sigue disponible con `explain` por ese result_id.")
        else:
            env["persistido"] = True
    else:
        env["operation_id"] = None
        env["persistido"] = False
    return env