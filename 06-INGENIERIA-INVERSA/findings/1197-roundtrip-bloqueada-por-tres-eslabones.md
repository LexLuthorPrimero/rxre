# 1197 — `roundtrip` reescrita desde el bytecode, y el round-trip declarado bloqueado por **tres eslabones nombrados** en vez de por "no funciona"

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=INSTRUMENT-RECOVERY + BLOCKED-AUDIT
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   tools/ibref.py
CLASE=IMPLEMENTATION · LIMITACION · ESTADO=BLOQUEADO_CON_TRES_ESLABONES
CONTINUA=1196 (116 vectores, sin duplicados) -> 1197
ORACULO=tools/_orculo_ibref.pyc  116/116  sha256 e0bdb8d023b1…  modo 444
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST
```

## 0 · `roundtrip` era una invención mía, y su esqueleto estaba en `co_varnames`

La función que reconstruí tenía código muerto dentro —`n.split("_" + _normal(n))[0] if
False else n`— que es la señal de que su autor no sabía qué estaba escribiendo. Los
`co_varnames` del original, en cambio, dan el esqueleto completo:

```text
ib, tablas, eval_call, macros, enlaces, filas,
op, n, idxs,          <- for op, n, idxs in _segmentar(ib)
dvals, lay, pos,       <- los VALORES, el LAYOUT, la POSICION en la lista
dw_i, dv, expr,        <- indice de dword, su valor, su expresion
entrada, campo, valor,
tm2, ancho, lo, hi, rango,    <- los DOS matches y el rango
tm1, base, leido, extra
```

Y las constantes dan la sintaxis de la declaración, los dos regex, las ocho claves de fila y
el orden de veredictos. Todo eso está en `1196`; lo que faltaba era la función, y se ha
reescrito con ese contrato.

## 1 · El `re.I` no era decorativo: era el punto entero

El oráculo busca la entrada con

```python
re.search(re.escape(campo), entrada, re.I)
```

El driver escribe **`PACKET3_T_ALFA(3)`** y la declaración dice **`alfa[1:0]`**. El nombre
no coincide en caja. Sin `re.I` el campo no se encuentra nunca, y **todo** sale
`NO_EXTRAIBLE` — que es exactamente el síntoma que tenía mi versión, y que yo leía como
"la declaración no nombra el campo".

> El `re.I` de un regex es una afirmación sobre la realidad que se está comparando. No
> estaba puesto por descuido: estaba puesto porque los dos lados no coinciden en caja.

## 2 · El fixture, recuperado literal — y lo que yo había inventado en su lugar

```text
'PACKET3(PACKET3_T, 0)'                                   <- cabecera
'PACKET3_T_ALFA(3) | PACKET3_T_BETA(1)'                    <- dos campos en un dword
'PACKET3_T_ALFA(3)'
'PACKET3_T_GAMMA(ring_me == 1 ? 0 : 1)'
'PACKET3_T'                                                <- la CLAVE de `tablas`
'CONTROL[31:0]  (alfa[1:0] | beta[31:31] | gamma[8:2])'
'CONTROL[31:0]  (alfa[4:2])'
'CONTROL[31:0]  (alfa[1])'
'CONTROL[31:0]  (gamma[31] | check[30] | db[25:2])'
'CONTROL[31:0]  (alfa[1:0])'
'SOBRANTE[31:0]'
```

Lo mío era otra cosa: opcode `PACKET3_MAP_QUEUES_*`, declaración como tuplas
`("ALFA", (0, 31))`, y campos `DELTA`, `EPSILON`, `ZETA`, `ETA`, `THETA` que **no existen
en el original**. En el original solo hay `ALFA`, `BETA` y `GAMMA`.

Y la forma de `tablas` queda determinada por la constante suelta `'PACKET3_T'`, que no es un
patrón sino una **clave**: es el nombre del paquete sin `PACKET3_`.

## 3 · Los tres eslabones que faltan, nombrados uno por uno

Con el fixture puesto, los siete vectores siguen en rojo. Los tres motivos, medidos:

### 3.1 El opcode es un número y hace falta el nombre

```python
_segmentar(ib)  ->  (44, 2, [0, 1, 2])
```

Y hacen falta dos cosas con el **nombre**: la clave de `tablas` (que es `'PACKET3_T'`, una
cadena) y el prefijo que `_campos_mencionados` usa para partir `PACKET3_T_ALFA(3)`. Mi
versión pasaba el entero y `re.escape(44)` reventaba:

```text
  TypeError: decoding to str: need a bytes-like object, int found
