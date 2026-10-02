# VM-FLUSH-GFX8 — el productor del invalidate, y lo que el anillo dice de él

> Fecha: 2026-10-02. STATIC (corpus) + un discriminante sobre la captura del
> anillo GFX ya existente. Sin GPU, sin MMIO, sin debugfs.
> `GPU INTACTA` · `WRITE_EXECUTION NONE` · `RESEARCH/` sin modificar.

---

## 1 · El productor: `gmc_v8_0_emit_flush_gpu_tlb`

Estaba sin mirar, y es el eslabón que faltaba entre el VMID software y el
registro de hardware. `gmc_v8_0.c:668-683`, cinco líneas:

```c
static uint64_t gmc_v8_0_emit_flush_gpu_tlb(struct amdgpu_ring *ring,
					    unsigned int vmid, uint64_t pd_addr)
{
	uint32_t reg;

	if (vmid < 8)
		reg = mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + vmid;
	else
		reg = mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + vmid - 8;
	amdgpu_ring_emit_wreg(ring, reg, pd_addr >> 12);

	/* bits 0-15 are the VM contexts0-15 */
	amdgpu_ring_emit_wreg(ring, mmVM_INVALIDATE_REQUEST, 1 << vmid);

	return pd_addr;
}
```

Se llega a él por indirección, no por nombre: `amdgpu_gmc_emit_flush_gpu_tlb`
es una **macro** a un puntero a función
(`amdgpu_gmc.h:371` → `adev->gmc.gmc_funcs->emit_flush_gpu_tlb`), y la
implementación de GFX8 se asigna en `gmc_v8_0.c:1736`.

### Lo que dice el comentario del driver, y si se sostiene

`/* bits 0-15 are the VM contexts0-15 */`, y el valor escrito es `1 << vmid`.
Eso solo es correcto si `INVALIDATE_DOMAIN_i` está en el bit `i`. Comprobado
en el header, no supuesto:

| generación | `SHIFT[i] == i` en los 16 |
|---|---|
| `gmc_6_0` | sí |
| `gmc_7_0` | sí |
| `gmc_7_1` | sí |
| `gmc_8_1` | sí |
| `gmc_8_2` | sí |

**Cinco generaciones, el mismo invariante.** `1 << vmid` no es una coincidencia
que funciona: es el contrato del campo.

Y `gfx_v8_0.c` incluye `gmc/gmc_8_2_d.h` y `gmc_8_2_sh_mask.h` (líneas 41-42),
así que la generación que le toca es `gmc_8_2`. El control `CN-R29` de
`selfcheck.py`, que no es de esta sesión, ya fijaba esa parte.

### Addresses (gmc_8_2_d.h)

| registro | offset |
|---|---|
| `mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR` | `0x50e` |
| `mmVM_INVALIDATE_REQUEST` | `0x51e` |
| `mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR` | `0x54f` |

Los bloques de contextos 0 y 8 están separados: `0x50e..0x515` para VMID 8-15 y
`0x54f..0x556` para VMID 0-7. El `if (vmid < 8)` del driver existe por eso, y
**no** por el registro del invalidate, que es único.

---

## 2 · La cadena completa, en orden de emisión

```
gfx_v8_0_ring_emit_vm_flush(ring, vmid, pd_addr)        gfx_v8_0.c:6191
│
├─ gmc_v8_0_emit_flush_gpu_tlb(ring, vmid, pd_addr)     gmc_v8_0.c:668
│    ├─ WRITE_DATA  PTBA[vmid] = pd_addr >> 12          registro
│    └─ WRITE_DATA  VM_INVALIDATE_REQUEST = 1 << vmid   registro
│
└─ /* wait for the invalidate to complete */            gfx_v8_0.c:6199
     └─ WAIT_REG_MEM cnt=5, control=0x000, sobre 0x51e, ref=0, mask=0, poll=0x20
```

Con valores reales para `vmid = 7` y `pd_addr = 0x1_0025_8000`, que es una de
las ocho direcciones observadas en el anillo (EV-21):

