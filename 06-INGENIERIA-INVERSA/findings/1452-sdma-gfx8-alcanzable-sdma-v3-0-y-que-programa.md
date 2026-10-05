# 1452 — Para Polaris12 el SDMA alcanzable es `sdma_v3_0.c`: `sdma_v4_0.c` está en el Makefile y es código muerto

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · CORPUS=rx550-upstream-7.2.8
TARGET=CHIP_POLARIS12 (1002:699F) · GFX8 · GART 256 MiB

AFECTADO=vi.c:2113                     sdma_v3_1_ip_block  <- la tabla que SE INSTALA
         vi.c:2107                     case CHIP_POLARIS12  (el case, no la linea de add)
         sdma_v3_0.c:1693-1700         sdma_v3_1_ip_block, .funcs = &sdma_v3_0_ip_funcs
         sdma_v3_0.c:1544              sdma_v3_0_ip_funcs   <- la tabla que SE EJECUTA
         amdgpu_discovery.c:2559       sdma_v4_0_ip_block   <- UNICA puerta, inalcanzable
         amdgpu_discovery.c:3452       unico llamante de esa puerta
         amdgpu_device.c:2136,2150     CHIP_POLARIS12 hace break; discovery es el default
         Makefile:174-175              los dos .o se compilan  <- no prueba nada
CONTINUA=1403, 1404 (misma pregunta: quien elige el fichero)
CORRIGE=023, 047 y 035 (cadena de Producer) sin cambiar su conclusion util
NO_REPETIR=023 y 047 ya medidos; 1166/1177/1178 (PASID); 1403/1404 (VMPT)
ESTADO=PROVEN-SOBRE-EL-CORPUS · B es PROVEN con alcance · C es PROVEN con hueco medido
```

## 0 · LA PREGUNTA, Y POR QUE NECESITA EL TERCER NIVEL DE ALCANCE

La consigna pedía distinguir "está en el fichero" de "está en la tabla que se instala",
y nombraba `sdma_v4_0.c` como "el archivo clave". MEDIDO: **`sdma_v4_0.c` no es el
archivo clave de esta placa. No es ninguno.** Se compila (`Makefile:175`), tiene
2.741 líneas, y no se ejecuta nunca en Polaris12. El que se ejecuta se llama
`sdma_v3_0.c`, que es un nombre de fichero que induce a error por el mismo motivo
que `gfx_v1_0.c` en `1403`: el nombre no dice la generación, dice el *número de
revision del IP*, y en esta familia el fichero de Tonga sirve para Fiji, Carrizo,
Stoney y Polaris.

Los tres niveles, porque son tres medidas y cada una tiene un modo de fallo propio:

```
  NIVEL 1  el .o se compila y se enlaza            Makefile:174-175
  NIVEL 2  alguien hace amdgpu_device_ip_block_add  vi.c:2113
  NIVEL 3  ese add ocurre en el case de POLARIS12  vi.c:2107 -> 2113
```

Los tres tienen que ser verdad. El primero es el único que se comprueba mirando un
Makefile, y por eso es el único que no dice nada.

---

## 1 · A) QUÉ TABLA SE REGISTRA PARA `CHIP_POLARIS12`

### 1.1 · La puerta de entrada no es `vi.c` sino `amdgpu_device.c`

`amdgpu_device.c:2131-2155`, el switch completo:

```c
	case CHIP_TOPAZ:
	case CHIP_TONGA:
	case CHIP_FIJI:
	case CHIP_POLARIS10:
	case CHIP_POLARIS11:
	case CHIP_POLARIS12:          <-- :2136
	case CHIP_VEGAM:
	case CHIP_CARRIZO:
	case CHIP_STONEY:
		...
		r = vi_set_ip_blocks(adev);      <-- :2145
		break;
	default:
		r = amdgpu_discovery_set_ip_blocks(adev);   <-- :2150
		break;
```

**`CHIP_POLARIS12` hace `break` en `:2148`.** La rama `default:`, que es la única
que entra en `amdgpu_discovery_set_ip_blocks`, **no se ejecuta**. Ese `break` es la
puerta que decide el resto del hallazgo.

*Alcance verificado (§16):* `amdgpu_device.c` es un fichero del directorio `amdgpu`,
así que el grep es exhaustivo sobre el driver, no sobre una muestra. Y
`si_set_ip_blocks` (`:2110`) está en la rama `#ifdef CONFIG_DRM_AMDGPU_SI`, bajo
`case CHIP_VERDE..CHIP_HAINAN`, y `si.c` **no contiene la cadena `POLARIS12`**
(verificado: `grep -c POLARIS12 si.c` = **0**). `si.c` no compite.

### 1.2 · Lo que `vi.c` añade para Polaris12

