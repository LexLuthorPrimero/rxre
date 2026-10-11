#!/usr/bin/env python3
"""RXRE-003. Mutaciones contractuales sobre la INTERFAZ PUBLICA.

POR QUE ESTE FICHERO Y NO UN `if` MAS EN `test_rxre002.py`.

RXRE-002 dejo escrito el hallazgo: `un test que verifica lo que el sistema hace
no prueba que verifique lo correcto`. Un self-test en verde puede ser verde
porque no mira el campo que importa.

Aqui no se comprueba el comportamiento: se MUTA el comportamiento y se exige que
algo lo detecte. Cada mutacion es sobre la interfaz publica -- lo que una IA
tocaria por error, o lo que un cambio futuro romperia en silencio.

Y hay una mutacion que es la mas importante del fichero, y no es sobre RXRE:

    normalizador_ignora_productor

RXRE-002 la sufrio: el normalizador leia `_raw_json` en vez de la salida del
handler, asi que mutar el handler no cambiaba NADA de lo que salia. El camino
probado y el camino usado eran distintos. Si un mutador de esa clase sobrevive,
entonces las pruebas no estan mirando el dato real.

Lo que se exige de cada mutacion: que AL MENOS un test la detecte. Una
mutacion que sobrevive NO se arregla -- se REPARA LA COBERTURA, que es lo que
pide el encargo.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import signal
import sys
import tempfile
from typing import Callable, Dict, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

fails: List[str] = []
notas: List[str] = []


def _leer(p: str) -> str:
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def _escribir(p: str, t: str) -> None:
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(t)


# --- RXRE-1645: interrumpir a mitad de mutacion dejaba el fichero MUTADO.
# El `finally` del bucle NO corre con SIGTERM (Python no instala handler para
# esa senal) ni con SIGKILL. MEDIDO: un `test_mutations003` matado por timeout
# dejo `commands/handlers.py` con la mutacion `m_limitations_str` aplicada; el
# arbol quedo con codigo falso y CUALQUIER medicion posterior habria partido de
# un estado invalido (§01: un error que invalida conocimiento).
#
# Mientras el bucle no corre, el fichero en curso vive en `_EN_CURSO`. Un
# handler de SIGTERM/SIGINT restaura antes de morir. SIGKILL sigue siendo
# imposible de interceptar: por eso el backup `.backup` y el propio git siguen
# siendo la ultima red.
_EN_CURSO: Dict[str, str] = {}


def _restaurar_todo() -> List[str]:
    restaurados = []
    for p, orig in list(_EN_CURSO.items()):
        try:
            _escribir(p, orig)
            restaurados.append(p)
        except Exception:
            pass
    _EN_CURSO.clear()
    return restaurados


def _instalar_limpieza() -> None:
    def _handler(signum, frame):
        restaurados = _restaurar_todo()
        sys.stdout.flush()
        if restaurados:
            sys.stderr.write(
                "\nINTERRUMPIDO (senal %d): restaurado(s) %d fichero(s) "
                "mutado(s)\n" % (signum, len(restaurados)))
            for p in restaurados:
                sys.stderr.write("   " + p + "\n")
        sys.stderr.flush()
        # 128+senal: distingue interrupcion de fallo real del contrato.
        os._exit(128 + signum)

    for s in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(s, _handler)
        except (ValueError, OSError):
            pass


# --- Los mutadores. Cada uno recibe la ruta de un fichero y devuelve True si
# --- pudo aplicar el cambio. False = el mutador no aplica a ese fichero.

M_BLOQUEADO_A_EMPTY = "blocked->empty en el gate del target prohibido"
M_SIN_LIMITATION = "quitar la limitacion obligatoria de empty"
M_SIN_NEXT_ACTION = "dejar next_actions vacio"
M_ACTION_SIN_OP = "proponer una accion sin op"
M_RESULT_ID = "alterar el result_id"
M_SIN_PROVENANCE = "dejar provenance vacio"
M_LIMITATIONS_STR = "las limitations de provenance vuelven a un str troceado"
M_CAP_INVENTADA = "resolver a una capacidad que no existe"
M_ARISTA = "borrar las aristas"
M_CHAIN_VACIA = "dejar chain vacia en explain"
M_INTENCION_INVENTADA = "hacer que resolver() elija siempre la primera"
M_NORMALIZADOR_IG = "el normalizador deja de mirar al productor"
M_HANDLER_MUDO = "el handler deja de devolver resultados"
M_TARGET_LISTA_NEGRA = "target_permitido pasa a lista negra"


def m_blocked_empty(p: str) -> bool:
    t = _leer(p)
    if 'status=E.ST_BLOCKED' not in t:
        return False
    _escribir(p, t.replace('status=E.ST_BLOCKED', 'status=E.ST_EMPTY', 1))
    return True


def m_sin_limitation(p: str) -> bool:
    t = _leer(p)
    viejo = 'if status == ST_EMPTY and not e["limitations"]:'
    if viejo not in t:
        return False
    _escribir(p, t.replace(viejo, "if False and " + viejo, 1))
    return True


def m_sin_next(p: str) -> bool:
    t = _leer(p)
    if "env[\"next_actions\"] = next_actions(" not in t:
        return False
    _escribir(p, t.replace("env[\"next_actions\"] = next_actions(",
                           "env[\"next_actions\"] = [] if True else next_actions(", 1))
    return True


def m_accion_sin_op(p: str) -> bool:
    t = _leer(p)
    viejo = '    if ejecutable:\n        a["op"] = esp["op"]'
    if viejo not in t:
        return False
    _escribir(p, t.replace(viejo, '    if False:\n        a["op"] = esp["op"]', 1))
    return True


def m_result_id(p: str) -> bool:
    t = _leer(p)
    # MEDIDO: la firma de `_id` cambio al incluir la ubicacion, para que el id
    # fuera UNICO (36 usos del mismo texto daban 9 ids). Un mutador que apunta a
    # un texto viejo deja de aplicar en silencio y se reporta como "mutador no
    # aplica", que parece lo mismo que "sobrevivio" y no lo es.
    #
    #     un mutador que no aplica no es un mutador que sobrevive
    viejo = '"result_id": _id(tipo, valor, tool, location),'
    if viejo not in t:
        return False
    _escribir(p, t.replace(viejo, '"result_id": "res_constante",', 1))
    return True


def m_sin_provenance(p: str) -> bool:
    """Deja `provenance` VACIA.

    RXRE-1644: el ancla original -- `provenance=[{"kind": "stage", ...} for e
    in etapas]` -- dejo de existir cuando `engine.ejecutar_pipeline` paso a
    acumular `provenencia` de cada etapa y deduplicarla con
    `_dedup_por_clave`. El mutador reportaba INVALIDO porque no tocaba
    codigo: eso no lo convierte en inocuo, solo en no medido. El ancla
    vigente es la construccion del envelope, y el EFECTO buscado es el mismo
    -- una respuesta sin provenance, que `test_rxre003` SI detecta (lineas
    243-249: `bool(env["provenance"])` y `len(provenance) >= len(stages)`).
    """
    t = _leer(p)
    viejo = "        provenance=_dedup_por_clave(provenencia),"
    if viejo not in t:
        return False
    _escribir(p, t.replace(viejo, "        provenance=[],", 1))
    return True


def m_limitations_str(p: str) -> bool:
    """Reintroduce el defecto RXRE-1644: `lim_pct` como str, no como lista.

    El envelope hace `list(limitations or [])`; sobre un str eso da sus
    CARACTERES. La limitacion de `provenance` (rama JSON) salia como 163
    elementos de una letra. Va contra la seccion 15 de `test_rxre.py`, que
    exige que cada elemento sea una frase.
    """
    t = _leer(p)
    viejo = ('        lim_pct = ["`prov.py --json` devuelve PORCENTAJES de '
             'claves que cumplen "\n'
             '                   "el contrato, no un recuento de apariciones. '
             'Para el "\n'
             '                   "recuento, `rxre provenance` usa '
             '`prov.py --claves`."]')
    nuevo = ('        lim_pct = ("`prov.py --json` devuelve PORCENTAJES de '
             'claves que cumplen "\n'
             '                   "el contrato, no un recuento de apariciones. '
             'Para el "\n'
             '                   "recuento, `rxre provenance` usa '
             '`prov.py --claves`.")')
    if viejo not in t:
        return False
    _escribir(p, t.replace(viejo, nuevo, 1))
    return True


def m_cap_inventada(p: str) -> bool:
    t = _leer(p)
    # El texto literal cambio al reescribir el fallback para la lista blanca de
    # targets. Se busca la forma del dict, no la linea completa, para que un
    # cambio de redaccion del fallback no deje el mutador muerto en silencio.
    viejo = '"resolved": None, "candidates": [],'
    if viejo not in t:
        return False
    _escribir(p, t.replace(viejo, '"resolved": "cap.inventada", "candidates": [],', 1))
    return True


def m_arista(p: str) -> bool:
    t = _leer(p)
    viejo = '        if pat == "escritura":'
    if viejo not in t:
        return False
    _escribir(p, t.replace(viejo, '        if False:', 1))
    return True


def m_chain_vacia(p: str) -> bool:
    t = _leer(p)
    if '"chain": ["result", "operation", "tool", "input", "artifact",\n                      "source"],' not in t:
        return False
    _escribir(p, t.replace('"chain": ["result", "operation", "tool", "input", "artifact",\n                      "source"],',
                           '"chain": [],', 1))
    return True


def m_intencion_inventada(p: str) -> bool:
    t = _leer(p)
    return m_cap_inventada(p)


# La mutacion de la clase de RXRE-002: el normalizador deja de mirar al
# productor. Se aplica sobre el ENGINE, y lo que hay que demostrar es que
# mutar el HANDLER se nota. Por eso el mutador del engine va acompanado de la
# comprobacion de que el handler mutado cambia la respuesta.
def m_normalizador_ignora(p: str) -> bool:
    t = _leer(p)
    viejo = '    d = env.get("_raw_json")'
    if viejo not in t:
        return False
    _escribir(p, t.replace(viejo, '    d = env.get("_raw_json")\n    d = None', 1))
    return True


def m_handler_mudo(p: str) -> bool:
    """Muta el HANDLER, no el normalizador: el caso de RXRE-002 invertido."""
    t = _leer(p)
    viejo = '    hits = d.get("hits", []) or []'
    if viejo not in t:
        return False
    _escribir(p, t.replace(viejo, '    hits = []  # MUTACION: el handler mudo', 1))
    return True


def m_target_lista_negra(p: str) -> bool:
    """Convierte la lista BLANCA de target en lista negra.

    MEDIDO 2026-10-05: `target_permitido` era una lista negra que rechazaba solo
    tres formas del Intel. `i915`, `0000:03:00.0` y `unknown` pasaban los tres.
    Si una mutacion que devuelve eso NO la detecta ningun vector, el vector de
    target esta midiendo la forma del codigo y no el comportamiento.
    """
    t = _leer(p)
    viejo = "    return t in TARGETS_PERMITIDOS"
    if viejo not in t:
        return False
    _escribir(p, t.replace(viejo, "    return t not in ('0000:00:02.0', '0000:02.0', '02.0')", 1))
    return True




MUTACIONES: List[Tuple[str, str, str, str]] = [
    # (nombre, fichero, mutador, suite que debe detectarlo)
    (M_BLOQUEADO_A_EMPTY, "commands/query.py", m_blocked_empty,
     "test_rxre002.py"),
    (M_SIN_LIMITATION, "api/envelope.py", m_sin_limitation,
     "test_rxre.py"),
    # RXRE-1644: la seccion 15 de test_rxre.py ata el TIPO de `limitations`.
    # El defecto real era un str donde el contrato pide List[str], y se
    # reprodujo en el handler de `provenance` (rama JSON).
    (M_LIMITATIONS_STR, "commands/handlers.py", m_limitations_str,
     "test_rxre.py"),
    (M_SIN_NEXT_ACTION, "api/request.py", m_sin_next,
     "test_rxre003.py"),
    (M_ACTION_SIN_OP, "api/request.py", m_accion_sin_op,
     "test_rxre003.py"),
    # La unicidad del id se comprueba en test_rxre003 (y fue un bug REAL que
    # salio al escribir esa comprobacion). Declarar la mutacion contra
    # test_rxre002 daria "SOBREVIVE" sin medir nada.
    (M_RESULT_ID, "core/normalize.py", m_result_id,
     "test_rxre003.py"),
    (M_SIN_PROVENANCE, "core/engine.py", m_sin_provenance,
     "test_rxre003.py"),
    (M_CAP_INVENTADA, "core/capabilities.py", m_cap_inventada,
     "test_rxre002.py"),
    (M_ARISTA, "commands/query.py", m_arista,
     "test_rxre003.py"),
    (M_CHAIN_VACIA, "core/store.py", m_chain_vacia,
     "test_rxre003.py"),
    (M_NORMALIZADOR_IG, "core/engine.py", m_normalizador_ignora,
     "test_rxre003.py"),
    # MEDIDO: esta mutacion la detecta el FIXTURE, no test_rxre003. Declararla
    # contra la suite equivocada daria "SOBREVIVE" sin medir nada, que es peor
    # que no declararla.
    (M_HANDLER_MUDO, "commands/handlers.py", m_handler_mudo,
     "test_fixtures.py"),
    (M_TARGET_LISTA_NEGRA, "api/request.py", m_target_lista_negra,
     "test_rxre003.py"),
]


def _correr(suite: str) -> Tuple[bool, str]:
    ruta = os.path.join(HERE, suite)
    if not os.path.isfile(ruta):
        return False, "suite no existe: %s" % suite
    import subprocess
    p = subprocess.run([sys.executable, ruta], capture_output=True,
                       text=True, timeout=3000)
    return p.returncode != 0, (p.stdout or "")[-400:]


# --- RXRE-004: mutaciones del MECANISMO de backend ----------------------
# §14 pide mutation-first en cada mecanismo nuevo. No son de la interfaz de
# RXRE-001/002/003: son del camino BACKEND -> artefacto -> normalizacion ->
# provenance.
#
# Y la primera reproduce F8: el adapter leia el ejecutable equivocado y
# devolvia `exit 0` con el banner de rizin. Si eso NO lo detecta un vector,
# `exit 0` vuelve a ser sinonimo de resultado valido.

M_EXE_EQUIVOCADO = "el adapter usa el ejecutable equivocado (exit 0 + banner)"
M_PRECHECK_SALTADO = "el precheck se salta la firma ELF"
M_PROV_SIN_HASH = "la provenance pierde el hash del input"
M_HASH_DEL_RESULTADO = "el result_id se deriva solo del valor"
M_INVALIDO_A_VACIO = "invalid_input se convierte en empty"
M_TIPO_SUBIDO = "raw_binary se declara validated_semantics"
M_LIMPIEZA_FALSA = "la limpieza no quita los ANSI"
M_UNSUPPORTED_A_EMPTY = "unsupported se colapsa a empty"
M_VERSION_NO_VERIFICADA = "la version del backend se declara sin verificar"
M_VERSION_STATUS_FALSO = "backend_version_status se fija en VERIFIED"

# --- B2: mutaciones de los vectores que se LKUEGABAan en B0 y B2 ----------
# La regla de B0 sigue vigente: un vector que no esta DISCRIMINANTE no
# verifica el contrato, lo consuela. Estas dos mutan la ARQUITECTURA NO
# SOPORTADA, que es la que se acaba de medir.
M_ARCH_SOPORTADA_SIEMPRE = "una arquitectura sin identificar se declara soportada"
M_ARCH_DEDUCIDA = "la arquitectura se deduce del texto machine"


def m_arch_soportada_siempre(p):
    t = _leer(p)
    v = "    if sin_arch:"
    if v not in t:
        return False
    _escribir(p, t.replace(v, "    if False:  # mutado: siempre soportada", 1))
    return True


def m_arch_deducida(p):
    t = _leer(p)
    viejo = ('    sin_arch = (not arch) or ("unknown" in str(arch).lower()) \\\n')
    if viejo not in t:
        return False
    # Sustituye la comprobacion por una "deduccion": si hay machine, hay arch.
    _escribir(p, t.replace(
        viejo,
        '    sin_arch = not (arch or machine)  # mutado: deduce arch de machine\n',
        1))
    return True


# --- B3: mutaciones de la PROVENANCE PERSISTIDA --------------------------
# La clase de defecto que B3 repara es una FIRMA FALSA: una operacion de
# fichero que declara un target de hardware. Estas mutaciones la reintroducen.

M_TARGET_FALSO = "persistir firma la operacion de fichero con un target PCI"
M_CADENA_SIN_HASH = "la cadena del backend pierde el hash del input"
M_EXPLAIN_SIN_BACKEND = "explain deja de devolver la cadena del backend"



# --- B4: la ALLOW-LIST y la DECISION PRIMARY ------------------------------
# F3 en otra forma. `target_permitido` era una lista negra de targets
# peligrosos; la allow-list de capacidades es "solo lo que el registry
# declara". Estas mutaciones la convierten en lista negra / en lista local.

M_ALLOWLIST_PASA_TODO = "la allow-list acepta cualquier capability existente"
M_ALLOWLIST_COPIA_LOCAL = "la allow-list deja de preguntar al registry"
M_PRIMARY_CAMBIA = "PRIMARY pasa de rizin a radare2"
#: §15: la decision §18 tiene que ser MUTABLE. En prosa no lo seria.
M_DECISION_FICHERO = "backends/decision.json"
M_PARTIAL_COMO_AVAILABLE = "PARTIAL se declara AVAILABLE (se pierde la limitacion)"


def m_allowlist_pasa_todo(p):
    t = _leer(p)
    # Quita la comprobacion de adapter Y la de estado: solo queda "esta en el
    # registry?". Eso es una lista mas permisiva, no una allow-list.
    viejo = '    if capability not in ADAPTERS:'
    if viejo not in t:
        return False
    _escribir(p, t.replace(viejo, "    if False:  # mutado: pasa todo", 1))
    return True


def m_allowlist_copia_local(p):
    t = _leer(p)
    viejo = "    fichas = _todas_las_fichas()"
    if viejo not in t:
        return False
    # Una lista COPIA local. El registry puede cambiar y esta no se enteraria:
    # es el defecto exacto de "copiar en vez de preguntar".
    _escribir(p, t.replace(
        viejo,
        '    fichas = {"binary.inspect": {"estado_agregado": "AVAILABLE",\n'
        '                             "backends": ["rizin"],\n'
        '                             "limitaciones": []}}  # mutado: copia',
        1))
    return True


def m_primary_cambia(p):
    """PRIMARY=rizin -> PRIMARY=radare2, en el fichero de decision.

    MEDIDO (B7): la primera version de este mutador buscaba la cadena
    `"primary": "rizin",` en el CODIGO y devolvia False, porque la decision
    esta en `backends/decision.json` y no en un .py. Un mutador que no aplica
    no es una supervivencia: es MUTATOR_INVALID (§5). Por eso el objetivo
    cambia al fichero y la suite que lo vigila es la de dispatch, que es la
    que COMPARA `primary` contra el recuento real.
    """
    import json as _j
    try:
        d = _j.loads(_leer(p))
    except ValueError:
        return False
    if d.get("primary") != "rizin":
        return False
    d["primary"] = "radare2"
    _escribir(p, _j.dumps(d, indent=2, ensure_ascii=False) + "\n")
    return True


def m_partial_como_available(p):
    t = _leer(p)
    viejo = '"binary.cfg": "PARTIAL",            # agf: ASCII/visual, no JSON'
    if viejo not in t:
        return False
    _escribir(p, t.replace(
        viejo,
        '"binary.cfg": "AVAILABLE",            # mutado: pierde la limitacion', 1))
    return True


def m_target_falso(p):
    t = _leer(p)
    v = '"target": target_binario(artefacto, pre.get("input_hash", ""))},'
    if v not in t:
        return False
    _escribir(p, t.replace(
        v, '"target": "0000:01:00.0"},', 1))
    return True


def m_cadena_sin_hash(p):
    t = _leer(p)
    v = '"input_hash": prov.get("input_hash", ""),'
    if v not in t:
        return False
    _escribir(p, t.replace(v, '"input_hash": "",', 1))
    return True


def m_explain_sin_backend(p):
    t = _leer(p)
    viejo = '        backend = resp.get("cadena_backend") or {}\n'
    if viejo not in t:
        return False
    _escribir(p, t.replace(viejo, "        backend = {}\n", 1))
    return True


def m_exe_equivocado(p):
    t = _leer(p)
    v = '_exe_de(backend_id, "rz-bin") or exe'
    if v not in t:
        return False
    _escribir(p, t.replace(v, "exe", 1))
    return True


def m_precheck_saltado(p):
    t = _leer(p)
    v = "    if not _es_elf(artefacto):"
    if v not in t:
        return False
    _escribir(p, t.replace(v, "    if False:", 1))
    return True


def m_prov_sin_hash(p):
    t = _leer(p)
    v = '        "input_hash": pre["input_hash"],'
    if v not in t:
        return False
    _escribir(p, t.replace(v, '        "input_hash": "",', 1))
    return True


def m_hash_del_resultado(p):
    t = _leer(p)
    i = t.find("    h = hashlib.sha256(")
    if i < 0:
        return False
    j = t.find('.hexdigest()[:12]', i)
    if j < 0:
        return False
    _escribir(p, t[:i] + '    h = hashlib.sha256(str(valor).encode("utf-8")).hexdigest()[:12]'
              + t[j + len('.hexdigest()[:12]'):])
    return True


def m_invalido_a_vacio(p):
    t = _leer(p)
    v = '        return {"status": BK_INVALID, "precheck": pre,'
    if v not in t:
        return False
    _escribir(p, t.replace(v, '        return {"status": BK_EMPTY, "precheck": pre,', 1))
    return True


def m_tipo_subido(p):
    t = _leer(p)
    v = '        "type": RAW_BINARY,'
    if v not in t:
        return False
    _escribir(p, t.replace(v, '        "type": "validated_semantics",', 1))
    return True


def m_limpieza_falsa(p):
    t = _leer(p)
    v = "    return limpio, n"
    if v not in t:
        return False
    _escribir(p, t.replace(v, "    return s, 0", 1))
    return True


def m_unsupported_a_empty(p):
    t = _leer(p)
    v = 'BK_UNSUPPORTED = "unsupported"'
    if v not in t:
        return False
    _escribir(p, t.replace(v, 'BK_UNSUPPORTED = "empty"', 1))
    return True


def m_version_no_verificada(p):
    t = _leer(p)
    # MEDIDO B0: la linea se movio al refactorizar `identidad()` (ahora
    # `verificada = bool(v.get("verificada"))` y despues `"version_verificada":
    # verificada`). El mutador tiene que seguir apuntando a la MISMA
    #semantica, no a una cadena literal que el refactor borre.
    #
    #     un mutador que no aplica no es una supervivencia; es un mutador roto
    for viejo, nuevo in (
            ('"version_verificada": verificada,', '"version_verificada": True,'),
            ('"version_verificada": bool(v.get("verificada")),',
             '"version_verificada": True,')):
        if viejo in t:
            _escribir(p, t.replace(viejo, nuevo, 1))
            return True
    return False


def m_backend_version_status_falsa(p):
    t = _leer(p)
    v = ('"backend_version_status": "VERIFIED" if verificada else "UNVERIFIED",')
    if v not in t:
        return False
    _escribir(p, t.replace(v, '"backend_version_status": "VERIFIED",', 1))
    return True


# MEDIDO (B4): esta lista era de 3-tuplas y `entrada` anvadia la suite
# (`"test_backends004.py"`) para TODAS. Las tres mutaciones de la allow-list y
# la de `PARTIAL` SI se aplicaron, pero se corrrieron contra la suite
# equivocada y sobrevivieron. Tres sobrevividas que eran un fallo del ARNÉS:
# la mutacion estaba bien, la suite asignada no.
#
#     una mutacion contra la suite equivocada no es una supervivencia: es
#     una medicion que no se hizo
_B004 = "test_backends004.py"
_D004 = "test_dispatch004.py"
_MUTACIONES_BACKEND = [
    (M_EXE_EQUIVOCADO, "backends/adapters/rz_inspect.py", m_exe_equivocado, _B004),
    (M_PRECHECK_SALTADO, "backends/adapters/rz_inspect.py", m_precheck_saltado, _B004),
    (M_PROV_SIN_HASH, "backends/adapters/rz_inspect.py", m_prov_sin_hash, _B004),
    (M_HASH_DEL_RESULTADO, "backends/adapters/rz_inspect.py", m_hash_del_resultado, _B004),
    (M_INVALIDO_A_VACIO, "backends/adapters/rz_inspect.py", m_invalido_a_vacio, _B004),
    (M_TIPO_SUBIDO, "backends/adapters/rz_inspect.py", m_tipo_subido, _B004),
    (M_LIMPIEZA_FALSA, "backends/contract.py", m_limpieza_falsa, _B004),
    (M_UNSUPPORTED_A_EMPTY, "backends/contract.py", m_unsupported_a_empty, _B004),
    (M_VERSION_NO_VERIFICADA, "backends/contract.py", m_version_no_verificada, _B004),
    (M_VERSION_STATUS_FALSO, "backends/contract.py", m_backend_version_status_falsa, _B004),
    (M_ARCH_SOPORTADA_SIEMPRE, "backends/adapters/rz_inspect.py",
     m_arch_soportada_siempre, _B004),
    (M_ARCH_DEDUCIDA, "backends/adapters/rz_inspect.py", m_arch_deducida, _B004),
    (M_TARGET_FALSO, "backends/adapters/rz_inspect.py", m_target_falso, _B004),
    (M_CADENA_SIN_HASH, "backends/adapters/rz_inspect.py", m_cadena_sin_hash, _B004),
    (M_EXPLAIN_SIN_BACKEND, "core/store.py", m_explain_sin_backend, _B004),
    (M_ALLOWLIST_PASA_TODO, "backends/dispatch.py", m_allowlist_pasa_todo, _D004),
    (M_ALLOWLIST_COPIA_LOCAL, "backends/dispatch.py", m_allowlist_copia_local, _D004),
    (M_PARTIAL_COMO_AVAILABLE, "backends/registry.py", m_partial_como_available, _D004),
    (M_PRIMARY_CAMBIA, M_DECISION_FICHERO, m_primary_cambia, _D004),
]


# --- RXRE-005: los DOS BLOCKERS reparados -------------------------------
# Cada una seIntrodujo el mecanismo que hace que un external AI no pueda
# usar RXRE, y el vector tiene que detectarla. Si uno de estos sobrevive,
# el blocker vuelve.

M_RESEARCH_SIN_GUARDAR = "una hipotesis no se persiste (checkpoint vacio)"
M_PROVEN_SIN_REFS = "se acepta PROVEN sin evidencia"
M_GAP_KIND_EN_ACCION = "gap_kind se acepta en next_action"
M_TARGET_QUEBRADO = "la accion confunde el OBJETO con el DISPOSITIVO"
M_CONTRACTO_MIENTE = "el contrato vuelve a afirmar que no hay plan"
M_SIN_REQUEST = "next_actions deja de traer la linea enviable"
M_RESULTS_MEAN_HYPOTHESIS = "una hipotesis se guarda como resultado (evidencia)"


def m_research_sin_guardar(p):
    """La hipotesis se acepta pero NO se guarda.

    MEDIDO: esta es la mutacion que reproduce el BLOCKER 2 original sin
    tocar el DDL. `registrar_investigacion` responde `ok` y devuelve un id,
    asi que la IA cree que ha registrado su hipotesis, y el checkpoint
    siguiente sale vacio. Es el fallo mas peligroso de los tres: no da error,
    da confirmacion.

        una escritura que no ocurre tambien es un fallo silencioso
    """
    t = _leer(p)
    v = '    cur = c.execute(\n        "INSERT INTO research(kind,status,' 
    if v not in t:
        return False
    _escribir(p, t.replace(v, "    cur = None  # mutado: no escribe nada\n"
                          + v.split("cur = c.execute(")[0], 1))
    return True


def m_proven_sin_refs(p):
    t = _leer(p)
    v = '    if status == "PROVEN" and not refs:'
    if v not in t:
        return False
    _escribir(p, t.replace(
        v, "    if False:  # mutado: PROVEN sin evidencia", 1))
    return True


def m_gap_kind_en_accion(p):
    t = _leer(p)
    v = '    if gap_kind and kind not in ("hypothesis", "claim"):'
    if v not in t:
        return False
    _escribir(p, t.replace(
        v, "    if False:  # mutado: gap_kind en cualquier kind", 1))
    return True


def m_target_quebrado(p):
    """Vuelve a la colision OBJETO/DISPOSITIVO de RXRE-005.

    Con esta mutacion, la accion `cross_check_uses` copia el SIMBOLO a la
    raiz del request siguiente, `target_permitido` lo lee como dispositivo y
    responde `blocked`: RXRE propone una accion que el propio RXRE rechaza.
    MEDIDO antes de reparar: 3 de 12 acciones disponibles fallaban asi.
    """
    t = _leer(p)
    # MEDIDO (RXRE-005): la primera version de este mutador cambiaba la linea
    # `val = objetivo if ... else tgt`, y SOBREVIVIO. Motivo: la reparacion NO
    # esta ahi. La reparacion es el BLOQUE que va despues
    # (`if esp.get("args_target_es_objeto") and objetivo:`), que quita `target`
    # de los args, lo pone en `inputs` y devuelve el dispositivo a la raiz.
    # Mutar `val` no lo desactiva, porque ese bloque se ejecuta igual.
    #
    #     un mutador que no reproduce el defecto no mide el defecto
    #
    v = '    if esp.get("args_target_es_objeto") and objetivo:'
    if v not in t:
        return False
    _escribir(p, t.replace(
        v, "    if False:  # mutado: vuelve la confusion objeto/dispositivo", 1))
    return True


def m_contrato_miente(p):
    """El contrato vuelve a afirmar que no existe lo que existe.

    Reproduce el BLOCKER 1: una IA que solo lee el contrato no pide `record`
    ni `checkpoint`, porque el contrato dice que no hay. Es el unico mutador
    de todo el fichero que toca un DOCUMENTO, y tambien es el unico cuya
    supervivencia es un fallo silencioso: el codigo funciona igual.

        el codigo puede estar perfecto y el contrato mentir
    """
    t = _leer(p)
    v = "### 1.4 `checkpoint` — continuar sin que nadie te lo explique"
    if v not in t:
        return False
    _escribir(p, t.replace(
        v, v + "\n\n**No hay `checkpoint`.** Se documenta abajo como "
          "ausencia real.\n", 1))
    return True


def m_sin_request(p):
    """`next_actions` deja de traer la linea enviable.

    MEDIDO: con `op` y `args` separados, enviar `args` da
    `error: falta op en la peticion`. `request` es la forma canonica; sin
    ella, toda accion hay que reconstruirla antes de poder seguirla.
    """
    t = _leer(p)
    v = '            a["request"] = dict(args, op=op)'
    if v not in t:
        return False
    _escribir(p, t.replace(
        v, "            pass  # mutado: no hay linea enviable", 1))
    return True


def m_results_mean_hypothesis(p):
    """La hipotesis se guarda como si fuera EVIDENCIA.

    §10: "las interpretaciones deben ser separables de los resultados". Con
    esta mutacion una hipotesis entra en `results`, con su `result_id` y su
    provenance. Un `grep` de la base la encontraria igual que un hallazgo
    medido, y `explain` le diria a la IA que viene de un producer.

        una interpretacion con provenance parece un hecho
    """
    t = _leer(p)
    v = ('    cur = c.execute(\n'
         '        "INSERT INTO research(kind,status,text,gap_kind,')
    if v not in t:
        return False
    insercion_falsa = (
        '    c.execute("INSERT INTO results(result_id,type,value,source,' 
        'file,line,scope,tool,tool_version,status,raw_json,timestamp) "'
        'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", '
        '("mut_" + str(kind), "hyp_" + kind, text, "", "", None, "", "",'
        ' "", "", json.dumps({"text": text}), ts))\n')
    _escribir(p, t.replace(v, insercion_falsa + v, 1))
    return True

def m_refs_invalidos_aceptados(p):
    """Los refs son aceptados aunque NO existan.

    MEDIDO (RXRE-005, D4): refs_invalidos comprobaba que cada referencia
    existia. Mutar esto permite que refs inventados pasen sin error.
    """
    t = _leer(p)
    v = "    malos = refs_invalidos(c, refs)"
    if v not in t:
        return False
    # Mutar: permitir refs no existentes (malos siempre vacio)
    _escribir(p, t.replace(v, "    malos = []  # mutado: refs siempre validos", 1))
    return True


def m_edge_ref_invalido(p):
    """edge: refs se rechazan aunque sean validos.

    MEDIDO (RXRE-005, D5): edge: refs son citables. Mutar esto hace que
    edge: sea rechazado siempre.
    """
    t = _leer(p)
    # Replace the entire if-block
    old = '    if r.startswith("edge:"):'
    if old not in t:
        return False
    # Find the full block and replace with always-reject
    # Use a simpler approach: comment out the edge ref result
    new = '    if False:  # mutado: edge: refs siempre rechazados'
    _escribir(p, t.replace(old, new, 1))
    return True

def m_max_hits_no_limita(p):
    """El tope max_hits no recorta los resultados reales.

    MEDIDO (RXRE-005, D9): el codigo originalmente recortaba `hits` (lo que
    sale en pantalla) pero no los `results` reales. Mutar para que el tope
    NO afecte a los resultados devueltos.
    """
    t = _leer(p)
    v = '        hits = hits[: int(topes)]'
    if v not in t:
        return False
    # Mutar: no truncar hits
    _escribir(p, t.replace(
        v, "        # mutado: tope max_hits no afecta a resultados\n        # hits = hits[: int(topes)]", 1))
    return True



_F005 = "test_field005.py"
M_REF_INVALIDOS_ACEPTADOS = "refs invalidos son aceptados"
M_EDGE_REF_INVALIDO = "edge: refs son rechazados aunque validos"
M_MAX_HITS_NO_LIMITA = "max_hits no recorta los resultados"

MUTACIONES_CAMPO = [
    (M_RESEARCH_SIN_GUARDAR, "core/store.py", m_research_sin_guardar, _F005),
    (M_PROVEN_SIN_REFS, "core/store.py", m_proven_sin_refs, _F005),
    (M_GAP_KIND_EN_ACCION, "core/store.py", m_gap_kind_en_accion, _F005),
    (M_TARGET_QUEBRADO, "api/request.py", m_target_quebrado, "test_rxre003.py"),
    (M_CONTRACTO_MIENTE, "docs/RXRE_PUBLIC_CONTRACT.md", m_contrato_miente, _F005),
    (M_SIN_REQUEST, "api/machine.py", m_sin_request, _F005),
    (M_RESULTS_MEAN_HYPOTHESIS, "core/store.py", m_results_mean_hypothesis, _F005),
    (M_REF_INVALIDOS_ACEPTADOS, "core/store.py", m_refs_invalidos_aceptados, _F005),
    (M_EDGE_REF_INVALIDO, "core/store.py", m_edge_ref_invalido, _F005),
    (M_MAX_HITS_NO_LIMITA, "commands/handlers.py", m_max_hits_no_limita, "test_rxre002.py"),
]

def main() -> int:
    _instalar_limpieza()
    print("MUTACIONES CONTRACTUALES -- RXRE-003 + RXRE-004")
    print()
    sobrevividas = []
    invalidos = []
    aplicadas = 0
    entrada = MUTACIONES + _MUTACIONES_BACKEND + MUTACIONES_CAMPO
    for nombre, rel, mut, suite in entrada:
        ruta = os.path.join(PKG, rel)
        orig = _leer(ruta)
        _EN_CURSO[ruta] = orig
        try:
            if not mut(ruta):
                # §14: MUTATOR_INVALID no es supervivencia. Un mutador que no
                # toca el codigo no ha medido nada, y contarlo como supervivencia
                # infla el numero de forma enganosa.
                print("  INVALIDO     %-46s (no modifica %s)" % (nombre, rel))
                invalidos.append(nombre)
                continue
            aplicadas += 1
            detectada, salida = _correr(suite)
            if detectada:
                print("  DETECTADA    %-46s por %s" % (nombre, suite))
            else:
                print("  SOBREVIVE    %-46s por %s" % (nombre, suite))
                sobrevividas.append(nombre)
        finally:
            _escribir(ruta, orig)
            _EN_CURSO.pop(ruta, None)

    print()
    print("mutaciones aplicadas: %d de %d   invalidos: %d"
          % (aplicadas, len(entrada), len(invalidos)))
    if invalidos:
        print("  (los invalidos NO cuentan como supervivencia: notocaron codigo)")
    if sobrevividas:
        print("SOBREVIVIDAS (%d):" % len(sobrevividas))
        for s in sobrevividas:
            print("   " + s)
        print()
        print("Una mutacion que sobrevive NO es un bug del runtime: es un hueco de")
        print("COBERTURA del contrato. No se arregla anadiendo funcionalidad.")
        return 1
    print("ninguna mutacion sobrevive: el contrato esta verificado por el camino")
    print("real de datos, no solo por la forma final.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
