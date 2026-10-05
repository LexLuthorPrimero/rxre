# 1403 — GFX8 nunca instala `adev->gfxhub.funcs`: todo `gfxhub_v1_0.c` está muerto en esta ASIC, y eso corrige la premisa de `1179`

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · CORPUS=rx550-upstream-7.2.8
TARGET=CHIP_POLARIS12 (1002:699F)

AFECTADO=gmc_v8_0.c:1039-1056      gmc_v8_0_early_init   NO asigna gfxhub.funcs
         amdgpu_drv.c:2377-2535    amdgpu_pci_probe     NO asigna gfxhub.funcs
         gmc_v9_0.c:1487-1494      gmc_v9_0_set_gfxhub_funcs  UNICO sitio que
                                       instala gfxhub_v1_0_funcs
         gfxhub_v1_0.c:413-442     gfxhub_v1_0_init     NO SE EJECUTA en GFX8

CORRIGE=1179-gfx8-calcula-los-offsets-del-semaforo-y-no-los-usa.md
        1177 y 1178 no se ven afectados (su simbolo no se invoca desde ningun
        fichero, y los ficheros ausentes son de probe, no de KFD)
EXPLICA=1145, de forma retrospectiva: el parametro `vmhub` que
        gmc_v8_0_flush_gpu_tlb ignora no esta ignorado por capricho, esta vacio
ESTADO=PROVEN-SOBRE-EL-CORPUS · alcance cerrado por §16
```

## 0 · LO QUE AFIRMABA `1179`, Y POR QUÉ ERA FALSO

`1179` afirmó, con tres medidas:

> *El hub de GFX8 **calcula** los offsets del semáforo… y nunca los usa.*

Las tres medidas eran buenas. **La primera mitad de la frase es falsa**, y el
error no está en cómo se midió: está en **no comprobar de dónde viene el código
que hace la medición**.

`gfxhub_v1_0_init()` es, para Polaris12, **código muerto**.

## 1 · LA MEDICIÓN, EN CINCO PASOS QUE NO DEPENDEN UNO DEL OTRO

**(a) Dónde se asigna `adev->gfxhub.funcs`, en todo el árbol:**

```
  gmc_v9_0.c:1490    &gfxhub_v1_2_funcs
  gmc_v9_0.c:1492    &gfxhub_v1_0_funcs
  gmc_v10_0.c:604    &gfxhub_v2_1_funcs
  gmc_v10_0.c:607    &gfxhub_v2_0_funcs
  gmc_v11_0.c:601    &gfxhub_v3_0_3_funcs
  gmc_v11_0.c:611    &gfxhub_v11_5_0_funcs
  gmc_v11_0.c:614    &gfxhub_v3_0_funcs
  gmc_v12_0.c:625    &gfxhub_v12_0_funcs
  gmc_v12_0.c:628    &gfxhub_v12_1_funcs
```

**Ocho. Ninguno en `gmc_v8_0.c`.**

**(b) Quién invoca `gmc_v9_0_set_gfxhub_funcs`, el único que instala
`gfxhub_v1_0_funcs`:**

```
  gmc_v9_0.c:1487   la definición
  gmc_v9_0.c:1599   la ÚNICA llamada
```

Función estática, llamada una vez, desde el init de **GFX9**.

**(c) `gmc_v8_0_early_init`, leído entero (`gmc_v8_0.c:1039-1056`):**

```c
static int gmc_v8_0_early_init(struct amdgpu_ip_block *ip_block)
{
        struct amdgpu_device *adev = ip_block->adev;

        gmc_v8_0_set_gmc_funcs(adev);
        gmc_v8_0_set_irq_funcs(adev);

        adev->gmc.shared_aperture_start = 0x2000000000000000ULL;
        adev->gmc.shared_aperture_end =
                adev->gmc.shared_aperture_start + (4ULL << 30) - 1;
        adev->gmc.private_aperture_start = adev->gmc.shared_aperture_end + 1;
        adev->gmc.private_aperture_end =
                adev->gmc.private_aperture_start + (4ULL << 30) - 1;
        adev->gmc.noretry_flags = AMDGPU_VM_NORETRY_FLAGS_TF;

        return 0;
}
```

Dos punteros de función y cuatro constantes. **Ni `gfxhub.funcs` ni
`vmhub_funcs`.**

**(d) `amdgpu_pci_probe`, leído entero (`amdgpu_drv.c:2377-2535`):** 159 líneas.
Asigna `adev` con `devm_drm_dev_alloc()`. **No toca `gfxhub`.**

**(e) Quién llama a `adev->gfxhub.funcs->init(adev)`:**

```
  aldebaran.c:276   gmc_v10_0.c:753   gmc_v11_0.c:751
  gmc_v12_0.c:821   gmc_v9_0.c:1855   sienna_cichlid.c:163
