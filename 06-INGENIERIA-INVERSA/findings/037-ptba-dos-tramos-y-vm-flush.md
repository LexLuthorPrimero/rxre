# 037 · Los PTBA de GFX8 son **dos** tramos, no un array de 16 — y la secuencia de vm-flush ya está implementada

`CLASSIFICATION=IMPLEMENTATION+CORRECTION` · `TRACK=STATIC` · `GPU INTACTA` · `RUNTIME=NOT_RUN`
`IMPLEMENTS=la pieza que 036 declaró ausente` · `ALIASES=el orden de ejecución, frontera D`

## CUDA principal

El emisor de PTE de `036` no tenía destino. Ahora lo tiene: en GFX8 el directorio de páginas
lo escribe un paquete sDMA al IB, y el registro que lo nombra lo escribe el command processor
**desde el mismo IB**, con dos `WRITE_DATA` y un `WAIT_REG_MEM`. La función
`rx550_vm_flush()` emite los 19 dwords exactos.

Y al implementarla apareció un **`ERROR` propio de tipo silencioso**, el más peligroso de los
que he encontrado: **los PTBA no son un array de 16 registros con paso 1**. Son dos tramos
disjuntos de ocho, y el segundo está en dirección *menor*.

```
mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR   0x54f     gmc_8_1_d.h:636
mmVM_CONTEXT7_PAGE_TABLE_BASE_ADDR   0x556     gmc_8_1_d.h:643     (paso 1 dentro del tramo)
mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR   0x50e     gmc_8_1_d.h:607     <- NO 0x557
mmVM_CONTEXT15_PAGE_TABLE_BASE_ADDR  0x515     gmc_8_1_d.h:614     (paso 1 dentro del tramo)

0x50e - 0x54f = -0x41
```

## Por qué el error no se ve: el destino de los VMID 8-15

`gmc_v8_0_emit_flush_gpu_tlb()` (`gmc_v8_0.c:666-671`) hace la rama, y con razón:

```c
if (vmid < 8)
        reg = mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + vmid;
else
        reg = mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + vmid - 8;
```

Un driver propio que asumiera un solo array calcularía `0x54f + vmid`. Para los VMID 8-15 eso
da `0x557..0x55e`, y el header dice qué vive ahí:

```
0x557  mmVM_CONTEXT0_PAGE_TABLE_START_ADDR
0x558  mmVM_CONTEXT1_PAGE_TABLE_START_ADDR
...
0x55d  mmVM_CONTEXT1_PAGE_TABLE_END_ADDR
0x55e  mmVM_CONTEXT0_PAGE_TABLE_END_ADDR
```

Escribir una dirección de page directory en los registros de **apertura** mueve la ventana de
GPUVA que se traduce. No falla, no avisa, y toda dirección fuera de la ventana nueva queda sin
mapear. Un `PA` equivocado y un `PTBA` equivocado se reportan igual — como "las direcciones no
funcionan" — y el segundo es el que se puede evitar por completo con aritmética.

**La rama no es una comodidad, y hay una segunda prueba de que es intencionada:**
`amdgpu_amdkfd.c:766` rechaza todo `vmid < first_kfd_vmid`, y `gmc_v8_0.c:1162` pone
`first_kfd_vmid = 8` para GFX8. El `vmid - 8` de `amdgpu_amdkfd_gfx_v8.c:581` **no puede
underflow** porque la guarda lo hace precondición. La partición en 8 es una frontera de
dominio, no una convención de nombres.

`rx550_vm_ptba_reg()` devuelve **0** para un vmid fuera de 0-15, y la suite verifica que 0 no
se confunda con un registro válido (`0x54f` es el contexto 0, real). Saturar sería peor que
rechazar: programaría el contexto GART.

## La secuencia completa, y el estado real del orden

`rx550_vm_flush()` compone `gfx_v8_0_ring_emit_vm_flush()` (`gfx_v8_0.c:6197-6221`) y
`gmc_v8_0_emit_flush_gpu_tlb()` (`gmc_v8_0.c:661-677`):

| paso | qué | cómo | dwords |
|---|---|---|---|
| 1 | PTEPDE | paquete sDMA al mismo IB | 10 |
| 2 | PTBA(vmid) | `WRITE_DATA` = `pd_addr >> 12` | 5 |
| 3 | `VM_INVALIDATE_REQUEST` | `WRITE_DATA` = `1 << vmid` | 5 |
| 4 | esperar | `WAIT_REG_MEM` ref 0, mask 0, poll 0x20 | 7 |
| 5 | sincronizar PFP | `PFP_SYNC_ME` (sólo ring GFX) | 2 |

19 dwords con el sync, 17 sin él. La conexión que faltaba queda explícita: **en GFX8 el
directorio lo escribe SDMA en memoria, y el registro que lo nombra lo escribe el CP desde el
mismo IB.** Ninguno de los dos por separado es una traducción.

**Lo que esto NO establece.** El orden de arriba es `PROVEN` a nivel de *emisión de software*
y nada más. Sigue abierto, y no lo he tocado:

- si el hardware retira los tres en ese orden — `NOT_DETERMINED`
- qué espera exactamente el paso 4, dado que `FUNCTION(0)` = "always" y `mask` = 0, o sea no
  compara nada — `NOT_DETERMINED` (`029`)
- cuándo ve el page walker un PTE nuevo — `NOT_DETERMINED` (`030`)

La función devuelve `1`/`0` para que un llamador no pueda quedarse con un VMID sin flush
completo, y es **todo-o-nada**: un vm-flush a medias es un flujo de comandos distinto, no uno
más corto.

## La otra asimetría: WRITE_DATA vs SET_SH_REG

