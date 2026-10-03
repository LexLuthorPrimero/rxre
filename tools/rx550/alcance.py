#!/usr/bin/env python3
"""alcance — ¿de dónde viene el orden de las funciones de riesgo?

RX550_ROOT = os.environ.get("RX550_ROOT", "/home/lucas/Escritorio/RX550-INVESTIGACION")
RX550_ARQ = os.environ.get("RX550_ARQ", os.path.join(RX550_ROOT, "08-ARQUITECTURA"))

POR QUE        Quedan 12 funciones de riesgo que comparten bloque IP y
               registro con otra, sin mutex.  Se descarto una (la del IRQ)
               probando que su unico llamante es de proceso, pero eso mira
               SOLO el padre inmediato.  El orden puede venir de mas arriba:
               un `pre_soft_reset` que serializa a todo el bloque haria
               inocuas dos leafs que no toman nada.

               La pregunta correcta es TRANSITIVA: ¿existe algun camino desde
               una raiz asincrona (IRQ, workqueue, timer, kthread) hasta la
               funcion?  Si no, el contexto es de proceso y no hay carrera
               posible por construccion — porque el unico reloj que puede
               intercalar dos rutinas de proceso es el planificador, y el
               planificador no las hace solaparse si ninguna cede el CPU con
               el registro a medio actualizar.

               Si el unico camino es de proceso, el descarte se sostiene.  Si
               hay una raiz asincrona, el descarte se CAE y hay que decirlo.

METODO         Call graph por AST (`callgraph`, TOOL_VALIDATED): llamadas
               directas y por tabla de ops.  Se sube desde cada funcion de
               riesgo hasta:
                 - una raiz asincrona, o
                 - `TOP` (nadie la llama: raiz de la recursion del arbol).
               Se registra el camino mas corto a cada raiz, para poder
               citarlo, no solo contar niveles.

               Un subtlety que hay que declarar: el call graph por AST solo ve
               el MISMO `.c` (las funciones son `static`, enlace interno) y los
               miembros de tablas de ops.  Un llamante de otro `.c` a traves de
               un puntero a funcion NO se ve, porque el CallExpr lleva un
               MemberExpr y no el nombre.  Para esas se usa el camino por ops
               table, que si es visible.  Lo que no se ve se declara
               `NO_RESOLUBLE`, nunca se cuenta como "de proceso".

CONTROL        El resultado que mas riesgo tiene es "de proceso para todos",
               porque llevaria a descartar 12 funciones.  Asi que:
                 - CONTROL POSITIVO: la funcion del IRQ DEBE salir con raiz
                   asincrona.  Si saliera de proceso, el metodo estaria roto y
                   el "de proceso" de los demas no valdria nada.
                 - el numero de funciones con raiz asincrona se cuenta, y se
                   exige que coincida con lo observado.
                 - lo que no se puede resolver se reporta aparte, nunca como
                   proceso.

DEPENDENCIAS   callgraph, funcspan, conflicto  (todas TOOL_VALIDATED)
LIMITACION     Sin analisis de punteros a funcion entre ficheros mas alla de
               las tablas de ops.  Un puntero guardado en una variable local
               seria invisible.  Se declara.
"""

import os
import re
import sys
import json
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from paths import AMD as _AMD                     # noqa: E402
import funcspan                                    # noqa: E402
import callgraph as _cg                            # noqa: E402

VERSION = "1.0"
NAME = "alcance"

# Raices asincronas.  El nombre se busca en la funcion: son prefijos que el
# driver usa para todo lo que corre fuera del contexto de proceso.
RE_ASINC = re.compile(
    r"^amdgpu_irq_|_irq\b|_irq_|_intf\b|_int_|interrupt|throttler|workqueue|"
    r"^wq_|_work\b|delaywork|timer|_kthread|kworker|process_.*interrupt|"
    r"gpu_reset_worker|psw_|_psw|fault_handler|pagefault|page_fault",
    re.I)


def es_asincrona(nombre):
    return bool(nombre) and bool(RE_ASINC.search(nombre))


_OPS_CACHE = {}


