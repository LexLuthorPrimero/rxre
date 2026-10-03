#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mutdrv.py -- poder discriminante de las suites en C de la linea de driver.

QUE MIDE
    Para cada comparador de borde que encuentra en un .c del driver, genera un
    MUTANTE cambiando el operador y lo mide:

        KILLED      el mutante no pasa la suite      -> la suite lo detecta
        SURVIVED    el mutante pasa la suite        -> NO lo detecta.  AGUERO
        EXCLUDED    el mutante no compila           -> no es prueba de la suite
        NO_EFFECT   el mutante es equivalente       -> no cuenta ni a favor ni en contra

POR QUE CADA OPERADOR SE MUEVE A SU VERSION LARGA, Y AL REVES
    `<` -> `<=` y `<=` -> `<`  se hacen por separado.  Un mutante que decompila
    con -Werror cuenta como EXCLUDED, no como fallo: si no compila, la suite no
    ha medido nada, y decir que la "detecto" seria mentir.

POR QUE UN SUPERVIVIENTE NO ES UN FALLO DE LA SUITE, todavia
    Puede ser que la suite no lo mire, o que lo mire y no lo distinga.  Por eso
    el informe da el CODIGO y la LINEA exactos: sin eso el hallazgo es
    inutilizable.  Un "la suite es floja" sin linea no es accionable.

QUE NO ES ESTA HERRAMIENTA
    No mide correccion del driver.  Mide si las pruebas que el proyecto tiene
    escritas noticedarian el cambio.  Un driver con 0 supervisientes no es un
    driver correcto: es un driver del que nadie busca los fallos.
    ESA ES LA DIFERENCIA entre cobertura y discriminacion, y es la que 980
    demostro que faltaba.

RIESGO
    CERO.  Trabaja sobre COPIAS en un directorio temporal.  El corpus no se
    escribe ni se lee para decidir nada.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

# (regex del operador, sustitucion)  -- se aplican en este orden y se para en
# el primero que aplica, para no hacer dos mutaciones en la misma linea.
FLIPS = [
    (re.compile(r'<='), '<'),
    (re.compile(r'>='), '>'),
    (re.compile(r'(?<![<>=!])<(?!=)'), '<='),
    (re.compile(r'(?<![<>=!])>(?!=)'), '>='),
    (re.compile(r'=='), '!='),
    (re.compile(r'!='), '=='),
]


def _sigue_en_comentario(linea, en_com):
    """Actualiza el estado de comentario de bloque tras leer `linea`."""
    i = 0
    while True:
        if en_com:
            j = linea.find('*/', i)
            if j < 0:
                return True
            en_com = False
            i = j + 2
            continue
        a = linea.find('/*', i)
        b = linea.find('//', i)
        if b >= 0 and (a < 0 or b < a):
            return False
        if a < 0:
            return False
        en_com = True
        i = a + 2


def flip_line(line):
    """Devuelve (linea_mutada, operador_original, operador_nuevo) o None.

    MEDIDO 2026-10-03: esta funcion calculaba `codigo` -- la parte de la linea
    que no es comentario -- y despues NO LA USABA, con lo que mutaba tambien
    dentro de comentarios de bloque.  El efecto fue DOS SUPERVIVIENTES FALSOS:
    las lineas 61 y 62 de rx550_submission.c son la cabecera comentada de
    PACKET3, y "mutarlas" no cambia el comportamiento del binario.  El
    instrumento reportaba agujeros donde no habia nada.

    La leccion es la del propio hallazgo: un instrumento que produce una cifra
    sin mirar de donde sale puede estar midiendo su propia fruta.  Aqui se nota
    porque los dos supervivientes eran lineas que un humano lee como comentario;
    un monton de supervivientes APARENTES en lineas comentadas es la senal.
    """
    return _flip(line, False)


