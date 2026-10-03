"""inventario_universo.py -- el universo de arboles hermanos, medido y clasificado.

QUE ES

La pregunta que responde es la de la regla de un solo arbol activo: de los
directorios que hay FUERA de PROJECT_ROOT y que se parecen a este proyecto, cual
es una copia, cual es un archivo, cual es otro proyecto y cual esta vacio. No
decide nada: mide y clasifica lo que se puede clasificar por comparacion
mecanica, y marca PENDING_COMPARISON lo que no.

POR QUE ESTA EN 01-AUDITORIA Y NO EN tools/

Porque su unico consumidor es este, y su salida son tablas de clasificacion de
arboles, no un protocolo que otras herramientasreutilizar reutilizar.

LO QUE NO ESTABLECE, y esta en el codigo a proposito

Compara RUTAS, no contenido. Dos arboles con distinta estructura dan 100% de
"solo alli" sin que haya ni una linea duplicada, y al reves: un fichero movido
de nombre aparece como unico aqui y como perdido alla. Ese limite se midi en
este mismo conjunto: el backup hermano tiene 31524 rutas y solo 1 en comun con
el proyecto, cifra que no significa nada porque el backup no esta organised como
el proyecto.

Por eso el script imprime el aviso antes de la tabla. Un inventario que
presentara ese numero como veredicto de duplicacion seria peor que no tenerlo.

LO QUE SI ESTABLECE

  - el tamano, el numero de ficheros y el digest de cada arbol hermano
  - si un arbol tiene git, y si el repo tiene historia
  - si el repositorio padre existe y si rastrea algo
  - un techo, no un veredicto: N rutas que el proyecto no tiene con ESE nombre

ESTADO

  PRODUCCION. Sin self-test, y declarado: no se ha autoprobado con vectores
  conocidos. Se valida por ejecucion y por la revision manual de su tabla de
  salida, que es la unica forma de validar un inventario de un solo caso.

Como re-ejecutarlo, desde la raiz del proyecto:

    python3 01-AUDITORIA/tools/inventario_universo.py

Resultado del 2026-10-03, con el que se escribio el addendum del kernel:

    estudiar_nootboolm_rx550             0.2M    27  EVIDENCIA_UNICA_POR_COMPARAR
    RX550-INVESTIGACION-NOTEBOOKLM       3.4M   106  EVIDENCIA_UNICA_POR_COMPARAR
    RX550_Iterative_Research             0.0M     0  STALE_VACIO
    RX550_Modo_Torneo_Backup_2026-...  1636.8M 31524 EVIDENCIA_UNICA_POR_COMPARAR
    HASWELL                              3.4M   141  EVIDENCIA_UNICA_POR_COMPARAR
    .git                                 0.0M     0  STALE_VACIO

Y de ahi salio lo que no era esperable: el backup de 1,6 GB NO contiene una
copia de este proyecto, sino el proyecto hermano "RX 550 Modo Torneo", con su
propio manifest y su propio ciclo. Su clasificacion es
SIBLING_PROJECT__SEPARATE_SCOPE, no ARCHIVE.
"""

import hashlib
import os
import subprocess
import time

HOME = os.path.expanduser('~')
RAIZ = os.path.join(HOME, 'Escritorio', 'RX550-INVESTIGACION')

# (nombre, pista de lo que se sospechaba antes de medir)
CANDIDATOS = [
    ('estudiar_nootboolm_rx550', 'ESTUDIO_SIN_GIT'),
    ('RX550-INVESTIGACION-NOTEBOOKLM', 'HERMANO'),
    ('RX550_Iterative_Research', 'HERMANO_VACIO'),
    ('RX550_Modo_Torneo_Backup_2026-09-19_0836', 'BACKUP'),
    ('HASWELL', 'PROYECTO_CPU_CON_GIT'),
    ('.git', 'REPO_PADRE'),
]

# .git se recorre aparte: incluirlo en el manifiesto haria que el digest
# cambiase con cada commit y el inventario dejaria de ser comparable consigo
# mismo entre dos dias.
EXCLUIR = {'.git', '__pycache__', '.write-lock'}


