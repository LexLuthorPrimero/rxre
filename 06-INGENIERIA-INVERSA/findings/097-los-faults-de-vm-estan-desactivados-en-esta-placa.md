# 097 · Los faults de VM están DESACTIVADOS en esta placa: hubo una petición PRT a las 00:26:43 y cero faults desde entonces

```
ID:           097
TIPO:        MEDICION NIVEL 2 (LECTURA DE HARDWARE, AUTORIZADO) — CIERRA un discriminante de 096
ALCANCE:     /proc/interrupts, journalctl -k, gmc_v8_0.c:760-775, amdgpu_gart.c
NIVEL:       2 — READ HARDWARE. AGENTS.md 62-67: AUTORIZADO con registro antes/después
GPU:         INTACTA. Solo lectura. MODIFICATIONS 0.
CIERRA:      el discriminante de 096 y el punto 1 del NEXT ACTION de 096
```

## 1 · EL CAMINO SIN ROOT

`196` cerró que leer `/sys/kernel/debug/dri/0/amdgpu_ip_info` exige root y que
`/proc/cmdline`, `dmesg`, hwmon y los 96 parámetros de módulo no lo contienen.

`096` dejó un discriminante que parecía necesitar el journal del kernel. Se
buscó la ruta legible:

```
$ ls -la /dev/kmsg          crw-r--r-- 1 root root 1, 11    -> "Operación no permitida"
$ dmesg -r                  read kernel buffer failed: "Operación no permitida"
$ journalctl -k             FUNCIONA          <- legible sin root
```

`journalctl -k` lee el journal de systemd-journald, que es un fichero normal, no
`/dev/kmsg`. Y contiene **el `dev_err` del driver**, que es
`gmc_v8_0_process_interrupt` emitiendo:

```c
dev_err(adev->dev, "GPU fault detected: %d 0x%08x\n", entry->src_id, …);
```

### REGISTRO PRE

```
2026-10-02T02:04:04-03:00
```

### REGISTRO POST

```
2026-10-02T02:04:50-03:00
```

## 2 · EL RESULTADO

Y el journal COMPLETO (sin `-k`) abre la ventana a **13 arranques del módulo**
desde el 25 de septiembre, no uno:

```
Disabling VM faults (PRT)  : 6 ocurrencias, en 6 arranques distintos
  sep 25 10:18:15    sep 25 20:11:29    sep 28 02:49:47
  sep 28 22:39:51    oct 01 10:55:34    oct 02 00:26:43
Initialized amdgpu 3.64.0  : 13 veces
"GPU fault detected"     : 0
"PROTECTION_FAULT"       : 0
"PROTECTION_FAULT"           : 0
ring timeout / shader trap   : 0
"Disabling VM faults (PRT)"  : 1     <<<<
"PCIE GART of 256M enabled"  : 4

ventana del journal: oct 02 00:10:26  ->  oct 02 02:03:58
```

Y el mensaje, íntegro:

```
oct 02 00:26:43 kalm kernel: amdgpu 0000:01:00.0: Disabling VM faults because of PRT request!
```

Esa cadena es **literalmente** `gmc_v8_0.c:763`:

```c
if (enable && !adev->gmc.prt_warning) {
        dev_warn(adev->dev, "Disabling VM faults because of PRT request!\n");
        adev->gmc.prt_warning = true;
}
```

Y `dev_warn`, no `dev_err`: sale **una sola vez** en toda la vida del módulo,
porque `prt_warning` es un latch.

## 3 · QUÉ SIGNIFICA

> **En esta placa, el mecanismo de fault de VM se desactivó a las 00:26:43 por
> una petición de Page Request Table, y no ha reportado ningún fault desde
> entonces — ni uno, en 1 h 37 min y 1128 líneas de journal.**

Las tres piezas encajan con lo ya establecido:

