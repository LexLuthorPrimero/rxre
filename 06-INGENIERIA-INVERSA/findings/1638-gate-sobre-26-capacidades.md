# 1638 — EL GATE SOBRE LAS 26 CAPACIDADES: 16 PASAN, Y LO QUE FALLABA ERA UNA FORMA, NO ONCE FALLOS

```text
CLASSIFICATION=IMPLEMENTATION
WORK_CLASS=RXRE-AUTO-002
AUTOR=SISTEMA AUTONOMO RXRE
FECHA=2026-10-15
TARGET=Polaris12 (RX550) · GFX8 · 1002:699f
QUESTION=¿Cuantas capacidades del CLI pasan los ocho principios, y por que?
STATE=PROVEN
```

## EL PUNTO DE PARTIDA

RXRE-AUTO-001 (1637) puso el gate de los ocho principios DENTRO de `_persistir`.
Pero el gate solo se habia probado con DOS capacidades: `source.ast_parse` y
`binary.inspect`. Las otras 24 no habian pasado por el ni una vez.

Un gate calibrado con dos muestras de veintiseis no es un gate: es una puerta
con dos hojas probadas. Este hallazgo mide las veintiseis.

## LA MEDICION

```text
antes (1637)                despues (1638)
-------------------         -------------------
PASA           4            PASA                16
BLOQUEADA     11            BLOQUEADA            0
NO_CUBIERTA    8            NO_CUBIERTA          4
PRODUCTOR_*    3            PRODUCTOR_*           5
                            SIN_GATE              1
```

Instrumento: `.work/tmp/auditar_todas.py`. Ejecuta cada capacidad con una
entrada REAL y registra el veredicto del gate. No es un test: es el instrumento
de medicion. Los tests vienen con los datos.

## LAS 11 BLOQUEADAS ERAN UNA SOLA CAUSA

Las 11 bloqueadas decian lo mismo, con las mismas dos razones:

```text
TIERRA sin prueba: provenance como cadena sin estructura
FUEGO   sin prueba: sin provenance estructurada
```

No son once fallos: es UN fallo de forma, once veces. Un principio que se
queja once por cada capacidad esta describiendo un contrato que nadie cumple,
no once defectos independientes.

Y el dato NO faltaba. MEDIDO en `cs_disasm.py`:

```text
linea 231:  pre["input_hash"] = sha256_de(ruta)
linea 343:  "artifact_hash": pre["input_hash"]
```

El hash se calcula y se USA. Lo que no se hacia era copiarlo a donde el
contrato lo pide. La evidencia estaba archivada en `pre` y en el resultado; el
campo `provenance` recibia la palabra:

```python
"provenance": "completa"     # <- una palabra donde el contrato pide evidencia
```

## POR QUE NO SE RELAJO EL GATE

Porque relajar seria el error caro, y ya se pago una vez: convertir un principio
en lista de exenciones. Si `provenance: "completa"` se aceptara, las once
capacidades volverian a persistir y el nombre `completa` seguiria mintiendo.

El gate estaba bien calibrado. Lo que estaba mal era el contrato incumplido.

## LO QUE SE HIZO

**Un constructor, no once parches.** `backends/adapters/provenance.py`:

```python
def construir(estado, input_hash, backend, command_or_api,
              transformacion, normalizador, ...) -> dict
def desde_precheck(pre, **kw) -> dict     # atajo para los 8 adapters
```

Los ocho adapters que usaban la cadena pasan a usar el dict. Y cada uno recibe
una `transformacion` VERDADERA: la que su propia documentacion declara. Un
constructor comun no puede saber que hace cada adapter, asi que el adapter la
dice y el constructor la escribe. Si el modulo la rellenara por su cuenta,
seria el modulo mintiendo en nombre de quien no miente.

## EL AGUJERO DE AGUA: EL GATE APROBABA Y NADIE GUARDABA

Medido despues de arreglar la provenance:

```text
gate=True   persistido=False   operation_id=None
```

Diez capacidades pasaban el gate y no persistian. Ocho adapters no tenian
`persistir()`. AGUA quedaba satisfecho en la INTENCION (`persiste_pretendido`)
y NO en el hecho. Y la propiedad de AGUA es el hecho: "recuperable por
`result_id`".

**Un fallback generico, no ocho wrappers.** `store.registrar` YA es generico:
toma la operacion y la guarda. Los ocho wrappers existentes solo difieren en el
nombre de la capability y el target. Escribir ocho copias del mismo dict es
como se producen ocho formas distintas, y las ocho se pudren.

El fallback exige lo mismo que el gate ya aprobo: `result_id` en cada resultado e
`input_hash` en la provenance. Si falta, NO guarda. Un fallback que guardara
cualquier cosa seria peor que no tener fallback.

Resultado: **las 16 que pasan ahora tambien persisten.**

## LA CAUSA RAIZ DEL RESTO: `/tmp` LLENO

Y aqui esta lo que mas valor tiene, porque no era un bug del codigo.

```text
/tmp: 5,9 G usado, 0 libre (100%)
```

El culpable era un directorio oculto de 5,2 G:

```text
/tmp/.fix-01-COORDINACION-1001876
├── 06-INGENIERIA-INVERSA/agents/ast/sdma_v3_0.c.json    830 MB
├── tools/rxre/github/radare2/.git/...pack                205 MB
├── tools/rxre/github/rizin/.git/...pack                  167 MB
├── rx550-upstream-7.2.8/linux-7.2.8.tar.xz              153 MB
├── RESEARCH/evidence/linux-7.1.3.tar.xz                 151 MB
└── tools/rxre/github/angr/.git/...pack                    91 MB
```

Una copia de trabajo del proyecto. Con el `.git` **corrupto**: `HEAD` vacio
(0 bytes), `root:root` modo 600, y `git status` respondiendo *"no es un
repositorio git"*. No era worktree registrado, ningun proceso la usaba.

Liberado (con confirmacion del usuario): **`/tmp` de 5,9 G/0 libre a 695 M/5,2 G
libre.**

### Lo que eso desbloqueo, MEDIDO

| Antes | Despues |
|---|---|
| `spatch` -> `Sys_error("No space left on device")` | `status: ok` |
| baseline 33 passed / 6 failed | **39 passed / 0 failed** |

`spatch` (coccinelle) usa `/tmp` **hardcodeado**: ignora `TMPDIR`. No hay
workaround. La unica salida era liberar el directorio.

## EL WORKAROUND DE GHIDRA: MISMO SINTOMA, DISTINTA SALIDA

`binary.decompile` fallaba con:

```text
ERROR REPORT: No queda espacio en el dispositivo
java.io.IOException: No space left on device
```

La diferencia con `spatch`: el JVM SI respeta `-Djava.io.tmpdir`. Asi que el
adapter ahora apunta el temp del JVM al directorio que ya creo y comprobo
escribible:

```text
JAVA_TOOL_OPTIONS=-Djava.io.tmpdir=<tmpdir del adapter>
```

Medido: la misma invocacion sobre el mismo binario pasa de `error` a
`n_functions: 4` con el JSON escrito. Y solo si el usuario no fijo ya uno: un
`JAVA_TOOL_OPTIONS` del entorno gana, que es lo correcto.

`binary.decompile` pasa el gate y persiste.

## DOS BUGS REALES QUE EL INVENTARIO DESTAPO

### 1. Las 8 capacidades `rxre.*` apuntaban a `persistir`... y por eso no eran un bug

```text
rxre.create_finding          funcion='persistir'
rxre.get_finding             funcion='persistir'
... (las 8)
```