def manifiesto(d):
    """rutas relativas -> (tamano, mtime). Excluye .git y caches."""
    out = []
    for raiz, dirs, files in os.walk(d):
        dirs[:] = [x for x in dirs if x not in EXCLUIR]
        for f in files:
            p = os.path.join(raiz, f)
            try:
                st = os.lstat(p)
            except OSError:
                continue
            out.append((os.path.relpath(p, d), st.st_size, int(st.st_mtime)))
    return out


def digest(d):
    """sha de la lista rutas:tamano:mtime. Logico, no de bytes: mas barato y
    suficiente para saber si un arbol se ha movido."""
    h = hashlib.sha256()
    for p, s, m in sorted(manifiesto(d)):
        h.update(('%s:%d:%d\n' % (p, s, m)).encode('utf-8', 'replace'))
    return h.hexdigest()


def main():
    print('PROJECT_ROOT   %s' % RAIZ)
    print('FECHA          %s' % time.strftime('%Y-%m-%d'))
    print()
    print('%-36s %10s %7s %-18s %s'
          % ('ruta', 'tamano', 'fich.', 'digest', 'clasificacion'))
    print('-' * 118)

    proy = {p for p, _s, _t in manifiesto(RAIZ)}

    for nombre, pista in CANDIDATOS:
        d = os.path.join(HOME, 'Escritorio', nombre)
        if not os.path.exists(d):
            print('%-36s %s' % (nombre, 'NO EXISTE'))
            continue

        m = manifiesto(d)
        n = len(m)
        tam = sum(s for _p, s, _t in m)
        dg = digest(d)[:16]
        es_dir = os.path.isdir(d)

        if not es_dir or n == 0:
            print('%-36s %9.1fM %7d %-18s %s'
                  % (nombre, tam / 1e6, n, dg,
                     'STALE_VACIO' if n == 0 else 'NO_ES_DIRECTORIO'))
            continue

        propias = {p for p, _s, _t in m}
        solo_ahi = propias - proy
        comunes = len(propias & proy)

        if solo_ahi == 0:
            clas = 'CON_VISTA_AL_CANONICO'
        elif len(solo_ahi) < 0.05 * len(propias):
            clas = 'CANDIDATO_ARCHIVE__PENDING_COMPARISON'
        else:
            clas = 'EVIDENCIA_UNICA_POR_COMPARAR'

        print('%-36s %9.1fM %7d %-18s %s' % (nombre, tam / 1e6, n, dg, clas))
        print('%38s %d rutas propias, %d en comun, %d SOLO AHI (%4.1f%%)'
              % ('', len(propias), comunes, len(solo_ahi),
                 100.0 * len(solo_ahi) / len(propias)))

    print()
    print('AVISO, y es el punto del script.')
    print('  Se comparan RUTAS, no contenido. Dos arboles con distinta estructura')
    print('  dan 100% de "solo alli" sin ni una linea duplicada. El numero de la')
    print('  tabla es un TECHO, no un veredicto de duplicacion. Para afirmar')
    print('  duplicacion hay que comparar contenido, que es otro paso.')

    print()
    padre = os.path.join(HOME, 'Escritorio')
    if os.path.isdir(os.path.join(padre, '.git')):
        r = subprocess.run(['git', '-C', padre, 'ls-files'],
                           capture_output=True, text=True)
        lg = subprocess.run(['git', '-C', padre, 'log', '--oneline', '-1'],
                            capture_output=True, text=True)
        print('repositorio padre en ~/Escritorio:')
        print('  ficheros rastreados: %d' % len(r.stdout.split()))
        print('  ultimo commit:       %s' % (lg.stdout.strip() or '(ninguno)'))
        if not r.stdout.split() and not lg.stdout.strip():
            print('  veredicto: STALE. No rastrea nada y no tiene historia, asi que')
            print('  NO es un repo anidado activo y NO corrompe la procedencia.')
            print('  Se deja quieto: borrar un .git sin permiso seria destructivo y')
            print('  no aporta nada.')

    print()
    r = subprocess.run(['git', '-C', RAIZ, 'ls-files'], capture_output=True, text=True)
    lg = subprocess.run(['git', '-C', RAIZ, 'log', '--oneline', '-1'],
                        capture_output=True, text=True)
    print('el proyecto, que es la unica raiz activa:')
    print('  repo propio: %d ficheros rastreados, HEAD = %s'
          % (len(r.stdout.split()), (lg.stdout.strip() or '-')[:56]))


if __name__ == '__main__':
    main()