#!/usr/bin/env python3
"""RXRE-BMS-EXT-003: `binary.decompile` ejecutado de verdad, y protegido.

QUE PROTEGE ESTE CHECK, Y POR QUE
---------------------------------
MEDIDO 2026-10-14: tres restricciones de Ghidra 12.1.4 que NO estan
documentadas y que costaron tres experimentos fallidos:

  1. `-postScript` NO puede recibir `DumpDecomp.class`.
     `HeadlessAnalyzer.checkScript` construye el URLClassLoader con
     `GhidraScriptUtil.getScriptSourceDirectories()` y el `-scriptPath`
     NO participa. Resultado: "java class not found for 'DumpDecomp'",
     aunque la clase exista y `-scriptPath` apunte a su directorio.
     Hay que pasar `DumpDecomp.java` (NOMBRE DE FICHERO).

  2. `-scriptPath` admite UNA SOLA ruta. MEDIDO: SCRIPTS -> OK;
     SCRIPTS:<dir vacio> -> "Script not found"; dos flags -scriptPath
     repetidos -> "Script not found". Un directorio vacio tambien lo rompe,
     asi que no es colision de nombres: el descriptor no admite mas de una.

  3. Ghidra compila el FUENTE el mismo. La clase precompilada no hace
     falta en la invocacion (sigue siendo el chequeo barato de contrato).

Estas tres cosas las ha fixing una persona. Si alguien "simplifica" el argv,
este check falla en vez de devolver "Script not found" tres minutos despues.

NIVELES DE VERIFICACION, QUE NO SE MEZCLAN
-------------------------------------------
  A. compilacion  -> el fuente compila contra los JARs reales   (barato)
  B. invariantes  -> el argv cumple las 3 reglas de arriba      (barato)
  C. ejecucion    -> Ghidra arranca y produce pseudocodigo      (lento, ~20s)
  D. trazabilidad -> persistido y `explain` reconstruye         (medio)

Cada nivel dice lo que cubre. Un nivel que no se ha ejecutado NO se
reporta como verde: se reporta como NO EJECUTADO.
"""
import json, os, re, subprocess, sys, tempfile, shutil, time

REPO = "/home/lucas/Escritorio/rxre"
PKG = os.path.join(REPO, "tools")
RXRE = os.path.join(PKG, "rxre")
MAQUINA = os.path.join(RXRE, "api", "machine.py")
ADAPTER = os.path.join(RXRE, "backends", "adapters", "gh_decompile.py")
FUENTE = os.path.join(RXRE, "backends", "scripts", "DumpDecomp.java")
BUILD = os.path.join(RXRE, "backends", "scripts", "build")
HOME = "/usr/lib64/ghidra"
NL = chr(10)

ok, no_ejecutado = [], []


def v(etiqueta, cond, detalle=""):
    (ok if cond else no_ejecutado).append(
        "%s %s%s" % ("PASS" if cond else "FAIL", etiqueta,
                    (" -> " + str(detalle)[:150]) if detalle else ""))


print("=" * 74)
print("A) COMPILACION contra los JARs reales")
print("=" * 74)
v("el fuente existe", os.path.isfile(FUENTE), FUENTE)
src = open(ADAPTER, encoding="utf-8").read()
jars = sorted(__import__("glob").glob(HOME + "/Ghidra/**/*.jar", recursive=True))
v("hay JARs de Ghidra", len(jars) > 100, "%d jars" % len(jars))
if os.path.isfile(FUENTE) and jars:
    os.makedirs(BUILD, exist_ok=True)
    p = subprocess.run(["javac", "-nowarn", "-cp", ":".join(jars), "-d", BUILD,
                        FUENTE], capture_output=True, text=True, timeout=900)
    v("el fuente compila contra los JARs de esta maquina",
      p.returncode == 0 and os.path.isfile(os.path.join(BUILD, "DumpDecomp.class")),
      p.stderr[-200:] if p.returncode else "DumpDecomp.class")

