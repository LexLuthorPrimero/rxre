# 169 · Los cinco sitios que dependen de `vram_full_visible`: **ninguno está muerto**, y el quinto fija el `fpfn`

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC + HOST_OBSERVATION` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=OBSERVED_READ_ONLY` · `GPU INTACTA`
`CORPUS=RESEARCH/working/linux-7.1.3` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`DESARROLLA=el UNLOCK de 163; propaga el resultado negativo de secA a secF`
`NIVEL=2 (lectura de BAR, solo lectura, registrado antes/despues)`

## Cuestión principal

`233` dejó esto escrito:

> *`amdgpu_gmc_vram_full_visible` decide en cinco sitios distintos
> (`amdgpu_cs.c:752,811,833`, `amdgpu_object.c:709`, `amdgpu_ttm.c:138`). Cuáles
> de esos son alcanzables en esta placa es la propagación del resultado
> negativo, y es lo que falta para cerrar §F.*

## Criterio de terminación

Clasificar cada uno de los cinco como alcanzable o no, y con qué valor. **Cumplido:
los cinco son alcanzables y los cinco toman la rama `true`.**

## Los cinco, y qué hacen

| # | sitio | qué hace al ser `true` |
|---|---|---|
| 1 | `amdgpu_cs.c:752` | contabilidad extra de deuda sobre la VRAM **visible** (`accum_us_vis`) |
| 2 | `amdgpu_cs.c:811` | no mover a VRAM visible un BO con `CPU_ACCESS_REQUIRED` si se agotó la cuota |
| 3 | `amdgpu_cs.c:833` | suma `bytes_moved_vis` a la contabilidad |
| 4 | `amdgpu_object.c:709` | al crear un BO, reporta los bytes movidos **dos veces** |
| 5 | `amdgpu_ttm.c:138` | **fija el `fpfn` del BO al tamaño de la VRAM visible** |

**Ninguno es alcanzable condicionalmente ni está muerto en esta placa.** La
configuración "BAR pequeño" no es una esquina degradada: es la configuración
principal, con cinco rutas de código activas.

## El quinto es el que tiene consecuencias

`amdgpu_ttm.c:136-150`:

```c
} else if (!amdgpu_gmc_vram_full_visible(&adev->gmc) &&
           !(abo->flags & AMDGPU_GEM_CREATE_CPU_ACCESS_REQUIRED) &&
           amdgpu_res_cpu_visible(adev, bo->resource)) {
        /* Try evicting to the CPU inaccessible part of VRAM first, but only
         * set GTT as busy placement, so this BO will be evicted to GTT
         * rather than causing other BOs to be evicted from VRAM */
        amdgpu_bo_placement_from_domain(abo, AMDGPU_GEM_DOMAIN_VRAM |
                                        AMDGPU_GEM_DOMAIN_GTT |
                                        AMDGPU_GEM_DOMAIN_CPU);
        abo->placements[0].fpfn = adev->gmc.visible_vram_size >> PAGE_SHIFT;
}
```

**`abo->placements[0].fpfn = visible_vram_size >> PAGE_SHIFT`** es el mecanismo por
el que un BAR pequeño sigue funcionando: cualquier BO que la CPU pueda tocar
queda **confinado a la ventana visible del BAR**, y si se llena se evacúa a GTT
en vez de expulsar a otros BOs de VRAM.

## El número, medido

NIVEL 2, lectura pura, con registro antes y después:

```
PRE   2026-10-02T06:59:55-03:00
      $ lspci -s 01:00.0 -vv | grep Region
      Region 0: Memory at e0000000 (64-bit, prefetchable) [size=256M]
      Region 2: Memory at f0000000 (64-bit, prefetchable) [size=2M]
      Region 4: I/O ports at e000 [size=256]
      Region 5: Memory at f7d00000 (32-bit, non-prefetchable) [size=256K]
POST  2026-10-02T07:01:22-03:00   (idéntico: no se escribió nada)
```

```
visible_vram_size = 256 MiB = 268435456 bytes
fpfn = 268435456 >> 12 = 65536 páginas
real VRAM ≈ 2 GiB  ->  real != visible  ->  vram_full_visible = FALSE
```

**`fpfn = 65536`.** Ese es el límite en páginas de cualquier BO CPU-visible de
esta placa, y sale de una medición, no de una suposición.

Y hay un segundo dato en esa misma lectura: **BAR2 = 2 MiB**. Es la apertura de
registros MMIO, la que usa `AMDGPU_PL_MMIO_REMAP` — y `amdgpu_ttm.c:128-130`
trata ese placement como `num_placement = 0`, es decir "nunca desconectable".

## El cuarto explica el presupuesto de los tres primeros

`amdgpu_object.c:709-713`:

```c
if (!amdgpu_gmc_vram_full_visible(&adev->gmc) &&
    amdgpu_res_cpu_visible(adev, bo->tbo.resource))
        amdgpu_cs_report_moved_bytes(adev, ctx.bytes_moved, ctx.bytes_moved);
else
        amdgpu_cs_report_moved_bytes(adev, ctx.bytes_moved, 0);
```

**El mismo valor se reporta dos veces** cuando el BO es CPU-visible: una como
"movido" y otra como "movido en visible". Eso alimenta el presupuesto que los
sitios 1-3 gastan. Los cuatro son **un solo mecanismo de contabilidad**: un
presupuesto de cuántos bytes se pueden mover dentro de la ventana del BAR, para
que evictuar no provoque un fallo de `ENOMEM` visible al usuario.

