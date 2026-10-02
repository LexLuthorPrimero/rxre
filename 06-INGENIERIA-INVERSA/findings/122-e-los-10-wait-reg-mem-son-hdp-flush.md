# 122 · los 10 `WAIT_REG_MEM` del anillo son `hdp_flush`, y eso corrige a 107, 108 y 109

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC + HOST_OBSERVATION
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=OBSERVED_READ_ONLY · GPU INTACTA
```

## Qué resuelve

Tres cosas, todas con el mismo bloqueador detrás:

1. **El reparto de los dwords de payload de `WAIT_REG_MEM`**, abierto desde el
   principio: `soc15d.h` declara 7 campos para 5 dwords.
2. **La atribución de los `WAIT_REG_MEM` observados**, que `107` degradó a
   `CORROBORATED` y que `111` lo dio por tal sin resolver.
3. **La contradicción de 1 `PFP_SYNC_ME` contra 34 fences** de `111`.

## El bloqueador, cerrado

Conté las escrituras reales de `gfx_v8_0_ring_emit_vm_flush`, `L6199`-`L6207`:
**cabecera + 6 dwords de payload**, con `count` = 5 en la cabecera. Y el mismo
desajuste en `hdp_flush`. **No es un error de lectura: es la convención.**

Medido sobre el anillo, en dos paquetes de opcode y largo distintos:

```
WAIT_REG_MEM  (0x3C, count=5) : observado 7 dwords  = cabecera + 6 payload   6-1 = 5  OK
INDIRECT_BUFFER (0x3F, count=2): observado 4 dwords = cabecera + 3 payload   3-1 = 2  OK
```

> **La convención de `PACKET3(op, n)` en este driver es `n` = payload − 1.**
> El paquete ocupa `n + 2` dwords.

`sid.h`: `PACKET3(op,n) = (TYPE3<<30) | ((op & 0xFF) << 8) | ((n & 0x3FFF) << 16)`.
**El campo se escribe tal cual; no hay corrección.** Los 7 campos de `soc15d.h`
no son 7 dwords: **se solapan según `OPERATION`**, y por eso la cuenta no cuadra
con una lectura campo a campo.

**La lectura de 7 dwords del principio era correcta. Lo que estaba mal era
contarla contra el `count` sin medir el paso real en el anillo.**

## La atribución, resuelta por discriminante

El anillo vivo tiene 10 `WAIT_REG_MEM`. Decodificados:

```
+0  0xC0053C00   cabecera, tipo 0x3C, count 5
+1  0x00000143   flags
+2  0x00001537
+3  0x00001538
+4  0x00000001
+5  0x00000001
+6  0x00000020
+7  0xC0012800   <- cabecera del paquete siguiente: el anterior acaba en +6
```

Decodificación de los flags con los shifts de `soc15d.h`:

```
FUNCTION  [2:0] = 3        (equal)
MEM_SPACE [5:4] = 0
OPERATION [7:6] = 1        (write, wait, write)
ENGINE    [8]   = 1        <- WAIT_REG_MEM_ENGINE(x) = (x) << 8
```

**Y el emisor que produce exactamente eso es `gfx_v8_0_ring_emit_hdp_flush`:**

```
gfx_v8_0.c:6036  static void gfx_v8_0_ring_emit_hdp_flush(struct amdgpu_ring *ring)
gfx_v8_0.c:6047  amdgpu_ring_write(ring, PACKET3(PACKET3_WAIT_REG_MEM, 5));
gfx_v8_0.c:6048  amdgpu_ring_write(ring, (WAIT_REG_MEM_OPERATION(1) |
gfx_v8_0.c:6049                   WAIT_REG_MEM_FUNCTION(3) |
gfx_v8_0.c:6050                   reg_mem_engine));
gfx_v8_0.c:6051  amdgpu_ring_write(ring, mmGPU_HDP_FLUSH_REQ);
gfx_v8_0.c:6052  amdgpu_ring_write(ring, mmGPU_HDP_FLUSH_DONE);
gfx_v8_0.c:6053  amdgpu_ring_write(ring, ref_and_mask);
gfx_v8_0.c:6054  amdgpu_ring_write(ring, ref_and_mask);
gfx_v8_0.c:6055  amdgpu_ring_write(ring, 0x20);
```

**Seis campos, seis dwords observados, los seis coinciden:**

| offset | observado | fuente | |
|---|---|---|---|
| flags | `0x143` | `OPERATION(1)｜FUNCTION(3)｜ENGINE(1)` | `gfx_v8_0.c:6048-6050` |
| +2 | `0x1537` | `mmGPU_HDP_FLUSH_REQ` | `gfx_v8_0.c:6051` |
| +3 | `0x1538` | `mmGPU_HDP_FLUSH_DONE` | `gfx_v8_0.c:6052` |
| +4 | `0x1` | `ref_and_mask` | `gfx_v8_0.c:6053` |
| +5 | `0x1` | `ref_and_mask` | `gfx_v8_0.c:6054` |
| +6 | `0x20` | poll interval | `gfx_v8_0.c:6055` |

`mmGPU_HDP_FLUSH_REQ = 0x1537` y `_DONE = 0x1538`: comprobado en el árbol de
headers, y hay **seis definiciones distintas de esas dos macros en el corpus**
(0x0e26, 0x0106, 0x1537), lo que confirma que **el valor correcto es el del
ASIC de esta GPU** y que citar la constante equivocada habría roto todo.

## Los dos emisores, contrastados

| | motor | flags | FUNCTION | OPERATION | addr |
|---|---|---|---|---|---|
| `hdp_flush` `L6036` | `ENGINE(1)` `/*pfp*/` | `0x100` | **3** | **1** | `0x1537` |
| `vm_flush` `L6191` | `ENGINE(0)` `/*me*/` | `0x000` | **0** | **0** | `0x051E` |
| **observado** | `ENGINE(1)` | `0x143` | **3** | **1** | **`0x1537`** |

**El observado es `hdp_flush`, sin ambigüedad posible.**

## Y de paso: el ring espera al PFP, el flush de TLB espera al ME

```
gfx_v8_0.c:5245   *ref_and_mask   = GPU_HDP_FLUSH_DONE__CP0_MASK;   0x00000001
gfx_v8_0.c:5246   *reg_mem_engine = WAIT_REG_MEM_ENGINE(1);  /* pfp */
```

**`GPU_HDP_FLUSH_DONE__CP0_MASK = 0x00000001`, y el observado es 1.** Así que el
driver espera a que `GPU_HDP_FLUSH_DONE` valga exactamente `1`: **un único bit de
estado para el pipe de graphics**, y en el anillo GFX ese bit es el 0.

**Y los dos emisores esperan a motores distintos:**

- **`hdp_flush` espera al PFP** (`ENGINE(1)`, el comentario del propio driver lo dice)
- **`vm_flush` espera al ME** (`ENGINE(0)`, comentario en `L6202`)

**Eso corrobora la asimetría de `108` desde un paquete independiente del que `108`
usó**, y le añade el dato de que **son dos esperas distintas con propósitos
distintos, no dos nombres de la misma espera.**

## Y la contradicción de 111 queda resuelta por otra vía

```
gfx_v8_0.c:6212   amdgpu_ring_write(ring, PACKET3(PACKET3_PFP_SYNC_ME, 0));
```

**`PACKET3_PFP_SYNC_ME` se emite desde exactamente una línea de todo
`gfx_v8_0.c`, y esa línea está dentro de `gfx_v8_0_ring_emit_vm_flush`.**

```
1 PFP_SYNC_ME observado  ==>  1 gfx_v8_0_ring_emit_vm_flush ejecutado en la ventana
```

**PROVEN.** Y `115`/`116` explican por qué hubo exactamente uno: un compositor en
régimen no cambia de page tables, así que no pide vm_flush.

**El `WAIT_REG_MEM` de ese vm_flush no estaba en la ventana** — fue
`FUNCTION(0)`, no `FUNCTION(3)`, y ya había salido del buffer circular. **Por eso
10 paquetes visibles y 1 flush no se contradicen: son de dos emisores
distintos.**

## Corrijo tres hallazgos míos

| # | lo que decía | lo correcto |
|---|---|---|
| `107` | los `WAIT_REG_MEM` del anillo, atribución `CORROBORATED` a `L6047` | **`PROVEN`: `gfx_v8_0_ring_emit_hdp_flush` `L6036-6056`, seis campos coincidentes** |
| `108` | `PFP_SYNC_ME` como parte de la secuencia de cada vm_flush | **correcto, y ahora `PROVEN` por ser `L6212` el único emisor** |
| `109` | los 10 `WAIT_REG_MEM` como "esperas de la secuencia" | **son `hdp_flush`, no vm_flush. Dos emisores, dos esperas, dos motores** |

**Y una corrección dentro de mi propio razonamiento de esta tanda:** al principio
escribí que los flags observados eran `FUNCTION=3, OPERATION=1` "sin declarar" y
que el bit 8 no estaba en `soc15d.h`. **El bit 8 sí: `WAIT_REG_MEM_ENGINE(x) =
(x) << 8`.** Lo leí de la lista de `PACKET3_WAIT_REG_MEM__*`, que no incluye los
campos `WAIT_REG_MEM_*` de alias. **Dos tablas con los mismos campos y dos
nombres, y leí la que no tocaba.**

**Y otra: derivé `ref_and_mask = 0x4` de `GPU_HDP_FLUSH_DONE__CP2_MASK` y el
observado es 1.** No cuadraba, busqué el resto del `switch` y el anillo GFX toma
la rama `else`, que usa `CP0_MASK`. **Lo comprobé en vez de forzar el número.**

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| `n` = payload − 1 en `PACKET3` | `PROVEN_DERIVED` (dos paquetes, dos largos) |
| Los 7 campos de `soc15d.h` se solapan por `OPERATION` | `PROVEN_DERIVED` |
| Los 10 `WAIT_REG_MEM` observados son `hdp_flush` | `PROVEN` (6/6 campos) |
| `mmGPU_HDP_FLUSH_REQ/DONE` = `0x1537`/`0x1538` en este ASIC | `PROVEN` |
| `hdp_flush` espera al PFP, `vm_flush` al ME | `PROVEN` (`L5246`, `L6202`) |
| `GPU_HDP_FLUSH_DONE__CP0_MASK` = 1 | `PROVEN` |
| `PFP_SYNC_ME` sólo se emite en `L6212` | `PROVEN` |
| 1 `PFP_SYNC_ME` = 1 vm_flush | `PROVEN_DERIVED` |
| Por qué el driver **escribe** 1 y espera igualdad a 1 | **`NOT_DETERMINED`** |
| Si el hardware pone ese bit al terminar el flush | **`NOT_PROVEN`** — requiere placa |
| Cuándo se llama `hdp_flush` | **`NOT_DETERMINED`** |

**Las dos últimas son el resto del trabajo, y son hardware.** Que el bit 0 de
`GPU_HDP_FLUSH_DONE` lo ponga el PFP al vaciar el HDP, y cada cuánto se llama
`hdp_flush`, no sale del corpus. **Pero ahora la pregunta está bien hecha**: sé
el registro, sé el bit, sé el motor y sé el valor exacto que espera. Antes de
esta nota no sabía cuál de los dos emisores era, y por eso el resto no se podía
formular.

## Procedencia

- `OBSERVED` -- `/tmp/rg3.bin`, volcado de `debugfs/amdgpu_ring_gfx`, sólo
  lectura. 2051 dwords; 10 `WAIT_REG_MEM` en índices 8, 264, 281, 311, 520, 776,
  1032, 1288, 1544, 1800; primer paquete decodificado en `+0..+6`.
- `STATIC` -- `gfx_v8_0.c:6036-6056` `:6191-6215` `:5215-5248`, `soc15d.h`,
  `sid.h` (`PACKET3`), `GPU_HDP_FLUSH_DONE__CP0_MASK`.
- Sin MMIO write, sin TLB, sin módulos.
- **Corrige `107`, `108` y `109`, que son míos.**
- Encadenada con `111` (next IB), `113` (el vm_flush lo pide el scheduler),
  `115`/`116` (marca de agua por VMID, `use_cpu_for_update` nunca dispara).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

**Una nota sobre el método, y es la que me llevo.**

Estuve un turno entero discutiendo si los `WAIT_REG_MEM` eran o no de
`hdp_flush`, con argumentos de lectura del fuente, y llegué a la conclusión
equivocada dos veces. **Lo que lo resolvió no fue leer más código: fue medir el
paso entre dos paquetes iguales en el anillo y contar los campos que
coincidían.** Seis de seis.

**Un paquete que se parece a otro en cinco campos puede ser de otro emisor. Uno
que coincide en seis, con el nombre del registro y el intervalo de poll, es de
ese emisor.** Esa es la prueba, y era un volcado de 2051 dwords que llevaba
horas en `/tmp` sin que se me ocurriera medirlo.