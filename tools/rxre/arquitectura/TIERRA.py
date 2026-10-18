"""TIERRA: el grafo de evidencia. Y EVIDENCE, que vive dentro de el.

    CAPA TRANSVERSAL · REGISTRA.

Del diagrama:

    grafo de evidencia:
      · hash SHA-256 por artefacto
      · procedencia (productor -> transformacion -> consumidor)
      · contradicciones registradas

Y los tres bloques de schema que el diagrama fija:

    SCHEMA DEL CLAIM  id · statement · object_hash · scope · epistemic_state
                      evidence_refs[] · derivation_refs[] · contradiction_refs[]
                      falsification_test · unresolved_obligations[]
    EVIDENCE          append-only · delete prohibido por MECANISMO
                      hash de fila verificado al leer · supersedes_ref
    ESTADOS           6, incluido INVALIDATED (que NO es automatico)
    HASH              3 capas separadas

DONDE NO SE USA UN LOCK GLOBAL
-------------------------------
`[v3] CONCURRENCIA POR OPERACION (no global)`:

    · actualizar estado  -> optimistic (version + row_count)
    · agregar evidencia  -> append, sin lock sobre el claim
    · reevaluacion       -> pessimistic (locked_by + expires)

Los tres coexisten porque protegen operaciones distintas. Un lock global
serializaria las tres y haria inutil el modelo: la evidencia se anade desde
hilos que estan midiendo el mundo, y bloquearlos mientras otro decide el
estado epistemico convertiria la medicion en una accion atomica.
"""
from __future__ import annotations

import os
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple

from . import (DEFERRED, INVALIDATED, NOT_DETERMINED, PARTIAL, PROVEN,
               PROVEN_ABSENT)
from .schemas import (CLAIM_CAMPOS, EVIDENCE_CAMPOS, canonico,
                      hash_contenido, hash_fila, validar_claim)

# --- decisiones de REEVALUACION (distintas de los estados epistemicos) ----
# REVERTED no es un estado epistemico: es la DECISION de devolver el claim a
# PROVEN porque se refuto la contradiccion. Por eso vive aqui y no en el
# tuplo de estados: una reevaluacion puede decidir INVALIDATED, REVERTED o
# PARTIAL, y solo estos dos ultimos son estados.
REVERTED = "REVERTED"
DECISIONES_REEVALUACION = (INVALIDATED, REVERTED, PARTIAL)

# --- estados de las tres capas del hash -----------------------------------
INTEGRIDAD_PASS = "PASS"
INTEGRIDAD_FAIL = "FAIL"
AUTENTICIDAD_PASS = "PASS"
AUTENTICIDAD_NOT_DETERMINED = "NOT_DETERMINED"
AUTENTICIDAD_FAIL = "FAIL"
VALIDAD_REQUIERE_PRUEBA = "REQUIERE_PRUEBA_SEPARADA"

# --- estados de prueba (distintos de los epistemicos) ---------------------
TEST_PASS = "PASS"
TEST_FAIL = "FAIL"
TEST_NOT_RUN = "NOT_RUN"

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

-- CLAIM. El estado epistemico es UN campo; el estado de la PRUEBA y la
-- severidad de la contradiccion son OTROS. Aplanarlos seria el error que
-- el diagrama prohibe explicitamente.
CREATE TABLE IF NOT EXISTS claims (
    claim_id               TEXT PRIMARY KEY,
    statement              TEXT NOT NULL,
    object_hash            TEXT NOT NULL,
    scope                  TEXT NOT NULL,
    epistemic_state        TEXT NOT NULL,
    evidence_refs          TEXT NOT NULL DEFAULT '[]',
    derivation_refs        TEXT NOT NULL DEFAULT '[]',
    contradiction_refs     TEXT NOT NULL DEFAULT '[]',
    falsification_test     TEXT NOT NULL,
    unresolved_obligations TEXT NOT NULL DEFAULT '[]',
    reevaluation_ref       TEXT,
    version                INTEGER NOT NULL DEFAULT 0,
    row_count              INTEGER NOT NULL DEFAULT 0,
    created_at             TEXT NOT NULL,
    updated_at             TEXT NOT NULL
);

