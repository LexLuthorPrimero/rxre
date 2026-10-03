# 046 · Una herramienta se cita a sí misma, y eso obliga a jerarquizar las fuentes

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`HERRAMIENTAS=08-ARQUITECTURA/tools/stale_gap.py`, `_selftest_stale_gap.py`,
`corpus_guard.py` · `CONTINUES=045`

## Cuestión principal

`045` documentó que un estado citado en una frase negativa se cuela como
respuesta cerrada. Al escribir ese hallazgo, ¿qué pasó?

## Criterio de terminación

Cruzar `045` contra sus propias reglas. **Cumplido: la herramienta se citaría a
sí misma, en siete fronteras abiertas.**

## Lo que pasó

Se reprodujo **solo**. Las líneas de `045` que citan `FUNCTION=always` para
explicar el fallo se convirtieron en "respuesta cerrada" de siete fronteras que
siguen abiertas:

```
045:117  "para llegar a `PROVEN` es exactamente lo contrario. El texto
         decia que no se puede llegar a `PROVEN`."
045:118  "llegar a `PROVEN`."          <- sin negacion visible
```

El filtro de negación de `045` mira **una línea**. Una línea de continuación no
tiene la negación, porque la frase empieza en la anterior. `222` hereda el
`PROVEN` de `221` y se cuela.

**Y el documento que lo produce es este proyecto hablando de su propia
herramienta.** Una herramienta que cita el caso que analiza, se cita a sí misma.

## La jerarquía que esto obliga

Un hallazgo mide el ASIC. Un documento de método mide el **proyecto**. Sus
afirmaciones sobre el hardware son *ejemplos de por qué una herramienta falla*,
no respuestas.

Eso no se arregla con un filtro de lenguaje, porque el problema no está en la
frase: está en la **premisa**. Un documento de método, por definición, no mide
el hardware. Y eso se corrige por una propiedad de la **fuente**: el nombre del
fichero.

```
SERIE_METODO = [
    r"herramient",            # 038, 056-sin-herramientas
    r"fronteras-obsoletas",   # 045, este detector
    r"mapa-causal",           # 042
    r"grafo-y-detector",      # 041
    r"auditoria|prospeccion", # 048-claims, 041-procedencia
    r"correccion.*make",      # 044-correccion-implementada
    r"convencion-de-count",   # 045-la-convencion
    r"el-limite-del-claim",   # 047-los-diez-selectores
]
```

La lista está **entera y visible**, no un patrón genérico, para que se pueda
discutir qué entra. Añadir un patrón es barato, y por eso es peligroso: una
exclusión debe poder justificarse.

Efecto medido: `RESUELTA_OTRO` pasó de 33 a **24**, y **0** de las 24 responden
desde un documento de método. Antes, 7 sí lo hacían.

## Un sujeto escrito en negrita, no entre backticks

Al mirar las 112 fronteras `SIN_SUJETO` resultó que muchas sí lo tienen:

```
001:213  **GFX_HWIP sigue `NOT_DETERMINED`.**
009:145  **Estado: `NOT_DETERMINED`, causa distinta.**
```

El sujeto es el identificador, y está en **negrita** o en `CONSTANTE_EN_MAYÚSCULAS`.

Una frontera a la que "le falta el sujeto" no se puede cerrar ni repetir. Perder
el sujeto por mirarlo solo entre backticks convierte un dato en un defecto de
documento.

`SIN_SUJETO`: 112 → **86**.

### Y el orden en que se buscan los candidatos decide el resultado

Puse la fuente nueva **antes** que las existentes. Resultado:

```
SIN_SUJETO     112 -> 185
RESUELTA_OTRO   29 ->  19
```

**La ampliación destruyó información que ya se tenía.** No es "buscar más", es
cambiar el extractor a algo peor: la fuente débil pisó a la fuerte.

El orden correcto es el de confianza:

```
1. backticks explícitos     (el autor puso comillas: es un símbolo)
2. IDENT = ESTADO           (forma formal de tabla)
3. negrita / CONSTANTE      (prosa)
```

