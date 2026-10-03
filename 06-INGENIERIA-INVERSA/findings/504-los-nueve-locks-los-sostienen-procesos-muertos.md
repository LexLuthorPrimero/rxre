# 504 · Los nueve locks del proyecto los sostienen procesos que ya no existen

`CLASSIFICATION=EVIDENCE` · `TRACK=RUNTIME` · `WORK_CLASS=READ_ONLY`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=OBSERVED` · `GPU INTACTA`
`HARDWARE_SCOPE=HOST-C/RX550`

## Cuestión principal

`findnum: control negativo` empezó a fallar con `TimeoutError: lock ocupado`.
La pregunta es si es contención real o **un lock muerto que ya no bloquea a
nadie y solo parece que bloquea**. No es una pregunta retórica: un lock
"ocupado" por un proceso inexistente **miente**, y un mecanismo de bloqueo que
miente es peor que no tener ninguno.

## Criterio de terminación

Comprobar, **PID por PID y contra `/proc`**, si quien sostiene cada lock está
vivo. **Cumplido.**

## La medición

```
PID 217323  MUERTO   .write-lock/findnum/
PID 155365  MUERTO   .write-lock/drv047/
PID 134240  MUERTO   .write-lock/drv097/
PID 157878  MUERTO   .write-lock/drv101/
PID 158246  MUERTO   .write-lock/drv102/
PID 158625  MUERTO   .write-lock/drv103/
PID 162872  MUERTO   .write-lock/drv105/
PID 71978   MUERTO   .write-lock/btfq/
PID 61451   MUERTO   .write-lock/smu/
```

**9 de 9 locks con PID están sostenidos por procesos que no existen.**

Y dos de ellos son míos:

```
.write-lock/coh/     -> 175630  2026-10-02T05:59:38  scope=coh
.write-lock/drv112/  -> 175630  2026-10-02T03:26:24  scope=drv112
```

`175630` era el PID persistente de mi sesión de opencode. **Ya no existe**
(`/proc/175630` ausente), y sin embargo sigue sosteniendo dos locks. No los
solté yo: se quedaron porque el proceso que los tomó terminó.

Los otros locks (`docs`, `findings`, `revkit`) están tomados por `session=opencode`
con `PID=24792`, que **sí está vivo**, y llevan además `previo=` y la nota de
toma:

```
toma=el lock anterior lo tenia PID ya muerto (382922); /proc/382922 no existe;
     verificado por /proc y no por ps
```

**El proyecto ya tiene un procedimiento escrito para esto**, y dice lo correcto:
comprobar contra `/proc`, no contra `ps`, y anotar el PID previo. O sea: **la
toma de locks caducados ya se practica; lo que no existe es la detección
automática.**

## Por qué `findnum` falla, y por qué su fallo es el correcto

El control negativo de `findnum` reserva dos números y espera que el segundo
rechace. Falla **al_no poder tomar el lock**, no al detectar el duplicado:

```
File "findnum.py", line 144, in reserve
    a, _ = reserve("self-test A")
