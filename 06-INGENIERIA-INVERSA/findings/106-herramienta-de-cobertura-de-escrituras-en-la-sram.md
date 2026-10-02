# 106 · Una herramienta para la pregunta que fallo tres veces, y su limitacion declarada

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## El problema que esta herramienta viene a resolver

Tres documentos consecutivos (`102` y `104`, dos veces este ultimo) produjeron un veredicto
**equivocado** por el mismo motivo: comparar rangos en **sistemas de coordenadas
distintos**.

- `102`: el clasificador no distinguia "puesto a cero a proposito" de "nunca tocado".
- `104`, primer intento: comparar el final de un array en base de host contra la base de
  la copia, y obtener "0 bytes fuera".
- `104`, segundo intento: sumar 108 donde habia que restarlo, y obtener "invade 108 bytes".

En los tres, la **aritmetica era correcta** y el **veredicto era el contrario de lo que
corresponde**. Eso no se arregla con mas cuidado al calcular: se arregla haciendo que la
comprobacion sea mecanica y repetible.

## `tools/smc_copy_scope.py` 1.0.0 · TOOL_VALIDATED

La pregunta que responde, y que es la que faltaba:

> **Esta escritura en la SRAM del SMC, la pisa despues otra escritura?**

Que no es lo mismo que "escriben en la misma direccion": una escritura puede estar mal y
quedar anulada por una copia posterior mas grande, y a la inversa.

Estado: `TOOL_VALIDATED`, 13 vectores de self-test.

## Las dos reglas que hacen que funcione

### 1. Cada destino lleva su BASE, y dos bases distintas nunca se comparan

Esta regla corrige directamente el error que me costo a mano en `104`. Sin ella, la
herramienta dijo que `polaris10_smumgr.c:140` (que escribe `dpm_table_start + 112`) quedaba
tapada por `:1507` (que escribe `arb_table_start`): **dos tablas distintas**, comparadas
como si fueran la misma region.

Con la regla, cada escritura lleva el nombre de su base (`TABLA_DPM` para lo que se
expresa como `dpm_table_start + offsetof(...)`, `miembro:<expr>` para lo que es un
direccion de tabla propia), y `decide()` rechaza cualquier pareja con bases diferentes.

Es el caso M del self-test, y existe precisamente porque es el fallo que ya cometi.

### 2. La contencion exige rango COMPLETO, no solape

Un solape parcial deja bytes sin cubrir. `MemoryLevel` en `+708` (96 B) frente a
`GraphicsLevel` en `+236` (448 B) se solapan, pero la segunda no contiene a la primera: los
96 bytes de `MemoryLevel` quedan fuera. Es el caso C, y el fixture esta para que ese par
no se confunda con el par tapada/viva.

## Los pares que se confirman mutuamente

El self-test no tiene un caso: tiene pares. Sin un par que se confirme, una herramienta
que no distingue un caso malo de uno bueno no prueba nada.

| caso | diferencia | resultado exigido |
|---|---|---|
| A vs B | la segunda copia mide 1776 o 8 | `TAPADA` vs `VIVA` |
| C | solape pero no contencion | `VIVA` |
| J vs K | falta uno de los dos `sizeof` | 1776 vs `None` |
| L | cast delante del `sizeof` | 36 |
| M | dos bases distintas | la primera queda `VIVA` |

El caso **K** es el que mas me importa: si falta el `sizeof` de uno de los dos operandos,
la herramienta **no devuelve el que sí sabe**. Devolver 1884 a medias, cuando la
expresion es `sizeof(A) - 3 * sizeof(B)`, seria exactamente el 108 que da nombre al hueco.
Un numero plausible y falso.

## Lo que el self-test cazo, incluidos fallos de la propia herramienta

Los documento porque son reales, y porque el caso 9 (comprobar que el fuente no tenga CJK)
me cazo a mi:

1. **La segmentacion agrupaba la firma con la primera sentencia**, asi que la declaracion
   `uint32_t array = dpm_table_start + offsetof(...)` nunca quedaba aislada y el patron a
   resolver no se veia.
