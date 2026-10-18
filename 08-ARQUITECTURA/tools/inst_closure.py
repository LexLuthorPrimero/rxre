#!/usr/bin/env python3
# CONTRACT: name=inst_closure
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
"""
QUE PARTE DE display/ SE INSTANCIA EN ESTA GPU, POR ALCANZABILIDAD Y NO
POR COMPILACION.

Por que esto no es "que ficheros hay":

El arbol display/ tiene 510 .c y 443.839 lineas para chips que van de Polaris12
a Arcturus. Todas se COMPILAN, porque el Makefile las mete todas, y por eso
"esta compilado" no dice nada sobre si algo de ahi se ejecuta en esta placa.
La pregunta util para un driver propio es distinta y mas estrecha:

  de esas 443.839 lineas, cuantas se INSTANCIAN en Polaris12?

Y tiene respuesta estatica, porque el driver es una cascada de punteros a
funcion y el unico punto donde se decide el ASIC es el constructor de
recursos. Para Polaris12 es dc/resource/dce112/, que a su vez engancha los
constructores dce110_ de bloque (159). A partir de ahi el grafo de llamadas
es determinista y se recorre entero.

Lo que sale es lo que un driver propio tiene que reimplementar. Lo que queda
fuera es codigo de otras veinte generaciones que no hace falta ni leer.

LIMITACION 1 -- el recorrido es por NOMBRE, no por tipo. Si dos .c definen el
mismo nombre estatico se resuelve el primero en orden alfabetico. Se declara;
no se oculta. La herramienta cuenta e imprime las colisiones que encuentra.

LIMITACION 2 -- la asignacion a tabla se sigue como arista. Un dispatch
x->funcs->op = mi_impl no es una llamada, asi que sin ese patron el recorrido
perderia los 75 manejadores de dce110_hwseq (173), que es justamente el
objetivo. El patron es ->(nombre) = (nombre) y su limitacion es que no
distingue a que tabla se asigna. Aqui no hace falta: lo que se busca es el
conjunto de simbolos alcanzables, no el orden de invocacion.

LIMITACION 3 -- el corpus es display/ entero. Una llamada que salga hacia
amdgpu/ no se sigue, y por eso las semillas genericas se declaran a mano en
GENERIC_ROOTS en vez de deducirse. Lo que se sale del arbol queda MARCADO como
fuera, nunca se cuenta como alcanzable.

LIMITACION 4 -- esto es alcanzabilidad ESTATICA por constructor. No dice que
se ejecute en una sesion concreta: un modo concreto ejecuta un subconjunto
(175). Lo que responde es "que codigo puede llegar a correr en esta placa",
que es la cota superior y la unica obtenible sin NIVEL 4.
"""
import re
import sys
import glob
import os
import argparse
from collections import defaultdict, deque

_REL = "RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/display"


def _raiz():
    """raiz del proyecto: primero desde el cwd, luego desde la ubicacion de la
    propia herramienta. BASE tiene que ser ABSOLUTA porque subtree() hace
    relpath() y lineas_alcanzables() le pasa rutas relativas a BASE; con BASE
    relativa y rutas absolutas mezcladas, relpath devuelve ../../.. y
    todo el reparto por subarbol sale vacio."""
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for base in (os.getcwd(), raiz):
        cand = os.path.join(base, _REL)
        if os.path.isdir(cand):
            return cand
    return os.path.abspath(_REL)


BASE = _raiz()


def poblacion_asics(base):
    """(lista de ASIC del corpus, motivo por el que no se pudo calcular).

    Los ASIC de DML son los directorios de `dc/resource/`, y son la poblacion
    REAL: no un catalogo escrito a mano ni un fichero que se pueda mover. Se
    calcula del mismo BASE que la herramienta ya recorre.

    El segundo elemento del return es la parte importante. Devuelve un texto si
    NO se ha podido calcular la poblacion, y en ese caso el llamante tiene que
    declarar que no comprueba el nombre y SEGUIR. Devolver una lista vacia como
    si fuera una poblacion vacia seria el error del primer intento del
    hallazgo 1055: con el enum vacio, todos los nombres salian "desconocidos" y
    la herramienta rechazaba hasta el valor correcto.
    """
    d = os.path.join(base, "dc", "resource")
    if not os.path.isdir(d):
        return [], "no existe %s" % d
    asics = sorted(x for x in os.listdir(d)
                   if os.path.isdir(os.path.join(d, x))
                   and not x.startswith("."))
    if not asics:
        return [], "%s existe pero no tiene subdirectorios" % d
    return asics, None

# SIN semillas por ASIC. La primera version sembraba ademas
# dc/resource/dce112/, y eso era un error de diseño: medir el conjunto de lo
# que se alcanza desde el constructor por ASIC es medir SOLO el camino de
# arranque, no el de modo de pantalla, y por eso salia un 2,1% en lugar del
# 28,7%. El constructor de ASIC se alcanza desde dc_create como cualquier otro
# nodo, asi que sembrarlo no anade nada y si limita.
ASIC_CONSTRUCTORS = []

# Semillas genericas. Sin ellas el recorrido desde el constructor no llega al
# camino real, porque el constructor devuelve una tabla que consume la capa de
# arriba. Las que no existan se imprimen como NO resueltas, nunca se inventan.
# SEMILLAS. dc_create es la unica raiz real, y su justificacion esta en el
# corpus: amdgpu_dm/amdgpu_dm.c:2038 hace
#
#     adev->dm.dc = dc_create(&init_data);
#
# y dc_create esta definida en dc/core/dc.c:1508. Todo lo demas de DML entra
# por ahi.
#
# La primera version de esta lista tenia 28 nombres inventados -- dc_create_
# resource, dc_hw_sequencer_init, dc_link_srv_init, dc_sspl_init, ... -- y las
# 28 NO existian. La herramienta lo decia ("semillas NO resueltas: 28") y
# seguia imprimiendo un reparto, que es la forma mas peligrosa de estar
# equivocado: un numero con la advertencia al lado. Los constructores de ASIC
# NO son semillas: dc/resource/dce112/ se alcanza desde dc_create, y sembrarlo
# ademas mide solo el camino de arranque, no el de modo de pantalla.
GENERIC_ROOTS = [
    "dc_create",
]

FUNC_DEF = re.compile(r"^(static\s+)?[\w \*]*?\**(\w+)\s*\(")
CALL = re.compile(r"\b(\w+)\s*\(", re.S)
ASSIGN = re.compile(r"->\s*([\w\.]+)\s*=\s*&?\s*(\w+)")
COMENTARIO = re.compile(r"/\*.*?\*/", re.S)

