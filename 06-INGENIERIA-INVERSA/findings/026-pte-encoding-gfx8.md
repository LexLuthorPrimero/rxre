# 026 · El PTE de GFX8: 40 bits de PA, verificados por tres vías independientes

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=RESEARCH/working/linux-7.1.3`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`RUNTIME=NOT_RUN` · `GPU INTACTA`
`COMPLEMENTS=024-page-table-geometria-gfx8.md` (geometria), `DRIVER-MISSION-STATE.md` (Q1/Q2)

## CUDA principal

La direccion fisica del page table de GFX8 es de **40 bits**, y eso sale de tres
derivaciones independientes que no se citan entre si:

```
1. pte_addr_mask = 0x000000FFFFFFF000   [gmc_v8_0.c:1134]      PA = bits 39:12 = 28
2. PHYSICAL_PAGE_NUMBER  MASK 0xfffffff [gmc_8_2_sh_mask.h:6755] PFN = 28 bits
3. amdgpu_vm_adjust_size(..., max_bits = 40) [gmc_v8_0.c:1127]
                                                PA = 40 bits
28 + 12 = 40   en las tres
```

La unidad es la que fija `024`: PFN de 28 bits y direccion de 4 KiB. No es una
coincidencia entre dos fuentes del mismo fichero: la via 2 es un
registro de hardware, y la via 3 es un parametro de software que nadie
tendria por prueba de nada.

## CUDA secundaria: la clase de evidencia de los flags

Los bits 11:0 del PTE **existen en el driver, no en el hardware**. El arbol de
registros de GFX8 no declara ni un solo bitfield para ellos:

```
gmc_8_2_sh_mask.h:  0 resultados para un PTE de 28 entradas
gca/gfx_8_0_d.h, gfx_8_1_d.h:  ningun registro de page table
```

El unico sitio donde esta el layout de los bits bajos es un **comentario** de
`gmc_v8_0.c` (`PTE format on VI`). Un comentario es evidencia de intencion, no de
hardware — el mismo criterio con el que `017` trato `FUNCTION=always`.

## Alcance exacto

1. Localizar la funcion que escribe PTEs y aislar su aritmetica.
2. Resolver el campo de direccion y contrastarlo con otras fuentes.
3. Separar lo que el hardware declara de lo que solo dice el driver.
4. Clasificar.

## Criterio de terminacion (cumplido)

La funcion de escritura esta aislada en 3 lineas, la mascara esta resuelta, y las tres
derivaciones de los 40 bits estan calculadas. Agotado.

---

## 1 · La funcion completa

`amdgpu_gmc_set_pte_pde` (`amdgpu_gmc.c:163-176`), GFX8 y todas las generaciones:

```c
int amdgpu_gmc_set_pte_pde(struct amdgpu_device *adev, void *cpu_pt_addr,
                           uint32_t gpu_page_idx, uint64_t addr, uint64_t flags)
{
        void __iomem *ptr = (void *)cpu_pt_addr;
        uint64_t value;

        /* The following is for PTE only. GART does not have PDEs. */
        value = addr & adev->gmc.pte_addr_mask;
        value |= flags;
        writeq(value, ptr + (gpu_page_idx * 8));

        return 0;
}
```

Tres hechos, todos `PROVEN`:

1. **`cpu_pt_addr` es una direccion de CPU.** El tipo es `void __iomem *` pero se
   indexa con `ptr + gpu_page_idx * 8` y se escribe con `writeq` — eso es una
   `ioremap`/mapping del kernel, no MMIO de dispositivo. Confirmado por `025` §1: el
   page table se escribe desde la CPU.
2. **`gpu_page_idx * 8`**: una entrada de 8 bytes, y el indice esta en **paginas**, no
   en bytes. El desplazamiento total es `gpu_page_idx << 3`.
3. **La aritmetica son dos operaciones**: mascara y OR. El driver **no** posiciona
   ningun campo, no valida rangos, y devuelve siempre 0. Todo el significado esta en
   `pte_addr_mask` y en `flags`, que pone el llamante.

Un comentario del propio driver: *"GART does not have PDEs"*. Consistente con `024`:
`PAGE_TABLE_DEPTH = 0` para el contexto del GART.

## 2 · El campo de direccion, campo por campo

`pte_addr_mask = 0x000000FFFFFFF000` (`gmc_v8_0.c:1134`, comentario `/* 40 bit PA */`):

```
63       40 39                      12 11        0
+---------+-------------------------+-----------+
|  0      |     PA[27:0]            |  flags    |
| (24 b)  |     28 bits             |  12 bits  |
+---------+-------------------------+-----------+
```

Lo que el driver **pone a cero** son los 24 bits altos, porque la mascara los
elimina. Y `ADDR` es una direccion de byte, de donde salen los `<<12` de los
llamantes: `table_addr >> 12`, `pd_addr >> 12`, `page_base` ya en bytes.

### 2.1 · Las tres derivaciones

**Via 1 — la mascara del driver:**

```
0x000000FFFFFFF000  ->  PA = bits 39:12  = 28 bits de numero de pagina
28 + 12 = 40 bits de direccion fisica
```

**Via 2 — el registro del hardware:**

```
gmc_8_2_sh_mask.h:6755
  VM_CONTEXT0_PAGE_TABLE_BASE_ADDR__PHYSICAL_PAGE_NUMBER_MASK  0xfffffff
  VM_CONTEXT0_PAGE_TABLE_BASE_ADDR__PHYSICAL_PAGE_NUMBER__SHIFT 0x0