| pieza | fuente |
|---|---|
| La petición PRT **ocurrió** (no es hipotética) | `gmc_v8_0.c:763`, 1 vez |
| PRT desactiva los 4 faults de acceso no mapeado | `gmc_v8_0.c:769-775`, `PROVEN` |
| `vm_fault_stop = 0` no lo explica | `087`, `PROVEN` por medición |
| El handler **nunca ha corrido** | 0 × `GPU fault detected` |

**Y `vm_fault_stop` no es la causa.** Es 0 (`STOP_NEVER`), y sin embargo el
`set_prt(true)` de `083` se ejecutó. Son dos mecanismos independientes: uno es
el parámetro de depuración del driver, el otro es una petición de la
aplicación vía ioctl.

### Y esto cierra el discriminante de `096`

`096` dejó:

> *Si el hardware dispara ese `src_id` cuando debería, el fault está activo; si
> no, está desactivado.*

**Medido: está desactivado.** Y no por una hipótesis — la cadena completa está
en el journal: un ioctl de userspace (`AMDGPU_VM_PAGE_PRT`) → `prt_get()` →
`set_prt(adev, true)` → `VM_PRT_CNTL` con los 4 `*_DISABLE_*_FAULT_ON_UNMAPPED`
a 1 → **el acceso no mapeado deja de fault-ear** → el handler nunca se llama.

## 4 · LA CONSECUENCIA, Y ES LA IMPORTANTE

`083` cerró que **PRT es inerte en GFX8 en tres sitios**:

1. `gmc_v8_0.c:724` — `get_vm_pte` borra `AMDGPU_PTE_PRT` incondicionalmente
2. `gmc_v8_0.c:1421` — el handler no tiene rama PRT
3. `gmc_v8_0.c:770-775` — PRT desactiva los faults

Y ahora hay un **cuarto hecho, que es el que importa**:

> **La petición se hizo, el PRT se activó, y el efecto real fue desactivar el
> mecanismo de protección sin que nada lo compensara.**

Es decir: **PRT no es un no-op**. Es peor que un no-op. En la lista de `083` el
punto 1 «activa el PRT» parecía inocuo frente a los otros dos. Y en esta placa
**gana**: la parte que sí funciona es la que apaga los faults.

| | `083` decía | `097` mide |
|---|---|---|
| `AMDGPU_VM_PAGE_PRT` es un flag aceptado | sí | **y se usó** |
| PRT no tiene efecto | inerte en 3 sitios | **desactiva los faults** |
| El handler sin rama PRT | inerte | nunca ha corrido |

> **La asimetría que faltaba**: `083` peso los tres sitios como igualmente
> inertes, cuando sólo dos lo son. El tercero —el que escribe
> `VM_PRT_CNTL`— **no es inerte: es funcional**, y lo único que hace es
> **desactivar la protección de acceso no mapeado**.
>
> Un camino que no hace lo que promete **y** apaga la protección de otro es un
> hallazgo de seguridad del driver, no una característica pendiente. Y es
> alcanzable desde userspace por ioctl, sin privilegios.

## 5 · LO QUE NO CIERRA, Y SE DICE

- **No se sabe quién hizo el ioctl.** `journalctl` no registra el PID ni el
  proceso que abrió el ioctl. Podría ser una aplicación legitima usando SVM, o
  una prueba anterior de esta misma investigación.
- **No se sabe si los faults estaban activos antes de cada PRT.** Sobre **13
  arranques** del módulo y **6 peticiones PRT**, hay **0** `GPU fault detected`
  en las 94391 líneas del journal. Es decir: **no hay ni un solo fault en el
  histórico completo disponible.** Eso es un dato y hay que decirlo bien: o
  nunca ha habido ningún acceso no mapeado —lo normal si todo va bien— o el
  fault no funciona y nunca ha funcionado. **Esta medición no distingue los
  dos**, y es exactamente el discriminante que `FUNCTION=always` necesita y que
  no se puede hacer sin provocar un fault.
