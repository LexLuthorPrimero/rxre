# CONTRADICCION PENDIENTE: 014-q1-gpuvm-minimal.md tiene block_size = 9

## Estado

`OPEN`. No se puede cerrar aquí porque el scope `docs` está tomado por otra
sesión (`.write-lock/docs`, PID 73490). Este documento **no** modifica `014`;
solo deja constancia de lo que hay que corregir cuando el lock se libere.

## Qué dice 014 y por qué está mal

`08-ARQUITECTURA/designs/014-q1-gpuvm-minimal.md:69` afirma:

> Con `block_size = 9` (`:2464`, rama `num_level > 1`) y
> `max_level = 1` → `root_level = AMDGPU_VM_PDB0` (`:2452`).

La cita es incoherente consigo misma. `max_level = 1` implica
`num_level = min_t(1, tmp) = 1`, y `1 > 1` es falso, así que la rama
`num_level > 1` **no** se toma. La rama correcta es el `else` de
`amdgpu_vm.c:2454`:

```c
else if (adev->vm_manager.num_level > 1)
        adev->vm_manager.block_size = 9;
else
        adev->vm_manager.block_size = amdgpu_vm_get_block_size(tmp);
```

El recorrido completo está reproducido en `tools/btfq/vmsize.py`, que ejecuta
las mismas líneas del fuente y devuelve `block_size = 10` con los números reales
de esta máquina (`MemTotal = 12098912 kB`, sin parámetros de módulo forzados).

Lo decisivo no es la aritmética sino esto: **el host registra
`block size is 10-bit`**, y eso es una observación. Ninguna lectura de `014`
puede sobreescribirla. Y el modelo que la produce, calculado solo desde el
corpus, coincide con ella.

## La prueba que cierra el caso

```
corpus (vmsize.py)          host (journalctl -k -b)
  block_size = 10             block size is 10-bit
```

Coinciden. `block_size = 9` queda **REFUTED**.

## Consecuencias en cascada

`014` deriva de `block_size = 9`:

| Afirmación de `014` | Estado |
|---|---|
| `BITS_PER_LEVEL = 9` | **REFUTED** — son 10 |
| 512 entradas por nivel | **REFUTED** — son `2^10 = 1024` |
| 4 KiB por tabla de nivel | **REFUTED** — son 8 KiB |
| un PTB cubre 2 MiB | **REFUTED** — son 4 MiB |
| `GPUVA_WIDTH_BITS = 30` | **REFUTED** — el `max_bits` del `adjust_size` es 40 |
| `MIN_VIABLE_ASPACE = 2 MiB` | **REFUTED** — son 4 MiB |
| `root_level = AMDGPU_VM_PDB0` | se mantiene (correcto) |
| entrada de 64 bits | se mantiene: `fragment_size = 9` hace que 512 entradas ocupen exactamente 4 KiB, lo que sigue confirmando 8 B por entrada |

Nota sobre la última fila: la coincidencia de 512 entradas con 4096 B **no**
sostiene el tamaño de nivel, sino el tamaño de la **entrada**. Son cosas
distintas y `014` las confunde.

## Causa raíz: el 9 del fragmento se convirtió en el 9 del nivel

`014` declara las dos cifras juntas:

```
línea 18:  BITS_PER_LEVEL     = 9       PROVEN
línea 36:  fragment_size_default = 9
```

La llamada real es `amdgpu_vm_adjust_size(adev, 64, 9, 1, 40)`, donde el `9` es
`fragment_size_default` y el `40` es `max_bits`. **El `9` que aparece en la
firma es el fragmento, no el block size.** `block_size` no viene en la llamada:
lo decide la rama `else` más abajo, y ahí sale `10`.

Lo que refuerza la confusión es que `512 entradas × 8 B = 4096 B` cuadra
exactamente, y esas 512 entradas **sí** son el fragmento (`2^9`). Así que el
documento tiene un dato correcto —el tamaño del fragmento en bytes— y lo usa
para sostener la cifra equivocada del nivel:

```
entradas de fragmento = 2^9  = 512   ->  512 × 8 B = 4096 B = 4 KiB   <- CORRECTO
entradas por nivel    = 2^10 = 1024  -> 1024 × 8 B = 8192 B = 8 KiB   <- el nivel real
```

Un fragmento de 4 KiB encaja en una página; un nivel de 8 KiB no. El hardware
no obliga a que una tabla de nivel quepa en 4 KiB: la PCB (page table base) es
una dirección de 4 bytes, no un tamaño, y no tiene por qué estar paginada.

## Acción requerida cuando `docs` esté libre

1. Sustituir `BITS_PER_LEVEL = 9` por `10`.
2. Corregir 512 → 1024 entradas, 4 KiB → 8 KiB por tabla de nivel.
3. Corregir la cobertura del PTB de 2 MiB a 4 MiB.
4. Corregir `GPUVA_WIDTH_BITS` de 30 a 40.
5. Corregir `MIN_VIABLE_ASPACE` de 2 MiB a 4 MiB.
6. Corregir la cita de la rama en `:2464`.
7. Dejar explícito que 512 entradas / 4 KiB es el **fragmento**, no el nivel.

Y revisar `04-IMPLEMENTACION/rx550-mem/` y `04-IMPLEMENTACION/rx550-driver/`,
que se escribieron contra la geometría de 512 entradas y 2 MiB.

## Por qué esto importa más de lo que parece

`014-q1-gpuvm-minimal.md` declara **Q1 CLOSED**. Con `BITS_PER_LEVEL` equivocado,
la implementación de page tables derivada de él tiene el granularity equivocado
en el nivel de entrada. Si Q1 está cerrada sobre una cifra refutada, el
`CLOSED` no es válido y lo que herede de él tampoco.

Q1 debería marcarse **CONTRADICTED**, no `CLOSED`, hasta que se corrija.

## Evidencia

- `tools/btfq/vmsize.py` — modelo ejecutable, `rc=0`, coincide con el host.
- `tools/btfq/vmsize.md` — derivación completa y los dos errores de modelo que
  hubo que corregir antes de llegar aquí.
- `RESEARCH/working/.../amdgpu_vm.c:2426-2464` — el cálculo.
- `RESEARCH/working/.../gmc_v8_0.c:1127` — la llamada.
- `journalctl -k -b | grep "vm size is"` — la observación del host.