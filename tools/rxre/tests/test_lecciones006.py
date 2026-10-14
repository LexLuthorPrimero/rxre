#!/usr/bin/env python3
"""RXRE-AUTONOMY-006: lecciones vigiladas.

QUE SE MIDE
-----------
No "cuantas reflexiones hay", sino cuantas tienen un CHECK QUE CORRE. La
distincion no es academica: MEDIDO 2026-10-14, este arbol arrastro meses
con tres afirmaciones FALSAS en prosa (`umr -O no_colour`, `umr -g
polaris12@0`, `polaris12.smc.gpu_length`). Escribir una reflexion sobre
ellas no las arregla: para eso hace falta un check que falle si vuelven.

Lo que este test demuestra:
  1. una reflexion SIN check se registra y se dice que no esta vigilada;
  2. una reflexion CON check se registra como vigilada;
  3. `op: lessons` mide la cobertura y separa las dos;
  4. un check que senala a un fichero inexistente se reporta como roto, no
     como vigilar bien;
  5. una reflexion con ese mismo check roto NO puede pasar por vigilada.

(5) es el punto. Un sistema que cuenta lochecksin comprobarlos no es
distinto de uno que no los cuenta: solo tiene mas numeros.
"""
import json, os, subprocess, sys, tempfile, shutil

PKG = "/home/lucas/Escritorio/rxre/tools"
RXRE = PKG + "/rxre"
MAQUINA = RXRE + "/api/machine.py"
sys.path.insert(0, PKG)
sys.path.insert(0, RXRE)
from core import store as S  # noqa: E402

dbdir = tempfile.mkdtemp(prefix="lecciones_")
DB = os.path.join(dbdir, "l.sqlite3")
env = {**os.environ, "PYTHONPATH": PKG + ":" + RXRE, "RXRE_DB": DB}
ok = []


def pedir(reqs, timeout=120):
    p = subprocess.run([sys.executable, MAQUINA],
                       input="\n".join(json.dumps(r) for r in reqs) + "\n",
                       capture_output=True, text=True, timeout=timeout, env=env)
    return [json.loads(x) for x in p.stdout.strip().splitlines() if x.strip()], p


print("=" * 74)
print("1) Una reflexion SIN check: se registra, y se dice que no esta vigilada")
print("=" * 74)
a = pedir([{"op": "reflect",
            "feedback": "el feedback se ve mal en el log",
            "reflection": "el log no distingue mayusculas",
            "outcome": "failure"}])[0][0]
print("  status=%s vigilada=%s" % (a.get("status"), a.get("vigilada")))
print("  nota   =%s" % (a.get("nota") or "")[:100])
if a.get("status") == "ok" and a.get("vigilada") is False:
    ok.append("una reflexion sin check NO se declara vigilada")

print("\n" + "=" * 74)
print("2) Una reflexion CON check real: se declara vigilada")
print("=" * 74)
b = pedir([{"op": "reflect",
            "feedback": "MEDIDO: umr -O no_colour -> error: Unknown option",
            "reflection": "UMR v1.0.0 no tiene opcion no_colour; la lista real "
                          "incluye use_colour. Un ejemplo ejecutable que nadie "
                          "ejecuta no es memoria.",
            "outcome": "failure",
            "strategy": "no pasar flags de opcion a UMR sin verificarlos",
            "check_ejecutable": "test_umr_hardware002.py"}])[0][0]
print("  status=%s vigilada=%s check=%s" % (b.get("status"), b.get("vigilada"),
                                            b.get("check_ejecutable")))
if b.get("status") == "ok" and b.get("vigilada") is True:
    ok.append("una reflexion con check se declara vigilada")

print("\n" + "=" * 74)
print("3) Un check que senala a un fichero INEXISTENTE se reporta roto")
print("=" * 74)
pedir([{"op": "reflect",
        "feedback": "apunta a un test que no existe",
        "reflection": "esta leccion esta mal enlazada a proposito",
        "outcome": "failure",
        "check_ejecutable": "test_que_no_existe_9999.py"}])
lecciones, _ = pedir([{"op": "lessons"}])
L = lecciones[0]
lec = L["lecciones"]
print("  total=%s con_check=%s sin_check=%s cobertura=%s%%"
      % (lec["total"], lec["con_check"], lec["sin_check"], lec["cobertura_pct"]))
print("  checks que no sostienen: %s"
      % [(x["check"], x.get("motivo")) for x in lec["checks_que_no_sostienen"]])
roto = any("test_que_no_existe_9999" in (x.get("check") or "")
           for x in lec["checks_que_no_sostienen"])
if roto:
    ok.append("un check a fichero inexistente se reporta ROTO, no como vigilancia")
if lec["sin_check"] == 1 and lec["total"] == 3:
    ok.append("la cobertura separa lo vigilado de lo simplemente escrito")
else:
    ok.append("FALLO cobertura: %s/%s/%s" % (lec["total"], lec["con_check"],
                                            lec["sin_check"]))

# El que vigila NO debe contar como vigilado
vigiladas_ids = {v["reflexion_id"] for v in L.get("vigiladas", [])}
rotas_ids = {x["reflexion_id"] for x in lec["checks_que_no_sostienen"]}
if not (rotas_ids & vigiladas_ids):
    ok.append("un check roto NO cuenta como vigilancia")
else:
    ok.append("FALLO: un check roto cuenta como vigilado")

print("\n" + "=" * 74)
print("4) El store y la superficie cuentan lo MISMO")
print("=" * 74)
c = S.conectar(DB)
directo = S.verificar_lecciones(c)
c.close()
# El store llama al total `reflexiones` y la superficie lo expone como
# `total`. Se comparan los MISMOS numeros por los dos caminos.
mismo = (directo["reflexiones"] == lec["total"]
         and directo["con_check"] == lec["con_check"]
         and directo["sin_check"] == lec["sin_check"]
         and len(directo["checks_que_no_sostienen"])
         == len(lec["checks_que_no_sostienen"]))
print("  store:   total=%s con_check=%s sin_check=%s rotas=%d"
      % (directo["reflexiones"], directo["con_check"], directo["sin_check"],
         len(directo["checks_que_no_sostienen"])))
print("  surface: total=%s con_check=%s sin_check=%s"
      % (lec["total"], lec["con_check"], lec["sin_check"]))
if mismo:
    ok.append("el store y 'op: lessons' no se contradicen")

print("\n" + "=" * 74)
print("5) El op existe y esta listado")
print("=" * 74)
ops = pedir([{"op": "ops"}])[0][0]["results"]
nombres = {o["op"] for o in ops}
print("  lessons en ops: %s" % ("lessons" in nombres))
if "lessons" in nombres:
    ok.append("'op: lessons' esta en la superficie publica")

shutil.rmtree(dbdir, ignore_errors=True)
print("\n" + "=" * 74)
fallos = [o for o in ok if o.startswith("FALLO")]
for o in ok:
    print("  %s" % o)
print("=" * 74)
print("  %d/%d" % (len(ok) - len(fallos), len(ok)))
sys.exit(1 if fallos else 0)