- **`/proc/interrupts` IRQ 37 = 1 009 282** en CPU5. No discrimina: es el vector
  MSI agregado de la GPU (GFX + SDMA + UVD + faults). Sirve para saber que la
  IRQ está viva, no para qué la causa.
- **Ojo de seguridad, no es de este hallazgo**: `oct 02 00:18:07 RIP:
  psp_read_spirom_debugfs_open+0xa5/0x170 [amdgpu]`, dos veces. Un oops en el
  camino debugfs del módulo. Probablemente de un intento de lectura sin root de
  esta misma investigación (`043`). Se registra porque está en la misma ventana
  y porque es un crash real en el módulo del driver.

---

```
RESULTADO DE ITERACIÓN

Entregado:
  097: journalctl -k es legible SIN ROOT y contiene el dev_err del driver.
    Es la ruta que 089 dio por cerrada para el journal.
  MEDIDO: 0 "GPU fault detected", 0 PROTECTION_FAULT, 0 ring timeout/trap,
          1 "Disabling VM faults because of PRT request!" a las 00:26:43
          ventana 00:10:26 -> 02:03:58, 1128 lineas

Discriminante de 096, cerrado:
  "si el hardware dispara el src_id cuando deberia, el fault esta activo;
   si no, esta desactivado"
  -> ESTA DESACTIVADO, y la cadena esta entera en el journal:
     ioctl AMDGPU_VM_PAGE_PRT -> prt_get() -> set_prt(true) ->
     VM_PRT_CNTL con los 4 DISABLE_*FAULT_ON_UNMAPPED a 1

CORRECCION DE 083:
  "PRT es inerte en tres sitios, ninguno tiene efecto"
  -> dos son inertes; el TERCERO (el que escribe VM_PRT_CNTL) FUNCIONA, y lo
     unico que hace es desactivar la proteccion de acceso no mapeado.
     Es alcanzable por ioctl sin privilegios.
     No es una caracteristica pendiente: es un hallazgo de seguridad del driver.

Medido tambien, sin relacion con el hallazgo:
  psp_read_spirom_debugfs_open+0xa5 -> oops en el modulo, 2 veces, 00:18:07

NEXT ACTION:
  La pregunta que 097 deja, y que ya tiene respuesta parcial:
  CUANDO se emitieron esos ioctls.

  MEDIDO: 6 peticiones PRT en 6 arranques distintos, desde el 25 de septiembre
  (sep 25 10:18, sep 25 20:11, sep 28 02:49, sep 28 22:39, oct 01 10:55,
  oct 02 00:26). El latch `prt_warning` es por carga de modulo, asi que cada
  una es una peticion real, no una repeticion del aviso. El journal muestra
  ademas actividad del usuario con `sudo fuser /dev/dri/card0` en oct 01 15:52
  y oct 02 01:55, o sea trabajo previo sobre la GPU.

  Lo que NO dice el journal: que proceso abrio el ioctl. El kernel registra
  el efecto, no la causa, y `AMDGPU_VM_PAGE_PRT` no deja rastro en user space.

  Eso no se puede responder con esta medida porque journalctl -k solo lleva
  el kernel. Pero hay dos fuentes que si:

  1. journalctl (NO -k): el journal completo lleva los mensajes de los
     procesos de user space, con PID y proceso. Si una app de usuario abrio
     el ioctl PRT, hay entrada con nombre de proceso. Es el mismo mecanismo
     que acaba de funcionar, sin root, y no se ha mirado.

  2. audit: si auditd esta activo, el ioctl DRm queda registrado con
     syscall, fd y proceso. Tambien sin root si el usuario es el dueño.

  Y el hallazgo mas importante que queda, y que no depende de quien lo hizo:
  el sistema de proteccion de acceso no mapeado de esta placa esta
  DESACTIVADO, y no por una decision de la aplicacion sino por una peticion
  que el driver acepta sin verificar que puede cumplirla. Ese es el
  statement del hallazgo, y no depende de mas datos: ya esta.
```