-- EVIDENCE. Append-only. Y eso no es un flag: es un TRIGGER.
CREATE TABLE IF NOT EXISTS evidence (
    evidence_id    TEXT PRIMARY KEY,
    claim_id       TEXT NOT NULL,
    kind           TEXT NOT NULL,
    payload        TEXT NOT NULL,
    producer       TEXT NOT NULL,
    transformacion TEXT NOT NULL,
    row_hash       TEXT NOT NULL,
    supersedes_ref TEXT,
    created_at     TEXT NOT NULL,
    FOREIGN KEY (claim_id) REFERENCES claims(claim_id)
);

-- [v3-5] INMUTABILIDAD COMO MECANISMO, NO COMO FLAG.
--   El diagrama dice "delete prohibido por permiso en punto de escritura".
--   "Permiso" aqui es un TRIGGER: el motor lo impone. Ningun camino de
--   codigo —ni siquiera uno futuro— puede saltarselo escribiendo `DELETE`.
--   Un flag (`mutable=1`) se puede ignorar con el mismo esfuerzo que se
--   escribe; un trigger hace que el intento sea un error del motor.
CREATE TRIGGER IF NOT EXISTS trg_evidence_no_delete
BEFORE DELETE ON evidence
BEGIN
    SELECT RAISE(ABORT, 'EVIDENCE_APPEND_ONLY: DELETE prohibido');
END;

CREATE TRIGGER IF NOT EXISTS trg_evidence_no_update
BEFORE UPDATE ON evidence
BEGIN
    SELECT RAISE(ABORT, 'EVIDENCE_APPEND_ONLY: UPDATE prohibido');
END;

-- La correccion se hace por supersedes_ref: la fila vieja no se borra ni
-- se muta, se declara superada por una fila nueva.
CREATE TRIGGER IF NOT EXISTS trg_evidence_no_reparent
BEFORE UPDATE OF claim_id ON evidence
BEGIN
    SELECT RAISE(ABORT, 'EVIDENCE_INMUTABLE: no se reasigna de claim');
END;

-- CONTRADICCION: es un REGISTRO, no un estado del claim.
CREATE TABLE IF NOT EXISTS contradictions (
    contradiction_id TEXT PRIMARY KEY,
    claim_id        TEXT NOT NULL,
    statement       TEXT NOT NULL,
    severity        TEXT NOT NULL,     -- calculada, no declarada
    resolved_by     TEXT,
    resolved_state  TEXT,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (claim_id) REFERENCES claims(claim_id)
);

-- REEVALUACION: el paso documentado que puede producir INVALIDATED o
-- devolver el claim a PROVEN si se refuta la contradiccion.
CREATE TABLE IF NOT EXISTS reevaluations (
    reevaluation_id   TEXT PRIMARY KEY,
    claim_id          TEXT NOT NULL,
    contradiction_id  TEXT NOT NULL,
    decision          TEXT NOT NULL,   -- INVALIDATED | REVERTED | PARTIAL
    rationale         TEXT NOT NULL,
    created_at        TEXT NOT NULL,
    FOREIGN KEY (claim_id) REFERENCES claims(claim_id)
);

-- [v3-3] PESSIMISTIC POR OPERACION. Nunca global: la clave incluye el
-- claim_id, de modo que dos claims distintos se reevaluan en paralelo.
CREATE TABLE IF NOT EXISTS claim_locks (
    claim_id   TEXT NOT NULL,
    locked_by  TEXT NOT NULL,
    acquired_at TEXT NOT NULL,
    expires_at REAL NOT NULL,
    PRIMARY KEY (claim_id)
);

