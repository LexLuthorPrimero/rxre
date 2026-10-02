# 114 · La herramienta que audita mis propias marcas encontró cinco bugs propios y uno de ellos era una afirmación falsa

`CLASSIFICATION=METHODOLOGY` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=OWN_DRIVER_ONLY` · `MODIFICATIONS_CORPUS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`HERRAMIENTA_NUEVA=tools/implgate.py` (`TOOL_VALIDATED`, 18 vectores)
`CONTINUES=113` · `IMPLEMENTA=AGENTS.md §IMPLEMENTATION_GATE (748-760)`

## Cuestión principal

`AGENTS.md` 748-760 exige, antes de implementar:

```
REQUIREMENT → EVIDENCE → SEMANTICS → REPRESENTATION
→ HARDWARE_EFFECT → CONTRACT → TEST
```

y prohíbe implementar una semántica «sólo porque existe en AMDGPU». La
cláusula operativa es la última: *«si alguna parte sigue `NOT_DETERMINED`,
marcarla explícitamente»*. Una marca explícita es auditable sin opinión. ¿Lo
cumple el driver propio?

## Criterio de terminación

Para cada función de emisión: ¿lleva marca de estado de evidencia, y la
marca que lleva es vigente? **Cumplido: 22 funciones, 17 con marca, 5 sin
marca, 0 marcas caducadas.**

## Respuesta

```
funciones reales            22     (no 29: 7 filas eran prototipos)
con marca                   17
  PROVEN / PROVEN_DERIVED   16
  NOT_DETERMINED             7   (pueden solaparse con los anteriores)
sin marca                    5
NO VERIFICABLES (cita ambigua) 7
CONJUNCIONES A REVISAR        1
marcas caducadas probadas    0
```

Las 17 con marca son correctas y **actuales**: `rx550_pm4.c:140` sigue
diciendo que *por qué* amdgpu no cuenta el iniciador como payload es
`NOT_DETERMINED`, y `095` probó el *qué* (`count = payload − 1`, 48/48) sin
cerrar el *por qué*. El driver no se quedó atrás.

## Lo que la herramienta encontró en sí misma

Cinco defectos, todos **míos**, todos de la misma familia: una comprobación
que parecía funcionar porque devolvía un valor plausible.

### 1. Un `0` que era un bug, y que se leía como resultado bueno

`bloque_comentario` arrancaba en `i = ini - 1`, o sea en la línea de la
**definición misma**, que no empieza por `/*`. Rompía en la primera
iteración y devolvía cadena vacía: las **29 funciones salían «SIN MARCA»**.
Lo cazó el selftest con un vector de 8 líneas. Número falso: 29 sin marca en
lugar de 0 con marca. El detalle está en `072`-ancla y `075`-rangos: la
misma forma, sexta vez.

### 2. Resolución de citas por posición alfabética — el defecto de `048`, Cometido otra vez

`cerrada_en()` tomaba `sorted(os.listdir(d))` y devolvía el **primer**
fichero que casaba con el número. `048-numeros-de-hallazgo-no-identifican.md`
ya mide que **58 de 106 números no identifican un documento**, y que **72
documentos son alcanzables sólo por su posición alfabética**. El defecto
creció: `048` lo midió en **37 duplicados sobre 82 números**; hoy son **58
sobre 106**.

No lo corregí yo. Lo corrigió **un agente**: cito `findings/039` para la
semántica de `gfx_v8_0_emit_mem_sync` y leyó
`039-cierre-de-includes-resolucion-real.md`, cuando el texto estaba en
`039-coherencia-ib-si-existe.md`. Es el mismo error de `048` —«encontré el
error cometiéndolo»— hecho a mano y por un lector distinto.

**Corrección**: un número ambiguo ya **no se resuelve**, se declara
`AMBIGUO(n)` con la lista. Elegir el primero produce un `PROVEN` plausible
del fichero equivocado, que es peor que no resolver porque no se ve. Y el
regex de cita pasó a capturar el slug: `findings/039-coherencia-ib-si-existe.md`
sí resuelve, `findings/039` no.

### 3. Confundí «caducada» con «no resoluble» — y acusé al código

Corregido (2), 11 citas salieron `AMBIGUO`. Mi clasificación las contaba como
**MARCAS CADUCADAS**: es decir, acusaba al driver de afirmar una prudencia
caducada cuando lo que ocurría es que yo no había podido resolver dónde
mirar. Un número ambiguo no es una caducidad: no se ha resuelto nada, así que
no se puede afirmar nada. Son dos clases distintas y ahora se imprimen
distintas, y las ambiguas **no hacen fallar el gate**: un gate que falla por
indeterminación deja de ser informativo.

