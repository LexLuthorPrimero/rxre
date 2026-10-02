# IMPLEMENTATION-STATUS — qué existe, qué está cargado, qué está probado

> Distingue cuatro cosas que el repo confunde con frecuencia:
> `ESCRITO` ≠ `COMPILA` ≠ `SE HA VISTO EJECUTAR` ≠ `VALIDADO`.
> Un binario en disco no es un módulo cargado. Un test compilado no es un test
> ejecutado. Y nada de esto, sin excepción, es una afirmación sobre el hardware.
>
> `LAST_VERIFIED: 2026-10-01 11:20 -03:00`

---

## 1 · Lo que NO se ha hecho, y es lo primero que hay que saber

```
GPU_TOCADA          NO
MÓDULO_CARGADO      NO  -- nhwa, rx550, rx550_drv, rx550_pciid: ninguno en /proc/modules
ESCRITURA_A_MMIO    NONE
ESCRITURA_A_REGS    NONE
PCI CONFIG WRITE    NONE
BIND/UNBIND        NONE
RESET_DE_GPU        NONE
INSMOD / RMMOD     NONE
TAKEOVER           NO EJECUTADO
sysfs ESCRITO      NUNCA
FIRMWARE/VBIOS      INTACTOS
KERNEL             7.1.3-200.nobara.fc44, sin modificar
BOOT/PARTICIONES    INTACTOS
```

Comprobado por `/proc/modules` y `lsmod`:

```console
$ grep -iE "amdgpu|nhwa|rx550" /proc/modules
amdgpu 18698240 5 - Live 0x0000000000000000
amdxcp 12288 1 amdgpu, Live …
drm_ttm_helper, drm_exec, drm_buddy, gpu_sched, ttm, drm_suballoc_helper …
  <-- los únicos con amdgpu en la lista de usuarios. nhwa y rx550 no aparecen

$ lsmod | grep -iE "nhwa|rx550"
(nhawa/rx550 NOT loaded)
```

**La única operación de GPU que este proyecto ha ejecutado** es el shader BC3 de la
línea B, el 2026-09-29, como workload de usuario vía RADV. Eso no es una toma de
control del driver y no toca `/sys`. Ningún documento del repo hace esta distinción
explícita; por eso está aquí.

## 2 · Driver propio — Stage 1

```
DIRECTORIO  04-IMPLEMENTACION/rx550-driver/   (UNTRACKED, 9 fuentes + 9 tests)
SUBCOMPONENTE  07-DRIVER/kernel/   rx550.ko, rx550_drv.ko, rx550_main.c, rx550_pm4.c
SUBCOMPONENTE  07-DRIVER/driver/   rx550_pciid.c/.h, test_rx550_pciid.sh (UNTRACKED)
```

| Artefacto | Escrito | Compila | Cargado | Visto ejecutar | Validado |
|---|---|---|---|---|---|
| `rx550_drv.ko` | sí | sí | **no** | no | por `nm` |
| `rx550.ko` (char device) | sí | sí | **no** | no | por `nm` (es **no** driver PCI) |
| `rx550_pciid.ko` | sí | sí | **no** | no | — |
| `nhwa.ko` (ep08) | sí | sí | **no** | no | — |
| `tests/test_{fence,mem,mmio_access,regs,resource,submit,target_match,vm}` | sí | sí | n/a | **sí**, local | no |
| `tests/test_static.sh` | sí | — | n/a | no | no |

```
STAGE1-SUBSYSTEMS.md  07-DRIVER/kernel/      UNTRACKED
```

### 2.1 · `rx550_pm4.c` — el emisor de PTE, con un error de un dword **ya compilado**

```
ARTEFACTO   07-DRIVER/kernel/rx550_pm4.c  +  rx550_pm4.h   UNTRACKED en git
ORIGEN      036-correccion-023-implementada-ptepde.md, que implementa 035
ACTUALIZADO 038 (mtime del .c: 2026-10-01 13:14:14) — se reescribió DESPUÉS de que 035
            publicara su corrección, y SEGUÍA con `count - 1`. No es código abandonado
            >> **CORRECTED 2026-10-02**: ya no.  `rx550_pm4.c:298` escribe `count`, y
            >> la función entera replica `sdma_v3_0.c:986-996` dword a dword.  Ver
            >> `docs/OPEN-FRONTIERS.md` F3d y `RE-52`
ESTADO      ESCRITO · COMPILA · suite 75 checks verdes · NO CARGADO · NO VISTO EJECUTAR
LO QUE HACE  gains rx550_sdma_header() y rx550_sdma_vm_set_pte_pde(); emite 10 dwords
```

