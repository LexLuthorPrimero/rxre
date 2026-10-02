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

## 0.b · Cambio de la segunda ronda de 2026-10-02

Todo lo de esta ronda sale de artefactos que **ya estaban en el árbol** y no se
habían mirado. Ni GPU, ni MMIO, ni insmod. `GPU INTACTA` · `WRITE_EXECUTION NONE`.

**Una regla de PM4, resuelta, que cambia cómo se escribe cualquier cosa**

| | |
|---|---|
| el campo `count` de un paquete PM4 cuenta el payload **menos uno** | `PROVEN_DERIVED` (EV-30) |
| emisiones de `gfx_v8_0.c` que reconcilian | **49 de 49** |
| confirmación de hardware | el test del anillo, en el anillo de **compute** |

El test del anillo (`gfx_v8_0_ring_test_ring`) reserva 3 dwords, declara `count=1`
y escribe 2 payload, y después sondea `mmSCRATCH_REG0` hasta que lea
`0xDEADBEEF`. Si el hardware leyera exactamente `count`, no se ejecutaría el
tercer dword, el test daría `ETIMEDOUT` y `sched.ready` quedaría a 0, con lo que
el anillo no se usaría nunca. El anillo de compute **está usado**.

**Un observador que se daba por inexistente**

| | |
|---|---|
| tabla GART (PA) | `0x000000F400900000`, del log de arranque |
| offset dentro de VRAM | `0x900000` = 9 MiB |
| ventana del BAR | 256 MiB |
| ¿legible por CPU? | **sí**, por `resource0` en ese offset |

F12 pasó de `NOT_AVAILABLE` a `BLOCKED_BY_CREDENTIAL`: `resource0` es root-only
y este proceso corre como uid 1000. **Es una credencial ausente, no una
capacidad ausente**, y leer el BAR es NIVEL 2 según el propio AGENTS.md.

**Direcciones del arranque, que no estaban en ninguna otra fuente**

```
VRAM (PA)   0xF400000000 .. 0xF47FFFFFFF
GART (VA)   0xFF00000000  .. 0xFF0FFFFFFF
GART        65536 páginas x 4 KiB = 256 MiB, exacto
BAR         256 MiB con RAM 2048 MiB
GTT         5907 MiB de RAM del sistema
bloque GMC  gmc_v8_1_0
```

**Y una correction al project's own state**: el ASIC instancia **`gmc_v8_1_0`**,
aunque `gfx_v8_0.c` incluye los headers `gmc_8_2`. No hay contradicción, y el
invariante del invalidate está comprobado en ambas generaciones.

**Lo que se retiró en esta ronda**, y es lo que más importa para el que lea el
log: cinco afirmaciones propias que eran falsas, entre ellas un `REFUTED` que no
se sostenía (EV-27) y una tabla que decía que `vm_flush` era una excepción
(EV-28, y era por un `grep -n` que no hice).

**La lección, cuatro veces**: el dato estaba a un comando de distancia y no se
buscó. Tres herramientas del árbol ya hacían el trabajo —`pm4census.py`,
`count_vmflush_dw.py` y `revkit/pte.py`, que es mía—, y F12 se dio por
inobservable sin abrir `journalctl -k -b`.

---

## Ronda 2026-10-02 (tarde) · EV-35 · la tabla de opcodes de `pm4dec`

**Cerrado**: la numeración de opcodes de PACKET3 **depende de la generación de
ASIC**, y la de GFX8 no sale de `sid.h` sino de `vid.h`. No es una preferencia:
`gfx_v8_0.c` incluye `vid.h` y ningún otro header de opcodes, medido sobre el
grafo de includes del corpus. `PROVEN`.

**Tres opcodes que faltaban y tres que estaban mal.** `0x49` `RELEASE_MEM`,
`0x58` `ACQUIRE_MEM` y `0x79` `SET_UCONFIG_REG` no están en `sid.h` y sí salen en
el anillo de compute capturado: ahora se nombran. Y `sid.h`, que es de SI/GCN1,
numera los tres `LOAD_*` una posición desplazada, así que nombraba mal `0x5F`,
`0x60` y `0x61`. El segundo defecto **lo introduje yo** al arreglar el primero,
mezclando los cinco headers, y lo detecté midiendo el reparto de nombres en vez
de dar por buena la primera versión que funcionaba.

**Lo que no se mueve, comprobado y no supuesto**: de los 8 opcodes que usan
`EV-21`..`EV-30`, **0 de 8** dependen de la elección de cabecera. `EV-29` y `EV-30`
intactas.

**El anillo SDMA no es PM4.** 0 de 118 cabeceras aparentes reciben nombre. Antes
`pm4dec` publicaba `paquetes : 17` como si fuera una medida. Ahora avisa, y el
aviso no sale en el anillo GFX.

**Una rama declarada y no validada**: ninguna fuente del corpus (625 ficheros,
304 `.c` + 321 `.h`) incluye más de un header de opcodes, así que la guarda de
ambigüedad de `cargar_opcodes()` es inalcanzable. Existe, y se dice que no está
probada.