Con el orden correcto: `SIN_SUJETO` 86 y `RESUELTA_OTRO` 24, que es más que
antes en las dos direcciones.

## Una comprobación de integridad que decía lo que no era

El reinicio del servidor borró `/tmp/corpus_guard_state.json`, y `--verify`
respondió:

```
no hay referencia. ejecuta primero --snapshot
```

En un proyecto que **no había tocado el corpus**.

El fallo no es que el fichero desaparezca: eso lo avisa. Es que esa respuesta y
"el corpus cambió" son distintas, y la primera se lee como la segunda, o al
revés.

**Un control que pierde su referencia tiene que decirlo de forma
inequívoca.**

Tres arreglos:

1. El estado vive **también en el repositorio**. Si las dos copias difieren,
   avisa y usa la del repositorio: comparar contra una referencia arbitraria
   daría un veredicto de integridad que no significa nada.
2. Sin referencia: responde **2**, no 0, y dice `DESCONOCIDO: ni intacto ni
   modificado`.
3. `run_all` ejecuta `--verify` (huella de 2787 ficheros) **además** de
   `--git`.

El tercero importa: `--git` devuelve 0 cuando `git status --porcelain RESEARCH/`
está vacío, y eso **no es una verificación del corpus**. Solo comprueba que git
no ve cambios. Si alguien regenera un fichero y lo commitea, `--git` dice que
todo bien y no es cierto.

Verificado con los tres casos: sin referencia → `rc=2`; referencia de `/tmp`
falsa y la del repo buena → avisa y usa la buena; restaurada → `rc=0`.

## El self-test también tiene contrato

`stale_gap` declaraba `READONLY=yes` y era cierto: sin argumentos solo lee. Con
`--self-test` escribía, para construir los ficheros que prueban sus filtros. El
validador leía el código, encontraba la apertura en modo escritura, y **tenía
razón** en que el contrato mentía. Las dos cosas eran ciertas.

Tres salidas:

| | |
|---|---|
| `WRITES_FILES=yes` | cierto pero más débil: afirma que puede escribir cuando en el 95% de sus ejecuciones no puede. Un contrato inflado deja de distinguir herramientas. |
| self-test en memoria | pierde lo único que lo hace útil: probar los filtros contra ficheros de verdad. |
| **fichero aparte** | cada uno declara lo que hace, y los dos contratos son ciertos a la vez. |

Se eligió la tercera. Y **mientras tanto** la contradicción se dejó marcada
como `FALLA`, sin resolver con el atajo cómodo: un control que se pone rojo
obliga a decidir; uno que se pone verde porque se cambió el contrato para que
lo hiciera, no.

### Y el epílogo que nadie pidió

Resuelto eso, `toolkit` seguía marcando `FALLA` con **un patrón de escritura**.
El único sitio que quedaba era el comentario que **explicaba** el problema,
escrito con el patrón literal dentro.

Un comentario que *describe* una escritura se cuenta como escritura: el
validador lee el fichero entero y no distingue código de prosa.

Se reescribió el comentario. **El contrato más fuerte no es el que se escribe:
es el que ninguna otra herramienta puede contradecir.**

## Un fallo de `citecheck`, de otra sesión

`run_all` marca `FALLA citecheck: 32 vectores`:

```
FAIL  una cadena que sale del rango del .md se marca, no se resuelve mal
      got=['LINE_OUT_OF_RANGE', 'LINE_OUT_OF_RANGE']
      want=['OK', 'LINE_OUT_OF_RANGE']
```

Es una herramienta **no commiteada, de otra sesión**. No la he tocado. Lo
registro porque un runner rojo tiene que tener una explicación, y "lo otro lo
está arreglando" es una explicación que caduca.

## Clasificación

