# 068 · La cadena de emisión de §D está entera en 26 líneas, y su aritmética cuadra

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC · CORPUS=RESEARCH/working/linux-7.1.3
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · WORK_CLASS=READ_ONLY/EVIDENCE
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

El orden de emisión de software de §D —`PTBA` → `INVALIDATE` → `WAIT` →
`PFP_SYNC_ME`— está **cerrado como secuencia de texto**, con los valores exactos
de cada paquete, en `gfx_v8_0.c:6191-6215`.

Lo importante: **esto no cierra §D**. Cierra la mitad del lado software y deja
bien delimitado qué queda sin resolver. Y también confirma que las invalidaciones
de TLB van **por ring**, no por MMIO directo — un dato de §C que no estaba
registrado.

## La secuencia completa

```
gfx_v8_0.c:6191  static void gfx_v8_0_ring_emit_vm_flush(ring, vmid, pd_addr)
gfx_v8_0.c:6194      int usepfp = (ring->funcs->type == AMDGPU_RING_TYPE_GFX);
gfx_v8_0.c:6196      amdgpu_gmc_emit_flush_gpu_tlb(ring, vmid, pd_addr);
gfx_v8_0.c:6199      PACKET3(PACKET3_WAIT_REG_MEM, 5)
gfx_v8_0.c:6200          WAIT_REG_MEM_OPERATION(0)   /* wait  */
gfx_v8_0.c:6201          WAIT_REG_MEM_FUNCTION(0)   /* always */
gfx_v8_0.c:6202          WAIT_REG_MEM_ENGINE(0)     /* me */
gfx_v8_0.c:6203      mmVM_INVALIDATE_REQUEST
gfx_v8_0.c:6204      0                /* addr  */
gfx_v8_0.c:6205      0                /* ref   */
gfx_v8_0.c:6206      0                /* mask  */
gfx_v8_0.c:6207      0x20             /* poll interval */
gfx_v8_0.c:6210      if (usepfp)
gfx_v8_0.c:6212          PACKET3(PACKET3_PFP_SYNC_ME, 0)
gfx_v8_0.c:6213          0x0
```

Y lo que hace la línea 6196, en `gmc_v8_0.c:668-683`:

```
gmc_v8_0.c:673      if (vmid < 8)
gmc_v8_0.c:674          reg = mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + vmid;
gmc_v8_0.c:675      else
gmc_v8_0.c:676          reg = mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + vmid - 8;
gmc_v8_0.c:677      amdgpu_ring_emit_wreg(ring, reg, pd_addr >> 12);
gmc_v8_0.c:680      amdgpu_ring_emit_wreg(ring, mmVM_INVALIDATE_REQUEST, 1 << vmid);
```

Dos cosas quedan **PROVEN** con esto:

1. **El invalidate es `1 << vmid`**, un bit por contexto. El comentario del
   propio código lo dice: *"bits 0-15 are the VM contexts0-15"*.
2. **`PAGE_TABLE_BASE_ADDR` se escribe con `pd_addr >> 12`**, o sea que la
   dirección de la page table va en unidades de 4 KiB. Coincide con `gmc_v8_0.c:889`
   (`table_addr >> 12` para la GART), lo que confirma que el mismo campo se usa
   para GART y para VM de usuario con la misma escala.

**El orden de escritura es PTBA primero, invalidate después.** Y el registro que
se escribe primero es distinto según el VMID: `CONTEXT0` para 0-7, `CONTEXT8`
para 8-15. Eso es la misma estructura de dos bloques que 064 y 065aclararon, y
aquí aparece por qué existe.

## La aritmética declarada cuadra, y explica el +2

`gfx_v8_0.c` declara el tamaño de esta operación **tres veces**, una por cada
tipo de ring. Con `VI_FLUSH_GPU_TLB_NUM_WREG = 3` (`vi.h:27`):

```
gfx_v8_0.c:6881   3*5 + 9  = 24     ring GFX
gfx_v8_0.c:6929   3*5 + 7  = 22     ring COMPUTE
gfx_v8_0.c:6964   17       = 17     ring KIQ
```

