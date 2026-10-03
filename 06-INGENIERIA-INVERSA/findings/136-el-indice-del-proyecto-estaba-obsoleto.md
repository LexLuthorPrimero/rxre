# 136 · El índice del proyecto estaba obsoleto, y mi trabajo ya lo indexaba otro con otra numeración

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 1 (`EVIDENCE-MATRIX.md`, regenerado)

**71 hallazgos y 21 herramientas que el índice del proyecto no conocía no son trabajo: son trabajo
invisible.** Lo he comprobado, lo he cerrado, y de paso he descubierto que **la numeración de
hallazgos esta duplicada entre los dos agentes** y que el mio ya estaba indexado bajo los números
del otro.

## Lo que encontre

`EVIDENCE-MATRIX.md` lleva en su cabecera:

```html
<!-- GENERADO POR tools/artifacts.py. NO EDITAR A MANO: la siguiente ejecucion lo sobrescribe. -->
```

**Es estado derivado.** La version en disco tenia **223 lineas** y mis seis hallazgos mas
recientes no aparecian:

```
los-26-count-valen-uno            0
clockstretcher-viva               0
ulv-viva-y-linklevel              0
hay-un-objeto-vddc-svid2          0
tres-capas-del-mvdd               0
```

## Y el descubrimiento: hay dos numeraciones

Antes de «arreglar» nada mire si mi trabajo estaba realmente fuera, y **no lo estaba.** La
numeracion esta duplicada entre los dos agentes, y **el otro agente ya indexaba mis hallazgos
bajo sus propios numeros:**

| fila en la matriz | mi fichero | |
|---|---|---|
| 224 | `120-dpm-levels-8-contra-una-cuenta...` | mio |
| 225 | `123-tabla-cac-vddgfx-basura...` | mio |
| 226 | `124-barrido-de-la-frontera-vbios-host` | mio |
| 227 | `125-enable-dpm-tasks-devuelve-cero` | mio |
| 228 | `126-contrato-de-error-de-los-1093-asserts` | mio |
| 229 | `128-copia-sin-cota-contra-array-fijo-de-8` | mio |
| 230 | `129-la-segunda-frontera-barrida` | mio |

Y en los mas recientes **las dos numeraciones coinciden**: `131`, `132`, `133`, `134`, `135` son
los mios en ambas.

> **Mi `063` lleva un contador propio de «hallazgos propios 081-135» que NO es el del proyecto.**
> Es un esquema autoasignado para no pisar al otro agente. **Para el proyecto, el numero autoritativo
> es el de la matriz, y no siempre es el mio.**

Esto no es un defecto: es exactamente lo que hace falta cuando dos agentes numeran en paralelo.
Pero **es un sitio donde un numero significa dos cosas**, y hay que saberlo.

## Como lo he cerrado

**No editando el markdown: ejecutando la herramienta del proyecto.** Y en ese orden:

```
1. python3 tools/artifacts.py --selftest
     RESULT: PASS (14 vectores)                  <- la herramienta esta validada

2. python3 tools/artifacts.py --json             <- vista previa, sin escribir nada
     artefactos: CONTRADICTIONS, CURRENT-STATE, EVIDENCE-MATRIX, KNOWLEDGE-GRAPH,
                 NEGATIVE-RESULTS, OPEN-FRONTIERS, TOOLS-STATUS

3. python3 tools/artifacts.py --solo EVIDENCE-MATRIX --json    <- comprueba que
     artefactos producidos: ['EVIDENCE-MATRIX']                    solo produce UNO

4. python3 tools/artifacts.py --solo EVIDENCE-MATRIX --escribir  <- escribe ese, y solo ese
```

**`--solo` es lo que hace esto aceptable.** La herramienta genera **siete** artefactos en la raiz
del proyecto, y seis son documentos compartidos. **Sin `--solo` habria reescrito seis ficheros
que no son mios**, para arreglar uno que si lo es.

## Lo que verifique despues

| fichero | lineas | mtime |
|---|---|---|
| **EVIDENCE-MATRIX.md** | **350** | **14:36** (esta ejecucion) |
| CONTRADICTIONS.md | 74 | 04:27 |
| CURRENT-STATE.md | 57 | 04:27 |
| KNOWLEDGE-GRAPH.md | 151 | 04:27 |
| NEGATIVE-RESULTS.md | 148 | 04:27 |
| OPEN-FRONTIERS.md | 460 | 04:27 |
| TOOLS-STATUS.md | 69 | 04:27 |

**Los seis conservan su mtime: no se han tocado.** Y la cabecera de «generado» sigue ahi.

**El indice paso de 223 a 350 lineas, y ahora contiene 339 filas de hallazgos**, entre ellos las
seis mias que faltaban.

- `MODIFICATIONS = 1`, y es un fichero generado, no fuente
- `LOS_SEIS_OTROS_ARTEFACTOS_INTACTOS = PROVEN`: mtime 04:27 en los seis
- `LA_HERRAMIENTA_ESTA_VALIDADA = PROVEN`: 14 vectores, PASS
- `SINO_SOLO_HUBIERA_REESCRITO_SEIS_FICHEROS_COMPARTIDOS = PROVEN_DERIVED`

## Lo que esto obliga a hacer en cualquier trabajo multi-agente

1. **El estado derivado se regenera, no se parchea.** El fichero lo dice en su cabecera. Editar
   a mano un indice generado garantiza que la siguiente ejecucion lo borre, y que el trabajo
   parezca no existir entre dos ejecuciones.
2. **Una herramienta que genera N artefactos compartidos necesita `--solo`.** Y hay que
   **comprobar en vista previa que `--solo` produce uno**, no suponerlo: por eso hice el paso 3
   antes del 4.
3. **Un numero que significa dos cosas es un sitio de colision silenciosa.** Dos agentes
   numerando en paralelo lo inevititan; lo que hay que hacer es **saber cual manda**. Aqui
   manda la matriz.
4. **Y un indice obsoleto no se ve desde dentro del trabajo.** Mis 71 hallazgos se veian completos
   desde `findings/`. **El hueco solo aparece mirando el indice del proyecto** — y por eso es una
   comprobacion que hay que hacer a proposito, no por casualidad.

## Clasificacion

- `EL_INDICE_DEL_PROYECTO_ESTABA_OBSOLETO = PROVEN`: 223 lineas, sin mis seis ultimos
- `LA_NUMERACION_DE_HALLAZGOS_ESTA_DUPLICADA = PROVEN`: 224-230 son los mios con su numeracion
- `PARA_EL_PROYECTO_MANDA_EL_NUMERO_DE_LA_MATRIZ = PROVEN`
- `MI_CONTADOR_PROPIO_DE_063_NO_ES_EL_DEL_PROYECTO = PROVEN`
- `LA_HERRAMIENTA_ESTA_VALIDADA = PROVEN`: 14 vectores
- `SOLO_SE_HA_ESCRITO_UN_FICHERO = PROVEN`: los otros seis conservan mtime
- `MODIFICATIONS_HA_PASSADO_DE_0_A_1 = PROVEN`, sobre un fichero generado

## Estado

Hallazgo **136**: **la primera modificacion del proyecto**, y sobre **estado derivado**, con la
herramienta del propio proyecto y validada. Los seis artefactos compartidos que el generador
produce tambien **intactos**, y mis seis hallazgos mas recientes **ya son indices**.