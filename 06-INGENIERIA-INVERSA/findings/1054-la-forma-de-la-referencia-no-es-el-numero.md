# 1054 — la forma de la referencia no es el número: 4 tokens distintos detrás de un mismo verbo

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN-TOOLDESIGN
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST, EJECUTANDO tools/artifacts.py
AFECTADO=tools/artifacts.py:317-320 (gen_current_state)  ·  tools/claims.py:749
ESTADO=PROBADO · REPARADO · reconciliado a 42/42 · self-test 27 vectores PASS
```

## El defecto, y por qué el hallazgo 259 loersea mal

El hallazgo 259 dice que `findings/` tiene 65 números con dos ficheros (hoy 74) y que por
eso `CORRECTED_BY=NNN` no se puede resolver. Es cierto. **Pero el número no es el
problema principal: es la forma del token lo que se estaba tirando.**

MEDIDO sobre las 42 referencias con verbo de corrección de `findings/`:

| forma del token | n | qué significa |
|---|---|---|
| `CORRECTS=040-smu-canal-mensajes-gfx8.md` | **14** | **nombre de fichero: resuelve exacto** |
| `CORRECTS=040` | 15 | número: puede ser ambiguo |
| `CORRECTS=105-se-ih-y-el-camino-real-de-los-faults.md` | 5 | slug sin `.md`: resuelve exacto |
| `CORRECTED_BY=087-CORRECCION-POSTERIOR` | **5** | auto-anotación: **no es una referencia** |
| `CORRECTED_BY=NNN` | **3** | plantilla de prosa: **no es una referencia** |

**14 de 42 referencias ya llevan el nombre de fichero.** El proyecto **ya escribe** la
desambiguación que 259 pedía. Y la herramienta la destruía:

```python
# tools/artifacts.py, antes
for rx in (r"CORRECTED_BY=([\w-]+)", r"CORRIGE_LA_POLITICA=(\d{3,4})",
           r"CORRECTS=(\d{3,4})"):
```

`CORRECTS=(\d{3,4})` sobre `CORRECTS=040-smu-canal-mensajes-gfx8.md` captura `040`,
publica `-> corregida por 040`, **y pierde el nombre**.

> Un nombre exacto convertido en un número ambiguo es peor que no leer la referencia,
> porque **parece que se leyó**. Y `040` tiene tres ficheros.

En el otro extremo, `CORRECTED_BY=([\w-]+)` capturaba el token entero y publicaba
`-> corregida por 087-CORRECCION-POSTERIOR` y `-> corregida por NNN`.

Y esto no lo decidí yo: `1049-los-74-numeros-duplicados.md:103` dice, textual,
*«`CORRECTED_BY=NNN` necesita el **nombre del fichero**, no el número»*. La
prescripción estaba escrita en el árbol antes de que existiera el resolutor.

## El resultado medido, antes y después

`gen_current_state(root, ind)` tarda **0,0 s**. Ejecutado sobre el corpus real:

| | antes | después |
|---|---|---|
| filas de «corregida por» | **35** | **28** |
| de ellas, referencias a otro hallazgo | 12 | **16** |
| destinos que no son un hallazgo | **8** | 0 |
| auto-aristas | 1 | **0** |
| aristas duplicadas | 4 | **0** |

**Reconciliado a 42/42, sin huecos:**

```
16  RESUELTA
11  AMBIGUA          el número tiene >1 fichero y el token no lo desambigua
 8  NO_REFERENCIA    no empieza por dígito: plantilla o literal
 5  NO_REFERENCIA    auto-anotación CORRECCION-POSTERIOR
 1  NO_REFERENCIA    el token nombra este mismo fichero
 1  INEXISTENTE      1011 -> 04-IMPLEMENTACION (una ruta, no un hallazgo)
----
42
```

## Los tres defectos, y los tres tienen la misma forma

**La rama hermana tiene el guard y esta no.** En la misma función, veinte líneas más
arriba, ya estaba escrito:

```python
# Se descarta la auto-referencia: 091 dice en su cuerpo
# "CLAUSULA_RETRACTADA_POR=091" al DESCRIBIR lo que hizo, y el escaner lo contaba
# como retractado por sí mismo. Un hallazgo no se retracta a sí mismo.
for rx in (r"CLAUSULA_RETRACTADA_POR=(\d{3,4})", r"RETRACTED_BY=(\d{3,4})"):
    for g in re.findall(rx, txt):
        if g == m.group(1):        # <-- ESTE GUARD
            continue
        item = ...
        if item not in retr:       # <-- Y ESTE DEDUP
```

1. **`corr` no tenía guard de auto-referencia.** Salía `030 -> corregida por 030`,
   porque `030-page-walker:117` **describe** la convención al explicarla.
2. **`corr` no tenía dedup.** `72 -> 041` y `73 -> 040` salían **dos veces** cada uno,
   porque dos verbos distintos del mismo fichero disparan la misma arista.
3. **`corr` no distinguía token de número.** Por eso los 8 destinos inventados.

Es la **tercera vez** que sale esta forma en la sesión, y ya está escrito:
`constmap.py` (arregló el self-test, dejó la CLI), `drift.py` (arregló el informe, dejó
la escritura), y ahora esto.

## Una regresión mía, medida antes de llegar al árbol

Escribí el resolutor con `bynum` construyéndose **en el mismo bucle** que resuelve. Como
los ficheros van en orden alfabético, al llegar al fichero `019` el `030` todavía no se
había leído, así que `bynum.get(30, [])` devolvía `[]` y:

```text
019 -> corregida por 030    AMBIGUA (2 candidatos)   <-- lo correcto
  019 -> corregida por 030    ROTA (no existe)         <-- lo que salia
