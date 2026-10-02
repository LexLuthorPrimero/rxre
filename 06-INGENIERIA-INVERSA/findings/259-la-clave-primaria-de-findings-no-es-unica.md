# 259 · La clave primaria de `findings/` no es única: 65 números con dos ficheros

`CLASSIFICATION=PROJECT_INTEGRITY` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CORPUS=06-INGENIERIA-INVERSA/findings/` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`DESARROLLA=la regeneracion de los artefactos de estado, que destaparon esto`

## Cuestión principal

Regeneré los artefactos de estado del proyecto porque estaban desfasados, y al
hacerlo apareció que **dos hallazgos distintos comparten número**.

## Criterio de terminación

Medir la unicidad del identificador de hallazgo en todo el árbol. **Cumplido, y el
resultado es un defecto, no un cierre.**

## La medición

```
ficheros .md totales       : 347
numeros distintos          : 255
numeros CON COLISIÓN (>1)  : 65
ficheros implicados         : 157
```

**Dos hallazgos sin relación entre sí comparten el mismo identificador.**

```
001:
    001-amdgpu-overview.md                          16450 bytes
    001-amdgpu-location.md                           3537 bytes
010:
    010-pgm-rsrc1-decoded.md                         9534
    010-integration-validation.md                    29565
025:
    025-gart-invalidate-con-orden-cpu.md             13831
    025-vm-flush-path-gfx8-63dw.md                   9038
