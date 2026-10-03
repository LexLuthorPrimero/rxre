# HARDWARE-FINGERPRINT.md

```text
CLASSIFICATION=MEASUREMENT+REGISTRY
TRACK=RUNTIME (solo lectura) · GENERADO=2026-10-02
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
GPU INTACTA · NO SE ESCRIBIÓ EN NINGÚN REGISTRO DE HARDWARE
```

**POR QUÉ EXISTE.** El prompt maestro (§4) exige verificar el target antes de investigación
crítica, y no existía ningún artefacto con esa información: los 30+ registros de estado de la raíz
(`CURRENT-STATE.md`, `PROYECTO_STATUS.md`, `EVIDENCE-MATRIX.md`, …) describen el proyecto pero
ninguno fija la máquina. Este fichero es ese artefacto mínimo.

**REGLA DE REFRESH.** Los valores marcados `[DERIVA]` cambian entre sesiones sin que cambie el
hardware. Los marcados `[FIJO]` son propiedades de la placa y no deberían cambiar nunca.
Si un `[FIJO]` cambia, es la señal de que el target ha cambiado y hay que releer todo.

---

## 1 · Veredicto

```text
TARGET_MATCH = si
```

**Los siete campos del contrato de target (§3) están verificados y coinciden.** No procede
`TARGET_MISMATCH` ni modo inerte.

| campo §3 | declarado | medido | veredicto |
|---|---|---|---|
| CPU | Intel Core i7-4790 / Haswell | `Intel(R) Core(TM) i7-4790 CPU @ 3.60GHz` | coincide |
| GPU | AMD Radeon RX 550 | `[1002:699f]` Lexa PRO / RX 550 | coincide |
| ASIC | Polaris12 | device id `0x699f`, rev `0xc7` | coincide |
| GPU arch | GFX8 | corpuse Linux 7.1.3 + `246`/`253`/`254` sobre `smu12` | coincide |
| VRAM | ~2 GiB | 2048 MiB, base `0xF400` (log) | coincide |
| iGPU | Intel HD 4600 | `8086:0412` en `0000:00:02.0`, driver `i915` | coincide |
| RAM | 12 GiB DDR3 | 12098904 kB = 11.54 GiB | coincide |
| Board | ECS H81H3-M4 | `ECS` / `H81H3-M4` / v1.0 | coincide |
| OS | Nobara/Fedora-based | `7.1.3-200.nobara.fc44.x86_64` | coincide |

---

## 2 · HOST `[FIJO]`

```text
CPU            Intel Core i7-4790 @ 3.60GHz  (4C/8T)
BOARD_VENDOR   ECS
BOARD_NAME     H81H3-M4
BOARD_VERSION  1.0
BIOS_DATE      05/21/2015
```

## 3 · GPU `[FIJO]` — el ASIC objetivo

```text
BUS            0000:01:00.0
VENDOR:DEVICE  0x1002:0x699f        "Lexa PRO" / RX 540X/550/550X
REVISION       0xc7                 [DERIVA] el rev_id de la GPU
SUBSYS         0x1002:0x0b04
CLASS          0x030000
DRIVER         amdgpu   (enlace a /sys/bus/pci/devices/0000:01:00.0/driver)
IRQ            37
BAR0           268435456 bytes = 256 MiB   [FIJO]
```

**⇒ `PROVEN_DERIVED`. El BAR0 es de 256 MiB y concuerda con `242`, que lo dedujo del log
(`[drm] Detected VRAM RAM=2048M, BAR=256M`) y del hueco BAR5. Las dos vías son independientes:
una lee el recurso del kernel, la otra el log de arranque.** `PROVEN_DERIVED`.

**⇒ Y esa coincidencia es la que sostiene `163`: la VRAM no es full-visible por el BAR, porque
2.048 MiB de VRAM contra 256 MiB de ventana.** `PROVEN_DERIVED`.

## 4 · GPU `[DERIVA]` — estado publicado por el driver

```text
CORPUS         /home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/working/linux-7.1.3
KERNEL         7.1.3-200.nobara.fc44.x86_64        [DERIVA]
AMDGPU_KO      /lib/modules/7.1.3-200.nobara.fc44.x86_64/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst
AMDGUI_VERMAGIC 7.1.3-200.nobara.fc44.x86_64        [DERIVA]
AMDGUI_SRCVER   D68004925455E20A24C2B87            [DERIVA] cambia con cada rebuild
```

**⇒ `PROVEN_DERIVED`. El corpus `linux-7.1.3` es la versión del kernel en ejecución, no una
copia arbitraria. Eso convierte cada cita de findings en una cita sobre el código que realmente
está cargado, y es la condición para que la lectura estática valga como evidencia del
comportamiento observado.** `PROVEN_DERIVED`.

## 5 · MEMORIA `[DERIVA]`

```text
MemTotal       12098904 kB = 11.54 GiB
SwapTotal      21703148 kB = 20.70 GiB
```

**⇒ `PROVEN`. `MemTotal` ha derivado 8 kB desde la medición de `243`, que cite 12098912 kB. El
valor exacto no es estable porque los módulos del kernel reservan memoria conforme se cargan.** `PROVEN`.

