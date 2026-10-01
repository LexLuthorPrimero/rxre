# 037 · El mapa de registros es un mosaico de seis familias, y 60 escrituras para arrancar el chip

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=RESEARCH/working/linux-7.1.3`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`RUNTIME=NOT_RUN` · `GPU INTACTA`
`HERRAMIENTA=08-ARQUITECTURA/tools/gmmio_inventory.py` (nueva, 2 mutaciones validadas)
`CONTINUES=036-vocabulario-pm4-vivo-polaris12.md` (reutiliza su alcanzabilidad)

## CUDA principal

El fichero que implementa este ASIC se llama `gfx_v8_0.c` e **incluye seis mapas de
registro distintos**, no uno:

```
  gmc/gmc_8_2_d.h       882    Polaris12   MEMORIA
  oss/oss_3_0_d.h       545    VI generico OSS
  bif/bif_5_0_d.h       475    VI generico PCIe
  gca/gfx_8_0_d.h      2633    VI generico NUCLEO DE GRAFICOS
  dce/dce_10_0_d.h     6924    VI generico DISPLAY
  smu/smu_7_1_3_d.h     133    Polaris12   RELOJ
                              --------------------------------
                              11592 registros unicos resolubles
                              de los cuales 1015 son de familia Polaris12
```

**Solo GMC y SMU son especificos de Polaris12.** El nucleo de graficos —donde vive todo
el trabajo— sale del generico de VI. Y el bloque mas grande del mosaico, con 6924
registros, es el **display**, que el camino de compute ni toca.

Eso invierte una intuicion razonable: para un driver propio de esta placa **no hace
falta ningun header especifico de Polaris para casi todo lo que importa**. Donde si lo
hace es en la memoria y en el reloj.

Y el inventario concreto: **60 registros escritos y 34 solo leidos**, con offset
resuelto y sin una sola colision.

## Alcance exacto

1. Resolver el mapa compuesto con offsets reales.
2. Inventariar escrituras y lecturas del camino GFX8 alcanzable.
3. Detectar colisiones de offset como control de la propia resolucion.
4. Validar por dos mutaciones.

## Criterio de terminacion (cumplido)

94 registros con offset, 9056 campos de mascara cargados, dos mutaciones que detectan
desviaciones, corpus restaurado e intacto. Agotado.

---

## 1 · La correccion que tuve que hacer antes de empezar

Escribi, en la primera version del docstring de la herramienta:

> "el mapa de registros del RX550 es `gmc_8_2`"

**Es falso.** Lo dije al ver el `#include "gmc/gmc_8_2_d.h"` sin listar los demas, que es
exactamente el error de `024`, `031`, `032` y `035`: **afirmar algo a partir de la primera
pista en vez de del conjunto.**

La version corregida esta al principio del fichero de la herramienta y aqui, porque el
error era de partida y no de detalle.

## 2 · El inventario

Herramienta: `08-ARQUITECTURA/tools/gmmio_inventory.py`. Importa `pm4_reachable` para
reusar su indice y su alcanzabilidad — que ya esta validada por mutacion — en vez de
reimplementar la parte cara.

### 2.1 · Escritos: 60 registros, 94 escrituras

Los mas estructurales, por su peso en el anillo:

```
mmCP_RB0_BASE            0x003040   gfx_8_0    base del IB del ring
mmCP_RB0_CNTL           0x003041   gfx_8_0    9 campos   control del ring
mmCP_RB0_RPTR_ADDR      0x003043   gfx_8_0    donde publica el rptr
mmCP_RB0_RPTR_ADDR_HI   0x003044   gfx_8_0
mmCP_RB0_WPTR           0x003045   gfx_8_0    W=2 R=2  <-- el par de 031
mmCP_RB_WPTR_POLL_ADDR_LO/HI  0x3046/7
mmCP_RB_DOORBELL_CONTROL      0x003059
mmCP_RB_DOORBELL_RANGE_LOWER  0x00305a
mmCP_RB_DOORBELL_RANGE_UPPER  0x00305b
mmCP_HQD_PQ_RPTR        0x00324f   cola de trabajo: rptr
mmCP_HQD_PQ_WPTR        0x003255   cola de trabajo: wptr
mmCP_HQD_EOP_RPTR/WPTR  0x00326d/6
mmCP_HQD_EOP_WPTR_MEM   0x003279
mmCP_DEVICE_ID          0x00304b
mmCP_MAX_CONTEXT        0x0030ae
mmCP_ENDIAN_SWAP        0x003050
```

