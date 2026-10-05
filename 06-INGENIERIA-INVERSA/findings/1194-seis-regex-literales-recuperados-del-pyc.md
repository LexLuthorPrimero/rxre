# 1194 — `ibref.py` de 77 a 102 de 116. La mitad de los fallos eran **cosas que el oráculo tenía y yo no había buscado**: seis regex literales, recuperables del `.pyc` emparejando `LOAD_CONST`/`STORE_NAME` del bytecode

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=INSTRUMENT-RECOVERY + DIFFERENTIAL-ORACLE
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   tools/ibref.py
CLASE=IMPLEMENTATION · ESTADO=PARCIAL_MEDIDO
CONTINUA=1183 (reconstruccion)  ->  1193 (77->85)  ->  1194 (85->102)
ORACULO=tools/_orculo_ibref.pyc  116/116  sha256 e0bdb8d023b1…342140  modo 444
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST
```

## 0 · El error de partida, que es lo que hacía el diagnóstico engañoso

Copié `ibref.py` a `/tmp` para trabajar sobre una copia. `RAIZ` se resuelve como
`dirname(dirname(abspath(__file__)))`, así que pasó a ser `/tmp`, y
`entrada_por_defecto()` devolvió una ruta inexistente. Cinco vectores de `ALIGN`
fallaron y el diagnóstico correcto era **el entorno, no el instrumento**.

Montado el árbol espejo (`RESEARCH` y `08-ARQUITECTURA` enlazados), los mismos cinco
seguían fallando. Eso ya no era entorno, y ahí empezó el trabajo real.

## 1 · Lo que había debajo de los cinco: un par mal emparejado

El selftest carga **dos** juegos y nada exigía que fueran del mismo:

```text
  ev, lm              el STUB       (cargar_evaluador(pystub))
  _ev_real, _lm_real  los de verdad (cargar_evaluador())
```

Los vectores de `ALIGN` pasaban `macR` (macros reales) con `ev` (stub, sin headers de
kernel). **+5.**

## 2 · Los seis regex que el oráculo tenía y yo no habia mirado

No eran ideas que faltaran: eran **literales**, y se recuperan emparejando la secuencia
`LOAD_CONST` → `STORE_NAME` del bytecode del módulo:

```python
RE_IDX_WRITE      = '([A-Za-z_]\\w*)\\.ptr\\s*\\[\\s*([^\\]]+?)\\s*\\]\\s*=\\s*(.+?);'
RE_FOR            = '^[ \\t]*for\\s*\\(\\s*([A-Za-z_]\\w*)\\s*=\\s*([^;]+?)\\s*;\\s*\\1\\s*<\\s*([^;]+?)\\s*;\\s*(?:\\1\\s*\\+=\\s*([^)]+?)|\\1\\+\\+)\\s*\\)'
RE_FOR_CUALQUIER  = '^[ \\t]*for\\s*\\('
RE_COMPARACION    = '^(.+?)\\s*(==|!=)\\s*(.+)$'
RE_ARR_DECL       = '^[ \\t]*(?:static\\s+)?(?:const\\s+)?u32\\s+([A-Za-z_]\\w*)\\s*\\[\\s*\\]\\s*=\\s*\\{'
RE_ASIGN          = '^[ \\t]*(?:[A-Za-z_]\\w*)[ \\t]*(\\+?=)[ \\t]*(.+?);[ \\t]*$'
```

Tres consecuencias que no eran adivinables de deducir:

```text
RE_IDX_WRITE existe  ->  hay DOS formas de escritura.  `ib.ptr[ib.length_dw++]`
                         (secuencial) y `ib.ptr[i + 4]` (POSICIONAL).  Yo solo
                         tenia la primera, y por eso los tres vectores POSICIONAL
                         no tenian ni una fila.

RE_COMPARACION existe  ->  hay un regex para RECHAZAR un `for` cuya comparacion no
                         es `<`.  Es lo que hace que el rechazo pueda decir POR QUE
                         en vez de solo fallar en silencio.

RE_ASIGN no captura el NOMBRE  ->  `(?:[A-Za-z_]\\w*)` va sin grupo.  Una
                         declaracion tipada (`u32 x = 1;`) NO casa,  porque tras
                         `u32` hay un espacio y un identificador, no un `=`.  En C
                         una declaracion no es una asignacion,  y el regex lo sabe.
