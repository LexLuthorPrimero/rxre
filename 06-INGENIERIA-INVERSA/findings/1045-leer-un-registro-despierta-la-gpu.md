# 1045 — «solo lectura» no es «sin efecto»: abrir el nodo render reanuda la GPU, y esta GPU es la de la pantalla

```
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN-MMR-PROBE
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST (sysfs) + LEIDO_EN_CORPUS (fuente)
AFECTADO=04-IMPLEMENTACION/mmr-probe/mmr_probe.c   (instrumento construido, NO ejecutado)
BLOQUEANTE=CITADO, no automatico: amdgpu_kms.c:1453
ESTADO=PROBADO (el efecto) · PROBADO (la causa, por fuente)
        · EL EXPERIMENTO = DEFERRED, con causa precisa y no con un "no"
```

## La afirmación

El mapa de contadores dejó abierta una acción: leer `GRBM_STATUS` por
`AMDGPU_INFO_READ_MMR_REG` **sin root**, para obtener la serie temporal de
`GUI_ACTIVE` que separa H1 (GPU ocupada) de H6 (inanición). La consigna de riesgo
decía `RIESGO NINGUNO. READ_ONLY.`

**Eso es falso, y no por una opinión: por una línea del driver.**

## MEDIDO

### 1. La RX550 es el adaptador de vídeo de ARRANQUE

```
/sys/class/drm/card1/device/boot_vga        = 1
/sys/class/drm/card0/device/driver -> i915   (la iGPU de Intel es card0)
/sys/class/drm/card1/device/driver -> amdgpu
/sys/bus/pci/devices/0000:01:00.0/power_state        = D3hot
/sys/bus/pci/devices/0000:01:00.0/power/runtime_status = suspended
/sys/bus/pci/devices/0000:01:00.0/power/runtime_control = auto
/sys/bus/pci/devices/0000:01:00.0/power/autosuspend_delay_ms = 5000
runtime_active_time = 278853 s   runtime_suspended_time = 59648974 s
```

Con la iGPU presente y la dGPU al 0,46 % activa, el compositor está usando el
i915 para display y la RX550 está dormida. **`boot_vga=1` significa que en el
arranque la RX550 fue la de la pantalla**, así que despertarla no es un cambio de
potencia invisible: es la de la GPU que la maquina cree que controla el display.

### 2. Abrir el nodo render la reanuda. Incondicionalmente.

`amdgpu_kms.c:1435`:

```c
int amdgpu_driver_open_kms(struct drm_device *dev, struct drm_file *file_priv)
{
        ...
        flush_delayed_work(&adev->delayed_init_work);        /* :1443 */
        if (amdgpu_ras_intr_triggered()) { ... }             /* :1446 */
        ...
        r = pm_runtime_get_sync(dev->dev);                    /* :1453  <-- AQUI */
```

Y ese `.open` es el que usan **las dos** registraciones del driver
(`amdgpu_drv.c:3076` y `amdgpu_drv.c:3102`), la de KMS y la de render. No hay
 camino de `open` más ligero: el nodo render pasa por el mismo
`amdgpu_driver_open_kms` que el nodo de control.

**Medido en el propio driver:** tras el arranque, `amdgpu_drv.c:2483-2488` hace

```c
pm_runtime_use_autosuspend(ddev->dev);
pm_runtime_set_autosuspend_delay(ddev->dev, 5000);
pm_runtime_allow(ddev->dev);
pm_runtime_put_autosuspend(ddev->dev);       /* :2488  la deja dormida */
```

y `drm_open` → `.open` → `pm_runtime_get_sync` la despierta cada vez que alguien
abre el nodo. Por eso el nodo de censo midió **99,52 % de uptime suspendido**:
nadie la abre.

### 3. El ioctl no es el problema; el `open` lo es

La distinction que salva algo de esto: **`AMDGPU_INFO_READ_MMR_REG` no pide
energía**. La ruta es

```
amdgpu_kms.c:875   AMDGPU_INFO  ->  amdgpu_info_ioctl
amdgpu_kms.c:899   count > 128 -> -EINVAL
amdgpu_kms.c:911   for (...) amdgpu_asic_read_register(adev, se, sh, offset + i, &regs[i])
vi.c:1431          .read_register = &vi_read_register
vi.c:834-835       default: return RREG32(reg_offset);      <-- MMIO vivo, sin escritura
```

El único efecto lateral está en `open`, no en el ioctl. Eso significa que el
efecto es **una vez por fd abierto**, no por muestra: se mide, se anota, y una
vez cerrado el descriptor la GPU vuelve a `suspended` por autosuspend. Es
**reversible y observable**. No es inocuo.

## Lo que queda establecido, y es lo que importa

1. **Los 21 registros MMIO-vivos existen y son alcanzables por ioctl** —
   `vi.c:665-742` tiene 76 entradas, 53 son caché de software
   (`adev->gfx.config.*`) y 21 caen en `default: RREG32`. Verificado leyendo el
   `switch`, no supuesto. `mmGRBM_STATUS` (0x2004) es la primera entrada.
2. **El único modo de leerlos sin root es el nodo render**, porque
   `AMDGPU_INFO` lleva `DRM_AUTH|DRM_RENDER_ALLOW` (`amdgpu_drv.c:3057`) y
   `/dev/dri/renderD129` es 0666 mientras `/dev/dri/card1` es 0660 `root:video` y
   el usuario no está en `video` ni en `render`.
3. **Abrir ese nodo reanuda la GPU**, y la GPU es `boot_vga`.