| dword | valor | qué es |
|---|---|---|
| 0 | `0xC0003733` | `PACKET3_WRITE_DATA`, count 3 |
| 1 | `0x40110000` | `WR_CONFIRM` \| `ENGINE(1)` \| `WR_ONE_ADDR` \| `DST_SEL(0)` |
| 2 | `0x556` | `mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + 7` |
| 3 | `0x100258` | `pd_addr >> 12` |
| 4 | `0xC0003733` | `PACKET3_WRITE_DATA`, count 3 |
| 5 | `0x40110000` | idem |
| 6 | `0x51e` | `mmVM_INVALIDATE_REQUEST` |
| 7 | `0x00000080` | `1 << 7` |
| 8 | `0xC0053C00` | `PACKET3_WAIT_REG_MEM`, count **5** |
| 9 | `0x00000000` | control: `OP(0) \| FN(0) \| ENG(0)` — **dword cero** |
| 10 | `0x51e` | registro vigilado |
| 11 | `0x00000000` | ref |
| 12 | `0x00000000` | mask |
| 13 | `0x00000020` | poll interval |

Layout de `WRITE_DATA` según `sid.h:377-388`: `DST_SEL<<8`, `WR_ONE_ADDR<<16`,
`WR_CONFIRM<<20`, `ENGINE_SEL<<30`. Opcode `0x37`, **no** `0x3D` (que es
`MEM_WRITE`). Se comprobó contra los opcodes que `pm4dec` carga de `sid.h` en
runtime, no de memoria.

**El control dword del WAIT_REG_MEM es cero.** Con `FUNCTION(0)`, `OPERATION(0)`
y `ENGINE(0)` no queda ni un bit puesto: la forma de *esperar sin comparar
contra nada*. Es lo único que tiene sentido si lo que esperas es "a que pase
algo" y no "a que valga X".

Esto responde a la pregunta que el proyecto llevaba abierta como
`hardware trigger de always: NOT_DETERMINED`. **No es un trigger: es una
espera**, y espera a que el invalidate de TLB haya terminado. El hardware no
dispara nada por su cuenta.

---

## 3 · El off-by-one NO es del tipo de paquete, es del emisor

Esto corrige la lectura plana de EV-19. En el driver hay **dos** emisores de
`WAIT_REG_MEM` y no coinciden:

| emisor | payload escritos | `count` declarado | of-by-one |
|---|---|---|---|
| `gfx_v8_0_emit_hdp_flush` (gfx_v8_0.c:6046) | **6** | 5 | sí |
| `gfx_v8_0_ring_emit_vm_flush` (gfx_v8_0.c:6199) | **5** | 5 | no |

El de HDP flush escribe `ref_and_mask` **dos veces** (dwords 4 y 5 de su
bloque) y por eso se pasa en uno. El del vm flush no.

Un driver propio que copie "la forma del paquete" sin mirar el emisor se
equivoca en uno de los dos.

### Confirmado con los bytes crudos del anillo real

`capturas/amdgpu_ring_gfx.txt`, dwords 8..14, leídos del binario:

```
[ 8] 0xc0053c00   cabecera: tipo 3, opcode 0x3C, count = 5
[ 9] 0x00000143   control: FUNCTION(3) | OPERATION(1)<<6 | ENGINE(1)<<8
[10] 0x00001537   mmGPU_HDP_FLUSH_REQ
[11] 0x00001538   mmGPU_HDP_FLUSH_DONE
[12] 0x00000001   ref_and_mask
[13] 0x00000001   ref_and_mask   (2º, el que sobra del conteo)
[14] 0x00000020   poll interval  <-- séptimo dword del bloque
```

**Siete dwords consecutivos forman un `WAIT_REG_MEM` cuyo campo `count` dice
cinco.** El `0x20` está físicamente en el buffer, en la posición correcta, y
fuera del conteo declarado. Eso es EV-19, confirmado con los bytes y no con la
fuente.

Que `pm4dec` no lo viera antes no es un fallo suyo: `dwords` es la extensión
**declarada** (cabecera + `count`), no la escrita. El sobrante se le sale como
un dword suelto, que es exactamente lo que reportaba como
`PKT0(dato, no cabecera) cnt=32`.

---

## 4 · Discriminante: el hardware NO lee exactamente `count`

Si el hardware se detuviera tras `count` payload, el dword 14 (`0x00000020`)
sería una cabecera tipo 0 con `count = 32` (el count de tipo 0 está en los bits
**bajos**, no en `[29:16]`), y el siguiente paquete empezaría en el dword 47.
El dword 47 es `0x00001040`: tipo 0 otra vez, con count 4160. A partir de ahí el
anillo no contiene ningún paquete más.

Recorriendo el anillo entero de las dos formas:

| lectura | paquetes tipo 2/3 válidos | cabeceras tipo 0 espurias |
|---|---|---|
| `count` exactos (5) | **3** | **2** |
| los 6 payload | **11** | **0** |