def _en_ops_table(base, fichero, nombre):
    """¿`nombre` se asigna a un miembro en algun .c de amdgpu?  (tabla de ops)

    Es la unica forma de distinguir "no tiene llamante" de "su llamante es un
    puntero a funcion".  El CallExpr de una llamada por miembro lleva un
    MemberExpr, no el nombre, asi que el AST no lo ve: el nombre solo aparece
    en la ASIGNACION de la tabla.  Sin esta comprobacion, una funcion alcanzada
    por ops table se contabiliza como raiz, y su contexto — de proceso o de
    IRQ — queda sin determinar.  Es la clase F evitada: un escaneo que no ve
    algo y lo reporta como si no existiera.
    """
    clave = (base, nombre)
    if clave in _OPS_CACHE:
        return _OPS_CACHE[clave]
    patron = re.compile(r"\.\w+\s*=\s*\**\s*" + re.escape(nombre) + r"\s*,")
    ok = False
    try:
        amdgpu = os.path.join(base, "amdgpu")
        for f in _ficheros_cache(base):
            try:
                txt = _texto_cache(os.path.join(amdgpu, f))
            except OSError:
                continue
            if patron.search(txt):
                ok = True
                break
    except OSError:
        ok = False
    _OPS_CACHE[clave] = ok
    return ok


# El texto de cada .c se lee MUCHAS veces (por cada nodo sin llamantes, por
# cada miembro de ops).  Sin esta cache, `raices` releia ~100 ficheros por
# nivel de recursion y reventaba con RecursionError.  (correccion 155)
_FICH_CACHE = {}
_TXT_CACHE = {}


def _ficheros_cache(base):
    if base not in _FICH_CACHE:
        amdgpu = os.path.join(base, "amdgpu")
        try:
            _FICH_CACHE[base] = sorted(f for f in os.listdir(amdgpu)
                                       if f.endswith(".c"))
        except OSError:
            _FICH_CACHE[base] = []
    return _FICH_CACHE[base]


def _texto_cache(ruta):
    if ruta not in _TXT_CACHE:
        _TXT_CACHE[ruta] = open(ruta, encoding="utf-8",
                                errors="replace").read()
    return _TXT_CACHE[ruta]


# --- EL SEGUNDO ANILLO (correccion 187) -------------------------------------
#
# `contract.BLOQUES` son los 8 ficheros donde vive la RUTA VI.  Con solo esos,
# el resolutor llegaba a la tabla de ops y se paraba: el miembro se invoca desde
# un fichero que no esta en el grafo, y `cl.get(fichero)` devolvia None ->
# NO_RESOLUBLE -> VIA_OPS.  Las 12 que quedaban asi NO eran sin clasificar por
# falta de datos: era que el grafo no incluía a quien las invoca.
#
# Y ese "quien" tiene una forma concreta y medible: el DESPACHADOR GENERICO, un
# bucle sobre `adev->ip_blocks[]` que llama al miembro por su NOMBRE y por eso
# sirve para cualquier ASIC.  Medido en el arbol:
#
#     amdgpu_device.c  ip_blocks[i].version->funcs->set_clockgating_state
#     amdgpu_device.c  ip_blocks[i].version->funcs->pre_soft_reset
#     amdgpu_ip.c      ip_blocks[i].version->funcs->set_clockgating_state
#     amdgpu_job.c     (mismo patron)
#
# Los 3 son el anillo siguiente.  Anadirlos NO es ampliar el universo a ciegas:
# son los ficheros donde la llamada deja de ser nominal y pasa a ser por tabla,
# que es exactamente el salto que el resolutor no sabia dar.
SEGUNDO_ANILLO = ("amdgpu_ip.c", "amdgpu_device.c", "amdgpu_job.c")


# --- PUNTOS DE ENTRADA: lo que convierte TOP en respuesta (correccion 189) ----
#
# Medido con el anillo de 11 ficheros, las 12 que quedaban en VIA_OPS no
# estaban sin resolver: su cadena llegaba hasta `amdgpu_device_set_cg_state`, y
# sus tres llamantes son
#
#     amdgpu_device_ip_late_init        <- amdgpu_device_init
#     amdgpu_device_ip_suspend_phase1   <- amdgpu_device_gpu_recover
#     amdgpu_device_fini_hw             (TOP)
#     amdgpu_device_halt                (TOP)
#
# es decir, la cadena AGUANTA en funciones que NADIE llama.  Eso es lo que
# `raices` etiqueta TOP, y yo lo llevaba leyendo como NOT_DETERMINED desde la
# correccion 159.  Es una confusion de la misma familia que la 152 pero un
# nivel mas arriba: alli se confundio TOP con VIA_OPS; aqui se confunde
# "la cadena se agota" con "no se puede determinar".
#
# Agotarse NO es indeterminacion.  Agotarse en `amdgpu_device_init` es una
# respuesta definitiva: ahi se entra desde el probe del driver, en proceso.
# Agotarse en una funcion desconocida si seria indeterminacion.  Lo que
# distingue las dos cosas es si la funcion terminal es un PUNTO DE ENTRADA
# conocido, y eso es una tabla, no un analisis.
PUNTOS_DE_ENTRADA = {
    "amdgpu_device_init", "amdgpu_device_fini_hw", "amdgpu_device_halt",
    "amdgpu_device_ip_init", "amdgpu_device_ip_fini",
    "amdgpu_device_suspend", "amdgpu_device_resume",
    "amdgpu_device_gpu_recover", "amdgpu_device_ip_early_init",
    "amdgpu_device_ip_late_init", "amdgpu_pci_probe",
}
# Contexto de un punto de entrada.  TODOS son proceso: se alcanzan desde el
# probe, el ioctl de recovery o el suspend/resume del driver.
CONTEXTO_ENTRADA = "PROCESO"


