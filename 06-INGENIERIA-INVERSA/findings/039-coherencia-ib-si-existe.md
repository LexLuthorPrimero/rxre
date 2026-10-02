# 039 · `PROVEN_ABSENT` retractado: GFX8 **sí** tiene `emit_mem_sync`. Y la coherencia del IB está resuelta

`CLASSIFICATION=CORRECTION+IMPLEMENTATION` · `TRACK=STATIC` · `GPU INTACTA` · `RUNTIME=NOT_RUN`
`RETRACTS=el PROVEN_ABSENT que emití al final de la iteración 17` · `CIERRA=la frontera G`

## CUDA principal

En el informe anterior afirmé que GFX8 no tiene `emit_mem_sync`, y construí sobre esa
afirmación una conclusión: "la coherencia CPU→GPU del IB no la establece ningún paquete en
este ASIC".

**Era falso.** `gfx_v8_0.c:6916` tiene `.emit_mem_sync = gfx_v8_0_emit_mem_sync` y `:6950`
tiene `.emit_mem_sync = gfx_v8_0_emit_mem_sync_compute`. Sin `head`, `grep -c emit_mem_sync
gfx_v8_0.c` devuelve **5**. Con `head -20` sobre todo el directorio devolvía las primeras
cuatro de `gfx_v10_0.c` en adelante y yo leí esa lista como completa.

**La conclusión también era falsa, y por el camino correcto.** La coherencia no está
ausente: está establecida por un paquete concreto, distinto en cada tipo de ring, y ya está
implementado y validado. Lo que queda abierto no es si existe sino qué cubre exactamente.

## El método, que es lo que hay que corregir

Es la **segunda** vez en dos iteraciones que un `grep | head` produce una ausencia falsa. La
primera fue `037`, buscando el programador de PTBA por VMID; casi escribo que el camino DRM no
programa PTBA. La segunda, aquí. Las dos tienen la misma forma y la misma causa: la lista
visible parecía completa y no lo era.

`AGENTS.md` §"Una lectura parcial jamás puede sustentar una ausencia" lo dice, y §
"PRE-EXECUTION CONTRACT CHECK" añade "Nunca aceptar 'grep encontró 0' si el grep estaba mal
construido". El error no fue un grep mal construido: fue un grep **bien** construido cuyo
resultado yo truncé y luego traté como exhaustivo. Es peor, porque no se detecta lookingando
el comando.

**Regla que queda escrita para no repetirlo, y que se puede verificar:** cuando una
búsqueda va a sostener una afirmación de ausencia, el resultado tiene que caber entero en la
salida, o hay que acompañar el número. `grep -c` en lugar de listar. Apliqué eso y el número
salió 5.

## Lo que hay, y son dos paquetes

GFX8 no tiene *un* `emit_mem_sync`, tiene **dos**, y el driver elige entre ellos por tipo de
ring. `gfx_v8_0_emit_mem_sync()`:

```c
amdgpu_ring_write(ring, PACKET3(PACKET3_SURFACE_SYNC, 3));
amdgpu_ring_write(ring, PACKET3_TCL1_ACTION_ENA |
                  PACKET3_TC_ACTION_ENA |
                  PACKET3_SH_KCACHE_ACTION_ENA |
                  PACKET3_SH_ICACHE_ACTION_ENA |
                  PACKET3_TC_WB_ACTION_ENA);  /* CP_COHER_CNTL */
amdgpu_ring_write(ring, 0xffffffff);  /* CP_COHER_SIZE */
amdgpu_ring_write(ring, 0);            /* CP_COHER_BASE */
amdgpu_ring_write(ring, 0x0000000A);   /* poll interval */
```

`gfx_v8_0_emit_mem_sync_compute()` usa `PACKET3_ACQUIRE_MEM` con count 5 y **añade
`CP_COHER_SIZE_HI` y `CP_COHER_BASE_HI`**: siete dwords frente a cinco.

| | ring GFX | ring compute/KIQ |
|---|---|---|
| opcode | `SURFACE_SYNC` 0x43 | `ACQUIRE_MEM` 0x58 |
| dwords | 5 | 7 |
| base de coherencia | **32 bits** | **64 bits** |
| `CP_COHER_CNTL` | `0x28C40000` | `0x28C40000` (igual) |

La asimetría de 32/64 bits es la razón de que existan dos: con `SIZE` 0xFFFFFFFF y `BASE` 0
la forma GFX cubre la ventana de 4 GiB entera, y no puede nombrar una base por encima. Un IB
en GTT por encima de 4 GiB de espacio PCI no se direcciona por `BASE` sino por `SIZE`, que es
otro mecanismo y sobre el cual este fichero no afirma nada.