**La lección de la ronda, y es la duodécima vez**: un `0` con el patrón pegado al
componente (`amdgpu*.c` en vez de `amdgpu/*.c`) sale bien formado, se imprime, y
no significa nada. Casi lo dejo escrito como evidencia. Además escribí "0 de los
179 ficheros" con un 179 que no había contado. A partir de aquí, **todo recuento
lleva el número de elementos examinados, y los controles que dependen de ficheros
externos OMITen si no los encuentran**.

---

## Ronda 2026-10-02 (tarde 2) · RK-10 · los layouts de la BTF, guardados

`/sys/kernel/btf/amdgpu` es **por arranque**, y en esta máquina se reescribió
dentro del mismo arranque. `pahole` sobre el `.ko` no es alternativa: su
sección `.BTF` está partida y falla. O sea que había una puerta de un solo
sentido: cuando el layout hiciera falta y no estuviera guardado, ya no habría de
dónde sacarlo.

**Guardado**: `revkit/btfsnap.py` y `revkit/btf-amdgpu-layouts.txt`, 12 structs
resueltos con su procedencia (sha256, `uname -r`, versión de `pahole`). La BTF
son 3.88 MB y no es versionable; los layouts sí, y son lo que sirve.

**Cobra de inmediato**: el snapshot dice `u64 flags; /* 584 8 */` en
`struct amdgpu_bo`, y 584 = **0x248**. Es la corroboración de `EV-33`, y a
diferencia de la medida en vivo **queda en disco para después del reinicio**.

**Una categoría nueva**: `NO_EN_BTF` no es `PROVEN_ABSENT`. La BTF del módulo
solo cubre los tipos que el módulo exporta. Medido: `drm_bo` **no** está y
`drm_gem_object` **sí**: es un renombrado en este kernel, no una ausencia. Una
herramienta que mezclara los dos habría producido un `PROVEN_ABSENT` falso.

**Tres defectos propios cazados antes de usar la herramienta**: `--comparar` daba
deriva falsa en cada ejecución (la línea de hora siempre cambia), `--structs ""`
caía en silencio a la lista por defecto, y un `NameError` en un generador roto.
El selftest se **provocó** con un mutante que reinstala la sustitución silenciosa
y sale `rc=1`: un control que no puede fallar no sería un control.

**Sin cambio de bloqueos**: `F12` sigue necesitando root —`RX550_SUDO_PASS`
comprobada esta ronda, **ausente**, se perdió al reiniciar— y además un anillo
con `vm_flush`, que no está en las 4 capturas. `F2b` y `F14` igual.

---

## Ronda 2026-10-02 (tarde 3) · EV-36 · la pregunta del EXPLICIT_SYNC, cerrada por su premisa

Dejé abierta la pregunta de si `bo->flags & EXPLICIT_SYNC` decide cómo pasar un
IB. **La premisa era falsa**, y se cierra por donde faltaba:

- `amdgpu_cs_sync_rings()` corre **antes** de `amdgpu_cs_submit()`, que es donde
  se emiten los IB, y no escribe un solo dword.
- Lo que decide es el modo de dependencia de fence, y en `EXPLICIT`
  `amdgpu_sync_test_fence` devuelve `false` **siempre**: **no hay dependencia
  implícita**.
- Los fences de VM y KFD se descartan antes del `switch` porque el owner es
  `&fpriv->vm`: **los fences de actualización de VM nunca crean dependencia de
  job por esta vía**.
- `AMDGPU_SYNC_ALWAYS` es un **miembro muerto**: 2 apariciones en todo el árbol
  (definición y `case`), en los tres árboles del corpus.

**El fallo de método, que importa más**: busqué `EXPLICIT_SYNC` y encontré 3
coincidencias, ninguna el consumidor real. Una era un accessor
(`amdgpu_bo_explicit_sync`). "3 y ninguna lo usa" se lee como "no influye", y
sí influye. Un accessor con nombre propio rompe la búsqueda por el símbolo
original.

**Sin tocar hardware.** Todo es lectura de fuente. `EV-21`..`EV-30` intactas: el
contenido del IB y el `count` no entran en esta decisión.

---

## Ronda 2026-10-02 (tarde 4) · EV-37 · el censo era 49, y NOP es la excepcion

**"50 de 50" estaba mal, en 5 sitios de 4 documentos.** `6078`
(`INDIRECT_BUFFER_CONST`) y `6080` (`INDIRECT_BUFFER`) son las **dos ramas del
mismo `if/else`** sobre un `header` unico, y solo se escribe una: lo que viene
despues son siempre 3 escrituras, con `count = 2`. El numero de sitios de emision
distintos es **49**, y la aritmetica cierra exacta: 43 automaticas + 6 a mano.

**La septima "sin reconciliar" era ese brazo duplicado.** El texto decia siete con
una tabla de seis. Por eso el recuento no cuadraba y no se veia.

