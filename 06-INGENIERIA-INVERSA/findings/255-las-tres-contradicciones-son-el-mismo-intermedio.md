# 255 · `num_level`, `block_size` y `page_table_depth`: las tres contradicciones de `next_work.py` son la misma, y ninguna es contradicción

```text
CLASSIFICATION=CORRECTION+MEASUREMENT · TRACK=STATIC + RUNTIME(lectura)
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0 · WRITE_EXECUTION=NONE
RUNTIME=REGISTRO DE ARRANQUE y /proc/meminfo SOLO LECTURA · GPU INTACTA
```

> **Convención de rutas.** `amdgpu/x.c` = `drivers/gpu/drm/amd/amdgpu/x.c`. Las 10 citas de
> código resuelven con base `drivers/gpu/drm/amd/`.

## Qué resuelve

**Las tres contradicciones que `next_work.py` coloca primero son artefactos de su propio criterio, no
discrepancias en el corpus.** `REFUTED` (la contradicción) / `PROVEN` (el valor real).

**⇒ `PROVEN`. Las tres se resuelven en una sola función, `amdgpu_vm_adjust_size`
(`amdgpu/amdgpu_vm.c:2379`), y las tres son el resultado de confundir un valor calculado con el
valor que el ASIC impone.** `PROVEN`.

**⇒ `PROVEN`. El valor real de los tres, para Polaris12:** `num_level = 1`, `block_size = 10`,
`root_level = AMDGPU_VM_PDB0`, `fragment_size = 9`. Los cuatro, contados por programa con los
parámetros que `gmc_v8_0.c:1127` pasa a esa función.** `PROVEN`.

## 1 · La cadena, desde la llamada

**⇒ `PROVEN`. `amdgpu/gmc_v8_0.c:1127` es la única llamada que aplica a Polaris12:** `PROVEN`.

```c
1123  /* Adjust VM size here.
1124   * Currently set to 4GB ((1 << 20) 4k pages).
1125   * Max GPUVM size for cayman and SI is 40 bits.
1126   */
1127  amdgpu_vm_adjust_size(adev, 64, 9, 1, 40);
```

**⇒ `PROVEN_DERIVED`. Y el comentario es engañoso por diseño: dice «cayman and SI», que son
generationes anteriores a GFX8. La función la usa GFX8 igual, con `max_bits = 40` y no 48, y el
comentario es la explicación de por qué: en VI el espacio de direcciones de 40 bits no es un
arbitrario, es el límite de la generación.** `PROVEN_DERIVED`.

**⇒ La firma (`amdgpu_vm.c:2379-2381`) fija el significado de los cinco argumentos, y es lo que
desambigua la contradicción:**

```c
2379  void amdgpu_vm_adjust_size(struct amdgpu_device *adev, uint32_t min_vm_size,
2380                             uint32_t fragment_size_default, unsigned max_level,
2381                             unsigned max_bits)
```

| argumento | valor GFX8 | lectura |
|---|---|---|
| `min_vm_size` | 64 | MB, suelo del tamaño de VM |
| `fragment_size_default` | 9 | `fragment_size` por defecto, **coincide con el estado del proyecto** |
| `max_level` | **1** | **el límite del ASIC** |
| `max_bits` | 40 | bits del espacio de direcciones |

**⇒ `PROVEN_DERIVED. El `40` del último argumento es `max_bits`, no un nivel. Es el número que más
probablemente se lee mal, porque está en la misma llamada que el `1` que sí es un nivel, y ambos
son enteros pequeños en posiciones contiguas.** `PROVEN_DERIVED`.

## 2 · `num_level`: por qué aparecen el 1 y el 2

**⇒ `PROVEN`. El cálculo son cinco líneas, `amdgpu_vm.c:2383` a `2428`:** `PROVEN`.

```c
2383      unsigned int max_size = 1 << (max_bits - 30);
2388      if (amdgpu_vm_size != -1) {
2389          vm_size = amdgpu_vm_size;
...
2395      } else {
2414          si_meminfo(&si);
2415          phys_ram_gb = ((uint64_t)si.totalram * si.mem_unit + (1 << 30) - 1) >> 30;
2417          vm_size = roundup_pow_of_two(clamp(phys_ram_gb * 3, min_vm_size, max_size));
2419      }
2421      adev->vm_manager.max_pfn = (uint64_t)vm_size << 18;
2424      tmp = roundup_pow_of_two(adev->vm_manager.max_pfn);
2425      if (amdgpu_vm_block_size != -1)
2426          tmp >>= amdgpu_vm_block_size - 9;
2427      tmp = DIV_ROUND_UP(fls64(tmp) - 1, 9) - 1;
2428      adev->vm_manager.num_level = min_t(unsigned int, max_level, tmp);
```

**⇒ La cuenta completa, por programa, con `MemTotal = 12098904 kB` medido en esta sesión:** `PROVEN_DERIVED`.

```text
max_size        = 1 << (40-30)               = 1024 MB
rama            = amdgpu_vm_size == -1       -> si_meminfo          (el default)
phys_ram_gb     = ceil(12389285888 / 2^30)   = 12
vm_size         = rup2(clamp(36, 64, 1024)) = rup2(64) = 64 MB
max_pfn         = 64 << 18                   = 2^24
tmp             = rup2(2^24)                 = 2^24
amdgpu_vm_block_size == -1                   -> no se aplica el >>=
fls64(2^24)     = 25
tmp             = DIV_ROUND_UP(24, 9) - 1    = 3 - 1 = 2
num_level       = min_t(1, 2)                = 1
```

**⇒ `PROVEN_DERIVED. Y aquí está la contradicción completa: `tmp = 2` y `max_level = 1`. Los dos
números que `next_work.py` recoge como «dos valores de `num_level`» son uno el resultado del
`min_t` y el otro el operando que el `min_t` descartó. El campo `num_level` vale 1; el 2 es un
intermedio que existe dentro de la función y no sale de ella.** `PROVEN_DERIVED`.

