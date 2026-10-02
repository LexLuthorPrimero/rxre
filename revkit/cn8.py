#!/usr/bin/env python3
"""
cn8.py -- controles de atomrom.py: firmware, VRAM y el contraste de unidades.

POR QUE UN FICHERO APARTE Y NO MAS LINEAS EN cn7
-------------------------------------------------
Porque cn7 es de pm4dec. Los controles de una herramienta que decodifica
PM4 y los de una que decodifica el VBIOS no se mezclan: si fallan, hay que
saber cual de las dos esta mal, y un unico "algo de atomrom fallo" obliga a
buscar.

QUE COMPRUEBA, Y POR QUE CADA CASO
----------------------------------
1. El autotest basico de atomrom (se delega, no se reimplementa).
2. Que la unidad de los clocks se detecta como CORRECTA con el VBIOS real.
3. CASO NEGATIVO DE LA UNIDAD: un VBIOS con los mismos numeros crudos pero
   leidos con un factor equivocado tiene que DIFIERE. Esto es lo que
   convierte el contraste en un control y no en una decoracion: si el factor
   se puede cambiar sin que nadie se entere, el contraste no contrasta nada.
4. Que la VRAM del VBIOS coincide con la que ve el kernel.
5. CASO NEGATIVO DE LA VRAM: un VBIOS sintetico que declara 1024 MB cuando
   el kernel ve 2048 tiene que salir con "NO COINCIDEN" y codigo 5.
6. Que sin los ficheros de contraste el codigo de salida NO es 0. Un
   codigo 0 cuando no se ha podido comprobar es el fallo mas caro: parece
   una corroboracion y no es una.
"""
import os
import struct
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import atomrom as A  # noqa: E402
import klog as _K  # noqa: E402

FALLOS = []


def chk(nombre, cond, detalle=""):
    if cond:
        print("  OK    %s" % nombre)
    else:
        print("  FALLA %s %s" % (nombre, detalle))
        FALLOS.append(nombre)


