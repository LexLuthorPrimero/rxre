# 243 · Los 5.907 MiB de GTT son la mitad de la RAM, y el «residuo de 136 MiB» que yo escribí era un error mío

```text
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC+RUNTIME
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0 · WRITE_EXECUTION=NONE
RUNTIME=/proc/meminfo SOLO LECTURA · GPU INTACTA
```

## Qué resuelve

**El punto abierto número 1 de `204`: de dónde salen los 5.907 MiB de GTT.** `PROVEN`.

**⇒ `ttm_tt_pages_limit()` no está en el corpus — `drivers/gpu/drm/ttm/` no existe, y tampoco
existe ningún header que lo declare, porque `include/linux/` tiene un solo fichero.** `PROVEN_ABSENT`.

**⇒ Pero el valor observado cuadra exactamente, sin residuo, con la mitad de la RAM del host:
`MemTotal = 12.098.912 kB`, `12098912 / 2 / 1024 = 5907` MiB.** `PROVEN_DERIVED`.

**⇒ Y el «136 MiB sin explicar» que escribí en el punto de partida de esta nota era un error
aritmético mío, no un hecho.** `ERROR`. Es la quinta vez que me pasa en esta línea y la razón
es siempre la misma: calcular el número en la cabeza en vez de dejar que el programa lo calcule.
La mitad de 12.098.912 kB son 6.049.456 kB, y eso son 5.907 MiB. Lo comprobé en `/proc/meminfo`
y en el propio texto de `024-page-table-geometria-gfx8.md:116`, que ya citaba el valor correcto.

## 1 · Lo que el corpus no tiene

```text
[ -d drivers/gpu/drm/ttm ]        -> AUSENTE
[ -d include/drm ]                -> AUSENTE
[ -d include/uapi ]               -> AUSENTE
[ -d drivers/gpu/drm/drm-sched ]  -> AUSENTE
find include/linux -type f | wc -l -> 1   (solo pm_runtime.h)
grep -rn ttm_tt_pages_limit include/  -> (cero resultados)
```

**⇒ `PROVEN_ABSENT`. La definición de `ttm_tt_pages_limit()` está en un directorio que este
corpus no contiene, y no hay ninguna declaración de ella en el único directorio de cabeceras
que sí contiene.** `PROVEN`.

**⇒ Los cinco sitios que la llaman son todos de amdgpu y amdkfd:**

| fichero:línea | uso |
|---|---|
| `amdgpu_ttm.c:2140` | `gtt_size = ttm_tt_pages_limit() << PAGE_SHIFT;` |
| `amdgpu_amdkfd.c:520` | `mem_info->local_mem_size_public = (ttm_tt_pages_limit() << PAGE_SHIFT);` |
| `amdgpu_amdkfd.c:829` | `tmp = (ttm_tt_pages_limit() << PAGE_SHIFT) / num_online_nodes();` |
| `amdgpu_amdkfd.c:839` | `return (ttm_tt_pages_limit() << PAGE_SHIFT);` |
| `amdgpu_amdkfd_gpuvm.c:131` | `kfd_mem_limit.max_ttm_mem_limit = ttm_tt_pages_limit() << PAGE_SHIFT;` |

**⇒ `PROVEN`. Y el segundo uso relevante es la misma función partida por número de nodos NUMA
en `amdgpu_amdkfd.c:829`, lo que significa que el valor de 5.907 MiB que observé es el del nodo
que reporta el log, no un total de la máquina.** `PROVEN_DERIVED`.

## 2 · La aritmética, por programa y no mentalmente

```python
MemTotal            = 12098912 kB = 11.54 GiB
/2                  = 6049456 kB
/2//1024            = 5907 MiB   <-- OBSERVADO: "5907M of GTT memory ready."
```

**⇒ `PROVEN_DERIVED`. El rango de `MemTotal` que produce exactamente 5.907 por esa operación es
12.097.536 .. 12.099.583 kB, y el valor real de esta host, 12.098.912 kB, cae dentro.** `PROVEN`.

**⇒ Y el orden de magnitud cuadra por un motivo que sí está en el corpus: la comparación que el
propio driver hace es entre GTT y VRAM, `amdgpu_ttm.c:2164` `if (adev->gmc.real_vram_size < gtt_size)`.
Con 2.048 MiB de VRAM y 5.907 MiB de GTT la comparación es falsa, que es exactamente el caso en
el que el log muestra la línea.** `PROVEN_DERIVED`.

## 3 · El valor es sustituible desde userspace, y eso es la parte accionable

**⇒ `amdgpu_drv.c:155` declara `int amdgpu_gtt_size = -1; /* auto */`, y `amdgpu_drv.c:302`
lo expone como `module_param_named(gttsize, amdgpu_gtt_size, int, 0600)`, con la descripción
`"Size of the GTT userspace domain in megabytes (-1 = auto)"` en `amdgpu_drv.c:301`.** `PROVEN`.

