# 944 — La causa de las colisiones de numeración: el mecanismo existe, es atómico, y 429 de 450 notas no lo usan

Estado: `PROVEN` la causa. Instrumento: `fronteras.py --reservas`, 17 de 17.
Alcance: `06-INGENIERIA-INVERSA/findings/`, 450 notas.
AUTORIA=AGENTE-SMU

## La cadena de lo que se encontró

`943` encontró que 70 números de nota están duplicados y propuso un lock por número. Fui a buscar
cómo se asignan los números antes de construir nada, y el mecanismo **ya existía**.


`943` encontró que 70 números de nota están duplicados y propuso un lock por número. Fui a buscar cómo
se asignan los números antes de construir nada, y el mecanismo **ya existía**:

```
findnum.py
  Lock        con mkdir, atomico
  reserve()   escribe un stub en _reservas/NNN-reservado.res dentro del lock
  release()   lo borra
  self_test() con su propia suite
```

Es exactamente el lock que `943` proponía, construido, probado y con self-test. **No hacía falta
construirlo.**

Y hay 20 reservas vigentes — 259, 272 a 291, 501 a 507. **El mecanismo se usó y dejó de usarse.**

## El número

```
reservas vigentes: 20
notas escritas SIN pasar por la reserva: 429 de 450
```

No es «yo no lo usé esta sesión». Son **429 notas consecutivas** sin reserva, que es prácticamente todo
el corpus reciente. La práctica terminó sola, sin que nadie lo decidiera.

## Por qué importa, y no es por las notas que ya están

Las notas existentes se pueden resolver leyendo el contexto —lo comprobé con una muestra de citas de
`108`, `100`, `258` y `130`, y en las cuatro el contexto desambigua sin dificultad—. El daño hecho es
ambigüedad, y la ambigüedad tiene salida.

El daño que **sigue creciendo** es el contrario: **429 notas pueden colisionar con la siguiente.** Y no
es teórico, porque en esta misma sesión pasó: al escribir `942` encontré que otra sesión había escrito
`941` un minuto antes.

## La lección, que es más útil que el número

Un mecanismo correcto que no está en el camino no previene nada.

`findnum.py` tiene lock atómico, reserva y self-test, y sus controles pasan. Todo lo que un mecanismo
de exclusión necesita está ahí. Y da igual, porque el número libre se calculaba con un script propio
en cada caso:

```python
python3 -c "
import os,re
ids={int(m.group(1)) for f in os.listdir('.') if (m:=re.match(r'^(\d{3,})-',f))}
print('libre:',[n for n in range(max(ids)+1,max(ids)+4) if n not in ids][:2])"
```

Funciona, da el número correcto, y **no reserva nada**. Es un lector de disponibilidad exercising de
propósito, y se nota poco porque devuelve la respuesta que se le pide.

Es el mismo patrón que el resto de la sesión, con distinta ropa: la bandera `--tex` detrás de un
`continue` (código muerto que parecía vivo), el `binding 0` escrito solo en el `else`, la marca de GPU
leída de la calibración. **Una cosa presente que no hace su trabajo porque está en el sitio
equivocado, o porque nadie la invoca.**

## El arreglo

Añadido: `fronteras.py --reservas` informa de las notas sin reserva y **devuelve 1**. Es el mismo
tratamiento que recibió el binario de `bench.py` en `930`: si un artefacto tiene un productor
declarado, el consumidor comprueba que pasó por él.

Eso convierte una práctica en un estado verificable. No obliga a nada por sí solo —un preflight que
nadie ejecuta tampoco previene— pero hace que ejecutar el preflight tenga información que antes no
tenía.

Lo que falta para cerrarlo del todo: que `fronteras.py` lo ejecute él mismo, igual que ejecuta su
propio self-test, y que se niegue a resolver fronteras si hay reservas sin consumir. Con eso, el
camino por defecto pasa por la reserva.

## Un fallo latente que se vio de paso

`findnum.py` usa `%03d` para el stub, que es un ancho **mínimo** y por tanto no falla al llegar a 1000.
Pero `used_numbers()` compara con `^(\d{3})-`, que es un ancho **exacto**: a partir de la nota 1000 la
herramienta dejaría de ver las notas existentes y entregaría números ya usados.

Hoy no hay ninguna nota de cuatro dígitos, así que no está causando daño. Es la clase de fallo que no
aparece hasta que aparece, y se ve ahora que hay 450 notas y ninguna más de tres dígitos. **No
arreglado**, anotado.

## Instrumentos

`08-ARQUITECTURA/tools/fronteras.py`, 17 de 17, tres modos: `--citas` y `--reservas` devuelven 1 cuando
hay un defecto, como un preflight.

## Lo que queda abierto

- **Cerrar el camino**, para que la reserva sea el modo por defecto y no una intercepta
  opcional. Es el arreglo de la causa y no está hecho.
- **El fallo latente de `^(\d{3})-`** en `findnum.py`, antes de la nota 1000.
- **`271-1` en `REOPENED` desde la nota 276**, el frente abierto más antiguo y el único reabierto a
  propósito sin constancia de cierre. No mirado en esta vuelta.
- **Las 167 notas con número colisionado.** No se renumeran: rompería 3840 citas entrantes.