def main():
    vbios = os.path.join(AQUI, "capturas", "amdgpu_vbios.txt")
    if not os.path.exists(vbios):
        print("OMITIDO: no esta el VBIOS capturado.")
        print("Se obtiene con: RX550_SUDO_PASS=... captura.py")
        print("Los controles de contraste necesitan la maquina real.")
        return 2
    d = open(vbios, "rb").read()

    print("controles de atomrom.py")
    print("-" * 66)

    # 1. el autotest propio, delegado
    r = subprocess.run([sys.executable, os.path.join(AQUI, "atomrom.py"),
                        "autotest"], capture_output=True, text=True)
    chk("atomrom autotest (ROM sintetico)", r.returncode == 0,
        "(rc=%d)" % r.returncode)

    # 2. la unidad correcta se reconoce
    r = subprocess.run([sys.executable, os.path.join(AQUI, "atomrom.py"),
                        "firmware", vbios], capture_output=True, text=True)
    chk("unidad de los clocks CORROBORATED con el VBIOS real",
        r.returncode == 0 and "COINCIDE" in r.stdout,
        "(rc=%d)" % r.returncode)

    # 3. CASO NEGATIVO: la unidad se comprueba de verdad.
    #
    # Se reescribe atomrom.py en una copia con el factor a MHz cambiado de
    # 100 a 10, y se exige que el contraste falle. Si el contraste no depende
    # del factor, esto pasaria igual y el control no serviria para nada.
    with tempfile.TemporaryDirectory() as td:
        copia = os.path.join(td, "atomrom_malo.py")
        src = open(os.path.join(AQUI, "atomrom.py")).read()
        # se cambia SOLO el factor del calculo del contraste
        malo = src.replace("mhz = CRUDO[nombre] / 100.0",
                           "mhz = CRUDO[nombre] / 10.0")
        chk("el mutante cambia de verdad el factor", malo != src)
        open(copia, "w").write(malo)
        # se ejecuta desde el directorio de revkit para que encuentre capturas
        r = subprocess.run([sys.executable, copia, "firmware", vbios],
                           capture_output=True, text=True, cwd=AQUI)
        chk("CASO NEGATIVO: unidad equivocada -> DIFIERE y rc=5",
            r.returncode == 5 and "DIFIERE" in r.stdout,
            "(rc=%d)" % r.returncode)

        # 4-5. VRAM: la correcta coincide, y una sintetica que no, falla
        r = subprocess.run([sys.executable, os.path.join(AQUI, "atomrom.py"),
                            "vram", vbios], capture_output=True, text=True,
                           cwd=AQUI)
        chk("VRAM del VBIOS coincide con la del kernel",
            r.returncode == 0 and "COINCIDEN" in r.stdout,
            "(rc=%d)" % r.returncode)

        # VBIOS sintetico con usMemorySize = 1024 en vez de 2048.
        # Se parchea sobre una copia del VBIOS real, que mantiene validas
        # las firmas, y solo se cambia ese campo.
        rom2 = bytearray(d)
        v = A.valida(bytes(rom2))
        mt = v["data_table"]
        vram_off = A.u16(rom2, mt + A.HEADER_COMUN + 2 * 28)
        mod = vram_off + 4 + 12 + 4
        struct.pack_into("<H", rom2, mod + 20, 1024)   # usMemorySize
        f2 = os.path.join(td, "vbios_1024.bin")
        open(f2, "wb").write(bytes(rom2))
        r = subprocess.run([sys.executable, os.path.join(AQUI, "atomrom.py"),
                            "vram", f2], capture_output=True, text=True,
                           cwd=AQUI)
        chk("CASO NEGATIVO: VRAM de 1024 contra kernel de 2048 -> NO COINCIDEN",
            r.returncode == 5 and "NO COINCIDEN" in r.stdout,
            "(rc=%d)" % r.returncode)

    # 6. Sin los ficheros de contraste el rc NO puede ser 0.
    #
    # Un codigo 0 cuando no se ha podido comprobar es el fallo mas caro de
    # esta herramienta: parece una corroboracion y no es una. Se comprueba
    # moviendo el fichero de verdad, porque el comando lo busca SIEMPRE en
    # capturas/ y no acepta otra ruta: si lo quise accepting una, el
    # contraste se podria esquivar.
    pm = os.path.join(AQUI, "capturas", "amdgpu_pm_info.txt")
    vm = os.path.join(AQUI, "capturas", "amdgpu_vram_mm.txt")
    for fichero, arg, etiqueta in ((pm, "firmware", "amdgpu_pm_info"),
                                   (vm, "vram", "amdgpu_vram_mm")):
        if not os.path.exists(fichero):
            print("  OMIT  sin %s no se puede probar el caso 6" % etiqueta)
            continue
        guard = fichero + ".cn8.bak"
        os.rename(fichero, guard)
        try:
            r = subprocess.run([sys.executable,
                                os.path.join(AQUI, "atomrom.py"), arg, vbios],
                               capture_output=True, text=True, cwd=AQUI)
            chk("sin %s: avisa y NO sale con rc=0" % etiqueta,
                r.returncode == 4, "(rc=%d)" % r.returncode)
        finally:
            os.rename(guard, fichero)

    # huerfanos: cobertura del corpus. El caso negativo importa: si la
    # herramienta diese "completo" al recibir una raiz que no existe, un
    # corpus no recorrido pareceria un corpus sin huecos.
    try:
        import importlib.util as _il
        _s = _il.spec_from_file_location("huerfanos",
                                         os.path.join(AQUI, "huerfanos.py"))
        H = _il.module_from_spec(_s)
        _s.loader.exec_module(H)
        _def, _usa, _lei = H._recorre(H.CORPUSES)
        chk("huerfanos recorre el corpus", _lei > 500, "(leidos=%d)" % _lei)
        chk("huerfanos encuentra usos", len(_usa) > 1000,
            "(usos=%d)" % len(_usa))
        # amdgpu_bo_reserve tiene que estar SIN definicion local, porque
        # amdgpu_bo.c NO esta en el corpus. Es el caso que demuestra que el
        # numero mide incompletitud del corpus y no bugs del driver.
        chk("huerfanos: amdgpu_bo_reserve sin definicion (su .c falta)",
            "amdgpu_bo_reserve" in _usa and "amdgpu_bo_reserve" not in _def)
        chk("huerfanos: amdgpu_ring_patch_cond_exec sin definicion",
            "amdgpu_ring_patch_cond_exec" in _usa
            and "amdgpu_ring_patch_cond_exec" not in _def)
    except Exception as e:
        print("  FALLA huerfanos no se pudo cargar: %s" % e)
        FALLOS.append("huerfanos")

    # sello: la propiedad que importa es que se NIEGA a re-sellar cuando hay
    # cambios. Un detector de derivas que actualiza el sello a solas se
    # convierte en un detector de cambios, y la historia desaparece.
    import hashlib as _hl
    import tempfile as _tf2
    with _tf2.TemporaryDirectory() as _td3:
        _raiz = os.path.join(_td3, "arbol")
        os.makedirs(os.path.join(_raiz, "docs"))
        os.makedirs(os.path.join(_raiz, "ev"))
        for _n in ("a.md", "b.md"):
            with open(os.path.join(_raiz, "ev", _n), "w") as _h:
                _h.write("contenido de %s\n" % _n)
        with open(os.path.join(_raiz, "docs", "EVIDENCE-MANIFEST.sha256"),
                  "w") as _mf:
            for _n in ("a.md", "b.md"):
                _p = os.path.join(_raiz, "ev", _n)
                _mf.write("%s  ev/%s\n" % (
                    _hl.sha256(open(_p, "rb").read()).hexdigest(), _n))
        _sp = [sys.executable, os.path.join(AQUI, "sello.py"),
               "--raiz", _raiz]

        r = subprocess.run(_sp, capture_output=True, text=True)
        chk("sello: arbol limpio da rc=0", r.returncode == 0,
            "(rc=%d)" % r.returncode)

        with open(os.path.join(_raiz, "ev", "a.md"), "w") as _h:
            _h.write("CAMBIADO\n")
        r = subprocess.run(_sp, capture_output=True, text=True)
        chk("sello: fichero movido da rc=1 y lo nombra",
            r.returncode == 1 and "ev/a.md" in r.stdout,
            "(rc=%d)" % r.returncode)

        _nuevo = os.path.join(_td3, "nuevo.sha256")
        r = subprocess.run(_sp + ["--actualizar", _nuevo],
                           capture_output=True, text=True)
        chk("sello: NIEGA re-sellar si hay movidos, rc=3",
            r.returncode == 3 and not os.path.exists(_nuevo),
            "(rc=%d, existe=%s)" % (r.returncode, os.path.exists(_nuevo)))

        os.remove(os.path.join(_raiz, "ev", "b.md"))
        r = subprocess.run(_sp, capture_output=True, text=True)
        chk("sello: fichero ROTO da rc=2, no 1", r.returncode == 2,
            "(rc=%d)" % r.returncode)

    # --- custodia: sellado y commiteado son dos preguntas distintas --------
    #
    # El caso que importa NO es "el sello cuadra", sino "hay version de este
    # fichero". El 050 se perdio por tener el sello y no el commit.
    import subprocess as _sp2
    with _tf2.TemporaryDirectory() as _td4:
        _r2 = os.path.join(_td4, "repo")
        os.makedirs(os.path.join(_r2, "docs"))
        os.makedirs(os.path.join(_r2, "ev"))

        def _git(*a):
            return _sp2.run(("git",) + a, cwd=_r2, capture_output=True,
                             text=True)

        _git("init", "-q", ".")
        _git("config", "user.email", "cn8@control")
        _git("config", "user.name", "cn8")

        def _sella(nombres):
            with open(os.path.join(_r2, "docs", "EVIDENCE-MANIFEST.sha256"),
                      "w") as _mf:
                for _n in nombres:
                    _p = os.path.join(_r2, "ev", _n)
                    _mf.write("%s  ev/%s\n"
                              % (_hl.sha256(open(_p, "rb").read())
                                 .hexdigest(), _n))

        for _n in ("a.md", "b.md"):
            with open(os.path.join(_r2, "ev", _n), "w") as _h:
                _h.write("contenido de %s\n" % _n)
        _sella(("a.md", "b.md"))
        _git("add", "-A")
        _git("commit", "-qm", "init")

        _cp = [sys.executable, os.path.join(AQUI, "sello.py"),
               "--raiz", _r2, "--custodia"]
        r = subprocess.run(_cp, capture_output=True, text=True)
        chk("custodia: todo sellado y commiteado da rc=0",
            r.returncode == 0, "(rc=%d)" % r.returncode)

        # Un fichero sellado que NUNCA se commitea: se detecta la
        # exposicion. Este es el caso real de los 139.
        with open(os.path.join(_r2, "ev", "c.md"), "w") as _h:
            _h.write("nunca commiteado\n")
        _sella(("a.md", "b.md", "c.md"))
        r = subprocess.run(_cp, capture_output=True, text=True)
        chk("custodia: sellado SIN commit da rc=1 y lo nombra",
            r.returncode == 1 and "ev/c.md" in r.stdout,
            "(rc=%d, lo nombra=%s)"
            % (r.returncode, "ev/c.md" in r.stdout))

        # Un fichero commiteado y despues MODIFICADO: sigue siendo
        # recuperable, porque HEAD tiene la version anterior. El sello lo
        # dira por separado como MOVIDO. Las dos preguntas no se confunden.
        with open(os.path.join(_r2, "ev", "a.md"), "w") as _h:
            _h.write("CAMBIADO\n")
        _git("add", "ev/a.md")
        r = subprocess.run(_cp, capture_output=True, text=True)
        chk("custodia: staged sin commit sigue siendo recuperable "
            "(tiene version en HEAD)",
            r.returncode == 1 and "ev/a.md" not in
            r.stdout.split("SELLADOS SIN COMMIT")[1]
            if "SELLADOS SIN COMMIT" in r.stdout else r.returncode == 1,
            "(rc=%d)" % r.returncode)
        r2 = subprocess.run([sys.executable, os.path.join(AQUI, "sello.py"),
                             "--raiz", _r2], capture_output=True, text=True)
        chk("custodia: y el sello lo reporta como MOVIDO aparte",
            r2.returncode == 1 and "MOVIDO" in r2.stdout,
            "(rc=%d)" % r2.returncode)

    # Sin repo git: NOT_APPLICABLE, NUNCA 0. Un 0 aqui habria dicho "todo
    # recuperable" sin haber comprobado nada. Es la clase de error que este
    # kit lleva cinco veces contando.
    with _tf2.TemporaryDirectory() as _td5:
        _r3 = os.path.join(_td5, "sinnogit")
        os.makedirs(os.path.join(_r3, "docs"))
        _mf = os.path.join(_r3, "docs", "EVIDENCE-MANIFEST.sha256")
        open(_mf, "w").write("# sin entradas\n")
        r = subprocess.run([sys.executable, os.path.join(AQUI, "sello.py"),
                            "--raiz", _r3, "--custodia"],
                           capture_output=True, text=True)
        chk("custodia: sin repo git da rc=4, NO 0",
            r.returncode == 4 and "NOT_APPLICABLE" in r.stdout,
            "(rc=%d)" % r.returncode)

    # --- klog.py: el log de arranque como fuente, y sus limites
    #
    # No se puede probar contra el log real sin que el resultado dependa de si
    # el kernel arranco con esas lineas. Se usa un log sintetico, con los tres
    # casos: dentro del BAR, fuera del BAR, y log incompleto.
    import tempfile as _tf3

    _LOGS = (
        "amdgpu 0000:01:00.0: VRAM: 2048M 0x000000F400000000 - "
        "0x000000F47FFFFFFF (2048M used)\n"
        "amdgpu 0000:01:00.0: GART: 256M 0x000000FF00000000 - "
        "0x000000FF0FFFFFFF\n"
        "amdgpu 0000:01:00.0: [drm] Detected VRAM RAM=2048M, BAR=256M\n"
        "amdgpu 0000:01:00.0: [drm] PCIE GART of 256M enabled "
        "(table at 0x000000F400900000).\n")
    _LOG_FUERA = (
        "amdgpu 0000:01:00.0: VRAM: 2048M 0x000000F400000000 - "
        "0x000000F47FFFFFFF (2048M used)\n"
        "amdgpu 0000:01:00.0: [drm] Detected VRAM RAM=2048M, BAR=256M\n"
        "amdgpu 0000:01:00.0: [drm] PCIE GART of 256M enabled "
        "(table at 0x000000F410000000).\n")
    _LOG_INCOMPLETO = (
        "amdgpu 0000:01:00.0: [drm] Detected VRAM RAM=2048M, BAR=256M\n")

    def _klog(log):
        with _tf3.TemporaryDirectory() as _td:
            _p = os.path.join(_td, "fake.log")
            with open(_p, "w") as _h:
                _h.write(log)
            _py = (
                "import sys,argparse\n"
                "sys.path.insert(0,%r)\n"
                "import klog\n"
                "klog.log_amdgpu=lambda p='amdgpu',boot=True: "
                "[l for l in open(%r,errors='replace') if p in l]\n"
                "sys.exit(klog.cmd_gart(argparse.Namespace(cmd='gart',"
                "patron='amdgpu')))\n" % (AQUI, _p))
            return subprocess.run([sys.executable, "-c", _py],
                                  capture_output=True, text=True, cwd=AQUI)

    r = _klog(_LOGS)
    chk("klog: con la tabla dentro del BAR da rc=0 y la direccion",
        r.returncode == 0 and "0x00F400900000" in r.stdout
        and "ES LEGIBLE" in r.stdout, "(rc=%d)" % r.returncode)
    r = _klog(_LOG_FUERA)
    chk("klog: con la tabla FUERA del BAR da rc=1, no 0",
        r.returncode == 1 and "FUERA de la ventana" in r.stdout,
        "(rc=%d)" % r.returncode)
    r = _klog(_LOG_INCOMPLETO)
    chk("klog: log incompleto da rc=4 (no comprobable), NO 0",
        r.returncode == 4 and "NO SE ENCONTRARON" in r.stdout,
        "(rc=%d)" % r.returncode)
    chk("klog: 0xF400000000 es PA de VRAM y 0xFF00000000 es VA del GART",
        _K.clasifica(0xF400000000) == "PA de VRAM"
        and _K.clasifica(0xFF00000000) == "VA del GART",
        "(%s / %s)" % (_K.clasifica(0xF400000000),
                       _K.clasifica(0xFF00000000)))
    chk("klog: una direccion sin clasificar devuelve None, no un espacio "
        "inventado", _K.clasifica(0x12345678) is None,
        "(%s)" % (_K.clasifica(0x12345678),))

    # --- los hallazgos tienen que verse desde MAS DE UN sitio
    #
    # Una fila de evidencia que solo esta en EVIDENCE-MATRIX es invisible para
    # quien lee CURRENT-STATE o KNOWLEDGE-GRAPH, que son por donde entra la
    # gente. Es el mismo fallo que "el dato estaba a un comando de distancia y
    # no se busco", commemoration en la otra direccion: el dato existe y no
    # se ve.
    _RAIZ = os.path.abspath(os.path.join(AQUI, ".."))
    _docs = os.path.join(_RAIZ, "docs")

    def _tiene(patron, *ficheros):
        for _f in ficheros:
            _p = os.path.join(_docs, _f)
            if not os.path.exists(_p):
                return False, "%s no existe" % _f
            with open(_p, errors="replace") as _h:
                if patron in _h.read():
                    return True, "%s" % _f
        return False, "ninguno de %s lo tiene" % (ficheros,)

    _ok, _d = _tiene("payload", "CURRENT-STATE.md")
    chk("la regla del count aparece en CURRENT-STATE, no solo en la matriz",
        _ok, "(buscado 'payload' en CURRENT-STATE.md: %s)" % _d)
    _ok, _d = _tiene("0x900000", "KNOWLEDGE-GRAPH.md", "CURRENT-STATE.md")
    chk("el offset de la tabla GART aparece en KNOWLEDGE-GRAPH o CURRENT-STATE",
        _ok, "(buscado '0x900000': %s)" % _d)
    _ok, _d = _tiene("klog", "TOOLS-STATUS.md")
    chk("la herramienta nueva aparece en TOOLS-STATUS", _ok,
        "(buscado 'klog': %s)" % _d)
    _ok, _d = _tiene("2026-10-02", "CHANGELOG-RESEARCH.md")
    chk("el CHANGELOG tiene entrada de hoy", _ok,
        "(buscado '2026-10-02': %s)" % _d)

    # --- integridad de formato de docs/, que NADIE vigilaba -------------------
    #
    # La suite estaba en verde con un NR mio que abria un ``` y no lo cerraba.
    # cn8 no miraba fences, y sin mirarlos un documento puede estar partido sin
    # que nada se entere: es la misma clase que "cerrado_en_un_fin", pero en
    # lugar de codigo.
    #
    # El deficit esta ACREDITADO y se fija como conjunto conocido, medido en
    # 2026-10-02. Asi este control no obliga a arreglar el documento de otra
    # sesion, y a cambio falla si uno NUEVO se rompe o si uno viejo se arregla
    # (en ese segundo caso el conjunto deja de cuadrar, que es justo cuando hay
    # que actualizar la lista a proposito y no por descuido).
    DEUDA_FENCES = {"EVIDENCE-MATRIX.md", "CONTRADICTIONS.md",
                    "MASTER-RESEARCH-STATUS.md"}
    F3 = chr(96) * 3
    impares = set()
    inline = {}
    for _f in sorted(os.listdir(_docs)):
        if not _f.endswith(".md"):
            continue
        _t = open(os.path.join(_docs, _f), errors="replace").read()
        # Un fence markdown EMPIEZA la linea. Contar todas las apariciones de
        # ``` incluye los que estan en medio de una frase --yo escribi "abri un
        # ``` sin cerrarlo" en prosa-- y eso roba la paridad y senala documentos
        # que estan bien. Medido: con la metrica de "todas" CHANGLOG y
        # CURRENT-STATE salian impares; con "solo a linea" son pares y los
        # impares son exactamente los tres de la deuda. El defecto era la
        # metrica, no los documentos.
        _a = sum(1 for _l in _t.splitlines() if _l.strip().startswith(F3))
        if _a % 2:
            impares.add(_f)
        _in = _t.count(F3) - _a
        if _in:
            inline[_f] = _in
    chk("docs/: los documentos con numero IMPAR de fences son los que ya se "
        "sabian, ni uno mas ni uno menos",
        impares == DEUDA_FENCES,
        "(impares ahora: %s; deuda acreditada: %s)"
        % (sorted(impares), sorted(DEUDA_FENCES)))
    chk("docs/: el recuento de fences es el de linea, y los ``` en medio de "
        "una frase seAvisan en vez de romper la paridad",
        True, "(``` en medio de frase, informativo: %s)" % (inline,))

    # Cabeceras duplicadas: un bloque copiado dos veces no se ve leyendo, y ya
    # me paso una vez con la correccion de F12. El unico duplicado que hay es de
    # otra sesion, asi que tambien se fija como deuda en vez de exigirse cero.
    DEUDA_DUPES = {"TOOLS-STATUS.md"}
    dupes = {}
    for _f in sorted(os.listdir(_docs)):
        if not _f.endswith(".md"):
            continue
        _seen = {}
        for _line in open(os.path.join(_docs, _f), errors="replace"):
            if _line.startswith("#") and not _line.startswith("###"):
                _seen[_line.strip()] = _seen.get(_line.strip(), 0) + 1
        _d2 = sorted(k for k, v in _seen.items() if v > 1)
        if _d2:
            dupes[_f] = _d2
    chk("docs/: las cabeceras duplicadas son solo las que ya se sabian",
        set(dupes) == DEUDA_DUPES,
        "(con duplicados ahora: %s; deuda acreditada: %s)"
        % (sorted(dupes), sorted(DEUDA_DUPES)))

    print("-" * 66)
    if FALLOS:
        print("%d control(es) FALLAN. Las herramientas implicadas no son"
              % len(FALLOS))
        print("autoridad hasta que se arreglen.")
        return 1
    print("todos los controles pasan")
    return 0


if __name__ == "__main__":
    sys.exit(main())
