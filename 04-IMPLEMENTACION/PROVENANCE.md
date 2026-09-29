# Procedencia de `integration_test.sh` y del pipeline F1 → F2

**Fecha**: 2026-09-29 · **Ámbito**: `04-IMPLEMENTACION/`

Este fichero existe porque el commit `0b95f90` no describe lo que contiene.

## Qué ocurrió

Estos ocho ficheros se escribieron y se preparationsaron (`git add`) en una
sesión:

| Fichero | Autoría |
|---|---|
| `04-IMPLEMENTACION/integration_test.sh` | sesión IA-2 del pipeline |
| `04-IMPLEMENTACION/tools/rx550_compress.c` | ídem |
| `04-IMPLEMENTACION/tools/rx550_decompress.c` | ídem |
| `04-IMPLEMENTACION/common/png_rw.c`, `png_rw.h` | ídem |
| `04-IMPLEMENTACION/Makefile` | ídem |
| `04-IMPLEMENTACION/README.md` | ídem |
| `.gitignore` (entradas `bin/`, `work/`, `*.rgba`) | ídem |

Estaban en el índice, pendientes de commit, cuando otra sesión ejecutó
`git commit` y los recogió dentro de `0b95f90`, cuyo mensaje versa sobre el
**layout 2D del PNG** y no sobre el pipeline.

Consecuencias, que son las que este fichero evita repetir:

1. **El mensaje no describe el contenido.** Quien lea `0b95f90` buscando el
   pipeline no lo encontrará, y quien busque el layout 2D encontrará ocho
   ficheros más de los que probablemente esperaba.
2. **Los SHA de los ficheros no son trazables a la sesión que los escribió.**
   `git blame` atribuye a `0b95f90` código que no escribió esa sesión.
3. **El commit `4ffb53f`, anterior, dice "3/3 PASO"** sobre un pipeline que
   en ese momento no estaba commiteado. La afirmación era cierta en la
   máquina de quien la escribió y no era reproducible por nadie más.

## Estado del contenido

**Idéntico en disco y en `HEAD`**, verificado fichero a fichero con
`git diff --quiet HEAD`. Nada se perdió. Lo que falta es el mensaje que
describe el trabajo, y no se puede añadir a un commit ya escrito sin
reescribir historia, que es exactamente lo que `COORDINACION.md` prohíbe.

## Qué contiene el pipeline, en resumen

Medido, dos corridas consecutivas idénticas, `rc=0`:

| Textura | Discrepancias GPU vs CPU | PSNR round-trip | Suelo | Estado |
|---|---|---|---|---|
| `t1_gradiente.png` | 0 / 16384 | 38.24 dB | 25 dB | PASO |
| `t2_ruido.png` | 0 / 16384 | 13.55 dB | 10 dB | PASO |
| `t3_estructura.png` | 0 / 16384 | 45.12 dB | 20 dB | PASO |

Las tres cifras no son la misma cifra: `0/16384` mide la fidelidad del
**decodificador**, el PSNR mide la calidad del **codificador** con pérdida, y
`GPUVSCPU 0` comprueba que el PNG conserve el orden de bloques. El detalle
está en `README.md` §«Las tres cifras».

Tres defectos que el pipeline encontró y que están corregidos en el código,
documentados en el README y en los comentarios de cada fichero:

1. Orden de bloque frente a orden de imagen, indistinguibles en un corpus de
   un solo bloque.
2. `dst` sin el factor 4 en el reordenado: escribía bien la primera fila y
   el resto en otro sitio.
3. `awk -v p=` en vez de `$1`: el PSNR llegaba por `stdin` y la comparación se
   hacía en `BEGIN`, que no lee `stdin`.

## Lección operativa

`git commit` sin `-a` ni argumentos recoge **lo que haya en el índice**, no lo
que la sesión en curso ha escrito. Con tres sesiones sobre un árbol, el índice
es estado compartido y el mensaje del commit describe una intención que puede
no ser la del contenido que se versiona.

Dos medidas, ninguna de las cuales estaba en el protocolo:

- **`git commit <ruta>`** en vez de `git commit` a secas, o `git commit -o`
  (`--only`) para ignorar el índice.
- **Releer el mensaje después de escribirlo.** El mensaje es la única parte
  del commit que no queda en el árbol, y es la única que no se puede
  verificar comparando ficheros.

`COORDINACION.md` describe el cerrojo de directorio. El cerrojo serializa las
escrituras al árbol; no serializa el índice de git, que es donde estos ocho
ficheros estaban esperando.

## Lo que este fichero NO hace

- No reescribe `0b95f90`. El contenido es correcto y está en `HEAD`; el
  mensaje es lo que no lo describe, y un `--amend` reescribiría un commit que
  otra sesión ya ha citado en su propio trabajo.
- No acusa a ninguna sesión. Que otra sesión recogiera el índice no es un
  error suyo si no sabía que había algo en él: el estado compartido del
  índice no es visible desde el árbol de trabajo. La omisión es del
  protocolo, y por eso la solución que propone es de protocolo.
- No sustituye al commit que falta. La trazabilidad por SHA de estos ocho
  ficheros sigue siendo `0b95f90`, y ese commit habla de otra cosa. Quien
  necesite la atribución exacta tiene que leer este fichero, no el log.
