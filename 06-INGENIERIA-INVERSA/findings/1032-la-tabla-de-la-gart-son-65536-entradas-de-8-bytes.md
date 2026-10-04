# 1032 · La tabla de la GART son 65536 entradas de 8 bytes, y eso se sabe sin mirar el hardware

`CLASSIFICATION=MEASUREMENT` · `TRACK=STATIC + HOST_OBSERVATION`
`CORPUS=RESEARCH/kernelbuild/linux-7.1.3` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`WORK_CLASS=IMPLEMENTATION` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=2`
`RUNTIME=NOT_RUN` · `GPU INTACTA`

---

## Por qué esto es un caso aparte

`rx550_gart_write.h:14` lo dice desde antes de este trabajo:

> *No es un allocator. No crea `gart.bo`. No decide su tamaño, su dirección ni su contenido.*

Y el plan de la secuencia (`rx550_gart_seq.c`) programa

```
mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR = tabla >> 12          gmc_v8_0.c:888
```

es decir, **dice dónde está la tabla y no la crea**. A propósito: el plan se
construye y se compara con el corpus sin tocar nada.

Lo que faltaba era lo otro, que es una aritmética de tres pasos:

```
amdgpu_gart.c:533    gart.num_gpu_pages    = gmc.gart_size / 4096
gmc_v8_0.c:960        gart.table_size       = gart.num_gpu_pages * 8
gmc_v8_0.c:961        gart.gart_pte_flags   = AMDGPU_PTE_EXECUTABLE
amdgpu_gart.c:270     la tabla se pide a VRAM, alineada a 4096
amdgpu_gart.c:276     memset_io(ptr, gart_pte_flags, table_size)
```

## La cuenta, con los números de esta máquina

`gmc.gart_size = 256 MiB`, del log del kernel de esta tarjeta:

```
num_gpu_pages = 268435456 / 4096   =  65536
table_size    = 65536 * 8          = 524288   =  512 KiB
valor inicial = AMDGPU_PTE_EXECUTABLE = 1ULL << 4 = 0x10   (amdgpu_vm.h:65)
```

**Y las 512 KiB van en VRAM**, no en memoria del sistema. `amdgpu_gart.c:110-118`
dice que la tabla en RAM es *«for ASICs that don't have dedicated VRAM»*, y esta
tarjeta tiene 2 GiB, así que le toca `amdgpu_gart_table_vram_alloc()`
(`amdgpu_gart.c:263-278`).

> **Esta es la primera pieza del camino del GART que se sabe SIN ejecutar nada.**
> Todo lo demás depende de un reset o de un firmware. Esto sale de una división y
> una multiplicación sobre un número que está en el log de esta máquina.

## El `*8` es el número que más fácil se confunde

`g.bytes = g.paginas << 3`, y hay tres cosas que lo sostienen:

1. **El corpus lo dice**, `gmc_v8_0.c:960`: `* 8`. Con 4, la tabla ocuparía
   256 KiB y seguiría siendo un número plausible. El test lo distingue
   explícitamente:

```c
uint64_t con_cuatro = ESPERADAS_PAGS * 4u;
CHECK_EQ(con_cuatro, ESPERADAS_BYTES / 2u, "con 4 bytes la mitad");
CHECK(con_cuatro != ESPERADAS_BYTES,      "el tamaño del corpus NO es el de 4");
```

2. **La coherencia con el resto del componente**: `rx550_vmid1_pte_page`
   (`rx550_vmid1_pgt.h`) ya usa `uint64_t *entries`. Las entradas de la GART son
   palabras de 64 bits, igual que las PTE.

3. **Por qué 64 y no 40**: es la misma razón por la que
   `rx550_vmid1_pgt.h:62-81` separa PDE de PTE en dos tipos. Los flags de PTE
   (`READABLE` bit 5, `WRITEABLE` bit 6) caen **dentro** de `39:1`, así que no
   pueden convivir con una dirección en la misma palabra de 40 bits.

## `AMDGPU_PTE_EXECUTABLE = 0x10`, y no cero

Una GART cuyas 65536 entradas valen 0 es una GART donde todas las páginas están
inválidas. Eso es un estado válido **después de un reset**, y no el estado desde
el que el driver arranca. La diferencia es **un bit**, y el `memset_io` de
`amdgpu_gart.c:276` lo pone.

El test lo distingue de `calloc`:

```c
memset(tabla, 0, ESPERADAS_PAGS * sizeof(uint64_t));
CHECK(tabla[0] == 0u,                        "calloc deja la tabla a cero");
CHECK(RX550_GART_PTE_EXECUTABLE != 0u,       "el valor del corpus NO es cero");
```

Y recorre las 65536 comparando contra el valor, contando las que no cuadran, y
comprueba que el contador de diferencias es 0 — para que un fallo por un error de
rango en el propio bucle no se lea como «el contenido es correcto».

## El truncamiento que se rechaza en vez de copiar

`amdgpu_gart.c:533` trunca:

```c
adev->gart.num_gpu_pages = adev->gmc.gart_size / AMDGPU_GPU_PAGE_SIZE;
```

Con un `gart_size` de 3 páginas y 1 byte salen 3 páginas, la tabla ocupa 24
bytes, y **la cuenta cuadra igual**. Nadie lo ve, porque el error es de 4095
páginas —32 MiB de ventana— repartido en entradas de la tabla.

`rx550_gart_tabla_geom()` **rechaza** el caso en vez de copiar el truncamiento, y
dice por qué en el propio código. Un módulo que copia un redondeo del corpus
hereda el redondeo sin heredar el motivo.

## Tres rechazos, con motivos distintos

| entrada | motivo | error |
|---|---|---|
| `gart_size == 0` | una GART de cero bytes no existe | `ERR_TAMANO` |
| `gart_size % 4096 != 0` | el corpus trunca; aquí se exige exactitud | `ERR_TAMANO` |
| `gart_size > 256 MiB` | la política del propio driver, `rx550_vmid0_gart.h:72` | `ERR_TAMANO` |

Y los bordes se comprueban por los dos lados:

```
4096            -> 1 entrada,  8 bytes     (mínimo, entra)
256 MiB         -> 65536,     524288        (el máximo de la política, entra)
512 MiB         -> rechazado
3*4096 + 1      -> rechazado, no truncado a 3 páginas
```

Un error **no escribe en el destino**: el test envenena la geometría del llamante
con `0xa5` y comprueba que sigue intacta, porque un destino a medias es peor que
un error.

## Self-test, cuatro mutaciones, cuatro detectadas

```
el divisor pasa de 8 a 4          ->  3 FAIL
no rechazar el tamano no multiplo->  1 FAIL
rellenar con 0 en vez del PTE    ->  1 FAIL
quitar el tope de RX550_GART_SIZE_MAX -> 1 FAIL
```

## Lo que NO dice

- **No dice que 512 KiB de entradas `0x10` mapeen nada.** No se ha ejecutado. Es
  `RUNTIME_REQUIRED`, y ahora con una limitación precisa que viene del finding
  1031: **25 de las 34 escrituras del GART van a registros que no se pueden
  leer**, así que la única señal de que la tabla ha quedado donde debía es el
  comportamiento posterior del GART, no una lectura de registro.
- **No dice que VRAM de 512 KiB alineado a 4096 se consiga.** Eso es del
  allocator (`rx550_vram.h`), que tiene su propio contrato y no se ha tocado.
- **No dice que la alineación sea 4096 por necesidad y no por costumbre.**
  `amdgpu_gart.c:272` lo pide así y no hay comentario que lo justifique; queda
  como `OBSERVED`, no como `PROVEN`.

## Trazabilidad

- `amdgpu_gart.c:533` (`num_gpu_pages`), `:263-278` (tabla en VRAM),
  `:110-118` (la de RAM y por qué es otra)
- `gmc_v8_0.c:960` (`table_size = num_gpu_pages * 8`), `:961`
  (`gart_pte_flags = AMDGPU_PTE_EXECUTABLE`)
- `amdgpu_vm.h:65` (`AMDGPU_PTE_EXECUTABLE = 1ULL << 4`)
- `gmc.gart_size = 256 MiB`: log del kernel de esta máquina
- Formato de entrada de 8 bytes: coherente con `struct rx550_vmid1_pte_page`
  (`rx550_vmid1_pgt.h`) y con la explicación de por qué PDE y PTE son tipos
  distintos (`rx550_vmid1_pgt.h:62-81`)
- Plan y aplicación: findings `1030` y `1031`
- Prefijo de numeración: 1032, reservado antes de escribir