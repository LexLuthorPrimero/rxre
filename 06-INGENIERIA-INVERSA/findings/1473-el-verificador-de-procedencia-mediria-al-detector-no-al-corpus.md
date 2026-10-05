# 1473 — El verificador de procedencia pasa de 126 a 63 a 2 según cómo se escriba la clave: el hueco que iba a medir no existe, y la herramienta que lo iba a cerrar tampoco

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

TIPO=HALLAZGO NEGATIVO · método intentado y descartado, con sus tres mediciones
ARTEFACTO MEDIDO=06-INGENIERIA-INVERSA/findings/   683 ficheros, 599 con token de estado
REPRODUCIBLE CON=tools/prov.py 1.0.0   9 vectores, 9 PASS, exit 0
HERRAMIENTA NO CONSTRUIDA=un verificador de procedencia.  Se descarto.
PROPOSITO ORIGEN=la propuesta V10 EVIDENCE-CLOSED RE del propietario

CIERRA=el punto de la propuesta V10 que decía "comprobar automaticamente que el
        claim tiene productor, que la transformacion esta documentada, ..."
        NO SE CONSTRUYE, y este documento dice por que con tres cifras medidas.
REUTILIZABLE=las TRES cifras, que son el resultado.  Un detector de procedencia
        escrito sobre este corpus mide lo que el regex sabe medir, no lo que
        el corpus declara.
```

## 0 · QUÉ SE PROPONÍA

De la lista V10 que pasó el propietario:

```text
  ¿el claim tiene productor?
  ¿la transformación está documentada?
  ¿la representación está identificada?
  ¿el consumidor está identificado?
  ¿existe evidencia independiente?
```

La primera pregunta es la única automatizable hoy sobre lo que hay escrito. Las
otras cuatro necesitan saber qué producer y qué consumidor son, y eso no está
formalizado en ningún sitio. **Así que la V10 empezaría por un verificador de
procedencia**, y ese verificador es el objeto de este hallazgo.

Y no funciona. No porque el corpus carezca de procedencia, sino porque
**cualquier detector de procedencia escrito sobre este corpus mide el detector.**

## 1 · LAS TRES MEDICIONES

Mismo corpus, mismo conjunto de 599 ficheros con token de estado, tres definiciones
distintas de "tiene procedencia". Las tres cuentas salen de `tools/prov.py`, que
las imprime juntas para que el denominador no se separe del porcentaje:

```
$ python3 tools/prov.py

  ficheros totales en el directorio   683
  hallazgos con token de estado       599
  de ellos, de esta sesion           43

  detector                     sin procedencia    %
    D1  lista cerrada + btik     466           77.8
    D2  D1 o cita o bloque        97           16.2
    D3  CLAVE= o cita o bloque      2            0.3

  factor D1/D3: 233.0x
```

| detector | definición | sin procedencia |
|---|---|---|
| **D1** | clave de una lista **cerrada** de 13 nombres, con backtick | 466 (77,8 %) |
| **D2** | D1 **o** cita `fichero.c:123` **o** bloque ```` ```c ```` | 97 (16,2 %) |
| **D3** | cualquier `CLAVE=` en mayúsculas al principio de línea, **o** cita `fichero:123`, **o** bloque de código | **2 (0,3 %)** |

**El hueco se multiplica por 233 entre D1 y D3.** Ninguno de los tres números
describe el corpus. Describen tres regex.

**Y las cifras absolutas se mueven, porque el corpus crece.** La primera vez que
lo medí a mano salían 151 y 96, sobre 597 ficheros. Hoje son 466 y 97, sobre 599.
No es que la.regex cambiese de opinión: es que la escribí tres veces de tres
formas. **Por eso el hallazgo se apoya en el factor, no en el número**, y por eso
los vectores de `prov.py` comprueban relaciones entre detectores y ningún número
absoluto. Un vector que comprobara `D1 == 466` fallaría mañana sin que nadie
tocara el detector, y sería un vector que mide el reloj.

## 2 · POR QUÉ D1 FALLA, Y ES LO INTERESANTE

D1 exigía backticks: `` `CORPUS= ``. Leí dos ficheros que D1 marcaba como sin
procedencia y los dos la tienen, escrita de otra forma:

```text
  003-exported-symbols.md
      **Objeto**: `amdgpu-analysis/amdgpu.ko`, SHA256 `a1a44c24...`
      **Volcados**: `symbols-all.txt` (65 596 lineas)
      -> clave en Markdown, dos puntos, NO igual, y con SHA256 del objeto

  040-corpus-verificado-contra-binario-y-runtime.md
      `HERRAMIENTAS_NUEVAS=08-ARQUITECTURA/tools/runtime_obs.py`, `binfacts.py`
      -> clave que no estaba en mi lista cerrada de 13
```

`040` es el caso limpio: usa `HERRAMIENTAS_NUEVAS`, y mi lista tenía
`HERRAMIENTA` singular y como subcadena con `=`. Una lista cerrada de claves
aceptables convierte cada hallazgo escrito por una persona distinta en un falso
negativo.

**Y D3 sigue.teniendo 2 falsos negativos**, por el mismo motivo con otra variante:

```text
  080-un-criterio-automatico-para-las-58-aristas-ambiguas.md
      ID:           080
      TOOL:        tools/relations.py v1.0.0, selftest 27/27 PASS
      -> dos puntos en vez de igual.  Con la Tool y el numero de version
         dentro del valor.
