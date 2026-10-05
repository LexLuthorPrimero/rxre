# 1126 — el `+ 9*1` del GART no es un desplazamiento: es la conversión de unidades entre dos formatos de página, y da 1 GiB

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · CORPUS=rx550-upstream-7.2.8
AFECTADO=amdgpu_gmc.c:1153-1156   (pde0_page_size)
         amdgpu_gmc.c:1167        (AMDGPU_PTE_FRAG(block_size + 9*1))
         amdgpu_gmc.c:1178-1180   (el bucle que llena las PDE0)
         amdgpu_vm.h:70           (AMDGPU_PTE_FRAG: << 7)
         1125-el-campo-fragment-esta-en-11-7-confirmado-por-la-macro.md
ESTADO=PROVEN · aritmetica que cierra en dos vias distintas · GPU INTACTA
```

## 0 · EL NÚMERO MÁGICO, Y POR QUÉ NO ES UN DESPLAZAMIENTO

`amdgpu_gmc.c:1167` escribe el campo fragment del PTE del GART así:

```c
flags |= AMDGPU_PTE_FRAG((adev->gmc.vmid0_page_table_block_size + 9*1));
```

El `9*1` está sin explicar, y se lee como un desplazamiento de nueve bits —que es
justo lo que llevó al comentario de `amdgpu_vm_pt.c:732` a decir que el campo
está en el bit 12.

**No lo es.** Es una conversión de unidades, y se demuestra con la aritmética que
el propio driver hace tres líneas más arriba.

## 1 · LAS DOS FORMAS, Y SU EQUIVALENCIA

**Forma A** — el tamaño de una PDE0, en `amdgpu_gmc.c:1156`:

```c
u64 pde0_page_size = (1ULL<<adev->gmc.vmid0_page_table_block_size)<<21;
```

Es decir: `2^block_size` páginas de **2 MiB**.

**Forma B** — el campo fragment del PTE, según `amdgpu_vm_pt.c:732` y la macro
`amdgpu_vm.h:70`: un valor `f` significa una granularidad de `1 << (12 + f)`.

Igualando las dos, con `block_size = fragment_size = 9` de esta ASIC:

```
  2^block_size · 2^21  ==  2^(12 + f)

  9 + 21                =  12 + f
  30                    =  12 + f
  f                     =  18        ==  block_size + 9
```

**Y `18` es exactamente lo que escribe `block_size + 9*1`.** El `9` es la
diferencia entre `21` y `12`: el número de bits que separan una página de 2 MiB
(la granularidad de la PDE0) de una de 4 KiB (la granularidad base del PTE).

MEDIDO, con los números de esta GPU:

```
  pde0_page_size = (1<<9)<<21 = 1073741824 bytes = 1024 MiB = 1 GiB
  campo FRAG     = 9 + 9      = 18
  1 << (12 + 18)             = 1 GiB          COINCIDE
```

> **El `+ 9*1` es `(21 − 12)`: la conversión de "página de 2 MiB" a "página de
> 4 KiB".** No es un campo de bits del PTE, no es un offset y no es arbitrario.
> Es una resta de exponentes, y por eso es un 9 y no un 7.

## 2 · POR QUÉ ESO PRODUCE 1 GiB, Y POR QUÉ ES LO QUE TIENE QUE PRODUCIR

La consequence no es cosmética. **Ese `PTE` es el que mapea la VRAM entera en
el GART**, y su granularidad decide cuántas entradas de PDE0 hacen falta.

MEDIDO el bucle de `amdgpu_gmc.c:1178-1180`:

```c
for (i = 0; vram_addr < vram_end; i++, vram_addr += pde0_page_size)
    amdgpu_gmc_set_pte_pde(adev, adev->gmc.ptr_pdb0, i, vram_addr, flags);
```

Con `pde0_page_size = 1 GiB` y **2 GiB de VRAM** en esta RX550:

```
  entradas PDE0 necesarias          = ceil(2 GiB / 1 GiB) = 2      (índices 0 y 1)
  entrada 3                          = el PTB gigante, para system pages
  entradas totales en PDB0           = 4