# DOS DEFECTOS EN EL PATRON DE ASIGNACION, y los dos costaban un bloque entero
# de codigo. La linea real es
#
#     pool->base.funcs = &dce112_res_pool_funcs;
#
# y un patron "->(\\w+)\\s*=\\s*(\\w+)" no casa por dos razones a la vez:
# el nombre del campo tiene DOS niveles, "base.funcs", y "(\\w+)" no cruza el
# punto; y el valor se asigna POR REFERENCIA, con ampersand delante. Los dos
# fallos estan en la misma linea de codigo y por eso producian el mismo
# sintoma y el mismo sintomo era invisible: la tabla entera se caia del grafo.
#
# El vector T23 del selftest usa la linea REAL del corpus, y por eso cazó los
# dos de golpe: un fixture inventado con "x->funcs = tabla" habria pasado con
# uno de los dos arreglado. Regla: un caso de prueba se copia del fichero, no
# del esquema que uno cree que tiene.
# dc/resource/dce112/dce112_resource.c:1243 escribe
#
# Consecuencia medida: dce112_res_pool_funcs, sus 8 entradas y
# dce112_validate_bandwidth no eran alcanzables, y con ellos toda la
# validacion de ancho de banda de esta placa -- las 964 lineas de
# dce112_validate_bandwidth (abs 893..964). El sintoma era discreto: bw_calcs
# no aparecia en el cierre. El defecto no estaba en el grafo ni en el mapa,
# estaba en un caracter de un patron.
#
# TERCER TIPO DE ARISTA, y el que faltaba. Las tablas de despacho de DML no se
# rellenan con "dc->hwss = dce110_funcs" y ya esta: los 75 manejadores de
# dce110_hwseq (173) viven dentro de un INICIALIZADOR DE STRUCT DESIGNADO,
#
#     static const struct dc_hw_sequencer_funcs dce110_private_funcs = {
#         .OP_NOP = dce110_OP_NOP,
#         ...
#     };
#
# y una tabla no es una funcion, asi que no esta en el indice y la arista se
# corta ahi. Con las dos formas anteriores el recorrido llegaba a 231 lineas de
# dc/hwss, que es el 0,8% de un directorio que es el codigo de ESTA GPU. Sin
# esto el punto ciego se come justo lo que se quiere medir.
# Se empareja nombre de tabla con su inicializador y se sacan los .campo = fn.
TABLA = re.compile(
    r"^\s*(?:static\s+)?(?:const\s+)?struct\s+\w+[ \t\*]*\**"
    r"(?P<tabla>\w+)\s*=\s*\{", re.M)
DEFINE_MACRO = re.compile(r"^DEFINE_\w+$")

KEYWORDS = {
    "if", "for", "while", "switch", "return", "sizeof", "case", "do", "else",
    "defined", "typedef", "struct", "union", "enum", "static", "inline",
    "const", "void", "unsigned", "signed", "char", "int", "long", "short",
    "float", "double", "goto", "break", "continue", "extern", "register",
    "volatile", "auto", "asm", "__asm__",
}


def sin_comentarios(lineas):
    """Una linea de salida por cada linea de entrada; las de comentario, vacias.

    Tres casos: bloques /* ... */ sustituidos por sus saltos de linea, para no
    desplazar los numeros; lineas que empiezan por //; lineas que empiezan por
    *, que son continuaciones de bloque.

    La primera version tenia el tercer caso invertido, y vaciaba si NO
    empezaba por asterisco. El sintoma eran 1.175 colisiones de nombre con
    "files" y "3x4", que son palabras de la licencia y de un comentario de
    matriz de color.
    """
    txt = "\n".join(lineas)
    txt = COMENTARIO.sub(lambda m: "\n" * m.group(0).count("\n"), txt)
    out = []
    for l in txt.split("\n"):
        t = l.lstrip()
        out.append("" if (t.startswith("//") or t.startswith("*")) else l)
    return out


# ---------------------------------------------------------------------------
# PODA POR GUARDAS DE IDENTIDAD DE CHIP
#
# De 1.112 switch en display/, 23 tienen etiquetas de identidad de chip. Esos
# 23 son el coste ENTERO de bajar la cota, y se enumeran solos con
# --censo_guardas. El recorrido sin podar sigue las dos ramas de cada uno, y por
# eso dc/dce60/ sale alcanzable en una placa que no puede ejecutar DCE 6.0.
#
# VALOR_POR_PLANTA: variable -> conjunto de valores posibles en ESTA placa.
# Cada valor tiene su cita, y la cadena entera es:
#
#   0x699F  -- amdgpu/amdgpu_drv.c:2041   --> CHIP_POLARIS12
#   CHIP_POLARIS12 -- amdgpu/amdgpu_device.c:1980,1987 --> AMDGPU_FAMILY_VI
#        (rama no-APU; esta placa es una GPU discreta, lspci: "Lexa PRO")
#   AMDGPU_FAMILY_VI -- display/amdgpu_dm/amdgpu_dm.c:1910 --> asic_id.chip_family
#   FAMILY_VI -- display/dc/core/dc_resource.c:170,178,179 --> DCE_VERSION_11_2
#
# El ultimo eslabon NO esta supuesto: esta escrito. Y el case que sobrevive es
# dc/core/dc_resource.c:308-309, DCE_VERSION_11_2 y DCE_VERSION_11_22, que
# llaman a dce112_create_resource_pool.
VALOR_POR_PLANTA = {
    # --- VERIFICABLES. Cada valor con su eslabon (189):
    #     amdgpu/vi.c:1587  adev->external_rev_id = adev->rev_id + 0x64
    #     dal_asic_id.h:116 #define VI_POLARIS12_V_A0 100
    #     dc_resource.c:178-179  ASIC_REV_IS_POLARIS12_V -> DCE_VERSION_11_2
    #     y el log imprime "POLARIS12".
    "dc_version": {"DCE_VERSION_11_2"},
    "version": {"DCE_VERSION_11_2"},
    "ctx->dce_version": {"DCE_VERSION_11_2"},
    "in_dc->ctx->dce_version": {"DCE_VERSION_11_2"},
    "dce": {"DCE_VERSION_11_2"},
    "adev->asic_type": {"CHIP_POLARIS12"},

    # --- CORREGIDO EN 189: la clave es la etiqueta QUE USA EL SWITCH, no el
    #     simbolo que escribe el llamante. dc_resource.c:141 etiqueta
    #     "case FAMILY_VI:", y FAMILY_VI es 130 en dal_asic_id.h:308.
    #     Antes ponia AMDGPU_FAMILY_VI, que se usa dos veces en el corpus y NO
    #     esta declarado en ninguna cabecera: por eso ninguna de las seis
    #     guardas sobre chip_family casaba y todas se quedaban sin podar.
    "asic_id.chip_family": {"FAMILY_VI"},
    "clk_mgr_base->ctx->asic_id.chip_family": {"FAMILY_VI"},
    "link->ctx->asic_id.chip_family": {"FAMILY_VI"},
    "dc->ctx->asic_id.chip_family": {"FAMILY_VI"},

    # --- SIN VALOR DECLARADO. Conjunto vacio a proposito: la regla
    #     conservadora de 184 convierte "ninguna etiqueta coincide" en "no
    #     podar" y en "reportar contradiccion", que es lo correcto cuando el
    #     valor no se puede demostrar. AMDGPU_FAMILY_VI sigue sin declararse.
    "adev->family": set(),
    # dcn_version solo tiene etiquetas DCN_VERSION_*, que no existen en una
    # placa DCE. Vacio por la misma razon.
    "dcn_version": set(),
}

