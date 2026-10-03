# 165 · El 1,75% de `display/` es el cálculo de modos de esta GPU; el 24,8% es el que no corre

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**La pregunta de viabilidad de todo el proyecto: cuánto de este driver hay que escribir
para una GPU, y cuánto hay que leer para saberlo.** Y la respuesta sale restando, como
salió el 58% de `157`.

**Y de paso responde una pregunta que llevaba quince notas sin medir: cuánta parte de
`display/` es genérica y cuánta es por generación.** La respuesta es que **la pregunta no
tiene una respuesta única, y las dos respuestas honestas difieren en 18,7 puntos
porcentuales** — pero el reparto por bloques da un número que sí decide.

## 1 · La partición es exacta, y por eso se puede restar

`display/` completo, medido por programa sobre 510 ficheros:

| | ficheros | líneas | % |
|---|---|---|---|
| por generación (la ruta tiene un segmento `dceNNN`/`dcnNNN`/`rvN`/`rn`/`vg`) | 308 | 254.882 | 57,4% |
| genérico | 202 | 188.957 | 42,6% |
| **suma** | **510** | **443.839** | |

**254.882 + 188.957 = 443.839 exactamente, y los dos conjuntos particionan el árbol sin
solaparse.** `PROVEN`, y la partición es lo que permite restar.

**Y el total, 443.839, es el mismo de `151` y `147`, medido por tercera vez con un
procedimiento distinto.** `PROVEN`.

## 2 · Y los dos criterios se contradicen, y esa contradicción es el hallazgo

El mismo árbol, clasificado de otra manera —¿el **nombre** del fichero lleva prefijo de
generación?—, da:

| criterio | por generación | genérico |
|---|---|---|
| por **ruta** (el directorio es de una generación) | **57,4%** | 42,6% |
| por **nombre** (el fichero lleva prefijo) | **38,7%** | 61,3% |

**Discrepancia: 18,7 puntos porcentuales.** Medido por programa. `PROVEN`.

**⇒ «Cuánta parte del driver de display es genérica» no tiene una respuesta única. Las dos
respuestas honestas difieren en casi un quinto del árbol.** `PROVEN_DERIVED`.

**Y la razón de la discrepancia es que hay tres cosas distintas que se confunden:**

| | ejemplo | por ruta | por nombre |
|---|---|---|---|
| directorio de generación con nombre neutro | `clk_mgr/rv1_clk_mgr.c`, `dml2_0/dc_dml2.c` | cuenta como genérico | cuenta como genérico |
| fichero de generación en directorio neutro | `dc/dce/dce_clock_source.c` (contiene ramas `dce112_*`) | genérico | **por generación** |
| directorio de generación con fichero de otro nombre | `dce100/dce_clk_mgr.c` | **por generación** | genérico |

**Los dos criterios se equivocan en sentidos opuestos, y por eso la media de los dos es
más honesta que cualquiera de los dos.** `PROVEN_DERIVED`.

**Y hay un cuarto criterio, el que de verdad responde a la pregunta, y es el
comportamiento en runtime:** En `151`, `using_dml2` es falso o está ausente en los seis
DCE, y el único camino a `true` es la máscara de depuración `DC_ENABLE_DML2`. **Es decir:
en esta máquina, el particionado real no es por ruta ni por nombre, es por si el código
llega a ejecutarse.** `PROVEN_DERIVED`.

## 3 · Y el reparto por bloques, que es el número que decide

`display/dml/` contiene DML1 **y** los directorios por generación de DML2. Separados:

| bloque | `.c` | líneas | % de `display/` | ¿corre aquí? |
|---|---|---|---|---|
| `dml/` (primer nivel) | 4 | 3.788 | 0,85% | **sí** |
| `dml/calcs/` | 3 | 3.698 | 0,83% | **sí** |
| `dml/dsc/` | 1 | 260 | 0,06% | **sí** |
| **DML1 total** | **8** | **7.746** | **1,75%** | **sí** |
| `dml/dcn*` (DML2 por generación) | 27 | 70.181 | 15,8% | no |
| `dml2_0/` (DML2 núcleo) | 31 | 40.058 | 9,0% | no |
| **DML2 total** | **58** | **110.239** | **24,8%** | **no** |

**⇒ El cociente DML2 / DML1 es 14,2 a 1.** `PROVEN`.

**⇒ El motor de cálculo de modos de esta GPU son 7.746 líneas, el 1,75% del árbol. Y el
motor de cálculo de modos que no se usa son 110.239, el 24,8%.** `PROVEN_DERIVED`.

**Y los seis bloques por generación más grandes del árbol son los seis directorios de
DML2, y ninguno corre aquí:**