### 4. «Caducada» tampoco era decidible — y el caso real lo demuestra

Quedó **una** conjunción, y es falsa: `rx550_sdma_vm_set_pte_pde` dice
`NOT_DETERMINED` **del hardware** y cita `034`, que dice `PROVEN` **del
driver de referencia**. El propio comentario lo escribe: *«the choice is
PROVEN_DERIVED from the reference driver, not PROVEN about the hardware»*.
Dos sujetos distintos que comparten prefijo. Que la coincidencia sea una
caducidad exige que ambos hablen de lo mismo, y el sujeto **no se lee de una
palabra**. El veredicto pasó a `CONJUNCIONES A REVISAR` e imprime la frase del
comentario, que la hace juzgable de un vistazo. **Es la cuarta vez que
confundo dos cosas que comparten prefijo.**

### 5. Prototipos contados como definiciones — 24 % de inflación

`if not m or l.rstrip().endswith(";"): continue` miraba **sólo la línea
actual**. Los prototipos de `rx550_pm4.h` que no caben en una línea terminan en
`,` en su primera línea, no en `;`, y pasaban como definiciones. Eran
exactamente 7, y son exactamente las 7 filas duplicadas. El discriminador
correcto es el terminador del **primer `;` o `{`** al avanzar, no el de la
primera línea: `es_prototipo()`.

**29 filas = 22 definiciones reales + 7 fantasmas.** Con el filtro viejo,
`rx550_pm4_write_data` salía dos veces, una `PROVEN_DERIVED` (línea 681, la
definición) y una `SIN MARCA` (línea 314, el prototipo). Era el mismo par en
dos ficheros, indistinguible porque la tabla **no imprimía el fichero**.

## La afirmación falsa de mi propia herramienta

El veredicto decía, en mayúsculas:

```
  SIN MARCA DE EVIDENCIA: 15
  Cada una emite paquetes al hardware sin declarar de donde sale la semantica.
```

**Es falso para este árbol, y es la parte más seria de este hallazgo.** En
`07-DRIVER/kernel/` no hay ni un `writel`, ni un `ioremap`, ni un `iowrite`:
cero. Las funciones escriben dwords en un buffer de **RAM que pasa el
llamante** (`struct rx550_pm4_ib.buf`), no en la GPU. Lo dice el propio driver
en `rx550_drv.c:23-24`:

> *"No lee ni escribe ningún registro de la GPU. Por eso probe() no toca MMIO
> en absoluto: ni siquiera para leer el ASIC id."*

Medido por un agente, no supuesto por mí. Una herramienta que afirma algo
falso sobre su propio objeto es peor que una que no afirma nada, porque su
salida se lee como si estuviera medida. Y era exactamente la forma que este
proyecto lleva 100 hallazgos previniendo: un número plausible sin un valor
competidor al lado que lo contradiga.

También corregí: el vocabulario de estados no incluía `OBSERVED`,
`CORROBORATED`, `CORRECTION`, `MODEL_CHOICE`, `DEFERRED` ni
`NOT_APPLICABLE`, que son estados válidos del modelo epistémico de
`AGENTS.md` y que el propio driver ya usaba — `rx550_pm4.c:63` dice
*«is OBSERVED from the macro and the binary»* y la herramienta lo marcaba
`SIN MARCA`.

## Lo que encontró en el driver: una contradicción entre `.h` y `.c`

Al marcar las funciones aparecieron 11 sitios sin evidencia propia. Uno era
una **contradicción interna**:

```
rx550_pm4.h:462   A count of 0 is rejected and writes nothing, because the
                  encoding is count - 1 and 0 - 1 would be 0xFFFFFFFF,
                  i.e. 4 G entries.

rx550_pm4.c:272   findings/034 read sdma_v4_0.c and "corrected" it to
                  `count - 1` -- wrong, and wrong in the dangerous direction...
                  So this writes `count`.
```

La cabecera conservaba el texto de `034`, que el `.c` **retracta
explícitamente** en el mismo driver. Un hallazgo retractado seguía vivo en la
cabecera, y la cabecera es lo que se lee antes de usar la función: el lector
recibe la regla equivocada y no tiene forma de saber que lo está.

