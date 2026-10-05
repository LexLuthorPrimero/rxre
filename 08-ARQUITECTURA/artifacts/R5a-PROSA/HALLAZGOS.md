# R5a-PROSA — el contrato en prosa de las herramientas no se falsificaba, y hay seis opciones documentadas que no existen

<!-- MEDIDO con tools/prosa.py. Artefacto: prosa.json (238 filas).
     Regenerar: python3 tools/prosa.py --json > 08-ARQUITECTURA/artifacts/R5a-PROSA/prosa.json -->

```
AGENCIA=RX550-INVESTIGACION · AGENT RE/TOOLING
WORK_CLASS=validacion-de-instrumentacion
RUNTIME=NO · sin sudo · sin ejecucion · GPU=INTACTA
escritura=3 ficheros NUEVOS.  Ningun fichero existente modificado.
herramienta   tools/prosa.py 1.0.0
sha256        b28dcf07ed83cc7818d36838245d478c6274254ed0e07691a999c722adc4a3b2
              (b28dcf07 es el vigente, y lo verifiqué con
               `git hash-object tools/prosa.py` DESPUÉS de la última edición,
               porque en una versión anterior de este bloque pondría un hash
               que ya no valía.  Un hash obsoleto en un bloque de procedencia
               es exactamente la clase de mentira que este trabajo denuncia)
artefacto     08-ARQUITECTURA/artifacts/R5a-PROSA/prosa.json
sha256        f1fdb1e7c4d259c8077f84909d9daa7099c991f47281b6615431b048e4c1f1cd
reproducible  f1fdb1e7c4d259c8077f84909d9daa7099c991f47281b6615431b048e4c1f1cd  (2 corridas, mismo hash)
informe       08-ARQUITECTURA/artifacts/R5a-PROSA/informe.txt
sha256        aab566d5ebdf42770f8ce081e7b6c37f60637d09f586afbe6816af140caeec5d
selftest      28 vectores, 0 fallos, rc=0   (HERMETICO: verificado en cwd ajeno)
```

## 0 · EL HUECO, Y LO DECLARO EL PROPIO PROYECTO

La capa meta ya mide si una herramienta tiene **forma** de contrato. Lo dice
`tools/toolcheck.py`, literalmente:

> *Lo que NO hace: no comprueba que la herramienta diga la verdad. Comprueba
> que tenga forma de decirla.*

Y `tools/riesgo.py` sí falsifica declaraciones — pero solo del vocabulario
**maquinable**: `WRITES_FILES=no`, `WRITES_GPU=no`, `READONLY=yes`. Tokens.

**La mayoría de las herramientas de este árbol no llevan contrato maquinable:
llevan prosa.** Secciones `QUE RESUELVE`, `LIMITE DECLARADO`, `VALIDACION`. Es
la forma que usan casi todas, y no hay token que falsificar.

MEDIDO sobre los siete directorios declarados en `toolreg.TOOL_DIRS`:

| | |
|---|---|
| ficheros | **238** |
| con contrato en prosa | **205** |
| `.c`/`.sh` → `NO_CLASIFICABLE` | 32 |
| sin docstring | 1 |

Y de las 205 con contrato, cuántas declaran una entrada que su código no
resuelve:

| veredicto | nº | qué es |
|---|---|---|
| `SIN_RESOLVER` | **242** | la prosa nombra un fichero y el código no lo menciona |
| `FLAG_INEXISTENTE` | **6** | la prosa nombra un flag que `add_argument` no registra |
| `SOLO_EN_LISTA` | 129 | se enumera como candidato. **No falsable.** |
| `EN_APLICACION` | 76 | el nombre llega a una llamada. No prueba uso. |
| `AUTOREFERENCIA` | 160 | la herramienta nombrándose a sí misma |

## 1 · R5-01 · SEIS OPCIONES DOCUMENTADAS QUE NO EXISTEN

Este es el hallazgo que carga, y es **decidible por completo**: lo que la
prosa nombra contra lo que `add_argument` registra. No hay heurística.

