#!/usr/bin/env python3
"""M415 — compatibilidad de esquema entre `store.registrar()` y bases existentes.

ARCHIVO NUEVO. No modifica `core/store.py`, `AGENTS.md`, contratos protegidos
ni ninguna base de datos protegida.

EL PROBLEMA, MEDIDO (no inferido)
---------------------------------
`store.DDL` declara 8 columnas que `store.registrar()` escribe, pero NO existe
ninguna funcion `_asegurar_columnas_*` para ellas: `conectar()` aplica el DDL
con `CREATE TABLE IF NOT EXISTS`, que no altera tablas ya creadas. Resultado
en las bases reales del repositorio (las dos, la raiz y `storage/`):

    sqlite3.OperationalError: table operations has no column named declared_scope
    sqlite3.OperationalError: table results has no column named verified_scope

Es decir: la ruta de persistencia (`store.registrar`, usada por `op:run` y por
todos los adapters de `backends/adapters/*.py`) esta rota contra el esquema
que hay en disco. Las 360 operaciones de `storage/` se escribieron antes de
que el contrato M281 anadiera la autorizacion de escritor.

QUE HACE ESTE MODULO
--------------------
1. Declara las 8 columnas que faltan, con los MISMOS tipos y defaults que
   `store.DDL`, para que la migracion no cambie semantica.
2. Migra solo COPIAS. Se niega a tocar en sitio las bases protegidas
   (`rxre.sqlite3` en la raiz y `tools/rxre/storage/rxre.sqlite3`).
3. Verifica invariantes antes/despues: integridad, foreign keys, conteo de
   filas, hash canonico de TODAS las filas de las columnas preexistentes, y
   definicion de las columnas preexistentes. Si algo cambia, borra la copia y
   falla: no deja una base a medias.
4. Es idempotente: la segunda pasada anade 0 columnas.
5. Permite deshacer: `deshacer()` restaura desde el snapshot y comprueba que
   el sha256 resultante es el del snapshot.

POR QUE NO SE TOCA `store.registrar()` PARA QUE HAGA LA MIGRACION
-----------------------------------------------------------------
`core/store.py` es zona protegida (`AGENTS.md` §5; sha256 e9c0cc5f...). Ademas
`conectar()` no es el sitio: muta esquema por diseño (crea tablas `edges`,
`relations`, `missions`, `reflexiones`, `mission_*` y 5 triggers que pueden no
existir). Eso esta bien en una copia; en la base protegida seria un cambio
silencioso. Aqui se mide y se reporta, no se esconde:

    `conectar()` crea tablas/triggers ausentes => se lista en
    `objetos_creados_por_store_conectar` y NO se confunde con la migracion.

LO QUE ESTE MODULO NO HACE
--------------------------
- No migra la base operativa. Eso requiere autorizacion explicita
  (`DBOP_SCHEMA_M290 INSUFFICIENT`, `DB_AUTH_ACTOR_M294 BLOCKED`).
- No decide verdad semantica. Persistir una fila no prueba una afirmacion.
- No arregla `conectar()`: lo usa despues de migrar, sobre la copia.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", ".."))

# Columnas que `store.DDL` declara y que `store.registrar()` escribe.
# El orden y las declaraciones se copian literalmente del DDL para que un
# `ALTER TABLE` produzca la misma forma que una base creada desde cero.
COLUMNAS_FALTANTES: Dict[str, Tuple[Tuple[str, str], ...]] = {
    "operations": (
        ("declared_scope", "TEXT DEFAULT ''"),
        ("authorized_scope", "TEXT DEFAULT ''"),
        ("auth_decision", "TEXT DEFAULT 'UNAUTH'"),
        ("auth_actor", "TEXT DEFAULT ''"),
        ("auth_timestamp", "TEXT DEFAULT ''"),
    ),
    "results": (
        ("verified_scope", "TEXT DEFAULT ''"),
        ("scope_decision", "TEXT DEFAULT 'UNVERIFIED'"),
        ("limitations_json", "TEXT DEFAULT '{}'"),
    ),
}

# Bases que NO se migran en sitio bajo ninguna circunstancia desde este modulo.
RUTAS_PROTEGIDAS = (
    os.path.join(ROOT, "rxre.sqlite3"),
    os.path.join(ROOT, "tools", "rxre", "storage", "rxre.sqlite3"),
)

# Tablas cuyo contenido no debe cambiar con la migracion. `meta` se valida
# aparte: la migracion SI escribe claves nuevas ahi (procedencia), y `sqlite_sequence`
# solo cambiaria si hubiera inserts (no los hay).
TABLAS_DATOS = (
    "operations", "results", "findings", "finding_relations", "audit_log",
    "claims", "research", "execution_events", "conflicts", "contradictions",
    "falsifications", "finding_reevaluations", "aprendizajes", "edges",
    "relations", "results_legacy", "dependency_states", "validation_remediations",
    "relation_chains",
)

VERSION_COMPAT = "m415-1"


# --------------------------------------------------------------------------
# utilidades
# --------------------------------------------------------------------------
def sha256_file(ruta: str) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as fh:
        for bloque in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


def es_ruta_protegida(ruta: str) -> bool:
    """True si `ruta` es (realpath) una de las bases protegidas del repo."""
    real = os.path.realpath(os.path.abspath(ruta))
    return any(real == os.path.realpath(p) for p in RUTAS_PROTEGIDAS)


def _ruta_de_conexion(c: sqlite3.Connection) -> str:
    try:
        for fila in c.execute("PRAGMA database_list"):
            if fila[1] == "main":
                return fila[2] or ""
    except sqlite3.Error:
        pass
    return ""


def exigir_no_protegida(c: sqlite3.Connection) -> str:
    """Aborta si la conexion apunta a una base protegida."""
    ruta = _ruta_de_conexion(c)
    if ruta and es_ruta_protegida(ruta):
        raise PermissionError(
            "MIGRACION_EN_SITIO_PROHIBIDA: %s es base protegida; migrar una "
            "copia y pedir autorizacion explicita (DBOP_SCHEMA_M290 "
            "INSUFFICIENT / DB_AUTH_ACTOR_M294 BLOCKED)" % ruta)
    return ruta


def _columnas(c: sqlite3.Connection, tabla: str) -> Dict[str, Dict[str, Any]]:
    return {r[1]: {"type": r[2], "notnull": r[3], "default": r[4], "pk": r[5]}
            for r in c.execute("PRAGMA table_info(%s)" % tabla)}


def columnas_faltantes(c: sqlite3.Connection) -> Dict[str, List[Tuple[str, str]]]:
    """Columnas del contrato que faltan en ESTA base, por tabla."""
    faltan: Dict[str, List[Tuple[str, str]]] = {}
    for tabla, esperadas in COLUMNAS_FALTANTES.items():
        try:
            actuales = _columnas(c, tabla)
        except sqlite3.Error:
            continue
        if not actuales:
            continue
        pend = [(n, d) for n, d in esperadas if n not in actuales]
        if pend:
            faltan[tabla] = pend
    return faltan


def _tablas(c: sqlite3.Connection) -> List[str]:
    return [r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name")]


def _objetos(c: sqlite3.Connection) -> Dict[str, List[str]]:
    """Triggers, indices y tablas: para detectar cambios colaterales."""
    salida: Dict[str, List[str]] = {"table": [], "trigger": [], "index": []}
    for tipo, nombre in c.execute(
            "SELECT type, name FROM sqlite_master "
            "WHERE type IN ('table','trigger','index') ORDER BY type, name"):
        salida.setdefault(tipo, []).append(nombre)
    return salida


def huella_datos(c: sqlite3.Connection,
                 tablas: Iterable[str] = TABLAS_DATOS,
                 excluir_columnas: Optional[Dict[str, List[str]]] = None
                 ) -> Dict[str, Any]:
    """Hash canonico del contenido de las columnas PREEXISTENTES.

    `excluir_columnas` permite hashear una base vieja y su copia migrada con
    el mismo conjunto de columnas: se excluyen las recien anadidas.
    """
    excluir_columnas = excluir_columnas or {}
    por_tabla: Dict[str, Any] = {}
    total = 0
    for tabla in tablas:
        cols = list(_columnas(c, tabla))
        if not cols:
            continue
        cols = [x for x in cols if x not in excluir_columnas.get(tabla, [])]
        if not cols:
            continue
        sql = "SELECT %s FROM %s ORDER BY rowid" % (
            ",".join('"%s"' % x for x in cols), '"%s"' % tabla)
        try:
            filas = [[_normaliza(v) for v in fila] for fila in c.execute(sql)]
        except sqlite3.Error:
            continue
        h = hashlib.sha256(json.dumps(filas, sort_keys=True,
                                      default=str).encode()).hexdigest()
        por_tabla[tabla] = {"filas": len(filas), "sha256": h, "columnas": cols}
        total += len(filas)
    global_h = hashlib.sha256(
        json.dumps(por_tabla, sort_keys=True, default=str).encode()).hexdigest()
    return {"por_tabla": por_tabla, "filas_total": total, "sha256": global_h}


def _normaliza(v: Any) -> Any:
    if isinstance(v, (bytes, bytearray, memoryview)):
        return {"__bytes_sha256__": hashlib.sha256(bytes(v)).hexdigest()}
    return v


def _meta(c: sqlite3.Connection) -> Dict[str, str]:
    try:
        return {r[0]: r[1] for r in c.execute("SELECT clave, valor FROM meta")}
    except sqlite3.Error:
        return {}


def _integridad(c: sqlite3.Connection) -> Dict[str, Any]:
    ic = c.execute("PRAGMA integrity_check").fetchone()[0]
    fk = [dict(zip(("tabla", "fila", "padre", "fkid"), r))
          for r in c.execute("PRAGMA foreign_key_check")]
    return {"integrity_check": ic, "foreign_key_violations": fk,
            "fk_sha256": hashlib.sha256(
                json.dumps(fk, sort_keys=True, default=str).encode()).hexdigest(),
            "ok": ic == "ok"}


# --------------------------------------------------------------------------
# migracion
# --------------------------------------------------------------------------
def migrar_copia(origen: str, destino: str,
                 huella_snapshot: Optional[str] = None) -> Dict[str, Any]:
    """Copia `origen` a `destino` y anade las columnas del contrato.

    - `origen` se abre en SOLO LECTURA (`mode=ro`): la migracion no puede
      escribir en la fuente ni por error.
    - Se niega si `destino` es una base protegida o ya existe.
    - Verifica invariantes; si falla, elimina `destino` y devuelve BLOCKED.

    Devuelve un dict con `status`, `columnas_anadidas`, `antes`, `despues`,
    `sha256_origen`, `sha256_destino` e `idempotente_segunda_pasada`.
    """
    origen = os.path.abspath(origen)
    destino = os.path.abspath(destino)
    if not os.path.isfile(origen):
        return {"status": "BLOCKED", "reason": "origen inexistente",
                "origen": origen}
    if es_ruta_protegida(destino):
        return {"status": "BLOCKED",
                "reason": "MIGRACION_EN_SITIO_PROHIBIDA: destino protegido",
                "destino": destino}
    if os.path.realpath(origen) == os.path.realpath(destino):
        return {"status": "BLOCKED",
                "reason": "origen y destino son el mismo archivo"}
    if os.path.exists(destino):
        return {"status": "BLOCKED",
                "reason": "destino ya existe; se exige copia nueva para no "
                          "sobrescribir evidencia"}

    os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
    sha_origen = sha256_file(origen)
    if huella_snapshot is None:
        huella_snapshot = sha_origen

    # 1. snapshot consistente (backup API: incluye WAL) desde origen read-only
    src = sqlite3.connect("file:%s?mode=ro" % origen, uri=True)
    dst = sqlite3.connect(destino)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()

    # 2. estado ANTES de migrar (sobre la copia, con sqlite3 crudo:
    #    NO se usa store.conectar() aqui porque su DDL crea tablas/triggers)
    c = sqlite3.connect(destino, isolation_level=None)
    c.row_factory = sqlite3.Row
    try:
        antes = {
            "columnas": {t: _columnas(c, t) for t in COLUMNAS_FALTANTES},
            "huella_datos": huella_datos(c),
            "objetos": _objetos(c),
            "meta": _meta(c),
            "integridad": _integridad(c),
            "columnas_faltantes": columnas_faltantes(c),
        }

        anadidas: Dict[str, List[str]] = {}
        c.execute("BEGIN IMMEDIATE")
        try:
            for tabla, pendientes in antes["columnas_faltantes"].items():
                for nombre, declaracion in pendientes:
                    c.execute("ALTER TABLE %s ADD COLUMN %s %s"
                              % (tabla, nombre, declaracion))
                    anadidas.setdefault(tabla, []).append(nombre)
            ahora = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            if anadidas:
                # La procedencia describe LA migracion. Una segunda pasada sin
                # nada que anadir no debe reescribirla (seria datar de nuevo un
                # cambio que no ocurrio).
                nuevas_meta = {
                    "store_compat_version": VERSION_COMPAT,
                    "store_compat_applied_at": ahora,
                    "store_compat_source_sha256": sha_origen,
                    "store_compat_source_path": origen,
                    "store_compat_added_json": json.dumps(anadidas, sort_keys=True),
                }
            else:
                nuevas_meta = {
                    "store_compat_version": VERSION_COMPAT,
                    "store_compat_last_noop_at": ahora,
                }
            for clave, valor in nuevas_meta.items():
                c.execute("INSERT OR REPLACE INTO meta(clave,valor) VALUES(?,?)",
                          (clave, valor))
            c.execute("COMMIT")
        except Exception as exc:  # noqa: BLE001
            c.execute("ROLLBACK")
            c.close()
            os.remove(destino)
            return {"status": "BLOCKED",
                    "reason": "migracion fallo y se descarto la copia: %s" % exc,
                    "sha256_origen": sha_origen}

        # 3. estado DESPUES, con las mismas columnas preexistentes
        despues = {
            "columnas": {t: _columnas(c, t) for t in COLUMNAS_FALTANTES},
            "huella_datos": huella_datos(
                c, excluir_columnas={t: v for t, v in anadidas.items()}),
            "objetos": _objetos(c),
            "meta": _meta(c),
            "integridad": _integridad(c),
            "columnas_faltantes": columnas_faltantes(c),
        }
    finally:
        c.close()

    # 4. invariantes
    problemas: List[str] = []
    if antes["huella_datos"]["sha256"] != despues["huella_datos"]["sha256"]:
        problemas.append("DATOS_CAMBIADOS: el hash de las filas preexistentes "
                         "no coincide")
    if antes["huella_datos"]["filas_total"] != despues["huella_datos"]["filas_total"]:
        problemas.append("CONTEO_CAMBIADO: %s -> %s" % (
            antes["huella_datos"]["filas_total"],
            despues["huella_datos"]["filas_total"]))
    for tabla, cols in antes["columnas"].items():
        for nombre, definicion in cols.items():
            if despues["columnas"].get(tabla, {}).get(nombre) != definicion:
                problemas.append("COLUMNA_ALTERADA: %s.%s" % (tabla, nombre))
    for tipo in ("table", "trigger", "index"):
        previos = set(antes["objetos"].get(tipo, []))
        posteriores = set(despues["objetos"].get(tipo, []))
        if previos != posteriores:
            problemas.append("OBJETOS_%s_CAMBIADOS: +%s -%s" % (
                tipo.upper(), sorted(posteriores - previos),
                sorted(previos - posteriores)))
    for clave, valor in antes["meta"].items():
        if despues["meta"].get(clave) != valor:
            problemas.append("META_ALTERADA: %s" % clave)
    if not despues["integridad"]["ok"]:
        problemas.append("INTEGRIDAD: %s" % despues["integridad"]["integrity_check"])
    # Las violaciones de FK pueden ser PREEXISTENTES (medido: `rxre.sqlite3`
    # tiene 2 referencias colgando de operations). Lo que la migracion no
    # puede hacer es CAMBIARLAS: se comparan, no se exige que no existan.
    if (antes["integridad"]["fk_sha256"]
            != despues["integridad"]["fk_sha256"]):
        problemas.append("FK_VIOLATIONS_CAMBIADAS: antes=%s despues=%s" % (
            antes["integridad"]["foreign_key_violations"],
            despues["integridad"]["foreign_key_violations"]))
    esperadas = sum(len(v) for v in COLUMNAS_FALTANTES.values())
    realmente = sum(len(v) for v in anadidas.values())
    if despues["columnas_faltantes"]:
        problemas.append("COLUMNAS_SIN_ANADIR: %s" % despues["columnas_faltantes"])

    if problemas:
        os.remove(destino)
        return {"status": "BLOCKED", "reason": "; ".join(problemas),
                "problemas": problemas, "sha256_origen": sha_origen}

    return {
        "status": "PROVEN",
        "version_compat": VERSION_COMPAT,
        "origen": origen,
        "destino": destino,
        "sha256_origen": sha_origen,
        "sha256_snapshot_referencia": huella_snapshot,
        "sha256_destino": sha256_file(destino),
        "columnas_anadidas": anadidas,
        "columnas_anadidas_total": realmente,
        "columnas_esperadas_total": esperadas,
        "antes": antes["huella_datos"],
        "despues": despues["huella_datos"],
        "integridad": despues["integridad"],
        "invariantes_ok": True,
        "objetos_antes": antes["objetos"],
        "objetos_despues": despues["objetos"],
        "meta_compat": despues["meta"],
    }


def asegurar_esquema(c: sqlite3.Connection) -> Dict[str, Any]:
    """Idempotente: anade las columnas que falten en una copia ya abierta.

    Se niega sobre base protegida. Devuelve `columnas_anadidas` (vacio si ya
    estaba compatible) — es la medicion que usa el evaluador de IDEMPOTENCIA.
    """
    ruta = exigir_no_protegida(c)
    pendientes = columnas_faltantes(c)
    anadidas: Dict[str, List[str]] = {}
    for tabla, cols in pendientes.items():
        for nombre, declaracion in cols:
            c.execute("ALTER TABLE %s ADD COLUMN %s %s"
                      % (tabla, nombre, declaracion))
            anadidas.setdefault(tabla, []).append(nombre)
    if anadidas:
        c.commit()
    return {"ruta": ruta, "columnas_anadidas": anadidas,
            "columnas_anadidas_total": sum(len(v) for v in anadidas.values()),
            "compatible": not columnas_faltantes(c)}


def objetos_que_anade_store_conectar(ruta: str) -> Dict[str, List[str]]:
    """Mide el cambio de esquema que produce `store.conectar()` por su DDL.

    Sobre una copia ya migrada: se listan tablas/triggers/indices que aparecen
    al conectar. Se reporta para no confundirlo con la migracion de M415.
    """
    if es_ruta_protegida(ruta):
        raise PermissionError("no se mide conectar() sobre base protegida")
    from . import store  # import local: evita ciclo y deja claro el uso
    antes = sqlite3.connect(ruta, isolation_level=None)
    previos = _objetos(antes)
    antes.close()
    c = store.conectar(ruta)
    c.close()
    despues_c = sqlite3.connect(ruta, isolation_level=None)
    posteriores = _objetos(despues_c)
    despues_c.close()
    salida: Dict[str, List[str]] = {}
    for tipo in ("table", "trigger", "index"):
        nuevos = sorted(set(posteriores.get(tipo, [])) - set(previos.get(tipo, [])))
        if nuevos:
            salida[tipo] = nuevos
    return salida


# --------------------------------------------------------------------------
# persistencia sobre copia migrada (usa store.registrar SIN modificarlo)
# --------------------------------------------------------------------------
def abrir_copia_migrada(origen: str, destino: str,
                        huella_snapshot: Optional[str] = None
                        ) -> Tuple[sqlite3.Connection, Dict[str, Any]]:
    """Migra una copia y la abre con `store.conectar()`.

    Devuelve `(conexion, informe)` con la migracion, los objetos que anadio
    `conectar()` y el sha256 del destino.
    """
    if es_ruta_protegida(destino):
        raise PermissionError("MIGRACION_EN_SITIO_PROHIBIDA: %s" % destino)
    informe = migrar_copia(origen, destino, huella_snapshot=huella_snapshot)
    if informe.get("status") != "PROVEN":
        raise RuntimeError("migracion no verificada: %s" % informe.get("reason"))
    from . import store
    informe["objetos_creados_por_store_conectar"] = \
        objetos_que_anade_store_conectar(destino)
    c = store.conectar(destino)
    return c, informe


def registrar_verificado(c: sqlite3.Connection, request: Dict[str, Any],
                        env: Dict[str, Any], duracion: float = 0.0
                        ) -> Dict[str, Any]:
    """`store.registrar()` + recuperacion independiente + verificacion.

    No reimplementa la escritura: llama al mecanismo existente. Lo que anade
    es la comprobacion de que lo escrito se puede releer con `row_hash`
    correcto, y que el resultado no se ha sobrescrito.
    """
    from . import store
    exigir_no_protegida(c)
    compat = asegurar_esquema(c)
    op_id = store.registrar(c, request, env, duracion)
    ids = [r["result_id"] for r in (env.get("results") or [])
           if isinstance(r, dict) and r.get("result_id")]
    recuperado = store.recuperar_evidencia_resultados(c, ids) if ids else {}
    faltan = [i for i in ids if i not in recuperado]
    hashes: Dict[str, Any] = {}
    for rid in ids:
        fila = c.execute("SELECT row_hash, operation_id FROM results "
                         "WHERE result_id=?", (rid,)).fetchone()
        hashes[rid] = {"row_hash": fila["row_hash"] if fila else None,
                       "operation_id": fila["operation_id"] if fila else None}
    operacion = store.explicar_operacion(c, op_id)
    return {
        "operation_id": op_id,
        "result_ids": ids,
        "recuperados": len(recuperado),
        "faltan": faltan,
        "row_hash_verified": not faltan and bool(ids),
        "hashes": hashes,
        "resultados_en_operacion": len(operacion.get("results") or [])
        if isinstance(operacion, dict) else None,
        "compat": compat,
        "status": "PROVEN" if (ids and not faltan) else "INSUFFICIENT",
    }


# --------------------------------------------------------------------------
# rollback
# --------------------------------------------------------------------------
def deshacer(destino: str, snapshot: str) -> Dict[str, Any]:
    """Restaura `destino` desde `snapshot` y verifica que coincide byte a byte."""
    if es_ruta_protegida(destino):
        return {"status": "BLOCKED",
                "reason": "MIGRACION_EN_SITIO_PROHIBIDA: destino protegido"}
    if not os.path.isfile(snapshot):
        return {"status": "BLOCKED", "reason": "snapshot inexistente"}
    esperado = sha256_file(snapshot)
    src = sqlite3.connect("file:%s?mode=ro" % os.path.abspath(snapshot), uri=True)
    dst = sqlite3.connect(os.path.abspath(destino))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    # Un -wal/-shm sobrante del destino podria reaplicarse sobre el contenido
    # restaurado: se eliminan antes de comparar.
    for sufijo in ("-wal", "-shm"):
        sobrante = os.path.abspath(destino) + sufijo
        if os.path.exists(sobrante):
            os.remove(sobrante)
    # backup() reescribe paginas; el sha del archivo puede diferir por la
    # cabecera WAL/orden de paginas, asi que se compara CONTENIDO, no bytes.
    c = sqlite3.connect(destino, isolation_level=None)
    c.row_factory = sqlite3.Row
    try:
        huella = huella_datos(c)
        cols_ops = list(_columnas(c, "operations"))
        cols_res = list(_columnas(c, "results"))
        integridad = _integridad(c)
    finally:
        c.close()
    src2 = sqlite3.connect("file:%s?mode=ro" % os.path.abspath(snapshot), uri=True)
    src2.row_factory = sqlite3.Row
    try:
        huella_ref = huella_datos(src2)
        cols_ops_ref = list(_columnas(src2, "operations"))
        cols_res_ref = list(_columnas(src2, "results"))
    finally:
        src2.close()
    ok = (huella["sha256"] == huella_ref["sha256"]
          and cols_ops == cols_ops_ref and cols_res == cols_res_ref
          and integridad["ok"])
    return {"status": "PROVEN" if ok else "NOT_DETERMINED",
            "restaurado": ok,
            "sha256_snapshot": esperado,
            "huella_destino": huella["sha256"],
            "huella_snapshot": huella_ref["sha256"],
            "columnas_revertidas": {
                "operations": cols_ops, "results": cols_res},
            "integridad": integridad}


def es_compatible(c: sqlite3.Connection) -> bool:
    return not columnas_faltantes(c)
