# MASTER-RESEARCH-STATUS — RX550 POLARIS12 / GFX8

> Índice operacional. Si algo aquí contradice a otro documento, **manda este** y el
> otro queda registrado como `STALE` en [`CONTRADICTIONS.md`](CONTRADICTIONS.md).
> `IMPLEMENTATION_IS_NOT_AUTHORITY`: que un fichero exista no prueba su contenido,
> y que un binario compile no prueba nada sobre el hardware.
>
> `LAST_VERIFIED: 2026-10-01 11:20 -03:00` · `VERIFIER: agente de documentación` ·
> `METODO: lectura de artefactos + ejecución de herramientas read-only + git log`

## PROJECT

Reconstruir el comportamiento real de una AMD Radeon RX 550 **Polaris12 / GFX8**
(`PCI 1002:699f`, ASIC Lexa PRO) y, a partir de esa evidencia, escribir un driver
Linux propio especializado en esa placa. La autoridad es
`EVIDENCIA → SEMÁNTICA → MODELO → TEST DISCRIMINANTE → IMPLEMENTACIÓN → VALIDACIÓN`.

El repo contiene **dos líneas de trabajo que no se deben confundir**:

| Línea | Qué es | Dónde vive | Estado |
|---|---|---|---|
| **A · GFX8 reverse engineering** | Reconstrucción de semántica de hardware desde el corpus del driver | `06-INGENIERIA-INVERSA/findings/`, `08-ARQUITECTURA/` | Activa, avanzando |
| **B · BC3/DXT5** | Compresor CPU + descompresor Vulkan como prueba de que la GPU ejecuta el shader propio | `04-IMPLEMENTACION/compressor|decompressor/` | `COMPLETE` salvo AD-12 |

`MASTER-RESEARCH-STATUS.md` de `00-INDICE/` es de la línea histórica de telemetría
(R-4B / D6 / C1, septiembre) y **no describe la línea A**. No usarlo como estado actual.

## OBJECTIVE

Cerrar, para Polaris12, la cadena completa — PCI → MMIO → MC/VRAM → GART → GPUVM →
PDE/PTE → page walker → VMID → TLB/invalidate → PM4 → IB → CP → rings → fences/IH →
SDMA → shaders → reset/recovery → power/thermal — sin depender de ninguna suposición
no identificada. Cada capa con estado explícito: `PROVEN` / `CORROBORATED` /
`NOT_DETERMINED`.

## CURRENT PHASE

**Fase A ·_tracker `STATIC`_, GFX8 execution + memory core.** La geometría de page
table, el productor de PTE, la secuencia de vm-flush, el presupuesto de dwords del
ring y la codificación PM4 están **cerrados sobre el corpus**. El path de invalidación
de TLB **no puede** dar completion observable por software con los registros
publicados: eso ya no es una pregunta abierta, es `NOT_IMPLEMENTABLE` (§`PROVEN`
en `018`). Lo que sigue abierto es **qué garantiza el hardware** durante el intervalo,
que es RUNTIME.

Fase B cerrada. Fase D (GPUVM/PTE/VMID/PTBA) **cerrada en software**; pendiente el
lado hardware.

## CURRENT VERIFIED STATE

Verificado por lectura directa el 2026-10-01. Detalle y evidencia en
[`CURRENT-STATE.md`](CURRENT-STATE.md).

```
HOST        Nobara Linux 44 · kernel 7.1.3-200.nobara.fc44.x86_64 · Mesa 26.2.3
GPU         1002:699f rev c7 en 0000:01:00.0 · amdgpu · card1 · renderD129 · hwmon1
IGPU        8086:0412 Intel HD 4600 en 0000:00:02.0 · i915 · card0 · renderD128
VRAM        2147483648 B total · 268435456 B visible (BAR0) · 6194642944 B GTT
PARAMS      vm_size=-1 vm_fragment_size=-1 vm_block_size=-1 vm_update_mode=-1
GPU INTACTA nhwa NO cargado · rx550* NO cargado · MODIFICATIONS=0 en el corpus
```

**El driver propio no está cargado ni se ha cargado nunca.** `lsmod` no muestra
`nhwa` ni ningún módulo `rx550`. Todo lo de la línea A es análisis de código.

## KNOWN HARDWARE

`PROVEN` por lectura del corpus y por `lspci`/`sysfs` de esta host:

```
ASIC            Polaris12 / GFX8 · gfx8 · GC_HWIP 8.0.0 · CHIP_POLARIS12=17
SE / CU / RB    2 shader engines · 8 CU · CU mask 0x1e · 4 RB
VRAM            2 GiB · fragment_size 9
GMC             gmc_v8_0 (gmc_8_1_d.h) · gfxhub vía gfx_v8_0 (gmc_8_2_d.h)
SDMA            sdma_v3_0 · SDMA_OP_GEN_PTEPDE = opcode 12 (vid.h/sid.h)
VM              num_level=1 · root_level=AMDGPU_VM_PDB0 · max_level=1 (parámetro)
                max_bits=40 · vm_size=64 GB · max_pfn=16777216 · block_size=10
BAR             256 MiB · vram_full_visible=FALSE → el writer CPU de PTE es
                inalcanzable bajo la política efectiva (vm_update_mode efectivo 0)
GART            geometría cerrada · placement BEST_FIT · base alineado a 4 GiB
                · gart_end derivado tras la alineación · hole vía max_mc_address
ATC             sin granularidad de invalidación en GFX8: 16 bits, un bit por VMID
```

**Corpus de referencia** (`CORPUS=`, se cita en cada finding):

| Ruta | Qué es | sha256 |
|---|---|---|
| `RESEARCH/working/linux-7.1.3/` | árbol de trabajo, == baseline | MANIFEST en `RESEARCH/baseline/MANIFEST.sha256` |
| `RESEARCH/baseline/linux-7.1.3/` | subárbol congelado del tarball | idem |
| `RESEARCH/kernelbuild/linux-7.1.3/` | headers instalados | `include/drm/amd_asic_type.h` = `cea577df…7809` |
| `rx550-upstream-7.2.8/linux-7.2.8/` | upstream 7.2.8 | tarball `12e8d5a9…941e` |

`local.sha256` == `upstream.sha256` en `rx550-upstream-7.2.8/`: **el árbol "local" es
upstream prístino, sin parches locales**. `RESEARCH/patches/` está vacío. Nadie ha
parcheado el driver de referencia en este repo.

## KNOWN SOFTWARE ENVIRONMENT

`/usr/bin/spirv-val` y `/usr/bin/glslangValidator` **sí están instalados** (se dijo
falso en su día; corregido en `49bd550`). ICD Vulkan presentes: `radeon_icd.x86_64`
(RADV) entre 22 más. `strace` `NOT_AVAILABLE` — no se instaló y no se cuenta como PASS.

## PROVEN

Con `EVIDENCE → archivo:línea → finding`. Detalle en [`EVIDENCE-MATRIX.md`](EVIDENCE-MATRIX.md).