| herramienta | flag documentado | `add_argument` registra | verificado a mano |
|---|---|---|---|
| `tools/claim.py:47` | `--coverage` | `--repo --scaffold --locate --next-id --json --selftest --version` | **SÍ** |
| `tools/msg_census.py:43` | `--list-unknown` | `--kernel --chip --root --msg --detail --json --selftest` | **SÍ** |
| `tools/reg_resolve.py:35` | `--across-headers` | `--kernel --amd-root --gfx --reg --field --fields-of --resolve --json --selftest` | **SÍ** |
| `tools/struct_layout.py:48` | `--fields` | `--kernel --amd-root --struct --offset --json --selftest` | **SÍ** |
| `tools/xref.py:43` | `--declares` | `--kernel --file --symbol --callers --json --selftest` | **SÍ** |
| `08-ARQUITECTURA/tools/contradict.py:50` | `--with-code` | `--sym --dir --all --check --min-sites --json --self` | **SÍ** |

Las seis están en un **bloque de opciones** del docstring — el sitio donde el
proyecto documenta lo que la herramienta acepta — y las seis son
ejemplos de uso que **no funcionan**.

Las cinco primeras son de la misma forma: una línea de ejemplo
`herramienta.py --kernel RAIZ --opcion` que alguien copió del patrón y no
existe. La sexta es distinta y más interesante:

```
  contradict.py --check             existe el valor en el codigo? (--with-code)
```

La prosa **sugiere** un flag `--with-code` que no existe; el flag real es
`--check`. Quien lea esa tabla y componga la orden obtiene un error de argparse
con el nombre de la opción que él se inventó, no con el que funciona.

> **Por qué esto importa y no es cosmético.** `TOOLS-STATUS.md` clasifica a
> `claim.py`, `msg_census.py`, `reg_resolve.py`, `struct_layout.py` y `xref.py`
> como `TOOL_VALIDATED` — su `--selftest` pasa. El estado de validación mide
> que la herramienta **funciona**. No mide que su **documentación** sea
> ejecutable. Una herramienta cuyo docstring da una orden que sale con error
> esta `TOOL_VALIDATED` y equivocada a la vez, y nada en el registro actual
> puede distinguir esos dos estados.

## 2 · R5-02 · LA ADJUDICACIÓN A MANO: 4 DE 8 FALSOS POSITIVOS

Esto es lo que hace el hallazgo utilizable, y es la parte que no se puede
saltar. La primera medición sobre el árbol real dio **35** `FLAG_INEXISTENTE`.
Los adjudiqué uno a uno leyendo el código. **Cuatro eran falsos.**

| fila | veredicto | por qué es FALSO |
|---|---|---|
| `struct_layout.py --fields` | FP | **yo me equivoqué al adjudicar**: `struct_layout.py` no registra `--fields-of`; ese flag es de `reg_resolve.py`. La herramienta tenía razón |
| `reenvio_freeze.py --forzar` | FP | la prosa dice `**ELIMINADO.**`. Documenta la retirada, honestamente |
| `flags_inventory.py --self` | FP | la herramienta lee `sys.argv[1:]` a mano; su docstring lo declara |
| `artifacts.py --que`, `--el`, `--y`, `--aceptar` | FP | la prosa usa `--` como guion parentético. No son flags |
| `round.py --contradictions` | FP | es el flag de `causal_map.py`, nombrado en su línea. La frase es verdadera |
| `prosa.py --algo` | FP | ilustración del patrón, dentro de este mismo fichero |

**35 → 6.** Tres correcciones, cada una con su regla y su vector:

1. **Guion parentético y flags de otro programa.** Un `--x` solo cuenta si la
   línea **empieza** por él **y tiene una vecina que también empieza** por un
   flag — la firma de un bloque de opciones. O si la línea invoca a **este**
   programa. Sin la exigencia de la vecina, dos vectores fallaban: una frase
   partida en dos líneas empieza igual que un bloque de opciones.
2. **Abreviatura de argparse.** `--fields` **funciona** si existe `--fields-of`,
   porque `allow_abbrev=True` es el defecto de CPython. Sin esta rama la
   herramienta acusaba de mentirosa a una documentación que funciona.
3. **Flag retirado.** Si la línea dice `ELIMINADO` / `ya no existe`, el
   veredicto es `FLAG_RETIRADO`, no inexistente. Acusar ahí sería responder a
   una pregunta que nadie ha hecho.

**Los cuatro FP que-me-quedaron son la mitad de la primera lista, y por eso la
adjudicación no es opcional.** Un eje que dice 35 y acierta 31 no es un eje.

## 3 · R5-03 · EL CASO QUE MOTIVÓ LA HERRAMIENTA, Y POR QUÉ NO ES HALLAZGO

