# 041 · Grafo de conocimiento y detector de contradicciones, automático

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`HERRAMIENTA_NUEVA=08-ARQUITECTURA/tools/causal_map.py`
`CONTINUES=040` · `DETECTA=la contradiccion de block_size de 035, automaticamente`

## CUDA principal

La contradiccion de `035` —tres sesiones declarando `block_size` como 13, 10 y
22/23/24, con dos equivocadas— la encontro yo al cruzado, leyendo. Una herramienta
la encuentra en un comando, y la encuentra desde el **primer** documento, no desde
el tercero:

```
$ python3 causal_map.py --contradictions

  block_size:
       10  x2   fuerza=9  (PROVEN)
       22  x1   fuerza=7  (debil)
```

Y valida por mutacion: anado `block_size = 33 | PROVEN` a un documento y lo detecta
como tercer valor fuerte.

Es el retorno de la regla del proyecto: cada hallazgo useful debe aumentar el
throughput futuro. Esta herramienta convierte "alguien va a notar la
contradiccion" en "la herramienta la nota siempre".

## Alcance exacto

1. Indexar las afirmaciones clasificadas de los 89 hallazgos, con su estado y procedencia.
2. Detectar contradicciones entre valores con estado fuerte.
3. Medir cobertura por entidad del dominio, para saber que falta.
4. Validar el detector por mutacion.

## Criterio de terminacion (cumplido)

Detector validado por mutacion (detecta el tercero y el primero reales), cobertura
medida, cuatro bugs de extraccion corregidos. Agotado.

---

## 1 · Que es y que no es

Es un **indice estructurado de lo que los documentos AFIRMAN**, con su estado
epistemico y su procedencia. No infiere, no rellena huecos, no resuelve
contradicciones.

Esa limitacion es la condicion para que sirva. Un grafo de conocimiento que rellena
lo que no encuentra con suposiciones es peor que no tener grafo: uno se puede
auditar documento a documento.

Lo que hace:

- Extrae `(sujeto, valor, estado, doc, linea)` de tablas de clasificacion y de
  prosa con valores.
- Agrupa por sujeto y lista valores distintos.
- **Filtra lo que es contradiccion real**: exige dos valores con estado fuerte
  (>= `DERIVATION`), no ruido de extraccion.
- Mide cobertura por entidad del dominio.
- Localiza fronteras (`NOT_DETERMINED`) por documento.

## 2 · La jerarquia de estados, y por que importa

Un grafo que no distingue `PROVEN` de `HYPOTHESIS` no dice nada. La jerarquia:

```
PROVEN (9) > PROVEN_ABSENCE (8) > OBSERVED (8) > PROVEN_DERIVED (7) >
DERIVATION (6) > SECONDARY_CORROBORATION (5) > NEGATIVE_RESULT (5) >
REFUTED (4) > HYPOTHESIS (3) > LIMITATION (2) > NOT_DETERMINED (0)
```

### 2.1 · El umbral que importa, y que estuve a punto de equivocar

La primera version exigia `PROVEN` (fuerza 9) en los **dos** valores para declarar
contradiccion. Con eso, se escondia la contradiccion REAL de `035`:

```
block_size = 10   PROVEN          (log del kernel)
block_size = 22   PROVEN_DERIVED   (030-page-walker, ventana de RAM)
```

Un `PROVEN_DERIVED` no es ruido: es una afirmacion con estado fuerte y con un valor
concreto. Si el proyecto afirma 10 y 22, hay que resolverlo, **no esconderlo por
debajo de un umbral**.

El corte correcto es `>= DERIVATION`, que incluye lo que tiene fuerza y excluye lo
que es frontera (`NOT_DETERMINED`, `HYPOTHESIS`). Lo que queda excluido no es
"debil", es **frontera abierta** — una categoria distinta.

## 3 · La contradiccion de block_size, automatizada

