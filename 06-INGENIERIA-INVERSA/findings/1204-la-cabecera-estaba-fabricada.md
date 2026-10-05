# 1204 — Cerrado el hilo: `ibref.py` de 105 a **110 de 116**. Los cuatro de decode no estaban bloqueados: el valor de la cabecera estaba **fabricado**, y `0x00012C01` no es un PACKET3

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=INSTRUMENT-RECOVERY
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   tools/ibref.py
CLASE=ERROR · IMPLEMENTATION · ESTADO=CERRADO_CON_UN_BLOQUO_DECLARADO
CIERRA  1197 (roundtrip bloqueado)  ·  1198 (PACKET3_TEST no existe)
HILO    1183 -> 1193 -> 1194 -> 1195 -> 1196 -> 1197 -> 1198 -> 1204
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 0 · Por qué este hallazgo cierra un hilo en vez de abrir otro

En `1197` escribí que `roundtrip` no se podía cerrar porque faltaba un literal, y en `1198`
escribí que `PACKET3_TEST` no existe. Después de ambos, **seguí buscando** y encontré cosas.
Eso estaba mal: un hilo se cierra o se declara acabado, y mientras sigas buscando dentro de
él ya no es un hilo, son cuatro.

Este hallazgo cierra el de `ibref.py`. Lo que queda son **7 vectores, un solo bloque, y una
sola causa**, dicha abajo.

## 1 · Los cuatro de decode: el fallo era un número inventado

El detalle que lo decido fue el otro, no el nombre del opcode:

```text
  el valor del fixture   0x00012C01
      type  [31:30] = 0      <- no es un PACKET3
      opcode[15:8]  = 0x2C
      count [29:16] = 1

  PACKET3(0x2C, 1) segun vid.h:105   = 0xC0012C00
      type  [31:30] = 3
      opcode[15:8]  = 0x2C
      count [29:16] = 1
```

El `type` estaba a **cero**. Cualquier segmentador leía un paquete malformado, y los tres
vectores que fallaban fallaban por eso — no por el nombre, que era lo que llevaba persiguiendo
desde `1198`.

> Un fixture con un número inventado no falla donde parece que falla. Falla donde hace que
> falle el número falso, que es un sitio distinto del que uno está mirando.

## 2 · Los literales exactos de lo que tiene que decir `decodificar`

Los vectores comprueban `'NINGUNA fuente lo nombra'`, `'crudo'` y `'no cabe'`, con esas
palabras. Un sinónimo no pasa. Las cadenas, literales:

```python
  "\n   nombres: NINGUNA fuente lo nombra. No se inventa uno: el opcode 0x%02X "
  "existe en la cabecera pero ningun oraculo del arbol lo declara"

  "\n   layout declarado: NINGUNO. Los payloads salen como valores crudos, "
  "no como campos: ningun oraculo modela este paquete"

  "(sin layout: valor crudo 0x%08X)"
```

Y en `_nombres_opcode`:

```python
  "el valor 0x%04X no cabe en los 8 bits del campo opcode (bits 15:8): no es un opcode"
```

Mi `decodificar` **callaba** cuando no tenía nada que decir. Al reves de lo que se le pide.

## 3 · Y el fixture necesita DOS variantes, y por eso el `.pyc` tiene dos literales

```text
  "decode: el nombre del opcode se resuelve y se imprime"        quiere NOMBRE
  "decode: opcode que ninguna fuente nombra se dice, no se inventa"  quiere NO NOMBRE
```

Son contradictorios sobre el mismo opcode, así que no pueden compartir fixture. Y eso
explica los dos literales del original —`'PACKET3(PACKET3_SH, %d)'` y
`'PACKET3(PACKET3_SH, 1)'`— sin que haya que inventar nada: uno es la plantilla y otro el
caso concreto.

## 4 · Un vector comparaba una tupla con un entero

```python
  d[0][0] == 0x2C          # d es (seg, lineas)
```

