#!/usr/bin/env python3
"""git_sano.py — comprueba que el HISTORIAL de este repositorio se puede leer.

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · HARDWARE_SCOPE=N/A
VERSION=1.0.0
INVOCADO_POR=manual  ·  SELF_TEST_FLAG=--selftest

POR QUE EXISTE, Y QUE ESTA MEDIDO

  El repositorio tiene CINCO objetos sueltos de 0 bytes:

      $ find .git/objects -type f -size 0
      729ab738dea2c67c28e065abbab87ec373d47141
      4aebdccf2401289d61936c9b9b6afc79284af064
      f5a80d162be89c1046b4f09d70eb4af8a182cdfb
      499bffcbd6f36c3141f5c2497957e43f4e2c50d6
      01361a2b7a9c669ab7f1cb53f97b15b64c5640c6

  Un objeto de 0 bytes no se descomprime: la cadena termina a media secuencia.  No
  es el blob vacio legitimo de git  —e69de29bb2d1…, que esta bien formado—  sino un
  fichero truncado en disco.

  Y ESTO ES LO QUE HACE QUE LA PUERTA SEA NECESARIA:

      git fsck --connectivity-only                    rc=0   dice "error"
      git fsck --connectivity-only --no-dangling      rc=0   dice "error"
      git fsck --full                                 rc=3   dice "error"

  `--connectivity-only` es la bandera que se usa POR VELOCIDAD,  y es la que
  reporta la corrupcion en stderr y DEVUELVE CERO.  O sea:  la forma natural de
  usar fsck como puerta  —ejecutarlo y mirar el codigo de salida—  NO PUEDE
  FALLAR.  Imita exactamente al defecto que este proyecto lleva cinco commits
  corrigiendo:  un control cuyo codigo de salida no significa nada ocupando el
  sitio de un control.

POR QUE ESTA HECHA ASI,  Y NO CON UN `git fsck` Y YA

  · La cuenta de ficheros de 0 bytes la hace ESTE programa con os.stat(),  no la
    infiere del codigo de salida de git.  Es la misma disciplina que el resto del
    componente:  la medida la hace el instrumento.
  · Se usa `--full`  —que si distingue—  y NO `--connectivity-only`  —que no—.
    Y el motivo esta escrito aqui,  con los dos numeros medidos,  para que nadie
    "optimice" la bandera dentro de seis meses.
  · El codigo de salida DISTINGUE las dos cosas:  corrupcion  y  no-poder-leer.
    No son lo mismo y no deben tener el mismo codigo.

LO QUE ESTO NO COMPRUEBA,  DECLARADO

  · Los PACKS.  Aqui solo se cuentan objetos sueltos  —.git/objects/XX/…—.
    MEDIDO que fsck --full da los mismos 5,  de modo que los packs estan bien;
    pero eso es una medicion de esta sesion,  no una invariante del programa.
  · Si git esta ausente.  rc=5,  y se dice que es ausencia de herramienta  y no
    una garantia de salud.
  · Que el contenido de los objetos sea el que deberia.  Solo que se pueda LEER.

CODIGOS DE SALIDA
  0  sano:  cero objetos de 0 bytes  y  fsck no reporta corrupcion
  3  CORRUPTO:  hay objetos de 0 bytes,  o fsck --full lo confirma
  4  git no disponible  (entorno,  no salud del repositorio)
  5  no se pudo determinar
"""

import os
import subprocess
import sys

VERSION = "1.0.0"
TOOL = "git_sano.py"

# ── POR QUE --full Y NO --connectivity-only ──────────────────────────────────
# MEDIDO 2026-10-04 sobre este repositorio:
#     git fsck --connectivity-only               rc=0   14 lineas "esta vacio"
#     git fsck --connectivity-only --no-dangling rc=0    2 lineas "esta vacio"
#     git fsck --full                            rc=3    5 lineas "esta vacio"
#
# La bandera rapida dice "error" y sale con 0.  Usarla seria construir la puerta
# sobre el unico modo de fsck que NO puede fallar.
FSCK_FLAGS = ("--full",)

# Objetos sueltos = .git/objects/XX/yyyy…  (dos niveles, sin "pack" ni "info").
_LOOSE_SUFIJOS = 39  # longitud de "499bffcbd6f36c3141f5c2497957e43f4e2c50d6"


