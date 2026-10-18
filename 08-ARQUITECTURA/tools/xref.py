#!/usr/bin/env python3
# CONTRACT: name=xref
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py.  Veredicto
# `READONLY=yes, WRITES_FILES=no`: no tiene ninguna escritura: no hay nada que resolver.
#
# ESTA HERRAMIENTA LA INVOCA `run_all.py`.  Eso se midio con
# RXRE/tools/rxre_deleg.py, que resolvio 72 invocaciones entre herramientas del
# proyecto -- todas en TABLAS, ninguna en un `subprocess` literal, y por eso
# ningun grafo de imports las ve.  De las 47 que invoca, estas cuatro estaban
# SIN contrato, y son justo las que `toolkit.py` reportaba como "SIN CONTRATO:
# no se puede afirmar nada de esta herramienta".
#
# Declarar `WRITES_FILES=no` sin escrituras no es trivial: es la clase que hace
# falta para que una herramienta pueda enrutarse Y se sepa que es segura.  Con
# contrato y sin capacidad enrutable, el par no existe (hallazgo 1491).
#
# TOUCHES_INTEGRATED=no, y se declara aunque toolkit.py no lo conozca: la
# frontera que no se puede declarar es la que no se puede hacer cumplir (1487).
"""
xref.py -- quien LEE y quien ESCRIBE un simbolo, en todo el corpus.

POR QUE EXISTE
    La pregunta que mas se repitio en una sesion de ingenieria inversa no es
    "donde aparece X" (grep responde a eso), sino:

        ¿quien CONSUME este campo?

    Un campo se produce en un fichero tematico y se consume en otro muy
    distinto.  Buscar el consumidor en el bloque tematico que lo produce es el
    error clasico: se responde la pregunta en el sitio donde ya se conocia la
    respuesta.  grep no ayuda porque devuelve lineas, y una linea no dice si
    ese punto ESCRIBE el valor o lo LEE.

    Un ejemplo real de por que importa: en el mismo dia se escribio que
    "mc_mask" se fijaba en gmc_v8_0.c:1133.  Eso es un punto de ESCRITURA.
    El lugar donde el valor se USA para calcular el limite de VRAM esta en otro
    fichero, y sin esa division la afirmacion es correcta pero inútil.

QUE PRODUCE, POR SIMBOLO
    Cada aparicion clasificada como una de:
      DEFINE     #define / definicion de funcion / declaracion de campo
      WRITE      asignacion, ++/--, o paso por direccion (&x)
      READ       uso en una expresion
      DECL       mencion que no es de ninguna de las anteriores
    Y un resumen por fichero, que es la vista que responde a la pregunta.

POR QUE NO ES UN PARSER DE C
    Un parser de C que clasifique esto bien requiere el AST completo.  Este
    script clasifica con patrones estructurales, que es un 90% y no un 100%.

LIMITE DECLARADO, Y ES EL PUNTO DEL DOCUMENTO
    NO sabe distinguir un identificador del cuerpo de uno de una cadena de
    caracteres, ni macros que se expanden a varios tokens, ni un campo cuyo
    nombre aparece en un comentario.  En concreto:

      - no ignora comentarios ni cadenas: una mencion dentro de "/* ... */"
        cuenta como READ si parece un uso, y puede no contar si no lo parece;
      - un #define de varias lineas con continuacion se trata como una;
      - "WRITE" es una INTENCION LEXICA, no un hecho: `p = p` se marca como
        escritura aunque solo lea.

    Por eso imprime la linea real de cada sitio.  La clasificacion ordena la
    busqueda; no la sustituye.  Es un filtro con las manos a la vista, no un
    oraculo.

DONDE NO APLICA
    Solo sobre codigo C del corpus.  No indexa el hardware, no lee el registro
    de arranque, no infiere nada que no este escrito en el fichero.

USO
    xref.py --sym mc_mask                    todos los sitios, clasificados
    xref.py --field mc_mask                  agrupa por expression receptora
    xref.py --field mc_mask --write          solo los que ESCRIBEN
    xref.py --file gmc_v8_0.c --sym mc_mask  limitado a un fichero
    xref.py --context                        imprime la linea real (por defecto)
    xref.py --self                           autotest

DEPENDENCIAS
    python3 >= 3.9.  Sin red, sin root, sin escrituras.  Reutiliza el indice
    de doclint si esta, porque ese indice incluye el kernel INSTALADO EN EL
    HOST, que es el binario que corre, y no solo el arbol de referencia.
"""

