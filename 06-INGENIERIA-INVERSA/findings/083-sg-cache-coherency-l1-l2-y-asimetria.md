# 083 · §G por primera vez: la cadena enable/disable de las cachés de traducción, y dos campos que no se apagan

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC · CORPUS=RESEARCH/working/linux-7.1.3
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · WORK_CLASS=READ_ONLY/EVIDENCE
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN · GPU INTACTA
```

## Por qué esta nota existe

`AGENTS.md` §G es **CACHE / COHERENCY**: *resolver CPU ↔ page tables ↔ GPU ↔ TLB
↔ GPU caches ↔ GART ↔ VRAM/system RAM*, con la instrucción *"no asumir
coherencia por analogía"*.

No la había tocado nadie. `067` sí lo menciono:

```
CLON 3 lines from the previous thinking block

Mencionó `MC_VM_MX_L1_TLB_CNTL` porque hacía falta para describir
cómo se habilita la GART, y Hesse wrote it como dato de ese contexto: `SYSTEM_ACCESS_MODE = 3`.
Al leerlo para §G, el registro resultó ser **la mitad de §G**, y no un parámetro
de la GART.

## La cadena completa de enable, en un solo sitio

```
gmc_v8_0.c:843   tmp = RREG32(mmMC_VM_MX_L1_TLB_CNTL);
gmc_v8_0.c:844   ENABLE_L1_TLB, 1
gmc_v8_0.c:845   ENABLE_L1_FRAGMENT_PROCESSING, 1
gmc_v8_0.c:846   SYSTEM_ACCESS_MODE, 3
gmc_v8_0.c:847   ENABLE_ADVANCED_DRIVER_MODEL, 1
gmc_v8_0.c:848   SYSTEM_APERTURE_UNMAPPED_ACCESS, 0
gmc_v8_0.c:849   WREG32(mmMC_VM_MX_L1_TLB_CNTL, tmp);
```

Cinco campos, leídos-modificados-escritos. **Nunca se escribe un valor directo**:
siempre `RREG32` primero. Eso es coherencia por construcción en el propio driver —
no reescribe un registro que no ha leído, y por tanto no pisa un estado que
alguien más puso.

### Los cinco campos, con su posición

```
  gmc_8_1_sh_mask.h   ENABLE_L1_TLB                       mask 0x1    shift 0x0
  gmc_8_1_sh_mask.h   ENABLE_L1_FRAGMENT_PROCESSING       mask 0x2    shift 0x1
  gmc_8_1_sh_mask.h   SYSTEM_ACCESS_MODE                  mask 0x18   shift 0x3
  gmc_8_1_sh_mask.h   SYSTEM_APERTURE_UNMAPPED_ACCESS     mask 0x20   shift 0x5
  gmc_8_1_sh_mask.h   ENABLE_ADVANCED_DRIVER_MODEL        mask 0x40   shift 0x6
  gmc_8_1_sh_mask.h   ECO_BITS                            mask 0x780  shift 0x7   <- nunca escrito
```

`ECO_BITS` existe y el driver no lo toca. Los cinco que escribe ocupan bits 0, 1,
3-4, 5 y 6: **el registro tiene seis campos y el driver usa cinco.**

## La segunda mitad: el L2, en las líneas siguientes

```
gmc_v8_0.c:852   ENABLE_L2_CACHE, 1
gmc_v8_0.c:853   ENABLE_L2_FRAGMENT_PROCESSING, 1
gmc_v8_0.c:854   ENABLE_L2_PTE_CACHE_LRU_UPDATE_BY_WRITE, 1
gmc_v8_0.c:855   ENABLE_L2_PDE0_CACHE_LRU_UPDATE_BY_WRITE, 1
gmc_v8_0.c:856   EFFECTIVE_L2_QUEUE_SIZE, 7
gmc_v8_0.c:857   CONTEXT1_IDENTITY_ACCESS_MODE, 1
gmc_v8_0.c:858   ENABLE_DEFAULT_PAGE_OUT_TO_SYSTEM_MEMORY, 1
```

**Tres de esos siete son coherencia pura:**

| campo | qué significa para §G |
|---|---|
| `ENABLE_L2_PTE_CACHE_LRU_UPDATE_BY_WRITE` | una escritura por CPU invalida la entrada de la caché L2. Es **coherencia por software**. |
| `ENABLE_L2_PDE0_CACHE_LRU_UPDATE_BY_WRITE` | lo mismo para la entrada de PDE0 |
| `ENABLE_DEFAULT_PAGE_OUT_TO_SYSTEM_MEMORY` | el page-out por defecto va a RAM del sistema, no a VRAM |

