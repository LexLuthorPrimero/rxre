# 308 · 74 numeros de hallazgo estan duplicados, y 1739 citas no saben a cual se refieren

```
PENDIENTE=308-1 | HALLAZGO=308-setenta-y-cuatro-numeros-colisionan-y-1739-citas-no-saben-a-cual.md
             | ESTADO=NOT_DETERMINED
             | NECESITA=CORPUS | ALCANZABLE_SIN_ROOT=si
```

## Que se midio

Despues de reparar las 1038 citas que apuntaban al hallazgo equivocado, queda
un defecto del mismo genero y mas grande.

```
  hallazgos en disco                      520
  numeros distintos                        419
  numeros con COLISION                     74
  ficheros implicados en colisiones       175
  citas a esos numeros, sin resolver      1739
  de los 74, citados por alguien          72
```

1739 es mas que las 1038 del hallazgo anterior. Y a diferencia de aquellas,
esta vez **no hay mapa**: no existe ninguna tabla que diga a que numero
pertenece cada cita, porque la ambiguedad no viene de un renumerado, sino de
que dos hallazgos distintos comparten numero desde el principio.

## Las dos clases, medidas y NO confundidas

```
  colisiones con el MISMO stem (mismo hallazgo en dos ficheros)   0
  colisiones con stems DISTINTOS (dos hallazgos, un numero)      74
```

Las 74 son de la segunda clase. Ejemplos:

```
  `001`  001-amdgpu-location.md
         001-amdgpu-overview.md
  `023`  023-pte-productor-sdma-gfx8.md
         023-pm4-count-convencion-medida.md
```

No es que un hallazgo este duplicado: es que dos hallazgos distintos se
 reparten el mismo numero. Por eso **no hay reparacion mecanica posible**: no
 hay nada que "arreglar", hay algo que **elegir**.

## El contexto desambigua a veces (se cuenta mas abajo, con el instrumento)

El contexto SI desambigua a veces. Medido, con el caso de `023`:

```
  029-release-mem-y-eop-exec-muerto.md L84
    Verificacion con la herramienta de `023` (`pm4_count_census.py`, que mide
```

La linea nombra `pm4_count_census.py`, y ese identificador esta en
`023-pm4-count-convencion-medida.md`. El autor sabe cual quiere decir. Un
lector con el fichero abierto tambien.

## Lo que se puede automatizar: MEDIDO, con instrumento

`08-ARQUITECTURA/tools/ambig_citas.py` mide el reparto en tres clases, y no
adivina: una "pista" es una palabra del titulo de uno de los candidatos que
aparece en la linea que cita. Las palabras de estructura en castellano (para,
porque, cuando, mismo, forma...) se descartan, porque aparecen en casi
cualquier linea y convertirian la heuristica en ruido.

```
  citas ambiguas                          1739
  con pista que DECIDE (un solo candidato)  270   (15%)
  con pista que NO decide (varios)            5
  sin ninguna pista                       1464   (84%)
```

La cifra se movio de 1736 a 1739 al escribir este propio hallazgo: la tabla de
arriba nombra candidatos, y al nombrarlos produjo tres citas nuevas de su propia
clase. **Un documento que describe la ambiguedad la reproduce.** Por eso el
reparto de arriba es el que dice `ambig_citas.py` en este momento y no una
cifra guardada, y por eso el artefacto se regenera en vez de editarse.

**Y la cifra no es la que decia una medicion previa.** Aquella decia 315 y esta
dice 270. La diferencia son las palabras de estructura: 315 cuenta pistas que
nombran algo del hallazgo, 270 cuenta pistas que ademas son distinguibles. Las
dos son correctas si se dice cual se esta contando, y por eso el instrumento
declara la lista.

## La heuristica ACIERTA, y eso es lo que hay que mirar

Con cobertura no se decide nada. Se lee. Diez citas con pista, a mano:

```
  la linea dice                              elijio                                   verdict
  "los diez selectores de despacho"          los-diez-selectores-y-el-limite         OK
  "el MTYPE que no existe"                   g-el-mtype-no-existe-en-gfx8             OK
  "el codigo de salida del validador"        validador-flujo-y-regla-del-count        OK
  "`133` (el MTYPE)"                         g-el-mtype-no-existe-en-gfx8             OK
  "el documento que declara que manda"       el-documento-que-declara-que-manda       OK
  "`096` (el mecanismo de fence)"            se-mecanismo-de-fence-completo           OK
  "El spec de GFX8 no esta publicado"        mmu-vm-no-publicado                      MAL
  "el spec de GFX8, que ya establecio que    mmu-vm-no-publicado                      MAL
   no esta publicado"
  "corroboracion desde otra tabla"           tabla-de-relojes-dpm-reconstruida        dudoso
  "`096` tambien afirmaba una invasion:      arbitraje-dram-...-tabla-de-ventilacion  dudoso
   la de la tabla de..."
```