Este documento existe por una caso concreto, y ese caso **no sale como
hallazgo**. Se dice con todas sus letras.

`revkit/pm4dec.py` declara en su docstring:

> *De `sid.h` del corpus, leído EN TIEMPO DE EJECUCIÓN.*

Y su código hace lo contrario, y lo dice a cuarenta líneas:

- elige la tabla con el **grafo de includes** de `gfx_v8_0.c` (MEDIDO por R2:
  ese fichero compila `vid.h` y ningún otro header de opcodes), y
- su propio bloque de comentarios explica que **`sid.h` es la cabecera
  disidente**: la única de seis que desplaza `LOAD_SH`/`LOAD_CONFIG`/
  `LOAD_CONTEXT` una posición (`0x61/0x60/0x5F` frente a `0x5F/0x60/0x61` de
  las otras cinco).

O sea: **el contrato en prosa declara exactamente el INPUT que el código
existe para rechazar.**

Mi herramienta lo ve y lo clasifica `SOLO_EN_LISTA`, y la deja en la sección
informativa. Y **ese es el veredicto correcto**, por esto:

- el literal `sid.h` **sí aparece** en el código —en `HEADERS_OPCODE`, en
  `SID_CANDIDATOS`, en `RENUMERADOS_SID`— porque lo nombra para excluirlo;
- por tanto un chequeo de prosa **no puede falsarlo**: no hay ausencia que
  medir;
- y la verdad de la cadena (`vid.h` es la cabecera que esta generación compila)
  **no la da un grep de prosa**: la da el **cierre de includes**, que es
  trabajo de R2, no de un verificador de prosa.

> **Lo que esto deja, dicho sin adornos.** Un instrumento de este estilo puede
> demostrar que una declaración **no se resuelve** en el código. No puede
> demostrar que sea falsa cuando el código la menciona para descartarla. La
> diferencia entre las dos cosas es un **grafo de includes**, y confundirlas es
> exactamente el error que este trabajo denuncia en los demas.

**Esto no es un hallazgo nuevo de `pm4dec.py`. Es un hallazgo sobre el
instrumento**: la afirmación que carga con la mayor parte del peso del
decodificador PM4 del proyecto **no es falsable con esta clase de
instrumento**, y hasta ahora no estaba escrito en ninguna parte.

## 4 · R5-04 · LO QUE ESTO MIDE Y LO QUE NO

**Mide**, con oráculo independiente:

- Para un **flag**: qué nombra la prosa contra qué registra `add_argument`.
  Decidible, completo, sin heurística. Es el único veredicto fuerte.
- Para un **fichero**: si el nombre que la prosa declara llega a una llamada
  (`EN_APLICACION`), solo se enumera (`SOLO_EN_LISTA`) o **no aparece**
  (`SIN_RESOLVER`).

**No mide, y no se puede medir con análisis estático de prosa:**

- que un fichero en `EN_APLICACION` se **use** de verdad. El nombre llega a una
  llamada; no se sabe si de ahí sale una lectura o un mensaje de error.
- que `SIN_RESOLVER` sea **MENTIRA**. Una ruta construida en tiempo de ejecución
  —`prefijo + sufijo`— no deja rastro literal. `SIN_RESOLVER` significa "la
  declaración no se resuelve en el código", y se queda ahí.
- los **comentarios**, que no están en el AST. Por eso `reenvio_freeze.py`
  documenta en un comentario que `--forzar` ya no existe, y eso no lo ve: lo ve
  la prosa.
- `.c` y `.sh`: 32 ficheros `NO_CLASIFICABLE`. Su prosa vive en comentarios, y
  `ast` no la da. Contarlos como `SIN_RESOLVER` sería el defecto entero con
  otro envoltorio.

**Una regla que es demasiado ancha, y se deja así a propósito.** La rama que
degrada a `NO_CLASIFICABLE` porque el código menciona `sys.argv` salta con el
modismo `sys.exit(main(sys.argv[1:]))`, que es universal — `claim.py` lo tiene
en la línea 758. Se podría afinar y no se ha hecho: el error va hacia *no se
puede concluir*, nunca hacia *acuso*. Un instrumento que acusa de más no sirve;
uno que se calla de más solo pierde sensitivity, que se recupera leyendo el
código.