`vi.c:2105-2114`, literal:

```c
	case CHIP_POLARIS10:
	case CHIP_POLARIS11:
	case CHIP_POLARIS12:                        <-- :2107
	case CHIP_VEGAM:
		amdgpu_device_ip_block_add(adev, &vi_common_ip_block);
		amdgpu_device_ip_block_add(adev, &gmc_v8_1_ip_block);
		amdgpu_device_ip_block_add(adev, &tonga_ih_ip_block);
		amdgpu_device_ip_block_add(adev, &gfx_v8_0_ip_block);
		amdgpu_device_ip_block_add(adev, &sdma_v3_1_ip_block);   <-- :2113
		amdgpu_device_ip_block_add(adev, &pp_smu_ip_block);
```

**El add es la línea 2113, no la 2107.** La 2107 es el `case`. Cito las dos porque
esa confusión es exactamente la que hace que alguien cite mal.

`sdma_v3_1_ip_block`, `sdma_v3_0.c:1693-1700`:

```c
const struct amdgpu_ip_block_version sdma_v3_1_ip_block =
{
	.type = AMD_IP_BLOCK_TYPE_SDMA,
	.major = 3,
	.minor = 1,
	.rev = 0,
	.funcs = &sdma_v3_0_ip_funcs,      <-- :1699
};
```

Y `.minor = 1` es **todo** lo que distingue este bloque del `sdma_v3_0_ip_block`
de la línea 1684. Las dos tablas de versión apuntan a **la misma** `amd_ip_funcs`:

```
  sdma_v3_0_ip_funcs   sdma_v3_0.c:1544   .name = "sdma_v3_0"
  early_init                                  sdma_v3_0_early_init    (:1092)
  sw_init / sw_fini / hw_init / hw_fini      mismo nombre
  suspend / resume / is_idle / wait_for_idle  mismo nombre
  pre/post_soft_reset / soft_reset           mismo nombre
```

> **La tabla que se instala se llama `sdma_v3_1_ip_block`; la tabla que se ejecuta
> se llama `sdma_v3_0_ip_funcs`; el fichero es `sdma_v3_0.c`.** Tres nombres, un
> solo bloque. La tabla de GFX8 (`amd_ip_funcs`) es la de `sdma_v3_0`, compartida
> con Tonga, Fiji, Carrizo y Stoney: **cuatro de sus cinco campos son idénticos y
> el único que vary es `.major/.minor` del bloque de versión, que no ejecuta
> código.**

### 1.3 · Por qué `sdma_v4_0.c` no se ejecuta

`sdma_v4_0_ip_block` se añade en **un solo sitio del árbol**:

```
  amdgpu_discovery.c:2559    amdgpu_device_ip_block_add(adev, &sdma_v4_0_ip_block);
```

y ese site está dentro de `amdgpu_discovery_set_sdma_ip_blocks`, cuyo único
llamante es:

```
  amdgpu_discovery.c:3452    r = amdgpu_discovery_set_sdma_ip_blocks(adev);
```

dentro de `amdgpu_discovery_set_ip_blocks` (`:2841`), que a su vez solo se llama
desde el `default:` de `amdgpu_device.c:2150`.

```
  sdma_v4_0.c  --NO-->  amdgpu_discovery.c:2559
                     <-- solo desde :3452
                     <-- solo desde amdgpu_discovery_set_ip_blocks
                     <-- solo desde amdgpu_device.c:2150  (default:)
                     <-- Polaris12 hace break en :2148
```

**`PROVEN`: `sdma_v4_0.c` no se ejecuta en Polaris12.** Y la función que decide es
`amdgpu_ip_version(adev, SDMA0_HWIP, 0)` (`:2550`), que Polaris12 nunca consulta:
el `break` de `:2148` impide que se llame.

### 1.4 · El `Makefile` no es evidencia, y por qué importa aquí

```
  Makefile:174     sdma_v3_0.o \
  Makefile:175     sdma_v4_0.o \
```

Los diez ficheros `sdma_v*.c` del árbol compilan. `ls sdma*.c` da 10. Si alguien
mide "qué SDMA tiene esta placa" contando ficheros, o leyendo el Makefile, o
buscando `sdma_` en el árbol, salen **diez** respuestas y **ninguna** es la
correcta. La lista real de ficheros SDMA **ejecutados** en Polaris12 es de **uno**:

```
  sdma_v3_0.c     ALCANZABLE   (via vi.c:2113)
  sdma_v2_4.c     NO   (solo CHIP_TOPAZ,       vi.c:2060)
  sdma_v4_0.c     NO   (discovery, unreachable)
  sdma_v4_4.c     NO   (cero referencias en el arbol)
  sdma_v4_4_2.c   NO   (discovery)
  sdma_v5_0.c     NO   (discovery)
  sdma_v5_2.c     NO   (discovery)
  sdma_v6_0.c     NO   (discovery)
  sdma_v7_0.c     NO   (discovery)
  sdma_v7_1.c     NO   (discovery)
```

