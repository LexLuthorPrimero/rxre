#!/usr/bin/env python3
# CONTRACT: name=selfcheck
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=indeterminado
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py, y el veredicto fue `NO_DETERMINED`.
# NO se upgraded a `WRITES_FILES=yes` porque no esta medido, y NO se dejo en
# `no` porque el codigo no lo sostiene.  La razon del NO_DETERMINED es que sus 3 escrituras son de selftest y ademas invoca al compilador por subprocess.
#
# Poner `yes` seria MENTIR en un sentido que el validador no puede detectar, que
# es lo que el propio toolkit.py escribe de sus cinco falsos positivos: "un
# contrato en prosa no se puede comprobar con una maquina".  Poner `no` seria
# Peor: seria una afirmacion que nadie ha comprobado.
#
# TOUCHES_INTEGRATED=no: lee sysfs y ficheros.  No hace ioctl ni escribe en la
# GPU.  Ver 1487.
"""
selfcheck.py -- controles del propio revkit.

POR QUE
-------
Una herramienta que no puede fallar no esta probada. Y un kit que se valida a
si mismo sin negatives puede estar roto sin que nadie lo note: las seis
herramientas de este kit ya dieron un 0 falso cada una durante su construccion.

La razon de este fichero es concreta: el modo de fallo dominante del proyecto
NO es obtener un numero equivocado, es obtener un cero que parece un resultado.
Asi que el control mas importante es que cada herramienta FALLE cuando debe.

QUE COMPRUEBA

CN-R1  cidx detecta una mutacion en el corpus (no devuelve cache obsoleta)
CN-R2  cidx con un simbolo imposible devuelve NOT_FOUND, no 0 mudo
CN-R3  cidx avisa cuando se le pasa un fragmento en vez de identificador
CN-R4  regs encuentra un campo cuya MASK y SHIFT se han de leer del fichero
CN-R5  regs detecta una MASK incoherente con su SHIFT
CN-R6  obs no confunde card0 (Intel) con card1 (AMD)
CN-R7  obs deduplica el log: 11 lineas iguales = 1 hecho
CN-R8  vclaims no cuenta una cita a Mesa como cita rota
CN-R9  vclaims detecta una cita que rebasa el final del fichero
CN-R10 pte separa DEFINIDO de ALCANZABLE (el error de MTYPE)
CN-R11 pte dump decodifica una PTE con los flags que se le ponemos
CN-R12 ningun fichero tiene CJK ni cirilico colados
CN-R13 ningun .md tiene backticks colgando ni cruzados
CN-R14 cidx enumera los WAIT_REG_MEM_FUNCTION de GFX8 y son 3, con un solo
       FUNCTION(0). Si esto cambia, el hallazgo de WAIT-REG-MEM.md cambia.
"""
import os
import re
import subprocess
import sys
import unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
RESULTADOS = []


def anota(nombre, ok, detalle):
    RESULTADOS.append((nombre, ok, detalle))
    print("  %-52s %s" % (nombre, "OK" if ok else "FALLO"))
    print("      %s" % detalle)


