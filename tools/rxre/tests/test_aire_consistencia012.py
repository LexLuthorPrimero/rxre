#!/usr/bin/env python3
"""RXRE-012 AIRE: la misma verdad fisica, la misma descripcion en cada modulo.

CASO REAL MEDIDO 2026-10-15 (chmod 000 sobre una copia de /bin/ls):

  modulo                              decia
  ----------------------------------  -----------------------------------
  rz_inspect (binary.inspect)         "la entrada no es un ELF (firma
                                       distinta de \\x7fELF)"  -> FALSO:
                                       la firma nunca se leyo
  _verificar_integridad_artefacto     "artefacto no legible"  -> verdadero
                                      PERO artifact_exists=false -> FALSO:
                                      os.path.exists ya habia medido que si

Dos modulos, dos descripciones distintas del MISMO hecho, y ambas con al
menos una afirmacion que no se sostiene. El caso PE (MZ) sirve de control:
ahi la firma SI se leyo y "no es un ELF" es una afirmacion verdadera.

Lo que esta prueba blinda:
  1. ILEGIBLE: precheck.input_legible=false, input_es_elf=None (no-saber,
     no falso); NINGUNA limitation puede afirmar "firma distinta"; el
     artifact_check dice exists=true + readable=false.
  2. PE: firma leida -> input_es_elf=false es VERDADERO; no se invoca al
     backend; artifact_check existe y es legible.
  3. TEXTO: mismo contrato que el PE (firma leida y distinta).
  4. ELF real: input_es_elf=true y el precheck queda ok (no se degrada el
     camino feliz).
  5. COHERENCIA INTERNA: si precheck.input_legible es False, ninguna
     limitation puede contener "firma distinta" (prohibido afirmar lo que no
     se midio). Es la regla AIRE: los canales no se contradicen.

DB-only + filesystem temporal: no toca GPU, no toca hardware, no requiere
root. iGPU 0000:00:02.0 intacta.
"""
import json, os, struct, subprocess, sys, tempfile, shutil

PKG = "/home/lucas/Escritorio/rxre/tools"; RXRE = PKG + "/rxre"
MAQUINA = RXRE + "/api/machine.py"

# /tmp puede ser un tmpfs lleno; /var/tmp esta en el fs raiz con espacio.
BASE_TMP = os.environ.get("RXRE_TEST_TMPDIR", "/var/tmp")
work = tempfile.mkdtemp(prefix="aire_012_", dir=BASE_TMP)
env = {**os.environ, "PYTHONPATH": PKG + ":" + RXRE,
       "RXRE_DB": os.path.join(work, "aire.sqlite3")}
ok = []


def pedir(reqs, timeout=90):
    ent = "\n".join(json.dumps(r) for r in reqs) + "\n"
    p = subprocess.run([sys.executable, "-B", MAQUINA],
                       input=ent, capture_output=True, text=True,
                       timeout=timeout, env=env)
    out = []
    for l in p.stdout.splitlines():
        if l.strip():
            try:
                out.append(json.loads(l))
            except json.JSONDecodeError:
                pass
    return out


# --- Casos nominales --------------------------------------------------------
ilegible = os.path.join(work, "no_legible.bin")
shutil.copy("/bin/ls", ilegible)
os.chmod(ilegible, 0o000)

pe = os.path.join(work, "pe_min.exe")
data = bytearray(128)
data[0:2] = b"MZ"
struct.pack_into("<I", data, 60, 0x40)
data[0x40:0x44] = b"PE\x00\x00"
open(pe, "wb").write(bytes(data))

texto = os.path.join(work, "texto.txt")
open(texto, "w").write("esto no es un ELF, es texto\n")

# 1) ILEGIBLE (chmod 000): no-saber, no falso
res = pedir([{"op": "run", "capability": "binary.inspect",
              "artefacto": ilegible}])
d = res[0] if res else {}
pre = d.get("precheck", {})
ac = d.get("artifact_check", {})
lims = d.get("limitations", [])
print("1) ILEGIBLE: status=%s legible=%s es_elf=%s exists=%s readable=%s"
      % (d.get("status"), pre.get("input_legible"), pre.get("input_es_elf"),
         ac.get("artifact_exists"), ac.get("artifact_readable")))
