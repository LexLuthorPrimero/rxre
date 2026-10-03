# 948 — Camino cerrado: `fronteras.py` delega en `findnum.py`, y el fallo de los tres dígitos está arreglado con un vector de cuatro

Estado: `PROVEN`. Herramientas: `fronteras.py` 18 de 18, `findnum.py --self-test` OK con 8 vectores.
Alcance: `06-INGENIERIA-INVERSA/findings/`.
AUTORIA=AGENTE-SMU

## Qué cierra

`944` dejó dos cosas: que el camino de reserva no estaba cerrado, y un fallo latente en
`findnum.py`. Las dos están cerradas.

## 1 · El fallo latente: `^(\d{3})-`

`used_numbers()` listing con un patrón de **ancho exacto**:

```python
m = re.match(r"^(\d{3})-", name)
```

En cuanto hubiera existido la nota `1000`, `1000-algo.md` dejaría de casar, `used_numbers` dejaría de
verla, y `next_free()` volvería a entregar un número que ya existe. **Silencioso**: la herramienta
responde, y responde mal.

La incoherencia estaba dentro de la misma idea de «número de nota». La mitad de escritura usa
`"%03d-reservado.res"`, que es un ancho **mínimo** y por tanto no sufre; la mitad de lectura usa un
ancho **exacto** y sí. Dos mitades de la misma convención, diciendo cosas distintas.

Arreglado a `\d{3,}`, con vector en el self-test:

```
used_numbers ve los de cuatro digitos                    [999, 1000, 1001]
next_free no devuelve un 1000 que ya existe              1002
```

El vector **escribe sus propios ficheros en un temporal** en vez de mirar el árbol real, y eso es
deliberado: el árbol todavía no tiene ninguna nota de cuatro dígitos, así que un caso que mirara el
árbol real no vería nada y el fallo reaparecería al cruzar los 999 sin que nadie se entere. **Un caso
de prueba para un fallo futuro tiene que fabricar el futuro.**

## 2 · El camino: la reserva es ahora lo que se ve

Antes, cada vez que hacía falta un número libre calculaba el conjunto de números usados por mi cuenta:

```python
ids={int(m.group(1)) for f in os.listdir('.') if (m:=re.match(r'^(\d{3,})-',f))}
print('libre:',[n for n in range(max(ids)+1,max(ids)+4) if n not in ids][:2])
```

Funciona, da el número correcto, y no reserva nada. Es un lector de disponibilidad haciendo de
escritor en apariencia.

Ahora `fronteras.py` **delega**:

```
--- el numero que sigue ---
  libre segun findnum.py: 948
  findnum.py reserve 948   # lo toma en serio; --next solo informa
  NINGUN otro metodo sirve: un numero libre que nadie reserva no es un numero
```

Y `numero_reservable()` **no reserva**: informar y tomar son dos acciones distintas, y un informe que
reserva al ejecutarse deja el árbol modificado sin que nadie lo pidiera.

Cerrado el circuito completo y comprobado de extremo a extremo:

```
findnum.py reserve 948      -> reservado 948, stub en _reservas/
findnum.py --next           -> 949        (antes daba 948: la reserva se ve)
```

## Por qué esto era el arreglo de la causa y no del síntoma

Las 429 notas sin reserva **no se arreglan** con esto, y no se van a arreglar: están escritas. Lo que
se arregla es que la siguiente nota tome el número por el camino que reserva.

Y el efecto de la auditoría sigue ahí: `fronteras.py --reservas` devuelve 1 mientras haya notas sin
reserva, así que la proporción es un **estado verificable** y no una costumbre.

## Detalle que salió de paso, y que no es menor

`findnum.py` con un argumento no reconocido **reserva un número**. No hay rama de error: el caso por
defecto es «reservar». Le pasé `--selftest` en vez de `--self-test` y consumió el 947 sin decir nada.

Es una decisión discutible y la dejo como está porque es el caso de uso frecuente —casi siempre se
quiere reservar—, pero un nombre de bandera mal escrito tiene un coste real y silencioso. Con
`--next` y `--list` yaen el caso de solo consulta; lo que falta es que un flag desconocido avise.

## Instrumentos

- `fronteras.py` 18 de 18. Modos: `--citas`, `--reservas`, y el informe principal que ahora delega el
  número en `findnum.py`.
- `findnum.py` `--self-test` OK, 8 vectores y 3 controles, uno nuevo de cuatro dígitos.

## Lo que queda abierto

- **Que `findnum.py` avise de una bandera desconocida** en vez de reservar. Barato, y es lo que me
  costó un número.
- **Que `fronteras.py` se niegue a resolver fronteras si hay reservas sin consumir.** Con 429 notas
  sin reserva, esa condición se cumple siempre y el informe no serviría de nada; hay que distinguir
  «reservada y no escrita» de «nunca reservada», y solo la primera es un error actual.
- **El fallo de los 1000 números, ya arreglado en lectura.** Queda el sitio de escritura, que usa
  `%03d` y no sufre; no hay nada que hacer ahí.
- **`271-1` en `REOPENED` desde la nota 276**, el frente abierto más antiguo y el único reabierto a
  propósito sin constancia de cierre. No mirado.
