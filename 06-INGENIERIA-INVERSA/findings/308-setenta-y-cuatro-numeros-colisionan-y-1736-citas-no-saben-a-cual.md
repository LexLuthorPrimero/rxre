# 308 · 74 numeros de hallazgo estan duplicados, y 1736 citas no saben a cual se refieren

```
PENDIENTE=308-1 | HALLAZGO=308-setenta-y-cuatro-numeros-colisionan-y-1736-citas-no-saben-a-cual.md
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
  citas a esos numeros, sin resolver      1736
  de los 74, citados por alguien          72
```

1736 es mas que las 1038 del hallazgo anterior. Y a diferencia de aquellas,
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

## Por que el contexto desambigua en unos casos y en otros no

El contexto SI desambigua a veces. Medido, con el caso de `023`:

```
  029-release-mem-y-eop-exec-muerto.md L84
    Verificacion con la herramienta de `023` (`pm4_count_census.py`, que mide
```

La linea nombra `pm4_count_census.py`, y ese identificador esta en
`023-pm4-count-convencion-medida.md`. El autor sabe cual quiere decir. Un
lector con el fichero abierto tambien.

Lo que se midio es cuanto se puede automatizar, y la respuesta es: poco.

```
  citas ambiguas                                        1736
  con una palabra del TITULO del hallazgo en la misma linea  315
  sin ninguna pista de ese tipo                          1421
```

Una heuristica de "palabra del titulo en la linea" acierta en 315 de 1736 y no
dice nada de las otras 1421. **Aplicarla solo** daria un resultado donde el 81%
queda igual: exactamente el defecto que se estaba reparando, a otra escala.

## Por que esto no se arregla aqui, y por que no es un bug

Es `NOT_DETERMINED` y no `FAILING`. Hay tres salidas legitimas y elegir una es
una decision de politica del proyecto, no una reparacion mecanica:

1. **Renumerar uno de los dos** de cada colision. Cierra la ambiguedad, pero
   produce mas referencias colgando si no se accompanies de una reparacion del
   mismo rigor que la de `refs_repair.py`. Y hay 74, no 43.
2. **Declarar que el numero es una etiqueta y la clave es el `stem`.** Es lo que
   ya dice `ESTADO.md` §5 ("el numero no identifica a un finding; para citar,
   usar el nombre del fichero"), y es la unica que no genera trabajo futuro.
   Pero cambiar eso obliga a las 1736 citas.
3. **Dejarlo y marcar cada cita ambigua**, para que quien lea sepa que tiene
   que abrir los dos ficheros.

Lo que NO es una salida: un script que elija el primero que encuentre.

## Lo que si se puede automatizar sin decidir nada

Un informe, no una reparacion: para cada cita ambigua, los ficheros que puede
significar, y si la linea contiene alguna pista. Eso es una **carta de
amplitud**: convierte "el numero es ambiguo" en "este numero lo tienen estos
tres hallazgos y esta linea menciona tal palabra". Con eso, la decision de
politica se puede tomar con la lista delante en vez de con una cifra.

**Estado: `NOT_DETERMINED`.** El trabajo automatico que falta es el informe de
amplitud; el trabajo humano que falta es elegir la politica.

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