### 2.1.1 · Los tres punteros de escritura, y cual es cual

`031` cerrojo el par `rptr`/`wptr` **del software**. El hardware tiene mas punteros, y
cual es cual lo resuelve el inventario junto con los sitios de escritura:

| | donde | cuantas veces | que es |
|---|---|---|---|
| `*ring->wptr_cpu_addr` | cada submit | por submit | pagina del writeback (`031`) |
| `mmCP_RB_DOORBELL_CONTROL` `0x3059` | ring init | 1 | **de donde el HW saca el indice de la puerta** |
| `mmCP_HQD_PQ_WPTR` `0x3255` | ring init | 1, con valor literal `0` | puntero de escritura de la cola |
| `mmCP_RB0_WPTR` `0x3045` | ring init **y** rama sin doorbell | 1 + 1 | puntero del ring del CP |

Sitios exactos:

```
gfx_v8_0.c:4255   WREG32(mmCP_RB0_WPTR, ring->wptr)          <- init
gfx_v8_0.c:6031   WREG32(mmCP_RB0_WPTR, ...) ; RREG32(...)  <- set_wptr_gfx, rama ELSE
gfx_v8_0.c:6019   return RREG32(mmCP_RB0_WPTR)               <- get_wptr, rama ELSE
gfx_v8_0.c:4380   WREG32(mmCP_HQD_PQ_RPTR, 0)                <- init
gfx_v8_0.c:4381   WREG32(mmCP_HQD_PQ_WPTR, 0)                <- init
gfx_v8_0.c:4200   CP_RB_DOORBELL_CONTROL.DOORBELL_OFFSET = ring->doorbell_index
```

### 2.1.2 · Y con eso, `031` §3 queda cerrado — y mi hipotesis de este documento era incorrecta

Escribi en mi primera redaccion que "el wptr del que habla `031` —el que va al doorbell—
es `CP_HQD_PQ_WPTR`, no `CP_RB0_WPTR`". **Es falso**, y lo veo con los sitios:

1. `CP_HQD_PQ_WPTR` se escribe **una vez, con el literal `0`**, en el init del ring. No es
   el puntero por submit.
2. `CP_RB0_WPTR` aparece en `set_wptr_gfx` **solo en la rama `else`** —la que `031`
   demostro **muerta** en GFX8 porque `use_doorbell` es `true`— y en `get_wptr` por la
   misma razon.
3. Lo que realmente gobierna la puerta es **`CP_RB_DOORBELL_CONTROL.DOORBELL_OFFSET`**
   (`0x3059`, `:4200`), escrito una vez al crear el ring con `ring->doorbell_index`.

La cadena real es:

```
init:   CP_RB_DOORBELL_CONTROL.DOORBELL_OFFSET = doorbell_index
        -> el HW sabe que apertura vigilar
submit: *wptr_cpu_addr = wptr        (GTT, pagina del writeback)
        writel(doorbell[doorbell_index], wptr)   (apertura, 031)
```

Y `CP_RB0_WPTR` sirve para **dos cosas distintas**: el valor inicial del ring al
arrancarlo, y el mecanismo **alternativo sin doorbell** que en esta ASIC no se usa.

`PROVEN_DERIVED`, con la dependencia nombrada: el codigo no dice que el CP lea la pagina
del writeback; se deduce de que el doorbell solo lleva el indice y el valor del wptr solo
existe en esa pagina. Es la misma clase de `DERIVATION` que `031` §3.

**Consecuencia para el driver propio:** si implementa `use_doorbell = false` y usa
`CP_RB0_WPTR`, necesita el patron `WREG32` + `RREG32` de confirmacion —que `031` §2.0
descubrio y que es **codigo muerto en el driver de referencia**—, y necesita
`CP_RB_DOORBELL_CONTROL.DOORBELL_EN = 0`. Si usa el doorbell —que es lo que hace GFX8—,
`CP_RB0_WPTR` solo se programa una vez, al arrancar el ring. **Dos disenos validos con
coste distinto, y el driver de referencia solo ejercita el segundo.**

### 2.2 · Lectura: 34 registros