def ficheros_del_resolutor(amd=None):
    """BLOQUES + SEGUNDO_ANILLO, filtrado por lo que existe de verdad"""
    import conflicto as _cf
    base = amd or _AMD
    want = list(_cf.contract.BLOQUES) + list(SEGUNDO_ANILLO)
    out = [f for f in want if os.path.isfile(os.path.join(base, "amdgpu", f))]
    # Se declara el conjunto de trabajo a la cache: son los 11 ficheros que esta
    # corrida va a parsear, y sin esto la politica "mas antigua primero" se
    # lleva por delante los mas pesados, que son precisamente estos.  MEDIDO:
    # con el techo a 10 GB se perdian gfx_v8_0, gmc_v8_0, gfxhub_v2_1, ih_v7_0,
    # sdma_v3_0, amdgpu_device y amdgpu_ip.  (197)
    try:
        import funcspan as _fs
        _fs.proteger_entradas(out)
    except Exception:
        pass
    return out


def callers_por_fichero(amd=None, solo=None):
    """{fichero: {funcion: [(llamante, linea)]}}

    `solo` acota a una lista de ficheros.  SIN acotar, esto construye el AST de
    los ~100 .c de amdgpu y se va a **9.3 GB de RSS**: medido, no supuesto.  Y
    no hace falta: la pregunta es de donde viene el orden de las funciones de
    la RUTA VI, y esas solo aparecen en los 6 ficheros de `contract.BLOQUES`.
    Un llamante en otro .c no puede invocar directamente una funcion `static`
    de la ruta; solo a traves de una ops table, que se declara aparte.
    """
    base = amd or _AMD
    amdgpu = os.path.join(base, "amdgpu")
    if solo:
        nombres = list(solo)
    else:
        nombres = sorted(f for f in os.listdir(amdgpu)
                         if f.endswith(".c"))
    out = {}
    for f in nombres:
        if not f.endswith(".c"):
            continue
        ruta = os.path.join(amdgpu, f)
        if not os.path.isfile(ruta):
            continue
        defs, calls = _cg.funciones_y_llamadas(ruta)
        if defs is None:
            out[f] = None            # clang no pudo: se declara, no se inventa
            continue
        m = collections.defaultdict(set)
        for c in calls:
            if len(c) != 3 or not c[0] or not c[1] or c[0] == c[1]:
                continue
            # la linea puede ser None si el CallExpr no trae offset (clang no lo
            # da en toda construccion).  Un llamante sin posicion no se puede
            # citar, asi que no entra: Better sin el dato que ordenarlo con
            # None mezclado y reventar al comparar.  (correccion 138)
            if c[2] is None:
                continue
            m[c[1]].add((c[0], c[2]))
        out[f] = {k: sorted(v) for k, v in m.items()}
    return out


