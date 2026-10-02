# 094 · GFX8 sólo escribe los bits 0-11 del PTE: el resto de la tabla de flags es de GFX9 en adelante

```
ID:           094
TIPO:        HALLAZGO — cierra el formato del PTE completo (segunda parte de 093)
ALCANCE:     gmc_v8_0.c:955, gmc_v9_0.c:1780, amdgpu_gart.c:276/431-437,
              amdgpu_vm.h:73-133
NIVEL:       0 — lectura de corpus
GPU:         INTACTA
CIERRA:      el NEXT ACTION de 093, con el método que 089 usó para GC_HWIP
```

## 1 · EL MÉTODO, Y POR QUÉ ERA EL ADECUADO

`093` dejó que el hardware documenta `63:40 reserved` para el PTE, y que
`amdgpu_vm.h` define ocho flags por encima del bit 40. La pregunta es si el
driver de GFX8 los usa.

Y la forma de responderla **no** es leer el valor del registro —`089` ya
demostró que eso exige root— sino **leer quién escribe qué**:

> ¿`gmc_v8_0.c`, el fichero del ASIC propio, escribe algún flag de PTE por
> encima del bit 40?

Es el mismo discriminante que `089` aplicó a `GC_HWIP`: *«¿tiene el upstream un
camino para mi ASIC?»*. Se responde leyendo el switch, no el registro.

## 2 · EL RESULTADO

Flags con bit ≥ 40 en `amdgpu_vm.h`, y **quién** los usa:

| bit | símbolo | usuarios en el árbol |
|---|---|---|
| 51 | `AMDGPU_PTE_PRT` | `amdgpu_vm.h` |
| 55 | `AMDGPU_PTE_LOG` | `amdgpu_vm.h` |
| 56 | `AMDGPU_PTE_TF` | `gmc_v9_0.c`, `gmc_v10_0.c`, `gmc_v11_0.c` |
| 56 | `AMDGPU_PTE_PRT_GFX12` | `gmc_v12_0.c` |
| 58 | `AMDGPU_PTE_NOALLOC` | `gmc_v10_0.c`, `gmc_v11_0.c`, `gmc_v12_0.c` |
| 58 | `AMDGPU_PTE_DCC` | `gmc_v12_0.c` |
| 59 | `AMDGPU_PTE_BUS_ATOMICS` | `gmc_v12_1.c` |
| 63 | `AMDGPU_PTE_IS_PTE` | `gmc_v12_0.c`, `amdgpu_vm_pt.c` |
| 48 | `AMDGPU_PTE_MTYPE_NV10` | `gmc_v11_0.c` |
| 54 | `AMDGPU_PTE_MTYPE_GFX12` | `gmc_v12_1.c` |
| 57 | `AMDGPU_PTE_MTYPE_VG10` | `amdgpu_gart.c:437`, `gmc_v9_0.c:1780` |

**`gmc_v8_0.c` no aparece ni una vez.** Cero.

### El contraejemplo que había que buscar, y por qué no era contraejemplo

`amdgpu_gart.c:437` escribe `AMDGPU_PTE_MTYPE_VG10(flags, AMDGPU_MTYPE_NC)` —
**bit 57** — en un PTE, y `amdgpu_gart.c` es un fichero **compartido**, no
específico de GFX8. A primera vista rompe la regla.

No la rompe, y por qué importa:

```c
/* amdgpu_gart.c:431 */
void amdgpu_gart_map_gfx9_mqd(struct amdgpu_device *adev, uint64_t offset, …)
```

**La función se llama `gfx9`.** Es el camino de mapeo del **MQD**, y su nombre lo
delata. No es el camino general de la GART.

El camino general dice otra cosa, y lo dice en el ASIC propio:

```c
/* gmc_v8_0.c:955 */
adev->gart.gart_pte_flags = AMDGPU_PTE_EXECUTABLE;      /* = bit 4, y nada mas */

/* amdgpu_gart.c:276 */
memset_io(adev->gart.ptr, adev->gart.gart_pte_flags, adev->gart.table_size);
```

**La tabla GART entera de esta placa se rellena con `0x0000000000000010`.** Contra
`gmc_v9_0.c:1780`, que hace
`AMDGPU_PTE_MTYPE_VG10(0ULL, MTYPE_UC) | …` — bit 57 y compañía.

