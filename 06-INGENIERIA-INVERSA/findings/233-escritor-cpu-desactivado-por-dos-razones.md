# 233  Por qué no hay escritor CPU de page tables: **dos razones independientes, no una**

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CORPUS=RESEARCH/working/linux-7.1.3` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`CORRIGE=la razon de la linea consolidada "CPU page-table writer inalcanzable"`
`CIERRA=la pregunta que 156 dejo abierta sobre el flush HDP`

## Cuestión principal

El estado consolidado dice:

> *`vm_update_mode = -1` observado; política efectiva `vm_update_mode = 0`.*
> *CPU page-table writer inalcanzable bajo política efectiva.*

Eso dice **qué** pasa pero no **por qué**. Y hay una razón que faltaba.

## Criterio de terminación

Determinar la condición exacta que desactiva el escritor CPU, y comprobar si es
una o varias. **Cumplido: son dos, e independientes entre sí.**

## La política por defecto, textual

`amdgpu_drv.c:458-460`, la documentación del parámetro lo dice entero:

```
 * DOC: vm_update_mode (int)
 * Override VM update mode. VM updated by using CPU (0 = never, 1 = Graphics
 * only, 2 = Compute only, 3 = Both). The default is -1 (Only in large BAR(LB)
 * systems Compute VM tables will be updated by CPU, otherwise 0, never).
```

Y el código, `amdgpu_vm.c:2884-2899`:

```c
if (amdgpu_vm_update_mode == -1) {
        if (amdgpu_gmc_vram_full_visible(&adev->gmc) &&
            !amdgpu_sriov_vf_mmio_access_protection(adev))
                adev->vm_manager.vm_update_mode = AMDGPU_VM_USE_CPU_FOR_COMPUTE;
        else
                adev->vm_manager.vm_update_mode = 0;
} else
        adev->vm_manager.vm_update_mode = amdgpu_vm_update_mode;
```

## Razón 1: la VRAM no es totalmente visible por el BAR

`amdgpu_gmc.h:394-398`:

```c
static inline bool amdgpu_gmc_vram_full_visible(struct amdgpu_gmc *gmc)
{
	WARN_ON(gmc->real_vram_size < gmc->visible_vram_size);
	return (gmc->real_vram_size == gmc->visible_vram_size);
}
```

Una igualdad y un `WARN_ON` de autocomprobación. En esta RX550 el BAR no cubre
toda la VRAM, así que es `FALSE` y cae al `else`: **`vm_update_mode = 0`**.

Eso ya lo tenía el proyecto.

## Razón 2: la política por defecto **nunca** concede la ruta GFX

Este es el dato que faltaba, y no depende del BAR:

```c
adev->vm_manager.vm_update_mode = AMDGPU_VM_USE_CPU_FOR_COMPUTE;
```

La rama que se cumple cuando la VRAM sí es visible asigna **solo**
`AMDGPU_VM_USE_CPU_FOR_COMPUTE` (`amdgpu_vm.h:186`, bit 1). **No hay ninguna
rama que asigne `AMDGPU_VM_USE_CPU_FOR_GFX`** (`amdgpu_vm.h:185`, bit 0).

Es decir: **aunque esta placa tuviera BAR completo, la ruta CPU de GFX seguiría
apagada por defecto.** El `amdgpu_vm_update_mode == -1` solo puede producir
`..._FOR_COMPUTE` o `0`. Para obtener `..._FOR_GFX` hay que pasar el parámetro a
mano.

Y no se puede cambiar en caliente: `module_param_named(vm_update_mode, ...,
int, 0444)` (`amdgpu_drv.c:462`), es decir **solo lectura**, fijable solo al
cargar el módulo.

## Y el driver se avisa a sí mismo

`amdgpu_vm.c:2631-2632`, dentro de `amdgpu_vm_init()`:

```c
WARN_ONCE((vm->use_cpu_for_update &&
           !amdgpu_gmc_vram_full_visible(&adev->gmc)),
          "CPU update of VM recommended only for large BAR system\n");