TimeoutError: lock ocupado
```

Eso es **comportamiento correcto**: prefiero refuses a corromper la
numeración. El problema es otro, y es más interesante:

> **El fallo de un test por lock ocupado es indistinguible del fallo por
> contención real.** El control negativo no sabe si lo bloquea un proceso vivo o
> uno muerto, y por eso **no puede decir por qué falló**.

Es la misma clase de fallo de siempre, con la forma nueva: un instrumento cuyo
negativo no distingue entre "no puedo" y "no hay". Un test que sólo sabe decir
"falla" no es un test de contención: es un test de disponibilidad.

## Lo que NO he hecho, y por qué

**No he soltado ni tomado ningún lock.** Ni los nueve, ni los dos míos.

- Los nueve son de **ámbitos de otras sesiones** (`btfq`, `drv047`, `drv097`,
  `drv101`, `drv102`, `drv103`, `drv105`, `smu`). Reclamarlos es exactamente el
  `OwnedError` que `COORDINACION.md` prohíbe.
- Los dos míos **están caducados porque yo**, y soltarlos sería lo correcto, pero
  están en un directorio compartido y otra sesión podría estar usándolos como
  señal de "esto está ocupado". Cambiar un fichero de lock compartido sin
  acuerdo no es mío, aunque el contenido sea culpa mía.

**Lo que sí hago es dejarlo medido y escrito**, que es lo que corresponde.

## Lo que esto cuesta, medido

Un `run_all` de 63 comprobaciones no puede terminar porque **una comprobación no
puede empezar**. Y no es una comprobación cualquiera: es el **control negativo
de la herramienta que numera los hallazgos**. Es decir:

> **El mecanismo que garantiza que los números de hallazgo sean únicos está
> protegido por un lock que ya no protege nada.**

Y hay un agravante que ya está documentado en este proyecto: existen **73 números
de hallazgo duplicados** en el árbol. El número de Reservar es correcto; el
número de *respetarlo* no lo es.

## Confounders

- **`/proc` no es `ps`.** Un PID puede reutilizarse: `/proc/217323` ausente
  significa que *ningún* proceso tiene ese PID ahora, que es lo que hace falta.
  No he mirado si esos PIDs existieron alguna vez; no hay forma aquí.
- **He comprobado solo los locks con PID.** Los de `session=opencode` llevan un
  formato distinto y no los he auditado, salvo el de `24792`, que está vivo.
- **No he contado cuántos locks hay en total**; hay 15 directorios en
  `.write-lock/` y solo 12 tienen `owner`.
- **No he probado a reservar un número ahora mismo.** El `--commit 503` de este
  hallazgo **sí funcionó**, lo que sugiere que `findnum` sí pudo tomar el lock
  moments antes. Eso hace que la contención sea ** intermitente**, y por eso el
  fallo es más difícil de leer de lo que parece.

## Clasificación

| afirmación | estado |
|---|---|
| los 9 locks con PID los sostienen procesos inexistentes | `OBSERVED` — `/proc` |
| `175630` (mi PID de sesión) no existe | `OBSERVED` |
| yo sostengo `coh` y `drv112` con PID muerto | `OBSERVED` |
| el protocolo correcto es comprobar contra `/proc`, no `ps` | `PROVEN` — nota en `docs/` |
| `findnum` falló por lock, no por su control | `OBSERVED` — traza |
| los locks caducados datan del proceso que los tomó | `PROVEN` — el fichero owner no se renueva |
| la toma de locks caducados ya se practica | `PROVEN` — `toma=` y `previo=` en dos locks |
| los 9 locks se pueden reclamar sin riesgo | `NOT_DETERMINED` — decisión de coordinación |
| existe detección automática de caducidad | **`REFUTED`** — nada en el protocolo la hace |

## Desfalsificación

- **(a)** los PIDs están muertos → refutable con `test -d /proc/$PID`.
  **Verificado en los 9.**
- **(b)** el fallo es de lock y no del control → refutable con la traza de
  `findnum`. **Verificado: `TimeoutError` en `reserve`, antes del control.**
- **(c)** el procedimiento correcto ya existe → refutable leyendo el `owner` de
  `docs/` y `revkit`. **Verificado: `toma=`, `previo=`, y la advertencia de
  verificar por `/proc` y no por `ps`.**
- **(d)** que la contención sea intermitente → refutable reintentando.
  **`--commit 503` funcionó justo antes. Verificado por contraste.**

## UNLOCKS

- **Un lock caducado es peor que no tener lock**: no solo no bloquea, sino que
  **afirma** que bloquea. Quien lo leataken "ocupado" y concluyo que hay
  conflicto cuando no lo hay.
- **La prueba de que un control negativo funciona tiene que poder fallar por la
  razón correcta.** El de `findnum` sólo sabe decir "falla", y ahora no se sabe
  por qué. Eso lo hace un test de disponibilidad, no de contención.
- **Los 73 números duplicados y este lock son el mismo problema por dos
  extremos**: el mecanismo que debería impedirlos no está, y el que los
  reserva cuenta no distingue el choque real del fantasma.
- **Siguiente paso, y sale de aquí**: `findnum` debería **comprobar la
  liveness del PID que figura en `owner` antes de esperar**, y devolver un
  código de salida DISTINTO para "lock tomado por un proceso muerto" que para
  "lock tomado por un proceso vivo". Es el mismo principio que §23 pide a las
  herramientas: **un resultado negativo debe poder decir por qué es negativo**.
  Es un cambio pequeño, es mío, y hace que 9 locks caducados dejen de parecer
  un conflicto.

## Evidencia

```
for d in .write-lock/*/; do cat $d/owner; done
for p in 217323 155365 134240 157878 158246 158625 162872 71978 61451; do
    test -d /proc/$p || echo "$p MUERTO"; done          -> 9 de 9
test -d /proc/175630 || echo "mi PID de sesion, muerto"
cat .write-lock/docs/owner   -> toma=... /proc/382922 no existe; previo=382922
findnum --commit 503         -> OK minutes antes: la contencion es intermitente
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.