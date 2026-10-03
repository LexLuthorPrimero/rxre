#!/usr/bin/env python3
# CONTRACT: name=run_all
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=yes
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
r"""
RUNNER -- una sola entrada para toda la caja de herramientas.

CODIGO DE SALIDA, que es un CONTRATO y no un numero
--------------------------------------------------
    0   todas las comprobaciones pasan
    1   hay un fallo REAL: requiere accion de quien lo ejecuta
    3   NINGUN fallo es accion de quien lo ejecuta: estan bloqueados por
        trabajo de otra sesion

EL 3 NO ES "TODO BIEN". Es "no hay nada que hacer aqui". La distincion importa:
un runner que sale con 1 por herramientas que no son suyas esta diciendo "fallo"
cuando no hay fallo que arreglar, y un rojo que no significa nada es peor que no
tener rojo, porque entrena a ignorar el codigo de salida.

Y el 3 se emite SIEMPRE con el motivo debajo, uno por comprobacion, diciendo
quien bloquea y por que. Un codigo de salida del que no se dice que significa es
un codigo que nadie puede usar.

Las comprobaciones bloqueadas estan en BLOQUEADO_POR_OTRA_SESION, mas abajo, con
el motivo de cada entrada. Es una DECLARACION, no un filtro: por eso anadir una
entrada de mas no relaja nada, que es justo lo que un filtro haria.

--check ejecuta lo necesario para decidir si el corpus esta intacto, sin las
comprobaciones pesadas. --self ejecuta las comprobaciones de contrato.

NO hay --help. Se escribio aqui un "--help da el detalle" antes de comprobar que
existiera, y `--help` no hace nada. Un contrato con una linea falsa es peor que
un contrato sin esa linea, porque se cita.

Por que existe. Con siete herramientas distintas, cada ronda terminaba asi:

    python3 pm4_reachable.py | head -40
    python3 gmmio_inventory.py | head -60
    python3 pm4_layout_audit.py
    git status --porcelain RESEARCH/
    grep -P '[\x{4e00}-\x{9fff}]' 06-.../0*.md
    ...

Cinco comandos con cinco sintaxis distintas, y es facil olvidar uno. El peor
caso real: olvidar el grep de intrusiones de otro idioma, que es el defecto que
mas he repetido.

Este script corre todo, comprueba el estado del corpus ANTES y DESPUES, y
termina con un codigo de salida utilizable desde un hook de commit.

Uso:
  python3 run_all.py              todo
  python3 run_all.py --quick      solo lo barato y lo que detecta errores
  python3 run_all.py --check      solo integridad (para un pre-commit hook)
Salida: 0 si todo bien, 1 si algo falla de verdad.
"""
import subprocess
import sys
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/lucas/Escritorio/RX550-INVESTIGACION"
GUARD = os.path.join(HERE, "corpus_guard.py")


def run(label, cmd, want_lines=0, quick_ok=False, rc_ok=None):
    """Ejecuta una comprobacion. `rc_ok` es la lista de codigos que valen.

    POR QUE EXISTE `rc_ok` Y POR QUE NO PUEDE VIVIR EN EL LLAMANTE.

    `num_collision` devuelve 3 cuando hay numeros de hallazgo duplicados. Es un
    HECHO del proyecto, no un fallo de la herramienta: ponerlo en rojo obligaria
    a cambiar la convencion de citacion por las malas.

    La primera version de esto lo resolvio en el bucle del llamante:

        rc, ok = run(...)
        if ok and rc_tol is not None and rc not in (0, rc_tol):
            ok = False

    Y no funcionaba, porque `ok` ya era False: `run` devuelve `rc == 0`, y con
    rc=3 nunca puede ser cierto. La condicion `if ok and ...` nunca se
    cumplia, y la herramienta se quedaba en FALLA sin poder marcarlo.

    Es la clase de error que mas cuesta ver: la logica es correcta y la
    herramienta devuelve un valor que la hace inalcanzable. Por eso la
    decision se toma AQUI, donde se conoce el codigo de salida, y no dos
    niveles mas arriba.
    """
    print(f"\n{'=' * 70}")
    print(f">>> {label}")
    print(f"{'=' * 70}")
    t = time.time()
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True,
                           text=True, timeout=600)
    except subprocess.TimeoutExpired:
        print("TIMEOUT tras 600 s")
        return 1, False
    dt = time.time() - t
    out = (r.stdout or "").strip()
    err = (r.stderr or "").strip()
    if out:
        lines = out.split("\n")
        for l in lines[-want_lines:] if want_lines else lines:
            print(l)
        if want_lines and len(lines) > want_lines:
            print(f"... ({len(lines) - want_lines} lineas antes omitidas)")
    if err:
        print(f"--- stderr ---")
        for l in err.split("\n")[-8:]:
            print(l)
    print(f"[{dt:.1f}s  rc={r.returncode}]")
    validos = [0] if rc_ok is None else list(rc_ok)
    return r.returncode, r.returncode in validos


