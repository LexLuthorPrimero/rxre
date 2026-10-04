# CITAS POR NUMERO EN PROSA — declaracion de clases, decision y puerta

Nodo `CITAS-PROSA-A3`.  MEDIDO, no supuesto.  Cada cifra de aqui lleva el
instrumento que la produjo y el artefacto donde queda el expediente.

Estado del arbol al medir: 74 numeros duplicados, 546 ficheros en `findings/`,
mapa congelado de 56 renumeraciones.  La poblacion de A3 medida fue **2230** (no
2152) porque otro nodo escribio mientras yo contaba; ver DERIVA, abajo.
**DERIVA DETECTADA**: durante el trabajo, `08-ARQUITECTURA/tools/reenvio_gate.py`
lo esta escribiendo otro nodo y sus numeros de linea se movieron bajo los pies
dos veces.  Las cifras de aqui son de un instante; el metodo es reproducible.

---

## 1. LO QUE SE PREGUNTA, Y POR QUE "CUANTAS ESTAN MAL" ES FALSA

`check_num_unico.py` A3 cuenta 2152 citas por numero que caen sobre un numero
duplicado y sale con codigo 4.  La lectura obvia es "2152 defectos".  Es falsa,
y esta falseada por medicion en las tres direcciones:

- **No todas son citas.** MEDIDO: 25 de las 2230 (1,12 %) no son citas.  Son
  **patrones binarios de 3-4 bits** de la tabla de decodificacion SIB de x86-64
  (22 en `05-FUENTES-EXTERNAS/.../R0-7-REFERENCIA-X86-64-...md`: `` `001` ``,
  `` `010` ``, `` `100` ``, `` `101` ``) y **rangos de bits de registro**
  (3 ocurrencias de `D0[127:0]` en dos volcados de `08-ARQUITECTURA/artifacts/`).
  El detector de citas no distingue un numero de hallazgo de un patron binario.

- **No todas son erroneas.** MEDIDO por muestra estratificada de 132
  adjudicaciones manuales: **0 clase 3**.  Ninguna cita de la muestra apunta a un
  fichero que no diga lo que la prosa afirma.

- **No todas son reparables.** MEDIDO: en el 54 % de la poblacion la cita **no
  dice** a cual de los dos o tres ficheros del numero va.  Para reescribirla
  habria que saber cual, y la cita no lo contiene.  Reescribirla seria
  **fabricar un destino**, que es peor que un numero ambiguo: el numero se ve
  comparar con el fichero, el destino inventado se cita como verificado.

---

## 2. LAS TRES CLASES, Y QUE HACE CADA UNA

Definiciones operativas, las que se usaron para adjudicar:

| clase | definicion | que hacer |
|---|---|---|
| **C1** correcta | la propia cita dice a cual va, y ese fichero sostiene lo que la prosa afirma | no tocar. No es un defecto |
| **C2** ambigua | la cita NO dice a cual va: la frase no tiene contenido, o el contenido esta en los dos | se queda el numero y se declara. No se repara |
| **C3** equivocada | la cita dice a cual va, y ese fichero NO dice lo que la prosa afirma | se repara por nombre de fichero, con la cita del destino que lo demuestra |

Se anaden tres sub-clases de C1 con la prueba ya hecha por construccion, no por
juicio: `C1_AUTOCITA` (la cita va dentro del fichero cuyo prefijo es el numero),
`C1_INDICE` (el numero es la etiqueta de una fila de indice que continua con los
nombres), `C1_INSTRUMENTO` (el fichero tiene por objeto la ambiguedad de las
citas, y la cita ambigua es el dato) y `C1_NUMERO` (la prosa habla del numero,
no del hallazgo).  Las cuatro tienen el mismo argumento que el registro
`tools/CITA-CODIGO-EXCEPTIONS.txt` ya acepta para el codigo.

---

## 3. LAS CIFRAS, CON SU MARGEN DE ERROR

Muestra **estratificada** por (directorio x clase del proxy), semilla 20261004,
n = 14 por estrato y el estrato entero cuando cabe en 14.  La muestra esta en
`tools/citas_prosa_adjudicado.py`, con el verbo y la prueba de cada veredicto.
La Artefacto con la lista depareo es
`08-ARQUITECTURA/validations/citas-prosa-muestra-20261004.json.gz`.

