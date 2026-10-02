# 087 · Los tres PIDController no los escribe el host: son del firmware

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## La pista

`polaris10_smumgr.c:2122` tiene esta longitud de copia:

```c
sizeof(SMU74_Discrete_DpmTable) - 3 * sizeof(SMU74_PIDController)
```

Restar `3 * sizeof(PID)` no sale de la nada. Si la struct tiene tres PID al principio
y la copia empieza justo despues, la resta es una manera indirecta de decir "desde
`SystemFlags` hasta el final". La forma es rara y por eso merece comprobarse.

Comprobado: `offsetof(SMU74_Discrete_DpmTable, SystemFlags)` = 108, y
`3 * sizeof(SMU74_PIDController)` = 3 x 36 = **108**. La resta coincide exactamente
con el offset del primer campo que no es un PID.

## Resultado: el host no escribe los 108 primeros bytes

Prueba por union de intervalos, no por conteo. Las copias del host cuyo destino cae
dentro de `dpm_table_start`:

```
:2118  [  108, 1884)  len=1776  SystemFlags
:2398  [ 1692, 1696)  len= 4    LowSclkInterruptThreshold

union = [(108, 1884)]
[0,108) cubierto?  False
cobertura total: 1776 de 1884 bytes
```

La segunda escritura esta dentro de la primera, asi que la union es un solo intervalo.

Y no es que las otras escrituras se me escapen: las que pasan por variables
precalculadas (`vr_config_address`, `graphics_level_address`, `array`) se calculan en
`polaris10_smumgr.c:140,147,155,164`, y **los 12** sitios del fichero que tocan
`dpm_table_start` tienen la forma `dpm_table_start + offsetof(SMU74_Discrete_DpmTable,
campo)`. Sin excepcion:

| offset | campo | linea |
|---:|---|---|
| 108 | `SystemFlags` | 2119 |
| 112 | `VRConfig` | 140 |
| 236 | `GraphicsLevel` | 147, 1046, 2594 |
| 708 | `MemoryLevel` | 155, 1215, 2597 |
| 1576 | `UvdBootLevel` | 2292 |
| 1577 | `VceBootLevel` | 2328 |
| 1592 | `BootMVdd` | 164 |
| 1692 | `LowSclkInterruptThreshold` | 2400 |

Offset minimo alcanzado: **108**. Ninguno por debajo.

## Y no es que el host los lea

Recuento sobre todo el subarbol `pm/powerplay`:

```
apariciones de "PIDController" en ficheros .c :  6
que no son la aritmetica del tamano         :  0
```

Las seis son la misma expresion, una por generacion:

```
polaris10_smumgr.c:2122   sizeof(SMU74_Discrete_DpmTable) - 3 * sizeof(SMU74_PIDController)
ci_smumgr.c:2114         sizeof(SMU7_Discrete_DpmTable)  - 3 * sizeof(SMU7_PIDController)
fiji_smumgr.c:2108       sizeof(SMU73_Discrete_DpmTable) - 3 * sizeof(SMU73_PIDController)
tonga_smumgr.c:2439      sizeof(SMU72_Discrete_DpmTable) - 3 * sizeof(SMU72_PIDController)
vegam_smumgr.c:2137      sizeof(SMU75_Discrete_DpmTable) - 3 * sizeof(SMU75_PIDController)
iceland_smumgr.c:2060    sizeof(SMU71_Discrete_DpmTable) - 3 * sizeof(SMU71_PIDController)
```

**Ningun `.c` del subarbol lee ni escribe un campo PIDController.** Solo aparecen en las
cabeceras como declaraciones. Seis generaciones, Tonga, Fiji, CI, Iceland, Vega10 y
Polaris10, exactamente el mismo patron.

## Que es lo que el firmware gobierna

`inc/smu74.h:234`:

```c
struct SMU74_PIDController {
        uint32_t Ki;                    /* ganancia integral */
        int32_t  LFWindupUpperLim;      /* anti-windup por arriba */
        int32_t  LFWindupLowerLim;      /* anti-windup por abajo */
        uint32_t StatePrecision;
        uint32_t LfPrecision;
        uint32_t LfOffset;
        uint32_t MaxState;
        uint32_t MaxLfFraction;
        uint32_t StateShift;
};
```

Nueve campos, 36 bytes. Es un controlador PID de lazo cerrado con anti-windup, que es
justo lo que gobierna una tension en regimen variable. El bucle corre **en el
firmware**.

Que el host lo deje en paz es coherente: un PID necesita leer el error real en cada
muestra, y el host no tiene esa realimentacion.

## Por que esto importa para un driver propio

Dos consecuencias, y la segunda es la trampa:

1. **No hay que rellenar los PID.** Un driver propio que intiente inicializar
   `GraphicsPIDController` esta escribiendo en memoria que el firmware usa y el host no
   lee. No es un campo opcional del contrato: es territorio del firmware.

2. **Los 108 bytes hay que reservarlos igual.** Si el driver propio hace la struct sin
   los tres PID, o si los pone al final, **todos** los offsets posteriores se desplazan
   108 bytes y el firmware lee los campos equivocados sin avisar. No hay ninguna
   comprobacion que lo detecte: es el mismo desplazamiento silencioso de `081`, pero en
   el lado de la escritura en vez de en el lado de la medicion.

O sea: los tres PID se ignoran como contenido y se respetan como espacio.

## El patron es identico en las seis generaciones

Es lo que hace que sea una decision de arquitectura y no un descuido de Polaris10. En
Tonga, un ASIC de 2012, el mismo patron. El host nunca ha gestionado estos
controladores.

## Clasificacion

- `SMC_PID_REGION_NOT_HOST_WRITTEN = PROVEN`: union de escrituras = `[108, 1884)`.
- `SMC_PID_NO_HOST_ACCESS = PROVEN`: 6 apariciones en `.c`, las 6 son la aritmetica del
  tamano, 0 accesos a campo.
- `SMC_PID_OWNER = FIRMWARE`: nueve campos de PID con anti-windup, sin acceso desde el
  host.
- `SMC_PID_RESERVED_SIZE = PROVEN`: 108 bytes, y la expresion de copia lo resta
  explicitamente en las seis generaciones.

## Lo que esto NO dice

No dice que valores tiene el firmware ahi. No dice si los PIDs estan activos. No dice
que el firmware lea los tres, o solo el de graficos: que haya tres no implica que los
tres se usen.

No dice nada del firmware mas alla de esto. `FW_SMU_INTERPRETATION` sigue
`NOT_IN_CORPUS`.