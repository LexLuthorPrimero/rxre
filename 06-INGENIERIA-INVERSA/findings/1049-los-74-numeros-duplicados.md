# 1049 — los 74 números duplicados: lo que bloquean, lo que no, y tres premisas mias, medidas antes de comprobar

```
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN-INTEGRIDAD
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=06-INGENIERIA-INVERSA/findings/  (551 ficheros, 450 numeros)
         08-ARQUITECTURA/tools/findings_index.py
ESTADO=PROBADO (la duplicacion y su alcance) · NO REPARADO · premisas falsas REGISTRADAS
```

## El hecho, medido

```
hallazgos publicados   551 ficheros
numeros distintos      450
numeros con >1 fichero  74        (47 con 2 ficheros, 27 con 3)
ficheros implicados    175
rango de las colisiones  1 .. 1011   (48 por debajo de 100, 26 por encima)
numeros libres por debajo de 1248:  797
```

Y las colisiones son de contenido genuinamente distinto, no copias:

```
  1:  001-amdgpu-location.md   /  001-amdgpu-overview.md
 33:  033-mmu-vm-no-publicado.md
      033-pm4-spec-gfx8-no-existe-y-el-encuadre.md
      033-protections-opaco-en-el-camino-gpuvm.md
```

**Los 74 tienen al menos una cita.** Recuento mío sobre `git ls-files` menos
`findings/`, forma `` `NNN` ``: **2588 citas** que nombran un número duplicado. El
censo de la puerta dice **2222**. Dos mediciones independientes de la misma magnitud,
con denominadores distintos. **Se registran las dos y no se promedian**: la diferencia
de 366 citas es en sí misma un dato sin explicar.

## Lo que bloquean, citado

`08-ARQUITECTURA/tools/findings_index.py:913-919`:

```python
if col:
    print("DEFECTO DE INTEGRIDAD: el numero de hallazgo no es clave unica.")
    print("Por eso CORRECTED_BY=NNN y el calculo de sentido de")
    print("CONTRADICTIONS.md no se pueden resolver de forma fiable.")
else:
    print("OK: clave unica.")
return 1 if col else 0
```

Y en su cabecera, lineas 23-24:

> «x, y el calculo de
> sentido de CONTRADICTIONS.md resuelve de forma arbitraria cuando hay dos destinos»

**Eso es lo único que rompen.** Dos cosas concretas, y no son el índice: la
desambiguación de `CORRECTED_BY=NNN`, y el sentido de las flechas en `CONTRADICTIONS.md`.

## Lo que NO bloquean, y aquí es donde me equivoqué tres veces

**Estaba mal decir que esto impedía regenerar un índice.** No lo hace. Y la razón de que
lo creyera es que no miré qué hacen los ficheros que compare:

| lo que yo creía | lo que es, leído |
|---|---|
| `FINDINGS-RENUMERACIONES.md` es el índice de hallazgos | tiene dos secciones: `## Numeros con colision` (línea 73) y `## Renumeraciones` (línea 152). **No lista hallazgos** |
| `findings_index.py` genera ese índice | **imprime un diagnóstico y sale con 1**. No escribe nada en este modo |
| `08-ARQUITECTURA/RE-INDEX.md` es el índice de hallazgos | es `# RE-INDEX — correcciones propias (Polaris12)`: un registro de errores 1..N y su corrección |

La tercera medición es la que más me engaña: conté «450 hallazgos en disco, 303 de sus
números no aparecen en `RE-INDEX.md`» y lo escribí como brecha de cobertura. **Estaba
midiendo una lista de hallazgos contra un registro de correcciones.** Cero de los 450
nombres de fichero aparecen ahí, y no deberían aparecer ninguno.

**Y hay una cuarta, que es la que más me cuesta escribir.** Escribí el hallazgo 1048
—«un filtro que excluye por construcción a la población que dice medir»— y en la misma
sesión conté los duplicados con `^\d{4}-`, que sólo encuentra los de cuatro dígitos, y
obtuve **1 duplicado en lugar de 74** porque el rango real es de tres. Lo anuncié como
«1, no 74» y construí sobre ello. **Es exactamente la cuarta instancia del defecto del
1048, y la cometí a la vista del 1048.**

## Por qué no se repara, y por qué no es que no se pueda

Mecanicamente es trivial: 175 ficheros, 74 números, hay que renumerar **101**, y hay
**797 números libres**. Ni la mecanica es el problema.

El problema es epistemológico y el hallazgo 1040 ya lo escribió:

> *«reparar una cita de la forma `NNN` exige saber **QUIÉN TENÍA EL NÚMERO ANTES**»*

Con 2588 citas que nombran un número duplicado, y esos números teniendo 2 o 3
ficheros distintos, **no existe en el árbol información que diga cuál quería el autor.**
Renumerar un fichero convierte sus citas en ambigüas o falsas, y no hay forma de
arreglarlas después, porque el destino no se conoce.

Y renumerar es peor que eso: es la operacion que ya está documentada como
peligrosa en este proyecto. Un renumerado es un acto con procedencia, y aquí la
procedencia sería inventada.

## Qué sí se puede hacer ahora, y es barato

**1. Desambiguar `CORRECTED_BY`.** Es el dano concreto y verificable, y no exige
renumerar nada: `CORRECTED_BY=NNN` necesita el **nombre del fichero**, no el número.
`CONTRADICTIONS.md` necesita el mismo dato para calcular el sentido de una flecha. Con
esa información, el generador deja de abortar y las 175 filas dejan de ser ambiguas
— **sin tocar ni un número**.

**2. Cerrar la diferencia de 366 citas** entre mi 2588 y el 2222 del censo. Es un
recuento contra dos denominadores: hay que saber qué ficheros entran en cada uno.

**3. Una puerta que ya no depende de la unicidad.** La que importa a futuro, y que es
la generalización de 1048 aplicada aquí: **`CORRECTED_BY` y el índice de
contradicciones no deberían necesitar la unicidad del número como precondición para
funcionar.** Deberían poder trabajar con el par `(número, fichero)` y, cuando el numero
esté duplicado, **decir que está ambiguo** en lugar de resolverlo en silencio.

## Lo que NO se afirma

- **No se afirma que los 74 duplicados sean un defecto del contenido.** Son 175
  hallazgos distintos que comparten número. Puede que el número sea la clave que se
  eligió mal, y no los hallazgos.
- **No se afirma que la cifra de 2588 sea la buena.** Es la mía, con mi denominador.
- **No se repara nada aquí.** No se renumera, no se edita `CONTRADICTIONS.md`, no se
  toca el generador.