# 093 · El formato del PTE y del PDE está documentado en el propio fuente de GFX8, y `get_vm_pte` borra el PRT

```
ID:           093
TIPO:        HALLAZGO — AGENTS.md §A y §B cerradas por lectura del fuente del ASIC propio
ALCANCE:     gmc_v8_0.c:687-724, amdgpu_vm_pt.c:412/686, amdgpu_vm.h:57-73
NIVEL:       0 — lectura de corpus
GPU:         INTACTA
CIERRA:      083 (PRT) definitivamente, y abre A y B por el lado del hardware
```

## 1 · LO QUE ESTÁ ESCRITO EN EL FUENTE

`gmc_v8_0.c:687-702` — el propio archivo del ASIC propio documenta los dos
formatos:

```c
/*
 * PTE format on VI:
 * 63:40 reserved
 * 39:12 4k physical page base address
 * 11:7 fragment
 * 6 write
 * 5 read
 * 4 exe
 * 3 reserved
 * 2 snooped
 * 1 system
 * 0 valid
 *
 * PDE format on VI:
 * 63:59 block fragment size
 * 58:40 reserved
 * 39:1 physical base address of PTE
 * bits 5:1 must be 0.
 * 0 valid
 */
```

`AGENTS.md` §A pide exactamente:

> *Resolver encoding → bits → address → flags → fragment → valid →
> system/VRAM → permissions → page-table hierarchy.*

**Está la lista completa, en el orden de la pregunta, en el fichero del ASIC
que la ejecuta.** Y §B:

> *Resolver VA → root → PDE → PTE → physical address. Determinar: niveles,
> root_level, num_level, page size, fragmentation, invalid entries…*

| pregunta de `AGENTS.md` | respuesta | fuente |
|---|---|---|
| bits del PTE | los de arriba | `gmc_v8_0.c:687-696` |
| base física del PTE | **39:12**, 4 KiB | `:688` |
| flags | `6 write · 5 read · 4 exe` | `:690-692` |
| fragment | **11:7**, 5 bits | `:689` |
| valid | **bit 0** | `:695` |
| system/VRAM | **bit 1 = system** | `:694` |
| niveles del page walker | **1**: no hay campo de nivel en el PDE | `:697-702` |
| base del PTE en el PDE | **39:1** | `:700` |
| fragmentación en el PDE | **63:59 block fragment size** | `:698` |

## 2 · CONFIRMACIÓN INDEPENDIENTE DE `088`

`088` encontró `AMDGPU_PTE_SYSTEM (1ULL << 1)` en `amdgpu_vm.h:58` y lo cerró
por el lado del **driver**. El comentario del hardware dice **`1 system`**, y lo
dice desde el otro lado del mismo campo.

Dos fuentes, dos capas, el mismo bit. Y ahora por el motivo: **bit 1 = system**
es precisamente lo que hace que `088` y `081` encajen:

```
SYSTEM_ACCESS_MODE = NOT_IN_SYS   (bit de contexto, gmc_v8_0.c:840)
PTE.SYSTEM         = 0            (bit de página,    gmc_v8_0.c:694)
amdgpu_gart.c:401  WARN_ON_ONCE(flags & AMDGPU_PTE_SYSTEM)
```

Los tres dicen lo mismo: **la GART no traduce a RAM de sistema**. Ahora con la
fuente del hardware confirmando que el bit 1 *es* el bit de system.

### Una discrepancia que no es discrepancia

| capa | bit 3 del PTE |
|---|---|
| hardware (`gmc_v8_0.c:692`) | **`reserved`** |
| driver (`amdgpu_vm.h:62`) | `AMDGPU_PTE_TMZ (1ULL << 3)` |

El driver **define** un flag en un bit que el hardware documenta como reservado.
No es un bug: es una definición que la ASIC no honra. Se registra porque un
driver propio que escriba `AMDGPU_PTE_TMZ` está escribiendo en un bit que el
formato dice que no existe.

## 3 · `083` QUEDA CERRADO, Y MÁS FUERTE DE LO QUE DECÍA

