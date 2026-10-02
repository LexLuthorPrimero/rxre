# 180 · Las ocho direcciones de registro del driver, cada una con su línea en el ASIC. Y el tipo de fallo que un `#define` con comentario de cola esconde

```
CLASSIFICATION=VERIFICATION+TOOLING · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

`171` dice que el primer eslabón vacío es MMIO, y `176` midió la mitad de su
contrato. Falta lo que decide si un offset del driver es una dirección o una
tentaliva: **cada `#define` de registro, con la línea del ASIC que lo respalda.**

`tools/regconst.py` lo automatiza. Resultado sobre el árbol actual:

```
PROVEN_POR_CITA   RX550_MM_VM_CONTEXT0_PTBA       0x54f   rx550_pm4.h:125
                   mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR 0x54f   gmc_8_1_d.h:636
PROVEN_POR_CITA   RX550_MM_VM_CONTEXT8_PTBA       0x50e   rx550_pm4.h:126
                   mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR 0x50e   gmc_8_1_d.h:607
PROVEN_POR_CITA   RX550_MM_VM_INVALIDATE_REQUEST  0x51e   rx550_pm4.h:127
                   mmVM_INVALIDATE_REQUEST           0x51e   gmc_8_1_d.h:615
PROVEN            MM_COMPUTE_DISPATCH_INITIATOR   0x2e00  test_pm4.c:194
PROVEN            MM_COMPUTE_NUM_THREAD_X         0x2e07  test_pm4.c:195
PROVEN            MM_COMPUTE_PGM_LO               0x2e0c  test_pm4.c:196
PROVEN            MM_COMPUTE_PGM_HI               0x2e0d  test_pm4.c:197
PROVEN            MM_COMPUTE_PGM_RSRC1            0x2e12  test_pm4.c:198

30 #define con valor leídos: 8 direcciones de registro, 22 no lo son
las 8 verificadas, 0 discrepantes
```

Las ocho verificadas **a mano después**, una por una, con `sed -n`. No porque
la herramienta no lo hiciera, sino porque esta sesión ya ha visto cómo una
herramienta nueva da un número plausible y falso: `drvchain.py` informó
`19 de 19 AUSENTE` sin haber cargado un solo fichero.

## 1 · El tipo de fallo que el comentario de cola escondía

Las tres constantes de GMC del driver se escriben así:

```c
#define RX550_MM_VM_CONTEXT0_PTBA  0x54f  /* gmc_8_1_d.h:636 */
```

**El comentario de cola es la procedencia.** Y una versión anterior del patrón
exigía fin de línea, con lo cual esas tres **no se leían**. Peor: las cinco de
`test_pm4.c` no llevan comentario y sí se leían. El resultado era

```
5 constantes: PROVEN 5
```

Cinco de ocho, todas en verde, y **sin decir que faltaban tres**. Y lo que se perdía eran **precisamente las que llevan cita**, que son las más
fiables: el único rasgo que distingue una constante verificada de una
supuesta desaparecía del recuento. Perder una tabla entera de «no he encontrado
nada» es mucho menos malo que perder un cinco de ocho sin decirlo.

Es un error de *denominador*, no de lectura: la respuesta seguía siendo verde
y correcta sobre lo que contaba. Solo faltaba el número de lo que no contaba.

## 2 · Verificar la cita es más fuerte que reconocer el nombre

El corpus llama a lo que el driver llama `MM_VM_CONTEXT0_PTBA`:
`mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR`. El emparejamiento por nombre da
`NO_EN_CORPUS` sobre un registro que existe, y eso es peor que no decir nada:
afirma una ausencia que es falsa.

La regla que funciona es la que el propio driver ya usa —**declarar de dónde
sale cada constante y comprobar esa declaración**:

```
PROVEN_POR_CITA        la línea citada existe y define ESE valor
CITA_CON_OTRO_VALOR    la línea citada existe y define OTRO valor
PROVEN                 el nombre resuelve con ese valor, en esta generación
VALOR_DISCREPANTE      el nombre resuelve con otro valor
GENERACION_DIERE       el valor existe, pero en el _d.h de otra generación
NO_EN_CORPUS           no se ha encontrado. NO es que el registro no exista
```

Para eso hace falta un **índice inverso por posición**: una cita dice fichero y
línea, no nombre. La primera versión buscaba la cita *dentro* de los candidatos
de nombre, y por eso no podía funcionar justo en los casos que más la
necesitan — los que no casan por nombre.

## 3 · Un `NO_EN_CORPUS` de más es peor que uno de menos

