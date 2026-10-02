# 064 · El mapa de bits completo de `VM_CONTEXT*_CNTL` en GFX8: dónde cae F3 y dónde caen los 6 faults de protección

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC · CORPUS=RESEARCH/working/linux-7.1.3
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · WORK_CLASS=READ_ONLY/EVIDENCE
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**F3 pasa de `NOT_DETERMINED` a `PARTIAL`**, no a cerrado: el campo queda
**acotado por su geometría exacta** y se separa el que es software del que es
hardware. Antes sólo se sabía que eran "2 bits, 4 valores, 2 usados, 5
cabeceras". Ahora se sabe qué bits son, qué se escribe en ellos, y qué hace el
contexto structuralmente distinto en cada caso.

También entrega §A sin coste: **los 6 tipos de fault de protección** están en el
mismo registro, con sus posiciones exactas y con el recuento que demuestra que el
conjunto está cerrado.

## La geometría del campo, en la cabecera correcta

**Aquí hay un aviso de método que va antes que el resultado.** Los registros GFX8
viven en `include/asic_reg/gmc/gmc_8_1_sh_mask.h`. No en `gmc_v8_0.h`, no en
`mmhub_1_8_0_sh_mask.h`. Busqué primero en `mmhub/` porque `PAGE_TABLE_DEPTH`
también existe allí, y durante varias llamadas estuve leyendo la tabla de bits
equivocada.

Y esa lectura equivocada dio un resultado que parecía plausible y era falso:

| campo | `mmhub_1_8_0_sh_mask.h` | `gmc_8_1_sh_mask.h` (la buena) |
|---|---|---|
| `PAGE_TABLE_DEPTH` | mask `0x6`, shift `0x1` | mask `0x6`, shift `0x1` |
| `PAGE_TABLE_BLOCK_SIZE` | mask `0x78`, shift `0x3` | mask `0xf000000`, shift `0x18` |

`PAGE_TABLE_DEPTH` coincide en ambas porque el registro se copió de MMHUB a GMC
en GFX8. **`PAGE_TABLE_BLOCK_SIZE` cambia de bits 3-6 a bits 24-27**. O sea: la
cabecera de MMHUB de GFX8 no describe el registro que escribe `gmc_v8_0.c`, y
tomarla como fuente produce un mapa de bits plausible y equivocado. Por eso
`include_closure.py` dice que GFX8 tiene seis cabeceras de registro: no es una
advertencia de estilo, es la diferencia entre el número correcto y uno equivocado.

## F3 · el campo y sus dos valores

```
gmc_8_1_sh_mask.h:6583   VM_CONTEXT0_CNTL__PAGE_TABLE_DEPTH_MASK         = 0x6
gmc_8_1_sh_mask.h:6584   VM_CONTEXT0_CNTL__PAGE_TABLE_DEPTH__SHIFT       = 0x1
gmc_8_1_sh_mask.h:6623   VM_CONTEXT0_CNTL__PAGE_TABLE_BLOCK_SIZE_MASK    = 0xf000000
gmc_8_1_sh_mask.h:6624   VM_CONTEXT0_CNTL__PAGE_TABLE_BLOCK_SIZE__SHIFT  = 0x18
```

El ancho se calcula desde la máscara, no se supone: `0x6` es un bloque de
**2 bits contiguos** en la posición **1**, o sea bits **[1:2]**, cuatro valores
posibles (0, 1, 2, 3).

Una corrección a un cálculo mío: un script de comprobación mío reportó "3 bits"
para `mask=0x6`. Es incorrecto: `bit_length()` devuelve la posición del bit más
alto más uno, no el ancho. El ancho de `0x6` es 2, y coincide con lo que la
frontera ya afirmaba.

**GFX8 sólo escribe 0 y 1.** Los valores 2 y 3 existen en el campo y ningún
código de este ASIC los usa. Queda registrado como `NOT_DETERMINED` en sentido
estricto: que el driver no los escriba no prueba que el hardware no los interprete.

## Los dos valores, y la diferencia estructural que los acompaña

`gmc_v8_0_gart_enable` escribe el campo dos veces, y cada vez en un contexto
distinto. Lo que separa los dos casos **no es sólo el valor del campo**:

