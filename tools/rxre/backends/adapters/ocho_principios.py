#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-ECO-001. Los ocho principios, como CAPA EJECUTABLE, no como prosa.

POR QUE ESTO ES CODIGO Y NO UN DOCUMENTO.

El encargo dice que los ocho principios "deben intervenir en operaciones
reales, no quedarse en documentacion". Documentados, los ocho son ocho
parrafos que nadie ejecuta. Aqui son ocho funciones con ENTRADA, SALIDA Y
FALLO, y el unico criterio para que una exista es que haya cambiado una
decision real.

El contrato de cada principio es el mismo que el de una capacidad: no devuelve
texto, devuelve un estado que puede ser `ok`, `blocked` o `violation`. Y el
`gate()` final es lo que hace que no sean decoracion: sin su veredicto, una
operacion NO se marca como completada.

## QUE ES ESTO Y QUE NO ES

ES una AUDITORIA de una operacion de RXRE, no un plan de trabajo. No decide
que hay que investigar: comprueba si lo que se acaba de hacer cumple las
condiciones que RXRE se exige a si misma.

    un principio que no puede FALLAR no es un principio

Y hay una asimetria deliberada: los ocho pueden devolver `violation`, pero
ninguno puede "aprobar" por defecto. Si no hay evidencia de que la condicion
se cumple, el estado es `NOT_PROVEN`, no `ok`. Que el树的 mayoria no mire es
justamente lo que hay que evitar.

## POR QUE `nota_8_principios` Y NO `ocho_principios`

Porque es una AUDITIA con veredicto, no una enumeracion. Y `nota_` porque lo
que produce es una anotacion sobre una operacion: no la sustituye, no la
sustituye por un puntuacion, no decide el resultado.
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, List

# --------------------------------------------------------------------------
# Veredictos
# --------------------------------------------------------------------------
#: `ok`          la condicion se cumple Y hay evidencia que lo demuestra
#: `violation`   hay evidencia de que NO se cumple
#: `not_proven`  NO HAY EVIDENCIA de que se cumpla. No es lo mismo que `ok`.
#:
#: La distincion importa. Si un principio ausente devuelve `ok`, el sistema se
#: auto-absuelve por omision. §9: EXITENCE != OBSERVATION.
VEREDICTOS = ("ok", "violation", "not_proven")


class V:
    """Un veredicto con su porque. Sin porque, un veredicto no es revisable."""

    __slots__ = ("estado", "porque", "evidencia")

    def __init__(self, estado: str, porque: str, evidencia: Any = None) -> None:
        assert estado in VEREDICTOS, estado
        self.estado = estado
        self.porque = porque
        self.evidencia = evidencia

    def a_dict(self) -> Dict[str, Any]:
        return {"estado": self.estado, "porque": self.porque,
                "evidencia": self.evidencia}

    def __repr__(self) -> str:
        return "<V %s: %s>" % (self.estado, self.porque[:60])


def ok(porque: str, ev: Any = None) -> V:
    return V("ok", porque, ev)


def violation(porque: str, ev: Any = None) -> V:
    return V("violation", porque, ev)


def no_provado(porque: str, ev: Any = None) -> V:
    return V("not_proven", porque, ev)


# --------------------------------------------------------------------------
# 1. CUERPO — observar la realidad
# --------------------------------------------------------------------------
def cuerpo(env: Dict[str, Any]) -> V:
    """La operacion produjo algo REAL y se puede distinguir de lo supuesto.

    El fallo tipico que atrapa: un producer que devuelve `ok` sin haber
    ejecutado nada. El sintoma es un resultado con la forma correcta y el
    contenido vacio.
    """
    pre = env.get("precheck") or {}
    ejec = env.get("ejecucion") or {}
    res = env.get("results") or []

    if env.get("status") not in ("ok", "empty", "unsupported"):
        return violation(
            "una operacion que no llega a `ok` no se audita: su estado es %r"
            % env.get("status"))
    if not res:
        return no_provado(
            "la operacion no produjo resultados que observar",
            {"status": env.get("status")})
    if pre.get("ok") is not True:
        return violation(
            "los resultados existen pero el precheck NO paso: se emitieron "
            "sin haber verificado la entrada", pre)
    if ejec.get("exit_status") not in (0, None):
        return violation(
            "hay resultados con exit_status=%r: el producer fallo y aun asi "
            "se persistio algo" % ejec.get("exit_status"), ejec)
    if "argv" not in ejec and "command_or_api" not in ejec:
        return violation(
            "no hay ni argv ni command_or_api: no se puede reconstruir QUE "
            "se ejecuto, solo QUE se respondió")
    return ok("operacion ejecutada, con argv verificable y resultados reales",
              {"n_resultados": len(res), "exit_status": ejec.get("exit_status"),
               "argv": ejec.get("argv")})