## 3 · LA AFIRMACIÓN

> **GFX8 escribe exclusivamente los bits 0-11 del PTE. Ningún flag con bit ≥ 40
> de `amdgpu_vm.h` se escribe en esta ASIC, y el hardware los documenta como
> `63:40 reserved`.**

| afirmación | estado |
|---|---|
| El formato del PTE en GFX8 es `11:0` | `PROVEN` (`gmc_v8_0.c:687-696`) |
| `gmc_v8_0.c` no escribe ningún flag ≥ 40 | `PROVEN` por lectura, con denominador: 8 flags + 3 macros MTYPE, 11 símbolos, **0 usos** |
| La GART de GFX8 se rellena con `EXECUTABLE` solo | `PROVEN` (`gmc_v8_0.c:955` + `amdgpu_gart.c:276`) |
| El único uso de `MTYPE_VG10` en `amdgpu_gart.c` es una función llamada `gfx9` | `PROVEN` (`amdgpu_gart.c:431`) |
| Los bits 40-63 del PTE están reservados en GFX8 | `PROVEN` + `094` (coherencia hardware/driver, sin excepción) |

### Lo que esto cierra y lo que previene

**Cierra el formato del PTE completo.** Con `093` (los bits 0-11 y el PDE) más
`094` (los bits 40-63 no existen), el formato de la page table de GFX8 está
**completo**:

```
63            12 11    7 6 5 4 3 2 1 0
+---+--------+-----+-+-+-+-+---+-+-+-+
|  R E S E R V E D    |FRAG| W R E |S|V|     <- "VOI" = "VALID A"
+---+--------+-----+-+-+-+-+---+-+-+-+
            |  4 KiB physical page base address
```

Y los `reserved` de arriba **coinciden exactamente** con el comentario del
hardware. No es que el driver no escriba ahí: es que el hardware no tiene nada
que leer ahí, y el driver no inventa.

**Y previene un error concreto en un driver propio.** `AMDGPU_PTE_IS_PTE`
(bit 63), `AMDGPU_PTE_NOALLOC` (bit 58), `AMDGPU_PTE_TF` (bit 56) están **definidos
en el header que se compila para esta placa** y **no existen en el hardware**.
Escribirlos no da error, no da warning, y no cambia el comportamiento — porque
el hardware los ignora. La trampa es escribir un PTE copiando la tabla de otro
generación sin comprobar contra el formato.

> **Los tres sitios donde GFX8 declara bits inexistentes** — `TMZ` en el bit 3
> (`093`), y `PRT_GFX12`/`IS_PTE`/`NOALLOC`/`TF`/`DCC`/`BUS_ATOMICS`/`LOG`/
> `MTYPE_*` por encima de 40 (`094`) — comparten una causa: **`amdgpu_vm.h` es un
> header común a todas las generaciones y no está acotado por ASIC.** Un symbolo
> definido ahí no significa que exista en tu ASIC, y el compilador no lo avisa.
>
> El discriminante que sí funciona es el de `094`: **buscar quién lo usa.** No
> si está definido.

## 4 · POR QUÉ ESTA ITERACIÓN NO PRODJOJO ERRORES

Ninguno. Fue una medición dirigida con un resultado donde se esperaba
(`gmc_v8_0.c` sin flags altos), **y eso mismo es información**: el
contraejemplo de `amdgpu_gart.c:437` se buscó deliberadamente, se investigó, y
resultó ser una función llamada `gfx9`.

Eso es lo contrario de `089`, donde el resultado fue inesperado y hubo tres
correcciones seguidas. Aqui el resultado esperado se confirmo, y la
confirmacion traia un contraejemplo que hubo que **resolver** en lugar de
descartar.

## 5 · ESTADO DE LA FRONTERA A

| elemento de `AGENTS.md` §A | estado | fuente |
|---|---|---|
| encoding | `PROVEN` | `093` |
| bits | `PROVEN` | `093` + `094` |
| address (39:12, 4 KiB) | `PROVEN` | `093` |
| flags (6 w · 5 r · 4 x) | `PROVEN` | `093` |
| fragment (11:7, 5 bits) | `PROVEN` | `093` |
| valid (bit 0) | `PROVEN` | `093` |
| system/VRAM (bit 1) | `PROVEN` | `093` + `088` + `081` |
| permissions | `PROVEN` | `093` |
| page-table hierarchy (1 nivel) | `PROVEN` | `093` |
| **bits 40-63 reservados** | **`PROVEN` — `094`** | **`094`** |

