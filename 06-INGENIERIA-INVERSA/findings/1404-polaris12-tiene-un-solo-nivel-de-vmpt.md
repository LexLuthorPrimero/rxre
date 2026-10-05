# 1404 — Polaris12 tiene como mucho **un** nivel de VMPT, y de los dieciséis contextos solo dos reciben ever un `CNTL`

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · CORPUS=rx550-upstream-7.2.8
TARGET=CHIP_POLARIS12 (1002:699F)

AFECTADO=gmc_v8_0.c:1121          amdgpu_vm_adjust_size(adev, 64, 9, 1, 40)
         gmc_v8_0.c:887-891        mmVM_CONTEXT0_CNTL   depth 0   (GART)
         gmc_v8_0.c:917-929        mmVM_CONTEXT1_CNTL   depth 1   (un usuario)
         gmc_v8_0.c:1156-1162      first_kfd_vmid = 8
         asic_reg/gmc/*.h          mmVM_CONTEXT{2..15}_CNTL NO EXISTEN
         asic_reg/gc/gc_9_0_offset.h  los 16 CNTL si existen (0x0880-0x088f)

CONTINUA=1403 (el código GC que los escribiria no se ejecuta en GFX8)
ESTADO=PROVEN-EN-EL-CORPUS · el "que pasa con los VMID 2-15" es
        NOT_DETERMINED y queda con discriminante de runtime
```

## 0 · LO QUE `1403` DEJÓ COMPUESTO

`1403` midió que `adev->gfxhub.funcs` no se asigna para Polaris12, y por tanto
que todo `gfxhub_v1_0.c` está muerto. Dejaba una pregunta sin responder:

> *`mmVM_CONTEXT{2..15}_CNTL` están en el bloque GC. Si el único código que los
> escribe está muerto, ¿quién configura los contextos 2 a 15?*

Este hallazgo responde **dónde están esos registros**, **cuánta profundidad de
tabla admite esta ASIC**, y **qué dos contextos reciben ever un control**. La
tercera parte queda `NOT_DETERMINED`, con el motivo medido y un discriminante.

## 1 · LA PROFUNDIDAD DE TABLA DE ESTA ASIC: UN NIVEL, Y ES UN DATO DURO

`gmc_v8_0.c:1119-1121`, con el comentario del driver:

```c
/* Max GPUVM size for cayman and SI is 40 bits.
 */
amdgpu_vm_adjust_size(adev, 64, 9, 1, 40);
```

Firma (`amdgpu_vm.c:2355-2356`):

```c
void amdgpu_vm_adjust_size(struct amdgpu_device *adev, uint32_t min_vm_size,
                           uint32_t fragment_size_default, unsigned max_level,
                           unsigned max_bits)
```

Y `amdgpu_vm.c:2404`:

```c
adev->vm_manager.num_level = min_t(unsigned int, max_level, tmp);
```

MEDIDO para Polaris12:

| magnitud | valor | de dónde |
|---|---|---|
| `min_vm_size` | 64 GB | `gmc_v8_0.c:1121` |
| `fragment_size_default` | 9 | `gmc_v8_0.c:1121` |
| **`max_level`** | **1** | `gmc_v8_0.c:1121` |
| `max_bits` | 40 | `gmc_v8_0.c:1121` |
| `num_level` | **1** | `min(1, tmp)` = 1 |

**Es la única llamada a `amdgpu_vm_adjust_size` en todo `gmc_v8_0.c`** — verificado
por grep sobre el fichero.

> **`max_level = 1` significa que esta ASIC no tiene GPUVM de más de dos niveles:
> un PDE y un PTE.** No es una opción del driver ni un ahorro: es el techo que el
> driver sepone a sí mismo para esta generación. Cualquier driver propio que
> quiera una tabla más profunda en esta placa tiene que responder antes por qué el
> upstream decidió que no.

Y hay un dato de layout que sale de aquí y que `1403` no había visto:
`gfxhub_v1_0.c:257-262` hacía

```c
num_level = adev->vm_manager.num_level;
block_size = adev->vm_manager.block_size;
if (adev->gmc.translate_further)
        num_level -= 1;
else
        block_size -= 9;
```

El `block_size -= 9` está ahí porque **`fragment_size_default = 9`**. O sea: **el
offset 9 del que habla `1126` tiene su origen medido, y es este 9.**

## 2 · `mmVM_CONTEXT{2..15}_CNTL` NO EXISTEN EN NINGUNA VENTANA GMC

Verificado sobre **todo** `include/asic_reg/`, no sobre un header:

```
  define mmVM_CONTEXT2_CNTL   ->  gc/gc_9_0_default.h   gc/gc_9_0_offset.h
                                 gc/gc_9_1_offset.h     gc/gc_9_2_1_offset.h
                                 mmhub/mmhub_1_0_default.h  mmhub/mmhub_1_0_offset.h
                                 mmhub/mmhub_9_1_offset.h    mmhub/mmhub_9_3_0_offset.h

  mismo para mmVM_CONTEXT15_CNTL, conjunto IDENTICO