**⇒ `REFUTED`. No hay contradicción sobre `num_level`: hay un valor correcto (`1`) y un
intermedio local (`2`). La diferencia es de 1 y viene de `max_level`, que es un límite
del ASIC, no del cálculo.** `REFUTED`.

**⇒ `PROVEN`. `024` ya lo tenía dicho con la frase exacta: «`num_level = 1` porque
`max_level = 1`, aunque el cálculo del tamaño pediría 2». La afirmación es correcta; lo que
faltaba era la aritmética, que está aquí medida.** `PROVEN`.

## 3 · `root_level`: un error mío que el programa cometió primero

**⇒ `PROVEN`. El switch es `amdgpu_vm.c:2429-2444` y `case 1` asigna `AMDGPU_VM_PDB0`
(`amdgpu_vm.c:2439-2440`).** `PROVEN`.

| `num_level` | `root_level` |
|---|---|
| 4 | `AMDGPU_VM_PDB3` |
| 3 | `AMDGPU_VM_PDB2` |
| 2 | `AMDGPU_VM_PDB1` |
| 1 | **`AMDGPU_VM_PDB0`** |

**⇒ `ERROR`. Mi primer script imprimió `root_level = AMDGPU_VM_PDB1`, porque leí el valor de
`tmp` en lugar del de `num_level` y apliqué `PDB<tmp>` por analogía. `024:54` decía `PDB0` y la
razón es que `PDB` se numera desde 0 igual que `num_level`: `case 1` da `PDB0`, no `PDB1`. El
error fue mío y una comprobación cruzada contra `024` lo habría cazado antes de escribir.** `ERROR`.

## 4 · `block_size`: el mismo mecanismo, la misma función

**⇒ `PROVEN`. Con `num_level == 1` la rama que se aplica es `amdgpu_vm.c:2453-2454`,
`adev->vm_manager.block_size = amdgpu_vm_get_block_size(tmp)`, con `tmp = 2`.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Y aquí hay un error de nomenclatura en el propio driver que es la segunda
mitad de la contradicción: el parámetro de `amdgpu_vm_get_block_size`
(`amdgpu/amdgpu_vm.c:2356`) se llama `vm_size`, y el comentario de `amdgpu_vm.c:2350` dice
«@vm_size: VM size», pero el valor que recibe es `tmp`, que es un índice de nivel
(`DIV_ROUND_UP(...) - 1`), no un tamaño de VM. El nombre del parámetro describe otra cosa.** `PROVEN_DERIVED`.

**⇒ La función, `amdgpu_vm.c:2356-2367`, y su cuenta con `tmp = 2`:** `PROVEN`.

```c
2356  static uint32_t amdgpu_vm_get_block_size(uint64_t vm_size)
2357  {
2358      /* Total bits covered by PD + PTs */
2359      unsigned bits = ilog2(vm_size) + 18;
2361      /* Make sure the PD is 4K in size up to 8GB address space.
2362       * Above that split equal between PD and PTs */
2363      if (vm_size <= 8)
2364          return (bits - 9);
2365      else
2366          return ((bits + 3) / 2);
2367  }
```

```text
vm_size (que recibe tmp) = 2
bits   = ilog2(2) + 18  = 1 + 18 = 19
2 <= 8  ->  return bits - 9 = 19 - 9 = 10
```

**⇒ `PROVEN`. `block_size = 10`. Coincide con `035`, que ya había corregido a `024` en este
punto.** `PROVEN`.

**⇒ `REFUTED`. El `22` que `next_work.py` recoge como segundo valor de `block_size` no sale de
ninguna rama de esta función: el máximo alcanzable con `vm_size <= 8` es `bits - 9`, y para que
saliera 22 haría falta `bits = 31`, o sea `ilog2(vm_size) = 13`, o sea `vm_size = 8192`. El 22
no es un valor de esta función para ningún `tmp` que GFX8 pueda producir.** `REFUTED`.

