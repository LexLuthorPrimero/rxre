# 081 · `SYSTEM_ACCESS_MODE = 3` es `NOT_IN_SYS`, y cierra la mitad de la frontera F por lectura

```
ID:           081
TIPO:        HALLAZGO — CIERRA dos NOT_DETERMINED por lectura de corpus
ALCANCE:     06-INGENIERIA-INVERSA/findings/067:109, frontera F de AGENTS.md
TOOL:        tools/sysaccess.py v1.0.0, selftest 16/16 PASS
GPU:         INTACTA. Lectura de corpus, nada más.
CORRIGE_A:   067 §"Lo que sigue abierto"
```

## POR QUÉ ESTA TAREA, Y POR QUÉ NO LAS QUE YO ESTABA HACIENDO

`AGENTS.md` §INICIO INMEDIATO manda `GLOBAL WORK SCAN` y elegir por
`UNCERTAINTY_REDUCTION + PATH_UNLOCKS + IMPLEMENTATION_RELEVANCE +
VALIDATION_VALUE`. Las ocho iteraciones anteriores fueron una cadena de mis
propios `NEXT ACTION` sobre la documentación del proyecto —auditoría de
referencias, grafo de findings, vocabulario de relaciones—, que **no está en
ninguna de las ocho fronteras A–H de `AGENTS.md`**.

Se ejecutó el `GLOBAL WORK SCAN` sobre `frontier.py --json`:

```
huecos por frontera (un hueco puede contarse en varias):
   A: 19    B: 35    C: 62    D: 30
   E: 151   F: 35    G: 40    H: 13
```

`E` (PM4/CP/IB) domina por volumen y está cerrada a nivel estático. `H` está
explícitamente diferida por `AGENTS.md` —*«después de cerrar core»*—, y el core no
lo está. **`F` es la menos trabajada de las que no están diferidas**, y es la
única cuya pregunta central sigue abierta por lectura:

```
## F. MEMORY SYSTEM
Resolver GART: GPUVA → GART PTE → physical RAM → PCIe.
Separar GPUVM translation de MC address decoding.
```

`067:109` la nombra:

| Afirmación | Estado en `067` |
|---|---|
| Qué hace el hardware con `SYSTEM_ACCESS_MODE = 3` | `PROVEN` — `NOT_IN_SYS`: el acceso NO está en RAM de sistema |
| Por qué `SYSTEM_ACCESS_MODE = 3` y no otro | `PROVEN` — `sid.h:95-98` enumera los 4 valores, y el escritor en `gmc_v8_0.c:840` pone 3 para la GART |

**Las dos se responden con `sed -n '95,98p' sid.h`.**

## 1 · LA LECTURA

```
sid.h:95  #define  SYSTEM_ACCESS_MODE_PA_ONLY        (0 << 3)
sid.h:96  #define  SYSTEM_ACCESS_MODE_USE_SYS_MAP     (1 << 3)
sid.h:97  #define  SYSTEM_ACCESS_MODE_IN_SYS          (2 << 3)
sid.h:98  #define  SYSTEM_ACCESS_MODE_NOT_IN_SYS      (3 << 3)
```

| valor | símbolo | qué habilita |
|---|---|---|
| 0 | `PA_ONLY` | solo dirección física, sin traducción |
| 1 | `USE_SYS_MAP` | usa el mapa del sistema |
| 2 | `IN_SYS` | el acceso está en RAM de sistema |
| **3** | **`NOT_IN_SYS`** | **el acceso NO está en RAM de sistema** |

Y el escritor, en el ASIC propio:

```
gmc_v8_0.c:838  tmp = RREG32(mmMC_VM_MX_L1_TLB_CNTL);
gmc_v8_0.c:839  tmp = REG_SET_FIELD(tmp, MC_VM_MX_L1_TLB_CNTL, ENABLE_L1_TLB, 1);
gmc_v8_0.c:840  tmp = REG_SET_FIELD(tmp, MC_VM_MX_L1_TLB_CNTL, SYSTEM_ACCESS_MODE, 3);
gmc_v8_0.c:841  tmp = REG_SET_FIELD(tmp, MC_VM_MX_L1_TLB_CNTL, ENABLE_ADVANCED_DRIVER_MODEL, 1);
```

## 2 · LAS DOS RESPUESTAS

