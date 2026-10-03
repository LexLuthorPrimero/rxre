# DRIVER-MISSION-STATE

```
MISSION_ACTIVE            = YES
RUNTIME                   = NOT_RUN
MODULE_LOADED             = NO
PROBE_ACTIVE              = NO
GPU_TOUCHED               = NO
STAGING                   = EMPTY
COMMIT                    = NO
MISSION_COMPLETE          = NO

CURRENT_QUEUE_ITEM        = Q5
COMPLETED_QUEUE           = Q1, Q3, Q4
BLOCKED_QUEUE             = Q2 (OWNED_BY_OTHER_SESSION, en curso)
DEFERRED_QUEUE            = Q5 pertenece al bloque D de 012 (misma sesion)
ACTIVE_FRONTIER           = SUBMISSION_CONTRACT → cerrado
NEXT_REQUIRED_WORK        = Q5 GCN8_OPCODE_FILTER
RUNTIME_REQUIRED          = NO
HUMAN_DECISION_REQUIRED   = NO

ASSERTIONS                = 343
FAILURES                  = 0
WARNINGS                  = 0
```

## COLISIÓN DETECTADA — Q2

Otra sesión escribió un **Q2 completo en paralelo en este mismo workspace**, y
sobreescribió el mío.

```
09:04:21  tests/test_mem.c    <- sobreescrito (el mio)
09:04:27  target_mem_host.h   <- nuevo, suyo
09:04:32  target_mem.h        <- sobreescrito (el mio)
```

Su Q2 es **más profundo que el mío**: modela la codificación de entradas
PDE/PTE, no solo el ciclo de vida.

```
TM_PDE_LEAF      = bit 54      "GFX8. GFX12 sería el 63"
TM_LEVEL_ENTRIES = 512
TM_PN_BITS       = 28
TM_PA_BITS       = 40
TM_PTE_{VALID,READABLE,WRITEABLE,EXECUTABLE,PRIV}
TM_RESERVED_{CSA,SEQ64,TRAP}  +  TM_VA_USER_START/END
```

**CROSS-VALIDATION.** Su `TM_PN_BITS = 28` y su `TM_PA_BITS = 40` coinciden
con lo que Q1 derivo independientemente del registro
`mmVM_CONTEXT8..15_PAGE_TABLE_BASE_ADDR.PHYSICAL_PAGE_NUMBER` (máscara
`0xfffffff`) y con `TVM_MAX_PHYS_FROM_PN = 2^40`. Dos derivaciones
independientes del mismo hecho de hardware coinciden.

**DECISIÓN**: `Q2 = OWNED_BY_OTHER_SESSION`. No se duplica. No se tocan sus
ficheros. `test_mem` se retiró de la cola de build de esta sesión porque su
`test_mem.c` está a medio escribir (no incluye `target_mem.h`, y
`target_mem_host.h` duplica typedefs que su propio test ya define).

**DEFECTO DEL PROMPT DE MISIÓN**: declara `04-IMPLEMENTACION/rx550-driver/`
como línea canónica compartida para todos los agentes, y reparte la misma cola
Q1..Q20. Dos agentes que toquen la misma Q se pisan. Requiere partición por
agente o por Q.

## Closed

| Q | qué cierra | evidencia |
|---|---|---|
| Q1 | GPUVM_MINIMAL_MODEL | límites leídos de `gmc_8_2_d.h` + `sh_mask`, cross-check en test |
| Q3 | FENCE_MODEL | estado + monotonicidad ESA + wraparound; P-8 reutilizado, no reabierto |
| Q4 | SUBMISSION_CONTRACT | `EJECUCION` no es estado de la máquina; requiere lectura independiente |
| C4-rep | defecto reparado | `-EBUSY` se propagaba como `-ENODEV` |

## Hallazgo estructural de Q1 (condiciona todo lo demás)

```
gca/gfx_8_0_d.h     ->   0 registros mmVM_*/mmGTT*/mmPTE*
gc/gc_9_0_offset.h  -> 510
gmc/gmc_8_2_d.h     ->  los de GFX8, bloque GMC
```

GFX8 no tiene motor de recorrido de tabla de páginas. La tabla la escribe la
CPU. El modelo de VM es plano por necesidad, no por elección.

## Invariante de Q1 que Q2 confirma por otra vía

```
NÚMERO DE PÁGINA FÍSICA != DIRECCIÓN FÍSICA
28 bits + 12 de shift = 40 bits
```

## Regla que Q4 hace estructural

```
WPTR  demuestra que se publicó
RPTR  demuestra que se consumió
FENCE demuestra que llegó al fence
NINGUNO demuestra que hubo efecto

tse_effect_observed() exige una LECTURA del destino.
No existe transición que alcance "ejecución".
```

## Stop conditions

Ninguna cumplida. Q5 es accionable sin runtime.

---

# ACTUALIZACION DE ESTADO (967) — Q5 CERRADA EN PARTE, no cerrada

Registro en el **estado canonico**, no en el documento de diseño, porque aquí es donde vive
`NEXT_REQUIRED_WORK`. El texto de arriba no se borra.

## Que estaba cerrado y que no

`Q5 GCN8_OPCODE_FILTER` era `NEXT_REQUIRED_WORK`. Lo que 967 cierra es **una parte** de Q5:

```
DECIDIR LA TABLA instruccion->opcode          CERRADO   la tabla EXTERNAL existe y esta medida
DISCRIMINAR LA SUPUESTA AMBIGUEDAD             CERRADO   era la REGLA de agrupacion, no el opcode
EL EFECTO OBSERVABLE EN LA GPU                 ABIERTO   sigue necesitando RUNTIME_REQUIRED
```

## El dato que Q5 pedia

`013` decía: la tabla instrucción→opcode es `RUNTIME_REQUIRED` para verificarlo, pero escribible si se
acepta tabla `EXTERNAL`. Con 967 la `EXTERNAL` ya no es una elección: son 216 entradas de
`gfx_8_0_enum.h`, 63 familias bajo `prefijo2` y 80 bajo `completo`, con **0 colisiones internas** bajo la
regla que se afirma. Instrumento: `gfx8_opcode.py`, con auto-test, 6 controles negativos y cross-check
por `awk/sort/uniq`.

## Lo que sigue bloqueando el efecto observable

No es la tabla. Es que **4 de las 5 tablas de opcode GFX8 no están en el corpus**: solo existe
`gfx_8_0_enum.h`. `NOT_AVAILABLE`, con forma precisa. Un programa con efecto observable necesita además
los campos de operando y registro, que son otra tabla y tampoco están.

## Advertencia que se deja escrita

La primera versión de la herramienta **informaba 0 colisiones con cualquier entrada**, porque guardaba
las familias en un dict indexado por valor, donde dos nombres con el mismo valor no son representables.
No era una medición: era una tautología. Se detectó al darle datos que no podían ser ciertos, no al
ejecutarla. Un instrumento que no puede fallar no es evidencia, por muy verde que sea su salida.
