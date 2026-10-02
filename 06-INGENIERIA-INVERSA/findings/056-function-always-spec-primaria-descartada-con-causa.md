# 056 · `FUNCTION=always`: la spec primaria existe, es de shaders, y nunca hubo documentación pública del packet decoder

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC+EXTERNAL` · `CORPUS=RESEARCH/working/linux-7.1.3`
`HARDWARE_SCOPE=HOST-C/RX550` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=SCOPED(findings)` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CORRECTS=la clasificación NOT_AVAILABLE que yo mismo hice en iteraciones previas`
`REFERENCIA=AGENTS.md §C, §DOCUMENTACIÓN EXTERNA, §TERMINATION/BLOCK POLICY`

## CUDA principal

`FUNCTION=always` no es `NOT_AVAILABLE`. La especificación primaria de AMD **existe**
y está publicada: *"Vega" Instruction Set Architecture*, 288 páginas, con
Specification Agreement legal. Está en GPUOpen y en `docs.amd.com` (ID 70656,
release 2020-01-27).

Lo que hace es **descartada con causa**. Su índice, leído en dos fuentes
independientes que reproducen el mismo árbol de 13 capítulos, es de **ISA de
shaders**: Scalar ALU, Vector ALU, Scalar/Vector Memory, Flat Memory, Data Share,
Pixel/Vertex params, Instruction Details, Microcode Formats. **Ningún capítulo
trata packet3, PM4, ni los comandos del command processor.** El CP aparece sólo en
el diagrama de bloques del capítulo 1.

La clasificación correcta no es "no encontramos la fuente" sino: **la
documentación pública de AMD separa ISA de shaders de packet decode, y sólo
publica lo primero.** Eso es una `NEGATIVE_RESULT` con la causa nombrada, y es un
resultado más fuerte que un bloqueo.

## 1 · La escalera de DOCUMENTACIÓN EXTERNA, completa

AGENTS.md:698-717 exige los pasos en orden antes de declarar una ausencia. Esta
es la ejecución íntegra:

| # | paso | resultado |
|---|---|---|
| 1 | corpus | 5 packet headers: `vid.h`, `cikd.h`, `nvd.h`, `sid.h`, `soc15d.h`, `gfx_v12_1_pkt.h`. Sólo el enum 0..6 |
| 2 | headers | idénticos entre sí. Ningún comentario del trigger |
| 3 | históricos | `gmc_v6_0.c`, `gmc_v7_0.c`: mismo enum, misma numeración |
| 4 | Mesa / LLVM | LLVM publica GFX8 (`AMDGPUAsmGFX8`, versiones 8/9/10/11/15/18). **Es ISA de shaders, no packet decode. No cuenta para §C** |
| 5 | primaria | **EXISTE.** AMD, *"Vega" ISA*, 288 pp. Clasificación `PRIMARY_DOCUMENTATION` |

Los cuatro primeros ya estaban hechos en iteraciones previas. **El quinto no, y
es el que decide.** Mi clasificación anterior de `NOT_AVAILABLE` era una
afirmación sin comprobar, hecha tras verificar 2 de 5 pasos — exactamente lo que
TERMINATION / BLOCK POLICY (AGENTS.md:1055-1072) prohíbe al declarar un bloqueo.

## 2 · El índice de la spec, y por qué no responde

Reproducido de forma idéntica en dos fuentes independientes (GPUOpen y
`rocmdoc.readthedocs.io`, que replican el mismo árbol):

```
Cap 1   Introduction
Cap 2   Program Organization
Cap 3   Kernel State
Cap 4   Program Flow
Cap 5   Scalar ALU Operations
Cap 6   Vector ALU Operations
Cap 7   Scalar Memory Operations
Cap 8   Vector Memory Operations
Cap 9   Flat Memory Instructions
Cap 10  Data Share Operations
Cap 11  Pixel Color and Vertex Shader Parameters
Cap 12  Instruction Details
Cap 13  Detailed Specification of Each Microcode Format
```

Los tres símbolos de la pregunta:

| símbolo | ¿aparece en el índice? |
|---|---|
| `WAIT_REG_MEM` | no |
| `PACKET3` | no |
| `CONTEXT_CONTROL` | no |

El documento es sobre las **microcode formats del shader array**. `PACKET3` es un
paquete del **command processor**, que es otra unidad funcional: el propio
documento lo nombra sólo en la figura del cap 1, como bloque del diagrama.

**Conclusión:** para la semántica del predicado de `WAIT_REG_MEM`, la
documentación pública de AMD no es la fuente, y no porque esté incompleta sino
porque cubre otra cosa.

## 3 · Fuentes con el enum, y por qué NO son evidencia

Aparecen tres réplicas independientes de `PACKET_TYPE3` con el opcode
`0x3C = IT_WAIT_REG_MEM`:

| fuente | clase | por qué no sirve |
|---|---|---|
| `drivers/gpu/drm/amd/amdkfd/kfd_pm4_opcodes.h` | `CORPUS` | enum de opcodes, sin semántica de ningún campo |
| `intel-gpu-tools/lib/amdgpu/amd_PM4.h` (Debian 1.27.1) | `CORPUS` | derivado del header de AMD. Documenta `WRITE_DATA_DST_SEL`, no `WAIT_REG_MEM_FUNCTION` |
| `gem5 src/dev/amdgpu/pm4_packet_processor.hh` | `CORPUS` | implementa el decode, no documenta el predicado |

**Ninguno documenta el trigger de `FUNCTION`.** Reproducen el enum, que ya
tenemos. Por `DOCUMENTACIÓN EXTERNA` ("No presentar secundaria como primaria") no
se pueden elevar a evidencia del hardware.

## 4 · Acceso a la spec: NOT_FETCHED por acceso, no por inexistencia

Registro esto con precisión, porque la distinción ya me costó un falso positivo
antes hoy (contar paquetes con `dpkg` en un sistema Fedora):

| vía | resultado |
|---|---|
| `amd.com/…/vega-shader-instruction-set-architecture.pdf` | `fetch` timeout ×2. `curl` sin respuesta. **El host no responde desde esta máquina** |
| `techpowerup.com/gpu-specs/docs/amd-vega-isa.pdf` | espejo del mismo PDF, pide **verificación de bot**. No la evito |
| `docs.amd.com/api/khub/documents/…/content` | **HTTP 401**: requiere autenticación |

Control de red, para separar host de herramienta: `raw.githubusercontent.com` y
`releases.llvm.org` responden **HTTP 200** en la misma sesión. La red funciona;
`amd.com` no responde.

⇒ La spec está **`NOT_FETCHED` por acceso**. No la he leído. **No afirmo nada
sobre su contenido más allá del índice**, que es lo que las dos fuentes
muestran literalmente. La conclusión de §2 se sostiene en el índice, no en una
lectura del documento.

## 5 · Clasificación corregida

| afirmación | clase | estado |
|---|---|---|
| la spec primaria de AMD existe y es pública | FACT | **PROVEN** (GPUOpen + docs.amd.com, ID 70656) |
| es de ISA de shaders, no de packet decode | FACT | **PROVEN** (índice en 2 fuentes) |
| ningún capítulo trata packet3 / PM4 / CP | NEGATIVE_RESULT | **PROVEN_ABSENT**, 13 capítulos × 2 fuentes |
| las 3 réplicas del enum no documentan el trigger | NEGATIVE_RESULT | **PROVEN_ABSENT**, 3 fuentes |
| LLVM GFX8 no aplica a §C | DERIVATION | **PROVEN_DERIVED** (es shader ISA) |
| QEMU no puede ser fuente de decoder GFX8 | DERIVATION | **PROVEN_DERIVED** (ver §6) |
| **trigger de `FUNCTION=always`** | — | **`NOT_DETERMINED`, con la fuente primaria localizada y descartada con causa** |

**Deja de ser `NOT_AVAILABLE`.** Era un bloqueo que nadie había comprobado.

## 6 · QEMU, verificado sin instalarlo

TOOL COMPATIBILITY CONTRACT aplicado antes de descartar:

- `qemu-system-x86_64`: **no instalado**, pero **disponible** en el repositorio
  (`qemu-system-x86.x86_64 2:10.2.2-1.fc44 nobara`) ⇒ `NOT_INSTALLED`, **no**
  `NOT_AVAILABLE`
- Instalado sí: `qemu-common`, `qemu-user-static-*` (21 arquitecturas),
  `qemu-device-display-qxl`, `qemu-ui-*`, `ipxe-roms-qemu`
- `/usr/share/qemu/`: 35 ficheros, 34 son `keymaps/` y 1 `linuxboot_dma.bin`.
  **Ningún blob de vídeo**
- `qemu-user-static` emula ISA de CPU, no de GPU. `qemu-system-x86` emula
  máquina con VGA genérico / Cirrus / QXL / stdvga. **0 coincidencias de
  `amdgpu` en el contenido real de los paquetes instalados**

⇒ No existe un dispositivo GPU AMD emulado en QEMU, ni para GFX8 ni para
Polaris12. Instalar el paquete no produciría un decoder de packets. **La
comprobación no requería instalarlo**, y no se instaló nada.

## 7 · Qué cerraría `FUNCTION=always`, y qué no existe

Para pasar de `NOT_DETERMINED` a `PROVEN` harían falta tres cosas, y ninguna
existe como documento público:

1. Silicon documentation con NDA (no accesible, y no es una ruta legítima)
2. Reverse engineering del decoder — que es lo que el propio proyecto es, y
   exige el discriminante runtime de F1
3. **El discriminante runtime**, escrito en `017 §5` y en `OPEN-FRONTIERS.md:38-43`:
   escribir un `WAIT_REG_MEM(FUNCTION=always, poll=0x20)` y leer
   `INVALIDATE_REQUEST` desde software, entre dos IBs, con el invalidate
   deliberadamente retardado; y repetir con `poll=0x0` y `poll=0xFF`. Si el
   resultado cambia con el poll, el wait espera algo.

**Nota importante sobre (3):** la lectura de `INVALIDATE_RESPONSE` que hace
`gmc_v8_0_flush_gpu_tlb_pasid` (`gmc_v8_0.c:641`) no sirve como discriminante.
`018-execution-order-invalidacion-gfx8.md:69-74` ya lo establecio: `REQUEST`
es un mapa de 16 bits sin token, así que un `RESPONSE` con bits puestos no
distingue una invalidación nueva de una anterior. Esa objeción es correcta y
este documento la reitera.

## 8 · Clasificación del hallazgo

Este documento **no cierra §C** y no pretende. Lo que hace es corregir una
clasificación mía que estaba mal, y eso vale más que un hallazgo nuevo porque
cambia lo que el proyecto cree que le falta:

| antes | ahora | por qué |
|---|---|---|
| `NOT_AVAILABLE` | **`NOT_DETERMINED` con la fuente primaria descartada con causa** | la spec existe; es de shaders |
| "faltan las fuentes" | "las fuentes existen y no cubren esta pregunta" | escalera de 5 pasos ejecutada |
| `BLOCKED_BY_CORPUS` | **`BLOCKED_BY_EXTERNAL_DEPENDENCY`** | falta doc de packet decode, y no es pública |

Consecuencia operativa: un driver propio **no debe implementar ninguna semántica
para `FUNCTION=0`** (IMPLEMENTATION GATE, AGENTS.md:1092-1115). La codificación
está `PROVEN`; el efecto de hardware no. Se implementa la codificación porque es
lo que hace el driver de referencia, y se marca como no verificado — no porque
"funciona", sino porque es lo que el hardware acepta como paquete válido.

## 9 · Nota de proceso

Dos veces en esta iteración afirmé antes de verificar:

1. "QEMU no emula GPU ISA" — lo dije en el mismo comando que decía estar
   verificándolo. Corregido consultando el contenido real de los paquetes.
2. "0 paquetes qemu instalados", usando `dpkg` en Fedora/Nobara. `dpkg` no
   existe. Era un falso 0 producido por un comando inexistente, que es
   literalmente el patrón que AGENTS.md:257-267 prohíbe.

Las dos producen la misma clase de resultado: un número aparentemente sólido y
falso. La segunda casi me da un `NOT_AVAILABLE` en un informe. Y la que es
reparable —`NOT_FETCHED` por acceso frente a por inexistencia— es la misma
distinción que apliqué a `dpkg`, aplicada ahora al documento.

El fichero se corrompió al escribirlo (un bucle de caracteres CJK en la línea
170). Detectado con un grep de caracteres no-ASCII, recortado a la línea 169 y
completado. **Verificar el artefacto después de escribirlo, no antes.**
