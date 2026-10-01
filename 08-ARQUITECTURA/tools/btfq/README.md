# btfq — el driver amdgpu REALMENTE cargado, no el que queremos que sea

## Qué es

Un lector de BTF que responde a una pregunta que el corpus no puede:
**¿qué compila el driver que ahora mismo está corriendo en la RX550?**

`RESEARCH/working/linux-7.1.3` son los fuentes de donde venimos.
`/sys/kernel/btf/amdgpu` es el binario donde estamos. Coinciden en número de
versión (`7.1.3-200.nobara.fc44` frente a `7.1.3`), pero un distro aplica
parches, así que la coincidencia de versión **no** implica coincidencia de
fuentes. Esta herramienta mide esa divergencia en vez de suponerla.

Se lee sin root, porque `/sys/kernel/btf/` es `r--r--r--`. No toca la GPU.

## Uso

```
./btfq.py census                    control de integridad del parseo
./btfq.py enums   <subcadena>        enums por nombre de enum o de valor
./btfq.py struct  <nombre>           campos con offset REAL en bits
./btfq.py size    <struct>           size declarado vs último campo
./btfq.py present <subcadena>        miembros cuyo nombre contenga eso
./btfq.py where   <subcadena>        de qué base/módulo salió cada tipo

./crosscheck.py <struct> <header.h>  corpus (fuente) vs BTF (binario)
./vmsize.py                         geometría de GPUVM: modelo vs log del host
./sweep.py                          rastro de la cifra refutada por el proyecto

python3 cn4.py                      controles del parser BTF
python3 cn5.py                      controles del contraste
python3 cn6.py                      controles del barrido
```

Documentos: `vmsize.md` (geometría y la contradicción falsa del `dev_info`),
`bootlog.md` (observaciones de arranque), `vbios.md` (dónde vive el número de
CUs y por qué el corpus no puede derivarlo), `cus.md` (el protocolo completo para
descubrir cuántos CUs hay activos, con registros y el fallo silencioso), este
README.

Códigos de salida: `0` éxito, `1` sin coincidencias, divergencia o controles
fallidos, `2` uso incorrecto, `3` el BTF no se pudo parsear.

## Resultados obtenidos

### 1. El corpus y el binario coinciden en `amdgpu_gmc`

87 campos, intersección 87, cero divergencias reales. El host **no** lleva
parches en esta struct. Esto es una corroboración independiente del corpus:
viene del binario, no de releer los fuentes.

Un campo aparece en la fuente y no en el BTF: `idx`, el miembro de la struct
anónima dentro de `fault_hash[]`. BTF no nombra los miembros de structs
anónimas, así que se reporta como `(anon)`. Es una limitación **del formato**,
no una divergencia medida, y por eso no cuenta como diferencia.

### 2. `MTYPE` sí existe en el binario — pero no en GFX8

El binario contiene cinco enums distintos llamados `MTYPE`, con valores
inconsistentes entre sí (`MTYPE_UC = 3` en dos de ellos, `MTYPE_C_RW_US = 0`
en otro). Los declara el driver para ASICs que no son el nuestro.

Esto **no** contradice el hallazgo anterior de que GFX8 no usa `MTYPE`: la
razón sigue siendo que `gmc_v8_0.c` no abre ningún `_enum.h`. Pero la
formulación correcta es "GFX8 no usa MTYPE", no "MTYPE no existe".

Los cinco enums `MTYPE` tienen **cero** referencias desde structs, miembros o
`DATASEC`. Existen en el binario sin que ningún tipo los use.

### 3. `amdgpu_gart` no tiene ningún campo de MTYPE

5 campos: `bo`, `ptr`, `num_gpu_pages`, `num_cpu_pages`, `table_size`,
`gart_pte_flags` (`int64`). Es consistente con que GFX8 no escriba MTYPE en
las PTE: no tiene dónde hacerlo.

### 4. Lo que BTF NO puede decir