```

Lo vi porque el recuento de «rotas» era 4 y dos de ellas no tenían sentido. **Dos
pasadas, y el índice se construye entero antes de resolver nada.** La versión final da
1 rota, y es real.

Y antes de cerrar: mi caso `NO_REFERENCIA` descarta tokens, y **un descarte que se come
una referencia real es peor que el defecto que he arreglado**. Los 8 revisados uno a uno:

| fichero:línea | token | qué es |
|---|---|---|
| `050:5` | `statement-in-session-2026-10-01` | etiqueta de `SCOPE_CLAIM` |
| `056:6` | `la` | prosa: *«`CORRECTS=la clasificación NOT_AVAILABLE...`»* |
| `073:50` | `la` | prosa, y la fila lo dice: *«CIERRA=la, CORRECTS=la -> sí es prosa»* |
| `1011:9` | `AD-8` | un id de decisión, no un hallazgo |
| `1011:11` | `DECISIONS.md:896` | fichero y línea, no un hallazgo |
| `1049:44,57,103` | `NNN` | plantilla. **`1049` es mío** |

Ninguno es una referencia. Y los dos últimos son interesantes porque el proyecto escribe
`CORRECTS=` para cosas que no son hallazgos, lo que confirma que el verbo se usa como
marcador genérico y no solo como puntero.

## Lo que queda abierto, y son 11

De 28 aristas, **16 son inequívocas y 11 siguen sin poder resolverse**, todas por número
duplicado:

```text
019 -> 030  [2]      046 -> 040  [3]      073 -> 040  [3]   (x2 en el fichero)
023 -> 035  [2]      051 -> 046  [3]      074 -> 040  [3]
035 -> 023  [2]      072 -> 041  [3]      259 -> 025  [2]   (x2 en el fichero)
```

Dos de ellas las resuelve el texto, y lo comprobé leyéndolo:

- **`019:8` → `030-page-walker-gfx8-2-niveles.md`**. La línea 13 del propio 019 lo
  escribe: *«Ver `030-page-walker-gfx8-2-niveles.md`»*.
- **`023:6` → `035-correccion-ptepde-es-polaris12.md`**. El texto dice que 035 leyó
  `sdma_v4_0.c` en vez de `sdma_v3_0.c`, y el otro 035 es
  `035-block-size-tres-claims-y-un-log.md`, que no va de SDMA. El nombre y el
  contenido coinciden.

**Las otras 9 no las decido yo**: son hallazgos de otras sesiones y el principio de no
mezclar ámbitos sigue en pie. Lo que sí hace el generador ahora es **decirlas** en una
sección propia, con el número de candidatos, en vez de elegir un destino en silencio.

Eso es la diferencia entre el antes y el después, y es la de todo este proyecto: antes
el generador publicaba 35 filas y 12 eran verdad; ahora publica 28 y las 28 son verdad,
de las cuales 11 dicen **no sé**.

## `claims.py` también tenía el problema, y NO lo tenía

`tools/claims.py:749` usa `CORRECTED_BY=(\d{3})`, solo dígitos, lo que trunca
`087-CORRECCION-POSTERIOR` a `087` y produce `087 CORREGIDO_POR 087`.

**Lo comprobé y está bien**: la línea 753 es `if este and num != este:`, o sea el guard
de auto-referencia **ya estaba**. Mi primera medición aplicó las regex a mano y
dijo «6 aristas reflexivas»; era falso para `claims.py`, porque apliqué el patrón sin el
guard que está tres líneas más abajo.

**Octava vez esta sesión que aplico un regex en vez de ejecutar la cosa.** El
`resolver_destino` de `artifacts.py` se puede reutilizar tal cual en `claims.py`, que es
el segundo consumidor; no lo he hecho porque no lo he medido ejecutando `claims.py`.

## Lo que NO se afirma

- **No se afirma que las 11 ambiguas estén resueltas.** Están medidas y declaradas.
- **No se ha editado ningún hallazgo de otra sesión.** Los 9 `CORRECTS=040-smu-...` ya
  traen el nombre; los que faltan son decisión de quien escribió esos hallazgos.
- **`tools/claims.py` no se ha tocado.** Su regex sigue siendo `\d{3}`; lo correcto
  sería que llamara a `resolver_destino`, y eso no está hecho ni medido.
- **No se ha regenerado `CURRENT-STATE.md`.** El artefacto se ha producido en memoria
  para medirlo. Regenerarlo escribe un fichero del proyecto y es otra decisión.
- **El `self-test` de `artifacts.py` pasa con 27 vectores**, pero pasar su self-test no
  demuestra que su salida sea correcta: comprueba su propia lógica, no la unicidad de su
  entrada. Eso lo dijo el hallazgo 259 y sigue siendo cierto.