```

**El driver sabe que forzar la ruta CPU aquí es una mala idea y avisa.** No es un
descuido de configuración: hay un guardián puesto para exactamente este caso.

## El hallazgo de lectura: dos funciones, un mensaje, bits opuestos

Esto sí es un problema real de legibilidad:

| función | bit que consulta | línea |
|---|---|---|
| `amdgpu_vm_init()` | `AMDGPU_VM_USE_CPU_FOR_GFX` (bit 0) | `amdgpu_vm.c:2626` |
| `amdgpu_vm_make_compute()` | `AMDGPU_VM_USE_CPU_FOR_COMPUTE` (bit 1) | `amdgpu_vm.c:2735` |

Y **las dos imprimen exactamente el mismo texto**:

```c
dev_dbg(adev->dev, "VM update mode is %s\n",
        vm->use_cpu_for_update ? "CPU" : "SDMA");
```

Aparece en `amdgpu_vm.c:2629-2630` y en `amdgpu_vm.c:2738-2739`.

**Quien lea el log no puede saber cuál de las dos decisiones está mirando.** Con
`vm_update_mode = 3` las dos dirían "CPU"; con `= 1`, una diría "CPU" y la otra
"SDMA", con texto idéntico. Es la clase de ambigüedad que hace inútil un log de
diagnóstico.

## El vínculo con §G: el mismo bit decide dos cosas

Esto es lo que responde a la pregunta que `232` dejó abierta.

`amdgpu_ids.c:266`, `:334` y `:338`:

```c
bool needs_flush = vm->use_cpu_for_update;
...
job->vm_needs_flush = vm->use_cpu_for_update;
```

Y su uso, `amdgpu_ids.c:280` y `:307`:

```c
if (... !adev->vm_manager.concurrent_flush && needs_flush)
        ring = NULL;
