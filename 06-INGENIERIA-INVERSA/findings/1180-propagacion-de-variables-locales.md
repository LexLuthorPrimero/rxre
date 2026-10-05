# 1180 — Propagación de variables locales: `vgpr_offset = 768`, `sgpr_offset = 1280`, y **el hueco entre las dos cargas de shader es de 62 dwords, que es exactamente lo que dice la fórmula del driver**

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=IMPLEMENTATION · SEMANTIC-CLOSURE
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   tools/ibref.py    (propagar_locales, +12 vectores,
                              93 -> 105)
                              tools/verif.py    (2 medidas, 48 -> 50 declaradas)
                              08-ARQUITECTURA/artifacts/R17-LOCALES/
MODIFICADO_NADA_EXISTENTE    pm4_codec.py, pm4_emit.py, gfx_v8_0.c INTACTOS
CLASSIFICATION=IMPLEMENTATION · SEMANTIC-CLOSURE · VALIDATION
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ESTADO=ULTIMA FRONTERA DE LA CADENA CERRADA · CONTRATO P1-P4 EJECUTADO
```

## 0 · El resultado, primero

```text
LOCALES RESUELTAS
   total_size    = 1448
   vgpr_offset   =  768
   sgpr_offset   = 1280
   paradas: 9  ->  i, r, tmp     (las que NO son aritmetica)

COMPROBACION INDEPENDIENTE, y esto es lo que importa:

   vgpr_offset/4 = 768/4  = 192  ->  66 escrituras en ptr[192..257]
   sgpr_offset/4 = 1280/4 = 320  ->  42 escrituras en ptr[320..361]

   hueco: ptr[258..319] = 62 dwords

   y la formula del driver para ese hueco:
   ALIGN(sizeof(vgpr_init_compute_shader), 256)/4 - 66 = 128 - 66 = 62

   -> 62 = 62
```

El hueco **no estaba medido**: salía de restar dos números que el sintetizador
nunca había tenido. Y sale igual que la fórmula que el driver usa para calcular
la separación, por una vía completamente distinta.

## 1 · MI PREDICCIÓN, Y QUE ERA FALSA

`1153 §6` escribió, sobre la aritmética ya parcialmente resuelta:

```text
vgpr_offset  768
sgpr_offset  768 + ALIGN(264,256)/4 = 768 + 128 = 896
```

Medido: **`sgpr_offset = 1280`**, no 896.

El error fue mío y de un tipo concreto: **mezclé unidades a mitad de la cuenta**.
`total_size` y `sgpr_offset` están en **bytes**; solo al indexar `ib.ptr[...]` se
divide por 4. Yo dividí antes de sumar:

```text
lo que escribi      768 + 512/4 = 896        <-- 512/4, con error mio
lo que hace C        768 + 512    = 1280      <-- y despues /4 al indexar
```

Y ese mismo párrafo decía, dos líneas más abajo:

> *"adivinar el resultado final antes de ejecutarlo es exactamente lo que este
> proyecto prohíbe. Queda como `NOT_DETERMINED` hasta que `P1..P4` se implemente"*.

La prohibición estaba escrita y la incumplí en la línea siguiente. La cifra no
era una hipótesis: era una cuenta hecha a mano y presentada con el formato de
un dato. Un número escrito a mano con decimales de producción es un número que
nadie va a volver a mirar.

## 2 · EL CONTRATO, EJECUTADO

`1151 §6` escribió `P1..P4` **antes** de implementar. Eso es lo que hizo que
esta sección sea una lista de hechos y no una de sorpresas.

```text
P1  `CLAVE += <expr>` es `CLAVE = CLAVE + expr` EN C
    VECTOR  a = 1; a += 1;  ->  2
    VECTOR  a = 10; a += 5; a += 3;  ->  18

P2  si la expresion no resuelve a entero, la variable QUEDA SIN LIGAR y se DECLARA
    VECTOR  tmp = RREG32(ALGO);  ->  {} con parada que nombra RREG32