```

**Falta la tabla opcode → nombre.** Se ha añadido `_nombre_de_paquete()`, que degrada a
`None` en vez de reventar. Un vector bloqueado debe decir que está bloqueado: el crash
esconde el motivo y hace parecer que el fallo es otro.

### 3.2 Un dword puede llevar dos campos, y mi emparejamiento exige uno

El literal es `'PACKET3_T_ALFA(3) | PACKET3_T_BETA(1)'`. `_campos_mencionados` empareja
**toda** la expresión contra `^PACKET3_([A-Z0-9_]+)\s*(\(...\))?\s*$`, y con un `|` en medio
no hay manera de que case. Resultado medido: **0 filas**.

> Falta partir por `|` antes de emparejar. Y el literal existe precisamente para
> probarlo: es el caso de dos campos en un dword, que es lo que un layout de PM4 hace
> constantemente.

### 3.3 La cabecera literal lleva `count = 0`

```python
'PACKET3(PACKET3_T, 0)'
```

`PACKET3(op, n)` mete `n` en los bits 23:16, así que el valor numérico de ese dword tiene
**count 0**, y `_segmentar` ve un paquete sin payload. Comprobado:

```text
  valor con count=0  ->  [(44, 0, [0]), (0, 0, [1]), (0, 0, [2]), (0, 0, [3])]
  valor con count=2  ->  [(44, 2, [0, 1, 2])]
```

Falta un literal: **la cabecera cuyo valor cargue el `count` real**. Rellenarlo con un 2
inventado sería fabricar el fixture, que es lo mismo que `1193` me corrigió a mí.

## 4 · Lo que sí ha cambiado en el instrumento

```text
  roundtrip()   reescrita con el contrato del .pyc:  sintaxis de la declaracion,
                los dos regex con escape y sin distincion de caja, las ocho
                claves de fila (paquete, dword, payload, campo, esperado, rango,
                leido, veredicto) y el orden de los seis veredictos
  _campo_por_nombre()   [hi:lo] antes que [N];  al reves, un campo de dos bits
                        saldria de un bit
  _campos_texto()       lo que la DECLARACION nombra, separado de lo que el
                        driver ESCRIBE:  confundirlas daria como sobrante un
                        campo que el driver si escribe
  _nombre_de_paquete()  degrada a None en vez de reventar con TypeError
  DECL_RT               las seis entradas literales del .pyc
```

Los doce vectores siguen en rojo — **no hay ninguno verde nuevo**— y el total se mantiene en
116 sin regresión. Lo que ha cambiado es que el bloqueo está **descrito**, y antes no lo
estaba.

## 5 · El estado, y por qué un instrumento bloqueado se declara en vez de empujarse

```text
  ibref.py   104 de 116 vectores      (63 al terminar 1183)
  rxre       188 vectores rc=0
  huella      27 vectores rc=0
  toolreg     14 checks, 0 failures
  oraculo    116/116  sha256 e0bdb8d023b1…  modo 444

  los 12 que quedan
     7  round-trip      bloqueado por los tres eslabones de §3
     3  decode          falta el layout declarado de PACKET3_TEST
     1  desenrollo RECHAZA: comparacion distinta de `<`
                         RE_COMPARACION esta importado y el rechazo no lo mira
     1  ampliacion: las macros del primario
                         PACKET3_TEST no aparece en pm4_emit.py (0 ocurrencias)
                         ni en el STUB:  no se sabe de donde deberia salir
```

> Un instrumento bloqueado que se declara bloqueado vale más que uno que se empuja: el
> primero dice dónde parar y el segundo deja de decirlo.

## 6 · Procedimiento

```text
RECUPERADO  co_varnames de roundtrip  ->  el esqueleto de la funcion
RECUPERADO  10 literales del fixture  ->  4 expresiones y 6 entradas
RECUPERADO  la forma de `tablas`:  {CLAVE: [entradas de TEXTO]}
REESCRITA   roundtrip con ese contrato
MEDIDO      con el fixture puesto:  0 filas, y los 3 motivos identificados
NO HECHO    los 3 eslabones:  tabla opcode->nombre,  partir por `|`,  y el
            literal de la cabecera con el count real
no hecho    nada de esto se ha rellenado con un valor inventado
runtime     RUNTIME=NOT_RUN.  Ni la RX550 ni la Intel.  i915 y amdgpu intactos
```