**`NOP` NO obedece `count = payload − 1`.** El relleno se escribe `.nop =
PACKET3(PACKET3_NOP, 0x3FFF)`: el campo `count` va a todos-unos **a proposito**.
"49 de 49" no incluye los 3 sitios de `NOP`, asi que el veredicto no lo afirma.
Quien escriba un driver tiene que saber que `NOP` es relleno.

**Lo que de verdad importa: `pm4census` lee otro fichero.** Sin `--kernel` reporta
7209 lineas, que es la copia de **`rx550-upstream-7.2.8`**, no el 7.1.3 que corre
el host. Los tres arboles del corpus tienen el mismo `gfx_v8_0.c` byte a byte, asi
que no hay ambiguedad: es que la herramienta mide otra cosa y lo etiqueta como "el
fichero que esta GPU ejecuta".

**Y una lista mia retirada**: los "17 opcodes que cuelgan de RE-30" omitian 8
paquetes que si llevan `count` e incluian los dos casos composicionales mas duros.
La pregunta estaba mal planteada: **todos** los PACKET3 llevan campo `count`; lo
que distingue es quien tiene payload.

**Deficit heredado, medido y atribuido**: `EVIDENCE-MATRIX.md` tiene un numero
impar de fences desde antes de hoy (181 en `bfbc393`, 209 ahora; cada ronda anade
un numero par). No lo localizo y **retiro** la linea 1985 que tenia anotada: era
una localizacion inventada por un metodo que no puede darla. Queda
`NOT_DETERMINED` y declarado, no reparado.

## Ronda duplicada a proposito

---

## Ronda 2026-10-02 (tarde 5) · F12 era EACCES, y hay un tercer bloqueo

**Me equivoqué en el diagnóstico de F12 y lo he corregido.** Escribí que
`/sys/kernel/debug/dri/0/` "no existe". **Es `EACCES`.** El padre es
`0700 root:root` y debugfs está montado, así que todo lo que hay debajo devuelve
permiso denegado y **no hay forma de saber si existe**. `NOT_DETERMINED` por
permiso, no `NOT_FOUND`. Es justo la conversión que las reglas prohíben, cometida
por mí (`NR-2026-10-02-s`).

**Y F12 tenía un tercer bloqueo que no estaba en la lista, medido**: no hay
ningún cliente DRM abierto (0 coincidencias de `/dev/dri/*` en `/proc/*/fd`), y
los directorios de debugfs de amdgpu son **por cliente**. Sin cliente no hay
`dri/<minor>/`, tenga root o no. La cadena son tres eslabones: cliente abierto,
root, y una carga que produzca el anillo.

**No abro el cliente.** `/dev/dri/renderD128` es `crw-rw-rw-`, o sea que no
requiere permiso — pero abrir un cliente DRM es **NIVEL 3**, toca el driver, y
solo se justificaría con un discriminante que cierre algo. Anotado como ruta.

**Lo que sí sale: el observador de F2b existe y es upstream.**
`amdgpu_debugfs.c:2585` registra `vm_pagetable_info` con modo `0444`, y está en
los tres árboles del corpus. Dejaba de dar por buena la idea de que "no hay
observador", que era una afirmación que llevaba rondando sin mirar el upstream.

**Y lo que otra sesión dejó anotado en el writer de PDE**, que toca F2b: la ruta
**CPU enmascara `pt` a `pte_addr_mask`** (`amdgpu_gmc.c:171`) y la ruta **SDMA
guarda `addr|flags` sin enmascarar** (`amdgpu_vm_sdma.c:197`). Los dos escritores
codifican la dirección distinto. Pendiente de verificar por mis vías.

**Medido de paso**: `baseline` y `working` son **byte-idénticos** (2787 ficheros,
0 diferencias), así que da igual cuál lea una herramienta. `kernelbuild` tiene
los mismos 2787 pero **4 distintos** — `amdgpu_debugfs.c/.h`, `amdgpu_vm.c`,
`amdgpu_vm_pt.c` — que no son otra versión del kernel sino la instrumentación que
añadió otra sesión.

**Y un hueco de la suite, cerrado**: `cn8` no miraba fences ni cabeceras
duplicadas, y la suite estaba en verde con un documento partido. Dos controles
nuevos, con la deuda **fijada como conjunto** en vez de exigir cero, y
provocados en los tres sentidos (fence nuevo, duplicado nuevo, y **arreglar la
deuda de otro**, que también falla para que la lista no se olvide).

---

## Ronda 2026-10-02 (tarde 6) · EV-38 · quien escribe la PTE, y con que ancho

**Hay TRES codificadores de PTE/PDE, no uno ni dos**, y difieren en dos ejes:

| ruta | donde | enmascara | como escribe |
|---|---|---|---|
| CPU | `amdgpu_gmc.c:173-175` | **sí** | `writeq`, un store de 64 bits |
| SDMA, una PTE | `sdma_v2_4.c` `_vm_write_pte` | no | dos stores de 32 bits, en un paquete SDMA |
| SDMA, lote | `amdgpu_vm_sdma.c:276-279` | no | `u64` armado dentro del IB |

