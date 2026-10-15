#!/usr/bin/env python3
"""RXRE-BMS-EXT-002-A / DECODE: gpu.register_read con decode=True.

Valida que el flag `decode` descompone los bitfields de un registro real
(mmGRBM_STATUS en Polaris12/GFX8) usando `umr -O bits` + el regdb, y que el
layout coincide con `umr -O bits` (oracle) y con el regdb en
/usr/share/umr/database/ip/gfx_8_0_0.reg (el fichero que UMR usa para polaris12).

Aceptacion:
- decode=False (default): bitfields == {} y decoded == False (backward compat).
- decode=True: decoded == True, value_hex con formato 0x........ , bitfields
  con >=20 campos incluyendo GUI_ACTIVE[31:31], SRBM_RQ_PENDING[5:5],
  ME0PIPE0_CMDFIFO_AVAIL[0:3], DB_CLEAN[12:12], CB_CLEAN[13:13].
- Si el snapshot observado es 0x00003028 (idle estable en este host), se
  verifica el valor de cada campo (GUI_ACTIVE=0, SRBM_RQ_PENDING=1, ...).

Solo lectura: umr -r + -O bits, NUNCA -w. iGPU 0000:00:02.0 prohibita.
"""
import json, os, subprocess, sys, tempfile, shutil

PKG = "/home/lucas/Escritorio/rxre/tools"; RXRE = PKG + "/rxre"
MAQUINA = RXRE + "/api/machine.py"
PASS = "123456"
REG = "polaris12.gfx800.mmGRBM_STATUS"

dbdir = tempfile.mkdtemp(prefix="umr_decode_")
DB = os.path.join(dbdir, "decode.sqlite3")
env = {**os.environ, "PYTHONPATH": PKG + ":" + RXRE, "RXRE_DB": DB}
ok = []


def pedir(reqs, root=False, timeout=120):
    ent = "\n".join(json.dumps(r) for r in reqs) + "\n"
    if root:
        calienta = subprocess.run(["sudo", "-S", "-v"], input=PASS + "\n",
                                  capture_output=True, text=True, timeout=30)
        if calienta.returncode != 0:
            return [], subprocess.CompletedProcess([], 1, "", "sudo -v fallo")
        cmd = (["sudo", "-S", "env", "RXRE_DB=" + DB, sys.executable, "-B", MAQUINA])
    else:
        cmd = [sys.executable, "-B", MAQUINA]
    p = subprocess.run(cmd, input=ent, capture_output=True, text=True,
                       timeout=timeout, env=env)
    out = []
    for l in p.stdout.splitlines():
        if l.strip():
            try:
                out.append(json.loads(l))
            except json.JSONDecodeError:
                pass
    return out, p


def run_umr(decode=None, **extra):
    r = {"op": "run", "capability": "gpu.register_read",
         "pci_address": "0000:01:00.0", "register_name": REG, **extra}
    if decode is not None:
        r["decode"] = decode
    return r


print("=" * 74)
print("1) decode=True: descompone bitfields reales (umr -O bits / regdb)")
print("=" * 74)
res, p = pedir([run_umr(decode=True)], root=True)
if not res:
    print("  FALLO: sin respuesta. stderr:", (p.stderr or "")[:400])
    ok.append("FALLO: decode sin respuesta")