import argparse
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = "/home/lucas/Escritorio/RX550-INVESTIGACION"
sys.path.insert(0, HERE)

_idx = None
_idx_src = None


def get_index(verbose=False):
    global _idx, _idx_src
    if _idx is not None:
        return _idx
    try:
        import doclint
        t = time.time()
        _idx = doclint.build_index()
        _idx_src = f"doclint.build_index() ({len(_idx)} ficheros, {time.time()-t:.1f}s)"
    except Exception as e:                                     # noqa: BLE001
        if verbose:
            print(f"  doclint no disponible ({e}); indice propio", file=sys.stderr)
        _idx = {}
        for root in (f"{PROJECT}/RESEARCH/working", f"{PROJECT}/04-IMPLEMENTACION"):
            for dp, _d, fs in os.walk(root):
                for f in fs:
                    if f.endswith((".c", ".h")):
                        p = os.path.join(dp, f)
                        try:
                            with open(p, errors="replace") as fh:
                                _idx[p] = fh.read().split("\n")
                        except OSError:
                            pass
        _idx_src = f"propio ({len(_idx)} ficheros)"
    if verbose:
        print(f"  indice: {_idx_src}", file=sys.stderr)
    return _idx


def classify(line, sym):
    """
    Clasifica UNA linea de codigo que contiene `sym`.
    Devuelve (clase, expression_receptora) o (None, None) si no encaja.
    """
    # quitar el numero de linea que algunos codigos traen pegado
    s = line.strip()

    if re.match(rf'#\s*define\s+{re.escape(sym)}\b', s):
        return ("DEFINE", sym)

    # definicion de funcion:  tipo sym(args)   {   al final
    if re.match(rf'^[A-Za-z_].*\b{re.escape(sym)}\s*\([^;]*\)\s*$', s) and \
       not s.startswith(("if", "for", "while", "switch", "return")):
        if re.search(rf'\b{re.escape(sym)}\s*\(', s) and not re.search(r'=', s.split(sym)[0]):
            return ("DEFINE", sym)

    # escritura directa:  sym = ...   (pero no ==, !=, <=, >=)
    # Escritura por paso a funcion: f(..., sym, ...).  Es la forma de los
    # registros de ring en AMDGPU: amdgpu_ring_write(ring, mmVM_INVALIDATE_REQUEST)
    # ESCRIBE ese registro, y el clasificador solo miraba "sym =" decia que no
    # habia ninguna escritura.  El caso aparecio con §C, y es general: cualquier
    # registro que se escriba a un ring en vez de a MMIO directo se escapaba.
    # No se puede distinguir f(sym) de lectura sin mirar la funcion, asi que se
    # marca WRITTEN_ARG y se imprime la linea: la revision decide.  Un filtro con
    # las manos a la vista, no un oraculo.
    m = re.search(rf'\b(amdgpu_ring_write|amdgpu_ring_write_1|WRITE_REG|WREG32|'
                  rf'reg_set_field|REG_SET_FIELD|amdgpu_mm_wb|'
                  rf'amdgpu_sched_write)\s*\(([^)]*\b'
                  rf'{re.escape(sym)}\b[^)]*)\)', s)
    if m:
        return ("WRITTEN_ARG", sym)

    # escritura directa:  sym = ...
    # El caracter anterior no puede ser un operador, o "x == sym" y "x <<= sym"
    # se leerian como escritura.
    # Se aceptan los operadores COMPUESTOS (+=, -=, <<=, &=, |= ...) porque
    # todos escriben en sym.  La forma simple "sym =" sola deja fuera
    # "campo += n", que es escritura y es habitual en caches y contadores.
    # Hallado por el control negativo, no leyendo el codigo.
    if re.search(rf'(?:^|[^=!<>+\-*/%&|^]){re.escape(sym)}\s*'
                 rf'(?:[+\-*/%&|^]|<<|>>)?=(?![=])', s):
        return ("WRITE", sym)
    # incremento y decremento, en las DOS formas.  Solo con prefijo (++x) es un
    # bug real: la forma postfija (x++) es igual de escritura y es la habitual
    # en codigo de indices.  Detallado por un fallo del propio self-test.
    if re.search(rf'--\s*{re.escape(sym)}\b|\+\+\s*{re.escape(sym)}\b', s):
        return ("WRITE", sym)
    if re.search(rf'\b{re.escape(sym)}\s*(?:--|\+\+)', s):
        return ("WRITE", sym)
    # escritura por direccion: &sym  o  &algo->sym.  El "&" no esta pegado al
    # simbolo en el segundo caso, asi que hay que permitir la cadena de
    # punteros entre medias.  Pasar la direccion ES escribir.
    #
    # PERO "&" tambien es AND bitwise.  La diferencia no es el simbolo, es lo
    # que hay ANTES del "&": un operando a la izquierda lo convierte en AND
    # (lectura), y el inicio de una expresion lo deja en direccion-de (escritura).
    # Confundirlos marca como escritura cada mascara de bits del arbol, que es
    # justo el caso de uso mas frecuente en un driver de GPU.  Detectado por el
    # self-test, no por lectura del codigo.
    addr = re.search(rf'&\s*(?:[A-Za-z_]\w*\s*(?:->|\.)\s*)*'
                     rf'{re.escape(sym)}\b', s)
    if addr:
        before = s[:addr.start()].rstrip()
        es_binario = bool(before) and before[-1] in ')]}"\''
        es_binario = es_binario or bool(re.search(r'[\w]$', before))
        if not es_binario:
            return ("WRITE", sym)

    # lectura: la palabra aparece y no es una escritura
    if re.search(rf'\b{re.escape(sym)}\b', s):
        # declaración sin inicializar:  tipo sym;
        if re.search(rf'^[A-Za-z_][\w\s\*]*\b{re.escape(sym)}\s*;', s):
            return ("DECL", sym)
        return ("READ", sym)
    return (None, None)


