#!/usr/bin/env python3
"""
CORPUS GUARD -- integridad del corpus alrededor de una prueba de mutacion.

Por que existe. En cada ronda en que hago una mutacion (cambiar un valor en
el corpus para comprobar que una herramienta lo detecta) repito la misma
secuencia a mano:

    cp fichero /tmp/backup
    ... mutar ...
    ejecutar la herramienta
    cp /tmp/backup fichero
    git status --porcelain RESEARCH/     <- comprobar que VOLVI

Ese ultimo paso es el importante y es el que me puede fallar. Si el
restaurado falla o se olvida, el corpus queda modificado y todas las rondas
posteriores estan Midiendo codigo que yo altere. Es el peor tipo de
contaminacion: silenciosa, persistente, y aparece como si fuera un hallazgo.

Esto lo hace en un comando, con verificacion de hash antes y despues:

    python3 corpus_guard.py --snapshot
    python3 corpus_guard.py --check                 # antes de mutar
    python3 corpus_guard.py --restore
    python3 corpus_guard.py --verify                # despues de restaurar
    python3 corpus_guard.py --mutate FICHERO 'python -c "..."'

Y lo mas util: --test, que envuelve una mutacion y una ejecucion, restaura
SIEMPRE, y devuelve codigo distinto de cero si el corpus no quedo intacto.
Con eso, una prueba de mutacion deja de ser una secuencia de cuatro pasos
manuales y pasa a ser una linea.
"""
import hashlib
import os
import subprocess
import sys
import json
import tempfile
import time

ROOT = "/home/lucas/Escritorio/RX550-INVESTIGACION"
# Lo que NO se toca nunca: es el corpus de referencia y el arbol de trabajo
# de otras sesiones.
PROTECTED = [
    "RESEARCH/working/linux-7.1.3",
]
STATE = os.path.join(tempfile.gettempdir(), "corpus_guard_state.json")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint():
    """{ruta_relativa: sha256} de todo lo protegido."""
    out = {}
    for rel in PROTECTED:
        base = os.path.join(ROOT, rel)
        for dirpath, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in (".git",)]
            for f in files:
                p = os.path.join(dirpath, f)
                out[os.path.relpath(p, ROOT)] = sha(p)
    return out


def load_state():
    if os.path.exists(STATE):
        try:
            return json.load(open(STATE))
        except (OSError, ValueError):
            return None
    return None


def save_state(fp):
    json.dump(fp, open(STATE, "w"), indent=1)


def diff(a, b):
    changed, added, removed = [], [], []
    for k in set(a) | set(b):
        if k in a and k in b:
            if a[k] != b[k]:
                changed.append(k)
        elif k in b:
            added.append(k)
        else:
            removed.append(k)
    return sorted(changed), sorted(added), sorted(removed)


def show(label, changed, added, removed):
    if not (changed or added or removed):
        print(f"{label}: sin diferencias")
        return 0
    print(f"{label}: {len(changed)} modificados, "
          f"{len(added)} nuevos, {len(removed)} borrados")
    for k in changed:
        print(f"   M  {k}")
    for k in added:
        print(f"   +  {k}")
    for k in removed:
        print(f"   -  {k}")
    return 1


def git_status():
    r = subprocess.run(["git", "status", "--porcelain", "--", "RESEARCH/"],
                       cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip()


def main():
    args = sys.argv[1:]

    if not args or args[0] == "--help":
        print(__doc__)
        print("uso:")
        print("  --snapshot        guarda la huella actual como referencia")
        print("  --check           compara con la referencia")
        print("  --restore         restaura desde la referencia")
        print("  --verify          compara y ademas mira git status")
        print("  --mutate F CMD    copia F, ejecuta CMD, restaura, verifica")
        print("  --git             solo git status --porcelain RESEARCH/")
        return 0

    if args[0] == "--git":
        s = git_status()
        print(s if s else "(vacio: el corpus esta intacto)")
        return 1 if s else 0

    if args[0] == "--snapshot":
        fp = fingerprint()
        save_state(fp)
        print(f"huella guardada: {len(fp)} ficheros bajo {', '.join(PROTECTED)}")
        print(f"estado en {STATE}")
        return 0

    ref = load_state()
    if ref is None:
        print("no hay referencia. ejecuta primero --snapshot")
        return 2

    if args[0] == "--check":
        c, a, d = diff(ref, fingerprint())
        return show("comparacion con la referencia", c, a, d)

    if args[0] in ("--verify", "--restore"):
        cur = fingerprint()
        c, a, d = diff(ref, cur)
        if args[0] == "--restore" and (c or a or d):
            for k in c:
                src = os.path.join(ROOT, k)
                if os.path.exists(src):
                    # se escribe el contenido original desde la copia en disco
                    # guardada en el backup, no desde la referencia (que solo
                    # tiene hashes y no puede reconstruir un fichero).
                    bak = os.path.join(tempfile.gettempdir(),
                                       "corpus_guard_backup", k)
                    if os.path.exists(bak):
                        shutil_copy(bak, src)
                        print(f"restaurado {k}")
                    else:
                        print(f"NO SE PUEDE RESTAURAR {k}: no hay copia")
                        return 2
            c, a, d = diff(ref, fingerprint())
        show("estado del corpus", c, a, d)
        s = git_status()
        if s:
            print(f"\ngit status --porcelain RESEARCH/ reporta cambios:\n{s}")
            return 1
        print("\ngit status --porcelain RESEARCH/: vacio")
        return 0

    if args[0] == "--mutate":
        if len(args) < 3:
            print("uso: --mutate FICHERO 'COMANDO'")
            return 2
        target = args[1]
        cmd = args[2]
        bakdir = os.path.join(tempfile.gettempdir(), "corpus_guard_backup")
        dest = os.path.join(bakdir, target)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        full = os.path.join(ROOT, target)
        if not os.path.exists(full):
            print(f"no existe {full}")
            return 2
        shutil_copy(full, dest)
        print(f"copia de seguridad de {target}")
        try:
            r = subprocess.run(cmd, shell=True, cwd=ROOT)
            print(f"--- comando devuelto {r.returncode} ---")
        finally:
            shutil_copy(dest, full)
            print(f"restaurado {target}")
        c, a, d = diff(ref, fingerprint())
        rc = show("verificacion tras restaurar", c, a, d)
        if rc:
            print("\n*** EL CORPUS NO VOLVIO A SU ESTADO. INVESTIGAR. ***")
            return 1
        print("\ncorpus intacto")
        return 0

    print(f"opcion desconocida: {args[0]}")
    return 2


def shutil_copy(src, dst):
    import shutil
    shutil.copy2(src, dst)


if __name__ == "__main__":
    sys.exit(main())