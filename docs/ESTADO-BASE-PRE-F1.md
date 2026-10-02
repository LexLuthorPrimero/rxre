# Estado base pre-experimento F1 — capturado antes de cualquier carga de módulo

```
CLASSIFICATION=DOCUMENTATION · TRACK=RUNTIME_READ_ONLY · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=OBSERVED_READ_ONLY · GPU INTACTA
```

## Por qué existe este documento

Se autorizó root y contraseña para la sesión, y con eso `F1` deja de estar
`BLOCKED_BY_AUTHORIZATION`. Antes de usar esa autorización, evalué el efecto
real, como manda `AGENTS.md`, y **el resultado fue no proceder con la carga**.

Esto no es cautela formal. Está medido:

```
$ sudo fuser -v /dev/dri/card0 /dev/dri/renderD128
/dev/dri/card0:    lucas  1757  kwin_wayland
                   lucas  1859  Xwayland
/dev/dri/renderD128: lucas 1757  kwin_wayland

$ loginctl show-session 3 -p Type -p Active -p Remote
Type=wayland   Active=yes   Remote=no
```

**Hay una sesión gráfica tuya activa sobre esta GPU, ahora mismo.** Cargar
`rx550_drv.ko` provoke un reset de GPU, y un reset en medio de `kwin_wayland` te
tira el escritorio. Eso no lo puedo revertir y no es el riesgo que la
autorización cubría: la autorización cubría "escribir en la GPU", no "cortar la
sesión de quien me autorizó".

Con la GPU tomada por el compositor, los clocks dan `EBUSY` por dos vías
independientes:

```
$ runtime_obs.py module
power_dpm_force_performance_level  <EBUSY: el driver tiene el recurso tomado>
```

`gpu_recovery = -1` (auto) y `panic_on_oops = 0`. Un hang del driver propio no
haría panic: dejaría el sistema colgado sin auto-recuperación, que es el peor
escenario posible con un escritorio en uso.

**Lo que sí hice con la autorización**: capturar el estado base que el gate P0
exige antes de cualquier experimento (§1 "Identidad y estado base"), que es
requisito previo y no el experimento mismo. Ninguna escritura en la GPU.

## Estado base, capturado

| Campo | Valor observado | Método | Limitación |
|---|---|---|---|
| Módulo cargado | `amdgpu 18698240 5` (5 referencias) | `lsmod` | módulo del kernel del host, no el propio |
| Driver propio | `04-IMPLEMENTACION/rx550-driver/rx550_drv.ko` | `find` | existe compilado; **nunca cargado** |
| `gpu_recovery` | `-1` (auto) | sysfs | reset automático activo; reset con driver propio sin validar |
| `panic_on_oops` | `0` | `/proc/sys` | un hang no entra en panic |
| `VM_INVALIDATE_RESPONSE` | `NO_OBSERVED` en corpus | `017 §5` | nadie ha leído el valor observando |
| VRAM total | `2147483648` (2 GiB) | sysfs `mem_info_vram_total` | coherente con el log de arranque |
| VRAM usada | `5439488` (5.4 MiB) | sysfs | incluye la sesión gráfica activa |
| VRAM visible | `268435456` (256 MiB) | sysfs | BAR visible, coherente con `BAR=256M` |
| Clocks | `EBUSY` en `pp_dpm_sclk`, `pp_dpm_mclk` | sysfs | **el compositor tiene el recurso** |
| Sesión gráfica | Wayland activa, `Remote=no` | `loginctl` | no es SSH; hay consola local |

Los tres últimos de la columna de VRAM y los clocks son el dato que hace la
decisión inevitable: **no se puede medir el estado de la MMU con el compositor
usando la GPU**, ni siquiera en lectura, para los registros que el driver tiene
tomados.

## Qué haría falta para proceder, y por qué no lo hago

El discriminante de `017 §5` es:

```
escribir un PM4 WAIT_REG_MEM always y un RREG32 de REQUEST entre IBs,
con un VMID cuyo invalidate se retrase artificialmente
```

Eso **exige** escribir en un ring, lo que exige cargar el módulo, lo que exige
resetear la GPU mientras el compositor está encima. No hay versión de sólo
lectura de este experimento: la pregunta es qué hace el hardware *durante* una
secuencia, y eso hay que ejecutarla.

Las condiciones que harían el experimento aceptable, y que son verificables:

1. Sesión gráfica cerrada (`loginctl terminate-session 3`), compositor parado.
2. `kwin_wayland` y `Xwayland` sin fds sobre `/dev/dri/*`.
3. Idealmente `panic_on_oops=1` para que un hang entre en panic en vez de
   colgarse, o una ventana de recuperación fuera de esta sesión.
4. Reinicio tras la prueba, con el módulo del host restaurado.

Eso lo tiene que decidir quien está delante de la máquina, no un proceso
autónomo. Preparar el procedimiento por escrito sí es trabajo que puedo hacer, y
es lo que queda registrado en `017 §5` y en esta nota.

## Lo que este documento NO cierra

| Afirmación | Estado |
|---|---|
| Que la carga del driver propio rompería la sesión | `PROVEN` (fuser + loginctl) |
| El estado base exigido por el gate P0 | `PROVEN` (capturado) |
| Que `F1` requiere escribir en un ring | `PROVEN` (`017 §5`) |
| Que `F1` se pueda hacer sin reset | `REFUTED` |
| El intervalo `0x20` en hardware | `NOT_DETERMINED`, sin cambio |
| Trigger hardware de `FUNCTION=always` | `NOT_DETERMINED`, sin cambio |

`F1` sigue `NOT_DETERMINED`. Lo que cambia es que la autorización dejó de ser el
bloqueo, y ahora el bloqueo es **condición de sesión**, que es verificable y
resoluble cerrando el escritorio.

## Procedencia

- `RUNTIME_READ_ONLY`: `lsmod`, sysfs, `/proc/sys`, `loginctl`, `fuser`. Sin
  escrituras, sin `insmod`, sin ioctl de escritura, sin tocar la GPU.
- Se usó `runtime_obs.py` de otra sesión en vez de construir otra herramienta de
  lectura: ya hacía lo necesario, y `AGENTS.md` pide componer antes de crear.
- `rx550_drv.ko` **no se cargó**. La GPU no se modificó.
- Se respetó `COORDINACION.md:184`: el gate P0 y `017` son de otras sesiones y
  no se reescribieron; esto los informa.