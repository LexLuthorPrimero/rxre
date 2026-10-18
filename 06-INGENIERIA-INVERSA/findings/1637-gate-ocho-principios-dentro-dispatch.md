# 1637 — EL GATE DE LOS OCHO PRINCIPIOS ESTÁ DENTRO DEL DISPATCH — MEDIDO

```text
CLASSIFICATION=IMPLEMENTATION
WORK_CLASS=RXRE-AUTO-001
AUTOR=SISTEMA AUTÓNOMO RXRE
FECHA=2026-10-15
TARGET=Polaris12 (RX550) · GFX8 · 1002:699f
QUESTION=¿Qué impide que un resultado `ok` ilegible quede en la base de datos?
STATE=PROVEN
```

## EL AGUJERO QUE ESTE TRABAJO CIERRA

RXRE-ECO-001 (hallazgo 1635) construyó los ocho principios como código ejecutable
y `./rxre audit` para aplicarlos a una operación. La demostración fue
end-to-end y correcta: tres envelopes con el **mismo** `status: ok` y veredictos
distintos.

Pero había un agujero que el propio hallazgorowser no cerraba: **`audit` era
voluntario**. Nada impedía persistir un `ok` sin trazabilidad. Nada lo impedía
porque la puerta no estaba puesta.

Y se notaba en el propio suite. `test_eco_ast001` (58 checks) ponia:

```python
env = ts_ast.parsear(AMDGPU_H, lenguaje="c")
env["persistido"] = True          # <- lo ponía A MANO
```

Por qué a mano: porque nadie más lo ponía. Los 58 checks pasaban y producción
no podía hacer lo mismo. **Un test que fabrica su propia precondición no mide
producción: mide el test.**

## LA PUERTA

`backends/gate.py` + `_persistir()` audita **antes** de tocar la tabla:

```python
if not env.get("gate_evaluado"):
    veredicto = _gate.evaluar(env)
    env["gate_evaluado"] = True
    if not _gate.cerrar_o_abrir(env):
        env["motivo_persistencia"] = "NO se persiste: los ocho principios..."
        return None                     # <- NO hay INSERT
```

El **orden** es la garantía, no un detalle. Si el gate corriera después de
persistir, un envelope inválido ya estaría dentro y habría que borrarlo: y
borrar es una operación que puede fallar. La puerta va antes del `INSERT`.

Medido:

```text
ast_parse   -> gate=True  persistido=True  op=op_fdc3d74bc94fe22e
bin.inspect -> gate=True  persistido=True  op=op_7be10396b66fff89
```

Y bloquea cuando debe:

```text
provenance sin input_hash -> operation_id=None
  motivo: NO se persiste: los ocho principios no cierran la operacion.
          TIERRA en violacion: provenance sin input_hash...
```

## EL DEADLOCK QUE CONSTRUÍ (Y QUE LA PUERTA REVELÓ)

El primer intento **bloqueó el 100% de las operaciones válidas**:

```text
status:         ok
resultados:     1
gate cerrado:   False
BLOQUEO: AGUA en violacion: la operacion NO se persistio
```

Un ciclo, medido:

```
AGUA exige    env["persistido"] is True
persistido    lo pone _persistir() DESPUÉS de persistir
el gate corre ANTES de _persistir()
→ persistido todavía no existe
→ AGUA dice "no persistido"
→ el gate no cierra
→ no se persiste
→ persistido no se pondrá nunca
```

No era un caso raro: era el camino **normal** de toda operación `ok`.

**Primer intento de arreglo** (falló): declarar `persiste_pretendido=True`
después de que el gate apruebe. Es el mismo deadlock — si el gate no aprueba,
esa línea nunca se ejecuta. Lo medí: `persiste_pretendido=None` tras el fallo.

**Arreglo que funciona**: `gate.evaluar()` declara la intención **antes** de
auditar, y AGUA la acepta **como intención declarada**, no como hecho. Lo que
se pierde (AGUA ya no detecta que la escritura falle) lo cubre `ejecutar()`,
que mira el `operation_id` devuelto por la base. La propiedad no se relaja: se
reparte en dos puntos donde cada uno mira lo que puede saber.

## LA CALIBRACIÓN QUE FALTABA (Y ROMPIÓ 3 CHECKS)

Conectar el gate rompió `test_dispatch004` (3 de 132). Sobre `binary.inspect`:

```
ALMA en violacion: la operacion devuelve estructura pero no hay pregunta
ETER sin prueba:   el resultado NO se enlaza con nada: es un dato aislado
```

`binary.inspect` estaba **perfectamente bien**: `provenance` completa con
`input_hash`, `cadena`, `normalizador`. Lo que le faltaba era que ALMA y ETER
estaban calibrados para **una** capacidad: `source.ast_parse`.

**No se relajó el gate.** Relajar sería el error caro: "ALMA no aplica a
`binary.*`" convierte el principio en una lista de exenciones, y a partir de
ahí cada capacidad nueva pediría la suya.

Lo que se hizo fue mirar `scope`, que el envelope **ya declara**:

```text
scope == "source"  -> se exige patron o estructura  (ALMA / ETER)
scope == "binary"  -> se exige artefacto + hash: ESO es la pregunta
```

