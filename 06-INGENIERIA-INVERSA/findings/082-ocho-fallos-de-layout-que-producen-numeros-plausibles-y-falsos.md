# 082 · Ocho fallos de layout que producen numeros plausibles y falsos

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## Por que esto merece un documento

Un error de herramienta que devuelve un valor equivocado es mucho peor que uno que
falla. Un `None` se ve. Un `1120` con `CONFIANZA COMPLETA` no se ve: se usa, se anota
como PROVEN y se propaga.

Los ocho fallos de aqui tienen esa misma forma. Todos estan medidos con gcc como
referencia, y todos estaban presentes mientras el self-test pasaba en verde.

## Conformidad medida

`tools/gccverify.py` compila la cabecera real del corpus, lee `sizeof` y `offsetof` del
compilador, y los compara con el modelo de `tools/struct_layout.py`.

```
smu74_discrete.h         coinciden 32   divergen 0   no medidas 0
smu73_discrete.h         coinciden 29   divergen 0   no medidas 0
smu72_discrete.h         coinciden 31   divergen 0   no medidas 0
smu75_discrete.h        coinciden 32   divergen 0   no medidas 0
TOTAL 124 structs · 124 coinciden · 0 divergen
```

Estado **anterior** a estas correcciones, mismo metodo: 31/32 en smu74_discrete.h, con
`SMU7_MclkDpmScoreboard` divergiendo.

## Los ocho fallos

| # | fallo | como se manifestaba | como se caza |
|---|---|---|---|
| 1 | `parse_fields` descarta arrays multidimensionales | `entries[A][B]` se pierde; el struct mide 0 en ese campo | gcc: `SMU74_Discrete_MCArbDramTimingTable` = 384, el modelo daba 0 |
| 2 | `main()` no llamaba a `resolve_nested` | la CLI no mide nada anidado: `TAMANO None` en el caso de uso principal | el caso que falla es el que la herramienta existe para medir |
| 3 | macros con definiciones conflictivas resueltas por orden de recorrido | `SMU__NUM_PCIE_DPM_LEVELS` = 8 en seis ficheros, `0` en `pm/legacy-dpm/kv_dpm.h:29`; el array resultante mide 0 | `sizeof(DpmTable)`: 1756 en vez de 1884. Diferencia = 128 = `16 * 8`, el array que faltaba |
| 4 | `layout` cuenta un limite sin resolver como **1 elemento** | `T a[NO_EXISTE]` mide 4 bytes en vez de declarar que no se sabe | vector de self-test propio; el total queda `None` |
| 5 | una declaracion no reconocida no invalida el total | `CONFIANZA COMPLETA` con un campo de menos | ahora `unknown` no vacio → `total_size = None` |
| 6 | punteros sin parsear | `uint32_t *p;` se pierde; con las estrellas cambiadas por espacios, `type_size` media el **tipo base**: un puntero de 4 | gcc: `Ptrs` = 32, el modelo daba 24 |
| 7 | punteros a funcion sin parsear | `void (*TargetStateCalculator)(uint8_t);` se pierde: 16 bytes | `SMU7_MclkDpmScoreboard`: 92 en vez de 106 |
| 8 | `#pragma pack(push, 1)` ignorado | `smu74.h:28` empaqueta toda la cabecera; el modelo alineaba los punteros a 8 | `_Alignof(SMU7_MclkDpmScoreboard)` = 1 |

### Tres que no son de layout

Estan en `tools/smc_layout.py` y producen el mismo tipo de fallo.

| # | fallo | como se manifestaba |
|---|---|---|
| 9 | `sizeof(u8)`, `sizeof(u32)` tratados como "tipo no medido" | 77 de 110 copias de la SMC sin auditar por no saber que un `u32` ocupa 4 bytes |
| 10 | `#define` con comentario final no se indexaba | **132 macros** del subarbol `pm` desaparecian en silencio, entre ellas `SMU__NUM_PCIE_DPM_LEVELS`. Una macro ausente y una macro que vale cero se confunden |
| 11 | el evaluador de `sizeof` no multiplicaba | `sizeof(T) * SMU7_MAX_LEVELS_GRAPHICS` daba `None`, que es indistinguible de "falta el tipo" |

## La regla que los une

`SILENT_ZERO_IS_A_CLAIM`.

Un `0` medido, un `1` por defecto, un total sin declarar que falta un campo: todos
producen un numero. Y un numero no se distingue de una verdad a simple vista. Lo que
hace falta no es acertar mas, es **declarar cuando no se sabe**.

Consecuencias concretas que se tomaron:

- un cuerpo de struct con contenido que produce **cero** campos no es un struct de cero
  bytes: no se ha parseado, y se declara
- `DIVISION_NO_AUDITABLE`: `sizeof(A) / sizeof(B)` es un numero de elementos, no de
  bytes, y aceptarlo como longitud daria por buena una copia ocho veces corta
- un limite de array sin resolver es `None`, jamas `1`
- `CONFIANZA COMPLETA` exige que no quede ninguna declaracion sin entender

## Verificacion independiente

Los vectores del self-test de `struct_layout.py` no estan inventados: 11 structs y 23
offsets fijados por `gcc` con `_Static_assert`, que cubren punteros, arrays
multidimensionales, array flexible y `pack`.

```
gcc -o /dev/null crosscheck.c   ->  19 asserts, todos se cumplen
```

Y `gccverify.py` tiene su propio self-test con las tres salidas: `OK`, `NO_COMPILE` y
`SIN_CAMPOS`. Una herramienta que solo sabe decir que si no se puede usar para detectar
sus propios fallos.

## Clasificacion

- `STRUCT_LAYOUT_CONFORMANCE = PROVEN`: 124/124 contra gcc en cuatro generaciones.
- `GCCVERIFY = TOOL_VALIDATED`.
- `STRUCT_LAYOUT_SELF_TEST = TOOL_PARTIAL`: los vectores ahora exceden al fixture, pero
  solo cubren 11 structs. La conformidad sobre el corpus se midio con `gccverify`, no
  con el self-test, y por eso existen las dos cosas.

## Lo que esto NO dice

`gcc` es la verdad de terreno del **layout en x86-64**. No dice nada del firmware, del
hardware, ni de si el driver usa bien el valor. Un struct bien medido y mal usado sigue
siendo un bug.