**Once paquetes válidos frente a tres, y cero dwords espurios en 2051.** La
lectura de seis es la única que deja el anillo con sentido.

Consecuencia: la hipótesis *"el hardware lee exactamente los `count` payload
dwords"* queda **REFUTADA** por el anillo real. Un driver propio que lo creyera
haría lo mismo que el hardware: perdería el anillo.

Lo que **queda abierto**, y es corto:

- `NOT_DETERMINED`: si el count es `payload - 1` (lee 6 siempre) o si el
  hardware trata los dwords tipo 0 como no-op y los salta. Con esta captura
  **no se distinguen**: los dos dan 11 paquetes y 0 espurias.

Y ahí está el nudo, porque si la respuesta fuera "lee 6 siempre", el emisor de
`vm_flush` (que escribe 5 y declara 5) **se comería un dword del paquete
siguiente**. O el count significa algo distinto de lo que parece, o uno de los
dos emisores tiene un defecto. Los tres son compatibles con lo observado.

---

## 5 · Reconciliación con el finding 106 de otra sesión

`daec702` concluye que `VM_INVALIDATE_REQUEST` no tiene campo `FUNCTION`, y es
correcto: en `gmc_8_2` los únicos campos son `INVALIDATE_DOMAIN_0..15`, sin
nada por encima del bit 15.

Y ahora se entiende **por qué**: el invalidate no necesita un selector de modo
porque va dirigido por **bit**. `1 << vmid` dice a qué contexto se aplica. Un
campo `FUNCTION` habría sobrado.

No hay contradicción entre 106 y EV-17: son dos `FUNCTION` distintos, uno de un
opcode de PM4 (`sid.h:398`) y otro de un registro MMIO. El proyecto los tuvo
confundidos.

---

## 6 · Lo que esto NO cierra

- El **contenido** de la page table. Esta función escribe el PTBA (`pd_addr>>12`),
  no las PTE. `NOT_AVAILABLE` por debugfs en 7.1.3.
- Si el hardware lee `count` o `count+1`, o qué hace con un dword tipo 0. Ver §4.
- Si el registro `VM_INVALIDATE_REQUEST` se auto-limpia tras serviced. El
  `ref=0, mask=0` sugiere que **no** se compara contra nada, solo que cambió,
  pero eso no dice si hay un bit de "done" en otro sitio.
- **La variante de vm_flush no está en el anillo capturado**: los 8
  `WAIT_REG_MEM` observados son todos `0x143`, o sea de HDP flush.
  `NOT_OBSERVED`, no `PROVEN_ABSENT`. Los `WRITE_DATA` van todos a `0xBCC`.

---

## 7 · Errores propios durante esta sesión

Cuatro, y los tres primeros de la misma familia: **elegir una definición antes
de buscar todas**.

1. Synthetic ring con opcode `0x3D` (`MEM_WRITE`) en vez de `0x37`
   (`WRITE_DATA`). Lo cazó el propio control.
2. Synthetic ring con la dirección del registro en un dword a cero. Lo cazó el
   propio control.
3. Contar cabeceras tipo 0 con el count leído de `[29:16]`, cuando en tipo 0
   está en los bits bajos. Dio 6 espurias donde eran 2. Lo cazó una mutación
   de M2, que hacía ver las dos lecturas como iguales.
4. Afirmar que "el `0x20` es un literal, no una macro". Es literal en
   `gfx_v8_0.c`, que es lo que había mirado; la macro
   `PACKET3_WAIT_REG_MEM__POLL_INTERVAL` existe en `soc15d.h:212` y `nvd.h:202`.
   **Es el mismo error de las tres primeras**: afirmar una ausencia desde el
   único sitio que ya sabía que la tenía.

Y un quinto, de otra familia: un control que **se saltaba en silencio** porque
buscaba el `WAIT_REG_MEM` en la última posición, y por el propio off-by-one que
medía, el sobrante quedaba al final. La guarda ahora falla si no lo encuentra.
Un control que no se ejecuta es peor que no tenerlo: parece cobertura.

Este patrón es la séptima vez que aparece la misma forma de fallo en el
proyecto (F11). La forma aquí es **búsqueda con el ámbito justo suficiente para
confirmar lo que ya se sospechaba**, que es el riesgo específico de trabajar
alrededor de una hipótesis ya formada.

## 8 · El poll interval: lo que el corpus sí dice (búsqueda por agente, 2026-10-02)