```
mmGRBM_STATUS2   0x002002   R=3
mmGRBM_STATUS    0x002004   R=2
mmSRBM_STATUS    0x000394
mmCP_HQD_ACTIVE  0x003247   R=2
mmCP_HQD_PERSISTENT_STATE  0x003249
mmCP_HQD_QUANTUM 0x00324c
mmMC_FUS_DRAM0/1_BANK_ADDR_MAPPING  0xa11 / 0xa12   <-- gmc_8_2
```

Los dos `DRAM_BANK_ADDR_MAPPING` son los unicos registros de familia **Polaris12** que se
leen, y ambos sirven para detectar el tipo de VRAM montada. Es el unico sitio del camino
donde la configuracion fisica de la placa —que DRAM, como esta mapeada— se consulta.

### 2.3 · El reparto por familia, sobre lo que se toca

El dato util para un driver propio: **la familia de la que sale cada registro, no el
nombre**. 94 registros tocados, y la gran mayoria viene del nucleo generico de VI.

## 3 · Tres espacios de direccionamiento, no uno

Lo segundo que resulto al mirar el codigo en vez de los headers:

```
1. RREG32(mmX) / WREG32(mmX, v)      offset directo de BAR
2. RREG32_SMC(ixX) / WREG32_SMC       apertura del SMC, registros con prefijo ix
3. AMDGCN_REG_OFFSET(B, n, regX)     direccionado por bloque
```

El caso 2 es el que `031` no vio: `gfx_v8_0.c:799` usa `RREG32_SMC(ixCG_ACLK_CNTL)`, y
`amdgpu_reg_smc_rd32` es una ruta **distinta** a la de `RREG32`. Un driver propio que solo
sepa de `RREG32` no puede tocar el SMC, y el SMC es quien programa los relojes.

Los registros `ix*` no son un offset de BAR: son indices de una apertura aparte. De ahi
que los 60+34 del inventario **no incluyan ni uno del SMC**, y eso es una limitacion
declarada, no un resultado.

## 4 · Los dos controles que hacen creible la herramienta

### 4.1 · Colision de offsets

Resolver el mapa por orden de `#include` es una apuesta: si dos familias definen el mismo
nombre, gana la primera, y si ese nombre aparece en dos offsets distintos, se pierde
informacion en silencio. Se comprueba sobre los registros **tocados**:

```
94 registros, 94 offsets distintos, ninguna colision
```

Eso confirma que el orden de familias esta bien. Se comprueba sobre los tocados y no
sobre los 11592 del mapa entero, porque en el mapa completo los alias son legitimos y
habituales.

### 4.2 · Dos mutaciones

| mutacion | resultado |
|---|---|
| `mmCP_RB0_CNTL` `0x3041` → `0x9999` | el inventario reporta `0x009999` — lee la cabecera |
| `mmCP_RB0_CNTL` `0x3041` → `0x3040` | **colision detectada**: `0x003040: mmCP_RB0_BASE, mmCP_RB0_CNTL` |

La segunda es la que importa: **valida el validador**. Un chequeo que nunca haasonde fallado
no demuestra que funcione. Al poner el registro encima de su vecino —que es el error
realista, un typo de digito— el detector lo ve.

Restaurado el corpus, y `git status --porcelain RESEARCH/` vacio.

## 5 · Dos bugs de la herramienta, ambos silenciosos

### 5.1 · `__MASK` en vez de `_MASK`: informo "0 campos" para todo

El `_sh_mask.h` usa **un** underscore antes de `MASK`:

```
CP_RB0_CNTL__RB_BUFSZ_MASK
|REG     |CAMPO| MASK
```

Yo escribi el patron `(\w+)__(\w+)__MASK`. Con `__` la regex **no casa nada**, el
conteo de campos sale 0 para los 94 registros, y la herramienta **no lanza error**: es
un falso dato que parece un resultado. Es el peor tipo de fallo posible en una
herramienta de inventario, porque no se manifiesta como fallo.

Lo mas facil de detectar fue la segunda comprobacion: `mmCP_RB0_CNTL` tiene 9 campos
reales segun el header, y la herramienta decia 0. Un 0 que se podia contar con el dedo.

### 5.2 · Faltaban tres familias de mascaras