| # | Afirmación | Evidencia |
|---|---|---|
| P1 | El path de **ring** no puede observar completion de `VM_INVALIDATE_REQUEST`: no hay registro de ack, y `WAIT_REG_MEM` se emite con `FUNCTION=0 (always)`, `ref=0`, `mask=0` — ningún bit comparado | `017` §3; `gfx_v8_0.c:6199-6207` |
| P2 | Por tanto la **espera explícita** de completion del invalidate es `NOT_IMPLEMENTABLE` con este juego de registros. El *orden* respecto al siguiente IB sigue `NOT_DETERMINED` y sí es medible | `018` §CUDA |
| P3 | `VM_INVALIDATE_REQUEST` en GFX8 no tiene granularidad: 16 bits, un bit por VMID, sin selectores L1/L2/4K. `flush_type` y `vmhub` son parámetros muertos en `gmc_v8_0_flush_gpu_tlb` | `019` §CUDA; `gmc_v8_0.c:661-666` |
| P4 | El **writer de page tables de GFX8 es un paquete SDMA de 9 dwords**, `SDMA_OP_GEN_PTEPDE`. El writer CPU existe y es correcto, y está cerrado por diseño. **No hace falta escribir un PTE a mano: hay que emitir un paquete** | `023-pte` §CUDA; `sdma_v3_0.c` |
| P5 | `AMDGPU_PTE_PRT` no es un tipo de entrada en GFX8: bits 40-63 reservados, y el driver lo borra (`&= ~PRT`). El mecanismo equivalente es el aperture de rango `mmVM_PRT_APERTURE*` | `023-pte` §3; `gmc_v8_0.c:792-810` |
| P6 | `emit_frame_size` de GFX8 **reserva el peor caso**, no el caso activo: 172 dw (GFX) / 109 (compute). `CE_META`/`DE_META` reservan la variante `chained_ib`, condicionada a `amdgpu_sriov_vf` = falso en una Polaris12 física | `021-frame`; verificado con `pm4dw`: declarado 172 / 109 |
| P7 | `ring_funcs_gfx` y `_compute` **sobre-reservan 5 dwords**; `ring_funcs_kiq` coincide exacto. Causa: `VI_FLUSH_GPU_TLB_NUM_WREG = 3` (`vi.h:27`) frente a **2** llamadas reales a `emit_wreg` en `gmc_v8_0_emit_flush_gpu_tlb` (`gmc_v8_0.c:678,681`). Sobre-reserva es correcto; **ningún ring está infra-reservado** | `020`; recountado con `pm4dw` y con lectura directa |
| P8 | La convención de encoding `PACKET3(op, n) → n = payload − 1` es una **propiedad medida**: 68/68 emisiones contables del path GFX8, 170/171 del árbol amdgpu completo. Herramienta con discriminante (mutante `payload+2` → 1/172, rc=1) | `023-pm4-count`; reejecutado |
| P9 | `COND_EXEC` en GFX8 **se emite y no puede hacer nada**: el predicado se inicializa a 1 y los 20 call sites que lo bajan a 0 son de preemption, que GFX8 no tiene. `dw4` **es el cuarto payload**, no un extra | `022` §CUDA, enmendado por `023-pm4-count` |
| P10 | La geometría de page table de Polaris12 queda numérica: `num_level=1`, `block_size=10`, `fragment_size=9`, `max_pfn=16777216`, PTB = 1024 entradas (8 KiB), PDB0 = 16384 entradas (128 KiB), GPUVA 36 bits. **La cadena derivada coincide palabra por palabra con la línea que el host imprimió en el boot** | `gfx8vmgeom` (37 aserciones, 12 controles negativos vivos); `024` §2 |
| P11 | `num_level = 1` viene de `max_level = 1`, un **argumento del driver**, no de una limitación del silicio. `DRIVER-MISSION-STATE.md` ("modelo plano por necesidad") queda `REFUTED` en esa mitad | `024` §6 |
| P37 | **Este ASIC despacha sus PTE con `sdma_v3_0`, no con `sdma_v4_0`.** `vi.c:2113` mete `sdma_v3_1_ip_block` para `CHIP_POLARIS12`, y ese bloque declara `.funcs = &sdma_v3_0_ip_funcs` — **no tiene fichero propio**, es un alias dentro de `sdma_v3_0.c`. El emisor de referencia escribe `count`, no `count - 1`. Lo confirmó el `dev_info` del host: `<sdma_v3_1_0> (sdma_v3_0)` | `C-011`, `RE-32`. **Y el error ya está compilado en `rx550_pm4.c:277`** |
| P45 | **`ipsolve`** resuelve el gate que `RE-39` declaró ausente: qué `.c` implementa cada bloque de IP **para un ASIC dado**, siguiendo el puntero `.funcs`. Verificado por mí: `--selftest` **12/12**, y `--bootlog` contra el kernel en ejecución da **9 de 9 bloques** con `rc=0` en ~25 s. `--expect` es puerta de CI. Confirmó mecánicamente `C-011`, `051` y `046`, y descobriu un dato nuevo: **DisplayCore está compilado y activo** en este host, y el caso VI de `vi.c` no tiene rama `else` para `dce_v10_0` | `TL-11`, `RE-41`. **7 defectos los encontró en sí misma**, incluido no manejar el *fall-through* de C |
| P47 | **La caja de herramientas tiene 44 fuentes en DOS directorios**, no 26 en uno: `pm4_count_census`, `count_vmflush_dw` y `frame_budget` se mudaron a `08-ARQUITECTURA/tools/` y se documentaban como entradas TL de `tools/`. Estado medido: **PASS 15 · NO_SELFTEST 19 · NONZERO 2 · REFUSED 7**, y **12 documentadas de 44**. 13 aparecieron *entre dos ejecuciones* del registro. Hay **dos convenciones de contrato** distintas (`WORK_CLASS=` frente a `# CONTRACT:`) | `RE-44`, `TL-13`. La cifra de PASS es 15 de 44, no 44, y así hay que leerla |
> **AVISO DE NOMBRE, y es una contradicción sin resolver.**  Nueve de los quince
> ficheros de `docs/` tienen un homónimo en otra parte del árbol, y los de la raíz los
> está escribiendo otra sesión EN PARALELO desde el 2026-10-02.  El censo documental
> del proyecto apunta al `00-INDICE/MASTER-RESEARCH-STATUS.md` de 64 kB, no a este de
> 49 kB.  Ver `C-012`.  Quien pida un documento por su nombre puede abrir el que no
> es.

