# 1048 — el fallo que se repite: un filtro que excluye por construcción a la población que dice medir

```
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN-AUDITORIA
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ORIGEN=cuatro mediciones independientes que solo juntas muestran el patron
ESTADO=PROBADO (cuatro instancias) · la cuarta la esteemed este hallazgo
```

## El patrón

No son cuatro defectos. Es **uno**, y aparece en sitios que no se parecen entre si:
una puerta de citas, una herramienta de reparacion, un generador de indice y un
contador de notas. En los cuatro, un filtro decide que se mira, y el filtro deja
fuera justo lo que habia que mirar. **Y en los cuatro, la herramienta no falla: sale
con un numero, y el numero parece bueno.**

Lo grave no es que se pierda cobertura. Es que **se pierde en silencio y el
resultado sigue pareciendo una medicion**.

## Las cuatro instancias

### 1. `check_num_unico.py:635` — las 225 citas que la puerta no puede ver

```python
if num not in dups:
    continue
```

Solo cuenta citas cuyo numero este en `dups`, el conjunto de **numeros duplicados**.
MEDIDO por el nodo `CITAS-150`: de 255 citas que apuntan a numeros renumerados, **30
son visibles y 225 son invisibles por construccion**. Y los cuatro numeros con C3
confirmado —103, 104, 144, 188— **son unicos hoy**, o sea que la puerta
estructuralmente no puede verlos.

### 2. `refs_repair.py` — repara dentro de `findings/` y los C3 estan fuera

MEDIDO hoy, con las dos herramientas y en modo `--ambito todos`:

```
$ python3 08-ARQUITECTURA/tools/refs_repair.py
nada que reparar (ambito=mios)

$ python3 08-ARQUITECTURA/tools/refs_repair.py --ambito todos
VISTA PREVIA (no se escribe)
   ... 12 referencias a reparar, todas `1011`->`1020` y `286`->`401`
```

Los 6 C3 confirmados **no aparecen en ninguno de los dos modos**. La razon es
estructural: `_candidatos()` recorre los ficheros del mapa de renumerado, que son
todos de `06-INGENIERIA-INVERSA/findings/`. Los 6 C3 viven en
`NEGATIVE-RESULTS.md` y en `docs/AGENTS-RECTOR-2026-10-02.md`. **La herramienta no
falla: mira donde siempre ha mirado.**

Y hay un detalle que hace esto mas instructivo todavia: la herramienta **si** tiene
un `--ambito todos`, y su self-test comprueba explicitamente que el ambito por defecto
**no** sea `todos` (`corpus: el ambito no es 'todos'`). Es decir: **el diseño
deliberado de esa herramienta es no reescribir la prosa de otra sesion.** Con lo cual
los 6 C3 no son un fallo de `refs_repair.py`. Son la consecuencia correcta de una regla
correcta, y estan en prosa que **no es mia**.

### 3. `\d{3}` donde hacia falta `\d{3,4}` — 25 hallazgos invisibles

`artifacts.py` y `dupenum.py` contaban numeros de hallazgo con un ancho exacto de tres
digitos. Hay hallazgos de cuatro. **MEDIDO: 25 de ellos no existian para el recuento.**

El `.gitignore` del propio arbol ya registra el mismo criterio aplicado bien —«una
casa y la otra no»— aplicado a las banderas, y el self-test de `check_num_unico.py`
tiene un vector que demuestra que el patron estrecho **no** encuentra la colision de
cuatro digitos. El patron estaba documentado como trampa y se cayo en ella.

### 4. `cn8.py` — ciego a dos entradas con el mismo `## TL-nn`

`cn8.py` es ciego al caso B: dos entradas con el mismo encabezado `## TL-nn` y cuerpo
distinto. Es un filtro que compara el encabezado y no el **numero de entrada**, que es
la clave primaria. Clasificado `PARTIAL`, no reparado.

## Por que esto es el hallazgo y no una lista

Las cuatro herramientas son de dominios distintos: citas, reparacion, indice, notas.
Lo unico que comparten es que **producen un entero y ese entero se publica**.

Y hay un quinto caso que ya no es un filtro sino una **clave equivocada**, y que
merece estar en la lista porque se confunde con los otros: `toalaudit.py`
deduplicaba por `os.path.realpath`, que bajo los 6 `mount --bind` del arbol da dos
cadenas distintas para el mismo inodo (hallazgo 1047). Ahi el filtro **no excluye a
nadie**: incluye al mismo fichero dos veces. Es el defecto espejo, y comparte la raiz:
**la herramienta no sabe que identidad tiene aquello que cuenta.**

## La regla que sale, y que es aplicable

> **Antes de publicar un recuento de una herramienta que filtra, hay que publicar
> tambien que excluye el filtro.**

No como promesa, sino como salida. Concretamente, para cada herramienta que cuente con
un filtro, tres numeros y no uno:

```
CONTADO      lo que el filtro deja pasar
EXCLUIDO     lo que el filtro descarta, por clase y por cantidad
JUSTIFICADO  por que se descarta eso
```

El segundo numero es el que no existe hoy en ninguna de las cuatro. Y sin el, el
primero no es interpretable: **2152 y 2222 son incomparables si no se sabe que hay
entre medias.**

Y hay un cuarto numero, mas barato que los otros tres y el que mas veces habria
atado esto:

```
CONTROL  un caso que el filtro DEJA FUERA y que yo se que deberia entrar
```

Es lo que hacen los self-tests de este arbol cuando estan bien hechos —«y con
`\d{3}` NO la veria (control negativo del patron)», «y con el censo real NO
dispara»—, y es exactamente lo que falto en las cuatro instancias. **Un filtro sin un
caso que se le escape es un filtro que nadie ha probado.**

## Lo que esto NO es

No es una critica a las cuatro herramientas: las tres primeras **funcionan** dentro de
su ambito y su autodocumentacion es buena. No es un defecto de criterio de quien las
escribio: es un defecto de lo que la puerta *comprueba*, que es el recuento, y no de
lo que la puerta *dice medir*, que es la poblacion.

Y no he cambiado ninguna de las cuatro. El arreglo de la instancia 1 tiene un
obstaculo de fondo que no aparece en la instancia 2: el exit 7 **no es enumerable**,
porque su poblacion y la de las 225 son disjuntas por construccion. Lo que hay que
decidir es si la puerta cambia de poblacion o si **dice que no puede** seguir el
rastro de una clase de citas a la que no llega. Ambas son defendibles. Ninguna es
gratuita.