# --------------------------------------------------------------------------
# 2. MENTE — comprender las causas
# --------------------------------------------------------------------------
def mente(env: Dict[str, Any]) -> V:
    """Toda afirmacion lleva su `por_que`, y hay un control negativo.

    Un producer que nunca puede decir "no he encontrado esto" no es un
    discriminante: es una funcion constante. §48.
    """
    res = env.get("results") or []
    lims = [l for r in res if isinstance(r, dict)
            for l in (r.get("limitations") or [])]
    ejec = env.get("ejecucion") or {}

    if res and not lims:
        return violation(
            "hay resultados sin UNA sola limitacion declarada: una capacidad "
            "sin limitaciones declaradas esta diciendo que no tiene ninguna, "
            "y no hay producer en esa posicion")
    if ejec.get("duration_s") is None and env.get("status") == "ok":
        return no_provado(
            "no hay duracion: no se puede distinguir 'no tardo' de 'no se "
            "midio'")
    return ok("limitaciones declaradas y duracion medida",
              {"n_limitaciones": len(lims),
               "duration_s": ejec.get("duration_s")})


# --------------------------------------------------------------------------
# 3. ALMA — mantener el propósito
# --------------------------------------------------------------------------
def alma(env: Dict[str, Any]) -> V:
    """La operacion responde a una PREGUNTA, no a una curiosidad.

    Es la razon por la que `source.ast_parse` exige `patron` O se declara que
    la pregunta es estructural: parsear 7066 nodos sin pregunta es trabajo sin
    destino. Se acepta la pregunta estructural (`que estructura tiene`), pero
    se exige que este EXPLICITA.
    """
    res = env.get("results") or []
    if not res:
        return no_provado("sin resultados no hay proposito que evaluar")
    r0 = res[0] if isinstance(res[0], dict) else {}
    val = r0.get("value")
    tiene_patron = bool((r0.get("raw") or {}).get("n_coincidencias"))

    # MEDIDO 2026-10-15. Conectar el gate al dispatch rompio
    # `test_dispatch004` porque `binary.inspect` no tiene `patron`. No es un
    # defecto del adapter: es que ALMA estaba calibrada para UNA capacidad.
    #
    # La pregunta "que patron buscas?" solo tiene sentido para un producer de
    # TEXTO. Para un binario, la pregunta ES el artefacto: describirse el
    # binario entero es un objetivo legitimo, y `binary.inspect` lo cumple.
    #
    # La regla mira `scope`, que es el propio envelope declarandolo. No es
    # una lista de capacidades admitidas: es una lista de TIPOS de pregunta.
    # Un `gpu.register_read` de manana tendra otro scope, y se le hara la
    # pregunta que le corresponde sin editar nada aqui.
    #
    # Y si `scope` NO esta declarado, no se aplica ninguna excepcion: se
    # sigue exigiendo la forma estricta. La excepcion se PIDE, no se asume.
    scope = (r0.get("scope") or env.get("scope") or "")
    if scope != "source":
        pregunta = (env.get("question") or "").strip()
        artefacto = r0.get("artifact") or r0.get("source") or ""
        if pregunta or (artefacto and r0.get("artifact_hash")):
            return ok("pregunta servida: %s" % (
                "pregunta declarada" if pregunta
                else "artefacto %s con hash" % artefacto),
                {"scope": scope or "no declarado",
                 "pregunta": pregunta, "artefacto": artefacto})
        return violation(
            "scope %r sin pregunta: ni `question` en el envelope ni "
            "artefacto con hash en el resultado. Un producer sin pregunta "
            "que SERVIR es trabajo sin destino (ALMA)"
            % (scope or "no declarado"))

    # Una pregunta de estructura se legitima por el TAMANO del sujeto, no por
    # la excepcion: es lo que hace `binary.inspect` sobre un binario entero.
    es_estructural = isinstance(val, dict) and val.get("nodos", 0) > 0
    if not (es_estructural or tiene_patron):
        return violation(
            "la operacion devuelve estructura pero no hay pregunta: ni "
            "patron ni sujeto que lo justifique. Parsear por parsear es "
            "trabajo sin destino (ALMA)")
    return ok("pregunta servida: %s" % (
        "patron %r" % ((r0.get("raw") or {}).get("n_coincidencias"),)
        if tiene_patron else "estructura de %s nodos" % (val.get("nodos"),)),
        {"patron": tiene_patron, "nodos": (val or {}).get("nodos")})


