# 936 - La capacidad `WRITES_GPU` significa dos cosas y `bench.py` cae en las dos: se desambigua el contrato

Estado: `CONTRADICTION` resuelta por desambiguación, no por elección.
Alcance: los instrumentos propios de `08-ARQUITECTURA/tools/`.
AUTORIA=AGENTE-SMU

## La contradicción

Dos instrumentos míos, sobre el mismo banco, dicen cosas incompatibles:

**`932`** busca acceso MMIO en `bench.py` —`/dev/mem`, `__iomem`, `outl`— y no lo encuentra, y concluye
que la declaración `WRITES_GPU=yes` es **falsa**. El criterio de terminación que se puso era explícito:
«buscar acceso MMIO. Cumplido».

**`bench.py`** declara `WRITES_GPU=yes`, y todos los demás instrumentos del árbol declaran
`WRITES_GPU=no`, incluido `toolaudit.py`, que es quien define el vocabulario.

Ninguno de los dos miente bajo su propia lectura. El problema es que **`WRITES_GPU` no tiene una
sola definición**, y `932` eligió una sin declararlo.

## Lo que el banco hace de verdad

| hecho | cómo se sabe |
|---|---|
| no toca ningún registro MMIO | 0 apariciones de `mmio`, `/dev/mem`, `__iomem`, `outl`, `inl` en los `.c` del árbol |
| envía trabajo que hace escribir a la GPU | `vkQueueSubmit`, y los shaders escriben en `d[WSIZE + i]` y el host lo ve al releer |
| crea un `VkDevice` y reserva memoria del dispositivo | `vkCreateDevice`, `vkAllocateMemory` |

Bajo la lectura «escribe registros MMIO», `bench.py` debería declarar `no`. Bajo la lectura «hace que
la GPU escriba», debe declarar `yes`. Las dos son defendibles y por eso el nombre no sirve.

## Un agravante que nadie había leído

El contrato original era:

```
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_GPU=yes
```

Eso es una **contradicción en la cara del contrato**: de sólo lectura no puede escribir en la GPU. Y
la contradicción es exactamente lo que induce la lectura equivocada: si se lee `READONLY=yes`, la
línea siguiente tiene que ser un error, y entonces el veredicto de `932`, «la declaracion es falsa»,
parece la corrección natural de un error tipográfico.

No era un error tipográfico. Era un nombre que significa dos cosas, más una bandera que se
contradecía a sí misma.

## La resolución

No se elige una lectura. Se declara **cada hecho por separado**, a la granularidad en que no hay
ambigüedad:

```
# CONTRACT: READONLY=no
# CONTRACT: WRITES_GPU=yes
# CONTRACT: WRITES_GPU_MMIO=no
# CONTRACT: WRITES_GPU_WORK=yes
```

`toolkit.py` lee el contrato con `re.match(r"#\s*CONTRACT:\s*(\w+)\s*=\s*(\S+)")`, que acepta claves
arbitrarias, así que las dos nuevas se leen sin tocar el parser. Comprobado:

```
name = bench    READONLY = no    WRITES_GPU = yes
WRITES_GPU_MMIO = no              WRITES_GPU_WORK = yes
```

Y `READONLY` pasa a `no`, porque el banco crea un dispositivo, reserva memoria y envía trabajo. Era
falso antes.

Esto no reescribe `932`, que hizo bien su trabajo con el criterio que se dio. Lo que cambia es que su
conclusión pasa de «la declaración es falsa» a «la declaración era ambigua», y eso lo deja dicho el
propio `bench.py` en el comentario que acompaña al contrato.

## Lo que esto cuesta y por qué merece la pena

Una capacidad que se presta a dos lecturas opuestas **no es una capacidad**: es un adorno. Y en un
árbol donde las decisiones se toman leyendo el contrato de cada herramienta antes de ejecutarla, un
contrato que se contradice no falla donde falla: funciona, y su fallo aparece más tarde, en el
número que alguien publica.

La comprobación cuesta una línea: `grep -c WRITES_GPU bench.py` y `grep -cE 'mmio|/dev/mem' *.c`.

## Instrumentos

- `bench.py`: contrato desambiguado, 15 de 15.
- No se tocó `toolaudit.py` ni su vocabulario: la corrección es del contrato que estaba mal escrito,
  no del que lo leía.

## Lo que queda abierto

- **`READONLY=yes` en herramientas que sí envían trabajo.** Si hay más declarando `READONLY=yes` con
  capacidad de envío, el mismo problema está en todas ellas y aquí solo se ha mirado una. No se ha
  buscado: es una búsqueda de un minuto y no está hecha.
- **`WRITES_SYSFS`, `WRITES_FILES`, `MUTATES_CORPUS`**: el mismo tratamiento de una clave por
  capacidad, por si alguna tiene dos lecturas. Tampoco buscado.
