# 1196 — Los **116 vectores** del oráculo, sin duplicados y con el que faltaba. El contrato de `roundtrip` recuperado del `.pyc` entero, y **la regla que lo une al opcode no se recuperó** — así que no se inventó

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=INSTRUMENT-RECOVERY
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   tools/ibref.py
CLASE=IMPLEMENTATION · LIMITACION · ESTADO=PARCIAL_MEDIDO
CONTINUA=1183 -> 1193 -> 1194 -> 1195 -> 1196
ORACULO=tools/_orculo_ibref.pyc  116/116  sha256 e0bdb8d023b1…  modo 444
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST
```

## 0 · Los dos vectores duplicados: el oráculo los nombra **una vez**

`1195` encontró que de mis 117 llamadas a `chk` para 116 vectores sobraban dos, con nombres
repetidos. La pregunta era cuál de las dos llamadas de cada par era la buena, y eso lo
contesta el `.pyc`, no el conteo:

```text
  en el ORACULO   1x  comentarios: quitar un comentario NO desplaza las lineas posteriores
                 1x  comentarios: el contenido del comentario desaparece pero el sitio no

  en el ARBOL    2x  comentarios: quitar un comentario NO desplaza las lineas posteriores
                 2x  comentarios: el contenido del comentario desaparece pero el sitio no
```

Y los dos fixtures no eran el mismo. El segundo llevaba escrito de dónde venía:

```python
# FIXTURE REAL, del bytecode del original: 'a\n/* uno\ndos\ntres */\nb\n'
```

Comprobado contra el `.pyc`: la constante existe y es **exactamente** esa. El primero usaba
un array que me había inventado. Se quitó el par inventado.

> Un vector duplicado **pasa**, y pasar es lo que se supone que tiene que hacer. Por eso no
> se ve contando fallos sino contando **nombres**.

## 1 · El vector que faltaba: recuperado por NOMBRE, y declarado como tal

```text
  del oraculo que me faltan de verdad
    ampliacion: la prueba de roots se pudo ejecutar
```

El `.pyc` nombra el vector pero su aserción vive en el bytecode y no es legible como texto.
Lo que se ha escrito afirma **lo que el nombre permite afirmar**, y lo dice dentro del
propio vector:

```python
# RECUPERADO POR NOMBRE, NO POR CODIGO.  El `.pyc` nombra este vector pero su
# asercion esta en el bytecode y no es legible como texto. Lo que se afirma aqui
# es lo que el NOMBRE permite afirmar, y se declara que no es mas que eso:
#
#     un vector cuyo nombre se recupera y cuya afirmacion no,  es un vector
#     con el nombre puesto
```

La afirmación: la prueba de raíz tiene que poder **ejecutarse**. Si `KERNEL_INC` no existe,
`_raiz_segera()` devuelve `False` sin mirar nada, la ampliación queda muerta para siempre, y
el síntoma sería "no hay macros" — no "no se pudo comprobar".

## 2 · El saldo: 116 vectores, sin repetidos

```text
  llamadas a chk        116   (el oraculo: 116)
  nombres distintos     116   (sin duplicados)
  pasan                 104
  fallan                 12

  1183 (reconstruccion)  63 / 116
  1193                   77 -> 85
  1194                   85 -> 102
  1195                  102 -> 105
  1196                  105 -> 104      (2 menos: los duplicados; +1: el que faltaba)
                         ─────────────
                         +41 desde la reconstruccion
```

Que el recuento de `ok` **baje** dos vectores mientras el total se mantiene es lo correcto:
se quitaron dos que probaban lo mismo dos veces. Un instrumento que sube de verde porque se
ha añadido cobertura está mintiendo si la cobertura ya estaba.

## 3 · `roundtrip`: el contrato está recuperado ** entero**, menos una pieza

Del `.pyc`, constantes de `roundtrip` y nombres de `co_names`:

```text
  SINTAXIS DE LA DECLARACION
     CONTROL[31:0]  (alfa[4:2])
     alfa[1:0] | beta[31:31] | gamma[8:2]
     "alfa[1]"          ->  rango  "%d (lsb solo)"
     "alfa[1:0]"        ->  rango  "%d:%d"

  LOS DOS REGEX
     \b%s\s*\[\s*(\d+)\s*:\s*(\d+)\s*\]      campo con rango
     \b%s\s*\[\s*(\d+)\s*\]                   campo de un bit

  OCHO CLAVES POR FILA
     paquete, dword, payload, campo, esperado, rango, leido, veredicto

  ORDEN DE VEREDICTOS
     NO_EXTRAIBLE -> VALOR_NO_AISLABLE -> OK_SOLO_UN_BIT -> OK -> MISMATCH
     -> FUERA_DE_PAQUETE   (con el texto "(entrada %d de la declaracion)")

  COMO SE BUSCA LA ENTRADA
     re.search(re.escape(campo), entrada, re.I)     sin distincion de mayusculas