```
ESTADO    CODIGO  VALIDADO  CONTROL NEGATIVO  CARGADO
rx550_pm4  sí        NO            el equivocado   NO
```

**Por qué la columna de validación dice `NO` siendo que la suite pasa con 75 checks.**

```c
/* rx550_pm4.h:195 */   #define RX550_SDMA_PTEPDE_DW  10   /* sdma_v4_0.c:1649-1658 */
/* rx550_pm4.h:301 */   la codificación es count - 1, y count 0 daría 0xFFFFFFFF
/* rx550_pm4.c:298 */   ib->buf[ib->length_dw++] = count;   <- era count - 1
```

Las dos puntas del test leen `RX550_SDMA_PTEPDE_DW` **del mismo header**. Es coherencia,
no validación: no hay una segunda fuente con la que la constante pueda discrepar. Los 75
checks pueden estar verdes y el número estar equivocado, y están.

```
EL NÚMERO ESTÁ MAL, y por una causa registrada en C-011
  este ASIC usa sdma_v3_0, no sdma_v4_0:
    vi.c:2113              sdma_v3_1_ip_block  para CHIP_POLARIS12
    sdma_v3_0.c:1699       .funcs = &sdma_v3_0_ip_funcs
    host, boot de hoy      "detected ip block number 4 <sdma_v3_1_0> (sdma_v3_0)"
  y el emisor de referencia de ESTA GPU escribe `count`, no `count - 1`:
    sdma_v3_0.c:996        count          <- el que ejecuta este ASIC
    sdma_v4_0.c:1658       count - 1      <- no lo ejecuta; era el que copiaba rx550_pm4.c
    sdma_v3_0.c:996        count         <- lo que ejecuta este ASIC
  CONSECUENCIA  un driver propio que use esto escribe UN PTE POR ENCIMA del final del
  rango pedido. Es corrupción silenciosa de memoria, no un fallo visible
GRAVEDAD  ALTA, y es el primer error de este árbol cuya corrección NO está en la
  documentación: no es un documento con un número malo, es código compilable que emite
  el número. Es el primer caso donde el número malo no está en un documento sino en la
  instrucción de máquina que se ejecuta
POR QUENO LO DETECTÓ LA SUITE DE 036
  036 declara haber introducido cinco mutaciones que la suite detecta. Ninguna puede ser
  esta: la suite no tiene una segunda fuente con la que discrepar del .h
LO QUE FALTA PARA VALIDARLO, y es concreto
  un control negativo contra el emisor del driver de REFERENCIA, no contra la propia
  constante. Comparar `rx550_pm4.c` con `sdma_v3_0.c:982-997` carácter a carácter sobre
  los dos últimos dwords es lo que habría atrapado esto
LO QUE NO SE HACE  editarlo. Es trabajo de otra sesión, con su cerrojo, y 036 es
  implementación viva. COORDINACION.md:184 es "informa, no arregles"
Y UNA SEGUNDA CAPA, declarada por 038 desde dentro del propio proyecto
  la circularidad era real y la reconocía el propio autor: el codificador se escribió
  leyendo amdgpu y las expectativas del test se transcribieron del MISMO amdgpu, así que
  un error de lectura replicado en los dos sitios pasa las comprobaciones
  036/037 lo declararon, 035 lo cometió, y 038 lo rompe con rx550pm4val.c, que valida
  ESTRUCTURA sin acceso al corpus
  PERO declara su propia salida: "ya se sabe que acepta uno: count en vez de count-1"
  Es decir: el validador caza el error estructural y NO el de valor. Y el de C-011 es de
  valor. Para sDMA la longitud es implícita en el opcode, no en un campo count — por eso
  una regla de PACKET3 (count = payload − 1) no alcanza a PTEPDE
VERIFICADO  grep sobre rx550_pm4.c:239, 253, 265, 268, 277, 301 y rx550_pm4.h:192, 194,
            195, 300. La cadena de bloques del ASIC, leída del corpus y del dev_info
```



**El control negativo que hace creíble a `check-drivers`**: cada comprobación falla si
el símbolo buscado **aparece**. Sin control contrario, "no encontré X" y "no hay X"
son la misma frase, y en este repo eso ya ha costado dos veces.

```console
rx550_drv.ko  DEBE ser driver PCI (positivo):
  OK    U __pci_register_driver / pci_enable_device / pci_request_regions
  OK    d rx550_pci_driver
rx550.ko      NO debe ser driver PCI (negativo):
  OK    0 símbolos pci
la etapa 1    NO mapea MMIO (negativo):
```

