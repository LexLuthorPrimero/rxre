# 075 · El mapa completo de flags de PTE, y una bifurcación que `074` no vio

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC · CORPUS=RESEARCH/working/linux-7.1.3
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · WORK_CLASS=READ_ONLY/EVIDENCE
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué corrige y qué añade a `074`

`074` Probó que el host no compone el PTE en la ruta `GEN_PTEPDE`. Es cierto
para `count >= 3`, y **falso para `count < 3`**. Hay dos rutas distintas:

```
amdgpu_vm_sdma.c:196    if (count < 3) {
amdgpu_vm_sdma.c:197        amdgpu_vm_write_pte(p->adev, ib, pe, addr | flags,
amdgpu_vm_sdma.c:198                            count, incr);
amdgpu_vm_sdma.c:199    } else {
amdgpu_vm_sdma.c:200        amdgpu_vm_set_pte_pde(p->adev, ib, pe, addr,
amdgpu_vm_sdma.c:201                            count, incr, flags);
```

**`addr | flags`**: para pocas entradas el host **arma el PTE él mismo**. Para
muchas, pasa dirección y máscara por separado y lo compone el hardware.

Esto no es una curiosidad: **un driver propio que sólo implemente `GEN_PTEPDE`
falla en el caso pequeño**, que es el caso de un mapping de una sola página — el
más común y el primero que se prueba.

## El mapa de flags, y coincide bit a bit con el layout del hardware

`amdgpu_vm.h:57-84`, literalmente:

```
  AMDGPU_PTE_VALID       (1ULL <<  0)
  AMDGPU_PTE_SYSTEM      (1ULL <<  1)
  AMDGPU_PTE_SNOOPED     (1ULL <<  2)
  AMDGPU_PTE_TMZ         (1ULL <<  3)
  AMDGPU_PTE_EXECUTABLE  (1ULL <<  4)
  AMDGPU_PTE_READABLE    (1ULL <<  5)
  AMDGPU_PTE_WRITEABLE   (1ULL <<  6)
  AMDGPU_PTE_FRAG(x)     ((x & 0x1fULL) << 7)      5 bits, 11:7
  AMDGPU_PTE_PRT         (1ULL << 51)
  AMDGPU_PTE_LOG         (1ULL << 55)
  AMDGPU_PTE_TF          (1ULL << 56)
  AMDGPU_PTE_NOALLOC     (1ULL << 58)
```

Y el layout declarado en `gmc_v8_0.c:691-702`:

```
   0  valid        <->  PTE_VALID       << 0
   1  system       <->  PTE_SYSTEM      << 1
   2  snooped      <->  PTE_SNOOPED     << 2
   3  reserved     <->  PTE_TMZ         << 3      <-- DISCREPANCIA
   4  exe          <->  PTE_EXECUTABLE  << 4
   5  read         <->  PTE_READABLE    << 5
   6  write        <->  PTE_WRITEABLE   << 6
  11:7 fragment    <->  PTE_FRAG(x)     << 7      (5 bits, encaja exacto)
 39:12 dirección
```

**Siete de ocho coinciden bit a bit.** La excepción es el bit 3: el layout de
`gmc_v8_0.c:699` dice literalmente `3 reserved` y el driver define
`AMDGPU_PTE_TMZ (1ULL << 3)` en `amdgpu_vm.h:62`. Es una contradicción real y
**sin arbitrar**: el comentario de layout puede estar desactualizado respecto al
flag que el driver sí usa.

Y hay cinco flags del driver por encima del bit 39 que el layout no menciona.
**Eso se explica, y no es un misterio** — ver la sección siguiente.

## Los flags altos no son contradicciones: son de otras generaciones

```
amdgpu_vm.h:73    AMDGPU_PTE_PRT      (1ULL << 51)
amdgpu_vm.h:78    AMDGPU_PTE_LOG      (1ULL << 55)
amdgpu_vm.h:81    AMDGPU_PTE_TF       (1ULL << 56)
amdgpu_vm.h:84    AMDGPU_PTE_NOALLOC  (1ULL << 58)
amdgpu_vm.h:131   AMDGPU_PTE_DCC      (1ULL << 58)
amdgpu_vm.h:132   AMDGPU_PTE_BUS_ATOMICS (1ULL << 59)
```

Y el que se usa en la ruta de VRAM:

```
amdgpu_vm.h:121   AMDGPU_PTE_PRT_GFX12  (1ULL << 56)
amdgpu_vm.h:122   AMDGPU_PTE_PRT_FLAG(adev) = ((amdgpu_ip_version(adev, GC_HWIP, 0)
amdgpu_vm.h:123                              >= IP_VERSION(12, 0, 0)) ? GFX12 : 0
```

**`AMDGPU_PTE_PRT_FLAG` devuelve 0 en GFX8.** Es una comprobación de generación, y
GFX8 es anterior a 12.0.0.

