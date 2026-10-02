# 036 · `035` implementado: el emisor de PTE existe, y la suite lo somete a cinco mutaciones

<!-- CLAUSULA_RETRACTADA_POR=091 -->
> ⚠ **La cláusula del bloqueo técnico de este documento está RETRACTADA.**
> Se leyeron `CONFIG_MODULE_SIG_ALL` y `CONFIG_SECURITY_LOCKDOWN_LSM`, y **no**
> `CONFIG_MODULE_SIG_FORCE`, que está `# CONFIG_MODULE_SIG_FORCE is not set`.
> Medido: `lockdown=[none]`, `SecureBoot disabled`, y un `.ko` propio **compila**
> con `vermagic` idéntico y **sin firmar**. No hay bloqueo técnico: lo que queda
> es NIVEL 4 → `BLOCKED_BY_AUTHORIZATION`. Ver `091`.

`CLASSIFICATION=IMPLEMENTATION` · `TRACK=STATIC` · `IMPLEMENTS=035` · `GPU INTACTA` · `RUNTIME=NOT_RUN`
`RETRACTED_PARTLY_BY=043` — **el `count - 1` implementado aquí pertenece al ASIC equivocado.**
`sdma_v3_0.c:996` es el emisor que corre en Polaris12 y escribe `count` plano. Corregido en
la iteración siguiente: codificador y suite usan `count`. Sobrevive de este documento: los 10
dwords, el opcode con valor 12, la cabecera de un byte en `[7:0]`, y el rechazo de
`count == 0`.

## CUDA principal

`035` corrigió el productor de PTE de Polaris12. Esta iteración lo **implementa** en el
codificador del driver propio y demuestra que la suite detecta los errores, no que sólo
pasa.

- `rx550_pm4.c` gana `rx550_sdma_header()` y `rx550_sdma_vm_set_pte_pde()`.
- `test_pm4.c` pasa de 49 a **75 checks**, todos verdes.
- **Cinco mutaciones** introducidas una a una: las cinco las detecta la suite.
- El módulo del kernel recompila (`rx550.ko`, 375360 B) con los símbolos nuevos dentro.

## Lo implementado

```
rx550_pm4.h   RX550_SDMA_PKT_OP_MASK      0x000000ff   vega10_sdma_pkt_open.h:70
              RX550_SDMA_PKT_OP_SHIFT     0            vega10_sdma_pkt_open.h:71
              RX550_SDMA_OP_PTEPDE        12           vega10_sdma_pkt_open.h:37
              RX550_SDMA_PTEPDE_DW        10           sdma_v4_0.c:1649-1658
              rx550_sdma_header()
              rx550_sdma_vm_set_pte_pde()

rx550_pm4.c   emits 10 dwords: hdr, pe[2], flags[2], addr[2], incr, 0, count-1
```

`RX550_SDMA_PTEPDE_DW` es una constante, no un literal Repetido en el `.c`. El test la usa
para el caso de capacidad exacta, así que un cambio en el número de dwords rompe la
compilación del test en vez de desincronizarse en silencio.

## La segunda forma de cabecera, y por qué no es opcional

`rx550_pm4_header()` construye un PACKET3: tipo 3 en `[31:30]`, opcode en `[15:8]`, cuenta de
14 bits en `[23:16]`. Un paquete sDMA no tiene nada de eso:

```
SDMA_PKT_HEADER_op_offset 0
SDMA_PKT_HEADER_op_mask   0x000000FF
SDMA_PKT_HEADER_op_shift  0
```

Un byte de opcode en `[7:0]`, y nada más. La cabecera de `PTEPDE` es literalmente
`0x0000000C`. **El motor sDMA deduce la longitud del propio opcode**, así que un paquete sDMA
truncado no es un error de parseo sino un flujo de instrucciones distinto: el desalineamiento
se propaga en silencio. Por eso la comprobación de capacidad es Todo-o-nada, y por eso
`RX550_SDMA_PTEPDE_DW` alimenta la condición.

Verificado en el `.ko` compilado: el dword `0xC0000C00` — PTEPDE mal tratado como PACKET3 —
aparece **0 veces**.

## Las cinco mutaciones

Cada una: introducir, compilar, ejecutar, restaurar. La suite **no** pasa con ninguna.

| # | mutación | checks que fallan |
|---|---|---|
| M1 | `count` en vez de `count - 1` (el error de `023`) | 3 |
| M2 | cabecera sDMA con layout PACKET3 | 5 |
| M3 | intercambiar `flags` y `addr` | 4 |
| M4 | eliminar la guarda `count == 0` | 2 |
| M5 | `> size_dw - 1` en la comprobación de capacidad | 1 |

M1 reproduce exactamente el error que `035` corrigió, y la suite lo nombra:

```
  [FAIL] dw9  count - 1, NOT count -- got 0x00000004, expected 0x00000003
  [FAIL] dw9 is not the raw count (the 023 error)
  [FAIL] count=1 encodes 0 entries-minus-one -- got 0x00000001, expected 0x00000000
```

M5 es la que importa para el resto del driver: una comprobación de capacidad con
off-by-one **no** se detecta en la suite de este paquete si el IB es suficientemente grande,
porque el estado final es idéntico. Sólo se ve cuando el IB es de 9 dwords. Se detecta aquí;
en el camino real depende del tamaño del IB que elija el llamador.