| | VMID 0 (GART) | VMID 1-15 (userspace) |
|---|---|---|
| `PAGE_TABLE_DEPTH` | `0` (`gmc_v8_0.c:895`) | `1` (`gmc_v8_0.c:925`) |
| `PAGE_TABLE_START_ADDR` | `gart_start >> 12` | `0` |
| `PAGE_TABLE_END_ADDR` | `gart_end >> 12` | `max_pfn - 1` |
| `CNTL2` escrito con | `0` | `4` |
| rangoEffective | acotado a la GART | VM entera |

Esto es lo que hace que la hipótesis natural ("0 = sin page table, 1 = con page
table") **no encaje**: ambos contextos tienen page table. VMID 0 escribe su
`PAGE_TABLE_BASE_ADDR` en `gmc_v8_0.c:889` igual que VMID 1.

Lo que sí distingue a VMID 0 es que su page table está **acotada por un rango
START/END** y la de userspace cubre `0 .. max_pfn-1` sin cota superior real.

**Y el dato que mas acota la semántica**: `VM_CONTEXT1_CNTL2` tiene un campo
llamado `CLEAR_PROTECTION_FAULT_STATUS_ADDR`, y otro llamado
`ENABLE_CLEAR_PROTECTION_FAULT_STATUS_ADDR_WHEN_INVALIDATE_CONTEXT`. Eso ata el
bit 1 de `CNTL2` a la semántica de invalidate. Los dos valores `0` y `4` que
escribe el driver **difieren en el bit 2**, que es
`ENABLE_INTERRUPT_PROCESSING_FOR_SUBSEQUENT_FAULTS_PER_CONTEXT`.

```
gmc_8_1_sh_mask.h:6687   VM_CONTEXT1_CNTL2__CLEAR_PROTECTION_FAULT_STATUS_ADDR_MASK                     = 0x1   shift 0x0
gmc_8_1_sh_mask.h:6691   VM_CONTEXT1_CNTL2__ENABLE_CLEAR_..._WHEN_INVALIDATE_CONTEXT_MASK               = 0x2   shift 0x1
gmc_8_1_sh_mask.h:6692   VM_CONTEXT1_CNTL2__ENABLE_INTERRUPT_PROCESSING_FOR_SUBSEQUENT_FAULTS_MASK     = 0x4   shift 0x2
```

El código escribe `0` en VMID 0 y `4` en userspace, o sea **activa el
procesamiento de interrupts por faults posteriores para userspace y no para la
GART**. Eso es comportamiento de interrupt coherente con lo que ya está
documentado sobre IH, y es la diferencia funcional que el bit 2 realmente
introduce. No es la misma cosa que la profundidad de la page table: son campos
distintos del registro CNTL y CNTL2.

## §A · los faults de protección en GFX8, con posición exacta y conjunto cerrado

El mismo registro `VM_CONTEXT*_CNTL` trae, para cada tipo de fault, dos campos:
uno de `DEFAULT` (qué hacer por omisión) y otro de `INTERRUPT`. Los tipos
encontrados en `gmc_8_1_sh_mask.h` para `VM_CONTEXT0_CNTL`:

Conteo por tipo de tipo de fault en `gmc_8_1_sh_mask.h`, para `VM_CONTEXT0_CNTL`
(solo lo que **existe**):

```
  VALID_PROTECTION_FAULT_ENABLE_*     6 defines
  READ_PROTECTION_FAULT_ENABLE_*      6 defines
  WRITE_PROTECTION_FAULT_ENABLE_*     6 defines
  EXECUTE_PROTECTION_FAULT_ENABLE_*   6 defines
  DUMMY_PAGE_PROTECTION_FAULT_ENABLE_*  4 defines
  RANGE_PROTECTION_FAULT_ENABLE_*     4 defines
```

**No hay 8 tipos: hay 6.** Y dos correcciones sobre lo que escribí en la primera
redacción de esta nota:

- `SECURE_PROTECTION_FAULT_ENABLE_*` **no existe en GFX8**. Existe en MMHUB y en
 ASIC posteriores; lo había leído de la cabecera equivocada.
- `RETRY_PERMISSION_OR_INVALID_PAGE_FAULT` y `RETRY_OTHER_FAULT` **tampoco
  existen en ninguna cabecera `gmc_*`**. Sólo en `mmhub_1_8_0_sh_mask.h`, con
  máscara `0x80` y `0x100`. No son parte de este registro en GFX8.

Verificado por recuento sobre las cuatro cabeceras GFX8 (`gmc_8_1_sh_mask.h`,
`gmc_8_1_d.h`, `gmc_8_2_sh_mask.h`, `gmc_8_2_d.h`): cero apariciones de
`__SECURE_PROTECTION` y cero de `__RETRY_`.

Eso **deja §A más cerrado de lo que parecía, no menos**: los 6 tipos que sí
existen son el conjunto completo de faults de protección de GFX8, y no hay un
sétimo campo escondido. El recuento por tipo es la forma de saberlo, y es la que
impide el error que acabo de cometer.

Bits con posición exacta, de los que sí existen:

```
  RANGE_PROTECTION_FAULT_ENABLE_INTERRUPT_MASK      = 0x8    shift 0x3
  RANGE_PROTECTION_FAULT_ENABLE_DEFAULT_MASK        = 0x10   shift 0x4
  DUMMY_PAGE_PROTECTION_FAULT_ENABLE_INTERRUPT_MASK  = 0x40   shift 0x6
```

`ENABLE_CONTEXT` ocupa el bit 0 y `PAGE_TABLE_DEPTH` los bits [1:2], así que el
layout arranca contiguo desde el 0.

**Por qué esto importa para §A.** La frontera A separa "Linux escribe este bit"
de "hardware interpreta este bit así". Con este mapa, la primera mitad está
`PROVEN` para GFX8 con posición exacta y **conjunto cerrado**, y la segunda
sigue `NOT_DETERMINED` con una lista precisa de 6 campos × 2 modos (DEFAULT e
INTERRUPT) que consultar en la spec primaria. Antes el trabajo de §A exigía
localizar los campos y todavía podía quedar alguno sin ver; ahora el recuento los
cierra.

La conexión con `noretry` en la ruta de VM **no se sostiene en GFX8**: los bits
de reintento no están en este registro. Sigue habiendo una política de reintento
en software, pero no es un campo de `VM_CONTEXT*_CNTL` en este ASIC.

## Lo que NO se cierra

| Afirmación | Estado | Por qué |
|---|---|---|
| `PAGE_TABLE_DEPTH` ocupa bits [1:2] de `VM_CONTEXT*_CNTL` | `PROVEN` | máscara y shift, cabecera GFX8 |
| GFX8 escribe 0 para VMID 0 y 1 para userspace | `PROVEN` | dos escrituras, misma función |
| Los valores 2 y 3 no los usa este driver | `PROVEN` (software) | barrido del corpus |
| Que el hardware no interprete 2 y 3 | `NOT_DETERMINED` | requiere spec primaria |
| Qué significa 0 vs 1 **en el hardware** | `NOT_DETERMINED` | ver abajo |
| Los 6 tipos de fault y su posición | `PROVEN` (software) | cabeceras |
| El conjunto de faults está cerrado (6, no 8) | `PROVEN` | recuento sobre las 4 cabeceras gmc_* |
| `SECURE_*` y `RETRY_*` existen en GFX8 | `REFUTED` | cero apariciones en gmc_8_1 y gmc_8_2 |
| Semántica de hardware de cada fault | `NOT_DETERMINED` | requiere spec primaria |

**F3 sigue abierta en su parte nuclear.** Lo que aquí se cierra es la
geometría. La pregunta "¿qué significa cada valor para el hardware?" no se
responde leyendo el driver: el driver escribe el valor, y eso es software
behaviour. Los dos candidatos que quedan son:

1. `DEPTH` cuenta niveles de page table, y 0 significaría "GART plana". La
   evidencia **en contra**: VMID 0 sí escribe `PAGE_TABLE_BASE_ADDR` y sí tiene
   rango START/END acotado, que es lo que hace una page table.
2. `DEPTH` selecciona el modo de cálculo de traducción del walker para el
   contexto. Esto es consistente con lo observado, pero no está demostrado.

Para cerrar F3 hace falta la especificación primaria de MMHUB/GMC, o un
discriminante de runtime. **No he buscado fuera del corpus**: `CORPUS_
COMPLETENESS_CHECK` dice que primero se agota lo que hay, y F3 ya tiene ahora
todo lo que el corpus puede dar.

## Procedencia

- `CORPUS` — `gmc_8_1_sh_mask.h`, `gmc_v8_0.c`, `gmc_v8_0_gart_enable`.
- Sin `RUNTIME`, sin lectura de la GPU, sin escrituras.
- Nota de método: la primera lectura de este trabajo usó
  `mmhub_1_8_0_sh_mask.h` y dio `PAGE_TABLE_BLOCK_SIZE` en bits 3-6. Está
  corregido arriba. El error no cambió ninguna conclusión publicada porque no se
  publicó, pero es exactamente la clase "asumí el nombre antes de mirar".