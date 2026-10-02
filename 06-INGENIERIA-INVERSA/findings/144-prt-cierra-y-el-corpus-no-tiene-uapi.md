# 144 · El PRT cierra en comportamiento y no en número, y el corpus no tiene interfaz de usuario

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

Dos cosas, y la segunda es la que cambia el estado del proyecto.

1. **El PRT queda cerrado en comportamiento.** Se sabe exactamente qué hay que hacer
   para activarlo, qué escribe, y por qué `099` no era un fallo. **Y se descubre una
   asimetría en GFX8 que un driver propio no debe replicar.**
2. **El corpus no contiene ninguna interfaz de usuario.** Ni las estructuras, ni los
   números de ioctl, ni los valores de las banderas. **El único hueco que queda para
   el objetivo final del proyecto no es de hardware y no se cierra investigando.**

## 1 · Qué es un mapeo PRT

`amdgpu_gem.c:812-817`, las dos listas de banderas admitidas:

```c
const uint32_t valid_flags = AMDGPU_VM_DELAY_UPDATE |
        AMDGPU_VM_PAGE_READABLE | AMDGPU_VM_PAGE_WRITEABLE |
        AMDGPU_VM_PAGE_EXECUTABLE | AMDGPU_VM_MTYPE_MASK |
        AMDGPU_VM_PAGE_NOALLOC;
const uint32_t prt_flags = AMDGPU_VM_DELAY_UPDATE |
        AMDGPU_VM_PAGE_PRT;
```

**`AMDGPU_VM_PAGE_PRT` no está en `valid_flags`. Está en un conjunto aparte.** Y la
validación (`L859`) es:

```c
if ((args->flags & ~valid_flags) && (args->flags & ~prt_flags)) {
        dev_dbg(dev->dev, "invalid flags combination 0x%08X\n", args->flags);
        return -EINVAL;
}
```

**Se acepta si no hay bits fuera de `valid_flags` *o* no hay bits fuera de
`prt_flags`.** Evaluado:

| banderas | `~valid_flags` | `~prt_flags` | ¿se acepta? |
|---|---|---|---|
| `DELAY_UPDATE` (sólo) | 0 | `PAGE_PRT` | **sí** (primer término 0) |
| `DELAY_UPDATE\|PAGE_PRT` | `PAGE_PRT` | 0 | **sí** (segundo término 0) |
| `...\|PAGE_READABLE` | `PAGE_PRT` | `PAGE_READABLE` | **no** — ambos no nulos |
| `PAGE_PRT` sin `DELAY_UPDATE` | `DELAY_UPDATE\|PAGE_PRT` | 0 | **sí** (pero ver §2) |

**`AMDGPU_VM_PAGE_PRT` es estrictamente exclusivo con `READABLE`, `WRITEABLE`,
`EXECUTABLE`, `NOALLOC` y `MTYPE`, y va siempre con `AMDGPU_VM_DELAY_UPDATE`.**
`PROVEN`, una línea de booleano.

## 2 · Y un mapeo PRT no tiene objeto de respaldo

`amdgpu_gem.c:882-891`:

```c
if ((args->operation != AMDGPU_VA_OP_CLEAR) &&
    !(args->flags & AMDGPU_VM_PAGE_PRT)) {
        gob = drm_gem_object_lookup(filp, args->handle);
        ...
        abo = gem_to_amdgpu_bo(gob);
} else {
        gob = NULL;
        abo = NULL;
}
```

**Con `AMDGPU_VM_PAGE_PRT` el driver no busca el BO: `gob = NULL`, `abo = NULL`.**

**Ahí está la semántica entera del PRT, en dos líneas:** es un mapeo **sin objeto de
respaldo**, para un rango de direcciones reservadas, cuyo único efecto es que los
accesos a ese rango no generen fault. Por eso no puede llevar permisos —no hay nada
que proteger— y por eso necesita `DELAY_UPDATE`: **tiene que aplicarse en el momento
del invalidate, no en el siguiente.**

`PROVEN_DERIVED`, y encaja con el nombre del registro: el `Page Request Trigger` no
pide páginas, apaga faults en un rango.

## 3 · La cadena completa, de la petición de userspace al registro

