# bootlog — lo que el host ya dijo y nadie exploitable

## Qué es

Extracción del registro de arranque del kernel (`journalctl -k -b`, solo
lectura) de la RX550 de este host. Son **observaciones**, no derivaciones: el
driver produjo estas líneas describiendo el hardware que encontró.

No requiere root y no toca la GPU. `GPU INTACTA`, `WRITE_EXECUTION NONE`.

## Valor

El log tiene 97 líneas de amdgpu. Casi todas son geometría que ya estaba
modelada. Pero dos líneas aportan algo que el corpus **no** puede dar, porque
son hechos de este hardware concreto.

## 1. Topología real de CUs

```
amdgpu 0000:01:00.0: SE 2, SH per SE 1, CU per SH 5, active_cu_number 8
```

`AGENTS.md` ya declaraba «2 shader engines, 1 shader array por SE, 8 CUs, CU
masks 0x1e». El log **confirma** esos cuatro datos y añade el desglose que no
estaba explícito: `CU per SH = 5` con `active_cu_number = 8`.

Eso tiene una consecuencia aritmética que conviene no pasar por alto:

```
SH por SE = 1, CU por SH = 5  ->  5 CUs por SE
SE = 2                          ->  2 × 5 = 10 CUs fisicos
active_cu_number = 8            ->  8 CUs activos
```

Así que hay **10 CUs físicos y 8 activos**, no 8 físicos. Los 8 son los que
`active_cu_number` refleja tras el enmascaramiento. Es la clase de detalle que
importa al escribir un kernel propio: elmask de CUs (`0x1e`) selecciona 8 de
10, y ese residuo no aparece en ninguna lectura queparta de "8 CUs".

`OBSERVATION` → `CORROBORATED` para los cuatro valores ya declarados.
`DERIVATION` nueva: 10 CUs físicos, 8 activos.

## 2. El hardware pidió PRT y el driver loactuo

```
amdgpu 0000:01:00.0: Disabling VM faults because of PRT request!
```

Esta es la observación con más valor del log, porque cierra una cadena completa
que el corpus solo tenía en estática.

### La cadena

```
proceso de usuario
  -> ioctl DRM_IOCTL_AMDGPU_GEM_VA con AMDGPU_VM_PAGE_PRT
     (amdgpu_gem.c:815, prt_flags = DELAY_UPDATE | PAGE_PRT)
  -> mapping->flags |= AMDGPU_VM_PAGE_PRT
  -> el driver detecta la bandera en amdgpu_vm_fini (amdgpu_vm.c:2814)
  -> llama gmc_funcs->set_prt(adev, true)
     (vtable, gmc_v8_0.c:1738 -> gmc_v8_0_set_prt, gmc_v8_0.c:766)
  -> escribe mmVM_PRT_CNTL: CB_DISABLE_READ/WRITE_FAULT_ON_UNMAPPED_ACCESS = 1
  -> el hardware deja de generar fault de VM en accesos no mapeados
```

`max_cu_per_sh` viene del **VBIOS**, no de una constante del driver
(`amdgpu_atomfirmware.c:964`, campo `v27.max_cu_per_sh` de la tabla
`ATOM_IGD_INFO`; también `amdgpu_device.c:1848` por la vía
`gpu_info_fw->gc_num_cu_per_sh`). Por eso el corpus **no puede derivarlo**: es
una propiedad de esta placa concreta, y el único modelo que la contiene es el
VBIOS de esta GPU.

Para un driver propio esto significa que el número de CUs no se puede
codificar: hay que leerlo del VBIOS igual que hace el driver de referencia. Y
que el `CU masks 0x1e` declarado en `AGENTS.md` es una consecuencia del
`active_cu_number`, no del número de CUs que el hardware tiene.

Es decir: **un proceso en esta máquina usó PRT, y el driver y el hardware
respondieron**. Eso es una confirmación de runtime que ningún documento
estático puede dar.

### Por qué esto NO contradice a `pteflags`

`pteflags` clasificó `AMDGPU_PTE_PRT` como `CLEARED_NOT_SET`, con la nota
«`gmc_v8_0_get_vm_pte` lo borra, no lo pone». **Eso sigue siendo cierto** y no
se toca.

Lo que este hallazgo añade es que PRT tiene **dos mecanismos distintos**:

| | PTE bit 51 | `mmVM_PRT_CNTL` |
|---|---|---|
| naturaleza | flag por entrada | registro de control global |
| granularidad | por PTE | por GPU |
| quién lo escribe | `get_vm_pte` lo borra | `gmc_v8_0_set_prt` lo pone |
| en GFX8 | nunca activo | **activado por hardware en runtime** |

Confundir los dos produce un error concreto: buscar el bit 51 en las PTEs para
saber si PRT está activo, cuando en GFX8 la señal real está en
`VM_PRT_CNTL`. Para un driver propio, `PRT` es un registro de estado global
que hay que leer y propagar, no un bit de entrada.

### Clasificación

- Existe la ruta GFX8 de PRT y el hardware la ejerció: **OBSERVED**
- `AMDGPU_PTE_PRT` nunca se pone en GFX8: **PROVEN** (`pteflags`, sin cambio)
- La semántica de hardware de `CB_DISABLE_*_FAULT_ON_UNMAPPED_ACCESS`:
  **NOT_DETERMINED**. El log prueba que se activó, no qué efecto exacto tuvo.

## 3. Cuarta vía independiente de que GFX8 no usa MTYPE

Ya había tres: `gmc_v8_0.c` no abre ningún `_enum.h`; el BTF del módulo cargado
no tiene campo MTYPE en `amdgpu_gart`; los cinco enums `MTYPE` del binario no
tienen ninguna referencia.

La cuarta: `AMDGPU_VM_MTYPE_MASK` es un flag de VA **aceptado por el ioctl**
(`amdgpu_gem.c:814`, en `valid_flags`), pero solo lo consumen:

```
gmc_v9_0.c   gmc_v10_0.c   gmc_v11_0.c   gmc_v12_0.c   gmc_v12_1.c
```

`gmc_v8_0.c` **no aparece**. Por enumeración de ficheros, no leyendo una rama
y suponiendo que es inalcanzable.

Esto importa porque el ioctl **acepta** MTYPE en cualquier ASIC. Un usuario
puede pedirlo en GFX8 y el driver no lo rechaza en la validación: simplemente no
existe consumidor. La necesidad de rechazarlo es un requisito de un driver
propio.

## Limitaciones

- El registro de arranque es de **este** arranque. Si el módulo se recargó con
  parámetros distintos, el log ya no lo refleja.
- `/sys/module/amdgpu/parameters/*` no es legible sin root, así que no se puede
  saber si algún paráximo alteró la geometría.
- `10:55:34` es la hora del mensaje de PRT, casi cinco horas después del
  arranque (`05:49:05`). El evento que lo disparó no aparece en el log.
- No hay forma de confirmar que el proceso que pidió PRT fuera el mismo que
 hemos.

## Cómo reproducir

```sh
journalctl -k -b --no-pager | grep amdgpu
```

Solo lectura. No se escribe nada, no se toca la GPU.