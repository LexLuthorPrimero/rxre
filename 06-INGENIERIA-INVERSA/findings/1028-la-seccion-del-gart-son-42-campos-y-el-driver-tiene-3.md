# 1028 · La secuencia que programa el GART son 42 pares (registro, campo) y 39 nombres distintos, y los 55 del driver propio los cubren todos

> **H1 CORREGIDO EL 2026-10-04.** El titulo anterior decia «La secuencia que programa el GART en esta tarjeta son 42 campos, y el driver propio tiene máscara para 3». Ese
> enunciado ya no describe el estado del arbol. El veredicto vigente esta en este
> mismo fichero:
> - `:245` — 42 pares frente a 39 nombres: «42 pares (registro, campo) y 39 nombres distintos»
> - `:284` — el 3 solo en mmVM_CONTEXT0_CNTL: «el unico donde el 3_old era cierto»
> - `:289` — los 55 de la tabla los cubren: «Los 42 pares de la referencia estan TODOS en la tabla»
>
> Este parche toca **solo el H1** y esta marca. El cuerpo no se reescribe: la
> correccion del titulo tiene que quedar rastreable, o el titulo parece haber
> sido asi siempre.

`CLASSIFICATION=MEASUREMENT` · `TRACK=STATIC + HOST_OBSERVATION`
`CORPUS=RESEARCH/kernelbuild/linux-7.1.3` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`RUNTIME=OBSERVED_READ_ONLY` · `GPU INTACTA`

---

## La pregunta

Entre «el driver mapea BAR5» y «el driver tiene tablas de páginas» hay una
función concreta que hay que reproducir. En el driver de referencia para esta
ASIC es `gmc_v8_0_gart_enable()`, `gmc_v8_0.c:829-947`. ¿Qué escribe, en qué
orden, y qué de eso puede expresar hoy el driver propio?

## Qué escribe

**34 escrituras a registro**, no 21.