```
userspace: amdgpu_gem_va_ioctl con PAGE_PRT
   |
   +-- amdgpu_gem.c:882   NO se busca BO              -> mapeo sin respaldo
   +-- amdgpu_gem.c:859   PAGE_PRT excluye permisos    -> validado
   |
amdgpu_vm.c:1809  if (mapping->flags & AMDGPU_VM_PAGE_PRT)
amdgpu_vm.c:1810          amdgpu_vm_prt_get(adev);
   |
amdgpu_vm.c:1452  if (atomic_inc_return(&num_prt_users) == 1)
   |
amdgpu_vm.c:1436  spin_lock_irqsave(&prt_lock)
amdgpu_vm.c:1437  enable = !!atomic_read(&num_prt_users)
amdgpu_vm.c:1438  set_prt(adev, enable)
   |
gmc_v8_0.c:792   enable -> 8 registros PRT_APERTURE al rango real
gmc_v8_0.c:775   + los 7 bits de VM_PRT_CNTL
gmc_v8_0.c:771   + dev_warn "Disabling VM faults because of PRT request!"
   |
=> los faults de VM quedan desactivados en el rango reservado del driver
```

**Once saltos, de la llamada de userspace al `dev_warn`, y todos legibles.** Y el
`L1455` de `143` sigue en pie: los rangos que se silencian son
`AMDGPU_VA_RESERVED_BOTTOM` a `max_pfn` menos `AMDGPU_VA_RESERVED_TOP` — las dos
franjas que el driver se reserva.

## 4 · Y la asimetría de GFX8, que es lo que hay que saber para no copiarlo

Los cuatro ficheros que **honran** `AMDGPU_VM_PAGE_PRT` en el PTE:

```
gmc_v9_0.c:1192     gmc_v10_0.c:510     gmc_v11_0.c:501     gmc_v12_0.c:536
```

**`gmc_v8_0.c` no está, y su `get_vm_pte` hace lo contrario (`L728`):**

```c
*flags &= ~AMDGPU_PTE_PRT;
```

Entonces, en esta GPU:

| | efecto | ¿ocurre? |
|---|---|---|
| **global** | sube `num_prt_users`, y con él los faults de VM se apagan en el rango reservado | **sí** — `amdgpu_vm.c:1809` es independiente del chip |
| **por página** | el PTE lleva el bit 51 (`AMDGPU_PTE_PRT`) | **no** — forzado a cero |

**Un proceso que pida `AMDGPU_VM_PAGE_PRT` en esta GPU obtiene el efecto global —que
apaga los faults de VM de todos los demás— sin el efecto por página que lo
justifica.** `PROVEN_DERIVED`, de dos ausencias y dos presencias en ficheros
distintos.

**La regla para un driver propio, y es la conclusión de esta nota:**

> **En GFX8, `AMDGPU_VM_PAGE_PRT` no debe exponerse en el ioctl.** Aceptarlo cuesta
> silenciar faults de VM para toda la GPU y no aporta nada a quien lo pidió.

**No lo digo como juicio sobre el driver de referencia: no sé si es intencionado,
porque la uAPI no está en el corpus (§6) y no puedo ver el commit.** Lo digo como
hecho derivado, y como la razón por la que un driver propio tiene que tomar una
decisión explícita aquí.

## 5 · El ciclo se cierra con `099`, por sexta vez y ahora por mecanismo

La cadena de notas sobre PRT, con lo que aportó cada una:

| nota | aportación |
|---|---|
| `099` | observó PRT dispararse |
| `131` | encontró `VM_PRT_CNTL` = `0x534` con siete campos |
| `138` | los protection faults van a la página por defecto por defecto |
| `139` | `AMDGPU_PTE_PRT` (bit 51, reservado) **no es** `VM_PRT_CNTL` |
| `142` | el bloque de nueve registros `0x52c`–`0x534` |
| `143` | el PRT es un contador de referencias; los golden escriben el valor de "desactivado" |
| **`144`** | **PRT = un mapeo sin BO, exclusivo con los permisos; en GFX8 el efecto global ocurre y el por página no** |

**Y la explicación de `099`, completa:** un PRT que dispara significa que algún
proceso pidió un mapeo sin respaldo, que el drivercez le apagó los faults de VM en
su rango reservado, y que por eso hay un `dev_warn` en el log. **No es un fallo del
gestor de memoria, no es una configuración mal formada, y no es una contradicción
entre `099` y `131`. Es la función trabajando.**

## 6 · El corpus no tiene interfaz de usuario, y eso es lo que queda

