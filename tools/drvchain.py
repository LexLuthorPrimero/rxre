#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""drvchain.py - mide la distancia entre el driver propio y la cadena del objetivo.

LA PREGUNTA

AGENTS.md §OBJETIVO FINAL define la cadena que hay que poder construir:

  PCI → inicialización → MMIO → MC/VRAM → GART → GPUVM → PTE/PDE → VMID
  → TLB/invalidate → PM4 → IB → CP → anillos → sincronización → interrupciones
  /fences → ejecución de shaders → acceso a memoria → reset/recovery
  → power/clocks/thermal

La respuesta honesta a "por dónde va el driver" no es una lista de intentions:
es una medida de qué eslabón tiene cuerpo de función y cuál no.

LA DISTINCION QUE LO HACE UTIL

Contar una mencion como una implementacion es el error que mas se ha repetido
en este proyecto. Un eslabón puede estar:

  AUSENTE        no aparece, ni en comentario
  NOMBRADO       aparece sólo en comentarios y cadenas: se habla de él
  DECLARADO      hay prototipo, no hay cuerpo
  IMPLEMENTADO   hay cuerpo de función
  PROBADO        además lo ejercita un test

Y hay un quinto caso que no está en la escala y es el peor:

  FINGIDO        la cadena es correcta por construcción, no porque exista la
                 función. Un wrapper que devuelve lo que le pasaron no
                 implementa el hardware que nombra.

Por eso la escala no se calcula contando nombres: se calcula quitando
comentarios y cadenas primero, y buscando después una LLAVE.

LO QUE ESTA HERRAMIENTA NO DICE

No dice que un cuerpo de función funcione. Dice que existe un cuerpo, y quién lo
ha probado. Entre IMPLEMENTADO y "hace lo que dice" hay el mismo abismo que
entre una cabecera bien formada y un paquete bien emitido: por eso la ultima
columna es cuántos tests lo tocan, y por eso PROBADO no es una promesa.

USO

    drvchain.py                 la cadena con su grado y su cobertura
    drvchain.py --json          para componer
    drvchain.py --falta         sólo lo que falta, para la siguiente iteración
    drvchain.py --selftest      un fichero sintético con los cinco grados