- **Macros.** Los flags de PTE (`AMDGPU_PTE_VALID` y compañía) son `#define`
  en `amdgpu_vm.h`, y BTF solo describe tipos. La prueba del discriminante:
  `GFX8` (macro) no aparece; `amdgpu_vm_level` (enum real) sí.
  **Conclusión: `btfq` complementa a `pteflags`, no lo sustituye.** Para los
  flags de PTE hace falta el preprocesador.
- **Valores en runtime.** BTF da tipos, no instancias. Responde "qué
  constantes compila el driver", no "qué hay en `adev->gmc.x` ahora mismo".

## 5. La geometría de GPUVM: el corpus acierta, y el log lo confirma

`vmsize.py` modela `amdgpu_vm_adjust_size` desde el corpus y lo compara con
`journalctl -k -b`, que es una **observación del host**, no una derivación.

```
MODELO (corpus)              HOST (log)
  vm_size    = 64 GB           64 GB     coincide
  num_level  = 1               2 levels  coincide (el log imprime num_level+1)
  block_size = 10              10-bit    coincide
  fragment   = 9               9-bit     coincide
```

`rc=0`. El corpus predice correctamente la geometría del hardware real, y como
corroboración independiente predice también GART 256 MiB para `CHIP_POLARIS12`
(`gmc_v8_0.c:595`), que es lo que el host registra. Dos geometrías
independientes, dos coincidencias.

El detalle está en `vmsize.md`, que incluye la contradicción falsa que casi se
declara (el `+1` del `dev_info`) y los dos errores de modelo que hubo que
corregir antes de llegar a la coincidencia.

## 6. El log de arranque: dos observaciones que el corpus no puede dar

`bootlog.md` extrae las 97 líneas de amdgpu de `journalctl -k -b` (solo
lectura). Casi toda la geometría ya estaba modelada, pero dos líneas aportan
hechos de **este** hardware:

**Topología de CUs, y un residuo que faltaba.** El log dice
`SE 2, SH per SE 1, CU per SH 5, active_cu_number 8`.
`AGENTS.md` ya declaraba 2 SE, 1 SH/SE, 8 CUs y máscara
`0x1e`; el log confirma los cuatro y añade el desglose: **10 CUs físicos
(`2 × 5`), de los que 8 están activos**.

El número de CUs **no es una constante del driver**. `max_cu_per_sh` viene del
**VBIOS** (`amdgpu_device.c:1848`, `gpu_info_fw->gc_num_cu_per_sh`), así que el
corpus no puede derivarlo: es una propiedad de esta placa.

Y los 8 **activos** tampoco son una máscara fija. Los calcula
`gfx_v8_0_get_cu_info()` (`gfx_v8_0.c:7072`) **escribiendo** la máscara de CUs
inactivos y **leyendo de vuelta** el bitmap de activos con
`gfx_v8_0_get_cu_active_bitmap()`. El silicio decide cuáles quedan activos. El
VBIOS publica `active_cu_per_sh` en el offset 40 de la tabla y el driver
**no lo lee**: aparece en las tres declaraciones de `atomfirmware.h` y en
ningún `.c` de `drivers/gpu/drm/`.

**Consecuencia para un driver propio:** no se pueden codificar los CUs activos.
Leer solo el VBIOS daría 10, y lanzar sobre 2 CUs que el hardware no responde a
activar no da un fallo visible, da comportamiento raro, que es peor porque
parece un bug de timing. Layout byte a byte de la tabla en `vbios.md`, y el
protocolo completo de descubrimiento en `cus.md`, incluido el fallo silencioso
cuantificado: sin el `& mask` final el conteo da **30** CUs en vez de 8, y el
hardware sigue respondiendo.

**PRT se ejerció en runtime.**

```
amdgpu 0000:01:00.0: Disabling VM faults because of PRT request!
```

Cadena trazada completa: ioctl `DRM_IOCTL_AMDGPU_GEM_VA` con
`AMDGPU_VM_PAGE_PRT` (`amdgpu_gem.c:815`) → `amdgpu_vm_fini` detecta la bandera
(`amdgpu_vm.c:2814`) → `gmc_v8_0_set_prt` escribe `mmVM_PRT_CNTL`
(`gmc_v8_0.c:766`). **Un proceso en esta máquina usó PRT.**