**Por qué se mantiene `rx550.ko` si no es el camino principal**: el propio Makefile lo
dice, y es un argumento bueno. No es un driver PCI — no tiene `struct pci_driver`, no
se registra con `pci_register_driver`, verificado con `nm` sobre el `.ko` — y un char
device no puede dar a userspace un BAR mapeado, que es lo que un driver de GPU
necesita. Se sigue compilando para que su código no se pudra, y porque `rx550_pm4.c`
tiene una suite que depende de él. **Decidir si se retira es la frontera F4.**

## 3 · Componentes modelados — sin hardware

Tres directorios, todos `UNTRACKED`, todos con tests y sin haber tocado la GPU:

| Componente | Ficheros | Qué modela | Estado |
|---|---|---|---|
| `04-IMPLEMENTACION/rx550-mem/` | 13 | Modelo de memoria: codificación de entradas PDE/PTE, ciclo de vida de la VM | escrito, compilado, tests written; `test_mem` **se retiró de la cola** de una sesión porque su `test_mem.c` estaba a medio escribir y `target_mem_host.h` duplicaba typedefs que su propio test ya definía |
| `04-IMPLEMENTACION/rx550-pm4/` | 5 | Codificador PM4, con `EVIDENCE.md` | escrito |
| `04-IMPLEMENTACION/rx550-torneo/` | — | Control seguro por DPM, perfiles, telemetría CSV | escrito, 64/64 checks (2026-09-25) |

El `rx550-mem` es el componente con más solapamiento entre sesiones: `Q2 = OWNED_BY_OTHER_SESSION`,
registrado en `DRIVER-MISSION-STATE.md` tras una sobrescritura a las 09:04 del 2026-09-29.

## 4 · Herramientas de análisis

Ver [`TOOLS-STATUS.md`](TOOLS-STATUS.md). Resumen de lo que sostiene evidencia:

```
VALIDATED    pm4_count_census.py · pm4dw.c · gfx8vmgeom · validate_rx550_final.py
TRACKED      count_vmflush_dw.py · frame_budget.py · semref (script) · kdeps.c
INVALID      semref (dependencia perdida)
SIN VALIDAR  kdeps.c · evidence_search.py (sin test de fallo)
NO HAY       ninguna que lea un registro de hardware
```

## 5 · Línea B — BC3/DXT5

### Fase 1 · Compresor CPU — `COMPLETE`

```
TEST                     26/26 [ OK ], 0 [FAIL]        make test
CAPACIDAD DE FALLAR      make check-ramp-discriminates
                           total : 65536 / 65536 pares con discrepancia
                           peor error : 255 de 255
                           RESULT: NO CONFORMA con la especificacion
                           OK: rejected the known-wrong ramp (exit 1)
                           rc=0
PSNR                     reference 28.78 · smooth 19.59 · pure noise 13.65
                         adversarial 10.90 dB
THROUGHPUT               C 83.7 · AVX2 86.0 MB/s  ->  speedup 1.03x
SPEEDUP AVX2             NOT_CONCLUYENTE  [NR-11]
                         El rango intra-implementación (C 78.9-85.1, AVX2 83.5-88.6)
                         es del orden de la diferencia entre implementaciones.
                         NO se afirma aceleración
BIT-IDÉNTICO             AVX2 == C sobre 200000 bloques
```

**El rango intra-run es el criterio, y es la regla que este proyecto se aplica a sí
mismo**: una diferencia menor que el rango intra-run no es una diferencia, es ruido, y
se reporta `NOT_CONCLUYENTE`. La primera versión de `CIERRE_PROYECTO.md` afirmaba un
speedup numérico; el dato se retiró cuando se midió el rango.

### Fase 2 · Descompresor GPU — `COMPLETE`, con `NOT_RECHECKED`

```
SALIDA DECLARADA  bloques discrepantes : 0 de 64
                  bytes discrepantes   : 0 de 4096
                  RESULT: GPU == CPU.   rc=0
                  3 corridas consecutivas
VALIDACIÓN DE SALIDA  4005 de 4096 bytes no nulos
                      ninguna palabra conserva el veneno 0xDEADBEEF
SIN SHADER NI QUAD     el shader mapea una invocación a un PÍXEL, no a un bloque:
                      DISPATCHES = ceil(64/256) = 1 estaba mal, hacen falta 4;
                      faltaba vkCmdPushConstants; el índice de color usaba & 0xFF
CORROBORACIÓN EN DISCO  3 imágenes PNG, 0 de 16384 bytes cada una
                      04-IMPLEMENTACION/work/*.decompress.log
                      *** IGNORADAS POR GIT (.gitignore:78) ***
NO VERSIONADO            la salida del agreement test de 64 bloques no está persistida
ESTADO HOY               NOT_RECHECKED. El texto de 7ed1eca es testimony, no artefacto
```

