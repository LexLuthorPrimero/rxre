# 1203 — Los valores que el driver **pasa** a un campo son una cota inferior de su anchura, y para `PIPE` esa vía da **2 bits**: lo mismo que la vía del hueco, por dos caminos que no se conocen entre sí

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=PM4-SEMANTICS + DIFFERENTIAL-ORACLE
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   tools/ancho_pm4.py  (nuevo, 38 vectores, rc=0)
CLASE=DERIVATION · CORROBORATION · ESTADO=PROBADO_OK
ABRE 1202 §4 punto 5, que era la unica via que quedaba dentro del arbol
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 0 · La idea, y por qué no vale con literales

`1202` barrido 69 091 ficheros y concluded que el árbol **no declara ni una** anchura de campo
PM4, para ningún ASIC, y que la deducción por huecos de `1200` cierra 1 grupo de 15. La vía
que quedaba dentro del árbol era ésta:

```text
los valores que el driver le PASA a un campo son una cota INFERIOR de su anchura
```

Y se probó primero con literales, y **no daba nada**:

```text
  MAP_QUEUES_QUEUE_SEL=0  VMID=0  ENGINE_SEL=1  NUM_QUEUES=1
```

Todo 1 bit, porque el driver casi nunca pasa literales a los campos que importan:

```c
  PACKET3_MAP_QUEUES_QUEUE(ring->queue)
  PACKET3_MAP_QUEUES_PIPE(ring->pipe)
  PACKET3_MAP_QUEUES_DOORBELL_OFFSET(ring->doorbell_index)
```

El rango está **dos saltos más allá**, y ese es el trabajo del resolutor.

## 1 · La cadena que hay que recorrer

```text
  gfx_v8_0.c:1910        adev->gfx.mec.num_pipe_per_mec = 4;
  amdgpu_gfx.c:65         *pipe = (bit / adev->gfx.mec.num_queue_per_pipe)
                                % adev->gfx.mec.num_pipe_per_mec;
  amdgpu_gfx.c:296        ring->pipe = pipe;
  gfx_v8_0.c:4348         PACKET3_MAP_QUEUES_PIPE(ring->pipe)

  =>  pipe  en  [0, 3]      =>  hacen falta 2 bits
```

Tres detalles que estorbaron y que son la parte interessante:

| Detalle | Qué pasó |
|---|---|
| `num_pipe_per_mec = 4` es una **asignación**, no un `#define` | Con solo defines el resolutor no encontraba el módulo y devolvía `None` |
| La asignación está **partida en dos líneas** | `*pipe = (bit / …)` sigue en la línea siguiente, y emparejando línea a línea no se ve |
| El `PIPE` de `gfx_v8_0.c` es un `int` **desnudo**, no `ring->pipe` | El resolutor sólo aceptaba `X->Y` |

## 2 · Las dos vías, y por qué son independientes

```text
  VÍA A   el hueco hasta el campo SIGUIENTE          campos_pm4
          PIPE << 29,  siguiente ME << 31   ->   2 bits

  VÍA B   los valores que el driver le PASA          ancho_pm4
          pipe en [0, 3]                    ->   2 bits
```

No se conocen entre sí: la A lee **desplazamientos**, la B lee **valores**. Que coincidan
es un dato, no una redundancia.

## 3 · El resultado

```text
$ ancho_pm4.py --contradicciones

  DOS VIAS  6 campos comparables
  NINGUNA CONTRADICCION.  Donde las dos vias pueden compararse,  coinciden.
```

Y el detalle, que es donde está el contenido:

```text
  CAMPO                        vía B (cota)  vía A (hueco)
  MAP_QUEUES_PIPE                      2            2      OK
  MAP_QUEUES_QUEUE_SEL                 1            4      (cota floja)
  MAP_QUEUES_ENGINE_SEL                1            3      (cota floja)
  MAP_QUEUES_QUEUE_TYPE                1            3      (cota floja)
  MAP_QUEUES_ALLOC_FORMAT              1            2      (cota floja)
  QUERY_STATUS_INTERRUPT_SEL           1            2      (cota floja)
```

La distinción que hay que hacer al leerlo:

```text
PIPE         la vía B FIJA el ancho en 2:  el rango [0,3] no cabe en 1 bit.
             Y la vía A da 2.  CONVERGEN.

los otros 5  la vía B da 1:  el driver solo pasa 0 o 1 en este árbol.  Una cota
             de 1 la satisface CUALQUIER ancho >= 1,  asi que corrobora pero no
             fija.  No es que las vias discrepen:  es que una de ellas casi no
             dice nada.
```