**⇒ `PROVEN_DERIVED`. La conclusión de `243` es robusta a esa deriva: el rango de `MemTotal` que
produce 5.907 MiB por `MemTotal/2/1024` es 12.097.536 .. 12.099.583 kB, y tanto el valor antiguo
como el actual caen dentro. Lo que no es robusto es la cifra citada, que hay que volver a leer
antes de usarla en una cuenta.** `PROVEN_DERIVED`.

**⇒ `PROVEN`. Hay 20.70 GiB de swap en una máquina que `AGENTS.md` describe como 12 GiB. No
afecta a la investigación, pero sí a cualquier benchmark: una carga que entre en swap midiendo
rendimiento mide disco, no GPU.** `PROVEN`.

## 6 · GRAFICOS `[FIJO]`

```text
card0          0000:00:02.0   Intel HD 4600   driver=i915
                 card0-HDMI-A-1   card0-VGA-1
card1          0000:01:00.0   Lexa PRO       driver=amdgpu
                 card1-DVI-D-1     card1-HDMI-A-2
```

**⇒ `PROVEN`. `card0` es la iGPU y `card1` es la AMD. Cualquier lectura de `/sys/class/drm/card0`
es de la Intel, no del ASIC objetivo.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Ésta es la trampa de lectura más fácil de esta máquina, y por eso está en
el artefacto y no en una nota: los índices de `cardN` no coinciden con los índices del bus PCI.
`card1` es el bus `01:00.0`. Una herramienta que asuma `card0` = la primera GPU PCI mide la
Intel.** `PROVEN_DERIVED`.

**⇒ Y el corpus tiene soporte de esto: el log de `163` registra «initializing kernel modesetting
(POLARIS12 0x1002:0x699F …)» con el bus explícito, y `166` y `167`
describen dos conectores DVI y un HDMI, que es exactamente lo que muestra `card1`.** `PROVEN_DERIVED`.

## 7 · Rutas NO disponibles sin `root`

```text
/sys/bus/pci/devices/0000:01:00.0/resource{0,2,4,6}   vacíos
setpci -s 01:00.0 0x10                                sin permiso
lspci -v -s 01:00.0                                   solo da Subsystem
```

**⇒ `PROVEN_ABSENT`. El config space completo del ASIC no es legible sin privilegios. El
tamaño del BAR0 sí se obtiene sin ellos, por el inode de `resource0`, que declara
268435456 bytes.** `PROVEN_ABSENT`.

**⇒ `PROVEN_DERIVED. Consecuencia de método: para el fingerprint no hace falta root, y la vía
del inode de `resource` es preferible porque es de lectura y no de interpretación. Anotar el
tamaño del recurso desde `ls -la` es un dato; deducir el espacio de direcciones del target del
VBIOS es una inferencia, y aquí coinciden porque el target se verificó por otra vía.** `PROVEN_DERIVED`.

---

## 8 · Firmware localizable `[FIJO]`

```text
/lib/firmware/amdgpu/          677 ficheros, 23 de polaris12_*.bin.xz
PROYECTO 06-INGENIERIA-INVERSA/firmware/polaris12_smc.bin
```

**⇒ `PROVEN`. El `.bin` del proyecto y el `.xz` del sistema descomprimen a bytes idénticos
(SHA-256 `4b8eb326a7fbd391554fe50bc43cf04a917b01a806884ea324f5c3fe88a6ec77`, 130388 bytes). Es
la misma imagen, así que un análisis hecho sobre una vale para la otra.** `PROVEN`.

## 9 · Qué NO cubre este artefacto

```text
REGISTROS MMIO         requiere NIVEL 2 + debugfs; no formatea parte del target
TABLETA PM4 en vuelo   requiere workload activo; ausente en reposo
ESTADO DEL RELOJ       requiere leer mmGfxClock; 161 y 220 lo derivaron del VBIOS
TELEM                 ausente en runtime; 222 lo derivó del VBIOS
ESTADO DE VRAM RUNTIME ausente en reposo; 199/204 lo derivaron del log de arranque
```

**⇒ `NOT_AVAILABLE`. Todo lo anterior se obtuvo por derivación desde el log de arranque y el
VBIOS, no por lectura directa. Es evidencia de segundo orden respecto a lo que daría un
`debugfs` legible, y esa distinción está registrada en vez de diluida.** `NOT_AVAILABLE`.

---

## 10 · Procedimiento para refrescar

```text
1. leer  §2 a §6  con los comandos de este fichero
2. si algún [FIJO] cambió  -> TARGET_MISMATCH, releer AGENTS.md antes de continuar
3. si algún [DERIVA] cambió -> anotarlo, no es cambio de target
4. re-ejecutar el corpus-manifest: el kernel manda, no el corpus
```

**⇒ `PROVEN_DERIVED. El punto 4 es el que evita el error más caro del proyecto: trabajar
contra un corpus que no es la versión del kernel en ejecución produce findings correctos y
conclusiones que no describen la máquina.** `PROVEN_DERIVED`.