2. **Partir los argumentos por coma a pelo rompia `offsetof(T, campo)`**: la coma interna
   partia el destino en dos. Y lo grave es que la herramienta **seguia devolviendo una
   fila**, con el destino truncado: un fallo silencioso que parece un dato.
3. **Solo miraba el primer argumento**, igual que el fallo que cometi en `uninit_copy`.
4. **La funcion salia `?`** en todas las escrituras, porque la segmentacion empieza
   despues de la llave y la firma nunca llega a ser una sentencia.
5. **CJK en el fuente**, escrito por mi al anadir un comentario.

## La limitacion, y donde se manifiesta

La herramienta usa el **orden textual de las sentencias**, y solo sabe que una escritura
tapa a otra si estan **en la misma funcion**. Across functions no sabe quien va antes, y
por eso **no afirma cobertura**: la deja como no cubierta.

Eso se manifiesta justo en el caso que mas importa:

```
VIVA      140  polaris10_setup_graphics_level_structure   112..115
TAPADA    ...  polaris10_init_smc_table                   108..1883
```

La herramienta dice `VIVA` porque estan en funciones distintas, y **tiene razon en no
afirmar**. La verdad es que `init_smc_table` corre despues y la sobreescribe, y para
saberlo hay que seguir la cadena de llamadas a mano.

Y al seguirla a mano (abajo) resulta que la conclusion es la misma que en la correccion
manual de `104`: la copia completa va la ultima y tapa las parciales.

O sea: **la herramienta no cerro ese caso, pero tampoco lo dio por bueno**. Es
exactamente el comportamiento que quiero: cuando no sabe, dice que no sabe, en vez de
inventar una cobertura.

## Lo que si resuelve, y con numeros del compilador

Los offsets vienen de `gccverify`, que los pide al gcc de verdad: **98 offsets medidos**
para `SMU74_Discrete_DpmTable`, no calculados por mis reglas de ABI. Y la aritmetica del
tamano la resuelve con la misma regla:

```
smumgr/polaris10_smumgr.c:2115   dpm_table_start + offsetof(SystemFlags)
                                 tam=108..1883   1776B
```

Que es exactamente el `1884 - 108 = 1776` del hallazgo `104`, obtenido por la
herramienta y no por calculo mio.

## La cadena que la herramienta NO puede seguir

Para cerrar el orden real hace falta esto, verificado a mano:

```
amdgpu_dpm.c:680          pp_funcs->load_firmware(...)          = pp_dpm_load_fw
amd_powerplay.c:315       hwmgr->smumgr_funcs->start_smu(...)   = polaris10_start_smu
polaris10_smumgr.c:318    smu7_request_smu_load_fw(hwmgr)
polaris10_smumgr.c:311    polaris10_avfs_event_mgr(hwmgr)
polaris10_smumgr.c:182    polaris10_setup_graphics_level_structure(hwmgr)
                          -> escribe en :140, :147, :155, :164
```

y despues, en otro camino:

```
smu7_hwmgr.c:1622         smum_init_smc_table(hwmgr)
polaris10_smumgr.c:1913   polaris10_init_smc_table
polaris10_smumgr.c:2118   smu7_copy_bytes_to_smc   -> la copia de 1776 B
```

O sea: **las escrituras de `:140`..`:164` ocurren ANTES que la copia completa de `:2118`,
y quedan tapadas.** Confirmado por las dos vias.

Y las de `:1143` (448 B de `GraphicsLevel`) y `:1243` (96 B de `MemoryLevel`): estan en
`polaris10_populate_all_graphic_levels` y `..._memory_levels`, que se llaman desde
`init_smc_table` en `:1956` y `:1960`, o sea **antes** de la copia de `:2118`. Tambien
tapadas.

Y `:2252` (36 B de la tabla de ventilacion) y `:1507` (384 B de la de arbitraje) estan en
**otras tablas**, con **otras bases**: no hay nada que las tape y no hay nada que puedan
tapar. `VIVA` de verdad.