SIN_COINCIDENCIA = []

# SEGUNDO TIPO DE GUARDIA: un "if" cuya condicion incluye una bandera de
# depuracion que esta placa NO tiene puesta.
#
# dc/dml2_0/dml2_wrapper.c:96
#     if ((in_dc->debug.using_dml21) && (in_dc->ctx->dce_version >= DCN_VERSION_4_01)) {
#             return dml21_create(in_dc, dml2, config);
#     }
#
# Es un "if", no un "switch", asi que el censo de 184 no lo ve, y las 265
# funciones de dc/dml2_0/dml21/ se colaban. Y no se puede deducir de la version:
# la condicion es la bandera Y la version.
#
# Y el valor de la bandera si es demostrable: amdgpu_dm/amdgpu_dm.c:2075 es la
# UNICA aparicion de DC_ENABLE_DML2 en todo display/, y pone using_dml2 y
# using_dml21 a true DENTRO de ese if de mascara de depuracion. Con mascara a
# cero, las dos son false.
BANDERAS_FALSAS = {
    "using_dml2", "using_dml21", "disable_dsc", "disable_stutter",
    "disable_clock_gate", "force_subvp_mclk_switch", "visual_confirm",
}

IDENT = re.compile(r"^(DCE_VERSION_|DCN_VERSION_|CHIP_|AMDGPU_FAMILY_|FAMILY_|REV_)")


def censo_guardas(lista):
    """(fichero, variable, linea_switch, [(etiqueta, linea_absoluta)]).

    El cierre del switch se busca por PROFUNDIDAD DE LLAVES, no por "la
    proxima linea que sea una }". La primera version reiniciaba con cualquier
    llave, y dentro de un switch hay llaves anidadas -- un if dentro de un case
    las tiene -- de modo que el censo se paraba a mitad y se comia el switch
    siguiente. Sintoma medido: resource_parse_asic_id tiene 8 etiquetas de
    chip y el censo contaba 5; y el switch de dc_create_resource_pool contaba
    32 casos cuando tiene 24, que hacia que la poda borrase la rama correcta
    y dc/resource quedase en 0,0%.
    """
    out = []
    for p in lista:
        rel = os.path.relpath(p, BASE)
        lineas = sin_comentarios(open(p, errors="replace").read().split("\n"))
        cur = None
        prof = 0
        pend = []
        for i, l in enumerate(lineas):
            s = l.strip()
            m = re.match(r"switch\s*\(\s*([\w\.\->\[\]]+)\s*\)", s)
            if m and cur is None:
                cur = (m.group(1), i)
                pend = []
                prof = s.count("{") - s.count("}")
                continue
            if cur is None:
                continue
            c = re.match(r"case\s+(\w+)\s*:", s)
            if c:
                pend.append((c.group(1), i))
            prof += s.count("{") - s.count("}")
            if prof <= 0:
                if pend and any(IDENT.match(x[0]) for x in pend):
                    out.append((rel, cur[0], cur[1], pend))
                cur = None
                pend = []
                prof = 0
    return out


def _podar_banderas(lineas, base):
    """Vacia el cuerpo de un 'if (x->debug.using_dml21)' y de lo que sigue."""
    out = list(lineas)
    for i, l in enumerate(lineas):
        s = l.strip()
        if not s.startswith("if"):
            continue
        bandera = next((b for b in BANDERAS_FALSAS if b in s), None)
        if bandera is None:
            continue
        d = 0
        visto = False
        for k in range(i, len(out)):
            d += out[k].count("{") - out[k].count("}")
            if "{" in out[k]:
                visto = True
            if d == 0 and visto:
                for m in range(i, k + 1):
                    out[m] = ""
                break
    return out


def podar(cuerpo, guardas, base=0):
    """Quita del cuerpo las ramas de switch que esta placa no puede tomar."""
    lineas = list(cuerpo)
    lineas = _podar_banderas(lineas, base)
    for rel, var, li, pend in guardas:
        valores = VALOR_POR_PLANTA.get(var)
        if valores is None:
            continue
        # COORDENADAS. li es la linea ABSOLUTA en el fichero, y lineas es un
        # recorte del cuerpo de UNA funcion. Sin restar la linea base de la
        # funcion, la guarda se aplica sobre la linea equivocada y la poda no
        # hace nada: se midio y quitaba 1 funcion de 3.077 mientras
        # dc/dce60 seguia al 50%. Es el septimo bug de esta herramienta y es
        # el mismo tipo que el del indice de caracter: coordenadas mezcladas.
        cur_li = li
        li = li - base
        if not (0 <= li < len(lineas)):
            continue
        if "switch" not in lineas[li] or var not in lineas[li]:
            continue
        # rango de cada case: desde su 'case' hasta el siguiente 'case' o el
        # cierre del switch, deducido por la llave final
        d = 0
        cierre = None
        for k in range(li, len(lineas)):
            d += lineas[k].count("{") - lineas[k].count("}")
            if d == 0 and k > li:
                cierre = k
                break
        if cierre is None:
            continue
        # Las lineas de cada case TAMBIEN son absolutas al fichero. Traducir
        # solo la linea del switch y no estas es lo que hacia que la poda no
        # modificara NI UNA LINEA.
        #
        # Y HAY QUE AGRUPAR LAS TIRADAS DE ETIQUETAS. En C,
        #
        #     case DCE_VERSION_11_2:
        #     case DCE_VERSION_11_22:
        #             res_pool = dce112_create_resource_pool(...);
        #
        # las dos etiquetas comparten UN cuerpo. Podiendo etiqueta por etiqueta,
        # DCE_VERSION_11_22 no estaba en el conjunto de esta placa y su rango
        # --desde su 'case' hasta la etiqueta siguiente-- se llevaba el cuerpo
        # entero, de modo que dce112_create_resource_pool desaparecia y
        # dc/resource quedaba en 0,0%. Una etiqueta que cae bien no protege
        # el cuerpo que comparte con otra que cae mal. La regla de C es que
        # el cuerpo se ejecuta si CUALQUIER etiqueta de la tirada coincide.
        tiradas = []
        for etiqueta, ini_abs in pend:
            if tiradas and ini_abs - base <= tiradas[-1][1] + 1:
                tiradas[-1][0].add(etiqueta)
                tiradas[-1][1] = max(tiradas[-1][1], ini_abs - base)
            else:
                tiradas.append([{etiqueta}, ini_abs - base, ini_abs - base])
        # SEMANTICA DE C, Y CORRIGE LA REGLA DE 184.
        #
        # Si NINGUNA etiqueta de un switch coincide con el valor declarado, C
        # cae a "default:" y a NINGUN otro brazo. La regla conservadora de 184
        # hacia justo lo contrario: no podar ninguna, y por eso arrastraba los
        # 14.467 codigos de dc/dml2_0 que 185 demostro que son de DCN.
        #
        # El sintoma era "dc/dml2_0 sale alcanzable en una placa DCE", y la
        # causa precisa son los dos switch que elijeron no podar:
        # dml2_wrapper.c:61 y dml21_translation_helper.c:44, los dos con
        # etiquetas DCN_VERSION_* y ninguno con DCE_VERSION.
        #
        # No es una convencion, es la semantica del lenguaje: se poda todo
        # brazo explicito cuya etiqueta no coincide, SIEMPRE, y se conserva
        # solo "default:". Lo que no coincide ya no es una contradiccion del
        # mapa: es la respuesta.
        if not (set(x[0] for x in pend) & valores):
            SIN_COINCIDENCIA.append((rel, var, cur_li + 1,
                                    sorted(set(x[0] for x in pend))[:6]))

        tiradas = []
        for etiqueta, ini_abs in pend:
            if tiradas and ini_abs - base <= tiradas[-1][1] + 1:
                tiradas[-1][0].add(etiqueta)
                tiradas[-1][1] = max(tiradas[-1][1], ini_abs - base)
            else:
                tiradas.append([{etiqueta}, ini_abs - base, ini_abs - base])
        for j, (etiquetas, ini, fin_abs) in enumerate(tiradas):
            fin = (tiradas[j + 1][1] - 1) if j + 1 < len(tiradas) else cierre
            # "default" sobrevive SIEMPRE, y solo si el switch tiene el brazo.
            if (etiquetas & valores) or ("default" in etiquetas and
                                         not (etiquetas - {"default"})):
                continue
            for k in range(max(0, ini), min(fin + 1, len(lineas))):
                lineas[k] = ""
    return lineas