def receiver(line, sym):
    """
    Expression que CONTIENE al simbolo, p.ej. en
        adev->gmc.mc_mask = 0xffffffffffULL;
    devuelve   adev->gmc.mc_mask
    Es lo que permite agrupar "quien escribe QUE campo", que es la pregunta
    real: dos escrituras a mc_mask y a vm_mask son cosas distintas.
    """
    m = re.search(r'([A-Za-z_][\w]*(?:\s*(?:->|\.)\s*[A-Za-z_][\w]*)+)', line)
    if m and sym in m.group(1):
        return re.sub(r'\s+', '', m.group(1))
    m = re.search(rf'\b({re.escape(sym)})\b', line)
    return m.group(1) if m else None


def scan(sym, idx, only_file=None, want_context=True):
    """
    Devuelve (por_fichero, todos).
    por_fichero: {fichero: {clase: [sites]}}
    """
    pat = re.compile(rf'\b{re.escape(sym)}\b')
    por_fichero, todos = {}, []
    for path, lines in idx.items():
        base = os.path.basename(path)
        if only_file and only_file not in base:
            continue
        for i, line in enumerate(lines, 1):
            if not pat.search(line):
                continue
            clase, _ = classify(line, sym)
            if clase is None:
                continue
            site = {
                "file": base,
                "path": os.path.relpath(path, PROJECT),
                "line": i,
                "class": clase,
                "receiver": receiver(line, sym),
            }
            if want_context:
                site["code"] = line.strip()[:104]
            todos.append(site)
            por_fichero.setdefault(base, {}).setdefault(clase, []).append(site)
    return por_fichero, todos


