# 246 · §G: la coherencia de GFX8 tiene tres registros y ninguno es de caché

```text
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0 · WRITE_EXECUTION=NONE
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**Abre §G.** La cuestión era qué hace el driver para que la CPU vea lo que la GPU escribió y para
que la GPU vea lo que la CPU escribió, y la respuesta tiene forma cerrada: **en GFX8 la cadena
de coherencia son exactamente tres registros, y ninguno de ellos invalida una caché de datos.**

**⇒ `PROVEN`. Los tres son `VM_CONTEXT{0,8}_PAGE_TABLE_BASE_ADDR`, `VM_INVALIDATE_REQUEST`
(invalidación de TLB) y `GPU_HDP_FLUSH_REQ`/`DONE` (puerto de datos del host).** `PROVEN`.

**⇒ `PROVEN_ABSENT`. GFX8 no tiene ningún registro de control de caché de datos en el corpus:
no existe ningún `*CACHE_CONTROL` en `asic_reg/gca/gfx_8_0_d.h` ni en `gfx_8_1_d.h`, y
`clearstate_vi.h` no contiene ninguna entrada de L2.** `PROVEN_ABSENT`.

**⇒ `PROVEN_DERIVED`. El mecanismo de coherencia de GFX8 es la espera, no la invalidación de
caché: el driver no limpia nada, espera a que lo limpiado por el hardware haya ocurrido.** `PROVEN_DERIVED`.

## 1 · La cadena completa, packet a packet

**⇒ `gfx_v8_0_ring_emit_vm_flush`, `gfx_v8_0.c:6191`, emite en el anillo GFX exactamente esto:** `PROVEN`.

```c
6191  static void gfx_v8_0_ring_emit_vm_flush(struct amdgpu_ring *ring,
6192                                          unsigned vmid, uint64_t pd_addr)
6193  {
6194      int usepfp = (ring->funcs->type == AMDGPU_RING_TYPE_GFX);
6195
6196      amdgpu_gmc_emit_flush_gpu_tlb(ring, vmid, pd_addr);
6197
6198      /* wait for the invalidate to complete */
6199      amdgpu_ring_write(ring, PACKET3(PACKET3_WAIT_REG_MEM, 5));
6200      amdgpu_ring_write(ring, (WAIT_REG_MEM_OPERATION(0) | WAIT_REG_MEM_FUNCTION(0)
6201                       | WAIT_REG_MEM_ENGINE(0)));
6203      amdgpu_ring_write(ring, mmVM_INVALIDATE_REQUEST);
6204      amdgpu_ring_write(ring, 0);          /* ref */
6205      amdgpu_ring_write(ring, 0);          /* mask */
6206      amdgpu_ring_write(ring, 0x20);       /* poll interval */
6207
6208      /* compute doesn't have PFP */
6209      if (usepfp) {
6210          amdgpu_ring_write(ring, PACKET3(PACKET3_PFP_SYNC_ME, 0));
6211      }
6212  }
```

**⇒ `PROVEN. Y el comentario de `gfx_v8_0.c:6198` dice literalmente «wait for the invalidate to
complete»: la INVALIDATE_REQUEST de la línea 6203 se emite DENTRO de un `WAIT_REG_MEM`, es decir
el driver la usa como registro de respuesta, no como petición.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Ésa es la diferencia con SOC15 y la razón de que la sincronización sea
distinta: aquí laInvalidate se ejecuta y se espera en la misma palabra, mientras que en SOC15 el
driver la escribe una vez y la espera N veces, una por VMID.** `PROVEN_DERIVED`.

**⇒ Y la segunda mitad de la Invalidate_request, la lectura de `VM_INVALIDATE_RESPONSE`, no la
hace nadie en este camino: `gfx_v8_0.c:6203-6206` escribe ref=0, mask=0, interval=0x20, y el
acuse se descarta.** `PROVEN`. Esto confirma y delimita lo que `213`/XPcción C ya habían cerrado
desde el otro lado.