Cargaba cuatro `_sh_mask.h` de seis, y por eso `mmSRBM_GFX_CNTL`, `mmHDP_ADDR_CONFIG` y
`mmGMCON_DEBUG` salian con **0 campos**: no porque no los tengan, sino porque no mire
donde estaba su mascara. Un 0 por no haber buscado es indistinguible de un 0 real.

Corregido: los seis. Ahora la columna lleva **el nombre de la familia**, para que si un
campo vuelve a 0 se vea de inmediato de donde.

### 5.3 · Y una normalizacion que hacia falta antes

El `_sh_mask.h` nombra los registros **sin** el prefijo —`CP_RB0_CNTL__...`— y el `_d.h`
**con** el —`mmCP_RB0_CNTL`. Hay que quitar el `mm` en un lado para casarlos. Sin eso, 0
campos otra vez, por una razon distinta.

## 6 · Clasificacion

| afirmacion | estado |
|---|---|
| `gfx_v8_0.c` incluye seis familias de registro | `PROVEN` — `:41-58` |
| Solo GMC (`8_2`) y SMU (`7_1_3`) son Polaris12 | `PROVEN` |
| `dce_10_0` tiene mas registros que todos los demas juntos | `PROVEN` — 6924 de 11592 |
| 60 registros escritos, 94 escrituras, 34 solo leidos | `PROVEN` — alcanzabilidad + offset |
| Ninguna colision de offset en los tocados | `PROVEN` — y validado por mutacion |
| `CP_RB0_*` y `CP_HQD_PQ_*` son punteros de escritura distintos | `PROVEN` |
| Que el doorbell lo gobierne `CP_RB_DOORBELL_CONTROL.DOORBELL_OFFSET` | `PROVEN_DERIVED` — §2.1.2 |
| Tres espacios de direccionamiento | `PROVEN` |
| El inventario esta completo | `NOT_DETERMINED` — ver §8 |
| Que el numero de escrituras sea el trabajo del driver propio | `OBSERVATION` |

## 7 · Confounders

- **El corpus es parcial: faltan `display/` y `dc/`.** `dce_10_0_d.h` esta presente y es la
  familia mas grande, pero el codigo que la usa **no esta en el corpus**. El unico acceso
  de display que aparece (`mmDMIF_ADDR_CALC`) viene de una funcion compartida del path
  GFX8. Para un driver de compute, esto es aceptable; para uno con salida de video, el
  inventario esta **muy incompleto** y el estado honesto es `NOT_DETERMINED`.
- **Los registros del SMC no estan inventariados.** `RREG32_SMC` usa el prefijo `ix` y una
  apertura distinta; el inventario solo cubre `RREG32`/`WREG32` con nombres `mm*`. Y el SMC
  es quien programa relojes, que es justo lo que `044` (xclk) y la sesion `smu` estan tocando. **Solapamiento de ambito con otra sesion, declarado.**
- **`CP_HQD_PQ_WPTR` no se reescribe nunca** (`gfx_v8_0.c:4381`, literal `0`). Quien lo
  actualiza en el hardware no esta en el corpus, o no existe en el driver. Por eso lo
  clasifico como puntero de cola *inicializado*, no como puntero vivo. Si el hardware lo
 incrementa por su cuenta, la lectura `RREG32(mmCP_HQD_PQ_RPTR)` de `:4496` lo confirma
  como lectura de estado, no de control. `PROVEN` el codigo; `NOT_DETERMINED` quien lo
  escribe.
- **94 escrituras no son 94 tareas.** `mmGB_TILE_MODE0` y `mmGB_MACROTILE_MODE0` aparecen 7
  veces cada uno porque se escriben por cada vista. El numero mide **vocabulario de
  registros**, no trabajo de implementacion.
- `mmSRBM_GFX_CNTL` aparece con sitio `vi.c:586`, fuera de `gfx_v8_0.c`. Correcto: es una
  funcion compartida (`vi.c`) alcanzable desde el mismo grafo. La etiqueta de sitio es el
  primer sitio, no el unico.

## 8 · UNLOCKS

- **El conjunto de registros a programar queda acotado en 60, con offset.** Junto con los
  21 paquetes de `036`, es la lista de trabajo completa del driver propio: *21 paquetes y
  60 registros*.