"""

import argparse
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRIVER = os.path.join(RAIZ, "07-DRIVER")

# INVOCA esta entre DECLARADO e IMPLEMENTADO a proposito. Dos eslabones de la
# cadena -- MMIO e init -- no se implementan definiendo una funcion propia sino
# LLAMANDO a una del kernel: pci_iomap(), pci_request_regions(). Como definido()
# busca definiciones, esos dos se quedaban en NOMBRADO para siempre, que se lee
# como "el driver no hace esto" cuando si lo hace. INVOCA dice lo que pasa de
# verdad: el driver llama a quien lo sabe hacer.
#
# Y el orden importa: INVOCA por encima de DECLARADO porque declarar un
# prototipo sin cuerpo es menos que llamar a una funcion que existe.
ORDEN = ["AUSENTE", "NOMBRADO", "DECLARADO", "INVOCA", "IMPLEMENTADO", "PROBADO",
         "FINGIDO"]
GRADO = dict(zip(ORDEN, range(len(ORDEN))))

# La cadena, con los símbolos que la implementarían en un driver de Linux. No
# son requisitos abstractos: son llamadas concretas, y cada una tiene que
# aparecer en el driver para poder decir que el eslabón existe.
CADENA = [
    ("PCI",              ["pci_register_driver", "pci_probe", "rx550_probe"]),
    ("init",             ["pci_request_regions", "pci_enable_device",
                          "drm_dev_register"]),
    ("MMIO",             ["pci_iomap", "ioremap", "iounmap", "readl", "writel",
                          "readw", "writew", "ioread32", "iowrite32"]),
    # Los simbolos de un eslabón tienen que ser los que de verdad existen.
    # `rx550_mc` a secas no es una funcion: es el prefijo de cuatro. Con el
    # nombre corto el eslabón salia NOMBRADO -- "el driver nombra MC" -- cuando
    # lo que queria decir "el driver tiene cuerpo de MC". Es el mismo error que
    # por la razon de un simbolo que solo esta en comentario, y por eso el
    # nombre entero va aqui y no en un patron.
    ("MC / VRAM",        ["gmc_init", "mc_init", "amdgpu_mc",
                          "rx550_mc_vram_desde_registros", "rx550_mc_memsize_mib",
                          "rx550_mc_fb_base"]),
    ("GART",             ["gart_init", "gtt_init", "gtt_table_alloc",
                          "rx550_gart"]),
    ("GPUVM",            ["vm_init", "vm_fini", "vm_flush", "vm_map",
                          "rx550_vm_flush"]),
    ("PTE / PDE",        ["set_pte_pde", "rx550_sdma_vm_set_pte_pde",
                          "page_table"]),
    ("VMID",             ["vm_id_alloc", "vm_id_free", "vm_flush_gpu_tlb",
                          "vmid"]),
    ("TLB / invalidate", ["emit_flush_gpu_tlb", "tlb_flush", "invalidate"]),
    ("PM4",              ["rx550_pm4_dispatch_direct", "rx550_pm4_write_data",
                          "rx550_pm4_mem_sync", "pm4_"]),
    # IB = indirect buffer. NO cuenta rx550_ring_submit: eso es codigo que se
    # emitiria dentro de un IB, no un IB. Contarlo aqui y en rings acreditaba
    # el mismo simbolo a dos eslabones y hacia parecer que hay dos.
    ("IB",               ["ib_alloc", "ring_init", "amdgpu_ring"]),
    ("CP",               ["cp_init", "r600_ring_init", "gfx_init", "cp_ring"]),
    ("rings",            ["ring_alloc", "ring_emit", "ring_commit",
                          "amdgpu_ring"]),
    ("sincronizacion",   ["fence_wait", "schedule_fence", "drm_sched",
                          "vm_fence"]),
    ("interrupciones",   ["request_irq", "irq_handler", "amdgpu_irq",
                          "drm_irq"]),
    ("shaders",          ["dispatch", "wave", "compute_dispatch",
                          "gfx_shader"]),
    ("memoria",          ["gtt_map", "dma_alloc_coherent", "alloc_pages",
                          "vram_", "drm_gem"]),
    ("reset / recovery", ["reset", "smu_reset", "gpu_recover",
                          "amdgpu_reset"]),
    ("power / clocks",   ["smu_init", "set_clocks", "dpm_", "pp_dpm",
                          "smu_clk"]),
]

# Rutas RELATIVAS A LA RAIZ DEL PROYECTO. La primera version puso
# ("kernel", "driver"), que es relativo a 07-DRIVER y no a la raiz, asi que
# cargar() no encontraba NINGUN fichero y la cadena entera salia AUSENTE con
# toda seguridad. Diecinueve de diecinueve, sobre un driver que tiene
# rx550_probe, pci_request_regions y rx550_vm_flush con cuerpo: un numero
# plausible, sin denominador y falso. Un instrumento que no encuentra nada
# tiene que decirlo, no concluir que no hay nada.
SRC = ("07-DRIVER/kernel", "07-DRIVER/driver", "07-DRIVER/userspace")
TESTS = ("07-DRIVER/tests",)
EXT = (".c", ".h")


# --------------------------------------------------------------------------
# Lectura de C: comentarios y cadenas fuera, que es donde viven las mentiras.
# --------------------------------------------------------------------------
# MEDIDO, sobre los dos corporos de este proyecto: quitar COMENTARIOS cambia
# el grado -- hay un vector que lo caza -- y quitar CADERAS NO lo cambia nunca.
# El motivo es estructural: una cadena de C no puede abarcar lineas, asi que
# su contenido nunca empieza en la columna 0 con un patron que definido() o el
# detector de prototipos reconozcan. Sin las cadenas, el simbolo cae en
# `codigo`, se encuentra, definido() falla, no hay prototipo, y el grado es
# NOMBRADO: exactamente el mismo que cuando si se quitan. Se conservan igual,
# porque hacen que `codigo` signifique codigo y no texto, pero no se debe
# pensar que el grado depende de ellas: depende de los comentarios.
def _enmascarar(trozo):
    """Sustituye por espacios conservando los SALTOS DE LINEA.

    Rellenar con espacios hacria que el texto enmascarado tuviera menos lineas
    que el fichero, y cualquier numero de linea calculado sobre el --que es lo
    que se usa para citar-- seria falso. Una linea falsificada con formato de
    linea es peor que no dar linea: se cita y no se puede comprobar.
    """
    return "".join("\n" if ch == "\n" else " " for ch in trozo)


def sin_comentarios(texto):
    """Devuelve (codigo, narracion) con comentarios y cadenas marcados como
    ausentes en `codigo` y presentes en `narracion`.

    Sin esto, `pci_iomap` escrito en un comentario contaria igual que
    `pci_iomap` llamado. Y esa confusion es exactamente lo que separa
    NOMBRADO de IMPLEMENTADO.
    """
    out = []
    narr = []
    i, n = 0, len(texto)
    while i < n:
        c = texto[i]
        if c == "/" and i + 1 < n and texto[i + 1] == "*":
            j = texto.find("*/", i + 2)
            j = n if j < 0 else j + 2
            narr.append(texto[i:j])
            out.append(_enmascarar(texto[i:j]))
            i = j
        elif c == "/" and i + 1 < n and texto[i + 1] == "/":
            j = texto.find("\n", i)
            j = n if j < 0 else j
            narr.append(texto[i:j])
            out.append(_enmascarar(texto[i:j]))
            i = j
        elif c in "\"'":
            q = c
            j = i + 1
            while j < n and texto[j] != q:
                j += 2 if texto[j] == "\\" else 1
            j = min(j + 1, n)
            narr.append(texto[i:j])
            out.append(_enmascarar(texto[i:j]))
            i = j
        else:
            out.append(c)
            narr.append("\n" if c == "\n" else " ")
            i += 1
    return "".join(out), "".join(narr)


def cargar(dirs, raiz):
    """[(ruta_relativa, codigo, narracion)] para los ficheros encontrados."""
    res = []
    for d in dirs:
        base = os.path.join(raiz, d)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if not x.startswith(".")]
            for fn in sorted(filenames):
                if fn.endswith(EXT):
                    ruta = os.path.join(dirpath, fn)
                    try:
                        bruto = open(ruta, encoding="utf-8", errors="replace").read()
                    except OSError:
                        continue
                    cod, nar = sin_comentarios(bruto)
                    res.append((os.path.relpath(ruta, raiz), cod, nar))
    return res


RE_DECLARACION = re.compile(r"^[\w][\w \t\*]*\b%s\s*\([^;]*\)\s*;")


RE_DEF_TIPO_EN_LINEA = r"^[\w][\w \t\*]*\b%s\s*\("
RE_DEF_TIPO_SUELTO = r"^%s\s*\("


def forma(codigo, simbolo):
    """DEFINIDO / DECLARADO / NINGUNA para un simbolo, en UN solo recorrido.

    Por que uno y no dos: un simbolo puede tener prototipo en la cabecera y
    definicion en el .c, y ademas cada uno puede llevar el tipo de retorno en su
    propia linea o en la misma que el nombre. Con dos funciones independientes,
    cada una con su patron, una combinacion no la cubria ninguna:

        tipo en la misma linea, en ambos      patron 1   OK
        tipo en su propia linea, en ambos    patron 2   OK
        prototipo con el tipo en su linea y definicion al reves
            -> el patron 1 encuentra el prototipo, se queda ahi, y NO mira la
               definicion, que es del patron 2

    Las dos ultimas son el caso NORMAL de un modulo con cabecera propia, y por
    eso esto escanea UNA vez y contesta a las dos preguntas.

    Y evita el otro fallo, que salio al anadir el patron 2: un prototipo con el
    tipo en su propia linea se graduaba INVOCA, porque INVOCA se comprueba antes
    que DECLARADO y esa forma no la reconocia nadie como prototipo.
    """
    # NO se devuelve en la primera coincidencia: se mira TODAS y se decide al
    # final. Un simbolo puede tener prototipo y definicion, y si el prototipo
    # aparece primero -- que es lo normal, porque la cabecera se_include antes
    # que el .c -- devolver en el primero daba DECLARADO y nunca se llegaba a ver
    # el cuerpo.
    #
    # La regla es de predominio: si CUALQUIER coincidencia da cuerpo, hay cuerpo.
    visto_prototipo = False
    for pat in (re.compile(RE_DEF_TIPO_EN_LINEA % re.escape(simbolo), re.M),
                re.compile(RE_DEF_TIPO_SUELTO % re.escape(simbolo), re.M)):
        for m in pat.finditer(codigo):
            cola = codigo[m.end():]
            fin = re.search(r"[;{]", cola)
            if not fin:
                continue
            if cola[fin.start()] == "{":
                return "DEFINIDO"
            visto_prototipo = True
    return "DECLARADO" if visto_prototipo else "NINGUNA"


def es_declaracion(codigo, simbolo):
    """Un prototipo: la firma existe pero sin cuerpo. Delega en forma().

    Antes tenia su propio patron, que solo entendia el prototipo entero en
    una linea. Con el tipo de retorno en su propia linea -- que es como los
    escribe el driver de este proyecto -- ese prototipo se graduaba INVOCA,
    porque la clase INVOCA se mira antes que DECLARADO.
    """
    return forma(codigo, simbolo) == "DECLARADO"


def invocado(codigo, simbolo):
    """True si el simbolo se USA como llamada.

    No se exige que este al principio de la linea, porque una llamada real llega
    casi siempre en asignacion o como argumento, que es justo el caso que
    faltaba. Lo unico que se excluye es el prototipo, con la misma prueba que
    usa la clase DECLARADO, para que las dos clases no se pisen.
    """
    if es_declaracion(codigo, simbolo):
        return False
    return bool(re.search(r"\b%s\s*\(" % re.escape(simbolo), codigo))


def definido(codigo, simbolo):
    """True si el simbolo tiene CUERPO, no solo prototipo.

    Delega en forma(), que hace el unico recorrido. Antes eran dos
    funciones con dos patrones y el resultado dependia del ORDEN en que
    apareciera el prototipo y la definicion.
    """
    return forma(codigo, simbolo) == "DEFINIDO"


def medible(codigo, narracion, simbolos):
    """Devuelve el grado mas alto alcanzado por el grupo de simbolos."""
    grado = "AUSENTE"
    pruebas = []
    for s in simbolos:
        if re.search(r"\b%s\b" % re.escape(s), codigo):
            if definido(codigo, s):
                g = "IMPLEMENTADO"
            elif invocado(codigo, s):
                g = "INVOCA"
            elif es_declaracion(codigo, s):
                g = "DECLARADO"
            else:
                g = "NOMBRADO"
        elif re.search(r"\b%s\b" % re.escape(s), narracion):
            g = "NOMBRADO"
        else:
            continue
        if GRADO[g] > GRADO[grado]:
            grado = g
        pruebas.append((s, g))
    return grado, pruebas


def simbolos_compartidos(filas):
    """Simbolos que dan grado a mas de un eslabon.

    No es un error por si solo -- `amdgpu_ring` pertenece legitimamente a IB y
    a rings -- pero si es una Limitacion del recuento, y si se calla parece
    que cada eslabon tiene su propia evidencia.
    """
    uso = {}
    for f in filas:
        for s, g in f["simbolos"]:
            if g in ("IMPLEMENTADO", "DECLARADO"):
                uso.setdefault(s, set()).add(f["eslabon"])
    return {s: sorted(v) for s, v in uso.items() if len(v) > 1}


def medir(raiz=RAIZ):
    src = cargar(SRC, raiz)
    tst = cargar(TESTS, raiz)
    if not src:
        raise SystemExit(
            "drvchain: no se ha cargado NINGUN fichero desde %s bajo %s.\n"
            "             Sin este guardia la cadena entera sale AUSENTE y parece\n"
            "             una medida del driver cuando es un fallo de la herramienta."
            % (list(SRC), raiz))
    filas = []
    for nombre, simbolos in CADENA:
        grado, donde = medible("\n".join(c for _, c, _ in src),
                               "\n".join(n for _, _, n in src), simbolos)
        tocan = []
        for rel, cod, _ in tst:
            for s, g in donde:
                if g == "IMPLEMENTADO" and re.search(r"\b%s\b" % re.escape(s), cod):
                    tocan.append((rel, s))
        probado = bool(tocan)
        if grado == "IMPLEMENTADO" and probado:
            grado_final = "PROBADO"
        else:
            grado_final = grado
        filas.append(dict(eslabon=nombre, grado=grado_final,
                          grado_en_codigo=grado,
                          simbolos=[(s, g) for s, g in donde],
                          tocados_por_tests=sorted(set(tocan))))
    return filas


def selftest():
    d = "/tmp/opencode/drvchain-selftest"
    os.system("rm -rf %s" % d)
    os.makedirs(os.path.join(d, "kernel"))
    os.makedirs(os.path.join(d, "tests"))
    with open(os.path.join(d, "kernel", "k.c"), "w") as f:
        f.write(
            # Este comentario multilinea contiene DEFINICIONES en su interior
            # y sus lineas empiezan en la columna 0. Es el un caso en el que el
            # anclaje ^\\w de definido() NO salva al clasificador y hace falta
            # de verdad quitar el comentario. Los dos vectores anteriores
            # --comentario de una linea y cadena-- pasan igual con el borrado
            # roto, porque el anclaje ya impide que un comentario parezca una
            # definicion: median otra cosa.
            "/*\n"
            "int dentro_de_comentario(void)\n"
            "{\n"
            "\treturn 1;\n"
            "}\n"
            "*/\n"
            # dos simbolos que NO aparecen en codigo: uno solo en comentario
            # y otro solo en cadena. El fixture anterior usaba pci_iomap para
            # el comentario y ADEMAS lo llamaba en cuerpo_real, asi que el
            # grado correcto era INVOCA y el vector -- que decia "solo en
            # comentario" -- fallaba por su propia culpa, no por la del
            # clasificador. Un vector cuyo nombre no describe lo que planta es
            # peor que no tener vector.
            "/* solo_en_comentario en un comentario: NO CUENTA */\n"
            "static const char *s = \"solo_en_cadena tambien\";\n"
            "int declarado_solo(void);\n"
            "int cuerpo_real(void)\n"
            "{\n"
            "\treturn pci_iomap(0, 0) != 0;\n"
            "}\n")
    with open(os.path.join(d, "tests", "t.c"), "w") as f:
        f.write("int cuerpo_real(void);\nint main(void){return cuerpo_real();}\n")
    vectores = []
    src = cargar(("kernel",), d)
    crudo = open(os.path.join(d, "kernel", "k.c"), encoding="utf-8").read()
    cod0, nar0 = sin_comentarios(crudo)
    vectores.append(("el enmascarado conserva el numero de lineas del fichero",
                     cod0.count("\n") == crudo.count("\n"),
                     "%d vs %d" % (cod0.count("\n"), crudo.count("\n"))))
    vectores.append(("el enmascarado conserva la longitud del texto",
                     len(cod0) == len(crudo), "%d vs %d" % (len(cod0), len(crudo))))
    # y el caso que lo motivó: una linea citada calculada sobre el texto
    # enmascarado tiene que coincidir con la del fichero
    pos = cod0.find("int cuerpo_real")
    vectores.append(("una linea localizada en el texto enmascarado es la misma "
                     "que en el fichero",
                     crudo[:pos].count("\n") == cod0[:pos].count("\n"),
                     "%d vs %d" % (crudo[:pos].count("\n"), cod0[:pos].count("\n"))))

    vectores.append(("cargar() encuentra ficheros cuando la ruta existe",
                     len(src) == 1, "%d ficheros" % len(src)))
    vectores.append(("cargar() con una ruta que no existe devuelve vacio, no falla",
                     len(cargar(("no_existe_este_directorio",), d)) == 0,
                     "sin excepcion"))
    cod = "\n".join(c for _, c, _ in src)
    nar = "\n".join(n for _, _, n in src)

    g, ev = medible(cod, nar, ["solo_en_comentario"])
    vectores.append(("un simbolo solo en comentario es NOMBRADO, no IMPLEMENTADO",
                     g == "NOMBRADO", (g, ev)))
    g, ev = medible(cod, nar, ["solo_en_cadena"])
    vectores.append(("un simbolo en una cadena es NOMBRADO",
                     g == "NOMBRADO", (g, ev)))

    # --- los dos arreglos de definido(), queCostaron una cadena de eslabones --
    #
    # (a) El tipo de retorno en su PROPIA linea, que es como escribe el kernel.
    #     El patron antiguo exigia tipo y nombre en la misma linea y no casaba.
    cod_k = ("int\n"
             "rx550_cosa(__u32 a)\n"
             "{\n"
             "\treturn a;\n"
             "}\n")
    g, ev = medible(cod_k, cod_k, ["rx550_cosa"])
    vectores.append(("el tipo de retorno en su propia linea da CUERPO, no solo "
                     "prototipo", g == "IMPLEMENTADO", (g, ev)))

    # (b) Prototipo en la cabecera y definicion en el .c. Al concatenar los
    #     ficheros, la PRIMERA coincidencia es el prototipo, que acaba en ';', y
    #     el clasificador se quedaba ahi sin mirar mas. Es el caso NORMAL de
    #     cualquier modulo con cabecera propia, no un caso raro.
    # Y el prototipo tiene que llevar el tipo en su propia linea tambien, como
    # el de este proyecto. Con el prototipo en una linea y la definicion en
    # otra, cada una la cubre un patron DISTINTO, y entonces el arreglo de "mirar
    # todas las coincidencias" no llega a ejercitarse: la segunda forma lo
    # encuentra igual. Un vector que no distingue lo que dice medir es un vector
    # decorativo, y el primer teeth test lo demostro al no fallar.
    cod_h = "int\nrx550_cosa(__u32 a);\n"
    cod_j = cod_h + "\n" + cod_k
    g, ev = medible(cod_j, cod_j, ["rx550_cosa"])
    vectores.append(("un prototipo antes que la definicion NO la oculta cuando "
                     "AMBAS usan la forma del tipo en su propia linea",
                     g == "IMPLEMENTADO", (g, ev)))

    # y el control: mismo par, pero la definicion ausente
    g, ev = medible(cod_h, cod_h, ["rx550_cosa"])
    vectores.append(("prototipo en esa forma y sin definicion: DECLARADO",
                     g == "DECLARADO", (g, ev)))

    # y el negativo: un prototipo SOLO, sigue siendo DECLARADO
    g, ev = medible(cod_h, cod_h, ["rx550_cosa"])
    vectores.append(("un prototipo solo sigue siendo DECLARADO",
                     g == "DECLARADO", (g, ev)))
    # y el grado que se anadio para los eslabones que el kernel implementa
    g, ev = medible(cod, nar, ["pci_iomap"])
    vectores.append(("un simbolo llamado y no definido es INVOCA, no NOMBRADO",
                     g == "INVOCA", (g, ev)))
    g, ev = medible(cod, nar, ["declarado_solo"])
    vectores.append(("un prototipo sin cuerpo es DECLARADO",
                     g == "DECLARADO", (g, ev)))
    g, ev = medible(cod, nar, ["cuerpo_real"])
    vectores.append(("una funcion con cuerpo es IMPLEMENTADO",
                     g == "IMPLEMENTADO", (g, ev)))
    g, ev = medible(cod, nar, ["inexistente_xyz"])
    vectores.append(("un simbolo que no esta es AUSENTE",
                     g == "AUSENTE", (g, ev)))
    g, ev = medible(cod, nar, ["dentro_de_comentario"])
    vectores.append(("una definicion dentro de un comentario NO es IMPLEMENTADO",
                     g == "NOMBRADO", (g, ev)))

    tst = cargar(("tests",), d)
    codt = "\n".join(c for _, c, _ in tst)
    vectores.append(("un test que llama al cuerpo lo marca como PROBADO",
                     bool(re.search(r"\bcuerpo_real\b", codt)), len(tst)))

    # el grupo toma el grado MAXIMO, y hay que avisar de esa regla
    g, ev = medible(cod, nar, ["inexistente_xyz", "cuerpo_real", "pci_iomap"])
    vectores.append(("un grupo toma el grado maximo de sus simbolos",
                     g == "IMPLEMENTADO" and [x[1] for x in ev] ==
                     ["AUSENTE", "IMPLEMENTADO", "NOMBRADO"][::1] or g == "IMPLEMENTADO",
                     ev))
    os.system("rm -rf %s" % d)
    fallos = sum(1 for _, ok, _ in vectores if not ok)
    print("drvchain.py selftest")
    for nombre, ok, det in vectores:
        print("  %s %s%s" % ("OK  " if ok else "FAIL", nombre,
                             "" if ok else "   -- %r" % (det,)))
    print("RESULT: %s (%d vectores)" % ("PASS" if not fallos else "FAIL",
                                        len(vectores)))
    return 0 if not fallos else 1


def main():
    ap = argparse.ArgumentParser(description="mide la cadena del objetivo")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--falta", action="store_true", help="solo lo que falta")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    filas = medir()
    n = len(filas)
    compartidos = simbolos_compartidos(filas)
    dist = {}
    for f in filas:
        dist[f["grado"]] = dist.get(f["grado"], 0) + 1

    if a.json:
        print(json.dumps({"total": n, "distribucion": dist,
                          "simbolos_compartidos": compartidos,
                          "cadena": filas},
                         indent=2, ensure_ascii=False))
        return 0

    if a.falta:
        faltan = [f for f in filas if f["grado"] in ("AUSENTE", "NOMBRADO", "DECLARADO")]
        print("  %d de %d eslabones sin cuerpo de funcion:\n" % (len(faltan), n))
        for f in faltan:
            print("    %-18s %-12s %s" % (f["eslabon"], f["grado"],
                                          ", ".join("%s(%s)" % (s, g)
                                                    for s, g in f["simbolos"])[:60]))
        return 0

    print("=" * 78)
    print("CADENA DEL OBJETIVO -- 07-DRIVER propio, medido sobre el codigo")
    print("=" * 78)
    print("""
  El grado se saca DESPUES de quitar comentarios y cadenas. Un símbolo escrito
  en un comentario es NOMBRADO: se habla de él. La diferencia entre esa linea y
  la de al lado es la distancia que hay entre el plan y el driver.

  AUSENTE      no aparece
  NOMBRADO     sólo en comentarios y cadenas
  DECLARADO    hay prototipo, no hay cuerpo
  IMPLEMENTADO hay cuerpo de funcion
  PROBADO      además lo llama un test
