# R4-VERIF — una puerta de deriva sobre lo que miden las otras tres herramientas

<!-- MEDIDO con tools/verif.py. Artefacto: linea-base.json (17 medidas). -->

```
AGENCIA=RX550-INVESTIGACION · AGENT RE/TOOLING
WORK_CLASS=validacion-de-instrumentacion
RUNTIME=NO · sin sudo · sin GPU · no ejecuta las herramientas, las LEE su JSON
escritura=2 ficheros NUEVOS + la propia linea base.  Ningun fichero existente modificado.
herramienta   tools/verif.py 1.0.0
selftest      13 vectores, 0 fallos, rc=0
medidas       17, en cuatro clases de expectativa
```

## 0 · EL AGUJERO QUE ESTA PUERTA TAPONA

Los tres instrumentos de este ciclo producen afirmaciones sobre el corpus, y
esas afirmaciones se escribieron en `artifacts/R1-R3/`. **Esos tres documentos
ya no se van a volver a mirar**, y las mediciones que contienen se quedan viejas
sin que nadie lo note.

No es hipotético. **MEDIDO**: la población de herramientas pasó de 199 a 202
durante este trabajo, porque se añadieron `pm4ops.py` y `dwarfx.py`. El
documento R1 dice 199. Nadie se enteró, porque el documento no se contrasta con
nada: es una foto, y las fotos envejecen.

## 1 · POR QUÉ CONJUNTOS Y NO RECUENTOS

MEDIDO, y la razón es concreta: un `--congelar`/`--verificar` sobre recuentos
habría disparado tres veces en un día por cosas que no son hallazgos —yo
añadiendo herramientas—. El conjunto detools con hueco pasa de 7 a 8 porque hay
una herramienta más, y eso **es información con nombre**, no ruido.

Por eso las medidas son conjuntos de sujetos nombrados, y el diff dice
`APARECEN` / `DESAPARECEN` con los nombres. Añadir `dwarfx.py` aparece como lo
que es.

## 2 · LAS CUATRO CLASES, Y POR QUÉ NO BASTAN DOS

Una puerta de deriva sin decir qué se espera de cada medida es una alarma que
nadie escucha. Es lo que el propio `toolreg.py` escribe de una interlusa que
llora por escritura: *"an interlock that cries wolf gets ignored, and then it
protects nothing"*.

| clase | qué significa | qué pasa si se mueve |
|---|---|---|
| `ESTABLE` | debe dar lo mismo siempre | alguien cambió algo sin decidirlo |
| `VACIA` | se espera vacía | **hallazgo nuevo** |
| `CONOCIDA` | se sabe que **no** está vacía | solo noteworthy si **crece** o se corrige |
| `DRIFTABLE` | se mueve legítimamente | se informa, no se juzga |

### 2.1 · `CONOCIDA` existe por MEDIDO, no por gusto

Al correr esto por primera vez sobre el corpus real, dos medidas marcadas
`VACIA` resultaron no estarlo: guardaban defectos **ya escritos** en hallazgos.
Con la etiqueta equivocada la puerta habría gritado `HALLAZGO` en cada
ejecución por algo que ya se sabe, y a la tercera nadie la mira.

| medida | clase inicial | lo que mide | clase correcta |
|---|---|---|---|
| `gate.alcanzable_sin_flag` | `VACIA` | 1: `amdioread.py` | **`CONOCIDA`** |
| `pm4.inconsistentes_pm4decode` | `VACIA` | 4 en `pm4decode.c` | **`CONOCIDA`** |
| `dwarf.linea_movida` | `VACIA` | 0 | `VACIA` — sigue siendo hallazgo nuevo |

## 3 · TRES ESTADOS QUE NO SON EL MISMO

La primera versión confundía dos de ellos, y dos vectores lo cazaron:

| estado | qué es |
|---|---|
| `NO_SE_MIDE` | el instrumento no produjo la medida. **Instrumento roto.** |
| `SIN_BASE` | la medida existe pero la línea base no la tiene. **Base incompleta.** |
| *(cambio)* | comparables, y difieren |

Tratar `NO_SE_MIDE` como "sin cambio" es **una puerta que se apaga sola cuando
falla el sensor**: verde por avería.

## 4 · UN BUG QUE HACE LLORAR A LA PUERTA

Comparar dos listas por **orden** reportaba como deriva un simple reorden, con
un diff vacío. Una alarma que suena sin mostrar nada es ruido, y el ruido es lo
que hace que la gente deje de mirar la puerta. Ahora dos listas se comparan por
conjunto, y si solo cambia el orden no se informa. Vector `DER_7`.

## 5 · VERIFICADO QUE DISPARA

Una automatización que nunca suena es teatro. Se comprobó perturbando una copia
de la línea base con los tres casos, y disparando los tres:

```
  DERIVA EN 3 de 17 medidas

  !! SE ESPERABA VACIA Y NO LO ESTA.  Esto es un HALLAZGO NUEVO
     dwarf.linea_movida          DESAPARECEN (1): rx550_pdb0.state

  !! SE ESPERABA ESTABLE Y NO LO ESTA.  Algo cambio sin que nadie lo decidiera
     pm4.alcance_generacion      DESAPARECEN (1): sid.h

  ~  DRIFTABLE, cambio legitimo probable.  Se informa, no se juzga.
     flags.ambiguos             SIN CONGELAR.  Ahora mide: 23 elementos
```

El terceroDlava: la primera versión volcaba los 23 nombres en crudo, 23
líneas tapando las dos derivas que de verdad importaban. Ahora resume el tamaño
y muestra seis.

## 6 · LO QUE ESTA PUERTA NO DICE

```
  Ojo con lo que esto NO dice: que las mediciones SIGUAN dando lo
  mismo no dice que sean correctas.  Solo dice que nadie cambio el
  sujeto.  La correccion la puso quien las escribio.
```

**Deriva no es juicio.** La puerta dice *qué* cambió. Si el cambio es bueno o
malo es de quien lee. Y una medida que no se puede tomar no cuenta como verde.

## 7 · USO

```
python3 tools/verif.py              compara con la linea base; rc=1 si hay deriva
python3 tools/verif.py --fijar      escribe la linea base (unica escritura)
python3 tools/verif.py --json       salida estructurada
python3 tools/verif.py --selftest   13 vectores, hermetico
```

Códigos de salida: `0` sin deriva · `1` con deriva · `2` sin línea base, o un
instrumento no responde.

```
ESTADO
  ficheros escritos    3, todos nuevos
  ficheros modificados 0
  GPU                  INTACTA
  sudo                 NO usado
  herramientas ejecutadas por la puerta  0  (solo lee su --json)
  commits              NINGUNO
```