print()
print("=" * 74)
print("B) INVARIANTES del argv (lo que costara tres experimentos)")
print("=" * 74)

# MEDIDO: dosextractores ingenuos fallan aqui, y por motivos distintos.
#
#  1. `argv = [` a secas se queda con la RAMA DE FIXTURE
#     (`["<fixture>", fixture_json]`), que no es la invocacion real.
#  2. Una ventana de +-900 caracteres alrededor de `analyzeHeadless` TAMPOCO
#     sirve: entre `-import` y `-scriptPath` hay un bloque de comentario
#     largo que documenta por que la ruta es una sola, y empuja las dos
#     flags que se comprueban fuera de la ventana.
#
# Se extrae el LITERAL de la lista, desde su apertura hasta su cierre.
ini = src.find("argv = [os.path.join(GHIDRA_HOME")
fin = src.find("]\n", ini) if ini > 0 else -1
cuerpo = src[ini:fin + 1] if ini > 0 and fin > ini else ""
v("la invocacion real de analyzeHeadless existe", bool(cuerpo))
v("la invocacion importa el binario y pide el fuente",
  "-import" in cuerpo and "DumpDecomp.class" not in cuerpo)

# Regla 1: se pasa el FUENTE, no la clase
ps = re.search(r'"-postScript",\s*([A-Za-z_][\w.]*)', cuerpo)
nombre_post = ps.group(1) if ps else ""
v("REGLA 1: -postScript usa el .java, no el .class",
  nombre_post == "POSTSCRIPT", nombre_post or "(no encontrado)")
v("REGLA 1: la clase no se pasa a -postScript",
  not re.search(r'"-postScript",\s*CLASE', src))
v("POSTSCRIPT apunta al fuente",
  re.search(r'POSTSCRIPT\s*=\s*os\.path\.basename\(FUENTE\)', src) is not None)

# Regla 2: una sola ruta
sp = re.search(r'"-scriptPath",\s*([^\n]+)', cuerpo)
linea = (sp.group(1).strip().rstrip(",") if sp else "")
valor = linea.strip('"')
v("REGLA 2: -scriptPath recibe UNA sola ruta (sin os.pathsep)",
  "os.pathsep" not in linea, linea)
v("REGLA 2: la ruta es SCRIPTS, no SCRIPTS:BUILD",
  valor == "SCRIPTS", valor)

# Regla 3: la precompilacion sigue siendo chequeo, no parte del argv.
#
# MEDIDO al escribir este check: `BUILD` SI aparece dentro del literal del
# argv, porque el comentario que explica por que NO se pone `BUILD` en la
# ruta menciona la palabra. Buscar texto sin quitar comentarios mide el
# comentario, no el codigo. Un check que falla por su propia documentacion
# es un check que empuja a borrar la explicacion.
codigo = "\n".join(l for l in cuerpo.splitlines()
                   if l.strip() and not l.strip().startswith("#"))
v("REGLA 3: BUILD no aparece en el CODIGO de la invocacion",
  "BUILD" not in codigo)
v("REGLA 3: la precompilacion se sigue invocando",
  "compilar()" in src)
v("REGLA 3: Ghidra compila el fuente el mismo (el .class no viaja)",
  nombre_post == "POSTSCRIPT" and "DumpDecomp.class" not in codigo)

print()
print("=" * 74)
print("C) EJECUCION REAL (lenta) y D) TRAZABILIDAD")
print("=" * 74)
dbdir = tempfile.mkdtemp(prefix="gh003_")
DB = os.path.join(dbdir, "d.sqlite3")
env = {**os.environ, "PYTHONPATH": PKG + ":" + RXRE, "RXRE_DB": DB}
req = {"op": "run", "capability": "binary.decompile", "artefacto": "/bin/ls",
       "backend_id": "ghidra", "max_funcs": 1, "timeout": 1500}
t0 = time.time()
p = subprocess.run([sys.executable, MAQUINA], input=json.dumps(req) + NL,
                   capture_output=True, text=True, timeout=1700, env=env)