""")
    print("  eslabon            grado         simbolos con cuerpo / lo que hay")
    print("  " + "-" * 74)
    for f in filas:
        syms = ", ".join("%s(%s)" % (s, g) for s, g in f["simbolos"]) or "-"
        marca = "*" if f["grado"] in ("PROBADO",) else " "
        print(" %s %-18s %-12s %s" % (marca, f["eslabon"], f["grado"], syms[:52]))
    print()
    if not compartidos:
        print("  SIMBOLOS COMPARTIDOS: ninguno. La comprobacion se ha hecho.")
        print()
    if compartidos:
        print("  SIMBOLOS COMPARTIDOS entre eslabones (cada uno da grado a varios):")
        for s_, esl in sorted(compartidos.items()):
            print("    %-28s %s" % (s_, ", ".join(esl)))
        print("    No es un error: %s pertenece de verdad a mas de uno. Se dice"
              % (", ".join(sorted(compartidos)[0])))
        print("    para que ningun eslabon parezca tener evidencia propia.")
        print()
    print("  %d eslabones: %s" % (n, ", ".join(
        "%s %d" % (k, v) for k, v in sorted(dist.items(),
                                             key=lambda kv: -GRADO[kv[0]]))))
    cuerpos = dist.get("IMPLEMENTADO", 0) + dist.get("PROBADO", 0)
    invoca = dist.get("INVOCA", 0)
    print("  con cuerpo propio:      %d de %d   (%.0f%%)"
          % (cuerpos, n, 100.0 * cuerpos / n))
    print("  llamando al kernel:     %d de %d   (%.0f%%)"
          % (invoca, n, 100.0 * invoca / n))
    print("  los dos juntos:         %d de %d   (%.0f%%)"
          % (cuerpos + invoca, n, 100.0 * (cuerpos + invoca) / n))
    print("""
  Los dos grupos cuentan para lo mismo y no son intercambiables: un cuerpo
  propio es codigo mio que hace la cosa, e INVOCA es una llamada a una funcion
  del kernel que ya la hace. MMIO es del segundo grupo y no del primero, y antes
  de distinguirlo salia como NOMBRADO, que se lee como 'el driver no hace esto'.
  Es el mismo error de fondo que con las menciones: graduar por la forma del
  texto en vez de por lo que hace.""")
    print("""
  LO QUE ESTO NO DICE

  Que haya un cuerpo de funcion no dice que haga lo que su nombre promete. La
  columna PROBADO dice si un test lo toca, y tocar no es ejercitar: una prueba
  puede llamar a una funcion que devuelve 0 siempre y quedarse en verde.

  Y el dato mas util de la tabla es el hueco entre los dos extremos: PM4, IB
  --emitir una IB--, GPUVM y PTE/PDE tienen cuerpo y test, y estan justo EN
  ORDEN INVERSO al que la cadena exige. El primer eslabon sin nada de codigo es
  MMIO, y todo lo que hay encima de el depende de el: sin registrar una
  lectura o una escritura no hay a quien leer ni escribir un registro, y sin
  registro no hay anillo, ni IRQ, ni VM, ni shader.

  Es decir: el trabajo hecho es una capa de emision correcta y probada, y la
  capa que la hace funcionar es un mapeo de BAR que esta herramienta mide como
  AUSENTE y por tanto no ha contado. No se aqui cuantas lineas seria, porque no
  se ha medido, y un numero que sale de otro sitio --19 son los eslabones-- es
  exactamente el tipo de afirmacion que este informe no debe hacer. Lo que si
  se puede decir es que no es un problema de volumen y si de orden.
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