P3  CICLOS: tope de rondas y se declara
    VECTOR  a = b + 1; b = a + 1;  ->  {} y DOS paradas con motivo

P4  solo identificadores simples
    VECTOR  p->field = 1; arr[i] = 2; c = 3;  ->  ni `field` ni nada, c = 3
```

`P1` estaba escrito porque es el error más tentador, y casi lo cometo: al
empezar a escribir la función lo implementé como `a + expr`, que da el mismo
número. Lo dice el propio contrato, y por eso el vector existe.

### 2a · Tres cosas más que el contrato no prevía

```text
UNA ASIGNACION PARTIDA EN DOS LINEAS
    b = a +
            4;
  MEDIDO: con un regex anclado por linea no se recoge NINGUNA. El driver
  escribe `total_size =` y la expresion en la linea siguiente, y son las TRES
  sumas de `total_size`.

UNA REASIGNACION SECUENCIAL NO ES UN CICLO
    b = 2; a = b * 3; b = a + 1;
  Mi primer vector lo llamaba ciclo y no lo era: gana la ULTIMA, b = 7. El
  vector de ciclo de verdad es `a = b + 1; b = a + 1;` sin valor inicial.

UNA ASIGNACION DENTRO DE UN `if` NO SE PROPAGA
    a = 1; if (x) a = 2;   ->  a = 1
  No hay flujo de control en el sintetizador, asi que la que esta DENTRO de
  un condicional no se toca. Es lo unico defendible sin un motor de flujo, y
  por eso hay vector: para que quede dicho y no sea un descuido.