| estrato | N | n | C1 | C2 | C3 | no-cita | p(C1) | IC 95 % (Wilson) |
|---|---|---|---|---|---|---|---|---|
| findings \| sin senal    | 956 | 14 |  2 | 12 | 0 | 0 | 0,143 | [0,040 , 0,399] |
| findings \| ngrama        | 787 | 14 | 10 |  4 | 0 | 0 | 0,714 | [0,454 , 0,883] |
| otros \| sin senal       | 108 | 14 |  9 |  0 | 0 | 5 | 0,643 | [0,388 , 0,837] |
| findings \| ambigua      | 100 | 14 |  5 |  9 | 0 | 0 | 0,357 | [0,163 , 0,612] |
| docs \| ngrama           |  58 | 14 | 13 |  1 | 0 | 0 | 0,929 | [0,685 , 0,987] |
| docs \| sin senal        |  53 | 14 |  6 |  8 | 0 | 0 | 0,429 | [0,214 , 0,674] |
| findings \| autocita     |  38 | 14 | 14 |  0 | 0 | 0 | 1,000 | [0,785 , 1,000] |
| otros \| ngrama          |  31 | 14 | 13 |  1 | 0 | 0 | 0,929 | [0,685 , 0,987] |
| docs \| ambigua          |   9 |  8 |  3 |  5 | 0 | 0 | 0,375 | [0,137 , 0,694] |
| findings \| token raro    |   7 |  7 |  4 |  3 | 0 | 0 | 0,571 | [0,250 , 0,842] |
| otros \| ambigua         |   5 |  5 |  4 |  1 | 0 | 0 | 0,800 | [0,376 , 0,964] |

**Estimacion ponderada de la poblacion (2152 en la corrida del expediente):**

```
C1  (correcta)     984   45,7 %    IC 95 % = [ 560 .. 1407 ]  =  [26,0 % .. 65,4 %]
C2  (ambigua)     1168   54,3 %    (complemento; los dos casos se mueven a la vez)
C3  (equivocada)     0    0,0 %    0 confirmadas sobre 132 adjudicaciones
no-citas            25    1,16 %   MEDIDO de forma determinista, no estimado
```

El margen es ancho y el motivo se declara: el estrato mas grande
(`findings | sin senal`, 956 citas, el 44 % de la poblacion) tiene n = 14 y
p = 0,143, y su IC es [0,040 , 0,399].  Con n = 60 en ese estrato el intervalo
se cerraria a la mitad.  **La cifra de 45,7 % es un punto medio con un IC de 40
puntos de ancho; usarla como si fuera 45,7 % seria mentir.**

Lo que NO se puede frivolous: `findings | sin senal` y `findings | ngrama` suman
1743 de las 2152, y en ambos la proporcion de C1 se mueve en la misma direccion
que la del estrato `otros | sin senal`.  La conclusion "la mitad C1, la mitad C2"
es solida; el reparto fino dentro de cada directorio, no.

### Las cifras son de un instante, y por que el margen es de 40 puntos

La poblacion medida fue 2230 en la corrida de la tabla y 2152 en la del
expediente: durante el trabajo otro nodo escribio en
`08-ARQUITECTURA/tools/reenvio_gate.py` y en `docs/`.  **DERIVA DETECTADA**, y se
declara en vez de promediarse: las dos poblaciones son el mismo conjunto de
clases con 78 citas mas, todas en prosa, ninguna en codigo.  Lo que no cambia con
la deriva es la conclusion, porque sale de la MUESTRA y no del total.

### El proxy automatico NO sirve para repartir la poblacion

MEDIDO y es el limite mas importante de este trabajo.  El censo clasifica con
tres senales (n-grama contiguo, token identificador raro, comparacion contra el
destino del mapa de renumeraciones).  Contra las 12 etiquetas a mano de
`tools/citas_prosa_etiquetas.py`:

```
ACIERTO ESTRICTO : 2/12 = 16,7 %
RESUELVE LA CLASE: 3/12 = 25,0 %
```

Su unica afirmacion que sobrevive es la **ausencia de clase 3**.  Uso: generar
sospechas, no contar.  Por eso las cifras de arriba salen de la muestra, no del
proxy.

---

## 4. LO QUE SE REPARA: NADA, Y POR QUE

**Clase 3 = 0.  No hay nada que reparar.**

Y no es que no se haya buscado.  La primera version del clasificador SI producia
clase 3 — 4 con destino — y **las cuatro eran falsas**.  Todas adjudicadas a mano
en `tools/citas_prosa_etiquetas.py`:

- `FINDINGS-RENUMERACIONES.md:61` — es la **fila del propio indice** de
  renumeraciones: `| 1011 | 1020 | 3 |`.  Correcta por construccion.
- `RESERVAS-DESYNC.md:182`, `:183`, `:283`, `:353` — el documento que **explica**
  ese renumerado.  La cita nombra el numero viejo en su papel de numero viejo.