Y con una regla dura: **si `scope` no está declarado, no hay excepción.** Se
aplica la forma estricta. La excepción se pide, no se asume. Un
`gpu.register_read` de mañana tendrá otro scope y hará falta declararlo.

La razón epistemica, no solo de compatibilidad: ETER diciendo de `/bin/ls` que
es "un dato aislado" es una **afirmación falsa**. Está enlazado al resto del
análisis por su sha256. Un principio que miente sobre la mayoría de las
capacidades no es un principio: es mala calibración con buena intención.

## MUTATION TESTING: 4 DE 5 MUEREN

Y aquí está lo que más valor tiene, porque los **dos primeros escaparon**.

| Mutante | Resultado |
|---|---|
| M1 `cerrar_o_abrir` siempre `True` | 26/33 — **MUERE** |
| M2 bypass de la puerta en dispatch | 25/33 — **MUERE** |
| M4 `persistido=True` sin fila | 32/33 — **MUERE** |
| M6 el gate ignora TIERRA | 29/33 — **MUERE** |
| M5 sin la exención de `blocked` | 33/33 — **EQUIVALENTE** |

### Los dos que escaparon eran fallos del test, no del código

**M1: `cerrar_o_abrir()` era código muerto.** Existía, documentada como "la
decisión, sin adornos", y **no la llamaba nadie**: el dispatch comparaba
`evaluar()` directamente. La función que decide no estaba en el camino de
ninguna decisión real. Un test que la midiera probaría una rama muerta. Se
arregló conectándola, y ahora hay **una** manera de decidir.

**M3: el test miraba tarde.** `test_persistido_no_se_pose_a_mano` afirmaba
`"persistido" not in env` **antes** de persistir. Eso comprueba que el
*adapter* no lo pone —cierto, y no es la pregunta—. El mutante lo ponía en
`_persistir`, después de esa aserción, y no se veía nunca. La versión que
importa afirma **después** y mira los dos lados:

```text
persistido=True  Y  hay fila   -> correcto
persistido=True  Y  no hay fila -> mentira, y el nombre no la delata
```

Por eso mira la **base**. Un booleano sin contraparte material es una promesa,
y las promesas no se verifican solas.

### M5 es equivalente, y se declara como tal

Con M5 un `blocked` no entra en la exención, sino en `_ocho_gate()`. Y `CUERPO`
devuelve `violation` para todo estado que no sea `ok`/`empty`/`unsupported` —
**exactamente el mismo resultado** que la exención.

Dos rutas para lo mismo. Ningún test puede separarlas. La exención sigue siendo
correcta (declarar "no se audita un `blocked`" es más legible que dejar que
CUERPO lo rechace por accidente), pero no es la única que lo consigue, y eso se
documenta en vez de fingirse cobertura.

### M4: el caso que faltaba

`if result is not None` → `if True` pasaba 33/33 porque con `source.ast_parse`
la persistencia **siempre** tiene éxito: o hay `operation_id`, o hay excepción.
El `None` no se daba. Mutante equivalente *bajo las condiciones del suite*.

Equivalente no es inofensivo: es "el suite no lo ejercita". Se fabricó el caso
que faltaba con un adapter que devuelve `None` a propósito.

## EL RIESGO DE AÑADIR UNA PUERTA: QUE SE COMA LOS ERRORES HONESTOS

Un `blocked` significa "el producer no pudo, y lo dice". Si el gate lo bloqueara,
un fallo declarado se volvería invisible (§81). Verificado:

```text
gate.honesto.no_lo_bloquea_la_puerta   PASS
gate.honestado.motivo_es_del_producer  PASS
```

El gate audita `ok`. Nunca `blocked`, `invalid_input`, `error`, `unsupported` ni
`empty` — todos verificados individualmente.

## ESTADO

```text
CLAIM=un resultado ok sin trazabilidad puede persistirse
STATE=REFUTED (37 checks; TIERRA/AIRE rotos -> operation_id=None)

CLAIM=los ocho principios pueden ser una puerta, no un informe
STATE=PROVEN (gate.orden.antes_del_insert + mutación 4/5)

CLAIM=ALMA/ETER aplican igual a source. y a binary.*
STATE=REFUTED (calibrados por scope; un bin.inspect no busca un patron)

CLAIM=M5 (sin la exención) cambia el comportamiento
STATE=EQUIVALENTE (dos rutas, mismo veredicto; documentado, no fingido)
```

## LO QUE NO SE HIZO

- **No se auditaron las 24 capacidades restantes.** Solo `source.ast_parse` y
  `binary.inspect` pasaron por el gate. Las demás están `NOT_DETERMINED`.
- **No se arregló `cocci_search`.** `test_backends_bulk` falla por un bug
  preexistente: el adapter busca el patrón en un fichero que no existe
  (`status: invalid_input`, `no existe el patron: expression x;`). Verificado
  idéntico **con y sin** mis cambios.
- **No se reparó `/tmp`.** Está al 100% (tmpfs, 5,9 G de clones de otro actor).
  Es la causa de ~5 fallos transitorios de la baseline. **No es mío**: no toco
  el trabajo de otro actor.