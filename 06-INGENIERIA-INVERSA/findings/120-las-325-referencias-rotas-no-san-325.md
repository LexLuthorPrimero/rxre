# 116 · Las 325 referencias rotas no son 325, y ninguna se arregla escribindo el nombre bueno

`CLASSIFICATION=METHODOLOGY` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`HERRAMIENTA_NUEVA=tools/reftriage.py` (`TOOL_VALIDATED`, 11 vectores)
`CONTINUES=119` · `AUDITA=071` (que ya documenta 4 de estas por nombre)

## Cuestión principal

Dos herramientas registradas del proyecto dan cifras incompatibles sobre la
integridad de las citas:

```
tools/audit_citations.sh     495 citas resueltas · 0 omitidas · 0 fallos
tools/artifacts.py           325 ROTA + 6 ROTA_HISTORICA + 3373 RUTA_EQUIVOCADA
```

Durante varias rondas esto se leyó como una contradicción entre dos
herramientas que miden lo mismo. **Miden conjuntos distintos, y medidos:**

```
audit_citations.sh    495 citas     en 07-DRIVER/ y tools/  -- el driver propio
artifacts.py         6856 refs      en todo el árbol, findings incluidos
```

Entre los hallazgos 070-080 y los de rondas anteriores, el conjunto de
referencias del proyecto creció más de 13× sin que la cifra de la herramienta
del driver creciera, porque esa herramienta audita el driver y el driver no
creció. **No hay contradicción: hay alcances, y no estaban declarados.**

Verificado antes de afirmarlo: los siete nombres más citados por
`artifacts.py` como ROTA —`CLAUDE.md`, `DESIGN.md`, `PROJECT-ROADMAP.md`,
`PRE.md`, `docs/config.md`, `docs/rules.md`, `claude/CLAUDE.md`— **no
existen en ninguna parte del árbol**, verificados con `find` desde la raíz y
no desde un subdirectorio. Es la quinta vez que compruebo un `0` que podía
ser de ámbito.

## Respuesta: de qué son las 325

Un recuento sin descomposición obliga a elegir entre dos salidas que no
significan nada: ignorarlo, o aceptarlo y dejar de mirar la herramienta.
`tools/reftriage.py` las clasifica por naturaleza:

```
FICHERO_INEXISTENTE:SIN_CANDIDATO      215   66.2 %   deuda real
NO_ES_UN_FICHERO:RUTA                   75   23.1 %   defecto del extractor
AUSENCIA_DOCUMENTADA                    35   10.8 %   registra un resultado
```

**Un tercio de las 325 no son deuda.** 75 las produce el propio
`artifacts.py`, que captura directorios (`06-INGENIERIA-INVERSA/`,
`tmp/opencode/contract/`) como si fueran nombres de fichero. 35 son documentos
que **afirman** la ausencia: `02-ARQUITECTURA/OPENCODE-CONFIG-AUDIT.md:145`
es una tabla de qué ficheros de configuración están presentes, con `✗` y
`NOT_FOUND` en la propia celda. Ahí la referencia no está rota: registra un
`NEGATIVE_RESULT`, que es información, y por eso no se corrige.

## El dato que decide la acción: cero candidatos

```
citas de deuda real: 215
nombres DISTINTOS:   130
documentos afectados: 51
nombres con candidato de renombrado: 0
```

**Ninguno de los 130 nombres tiene un nombre parecido en el árbol.** Eso
descarta la explicación cómoda —«se renombraron y las citas quedaron viejas»—
y deja dos, que exigen decisiones distintas:

1. **Se borraron.** Entonces la cita es deuda y la acción es reescribir el
   documento, no tocar el nombre.
2. **Nunca existieron**, porque el documento los cita como ejemplo. Entonces la
   acción es **declarar la excepción**, como ya se hizo con 6 en
   `tools/REF-EXCEPTIONS.txt` y con 4 por nombre en `071`.

Y no se puede elegir entre las dos midiendo: exige leer el documento. Por eso
la herramienta **no afirma cuál es cuál**. Acota la lectura a ±4 líneas de
contexto y por eso clasifica por tendencia, no con certeza; un documento puede
decir «`X.md` no existe» en una línea y citarlo como evidencia en la siguiente.

La distribución dice que tampoco es un arreglo corto:

```
los 10 nombres mas citados   66 de 215  = 31 %
nombres que salen una vez    96
```

## Dos defectos de `artifacts.py` que salieron al medir esto

**1. Cuenta 325 y imprime 14.** El recuento sale de `len(aud["rotas"])` y el
bucle de impresión está acotado. Un recuento que no se puede auditar contra
su propia evidencia obliga a fiarse del número, que es justo lo que un
recuento no debería obligar. Las 311 restantes no se ven en ninguna parte.

**2. El código de salida siempre vale 1.** Es `return 1 if n_rota else 0`, y
`n_rota` es 325 porque hay citas deliberadamente ausentes en documentos que
documentan ausencias. Una herramienta cuyo código de salida no puede
distinguir «todo correcto» de «todo roto» no tiene código de salida: tiene una
constante. Consecuencia práctica: nadie puede usarla en una comprobación
automática, así que **nadie la usa en una comprobación automática**, y sus 325
no se han visto desde que se escribieron.

## Lo que falta por hacer, y no es un bucle

Con las tres clases separadas, la deuda real son **215 citas en 51
documentos**, sin candidato de renombrado en ninguna. Lo que decide el
coste no es el número de citas sino cuántos de esos 51 documentos son de la
clase 2 (ejemplos) y cuántos de la clase 1 (borrados), y eso es una lectura
por documento.