```

## 3 · DOS BUGS DEL JUNTADOR DE SENTENCIAS

**El primero: acumulaba el prologo.**

```c
void f(void) {      <-- NO lleva `;`
    a = 1;
```

La primera versión juntaba líneas hasta ver un `;`, así que el prólogo se
pegaba a la primera asignación y **las tres siguientes no se recogían**.
Cero asignaciones recogidas, cero resueltas, y el contrato declarando 15 paradas
como si hubiera intentado quince cosas.

Eso es un fallo con una propiedad especialmente mala: **la salida parece
trabajo y no hay trabajo**. Un instrumento que declara paradas sin decir
"no he recogido ninguna asignación" es indistinguible de uno que lo ha
intentado quince veces.

La regla correcta cabe en una línea: en C una sentencia termina en `;`. Se quita
el prólogo y se parte por `;`.

**El segundo: `$` es fin de cadena y `.` no cruza el salto de línea.**

```python
re.match(r"^([A-Za-z_]\w*)\s*(\+?=)\s*(.+)$", sent)
```

Con `sent` = `"b = a +\n4"`, `(.+)$` no casa. Los espacios se normalizan antes
de casar y las asignaciones partidas se recogen. Es el tipo de bug que solo
aparece si un vector tiene un caso de dos líneas, y el caso de dos líneas es
literalmente la primera línea del código que había que sintetizar.

## 4 · LO QUE SIGUE SIN RESOLVERSE, Y SON LAS 9 PARADAS

```text
   i    el indice de bucle
   r    el resultado de amdgpu_ib_get / amdgpu_ib_schedule
   tmp  RREG32(...) y REG_SET_FIELD(...)
```

Ninguna de las tres es aritmética:

```text
i    un indice de bucle se propaga por el desenrollado, no por la propagacion.
     Meterlo aqui seria duplicar capacidad. Y duplicar capacidad es como se
     rompen las cosas: dos caminos que resuelven lo mismo y solo uno se
     prueba cuando el otro cambia.

r    una llamada a funcion. Su valor depende de la ejecucion. La propagacion
     NO puede inventarlo, y no lo hace: lo declara.

tmp  RREG32 es una LECTURA de registro de hardware. Su valor no esta en el
     fuente, esta en el silicio. Declararlo es lo unico correcto, y es tambien
     lo que impide que un sintetizadorpresentara lecturas de hardware como
     numeros de IB.
```

> Las paradas no son fracasos del instrumento. Son **la frontera entre lo que se
> puede derivar del código y lo que solo existe cuando corre**, y un
> sintetizador que no las declara está mintiendo sobre su propio alcance.

## 5 · POR QUÉ `106` NO ES EL ÚNICO PUNTO, Y NO SE PUEDE COMPROBAR AQUÍ

`total_size = 1448` es el valor **final** de la variable, después de las nueve
sentencias. La IB usa `vgpr_offset` y `sgpr_offset`, que se fijan antes. Pero el
prologo del fragmento tiene esto:

```c
ib.length_dw = 0;
```

después de la carga de shader, y antes de los bucles de `SET_SH_REG`. El
sintetizador **no lleva la cuenta de `length_dw`**, porque solo lo usa para
saber el índice del puntero, no para acumular un total.

Consecuencia: la IB que sale tiene 294 dwords **sin segmentar**, y el `length_dw`
que el driver calcularía no está en la salida. Es un `NOT_DETERMINED` declarado:
puedo decir que no lo calculo, no que no se pueda calcular.

## 6 · PROCEDIMIENTO

```text
instrumento   ibref  propagar_locales(lineas, ini, fin, ...)
vectores      93 -> 105, rc=0
             12 nuevos: P1 x3, P3 x3 (ciclo real, reasignacion, motivo),
                        lectura de registro, cadena de tres, dos lineas,
                        p->field, comentario, if

medicion      total_size 1448 · vgpr_offset 768 · sgpr_offset 1280
             66 escrituras en ptr[192..257]
             42 escrituras en ptr[320..361]
             hueco ptr[258..319] = 62 dwords
             formula del driver: ALIGN(264,256)/4 - 66 = 128 - 66 = 62

             el hueco coincide: la medicion dinamica y la formula estatica
             dan el mismo numero por vias distintas

no-regresion  kiq_kcq_enable: 15 dwords IDENTICOS antes y despues
              shader-init: 294 dwords, 285 completos, 9 incompletos (igual)
puerta        48 -> 50 declaradas, SIN DERIVA
              ibref.locales y ibref.locales_paradas perturbadas: rc=1
              restauradas: rc=0
otros         layoutcross 79 vectores rc=0 · mmio 48 vectores rc=0
artefacto     08-ARQUITECTURA/artifacts/R17-LOCALES/{ib.txt, ib.json, locales.txt}
escrituras    0 ficheros de otros agentes
```

## 7 · LO QUE ESTO NO PRUEBA

**No prueba que los offsets sean correctos en el hardware.** Son el resultado de
evaluar la aritmética del driver con sus propias macros. Que el ASIC espere la
carga en `ptr[192]` es otra cosa, y `RUNTIME=NOT_RUN`.

**No prueba que `total_size` sea lo que el driver cree.** Si el driver se
equivoca al calcular el tamaño, yo me equivoco igual con él. **Comparto el sujeto,
no lo contrasto** — que es lo que dije en `1151 §7` y sigue siendo cierto.

**No hay un oráculo independiente para `sgpr_offset = 1280`.** El hueco de 62
dwords SÍ es una corroboración parcial: sale de las escrituras generadas y
coincide con la fórmula. Pero la coincidencia es **con la misma aritmética del
driver**, no con el hardware. Un.driver que calculase el hueco consistentemente
equivocado daría el mismo 62 en los dos sitios.

**No he hecho el desenrollado de bucles anidados**, y ahora que `i` aparece como
parada declarada se ve mejor por qué: `i` se resuelve por la vía del desenrollado,
que es la correcta, y la propagación no lo toca. Dos capacidades, dos vías, sin
duplicar.

**Y `ib.length_dw` sigue sin calcularse**, declarado en §5.