Ambos escriben un registro desde el mismo ring, y **usan convenciones distintas**:

| paquete | payload del registro |
|---|---|
| `SET_SH_REG` | **offset** desde `0x2C00` |
| `WRITE_DATA` | el **número absoluto** del registro |

`rx550_pm4_reg_offset()` existe justamente para que nadie olvide la resta. Un helper compartido
entre los dos escribiría o un offset sin sentido o un registro 0x2C00 registros más allá, y
ninguno de los dos se reporta. La suite lo comprueba con una aserción explícita: el valor
emitido **no** puede ser el offset.

Palabras de comando (`sid.h:386-392`), las tres de `gfx_v8_0_ring_emit_wreg()`:

```
ring GFX      WRITE_DATA_ENGINE_SEL(1) | WR_CONFIRM = 0x40100000
ring KIQ      1 << 16                               = 0x00010000
por defecto   WR_CONFIRM                            = 0x00100000
```

## `ERROR` propio, y los dos `grep`

Escribí en el código que `WAIT_REG_MEM_OPERATION` **no existe**, porque lo busqué en
`sid.h:398-413` y allí sólo están `FUNCTION`, `MEM_SPACE` y `ENGINE`. **Es falso**: existe en
`vid.h:182` como `(x) << 6`, y `gfx_v8_0.c` usa los dos valores en el mismo fichero —
`OPERATION(0)` en `:6206` ("wait") y `OPERATION(1)` en `:6054` ("write, wait, write").

La causa es que **`sid.h` no es el header del que salen estos campos**: `gfx_v8_0.c:33-35`
incluye `vi.h`, `vi_structs.h` y `vid.h`. Es el mismo error que ya ocultó los `PACKET3_*` en
esta sesión — `#define` con tabulador, y fichero equivocado. La corrección aplicada es
acotar el `grep` al header que el código incluye, y `OPERATION` pasó a ser parámetro.

Y un segundo `ERROR`, del mismo tipo que el que casi me hace reportar una ausencia falsa: para
buscar el programador de PTBA por VMID usé

```
grep -rn "PAGE_TABLE_BASE_ADDR" *.c | grep -v "gmc_8\|gfx_8" | head -20
```

y leí la salida visible como la lista completa. **El `grep` estaba bien; el `head -20` la
truncó** y yo convertí una lectura parcial en una ausencia — exactamente lo que
`AGENTS.md` §"Una lectura parcial jamás puede sustentar una ausencia" prohíbe. El mismo grep
sin `head` devuelve 155 líneas, y entre ellas `gmc_v8_0.c:668`. Casi escribo que el camino DRM
no programa PTBA por VMID. No lo hace mal: hay un `head` de más.

## Las pruebas

`test_pm4.c` pasa de 75 a **147 checks**, todos verdes, sin warnings con
`-Wall -Wextra -Wshadow`. Cuatro mutaciones nuevas, todas detectadas:

| # | mutación | checks que fallan |
|---|---|---|
| M1 | PTBA como un array único de 16 con paso 1 | 5 |
| M2 | `WRITE_DATA` con el offset de `SET_SH_REG` | 6 |
| M3 | PTBA **después** del invalidate | 4 |
| M4 | vm-flush sin la espera | 8 |

M3 y M4 apuntan a lo que esta iteración establece: el **orden** dentro de la secuencia es
parte de la especificación, no un detalle de implementación, y la suite lo vigila.

Un fallo real de la suite, y era mío: escribí `0x12345` donde `0x1234567000 >> 12` es
`0x1234567`. Siete dígitos hex, no cinco. El test me cazó a mí, que es la mitad
de lo que sirve tener un test.

## Falsación

- La geometría de dos tramos se refutaría si `gmc_8_1_d.h` tuviera
  `mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR == 0x557`. La suite lo comprueba como desigualdad, no
  como constante.
- La secuencia se refutaría si `gfx_v8_0_ring_emit_vm_flush()` tuviera otra forma. Su
  lectura está transcrita de `:6197-6221`; las cuatro mutaciones la fijan desde el lado
  contrario, pero ninguna de las dos direcciones prueba el hardware.
- `rx550_vm_ptba_reg()` se refutaría si el ASIC de este host seleccionase un `ip_block` distinto
  de `gmc_v8_0_gmc_funcs`. Cierra con una lectura de `GC_HWIP`; no ejecutada.

## Evidencia

```
gmc_8_1_d.h:            607,614,636,643 (los cuatro PTBA), 615 (VM_INVALIDATE_REQUEST)
gmc_v8_0.c:             33-35 (vi.h, vi_structs.h, vid.h), 661-677 (emit_flush_gpu_tlb),
                        906-911 (gmc_v8_0_gart_enable: los 15 contextos al GART),
                        1162 (first_kfd_vmid = 8), 1727-1735 (gmc_v8_0_gmc_funcs)
gfx_v8_0.c:             6197-6221 (ring_emit_vm_flush), 6054 (OPERATION(1))
amdgpu_gmc.h:           373 (macro emit_flush_gpu_tlb)
amdgpu_amdkfd.c:        766 (is_kfd_vmid)
amdgpu_amdkfd_gfx_v8.c: 574-583 (PTBA de KFD, sólo vmid >= 8)
vid.h:                  169-186 (WAIT_REG_MEM_*), sid.h:377,386-392,397,465 (opcodes y cmd)
modificaciones:         rx550_pm4.{c,h} + test_pm4.c; rx550.ko 385648 B, KBUILD_RC=0
corpus:                 MODIFICATIONS=0, sha256 12e8d5a973d1ad7c…c3e51941
```

Ningún registro leído de MMIO. `insmod` no ejecutado. `GPU INTACTA`.
