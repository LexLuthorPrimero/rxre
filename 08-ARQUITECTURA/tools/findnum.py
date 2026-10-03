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
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIND = os.path.join(ROOT, "06-INGENIERIA-INVERSA", "findings")
RESDIR = os.path.join(FIND, "_reservas")
LOCKDIR = os.path.join(ROOT, ".write-lock", "findnum")
STUB_PREFIX = "reservado"


def repo_root():
    return ROOT


def used_numbers(directorio=None):
    """Numeros que YA tienen fichero. Base: el nombre del fichero.

    `directorio` existe para que el self-test no lea el arbol real. Es la parte
    de LECTURA que faltaba aislar cuando se aislo la escritura: sin esto, el
    test aislaba donde escribe y seguia leyendo de verdad.
    """
    out = set()
    base = directorio or FIND
    if not os.path.isdir(base):
        return out
    for name in os.listdir(base):
        # \d{3,} y NO \d{3}. Un ancho de tres es un ancho EXACTO: en cuanto aparezca
        # la nota 1000, "1000-algo.md" deja de casar y used_numbers deja de verla, con
        # lo cual next_free vuelve a entregar un numero que ya existe. El fallo es
        # silencioso -- la herramienta responde, y responde mal -- y solo se manifiesta
        # al cruzar los 999, que es cuando ya hay 1000 notas escritas y citas que romper.
        #
        # Y el stub usa "%03d", que es un ancho MINIMO y por tanto no sufre. La
        # incoherencia estaba entre las dos mitades de la misma idea de "numeros de
        # nota", y por eso la mitad de escritura y la de lectura no decian lo mismo.
        m = re.match(r"^(\d{3,})-", name)
        if m:
            out.add(int(m.group(1)))
    return out


# El registro del otro allocator.  MEDIDO 2026-10-03: hay DOS herramientas que
# reservan numeros de hallazgo y cada una con su propio registro, y ninguna ve
# las reservas de la otra:
#
#   tools/nextnum.py                  -> .nextnum.lock            43 reservas
#   08-ARQUITECTURA/tools/findnum.py  -> findings/_reservas/*.res   5 reservas
#
# Las dos leen el directorio de hallazgos, asi que un numero CON fichero se ve
# ocupado por las dos.  El hueco es la ventana entre "reservado" y "fichero
# escrito", que es justo la ventana para la que existe una reserva.  Y dos
# hallazgos con el mismo numero son los 74 que ya hay:  aqui esta su fuente.
LOCK_AJENO = os.path.join(ROOT, ".nextnum.lock")


def _reservas_del_registro_ajeno() -> dict:
    """Reservas que hizo `tools/nextnum.py`, en formato {numero: (titulo, "")}.

    Su registro es una linea por numero, sin titulo ni fecha, asi que las dos
    titulos se inventan como cadenas vacias: lo que se necesita de el es SOLO la
    ocupacion, que es un dato que no depende de la forma del registro.
    """
    out = {}
    try:
        with open(LOCK_AJENO, encoding="utf-8", errors="replace") as fh:
            for l in fh:
                l = l.strip()
                # \d{3,} y NO \d{3}:  un ancho de tres es EXACTO, y por eso
                # los numeros de cuatro digitos no se verian nunca.
                if re.match(r"^\d{3,}$", l):
                    out[int(l)] = ("", "")
    except OSError:
        pass
    return out


def reservations():
    """Reservas vigentes: {numero: (titulo, timestamp)}.

    Incluye las del otro allocator.  MEDIDO 2026-10-03: antes de esto, este
    modulo ciaba 5 reservas y habia 48 en el arbol;  las otras 43 eran
    invisibles para el, que es el unico caso en que una reserva puede servir de
    algo.
    """
    out = dict(_reservas_del_registro_ajeno())
    if not os.path.isdir(RESDIR):
        return out
    for name in sorted(os.listdir(RESDIR)):
        if not name.endswith(".res"):
            continue
        # \d{3,} y NO \d{3}. Este es el MISMO fallo que `used_numbers()` ya
        # corrigio mas abajo en este fichero, y que se manifesto como un fallo de
        # run_all el 2026-10-03: `.nextnum.lock` tiene una reserva `298` cuyo
        # fichero de hallazgo ya no existe, y al cruzarse con un nombre de
        # cuatro digitos, `re.match` devolvio None y `.group(1)` levanto
        # AttributeError. El self-test murio antes de empezar.
        #
        # Un ancho de tres es un ancho EXACTO. La mitad de lectura de este
        # fichero ya lo dice en `used_numbers()`, y `reservations()` no lo
        # decia: la incoherencia estaba entre las dos mitades de la misma idea.
        m = re.match(r"^(\d{3,})-", name)
        if not m:
            continue
        n = int(m.group(1))
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