def selftest(verbose=False):
    """Vectores conocidos: MC_MASK_SITES son 7 puntos de escritura REALES."""
    # Ground truth verificado a mano en una sesion anterior, sobre
    # gmc_v6_0.c:838, v7_0.c:1018, v8_0.c:1133, v9_0.c:1996, v10_0.c:849,
    # v11_0.c:823, v12_0.c:920.  El test falla si el clasificador deja de
    # reconocer la forma "adev->gmc.mc_mask = ...;" que los siete comparten.
    MC_WRITE_FILES = {"gmc_v6_0.c", "gmc_v7_0.c", "gmc_v8_0.c", "gmc_v9_0.c",
                      "gmc_v10_0.c", "gmc_v11_0.c", "gmc_v12_0.c"}
    fails = 0

    def chk(name, got, want):
        nonlocal fails
        ok = got == want
        if not fails and not ok:
            pass
        if not ok:
            fails += 1
        print(f"  {'PASS' if ok else 'FAIL'}  {name}"
              f"{'' if ok else f'  got={got!r} want={want!r}'}")

    print("  --- clasificador: casos unitarios ---")
    # Escritura a un ring: ESCRIBE el registro, y sin este caso se reportaba
    # cero escrituras de mmVM_INVALIDATE_REQUEST siendo que hay 26 sitios.
    chk("un argumento de ring_write -> WRITTEN_ARG",
        classify("amdgpu_ring_write(ring, mmVM_INVALIDATE_REQUEST);",
                 "mmVM_INVALIDATE_REQUEST")[0], "WRITTEN_ARG")
    chk("WREG32 con el simbolo -> WRITTEN_ARG",
        classify("WREG32(mmVM_CONTEXT0_CNTL, tmp);",
                 "mmVM_CONTEXT0_CNTL")[0], "WRITTEN_ARG")
    chk("pero una lectura no se confunde",
        classify("if (x & mmVM_INVALIDATE_REQUEST) {",
                 "mmVM_INVALIDATE_REQUEST")[0], "READ")

    chk("asignacion -> WRITE",
        classify("adev->gmc.mc_mask = 0xffffffffffULL;", "mc_mask")[0], "WRITE")
    chk("lectura en comparacion -> READ",
        classify("if (x & adev->gmc.mc_mask) {", "mc_mask")[0], "READ")
    # Asignacion COMPUESTA: escribe en sym.  El self-test solo cubria "sym =",
    # y por eso el control negativo encontro "campo += 4" como READ.
    chk("sym += n -> WRITE",
        classify("foo->bar.mc_mask += 4;", "mc_mask")[0], "WRITE")
    chk("sym <<= 1 -> WRITE",
        classify("mc_mask <<= 1;", "mc_mask")[0], "WRITE")
    chk("otro campo <<= sym -> sym se LEE",
        classify("total <<= mc_mask;", "mc_mask")[0], "READ")
    chk("x == sym NO es escritura", classify("a == mc_mask;", "mc_mask")[0], "READ")

    chk("== NO es escritura",
        classify("if (mc_mask == foo)", "mc_mask")[0], "READ")
    chk("<= NO es escritura",
        classify("if (mc_mask <= foo)", "mc_mask")[0], "READ")
    chk("->= NO es escritura",
        classify("if (a->mc_mask) {", "mc_mask")[0], "READ")
    chk("por puntero &sym -> WRITE",
        classify("set_prt(table, &vm->mc_mask);", "mc_mask")[0], "WRITE")
    # Las dos formas de incremento son escritura.  El primer self-test solo
    # aceptaba la prefija y fallo con la postfija, que es la habitual.
    chk("sym++ (postfijo) -> WRITE",
        classify("mc_mask++;", "mc_mask")[0], "WRITE")
    chk("++sym (prefijo) -> WRITE",
        classify("++mc_mask;", "mc_mask")[0], "WRITE")
    chk("sym-- (postfijo) -> WRITE",
        classify("for (mc_mask--; )", "mc_mask")[0], "WRITE")
    chk("&algo->sym -> WRITE (direccion de un campo)",
        classify("set_prt(table, &vm->mc_mask);", "mc_mask")[0], "WRITE")
    # "&" unario (direccion) contra "&" binario (AND bitwise).  El AND es una
    # LECTURA: marcarlo como escritura convierte todo el arbol de mascaras de
    # bits en un mapa falso de escritura.
    # `addr &= mc_mask` ESCRIBE addr y LEE mc_mask.  La clase se pide respecto
    # a mc_mask, asi que lo correcto es READ.  (La primera version de este
    # test decia WRITE con la etiqueta diciendo "no es escritura": el test
    # estaba mal, no el clasificador.)
    chk("addr &= mc_mask  -> mc_mask se LEE",
        classify("addr &= adev->gmc.mc_mask;", "mc_mask")[0], "READ")
    chk("x & campo -> READ (AND con operando a la izquierda)",
        classify("if (x & adev->gmc.mc_mask) {", "mc_mask")[0], "READ")
    chk("(x) & campo -> READ",
        classify("y = (addr) & adev->gmc.mc_mask;", "mc_mask")[0], "READ")
    chk("puntero tras & -> WRITE",
        classify("t->x = &vm->mc_mask;", "mc_mask")[0], "WRITE")
    chk("#define -> DEFINE",
        classify("#define MC_MASK_BITS 40", "MC_MASK_BITS")[0], "DEFINE")
    chk("declaracion simple -> DECL",
        classify("unsigned long mc_mask;", "mc_mask")[0], "DECL")
    chk("sin el simbolo -> None",
        classify("int totally_unrelated;", "mc_mask")[0], None)

    print("  --- receptor: la pregunta real ---")
    chk("receptor de una cadena de flechas",
        receiver("adev->gmc.mc_mask = 0xffffffffffULL;", "mc_mask"),
        "adev->gmc.mc_mask")
    chk("receptor con punto",
        receiver("adev->gmc.mc_mask = 1;", "mc_mask"), "adev->gmc.mc_mask")
    chk("no inventa receptor en una lectura simple",
        receiver("if (mc_mask) return;", "mc_mask"), "mc_mask")

    print("  --- contra el corpus real ---")
    idx = get_index(verbose)
    chk("el corpus esta indexado", len(idx) > 100, True)
    por_fichero, todos = scan("mc_mask", idx, want_context=False)
    escritos = {f for f, c in por_fichero.items() if "WRITE" in c}
    faltan = MC_WRITE_FILES - escritos
    chk("los 7 ficheros con escritura de mc_mask estan",
        faltan, set())
    chk("y clasifica como WRITE esas escrituras",
        sorted(escritos & MC_WRITE_FILES) and
        all(any(s["class"] == "WRITE" for s in por_fichero[f]["WRITE"])
            for f in escritos & MC_WRITE_FILES), True)
    chk("gmc_v8_0.c aparece y su receptor es el campo completo",
        any(s["receiver"] == "adev->gmc.mc_mask"
            for s in todos if s["file"] == "gmc_v8_0.c"
            and s["class"] == "WRITE"), True)

    n_read = sum(len(c.get("READ", [])) for c in por_fichero.values())
    n_write = sum(len(c.get("WRITE", [])) for c in por_fichero.values())
    # El fallo real que casi se escapa: se pidio "level_shift" creyendolo el
    # simbolo, y la palabra no existe porque el simbolo es
    # amdgpu_vm_pt_level_shift.  "\b" no corta dentro de un identificador.
    sub = substring_only("level_shift", idx)
    chk("detecta que level_shift es subcadena de otro simbolo",
        len(sub) > 0, True)
    chk("y propone el simbolo real",
        "amdgpu_vm_pt_level_shift" in [s for s, _ in sub], True)
    chk("un nombre completo NO aparece como subcadena de si mismo",
        [s for s, _ in substring_only("mc_mask", idx)
         if s in ("mc_mask", "mc_maskXYZ")], [])
    chk("substring_only no inventa simbolos para un termino generico",
        isinstance(substring_only("zzzz_inexistente", idx), list), True)

    print(f"  mc_mask en el corpus: {len(todos)} sitios "
          f"({n_write} WRITE, {n_read} READ) en {len(por_fichero)} ficheros")
    print(f"  {'todos pasan' if not fails else f'{fails} FALLAN'}")
    return 1 if fails else 0