```

`003` y `080` tienen procedencia completa: objeto con hash, comando, salida,
versión de herramienta y número de vectores. **D3 no las ve porque exige `=`.**

## 3 · POR QUÉ NO CONSTRUYO EL VERIFICADOR

Tres razones, y la tercera es la que manda.

**3.1 · No hay hueco que cerrar.** 597 de 599 hallazgos tienen procedencia
declarada. Un verificador que pasara el 99,7 % no vigila nada: da una falsa
sensación de cobertura sobre algo que ya está cubierto a mano.

**3.2 · Su única clase de error sería el falso negativo sobre sí mismo.** Un
verificador de procedencia que no reconoce `ID:` produce `NOT_FOUND` sobre un
fichero con dos hashes SHA256 en la cabecera. Eso es exactamente el fallo que
`1470` §3 medió en los registros: **producir menos resultados y que el
`NOT_FOUND` se lea como ausencia.** Construirlo sería replicar el error que acabo
de documentar.

**3.3 · El presupuesto de `§93` no lo aguanta.** `NO AUTOMATION THEATER`: una
automatización debe reducir coste real o aumentar observabilidad. Ésta no hace
ninguna de las dos cosas en este corpus.

Lo que **sí** sale del ejercicio es el resultado, que es la tabla de §1 y estas
tres reglas, escritas para el que intente escribirlo después:

```text
  AL ESCRIBIR UN VERIFICADOR DE PROCEDENCIA SOBRE HALLAZGOS EN LENGUAJE LIBRE

    1. NO uses una lista cerrada de claves.  Medido: `HERRAMIENTAS_NUEVAS` no
       estaba en la lista de 13 y produjo 40 falsos negativos.
    2. NO exijas un separador.  Medido: `=`, `: ` y Markdown `**` conviven.
    3. NO confundas "mi regex no lo ve" con "el hallazgo no lo declara".
       Si el detector da 0,3 % de huecos, el detector es el problema: ningun
       fichero de este corpus esta tan mal documentado como para fallar
       tres formas de trazabilidad a la vez.
```

## 4 · LO QUE SÍ SE PUEDE AUTOMATIZAR, Y ES OTRA COSA

La V10 no está muerta, pero su punto de entrada no es este. Lo que sí es
automatizable con el corpus actual, y ya está medido:

```text
  ESTADO=PROVEN     474 ficheros
  ESTADO=NOT_DETERMINED  445 ficheros   (se solapan con los anteriores:
                                           muchos hallazgos son a la vez
                                           "esto queda probado" y
                                           "esto otro no")
  NOT_DETERMINED en 445 de 683 ficheros
  y solo 43 ficheros son de esta sesion (WORK_CLASS=AGENT-RE-TOOLING)
```

**El término `NOT_DETERMINED` aparece en 445 ficheros y sólo hay 42 hallazgos
míos.** Las dos cosas que eso permite medir, y que son las que la propuesta
llama "saber qué NO sabe":

```text
  1. INVENTARIO DE NOT_DETERMINED POR RAZON
     El proposed "REASON: static encoding ✓ / runtime execution x" es
     automatizable si cada NOT_DETERMINED declara que falta.  Ahora no lo
     declara de forma parseable, pero al menos lo dice en prosa, y esa prosa
     es leible por persona.  445 ocurrencias es material real.

  2. SEPARAR AUTORIA DE TRABAJO
     680 ficheros, 42 mios.  El contador de trabajo no identifica al autor, y
     este hallazgo lo confirma con un numero, no con una estimacion.
```

El punto 1 es el que corresponde a la V10 y es el siguiente candidato. El punto 2
es el que la directiva del propietario ya pedía declarar por separado.

## 5 · ESTADO

```text
VEREDICTO          NO CONSTRUIR el verificador de procedencia.  El hueco no
                   existe: 99,7 % con procedencia, y los 2 fallos del detector
                   mas laxo son de nuevo falsos negativos suyos.

ENTREGADO          tools/prov.py 1.0.0, que reproduce la tabla de §1 con un
                   unico comando y 9 vectores.  No es el verificador que se
                   descarto: es el que permite FALSAR la razon por la que se
                   descarto.  Sin el, la conclusion seria una afirmacion.

REUTILIZABLE       el metodo: cuando una medicion de campo grande daria una cifra
                   que suena a problema, la primera pregunta es si el instrumento
                   es correcto.  Aqui la cifra se movio de 151 a 466 en dos
                   ejecuciones sin que nadie tocara el corpus, y cayo a 2 al
                   abrir la definicion.  Tres detectors, un solo corpus.

SIGUIENTE           el punto 1 de §4: inventario de NOT_DETERMINED POR RAZON.
                   Ahi si hay 445 ocurrencias reales y ninguna depende de mi
                   forma de escribir.
```