FIND_AISLADO = None
_AISLADO = False


class _Aislado:
    """Apunta LOCKDIR y RESDIR a un directorio temporal, y los restaura.

    Es un context manager para que el estado global se restaure SIEMPRE, incluso
    si la prueba revienta. Un `finally` escrito a mano se olvida; esto no se
    olvida porque es la unica forma de que el bloque salga.

    LOCK_AJENO entra aqui por lo mismo, y porque el self-test lo demostrara:
    al empezar a leer el registro del otro allocator se olvido de aislarlo, y
    dos vectores devolvieron 1026 en vez de 11 y 12.  El sintoma parecia un
    cambio de comportamiento de `next_free()`, y no lo era: era una lectura del
    estado global real colandose en un test que se creia aislado.

    O sea: aislar la escritura no aisla la lectura, y el arreglo de arriba
    anadio una lectura mas.  El self-test lo dijo, que es para lo que existe.
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
        self._ajeno = globals()["LOCK_AJENO"]
        # El registro ajeno se copia a un temporal VACIO, no se apunta al
        # original:  si se apunta, el test depende otra vez del estado global.
        globals()["LOCK_AJENO"] = os.path.join(self._tmp, "ajeno.lock")
        open(globals()["LOCK_AJENO"], "w").close()
        self._find = FIND_AISLADO
        globals()["FIND_AISLADO"] = os.path.join(self._tmp, "hallazgos")
        os.makedirs(globals()["FIND_AISLADO"], exist_ok=True)
        globals()["_AISLADO"] = True
        globals()["LOCKDIR"] = os.path.join(self._tmp, "lock")
        globals()["RESDIR"] = os.path.join(self._tmp, "reservas")
        return globals()["LOCKDIR"], globals()["RESDIR"]

    def __exit__(self, *a):
        globals()["LOCK_AJENO"] = self._ajeno
        import shutil
        globals()["LOCKDIR"] = self._lock
        globals()["RESDIR"] = self._res
        globals()["FIND_AISLADO"] = self._find
        globals()["_AISLADO"] = False
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
        # SIEMPRE se une el estado real, pase lo que pase con `taken`.
        #
        # Sin esta union, dos reservas con el MISMO taken elegian el mismo
        # numero y la segunda SOBRESCRIBIA el fichero de la primera, perdiendo
        # su titulo en silencio. Medido:
        #     primera -> 011   segunda -> 011   mismo fichero
        #     queda: "titulo-B", el titulo-A desaparece
        # El flock serializa igual; lo que faltaba era la informacion que hace
        # unica la operacion. Un candado que protege la seccion critica pero no
        # el estado que la define no protege la operacion.
        #
        # `taken` puede AÑADIR informacion (el test fija {7,9,10}), nunca
        # sustituirla.
        real = used_numbers(FIND if not _AISLADO else FIND_AISLADO) \
            | set(reservations())
        n = next_free(lowest, real | set(taken or ()))
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


def _vector_registro_ajeno(tmp_lock):
    """La reserva del otro allocator tiene que verse desde aqui.

    Sin este vector, quitar `_reservas_del_registro_ajeno()` no rompe NADA del
    self-test:  `reservations()` volveria a 5 entradas, `next_free()` volveria a
    dar los mismos numeros, y todo pasaria.  Es decir, el arreglo se podria
    deshacer sin que nadie se entere, que es la forma mas habitual de que un
    arreglo no exista.
    """
    with open(tmp_lock, "w", encoding="utf-8") as fh:
        fh.write("1021\n1022\n")
    try:
        r = reservations()
        if 1021 not in r or 1022 not in r:
            return "las reservas del registro ajeno no se ven: %r" % (sorted(r)[-3:],)
        if next_free(taken=set(r) | {1025}) != 1026:
            return "next_free ignora la reserva ajena"
    finally:
        open(tmp_lock, "w").close()
    return None


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

    # --- los numeros de cuatro digitos -------------------------------------
    # El fallo era silencioso: la herramienta respondia, y respondia mal. Un caso que
    # solo mira el self-test con numeros de tres digitos no lo puede ver, asi que el
    # vector tiene que traer un numero de cuatro aunque el arbol real todavia no tenga
    # ninguno. Por eso este caso escribe sus propios ficheros en un temporal en vez de
    # mirar el arbol: el arbol no tiene 1000 todavia, y el fallo aparece cuando llegue.
    with tempfile.TemporaryDirectory() as d4:
        for nm in ("999-a.md", "1000-b.md", "1001-c.md"):
            open(os.path.join(d4, nm), "w").close()
        usados4 = used_numbers(d4)
        eq("used_numbers ve los de cuatro digitos", sorted(usados4), [999, 1000, 1001])
        eq("next_free no devuelve un 1000 que ya existe",
           next_free(taken=usados4), 1002)

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
        # 4b. DOS RESERVAS CON EL MISMO `taken` TIENEN QUE DAR NUMEROS
        #     DISTINTOS. Este control NO existia, y por eso el defecto de que
        #     `taken` sustituyera al estado de disco llego a commitearse: la
        #     suite pasaba mientras dos reservas con el mismo conjunto elegian
        #     el mismo numero y la segunda sobrescribia el titulo de la primera.
        #     Solo se vio probando a mano, y eso es exactamente lo que un
        #     self-test deberia evitar.
        c1, ruta_c1 = reserve("dup A", taken=fijo)
        c2, ruta_c2 = reserve("dup B", taken=fijo)
        if c1 == c2:
            fails.append("dos reservas con el MISMO taken dieron %d: taken"
                         " esta sustituir al estado de disco" % c1)
        if ruta_c1 == ruta_c2:
            fails.append("dos reservas con el MISMO taken escribieron el"
                         " mismo fichero: la segunda sobrescribe la primera")
        # Y el caso mas grave: que el titulo de la primera no desaparezca.
        cuerpo = ""
        try:
            with open(ruta_c1, encoding="utf-8") as fh:
                cuerpo = fh.read()
        except OSError as e:
            fails.append("no se pudo leer la reserva: %s" % e)
        if "dup A" not in cuerpo:
            fails.append("el titulo de la primera reserva se perdio: el"
                         " fichero contiene %r" % cuerpo.strip()[:60])

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

    # 9. CONTROL NEGATIVO DEL DESPACHO. Este es el vector que faltaba y que
    #    permitio el defecto: los vectores 1-8 prueban `next_free()` y
    #    `reserve()`, pero el fallo estaba ENTRE las dos, en como `main()`
    #    repartia argv. Con la version 1.1.0 este bloque entero daba verde:
    #    `main(["--selftest"])` devolvia 0 y habia escrito un fichero de reserva.
    #
    #    Se prueba dentro del aislamiento por la misma razon que el vector 4: un
    #    self-test que escribe en el arbol real es un self-test que ensucia.
    #    Y se comprueban LAS DOS MITADES por separado, porque una pasa sin la
    #    otra: que rc != 0 sin escribir nada, y que no aparezca ninguna reserva.
    with _Aislado() as (lockdir3, resdir3):
        # El uso se imprime por stderr en cada invocacion. Sin silenciarlo, ocho
        # pantallas de texto esconden el "self-test OK" que es lo que se lee.
        import contextlib
        _sink = open(os.devnull, "w")
        # El directorio de reservas puede no existir todavia: `_Aislado()` lo
        # apunta a un temporal nuevo y solo `reserve()` lo crea. Ausente ES el
        # estado de partida, asi que se registra como conjunto vacio en vez de
        # reventar. Y es el estado que MAS prueba da: si el directorio no existia
        # y al final existe, algo escribio.
        antes = set(os.listdir(resdir3)) if os.path.isdir(resdir3) else set()

        # (a) INVALIDAS: rc distinto de cero. `--selftest` y `--self` son los
        #     tokens que en el arbol real reservaron un numero cada uno.
        invalidas = (["--selftest"], ["--self"], ["-x"], ["--json"],
                    ["--release", "no-es-un-numero"], ["--commit"])
        with contextlib.redirect_stdout(_sink), contextlib.redirect_stderr(_sink):
            for argv_malo in invalidas:
                rc_malo = main(argv_malo)
                if rc_malo == 0:
                    fails.append("main(%r) devolvio 0: una opcion invalida tiene"
                                 " que fallar, no devolver exito" % (argv_malo,))

            # (b) VALIDAS: rc cero, y SIN escribir. `--help` es el caso donde
            #     solo falla la segunda mitad: antes imprimia el uso y aun asi
            #     reservaba.
            for argv_bueno in (["--help"], ["-h"]):
                if main(argv_bueno) != 0:
                    fails.append("main(%r) devolvio distinto de 0: --help es"
                                 " ayuda, no una entrada invalida"
                                 % (argv_bueno,))
        _sink.close()

        # (c) La mitad que importa: NINGUN token desconocido toco el disco.
        despues = set(os.listdir(resdir3)) if os.path.isdir(resdir3) else set()
        if despues != antes:
            fails.append("main() escribio en el directorio de reservas ante un"
                         " token que no es opcion: %s"
                         % sorted(despues - antes))

    release(b)

    # (d) El registro ajeno, dentro del aislamiento:  con un temporal con dos
    #     reservas, tienen que verse desde aqui.
    with _Aislado():
        prob = _vector_registro_ajeno(LOCK_AJENO)
        if prob:
            fails.append(prob)

    if fails:
        print("self-test FALLA (%d)" % len(fails))
        for f in fails:
            print("   " + f)
        return 1
    print("self-test OK (8 vectores, 4 controles)")
    return 0


VERSION = "1.2.0"

# MEDIDO 2026-10-03. `main()` solo conocia `--self-test`; TODO lo demas caia en
# `reserve(" ".join(argv))`. Consecuencia medida sobre el arbol real: 12 ficheros
# de reserva en findings/_reservas/ cuyo titulo es un flag --
# `--selftest`, `--self`, `--help` -- y que existen porque alguien ejecuto
#
#     findnum.py --selftest
#
# esperando un self-test. La herramienta RESERVO UN NUMERO, escribio el fichero
# y salio con rc=0 printing "reservado NNN". No fallo: fallo hacia adelante, y
# en la herramienta cuya unica razon de existir es que los numeros NO colisionen.
#
# El pool que hacia ese trabajo estaba contaminado por la propia herramienta.
# El self-test de esta version no podia verlo porque solo prova `next_free()` y
# `reserve()` por separado: el fallo estaba en el DESPACHO de argv, entre las dos.
#
# Por eso el arreglo no es "aceptar `--selftest` como alias". Aceptar el alias
# deja vivo el agujero: el proximo flag mal escrito vuelve a reservar. Lo que
# hace falta es que un token que empieza por `-` y no es una opcion CONOCIDA
# no pueda llegar a `reserve()`. Salida distinta de cero, mensaje que nombra las
# opciones, y CERO ficheros escritos.
KNOWN_OPCIONES = ("--self-test", "--next", "--lowest", "--list",
                  "--release", "--commit", "--help", "-h")


def uso(problema=None, token=None):
    if problema:
        print("findnum: %s" % problema, file=sys.stderr)
        if token is not None:
            print("  token recibido: %r" % token, file=sys.stderr)
            print("  NO se ha reservado ningun numero.", file=sys.stderr)
        print("", file=sys.stderr)
    print("uso:", file=sys.stderr)
    print("  findnum.py [<titulo>]              reserva un numero y lo muestra",
          file=sys.stderr)
    print("  findnum.py --next [--lowest]        muestra el siguiente, no reserva",
          file=sys.stderr)
    print("  findnum.py --list                   reservas vigentes", file=sys.stderr)
    print("  findnum.py --release N              libera la reserva N", file=sys.stderr)
    print("  findnum.py --commit N <titulo> <slug>", file=sys.stderr)
    print("  findnum.py --self-test              (con dos guiones, y 'test')",
          file=sys.stderr)
    print("  findnum.py --help", file=sys.stderr)
    return 2


def main(argv):
    # El guardia va ANTES de cualquier otra rama: si un flag desconocido puede
    # llegar al final, el final reserva.
    for tok in argv:
        if tok.startswith("-") and tok not in KNOWN_OPCIONES:
            cerca = [o for o in KNOWN_OPCIONES if o.lstrip("-").startswith(
                tok.lstrip("-")[:3])]
            msg = "opcion desconocida %r" % tok
            if cerca:
                msg += "; quiza querias %s" % " o ".join(cerca[:3])
            return uso(msg, tok)

    if "--help" in argv or "-h" in argv:
        # `uso()` devuelve 2 porque su caso normal es "no se que hacer con esto".
        # Pedir la ayuda no es un error de invocacion: es una invocacion valida.
        # Por eso el 0 va aqui y no dentro de `uso()`. La primera version de
        # este arreglo devolvia 2 tambien para --help, y lo caza el vector 9b.
        uso()
        return 0

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
        i = argv.index("--release")
        if i + 1 >= len(argv):
            return uso("--release necesita un numero")
        try:
            n = int(argv[i + 1])
        except ValueError:
            return uso("--release necesita un numero entero, no %r" % argv[i + 1])
        ok = release(n)
        print("liberado %03d" % n if ok else "no habia reserva %03d" % n)
        return 0 if ok else 2

    if "--commit" in argv:
        i = argv.index("--commit")
        if i + 1 >= len(argv):
            return uso("--commit necesita un numero")
        try:
            n = int(argv[i + 1])
        except ValueError:
            return uso("--commit necesita un numero entero, no %r" % argv[i + 1])
        title = argv[i + 2] if len(argv) > i + 2 else "(sin titulo)"
        stub = argv[i + 3] if len(argv) > i + 3 else "titulo"
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