**El hecho que decide: `pte_addr_mask` tiene UNA sola lectura en todo el driver**,
en `amdgpu_gmc.c:173`, que es la **ruta CPU**. Las dos rutas SDMA —la efectiva en
esta placa— no la consultan. Y no hay ninguna guardia que compruebe que la
dirección quepa: se buscaron otras formas antes de afirmarlo, y los `WARN_ON`
que hay son de espacio en el IB y de rangos de VRAM.

**La frontera para un driver propio**: la máscara es `0x000000FFFFFFF000`, bits
[39:12] → **28 bits** de dirección, ventana 256 MiB. Con direcciones legales la
máscara no quita nada y las tres rutas escriben lo mismo. En cuanto una PA
necesite más de 28 bits sobre el offset (**PA ≥ 2^40**) la CPU trunca y SDMA no, y
nada avisa. O se garantiza que la PA cabe, o se implementa la guardia que AMD no
puso.

**Corregida una formulation mía**: "el ASIC instancia `gmc_v8_1_0`" era engañoso.
`gmc_v8_1_ip_block` es un *descriptor* de versión de IP que comparte
`.funcs = &gmc_v8_0_ip_funcs`; no hay implementación v8_1 separada. Da igual cuál
sea la revisión: la máscara es la de `gmc_v8_0.c:1134`.

**Y no hice falta retirar nada**: dudé de mis "28 bits" y los conté con Python.
Estaban bien. El error era mío leyendo el hex.

**Mi control nuevo cometía el mismo error que el hallazgo**: grepeaba la máscara
por todo el árbol y, al mutar la de `gmc_v8_0.c`, leía la de `gmc_v6_0.c` — que
tiene el mismo valor — y pasaba en verde. Es la tercera vez en la sesión que
mezclar generaciones al leer un valor compartido sale bien(false positive).
Corregido, y con mutación que ahora sí lo cae.