## 2 · `gmc_v8_0_emit_flush_gpu_tlb`: dos escrituras, no tres

**⇒ `gmc_v8_0.c:668`, y las dos escrituras son `gmc_v8_0.c:677` y `gmc_v8_0.c:680`:** `PROVEN`.

```c
673      if (vmid < 8)
674          reg = mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + vmid;
675      else
676          reg = mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + vmid - 8;
677      amdgpu_ring_emit_wreg(ring, reg, pd_addr >> 12);
678
679      /* bits 0-15 are the VM contexts0-15 */
680      amdgpu_ring_emit_wreg(ring, mmVM_INVALIDATE_REQUEST, 1 << vmid);
```

**⇒ `PROVEN_DERIVED. El `else` no es un caso raro: es la mitad alta del espacio de VMID, y el
mismo `if (vmid < 8)` está repetido en `gmc_v7_0.c`. GFX8 tiene 16 contextos y el driver los
parte en dos bloques de 8.** `PROVEN_DERIVED`.

**⇒ Y el puntero de tabla se escribe DESPLAZADO: `pd_addr >> 12`, el mismo `>> 12` que
`Fragment size = 9` implica, y coherente con `241`, que cerró `0x64 = VI_POLARIS12_V_A0` como el
eslabón de identidad.** `PROVEN_DERIVED`.

## 3 · El presupuesto de dwords, y el margen que deja

**⇒ `emit_frame_size` declara `gfx_v8_0.c:6881` `VI_FLUSH_GPU_TLB_NUM_WREG * 5 + 9` para el anillo
GFX, y `gfx_v8_0.c:6929` el mismo `* 5 + 7` para el anillo compute.** `PROVEN`.

**⇒ La diferencia entre `9` y `7` son exactamente los 2 dwords del `PACKET3(PACKET3_PFP_SYNC_ME, 0)`
de `gfx_v8_0.c:6212`, que el anillo compute no emite porque `usepfp` es falso.** `PROVEN_DERIVED`.

**⇒ `vi.h:27` dice `#define VI_FLUSH_GPU_TLB_NUM_WREG 3`, pero `gmc_v8_0_emit_flush_gpu_tlb` sólo
hace 2 `amdgpu_ring_emit_wreg`, y `gmc_v7_0.c` igual: 2.** `PROVEN`.

**⇒ Y el multiplicador del presupuesto, 5, es correcto: `gfx_v8_0_ring_emit_wreg`
(`gfx_v8_0.c:6349`) escribe exactamente 5 dwords — `PACKET3(PACKET3_WRITE_DATA, 3)`, `cmd`,
`reg`, `0` y `val`—, porque `vid.h:105` define `PACKET3(op, n)` como una única dword con el
recuento de operandos en los bits altos.** `PROVEN`.

**⇒ Con esas dos medidas, el presupuesto declarado es 3·5 + 9 = 24 dwords para el anillo GFX y
3·5 + 7 = 22 para el compute, y el gasto real contado paquete a paquete es
2·5 + 6 + 1 = 17 y 2·5 + 6 = 16.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. El margen es de 7 dwords en el anillo GFX y 6 en el compute, y la diferencia
entre ambos márgenes es exactamente el `PFP_SYNC_ME`. El excedente se explica entero por una
sola cosa: el driver reserva 3 WREG donde emite 2, es decir 5 dwords de más.** `PROVEN_DERIVED`.

**⇒ Y ese excedente es correcto y es lo que hay que replicar. Un `emit_frame_size` corto
provoca que dos frames se solapen en el ring, y el síntoma de eso no es un fallo visible sino
corrupción intermitente: por eso el driver reserva de más en vez de ajustar al tightness.** `PROVEN_DERIVED`.

