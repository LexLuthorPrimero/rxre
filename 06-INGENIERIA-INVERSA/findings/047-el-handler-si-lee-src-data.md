# 047 · El handler de faults sí lee `src_data[0]` — y lo imprime

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`HERRAMIENTAS=08-ARQUITECTURA/tools/stale_gap.py`, `_selftest_stale_gap.py`
`CORRIGE=051 §6 "el handler la ignora" (CORRECTED), y 052:137-138`
`CONTINUES=046`

## Cuestión principal

¿El handler de faults de GFX8 lee `entry->src_data[0]`?

## Criterio de terminación

Leer el handler completo y contar los accesos al campo. **Cumplido: dos
accesos, y los dos son para imprimirlo.**

## Respuesta

**Sí. Dos veces.** Y en las dos se imprime.

```c
/* gmc_v8_0.c:1433-1437, camino SRIOV VF */
dev_err(adev->dev, "GPU fault detected: %d 0x%08x\n",
        entry->src_id, entry->src_data[0]);
dev_err(adev->dev, " Can't decode VM fault info here on SRIOV VF\n");

/* gmc_v8_0.c:1464-1466, camino normal, bajo printk_ratelimit */
dev_err(adev->dev, "GPU fault detected: %d 0x%08x\n",
        entry->src_id, entry->src_data[0]);
```

## Lo que `051` afirmó, y por qué está mal

`051` §6 escribió:

> El driver **descarta** la información del IV en `gmc_v8_0_process_vm_fault`,
> que sólo lee los tres registros `PROTECTION_FAULT_{ADDR,STATUS,MCCLIENT}`
> (`gmc_v8_0.c:1446-1448`). Y sin embargo `src->funcs->process` recibe
> `*amdgpu_iv_entry` completo … con `vmid` y `pasid` disponibles.

Y en esa misma línea: *"Lo que sí es `PROVEN` es que el IV transporta identidad
y que el handler la ignora."*

Es `REFUTED`. El handler no la ignora: **la lee y la escribe en el log de
errores**. Lo que `051` vio fue que no la *decodifica*, que es una afirmación
distinta y correcta.

### Y el nombre de la función estaba mal en `051`

`051` cita `gmc_v8_0_process_vm_fault`. Ese símbolo **no existe**:

```
$ grep -n "gmc_v8_0_process_vm_fault" gmc_v8_0.c
(sin resultado)
```

El nombre real es **`gmc_v8_0_process_interrupt`**, y su firma delata la causa
del error:

```c
static int gmc_v8_0_process_interrupt(struct amdgpu_device *adev,
                                      struct amdgpu_irq_src *source,
                                      struct amdgpu_iv_entry *entry)
```

`process`, no `process_vm_fault`. El handler es **compartido** por los dos IV, y
por eso el nombre real es genérico. `051` inventó un nombre más específico al
recordar la función, y luego atribuyó a ese nombre inventado una lista de
lecturas.

Esa es la clase de fallo: **un nombre plausible inventado, rellenado con lo que debería hacer**,
y luego se citan las líneas de la función real como si respaldaran la versión
inventada.

## El hallazgo real: los dos IV de fault comparten handler

Por eso el contenido de `src_data[0]` no se puede decodificar desde el driver.

`0x92` (`GFX_PAGE_INV_FAULT`) y `0x93` (`GFX_MEM_PROT_FAULT`) se registran
**ambos** contra la misma función:

```c
/* gmc_v8_0.c:1115 */
amdgpu_irq_add_id(adev, AMDGPU_IRQ_CLIENTID_LEGACY,
                  VISLANDS30_IV_SRCID_GFX_PAGE_INV_FAULT, &adev->gmc.vm_fault);

/* gmc_v8_0.c:1119 */
amdgpu_irq_add_id(adev, AMDGPU_IRQ_CLIENTID_LEGACY,
                  VISLANDS30_IV_SRCID_GFX_MEM_PROT_FAULT, &adev->gmc.vm_fault);
```

Y esa función lee **los mismos tres registros** para ambos:
`mmVM_CONTEXT1_PROTECTION_FAULT_{ADDR,STATUS,MCCLIENT}` (`gmc_v8_0.c:1446-1448`).

Es decir: **la distinción entre "fallo de invalidación de página" y "fallo de
protección de memoria" no está en el handler**, porque el handler es uno. Está
en `src_id`, que es lo único que se imprime sin interpretar
(`entry->src_id`).

Y `061` cerró otra cosa: `src_data[0]` ∈ {0, 1} en el **camino de display**
(`dce_v8_0.c`), donde el switch tiene dos casos. Eso **no** dice nada del
camino de fault, que es un consumidor distinto del mismo campo.