dur = time.time() - t0
if not p.stdout.strip():
    v("C: la superficie responde", False, p.stderr[-200:])
else:
    a = json.loads(p.stdout.strip().splitlines()[0])
    print("   status=%s exit=%s %.1fs n_functions=%s n_decompiladas=%s"
          % (a.get("status"), (a.get("ejecucion") or {}).get("exit_status"),
             dur, a.get("n_functions"), a.get("n_decompiladas")))
    v("C: Ghidra ejecuta y responde ok", a.get("status") == "ok",
      (a.get("limitations") or [""])[0][:110])
    res = a.get("results") or []
    v("C: hay pseudocodigo", len(res) > 0, "%d resultados" % len(res))
    if res:
        c = (res[0].get("value") or {}).get("c") or ""
        # FIRMA del decompilador de Ghidra. Un fixture no la produce por
        # casualidad; una variable inventada, tampoco.
        firma = ("undefined" in c and ("param_" in c or "local_" in c)
                 and ("uVar" in c or "iVar" in c or "code" in c
                      or "DAT_" in c or "stack_" in c))
        v("C: el pseudocodigo es del decompilador de Ghidra", firma,
          "%d lineas" % c.count("\n"))
        v("C: el ancho y la linea se conservan",
          (res[0].get("value") or {}).get("c_lineas", 0) > 10,
          "c_lineas=%s" % (res[0].get("value") or {}).get("c_lineas"))
    v("D: persistido", a.get("persistido") is True, str(a.get("persistido")))
    v("D: hay operation_id", bool(a.get("operation_id")), a.get("operation_id"))
    if res:
        q = subprocess.run([sys.executable, MAQUINA],
                           input=json.dumps({"op": "explain",
                                             "result_id": res[0]["result_id"]}) + NL,
                           capture_output=True, text=True, timeout=180, env=env)
        e = json.loads(q.stdout.strip().splitlines()[0]) if q.stdout.strip() else {}
        v("D: explain reconstruye la decompilacion",
          e.get("status") == "ok", e.get("status"))
    import sqlite3
    cn = sqlite3.connect(DB)
    try:
        n_op = cn.execute("SELECT count(*) FROM operations").fetchone()[0]
        n_re = cn.execute("SELECT count(*) FROM results").fetchone()[0]
    finally:
        cn.close()
    v("D: la evidencia fue a la base PEDIDA",
      n_op >= 1 and n_re >= 1, "operations=%d results=%d" % (n_op, n_re))
shutil.rmtree(dbdir, ignore_errors=True)

print()
print("=" * 74)
print("E) RUTAS DE FALLO (baratas, sin arrancar Ghidra)")
print("=" * 74)
dbdir = tempfile.mkdtemp(prefix="gh003b_")
env2 = {**os.environ, "PYTHONPATH": PKG + ":" + RXRE,
        "RXRE_DB": os.path.join(dbdir, "d.sqlite3")}
casos = [
    ("no existe el artefacto", "/no/existe/esta/de/aqui", "invalid_input"),
    ("no es ELF", "/etc/hostname", "invalid_input"),
]
for etiqueta, art, esperado in casos:
    q = subprocess.run([sys.executable, MAQUINA],
                       input=json.dumps({"op": "run", "capability": "binary.decompile",
                                         "artefacto": art}) + NL,
                       capture_output=True, text=True, timeout=300, env=env2)
    r = json.loads(q.stdout.strip().splitlines()[0]) if q.stdout.strip() else {}
    v("E: %s -> %s" % (etiqueta, esperado), r.get("status") == esperado,
      r.get("status"))
shutil.rmtree(dbdir, ignore_errors=True)

print()
print("=" * 74)
fallos = [o for o in ok + no_ejecutado if o.startswith("FAIL")]
for o in ok + no_ejecutado:
    print("  %s" % o)
print("=" * 74)
print("  %d/%d" % (len(ok) - len(fallos), len(ok) + len(no_ejecutado)))
sys.exit(1 if fallos else 0)