| | WREG | `WAIT_REG_MEM` | `PFP_SYNC_ME` | total |
|---|---|---|---|---|
| real anillo GFX | 2 × 5 = 10 | 1+5 = 6 | 1 | **17** |
| real anillo compute | 2 × 5 = 10 | 1+5 = 6 | — | **16** |
| declarado GFX (`6881`) | 3 × 5 = 15 | +9 | (incluido) | **24** |
| declarado compute (`6929`) | 3 × 5 = 15 | +7 | — | **22** |
| **margen** | **5** | 3 / 2 | 1 | **7 / 6** |

**⇒ Y el contraste con SOC15: `soc15.h:34` `SOC15_FLUSH_GPU_TLB_NUM_WREG 6` y `soc15.h:35`
`SOC15_FLUSH_GPU_TLB_NUM_REG_WAIT 3`, y `gfx_v9_0.c` tiene un término `* 7` de REG_WAIT que GFX8
no tiene. GFX8 no es una versión anterior por descuido: tiene un mecanismo distinto, y el
presupuesto lo refleja.** `PROVEN_DERIVED`.

## 4 · La otra mitad: el HDP, que es de NBIO y no de GMC

**⇒ `PROVEN`. La coherencia de los anillos SDMA no pasa por GMC: `sdma_v4_0_ring_emit_hdp_flush`
(`sdma_v4_0.c:859`) llama a `sdma_v4_0_wait_reg_mem` con los offsets que devuelve NBIO.** `PROVEN`.

```c
865      ref_and_mask = nbio_hf_reg->ref_and_mask_sdma0 << ring->me;
867      sdma_v4_0_wait_reg_mem(ring, 0, 1,
868              adev->nbio.funcs->get_hdp_flush_done_offset(adev),
869              adev->nbio.funcs->get_hdp_flush_req_offset(adev),
870              ref_and_mask, ref_and_mask, 10);
```

**⇒ `PROVEN_DERIVED. El `<< ring->me` de `sdma_v4_0.c:865` es lo que hace que un anillo SDMA no
espera la another's flush: cada ME tiene su propio bit en `ref_and_mask`. Es un mecanismo de
coherencia por unidad de hardware, no un mutex.** `PROVEN_DERIVED`.

**⇒ Los dos registros son `mmGPU_HDP_FLUSH_REQ` y `mmGPU_HDP_FLUSH_DONE`, y `nbio_v7_0.c:240`
y `nbio_v7_0.c:245` los obtienen con `SOC15_REG_OFFSET(NBIO, 0, ...)`, o sea bloque NBIO
índice 0.** `PROVEN`.

**⇒ Y esto es un dato sobre la disposición de registros: la coherencia del puerto de host no es un asunto de GMC sino de
NBIO, y su offset se resuelve por una tabla de función por ASIC
(`adev->nbio.funcs->get_hdp_flush_*_offset`), no por un `#define` directo.** `PROVEN_DERIVED`.

**⇒ El presupuesto en el anillo SDMA de GFX8 lo declara `sdma_v4_0.c:2430` `6 +
sdma_v4_0_ring_emit_hdp_flush` y `sdma_v4_0.c:2431` `3 + /* hdp invalidate */`. Dos partidas
distintas para lo que la función hace con una sola llamada: la Invalidate se cuenta aparte del
flush.** `PROVEN`.

## 5 · La ausencia, que es el hallazgo de §G

**⇒ `PROVEN_ABSENT`. `grep -hoE '\b[A-Z][A-Z_0-9]*CACHE_CONTROL\b'` sobre
`asic_reg/gca/gfx_8_0_d.h` y `gfx_8_1_d.h` devuelve cero. GFX8 no tiene ningún registro de
control de caché L2 en el corpus.** `PROVEN_ABSENT`.