| P60 | **El vocabulario cerrado de `TYPE` era decorativo: 12 de 51 claims (24 %) tenían prosa dentro del campo**, y `STATE` estaba limpio. Cada anotación era cierta y útil donde estaba —`DERIVATION + NEGATIVE_RESULT`, `OBSERVATION, con medición propia`— y nadie dijo que dejaba el campo ilegible: **las doce se escribieron así porque el vocabulario era una lista y no un check**. Normalizado a un token, con la información mudada a `ALSO`/`NOTA`, y `docscan.check_taxonomy` ahora falla si un token válido lleva prosa detrás | `TL-46`, `NR-14`, `R-31`. La regla la propuso el hallazgo `071` de otra sesión: *«un `not found` sin cota no es una medida: es un olvido»* — y **el bug de `drift.py` era una instancia de la suya**: un método de búsqueda que no alcanza, usado para afirmar una ausencia |
| P59 | **`F3d` estaba ARREGLADO en el código y mi documentación seguía diciendo que no**. Leyendo `rx550_pm4.c` para responder a la pregunta que `revkit/PTEPDE-GFX8.md` dejó escrita y nadie había contestado: `:298` escribe **`count`**, y la función replica `sdma_v3_0.c:986-996` **dword a dword** —las diez, en orden— con `RX550_SDMA_PTEPDE_DW = 10` concordando. Las diez apariciones de `count - 1` que quedan en `07-DRIVER/` están en **comentarios y tests** | `RE-52`, `R-30`, `F3d` CORRECTED. Actualizado en `OPEN-FRONTIERS`, `IMPLEMENTATION-STATUS`, `CONTRADICTIONS`. **Nada borrado**: el defecto existió y se detectó tarde, y eso prueba que una suite verde puede no ver un error de un byte en el argumento de un emisor de DMA |
| P58 | **`FINDINGS-INDEX.md` tenía 48 hallazgos sin indexar de 114 — la forma que tiene aquí la documentación vieja: el árbol crece varias veces por hora y el documento no le sigue**. `docscan --index` añade las 49 filas que faltaban, insertadas tras la última fila de la tabla —porque el fichero tiene prosa después— y **cada una marcada `NO LEIDA`**: el título es transcripción, no juicio, y un índice que presentara 49 hallazgos «documentados» sin decir que nadie los abrió mentiría por formato | `TL-45`, `R-29`. La primera versión puso `CUDA principal` en las 49 filas:tomaba el primer H2 y ese H2 es siempre el mismo. Indexar también hizo aparecer, solo, que el hallazgo `043-asercion-struct-mqd-contra-offsets` y la herramienta `gccverify.py` son el mismo problema desde dos direcciones |
| P57 | **Las 76 herramientas de otras sesiones que `docs/` no citaba ya son localizables con un grep**: `TL-43` las transcribe desde su propia cabecera con ruta, tamaño, contrato declarado y primera frase. **`98 → 0`**, y la primera cifra era una inflacción mía: la detección exigía acentos graves y no veía las menciones en texto plano, así que contaba como no vistas hasta mis propias herramientas con `TL-01` incluida. Es la tercera vez que este proyecto se infla una cifra al medir | `TL-43`, `R-28`. El método ahora va impreso junto al número, y hay un check que acepta las tres formas de escribir un nombre. Y `TL-44` documenta `gccverify.py`, que **pregunta al compilador** —la autoridad sobre ABI— y distingue `NO_COMPILE` de fallo de layout |
| P56 | **`drift.py` mide la variable que faltaba: si el árbol se movió bajo la documentación**. Descubrió que el registro conoce **2** directorios de herramientas y el repositorio tiene **7**, con **76 guiones sin documentar** —incluido `revkit/` entero, 18 guiones y 5928 líneas, cero documentados—. Y encontró una contradicción **que causé yo**: existe un censo documental `DESIGN_FROZEN` de 1576 filas, **0 de mis 15 ficheros** están en él, y los dos únicos matches aparentes son **otros ficheros con el mismo nombre**. Nueve de mis ficheros tienen homónimo, y además **otra sesión escribe un segundo índice en la raíz desde hoy** con seis de esos nombres | `TL-42`, `R-27`, `C-012`. **No se arbitra leyendo**: es decisión de coordinación. Se registra, se desambigua en lo propio, y se escribe la fila que falta sin aplicarla |
| P55 | **`constmap.py` comprueba las 43 constantes de `rx550_pm4.h` contra la línea upstream que cada una cita en su propio comentario**: `AGREE 15 · AGREE_DISCRIMINATING 8 · AGREE_COMMENT 4 · WITNESS_USAGE 3`, y **`DISAGREE 0`** — los 32 con testigo quedan cuadrados, sin veredicto sin explicar. Eso **acota F3d**: la capa de constantes está limpia, y el defecto de `rx550_pm4.c:277` está en el `.c` y es **simbólico, no de valores**. Y casi lo dije al revés: vi dos citas apuntando a `amdgpu_ring_write` y escribí «dos citas equivocadas» — `gfx_v8_0.c:6047` **es** el `PACKET3_WAIT_REG_MEM` de la función correcta | `TL-41`, `R-26`, `RE-51`. Tercera guarda que se detecta a sí misma en este proyecto: el arreglo fue una guarda **inmune al texto** |
| P54 | **`citations.py` resuelve las 2398 citas `fichero.c:N` del texto propio y dice cuánto pesa cada una**: `ROBUST 1070 · VERSIONED 839 · UNIDENTIFIABLE 261 · FRAGILE 135`. Con eso corrigió **una alarma suya**: la primera medición dio `1116 FRAGILE = 47 %`, y era casi todo artefacto de contar 7.1.3 y 7.2.8 como una sola versión. Medido de verdad, **130 de 135** caen en los cuatro ficheros que una sesión instrumentó, y se traducen con delta **constante** (`amdgpu_vm.c +12`, `amdgpu_vm_pt.c +26`) —el par `+0` identifica el prístino por construcción, sin que la herramienta elija. Corrobora por otra vía lo que `working-vs-kernelbuild-difference.md` ya probó por hash, y añade lo que a ese fichero le faltaba: la **exposición** | `TL-40`, `R-25`, `RE-50`. `UNIDENTIFIABLE 261` son la trampa: `vi.h:27` resuelve también a la cabecera de un driver Tegra |
| P53 | **`snapshot.py` sella `PRE-STATE · POST-STATE · DIFF` del ciclo de experimentos, la parte que no dependía de autorización**: el hash cubre **solo los hechos estables**, así que dos capturas seguidas dan el mismo `stable-id` y un diff informa de cambios reales. Arbitrado contra el kernel: **3 `AGREE`**. Al arbitrar encontró **dos defectos que ningún fixture podía ver**: fotografiaba la **iGPU Intel** `0x8086:0x0412` en vez de la RX550, y su dirección PCI era el **puente** `0000:00:01.0`, no el dispositivo `0000:01:00.0` — un valor plausible que no se delata | `TL-39`, `R-24`. La ausencia ahora se **escribe** `<ausente>` y se cuenta: el silencio era lo que tapaba al error. **Seis** defectos en sí misma, y el último la inutilizaba: `tools_git_head` estaba en el hash, así que un commit ajeno movía el id sin que la GPU cambiara |
| P52 | **`claim.py --locate` trae los `fichero:línea` que la evidencia de una claim ya cita, sin elegirlos**: `FETCHABLE 0 · ADVERTISED 11 · MANUAL 14`. Cerró `RE-10` con seis líneas medidas, entre ellas `gmc_v8_0.c:1127` —donde `amdgpu_vm_adjust_size(adev, 64, 9, 1, 40)` muestra las **entradas como argumento literal**, la evidencia más fuerte posible—. Y corrigió **una afirmación mía**: dije que 15 de 25 citaban un finding con `LOCATION` declarada, y son **0** | `TL-38`, `R-23`. Traer ≠ elegir: `691` y `702` son líneas reales |
| P51 | **24 de 47 claims del registro no son auditables por la regla del propio proyecto**: tienen `SOURCE` (de quién es) pero no `LOCATION` (dónde está). El 51 %. Y el ejemplo duele: **`RE-10`**, la claim que sostiene `block_size`, `num_level`, `root_level` y el tamaño de la page table —la más citada del registro— no tiene ni una línea de código. Verificado a mano sobre RE-10/17/19 para descartar artefacto del parser | `RE-49`, `TL-37`. No es que sean falsas: es que no son **comprobables** |
| P50 | **28 de 95 findings no estaban citados por nada en `docs/`** — 29 % de la evidencia del proyecto sin registrar, y entre ellos un **segundo testigo independiente de `C-011`** (`043`) y tres que **corrigen una fila mía** sobre `src_data[0]`. Se cerró con dos claims nuevas: `RE-47` y `RE-48`. `claim.py` mide esa cobertura y **no puede escribir** (su self-test legaliza su propio fuente) | `TL-37`, `R-22`. La cobertura casa por nombre completo, no por número: hay 27 colisiones de índice |
| P49 | **`round` automatiza el paso que decidió `C-009`, `C-010` y `C-011`**: leer un finding nuevo, extraer sus cifras y arbitrarlas contra el autoinforme del kernel. Verificado sobre el árbol real: encuentra **`block_size = 22` contra el 10 del kernel**, desde el §CUDA del finding, en un comando. Compone `docscan` + `toolreg` + `causal_map` en vez de reimplementarlos. **Clasificado `TOOL_PARTIAL`**: recall de 7 claims sobre 92 findings, declarado | `TL-35`, `R-21`. Su detector de conflictos propio se descartó: `causal_map` ya lo hacía mejor |
| P48 | **`msg_census` sobreestima los mensajes SMC en 36×, y su self-test pasa.** Titular: 503 sitios de envío. Sus propios veredictos: `VIVA 11 · MUERTA 5 · NO_CONDICIONAL 487`. Realidad: el fichero activo es `polaris10_smumgr.c` con **14** sitios, que resuelven **14/14** contra `smu7_ppsmc.h`. El incidente ya estaba registrado en la cabecera de `toolcheck.py` y **sigue vivo**. Hay una línea H activa ahora mismo | `RE-43`, `TL-14`. El filtro que le falta ya existe en `pm4census.py` |
| P46 | **`docscan`** convierte la ronda documental en comando: 7 comprobaciones con severidades `defect`/`stale`/`review`, `--sync` para los contadores, y `--json`. Verificado por mí: `12/12` self-test, `defect 0`, `rc=0`. **Encontró un error mío de inmediato**: yo escribí `TRACKED 0 de 87` por un `git ls-files` hecho desde `docs/` sin `-C`; la realidad era 38. De ahí `--sync`, que mide y corrige juntos, informa cada sustitución y es idempotente | `TL-12`, `RE-42`. 7 comprobaciones |
| P43 | El **vector de interrupción de GFX8 queda decodificado por completo**: `src_id` dice **qué**, `vmid`+`pasid` dicen **quién**, `src_data[0]` dice **dónde**. Para faults de traducción son **exactamente dos** SRCID —`0x92` y `0x93`, contiguos, mismo handler—, no un rango. Y la tabla tiene **112 vectores, ninguno catalogado** en el proyecto | `052`, `RE-40`, sobre `RE-36` |
| P44 | **`asic_resolver`** convierte `COMPILE_GATE_BEFORE_TRACE_GATE` de regla recordada en **comando ejecutado**. Verificado por mí: `--selftest` → `RESULTADO OK`, `rc=0`, y la herramienta avisa ella misma que *"pasar esto NO valida la semántica del hardware"*. Detecta por máquina el error de `050` (`CHIP_POLARIS10 = 15` ≠ nuestra `17`) y cuenta que **15 de 39 ramas de `smu7_hwmgr.c` no se ejecutan** en nuestra tarjeta | `053`, `TL-10`, `RE-39` |
| P42 | La **circularidad** del test propio estaba declarada: el codificador se escribió leyendo amdgpu y las expectativas se transcribieron del **mismo** amdgpu, así que un error de lectura replicado pasa las comprobaciones. `035` es exactamente eso. Se rompe con `rx550pm4val.c` + `rx550_pm4_emit.c`: valida **estructura** sin acceso al corpus. **Y declara su propio límite**: acepta `count` donde espera `count-1`, y lo dice escrito | `038`, `RE-37`. Corrobora `C-011` desde dentro |
| P40 | El vector de interrupción de GFX8 son **16 bytes, 4 dwords** (`tonga_ih.c:248-270`): `src_id` 8 · `src_data[0]` **28** · `ring_id` 8 · `vmid` 8 · **`pasid` 16**, ese último packed en `dw2[31:16]**. Es el **único punto donde el hardware reporta un PASID** en toda la arquitectura, y `client_id` **no es un campo del vector**: se fija a `AMDGPU_IRQ_CLIENTID_LEGACY` | `051`, `RE-36` |
| P41 | **El nombre del `ip_block` en el log de arranque NO predice el nombre del fichero.** Tres casos con la misma forma: `<sdma_v3_1_0> (sdma_v3_0)` sin `sdma_v3_1.c`; `<ih_v3_0_0> (tonga_ih)` sin `ih_v3_0.c`; `<gmc_v8_1_0> (gmc_v8_0)`. Es un **número de versión**, no un nombre. Para localizar el código hay que seguir `.funcs`, que es un símbolo | `051` lo dice textual, y es la regla que este árbol aprendió a costa de `C-011` |
| P39 | **El bloque MMU/VM de GFX8 no está publicado por AMD.** El índice oficial de arquitectura enumera **14 documentos**: 13 ISA de shader, 1 de firmware de scheduler. **Ninguno** trata MMU, TLB, page walker, formato de PTE ni orden de invalidación. Y no es descuido de indexado: el propósito que AMD declara para un ISA es *"compiler writers"* | `033-mmu-vm-no-publicado`, `RE-34`. `NOT_PUBLISHED`, que es más fuerte que `NOT_DETERMINED` |
| P38 | `046` **refuta la línea H entera tal como estaba escrita**: `si_dpm.c` y `si_smc.c` **no se compilan para Polaris12** (`legacy-dpm/Makefile:28`, solo bajo `CONFIG_DRM_AMDGPU_SI`; y `DRM_AMDGPU_VI` ni existe). La ruta real es **PowerPlay + `smu7` + `polaris10_smu_funcs`** (`hwmgr.c:154-158`). El control de energía de este ASIC son **tablas de voltaje por dominio** (`polaris10_smumgr.c:664/691/716`), no curvas A-T: `calculate_at`, `calculate_u_and_p`, `bsp` y `ClockVoltageDependency` tienen **0 ocurrencias** en la ruta activa | `046`, y medido |
| P34 | **La especificación PM4 de GFX8 NO EXISTE.** Existe la fuente primaria —*Reference Guide, Graphics Core Next Architecture, Generation 3*, rev. 1.0 (2015-03), **637 páginas**— y se **contó**: cero apariciones de `PACKET3`, `PKT3`, `RELEASE_MEM`, `COND_EXEC`, `VM_INVALIDATE`, `INT_SEL`, `WRITE_AT`, `GRBM`, `mmCP`. AMD nunca publicó el framing PM4 para GCN3 | `033-pm4-spec` §1. `NEGATIVE_RESULT`, y es `PROVEN` con la causa nombrada |
| P35 | El **framing** PM4 de GFX8 queda cerrado: `F = datos − 1`, paquete = `F + 2` dwords. Es decir, `n` se cuenta sobre el **total**, no sobre los datos — que era la ambigüedad que `RE-08` dejaba abierta. Tres casos del corpus, `WAIT_REG_MEM` ×3 | `033-pm4-spec` §3. `PROVEN_DERIVED` |
| P36 | Una aserción de freedreno queda **`REFUTED`**: `pkt_is_type3` exige opcode `< 0x80`, pero hay **12 de 74** opcodes PACKET3 de GFX8 ≥ `0x80`. Once tienen cero usos; **el superviviente es `SWITCH_BUFFER` (0x8B), con 13 usos y vivo** | `033-pm4-spec` §4. Contraejemplo vivo |
| P33 | Antes de GMC v9 **no hay huge pages**: el driver se niega a usar un nivel no-hoja como hoja, literalmente. `PAGE_TABLE_BLOCK_SIZE` existe en el registro pero **no se usa como tamaño de bloque**. Recorta el espacio de diseño del driver propio | `030-page-walker` §CUDA, `amdgpu_vm_pt.c:825-832` en 7.2.8 / `:840` en 7.1.3 |
| P12 | `PAGE_TABLE_DEPTH` recibe **valores distintos en el mismo campo**: `0` para el contexto 0 (GART) y `1` para los contextos 1-15. El corpus no declara qué significan | `024` §3 |
| P13 | El path **GART** sí tiene completion observable, y no por hardware nuevo: lo ejecuta la CPU (`mb()` + `flush_hdp`), así que el retorno de la función *es* la sincronización | `025` §CUDA; `amdgpu_gart.c:492-506` |
| P14 | `AGENTS.md:169` ("WAIT_REG_MEM espera REQUEST == 0") es `REFUTED` a nivel de encoding: confundió `ref=0` con una comparación contra cero. Sobrevivió de `017`: mecanismo de invalidación, request por VMID, y "no es prueba de completion" | `017` §4 |
| P15 | La ruta máxima de `amdgpu_vm_flush` en el ring GFX es **63 dw**, y es **alcanzable**: las cuatro ramas coexisten porque `amdgpu_vm_flush` fuerza cuatro flags a la vez tras un reset de VMID, y son campos distintos del job sin exclusión mutua. Reserva 172, **ninguna infrarreserva** | `025-vm-flush` §CUDA, con `pm4dw --path` |
| P16 | El frame completo de GFX8 son **121 dw** (137 con chained IB), y la reserva de un envío son **dos sumandos**: `emit_frame_size + num_ibs * emit_ib_size` (`amdgpu_ib.c:197-198`). Alcance con 51 dw de holgura. **Seis ramas del camino de envío no existen en GFX8** | `026-frame` §1, §CUDA |
| P17 | `write_multiple` emite **17 dwords**, no 1. La fuente del tamaño es `vi_structs.h`, que documenta los payloads de metadatos en DWORD exactos y que nadie estaba usando | `026-frame` §CUDA; sustituye a `NR-07` |
| P18 | El **fence sí tiene completion**, y es el único punto del path de submit donde el hardware confirma que el trabajo anterior terminó. Tres formas: GFX `EVENT_WRITE_EOP` ×2, COMPUTE `RELEASE_MEM` ×1. Cambia en cada generación | `028-fence` §CUDA, §1 |
| P19 | El PTBA de GFX8 sale de **una sola operación** sin código condicional: `asic_type(17) >= CHIP_VEGA10(19)` es falso, luego `pd_addr = amdgpu_bo_gpu_offset(bo)` | `027-ptba` §CUDA |
| P20 | El PTE de GFX8 direcciona **40 bits de PA por tres vías**; los flags sólo constan por comentario | `026-pte` |
| P21 | `RELEASE_MEM` en GFX8 **no tiene campo de número** (`PACKET3(...,5)`, 6 payload) frente a GFX9 (`PACKET3(...,6)`, 7 payload, con un dw extra). Por eso no necesita el `seq − 1` que exigían GFX7/8: es estructural, no paramétrico | `029-release-mem` §CUDA |
| P22 | `emit_cleaner_shader` es un predicado **permanentemente falso** en Polaris12: `ring->funcs->emit_cleaner_shader` es NULL. No es un `if` que pueda activarse. Elimina una rama entera del espacio de diseño | `025-vm-flush` §7 |
| P23 | El **writeback buffer** son 1024 slots y cada ring pide 5. Cuatro se liberan en `amdgpu_ring_fini`; **`trail_fence_offs` no**. Fuga en el driver de referencia, con modo de fallo duro. Este repo no modifica `amdgpu_ring.c` | `030` §CUDA. **Sólo se leyó esa sección** |
| P24 | **Censo completo de los flags de PTE de GFX8, con productor y estado por bit.** `VALID`, `SYSTEM`, `SNOOPED`, `READABLE`, `WRITEABLE`, `EXECUTABLE`, `FRAG` (11:7) y `PDE_PTE` (54) se escriben. `PRT` (51) es `CLEARED_NOT_SET`: nadie lo pone y el único que lo menciona lo borra. `LOG` (55), `TF` (56), `NOALLOC` (58), `BFS` (59), `IS_PTE` (63) son `OTHER_GEN` | `pteflags` census: 19 aserciones, 0 fallos, 5/5 controles negativos |
| P25 | El contraste que hace que el censo signifique algo: `MTYPE_UC` **no existe en la TU de `gmc_v8_0.c`** y sí en la de `gmc_v9_0.c`. No es que GFX8 decida no escribirlo: es que el símbolo no existe en su unidad de traducción, luego no podría escribirlo aunque quisiera | `pteflags` §informe |
| P27 | **Censo de `write_multiple` resuelto por herramienta**: `vi_ce_ib_state` 4 dwords → `ce_meta` emite **8 dw** activo / **14** con chained IB; `vi_de_ib_state` 17 → **21** / **31**. Las cuatro cifras coinciden con las que `021-frame` dedujo a mano seis horas antes: `CORROBORATED`, no duplicado | `027-write-multiple` + `pm4dw --struct-size`, verificado contra el código |
| P28 | `PROTECTIONS` es un campo de **8 bits que el hardware rellena y el driver de referencia no descompone** en el camino GPUVM: el decode estructurado existe en UN solo punto de todo el driver y está tras un gate de KFD. GFX6 y GFX7 tampoco lo descomponen. **Esto renombra el bloqueo de `F2b`**: no es sólo que falte la spec, es que el observador de referencia no produjo el dato en el camino relevante. Un driver propio tendrá que **inventar su propia decodificación**, y no puede heredar la de KFD | `033` §4, §5 |
| P29 | El **layout del PTE de GFX8 tiene una sola fuente**: el comentario de `gmc_v8_0.c:691-702`, **sin corroboración en ninguna cabecera ASIC**. Ningún finding anterior lo decía | `033` §6 |
| P30 | La L2 puede **byte-swappear PDE y PTE por separado** (`PDE_ENDIAN_SWAP_MODE` MASK 0x30, `PTE_ENDIAN_SWAP_MODE` MASK 0x0c, presentes de `gmc_6_0` a `gmc_8_2`) y el driver de referencia **no los programa**. Relevante para un driver propio que ponga la tabla en VRAM en vez de GTT | `033` §7. Colateral, `NOT_IN_ANY_DOC` hasta ahora |
| P31 | El completion del fence **no usa ninguna barrera en el camino de lectura**: `le32_to_cpu(*drv->cpu_addr)`, sin `mb()`, sin `readl()`, sin `volatile`. La garantía está en que la página es **coherente por construcción**, por el `pin` del BO. Cierra `031 §4`, que estaba `NOT_DETERMINED` sin causa | `032` |
| P32 | **El driver NO escribe los registros de reloj de GFX8.** Calcula un payload de nivel de rendimiento, lo serializa, lo sube a la SRAM del SMC, y es el **firmware del SMU** quien aplica el cambio. Y entre pares de niveles **no envía frecuencias: envía una banda de histéresis `[t_l, t_h]`** por la que el firmware decide. Abre la **línea H**, que hasta ahora tenía 0 findings | `040` §CUDA, `041` §CUDA |
| P26 | El estado de control de un ring vive en **tres dominios de memoria** — `ring->ring` (GTT), `wptr_cpu_addr` (GTT) y `doorbell.cpu_addr` (BOORBELL, MMIO) — y la secuencia de commit los recorre **sin un único `mb()` explícito** en el path del ring. El hardware recibe el timbre y necesita leer `wptr`, que está en otra página y otra BO | `031` §CUDA. **Sólo se leyó esa sección** |

## REFUTED

No volver a investigar sin contradicción nueva:

| Afirmación refutada | Por qué | Dónde |
|---|---|---|
| "WAIT_REG_MEM espera `REQUEST == 0`" | `FUNCTION=0` es `always`; con `mask=0` no hay comparación posible | `017` §4, contra `29⁄9⁄26.md:169` |
| "Esperar el completion del invalidate es una investigación pendiente" | No hay registro de ack en GFX8: es `NOT_IMPLEMENTABLE`, no `NOT_DETERMINED` | `018` |
| "`dw4` de `COND_EXEC` es un dword extra fuera del payload" | Es el cuarto payload; `n = payload − 1` en 68/68 | `023-pm4-count`, contra `022` §4 original |
| "El agreement test BC3 no pasa, 57 de 64 bloques difieren" | Pasa: 0 de 64 bloques, 0 de 4096 bytes, 3 corridas. Era el estado previo a AD-13 | `7ed1eca` (2026-09-29 01:17) |
| "El modelo de VM plano es una limitación del silicio" | Es `max_level = 1`, un argumento del driver | `024` §6 |
| `BITS_PER_LEVEL = 9`, `GPUVA_WIDTH_BITS = 30`, `MIN_VIABLE_ASPACE = 2 MiB` (`014-q1`, marcados `PROVEN`) | Los tres están mal: `block_size = 10` (1024 entradas), GPUVA 36 bits, 4 MiB. Eran la rama `num_level > 1`, que no corre | `2599c65` |
| `block_size = 22` (`030-page-walker`, que se declaraba *corrección*) | Contradice el `dev_info` del kernel en ejecución. Alimentó a `get_block_size` el `tmp` de **antes** de la línea 2427 | `C-009` |
| El emisor de PTE de Polaris12 es `sdma_v4_0`, con `count - 1` (`035`, implementado en `036`) | Este ASIC despacha por `sdma_v3_0`, que escribe `count`. `sdma_v3_1_ip_block` es un alias sin fichero propio | `C-011`, `RE-32` |
| La línea H se trazó sobre `si_dpm.c` / `si_smc.c` (`040`–`045`) | **Esos ficheros no se compilan para Polaris12.** La ruta es PowerPlay + `smu7` + `polaris10_smu_funcs`, y son tablas de voltaje por dominio | `046`, `P38` |
| "Falta la especificación PM4 de GFX8" / "Falta la doc del bloque MMU" | **Ninguna de las dos existe.** AMD no publicó el framing PM4 de GCN3 (637 páginas contadas, cero PM4) ni documento alguno sobre MMU/VM/TLB/page walker para GFX8. Es una restricción estructural, no una frontera pendiente | `RE-29`, `RE-34` |

## NOT_DETERMINED

Con la causa nombrada, que es lo que las hace accionables:

| # | Cuestión | Causa | Discriminante |
|---|---|---|---|
| N1 | Qué garantiza el hardware durante el intervalo `0x20` de un `WAIT_REG_MEM` sin predicado | **La spec no existe**, no está perdida: `RE-29`. El campo `PACKET3_COND_EXEC = 0x22` es opcode y nada más | RUNTIME: `WAIT_REG_MEM always` + `RREG32` de `REQUEST` entre IBs, con un VMID cuyo invalidate se retrase. **No autorizado**. Frontera F3c |
| N2 | Orden de ejecución del invalidate respecto al siguiente IB | `:018` cierra la *espera*, no el *orden* | RUNTIME |
| N3 | Qué significa `PAGE_TABLE_DEPTH` `0` frente a `1` | Ninguna cabecera ni comentario del árbol, y **la spec primaria no contiene PM4**: `RE-29` | `BLOCKED_BY_NEGATIVE_RESULT`. Medir, no buscar |
| N4 | Si el hardware GFX8 trata el bit 3 del PTE como reservado — lo que hace segura la línea `&= ~PRT` | Sin spec, y **la spec no existe**: `RE-29` | RUNTIME |
| N4c | La **correspondencia PTE → `PROTECTIONS`**: el PTE codifica 3 bits de permisos, el hardware reporta 8, y **el mapeo no existe en el corpus**. Dos hipótesis sin separador: A = `[3:5]` espeja R/W/X y `[2:0]` son subtipos de fallo; B = `[7:0]` es un Fault-ID opaco | `033` §4, con dos hipótesis A/B que nada separa | Producir un fault conocido y leer `PROTECTIONS` las separa. RUNTIME, y una de las pocas cosas que un runtime discriminaría sin la spec |
| N4b | **La semántica de hardware de cada bit de PTE** (VALID, SYSTEM, SNOOPED, EXECUTABLE, READABLE, WRITEABLE, FRAG, PDE_PTE). El *censo* está cerrado en RE-22 con productor y estado por bit; la *semántica* no, y el propio binario lo declara | Sin spec primaria. Frontera F2b | RUNTIME, y dependiente de F1 |
| N5 | Si la entrada `block_size − 9` se interpreta como "block_size" | `MASK 0xf000000`/`SHIFT 0x18` en GFX8 vs `0x78`/`SHIFT 3` en GFX9: el hardware **redefine el campo**. Es `MODEL_CHOICE` del driver | `BLOCKED_BY_NEGATIVE_RESULT`. Medir, no buscar |
| N6 | Efecto real de `VM_CONTEXT{n}_PAGE_TABLE_BASE_ADDR` sobre traducciones cacheadas; teardown de TLB; reutilizar tabla con TLB vivo | Requiere RUNTIME + confounders (TLB preexistente, `NO_INVALIDATION` en `ATC_VMID{n}_PASID_MAPPING` bit 30) | RUNTIME |
| N7 | **AD-12**: ¿el sampler del Polaris12 decodifica la rampa alfa BC3 con truncamiento o con `+3`/`+2`? | El proyecto entrega un encoder; el consumidor es el hardware. Error sistemático en el 82.9 % de los pares | Experimento GL preparado: textura DXT5 como color attachment de FBO, `glReadPixels`, 65536×8 = 1048576 observaciones, sin shader |
| N8 | `GFX_HWIP` de este shader en particular | El agreement test no consulta ni infiere la generación gfx | — |

## OPEN FRONTIERS

Detalle con pregunta, evidencia, evidencia faltante y test discriminante en
[`OPEN-FRONTIERS.md`](OPEN-FRONTIERS.md). Resumen de las que tienen más valor
informativo:

- **F1 · N1/N2 juntos**: una sola carrera PM4 que mida si el hardware ordena el
  invalidate antes del IB siguiente. Cierra dos fronteras y produce el único dato de
  ordenamiento que falta. **Bloqueada por autorización runtime.**
- **F2 · N7 (AD-12)**: único `NOT_DETERMINED` de la línea B, y el único cuya
  respuesta pueda obligar a **revertir una decisión ya tomada** (`AD-11`). Es la
  frontera con más consecuencia del proyecto.
- **F2b · N4b**: la semántica de hardware de cada bit de PTE. El censo ya está
  cerrado —`pteflags` verificó 19 aserciones y 5 controles negativos, y clasifica cada
  bit como `WRITTEN`, `CLEARED_NOT_SET` u `OTHER_GEN`—, así que lo que queda es
  exactamente lo que no se puede obtener estáticamente: qué hace el silicio con cada
  bit. **Es la frontera más grande que queda abierta, y es grande por defecto: son ocho
  bits.** Bloqueada dos veces, igual que F1.
- **F3 · P12/N3**: la asimetría contexto-0 / contexto-1-15 en `PAGE_TABLE_DEPTH` es
  el punto exacto donde el modelo plano del kernel y el de userspace divergen en el
  mismo ASIC. Sin primaria, no avanza.
- **F4 · cierre del driver Stage 1**: `07-DRIVER/kernel/rx550_drv.ko` compila y
  `check-drivers` verifica por `nm` que **es** driver PCI y que el `rx550.ko` viejo
  **no** lo es. Falta decidir si el char-device se retira. Sin runtime.

## ACTIVE BLOCKERS

| Bloqueo | Tipo | Qué lo levanta |
|---|---|---|
| Todo el discriminante de runtime (N1, N2, N4, N6) | `BLOCKED_BY_AUTHORIZATION` | Autorización explícita + ruta de recuperación independiente verificada (`SSH-RECOVERY-PATH-2026-10-01.md` está en `PARTIAL`, **1 de 3** condiciones) |
| N3, N5 | **`BLOCKED_BY_NEGATIVE_RESULT`** | **Cambiado el 2026-10-01.** No es "no hemos encontrado la spec": existe, se ha medido, y **no contiene PM4** (`RE-29`). La vía estática está agotada y correctamente cerrada. Lo que queda es RUNTIME |
| Los payloads de `COND_EXEC`, `RELEASE_MEM`, `VM_INVALIDATE_RESPONSE`, `INT_SEL=2` | **`BLOCKED_BY_AUTHORIZATION`** | Frontera `F3c`, nueva. El framing está cerrado (`P35`); el payload no está en ningún documento. Hay que medirlo. Comparte bloqueo con `F1` y puede ir en la misma submission |
| `PATCH-REGISTRY` / publicación | `DEFERRED` | `READY_FOR_GITHUB=NO`; sin remoto configurado |
| Estado documental de la línea A | `RESOLVED 2026-10-01` | Este `docs/` + reconciliación de `PROYECTO_STATUS.md` y `README.md` |

## ACTIVE EXPERIMENTS

Detalle en [`EXPERIMENTS.md`](EXPERIMENTS.md). **Ninguno en curso.**

Histórico cerrado: R-4A/R-4B/R-4C, M1, EP-05/06/08, F4-A v2.1/v2.2/v2.3,
`ep08-doorbell-suppression`, `minitest-7.3-B`. Veredicto R-4B v2.3 =
`INCONCLUSIVE` y `NO se reintenta S2`.

## AVAILABLE TOOLS

Estado, contrato, fallos conocidos y validación en
[`TOOLS-STATUS.md`](TOOLS-STATUS.md). Resumen de lo que **funciona hoy**:

| Herramienta | Para qué | Estado |
|---|---|---|
| `pm4_count_census.py` | Census de la convención `n = payload − 1` | `VALIDATED`, rc=0, 68 contables + 22 `UNKNOWN` con motivo |
| `pm4dw.c` | Conteos de dwords; `--struct` da cota superior, **`--path` compone la secuencia real** | `VALIDATED`; 3 correcciones de invocación documentadas; corregido durante esta ronda |
| `gfx8vmgeom` | Geometría GPUVM contra la línea del boot | `VALIDATED`: 37 aserciones, 0 fallos, 12/12 controles negativos |
| `frame_budget.py`, `count_vmflush_dw.py` | Presupuestos de dw | `TRACKED`, `PARTIAL`, superados en parte por `pm4dw --path` |
| `pteflags` | Censo de productores de flags de PTE, con estado por bit | `VALIDATED`: 19/0, 5/5 negativos. **Sin README**, y cwd-dependiente como `gfx8vmgeom` |
| `semref` | `DEFINITION` vs `CALL` de un símbolo | **`INVALID`** — Coccinelle vivía en `/tmp` y se perdió |
| `validate_rx550_final.py` | Captura read-only del host | `VALIDATED`, rc=0, `writes_to_system=false` |
| `evidence_search.py` | Búsqueda con universo declarado | `FUNCIONAL`, **sin Discriminación negative-test registrada** |

## RECENT STATE CHANGES

Ver [`CHANGELOG-RESEARCH.md`](CHANGELOG-RESEARCH.md) para el detalle. Lo que un
agente nuevo necesita saber de hoy:

```
10:12  020  sobre-reserva de 5 dw en vm-flush, causa en vi.h:27
10:28  021  emit_frame_size reserva el peor caso (172/109), no el caso activo
10:34  022  COND_EXEC inerte en GFX8
10:52  023p convención n = payload − 1 MEDIDA (68/68); 022 enmendado
10:52  feat gfx8vmgeom: la geometría de Q1 (014) era incorrecta
10:57  024  geometría de page table cerrada; refuta la mitad de DRIVER-MISSION-STATE
11:05  025g la ruta GART sí tiene completion observable
11:0x  pm4dw recibe --path; se leen 11:18, 11:25, 11:27, 11:40
11:18  024p documentación de la herramienta de conteo de emisión
11:15  026p el PTE de GFX8: 40 bits de PA por tres vías, flags sólo por comentario
11:25  027  el PTBA: una sola aritmética, de la ioctl al registro
11:27  025v la ruta de vm_flush son 63 dw, y las cuatro ramas coexisten
11:38  028  el fence SÍ tiene completion, y cambia en cada generación
11:40  026f el frame completo son 121 dw; la reserva son dos sumandos
11:44  029  por qué RELEASE_MEM no necesita seq−1, y qué queda muerto en GFX8
12:03  027  `write_multiple` deja de ser una bandera: `pm4dw --struct-size --wm-sites`
12:2x  032  la lectura del fence no usa barrera; la garantía está en el `pin` del BO
12:3x  033  `PROTECTIONS` es opaco en el camino GPUVM, y renombra el bloqueo de F2b
12:4x  040/041 LÍNEA H ABIERTA: el canal de mensajes al SMU, y la banda de histéresis
12:0x  DOCS este árbol; PROYECTO_STATUS y README reconciliados; FINDINGS-INDEX y
      AGENTS-ADDENDA creados