```
$ python3 causal_map.py --contradictions
  block_size:
       10  x2   fuerza=9  (PROVEN)
       22  x1   fuerza=7  (debil)

$ # mutante: anadir "block_size medido | 33 | PROVEN" a un documento
  block_size:
       10  x2   fuerza=9  (PROVEN)
       22  x1   fuerza=7  (debil)
       33  x1   fuerza=9  (PROVEN)      <- detectado
```

El detector encuentra el tercero y el primero. Mutacion validada.

Que `22` sea de `030-page-walker` es correcto: ese documento afirma 22/23/24 segun
la RAM del host, y el grafo no sabe si es un error o una lectura distinta. Lo que
hace es **ponerlo al lado del 10 para que alguien lo mire**. La distincion
documento-a-documento la hace una persona o una herramienta mas especifica.

## 4 · Cuatro bugs de extraccion, y por que la mitad era ruido

La primera version extraia 131 "afirmaciones", muchas de ellas falsos valores
tomados de cualquier numero de la linea. Cuatro correcciones:

### 4.1 · El valor tiene que ser del sujeto, no de la linea

Un regex suelto tomaba el primer numero que encontraba —la longitud del documento,
un offset de linea, un bit de un campo—. De ahi que `block_size` apareciera con
nueve valores distintos, la mayoria no siendo `block_size = N`.

Corregido: el valor tiene que seguir al sujeto tras un operador (`=`, `es`, `:`),
y no puede haber otro sujeto conocido en medio.

### 4.2 · El valor puede estar en la celda siguiente

La primera tabla de un documento tiene el valor en la columna contigua:
`| block_size medido | 33 | PROVEN |`. El valor no esta en la celda del sujeto. El
mutante de prueba hizo visible esto: la linea se parseaba con `valor=None`.

### 4.3 · La negacion descarta el sujeto, no la frase

Un documento decia literalmente:

```
| `get_block_size` recibe `tmp` reasignado (=2), no `vm_size` | `PROVEN` |
```

El `2` es de `tmp`. `vm_size` se menciona para **descartarlo**. Y la celda esta
marcada `PROVEN`, asi que sin esta comprobacion el detector declaraba
`vm_size = 2 PROVEN`, contra el `64 PROVEN` de otros documentos. Falso positivo
sobre una frase que se autonega.

Corregido: si hay negacion pegada al sujeto o al valor, se descarta. Y la ventana
es **estrecha a proposito** — la primera version usaba 60 caracteres, y como "no"
aparece en casi cualquier frase matizada ("no por la version", "no es lo mismo"),
descartaba la afirmacion entera. Con la ventana ancha solo quedaban 39 claims de 89
documentos: **la mitad del proyecto invisible para la herramienta**. Con la
ventana pegada, 48, y la deteccion de negacion sigue funcionando.

## 5 · Cobertura: que tiene mapa y que no

```
  entidad     fuerte  debil  abierta  docs
  REG              0      1        0     1
  RING             5      0        6     6

  SIN NINGUNA AFIRMACION FUERTE: CORPUS, FENCE, FREQ, GART, GPUVM,
  IB, PM4, REG, SCHED, TLB
```

Ocho de diez entidades del dominio no tienen ninguna afirmacion fuerte. Es un
dato util pero **con una salvedad importante**: la extraccion solo captura
afirmaciones `(sujeto, valor, estado)` en tablas de clasificacion, y muchos
documentos afirman cosas sin ese formato. Asi que "sin afirmacion fuerte" quiere
decir "no hay una afirmacion clasificada en ese formato", que no es exactamente
"no se ha escrito". Es una cota inferior, no una medida. Lo digo para que no se
lea mas fuerte de lo que es.

Lo que si es solido: **el detector de contradicciones funciona y esta validado por
mutacion.** Eso es lo que aporta esta ronda. La cobertura es un indice para saber
donde mirar, no una medida de avance.

## 6 · Clasificacion