**⇒ Y `amdgpu_ttm.c:2141-2151` lo respeta: si `amdgpu_gtt_size != -1` usa
`(uint64_t)amdgpu_gtt_size << 20` y avisa por `drm_warn` si el valor calculado por TTM no coincide.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Consecuencia práctica: los 5.907 MiB que vi son el valor por defecto con
`gttsize` sin tocar. Cambiando `amdgpu.gttsize=N` a `< 2048` la ventana de GTT pasa a ser más
pequeña que la VRAM, y entonces se entra en la rama de `amdgpu_ttm.c:2164` que ya no estaba
probada. Es un experimento de NIVEL 2, de los que sólo necesitan `amdgpu.gttsize=` y recargar
el módulo, sin tocar hardware.** `NOT_TESTED`.

**⇒ Y hay un suelo declarado en `amdgpu_device.c:1563`: si `amdgpu_gtt_size != -1 &&
amdgpu_gtt_size < 32` el driver lo descarta y lo pone a `-1` con un `drm_warn`, es decir 32 MiB
es el menor valor que sobrevive.** `PROVEN`.

## 4 · El censo del corpus, que es la otra mitad de esta nota

**⇒ El corpus tiene 2.787 ficheros y sólo tres directorios de primer nivel: `Documentation/`,
`drivers/` e `include/`.** `PROVEN`.

| primer nivel | ficheros | líneas |
|---|---|---|
| `drivers/` | 2.785 | 6.175.805 |
| `Documentation/` | **1** | 704 |
| `include/` | **1** | 823 |

**⇒ `drivers/gpu/drm/` contiene un único directorio, `amd/`, con 2.769 ficheros, el 99,35% de
`drivers/`.** `PROVEN`.

**⇒ Los dos únicos ficheros del corpus que no son del subárbol de AMD son
`Documentation/ABI/testing/sysfs-bus-pci` y `include/linux/pm_runtime.h`.** `PROVEN`.

**⇒ Eso corrige un dato que el estado venía arrastrando —«984/986 ficheros, único hueco
`include/uapi/` e `include/drm/`»—: el número real es 2.787 ficheros y los huecos son mucho
mayores que dos directorios.** `ERROR`.

**⇒ Y `drivers/gpu/drm/amd/include/asic_reg/` tiene 476 ficheros, los 476 con extensión `.h`:
offsets, máscaras de shift, valores por defecto, funciones de registro, enums y SMN. No hay ni
un fichero de descripción.** `PROVEN`.

## 5 · `UN_REGISTRO` no significa lo que parecía

**⇒ `OPEN-FRONTIERS.md` contiene 34 filas marcadas `UN_REGISTRO`, que nombran 5 registros
distintos: `mmVM_INVALID` (6 veces), `mmGDS_COMPUT` (5), `mmGPU_HDP_FLUSH_REQ` (4),
`mmVM_CONTEXT1_PROTECT` (3), `mmSMC_IND_DA` (3).** `PROVEN`.

**⇒ Y los cinco están presentes en `asic_reg/`, en 13, 12, 7, 5 y 7 ficheros respectivamente.** `PROVEN`.

**⇒ `PROVEN_DERIVED. `UN_REGISTRO` no quiere decir «el registro no está en el corpus», quiere
decir «el registro no tiene documentación». El corpus tiene 476 cabeceras de registros y cero
documentación de registros, porque su único fichero de documentación es un ABI de sysfs de PCI
que no tiene nada que ver.** `PROVEN_DERIVED`.

**⇒ Y la consecuencia es la que decide si una frontera se puede cerrar: una fila `UN_REGISTRO`
con el nombre del registro y sin su semántica no se cierra leyendo este corpus. Se cierra
leyendo documentación externa, que es una fuente de otro proyecto y no fuente primaria.** `PROVEN_DERIVED`.

## 6 · Lo que queda abierto de §F

**⇒ El último tramo de §F —de la ventana de GTT a la RAM del sistema— queda cerrado por la
aritmética y abierto por el mecanismo: sé que 5.907 es la mitad de `MemTotal` y sé que la función
que lo produce no está en el corpus, pero no sé qué reserva le resta el TTM ni si esa reserva es
la que explica el suelo de `gttsize`.** `NOT_DETERMINED`.

**⇒ Es el mismo tipo de cierre que `dc/dce60`: evidencia independiente suficiente para la
medida, fuente ausente para el mecanismo.** `PROVEN_DERIVED`.

**⇒ Y con esto `§F` queda sin ningún punto abierto que no sea de la forma «mecanismo ausente»:
la base de VRAM, el tamaño de VRAM, el final de VRAM, el agujero, el GART y el GTT están todos
medidos contra el log y explicado contra el corpus, salvo por la función del TTM que no está
en el árbol.** `PROVEN_DERIVED`.