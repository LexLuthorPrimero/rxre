#!/usr/bin/env python3
"""RXRE-011 AGUA: leccion -> plan (influencia demostrable).

Verifica el lazo AGUA (Observe -> Validate -> Reason -> Prioritize -> Execute
-> Evaluate -> Persist -> Learn -> Influence -> Verify -> Integrate) sobre la
capa de decisiones: una leccion de FALLO registrada por `op:reflect` para la
capability `gpu.register_read` DEBE influir en la salida de `op:plan` para esa
misma capability (agrega `warning` + `reflexiones_previas` con la estrategia),
y NO para una capability sin leccion (control).

Discriminante: la leccion viaja hasta el plan y modifica su veredicto (warning),
no solo se expone. La leccion proviene del hallazgo de decode de mmGRBM_STATUS
(umr -O bits + regdb ip/gfx_8_0_0.reg, 24 bitfields; 0x00003028 idle): la
variante raw-only fue insuficiente, por lo que la estrategia corregida es usar
decode=True.

DB-only: op:reflect / op:plan son store ops (no tocan GPU). iGPU
0000:00:02.0 prohibita.
"""
import json, os, subprocess, sys, tempfile, shutil

PKG = "/home/lucas/Escritorio/rxre/tools"; RXRE = PKG + "/rxre"
MAQUINA = RXRE + "/api/machine.py"

dbdir = tempfile.mkdtemp(prefix="agua_plan008_")
DB = os.path.join(dbdir, "agua.sqlite3")
env = {**os.environ, "PYTHONPATH": PKG + ":" + RXRE, "RXRE_DB": DB}
ok = []


def pedir(reqs, root=False, timeout=120):
    ent = "\n".join(json.dumps(r) for r in reqs) + "\n"
    if root:
        calienta = subprocess.run(["sudo", "-S", "-v"], input="123456\n",
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


# 1) APRENDER: reflexion de fallo derivada del hallazgo de decode (outcome=failure)
res, _ = pedir([{"op": "reflect", "target": "gpu.register_read",
                  "capability": "gpu.register_read",
                  "feedback": "gpu.register_read entrego RAW_BINARY sin campos; el layout "
                              "solo se obtiene con umr -O bits + regdb ip/gfx_8_0_0.reg "
                              "(24 bitfields en 0x00003028)",
                  "reflection": "umr -O bits decodifica el layout (regdb autoridad); "
                                "interpretacion semantica de campos es hipotesis hasta "
                                "multiples samples; un snapshot no prueba estado sostenido",
                  "outcome": "failure",
                  "strategy": "usar decode=True (-O bits+regdb); 0x3028 snapshot idle "
                              "(SRBM_RQ_PENDING=1=lector); no confiar en un solo sample",
                  "check_ejecutable": "tools/rxre/tests/test_umr_decode003.py"}],
               root=False)
r0 = res[0] if res else {}
print("1) APRENDER op:reflect: status=%s" % r0.get("status"))
if r0.get("status") not in ("error",):
    ok.append("APRENDER: op:reflect registra la leccion sin error")
else:
    ok.append("FALLO: APRENDER op:reflect")

# 2) INFLUIR: op:plan gpu.register_read debe consultar la leccion
rp, _ = pedir([{"op": "plan", "capability": "gpu.register_read"}], root=False)
P = rp[0] if rp else {}
lec = P.get("reflexiones_previas") or []
w = P.get("warning") or ""
print("2) INFLUIR op:plan gpu.register_read: status=%s n_lecciones=%d warning=%s"
      % (P.get("status"), len(lec), bool(w)))
if bool(w) and "Revisar antes de ejecutar" in w and len(lec) == 1:
    ok.append("INFLUIR: plan gpu.register_read agrega warning (leccion influye la decision)")
else:
    ok.append("FALLO: INFLUIR")
if lec and lec[0].get("strategy", "").startswith("usar decode=True"):
    ok.append("INFLUIR: la estrategia viaja hasta el plan")
else:
    ok.append("FALLO: estrategia no viaja al plan")

# 3) CONTROL: op:plan binary.inspect (sin leccion) -> no warning
rc, _ = pedir([{"op": "plan", "capability": "binary.inspect"}], root=False)
Pc = rc[0] if rc else {}
print("3) CONTROL op:plan binary.inspect: warning=%s n_lecciones=%d"
      % (bool(Pc.get("warning")), len(Pc.get("reflexiones_previas") or [])))
if (not Pc.get("warning")) and not (Pc.get("reflexiones_previas")):
    ok.append("CONTROL: plan sin leccion no agrega warning (discriminante)")
else:
    ok.append("FALLO: CONTROL")

shutil.rmtree(dbdir, ignore_errors=True)
fallos = [o for o in ok if o.startswith("FALLO")]
print("\n" + "=" * 70)
for o in ok:
    print("  %s" % o)
print("=" * 70)
print("  %d/%d" % (len(ok) - len(fallos), len(ok)))
sys.exit(1 if fallos else 0)