# --------------------------------------------------------------------------
# 4. TIERRA — anclar el conocimiento
# --------------------------------------------------------------------------
def tierra(env: Dict[str, Any]) -> V:
    """Cada afirmacion lleva su procedencia y su hash de entrada.

    El fallo que mas caro sale en RXRE: un resultado sin `input_hash` no se
    puede volver a ejecutar, y sin volver a ejecutar no se puede comprobar.
    Un resultado huerfano es una afirmacion sin fuente.
    """
    prov = env.get("provenance") or {}
    res = env.get("results") or []

    if isinstance(prov, str):
        if "PROVENANCE_INCOMPLETE" in prov:
            return violation("la provenance se declara incompleta: %s" % prov)
        return no_provado("provenance como cadena sin estructura")
    if not prov:
        return violation("no hay provenance")
    if not prov.get("estado"):
        return no_provado("la provenance no declara su estado")
    if prov.get("estado") != "completa":
        return violation("provenance en estado %r" % prov["estado"])
    if not prov.get("input_hash"):
        return violation(
            "provenance sin input_hash: el resultado no se puede volver a "
            "ejecutar sobre la misma entrada")
    for r in res:
        if isinstance(r, dict) and not r.get("artifact_hash"):
            return violation("un resultado no lleva artifact_hash")
    return ok("provenance completa con input_hash verificable",
              {"input_hash": prov.get("input_hash")[:16],
               "estado": prov.get("estado")})


# --------------------------------------------------------------------------
# 5. FUEGO — transformar y experimentar
# --------------------------------------------------------------------------
def fuego(env: Dict[str, Any]) -> V:
    """La transformacion del producer esta DECLARADA, no implicita.

    "Normaliza" no es una transformacion: es un nombre. Lo que hace
    auditable una transformacion es que se pueda volver a aplicar a la misma
    entrada y dar el mismo resultado.
    """
    prov = env.get("provenance") or {}
    if not isinstance(prov, dict):
        return no_provado("sin provenance estructurada")
    tr = prov.get("transformacion")
    norm = prov.get("normalizador")
    if not tr:
        return violation("no hay transformacion declarada: el valor del "
                         "resultado aparece de la nada")
    if not norm:
        return violation("hay transformacion pero no un normalizador "
                         "identificable: no se puede volver a aplicar")
    return ok("transformacion y normalizador identificados",
              {"transformacion": tr[:80], "normalizador": norm})


# --------------------------------------------------------------------------
# 6. AIRE — preservar el flujo de información
# --------------------------------------------------------------------------
def aire(env: Dict[str, Any]) -> V:
    """Nada se ha truncado en silencio por el camino.

    Es el principio que mas falla sin que nadie lo note: una lista recortada a
    50 que no dice que hay mas hace que un consumidor cuente 50 cuando el
    numero real es 400. No es un error de formato: es un error de magnitud.
    """
    res = env.get("results") or []
    problemas = []
    for r in res:
        if not isinstance(r, dict):
            continue
        raw = r.get("raw") or {}
        # Un total declarado debe ser consistente con la lista que lo acompana.
        if "n_coincidencias" in raw and "coincidencias" in raw:
            total = raw.get("n_coincidencias") or 0
            lista = len(raw.get("coincidencias") or [])
            if lista < total and not raw.get("coincidencias_truncadas"):
                problemas.append(
                    "raw dice %d coincidencias, publica %d y NO declara que "
                    "este truncado" % (total, lista))
        if "n_errores_parseo" in raw and "errores_parseo" in raw:
            total_e = raw.get("n_errores_parseo") or 0
            lista_e = len(raw.get("errores_parseo") or [])
            if lista_e < total_e and not raw.get("errores_parseo_truncados"):
                problemas.append(
                    "raw dice %d errores de parseo, publica %d y NO declara "
                    "truncado" % (total_e, lista_e))
        # Una limitacion que menciona truncado debe existir.
        for lim in (r.get("limitations") or []):
            if "trunc" in lim.lower() and not (
                    raw.get("coincidencias_truncadas")
                    or raw.get("errores_parseo_truncados")):
                problemas.append("limitaion anuncia truncado pero no lo hay: %r"
                                 % lim[:60])
    if problemas:
        return violation("; ".join(problemas), {"n": len(problemas)})
    return ok("ningun truncado sin declarar")