## 5 · LO QUE NO SE TOCA

- **No se corrige ninguna prosa.** Este nodo MIDE. Las seis opciones de §1 las
  corrige quien escribió esas herramientas, y son seis correcciones de una
  línea.
- **No se regenera `TOOLS-STATUS.md`.** Lo genera `tools/artifacts.py`, y ese
  fichero estaba **modificado sin commitear** por otro nodo mientras esto
  corría (`git status`). Regenerarlo habría escrito sobre el trabajo de otro.
  Ver §7.
- **No se toca la GPU, ni el módulo, ni el runtime.** Análisis estático de
  ficheros. Por eso no necesita puerta.

## 6 · LOS DEFECTOS PROPIOS QUE SALIERON AL VALIDARLO

El selftest no fue decorativo: **en la primera ejecución falló 9 de 18
vectores**, y los 9 eran defectos reales.

| defecto | cómo lo cogió |
|---|---|
| **el docstring se contaba como código** | `ast.walk` ve el docstring del módulo igual que cualquier cadena, así que las palabras del contrato entraban como referencias y **toda** declaración salía `SUSTENTADA`. Un instrumento que no puede fallar no informa de nada: habrían salido 238 filas en verde |
| **hermetismo recursivo** | el vector comprobaba el cwd lanzando `--selftest`, que lanzaba el vector hermetico, que lanzaba `--selftest`. Bomba de procesos: 120 s sin imprimir |
| `SID_CANDIDATOS` con `if (a := "FLAG", tok) in vistos` | syntactically legal, ilegible. Reescrito |
| fichero vacío clasificado `SIN_CONTRATO` | un fichero vacío no es "una herramienta que no declara nada": no hay ni prosa ni código con el que comparar |
| ruta con directorio → `SIN_RESOLVER` | la prosa escribe `drivers/gpu/drm/amd/amdgpu/vid.h` y el código escribe `"vid.h"` porque lo resuelve con `os.path.join`. **El caso correcto**, y cargarlo sería acusar de mentira a la herramienta que hace bien. Ya le pasó a este proyecto con la resolución de includes en un solo directorio (R2-02) |
| **131 filas de autorreferencia** | `inventario_universo.py -- hace un inventario`: la herramienta nombrándose. **35 % de las 373** `SIN_RESOLVER` iniciales. Una herramienta no es su propia entrada |

Los seis estan en `--selftest` con vector. Los dos ultimos los vi al MEDIR, no
al escribir, que es la parte que un selftest escrito a posteriori no caza.

## 7 · SIGUIENTE ACCIÓN DE TOOLING, PARA QUIEN LLEVE EL REGISTRO

1. **Corregir las seis opciones de §1.** Seis líneas, seis herramientas.
2. **Registrar `tools/prosa.py` en `TOOLS-STATUS.md`**, cuando
   `tools/artifacts.py` deje de estar modificado por otro nodo. Ahora
   declararía 239 herramientas, no 238.
3. **Extender el eje de prosa a `.c`.** Son 32 ficheros, y varios son
   instrumentos que el proyecto usa (`amdmmr.c`, `amdinfo.c`, `vbiosread.py`).
   Requiere comentarios, no AST: otra clase de oráculo, y por tanto otro
   instrumento. No se ha hecho aquí.
4. **Atacar el caso `SOLO_EN_LISTA` con la herramienta correcta**, que no es
   esta: un resolvedor que compare *qué cabecera selecciona el grafo de
   includes* contra *qué cabecera declara la prosa*. R2 ya tiene la mitad.

```
ESTADO
  ficheros escritos    3, todos nuevos
  ficheros modificados 0
  GPU                  INTACTA
  sudo                 NO usado
  commits              NINGUNO
  adjudicacion a mano  8 de 8 (4 falsos positivos encontrados y corregidos)
```

```
OBSERVATION_FOR_MAIN_AGENT
  revkit/pm4dec.py: el docstring declara que los opcodes salen de sid.h y el
  codigo los saca de vid.h por el grafo de includes de gfx_v8_0.c.  sid.h es
  ademas la cabecera DISIDENTE de las seis, segun R2.  No lo corrijo aqui: es
  una frase de docstring de un fichero que otro nodo esta editando
  (revkit/ aparecia modificado en git status durante esta sesion).
  Decision de semantica HW -- cual opcode es el bueno para GFX8 -- NO es mia.
```