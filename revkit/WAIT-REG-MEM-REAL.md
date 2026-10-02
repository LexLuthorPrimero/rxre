# WAIT-REG-MEM-REAL.md — un WAIT_REG_MEM ejecutado por el hardware

## Que es esto

En `revkit/WAIT-REG-MEM.md` se reconstruyo el paquete `WAIT_REG_MEM` de GFX8
**solo desde el codigo fuente**. Alli se establecio que GFX8 emite unicamente
`FUNCTION(0)` y `FUNCTION(3)`, y que `always` no es alcanzable porque el
campo FUNCTION tiene dos bits.

Eso era `DERIVATION` a partir de la fuente. Aqui hay algo mejor: un
`PACKET3_WAIT_REG_MEM` **real, capturado del anillo de la GPU y ejecutado por
el hardware**, con su payload contrastado una a una vez contra la
construccion que hace el driver.

## De donde sale

`revkit/capturas/amdgpu_ring_gfx.txt`, nodo `amdgpu_ring_gfx` de debugfs.
Offset 12 de la cabecera + dword 8 del anillo.

Paquete en el dword 8: `0xc0053c00`

Con `PACKET3(op, n) = (3 << 30) | (op << 8) | (n << 16)` (sid.h:336):

| campo | formula | valor | nombre (sid.h) |
|---|---|---|---|
| tipo | `>> 30` | 3 | PACKET3 |
| opcode | `>> 8 & 0xFF` | 0x3C | `PACKET3_WAIT_REG_MEM` |
| count | `>> 16 & 0x3FFF` | 5 | 5 dwords de payload |

## Los 5 dwords de payload, contrastados con el driver

Payload observado (dwords 9 a 13 del anillo):

```
0x00000143
0x00001537
0x00001538
0x00000001
0x00000001
```

Lo que el driver escribe en `gfx_v8_0_emit_hdp_flush`
(gfx_v8_0.c:6047-6056):

```c
amdgpu_ring_write(ring, PACKET3(PACKET3_WAIT_REG_MEM, 5));
amdgpu_ring_write(ring, (WAIT_REG_MEM_OPERATION(1) | /* write, wait, write */
                         WAIT_REG_MEM_FUNCTION(3) |  /* == */
                         reg_mem_engine));
amdgpu_ring_write(ring, mmGPU_HDP_FLUSH_REQ);
amdgpu_ring_write(ring, mmGPU_HDP_FLUSH_DONE);
amdgpu_ring_write(ring, ref_and_mask);
amdgpu_ring_write(ring, ref_and_mask);
amdgpu_ring_write(ring, 0x20); /* poll interval */
```

Correspondencia:

| payload | contenido observado | lo que el driver pone ahi |
|---|---|---|
| [0] | `0x00000143` | `OPERATION(1) \| FUNCTION(3) \| engine` |
| [1] | `0x00001537` | `mmGPU_HDP_FLUSH_REQ` |
| [2] | `0x00001538` | `mmGPU_HDP_FLUSH_DONE` |
| [3] | `0x00000001` | `ref_and_mask` |
| [4] | `0x00000001` | `ref_and_mask` |

### Cada valor, verificado contra el ASIC de esta GPU

No se han supuesto las direcciones. `mmGPU_HDP_FLUSH_REQ` esta definido en
varios bloques BIF con valores distintos, y el que coincide con lo
observado es el de **BIF 4.1**, que es la generacion de Polaris12:

```
asic_reg/bif/bif_4_1_d.h:        mmGPU_HDP_FLUSH_REQ   0x1537
asic_reg/bif/bif_4_1_d.h:        mmGPU_HDP_FLUSH_DONE  0x1538
asic_reg/bif/bif_4_1_sh_mask.h:  GPU_HDP_FLUSH_DONE__CP0_MASK  0x1
```

Las tres casan exactamente. `REQ` y `DONE` en registros adyacentes,
`0x1538 - 0x1537 = 1`, y `ref_and_mask` con el valor que
`gfx_v8_0_get_hdp_flush_mask()` calcula para un anillo GFX (rama `else` de
gfx_v8_0.c:5243-5246: `*ref_and_mask = GPU_HDP_FLUSH_DONE__CP0_MASK`).

Ocho identificadores independientes dan el mismo resultado.

## Descomposicion de 0x143

```
0x143 = 0b0001_0100_0011
```

| bits | valor | campo |
|---|---|---|
| [1:0] | `0b11` = 3 | `FUNCTION` = 3 |
| [4] | 1 | `OPERATION` = 1 (write, wait, write) |
| [6] | 1 | `ENGINE` = 1 = PFP |

El ENGINE=1=PFP concuerda con `*reg_mem_engine = WAIT_REG_MEM_ENGINE(1); /* pfp */`
en gfx_v8_0.c:5246.

### Lo que esto CONFIRMA

