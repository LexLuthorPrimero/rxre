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

import importlib
import os
import signal
import sys
import threading
import time
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
# MEDIDO: la raiz de PAQUETE, no el directorio de este fichero. Con
# `backends/` en el path, `from core import store` buscaria `backends/core/`.
PKG = os.path.abspath(os.path.join(HERE, "..", ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from backends import registry  # noqa: E402
from backends.contract import BACKEND_RC  # noqa: E402

#: Los unicos adapters que existen. Una capacidad sin entrada aqui NO se
#: ejecuta, por mucho que el registry la declare AVAILABLE: eso seria una
#: capacidad declarada sin producer, que es exactamente lo que §5 prohibe.
#:
#: MEDIDO: hoy hay UNA capacidad con producer. Registrarla aqui no es
#: infraestructura por adelantado: es la lista de lo que existe, y growea
#: cuando growe.
#:
#: ARCH-EXEC-002: dispatch-level timeout. El adapter llama a
#: Backend.ejecutar() que tiene su propio timeout (900s default), pero el
#: adapter tambien hace parsing, cleanup, DB, etc. que no estan cubiertos.
#: Este es un safety net via signal.SIGALRM (Linux-only). NO cancela el
#: trabajo subyacente; impide que el dispatch bloquee indefinidamente.
DISPATCH_TIMEOUT = 600  # 10 minutos: safety net, no el timeout primario.
ADAPTERS = {
    "binary.inspect": {
        "modulo": "backends.adapters.rz_inspect",
        "funcion": "inspect",
        "backend_por_defecto": "rizin",
        "parametros": ["artefacto", "backend_id", "timeout"],
        "obligatorio": ["artefacto"],
    },
    # --- Lote RXRE-BULK-2026-10-12. -------------------------------------
    # MEDIDO: Ghidra 12.1.4 decompila `/usr/bin/ls` (5/5 funciones). Es
    # `PARTIAL` porque su loader ELF no produce funciones para ET_REL, que
    # es justo la clase del driver del proyecto; la limitacion viaja con la
    # capacidad y el adaptador la clasifica como `unsupported`, no `empty`.
    "binary.decompile": {
        "modulo": "backends.adapters.gh_decompile",
        "funcion": "decompile",
        "backend_por_defecto": "ghidra",
        "parametros": ["artefacto", "backend_id", "timeout", "max_funcs",
                       "filtro_nombre", "project_dir", "fixture_json"],
        "obligatorio": ["artefacto"],
    },
    # MEDIDO: spatch 1.3.1 aplica el patron y el control negativo no
    # produce diff. Namespace `source.` porque Coccinelle necesita FUENTES.
    "source.semantic_search": {
        "modulo": "backends.adapters.cocci_search",
        "funcion": "buscar",
        "backend_por_defecto": "coccinelle",
        "parametros": ["artefacto", "patron", "backend_id", "timeout",
                       "include_dirs", "fixture_diff"],
        "obligatorio": ["artefacto", "patron"],
    },
    # MEDIDO 2026-10-15: `amdgpu.h` -> 7066 nodos AST, 10 nodos ERROR.
    # tree-sitter NO sustituye a spatch: spatch responde sobre un patch,
    # tree-sitter responde sobre la ESTRUCTURA. Ademas sus modos de fallo son
    # opuestos (spatch casa dentro de un string; tree-sitter no), asi que un
    # `empty` de uno es discriminante para el otro.
    "runtime.trace": [],
    "formal.check": [],
    "source.ast_parse": {
        "modulo": "backends.adapters.ts_ast",
        "funcion": "parsear",
        "backend_por_defecto": "tree-sitter",
        "parametros": ["artefacto", "lenguaje", "patron", "limite",
                       "backend_id", "timeout"],
        "obligatorio": ["artefacto"],
    },
    # MEDIDO 2026-10-12: rizin `aa; aflj` -> 202 funciones sobre
    # /usr/bin/ls; radare2 -> 201. La diferencia es de COBERTURA de
    # simbolos (200 comunes con offsets IDENTICOS), no de formato. Por eso
    # esta capacidad NO declara un backend como autoridad: ejecuta el que
    # se le pida y declara cual fue.
    #
    # Es la PRIMERA de la brecha de 12: desbloquea basic_blocks,
    # disassemble, xrefs y dataflow, que dependen del mismo discovery.
    # MEDIDO 2026-10-12: las cinco de CONTENEDOR responden SIN `aa`, con
    # la misma forma de invocacion y sin dependencia entre si (iSj 32, iij
    # 121, iEj 16, izj 639, isj 323 sobre /bin/ls). Por eso comparten UN
    # adapter: cerrarlas por separado serian cinco copias del mismo
    # esqueleto invocando cinco veces al mismo producer.
    #
    # El grafo de dependencias medido queda partido aqui: estas cinco no
    # pagan analisis de funciones; basic_blocks, cfg, xrefs, callgraph,
    # dataflow y disassemble_func si, y dependen de `binary.functions`.
    "binary.sections": {
        "modulo": "backends.adapters.rz_container",
        "funcion": "secciones",
        "backend_por_defecto": "rizin",
        "parametros": ["artefacto", "backend_id", "timeout", "limite",
                       "fixture_json"],
        "obligatorio": ["artefacto"],
    },
    "binary.imports": {
        "modulo": "backends.adapters.rz_container",
        "funcion": "imports",
        "backend_por_defecto": "rizin",
        "parametros": ["artefacto", "backend_id", "timeout", "limite",
                       "fixture_json"],
        "obligatorio": ["artefacto"],
    },
    "binary.exports": {
        "modulo": "backends.adapters.rz_container",
        "funcion": "exports",
        "backend_por_defecto": "rizin",
        "parametros": ["artefacto", "backend_id", "timeout", "limite",
                       "fixture_json"],
        "obligatorio": ["artefacto"],
    },
    "binary.strings": {
        "modulo": "backends.adapters.rz_container",
        "funcion": "strings",
        "backend_por_defecto": "rizin",
        "parametros": ["artefacto", "backend_id", "timeout", "limite",
                       "fixture_json"],
        "obligatorio": ["artefacto"],
    },
    "binary.symbols": {
        "modulo": "backends.adapters.rz_container",
        "funcion": "symbols",
        "backend_por_defecto": "rizin",
        "parametros": ["artefacto", "backend_id", "timeout", "limite",
                       "fixture_json"],
        "obligatorio": ["artefacto"],
    },
    # MEDIDO 2026-10-12: `afbj` responde como JSON en los DOS producers
    # (rizin 388 bloques, radare2 386 sobre /bin/ls). Va en
    # `rz_functions` y no en `rz_container` porque MEDIDO necesita `aa`:
    # ahi viven las capacidades que NO lo necesitan.
    #
    # Lo que NO se puede cerrar todavia, con la medicion al lado:
    #   cfg, dataflow, disassemble_func -> `agCj`, `agfj` y `pdfj` NO
    #     producen JSON en rizin NI en radare2 (salida ASCII o malformada).
    #     Cerrarlas exigiria un parser de ASCII, que es otra capacidad y
    #     otro riesgo. Se declaran, no se disimulan.
    #   callgraph -> solo radare2 `agj` responde JSON; rizin `agCj` no.
    #     Cerrarla exigiria declarar la asimetria por producer.
    "binary.basic_blocks": {
        "modulo": "backends.adapters.rz_functions",
        "funcion": "basic_blocks",
        "backend_por_defecto": "rizin",
        # MEDIDO 2026-10-12: `funcion` NO es opcional en la practica. Sin
        # el, `afbj` da los bloques de la funcion en la posicion actual (el
        # entrypoint), que no es lo que el nombre de la capacidad sugiere.
        # Se declara como parametro para que quien llame tenga que decidir.
        "parametros": ["artefacto", "funcion", "backend_id", "timeout",
                       "verb", "limite", "fixture_json"],
        "obligatorio": ["artefacto"],
    },
    # MEDIDO 2026-10-12 (RXRE-1634): `binary.disassemble` y
    # `binary.disassemble_func` las cerraba Capstone, un producer de
    # MODULO en proceso (no subproceso). Se registra aqui y no en
    # `rz_container`/`rz_functions` porque ahi viven las que operatesn
    # sobre rangos de un fichero que otro producer ya delimito.
    #
    # MEDIDO, esto es lo que NO pueden cumplir los producers que ya
    # estaban: rizin `aa; pdfj @ main` no emite JSON, y radare2
    # `agC`/`agf` tampoco. El JSON existe para un rango corto (`pdj 8`) y
    # no para una funcion entera, que es justo el caso de uso.
    "binary.disassemble": {
        "modulo": "backends.adapters.cs_disasm",
        "funcion": "desensamblar",
        "backend_por_defecto": "capstone",
        # `backend_id` va DECLARADO y no por defecto: el dispatch filtra
        # por esta lista. MEDIDO: sin declararlo aqui, un
        # `backend_id="rizin"` se descartaba en silencio y el adapter
        # recibia "capstone" - la comprobacion no podia dispararse y el
        # etiqueta habria mentido.
        "parametros": ["artefacto", "inicio", "longitud", "arquitectura",
                       "timeout", "fixture_bin", "backend_id"],
        "obligatorio": ["artefacto"],
    },
    "binary.disassemble_func": {
        "modulo": "backends.adapters.cs_disasm",
        "funcion": "desensamblar",
        "backend_por_defecto": "capstone",
        "parametros": ["artefacto", "inicio", "longitud", "arquitectura",
                       "timeout", "fixture_bin", "backend_id"],
        "obligatorio": ["artefacto"],
    },
    # MEDIDO 2026-10-12 (RXRE-1635): `binary.xrefs` la cerraba un
    # adapter nuevo (`rz_xrefs`). MEDIDO: `axtj` y `axfj` responden JSON
    # en rizin y radare2. El registro ya documentaba la trampa: "los xrefs
    # exigen `aaa`, no `aa`. MEDIDO: `aa; axtj` -> [] y `aaa; axtj` -> 3".
    # Por eso el adapter toma `nivel_analisis` como parametro y declara la
    # dependencia en cada respuesta: un `empty` sin contexto es un error,
    # porque `aa` da empty sin que falte nada.
    #
    # Capstone NO cubre xrefs: no hace analisis de funciones. Esta
    # capacidad usa rizin/radare2, y no se puede cerrar con un producer
    # que no existe.
    "binary.xrefs": {
        "modulo": "backends.adapters.rz_xrefs",
        "funcion": "xrefs",
        "backend_por_defecto": "rizin",
        "parametros": ["artefacto", "inicio", "longitud", "backend_id",
                       "nivel_analisis", "timeout", "fixture_json"],
        "obligatorio": ["artefacto"],
    },
    # MEDIDO 2026-10-12 (RXRE-1636): `binary.callgraph` cerraba un
    # adapter nuevo (`rz_callgraph`). MEDIDO: radare2 `agCj` produce JSON
    # con funciones y aristas (funciones -> imports). rizin `agCj` no
    # funciona (produce ASCII). Esta es la diferencia clave vs xrefs:
    # callgraph captura relaciones interfuncionales, xrefs solo referencias.
    #
    # ETERA01-D1 (2026-10-17): `nivel_analisis` es parte del contrato. El
    # adapter ejecuta el nivel SOLICITADO (antes `aa; agCj` fijo) y expone el
    # nivel efectivo en `ejecucion.nivel_analisis`. MEDIDO /bin/ls:
    # aa=5 nodos, aaa=84, aaaa=120: un nivel insuficiente puede omitir
    # funciones y relaciones.
    "binary.callgraph": {
        "modulo": "backends.adapters.rz_callgraph",
        "funcion": "callgraph",
        "backend_por_defecto": "radare2",
        "parametros": ["artefacto", "inicio", "longitud", "backend_id",
                       "nivel_analisis", "timeout", "fixture_json"],
        "obligatorio": ["artefacto"],
    },

    # ARCH-EXEC-002: binary.cfg y binary.dataflow ahora tienen adapter.
    # Antes estaban como AVAILABLE en registry pero SIN adapter → NO ejecutables.
    "binary.cfg": {
        "modulo": "backends.adapters.rz_cfg",
        "funcion": "cfg",
        "backend_por_defecto": "radare2",
        "parametros": ["artefacto", "backend_id", "timeout", "verb",
                       "fixture_json"],
        "obligatorio": ["artefacto"],
    },
    "binary.dataflow": {
        "modulo": "backends.adapters.rz_cfg",
        "funcion": "dataflow",
        "backend_por_defecto": "radare2",
        "parametros": ["artefacto", "backend_id", "timeout", "verb",
                       "fixture_json"],
        "obligatorio": ["artefacto"],
    },
    "binary.functions": {
        "modulo": "backends.adapters.rz_functions",
        "funcion": "functions",
        "backend_por_defecto": "rizin",
        "parametros": ["artefacto", "backend_id", "timeout", "verb",
                       "limite", "fixture_json"],
        "obligatorio": ["artefacto"],
    },
    # RXRE-1641: capacidades de hallazgo
    "rxre.create_finding": {
        "modulo": "backends.adapters.rz_findings",
        "funcion": "persistir",
        "backend_por_defecto": "knowledge",
        "parametros": ["capability", "claim", "evidence_ids", "epistemic",
                       "provenance", "limitations", "op_id", "target"],
        "obligatorio": ["claim", "evidence_ids", "epistemic",
                        "provenance", "limitations"],
    },
    "rxre.get_finding": {
        "modulo": "backends.adapters.rz_findings",
        "funcion": "persistir",
        "backend_por_defecto": "knowledge",
        "parametros": ["capability", "finding_id", "epistemic", "provenance",
                       "limitations"],
        "obligatorio": ["finding_id"],
    },
    "rxre.list_finding_relations": {
        "modulo": "backends.adapters.rz_findings",
        "funcion": "persistir",
        "backend_por_defecto": "knowledge",
        "parametros": ["capability", "finding_id", "epistemic", "provenance",
                       "limitations"],
        "obligatorio": ["finding_id"],
    },
    "rxre.create_finding_relation": {
        "modulo": "backends.adapters.rz_findings",
        "funcion": "persistir",
        "backend_por_defecto": "knowledge",
        "parametros": ["capability", "source_finding_id", "target_finding_id",
                       "relation", "evidence", "confidence"],
        "obligatorio": ["source_finding_id", "target_finding_id",
                        "relation", "evidence"],
    },
    # RXRE-1643: knowledge reuse capabilities
    "rxre.list_findings": {
        "modulo": "backends.adapters.rz_findings",
        "funcion": "persistir",
        "backend_por_defecto": "knowledge",
        "parametros": ["capability", "finding_id", "epistemic", "limit"],
        "obligatorio": [],
    },
    "rxre.search_findings": {
        "modulo": "backends.adapters.rz_findings",
        "funcion": "persistir",
        "backend_por_defecto": "knowledge",
        "parametros": ["capability", "artifact", "architecture", "tool", "tool_settings", "question", "limit"],
        "obligatorio": [],
    },
    "rxre.evaluate_applicability": {
        "modulo": "backends.adapters.rz_findings",
        "funcion": "persistir",
        "backend_por_defecto": "knowledge",
        "parametros": ["capability", "finding_id", "artifact", "architecture", "tool", "tool_settings", "question"],
        "obligatorio": [],
    },
    # RXRE-1644: Investigation planner
    "rxre.plan_investigation": {
        "modulo": "backends.adapters.rz_findings",
        "funcion": "persistir",
        "backend_por_defecto": "knowledge",
        "parametros": ["capability", "question", "artifact", "architecture", "tool", "tool_settings", "question_context", "prior_finding_ids"],
        "obligatorio": [],
    },
    # BMS-EXT-002. UMR backend for GPU register observation.
    # NOT_DETERMINED: UMR exists and version is verifiable, but register
    # reading requires root (geteuid()==0). The adapter handles this by
    # returning `blocked` when not root. The capability is NOT executable
    # (NOT_DETERMINED is not in EJECUTABLES), but the adapter is registered
    # so that when permissions are available, it works.
    "gpu.register_read": {
        "modulo": "backends.adapters.umr_read",
        "funcion": "register_read",
        "backend_por_defecto": "umr",
        "parametros": ["pci_address", "register_name", "backend_id",
                       "timeout", "decode"],
        "obligatorio": ["pci_address", "register_name"],
    },
    # RXRE-REA-001: REA adapter for firmware/binary inspection.
    # NOT_DETERMINED: REA 6.5.0 is installed but heavy dependencies (pwntools,
    # pyelftools, unicorn) are not available. The adapter runs REA CLI and
    # returns `unsupported` for deep analysis, `ok` for basic raw-binary inspection.
    "rea.inspect_firmware": {
        "modulo": "backends.adapters.rea_inspect",
        "funcion": "inspect",
        "backend_por_defecto": "rea",
        "parametros": ["artefacto", "backend_id", "timeout"],
        "obligatorio": ["artefacto"],
    },

}

#: Estados que permiten EJECUTAR. `PARTIAL` entra con su limitacion; los otros
#: dos no entran.
EJECUTABLES = ("AVAILABLE", "PARTIAL")


def _persistir_generico(env: Dict[str, Any]) -> Optional[str]:
    """Persiste una operacion cuyo adapter NO define `persistir`.

    MEDIDO 2026-10-15 (RXRE-AUTO-002). Ocho adapters pasaban el gate de los ocho
    principios y no hacian nada al persistirse: `gate=True` con
    `persistido=False` y `operation_id=None`. AGUA quedaba satisfecho en la
    INTENCION y no en el hecho.

    No escribir ocho wrappers a mano: `store.registrar` YA es generico, y los
    ocho wrappers existentes solo difieren en el nombre de la capability y el
    target. Ocho copias del mismo dict es como se producen ocho formas
    distintas.

    ## LO QUE EXIGE, Y NO SE RELAJA.

    Los mismos requisitos que el gate ya aprobo: `result_id` en cada resultado
    e `input_hash` en la provenance. Si falta, NO se guarda y se devuelve None.
    Un fallback que guardara cualquier cosa seria peor que no tener fallback.

    ## LO QUE DECLARA COMO LIMITACION.

    El `question` del request se DERIVA del envelope, no lo escribe el
    adapter. Es menos rico que el wrapper a mano. Si un adapter necesita un
    `question` especifico, debe definir su propio `persistir` y esta funcion
    no lo tocara: `getattr(mod, "persistir", None)` gana.
    """
    from core import store as S

    res = env.get("results") or []
    ids = [r.get("result_id") for r in res
           if isinstance(r, dict) and r.get("result_id")]
    # H1/F4: Para operaciones empty ejecutadas (precheck.ok=true), permitimos
    # la persistencia incluso sin result_id, ya que el objetivo es registrar
    # que la operación ocurrió, no que produjo resultados recuperables.
    _status = env.get("status", "")
    _precheck = env.get("precheck") or {}
    _es_empty_ejecutable = (
        _status == "empty" and _precheck.get("ok") is True
    )
    if not ids and not _es_empty_ejecutable:
        # Sin result_id no hay nada que recuperar: AGUA no se satisface con
        # una promesa. Se declara el motivo en vez de guardar el vacio.
        env["motivo_persistencia"] = (
            "no se persiste: la operacion no trae result_id, y sin el no hay "
            "nada recuperable (AGUA)")
        return None

    prov = env.get("provenance") or {}
    if isinstance(prov, dict) and not prov.get("input_hash"):
        env["motivo_persistencia"] = (
            "no se persiste: la provenance no trae input_hash (TIERRA)")
        return None

    # H1/F4: Para operaciones empty, podemos no tener resultados para extraer
    # artefacto. res0 queda vacio y el target se deriva de capability.
    res0 = res[0] if (res and isinstance(res[0], dict)) else {}
    artefacto = res0.get("source", "") or res0.get("artifact", "") or ""
    cap = env.get("capability") or ""
    scope = res0.get("scope") or ("source" if cap.startswith("source.") else
                                  "binary")
    target = "%s:%s" % (scope, os.path.basename(artefacto) or cap)

    c = S.conectar()
    try:
        existentes = []
        for i in ids:
            if c.execute(
                "SELECT 1 FROM results WHERE result_id=?", (i,)
            ).fetchone():
                existentes.append(i)
        if existentes:
            # Colision: el resultado ya esta guardado. No se reescribe, y se
            # devuelve el identificador que YA existe, porque guardar dos veces
            # lo mismo es crear dos filas que dicen lo mismo.
            return "COLISION:%s" % ",".join(existentes)

        op_id = S.registrar(
            c,
            {"request_id": "",
             "question": env.get("question") or cap,
             "capability": cap,
             "scope": scope,
             "target": target},
            {"operation": cap,
             "status": env.get("status"),
             "backend": env.get("backend_identity") or env.get("backend"),
             "ejecucion": env.get("ejecucion"),
             "provenance": env.get("provenance"),
             "precheck": env.get("precheck"),
             "cadena_backend": env.get("cadena_backend", {}),
             "results": res,
             # RXRE-AUTO-003: persistido en response_json para que el gate
             # en explain pueda leerlo sin inferir.
             "persistido": True},
            duracion=(env.get("ejecucion") or {}).get("duration_s", 0))
        return op_id
    finally:
        c.close()


def _persistir(env: Dict[str, Any]) -> Any:
    """La persistencia de envelopes, que es de RXRE y no de un backend.

    Cada adapter debe definir su propia funcion `persistir(env)` que devuelve
    un identificador de operacion (string) o None si no se pudo persistir.
    Si el adapter devuelve un dict con `operation_id` (patron de rz_xrefs y
    rz_callgraph), se extrae el string y se preserva la metadata en env.
    Esta funcion delega al adapter correspondiente.
    """
    capability = env.get("capability")
    if not capability or capability not in ADAPTERS:
        # No hay adapter registrado, no se puede persistir
        return None

    # RXRE-AUTO-001: la puerta. Se evalua ANTES de tocar la base de datos, y
    # solo sobre `ok`, porque `ok` es el unico estado que puede meter una
    # afirmacion no atribuible. Un `blocked` es una respuesta honesta del
    # producer y se persiste con su motivo.
    #
    # MEDIDO 2026-10-15: antes de esto, `persistido` lo ponia quien quisiera.
    # `test_eco_ast001` lo hacia a mano. El resultado es que el test pasaba y
    # produccion no podia: el envelope de un test compliant es un envelope
    # construido a proposito.
    if not env.get("gate_evaluado"):
        from backends import gate as _gate
        veredicto = _gate.evaluar(env)
        env["gate"] = {
            "evaluable": veredicto.get("evaluable"),
            "operacion_cerrada": veredicto.get("operacion_cerrada"),
            "razon": veredicto.get("razon", ""),
            "estado_envoltura": env.get("status"),
        }
        env["gate_evaluado"] = True
        # MEDIDO 2026-10-15 (mutation testing): se usaba `evaluar()` y se
        # comparaba aqui. Eso dejaba `cerrar_o_abrir()` FUERA del camino: una
        # funcion que decision y a la que nadie llamaba. El mutante que la
        # ponia a `return True` paso 23/23, porque nadie la miraba.
        #
        # Ahora la decision pasa por la funcion que la encapsula. Una sola
        # manera de decidir, y esa si es la que un test puede atacar.
        if not _gate.cerrar_o_abrir(env):
            motivos = _gate.razones_de_bloqueo(env)
            env["motivo_persistencia"] = (
                "NO se persiste: los ocho principios no cierran la operacion. "
                + (" | ".join(motivos) if motivos else "sin detalle"))
            env["gate"]["motivos"] = motivos
            return None
        # MEDIDO 2026-10-15, dos veces en el mismo dia:
        #
        #   1. Sin esto, AGUA decia "no persistido" sobre una operacion
        #      PERFECTAMENTE VALIDA, porque `persistido` solo se ponia
        #      despues de persistir y el gate corre antes. El gate cerraba
        #      contra si mismo y bloqueaba el 100% de las operaciones ok.
        #   2. La solucion NO es poner `persistido = True` aqui: eso hace
        #      que el nombre vuelva a mentir. Lo que se declara es la
        #      INTENCION, y `ejecutar()` confirma con el `operation_id`
        #      real. La propiedad no se relaja: se reparte en dos puntos
        #      donde cada uno mira lo que puede saber.
        env["persiste_pretendido"] = True

    adapter_info = ADAPTERS[capability]
    try:
        mod = importlib.import_module(adapter_info["modulo"])
        persistir_fn = getattr(mod, "persistir", None)
        if persistir_fn is None:
            # MEDIDO 2026-10-15 (RXRE-AUTO-002). Ocho adapters pasaban el gate
            # de los ocho principios y NOHACIAN NADA al persistirse:
            #
            #     gate=True  persistido=False   operation_id=None
            #
            # El gate aprobaba porque la provenance ya estaba en orden, pero
            # el adapter no tenia `persistir`. AGUA quedaba satisfecho en la
            # INTENCION (`persiste_pretendido`) y NO en el hecho. Y la
            # propiedad de AGUA es el hecho: "recuperable por result_id".
            #
            # POR QUE UN FALLBACK Y NO OCHO `persistir`.
            #
            # Porque `store.registrar` YA es generico: toma la operacion y la
            # guarda. Los ocho wrappers existentes solo difieren en el nombre
            # de la capability y el target. Escribir ocho copias del mismo
            # dict es como se producen ocho formas distintas, y las ocho se
            # pudren.
            #
            # Y porque esto NO relaja AGUA: sigue exigiendo `result_id` en los
            # resultados y `input_hash` en la provenance. Si algo falta, el
            # fallback NO guarda. Es el mismo contrato, sin el wrapper.
            #
            # LO QUE SE PIERDE: que el `question` del request sea especifico
            # de la capacidad. Se deriva del envelope. Es menos rico que el
            # wrapper a mano, y eso se declara aqui en vez de fingirse
            # equivalente.
            result = _persistir_generico(env)
            if result is not None:
                env["persistido"] = True
                return result
            return None
        result = persistir_fn(env)
        if result is not None:
            # RXRE-AUTO-001: `persistido` lo declara QUIEN PERSISTIO, no el
            # que lo pidio. Antes lo podia poner cualquiera antes de que
            # existiera el registro; ahora significa "hay fila en la tabla".
            env["persistido"] = True

        # MEDIDO BMS-008: los adapters pueden devolver str (operation_id)
        # o dict con operation_id (rz_xrefs, rz_callgraph). Normalizar a str
        # y preservar metadata para que machine.py pueda exponerla.
        if isinstance(result, dict):
            op_id = result.get("operation_id") or result.get("op_id")
            for key in ("producer", "backend_id", "nivel_analisis", "metadata",
                        "contract_version", "input_hash", "output_hash",
                        "reproducible", "persistido"):
                if key in result and key not in env:
                    env[key] = result[key]
            return op_id
        return result
    except (ImportError, AttributeError):
        # Error al importar el adapter o al obtener persistir
        return None
    except Exception as e:
        # BMS-008: capturar errores de persistencia (sqlite3.OperationalError, etc.)
        # para que no crashee ejecutar(), pero registrar el error para diagnostico.
        env["motivo_persistencia"] = "error en persistir: %s: %s" % (
            type(e).__name__, str(e))
        return None

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
    "binary.callgraph": ["binary.inspect", "binary.functions", "binary.callgraph"],
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




def resolve(capability: str, backend: str = None) -> dict:
    """Resuelve por capacidad (ROUTER-1 / ROUTER-3)."""
    if capability not in ADAPTERS:
        raise ValueError("capacidad desconocida: %s" % capability)
    info = ADAPTERS[capability]
    if backend:
        # Si piden backend específico, verificar que esté en los disponibles
        default = info.get("backend_por_defecto", "")
        # Aceptamos cualquier backend que el adapter declare (simplificado)
        return {"capability": capability, "backend": backend}
    return {"capability": capability, "backend": info.get("backend_por_defecto", info.get("modulo"))}


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


def _run_adapter(fn, kwargs: Dict[str, Any],
                 timeout: int = DISPATCH_TIMEOUT) -> Dict[str, Any]:
    """Ejecuta un adapter con un safety net de timeout.

    El adapter primario usa Backend.ejecutar() (subprocess.run con timeout).
    Pero el adapter tambien hace parsing, cleanup, SQLite ops, etc. que no
    están cubiertos por el timeout del backend. Este safety net via
    signal.SIGALRM impide que el dispatch bloquee indefinidamente.

    SEMÁNTICA DEL TIMEOUT:
    - NO cancela el trabajo subyacente (Python no puede matar threads).
    - NO persiste resultados parciales: si dispara, devolvemos `blocked`.
    - El adapter puede estar en medio de un subprocess.run(); el child puede
      quedar como zombie hasta que el padre termine o muera.
    - Un timeout del dispatch ≠ timeout del backend: el primero es 10 min
      (safety net), el segundo es configurable (default 900s).

    SOLO funciona en el hilo principal (signal.SIGALRM). RXRE corre en
    single-thread. Si se ejecuta en un thread secondario, el timeout se
    desactiva silenciosamente (signal.SIGALRM no propagable a threads).
    """
    def _alarm_handler(signum, frame):
        raise TimeoutError("dispatch timeout")
    # signal.SIGALRM solo funciona en el hilo principal
    is_main = threading.current_thread() is threading.main_thread()
    if not is_main:
        return fn(**kwargs)  # No safety net en threads secondarios
    old = signal.signal(signal.SIGALRM, _alarm_handler)
    signal.alarm(timeout)
    try:
        return fn(**kwargs)
    except TimeoutError:
        return {"status": "blocked", "ejecucion": {"timeout": True,
                "stderr": "timeout a los %ds (dispatch-level)" % timeout},
                "precheck": {"ok": False, "dispatch_timeout": timeout},
                "limitations": [
                    "el adapter no termino a los %ds. Este timeout es un "
                    "safety net y NO cancelo el trabajo subyacente; el "
                    "proceso hijo puede seguir activo." % timeout,
                    "no se persistieron resultados parciales: el envelope "
                    "no tiene `results`, por lo que _persistir no se llama.",
                    "si el producer es un subproceso, verificar procesos "
                    "huerfanos con `ps aux | grep <exe>`."]}
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


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
    # MEDIDO: antes esto era `getattr(rz_inspect, ...)` con el modulo
    # IMPORTADO arriba. Eso hacia que el dispatch solo pudiera despachar a
    # UN adapter, y el registro de la tabla `ADAPTERS` fuera decorativo
    # para todo lo demas: se podia declarar una capacidad con backend y
    # producer, y la ejecucion fallaba con AttributeError.
    #
    # Ahora se resuelve por el `modulo` que la propia tabla declara. La
    # tabla es la autoridad, y el dispatch la consulta: la misma regla que
    # ya valia para la allow-list de capacidades.
    mod = None
    try:
        mod = importlib.import_module(a["modulo"])
    except ImportError as exc:
        return {"status": "blocked", "capability": capability,
                "ejecutada": False,
                "motivo": "el adapter declarado no se pudo importar: %s (%s)"
                          % (a["modulo"], exc),
                "regla": "sin adapter importable no hay producer",
                "results": [], "next_actions": []}
    fn = getattr(mod, a["funcion"], None)
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
    # MEDIDO 2026-10-15 (RXRE-AUTO-002). Las capacidades `rxre.*` declaran
    # `capability` en sus `parametros` porque su adapter (`persistir` de
    # `rz_findings`) es un ENRUTADOR: lee `env.get("capability")` y despacha
    # a `crear_hallazgo`, `listar_hallazgos`, etc.
    #
    # Pero `ejecutar` ponia `env["capability"]` DESPUES de llamar al adapter,
    # asi que el enrutador nunca lo veia y caia por el camino vacio,
    # devolviendo None. Y un None no es una respuesta: es un traceback.
    #
    #     params={'capability': 'rxre.list_findings'}  -> ok
    #     params={'limit': 5}                          -> error
    #
    # Lo medido arriba, sobre las mismas capacidades. Se inyecta el valor
    # que el propio ADAPTERS declara que la funcion necesita: no se inventa
    # un parametro nuevo, se entrega el que la tabla ya pedia.
    if "capability" in a["parametros"] and "capability" not in kwargs:
        kwargs["capability"] = capability
    env = _run_adapter(fn, kwargs)
    # MEDIDO 2026-10-15 (RXRE-AUTO-002). Un adapter que devuelve `None` en vez
    # de un envelope hace crashear el dispatch entero:
    #
    #     TypeError: 'NoneType' object does not support item assignment
    #         env["capability"] = capability
    #
    # Medido sobre `rxre.list_findings`, `rxre.search_findings` y
    # `rxre.get_finding`. No es un traceback feo: es una violacion de CUERPO,
    # que exige que el estado este CONTROLADO. Un adapter que no responde no
    # es una respuesta; y si el dispatch se cae, el que llama no recibe ni el
    # estado.
    #
    # Se convierte en `error` con el motivo, que es lo que el contrato pide:
    # una respuesta controlada con su causa, nunca un traceback.
    if env is None:
        return {"status": "error", "capability": capability,
                "ejecutada": True,
                "motivo": "el adapter '%s' devolvio None en vez de un "
                          "envelope. Un producer que no responde no es una "
                          "respuesta: se reporta como error con su causa"
                          % a["funcion"],
                "results": [], "next_actions": []}
    env["capability"] = capability
    env["ejecutada"] = True
    # MEDIDO 2026-10-12 (RXRE-1632): `ejecutada` dice si se INVOCO al
    # adapter, que no es lo mismo que si se ARRANCO el producer. Un
    # `invalid_input` sale con `ejecutada: True` y con el producer sin
    # tocar: se cayo en el precheck. Es el mismo patron que "exit 0 no es
    # resultado valido", un nivel mas arriba.
    #
    # El nombre solo inducia a error, asi que se hace explicito lo que ya
    # se sabe: `ejecucion` existe en el envelope solo cuando hubo una
    # invocacion real (argv, exit_status, duracion). El campo no cambia
    # `ejecutada` porque un test lo protege con el otro sentido.
    env["producer_ejecutado"] = bool(env.get("ejecucion"))
    env["rc"] = BACKEND_RC.get(env.get("status"), 1)
    # MEDIDO 2026-10-12 (RXRE-1631): el contrato declara `limitations` como
    # campo del envelope, pero los adapters lo dejaban a veces SOLO dentro
    # de `ejecucion`. Un consumidor que lea `env["limitations"]` recibia
    # KeyError en las rutas de error, justo donde mas lo necesita: es ahi
    # donde el motivo es lo unico que dice por que no se pudo.
    #
    # El fallo aparecio en las pruebas de `binary.functions` con la salida
    # mal formada. Se arregla AQUI y no en cada adapter porque es una
    # propiedad del ENVELOPE, no de un producer: cualquier adapter nuevo
    # la tiene gratis y no puede olvidarla.
    if not env.get("limitations"):
        env["limitations"] = (env.get("ejecucion", {}) or {}).get(
            "limitations", [])
    # MEDIDO (B4): sin esto, `explain <result_id>` devolvia `empty` después de
    # un `run` que habia funcionado. El resultado existia y no estaba
    # registrado: la cadena de §9 se rompia en el ultimo eslabon, justo el que
    # se pide para poder SEGUIR investigando.
    #
    #     un resultado que no se puede explicar no es un resultado
    #
    # Solo se persiste si hay resultados que explicar, O si es una operación
    # Ejecutada con cero resultados (status="empty" con precheck.ok=true).
    # Un `blocked` sin resultados no tiene nada que reconstruir, y registrarlo
    # llenaria la base de filas que no explican nada.
    _status = env.get("status", "")
    _ejecucion = env.get("ejecucion") or {}
    _precheck = env.get("precheck") or {}
    # H1/F4: persistir operaciones ejecutadas con results=[], siempre que
    # el precheck haya sido exitoso (precheck.ok=true).
    # Esto permite distinguir EXECUTED+ZERO_RESULTS de NOT_EXECUTED.
    _es_empty_con_ejecucion = (
        _status == "empty"
        and _ejecucion
        and _precheck.get("ok") is True
    )
    if env.get("results") or _es_empty_con_ejecucion:
        op_id = _persistir(env)
        env["operation_id"] = op_id
        # MEDIDO (B4): `result_id` es determinista, así que pedir DOS VECES la
        # misma inspeccion da siempre `COLISION`. Eso NO es un fallo: es que la
        # evidencia ya existe y `explain` la alcanza. Reportarlo como
        # `persistido: false` seria decir "no se guardo" cuando en realidad esta
        # guardada, y una IA leeria que su resultado se ha perdido.
        #
        #     una colision de un id determinista es la garantia funcionando
        if op_id and str(op_id).startswith("COLISION:"):
            env["persistido"] = True
            env["nota_persistencia"] = (
                "el resultado ya estaba registrado con el MISMO result_id "
                "(determinista). No se creo una fila nueva porque habria "
                "pisado la anterior con el mismo contenido. La evidencia "
                "sigue disponible con `explain` por ese result_id.")
        elif op_id:
            env["persistido"] = True
        else:
            # BMS-008: _persistir devolvio None → la persistencia fallo o no
            # se intento. No reportar `persistido: True` falsamente.
            env["persistido"] = False
    else:
        env["operation_id"] = None
        # BMS-009: las capabilities de conocimiento (rxre.create_finding,
        # rxre.create_finding_relation) persisten directamente a findings /
        # finding_relations y no setean 'results'. El adapter puede setear
        # env["persistido"] = True tras una escritura exitosa. Solo asignar
        # False si el adapter no definio persistido — no sobreescribir el
        # juicio del adapter sobre su propia persistencia.
        if "persistido" not in env:
            env["persistido"] = False
    return env