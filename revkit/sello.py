#!/usr/bin/env python3
"""
sello.py -- verifica el manifiesto de evidencia y lo mantiene al dia.

QUE ES ESTO
-----------
`docs/EVIDENCE-MANIFEST.sha256` sella 245 ficheros de los que depende
`docs/`. El proposito esta escrito en su primera linea: "la pregunta es si se
movio la EVIDENCIA". `docs/` NO se sella, precisamente porque se edita a
menudo; lo que no debe moverse sin querer es la evidencia.

Esta herramienta responde a tres preguntas distintas, que es donde suele
confundirse:

  1. ¿ALGUN fichero sello ya no esta?        -> ROTO
  2. ¿ALGUN fichero sello cambio?            -> MOVIDO
  3. ¿Hay evidencia NUEVA sin sellar?        -> SIN SELLAR

Las tres se contestan por separado porque significan cosas distintas. Un
fichero que falta y un fichero que cambio no se arreglan igual: el primero
puede ser un borrado, el segundo una edicion.

LO QUE ESTA FUERA DE ALCANCE, Y POR QUE
----------------------------------------
No decide si un cambio es legitimo. No puede: eso requiere saber si quien
lo escribo debia escribirlo. Lo que hace es DECIR QUE PASO, con la fecha y
el fichero, y no dejar que se entere por un documento que se contradiga
despues.

QUE NO HACE, Y ES LO IMPORTANTE
--------------------------------
No re-sella nada automaticamente. Volver a sellar un fichero que cambio sin
mirarlo convierte un detector de derivas en un detector de cambios: el
sello se actualiza y la perdida de historia desaparece.

Hay un `--actualizar` explicito, y escribe un fichero NUEVO, sin tocar el
anterior. Un sello que se sobrescribe a si mismo no recuerda nada.

TRES ESTADOS, Y POR QUE NO SE COLAPSAN EN UNO
---------------------------------------------
  OK        el fichero existe y su suma coincide
  MOVIDO    existe, pero la suma no coincide
  ROTO      no existe, o no se puede leer
  NUEVO     esta en el arbol, no estaba en el sello, y no es ruido

Un MOVIDO y un ROTO se distinguen porque el ROTO es el que obliga a
preguntarse si se perdio algo, y esa pregunta no se puede hacer despues si
todo se reduce a "el manifiesto no cuadra".
"""
import argparse
import datetime
import hashlib
import os
import sys

MANIFIESTO = "../docs/EVIDENCE-MANIFEST.sha256"

# Raiz por defecto, relativa al SCRIPT (ver la nota de --raiz en main).
RAIZ_POR_DEFECTO = ".."

# Rutas cuyo cambio se espera y no es deriva. Se declaran de forma explicita
# y se pueden anadir, pero nunca se anaden a ciegas: cada una es una
# decision, y por eso esta en codigo y no en un parametro.
RUTAS_QUE_NO_SE_SELLAN = {
    ".git", "__pycache__", "node_modules",
    # el manifiesto mismo no se sella a si mismo
    "docs/EVIDENCE-MANIFEST.sha256",
    # artefactos de build
    "capturas",
}

# Extensiones que son datos binarios o ruido de build, no evidencia.
NO_EVIDENCIA_EXT = {
    ".o", ".ko", ".so", ".pyc", ".png", ".jpg", ".rgba", ".bin", ".spv",
    ".ninja_deps", ".modinfo",
}

# Ruido que se sabe que existe y que no es evidencia. Declarado, no
# deducido, para que la exclusion sea revisable.
RUIDO_CONOCIDO = {
    "research/working", "research/baseline", "research/kernelbuild",
    "rx550-upstream-7.2.8",
}


