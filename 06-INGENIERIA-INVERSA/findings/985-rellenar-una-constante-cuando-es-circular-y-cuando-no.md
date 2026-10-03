# 985 · Rellenar una constante con lo que mido hoy: cuándo es CIRCULAR y cuándo es exactamente lo correcto

```text
CLASSIFICATION=DERIVACION+METHOD · TRACK=CORPUS
CORPUS=no aplica: es una regla de método, y se sostiene sobre 982
HARDWARE_SCOPE=amdgpu 1002:699f rev c7 · pahole v1.30 · BTF del módulo en ejecución
WORK_CLASS=READ_ANALYSIS + WRITE_LOCAL
AUTHORIZATION=NONE · GPU INTACTA
AUTORIA=AGENT-04 (RUNTIME/PROBING/FUZZING/ORACLES)
CONTINUES=982, donde se aplicó por primera vez a nueve constantes de dos clases distintas
HALLAZGO=reutilizable en todo preflight, guard, assert y pin de este proyecto
```

## El caso que obliga a decidir

`preruntime.sh` usaba nueve variables que no declaraba. "Arreglarlo" es fácil: leerlas del
sistema y escribirlas. **Eso habría producido un harness que arranca, pasa el preflight y no
comprueba nada.** Y no se habría notado.

La pregunta no es *"¿puedo rellenar la constante?"* —siempre se puede. Es:

> **¿La pregunta que responde la comprobación es la misma que responde la medición que la
> alimenta?**

## Las dos clases

| | **IDENTIDAD DE OBJETIVO** | **LAYOUT DE STRUCT** |
|---|---|---|
| Pregunta | *¿es esta la placa que diseñé?* | *¿el struct se ha movió?* |
| Fuente legítima | un registro **previo** de la identidad | una medición fechada, como **línea base** |
| Rellenar con HOY | **CIRCULAR.** La placa actual siempre «coincide consigo misma». | **NO CIRCULAR.** Fijar hoy es lo que permite detectar el movimiento de mañana. |
| Consecuencia del error | el preflight **siempre pasa**. No protege contra nada. | el guard **no puede detectar nada**, o detecta tarde. |

Lo que las separa no es la cantidad de datos, ni la fuente, ni la confianza: es **la
dirección del tiempo**. Una comprobación de identidad mira *hacia atrás* —"¿esto es lo que
vi antes?"— y por eso su dato tiene que venir de antes. Una comprobación de estructura mira
*hacia delante* —"¿esto sigue como lo dejé?"— y por eso su dato tiene que ser el presente
declarado como pasado.

## Aplicado a EP08, con las nueve constantes

**Clase identidad — 4 constantes, fuentes previas:**

```
TARGET_PCI_SUB_VEN   0x1002   HARDWARE-FINGERPRINT.md:60  +  snapshot 2026-09-19 L84
TARGET_PCI_SUB_DEV   0x0b04   HARDWARE-FINGERPRINT.md:60  +  snapshot 2026-09-19 L84
TARGET_PCI_REVISION  0xc7     HARDWARE-FINGERPRINT.md:59  +  snapshot 2026-09-19 L83
TARGET_MODALIAS      (derivado por composición de las tres anteriores)
```

`TARGET_MODALIAS` merece una fila propia porque es un caso aparte: **no es un dato
independiente**, es una serialización de los otros cuatro. Declararlo y comprobarlo no añade
evidencia: añade **coherencia**. Que el modalias que dice el kernel sea exactamente el que
compone la identidad que comparamos detecta que los cinco campos no se han mezclado mal. Es
menos de lo que parece, y más de lo que no es nada. Por eso el fichero reparado lo dice
explícitamente en vez de dejar que parezca un quinto dato.

**Clase layout — 4 constantes, línea base fechada:**

```
NHWA_OFF_ASIC_TYPE      = $NHWA_ASIC_TYPE_OFFSET   (alias, no un segundo literal)
NHWA_OFF_PCI_SUB_VEN    = 64
NHWA_OFF_PCI_SUB_DEV    = 66
NHWA_OFF_PCI_REVISION   = 72
```

## El detalle que evita el siguiente error

`NHWA_OFF_ASIC_TYPE` se declara como **alias** de la constante que ya existía con otro
nombre, y no como un segundo número:

```bash
readonly NHWA_OFF_ASIC_TYPE="$NHWA_ASIC_TYPE_OFFSET"
```

Dos literales iguales en dos sitios **pueden divergir sin que nada lo note**, y nada lo
notaría: las dos líneas se leen bien, `bash -n` pasa, y el día que diverjan el preflight
dirá que el struct se movió cuando lo que se movió fue una constante. Es el mismo patrón del
`$(NF-1)` de 973, dos niveles más abajo: **el guard que compara contra un valor que él mismo
puede haber cambiado no es un guard**.

## La regla, escrita para reutilizarla

```
Antes de rellenar una constante que una comprobación va a comparar, responder:

  1. ¿La comprobación mira HACIA ATRÁS (¿es esto lo que era?)?
        -> el dato tiene que ser PREVIO y FECHADO. Rellenar con hoy es circular.

  2. ¿La comprobación mira HACIA DELANTE (¿esto sigue igual que cuando lo medí)?
        -> el dato tiene que ser la medición de HOY, DECLARADA CON FECHA como línea base.

  3. ¿El valor se deriva de otros que ya se comparan?
        -> no es evidencia nueva: es COHERENCIA. Declararlo como tal, no como un dato más.

  4. ¿El valor ya existe en el fichero con otro nombre?
        -> ALIAS, no un segundo literal. Dos copias divergen sin aviso.

  Si la respuesta a 1 es que sí, y el dato viene de hoy, la comprobación no comprueba nada.
  Y no se va a notar: va a PASAR.
```

## Por qué importa fuera de EP08

Este proyecto tiene preflights en todas partes: `assert_contract.py`, `drivchain.py`,
`implgate.py`, `govcheck.py`, los `EXPECTED_*` de cada script de kernel, los `*_EXPECTED` de
los experimentos. **Todos tienen constantes cuya procedencia no está escrita.** En la mayoría
de los casos el valor se obtuvo de la máquina que después lo va a comprobar, y eso no es un
error por definición: es un error cuando la comprobación pretende ser una comprobación y no
una observación.

La distinción que salva es la misma que el proyecto ya usa en otro sitio: un PIN fechado es
un artefacto; una constante rellenada del entorno es una **observación disfrazada de
constante**. Se distinguen por una sola cosa: **si tiene fecha y hash, o no**.

```
LIMITACION  Regla de método, no medible en este nodo. Lo que se ha hecho es aplicarla a
            nueve constantes y comprobar que el resultado se sostiene: 982 es la prueba.
            Lo que NO se ha hecho — y es lo siguiente — es un censo de las constantes del
            resto del proyecto por esta misma clasificación. Ese es un nodo aparte.
```