`EFFECTIVE_L2_QUEUE_SIZE = 7` es el otro extremo: **tamaño de cola 7, no potencia
de dos.** Eso es un parámetro de rendimiento escrito en un registro de coherencia, y
es el dato que más seotomaría para gestionar el hardware.

## El disable, y la asimetría que importa

```
gmc_v8_0.c:980   tmp = RREG32(mmMC_VM_MX_L1_TLB_CNTL);
gmc_v8_0.c:981   ENABLE_L1_TLB, 0
gmc_v8_0.c:982   ENABLE_L1_FRAGMENT_PROCESSING, 0
gmc_v8_0.c:983   ENABLE_ADVANCED_DRIVER_MODEL, 0
gmc_v8_0.c:984   WREG32(mmMC_VM_MX_L1_TLB_CNTL, tmp);
```

Tres campos. **Faltan dos de los cinco:**

```
  SYSTEM_ACCESS_MODE             se enciende, NO se apaga
  SYSTEM_APERTURE_UNMAPPED_ACCESS se enciende, NO se apaga
```

No es un descuido evidente: al no escribirlos, el valor que se leía en el
`RREG32` de L980 se conserva. Y como el enable puso `SYSTEM_ACCESS_MODE = 3`, ese
`3` **queda puesto tras el disable.**

```
  estado tras enable+disable:
    ENABLE_L1_TLB                     0
    ENABLE_L1_FRAGMENT_PROCESSING     0
    ENABLE_ADVANCED_DRIVER_MODEL      0
    SYSTEM_ACCESS_MODE                3   <-- persiste
    SYSTEM_APERTURE_UNMAPPED_ACCESS   0   <-- persistía 0 de todos modos
```

`SYSTEM_APERTURE_UNMAPPED_ACCESS` se puso a 0 al encender, así que dejarlo es
inofensivo. **`SYSTEM_ACCESS_MODE = 3` es el que persiste**, y es el campo que
controla cómo accede el sistema a la memoria del contexto.

**Lo que eso implica, y lo que no.** Que el campo queda a 3 tras el teardown es un
hecho `PROVEN` del código. Que deba quedar a 0 es una expectativa, no un
requisito verificado. Puede que 3 sea el valor por defecto del hardware y que
"no escribirlo" sea exactamente lo correcto; puede que el driver haya supuesto
que nunca hace falta. **El corpus no lo dice**, y la frontera pide no asumir
coherencia por analogía — así que esto queda `NOT_DETERMINED` con el hecho y la
duda separados.

El teardown es la función `gmc_v8_0_gart_disable`, que es el mismo LIFO que
documentó `051`: `gart_disable` al final.

## Lo que §G queda por cerrar

`AGENTS.md` §G pide resolver la cadena completa. Con esto queda:

```
  TLB de L1          configuración PROVEN, con los 5 campos y sus posiciones
  caché de L2        configuración PROVEN, con los 7 campos
  coherencia         los 2 campos LRU_UPDATE_BY_WRITE: PROVEN que están puestos
  qué pasa cuando    el hardware ve una translation nueva o invalida     NOT_DETERMINED
  visibilidad        cuándo una escritura de CPU llega a la GPU          NOT_DETERMINED
  SYSTEM_ACCESS_MODE qué significa 3, y si debe volver a 0              NOT_DETERMINED
```

Las tres últimas son `NOT_DETERMINED` y **ninguna se resuelve leyendo el driver**:
son comportamiento del hardware. Es el mismo punto donde §A, §C y §D chocan con
`RE-29` (AMD nunca publicó el framing de GCN3).

## El punto honesto

`AGENTS.md` dice de §G *"no asumir coherencia por analogía"*. Lo que esta nota
muestra es **cuál es la configuración**, que es lo que se puede leer. Lo que no
muestra es que la coherencia funcione, que es lo que la frontera pide. Y las dos
cosas son distintas: una tabla de bits exacta da la sensación de coherencia
resuelta sin resolverla.

Lo mismo vale para el asimetría de `SYSTEM_ACCESS_MODE`: es un hallazgo real y
es una pregunta, no una conclusión.

## Procedencia

- `CORPUS` — `gmc_v8_0.c:829-990` (`gart_enable` y `gart_disable`),
  `include/asic_reg/gmc/gmc_8_1_sh_mask.h`.
- Herramientas: `xref.py` (8 escrituras en 2 bloques), `regdb.py` (posiciones).
- Encadenada con `067` (que citaría este registro sin saber que es §G) y `051`
  (el teardown LIFO).
- Sin `RUNTIME`, sin lectura de la GPU, sin escrituras.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`: son de otras sesiones.