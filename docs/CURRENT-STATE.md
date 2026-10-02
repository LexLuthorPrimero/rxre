# CURRENT-STATE — sólo lo verificable hoy

> Este fichero contiene **únicamente** el estado actual comprobado. Nada histórico,
> nada proyectado, nada "`debería ser`".
> Cada valor lleva `OLD → NEW` cuando cambió, con evidencia y fecha, según §7.
> `LAST_VERIFIED: 2026-10-02 - revkit/` · método: lectura de artefactos + read-only + git log.

## 0 · Cambio de esta ronda: hay acceso root al debugfs

Lo que antes era `BLOCKED_BY_AUTHORIZATION` dejó de serlo. **Con acceso root
se lee el debugfs de amdgpu en `/sys/kernel/debug/dri/0000:01:00.0`**, y de ahí
salieron las filas EV-14 a EV-24 de `EVIDENCE-MATRIX.md`.

Tres cosas que cambió y que conviene tener presentes:

| antes | ahora |
|---|---|
| VBIOS: `BLOCKED_BY_AUTHORIZATION` | leído y validado, 58880 B (EV-14) |
| PTE reales: sin observador | `NOT_AVAILABLE` **por debugfs**: `amdgpu_vm_info` en 7.1.3 solo lista BOs, `amdgpu_gart` no existe |
| `/sys/module/amdgpu/parameters/*`: ilegible | legible |

**Lo que sigue bloqueado o ausente**, sin cambios:

- `amdgpu_iomem` da `EPERM` **incluso con root**. `NOT_AVAILABLE`.
- `amdgpu_regs*` no se lee: 2 de 3 reinicios del servidor correlacionaron
  con su lectura. Es una correlación, no una causa demostrada.
- `amdgpu_sensors` da `EINVAL` al leer: no está en la lista de nodos de
  este kernel.

**Herramienta nueva asociada**: `revkit/` (20 herramientas, 32 validaciones
en `check.sh`, todas verdes). Los controles de la sesión están en
`cn7.py` (19) y `cn8.py` (12), con casos negativos por mutación real.

**Corpus**: `huerfanos.py` mide que el corpus cubre el 89 % de los símbolos
que el driver usa. 296 de 2608 se usan sin definición local. No es una
lista de fallos del driver: `amdgpu_bo.c` no está, y `amdgpu_bo_reserve`
se usa 228 veces (EV-24).

## 1 · Host

| Dato | Valor | Cómo se obtuvo | Fecha |
|---|---|---|---|
| Distro | Nobara Linux 44 (KDE Plasma Desktop Edition) | `/etc/os-release` | 2026-10-01 |
| Kernel | `7.1.3-200.nobara.fc44.x86_64` | `uname -r` | 2026-10-01 |
| Mesa | `26.2.3` | `glxinfo -B` → `OpenGL version string: 4.6 … Mesa 26.2.3` | 2026-10-01 |
| `spirv-val` | **instalado**, `/usr/bin/spirv-val` | `which` | 2026-10-01 |
| `glslangValidator` | **instalado**, `/usr/bin/glslangValidator` | `which` | 2026-10-01 |
| `strace` | `NOT_AVAILABLE` | declarado en `CHANGELOG.md`; no instalado | — |
| `ctags` | Universal Ctags 6.2.1, `/usr/bin/ctags` | `semref engines` | 2026-10-01 |
| Coccinelle | **`NOT_AVAILABLE`** — vivía en `/tmp/opencode/tools`, ese directorio no existe | `semref engines` | 2026-10-01 |

### El árbol se movió durante esta ronda

```
HEAD al empezar     ce88b5f  (022)
HEAD al terminar    ceb4d52
COMMITS NUEVOS      5fa4826 (026-pte) · fc11d1e (027-ptba) · 80fbd9e (028-fence) ·
                    f768a4f (030-wb) · 13f1b13 (031-rptr/wptr)
                    más 024-pm4dw, 025-vm-flush, 026-frame, 029-release-mem sin commitear
CONSECUENCIA        nueve hallazgos aparecieron mientras se redactaba esta documentación.
                    Ya están incorporados. Lo que venga después, no
COMPROBAR AL RELEER git log --oneline -1
```

