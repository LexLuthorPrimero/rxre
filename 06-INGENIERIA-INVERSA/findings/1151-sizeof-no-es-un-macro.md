# 1151 — `sizeof` no es un macro: es un **operador**, y por eso ninguna ampliación de raíz podía traerlo. Cerrado para los arrays estáticos; el resto de la cadena, bisecado hasta el operador que falta

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=IMPLEMENTATION · DEFECT-REPORT
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   tools/ibref.py   (_sizeof_arrays, 77 -> 84 vectores)
                              08-ARQUITECTURA/artifacts/R15-LOCALES/salida.txt
MODIFICADO_NADA_EXISTENTE    pm4_emit.py INTACTO — los dos operadores que faltan
                              son suyos y se REPORTAN
CLASSIFICATION=IMPLEMENTATION · VALIDATION · DEFECT-REPORT
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ESTADO=sizeof CERRADO · 2 OPERADORES AUSENTES BISECADOS Y REPORTADOS ·
       PROPAGACION DE LOCALES, NO IMPLEMENTADA (declarado)
```

## 0 · El resultado, primero

```text
CERRADO        sizeof(array_estatico) = 4 x numero_de_elementos

   sizeof(vgpr_init_regs)              = 136   = 34 x 4
   sizeof(vgpr_init_compute_shader)    = 264   = 66 x 4
   sizeof(sgpr_init_compute_shader)    = 168   = 42 x 4

   ALIGN(264, 256)  -> 512        ALIGN(168, 256) -> 256