| directorio | líneas | % de `display/` |
|---|---|---|
| `dc/dml/dcn20` | 16.256 | 3,7% |
| `dc/dml/dcn32` | 14.327 | 3,2% |
| `dc/dml/dcn31` | 9.678 | 2,2% |
| `dc/dml/dcn314` | 9.481 | 2,1% |
| `dc/dml/dcn30` | 8.906 | 2,0% |
| `dc/dml/dcn21` | 7.960 | 1,8% |
| **los seis juntos** | **66.608** | **15,0%** |

**⇒ El mayor bloque de código por generación de amdgpu es código que esta GPU no ejecuta,
y es el 15% del árbol de display.** `PROVEN_DERIVED`.

**Y esto es exactamente el patrón de `159` en su forma inversa.** Allí el coste de una
generación nueva era el 21% de la anterior, porque las nuevas heredan; aquí la
consecuencia es que **el 24,8% del driver de display es un motor de cálculo que una
generación de chip de 2013 no ejecuta y dos de 2019 sí, y 2013 cuesta el 1,75%.**

## 4 · El reparto completo, y lo que significa para un driver propio

| | líneas | % de `display/` |
|---|---|---|
| **DML1 — el cálculo de modos que corre** | **7.746** | **1,75%** |
| DML2 — el cálculo de modos que no corre | 110.239 | 24,8% |
| resto — enlace, reloj, IRQ, tablas de recursos, pegamento | 325.854 | 73,4% |

**⇒ El 73,4% restante no es «código de otros chips» ni «código de este chip»: es el
entrenamiento de enlaces, los 160 registros de HDP, el gestor de reloj, el decodificador
de interrupciones, las tablas de swizzle y el pegamento con DRM — todo lo que las quince
notas anteriores han medido subsystem por subsystem.** `PROVEN_DERIVED`.

**Y el reparto de este chip concreto dentro de ese 73,4%, con todo lo medido:**

| subsistema | referencia | líneas | qué se hereda |
|---|---|---|---|
| enlace y protocolos | `link/` | 19.451 | `dce110_*`, 4 carriles, HBR3 |
| decodificador de IRQ | `irq/` | 7.870 | `irq_service_dce110.c`, 6 tuberías |
| gestor de reloj | `clk_mgr/dce112` | 237 | `dce_clk_mgr_construct` de DCE 10.0 |
| fichero de recursos | `resource/dce112` | 1.442 | 5 subsistemas `dce110_` |
| codificador de stream | `dce/` | 17.841 | `dce110_str_enc_funcs`, 22 de 38 |
| **código propio de DCE 11.2** | varios | **52 funciones** | el 21% de DCE 11.0 |

**⇒ Para una implementación propia, el número accionable es este: 1.442 líneas de
cableado, 52 funciones propias, y 7.746 líneas de cálculo de modos.** `PROVEN_DERIVED`.

**Y el resto son 325.854 líneas de las que esta GPU usa una fracción, y esa fracción está
en `link/`, `irq/` y en los ficheros compartidos que `232` ya había localizado.**

## Lo que NO cierra

| afirmación | estado |
|---|---|
| La partición es exacta: 254.882 + 188.957 = 443.839 | `PROVEN` |
| 510 ficheros, 443.839 líneas, medido por tercera vez | `PROVEN` |
| Por ruta: 57,4% por generación. Por nombre: 38,7% | `PROVEN` |
| Discrepancia de 18,7 puntos porcentuales | `PROVEN` |
| Los tres casos que hacen discrepar los criterios | `PROVEN_DERIVED` |
| El particionado real es por ejecución, no por ruta | `PROVEN_DERIVED` |
| DML1: 8 `.c`, 7.746 líneas, 1,75% | `PROVEN` |
| DML2: 58 `.c`, 110.239 líneas, 24,8% | `PROVEN` |
| Cociente DML2 / DML1 = 14,2 a 1 | `PROVEN` |
| Los 6 mayores bloques por generación son DML2 y no corren | `PROVEN_DERIVED` |
| DML1 + DML2 + resto = 443.839 | `PROVEN` |
| Cuántas de las 325.854 líneas ejecuta esta GPU | **`NOT_DETERMINED`** |
| Cuál es el reparto exacto entre enlace, reloj e IRQ en ejecución | **`NOT_DETERMINED`** |
| Si `151` cuenta 20 ficheros como 8 `.c` + 12 `.h` y eso es DML1 | **`PROVEN_DERIVED`** |

**La primera de las abiertas es la que queda, y no se cierra leyendo: es la línea base
completa.** *Y se puede acotar sin leer 325.854 líneas:* de los 6.384 datos de `drm_info`
—la línea base de conocida por cada objeto de la GPU— sale el subconjunto que esta
generación*DML1* ejecuta, y `drm_info` lo da el driver al arrancar.