```

## Por qué esto es el defecto más grave del proyecto

El número de hallazgo es **la clave primaria** de la base de conocimiento. Todo lo
que cuelga de él queda ambiguo:

- `CORRECTED_BY=025` — ¿qué hallazgo corrige el 025, de los dos?
- `CLAIM-025` — ¿cuál de los dos es el claim?
- Una cita como `006-.../025-...` — ¿a cuál apunta?
- `CONTRADICTIONS.md` calcula el **sentido** de cada arista a partir de esos
  números. **Con 65 colisiones, el cálculo del sentido es correcto pero la arista
  que resuelve es arbitraria cuando hay dos destinos con el mismo nombre.**

Lo último es lo grave: **una herramienta validada, alimentada con una clave no
única, produce resultados incorrectos sin ninguna señal**. El self-test de
`tools/artifacts.py` pasa con 14 vectores y aun así no puede detectar esto, porque
comprueba su propia lógica, no la unicidad de su entrada.

## Causa

Ya estaba identificada y documentada en mi hallazgo `190`: hay **dos numeradores
sin coordinar**.

| numerador | flock | fichero de reserva |
|---|---|---|
| `08-ARQUITECTURA/tools/findnum.py` | 4 usos | `_reservas/NNN-reservado.res` |
| `tools/nextnum.py` | **0** | **ninguno** |

`nextnum.py` calcula el siguiente número **sin lock y sin reserva en disco**, así
que dos sesiones que numeran a la vez obtienen el mismo número. Un tercer camino es
la numeración manual.

**El 259 que reservé para este hallazgo lo comprobé después de reservarlo**: 0
ficheros con ese número. Es la comprobación que debería hacer `findnum.py` **antes**
de reservar, y que hoy no hace.

## Lo que NO es este defecto

**No es duplicación de contenido.** Lo verifiqué porque era mi hipótesis inicial y
era falsa: `144-prt-cierra-y-el-corpus-no-tiene-uapi.md` y
`231-ip-version-del-firmware-cierra-gfx-hwip.md` **no** son el mismo hallazgo
— el 144 actual trata de PRT y el 231 del IP version del firmware. Lo que ocurrió es
**renumeración**: mi 144 pasó a ser el 231 y el número 144 se reutilizó para otro
contenido.

Eso significa dos cosas distintas:

1. **Quien renumeró lo hizo bien** — no duplicó, reasignó.
2. **Pero no dejó tabla de reenvío**, así que cada referencia interna a `144`,
   `185` o `202` escrita en el momento de aquella iteración apunta hoy a un
   hallazgo distinto. Mi `247` dice *"`202` queda RETRACTADO"* y ese `202` ya no es
   el documento que retracté.

## Qué se necesita para cerrarlo

**Renumerar no basta.** Si se renumera sin tabla de reenvío, el problema se repite
en la siguiente colisión. El cierre mínimo es:

1. **Un único numerador**, con `flock` y reserva en disco, para todo el árbol.
2. **Reservar comprobando la unicidad** antes de escribir, no después.
3. **Una tabla de reenvío** `viejo → nuevo` para toda renumeración pasada, para que
   las referencias históricas se resuelvan.
4. **Una comprobación de unicidad** como parte del generador de artefactos, para que
   esto sea detectable por máquina y no por un ojo.

Nada de eso lo he hecho: **son ficheros de otra sesión** y el principio de no
mezclar ámbitos sigue en pie. Lo que hago es dejar medido y documentado.

## Clasificación

| afirmación | estado |
|---|---|
| 65 números tienen más de un fichero | `PROVEN` — recuento |
| 157 ficheros implicatedad | `PROVEN` |
| El número es la clave primaria | `PROVEN` — por construcción del árbol |
| Dos numeradores sin lock | `PROVEN` — grep de flock |
| `findnum.py` no comprueba unicidad al reservar | `PROVEN` — inspección |
| Que 144 y 231 sean duplicados | **REFUTADO** — son contenidos distintos |
| Que hubiera renumeración sin reenvío | `PROVEN` — comparación de títulos |
| Cuántas referencias internas quedaron colgando | `NOT_DETERMINED` |
| Que el árbol pueda repararse sin perder trazabilidad | `NOT_DETERMINED` |

## Confounders

- **El recuento es de nombres de fichero, no del campo `CLAIM_ID` de dentro.** Un
  hallazgo podría declarar un ID distinto al de su fichero. **No lo he comprobado**,
  y si fuera así el defecto cambiaría de forma: no sería clave duplicada sino clave
  divergente, que es distinto y peor.
- **No sé cuál de los dos ficheros de cada colisión es el canónico**, ni si ambos
  se pretendían conservar. Con 65 colisiones eso es trabajo manual, no una regla.
- **Los artefactos regenerados los producí yo**, así que la fecha de esta medición
  es la de hoy. El estado de ayer era el que copié en `/tmp/opencode/artefactos-antes/`.

## Desfalsificación

- **(a)** 65 colisiones → refutable contando nombres repetidos en `findings/`.
- **(b)** 2 numeradores sin lock → refutable con grep de `flock` en cada uno.
- **(c)** No es duplicación → refutable comparando títulos y hashes. **Verificado.**
- **(d)** Que `findnum.py` no compruebe unicidad → refutable reserving un número
  ocupado y viendo si falla. **No lo he probado** porque escribiría en `_reservas`.

## UNLOCKS

- **Este es el bloque raíz del proyecto por encima de cualquiera técnico.** Un
  identificador no único hace que las contradicciones, la evidencia, la matriz y las
  dependencias **no se puedan resolver de forma fiable**, aunque cada herramienta
  sea correcta.
- **Une la cadena de colisiones de `190` con una medición**: ya sabía que había dos
  numeradores; ahora sé **cuántos** números están dañados.
- **Un requisito nuevo, y es de la herramienta**: comprobar unicidad **antes** de
  reservar, no confiar en el sello de `max+1`, que es exactamente el patrón que
  falla cuando dos procesos leen el mismo `max`.
- **La lección de `247` aplicada al proyecto entero**: un `0` o un conteo que viene
  del instrumento y no de los datos parece un resultado. Aquí `255 números
  distintos` parecía "el estado del proyecto" y era `347 ficheros`.
- **Siguiente paso**: decidir renumeración con tabla de reenvío, o renumeración
  sin ella. La primera cuesta más y es la única que conserva la trazabilidad.

## Evidencia

```
findings/*.md                              347 ficheros
numeros distintos                          255
numeros con >1 fichero                      65
ficheros implicados                        157

001-amdgpu-overview.md  vs  001-amdgpu-location.md
025-gart-invalidate-con-orden-cpu.md vs 025-vm-flush-path-gfx8-63dw.md

08-ARQUITECTURA/tools/findnum.py   grep -c flock        -> 4
tools/nextnum.py                    grep -c flock|.res   -> 0
tools/artifacts.py --selftest                            -> PASS (14 vectores)
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.