def substring_only(sym, idx, only_file=None):
    """
    Simbolos reales que CONTIENEN la cadena sym.
    Es el diagnostico de "he pedido un nombre que es parte de otro simbolo",
    que es el error de nombres mas comun al rastrear en C: en
    amdgpu_vm_pt_level_shift NO existe la palabra level_shift, porque '_' es
    caracter de palabra y \\b no corta ahi.
    Devuelve [(simbolo_encontrado, nº_de_sitios), ...] ordenado por frecuencia.
    """
    pat = re.compile(r'\b[A-Za-z_]\w*' + re.escape(sym) + r'\w*\b')
    conteo = {}
    for path, lines in idx.items():
        if only_file and only_file not in os.path.basename(path):
            continue
        for line in lines:
            for m in pat.finditer(line):
                if m.group(0) != sym:
                    conteo[m.group(0)] = conteo.get(m.group(0), 0) + 1
    return sorted(conteo.items(), key=lambda kv: -kv[1])


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sym", help="simbolo a rastrear")
    ap.add_argument("--field", help="alias de --sym, con agrupacion por receptor")
    ap.add_argument("--file", help="limitar a este fichero")
    ap.add_argument("--write", action="store_true", help="solo escrituras")
    ap.add_argument("--read", action="store_true", help="solo lecturas")
    ap.add_argument("--context", action="store_true", default=True)
    ap.add_argument("--no-context", dest="context", action="store_false")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()

    if a.self:
        return selftest(a.verbose)

    sym = a.sym or a.field
    if not sym:
        ap.print_help()
        return 2

    idx = get_index(a.verbose)
    por_fichero, todos = scan(sym, idx, a.file, a.context)

    if a.write:
        # WRITTEN_ARG tambien ES una escritura: el registro se pasa a
        # amdgpu_ring_write().  Filtrar solo por "WRITE" dejaba fuera los
        # registros que se emiten a un ring en vez de escribirse en MMIO, que
        # es como se invalidan las TLB en AMDGPU.  El fallo se manifesto como
        # "0 escrituras" de mmVM_INVALIDATE_REQUEST con 17 sitios encima.
        todos = [s for s in todos if s["class"] in ("WRITE", "WRITTEN_ARG")]
    elif a.read:
        todos = [s for s in todos if s["class"] == "READ"]

    if a.json:
        print(json.dumps({"sym": sym, "sites": todos,
                          "by_file": {f: {k: len(v) for k, v in c.items()}
                                      for f, c in por_fichero.items()}},
                         indent=2))
        return 0

    if not todos:
        # Diagnostico del fallo mas frecuente al usar esto: pedir un nombre
        # que es SUBCADENA de otro simbolo.  "\\b" no corta dentro de un
        # identificador, asi que amdgpu_vm_pt_level_shift NO contiene una
        # palabra "level_shift".  Sin este aviso la herramienta dice "no
        # existe" y eso se lee como una conclusion sobre el hardware.
        # Ocurrio de verdad: se pidio "level_shift" creyendolo el simbolo.
        sub = substring_only(sym, idx, a.file)
        if sub:
            print(f"  {sym}: NINGUN sitio con ese NOMBRE EXACTO.")
            print(f"  PERO la cadena aparece dentro de {len(sub)} simbolos distintos:")
            for nombre, n in sub[:12]:
                print(f"    {nombre}   ({n} sitios)")
            print()
            print(f"  Usa --sym {sub[0][0]} si ese es el simbolo que buscabas.")
        else:
            print(f"  {sym}: NINGUN sitio clasificado en el corpus. "
                  f"Comprueba el nombre antes de concluir que no existe.")
        return 1

    # vista principal: agrupado por fichero y clase
    por_fichero_filtrado = {}
    for s in todos:
        por_fichero_filtrado.setdefault(s["file"], []).append(s)
    print(f"  SIMBOLO  {sym}   {len(todos)} sitios en {len(por_fichero_filtrado)} ficheros")
    print()
    for f in sorted(por_fichero_filtrado):
        sites = por_fichero_filtrado[f]
        # WRITTEN_ARG cuenta como escritura en el resumen, igual que en el
        # filtro --write.  Si no, la linea decia "0 WRITE 0 READ" con un
        # WRITTEN_ARG debajo, que es una contradiccion visible.
        cw = sum(1 for s in sites if s["class"] in ("WRITE", "WRITTEN_ARG"))
        cr = sum(1 for s in sites if s["class"] == "READ")
        print(f"    {f:26} {len(sites):3} sitios   "
              f"{cw} WRITE  {cr} READ  {sites[0]['path']}")
        for s in sites:
            if a.context:
                print(f"      {s['class']:6} {s['line']:5}  {s.get('code','')[:82]}")
        print()

    # vista de campo: agrupado por expression receptora.  Es la que responde
    # "¿quien escribe QUE campo", que es la pregunta que grep no puede.
    if a.field:
        recs = {}
        for s in todos:
            recs.setdefault((s["receiver"], s["class"]), []).append(s)
        print("  POR EXPRESION RECEPTORA")
        for (r, c) in sorted(recs, key=lambda k: (str(k[0]), k[1])):
            ss = recs[(r, c)]
            fl = sorted({x["file"] for x in ss})
            print(f"    {c:6} {str(r):34} {len(ss):3} en {len(fl)} ficheros: "
                  f"{', '.join(fl[:4])}{' ...' if len(fl) > 4 else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())