Verificado por grep de `sdma_v*_ip_block` sobre todo el directorio: las únicas
apariciones fuera del propio fichero de definición están en `vi.c` (6) y
`amdgpu_discovery.c` (6). `sdma_v4_4_ip_block` no aparece en ninguna: existe el
`.c` y no existe el bloque. **Once ficheros, diez `.o`, seis tables de dispatch,
un solo bloque ejecutado.**

---

## 2 · B) ¿SDMA PROGRAMA ALGÚN REGISTRO DE MMU EN GFX8?

### 2.1 · La medida bruta: qué registros nombra el fichero

```
  grep -c "mmVM_\|mmATC_"  sdma_v3_0.c   ->  1     (mmVM_INVALIDATE_REQUEST, :1067)
  grep -c "mmVM_\|mmATC_"  sdma_v4_0.c   ->  0     (grep exit 1)
  grep -c "mmATC_"         sdma_v3_0.c   ->  0
  grep -c "mmVM_CONTEXT"   sdma_v3_0.c   ->  0
  grep -c "mmVM_CONTEXT"   sdma_v4_0.c   ->  0
  grep -c 'include "gmc'  sdma_v4_0.c   ->  0     (no incluye ningun header GMC)
```

`sdma_v3_0.c` **incluye** `gmc/gmc_8_1_d.h` (`:38`) — es el header de esta ASIC.
Por eso **puede** nombrar `mmVM_INVALIDATE_REQUEST` y no lo nombra por casualidad.
`sdma_v4_0.c` no incluye ningún header GMC: sus includes son `sdma0..sdma7/*_4_2_*`
y `soc15_common.h` (`:33-52`). **No puede** nombrar un registro de MMU aunque
quisiera: el símbolo no existe en su ámbito de compilación. Eso es la razón
**mecánica** de que el conteo sea 0, y es distinta de la razón de que en GFX8 no
corra.

### 2.2 · La respuesta, y el modo de fallo que casi me engaña

**SDMA no programa ningún registro de MMU por su cuenta. Cero. Ni `mmVM_CONTEXT*`
ni `mmATC_*` ni ningún otro.** Lo único que nombra es una lectura-espera:

`sdma_v3_0.c:1058-1073`, la función entera:

```c
static void sdma_v3_0_ring_emit_vm_flush(struct amdgpu_ring *ring,
					 unsigned vmid, uint64_t pd_addr)
{
	amdgpu_gmc_emit_flush_gpu_tlb(ring, vmid, pd_addr);      <-- :1061

	/* wait for flush */
	amdgpu_ring_write(ring, SDMA_PKT_HEADER_OP(SDMA_OP_POLL_REGMEM) |
			  SDMA_PKT_POLL_REGMEM_HEADER_HDP_FLUSH(0) |
			  SDMA_PKT_POLL_REGMEM_HEADER_FUNC(0)); /* always */
	amdgpu_ring_write(ring, mmVM_INVALIDATE_REQUEST << 2);    <-- :1067
	amdgpu_ring_write(ring, 0);
	amdgpu_ring_write(ring, 0); /* reference */
	amdgpu_ring_write(ring, 0); /* mask */
	amdgpu_ring_write(ring, SDMA_PKT_POLL_REGMEM_DW5_RETRY_COUNT(0xfff) |
			  SDMA_PKT_POLL_REGMEM_DW5_INTERVAL(10));
}
```

Tres cosas, y las tres importan:

1. **El nombre del registro aparece dentro de un `POLL_REGMEM`**, no de un write.
   `FUNC(0) /* always */` y `mask = 0`: es un *poll* de un registro, y con máscara
   cero el paquete no espera a ninguna transición. Es exactamente el mismo
   defecto que `1411` mide en `gfx_v8_0.c:6204-6213` por el camino PM4 — aquí por
   el camino SDMA. **No lo repito, lo extiendo**: el patrón está en los dos
   motores de esta ASIC, no es un descuido del autor del PM4.
2. **El `<< 2` convierte el offset de byte a offset de dword.** `mmVM_INVALIDATE_REQUEST`
   es `0x51e` (`gmc/gmc_8_1_d.h:615`); `0x51e << 2 = 0x1478`. El campo de dirección
   del `POLL_REGMEM` de SDMA es un índice de dword. `gfx_v8_0.c:6209` escribe
   `mmVM_INVALIDATE_REQUEST` **sin** desplazar, porque el campo equivalente del PM4
   es una dirección de byte. **El mismo registro, codificado en dos unidades
   distintas según el motor.** Un driver propio que copie la línea del PM4 al
   paquete SDMA está copiando un error de factor 4.