```

**Aviso de frescura — importante**: HEAD se movió **ocho veces** mientras se redactaba
este índice, de `ce88b5f` a `13f1b13`. Aparecieron findings nuevos **después** de que
empezara este trabajo: 024p, 025v, 026p, 026f, 027, 028, 029, **030** y **031**. Todo
lo que se ha podido verificar está incorporado; `030` y `031` sólo en su §CUDA, y
declarado como tal dos veces cada uno.

La lección operativa de esta ronda es que **el árbol documental de este proyecto se
mueve más rápido de lo que una sola ronda documental puede seguir**. Con tres sesiones
escritas, cada ronda de unas dos horas coincide con otra. La mitigación no es escribir
más rápido: es que cada fila lleve el nombre del finding que la respalda, de modo que
`grep -r` localice qué hay que re-verificar. Por eso este fichero no cita commits
sueltos en las tablas PROVEN: cita el finding.

### C-009 zanjada con el árbitro más fuerte que existe

El kernel **en ejecución** imprimió hoy a las 05:49:05:

```
amdgpu 0000:01:00.0: vm size is 64 GB, 2 levels, block size is 10-bit, fragment size is 9-bit
```

`block_size = 10`. Eso confirma `RE-10` y **refuta** las cifras 22/23/24 del finding
`030-page-walker`, que las daba como una *corrección* de un error anterior. Dos hallazgos
posteriores ya habían intentado corregir esta misma cifra —`024` con 13, y
`030-page-walker` con 22— y los dos se equivocaron de argumento en
`amdgpu_vm_get_block_size(tmp)`: alimentaron, respectivamente, `vm_size` y el `tmp` de
*antes* de la línea 2427. El valor que el código pasa es el de *después*: `2`.

Detalle y cadena en [`CONTRADICTIONS.md`](CONTRADICTIONS.md) C-009.

**La lección transferible, y es la más útil de esta ronda**: cuando dos sesiones tengan
hipótesis sobre el mismo número, no gana la que argumenta mejor — gana la que ha
comprobado contra el hardware. `block_size` ya lleva tres cifras sucesivas: 13, luego 22,
y el 10 que sí coincide con lo que la máquina imprimió al arrancar. Un árbol documental
sin esa disciplina acumula correcciones de correcciones, y la cuarta habría sido la que
sobrevive.

Al releer, comprobar `git log --oneline -1` primero. Si se movió, lo último
desactualizado son las filas P15-P33. Y C-009, que se resolvió por arbitraje del kernel
en ejecución: si el host reinicia con otro kernel, hay que repetir ese arbitraje, porque
`block_size` es un valor calculado en runtime y no una constante del silicio.

## CRITICAL DEPENDENCIES

```
PTE/PDE ←── SDMA_OP_GEN_PTEPDE (P4). El driver propio emite un paquete, no escribe memoria.
   └── depende de la geometría (P10) para saber cuántas tablas y de qué tamaño
