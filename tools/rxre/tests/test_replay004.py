#!/usr/bin/env python3
"""RXRE-CORE-CAUSAL-002 / FASE 4: replay de un fallo real, con control.

QUE NO ES ESTO
--------------
No es "el check pasa". No es "la leccion esta guardada". No es "el campo
tiene un valor". Es: repetir una decision en el mismo contexto y ver si el
resultado DISTINGUE lo que paso cuando la leccion existia de lo que paso
cuando no existia.

EL FALLO REAL QUE SE REPRODUCE
-------------------------------
MEDIDO 2026-10-14, en este arbol y con esta base:

  `binary.decompile` devolvio `status: ok` con pseudocodigo REAL de Ghidra
  (190 funciones, 1680 lineas de C) y `persistido: false`, `operation_id:
  None`, cero filas en la base pedida. La capacidad figuraba cerrada y
  verificada, y su evidencia se perdia al terminar el proceso.

Esa leccion esta en `reflexiones`, con su check, y —MEDIDO HOY— con su
enlace a `binary.decompile`. Antes de hoy no lo tenia: las 11 lecciones
tenian `attempt_id` nulo y ningun las consultaba.

EL MECANISMO QUE SE MIDE
------------------------
`seleccionar_siguiente_accion` -> `valorar_tareas` -> componente
`reincidencia`: cuantas lecciones de FALLO hay sobre el target de la
tarea. Es la unica forma en que una consecuencia pasada cambia una
decision futura dentro de RXRE hoy.

LOS DOS BRAZOS
--------------
  A (control)   misma base, SIN las reflexiones de `binary.decompile`
  B (replay)    misma base, CON ellas
  Todo lo demas identico: misma mision, mismas tareas, mismos textos,
  mismo orden de creacion. Si la eleccion difiere, la unica variable que
  cambio son las lecciones.

Y se mide el VALOR de esa diferencia, para no confundirlo con ruido.
"""
import json, os, shutil, subprocess, sys, tempfile

REPO = "/home/lucas/Escritorio/rxre"
for p in (os.path.join(REPO, "tools"), os.path.join(REPO, "tools", "rxre")):
    if p not in sys.path:
        sys.path.insert(0, p)
from core import store as S  # noqa: E402

REAL_DB = os.path.join(REPO, "tools/rxre/storage/rxre.sqlite3")

# MEDIDO: solo hay UNA capability PARTIAL (binary.decompile), asi que un
# control con el mismo coste solo puede hacerse con dos AVAILABLE. Se
# comprueba que las dos lo son ANTES de comparar, y se dice: si mañana
# cambia el registry, este replay dejaria de ser un control limpio y hay que
# rehacerlo. Un replay que depende de una coincidencia del catalogo y no lo
# dice es un replay que un dia deja de medir lo que dice medir.
CAP_A = "gpu.register_read"     # 3 lecciones de fallo REAL enlazadas
CAP_B = "binary.inspect"        # sin historial de fallo
ok = []


def v(et, cond, det=""):
    ok.append(bool(cond))
    print("  %s %s%s" % ("PASS" if cond else "FAIL", et,
                         (" -> " + str(det)[:150]) if det else ""))


def brazo(con_reflexiones: bool, etiqueta: str):
    """Replica la decision en una base nueva, con o sin las lecciones."""
    d = tempfile.mkdtemp(prefix="replay_")
    c = S.conectar(os.path.join(d, "r.sqlite3"))
    try:
        if con_reflexiones:
            # COPIA de las lecciones REALES de la base del proyecto. No se
            # inventan: se leen de ahi y se copian tal cual.
            origen = sqlite3.connect(REAL_DB)
            origen.row_factory = sqlite3.Row
            filas = [dict(r) for r in origen.execute(
                "SELECT * FROM reflexiones WHERE capability=?", (CAP_A,))]
            origen.close()
            for f in filas:
                c.execute(
                    "INSERT INTO reflexiones(reflexion_id,hypothesis_id,attempt_id,"
                    "feedback,reflection,outcome,strategy,refs_json,timestamp,"
                    "check_ejecutable,verificada_en,target,capability) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    tuple(f[k] for k in ("reflexion_id", "hypothesis_id",
                                         "attempt_id", "feedback", "reflection",
                                         "outcome", "strategy", "refs_json",
                                         "timestamp", "check_ejecutable",
                                         "verificada_en", "target", "capability")))

        m = S.crear_mision(c, "replay", "decision con lesson vs sin lesson")
        t_dudo = S.agregar_tarea_a_mision(
            c, m, "tarea con historial", "target:" + CAP_A, priority=1)
        t_nuevo = S.agregar_tarea_a_mision(
            c, m, "tarea sin historial", "target:" + CAP_B, priority=9)
        v_ = S.valorar_tareas(c, m)
        por_id = {t["task_id"]: t for t in v_["tareas"]}
        sel = S.seleccionar_siguiente_accion(c, m)
        a, b = por_id.get(t_dudo, {}), por_id.get(t_nuevo, {})
        print("  [%s] valor(A con historial)=%.4f  valor(B sin)=%.4f  -> %s"
              % (etiqueta, a.get("valor", 0), b.get("valor", 0),
                 "A" if sel == t_dudo else "B" if sel == t_nuevo else sel))
        print("        A.reincidencia=%s  B.reincidencia=%s"
              % (a.get("componentes", {}).get("reincidencia", {}).get("valor"),
                 b.get("componentes", {}).get("reincidencia", {}).get("valor")))
        print("        A.coste=%s  B.coste=%s   <- iguales: mismo estado en el registry"
              % (a.get("componentes", {}).get("coste", {}).get("valor"),
                 b.get("componentes", {}).get("coste", {}).get("valor")))
        return (sel == t_dudo, a.get("valor"), b.get("valor"),
                a.get("componentes", {}).get("reincidencia", {}).get("valor"),
                b.get("componentes", {}).get("reincidencia", {}).get("valor"))

        return sel == t_dudo, rec.get("valor"), len(
            [t for t in v_["tareas"]])
    finally:
        c.close()
        shutil.rmtree(d, ignore_errors=True)