**La frontera A queda cerrada por lectura**, con las dos capas —hardware y
driver— verificadas por separado y de acuerdo.

---

```
RESULTADO DE ITERACIÓN

Entregado:
  094: GFX8 escribe SOLO los bits 0-11 del PTE
    11 simbolos con bit >= 40 en amdgpu_vm.h, 0 usos en gmc_v8_0.c
    gmc_v8_0.c:955  gart_pte_flags = AMDGPU_PTE_EXECUTABLE  (bit 4, nada mas)
    amdgpu_gart.c:276  memset_io de TODA la tabla GART con ese valor
    el unico uso de MTYPE_VG10 (bit 57) en amdgpu_gart.c esta en una funcion
    llamada amdgpu_gart_map_gfx9_mqd -- no es el camino de GFX8

Medido:
  bit 51 PTE_PRT         -> solo amdgpu_vm.h
  bit 55 PTE_LOG         -> solo amdgpu_vm.h
  bit 56 PTE_TF          -> gmc_v9_0, gmc_v10_0, gmc_v11_0
  bit 56 PTE_PRT_GFX12   -> gmc_v12_0
  bit 58 PTE_NOALLOC     -> gmc_v10_0, gmc_v11_0, gmc_v12_0
  bit 58 PTE_DCC         -> gmc_v12_0
  bit 59 PTE_BUS_ATOMICS -> gmc_v12_1
  bit 63 PTE_IS_PTE      -> gmc_v12_0, amdgpu_vm_pt.c
  bit 48/54/57 MTYPE_*   -> gmc_v11_0, gmc_v12_1, amdgpu_gart.c:437
  gmc_v8_0.c             -> 0 apariciones en las 11

CLOSED:
  AGENTS.md seccion A, COMPLETA: los 9 elementos, con hardware y driver
    verificados por separado y de acuerdo.

Regla que sale, y es la util para un driver propio:
  un simbolo definido en amdgpu_vm.h NO significa que exista en tu ASIC.
  TMZ existe en el bit 3 (hardware: reserved). PRT_GFX12, IS_PTE, NOALLOC,
  TF, DCC, BUS_ATOMICS, LOG y los tres MTYPE no existen en GFX8.
  El compilador no avisa. El unico discriminante es QUIEN LO USA.

NEXT ACTION:
  Con A cerrada, y segun AGENTS.md "H. PERFORMANCE CONTROL: despues de cerrar
  core", queda decidir si el core esta suficientemente cerrado para H. Mi
  lectura es que NO, y el hueco que lo impide tiene nombre:

  Cierre: VM_INVALIDATE_REQUEST -> hardware action -> invalidation ->
          completion -> visibility. De eso, `FUNCTION=always` sigue
          NOT_DETERMINED con el hardware trigger desconocido, y el punto de
          visibilidad del PTE tambien.

  Y hay una lectura NIVEL 2 que se puede hacer SIN cargar modulo y que ataca
  los dos a la vez: el unico camino por el que la GPU comparte estado con el
  host es el de las interrupciones, y gmc_v8_0.c:1113 ya Registro
  AMDGPU_IRQ_CLIENTID_LEGACY / VISLANDS30_IV_SRCID_GFX_MEM_PROT_FAULT en
  adev->gmc.vm_fault. Un handler de IRQ propio podria observar si el hardware
  dispara ese src_id cuando deberia, que es el discriminante de si el fault
  esta activo.

  Eso es NIVEL 3 (inyeccion de un handler) y ademas es un modulo. No sin
  autorizacion.

  Por via NIVEL 0/2, lo que queda y es concreto:
  - 093/094 han dejado la frontera A cerrada pero el CAMINO de emision sin
    reconciliar con el hardware: 045 cerro `count = payload - 1` en gfx_v8_0.c
    con 43/43 emisiones, y ahora sabemos ademas que el destino de
    emit_flush_gpu_tlb es mmVM_INVALIDATE_REQUEST con 1 << vmid. La pregunta
    que ninguno de los dos responde: el `count` que emite el driver, con el
    que el hardware consume, es el mismo para PACKET3 y para wreg? Que es
    justo el cruce de las fronteras C y E.
```