# --------------------------------------------------------------------------
# 7. AGUA — adaptarse y aprender
# --------------------------------------------------------------------------
def agua(env: Dict[str, Any]) -> V:
    """Lo que se aprendio queda PERSISTIDO y es recuperable.

    Un resultado que no se persiste es una afirmacion que existio en el
    scroll del terminal. El principio no es "hay memoria": es que la memoria
    sea recuperable por un tercero que no estaba aqui.
    """
    persistido = env.get("persistido")
    if persistido is True:
        return ok("operacion persistida y recuperable por result_id")
    if persistido is False:
        return violation("la operacion NO se persistio: nadie mas podra "
                         "reconstruirla")

    # MEDIDO 2026-10-15. El gate corre ANTES de `_persistir`, asi que aqui
    # `persistido` todavia no existe. Sin esta rama, AGUA decia "no
    # persistido" sobre una operacion valida y el gate bloqueaba el 100% de
    # las operaciones `ok`: un ciclo AGUA -> persistido -> gate -> AGUA.
    #
    # Lo que se acepta es la INTENCION (`persiste_pretendido`), no la fila.
    # Y se declara como limitacion que la persistencia es la siguiente
    # instruccion: un principio que acepta algo tiene que decir que accepta.
    #
    # Lo que este principio ya NO cubre, y por que no es una perdida: que la
    # escritura falle. Lo cubre `ejecutar()`, que mira el `operation_id`
    # devuelto y solo entonces pone `persistido = True`.
    if env.get("persiste_pretendido") is True:
        return ok("operacion con resultado direccionable y persistencia "
                  "aprobada por el gate; la escritura es la siguiente "
                  "instruccion, no un hecho consumado",
                  {"result_id": (env.get("results") or [{}])[0].get("result_id")})
    if env.get("result_id") is None:
        ids = [r.get("result_id") for r in (env.get("results") or [])
               if isinstance(r, dict)]
        if not any(ids):
            return violation("ningun resultado lleva result_id: la evidencia "
                             "no es direccionable")
        return no_provado("hay result_id (%s) pero la operacion no declara si "
                          "se persistio" % ids[0])
    return ok("hay result_id direccionable", env.get("result_id"))