def sha256(path, bloque=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(bloque)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def lee_manifiesto(ruta):
    """
    Devuelve [(sha_esperado, ruta_relativa), ...].

    Se ignoran las lineas de comentario y las vacias. Una linea malformada
    NO se descarta en silencio: es un dato sobre el manifiesto mismo.
    """
    entradas = []
    malformadas = []
    with open(ruta, errors="replace") as f:
        for i, ln in enumerate(f, 1):
            s = ln.strip()
            if not s or s.startswith("#"):
                continue
            partes = s.split(None, 1)
            if len(partes) != 2 or len(partes[0]) != 64:
                malformadas.append((i, s[:70]))
                continue
            entradas.append((partes[0], partes[1].strip()))
    return entradas, malformadas


def es_evidencia_candidata(ruta_rel):
    r = ruta_rel.lower()
    for ruido in RUIDO_CONOCIDO:
        if r.startswith(ruido + "/") or r == ruido:
            return False
    for no in RUTAS_QUE_NO_SE_SELLAN:
        if r == no.lower() or r.startswith(no.lower() + "/"):
            return False
    ext = os.path.splitext(r)[1].lower()
    if ext in NO_EVIDENCIA_EXT:
        return False
    return True


def indice_sellados(raiz):
    """
    Devuelve el conjunto de sha256 de TODOS los blobs del object store, sueltos
    e inalcanzables.

    POR QUE `--batch-all-objects` Y NO `rev-list`
    --------------------------------------------
    La pregunta que responde esto es "¿existe el CONTENIDO SELLADO en algun
    objeto?". Y el contenido sellado puede ser, justamente, lo que ya no
    referencia ningun commit: ese es el caso que importa. Un recorrido por
    ramas (`rev-list --all`) daria "no lo encuentro" tambien para los 33 casos
    en los que SI esta, y no podriamos distinguir los dos. Aqui se recorre el
    object store entero, que es lo unico que separa "nunca existio" de "existio
    y se perdio la referencia".

    MEDIDO: 7612 blobs, 4,2 s. No se cachea a proposito. Un indice de sumas
    cacheado es un indice que queda viejo sin que nadie lo note, que es el mismo
    fallo que este fichero denuncia en su primera linea.

    MEDIDO tambien: hay 5 objetos sueltos de tamano cero (hallazgo 1058) y `git
    cat-file --batch` escupe errores por ellos en stderr. No es fallo: son
    objetos ilegibles, se los salta, y el numero de blobs hasheados lo dice todo.
    """
    import subprocess as _sp
    import hashlib as _hl

    r = _sp.run(("git", "cat-file", "--batch-all-objects",
                 "--batch-check=%(objectname) %(objecttype)"),
                cwd=raiz, capture_output=True, text=True)
    # EL ERROR QUE ESTABA, Y EL QUE NO.
    #
    # 1. EL REAL. El `--batch-check=<formato>` va UNIDO con `=`. Pasado como dos
    #    argumentos, git responde `fatal: los modos de batch no toman
    #    argumentos` con rc=129 y stdout vacio. En un shell no se nota, porque
    #    alli el `=` y las comillas hacen que sea una sola palabra: la forma que
    #    funcionaba en la linea de comandos era distinta de la que escribi en el
    #    codigo. Esto es lo que produjo NOT_AVAILABLE en la primera corrida real,
    #    y por eso la rama de "no se" no mintio: es exactamente para lo que esta.
    #
    # 2. EL QUE CREI, Y NO ERA CIERTO. Escribi antes aqui que "hay 5 objetos
    #    ilegibles y `cat-file` devuelve rc != 0 por ellos, asi que gatear por
    #    returncode hacia desaparecer los 7612". MEDIDO y FALSO: con un objeto
    #    vacio en un repo de prueba, la enumeracion devuelve **rc=0** con 4
    #    lineas en stdout y el error en stderr. En este repositorio tambien:
    #    rc=0. El rc no se mueve.
    #
    #    No lo borro porque la LEccion sigue valiendo y es la misma de siempre:
    #    escribi una causa plausible y solo la medi despues. Lo que si se
    #    sostiene es mas pequeno: **el rc no lleva informacion sobre si la
    #    enumeracion esta completa**, asi que el unico criterio para "no
    #    disponible" es que stdout venga vacio. La razon por la que NO se
    #    gatea es que gatear por un numero que no lo sabe es una manera de
    #    fabricar una respuesta, no de evitar una.
    blobs = [ln.split()[0] for ln in (r.stdout or "").splitlines()
             if ln.split()[1:2] == ["blob"]]
    if not blobs:
        return None

    proc = _sp.Popen(("git", "cat-file", "--batch"), cwd=raiz,
                     stdin=_sp.PIPE, stdout=_sp.PIPE)
    vistos = set()
    ilegibles = 0
    try:
        for i in range(0, len(blobs), 200):
            trozo = blobs[i:i + 200]
            try:
                proc.stdin.write(("\n".join(trozo) + "\n").encode())
                proc.stdin.flush()
            except (BrokenPipeError, OSError):
                break
            for _oid in trozo:
                cab = proc.stdout.readline().split()
                if len(cab) < 3:
                    ilegibles += 1
                    continue
                try:
                    n = int(cab[2])
                except ValueError:
                    ilegibles += 1
                    continue
                cuerpo = proc.stdout.read(n)
                proc.stdout.read(1)
                vistos.add(_hl.sha256(cuerpo).hexdigest())
    finally:
        try:
            proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        proc.wait()
    if ilegibles:
        # Se dice. Un indice con 5 huecos no es un indice completo, y si no se
        # dice parece que lo es.
        sys.stderr.write("  aviso: %d objeto(s) ilegible(s) del total de %d; "
                         "el indice de sumas no los cubre\n"
                         % (ilegibles, len(blobs)))
    return vistos


def clasifica_custodia(entradas, recuperables, commiteados):
    """
    Nucleo PURO de la custodia: sin git, sin disco, sin reloj.

    Se separa de `custodia()` a proposito, por una razon que ya ha_costado dos
    veces hoy en este trabajo: una funcion que hace E/S y ademas decide no se
    puede probar sin montar el mundo. Con el nucleo separado, los vectores del
    self-test son entradas y salidas, y no dependen de este repositorio ni de su
    estado.

    Devuelve los cuatro grupos que el 1059 midio, y una quinta lista con los
    sellados cuyo contenido no aparece en ninguna parte.

    LA QUINTA CLASE NO BAJA EL CODIGO DE SALIDA
    ------------------------------------------
    `SELLADO_PERDIDO` es un HECHO que hay que mirar, no un fallo del sello. El
    sello ha hecho su trabajo: ha dicho la verdad. Si esto bajara el rc, el
    invariante "no cambia lo que ya devolvia para las entradas con Q1 = True"
    seria falso, y una puerta que se pone roja por un hecho informativo
    entrena a ignorar sus propios rojos. Decision escrita en el §6 del 1059.
    """
    sellados = set(rel for _h, rel in entradas)
    ambos = sellados & commiteados
    sellado_sin_commit = sellados - commiteados
    commit_sin_sello = commiteados - sellados
    sin_recuperar = []
    if recuperables is not None:
        sin_recuperar = [(h, rel) for h, rel in entradas
                         if h not in recuperables]
    else:
        sin_recuperar = None      # no se pudo indexar: NO se afirma nada
    return dict(ambos=ambos, sellado_sin_commit=sellado_sin_commit,
                commit_sin_sello=commit_sin_sello,
                sin_recuperar=sin_recuperar, sellados=sellados)


def custodia(raiz, entradas, silencioso=False, a_todos=False,
             recuperables=Ellipsis, _commiteados=None):
    """Cruza el sello con git y dice, para cada fichero de evidencia,
    si su corrupcion se DETECTA y si se puede RECUPERAR.

    Son dos preguntas distintas y una no implica la otra:

      DETECTAR   el manifiesto tiene el sha256. Si el fichero cambia, se nota.
      RECUPERAR  hay una version commiteada. Si se pierde, se vuelve.

    Un fichero sellado y sin commit es el caso peligroso: se detecta que se
    rompio y no hay de donde volver. Es exactamente como se perdio el 050.

    Por que `ls-tree` y no `ls-files`
    ---------------------------------
    `git ls-files` lista el INDICE, que en este proyecto es estado compartido
    entre sesiones: una sesion stagea y otra commitea. Un fichero stageado sin
    commitear aparece en `ls-files` y NO es recuperable, porque todavia no
    existe en ningun commit. Para "recuperable" hay que mirar HEAD, y para eso
    `ls-tree -r HEAD`.

    QUE ES LO QUE ESTA MAL, Y QUE ESTABA EN EL 1059
    -----------------------------------------------
    Esta funcion respondia "¿la RUTA esta en `ls-tree HEAD`?" y la imprimia
    como "detecta y recupera". Son dos preguntas distintas: la ruta puede estar
    en HEAD y el CONTENIDO SELLADO no estar en ningun objeto, porque lo
    commiteado fue una version posterior. MEDIDO: 30 de 245 entradas del
    manifiesto de este proyecto estan asi, y para ellas "recupera" era falso.

    Ahora se pregunta las dos. La de la ruta sigue igual, porque es la que
    responde si hay una version de la que VOLVER. La del contenido se responde
    con `indice_sellados()`, y se imprime aparte.
    """
    import subprocess as _sp

    sellados = set(rel for _h, rel in entradas)

    def _git(*args):
        return _sp.run(("git",) + args, cwd=raiz, capture_output=True,
                       text=True)

    r = _git("rev-parse", "--git-dir")
    if r.returncode != 0:
        if not silencioso:
            print("CUSTODIA DE LA EVIDENCIA")
            print("  NOT_APPLICABLE: %s no es un repositorio git" % raiz)
            print("  No se puede decir nada sobre recuperabilidad.")
        return 4

    r = _git("ls-tree", "-r", "--name-only", "HEAD")
    if r.returncode != 0:
        if not silencioso:
            print("CUSTODIA DE LA EVIDENCIA")
            print("  NOT_AVAILABLE: `git ls-tree HEAD` fallo (rc=%d)"
                  % r.returncode)
            print("  Puede no haber commits todavia.")
        return 4

    commiteados = set(l.strip() for l in r.stdout.split("\n") if l.strip())

    # indice menos HEAD = stageado sin commitear. No es recuperable y no es
    # error: se imprime aparte para que no se confunda con la custodia.
    r = _git("ls-files")
    indice = set(l.strip() for l in r.stdout.split("\n") if l.strip())
    sin_commit = indice - commiteados

    ambos = sellados & commiteados
    sellado_sin_commit = sellados - commiteados
    commit_sin_sello = commiteados - sellados
    ni_uno = set()  # por construccion: todo lo sellado esta en un lado o en otro

    # LA SEGUNDA PREGUNTA. Se calcula una vez y se imprime aparte.
    #
    # `recuperables` es `Ellipsis` por defecto, que significa "no me lo han
    # pasado": entonces se calcula aqui. Se puede pasar como conjunto desde el
    # self-test, que es como se prueban las dos ramas sin montar un repositorio.
    if recuperables is Ellipsis:
        recuperables = indice_sellados(raiz)
    if recuperables is not None:
        sin_recuperar = [(h, rel) for h, rel in entradas
                         if h not in recuperables]
    else:
        sin_recuperar = None

    if not silencioso:
        print("=" * 78)
        print("CUSTODIA DE LA EVIDENCIA")
        print("=" * 78)
        print("El sello DETECTA la corrupcion.  El commit RECUPERA la perdida.")
        print("Son preguntas distintas, y una no implica la otra.")
        print()
        print("  LA PREGUNTA DE LA RUTA  (¿hay una version commiteada?)")
        print("  %-46s %d" % ("sellado + commiteado", len(ambos)))
        print("  %-46s %d" % ("sellado SIN commit     (detecta, NO recupera)",
                              len(sellado_sin_commit)))
        print("  %-46s %d" % ("commiteado SIN sello  (recupera, no detecta)",
                              len(commit_sin_sello)))
        print("  %-46s %d" % ("ni sello ni commit   (ni detecta ni recupera)",
                              len(ni_uno)))
        print()
        print("  LA PREGUNTA DEL CONTENIDO  (¿el estado SELLADO sigue existiendo?)")
        if sin_recuperar is None:
            print("  NOT_AVAILABLE: no se pudo indexar el object store. No se")
            print("  afirma nada: 'no lo he encontrado' no es 'no existe'.")
        else:
            print("  %-46s %d" % ("sellado y RECUPERABLE por contenido",
                                  len(entradas) - len(sin_recuperar)))
            print("  %-46s %d" % ("SELLADO PERDIDO (no esta en ningun objeto)",
                                  len(sin_recuperar)))
            # EL DENOMINADOR, DICHO.
            #
            # MEDIDO: sin esto, esta herramienta decia 32 y el hallazgo 1059
            # decia 30, y las dos cifras eran correctas sobre populaciones
            # distintas -- 30 sobre las 243 que TIENEN ruta en HEAD, 32 sobre
            # las 245 del manifiesto. Los 2 de diferencia son
            # 07-DRIVER/kernel/*.mod.c, que no tienen ruta commiteada y por eso
            # ya estan en "SELLADOS SIN COMMIT". Son las dos clases a la vez, y
            # una cifra sin denominador obliga a ese trabajo de reconciliar.
            #
            # Con las dos lineas, el que lee esto sabe que el numero que le
            # importa para "detecta y recupera mentia" es el de abajo.
            _en_ruta = [x for x in sin_recuperar if x[1] in ambos]
            print()
            print("  de los cuales, CON ruta commiteada (los que hacen que")
            print("  'detecta y recupera' sea falso): %d de %d"
                  % (len(_en_ruta), len(ambos)))
        print()
        print("  stageados sin commitear: %d  (no es error: no hay commit aun)"
              % len(sin_commit))
        print()
        if sin_recuperar:
            print("  LAS DOS PREGUNTAS NO COINCIDEN")
            print()
            print("  Que un fichero este en HEAD y su contenido sellado este en")
            print("  ningun objeto es la posicion EXACTAMENTE en la que `detecta y")
            print("  recupera` era falso: hay version a la que volver, pero no es")
            print("  la que el sello certifica. MEDIDO: 30 de 245 en este proyecto.")
            print()

    if sellado_sin_commit and not silencioso:
        from collections import Counter as _Ct
        c = _Ct()
        for r_ in sorted(sellado_sin_commit):
            c[r_.split("/")[0] + "/" if "/" in r_ else "(raiz)"] += 1
        print("SELLADOS SIN COMMIT, por directorio (lo expuesto a perdida):")
        for k, n in c.most_common():
            print("  %-46s %d" % (k, n))
        print()
        # Y los ficheros uno a uno, porque la accion que esta herramienta
        # exige es decidir fichero a fichero. Solo dar el recuento por
        # directorio hace imposible cumplirla. Un control cn8 detecto
        # esto: el recuento estaba bien pero los nombres no salian.
        _todos = sorted(sellado_sin_commit)
        _top = _todos if a_todos else _todos[:40]
        print("SELLADOS SIN COMMIT, uno a uno (%d de %d%s):"
              % (len(_top), len(_todos),
                 "" if a_todos else ", se muestran 40"))
        for r_ in _top:
            print("  %s" % r_)
        if not a_todos and len(_todos) > 40:
            print("  ... y %d mas (--todos para verlos)"
                  % (len(_todos) - 40))
        print()
        print("  Si uno de estos se corrompe, el sello lo dira y no habra")
        print("  version de la que volver. El 050 se perdio asi.")
        print()

    # SELLADO_PERDIDO SE IMPRIME Y NO CAMBIA EL CODIGO DE SALIDA.
    #
    # Decidido en el §6 del hallazgo 1059 y escrito aqui para que no se lea
    # como descuido: es un HECHO que hay que mirar, no un fallo del sello. El
    # sello ha hecho su trabajo, que es decir la verdad. Una puerta que se pone
    # roja por un dato informativo entrena a ignorar sus propios rojos, y el
    # invariante "para las entradas con Q1 = True no cambia nada" se romperia.
    if sin_recuperar and not silencioso:
        _top2 = sin_recuperar if a_todos else sin_recuperar[:40]
        print("SELLADO PERDIDO: el contenido que el manifiesto certifica no esta")
        print("en ningun objeto del repositorio (%d de %d%s):"
              % (len(_top2), len(sin_recuperar),
                 "" if a_todos else ", se muestran 40"))
        print()
        for _h, rel in _top2:
            print("  %-52s %s" % (rel[:52], _h[:16]))
        if not a_todos and len(sin_recuperar) > 40:
            print("  ... y %d mas (--todos para verlos)"
                  % (len(sin_recuperar) - 40))
        print()
        print("  Esto NO baja el codigo de salida, y no es un descuido.")
        print("  El sello ha dicho la verdad. Lo que no se puede es volver")
        print("  AL ESTADO SELLADO, y por eso no se debe re-sellar solo:")
        print("  hacerlo cambia el manifiesto y con el se pierde lo unico que")
        print("  decia que ese estado existio alguna vez.")
        print()

    return 1 if sellado_sin_commit else 0


def selftest():
    """
    Vectores del nucleo puro `clasifica_custodia`.

    Este fichero no tenia NINGUN self-test antes de que el 1059 le pidiera una
    clase nueva, y eso es en si mismo el dato: una herramienta que decide si la
    evidencia del proyecto se puede recuperar, sin un solo vector que la rompa a
    proposito.

    SIN DISCO, SIN GIT, SIN RELOJ. Los cuatro casos que importan:

      control POSITIVO  un sellado cuyo sha256 SI esta en el conjunto indexado
      control NEGATIVO  un sellado cuyo sha256 NO esta, con la ruta presente en
                        HEAD: es exactamente el caso del 1059, y tiene que salir
                        SELLADO_PERDIDO sin que baje el codigo de salida
      invariante        para las entradas con Q1 = True, el reparto tiene que ser
                        IDENTICO al que daba la version anterior
      INDISPONIBLE      si no se pudo indexar, NO se afirma nada: "no lo he
                        encontrado" no es "no existe"
    """
    import hashlib as _hl
    fallos = 0
    vectores = 0

    def chk(nombre, cond, detalle=""):
        nonlocal fallos, vectores
        vectores += 1
        if cond:
            print("    OK   %-54s %s" % (nombre, detalle))
        else:
            fallos += 1
            print("    FALLA %-54s %s" % (nombre, detalle))

    A = _hl.sha256(b"contenido A").hexdigest()
    B = _hl.sha256(b"contenido B").hexdigest()
    FALSO = "0" * 64

    entradas = [(A, "findings/a.md"), (B, "findings/b.md"),
                (FALSO, "findings/c.md")]
    commiteados = {"findings/a.md", "findings/b.md", "findings/c.md"}
    rec = {A, B}

    r = clasifica_custodia(entradas, rec, commiteados)
    chk("P1_control_positivo_se_recupera", len(r["sin_recuperar"]) == 1)
    chk("P2_control_negativo_es_el_ruta_que_esta_en_HEAD",
        r["sin_recuperar"] == [(FALSO, "findings/c.md")],
        str(r["sin_recuperar"]))
    chk("P3_las_tres_rutas_estan_commiteadas",
        len(r["ambos"]) == 3 and len(r["sellado_sin_commit"]) == 0,
        "ambos=%d" % len(r["ambos"]))

    # INVARIANTE: con Q1 = True para todo, el reparto es el de antes del 1059.
    r2 = clasifica_custodia(entradas, {A, B, FALSO}, commiteados)
    chk("I1_invariante_si_todo_es_recuperable",
        r2["sin_recuperar"] == [] and r2["ambos"] == commiteados,
        "sin_recuperar=%d" % len(r2["sin_recuperar"]))

    # sellado sin commit: sigue siendo la clase que baja el rc
    r3 = clasifica_custodia(entradas, rec, {"findings/a.md"})
    chk("I2_sin_commit_va_a_su_propia_clase",
        r3["sellado_sin_commit"] == {"findings/b.md", "findings/c.md"}
        and len(r3["ambos"]) == 1)
    chk("I3_un_sellado_sin_commit_puede_ser_perdido_y_sin_commit",
        ("%s" % FALSO, "findings/c.md") in r3["sin_recuperar"])

    # INDISPONIBLE: no se indexa -> no se afirma nada
    r4 = clasifica_custodia(entradas, None, commiteados)
    chk("I4_sin_indice_no_se_afirma_ausencia", r4["sin_recuperar"] is None,
        "None = no se sabe, no 'no existe'")

    # entradas vacias
    r5 = clasifica_custodia([], set(), set())
    chk("I5_vacio_no_inventa_clases",
        r5["sin_recuperar"] == [] and r5["ambos"] == set())

    # el mismo sha256 para dos rutas: ambas tienen que salir, porque el
    # contenido sellado es el mismo y por eso es el mismo estado
    ent6 = [(A, "x/1.md"), (A, "x/2.md")]
    r6 = clasifica_custodia(ent6, set(), {"x/1.md", "x/2.md"})
    chk("I6_sha_repetido_sale_una_vez_por_ruta", len(r6["sin_recuperar"]) == 2)

    print("  %d vectores, %d fallos" % (vectores, fallos))
    return fallos


def selftest_custodia_real():
    """
    Segunda capa: `custodia()` e `indice_sellados()` sobre un repo de mentira.

    POR QUE EXISTE, Y NO ES POR CUBRIR CODIGO
    -----------------------------------------
    MEDIDO: con la primera capa (el nucleo puro) las mutaciones M16 --que hace
    que SELLADO_PERDIDO baje el codigo de salida-- y M17 --que vuelve a gatear
    por el codigo de salida de git-- pasaban 9 de 9. Las dos viven en codigo que
    el nucleo puro no toca.

    Es la tercera vez en este trabajo que un self-test no detecta un defecto
    porque **no ejerce el camino donde esta el defecto**, y por eso esta capa
    monta un repositorio entero en un directorio temporal. Es hermetica en el
    sentido que importa: no toca ESTE repositorio, y por tanto no puede dar una
    respuesta que dependa de como esté el arbol hoy.

    Lo que verifica, y son las dos cosas que la otra capa no puede:

      1. `indice_sellados()` finds a blob that IS in the repo  (control positivo)
      2. `indice_sellados()` does NOT find a sha256 that is not (control negativo)
      3. `custodia()` keeps its rc when only SELLADO_PERDIDO exists (invariante)
      4. `custodia()` DOES lower its rc when a sellado has no commit
    """
    import tempfile as _tf
    import subprocess as _sp

    fallos = 0
    vectores = 0

    def chk(nombre, cond, detalle=""):
        nonlocal fallos, vectores
        vectores += 1
        if cond:
            print("    OK   %-54s %s" % (nombre, detalle))
        else:
            fallos += 1
            print("    FALLA %-54s %s" % (nombre, detalle))

    def git(d, *a):
        return _sp.run(("git",) + a, cwd=d, capture_output=True, text=True)

    with _tf.TemporaryDirectory() as td:
        d = os.path.join(td, "repo")
        os.makedirs(d)
        ident = ["-c", "user.email=t@t", "-c", "user.name=t",
                 "-c", "commit.gpgsign=false"]
        git(d, *ident, "init", "-q")
        # dos ficheros: A se commitea y luego se cambia; B nunca se commitea
        for nm, cuerpo in (("a.md", "A0\n"), ("b.md", "B0\n")):
            with open(os.path.join(d, nm), "w") as f:
                f.write(cuerpo)
        git(d, *ident, "add", "-A")
        git(d, *ident, "commit", "-qm", "inicial")

        idx = indice_sellados(d)
        chk("R1_indice_se_construye", isinstance(idx, set) and len(idx) >= 2,
            "%d blobs" % (len(idx) if idx else -1))

        import hashlib as _hl
        h_b = _hl.sha256(open(os.path.join(d, "b.md"), "rb").read()).hexdigest()
        chk("R2_control_positivo_el_blob_que_esta_se_encuentra",
            idx is not None and h_b in idx)
        chk("R3_control_negativo_un_sha_inventado_no_se_encuentra",
            idx is not None and ("f" * 64) not in idx)

        # b.md sale del repo. `--cached` solo lo saca del INDICE: hace falta el
        # commit, porque `custodia` mira `ls-tree HEAD` y no el indice. Sin el
        # commit, b.md sigue en HEAD, no hay "sellado sin commit", y el vector
        # R6 no probaria lo que dice probar.
        git(d, "rm", "-q", "--cached", "b.md")
        git(d, *ident, "commit", "-qm", "quita b")
        chk("R0_b_ya_no_esta_en_HEAD",
            git(d, "rev-parse", "--verify", "-q", "HEAD:b.md").returncode != 0)

        # manifiesto: a.md con el hash de su version ACTUAL (que no esta
        # commiteada) y b.md con el hash de la version commiteada
        with open(os.path.join(d, "a.md"), "w") as f:
            f.write("A1\n")
        ha = _hl.sha256(open(os.path.join(d, "a.md"), "rb").read()).hexdigest()
        man = os.path.join(d, "MANIFESTO.sha256")
        with open(man, "w") as f:
            f.write("# test\n%s  a.md\n%s  b.md\n" % (ha, h_b))
        entradas, malas = lee_manifiesto(man)
        chk("R4_manifiesto_de_prueba_se_lee", len(entradas) == 2
            and not malas)

        rc = custodia(d, [(ha, "a.md")], silencioso=True)
        chk("R5_solo_SELLADO_PERDIDO_no_baja_el_rc", rc == 0,
            "rc=%d  (invariante del §6 del 1059)" % rc)

        # el caso REAL: a.md esta en HEAD, y su contenido SELLADO ("A1") nunca
        # se commiteo. Se comprueba que de verdad se cae en SELLADO_PERDIDO y no
        # en "recuperable", porque un rc=0 aqui seria el bug del 1059的.
        r_solo = clasifica_custodia([(ha, "a.md")], indice_sellados(d),
                                    {"a.md", "b.md"})
        chk("R5b_es_SELLADO_PERDIDO_y_no_otra_cosa",
            r_solo["sin_recuperar"] == [(ha, "a.md")]
            and "a.md" in r_solo["ambos"],
            "en HEAD=%s  sellado recuperable=%s"
            % ("a.md" in r_solo["ambos"],
               not r_solo["sin_recuperar"]))

        # ahora uno SIN commit: b.md no esta en HEAD
        rc2 = custodia(d, [(h_b, "b.md")], silencioso=True)
        chk("R6_sellado_sin_commit_si_baja_el_rc", rc2 == 1, "rc=%d" % rc2)

        # los dos a la vez: manda el sin commit
        rc3 = custodia(d, entradas, silencioso=True)
        chk("R7_el_sin_commit_manda_sobre_el_perdido", rc3 == 1, "rc=%d" % rc3)

        # 8. UN OBJETO ILEGIBLE, QUE ES LA CONDICION REAL DE ESTE REPOSITORIO.
        #
        # MEDIDO: la mutacion M17 --volver a gatear por el codigo de salida de
        # `cat-file --batch-all-objects`-- pasaba 9 de 9 con este repo de mentira,
        # porque un repo sano devuelve rc=0 y la puerta nunca llega a abrirse. Y
        # sin embargo en ESTE repositorio hay 5 objetos sueltos de tamano cero
        # (hallazgo 1058), y ahi la puerta se abria y contestaba
        # NOT_AVAILABLE sobre el object store entero.
        #
        # El fixture era mas sano que la realidad y por eso no reproducia el
        # defecto. Se escribe un objeto vacio de verdad.
        _d = os.path.join(d, ".git", "objects", "ab")
        os.makedirs(_d, exist_ok=True)
        with open(os.path.join(_d, "c" * 38), "wb"):
            pass
        idx3 = indice_sellados(d)
        chk("R8_un_objeto_ilegible_no_tapa_el_resto_del_indice",
            idx3 is not None and h_b in idx3,
            "idx=%s" % ("None" if idx3 is None else "%d entradas" % len(idx3)))

    print("  %d vectores, %d fallos" % (vectores, fallos))
    return fallos


def main():
    ap = argparse.ArgumentParser(
        description="verifica el sello de evidencia")
    ap.add_argument("--raiz", default=None,
                    help="raiz del proyecto; por defecto '..' relativo al "
                         "script, y si se da valor, relativo al CWD")
    ap.add_argument("--manifiesto", default=None)
    ap.add_argument("--nuevos", action="store_true",
                    help="lista tambien la evidencia sin sellar")
    ap.add_argument("--actualizar", default=None, metavar="FICHERO",
                    help="escribe un manifiesto NUEVO; no toca el anterior")
    ap.add_argument("--custodia", action="store_true",
                    help="cruza el sello con git: detecta vs recupera")
    ap.add_argument("--todos", action="store_true",
                    help="con --custodia, lista los 139 sin truncar a 40")
    ap.add_argument("--selftest", action="store_true",
                    help="vectores del nucleo de custodia; sin disco ni git")
    a = ap.parse_args()

    if a.selftest:
        f1 = selftest()
        print()
        print("SEGUNDA CAPA: custodia() e indice_sellados() sobre un repo falso")
        f2 = selftest_custodia_real()
        return 0 if (f1 == 0 and f2 == 0) else 1

    aqui = os.path.dirname(os.path.abspath(__file__))
    # SEMANTICA DE --raiz, que estuvo mal dos veces:
    #   sin flag   -> relativo al SCRIPT, para que `python3 revkit/sello.py`
    #                funcione desde cualquier directorio, incluida la raiz del
    #                proyecto, donde el default `..` debe seguir dando la raiz
    #                del proyecto y no su padre
    #   con flag   -> relativo al CWD, que es lo que espera cualquiera que
    #                escribe `--raiz .`. Antes resolvia contra el script en los
    #                dos casos, con lo que `--raiz .` sobre un arbol de prueba
    #                apuntaba a revkit/ y fallaba con un error que no tenia
    #                nada que ver con lo que se estaba probando
    if a.raiz is None:
        raiz = os.path.abspath(os.path.join(aqui, RAIZ_POR_DEFECTO))
    else:
        raiz = os.path.abspath(a.raiz) if os.path.isabs(a.raiz) else \
            os.path.abspath(os.path.join(os.getcwd(), a.raiz))
    # El manifiesto se busca en la raiz indicada, y si no esta, en docs/ de
    # esa raiz. Antes se resolvia siempre contra la raiz del script, con lo
    # que --raiz no servia para nada.
    if a.manifiesto:
        manifiesto = a.manifiesto
    else:
        manifiesto = os.path.join(raiz, "docs", "EVIDENCE-MANIFEST.sha256")
        if not os.path.exists(manifiesto):
            alt = os.path.join(raiz, "EVIDENCE-MANIFEST.sha256")
            if os.path.exists(alt):
                manifiesto = alt
    if not os.path.exists(manifiesto):
        print("no existe el manifiesto: %s" % manifiesto)
        return 2

    entradas, malformadas = lee_manifiesto(manifiesto)
    # --custodia es independiente del chequeo de integridad: responde a otra
    # pregunta y tiene otro codigo de salida. Si comparten rc, un rc=1 seria
    # ambiguo entre "la evidencia se movio" y "la evidencia no tiene version".
    if a.custodia:
        return custodia(raiz, entradas, a_todos=a.todos)
    print("=" * 78)
    print("SELLO DE EVIDENCIA")
    print("=" * 78)
    print("manifiesto: %s" % manifiesto)
    print("entradas   : %d" % len(entradas))
    print("raiz       : %s" % raiz)
    print()

    ok = movidos = rotos = ilegibles = 0
    detalle_movidos = []
    detalle_roto = []
    for esperado, rel in entradas:
        p = os.path.join(raiz, rel)
        if not os.path.exists(p):
            rotos += 1
            detalle_roto.append((rel, "NO EXISTE"))
            continue
        try:
            got = sha256(p)
        except OSError as e:
            ilegibles += 1
            detalle_roto.append((rel, "ilegible: %s" % e))
            continue
        if got == esperado:
            ok += 1
        else:
            movidos += 1
            detalle_movidos.append((rel, esperado[:12], got[:12]))

    print("RESULTADO")
    print("  %-12s %d" % ("OK", ok))
    print("  %-12s %d" % ("MOVIDO", movidos))
    print("  %-12s %d" % ("ROTO", rotos))
    if ilegibles:
        print("  %-12s %d" % ("ILEGIBLE", ilegibles))
    print()

    if malformadas:
        print("LINEAS MALFORMADAS EN EL MANIFIESTO: %d" % len(malformadas))
        for i, s in malformadas[:5]:
            print("  linea %d: %r" % (i, s))
        print("  No se ignoran: un manifiesto con lineas rotas sella menos")
        print("  de lo que dice, y eso no se ve en el recuento.")
        print()

    if detalle_movidos:
        print("EVIDENCIA QUE SE MOVIO (%d):" % len(detalle_movidos))
        print("  %-64s %-14s %s" % ("fichero", "esperado", "obtenido"))
        for rel, esp, got in sorted(detalle_movidos):
            print("  %-64s %-14s %s" % (rel[:64], esp, got))
        print()
        print("  ESTO NO ES UN ERROR POR SÍ SOLO. Editar evidencia es")
        print("  legitimo si quien lo hace sabe lo que hace. Lo que no es")
        print("  legitimo es que no quede constancia.")
        print()

    if detalle_roto:
        print("EVIDENCIA ROTA (%d):" % len(detalle_roto))
        for rel, why in sorted(detalle_roto):
            print("  %-64s %s" % (rel[:64], why))
        print()
        print("  Esto es mas grave que MOVIDO: un fichero que no esta no se")
        print("  puede re-sellar, y el sello lo declaraba como evidencia.")
        print()

    # Evidencia nueva sin sellar
    nuevos = []
    if a.nuevos or a.actualizar:
        sellados = set(rel for _h, rel in entradas)
        for dp, dns, fns in os.walk(raiz):
            dns[:] = [d for d in dns if d not in (".git", "__pycache__",
                                                 "node_modules")]
            for fn in fns:
                p = os.path.join(dp, fn)
                rel = os.path.relpath(p, raiz)
                if rel in sellados:
                    continue
                if not es_evidencia_candidata(rel):
                    continue
                if not fn.endswith((".md", ".py", ".sh", ".c", ".h")):
                    continue
                nuevos.append(rel)
        if nuevos:
            print("EVIDENCIA SIN SELLAR: %d ficheros" % len(nuevos))
            for rel in sorted(nuevos)[:30]:
                print("  %s" % rel)
            if len(nuevos) > 30:
                print("  ... y %d mas" % (len(nuevos) - 30))
            print()

    # Actualizar: escribe un fichero NUEVO, nunca sobrescribe el anterior.
    if a.actualizar:
        if movidos or rotos:
            print()
            print("NO SE ESCRIBE EL SELLO NUEVO.")
            print()
            print("Hay %d ficheros MOVIDOS y %d ROTOS, y sellarlos ahora"
                  % (movidos, rotos))
            print("convertiria esto en un detector de cambios en vez de uno")
            print("de derivas: el sello se actualizaria y la perdida de")
            print("historia desapareceria.")
            print()
            print("Hay que decidir primero, fichero a fichero, si el cambio")
            print("es legitimo. Eso no lo puede hacer un script.")
            return 3
        with open(a.actualizar, "w") as f:
            f.write("# drift 1.0.0  -- sello de evidencia\n")
            f.write("# regenerado %s\n"
                    % datetime.datetime.now().isoformat(timespec="seconds"))
            f.write("# %d ficheros\n" % len(entradas))
            for esperado, rel in sorted(entradas, key=lambda x: x[1]):
                f.write("%s  %s\n" % (esperado, rel))
        print("Sello nuevo escrito en %s" % a.actualizar)
        print("El anterior NO se ha tocado.")
        return 0

    # Codigo de salida: distingue lo que obliga a preguntar de lo que no.
    if rotos:
        return 2
    if movidos:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