3. **La escritura real la hace el GMC, no el SDMA.** `amdgpu_gmc_emit_flush_gpu_tlb`
   (`amdgpu_gmc.h:373`) es un macro que despacha a
   `adev->gmc.gmc_funcs->emit_flush_gpu_tlb`, y para GFX8 eso es
   `gmc_v8_0_emit_flush_gpu_tlb` (`gmc_v8_0.c:662`, instalado en `:1730`):

```c
static uint64_t gmc_v8_0_emit_flush_gpu_tlb(struct amdgpu_ring *ring,
					    unsigned int vmid, uint64_t pd_addr)
{
	uint32_t reg;

	if (vmid < 8)
		reg = mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + vmid;     <-- :668
	else
		reg = mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + vmid - 8;
	amdgpu_ring_emit_wreg(ring, reg, pd_addr >> 12);         <-- :671

	/* bits 0-15 are the VM contexts0-15 */
	amdgpu_ring_emit_wreg(ring, mmVM_INVALIDATE_REQUEST, 1 << vmid);
	return pd_addr;
}
```

`amdgpu_ring_emit_wreg` (`amdgpu_ring.h:448`) acaba en
`sdma_v3_0_ring_emit_wreg` (`sdma_v3_0.c:1075`), que **sí** es una escritura:

```c
	amdgpu_ring_write(ring, SDMA_PKT_HEADER_OP(SDMA_OP_SRBM_WRITE) |
			  SDMA_PKT_SRBM_WRITE_HEADER_BYTE_EN(0xf));
```

> **El mismo anillo, la misma función `emit_wreg`, y sin embargo la escritura la
> describe `gmc_v8_0.c` y no `sdma_v3_0.c`.** El SDMA es el **carro**; el GMC es el
> que decide **qué** registro y **qué** valor. `sdma_v3_0.c` no sabe qué es
> `mmVM_CONTEXT0`. Eso responde B con el alcance correcto: *alcanza* a
> `mmVM_CONTEXT*` **por POWER** (a través de un puntero a función que el GMC
> instaló), **nunca por NOMBRE**.

### 2.3 · `mmATC_*`: ni por nombre ni por power

El grep da 0 en ambos ficheros SDMA. Los únicos `WREG32(mmATC_*)` del árbol
alcanzable están en `gmc_v8_0.c` y son **otro registro**:

```
  gmc_v8_0.c:1525, 1561, 1605, 1641    WREG32(mmATC_MISC_CG, data)
```

`mmATC_MISC_CG` es el **clock gating del ATC**, escrito dentro de
`fiji_update_mc_medium_grain_clock_gating` (`:1500`) y sus hermanas, que son
rutinas de power management. No es un registro de page table. La única lectura de
`mmATC_VMID0_PASID_MAPPING` es `gmc_v8_0.c:627`, en
`gmc_v8_0_flush_gpu_tlb_pasid`, y es un `RREG32` **de lectura**. Sus escritores,
según `1166`, `1177` y `1178`, son `gmc_v8_0_emit_pasid_mapping` (que escribe
`mmIH_VMID_0_LUT`, **otro** registro, `gmc_v8_0.c:682`) y dos punteros de KFD en
tablas de dispatch sin invocación.

**`PROVEN`: en el camino alcanzable de Polaris12, ningún escritor de SDMA alcanza
ningún `mmATC_*` de page table.**

### 2.4 · Tabla de B

| registro | lo nombra SDMA | lo escribe SDMA | cómo llega si llega |
|---|---|---|---|
| `mmVM_CONTEXT{0,8}_PAGE_TABLE_BASE_ADDR` | no (0 ocurrencias) | **sí, por power** | `emit_vm_flush` → macro GMC → `gmc_v8_0.c:671` → `SRBM_WRITE` |
| `mmVM_INVALIDATE_REQUEST` | **sí** (`:1067`) | no | solo `POLL_REGMEM`, `FUNC(0)`, `mask=0` |
| `mmVM_CONTEXT*_CNTL` | no | no | los escribe `gmc_v8_0.c` en CPU (`:891`, `:929`) |
| `mmIH_VMID_0_LUT` | no | **sí, por power** | `amdgpu_vm.c:848` → `gmc_v8_0.c:682` → `SRBM_WRITE` |
| `mmATC_VMID0_PASID_MAPPING` | no | no | sin escritor alcanzable (`1177`/`1178`) |
| `mmATC_MISC_CG` | no | no | clock gating, `gmc_v8_0.c` en CPU |

### 2.5 · Lo que SDMA sí programa: datos, no control