El `+9` contra `+7` son los **2 dwords del `PFP_SYNC_ME`**, y se explica por
`usepfp`:

| ring | `usepfp` | `PFP_SYNC_ME` | declarado |
|---|---|---|---|
| GFX | `type == AMDGPU_RING_TYPE_GFX` → TRUE | sí | 3·5+9 = 24 |
| COMPUTE | FALSE | no | 3·5+7 = 22 |
| KIQ | FALSE | no | 17 |

Los `3*5` son los tres anillos de cinco dwords: el paquete `PAGE_TABLE_BASE_ADDR`
y el de `INVALIDATE_REQUEST`, más el tercero que cuenta `VI_FLUSH_GPU_TLB_NUM_WREG`.

**El 17 del KIQ no encaja con `3*5+7 = 22`.** La diferencia es exactamente 5,
un `emit_wreg` completo. Lo dejo anotado como `NOT_DETERMINED` con la diferencia
medida en vez de redondeado a una explicación: no sé si el KIQ omite el WREG del
`PAGE_TABLE_BASE_ADDR`, o si el 17 está simplemente mal, y son dos cosas distintas con
consecuencias distintas para un driver propio.

Un driver que reserve 22 dwords para el KIQ y la función emita 17 se desborda en
anillo. Un número de reserva *mayor* es seguro; uno menor no. Eso se decide
midiendo, y aquí no se ha medido.

## Lo que esto NO cierra

| Afirmación | Estado |
|---|---|
| Orden de emisión software de §D | `PROVEN` (texto, con valores) |
| El invalidate es `1 << vmid` | `PROVEN` |
| `PAGE_TABLE_BASE_ADDR` va en unidades de 4 KiB | `PROVEN` |
| El invalidate se emite por ring, no por MMIO | `PROVEN` |
| `CONTEXT0` para vmid 0-7, `CONTEXT8` para 8-15 | `PROVEN` |
| `PFP_SYNC_ME` sólo en ring GFX | `PROVEN` |
| Los 3 tamaños declarados: 24 / 22 / 17 | `PROVEN` (valores declarados) |
| Por qué KIQ declara 17 y no 22 | `NOT_DETERMINED` |
| **Orden de ejecución en hardware** | `NOT_DETERMINED` |
| Si `FUNCTION=0` (always) espera o no | `NOT_DETERMINED` |

**F1 sigue abierta y por esto.** La secuencia de arriba es lo que el driver
*escribe*. Si el hardware la ejecuta en ese orden es otra pregunta, y la única
vía para responderla sigue siendo el discriminante de `017 §5`: ejecutar
`WAIT_REG_MEM` con `poll` distinto contra `INVALIDATE_REQUEST` y observar. Eso
requiere root y carga del driver propio. `BLOCKED_BY_AUTHORIZATION`, sin cambios.

Lo que esta nota hace es **acotar el experimento**: ahora se sabe exactamente
qué registro, qué función y qué valores usar, y que `ENGINE=0` (me) y
`ENGINE=usepfp` son las dos variantes que el propio driver emite. El
discriminante de `017` ya apuntaba a `INVALIDATE_REQUEST`; ahora además sabemos
que el software lo escribe con `mask=0` y `ref=0`, que es lo que hace que la
comparación sea significativa.

## Procedencia

- `CORPUS` — `gfx_v8_0.c`, `gmc_v8_0.c`, `vi.h`.
- Herramientas: `xref.py` (encontró `gfx_v8_0.c:6203` tras corregir el
  clasificador), `causal.py` (grafo), y aritmética verificada aparte.
- Sin `RUNTIME`, sin escritura en la GPU.
- Nota: `causal.py` no produjo aristas de llamada para estas dos funciones porque
  no se llaman: se instancian como punteros en `struct amdgpu_ring_funcs`. La
  herramienta clasifica llamadas, no asignaciones de punteros de función; queda
  como límite declarado, no como ausencia de relación.