Aquí medí el alcance del corpus, y el resultado es la cosa más importante de esta
nota.

| | |
|---|---|
| ficheros en el corpus | **2787** |
| de los cuales `.c` | 984 |
| de los cuales `.h` | 1721 |
| `.c` del driver amdgpu | 304 |
| `.h` del driver amdgpu | 321 |
| `.h` de `asic_reg/` | 551 |
| **`include/uapi/`** | **NO EXISTE** |
| **`include/drm/`** | **NO EXISTE** |
| `include/linux/` | **1 fichero** — `pm_runtime.h` |
| `Documentation/` | **1 fichero** — `ABI/testing/sysfs-bus-pci` |

**Y las dos comprobaciones que lo cierran:**

```
struct drm_amdgpu_gem_va            -> NO DEFINIDO EN NINGUNA PARTE DEL CORPUS
struct drm_amdgpu_gem_va_mapping    -> NO DEFINIDO EN NINGUNA PARTE DEL CORPUS
```

**Y `amdgpu_gem.c` incluye once cabeceras que el corpus no tiene**, entre ellas
`drm/amdgpu_drm.h` y todo el árbol `drm/`:

```
FALTA  drm/amdgpu_drm.h          FALTA  drm/drm_drv.h        FALTA  drm/drm_exec.h
FALTA  drm/drm_gem_ttm_helper.h  FALTA  drm/drm_syncobj.h    FALTA  drm/ttm/ttm_tt.h
FALTA  linux/ktime.h             FALTA  linux/module.h       FALTA  linux/pagemap.h
FALTA  linux/pci.h               FALTA  linux/uaccess.h
```

**El corpus es un subconjunto curado: el driver amdgpu, sus cabeceras de registros,
`drivers/pci`, `drivers/base`, un fichero de ABI de PCI sysfs y una cabecera del
kernel.** Y nada más.

### Qué significa eso, en concreto

**Todo lo que el proyecto ha glittering correctamente hasta ahora es interno al
driver.** La geometría de la tabla de páginas, la configuración de TLB y L2, el mapa
de direcciones, el formato del PTE, los registros del PRT, la cadena del invalidate:
todo eso vive en `drivers/gpu/drm/amd/amdgpu` y en `asic_reg/`, y todo eso está
cerrado o acotado.

**Lo que falta es la frontera del driver con el mundo**, y son cuatro cosas:

| falta | para qué |
|---|---|
| los números de ioctl de `DRM_IOCTL_AMDGPU_*` | que algo pueda invocar el driver |
| el layout de `drm_amdgpu_gem_va` y `drm_amdgpu_gem_va_mapping` | para pedir mapeos |
| los valores de `AMDGPU_VM_*`, `AMDGPU_VA_OP_*`, `AMDGPU_PTE_*` | para expresarlos |
| la semántica de `AMDGPU_VM_PAGE_PRT` en el contrato de userspace | para §4 |

**Y ninguna se deriva del corpus. No es `NOT_DETERMINED`, que se cierra con más
lectura: es `NOT_IN_CORPUS` en el sentido fuerte, y la medición lo demuestra.**

**Consecuencia directa para el objetivo final del proyecto:** un driver propio
escrito con este corpus **no sería utilizable por un compositor.** Podría arrancar la
GPU, configurar la traducción, escribir los cuatro registros PRT y mapas de
memoria —todo
lo de esta tanda— pero un proceso de userspace no podría hablar con él. **Eso no es
un problema de hardware, no requiere placa, y no se resuelve investigando el
corpus.**

