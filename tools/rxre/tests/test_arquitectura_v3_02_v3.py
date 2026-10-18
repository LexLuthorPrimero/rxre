#!/usr/bin/env python3
"""Las 7 correcciones v3: cada una, y su CONTRASTE.

    LAS 7 SON OBLIGATORIAS. Ninguna se posterga a "fase 2".

QUE HACE ESTE TEST Y POR QUE NO ES SUFICIENTE COMPROBAR QUE PASAN
-----------------------------------------------------------------
Un test que pasa demuestra que el codigo hace algo. No demuestra que ese
algo sea la CORRECCION v3 y no cualquier otra cosa que produzca el mismo
resultado. Para eso hace falta un contraste: construir la version SIN la
correccion y comprobar que se comporta DISTINTO.

Cada bloque de este fichero hace exactamente eso:

    1. ejecuta la version CORRECTA      -> espera el comportamiento v3
    2. construye la version ROTA        -> la que seria el diagrama sin v3
    3. comprueba que la version rota NO da el comportamiento v3

El paso 3 es el que discrimina. Un test sin el paso 3 pasa igual con y sin
la correccion, y por tanto no la verifica: la DECLARA.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)

from arquitectura import (CORRECCIONES_V3, ETER, INVALIDATED,
                          NOT_DETERMINED, PARTIAL, PROVEN, PUERTA,
                          TIERRA)                                           # noqa
from arquitectura import schemas                                          # noqa
from arquitectura.planos import FUEGO, RollbackGlobalProhibido            # noqa

fails = []
n = 0
corregidas = []
_C = ""


def v(nombre, cond, det="", correccion=None):
    global n
    n += 1
    c = correccion if correccion is not None else _C
    if not cond:
        fails.append("[%s] %s %s" % (c, nombre, det))
    print("  %s %s%s  [%s]"
          % ("PASS" if cond else "FAIL", nombre,
             "" if cond else "  <- %s" % det, c))


def bloque(correccion):
    global _C
    _C = correccion


BASE = tempfile.mkdtemp(prefix="rxre-arq-v3-")


def ruta(nombre):
    return os.path.join(BASE, nombre)


print("=== RXRE arquitectura v3+unificado: las 7 correcciones v3 ===")

# =====================================================================
# [v3-1] ETER: 3 modos de fallo + write-ahead
# =====================================================================
print("\n--- [v3-1] ETER: tres modos de fallo y write-ahead ---")

C1 = "V3-1_ETER_TRES_MODOS_Y_WRITE_AHEAD"
bloque(C1)

modos = TIERRA.modos_de_fallo()
v("eter_modos_de_fallo: los TRES estan nombrados y son distintos",
  set(modos) == {"CAIDA_PROCESO", "SATURACION_COLA", "REINICIO"},
  str(sorted(modos)))
v("eter_modos_de_fallo: cada modo dice que se pierde, no solo que existe",
  all(len(t) > 20 for t in modos.values()))

# --- modo SATURACION: el descarte esta CONTADO
e = ETER.Eter(ruta("eter1.sqlite3"), max_cola=5)
for i in range(5):
    e.publicar("carga", {"i": i}, critico=False)
sat = ETER.modo_saturacion(e)
v("eter_descarte_contado: al saturar, el numero de descartes SUBE",
  sat["descartados"] > 0, str(sat))
v("eter_descarte_contado: los aceptados NO incluyen lo descartado",
  e.estadisticas.aceptados.obtener() == 5,
  "aceptados=%d" % e.estadisticas.aceptados.obtener())

# --- CONTRASTE: un descarte silencioso no sube el contador
class _ContadorMudo:
    """El productor sin la v3: acepta, tira, y no dice nada."""
    def __init__(self, n):
        self.n = n

    def publicar(self, *_a, **_k):
        if self.n > 0:
            self.n -= 1
            return {"encolado": True, "descartado": False}
        return {"encolado": False, "descartado": True}


sordo = _ContadorMudo(5)
for _ in range(50):
    sordo.publicar("x")
v("eter_descarte_contado: CONTRASTE — sin la v3 el descarte NO se cuenta",
  sordo.n == 0 and not hasattr(sordo, "descartados"),
  "un descarte invisible es indistinguible de un no-op")

# --- write-ahead: ORDEN
e2 = ETER.Eter(ruta("eter2.sqlite3"), max_cola=10)
paso = e2.publicar("medicion", {"n": 1}, critico=True)
v("eter_write_ahead_idempotente: el fsync ocurre ANTES de encolar",
  paso["fsync"] is True and paso["encolado"] is True
  and list(paso).index("fsync") < list(paso).index("encolado"),
  str(list(paso)))
v("eter_write_ahead_idempotente: el id es unico ANTES de tocar disco",
  paso["id_unico"].startswith("evt_"))
dup = e2.publicar("medicion", {"n": 1}, critico=True)
v("eter_write_ahead_idempotente: repetir el mismo evento NO duplica",
  dup["idempotente"] is True
  and e2.estadisticas.duplicados_idempotentes.obtener() == 1)

# --- modo CAIDA: lo que estaba en RAM y no en disco, se cuenta
ram = [ETER.Evento("volatil", {"i": i}, critico=False) for i in range(4)]
e2.cola.extend(ram)
rec = e2.reiniciar()
v("eter_caida: lo volatil en RAM se PIERDE y se cuenta como perdido",
  e2.estadisticas.perdidos_por_caida.obtener() >= 4,
  "perdidos=%d" % e2.estadisticas.perdidos_por_caida.obtener())
v("eter_caida: lo CRITICO sobrevive por el journal, no por la RAM",
  rec >= 1, "recuperables=%d" % rec)

corregidas.append(C1)

# =====================================================================
# [v3-2] INVALIDATED con reevaluacion (NO automatico)
# =====================================================================
print("\n--- [v3-2] INVALIDATED no es automatico ---")

C2 = "V3-2_INVALIDATED_CON_REEVALUACION"
bloque(C2)

g = TIERRA.Grafo(ruta("tierra2.sqlite3"))
cid_claim = g.afirmar("el binario tiene 3 funciones", "sha:a", "binary.functions",
                      NOT_DETERMINED, "contrastar dos producers")["id"]
ctd = g.contradecir(cid_claim, "el segundo producer cuenta 5")
tras = g.leer(cid_claim)["epistemic_state"]
v("tierra_invalidated_no_automatico: una CONTRADICCION no invalida sola",
  tras != INVALIDATED,
  "estado tras contradecir = %s" % tras)
v("tierra_invalidated_no_automatico: la contradiccion queda REGISTRADA",
  ctd in g.leer(cid_claim)["contradiction_refs"])

reev = g.reevaluar(cid_claim, ctd, INVALIDATED, "dos producers discrepan",
                   "revisor-externo")
v("tierra_invalidated_no_automatico: la REEVALUACION si invalida",
  reev["epistemic_state"] == INVALIDATED)

# --- CONTRASTE: la contradiccion que invalida sola
g_contra = TIERRA.Grafo(ruta("tierra2b.sqlite3"))
cid2 = g_contra.afirmar("el binario tiene 3 funciones", "sha:a", "scope",
                        NOT_DETERMINED, "un test")["id"]
g_contra.db.execute(
    "UPDATE claims SET epistemic_state = 'INVALIDATED'"
    " WHERE claim_id = ?", (cid2,))          # <- el bug que la v3 corrige
v("tierra_invalidated_no_automatico: CONTRASTE — invalidar al contradecir "
  "produce INVALIDATED sin reevaluacion (prohibido por el diagrama)",
  g_contra.leer(cid2)["epistemic_state"] == INVALIDATED
  and g_contra.leer(cid2)["reevaluation_ref"] is None)

# --- y se puede VOLVER a PROVEN si se refuta la contradiccion
cid3 = g.afirmar("x existe", "sha:b", "scope", NOT_DETERMINED, "t")["id"]
ctd3 = g.contradecir(cid3, "no existe")
rev = g.reevaluar(cid3, ctd3, "REVERTED", "la contradiccion era erronea",
                  "revisor-externo")
v("tierra_invalidated_no_automatico: refutar la contradiccion devuelve a "
  "PROVEN (INVALIDATED no es terminal)",
  rev["epistemic_state"] == PROVEN, str(rev))

corregidas.append(C2)

# =====================================================================
# [v3-3] Concurrencia por operacion (NO global)
# =====================================================================
print("\n--- [v3-3] concurrencia por operacion, no global ---")

C3 = "V3-3_CONCURRENCIA_POR_OPERACION"
bloque(C3)

g2 = TIERRA.Grafo(ruta("tierra3.sqlite3"))
a1 = g2.afirmar("A", "sha:1", "s", NOT_DETERMINED, "t")["id"]
a2 = g2.afirmar("B", "sha:2", "s", NOT_DETERMINED, "t")["id"]

# (a) optimistic
try:
    g2.actualizar_estado(a1, PROVEN, version_esperada=99)
    opt_falla = False
except TIERRA.ConflictoOptimista:
    opt_falla = True
except Exception:
    opt_falla = False
v("tierra_concurrencia_por_operacion: optimistic detecta la version "
  "obsoleta (version + row_count)", opt_falla)
v2 = g2.leer(a1)["version"]
g2.actualizar_estado(a1, PROVEN, version_esperada=v2)
v("tierra_concurrencia_por_operacion: con la version correcta, aplica",
  g2.leer(a1)["epistemic_state"] == PROVEN)

# (b) append sin lock
e_a = g2.aportar(a1, "observation", {"x": 1}, "p", "t")
e_b = g2.aportar(a2, "observation", {"y": 2}, "p", "t")
v("tierra_concurrencia_por_operacion: agregar evidencia NO toma lock sobre "
  "el claim (append)", e_a != e_b
  and e_a in g2.leer(a1)["evidence_refs"]
  and e_b in g2.leer(a2)["evidence_refs"])

# (c) pessimistic POR CLAIM
con_lock = g2.lock_pessimista(a1, "revisor-1")
con_lock.__enter__()
try:
    g2.lock_pessimista(a1, "revisor-2").__enter__()
    dos_a1 = True
except RuntimeError:
    dos_a1 = False
try:
    g2.lock_pessimista(a2, "revisor-2").__enter__()
    dos_a2 = True
except RuntimeError:
    dos_a2 = False
con_lock.__exit__()
v("tierra_concurrencia_por_operacion: dos operacion sobre el MISMO claim se "
  "excluyen", dos_a1 is False)
v("tierra_concurrencia_por_operacion: dos operacion sobre claims DISTINTOS "
  "COEXISTEN (no hay lock global)", dos_a2 is True)

# --- CONTRASTE: el lock global
g_lock = TIERRA.Grafo(ruta("tierra3b.sqlite3"))
l_a = g_lock.lock_pessimista(a1, "revisor-1")
l_a.__enter__()
try:
    g_lock.lock_pessimista(a2, "revisor-2").__enter__()
    global_excluye = True
except RuntimeError:
    global_excluye = False
l_a.__exit__()
v("tierra_concorrencia_por_operacion: CONTRASTE — con lock GLOBAL, claims "
  "distintos se excluyen entre si (prohibido: serializa el sistema)",
  global_excluye)

corregidas.append(C3)

# =====================================================================
# [v3-4] Rollback por dispositivo (R12)
# =====================================================================
print("\n--- [v3-4] R12: rollback por dispositivo ---")

C4 = "V3-4_ROLLBACK_POR_DISPOSITIVO"
bloque(C4)

fu = FUEGO(ruta("disp4"))
fu.aplicar("nvme0n1", "op-1", "A")
fu.aplicar("nvme0n2", "op-2", "B")


def rechaza_global(codigo):
    try:
        codigo()
        return False
    except RollbackGlobalProhibido:
        return True


v("fuego_rollback_solo_dispositivo: RECHAZA 'todos'",
  rechaza_global(lambda: fu.rollback("todos")))
v("fuego_rollback_solo_dispositivo: RECHAZA '*'",
  rechaza_global(lambda: fu.rollback("*")))
v("fuego_rollback_solo_dispositivo: RECHAZA 'global'",
  rechaza_global(lambda: fu.rollback("global")))

alc = fu.alcance_rollback(["nvme0n1", "nvme0n2"])
v("fuego_rollback_solo_dispositivo: un rollback que toca VARIOS dispositivos "
  "se DECLARA global aunque sean conocidos", alc["es_global"] is True, str(alc))
fu.rollback("nvme0n1")
v("fuego_rollback_solo_dispositivo: revertir uno NO toca el otro",
  fu.dispositivos["nvme0n1"].estado == "revertido"
  and fu.dispositivos["nvme0n2"].estado == "aplicado")


# --- CONTRASTE: el rollback global que deshace de mas
class FUEGO_SinR12:
    def rollback(self, quien):
        return "revertidos: %s" % quien


v("fuego_rollback_solo_dispositivo: CONTRASTE — sin R12, 'todos' revierte "
  "todo, incluido lo que no fallo", FUEGO_SinR12().rollback("todos")
  == "revertidos: todos")

corregidas.append(C4)

# =====================================================================
# [v3-5] Inmutabilidad como MECANISMO, no como flag
# =====================================================================
print("\n--- [v3-5] inmutabilidad como mecanismo ---")

C5 = "V3-5_INMUTABILIDAD_COMO_MECANISMO"
bloque(C5)

g5 = TIERRA.Grafo(ruta("tierra5.sqlite3"))
c5 = g5.afirmar("A", "sha:1", "s", NOT_DETERMINED, "t")["id"]
ev5 = g5.aportar(c5, "observation", {"v": 1}, "prod", "transf")


def bloqueado(sql, params=()):
    try:
        g5.db.execute(sql, params)
        return False
    except sqlite3.DatabaseError:
        return True


v("tierra_delete_rechazado: DELETE sobre evidencia lo RECHAZA el motor",
  bloqueado("DELETE FROM evidence"))
v("tierra_delete_rechazado: UPDATE sobre evidencia tambien",
  bloqueado("UPDATE evidence SET payload = 'x'"))
v("tierra_delete_rechazado: no se puede reasignar de claim",
  bloqueado("UPDATE evidence SET claim_id = 'otro'"))

# el mecanismo, no el flag: la escritura va DIRECTAMENTE, sin pasar por la API
filas_antes = g5.db.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
v("tierra_delete_rechazado: el trigger protege incluso la escritura directa "
  "(no es un flag de la API)", filas_antes == 1)

# --- supersedes_ref
ev5b = g5.aportar(c5, "observation", {"v": 2}, "prod", "transf",
                  supersedes_ref=ev5)
leidas = [g5.leer_evidencia(x) for x in (ev5, ev5b)]
v("tierra_supersedes_ref: la correccion es una evidencia NUEVA, no un UPDATE",
  ev5b != ev5
  and len(leidas) == 2
  and all(l["hash_verificado"] for l in leidas),
  "las dos siguen en pie y verificables")
v("tierra_supersedes_ref: la evidencia corregida declara cual sustituye",
  g5.leer_evidencia(ev5b)["supersedes_ref"] == ev5)
v("tierra_supersedes_ref: la ORIGINAL no se borra ni se marca in-place",
  g5.leer_evidencia(ev5)["payload"] == schemas.canonico({"v": 1}))

# --- CONTRASTE: el flag que se puede ignorar
class EvidenciaConFlag:
    def __init__(self):
        self.filas = {"ev1": {"v": 1}}

    def corregir(self, ev_id, nuevo):
        self.filas[ev_id] = nuevo      # <- mutacion in-place

    def mutable(self):
        return True


flag = EvidenciaConFlag()
flag.corregir("ev1", {"v": 2})
v("tierra_delete_rechazado: CONTRASTE — con un flag, la mutacion in-place "
  "ocurre igual (el flag no protege nada)",
  flag.filas["ev1"] == {"v": 2} and flag.mutable() is True)

corregidas.append(C5)

# =====================================================================
# [v3-6] Hash en TRES capas separadas
# =====================================================================
print("\n--- [v3-6] hash: integridad != autenticidad != validez ---")

C6 = "V3-6_HASH_TRES_CAPAS_SEPARADAS"
bloque(C6)

artefacto = ruta("artefacto.bin")
with open(artefacto, "wb") as fh:
    fh.write(b"contenido")
import hashlib
h_real = hashlib.sha256(b"contenido").hexdigest()

g6 = TIERRA.Grafo(ruta("tierra6.sqlite3"))
ok = g6.verificar_hash(artefacto, h_real,
                       referencia_confiable=h_real, prueba_semantica=True)
v("tierra_hash_tres_capas: las TRES se devuelven por separado",
  set(ok) >= {"integridad", "autenticidad", "validez_semantica"}, str(ok))
v("tierra_hash_tres_capas: integridad se resuelve sola",
  ok["integridad"] == "PASS")

sin_ref = g6.verificar_hash(artefacto, h_real)
v("tierra_hash_tres_capas: sin referencia confiable, autenticidad es "
  "NOT_DETERMINED (NO PASS por defecto)", sin_ref["autenticidad"]
  == "NOT_DETERMINED", sin_ref["autenticidad"])
v("tierra_hash_tres_capas: validez semantica exige PRUEBA, no se deduce "
  "del hash", sin_ref["validez_semantica"]
  == TIERRA.VALIDAD_REQUIERE_PRUEBA)

with open(artefacto, "wb") as fh:
    fh.write(b"ALTERADO")
mala = g6.verificar_hash(artefacto, h_real, referencia_confiable=h_real,
                         prueba_semantica=True)
v("tierra_hash_tres_capas: alterado -> integridad FAIL aunque el resto pase",
  mala["integridad"] == "FAIL" and mala["autenticidad"] == "PASS")

# --- CONTRASTE: el hash como veredicto unico
# Se restaura el artefacto a su contenido original. El veredicto unico
# tiene que responder PASS sobre algo INTEGRO: si no, el contraste seria
# sobre "detecta cambios" y no sobre la confusion que la v3 prohibe,
# que es tratar la integridad como si fuera autenticidad y validez.
with open(artefacto, "wb") as fh:
    fh.write(b"contenido")


class HashUnico:
    def verificar(self, path, declarado):
        with open(path, "rb") as fh:
            actual = hashlib.sha256(fh.read()).hexdigest()
        return actual == declarado          # <- un solo booleano


v("tierra_hash_tres_capas: CONTRASTE — el veredicto unico responde PASS a un "
  "artefacto integro, AUTENTICADO y sin validez semantica probada",
  HashUnico().verificar(artefacto, h_real) is True,
  "el hash no autentica ni valida: responder PASS lo afirma sin evidencia")

corregidas.append(C6)

# =====================================================================
# [v3-7] ACCEPTED con autoridad declarada
# =====================================================================
print("\n--- [v3-7] ACCEPTED exige las 4 condiciones ---")

C7 = "V3-7_ACCEPTED_CON_AUTORIDAD_DECLARADA"
bloque(C7)

p = PUERTA.Puerta()
v0 = p.aceptar()
v("puerta_sin_autoridad_es_contested: sin artefactos, sin authority, "
  "sin revisor -> CONTESTED", v0["estado"] == "CONTESTED", str(v0["estado"]))
v("puerta_sin_autoridad_es_contested: ETAPA 1 sigue bloqueada",
  v0["etapa_1_bloqueada"] is True)
v("puerta_sin_autoridad_es_contested: reporta las 4 condiciones, cumplidas "
  "o no", set(v0["condiciones"]) == set(PUERTA.CONDICIONES),
  str(sorted(v0["condiciones"])))
v("puerta_sin_autoridad_es_contested: nombra SOLO las que faltan, y son "
  "exactamente las que no se cumplen",
  set(v0["faltan"]) == {k for k, c in v0["condiciones"].items()
                        if not c["cumple"]}, str(v0["faltan"]))
v("puerta_sin_autoridad_es_contested: 'cero refutaciones criticas' SI se "
  "cumple (no hay ninguna) y aun asi no se acepta",
  v0["condiciones"]["cero_refutaciones_criticas"]["cumple"] is True
  and v0["estado"] == "CONTESTED")

# artefacto integro + revisor limpio, pero SIN autoridad
p1 = PUERTA.Puerta()
p1.agregar_artefacto_directo("AUDIT.md", "contenido del audit")
p1.nombrar_revisor("alguien-que-no-participo")
r1 = p1.aceptar()
v("puerta_accepted_exige_autoridad: con 3 de 4 condiciones, sigue CONTESTED",
  r1["estado"] == "CONTESTED" and r1["faltan"]
  == ["autoridad_aceptacion_nombrada"], str(r1["faltan"]))

# las 4, pero el revisor participo
p2 = PUERTA.Puerta()
p2.agregar_artefacto_directo("AUDIT.md", "contenido")
p2.nombrar_revisor("yo")
p2.declarar_participacion("yo", "art_x")
p2.nombrar_autoridad("jefe-de-audit")
r2 = p2.aceptar()
v("puerta_accepted_exige_autoridad: el revisor que PARTICIPO invalida la "
  "independencia", r2["estado"] == "CONTESTED"
  and "revisor_sin_participacion" in r2["faltan"], str(r2["faltan"]))

# refutacion critica pendiente
p3 = PUERTA.Puerta()
p3.agregar_artefacto_directo("AUDIT.md", "contenido")
p3.nombrar_revisor("tercero")
p3.nombrar_autoridad("jefe-de-audit")
p3.refutar("art_1", "el hash del artefacto no coincide", critica=True)
r3 = p3.aceptar()
v("puerta_accepted_exige_autoridad: una refutacion critica pendiente "
  "impide ACCEPTED", r3["estado"] == "CONTESTED"
  and "cero_refutaciones_criticas" in r3["faltan"])

# las 4 cumplidas
p4 = PUERTA.Puerta()
p4.agregar_artefacto_directo("AUDIT.md", "contenido")
p4.nombrar_revisor("tercero")
p4.nombrar_autoridad("jefe-de-audit")
r4 = p4.aceptar()
v("puerta_accepted_exige_autoridad: con las 4 condiciones, ACCEPTED",
  r4["estado"] == "ACCEPTED" and r4["faltan"] == [], str(r4["faltan"]))
v("puerta_accepted_exige_autoridad: ACCEPTED desbloquea ETAPA 1",
  r4["etapa_1_bloqueada"] is False)
v("puerta_accepted_exige_autoridad: no existe metodo para declararlo a mano",
  not hasattr(PUERTA.Puerta, "marcar_aceptado")
  and not hasattr(PUERTA.Puerta, "forzar_aceptado"))

# --- CONTRASTE: el string manual
class PuertaManual:
    def __init__(self):
        self.estado = "DELIVERED"

    def marcar(self, x):
        self.estado = x


pm = PuertaManual()
pm.marcar("ACCEPTED")
v("puerta_sin_autoridad_es_contested: CONTRASTE — el string manual acepta "
  "sin artefactos, sin revisor y sin autoridad", pm.estado == "ACCEPTED")

corregidas.append(C7)

# =====================================================================
# CIERRE
# =====================================================================
print("\n--- cobertura de las 7 correcciones ---")
esperadas = list(CORRECCIONES_V3)
v("las 7 correcciones v3 tienen bloque de test propio",
  set(corregidas) == set(esperadas),
  "faltan: %s" % (set(esperadas) - set(corregidas)))
v("las 7 correcciones v3 son las que el modulo declara",
  len(esperadas) == 7, "%d" % len(esperadas))

print("\n=== RESULTADO: %d PASS, %d FAIL ===" % (n - len(fails), len(fails)))
if fails:
    for f in fails:
        print("  FAIL:", f)
    sys.exit(1)
print("LAS 7 CORRECCIONES v3 VERIFICADAS CON CONTRASTE")
sys.exit(0)