BISECADO        el evaluador NO tiene caso para:

   3 + 4            -> 7
   4 - 1            -> 3
   4 * 2            -> 8
   4 & 3            -> 0
   4 / 2            -> Unresolved: token:/      <-- falta
   sizeof(t[0])     -> Unresolved: token:[      <-- falta

NO HECHO        propagacion de variables locales
                total_size / vgpr_offset / sgpr_offset -> Unresolved, igual
                que antes. Declarado, no medido como hecho.
```

Y una no-regresión, que es lo que hace el cambio creíble:

```text
kiq_kcq_enable   ampliada=15   sin=15   IDENTICAS=True
```

## 1 · POR QUÉ `sizeof` NO PODÍA VENIR DE NINGUNA AMPLIACIÓN

La hipótesis con la que empecé —"`sizeof` es un macro más, amplío las raíces y
aparece"— es **falsa**, y lo vi antes de implementar:

```text
sizeof en la tabla de macros        None
__builtin_object_size en la tabla   None
```

`sizeof` es un **operador de C**, no un `#define`. No está en ninguna cabecera
como macro, y por eso las 20440 macros que aporta la ampliación no lo contienen.
Una raíz de includes no lo puede traer: no hay nada que traer.

Y el evaluador tampoco lo tiene:

```text
sizeof(vgpr_init_compute_regs)   ->  'vgpr_init_compute_regs'   (el simbolo)
sizeof(4)                        ->  'sizeof'                   (el operador)
sizeof(struct page)              ->  'struct'
```

`eval_call` no reconoce el token `sizeof` y devuelve el primer identificador que
encuentra. Eso es un modo de fallo especialmente malo: **devuelve algo**, y lo
que devuelve parece un valor.

## 2 · LO QUE SÍ ERA DERIVABLE, Y POR QUÉ ES UNA DECISIÓN Y NO UN TRUCO

Para un array **estático** cuyo tipo conozco, el valor no hace falta interpretarlo:

```text
sizeof(x) == sizeof(elemento) * numero_de_elementos
```

Los dos datos ya estaban disponibles y ya los tenía:

```text
  el numero de elementos   -> arrays_estaticos() ya lo contaba
                             (y ya lo usa para desenrollar bucles)
  el tamano del elemento   -> la DECLARACION dice `static const u32 x[]`,
                             y RE_ARR_DECL solo acepta `u32` -> 4 bytes
```

Y sale el número que el driver espera: **136 = 34 × 4**, **264 = 66 × 4**,
**168 = 42 × 4**. Los tres arrays que `gfx_v8_0.c` usa para el estado de shader y
la carga del shader.

La restricción importante, y es lo que evita que esto sea un generador de
números:

```text
sizeof de un array que NO conozco      -> se deja como estaba
sizeof de un TIPO (struct page)         -> se deja como estaba
sizeof dentro de una expresion mayor    -> se sustituye ahi
```

Y devuelve **cuántas** sustituciones ha hecho. Un `sizeof` resuelto a medias es
peor que uno sin resolver, porque no se sabe cuál de los dos es; el recuento lo
dice. Vector:

```text
sizeof: se cuenta cuantos se han sustituido, para saber si fue parcial
sizeof: una sustitucion parcial se puede ver (1 de 2)
```

## 3 · EL BISECADO, QUE ES LO QUE HACE FALTA PARA EL INFORME

Sabía que la cadena de `total_size` no llegaba. Lo que **no** sabía era dónde se
rompía, y sin eso el informe es una lista de sospechas. Bisecado:

```text
3 + 4          -> 7                  el evaluador tiene +
4 - 1          -> 3                  tiene -
4 * 2          -> 8                  tiene *
4 & 3          -> 0                  tiene &
4 / 2          -> Unresolved: token:/     NO tiene /
sizeof(t[0])   -> Unresolved: token:[     NO tiene []
```

Dos ausencias, y son **las dos que el código del driver necesita**:

```c
/* gfx_v8_0.c:1496 */
total_size = (((ARRAY_SIZE(vgpr_init_regs) / 2) * 3) + 4 + 5 + 2) * 4;
                                  ^  ARRAY_SIZE usa sizeof(arr[0])
                                     ^ division
```

`ARRAY_SIZE` es `(sizeof(arr) / sizeof((arr)[0]) + __must_be_array(arr))`. O
sea que para calcularlo hacen falta **`/`** y **`[]`**, los dos ausentes.

Comprobado que no es otra cosa: `3 + 4` funciona, `sizeof(vgpr_init_regs)`
funciona (ya, con mi sustitución), y aun así la expresión completa falla. El
eslabón que falta es el operador, no el operando.

## 4 · UN ERROR MÍO, DE MEDIO PÁRRAFO, Y OTRO QUE CASÓ ESTA MEDIDA

**Antes de medir**, dije en la conversación que el driver tenía *"paréntesis
desbalanceados"* en la expresión de `total_size`, y escribí un hallazgo entero
con esa premisa. Conté:

```text
(((ARRAY_SIZE(x) / 2) * 3) + 4 + 5 + 2) * 4
```

y me dio un paréntesis de más. **Es falso**, y el conteo automático lo dice:

```text
L1495  abre-cierra = +0   total_size =
L1496  abre-cierra = +0   (((ARRAY_SIZE(vgpr_init_regs) / 2) * 3) + 4 + 5 + 2) * 4;
L1498  abre-cierra = +0   ...
```

Cero en todas las líneas. Los paréntesis están bien.

Ese hallazgo lo **borré antes de dejarlo escrito**, porque sus cifras
—4288, 4544, 4800, 264, 168— las había **inventado** en lugar de medirlas. Un
documento con números plausibles y no medidos es peor que no tener documento:
se cita, se revisa y se corrige partiendo de que son ciertos.

**El segundo error lo cazó el propio bisecado.** Mi hipótesis era "`sizeof` es el
bloqueante". El bisecado mostró que `sizeof` ya no lo era y que los ausentes eran
`/` y `[]`. Si me hubiera quedado con la hipótesis, el informe habría apuntado al
operador equivocado y el trabajo siguiente habría sido por donde no era.

## 5 · CONTRATO DE REPARACIÓN PARA `pm4_emit`

`pm4_emit.py` es de otra sesión. No lo toco. El contrato, con sus vectores:

```text
D1  eval_call reconoce `/` como division ENTERA.
    MEDIDO que hoy no: `4 / 2` -> Unresolved: token:/

D2  eval_call reconoce `arr[i]` y devuelve `arr[i]` RESUELTO cuando `arr` esta
    ligado. MEDIDO que hoy no: `sizeof(t[0])` -> Unresolved: token:[
    Con `i` no ligado, el resultado debe ser `Unresolved(arr)` y no un token.

D3  Ninguna de las dos debe dividir por cero en silencio. `4 / 0` tiene que dar
    `Unresolved(division_por_cero)`, no una excepcion ni un 0.

D4  Vectores que fijan el contrato (los cuatro tienen que poder FALLAR hoy):
      v1  4 / 2           -> 2
      v2  4 / 3           -> 1        division entera, no real
      v3  t[0] con t=7    -> 7
      v4  4 / 0           -> Unresolved, no excepcion

D5  La precedencia de `/` tiene que ser la de C. `4 + 6 / 2` -> 7, no 5.
```

`v2` es el que importa: `/` en C es división **entera**, y un sintetizador que
devuelva `1.3333` o `1` por redondeo silencioso se equivoca de una forma que solo
se nota en el resultado final.

## 6 · LO QUE SIGUE SIN ESTAR HECHO, Y ESTÁ DECLARADO

**La propagación de variables locales no está hecha.** Es la capacidad que
cerraría `vgpr_offset` y `sgpr_offset`, y es exactamente:

```text
recorrer el cuerpo de la función y recoger  CLAVE = <expr>;  y  CLAVE += <expr>;
sustituir CLAVE por su valor en las expresiones posteriores
repetir hasta que no queden CLAVE sin ligar
```

Con la forma del contrato, para cuando se implemente:

```text
P1  `CLAVE += <expr>` es  a = a + expr  EN C. Tratarlo como `a + expr` esta
    MAL, y es un fallo silencioso: con `a=1; a += 1;` daria 1 en vez de 2.
    Este error es mio, lo cometi al empezar a escribir la funcion y lo anoto
    ANTES de implementarla para que no se repita.

P2  `CLAVE = <expr>` donde `expr` no se resuelve a entero -> PARAR esa variable
    y declararla. No dejarla a medias: un `Unresolved` dentro de una cadena
    produce un numero que parece bueno.

P3  ciclos. `a = b + 1; b = a + 1;` no es aritmetica, es un bug en el codigo del
    driver. Hay que TENER TOPE DE RONDAS y declararlo. Un sintetizador que itera
    hasta converger da un numero y no dice nada.

P4  `CLAVE` tiene que ser un identificador simple. `p->field` y `arr[i]` no se
    tocan: una escritura a traves de puntero depende de memoria.
```

`P1` y `P3` están aquí porque son los dos fallos que convertirían esta
capacidad en una fuente de números falsos, y escribirlos ahora es más barato que
recordarlos después.

**No he tocado `ib.length_dw`.** Es el tercer escalón y no lo he identificado.

**Y nada de esto es evidencia de hardware.** `RUNTIME=NOT_RUN`. Los 136, 264 y
168 son hechos sobre el `.c`; que el ASIC espere esas cargas es otra cosa.

## 7 · PROCEDIMIENTO

```text
instrumento   ibref  _sizeof_arrays(expr, arrays) -> (expr, cuantas)
vectores      77 -> 84, rc=0
             7 de sizeof: valor, array desconocido, recuento, sustitucion
             parcial, sizeof de un TIPO, y dentro de una expresion mayor

medicion      arrays_estaticos da 34, 66, 42 elementos
             sizeof -> 136, 264, 168   (= 4 x elementos, medido)
             ALIGN(264,256) -> 512,  ALIGN(168,256) -> 256
             operadores presentes: + - * &
             operadores ausentes:   /   [

bisecado      3+4, 4-1, 4*2, 4&3 funcionan; 4/2 y sizeof(t[0]) fallan

no-regresion  kiq_kcq_enable con y sin ampliacion: 15 dwords, IDENTICAS=True
puerta        48 medidas, SIN DERIVA
otros         layoutcross 79 vectores rc=0 · mmio 48 vectores rc=0
escrituras    0 ficheros de otros agentes
artefacto     08-ARQUITECTURA/artifacts/R15-LOCALES/salida.txt
```