VMID/PTBA ←── depende de P4 y de que el invalidate tenga efecto (N6, sin cerrar)
Submission ←── presupone el orden (N1/N2). Con P1/P2, la seguridad del path de ring
               depende de un invariante del propio ring, no de un handshake
GART ←── P13: tiene completion; y su geometría es independiente de la de GPUVM
ATC  ←── P3: sin granularidad. La pregunta "¿qué nivel de TLB?" no tiene encoding
```

Grafo completo con aristas y contraprestaciones en [`KNOWLEDGE-GRAPH.md`](KNOWLEDGE-GRAPH.md).

## NEXT TECHNICAL ACTIONS

Ordenadas por valor informativo, no por facilidad. Las tres primeras son
documentales y no tocan hardware.

1. **Resolver la contradicción de la línea B en `docs/CONTRADICTIONS.md` (`DOC-001`)**
   y verificar si la limitación #3 de `PROYECTO_STATUS.md` (`rc=0` con `[FAIL]`) sigue
   viva. Es lo único de la lista que puede dar un `FALSE` positivo en CI hoy.
2. **Re-ejecutar `test_decompress`** para tener una marca de `GPU == CPU` **posterior**
   a la corrección de AD-13 y no solo el texto de `7ed1eca`. Los
   `04-IMPLEMENTACION/work/*.decompress.log` que sí registran `0 de 16384` están
   **ignorados por git** (`.gitignore:78`) y no son evidencia versionada.
3. **Ejecutar F2 (AD-12)** — el experimento está escrito y no se ha hecho. Es la única
   frontera cuya respuesta puede obligar a revertir `AD-11`.
4. **Cerrar Stage 1** (`F4`): decidir el destino de `rx550.ko` (char device) ahora que
   `check-drivers` demuestra por `nm` que no es driver PCI. Decisión de diseño, sin GPU.
5. **Trackear lo que no está en git**: 5 findings (`017`, `018`, `019`, `023-pte`,
   `021-lock`) y las herramientas `evidence_search.py`, `pm4dw.c`, `semref`, más
   `04-IMPLEMENTACION/rx550-mem/` y `rx550-pm4/` completos. Están en disco y no
   versionados; `COORDINACION.md:9-12` ya registró dos pérdidas por esto.
6. **Resolver las colisiones de índice** en `findings/`: `001`, `010`, `021` y `023`
   están duplicados. `021-lock` lo explica y lo dejó abierto a propósito.

## DOCUMENTATION HEALTH

```
DOCUMENTATION_CONSISTENCY = CONSISTENTE, VERIFICADO POR HERRAMIENTA (2026-10-01 15:1x)
```

15 ficheros, 10924 líneas. Los doce que pide el inventario de estado, más
`FINDINGS-INDEX.md` y `AGENTS-ADDENDA.md`. Referencias internas rotas: 0. Símbolos
`RE`/`TL`/`F` citados sin definir: 0. Valores antiguos sin marcar: 0.

**Las reservas son seis y están declaradas**, no descubiertas por un escaneo:

```
1. EL ÁRBOL SE MUEVE MÁS RÁPIDO QUE UNA RONDA DOCUMENTAL
   HEAD se movió 7 veces en esta ronda. Nueve findings aparecieron después de empezar.
   030 y 031 están registrados SÓLO desde su §CUDA, declarado dos veces cada uno.
   Mitigación: cada fila cita el FINDING que la respalda, nunca el commit, para que
   `grep -r` localice qué re-verificar. Por eso hay un aviso de frescura con el rango
   de commits en vez de un historial de commits

2. LO QUE NO SE HA LEÍDO NO SE REGISTRA
   De 030, 031 y 029 se leyó el §CUDA. Lo demás no. En RE-21bis y RE-22bis está
   escrito. Es preferible a rellenar por inferencia

3. LA AUTOMATIZACIÓN NO SUSTITUYE LA INTERPRETACIÓN, y el límite está escrito
   `round` mide; no juzga. Extracto de su vocabulario, que no se redondea:
     AGREE = «consistente con el autoinforme del kernel».  NO «verdadero»
     DISAGREE = «el kernel dice otra cosa».  NO «el finding está mal»
     NO_KERNEL = «no lo sé»   ·   NOT_ARBITRABLE = «esta pregunta no se arbitra así»
   Que `block_size = 22` sea incorrecto no lo deduce la herramienta: lo deduce el hecho
   de que el kernel lo contradice **y** de que el código lo confirma.  La segunda mitad
   es trabajo de una persona.  Y sólo cuatro líneas del kernel arbitran, de 92 findings
   `TL-36`

4. ESTA RONDA ENCONTRÓ UN NÚMERO MALO EN CÓDIGO COMPILABLE
   `rx550_pm4.c:277` escribe `count - 1` donde este ASIC espera `count`. Lo detectó un
   hallazgo posterior (`035`) que se declaraba corregirlo al revés. Registrado en `C-011` y
   `IMPLEMENTATION-STATUS §2.1`. **No se editó el código**: es de otra sesión, con su
   cerrojo, y `COORDINACION.md:184` es "informa, no arregles". Es el punto de mayor
   gravedad de todo el árbol y el único cuya corrección no está en la documentación

   >> **CORREGIDO 2026-10-02, y por tanto este párrafo ya no describe el árbol.**
   >> `rx550_pm4.c` escribe `count` desde antes de esta fecha: `:298`, no `:277`.
   >> La función replica `sdma_v3_0.c:986-996` dword a dword.  Medido en `RE-52`.
   >> Lo de arriba se conserva porque era verdad cuando se escribió, y porque el
   >> retraso es parte del resultado: una suite verde no vio un error de un byte
   >> en el argumento de un emisor de DMA.  Estado actual en `OPEN-FRONTIERS` F3d

5. EL 51 % DEL REGISTRO DE CLAIMS NO ES AUDITABLE
   24 de 47 tienen `SOURCE` pero no `LOCATION`. Se mide con `claim.py` y se verificó a mano
   para descartar artefacto del parser. No son necesariamente falsas: son no comprobables,
   que es la diferencia que este registro existe para documentar. Cerrarlo exige elegir la
   línea correcta de cada evidencia, y esa elección es conocimiento, no texto

6. LAS AFIRMACIONES DE LA LÍNEA B SON TESTIMONY, NO ARTEFACTO
   "GPU == CPU 0/4096 en 3 corridas" viene del texto de un commit. Los .log que
   registran 0 de 16384 en tres imágenes están IGNORADOS por .gitignore:78, y la
   cifra "4005 de 4096 bytes no nulos" no aparece en ningún log persistido.
   Frontera F6

Lo que estaba mal y **ya está corregido** en esta ronda:

| Defecto | Clase | Corrección |
|---|---|---|
| `PROYECTO_STATUS.md` decía en la cabecera `0/4096 PASS` y 30 líneas más abajo `57 de 64 FAIL` | `CONTRADICTORY` | Limitaciones marcadas `SUPERSEDED`/`NOT_RECHECKED` con el commit que las dejó obsoletas |
| `README.md` declaraba kernel `6.18.2`/Mesa `25.3.2`/`card2` | `STALE` | Bloque marcado `HISTÓRICO`; estado real verificado y enlazado |
| `00-INDICE/MASTER-RESEARCH-STATUS.md` se autodescribe como "punto único de entrada" y no menciona la línea A | `STALE` | Este fichero pasa a ser el índice; el otro queda acotado explícitamente |
| Los findings no tenían índice legible, y hay **24 índices duplicados** + huecos (004) | `INVALID` (índice) | Creado [`FINDINGS-INDEX.md`](FINDINGS-INDEX.md): cita por nombre completo, marca `TRACKED`/`UNTRACKED` de los 87, y dice qué se pierde con cada uno de los 87 sin versionar |
| Dos findings **se contradicen sobre `block_size`** (10 vs 22) | `CONTRADICTORY` | Resuelto en `C-009` con el árbitro del kernel en ejecución. El finding perdedor queda marcado en el índice, no se edita |

Lo que **sigue abierto** y no se corrigió aquí:

| Defecto | Clase | Por qué |
|---|---|---|
| `MASTER-RESEARCH-STATUS.md` de `00-INDICE/` (64 KB) describe la línea de telemetría y se autodenomina entrada única | `SUPERSEDED_NOT_DELETED` | Borrarlo es decisión humana; se acota por referencia |
| 7 índices de finding duplicados (`001`,`010`,`021`,`023`,`024`,`025`,`026`) | `INVALID` (índice) | Los findings son de sesiones distintas; renombrarlos es de las sesiones autoras, no mío. **Empeora:** eran 4 al empezar esta ronda y son 7 al terminarla |
| `29⁄9⁄26.md:169` conserva la afirmación refutada sin marca de enmienda | `CONTRADICTORY` | Fichero de otra sesión; la enmienda vive en `017` §4 y aquí. **Candidato a nota de precedence** |
| `DRIVER-MISSION-STATE.md` afirma el modelo plano "por necesidad" | `REFUTED_UPDOWNSTREAM` | Refutado en `024`; el fichero no lleva la marca. Documentar ≠ reescribir |
| 5 herramientas, 2 componentes y **87 findings** sin versionar | `UNTRACKED_EVIDENCE` | Requiere `git add`; lo decide la sesión propietaria. **La curva: 5 → 9 → 11 → 17 en tres rondas.** El único defecto de este árbol que crece solo |
| `semref` no ejecutable | `INVALID` | Coccinelle no está y se perdió con `/tmp`. Reinstalar es acción de entorno |
| `gfx8vmgeom` y `pteflags` no se ejecutan desde la raíz del repo | `ERROR` de invocación, **patrón repetido** | Dos herramientas, mismo defecto: rutas relativas al cwd y un mensaje que nombra el fichero en vez de la ruta. Los dos códigos de salida sí son correctos (rc=2). Ver `NR-05` |
| `pteflags` sin `README.md` | `UNDOCUMENTED_TOOL` | Documentado aquí; su README es fichero de otra sesión |
| `pm4dw --struct` pide la VARIABLE, no el TIPO | `USAGE` no intuitivo | Medido y documentado. Con `--struct amdgpu_ring_funcs` sale `STRUCT_NOT_FOUND`, rc=1 |

**Trazabilidad de esta ronda**: todo lo afirmado arriba se comprobó contra artefactos
del repo o se ejecutó read-only. Lo único **no** verificado por mí y marcado como tal:
el `[OK] 4005 de 4096 bytes no nulos` del agreement test, cuyo registro original está
en un commit y cuyos `.log` no están versionados (acción 2 de arriba).

## LAST VERIFIED

`2026-10-01 11:20 -03:00` · host `7.1.3-200.nobara.fc44` · **HEAD se movió cinco
veces durante la ronda**, de `ce88b5f` a `80fbd9e`; siete findings aparecieron después
de que empezara este trabajo y ya están incorporados · sin escrituras a hardware ·
sin MMIO · sin tocar `/sys` · sin `insmod`/`rmmod` · `GPU INTACTA` · cerrojos tomados
`docs` y `rootmd` (PIDs 55320 y 56795), ambos liberados · ningún fichero ajeno
modificado salvo las marcas deconciliación de `PROYECTO_STATUS.md` y `README.md` ·
ningún commit ajeno.

**Al releer este fichero, comprobar `git log --oneline -1` primero.** Si HEAD se movió
otra vez, lo último desactualizado son las filas P15-P22 de la tabla PROVEN.