Un agente buscó en los tres corpus completos lo que el dword `0x20` significa.
Verificado a mano lo que se cita aquí. Comandos y ámbito van en
`docs/OPEN-FRONTIERS.md` F12b.

### 8.1 · El nombre de la macro sí existe

```
soc15d.h:212   #define PACKET3_WAIT_REG_MEM__POLL_INTERVAL(x) ((((unsigned)(x)) & 0xFFFF) << 0)
nvd.h:202      idéntica
```

**Retira** lo que dije antes en la sesión de que "el `0x20` es un literal, no una
macro". Es literal en `gfx_v8_0.c`, que es lo que se vio; pero la macro existe
para la familia soc15 y para Navi. Y da un dato de campo que no teníamos:

**el poll interval es de 16 bits, bits [15:0], y va en el payload del paquete.**

### 8.2 · El valor se discrimina por PROPÓSITO, no por ASIC

En GFX8, comprobado en `gfx_v8_0.c`:

| emisor | espera sobre | poll interval |
|---|---|---|
| `gfx_v8_0_ring_emit_pipeline_sync` (:6174) | **memoria** (`MEM_SPACE(1)`), `FUNCTION(3)` | **`4`** |
| `gfx_v8_0_ring_emit_hdp_flush` (:6046) | registro | **`0x20`** |
| `gfx_v8_0_ring_emit_vm_flush` (:6199) | registro | **`0x20`** |

Y el mismo reparto, con literales fijos, en `gfx_v6_0.c` y `gfx_v7_0.c`: los
tres `pipeline_sync` usan `4`, los tres `hdp_flush`/`vm_flush` usan `0x20`. En
gfx9 a gfx12 el helper `*_wait_reg_mem()` recibe el valor como argumento
`inv`, y los call sites mantienen el mismo reparto.

**Esto es lo más fuerte que hay sobre el poll interval, y es una inferencia por
correlación, no una afirmación del corpus:** el driver pone un valor distinto
para una espera semánticamente distinta. Si el hardware no lo leyeran, el `4`
y el `0x20` serían lo mismo y la diferencia sería ruido de estilo. Y si lo lee,
**un driver propio que copie `0x20` donde debería ir `4` sonsonaría al ritmo
equivocado** — en un `pipeline_sync`, que es una sincronización real de pipeline.

El corpus **no escribe en ningún sitio** por qué. Eso sigue siendo
`NOT_DETERMINED`: la correlación es fuerte, el mecanismo no está documentado.

### 8.3 · Existe un presupuesto de reintentos, y el driver no lo programa

```
asic_reg/gca/gfx_8_0_d.h:498   #define mmCP_WAIT_REG_MEM_TIMEOUT  0xc074
```

Registro de 32 bits, presente desde gfx6, en el bloque **CP**. Desde gfx9 hay
además un source ID de interrupción:

```
GFX_11_0_0__SRCID__CP_ME_WAIT_REG_MEM_POLL_TIMEOUT = 192  // 0xC0
```

**Ningún `.c` del driver lee ni escribe `mmCP_WAIT_REG_MEM_TIMEOUT`.** Comprobado
con `grep -rn CP_WAIT_REG_MEM_TIMEOUT .../amdgpu/*.c`: vacío. Solo los headers
lo definen.

Consecuencias, y son las dos cosas accionables de esta sección:

1. El hardware tiene un **contador de reintentos** para el sondeo de
   `WAIT_REG_MEM`, con su source ID de timeout. El valor de corte lo pone el
   hardware por defecto, no el driver.
2. En gfx8 **no hay source ID** de ese timeout en el corpus. O el timeout no
   genera interrupción en gfx8, o el source ID no está en el árbol.
   `NOT_FOUND` en `asic_reg/gca/irqsrcs_gfx_8_*.h`, que **no existe** (el glob
   solo devuelve `gfx_8_0_*` y `gfx_8_1_*`).

Un driver propio tiene que decidir qué hacer si el invalidate no termina:
esperar en silencio hasta el tope por defecto del hardware, o programar el
timeout. **El corpus no dice qué hace el hardware al agotarlo.**

### 8.4 · Corroboración del off-by-one desde OTRO paquete

`PACKET3_ACQUIRE_MEM` documenta su layout con el poll interval en el dword
**número 7**:

```
soc15d.h:392-401 (idéntico en nvd.h:455)
 * 1.  HEADER
 * 2.  COHER_CNTL [30:0]
 ...
 * 7.  POLL_INTERVAL [15:0]
```

