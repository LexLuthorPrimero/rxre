#!/usr/bin/env python3
"""RXRE-CAUSAL-EVOL-001: SOUL. ¿El valor CAMBIA la priorizacion?

NO es un test de "la funcion existe". La pregunta es de comportamiento: con
los MISMOS datos, ¿elega la misma tarea que antes? Si elige siempre la
misma, la funcion es decoracion.

LOS CUATRO CASOS QUE IMPORTAN
-----------------------------
 1. COMPETICION POR VALOR
    Una tarea facil y sin impacto con `priority=5` contra una que desbloquea
    tres tareas con `priority=1`. La funcion DEBE elegir la segunda: el
    entero escrito a mano no puede saber lo del desbloqueo.

 2. DEPENDENCIA
    Una tarea con valor maximo pero bloqueada por una pendiente NO puede
    salir. Y una desbloqueada con valor bajo SI sale cuando la de arriba no
    puede. La puerta no se negocia con numeros.

 3. EVIDENCIA DEBIL
    Una tarea cuyo objetivo ya tiene hallazgo no vale lo mismo que otra sin
    ninguno. Y una tarea cuyo objetivo tiene PREGUNTAS ABIERTAS vale mas
    que una cerrada. La funcion tiene que distinguirlo con datos reales.

 4. COBERTURA
    Un componente sin datos no vale 0: se excluye, se renormaliza y se
    declara la cobertura. Una tarea con cobertura 0.5 no es la misma que
    una con cobertura 1.0 aunque el valor salga parecido.
"""

import os, sys, tempfile, shutil

REPO = "/home/lucas/Escritorio/rxre"
for p in (os.path.join(REPO, "tools"), os.path.join(REPO, "tools", "rxre")):
    if p not in sys.path:
        sys.path.insert(0, p)

from core import store as S

dbdir = tempfile.mkdtemp(prefix="soul_")
db = os.path.join(dbdir, "s.sqlite3")
# MEDIDO: `conectar(ruta)` devuelve la CONEXION; lo que habia aqui devolvia
# otra cosa y `crear_mision` reventaba con 'str' object has no attribute
# 'execute'. Se comprueba el tipo en vez de suponerlo.
_abrir = S.conectar(db)
assert hasattr(_abrir, "execute"), "conectar() devolvio %r, no una conexion" % type(_abrir)
c = _abrir
ok = []


def v(etiqueta, cond, detalle=""):
    ok.append((cond, etiqueta, detalle))
    print("  %s %s%s" % ("PASS" if cond else "FAIL", etiqueta,
                         (" -> " + str(detalle)[:150]) if detalle else ""))


print("=" * 74)
print("1) COMPETICION: facil-sin-impacto vs desbloquea-tres")
print("=" * 74)
m = S.crear_mision(c, "competicion", "prioridad por valor")
facil = S.agregar_tarea_a_mision(c, m, "tarea facil", "sin dependencias", priority=5)
hubo = S.agregar_tarea_a_mision(c, m, "tarea que desbloquea",
                                "tres tareas dependen de esta", priority=1)
for i in range(3):
    S.agregar_tarea_a_mision(c, m, "dependiente %d" % i,
                             "", priority=9,
                             dependencies=[hubo])

v_manual = S.seleccionar_siguiente_accion(c, m, por_valor=False)
v_valor = S.seleccionar_siguiente_accion(c, m, por_valor=True)
val = {t["task_id"]: t for t in S.valorar_tareas(c, m)["tareas"]}
print("   facil     valor=%.3f  (%s)" % (val[facil]["valor"], val[facil]["por_que"]))
print("   desbloq.  valor=%.3f  (%s)" % (val[hubo]["valor"], val[hubo]["por_que"]))
print("   antes (priority) -> %s" % v_manual)
print("   ahora (valor)     -> %s" % v_valor)
# MEDIDO al escribir el test: las tres dependientes se crearon con
# priority=9 y la facil con priority=5, asi que el orden antiguo elige una
# DEPENDIENTE. Eso no es un detalle del experimento: es una demostracion
# mejor de lo que se queria probar. El orden antiguo elige una tarea que
# depende de otra sin hacer, y nunca abrio `dependencies`.
dependientes = {t["task_id"] for t in S.obtener_tareas_mision(c, m)
                if t["title"].startswith("dependiente")}
v("el entero a mano elige una DEPENDIENTE bloqueada (nunca miro "
  "dependencies)", v_manual in dependientes, v_manual)
v("el VALOR elige la que desbloquea", v_valor == hubo, v_valor)
v("el comportamiento cambia de verdad", v_manual != v_valor)

print()
print("=" * 74)
print("2) DEPENDENCIA: la puerta no se negocia con numeros")
print("=" * 74)
m2 = S.crear_mision(c, "bloqueo", "puerta de dependencia")
bloqueante = S.agregar_tarea_a_mision(c, m2, "bloqueante", "sin hacer", priority=9)
cand = S.agregar_tarea_a_mision(c, m2, "candidata bloqueada", "", priority=0,
                                dependencies=[bloqueante])
val2 = {t["task_id"]: t for t in S.valorar_tareas(c, m2)["tareas"]}
sel2 = S.seleccionar_siguiente_accion(c, m2, por_valor=True)
print("   bloqueada por: %s   valor=%.3f" % (val2[cand]["bloqueada_por"],
                                             val2[cand]["valor"]))