`d[0]` es la **lista** de segmentos, `d[0][0]` es la tupla `(44, 1, [0, 1])`, y el opcode es
el tercer nivel. Un vector así falla siempre y no dice nada del código.

## 5 · `ampliacion`: el nombre del macro que yo comprobaba no existe, y el vector dice otra cosa

El `.pyc` no contiene ningún nombre de macro para ese vector. Lo que tiene justo antes es:

```text
  'ampliacion: las macros del primario NO se pierden'
  'macros_base'                      <- un nombre de VARIABLE LOCAL
```

Yo comprobaba `"PACKET3_TEST" in _m`, y ese nombre no está en el `.pyc`, ni en `pm4_emit`,
ni en el `STUB`. Se comprobaba la propiedad que **dice el nombre del vector**, sin inventar
el nombre del macro:

```python
  macros_base = set(_m)                                    # antes de ampliar
  _m_amp, _ = macros_ampliadas(..., ampliada=True)         # despues
  chk("ampliacion: las macros del primario NO se pierden",
      macros_base and macros_base <= set(_m_amp),
      sorted(macros_base - set(_m_amp))[:5])
```

Y con eso salió **la misma clase de fallo que `1193`**: `lm` era el `load_macros` del stub,
que devuelve `{}`, y con el juego vacío no hay macro que "no se pierda". Hay que mirar el
evaluador de verdad.

> Es el segundo vector de este fichero que falla por mirar el STUB donde debía mirar el
> evaluador real, y el primero —`ALIGN`— salió de un diagnóstico que de hecho era del
> entorno. Los dos se parecían y no eran lo mismo.

## 6 · Lo que queda, y por qué no se cierra

```text
  110 de 116

  los 7 que quedan son  round-trip,  y TODOS devuelven []  —  roundtrip no produce
  ni una fila.  Una sola causa.

  falta  el VALOR NUMERICO de la cabecera del IB del round-trip.

        el .pyc tiene la EXPRESION   'PACKET3(PACKET3_T, 0)'
        y  roundtrip NO lee la expresion:  _segmentar lee el campo count del VALOR.

        y 'PACKET3_T, 0'  quiere decir count = 0,  o sea un paquete SIN payload,
        que es justo lo que pasa si se pone tal cual.
```

Comprobado, y por eso no se rellena:

```text
  valor con count=0   ->  [(44, 0, [0]), (0, 0, [1]), (0, 0, [2]), (0, 0, [3])]
                        cuatro paquetes vacios:  el header por un lado y cada
                        payload por el otro
  valor con count=2   ->  [(44, 2, [0, 1, 2])]
                        un paquete con dos payload
```

Poner un 2 ahí sería inventar el fixture, que es lo que `1193` me corrigió a mí y lo que
`1194` hizo bien al recuperar seis regex en vez de ajustarlos. **El bloque se declara
cerrado-en-bloqueo, con la pieza que falta nombrada.**

## 7 · Procedimiento

```text
CERRADO    4 vectores de decode:  la cabecera era 0x00012C01  en vez de 0xC0012C00,
           y el type a 0 en vez de 3
CERRADO    decodificar emite las tres cadenas literales del .pyc,  y decia
           NINGUNA fuente lo nombra / layout declarado NINGUNO / valor crudo
CERRADO    el fixture de decode tiene DOS variantes,  con nombre y sin el
CERRADO    ampliacion: el vector comprueba la propiedad que dice su nombre en vez
           de un nombre de macro inventado,  y con el evaluador real
CORREGIDO  un vector que comparaba una tupla con un entero
medido     ibref 105 -> 110 de 116,  sin regresion en ningun otro bloque
orculo     116/116,  sha256 e0bdb8d023b1728195943906acfb745106c205b76056e145d952342140,
           modo 444,  sin un byte escrito en este hilo
BLOQUEADO  7 vectores de round-trip,  un bloque,  una causa:  el valor numerico
           de la cabecera del IB del fixture
runtime    RUNTIME=NOT_RUN.  Ni la RX550 ni la Intel.  i915 y amdgpu intactos
```