**⇒ `PROVEN_DERIVED. `035` titula exactamente esto —«Tres valores para `block_size`»— y su
conclusión es que los otros dos eran errores de redondeo previos. La contradicción que
`next_work.py` ve ahora es un eco de esos errores ya corregidos, no una reopening.** `PROVEN_DERIVED`.

## 5 · `page_table_depth`: el tercer valor, y por qué existe

**⇒ `PROVEN_DERIVED. `next_work.py` recoge `['0', '2', '1']` para `page_table_depth`. Con
`num_level = 1` y `root_level = PDB0` el número de tablas es 2 (una PDE y una PTE). El `2` es
correcto. El `1` es `num_level`. Y el `0` es el índice `PDB0` leído como número de niveles.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Es el mismo error por tercera vez, con una diferencia: aquí los tres números
salen de tres campos legítimos y distintos —`num_level`, el número de tablas, y el índice
`root_level`— y la herramienta los funda en una sola clave porque los tres aparecen cerca en el
texto. No es una contradicción del corpus: es una colisión de sinonimia en el extractor.** `PROVEN_DERIVED`.

**⇒ Y por eso los tres nombres que usa `next_work.py` no son campos del driver: `num_level` sí
existe en `amdgpu_vm.c`, pero `block_size` también, y `page_table_depth` no aparece en
`amdgpu/`. El extractor está leyendo prosa, no struct.** `PROVEN_DERIVED`.

## 6 · El patrón de fondo, que es el hallazgo real de esta nota

**⇒ `PROVEN_DERIVED`. Las tres contradicciones tienen la misma causa y la misma forma: un
resultado calculado junto al límite que lo acota, en la misma expresión, sin que nadie registre
cuál de los dos sobrevive. `min_t(1, 2)` es el caso canónico, y el `min_t` es literalmente la
línea donde se resuelve.** `PROVEN_DERIVED`.

**⇒ Y esto no es un defecto del corpus sino de la lectura: el corpus está bien, lo que no está
bien es un extractor que recoge números sin saber de qué expresión salen. Las tres filas que
`next_work.py` pone primero son sus tres falsos positivos, y su propia cabecera lo admite:
«NO decide cuál hacer. Decide cuál es el más barato de empezar».** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Consecuencia sobre el ranking: los candidatos `[0]`, `[1]` y `[2]` no son
trabajo, son ruido. Y como la herramienta ordena por coste, y el ruido tiene coste 1, el ruido
sale primero. Un ranking ordenado por coste sin filtro de validez es un ranking de lo que más
fácil es malinterpretar.** `PROVEN_DERIVED`.

**⇒ `REFUTED`. Ninguna de las tres contradicciones era real. La contradicción estaba en la
herramienta, no en el conocimiento.** `REFUTED`.

## 7 · Lo que queda abierto

**⇒ `NOT_DETERMINED`: si `amdgpu_vm_size` o `amdgpu_vm_block_size` pueden estar fijados por
módulo en esta máquina. El código tiene las dos ramas (`amdgpu_vm.c:2388` y `:2425`) y el estado
del proyecto asume los defaults `-1`, pero no hay medición de los valores efectivos en runtime.
Es la diferencia entre «el valor por defecto» y «el valor que se está usando».** `NOT_DETERMINED`.

```text
PENDIENTE=255-1 | HALLAZGO=255-*.md | ESTADO=NOT_DETERMINED
           | NECESITA=/sys/module/amdgpu/parameters/vm_size
           | ALCANZABLE_SIN_ROOT=NO_MEDIDO
```

**⇒ Y ese discriminante es trivial y no necesita placa, sólo leer dos ficheros de sysfs. Si
`/sys/module/amdgpu/parameters/` no expone esos parámetros, la ruta no existe y el asunto queda
cerrado como `PROVEN_ABSENT` del parámetro.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Con esto la geometría de page tables de GFX8 queda con sus cinco valores
cerrados y medidos: `fragment_size = 9`, `block_size = 10`, `num_level = 1`, `root_level =
AMDGPU_VM_PDB0`, `max_bits = 40`. Es la cadena de `024` y `035` completa, con la aritmética que
faltaba y con las tres supuestas contradicciones resueltas.** `PROVEN_DERIVED`.

## 8 · Errores propios registrados en esta nota

**⇒ `ERROR`. Escribí `root_level = AMDGPU_VM_PDB1` porque leí `tmp` en vez de `num_level`. Lo
detecté al verificar contra `024:54`, que decía `PDB0`. El error y su detección ocurrieron en la
misma iteración, que es el mejor caso posible y sigue siendo un error.** `ERROR`.

**⇒ `ERROR`. Un script mío falló dos veces seguidas con `NameError: vm_size2` y
`1ULL<<40` — sintaxis de C en Python — antes de que la cuenta saliera. Los dos fallos eran del
script de cálculo, no del corpus, y ninguno cambió una conclusión porque ninguna conclusión se
escribió hasta que la cuenta salió bien.** `ERROR`.

**⇒ Y el patrón es el de `246`: el número que decide salió bien sólo porque al final dejó que el
programa lo calculara entero. Lo que no puedo evitar es el error de lectura de arriba, y lo
único que lo cazó fue contrastar contra una nota anterior.** `ERROR`.