### Transiciones de host registradas

```
2026-09-25 → 2026-10-01   distro    Nobara Linux 43 → 44
2026-09-25 → 2026-10-01   kernel    6.18.2-200.nobara.fc43 → 7.1.3-200.nobara.fc44
2026-09-25 → 2026-10-01   mesa      25.3.2 → 26.2.3
2026-09-25 → 2026-10-01   drm node  card2 → card1      (renderD129 y hwmon1 no cambian)
           EVIDENCIA      uname -r, glxinfo -B, readlink /sys/class/drm/card*/device
           RAZÓN          el host se actualizó entre la captura del 2026-09-25 y esta.
           IMPACTO        toda cifra de README.md:13-16 que nombre versión o nodo de DRM
                          está obsoleta. La salida de `validate_rx550_final.py` es la que
                          manda ahora, no el README.
```

## 2 · GPU

```
PCI          01:00.0 VGA compatible controller [0300]
             Advanced Micro Devices Lexa PRO [Radeon 540/540X/550/550X / RX 540X/550/550X]
             [1002:699f] (rev c7)
drm          card1 · renderD129          (DRIVER=amdgpu, PCI_SLOT_NAME=0000:01:00.0)
hwmon        hwmon1 → name "amdgpu"
             hwmon0 = acpitz · hwmon2 = coretemp
             <-- el índice hwmon1 que dice README.md:16 sigue siendo correcto por casualidad
VRAM total   2147483648 B   (2.0 GiB)   /sys/class/drm/card1/device/mem_info_vram_total
VRAM visible 268435456 B  (256 MiB)      /sys/class/drm/card1/device/mem_info_vis_vram_total
GTT total    6194642944 B                /sys/class/drm/card1/device/mem_info_gtt_total
BAR0         268435456 B                 stat /sys/bus/pci/devices/0000:01:00.0/resource0
```

`lspci -v` confirma la BAR: `Memory at e0000000 (64-bit, prefetchable) [size=256M]`.

**Consecuencia**: `vram_full_visible` es `FALSE` (256 MiB visibles contra 2 GiB de
VRAM), luego el writer CPU de page tables es inalcanzable bajo la política efectiva.
Ver `025` §evidencia y `023-pte` §CUDA.

### Parámetros de módulo

```
/sys/module/amdgpu/parameters/vm_size           = -1
/sys/module/amdgpu/parameters/vm_fragment_size  = -1
/sys/module/amdgpu/parameters/vm_block_size     = -1
/sys/module/amdgpu/parameters/vm_update_mode    = -1
```

Los cuatro en `-1` = rama automática. Esto **elimina** la vía de falsificación (a) de
`024` §9: `vm_size = 64 GB` no depende de que nadie haya forzado un parámetro.

## 3 · iGPU

```
0000:00:02.0   Intel HD Graphics 4600 (HSW GT2) [8086:0412]
drm            card0 · renderD128   (DRIVER=i915)
```

La pantalla va por la iGPU. La RX550 es GPU secundaria sin salida de vídeo — decisión
deliberada de seguridad que sostiene todo el resto: perder la sesión gráfica no exige
tirar la RX550.

## 4 · Estado de la GPU — la afirmación más importante de este fichero

```
GPU_TOUCHED     NO
MODULE_LOADED   NO  (nhwa NO cargado; ningún módulo rx550 cargado)
PROBE_ACTIVE    NO
STAGING         sin entrada de driver's own en el árbol
MODIFICATIONS   0  en el corpus
WRITE_EXECUTION NONE
```

Comprobado:

```console
$ grep -iE "amdgpu|nhwa|rx550" /proc/modules
amdgpu 18698240 5 - Live 0x0000000000000000
amdxcp 12288 1 amdgpu, Live …
drm_ttm_helper … amdgpu …          <-- los únicos nhwa/rx550: ninguno

$ lsmod | grep -iE "nhwa|rx550"
(nhawa/rx550 NOT loaded)
```

Existen binarios **construidos pero no cargados** en disco: `rx550_drv.ko`,
`rx550.ko`, `rx550_pciid.ko`, `nhwa.ko`. `MODULES_ORDER` ≠ `LOADED`.

**No confundir** con la línea B, donde el shader Vulkan **sí** se ejecutó en la RX550
el 2026-09-29. Eso fue un workload de usuario vía RADV, no una toma de control del
driver. La diferencia importa y ningún documento del repo la hace explícita.

## 5 · Estado del driver propio

```
STAGE1   dos .ko construidos:
           rx550_drv.ko    SI es driver PCI  (verificado por nm: __pci_register_driver,
                                               pci_enable_device, d rx550_pci_driver)
           rx550.ko        NO es driver PCI  (0 símbolos pci) — es char device
           rx550_pciid.ko  SI es driver PCI, sólo filtra el ID
         check-drivers: cada comprobación tiene control negativo; sin él "no encontré X"
         y "no hay X" serían la misma frase
CARGADO  ninguno
ENVIADO  ninguno
```

`07-DRIVER/kernel/Makefile` documenta en el propio comentario por qué `rx550.ko` se
mantiene: para que su código no se pudra, y porque `rx550_pm4.c` tiene una suite que
depende de él. **No** es que esté en el camino principal.

## 6 · Estado del corpus

| Árbol | Estado | Identidad |
|---|---|---|
| `RESEARCH/working/linux-7.1.3/` |árbol de trabajo | == `RESEARCH/baseline/linux-7.1.3` |
| `RESEARCH/baseline/linux-7.1.3/` | congelado del tarball | `MANIFEST.sha256` |
| `RESEARCH/kernelbuild/linux-7.1.3/` | headers instalados | `include/drm/amd_asic_type.h` sha256 `cea577df…7809` |
| `rx550-upstream-7.2.8/linux-7.2.8/` | upstream prístino | `local.sha256` == `upstream.sha256` |

```
SIN PARCHES LOCALES  PROVEN.  local.sha256 == upstream.sha256 (12e8d5a9…941e).
                      RESEARCH/patches/ está vacío.
NINGUNA DIFERENCIA ENTRE 7.1.3 Y 7.2.8 EN LO QUE IMPORTA
                      gmc_v8_0.c  7.1.3 d76f4144…a0721  7.2.8 a1fc653c…8d321  (distintos)
                      gfx_v8_0.c  7.1.3 2427f5b5…404d0  7.2.8 fd1f3e4b…afa63e  (distintos)
                      PERO la rama de block_size es idéntica, y gfx8vmgeom lo cruza:
                      "7.2.8: la MISMA rama, luego no es artefacto de versión"
```

Que los `.c` tengan sha distinto **no** significa que la semántica difiera. Es la
razón por la que `gfx8vmgeom` tiene un control de cruce de versión, y por la que las
conclusiones de `020`/`023-pm4-count` (hechas sobre 7.1.3) se sostienen en 7.2.8.

## 7 · Estado documental — qué se sabe del árbol documental