```

Seis. **Ninguno en `gmc_v8_0.c`.**

> **Y la cadena de bloquesip para Polaris12 cierra el círculo:** `vi.c:2110` añade
> `gmc_v8_1_ip_block`, cuyo `.funcs = &gmc_v8_0_ip_funcs`, cuyo
> `.early_init = gmc_v8_0_early_init` — el del punto (c).

**⇒ Para Polaris12, `adev->gfxhub.funcs` no se asigna nunca, y
`gfxhub_v1_0_init()` no se ejecuta nunca.**

## 2 · LO QUE ESO DEJA EN CEROS

`gfxhub_v1_0_init()` es lo único que rellena la struct `amdgpu_vmhub` para GFX8.
Sus campos, y su estado real en esta ASIC:

| campo | lo que dice el nombre | valor real en Polaris12 |
|---|---|---|
| `ctx_distance` | distancia entre contextos | **sin calcular** |
| `ctx_addr_distance` | distancia entre direcciones | **sin calcular** |
| `vm_inv_eng0_sem` | semáforo de invalidación | **sin calcular** |
| `vm_inv_eng0_req/ack` | request/ack de invalidación | **sin calcular** |
| `ctx0_ptb_addr_lo32/hi32` | base de la tabla del GART | **sin calcular** |
| `vm_context0_cntl`, `vm_cntx_cntl*`, `vm_contexts_disable` | contexto 0 | **sin calcular** |

Y como `adev` se crea con `devm_drm_dev_alloc()`, que es API de DRM documentada
como allocadora a cero, todos esos campos valen **0** antes de que nadie los
escriba.

> **Consecuencia directa y dura:** cualquier código de GFX8 que multiplicara
> `vmid * hub->ctx_distance` daría **`0` para todos los VMID**, no la dirección
> correcta. No es que el valor sea pequeño: es **cero**. Y no hay ningún
> `BUG_ON` que lo detecte.
>
> Ese es exactamente el modo de fallo silencioso que un driver propio tiene que
> evitar a propósito: **si replica `gfxhub_v1_0.c` tal cual, escribe en el
> registro de contexto 0 quince veces y cree que ha configurado quince VMIDs.**

## 3 · CORRIGE `1179`, Y LE QUITA LA MEDIOGA

`1179` construyó su hallazgo sobre un campo «lleno y no leído». La tabla correcta es:

| | lo que decía `1179` | lo que es |
|---|---|---|
| `vm_inv_eng0_sem` para GFX8 | calculado, con offset válido | **nunca calculado** |
| lectura por GFX8 | ninguna | ninguna |
| fuerza de la prueba | el campo tenía valor y no se leía | **el campo no existe como dato** |

**La conclusión de `1179` sobre el semáforo sobrevive, y sale reforzado:** no es que
GFX8 lo ignore por tener un hub, es que **la ruta entera que lo calcularía no se
ejecuta**. Lo que `1145` ya había medido por otra vía —que `gmc_v8_0_flush_gpu_tlb`
ignora su parámetro `vmhub`— queda **explicado**: no lo ignora por estilo, lo
ignora porque para GFX8 ese parámetro apunta a una struct que nadie ha rellenado.

**Y el patrón de las tres últimas se invierte aquí:**

```
  1177   dos escritores, uno en tabla sin invocación   -> quitar un productor
  1178   lector sin escritor                          -> quitar un productor
  1179   campo escrito sin lector                     -> quitar un productor
  1403   fichero entero sin ejecutar                  -> quitar UN FICHERO
```

**El nivel de la error sube un peldaño cada vez.** Y el patrón que lo produce es
siempre el mismo: **contar menciones donde había que contar alcance.**

## 4 · §16 · EL ALCANCE SE COMPRUEBA ANTES DE DECLARAR LA AUSENCIA

Antes de escribir «nunca se asigna» hago el gate de alcance, porque es
justo el tipo de afirmación que un corpus parcial convierte en falsehood:

```
  amdgpu_main.c   ausente en los 4 arboles del proyecto
  amdgpu_bus.c    ausente en los 4 arboles del proyecto
