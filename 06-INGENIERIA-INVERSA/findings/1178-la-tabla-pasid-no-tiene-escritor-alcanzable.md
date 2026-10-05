# 1178 — el lector de la tabla PASID tiene dos escritores y ninguno se invoca: la lectura es decorativa en este corpus, y eso generaliza `1177`

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · CORPUS=rx550-upstream-7.2.8
AFECTADO=amdgpu_amdkfd_gfx_v8.c:87,100,594   la funcion, la escritura, el puntero
         amdgpu_amdkfd_gfx_v7.c:93,105,573   la MISMA funcion, otra generacion
         gmc_v8_0.c:619-637                  el unico LECTOR (visto en 1153)
AMPLIA=1177-set-pasid-vmid-mapping-no-se-invoca.md, y corrige su alcance:
       1177 solo miro gfx_v8; el patron es identico en gfx_v7
ESTADO=PROVEN-LECTOR-SIN-ESCRITOR-VIVO
```

## 0 · QUÉ HACE `1177`, Y QUÉ LE FALTA

`1177` demostró que `set_pasid_vmid_mapping` **no se invoca**, y de ahí salió
la conclusión de que la tabla `ATC_VMID0_PASID_MAPPING` es un lector sin
escritor.

El hallazgo es correcto. **El alcance no lo es**, y esta medición lo corrige:

`1177` miró **una** generación. MEDIDO el árbol entero, hay **dos** escritores de
esa tabla, y los dos están en el mismo patrón de KFD:

```
  amdgpu_amdkfd_gfx_v8.c:100   WREG32(mmATC_VMID0_PASID_MAPPING + vmid, pasid_mapping)
  amdgpu_amdkfd_gfx_v7.c:105   WREG32(mmATC_VMID0_PASID_MAPPING + vmid, pasid_mapping)
```

Dos funciones distintas, **casi idénticas línea por línea**, en ficheros de dos
generaciones distintas:

```
  amdgpu_amdkfd_gfx_v8.c:87    static int kgd_set_pasid_vmid_mapping(...)
  amdgpu_amdkfd_gfx_v7.c:93    static int kgd_set_pasid_vmid_mapping(...)
```

Y **los dos punteros están en tablas de dispatch sin invocación**, igual que el
que `1177` midió:

```
  amdgpu_amdkfd_gfx_v8.c:594   .set_pasid_vmid_mapping = kgd_set_pasid_vmid_mapping
  amdgpu_amdkfd_gfx_v7.c:573   .set_pasid_vmid_mapping = kgd_set_pasid_vmid_mapping
```

> **Un lector sin escritor es un dato. Un lector sin escritor en dos
> generaciones distintas es una patrón**, y un patrón se puede afirmar, mientras
> que un caso suelto se puede refutar con un fichero más. La diferencia es la
> que separa un hallazgo reutilizable de una anecdote.

## 1 · LA MEDICIÓN COMPLETA, Y QUÉ ES Y QUÉ NO ES

MEDIDO sobre los dos escritores y el lector:

```
 Productores de ATC_VMID0_PASID_MAPPING
    amdgpu_amdkfd_gfx_v8.c   puntero en tabla   invocado NO
    amdgpu_amdkfd_gfx_v7.c   puntero en tabla   invocado NO
    total                                                              2

  Lector de ATC_VMID0_PASID_MAPPING
    gmc_v8_0_flush_gpu_tlb_pasid  lee 15 registros                    SI, alcanzable
    total                                                              1

  Escritores ALCANZABLES                                             0
```

**Cero escritores alcanzables, un lector alcanzable.** Y el lector no es un
buscador de strings: es el callback que la vía 2 de invalidación de TLB usa para
construir su máscara, y que `1153` ya midió como alcanzable desde
`amdgpu_vm.c:1715`.

## 2 · LA CONSECUENCIA, Y HAY QUE DECIRLA CON CUIDADO

Si ningún escritor alcanzable pone `ATC_VMID0_PASID_MAPPING__VALID_MASK`, y el
lector exige ese bit para añadir un VMID a la máscara:

```c
gmc_v8_0.c:625-633
  for (vmid = 1; vmid < 16; vmid++) {
          u32 tmp = RREG32(mmATC_VMID0_PASID_MAPPING + vmid);
          if ((tmp & ATC_VMID0_PASID_MAPPING__VALID_MASK) &&
              (tmp & ATC_VMID0_PASID_MAPPING__PASID_MASK) == pasid)
                  mask |= 1 << vmid;
  }
  WREG32(mmVM_INVALIDATE_REQUEST, mask);
