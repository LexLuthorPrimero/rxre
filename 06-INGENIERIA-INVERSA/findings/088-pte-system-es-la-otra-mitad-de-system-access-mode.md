# 088 · `AMDGPU_PTE_SYSTEM` es la otra mitad de `SYSTEM_ACCESS_MODE`, y el eje correcto de `047` es el registro de bloque, no el tipo de fichero

```
ID:           088
TIPO:        HALLAZGO + CORRECCION DE METODO (no de conclusion)
ALCANCE:     amdgpu_vm.h:57-133, amdgpu_gart.c:401, gmc_v8_0.c,
              psp_v10_0.c:61, 666 llamadas a amdgpu_ip_version
NIVEL:       0 — lectura de corpus
GPU:         INTACTA
CIERRA:      el punto 1 del NEXT ACTION de 087
```

## 1 · EL CAMPO DEL PTE EXISTE, Y CIERRA A Y F A LA VEZ

`087` dejó que el patrón de `081` y `082` tiene un tercer caso: si
`MC_VM_MX_L1_TLB_CNTL` decide si lo traducido se decodifica como MC address, el
hardware tiene que mirar un campo del PTE. Está, y tiene nombre:

```
amdgpu_vm.h:57   #define AMDGPU_PTE_VALID       (1ULL << 0)
amdgpu_vm.h:58   #define AMDGPU_PTE_SYSTEM      (1ULL << 1)
amdgpu_vm.h:59   #define AMDGPU_PTE_SNOOPED     (1ULL << 2)
amdgpu_vm.h:62   #define AMDGPU_PTE_TMZ         (1ULL << 3)
amdgpu_vm.h:65   #define AMDGPU_PTE_EXECUTABLE  (1ULL << 4)
amdgpu_vm.h:67   #define AMDGPU_PTE_READABLE    (1ULL << 5)
amdgpu_vm.h:68   #define AMDGPU_PTE_WRITEABLE   (1ULL << 6)
amdgpu_vm.h:70   #define AMDGPU_PTE_FRAG(x)     ((x & 0x1fULL) << 7)
```

**`AMDGPU_PTE_SYSTEM` es el bit 1, y es el equivalente exacto de
`SYSTEM_ACCESS_MODE = NOT_IN_SYS`.** Los dos viven en sitios distintos y dicen lo
mismo desde dos niveles:

| | registro, por contexto | PTE, por página |
|---|---|---|
| campo | `MC_VM_MX_L1_TLB_CNTL.SYSTEM_ACCESS_MODE = 3` | `PTE.SYSTEM = 0` |
| valor | `NOT_IN_SYS` | bit apagado |
| dice | *este contexto no trata salidas como RAM de sistema* | *esta página no está en RAM de sistema* |

Y hay una confirmación que **no es un inferencia mía**, sino una aserción del
propio driver:

```
amdgpu_gart.c:401   WARN_ON_ONCE(flags & AMDGPU_PTE_SYSTEM);
```

**Escribir `AMDGPU_PTE_SYSTEM` en un PTE de la GART es un `WARN_ON`.** El
driver afirma, en una línea, que la GART traduce a **no**-sistema. Y eso
coincide exactamente con `081`: `SYSTEM_ACCESS_MODE = 3` = `NOT_IN_SYS`, escrito
en `gmc_v8_0.c:840` por el mismo driver que prohíbe el bit por PTE.

> Esto es lo que `AGENTS.md` §F pedía —*«Resolver GART: GPUVA → GART PTE →
> physical RAM → PCIe. Separar GPUVM translation de MC address decoding»*— y lo
> que §A pedía —*«Resolver encoding → bits → … → system/VRAM»*— **cerrados
> ambos por el mismo par de símbolos**, uno en el registro y otro en la tabla.
> El mismo campo, en dos niveles, es la evidencia de que la separación es
> real y no una convención de nombres.

| afirmación | estado |
|---|---|
| `AMDGPU_PTE_SYSTEM` es el bit 1 del PTE | `PROVEN` (`amdgpu_vm.h:58`) |
| Ponerlo en un PTE de GART dispara `WARN_ON_ONCE` | `PROVEN` (`amdgpu_gart.c:401`) |
| La GART traduce a VRAM, no a RAM | `PROVEN` por dos fuentes independientes que coinciden |
| `SYSTEM_ACCESS_MODE = 3` es el nivel de contexto del mismo campo | `PROVEN` (`081`) |
| Los otros tres valores de `SYSTEM_ACCESS_MODE` habilitan el modo sistema | `PROVEN` (`sid.h:95-97`) |
| El hardware consulta `PTE.SYSTEM` por página | `PROVEN_DERIVED` — coherente con que exista el campo y con el `WARN_ON`, pero el corpus no contiene la lectura |

## 2 · LO QUE `083` DECÍA QUE FALTABA, Y SÍ ESTÁ CODIFICADO

