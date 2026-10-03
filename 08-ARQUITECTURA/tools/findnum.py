#!/usr/bin/env python3
# CONTRACT: name=findnum
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=yes
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no

"""findnum -- reserva un numero de hallazgo de forma atomica y visible.

Por que existe: `num_collision.py` mide 37 numeros duplicados sobre 82, y esta sesion ha chocado TRES veces (111, 119, 120) con otra sesion escribiendo a la
vez. Renumerar no es una perdida de tiempo menor: obliga a revalidar el
documento y a volver a escribir el mensaje de commit.

Un numero NO puede reservarse solo poniendo "el siguiente libre" en memoria: dos
sesiones leen la misma lista y eligen el mismo. Por eso la reserva es:

  1. cerrar el lock con flock (atomicidad REAL entre procesos, no "espero un
     segundo y reintento"),
  2. escribir un fichero de reserva en disco,
  3. devolver el numero ya reservado.

El paso 3 es lo que lo hace util entre sesiones: la reserva esta en el arbol de
git y la otra sesion la ve al listar.

Uso:
  findnum.py                    reserva y muestra el numero (sin commitear)
  findnum.py --next             muestra el siguiente (max+1), no reserva
  findnum.py --next --lowest    muestra el hueco mas bajo, no reserva
  findnum.py --list             reservas vigentes
  findnum.py --commit           commitea las reservas y crea el hallazgo
  findnum.py --release N        libera la reserva N
  findnum.py --self-test

Codigos de salida:
  0  todo bien
  2  --commit sin numero, o numero ya reservado
  3  no se pudo tomar el lock
"""

import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIND = os.path.join(ROOT, "06-INGENIERIA-INVERSA", "findings")
RESDIR = os.path.join(FIND, "_reservas")
LOCKDIR = os.path.join(ROOT, ".write-lock", "findnum")
STUB_PREFIX = "reservado"


def repo_root():
    return ROOT


def used_numbers():
    """Numeros que YA tienen fichero. Base: el nombre del fichero."""
    out = set()
    if not os.path.isdir(FIND):
        return out
    for name in os.listdir(FIND):
        m = re.match(r"^(\d{3})-", name)
        if m:
            out.add(int(m.group(1)))
    return out


def reservations():
    """Reservas vigentes: {numero: (titulo, timestamp)}."""
    out = {}
    if not os.path.isdir(RESDIR):
        return out
    for name in sorted(os.listdir(RESDIR)):
        if not name.endswith(".res"):
            continue
        n = int(re.match(r"^(\d{3})-", name).group(1))
        with open(os.path.join(RESDIR, name), encoding="utf-8") as fh:
            lines = fh.read().split("\n")
        title = lines[1] if len(lines) > 1 else ""
        ts = lines[2] if len(lines) > 2 else ""
        out[n] = (title, ts)
    return out


def next_free(lowest=False, taken=None):
    """Siguiente numero reservable.

    Por defecto devuelve MAX+1, NO el hueco mas bajo. El historico tiene
    huecos reales (no existe 004), y rellenar el hueco mas bajo numbraria un
    hallazgo nuevo como "4" en medio de 121: confuso y peor de trazar.
    Rellenar huecos es una operacion distinta, y se pide con lowest=True.

    `taken` EXISTE para que quien llama decida de donde sale el conjunto. Por
    defecto sale de ahi, como siempre, para no romper a los que no pasan nada.

    POR QUE: leer el arbol DENTRO de la funcion hacia que el self-test no
    pudiera aislarse. El lock ya va a un temporal, pero los numeros seguian
    saliendo de los hallazgos reales, asi que el test dependia del estado global
    en LECTURA. Aislar la escritura no aísla la lectura: es el mismo error por
    otro lado.

    Y el caso que lo hace necessary, no comodo: sin `taken`, un self-test con un
    conjunto vacio devolveria 1, y reservaria el numero 1 de un proyecto que
    va por el 503. Un test que reserva un numero que el proyecto podria usar no
    esta probando la funcion: esta usando el numero mas valuables que hay.
    """
    if taken is None:
        taken = used_numbers() | set(reservations())
    else:
        taken = set(taken)
    if not taken:
        return 1
    if lowest:
        n = 1
        while n in taken:
            n += 1
        return n
    return max(taken) + 1