...
job->vm_needs_flush = needs_flush;
```

**`use_cpu_for_update` no solo elige el escritor de las tablas: también decide si
reutilizar un VMID exige un flush HDP antes de confiar en ellas.**

Ese es el motivo de que exista el flush HDP de `232`. No es una precaution
genérica: es la contrapartida exacta de que el escritor sea la CPU. Con SDMA como
escritor, las escrituras van por el camino de la GPU y las ordena el fence; con
escritor CPU hace falta un flush.

**En esta placa `needs_flush` arranca en `false` siempre**, así que la rama de
reutilización de VMID con flush es **inalcanzable**. No es código muerto en el
sentido de que nunca se ejecuta en ninguna configuración; es inalcanzable *en
esta configuración*.

## Clasificación

| afirmación | estado |
|---|---|
| `vm_update_mode = -1` produce `..._COMPUTE` o `0` | `PROVEN` — `amdgpu_vm.c:2888-2894` |
| Ninguna rama asigna `..._FOR_GFX` por defecto | `PROVEN_ABSENT` |
| El BAR no cubre la VRAM aquí | `PROVEN` — observación previa del proyecto |
| `vram_full_visible` es `real == visible` | `PROVEN` — `amdgpu_gmc.h:394` |
| El parámetro es `0444`, solo al cargar | `PROVEN` — `amdgpu_drv.c:462` |
| El driver advierte si se fuerza sin BAR completo | `PROVEN` — `amdgpu_vm.c:2631` |
| Las dos funciones imprimen el mismo texto | `PROVEN` — `:2629` y `:2738` |
| `use_cpu_for_update` gobierna también `needs_flush` | `PROVEN` — `amdgpu_ids.c:266,334` |
| La rama de VMID con flush es inalcanzable aquí | `PROVEN_DERIVED` |
| Que el escritor SDMA baste sin flush | `NOT_DETERMINED` — depende del fence |

## Confounders

- **La rama GFX existe y es alcanzable**, con `amdgpu.vm_update_mode=1` al
  cargar. No digo que el driver no pueda, digo que **por defecto no lo hace en
  ninguna placa**, ni con BAR completo.
- **`concurrent_flush` también mueve `needs_flush`** (`amdgpu_ids.c:277`, `:350`,
  `:353` lo ponen a `true` por otras condiciones). El `false` inicial es lo que
  hereda de `use_cpu_for_update`; las otras rutas no las he seguido enteras.
- **No he medido nada.** Todo es lectura de la política.
- **`real_vram_size` y `visible_vram_size`** los doy por el estado ya
  establecido del proyecto; no los he vuelto a derivar.

## Desfalsificación

- **(a)** El default nunca concede GFX → refutable con `amdgpu_vm.c:2888-2894`:
  las dos únicas asignaciones son `..._COMPUTE` y `0`.
- **(b)** Dos funciones con el mismo texto → refutable con `:2629` y `:2738`.
- **(c)** `needs_flush` sale de `use_cpu_for_update` → refutable con
  `amdgpu_ids.c:266,334`.
- **(d)** El guardián existe → refutable con `amdgpu_vm.c:2631`.
- **(e)** Que el escritor SDMA no necesite flush → **no refutable aquí**.

## UNLOCKS

- **La línea consolidada queda corregida.** No es una razón, son dos, y la
  segunda vale para **toda placa con el driver por defecto**, no solo para esta.
- **`232` queda respondida**: el flush HDP de §G existe porque el escritor CPU
  existe en *otras* configuraciones. En esta, la rama que lo necesita es
  inalcanzable.
- **Un defecto de legibilidad concrete**: dos funciones con mensaje idéntico para
  decisiones opuestas. Un driver propio debería diferenciar los strings, y eso es
  una mejora de diagnóstico, no de función.
- **Para el driver propio hay una decisión que el driver por defecto no toma**:
  esta placa no tiene ruta CPU para GFX porque nadie la pidió, no porque el
  hardware no la soporte. Con BAR completo y parámetro a 1, la tiene.
- **Siguiente paso natural**: `amdgpu_gmc_vram_full_visible` decide en cinco
  sitios distintos (`amdgpu_cs.c:752,811,833`, `amdgpu_object.c:709`,
  `amdgpu_ttm.c:138`). Cuáles de esos son alcanzables en esta placa es la
  propagación del resultado negativo, y es lo que falta para cerrar §F.

## Evidencia

```
amdgpu_drv.c:174    int amdgpu_vm_update_mode = -1
amdgpu_drv.c:458-460  "0 = never, 1 = Graphics only, 2 = Compute only, 3 = Both.
                       The default is -1 (Only in large BAR(LB) systems
                       Compute VM tables will be updated by CPU, otherwise 0)"
amdgpu_drv.c:462    module_param_named(..., int, 0444)

amdgpu_vm.c:2888    ... = AMDGPU_VM_USE_CPU_FOR_COMPUTE;    <- unica rama util
amdgpu_vm.c:2894    ... = 0;
amdgpu_vm.c:2626    use_cpu_for_update = !!(mode & AMDGPU_VM_USE_CPU_FOR_GFX)
amdgpu_vm.c:2631    WARN_ONCE(use_cpu && !full_visible, "recommended only for large BAR")
amdgpu_vm.c:2735    use_cpu_for_update = !!(mode & AMDGPU_VM_USE_CPU_FOR_COMPUTE)

amdgpu_vm.h:185-186  AMDGPU_VM_USE_CPU_FOR_GFX (1<<0) / _FOR_COMPUTE (1<<1)
amdgpu_gmc.h:394     return (gmc->real_vram_size == gmc->visible_vram_size)

amdgpu_ids.c:266    bool needs_flush = vm->use_cpu_for_update;
amdgpu_ids.c:307    job->vm_needs_flush = needs_flush;
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.