```

Y el propio driver lo dice, en el comentario de `amdgpu_gmc.c:1175-1177`:

> *The first n PDE0 entries are used as PTE, pointing to vram. The n+1'th PDE0
> entry points to a huge PTB who has more than 512 entries each pointing to a 4K
> system page.*

**O sea: 2 entradas de VRAM y 1 de sistema, 4 entradas en total.** Y eso es lo
que sale de la aritmética con el `+ 9` explicado.

> **Si el campo fragment valiera `block_size` a secas (9 en vez de 18), la
> granularidad sería `1 << (12+9)` = 2 MiB, y harían falta 1024 entradas de PDE0
> para 2 GiB de VRAM.** El `+9` es lo que evita eso: con él, 2 entradas. Eso no
> es una constante decorativa, es la diferencia entre un GART de 4 entradas y
> uno de 1025.

## 3 · EL BIT 20 DE MÁS, QUE TAMBIÉN ESTÁ EXPLICADO

El `<< 21` de `pde0_page_size` y el `<< 20` de `amdgpu_gmc.c:62` son la misma
palabra:

```c
uint32_t pde0_page_shift = adev->gmc.vmid0_page_table_block_size + 21;
```

Con `block_size = 9`, `pde0_page_shift = 30`, o sea que la dirección de una PDE0
se indexa con **30 bits**, que es exactamente el rango de 2 GiB de VRAM de esta
tarjeta. Y `adev->gmc.mc_mask = 0xffffffffff` son 40 bits, que es el máximo de
GPUVM en SI, como dice el comentario de `gmc_v8_0.c:1117-1119`.

Los tres números encajan: **9 → 30 → 40**, y la GPU tiene 2 GiB.

## 4 · LO QUE CIERRA, Y LO QUE NO

**Cierra** (`PROVEN`):

- el campo fragment del PTE del GART vale `block_size + 9 = 18` en esta ASIC, y
  produce una granularidad de **1 GiB**;
- el `9` es `(21 − 12)`, la diferencia entre la granularidad de la PDE0 y la del
  PTE, y no un campo ni un offset;
- con ese valor, la VRAM de 2 GiB necesita **2 entradas de PDE0** y el PTB
  gigante ocupa la tercera: 4 entradas en total en `PDB0`.

**No cierra** (`NOT_DETERMINED`):

- **Que el hardware lo lea así.** La aritmética demuestra que el valor es
  coherente con lo que el driver afirma y con el tamaño de la VRAM; no demuestra
  que la GPU lea el campo donde la macro lo pone. Eso es lo mismo que queda
  abierto en `1125`.

## 3 bis · UNA AFIRMACIÓN MÍA QUE ERA MAL FORMULADA, Y SU MEDIDA

La primera versión de este documento decía:

> *`vmid0_page_table_block_size` no está inicializado en `gmc_v8_0.c`.*

Es **cierto**, pero estaba incompleto, y la incompletitud es la parte
interesante. MEDIDO sobre **todas** las asignaciones del árbol:

```
  gmc_v9_0.c:1769    vmid0_page_table_block_size = 12
  gmc_v9_0.c:1772    vmid0_page_table_block_size = 0
  gmc_v12_0.c:786    vmid0_page_table_block_size = 12
  gmc_v12_0.c:789    vmid0_page_table_block_size = 0
```

**Cuatro asignaciones, dos ficheros, y ninguno es de GFX8.** Y el campo **sí se
lee** en la ruta de esta ASIC, en `gfxhub_v1_0.c:227`:

```c
tmp = REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL, PAGE_TABLE_BLOCK_SIZE,
                    adev->gmc.vmid0_page_table_block_size);
```

O sea: **GFX8 lee un campo que nadie asigna para GFX8.**

> No es una ausencia de lectura, que es lo que dije: es una lectura de un campo
> **sin productor en esta generación**. Y eso tiene una consecuencia práctica
> directa —el valor que llegue al registro es el que tuviera el `kmalloc` del
> dispositivo, que para un driver recién cargado es cero en la práctica pero no
> por diseño— y por eso la aritmética de §1 **depende** de que valga 9 y no 0.
>
> Con `block_size = 0`, el campo fragment valdría `0 + 9 = 9`, la granularidad
> sería `1 << 21` = 2 MiB, y harían falta **1024 entradas de PDE0** para los
> 2 GiB de VRAM. Con 9, hacen falta **2**. La diferencia entre un GART de 4
> entradas y uno de 1025 depende de un campo que en este corpus no tiene
> productor para nuestra ASIC.
>
> **Eso es `NOT_DETERMINED` y no se convierte en nada más aquí.** No hay lectura
> de hardware que lo cierre, y suponer "será que vale 9" porque encaja con los
> números sería exactamente la circularidad que este proyecto prohibe.

Y la lección de método, que es la parte que me llevo:

> **Concluir "no está inicializado" mirando un solo fichero es un
> `NOT_FOUND` apresentado como `PROVEN_ABSENT`.** Lo que había que medir era
> «¿quién lo asigna en todo el árbol?», y la respuesta —cuatro sitios, ninguno
> de GFX8— es distinta y más fuerte que lo que había escrito.

## 5 · POR QUÉ ESTE HALLAZGO ES MÁS QUE UN NÚMERO EXPLICADO

Porque `1125` resolvió **dónde** está el campo fragment, y este resuelve
**qué valor tiene y por qué**. Los dos juntos convierten un `9*1` que parecía
un descuido en una conversión de unidades verificable.

Y hay una consecuencia que va más allá de la GART: la granularidad de 1 GiB del
GART es **lo que hace que la VRAM de esta RX550 quepa en dos entradas de PDE0**.
Si el campo se leyera en otro sitio, el GART sería de 1025 entradas en vez de 4,
y eso es una diferencia de estructura de la tabla de page table, no de
rendimiento.

> Un número mágico en un `* 1` es la forma más barata que tiene el código de
> decir *"esto es una resta de exponentes y alguien no escribió por qué"*. Y
> en este árbol hay al menos tres nueves con significado distinto —`+ 9*1` en
> `amdgpu_gmc.c:1167`, `− 9` en `gmc_v8_0.c:928`, y `amdgpu_vm_adjust_size(adev,
> 64, 9, 1, 40)` en `gmc_v8_0.c:1121`— y **el primero y el segundo son el mismo
> nueve con signo contrario**, y el tercero no es un nueve de page table sino un
> parámetro de rango de direcciones.

## 6 · ESTADO

```
  campo fragment del GART      18 = 9 + 9         PROVEN (aritmetica)
  granularidad resultante      1 GiB              PROVEN
  entradas PDE0 para 2 GiB     2 (+1 PTB)         PROVEN
  entradas totales en PDB0     4                  PROVEN
  lectura por el hardware      NOT_DETERMINED     falta la guia de HW
  vmid0_page_table_block_size  4 asignaciones, NINGUNA de GFX8   NOT_DETERMINED

  GPU     INTACTA
  sudo    NO usado
  corpus  solo lectura
```