El resto del MMU que toca SDMA no lo programan registros sino **entradas de tabla**,
por tres paquetes (`sdma_v3_0.c:925`, `:952`, `:982`, con el dispatch en
`amdgpu_vm_sdma.c:187-203`):

```
  SDMA_OP_GEN_PTEPDE / SDMA_OP_WRITE / SDMA_OP_COPY     tonga_sdma_pkt_open.h:37,27,28
```

`023` mide los tres y su tabla es correcta. No la repito. Lo que **no** estaba
dicho y sale de aquí:

> **El productor de PTE de GFX8 es un emisor de paquetes, no un escritor de
> registros. Los dos caminos son disjuntos y no se tocan: los *registros* de MMU
> los escribe el GMC desde CPU (`gmc_v8_0.c` en WREG32) o desde el anillo vía
> `emit_wreg`; las *entradas* de tabla las escribe el SDMA con tres paquetes que
> no nombran ningún registro. Un driver propio tiene que implementar las dos
> mitades y no puede confundirlas: la primera es un `writeq` de 32 bits con
> desplazamiento de PFN, la segunda es un emisor de 9 dwords.**

### 2.6 · Una diferencia que solo se ve al comparar las dos tablas

`sdma_v3_0.c:982-997` y `sdma_v4_0.c:1643-1659` emiten **el mismo paquete** con
**un dword distinto**:

```
  sdma_v3_0.c:996    ib->ptr[ib->length_dw++] = count;        /* number of entries */
  sdma_v4_0.c:1658   ib->ptr[ib->length_dw++] = count - 1;    /* number of entries */
```

Y el opcode tiene nombre distinto en cada generación:

```
  tonga_sdma_pkt_open.h:37    #define SDMA_OP_GEN_PTEPDE  12
  vega10_sdma_pkt_open.h:37    #define SDMA_OP_PTEPDE      12
```

Mismo valor, mismo significado, **distinto convenio de conteo** (inclusivo vs
exclusivo). Esto es `PROVEN` sobre el corpus y es exactamente el tipo de cosa que
hace que copiar un paquete de la generación equivocada funcione en un caso y
escriba una entrada de mas en el borde. `sdma_v4_0.c` es la generación equivocada
para esta placa (`:1.3`) — **pero su semántica de `count` es la que hay que
entender para no equivocarse al reimplementar la buena.**

---

## 3 · C) LA INTEGRACIÓN CON EL GART

### 3.1 · De dónde sale la dirección del GART

Hay **dos**producer de direcciones GART en el camino alcanzable, y ninguno de los
dos está en `sdma_v3_0.c`.

**Productor 1 — el BO de la propia tabla GART.** `amdgpu_ttm_map_buffer`
(`amdgpu_ttm.c:199-285`) calcula:

```c
	dst_addr = amdgpu_bo_gpu_offset(adev->gart.bo);                    <-- :261
	dst_addr += (entity->gart_window_offs[window] >> AMDGPU_GPU_PAGE_SHIFT) * 8;
	amdgpu_emit_copy_buffer(adev, &job->ibs[0], src_addr,
				dst_addr, num_bytes, 0);                     <-- :263
```

`amdgpu_emit_copy_buffer` (`amdgpu_sdma.h:191`) ->
`buffer_funcs->emit_copy_buffer`, que para esta ASIC es
`sdma_v3_0_emit_copy_buffer` (`sdma_v3_0.c:1631`, instalado en `:1679`), es decir
**un `SDMA_OP_COPY / SDMA_SUBOP_COPY_LINEAR` de 7 dwords**.

El GART **no** se direcciona por un offset propio: `amdgpu_bo_gpu_offset_no_check`
(`amdgpu_object.c:1520`) resuelve un `TTM_PL_TT` por
`amdgpu_gmc_agp_addr`, y **si eso falla cae a `amdgpu_ttm_domain_start(TTM_PL_TT)`
que es `adev->gmc.gart_start`** (`amdgpu_ttm.c:714-724`).

Y aquí está el detalle que hace que esto sea un régimen y no un accidente:
**`amdgpu_gmc_agp_addr` siempre falla en GFX8.** `gmc_v8_0.c:420` llama a
`amdgpu_gmc_set_agp_default`, que pone `agp_start = 0xffffffffffff`, `agp_end = 0`,
`agp_size = 0` (`amdgpu_gmc.c:401-403`), y **`amdgpu_gmc_agp_location` no se llama
nunca desde `gmc_v8_0.c`** (verificado: sus 4 llamantes son `gmc_v9_0.c:1664`,
`gmc_v10_0.c:664`, `gmc_v11_0.c:669`, `gmc_v12_0.c:706`). Con `agp_size = 0`, la
guarda de `amdgpu_gmc.c:198` es siempre cierta:

```c
	if (bo->ttm->dma_address[0] + PAGE_SIZE >= adev->gmc.agp_size)
		return AMDGPU_BO_INVALID_OFFSET;
```

> **`PROVEN`: el AGP está muerto en Polaris12 y el GART es el único camino.** No es
> que el AGP se prefiera o se evite: es que `agp_size == 0` lo invalida siempre.
> `mmMC_VM_AGP_TOP` se programa a `0 >> 22 = 0` y `mmMC_VM_AGP_BOT` a
> `0xffffffffffff >> 22 = 0x3ffffff` (`gmc_v8_0.c:485-487`): **la ventana de AGP se
> programa invertida, de `0x3ffffff` a `0`.** El hardware la rechaza; el driver no
> se queja.

**Productor 2 — la dirección de la ventana, para el TTM.** La dirección que ve el
motor es `amdgpu_compute_gart_address` (`amdgpu_ttm.h:226-231`):

```c
	return gmc->gart_start + entity->gart_window_offs[index];
```

y se llama en `amdgpu_ttm.c:244`. Los offsets salen de
`amdgpu_ttm_buffer_entity_init` (`amdgpu_ttm.c:2065-2069`):

```c
		entity->gart_window_offs[i] =
			amdgpu_gtt_node_to_byte_offset(&entity->gart_node) +
				i * GTT_MAX_PAGES * PAGE_SIZE;
```

con `GTT_MAX_PAGES = (AMDGPU_GTT_MAX_TRANSFER_SIZE >> PAGE_SHIFT) = 1024`
(`amdgpu_ttm.h:42`, `amdgpu_ttm.c:214`). Cada ventana son **4 MiB**.

### 3.2 · Geometría medida para Polaris12

| magnitud | valor | fuente |
|---|---|---|
| `gart_size` por defecto | **256 MiB** | `gmc_v8_0.c:597,600` (`CHIP_POLARIS12` cae en el `default:` con `SZ_256M`) |
| `num_gpu_pages` | 65536 | `amdgpu_gart.c:533`, `256 MiB / 4 KiB` |
| `gart.table_size` | **524288 bytes (512 KiB)** | `gmc_v8_0.c:954`, `num_gpu_pages * 8` |
| `AMDGPU_GPU_PAGE_SIZE` | 4096 | `amdgpu_gart.h:35` |
| `AMDGPU_GPU_PAGES_IN_CPU_PAGE` | 1 | `amdgpu_gart.h:40` (en x86-64) |
| `GART` en el `drm_mm` | `0 .. gart_size>>12` | `amdgpu_gtt_mgr.c:366` |
| ventana GART TTM | 4 MiB (1024 paginas) | `amdgpu_ttm.c:2068` |
| ventanas por entidad de movimiento | 2 | `amdgpu_ttm.c:2384` |
| **GART consumido por 2 ventanas** | **8 MiB de 256 MiB = 3.1 %** | derivado |

### 3.3 · Validación y asserts: la tabla

Medido sobre el camino GART alcanzable. La columna de la derecha es lo que un
driver propio tiene que reimplementar, porque **cada `BUG_ON` es un invariante
que el upstream está asertando en hardware y que nadie más comprueba**.

| sitio | construcción | qué asegura |
|---|---|---|
| `amdgpu_ttm.c:216-217` | `BUG_ON(copy_max_bytes < GTT_MAX_PAGES * PAGES_IN_CPU_PAGE * 8)` | umbral 8192; `sdma_v3_0` da `0x3fffe0` = 4194272. Margen x512 |
| `amdgpu_ttm.c:219-220` | `WARN_ON(mem_type == AMDGPU_PL_PREEMPT) -> -EINVAL` | el preempted no se mapea por GART |
| `amdgpu_ttm.c:240` | `num_pages = min(num_pages, GTT_MAX_PAGES)` | recorta, no aborta |
| `amdgpu_ttm.c:2052-2053` | `if (ARRAY_SIZE(gart_window_offs) < num_gart_windows) return -EINVAL` | **el unico assert de las ventanas**: el array es `[2]` (`amdgpu_ttm.h:59`) |
| `amdgpu_gart.c:362-363` | `if (!drm_dev_enter(...)) return` | no mapear durante el reset |
| `amdgpu_gart.c:401` | `WARN_ON_ONCE(flags & AMDGPU_PTE_SYSTEM)` en `map_vram_range` | el rango VRAM no lleva SYSTEM |
| `amdgpu_vm_sdma.c:116` | `WARN_ON(ib->length_dw == 0)` | IB no vacio al commitear |
| `amdgpu_vm_sdma.c:122` | `WARN_ON(ib->length_dw > p->num_dw_left)` | no desbordar el IB |