def subtree(relpath, base=None):
    """Primer nivel bajo dc/, o el propio dc/ cuando no hay subnivel.

    El argumento es un FICHERO, asi que hay que quitarle el nombre antes de
    contar niveles: dc/dc.c tiene dos componentes y dc/ tiene uno, y los dos
    son el subarbol "dc". La primera version contaba sobre la ruta del fichero
    y devolvia "dc/dc.c", un subarbol que no existe. Lo detecto el vector T6.
    """
    rel = os.path.relpath(os.path.abspath(relpath), base or BASE)
    if rel.startswith(".."):
        raise ValueError(f"subtree(): {relpath!r} esta fuera de BASE")
    partes = rel.split(os.sep)
    directorios = partes[:-1]
    if not directorios:
        return partes[0]
    if directorios[0] != "dc":
        return directorios[0]
    if len(directorios) == 1:
        return "dc"
    return "dc/" + directorios[1]


def index_functions(verbose=False, ficheros=None, base=None):
    """nombre -> (subarbol, fichero, ini, fin, cuerpo, es_macro).

    El cuerpo va dentro del indice a proposito. La primera version reabria el
    fichero por su nombre, y el selftest, que usa nombres sinteticos, se caia
    con FileNotFoundError. Un programa que no puede ejecutarse en su propio
    caso de prueba no esta probado.
    """
    idx = {}
    dup = []
    macros = []
    descuadres = []
    lista = ficheros if ficheros is not None else sorted(glob.glob(f"{BASE}/**/*.c", recursive=True))
    for p in lista:
        todas = open(p, errors="replace").read().split("\n")
        src = sin_comentarios(todas)
        st = subtree(p, base)
        rel = os.path.relpath(p, base or BASE)
        i = 0
        while i < len(src):
            l = src[i]
            m = FUNC_DEF.match(l) if not l.rstrip().endswith(";") else None
            if m:
                name = m.group(2)
                if name in KEYWORDS:
                    i += 1
                    continue
                if DEFINE_MACRO.match(name):
                    # Macro de tipo funcion: DEFINE_FREE(state_release, ...).
                    # No es una definicion de funcion: su cuerpo es la linea de
                    # la invocacion, con comas de mas y sin llaves. Indexada
                    # como funcion se tragaria lineas hasta la primera llave
                    # del fichero. Se indexa como nodo sin rango de lineas.
                    macros.append(name)
                    idx.setdefault(name, (st, rel, i, i, todas[i:i + 1], True))
                    i += 1
                    continue
                j = i
                while j < len(src) and "{" not in src[j]:
                    j += 1
                if j >= len(src):
                    i += 1
                    continue
                d = 0
                cerrado = False
                for k in range(j, len(src)):
                    d += src[k].count("{") - src[k].count("}")
                    if d == 0:
                        if name in idx:
                            dup.append((name, idx[name][1], rel))
                        else:
                            idx[name] = (st, rel, i, k, todas[i:k + 1], False)
                        i = k
                        cerrado = True
                        break
                if not cerrado:
                    # NO break. La primera version hacia break aqui, y una sola
                    # llave sin emparejar -- una "{" dentro de un literal de
                    # cadena, por ejemplo -- descuadraba el contador para el
                    # resto del FICHERO, que se dejaba de indexar entero. Por
                    # eso dce110_link_encoder_construct no aparecia: no es que
                    # no exista, es que estaba despues del punto de corte.
                    # Se registra el descuadre y se sigue desde la linea
                    # siguiente, que es lo unico honesto que se puede hacer sin
                    # un parser de C.
                    descuadres.append((name, rel, i + 1))
                    i += 1
            i += 1
    if verbose:
        print(f"  colisiones de nombre entre .c: {len(dup)}")
        print(f"  macros indexadas como nodo sin rango: {len(set(macros))}")
        print(f"  funciones con llaves descuadradas (fichero NO abandonado): {len(descuadres)}")
        for n, f, l in descuadres[:5]:
            print(f"      {n}  {f}:{l}")
    return idx, dup, descuadres