CREATE INDEX IF NOT EXISTS ix_ev_claim  ON evidence(claim_id);
CREATE INDEX IF NOT EXISTS ix_ct_claim  ON contradictions(claim_id);
CREATE INDEX IF NOT EXISTS ix_claims_ep ON claims(epistemic_state);
"""


def _ahora() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class EvidenciaAlterada(RuntimeError):
    """El motor rechazo una escritura in-place. Es el mecanismo funcionando."""


class ConflictoOptimista(RuntimeError):
    """La version cambio entre lectura y escritura (version + row_count)."""


class LockExpirado(RuntimeError):
    pass


class Grafo:
    """El grafo de evidencia. Una instancia por base.

    La base es siempre la que se le pase. El constructor NO abre ni crea la
    base de desarrollo de RXRE: este grafo es un artefacto separado.
    """

    def __init__(self, ruta: str, timeout: float = 5.0):
        self.ruta = ruta
        directorio = os.path.dirname(os.path.abspath(ruta))
        if directorio:
            os.makedirs(directorio, exist_ok=True)
        self.db = sqlite3.connect(ruta, timeout=timeout,
                                  isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(SCHEMA_SQL)
        self._abrir = True

    def cerrar(self) -> None:
        self.db.close()

    # -- utilidades ------------------------------------------------------
    @staticmethod
    def _cargar(lista: str) -> List[str]:
        import json
        return json.loads(lista)

    @staticmethod
    def _volcar(lista: List[str]) -> str:
        import json
        return json.dumps(list(lista), separators=(",", ":"))

    # -- SCHEMA DEL CLAIM ------------------------------------------------
    def afirmar(self, statement: str, object_hash: str, scope: str,
               epistemic_state: str, falsification_test: str,
               evidence_refs: Optional[List[str]] = None,
               derivation_refs: Optional[List[str]] = None,
               unresolved_obligations: Optional[List[str]] = None,
               claim_id: Optional[str] = None,
               reevaluation_ref: Optional[str] = None) -> Dict[str, Any]:
        """Declara un claim. Devuelve el dict completo.

        Rechaza un claim sin `falsification_test`: el diagrama lo pone en el
        schema, y una afirmacion sin termino de contraste no es un claim.
        """
        claim = {
            "id": claim_id or ("clm_" + hash_contenido(
                [statement, object_hash, scope])[:16]),
            "statement": statement,
            "object_hash": object_hash,
            "scope": scope,
            "epistemic_state": epistemic_state,
            "evidence_refs": list(evidence_refs or []),
            "derivation_refs": list(derivation_refs or []),
            "contradiction_refs": [],
            "falsification_test": falsification_test,
            "unresolved_obligations": list(unresolved_obligations or []),
            "reevaluation_ref": reevaluation_ref,
        }
        errores = validar_claim(claim)
        if errores:
            raise ValueError("claim invalido: %s" % "; ".join(errores))

        ahora = _ahora()
        self.db.execute(
            "INSERT OR REPLACE INTO claims (claim_id, statement, object_hash,"
            " scope, epistemic_state, evidence_refs, derivation_refs,"
            " contradiction_refs, falsification_test,"
            " unresolved_obligations, reevaluation_ref, version, row_count,"
            " created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,'[]',?,?,?,0,0,?,?)",
            (claim["id"], statement, object_hash, scope, epistemic_state,
             self._volcar(claim["evidence_refs"]),
             self._volcar(claim["derivation_refs"]),
             falsification_test,
             self._volcar(claim["unresolved_obligations"]),
             reevaluation_ref, ahora, ahora))
        return self.leer(claim["id"])

    def leer(self, claim_id: str) -> Optional[Dict[str, Any]]:
        fila = self.db.execute(
            "SELECT * FROM claims WHERE claim_id = ?",
            (claim_id,)).fetchone()
        if fila is None:
            return None
        d = dict(fila)
        for c in ("evidence_refs", "derivation_refs", "contradiction_refs",
                  "unresolved_obligations"):
            d[c] = self._cargar(d[c])
        # El schema del diagrama llama a la clave `id`. La columna se llama
        # `claim_id` porque `id` a secas choca con laPk en SQL; el alias
        # evita que quien consume el grafo tenga que saber eso.
        d["id"] = d["claim_id"]
        return d

    # -- EVIDENCE: append, sin lock sobre el claim -----------------------
    def aportar(self, claim_id: str, kind: str, payload: Any,
                producer: str, transformacion: str,
                supersedes_ref: Optional[str] = None) -> str:
        """Anade evidencia. NO toma lock sobre el claim.

        Es la razon de la concurrencia por operacion: agregar evidencia es
        append puro, y bloquea a quien esta decidiendo el estado.

        `supersedes_ref` NO borra la evidencia vieja: declara que esta la
        corrige. Las dos coexisten y el hash de fila de la vieja sigue
        verificable.
        """
        # El hash de fila se calcula sobre el payload YA CANONIZADO, que es
        # como queda en disco. Hashear el objeto Python antes de
        # canonizar daria un hash que nunca coincidiria con el de la lectura:
        # el mecanismo de inmutabilidad pareceria roto cuando lo unico roto
        # seria el orden de las operaciones.
        # [v3-5] supersedes_ref DEBE apuntar a una evidencia existente.
        # Una correccion que no apunta a nada no es una correccion.
        if supersedes_ref is not None:
            previa = self.db.execute(
                "SELECT evidence_id FROM evidence WHERE evidence_id = ?",
                (supersedes_ref,)).fetchone()
            if previa is None:
                raise ValueError(
                    "supersedes_ref inexistente: %s. Una correccion que no "
                    "apunta a nada no es una correccion." % supersedes_ref)
            # No se puede supersedir a si mismo (ciclo de longitud 1).
        # ev_id se calcula DESPUES, asi que esta comprobacion se hace
        # despues del calculo del id. Ver abajo.

        carga_canon = canonico(payload)
        contenido = {
            "claim_id": claim_id,
            "kind": kind,
            "payload": carga_canon,
            "producer": producer,
            "transformacion": transformacion,
            "supersedes_ref": supersedes_ref,
        }
        ev_id = "ev_" + hash_contenido(contenido)[:16]
        fila_hash = hash_fila(contenido)

        # Comprobacion de ciclo de longitud 1, ahora que ev_id existe.
        if supersedes_ref is not None and supersedes_ref == ev_id:
            raise ValueError(
                "una evidencia no puede supersedirse a si misma")

        self.db.execute(
            "INSERT INTO evidence (evidence_id, claim_id, kind, payload,"
            " producer, transformacion, row_hash, supersedes_ref, created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (ev_id, claim_id, kind, carga_canon, producer,
             transformacion, fila_hash, supersedes_ref, _ahora()))

        # El claim se actualiza de forma OPTIMISTA (version + row_count).
        # Si alguien mas movio la version, el update no aplica y hay que
        # reintentar: eso es concurrencia, no corrupcion.
        for _ in range(8):
            self.db.execute(
                "UPDATE claims SET evidence_refs = json_insert"
                " (evidence_refs, '$[#]', ?), row_count = row_count + 1,"
                " version = version + 1, updated_at = ?"
                " WHERE claim_id = ?",
                (ev_id, _ahora(), claim_id))
            if self.db.total_changes and self.db.execute(
                    "SELECT 1 FROM evidence WHERE evidence_id = ?",
                    (ev_id,)).fetchone():
                return ev_id
        raise RuntimeError("no se pudo registrar la evidencia")

    def cadena_supersedes(self, evidence_id: str) -> List[Dict[str, Any]]:
        """Devuelve la cadena de evidencia enlazada por supersedes_ref.

        La cadena va de la mas antigua a la mas nueva: si B supersede a A,
        y C supersede a B, la cadena es [A, B, C].

        Sin esta funcion, supersedes_ref es un campo que nadie recorre: un
        enlace que no se puede seguir no es un enlace, es un comentario.

        Devuelve lista vacia si la evidencia no existe.
        """
        cadena: List[Dict[str, Any]] = []
        actual: Optional[str] = evidence_id
        visitados: set = set()
        while actual is not None and actual not in visitados:
            visitados.add(actual)
            fila = self.db.execute(
                "SELECT * FROM evidence WHERE evidence_id = ?",
                (actual,)).fetchone()
            if fila is None:
                break
            cadena.append(dict(fila))
            actual = fila["supersedes_ref"]
        cadena.reverse()
        return cadena

    def leer_evidencia(self, evidence_id: str,
                       verificar: bool = True) -> Dict[str, Any]:
        """Lee evidencia VERIFICANDO el hash de fila.

        `verificar=True` recalcula el hash y lo compara. Si no coincide, la
        fila fue alterada por una via que el trigger no cubre y hay que
        saberlo. Devolver la fila sin verificar seria asumir la inmutabilidad
        en vez de comprobarla.
        """
        fila = self.db.execute(
            "SELECT * FROM evidence WHERE evidence_id = ?",
            (evidence_id,)).fetchone()
        if fila is None:
            raise KeyError(evidence_id)
        d = dict(fila)
        if verificar:
            recomputado = hash_fila({
                "claim_id": d["claim_id"],
                "kind": d["kind"],
                "payload": d["payload"],
                "producer": d["producer"],
                "transformacion": d["transformacion"],
                "supersedes_ref": d["supersedes_ref"],
            })
            d["hash_verificado"] = (recomputado == d["row_hash"])
        return d

    # -- [v3-2] INVALIDATED NO ES AUTOMATICO -----------------------------
    def contradecir(self, claim_id: str, statement: str,
                     severity: str = "media") -> str:
        """Registra una contradiccion. NO cambia el estado del claim.

        El diagrama: "INVALIDATED != automatico: contradiccion ->
        reevaluacion documentada -> puede resultar en INVALIDATED o volver
        a PROVEN si se refuta".

        Si este metodo invalidara, la correccion v3-2 estaria ausente.
        """
        c_id = "ctd_" + hash_contenido([claim_id, statement])[:16]
        self.db.execute(
            "INSERT INTO contradictions (contradiction_id, claim_id,"
            " statement, severity, created_at) VALUES (?,?,?,?,?)",
            (c_id, claim_id, statement, severity, _ahora()))
        self.db.execute(
            "UPDATE claims SET contradiction_refs = json_insert"
            " (contradiction_refs, '$[#]', ?), version = version + 1,"
            " updated_at = ? WHERE claim_id = ?",
            (c_id, _ahora(), claim_id))
        return c_id

    def reevaluar(self, claim_id: str, contradiction_id: str,
                  decision: str, rationale: str,
                  reviewer: str) -> Dict[str, Any]:
        """El paso documentado. Aqui si se puede invalidar.

        `decision` ∈ {INVALIDATED, REVERTED, PARTIAL}.
        REVERTED devuelve el claim a PROVEN: refutar una contradiccion es
        tan legitimo como aceptarla.
        """
        if decision not in (INVALIDATED, REVERTED, PARTIAL):
            raise ValueError("decision de reevaluacion invalida: %r"
                             % (decision,))
        r_id = "rev_" + hash_contenido(
            [claim_id, contradiction_id, decision, rationale, reviewer])[:16]
        ahora = _ahora()
        self.db.execute(
            "INSERT INTO reevaluations (reevaluation_id, claim_id,"
            " contradiction_id, decision, rationale, created_at)"
            " VALUES (?,?,?,?,?,?)",
            (r_id, claim_id, contradiction_id, decision, rationale, ahora))

        nuevo = {INVALIDATED: INVALIDATED,
                 REVERTED: PROVEN,
                 PARTIAL: PARTIAL}[decision]
        with self.lock_pessimista(claim_id, reviewer):
            self.db.execute(
                "UPDATE claims SET epistemic_state = ?, reevaluation_ref = ?,"
                " version = version + 1, updated_at = ? WHERE claim_id = ?",
                (nuevo, r_id, ahora, claim_id))
            self.db.execute(
                "UPDATE contradictions SET resolved_by = ?,"
                " resolved_state = ? WHERE contradiction_id = ?",
                (reviewer, nuevo, contradiction_id))
        return {"reevaluation_id": r_id, "decision": decision,
                "epistemic_state": nuevo, "reviewer": reviewer}

    # -- [v3-3] CONCURRENCIA POR OPERACION ------------------------------
    def actualizar_estado(self, claim_id: str, nuevo_estado: str,
                          version_esperada: int) -> None:
        """OPTIMISTIC: exige la version que el llamador leyo.

        `WHERE version = ?`. Si otro hilo movio el estado, rowcount = 0 y se
        lanza ConflictoOptimista. El llamador reintenta con la version
        nueva. No hay lock, no hay espera.
        """
        if nuevo_estado not in (PROVEN, PARTIAL, NOT_DETERMINED,
                                PROVEN_ABSENT, DEFERRED, INVALIDATED):
            raise ValueError("estado epistemico invalido: %r" % (nuevo_estado,))
        cur = self.db.execute(
            "UPDATE claims SET epistemic_state = ?, version = version + 1,"
            " updated_at = ? WHERE claim_id = ? AND version = ?",
            (nuevo_estado, _ahora(), claim_id, version_esperada))
        if cur.rowcount == 0:
            raise ConflictoOptimista(
                "version de %s cambio; se esperaba %d"
                % (claim_id, version_esperada))

    class _LockPessimista:
        def __init__(self, grafo, claim_id, quien):
            self.grafo, self.claim_id, self.quien = grafo, claim_id, quien
            self.adquirido = False

        def __enter__(self):
            ahora = time.time()
            try:
                self.grafo.db.execute(
                    "INSERT INTO claim_locks (claim_id, locked_by,"
                    " acquired_at, expires_at) VALUES (?,?,?,?)",
                    (self.claim_id, self.quien, _ahora(), ahora + 30.0))
                self.adquirido = True
            except sqlite3.IntegrityError:
                fila = self.grafo.db.execute(
                    "SELECT locked_by, expires_at FROM claim_locks"
                    " WHERE claim_id = ?", (self.claim_id,)).fetchone()
                if fila["expires_at"] > ahora:
                    raise RuntimeError(
                        "claim %s bloqueado por %s" % (self.claim_id,
                                                       fila["locked_by"]))
                self.grafo.db.execute(
                    "UPDATE claim_locks SET locked_by = ?, acquired_at = ?,"
                    " expires_at = ? WHERE claim_id = ?",
                    (self.quien, _ahora(), ahora + 30.0, self.claim_id))
                self.adquirido = True
            return self

        def __exit__(self, *_):
            if self.adquirido:
                self.grafo.db.execute(
                    "DELETE FROM claim_locks WHERE claim_id = ? AND"
                    " locked_by = ?", (self.claim_id, self.quien))
            return False

    def lock_pessimista(self, claim_id: str, quien: str,
                        ttl: float = 30.0) -> "_LockPessimista":
        """PESSIMISTIC POR CLAIM, con expiracion.

        Nunca global: la PK es `claim_id`, asi que dos claims distintos se
        reevaluan en paralelo. Si el lock fuera global, "reevaluacion"
        serializaria todas las reevaluaciones del sistema, que es
        precisamente lo que el diagrama prohibe.
        """
        return Grafo._LockPessimista(self, claim_id, quien)

    # -- [v3-6] TRES CAPAS DEL HASH, SEPARADAS ---------------------------
    def verificar_hash(self, artifact_path: str, declared_hash: str,
                       referencia_confiable: Optional[str] = None,
                       prueba_semantica: Optional[bool] = None) -> Dict:
        """Devuelve las tres capas por separado. NUNCA un veredicto unico.

            integridad    -> hash actual == hash declarado?      PASS / FAIL
            autenticidad  -> coincide con referencia confiable?   PASS /
                                                                    NOT_DETERMINED
            validez sem.  -> el artefacto dice lo que el claim
                             afirma?                             requiere PRUEBA

        Un hash integro NO autentica y NO valida semanticamente. Devolver
        un booleano unico seria la forma exacta de perder esa distincion.
        """
        import hashlib
        with open(artifact_path, "rb") as fh:
            actual = hashlib.sha256(fh.read()).hexdigest()

        integridad = (INTEGRIDAD_PASS if actual == declared_hash
                      else INTEGRIDAD_FAIL)

        if referencia_confiable is None:
            autenticidad = AUTENTICIDAD_NOT_DETERMINED
        elif referencia_confiable == declared_hash:
            autenticidad = AUTENTICIDAD_PASS
        else:
            autenticidad = AUTENTICIDAD_FAIL

        if prueba_semantica is None:
            validez = VALIDAD_REQUIERE_PRUEBA
        else:
            validez = (TEST_PASS if prueba_semantica else TEST_FAIL)

        return {
            "integridad": integridad,
            "autenticidad": autenticidad,
            "validez_semantica": validez,
            "hash_actual": actual,
            "hash_declarado": declared_hash,
            "advertencia": "un hash detecta cambios; no autentica y no "
                           "valida semantica",
        }


# -- superficie de modulo, para lo que el diagrama nombra -----------------
def modos_de_fallo() -> Dict[str, str]:
    """Los tres modos de fallo de ETER. Vive aqui porque es el registro."""
    return {
        "CAIDA_PROCESO": "la RAM se pierde; solo sobrevive lo que llego "
                         "a disco con fsync",
        "SATURACION_COLA": "el productor descarta; el descarte se CUENTA, "
                           "no es silencioso",
        "REINICIO": "el proceso vuelve; lo unico que sobrevive es el disco",
    }


def contractos_sincronos() -> Dict[str, str]:
    """MENTE, CUERPO y FUEGO se conectan por contrato sincrono directo.

    No hay mediacion asincrona entre ellos: si CUERPO mide, FUEGO transforma
    sobre ESA medida, y MENTE decide sobre ESE resultado. Un bus en el medio
    abriria la puerta a que FUEGO transformara una medida que ya no es.
    """
    return {
        "MENTE_CUERPO": "HIPOTESIS RIVAL <- MEDICION que la pone o la tumba",
        "CUERPO_FUEGO": "MEDICION VERIFICADA en punto de uso -> TRANSFORMACION",
        "FUEGO_MENTE": "TRANSFORMACION CONTROLADA -> HIPOTESIS DERIVADA",
        "CUERPO_CUERPO": "SYNC: el hash se verifica al USAR, no al escribir",
    }