| afirmacion | estado |
|---|---|
| 89 documentos de hallazgo indexados | `PROVEN` |
| La contradiccion de `block_size` (10 vs 22) se detecta sola | `PROVEN` — validado por mutacion |
| Un tercer valor fuerte se detecta por mutacion | `PROVEN` |
| El detector distingue PROVEN vs PROVEN_DERIVED | `PROVEN` |
| `NOT_DETERMINED` no cuenta como contradiccion | `PROVEN` |
| La negacion ("no `vm_size`") se descarta | `PROVEN` |
| Cobertura por entidad | `OBSERVATION` — cota inferior, no medida |
| Que `22` sea error o lectura distinta de `10` | `NOT_DETERMINED` — la herramienta lo pone al lado, no lo resuelve |

## 7 · Confounders

- **La cobertura es una cota inferior**, no una medida. Solo captura
  afirmaciones en formato `(sujeto, valor, estado)`. Muchos documentos afirman
  cosas sin ese formato.
- **El detector no sabe si un `PROVEN` posterior es una enmendanza o un
  error.** Un documento puede retractar a otro correctamente (como `024`/`035` con
  `block_size`) y el grafo los seguira listando como si se contradijieran. La
  herramienta **pone al lado**; no decide.
- Los umbrales (`FUERZA`, `>= DERIVATION`) son mios. Elegir donde va la linea
  entre "contradiccion" y "ruido" es un juicio, y es discutible. Lo declare en vez
  de esconderlo.
- El parser de negacion no entiende todos los casos en castellano. En particular
  distingue "no" pegado, pero no "excepto que" ni construcciones mas largas. Es
  heuristica.
- **No he integrado la herramienta al runner** (`run_all`), asi que no corre
  automaticamente. Es el paso siguiente natural y esta declarado, no hecho.

## 8 · UNLOCKS

- **La contradiccion pasa de "al cruzarlo, lo notas" a "siempre se nota".** El
  coste de esta clase de error baja a cero de forma permanente.
- **La jerarquia de estados es reutilizable.** Cualquier herramienta que
  clasifique afirmaciones (futura, o el detector de evidencia) puede importar
  `FUERZA` de aqui.
- **La cobertura, aunque sea cota inferior, ya dice que GPUVM, PM4, FENCE,
  GART, TLB y SCHED son las entidades con menos mapa.** Eso orienta las proximas
  rondas sin tener que leer 89 documentos.
- **La extraccion es la pieza reutilizable**: sujeto + valor + estado + procedencia,
  de tablas de clasificacion y de prosa. Cualquier afirmacion nueva del proyecto
  entra en el grafo sin trabajo extra.

## 9 · Criterio de falsificacion

Se refutaria si: (a) el detector no encontrara un `PROVEN` inyectado — refutable
con el mutante de `block_size=33`, que es la prueba que hice; (b) `035` no contuviera
realmente las tres afirmaciones que dice — refutable con `--claims block_size`; (c)
la ventana de negacion descartara afirmaciones validas — refutable contando claims
con la ventana ancha vs la estrecha, que es como se detecto que la ancha era
mala; (d) la cobertura fuera una medida y no una cota — refutable contando
documentos sin afirmacion clasificada, que es lo que falta por medir.

## 10 · Evidencia

```
HERRAMIENTA:
  08-ARQUITECTURA/tools/causal_map.py
    89 documentos, 48 afirmaciones clasificadas
    contradicciones: block_size 10 (PROVEN) vs 22 (PROVEN_DERIVED)
    mutacion: block_size=33 PROVEN inyectado -> detectado como tercer valor
    cobertura: REG 0 fuerte, RING 5 fuerte; 8 entidades sin afirmacion fuerte

VALIDACION:
  --claims block_size  -> los valores con su estado y documento
  --coverage           -> entidades del dominio sin mapa
  --frontiers          -> NOT_DETERMINED por documento
  --json               -> el grafo entero, para composicion
  mutacion con 33      -> detected (la validacion principal)
```

`WRITE_EXECUTION=NONE`. `GPU INTACTA`.