**Y el control de fences de la ronda anterior me cazó a mí**: abrí un ``` sin
cerrar en el NR nuevo, y `cn8` lo vio en la misma pasada. Antes habría entrado con
la suite en verde.

---

## Ronda 2026-10-02 (tarde 7) · EV-38bis · cuatro codificadores, y el hardware tiene un campo "mask"

Al revisar EV-38 comprobé si había repetido el error de generación. Lo había, y
**dos veces**: en la tabla y en el control.

**Polaris12 instala `sdma_v3_1_ip_block`** (`vi.c:2113`), que comparte
`sdma_v3_0_ip_funcs`. El codificador vivo es **`sdma_v3_0_vm_write_pte`**, no el
de `sdma_v2_4` que yo citaba — ese es el de Topaz, otro ASIC de la misma familia.

**Y apareció un cuarto codificador**, que es el que de verdad importa:

| ruta | dónde | enmascara | cómo escribe |
|---|---|---|---|
| CPU | `amdgpu_gmc.c:173-175` | **sí** | `writeq` |
| SDMA `count<3` | `sdma_v3_0.c:952` | no | `addr|flags` por software, split de 32 bits |
| SDMA `count>=3` | `sdma_v3_0.c:982` | no | `SDMA_OP_GEN_PTEPDE`, 10 dwords, con campo **`mask`** y campo **`value`** |
| SDMA en lote | `amdgpu_vm_sdma.c:276-279` | no | `u64` armado en el IB |

**El criterio es `count < 3`**. Con 1–2 entradas el software hace el OR y **no hay
máscara**. Con **3+**, el hardware recibe los flags **como campo "mask"** y la
dirección **sin enmascarar como "value"**: **el AND lo hace el propio SDMA**.

**Los dos caminos no son dos formas de escribir lo mismo**: uno dice "valor ya
combinado" y el otro "máscara de hardware + valor". Solo uno tiene un campo de
máscara en el hardware, y para un driver propio esa es una decisión de diseño, no
un detalle de codificación. El de lote usa `copy_pte_num_dw = 7`.

**El control ya no lleva nombres de fichero a mano**: deriva del `case` del chip
al bloque, de ahí al fichero, de ahí a `.funcs`, y de ahí a la tabla de PTE. Y
**esa derivación tuvo al principio el defecto que pretendía cazar**: `vi.c` tiene
ocho `case CHIP_POLARIS12` en switches distintos, y yo agarraba el primero.
Anclado a la función.

Es la **cuarta** vez en la sesión que mezclar generaciones produce un falso
positivo: `sid.h` en EV-35, `gmc_v6_0.c` en el control de la máscara,
`pm4census` con 7.2.8, y ahora el SDMA. La regla que sale es una sola: **en un
control, un nombre de fichero no es un dato, es una suposición con formato de
dato.**

## Ronda 2026-10-02 (tarde 8) · EV-39 · `GC_HWIP` vale 0, y de ahi sale el flush

**LO QUE PASA DE `NOT_DETERMINED`/`DERIVATION` A `PROVEN`**

1. `amdgpu_ip_version(adev, GC_HWIP, 0) == 0` en esta placa. `PROVEN`, con la
   cadena de cinco eslabones en `EVIDENCE-MATRIX.md` (EV-39). El eslabon que
   faltaba era el `kzalloc`: no basta con que nadie escriba el campo, hace falta
   que el `struct` entero se reserve a cero, y se reserva con
   `devm_drm_dev_alloc` -> `kzalloc(sizeof(struct amdgpu_device))`.

2. **El flush de TLB en la actualizacion de page tables es incondicional**, y ya
   no es solo "el codigo lo hace": hay causa. `amdgpu_vm.c:1157` compara `0 <
   IP_VERSION(9,0,0)`, que es cierto por construccion, porque `IP_VERSION(mj,..)`
   es `(mj<<24)|..` y para ningun ASIC real vale 0. Confirma y **explica** el
   "SB page walker invalidate siempre obligatorio" de `085`.

3. **Los cuatro codificadores de PTE/PDE toman la rama legacy.** `AMDGPU_PTE_PRT_FLAG`,
   `AMDGPU_PDE_BFS_FLAG` y `AMDGPU_PDE_PTE_FLAG` bifurcan sobre `GC_HWIP >=
   12.0.0`, que aqui es falso. Mi driver propio **no** debe usar el bit 56 para
   PRT ni el bit 63 para PDE-como-PTE: son campos de gfx12.

**LO QUE SE ESTRECHA**

4. La granularidad de 8 PTE del TLB de GFX8 pasa de "propiedad del hardware" a
   `NOT_INDEPENDENTLY_CORROBORATED`: una sola fuente (el comentario de
   `amdgpu_vm.c:1155`, unico lugar del driver que lo dice), sin registro que lo
   describa en `asic_reg/gmc/gmc_8_{1,2}_sh_mask.h` y sin codigo que dependa de la
   alineacion a 8 como contraprueba. **La consecuencia queda `PROVEN`; la causa no.**
   Y la distincion importa: *"se por que"* frente a *"copie por que"*.

**LO NUEVO, Y ES DE MI DOMINIO**

5. **MES es inalcanzable en Polaris12** (`PROVEN_ABSENT`), y por un motivo que
   no es "este ASIC no esta en la lista":
   `amdgpu_discovery_set_mes_ip_blocks()` selecciona el bloque leyendo
   **`GC_HWIP`**, con 13 casos todos `11.x`/`12.x` y `default: break;`. Con el
   valor 0 no casa ninguno. Y no existe `mes_v9_*.c` ni `mes_v10_*.c`: los unicos
   tres son `v11_0`, `v12_0`, `v12_1`.

   Esto corrobora **EV-38bis desde una direccion que no habia usado**. Ahi segui el
   codificador vivo por `sdma_v3_0_ip_funcs`; aqui pregunte si existe hardware de
   VM-ops en MES. No existe, luego no hay codificador de PTE/PDE en MES. Dos
   caminos, la misma conclusion.

6. **Un eje que el censo de versiones no mide**: una comparacion puede ser
   constante *y* estar en codigo que no se ejecuta. De las 46 comparaciones que
   reporta `ipver_zero.py`, **5 estan en `amdgpu_mes.c`, sin ningun llamador
   alcanzable desde la ruta VI**. Se quedan **41** las que gobiernan esta placa.
   La herramienta no es incorrecta: no mide alcance, y su docstring solo declara
   que no evalua `switch`.

**Y UN HECHO DE ESTRUCTURA DEL CORPUS, QUE NO ES SECUNDARIO**

7. `baseline/` y `working/` son arboles **PARCIALES**: solo `drivers/gpu/drm/amd/`.
   El core de DRM solo esta en `kernelbuild/`, que es la raiz completa. Sin mirar
   `kernelbuild` habria declarado el eslabon 3 ausente cuando existe, y EV-39
   entera habria quedado `NOT_DETERMINED` por una limitacion mia. **"No lo
   encontre en `baseline`" es `NOT_AVAILABLE`, nunca `PROVEN_ABSENT`.**

**Quinta vez que mezclar generaciones da un numero falso.** Mi grep dio 260 sitios
de `GC_HWIP`; el numero bueno es 50 en 18 ficheros. Countaba ficheros que en esta
placa no se ejecutan (`gfx_v9_0.c`, `gfx_v10_*.c`, `nv_*`). Es el mismo patron que
`sid.h` en EV-35, `gmc_v6_0.c` en el control de mascara, `pm4census` con 7.2.8 y
el SDMA. **Contar apariciones en un arbol no es contar cosas que se ejecutan.**

`GPU INTACTA. WRITE_EXECUTION NONE. NIVEL 0/1.`

## Ronda 2026-10-02 (tarde 9) · EV-40 · los bloques IP que existen en esta placa

Es el **item 1 del universo de investigacion** (device initialization), y no
tenia nada. Ahora esta entero y medido.

**1 · HAY DOS RUTAS DE SELECCION, Y SON MUTUAMENTE EXCLUSIVAS.**
`amdgpu_device.c:1978-1999` reparte por `adev->asic_type`:

```
case CHIP_POLARIS12:  ... adev->family = AMDGPU_FAMILY_VI;
                       r = vi_set_ip_blocks(adev);          break;