```

## 3 · El error de semántica que emitía una IB con un dword de más

Mi cuenta de iteraciones era

```python
n = (fin - inicio) // paso + 1        # la cuenta de `<=`
```

Con `<`, `i = 0`, `ARRAY_SIZE(t) = 6` y `i += 2`, eso da **4** iteraciones donde deben
ser 3. Y la cuarta lee `t[6]`, **fuera del array**.

> Un desenrollador que emite de más no falla al escribir: sintetiza una IB con un
> dword de más y nadie lo ve.

```python
n = -((inicio - fin) // paso)          # techo de (fin - inicio)/paso
```

## 4 · El fixture estaba mal, y el oráculo lo decía en el nombre del vector

`DES_BUCLE_LLAVES` es **reconstruido**, y mi versión ponía `i++`. Dos cosas lo dicen,
ninguna de las dos soy yo:

```text
1. el nombre del vector del oráculo es, literalmente,
   "desenrollo: el bucle de ARRAY_SIZE da 3 iteraciones (6 elem, +2)".
   Con `i++` sobre 6 elementos salen 6 iteraciones en C, no 3.  El "+2" ES el paso.

2. el mensaje de rechazo del oráculo: "solo se entiende
   for (V = <entero>; V < <limite>; V += <entero>)", y hay un vector APARTE para
   `i++` ("i++ equivale a i += 1").  O sea: `i++` existe, pero en otro fixture.
```

Recuperé el fixture **por el nombre del vector**. Adaptar el código para que dieran 3
con `i++` habría sido inventar una regla de C que no existe.

## 5 · Los cuatro fallos que no decían nada de su causa

| Síntoma | Causa real |
|---|---|
| 3 filas donde deben ser 6 | `m.group(0).rstrip().endswith("{")` —el grupo termina en `)`, **nunca** en `{`. El bucle con llaves caía siempre por la rama de sentencia única |
| `t[0 + 1]` en vez de `t[1]` | `desenrollar` construía la tabla `arrays` y le pasaba **`{}`**. Sin tabla, el elemento no se resuelve; después la sustitución de la variable ligaba `i` y la suma no se plegaba |
| 3 filas y 0 valores | `_intento("i + 1", lig)` devolvía `None`: no plegaba aritmética. Añadido `_indice_aritmetico` |
| la escritura posicional se capturaba **sin destino** | `_destino_de` buscaba `[i + 4]` dentro del texto, y `RE_IDX_WRITE` entrega el índice **sin corchetes** |

> El sintoma "hemos añadido soporte y hay MENOS filas" fue el que hizo sospechar del
> filtro y no del añadido: al recorrer los dos regex seguidos, cada escritura
> secuencial salía **dos veces** (`ib.ptr[ib.length_dw++]` cumple los dos patrones).
> 6 filas se fueron a 9.

Y una lección de método que sale de este bloque entero:

> Ninguno de estos fallos se veía leyendo el sintoma. Los cinco primeros se
> diagnosticaron **midiendo**: comparar el comportamiento del oráculo contra el mío,
> no leer el código mío esperando que el error se describa a sí mismo.

## 6 · El saldo

```text
  1183 (reconstruccion)          63 / 116
  1193 (esta sesion, 1)          77 -> 85     +8
  1194 (esta sesion, 2)          85 -> 102    +17
                                 ─────────────
                                 +39 en dos hallazgos

  queda
    round-trip      7   los 6 estados con su formato de declaracion y los
                         fixtures;  NO_EXTRAIBLE para los siete campos porque
                         la declaracion no los nombra
    decode          3   el layout de PACKET3_TEST no esta declarado
    desenrollo      1   RECHAZA: comparacion distinta de `<`
    cond            2   punto decimal; lista de escrituras que incluye lo no emitido
    propagacion     1   asignacion dentro de un `if`
    ampliacion      1   las macros del primario

  oraculo  116/116  sha256 e0bdb8d023b1728195943906acfb745106c205b76056e145d952342140
           modo 444.  No se le ha escrito ni un byte en ninguna de las dos sesiones
```

## 7 · Procedimiento

```text
RECUPERADO  6 regex literales del .pyc por LOAD_CONST/STORE_NAME del bytecode
            mas los nombres RE_ de co_names,  que dicen que existen y para que
CORREGIDO   el par stub/real de ALIGN                          +5
CORREGIDO   RE_FOR al literal del oraculo
CORREGIDO   la cuenta de iteraciones:  era la de `<=`            +7 (desenrollo)
CORREGIDO   la deteccion de llaves del cuerpo de bucle          +1
CORREGIDO   la tabla arrays se construye y SE USA
CORREGIDO   plegado aritmetico de indices                       +3
CORREGIDO   destino posicional, con y sin corchetes             +2
CORREGIDO   RE_IDX_WRITE para las escrituras POSICIONAL
CORREGIDO   el solape entre los dos regex de escritura
no hecho    round-trip, que necesita los 6 estados y su formato de declaracion
runtime     RUNTIME=NOT_RUN.  Ni la RX550 ni la Intel.  i915 y amdgpu intactos
```
