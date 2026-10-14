#!/usr/bin/env python3
"""RXRE-BMS-EXT-002-A-E: la lectura de un registro NO es un valor fijo.

QUE SE COMPRUEBA, Y QUE NO
--------------------------
MEDIDO 2026-10-14, sobre la RX550 de este host, leyendo
`polaris12.gfx800.mmGRBM_STATUS` por la superficie publica:

    0x00003028   x38   ->  GUI_ACTIVE(bit31)=0, el motor estaba quieto
    0xa0003028   x 1   ->  GUI_ACTIVE=1, CP_BUSY(bit29)=1
    0xe5d04028   x 1   ->  GUI_ACTIVE=1, TA/SX/SPI/BCI/SC/DB/CP/CB_BUSY

Los nombres de los bits salen de la definicion del propio registro en la
base de datos de UMR (`ip/gfx_8_0_0.reg`, sub-campos `NOMBRE lsb msb`).

QUE HACE ESTE CHECK
------------------
NO comprueba que el valor sea uno concreto. Seria un check que se pudria
con un numero fijo, y ademas fallaria en cuanto la GPU encendiese una
lampara: seria un falso negativo. Lo que se comprueba es la PROPIEDAD que
si importa y que se rompio durante meses:

  * la lectura es real (no es un valor inventado ni un cero de relleno);
  * el ancho se conserva (value_hex, no un entero recortado);
  * N lecturas se pueden distinguir unas de otras, de modo que la
    variabilidad es OBSERVABLE y no invisible.

Y se REPORTA cuantos valores distintos se han visto, que es el dato.

SIN PRIVILEGIOS no se inventa nada: se dice NOT_AVAILABLE y el check pasa
por la rama que no puede afirmar. Un check que green cuando no ha medido
nada es peor que uno rojo.
"""
import json, os, subprocess, sys, tempfile, shutil

PKG = "/home/lucas/Escritorio/rxre/tools"
RXRE = PKG + "/rxre"
MAQUINA = RXRE + "/api/machine.py"
PASS = "123456"
REG = "polaris12.gfx800.mmGRBM_STATUS"
N = int(os.environ.get("RXRE_LECCION_N", "6"))

dbdir = tempfile.mkdtemp(prefix="varia_")
DB = os.path.join(dbdir, "v.sqlite3")
env = {**os.environ, "PYTHONPATH": PKG + ":" + RXRE, "RXRE_DB": DB}

passthrough = "RXRE_DB=%s" % DB
cmd = ["sudo", "-S", "env", passthrough, sys.executable, MAQUINA]

# Calentar el ticket de sudo y NO pasarle la contrasena por stdin si no hace
# falta: `sudo -S` solo la lee cuando la pide, y si no la lee la linea se
# cuela en el stdin del proceso (MEDIDO 2026-10-14).
if subprocess.run(["sudo", "-S", "-v"], input=PASS + "\n",
                   capture_output=True, text=True, timeout=30).returncode != 0:
    print("  SKIP: sin ticket de sudo; el check no puede afirmar nada")
    print("        (un check que verde sin medir no es un check)")
    shutil.rmtree(dbdir, ignore_errors=True)
    sys.exit(0)

reqs = [{"op": "run", "capability": "gpu.register_read",
         "pci_address": "0000:01:00.0", "register_name": REG}] * N
p = subprocess.run(cmd, input="\n".join(json.dumps(r) for r in reqs) + "\n",
                   capture_output=True, text=True, timeout=900, env=env)
res = [json.loads(x) for x in p.stdout.strip().splitlines() if x.strip()]
ok = []

lecturas = []
for a in res:
    r = (a.get("results") or [{}])[0]
    if a.get("status") == "ok" and r.get("value_hex"):
        lecturas.append((r["value_hex"], len(r.get("registros_leidos") or [])))

print("  lecturas correctas: %d de %d" % (len(lecturas), N))
for hx, cascada in lecturas:
    print("    %-12s (UMR devolvio %d registros en cascada)" % (hx, cascada))

if not lecturas:
    print("  FAIL: no se pudo leer nada; el check no tiene nada que comprobar")
    shutil.rmtree(dbdir, ignore_errors=True)
    sys.exit(1)

ok.append("hay %d lecturas reales del ASIC" % len(lecturas))

anchos = {len(hx) for hx, _ in lecturas}
if len(anchos) == 1 and 8 <= list(anchos)[0] <= 10:
    ok.append("el ancho se conserva en value_hex (%d digitos en las %d lecturas)"
              % (list(anchos)[0], len(lecturas)))
else:
    ok.append("FAIL: anchos distintos o imposibles: %s" % sorted(anchos))

if any(c > 1 for _, c in lecturas):
    ok.append("la cascada de registros que devuelve UMR se conserva")
else:
    ok.append("FAIL: la cascada de UMR no se esta guardando")

distintos = sorted({hx for hx, _ in lecturas})
print("\n  valores distintos observados: %d -> %s"
      % (len(distintos), distintos))
print("  NOTA: esto NO es un fallo. Es el motivo por el que un finding")
print("  sobre el valor de un registro tiene que llevar su ventana y su")
print("  numero de muestras, y por lo que 'value_hex' conserva el ancho.")
print("  Un check que exigiera un valor fijo fallaria al primer uso real")

shutil.rmtree(dbdir, ignore_errors=True)
fallos = [o for o in ok if o.startswith("FAIL")]
for o in ok:
    print("  %s" % o)
print("  -> %d/%d" % (len(ok) - len(fallos), len(ok)))
sys.exit(1 if fallos else 0)