Así que las dos fronteras de `052` no se cierran con lo que hay:

| frontera | estado | por qué |
|---|---|---|
| `052:137` contenido de `src_data[0]` en cada caso | `NOT_DETERMINED` | requiere RUNTIME: el driver lo imprime pero no lo decodifica |
| `052:138` diferencia de comportamiento entre `0x92` y `0x93` | `NOT_DETERMINED` | **no la hay en el handler**: comparten función y registros. La diferencia está en `src_id`, que sí se distingue. |

## El dato disponible sin RUNTIME

Hay algo que `051` no vio y que **reduce** el alcance de la primera frontera: el
valor se imprime en decimal y en hexadecimal con el mismo formato, y hay un
camino donde **no depende del ratelimit**:

```c
/* camino SRIOV VF: sin printk_ratelimit, sin condición */
dev_err(adev->dev, "GPU fault detected: %d 0x%08x\n", ...);
```

En esta placa no hay SRIOV VF (un solo ASIC, sin virtualization), así que ese
camino no se ejecuta. Pero el camino **normal** sí, y su condición es
`printk_ratelimit()`: el primer fault siempre imprime.

**Consecuencia para el driver propio:** un `dmesg` tras provocar un fault da el
valor de `src_data[0]` sin ningún instrumento nuevo. Eso **no** es RUNTIME
necesario en el sentido de "hay que escribir en el hardware": es RUNTIME de
observación, y solo depende de que ocurra un fault.

## Clasificación

| afirmación | estado |
|---|---|
| El handler lee `entry->src_data[0]` | `PROVEN` — `gmc_v8_0.c:1435`, `:1465` |
| Lo lee dos veces y ambas son para imprimirlo | `PROVEN` — `grep` del campo |
| No lo decodifica | `PROVEN_ABSENT` — no hay más acceso en el fichero |
| `051`: "el handler la ignora" | `REFUTED` — la lee y la imprime |
| `gmc_v8_0_process_vm_fault` existe | `PROVEN_ABSENT` — no está en el fichero |
| El nombre real es `gmc_v8_0_process_interrupt` | `PROVEN` — `gmc_v8_0.c:1427` |
| `0x92` y `0x93` comparten handler | `PROVEN` — `gmc_v8_0.c:1115`, `:1119` |
| Leen los mismos tres registros para ambos | `PROVEN` — un solo cuerpo |
| La diferencia entre ambos IV está en `src_id` | `DERIVATION` — es lo único no compartido |
| `052:138` es una frontera real de contenido | `REFUTED` — no hay bifurcación en el handler |
| `061` (src_data ∈ {0,1}) aplica al camino de fault | `REFUTED` — `061` habla de `dce_v8_0.c` |
| Contenido de `src_data[0]` en un fault | `NOT_DETERMINED` — RUNTIME de observación |
| Significado de los valores que imprima | `NOT_DETERMINED` — no hay decodificador |

## El confounders que quedaba abierto, cerrado

`047` §Confounders decía: *"el dispatcher genérico podría leerlo antes de
repartir; no está comprobado"*. Está comprobado:

```c
/* amdgpu_ih.c:280-292 */
entry->src_data[0] = dw[4];
entry->src_data[1] = dw[5];
entry->src_data[2] = dw[6];
entry->src_data[3] = dw[7];
```

**Escribe**, no lee. El dispatcher no interpreta `src_data`, lo copia. Y en el
caso de GFX8 es una copia **sin máscara**, a diferencia de otras generaciones:

```
cik_ih.c:271   entry->src_data[0] = dw[1] & 0xfffffff;
cz_ih.c:260    entry->src_data[0] = dw[1] & 0xfffffff;
amdgpu_ih.c:289 entry->src_data[0] = dw[4];        <- sin máscara
```

Los tres leen el mismo campo, pero **cik/cz leen `dw[1]` enmascarado y GFX8 lee
`dw[4]` entero**. Es una diferencia de disposición del IV entre generaciones,
no un descuido.

### El dato duro para el driver propio

El valor que el handler imprime es **el dword 4 del IV, sin transformar**:

```
dw[0]  client_id[7:0] | src_id[15:8] | ring_id[23:16] | vmid[27:24] | vmid_src[31]
dw[1]  timestamp[31:0]
dw[2]  timestamp[47:32] | timestamp_src[63:48]
dw[3]  pasid[15:0] | node_id[23:16]
dw[4]  src_data[0]     <- este es el valor de la frontera
dw[5]  src_data[1]
dw[6]  src_data[2]
dw[7]  src_data[3]
```

