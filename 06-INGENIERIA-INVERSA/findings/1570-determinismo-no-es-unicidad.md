# 1570 · Determinismo no es unicidad: `result_id` sobre valor normalizado no identifica

```
CLASSIFICATION=ERROR · TRACK=STATIC
HARDWARE_SCOPE=NINGUNO · WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS=0
GPU INTACTA
CIERRA=la regla F6 para el caso que F6 no habia medido
ABRE=la misma confusion en otros campos derivados del valor
```

## El caso medido

Dos copias **byte-idénticas** de `rxre_min.elf` en rutas distintas:

```text
valor normalizado  A == B          True
input_hash         A == B          True   (son el mismo contenido)
result_id          A = res_…_49f1f83a2e58
result_id          B = res_…_e2839fc46823
¿colisionan?                        False
```

El `result_id` correcto **incorpora la ubicación**, así que distingue. Con un
id derivado **sólo del valor**, los dos colapsarían en un único identificador.

## Por qué son dos cosas distintas

| propiedad | definición | la rompe |
|---|---|---|
| **determinismo** | la misma entrada → el mismo id | cambiar el valor |
| **unicidad** | entradas distintas → ids distintos | derivar de un valor no injectivo |

Un vector que sólo comprueba determinismo pasa con las dos implementaciones:
inspeccionar dos veces el mismo fichero da el mismo valor y el mismo id
con cualquiera de ellas. Por eso la mutación `result_id ← hash(str(valor))`
**sobrevivió** a los vectores de B0.

> determinismo no es unicidad

## Los dos vectores ciegos (y por qué lo eran)

**B0.** El vector comparaba el id contra `json.dumps(valor)`, pero el mutador
usaba `str(valor)`: bytes distintos, hash distinto, vector ciego.

**B2.** Corregido a `str(valor)`, el vector seguía pasando por la razón
equivocada: el id real es `hash("raw_binary|artefacto|backend|json(v)")`, que
tampoco termina en `hash(json(v))`. Un id derivado **sólo** del valor tampoco.

```
un vector que pasa por la razón equivocada no mide nada
un vector tiene que derivar el id con la misma fórmula que el mutador
```

El vector que **sí** discrimina es de comportamiento: dos artefactos con el
**mismo** valor normalizado deben dar ids **distintos**. Sin la precondición
(`valores iguales`), la unicidad no probaría nada — y la precondición se
comprueba explícitamente en el test.

## El corolario sobre `COLISION`

`result_id` es determinista, así que pedir dos veces la misma inspección da
siempre `COLISION`. Eso **no es un fallo**: es que la evidencia ya existe y
`explain` la alcanza.

```
una colisión de un id determinista es la garantía funcionando
```

Reportarlo como `persistido: false` diría "no se guardó" cuando **sí** está
guardada. Se distingue explícitamente en el envelope.

## Provenance

```text
artefacto   tools/rxre/fixtures/bin/rxre_min.elf  sha256 a183f60d…
adaptador   backends/adapters/rz_inspect.py  _id_resultado()  (4 componentes)
mutacion    "el result_id se deriva solo del valor"   DETECTADA en B2
vector      test_backends004.py  seccion 7 + B2-C
limitacion  no se prueba la no-colision contra un producer real que produzca
            dos valores identicos; se prueba contra dos artefactos iguales
```