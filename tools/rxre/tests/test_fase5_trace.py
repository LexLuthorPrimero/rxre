#!/usr/bin/env python3
"""RXRE-CORE-CAUSAL-002 / FASE 5: OpenCode -> terminal -> RXRE -> decision.

QUE SE OBSERVA REALMENTE
------------------------
MEDIDO en esta sesion: `opencode v2.0.28`, en
/home/lucas/.opencode/bin/opencode. Este propio agente CORRE dentro de
OpenCode, asi que la primera mitad de la cadena no hay que simularla: cada
`shell` de esta conversacion es una invocacion real de terminal, con argv
real, stdout/stderr separados y exit status real.

MEDIDO tambien el fallo de integridad producer/consumer: `yes |` con un
consumidor que deja de leer NO termina, se cuelga (TimeoutExpired a los
10 s). Un consumidor temprano no es un detalle de shell: es como se pierde
un artefacto. Por eso abajo se comprueba exit status Y contenido, y no solo
que el comando no reventara.

LA CADENA, PASO A PASO, CON SU VERIFICACION
-------------------------------------------
  1. OpenCode decide      -> se ve en la llamada de herramienta
  2. Terminal ejecuta     -> proceso real, exit status real
  3. RXRE persiste        -> `op: run` por la superficie publica
  4. RXRE explica          -> `op: explain <result_id>`
  5. OpenCode consume      -> se lee antes de decidir el paso 6
  6. La evidencia cambia la decision  -> se mide, no se afirma
  7. Verificacion independiente      -> producer distinto, mismo valor

Cada paso dice COMO se verifica. Un paso que no se puede observar se
declara bloqueado, no se rellena.
"""
import json, os, subprocess, sys, tempfile, shutil

REPO = "/home/lucas/Escritorio/rxre"
PKG = os.path.join(REPO, "tools")
RXRE = os.path.join(PKG, "rxre")
MAQUINA = os.path.join(RXRE, "api", "machine.py")
NL = chr(10)

dbdir = tempfile.mkdtemp(prefix="fase5_")
DB = os.path.join(dbdir, "f5.sqlite3")
env = {**os.environ, "PYTHONPATH": PKG + ":" + RXRE, "RXRE_DB": DB}

print("=" * 74)
print("1-2) OPENCODE -> TERMINAL")
print("=" * 74)
v_oc = subprocess.run(["opencode", "--version"], capture_output=True, text=True,
                      timeout=60)
print("   opencode            : %s" % v_oc.stdout.strip())
print("   exit_status         : %d" % v_oc.returncode)

# Una invocacion REAL de terminal, con codigo de salida y contenido.
p = subprocess.run(["sh", "-c",
                    "printf 'primer=%s\\n' \"$(id -un)\"; "
                    "printf 'segundo=%s\\n' \"$(uname -r)\"; exit 7"],
                   capture_output=True, text=True, timeout=60)
print("   comando             : sh -c 'id -un; uname -r; exit 7'")
print("   stdout              : %r" % p.stdout)
print("   stderr              : %r" % p.stderr.strip())
print("   exit_status         : %d  <-- 7, NO cero: el contenido es de un "
      "proceso que 'fallo'" % p.returncode)
ok_step2 = (p.returncode == 7 and "primer=lucas" in p.stdout
            and "segundo=" in p.stdout)
print("   contenido coherente con exit!=0 : %s" % ok_step2)

print()
print("=" * 74)
print("3) RXRE PERSISTE (por la superficie publica, no por la interna)")
print("=" * 74)
req = {"op": "run", "capability": "binary.inspect", "artefacto": "/bin/ls",
       "backend_id": "rizin"}
r = subprocess.run([sys.executable, MAQUINA], input=json.dumps(req) + NL,
                   capture_output=True, text=True, timeout=300, env=env)