1. `FUNCTION` ocupa **[1:0]**, o sea dos bits. Con dos bits el valor maximo
   es 3, y por tanto **`always` (que seria 4 o mayor) es inalcanzable en
   GFX8**. Esto era `DERIVATION`; ahora esta `CORROBORATED` con un paquete
   real.

2. `FUNCTION = 3` esta observed, no solo deducido del codigo.

3. El segundo dword es la direccion del registro comparado, y REQ/DONE son
   consecutivos: es un handshake de un solo bit.

### El sexto dword: el driver escribe mas de lo que declara

El driver escribe 6 dwords tras la cabecera:

```c
PACKET3(PACKET3_WAIT_REG_MEM, 5)   <-- declara count = 5
... ref_and_mask                  <-- payload[4], el quinto
amdgpu_ring_write(ring, 0x20);     /* poll interval */   <-- el sexto
```

En el anillo, el dword 14 es `0x00000020`. O sea que el sexto dword **si
esta**, y vale 0x20, que es el poll interval que pone el driver.

Asi que el descriptor dice 5 y hay 6 dwords escritos. Dos lecturas
posibles y **ninguna se elige aqui**:

1. El hardware lee 5 y el sexto se ignora. En ese caso el poll interval no
   llega a tener efecto.
2. El hardware lee 6 y `count` esta off-by-one en el driver.

Que pasara NO se deduce de este volcado. `NOT_DETERMINED`.

Lo que si se afirma: el anillo contiene los 6 dwords, en ese orden. Eso es
observacion, no interpretacion.

### Lo demas que NO se cierra

- **El significado hardware de `FUNCTION(3)` sigue siendo `NOT_DETERMINED`.**
  Saber que vale 3 y que se emite para el flush HDP NO dice que haga el
  hardware con el. El paquete es el mismo que el driver escribe; que lo
  ejecute no lo explica.
- Que la secuencia de 8 bloques sea un unico job o 8 ejecuciones del mismo
  job, no se sabe. El anillo no lleva marcas de trabajo.

## Contexto del anillo

El anillo GFX tiene 2048 dwords. El contenido decodificado son 8 bloques
identicos en estructura, arrancando en los dwords 3 + 256k:

| paquetes por bloque | veces |
|---|---|
| `PACKET3_WAIT_REG_MEM` | 8 |
| `PACKET3_CONTEXT_CONTROL` | 8 |
| `PACKET3_INDIRECT_BUFFER` | 8 |
| `PACKET3_WRITE_DATA` | 8 |
| `PACKET3_SWITCH_BUFFER` | 8 |
| `PACKET3_EVENT_WRITE_EOP` | 32 |
| NOP de relleno | 1648 (8 tiradas de 206) |

`SWITCH_BUFFER` y `EVENT_WRITE_EOP` son paquetes de fin de frame. La
repeticion de 8 bloques, cada uno alineado a 256 dwords, concuerda con
`.align_mask = 0xff` de `gfx_v8_0_ring_funcs_gfx` (gfx_v8_0.c:6872).

## Estado

| afirmacion | estado |
|---|---|
| hay un WAIT_REG_MEM real en el anillo GFX | `OBSERVED` |
| opcode 0x3C = `PACKET3_WAIT_REG_MEM` | `PROVEN` (sid.h) |
| el payload casa 1:1 con `gfx_v8_0_emit_hdp_flush` | `PROVEN` (5 de 5 campos) |
| `mmGPU_HDP_FLUSH_REQ = 0x1537` en BIF 4.1 | `PROVEN` (bif_4_1_d.h) |
| `mmGPU_HDP_FLUSH_DONE = 0x1538` en BIF 4.1 | `PROVEN` (bif_4_1_d.h) |
| `ref_and_mask = GPU_HDP_FLUSH_DONE__CP0_MASK = 0x1` | `PROVEN` (bif_4_1_sh_mask.h) |
| FUNCTION ocupa [1:0] en GFX8 | `CORROBORATED` |
| `always` inalcanzable en GFX8 | `CORROBORATED` |
| FUNCTION(3) se emite para el flush HDP | `OBSERVED` |
| ENGINE=1 = PFP en este paquete | `OBSERVED` |
| hay 6 dwords escritos con count declarado 5 | `OBSERVED` |
| que lee el hardware: 5 o 6 | `NOT_DETERMINED` |
| que hace el hardware con FUNCTION(3) | `NOT_DETERMINED` |

## Lo que este documento cambia respecto a WAIT-REG-MEM.md

`WAIT-REG-MEM.md` dedujo del codigo que GFX8 solo emite `FUNCTION(0)` y
`FUNCTION(3)`, y que `always` es inalcanzable porque el campo es de dos
bits. Eso sigue siendo correcto, pero era `DERIVATION`.

Aqui `FUNCTION` en `[1:0]` queda `CORROBORATED` por un paquete real, y
`always` inalcanzable pasa de deducción a corroboración.

Lo que **no** cambia: el significado hardware de cada valor de `FUNCTION`.
Este documento no lo cierra, y no se presenta como si lo hiciera.
