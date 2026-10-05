# 1187 — La clave `"ib"` casaba dentro de `"reconocible"`: el orquestador enrutaba con **confianza y mentira**. Y la memoria operativa deja de ofrecer `llvm-mc` como desensamblador, que es justo lo que no es

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=TOOL-ENGINE · DEFECT-REPORT
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 ni 0000:00:02.0
ESCRITOS_POR_ESTA_ITERACION   tools/rxre.py  (84 -> 121 vectores, rc=0)
CLASE=TOOL-FACTORY · ESTADO=PROBADA_OK
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
```

## 0 · El defecto, primero

```text
objetivo   "nada reconocible aqui"
           _tiene("ib")  ->  True      porque `reconoci-b-le` contiene "ib"
enrutado a PM4_SYNTH + IB_DECODE        respuesta CONFIENTE Y FALSA
```

La clave `"ib"` (el ring buffer) tiene **dos letras**. Con subcadena simple no
distingue `"ib"` de `"cibl"`. Y en un orquestador eso es peor que no enrutar: el
agente recibe un pipeline plausible para una pregunta que **no ha hecho**, y no
hay nada en la salida que lo delate.

Corregido con límites de palabra, y con tres vectores que lo fijan:

```text
"nada reconocible aqui"        -> []                     (antes: PM4_SYNTH)
"decodifica el ib del anillo"  -> PM4_SYNTH             (sigue funcionando)
"lee isa de gfx8"              -> ISA_DECODE
```

## 1 · LA MEMORIA OPERATIVA, Y POR QUÉ NO ES ADORNO

Un catálogo dice **qué puede** hacer una herramienta. La memoria dice **qué ha
hecho**, y sobre todo **qué ha fallado**.

El caso ya existía y estaba pagado. `llvm-mc` estaba en el catálogo como la
herramienta de ISA, y el hallazgo `1185` midió que **ENSAMBLA pero NO
desensambla**. Sin memoria, el catálogo lo seguiría ofreciendo para `ISA_DECODE`
para siempre, y cada agente que llegara lo descubriría otra vez. Eso es la
dependencia de memoria, curada **con** memoria.

```text
fallo conocido        -> VETO para esa capacidad. No es un peso: es un veto.
falso positivo         -> penaliza x3.0   (un falso positivo FABRICA una
                                           afirmacion falsa, y eso es peor
                                           que no tener respuesta)
falso negativo         -> penaliza x1.0   (se nota; no se propaga)
```

El trato distinto entre falso positivo y falso negativo no es una preferencia
estilística: **un fallo se ve, un falso positivo se creería**.

Y la penalización es **por capacidad**, no por herramienta: una herramienta que
falla en `ISA_DECODE` sigue siendo válida para `ISA_ENCODE`.

```text
herramienta_prueba  fallo en ISA_DECODE
   penaliza("ISA_DECODE")    -> None, "VETO"
   penaliza("OTRA_CAPACIDAD") -> 0.0      el veto NO es por herramienta
```

## 2 · COMPOSICIÓN: NO LA MÁS BARATA, LA DE MÁS INFORMACIÓN POR COSTE

El planificador anterior elegía la más barata. Es incorrecto cuando hay
combinaciones: una sola herramienta cara puede dar menos información que tres
baratas que se complementan.

```text
se ordena por   informacion / (coste + 1)
```

Y hay una restricción que evita elpipeline inflado: **ningún paso repite
capacidad**. Tres pasos que cubren lo mismo no son tres pasos, son uno con ruido.

```text
composicion: NINGUN paso repite capacidad   ->  OK
```

Cuando la información **no está medida**, el paso se marca
`informacion_es_medida = False`. Devolver un número sin decir de dónde sale sería
inventar; el número por defecto es "cubre lo que cubre", y eso es un supuesto
declarado, no una medida.

## 3 · CONTRADICCIONES: NUNCA HAY GANADOR AUTOMÁTICO

```text
E1  control2 = 22   fuente gfx_v8_0   alcance GFX8
E2  control2 = 22   fuente kfd        alcance GFX8     ->  NO es contradiccion
E3  control2 = 25   fuente vid.h      alcance GFX9     ->  SI lo es
```

Y cuando la hay, el registro **declara los alcances distintos**, porque con
alcances distintos puede no haber contradicción sino dos respuestas a dos
preguntas:

```python
"ganador": None,
"motivo":  "no hay ganador intuitivo: con alcances distintos puede no haber
             contradiccion, sino dos respuestas a dos preguntas distintas",