**Por qué la validación de salida es lo que hace que el resultado sea evidencia**: un
dispatch que no corre deja el buffer como se inicializó. Comparado byte a byte contra
la referencia de CPU da **cero discrepancias y un PASS**. Sin las dos comprobaciones
—salida no trivial, ningún patrón veneno— el defecto 2 habría producido un `PASS`
vacío. Está escrito en el README del decompresor y es el punto entero de la sección.

### Lo que la línea B NO demuestra

```
GFX_HWIP             NOT_DETERMINED. El test no consulta ni infiere la generación gfx
AD-12                NOT_DETERMINED. Frontera F2
spirv-val            VALIDADO. rc=0. Se dijo que faltaba y era FALSO (49bd550)
                     Queda pendiente sólo que el driver acepte el módulo, que es
                     evidencia sobre ese driver
EL CORPUS            determinista y sintético: guarda de regresión, no prueba exhaustiva
UN DISPATCH          no mide rendimiento. No hay cifra de rendimiento de la línea B
LIMITACIÓN #3        el test devuelve rc=0 aunque imprima [FAIL]. NO REVERIFICADO
                     Escrito por b7ed0c1 el 2026-09-29; sigue sin comprobar. Es lo
                     único de la línea que puede dar un verde falso en CI
```

## 6 · Puertas de autorización

`opencode.json` codifica las políticas en el harness. Estado medido:

```
DENY     c1 * · run_c1* · vkmark · glxgears · glmark2 · unigine · superposition
         gravitymark · nvidia-smi · nvtop · amdgpu_top
         modprobe · insmod * · rmmod * · systemctl · reboot · poweroff
         toda escritura a /sys/*  (echo/tee/cat/cp/mv/ln/sed -i)
         git push · git reset --hard · git filter-branch
         curl|sh NO, wget|sh NO (asimetría intencional)
ASK      insmod / rmmod  <- CAMBIADO de deny a ask en 65447aa (2026-10-01 06:39)
                           "para el experimento B"
         git checkout -- * · git restore * · git clean * · git rebase
         dnf remove · chown -R · ~/.config/opencode/*
ALLOW    bash general (incluye sudo) · edit en el repo · webfetch · websearch
         commit · task · read
```

**Lo que el cambio de `insmod`/`rmmod` a `ask` significa**: la política ya no impide
cargar un módulo; la pide. `65447aa` lo justifica con "el experimento B". Eso es una
**solicitud de autorización**, no una autorización concedida. La GPU sigue intacta y
ningún módulo del proyecto está cargado. La ruta de recuperación independiente está en
`PARTIAL` (1 de 3 condiciones), y `SSH-RECOVERY-PATH-2026-10-01.md` es explícito en que
la sesión del agente cuelga de la sesión gráfica: **el agente no puede ser su propia
ruta de recuperación**.

## 7 · Inventario de artefactos de build sin versionar

```
MÓDULOS      rx550_drv.ko · rx550.ko · rx550_pciid.ko · nhwa.ko
BINARIOS     rx550_compress · rx550_decompress · test_compress · test_alpha_ramp
             test_decompress · shader_vs_c · test_hardware_bc3 · vk_pipeline_min
             test_fence · test_mem · test_mmio_access · test_regs · test_resource
             test_submit · test_target_match · test_vm
TOOLS        gfx8vmgeom · semref · check-real-tree · run-bench · run-bench-real
OBJETOS      *.o · Module.symvers · modules.order · *.cmd   (gitignored)
```

**Ninguno de los binarios de la línea B está tracked.** `test_decompress` sí lo está
(`git ls-files` lo confirma) — es la excepción. Los demás los cubre `.gitignore`
línea a línea. La consecuencia relevante no es el repo: es que **un binario no
versionado no se puede re-ejecutar dentro de tres meses**, y varios de ellos son la
única forma de volver a obtener un dato.

## 8 · Resumen en una frase — el estado de la implementación

```
ESCRITO            mucho, y bien estructurado: dos líneas, componentes separados,
                   contratos escritos, control negativo en las herramientas
COMPILA            sí, los cuatro .ko y las tres suites
SE HA VISTO        las herramientas de análisis, sí y con discriminante.
EJECUTAR           los tests deStage 1, sí. La línea B, sí (2026-09-29).
CARGADO EN LA GPU  NADA
VALIDADO           el análisis estático, con contrapruebas (tool vs boot log).
                   El agreement test BC3, por testimony.
LA GPU             INTACTA
```

Lo que falta para que el driver propio toca hardware son dos cosas, y ninguna es
técnica: **una ruta de recuperación independiente demostrada** (hoy `PARTIAL`) y
**una autorización explícita**. Todo lo demás ya está escrito.