default:                  r = amdgpu_discovery_set_ip_blocks(adev);   break;
```
La primera es la ruta por **FAMILIA** y la segunda por **VERSION** (`GC_HWIP`).
Polaris12 entra en el `case` y no llega al `default`. Consecuencias, ambas
`PROVEN`:

- **Ninguna funcion `amdgpu_discovery_set_*` se ejecuta en esta placa.** Con ello,
  los `switch` sobre `GC_HWIP` que estan ahi dentro no son "degenerados": son
  codigo que no llega a correr.
- **No se instancia ningun bloque de hardware de 9.x/10.x/11.x/12.x.**

**2 · LOS DIEZ BLOQUES QUE EXISTEN.** De los 84 que el driver sabe anadir,
Polaris12 instancia **10**: ocho incondicionales y dos condicionados.

```
INCONDICIONAL   vi_common_ip_block      vi.c:2109
INCONDICIONAL   gmc_v8_1_ip_block       vi.c:2110
INCONDICIONAL   tonga_ih_ip_block       vi.c:2111
INCONDICIONAL   gfx_v8_0_ip_block       vi.c:2112
INCONDICIONAL   sdma_v3_1_ip_block      vi.c:2113
INCONDICIONAL   pp_smu_ip_block         vi.c:2114
INCONDICIONAL   uvd_v6_3_ip_block       vi.c:2121
INCONDICIONAL   vce_v3_4_ip_block       vi.c:2122
CONDICIONAL     amdgpu_vkms_ip_block    vi.c:2116   if (adev->enable_virtual_display)
CONDICIONAL     dm_ip_block             vi.c:2119   else if (has_dc_support)
```
Las condiciones **no se evaluan**: es otra pregunta y es de runtime.

**3 · CORROBORACION INDEPENDIENTE DE EV-38bis.** Alli llegue a
`gmc_v8_1_ip_block` y `sdma_v3_1_ip_block` por la cadena
`sdma_v3_0_vm_write_pte` -> `sdma_v3_1_ip_block` -> `sdma_v3_0_ip_funcs`. Aqui los
he encontrado por un camino **invertido**: preguntando que bloques existen, sin
mirar funciones. Mismos dos nombres, dos caminos, conclusion independiente.

**4 · CORROBORACION DE LA OTRA SESION.** Su `190` decia que el kernel registra 9
bloques IP y que tres no se habian mirado nunca: `dm`, `uvd_v6_3`, `vce_v3_4`.
Los tres estan aqui: dos en el brazo de Polaris12 (uno condicionado) y dos
incondicionales. Los nombres casan.

**5 · ALCANCE: 4 DE 50 COMPARACIONES DE `GC_HWIP` DESCARTABLES, CON HECHO.**

```
sonas descartables de 50           4     (el resto, 46, NO probadas alcanzantes)
amdgpu_gfx.c:514  amdgpu_gfx_mqd_symmetrically_map_cu_mask   -> gfx_v11_0, gfx_v12_0
amdgpu_gmc.c:1766 amdgpu_gmc_get_vram_info                   -> gmc_v9_0/v10_0/v11_0/v12_0
amdgpu_mes.c:682  amdgpu_mes_init_microcode                  -> mes_v11_0/v12_0/v12_1
amdgpu_mes.c:683  amdgpu_mes_init_microcode                  -> mes_v11_0/v12_0/v12_1
```
La regla del descarte es **un hecho, no una aproximacion**: todos los llamadores
de la funcion estan en ficheros que **solo** implementan un bloque IP que no se
instancia. Eso es EV-39, verificado. Lo que queda no esta probado alcanzante:
`no descartado` no es `vivo`.

**LIMITE DECLARADO, y es una perdida de positivos A PROPOSITO:** la regla es de un
solo salto. Si el intermediario vive en un fichero comun, el sitio no se descarta
aunque no se ejecute nunca. Por eso **esta cifra es 4, no 7**: ver la correccion
en `NEGATIVE-RESULTS.md`.

`GPU INTACTA. WRITE_EXECUTION NONE. NIVEL 0/1.`

## Ronda 2026-10-02 (tarde 10) · los 145 puntos de entrada del driver en esta placa

El driver entra al hardware casi todo por **puntero a funcion**. Ese camino es
invisible para cualquier indice de llamadas por nombre, y es el que un driver
propio tiene que implementar primero.

**LOS DIEZ BLOQUES, SUS DIEZ TABLAS, Y NINGUNA SE LLAMA COMO SU BLOQUE**

```
bloque               tabla                        funciones  definida en
vi_common_ip_block   vi_common_ip_funcs                 11   amdgpu/vi.c
gmc_v8_1_ip_block    gmc_v8_0_ip_funcs                 17   amdgpu/gmc_v8_0.c
tonga_ih_ip_block    tonga_ih_ip_funcs                 15   amdgpu/tonga_ih.c
gfx_v8_0_ip_block    gfx_v8_0_ip_funcs                 19   amdgpu/gfx_v8_0.c
sdma_v3_1_ip_block   sdma_v3_1_ip_funcs                 19   amdgpu/sdma_v3_0.c
pp_smu_ip_block      pp_ip_funcs                       12   pm/powerplay/amd_powerplay.c
amdgpu_vkms_ip_block amdgpu_vkms_ip_funcs                9   amdgpu/amdgpu_vkms.c
uvd_v6_3_ip_block    uvd_v6_3_ip_funcs                 15   amdgpu/uvd_v6_0.c
vce_v3_4_ip_block    vce_v3_4_ip_funcs                 18   amdgpu/vce_v3_0.c
dm_ip_block          amdgpu_dm_funcs                   10   display/amdgpu_dm/amdgpu_dm.c
                                                        ---   145 en total