**Y hay una consecuencia más pequeña pero real:** `AMDGPU_VM_PAGE_PRT` es un nombre
sin número en este proyecto. Cada vez que he escrito un valor de bandera PRT en las
notas anteriores lo he hecho desde `amdgpu_vm.h` o desde `gmc_8_1_sh_mask.h`, donde
sí están; pero **las banderas `AMDGPU_VM_*` sólo son nombres aquí**, y la
verificación de la exclusividad de §1 es sobre posiciones de bit **derivadas de los
`#define` locales**, no de la uAPI.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| `PAGE_PRT` es exclusivo con los permisos | `PROVEN` (una línea de booleano) |
| Un mapeo PRT no tiene BO | `PROVEN` |
| `DELAY_UPDATE` acompaña a `PAGE_PRT` | `PROVEN` |
| La cadena userspace → registro, 11 saltos | `PROVEN_DERIVED` |
| Los rangos silenciados son las franjas reservados | `PROVEN` (`143`) |
| GFX8: efecto global sí, por página no | `PROVEN_DERIVED` |
| `gmc_v8_0.c` está en la lista de los que honran la bandera | `PROVEN_ABSENT` |
| `099` resuelto por mecanismo | `PROVEN_DERIVED` |
| El valor numérico de `AMDGPU_VM_PAGE_PRT` | **`NOT_IN_CORPUS`** |
| `struct drm_amdgpu_gem_va` | **`NOT_IN_CORPUS`** |
| Los ioctl de `DRM_IOCTL_AMDGPU_*` | **`NOT_IN_CORPUS`** |
| `AMDGPU_VM_MTYPE_MASK` y las demás `AMDGPU_VM_*` | **`NOT_IN_CORPUS`** |
| Si la asimetría de GFX8 es intencionada | **`NOT_DETERMINED`** — hace falta el commit |
| La geometría, la traducción y el mapa | **cerrados** (`132`, `136`-`140`, `143`) |

**Las cuatro primeras filas del final son un `BLOCKED_BY_EXTERNAL_DEPENDENCY`, y es
la primera vez que aparece una de esas en este proyecto.** No es hardware, no son
permisos, no es una sesión gráfica que cerrar: **es un fichero que no está.**

## Procedencia

- `STATIC` -- `amdgpu_gem.c:809-891`, `amdgpu_gem.c:812-817`, `amdgpu_gem.c:859`,
  `amdgpu_gem.c:882-891`, `amdgpu_vm.c:1431-1549`, `amdgpu_vm.c:1809-1810`,
  `amdgpu_vm.c:2117-2133`, `amdgpu_vm.c:2791-2814`, `gmc_v8_0.c:766-816`,
  `gmc_v8_0.c:1738`, `gmc_v9_0.c:1192`, `gmc_v10_0.c:510`, `gmc_v11_0.c:501`,
  `gmc_v12_0.c:536`.
- Medición del corpus: `find` sobre `linux-7.1.3`, recuentos de `.c`/`.h` por
  directorio, `grep -rn 'struct drm_amdgpu_gem_va {'` sobre el árbol entero,
  y contraste de cada `#include <...>` de `amdgpu_gem.c` contra `find -path`.
  **Todo impreso por programa.** La cuenta de ficheros del corpus es lo que sostiene
  §6, y sale de un `find`, no de una impresión.
- Encadenada con `143` (el contador de referencias y los golden), `142` (el bloque
  `0x52c`–`0x534` y la apertura AGP), `139` (la homonimia PRT), `138` (los
  protection faults), `131` (`VM_PRT_CNTL`), `099` (**cerrado**), `140` (el mapa de
  direcciones), `136`/`137` (la traducción).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**Fui a cerrar el PRT por el lado de software y me topé con el borde del mundo.**

Iba a hacer una cosa pequeña: cuatro `grep` para ver quién pone
`AMDGPU_VM_PAGE_PRT`. Salió una lista de doce usos, cuatro ficheros que honran la
bandera y uno que la borra — **todo el Thread cerrado** — y después, por confirmar
el valor de la bandera, un `grep` que no devolvió nada.

**Un `grep` vacío es la señal más valiosa que da una herramienta, y casi siempre
significa que la pregunta estaba mal hecha.** No era que la bandera no tuviese valor:
es que **el fichero donde viven todos los valores no está en el corpus.** Y de ahí
salió lo que de verdad importa, que no era el PRT: **el proyecto lleva ciento
cuarenta y tres notas cerrando el interior del driver, y la frontera con el mundo no
está.**

*El valor de una constant depende de dónde vive, y un `grep` que no encuentra nada
no dice "no existe": dice "no está donde yo estoy mirando".* Y cuando el fichero
que falta es la uAPI entera, el `grep` vacío no es un hueco pequeño — **es la
medida exacta de lo que el corpus no es.**

**Y la lección de fondo es la de `140` y `142`, del revés.** Allí, dos notas
seguidas, el camino barato fue leer lo que el driver imprimía. Aquí el camino barato
fue leer lo que el driver **incluía**, y la lista de includes resultó ser el
inventario de lo que falta. **Un `#include` que no resuelve es un `NOT_IN_CORPUS`
con la medida, y vale por un finding entero.**
