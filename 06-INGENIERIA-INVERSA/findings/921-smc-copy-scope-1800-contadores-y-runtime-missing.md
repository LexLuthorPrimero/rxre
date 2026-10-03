# 921 · `smc_copy_scope` 1.8.0: contadores por línea y el estado `RUNTIME_MISSING`

WORK_CLASS=READ_ONLY · MODIFICATIONS: **1 fichero**, `tools/smc_copy_scope.py`, mío · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Resultado
>
> Los dos arreglos que pedí están **hechos y validados**, y uno de ellos resultó
> ser mejor de lo que yo había planeado: los cinco `NO_RESUELTO` no eran cinco.
>
> **Tres son `RUNTIME_MISSING`**, un estado que no existía: la dirección la
> asigna el firmware en runtime, así que no cabe afirmar cobertura ni en un
> sentido ni en el otro. Mezclarlos con «el instrumento no pudo» era el defecto.
>
> Y el recuento del self-test **mintía**: decía 34 vectores ejecutando 81.

## 1. Qué cambió

### A) Contadores indexados por punto de uso

`--contador NOMBRE@LINEA=N`. El caso real es `array_size`, que vale **448** en
`:1048` y **96** en `:1217`, con el mismo nombre.

Antes se indexaban por nombre plano, así que había que elegir uno. Elegir mal da
un rango con la magnitud correcta y el valor equivocado: **un número plausible y
falso**, que es peor que un cero porque no se detecta como ausencia.

Tres reglas que hicieran falta y que no eran obvias:

1. **Refinan, no sustituyen.** Si ninguna declaración por línea aplica a un uso,
   se cae al contador global. Sin eso, un `--contador array_size@9=96` rompía
   todo lo anterior, que es justo lo que sí tiene valor.
2. **Se comparan con la línea de la llamada, no con el inicio del fragmento.** Un
   fragmento arranca tras el `;` anterior y puede cubrir dos o tres líneas antes
   de la llamada. Con el inicio, una declaración en la línea de la llamada queda
   «posterior» y nunca se usa.
3. **Línea, no offset.** `pos` es un offset de carácter y la entrada es un número
   de línea. Compararlos da `233 <= 10`, falso, y el contador nunca se elige.

### B) Estado nuevo: `RUNTIME_MISSING`

Las tres escrituras que la herramienta no reconocía son esto:

```
:654   smu7_read_smc_sram_dword(..., &pm_fuse_table_offset, SMC_RAM_END)   (:614)
:1872  smu7_read_smc_sram_dword(..., &tmp, SMC_RAM_END)                  (:1870)
:1881  smu7_read_smc_sram_dword(..., &tmp, SMC_RAM_END)                  (:1878)
```

**La dirección la dice el firmware cuando corre.** Ningún instrumento estático
puede resolverla, y no son offsets de la tabla DPM, así que **no pueden ser
`TAPADAS` ni por orden ni por rango**.

Eso es una categoría distinta de «el instrumento no pudo», y el diseño de esta
herramienta lleva toda la sesión insistingiendo en no mezclarlas. Se distingue de
una lectura que solo lee por el `&` del puntero de salida, y ese caso Negative
tiene vector.

## 2. El resultado sobre el fichero real

```
smc_copy_scope 1.8.0 · 13 escrituras · 101 offsets · 7 tamanos medidos

TAPADA          4   :142 :149 :157 :166        las cuatro escrituras AVFS
VIVA            3   :1511  :2118  :2254
SIN_ORDEN       1   :2398
RUNTIME_MISSING 3   :654   :1872  :1881
NO_RESUELTO     2   :1146  :1246
```

**Los `NO_RESUELTO` bajan de 5 a 2, y los dos que quedan no son del instrumento
sino del código**, por un motivo concreto y nombrado:

```c
:1046   uint32_t array = smu_data->smu7_data.dpm_table_start +
         offsetof(SMU74_Discrete_DpmTable, GraphicsLevel);
:1215   uint32_t array = smu_data->smu7_data.dpm_table_start +
         offsetof(SMU74_Discrete_DpmTable, MemoryLevel);
```

Un local cuyo valor es `miembro + offsetof(...)` **partido en dos líneas**.
`ctx_vars` no registra esa forma, así que el destino queda sin resolver mientras
que el **tamaño ya se resuelve bien**:

```
:1146  tam=448  nota='variable local array + contador array_size@1046'
:1246  tam=96   nota='variable local array + contador array_size@1215'
```

El arreglo A está aplicado y funciona; lo que falta es la segunda mitad de B, y
ahora se sabe exactamente qué forma hay que enseñarle al resolutor.

## 3. El hallazgo del día dentro de la propia herramienta

```
antes:   smc_copy_scope 1.7.0 · RESULTADO OK · 34 vectores conocidos reproducidos
ahora:   smc_copy_scope 1.8.0 · RESULTADO OK · 81 vectores conocidos reproducidos
```