`CP_COHER_CNTL` es el OR de cinco bits: cuatro `ACTION_ENA` de invalidación y `TC_WB` de
writeback. **Los dos lados están activos**, así que el paquete invalida *y* escribe, no uno de
los dos. Qué cachés cubre eso en GFX8 es `NOT_DETERMINED`: los nombres de los campos son la
única evidencia y se solapan.

## La cadena, completa

```
amdgpu_ib.c:79-80   ib->flags = AMDGPU_IB_FLAG_EMIT_MEM_SYNC
                    /* "flush the cache before commit the IB" */
amdgpu_ib.c:362     pool en AMDGPU_GEM_DOMAIN_GTT  -> el IB es RAM de sistema
amdgpu_ib.c:235-236 if (ib->flags & EMIT_MEM_SYNC && ring->funcs->emit_mem_sync)
                        ring->funcs->emit_mem_sync(ring)
amdgpu_ib.c:368     amdgpu_ring_ib_begin(ring)  -- el sync va en el RING
```

El IB lo escribe la CPU en GTT y lo lee la GPU sobre PCIe. El paquete de coherencia va **en el
ring**, justo antes del `SDMA_OP_INDIRECT` que lo nombra, no dentro del IB. Son dos espacios
de direcciones distintos y ésa es la razón estructural de que esto no sea concatenación.

`gfx_v8_0.c:816-822`, la referencia al IB:

```c
sdma_v4_0_ring_insert_nop(ring, (2 - lower_32_bits(ring->wptr)) & 7);
/* "IB packet must end on a 8 DW boundary" */
amdgpu_ring_write(ring, SDMA_PKT_HEADER_OP(SDMA_OP_INDIRECT) |
                  SDMA_PKT_INDIRECT_HEADER_VMID(vmid & 0xf));
amdgpu_ring_write(ring, lower_32_bits(ib->gpu_addr) & 0xffffffe0);
amdgpu_ring_write(ring, upper_32_bits(ib->gpu_addr));
amdgpu_ring_write(ring, ib->length_dw);
amdgpu_ring_write(ring, 0);
amdgpu_ring_write(ring, 0);
```

Cinco puntos, y cada uno costó algo:

1. Cabecera **sDMA** con el VMID en la misma palabra, no PACKET3.
2. `& 0xffffffe0` es una **máscara, no una comprobación**. Una dirección desalineada se
   redondea en silencio y la GPU lee de otro sitio. El codificador propio **rechaza**, que es
   la única forma de que el llamador se entere.
3. `length_dw` es **absoluto**, no menos uno. Convención opuesta a la del PTEPDE y a la del
   `count` de PACKET3, y equivocarse ejecuta un prefijo del IB sin error.
4. Los dos ceros finales no los cuenta nadie. Seis dwords de un opcode que no lleva longitud.
5. El NOP de alineación depende de `ring->wptr`, que este codificador no modela. **No se
   emite y no se afirma que sea correcto**; `RX550_SDMA_INDIRECT_NOP_PAD_FOR` da la fórmula.

## Tres errores propios en esta iteración, todos de "número plausible"

**El opcode del INDIRECT.** Escribí `17`. Es **`4`** (`vega10_sdma_pkt_open.h:29`). No lo
detectó el compilador: `17` no está definido, así que lo cogí de un valor supuesto y
compilaba. Lo paró leer el header.

**El VMID.** Lo puse en bits 3:0. Está en **19:16** (`vega10_sdma_pkt_open.h:2083`; el mask
es 0xF, el shift 16). Esto es el error más instructivo de la serie: la máscara *sí* es 0xF,
así que leerla como posición es razonable y da un campo que se solapa con el opcode. Escribí
`4 | vmid` en vez de `4 | (vmid << 16)`, lo que produce el opcode `4|vmid` — otro paquete
sDMA, sin error de build ni warning, y sin fallo de test salvo que un test conozca el valor
correcto por otra vía.

**La longitud del INDIRECT.** Puse 7. Son **6**. Y la explicación que escribí para el NOP
—"el 2 es el tamaño de la cabecera"— también era falsa: el 2 es `8 - longitud`, porque con 6
dwords y `w = wptr & 7` el paquete acaba 8-alineado exactamente cuando `w == 2`. Escribí una
explicación que sonaba a explicación.

Los dos primeros los paró leer el header; el tercero lo paró el test. Los tres son la misma
clase, y esa clase es exactamente lo que `035` fue: un número plausible en vez de uno medido.

## Implementado y validado

```
rx550_pm4_surface_sync()    5 dwords, 0x28C40000
rx550_pm4_acquire_mem()     7 dwords, con SIZE_HI y BASE_HI
rx550_pm4_mem_sync()        dispatch por tipo de ring
rx550_pm4_indirect()        6 dwords, rechaza desalineado / vmid>15 / length 0
rx550_ring_submit()         sync + INDIRECT, todo-o-nada
```

