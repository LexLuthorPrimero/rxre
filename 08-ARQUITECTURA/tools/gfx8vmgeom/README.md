# gfx8vmgeom — geometría GPUVM de GFX8/Polaris12, derivada del corpus

`gfx8vmgeom` calcula la geometría de page tables que el driver de amdgpu
programa en un Polaris12, y la **contrasta con la línea que el host imprimió en
el boot**. No escribe registros, no lee MMIO, no ejecuta código del driver: es
un cálculo sobre el texto del árbol de referencia.

## Por qué existe

`08-ARQUITECTURA/designs/014-q1-gpuvm-minimal.md` cerró `Q1 GPUVM_MINIMAL`
afirmando:

```
BITS_PER_LEVEL     = 9       PROVEN
GPUVA_WIDTH_BITS   = 30      PROVEN
MIN_VIABLE_ASPACE  = 2 MiB   DERIVATION
```

Las tres cifras están mal, y no por una diferencia de criterio: por una rama
del código que no es la que corre. El host imprimió

```
vm size is 64 GB, 2 levels, block size is 10-bit, fragment size is 9-bit
```

`block_size` es **10**, no 9. Como `PTB` tiene `1 << block_size` entradas, no
512 sino **1024**; un `PTB` mide 8 KiB, no 4 KiB; y la unidad mínima real son
**4 MiB**, no 2 MiB.

## La causa concreta

`amdgpu_vm.c:2446-2454`:

```c
if (amdgpu_vm_block_size != -1)
        ...bloque superior...
else if (adev->vm_manager.num_level > 1)
        adev->vm_manager.block_size = 9;              /* <- la que cita 014 */
else
        adev->vm_manager.block_size = amdgpu_vm_get_block_size(tmp);
```

Con `max_level = 1` (`gmc_v8_0.c:1127`), `num_level` sale **1**, así que la
rama `> 1` no se ejecuta. Corre la del `else`, que pasa `tmp` —un valor
derivado de `fls64`— y **no** `vm_size`. `get_block_size(2)` devuelve 10.

Si se hubiera pasado `vm_size = 64`, `get_block_size` habría devuelto 13. El
control negativo `CN-1` mide precisamente esa diferencia.

## Uso

```bash
make test          # test + 12 controles negativos (target por defecto)
make check-corpus  # fuentes pristine vs árbol instrumentado
make report        # solo el informe, para pegar en un documento
make check-noa8    # guardas: la herramienta no toca hardware
make clean
```

## La regla que hace la herramienta creíble

**Ninguna constante del modelo está escrita a mano.** Todas se extraen del
corpus con una búsqueda anclada:

| dato | de dónde sale |
|---|---|
| `min_vm_size`, `fragment_size_default`, `max_level`, `max_bits` | `gmc_v8_0.c`, de la llamada real a `amdgpu_vm_adjust_size` |
| `pte_addr_mask` → 40 bits de PA | `gmc_v8_0.c` |
| posición de cada bit de PTE | `amdgpu_vm.h`, leyendo el `<<` de cada `#define` |
| `CHIP_POLARIS12` vs `CHIP_VEGA10` | `include/drm/amd_asic_type.h`, contando el enumerador |
| `GC_HWIP` | `gfx_v8_0.c`, de `gfx_v8_0_ip_block` |

Si un ancla no aparece, la herramienta **falla con `rc=2`**. No devuelve un
cero que luego se propaga como si fuera una propiedad del hardware.

## Las dos raíces, y por qué

El corpus de este repo está partido:

- `RESEARCH/working/linux-7.1.3` → `drivers/gpu/drm/amd/amdgpu`, **7.1.3 prístino**
- `RESEARCH/kernelbuild/linux-7.1.3` → `include/drm/amd_asic_type.h`, que en
  `working` no está

`working` y `baseline` traen `include/linux` y nada más. Mezclarlos a ciegas
sería repetir el fallo que este repo ya registró dos veces con árboles
instrumentados, así que la mezcla es **explícita** y **verificada**: la
herramienta exige que el `sha256` de `amd_asic_type.h` sea el del tarball
`cea577df…a7809`, y calcula ese hash con su propia implementación en lugar de
confiar en `sha256sum`.