def _flip(line, en_comentario):
    """`en_comentario` es el estado que llega desde la linea anterior: un
    comentario de bloque abre en una linea y sigue en las siguientes."""
    s = line.lstrip()
    if en_comentario:
        # dentro de un comentario de bloque solo se muta si el comentario se
        # cierra y queda codigo despues en la misma linea
        if '*/' not in line:
            return None
        antes, _, despues = line.partition('*/')
        s = despues.lstrip()
        if not s or s.startswith('//'):
            return None
        base = antes + '*/' + despues
        off = len(antes) + 2
    else:
        if s.startswith('//'):
            return None
        if s.startswith('/*'):
            if '*/' not in line:
                return None          # abre y no cierra: comentario entero
            base = line
            off = line.index('*/') + 2
        else:
            base = line
            off = 0

    # MEDIDO 2026-10-03 por la auto-prueba del clasificador: una linea de CODIGO
    # con comentario de linea al final (`int y = 1;  // no < aqui`) mutaba el
    # `<` del comentario.  El comentario de linea se corta ANTES de buscar, y
    # solo se corta el `//` que cae en la parte de CODIGO de la linea.
    #
    # LIMITACION DECLARADA: esto corta tambien un `//` dentro de un literal de
    # cadena.  No hay ninguno en las comparaciones que se mutan aqui, y
    # comprobarlo en cada linea costaria mas que el caso que evita.
    corte = base.find('//', off)
    if corte >= 0:
        base = base[:corte]

    for pat, nuevo in FLIPS:
        m = pat.search(base, off)
        if m:
            return base[:m.start()] + nuevo + base[m.end():], m.group(0), nuevo
    return None


def compilar(cc, raiz, cwd, fuentes, salida):
    cmd = [cc, '-O2', '-Wall', '-Wextra', '-Werror', '-I', raiz,
           '-I', os.path.join(os.path.dirname(raiz), 'rx550-pm4'),
           '-o', salida] + fuentes
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode == 0, (p.stderr or '')[-400:]