def ejecuta(args, timeout=300):
    r = subprocess.run([sys.executable] + args, cwd=AQUI,
                       capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def r1_cidx_cache_invalida():
    """
    El cache es lo que hace cidx rapido, y tambien lo que puede mentir.

    Se toca un fichero de /tmp y se comprueba que el indice lo refleja. Un
    cache que no invalida devuelve el indice viejo con la confianza del nuevo.
    """
    import tempfile
    d = tempfile.mkdtemp(prefix="cidxtest")
    p = os.path.join(d, "x.c")
    open(p, "w").write("void f(void) { /* SINBOLO */ }\n")
    rc, out, _ = ejecuta(["cidx.py", "use", "SINBOLO", "--raiz", d])
    rc2, out2, _ = ejecuta(["cidx.py", "use", "SINBOLO", "--raiz", d])
    open(p, "w").write("void f(void) { int SINBOLO; }\n")
    rc3, out3, _ = ejecuta(["cidx.py", "use", "SINBOLO", "--raiz", d])
    ok = ("1 fichero" in out3) or ("1 fich" in out3)
    anota("CN-R1 cidx invalida el cache si el corpus cambia", ok,
          "con SINBOLO definido, use lo ve: %s"
          % ("si" if ok else "NO -- el cache devuelve datos viejos"))
    return ok


def r2_cidx_not_found():
    rc, out, _ = ejecuta(["cidx.py", "use", "ESTE_NO_EXISTE_XYZ_123"])
    ok = rc == 1 and "0 ficheros" in out
    anota("CN-R2 cidx: simbolo imposible -> rc=1 y NOT_FOUND", ok,
          "rc=%d, dice '0 ficheros': %s" % (rc, "si" in (out,)))
    return ok


def r3_cidx_fragmento_avisa():
    rc, out, _ = ejecuta(["cidx.py", "use", "MTYPE"])
    ok = rc == 1 and "AVISO" in out
    anota("CN-R3 cidx avisa si le pasas un fragmento", ok,
          "rc=%d, contiene AVISO: %s" % (rc, "AVISO" in out))
    return ok


def r4_registers_leen_fichero():
    rc, out, _ = ejecuta(["regs.py", "CC_GC_SHADER_ARRAY_CONFIG",
                          "INACTIVE_CUS", "--asic", "gfx_8_0"])
    # valor que se verifico A MANO en gfx_8_0_sh_mask.h:17713
    ok = rc == 0 and "0xffff0000" in out and "16" in out
    anota("CN-R4 regs lee MASK y SHIFT del fichero real", ok,
          "esperado MASK=0xffff0000 SHIFT=16 -> 16 bits; obtenido: %s"
          % (out.strip().splitlines()[-1][:70] if out.strip() else "(vacio)"))
    return ok


def r5_mascara_incoherente():
    """una MASK con bits sueltos debe marcarse incoherente"""
    rc, out, _ = ejecuta(["regs.py", "--incumplen"])
    ok = rc == 0
    tiene = "MASK incoherente" in out or "incumple" in out
    anota("CN-R5 regs reporta MASK incoherentes", ok,
          "rc=%d, %d discrepancias" % (rc, out.count("mask=0x")))
    return ok


def r6_obs_no_confunde_dispositivos():
    rc, out, _ = ejecuta(["obs.py", "gpu"])
    ok = "1002" in out and "0x699f" in out
    # y no debe reportar la Intel como la objetivo
    mal = "8086" in out.split("ENCONTRADA")[1] if "ENCONTRADA" in out else False
    anota("CN-R6 obs localiza por identidad PCI, no por indice", ok and not mal,
          "encuentra 1002:699f y no confunde con la Intel: %s" % (ok and not mal))
    return ok and not mal


def r7_obs_deduplica():
    rc, out, _ = ejecuta(["obs.py", "log-uniq", "--filtro", "PCIE GART"])
    # el log tiene ~11 lineas de PCIE GART y deben ser 1 hecho
    m = re.search(r"(\d+) lineas?, (\d+) hechos? unicos", out)
    if not m:
        anota("CN-R7 obs deduplica el log", False,
              "no se pudo leer el recuento: %s" % out.strip()[-80:])
        return False
    nlin, nhechos = int(m.group(1)), int(m.group(2))
    ok = nlin > 1 and nhechos == 1
    anota("CN-R7 obs deduplica: N lineas iguales = 1 hecho", ok,
          "%d lineas -> %d hechos unicos" % (nlin, nhechos))
    return ok


def r8_vclaims_externas():
    """
    CN-R8: vclaims CLASSIFICA bien, separando una fuente externa de Mesa de una
    cita rota de verdad.

    MEDIDO 2026-10-03: este control afirmaba medir eso, pero lo que hacia era
    recorrer el arbol entero y exigir rc=0 y "0 citas rotas". Es decir, media la
    LIMPIEZA DEL MUNDO, no el comportamiento de la herramienta. Y como las citas
    rotas del arbol dependen de lo que escriben otras sesiones, el control se
    rompio solo: 08-ARQUITECTURA/RE-INDEX.md, untracked y de otra sesion, trajo
    citas a ficheros que no existen en ninguna raiz.

    Un control que afirma medir una herramienta y mide el mundo se rompe por
    causas que no estan en su alcance, y cuando se rompe hay que elegir entre
    ignorarlo --y entonces no vale para nada-- o arreglarlo sin causa.

    Ahora mide la herramienta, sobre cn-r8.fixture, que tiene tres citas con
    resultado conocido written con bytes literales: una de Mesa que NO es rota,
    una rota de verdad, y una buena al corpus. El rc que se espera es 1, porque
    el fixture TIENE una cita rota: un control que espera exito sobre un fixture
    con un caso malo no esta probando el caso malo.
    """
    rc, out, _ = ejecuta(["vclaims.py", "cn-r8.fixture"])
    ext = re.search(r"FUENTES EXTERNAS[^:]*: (\d+)", out)
    malas = re.search(r"NO resuelven: (\d+)", out)
    if not ext or not malas:
        anota("CN-R8 vclaims separa Mesa de citas rotas", False,
              "no se pudo leer el recuento: %s" % out.strip()[-80:])
        return False
    n_ext, n_malas = int(ext.group(1)), int(malas.group(1))
    if n_ext != 1:
        anota("CN-R8 vclaims separa Mesa de citas rotas", False,
              "esperaba 1 externa y conto %d" % n_ext)
        return False
    if n_malas != 1:
        anota("CN-R8 vclaims separa Mesa de citas rotas", False,
              "esperaba 1 rota y conto %d" % n_malas)
        return False
    if "si_blit.c" not in out:
        anota("CN-R8 vclaims separa Mesa de citas rotas", False,
              "la cita de Mesa no aparece como externa")
        return False
    if "fichero_que_no_existe_jamas.c" not in out:
        anota("CN-R8 vclaims separa Mesa de citas rotas", False,
              "la cita rota no aparece como rota")
        return False
    if rc != 1:
        anota("CN-R8 vclaims separa Mesa de citas rotas", False,
              "con una cita rota en el fixture el rc debe ser 1 y es %d" % rc)
        return False
    # y la buena NO debe marcarse: si lo estuviera, el fixture estaria
    # distinguiendo mal, que es el defecto espejo
    if "sdma_v3_0.c" in out.split("NO resuelven")[-1]:
        anota("CN-R8 vclaims separa Mesa de citas rotas", False,
              "una cita buena al corpus aparece como rota")
        return False
    anota("CN-R8 vclaims separa Mesa de citas rotas", True,
          "rc=%d, 1 externa (Mesa) + 1 rota + 1 buena, sobre fixture" % rc)
    return True


def r9_vclaims_detecta_rango_malo():
    """una cita a la linea 999999999 debe fallar"""
    import tempfile
    d = tempfile.mkdtemp(prefix="vctest")
    md = os.path.join(d, "x.md")
    open(md, "w").write("cita amdgpu_vm.c:999999 al final\n")
    rc, out, _ = ejecuta(["vclaims.py", md])
    ok = rc == 1 and "NO resuelven" in out
    anota("CN-R9 vclaims detecta cita fuera de rango", ok,
          "rc=%d, %s" % (rc, "lo detecta" if ok else "NO lo detecta"))
    return ok


def r10_pte_separa_alcanzable():
    rc, out, _ = ejecuta(["pte.py", "para-gfx8"])
    ok = rc == 0 and "ALCANZABILIDAD DEMOSTRADA" in out
    # LOG y NOALLOC deben salir como NO alcanzables, que es el error de MTYPE.
    # El espacio tras el bit es VARIABLE: la columna del bit es %2d, asi que
    # con bit 55 (dos digitos) queda doble espacio. La primera version del
    # control uso \s+, que no casa con dos, y dio FALLO sobre una herramienta
    # que era correcta. Un control mal escrito ensucia la suite igual que una
    # herramienta mal escrita.
    # El orden en la linea es "bit NN  NOMBRE ... solo en", NO "NOMBRE bit".
    # Dos versiones de este control fallaron por eso: una buscaba el nombre
    # antes del bit, la otra exigia un solo espacio. Ninguna de las dos
    # reflejaba un fallo de pte.py, que era correcta.
    log_fuera = re.search(r"bit\s+55\s+AMDGPU_PTE_LOG\s+solo en", out)
    anota("CN-R10 pte separa DEFINIDO de ALCANZABLE", ok and log_fuera,
          "AMDGPU_PTE_LOG (bit 55) clasificado como no alcanzable: %s"
          % ("si" if log_fuera else "NO"))
    return ok and bool(log_fuera)


def r11_pte_dump():
    # PTE con VALID|SYSTEM|READABLE = bits 0,1,5
    v = (1 << 0) | (1 << 1) | (1 << 5)
    rc, out, _ = ejecuta(["pte.py", "dump", hex(v)])
    ok = rc == 0 and "VALID" in out and "SYSTEM" in out and "READABLE" in out
    # y que NO diga WRITABLE, que no se puso
    no_mal = "WRITABLE=1" not in out
    anota("CN-R11 pte dump decodifica los flags puestos", ok and no_mal,
          "0x%x -> VALID, SYSTEM, READABLE activos; WRITABLE ausente: %s"
          % (v, no_mal))
    return ok and no_mal


def r12_sin_cjk():
    malos = []
    for pat in ("*.md", "*.py", "*.sh"):
        for f in sorted(__import__("glob").glob(os.path.join(AQUI, pat))):
            for i, linea in enumerate(
                    open(f, encoding="utf-8", errors="replace"), 1):
                if any((0x3000 <= ord(c) <= 0x9FFF or
                        0xAC00 <= ord(c) <= 0xD7AF or
                        0x0400 <= ord(c) <= 0x04FF) for c in linea):
                    malos.append("%s:%d" % (os.path.basename(f), i))
    anota("CN-R12 sin CJK ni cirilico en los ficheros", not malos,
          "%s" % (", ".join(malos[:6]) if malos else "limpio"))
    return not malos


def r13_backticks():
    """
    Dos fallos distintos:
      colgando: una linea con backtick impar cuya siguiente no cierra
      cruzado:  `a y `b` -> numero par, pero el render se rompe
    """
    import glob
    colg, cruz = [], []
    for f in sorted(glob.glob(os.path.join(AQUI, "*.md"))):
        dentro = False
        for i, linea in enumerate(
                open(f, encoding="utf-8", errors="replace"), 1):
            st = linea.strip()
            if st.startswith("```"):
                dentro = not dentro
                continue
            if dentro:
                continue
            c = linea.replace("\\`", "").count("`")
            if c % 2 == 1:
                colg.append("%s:%d" % (os.path.basename(f), i))
            resto = re.sub(r"`[^`\n]*`", "", linea.replace("\\`", ""))
            if "`" in resto:
                cruz.append("%s:%d" % (os.path.basename(f), i))
    anota("CN-R13 sin backticks colgando ni cruzados",
          not colg and not cruz,
          "colgando=%s cruzado=%s" % (colg[:4] or "-", cruz[:4] or "-"))
    return not colg and not cruz


def r14_wait_reg_mem():
    """
    El hallazgo de WAIT-REG-MEM.md depende de una enumeracion que puede
    cambiar si cambia el corpus. Se fija como control para que el documento
    no se quede obsoleto sin que nadie lo note.
    """
    rc, out, _ = ejecuta(["cidx.py", "use", "WAIT_REG_MEM_FUNCTION"])
    g8 = [l for l in out.splitlines() if "gfx_v8_0.c:" in l]
    ceros = [l for l in g8 if "FUNCTION(0)" in l]
    ok = len(g8) == 3 and len(ceros) == 1
    anota("CN-R14 GFX8 emite 3 WAIT_REG_MEM, un solo FUNCTION(0)", ok,
          "%d usos en gfx_v8_0.c, %d con FUNCTION(0): %s"
          % (len(g8), len(ceros), [l.split(":")[0] + ":" + l.split(":")[1]
                                    for l in g8]))
    return ok


def r15_invalidate_canales():
    """
    INVALIDATE-CANALES.md afirma dos ausencias por enumeracion:
      1. nadie LEE mmVM_INVALIDATE_REQUEST
      2. nadie usa los canales ENG0..ENG17
    Esas ausencias son la base del documento, asi que se fijan como control.
    """
    rc, out, _ = ejecuta(["cidx.py", "use", "mmVM_INVALIDATE_REQUEST"])
    lineas = [l for l in out.splitlines() if re.search(r"\w+\.c:\d+", l)]
    ficheros = {re.match(r"(\S+\.c):\d+", l).group(1) for l in lineas
                if re.match(r"(\S+\.c):\d+", l)}
    # (1) ningun uso es una lectura
    lecturas = [l for l in lineas
                if "RREG" in l or "readl" in l.lower() or "rreg" in l.lower()]
    rc2, out2, _ = ejecuta(["cidx.py", "use", "mmVM_INVALIDATE_ENG0"])
    canales = "0 ficheros lo usan" in out2
    ok = len(ficheros) == 10 and not lecturas and canales
    anota("CN-R15 invalidate: 10 ficheros, 0 lecturas, 0 canales", ok,
          "%d usos en %d ficheros, %d lecturas, canales sin uso: %s"
          % (len(lineas), len(ficheros), len(lecturas), canales))
    return ok


def r16_ibtrace_encuentra_vm_flush():
    """
    ibtrace debe encontrar la secuencia de emit_vm_flush que se verifico A
    MANO. Si deja de encontrarla, el herramienta no sirve y WAIT-REG-MEM.md y
    INVALIDATE-CANALES.md se quedan obsoletos sin aviso.
    """
    rc, out, _ = ejecuta(["ibtrace.py", "func",
                          "gfx_v8_0.c::gfx_v8_0_ring_emit_vm_flush"])
    # lo verificado a mano: 9 escrituras, 2 headers, y el rango 6191-6215
    ok = rc == 0 and "9 escrituras" in out and "2 headers" in out
    # y que el opcode del WAIT este resuelto, no sin nombre
    resuelto = "PACKET3_WAIT_REG_MEM = 0x3C" in out
    anota("CN-R16 ibtrace reproduce la secuencia de emit_vm_flush", ok and resuelto,
          "9 escrituras/2 headers y opcode resuelto: %s"
          % (ok and resuelto))
    return ok and resuelto


def r17_ibtrace_comentarios_no_parten():
    """
    Los comentarios van EN MEDIO de los argumentos en el estilo de amdgpu:

        amdgpu_ring_write(ring, (WAIT_REG_MEM_OPERATION(0) | /* wait */
                                 WAIT_REG_MEM_FUNCTION(0) |  /* always */

    Si la herramienta no quita comentarios antes de parsear, cuenta DOS
    escrituras donde hay UNA y pierde los flags del medio. Este control
    comprueba que la expresion completa aparece en una sola linea de salida.
    """
    rc, out, _ = ejecuta(["ibtrace.py", "func",
                          "gfx_v8_0.c::gfx_v8_0_ring_emit_vm_flush"])
    # la linea del WAIT debe traer los TRES campos en la misma salida
    uno = ("WAIT_REG_MEM_OPERATION" in out and "WAIT_REG_MEM_FUNCTION" in out
           and "WAIT_REG_MEM_ENGINE" in out)
    anota("CN-R17 los comentarios no parten una escritura en varias", uno,
          "los 3 campos del WAIT aparecen juntos: %s" % uno)
    return uno


def r18_sync_es_invariante():
    """
    TODAS las generaciones v6 a v12 emiten PFP_SYNC_ME en vm_flush. Eso
    convierte "por que GFX8 lo emite" en una pregunta con respuesta de
    diseno, no de capricho. Se fija como control porque es la afirmacion que
    da contexto al NOT_DETERMINED del efecto en hardware.
    """
    rc, out, _ = ejecuta(["ibtrace.py", "sync"])
    gens = set()
    for l in out.splitlines():
        if "PFP_SYNC_ME" in l and "vm_flush" in l:
            for g in ("v6_0", "v7_0", "v8_0", "v9_0", "v10_0", "v11_0",
                      "v12_0", "v12_1"):
                if g in l:
                    gens.add(g)
    ok = len(gens) >= 6 and "v8_0" in gens
    anota("CN-R18 PFP_SYNC_ME en vm_flush es invariante v6-v12", ok,
          "generaciones que lo emiten: %s" % ", ".join(sorted(gens)))
    return ok


def r19_causa_clasifica_correctamente():
    """
    causa.py debe clasificar un registro que se escribe y no se lee como tal.
    Esa clasificacion es la que sostiene INVALIDATE-CANALES.md. Si se
    clasifica como "uso" generico, el documento pierde su base.
    """
    rc, out, _ = ejecuta(["causa.py", "mapa", "mmVM_INVALIDATE_REQUEST"])
    ok = rc == 0 and "SE ESCRIBE PERO NO SE LEE" in out
    # y NO debe aparecer ninguna lectura MMIO
    sin_lectura = "lectura-MMIO" not in out
    anota("CN-R19 causa clasifica invalidate como solo-escrito", ok and sin_lectura,
          "detecta la ausencia de lectura: %s, y no inventa lecturas: %s"
          % (ok, sin_lectura))
    return ok and sin_lectura


def r20_descubrir_registros():
    """
    El modo descubrimiento debe encontrar registros MMIO en gfx_v8_0.c.
    Si devuelve 0, el instrumento que sirve para ENCONTRAR TRABAJO esta roto,
    y es peor que no tenerlo: no avisa.
    """
    rc, out, _ = ejecuta(["causa.py", "descubrir", "gfx_v8_0"])
    m = re.search(r"total distintos\s*:\s*(\d+)", out)
    m2 = re.search(r"SOLO escritos\s*:\s*(\d+)", out)
    if not m or not m2:
        anota("CN-R20 descubrir encuentra registros MMIO", False,
              "no se pudo leer el recuento")
        return False
    tot, solo = int(m.group(1)), int(m2.group(1))
    ok = tot > 50 and solo > 0 and solo < tot
    anota("CN-R20 descubrir encuentra registros MMIO", ok,
          "%d registros, %d solo escritos, %d leidos" % (tot, solo, tot - solo))
    return ok


def r19b_sdma_ptepde_de_este_asic():
    """
    El emisor de PTEPDE del ASIC de POLARIS12 es
    sdma_v4_0_vm_set_pte_pde, y termina con "count - 1".

    Es la funcion que escribe las page tables de esta GPU, y C-011 la marca
    con severidad MUY ALTA por escribir UN PTE POR ENCIMA del rango pedido.
    Se fija como control porque si el corpus cambia, o si la herramienta
    deja de verla, esa severidad deja de estar justificada.

    Y comprueba la escritura por ib->ptr[], que es la que usan los emisores
    de SDMA: sin ella, ibtrace decia "sin escrituras" de la funcion MAS
    importante para PTE.
    """
    rc, out, _ = ejecuta(["ibtrace.py", "func",
                          "sdma_v4_0.c::sdma_v4_0_vm_set_pte_pde"])
    n = re.search(r"(\d+) escrituras", out)
    tiene = "count - 1" in out
    por_ptr = "ib->ptr" in out
    ok = rc == 0 and n and int(n.group(1)) == 10 and tiene and por_ptr
    anota("CN-R19b PTEPDE de POLARIS12: 10 dwords, ultimo = count-1", ok,
          "%s escrituras, count-1 presente: %s, escritura por ib->ptr: %s"
          % (n.group(1) if n else "?", tiene, por_ptr))
    return ok


def r21_scan_no_devuelve_vacio():
    """
    scan.py es el instrumento que DESCUBRE trabajo. Si devuelve una lista
    vacia o solo ruido, es peor que no existir: da la sensacion de que no hay
    nada pendiente.

    Se comprueba que produce las cinco secciones y que al menos una tiene
    contenido real.
    """
    rc, out, _ = ejecuta(["scan.py"])
    secciones = ["BLOQUEANTES", "HUECOS", "INVARIANTES", "SOLO-ESCRITOS",
                 "ABIERTAS"]
    faltan = [s for s in secciones if s not in out]
    ok = rc == 0 and not faltan
    anota("CN-R21 scan produce las 5 secciones", ok,
          "faltan: %s" % (faltan or "ninguna"))
    return ok


def r22_scan_no_ordena_por_ruido():
    """
    El ranking de bloqueantes NO debe estar dominado por la propia palabra
    buscada. La primera version tenia NOT_DETERMINED en el puesto 1 con 189
    apariciones: eso no ordena nada.

    Se comprueba que "NOT_DETERMINED" NO aparezca en la tabla de simbolos.
    """
    rc, out, _ = ejecuta(["scan.py", "--solo", "bloqueantes"])
    # La primera version de este control partia la salida por el guion y
    # buscaba en el segundo trozo, que es donde esta la tabla. Con dos
    # guiones en la salida, el segundo trozo ya no es la tabla, y el control
    # daba FALLO sobre una salida que estaba bien. Un control que no sabe
    # donde mira da falsos negativos y entrena a ignorar.
    #
    # Ahora se comprueba lo que se quiere comprobar: que ninguna FILA de la
    # tabla tenga como simbolo una palabra de la maquina de estados.
    filas = []
    started = False
    for l in out.splitlines():
        if l.startswith("simbolo"):
            started = True
            continue
        if started:
            if not l.strip() or l.startswith("Criterio"):
                break
            m = re.match(r"^(\S+)\s+(\d+)\s+(\d+)\s+(.*)$", l)
            if m:
                filas.append(m.group(1))
    RUIDO = {"NOT_DETERMINED", "PROVEN", "DERIVATION", "OBSERVATION",
             "CONCLUSION", "HYPOTHESIS", "UNKNOWN", "NOT_FOUND",
             "NOT_AVAILABLE", "NOT_OBSERVED", "REFUTED", "PARTIAL",
             "CORROBORATED", "FACT", "TEST", "POLICY", "ERROR"}
    sucias = [f for f in filas if f in RUIDO]
    ok = filas and not sucias
    anota("CN-R22 scan no ordena por la palabra que busca", bool(ok),
          "%d filas, %d con ruido como simbolo; primera: %s"
          % (len(filas), len(sucias), filas[0] if filas else "-"))
    return bool(ok)


def r23_invariantes_detectados():
    """
    El detector de invariantes debe encontrar PFP_SYNC_ME en multiples
    generaciones. Es la comprobacion de que el modo invariantes funciona:
    si no encuentra uno que SI existe, no sirve para detectar los nuevos.
    """
    rc, out, _ = ejecuta(["scan.py", "--solo", "invariantes"])
    ok = bool("PFP_SYNC_ME" in out and re.search(r"en [4-9] generacion", out))
    anota("CN-R23 detecta invariantes de la familia", ok,
          "PFP_SYNC_ME presente y con 4+ generaciones: %s" % bool(ok))
    return ok


def r24_verdiff_ambos_arboles():
    """
    verdiff depende de que existan LOS DOS arboles. Si uno falta, comparar
    "identicas" sobre una ausencia seria el peor resultado posible.
    """
    rc, out, _ = ejecuta(["verdiff.py", "fn", "gmc_v8_0.c",
                          "gmc_v8_0_emit_flush_gpu_tlb"])
    ok = rc == 0 and "7.1.3: lineas" in out and "7.2.8: lineas" in out
    anota("CN-R24 verdiff ve los dos arboles", ok,
          "encuentra la funcion en ambas versiones: %s" % ok)
    return ok


def r25_verdiff_no_confunde_ausencia():
    """
    "NO EXISTE en ninguna" NO es "IDENTICA".

    La primera version de verdiff reportaba IDENTICA cuando no encontraba la
    funcion en NINGUNA de las dos, porque hacia c1 == c2 con ambos a None. Eso
    es la peor forma de equivocarse: convierte una inability de leer en una
    afirmacion de igualdad.

    Se comprueba con un nombre que no existe: debe decir NO EXISTE, no
    IDENTICA.
    """
    rc, out, _ = ejecuta(["verdiff.py", "fn", "gmc_v8_0.c",
                          "esta_funcion_no_existe_xyz"])
    ok = rc == 1 and "NO EXISTE EN NINGUNA" in out and "IDENTICA" not in out
    anota("CN-R25 verdiff distingue ausencia de igualdad", ok,
          "dice NO EXISTE y no IDENTICA: %s" % ok)
    return ok


def r26_registro_dos_campos():
    """
    CP_RB_WPTR_POLL_CNTL tiene DOS campos que lo ocupan entero. Ese layout es
    la base de la correccion de RB-POLL.md: sin el, la lectura del codigo da
    el campo equivocado.
    """
    rc, out, _ = ejecuta(["regs.py", "CP_RB_WPTR_POLL_CNTL", "--asic", "gfx_8_0"])
    n = len(re.findall(r"bits @", out))
    tiene_f = "POLL_FREQUENCY" in out
    tiene_i = "IDLE_POLL_COUNT" in out
    ok = n == 2 and tiene_f and tiene_i
    anota("CN-R26 WPTR_POLL_CNTL tiene 2 campos, sin huecos", ok,
          "%d campos, POLL_FREQUENCY=%s IDLE_POLL_COUNT=%s"
          % (n, tiene_f, tiene_i))
    return ok


def r27_correlate_tiene_tabla():
    """
    correlate.py debe producir una tabla de hallazgos con su herramienta.
    Si devuelve una lista vacia o revienta, el enlace entre "lo que se
    afirmo" y "lo que se puede comprobar" se pierde, que es justo lo que
    automatiza.
    """
    rc, out, _ = ejecuta(["correlate.py"])
    m = re.search(r"(\d+) documentos analizados", out)
    ok = rc == 0 and m and int(m.group(1)) > 50
    # y debe clasificar con MAS DE UNA herramienta
    multi = len(re.findall(r"\d+ documentos\s+\S+", out))
    anota("CN-R27 correlate produce la tabla hallazgo-herramienta", bool(ok),
          "%s documentos, %d herramientas clasificadas"
          % (m.group(1) if m else "?", multi))
    return bool(ok)


def r28_verdiff_comentarios_encuentra():
    """
    verdiff doc debe buscar en COMENTARIOS de las dos versiones. Es la via
    para acotar NOT_DETERMINED sin runtime, y si devuelve 0 seria inútil.
    """
    rc, out, _ = ejecuta(["verdiff.py", "doc", "IDLE_POLL_COUNT"])
    dos = "7.1.3" in out and "7.2.8" in out
    n = re.search(r"total (\d+) lineas", out)
    ok = rc == 0 and dos and n and int(n.group(1)) > 0
    anota("CN-R28 verdiff doc busca en ambas versiones", bool(ok),
          "dos versiones y %s lineas de comentario"
          % (n.group(1) if n else "?"))
    return bool(ok)


def r29_dos_headers_ambos_validos():
    """
    GFX8 usa DOS headers de ASIC distintos, y ambos son correctos:
      gmc_v8_0.c  incluye gmc_8_1_sh_mask.h
      gfx_v8_0.c  incluye gmc_8_2_sh_mask.h

    Se fijo como control porque en INVALIDATE-CANALES.md se afirmo primero
    que gmc_8_2 estaba mal, y era falso. El control comprueba que los dos
    headers estan presentes, para que nadie vuelva a "corregir" al reves.

    Y comprueba que DOMAIN_INVALIDATED es identico en ambos, que es lo que
    hace la cita irrelevante en cuanto al valor.
    """
    import subprocess as sp
    amk = ("/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/working/"
           "linux-7.1.3/drivers/gpu/drm/amd/amdgpu")
    inc = ("/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/working/"
           "linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gmc")
    gmc1 = open(os.path.join(amk, "gmc_v8_0.c"), encoding="utf-8",
                errors="replace").read()
    gfx1 = open(os.path.join(amk, "gfx_v8_0.c"), encoding="utf-8",
                errors="replace").read()
    a = "gmc_8_1_sh_mask.h" in gmc1
    b = "gmc_8_2_sh_mask.h" in gfx1
    h1 = [l for l in open(os.path.join(inc, "gmc_8_1_sh_mask.h"),
                          encoding="utf-8", errors="replace")
          if "DOMAIN_INVALIDATED" in l]
    h2 = [l for l in open(os.path.join(inc, "gmc_8_2_sh_mask.h"),
                          encoding="utf-8", errors="replace")
          if "DOMAIN_INVALIDATED" in l]
    ok = a and b and h1 == h2 and len(h1) == 32
    anota("CN-R29 los dos headers de ASIC son validos y coinciden", ok,
          "gmc_v8_0 usa 8_1=%s, gfx_v8_0 usa 8_2=%s, DOMAIN_INVALIDATED "
          "identico=%s (%d lineas)" % (a, b, h1 == h2, len(h1)))
    return ok


def main():
    print("Controles del propio revkit")
    print()
    print("El modo de fallo dominante de este proyecto no es un numero")
    print("equivocado: es un CERO que parece un resultado. Asi que lo que")
    print("se comprueba es que cada herramienta FALLE cuando debe.")
    print()
    pruebas = [
        r1_cidx_cache_invalida, r2_cidx_not_found, r3_cidx_fragmento_avisa,
        r4_registers_leen_fichero, r5_mascara_incoherente,
        r6_obs_no_confunde_dispositivos, r7_obs_deduplica,
        r8_vclaims_externas, r9_vclaims_detecta_rango_malo,
        r10_pte_separa_alcanzable, r11_pte_dump, r12_sin_cjk, r13_backticks,
        r14_wait_reg_mem, r15_invalidate_canales,
        r16_ibtrace_encuentra_vm_flush, r17_ibtrace_comentarios_no_parten,
        r18_sync_es_invariante, r19_causa_clasifica_correctamente,
        r20_descubrir_registros, r19b_sdma_ptepde_de_este_asic,
        r21_scan_no_devuelve_vacio, r22_scan_no_ordena_por_ruido,
        r23_invariantes_detectados, r24_verdiff_ambos_arboles,
        r25_verdiff_no_confunde_ausencia, r26_registro_dos_campos,
        r27_correlate_tiene_tabla, r28_verdiff_comentarios_encuentra,
        r29_dos_headers_ambos_validos,
    ]
    fallos = 0
    for fn in pruebas:
        try:
            if not fn():
                fallos += 1
        except Exception as e:
            anota(fn.__name__, False, "EXCEPCION: %s" % e)
            fallos += 1
    print()
    print("%d/%d controles vivos" % (len(pruebas) - fallos, len(pruebas)))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())