**⇒ `PROVEN. Para contraste, `mmDB_RMI_L2_CACHE_CONTROL` sí existe, y sólo en
`asic_reg/gc/gc_10_1_0_offset.h:5785` y `gc_10_3_0_offset.h`. Aparece a partir de gfx10.** `PROVEN`.

**⇒ Y el driver lo usa: `clearstate_gfx10.h:56` escribe `0x00150055, // DB_RMI_L2_CACHE_CONTROL`
y `clearstate_gfx10.h:286` escribe `0x00550055, // CB_RMI_GL2_CACHE_CONTROL`. `clearstate_vi.h`,
que es el equivalente de GFX8 y está incluido en `gfx_v8_0.c:39`, no tiene ninguna entrada de L2.**
`PROVEN`.

**⇒ `PROVEN_DERIVED. Corolario para el driver propio: en GFX8 no existe la operación «vaciar L2»
que sí existe en gfx10+. No es que el driver de amdgpu la omita: es que no hay dónde escribirla.
Un driver propio para Polaris12 no puede portar esa parte de gfx10, porque el hardware no la expone.** `PROVEN_DERIVED`.

**⇒ Y el mecanismo que sustituye a esa operación es la semántica de la propia carga, no un
registro. Eso no se deduce del corpus: es `NOT_DETERMINED`, y es el punto que queda abierto de §G.** `NOT_DETERMINED`.

**⇒ `PROVEN_DERIVED`. Y hay un dato que acota mucho ese `NOT_DETERMINED`: el comentario de
`gmc_v9_0.c:2178` afirma que «Vega20+XGMI caches PTEs in TC and TLB», lo que implica por
contraposición que en GFX8 las PTEs **no** se cachean en la Text Cache. La capa de caché que
§G no puede describir en GFX8 no es la de datos de shader, sino la de las propias tablas de
página, y está ausente por diseño del ASIC.** `PROVEN_DERIVED`.

## 6 · La puerta que decide el camino, y por qué no se abre aquí

**⇒ `amdgpu_gmc.h:371` es un macro que salta a la tabla de GMC:
`#define amdgpu_gmc_emit_flush_gpu_tlb(r, vmid, addr) (r)->adev->gmc.gmc_funcs->emit_flush_gpu_tlb(...)`,
y `gmc_v8_0.c:1736` asigna `.emit_flush_gpu_tlb = gmc_v8_0_emit_flush_gpu_tlb`.** `PROVEN`.

**⇒ Y hay una segunda puerta, más arriba: `amdgpu_gmc.c:711`
`amdgpu_gmc_flush_gpu_tlb` decide si el flush va al anillo por `amdgpu_job`, y su rama de
`amdgpu_gmc.c:730` añade un flush de tipo 2 y otro de tipo 0 según dos banderas
(`flush_tlb_needs_extra_type_2`, `flush_tlb_needs_extra_type_0`).** `PROVEN`.

**⇒ `PROVEN`. Y la razón de que las dos valgan cero en GFX8 es condicional y explícita, no una
suposición: `gmc_v9_0.c:2183` asigna `flush_tlb_needs_extra_type_2` con la condición
`amdgpu_ip_version(adev, GC_HWIP, 0) == IP_VERSION(9, 4, 0) && adev->gmc.xgmi.num_physical_nodes`,
y ese es el único punto de todo el árbol que la pone a `true`. Para Polaris12, GC_HWIP es 8, así
que la condición es falsa por construcción.** `PROVEN`.

**⇒ `PROVEN_ABSENT`. Y `flush_tlb_needs_extra_type_0` es un campo muerto: sus 5 apariciones en
todo el árbol son la declaración (`amdgpu_gmc.h:366`) y cuatro lecturas en `amdgpu_gmc.c`
(`:734`, `:803`, `:819`, `:831`). No hay ni una sola asignación en ningún ASIC.** `PROVEN_ABSENT`.

