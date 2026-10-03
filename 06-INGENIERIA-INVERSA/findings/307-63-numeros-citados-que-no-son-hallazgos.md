# 307 · 63 numeros citados que no son hallazgos: 114 citas, y la mayoria no son referencias

```
PENDIENTE=307-1 | HALLAZGO=307-63-numeros-citados-que-no-son-hallazgos.md | ESTADO=PARTIAL
             | NECESITA=CORPUS | ALCANZABLE_SIN_ROOT=si
             | NOTA=la auditoria del registro ya existe; queda decidir si el 298 se recupera
```

## Que se midio

Despues de reparar las 1038 citas que si apuntaban al hallazgo equivocado
(`refs_repair.py --ambito todos --aplicar`), el contador
de `refs_colgadas()` da **0**. Se escribio un tercer contador, independiente,
que no importa nada del proyecto, y tambien da 0.

Ese mismo contador independiente pregunta una cosa distinta y mide otra
cosa: **citas a numeros que NO existen como hallazgo**. Salen **114 citas en 63
numeros**.

```
  hallazgos en disco                  518
  citas a numeros que no son hallazgo  114   en 63 numeros
  de esos 63, en el mapa de renumeraciones  1   (el 975)
```

## Por que esto NO es el mismo defecto que las 1038

Las 1038 eran **punteros erroneos**: la cita existia, el numero existia, y
apuntaba a OTRO contenido. Muy grave: no se ve nada roto.

Estas 114 son **citas a numeros que no son nada**. Y aqui la mayoria no son
citas a hallazgos: son **magia**, escrita entre acentos graves porque el autor
los usa para cifras.

Medido sobre el corpus, agrupando por numero:

```
  `1024` x14   el tamano del anillo, no un hallazgo   (y el 1002 sujeto es un
               hallazgo que ya se renumero a 212, asi que el numero que sigue
               al 1024 en el titulo es el viejo)
  `0298` x12   numero de LINEAS de una tabla de cobertura, no un hallazgo
  `6780`..`6800` x5  offsets de struct en polaris10
  `5907` x1    MiB del limite de TTM
  `1120` x2    lineas de salida de una herramienta
  `1311` x3    numero de linea accionable
  `4096` `8192` `2048`  tamanos
```

O sea: de 63 numeros, la mayoria absoluta son **cifras**. Un linter que
intentara "arreglar" estas citations las convertiria en referencias a
hallazgos que no existen, que es peor que dejarlas como estan.

## El caso que SI es una cita, y por que importa

`298` aparece 12 veces y no es una cifra: es el hallazgo de la **tabla de
cobertura de herramientas**, y el 300 lo cita por su contenido.

```
  301-cinco-vias-de-leer-banderas.md L130
    298   303 lineas, una fila con una bandera que no existe
    300   472 lineas, la fila corregida
    301   612 banderas propias en 151 ficheros, y el self-test que lo comprueba
```

Esa tabla **da titulo y numero de linea** de `298`. Eso prueba dos cosas a la
vez: que `298` existio como hallazgo, y que alguien lo leyo.

Y hay una tercera, medida: **`298` sigue reservado en `.nextnum.lock`**.

```
  $ grep -x 298 .nextnum.lock
  298
```

El allocator de numeros lo apunto y el fichero se perdio. Eso lo saca de la
categoria "nunca existio" y lo mete en "se perdio con la reserva todavia
viva", que es un fallo distinto: **el allocator y el corpus se han
desincronizado**, y el un no se entera de que el otro perdio una entrada.

Medido tambien:
- no esta en el mapa de renumeraciones (`REENVIO-FINDINGS.tsv`, 43 pares)
- no esta en ninguna rama de git: `git rev-list --all` sobre 390 commits, y
  `git ls-tree` de cada uno sobre `findings/` no encuentra un `298-*`

Del resto de los 62, en cambio, ninguno esta reservado: `4`, `507`, `444`,
`1024`, `5907` son libres. Eso es lo que se esperaria si losMagic son cifras y
no entradas del allocator.

**Estado de `298`: `NOT_FOUND`, con evidencia de que existo y de que el
allocator lo sigue creyendo.** No es una referencia rota: es una referencia a
un hallazgo que se perdio sin dejar reenvio.

