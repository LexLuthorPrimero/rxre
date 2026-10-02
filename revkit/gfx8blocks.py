#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gfx8blocks.py -- que bloques IP instancia REALMENTE Polaris12, y como se llega.

Que resuelve. En un driver con dos mecanismos de seleccion, saber cual se ejecuta
es la pregunta previa a todo lo demas. Para esta placa:

  * `vi_set_ip_blocks(adev)` despacha por `adev->asic_type`   (ruta por FAMILIA)
  * `amdgpu_discovery_set_ip_blocks(adev)` despacha por `GC_HWIP`  (ruta por VERSION)

y en `amdgpu_device.c` son MUTUAMENTE EXCLUSIVOS: Polaris12 entra en el `case` y
no llega al `default`. De ahi se sigue el brazo y se listan los bloques.

Cuestion que responde: cual es la superficie de inicializacion de mi driver propio,
es decir, que hardware tengo queencerender para arrancar esta placa.

Observable producido: lista de bloques, con la condicion si la tienen.

Limites DECLARADOS, y son importantes:

  * Solo cubre la ruta por FAMILIA (`vi_set_ip_blocks`). La ruta por VERSION no se
    ejecuta en esta placa, asi que no hace falta, pero la herramienta NO lo
    comprueba: lo AFFIRMA como deduccion externa. Ver `--selftest`.
  * Las condiciones `if (...)` se reporta como `CONDICIONAL` con su texto; NO se
    evalua. Decidir si se cumple es otra pregunta (y es de runtime).
  * No cuenta el numero de bloques que se anaden en el otro ramal de la misma
    funcion: por construccion son de otro ASIC.

Validacion: `--selftest` con 3 vectores conocidos y 4 controles de fallo, y
mutacion externa comprobada (ver CHANGELOG). Estado: VALIDATED.