Y `:2396` (4 B de `LowSclkInterruptThreshold`) esta en `polaris10_update_sclk_threshold`,
que se invoca desde el camino de OverDrive, **fuera** de `init_smc_table`. Ahi si no hay
copia posterior: `VIVA` de verdad.

## Lo que esto deja establecido sobre `103` y `104`

| escritura | tabla | queda tapada por la copia de 2118? |
|---|---|---|
| `:140` VRConfig | DPM | **si** |
| `:147`/`:155` avfs | DPM | **si** |
| `:164` BootMVdd | DPM | **si** |
| `:1143` GraphicsLevel | DPM | **si** |
| `:1243` MemoryLevel | DPM | **si** |
| `:2252` FanTable | ventilacion | no, otra tabla |
| `:1507` ArbTable | arbitraje | no, otra tabla |
| `:2396` LowSclkInterruptThreshold | DPM | **no**: camino de OverDrive |

Y los parches de `103`, `update_uvd_smc_table` y `update_vce_smc_table`, **no aparecen**
en la lista de escrituras de la tabla. Y es por una razon que hay que entender, no por un
hueco de la herramienta: **no son copias, son leer-modificar-escribir** con
`cgs_read_ind_register` y `cgs_write_ind_register`. La herramienta busca
`smu7_copy_bytes_to_smc`, y esos dos sitios no la llaman.

Es una limitacion real de alcance: **la herramienta solo ve copias por la funcion de
copia, no las que se hacen registro a registro.** Los parches de `103` son exactamente
del segundo tipo, asi que su analisis tiene que seguir siendo manual.

## Clasificacion

- `SMC_TOOL_SCOPE = TOOL_VALIDATED`: 13 vectores, incluidos tres pares que se confirman
  mutuamente y un par base-distinta.
- `SMC_COPY_TAPADA_IS_FUNCTION_LOCAL = PROVEN_DERIVED`: la contencion solo se afirma
  dentro de una funcion. Across functions la herramienta declara que no sabe.
- `SMC_PARTIAL_COPIES_TAPPED_BY_FULL_COPY = PROVEN` por la cadena de llamadas completa:
  `:140`, `:147`, `:155`, `:164`, `:1143`, `:1243` quedan tapadas por `:2118`.
- `SMC_FAN_AND_ARB_WRITES_UNTOUCHED = PROVEN`: `:2252` y `:1507` estan en tablas con
  base propia; nada las tapa ni pueden tapar.
- `SMC_OVERDRIVE_WRITE_UNTOUCHED = PROVEN_DERIVED`: `:2396` esta en
  `polaris10_update_sclk_threshold`, camino de OverDrive, sin copia posterior en esa
  base. `RUNTIME_MISSING` si se ejecuta en esta placa.
- `SMC_RAW_REGISTER_WRITES_NOT_SEEN = PROVEN_ABSENT`: los parches de `103` no usan
  `smu7_copy_bytes_to_smc`, luego la herramienta no los detecta. **Limitacion de alcance
  declarada, no un hallazgo.**
- `SMC_TOOL_GOT_TWO_BASES_WRONG = PROVEN`: la primera version de la herramienta
  comparaba `dpm_table_start + 112` contra `arb_table_start` y daba una cobertura falsa.
  Corregido por el caso M.

## Lo que esto obliga a hacer en un driver propio

La regla que sale de las tres correcciones: **una comprobacion de desplazamiento tiene que
ser una funcion que calcula el rango en la base correcta, y una tabla que declara el
tamanio tiene que decir de donde sale cada byte.**

En concreto, en un driver propio:

1. `smc_addr(campo)` como funcion unica, con la compensacion del hueco dentro, y ninguna
   llamada a `dpm_table_start + offsetof` fuera de ella.
2. Un assert de rango que compare **en la base de la copia**, no en la base de la struct,
   cuando lo que se quiere comprobar es si una copia pisa a otra.
3. Y, para el caso de `103`, un mecanismo distinto: los leer-modificar-escribir registro a
   registro **no pasan por la copia**, asi que necesitan su propia verificacion. Una
   lectura de confirmacion tras escribir, no un assert de rango.