| afirmación | estado |
|---|---|
| `045` se cita a sí mismo y cierra 7 fronteras abiertas | `PROVEN` — cruce medido |
| Un documento de método no cierra fronteras del ASIC | `DERIVATION` — por definición |
| `RESUELTA_OTRO` 33 → 24 al excluir método | `MEASUREMENT` |
| 0 de las 24 responden desde un documento de método | `MEASUREMENT` |
| La ventana de negación debe abarcar la línea anterior | `DERIVATION` |
| `SIN_SUJETO` 112 → 86 con negrita y constantes | `MEASUREMENT` |
| El orden de candidatos decide más que la lista | `MEASUREMENT` — 112→185 al invertirlos |
| `--git` no verifica el corpus | `PROVEN` — `git status` vacío ≠ integridad |
| `rc=2` sin referencia, `rc=0` con referencia | `MEASUREMENT` — 3 casos |
| Que el fallo de `citecheck` sea real y no de uso | `NOT_DETERMINED` — herramienta ajena |

## Confounders

- **El orden de los candidatos lo decidí yo.** Backticks > `IDENT = ESTADO` >
  negrita es una conjetura sobre cómo escriben estos documentos, no una
  propiedad medida. El dato que la respalda es que invertirlos empeora las dos
  cifras, que es evidencia de orden pero no de cuál es el orden correcto.
- **`SERIE_METODO` es una lista de 8 patrones sobre 104 documentos.** 15 quedan
  fuera y pueden ser de método sin que yo lo sepa. El filtro es del mismo
  orden de exactitud que un detector de frase: alto en falsos positivos que
  importan, con falsos negativos desconocidos.
- **Un hallazgo de método puede contener un hallazgo de hardware real.** Si un
  documento de herramientas midiera el ASIC, el filtro tiraría su evidencia.
  No lo ha hecho ninguno de los ocho.
- **Excluir es más fácil que decidir.** Con un filtro más podría bajar el
  número de `RESUELTA_OTRO` a cero y el runner se vería más limpio. El filtro
  tiene controles **simétricos** precisamente para que eso no pase sin que se
  note.

## Desfalsificación

- **(a)** `045` no se cita a sí misma → refutable con `--json` y contando
  respuestas cuyo documento esté en `SERIE_METODO`; sale 0.
- **(b)** Excluir método no destruye evidencia real → refutable con el control
  10e-3 del self-test: un hallazgo normal sigue cerrando fronteras.
- **(c)** La ventana de negación no recorta de más → refutable con los
  controles 10b y 10d; ambos PASS.
- **(d)** El corpus estaba intacto cuando `--verify` dijo "no hay referencia" →
  refutable con `git status --porcelain RESEARCH/`; vacío.

## UNLOCKS

- **La jerarquía de fuentes queda explícita**: un hallazgo mide el ASIC, un
  documento de método mide el proyecto. Ninguna herramienta de este proyecto la
  tenía escrita, y todas la necesitan.
- **El runner comprueba integridad de verdad**, no solo que git esté limpio.
- **`SERIE_METODO` es un punto de extensión declarado**: cuando aparezca otro
  documento de método, se añade una línea y se dice por qué.
- **`stale_gap` cierra 24 fronteras y deja 86 sin sujeto**, que son 86 líneas
  de documento arreglables sin hardware.

## Evidencia

```
HERRAMIENTAS
  stale_gap.py                obsoletas 29 -> 43 -> 34 con los filtros
                              SIN_SUJETO 112 -> 86
                              self-test 15 controles, TOOL_VALIDATED
  _selftest_stale_gap.py      el unico fichero que escribe; contrato propio
  corpus_guard.py             estado en el repo, rc=2 sin referencia

NUMEROS
  RESUELTA_OTRO   29 -> 33 (negrita) -> 24 (excluir metodo)
  SIN_SUJETO     112 -> 185 (orden MAL) -> 86 (orden correcto)
  respuestas desde documentos de metodo: 0

VERIFICADO A MANO
  024:284  PAGE_TABLE_DEPTH  -> 064:168
  025:182  mb()              -> 031:274
  031:278  writel            -> 032:243

CORPUS
  2787 ficheros, huella sin diferencias
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.