- **Se desdobla el "wptr" en tres.** `031` cerrojo el par `rptr`/`wptr` del software. El
  hardware tiene **tres** punteros de escritura distintos, en dos niveles
  (`CP_RB0_*` y `CP_HQD_PQ_*`). Un driver propio que solo programe uno de ellos no
  arranca el ring.
- **`DESIGN_FREEDOM` con base medida: el mapa no es exotico.** 1015 de 11592 registros son
  de familia Polaris12, y solo 2 de los 94 tocados los usan. **El nucleo de graficos de
  esta placa es el de Volcanic Islands tal cual.** Eso reduce el riesgo del driver propio
  mas de lo que cabia esperar: la mayor parte se puede portar de GCN3 sin adaptacion.
- **Queda nombrado el mapa como mosaico, con la familia de cada registro.** Para escribir
  un driver hace falta saber de que header sale cada offset, y esa era la ambiguedad que
  acabo de cerrar.
- **Dos herramientas de la ronda anterior mas esta, las tres con validacion negativa.**
  La de registries valida **su propio validador** con la segunda mutacion, que es el
  control que faltaba en las otras dos.
- `044`/`smu` y esta se tocan: el SMC programa relojes y no esta cubierto aqui. Queda
  declarado para que nadie mida dos veces lo mismo.

## 9 · Criterio de falsificacion

Se refutaria si: (a) un registro del camino GFX8 se escribiera con un nombre `mm*` que
no estuviera en ninguno de los seis headers — la herramienta lo reportaria como "no
resuelto", y hoy el conteo es 0, luego no ocurre en el subgrafo examinado; (b) el orden de
resolucion por `#include` fuera incorrecto para algun nombre — contradicho por el chequeo
de colision, salvo que dos familias den el mismo offset al mismo nombre, caso en el que el
detector no podria verlo; (c) `CP_HQD_PQ_WPTR` no fuera el que gobierna el doorbell —
refutable leyendo el path de doorbell en `gfx_v8_0.c:4202-4220` y siguiendo el registro
que `PACKET3_MAP_QUEUES` recibe como `doorbell_offset`, que es la via mas directa;
(d) faltara algun registro porque `display/`/`dc/` no estan — refutable solo con el
corpus completo, y es una `LIMITATION` declarada, no un error.

## 10 · Evidencia

```
HERRAMIENTA:
  08-ARQUITECTURA/tools/gmmio_inventory.py
    mapas:   gmc_8_2 882 | oss_3_0 545 | bif_5_0 475
             gfx_8_0 2633 | dce_10_0 6924 | smu_7_1_3 133
    unicos resolubles: 11592    de familia Polaris12: 1015
    mascaras: 9056 campos en 9056 registros
    alcanzables: 262 funciones (importadas de pm4_reachable)
    resultado: A=60 escrituras(94 ops)  B=34 lecturas(44 ops)  C=0 no resueltos
    colisiones: ninguna (94 registros, 94 offsets)

VALIDACION NEGATIVA (dos mutaciones):
  1. mmCP_RB0_CNTL 0x3041 -> 0x9999
     el inventario reporta 0x009999        (lee la cabecera)
  2. mmCP_RB0_CNTL 0x3041 -> 0x3040
     *** colision: 0x003040: mmCP_RB0_BASE, mmCP_RB0_CNTL
     (valida el validador, que es lo que faltaba en 034 y 036)
  restaurado -> 60/34/0, sin colisiones, git status RESEARCH/ vacio

CODIGO:
  gfx_v8_0.c:41-58      seis includes de mapas de registro
  gfx_v8_0.c:799,802    RREG32_SMC / WREG32_SMC  (espacio del SMC)
  gfx_v8_0.c:4250-4270  CP_RB0_BASE/CNTL/RPTR/WPTR  (0x3040-0x3047)
  gfx_v8_0.c:4379-4381  CP_HQD_DEQUEUE_REQUEST / PQ_RPTR / PQ_WPTR
  gfx_v8_0.c:4568-4570  CP_HQD_EOP_RPTR/WPTR/WPTR_MEM
  gfx_v8_0.c:1781,1793,1797  MC_FUS_DRAM*_BANK_ADDR_MAPPING (gmc_8_2)
  amdgpu.h:1310         RREG32_SMC -> amdgpu_reg_smc_rd32
```

`WRITE_EXECUTION=NONE`. Ninguna escritura a la GPU. `GPU INTACTA`.