def objetos_vacios(repo):
    """Los objetos sueltos de tamano 0, contados aqui y no por fsck.

    MEDIDO que son 5.  Cada uno es un fichero que no se puede descomprimir, y
    eso es independiente de lo que fsck opine.
    """
    base = os.path.join(repo, ".git", "objects")
    if not os.path.isdir(base):
        return None
    out = []
    for d in sorted(os.listdir(base)):
        sub = os.path.join(base, d)
        if not os.path.isdir(sub) or len(d) != 2:
            continue
        for f in sorted(os.listdir(sub)):
            p = os.path.join(sub, f)
            try:
                if os.path.getsize(p) == 0:
                    out.append(d + f)
            except OSError:
                continue
    return out


def fsck(repo, timeout=180):
    """(rc, lineas-de-corrupcion).  rc None si git no se pudo ejecutar."""
    cmd = ["git", "fsck", "--no-progress"] + list(FSCK_FLAGS)
    try:
        r = subprocess.run(cmd, cwd=repo, capture_output=True,
                           text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None, []
    bajo = (r.stderr or "") + (r.stdout or "")
    malas = [l.strip() for l in bajo.splitlines()
            if "vac" in l and ("o" == l.strip()[-1:] or "empty" in l)]
    # MEDIDO que fsck escribe en stderr;  se leen las dos para no depender de eso.
    if not malas:
        malas = [l.strip() for l in bajo.splitlines() if l.startswith("error")]
    return r.returncode, malas


def medir(repo):
    vac = objetos_vacios(repo)
    if vac is None:
        return {"estado": "NO_REPO", "vacias": None, "fsck_rc": None,
                "fsck_lineas": []}
    rc, malas = fsck(repo)
    return {"estado": "MEDIDO", "vacias": vac, "fsck_rc": rc,
            "fsck_lineas": malas}


def main(argv):
    if "--selftest" in argv:
        return selftest()

    repo = "."
    if "--repo" in argv:
        i = argv.index("--repo")
        if i + 1 >= len(argv):
            print("%s: --repo necesita un argumento" % TOOL, file=sys.stderr)
            return 5
        repo = argv[i + 1]

    if "--version" in argv:
        print("%s %s" % (TOOL, VERSION))
        return 0

    m = medir(repo)

    if m["estado"] == "NO_REPO":
        print("%s: %s no tiene .git/objects  — no es un repositorio"
              % (TOOL, repo), file=sys.stderr)
        return 5

    vac = m["vacias"]
    print("%s %s  ·  %s" % (TOOL, VERSION, repo))
    print("  objetos sueltos de 0 bytes:  %d" % len(vac))
    for h in vac:
        print("      %s" % h)
    print("  git fsck %s:  rc=%s,  %d linea(s) de corrupcion"
          % (" ".join(FSCK_FLAGS), m["fsck_rc"], len(m["fsck_lineas"])))

    if m["fsck_rc"] is None:
        print("  VEREDICTO:  no se pudo determinar.  git no disponible o "
              "agotado el tiempo.  Esto NO es una garantia de salud.",
              file=sys.stderr)
        return 5

    if vac or m["fsck_rc"] != 0:
        print("  VEREDICTO:  CORRUPTO.  El historial NO es auditable.", file=sys.stderr)
        print("  Esto no lo arregla esta herramienta.  Reparar un objeto "
              "truncado cambia su SHA, y eso invalida cualquier referencia "
              "que lo contenga;  hay que decidir eso antes de tocarlo.", file=sys.stderr)
        print("  Y MEDIDO que `git gc` NO los toca:  la poda de objetos "
              "sueltos no-profundos esta fuera de su alcance.", file=sys.stderr)
        return 3

    print("  VEREDICTO:  sano.")
    return 0


def _arbol_temporal(base, con_objeto_roto):
    """Un repo real, con  un objeto de 0 bytes  si se le pide."""
    os.makedirs(os.path.join(base, "tools"), exist_ok=True)
    with open(os.path.join(base, "loquesea.txt"), "w") as fh:
        fh.write("contenido de prueba\n")
    r = subprocess.run(["git", "init", "-q", base], capture_output=True,
                       timeout=60)
    if r.returncode != 0:
        return False
    for cmd in (["git", "add", "-A"], ["git", "-c", "user.email=a@b",
                                       "-c", "user.name=c", "commit",
                                       "-q", "-m", "x"]):
        r = subprocess.run(cmd, cwd=base, capture_output=True, timeout=60)
        if r.returncode != 0:
            return False
    if con_objeto_roto:
        # Se localiza un objeto real y se trunca a 0 bytes.  Es la lesion exacta
        # del hallazgo 1039,  y se produce en lugar de fabricarse a mano para que
        # el vector pruebe la clase de fallo y no una imaginacion.
        objs = os.path.join(base, ".git", "objects")
        victim = None
        for d in sorted(os.listdir(objs)):
            sub = os.path.join(objs, d)
            if not os.path.isdir(sub) or len(d) != 2:
                continue
            for f in sorted(os.listdir(sub)):
                if os.path.getsize(os.path.join(sub, f)) > 0:
                    victim = os.path.join(sub, f)
                    break
            if victim:
                break
        if victim is None:
            return False
        # MEDIDO por el self-test:  los objetos de git se escriben en modo 0444,
        # de modo que abrirlos para truncar da PermissionError.  Hay que quitar
        # el permiso primero.  Es la segunda vez que este vector falla por un
        # motivo mio y no del hallazgo  —la primera fue el commit sin cambios—  y
        # las dos las ha encontrado el propio self-test,  que es para lo que
        # existe.
        os.chmod(victim, 0o644)
        with open(victim, "wb"):
            pass
    return True


def selftest():
    import tempfile
    print("%s %s -- self-test" % (TOOL, VERSION))
    print("  " + "-" * 62)
    fails = 0
    checks = 0

    print("  AVISO DE ALCANCE:  este self-test MODIFICA repositorios TEMPORALES")
    print("  que crea y destruye el.  No toca el repositorio del proyecto,  y no")
    print("  escribe en ningun sitio fuera de TMPDIR.  La comprobacion del")
    print("  repositorio REAL se hace aparte,  en modo normal.")

    # ── V1: repo limpio -> rc 0 ──────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as td:
        if not _arbol_temporal(td, False):
            print("  FAIL  no se pudo construir el repo temporal (git?)")
            return 1
        m = medir(td)
        checks += 1
        if m["vacias"] == [] and m["fsck_rc"] == 0:
            print("  OK    un repo sin objetos truncados mide 0 y fsck da 0")
        else:
            print("  FAIL  repo sano medido como %r / fsck rc=%r"
                  % (m["vacias"], m["fsck_rc"]))
            fails += 1

        # ── V2: el objeto truncado DEBE SER DETECTADO ────────────────────────
        # ESTE es el vector que la puerta necesita:  sin el, "vacias == []" no
        # distingue "no hay" de "no miro".
    # MEDIDO por el self-test en su PRIMERA ejecucion, y es un defecto mio:  este
    # bloque reutilizaba el temporal del vector V1,  y `git commit` sobre un
    # arbol ya confirmado devuelve 1  ("nothing to commit"),  de modo que la
    # inyeccion del objeto truncado NUNCA ocurria  y el vector no probaba nada.
    # Un vector que no puede correr es un vector que no puede fallar.
    with tempfile.TemporaryDirectory() as td2:
        if _arbol_temporal(td2, True):
            m = medir(td2)
            checks += 1
            if len(m["vacias"]) == 1 and m["vacias"][0]:
                print("  OK    un objeto truncado a 0 bytes SE DETECTA  (%s)"
                      % m["vacias"][0][:12])
            else:
                print("  FAIL  el objeto truncado NO se ha visto: %r"
                      % (m["vacias"],))
                fails += 1

            checks += 1
            rc_real = main(["--repo", td2])
            if rc_real == 3:
                print("  OK    la puerta devuelve 3 con corrupcion")
            else:
                print("  FAIL  la puerta devolvio %s con corrupcion" % rc_real)
                fails += 1
        else:
            print("  FAIL  no se pudo inyectar el objeto truncado")
            fails += 1
            checks += 2

    # ── V3: la bandera NO puede ser la que no distingue ──────────────────────
    # MEDIDO en el hallazgo:  --connectivity-only sale 0 con 14 lineas de
    # corrupcion.  Este vector comprueba que la constante de este programa NO es
    # esa,  sin necesidad de tener un repo corrupto.
    checks += 1
    if "--connectivity-only" not in FSCK_FLAGS:
        print("  OK    la puerta usa %s y no --connectivity-only, que sale 0"
              % " ".join(FSCK_FLAGS))
    else:
        print("  FAIL  la puerta usa --connectivity-only: sale 0 al reportar")
        fails += 1

    # ── V4: sin .git -> 5, y NO 0 ────────────────────────────────────────────
    # El control negativo del falso "sano":  si esto saliera 0, la puerta
    # valeria para un directorio que no es un repositorio.
    with tempfile.TemporaryDirectory() as td:
        checks += 1
        rc = main(["--repo", td])
        if rc == 5:
            print("  OK    un directorio sin .git devuelve 5, no 0")
        else:
            print("  FAIL  un directorio sin .git devolvio %s" % rc)
            fails += 1

    print("  " + "-" * 62)
    print("  %d checks, %d failures" % (checks, fails))
    print("RESULT: %s" % ("OK" if fails == 0 else "FAILED"))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