Corregido con sección `CORRECCION 1.0.0` en la `.h`, quoting el texto viejo y
atribuyéndolo a `034`. **La regla de rechazo del 0 no cambia por el error** —
un 0 no es una petición con significado — lo que cambia es el motivo, y el
motivo anterior era falso.

## Lo que queda abierto

| afirmación | estado |
|---|---|
| 22 funciones reales, 17 con marca, 5 sin | `MEASUREMENT` — `implgate.py` |
| 0 marcas caducadas probadas | `MEASUREMENT` |
| 58 de 106 números no identifican un documento | `MEASUREMENT` — `num_collision.py`, crece desde 37/82 en `048` |
| Ninguna función del driver escribe en la GPU | `MEASUREMENT` — 0 `writel`/`ioremap`/`iowrite` |
| Las 5 sin marca sonTrivia y no semántica | `NOT_DETERMINED` — exige leer el cuerpo; la herramienta **no lo afirma** |
| 7 funciones reales invisibles al regex (`long`, `ssize_t`, `const char *`, `int __init`, `void __exit`) | `MEASUREMENT` — `rx550_main.c` completo no aparece en la tabla |
| Los 11 codificadores no tienen consumidor en el kernel | `MEASUREMENT` — `rx550_drv.c` y `rx550_main.c` no incluyen `rx550_pm4.h`; el ioctl es `-ENOSYS` |
| Que el formato de `SET_SH_REG` sea `NOT_APPLICABLE` en esta placa | `PROVEN` — `gfx_v8_0.c:1485`, gate `!= CHIP_CARRIZO` |

## Confounders

- **El recuento depende del directorio.** `findings/` tenía 128 documentos
  cuando `048` midió; hoy tiene 178. Los 58 duplicados son una cota inferior.
- **`es_prototipo()` es un heurístico de 40 líneas de adelanto.** Un prototipo
  partido de forma distinta podría pasar por definición. El selftest cubre los
  cuatro casos reales de `rx550_pm4.h`, no todos los posibles.
- **Las 7 «conjunciones a revisar» son judgement calls.** La herramienta
 nouce que son; no las resuelve, y no debe.

## Lo que esta ronda deja escrito en el código

11 marcas insertadas, cada una citando el **nombre completo** del hallazgo
(`039-coherencia-ib-si-existe.md`, no `039`), y con `NOT_DETERMINED`
subordinado explícito donde la emisión es `PROVEN` y el alcance no lo es. El
inserter es idempotente y verifica toda cita contra el árbol antes de
escribir: un nombre de hallazgo inventado aborta el script, porque una marca a
medias es peor que ninguna — parece completa.

## Procedencia de esta ronda

Tres agentes en paralelo, **sólo lectura**: dos mapeando evidencia→función
sobre grupos disjuntos, y uno auditando la herramienta. Escribir ellos y
leerlos yo, para que no hubiera ediciones concurrentes sobre el mismo fichero.

**Dos veces cometí el mismo error de método**: el backup de `rx550_pm4.c` lo
tomé **después** de marcar, así que mis dos "restauraciones" devolvieron la
versión con marcas; y al borrar por índice lo hice en orden ascendente, que
desplaza los índices siguientes y me borró líneas de código reales
(`34385 B` frente a `34569 B`, y 5 errores de compilación). Recuperé desde el
backup, **verifiqué compilación y tests antes de seguir**, y reconstruí la
línea base con una condición comprobable: **34569 B exactos**, `/*` = `*/` =
34, cero `EVIDENCIA`. De ahí la regla que dejé escrita en el script:

> *Un criterio de inserción que puede meter texto dentro de código no es un
> criterio: es una apuesta.*

`WRITE_EXECUTION=OWN_DRIVER_ONLY`. `MODIFICATIONS_CORPUS=0`: el árbol de
Linux 7.2.8 no se ha tocado. `GPU INTACTA`.
---

# CORRECCION POSTERIOR — la misma cita, resuelta por el numero que este hallazgo denuncia

Este documento **no se reescribe**. Lo que sigue corrige la linea 43, que es
una cita ambigua resuelta por el metodo que este mismo hallazgo califica de
defectuoso. LoFound un agente, y no por leer con cuidado: por citar por
numero.

## Lo que dice la linea 43, sin tocar

```
`NOT_DETERMINED`, y `095` probó el *qué* (`count = payload − 1`, 48/48) sin
```

## Los dos errores

**1. `095` no es un hallazgo: son tres.**

```
095-camino-termico-y-un-assert-inerte.md          count=0  payload=0
095-los-5-sin-medir-y-los-2-limite-reconcilian.md  count=23 payload=18
095-se-pfp-me-ce-tres-motores-tres-icache.md       count=0  payload=0
```