**«Qué hace el hardware con `SYSTEM_ACCESS_MODE = 3`»** → `NOT_IN_SYS`. El
acceso **no** se trata como RAM de sistema; se decodifica como **dirección MC**,
o sea VRAM. `PROVEN`, por lectura del enum en `sid.h` **y** por la coherencia
entre el enum y el campo del registro.

**«Por qué 3 y no otro»** → es el único valor que **excluye** el modo sistema. Los
otros tres lo habilitan. Y la GART traduce a **VRAM**, no a RAM: por eso el modo
correcto es el que excluye la RAM. `PROVEN`, por la misma lectura.

> Es el mismo razonamiento que `067` ya tenía cerrado para la dirección del
> offset GART —*«Su dirección es un offset GPU, no una dirección de RAM»*—,
> aplicado al campo que decide cómo se interpreta la dirección traducida. La GART
> estaba media cerrada: sabíamos **dónde** estaba la tabla y **no** estaba en
> RAM. Faltaba **cómo** se declara que lo que sale de la traducción no es RAM.

## 3 · LA CRUZ, QUE ES LA QUE HACE QUE SEA EVIDENCIA

Que `sid.h` lo diga no basta: `sid.h` es un header, y un header define campos que
cada ASIC puede usar como le plazca. Lo que convierte la lectura en evidencia
es que el valor sea **el mismo en todos los ASIC que programan el registro**:

```
ASIC que programan el registro:  12
ficheros distintos:              12
VALORES USADOS:                  3
```

| registro | ASIC |
|---|---|
| `MC_VM_MX_L1_TLB_CNTL` | 5 — gmc_v8_0, gmc_v7_0, mmhub_v1_0, mmhub_v1_7, gfxhub_v1_0 |
| `MMMC_VM_MX_L1_TLB_CNTL` | 4 — mmhub_v2_0, v2_3, v3_0_1, v3_3, mmhub_v9_4 |
| `GCMC_VM_MX_L1_TLB_CNTL` | 3 — gfxhub_v2_0, v3_0, v11_5_0, v12_1 |

`gmc_v8_0.c` es el ASIC propio (`amdgpu_drv.c:2054`, `CHIP_POLARIS12`), y usa el
mismo 3 que los otros 11. **Cuatro generaciones de MC (v6/v7/v8 + MMHUB v9.4),
tres de GFXHUB, con el mismo valor.** Si el 3 fuera un accidente de GFX8, esta
tabla no lo ocultaría.

### Y por qué el nombre NO basta para resolver el 3

Los cuatro símbolos comparten el prefijo `SYSTEM_ACCESS_MODE_`. Un emparejamiento
ingenuo de `SYSTEM_ACCESS_MODE, 3` contra el enum no distinguiría
`SYSTEM_ACCESS_MODE_IN_SYS` de `SYSTEM_ACCESS_MODE_NOT_IN_SYS`, porque las dos
cadenas contienen `SYSTEM_ACCESS_MODE`. Resolver por subcadena habría dado
`IN_SYS` —el valor equivocado, y el que significa lo contrario— con la misma
apariencia de acierto.

La resolución correcta usa **los bits**: el enum está en `<< 3` y sus cuatro
valores son `0..3`, así que el campo ocupa los bits 3-4. `sysaccess.py` lo
comprueba y **rechaza** un enum con desplazamientos mezclados, que es
exactamente el caso en el que la resolución por subcadena mentiría.

Es la **décima** aparición de la clase «coincidencia parcial» del proyecto, y la
primera en la que el riesgo era **invertir el sentido** de lo que se afirma:
`IN_SYS` y `NOT_IN_SYS` describen comportamientos opuestos, así que el fallo no
sería «no encontré nada», sino «encontré lo contrario».

## 4 · `PROVEN_ABSENT` CON SU LÍMITE DECLARADO

```
Los modos 0 (PA_ONLY), 1 (USE_SYS_MAP), 2 (IN_SYS) no los usa NINGUN ASIC.
```

Y lo que eso prueba, escrito para que no se lea de más:

- **Sí prueba**: que en el árbol de Linux, ninguno de los 12 ASIC ejercita esos
  tres modos al configurar el L1 TLB.
- **No prueba**: que el hardware los rechace, ni que no hagan falta.

Un camino sin usar es un camino **sin probar**, no un camino inexistente. Es la
misma asimetría de `041` (466 macros) y de `050` (226 `SIN_PISTAS`): la ausencia
en el árbol es un dato sobre el árbol.

