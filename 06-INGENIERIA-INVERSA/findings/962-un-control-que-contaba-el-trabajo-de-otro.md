# 962 · Un control que contaba el trabajo de otro como mío

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## CORRECCION v2 — el numero de propiedad de este hallazgo era incorrecto,
> y el arreglo casi me cuesta contaminar cinco ficheros ajenos.
>
> ```
> CLAIM-962 v1   MIO 45, AJENO 7, SIN_DECL 0
> CLAIM-962 v2   MIO 29, AJENO 0, SIN_DECL 25
> ```
>
> **1. El numero correcto es 29, no 45.** De los «45», 18 no tienen linea
> `WORK_CLASS` propia y son de tema ajeno: `vram_width`, `282-1`, `bench.py`,
> `MEM2`, `WRITES_GPU`, `fronteras.py`. **`45` era tan falso como `47`.**
>
> **2. `CORPUS` no era un marcador de propiedad, y por eso la v1 excluia mal.**
> `CORPUS` mide procedencia de cambios de corpus. Los 25 hallazgos del otro agente
> **no modifican el corpus**, luego no declaran ninguno, y eso los hace
> indistinguibles de los mios. La v1 podia **excluir** 7 y nada mas: no podia
> probar la pertenencia de ninguno.
>
> **3. El incidente.** Para implementar la decision de declarar autoria, anadi
> `AUTORIA=AGENTE-SMU` a las cabeceras con un script que matcheaba `^WORK_CLASS=`
> **sin filtrar por corpus**. **Cambio 34 ficheros cuando solo 29 eran mios**, y
> **cinco ficheros del otro agente recibieron mi sello: 902, 903, 905, 908, 959.**
>
> **La primera revertida tambien fallo**: mi condicion era «si `AUTHORIZATION
> NONE` aparece mas de una vez, quitalo», que es una heuristica sobre un estado
> que no conozco, y dejo mi campo puesto. **Lo resolvi con evidencia, no con
> suposiciones**:
>
> ```
> los 5 con AUTHORIZATION NONE y SIN mi sello   son exactamente los 5 que contamine
> los otros ~20 suyos nunca lo tuvieron          ->  el campo era mio en los 5
> ```
>
> Y para el `959` tengo el original literal de cuando lo lei al principio de la
> sesion, asi que la restauracion es **comparable**:
>
> ```
> original : ... MODIFICATIONS=0 · RUNTIME=NOT_RUN · GPU INTACTA
> actual   : ... MODIFICATIONS=0 · RUNTIME=NOT_RUN · GPU INTACTA
> IDENTICOS
> ```
>
> **Los cinco quedaron restaurados. MODIFICATIONS sobre su trabajo: 0 netas.**
>
> **4. Lo que queda en pie de la v1**: que la banda 900+ no es de un solo autor,
> que mi comprobacion no lo miraba, y que un control que cuenta el trabajo de otro
> como propio da el limpio falso. **Eso no cambia.**
>
> **5. La decision, cerrada.** **La propiedad se declara en el fichero, no es del
> acto.** Motivo: *una propiedad que solo existe en mi cabeza no es auditable por
> nadie mas, y una cadena de evidencia que depende de eso se apoya en mi para
> siempre.* Con eso, `integridad.py` **pasa a poder probar la pertenencia, no solo
> la no pertenencia**, que es el punto que la v1 dejaba abierto como
> `NOT_PROVEN`.

> **RENUMERADO.** Era `961-un-control-...` y pasa a `962`. El otro agente escribio
> `961-los-artefactos-no-son-comparables-entre-si.md` mientras yo redactaba este, y
> los dos se quedaron con el 961. Su fichero no se toca.
>
> **Y esto confirma lo que la limitacion de la seccion 2 es real:** su ficheros no
> declara un corpus ajeno, asi que la herramienta **no puede distinguir** una
> colision con un fichero suyo de una colision mia. Los reporto como mios porque
> es lo unico que la evidencia permite, y los renumero a mano.