```

**Ni `gmc_6_0_d.h`, ni `gmc_7_0_d.h`, ni `gmc_7_1_d.h`, ni `gmc_8_1_d.h`, ni
`gmc_8_2_d.h`.** Ninguno de los cinco headers GMC de GCN6 a GCN8.2 define un
solo `CONTEXTn_CNTL` con n ≥ 2.

El mapa completo de la ventana GMC de GC 8.1 en ese rango (`gmc_8_1_d.h`):

```
  0x0500  mmVM_L2_CNTL
  0x0501  mmVM_L2_CNTL2
  0x0502  mmVM_L2_CNTL3
  0x0503  mmVM_L2_STATUS
  0x0504  mmVM_CONTEXT0_CNTL          <-- el unico grupo "0"
  0x0505  mmVM_CONTEXT1_CNTL          <-- el unico grupo "1"
  0x0506  mmVM_DUMMY_PAGE_FAULT_CNTL
  0x0507  mmVM_DUMMY_PAGE_FAULT_ADDR
  0x050c  mmVM_CONTEXT0_CNTL2
  0x050d  mmVM_CONTEXT1_CNTL2
  0x050e  mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR
   ...
  0x0515  mmVM_CONTEXT15_PAGE_TABLE_BASE_ADDR
  0x051e  mmVM_INVALIDATE_REQUEST
  0x051f  mmVM_INVALIDATE_RESPONSE
```

**Contraste con las 16 bases de tabla, que sí están todas** (las de 0–7 en
`0x054f–0x0556`, las de 8–15 en `0x050e–0x0515`, partida, según `1403` §5).

> **La asimetría es el hallazgo:** en la ventana GMC de esta ASIC hay
> **dieciséis** registros de base de tabla y **dos** de control de contexto. En la
> ventana GC hay **dieciséis** de control. El código que usa la ventana GC está
> muerto para GFX8 (`1403`).

## 3 · LOS DOS ÚNICOS CONTEXTOS QUE RECIBEN ALGO

`gmc_v8_0_gart_enable`, los dos únicos `REG_SET_FIELD` de `CNTL` que ejecuta
GFX8 (`gmc_v8_0.c`):

```c
/* setup context0 */
WREG32(mmVM_CONTEXT0_PAGE_TABLE_START_ADDR, adev->gmc.gart_start >> 12);
WREG32(mmVM_CONTEXT0_PAGE_TABLE_END_ADDR,   adev->gmc.gart_end   >> 12);
WREG32(mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR,  table_addr           >> 12);
...
tmp = RREG32(mmVM_CONTEXT0_CNTL);
tmp = REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL, ENABLE_CONTEXT, 1);
tmp = REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL, PAGE_TABLE_DEPTH, 0);
tmp = REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL, RANGE_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
WREG32(mmVM_CONTEXT0_CNTL, tmp);
```

y para el 1:

```c
tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, PAGE_TABLE_DEPTH, 1);
```

MEDIDO:

```
  mmVM_CONTEXT0_CNTL  ENABLE_CONTEXT=1  PAGE_TABLE_DEPTH=0   GART
  mmVM_CONTEXT1_CNTL  (ENABLE_CONTEXT)   PAGE_TABLE_DEPTH=1   un contexto
  mmVM_CONTEXT{2..15}_CNTL   sin escritor alcanzable en este corpus
```

Y `first_kfd_vmid = 8` (`gmc_v8_0.c:1156-1162`, con su comentario):

```
   * VMID 0 is reserved for System
   * amdgpu graphics/compute will use VMIDs 1-7
   * amdkfd will use VMIDs 8-15