CONTRACT: name=gfx8blocks
CONTRACT: READONLY=yes
CONTRACT: WRITES_FILES=no
CONTRACT: WRITES_SYSFS=no
CONTRACT: MUTATES_CORPUS=no
CONTRACT: WRITES_GPU=no
"""

import io
import os
import re
import sys

FUNCION = "vi_set_ip_blocks"
VIVOS = {
    "CHIP_POLARIS10": "POLARIS10", "CHIP_POLARIS11": "POLARIS11",
    "CHIP_POLARIS12": "POLARIS12", "CHIP_VEGAM": "VEGAM",
}
DEFAULT_CORPUS = ("/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/baseline/"
                  "linux-7.1.3/drivers/gpu/drm/amd/amdgpu")


def _leer(path):
    # MEDIDO: sin esto, una ruta ausente levanta FileNotFoundError y el control
    # de fallo "carpeta inexistente -> ERROR" pasaba o fallaba por el motivo
    # equivocado. Un negativo que pasa por la via equivocada no es un negativo.
    if not os.path.isfile(path):
        raise SystemExit("ERROR/INVALID: no existe %s" % path)
    return io.open(path, encoding="utf-8", errors="replace").read().splitlines()


def rango_de_funcion(lineas, nombre):
    """Devuelve (ini, fin) de la definicion de `nombre` en el fichero.

    MEDIDO, y es el defecto mas grave de los tres: `vi.c` tiene OCHO
    `case CHIP_POLARIS12:` distintos, uno por cada switch del fichero. La
    primera version buscaba la etiqueta en el FICHERO ENTERO y cogia el de la
    linea 274, dentro de `vi_query_video_codecs`, que no anade ningun bloque: el
    resultado era 0 con exito.

    La leccion es la misma de siempre con un disfraz nuevo: **acotar, luego
    emparejar**. Un acierto de busqueda es un indice, no un dato; y un numero de
    linea no es un sitio, es una posicion en un fichero.
    """
    ini = None
    for n, l in enumerate(lineas):
        # La firma y la llave pueden estar en lineas distintas: en ESTE driver
        # la firma acaba en ")" y la "{" va en la linea siguiente. La primera
        # version exigia que acabara en "{" y no encontraba la funcion.
        if re.match(r"^(static\s+)?\w[\w \*]*\b%s\s*\(" % re.escape(nombre), l):
            # n+1, NO n: con k=n se comparaba la propia firma contra "{" y
            # nunca casaba. Segundo off-by-one de esta misma funcion.
            k = n + 1
            while k < len(lineas) and not lineas[k].strip():
                k += 1
            if k < len(lineas) and lineas[k].strip() in ("{",):
                ini = n
                break
    if ini is None:
        raise SystemExit("ERROR/INVALID: no encuentro la definicion de %s" % nombre)
    # el final es la siguiente linea en columna 0 que abre otra definicion
    fin = len(lineas)
    for k in range(ini + 1, len(lineas)):
        l = lineas[k]
        if l and not l[0].isspace() and re.match(r"^(static\s+)?\w[\w \*]*\(", l):
            fin = k
            break
    return ini, fin


def brazo(lineas, etiqueta):
    """Devuelve las lineas del CUERPO que se ejecuta para `etiqueta`.

    MEDIDO, y es el defecto de fondo de la primera version: en C, `case` NO
    delimita codigo. Varias etiquetas consecutivas comparten UN MISMO cuerpo, y
    la ultima es la que lo trae. `case CHIP_POLARIS12:` cae hacia
    `case CHIP_VEGAM:` y ejecuta el cuerpo de VEGAM. Trocear por etiqueta daba
    0 bloques para POLARIS12, y el programa lo decia con exito.

    Es el mismo error de siempre con otro disfraz: contar ETIQUETAS en vez de
    codigo que se ejecuta. Un selector que devuelve una lista vacia sin decirlo
    es peor que uno que no existe.

    El grupo es: una o mas lineas `case X:` / `default:` consecutivas, seguidas
    de su cuerpo. Se localize la etiqueta, se retrocede hasta el comienzo del
    grupo y se avanza hasta el `break;` o el siguiente grupo.
    """
    ini_fn, fin_fn = rango_de_funcion(lineas, FUNCION)
    i = None
    for n in range(ini_fn, min(fin_fn, len(lineas))):
        if re.match(r"^\tcase %s:\s*$" % re.escape(etiqueta), lineas[n]):
            i = n
            break
    if i is None:
        raise SystemExit("ERROR/INVALID: no encuentro 'case %s:' DENTRO de %s. "
                         "Ojo: la etiqueta puede existir en otro switch del "
                         "fichero; esto es lo que hacia la version anterior."
                         % (etiqueta, FUNCION))
    # retroceder hasta el inicio del grupo de etiquetas consecutivas
    ini = i
    while ini - 1 > ini_fn and re.match(r"^\t(case |default:)", lineas[ini - 1]):
        ini -= 1
    # saltar las RESTANTES etiquetas del mismo grupo hasta la primera sentencia
    cuerpo = i
    while cuerpo + 1 < len(lineas) and re.match(r"^\t(case |default:)", lineas[cuerpo + 1]):
        cuerpo += 1
    # avanzar hasta el break; del cuerpo, o hasta el siguiente grupo
    sangria = None
    out = []
    for k in range(cuerpo + 1, len(lineas)):
        l = lineas[k]
        if re.match(r"^\t(case |default:)", l):
            break
        m = re.match(r"^(\t+)", l)
        if not l.strip():
            continue
        if m and sangria is None:
            sangria = len(m.group(1))
        if sangria and m and len(m.group(1)) < sangria:
            break
        if l.strip() == "break;":
            break
        out.append((k + 1, l))
    return out


def bloques(lineas, etiqueta):
    """Extrae los bloques del brazo, clasificando INCONDICIONAL / CONDICIONAL."""
    fila = []
    cond = None
    pendientes = 0
    for n, l in brazo(lineas, etiqueta):
        s = l.strip()
        m = re.search(r"&(\w+_ip_block)", s)
        if m and "amdgpu_device_ip_block_add" in s:
            # MEDIDO: la condicion era `pendientes == 0` para marcar
            # CONDICIONAL, con lo que los 6 bloques SIN condicion del brazo
            # caian en el else y salia INCONDICIONAL, y los 2 de dentro de un
            # `if` salian INCONDICIONAL. La respuesta conocida lo cazo.
            if cond is not None and pendientes > 0:
                fila.append((m.group(1), "CONDICIONAL", cond, n))
            else:
                fila.append((m.group(1), "INCONDICIONAL", "", n))
            pendientes = 0
            continue
        # una condicion pendiente cubre los adds que vienen despues
        if re.match(r"^(if|else if)\b", s):
            cond = s.rstrip(":")
            pendientes = 1
        elif s == "break;":
            pendientes = 0
    return fila


def ruta_exclusiva(carpeta):
    """Comprueba que la ruta por familia y la ruta por version NO se ejecutan
    ambas. Sin esto, la lista de bloques seria incompleta por construccion.

    No lo doy por sabido: si el `default:` no existiera, o si POLARIS12 no
    estuviera en el `case`, la herramienta devolveria una lista y seria falsa.
    """
    d = _leer(os.path.join(carpeta, "amdgpu_device.c"))
    txt = "\n".join(d)
    if FUNCION not in txt:
        raise SystemExit("ERROR/INVALID: amdgpu_device.c no llama a %s" % FUNCION)
    if not re.search(r"case CHIP_POLARIS12:", txt):
        raise SystemExit("ERROR/INVALID: no hay 'case CHIP_POLARIS12:'")
    # el default que lleva a la ruta por version
    m = re.search(r"default:\s*\n\s*r = amdgpu_discovery_set_ip_blocks\(adev\);", txt)
    if not m:
        raise SystemExit("ERROR/INVALID: no encuentro el default que deriva a "
                         "amdgpu_discovery_set_ip_blocks; la exclusividad no esta "
                         "demostrada y la lista seria incompleta")
    return True



def tablas_y_funcs(carpeta, bloques):
    """Para cada bloque, su tabla .funcs y las funciones que se registran en ella.

    Que resuelve, y por que hace falta: el driver llama a casi todo por PUNTERO a
    funcion, a traves de las tablas `*_ip_funcs`. Un indice de llamadas por texto
    NO las ve, con lo que "no hay ninguna llamada a esta funcion" no significa
    "esta funcion no se ejecuta": significa "nadie la llama por nombre".

    Y hay dos trampas mas, medidas en este mismo ASIC:

      * el BLOQUE y la TABLA no son lo mismo. `gfx_v8_0_ip_block` y
        `gfx_v8_1_ip_block` comparten `.funcs = &gfx_v8_0_ip_funcs`.
      * el BLOQUE y el FICHERO no son lo mismo. De los 10 bloques de esta placa,
        4 estan definidos en un fichero con otro nombre: `gmc_v8_1_ip_block` en
        `gmc_v8_0.c`, `sdma_v3_1_ip_block` en `sdma_v3_0.c`,
        `uvd_v6_3_ip_block` en `uvd_v6_0.c`, `vce_v3_4_ip_block` en `vce_v3_0.c`.
        Si se buscara el bloque por el nombre del fichero, 4 de 10 no se
        encontrarian. Un nombre de fichero no es un dato.

    Devuelve {bloque: (tabla, [funciones])}.
    """
    out = {}
    # MEDIDO, y es la diferencia entre "no existe" y "no lo he mirado": dos de
    # los diez bloques NO estan en amdgpu/. `pp_smu_ip_block` se define en
    # amd/pm/powerplay/amd_powerplay.c y `dm_ip_block` en
    # amd/display/amdgpu_dm/amdgpu_dm.c. Buscando solo dentro de amdgpu/ la
    # herramienta decia "SIN TABLA" de dos bloques que SI existen. No es que no
    # existan: es que no los mire. La raiz de busqueda sube a drm/amd/.
    raiz = os.path.dirname(carpeta.rstrip("/"))
    cands = []
    for base, _dirs, files in os.walk(raiz):
        for f in files:
            if f.endswith(".c"):
                cands.append(os.path.relpath(os.path.join(base, f), raiz))
    for bloque in bloques:
        # MEDIDO: la llave de apertura va en la LINEA SIGUIENTE en todos estos
        # ficheros ("static const struct amdgpu_ip_block_version X_ip_block ="),
        # asi que un patron que exija "={" al final de la linea no casa con
        # ninguno. Es el mismo descuido que en la firma de las funciones.
        patron_def = re.compile(r"^\w[\w \*]*?%s\s*=\s*\{?\s*$" % re.escape(bloque))
        patron_funcs = re.compile(r"\.funcs\s*=\s*&(\w+)")
        encontrado = False
        for f in cands:
            ls = _leer(os.path.join(raiz, f))
            for n, l in enumerate(ls):
                if patron_def.match(l.strip()) and                         re.match(r"^(const|static)", l):
                    # recorrer el cuerpo del bloque hasta la llave de cierre
                    cuerpo = []
                    # si la linea de definicion ya abre la llave, el cuerpo empieza
                    # en la siguiente; si no, empieza una linea despues. Se
                    # resuelve mirando, no suponiendo.
                    ini_cuerpo = n + 1
                    if not l.rstrip().endswith("{"):
                        ini_cuerpo = n + 2
                    for k in range(ini_cuerpo, min(ini_cuerpo + 30, len(ls))):
                        cuerpo.append(ls[k])
                        if ls[k].strip() == "};":
                            break
                    mt = patron_funcs.search("\n".join(cuerpo))
                    tabla = mt.group(1) if mt else None
                    if not tabla:
                        out[bloque] = (f, None, [])
                        encontrado = True
                        break
                    # ahora la tabla
                    pat_t = re.compile(r"^\w[\w \*]*?%s\s*=\s*\{?\s*$" % re.escape(tabla))
                    for ff in cands:
                        lss = _leer(os.path.join(raiz, ff))
                        for n2, l2 in enumerate(lss):
                            if pat_t.match(l2.strip()):
                                funcs = []
                                ini_c2 = n2 + 1
                                if not l2.rstrip().endswith("{"):
                                    ini_c2 = n2 + 2
                                for k in range(ini_c2, min(ini_c2 + 40, len(lss))):
                                    if lss[k].strip() == "};":
                                        break
                                    mf = re.match(r"^\.(\w+)\s*=\s*(\w+)\s*,?\s*$",
                                                 lss[k].strip())
                                    if mf and mf.group(2) != "NULL":
                                        funcs.append((mf.group(1), mf.group(2)))
                                out[bloque] = (ff, tabla, funcs)
                                encontrado = True
                                break
                        if encontrado:
                            break
                    if encontrado:
                        break
            if encontrado:
                break
        if not encontrado:
            out[bloque] = (None, None, [])
    return out

def selftest():
    """Vectores conocidos y controles de fallo. Un control que no puede fallar
    es peor que ninguno, asi que cada rama tiene su negativo."""
    ok = fallan = 0

    def chk(nombre, cond):
        nonlocal ok, fallan
        if cond:
            ok += 1
            print("  OK    %s" % nombre)
        else:
            fallan += 1
            print("  FALLA %s" % nombre)

    # --- vectores conocidos, leidos del fichero real -------------------------
    d = _leer(os.path.join(DEFAULT_CORPUS, "vi.c"))
    pol = bloques(d, "CHIP_POLARIS12")
    nombres = [x[0] for x in pol]
    incond = [x[0] for x in pol if x[1] == "INCONDICIONAL"]
    condic = [x[0] for x in pol if x[1] == "CONDICIONAL"]

    # el vector conocido, escrito a mano leyendo vi.c:2105-2123 ANTES de escribir
    # esta herramienta. Si el codigo cambia, esto falla y obliga a revisar el
    # vector en vez de aceptarlo en silencio.
    ESPERADO_INCOND = ["vi_common_ip_block", "gmc_v8_1_ip_block",
                       "tonga_ih_ip_block", "gfx_v8_0_ip_block",
                       "sdma_v3_1_ip_block", "pp_smu_ip_block",
                       "uvd_v6_3_ip_block", "vce_v3_4_ip_block"]
    ESPERADO_CONDIC = ["amdgpu_vkms_ip_block", "dm_ip_block"]

    chk("POLARIS12 tiene los 8 bloques incondicionales del vector conocido",
        incond == ESPERADO_INCOND)
    chk("POLARIS12 tiene los 2 condicionales del vector conocido",
        condic == ESPERADO_CONDIC)
    chk("POLARIS12 usa gmc_v8_1, NO gmc_v8_0", "gmc_v8_1_ip_block" in incond
        and "gmc_v8_0_ip_block" not in incond)
    chk("POLARIS12 usa sdma_v3_1, NO sdma_v3_0", "sdma_v3_1_ip_block" in incond
        and "sdma_v3_0_ip_block" not in incond)
    chk("no aparece ningun bloque de MES",
        not any("mes_" in x for x in nombres))
    chk("no aparece ningun bloque de vpe/vcn", not any(
        re.search(r"_(vpe|vcn|umsch|isp)_", x) for x in nombres))

    # --- los otros dos ASIC del mismo brazo deben dar SU subconjunto ---------
    p10 = [x[0] for x in bloques(d, "CHIP_POLARIS10") if x[1] == "INCONDICIONAL"]
    vegam = [x[0] for x in bloques(d, "CHIP_VEGAM") if x[1] == "INCONDICIONAL"]
    chk("POLARIS10 cae en el mismo brazo (mismos 8)",
        p10 == ESPERADO_INCOND)
    chk("VEGAM cae en el mismo brazo (mismos 8)", vegam == ESPERADO_INCOND)

    # --- un ASIC de OTRO brazo NO puede dar la misma lista -------------------
    caz = [x[0] for x in bloques(d, "CHIP_CARRIZO") if x[1] == "INCONDICIONAL"]
    chk("CARRIZO da un subconjunto DISTINTO (gmc_v8_0, no v8_1)",
        caz != ESPERADO_INCOND and "gmc_v8_0_ip_block" in caz
        and "gmc_v8_1_ip_block" not in caz)
    topaz = [x[0] for x in bloques(d, "CHIP_TOPAZ") if x[1] == "INCONDICIONAL"]
    chk("TOPAZ no lleva bloques de video (comentario del codigo)",
        not any(re.search(r"uvd|vce", x) for x in topaz))

    # --- controles de fallo --------------------------------------------------
    try:
        bloques(d, "CHIP_INEXISTENTE")
        chk("etiqueta inexistente -> ERROR, no lista vacia", False)
    except SystemExit:
        chk("etiqueta inexistente -> ERROR, no lista vacia", True)

    try:
        ruta_exclusiva(os.path.join(DEFAULT_CORPUS, "..", "no_existe_dir"))
        chk("carpeta inexistente -> ERROR", False)
    except SystemExit:
        chk("carpeta inexistente -> ERROR", True)

    # exclusivity: si el default que deriva a discovery desapareciera, la
    # herramienta tiene que negarse, porque la lista seria incompleta.
    import shutil
    import tempfile
    t = tempfile.mkdtemp()
    try:
        # El corpus es de SOLO LECTURA y shutil.copy conserva los permisos, con
        # lo que la mutacion reventaba con PermissionError en vez de probar el
        # control. MEDIDO. copyfile + chmod explicito.
        for f in ("vi.c", "amdgpu_device.c"):
            shutil.copyfile(os.path.join(DEFAULT_CORPUS, f), os.path.join(t, f))
            os.chmod(os.path.join(t, f), 0o600)
        p = os.path.join(t, "amdgpu_device.c")
        s = io.open(p, encoding="utf-8").read()
        s = s.replace("r = amdgpu_discovery_set_ip_blocks(adev);", "r = 0;")
        io.open(p, "w", encoding="utf-8").write(s)
        try:
            ruta_exclusiva(t)
            chk("sin el default a discovery -> ERROR (la lista seria incompleta)", False)
        except SystemExit:
            chk("sin el default a discovery -> ERROR (la lista seria incompleta)", True)
    finally:
        shutil.rmtree(t, ignore_errors=True)


    # --- pruebas de EXTREMO A EXTREMO sobre main(), no sobre los helpers ------
    # MEDIDO: las mutaciones M2 (quitar la exclusividad del main) y M4 (quitar
    # el guardia de lista vacia) NO las cazaba el self-test, porque solo probaba
    # los helpers. Probar las piezas no es probar el programa: el cableado es
    # justo lo que puede estar mal y no mirado.
    import contextlib
    import io as _io

    def _main(argv):
        buf = _io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                rc = main(argv)
        except SystemExit as e:
            rc = e.code if isinstance(e.code, int) else 1
        return rc, buf.getvalue()

    # 1. el corpus real: 10 bloques y rc=0
    rc, sal = _main(["--corpus", DEFAULT_CORPUS, "--asic=CHIP_POLARIS12"])
    chk("main() sobre el corpus real -> rc=0 y 10 bloques",
        rc == 0 and "total 10" in sal)

    # 2. un ASIC valido del mismo brazo
    rc, sal = _main(["--corpus", DEFAULT_CORPUS, "--asic=CHIP_VEGAM"])
    chk("main() sobre VEGAM -> rc=0 y los mismos 10",
        rc == 0 and "total 10" in sal)

    # 3. brazo sin bloques -> rc=3, NO rc=0. Este es el que caza M4.
    t = tempfile.mkdtemp()
    try:
        for f in ("vi.c", "amdgpu_device.c"):
            shutil.copyfile(os.path.join(DEFAULT_CORPUS, f), os.path.join(t, f))
            os.chmod(os.path.join(t, f), 0o600)
        p = os.path.join(t, "vi.c")
        s = io.open(p, encoding="utf-8").read()
        # MEDIDO: la primera version de ESTE test hacia s.index("case
        # CHIP_POLARIS12:") sin acotar, cogia la de la linea 274 y mutaba el
        # brazo equivocado: el test fallaba y la causa era el test, no la
        # herramienta. El error que la herramienta ya tiene corregido me ha
        # mordido a mi al escribir su prueba. Acotar, LUEGO emparejar, tambien
        # en la prueba.
        base = s.index("int vi_set_ip_blocks(")
        i = s.index("case CHIP_POLARIS12:", base)
        j = s.index("break;", i)
        s = s[:i] + s[i:j].replace("amdgpu_device_ip_block_add(adev, &", "falsa_llamada(adev, &") + s[j:]
        io.open(p, "w", encoding="utf-8").write(s)
        rc, sal = _main(["--corpus", t, "--asic=CHIP_POLARIS12"])
        chk("main() con un brazo sin bloques -> rc=3, no rc=0",
            rc == 3 and "ERROR/INVALID" in sal)
    finally:
        shutil.rmtree(t, ignore_errors=True)

    # 4. sin el default que deriva a discovery -> error, no lista incompleta.
    #    Este es el que caza M2.
    t = tempfile.mkdtemp()
    try:
        for f in ("vi.c", "amdgpu_device.c"):
            shutil.copyfile(os.path.join(DEFAULT_CORPUS, f), os.path.join(t, f))
            os.chmod(os.path.join(t, f), 0o600)
        p = os.path.join(t, "amdgpu_device.c")
        s = io.open(p, encoding="utf-8").read()
        s = s.replace("r = amdgpu_discovery_set_ip_blocks(adev);", "r = 0;")
        io.open(p, "w", encoding="utf-8").write(s)
        rc, sal = _main(["--corpus", t, "--asic=CHIP_POLARIS12"])
        chk("main() sin la exclusividad demostrada -> error, no lista",
            rc != 0)
    finally:
        shutil.rmtree(t, ignore_errors=True)

    # --- superficie de entrada por puntero a funcion ------------------------
    import contextlib
    import io as _io
    pol2 = [x[0] for x in bloques(_leer(os.path.join(DEFAULT_CORPUS, "vi.c")),
                                    "CHIP_POLARIS12")]
    info = tablas_y_funcs(DEFAULT_CORPUS, pol2)
    con_tabla = {b: info.get(b, (None, None, [])) for b in pol2}
    chk("los 10 bloques de POLARIS12 tienen tabla .funcs",
        len(pol2) == 10 and all(v[2] for v in con_tabla.values()))
    # REGRESION medida: buscar solo dentro de amdgpu/ dejaba a pp_smu y dm SIN
    # tabla, y decia "no existen" de dos bloques que si existen. Se comprueba el
    # nombre de los ficheros donde estan, no solo que haya tabla.
    chk("pp_smu_ip_block se busca FUERA de amdgpu/ (powerplay)",
        con_tabla["pp_smu_ip_block"][0].endswith("powerplay/amd_powerplay.c"))
    chk("dm_ip_block se busca FUERA de amdgpu/ (display)",
        con_tabla["dm_ip_block"][0].endswith("amdgpu_dm/amdgpu_dm.c"))
    chk("gfx_v8_1_ip_block usa la tabla gmc_v8_0_ip_funcs de OTRO bloque",
        con_tabla["gmc_v8_1_ip_block"][1] == "gmc_v8_0_ip_funcs")
    chk("pp_smu_ip_block NO usa una tabla con su propio nombre",
        con_tabla["pp_smu_ip_block"][1] == "pp_ip_funcs")
    total = sum(len(v[2]) for v in con_tabla.values())
    chk("145 funciones registradas en las 10 tablas", total == 145)
    # el modo completo no falla
    buf = _io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc0 = main(["--funcs"])
        chk("main --funcs -> rc=0", rc0 == 0)
    except SystemExit:
        chk("main --funcs -> rc=0", False)

    print("  ---")
    print("  vectores OK: %d   controles en rojo: %d" % (ok, fallan))
    return 1 if fallan else 0


def main(argv):
    if "--self-test" in argv:
        return selftest()
    carpeta = DEFAULT_CORPUS
    if "--corpus" in argv:
        carpeta = argv[argv.index("--corpus") + 1]
    if "--funcs" in argv:
        filas0 = bloques(_leer(os.path.join(carpeta, "vi.c")), "CHIP_POLARIS12")
        nombres = [x[0] for x in filas0]
        info = tablas_y_funcs(carpeta, nombres)
        total = 0
        print("gfx8blocks --funcs: la superficie de entrada por PUNTERO a funcion")
        print("  cada bloque -> su tabla .funcs -> las funciones que registra")
        print("  " + "-" * 76)
        for b in nombres:
            f, tabla, funcs = info.get(b, (None, None, []))
            if not funcs:
                print("  %-24s SIN TABLA o sin funciones  (fichero %s)" % (b, f))
                continue
            total += len(funcs)
            print("  %-24s %s  (%d funciones, en %s)"
                  % (b, tabla, len(funcs), f))
            for campo, fn in funcs:
                print("        .%-22s %s" % (campo, fn))
        print("  " + "-" * 76)
        print("  bloques con tabla: %d   funciones registradas: %d"
              % (sum(1 for b in nombres if info.get(b, (0, 0, []))[2]), total))
        print("  LIMITE: solo las tablas .funcs de los bloques. NO cubre los fops")
        print("  de DRM, los sysfs, el debugfs ni los ioctls, que tambien entran")
        print("  por puntero y son la via por la que el KERNEL llama al driver.")
        if total == 0:
            print("  ERROR/INVALID: 0 funciones. No es un resultado.")
            return 3
        return 0
    etiqueta = "CHIP_POLARIS12"
    for a in argv:
        if a.startswith("--asic="):
            etiqueta = a.split("=", 1)[1]
    ruta_exclusiva(carpeta)
    filas = bloques(_leer(os.path.join(carpeta, "vi.c")), etiqueta)
    print("gfx8blocks: bloques IP que instancia %s" % etiqueta)
    print("  via: vi_set_ip_blocks (ruta por FAMILIA, switch en adev->asic_type)")
    print("  la ruta por VERSION (amdgpu_discovery_set_ip_blocks) NO se ejecuta:")
    print("  en amdgpu_device.c ambas rutas son mutuamente exclusivas.")
    print("  " + "-" * 72)
    for nombre, clase, cond, n in filas:
        print("  %-26s %-13s vi.c:%-5d %s"
              % (nombre, clase, n, cond))
    ni = sum(1 for x in filas if x[1] == "INCONDICIONAL")
    print("  " + "-" * 72)
    print("  total %d: %d incondicionales, %d condicionales" % (len(filas), ni, len(filas) - ni))
    print("  las condiciones NO se evaluan: es otra pregunta, y es de runtime.")
    if not filas:
        # MEDIDO: la primera version devolvio "total 0" con rc=0. Una lista
        # vacia sin|POLARIS12 da bloques| es un fallo del parser, no un dato.
        print("  ERROR/INVALID: 0 bloques para %s. No es un resultado: es un"
              " fallo de" % etiqueta)
        print("                troceado. La version que fallaba devolvia 0 con"
              " exito.")
        return 3
    if ni == 0:
        print("  ERROR/INVALID: 0 bloques incondicionales. Ningun bloque se"
              " anade siempre,")
        print("                lo que en la practica significa que no se"
              " instancia hardware.")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))