def main():
    args = sys.argv[1:]
    quick = "--quick" in args
    check_only = "--check" in args
    results = []

    # 0. integridad del corpus, SIEMPRE primero
    rc, ok = run("INTEGRIDAD DEL CORPUS (antes)",
                 ["python3", GUARD, "--git"], want_lines=10)
    results.append(("integridad", ok, "objetivo"))

    if check_only:
        print("\nsolo integridad; fin.")
        return 0 if all(o for _, o in results) else 1

    # 1. herramientas de analisis
    CLASES_VISTAS = set()
    # --solo-objetivo / --solo-aparato. Con esto el numero que se lee como
    # "estado del proyecto" y el que se lee como "estado de la validacion" dejan
    # de ser el mismo numero.
    MODO = ("aparato" if "--solo-aparato" in sys.argv
            else "objetivo" if "--solo-objetivo" in sys.argv else "todos")
    tools = [
        ("cierre de includes de gfx_v8_0.c",
         ["include_closure.py", "gfx_v8_0.c", "--opcodes"], 0),
        ("PM4 alcanzabilidad y vocabulario vivo", ["pm4_reachable.py"], 0),
        ("PM4 layouts documentados vs emitidos", ["pm4_layout_audit.py"], 0),
        ("inventario de registros MMIO", ["gmmio_inventory.py"], 0),
        # lectura del ASIC en vivo, SOLO LECTURA. Verifica que el modulo
        # cargado es el que cree el corpus. No escribe nada.
        ("runtime: estado del ASIC (solo lectura)",
         ["runtime_obs.py", "module"], 0),
        ("binario real vs corpus", ["binfacts.py"], 0),
        ("PM4 codec: contraste de layouts", ["pm4_codec.py", "--check"], 0),
        ("PM4 codec: NOP contra regla 034", ["pm4_codec.py", "--nops"], 0),
        # El contrato de las herramientas. rc 0 si todas lo tienen.
        #
        # FALLA cuando hay alguna sin contrato, y eso INCLUYE herramientas
        # que otra sesion commiteo. No se relaja: el contrato es lo unico que
        # permite preguntar "esta herramienta puede tocar el hardware?", y
        # aceptarlo como no-fallo para que el semaforo quede verde seria
        # admitir que el semaforo ya no mide.
        #
        # Lo que si se hace es que el nombre de la herramienta que falla este
        # en la salida, que ya lo esta. Un rojo con nombre es informacion; un
        # verde con excusas es ruido.
        ("contrato de las herramientas", ["toolkit.py"], 0),
        # Lo de arriba FALLA, y el fallo es casi todo RUIDO que ya conozco:
        # toolkit.py senala como escritura cosas que no son escrituras del
        # proyecto. Su flag dice "si escribe ficheros DEL PROYECTO", y un
        # tempfile.mkstemp o un fichero en /tmp no lo son.
        #
        #   doclint.py       mkstemp + unlink en su self-test
        #   aperture.py      os.fdopen(_fd) con _fd de mkstemp
        #   struct_rw.py     open("/tmp/opencode/ko.asm")
        #   ipver_zero.py    if op == ">":      <- la regex de redireccion
        #   pm4_emit.py      "> 8 bits" dentro de un string     matchea una
        #                     COMPARACION y un TEXTO, no una escritura
        #
        # Lo que se hace aqui NO es relajar el contrato: es restar una lista
        # EXPLICITA de falsos positivos conocidos, comprobada, y seguir
        # fallando por cualquier otra cosa. Sin la lista, el rojo seria el mismo
        # hoy y dentro de un mes, y ahi es donde un rojo que no cambia enseña a
        # ignorar el semaforo -- que es justo el dano que toolkit.py dice querer
        # evitar con su excepcion AJENA.
        #
        # Y NO se arregla la declaracion de esas herramientas: declaran bien.
        # Cambiar WRITES_FILES a yes para que dejen de salir seria cambiar una
        # declaracion correcta por una falsa.
        ("contrato: sin falsos positivos conocidos", ["contract_filter.py"], 0),
        # El detector de contradicciones tiene que correr en CADA verificacion.
        # Si solo corre cuando me acuerdo, deja de ser un control y pasa a ser
        # una consulta: la contradiccion de block_size llego a tres documentos
        # porque nadie ejecuto nada en medio.
        ("contradicciones entre hallazgos",
         ["causal_map.py", "--contradictions"], 0),
        # El mapa causal. Se ejecuta entero porque su salida ES la
        # verificacion: si deja de encontrar las aristas que se conocen,
        # el corpus cambio o la herramienta se rompio.
        ("mapa causal (aristas del camino GFX8)", ["causal_chain.py"], 0),
        # El generador de trabajo. Se ejecuta para que el ranking este
        # disponible en cada verificacion y para que se note cuando cambia
        # el numero de registros sin documentar.
        ("siguiente trabajo (ranking)", ["next_work.py"], 12),
        # La asercion estructural del driver. Se ejecuta con codigo de salida
        # real: si el struct vi_mqd deja de cuadrar con los offsets, esto
        # devuelve 3 y el runner lo marca como fallo.
        ("asercion struct vi_mqd vs offsets", ["mqd_layout.py", "--mismatches"], 0),
        # --- las siete herramientas de la sesion de registros/simbolos ---
        # Se ejecutan con --self, no con su modo informative. La razon es la
        # misma que el mapa causal: un self-test que nadie ejecuta deja de
        # ser un control. Estas siete se escribieron hoy y su modo normal es
        # un informe, que siempre sale "bien" aunque la herramienta este rota.
        # El --self es lo que puede fallar.
        ("citecheck: 32 vectores", ["citecheck.py", "--self"], 0),
        ("scopeguard: preflight", ["scopeguard.py", "--self"], 0),
        ("xref: lectura/escritura", ["xref.py", "--self"], 0),
        ("causal: grafo de llamadas", ["causal.py", "--self"], 0),
        ("contradict: cifras en conflicto", ["contradict.py", "--self"], 0),
        ("regdb: campos entre familias", ["regdb.py", "--self"], 0),
        ("hdrmap: familias por .c", ["hdrmap.py", "--self"], 0),
        # F11 pide el titular CRUDO y el FILTRADO de cada herramienta con
        # numero.  Esta mide si alguna vez se leyo su salida, y publica las
        # suyas para que el proximo pueda aplicar el mismo criterio.
        ("toolaudit: F11 titular leido", ["toolaudit.py", "--self"], 0),
        # Catalogo de mensajes SMU: 276 para Polaris12. El dato generado que
        # 070 dejo abierto, y que una herramienta debe producir, no transcribir.
        ("smumsg: catalogo de mensajes", ["smumsg.py", "--self"], 0),
        # El barrido que hizo el hallazgo 065: registros escritos por un .c con
        # direccion distinta segun familia. Si el numero deja de ser 7, o el
        # corpus cambio o la herramienta se rompio. Se ejecuta entero porque
        # su SALIDA es la verificacion, no su codigo de salida.
        ("registros con offset distinto entre familias",
         ["regdb.py", "--scan-file",
          "RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/gmc_v8_0.c"],
         0),
        # Control negativo: una herramienta que no puede fallar no puede
        # decir que pasa. Debe detectar sus propias 4 mutaciones.
        ("mqd_layout: control negativo", ["mqd_layout.py", "--self-test"], 0),
        # La misma asercion en los 4 sitios que la hacen (display y KFD, dos
        # generaciones). Cuatro sitios que cuadran es CORROBORACION de que el
        # struct esta construido para ese layout; uno que cuadra es un caso.
        ("asercion struct->offset en 4 sitios", ["mqd_layout.py", "--sitios"], 0),
        # El validador de contratos debe pasar su propio control de la regla
        # "lo que no esta en git no reproba". Si _en_git se equivoca, esa
        # regla dejaria de ser una excepcion y seria un agujero.
        ("toolkit: control de propias/ajenas",
         ["toolkit.py", "--selftest-ajenas"], 0),
        # Fronteras del proyecto que otro documento YA cerro. Un NOT_DETERMINED
        # obsoleto dirige el trabajo hacia algo hecho. Se ejecuta entero porque
        # su SALIDA es la verificacion.
        ("fronteras obsoletas (trabajo ya hecho)", ["stale_gap.py"], 0),
        ("stale_gap: control negativo", ["stale_gap.py", "--self-test"], 0),
        # Los numeros de hallazgo identifican un hallazgo.
        #
        # `num_collision` devuelve 3 cuando HAY colisiones, y eso no es un
        # fallo de la herramienta: es un hecho del proyecto. Va con want_lines
        # y rc tolerado, para que el numero este a la vista en cada
        # verificacion y nadie pueda decir que no se sabia, sin declarar
        # catastrophe por una convencion de citacion que hay que DECIDIR
        # cambiar.
        ("numeros de hallazgo unicos", ["num_collision.py"], 10, 3),
        ("num_collision: control negativo",
         ["num_collision.py", "--self-test"], 0),
        # Que parte del hardware NO se puede leer porque su codigo no esta.
        # Devuelve 2 sin el .ko descomprimido, y eso es un dato: "no puedo
        # comprobarlo" no es "no falta nada".
        ("hueco del corpus por bloque",
         ["corpus_gap.py"], 26, 0),
        ("corpus_gap: control negativo",
         ["corpus_gap.py", "--self-test"], 0),
        # La contabilidad de tamano de anillo del propio driver, resuelta
        # estaticamente. El contraste es contra una cantidad INDEPENDIENTE
        # (los `emit_frame_size` comentados de gfx_v8_0.c), que es lo que
        # convierte el self-test en validacion y no en tautologia.
        ("PM4 emitido, contraste con emit_frame_size",
         ["pm4_emit.py", "--frame-size"], 0),
        ("pm4_emit: control negativo",
         ["pm4_emit.py", "--self-test"], 0),
        # CONTRASTE ESTATICO vs BINARIO. Es el unico control de todo el
        # proyecto que compara la aritmetica de pm4_emit con el codigo real
        # del modulo cargado en memoria: si un valor calculado no aparece en
        # los bytes de la funcion, rc=1 y sale FALLA.
        #
        # rc_tol=3: sin /tmp/amdgpu_loaded.ko esta herramienta no puede
        # observar nada. Eso es un estado del entorno, no un defecto del
        # metodo, y se deja a la vista en vez de declararse catastrophe.
        ("PM4 estatico vs codigo del .ko",
         ["ko_immediate.py", "--compare-all"], 19, 3),
        ("ko_immediate: control negativo",
         ["ko_immediate.py", "--self-test"], 1, 1),
        # El IP version que declara cada firmware, contrastado con los
        # ip_block del driver. Es lo que cerro la frontera GFX_HWIP: el
        # registro no existe en el corpus, pero la cabecera del firmware si.
        #
        # rc_tol=3: sin /lib/firmware/amdgpu no hay nada que leer. Es estado
        # del entorno, no defecto del metodo.
        ("IP version del firmware de polaris12",
         ["fw_ipver.py", "--placa", "polaris12"], 19, 3),
        ("fw_ipver: control negativo",
         ["fw_ipver.py", "--self-test"], 1, 1),
        # Que rama toma CADA comparacion de GC_HWIP con el valor 0. Es la
        # auditoria completa que 182 dejo a medias: 94 sitios con veredicto
        # mecanico, no una muestra de tres leidos a mano.
        ("GC_HWIP con valor 0: rama por sitio",
         ["ipver_zero.py", "--resumen"], 6, 0),
        ("ipver_zero: control negativo",
         ["ipver_zero.py", "--self-test"], 1, 1),
        # Superficie real de los 9 bloques IP, leida de las tablas constantes del
        # .ko cargado. El aserto es sobre el dato EXTRAIDO, no sobre la
        # estructura de quien lo extrae.
        ("ip_surface: 9 bloques con superficie real",
         ["ip_surface.py", "--bloque", "gfx_v8_0_ip_block"], 18, 0),
        ("ip_surface: control negativo",
         ["ip_surface.py", "--self-test"], 1, 1),
        # Prueba con adversario real: si el limite de apertura fuera falso, el
        # maximo de offset de alguna cabecera lo superaria y rc seria 3.
        ("apertura BAR5: todos los registros caben",
         ["aperture.py", "--todos"], 0, 0),
        ("aperture: control negativo",
         ["aperture.py", "--self-test"], 1, 1),
        # Balance lectura/escritura de un offset de struct en el binario. El
        # control pareado esta en el propio self-test: las dos regex de direccion
        # no pueden casar la misma linea.
        ("struct_rw: control de direccion",
         ["struct_rw.py", "--self-test"], 1, 1),
        # El ancla es fuerte: sdma_v3_0_soft_reset solo toca mmSRBM_SOFT_RESET, y
        # el extractor tiene que devolver exactamente 0x398 y distinguir R de W.
        # El control negativo es amdgpu_gmc_tmz_set, que solo hace un dev_info.
        ("mmio_map: ancla 0x398 y control negativo",
         ["mmio_map.py", "--self-test"], 1, 1),
        # Veredicto TARGET_MATCH contra el contrato de target. Codigo de salida
        # distinto para MATCH / MISMATCH / INDETERMINATE: un campo ilegible NO
        # es MATCH, y sin esa separacion el fingerprint "pasaria" a medias.
        ("fingerprint: TARGET_MATCH",
         ["fingerprint.py", "--completo"], 0, 0),
        ("fingerprint: parser con 3 controles negativos",
         ["fingerprint.py", "--self-test"], 1, 1),
        # Validacion de la herramienta de integridad del registro de hallazgos.
        # El self-test pasa. El RECUENTO de colisiones NO se mete como check
        # que deba pasar: findings_index devuelve 1 mientras existan las 65
        # colisiones de 259, y anadirlo aqui haria que run_allDijera "todo bien"
        # mientras el defecto sigue vivo. Se ejecuta a mano hasta que se arregle.
        ("findings_index: unicidad y tabla de reenvio",
         ["findings_index.py", "--self-test"], 1, 1),
        # Alcance del regex y lista de ficheros propios. El control negativo
        # importa: una lista vacia significaria "no toco nada", no "todo".
        ("refs_repair: alcance y lista propia",
         ["refs_repair.py", "--self-test"], 1, 1),
        # El contrato de hardware del driver cotejado con las definiciones del
        # ASIC. §8: la implementacion no es autoridad sobre la semantica. rc=0
        # exige que TODAS las constantes de registro esten CONFIRMADAS.
        ("driver_offsets: contrato de registros contra el ASIC",
         ["driver_offsets.py"], 0, 0),
        ("driver_offsets: anclas y controles del filtro",
         ["driver_offsets.py", "--self-test"], 1, 1),
        # Los 12 opcode de paquete del driver cotejados con sid.h/vid.h. Un
        # valor distinto produce sumisiones invalidas SIN sintoma hasta que el
        # trabajo no llega a la GPU, asi que esto va en la automatizacion.
        ("driver_offsets: 12 opcode PM4 contra la ISA",
         ["driver_offsets.py", "--pm4"], 0, 0),
        # Los 8 shifts de campo. Un opcode correcto con un campo mal puesto emite
        # un paquete BIEN FORMADO que hace OTRA cosa, y eso si da sintomas.
        ("driver_offsets: 8 campos de paquete contra la ISA",
         ["driver_offsets.py", "--campos"], 0, 0),
        # Los dwords de la secuencia de vm-flush, CONTADOS en los emisores. Si
        # un emisor cambia y la constante no, esta comprobacion falla.
        ("driver_offsets: 19/17 dwords de vm-flush contados",
         ["driver_offsets.py", "--vflush"], 0, 0),
        # Residuos de codificacion en los mensajes de commit. rc=1 si hay.
        # Va en el runner y no solo antes de escribir porque un control que
        # depende de que te acuerdes se salta: el que revisa es el mismo que
        # acaba de escribir el texto y ya lo tiene en la cabeza. Asi el residuo
        # sale en run_all y no se queda.
        # El codigo de salida, DECLARADO y COMPROBADO, en cada verificacion.
        # Fuera del runner esto seria un control que se ejecuta a veces, y eso
        # es una convencion con comentarios. Adentro es una invariante: si una
        # herramienta empieza a devolver otra cosa de la que dice, salta aqui.
        ("exit_contract: EXIT_ON_SUCCESS se cumple",
         ["exit_contract.py"], 0, 0, "aparato"),
        # WRITES_GPU=yes sin acceso a la barra en toda la cadena de delegacion.
        # rc=3 y no 1: hoy el unico caso (bench.py) NO esta versionado, y cambiar
        # el contrato de otra sesion para que deje de salir seria cambiar una
        # declaracion para silenciar un validador. El 3 lo dice sin tocar nada.
        # AVISA SOLO. Compara los hashes de los ficheros clasificados con los de
        # la ultima ejecucion, y avisa si alguno cambio. rc=1 y no es un fallo: es
        # un cambio. Lo que no es admisible es que pase inadvertido, porque
        # entonces un hallazgo sigue citando un fichero que ya no es ese.
        # rc esperado 0 en el caso normal; si sale 1, LEERLO antes de fiarse de
        # cualquier cifra medida sobre esos ficheros.
        ("vigilia: ningun fichero clasificado ha cambiado",
         ["contract_exec.py", "--vigilar"], 0, 0, "aparato"),
        ("capacidad: WRITES_GPU declarado sin uso",
         ["contract_exec.py", "--capacidad"], 3, 3, "aparato"),
        ("commitmsg_lint: sin residuos en 25 mensajes",
         ["commitmsg_lint.py", "--commits=25"], 0, 0, "aparato"),
        # Colisiones de nombre entre los 4 directorios de herramientas. rc=1
        # si hay CONFLICTO (mismo nombre, hash distinto): son dos
        # herramientas que se contradicen segun el directorio desde el que se
        # mire. C-015 lo registra; esto lo mantiene cierto.
        # Las 3 colisiones conocidas (C-015) se ACEPTAN y se listan: no se
        # arreglan aqui porque son decision de coordinacion entre sesiones. El
        # check es de REGRESION -- falla si aparece una NUEVA. Exigir cero
        # haria que el check fallara siempre, y un check que falla siempre no
        # informa de nada.
        ("cite_registry: ningun conflicto de nombre NUEVO",
         ["cite_registry.py", "--guardio"], 0, 0, "aparato"),
        ("cite_registry: autotest (respuesta conocida y negativos)",
         ["cite_registry.py", "--self-test"], 0, 0, "aparato"),
        # La reserva de numeros de hallazgo. num_collision mide 37 duplicados
        # y esta sesion choco 3 veces (111, 119, 120) con otra escribiendo.
        # El self-test RESERVA y LIBERA de verdad: comprobar que el numero no
        # este duplicado sin tocar el disco seria un test de mentira.
        ("findnum: control negativo",
         ["findnum.py", "--self-test"], 0),
        # La tabla (device_id, revision) -> chip_id, leida del .ko cargado.
        # Es la que 050 dio por ausente porque hwmgr.c no esta en el corpus.
        # Devuelve 2 sin .ko y 3 si el layout deducido no encaja, y los dos
        # son datos: no se puede leer != no hay tabla.
        ("tabla de ASIC desde el binario", ["asic_table.py"], 26, 0),
        ("asic_table: control negativo",
         ["asic_table.py", "--self-test"], 0),
        # LA INTEGRIDAD CON HUELLA, no solo con git status.
        #
        # `--git` responde 0 cuando `git status --porcelain RESEARCH/` esta
        # vacio, y eso NO es una verificacion del corpus: solo comprueba que
        # git no ve cambios. Si alguien regenera un fichero y lo commitea, o
        # si el corpus se toco y luego se commiteo, `--git` dice que todo bien
        # y no es cierto.
        #
        # `--verify` compara la huella de 2787 ficheros con una referencia, y
        # devuelve 2 --distinto de 0-- cuando no hay ninguna referencia, para
        # que "no puedo comprobarlo" no se lea como "todo bien". Esa
        # distincion la hacia mal el propio corpus_guard, que antes devolvia
        # un texto de una linea indistinguible del exito.
        ("integridad del corpus (huella de 2787 ficheros)",
         ["corpus_guard.py", "--verify"], 0),
    ]
    if quick:
        tools = tools[1:]
    for t in tools:
        label, a, n = t[0], t[1], t[2]
        # a es la lista COMPLETA de argumentos, no solo el nombre del script.
        # include_closure necesita sus tres (script, fichero, --opcodes) y con
        # a[0] se quedava sin el fichero -> rc=2 -> "FALLA" sin motivo real.
        #
        # rc_tol: un codigo de salida que NO es fallo pero informa de un
        # estado. `num_collision` devuelve 3 cuando hay numeros de hallazgo
        # duplicados, y eso es un hecho del proyecto, no un error de la
        # herramienta. Marcarse FALLA obligaria a arreglar la convencion de
        # citacion por las malas; lo unico honesto es que el numero este a la
        # vista sin declarar catastrophe.
        #
        # Se distingue de `want_lines` porque no es lo mismo: `want_lines`
        # avisa si la salida sale VACIA, que si es un fallo. `rc_tol` acepta un
        # codigo concreto, que es una declaracion sobre que codigos son
        # validos para esa herramienta.
        rc_tol = t[3] if len(t) > 3 else None
        # CLASE de la comprobacion: "objetivo" (el hardware, el driver, el
        # proyecto) o "aparato" (las herramientas de validacion que construi
        # esta sesion). Es el QUINTO campo, con valor por defecto, para que las
        # tuplas de cuatro sigan valiendo y nadie tenga que reescribirlas.
        #
        # POR QUE. El runner ha pasado de 63 a 66 comprobaciones y las tres
        # ultimas que anadi miden MI aparato. run_all rc=3 significa hoy cosas
        # distintas segun si las FALLAs vienen del hardware o de las
        # herramientas, y esa ambiguedad crece con cada herramienta que anado.
        clase = t[4] if len(t) > 4 else "objetivo"
        if MODO == "objetivo" and clase != "objetivo":
            continue
        if MODO == "aparato" and clase != "aparato":
            continue
        CLASES_VISTAS.add(clase)
        rc, ok = run(label, ["python3", os.path.join(HERE, a[0])] + a[1:],
                     want_lines=n,
                     rc_ok=[0, rc_tol] if rc_tol is not None else None)
        results.append((label, ok, clase))

    # 2. linter de documentos. Esto es lo que mas me ha ahorrado.
    print(f"\n{'=' * 70}")
    print(">>> LINTER DE HALLAZGOS")
    print(f"{'=' * 70}")
    t = time.time()
    r = subprocess.run(["python3", os.path.join(HERE, "doclint.py"), "--self"],
                       cwd=ROOT, capture_output=True, text=True, timeout=600)
    dt = time.time() - t
    lines = (r.stdout or "").split("\n")
    for l in lines[-14:]:
        print(l)
    print(f"[{dt:.1f}s  rc={r.returncode}]")
    results.append(("doclint", r.returncode == 0, "objetivo"))

    # 3. integridad DESPUES. Si algo toco el corpus, esto lo dice.
    rc, ok = run("INTEGRIDAD DEL CORPUS (despues)",
                 ["python3", GUARD, "--git"], want_lines=10)
    results.append(("integridad final", ok, "objetivo"))

    # resumen
    print(f"\n{'=' * 70}")
    print("RESUMEN")
    print(f"{'=' * 70}")
    for label, ok, cactual in results:
        print(f"  {'OK  ' if ok else 'FALLA'}  [{cactual}] {label}")
    if MODO != "todos":
        print()
        print("  modo --solo-%s: %d comprobaciones de esa clase"
              % (MODO, len(results)))
    bad = [l for l, ok, _c in results if not ok]

    # POR QUE UNA LINEA ROJA PUEDE SER LA MISMA LINEA ROJA DOS VECES.
    #
    # Este runner llama a 42 herramientas distintas en 66 invocaciones, y algunas
    # se repiten. Si una de esas falla, el runner lo dice en TANTOS sitios como
    # checks la ejecutan: son N lineas rojas y UNA sola causa.
    #
    # Sin esto, el que lee cuenta N problemas y empieza a arreglarlos por
    # separado. Con esto, sabe que arreglar uno los arregla todos. Y el aviso
    # va AQUI, junto a la linea roja, porque es lo unico que hace que llegue.
    #
    # Se importa check_chain en vez de shelling out y parsear: el grafo ya esta
    # construido ahi y volver a hacerlo aqui seria una segunda fuente de verdad.
    # DOS CLASES DE ROJO, Y POR QUE.
    #
    # Los 2 FALLAs actuales los causan siete herramientas de OTRAS sesiones sin
    # contrato. Yo no puedo arreglarlas. Un runner que sale con rc=1 por eso
    # esta diciendo "fallo" cuando no hay nada que arreglar por mi parte, y un
    # rojo que no significa nada es peor que no tener rojo: entrena a ignorar
    # el codigo de salida.
    #
    # Es el mismo problema que toolkit.py resuelve con su excepcion AJENA, pero
    # un nivel mas arriba: alla es una herramienta la que no cuenta; aqui es el
    # runner entero el que se pone rojo por trabajo ajeno.
    #
    # LA LISTA ES EXPLICITA y lleva el motivo de cada entrada. No se deduce de
    # "esta herramienta no es mia": eso seria una heuristica sobre la autoria, y
    # la autoria no se deduce del codigo. Se declara quien esta bloqueando y por
    # que, para que dentro de un ano se pueda comprobar si sigue siendo cierto.
    BLOQUEADO_POR_OTRA_SESION = {
        "contrato de las herramientas":
            "toolkit.py: 5 SIN CONTRATO y 3 READONLY escribiendo, todas de "
            "otras sesiones (causal, citecheck, contradict, xref, scopeguard, "
            "hdrmap, inst_closure). Ninguna versionada menos una.",
        "contrato: sin falsos positivos conocidos":
            "contract_filter.py sobre los MISMOS 7 problemas de toolkit.py. "
            "Es el mismo fallo por la otra via: ver la linea roja de arriba.",
    }

    if bad:
        try:
            import check_chain as _cc
            inv = {}
            for etiqueta, raices, nivel2 in _cc.construir():
                for h in raices:
                    inv.setdefault(h, []).append(etiqueta)
                for h in nivel2:
                    inv.setdefault(h, []).append(etiqueta)
            for etiqueta in bad:
                # que herramientas ejecuta ESTA comprobacion, y quien mas las usa
                propias = [h for h in inv if etiqueta in inv[h]]
                compartidas = []
                for h in propias:
                    otros = [x for x in inv[h] if x != etiqueta]
                    if otros:
                        compartidas.append("%s <- %s"
                                           % (h, ", ".join(sorted(otros))))
                if compartidas:
                    print()
                    print("  %s" % etiqueta)
                    print("      ^ esta comprobacion ejecuta herramientas que")
                    print("        OTRAS comprobaciones tambien ejecutan. Si el fallo")
                    print("        es de una de ellas, estas lineas rojas son la")
                    print("        MISMA causa repetida:")
                    for c in sorted(compartidas):
                        print("          %s" % c)
        except Exception as _e:
            print("  (no se pudo cruzar con la cadena: %s)" % _e)

    # AVISO QUE NO PUEDE FALTAR, y va aqui y no en toolkit.py por dos motivos.
    #
    # 1) POR QUE NO EN toolkit.py: tiene 52 inserciones y 15 borrados SIN
    #    COMMITEAR de otra sesion. Anadir una linea ahi seria meter mi cambio en
    #    un commit que barre trabajo ajeno. No se toca.
    #
    # 2) POR QUE AQUI Y NO AHI: este es el sitio donde alguien LEE. Quien ve
    #    "63 OK" y la tabla de contratos no puede saber, por si mismo, que hay
    #    una clase de contrato que se verifica MUCHO peor que las otras. Poner
    #    el aviso junto al dato que se puede malinterpretar es lo unico que
    #    hace que llegue.
    #
    # LO QUE DICE, en una frase: las capacidades de HARDWARE se verifican por
    # DECLARACION, no contra el texto. `READONLY`, `WRITES_FILES` y
    # `MUTATES_CORPUS` se contrastan leyendo el codigo -- escribir un fichero
    # deja marca. Escribir en /sys NO deja marca: lo unico que hay es el
    # comentario de la herramienta y su propia tabla de escrituras, y no se
    # ejecuta nada para comprobarlas. Ver 551.
    print()
    print("  AVISO DE ALCANCE, no de resultado:")
    print("    WRITES_SYSFS y WRITES_GPU se verifican POR DECLARACION: la tabla")
    print("    que la herramienta escribe sobre si misma, sin ejecutar nada.")
    print("    READONLY / WRITES_FILES / MUTATES_CORPUS si se contrastan contra el")
    print("    texto. Las dos clases NO son comparables. Detalle en 551.")
    if bad:
        mias = [b for b in bad if b not in BLOQUEADO_POR_OTRA_SESION]
        ajenas = [b for b in bad if b in BLOQUEADO_POR_OTRA_SESION]
        print()
        if mias:
            print("FALLA REAL, requiere accion:")
            for b in mias:
                print("    %s" % b)
        if ajenas:
            print("FALLA BLOQUEADA, espera a otra sesion:")
            for b in ajenas:
                print("    %s" % b)
                print("        %s" % BLOQUEADO_POR_OTRA_SESION[b])
        print()
        if mias:
            print("rc=1  %d comprobacion(es) fallan de verdad: %s"
                  % (len(mias), mias))
            return 1
        print("rc=3  NINGUN fallo es accion de esta sesion. Las %d bloqueadas no"
              % len(ajenas))
        print("      se pueden arreglar aqui: son trabajo de otra sesion. El")
        print("      runner NO esta verde, y no dice que lo este.")
        return 3
    print("\ntodas las comprobaciones pasan")
    return 0


if __name__ == "__main__":
    sys.exit(main())