**Y un hueco medido, que es la parte accionable de C:**

```c
uint64_t amdgpu_vm_map_gart(const dma_addr_t *pages_addr, uint64_t addr)
{
	/* page table offset */
	result = pages_addr[addr >> PAGE_SHIFT];     <-- amdgpu_vm.c:953
```

**No hay ninguna comprobación.** Ni de rango contra `gart_size`, ni de que
`pages_addr` tenga `addr >> PAGE_SHIFT` entradas, ni un `WARN_ON`. Es un indice
crudo en un array cuyo tamaño es `ttm->num_pages` (`amdgpu_vm.c:1316`), y el
llamante es `amdgpu_vm_sdma.c:283`, en el bucle que rellena el IB. Un `addr` fuera
de rango lee fuera del array. En el upstream el invariante lo sostiene el caller
(`amdgpu_vm.c:1178-1208`); **en un driver propio es una aserción que hay que
escribir**, porque el caller es tuyo.

Lo mismo en `amdgpu_gmc_set_pte_pde` (`amdgpu_gmc.c:163-178`): cinco líneas,
`writeq(value, ptr + gpu_page_idx * 8)`, **cero validación de `gpu_page_idx`
contra `gart.table_size`**.

### 3.4 · Lo que el GART le da a SDMA, en una frase

```
  GART = 256 MiB de aperture, 65536 entradas de 8 bytes en VRAM (512 KiB),
  base alineada a 4 GiB por amdgpu_gmc_gart_location (BEST_FIT),
  AGP muerto (agp_size = 0), 2 ventanas de 4 MiB para TTM,
  el SDMA escribe en la tabla del GART con SDMA_OP_COPY de 7 dwords,
  y ninguna de esas dos operaciones tiene un assert de rango.
```

---

## 4 · CORRECCIONES A `023`, `047` Y LA CADENA DE `035`

**`023` acierta en la conclusión y tiene dos citas mal numeradas.** Su CUDA ("el
productor de PTE en GFX8 es un paquete SDMA de 9 dwords, `SDMA_OP_GEN_PTEPDE`") es
correcta, y su `CORRECTED_BY=035` se autorefuta con un argumento que **yo
confirmo**: `sdma_v3_0.c` es el fichero que corre (§1.2). Sus tres Producer están
en las líneas correctas (`amdgpu_gmc.c:163`, `sdma_v3_0.c:982`, `:952`, `:925`).
Pero:

- **Cita `vi.c:2107` como "la línea que añade `sdma_v3_1_ip_block`".** La 2107
  es `case CHIP_POLARIS12:`. El add está en **2113**. Corregido arriba (§1.2).
- **`023` no mide el alcance del fichero, solo su contenido.** Dice "producer de
  PTE en GFX8" y lista cuatro tablas de dos ficheros (`gfx_v6_0`, `gfx_v7_0`,
  `gfx_v8_0`, `gmc_v8_0`, `sdma_v3_0`) como "ficheros barrados", lo que es
  correcto y **no** dice cuál corre. La pregunta "¿quién elige este fichero?"
  sigue abierta después de `023`, y este hallazgo la cierra.

**`047` no se equivoca sobre SDMA**, pero su hallazgo es sobre otro tema (el canal
SMC con argumento) y su tabla de HWIP marca `SDMA0_HWIP` como `INALCANZABLE`, lo
que **coincide con lo que aquí se mide**: el selector de versión de SDMA no
decide nada en esta ASIC. No lo contradigo: lo confirmo con un mecanismo distinto
(`amdgpu_device.c:2148`).

**La cadena de `035` queda cerrada.** `035` leyó `sdma_v4_0.c`; este hallazgo
muestra por qué eso no podía funcionar: no es solo que el fichero sea de otra
generación, es que **no se enlaza en la tabla de esta ASIC**. `023` ya lo había
dicho; ahora está medido con el `break` de `amdgpu_device.c:2148` como causa.

---

## 5 · ESTADO Y LO QUE NO SE AFIRMA