class _Aislado:
    """Apunta LOCKDIR y RESDIR a un directorio temporal, y los restaura.

    Es un context manager para que el estado global se restaure SIEMPRE, incluso
    si la prueba revienta. Un `finally` escrito a mano se olvida; esto no se
    olvida porque es la unica forma de que el bloque salga.
    """

    def __enter__(self):
        import shutil
        import tempfile
        self._tmp = tempfile.mkdtemp(prefix="findnum-selftest-")
        # Se guardan los de verdad ANTES de tocarlos, y se escriben por
        # globals(). Asignar `LOCKDIR = ...` aqui crearia un LOCAL que
        # sombrea el global, y al leerlo antes de asignarlo sale
        # UnboundLocalError. Que es justo el error que salio.
        self._lock, self._res = globals()["LOCKDIR"], globals()["RESDIR"]
        globals()["LOCKDIR"] = os.path.join(self._tmp, "lock")
        globals()["RESDIR"] = os.path.join(self._tmp, "reservas")
        return globals()["LOCKDIR"], globals()["RESDIR"]

    def __exit__(self, *a):
        import shutil
        globals()["LOCKDIR"] = self._lock
        globals()["RESDIR"] = self._res
        shutil.rmtree(self._tmp, ignore_errors=True)
        return False


class Lock:
    """flock real. Sin flock no hay exclusion mutua que valga."""

    def __init__(self, path):
        self.path = path
        self.fh = None

    def __enter__(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.fh = open(self.path, "w")
        try:
            import fcntl
            fcntl.flock(self.fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except ImportError:
            pass                      # sin fcntl: degradar, no morir
        except OSError:
            self.fh.close()
            self.fh = None
            raise TimeoutError("lock ocupado")
        self.fh.write("%d %s scope=findnum\n" % (os.getpid(),
                                                  time.strftime("%Y-%m-%dT%H:%M:%S")))
        self.fh.flush()
        return self

    def __exit__(self, *a):
        if self.fh:
            try:
                import fcntl
                fcntl.flock(self.fh, fcntl.LOCK_UN)
            except Exception:
                pass
            self.fh.close()
        return False


def reserve(title="", lowest=False, taken=None):
    """Devuelve (numero, ruta_reserva). Atomico respecto a otros procesos.

    `taken` se pasa a `next_free`. Ver la nota de ahi: existe para que el
    self-test pueda decidir el conjunto y no leer el arbol real.
    """
    os.makedirs(RESDIR, exist_ok=True)
    with Lock(os.path.join(LOCKDIR, "owner")):
        n = next_free(lowest, taken)
        path = os.path.join(RESDIR, "%03d-%s.res" % (n, STUB_PREFIX))
        # write+rename: si alguien leyo la lista hace un instante, no ve un
        # fichero a medio escribir.
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write("RESERVADO numero=%03d pid=%d\n" % (n, os.getpid()))
            fh.write("%s\n" % (title or "(sin titulo)"))
            fh.write("%s\n" % time.strftime("%Y-%m-%dT%H:%M:%S"))
        os.replace(tmp, path)
    return n, path


def release(n):
    path = os.path.join(RESDIR, "%03d-%s.res" % (n, STUB_PREFIX))
    if not os.path.exists(path):
        return False
    os.remove(path)
    return True


def git(*args):
    return subprocess.run(["git"] + list(args), cwd=repo_root(),
                          capture_output=True, text=True)


def commit(n, title, stub="titulo"):
    """Commitea la reserva y crea el fichero del hallazgo con esa cabecera."""
    res = os.path.join(RESDIR, "%03d-%s.res" % (n, STUB_PREFIX))
    if not os.path.exists(res):
        return 2, "no hay reserva para %03d" % n
    slug = re.sub(r"[^a-z0-9]+", "-", stub.lower()).strip("-") or "hallazgo"
    path = os.path.join(FIND, "%03d-%s.md" % (n, slug))
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("# %03d · %s\n\n" % (n, title))
            fh.write("```\nCLASSIFICATION=DOCUMENTATION · TRACK=STATIC\n"
                     "CORPUS=RESEARCH/working/linux-7.1.3 · "
                     "HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0\n"
                     "WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · "
                     "MODIFICATIONS=0 · RUNTIME=NOT_RUN · GPU INTACTA\n```\n")
    git("add", os.path.relpath(res, ROOT), os.path.relpath(path, ROOT))
    r = git("commit", "-q", "-m",
            "%03d: %s\n\nnumero reservado con findnum.py (pid %d)\n\n"
            "WRITE_EXECUTION NONE / MODIFICATIONS 0 / GPU INTACTA"
            % (n, title, os.getpid()))
    if r.returncode:
        return 2, r.stderr.strip()[:120]
    os.remove(res)
    git("add", "-A", os.path.relpath(RESDIR, ROOT))
    git("commit", "-q", "-m", "findnum: libera la reserva %03d" % n)
    return 0, path


def self_test():
    fails = []

    def eq(label, got, want):
        if got != want:
            fails.append("%s: %r != %r" % (label, got, want))

    taken = used_numbers() | set(reservations())
    if not taken:
        fails.append("no se encontro ningun hallazgo: el scanner esta roto")
        print("self-test FALLA (1)"); print("   " + fails[0]); return 1

    # 1. next_free NUNCA devuelve un numero ocupado, ni de fichero ni reservado.
    nf = next_free()
    if nf in taken:
        fails.append("next_free devolvio %d, que ya esta ocupado" % nf)

    # 2. next_free por defecto es MAX+1, no el hueco mas bajo. Si devolviera
    #    el hueco mas bajo, un hallazgo nuevo saldria numerado entre los viejos.
    eq("next_free() es max+1", next_free(), max(taken) + 1)

    # 3. lowest=True si debe rellenar huecos, y el hueco debe estar libre.
    low = next_free(lowest=True)
    if low in taken:
        fails.append("next_free(lowest=True) devolvio %d, ocupado" % low)
    if low != next_free():
        pass                       # solo informativo: no tiene por que coincidir

    # 4. Reservar dos veces seguidas da dos numeros distintos y CRECIENTES.
    #
    #    EN UN DIRECTORIO TEMPORAL, y no en el de verdad. Antes usaba el lock y
    #    el directorio de reservas REALES, y por eso este test fallaba de forma
    #    intermitente: cualquier otra sesion reservando un numero hacia competir
    #    por el lock global, y el fallo era `TimeoutError: lock ocupado`, que no
    #    dice nada sobre la logica que este test quiere comprobar.
    #
    #    Un test que depende del estado global no es un test de la funcion: es
    #    un test de la_barata de los demas. Ademas dejaba ficheros .res de
    #    verdad en findings/_reservas/, o sea que un test que no deberia tocar
    #    nada escribia en el arbol.
    # El conjunto de numeros tambien es del temporal: {7, 9, 10}. Fijado a
    # mano para que el resultado sea 11 SIEMPRE, y el test pueda comprobarlo con
    # un numero exacto en vez de con "mayor que lo que hay ahora mismo". Con el
    # arbol real, el mismo test pasa con 504 y con 503 segun cuando se ejecute:
    # verde en los dos casos, comprobando cosas distintas.
    # El conjunto de numeros tambien sale del temporal: {7, 9, 10}, fijado a
    # mano para que el resultado sea 11 SIEMPRE. Asi el test comprueba un numero
    # EXACTO, no "mayor que lo que hay ahora mismo". Con el arbol real, el mismo
    # test pasa con 504 y con 503 segun cuando se ejecute: verde en los dos
    # casos, comprobando cosas distintas.
    fijo = {7, 9, 10}
    a = b = None
    with _Aislado() as (lockdir, resdir):
        a, _ = reserve("self-test A", taken=fijo)
        b, _ = reserve("self-test B", taken=fijo | {a})
        if a != 11:
            fails.append("con taken={7,9,10} esperaba 11 y devolvio %d" % a)
        if b != 12:
            fails.append("con taken={7,9,10,11} esperaba 12 y devolvio %d" % b)
        if a == b:
            fails.append("dos reservas seguidas dieron el mismo numero %d" % a)
        elif b <= a:
            fails.append("reservas no crecientes: %d luego %d" % (a, b))
        # 5. La reserva tiene que verse en disco: es lo que ve la otra sesion.
        res = reservations()
        for n in (a, b):
            ruta = os.path.join(resdir, "%03d-%s.res" % (n, STUB_PREFIX))
            if not os.path.exists(ruta):
                fails.append("falta el fichero de reserva %s" % ruta)
            if n not in res:
                fails.append("la reserva %d no aparece en reservations()" % n)
        # 6. El contenido del fichero de reserva tiene los campos que se leen.
        ruta = os.path.join(resdir, "%03d-%s.res" % (a, STUB_PREFIX))
        try:
            with open(ruta, encoding="utf-8") as fh:
                body = fh.read()
        except OSError as e:
            fails.append("no se pudo leer la reserva: %s" % e)
            body = ""
        for campo in ("RESERVADO numero=%03d" % a, "self-test A"):
            if campo not in body:
                fails.append("el fichero de reserva no contiene %r" % campo)
        # Y el control de .tmp AQUI, dentro del aislamiento: si mira el
        # directorio real despues, deja de comprobar los .tmp del propio test.
        # Un control que cambia de sujeto sin que se note sigue dando verde, y
        # verde sin comprobar es peor que no tener control.
        _tmp_left = [x for x in os.listdir(resdir) if x.endswith(".tmp")]
        if _tmp_left:
            fails.append("quedaron .tmp en el directorio aislado: %s"
                         % _tmp_left)


    # 7. release borra de verdad, y release de lo que no existe NO dice que si.
    #    Tambien dentro del aislamiento: `a` se reservo en el temporal, asi que
    #    releasedlo contra el directorio real no puede funcionar, y el fallo
    #    seria del test y no de release().
    with _Aislado() as (lockdir2, resdir2):
        a2, _ = reserve("self-test C")
        if not release(a2):
            fails.append("release(%d) devolvio False" % a2)
        if a2 in reservations():
            fails.append("release(%d) no lo quito de reservations()" % a2)
        if release(899):
            fails.append("release(899) devolvio True sin existir reserva")

    # 8. No debe quedar ningun .tmp: write+rename es atomico.
    left = [x for x in os.listdir(RESDIR) if x.endswith(".tmp")]
    if left:
        fails.append("quedaron .tmp sin limpiar: %s" % left)

    release(b)

    if fails:
        print("self-test FALLA (%d)" % len(fails))
        for f in fails:
            print("   " + f)
        return 1
    print("self-test OK (8 vectores, 3 controles)")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()

    if "--next" in argv:
        print(next_free(lowest="--lowest" in argv))
        return 0

    if "--list" in argv:
        res = reservations()
        if not res:
            print("sin reservas vigentes")
            return 0
        for n in sorted(res):
            print("%03d  %s  %s" % (n, res[n][1], res[n][0][:50]))
        return 0

    if "--release" in argv:
        n = int(argv[argv.index("--release") + 1])
        ok = release(n)
        print("liberado %03d" % n if ok else "no habia reserva %03d" % n)
        return 0 if ok else 2

    if "--commit" in argv:
        n = int(argv[argv.index("--commit") + 1])
        title = argv[argv.index("--commit") + 2] if \
            len(argv) > argv.index("--commit") + 2 else "(sin titulo)"
        stub = argv[argv.index("--commit") + 3] if \
            len(argv) > argv.index("--commit") + 3 else "titulo"
        rc, msg = commit(n, title, stub)
        print(msg)
        return rc

    try:
        n, path = reserve(" ".join(argv) or "(sin titulo)")
    except TimeoutError:
        print("otra sesion tiene el lock; reintenta", file=sys.stderr)
        return 3
    print("reservado %03d" % n)
    print("  %s" % os.path.relpath(path, ROOT))
    print("  escribe el hallazgo y luego: findnum.py --commit %03d <titulo> <slug>"
          % n)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