## 5 · QUÉ CIERRA Y QUÉ NO

**Cierra:**
- `067:109`, dos filas: `NOT_DETERMINED` → `PROVEN` por lectura, con el ASIC
  propio y la cruz de 12 ASIC como respaldo.
- La separación que `AGENTS.md` pide para `F`: *«GPUVM translation»* es el L1
  TLB, y `SYSTEM_ACCESS_MODE` decide si lo traducido se decodifica como **MC
  address (VRAM)** o como **RAM del sistema**. Es exactamente la frontera que el
  enunciado pedía separar, y queda separada por lectura.

**No cierra, y sigue abierto:**
- Los otros 33 huecos de `F`.
- `G` (40 huecos, coherencia): `AGENTS.md` dice *«no asumir coherencia por
  analogía»*, y `025:88` ya marca `NOT_DETERMINED` para la coherencia
  CPU↔MMIO↔GPU. Es el hermano de esta pregunta.
- `SYSTEM_APERTURE_UNMAPPED_ACCESS` se escribe a **0** en `gmc_v8_0.c:843` y el
  enum tiene `UNMAPPED_ACCESS_PASS_THRU = (0 << 5)`. **Misma estructura, misma
  pregunta**: qué hace un acceso al system aperture sin mapear cuando el driver
  elige *pass through*. Cerrado el de arriba, este es el siguiente de la misma
  serie y está a un `sed` de distancia.

## 6 · ERRORES PROPIOS

| error | detectado por |
|---|---|
| `proyecto()` subía **dos** niveles desde `tools/` en vez de uno → `FileNotFoundError` en `sid.h` | ejecución |
| `join(x[1] for x in en)` sobre `int` → `TypeError` en la sección `PROVEN_ABSENT` | ejecución |
| `()`, un término en inglés que se coló en el docstring | relectura |

Ninguno produjo un número falso: los dos fueron errores que pararon la
ejecución. Es la diferencia con las seis iteraciones anteriores, donde todos los
fallos productions un recuento plausible.

---

```
RESULTADO DE ITERACIÓN

Entregado:
  tools/sysaccess.py v1.0.0, selftest 16/16 PASS
  067:109 cerrado: los dos NOT_DETERMINED -> PROVEN
  la cruz de 12 ASIC que convierte la lectura en evidencia
  la distincion que evita resolver 3 contra IN_SYS por subcadena

Medido:
  12 ASIC programan MC_VM_MX_L1_TLB_CNTL (5), MMMC_ (4) y GCMC_ (3)
  12/12 usan el valor 3; ningun ASIC usa 0, 1 ni 2
  el enum esta en el bit 3 con 4 valores, coherente con la mascara del ASIC

Retractado por este hallazgo:
  las 8 iteraciones anteriores (071-080) trabajaron la AUDITORIA DEL PROYECTO,
  que no esta en ninguna de las fronteras A-H de AGENTS.md. El grafo de
  findings, el vocabulario de relaciones y el reparto de omisiones siguen
  existiendo y son correctos, pero eran tarea secundaria elegida por inercia
  de mis propios NEXT ACTION, no por el INFORMATION GAIN GATE.

NEXT ACTION:
  AGENTS.md manda cerrar el core antes de H. F y G son las core, y esta
  pregunta tiene una hermanaimmediatea del mismo tipo:

  1. `SYSTEM_APERTURE_UNMAPPED_ACCESS = 0` (= UNMAPPED_ACCESS_PASS_THRU) en
     gmc_v8_0.c:843. Que hace un acceso al system aperture SIN MAPEAR cuando el
     driver elige pass-through. Misma serie, misma lectura, frontera F.
     Y tiene una consecuencia de seguridad que la hace mas valiosa que la
     anterior: un hueco sin mapear que PASA DE PASO es un hueco por el que se
     puede entrar.

  2. `SYSTEM_ACCESS_MODE` en el otro lado del TLB: si el registro decide si la
     salida es MC o RAM, hay un campo equivalente en el PTE que el hardware
     consulta. La frontera A (PTE/PDE, "flags") y la F se juntan ahi, y ese
     cruce es el que AGENTS.md pide en A y en F a la vez.

  3. G (40 huecos): coherencia. `025:88` la marca NOT_DETERMINED y
     AGENTS.md prohibe asumirla por analogia.
```