## Por que no se arregla

Arreglarlo exigiria saber a que hallazgo corresponde cada una. Para `298`, el
contenido que se le atribuye es "la tabla de cobertura de herramientas, 303
lineas, una fila con una bandera que no existe", y el hallazgo 278 es
`el-recuento-de-cobertura-de-polaris10-por-fin` y el 213 es
`herramienta-de-cobertura-de-escrituras-en-la-sram`. Ninguno de los dos es el
`298`: uno es de registros SMC y el otro de escrituras.

La cifra **303** aparece en `301` como "lineas de la tabla de cobertura", y hay
un hallazgo (`291`) que habla de "doce cifras de poblacion, diez sin fecha y
ninguna commiteada". Que un hallazgo sobre cifras de poblacion este commiteado
y el hallazgo que las producia no, es exactamente el tipo de cosa que ese
hallazgo describe.

Esto **no se cierra aqui**: es una pregunta de investigacion, no una
reparacion mecanica. Y es de la clase `NOT_FOUND`, no de la clase puntero
erroneo. Confundirlas seria repetir el error que produjo las 1038 al reves.

## Auditoria del registro, y el 975 que NO es lo mismo

`tools/nextnum.py --auditar` existe ahora, y separa lo que antes se contaba
junto. Medido:

```
  reservas vivas                     38
  con fichero detras                 36
  SIN fichero detras                  2
    clase RENUMERADO                  1    975 -> ahora 976
    clase SIN ORIGEN DEMOSTRABLE      1    298
```

**El 975 no es una perdida.** Es un resto: su hallazgo se renumero a 976 y la
reserva del numero viejo quedo. Y `975 -> 976` esta en el mapa congelado, con
`reasignado=no`, que es exactamente la clase que el mapa registra cuando el
numero viejo quedo libre sin quedar ocupado por otro.

Juntos en un solo numero, el informe decia "2 fugas" y no decia si habia algo
que recuperar o si habia dos numeros que liberar. Separados, hay **una** perdida
posible y **un** resto que limpiar.

### Por que no se libera el 298

`reservados()` y `siguiente()` hacen bien su trabajo: `siguiente()` respeta la
reserva aunque no haya fichero, asi que el allocator no va a entregar el 298 por
error. El defecto no es de asignacion, es que el **registro deja de ser estado**:

```
  "298" en .nextnum.lock  se lee igual que
  "299" en .nextnum.lock  <- alguien esta escribiendo ahora mismo
```

y no hay forma de distinguirlos. Liberar el 298 cerraria el sintoma y taparia
el defecto real, que es que **nada comprueba que una reserva siga teniendo
fichero detras**. Con `--auditar` ya lo hay.

## Que NO se ha hecho

- No se ha escrito un linter que "arregle" estas 114 citas. Haria mas dano.
- No se ha declarado `PROVEN_ABSENT` para `298`. Se sabe que existio.
- No se ha liberado el 298 de `.nextnum.lock`, ni el 975.
- No se ha tocado ninguna cita de las 114. El corpus queda como estaba.

## Tesis que sostiene

Una cita entre acentos graves no significa "cita a un hallazgo". Significa
"esto va en codigo". Lo que decidia el significado era el **contenido**, y esa
es la parte que un regex no tiene.

La consecuencia practica: cualquier herramienta que mida citas tiene que
**contar al menos dos clases**, porque "numero entre acentos" las mezcla. Y la
que decide es la de `num not in hallazgos`, no la de `num renumerado`.

## Limite

El agrupamiento "cifra" / "cita" de esta tabla esta hecho leyendo las 12
muestras mas numerosas y unas cuantas más, NO las 114 una por una con un
criterio declarado. La proporcion real de cifras esta `NOT_DETERMINED`. Lo que
si esta medido al numero es esto: 63 numeros, 114 citas, 1 en el mapa de
renumeraciones.

## Como reproducirlo

Contador independiente, sin importar nada del proyecto:

```python
nums = {int(nombre.split("-")[0]) for nombre en glob(findings/*.md)}
for cada fichero, for cada `` `(\d{3,4})` ``:
    if v not in nums: contarlo
```