**6 correctos, 2 equivocados, 2 sin forma de decidir.** Precision ~75%.

Los dos fallos tienen la misma causa y es instructiva: la linea habla de "el
spec de GFX8 que no esta publicado", y el criterio hizo caso a la palabra
"publicado". El hallazgo que realmente significa es el del PM4 spec inexistente,
no el de mmu-vm-no-publicado. **El criterio busca una palabra suelta; la cita
quiere decir una cosa entera.**

### Por que NO se aplica automaticamente

270 casos con ~25% de error son unas **68 referencias nuevas equivocadas**.
Eso es exactamente la clase de dano que `refs_repair.py` acaba de eliminar de
1038 citas: un puntero que apunta a otro sitio y no se ve roto.

Aplicarla sola daria, de 1739 citas, 270 mejor y 68 peor. Y un linter que
"limpia" y por el camino crea 68 referencias rotas es peor que uno que no hace
nada: por lo menos el que no hace nada no engana.

## Por que esto no se arregla aqui, y por que no es un bug

Es `NOT_DETERMINED` y no `FAILING`. Hay tres salidas legitimas y elegir una es
una decision de politica del proyecto, no una reparacion mecanica:

1. **Renumerar uno de los dos** de cada colision. Cierra la ambiguedad, pero
   produce mas referencias colgando si no se accompanies de una reparacion del
   mismo rigor que la de `refs_repair.py`. Y hay 74, no 43.
2. **Declarar que el numero es una etiqueta y la clave es el `stem`.** Es lo que
   ya dice `ESTADO.md` §5 ("el numero no identifica a un finding; para citar,
   usar el nombre del fichero"), y es la unica que no genera trabajo futuro.
   Pero cambiar eso obliga a las 1739 citas, y es la unica de las tres que
   **no depende de acertar esas 1739 decisiones**. Las otras dos dependen.
3. **Dejarlo y marcar cada cita ambigua**, para que quien lea sepa que tiene
   que abrir los dos ficheros.

Lo que NO es una salida: un script que elija el primero que encuentre.

## El informe, que es lo que si se puede automatizar sin decidir nada

`08-ARQUITECTURA/tools/ambig_citas.py`:

```
  ambig_citas.py                 reparto en tres clases
  ambig_citas.py --resumen       por numero: candidatos, citas, con_pista
  ambig_citas.py --pistas        solo las que tienen pista, y a quien apuntan
  ambig_citas.py --tsv           una linea por cita, para hoja de calculo
  ambig_citas.py --escribir DIR  deja el .tsv y el .json
```

No elige. No reescribe. Para cada cita da los ficheros que puede significar y si
hay pista, que es el insumo de la decision sin ser la decision.

Su self-test tiene 9 vectores, y se comprobo mutando una copia: no filtrar la
auto-cita, no filtrar la colision, dar pista a todos los candidatos, forzar el
estado a "decide", y no aplicar la lista de palabras de estructura. Las cinco
mutaciones las detecta.

**Estado: `NOT_DETERMINED`.** El trabajo automatico esta hecho; el trabajo
humano es elegir la politica.

## Tesis que sostiene

Reparar las 1038 fue posible porque existe un **dato externo** que dice a donde
va cada cita: el mapa de renumeraciones. Aqui no hay dato externo, porque la
ambiguedad no es un error de una tabla: es que el identificador no es un
identificador.

Un identificador que no es unico no se arregla reescribiendo lo que lo usa.
Se arregla dejando de usarlo como identificador. Y eso no se puede hacer con
un script, porque es una decision sobre lo que el proyecto considera que es
un hallazgo.

## Como reproducirlo

```python
nums = {}
for f in glob("findings/*.md"):
    n = int(f.split("-")[0])
    nums.setdefault(n, []).append(f)

# numeros con mas de un fichero
col = {n: v for n, v in nums.items() if len(v) > 1}

# citas a esos numeros desde ficheros cuyo numero NO es ese
for f in todos:
    if int(f.split("-")[0]) in col:
        for m in re.finditer(r"`(\d{3,4})`", cuerpo):
            if int(m.group(1)) in col and int(m.group(1)) != int(f.split("-")[0]):
                contarlo
```