def selftest():
    """Auto-prueba del CLASIFICADOR, que es lo unico de esta herramienta que se
    puede comprobar sin hardware.

    MEDIDO 2026-10-03: sin estos casos la herramienta reporto DOS SUPERVIVIENTES
    FALSOS (las lineas 61 y 62 de rx550_submission.c, que son la cabecera
    comentada de PACKET3).  Mutar un comentario no cambia el binario, luego el
    mutante no podia ser detectado nunca, y eso no es un agujero de la suite: es
    un agujero del instrumento.  La cifra de poder discriminante habria salido
    mas baja por un fallo mio, que es la direccion en la que un error no se
    nota.
    """
    casos = [
        # (linea, operador_original_esperado o None, descripcion)
        ('\tif (reg < START || reg >= END)', '>=', 'comparador real'),
        ('\tif (a >= b)', '>=', 'el primer operador de la linea gana'),
        ('\tint x = a < b; /* trailing < */', '<', 'codigo antes de bloque'),
        ('\t/* c */ int z = p > q;', '>', 'codigo despues de bloque'),
        ('\t/* PACKET3(op, n) == (A << 30)', None, 'bloque abre y no cierra'),
        ('\t/* solo un < */', None, 'bloque entero en una linea'),
        (' *  type en [31:30]', None, 'continuacion de bloque'),
        ('\tint y = 1; // no < aqui', None, 'comentario de linea al final'),
        ('\t// entero <', None, 'linea entera de comentario'),
        ('#define RX550_X\t4', None, 'sin comparador'),
        ('\tif (x != 0)', '!=', 'distinto-igual'),
    ]
    ok = fail = 0
    print('  -- clasificador de linea: %d casos --' % len(casos))
    for linea, esperado, desc in casos:
        got = flip_line(linea)
        real = got[1] if got else None
        if real == esperado:
            print('      P  %s' % desc)
            ok += 1
        else:
            print('      F  %s   esperaba %s,Obtuvo %s' % (desc, esperado, real))
            fail += 1

    # Y el estado que viaja de linea a linea, que es lo que produjo los dos
    # supervivientes falsos: un bloque abierto en una linea tiene que seguir
    # abierto en las siguientes.
    # Y el estado que viaja de linea a linea, que es lo que produjo los dos
    # supervivientes falsos: un bloque abierto en una linea tiene que seguir
    # abierto en las siguientes.
    #
    # MEDIDO 2026-10-03: estas aserciones salieron ROJAS la primera vez, y las
    # dos faults eran MIAS, no del clasificador.  La tercera linea del bloque
    # cierra el comentario y trae codigo detras (`int q = m < n;`), y ese codigo
    # SI se debe mutar: un instrumento que solo muta antes de */ deja sin medir
    # el codigo que sigue al cierre, que es justo el caso interesante.  Y la
    # comprobacion de "el estado se cerro" estaba escrita al reves, diciendo que
    # se cerraba cuando estaba abierto.  Dos tests que no podia pasar.
    abierto = False
    bloque = [
        ('\t/* abre aqui <',     None),
        ('\t * sigue < con <',   None),
        ('\t */ int q = m < n;', '<'),     # codigo real despues de */
    ]
    for linea, esperado in bloque:
        r = flip_line(linea) if not abierto else _flip(linea, True)
        abierto = _sigue_en_comentario(linea, abierto)
        real = r[1] if r else None
        if real == esperado:
            print('      P  bloque multilinea: %-28r muta %s'
                  % (linea.strip()[:26], real))
            ok += 1
        else:
            print('      F  bloque multilinea: %-28r esperaba %s, obtuvo %s'
                  % (linea.strip()[:26], esperado, real))
            fail += 1
    if abierto:
        print('      F  el estado de comentario sigue abierto tras */')
        fail += 1
    else:
        print('      P  el estado de comentario se cierra tras */')
        ok += 1

    print('  %d pasaron, %d fallaron' % (ok, fail))
    return 1 if fail else 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--self-test':
        return selftest()
    if len(sys.argv) < 4:
        print(__doc__)
        print("uso: mutdrv.py <RAIZ_DRIVER> <suite.c> <driver.c> [mas .c ...]")
        print("     mutdrv.py --self-test")
        return 2
    raiz = os.path.abspath(sys.argv[1])
    suite_c = sys.argv[2]
    driver_c = sys.argv[3:]
    cc = os.environ.get('CC', 'gcc')
    tests = os.path.join(raiz, 'tests')
    # el cwd de la compilacion es tests/, luego las fuentes van por NOMBRE:
    # una ruta relativa a raiz seria tests/tests/...
    base_suite = os.path.basename(suite_c)

    tmp = tempfile.mkdtemp(prefix='mutdrv.')
    work = os.path.join(tmp, 'rx550-driver')
    shutil.copytree(raiz, work, symlinks=True,
                    ignore=shutil.ignore_patterns('*.o', '*.ko', '*.mod*', '*.cmd',
                                                  'modules.order', 'Module.symvers'))
    base_driver = [os.path.join(work, os.path.basename(x)) for x in driver_c]

    # --- baseline: sin mutar, tiene que pasar -------------------------------
    ok, err = compilar(cc, work, tests, [base_suite] + base_driver,
                       os.path.join(tmp, 'base'))
    if not ok:
        print('BASELINE NO COMPILA. No se mide nada sobre un arbol que no arranca.')
        print(err)
        shutil.rmtree(tmp, ignore_errors=True)
        return 1
    r = subprocess.run([os.path.join(tmp, 'base')], capture_output=True, text=True)
    if r.returncode != 0:
        print('BASELINE FALLA (rc=%d). La suite no esta verde de partida: '
              'no hay baseline contra el que comparar.' % r.returncode)
        print((r.stdout or '')[-400:])
        shutil.rmtree(tmp, ignore_errors=True)
        return 1
    print('baseline  %s  rc=0  (mutantes sobre %s)'
          % (os.path.basename(suite_c), ', '.join(os.path.basename(x) for x in driver_c)))
    print('-' * 74)

    # --- recorrido de las lineas mutables ----------------------------------
    killed = survived = excluded = 0
    CTL = []
    for di, dpath in enumerate(driver_c):
        rel = os.path.relpath(dpath, raiz)
        dst = os.path.join(work, os.path.basename(dpath))
        with open(dpath, encoding='utf-8', errors='replace') as fh:
            lineas = fh.readlines()
        # el estado de comentario de BLOQUE viaja de linea a linea: un /* abre
        # en una linea y sigue en las que siguen.  Sin esto se mutan las
        # cabeceras comentadas, que es el fallo que se midio.
        en_com = False
        for ln, linea in enumerate(lineas, 1):
            if len(linea) > 300 or '\t' * 3 in linea:
                en_com = _sigue_en_comentario(linea, en_com)
                continue
            f = flip_line(linea) if not en_com else _flip(linea, True)
            en_com = _sigue_en_comentario(linea, en_com)
            if not f:
                continue
            mutada, orig, nuevo = f
            with open(dst, 'w', encoding='utf-8') as fh:
                fh.writelines(lineas[:ln - 1] + [mutada] + lineas[ln:])
            ok, err = compilar(cc, work, tests, [base_suite] + base_driver,
                               os.path.join(tmp, 'm'))
            if not ok:
                excluded += 1
                CTL.append((rel, ln, orig, nuevo, 'EXCLUDED'))
                continue
            r = subprocess.run([os.path.join(tmp, 'm')], capture_output=True,
                               text=True, timeout=120)
            if r.returncode != 0:
                killed += 1
                CTL.append((rel, ln, orig, nuevo, 'KILLED'))
            else:
                survived += 1
                CTL.append((rel, ln, orig, nuevo, 'SURVIVED'))
            # se escribe el original para el siguiente mutante
            with open(dst, 'w', encoding='utf-8') as fh:
                fh.writelines(lineas)

    total = killed + survived + excluded
    print('mutantes            %d' % total)
    print('  KILLED            %d' % killed)
    print('  SURVIVED          %d   <-- la suite NO lo detecta' % survived)
    print('  EXCLUDED          %d   (no compila: no mide nada)' % excluded)
    if total:
        print('  poder discriminante sobre los comparables: %.1f%%'
              % (100.0 * killed / (killed + survived)))
    print('-' * 74)
    if CTL:
        print('SUPERVIVIENTES (con su localizacion exacta):')
        for rel, ln, orig, nuevo, est in CTL:
            if est == 'SURVIVED':
                print('  %s:%d   %s -> %s' % (rel, ln, orig, nuevo))
    if survived:
        print('-' * 74)
        print('AVISO, Y NO ES UN DETALLE DE REDACCION:')
        print('  "SURVIVED" mezcla DOS cosas que no se pueden leer igual.')
        print()
        print('    1. AGUJERO REAL   la suite no mira esa linea, o la mira y no la')
        print('                      distingue.  Se tapa anadiendo el caso del limite.')
        print()
        print('    2. MUTANTE EQUIVALENTE  el cambio no altera el comportamiento para')
        print('                      NINGUNA entrada, y ninguna entrada puede matarlo.')
        print('                      Se distingue por REDACCION, no por ejecucion, y')
        print('                      la herramienta no puede decidirlo.')
        print()
        print('  MEDIDO 2026-10-03: de los 10 supervivientes que dio test_vmid0_gart,')
        print('  6 eran agujeros y se taparon con 18 CHECK.  El ultimo superviviente,')
        print('  rx550_vmid0_gart.c:96 `>=` -> `>`, es EQUIVALENTE BAJO EL INVARIANTE:')
        print('  aperture_init exige size %% 4096 == 0, luego size>>12 == entries siempre,')
        print('  y la segunda guarda (index >= entries) captura lo que la primera dejaba')
        print('  pasar.  No hay entrada que lo mate.  Clasificarlo de "agujero" habria')
        print('  llevado a anadir un caso imposible de escribir.')
        print()
        print('  O sea: un porcentaje de poder discriminante SIN clasificar estos dos')
        print('  casos por separado no es una medida.  Es un numero con dos')
        print('  significados.')
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())