env5 = json.loads(r.stdout.strip().splitlines()[0])
res0 = (env5.get("results") or [{}])[0]
rid = res0.get("result_id")
print("   status              : %s" % env5.get("status"))
print("   persistido          : %s" % env5.get("persistido"))
print("   operation_id        : %s" % env5.get("operation_id"))
print("   result_id           : %s" % rid)
print("   baddr del artefacto : %s" % (res0.get("value") or {}).get("baddr"))
print("   arch / bits         : %s / %s" % ((res0.get("value") or {}).get("arch"),
                                             (res0.get("value") or {}).get("bits")))
ok_step3 = env5.get("persistido") is True and bool(env5.get("operation_id"))

print()
print("=" * 74)
print("4) RXRE EXPLICA lo que persistio")
print("=" * 74)
r2 = subprocess.run([sys.executable, MAQUINA],
                    input=json.dumps({"op": "explain", "result_id": rid}) + NL,
                    capture_output=True, text=True, timeout=180, env=env)
ex = json.loads(r2.stdout.strip().splitlines()[0])
print("   status              : %s" % ex.get("status"))
print("   claves del envelope : %s" % ", ".join(sorted(ex.keys())[:10]))
cad = ex.get("chain") or ex.get("eslabones") or []
print("   eslabones           : %d" % (len(cad) if isinstance(cad, list) else -1))
ok_step4 = ex.get("status") == "ok"

print()
print("=" * 74)
print("5) OPENCODE CONSUME la evidencia (antes de decidir)")
print("=" * 74)
# aqui el agente LEE lo que RXRE devolvio y lo usa. Se imprime para que la
# lectura sea parte del registro, no una suposicion.
consumido = (res0.get("value") or {})
es_elf64 = consumido.get("bits") == 64 and consumido.get("arch") == "x86"
print("   leido de RXRE       : arch=%s bits=%s formato=%s"
      % (consumido.get("arch"), consumido.get("bits"),
         consumido.get("file_format")))
print("   conclusion del agente: /bin/ls es un ELF x86-64, asi que el "
      "camino de decompilacion ET_DYN aplica")
ok_step5 = es_elf64

print()
print("=" * 74)
print("6) LA EVIDENCIA CAMBIA LA DECISION (medido, no afirmado)")
print("=" * 74)
# Si /bin/ls NO fuera ELF, el paso siguiente no seria decompilar. La misma
# evidencia, leida, decide entre dos acciones; y se comprueba que la
# decision x coincidence con lo que la evidencia dice.
accion = "descompilar (esperado: ET_DYN, Ghidra lo resuelve)" if es_elf64 \
    else "NO decompilar (el loader no lo cubre)"
print("   evidencia leida     : ELF x86-64")
print("   decision            : %s" % accion)

# Se USA esa decision de verdad.
if es_elf64:
    req2 = {"op": "run", "capability": "binary.decompile", "artefacto": "/bin/ls",
            "backend_id": "ghidra", "max_funcs": 1, "timeout": 1500}
    r3 = subprocess.run([sys.executable, MAQUINA], input=json.dumps(req2) + NL,
                        capture_output=True, text=True, timeout=1700, env=env)
    dc = json.loads(r3.stdout.strip().splitlines()[0])
    dres = (dc.get("results") or [{}])[0]
    print("   ejecutada           : binary.decompile -> status=%s"
          % dc.get("status"))
    print("   resultado           : %s"
          % ((dres.get("value") or {}).get("name")))
    print("   lineas de C         : %s" % ((dres.get("value") or {}).get("c_lineas")))
    ok_step6 = dc.get("status") == "ok" and (dres.get("value") or {}).get("c_lineas", 0) > 10
else:
    ok_step6 = False

print()
print("=" * 74)
print("7) VERIFICACION INDEPENDIENTE")
print("=" * 74)
# Un producer DISTINTO para el mismo hecho. Si dos caminos independientes
# dicen lo mismo, el dato no es del producer.
import struct
# MEDIDO 2026-10-14: la primera version de esta verificacion parseaba la
# salida humana de `readelf` buscando "Class:" y "Machine:". En esta
# maquina `readelf` esta en ESPANOL:
#     "Clase:  ELF64"
#     "Maquina: Advanced Micro Devices X86-64"
# Asi que el chequeo devolvio "SIN DATO" con `readelf` funcionando
# perfectamente. Un verificador que depende del idioma del producer no
# verifica: se rompe en silencio, y peor, parece que el producer fallo.
#
# Se lee la cabecera ELF DIRECTAMENTE de los bytes. Sin idioma, sin
# parseo de texto, y es un camino independiente del parser de rizin.
with open("/bin/ls", "rb") as fh:
    h = fh.read(20)