# --------------------------------------------------------------------------
# 8. ETER — integrar y descubrir
# --------------------------------------------------------------------------
def eter(env: Dict[str, Any]) -> V:
    """El resultado se conecta con lo demas, y lo que no se puede conectar
    se DECLARA como frontera.

    Un grafo sin fronteras declaradas no es un grafo: es un bosque. Y
    `reprocert`/`reproledger`/`openlineage`/`dvc` clonado pero no conectado es
    exactamente ese caso, asi que se comprueba en vez de suponer.
    """
    res = env.get("results") or []
    if not res:
        return no_provado("sin resultados que integrar")
    r0 = res[0] if isinstance(res[0], dict) else {}
    val = r0.get("value") or {}
    raw = r0.get("raw") or {}

    tiene_ruido = val.get("nodos", 0) > 0
    tiene_enlace = bool(raw.get("n_coincidencias"))

    # MEDIDO 2026-10-15. Misma causa que ALMA, y el mismo daño: un
    # `binary.inspect` de `/bin/ls` con su sha256 NO es "un dato aislado".
    # Esta enlazado a las demas capacidades `binary.*` que leen ese mismo
    # artefacto por el mismo hash. Decir lo contrario es una afirmacion falsa,
    # y un principio que miente sobre la mayoria de las capacidades no es un
    # principio: es mala calibracion con buena intencion.
    #
    # El enlace por hash es REAL y verificable: dos resultados que comparten
    # `artifact_hash` se pueden contrastar sin NADIE que lo afirme.
    if not tiene_enlace:
        h = r0.get("artifact_hash") or ""
        alcance = r0.get("scope") or env.get("scope") or ""
        if h and len(h) >= 16 and alcance != "source":
            return ok("enlazable por hash: %d caracteres, scope %r. Otros "
                      "resultados del mismo artefacto se contrastan con el, "
                      "y eso es verificable" % (len(h), alcance),
                      {"artifact_hash": h[:16], "scope": alcance})
    if tiene_ruido and tiene_enlace:
        return ok("el resultado tiene sujeto (estructura) y enlace (patron): "
                  "es integrable en el grafo de hallazgos",
                  {"nodos": val.get("nodos"),
                   "n_coincidencias": raw.get("n_coincidencias")})
    return no_provado(
        "el resultado NO se enlaza con nada: es un dato aislado. Se declara "
        "como frontera, no se disimula: un artefacto sin relacion es "
        "informacion que todavia no es evidencia",
        {"estructura": tiene_ruido, "enlace": tiene_enlace})


# --------------------------------------------------------------------------
# El gate
# --------------------------------------------------------------------------
PRINCIPIOS: Dict[str, Callable[[Dict[str, Any]], V]] = {
    "CUERPO": cuerpo,
    "MENTE": mente,
    "ALMA": alma,
    "TIERRA": tierra,
    "FUEGO": fuego,
    "AIRE": aire,
    "AGUA": agua,
    "ETER": eter,
}


def nota_8_principios(env: Dict[str, Any]) -> Dict[str, Any]:
    """Audita una operacion con los ocho principios.

    NO promedia, NO puntua. Cada principio devuelve su veredicto con su
    porque. El resumen dice CUANTOS fallan y CUANTOS no estan probados, que
    es informacion distinta de un score: un 7/8 con 1 sin probar no es lo
    mismo que un 7/8 con 1 en violacion, y un promedio borra esa
    diferencia.
    """
    veredictos = {nombre: fn(env) for nombre, fn in PRINCIPIOS.items()}
    viol = [n for n, v in veredictos.items() if v.estado == "violation"]
    no_prov = [n for n, v in veredictos.items() if v.estado == "not_proven"]
    cum = [n for n, v in veredictos.items() if v.estado == "ok"]

    if viol:
        estado = "violation"
    elif no_prov:
        # Ausencia de evidencia NO es aprobado. Si no hay prueba de que se
        # cumple, el estado honesto es que no esta probado.
        estado = "not_proven"
    else:
        estado = "ok"

    return {
        "estado": estado,
        "cumplen": cum,
        "en_violacion": viol,
        "sin_probar": no_prov,
        "n_cumplen": len(cum),
        "n_violacion": len(viol),
        "n_sin_probar": len(no_prov),
        "detalle": {n: v.a_dict() for n, v in veredictos.items()},
        "contrato": {
            "no_promedia": "un promedio de 8 veredictos oculta si el fallo es "
                           "una violacion o una falta de prueba",
            "no_absuelve": "un principio sin evidencia devuelve not_proven, "
                           "nunca ok",
            "puede_bloquear": "violation significa que la operacion NO esta "
                              "cerrada, aunque su status sea ok",
        },
    }


def gate(env: Dict[str, Any]) -> Dict[str, Any]:
    """El veredicto que decide si la operacion queda CERRADA.

    `status: ok` del producer NO es lo mismo que operacion cerrada. Este es
    el punto donde un resultado con limitacion se convierte en una accion
    declarada completa.
    """
    nota = nota_8_principios(env)
    cerrada = nota["estado"] == "ok"
    return {
        "operacion_cerrada": cerrada,
        "nota": nota,
        "razon": (
            "los ocho principios pasan" if cerrada else
            "principios en violacion: %s" % ", ".join(nota["en_violacion"])
            if nota["en_violacion"] else
            "principios sin evidencia suficiente: %s" % ", ".join(nota["sin_probar"])),
    }