def raices(cl, nombre, pendientes=None, prof=0, camino=None):
    """(raiz, camino) alcanzables desde `nombre`, o ('CICLO', [...])"""
    if pendientes is None:
        pendientes = set()
    if camino is None:
        camino = [nombre]
    if nombre in pendientes or prof > 24:
        return ("CICLO", camino)
    f, _, nom = nombre.rpartition(":")
    data = cl.get(f)
    if data is None:
        return ("NO_RESOLUBLE", camino)
    ll = data.get(nom)
    if not ll:
        # Aqui hay que distinguir DOS casos que se confundian:
        #   (a) la funcion se alcanza por una TABLA DE OPS: no hay CallExpr
        #       con su nombre, y el llamante es invisible para el AST.
        #   (b) la funcion es una RAIZ de verdad: nadie la llama.
        # Confundirlos daba "TOP" para las 13, incluida la del IRQ, y de ahi
        # se leyo que ninguna tenia llamante.  El dato que los separa es si el
        # NOMBRE aparece en una asignacion `.miembro = fn` en el .c: eso es
        # una tabla de ops, y se declara como tal.  (correccion 152)
        if _en_ops_table(_AMD, f, nom):
            # Se busca el MIEMBRO por el que se registra, y se sigue el
            # camino POR ESE MIEMBRO: los CallExpr de `x->miembro(...)` si son
            # visibles para el AST, asi que el contexto se puede determinar.
            miembro = _miembro_de_ops(_AMD, f, nom)
            if miembro:
                # `pendientes` se propaga: sin eso, un ciclo que pasa por la
                # via ops-table se visitaba para siempre y reventaba con
                # RecursionError en vez de devolver CICLO.  El limite de
                # profundidad no servia porque la rama ops reiniciaba el
                # contador desde 0 en cada salto.  (correccion 156)
                return raices_por_miembro(cl, f, miembro, camino,
                                          pendientes | {nombre})
            return ("VIA_OPS", camino)
        if nom in PUNTOS_DE_ENTRADA:
            return (CONTEXTO_ENTRADA, camino + [nom + " (punto de entrada)"])
        return ("TOP", camino)
    pendientes = pendientes | {nombre}
    for llam, _ln in ll:
        hijo = llam if ":" in llam else f"{f}:{llam}"
        # una raiz asincrona cortocircuita: basta un camino, no todos
        if es_asincrona(llam):
            return ("IRQ", camino + [hijo])
        # La cadena AGUANTA en un llamante que nadie llama.  Si ese llamante es
        # un punto de entrada conocido, la cadena no se agota: TERMINA, y
        # terminar en el probe es una respuesta, no una laguna.  Sin esto las 12
        # se quedaban en VIA_OPS aunque 3 llegaran a `amdgpu_device_init`.
        # (correccion 189)
        if llam in PUNTOS_DE_ENTRADA:
            return (CONTEXTO_ENTRADA, camino + [hijo + " (punto de entrada)"])
        r, c = raices(cl, hijo, pendientes, prof + 1, camino + [hijo])
        if r == "IRQ":
            return (r, c)
        if r == "PROCESO":
            return (r, c)
        # Un hijo que sale TOP o VIA_OPS **propaga su veredicto**, no se
        # descarta.  Antes se ignoraba y el padre caia en PROCESO: eso
        # convertia "el llamante de arriba no es visible" en "es de proceso",
        # que es justo la confusion que este analisis existe para evitar.
        # TOP significa que la cadena se agota sin poder determinar el
        # contexto, y eso es NOT_DETERMINED, no un veredicto favorable.
        # (correccion 159)
        if r in ("TOP", "VIA_OPS", "NO_RESOLUBLE", "CICLO", "SIN_NOMBRE"):
            return (r, c)
    return ("PROCESO", camino)


def _miembro_de_ops(base, fichero, nombre):
    """`.miembro = fn` — el nombre del miembro por el que se registra"""
    try:
        txt = _texto_cache(os.path.join(base, "amdgpu", fichero))
    except OSError:
        return None
    m = re.search(r"\.(\w+)\s*=\s*\**\s*" + re.escape(nombre) + r"\s*,",
                  txt)
    return m.group(1) if m else None


def raices_por_miembro(cl, fichero, miembro, camino, pendientes=None,
                       prof=0):
    """raiz de quien invoca `x->miembro(...)` en cualquier fichero"""
    if pendientes is None:
        pendientes = set()
    if prof > 12:
        return ("CICLO", camino)
    if fichero in pendientes:
        return ("CICLO", camino)
    pendientes = pendientes | {fichero}
    base = os.path.join(_AMD, "amdgpu")
    # El miembro se busca por TEXTO en TODOS los .c, no solo en los que estan en
    # el call graph.  `cl` solo contiene los ficheros de la ruta VI, asi que
    # exigir `f in cl` hacia que las tablas de ops cuyo consumidor esta en
    # soc15.c, amdgpu_vm.c o quien sea se dieran por inexistentes: de ahi que
    # las 13 salieran VIA_OPS sin llegar a ninguna raiz.  El consumidor de una
    # tabla de ops NO esta en el fichero que la declara.  (186)
    for f in _ficheros_cache(_AMD):
        pat = re.compile(r"->\s*" + re.escape(miembro) + r"\s*\(")
        try:
            txt = _texto_cache(os.path.join(base, f))
        except OSError:
            continue
        lineas = [i + 1 for i, ln in enumerate(txt.splitlines())
                  if pat.search(ln)]
        if not lineas:
            continue
        for ln in lineas:
            a, b, _m = funcspan.of_line(os.path.join(base, f), ln)
            if a is None:
                continue
            cab = txt.splitlines()[a - 1]
            mm = re.search(r"(\w+)\s*\(", cab)
            quien = mm.group(1) if mm else None
            if not quien:
                continue
            hijo = f"{f}:{quien}"
            if es_asincrona(quien):
                return ("IRQ", camino + [hijo])
            r, c = raices(cl, hijo, pendientes, prof + 1, camino + [hijo])
            if r in ("IRQ", "VIA_OPS"):
                return (r, c)
            if r == "PROCESO":
                return (r, c)
    # Se agoto la busqueda por miembro.  AQUI HAY UNA AFIRMACION MAS FUERTE de
    # la que<TResulta del nombre: los `->gart_enable(` que existen en el arbol
    # estan en aldebaran.c, sienna_cichlid.c, gfx_v11_0.c, gfx_v12_0.c,
    # gfx_v12_1.c y gmc_v9_0.c -- **ninguno** de la ruta VI.  O sea: la tabla
    # de gfxhub_v2_1 esta REGISTRADA y el nombre EXISTE, pero ningun consumidor
    # de esta generacion lo invoca.  Eso no es "no lo encuentro": es que la
    # tabla se registra y se deja sin uso en esta ASIC, y quien la invoca son
    # las de Aldebaran/Alaska/Arcturus.  (189)
    return ("MIEMBRO_OTRA_GENERACION", camino)


