# 080 · Un criterio automático para las 58 aristas ambiguas, y por qué no se puede aplicar

```
ID:           080
TIPO:        HALLAZGO NEGATIVO — método intentado y descartado, con su validación
ALCANCE:     tools/relations.py, KNOWLEDGE-GRAPH.md
TOOL:        tools/relations.py v1.0.0, selftest 27/27 PASS
GPU:         INTACTA
CIERRA:      el punto 1 del NEXT ACTION de 079 (con resultado negativo)
```

## RESUMEN

`079` dejó 58 aristas cuyo destino es un número ambiguo: el origen menciona
`023` y hay dos findings numerados `023`. Lo que hace falta es decidir cuál.

Se intentó un discriminante automático:

> **Un finding gana si el origen cita un término del corpus que aparece en él y
> en ninguno de los otros con el mismo número.**

Resultado: **no se puede aplicar**, por dos razones que sólo aparecen al
intentar validarlo.

## 1 · EL CRITERIO, Y SU PRIMERA MEDICIÓN

```
58 aristas ambiguas respaldadas por número
   AMBOS   (el origen cita términos exclusivos de los dos)   33  (57%)
   UNICO_B                                                              13  (22%)
   UNICO_A                                                               6  (10%)
   NINGUNO                                                              6  (10%)
```

19 resoluciones «únicas». Antes de usarlas: **¿es correcto?**

### El criterio estaba contaminado por metadatos

Los términos «exclusivos» queGanaban eran:

```
MODIFICATIONS   RESEARCH      HYPOTHESIS   ARQUITECTURA
CODIGO          PROVEN        WRITE_EXECUTION
```

Esos son **nombres de campo de la cabecera**, no términos del corpus. Salen
porque un campo aparece en una cabecera y no en la otra. Depurado con la lista
blanca `ESTRUCTURA` de `074`:

```
AMBOS   20 (34%)     UNICO_A  17 (29%)
NINGUNO 10 (17%)      UNICO_B  11 (19%)
```

**28 resoluciones candidatas**, de las que 17 son ahora términos reales
(`mmCP_HQD_EOP_CONTROL`, `VI_FLUSH_GPU_TLB_NUM_WREG`, `VOLTAGE_SCALE`).

## 2 · LA VALIDACIÓN, Y EL PRIMER FALLO

Antes de aplicar un criterio hay que probarlo donde se sabe la respuesta. Y
hay **un solo sitio donde se sabe**: cuando el origen **cita el finding por
nombre**. Ahí la respuesta no hay que deducirla —está escrita.

```
casos con respuesta conocida: 1
aciertos:                     0
```

### El fallo era mío, y lo arreglo

`045` tiene **tres** findings, y mi criterio comparaba `cands[0]` contra
`cands[1]`. Era binario sobre una entrada ternaria.

Corregido a multi-candidato — «exclusivo» pasa a ser *«en este y en ninguno de
los otros N-1»*:

```
casos con respuesta conocida: 1
aciertos:                     0
predicho: None      respuesta real: 045-la-convencion-de-count-nunca-se-mido-en-mi-asic.md
```

Sigue fallando.

## 3 · POR QUÉ NO PUEDE VALIDARSE — Y ÉSE ES EL HALLAZGO

El caso de prueba es este:

```
ORIGEN   023-pm4-count-convencion-medida.md
  linea 21:  una observación de contraste. Ver `045-la-convencion-de-count-nunca-se-mido-en-mi-asic.md`.
```

Y `045-la-convencion-de-count-…` es uno de los tres `045`.

**El origen nombra el fichero.** Por eso sabemos la respuesta: porque está
escrita. Y por eso el criterio no la encuentra: el criterio busca **términos del
corpus**, y en esa línea no hay ninguno —el término discriminante es
`count`, que va en minúsculas y no casa con el patrón de identificadores.

Queda la estructura inevitable:

```
¿el origen NOMBRA el destino?   ->  respuesta correcta, y NO hace falta criterio
¿el origen lo MENCIONA?         ->  hace falta criterio, y NO hay respuesta conocida
```

**El único conjunto con verdad conocida es el único donde el criterio es
innecesario.** No hay un solo caso donde ambos sean necesarios a la vez.

> Un método que no se puede validar contra ningún caso conocido no es un
> método con75% de acierto: es un método con **acierto desconocido**. Y esa
> cifra no se puede reducir por más que se aplique a 28 casos — aplicarlo sólo
> produciría 28 decisiones con apariencia de evidencia y sin ninguna detrás.

Por eso **las 28 resoluciones candidatas no se aplican**. Se imprimen como
candidatas y se marca que no están validadas.

### Lo que sí produce el criterio, sin usarlo como decisión

```
de las 58 ambiguas:
   un candidato con términos exclusivos citados:  28  (48%)
   varios candidatos con términos exclusivos:      21  (37%)
   ningún candidato con término exclusivo:          9  (16%)
```

Eso es un dato sobre **el texto**, no una decisión sobre la evidencia:
*en 28 de 58 el origen menciona algo que aparece en uno solo de los
candidatos*. Es una pista de lectura, y se registra como pista.

## 4 · POR QUÉ NO SE PUEDE VALIDAR DE OTRA MANERA, Y QUÉ SÍ

Tres vías, y las tres se han descartado con la razón:

**1 · Aplicar el criterio y ver si «parece razonable».** Es inventar con un
uniforme. `071` ya lo dice explícitamente: buscar el destino por parecido de nombre «sería
inventar a qué documento quería referirse el autor, y eso es peor que la
referencia rota».