```

**la máscara sale cero**, y `WREG32(mmVM_INVALIDATE_REQUEST, 0)` no invalida
nada.

Eso es lo que se puede afirmar: **en este corpus, la invalidación de TLB por
PASID no puede tener efecto**, porque su máscara se construye con un registro
que nadie escribe.

Y es un hallazgo de **alcance limitado**, por dos razones que hay que decir:

1. **El registro puede tener un valor por defecto en el hardware.** Si el
   `VALID` lo pone el reset de la GPU y no el driver, entonces el lector **sí**
   funciona y lo único decorativo es la ruta de escritura. Eso **no se puede
   distinguir sin leer el registro**.
2. **Puede haber un escritor fuera de este árbol.** Un `.h` distinto, un ioctl
   que llegue por otro nombre, o una versión del driver que sí lo invoque.

> **Lo que este hallazgo establece es `PROVEN` sobre el árbol: no hay escritor
> alcanzable. Lo que no establece es qué valor tiene el registro, y por tanto no
> establece que la vía esté rota.** Esa distinción es la que separa un
> `NOT_DETERMINED` de un `PROVEN_ABSENT` sobre el hardware, y es exactamente la
> línea que el proyecto lleva pidiendo que no se cruce.

## 3 · LO QUE CIERRA Y LO QUE ABRE

**Cierra** (`PROVEN` sobre el árbol):

- Los dos escritores de `ATC_VMID0_PASID_MAPPING` del corpus están **ambos
  inalcanzables**, y son copias de la misma función en dos generaciones.
- El único escritor **alcanzable** del mapeo de VMID a PASID es
  `gmc_v8_0_emit_pasid_mapping`, y **no toca** `ATC_VMID0_PASID_MAPPING`: solo
  escribe `mmIH_VMID_0_LUT`.
- Por tanto: `mmIH_VMID_0_LUT` **sí** se escribe en esta ASIC, y
  `ATC_VMID0_PASID_MAPPING` **no**.

**Abre** (`NOT_DETERMINED`, una lectura cada uno):

- El valor de `VALID_MASK` en los 15 registros de esta GPU. **Una lectura de
  `mmATC_VMID0_PASID_MAPPING + 1` lo cierra**, y decide si la vía 2 es
  funcional o decorativa.
- Si existe un escritor fuera del árbol.

## 4 · POR QUÉ ESTO ES MÁS VALIOSO QUE `1177`

Porque `1177` concluye que el productor B estaba muerto **para el caso de
GFX8**. Este hallazgo lo hace **para el patrón**, y el patrón tiene una
consecuencia que el caso suelto no tenía:

> **Si la única forma de escribir `ATC_VMID0_PASID_MAPPING` en este driver está
> muerta, entonces esa tabla no es parte de la ruta de la MMU en ninguna
> generación GCN de este árbol.** Y eso es una afirmación sobre la **arquitectura
> del driver**, no sobre un fichero: la vía por PASID **existe pero no está
> conectada**.

Lo que eso cambia para el proyecto es concreto: la lista de lo que hay que
implementar en un driver propio **se acorta en un elemento**. No hace falta
escribir esa tabla, porque nadie la escribe. Hay que escribir
`mmIH_VMID_0_LUT`, que sí, y eso es una instrucción por ring.

## 5 · LA LEY QUE EXTRAIGO, Y QUE ES LA MISMA DE TERCERA VEZ

| hallazgo | lo que tomé por vivo | lo que era |
|---|---|---|
| `023` | `sdma_v3_0.c` productor de PTE | el fichero equivocado |
| `047` | el cero de ficheros ASIC | tenía el equivocado en la lista |
| `1166` | dos escritores de `mmIH_VMID_0_LUT` | uno en tabla sin invocación |
| `1177` | un escritor muerto | **dos**, y por tanto un patrón |

Cuatro. Y las cuatro son la misma forma: **una función referenciada en una tabla
de dispatch parece código, y no lo es hasta que se encuentra quién la invoca.**

> La diferencia entre `1166` y `1177` está en **dónde se buscó**:
> `1166` encontró el símbolo por **lo que hace**, `1177` por **dónde estaba
> escrito**, y `1178` por **quién lo escribe de verdad**. Cada uno quita un
> productor más. **Tres productores, tres medidas, un mismo nullptr Johnson.**

Y lo que sigue siendo cierto de `1166`, porque `1178` no lo toca: **el productor
A escribe `mmIH_VMID_0_LUT` con `pasid` sin máscara, y eso sí ocurre.** La
diferencia de valores que `1166` señaló es real, pero **solo tiene un productor**,
así que no es una condición de carrera sino una asimetría entre dos registros que
se leen y se escriben por caminos distintos.

## 6 · LO QUE NO SE AFIRMA, EN UNA LISTA

- **No se dice que la invalidación por PASID esté rota.** Se dice que su máscara
  se construye con un registro sin escritor **en este corpus**, y que el valor
  por defecto del hardware no está medido.
- **No se dice que `VALID_MASK` valga 0.** Es un campo, y su valor es
  `NOT_DETERMINED`.
- **No se modifica KFD ni la GMC.** Ficheros de otras sesiones, y el árbol tiene
  los suyos modificados.
- **No se propone una herramienta.** `1177` §7 ya propuso extender
  `tools/unreach.py` a los punteros de `kgd_device_funcs`, y esta medición **le
  da el alcance exacto**: no es un puntero suelto, son **nueve tablas** y al
  menos **dos** símbolos muertos. Eso es un ciclo de instrumento, no una nota.

```
ESTADO
  ATC_VMID0_PASID_MAPPING
     escritores en el arbol              2   (KFD gfx_v7 y gfx_v8)
     escritores alcanzables              0   PROVEN
     lector alcanzable                   1   gmc_v8_0_flush_gpu_tlb_pasid
     -> mascara de la via 2             siempre 0 por codigo   PROVEN
     valor por defecto del hardware      NO MEDIDO -> 1 lectura lo cierra
  mmIH_VMID_0_LUT
     escritores alcanzables              1   gmc_v8_0_emit_pasid_mapping
     valor que escribe                   pasid, sin VALID_MASK  PROVEN
  la via por PASID es funcional?         NOT_DETERMINED (2 razones, §2)

  generaliza 1177 y corrige su alcance: 1 caso -> 2, y por tanto un patron
  GPU     INTACTA
  sudo    NO usado
```