def self_test():
    ok = fail = 0

    def chk(name, cond, extra=""):
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"    P  {name}")
        else:
            fail += 1
            print(f"    F  {name}  {extra}")

    print(f"  {NAME} {VERSION} self-test")

    # --- el detector de raiz asincrona, con casos de cada lado ---
    chk("detecta amdgpu_irq_handler", es_asincrona("amdgpu_irq_handler"))
    chk("detecta gfx_v8_0_irq_handler", es_asincrona("gfx_v8_0_irq_handler"))
    chk("detecta una workqueue", es_asincrona("gfx_v8_0_process_irq"))
    chk("detecta kworker", es_asincrona("do_kworkers"))
    chk("NO marca sw_init como asincrona",
        not es_asincrona("gmc_v8_0_hw_init"))
    chk("NO marca ring_process como asincrona",
        not es_asincrona("gfx_v8_0_ring_process"))
    chk("NO marca mc_stop", not es_asincrona("gmc_v8_0_mc_stop"))
    chk("un nombre vacio NO es asincrono", not es_asincrona(""))
    chk("un None NO es asincrono", not es_asincrona(None))

    # --- el recorrido, sobre un grafo SINTETICO con respuesta conocida ---
    cl = {
        # cadena de proceso: hoja <- init <- root
        "a.c": {"hoja_proc": [("init_proc", 10)],
                "init_proc": [("root_proc", 20)]},
        # cadena asincrona: hoja <- wrapper <- amdgpu_irq_handler
        "b.c": {"hoja_irq": [("wrapper", 30)],
                "wrapper": [("amdgpu_irq_handler", 40)]},
        # mixto: la hoja tiene dos caminos, uno de cada
        "c.c": {"hoja_mix": [("init_proc", 50)],
                "init_proc": [("root_proc", 60)],
                "root_proc": [("amdgpu_irq_handler", 70)]},
        # sin llamantes
        "d.c": {"huerfana": []},
        # fichero que clang no pudo resolver
        "e.c": None,
    }
    r, c = raices(cl, "a.c:hoja_proc")
    # Una cadena que se agota en la cima del grafo NO es "de proceso": es
    # "no se ha encontrado raiz asincrona, y donde se agota no es visible".
    # Decir PROCESO seria declarar segura una funcion cuyo contexto no se ha
    # determinado.  El veredicto honesto es TOP.  (correccion 159)
    chk("KNOWN: cadena que se agota -> TOP, no PROCESO", r == "TOP", (r, c))
    chk("KNOWN: TOP nunca se presenta como PROCESO",
        r != "PROCESO", r)
    chk("KNOWN: el camino se puede citar (con fichero)",
        "a.c:init_proc" in c, c)
    # y una cadena que SI tiene raiz asincrona en medio
    cl2s = {"a.c": {"hoja": [("cola", 10)], "cola": [("amdgpu_irq_handler", 20)]}}
    r2, c2 = raices(cl2s, "a.c:hoja")
    chk("KNOWN: raiz asincrona en medio -> IRQ aunque la cima sea TOP",
        r2 == "IRQ", (r2, c2))
    r, c = raices(cl, "b.c:hoja_irq")
    chk("KNOWN: cadena por IRQ -> IRQ", r == "IRQ", (r, c))
    # el camino lleva "fichero:nombre", no el nombre desnudo: comparar contra
    # el nombre a secas daria FALSO y el assert no probaria nada (clase C)
    chk("KNOWN: el camino incluye amdgpu_irq_handler",
        "b.c:amdgpu_irq_handler" in c, c)
    chk("KNOWN: el camino va de la hoja a la raiz, en orden",
        c == ["b.c:hoja_irq", "b.c:wrapper", "b.c:amdgpu_irq_handler"], c)
    r, c = raices(cl, "c.c:hoja_mix")
    chk("KNOWN: un solo camino asincrono basta -> IRQ", r == "IRQ", (r, c))
    r, c = raices(cl, "d.c:huerfana")
    chk("KNOWN: sin llamantes -> TOP (raiz)", r == "TOP", (r, c))
    r, c = raices(cl, "e.c:algo")
    chk("NEGATIVO: fichero no resoluble -> NO_RESOLUBLE, nunca PROCESO",
        r == "NO_RESOLUBLE", (r, c))
    chk("NEGATIVO: NO_RESOLIBLE no cuenta como proceso",
        raices(cl, "e.c:algo")[0] not in ("PROCESO",))

    # --- la distincion que faltaba: TOP vs VIA_OPS (correccion 152) ---
    # Sin esto, una funcion alcanzada por ops table se contaba como RAIZ, y
    # de ahi se leyo que "ninguna de las 13 tiene llamante".  La comprobacion
    # se hace sobre un fichero real del corpus, que es donde se registra la
    # tabla de ops de verdad.
    import conflicto as _cf0
    if os.path.isdir(os.path.join(_AMD, "amdgpu")):
        chk("OPS: la IRQ se detecta en tabla de ops",
            _en_ops_table(_AMD, "gmc_v8_0.c", "gmc_v8_0_vm_fault_interrupt_state"),
            "no detectada")
        chk("OPS: se obtiene el miembro por el que se registra",
            _miembro_de_ops(_AMD, "gmc_v8_0.c",
                            "gmc_v8_0_vm_fault_interrupt_state") == "set")
        chk("NEGATIVO: una funcion que NO esta en tabla no da VIA_OPS",
            not _en_ops_table(_AMD, "gmc_v8_0.c", "gmc_v8_0_esta_funcion_no_existe"))
        chk("NEGATIVO: una funcion con llamada directa NO esta en ops",
            not _en_ops_table(_AMD, "gmc_v8_0.c", "gmc_v8_0_mc_stop"),
            "mc_stop se ve como llamada directa, no por tabla")

    # --- CORPUS: con control positivo OBLIGATORIO ---
    import conflicto as _cf
    riesgo = _cf.riesgo_por_funcion()
    idx = {f"{r['fichero']}:{r['ini']}": r for r in riesgo}
    reg2r, conf = _cf.analizar(riesgo)
    en_conf = [f"{riesgo[i]['fichero']}:{riesgo[i]['ini']}" for i in conf]

    cl2 = callers_por_fichero(solo=list(_cf.contract.BLOQUES))
    chk("CONTROL: el call graph cubre los 6 ficheros de la ruta",
        all(f in cl2 for f in _cf.contract.BLOQUES), sorted(_cf.contract.BLOQUES))
    chk("CONTROL: el call graph NO esta vacio (acotado a la ruta VI)",
        sum(1 for v in cl2.values() if v) > 3,
        sum(1 for v in cl2.values() if v))
    chk("CONTROL: solo se parsean los ficheros de la ruta, no los 100",
        len(cl2) == len(_cf.contract.BLOQUES), len(cl2))

    # --- el SEGUNDO ANILLO: el despachador generico (187) ---
    anillo = ficheros_del_resolutor()
    chk("ANILLO: es BLOQUES + los 3 despachadores genericos",
        anillo == sorted(set(list(_cf.contract.BLOQUES) + list(SEGUNDO_ANILLO)),
                         key=anillo.index), anillo)
    chk("ANILLO: los 3 existen de verdad (universo con control positivo)",
        all(os.path.isfile(os.path.join(_AMD, "amdgpu", f))
            for f in SEGUNDO_ANILLO), SEGUNDO_ANILLO)
    for _f in SEGUNDO_ANILLO:
        _t = _texto_cache(os.path.join(_AMD, "amdgpu", _f))
        chk(f"ANILLO: {_f} TIENE el bucle ip_blocks[].version->funcs->",
            "ip_blocks[" in _t and ".version->funcs->" in _t)
    chk("ENTRADA: amdgpu_device_init es un punto de entrada",
        "amdgpu_device_init" in PUNTOS_DE_ENTRADA)
    chk("NEGATIVO: una funcion que NO es punto de entrada no da PROCESO",
        "gfx_v8_0_set_clockgating_state" not in PUNTOS_DE_ENTRADA)
    chk("ENTRADA: la IRQ NO es un punto de entrada de proceso",
        not any(es_asincrona(x) for x in PUNTOS_DE_ENTRADA),
        [x for x in PUNTOS_DE_ENTRADA if es_asincrona(x)])
    cl3 = callers_por_fichero(solo=anillo)
    # Las 3 que quedan no son "no encontradas": los `->gart_enable(` del arbol
    # estan en 6 ficheros y NINGUNO es de la ruta VI.  Es una afirmacion sobre
    # el universo, asi que necesita su control positivo: el mismo miembro SI se
    # encuentra en su generacion.  (189)
    _cons = []
    for _f in _ficheros_cache(_AMD):
        try:
            _t = _texto_cache(os.path.join(_AMD, "amdgpu", _f))
        except OSError:
            continue
        if re.search(r"->\s*gart_enable\s*\(", _t):
            _cons.append(_f)
    chk("MIEMBRO: ->gart_enable( SI existe en el arbol (universo no vacio)",
        len(_cons) >= 4, sorted(_cons))
    chk("MIEMBRO: y NINGUNO de sus consumidores es de la ruta VI",
        not (set(_cons) & set(_cf.contract.BLOQUES)),
        sorted(set(_cons) & set(_cf.contract.BLOQUES)))
    chk("ANILLO: el grafo ampliado parsea los 3 ficheros nuevos",
        all(cl3.get(f) for f in SEGUNDO_ANILLO),
        [f for f in SEGUNDO_ANILLO if not cl3.get(f)])

    irq_key = "gmc_v8_0.c:1385"
    # `en_conf` son claves "fichero:LINEA", pero `raices` espera el NOMBRE de la
    # funcion.  Pasarle la linea hacia que `rpartition(":")` devolviera "1385"
    # como nombre, que no esta en el call graph, y TODAS salian TOP.  No era
    # que el call graph no viera los llamantes: era que se le preguntaba por
    # el nombre equivocado.  (correccion 153)
    veredictos = {}
    for k in en_conf:
        f, _s, _l = k.partition(":")
        p = os.path.join(_AMD, "amdgpu", f)
        try:
            a, b, _m = funcspan.of_line(p, int(_l))
        except (OSError, ValueError):
            a = None
        if a is None:
            veredictos[k] = {"raiz": "NO_RESOLUBLE", "camino": [k]}
            continue
        cab = open(p, encoding="utf-8",
                   errors="replace").read().splitlines()[a - 1]
        mm = re.search(r"(\w+)\s*\(", cab)
        nom = mm.group(1) if mm else None
        if not nom:
            veredictos[k] = {"raiz": "SIN_NOMBRE", "camino": [k]}
            continue
        r, c = raices(cl3, f + ":" + nom)
        veredictos[k] = {"raiz": r, "camino": c, "nombre": nom}
    # El control positivo va DESPUES del bucle: antes de este arreglo estaba
    # aqui y leia `veredictos` sin haberlo inicializado.  Un assert que lee una
    # variable de mas arriba del sitio donde se calcula no comprueba el
    # calculo: comprueba el orden.  (correccion 154)
    if irq_key in idx:
        chk("CONTROL POSITIVO: la IRQ resuelve a un NOMBRE, no a una linea",
            veredictos.get(irq_key, {}).get("nombre")
            == "gmc_v8_0_vm_fault_interrupt_state",
            veredictos.get(irq_key))
        chk("CONTROL POSITIVO: la IRQ NO se clasifica como TOP (raiz sininfo)",
            veredictos.get(irq_key, {}).get("raiz") != "TOP",
            veredictos.get(irq_key))

    asinc = [k for k, v in veredictos.items() if v["raiz"] == "IRQ"]
    nores = [k for k, v in veredictos.items()
             if v["raiz"] in ("NO_RESOLUBLE", "SIN_NOMBRE")]
    ops = [k for k, v in veredictos.items() if v["raiz"] == "VIA_OPS"]
    proc = [k for k, v in veredictos.items() if v["raiz"] == "PROCESO"]
    _top = [k for k, v in veredictos.items() if v["raiz"] == "TOP"]
    _nores = [k for k, v in veredictos.items()
              if v["raiz"] in ("NO_RESOLUBLE", "SIN_NOMBRE")]
    top, nores = _top, _nores
    top = [k for k, v in veredictos.items() if v["raiz"] == "TOP"]

    chk("REGRESION: se analizan las 13 en conflicto",
        len(veredictos) == 13, len(veredictos))
    # El aserto fijaba "3 TOP" y el real es 0.  Ese 3 era CONSECUENCIA del
    # bug 153, no un hecho del driver: con la clave equivocada, 13 salian
    # TOP y 3 de ellas "no contaban" por un criterio arbitrario.  Corregido el
    # bug, el dato es 0: toda funcion en conflicto tiene un camino hasta una
    # raiz, ya sea directa o por ops table.  (correccion 157)
    # El reparto se cuenta POR ESTADO, no con una tupla de 5 posiciones: al
    # aparecer PROCESO por punto de entrada (189) y MIEMBRO_OTRA_GENERACION, la
    # tupla fijamented break se daba cuenta tarde y con un numero que no
    # significaba nada.  La asercion real es "cada una cae en un estado
    # conocido", que es lo que se comprueba.  (190)
    ESTADOS = {"IRQ", "PROCESO", "VIA_OPS", "MIEMBRO_OTRA_GENERACION",
               "NO_RESOLUBLE", "CICLO", "SIN_NOMBRE"}
    chk("REGRESION: las 13 caen en un estado CONOCIDO",
        all(v["raiz"] in ESTADOS for v in veredictos.values()),
        sorted({v["raiz"] for v in veredictos.values()} - ESTADOS))
    chk("REGRESION: las 13 se clasifican, ninguna sin veredicto",
        len(veredictos) == len(conf),
        (len(veredictos), len(conf)))
    chk("REGRESION: la IRQ resuelve a una raiz asincrona REAL",
        len(asinc) == 1, asinc)
    chk("REGRESION: 0 raices TOP (toda funcion tiene camino a una raiz)",
        len(top) == 0, (len(top), top))
    chk("REGRESION: las no resolubles NO se cuentan como proceso",
        all(veredictos[k]["raiz"] != "PROCESO" for k in nores), nores)
    # La IRQ debe quedar en un veredicto NO favorable.  Antes se exigia
    # "no es PROCESO" y "es IRQ o VIA_OPS": con la propagacion de los hijos
    # (correccion 159) el veredicto puede ser TOP si el camino se agota.  Lo
    # que NO puede ser es PROCESO: significaria que se ha declarado segura
    # una funcion de la que no se conoce el contexto.
    chk("REGRESION: la IRQ NO se clasifica como PROCESO",
        veredictos.get(irq_key, {}).get("raiz") != "PROCESO",
        veredictos.get(irq_key))
    chk("REGRESION: amdgpu_device_init resuelve a PROCESO, no a TOP",
        raices(cl3, "amdgpu_device.c:amdgpu_device_init")[0] == "PROCESO",
        raices(cl3, "amdgpu_device.c:amdgpu_device_init")[0])
    chk("REGRESION: la IRQ alcanza amdgpu_irq_disable_all por el miembro .set",
        veredictos.get(irq_key, {}).get("raiz") == "IRQ"
        and any("amdgpu_irq_disable_all" in c
                for c in veredictos.get(irq_key, {}).get("camino", [])),
        veredictos.get(irq_key))

    print(f"  {ok} pasaron, {fail} fallaron")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    if "--out" in sys.argv:
        import conflicto as _cf
        riesgo = _cf.riesgo_por_funcion()
        reg2r, conf = _cf.analizar(riesgo)
        cl = callers_por_fichero(solo=ficheros_del_resolutor())
        filas = []
        for i in sorted(conf):
            k = f"{riesgo[i]['fichero']}:{riesgo[i]['ini']}"
            # Misma resolucion de nombre que el self-test: `raices` espera el
            # NOMBRE, no la linea.  Pasarle la linea daba TOP a las 13, y el
            # `--out` habria publicado justo el dato erroneo.  (correccion 158)
            f = riesgo[i]["fichero"]
            p = os.path.join(_AMD, "amdgpu", f)
            a, b, _m = funcspan.of_line(p, riesgo[i]["ini"])
            cab = open(p, encoding="utf-8",
                       errors="replace").read().splitlines()[a - 1] if a else ""
            mm = re.search(r"(\w+)\s*\(", cab)
            nom = mm.group(1) if mm else None
            if nom:
                r, c = raices(cl, f + ":" + nom)
            else:
                r, c = "SIN_NOMBRE", [k]
            filas.append({"clave": k, "nombre": nom,
                          "cabecera": riesgo[i]["cabecera"][:56],
                          "bloque": riesgo[i]["bloque"],
                          "raiz": r, "camino": " <- ".join(c)})
        json.dump({"filas": filas}, open(os.path.join(RX550_ROOT, "06-INGENIERIA-INVERSA", "agents", "alcance.json"),
                                         "w"), indent=2, ensure_ascii=False)
        print(f"  funciones en conflicto analizadas: {len(filas)}")
        cnt = collections.Counter(f["raiz"] for f in filas)
        print(f"  reparto: {dict(cnt)}")
    else:
        print("uso: alcance.py --self-test | --out")