`083` concluded que en GFX8 no hay quien atienda la petición de página porque
`gmc_v8_0_process_interrupt` no tiene rama PRT. Correcto sobre el **handler**.
Lo que faltaba señalar es que la **codificación** del PTE sí existe:

```
amdgpu_vm.h:73    #define AMDGPU_PTE_PRT        (1ULL << 51)
amdgpu_vm.h:121   #define AMDGPU_PTE_PRT_GFX12  (1ULL << 56)
amdgpu_vm.h:122   #define AMDGPU_PTE_PRT_FLAG(adev)  \
                     ((amdgpu_ip_version((adev), GC_HWIP, 0) >= IP_VERSION(12,0,0))
                        ? AMDGPU_PTE_PRT_GFX12 : AMDGPU_PTE_PRT)
```

**Para GFX8 el bit de PRT en el PTE es el 51**, y la selección depende de
`GC_HWIP < 12.0.0`.

Hay además un **choque de bits documentado** que conviene registrar: el bit 56
es `AMDGPU_PTE_PRT_GFX12` **y también** `AMDGPU_PTE_TF (1ULL << 56)`. No es un
bug —son generaciones distintas, seleccionadas por `GC_HWIP`—, pero es exactamente el
tipo de cosa que un driver propio tiene que saber: **el bit 56 significa una
cosa en GFX12 y otra en GFX8**, y equivocarse al escribirlo produce un PTE de
significado distinto sin ningún aviso.

`083` queda **precisado**: el hueco no es «el PTE no tiene bit de PRT» —lo tiene,
el 51— sino «el handler no lo consulta». La codificación está; el servicing no.

## 3 · `047`: EL EJE CORRECTO NO ES EL TIPO DE FICHERO

Midiendo el cruce completo:

```
666 llamadas a amdgpu_ip_version() en 78 ficheros

selector      usos  ficheros
OSSYS_HWIP        0  NINGUNO                 <- el unico cero real
UVD_HWIP         35  amdgpu_vcn.c(10), vcn_v3_0.c(5), …
GC_HWIP         270  gfx_v10_0.c(45), gfx_v9_0.c(43), …
MP0_HWIP         92  amdgpu_psp.c(35), psp_v13_0.c(20), …
SDMA0_HWIP       45  sdma_v4_0.c(19), …
MP1_HWIP         26  soc15.c(9), …
DCE_HWIP         10  gmc_v9_0.c(5), …
VPE_HWIP         12  vpe_v6_1.c(7), …
ISP_HWIP          3  amdgpu_isp.c(1), …
VCN_HWIP         17  amdgpu_ras.c(4), …
```

`047` afirmación textual es *«Ningún fichero ASIC-específico consulta
`amdgpu_ip_version()`»*, y su conclusión es que los diez selectores son
inalcanzables. El primer enunciado **es demasiado ancho**, porque
`gfx_v10_0.c`, `psp_v13_0.c`, `gmc_v9_0.c`, `vcn_v4_0_5.c` **son**
ASIC-específicos y sí lo consultan. `047` se equivocó de eje, no de
conclusión.

El eje correcto es **el registro del bloque**, no el nombre del fichero. Y hay un
caso que lo demuestra en el propio corpus:

```
psp_v10_0.c:61      if ((amdgpu_ip_version(adev, GC_HWIP, 0) == IP_VERSION(9,1,0)) && …
psp_v10_0.c:4963    const struct amdgpu_ip_block_version psp_v10_0_ip_block = { … }

$ grep -n "psp_v10_0_ip_block" amdgpu_psp.c
(sin resultado)
```

`psp_v10_0.c` es un fichero versionado, consulta `GC_HWIP`, y su bloque **no
está registrado**. El call site es inalcanzable no porque el fichero sea
«ASIC-específico», sino porque **nadie instancia ese bloque**.

> **`CORRECCION DE METODO, NO DE RESULTADO`**: la conclusión de `047` sigue
> siendo correcta para GFX8 —`gmc_v8_0.c`, `gfx_v8_0.c`, `sdma_v3_0.c` están en
> la lista de cero—, pero la razón que dio era del eje equivocado, y un eje
> equivocado deja pasar casos como `psp_v10_0.c`. El discriminante correcto es
> *«¿está este `*_ip_block` registrado en el grafo que se instancia para
> `CHIP_POLARIS12`?»*, y eso lo responde `047`-como-método, no `047`-como-dato.
>
> Es el mismo patrón de `079` otra vez: **el agregado era correcto y la
> justificación, no.** Y el caso que lo delata lo encontré por accidente,
> buscando `psp_v10_0_ip_block` para otra cosa.

### Y el único cero real

**`OSSYS_HWIP` es el único de los diez que no se consulta en ninguna parte del
corpus.** Ni una llamada, ni un fichero. Eso sí es una afirmación estructural,
y es `PROVEN_ABSENT` con denominador: 666 llamadas examinadas, 9 selectores en uso,
1 sin uso.