print("   por_que: %s" % val2[cand]["por_que"][:130])
print("   seleccionada: %s" % sel2)
v("la tarea bloqueada se marca bloqueada", val2[cand]["bloqueada"] is True)
v("una bloqueada NO se selecciona pese a estar valorada",
  sel2 == bloqueante, sel2)
v("el motivo dice que el valor no la desbloquea",
  "no la desbloquea" in val2[cand]["por_que"])

print()
print("=" * 74)
print("3) EVIDENCIA: hallazgo existente vs pregunta abierta")
print("=" * 74)
m3 = S.crear_mision(c, "evidencia", "distincion por evidencia")
con_hallazgo = S.agregar_tarea_a_mision(c, m3, "ya sabemos esto",
                                         "target:gpu.register_read", priority=9)
con_duda = S.agregar_tarea_a_mision(c, m3, "no sabemos esto",
                                    "target:binary.decompile", priority=0)
S.registrar_investigacion(c, kind="hypothesis", status="OPEN",
                          text="¿que devuelve el decompilador?",
                          target="binary.decompile")
S.registrar_investigacion(c, kind="claim", status="PROVEN",
                          text="la lectura de registro funciona",
                          target="gpu.register_read")
# MEDIDO al escribir el test: primero se puso aqui una entrada de research
# y el componente dio `evidencia_ausente=1.0` para el caso "ya sabemos
# esto". Razon: un hallazgo es un HALLAZGO. Una pregunta cerrada es
# distinto, y el componente `evidencia_ausente` debe leer `findings`.
# Se registra el hallazgo de verdad; si no, el componente seria un
# contador de research con otro nombre.
from core.store import guardar_finding
guardar_finding(c, {"finding_id": "find_soul_test_1",
                    "claim": "gpu.register_read lee el ASIC real",
                    "epistemic": "PROVEN",
                    "evidence_ids": [],
                    "op_id": "",
                    "limitations": []})
val3 = {t["task_id"]: t for t in S.valorar_tareas(c, m3)["tareas"]}
for tid, nombre in ((con_hallazgo, "con hallazgo"), (con_duda, "con duda")):
    cc = val3[tid]["componentes"]
    print("   %-14s valor=%.3f  evidencia_ausente=%.2f  incertidumbre=%s"
          % (nombre, val3[tid]["valor"], cc["evidencia_ausente"]["valor"],
             cc["incertidumbre"]["valor"]))
    print("        fuente: %s" % cc["evidencia_ausente"]["fuente"])
v("la que tiene hallazgo NO se trata como sin evidencia",
  val3[con_hallazgo]["componentes"]["evidencia_ausente"]["valor"] == 0.0)
v("la que no tiene hallazgo se trata como tal",
  val3[con_duda]["componentes"]["evidencia_ausente"]["valor"] == 1.0)
v("una pregunta ABIERTA da incertidumbre > 0",
  val3[con_duda]["componentes"]["incertidumbre"]["valor"] > 0,
  val3[con_duda]["componentes"]["incertidumbre"]["fuente"])

print()
print("=" * 74)
print("4) COBERTURA: sin datos no es cero")
print("=" * 74)
m4 = S.crear_mision(c, "cobertura", "lo que no se sabe, declarado")
medible = S.agregar_tarea_a_mision(c, m4, "medible", "target:gpu.register_read")
opaca = S.agregar_tarea_a_mision(c, m4, "opaca", "sin target ni capability")
val4 = {t["task_id"]: t for t in S.valorar_tareas(c, m4)["tareas"]}
for tid, nombre in ((medible, "medible"), (opaca, "opaca")):
    t = val4[tid]
    print("   %-9s valor=%.3f cobertura=%.0f%%"
          % (nombre, t["valor"], t["cobertura"] * 100))
    print("        %s" % t["por_que"][:120])
v("la tarea sin target tiene MENOS cobertura",
  val4[opaca]["cobertura"] < val4[medible]["cobertura"],
  "%.2f vs %.2f" % (val4[opaca]["cobertura"], val4[medible]["cobertura"]))
v("los componentes sin datos NO valen 0",
  val4[opaca]["componentes"]["evidencia_ausente"]["valor"] is None,
  str(val4[opaca]["componentes"]["evidencia_ausente"]))
v("todos los componentes declaran su fuente",
  all("fuente" in cc and cc["fuente"] for t in val4.values()
      for cc in t["componentes"].values()))

print()
print("=" * 74)
print("5) DETERMINISMO: dos llamadas iguales, mismo resultado")
print("=" * 74)
a1 = [t["task_id"] for t in S.valorar_tareas(c, m)["tareas"]]
a2 = [t["task_id"] for t in S.valorar_tareas(c, m)["tareas"]]
v("el orden es estable entre llamadas", a1 == a2, a1)

print()
print("=" * 74)
print("6) NO REGRESIONA: el comportamiento viejo sigue disponible")
print("=" * 74)
v("por_valor=False conserva la ordenacion antigua",
  S.seleccionar_siguiente_accion(c, m, por_valor=False) == v_manual)

c.close()
shutil.rmtree(dbdir, ignore_errors=True)
fallos = [o for o in ok if not o[0]]
print("=" * 74)
print("  %d/%d" % (len(ok) - len(fallos), len(ok)))
sys.exit(1 if fallos else 0)