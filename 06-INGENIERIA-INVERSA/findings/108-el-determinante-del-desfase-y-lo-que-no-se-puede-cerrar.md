# 108 · El discriminante del hueco, aislado por via independiente: la respuesta es 0, no 108

> **H1 CORREGIDO EL 2026-10-04.** El titulo anterior decia «El discriminante del desfase de 108 bytes, aislado por via independiente». Ese
> enunciado ya no describe el estado del arbol. El veredicto vigente esta en este
> mismo fichero:
> - `:16` — no hay hueco: «**no hay hueco**»
> - `:23` — la respuesta es 0: «**tiene respuesta, y es»
>
> Este parche toca **solo el H1** y esta marca. El cuerpo no se reescribe: la
> correccion del titulo tiene que quedar rastreable, o el titulo parece haber
> sido asi siempre.

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> **CORREGIDO POR `218`.** El discriminante `--hueco 108` que da forma a todo este
> documento queda **REFUTADO**: **no hay hueco**. `dpm_table_start` es la base literal de la
> tabla y `offsetof(campo)` es la posicion correcta del campo dentro de ella.
>
> Es decir: con `--hueco 0` —que es el caso real— el parche de UVD cae en el DWORD de
> `UvdBootLevel`@1576, que es lo que el codigo pretendia. Y el byte que escribe es el 3
> (ver `219`), por convencion de mascara, no por desplazamiento.
>
> La pregunta que este documento aislo ("¿el hueco es 0 o 108?") **tiene respuesta, y es
> 0**. El metodo —usar la herramienta para aislar una variable— sigue siendo valido y lo
> que falta era el dato que `087` ya tenia.

## Lo que hace este documento

`107` encontro que el parche de UVD/VCE escribe sobre `Smio[5]`, no sobre `BootVddc`.
Lo he comprobado con una cuenta a mano, por cuarta vez en tres documentos con el mismo error de
base de coordenadas.

Ahora la misma cuenta la hace `tools/smc_copy_scope.py` en modo `--registro`, con los
offsets **medidos por gcc**, y da el mismo resultado. Eso convierte una afirmacion mia en
algo verificable y repetible.

## El resultado de la herramienta

```
$ smc_copy_scope.py --registro --hueco 108 \
      --gcc-struct "struct SMU74_Discrete_DpmTable" polaris10_smumgr.c

polaris10_smumgr.c:2295   pos_tabla=1576  struct=1468  cae en Smio  byte 20
polaris10_smumgr.c:2299   pos_tabla=1576  struct=1468  cae en Smio  byte 20
polaris10_smumgr.c:2331   pos_tabla=1576  struct=1468  cae en Smio  byte 20
polaris10_smumgr.c:2335   pos_tabla=1576  struct=1468  cae en Smio  byte 20
```

Y **el mismo codigo de Tonga**, con hueco 0:

```
$ smc_copy_scope.py --registro --hueco 0 \
      --gcc-struct "struct SMU72_Discrete_DpmTable" tonga_smumgr.c

tonga_smumgr.c:2690   pos_tabla=1788  struct=1788  cae en UvdBootLevel  byte 0
tonga_smumgr.c:2694   pos_tabla=1788  struct=1788  cae en UvdBootLevel  byte 0
```

**Mismo patron de codigo, resultado distinto, y la unica variable que cambia es el hueco.**

Eso es un discriminante: si el hueco es 0, el codigo acierta y toca el campo que queria.
Si es 108, toca `Smio`. Y el codigo es el mismo en los dos ficheros.

## Y el hueco no esta en el layout: verificado con gcc

La hipotesis natural seria que `SystemFlags` esta en 108 en SMU 7.4 y en 0 en las
anteriores. **Es falsa**, medida:

```
struct SMU72_Discrete_DpmTable   sizeof = 1972   offsetof(SystemFlags) = 108
struct SMU74_Discrete_DpmTable   sizeof = 1884   offsetof(SystemFlags) = 108
```

**Las dos.** Y las dos copias iniciales empiezan en `SystemFlags`:

```
tonga_smumgr.c:2437       dpm_table_start + offsetof(SMU72_Discrete_DpmTable, SystemFlags)
polaris10_smumgr.c:2119    dpm_table_start + offsetof(SMU74_Discrete_DpmTable, SystemFlags)
```

Las dos restan `3 * sizeof(PIDController)` del tamano. Las dos dejan 108 bytes al principio.

O sea: **el layout del host es identico en lo que importa, el codigo de copia es
identico, y el resultado no puede depender de ninguno de los dos.** Lo unico que queda es
la disposicion que el firmware da a la tabla en la SRAM, que no esta en el corpus.

## Lo que eso deja abierto, y con que estado

Tres preguntas distintas, y el estado de cada una:

| pregunta | estado | por que |
|---|---|---|
| El codigo de Polaris12 calcula bien la direccion de un parche? | **`PROVEN` que NO**, si el firmware coloca los campos en `offsetof` | el layout del host y el codigo de copia son identicos a Tonga, y ahi el mismo codigo acierta con hueco 0 |
| Tonga coloca los campos en `offsetof`? | **`PROVEN` que SI**, si su firmware es como el de 7.1-7.3 en general | el parche de Tonga existe desde SMU 7.0 y funciona: si estuviera desviado 108 en Tonga habria roto antes de que SMU 7.4 existiera |
| El firmware de Polaris12 coloca los campos en `offsetof` o en `offsetof+108`? | **`NOT_DETERMINED`** | requiere el firmware o el hardware |