`CASOS_SELFTEST = 34` era un **literal**. El self-test ejecutaba 81
comprobaciones y decía 34, y llevaba diciendo 34 mientras el número de vectores
crecía.

**Es exactamente el defecto que vengo corrigiendo todo el día, dentro del
instrumento que uso para corregirlo**: un número plausible, constante, y
verificado por nadie.

Corregido de la única forma que no vuelve a pasar: `chk` cuenta de verdad, el
resumen informa del recuento, y hay un **suelo** que avisa y devuelve `exit=3` si
algún vector deja de ejecutarse.

Comprobado subiendo el suelo a 999 a propósito:

```
$ (suelo 999)   ->  exit=3
   aviso: solo 81 comprobaciones ejecutadas y el suelo es 999
```

## 4. Validación

```
BUILD                 SINTAXIS OK (ast.parse)
BASIC TEST            --selftest -> RESULTADO OK, exit=0, 81 vectores
KNOWN INPUT           los 34 vectores previos siguen reproduciéndose
EXPECTED OUTPUT       TAPADA 4 / VIVA 3 / SIN_ORDEN 1 / RUNTIME_MISSING 3 / NO_RESUELTO 2
EDGE CASE             19b: contador declarado solo para lineas posteriores -> NO_RESUELTO
                      20b: una lectura SIN puntero de salida no da RUNTIME_MISSING
FAILURE CHECK         linea no numerica -> aviso y se ignora, no rompe
                      suelo a 999 -> exit=3
OUTPUT VALIDATION     el recuento del resumen es el real, comprobado con el suelo
REGRESSION            CJK en la herramienta: ninguno (lo detecto el vector casoI
                      sobre MI comentario, antes de que lo hiciera yo)
```

Y un fallo que el instrumento me detectó a mí: escribi dos ideogramas chinos en un comentario (esa misma regla, `casoI`, es la que
vigila el fuente de la herramienta, asi que el hallazgo es circular y por eso lo
cita sin reproducirlo) y
el vector `casoI` lo cazó en el self-test siguiente. **La herramienta vigila al
autor.**

## 5. Errores de esta iteración

Todos de la misma familia, y esta vez dentro del código de una herramienta
validada:

**1.** Definí `runtime_asignado` en `segmenta_lineas` y lo usé en
`_analiza_texto`. `NameError` inmediato, visible.

**2.** Metí `_a_offset` comparando líneas con offsets de carácter. Dos unidades
mezcladas. Lo encontré porque los vectores fallaban, no porque lo leyera bien.

**3. El peor, y del mismo tipo que el del VBIOS:** un script mío **falló en una
aserción después de imprimir un mensaje de éxito**, y como la escritura va al
final del script **el fichero no se guardó**. Seguí creyendo que el bloque de
conversión estaba eliminado. Lo encontré porque los vectores seguían fallando con
la lógica ya correcta.

Es un `COMMAND_EXECUTED → CLAIM_PROVEN` en miniatura: imprimí «eliminada» y lo
dije como hecho. Si el mensaje se hubiera impreso **después** de escribir, el
error se habría escondido del todo.

**4.** `Medido.__getitem__` lanza `KeyError` en clave ausente, así que el índice
por línea necesitaba `setdefault`. Lo vi por el `traceback`, no por leerlo.

**5.** Mezclé sangrías de 4 y de 8 espacios al editar, y el `edit` falló dos
veces con «no encontrado». A la tercera fui a buscar la línea exacta.

Ninguno es un error de razonamiento: todos son de **ejecución y verificación de
mi propia edición**, que es donde el proyecto más me ha sobrado hoy.

## 6. Frontier siguiente

**Enseñarle al resolutor de destinos la forma `miembro + offsetof(...)` partida en
dos líneas, para cerrar los dos `NO_RESUELTO` que quedan.**

Es una forma, no una familia: las dos ocurrencias del corpus son idénticas, y el
`tipo` de la expresión ya se resuelve en otros sitios.

```
ENTRADA     uint32_t array = <miembro> + offsetof(T, campo);   en 2 lineas
SALIDA      offset en la struct, como base + offsetof
VALIDACION  caso21 con esa forma; y :1146 -> 236, :1246 -> 708
PIVOTE      si la forma no se reconoce, NO_RESUELTO con el motivo exacto,
            nunca un 0
```

Con eso, **las 13 escrituras quedan clasificadas sin ningún `NO_RESUELTO`**, y
«quién escribe cada byte de los 1776» — que es lo que `502` pidió— pasa de
`PARCIAL` a cerrado.

Y una consecuencia que conviene decir: **`RUNTIME_MISSING` no es un hueco que se
pueda cerrar estáticamente**, y no debe intentarse. Las tres escrituras van a
direcciones que el firmware revela en runtime. Lo que sí se puede, y es lo
siguiente útil, es **saber qué hay en esas direcciones**: `:1872` y `:1881`
escriben `AVFS_meanNsigma` y `AVFS_SclkOffset` en la dirección que el firmware
indica en `SMU74_Firmware_Header`, y eso **sí** es legible en el VBIOS.