Y su `count` declarado es **5** (`gfx_v9_0.c:5596`:
`PACKET3(PACKET3_ACQUIRE_MEM, 5)`, con 6 escrituras; 7 en v10+ con count 6).

**El número del campo excede al `count` en dos.** Es el mismo patrón que el
`WAIT_REG_MEM` del HDP flush, y en un paquete independiente.

Lo que **no** dice el corpus: que ese dword no se consuma. Es lectura del
desajuste número/`count`, no una afirmación de AMD. Se registra como
`CORROBORATED`, no `PROVEN`.

### 8.5 · AMD tampoco lo sabía

`drivers/gpu/drm/amd/display/dc/dcn20/dcn20_vmid.c:46-52`:

```
	/* According the hardware spec, we need to poll for the lowest
	 * bit of PAGE_TABLE_BASE_ADDR_LO32 = 1 any time a GPUVM
	 * context is updated. We can't use REG_WAIT here since we
	 * don't have a seperate field to wait on.
	 *
	 * TODO: Confirm timeout / poll interval with hardware team
	 */
```

Es un bucle de CPU, no un paquete PM4, y es dcn20, no GFX8. Pero es la única
mención textual de "poll interval" como concepto **abierto**, y es una admisión
explícita de que el equipo de AMD no tenía el valor confirmado. Importa como
contexto de fiabilidad: no estamos investigando un misterio que AMD resolvió y no
documentó; es una cosa que AMD tampoco tenía.

## 9 · Lo que el corpus NO dice, con su ámbito

Tres corpus completos recorrido: `RESEARCH/baseline/linux-7.1.3` (completo),
`RESEARCH/kernelbuild/linux-7.1.3` (completo, con `Documentation/`), y
`rx550-upstream-7.2.8/linux-7.2.8` (completo).

| pregunta | estado |
|---|---|
| cómo sondea el hardware al encontrar un `WAIT_REG_MEM` | `NOT_FOUND` en los tres |
| qué significa numéricamente el poll interval | `NOT_FOUND` en los tres |
| si el `count` incluye o excluye el dword de poll | `NOT_FOUND` en los tres |
| un layout campo-a-campo de `WAIT_REG_MEM` para gfx8 | `NOT_FOUND`; el único es `gfx_v12_1_pkt.h:105-133`, de otro ASIC |
| `WAIT_REG_MEM_POLL` en `RESEARCH` | `NOT_FOUND` |

Lo único que se acerca a una descripción larga es la struct de la API MES, que
renombra y reordena los campos sin añadir semántica:

```
mes_v11_api_def.h:599-611   struct WAIT_REG_MEM { op; reference; mask; reg_offset1; reg_offset2; }
mes_v12_api_def.h:782-791   idem + RRMT_OPTION, con el comentario:
   "only function = equal_to_the_reference_value and mem_space = register_space
    supported for now"
```

Ese comentario es **la única restricción de semántica de `FUNCTION`** en todo
el corpus, y no menciona el poll interval.

Un dato del layout de `gfx_v12_1_pkt.h` que sí se traslada con cautious
caution: allí `WAIT_REG_MEM` tiene campos que en `sid.h` para GFX8 **no
existen**: `MODE<<10`, `MID_DIE_ID<<12`, `XCD_DIE_ID<<14`, `MES_INTR_PIPE<<22`,
`MES_ACTION<<24`, `TEMPORAL<<25`. Si el hardware de GFX8 tiene algo detrás del
bit 9, no está en el corpus. `NOT_IN_CORPUS`, no `PROVEN_ABSENT`.

Tres, y los tres de la misma familia: **elegir una definición antes de buscar
todas**.

1. Synthetic ring con opcode `0x3D` (`MEM_WRITE`) en vez de `0x37`
   (`WRITE_DATA`). Lo cazó el propio control.
2. Synthetic ring con la dirección del registro en un dword a cero. Lo cazó el
   propio control.
3. Contar cabeceras tipo 0 con el count leído de `[29:16]`, cuando en tipo 0
   está en los bits bajos. Dio 6 espurias donde eran 2. Lo cazó una mutación de
   M2, que hacía ver las dos lecturas como iguales.

Y un cuarto, de otra familia: un control que **se saltaba en silencio** porque
buscaba el `WAIT_REG_MEM` en la última posición, y por el propio off-by-one que
medía, el sobrante quedaba al final. La guarda ahora falla si no lo encuentra.
Un control que no se ejecuta es peor que no tenerlo: parece cobertura.