Y el instrumento sólo marca contradicción cuando `necesita > deducido`, que es la
condición correcta: una cota floja nunca contradice.

## 4 · Por qué esto cierra la corrección de `1200`/`1201`

`1200` había **corregido** a `1199`: su tabla decía `DOORBELL_OFFSET -> [25:2] y hueco`
y su conclusión `[3:2]`, y la que se sostenía era que la anchura no se deduce. Ese
corrección era correcto y dejaba el número **sin respaldo**.

Ahora:

```text
  PIPE   vía A (hueco) 2 bits  ==  vía B (valores) 2 bits
```

y `PIPE` es precisamente el campo que `1200` identificó como el del riesgo de solape, porque
`PIPE << 29` con 3 bits alcanzaría el bit 31 de `ME`. La conclusión de `1199` —que el
ancho de `PIPE` es 2— queda con **dos supports independientes dentro del árbol**, que es
justo lo que se le pedía.

`DOORBELL_OFFSET` sigue sin deducirse por ninguna de las dos vías: el driver lo llama con
`ring->doorbell_index`, y su rango depende de `adev->doorbell_index` en tiempo de ejecución.
**Ahí el hallazgo 1201 sigue en pie tal como está.**

## 5 · La cuarta y la quinta vez que un regex devuelve cero en silencio

`campos_pm4` lleva un guard que obliga a cada regex del fichero a encontrar algo, escrito
en `1201`. Ese guard **no se copió** a `ancho_pm4.py`, y el fallo se repitió entero:

```text
  RE_ASSIGN_INT = r"^\s*[A-Za-z_][\w.\->\s]*?\b([A-Za-z_]\w*)\s*=\s*(\d+);"
```

sin `re.M`. Con `re.match` sobre **una** línea funcionaba, y con `finditer` sobre el
fichero entero devolvía `[]`. El síntoma fue "0 enteros leídos".

> Un guard en un fichero no es una regla del proyecto: es una buena costumbre que se
> pierde en el fichero siguiente.

Ahora el guard está en los dos ficheros. Y hay dos fallos más de esta sesión que son del
mismo género:

```text
  CUANTIFICADORES ANIDADOS     RE_ASIGN_VAR llevaba `(?:[A-Za-z_]\w*(?:\s*->|…)?)*`
                               y el instrumento SE COLGABA:  no terminaba en 900 s.
                               El sintoma no es un error,  es una ausencia de
                               salida,  que es el peor modo de fallar porque
                               parece que workings.
                               La izquierda del `=`  se captura como texto
                               acotado y el ultimo identificador se saca en
                               Python,  sin regex.

DOS ESPACIOS DE NOMBRES        Al mezclar los `#define` con las asignaciones
                               `X = 4;`,  un `pipe` desnudo empezo a
                               resolverse como literal 0  —porque en algun sitio
                               hay un `pipe = 0`—  y el resolutor decia "PIPE
                               vale 0"  cuando lo que se sabe es "0..3".
                               Eso FABRICA una cota,  y la cota es
                               exactamente lo que sirve para detectar
                               contradicciones.
                               Un `#define`  y una variable de runtime no son
                               la misma cosa:  hay dos tablas y cada uso va a la
                               suya.
```

## 6 · Procedimiento

```text
nuevo     tools/ancho_pm4.py,  38 vectores rc=0
          valor_de()        literal y macro,  con guarda contra constante ciclica
          rango_de_una_asignacion()   solo `(a / b) % MOD`;  cualquier otra
                                      forma devuelve None con su texto
          enteros_asignados()   los `X = 4;`,  que NO son `#define`
          asignaciones_de_variables()   multilinea,  con linea por desplazamiento
          anchos_deducidos()   via A,  importando campos_pm4
          contradicciones()    compara las dos vias
          --contradicciones, --campo, --solo-deducidos

MEDIDO    255 campos PACKET3_* vistos en el driver
          34 con cota deducida;  221 sin deducir,  con el texto donde se paro
          6 comparables entre las dos vias;  0 contradicciones
          PIPE:  2 bits por las dos vias

corregido  RE_ASSIGN_INT sin re.M:  devolvia cero  (el guard no se habia copiado)
corregido  cuantificadores anidados:  el instrumento se colgaba
corregido  `#define` y `X = 4;`  mezclados:  fabricaba la cota de PIPE
NO HECHO  DOORBELL_OFFSET y los otros 14 grupos:  el rango depende de estado de
          ejecucion,  y sin hardware no se cierra
runtime   RUNTIME=NOT_RUN.  Ni la RX550 ni la Intel.  i915 y amdgpu intactos
```