#!/usr/bin/env python3
"""FASE B/C/D/E/F, juntas: la operacion `query`. Punto de entrada AI de RXRE-002.

QUE ES ESTO Y QUE NO ES.

Es la via por la que una IA pregunta sin saber nombres de scripts. Recibe el
request del contrato, resuelve la intencion a una capacidad, ejecuta su pipeline,
normaliza, guarda y devuelve. No decide nada por la IA: la intencion se resuelve
por pistas explicitas y se devuelve el reparto completo.

Lo que hace y por que cada cosa esta:

    resolver    intencion -> capacidad, con candidatos y sin adivinar
    composing   pipeline determinista, con estado por etapa
    normalize   resultados con forma comun y el RAW conservado
    store       provenance consultable por result_id
    relations   aristas del dominio SOLO si una herramienta las produjo

Y lo que NO hace, que es lo importante: no completa el build para que `xref`
funcione, no toca hardware, no escribe en el arbol de fuentes, y no convierte
ningun estado. `blocked` se propaga y se dice; `empty` no se convierte en
ausencia; y la Intel no aparece en ningun camino.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Optional

from api import envelope as E
from api.request import construir_request, envolver, target_permitido
from core import capabilities as caps
from core import engine
from core import normalize as N
from core import store as S


def _objetivo_de_la_pregunta(q: str) -> Optional[str]:
    """Saca el OBJETIVO del enunciado en prosa.

    No es un parser de lenguaje: es un caso concreto y declarado. Una IA puede
    escribir `¿quién escribe VM_CONTEXT0_CNTL?` y el objetivo esta ahi. Se
    recognize lo que se puede reconocer con certeza (identificadores C, tokens
    con `_` y mayusculas, nombres de fichero), y si no hay ninguno se devuelve
    None para que la respuesta pida el objetivo explicito.

    Un extractor que adivina es peor que uno que no extrae: un objetivo
    equivocado produce resultados de OTRO objetivo, y eso es un `empty` que se
    lee como un hallazgo.
    """
# Vocabulario minimo del dominio. Sin esto, "arreglar la averia del WIFI" extrae
# `WIFI` como si fuera un identificador de registro y RXRE responde una pregunta
# de fontaneria con el corpus de un driver de GPU.
#
# MEDIDO 2026-10-05: ese fue el caso, y el vector que lo caza: `WIFI` no
# casa con ninguno de los tres grupos. Un extractor que solo dice "no encontre"
# cuando NO encuentra, y adivina cuando encuentra cualquier cosa, es peor que uno
# que no extrae: produce resultados de OTRO objetivo.
#
#     un extractor de objetivo que no dice que NO extrajo, extrae cualquier cosa
#
# Los tres grupos son lo que el proyecto YA tiene en el corpus, no una lista de
# signos English inventada:
#   REG_NOMBRE   nombres de registro de amdgpu (asic_reg)
#   FUNC_NOMBRE  funciones del driver, que llevan prefijo de subsistema
#   FICHERO      rutas de fuente con extension
# MEDIDO 2026-10-05: el filtro es por FORMA y no por lista blanca de prefijos.
# La lista blanca de subsistemas hacia fallar lo que hay de verdad en el driver
# (`amdgpu_vm_init`, `gfxhub_v1_0.c`), y una lista blanca de nombres de funcion
# habria que mantenerla a mano para siempre: exactamente el trabajo que no se
# quiere. La forma es estable y el corpus ya la produce.
_DOMINIO_RE = re.compile(
    r"^(?:"
    # REGISTRO o MACRO: alfabetica + al menos un underscore. `WIFI` NO casa:
    # no tiene underscore, y esa era la forma que se colaba.
    r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+"
    # SIMBOLO DEL DRIVER: minuscula inicial con underscore, o prefijo conocido.
    r"|(?:amdgpu|gfxhub|soc15d|nbio|kmd|kfd|vm|ix|gtt|pte|pde|vmid)_[a-z0-9_]+"
    # FICHERO DEL CORPUS: ruta con extension de fuente.
    r"|[A-Za-z0-9_]+(?:[._/-][A-Za-z0-9_]+)*\.(?:c|h|S)"
    # SIGLA DE UNA PALA, si esta en el vocabulario. La pertenencia se comprueba
    # en Python y no en la regex: una regex de 60 siglas alternadas es ilegible y
    # hay que mantenerla a mano.
    #
    # MEDIDO 2026-10-05: sin esta rama, `VMID` y `GART` no pasaban porque no
    # tienen underscore. La comprobacion real es la de `_TERMINOS_DOMINIO`.
    r"|[A-Z][A-Z0-9]{1,7}"
    r")$")

#: Vocabulario del dominio: siglas de las entidades de GPU que pide el encargo
#: (§20). Es una lista blanca CORTA y CERRADA a proposito, no una lista de
#: nombres de funciones: son siglas, no identificadores, y no crecen con el
#: codigo. MEDIDO 2026-10-05: sin esto, "el registro VMID" no se resolvia,
#: porque `VMID` y `WIFI` tienen identica forma.
_TERMINOS_DOMINIO = frozenset((
    "VMID", "PDB0", "GART", "GTT", "BAR", "VRAM", "SDMA", "PM4", "VCE",
    "CAB", "MMHUB", "NBIO", "SOC15D", "GFX", "PCIE", "MMIO", "IB", "SE",
    "CU", "RB", "SH", "TCC", "UMD", "KMD", "FW", "PSP", "SMU", "PDE", "PTE",
    "VA", "VM", "CPC", "HPD", "UVD", "VCN", "AF", "SC", "AG", "XM", "DBG",
))


def _objetivo_de_la_pregunta(q: str) -> Optional[str]:
    """Saca el OBJETIVO del enunciado en prosa.

    No es un parser de lenguaje: es un extractor con vocabulario, y su
    compromiso es narrower que el de "algo que parece un identificador".
    Devuelve `None` cuando no esta seguro, y la respuesta pide el objetivo
    explicito. Un objetivo equivocado produce resultados de OTRO objetivo, que
    es un `empty` que se lee como un hallazgo.
    """
    q = q or ""
    # MEDIDO 2026-10-05: dos filtros sucesivos, y los dos fallaban en un
    # sentido distinto.
    #
    # 1. La guarda de "esto es una pregunta de RE" descartaba
    #    "donde esta amdgpu_vm_init": tiene `esta`, y la lista de palabras no lo
    #    tenia. Un filtro de vocabulario tiene que incluir las palabras que de
    #    verdad usa quien pregunta, o rechaza preguntas legitimas.
    #
    # 2. Los patrones solapaban y el primero que casa se llevaba el TROZO sin
    #    extension: de "el fichero gfxhub_v1_0.c" sacaba `gfxhub_v1_0`. Sin
    #    extension el objetivo no existe en el corpus, el `search` daria `empty`
    #    y se leeria como que el fichero no aparece.
    #
    #     un objetivo truncado produce un empty que se lee como un hallazgo
    #
    # Por eso los patrones van de mas especifico a menos, y la EXTENSION se
    # busca una sola vez, sobre el token completo.
    # La senal de "esto es RE" es que hay un TERMINO del dominio en el
    # enunciado, no que el verbo este en una lista. Un verbo se puede decir de
    # cien maneras ("mapea", "escribe", "configura", "revisa"); un termino del
    # dominio es un conjunto cerrado.
    _hay_term = any(t in _TERMINOS_DOMINIO
                    for t in re.findall(r"\b[A-Za-z][A-Za-z0-9_]*\b", q))
    _hay_forma = bool(re.search(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b", q)
                      or re.search(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b", q)
                      or re.search(r"\.(?:c|h|S)\b", q))
    if not (_hay_term or _hay_forma):
        return None

    cand: List[str] = []
    # 1) FICHERO: lo mas largo y mas especifico, e incluye la extension.
    cand += re.findall(r"\b[A-Za-z][A-Za-z0-9_]*(?:[._/-][A-Za-z0-9_]+)*"
                       r"\.(?:c|h|S)\b", q)
    # 2) REGISTRO o MACRO: alfabetica + underscore.
    cand += re.findall(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b", q)
    # 3) SIMBOLO DEL DRIVER: minuscula inicial + underscore, prefijo conocido.
    cand += re.findall(r"\b(?:amdgpu|gfxhub|soc15d|nbio|kmd|kfd|vm|ix|gtt|pte|"
                       r"pde|vmid)_[A-Za-z0-9_]+\b", q)
    # 4) TERMINOS DE UNA PALA del dominio, sin distincion de mayusculas.

    # MEDIDO 2026-10-05: "como se mapea la GART" devolvia None y "el registro
    # VMID"_aciertos. La diferencia era que el primer enunciado no contiene
    # NINGUNA de las palabras de la guarda (`registro|quien|donde|...`) y el
    # segundo si. Es decir: el filtro de vocabulario rechazaba preguntas
    # legitimate porque el verbo era "mapea" y no estaba en la lista.
    #
    #     una guarda de vocabulario siempre rechaza la pregunta legitima #N
    #
    # La guarda no era un filtro de dominio: era un filtro de VERBOS, y la
    # lista de verbos no termina. Se cambia de criterio: si el enunciado
    # contiene un termino del dominio, es una pregunta de RE. El termino es la
    # senal, y hay una lista FINITA de terminos; los verbos son infinitos.
    #
    # MEDIDO 2026-10-05: "donde esta el registro VMID" devolvia None. VMID y
    # WIFI tienen la MISMA forma -- cuatro mayusculas, sin underscore --, y solo
    # el vocabulario los distingue. Un filtro de FORMA no puede separarlos, y un
    # filtro de forma no era suficiente.
    #
    # Aqui la lista blanca es legitima y es corta, a diferencia del caso que
    # fallo antes. No es una lista de nombres de funciones, que habria que
    # mantener a mano y creceria sin fin: es el vocabulario del dominio, que es
    # FINITO y estable. Son las siglas de las entidades del §20 del encargo, y
    # todas ellas aparecen en el corpus.
    #
    #     la forma no distingue el dominio; el vocabulario si, y es finito
    for term in re.findall(r"\b[A-Z][A-Z0-9]{1,7}\b", q):
        if term in _TERMINOS_DOMINIO:
            cand.append(term)
            break

    # El filtro final: `_DOMINIO_RE` acepta la FORMA, y para las siglas de una
    # palabra la forma no basta -- `WIFI` tiene la misma que `VMID`. La
    # pertenencia al vocabulario se comprueba aqui, y es lo que impide que
    # cualquier sigla en mayusculas se convierta en un objetivo.
    for p in dict.fromkeys(cand):
        if not _DOMINIO_RE.match(p):
            continue
        if re.fullmatch(r"[A-Z][A-Z0-9]{1,7}", p) and p not in _TERMINOS_DOMINIO:
            continue                      # sigla de una palabra no reconocida
        return p
    return None


def _relaciones_de_registro(target: str, hits: List[Dict[str, Any]],
                            op_id: str) -> List[Dict[str, Any]]:
    """Deriva aristas ESCRIBE/LEE desde los usos, con la limitacion al lado.

    MEDIDO: no hay herramienta en `tools/` que clasifique lectura/escritura. La
    derivacion es por patron de texto (`de_uso_registro`) y cada arista nace
    `observed`, con la limitacion escrita. Una arista `observed` no es un hecho:
    es "el texto casa con un constructor de escritura". La unicidad del escritor
    NO se afirma, porque no se ha medido.
    """
    aristas: List[Dict[str, Any]] = []
    for h in hits:
        r = N.de_uso_registro(h, target)
        loc = r.get("location") or {}
        fn = "%s:%s" % (loc.get("file"), loc.get("line")) if loc.get("file") else None
        if not fn:
            continue
        pat = (r.get("raw") or {}).get("patron")
        if pat == "escritura":
            aristas.append({"src": fn, "tipo": "WRITES", "dst": target,
                            "status": "observed", "tool": "evidence_search.py",
                            "evidence": {"patron": pat, "text": r.get("value")},
                            "limitations": r.get("limitations") or []})
        elif pat == "lectura":
            aristas.append({"src": fn, "tipo": "READS", "dst": target,
                            "status": "observed", "tool": "evidence_search.py",
                            "evidence": {"patron": pat, "text": r.get("value")},
                            "limitations": r.get("limitations") or []})
        else:
            # No se inventa WRITES ni READS para un uso indeterminado. Se
            # guarda REFERENCES, que es lo que si se sabe.
            aristas.append({"src": fn, "tipo": "REFERENCES", "dst": target,
                            "status": "observed", "tool": "evidence_search.py",
                            "evidence": {"patron": pat, "text": r.get("value")},
                            "limitations": r.get("limitations") or []})
    return aristas


def responder(request: Dict[str, Any], db: Optional[Any] = None,
              persistir: bool = True) -> Dict[str, Any]:
    """La operacion `query`. De una pregunta a una respuesta con provenance."""
    # MEDIDO 2026-10-05: un request con `capability` explicita y sin `question`
    # fallaba con `RequestInvalido`, porque `construir_request` exigia `operation`
    # o `question`. Pero `capability` ES una forma de decir que se quiere, y es
    # la forma que usa el fixture y cualquier IA que ya sepa lo que quiere.
    #
    #     el contrato tiene tres maneras de pedir, no dos
    if request.get("capability") and not (request.get("question")
                                          or request.get("operation")):
        request = dict(request, question="capacidad explicita: %s"
                       % request["capability"])
    req = construir_request(request)

    # §31/§32 antes de nada: si el target no es el permitido, no se ejecuta.
    if not target_permitido(req.get("target", "")):
        env = E.envelope(
            req.get("operation") or "query", target=req.get("target"),
            status=E.ST_BLOCKED,
            limitations=[
                "target fuera del alcance de RXRE-002: %s. La GPU integrada del "
                "procesador queda fuera de TODA operacion (§32). No se ejecuta "
                "nada y no se afirma nada sobre ella." % req.get("target")],
            evidence=[{"kind": "alcance", "permitido": "0000:01:00.0",
                       "prohibido": "0000:00:02.0"}])
        return envolver(req, env)

    cap = req.get("capability") or ""
    res_cap: Dict[str, Any] = {}
    if not cap:
        # Resolucion por intencion. Si no hay pista, NO se elige una: se
        # devuelven las opciones, que es lo que una IA puede usar para decidir.
        res_cap = caps.resolver(req.get("question", "") or req.get("target", ""))
        cap = res_cap.get("resolved") or ""
        if not cap:
            env = E.envelope(
                "query", target=req.get("target"), status=E.ST_EMPTY,
                limitations=[res_cap.get("reason", "no se resolvio la intencion"),
                             "capacidades disponibles: %s"
                             % ", ".join(res_cap.get("options", []))],
                evidence=[{"kind": "capacidades", "opciones": caps.disponibles()}])
            return envolver(req, env, {"capability_resolution": res_cap,
                                       "next_actions": [
                                           {"action": "capabilities",
                                            "why": "elegir una capacidad explicita "
                                                   "de la lista",
                                            "produces": "operacion concreta"}]})
    faltan = caps.entradas_faltan(cap, req)
    if faltan:
        env = E.envelope("query", target=req.get("target"), status=E.ST_EMPTY,
                         limitations=["a la capacidad %s le faltan entradas: %s"
                                      % (cap, ", ".join(faltan))])
        return envolver(req, env, {"capability_resolution": res_cap})

    # MEDIDO 2026-10-05: SIN ESTE TECHO, `query` devolvio 6166562 resultados y
    # tardo 817s. La causa: `_b_search` pasa `--max-hits` a `evidence_search.py`,
    # donde ese flag es el TOPE DE ALMACENAMIENTO, no un limite de la consulta;
    # con el valor por defecto la herramienta recorre el universo entero y
    # escribe todas las coincidencias.
    #
    #     un "max_hits" que no limita la consulta no es un limite
    #
    # El techo sale de la capacidad declarada, no de un default escondido, y se
    # aplica con `min`: una IA puede pedir menos, nunca mas.
    cap_meta = caps.por_nombre(cap) or {}
    techo = int(cap_meta.get("max_hits", 200))
    req = dict(req)
    ins = dict(req.get("inputs") or {})

    # MEDIDO 2026-10-05: la intencion viaja en `question`, y `inputs` queda
    # vacio. Sin esto, `_args_de_operacion` devolvia `target=""` y `_b_search`
    # montaba `--query ''`, que casa con TODO el universo: 6166562 resultados en
    # 863s. El objetivo hay que sacarlo de donde ESTA, no asumir donde deberia
    # estar.
    #
    #     un objetivo ausente no es una busqueda de la cadena vacia
    objetivo = (ins.get("target") or ins.get("register_name")
                or ins.get("symbol_name") or ins.get("query"))
    if not objetivo and cap_meta.get("requires"):
        objetivo = _objetivo_de_la_pregunta(req.get("question", ""))
        if objetivo:
            ins["target"] = objetivo

    if not objetivo and cap_meta.get("requires"):
        env = E.envelope(
            "query", target=req.get("target"), status=E.ST_EMPTY,
            limitations=[
                "la capacidad %s necesita un objetivo (%s) y no se pudo extraer "
                "del enunciado. Pasa `inputs.target` explicitamente."
                % (cap, ", ".join(cap_meta["requires"])),
                "enunciado recibido: %r" % req.get("question", "")],
            evidence=[{"kind": "capability", "value": cap,
                       "requires": cap_meta.get("requires", [])}])
        return envolver(req, env, {"capability_resolution": res_cap})

    ins["max_hits"] = max(1, min(int(ins.get("max_hits") or techo), techo))
    req["inputs"] = ins

    t0 = time.time()
    env = engine.ejecutar_pipeline(cap, req)
    dur = time.time() - t0

    # Las aristas se derivan SOLO de lo que las etapas produjeron. Para
    # capacidades de registro, de los hits de la etapa de busqueda.
    aristas: List[Dict[str, Any]] = []
    if cap.startswith("register."):
        tgt = (req.get("inputs") or {}).get("target", "")
        hits = []
        for r in env.get("results") or []:
            if isinstance(r, dict) and r.get("type") == "source_occurrence":
                hits.append((r.get("raw") or {}))
        aristas = _relaciones_de_registro(tgt, [h for h in hits if h], "")

    op_id = ""
    if persistir:
        try:
            c = db or S.conectar()
            op_id = S.registrar(c, req, env, dur)
            for a in aristas:
                S.anadir_edge(c, a["src"], a["tipo"], a["dst"],
                              status=a["status"], scope=req.get("scope", ""),
                              tool=a["tool"], evidence=a["evidence"],
                              operation_id=op_id)
            if db is None:
                c.close()
        except Exception as e:            # la persistencia no tumba la respuesta
            env.setdefault("limitations", []).append(
                "no se pudo persistir la operacion (%s): la respuesta es valida "
                "pero no sera consultable con explain" % e)

    env["capability_resolution"] = res_cap or {"resolved": cap,
                                               "reason": "indicada por el request"}
    env["operation_id"] = op_id
    env["aristas"] = aristas
    env["duration_s"] = round(dur, 3)

    # MEDIDO (RXRE-005, D9): el contrato promete "tope de RESULTADOS por
    # etapa", pero `_capa_de_busqueda` topa los HITS. Los resultados incluyen
    # ademas los registros SINTETIZADOS (un `register` derivado del objetivo),
    # asi que pedir 8 devolvia 9:
    #
    #     un tope que no topa lo que promete hace falsa una promesa
    #
    # Se topa `results` y se DICE cuanto se recorto. Un recorte silencioso
    # seria peor: la IA creeria que solo hay 9 cosas.
    pedido = (req.get("inputs") or {}).get("max_hits")
    recortados = 0
    if pedido:
        pedido = int(pedido)
        rs = env.get("results") or []
        if len(rs) > pedido:
            recortados = len(rs) - pedido
            env["results"] = rs[:pedido]
            env["resultados_recortados"] = recortados
            env["limitations"] = list(env.get("limitations") or []) + [
                "se recortaron %d resultados para respetar "
                "inputs.max_hits=%d. El recorte NO es ausencia: hay %d "
                "resultados y se devuelven %d. Para ver todos, sube el tope "
                "(maximo de la capacidad: %d)."
                % (recortados, pedido, len(rs), pedido, techo)]

    extras: Dict[str, Any] = {}
    if aristas:
        extras["relations_summary"] = {
            t: sum(1 for a in aristas if a["tipo"] == t)
            for t in sorted({a["tipo"] for a in aristas})}
    return envolver(req, env, extras)


def explain(result_id: str, db: Optional[Any] = None,
            operation_id: str = "") -> Dict[str, Any]:
    """`explain`: por `result_id` (un resultado) o por `operation_id` (una operacion).

    MEDIDO 2026-10-05: aceptaba solo `result_id`, y la accion
    `explain_operation` que proponia `next_actions` fallaba con
    `error: falta 'result_id'`. Era un callejon en la propia reparacion.

    Se measured el otro camino tambien, porque una operacion de dos etapas no se
    puede explicar con el `result_id` de la ultima: hay que ver las dos.
    """
    c = db or S.conectar()
    if operation_id:
        r = S.explicar_operacion(c, operation_id)
    else:
        r = S.explicar(c, result_id)
    c.close()
    env = E.envelope(
        "explain", target=result_id, status=(E.ST_OK if r["status"] == "ok"
                                              else E.ST_EMPTY),
        results=[r] if r["status"] == "ok" else [],
        limitations=r.get("limitations", []),
        provenance=[{"kind": "consulta", "op": "store.explicar",
                     "result_id": result_id}])
    # MEDIDO (B4): la cadena del backend vive DENTRO de `results[0]` pero no se
    # exponia en el nivel superior. Una IA que lee el envelope -- que es lo que
    # hace, porque el envelope es el contrato -- tenia que saber abrir
    # `results[0].backend`, cosa que el contrato no decia. Y el caso grave: sin
    # esta clave, `explain` de una operacion de binario perdia el backend por
    # completo y la cadena de §9 se rompia en la ultima etapa.
    bc = (r.get("backend") or {}) if isinstance(r, dict) else {}
    env["backend"] = bc
    env["cadena_backend"] = bc.get("chain") or []
    if bc:
        env["target"] = bc.get("input_artifact", "") or result_id
    return env


def case(consulta: Dict[str, Any], db: Optional[Any] = None) -> Dict[str, Any]:
    """`case`: el paquete de handoff. §9/§10.

    NO es una tabla nueva ni una copia de la evidencia. Es una vista sobre
    `operations`, con un `case_id` derivado de (target, question). MEDIDO: sin
    esto, T8 -- perdida de contexto tras handoff -- era 100%.

    Lo que devuelve son REFERENCIAS. El detalle de cada resultado esta en
    `explain`, que ya existe y esta probado. Copiar aqui la evidencia seria
    crear un segundo sitio donde buscarla, y los dos se separarian.
    """
    c = db or S.conectar()
    tgt = consulta.get("target") or "0000:01:00.0"
    cid = consulta.get("case_id") or S.case_id_de(tgt, consulta.get("question", ""))
    if not target_permitido(tgt):
        env = E.envelope("case", target=tgt, status=E.ST_BLOCKED,
                         limitations=["target fuera de alcance: %s" % tgt])
        c.close()
        return env
    r = S.re_case(c, tgt)
    c.close()
    env = E.envelope(
        "case", target=tgt,
        status=E.ST_OK if r["status"] == E.ST_OK else E.ST_EMPTY,
        results=r["operations"],
        evidence=[{"kind": "re_case", "case_id": cid,
                   "n_operations": len(r["operations"]),
                   "n_results": len(r["results"]),
                   "n_edges": len(r["edges"])}],
        provenance=[{"kind": "consulta", "op": "store.re_case", "target": tgt}],
        limitations=r["limitations"] + r.get("aviso", []),
    )
    env["case_id"] = cid
    env["re_case"] = {k: r[k] for k in ("operations", "results", "edges")
                      if k in r}
    env["next_actions"] = [
        {"action": "explain", "available": True, "op": "explain",
         "args": {"result_id": (r["results"][0]["result_id"]
                                if r["results"] else "")},
         "why": "el detalle de cualquier resultado del caso",
         "produces": "de donde salio cada dato"},
        {"action": "relation", "available": bool(r["edges"]),
         "op": "relation",
         "args": {"clase": "writers",
                  "nodo": r["edges"][0]["src"] if r["edges"] else ""},
         "why": "las relaciones ya producidas, sin recalcularlas",
         "produces": "aristas del dominio"},
    ]
    return env


def relation_queries(consulta: Dict[str, Any], db: Optional[Any] = None
                     ) -> Dict[str, Any]:
    """`relation writers|consumers|path`. Consulta aristas; no las inventa."""
    c = db or S.conectar()
    clase = (consulta.get("clase") or "").lower()
    nodo = consulta.get("nodo") or ""
    tipo = {"writers": "WRITES", "readers": "READS",
            "references": "REFERENCES"}.get(clase)
    if clase == "path":
        aristas = [dict(x) for x in c.execute(
            "SELECT src,tipo,dst,status,scope,tool,timestamp FROM edges "
            "WHERE src=? OR dst=?", (nodo, nodo)).fetchall()]
        env = E.envelope("relation", target=nodo,
                         status=E.ST_OK if aristas else E.ST_EMPTY,
                         results=aristas,
                         limitations=[] if aristas else
                         ["no hay aristas que toquen %s. Las aristas solo "
                          "existen si una herramienta las produjo" % nodo])
    else:
        if not tipo:
            env = E.envelope("relation", target=nodo, status=E.ST_ERROR,
                             limitations=["clase de relacion desconocida: %s. "
                                          "Validas: writers, readers, references, "
                                          "path" % clase])
            c.close()
            return env
        r = S.relations(c, src=nodo, tipo=tipo)
        env = E.envelope("relation", target=nodo, status=r["status"],
                         results=r["results"], limitations=r["limitations"],
                         provenance=[{"kind": "consulta", "op": "store.relations",
                                      "tipo": tipo}])
    c.close()
    return env