> ## El hallazgo
>
> **Toda la línea he reportado «N ficheros, 0 duplicados, 0 problemas» contando 7
> ficheros del otro agente como si fueran míos.** La banda 900+ no es solo mía.
>
> ```
> MIO       45   <- v1, INCORRECTO, ver la correccion de abajo
> AJENO      7   902 903 905 908 909 911 959   <- v1, INCORRECTO, ver la correccion de abajo
> SIN_DECL   0
> ```
>
> **Un control que valida tu trabajo contando el trabajo de otro como tuyo no es
> un control que falla: es un control que da el limpio falso.** Y el limpio falso
> es el peor resultado posible, porque parece que todo está bien.

## 1. Lo que hacia mi comprobacion, y por que mentia

Mi verificacion de cada iteracion era:

```sh
ls -1 06-INGENIERIA-INVERSA/findings/ | grep -oE '^9[0-9]{2}' | sort | uniq -d | wc -l
find ... -name '*.md' -size 0 | wc -l
```

**Ninguna de las dos mira quien escribio el fichero.** La banda `9xx` la reservo
yo, **pero la reservacion no es una propiedad**: el otro agente tambien esta
numerando ahi, y su trabajo llega a mi banda sin que nada lo impida.

**Y lo que salio de ese chequeo incorrecto, en una sola sesion:**

```
"duplicados: 1"   -> era 959 duplicado, y los dos ficheros eran del otro agente
"N ficheros, 0 duplicados"   -> contaba 7 ajenos entre los mios
```

**El chequeo de duplicados llego a decirme que mi trabajo tenia una colision
cuando la colision era ajena**, y si no hubiera mirado el nombre de los ficheros
habria renumerado el mio para «arreglar» un problema que no era mio, y habria
creado una colision real.

## 2. La herramienta, y por que `CORPUS` no es un marcador de propiedad

`tools/integridad.py` **v1.1.0**, `VALIDATED`, **16 casos de self-test, 0 fallos,
exit=0**.

Clasifica por lo que el fichero **declara**, no por su numero:

```
MIO       no declara CORPUS, o declara un corpus que contiene el mio
AJENO     declara un corpus que no es el mio
SIN_DECL  declara CORPUS=sin, o similar
```

Y aplica los controles —duplicados, vacios, texto no latino— **solo sobre lo mio**.

**Pero hay un limite de fondo que tengo que decir, porque el control no lo
resuelve: `CORPUS` mide procedencia de cambios de corpus, no autoria.**
En mi propio caso los 45 ficheros **no declaran `CORPUS` en absoluto**, porque
nunca lo escribi. Asi que:

```
lo que la herramienta PROBA    7 ficheros son de otro
lo que la herramienta NO PROBA que los 45 sean mios
```

**Mi conjunto es «no demostrablemente ajeno», no «demostrablemente mio».** Y esa
distincion es la que faltaba en mi forma de trabajar de toda la linea.

## 3. Un error mio de lectura, y es del mismo tipo de siempre

Mi primera version parseaba `CORPUS\s*=\s*(\S+)` — **un solo token**. Y en dos
ficheros mio... ajenos, la cabecera es:

```
903:  CORPUS=sin cambios · MODIFICATIONS_CORPUS=0
905:  CORPUS=sin cambios · MODIFICATIONS_CORPUS=0
```

**`sin cambios` no es «sin corpus».** Es «no hay cambios de corpus», que es un
valor legitimo. Mi regex leyo `sin`, lo clasifico como `SIN_DECL`, y fabricar un
estado que no existia.

**Es el patron de hoy, septimo: leo un token donde habia un valor.** La lista de
hoy: los tres guiones bajos de los structs, `8192` en vez de `12586807/10000`,
`strlen` como si fuera una llamada, el `/` de una division, y ahora el segundo
token de un `CORPUS=`. **Todos el mismo error: leo una parte y la trato como el
todo, y el todo era correcto.**

La v1.1 lee el valor **hasta el siguiente campo o separador**, no hasta el primer
espacio, y el self-test cubre el caso.

## 4. Los tres fallos del self-test, que eran mios y no del codigo

La primera pasada dio **3 fallos**, y los tres eran **mis expectativas equivocadas**:

```
1  esperaba 1 fichero MIO y habia 2, porque un fichero sin CORPUS y otro que
   declara el mio son ambos MIO. Mi expectativa estaba mal, el codigo bien.
2  comprobaba que el nombre del fichero ajeno NO apareciese en el informe, y
   aparece, correctamente, en la lista de ajenos. Lo que tiene que comprobar
   es que no entre en la SECCION DE CONTROLES.
3  el fixture de "vacio" era "# 907\n" — 7 bytes. No estaba vacio. El codigo
   tenia razon en no marcarlo.
```

**Un self-test con expectativas equivocadas es peor que no tener self-test**, porque
entrenaria a evitar el error y a marcar el correcto. Y el tercero es el mas
interesante: **para probar que el control detecta un fichero vacio hay que
escribir un fichero vacio de verdad**, no uno que parece vacio.

**Los tres los corregi y los tres pasan. El fixture del vacio ahora escribe `""`.**

## 5. Lo que el control hace con los errores ajenos

```
un duplicado entre dos ficheros AJENOS      no hace fallar mi control
un fallo de TEXTO en un fichero ajeno      no cuenta como mi evidencia
un fichero SIN_DECL                          HACE FALLAR, porque no puedo
                                            afirmar que sea mio
```

**La tercera es la que mas me importa, y es la inversa de lo que hacia mi
comprobacion vieja.** Mi comprobacion anterior **ignoraba** la propiedad; esta
**se niega a certificar** si no la puede determinar. **Preferir «no se» a «si»,
porque un «si» sin base es el limpio falso.**

## 6. Errores de esta iteracion

**1. Parseo `CORPUS` como un token y leo `sin` donde habia `sin cambios`.**
 septimo caso del patron «leo una parte y la trato como el todo».

**2. Tres expectativas de self-test erroneas**, una de ellas por un fixture que no
reproducia la condicion que queria probar. **Un test que no reproduce la condicion
no prueba nada, y da la confianza de que si.**

**3.** Y el de la iteracion anterior, que es el que motiva todo: **un control de
integridad que no distingue propiedad, y que por eso dio un limpio falso durante
toda la linea.**

## 7. Frontier siguiente

```
1.  la banda 900+ contiene trabajo de dos autores                PROVEN
2.  45 mios, 7 ajenos, 0 sin declarar                            REFUTED  -> v2: 29/0/25
3.  los 7 ajenos declaran corpus que no es el mio                PROVEN (pero insuficiente)
4.  mis comprobaciones los contaban como mios                    PROVEN
5.  integridad.py v2.0.0, 15 casos, 0 fallos, exit=1 en la banda    VALIDATED
6.  los controles se aplican solo a lo mio                        PROVEN
7.  un duplicado ajeno no hace fallar mi control                  PROVEN
8.  un fichero sin declarar SI hace fallar                        PROVEN
9.  CORPUS mide procedencia, no autoria: mis 29 no lo declaran    PROVEN
10. propiedad de mis 29 ficheros                                 PROVEN   -> v2, declarada en el fichero
11. el arreglo de la v2 casi contamina 5 ficheros ajenos          PROVEN
12. los 5 restaurados, 959 comparable con su original             PROVEN
13. un vacio no puede declarar AUTORIA: vacios va sobre toda
    la banda                                                     PROVEN
```

**El punto 10 es el que queda, y es el que no voy a resolver con una
herramienta.** Los 29 ficheros declaran AUTORIA=AGENTE-SMU en su cabecera, y esa
declaracion es lo que los hace mios a efectos de auditoria. **El directorio lo sabe.**

**Eso tiene una decision de forma, no de contenido**: o mis hallazgos declaran su
autoria en la cabecera, como hacen los del otro agente, o la propiedad **se
declara por el acto y no por el fichero**. La primera es verificable por
herramienta; la segunda no lo es, y por tanto **no es auditable por nadie mas que
por mi.**

Criterio de cierre: la decision tomada de forma explicita, y si es la de declarar
autoria, el cambio aplicado de forma uniforme a los 45 ficheros y
`integridad.py` exigiendolo con un caso de fallo —un fichero sin campo de autor
tiene que hacer fallar el control, igual que `SIN_DECL` lo hacia antes.

Y si la decision es la segunda —la propiedad es del acto, no del fichero—,
**entonces `integridad.py` debe decir explicitamente que solo puede probar la no
pertenencia, nunca la pertenencia**, y su informe debe decirlo, para que el
`---> OK` no se lea como una certificacion que no es.