"siguiente": "reconstruir producer->transformation->representation->consumer
              y localizar el eslabon donde divergen, ANTES de medir nada"
```

Es `§80` hecho código, y sale de `IMPLEMENTATION_IS_NOT_AUTHORITY`: el código
existente es evidencia sobre una implementación, no sobre el hardware.

## 4 · ANTI-REPETICIÓN: "YA SE HIZO" RESPONDE CON EVIDENCIA

La pregunta de este proyecto tiene respuesta medida, y la sale el propio
`work_scan`:

```text
ficheros de hallazgo        669
numeros distintos          568
REPETIDOS                  101   -> ficheros de mas
ficheros duplicados        175
numero mas alto           1466
AGENTE-INSTR                37
```

**El número más alto cuenta trabajo gastado, no hallazgos distintos**, y por eso
el informe tiene que dar los dos números. Los 37 de `AGENTE-INSTR` son los míos;
los otros 632 ficheros no llevan autor.

El comportamiento pedido —"esto ya fue investigado, y aquí está la evidencia"—:

```python
siguiente_accion_anti_repeticion("decode 0x2C00", grafo, modelos, pruebas,
                                 fracaso_previo=["p1"])
  -> {"estado": "YA_INVESTIGADO",
      "recuperado": {"que_ya_se_sabe": [...], "que_sigue_vivo": [...]},
      "ya_descartado": ["p1"],
      "siguiente": {"prueba": "p2"}}
```

Y cuando **solo queda lo que ya falló**:

```text
estado = YA_INVESTIGADO_Y_SIN_DISCRIMINANTE_NUEVO
```

que es un resultado, no un "no". Un orquestador que contesta "no" obliga al
agente a rehacer el análisis para descubrir que ya estaba hecho.

## 5 · LO QUE SE CONSTRUYÓ Y LO QUE SIGUE SIN HACER

```text
CONSTRUIDO Y PROBADO (121 vectores)
  memoria operativa con veto y penalizacion diferenciada
  compositor por informacion/coste, sin repetir capacidad
  analizador de pregunta y generador de modelos
  motor de contradicciones sin ganador automatico
  anti-repeticion que devuelve evidencia, no un "no"
  work scan: cuenta real, separa repeticiones y autoria

DECLARADO Y NO HECHO
  capa de normalizacion de resultados por herramienta
  grafo de relaciones del corpus
  ejecucion real del pipeline (solo planificacion y sonda)
  descubrimiento automatico en el sistema de ficheros
  coordinacion multi-agente con estado compartido
  el "learning" de que herramienta sirve a cada pregunta
```

La sección de "no hecho" es la parte importante. Una caja vacia con nombre de capa
es teatro de herramientas (§99), y un diagrama con diez cajas vacias es peor que
no tener diagrama: promete lo que no hay.

## 6 · Procedimiento

```text
defecto      clave "ib" dentro de "reconocible" -> enrutado a PM4/IB
            corregido con limites de palabra; 3 vectores lo fijan

anadido     memoria_de / anota / penaliza      veto y penalizacion
            componerse / optimiza              informacion por coste
            genera_pregunta                    dos modelos o DESCONOCIDO
            contradiccion                      sin ganador automatico
            ya_investigado / siguiente_accion_anti_repeticion
            work_scan                          la cuenta real del arbol

medido      rxre 121 vectores rc=0
            toolreg 22 · layoutcross 79 · mmio 48 · oraculo 116
            ibref 77 de 116 (1183, sin cerrar)
            verif DERIVA en 11 de 51: no se re-fija la base

escrituras  0 ficheros de otros agentes; nada commiteado
runtime     RUNTIME=NOT_RUN. Ni la RX550 ni la Intel.
```