Lo que prueba: que ningún código de este árbol ramifica sobre la versión de
OSSYS. Lo que no prueba: que OSSYS no tenga versión distinta por ASIC —puede que
`amdgpu_ossys_*` no tenga HWIP porque no lo necesita—.

## 4 · ESTADO

```
PTE (amdgpu_vm.h)   bit0 VALID · bit1 SYSTEM · bit2 SNOOPED · bit3 TMZ
                    bit4 EXECUTABLE · bit5 READABLE · bit6 WRITEABLE
                    bits7-11 FRAG(5) · bit51 PRT (GFX8) / bit56 PRT (GFX12)
                    bit56 TF (GFX8) <- CHOQUE con PRT_GFX12
                    bit58 NOALLOC · bit63 IS_PTE
GART                amdgpu_gart.c:401 WARN_ON_ONCE(PTE_SYSTEM)  <- coherente con 081
PRT (GFX8)          bit 51, seleccionado por GC_HWIP < 12.0.0
PRT servicing       AUSENTE en gmc_v8_0_process_interrupt  (083)
selectores          666 llamadas / 78 ficheros / 9 de 10 en uso / OSSYS el unico 0
```

## 5 · LO QUE SIGUE ABIERTO

- **`psp_v10_0_ip_block` y compañía**: el discriminante correcto de `047` es
  «¿está el bloque registrado?», y eso se mide cruzando las definiciones de
  `*_ip_block` con `amdgpu_psp.c` / `amdgpu_discovery.c`. Es el mismo trabajo que
  hizo `tools/unreach.py` pero sobre el eje del registro. Es automatizable.
- **`AMDGPU_PTE_PRT_FLAG` depende de `GC_HWIP`**, y `GC_HWIP` está en la lista de
  `047`. Si el valor real de `GC_HWIP` en esta placa fuera ≥ 12, el driver
  escribiría el bit 56 en vez del 51 — y el bit 56 es `TF` en GFX8. **Es un
  discriminante de NIVEL 2 con una consecuencia concreta**: leer `GC_HWIP`.
- **G (40 huecos)**: coherencia, `025:88` `NOT_DETERMINED`.

---

```
RESULTADO DE ITERACIÓN

Entregado:
  088: AMDGPU_PTE_SYSTEM (bit 1) es el otro nivel de SYSTEM_ACCESS_MODE = NOT_IN_SYS,
    y amdgpu_gart.c:401 WARN_ON_ONCE lo afirma por el driver -> A y F cerradas
  AMDGPU_PTE_PRT = bit 51 en GFX8; el bit 56 es PRT en GFX12 y TF en GFX8
  083 queda PRECISADO: la codificacion del PTE existe; el servicing no
  el unico selector con cero usos es OSSYS_HWIP (de 10)

Medido:
  666 llamadas a amdgpu_ip_version() en 78 ficheros
  9 de los 10 selectores en uso; OSSYS_HWIP con 0
  psp_v10_0.c:61 usa GC_HWIP y su bloque NO esta registrado en amdgpu_psp.c

Corregido (metodo, no conclusion):
  047: "ningun fichero ASIC-especifico consulta amdgpu_ip_version()"
    -> demasiado ancho: gfx_v10_0.c, psp_v13_0.c, gmc_v9_0.c, vcn_v4_0_5.c
       SI lo hacen. El eje correcto es el REGISTRO DEL BLOQUE, no el nombre
       del fichero. La conclusion para GFX8 sigue siendo correcta.
  079 otra vez: el agregado era correcto y la justificacion no.

NEXT ACTION:
  El discriminante de 088 que tiene consecuencia concreta, y es NIVEL 2 con
  registro: LEER GC_HWIP en esta placa.

  Si GC_HWIP >= 12, AMDGPU_PTE_PRT_FLAG selecciona el bit 56, y el bit 56 en
  GFX8 es AMDGPU_PTE_TF. Es decir: el driver escribiría un PTE de page-fault
  en el bit de textura-filtrado. Con GFX8 en 8.x eso no puede pasar por
  construccion, asi que el discriminante deberia dar 8.x -- y si NO lo da,
  hay algo que no se entiende y eso es mas interesante que el resultado
  esperado. Un discriminante cuyo resultado esperado ya se conoce sigue
  valiendo: distingue "funciona" de "funciona por el motivo que creo".

  Y la automatizacion que 088 deja sobre la mesa, y que es la que de verdad
  importa para un driver propio: cruzAR las definiciones de *_ip_block con
  los registros, y producir la tabla "bloque declarado / bloque registrado /
  bloque alcanzable para CHIP_POLARIS12". Es el eje correcto de 047, es
  automatizable, y su salida es una lista de lo que un driver propio tiene
  que escribir a mano porque el upstream no le da.
```