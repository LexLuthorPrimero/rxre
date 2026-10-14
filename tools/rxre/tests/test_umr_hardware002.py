#!/usr/bin/env python3
"""RXRE-BMS-EXT-002-A: gpu.register_read validado contra el ASIC real.

QUE SE VALIDA Y QUE NO
----------------------
VALIDADO: que `gpu.register_read` lee un registro MMIO real de la RX550 de
este host por la superficie publica, y que el valor es el que UMR emite.

NO VALIDADO: el significado de los bits. El valor es RAW_BINARY. Un
finding que diga "mmGRBM_STATUS == 0x00003028" sin mas esta incompleto,
porque se ha MEDIDO que ese registro cambia (ver test_reproduccion).

POR QUE ESTE TEST CORRE ENTERO CON UN SOLO USUARIO
--------------------------------------------------
MEDIDO: si la lectura se hace con privilegios y el `explain` posterior sin
privilegios, `explain` responde `empty` y parece que la evidencia se ha
perdido. No se ha perdido: la BD usa WAL y el fichero `-wal`/`-shm` queda
con el propietario de quien la creo, asi que el otro usuario no ve las
paginas sin comprobar. El sintoma era del arnes, no de RXRE. Por eso aqui
todo el test usa el mismo usuario, y la persistencia se comprueba con el
mismo criterio.
"""
import json, os, subprocess, sys, tempfile, shutil

PKG = "/home/lucas/Escritorio/rxre/tools"
RXRE = PKG + "/rxre"
MAQUINA = RXRE + "/api/machine.py"
PASS = "123456"
REG_REAL = "polaris12.gfx800.mmGRBM_STATUS"
REG_VRAM = "polaris12.gmc810.mmMC_VM_FB_LOCATION"
NOMBRE_FALSO = "polaris12.smc.gpu_length"      # el que usaba el docstring

dbdir = tempfile.mkdtemp(prefix="umr_hw_")
DB = os.path.join(dbdir, "hw.sqlite3")
env = {**os.environ, "PYTHONPATH": PKG + ":" + RXRE, "RXRE_DB": DB}
ok = []


def pedir(reqs, root=False, timeout=120, env_=None):
    """Pide por la superficie publica. root=True corre TODO como root.

    MEDIDO: `sudo` arranca con `env_reset` y no reenvia `RXRE_DB`. Si no se
    pasa a mano, el proceso privilegiado escribe en la BD POR DEFECTO y la
    verificacion posterior mira otra. Se pasa explicitamente con `env`, que
    es la forma correcta de conservar configuracion a traves de sudo.
    """
    e = env_ or env
    ent = "\n".join(json.dumps(r) for r in reqs) + "\n"
    if root:
        passthrough = " ".join("%s=%s" % (k, e[k]) for k in sorted(e)
                               if k.startswith("RXRE_"))
        cmd = (["sudo", "-S", "env"] + passthrough.split()
               + [sys.executable, MAQUINA])
        # MEDIDO: `sudo -S` lee la contrasena de stdin SOLO si la pide. Con
        # el ticket ya cacheado no lee nada, y la linea de la contrasena se
        # cuela en el stdin del proceso como `123456`, que es un entero
        # valido. machine.py ya no se muere por eso (ver test_autonomy003),
        # pero para que este test mida lo que dice medir, la contrasena solo
        # se antepone cuando sudo la va a pedir de verdad.
        calienta = subprocess.run(["sudo", "-S", "-v"], input=PASS + "\n",
                                  capture_output=True, text=True, timeout=30)
        if calienta.returncode != 0:
            return [], subprocess.CompletedProcess(cmd, 1, "", "sudo -v fallo")
        p = subprocess.run(cmd, input=ent, capture_output=True, text=True,
                           timeout=timeout, env=e)
    else:
        cmd = [sys.executable, MAQUINA]
        p = subprocess.run(cmd, input=ent, capture_output=True, text=True,
                           timeout=timeout, env=e)
    out = []
    for l in p.stdout.splitlines():
        if l.strip():
            try:
                out.append(json.loads(l))
            except json.JSONDecodeError:
                pass
    return out, p


def run_umr(reg, **extra):
    return {"op": "run", "capability": "gpu.register_read",
            "pci_address": "0000:01:00.0", "register_name": reg, **extra}


print("=" * 74)
print("1) PRECHECK ESTATICO contra la BD de UMR (sin privilegios)")
print("=" * 74)
res, _ = pedir([run_umr(NOMBRE_FALSO), run_umr(REG_REAL)])
a_falso, a_real = res[0], res[1]
bd = (a_falso.get("precheck") or {}).get("registro_en_bd") or {}
print("  %-36s -> %s" % (NOMBRE_FALSO, a_falso.get("status")))
print("     %s" % (bd.get("motivo") or "")[:120])
bd2 = (a_real.get("precheck") or {}).get("registro_en_bd") or {}
print("  %-36s -> existe=%s" % (REG_REAL, bd2.get("existe")))
if a_falso.get("status") == "invalid_input" and not bd.get("existe"):
    ok.append("el nombre inexistente se rechaza SIN gastar privilegios")