```

Eso podría parecer un hueco fatal: sin el probe no se ve el alcance. MEDIDO:

- **`amdgpu_pci_probe` está en `amdgpu_drv.c:2377`.** Los dos ficheros no se
  perdieron: en 7.2.x su contenido vive en `amdgpu_drv.c`. La ruta de probe
  **está cubierta**.
- **`struct amdgpu_device` es privada del directorio `amdgpu`.** No hay ningún
  otro `.c` en el kernel que pueda asignar `adev->gfxhub.funcs`. El grep de ocho
  sitios es por tanto **exhaustivo sobre el driver**, no sobre una muestra.

**`PROVEN` sobre el corpus, con el alcance justificado.** Es la diferencia con
`1178`, que tuvo que quedarse en `NOT_FOUND` porque el alcance no daba.

*Limitación:* la **implementación** de `devm_drm_dev_alloc()` no está en este
proyecto, así que el «pone a cero» es **API documentada, no verificado aquí**.
No cambia la conclusión, que es sobre *asignación* y no sobre *valor inicial*.

## 5 · LO QUE QUEDA VIVO, Y ES LA MEDIDA QUE IMPORTA PARA UN DRIVER PROPIO

Si `gfxhub_v1_0.c` está muerto, **el único escritor alcanzable de la base de tabla
de páginas de un VMID en GFX8 es el legacy, por PM4, y es de 32 bits**:

```c
gmc_v8_0.c:662-677
static uint64_t gmc_v8_0_emit_flush_gpu_tlb(struct amdgpu_ring *ring,
                                            unsigned int vmid, uint64_t pd_addr)
{
        uint32_t reg;

        if (vmid < 8)
                reg = mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + vmid;
        else
                reg = mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + vmid - 8;
        amdgpu_ring_emit_wreg(ring, reg, pd_addr >> 12);
```

### Y el array de registros está **partido en dos mitades**

MEDIDO sobre `include/asic_reg/gmc/gmc_8_1_d.h` (GC 8.1 = Polaris12):

```
  0x050e  mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR     <-- la mitad ALTA
  0x050f  mmVM_CONTEXT9_PAGE_TABLE_BASE_ADDR
   ...
  0x0515  mmVM_CONTEXT15_PAGE_TABLE_BASE_ADDR

  0x054f  mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR     <-- la mitad BAJA
  0x0550  mmVM_CONTEXT1_PAGE_TABLE_BASE_ADDR
   ...
  0x0556  mmVM_CONTEXT7_PAGE_TABLE_BASE_ADDR
```

**`0x050e < 0x054f`.** Los ocho contextos de KFD están en direcciones **inferiores**
a los ocho de amdgpu, y el driver lo sabe: por eso el `if (vmid < 8) / else`.

Y con `gmc_v8_0.c:1156-1162`:

```
  /* number of VMs
   * VMID 0 is reserved for System
   * amdgpu graphics/compute will use VMIDs 1-7
   * amdkfd will use VMIDs 8-15 */
  adev->vm_manager.first_kfd_vmid = 8;
```

> **La línea que un driver propio no puede deducir es esta:** un mapeo lineal
> `BASE + vmid` acierta en los VMID 0–7 y **falla exactamente en los 8–15**, que
> son los de KFD/ROCm. El síntoma sería que el GART y amdgpu funcionan y ROCm no
> arranca, o arranca y hace direccions equivocadas. **Ningún `BUG_ON`, ningún
> assert: solo una aritmética que el nombre del registro sugiere y el hardware no
> cumple.**

Y hay un segundo detalle, menor pero del mismo tipo: `gmc_v8_0_emit_flush_gpu_tlb`
escribe **`pd_addr >> 12`**, un PFN de 32 bits. El camino de 64 bits
(`LO32`/`HI32`, `ctx_addr_distance = 2`) que documenta `gfxhub_v1_0.c` **no
existe para esta ASIC en este driver**.

## 6 · LO QUE NO SE AFIRMA

- **No se dice que `gfxhub_v1_0.c` esté mal escrito.** Está bien escrito para las
  ASICs que lo usan. Lo que se afirma es que **GFX8 no lo selecciona**.
- **No se dice que la GPU funcione por accidente.** El camino legacy
  (`gmc_v8_0_gart_enable` programa VMID 0 y VMID 1; `emit_flush_gpu_tlb`
  programa la base de cualquier VMID por PM4) es coherente y suficiente. Lo que se
  afirma es que **es el único que corre**, no que el otro sea necesario.
- **No se afirma nada sobre `mmVM_CONTEXT2_CNTL` a `15_CNTL`.** En el bloque GMC
  de GC 8.1 **no están definidos**; solo `CONTEXT0_CNTL` y `CONTEXT1_CNTL`
  existen ahí. Los dieciséis existen en el bloque GC (`gc_9_0_offset.h`,
  `0x0880–0x088f`), y ese bloque es el que solo usa `gfxhub_v1_0.c`.
  **Qué configura los contextos 2–15 en esta ASIC queda `NOT_DETERMINED`** y es
  una pregunta para el nodo de runtime, no una lectura de código.
- **No se modifica el corpus.** Todo es lectura.

## 7 · LA LECIÓN, Y ES LA QUINTA DE LA MISMA FAMILIA

| hallazgo | lo que tomé por vivo | lo que era |
|---|---|---|
| `023` | `sdma_v3_0.c` productor de PTE | el fichero equivocado |
| `047` | el cero de ficheros ASIC | tenía el equivocado en la lista |
| `1166` | dos escritores vivos | uno en tabla sin invocación |
| `1178` | un escritor muerto | dos, y por tanto un patrón |
| **`1403`** | **`gfxhub_v1_0.c` como el código de GFX8** | **código que GFX8 no selecciona** |

Cinco. Y la quinta tiene una diferencia que la hace la más útil de todas:

> **Las cuatro primeras se equivocaron al elegir *dentro* de un fichero vivo.
> Esta se equivocó al elegir el fichero entero.** Y no por un `grep` mal escrito:
> por leer `gfxhub_v1_0.c` entero, tres veces, con la función completa delante —
> exactamente el procedimiento que `1129`, `1144` y `1153` después me hicieron
> seguir por citas aisladas. **Leer la función entera garantiza que la citas son
> ciertas; no garantiza que el fichero sea de esta ASIC.**
>
> La pregunta que faltaba no era «¿es esto alcanzable?» sino **«¿quién elige este
> fichero, y me eligió a mí?»**. Y esa tiene respuesta en un solo sitio:
> `adev->gfxhub.funcs = …`, ocho líneas en el árbol, ninguna de GFX8.

**Y el instrumento que falta es de nuevo diminuto, y es el mismo de `1177` §7 y
`1178` §6:** falta aplicar la prueba de alcanzabilidad —la de `tools/unreach.py`—
al puntero **`adev->gfxhub.funcs`**, es decir: *para cada ASIC que el driver
soporta, ¿qué tabla instala y quién la invoca?* Eso es un grafo pequeño y
medible, y habría detectado esto y `1166` y `1177` con el mismo mecanismo.

**No lo implemento:** `tools/unreach.py` es de otra sesión y el árbol tiene sus
ficheros modificados sin commitear. Queda anotado como alcance exacto.

```
ESTADO
  adev->gfxhub.funcs para CHIP_POLARIS12
     sitios que lo asignan en el arbol            8
     de ellos en gmc_v8_0.c                      0        PROVEN
     sitios que lo instalan en amdgpu_pci_probe    0        PROVEN
     -> NO ASIGNADO                             PROVEN
  gfxhub_v1_0_init() en Polaris12                NO SE EJECUTA      PROVEN
  amdgpu_vmhub para GFX8
     ctx_distance, ctx_addr_distance,
     vm_inv_eng0_*, ctx0_ptb_addr_*              SIN CALCULAR       PROVEN

  CORRIGE la premisa de 1179 (conclusion intacta, mas fuerte)
  EXPLICA por que gmc_v8_0_flush_gpu_tlb ignora `vmhub`

  unico escritor alcanzable de la base de tabla
     gmc_v8_0_emit_flush_gpu_tlb    32 bit, PFN, por PM4, array partido
     array: CONTEXT0-7 0x54f..0x556  /  CONTEXT8-15 0x50e..0x515
     mapeo lineal base+vmid         falla en VMID 8-15  = los de KFD
  quien configura los contextos 2-15               NOT_DETERMINED -> runtime

  alcance verificado con §16: amdgpu_pci_probe esta en amdgpu_drv.c:2377
  GPU     INTACTA
  sudo    NO usado
  corpus  solo lectura
```