Parecia un error de registro. No lo es: `persistir` de `rz_findings` es
**doble proposito**. Cuando lo llama `ejecutar` actua de ENRUTADOR (lee
`env.get("capability")` y despacha a `crear_hallazgo`, `listar_hallazgos`...).
Cuando lo llama `_persistir` guarda. El codigo lo documenta.

El bug real estaba en `ejecutar`:

```python
env["capability"] = capability      # <- se pone DESPUES de llamar
```

El enrutador lee `capability` DENTRO de la llamada, asi que nunca lo veia y
caia por el camino vacio devolviendo `None`:

```text
params={'capability': 'rxre.list_findings'}  -> ok
params={'limit': 5}                          -> None -> traceback
```

Se inyecta el valor que el propio ADAPTERS declara que la funcion necesita. No
se inventa un parametro: se entrega el que la tabla ya pedia.

### 2. Un envelope `None` tumbaba el dispatch entero

```text
TypeError: 'NoneType' object does not support item assignment
    env["capability"] = capability
```

No es un traceback feo: es una violacion de **CUERPO**, que exige que el
estado este CONTROLADO. Un adapter que no responde no es una respuesta; y si
el dispatch se cae, el que llama no recibe ni el estado.

Se convierte en `error` con el motivo. Medido sobre las tres capacidades que lo
provocaban: de traceback a estado controlado.

## EL FIXTURE QUE DECLARABA UNA MENTIRA

`gh_decompile` en modo fixture devolvia:

```text
precheck.usa_fixture    True       <- declara la simulacion
provenance.estado       "completa"
provenance.input_hash   ""
results[0].artifact_hash ""
```

El envelope se contradecia a si mismo: decia en un sitio que era una simulacion
y en otro que la trazabilidad estaba completa. Y no lo estaba: no hay artefacto
que hashear, porque en modo fixture "el ARTEFACTO no tiene que existir".

No se marca incompleta, porque la simulacion SI es completa: reproduce el
producer entero. Lo que no es, es trazabilidad sobre un artefacto real. Se
anade `usa_fixture` a la provenance con la nota de que no hay hash porque no hay
entrada. Un lector ve "completa, con simulacion declarada" y sabe lo que tiene.

## ESTADO

```text
CLAIM=el gate de los ocho principios cubre las 26 capacidades
STATE=PARTIAL (16 verificadas; las demas son fronteras declaradas)

CLAIM=11 capacidades fallaban por 11 razones distintas
STATE=REFUTED (una causa: provenance como cadena; arreglada con un constructor)

CLAIM=el gate aprobaba capacidades que no persistian
STATE=REFUTED (8 adapters sin persistir; fallback generico; 16/16 persisten)

CLAIM=el CLI funciona igual con /tmp lleno
STATE=REFUTED (spatch hardcodea /tmp; Ghidra se arreglo; el resto no tiene salida)

CLAIM=las 8 capacidades rxre.* apuntan mal en el registro
STATE=REFUTED (apuntan a un enrutador doble proposito; el bug era otro)
```

## LO QUE NO SE HIZO

- **No se auditaron las 24 capacidades restantes en profundidad.** 16 pasan; las
  demas son fronteras declaradas, no mediciones:
  - `gpu.register_read` necesita hardware (`0000:01:00.0`) -> NOT_DETERMINED
  - `source.semantic_search` necesita un `.cocci`; no hay ninguno en el repo
  - `rxre.*` son CRUD sobre findings; con base vacia devuelven 0 resultados
- **No se arreglo `cocci_search` de raiz.** Ahora funciona porque se libero
  `/tmp`, no porque se cambio el adapter. Si `/tmp` se vuelve a llenar, vuelve
  a fallar. Eso es una dependencia del entorno, no una propiedad del codigo.
- **No se toco el trabajo de otro actor.** El `test_container1632` que fallaba
  por "26 vs 12" lo arreglo otro actor a las 13:24; verificado que no era mio.
- **No se borro nada sin confirmacion.** Los 5,2 G se liberaron con aprobacion
  explicita del usuario.