```

## 4 · MI HIPÓTESIS DE INCONSISTENCIA, Y POR QUÉ ERA FALSA

Al ver `PAGE_TABLE_DEPTH = 1` **codificado a mano** en la línea 919 mientras el
código muerto lo derivaba de `vm_manager.num_level`, mi hipótesis fue: *el 1
codificado contradice el `num_level` calculado*.

**MEDIDO y es falso.** `num_level = min(max_level, tmp) = min(1, tmp) = 1`. **El 1
codificado es exactamente el valor calculado.**

> **La lección del método, que es la sexta vez de la misma familia y la más
> barata:** un número mágico codificado a mano parece una desconexión hasta que se
> deriva el valor que la fórmula produce. Aquí los dos caminos dan 1, y el
> código muerto y el vivo **coinciden**. Derivar el número cuesta un `grep`; darlo
> por inconsistente cuesta un hallazgo entero.

Lo que sí queda, y es real, es lo otro: **los contextos 2 a 15 no reciben `CNTL`
alguno, ni con la profundidad correcta ni con ninguna.**

## 5 · LO QUE NO SE AFIRMA, Y EL DISCRIMINANTE

**`NOT_DETERMINED`**, y son tres preguntas distintas que no se pueden confundir:

1. **Si los registros `CONTEXT{2..15}_CNTL` existen en el hardware en la ventana
   GMC.** MEDIDO es que **ningun header GMC los publica**, para ninguna
   generación de GCN6 a GCN8.2. Eso es `NOT_PUBLISHED` del ASIC team, no
   `PROVEN_ABSENT` del silicio. Un hueco de publicación es la explicación más
   probable, y no la medida.

2. **Qué valor tienen tras el reset.** Si `ENABLE_CONTEXT` y `PAGE_TABLE_DEPTH`
   valen 0 tras el reset, un contexto de usuario 2–15 quedaría con depth 0
   (**GART-style, un nivel**) mientras sus tablas se construyen para depth 1. Eso
   sería una traducción mal hecha. Si el reset los deja en 1, no hay nada que
   explicar.

3. **Si la vía de usuario en GFX8 usa realmente más de un VMID.** Con
   `first_kfd_vmid = 8` el driver reserva 8 para amdgpu, pero **reservar no es
   usar**. Es `NOT_DETERMINED` cuántos se usan de hecho en esta placa.

**El discriminante que cierra las tres es uno solo, y es de runtime:**

```
  leer  mmVM_CONTEXT1_CNTL     y  mmVM_CONTEXT2_CNTL
  y si la ventana GC es distinta:  mmVM_CONTEXT{2..15}_CNTL en 0x0882..0x088f

  si CONTEXT2_CNTL != 0 y su ENABLE_CONTEXT == 1  -> el reset lo configura solo,
                                                   y no hay hueco que explicar
  si CONTEXT2_CNTL == 0                             -> hace falta el escritor que
                                                       no esta en este corpus
```

**Son cuatro registros MMIO, cuatro lecturas, sin escritura.** Y es la lectura que
`1128` ya pidió para `PAGE_TABLE_BLOCK_SIZE`, del mismo registro: **el mismo viaje
al nodo de runtime sirve para las dos preguntas.**

## 6 · LO QUE LE PASA A UN DRIVER PROPIO

Escribo la parte operativa, que es la que sobrevive al hallazgo:

```
  SIEMBRA que hay que respetar en Polaris12
     profundidad de GPUVM            max_level = 1     -> PDE + PTE, nada mas
     base de tabla de un VMID        PFN de 32 bit     -> pd_addr >> 12
     el array de bases esta partido  0-7 en 0x54f      (CONTEXTO del kernel)
                                      8-15 en 0x50e     (CONTEXTO de KFD)
     el GART usa depth 0, usuario depth 1             (y solo 1 contexto lo recibe)

  TRAMPA que hay que evitar
     copiar el mapa de la ventana GC de gfxhub_v1_0.c  -> muerto en GFX8 (1403)
     copiar la estructura de un hub de GCN9             -> ademas usa gc_9_0_offset.h
     asumir  base + vmid  para el array de bases       -> falla en VMID 8-15
     asumir 16 registros de CNTL en la ventana GMC      -> hay 2 publicados
```

> **La cuarta línea de las trampas es la que no se ve leyendo el driver**, porque
> el driver GFX8 no la pisa: simplemente no publica el mapa. Un driver propio
> que lea `include/asic_reg/gmc/gmc_8_1_d.h` concluirá que hay dos contextos,
> y **`mmVM_CONTEXT2_CNTL` no existirá en el compilador** si intenta
> nombrarlo. **El compilador es el que avisa, y es la única defensa que hay.**

## 7 · ESTADO

```
  CHIP_POLARIS12
     max_level                     1            PROVEN (gmc_v8_0.c:1121)
     num_level                     1            PROVEN (amdgpu_vm.c:2404)
     fragment_size_default         9            PROVEN
     offset 9 de block_size        origen medido en este 9   PROVEN
     PAGE_TABLE_DEPTH que escribe
        CONTEXT0 (GART)            0            PROVEN (gmc_v8_0.c:889)
        CONTEXT1 (usuario)         1            PROVEN (gmc_v8_0.c:919)
        y coincide con num_level=1               CORRIGE mi hipotesis
     ENABLE_CONTEXT escrito en     CONTEXT0 y CONTEXT1, y nadie mas   PROVEN

  mmVM_CONTEXT{2..15}_CNTL
     publicados en ventana GMC     0 de 5 headers gmc_6_0..gmc_8_2   PROVEN
     publicados en ventana GC      16, en gc_9_0_offset.h 0x0880-0x088f
     esa ventana, usada por GFX8   NO (1403)
     existen en el silicio GMC      NOT_PUBLISHED / NOT_DETERMINED
     valor tras reset               NOT_DETERMINED -> 2 lecturas MMIO

  numero de VMID de usuario realmente usados        NOT_DETERMINED -> traza

  discriminante: leer mmVM_CONTEXT{1,2}_CNTL, y si hace falta 0x0882-0x088f
  reutiliza el mismo viaje que 1128 pedia para PAGE_TABLE_BLOCK_SIZE

  refuta mi hipotesis de "constante magica incoherente": es el valor correcto
  corpus  solo lectura
  GPU     INTACTA
  sudo    NO usado
```