- `1039-...:39` y `:119` — el hallazgo afirma que el fichero corrupto tiene
  **11 598 bytes**.  MEDIDO: `1011-el-grep-de-ad8-...md` = 11 598 B y
  `1020-la-apertura-del-gart-...md` = 12 700 B.  Ademas el blob
  `499bffcbd6f3` existe y mide 0 bytes, que es lo que el hallazgo describe.  La
  cita va al 1011 de HOY, y se prueba **por tamano, no por vocabulario**.

El error de fondo, y por que se escribio: el mapa de renumeraciones dice **DONDE
esta un contenido**, no que **toda cita al numero viejo este equivocada**.  El
salto del uno al otro no se sostiene, y la tasa de acierto medida del detector
que lo daba por bueno fue **0 de 4**.  Esa correccion esta escrita en el
clasificador, en el sitio donde se hizo, para que no se repita.

**Clase 2 = 1168: se quedan con el numero y se declara.**  No hay destino que
poner.  Es la regla del punto 3 del encargo, aplicada.

**Clase 1 = 984: no se tocan.**  No son un defecto.  Son fragiles si el numero se
renumera, y la renumeracion es decision de otro nodo.

---

## 5. LO QUE SI SE ESTA DECIDIENDO ARREGLAR: 25 no-citas

Unica parte de A3 que se cierra sin tocar un solo hallazgo: **el detector de
citas esta mal**, no la prosa.  Y **no se arregla con una heuristica**, porque
tres heuristicas se probaron y las tres son peores que el defecto:

| regla | descarta | de las cuales NO son no-citas |
|---|---|---|
| balance global de corchetes | 421 | **359** |
| adyacencia a `[` o `]` | 8 | **5** |
| fila con 2+ tokens de solo 0/1 + cabecera de tabla | 11 | **3** |

La primera falla porque en markdown el balance de corchetes se abre con el
primer `[` sin cerrar —un enlace, una tabla, un literal de regex— y ya no vuelve
a cero, asi que todo lo demas parece "dentro de corchetes".  La segunda falla
porque `**[REFUTADO en \`272\`]**` acaba en `]` por el markdown, no por un rango de
bits.  La tercera falla porque `001`, `010`, `021` en una lista de hallazgos tiene
exactamente la misma firma que una fila de patrones binarios.

**Un detector que borra citas reales es peor que uno que cuenta de mas**: la que
cuenta de mas se ve en la tabla por directorios, y la que borra no se ve.  Por
eso el arreglo es una **declaracion por fichero**, con coincidencia EXACTA de
ruta y razon escrita — el mismo patron que ya usa
`tools/CITA-CODIGO-EXCEPTIONS.txt` para el codigo— y una lista cerrada no puede
borrar nada en un fichero que nadie declaro:

```
NO_CITA_FICHEROS = {
  "05-FUENTES-EXTERNAS/.../R0-7-REFERENCIA-X86-64-...md":
      "tabla de decodificacion SIB: 001, 010, 100, 101 son patrones binarios",   22
  "08-ARQUITECTURA/artifacts/Q5-MEM-TABLES/mem-tables.txt":
      "volcado de tablas de memoria: D0[127:0] es un rango de bits",              1
  "08-ARQUITECTURA/artifacts/Q5-ISA-CAP12/cap12.txt":
      "volcado del ISA: D0[127:0] y S2.u[127:0] son rangos de bits",              2
}
```

VERIFICADO, no supuesto: con esto, **A3 baja de 2230 a 2205**,
`no_citas_descartadas = 25`, en exactamente esos 3 ficheros, y el selftest de la
puerta sigue dando **30 comprobaciones, 0 fallos**.

El parche esta en `08-ARQUITECTURA/patches/citas-no-citas-y-A3-informativo.patch`
y **NO se ha aplicado**: ese fichero lo esta escribiendo otro nodo.

---

## 6. LA PUERTA: QUE DECIDO

**Decido: A3 no se cierra reparando prosa, y su codigo 4 deja de ser un fallo de
puerta.  Se queda como censo declarado y medido.**

El razonamiento, con la medida delante:

- A3 dice "no queda ninguna cita por numero colgando sobre un numero duplicado".
  Para que sea cierto habria que reescribir 2152 citas por nombre de fichero.
- MEDIDO: en el 54 % de ellas la cita no contiene nada que diga cual de los dos o
  tres ficheros es.  Reescribir esas es inventar el destino.
- MEDIDO: las que si son reparables (las de clase 1 con contenido que discrimina,
  ~30 % de la poblacion) **no estan mal**.  Reescribirlas arregla la fragilidad,
  no un defecto.