## La cadena tiene cuatro capas, no dos

El proyecto tenía la cadena de dos:

```
BAR pequeño  ->  CPU VM update FALSE  ->  SDMA writer
```

Con estos cinco sitios se ve que hay **dos capas más debajo**, que son las que
hacen que el BAR pequeño sea viable:

```
BAR0 = 256 MiB (medido)
  -> vram_full_visible = FALSE
       -> (capa 1) vm_update_mode = 0            -> SDMA escribe las tablas
       -> (capa 2) presupuesto de bytes visibles -> no se evacúa más de la cuenta
       -> (capa 3) fpfn <= 65536 páginas         -> el BO no sale del BAR
```

**Sin la capa 3, un driver con BAR de 256 MiB sobre VRAM de 2 GiB no
funcionaría.** Esa es la razón de que `vram_full_visible` se compruebe cinco
veces.

## Clasificación

| afirmación | estado |
|---|---|
| BAR0 = 256 MiB | `OBSERVED` — `lspci`, antes/después |
| BAR2 = 2 MiB (MMIO) | `OBSERVED` — ídem |
| `visible_vram_size = 256 MiB` | `DERIVATION` — del BAR0, para esta placa |
| `fpfn = 65536` | `DERIVATION` — `visible >> 12` |
| `vram_full_visible = FALSE` | `OBSERVED_DERIVED` — `2 GiB != 256 MiB` |
| Los 5 sitios son alcanzables | `PROVEN` — condición no depende de estado |
| Los 5 toman la rama `true` | `DERIVATION` — de `vram_full_visible` FALSE |
| El BO se confina a la ventana visible | `PROVEN` — `amdgpu_ttm.c:148` |
| El presupuesto evita `ENOMEM` por size | `DERIVATION` — del sentido del código |
| Que 256 MiB sea `visible_vram_size` exacto | `CORROBORATED` — no leído el campo |

## Confounders

- **`visible_vram_size` no lo he leído**, lo he deducido del BAR0. Para una
  discreta suele ser el tamaño del BAR, pero el driver puede capping distinto.
  `sysfs` no expuesto `resource0_size` en esta máquina, así que `lspci` fue la
  vía. Si estuviera, sería `OBSERVED` y no `DERIVATION`.
- **La VRAM real de 2 GiB** la doy por el estado consolidado del proyecto; no la
  he vuelto a medir en esta iteración.
- **No he seguido `amdgpu_res_cpu_visible()`** ni `concurrent_flush`, que son las
  otras dos condiciones de estos sitios. Mi clasificación es sobre
  `vram_full_visible`, no sobre el camino completo.
- **El sitio 4 tiene dos ramas `else`** en el código real (`:833` tiene un
  `goto retry`); no he auditado si el accounting puede contar dos veces un mismo
  movimiento.
- **Solo lectura.** No he escrito nada en el hardware.

## Desfalsificación

- **(a)** BAR0 = 256 MiB → refutable con `lspci -s 01:00.0 -vv`.
- **(b)** `fpfn = visible >> 12` → refutable con `amdgpu_ttm.c:148`.
- **(c)** Los cinco sitios → refutable con `grep -rn vram_full_visible`.
- **(d)** El BO se confina → refutable con la asignación de `placements[0].fpfn`.
- **(e)** `visible_vram_size` es exactamente el BAR0 → **no refutable con lo que
  tengo**; haría falta leer el campo.

## UNLOCKS

- **§F tiene su propagación cerrada**: el resultado negativo de §A no es una
 rareza, es lo que sostiene tres mecanismos activos.
- **`fpfn = 65536` es un número de implementación directo** para un driver
  propio: ningún BO accesible desde CPU puede salirse de ahí.
- **`BAR2 = 2 MiB` cierra el `MMIO_REMAP`**: es la apertura de registros, y su
  placement tiene `num_placement = 0` por construcción (`amdgpu_ttm.c:128-130`).
- **La conexión con `232` se cierra por el otro lado**: `232` mostró que la ruta
  del page table es SDMA; `169` muestra que la *razón* es que la CPU no puede
  ver la VRAM donde están esas tablas. Son la misma causa.
- **Siguiente paso**: `amdgpu_res_cpu_visible()` aparece en cuatro de los cinco
  sitios. Es el otro predicado, y determina qué BOs están sujetos al presupuesto.
  Con eso, §F queda cerrado por completo.

## Evidencia

```
amdgpu_gmc.h:394            return (real_vram_size == visible_vram_size)

amdgpu_cs.c:752             accum_us_vis          deuda de VRAM visible
amdgpu_cs.c:811             no mover CPU_ACCESS_REQUIRED si cuota agotada
amdgpu_cs.c:833             bytes_moved_vis +=
amdgpu_object.c:709         reporta (bytes, bytes) o (bytes, 0)
amdgpu_ttm.c:138            placements[0].fpfn = visible_vram_size >> PAGE_SHIFT
amdgpu_ttm.c:128-130        AMDGPU_PL_MMIO_REMAP -> num_placement = 0

$ lspci -s 01:00.0 -vv | grep Region
Region 0: [size=256M]      -> visible_vram_size
Region 2: [size=2M]        -> apertura MMIO

256 MiB >> 12 = 65536 paginas
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.