Dos de los tres **no mencionan `count` ni `payload` ni una vez**. El que lo
demuestra es el segundo, y es el que queria citar. `095` a secas no
selecciona ese documento: selecciona el primero en orden alfabetico, que es
justo el defecto que la seccion "Lo que la herramienta encontro en si misma",
punto 2, dice haber arreglado.

**2. `48/48` no aparece en ninguna parte.**

```
095-los-5-sin-medir-y-los-2-limite-reconcilian.md:1    titulo  45/45
                                          :21          "en 43 de 43"
                                          :117         43/50 -> 45/45
                                          :125         "45 de 45 emisiones"
```

El 48 es una cifra de otro sitio: la suma de las dos vias de medicion del
proyecto (45 automatizadas y 3 a mano), que es correcta **como total del
proyecto** y falsa **atribuida a este fichero**. Atribuir a un documento una
cifra que pertenece a otro es el mismo error que atribuir a un numero un
documento que no es.

## Que queda affirmed en su lugar

`findings/095-los-5-sin-medir-y-los-2-limite-reconcilian.md` sostiene
`count = payload − 1` en **45/45**, y sobre eso
`038-validador-flujo-y-regla-del-count.md:42` declara **caducado** el
`NOT_DETERMINED` que `rx550_pm4_dispatch_direct` afirmaba en su comentario.

Consecuencia que **si** cambia el veredicto de este hallazgo: el driver ya no
esta al dia ahi. Su comentario de `dispatch_direct` sigue diciendo que el
desajuste es `NOT_DETERMINED`, y `038:42` dice que no lo es. Corregido en el
codigo con la marca `NOT_DETERMINED CORREGIDO`, que retira la afirmacion y
cita a `038-validador-flujo-y-regla-del-count.md:42` y a
`095-los-5-sin-medir-y-los-2-limite-reconcilian.md:200-203`.

**La ironia no es adorno.** El parrafo 2 de este hallazgo explica que un
numero no identifica un documento, y el parrafo 1 de este mismo documento cita
por numero. No lo detecto yo: lo detecto el mismo criterio que construi, en
las manos de otro.

## Y la segunda contradiccion .h/.c, que la herramienta si encontro

`tools/hcconsist.py` — creado despues de escribirse esto — cruza las cifras
documentadas a ambos lados de cada funcion. De 9 pares comparables dio 4
discrepancias, **1 real** y 3 ruido:

```
rx550_pm4.h:381   rx550_pm4_indirect - reference an IB from the ring, SEVEN dwords.
rx550_pm4.c:459   rx550_pm4_indirect - reference an IB from the ring, SIX dwords.
```

La autoridad es el validador, `07-DRIVER/tests/test_pm4.c:728`:

```c
check_eq("indirect emits 6 dwords, not 7", (uint32_t)ib.length_dw, 6u);
```

**Seis es correcto. La cabecera estaba mal.** Y el nombre del test dice
literalmente *"not 7"*: este error exacto ya se Habia cazado una vez, se
corrigieron el `.c` y el test, y **la cabecera no se actualizo**. Un error
resucitado en el fichero que nadie vuelve a leer, que es donde mas confianza
da y donde menos se mira.

Las otras 3 discrepancias del cruce eran ruido de mi extractor, no del codigo:
`dispatch_direct` (la `.h` no declara recuento, el 5 salia de otra frase),
`event_write` y `ring_submit` (el extractor leyo "both" y "own"). Se declara
aqui para que el 1 de 4 no se lea como un acierto del 100%.

## Clasificacion anadida

| afirmacion | estado |
|---|---|
| `095` esta duplicado en tres documentos | `MEASUREMENT` |
| Dos de los tres no mencionan `count` | `MEASUREMENT` — 0 ocurrencias |
| `48/48` no aparece en el fichero citado | `MEASUREMENT` |
| El `NOT_DETERMINED` de `dispatch_direct` esta caducado | `PROVEN` — `038:42` + `095:...-reconcilian.md:117` |
| `indirect` son 6 dwords, no 7 | `PROVEN` — `test_pm4.c:728` |
| La `.h` afirmaba 7 | `REFUTED` por el validador |
| Que el cruce de cifras detecte contradicciones semanticas | `NOT_DETERMINED` — solo numericas; la de `count - 1` le habria pasado |

`CORRECTED_BY=114-CORRECCION-POSTERIOR`. La linea 43 se conserva intacta.
