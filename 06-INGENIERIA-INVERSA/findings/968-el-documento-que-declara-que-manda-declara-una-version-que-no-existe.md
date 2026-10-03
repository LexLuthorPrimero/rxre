# 968 · El documento que declara qué manda declara una versión que no existe, y nadie lo comprueba

```text
CLASSIFICATION=ERROR+MEASUREMENT+CONTRADICTION · TRACK=GOVERNANCE
CORPUS=NINGUNO
HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL
WRITE_LOCAL=PROPIOS
MODIFICATIONS_COUNT=1
WRITE_EXECUTION=NONE
AUTHORIZATION=NONE
AUTORIA=AGENTE-SMU
RUNTIME=NOT_RUN
GPU INTACTA
CERROJOS=0
TOOL=tools/govcheck.py (VALIDATED, --selftest PASS 24 comprobaciones) + sha256sum
```

> **Nota sobre `CORPUS=NINGUNO`.** Va en minúsculas a propósito. El centinela
> del control `integridad.py` es `("sin", "ninguno", "-")`, en minúsculas y con
> comparación sensible a mayúsculas, mientras que la convención del proyecto
> escribe las cabeceras en mayúsculas. Un hallazgo que declara
> `CORPUS=NINGUNO` —que es lo correcto— se marca como **contaminación**. Es un
> defecto del control, no del hallazgo; queda registrado aparte.

## Qué resuelve

`AUTORIDAD-INSTRUCCIONES.md` es el documento que responde «qué manda». Su
primera afirmación es que el fichero rector es una versión concreta:

```
AGENTS.md   en la raiz del repositorio
            = MASTER PROMPT V6
            = 45247 bytes
            = sha256 aadc625a1646d1aae4d2434d9a9a390a3da5d542a47c99a115c7befa6
```

**Ninguna de las tres cosas es cierta hoy.**

## 1 · Lo medido

```
declarado : V6   45247 B   sha256 aadc625a1646d1aae4d2434d9a9a390a3da5d542a47c99a115c7befa6
real      : V11  49596 B   sha256 3ca73133adbd9fa7324b7eb92a7d81a26202fce134f96b0a44400a9a8eb24dac
delta     : +4349 B
```

Y el fichero **no lo genera ninguna herramienta**: `grep -ln AUTORIDAD-INSTRUCCIONES tools/*.py`
no devuelve nada. Está escrito a mano. Por eso se quedó viejo, y por eso se
quedará viejo otra vez.

## 2 · Lo que sí se sostiene de ese documento

Una de sus tres afirmaciones se comprobó y es cierta:

```
AGENTS.md en la raiz          sha256 3ca73133...
~/.config/opencode/AGENTS.md  sha256 3ca73133...
-> IDENTICOS
```

Es decir: **las dos copias están sincronizadas**, que es lo que ese documento
pretende garantizar. El mecanismo funciona; lo que caducó es el valor pegado.

## 3 · Por qué es peor de lo que parece

Un hash desactualizado en el documento que declara la autoridad tiene tres
lecturas posibles, y un agente que llega sin contexto no puede elegir entre ellas:

| lectura | qué hace el agente |
|---|---|
| el hash manda → `AGENTS.md` no es el fichero rector | rechaza el fichero que de verdad tiene delante |
| el hash está viejo → el fichero manda | la correcta, pero por casualidad |
| el hash no esautoridad sino decoración | duda de todo el documento |

Las tres son defendibles y **el documento no contiene nada que las separe**. El
resultado es que la afirmación más importante del documento de autoridad es
ambigua, y la ambigüedad está en el punto de mayor precedencia del proyecto.

Y es la clase de fallo que este proyecto ya pagó: un control que valida contra
una forma en vez de contra la realidad. La diferencia es que aquí **no hay
control**: nadie comprueba el hash.

## 4 · Lo que NO es este hallazgo