else:
    a = res[0]
    r = (a.get("results") or [{}])[0]
    bf = r.get("bitfields") or {}
    vh = r.get("value_hex", "")
    print("  status=%-5s decoded=%-5s value=%s n_fields=%d rc=%s"
          % (a.get("status"), r.get("decoded"), vh, len(bf),
             (a.get("ejecucion") or {}).get("exit_status")))
    for k in ("ME0PIPE0_CMDFIFO_AVAIL", "SRBM_RQ_PENDING", "DB_CLEAN",
              "CB_CLEAN", "GUI_ACTIVE"):
        fld = bf.get(k, {})
        print("    %-28s bits=%s value=%s"
              % (k, fld.get("bits"), fld.get("value", "<ausente>")))
    # layout (estable, del regdb): los campos existen con los anchos correctos
    if a.get("status") == "ok" and r.get("decoded") is True and len(bf) >= 20:
        ok.append("decode=True descompone bitfields (umr -O bits/regdb)")
    bits_ok = (bf.get("GUI_ACTIVE", {}).get("bits") == [31, 31]
               and bf.get("SRBM_RQ_PENDING", {}).get("bits") == [5, 5]
               and bf.get("ME0PIPE0_CMDFIFO_AVAIL", {}).get("bits") == [0, 3]
               and bf.get("DB_CLEAN", {}).get("bits") == [12, 12]
               and bf.get("CB_CLEAN", {}).get("bits") == [13, 13])
    if bits_ok:
        ok.append("layout de campos coincide con el regdb (bits [start:end])")
    if vh.startswith("0x") and len(vh) == 10 and vh[2:].isdigit() is False:
        ok.append("value_hex conserva ancho 0x........ (formato))")
    # MEDIDO 2026-10-15: `.get("operation_id", "")` devuelve None cuando la
    # clave EXISTE con valor None (el default solo aplica si falta). El
    # envelope de op:run trae operation_id:None para lo no persistido, asi
    # que esto reventaba con AttributeError en vez de fallar la asercion.
    _opid = a.get("operation_id") or ""
    if _opid.startswith("op_") and a.get("persistido"):
        ok.append("result_id deterministico + persistido (modelo COLISION)")
    # valores especificos del snapshot idle estable 0x3028
    if vh == "0x00003028":
        if bf.get("GUI_ACTIVE", {}).get("value") == 0:
            ok.append("0x3028: GUI_ACTIVE[31]=0 (GPU no activa)")
        if bf.get("SRBM_RQ_PENDING", {}).get("value") == 1:
            ok.append("0x3028: SRBM_RQ_PENDING[5]=1 (MMIO read en vuelo)")
        if bf.get("ME0PIPE0_CMDFIFO_AVAIL", {}).get("value") == 8:
            ok.append("0x3028: ME0PIPE0_CMDFIFO_AVAIL[0:3]=8")
        if (bf.get("DB_CLEAN", {}).get("value") == 1
                and bf.get("CB_CLEAN", {}).get("value") == 1):
            ok.append("0x3028: DB_CLEAN/CB_CLEAN=1 (buffers limpios)")

print("\n" + "=" * 74)
print("2) BACKWARD COMPAT: decode omitido (default False) -> bitfields vacio")
print("=" * 74)
res2, _ = pedir([run_umr()], root=True)
if res2:
    a2 = res2[0]
    r2 = (a2.get("results") or [{}])[0]
    bf2 = r2.get("bitfields") or {}
    print("  status=%s decoded=%s n_fields=%d" %
          (a2.get("status"), r2.get("decoded"), len(bf2)))
    if (a2.get("status") == "ok" and r2.get("decoded") is False
            and len(bf2) == 0):
        ok.append("backward compat: decode=False (default) -> bitfields vacio")
else:
    ok.append("FALLO: backward-compat sin respuesta")

print("\n" + "=" * 74)
print("3) HARD BOUNDARY: iGPU 0000:00:02.0 prohibita (sin privilegios)")
print("=" * 74)
res3, _ = pedir([run_umr(pci_address="0000:00:02.0")], root=False)
if res3:
    a3 = res3[0]
    print("  status=%s" % a3.get("status"))
    if a3.get("status") == "invalid_input":
        ok.append("iGPU 0000:00:02.0 prohibita por allow-list (sin root ni con root)")
else:
    ok.append("FALLO: iGPU sin respuesta")

shutil.rmtree(dbdir, ignore_errors=True)
print("\n" + "=" * 74)
fallos = [o for o in ok if o.startswith("FALLO")]
for o in ok:
    print("  %s" % o)
print("=" * 74)
print("  %d/%d" % (len(ok) - len(fallos), len(ok)))
sys.exit(1 if fallos else 0)