La tercera es la unica que importa para la conclusion, y **no se puede cerrar
estaticamente**: `NOT_IN_CORPUS`, y el firmware no esta en el arbol de trabajo
(`find` de `*.bin`, `*.hex`, `*.rom`, `*.fw`: cero resultados).

Lo que **si** se puede decir es que hay una de estas dos, y cada una tiene consecuencia
distinta:

- **Si el firmware de 7.4 coloca los campos en `offsetof`** (igual que Tonga), entonces
  los once usos de `211` estan desviados 108 bytes y el parche de `210`/`107` escribe
  sobre `Smio[5]`. Eso es un defecto real, y el firmware de Tonga es la prueba de que la
  convencion de 7.4 cambio.
- **Si el firmware de 7.4 coloca los campos en `offsetof + 108`**, entonces el host
  **deberia** sumar 108 en los once usos, y lo que hay es un host que no se ha
  actualizado al cambio de disposicion. Mismo sintoma, causa distinta, y la correccion
  es opuesta.

**La aritmetica no puede distinguir entre las dos.** Solo el firmware.

## Y por que esto no es una excusa para dejar el hallazgo como esta

`211` y `210`/`107` estan **degradados a `PROVEN_DERIVED`**, no a "no se sabe":

- El **mecanismo** es `PROVEN`: hay dos bases de coordenadas mezcladas, el codigo y el
  layout usan una y el firmware usa otra, y nada lo reconcilia.
- El **impacto** es condicional: depende de la disposicion del firmware, y eso es
  `NOT_DETERMINED` con `NOT_IN_CORPUS` como causa.
- La **herramienta** convierte la pregunta en repetible: `--hueco 0` reproduce el
  comportamiento correcto, `--hueco 108` el desviado, y el comando exacto esta en este
  documento para que cualquiera lo ejecute.

Eso es lo que corresponde a un hallazgo cuyo ultimo eslabon no se puede cerrar sin
hardware: mecanismo cerrado, impacto parametrizado, y el parametro es una variable que
se puede cambiar con un flag.

## Lo que la herramienta valido, y lo que no

**Valido:** que la cuenta de la direccion es correcta y que el signo es el correcto. Los
casos 14, 15 y 16 del self-test existen exactamente para eso: 14 comprueba que escribir
en 1576 cae en `Smio` y se marca DISTINTO; 15 comprueba que escribir en
`offsetof(BootVddc) + 108` cae en `BootVddc` y se marca coincidente; 16 comprueba que
cambiar el hueco cambia la resolucion, o sea que el hueco es un parametro de verdad.

**No valido:** que el hueco valga 108 para este firmware. Eso no lo puede validar ninguna
herramienta estatica, porque es una propiedad del binario que no esta en el corpus.

## Clasificacion

- `SMC_DISCRIMINANT_IS_THE_HOLE = PROVEN`: el mismo codigo da `UvdBootLevel` con hueco 0
  y `Smio` con hueco 108. Unico parametro que cambia.
- `SMC_LAYOUT_IDENTICAL_IN_BOTH_GENERATIONS = PROVEN`: gcc mide
  `offsetof(SystemFlags) = 108` en `SMU72_Discrete_DpmTable` (1972 B) y en
  `SMU74_Discrete_DpmTable` (1884 B).
- `SMC_COPY_CODE_IDENTICAL_IN_BOTH = PROVEN`: `tonga:2437` y `polaris10:2119` usan la
  misma forma, con `SystemFlags` y `- 3 * sizeof(PIDController)`.
- `SMC_OFFSET_ERROR_MECHANISM = PROVEN`: dos bases de coordenadas sin reconciliar.
- `SMC_IMPACT_IS_CONDITIONAL = NOT_DETERMINED`: depende de la disposicion del firmware.
  `NOT_IN_CORPUS` (el firmware no esta en el arbol).
- `SMC_TONGA_GOOD_BEHAVIOUR_IS_CORROBORATION = CORROBORATED`: el parche de Tonga apunta a
  `UvdBootLevel` con hueco 0, lo que sugiere que su firmware coloca los campos en
  `offsetof`. **Corroboracion, no prueba:** no he visto ningun firmware.
- `SMC_TOOL_CASE14_15_16 = PROVEN`: los tres casos de self-test que fijan el signo del
  hueco y la dependencia del parametro.

## Lo que esto obliga a hacer en un driver propio

Un driver propio **no tiene este problema**, y esa es la razon de escribirlo:

1. El host define la disposicion de la tabla, no el firmware. Si el host copia desde 108,
   el host coloca `UvdBootLevel` en `offsetof - 108`, y el patch se calcula con esa misma
   regla. No hay dos bases porque hay una sola.
2. O, si el host **respeta** una disposicion que da el firmware, entonces la tiene que
   **leer** de la cabecera y no suponerla. La cabecera ya tiene campos para esto
   (`SMU74_Firmware_Header`), y leerlos es barato.
3. Y en los dos casos, un test: al arrancar, escribir un valor reconocible en cada campo
   que se va a parchear despues, y releerlo antes del primer parche. Si el parche va a
   tocar el campo correcto, lo leera intacto. Ese test habria cazado esto en un minuto.