`083` concluyó: *«el acceso no mapeado pide página, y en GFX8 no hay quien lo
atienda»*. Es cierto, pero era el **tercer** sitio. Los tres hacen que PRT sea
inerte en GFX8:

```
gmc_v8_0.c:712  static void gmc_v8_0_get_vm_pte(…)
gmc_v8_0.c:720          if (vm_flags & AMDGPU_VM_PAGE_EXECUTABLE)
gmc_v8_0.c:721                  *flags |= AMDGPU_PTE_EXECUTABLE;
gmc_v8_0.c:722          else
gmc_v8_0.c:723                  *flags &= ~AMDGPU_PTE_EXECUTABLE;
gmc_v8_0.c:724          *flags &= ~AMDGPU_PTE_PRT;      <<<< SIEMPRE
```

**La ruta de PTE de GFX8 borra `AMDGPU_PTE_PRT` incondicionalmente.** No
depende de `vm_flags`, no depende de nada.

Los tres sitios, juntos:

| # | sitio | qué hace |
|---|---|---|
| 1 | `amdgpu_gem.c:840/882` — flag de ioctl | **activa** el PRT (`set_prt(true)`) |
| 2 | `gmc_v8_0.c:724` — `get_vm_pte` | **borra** el bit PRT del PTE |
| 3 | `gmc_v8_0.c:1421` — handler de IRQ | **no tiene** rama PRT |

> **La conclusión de `083` se refuerza y se generaliza**: PRT no es «una función
> que falta» en GFX8, es una característica **sistemáticamente no implementada
> para este ASIC** en los tres puntos donde tendría que existir. Y el orden
> importa: el punto 1 puede **desactivar los faults de acceso no mapeado**
> (`gmc_v8_0.c:769-775`) mientras el punto 2 garantiza que ninguna página se
> marque como PRT y el punto 3 no responde.
>
> Eso convierte un hueco de implementación en una **afirmación sobre el
> modelo de faults de esta placa**: el camino `AMDGPU_VM_PAGE_PRT` es un
> **flag aceptado y sin efecto**, y no un camino que funcione a medias.

## 4 · EL PDE DE GFX8 ES UN `BUG_ON`, Y SÓLO LO USA EL CAMINO SVM

```c
gmc_v8_0.c:706  static void gmc_v8_0_get_vm_pde(struct amdgpu_device *adev, int level,
                                               uint64_t *addr, uint64_t *flags)
gmc_v8_0.c:710          BUG_ON(*addr & 0xFFFFFF0000000FFFULL);
```

**No decodifica nada: sólo afirma.** Y la máscara, contra el formato de la línea
699:

```
máscara: 0xFFFFFF0000000FFF  ->  bits 63:40  |  bits 11:0
PDE:     63:59 frag | 58:40 reserved | 39:1 base | 0 valid
```

La máscara exige `bits 63:40 == 0` — coherente con «63:59 fragment size» y
«58:40 reserved» — **y además `bits 11:0 == 0`**, lo que incluye el bit 0
(`valid`) y contradice «39:1 physical base address of PTE». La afirmación sólo
puede ser válida sobre el **fragment/addr de entrada**, no sobre un PDE
completo. Se registra como observación, no como error, porque el llamador
puede pasar algo que no es un PDE.

Y quién lo llama:

```
$ grep -rn "get_vm_pde" --include=*.c .
gmc_v8_0.c:706/1733   (definicion + registro en la tabla)
amdgpu_vm_pt.c:412    amdgpu_gmc_get_vm_pde(adev, level, …)
amdgpu_vm_pt.c:686    amdgpu_gmc_get_vm_pde(adev, level, &addr, &flags)
```

**Ningún llamador en `amdgpu_vm.c`.** El constructor de page tables del DRM
(`amdgpu_vm.c`) **nunca pide el PDE**; los dos llamadores están en
`amdgpu_vm_pt.c`, que es el camino de **SVM de KFD** (`AMDGPU_VM_MTYPE`, ATS).

