# 1030 · La secuencia del GART es un PLAN de 34 operaciones, y para construirlo hicieron falta 27 campos que no existían

`CLASSIFICATION=MEASUREMENT` · `TRACK=STATIC + HOST_OBSERVATION`
`CORPUS=RESEARCH/kernelbuild/linux-7.1.3` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`WORK_CLASS=IMPLEMENTATION` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=6`
`RUNTIME=NOT_RUN` · `GPU INTACTA`

---

## El cambio de estado

Antes de este trabajo el driver podía *expresar* la secuencia del GART
(`rx550_vmid0_regs_build()`, 119 aserciones) pero no *calcularla*: los 42 campos
que la referencia escribe no existían como datos, y no había ninguna función que
devolviera la secuencia.

Ahora:

| | antes | ahora |
|---|---|---|
| `rx550_gart_seq_build()` | no existe | 34 operaciones, en orden, validadas |
| campos en `rx550_reg_fields[]` | 28 | **55** |
| registros de la secuencia en la tabla | 10 de 20 | **20 de 20** |
| la secuencia se puede comparar con el corpus | no | **sí, 34 de 34** |

**Y no se ejecuta.** Devuelve un plan. Es la función más crítica del componente
y una ejecución equivocada deja el GART mal puesto sin avisar: un plan se
compara con `gmc_v8_0.c:829-947` en userspace, y eso no se puede hacer con la
GPU delante.

## Los 27 campos que faltaban, y de dónde salieron

`rx550_reg_fields[]` tenía 28 campos y sólo de **dos** registros. Los cinco
restantes no tenían ni un campo:

```
VM_L2_CNTL             7    VM_L2_CNTL2    2    VM_L2_CNTL3    3
VM_L2_CNTL4           12    VM_CONTEXT0_CNTL  3
```

Generados, no escritos de memoria. Tres decisiones que gobiernan cómo:

**El alcance son los headers que incluye el propio TU de la referencia.**
`gmc_v8_0.c:36-48` incluye `gmc_8_1_sh_mask.h`, `bif_5_0`, `oss_3_0`,
`dce_10_0`. Sólo esos. La primera versión-barrió `include/asic_reg/**/*_sh_mask.h`
y encontró 47379 símbolos… de **41 ficheros**, entre ellos `gmc_8_2_sh_mask.h`:
GFX8.2, otra generación, que **sobreescribió en silencio** los valores de
GFX8.1 porque un `dict` resuelve por orden de inserción. Con el alcance correcto:
**47379 símbolos, 0 colisiones con valor distinto.**

**La convención de los sufijos es asimétrica**: `<REG>__<FIELD>_MASK` con **un**
guion bajo, y `<REG>__<FIELD>__SHIFT` con **dos**. Buscar `__MASK` da 0
resultados sobre 27 campos que sí tienen máscara.

**El sufijo `L`.** Las máscaras del corpus son `0x00000001L`. Una expresión
regular que no lo admita no encuentra nada.

Con eso: 27 campos, **27 con `__SHIFT` declarado en el header**, y el invariante
`(mask >> shift) == 2^ancho − 1` sin una sola discrepancia.

## Los tres campos cuyo valor NO es un literal

Sólo tres, y no son una excepcion:

```
gmc_v8_0.c:866   field = adev->vm_manager.fragment_size;
gmc_v8_0.c:868   VM_L2_CNTL3.BANK_SELECT               = field
gmc_v8_0.c:869   VM_L2_CNTL3.L2_CACHE_BIGK_FRAGMENT_SIZE = field
gmc_v8_0.c:933   VM_CONTEXT1_CNTL.PAGE_TABLE_BLOCK_SIZE = block_size - 9
```

Un `uint32_t` no puede ser `fragment_size`. Quedan `RX550_FIELD_NO_CORPUS` en la
tabla, y el constructor los sustituye desde sus parámetros por una **lista
explícita** de tres entradas.

La lista es explícita y no una regla del tipo «*si no hay valor, usa el
fragment_size*». Con esa regla, un campo que se añadiera mañana y todavía no
tuviera valor decidido recibiría un 9 silencioso en un registro de
fragmentación. Con la lista, **da error**.

Y la lista fue de **dos** en la primera versión: le faltaba
`PAGE_TABLE_BLOCK_SIZE`, que ya constaba `NO_CORPUS` desde antes. El síntoma fue
que componer `mmVM_CONTEXT1_CNTL` —el último registro de la secuencia—
devolvía error, y el error se leía como «a este registro le faltan campos» cuando
lo que faltaba era una fila en una lista de tres.

## `RX550_FIELD_NO_CORPUS` significa dos cosas, y el valor solo no las distingue

Éste fue el fallo que costó más:

| procedencia | valor | qué hay que hacer |
|---|---|---|
| `PROVEN_CORPUS_WRITES` | `NO_CORPUS` | sustituir por el parámetro |
| `DECLARED_NOT_WRITTEN` | `NO_CORPUS` | **no tocar**: es lo que preserva el RMW |

La primera versión trataba los dos como el primero y devolvía error en los
**siete** registros RMW. Los doce `VMC_TAP`, los siete `_INTERRUPT`, los cinco
`_SAVE` y `ECO_BITS` son del segundo tipo: el corpus no los escribe, y el RMW
debe **dejarlos como están**, que es justo lo que hace el `RREG32`.

Y haberlos tratado como el primero habría sido peor: los tres simbólicos se
quedarían en `0xFFFFFFFF` recortado, es decir **fragmentación y tamaño de bloque
puestos a su valor máximo** por un RMW que sólo pretendía preservar lo demás.

## Cinco bugs reales, y los cuatro primeros los encontró el test

### 1. Una tabla de 19 entradas para 20 posiciones

`rx550_gart_rmw_de[]` mapeaba posición-del-orden → registro-RMW, y le faltaba
una entrada. En C una lista de 19 inicializadores para un array de 20 **se queda
corta en silencio** y el resto toma el valor cero. Consecuencia: desde la
posición 9 todo iba corrido una posición.

```
pos  9  mmVM_CONTEXT0_CNTL2     marcada como RMW      (es un literal 0)
pos 10  mmVM_CONTEXT0_CNTL      marcada como ciega    <-- esta
pos 19  mmVM_CONTEXT1_CNTL      se salía de la tabla
```

**Un `_Static_assert` de longitud no lo habría visto.** Ahora la tabla va con
designadores de índice explícitos, y el patrón no se puede equivocar.

### 2. El bucle de contextos iba al final

El comentario del código describía la posición correcta (`gmc_v8_0.c:910-916`,
entre `CTX1_PT_END` y `CTX1_PROT_FAULT`) y el código emitía las 19 explícitas,
después las 15 del bucle, y no volvía a emitir las tres últimas. El plan tenía
34 operaciones, **contaba bien**, y el orden estaba equivocado.

### 3. `mmVM_CONTEXT1_CNTL2` = 4, no 0

`gmc_v8_0.c:923` escribe un **4**. `mmVM_CONTEXT0_CNTL2` escribe un 0
(`L891`). Dos `case` que compartían el mismo valor, y el segundo no existía:
cayía en `default:` y pedía composición de campos a un registro sin campos.

### 4. `CTX1_PROT_FAULT` con el valor de `CTX0_PT_BASE`

Estaban en el mismo `case`, y los dos valían `table_pfn`. No: la página dummy va
a **los dos** contextos (`L889` y `L921`). Ponerle la raíz de la tabla de
páginas haría que los faults del contexto 1 apareciesen *dentro de la propia
tabla* como si fueran una página mapeada.

### 5. Un `NULL` desreferenciado, encontrado por una mutación

`rx550_gart_orden[]` tiene una ranura `NULL` para la posición del bucle. Cuando
la gestión del bucle estaba al final, la salvaba un `if (... == NULL) continue`
colocado **antes** de llamar a `rx550_gart_reg_index()`. Al mover el bucle a su
sitio, ese `continue` desapareció y nadie lo sustituyó.

Desactivar la rama del bucle con una mutación:

```
las dos guardas puestas  ->  exit 1,  4 FAIL
las dos quitadas        ->  SIGSEGV,  exit 139
```

**Ningún test cubre esas dos guardas**, porque en código correcto la ranura vacía
no se alcanza, y quitar sólo una de las dos no lo detecta nadie. Se quedan por
el motivo medido: el hardware no reintenta un `SIGSEGV` y un código de error sí.
El camino para resolverlo de verdad ya existe —que la tabla de orden deje de
llevar un `NULL` como centinela— y entonces sobrarán.

## Un error mío de aritmética, dos veces, y por que no lo detecte antes

```
mi conteo:   ventana del GART >> 12  =  267452415
             ventana del VM          =   16777216