Cuatro dwords de `src_data` caben en el IV de 32 B, y GFX8 los usa todos. Para
un driver propio esto significa que **`src_data[0]` no hay que decodificarlo: se
puede copiar tal cual y decidir qué significa**, en lugar de invertir el
formato como hacen las otras generaciones.

Y `src_id` está en `dw[0][15:8]`, junto a `client_id`. Ese dword sí distingue
`0x92` de `0x93`, y por eso la respuesta a `052:138` está en `src_id` y no en
`src_data[0]`.

## Confounders (restantes)

- **El conteo es de `gmc_v8_0.c`.** Hay otros consumidores de `src_data[0]` en
  el árbol (`dce_v6_0.c`, `dce_v8_0.c`, `dce_v10_0.c`), y cada uno lo decodifica
  para su propio camino. El hallazgo es del camino de **fault**.
- **El camino SRIOV VF no se ejecuta en esta placa.** Los dos accesos existen
  en el fichero, pero solo uno es alcanzable sin virtualización.
- **`052:138` pasa a `REFUTED` en el handler, no en el hardware.** El hardware
  podría diferenciar `0x92` de `0x93` en `src_data[0]`; lo que no hay es que el
  driver lo mire. Afirmar que no hay diferencia sería un salto que no doy.
- **`061` no se contradice con esto.** Habla de otro consumidor del mismo
  campo. Lo que no puede hacerse es extender su conclusión de display a fault.

## Desfalsificación

- **(a)** El handler lee `src_data[0]` → refutable con `grep -n src_data gmc_v8_0.c`;
  sale 1435 y 1465.
- **(b)** `gmc_v8_0_process_vm_fault` no existe → refutable con `grep`; vacío.
- **(c)** Los dos IV comparten handler → refutable con las dos líneas de
  `amdgpu_irq_add_id`, idéntico puntero `&adev->gmc.vm_fault`.
- **(d)** El dispatcher genérico no lee el campo → **no comprobado**, y es el
  confounders que queda abierto.

## UNLOCKS

- **`051` queda corregido** en su afirmación central, y el nombre de función que
  usó no existe. Es el caso más claro del proyecto de **inventar un nombre
  plausible y luego citar el real como si lo respaldara**.
- **`052:138` se retira** como frontera: no es una pregunta que el handler
  pueda responder.
- **El valor de `src_data[0]` en un fault es observable con `dmesg`**, sin
  escribir nada en el hardware. Eso baja el coste de esa frontera.
- **La diferencia entre `0x92` y `0x93` está en `src_id`**, que sí se
  distingue sin instrumentation. Es la vía barata para esa pregunta.

## Evidencia

```
amdgpu_ih.c:280   entry->client_id = dw[0] & 0xff
amdgpu_ih.c:281   entry->src_id   = (dw[0] >> 8) & 0xff
amdgpu_ih.c:282   entry->ring_id  = (dw[0] >> 16) & 0xff
amdgpu_ih.c:283   entry->vmid     = (dw[0] >> 24) & 0xf
amdgpu_ih.c:284   entry->vmid_src = (dw[0] >> 31)
amdgpu_ih.c:285   entry->timestamp = dw[1] | ((u64)(dw[2] & 0xffff) << 32)
amdgpu_ih.c:288   entry->pasid    = dw[3] & 0xffff
amdgpu_ih.c:289   entry->src_data[0] = dw[4]        <- sin mascara
amdgpu_ih.c:290   entry->src_data[1] = dw[5]

cik_ih.c:271      src_data[0] = dw[1] & 0xfffffff   <- otra generacion, con mascara

gmc_v8_0.c:1115   amdgpu_irq_add_id(..., GFX_PAGE_INV_FAULT, &gmc.vm_fault)
gmc_v8_0.c:1119   amdgpu_irq_add_id(..., GFX_MEM_PROT_FAULT, &gmc.vm_fault)
gmc_v8_0.c:1427   static int gmc_v8_0_process_interrupt(...)
gmc_v8_0.c:1435   dev_err(... entry->src_data[0])   <- camino SRIOV VF
gmc_v8_0.c:1446   addr    = RREG32(mmVM_CONTEXT1_PROTECTION_FAULT_ADDR)
gmc_v8_0.c:1447   status  = RREG32(mmVM_CONTEXT1_PROTECTION_FAULT_STATUS)
gmc_v8_0.c:1448   mc_client = RREG32(mmVM_CONTEXT1_PROTECTION_FAULT_MCCLIENT)
gmc_v8_0.c:1465   dev_err(... entry->src_data[0])   <- camino normal
gmc_v8_0.c:1744   gmc_v8_0_irq_funcs = { .process = gmc_v8_0_process_interrupt }

grep -n "gmc_v8_0_process_vm_fault" gmc_v8_0.c   ->  (vacio)
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.