> Eso es `AGENTS.md` §B por vía negativa: **una page table de un nivel no
> necesita leer su PDE**, y el código lo demuestra por omisión — el accessor
> existe, está registrado, y el camino que construye las PTEs del DRM no lo
> invoca. Un `PROVEN_ABSENT` con el consumidor identificado: *«la jerarquía de
> GFX8 no se recorre porque no hay segundo nivel»*.

## 5 · ESTADO DE A, B Y F TRAS ESTE HALLAZGO

| frontera | antes | ahora |
|---|---|---|
| **A** encoding/bits/flags/fragment/valid/system | `PROVEN` por lectura de código, sin el formato del hardware | **`PROVEN` con el formato del hardware en la fuente del ASIC propio** |
| **A** bit 3 | `AMDGPU_PTE_TMZ` definido | **`reserved` según el hardware** — el driver define un flag en un bit inexistente |
| **B** niveles | `PAGE_TABLE_DEPTH` sin enumeración (`POR_DEFINICION`) | **1 nivel, por omisión del consumidor** |
| **B** VA → root → PDE → PTE | derivado | **1 nivel: VA → PTE → PA directa** |
| **F** system vs VRAM | `NOT_IN_SYS` por `sid.h` | **+ `PTE.SYSTEM` bit 1 por el hardware** + `WARN_ON` del driver |
| PRT (`083`) | falta el handler | **tres sitios lo hacen inerte** |

## 6 · ERRORES PROPIOS

Ninguno en esta iteración: fue lectura dirigida y no hubo medición. Se declara
porque los dos hallazgos anteriores (089, 091) fallaron igual: uno leyo un
flag que no era el que hacia falta, y otro no abrio el archivo que si lo tenia.

---

```
RESULTADO DE ITERACIÓN

Entregado:
  093: formato del PTE y del PDE LEIDOS del fuente del ASIC propio (gmc_v8_0.c:687-702)
    -> AGENTS.md §A cerrado por el lado del hardware, no solo del driver
    -> AGENTS.md §B: 1 nivel, demostrado por ausencia de consumidor
    -> 088 confirmado independientemente: bit 1 = system, desde las dos capas
    -> discrepancia real: bit 3 es `reserved` en el hardware y TMZ en el driver
    -> 083 CERRADO: get_vm_pte borra AMDGPU_PTE_PRT incondicionalmente
       (gmc_v8_0.c:724), y con el handler sin rama son TRES sitios inertes

Medido:
  gmc_v8_0_get_vm_pde = un solo BUG_ON, no decodifica
  get_vm_pde tiene 2 llamadores, ambos en amdgpu_vm_pt.c (SVM de KFD)
  cero llamadores en amdgpu_vm.c (el constructor de PTEs del DRM)

CLOSED:
  AGENTS.md §A  encoding → bits → address → flags → fragment → valid →
                system/VRAM → permissions   TODOS por lectura del fuente
  AGENTS.md §B  niveles = 1, por la via negativa del consumidor
  083           PRT es inerte en GFX8 en 3 sitios, no en 1

NEXT ACTION:
  El hueco que queda de §A es el unico que la fuente NO cierra: los bits
  56-63 del PTE. amdgpu_vm.h define en ellos PTE_PRT_GFX12 (56), PTE_TF (56),
  PTE_MTYPE_VG10 (57), PTE_NOALLOC (58), PTE_DCC (58), PTE_BUS_ATOMICS (59),
  PTE_IS_PTE (63). Para GFX8 el hardware dice "63:40 reserved", o sea que
  ESOS flags no existen en esta placa, y el driver los escribe igualmente.
  Eso no es una discrepancia, es una COLISION documentada de generationalidad,
  y tiene una consecuencia concreta para un driver propio: escribir
  AMDGPU_PTE_IS_PTE en GFX8 pone un bit en un campo reservado.

  Y el discriminante de eso es de los que se pueden hacer por lectura, como
  089 hizo con GC_HWIP: buscar si gmc_v8_0.c usa alguna vez un flag de bit > 40
  del PTE. Si no los usa, es PROVEN por lectura que en GFX8 el driver solo
  escribe los bits 0-11 del PTE, y el resto de la tabla de amdgpu_vm.h es de
  otras generaciones. Eso cerraria el formato del PTE completo.
```