```text
  A) ALCANCE DE SDMA EN CHIP_POLARIS12                         PROVEN
     tabla que se instala        sdma_v3_1_ip_block   vi.c:2113
     tabla que se ejecuta        sdma_v3_0_ip_funcs   sdma_v3_0.c:1544
     fichero                      sdma_v3_0.c         (NO sdma_v4_0.c)
     causa de la exclusion        amdgpu_device.c:2148  break antes del default
     sdma_v4_0.c ejecutable      NO                  PROVEN
     ficheros SDMA alcanzables   1 de 10             PROVEN
     .o compilados               10                   no es evidencia
     instancias                  2                   sdma_v3_0.c:1102 + vid.h:28
     firmware                    polaris12_sdma{1}.bin  sdma_v3_0.c:289
     sin cola de paginas         has_page_queue = 0  (0 ocurrencias en sdma_v3_0.c)
     soporte de 64 bits          NO                  sdma_v3_0.c:1568 -> ptr_mask = buf_mask

  B) SDMA Y LOS REGISTROS DE MMU                               PROVEN CON ALCANCE
     mmVM_CONTEXT*  nombrados    0     en ambos ficheros
     mmATC_VMID0_*  nombrados    0     en ambos ficheros
     escrituras de MMU propias   NINGUNA por nombre
     escritas por power          mmVM_CONTEXT{0,8}_PAGE_TABLE_BASE_ADDR
                                 y mmIH_VMID_0_LUT, via emit_wreg = SRBM_WRITE
     unico registro nombrado     mmVM_INVALIDATE_REQUEST, y solo como POLL
     ese poll espera?            NO  FUNC(0) always, mask = 0   (mismo defecto
                                 que 1411 mide en el camino PM4; aqui es extensible)
     unidades del poll           <<2 -> indice de dword, frente a byte en PM4
     contraste de generacion     count (v3_0:996) vs count-1 (v4_0:1658)
                                 GEN_PTEPDE vs PTEPDE, mismo opcode 12

  C) GART                                                            PROVEN CON HUECO
     gart_size Polaris12         256 MiB   gmc_v8_0.c:597,600
     num_gpu_pages / table_size  65536 / 524288 bytes
     AGP                         MUERTO     agp_size = 0, amdgpu_gmc.c:401-403
     ventana de AGP en HW        invertida  AGP_TOP=0, AGP_BOT=0x3ffffff
     ventanas TTM                2 x 4 MiB = 8 MiB (3.1 % del GART)
     asserts en el camino        8, tabulados en §3.3
     rango de pages_addr         SIN ASSERT   amdgpu_vm.c:953
     rango de gpu_page_idx       SIN ASSERT   amdgpu_gmc.c:175

  LO QUE NO SE AFIRMA
     - que sdma_v4_0.c este mal escrito. Esta bien para Vaga. Lo que se afirma
       es que GFX8 no lo selecciona, que es la misma forma que 1403.
     - nada sobre el hardware. Cero MMIO, cero ejecucion, GPU INTACTA.
     - que los 8 asserts del camino GART sean suficientes. Son los que tiene el
       upstream; el hueco de rango es real yesta medido, no supuesto.

  LIMITACION
     el corpus es solo drivers/gpu/drm/amd. Las definiciones de SZ_256M, PAGE_SIZE
     y de las masks de page table viven en include/linux y en asic_reg/; SZ_256M
     se cita por el simbolo que usa gmc_v8_0.c, no por su valor numerico ledido.

  corpus   solo lectura (rx550-upstream-7.2.8/linux-7.2.8/drivers/gpu/drm/amd/)
  GPU      INTACTA
  sudo     NO usado
  target   0000:01:00.0 (RX550). La iGPU 0000:00:02.0 no se ha tocado.
```

## 6 · LO QUE ESTE HALLAZGO DEJA ABIERTO

Tres cosas, con su discriminante, porque son las que un driver propio tiene que
resolver antes de escribir una línea de SDMA:

1. **El `POLL_REGMEM` con `FUNC(0)` y `mask=0` no espera.** Es `PROVEN` sobre el
   codigo. *Por que el hardware tolera eso* es `NOT_DETERMINED` — es la misma
   pregunta que `1411` deja para el PM4, y comparte discriminante.
2. **`count` es inclusivo en GFX8 y exclusivo en Vaga.** `PROVEN` sobre las dos
   tablas. *Que el hardware GFX8 interprete el dw9 como inclusivo* es `RUNTIME`.
3. **El rango de `pages_addr` no esta asertado.** `PROVEN` por lectura. *Si el
   upstream puede alcanzar un `addr` fuera de rango* es `NOT_DETERMINED`: depende
   del caller, y el caller es `amdgpu_vm.c:1178-1208`, que no he medido en esta
   sesion.

Y una cuarta, que es la de la serie de `1403`/`1177`/`1178` y **la sexta** de la
misma familia: **falta el instrumento.** Falta aplicar la prueba de alcance —la de
`tools/unreach.py`— **a `adev->sdma.instance[i].ring.funcs`**: *para cada ASIC que
el driver soporta, que tabla se registra y quien la invoca.* Es un grafo de nueve
ficheros y una funcion (`vi_set_ip_blocks`) y habria detectado esto, y `035`, y
`023`, con el mismo mecanismo. No lo implemento: `tools/unreach.py` es de otra
sesion y el arbol tiene ficheros modificados sin commitear.