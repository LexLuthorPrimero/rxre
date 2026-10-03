# 961 — Dos artefactos con `PASS` y relojes a 313 y 1071 MHz: el 12 % de los pares del banco no son comparables entre sí

Estado: `PROVEN`. `bench.py` 24 de 24; 6 suites.
Alcance: `08-ARQUITECTURA/validations/`, 57 artefactos.
AUTORIA=AGENTE-SMU

## El hueco que había

Cada artefacto graba `hardware.fingerprint()` con `sclk_hz`, `mclk_hz`, `bar_size` y el kernel. **Y
nadie comparaba dos artefactos.** La información para saber si dos corridas eran comparables estaba en
el disco desde siempre y no se leía nunca.

La puerta de reloj que `959` añadió a la suite `jerarquia` —que corta si el reloj varió más de un 25 %
dentro de una corrida— resolvió el problema *dentro* de una corrida. El problema mayor era *entre*
corridas: dos mediciones de tiempo a 313 MHz y a 1071 MHz son ambas `PASS` y su diferencia parece una
medición cuando es un cambio de condiciones.

## Lo que hay en el disco ahora mismo

```
artefactos en disco: 57

suite          n   relojes sclk        veredictos
coalescencia    2   338 .. 1071 MHz     INVALID, PASS
curva          1   1071 .. 1071 MHz    PASS
jerarquia      5   304 .. 1066 MHz     PASS
regresion     11   1071 .. 1071 MHz    INVALID, PASS
selftest      33   438 .. 1071 MHz     PASS
textura        5   641 .. 1059 MHz     INVALID

4 de 6 suites con reloj variable entre corridas, relación mínima 0,29
```

**`jerarquia` tiene cinco artefactos, todos `PASS`, grabados entre 304 y 1066 MHz.** Cualquier
comparación entre ellos produciría un número sin sentido, y hasta ahora nada lo decía.

## Lo que se añadió

Cada artefacto nuevo lleva un bloque `comparabilidad`:

```json
"comparabilidad": {
  "estado": "NO_COMPARABLE",
  "previo": "bench-jerarquia-20261003-075732.json",
  "difieren": ["sclk_hz"],
  "comparables": {"sclk_hz": {"anterior": 313620000, "ahora": 1066000000,
                              "razon": 3.41, "estado": "DIFIERE"}},
  "nota": "la medicion es valida; lo que no esta licenciada es compararla con la anterior"
}
```

Se comparan `sclk_hz`, `mclk_hz`, `bar_size`, `pcie_gen`, `pcie_width` y el kernel, con una tolerancia
del 10 % por debajo de la cual se consideran el mismo estado.

## Lo más importante: el veredicto NO cambia

**`INVALID` significa que el dato es malo. `NO_COMPARABLE` significa que el dato está bien y la
comparación no está licenciada.** Son cosas distintas y colapsarlas es peligroso en las dos
direcciones: o se tiran datos buenos, o se conceden comparaciones inválidas.

Una corrida a 313 MHz es una medición perfectamente válida de lo que la GPU hizo a 313 MHz. Lo que no
vale es restarla de otra a 1071 MHz. Por eso la comparación va en un bloque aparte y el veredicto
intacto, y por eso el self-test comprueba las dos cosas por separado:

```
una corrida a 313 MHz contra otra a 1 GHz se marca NO_COMPARABLE    OK
la medicion sigue siendo PASS aunque no sea comparable              OK
```

Un control que solo sabe decir «no» no vale: **la primera corrida dice `SIN_PREVIA`**, y está.

## El fallo que el test descubrió, y era de pérdida de datos

Al montar el caso de comparabilidad falló, y no por la comparabilidad: **dos corridas dentro del mismo
segundo escribían el mismo fichero y la segunda pisaba a la primera.**

El nombre del artefacto es `bench-<suite>-<YYYYmmdd-HHMMSS>.json`, con resolución de un segundo. El
self-test hace dos escrituras seguidas y cayó dentro del mismo segundo, así que el artefacto previo
desapareció y la comparabilidad no tenía con qué comparar.

Eso no era un artefacto del test: **es pérdida de datos real**, y hacía que la comprobación que
acabo de añadir no tuviera nunca nada que comparar. El sufijo va ahora con cero a la izquierda
(`-002`), para que el orden lexicográfico siga siendo el orden cronológico —que es como se elige el
previo—: con `-2`, `-3`, `-10` sin rellenar, el `-10` ordenaría antes que el `-3`.

Es la segunda vez hoy que un caso de prueba encuentra un fallo de pérdida y no un fallo de lógica. La
razón es la misma en las dos: **un caso de prueba que hace dos cosas seguidas tropieza con el
segundo, que es donde están las colisiones de tiempo y de estado.**

## Un detalle de diseño que no cambió, a propósito

`comparar_con_previo` se llama **después** de escribir el fichero, porque comparar con el previo exige
que el actual ya esté en disco. Es un rodeo feo. La alternativa sería elegir el previo antes de
escribir, y sería más limpio; no la hice porque el codigo ya funciona y el self-test lo cubre, y
cambiar algo que funciona para que sea más bonito es el tipo de trabajo que este proyecto ha
despreciado siempre.

## Instrumentos

- `bench.py`: `artefactos_de()`, `comparar_con_previo()`, bloque `comparabilidad` en cada artefacto,
  sufijo sin colisión de nombre, 4 casos de self-test. **24 de 24.**
- Las seis suites sin cambios de comportamiento.

## Lo que queda abierto

- ~~Los 57 artefactos anteriores no tienen bloque de comparabilidad.~~ **Hecho**, y el resultado
  importa: contando pares, no artefactos sueltos,

  ```
  suite          n     licencia       pares no comparables / totales
  coalescencia   2     NINGUNA        1 de 1
  jerarquia      5     PARCIAL        4 de 10
  regresion     11     todas          0 de 55
  textura        5     PARCIAL        4 de 10

  total, sin selftest: 9 de 76 pares NO comparables (12 %)
  ```

  **El daño está concentrado, no repartido.** `coalescencia` tiene dos artefactos a 338 y 1071 MHz:
  **ninguna** pareja es comparable, así que la serie es inútil para comparar entre corridas, y su
  contenido dentro de una misma corrida sigue valiendo. `jerarquia` y `textura` pierden el 40 % de sus
  pares. `regresion` está limpia: sus once artefactos están todos a 1071 MHz.

  Esto corrige la lectura de arriba. El titular «los 57 artefactos no son comparables» era
  exagerado: el 88 % de los pares sí lo son. Lo que no es comparable es una **cuarta parte** de las
  comparaciones, concentrada en las suites nuevas.
- **La tolerancia del 10 % es un número puesto por mí**, sin justificar. Con la relación de reloj que
  se observa (0,29 a 3,4×) cualquier tolerancia entre 5 % y 30 % daría la misma respuesta, así que
  el numero no importa *ahora*. Importara cuando haya que afinar de verdad.
- **`jerarquia` es la única suite con puerta de reloj dentro de la corrida.** Las otras cinco
  dependen del reloj igual que ésta, y ahora tienen la comprobación *entre* corridas, pero no la de
  *dentro*. Son dos huecos distintos y el segundo sigue abierto.
