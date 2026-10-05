# 1152 — La cadena de `ARRAY_SIZE`, bisecada de punta a punta: **cuatro eslabones, uno cerrado por mí y tres con nombre y prueba**. El cuarto no es sintaxis: es una aserción de compilación que en un sintetizador debe valer 0

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=DEFECT-REPORT · SEMANTIC-CLOSURE
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   08-ARQUITECTURA/artifacts/R15-LOCALES/salida.txt
                              (cadena completa, eslabon por eslabon)
MODIFICADO_NADA_EXISTENTE    pm4_emit.py INTACTO
CLASSIFICATION=DEFECT-REPORT · SEMANTIC-CLOSURE · SCOPE-BOUNDING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ESTADO=FRONTERA DE `total_size` CERRADA COMO FRONTERA: 4 ESLABONES NOMBRADOS
```

## 0 · El resultado, primero

La expresión del driver es:

```c
total_size = (((ARRAY_SIZE(vgpr_init_regs) / 2) * 3) + 4 + 5 + 2) * 4;
```

y `ARRAY_SIZE` es `(sizeof(arr) / sizeof((arr)[0]) + __must_be_array(arr))`.
Medido eslabón por eslabón:

```text
1  sizeof(x)                 -> 136                     CERRADO en 1151
2  sizeof((arr)[0])          -> Unresolved: token:[    falta []
3  /                         -> Unresolved: token:/    falta /
4  __must_be_array(arr)      -> sin resolver            NO EXISTE la regla
```

> **ACTUALIZADO POR `1176`.** Los eslabones 3 y 4 **quedan sin uso**:
> `ARRAY_SIZE` se sustituye por el conteo que ya se hacía para desenrollar bucles,
> y la división se pliega entre literales. La cadena completa
> `(((ARRAY_SIZE(x) / 2) * 3) + 4 + 5 + 2) * 4` resuelve hoy a **248**, medido.
> El contrato `D1` y `D6` de abajo queda **sin объекto**; `D2` y `D3` siguen en
> pie para cualquier otro uso de `[]` y `/`. Se conserva el texto original porque
> el hallazgo debe leerse como lo que era: una medición de un momento.

**Eslabón 4 es el que cambia el encargo.** `__must_be_array` es:

```c
#define __must_be_array(a)   __BUILD_BUG_ON_ZERO_MSG(!__is_array(a), "must be array")
```

Es una **aserción de compilación**: existe para fallar al compilar si `a` no es
un array. En un sintetizador que evalúa, su valor correcto es **0, en silencio**.

Eso no es un operador que falte ni una macro que no se encuentre. Es una regla
**semántica** que no está escrita en ninguna parte: qué hacer con una aserción
cuando no hay compilación. No hay fichero donde arreglarlo, y por eso el
contrato no es de reparación sino de **decisión**.

## 1 · POR QUÍA ESTO CIERRA UNA FRONTERA Y NO LA ABRE

Tres hallazgos seguidos nombraron la misma cosa sin nombrar el último eslabón:

```text
1140 §4   "ALIGN resoluble -> falta propagar total_size"
1141 §8   "el segundo es propagar total_size... NO SE: no se cual es el siguiente"
1151 §6   "No he tocado ib.length_dw. Es el tercer escalon y no lo he identificado"
```

Ahora sí está, y medido:

```text
sizeof     -> cerrado
[ ]        -> falta en pm4_emit.eval_call      (contrato D2 de 1151)
/          -> falta en pm4_emit.eval_call      (contrato D1 de 1151)
__must_be_array -> falta una REGLA, no codigo   (nuevo, D6)
total_size     -> propagacion de locales, NO implementada (contrato P1..P4)
```

Cinco cosas, cuatro con dueño y una con forma. Antes había un "no sé cuál es el
siguiente" y ahora hay una lista. **Eso es lo que es cerrar una frontera**: no
resolverla, sino saber exactamente qué falta y por qué.

## 2 · EL HALLAZGO DE FONDO: UNA ASERCIÓN NO ES UNA OPERACIÓN

Que `__must_be_array` "no esté en la tabla de macros" es un detalle. Lo que
importa es que **aunque estuviera**, un sintetizador la habría tratado como una
función más y habría intentado darle un valor.

Y no tiene un valor propio: tiene un valor **para el compilador** (que va a
fallar) y un valor **para el que evalúa** (que es 0). Son dos consumidores con
respuestas distintas de la misma expresión.

La regla general, y que es más ancha que `__must_be_array`:

```text
Una asercion de compilacion tiene dos lecturas:
   - la lee el COMPILADOR  -> si se cumple mal, error; si se cumple bien, nada
   - la lee un SINTETIZADOR -> siempre 0, porque ya se asume que el codigo
                              compila, y el codigo que llega aqui ya ha
                              compilado en el arbol de otra sesion

Un sintetizador que devuelve `Unresolved(__must_be_array(...))` por prudencia
esta peor que uno que devuelve 0: pierde la expresion entera.
Un sintetizador que devuelve el valor del mensaje esta peor que los dos.
```

Y el corolario, que es la regla general que voy a proponer:

> **Un sintetizador de código que ya compila debe tratar toda aserción como 0.
> La prueba de que el código compila es que está en el árbol.** No tiene que
> comprobarlo, y si lo comprueba está haciendo trabajo de compilador.

Eso no es un parche: es una **decisión de alcance**, y por eso va al proprietario
del instrumento y no a un fichero mío.

## 3 · CONTRATO, COMPLETADO

`1151 §5` dejó `D1..D5` para `pm4_emit`. Se añade:

```text
D6  eval_call reconoce las aserciones de compilacion del kernel y devuelve 0.
    Ahora mismo no hay ninguna, y no es un operador que falte.

    Vectores, y todos tienen que poder fallar hoy:
      a1  __must_be_array(t)          -> 0        con t un array conocido
      a2  __must_be_array(7)          -> 0        NO da error: el codigo
                                                       ya compilo en el arbol
      a3  __BUILD_BUG_ON_ZERO_MSG(0, "x")   -> 0
      a4  __BUILD_BUG_ON_ZERO_MSG(1, "x")   -> Unresolved(BUILD_BUG), NO error
      a5  __must_be_array(x) sin x ligado   -> Unresolved(x)

    a4 es el que separa "aserción" de "cualquier cosa que devuelva 0":
    si el mensaje es distinto de 0, hay algo que NO se puede resolver y hay que
    decirlo. Si es 0, es una aserción y se cumple.
```

`a2` es el vector que importa más, porque es el que **impide** que la regla se
aplique de más: `__must_be_array(7)` no da error aunque `7` no sea un array,
porque el código que lo contiene ya se compiló en otra parte del árbol. Un
sintetizador que comprobara la aserción estaría reimplementando `__is_array`, y
eso es trabajo de compilador.

## 4 · MEDICIÓN COMPLETA, PARA QUE NO HAYA QUE REPETIRLA

```text
$ ibref --func gfx_v8_0_do_edc_gpr_workarounds --json

  vgpr_offset  -> Unresolved   (no implementado: propagacion de locales)
  sgpr_offset  -> Unresolved
  total_size   -> Unresolved

  dwords escritos 294, completos 285, incompletos 9
  bucles NO reconocidos 0
```

Y lo que sí funciona, para que conste:

```text
sizeof(vgpr_init_regs)             -> 136     = 34 x 4
sizeof(vgpr_init_compute_shader)   -> 264     = 66 x 4
sizeof(sgpr_init_compute_shader)   -> 168     = 42 x 4
ALIGN(264,256) -> 512    ALIGN(168,256) -> 256
```

Lo que la síntesis produce hoy no depende de ninguna de estas cinco cosas: la IB
de 294 dwords se genera sin `total_size`, porque los desplazamientos de carga de
shader son **posicionales** y van como texto ligado, no resueltos. Es decir: el
hueco está declarado y localizado, no está contaminando nada.

Eso es lo que permite que la frontera sea segura mientras está abierta: **el
eslabón que falta no toca ningún dato que hoy se use.**

## 5 · UNA COSA QUE NO ESTOY AFIRMANDO

**No sé si `ARRAY_SIZE` debería resolverse en absoluto.** Es tentador decir "hay
que arreglar `/`, `[]` y las aserciones", pero hay una razón para no decirlo:
`ARRAY_SIZE` sobre un array **declarado** tiene un valor trivial que ya conozco
por otra vía — `len(arrays_estaticos())`.

La pregunta correcta no es "¿cómo resuelvo `ARRAY_SIZE`?", sino:

```text
¿debería `ibref` entender `ARRAY_SIZE` en general,
 o sustituirlo por el conteo que ya sabe hacer,
 o dejar que quede sin resolver y que la IB lo declare?
```

Las tres son defendibles y tienen costes distintos:

```text
  entenderlo en general   -> mas faithful, y necesita D1, D2, D6
  sustituirlo             -> mas simple, y es un caso mas de "el dato ya lo tengo"
  dejarlo sin resolver    -> honesto, y 5 dwords mas INCOMPLETO en la salida
```

No elijo. Es una decisión que le toca a quien fije el contrato del sintetizador,
y lo que este hallazgo hace es **poner las tres sobre la mesa con su coste** en
lugar de abrir la brecha por la opción cara sin decirlo.

## 6 · PROCEDIMIENTO

```text
medicion    via REAL (sintetizar), no llamada directa a eval_call
            sizeof(vgpr_init_regs)            -> 136
            sizeof(vgpr_init_regs[0])         -> Unresolved: token:[
            ARRAY_SIZE(vgpr_init_regs)        -> Unresolved: <simbolo>
            ARRAY_SIZE(vgpr_init_regs) / 2    -> Unresolved: token:/
            (4 repeticiones de cada uno en sin_resuelto: no es un fallo, es
             el evaluador reintentando; el dato es el mismo)

inspeccion  ARRAY_SIZE      = (sizeof(arr) / sizeof((arr)[0]) + __must_be_array(arr))
            __must_be_array = __BUILD_BUG_ON_ZERO_MSG(!__is_array(a), "must be array")
            -> los dos aban como buscar la macro; uno es sintaxis y el otro
               es una asercion

estado      211 vectores (layoutcross 79 + ibref 84 + mmio 48), rc=0
            48 medidas de verif, SIN DERIVA
            19 documentos con doclint, 19 errores, los 19 de 1136 ya declarados
escrituras  0 ficheros de otros agentes
```

## 7 · LO QUE NO ESTÁ HECHO

**Nada de `D1..D6`.** `pm4_emit.py` es de otra sesión y este documento es un
informe, no una modificación.

**Nada de `P1..P4`.** La propagación de locales está especificada y no
implementada. Los contratos están escritos para que la implementación no tenga
que decidir nada sobre la marcha, que es la razón de que un contrato sirva.

**No he comprobado si `__BUILD_BUG_ON_ZERO_MSG` está siquiera en la tabla de
macros.** No hacía falta para nombrar la regla, pero sí para escribir `a3` y `a4`
como vectores ejecutables y no como especificación. Queda como `NOT_DETERMINED`.

**Y `RUNTIME=NOT_RUN`.** Todo lo medido es sobre ficheros. `136 = 34 × 4` es un
hecho sobre el `.c`, no sobre el ASIC.