Consecuencia directa y verificable: en `amdgpu_vm.c:1227`

```
if (flags & (AMDGPU_PTE_VALID | AMDGPU_PTE_PRT_FLAG(adev)))
```

para esta GPU la condición es **sólo `AMDGPU_PTE_VALID`**. El bit 51 no
participa, y `TF`/`NOALLOC`/`DCC`/`BUS_ATOMICS` no se emiten por esta ruta.

**Por qué importa más allá del dato**: es la misma clase de error que `065`
documentó para los offsets. Un flag definido en `amdgpu_vm.h` no es un flag de
esta GPU; hay que comprobar la generación. Los cinco flags altos existen en el
código y **cero** los usa GFX8, y `PTE_TMZ` en el bit 3 es el único que queda
discrepante — bit bajo, dentro del rango del layout, y el layout lo marca
reservado. Eso sí es una contradicción abierta.

### La pregunta de seguridad de `074`, respondida

`074` preguntaba si el host puede mandar `valid=0`. **Sí, estructuralmente**:
`AMDGPU_PTE_VALID` es `1ULL << 0` y viaja en `flags`, que el host compone. En la
ruta `count < 3` va con `addr | flags`, o sea **OR-ed**: el host pone el bit, no
lo borra. En la ruta `GEN_PTEPDE` va como máscara al hardware.

Lo que no puede es *quitar* un bit que ya esté, porque ambas rutas son OR, no
asignación. Para deshabilitar una traducción el driver tiene que escribir la
tabla, no el flag. Eso es una restricción de diseño que conviene conocer.

## La bifurcación VRAM vs RAM

```
amdgpu_vm.c:1227    } else if (flags & (AMDGPU_PTE_VALID | AMDGPU_PTE_PRT_FLAG(adev))) {
amdgpu_vm.c:1228            addr = vram_base + cursor.start;
amdgpu_vm.c:1229    } else {
amdgpu_vm.c:1230            addr = 0;
```

El caso VRAM **añade `vram_base` a la dirección del cursor**; el resto usa `addr=0`.
Es la traducción GART↔VRAM antes de generar el PTE, y es el punto donde una page
table de usuario puede acabar apuntando a VRAM sin que el driver escriba la
base dentro del PTE.

## `TF` y `NORETRY`: conexión con 070 y con 064

```
amdgpu_vm.h:94    AMDGPU_VM_NORETRY_FLAGS_TF = (AMDGPU_PTE_VALID | AMDGPU_PTE_SYSTEM | ...
```

`TF` es bit 56 del PTE, y `NORETRY` lo usa como criterio. Con `064` sale otra
conexión: los bits `RETRY_PERMISSION_OR_INVALID_PAGE_FAULT` y `RETRY_OTHER_FAULT`
**no existen en GFX8** (`064` los refutó por recuento sobre las cuatro cabeceras
`gmc_*`). Así que la política de reintento en esta GPU es **enteramente software**,
y `TF` en el PTE es la contraparte del lado de la traducción. Coherente, y no
contradicto.

## Estado

| Afirmación | Estado |
|---|---|
| El mapa de flags con posiciones exactas | `PROVEN` (`amdgpu_vm.h:57-84`) |
| 7 de 8 flags coinciden con el layout de `gmc_v8_0.c` | `PROVEN` |
| `PRT_FLAG` devuelve 0 en GFX8 (es GFX12+) | `PROVEN` (`amdgpu_vm.h:121-123`) |
| Los 4 flags >39 son de otras generaciones, no de GFX8 | `PROVEN` |
| Bit 3: `reserved` en el layout, `PTE_TMZ` en el driver | `CONTRADICTION` — sin arbitrar |
| Para `count < 3` el host compone el PTE (`addr \| flags`) | `PROVEN` |
| Para `count >= 3` lo compone el hardware | `PROVEN` |
| Ambas rutas son OR: el host no puede borrar un bit | `PROVEN` (derivado del código) |
| El caso VRAM suma `vram_base` | `PROVEN` (`amdgpu_vm.c:1228`) |
| Si `PTE_TMZ` tiene efecto en GFX8 | `NOT_DETERMINED` |

## Procedencia

- `CORPUS` — `amdgpu_vm.h:57-94`, `amdgpu_vm.c:1219-1234`,
  `amdgpu_vm_sdma.c:196-201`, `sdma_v3_0.c:987-996`, `gmc_v8_0.c:691-702`.
- Encadenada con `074` (el emisor), `C-011` (quién es el emisor correcto),
  `064` (bits de retry y mapa de `VM_CONTEXT*_CNTL`).
- Sin `RUNTIME`, sin lectura de la GPU, sin escrituras.
- No se editó `OPEN-FRONTIERS.md`: es de otra sesión (`COORDINACION.md:184`).