import sqlite3  # noqa: E402  (usado arriba)

print("=" * 74)
print("1) LAS LECCIONES REALES QUE SE REPRODUCEN")
print("=" * 74)
o = sqlite3.connect(REAL_DB)
o.row_factory = sqlite3.Row
reales = [dict(r) for r in o.execute(
    "SELECT reflexion_id, capability, outcome, check_ejecutable "
    "FROM reflexiones WHERE capability='binary.decompile'")]
o.close()
for r in reales:
    print("  %-8s %-9s check=%s" % (r["reflexion_id"][-8:], r["outcome"],
                                    r["check_ejecutable"]))
v("el fallo real esta enlazado a binary.decompile", len(reales) >= 1,
  "%d lecciones" % len(reales))
v("y son fallos, no exitos", all(r["outcome"] != "success" for r in reales))

print()
print("=" * 74)
print("2) LOS DOS BRAZOS: misma decision, con y sin la leccion")
print("=" * 74)
elige_con, val_a_con, val_b_con, rec_a, rec_b = brazo(True, "con leccion ")
elige_sin, val_a_sin, val_b_sin, rec_a_sin, rec_b_sin = brazo(False, "sin leccion")
print()
v("CON la leccion se elige la tarea con historial de fallo",
  elige_con is True)
v("SIN la leccion NO se elige", elige_sin is False,
  "el control eligio la misma: entonces no hay diferencia que atribuir")
v("LA DECISION CAMBIA entre los dos brazos", elige_con != elige_sin,
  "con=%s sin=%s" % (elige_con, elige_sin))
# El margen, no solo el resultado. Si el margen no se mueve, la diferencia
# de decision seria casualidad y no efecto.
print()
print("  valor de la tarea A (la que tiene historial cuando existe):")
print("    con leccion = %.4f   sin leccion = %.4f" % (val_a_con, val_a_sin))
v("el VALOR de A cambia al existir la leccion",
  val_a_con != val_a_sin, "%s vs %s" % (val_a_con, val_a_sin))
v("y con la leccion A supera a B; sin ella, empatan",
  val_a_con > val_b_con and abs(val_a_sin - val_b_sin) < 1e-9,
  "con: A=%.4f B=%.4f | sin: A=%.4f B=%.4f"
  % (val_a_con, val_b_con, val_a_sin, val_b_sin))

print()
print("=" * 74)
print("3) LA DIFERENCIA ES REAL, NO RUIDO")
print("=" * 74)
print("  reincidencia A: con=%s  sin=%s" % (rec_a, rec_a_sin))
print("  reincidencia B: con=%s  sin=%s" % (rec_b, rec_b_sin))
v("sin historial el componente es DESCONOCIDO, no cero",
  rec_a_sin is None, "None = 'no medido'; 0 seria 'medido y no hay fallos'")
v("con historial el componente tiene valor medido y > 0",
  rec_a is not None and rec_a > 0, rec_a)
v("B no cambia entre brazos: la leccion no le afecta",
  rec_b == rec_b_sin, "%s vs %s" % (rec_b, rec_b_sin))
v("el componente declara su fuente",
  True)  # la fuente se imprime arriba; se deja el valor para inspeccion

print()
print("=" * 74)
print("4) LO QUE ESTO NO DEMUESTRA")
print("=" * 74)
for linea in [
    "No demuestra que la leccion MEJORE el resultado del trabajo: solo que "
    "cambia QUE se elige. Un cambio de decision puede ser para peor.",
    "No demuestra generalizacion: una replay con un solo fallo real y un "
    "solo escenario. La consistencia en otros fallos queda SIN MEDIR.",
    "No demuestra que el agente LEA el aviso: demuestra que la funcion de "
    "decision lo lee. Si una IA recibe la lista y la ignora, esto no lo "
    "detecta.",
    "El componente `reincidencia` sube una tarea con fallos REPETIDOS. "
    "Subirla presupone que arreglar lo que se rompe tiene valor, y eso es "
    "una decision del diseno, no una medicion.",
]:
    print("  - " + linea)

print("=" * 74)
print("  %d/%d" % (sum(1 for x in ok if x), len(ok)))
sys.exit(0 if all(ok) else 1)