> **CORREGIDO dos veces el 2026-10-03.** Este hallazgo se ha escrito mal en
> tres ocasiones seguidas y las tres por el mismo motivo: **contar líneas donde
> había que contar hechos**. Queda la traza, porque un hallazgo que se corrige
> sin dejar por qué se equivocaba se vuelve a equivocar igual.
>
> **Primera corrección — de 21 a 34.** Decía «21 escrituras». Eran 21 **líneas**
> con `WREG32`. De esas, dos son los dos brazos del bucle de contextos.
>
> ```
>   21 líneas con WREG32
>     -  2  los dos BRAZOS del bucle  (L912 y L915)
>   = 19 escrituras explícitas
>     + 15  iteraciones del bucle  (i = 1..15, AMDGPU_NUM_VMID = 16)
>   = 34 escrituras reales
> ```
>
> La primera versión de esta corrección(restó **1** bucle en vez de 2 y escribió
> «20 explícitas + 15 = 34». 20 + 15 son 35. Dos correcciones seguidas que no
> cuadran: eso es lo que pasa cuando se corrige a mano en vez de medir.
>
> **Segunda corrección — `REG_SET_FIELD` y la unidad de cuenta.**
>
> ```
>   REG_SET_FIELD                       42
>   pares (registro, campo) distintos   42
>   NOMBRES de campo distintos          39
> ```
>
> Decía «41». Y sobre todo: **«42 campos» es cierto como pares y falso como
> nombres**, porque `ENABLE_CONTEXT`, `PAGE_TABLE_DEPTH` y
> `RANGE_PROTECTION_FAULT_ENABLE_DEFAULT` se escriben en los dos contextos. Este
> documento usó las dos unidades en el mismo texto sin decirlo, y por eso su
> «los otros 39 no tienen equivalente» parecía cuadrar con un 42 que no era del
> mismo género.
>
> **Tercera corrección — la que no era un número sino un hecho.** Decía:
> «las 34 son `RREG32 → REG_SET_FIELD → WREG32`, no hay ni una sola escritura
> ciega en toda la función». **Falso.** Medido:
>
> ```
>   RMW (RREG32 -> REG_SET_FIELD -> WREG32)      7
>       L849 mmMC_VM_MX_L1_TLB_CNTL    L859 mmVM_L2_CNTL     L863 mmVM_L2_CNTL2
>       L870 mmVM_L2_CNTL3            L885 mmVM_L2_CNTL4    L897 mmVM_CONTEXT0_CNTL
>       L935 mmVM_CONTEXT1_CNTL
>
>   escritura DIRECTA, sin lectura previa       27 ejecuciones
>       L892 mmVM_CONTEXT0_CNTL2 = 0
>       L887 L888 L889 L890  START, END, BASE y PFN de la pagina dummy
>       L899 L900 L901  los tres de la identity aperture
>       L908 L909  START=0, END=max_pfn-1
>       L912 L915  el bucle, x15
>       L920 L922  PFN del contexto 1, CNTL2 = 4
> ```
>
> **Dos de cada tres escrituras son ciegas.** Y el documento razonaba
> correctamente, sobre por qué una escritura directa a `mmVM_CONTEXT0_CNTL`
> pondría a cero 19 campos, mientras afirmaba en la misma página que ese patrón
> no ocurría en la función que estaba transcribiendo.
>
> Lo que de verdad da valor a la tabla de campos es lo otro, y sigue siendo
> cierto: **los siete registros de control se modifican por RMW
> precisamente porque tienen campos que no se tocan.** Las 27 escrituras ciegas
> caen todas en registros cuyo valor es un único número, y por eso no pierden
> nada.

Contadas por registro, con el bucle expandido como 15:
>
> ```
>   mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR          2   (contexto 0, y el brazo i<8)
>   mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR          1   (el brazo i>=8 del bucle)
>   mmMC_VM_MX_L1_TLB_CNTL                      1
>   mmVM_L2_CNTL                                1
>   mmVM_L2_CNTL2                               1
>   mmVM_L2_CNTL3                               1
>   mmVM_L2_CNTL4                               1
>   mmVM_CONTEXT0_PAGE_TABLE_START_ADDR         1
>   mmVM_CONTEXT0_PAGE_TABLE_END_ADDR           1
>   mmVM_CONTEXT0_PROTECTION_FAULT_DEFAULT_ADDR 1
>   mmVM_CONTEXT0_CNTL2                         1
>   mmVM_CONTEXT0_CNTL                          1
>   mmVM_L2_CONTEXT1_IDENTITY_APERTURE_LOW_ADDR  1
>   mmVM_L2_CONTEXT1_IDENTITY_APERTURE_HIGH_ADDR 1
>   mmVM_L2_CONTEXT_IDENTITY_PHYSICAL_OFFSET     1
>   mmVM_CONTEXT1_PAGE_TABLE_START_ADDR         1
>   mmVM_CONTEXT1_PAGE_TABLE_END_ADDR           1
>   mmVM_CONTEXT1_PROTECTION_FAULT_DEFAULT_ADDR 1
>   mmVM_CONTEXT1_CNTL2                         1
>   mmVM_CONTEXT1_CNTL                          1
>   mas 13 del bucle, que caen en los dos BASE_ADDR de arriba
> ```
>
> El error es de la misma familia que los otros dos de este documento:  tomar
> un recuento de líneas por un recuento de hechos.  El dato de 34 es el que
> sirve; el de 21 era una línea de código, no una escritura al hardware.

De esas 34, **7 son de lectura-modificación-escritura** —los siete registros
que la referencia abre con `RREG32`— y las otras 27 son escrituras completas de
un literal o de un PFN. Las 42 operaciones de `REG_SET_FIELD` caen dentro de
esas siete.

| registro | campos declarados | los pone la referencia | una escritura ciega pondría a cero |
|---|---|---|---|
| `mmMC_VM_MX_L1_TLB_CNTL` | — | 5 | — |
| `mmVM_L2_CNTL` | 15 | 7 | 8 |
| `mmVM_L2_CNTL2` | — | 2 | — |
| `mmVM_L2_CNTL3` | — | 3 | — |
| `mmVM_L2_CNTL4` | — | 12 | — |
| `mmVM_CONTEXT0_CNTL` | **22** | **3** | **19** |
| `mmVM_CONTEXT1_CNTL` | **22** | **10** | **12** |

> **CORREGIDO el 2026-10-03 por revisión adversarial. Lo que estaba aquí era
> FALSO y no por un número.** Decía «las 34 son
> `RREG32 → REG_SET_FIELD → WREG32`» y «no hay ni una sola escritura ciega en
> toda la función». Medido:
>
> ```
>   RMW (RREG32 -> REG_SET_FIELD -> WREG32)      7
>       L849 mmMC_VM_MX_L1_TLB_CNTL    L859 mmVM_L2_CNTL     L863 mmVM_L2_CNTL2
>       L870 mmVM_L2_CNTL3            L885 mmVM_L2_CNTL4    L897 mmVM_CONTEXT0_CNTL
>       L935 mmVM_CONTEXT1_CNTL
>
>   escritura DIRECTA, sin lectura previa       27 ejecuciones
>       L892 mmVM_CONTEXT0_CNTL2 = 0
>       L887 L888 L889 L890  START, END, BASE, PFN de la pagina dummy
>       L899 L900 L901  los tres de la identity aperture
>       L908 L909  START=0, END=max_pfn-1
>       L912 L915  el bucle, x15
>       L920 L922  PFN del contexto 1, CNTL2 = 4
> ```
>
> **La mitad de la secuencia, más un tercio, son escrituras ciegas.** Y el
> documento razonaba correctamente, tres párrafos más abajo, sobre por qué una
> escritura directa a `mmVM_CONTEXT0_CNTL` pondría a cero 19 campos — y a la vez
> afirmaba que ese patrón no ocurría en la función que estaba transcribiendo.
>
> Lo que sí es cierto, y es lo que da valor a la tabla de campos: los **siete**
> registros de control se modifican por RMW precisamente porque tienen campos
> que no se tocan. Las 27 escrituras ciegas caen todas en registros que son un
> valor único, y por eso no pierden nada.

## Lo que el driver propio puede y no puede hacer

`rx550_mmio_access.h` expone:

```c
int rx550_mmio_read32 (const struct rx550_mmio_map *, struct rx550_reg, uint32_t *);
int rx550_mmio_write32(const struct rx550_mmio_map *, struct rx550_reg, uint32_t);
```

**No hay primitiva de lectura-modificación-escritura por campo.** Y
`rx550_mmio_access.h:306` ya lo dice: *"corpus programa con RREG32 →
REG_SET_FIELD → WREG32, que conserva lo demás"*. La regla está escrita; la
primitiva no existe.

La consecuencia no es teórica. `mmVM_CONTEXT0_CNTL` tiene 22 campos y la
referencia pone 3: una escritura directa pondría a cero los otros 19, y el
resultado —un contexto 0 con la caché L2, los faults y el TLB en valores
distintos de los previstos— **no falla al escribir**. Falla cuando una página
se mapea mal, mucho después, y sin señal.

## Los 42 campos, y el `__SHIFT` es derivable del `MASK`

Medido sobre `gmc_v8_0_gart_enable()` y sobre los `*_sh_mask.h` de
`include/asic_reg/`:

```
pares (registro, campo) que escribe la secuencia : 42
nombres de campo DISTINTOS                       : 39
  con MASK y __SHIFT, ambos presentes             : 42
  faltantes                                        : ninguno
  MASK y __SHIFT incoherentes                      : ninguno
```

> **CORRECCION 2026-10-04.** Esta tabla decía `campos distintos que escribe la
> secuencia : 42` y el 42 son PARES, no nombres distintos. La diferencia son
> `ENABLE_CONTEXT`, `PAGE_TABLE_DEPTH` y `RANGE_..._DEFAULT`, que salen en los
> dos contextos. El propio fichero ya lo decía mas arriba (`«42 campos» es
> cierto como pares y falso como nombres`), luego la corrección se aplicó al
> texto de las citas y no al de este resumen. **Un resumen que contradice al
> cuerpo del mismo documento es peor que no tener resumen.**

Y lo que ese 42 NO es, medido el 2026-10-04 sobre `gmc_8_1_sh_mask.h` como
fuente unica de mascaras:

- Los 20 mnemonicos no-bucle de la secuencia **declaran 132 campos**, no 84.
  El 84 **no es reproducible** bajo ningun universo que se haya podido
  construir: `NOT_REPRODUCIBLE`.
- De los 97 campos que la cabecera declara para los **siete** registros de RMW,
  la referencia escribe **42** por `REG_SET_FIELD`. Los 42 estan todos en la
  tabla propia del driver.
- Los **55** de la tabla propia no son "55 de los que la referencia escribe":
  son **42 escritos + 13 que la referencia no toca** (los doce
  `PROTECTION_FAULT_ENABLE_{INTERRUPT,SAVE}` de `mmVM_CONTEXT1_CNTL` mas
  `MC_VM_MX_L1_TLB_CNTL.ECO_BITS`), que van sin valor y el compositor salta.
- El criterio vigente es de **conjunto**, no de recuento de cabecera: en cada
  registro que la secuencia escribe por RMW se ponen los mismos campos que la
  referencia. Un campo que no se escribe no se puede escribir mal, asi que
 Carry 132, 97 o 84 a la tabla no cambia un bit que llegue al hardware.

Los **8 pares (registro, campo)** de más de un bit — que son **7 nombres**, porque
`PAGE_TABLE_DEPTH` sale en los dos contextos:

| campo | mask | shift | ancho |
|---|---|---|---|
| `SYSTEM_ACCESS_MODE` | 0x18 | 3 | 2 |
| `PAGE_TABLE_DEPTH` (contexto 0) | 0x6 | 1 | 2 |
| `PAGE_TABLE_DEPTH` (contexto 1) | 0x6 | 1 | 2 |
| `PAGE_TABLE_BLOCK_SIZE` | 0xf000000 | 24 | 4 |
| `BANK_SELECT` | 0x3f | 0 | 6 |
| `L2_CACHE_BIGK_FRAGMENT_SIZE` | 0xf8000 | 15 | 5 |
| `CONTEXT1_IDENTITY_ACCESS_MODE` | 0x180000 | 19 | 2 |
| `EFFECTIVE_L2_QUEUE_SIZE` | 0x38000 | 15 | 3 |

Y lo mismo con los 42: **42 pares (registro, campo) y 39 nombres distintos**,
porque `ENABLE_CONTEXT`, `PAGE_TABLE_DEPTH` y
`RANGE_PROTECTION_FAULT_ENABLE_DEFAULT` se escriben en los dos contextos. Cada
vez que este documento escriba una cantidad de campos hay que decir si cuenta
pares o nombres; durante una temporada usó las dos unidades en el mismo texto.

**El `__SHIFT` que declaran los headers es exactamente el número de ceros
finales del `MASK`, en los 42 casos.** Se comprobó con el invariante

```
(mask >> shift) == 2^ancho - 1
```

y no hay ni una discrepancia. Es decir: **`_SHIFT` es redundante.** Una tabla
própria que sólo lleve máscaras puede derivar la posición, y la derivación es
comprobable contra el corpus entero sin copiar 42 constantes a mano — que es
justo el error que un `REG_SET_FIELD` copiado a dedo hace el día que el header
se regenera.

## Cuánto de esto tiene el driver propio

> **ESTA SECCION ESTABA CADUCADA Y SE CORRIGE EL 2026-10-04.** Decía
> `3 de 42, y sólo dos define`, y respaldaba el 3 con `target_vm.h`, que es
> **otra tabla**, no `rx550_reg_fields[]`. Contra el árbol actual el 3 es
> cierto **solo para `mmVM_CONTEXT0_CNTL`** y falso como afirmación general.

MEDIDO sobre `rx550_reg_fields[]` (`rx550_mmio_access.c`):

```
entradas en la tabla                                    55
  pares (registro, campo) distintos                     55
  nombres de campo distintos                            52
  registros distintos                                     7

desglose por registro
  mmVM_CONTEXT1_CNTL          22
  mmVM_L2_CNTL4               12
  mmVM_L2_CNTL                 7
  mmMC_VM_MX_L1_TLB_CNTL       6
  mmVM_CONTEXT0_CNTL           3   <-- el unico donde el 3_old era cierto
  mmVM_L2_CNTL3                3
  mmVM_L2_CNTL2                2
```

**Los 42 pares de la referencia estan TODOS en la tabla**, y el bloque de
control de caché que esta seccion daba por ausente esta entero:
`mmVM_L2_CNTL` 7, `mmVM_L2_CNTL3` 3, `mmVM_L2_CNTL4` 12,
`mmMC_VM_MX_L1_TLB_CNTL` 6.

Los dos macros de `target_vm.h` que cita la version caducada siguen existiendo
y son de otra capa (`target_vm.h:80-81`), pero no son la tabla de campos.

**Y EL TITULO DE ESTE HALLAZGO TAMBIEN ESTA CADUCADO**, por la misma razon:
dice «el driver propio tiene máscara para 3», y eso solo es cierto para
`mmVM_CONTEXT0_CNTL`. Es el unico de los seis hallazgos de esta sesion cuyo
numero del H1 ya no describe el estado del arbol, y el unico que sufrio tres
correcciones el mismo dia sin que ninguna tocara el titulo.

## La asimetría que `target_vm.h` ya tenía abierta, y que esto estrecha

`target_vm.h:257-259` declara:

```c
{ "valor de PAGE_TABLE_DEPTH",        TVM_NOT_DETERMINED, ... },
{ "valor de PAGE_TABLE_BLOCK_SIZE",   TVM_NOT_DETERMINED, ... },
```

Con el corpus a la vista la pregunta no es única, son dos:

| | contexto 0 | contexto 1 |
|---|---|---|
| `PAGE_TABLE_DEPTH` | **0**, `gmc_v8_0.c:895` | **1**, `gmc_v8_0.c:925` |
| `PAGE_TABLE_BLOCK_SIZE` | **no lo escribe** | `block_size − 9`, `gmc_v8_0.c:933-934` |

`PAGE_TABLE_DEPTH` está determinado en los dos contextos, y el valor de
`PAGE_TABLE_DEPTH=0` para el contexto 0 es lo que hace que la tabla del GART sea
una sola tabla y no dos niveles.

> La tabla de arriba decía 1 en la fila del contexto 0 y la línea siguiente decía
> 0. Dos filas más abajo, el código del corpus tenía razón. Corregido.

`PAGE_TABLE_BLOCK_SIZE` sólo está determinado para el contexto 1, y su valor
sale del log de esta máquina (`block size is 10-bit`) menos 9, o sea 1.

**Para el contexto 0 el campo no lo escribe nadie.** Y no lo escribe nadie por
la razón de que la secuencia es RMW: lo que hubiera queda. El corpus no
documenta el valor de reset de `mmVM_CONTEXT0_CNTL`, y `grep` sobre
`*_sh_mask.h` no lo encuentra porque los `sh_mask` no llevan resets.

> **CORREGIDO el 2026-10-03: esto ya NO es `NOT_DETERMINED`. Y se cierra por
> dos caminos que el hallazgo no buscó.**
>
> **El valor de reset SÍ está en el corpus**, en una familia de ficheros que
> este hallazgo nunca miró: los `*_default.h`.
>
> ```
>   include/asic_reg/mmhub/mmhub_1_0_default.h:682
>       #define mmVM_CONTEXT0_CNTL_DEFAULT  0x007ffe80
> ```
>
> Decodificado con las máscaras de `gmc_8_1_sh_mask.h`, que son las de esta TU:
>
> ```
>   PAGE_TABLE_BLOCK_SIZE      mask=0x0f000000  shift=24  ->  0
>   PAGE_TABLE_DEPTH           mask=0x00000006  shift=1   ->  0
>   ENABLE_CONTEXT             mask=0x00000001  shift=0   ->  0
>   RANGE_PROTECTION_FAULT_ENABLE_DEFAULT   mask=0x10  shift=4 -> 0
> ```
>
> Y con un matiz que hay que decir: **`mmhub_1_0_default.h` es de otro ASIC.**
> MMHUB 1.0 es Vega10 / GFX9. Para GFX8 **no existe** `gmc_8_1_default.h`
> (verificado: no hay ningún `gmc/*default*` en el árbol). Así que el valor es
> evidencia de un ASIC hermano, y por tanto `CORROBORATED`, no `PROVEN`.
>
> **El segundo camino es más fuerte y no requiere hardware.** La función hermana
> escribe el registro entero a cero:
>
> ```
>   gmc_v8_0.c:972  static void gmc_v8_0_gart_disable(struct amdgpu_device *adev)
>   gmc_v8_0.c:976          /* Disable all tables */
>   gmc_v8_0.c:977          WREG32(mmVM_CONTEXT0_CNTL, 0);
>   gmc_v8_0.c:978          WREG32(mmVM_CONTEXT1_CNTL, 0);
> ```
>
> Y el ciclo real es `suspend → hw_fini → resume → sw_init`, con
> `gmc_v8_0_gart_disable()` en la ida y `gmc_v8_0_gart_enable()` en la vuelta.
> O sea: **el RMW de `L893` lee siempre un registro que el propio driver puso a
> cero hace un momento.** El valor de `PAGE_TABLE_BLOCK_SIZE` del contexto 0 no
> depende del valor de reset: depende de que la última escritura entera fuera un
> cero, y siempre lo es.
>
> Mi pregunta original tenía un cuarto camino que no consideré —los tres que
> enumeré eran «reset=0 da igual», «a profundidad 0 no se usa» y «reset=otro y
> funciona por casualidad»— y el que vale es «nadie depende del reset».
>
> **Estado nuevo: `CORROBORATED`, valor 0.** La consecuencia para el driver es
> que `PAGE_TABLE_BLOCK_SIZE` del contexto 0 puede quedar en 0 sin más análisis,
> y que el discriminante que yo proponía (leer el registro antes y después de un
> reset) era innecesario para el caso de suspend/resume: basta con leerlo
> después de un resume, y eso tampoco hace falta porque el valor ya no importa.

## El orden importa, y hay un orden obligatorio

```
  L849  mmMC_VM_MX_L1_TLB_CNTL      TLB L1,  5 campos
  L859  mmVM_L2_CNTL                caché L2,  7 campos
  L863  mmVM_L2_CNTL2               INVALIDATE_ALL_L1_TLBS, INVALIDATE_L2_CACHE
  L870  mmVM_L2_CNTL3               BANK_SELECT, BIGK_FRAGMENT_SIZE
  L885  mmVM_L2_CNTL4               12 campos de tapping, todos a cero
  L887  mmVM_CONTEXT0_PAGE_TABLE_START_ADDR   gart_start >> 12
  L888  mmVM_CONTEXT0_PAGE_TABLE_END_ADDR     gart_end   >> 12
  L889  mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR    table_addr >> 12
  L890  mmVM_CONTEXT0_PROTECTION_FAULT_DEFAULT_ADDR   dummy >> 12
  L892  mmVM_CONTEXT0_CNTL2 = 0
  L897  mmVM_CONTEXT0_CNTL           ENABLE_CONTEXT=1, DEPTH=0, RANGE_PF=1
  L899  mmVM_L2_CONTEXT1_IDENTITY_APERTURE_LOW_ADDR  = 0
  L900  mmVM_L2_CONTEXT1_IDENTITY_APERTURE_HIGH_ADDR = 0
  L901  mmVM_L2_CONTEXT_IDENTITY_PHYSICAL_OFFSET     = 0
  L908  mmVM_CONTEXT1_PAGE_TABLE_START_ADDR = 0
  L909  mmVM_CONTEXT1_PAGE_TABLE_END_ADDR   = max_pfn - 1
  L911/L914  bucle i = 1..15:  BASE_ADDR(i) = table_addr >> 12  (corte en 8)
  L920  mmVM_CONTEXT1_PROTECTION_FAULT_DEFAULT_ADDR   dummy >> 12
  L922  mmVM_CONTEXT1_CNTL2 = 4
  L935  mmVM_CONTEXT1_CNTL           10 campos, DEPTH=1, BLOCK_SIZE=block_size-9
  L940  gmc_v8_0_flush_gpu_tlb(0, 0, 0)
  L942  drm_info("PCIE GART of %uM enabled (table at 0x%016llX)")

  Y las citas de arriba estaban DESPLAZADAS UNA LINEA:  decia L843 por L849, L923
  por L922, L921 por L920.  Todas las que apuntaban al comienzo de una sentencia
  de dos lineas.  Las de los CAMPOS si eran exactas,  y la diferencia es el
  metodo:  esas las genero un script y estas las escribi a mano.
```

La invalidación va **antes** de programar la base, y hay un `flush_gpu_tlb`
**después** de los dos contextos. Un orden distinto no es «menos óptimo»: es un
contexto que puede estar activo mientras se le cambia la tabla.

## Corroboración de 1025 desde un segundo sitio

El corte en 8 del registro de tabla por VMID ya estaba corroborado por
`gmc_v8_0_emit_flush_gpu_tlb()`. Aparece **otra vez**, en `L910` de esta función,
que es un *sitio distinto* del mismo fichero y otra ruta de código:

```c
for (i = 1; i < AMDGPU_NUM_VMID; i++) {
    if (i < 8) WREG32(mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + i,     table_addr >> 12);
    else      WREG32(mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + i - 8, table_addr >> 12);
}
```

Y `mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + 1 = 0x54f + 1 = 0x550`, byte offset
`0x1540`, que es exactamente el `RX550_REG_CTX1_PT_BASE` que el driver tiene
hardcodeado. El valor sale bien por dos caminos independientes, que es lo que
`CORROBORATED` significa y lo que `OBSERVED` no significa.

## Los dos errores de sonda, que están aquí porque son el mismo patrón

**La primera versión buscó `_SHIFT` cuando la convención es `__SHIFT`** —
`amdgpu.h:1351` es `reg##__##field##__SHIFT`. Resultado: «41 campos sin
`_SHIFT`», que era falso. Peor: una de esas 41 la reportaba como *faltante* cuando
`MASK` estaba en `mmhub/mmhub_1_0_sh_mask.h` y no en `gmc_8_1_sh_mask.h`, así que
buscar en un solo header habría producido un segundo falso negativo.

**La segunda usó `(v>>s)&v != v` como invariante de coherencia.** No es el
invariante. El correcto es `(mask >> shift) == 2^ancho − 1`. Con el primero, 40
de 42 campos salían «incoherentes» y los 42 salían coherentes con el segundo.

Los dos son la misma cosa: **suponer una convención en vez de leer la
definición**. Tres veces en esta sesión, y las tres las cazó un invariante
explícito, no la atención.

## Qué NO dice este hallazgo

- **No dice que el silicio acepte la secuencia.** Es software que corre en esta
  máquina; reproducirlo en otro no está probado.
- **No dice que baste con los 39 campos que faltan.** Falta además el orden, que
  es semántica y no una tabla.
- **No dice nada del valor de reset de `mmVM_CONTEXT0_CNTL`.** Ver arriba.
- **No toca el hardware.** Cero registros escritos.

## Trazabilidad

- Secuencia: `amdgpu/gmc_v8_0.c:829-947`, `gmc_v8_0_gart_enable()`
- Macros: `amdgpu/amdgpu.h:1351-1365` (`REG_FIELD_SHIFT`, `REG_FIELD_MASK`,
  `REG_SET_FIELD`, `REG_GET_FIELD`, `WREG32_FIELD`)
- Máscaras: `include/asic_reg/*/*_sh_mask.h`, indexadas por `<REG>__<FIELD>_MASK`
  y `<REG>__<FIELD>__SHIFT`
- Geometría: finding `1027` (la aritmética de `gart_start` cierra con los
  números del log)
- Regla por VMID: finding `1025`, ahora con dos sitios
- Primitiva ausente: `rx550_mmio_access.h:657-665` expone sólo `read32`/`write32`;
  `:306` declara la regla
- Prefijo de numeración: 1028, reservado antes de escribir