**Lo que las mutaciones no prueban**: que los valores esperados sean correctos. Un
lector equivocado del corpus, repetido en el codificador y en el test, pasa las 75. La
diferencia de procedencia está escrita en el propio test: las cinco cabeceras PACKET3 se
contaron dentro de `amdgpu.ko`; las de PTEPDE se transcribieron de `sdma_v4_0.c:1643-1659`,
porque un paquete PTEPDE no contiene ninguna cabecera PACKET3 que contar. Es el límite
declarado de esta sección, no un fallo.

## El módulo compila y contiene lo nuevo

```
$ make -C /lib/modules/7.1.3-200.nobara.fc44/build M=$(pwd) modules
  CC [M]  rx550_pm4.o
  LD [M]  rx550.o
  MODPOST Module.symvers
  LD [M]  rx550.ko
KBUILD_RC=0

$ nm rx550.ko | grep sdma
00000000000002f0 T rx550_sdma_header
0000000000000320 T rx550_sdma_vm_set_pte_pde

$ tam 375360 B
  dword 0x0000000C  (header sDMA PTEPDE):        6307 ocurrencias
  dword 0xC0000C00  (PTEPDE como PACKET3):          0 ocurrencias
```

Las 6307 ocurrencias de `0x0000000C` **no son todas este paquete**: el compilador también
emite el inmediato `12` en otros contextos. Lo que se afirma es la dirección, no el recuento.

`insmod` **no** se ejecuta: el host tiene `CONFIG_MODULE_SIG_ALL=y` y
  > **[091] CORRIGE ESTA CLAUSULA**: no hay bloqueo tecnico. Lo que se leyo fue
  > `CONFIG_MODULE_SIG_ALL` y **no** `CONFIG_MODULE_SIG_FORCE`, que esta
  > `# CONFIG_MODULE_SIG_FORCE is not set`. Medido en este host:
  > `lockdown=[none]`, `SecureBoot disabled`, y un `.ko` propio COMPILA con
  > `vermagic` identico y SIN FIRMAR. Lo que queda es NIVEL 4
  > (`BLOCKED_BY_AUTHORIZATION`), que es otra cosa. Ver 091.
`CONFIG_SECURITY_LOCKDOWN_LSM=y`, y la clave de firma no está en el host. Un módulo
compilado aquí no carga, y eso es política del host, no un defecto del código.

## Lo que NO hace esto

`rx550_sdma_vm_set_pte_pde()` emite el paquete. **No lo entrega.** La secuencia de
programación de registros que pone el IB en un ring y programa `VM_CONTEXT0_PAGE_TABLE_BASE_ADDR`
no está en este árbol, y hasta `gfx_v8_0_do_edc_gpr_workarounds()` —la única secuencia de
dispatch disponible— devuelve de inmediato para `CHIP_POLARIS12`. Un paquete correcto en un
comando que nadie entrega es un resultado de formato, no una GPU funcionando. Es la misma
frase que ya está en la cabecera de `test_pm4.c`, y sigue siendo cierta con 75 checks.

## UNLOCKS

- El productor de PTE está escrito, con la codificación corregida y **`count == 0` rechazado**
  en vez de emitir `0xFFFFFFFF` entradas. Un PTEPDE con `count-1` bajo la cuenta de entradas
  es corrupción de page table; el rechazo es lo que evita que un driver propio lo genere.
- Existe la segunda forma de cabecera. `rx550_pm4.h` ya declara las dos, y el test las
  distingue con una aserción explícita de que el bit de tipo está a 0.
- La suite de `test_pm4` tiene un procedimiento de mutación probado. `031` registró que un
  verificador que no ve el árbol no sirve; aquí el análogo es una suite que pasa sin que nadie
  haya comprobado que falla. Las cinco mutaciones son eso, y son reutilizables.

## Criterio de falsación

La implementación se refutaría si `sdma_v4_0.c:1658` no fuera `count - 1` para el ASIC de
este host — es decir, si la selección de `ip_block` de `amdgpu_discovery.c:2549-2560` no
eligiera `sdma_v4_0_ip_block`. Se cierra leyendo `SDMA0_HWIP` del host, que es una lectura
de MMIO y por tanto `NOT_RUN` aquí. La suite tampoco se refuta por sí sola: si las cinco
mutaciones dejaran de fallar, el procedimiento —no el driver— estaría mal.

## Evidencia

```
07-DRIVER/kernel/rx550_pm4.h    constantes sDMA,RX550_SDMA_PTEPDE_DW, dos prototipos
07-DRIVER/kernel/rx550_pm4.c    rx550_sdma_header, rx550_sdma_vm_set_pte_pde
07-DRIVER/tests/test_pm4.c      secciones 11, 12, 13; 75 checks
mutaciones M1-M5                restauradas; suite verde tras cada una
07-DRIVER/kernel/rx550.ko       375360 B, KBUILD_RC=0, símbolos presentes
corpus:                          MODIFICATIONS=0, sha256 tarball 12e8d5a973d1ad7c…c3e51941
```

Ningún registro leído de MMIO. `insmod` no ejecutado. `GPU INTACTA`.