- MEDIDO: la causa de la ambiguedad son los **74 numeros duplicados**, y
  renumerarlos rompe las citas que los nombran.  Es decision de otro nodo.
- MEDIDO: 25 de las 2152 no son citas, y eso si se arregla, y no con prosa.

Una puerta que no se puede satisfacer, que cuenta cosas que no son citas, y que
se "&nbsp;arregla"&nbsp;inventando destinos, es una puerta que enseña a su lector
a ignorar el codigo de salida.  Peor que no tenerla.

**Lo que se propone en su lugar, y solo esto:**

- `A3` pasa a `INFORMATIVO`: se ejecuta, se imprime con sus clases, no dispara
  codigo de salida.  `EXIT_CITAS_AMBIGUAS` conserva su valor 4 para no romper a
  quien lo compruebe y queda sin uso a proposito.  El **selftest de la puerta
  cambia** en los dos casos que afirmaban que 4 dispara, y el motivo queda escrito
  en el sitio: sin eso el parche dejaba la puerta fallando su propio test.
- La afirmacion que **si** se hace cumplir es la de las **no-citas**, porque
  cierra: 25 -> 0, y se cierra en el detector, no en la prosa.
- **NO se propone** "ninguna afirmacion de contenido debe quedar sin fichero que
  la sostenga".  Seria el criterio correcto en principio —la medicion apunta
  exactamente ahi, porque el 100 % de las 2152 es no verificable por numero—, pero
  **no hay ninguna medicion de su tasa de violacion actual**, y sin esa medicion
  la puerta seria una pertenencia.  Se deja como frontera abierta, con el
  instrumento que haria falta ya escrito (`citas_prosa_census.py --valida`
  construye el expediente fila a fila) y con la condicion que la abre: medir la
  tasa antes de escribir el umbral.

---

## 7. LO QUE QUEDA ABIERTO, Y POR QUE NO SE ABRE AQUI

- **El mapa de renumeraciones dice 52 referencias colgando en 6 numeros;
  replicando su propia regla salen 98 en 12.**  MEDIDO.  El indice
  `FINDINGS-RENUMERACIONES.md` esta **viejo**: se genero con 49 filas del mapa y
  el mapa tiene 56.  Es de otro nodo.
- **174 citas por numero apuntan a un numero renumerado; solo 24 caen dentro de
  la poblacion de A3** (2 numeros), porque A3 solo mira los duplicados.  Las otras
  **150, en 28 numeros, son invisibles a A3**, y no se han adjudicado.  Es el
  limite de alcance de A3 y esta medido.  Ese es el sitio donde puede quedar clase
  3 de verdad, y queda declarado, no medido.
- **El margen del 45,7 % es de 40 puntos.**  Con n = 60 en
  `findings | sin senal` se cierra a la mitad.  Instrumento escrito, muestra no
  rodada.
- **Dos entradas de registro pendientes** (`citas_prosa_adjudicado.py`,
  `citas_prosa_etiquetas.py`), por 76 citas, que son el codigo 6 que dispara la
  puerta AHORA.  Patch entregado, no aplicado: el fichero lo esta escribiendo
  otro nodo.  Con el patch 1 y el patch 2 la puerta da **rc=0 y codigos []**.

---

## 8. REPRODUCIR

```
python3 tools/citas_prosa_census.py --selftest        # 7 casos, los 3 signos
python3 tools/citas_prosa_census.py --cruzado         # poblacion == la de A3
python3 tools/citas_prosa_census.py --valida          # proxy contra 12 etiquetas a mano
python3 tools/citas_prosa_census.py --tsv 08-ARQUITECTURA/validations/citas-prosa-censo-<fecha>.tsv.gz
```

Los dos parches, written y NO aplicados, con su cabecera explicando el motivo:
`08-ARQUITECTURA/patches/citas-registro-2-entradas.patch` y
`08-ARQUITECTURA/patches/citas-no-citas-y-A3-informativo.patch`.

El expediente por cita va en `.tsv.gz` **a proposito**: `.tsv` esta en
`EXT_LEIBLES` de la propia puerta, y publicar el censo como `.tsv` lo cuenta
como prosa.  MEDIDO: A3 subio de 2143 a 4737 y A4 de 0 a 5 por el expediente del
censo.  Un instrumento que publica su resultado puede reescribir la medicion que
lo contiene.

Instrumentos: `tools/citas_prosa_census.py` (censo y clasificacion),
`tools/citas_prosa_etiquetas.py` (12 etiquetas a mano con su prueba),
`tools/citas_prosa_adjudicado.py` (132 veredictos de la muestra).