```
FINDINGS         137 ficheros en 06-INGENIERIA-INVERSA/findings/
INDEX            001 010 021 023 024 025 026 027 028 029 030 031 032 033 035 036 037 038 039 040 041 042 043 056 DUPLICADOS
                 (40 colisiones)  + HUECOS en la numeración: faltan 004
TRACKED          46 de 137
UNTRACKED        91: 017-vm-invalidate · 018-execution-order · 019-atc-l2 ·
                 021-write-lock · 023-pte-productor-sdma · 024-pm4dw ·
                 025-vm-flush-path · 026-frame-completo · 027-write-multiple ·
                 028-emit-frame-size · 029-orden-validacion-fence ·
                 030-page-walker · 033-protections-opaco · 040-smu · 041-histeresis ·
                 042-at-wire-format · 043-pll-bsp
                 <-- evidencia en disco, no en git. Empeora en CADA ronda: 5 → 9 → 11 → 17 → 28 → 30 → 49-> 9 -> 11 -> 17
ENCONTRADO       00-INDICE/MASTER-RESEARCH-STATUS.md se autodenomina "punto único de
                 entrada" y tiene 0 menciones de la línea A (grep de rx550_drv,
                 STAGE1, vm-invalidate, vmflush, COND_EXEC, GEN_PTEPDE = 0)
                 -> SUPERSEDED por docs/MASTER-RESEARCH-STATUS.md, sin borrar
CERRADO HOY      PROYECTO_STATUS.md reconciliado; README.md acotado; docs/ creado
```

## 8 · Lo que sigue `UNKNOWN` y no se está estimando

Nada en este fichero rellena un hueco por inferencia. Los huecos que quedan están
enumerados con su causa en `MASTER-RESEARCH-STATUS.md §NOT_DETERMINED` (N1–N8) y
en [`OPEN-FRONTIERS.md`](OPEN-FRONTIERS.md).

Lo que **no** estádetermined ni determinable aquí:

- si el hardware GFX8 interprets `PAGE_TABLE_BLOCK_SIZE` como `block_size − 9` (N5)
- qué significa `PAGE_TABLE_DEPTH` `0` frente a `1` (N3)
- el orden de ejecución real del invalidate (N2)
- si el sampler BC3 redondea o trunca (N7 / AD-12)
- si el agreement test BC3 sigue pasando **hoy** — el registro es de 2026-09-29 y sus
  `.log` están ignorados por git (`.gitignore:78`). Acción 2 en `NEXT TECHNICAL ACTIONS`.

## 9 · Cerrojo de escritura — estado leído, no accion

```
.write-lock/            SIN owner en raíz -> la raíz no está tomada
.write-lock/findings/   PID=53801 2026-10-01T10:50:07   PID MUERTO
.write-lock/pteflags/   pid=54930 2026-10-01T10:58:56   PID MUERTO
```

Tres cosas que `COORDINACION.md` no cubre y que quedan registradas:

1. **El `owner` de la raíz desapareció durante la ronda.** Estaba
   `52756 2026-10-01T10:40:08-03:00 takeover-human; alcance=tools/` a las 11:01, y a
   las 11:02 ya no existía. Nadie lo borró desde esta sesión —esta no había escrito
   nada todavía— así que **no hay registro de quién lo liberó**. Es exactamente la
   laguna que `021-write-lock` §Evidencia ya había nombrado: "no sé cuándo ni quién
   lo liberó, y no hay registro en el árbol que lo diga".
2. **El formato de `owner` no es único.** La raíz usaba `PID <fecha> <texto>`, y el
   preflight de `COORDINACION.md:71` busca `pid=[0-9]+`, que **no aparece** en ese
   formato. Con el formato de la raíz, el preflight no puede extraer el PID y cae en
   `OWNER_NOT_RUNNING` por un motivo que no es liveness. Los subdirectorios usan un
   formato distinto (`PID=53801 …` y `… scope=pteflags pid=54930`), y sólo el segundo
   casa con el regex.
3. **`docs/` y `rootmd` los tomé yo** con PID 55320 y 56795, ambos vivos al terminar.
   `pm4dw.c` cambió a las 10:46, 10:48, 10:53 y 11:14 mientras trabajaba: hay sesión
   activa en el árbol.

Nada de lo anterior autoriza a tomar un cerrojo ajeno. `021-write-lock` §Corrección
propone exactamente el guard que falta (comprobar el ancestro antes del `mkdir`) y
dice que no lo aplica porque `COORDINACION.md` es ley operativa. Sigue sin aplicarse.
**Es la acción con más probabilidad de volver a causar daño y la más barata de
arreglar.**