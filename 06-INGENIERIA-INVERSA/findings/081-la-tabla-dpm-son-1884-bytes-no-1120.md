# 081 · `SMU74_Discrete_DpmTable` son 1884 bytes, no 1120: una CORRECCION

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## Que se corrige

El valor `SMU74_Discrete_DpmTable = 1120 bytes` estaba registrado como **PROVEN** en
la memoria de la sesion, con la longitud de copia derivada `1120 - 3*36 = 1012`.

**Ese valor es incorrecto. El tamano real es 1884 bytes y la copia son 1776 bytes.**

El invariante que lo sostenia (`offsetof(SystemFlags) == 3 * sizeof(PIDController)`)
**si se cumple** y por eso el error no se veia mirando el invariante. Lo que estaba mal
era el total.

## Evidencia

La longitud de la copia esta escrita en el driver, en forma de expresion, y se puede
ejecutar:

`drivers/gpu/drm/amd/pm/powerplay/smumgr/polaris10_smumgr.c:2118-2123`

```c
result = smu7_copy_bytes_to_smc(hwmgr,
                smu_data->smu7_data.dpm_table_start +
                offsetof(SMU74_Discrete_DpmTable, SystemFlags),
                (uint8_t *)&(table->SystemFlags),
                sizeof(SMU74_Discrete_DpmTable) - 3 * sizeof(SMU74_PIDController),
                SMC_RAM_END);
```

Medido por el compilador, no por lectura:

| magnitud | valor |
|---|---|
| `sizeof(SMU74_Discrete_DpmTable)` | **1884** |
| `sizeof(SMU74_PIDController)` | 36 |
| `offsetof(SMU74_Discrete_DpmTable, SystemFlags)` | 108 |
| `3 * sizeof(PIDController)` | 108 |
| **longitud de la copia** | **1776** |
| cola del struct desde `SystemFlags` | 1776 |

Las dos ultimas filas coinciden: la copia llena exactamente desde `SystemFlags` hasta
el final de la struct. Eso es una comprobacion independiente del total, y confirma que
1884 es el valor correcto: con 1120 la copia habria sido 1012 y habria dejado 664 bytes
de la tabla sin subir al SMC.

### Como se ha medido

`smu74.h` no tiene ningun `#include`, asi que `smu74_discrete.h` compila suelto. Eso
permite preguntarle al compilador en vez de deducirlo:

```
$ gcc -I.../pm/powerplay/inc -o copy copy.c && ./copy
sizeof(DpmTable)      = 1884
```

La herramienta que hace esto de forma automatizada y reutilizable es
`tools/gccverify.py` (clasificada `TOOL_VALIDATED`), con su `--model` comparando el
modelo contra gcc campo a campo.

## Por que el error era posible

El valor 1120 no salia de medir: salia de la aritmetica interna del propio driver leida
como si el total fuese el final de la tabla. `struct_layout` daba 1120 en su momento
por cuatro fallos encadenados, todos del mismo tipo — **producen un numero plausible y
falso, no un error** — que se detallan en `082`:

1. `parse_fields` descartaba los arrays multidimensionales. `LinkLevel[SMU74_MAX_LEVELS_LINK]`
   se perdia y el struct media 0 bytes en ese campo.
2. Una macro con definiciones conflictivas se resolvia por orden de recorrido.
   `SMU__NUM_PCIE_DPM_LEVELS` vale `8` en seis ficheros y `0` en
   `pm/legacy-dpm/kv_dpm.h:29`; si ese se recorre primero, `LinkLevel[8]` mide 0.
3. Los punteros no se parseaban. `uint32_t *p;` caia al final de la cadena.
4. `layout` contaba un limite de array sin resolver como **1 elemento**, y una
   declaracion no reconocida no invalidaba el total: `CONFIANZA COMPLETA` con el campo
   equivocado.

Con (2) corregido, `LinkLevel` pasa de 0 a 16 bytes y el total de 1756 a **1884**, que es
justo 1884 - 1756 = 128 = `16 * 8` el array que faltaba.

## Consecuencia que queda abierta

La copia son **1776 bytes** a partir de `smu_data->smu7_data.dpm_table_start`. Con el
valor antiguo eran 1012. Si `dpm_table_start` se situara cerca del final de la RAM del
SMC, la diferencia entre 1012 y 1776 bytes decide si la subida cabe o no.

`dpm_table_start` se calcula con `SMC_RAM_END` menos el tamano reservado. Ese
tamano reservado es `NOT_DETERMINED` en este punto: no se ha medido. Es la
siguiente medicion util de esta linea, y es medible estaticamente porque el codigo que
lo reserva esta en el mismo subarbol.

## Clasificacion

- `SMC_TABLE_SIZE = PROVEN` en 1884, por compilador sobre la cabecera real.
- `SMC_COPY_LENGTH = PROVEN` en 1776, y coherente con la cola del struct.
- `1120 bytes` → **REFUTED**. Registrado como correccion, no como resultado.
- `SMC_RESERVED_TABLE_SIZE = NOT_DETERMINED`. Requiere medir el reparto de la RAM del
  SMC.

## Lo que este hallazgo NO dice

No dice que hace el firmware con esos 1776 bytes. El contrato de memoria esta medido;
la interpretacion sigue `NOT_IN_CORPUS`.

No se ha tocado el hardware. No hay escritura. No hay `/sys`, no hay modulos, no hay
commits.