**No se ha ejecutado.** Es trabajo de juicio sobre 51 documentos y no lo
automatizo: un `sed` que reescriba `CLAUDE.md` por un nombre parecido
inventaría a qué documento quería referirse el autor, que es peor que la
referencia rota.

## Clasificación

| afirmación | estado |
|---|---|
| `audit_citations.sh` y `artifacts.py` miden conjuntos distintos | `PROVEN` — 495 frente a 6856, y el alcance de cada una |
| Los 7 nombres más citados no existen en ninguna parte del árbol | `MEASUREMENT` — `find` desde la raíz, no desde un subdirectorio |
| 34 % de las ROTA no son deuda | `MEASUREMENT` — `reftriage.py` |
| Ninguno de los 130 nombres tiene candidato de renombrado | `MEASUREMENT` |
| 75 ROTA las produce el extractor de `artifacts.py` | `MEASUREMENT` — captura directorios |
| Qué parte de las 215 es clase 1 y qué parte clase 2 | `NOT_DETERMINED` — requiere leer 51 documentos |
| Que un `±4` líneas baste para separar ausencia documentada de cita rota | `NOT_DETERMINED` — es un límite declarado, no una medición |

## Confounders

- **La ventana de ±4 líneas es una elección, no un hecho.** Con ±10 habría más
  `AUSENCIA_DOCUMENTADA`; con ±1, menos. El 35 no es un número de verdad sobre
  la ausencia, es un número sobre un umbral. Y por eso la clase se llama
  `AUDITAR` y no `ROTA`.
- **`S:\INFORME\DESIGN.md` incluye rutas absolutas de otra máquina**, que no se
  pueden resolver aquí aunque el fichero exista allí. Están contadas como
  deuda y no lo son. Es un falso positivo por ejecucion en otra maquina y no lo he separado.
- **El recuento depende del directorio**: 6856 referencias es una cota
  inferior mañana.

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0` sobre el corpus: el árbol de Linux
7.2.8 no se ha tocado. `GPU INTACTA`.
---

# CORRECCION POSTERIOR — el reparto real, que estaba oculto detrás de 14 líneas impresas

Este documento **no se reescribe**. Lo que sigue añade el dato que faltaba y
corrige la atribución de "51 documentos afectados por deuda real".

## Lo que se corregía

El defecto era de `tools/artifacts.py`: el recuento salía de
`len(aud["rotas"])`, que cuenta **todos** los documentos, y la impresión era
`for r in fnd[:20]` sobre `fnd`, que recogía **sólo findings**. Resultado:
**340 declarados, 14 visibles**, y las 14 visibles todas de `071`. Un recuento
que no se puede reconciliar con su propia evidencia obliga a fiarse del número,
que es lo contrario de lo que sirve un recuento.

Corregido agrupando por documento y listando **los 71 completos**, con el
detalle acotado por documento y no globalmente, para que la suma de la lista
sea el total.

## El reparto, que es lo que cambia la lectura

```
71 documentos, 340 referencias rotas en total
45 de 340 en 06-INGENIERIA-INVERSA/findings
295 de 340 en el resto del árbol
```

**La cadena de evidencia del proyecto tiene 45 citas rotas, no 340.** Y las
295 restantes están en documentación de auditoría y planificación
(`02-ARQUITECTURA/OPENCODE-CONFIG-AUDIT.md` con 63, `REORGANIZATION-AUDIT.md`
con 59, `DOCUMENTATION-RELATIONSHIPS.md` con 23, y así forth), que citan
nombres de ficheros para afirmar **que no existen**.

Eso invierte la prioridad que yo había dado por hecha. Escribí que "la deuda
real son 215 citas en 51 documentos"; el número de documentos con deuda en
`findings/` es mucho menor que 51, porque la mayoría de los 51 son auditoría y
planificación. Y para la cadena de evidencia, que es lo que sostiene las
conclusiones, la cifra es 45.

**Un recuento agregado habría producido la misma conclusión equivocada con
cifras mayores**, que es la forma que tarda más en notarse.

## Lo que NO cambia

- `audit_citations.sh` (495, el driver) y `artifacts.py` (6856, todo el árbol)
  siguen siendo alcances distintos, no una contradicción.
- Los siete nombres más citados **siguen sin existir en ninguna parte**.
- `reftriage.py` sigue sin poder distinguir "se borró" de "nunca existió":
  eso exige leer el documento, y la ventana de ±4 líneas es un umbral
  elegido, no un hecho.
- El código de salida de `artifacts.py` **sigue valiendo siempre 1**, porque
  los documentos que documentan ausencias los cuentan como rotos. Ahora al
  menos se ve por qué, que es lo que faltaba para decidir si se arregla.

## Método

Tres correcciones de patch seguidas, todas de la misma forma: **la
indentacion decide a que bloque pertenece el codigo**, y aqui el bloque se
acababa de quedar DENTRO de un `if not fnd:` que no se cumple. En dos casos
el script abortaba por asercion **antes de escribir**, y en el tercero
la sintaxis era valida y el bloque simplemente no se ejecutaba: ningun error,
solo ausencia de salida. Un programa que no hace nada no se parece a uno que
falla, y por eso el sintoma --"el parche no surtio efecto"-- no senala la causa.

`CORRECTED_BY=120-CORRECCION-POSTERIOR`.