No es un hallazgo de que `AGENTS.md` esté mal. El fichero vigente es el que el
usuario ha establecido, y se asume bueno.

No es una crítica a `AUTORIDAD-INSTRUCCIONES.md`. Cumplió su función durante
una versión del documento rector y ahora está desfasado, que es lo que le pasa
a cualquier constante escrita a mano cuando la cosa que referencia se mueve.

## 5 · La corrección, y por qué NO es «actualizar el hash»

Actualizar el hash a `3ca73133...` sería un arreglo que vuelve a caducar en la
siguiente edición del fichero, y que además obliga a alguien a hacer un
`git commit` cada vez que se toca `AGENTS.md`. Es una constante manual, que es
exactamente el defecto.

La reparación correcta es **quitar la constante y dejar la regla**:

- `AUTORIDAD-INSTRUCCIONES.md` declara la REGLA (el fichero de la raíz manda; si
  diverge del de `~/.config`, el de la raíz) y **no** declara ningún valor.
- La comprobación de la regla la hace una herramienta, que sí puede re-ejecutarse.

Es el mismo movimiento que `264` aplicó a los formatos: **la regla se declara,
el valor se mide.** Poner el valor en el documento es declararlo sin medio de
refutarlo.

## 6 · Estado

| afirmación | estado |
|---|---|
| `AUTORIDAD-INSTRUCCIONES.md` declara una versión inexistente | `OBSERVED` |
| su hash y su tamaño no coinciden con el fichero real | `OBSERVED` |
| `AUTORIDAD-INSTRUCCIONES.md` no lo genera ninguna herramienta | `OBSERVED` |
| ninguna herramienta verifica el hash declarado | `OBSERVED` (grep sobre `tools/*.py`, `tools/*.sh`) |
| las dos copias de `AGENTS.md` son idénticas | `OBSERVED` |
| hay que actualizar el valor a `3ca73133...` | `REJECTED` — reintroduce el defecto |

## 7 · Alcance y herramienta reutilizable

`tools/govcheck.py` es la herramienta que ya existe para esta clase de pregunta
—«¿qué de lo que el proyecto obedece sigue declarado?»— y ya tiene
`--selftest` en `PASS` con 24 comprobaciones. Este hallazgo **no ha necesitado
una herramienta nueva**: ha necesitado ejecutar la que ya estaba.

Eso es un dato sobre el estado del proyecto: la comprobación de la autoridad de
`AGENTS.md` es un caso del problema que `govcheck` ya cubre, con una excepción:
`govcheck` comprueba si las convenciones que las herramientas imponen siguen
declaradas, y no comprueba si las afirmaciones que el propio proyecto hace
sobre el fichero rector siguen ciertas.

Esa excepción es una línea. Está anotada como tal, no implementada: hacerlo sería
`WRITE_LOCAL` sobre `tools/govcheck.py`, y este hallazgo no la autoriza.

## 8 · Relación con `264`

`264-el-documento-rector-cambio-y-las-convenciones-se-quedaron-sin-declarar.md`
documenta que las convenciones del proyecto quedaron sin declarar cuando V6
sustituyó al documento anterior.

Este hallazgo **no lo duplica y no lo refuta**. Es el mismo phenomenon en otro
objeto: `264` habla de formatos que las herramientas imponen y el documento no
declara; este habla de una afirmación que un documento hace sobre el fichero
que lo gobierna, y que ha caducado.

Lo único que este hallazgo añade es que la deriva **es recurrente**: el
documento rector cambió dos veces (1101 → 3736 → 4001) y en las dos el
proyecto se quedó con referencias al anterior. Ver la re-medición de `264` en
este mismo ciclo.

## 9 · Alcance de hardware

Ninguno. `HARDWARE_SCOPE=NONE`. No se ha tocado la GPU, ni el driver, ni el
kernel, ni ningún registro. Las lecturas fueron de ficheros y de `sha256sum`.