asserta = []
asserta.append(("NO se afirma firma sin leerla",
                not any("firma distinta" in l for l in lims)))
asserta.append(("precheck dice no legible",
                pre.get("input_legible") is False))
asserta.append(("precheck no afirma es_elf (None = no se sabe)",
                pre.get("input_es_elf") is None))
asserta.append(("artifact_check: existe=true aunque no legible",
                ac.get("artifact_exists") is True))
asserta.append(("artifact_check: readable=false",
                ac.get("artifact_readable") is False))
for nombre, cond in asserta:
    ok.append(("1) " + nombre) if cond else ("FALLO: 1) " + nombre))
    print("   %s %s" % ("PASS" if cond else "FAIL", nombre))

# 2) PE: firma LEIDA y distinta -> afirmarla es verdadero
res = pedir([{"op": "run", "capability": "binary.inspect", "artefacto": pe}])
d = res[0] if res else {}
pre = d.get("precheck", {})
lims = d.get("limitations", [])
print("2) PE: status=%s legible=%s es_elf=%s" %
      (d.get("status"), pre.get("input_legible"), pre.get("input_es_elf")))
c = (pre.get("input_legible") is True and pre.get("input_es_elf") is False
     and any("firma distinta" in l for l in lims)
     and any("no se invoco" in l for l in lims))
ok.append("2) PE: firma medida y distinta -> rechazo con motivo verdadero"
          if c else "FALLO: 2) PE")
print("   %s\n" % ("PASS" if c else "FAIL"))

# 3) TEXTO: mismo contrato que PE
res = pedir([{"op": "run", "capability": "binary.inspect", "artefacto": texto}])
d = res[0] if res else {}
pre = d.get("precheck", {})
c = pre.get("input_legible") is True and pre.get("input_es_elf") is False
ok.append("3) TEXTO: firma medida y distinta (input_es_elf=False)"
          if c else "FALLO: 3) TEXTO")
print("3) TEXTO: %s\n" % ("PASS" if c else "FAIL"))

# 4) ELF real: el camino feliz NO se degrada
res = pedir([{"op": "run", "capability": "binary.inspect", "artefacto": "/bin/ls"}])
d = res[0] if res else {}
pre = d.get("precheck", {})
c = (d.get("status") == "ok" and pre.get("input_legible") is True
     and pre.get("input_es_elf") is True and pre.get("ok") is True)
ok.append("4) ELF: legible + firma ELF + precheck ok + status ok"
          if c else "FALLO: 4) ELF (status=%s)" % d.get("status"))
print("4) ELF: %s\n" % ("PASS" if c else "FAIL"))

# 5) COHERENCIA: regla general sobre los tres canales delantera
res = pedir([{"op": "run", "capability": "binary.inspect", "artefacto": ilegible}])
d = res[0] if res else {}
pre, lims = d.get("precheck", {}), d.get("limitations", [])
c = not (pre.get("input_legible") is False
         and any("firma distinta" in l for l in lims))
ok.append("5) AIRE: canales coherentes (ilegible => sin afirmacion de firma)"
          if c else "FALLO: 5) COHERENCIA")
print("5) COHERENCIA: %s\n" % ("PASS" if c else "FAIL"))

# --- Nota de limite (explicita, no silenciada) -----------------------------
# Los adaptadores ahora comparten `estado_firma` (contract.py): binary.inspect,
# binary.functions, binary.container, binary.disasm, binary.cfg, binary.xrefs,
# binary.callgraph y binary.decompile distinguen ilegible de no-ELF.
# `op:lessons --capability X` expone el tracking de aplicacion (AGUA).
print("\n")

shutil.rmtree(work, ignore_errors=True)
fallos = [o for o in ok if o.startswith("FALLO")]
print("=" * 70)
for o in ok:
    print("  %s" % o)
print("=" * 70)
print("  %d/%d" % (len(ok) - len(fallos), len(ok)))
sys.exit(1 if fallos else 0)
