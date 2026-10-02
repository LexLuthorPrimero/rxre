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