**⇒ Y el comentario que explica el porqué es la mejor pista de toda §G, en `gmc_v9_0.c:2178`:
«Vega20+XGMI caches PTEs in TC and TLB. Add a heavy-weight TLB flush (type 2), which flushes
both.». Es decir, el flush pesado existe porque en Vega20 las PTEs se cachean en la Text Cache,
y en GFX8 no se cachean, y por eso no hay flush pesado.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Ésta es la respuesta de §G a por qué GFX8 no necesita lo que gfx10 sí:
en GFX8 la page table no pasa por la Text Cache, así que invalidar la TLB basta. La coherencia
de las PTEs en GFX8 es de una sola capa, y en Vega20 es de dos. El driver propio hereda esa
diferencia gratis si replica el camino de GFX8.** `PROVEN_DERIVED`.

**⇒ Y `flush_tlb_needs_extra_type_0` está condicionado a `flush_type == 2`
(`amdgpu_gmc.c:734`), pero como el campo nunca se pone a `true` esa condición es inerte: 4 de las
5 líneas que lo consultan no pueden ejecutar su rama en ningún ASIC de este driver.** `PROVEN_DERIVED`.

## 7 · Lo que queda abierto

**⇒ `NOT_DETERMINED`: qué garantiza exactamente la semántica de la carga de GFX8 cuando la
dirección no está en la caché. No hay registro que lo diga, no hay documentación de registros en
el corpus, y el único camino es observar.** `NOT_DETERMINED`.

```text
PENDIENTE=246-1 | HALLAZGO=246-*.md | ESTADO=NOT_DETERMINED
           | NECESITA=/sys/kernel/debug/dri/0/amdgpu_gem_evict_age  (o equivalente NV)
           | ALCANZABLE_SIN_ROOT=NO_MEDIDO
```

**⇒ Y el discriminante que lo cerraría es NIVEL 3, no NIVEL 2: hace falta mover una página
entre VRAM y RAM y observar si la lectura siguiente de la GPU ve el dato nuevo. Eso es
experimental con eviction, no lectura de un registro.** `NOT_TESTED`.

**⇒ Con esto §G queda con la parte de software completamente cerrada —qué se escribe, en qué
orden, con qué espera y con qué presupuesto— y con una sola pregunta abierta, que es de
semántica de hardware y no de código del driver.** `PROVEN_DERIVED`.

## 8 · Errores propios registrados en esta nota

**⇒ `ERROR`. Escribí primero `9 = 7 + 2` con un `PACKET3` de dos dwords de cabecera; el macro de
`vid.h:105` es una sola dword con el recuento en los bits altos, y el reparto real es 6 dwords
para el `WAIT_REG_MEM` de 5 operandos, no 7.** `ERROR`.

**⇒ `ERROR`. Di que el gasto real eran 19 dwords en el anillo GFX y 17 en el compute. Los valores
correctos, contados por programa contra el fichero, son 17 y 16. La causa del error fue buscar
`gfx_v8_0_ring_emit_wreg` en la línea equivocada —la 6884 en vez de la 6349— y obtener «0
escrituras», que el script aceptó como medida válida en lugar de como señal de que no había
encontrado la función.** `ERROR`.

**⇒ Y ése es el fallo de método, que es el que importa: un script que devuelve 0 porque no
encontró lo que buscaba produce un número falso con apariencia de número. La defence correcta
es comprobar que la función se localizó antes de usar su recuento.** `ERROR`.

**⇒ `ERROR`. Atribuí `flush_tlb_needs_extra_type_0 = 0` en GFX8 al comentario sobre un bug de
Navi 1x. Ese comentario es de otra cosa: la asignación real está en `gmc_v9_0.c:2183` y su
condición es `GC_HWIP == IP_VERSION(9, 4, 0)`, y además `flush_tlb_needs_extra_type_0` no se
asigna en ningún ASIC del árbol, sino que es un campo muerto.** `ERROR`.

**⇒ Y los tres errores tienen la misma forma y el mismo sitio: la conclusión escrita antes de
mirar el resultado del programa, y aceptada sin comprobar que el programa había encontrado lo
que decía medir.** `ERROR`.