```
**TRES IDENTIDADES DISTINTAS, Y LAS TRES SE ROMPEN EN ESTA PLACA.**

1. **El bloque no es la tabla.** `gfx_v8_0_ip_block` y `gfx_v8_1_ip_block`
   comparten `.funcs = &gfx_v8_0_ip_funcs`. `gmc_v8_1_ip_block` usa
   `gmc_v8_0_ip_funcs`. `dm_ip_block` usa `amdgpu_dm_funcs`. `pp_smu_ip_block` usa
   `pp_ip_funcs`.
2. **El bloque no es el fichero.** De los diez, **cuatro estan definidos en un
   fichero con otro nombre**: `gmc_v8_1_ip_block` en `gmc_v8_0.c`,
   `sdma_v3_1_ip_block` en `sdma_v3_0.c`, `uvd_v6_3_ip_block` en `uvd_v6_0.c`,
   `vce_v3_4_ip_block` en `vce_v3_0.c`.
3. **El bloque no esta en `amdgpu/`.** `pp_smu_ip_block` esta en
   `amd/pm/powerplay/` y `dm_ip_block` en `amd/display/amdgpu_dm/`. Buscando
   dentro de `amdgpu/` la herramienta decia "SIN TABLA" de dos bloques que **si
   existen**: no era una ausencia, era un alcance.

**La superficie de init abarca cuatro subsistemas**: `amdgpu/`, `pm/powerplay/`,
`display/amdgpu_dm/` y `include/`. Para un driver propio, "encender la placa" no
es un fichero: son cuatro.

**LIMITE DECLARADO.** Solo las tablas `.funcs` de los bloques. **No** cubre los
fops de DRM, los `dma_buf_ops`, los `file_operations`, sysfs ni debugfs, que
tambien entran por puntero y son la via por la que el **kernel** llama al driver.
Un `evict` de VRAM, por ejemplo, no pasa por ninguna tabla `.funcs`. Es
`NOT_IN_CORPUS` para esta cuenta, no `PROVEN_ABSENT`.

`GPU INTACTA. WRITE_EXECUTION NONE. NIVEL 0/1.`

## Ronda 2026-10-02 (tarde 11) · EV-41 · el camino de envio desde userspace

Falta en el estado el **primer tramo** de los items 12 y 13: como entra una orden
de userspace y hasta donde llega antes de salirse del driver. Esta ronda lo lee.

**LA SUPERFICIE DE IOCTLS, DECLARADA POR AMDGPU: 20.**

```
AMDGPU_GEM_CREATE     AMDGPU_CTX                AMDGPU_VM
AMDGPU_SCHED          AMDGPU_BO_LIST            AMDGPU_FENCE_TO_HANDLE
AMDGPU_GEM_MMAP       AMDGPU_GEM_WAIT_IDLE      AMDGPU_CS
AMDGPU_INFO           AMDGPU_WAIT_CS            AMDGPU_WAIT_FENCES
AMDGPU_GEM_METADATA   AMDGPU_GEM_VA             AMDGPU_GEM_OP
AMDGPU_GEM_USERPTR    AMDGPU_USERQ              AMDGPU_USERQ_SIGNAL
AMDGPU_USERQ_WAIT     AMDGPU_GEM_LIST_HANDLES
```
`amdgpu_ioctls_kms[]` en `amdgpu_drv.c:3046-3068`, y `amdgpu_kms_driver` la
registra en `.ioctls` con `.num_ioctls = ARRAY_SIZE`.

**LIMITE, y es el de la regla de no presentar un parcial como completo: el core de
DRM anade 78 ioctls mas** (`drm_ioctls[]`, `drm_ioctl.c:632`, solo en
`kernelbuild`). Asi que **20 es `NOT_COMPLETE`**, no "los 20 ioctls del driver".

**EL ORDEN REAL DEL ioctl DE ENVIO, LEIDO (no inferido).**
`amdgpu_cs_ioctl`, `amdgpu_cs.c:1411-1473`, ocho etapas y dos caminos de error:

```
1417  amdgpu_ras_intr_triggered()   -> -EHWPOISON   puerta RAS, la primera de todas
1420  adev->accel_working           -> -EBUSY       puerta de aceleracion
1423  amdgpu_cs_parser_init         -> error_fini
1429  amdgpu_cs_pass1               -> error_fini
1433  amdgpu_cs_pass2               -> error_fini
1437  amdgpu_cs_parser_bos          -> error_fini
1446  amdgpu_cs_patch_jobs          -> error_backoff
1450  amdgpu_cs_vm_handling         -> error_backoff
1454  amdgpu_cs_sync_rings          -> error_backoff
1458  trace_amdgpu_cs_ibs           (no puede fallar)
1460  amdgpu_cs_submit              -> error_backoff
1464  amdgpu_cs_parser_fini
error_backoff:1468  mutex_unlock(parser.bo_list->bo_list_mutex)
error_fini:1471     amdgpu_cs_parser_fini
```
**El orden NO es el orden del fichero.** `amdgpu_cs_parser_bos` esta definido en la
linea 845, despues de `pass2` (600), y se ejecuta **despues** de `pass2`;
`amdgpu_cs_patch_jobs` (1072) se ejecuta **antes** de `amdgpu_cs_vm_handling`
(1085). Si hubiera deducido la secuencia del orden de definicion, la habria dado
mal. **Octava vez que el orden en el fichero no es el orden de ejecucion.**

Los dos caminos de error no son intercambiables: `error_backoff` **desbloquea
`bo_list_mutex`** y `error_fini` no. O sea que el mutex se toma en
`amdgpu_cs_parser_bos` (1437) y el unico camino que lo suelta es el posterior, lo
que hace consistente que los tres fallos anteriores no lo hayan tomado todavia.

**LO QUE HACE CADA PASADA, por lo que LLAMA (no por lo que se llama).**
`pass1` llama a `p1_ib`, `p1_user_fence`, `p1_bo_handles`, `job_alloc`,
`sriov_vf` y `vm_set_task_info`. `pass2` llama a las siete `p2_*`: `p2_ib`,
`p2_dependencies`, `p2_syncobj_in`, `p2_syncobj_timeline_wait`, `p2_syncobj_out`,
`p2_syncobj_timeline_signal` y `p2_shadow`. O sea: **el estado de sincronizacion
entra por userspace en dos puntos distintos** y con dos mecanismos distintos, y
ambos estan en el camino de envio, no en un ioctl aparte.

**Y EL HALLAZGO DE FONDO: EL ENVIO ES ASINCRONO, Y A MEDIDA SE SALE DEL CORPUS.**
`amdgpu_cs_submit` (`amdgpu_cs.c:1275`) **no llama a `amdgpu_ring_commit`**. Crea
los fences (`amdgpu_ctx_add_fence`, `dma_resv_add_fence`) y empuja el trabajo con

```
drm_sched_entity_push_job(&p->jobs[i]->base)
```
que vive en el **core de DRM**, en `drivers/gpu/drm/scheduler/sched_entity.c`
(`EXPORT_SYMBOL` en la linea 631). Y `drivers/gpu/drm/scheduler/` **no esta en
`baseline` ni en `working`**: esos arboles solo tienen `drivers/gpu/drm/amd/`.

Consecuencias, y las dos importan:

1. **`AMDGPU_CS` devuelve 0 y el trabajo aun no se ha escrito en el anillo.** El
   ioctl analiza y encola; la escritura al anillo ocurre despues, desde el
   scheduler. El retorno del ioctl **no** significa ejecucion. Eso es una
   asincronia de software, deducible del corpus, y es distinta de la que tengo
   abierta como `hardware execution ordering NOT_PROVEN`.
2. **El camino sale del corpus a mitad.** La mitad de analisis esta entera
   (`amdgpu_cs.c`, 37 funciones, 1817 lineas); la mitad de ejecucion pasa por el
   core. Los saltos exactos dentro del scheduler son `NOT_IN_CORPUS` en
   `baseline`, no `PROVEN_ABSENT`. Reaparece la misma limitacion de EV-39: para
   leer el puente hay que ir a `kernelbuild`.

El reingreso al driver es por puntero a funcion: `amdgpu_job.c:515` registra
`.run_job = amdgpu_job_run` (`amdgpu_job.c:426`). Es el mismo patron que las 145
entradas de EV-40: **una llamada por puntero no aparece en ningun grep**, y por eso
las 145 no cubren este salto.

`GPU INTACTA. WRITE_EXECUTION NONE. NIVEL 0/1.`