Esto **no** contradice a `pteflags`, que clasificó `AMDGPU_PTE_PRT` como
`CLEARED_NOT_SET` («`get_vm_pte` lo borra, no lo pone») — eso sigue cierto.
Lo que añade es que PRT tiene **dos mecanismos**: el bit 51 de la PTE, por
entrada y nunca activo en GFX8, y `mmVM_PRT_CNTL`, un registro de control
**global** que el hardware activó aquí. Confundirlos produce un error concreto:
buscar el bit 51 en las PTEs para saber si PRT está activo, cuando en GFX8 la
señal real está en el registro.

**Cuarta vía de que GFX8 no usa MTYPE.** `AMDGPU_VM_MTYPE_MASK` es un flag que
el ioctl **acepta** en cualquier ASIC (`amdgpu_gem.c:814`), pero solo lo
consumen `gmc_v9_0.c`, `v10_0`, `v11_0`, `v12_0`, `v12_1`. `gmc_v8_0.c` no
aparece, verificado por enumeración de ficheros. Un driver propio tendría que
rechazarlo explícitamente, porque el ioctl no lo hace.

## Barrido de la cifra refutada

`sweep.py` rastrea `block_size` por todo el proyecto. **No** es un
`grep block_size | grep 9`: un grep así no distingue un `9` que es `block_size`
de uno que es `fragment_size`, ni un `22` dentro de `2^22`, ni una tabla que
lista 13/14/15 para refutarlos. Esa indistinción es precisamente la que produjo
los cuatro valores que circularon.

La primera versión marcó 60 líneas. Al revisarlas una a una, **el error real en
lógica de validación era cero**, y la causa fueron dos fallos del clasificador:

- `rx550_vmid1_pgt.c` ya acepta el rango codificable `[9, 24]`, luego
  `block_size = 10` entra sin problema. La guarda que rechazaba `!= 9` fue
  sustituida antes. Solo quedan obsoletos el **texto** del mensaje de error
  (`"block_size distinto de 9"`) y un comentario que afirma `NO ESCRIBE_EN_GFX8`
  para el valor 10, afirmación que el log refuta.
- `02-ARQUITECTURA/RESEARCH-LINES.md` lee `PAGE_TABLE_BLOCK_SIZE = block_size - 9 = 1`
  partiendo del `10` del log, que es exactamente lo que `gmc_v8_0.c:933` escribe.
  Correcto, y marcado `OBSERVED`.

**Conclusión: la cifra refutada está propagada a comentarios y mensajes, no a
la validación. No hay bug funcional por `block_size`.**

### Lo que el barrido NO aporta: ya está registrado

`docs/CONTRADICTIONS.md` ya tiene **`C-005`**, que documenta exactamente esto:
`014-q1` cerró la geometría con `BITS_PER_LEVEL = 9`, `GPUVA_WIDTH_BITS = 30` y
`MIN_VIABLE_ASPACE = 2 MiB` marcados `PROVEN`, las tres falsas, con el mismo
diagnóstico de rama y la misma causa raíz (el `9` de `fragment_size_default`
tomado por el de `block_size`, y la rama `num_level > 1` que no corre). Y
`C-006` cubre la extensión a `DRIVER-MISSION-STATE.md`.

Llegué a esa conclusión por vía independiente y la eliminé al encontrarla ya
documentada. Un hallazgo duplicado en el sitio equivocado cuesta más de lo que
informa: dos versões del mismo hecho que pueden divergir sin que nadie lo note.

Lo que el barrido sí añade es la **medición del residuo**: qué ficheros siguen
contendiendo cifras refutadas y, sobre todo, que ninguna de ellas está bajo
control de versiones (`git log` vacío para `014-q1-gpuvm-minimal.md` y para
`030-page-walker-gfx8-2-niveles.md`). `git checkout` no los restauraría.

## Por qué tiene dos capas: split BTF

Con `CONFIG_DEBUG_INFO_BTF_MENU` los ids de tipo del módulo **no son
locales**. Los `name_off` tampoco. La regla completa:

```
type_ids:   base ocupa 1..142435, módulo 142436..195834
name_off:   < len(base_pool)  -> pool del base
            >= len(base_pool) -> pool del módulo, en name_off - len(base_pool)
```

El razonamiento, que es lo que hace falta para confiar en la herramienta:

| | |
|---|---|
| base `vmlinux` | 142435 tipos |
| módulo `amdgpu` | 53399 tipos |
| `max(type_id)` del módulo | 195834 = 142435 + 53399 |

Que el máximo referenciado coincida **exactamente** con la suma solo cuadra si
los ids ya venían desplazados por el base. Y que el mínimo fuera de rango
(60629) caiga por debajo de los tipos propios del módulo (1..53399) descarta que
sea un error de parseo.

Para el pool de strings hay tres hipótesis y un discriminante medido:

| hipótesis | nombres con forma de identificador C |
|---|---|
| solo pool del módulo | 5.9% |
| base si menor, si no módulo sin desplazar | 6.3% |
| **base si menor, si no módulo desplazado** | **100.0%** |

El 100% no es heurística: no queda ni un nombre por explicar.

## Errores que esta herramienta cometió

Están aquí porque el patrón se repite y para no volver a caer.

1. **`btf_type` leído como 4 bytes** en vez de 12 (`name_off u32` + `info u32` +
   `size|type u32`). Cada entrada se leía desplazada y los kinds salían
   inventados (207, 21, 245). Un kind inventado hace que el recorrido se pare en
   la segunda entrada con un error que no señala el origen real.
2. **Offsets de header leídos como absolutos.** `type_off=0` significa "justo
   detrás del header", no "en el byte 0". Leerlo absoluto parseaba el propio
   encabezado como si fuera un tipo.
3. **`str_off` sumado a `type_off+type_len`.** `str_off` *ya* es
   `type_off+type_len`; sumarlo dos veces daba una geometría que no cerraba.
4. **Asumir que los ids del módulo son locales** y marcar 3972 referencias como
   colgantes. Eran perfectly válidas. Un falso positivo de "referencia
   colgante" induce a desconfiar de un dato que era correcto.
5. **Resolver los nombres siempre contra el pool del módulo**, lo que truncaba
   unos 23000 nombres.
6. **Un control negativo que no mutaba su entrada.** Mutaba un objeto ya
   construido y volvía a cargar, así que no mutaba nada observable: pasaba
   sin comprobar nada. Se rehízo en `cn4.py` mutando el fichero.
7. **`rc=$?` después de un pipe** da el código de `head`, no el del script.
   Parecía que una consulta fallaba cuando el script iba bien.

Y dos errores de método que no eran de la herramienta sino de cómo se usó:

8. **Una regex que devolvió 0 y se reportó sin comprobar.** La causa: al
   quitar comentarios quedaba una línea con solo espacios, y `^\s*` con `re.M`
   la consumía junto con el `\n`, así que el campo siguiente ya no casaba al
   inicio de línea. "0 resultados" y "parser roto" se ven igual.
9. **Una mutación de control que no aplicaba.** Buscaba
   `\tbool\t\t\tis_app_apu;\n` (tres tabuladores) cuando la línea real es
   `\tbool is_app_apu;\n`. El control se evaluaba como si hubiera aplicado.
   Ahora `cn5.py` verifica que su mutación ocurrió antes de juzgar si el
   contraste la detecta.

## Contradicciones: ya indexadas en `docs/`

La contradicción de `block_size` **ya estaba registrada** en
`docs/CONTRADICTIONS.md` como `C-005` (y su extensión como `C-006`), con el
mismo diagnóstico y la misma causa raíz que llegué a obtener por vía
independiente. No la duplico.

Lo que estas herramientas aportan sobre eso:

- `vmsize.py` la **reproduce de forma ejecutable**: modelo contra log del host,
  `rc=0`. `docs/CONTRADICTIONS.md` la razona en prosa.
- El barrido mide el **residuo**: qué ficheros siguen con cifras refutadas y que
  ninguna de ellas está bajo control de versiones.

## Controles negativos