**2 · Pedir confirmación humana a cada una.** 58 decisiones, y cada una es una
afirmación sobre qué depende de qué. Es trabajo de lectura que se puede hacer,
pero es lectura.

**3 · Usar el `ORDER` del número como pista.** atractivo, y no vale: los
duplicados existen porque dos sesiones escribieron a la vez. La posición
alfabética no codifica nada.

### La vía que sí funciona, y ya está en uso

`077` encontró que **las citas por nombre no son ambiguas**, aunque su número lo
sea. Y `079` lo confirmó: la única arista con cita nominal resuelve
exactamente.

> La desambiguación no necesita un criterio mejor. Necesita que el origen **cite
> por nombre**, y eso es una decisión de escritura, no de lectura.

## 5 · ERRORES PROPIOS

| error | detectado por |
|---|---|
| términos «exclusivos» que eran nombres de campo de cabecera | leyendo la lista: `MODIFICATIONS`, `CODIGO`, `PROVEN` no son términos del corpus |
| criterio binario (`cands[0]` vs `cands[1]`) sobre `045`, que tiene 3 | el caso de validación devolvió `None` con 3 candidatos |
| concluve «el criterio no funciona» antes de corregir el bug del criterio | el fallo era mio; la primera conclusion era prematura |

La tercera importa más que las otras dos: **el resultado negativo «el criterio
no valida» era verdadero y la razón era falsa.** Si no hubiera exigido ver el
`None` en vez del `0`, habría reportado «probablemente requiere más trabajo» y
descartado un criterio que solo tenía un bug. Un resultado negativo no cierra
una línea de investigación por sí solo: hay que haber descartado las causas
propias primero.

## 6 · ESTADO

```
grafo          91 filas · 78 pares · 14 familias · 73 destino AMBIGUO
respaldo       13 inequívocas (14%) · 58 por número ambiguo · 18 sin mención
desambiguación 58 pendientes · criterio automático NO APLICABLE (sin validación)
                 28 con candidato único por término exclusivo  (pista, no decisión)
                 21 con varios candidatos                     (pista)
                  9 sin candidato                             (pista)
declaración    123 findings · 78 números · 36 duplicados
               73 con relación · 46 sin ella · 10 omisiones (17 CLARA + 8 MUTUA)
vocabulario    19 verbos · 9 sin contenido semántico
frontera       259 huecos, 7 vías ·291 citas, 0 fallos
selftests      relations 27/27 · frontier 12/12 · claims 20/20 · artifacts 14/14
               rx550pm4val PASS · rx550ref PASS
GPU            01:00.0 Lexa PRO rev c7, INTACTA
```

## 7 · LO QUE QUEDA, Y ES QUE ES MENOS DE LO QUE PARECÍA

Las 58 no son 58 decisiones duras. Por número:

| nº de candidatos | aristas | esfuerzo |
|---|---|---|
| 2 candidatos | la mayoría | una lectura porfinding, 2 páginas |
| **3 candidatos** | `045` | 3 lecturas |
| **un origen que nombra el destino** | **ya resuelto** | 0 |

Y la vía que de verdad las cierra no es un criterio: es **escribir la cita por
nombre**. El nombre no es ambiguo aunque su número lo sea, y `079` lo demostró
con la única arista nominal del proyecto.

---

```
RESULTADO DE ITERACIÓN

Entregado:
  criterio multi-candidato de terminos exclusivos, con validacion explicita
  su validacion: 1 caso con respuesta conocida, 0 aciertos, y la RAZON:
    el unico caso con verdad conocida es el que el criterio no necesita
  el metodo NO SE APLICA; sus 28 candidatos se declaran como PISTA

Medido:
  58 ambiguas: 28 con candidato unico por termino exclusivo
               21 con varios candidatos
                9 sin candidato

Retractado por este hallazgo:
  "el criterio no funciona" -- la conclusion era correcta y la RAZON, falsa:
    el primer 0/1 era un bug mio (criterio binario sobre 3 candidatos)

NEXT ACTION:
  Lo que queda con valor, en orden:

  1. LAS 25 ARISTAS CLARA Y MUTUA de 077. 17 CLARA son escribibles sin leer:
     el destino ya declara su parte. Es edicion mecanica, y es lo unico del
     backlog que se puede cerrar entero hoy sin inventar nada.

  2. LOS 20 FINDINGS SIN CABECERA. Anadir la cabecera con los campos que ya
     usan los demas. Mecanico y auditable: tras hacerlo, el recuento de
     "sin ninguna etiqueta" debe ser 0, y ese 0 es la prueba de que se hizo.

  3. UN VERBO DE DEPENDENCIA. 9 de 19 verbos no dicen de que depende un
     finding. Sin uno, la mitad del grafo no afirma nada. Es convencion: hay
     que decidir nombre y semantica ANTES de aplicarlo a 123 hallazgos, y
     aplicarlo despues sin decidirlo seria el mismo defecto que las listas
     cerradas.

  4. LAS 58. Lectura. Y solo tiene sentido hacerlas si antes se decide si el
     grafo va a seguir declarandolas por numero o por nombre. Si por nombre,
     las 58 son un problema de escritura, no de lectura, y se arregla con el
     mismo gesto que las 17 CLARAS: poner el nombre en la etiqueta.

  Ese punto 4 es la decision de fondo, y es la unica que no es tecnica.
```