`kernelbuild` está instrumentado (`RE-02-E1`, ver
`RESEARCH/evidence/working-vs-kernelbuild-difference.md`). Por eso las fuentes
se toman de `working`. `make check-corpus` corre contra los dos para que se
vea que la instrumentación no altera la geometría.

## La capacidad de fallar, demostrada

12 controles negativos. Cada uno muta una entrada y exige que el veredicto
cambie. Un control que **no** detecta su propia mutación se marca `[DEAD]` y
cuenta como fallo: es peor que no tenerlo, porque aparenta cobertura.

```
CN-1   get_block_size recibiera vm_size en vez de tmp   (10 vs 13)
CN-2   la rama (num_level > 1) -> block_size = 9
CN-3   fragment_size = 8
CN-4   512 entradas por nivel
CN-5   PAGE_TABLE_BLOCK_SIZE = block_size, sin el -9
CN-6   gate asic_type >= VEGA10 invertido
CN-7   ancla inexistente en amdgpu_vm.h
CN-8   enumerador inexistente en amd_asic_type.h
CN-9   raíz de corpus inexistente
CN-10  max_bits 40 -> 30  (produce justamente el 9 que 014 afirma)
CN-11  sha256: cabecera mutada debe ser rechazada
CN-12  sensibilidad a la RAM del host
```

`CN-11` es el que sostiene la legitimidad de mezclar dos raíces: si el verificador
de hash aceptara cualquier fichero, la mezcla sería una confianza ciega.

### Dos controles que nacieron muertos

Esto quedó registrado porque es el fallo que el protocolo del repo ya prohíbe,
y conviene que sea visible:

- **`CN-10` con `max_bits = 48`**: con `max_size = 2^18` el clamp de
  `amdgpu_vm.c:2418` dejaba `vm_size` en su suelo de 64, el mutante no se
  propagaba y el control no distinguía nada. Salió `[DEAD]`. Se cambió a
  `max_bits = 30`, que sí llega al observable.
- **`CHIP_POLARIS12 = 17` falló con 19**: el extractor de enumeradores contaba
  desde `enum amd_asic_type` en vez de desde la llave de apertura, así que
  desplazaba todos los ordinales en 2. El defecto estaba en la herramienta, no
  en el corpus. La aserción lo detectó.

## Lo que la herramienta **no** establece

```
SUBMISSION, FETCH, EXECUTION en hardware    NOT_DETERMINED
semantica de hardware de cada bit de PTE     NOT_DETERMINED
si el hardware acepta 1024 entradas por PTB    NOT_DETERMINED
la linea observada                           OBSERVATION, de un boot previo
```

Que la aritmética del driver coincida con lo que el host imprimió es
`DERIVATION` corroborada por una `OBSERVATION`. No es evidencia de que el
silicio interprete así la geometría: para eso hace falta runtime, y esta
herramienta no lo hace.

## Estado

```
37 aserciones, 0 fallos
12 controles negativos, 12 detectados, 0 muertos
informe: 0 discrepancias
cruce de version 7.1.3 / 7.2.8   PROVEN, misma rama
3 corridas consecutivas, idénticas
test puede fallar: demostración con rc=2 sobre cabecera mutada
GPU INTACTA · RUNTIME NOT_RUN · WRITE_EXECUTION NONE
```

## Cruce de versión

La rama que decide `block_size` es la causa de todo el hallazgo. Si hubiera
cambiado entre versiones, el hallazgo sería un artefacto de 7.1.3 y no una
propiedad del ASIC. La herramienta lo comprueba ella sola, afirmando la
**forma** de la rama y no su número de línea:

| | 7.1.3 | 7.2.8 |
|---|---|---|
| `if (num_level > 1)` → `block_size = 9` | sí | sí |
| `else` → `get_block_size(tmp)` | sí | sí |
| `else` → `get_block_size(vm_size)` | **no** | **no** |

Un número de línea habría sido el tipo de acoplamiento que este repo ya
sufrió; una forma de rama sobrevive al cambio de versión.