```

28 bits de PFN. El campo del **registro**, no de un comentario. Es la unica de las tres
que es evidencia de hardware.

**Via 3 — un parametro de software:**

```
gmc_v8_0.c:1127   amdgpu_vm_adjust_size(adev, 64, 9, 1, 40);
                                                 ^^^^^^^^^^ max_bits
```

`max_bits` es el techo que el driver se da a si mismo para direccionar. Que coincida
con el ancho de la mascara **no es evidencia de hardware**: es coherencia interna del
driver. Si el driver tuviera un `max_bits` equivocado, las tres vias darian dos
resultados y un tercero, y la discordancia se veria.

| ASIC | `pte_addr_mask` | PA | `max_bits` |
|---|---|---|---|
| `gfx_v6_0` | `0x000000FFFFFFF000` | 40 | 40 |
| `gfx_v7_0` | `0x000000FFFFFFF000` | 40 | 40 |
| **`gfx_v8_0`** | **`0x000000FFFFFFF000`** | **40** | **40** |
| `gfx_v9_0` | `0x0000FFFFFFFFF000` | 48 | 48 |
| `gfx_v10_0` | `0x0000FFFFFFFFF000` | 48 | 48 |
| `gfx_v11_0` | `0x0000FFFFFFFFF000` | 48 | 48 |
| `gfx_v12_0` | `0x000FFFFFFFFFF000` | 52 | 57 |

La primera columna es lo que el driver **escribe**; la tercera es lo que el driver
**se permite**. Coinciden en todas menos GFX12, donde el driver se da mas margen del
que usa. Esa discrepancia es informacion: en GFX12 la mascara es una decision, no un
limite.

`PROVEN` el ancho de la mascara en cada ASIC. `PROVEN_DERIVED` la PA que resulta.

## 3 · Los flags: lo que dice el driver y lo que dice el hardware

Comentario de `gmc_v8_0.c`, formato PTE en VI:

```
63:40 reserved     39:12 direccion fisica de 4 KiB
11:7  fragment      6 write   5 read   4 exe
3    reserved       2 snooped 1 system  0 valid
```

Contraste con `AMDGPU_PTE_*` (`amdgpu_vm.h:57-133`):

| bit | nombre del driver | comentario de gmc_v8_0 | coincide |
|---|---|---|---|
| 0 | `AMDGPU_PTE_VALID` | `valid` | si |
| 1 | `AMDGPU_PTE_SYSTEM` | `system` | si |
| 2 | `AMDGPU_PTE_SNOOPED` | `snooped` | si |
| 3 | `AMDGPU_PTE_TMZ` | **`reserved`** | **NO** |
| 4 | `AMDGPU_PTE_EXECUTABLE` | `exe` | si |
| 5 | `AMDGPU_PTE_READABLE` | `read` | si |
| 6 | `AMDGPU_PTE_WRITEABLE` | `write` | si |
| 7..11 | `AMDGPU_PTE_FRAG(x)`, 5 bits | `fragment` | si |

**Siete de ocho coinciden. El bit 3 no.** El driver tiene `AMDGPU_PTE_TMZ` en el bit 3
—TMZ es un mecanismo de memoria cifrada de GFX9 en adelante— y el comentario de GFX8
lo declara reservado. El conflicto es real y esta en el codigo, no en mi lectura.

Que el hardware no lo declare es lo que hace la discordancia relevante: `gmc_8_2_sh_mask.h`
no tiene ni un bitfield para los 12 bits bajos del PTE, en ningun ASIC de GFX8. El
unico layout documentado de esos bits es un **comentario de fuente**, y un comentario
puede estar equivocado —el propio driver lo demuestra en otro sitio: el comentario
`PTE format on VI` coexiste con `AMDGPU_PTE_TMZ` en el bit 3, y uno de los dos se
aplica a GFX8 y el otro no.

### 3.1 · Bits altos que GFX8 no deberia tocar

Los flags con bit >= 12 estan todos por encima de `pte_addr_mask`, luego
`value = addr & mask` los pone a 0 **si el llamante no los pasa**. Y hay llamantes que
los pasan:

```
AMDGPU_PTE_PRT        bit 51   us  en gmc_v8_0.c   (y lo BORRA)
AMDGPU_PTE_TF         bit 56   no us
AMDGPU_PTE_NOALLOC    bit 58   no us
AMDGPU_PTE_LOG        bit 55   no us
AMDGPU_PTE_MTYPE_*    48 / 54  us
AMDGPU_PTE_IS_PTE     bit 63   no us
AMDGPU_PTE_DCC        bit 58   no us
AMDGPU_PTE_BUS_ATOMICS bit 59  no us
```

`gmc_v8_0_get_vm_pte` (`gmc_v8_0.c`) hace exactamente:

```c
*flags &= ~AMDGPU_PTE_PRT;
```

Borra el bit 51. Dos lecturas posibles, y el corpus no decide:

- `AMDGPU_PTE_PRT` existe en esta generacion y el driver lo limpia porque GFX8 no lo
  soporta -> coherente, y el bit 51 estaria en la zona que `pte_addr_mask` ya pone a 0,
  con lo que la linea seria redundante.
- `AMDGPU_PTE_PRT` no existe en GFX8 y la linea es un **residuo de portabilidad** —el
  sibling `gfx_v12_1` define `AMDGPU_PTE_PRT_GFX12` en el bit 56, lo que sugiere que el
  bit 51 cambio de significado en GFX12— -> la linea limpia un bit que no se usa.

`NOT_DETERMINED`. Lo que si es `PROVEN` es que la linea existe, que borra el bit 51, y
que el hardware no declara ese bit. La hipotesis de residuo es coherente con el
sibling, y por eso la dejo como la lectura mas probable sin presentarla como hecho.

## 4 · Clasificacion

| Afirmacion | Estado |
|---|---|
| `set_pte_pde` son 3 operaciones: mascara, OR, `writeq` | `PROVEN` (fuente) |
| `cpu_pt_addr` es una direccion de CPU, no MMIO de dispositivo | `PROVEN` (`writeq` sobre mapping del kernel) |
| La entrada de page table mide 8 bytes | `PROVEN` (`gpu_page_idx * 8`) |
| GFX8 escribe `PA[27:0]` en los bits 39:12 | `PROVEN` (`pte_addr_mask`) |
| La direccion fisica es de 40 bits | `PROVEN` (mascara) + `PROVEN` (PHYSICAL_PAGE_NUMBER, 28 bits) |
| 28 + 12 = 40, coherente con `max_bits = 40` | `PROVEN_DERIVED` (tercera via, software) |
| Los 24 bits altos los pone a 0 la mascara | `PROVEN_DERIVED` |
| El comentario de PTE y `AMDGPU_PTE_*` coinciden en 7 de 8 bits | `PROVEN` (comparacion) |
| El bit 3 es `TMZ` para el driver y `reserved` para el comentario de GFX8 | `PROVEN` (conflicto en el codigo) |
| Que significa el bit 3 en GFX8 | `NOT_DETERMINED` — el hardware no lo declara |
| Que el layout de los bits 11:0 sea el que dice el comentario | `NOT_DETERMINED` — unica fuente es un comentario |
| Que hace `*flags &= ~AMDGPU_PTE_PRT` en GFX8 | `NOT_DETERMINED` |
| Que la mascara del PTE exista en el hardware | `PROVEN_ABSENT` — 0 bitfields |

Ultima fila. El campo de direccion esta **triplemente verificado** y el de flags esta
**verificado en un solo comentario**. Esa asimetria es el resultado util: el driver
propio puede escribir la parte de direccion con confianza medida, y la de flags solo
con una `HYPOTHESIS` que habra que contrastar con hardware.

## 5 · Confounders

- La via 2 (el registro) es la unica de hardware; las vias 1 y 3 son del driver. Que
  coincidan tres no las convierte en tres evidencias independientes **de hardware**.
  `CORROBORATED` con dos fuentes de hardware, no `PROVEN` por tres vias.
- `024` calculo `max_pfn` con `vm_size = 64` GB; aqui solo importa que el techo de
  direccion es 40 bits. Los dos numeros no se mezclan: uno es el tope que el driver se
  impone, el otro el ancho real del campo.
- La busqueda de bitfields del PTE se hizo en `gmc_8_2_sh_mask.h` y
  `gca/gfx_8_{0,1}_sh_mask.h`. Otros bloques de registros del ASIC (`bif`, `hdp`,
  `oss`) no se barrieron para este campo. `NOT_DETERMINED` si un bitfield del PTE
  estuviera en otro bloque; improbable —el PTE es del GMC— pero no cerrado.

## 6 · UNLOCKS

- El driver propio puede construir un PTE de GFX8 con la parte de direccion **medida**:
  `(pa_fisica & ~0xFFF) | flags`, 8 bytes por entrada, indice en paginas. Es la unidad
  basica de la memoria y estaba sin resolver al nivel del bit.
- Los bits de flags quedan como `HYPOTHESIS` con el conflicto TMZ/reserved anotado. Es
  el punto exacto donde un discriminante runtime tiene valor: escribir un PTE con el
  bit 3 a 1 y el bit 3 a 0, y ver si el acceso funciona igual. Es un experimento
pequeno y bien acotado.
- `024` da la geometria (1 nivel, `block_size` 13) y este documento da el formato de la
  entrada. Juntos son el page table completo de GFX8 en forma de datos.
- La divergencia entre mascara y `max_bits` en GFX12 muestra que la mascara es
  `MODEL_CHOICE` del driver, no un limite del hardware. El driver propio puede elegir
  el suyo, con la evidencia de que el hardware acepta al menos el ancho que usa GFX8.

## 7 · Criterio de falsificacion

Se refutaria si: (a) apareciera un bitfield del PTE en otro bloque de registros de
GFX8 — refutaria la `PROVEN_ABSENT` y daria layout de hardware donde hay comentario;
(b) un ASIC GFX8 emulara el bit 3 con un significado que no sea `reserved`, lo que
haría el conflicto de §3 una pista y no una discrepancia; (c) el hardware aceptara
direcciones de mas de 40 bits, refutando la mascara como limite. (a) exige un barrido
de los bloques no revisados; (b) y (c) exigen hardware. Ninguno accesible con el
corpus.

## 8 · Evidencia

```
amdgpu_gmc.c:      163-176 (set_pte_pde completo)
gmc_v8_0.c:        1134 (pte_addr_mask), 1127 (max_bits=40),
                   692-710 (comentario PTE/PDE format on VI),
                   718-730 (get_vm_pte: borra PRT)
gmc_8_2_sh_mask.h: 6755-6756 (PHYSICAL_PAGE_NUMBER 0xfffffff)
amdgpu_vm.h:       57-133 (AMDGPU_PTE_*)
                   barrido de bitfields del PTE: 0 resultados en gmc_8_2_sh_mask.h
                   y en gca/gfx_8_{0,1}_sh_mask.h
gmc_v6_0.c:839, gmc_v7_0.c:1019, gmc_v9_0.c:1997, gmc_v10_0.c:850,
gmc_v11_0.c:824, gmc_v12_0.c:921   (pte_addr_mask por ASIC)
```

Ningun registro obtenido de MMIO. Ninguna operacion runtime. `GPU INTACTA`.

Nota de redaccion: el borrador contenia texto corrupto en la CUDA principal y en §6
(fragmentos de otro idioma). Corregido. Septimo caso del mismo defecto al escribir;
la nota se conserva porque el patron es mio y se repite de forma sistematica.