## Procedencia

- `STATIC` -- medición sobre `display/` con `os.walk` y dos criterios de clasificación
  implementados explícitamente: (a) la ruta contiene un segmento que casa con
  `^(dce\d+|dcn\d+[a-z]*|dcn3\d+…|rv1|rv2|rn|vg|vega\d*|nv\d*)$`;
  (b) el nombre del fichero casa con `^(dce\d+|dcn\d+[a-z]*|rv\d|rn|vg)_`. Conteo
  recursivo de ficheros `.c` y suma de líneas.
  Directorios citados: `display/dml/` con `calcs`, `dsc` y los trece `dcn*`;
  `display/dc/dml2_0/` recursivo; `display/dc/link/`, `display/dc/irq/`,
  `display/dc/clk_mgr/dce112/`, `display/dc/resource/dce112/`, `display/dc/dce/`.
- Las cifras de DML1, DML2, DML2-por-generación y la partición exacta, todas impresas por
  programa, con la comprobación `254.882 + 188.957 = 443.839` y la comprobación
  `8 + 58 = 66` ficheros y `7.746 + 110.239 = 117.985` líneas.
- **Dos errores míos en esta nota, ambos de la misma clase y ambos cazados por el
  programa:**
  (1) **la función de recuento era recursiva y se comió los subdirectorios `dcn*` de
  `dml/`**, contando DML1 como 39 `.c` y 81.885 líneas; el cociente salía **1,3 a 1** en
  vez de **14,2 a 1**, un factor de once equivocado. Corregido con dos variantes,
  `nonrec` y `rec`, y elegido explícitamente para cada bloque.
  (2) **escribí «33 puntos porcentuales» haciendo la resta a mano** cuando el programa
  imprimió 18,7. La resta de cabeza no es un programa.
- **Y `151` queda confirmado por tercera vez con un procedimiento distinto:** los 20
  ficheros y 11.875 líneas son exactamente `dml/` + `calcs` + `dsc`, contando `.c` y `.h`.
  **Y eso significa que los 20 ficheros de `151` son DML1, o sea el 1,75% de `display/`.**
- Encadenada con `151` (**su «motor de mode-setting de 20 ficheros» es el bloque DML1, y
  esta nota lo pone en su sitio: 1,75% del árbol**), `159` (el coste de una generación
  nueva, 21%, y aquí su consecuencia: 24,8% del árbol es DML2), `157` (el 58%, que salió
  de restar dos inventarios; esta nota sale de restar dos particiones),
  `232` (la tabla y el constructor, y aquí el reparto de 1.442 líneas de cableado),
  `162` (6 tuberías, 21 ficheros de IRQ), `161` (237 líneas de reloj),
  `160` (19.451 líneas de enlace), `155` (DCE 11.2), `153` (los siete `path`),
  `140`, `136`, `132`, `130` (memoria, verificada en `233`).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**Los dos errores de esta nota tienen la misma raíz, y es la raíz de la cuarta y la quinta
corrección del bloque: yo confié en una función que no hacía lo que yo creía que hacía.**

*La primera: le pedí «cuéntame las líneas de `dml/`» y me contó las de `dml/` **y** las
de los trece `dcn*` que hay dentro, porque la función caminaba en profundidad y yo no lo
sabía.* El resultado no era un error de aritmética: era **un conjunto distinto**, y
comparar DML1 con DML2 así es comparar un fichero con una carpeta. **El número que
imprimió, 81.885, era correcto para la pregunta que hizo la función, y esa no era mi
pregunta.** *Y por eso el error se escondió: un resultado plausible que responde a otra
pregunta es más peligroso que un resultado absurdo.*

*La segunda: resté 57,4 − 38,7 a mano y escribí 33.* Ninguna de las dos cifras del programa
era mía, y aun así las resté yo. **Toda resta entre dos números que imprime un programa
tiene que imprimirla el programa**, y esa regla estaba en la lista desde el principio de
la tanda y se incumplió en la misma frase que la cumplía dos párrafos antes.

**Y el resultado de fondo es la clase de número que no se obtiene leyendo: se obtiene
restando dos cosas que nadie había relacionado.** *Quince notas han medido subsistemas —
enlace, reloj, IRQ, codificador, tablas— y ninguna los había sumado contra el total
porque el total no era el número que interesaba.* **Al medir «qué fracción de
`display/` es el motor de cálculo de modos» aparece de golpe que la respuesta es 1,75%, y
que el 24,8% es un motor de cálculo que esta GPU no ejecuta.** *Los quince números
medidos siguen siendo ciertos y ninguno era suficiente: lo que faltaba era el
denominador, y un denominador no se encuentra midiendo el numerador otra vez.*