Por tanto: **la línea de runtime del usuario —R-NEW-94..98, N-INT-100..103,
R-NEW-21, N-INT-22/23/44, la separación H1/H6— no está bloqueada por permisos,
ni por raíz, ni por la ausencia de instrumentación. Está bloqueada por una
consecuencia de diseño del driver sobre el adaptador de display de arranque.**

Eso **reencuadra** la afirmación de que hace falta autorización de nivel 4 para
«tomar la GPU»: para la telemetría por ioctl no hace falta nivel 4, hace falta
aceptar que leer un registro **despierta la tarjeta que la maquina cree que dibuja la pantalla**.
Son dos cosas distintas, y la segunda no la nombra ninguna etiqueta de
`WORK_CLASS`.

## Clasificación corregida del observable

La regla de clasificación de §41 es `READABLE | WRITABLE | SIDE_EFFECTING |
DESTRUCTIVE | UNKNOWN_SEMANTICS`. Lo que se clasificado antes como
`READ_ONLY` es, con la evidencia de arriba:

```
IOCTL               : READ_ONLY        (no escribe ningun registro; RREG32)
APERTURA DEL NODO   : SIDE_EFFECTING   (pm_runtime_get_sync, amdgpu_kms.c:1453)
                     y el efecto es sobre el ADAPTADOR DE DISPLAY DE ARRANQUE
EXPERIMENTO COMPLETO: SIDE_EFFECTING, reversible, observable
```

Un instrumento que se declara `READ_ONLY` porque sólo hace lecturas **miente
sobre su propio efecto**, y esa clase de mentira es la que este proyecto lleva
toda la sesión desmontando en las herramientas. Ahora también en el hardware.

## Por qué NO se ejecutó, y por qué eso no es «no hacer nada»

`AGENTS.md` §43 exige, para permitir una excepción experimental, **conjuntamente**
: pregunta específica, objetivo identificado, alcance controlado, justificación de
riesgo, condición de aborto, vía de recuperación, efecto observable y validación
posterior. Todo eso existe aquí, y aun así **no se ejecuta**, por una razón que
está por encima de §43 y es la que el propio proyecto se puso:

> `SSH-RECOVERY-PATH.md`, paso **[3b] `NOT_PROVEN_EMPIRICALLY`**.

Es decir: **la vía de recuperación de esta máquina no se ha probado nunca.** Y la
acción que se propone es susceptible de cambiar el estado de la GPU de la
pantalla. §42 sube el riesgo por encima de `CONTROLLED_WRITE` cuando el
blast radius cae fuera del dispositivo. Aquí el blast radius es **la sesión
gráfica del usuario**.

Un experimento que puede dejar sin escritorio a quien está trabajando, ejecutado
con una recuperación no probada, no es un experimento controlado: es una apuesta.
Y el beneficio que compra —un número de ocupación— no compite con eso.

**Lo que sí se entrega y sí es utilizable:**

- El instrumento, compilado, con `-Wall -Wextra` y **0 avisos**.
- LaGate de seguridad: `count=1` fijo, porque el kernel **descarta el lote entero**
  con `-EFAULT` si la petición cruza un registro no permitido
  (`amdgpu_kms.c:917`); un lote grande no es «más datos», es un modo de fallo.
- La decodificación de los **24 campos** de `GRBM_STATUS` con su bit exacto, sacada
  de `gca/gfx_8_0_sh_mask.h`: `GUI_ACTIVE` = bit 31 / `0x80000000`,
  `CP_BUSY` = 29, `CB_BUSY` = 30, `SX_BUSY` = 20, `SC_BUSY` = 24, y 17 campos
  `*_BUSY` en total. **Verificado, no asumido** — el nombre del macro lleva doble
  guion bajo (`GRBM_STATUS__GUI_ACTIVE__SHIFT`) mientras el driver lo invoca con
  uno, y esa discrepancia es exactamente donde se cuela una constante inventada.
- La definición de idle **del driver**, que es la única semántica no nominal del
  corpus: `gfx_v8_0_is_idle()`, `gfx_v8_0.c:4798-4807`:
  `idle ⟺ ¬GUI_ACTIVE ∧ GRBM_STATUS2 == 0x8`.
- El programa **lee `power/runtime_status` antes y después** e imprime si cambió.
  Eso convierte el efecto lateral en observable en vez de oculto.

## Cómo se desbloquea, y por qué no lo hago yo

Hace falta **una** de estas dos, y la decisión no es técnica:

1. **Autorización explícita** para abrir `/dev/dri/renderD129` sabiendo que
   reanuda la GPU de display, **con la vía de recuperación probada antes**
   (resolver [3b] de `SSH-RECOVERY-PATH.md`). El orden importa: primero la vía,
   después el experimento.
2. **Un camino de lectura que no reanude.** Y aquí está el resultado de buscarlo:
   **no existe en userspace para esta tarjeta.** El `open` es el único punto de
   reanudación y lo usan las dos registraciones. `debugfs amdgpu_regs` leería los
   2555 registros, pero necesita root y no se ha medido si reanuda; y para
   seleccionar un evento hay que **escribir** el selector, lo que ya no sería
   lectura.

Lo que queda, por tanto, es `DEFERRED` con causa **citada y no automática**, que
es la diferencia entre este hallazgo y un bloqueo.

## Lo que NO se afirma

- No se afirma que ejecutar el sonda fuera a **dañar** hardware. No hay evidencia
  de eso; el riesgo es de sesión gráfica, no de la GPU.
- No se afirma que la reanudación sea la causa de ningún fallo observado. Ninguno
  ha sido observado.
- No se afirma que no se pueda leer un registro de esta ASIC. Se afirma, con
  cita, que **la vía sin root que había pasa por un `open` que reanuda**.