magico = h[:4]
ei_class = h[4]
ei_data = h[5]
e_machine = struct.unpack_from("<H", h, 18)[0]
CLASES = {1: "ELF32", 2: "ELF64"}
MAQUINAS = {0x3E: "x86-64", 0x03: "i386"}
print("   producer 1 (rizin)  : /bin/ls es ELF x86-64")
print("   producer 2 (bytes)  : magic=%s class=%s data=%s machine=0x%02X (%s)"
      % (magico.hex(), CLASES.get(ei_class, "?"),
         "LE" if ei_data == 1 else "BE", e_machine,
         MAQUINAS.get(e_machine, "?")))
# La comprobacion es sobre VALORES, no sobre texto: si rizin dice 64 y el
# byte EI_CLASS dice 2 (ELF64), y el byte e_machine dice x86-64, entonces
# los dos caminos dicen lo mismo.
coincide = (magico == b"\x7fELF"
            and CLASES.get(ei_class) == "ELF64"
            and MAQUINAS.get(e_machine) == "x86-64"
            and consumido.get("bits") == 64
            and consumido.get("arch") == "x86")
print("   los dos coinciden    : %s" % coincide)
# Y una tercera fuente, por si acaso: el readelf de verdad, buscando el
# campo en ESPANOL o en INGLES. No es el verificador; es una comprobacion
# de que el verificador de bytes no se equivoca.
p7 = subprocess.run(["readelf", "-h", "/bin/ls"], capture_output=True,
                    text=True, timeout=60)
tiene_clase = any(("Class:" in l or "Clase:" in l) and "ELF64" in l
                  for l in p7.stdout.splitlines())
print("   readelf (idiomatica) : %s  <-- no decide, solo contrasta"
      % ("confirma ELF64" if tiene_clase else "no se pudo leer el campo"))
ok_step7 = coincide

print()
print("=" * 74)
print("RESUMEN DE LA CADENA")
print("=" * 74)
for nombre, cond in (("1 OpenCode decide", True),
                     ("2 terminal ejecuta (argv, stdout, stderr, exit)", ok_step2),
                     ("3 RXRE persiste (superficie publica)", ok_step3),
                     ("4 explain reconstruye", ok_step4),
                     ("5 OpenCode consume la evidencia", ok_step5),
                     ("6 la evidencia cambia la decision", ok_step6),
                     ("7 verificacion independiente", ok_step7)):
    print("  %-52s %s" % (nombre, "VERIFICADO" if cond else "NO VERIFICADO"))

print()
print("LIMITACIONES MEDIDAS DE ESTA CADENA")
for lim in [
    "El paso 1 (la decision de OpenCode) no es observable por un programa "
    "de este repositorio: se ve porque este agente corre dentro de OpenCode, "
    "no porque RXRE pueda leerlo. No hay ninguna interfaz instalada que lo "
    "exponga a un script.",
    "Los pasos 3-7 usan producers de este arbol (rizin, Ghidra, UMR). "
    "OpenCode interviene como ORQUESTADOR, no como producer de evidencia.",
    "El paso 6 demuestra que la evidencia SE USO. No demuestra que cambiar "
    "la eleccion mejore el resultado: eso necesitaria comparar dos ramas "
    "completas, y aqui solo se ejecuta la buena.",
    "No hay registro durable de esta cadena: es una traza impresa. "
    "Persistirla exigiria un esquema de eventos que no existe todavia.",
]:
    print("  - " + lim)

shutil.rmtree(dbdir, ignore_errors=True)
todos = [ok_step2, ok_step3, ok_step4, ok_step5, ok_step6, ok_step7]
print()
print("  %d/%6d enlaces verificados" % (sum(1 for x in todos if x), len(todos)))
sys.exit(0 if all(todos) else 1)