def index_tablas(lista):
    """nombre de tabla -> simbolos a los que apunta.

    Los inicializadores de struct designado son aristas de dispatch igual que
    una llamada, y sin esto el recorrido llega a la tabla y se detiene: una
    tabla no es una funcion, asi que no esta en el indice y de ahi no se sale.

    TODO EL RECORRIDO ES POR LINEAS, no por caracteres. La primera version
    emparejaba TABLA sobre el texto unido y luego indexesaba el texto con un
    indice de linea, de modo que src[j] era el caracter "{" y no una linea, y
    el cuerpo salia partido en caracteres sueltos. Con eso se indexaban 744
    tablas y CERO aristas, y el selftest lo detecto.
    """
    tablas = {}
    CAMPO = re.compile(r"\.\s*(\w+)\s*=\s*&?\s*(\w+)")
    for p in lista:
        lineas = sin_comentarios(open(p, errors="replace").read().split("\n"))
        # offset en caracteres de cada inicio de linea, para traducir el
        # indice del regex a indice de linea
        offs = []
        acc = 0
        for l in lineas:
            offs.append(acc)
            acc += len(l) + 1
        texto = "\n".join(lineas)

        def linea_de(pos):
            import bisect
            return bisect.bisect_right(offs, pos) - 1

        for m in TABLA.finditer(texto):
            nombre = m.group("tabla")
            ini = linea_de(m.start())
            d = 0
            cuerpo = []
            cerrado = False
            for k in range(ini, len(lineas)):
                d += lineas[k].count("{") - lineas[k].count("}")
                cuerpo.append(lineas[k])
                if d == 0 and k > ini:
                    cerrado = True
                    break
            tablas.setdefault(nombre, set()).update(
                c.group(2) for c in CAMPO.finditer("\n".join(cuerpo)))
    return tablas


def edges(cuerpo, tablas=None, guardas=None, base=0):
    """Aristas salientes de un cuerpo: llamadas y asignaciones a tabla."""
    limpio = sin_comentarios(cuerpo)
    if guardas:
        limpio = podar(limpio, guardas, base)
    txt = "\n".join(limpio)
    out = set()
    for m in CALL.finditer(txt):
        if m.group(1) not in KEYWORDS:
            out.add(m.group(1))
    for m in ASSIGN.finditer(txt):
        out.add(m.group(2))
        if tablas:
            out |= tablas.get(m.group(2), set())
    for m in CALL.finditer(txt):
        if tablas:
            out |= tablas.get(m.group(1), set())
    return out


def alcanzables(idx, semillas, tablas=None, guardas=None):
    vis = {}
    q = deque()
    fuera = set()
    for s in semillas:
        if s in idx:
            vis[s] = 0
            q.append(s)
        else:
            fuera.add(s)
    while q:
        n = q.popleft()
        for m in edges(idx[n][4], tablas, guardas, idx[n][2]):
            if m in idx and m not in vis:
                vis[m] = vis[n] + 1
                q.append(m)
    return vis, fuera


def lineas_totales():
    tot = defaultdict(int)
    for p in glob.glob(f"{BASE}/**/*.c", recursive=True):
        tot[subtree(p)] += open(p, errors="replace").read().count("\n")
    return tot


def lineas_alcanzables(idx, vis):
    """Suma de los intervalos [ini,fin] de las funciones alcanzables, sin solapes."""
    cub = defaultdict(list)
    for n in vis:
        v = idx[n]
        if v[5]:
            continue
        cub[v[1]].append((v[2], v[3]))
    alc = defaultdict(int)
    for f, iv in cub.items():
        st_f = subtree(os.path.join(BASE, f))   # v[1] es relativa a BASE
        iv.sort()
        ini = prev = None
        for a, b in iv:
            if ini is None:
                ini, prev = a, b
            elif a <= prev + 1:
                prev = max(prev, b)
            else:
                alc[st_f] += prev - ini + 1
                ini, prev = a, b
        if ini is not None:
            alc[st_f] += prev - ini + 1
    return alc