El criterio de «esto es una dirección» aceptaba cualquier nombre terminado en
`_REG`. Con eso, `RX550_PKT3_SET_SH_REG 0x76` —un **opcode de paquete**, no una
dirección— entraba en la tabla y salía `NO_EN_CORPUS`. Un `NO_EN_CORPUS` de más
no es ruido: dice «no lo he encontrado» cuando lo que ocurre es «esto no es de
esta clase», y son dos afirmaciones distintas.

Con la excluyente:

```
22 NO_ES_REGISTRO    opcodes de paquete, números de ioctl, IDs de PCI
```

Se cuentan **y se listan**, en vez de quedarse fuera en silencio. Por eso el
informe dice `30 #define leídos: 8 direcciones, 22 no lo son`: si el criterio se
queda corto mañana, se ve como una caída de cobertura y no como un corpus más
pequeño.

## 4 · El coste, que era de 470 MB

La primera ejecución **agotó quince minutos**. Dos causas, ambas reales:

- El patrón del corpus iba anclado (`^[ \t]*#[ \t]*define…[ \t]*$`) en modo
  multilínea sobre 476 cabeceras. Las anclas se comprueban a mano ahora —el `#`
  tiene que estar en el índice 0 o tras un salto de línea—, que es la misma
  garantía y cuesta una comparación.
- Y el motivo de verdad: **`texto[:ini].count("\n")` dentro del bucle**. Con
  ~194000 coincidencias sobre ficheros de 20 MB, contar el prefijo cada vez son
  miles de millones de operaciones *por fichero*. Como `finditer` devuelve las
  coincidencias en orden, basta un cursor que avanza. De quince minutos a
  **veinte segundos**.

No se recortó el corpus para que corriera: `include/asic_reg` pesa 470 MB, de los
cuales 385 son tablas generadas `_mask.h` que **sí** contienen 1391 `#define`
con valor. Excluirlas habría sido ganar tiempo comprando una pérdida de evidencia, y el
tiempo se recuperó por el algoritmo.

## 5 · Y un vector que probaba otra cosa

El selftest cubría el índice y nada más: **la lógica que clasifica no tenía una
sola comprobación**, que es como se deja que lo más importante sea lo único que
nadie rompe a propósito. Hay siete vectores del clasificador ahora, y dos tienen
dientes comprobados:

```
romper la comparación de valor     ->  FAIL  cita a una línea con otro valor
romper la excluyente de opcodes    ->  FAIL  un opcode de paquete no entra
restaurado                         ->  PASS (15 vectores)
```

El primer intento de romper la comparación **no llegó a romper nada**: mi
`sed` apuntaba a una versión anterior de esa línea. Pasó en verde sin haber
probado el defecto. Es la tercera vez en esta sesión que un vector pasa por el
motivo equivocado, y la razón es siempre la misma —probaba el recorrido, no la
lógica—.

## Procedencia

```
tools/regconst.py                15 vectores, 7 del clasificador
gmc_8_1_d.h:607  :615  :636      los tres de GMC, verificados con sed
gfx_8_0_d.h:1281 1288 1293 1294 1299   los cinco de compute, idem
findings/176      tamano de BAR2 = 2 MiB, el corte de FUERA_DE_BAR2
findings/147      la clase GENERACION_DIERE, que es lo que hace
                  RX550_SDMA_OP_PTEPDE con su cita a vega10
findings/171      por que esto es lo que fija la prioridad siguiente
07-DRIVER/tests/test_pm4.c   208 checks, 0 failures
```

## CORRECCION POSTERIOR

Ninguna. Y una advertencia sobre el alcance, porque es la que más mal puede
usarse: **esto verifica el valor, no el uso**. Que `0x54f` sea el offset correcto
de `PTBA` es `PROVEN`. Que el driver lo escriba donde toca, en el orden que
GMC exige y con el campo de bits que toca, es otra pregunta, y la responden
`findings/043`, `findings/115`–`120` y `test_pm4.c`.

Una dirección verificada es el suelo del `§IMPLEMENTATION_GATE`, no su cierre.

Y lo que queda abierto, con su causa nombrada:

```
PENDIENTE=que bloque de registros vive en que BAR, y por tanto el desplazamiento
          dentro de BAR2 al que hay que sumar cada offset ya verificado
  | HALLAZGO=180-las-ocho-direcciones-de-registro-con-su-linea-en-el-asic.md
  | ESTADO=NOT_IN_CORPUS
  | NECESITA=un corpus con el nucleo de Linux: struct amdgpu_ip_block_version
  |          (amdgpu_ip.h:108) no lleva indice de BAR, no hay pci_iomap en
  |          ningun arbol de amdgpu, y PCI_BARn_* solo aparece en cabeceras
  |          locales de drivers no relacionados. Ver findings/176 §3
  | ALCANZABLE_SIN_ROOT=si
```