mi regla:    if ((gart_end >> 12) >= max_pfn) return -GEOMETRY;
```

**La regla rechazaba la geometría real de esta tarjeta.** Y no podía no hacerlo:
la ventana del GART está en `0xFF00000000`, a unos 4 GiB del tope de 40 bits, y
la del VM es de 16.7M páginas. El contexto 0 existe precisamente para dejar que
la GART viva por encima del límite del VM: su `PAGE_TABLE_DEPTH` es 0 y con una
sola tabla la dirección se usa como índice directo.

Las **dos ventanas son de dos contextos distintos y el corpus no las anida**:
`L886-887` para el contexto 0, `L907-908` para el contexto 1. No hay ninguna
relación entre `gart_end` y `max_pfn`.

Lo que sí se comprueba, y es lo único medido: los dos extremos van a un
`PHYSICAL_PAGE_NUMBER` de 28 bits.

Y el segundo error fue mío también, y en la dirección contraria: `+8 GiB` para
mover la ventana **rebasa los 40 bits** (`0xFF00000000 + 0x200000000 =
0x10100000000 > 2^40`), así que el constructor lo rechazaba y el fallo se leía
como «el plan no responde a la geometria». La ventana del GART **no se puede
mover por encima de `0xFFC0000000`**, y eso no estaba escrito en ninguna parte.

## Una diferencia de un caracter que no se ve

Entre la definición y el llamado de `rx550_gart_composer`:

```
definición:  rx550_gart_compo-s-er
llamado:     rx550_gart_compo-n-er
```

Idénticos a la vista. gcc: *implicit declaration* + *defined but not used*, las
dos a la vez, que es una combinación imposible en un fichero bien formado y por
eso hubo que medir byte a byte en vez de seguir leyendo el diagnóstico.

Se renombró a `rx550_gart_rmw_componer`. La lección no es el nombre: es que **`sed`
y `grep` con acentos y contipografías de una letra no son herramientas
confiables para verificar que dos identificadores son el mismo**, y que un
diagnóstico de compilador que se contradiga a si mismo es un dato sobre la
herramienta, no sobre el código.

## Verificación

**Un oráculo independiente.** Las 34 escrituras se transcribieron otra vez en
Python desde `gmc_v8_0.c:829-947`, sin mirar el driver, y se compararon con lo
que produce el C:

```
del plan: 34   del oráculo: 34   diferencias: 0
VEREDICTO: COINCIDEN las 34
```

No es el test comparándose a sí mismo: es una segunda transcripción del corpus.

**`tests/test_gart_seq.c`, 55 aserciones.** Las 34 operaciones con su registro y
su orden, los 15 del bucle contra `rx550_mmio_ctx_pt_base_index()`, los valores
derivados de la geometría, que los RMW **conservan** los bits de fuera del campo,
y que la geometría mueve el plan.

**Seis vectores de test míos estaban mal**, y por qué están escritos:

| vector | lo que pedía | lo correcto |
|---|---|---|
| vmid 1 | `0x54f` | `0x550` — `0x54f` es el ancla del **contexto 0** |
| `CTX1 PAGE_TABLE_DEPTH` | `0x6` | `0x2` — valor 1 en un campo de 2 bits es `0b01` en los bits 1..2 |
| `L2_CNTL4` | registro entero a 0 | los **doce** taps a 0 y lo demás conservado |
| `S3 destino intacto` | `!=` | `==` — estaba al revés y pasaba por el motivo equivocado |
| `S2 ventana` | `+8 GiB` | `+1 GiB`, porque `+8` rebasa los 40 bits |
| `S2 END` | «no se mueve» | sigue a la ventana entera |

**Self-test, cinco mutaciones, cinco detectadas:**

```
orden del bucle cambiado      ->  4 FAIL   (y sin SIGSEGV)
campo simbólico puesto a 0    ->  4 FAIL
PAGE_TABLE_DEPTH del ctx0 sin tocar ->  1 FAIL
campos declarados-no-escritos tratados como simbólicos -> 4 FAIL
las dos guardas NULL quitadas  ->  SIGSEGV,  exit 139
```

La quinta no la detecta ningún test **y es que no hay nada que detectar**: es
inalcanzable en código correcto. Queda anotado como tal, con la razón por la que
se conserva.

**La semilla de los `CNTL` era insuficiente** y el self-test lo enseñó:
arrancaban en `0x....0000`, y los bits 1 y 2 de `PAGE_TABLE_DEPTH` ya valían 0.
Con esa semilla, «poner `PAGE_TABLE_DEPTH=0`» y «no tocarlo» dan el mismo número.
Quitando esa asignación, **0 de 55** comprobaciones fallaban. Ahora el contexto 0
arranca con profundidad 3 y el contexto 1 con 2, ninguno de los dos es el valor
que se escribe, y quitar la asignación da 1 FAIL.

## Lo que NO dice

- **No dice que el hardware acepte la secuencia.** No se ha ejecutado. Es
  `RUNTIME_REQUIRED` y sigue siendo la única cosa que este trabajo no puede
  decir.
- **No dice que los 27 campos basten.** Faltan los campos de
  `mmVM_CONTEXT1_CNTL2` y de `mmVM_INVALIDATE_REQUEST`, que no los escribe
  `gmc_v8_0_gart_enable()` por `REG_SET_FIELD`, y eso está anotado.
- **No dice que `PAGE_TABLE_BLOCK_SIZE` del contexto 0 importe.** Sigue sin
  determinarse, por el motivo del finding 1028: la secuencia es RMW y lo que
  hubiera queda. `block_size = 9` da `9 − 9 = 0`, y el constructor lo rechaza
  como error de geometría en vez de escribir un `0xFFFFFFFF` recortado.

## Trazabilidad

- Secuencia: `amdgpu/gmc_v8_0.c:829-947`
- Máscaras: los cuatro `*_sh_mask.h` de `gmc_v8_0.c:36-48`, con el alcance tomado
  de ese include y no del árbol de directorios
- Contexto 0 ya construido: finding `1028`; página dummy: finding `1029`
- Primitiva de RMW por campo: finding `1028`
- Prefijo de numeración: 1030, reservado antes de escribir