```

Y los fixtures reales, que son **distintos** de los míos:

```text
  expresion del driver:   'PACKET3_T_ALFA(3) | PACKET3_T_BETA(1)'
  declaraciones:         'CONTROL[31:0]  (alfa[1:0] | beta[31:31] | gamma[8:2])'
                         'CONTROL[31:0]  (alfa[4:2])'
                         'CONTROL[31:0]  (alfa[1])'
                         'CONTROL[31:0]  (gamma[31] | check[30] | db[25:2])'
```

El mío usaba `PACKET3_MAP_QUEUES_ALFA` con `("ALFA", (0, 31))`: opcode inventado y
declaración como tuplas, cuando el oráculo la lleva como **texto** y por eso necesita
`re.escape` + `re.I`.

## 4 · Lo que **no** se recuperó, y por eso el bloque no se tocó

Falta **la regla que asocia un opcode con su declaración**. El oráculo usa `.get(...)`, y
el candidato natural es buscar el registro cuyo nombre menciona la expresión del paquete —
pero el candidato natural no es evidencia. Hay al menos tres reglas distintas que encajan
con todo lo recuperado:

```text
  (a) por nombre:  la expresion `PACKET3_T_ALFA(3)`  nombra el registro
  (b) por posicion:  el primer dword del paquete es el CONTROL
  (c) por prefijo:  el prefijo comun de los campos del dword
```

Elegir una sería **inventar** la interfaz de la función, y eso es exactamente el fallo que
`1193` y `1194` corrigieron en mí: cambiar el fixture `DES_BUCLE_LLAVES` porque mi código
daba otro número, en vez de recuperar el fixture.

> Un fixture cuyo formato se ha recuperado y cuya regla no, no se arregla adaptando el
> código: se declara incompleto.

Los siete vectores de `round-trip` quedan como están, y con la regla pendiente escrita.

## 5 · Los cinco fallos que quedan, y su estado real

| Vector | Por qué | Qué falta |
|---|---|---|
| 7 × `round-trip` | el fixture y la asociación opcode→declaración | la regla (ver §4) |
| 3 × `decode` | falta el layout declarado de `PACKET3_TEST` | el layout |
| 1 × `desenrollo RECHAZA: comparación distinta de `<`` | `RE_COMPARACION` está importado pero el rechazo no lo comprueba | el enganche |
| 1 × `ampliacion: las macros del primario` | `PACKET3_TEST` **no aparece** ni en `pm4_emit.py` (0 ocurrencias) ni en el `STUB` | saber de dónde debe salir |

El último es el más raro y queda dicho como raro: un vector que comprueba que una macro
existe, y esa macro no está en ninguno de los dos sitios donde tendría que estar. O mi
`STUB` está incompleto, o el vector recupera un nombre de macro que el original sacaba de
otro sitio. **No elegido.**

## 6 · Procedimiento

```text
AUDITADO    117 chk para 116 vectores -> 116 chk, 116 nombres distintos
            el par de comentarios inventado,  eliminado;  el del bytecode, conservado
RECUPERADO  ampliacion: la prueba de roots se pudo ejecutar  (por NOMBRE,  y
            declarado que su afirmacion no se recupera)
RECUPERADO  contrato de roundtrip: formato,  dos regex,  ocho claves,  orden de
            veredictos, y los cuatro fixtures literales
NO HECHO    reescribir roundtrip:  falta la regla opcode->declaracion,  y hay
            tres candidatas indistinguibles con lo recuperado
no hecho    los 3 de decode,  el 1 de ampliacion,  y el enganche del RECHAZA
runtime     RUNTIME=NOT_RUN.  Ni la RX550 ni la Intel.  i915 y amdgpu intactos
```