def selftest():
    """VECTORES CONOCIDOS, un control invertible, y los fallos ya Cometidos."""
    fallos = []
    n = 0

    def checar(cond, etiqueta):
        """Como el patron `if cond: fallos.append(...)` que ya usa este
        selftest, pero ademas CUENTA. Los 20 checks antiguos no se han tocado
        porque son de otra clase y reescribirlos todos seria un riesgo sin
        contrapartida: su numero se mide en runtime mas abajo, contando los
        sitios de comprobacion del fuente."""
        nonlocal n
        n += 1
        if not cond:
            fallos.append(etiqueta)

    # --- --asi, MEDIDO 2026-10-04 (nodo FILTROS-REPARO-2) ---
    #
    # Antes no habia ni un vector sobre --asi. El defecto era una ETIQUETA
    # MUERTA: el argumento no entraba en el calculo, y el titular nombraba un
    # ASIC sin comprobarlo. Un selftest que no lo probe puede seguir diciendo
    # "selftest: OK" mientras el titular sigue mintiendo.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        res = os.path.join(td, "dc", "resource")
        os.makedirs(os.path.join(res, "dce112"))
        os.makedirs(os.path.join(res, "dce110"))
        os.makedirs(os.path.join(res, "dcn20"))
        with open(os.path.join(res, "Makefile"), "w") as fh:
            fh.write("# no es un ASIC\n")
        asics, motivo = poblacion_asics(td)
        checar(asics == ["dce110", "dce112", "dcn20"],
               "T24 la poblacion de ASIC se calcula de dc/resource/")
        checar(motivo is None,
               "T25 con dc/resource presente no hay motivo de no comprobar")
        # El Makefile no es un ASIC: un fichero suelto no se cuela en la lista.
        checar("Makefile" not in asics,
               "T26 un fichero de dc/resource no es un ASIC")
        # Y el caso que NO es un filtro mal escrito: si no se puede calcular la
        # poblacion, se DECLARA y se sigue. Este es el vector que impide que
        # este arreglo repita el fallo del primer intento de 1055, que dejo
        # rc=2 hasta para el valor valido.
        vacio, motivo2 = poblacion_asics(os.path.join(td, "no-existe-esta-raiz"))
        checar(vacio == [] and motivo2,
               "T27 sin arbol no hay poblacion PERO SI motivo: no se rechaza todo")
        checar(not (motivo2 is None),
               "T28 la poblacion no disponible se distingue de la poblacion vacia")
    # Control positivo: el ASIC por defecto de esta GPU esta en el corpus real
    # SI el BASE de esta invocacion tiene dc/resource. Con BASE ausente el
    # vector se declara, no se da por bueno.
    asics_real, motivo_real = poblacion_asics(BASE)
    if motivo_real is None:
        checar(len(asics_real) > 0,
               "T29 la poblacion real de ASIC no esta vacia")
        checar("dce112" in asics_real,
               "T30 dce112, el ASIC por defecto, esta en la poblacion real")
    else:
        print(f"  selftest: T29/T30 NO APLICABLES: {motivo_real}")

    # 1. Transitividad minima. Los fixtures usan la MISMA forma que el indice
    #    real: la primera version tenia de 4 y el selftest no podia ejecutarse.
    # Las rutas de los fixtures tienen que estar DENTRO de BASE: subtree()
    # rechaza las de fuera, y es correcto que lo haga. La primera version de
    # estos fixtures usaba "f.c", que esta fuera, y el selftest se caia con
    # ValueError en vez de comprobar lo que queria comprobar.
    F1 = os.path.join(BASE, "dc/core/x.c")
    idx = {
        "a": ("dc/core", F1, 0, 3, ["void a(void)", "{", "  b();", "}"], False),
        "b": ("dc/core", F1, 4, 7, ["void b(void)", "{",
                                    "  /* z(); dentro de comentario */", "}"], False),
        "z": ("dc/core", F1, 8, 11, ["void z(void)", "{", "  ;", "}"], False),
    }
    vis, _ = alcanzables(idx, ["a"])
    if "b" not in vis:
        fallos.append("T1 la transitividad desde 'a' no llego a 'b'")
    if "z" in vis:
        fallos.append("T2 un simbolo solo comentado resulto alcanzable")

    # 2. CONTROL INVERTIDO. Sin este paso T1 pasaria aunque el recorrido no
    #    hiciese absolutely nada, porque "b in vis" seria falso igual.
    vis2, _ = alcanzables(idx, ["b"])
    if "a" in vis2:
        fallos.append("T3 el control invertido no fallo: ignora la semilla")

    # 3. Semilla inexistente: fuera, nunca alcanzable.
    vis3, fuera = alcanzables(idx, ["no_existe"])
    if "no_existe" in vis3:
        fallos.append("T4 una semilla inexistente se conto como alcanzable")
    if "no_existe" not in fuera:
        fallos.append("T5 una semilla inexistente no se marco como fuera")

    # 4. subtree sobre ficheros, incluidos los de primer nivel.
    for ruta, esp in [("dc/core/dc.c", "dc/core"), ("dc/dce/dce112/x.c", "dc/dce"),
                      ("amdgpu_dm/a.c", "amdgpu_dm"), ("dc/dc.c", "dc"),
                      ("dmub/src/a.c", "dmub")]:
        got = subtree(os.path.join(BASE, ruta))
        if got != esp:
            fallos.append(f"T6 subtree({ruta}) = {got}, esperaba {esp}")

    # 5. La arista de asignacion a tabla se sigue.
    F2 = os.path.join(BASE, "dc/dce/y.c")
    idx5 = {"c": ("dc/dce", F2, 0, 3, ["void c(void)", "{",
                                      "  x->funcs->op = impl;", "}"], False),
            "impl": ("dc/dce", F2, 4, 7, ["void impl(void)", "{", "  ;", "}"], False)}
    vis5, _ = alcanzables(idx5, ["c"])
    if "impl" not in vis5:
        fallos.append("T7 la arista de asignacion no se sigue")

    # 6. Un comentario NO crea una funcion. La linea 6 de todos los ficheros
    #    empieza por " * copy of this software...", y el patron crudo sacaba
    #    "files" de ahi. Sin este vector el indice puede tener basura y nadie
    #    se entera.
    limpio = sin_comentarios([" * The matrix needs to be a 3x4 (12 entry) matrix.",
                              " * files (the \"Software\")",
                              "int real(void)"])
    for i, l in enumerate(limpio):
        mm = FUNC_DEF.match(l)
        if mm and mm.group(2) in ("3x4", "files", "matrix", "Software", "entry"):
            fallos.append(f"T8 la linea de comentario {i + 1} produjo {mm.group(2)!r}")
    if not FUNC_DEF.match(limpio[2]) or FUNC_DEF.match(limpio[2]).group(2) != "real":
        fallos.append("T9 sin_comentarios borro la linea de codigo de verdad")

    # 7. Una macro DEFINE_* es un nodo sin rango de lineas.
    mm = FUNC_DEF.match("DEFINE_FREE(state_release, struct dc_state *, x)")
    if not mm or not DEFINE_MACRO.match(mm.group(2)):
        fallos.append("T10 la macro DEFINE_FREE no se reconoce como macro")

    # 8. El calculo de lineas alcanzables no puede solapar dos funciones.
    F3 = os.path.join(BASE, "dc/hwss/z.c")
    idx6 = {"p": ("dc/hwss", F3, 0, 9, ["x"] * 10, False),
            "q": ("dc/hwss", F3, 3, 5, ["y"] * 3, False)}
    alc = lineas_alcanzables(idx6, ["p", "q"])
    if alc.get("dc/hwss") != 10:
        fallos.append(f"T11 lineas solapadas: {alc.get('dc/hwss')}, esperaba 10")

    # 9. Una llave sin emparejar NO puede abandonar el resto del fichero. Este
    #    es el fallo mas caro de la herramienta: hacia break(), y por eso
    #    dce110_link_encoder_construct -- que existe y se llama desde
    #    dce112_resource.c -- no aparecia en el indice. Se comprueba con una
    #    linea que abre llave y no la cierra.
    #    El fichero de prueba va en /tmp, NUNCA dentro del corpus: la primera
    #    version lo escribia en dc/core/ y lo borraba al final, y eso es
    #    MUTATES_CORPUS=yes contra el contrato de la propia herramienta, y
    #    contra la regla de no anadir ficheros al corpus compartido. Con otro
    #    sesion leyendo el arbol a la vez, ese fichero existe.
    tmp = "/tmp/opencode/inst_closure_selftest.c"
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    with open(tmp, "w") as fh:
        fh.write('void antes(void)\n{\n\tantes_cuerpo();\n}\n'
                 'const char *s = "{";\n'
                 'void despues(void)\n{\n\tdespues_cuerpo();\n}\n')
    i2, _, _ = index_functions(ficheros=[tmp], base=os.path.dirname(tmp))
    os.remove(tmp)
    if "despues" not in i2:
        fallos.append("T12 una llave descuadrada abandono el resto del fichero")
    if "antes" not in i2:
        fallos.append("T13 se perdio la funcion que estaba ANTES del descuadre")

    # 10. La arista de tabla: un inicializador de struct designado es una
    #     arista de dispatch. Sin ella, dc->hwss = dce110_funcs llega a la
    #     tabla y se detiene, y con ella salen los 75 manejadores de 173.
    tmp2 = "/tmp/opencode/inst_closure_selftest2.c"
    os.makedirs(os.path.dirname(tmp2), exist_ok=True)
    with open(tmp2, "w") as fh:
        fh.write("static const struct t_funcs mis_funcs = {\n"
                 "\t.OP_NOP = op_nop,\n"
                 "\t.OP_X = op_x,\n"
                 "};\n"
                 "void construir(void)\n{\n\tdc->hwss = mis_funcs;\n}\n"
                 "void op_nop(void)\n{\n}\n"
                 "void op_x(void)\n{\n}\n")
    i3, _, _ = index_functions(ficheros=[tmp2], base=os.path.dirname(tmp2))
    tb = index_tablas([tmp2])
    os.remove(tmp2)
    if "mis_funcs" not in tb:
        fallos.append("T14 la tabla no se indexo")
    else:
        v3, _ = alcanzables(i3, ["construir"], tb)
        if "op_nop" not in v3 or "op_x" not in v3:
            fallos.append("T15 la arista de tabla no llega a los manejadores")

    # 11. La poda tiene que respetar que la linea de la guarda es ABSOLUTA al
    #     fichero y el cuerpo es un recorte. Sin la traduccion, podar() aplica
    #     la guarda sobre la linea equivocada y no hace nada, y eso se ve como
    #     "la poda no quito nada", que parece un resultado y es un bug.
    cuerpo = ["void f(void)", "{", "  switch (dc_version) {",
              "  case DCE_VERSION_6_0:", "      rama_60();", "      break;",
              "  case DCE_VERSION_11_2:", "      rama_112();", "      break;",
              "  }", "}"]
    g3 = [("x.c", "dc_version", 2, [("DCE_VERSION_6_0", 3),
                                    ("DCE_VERSION_11_2", 6)])]
    salida = podar(cuerpo, g3, base=0)
    if any("rama_60" in l for l in salida):
        fallos.append("T16 la poda no quito la rama de otro chip (base 0)")
    if not any("rama_112" in l for l in salida):
        fallos.append("T17 la poda se comio la rama de esta placa")
    # El mismo cuerpo, perotr bolcando que la funcion empieza en la linea
    # ABSOLUTA 10. Entonces la guarda esta en la absoluta 14 y su indice en el
    # recorte es 4. Si se pasa base=0 se aplica sobre la linea 14 del recorte,
    # que no existe, y la poda no hace nada.
    # El mismo cuerpo con cuatro lineas por delante, de modo que la funcion
    # empieza en la linea ABSOLUTA 10 y el switch queda en la 16. Las lineas
    # de los case se derivan de los indices del propio recorte mas base, que
    # es como las construye censo_guardas.
    cuerpo2 = ["void g(void)", "{", "  llamada();", "}"] + cuerpo
    g4 = [("x.c", "dc_version", 16, [("DCE_VERSION_6_0", 17),
                                     ("DCE_VERSION_11_2", 20)])]
    # T21: TIRADA DE ETIQUETAS. Las dos etiquetas comparten cuerpo; una sola
    # que coincida debe conservar el cuerpo entero. Con la poda etiqueta por
    # etiqueta, DCE_VERSION_11_22 --que no es de esta placa-- se lleva el
    # cuerpo de dce112_create_resource_pool y dc/resource queda en 0%.
    cuerpo3 = ["void h(void)", "{", "  switch (dc_version) {",
               "  case DCE_VERSION_11_2:", "  case DCE_VERSION_11_22:",
               "      rama_112();", "      break;",
               "  case DCE_VERSION_12_0:", "      rama_120();", "      break;",
               "  }", "}"]
    g5 = [("x.c", "dc_version", 2, [("DCE_VERSION_11_2", 3),
                                    ("DCE_VERSION_11_22", 4),
                                    ("DCE_VERSION_12_0", 7)])]
    salida5 = podar(cuerpo3, g5, base=0)
    if not any("rama_112" in l for l in salida5):
        fallos.append("T21 la poda se comio el cuerpo de una tirada que coincide")
    if any("rama_120" in l for l in salida5):
        fallos.append("T22 la poda no quito la rama de la otra tirada")
    salida2 = podar(cuerpo2, g4, base=10)
    if any("rama_60" in l for l in salida2):
        fallos.append("T18 con base=10 la poda no se translates")
    if not any("rama_112" in l for l in salida2):
        fallos.append("T19 con base=10 la poda se comio la rama correcta")
    salida3 = podar(cuerpo2, g4, base=0)
    if not any("rama_60" in l for l in salida3):
        fallos.append("T20 con base=0 la poda toco una linea que no le toca")

    # 23. Una tabla asignada POR REFERENCIA. dc112_resource.c:1243 escribe
    #     pool->base.funcs = &dce112_res_pool_funcs; y sin el "&" en el patron
    #     la tabla entera queda fuera del grafo. Es el bug que se llevo por
    #     delante las 964 lineas de dce112_validate_bandwidth.
    idx7 = {"c": ("dc/dce", os.path.join(BASE, "dc/dce/w.c"), 0, 3,
                  ["void c(void)", "{", "  pool->base.funcs = &mis_funcs;", "}"], False),
            "impl": ("dc/dce", os.path.join(BASE, "dc/dce/w.c"), 4, 7,
                     ["void impl(void)", "{", "  ;", "}"], False)}
    tb7 = {"mis_funcs": {"impl"}}
    vis7, _ = alcanzables(idx7, ["c"], tb7)
    if "impl" not in vis7:
        fallos.append("T23 una tabla asignada con & no se sigue")

    # El numero de vectores se mide, no se escribe a mano. Los checks antiguos
    # son del patron `if cond: fallos.append("T..")` y no incrementan `n`, asi
    # que se cuentan en runtime los sitios de comprobacion que hay en el fuente
    # de esta misma funcion. Un numero puesto a mano deja de ser cierto en
    # cuanto alguien anade un vector, que es justo cuando mas importa.
    import inspect as _inspect
    # Se quitan los comentarios ANTES de contar, por el mismo motivo que hace
    # el censo en su Apéndice A: sin quitarlos, este mismo comentario -- que
    # menciona el patron `fallos.append("T...")` -- se contaria como un vector
    # mas. MEDIDO: con el comentario dentro contaba 21 y sin el, 20.
    fuente = "\n".join(l for l in _inspect.getsource(selftest).splitlines()
                       if not l.strip().startswith("#"))
    heredados = len(re.findall(r'fallos\.append\("T', fuente))
    print(f"  vectores: {n + heredados} ({heredados} comprobaciones Tn heredadas"
          f" + {n} nuevas con contador)")
    print("  selftest:", "OK" if not fallos else "FALLA")
    for f in fallos:
        print("    -", f)
    return 0 if not fallos else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--asi", default="dce112")
    ap.add_argument("--funciones", action="store_true")
    ap.add_argument("--colisiones", action="store_true")
    ap.add_argument("--podar", action="store_true")
    ap.add_argument("--censo_guardas", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(selftest())

    print(f"  BASE = {BASE}")
    idx, dup, descuadres = index_functions(verbose=True)
    lista = sorted(glob.glob(f"{BASE}/**/*.c", recursive=True))
    tablas = index_tablas(lista)
    print(f"  tablas de despacho indexadas: {len(tablas)}")
    print(f"  aristas desde tablas: {sum(len(v) for v in tablas.values())}")
    print(f"  funciones indexadas: {len(idx)}")
    print(f"  ficheros con al menos un descuadre: {len({d[1] for d in descuadres})}")
    if a.colisiones and dup:
        for n, f1, f2 in dup[:15]:
            print(f"      {n}: {f1}  vs  {f2}")

    # --asi: MEDIDO 2026-10-04 (nodo FILTROS-REPARO-2, sobre el censo
    # 08-ARQUITECTURA/FILTROS-MAL-FORMADOS.md:704-756, veredicto ETIQUETA_MUERTA).
    #
    # Antes, `a.asi` aparecia en UNA linea de todo el fichero, y era dentro de
    # un print. El calculo de las semillas del ASIC itera ASIC_CONSTRUCTORS, que
    # esta vacio EN EL FUENTE por decision de diseño (comentario de :77-83:
    # sembrar el constructor de ASIC mide solo el camino de arranque, no el de
    # modo de pantalla, y por eso salia 2,1% en lugar de 28,7%).
    #
    # Consecuencia medida ANTES del arreglo, las tres con rc=0 y las tres
    # SALIDA IDENTICA salvo la etiqueta:
    #
    #   (sin --asi, default dce112)  ->  semillas del ASIC (dce112): 0 de []
    #   --asi dce999                 ->  semillas del ASIC (dce999): 0 de []
    #   --asi lista-que-no-existe    ->  semillas del ASIC (lista-que-no-existe): 0 de []
    #
    # El numero 0 es CORRECTO. Lo que no era cierto es la etiqueta: un titular
    # que nombra un ASIC que nadie ha comprobado. Por eso el arreglo NO cambia
    # la cuenta a 1 ni siembra nada: eso seria deshacer una decision de diseño
    # desde un arreglo de filtro, y cambiaria los porcentajes de la tabla.
    #
    # Lo que hace es COMPROBAR el nombre contra una poblacion real, y la
    # poblacion son los directorios de dc/resource/ del propio corpus que esta
    # herramienta ya recorre. MEDIDO: 24 ASIC distintos (dce100..dce120, dcn10..
    # dcn42), y dce112 esta entre ellos, que es el ASIC de esta GPU.
    #
    # Y el caso de "no he podido calcular la poblacion" NO se trata como "el
    # nombre es malo": se declara y se sigue. Es la lección del primer intento
    # del hallazgo 1055, que dejo rc=2 hasta para el valor valido porque
    # delego en un enum de un fichero que no existe en el arbol que la
    # herramienta recorre. Un arreglo que no distingue "el filtro estaba mal" de
    # "no hay datos" es el mismo defecto con el signo cambiado.
    asics, por_que_no = poblacion_asics(BASE)
    if por_que_no:
        print(f"  ASIC: no he podido comprobar --asi {a.asi!r}: {por_que_no}")
        print("  No se afirma nada sobre ese nombre. Las cifras de abajo no")
        print("  dependen de --asi en ningun caso.")
    elif a.asi not in asics:
        print(f"ERROR: --asi {a.asi} no es ningun ASIC de este corpus.")
        print(f"  ASIC que SI existen ({len(asics)}): {', '.join(asics)}")
        print()
        print("  No se ha medido nada. Antes esta herramienta imprimia")
        print("  'semillas del ASIC (%s): 0 de []' para cualquier nombre," % a.asi)
        print("  con rc=0: un titular que nombraba un ASIC sin comprobarlo.")
        return 2

    semillas = []
    for d in ASIC_CONSTRUCTORS:
        semillas += [n for n, v in idx.items() if v[1].startswith(d)]
    n_asic = len(semillas)
    semillas += GENERIC_ROOTS
    if por_que_no:
        print(f"  semillas del ASIC ({a.asi}): SIN COMPROBAR")
    else:
        print(f"  ASIC {a.asi}: existe en el corpus "
              f"({len(asics)} ASIC en dc/resource/).")
        print(f"  semillas del ASIC ({a.asi}): {n_asic}. "
              f"ASIC_CONSTRUCTORS esta VACIO por decision de diseño (:77-83),")
        print("  de modo que --asi no entra en el calculo de ninguna cifra de")
        print("  este informe. Es una etiqueta COMPROBADA, no una afirmacion.")
    print(f"  semillas genericas: {len(GENERIC_ROOTS)}")

    guardas = censo_guardas(lista)
    print(f"  guardas de identidad de chip: {len(guardas)}")
    if a.censo_guardas:
        for rel, var, li, pend in guardas:
            print(f"      {rel}:{li + 1}  switch({var})  {len(pend)} casos")
        return
    vis, fuera = alcanzables(idx, semillas, tablas, guardas if a.podar else None)
    if a.podar:
        print("  PODA APLICADA: solo se siguen las ramas que esta placa puede tomar")
        print(f"  switch sin ninguna etiqueta coincidente (solo default): {len(set(SIN_COINCIDENCIA))}")
        for rel, var, li, et in sorted(set(SIN_COINCIDENCIA))[:10]:
            print(f"      {rel}:{li}  switch({var})  etiquetas: {', '.join(et)}")
    faltantes = [s for s in GENERIC_ROOTS if s not in idx]
    print(f"  alcanzables: {len(vis)}")
    print(f"  semillas NO resueltas: {len(faltantes)}  {faltantes}")

    tot = lineas_totales()
    alc = lineas_alcanzables(idx, vis)
    tfot = defaultdict(int)
    for v in idx.values():
        tfot[v[0]] += 1
    nalc = defaultdict(int)
    for n in vis:
        nalc[idx[n][0]] += 1

    print()
    print("  %-20s %10s %10s %8s %10s %8s %8s" % (
        "subarbol", "funcs", "func_alc", "%funcs", "lineas", "lin_alc", "%lin"))
    T = sum(tot.values())
    TA = sum(alc.values())
    for st in sorted(tot, key=lambda s: -tot[s]):
        print("  %-20s %10d %10d %7.1f%% %10d %8d %7.1f%%" % (
            st, tfot[st], nalc[st], 100.0 * nalc[st] / max(tfot[st], 1),
            tot[st], alc[st], 100.0 * alc[st] / max(tot[st], 1)))
    print("  %-20s %10d %10d %7.1f%% %10d %8d %7.1f%%" % (
        "TOTAL", sum(tfot.values()), len(vis), 100.0 * len(vis) / max(sum(tfot.values()), 1),
        T, TA, 100.0 * TA / T))

    if a.funciones:
        print()
        print("  ALCANZABLES POR SUBARBOL")
        for st in sorted(nalc, key=lambda s: -nalc[s]):
            fs = sorted(n for n in vis if idx[n][0] == st)
            print("  %-20s %d" % (st, nalc[st]))
            if st in ("dc/core", "dc/link", "amdgpu_dm", "dc/dce", "dc/hwss",
                      "dc/dce110", "dc/clk_mgr"):
                for n in fs[:5]:
                    print("        %-46s %s:%d" % (n, idx[n][1], idx[n][2] + 1))


if __name__ == "__main__":
    # MEDIDO 2026-10-04: aqui estaba `main()` a secas, y se COMPROBO que el
    # `return 2` del arreglo de --asi no llegaba al shell: el mensaje de error
    # salia por pantalla y el proceso seguia con rc=0. Un return que no se
    # propaga al codigo de salida es un return decorativo, y es el mismo defecto
    # que repara este nodo -- un fallo que se anuncia y no se ve.
    # `sys.exit(main())` con main() devolviendo None da 0, que es lo que hacia
    # antes en el camino bueno.
    sys.exit(main())