# 1085 — la contradicción del enlace PCIe estaba resuelta desde el arranque, en una línea que el proyecto no había leído

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN-VALIDITY
CLASSIFICATION=RESOLUCION-DE-CONTRADICCION · TRACK=ESTATIC+KERNEL-LOG
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=09-POWER-CLOCKS/CURRENT-STATE.md  E-PWR-010  (OPEN CONTRADICTION -> RESUELTA)
         09-POWER-CLOCKS/CURRENT-STATE.md  E-PWR-011  (boot_vga=0 -> REFUTADO)
ORIGEN=09-POWER-CLOCKS/CURRENT-STATE.md §7 ("must be resolved before any
       bandwidth-bound conclusion") y el §58 [02] de mi turno
ESTADO=PROBADO · E-PWR-010 RESUELTA · E-PWR-011 CORREGIDA
GPU=INTACTA · solo lectura de sysfs y journal · sin sudo · sin escribir hardware
```

## 0 · La línea que lo resuelve

```
pci 0000:01:00.0: 16.000 Gb/s available PCIe bandwidth, limited by 5.0 GT/s PCIe x4 link
                  at 0000:00:01.0 (capable of 63.008 Gb/s with 8.0 GT/s PCIe x8 link)
```

**El kernel escribió las tres respuestas al arrancar, y el proyecto tenía la línea
en su propio `journal` sin haberla buscado.** La descomposición:

| lo que dice el log | lo que resuelve |
|---|---|
| `capable of 63.008 Gb/s with 8.0 GT/s PCIe x8 link` | **la tarjeta es x8**, y es `max_link_width=8` de sysfs. El `x16` de `pp_dpm_pcie` es inalcanzable |
| `limited by 5.0 GT/s PCIe x4 link` | **lo negociado es x4**: downtrain real y en régimen permanente |
| `at 0000:00:01.0` | el puerto raíz **no es `00:00.0`** sino `00:01.0` — y por eso mi primer script no encontraba la capacidad PCIe |

## 1 · LAS TRES EXPLICACIONES, ADJUDICADAS

`E-PWR-010` las dejó como candidatas sin discriminar. El estado real:

| # | explicación | veredicto | por qué |
|---|---|---|---|
| 1 | D3hot/downtrain hace que LNKSTA reporte `4`: es artefacto de suspensión | **REFUTADA** | el x4 se negoció **a las 16:08:14**, antes de cualquier lectura mía. Y medí que `LNKSTA` **en vivo lee 0/0** mientras sysfs lee `x4` (§2) |
| 2 | el slot es mecánicamente x8 y hay un x4 real | **CONFIRMADA** | ambos extremos soportan x8 y se negocia x4. El kernel cuantifica el coste |
| 3 | la tabla DPM declara x16 y hay que limitarlo | **CONSECUENCIA, no causa** | es cierto que el x16 es inalcanzable, pero **porque la tarjeta es x8**, no por la capa de enlace. No es una causa independiente |

**Y el coste, que era lo que faltaba para cualquier conclusión sobre ancho de banda:**

```text
disponible   16.000 Gb/s
potencial    63.008 Gb/s
deficit      3.94x          <- el ancho de banda PCIe de esta RX550 es un 25 % del posible
```

Esto **desbloquea las conclusiones de ancho de banda del proyecto**, que
`E-PWR-010` bloqueaba explícitamente. Con 3.94× menos enlace, cualquier techo
medido no es atribuible a la memoria ni a la ALU sin descontar esto primero.

## 2 · LA MEDICIÓN QUE CONFIRMA EL REFUT, Y MIS ERRORES DE RUTA

Intenté hacerlo por config space. **Dos fallos míos, y los dos importan:**

```
$ wc -c .../0000:01:00.0/config
64                       <- solo 64 bytes
$ lspci -vv
Capabilities: <access denied>          sin sudo
```

**El config space expuesto por sysfs está truncado a 64 bytes**, así que el puntero
de capacidad `0x34 -> 0x48` **cae fuera de la ventana** y `LNKCAP` —justo el ancho
máximo de la tarjeta, la observable que discriminaba— es **ilegible**. `dmesg` da
`Operación no permitida`. Las tres vías que yo probé fallan.

Lo que sí funciona, y que **no había probado**:

```text
LNKSTA (0x12)  velocidad=0  ancho=0        <- el enlace está CAÍDO
LNKCTL (0x14)  speed=0 width=0 ASPMctl=0  <- el kernel NO programa ningún clamp
runtime_status = suspended
sysfs current_link_speed/width = 5.0 GT/s x4
```

**Dos observables de "lo mismo" discrepando, y la que lee hardware discrepa.** Eso es
lo que refuta la explicación 1 por una vía independiente del log: sysfs
`current_link_*` **no lee LNKSTA**, devuelve el valor cacheado en `pci_dev`, que
persiste a través de la suspensión. El `x4` nunca fue una lectura viva.

Y **`LNKCTL = 0`** significa que el kernel **no está limitando el enlace**: el x4 es
lo que el hardware negoció, no una imposicion impuesto.

## 3 · SEGUNDA CORRECCIÓN: `boot_vga` NO ES 0

`E-PWR-011` afirma, y el proyecto lo viene usando como tranquilizador para trabajar sin
riesgo:

> *Since `boot_vga=0`, the RX550 drives no display: **all GPU load must be headless***

**`boot_vga` es `1`.**

```text
0000:00:02.0  (Intel iGPU)  ->  atributo boot_vga AUSENTE (no es 0: no existe)
0000:01:00.0  (RX550)       ->  boot_vga = 1
```

**La conclusión sobrevive, pero por otra razón, y la razón buena es más fuerte:**

| observable | valor | qué dice |
|---|---|---|
| `/sys/class/graphics/fb0/name` | **`i915drmfb`**, 1366×768 | el framebuffer de consola es de la **Intel** |
| `fb0/uevent DEVNAME` | `fb0` | y es el **único** `fb*` del sistema |
| `01:00.0/drm` | `card1 controlD65 renderD129` | la RX550 **no tiene nodo de framebuffer** |
| `card1` conectores | `DVI-D-1`, `HDMI-A-2` | está **conectada** a algo |
| log | `vgaarb: setting as boot VGA device` (RX550) | el arbiter VGA legacy eligió la RX550 |

**`boot_vga=1` y "la RX550 no conduce la consola" son las dos cosas a la vez**, y no se
contradicen: `boot_vga` refleja la elección del **arbiter VGA legacy**, y el log
también dice `fbcon: Taking over console` sobre `i915drmfb`. No hay contradicción;
lo que había era un **motivo equivocado**.

### 2 bis · Y un hecho de seguridad que `boot_vga=0` ocultaba

```
pci 0000:01:00.0: vgaarb: VGA device added: decodes=io+mem, owns=io+mem, locks=none
```

**La RX550 es propietaria del rango VGA legacy** — puertos de entrada/salida y memoria
— aunque no tenga framebuffer y la consola esté en la Intel. Con `boot_vga=0` eso
no se habría visto. **Cualquier acción futura que toque el rango VGA legacy choca con
esta tarjeta**, y `renderD129` (0666) no cubre eso. `E-PWR-011` da por bueno el
render node y no menciona el arbiter.

## 4 · LO QUE ESTO DESBLOQUEA Y LO QUE NO

**Desbloquea:** cualquier afirmación sobre techo de ancho de banda PCIe, porque el
denominador ya está medido (3.94×). También devuelve a PROVEN la línea del
propio `CURRENT-STATE` que decía *"must be resolved before any bandwidth-bound
conclusion"*.

**No desbloquea, y sigue abierto:**

- **`pp_table`: 778 bytes sin decodificar.** Es `SMU_TABLE_DPMCLKPOWRESET` de
  Arcturus, y contiene la **tabla de V/F y los niveles de power reales**, que es
  exactamente lo que haría falta para el §7 `DERIVED` de un punto único. `E-PWR-007`
  tiene **un solo punto** (214 MHz @ 687 mV) y no puede ser curva.
- **El estado `COMPUTE` vs `3D_FULL_SCREEN`** (`E-PWR-008`): las unidades de los
  campos de histéresis siguen sin establecer, y es la arista `WORKLOAD → CLOCK` del
  modelo causal.
- **La causa del downtrain.** *Que* hay x4 está `PROVEN`. *Por qué* —contacto, slot,
  placa base, BIOS— no: y esa es la pregunta que decide si es arreglable.

## 5 · PROCEDENCIA

```text
journalctl -k --no-pager | grep 'limited by'        <- la linea que resuelve E-PWR-010
journalctl -k --no-pager | grep 'boot VGA'         <- refuta E-PWR-011
sysfs  current_link_speed / current_link_width      5.0 GT/s x4 (cacheado)
sysfs  runtime_status                               suspended
config 0x12 LNKSTA                                  0/0   (enlace caido, en vivo)
config 0x14 LNKCTL                                  todo 0 (sin clamp)
config ventana                                      64 bytes -> LNKCAP ilegible
sysfs  /sys/module/pcie_aspm/parameters/policy      [default] performance powersave powersupersave
sysfs  /sys/class/graphics/fb0/name                 i915drmfb 1366x768
sysfs  01:00.0/boot_vga                             1
intervencion  NINGUNA.  Solo lectura.  Sin sudo.  GPU intacta.  No se ha cargado la GPU.
```

**Lo que este documento NO prueba.** No prueba **por qué** el enlace negoció x4: que
sea un downtrain es `PROVEN`, su causa es `NOT_DETERMINED`. No prueba que el log del
arranque de hoy describa el enlace de ahora con la misma negotiated si algo cambió
desde las 16:08 — solo que la línea se emitió en el arranque y que la lectura en vivo
de LNKSTA coincide con ella (enlace caído). No he tocado la GPU, no he cargado nada,
no he medido rendimiento. Y `boot_vga` ausente en la Intel **no es `0`**: es que el
atributo no existe, que son cosas distintas.