`rx550_pm4.c` de 563 a 726 líneas; `test_pm4.c` de 147 a **196 checks**; el validador de 12 a
**16 vectores**. Suite completa 230 checks, 0 fallos. `crosscheck` con 9 vectores CLEAN.
`rx550.ko` compila, `KBUILD_RC=0`.

**Tres mutaciones nuevas, las tres detectadas:**

| # | mutación | resultado |
|---|---|---|
| M6 | coherencia **después** del INDIRECT | `VIOLATION` en ambos vectores |
| M7 | VMID en bits 3:0 en vez de 19:16 | `UNDECODED` |
| M8 | INDIRECT de 7 dwords | `UNDECODED` |

M7 y M8 dan `UNDECODED` y no `VIOLATION`, y eso es lo correcto: el opcode alterado o la
longitud alterada desincronizan el recorrido, y la herramienta para con código 2 en vez de
inventar un análisis. `038` estableció ese código y esta iteración es su primer uso real.

El validador ahora comprueba la relación que faltaba: **coherencia antes de referencia**,
por posición, con un error si un INDIRECT no tiene paquete de coherencia previo.

## Lo que queda abierto, y es menos de lo que dije

| afirmación | estado |
|---|---|
| existe un paquete de coherencia en GFX8 | `PROVEN`, implementado |
| es distinto por tipo de ring | `PROVEN`, dos opcodes y dos anchos |
| va en el ring antes del INDIRECT | `PROVEN` por posición, validado |
| qué cachés cubre `CP_COHER_CNTL = 0x28C40000` en GFX8 | `NOT_DETERMINED` — sólo nombres de campo |
| si la forma de 32 bits basta para un IB en GTT sobre 4 GiB | `NOT_DETERMINED` — mecanismo por `SIZE`, no afirmado |
| si el NOP de alineación es necesario o cosmético | `NOT_DETERMINED` — depende de `wptr`, no modelado |

## Falsación

- La coherencia previa se refuta con un paquete INDIRECT sin paquete de coherencia delante que
  amdgpu produzca. Los 9 vectores de `crosscheck` incluyen la forma completa y el validador
  verifica la posición.
- Las longitudes y campos se refutan si `gfx_v8_0.c` o `sdma_v4_0.c` no dicen lo que cito. Cada
  constante del `.h` lleva su línea, y las tres mutaciones fijan los valores desde el lado
  contrario.
- `RX550_SDMA_INDIRECT_DW = 6` se refuta con un conteo distinto de `sdma_v4_0.c:816-822`.

## UNLOCKS

- La entrega está completa a nivel de formato: PTEPDE, vm-flush, coherencia, referencia al IB.
  Los cuatro escriben en el sitio correcto y el validador comprueba las relaciones.
- **Falta una cosa, y es la última del bloque E**: el `wptr` del ring y el doorbell. El NOP de
  alineación depende de `wptr`, así que el codificador actual no puede emitir una secuencia
  que dependa de la posición. Y sin doorbell no hay entrega: escribir el ring no hace que la
  GPU lo ejecute.
- El validador ya cubre 4 paquetes sDMA/PACKET3 y 3 relaciones entre paquetes. Añadir
  opcodes es mecánico; lo que cuesta son las relaciones nuevas.

## Evidencia

```
gfx_v8_0.c:         6916 y 6950 (emit_mem_sync en las dos tablas ring), funciones homónimas
amdgpu_ib.c:        79-80 (el flag), 235-236 (su consumo), 362 (GTT), 368 (ring_ib_begin)
sdma_v4_0.c:        816-822 (INDIRECT), 814 (el NOP de alineación)
vega10_sdma_pkt_open.h: 29 (SDMA_OP_INDIRECT=4), 2082-2083 (mask 0xF, shift 16)
vid.h:             201 (SURFACE_SYNC 0x43), 334 (ACQUIRE_MEM 0x58), 215-224 (los 5 bits)
verificacion:       grep -c emit_mem_sync gfx_v8_0.c = 5   (sin head; con head, 0 visibles)
modificaciones:     rx550_pm4.{c,h}, test_pm4.c, rx550pm4val.c, rx550pm4_emit.c, Makefile
suite:              22 + 12 + 196 = 230 checks, 0 fallos; 16/16 selftest; 9/9 crosscheck
rx550.ko:           KBUILD_RC=0
corpus:             MODIFICATIONS=0, sha256 12e8d5a973d1ad7c…c3e51941
```

Ningún registro leído de MMIO. `insmod` no ejecutado. `GPU INTACTA`.