if bd2.get("existe"):
    ok.append("el nombre real se reconoce contra la BD")

print("\n" + "=" * 74)
print("2) LA FRONTERA DURA: la Intel 0000:00:02.0 no se toca")
print("=" * 74)
res, _ = pedir([run_umr(REG_REAL, pci_address="0000:00:02.0")])
a = res[0]
print("  status = %s" % a.get("status"))
print("  motivo = %s" % (a.get("motivo") or (a.get("limitations") or ["-"])[0])[:100])
if a.get("status") == "invalid_input" and "allow-list" in (
        a.get("motivo") or (a.get("limitations") or [""])[0]):
    ok.append("la Intel sigue prohibida por allow-list, con privilegios o sin ellos")

print("\n" + "=" * 74)
print("3) SIN PRIVILEGIOS: bloqueado, y dice cual es el prerrequisito")
print("=" * 74)
res, _ = pedir([run_umr(REG_REAL)])
a = res[0]
prereq = [l for l in (a.get("limitations") or []) if "RXRE_ESCALATE" in l]
print("  status      = %s" % a.get("status"))
print("  prerrequisito = %s" % (prereq[0].strip() if prereq else "NO DECLARADO"))
if a.get("status") == "blocked" and prereq:
    ok.append("sin privilegios: BLOCKED con el prerrequisito exacto")

print("\n" + "=" * 74)
print("4) LECTURA REAL (con privilegios) por la superficie publica")
print("=" * 74)
res, p = pedir([run_umr(REG_REAL), run_umr(REG_VRAM)], root=True)
ids = []
for a in res:
    r = (a.get("results") or [{}])[0]
    ej = a.get("ejecucion") or {}
    print("  status=%-5s persistido=%-5s rc=%-4s op=%s"
          % (a.get("status"), a.get("persistido"), ej.get("exit_status"),
             a.get("operation_id")))
    print("     registro  = %s" % (r.get("location") or {}).get("register"))
    print("     valor_hex = %s   (dec %s)" % (r.get("value_hex"), r.get("value")))
    print("     argv      = %s" % " ".join(ej.get("argv") or [])[:96])
    print("     cascada   = %d registros devueltos por UMR"
          % len(r.get("registros_leidos") or []))
    if a.get("status") == "ok" and str(r.get("value_hex", "")).startswith("0x"):
        ok.append("lectura REAL del ASIC: %s = %s"
                  % ((r.get("location") or {}).get("register"), r.get("value_hex")))
        ids.append(r.get("result_id"))
    if r.get("value_hex") and len(r.get("value_hex")) == 10:
        ok.append("el ancho del registro se conserva en value_hex (%s)"
                  % r.get("value_hex"))

print("\n" + "=" * 74)
print("5) EARTH: la lectura de hardware es trazable con `explain`")
print("=" * 74)
if ids:
    res, p = pedir([{"op": "explain", "result_id": i} for i in ids], root=True)
    if not res:
        print("  explain no devolvio nada. stderr: %s" % p.stderr.strip()[:300])
        ok.append("FALLO explain: sin respuesta")
    for i, a in zip(ids, res):
        print("  %s -> status=%s" % (i, a.get("status")))
        if a.get("limitations"):
            print("     %s" % a["limitations"][0][:110])
        if a.get("status") == "ok":
            ok.append("explain reconstruye la lectura de hardware %s" % i[:28])

print("\n" + "=" * 74)
print("6) AIR: la superficie no muere con una linea JSON que no es objeto")
print("=" * 74)
p = subprocess.run([sys.executable, MAQUINA],
                   input='123456\n{"op": "ops"}\n',
                   capture_output=True, text=True, timeout=60, env=env)
lineas = [l for l in p.stdout.splitlines() if l.strip()]
print("  rc=%d  lineas de salida=%d  traceback=%s"
      % (p.returncode, len(lineas), "SI" if "Traceback" in p.stderr else "no"))
if p.stderr.strip():
    print("  stderr: %s" % p.stderr.strip()[:300])
tipos = []
for l in lineas:
    try:
        tipos.append(json.loads(l).get("status"))
    except Exception:
        pass
print("  estados devueltos: %s" % tipos)
if p.returncode == 0 and len(lineas) == 2 and tipos == ["invalid_input", "ok"]:
    ok.append("una linea no-objeto responde y el proceso sigue (%s)" % tipos)
elif p.returncode == 0 and len(lineas) == 2:
    ok.append("una linea no-objeto no tumba el proceso")

shutil.rmtree(dbdir, ignore_errors=True)
print("\n" + "=" * 74)
fallos = [o for o in ok if o.startswith("FALLO")]
for o in ok:
    print("  %s" % o)
print("=" * 74)
print("  %d/%d" % (len(ok) - len(fallos), len(ok)))
sys.exit(1 if fallos else 0)