`cn4.py` (4/4 vivos) muta el **fichero de entrada**, nunca un objeto ya
construido, y comprueba con sha256 que `/sys/kernel/btf/amdgpu` queda
byte-idéntico. Cubre: pool de strings corrupto, fichero truncado, `str_len`
alterado, integridad de la fuente.

`cn5.py` (4/4 vivos) es mutation testing del contraste: introduce
divergencias deliberadas en una **copia en `/tmp`** — nunca en `RESEARCH/`,
que además está bajo prohibición de escritura — y exige que el contraste las
vea. Sin esto, un contraste que solo sabe decir "coinciden" no ha demostrado
nada.

`cn6.py` (8/8 vivos) es el control del barrido, y es el más importante porque
allí el riesgo es el opuesto: **fallar de más**. Dos de los cinco casos de
clasificación fallaron la primera vez (`2^22` leído como `block_size = 22`, y
el rango codificable `[9,24]` leído como un claim sobre GFX8), que era
exactamente lo que inflaba el recuento de 60 líneas.

Los tres últimos controles son de integridad de los documentos, y existen
porque tres fallos reales pasaron inadvertidos:

- `CN-6f`, CJK o cirílico colados. Se me colaron varias veces en mitad de una
  frase española sin que se vieran al escribir.
- `CN-6g`, backticks colgando. Una sustitución con regex borró backticks de
  cierre en tres documentos. El primer criterio que probé —«el número total de
  backticks debe ser par»— **era incorrecto**: los bloques cercados aportan 3
  backticks cada uno y falsean la paridad. Se reemplazó por una comprobación
  de estado línea a línea.
- `CN-6h`, backticks emparejados pero **cruzados** (`uno \`a y \`b\``). Estos
  tienen número par y ninguna línea queda abierta, así que `CN-6g` los acepta;
  y el render queda mal. `CN-6h` los detecta y encontró dos casos reales en
  este mismo README.

Los tres se validaron con mutación: cada uno detecta su fallo y el árbol queda
limpio después.

Cuando los controles de un clasificador por contexto viven, eso **no** convierte
su salida en una lista de errores: `cn6.py` lo dice en su propia salida.

## Estado epistémico

- Parseo del BTF: **PROVEN** por geometría cerrada (0 referencias colgantes),
  recuento consistente y discriminante de strings al 100%.
- Corpus ≡ binario para `amdgpu_gmc`: **PROVEN** por contraste de campos.
- Geometría de GPUVM (`vm_size=64`, `num_level=1`, `block_size=10`,
  `fragment=9`): **PROVEN**, modelo del corpus y log del host coinciden.
- GART = 256 MiB en POLARIS12: **PROVEN**, corpus y log.
- GFX8 no usa `MTYPE`: **PROVEN** por cuatro vías independientes (fuente: cero
  `_enum.h` en `gmc_v8_0.c`; BTF: sin campo MTYPE en `amdgpu_gart`; binario: los
  cinco enums `MTYPE` sin referencias; enumeración de ficheros:
  `AMDGPU_VM_MTYPE_MASK` solo lo consumen `gmc_v9/v10/v11/v12`).
- `BITS_PER_LEVEL = 9` de `014`: **REFUTED** — son 10.
- El driver del host está parcheado respecto al corpus: **REFUTED**; la
  contradicción aparente venía del `+1` del `dev_info`.
- 10 CUs físicos, 8 activos: **DERIVATION** sobre `OBSERVATION` del log; la cifra
  viene del VBIOS (`amdgpu_device.c:1848`), no del driver, y los activos los
  decide el silicio, leído por `gfx_v8_0_get_cu_info()`.
- La ruta PRT de GFX8 existe y el hardware la ejerció: **OBSERVED**. La
  semántica de `CB_DISABLE_*_FAULT_ON_UNMAPPED_ACCESS`: **NOT_DETERMINED**.
- `AMDGPU_PTE_PRT` nunca activo en GFX8: **PROVEN** (`pteflags`, sin cambio).
- Semántica de hardware de cada bit de PTE: **NOT_DETERMINED**. Requiere runtime
  con root, no autorizado.